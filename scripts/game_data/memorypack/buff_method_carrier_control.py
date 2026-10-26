"""Current physical method-carrier bridge, with no concrete formatter admission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.class_creation_instructions import decode_class_creation_instructions
from scripts.game_data.il2cpp.method_carrier_control import validate_method_carrier_control
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL = 'buffMethodCarrierControl'
SCHEMA = 'endfield.buff-method-carrier-control-native-contract.v1'
SCOPE = 'anonymous-encoded-method-and-carrier-normal-control-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_method_carrier_control_native.json'


def _contract():
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if c.get('scope') != SCOPE or set(c['functions']) != {'lookup', 'inflate', 'depth'}:
        raise ValueError(LABEL + '.scope-or-function-set')
    return c


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'scope': SCOPE, 'nativeInputs': pins,
            'concreteGenericArgumentsOrCompiledSharingSelected': False,
            'positiveStoredGrammarAdmitted': False, 'wholeRootAdmitted': False,
            'runtimeExecutionKnown': False}


def _validate_image(image, c):
    index = BodyIndex(image)
    base = image.pe.image_base
    table_rva, image_size, raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(raw, lambda at, n: image.pe.bytes_at_va(base + at, n),
                              table_rva=table_rva, image_size=image_size)
    programs = {}
    families = {}
    for key, function in c['functions'].items():
        family = unwind.family(function['entryRva'])
        if json.loads(json.dumps(family)) != function['unwindFamily']:
            raise ValueError(LABEL + '.complete-unwind-parent-triples:' + key)
        windows = function['codeWindows']
        if len(windows) != len(family['ranges']) or {
                (w['startRva'], w['endRva']) for w in windows} != {
                tuple(r['runtimeTriple'][:2]) for r in family['ranges']}:
            raise ValueError(LABEL + '.owned-window-membership:' + key)
        image.check_windows(windows, label=LABEL)
        rows = []
        for window in windows:
            at = base + window['startRva']
            data = image.pe.bytes_at_va(at, window['endRva'] - window['startRva'])
            rows.extend(checked_rows(decode_class_creation_instructions(index.mapper, data, at), data, LABEL))
        actual = [[int(r['va'], 16)-base, bytes.fromhex(r['bytes']).hex().upper()] for r in rows]
        if actual != function['program']:
            raise ValueError(LABEL + '.complete-program-bytes:' + key)
        programs[key] = rows
        families[key] = family
    caller = c['callerPhysicalSource']
    caller_family = unwind.family(caller['entryRva'])
    if json.loads(json.dumps(caller_family)) != caller['unwindFamily']:
        raise ValueError(LABEL + '.caller-unwind-parent-triples')
    image.check_windows(caller['codeWindows'], label=LABEL)
    caller_ranges = {tuple(r['runtimeTriple'][:2]) for r in caller_family['ranges']}
    if {(w['startRva'], w['endRva']) for w in caller['codeWindows']} != caller_ranges:
        raise ValueError(LABEL + '.caller-owned-window-membership')
    for edge in c['actualCallerTransfers']:
        at = edge['callRva']
        raw = image.pe.bytes_at_va(base + at, 5)
        target = at + 5 + int.from_bytes(raw[1:], 'little', signed=True)
        if raw[:1] != b'\xe8' or raw.hex().upper() != edge['instructionHex'] or target != edge['targetRva']:
            raise ValueError(LABEL + '.actual-caller-transfer')
        if not any(start <= at and at+5 <= end for start, end in caller_ranges):
            raise ValueError(LABEL + '.caller-transfer-outside-owned-range')
    summary = validate_method_carrier_control(programs, image_base=base, contract=c)
    summary['unwindFamilies'] = families
    summary['callerPhysicalSourceUnwindFamily'] = caller_family
    summary['actualCallerTransfers'] = c['actualCallerTransfers']
    summary['callerFullSemanticPublicationProofRevalidated'] = False
    return summary


def validate_current_native_contract(*, gameassembly: Path, metadata: Path):
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                          gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return _skip(gate.status, gate.detail, pins)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'

    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']

    if not unity_matches():
        return _skip('mismatched' if unity.is_file() else 'missing', 'Selected UnityPlayer.dll missing or mismatched', pins)
    summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return _skip(after.status if after.status != 'validated' else 'mismatched', 'Selected native inputs changed during carrier validation', pins)
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
            'concreteGenericArgumentsOrCompiledSharingSelected': False,
            'positiveStoredGrammarAdmitted': False, 'wholeRootAdmitted': False,
            'runtimeExecutionKnown': False, 'evidenceBoundary': c['evidenceBoundary']}
