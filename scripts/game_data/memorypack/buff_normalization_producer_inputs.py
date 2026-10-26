"""Current owned initialization inputs; no live class/provider/root binding."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.normalization_instructions import decode_normalization_instructions
from scripts.game_data.il2cpp.normalization_producer_inputs import validate_producer_inputs
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL = 'buffNormalizationProducerInputs'
SCHEMA = 'endfield.buff-normalization-producer-inputs-native-contract.v1'
SCOPE = 'selected-owned-class-request-and-configuration-writer-inputs'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_normalization_producer_inputs_native.json'


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'nativeInputs': pins, 'scope': SCOPE,
            'concreteGenericSharingSelected': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path):
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if c.get('scope') != SCOPE:
        raise ValueError(LABEL + '.scope')
    pins = c['nativeInputs']
    before = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                          gameassembly=gameassembly, metadata=metadata)
    if before.status != 'validated':
        return _skip(before.status, before.detail, pins)
    unity = Path(before.gameassembly).parent / 'UnityPlayer.dll'

    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']

    if not unity_matches():
        return _skip('mismatched' if unity.is_file() else 'missing', 'Selected UnityPlayer.dll missing or mismatched', pins)
    image = open_native_image(before.gameassembly, before.metadata)
    base = image.pe.image_base
    directory, size, raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(raw, lambda at, n: image.pe.bytes_at_va(base + at, n),
                             table_rva=directory, image_size=size)
    f = c['producer']
    if json.loads(json.dumps(unwind.family(f['entryRva']))) != f['unwindFamily']:
        raise ValueError(LABEL + '.complete-parent-triples')
    ranges = [tuple(r['runtimeTriple'][:2]) for r in f['unwindFamily']['ranges']]
    if len(ranges) != 1 or [(w['startRva'], w['endRva']) for w in f['codeWindows']] != ranges:
        raise ValueError(LABEL + '.owned-code-membership')
    image.check_windows(f['codeWindows'], label=LABEL)
    rows = []
    for w in f['codeWindows']:
        data = image.pe.bytes_at_va(base + w['startRva'], w['endRva'] - w['startRva'])
        rows += checked_rows(decode_normalization_instructions(image.mapper, data, base + w['startRva']), data, LABEL)
    program = [[int(r['va'], 16) - base, bytes.fromhex(r['bytes']).hex().upper()] for r in rows]
    if program != f['program']:
        raise ValueError(LABEL + '.complete-code-inventory')
    for block in c['blocks']:
        if block['kind'] == 'configuration':
            expected = bytes.fromhex(block['sourceImageHex'])
            if image.pe.bytes_at_va(base + block['sourceRva'], len(expected)) != expected:
                raise ValueError(LABEL + '.configuration-image-bytes')
        else:
            for key in ('typeName', 'namespace'):
                literal = block[key]
                expected = bytes.fromhex(literal['rawHex'])
                if image.pe.bytes_at_va(base + literal['targetRva'], len(expected)) != expected:
                    raise ValueError(LABEL + '.request-literal-bytes')
    summary = validate_producer_inputs(program, c['blocks'])
    summary['completeProducerInstructionsChecked'] = len(program)
    summary['completeOwnedRanges'] = len(ranges)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=before.gameassembly, metadata=before.metadata)
    if after.status != 'validated' or not unity_matches():
        return _skip(after.status if after.status != 'validated' else 'mismatched', 'Selected native inputs changed', pins)
    return {'status': 'validated', 'nativeInputs': pins, 'scope': SCOPE, 'summary': summary,
            'concreteGenericSharingSelected': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False,
            'evidenceBoundary': c['evidenceBoundary']}
