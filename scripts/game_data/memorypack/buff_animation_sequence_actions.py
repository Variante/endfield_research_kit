"""PlayAnimation and JumpTo stored fields with independently owned sequences.

Animation strings, raw float bits and the required post-sequence destination
frame are preserved on original spans. Stored values do not prove playback,
callback selection or evaluated sequence control.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_sequence as sequences
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL = 'buffAnimationSequenceActions'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_animation_sequence_actions_native.json'
CHILDREN = ('sequence',)


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-animation-sequence-actions-native-contract.v1',
        status='exact-current-build', label=LABEL)
    if (set(value.get('records', {})) != {'playAnimation', 'jumpTo'}
            or len(value.get('actionDispatch', {})) != 2
            or set(value['actionDispatch'].values()) != set(value['records'])
            or value.get('childTypes') != {'sequence': sequences.TYPE_NAME}
            or value.get('sequenceSourceContract') != sequences.CONTRACT_PATH.name
            or value.get('stringSourceContract') != strings.CONTRACT_PATH.name):
        raise ValueError(f'{LABEL}.contract:shape')
    for key, count, field in (('playAnimation', 16, 'onEndAction'), ('jumpTo', 6, 'conditionAction')):
        record = value['records'][key]
        if record.get('inheritedMemberCount') != 4 or len(record['members']) != count:
            raise ValueError(f'{LABEL}.contract:record-count={key}')
        for member in record['members']:
            kind = member['kind']
            if kind == 'sequence':
                if (member['fieldName'] != field or member['declaredType'] != sequences.TYPE_NAME
                        or member.get('sourceContextInstructionRva') is None):
                    raise ValueError(f'{LABEL}.contract:typed-sequence={key}')
            elif kind == 'byte-payload' and member['declaredType'] == 'string':
                if not isinstance(member.get('sourceCall'), dict):
                    raise ValueError(f'{LABEL}.contract:string-source={key}')
            elif (kind == 'byte' and member['declaredType'] == 'bool'
                    or kind == 'raw4' and member['declaredType'] == 'float'
                    or kind == 'scalar32'):
                continue
            else:
                raise ValueError(f'{LABEL}.contract:member-kind={key}.{member["fieldName"]}')
    last = value['records']['jumpTo']['members'][-1]
    if (last['fieldName'], last['kind'], last['declaredType']) != ('destFrame', 'scalar32', 'int'):
        raise ValueError(f'{LABEL}.contract:required-destination-frame')
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in row['members']]
            for key, row in contract['records'].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = '', field: str = '') -> None:
    contract = _contract()
    source = contract['records'][record]['sourceContract'] if record else CONTRACT_PATH.name
    error = CensusGateError(f'{LABEL}.{check}', source=(CONTRACTS_DIR / source).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract['nativeInputs'])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': expected}
    sequence = children.get('sequence', {})
    if (sequence.get('status') != 'validated' or sequence.get('nativeInputs') != expected
            or sequence.get('typeName') != sequences.TYPE_NAME or sequence.get('readOrder') != sequences.READ_ORDER):
        _fail('shared-sequence', sequences.READ_ORDER, sequence)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else 'missing'
    if actual != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', expected['UnityPlayer.dll'], actual)
    string_native = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if string_native.get('status') != 'validated' or string_native.get('nativeInputs') != expected:
        _fail('string-native', expected, string_native)
    image = open_native_image(gate.gameassembly, gate.metadata)
    proved = {}
    for key, record in contract['records'].items():
        path = CONTRACTS_DIR / record['sourceContract']; source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        proved.update(records_native.validate_named_records(image, source, {key: record}, label=LABEL, fail=_fail))
        for member in record['members']:
            if member['kind'] == 'byte-payload' and member['sourceCall']['targetRva'] not in string_native['sourceHelpers']:
                _fail('string-source-helper', string_native['sourceHelpers'], member['sourceCall'],
                    record=key, field=member['fieldName'])
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract['actionDispatch'].items():
        record = contract['records'][key]; route = routes.get(int(tag))
        if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
                or route.wrapper_name != record['wrapperTypeName']
                or list(route.member_order) != [m['fieldName'] for m in record['members']]
                or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
            _fail('dispatcher-members', record['wrapperTypeName'], None if route is None else route.row(), record=key)
    after = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', expected['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': expected, 'recordMembers': proved,
        'actionDispatch': contract['actionDispatch'], 'stringNative': string_native,
        'evidenceBoundary': contract['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get('children', {})
    native = context.get('animationSequenceActions', {}); sequence = context.get('sequence', {})
    if (native_validation.get('status') != 'validated' or native.get('status') != 'validated'
            or native_validation.get('nativeInputs') != contract['nativeInputs']
            or native.get('nativeInputs') != contract['nativeInputs']
            or native.get('recordMembers') != _members(contract) or native.get('actionDispatch') != contract['actionDispatch']
            or sequence.get('status') != 'validated' or sequence.get('nativeInputs') != contract['nativeInputs']
            or sequence.get('typeName') != sequences.TYPE_NAME or sequence.get('readOrder') != sequences.READ_ORDER
            or native.get('stringNative', {}).get('status') != 'validated'
            or native.get('stringNative', {}).get('nativeInputs') != contract['nativeInputs']
            or str(tag) not in contract['actionDispatch'] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}.decode:depth-limit')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'animation-sequence-action') != tag:
        raise ValueError(f'{LABEL}.decode:physical-tag')
    record = contract['records'][contract['actionDispatch'][str(tag)]]; fields = []
    if reader.peek() == 255:
        reader.take(1, 'null-action-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte', 'scalar32', 'raw4'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, member['fieldName']).hex().upper()
            elif kind == 'byte-payload':
                reader.byte_payload()
                child = strings.decode_source_string(data, source=source, digest=digest, start=begin, end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'], native_validation=native['stringNative'])
                if child.get('wholeStoredSpanExact') is not True or [child.get('start'), child.get('end')] != [begin, reader.pos]:
                    raise ValueError(f'{LABEL}.decode:string-span at={begin}')
                value['child'] = {**child, 'recursiveStoredSchemaExact': True}
            elif kind == 'sequence':
                reader.sequence(depth + 1)
                value['child'] = sequences.decode_value(data, source, digest, begin, reader.pos, native_validation, depth + 1)
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact') is not True
                    or [value['child'].get('start'), value['child'].get('end')] != [begin, reader.pos]):
                raise ValueError(f'{LABEL}.decode:child-span at={begin}')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                'kind': kind, 'start': begin, 'end': reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-animation-sequence-action-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'tag': tag, 'typeName': record['runtimeTypeName'],
        'start': start, 'end': end, 'namedFields': fields, 'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
