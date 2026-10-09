"""Re-prove TickInterval's named consumer claims on the selected client.

Claims carry no build-specific addresses. Unsupported current bodies become
pendingReview, and every failed input or claim gate supplies no consumer rows.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import (open_native_image, read_reviewed_contract,
    NATIVE_MAPPER_PATH, METADATA_HELPER_PATH)
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots

CONTRACT_PATH = CONTRACTS_DIR / 'buff_tick_interval_consumers_native.json'
SCHEMA = 'endfield.buff-tick-interval-consumer-claims.v1'


def _unity_hash(path: Path) -> str | None:
    if not path.is_file(): return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def _proof_sources() -> list[dict[str, Any]]:
    return _parser_source_snapshots(Path(__file__)) + [_fingerprint(path)
        for path in (CONTRACT_PATH, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH)]


def load_consumer_claims(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    sources = _proof_sources()
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='reviewed', label='buffTickIntervalConsumers')
    gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    result = {'schema': 'endfield.buff-tick-interval-consumer-audit.v1', 'status': gate.status,
        'detail': gate.detail, 'rows': [], 'failures': [], 'contract': CONTRACT_PATH.as_posix(),
        'evidenceBoundary': contract['evidenceBoundary'], 'runtimeSchedulingOrEffectsObserved': False,
        'storedRootAdmitted': False, 'provenance': {'inputs': sources}}
    if gate.status != 'validated': return result
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    unity_hash = _unity_hash(unity)
    if unity_hash is None:
        return {**result, 'status': 'missing', 'detail': 'UnityPlayer.dll missing'}
    pins = {'GameAssembly.dll': gate.gameassembly_sha256,
        'global-metadata.dat': gate.metadata_sha256, 'UnityPlayer.dll': unity_hash}
    result['nativeInputs'] = pins
    index = BodyIndex(open_native_image(gate.gameassembly, gate.metadata))
    rows, failures = evaluate(index, contract['methods'])
    diagnostics = [{**failure, 'validator': 'buffTickIntervalConsumers',
        'source': CONTRACT_PATH.as_posix(), 'nativeInputs': pins} for failure in failures]
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    unity_after = _unity_hash(unity)
    if after.status != 'validated' or unity_after != unity_hash:
        return {**result, 'status': after.status if after.status != 'validated' else 'missing' if unity_after is None else 'mismatched',
            'detail': 'native inputs changed during consumer validation',
            'failures': diagnostics + [{'validator': 'buffTickIntervalConsumers', 'check': 'native-inputs-after',
                'source': str(gate.gameassembly), 'expected': pins,
                'actual': {'selectedGate': after.detail, 'UnityPlayer.dll': unity_after}}]}
    drift = [{'validator': 'buffTickIntervalConsumers', 'check': 'proof-source-after',
        'source': source['path'], 'expected': source, 'actual': actual}
        for source in sources if (actual := _fingerprint(Path(source['path']))) != source]
    if drift:
        return {**result, 'status': 'pendingReview', 'detail': 'proof sources changed during consumer validation',
            'failures': diagnostics + drift}
    return {**result, 'status': 'pendingReview' if failures else 'validated',
        'detail': f'{len(failures)} failed claim(s)' if failures else '',
        'rows': [] if failures else rows, 'failures': diagnostics}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path); parser.add_argument('--metadata', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / root) for root in ('reports', 'scratch', 'tmp')):
        parser.error('--output must be under reports/, scratch/ or tmp/')
    result = load_consumer_claims(gameassembly=args.gameassembly, metadata=args.metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'rows': len(result['rows']),
        'failures': result['failures'], 'detail': result['detail']}, ensure_ascii=False), flush=True)
    return 0 if result['status'] == 'validated' else 1


if __name__ == '__main__':
    raise SystemExit(main())
