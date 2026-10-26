"""Authenticate selected name/key/index/type-copy controls on explicit inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.normalization_instructions import decode_normalization_instructions
from scripts.game_data.il2cpp.class_name_lookup_control import validate_class_name_lookup
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL = 'buffClassNameLookup'
SCHEMA = 'endfield.buff-class-name-lookup-native-contract.v1'
SCOPE = 'complete-owned-control-and-selected-name-key-index-and-type-copy-projections'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_class_name_lookup_native.json'


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'nativeInputs': pins, 'scope': SCOPE,
            'classLookupReturnedNamedClassProved': False, 'concreteDamageTypeSharingSelected': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}


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
    programs = {}
    for key, f in c['functions'].items():
        if json.loads(json.dumps(unwind.family(f['entryRva']))) != f['unwindFamily']:
            raise ValueError(LABEL + '.complete-parent-triples:' + key)
        ranges = [tuple(r['runtimeTriple'][:2]) for r in f['unwindFamily']['ranges']]
        if [(w['startRva'], w['endRva']) for w in f['ownedWindows']] != ranges:
            raise ValueError(LABEL + '.owned-code-membership:' + key)
        image.check_windows(f['ownedWindows'], label=LABEL + '.' + key)
        rows = []
        for w in f['ownedWindows']:
            data = image.pe.bytes_at_va(base + w['startRva'], w['endRva'] - w['startRva'])
            rows += checked_rows(decode_normalization_instructions(image.mapper, data, base + w['startRva']), data, LABEL)
        programs[key] = sorted(rows, key=lambda row: int(row['va'], 16))
    md = image.metadata
    header_field = 8 + 8 * list(md.sections).index('typeDefinitions')
    if md.type_record_size != c['layout']['typeRecordBytes'] or header_field != c['layout']['typeDefinitionsHeader']:
        raise ValueError(LABEL + '.selected-metadata-record-layout')
    summary = validate_class_name_lookup(programs, image_base=base, contract=c, metadata_records=len(md.types))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=before.gameassembly, metadata=before.metadata)
    if after.status != 'validated' or not unity_matches():
        return _skip(after.status if after.status != 'validated' else 'mismatched', 'Selected native inputs changed', pins)
    return {'status': 'validated', 'nativeInputs': pins, 'scope': SCOPE, 'summary': summary,
            'conditions': c['conditions'], 'evidenceBoundary': c['evidenceBoundary'],
            'classLookupReturnedNamedClassProved': False, 'concreteDamageTypeSharingSelected': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
