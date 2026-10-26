"""Reprove Buff AI consumer field-to-argument claims on explicit native inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.instance_string_field_calls import MODE as STRING_FIELDS_MODE, prove as prove_string_fields
from scripts.game_data.il2cpp.ai_blackboard_selection import MODE as AI_SELECTION_MODE, prove as prove_ai_selection
from scripts.game_data.il2cpp.guarded_reference_getter import MODE as REFERENCE_GETTER_MODE, prove as prove_reference_getter
from scripts.game_data.il2cpp.generic_lookup_forwarding import MODE as LOOKUP_FORWARDING_MODE, prove as prove_lookup_forwarding
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _package_import_closure
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR/'buff_ai_consumer_claims.json'
SCHEMA = 'endfield.buff-ai-consumer-claims.v6'
PROVERS = {STRING_FIELDS_MODE: prove_string_fields, AI_SELECTION_MODE: prove_ai_selection,
           REFERENCE_GETTER_MODE: prove_reference_getter, LOOKUP_FORWARDING_MODE: prove_lookup_forwarding}


def audit(*, gameassembly: Path, metadata: Path, expected_gameassembly_sha256: str,
          expected_metadata_sha256: str, expected_unityplayer_sha256: str) -> dict:
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, status='reviewed', label='buffAiConsumers')
    report = {'schema': SCHEMA, 'status': 'pendingReview', 'claims': [], 'failures': [],
              'contractSha256': digest, 'evidenceBoundary': contract['evidenceBoundary'],
              'wholeRootGains': 0, 'runtimeExecutionKnown': False}
    paths = set(_package_import_closure(Path(__file__))) | {CONTRACT, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    inputs = [_fingerprint(p) for p in sorted(paths)]
    report['proofSources'] = inputs

    def gate():
        native = check_installed_native_inputs(expected_gameassembly_sha256, expected_metadata_sha256,
                                              gameassembly=gameassembly, metadata=metadata)
        if native.status != 'validated':
            return native.status, native.detail
        unity = Path(native.gameassembly).parent/'UnityPlayer.dll'
        if not unity.is_file():
            return 'missing', 'UnityPlayer.dll missing beside selected native image'
        if _fingerprint(unity)['sha256'] != expected_unityplayer_sha256.upper():
            return 'mismatched', 'Selected UnityPlayer.dll hash differs'
        for pin in inputs:
            if _fingerprint(Path(pin['path'])) != pin:
                return 'pendingReview', 'Source changed during evaluation: '+pin['path']
        return 'validated', ''

    status, detail = gate()
    if status != 'validated':
        report.update(status=status, failures=[{'check': 'selected-inputs', 'detail': detail}])
        return report
    report['nativeInputs'] = {'GameAssembly.dll': expected_gameassembly_sha256.upper(),
                             'global-metadata.dat': expected_metadata_sha256.upper(),
                             'UnityPlayer.dll': expected_unityplayer_sha256.upper()}
    rows = []
    symbol = '<native-image>'
    try:
        index = BodyIndex(open_native_image(gameassembly, metadata))
        for symbol, claim in contract['claims'].items():
            if claim.get('mode') not in PROVERS:
                raise ValueError('Unsupported named claim mode: '+str(claim.get('mode')))
            rows.append({'symbol': symbol, **PROVERS[claim['mode']](index, claim)})
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, StopIteration) as error:
        report['failures'].append({'check': 'named-claim', 'symbol': symbol, 'detail': str(error)[:2000]})
        return report
    status, detail = gate()
    if status != 'validated':
        report.update(status=status, failures=[{'check': 'selected-inputs-after', 'detail': detail}])
        return report
    report.update(status='validated', claims=rows)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--expected-gameassembly-sha256', required=True)
    parser.add_argument('--expected-metadata-sha256', required=True)
    parser.add_argument('--expected-unityplayer-sha256', required=True)
    parser.add_argument('--output', type=Path, default=REPO_ROOT/'reports/game_data/buff_ai_consumers_latest.json')
    args = parser.parse_args(argv)
    report = audit(gameassembly=args.gameassembly, metadata=args.metadata,
                   expected_gameassembly_sha256=args.expected_gameassembly_sha256,
                   expected_metadata_sha256=args.expected_metadata_sha256,
                   expected_unityplayer_sha256=args.expected_unityplayer_sha256)
    destination = args.output if report['status'] == 'validated' else args.output.with_name(args.output.stem+'_failure'+args.output.suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'claims': len(report['claims']), 'failures': report['failures'],
                      'report': str(destination)}), flush=True)
    return 0 if report['status'] == 'validated' else 1


if __name__ == '__main__':
    raise SystemExit(main())
