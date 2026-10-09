"""Positive Timeline source elements, independently of their enclosing list.

This lane authenticates generated source-wrapper programs and original spans.
It deliberately has no Buff root/list admission: reference adapter selection,
nullable runtime output and the positive list composition remain separate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import _writes_register
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buffered_owned_sources as buffered
from scripts.game_data.memorypack import setter_output_sources as setters
from scripts.game_data.memorypack import buff_sequence as sequence
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT

LABEL = 'buffTimelineElementSource'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_timeline_element_sources_native.json'
SCHEMA = 'endfield.buff-timeline-element-sources-native-contract.v1'
SCOPE = 'positive-source-wrapper-elements-only'
FIELD_TYPES = {
    'timeline': [('_endFrame', 'int'), ('_sequenceActionData', sequence.TYPE_NAME),
                 ('_startFrame', 'int'), ('forceSyncAnimData', 'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData')],
    'forceSync': [('forceSync', 'bool'), ('montageName', 'string'),
                  ('playbackSpeed', 'float'), ('targetFrame', 'int')],
}
KINDS = {
    'timeline': ['complete-buffered-int32-call', 'closed-reference-read',
                 'inline-original-buffer-load', 'closed-reference-read'],
    'forceSync': ['complete-normalized-byte-call', 'reviewed-physical-string-source-call',
                  'inline-original-buffer-load', 'inline-original-buffer-load'],
}


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status='exact-current-build', label=LABEL)
    if contract.get('scope') != SCOPE or set(contract['records']) != set(FIELD_TYPES):
        raise ValueError(f'{LABEL}.contract:scope-or-records')
    for key, record in contract['records'].items():
        if (record['memberCount'] != 4
                or [(m['fieldName'], m['declaredType']) for m in record['members']] != FIELD_TYPES[key]
                or [m['kind'] for m in record['members']] != KINDS[key]):
            raise ValueError(f'{LABEL}.contract:ordered-field-profile={key}')
    return contract


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _header(image: Any, record: dict, offsets: dict) -> None:
    program = record['positiveProgram']; header = record['header']
    positions = {row[0]: n for n, row in enumerate(program)}
    start = positions[header['readRva']] - 1
    segment = program[start:start + 9]
    expected = [f'488B43{offsets["currentPtr"]:02X}', '0FB630',
        f'8B6B{offsets["bufferLength"]:02X}', '83ED01', segment[4][1],
        f'48FF43{offsets["currentPtr"]:02X}', f'FF43{offsets["advancedCount"]:02X}',
        f'FF43{offsets["consumed"]:02X}', f'896B{offsets["bufferLength"]:02X}']
    branch = bytes.fromhex(segment[4][1])
    if ([r[1] for r in segment] != expected or len(branch) != 2 or branch[0] != 0x79
            or segment[4][0] + 2 + int.from_bytes(branch[1:], 'little', signed=True) != segment[5][0]):
        _fail('header-buffered-accounting', 'one byte into ESI and all four reader counters', segment)
    for key, literal in (('nullComparisonRva', 'FF'), ('positiveComparisonRva', '04')):
        n = positions[header[key]]; raw = bytes.fromhex(program[n + 1][1])
        wanted = b'\x0f\x84' if literal == 'FF' else b'\x0f\x85'
        if (program[n][1] != '4080FE' + literal or len(raw) != 6 or raw[:2] != wanted
                or program[n + 2][0] != program[n + 1][0] + 6):
            _fail('header-positive-branch', 'FF not taken; exact four-member branch not taken', program[n:n + 3])
    end = positions[header['positiveComparisonRva']]
    for at, raw_hex in program[start + 2:end]:
        raw = bytes.fromhex(raw_hex)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or _writes_register(decoded[0], 'rsi'):
            _fail('header-value-preservation', 'original header in nonvolatile RSI until count comparison', [at, raw_hex])


def _validate_image(image: Any, contract: dict) -> dict:
    selected = NativeReferenceContext(image); offsets = contract['readerFieldsUnboxedOffsets']
    if (image.type_name(contract['readerTypeDefinition']) != 'MemoryPack.MemoryPackReader'
            or not selected.is_value_type('MemoryPack.MemoryPackReader')
            or offsets != {n: selected.field('MemoryPack.MemoryPackReader::' + n)[2] - 16 for n in offsets}
            or set(offsets) != {'currentPtr', 'bufferLength', 'advancedCount', 'consumed'}
            or any(type(n) is not int or not 0 <= n < 128 for n in offsets.values())
            or len(set(offsets.values())) != 4):
        _fail('reader-layout', 'four distinct metadata-owned unboxed Reader fields', offsets)
    buffered.validate_int32_source(image, contract['int32Source'], offsets, fail=_fail)
    dependencies = contract['dependencies']
    byte_source = json.loads((CONTRACTS_DIR / dependencies['normalizedByteSource']).read_bytes())
    byte_records = json.loads((CONTRACTS_DIR / dependencies['normalizedByteRecord']).read_bytes())
    key, index = dependencies['normalizedByteMember']; byte_member = byte_records['records'][key]['members'][index]
    string_source = strings._contract(); sequence_source = sequence._contract()
    for name, dependency in (('byte-record', byte_records),
                             ('string-source', string_source), ('sequence-source', sequence_source)):
        if dependency['nativeInputs'] != contract['nativeInputs']:
            _fail('dependency-build', contract['nativeInputs'], {name: dependency['nativeInputs']})
    setters.validate_primitive_source(image, byte_source, byte_member, fail=_fail)
    byte_window = next(w for w in byte_source['codeWindows']
                       if w['startRva'] == byte_member['sourceCall']['targetRva'])
    image.check_windows([byte_window], label=LABEL)
    sequence.validate_selected_source(image, sequence_source)
    fields = {}
    for key, record in contract['records'].items():
        fields[key] = buffered.validate_owned_program(image, record, offsets, fail=_fail)
        _header(image, record, offsets)
    int_member = contract['records']['timeline']['members'][0]
    bool_member, string_member = contract['records']['forceSync']['members'][:2]
    if (int_member['sourceCall']['targetRva'] != contract['int32Source']['window']['startRva']
            or bool_member['sourceCall']['targetRva'] != byte_member['sourceCall']['targetRva']
            or string_member['sourceCall']['targetRva'] not in string_source['sourceHelpers']):
        _fail('physical-source-binding', 'complete authenticated Int32/bool/string helpers',
              [int_member['sourceCall'], bool_member['sourceCall'], string_member['sourceCall']])
    return fields


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                      metadata: Path | None = None) -> dict[str, Any]:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins, 'scope': SCOPE}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
                'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins, 'scope': SCOPE}
    fields = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    utf8 = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if utf8.get('status') != 'validated' or utf8.get('nativeInputs') != pins:
        return {'status': utf8.get('status', 'unresolved'), 'detail': 'UTF-8 source helper gate',
                'nativeInputs': pins, 'scope': SCOPE}
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during validation', 'nativeInputs': pins, 'scope': SCOPE}
    return {'status': 'validated', 'nativeInputs': pins, 'scope': SCOPE, 'recordMembers': fields,
            'utf8Source': utf8, 'wholeRootAdmitted': False, 'positiveListAdmitted': False,
            'evidenceBoundary': contract['evidenceBoundary']}


def decode_positive_element(data: bytes, *, source: str, digest: str, start: int, end: int,
                            native_validation: dict[str, Any], recursive_actions: dict[str, Any],
                            depth: int = 0) -> dict[str, Any]:
    """Certify one original positive source element, without admitting its list."""
    contract = _contract(); proof = native_validation
    expected = {k: [{'fieldName': m['fieldName'], 'declaredType': m['declaredType'], 'kind': m['kind']}
                    for m in record['members']] for k, record in contract['records'].items()}
    if (proof.get('status') != 'validated' or proof.get('scope') != SCOPE
            or proof.get('nativeInputs') != contract['nativeInputs'] or proof.get('recordMembers') != expected
            or proof.get('positiveListAdmitted') is not False or proof.get('wholeRootAdmitted') is not False
            or recursive_actions.get('status') != 'validated'
            or recursive_actions.get('nativeInputs') != contract['nativeInputs']
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}.decode:depth-limit')
    reader = Reader(data, source, end); reader.pos = start; reader.header(4); fields = []
    def scalar(name: str, width: int, declared: str) -> dict:
        begin = reader.pos; raw = reader.take(width, name)
        return {'fieldName': name, 'declaredType': declared, 'start': begin, 'end': reader.pos,
                'rawHex': raw.hex().upper()}
    fields.append(scalar('_endFrame', 4, 'int'))
    begin = reader.pos
    child = sequence.decode_value(data, source, digest, begin, end, recursive_actions, depth,
                                  require_end=False)
    if (child.get('recursiveStoredSchemaExact') is not True or child.get('start') != begin
            or type(child.get('end')) is not int or not begin < child['end'] < end):
        raise ValueError(f'{LABEL}.decode:sequence-child-span')
    reader.pos = child['end']
    fields.append({'fieldName': '_sequenceActionData', 'declaredType': sequence.TYPE_NAME,
                   'start': begin, 'end': reader.pos, 'child': child})
    fields.append(scalar('_startFrame', 4, 'int'))
    force_start = reader.pos; reader.header(4); force_fields = [scalar('forceSync', 1, 'bool')]
    begin = reader.pos; reader.byte_payload()
    helper = contract['records']['forceSync']['members'][1]['sourceCall']['targetRva']
    string = strings.decode_source_string(data, source=source, digest=digest, start=begin, end=reader.pos,
        source_helper_rva=helper, native_validation=proof.get('utf8Source', {}))
    force_fields.append({'fieldName': 'montageName', 'declaredType': 'string',
                         'start': begin, 'end': reader.pos, 'child': string})
    force_fields.append(scalar('playbackSpeed', 4, 'float'))
    force_fields.append(scalar('targetFrame', 4, 'int'))
    fields.append({'fieldName': 'forceSyncAnimData', 'declaredType': FIELD_TYPES['timeline'][-1][1],
        'start': force_start, 'end': reader.pos, 'child': {'start': force_start, 'end': reader.pos,
            'namedFields': force_fields, 'positiveSourceFieldsExact': True}})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:original-element-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-positive-timeline-source-element-receipt.v1',
        'source': source, 'logicalSha256': digest.upper(), 'start': start, 'end': end,
        'typeName': contract['records']['timeline']['runtimeTypeName'], 'namedFields': fields,
        'positiveSourceFieldsExact': True, 'recursiveStoredSchemaExact': False,
        'positiveListAdmitted': False, 'wholeRootAdmitted': False, 'runtimeMeaningExact': False,
        'scope': SCOPE, 'evidenceBoundary': contract['evidenceBoundary']}
