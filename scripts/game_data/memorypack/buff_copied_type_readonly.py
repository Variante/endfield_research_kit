"""Authenticate selected closed search/comparer stack-only effects."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.normalization_instructions import decode_normalization_instructions
from scripts.game_data.il2cpp.owned_partition import checked_rows, check_byte_partition
from scripts.game_data.il2cpp.type_comparer_control import validate_type_comparer
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL = 'buffCopiedTypeReadonly'
SCHEMA = 'endfield.buff-copied-type-readonly-native-contract.v1'
SCOPE = 'closed-search-type-comparer-and-count-leaf-control-conditional-stack-only-effects-and-selected-comparisons'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_copied_type_readonly_native.json'


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'nativeInputs': pins, 'scope': SCOPE,
            'inputTypeCopyPreservationProved': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


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
    unwind = UnwindChainIndex(raw, lambda at, n: image.pe.bytes_at_va(base + at, n), table_rva=directory, image_size=size)
    programs = {}
    for role, f in c['functions'].items():
        pieces = []
        if f['ownershipKind'] == 'exceptionFamily':
            if json.loads(json.dumps(unwind.family(f['entryRva']))) != f['unwindFamily']:
                raise ValueError(LABEL + '.complete-parent-triples:' + role)
            owned = [tuple(r['runtimeTriple'][:2]) for r in f['unwindFamily']['ranges']]
            if [(w['startRva'], w['endRva']) for w in f['ownedWindows']] != owned:
                raise ValueError(LABEL + '.owned-code-membership:' + role)
            image.check_windows(f['ownedWindows'], label=LABEL + '.' + role)
        elif f['ownershipKind'] == 'closedEntryProgram':
            if role != 'countLeaf' or f['unwindFamily'] is not None or f['ownedWindows'] or f['entryRva'] in unwind.entries:
                raise ValueError(LABEL + '.closed-entry-ownership')
            owned = []
        else:
            raise ValueError(LABEL + '.unreviewed-ownership')
        image.check_windows(f['codeWindows'] + f['paddingWindows'], label=LABEL + '.' + role)
        rows = []
        for w in f['codeWindows']:
            data = image.pe.bytes_at_va(base + w['startRva'], w['endRva'] - w['startRva'])
            rows.extend(checked_rows(decode_normalization_instructions(image.mapper, data, base + w['startRva']), data, LABEL))
            pieces.append((w['startRva'], w['endRva'], 'code'))
        for w in f['paddingWindows']:
            data = image.pe.bytes_at_va(base + w['startRva'], w['endRva'] - w['startRva'])
            if data != bytes.fromhex(w['rawHex']):
                raise ValueError(LABEL + '.padding-values')
            pieces.append((w['startRva'], w['endRva'], 'padding'))
        if 'table' in f:
            t = f['table']
            image.check_windows([t], label=LABEL + '.table')
            data = image.pe.bytes_at_va(base + t['startRva'], t['endRva'] - t['startRva'])
            if data != bytes.fromhex(t['rawHex']) or data != b''.join(value.to_bytes(4, 'little') for value in t['targetRvas']):
                raise ValueError(LABEL + '.table-values')
            pieces.append((t['startRva'], t['endRva'], 'table'))
        if owned:
            check_byte_partition(owned, pieces, LABEL + '.' + role)
        elif len(f['codeWindows']) != 1 or f['codeWindows'][0]['startRva'] != f['entryRva']:
            raise ValueError(LABEL + '.closed-entry-window')
        programs[role] = sorted(rows, key=lambda row: int(row['va'], 16))
    parent = c['parentCall']
    encoded = image.pe.bytes_at_va(base + parent['siteRva'], 5)
    target = parent['siteRva'] + 5 + int.from_bytes(encoded[1:], 'little', signed=True)
    if encoded.hex().upper() != parent['instructionHex'] or encoded[0] != 0xe8 or target != c['functions']['search']['entryRva']:
        raise ValueError(LABEL + '.actual-constructor-call')
    summary = validate_type_comparer(programs, image_base=base, contract=c)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=before.gameassembly, metadata=before.metadata)
    if after.status != 'validated' or not unity_matches():
        return _skip(after.status if after.status != 'validated' else 'mismatched', 'Selected native inputs changed', pins)
    return {'status': 'validated', 'nativeInputs': pins, 'scope': SCOPE, 'summary': summary,
            'actualConstructorCallJoined': True, 'conditions': c['conditions'], 'evidenceBoundary': c['evidenceBoundary'],
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
