"""Named BlowOffCharacter storage with a distinct inherited priority child.

The priority child has four required members. Its closed int/int base and
actual inherited setters are proved independently of generic zero offsets.
Targets, direction and four BlackboardDouble children keep their own proofs.
Stored flags, priority and speeds do not establish evaluated blow-off effects.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as directions
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack.inherited_reference_sources import validate_key_flag_int_flag

LABEL = 'buffBlowOffCharacterAction'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_blow_off_character_action_native.json'
CHILDREN = ('target', 'direction', 'effectVectors')


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-blow-off-character-action-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(value.get('records', {})) != {'blowOff', 'blowPriority'} or value.get('actionDispatch') != {'28': 'blowOff'}
            or {k: len(r['members']) for k, r in value['records'].items()} != {'blowOff': 15, 'blowPriority': 4}
            or value['records']['blowPriority']['members'][-1]['fieldName'] != 'useCustomValue'):
        raise ValueError(f'{LABEL}.contract:shape')
    for member in value['records']['blowOff']['members']:
        if member['kind'] in value['childTypes'] and (member['declaredType'] != value['childTypes'][member['kind']]
                or member.get('sourceContextInstructionRva') is None):
            raise ValueError(f'{LABEL}.contract:typed-child={member["fieldName"]}')
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in r['members']]
            for k, r in contract['records'].items()}


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, nativeInputs=_contract()['nativeInputs'])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    for name in CHILDREN:
        if children.get(name, {}).get('status') != 'validated' or children[name].get('nativeInputs') != pins:
            _fail('shared-child', {'name': name, 'nativeInputs': pins}, children.get(name))
    scalar_native = children['effectVectors'].get('scalarNative', {})
    if (scalar._contract()['nativeInputs'] != pins or scalar_native.get('status') != 'validated'
            or scalar_native.get('sourceStoreValidated') is not True
            or scalar_native.get('selectedReadOrder') != scalar._contract()['selectedReadOrder']):
        _fail('scalar-native', 'outer selected native gate and owned scalar read-order', scalar_native)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', pins['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    source_path = CONTRACTS_DIR / contract['records']['blowOff']['sourceContract']
    source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=source_path)
    proved = named.validate_named_records(image, source, {'blowOff': contract['records']['blowOff']},
        label=LABEL, fail=lambda check, expected, actual, **_details: _fail(check, expected, actual))
    string_native = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if string_native.get('status') != 'validated' or string_native.get('nativeInputs') != pins:
        _fail('string-native', pins, string_native)
    proved['blowPriority'] = validate_key_flag_int_flag(image, source, contract['records']['blowPriority'],
        contract['inheritedReferenceSource'], string_helpers=string_native['sourceHelpers'], fail=_fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    record = contract['records']['blowOff']; route = routes.get(next(iter(supported_tags())))
    if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != record['wrapperTypeName']
            or list(route.member_order) != [m['fieldName'] for m in record['members']]
            or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members', record['wrapperTypeName'], None if route is None else route.row())
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', pins['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': contract['actionDispatch'], 'stringNative': string_native,
        'evidenceBoundary': contract['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get('children', {}); native = context.get('blowOff', {})
    if (native_validation.get('status') != 'validated' or native.get('status') != 'validated'
            or native_validation.get('nativeInputs') != contract['nativeInputs'] or native.get('nativeInputs') != contract['nativeInputs']
            or native.get('recordMembers') != _members(contract) or native.get('actionDispatch') != contract['actionDispatch']
            or any(context.get(n, {}).get('status') != 'validated' or context[n].get('nativeInputs') != contract['nativeInputs'] for n in CHILDREN)
            or native.get('stringNative', {}).get('status') != 'validated' or native['stringNative'].get('nativeInputs') != contract['nativeInputs']
            or context['effectVectors'].get('scalarNative', {}).get('status') != 'validated'
            or context['effectVectors']['scalarNative'].get('sourceStoreValidated') is not True
            or context['effectVectors']['scalarNative'].get('selectedReadOrder') != scalar._contract()['selectedReadOrder']
            or scalar._contract()['nativeInputs'] != contract['nativeInputs']
            or str(tag) not in contract['actionDispatch'] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'blow-off-action') != tag:
        raise ValueError(f'{LABEL}.decode:physical-tag')

    def record(key: str) -> dict[str, Any]:
        begin = reader.pos; plan = contract['records'][key]; fields = []
        if reader.peek() == 255:
            reader.take(1, 'null-' + key)
            return {'start': begin, 'end': reader.pos, 'status': 'exact-null-wrapper', 'namedFields': [], 'recursiveStoredSchemaExact': True}
        reader.header(len(plan['members']))
        for member in plan['members']:
            at = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte', 'scalar32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, member['fieldName']).hex().upper()
                if key == 'blowPriority' and kind == 'byte':
                    value['normalSourceNormalizedValue'] = int(value['rawHex'], 16) != 0
            elif kind == 'byte-payload':
                reader.byte_payload()
                child = strings.decode_source_string(data, source=source, digest=digest, start=at, end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'], native_validation=native['stringNative'])
                value['child'] = {**child, 'recursiveStoredSchemaExact': child.get('wholeStoredSpanExact') is True}
            elif kind == 'scalar-flag-payload':
                value['child'] = record('blowPriority')
            elif kind == 'scalar-payload':
                reader.scalar_payload()
                child = scalar.decode_adding_cooldown(data, at, reader.pos, native_validation=context['effectVectors']['scalarNative'])
                value['child'] = {**child, 'start': child['startOffset'], 'end': child['consumedEnd'],
                                  'recursiveStoredSchemaExact': child.get('wholeValueExact') is True}
            elif kind == 'target':
                reader.target_profile(); span = {'start': at, 'end': reader.pos, 'fieldName': member['fieldName']}
                value['child'] = ({**span, 'status': 'exact-null-wrapper', 'recursiveStoredSchemaExact': True}
                    if data[at:reader.pos] == b'\xff' else target_decoder(data, source, digest, span, context))
            elif kind == 'direction':
                reader.direction_profile()
                child = directions.decode_direction_settings_value(data, source=source, logical_sha256=digest,
                    start=at, end=reader.pos, native_validation=context['direction'])
                if child.get('wholeStoredSpanExact') is not True or any(m.get('nestedTargetStatus') != 'exact-null'
                        for m in child['namedMembers'] if m['kind'] == 'object'):
                    raise ValueError(f'{LABEL}.decode:positive-direction-target at={at}')
                value['child'] = {**child, 'recursiveStoredSchemaExact': True}
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact') is not True
                    or [value['child'].get('start'), value['child'].get('end')] != [at, reader.pos]):
                raise ValueError(f'{LABEL}.decode:child-span at={at}')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                           'kind': kind, 'start': at, 'end': reader.pos, **value})
        return {'start': begin, 'end': reader.pos, 'typeName': plan['runtimeTypeName'],
                'namedFields': fields, 'recursiveStoredSchemaExact': True}

    parent = record('blowOff')
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-blow-off-character-action-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'tag': tag, 'start': start, 'end': end,
        'typeName': contract['records']['blowOff']['runtimeTypeName'], 'parent': parent,
        'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
