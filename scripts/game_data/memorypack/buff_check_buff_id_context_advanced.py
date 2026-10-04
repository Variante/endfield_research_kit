"""Compose the advanced Buff-ID condition with its typed stored children.

BlackboardBuffId inherits BlackboardString's three members. Its own source
reader must independently prove the same ordered source-helper/setter calls
before the shared value decoder can name an element of this different list.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as strings
from scripts.game_data.memorypack import buff_selector_shared_children as query
from scripts.game_data.memorypack import skill_timeline_check_buff_id_context_advanced as parent

LABEL = 'buffCheckBuffIdContextAdvanced'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_check_buff_id_context_advanced_native.json'


def _contracts():
    contract = json.loads(CONTRACT_PATH.read_bytes())
    source = json.loads((CONTRACTS_DIR / contract['sourceContract']).read_bytes())
    shared = strings._contract()
    parent_contract = parent._contract()
    if (contract.get('schema') != 'endfield.buff-check-buff-id-context-advanced-native-contract.v1'
            or contract.get('status') != 'exact-current-build'
            or contract.get('nativeInputs') != shared['nativeInputs']
            or contract.get('nativeInputs') != parent_contract['nativeInputs']
            or contract.get('sourceContract') != parent_contract['nestedSourceContract']
            or contract.get('parentContract') != parent.CONTRACT_PATH.name
            or contract.get('childContract') != strings.CONTRACT_PATH.name
            or source.get('anonymousReadOrder', {}).get('member3') != list(strings.READ_KINDS)
            or contract.get('serializedMemberCount') != len(strings.READ_ORDER)
            or [row.get('fieldName') for row in contract.get('sourceReads', [])] != list(strings.READ_ORDER)
            or [row.get('readKind') for row in contract['sourceReads']] != list(strings.READ_KINDS)
            or contract.get('listTypeName') != f"System.Collections.Generic.List`1<{contract['childTypeName']}>"):
        raise ValueError(f'{LABEL}.contract:shape-or-dependency')
    return contract, source, shared, parent_contract


def supported_tag():
    return _contracts()[3]['dispatcher']['unionTag']


def _fail(check, expected, actual):
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                            expected=expected, actual=actual)
    contract, _, _, parent_contract = _contracts()
    error.diagnostic.update({'validator': LABEL, 'unionTag': parent_contract['dispatcher']['unionTag'],
                             'nativeInputs': contract['nativeInputs']})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, string_native: dict[str, Any]) -> dict[str, Any]:
    contract, source, shared, parent_contract = _contracts()
    expected = contract['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': expected}
    if (string_native.get('status') != 'validated' or string_native.get('nativeInputs') != expected
            or string_native.get('selectedReadOrder') != list(strings.READ_ORDER)):
        _fail('shared-child-gate', {'status': 'validated', 'readOrder': list(strings.READ_ORDER)},
              {'status': string_native.get('status'), 'readOrder': string_native.get('selectedReadOrder')})
    parent_native = parent.validate_current_native_contract()
    if parent_native.get('status') != 'validated' or parent_native.get('nativeInputs') != expected:
        _fail('parent-gate', expected, parent_native)
    image = open_native_image(gate.gameassembly, gate.metadata)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    tag = parent_contract['dispatcher']['unionTag']; route = routes.get(tag)
    own_setters = parent_contract['setterMethods']
    wanted_types = ['string', contract['listTypeName'], own_setters[2][2], own_setters[3][2]]
    if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != parent_contract['dispatcher']['wrapperName']
            or route.inherited_member_count != 4 or list(route.member_order) != list(parent.FIELD_NAMES)
            or list(route.member_declared_types[4:]) != wanted_types
            or list(zip(route.member_kinds[:4], route.member_widths[:4], strict=True))
            != [('bool', 1), ('enum', 4), ('scalar32', 4), ('scalar32', 4)]):
        _fail('parent-members', {'names': list(parent.FIELD_NAMES), 'ownTypes': wanted_types},
              None if route is None else {'names': list(route.member_order), 'ownTypes': list(route.member_declared_types[4:])})
    context = source['nestedContexts'][0]
    instance = image.instantiations.resolve(context['methodSpec'][2])
    actual_list = runtime_type_name(image.pe, image.metadata, instance.arguments[0].type_pointer_va)
    if actual_list != contract['listTypeName'] or route.member_declared_types[5] != actual_list:
        _fail('typed-list-element', contract['listTypeName'],
              {'contextType': actual_list, 'parentFieldType': route.member_declared_types[5]})
    wrapper = contract['childWrapper']
    image.check_wrapper_inheritance(wrapper, label=LABEL)
    derived = derive_from_image(image)[wrapper['typeDefinition']]
    if (derived.wrapped_type != contract['childTypeName'] or derived.serialized_member_count != 3
            or [row.name for row in derived.members] != list(strings.READ_ORDER)
            or [row.declared_type for row in derived.members] != ['string', 'bool', 'string']
            or derived.parent_type_definition != shared['wrapper']['typeDefinition']):
        _fail('child-inherited-members', {'type': contract['childTypeName'], 'names': list(strings.READ_ORDER)}, derived.row())
    child_methods = [row for row in source['methods'] if row[1] == wrapper['typeName']]
    if len(child_methods) != 1:
        _fail('child-reader', 'one reviewed child reader', child_methods)
    reader = child_methods[0]
    normal = next(row for row in source['codeWindows'] if row['startRva'] == reader[3])
    for row in source['methods']:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(source['codeWindows'], label=LABEL)
    previous = normal['startRva']
    for row, shared_read, setter in zip(contract['sourceReads'], shared['sourceReads'], shared['wrapper']['setterMethods'], strict=True):
        read = row['sourceCall']; write = row['setterCall']; argument = row['sourceResultArgument']
        if (not previous <= read['rva'] < argument[0] < write['rva'] < normal['endRva']
                or read['targetRva'] != shared_read['sourceCall']['targetRva']
                or row['setterMethodIndex'] != setter['methodIndex']
                or image.method_pointer_va(image.metadata.methods[setter['methodIndex']])
                != image.pe.image_base + write['targetRva']):
            _fail('source-setter-order', {'field': row['fieldName'], 'setter': setter['methodIndex']}, row)
        strings._call(image, read); strings._call(image, write)
        image.check_instruction_windows([argument], label=LABEL)
        previous = write['rva'] + 5
    return {'status': 'validated', 'nativeInputs': expected, 'unionTag': tag,
            'memberNames': list(route.member_order), 'childTypeName': contract['childTypeName'],
            'listTypeName': contract['listTypeName'], 'childReadOrder': list(strings.READ_ORDER)}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
                  native_validation: dict[str, Any]) -> dict[str, Any]:
    contract, _, _, parent_contract = _contracts()
    children = native_validation['children']; native = children['advancedBuffIds']
    tag = parent_contract['dispatcher']['unionTag']
    if (native.get('status') != 'validated' or native.get('nativeInputs') != contract['nativeInputs']
            or native.get('unionTag') != tag or native.get('memberNames') != list(parent.FIELD_NAMES)
            or native.get('childTypeName') != contract['childTypeName']
            or native.get('listTypeName') != contract['listTypeName']
            or native.get('childReadOrder') != list(strings.READ_ORDER)
            or children['blackboardString'].get('status') != 'validated'
            or children['blackboardString'].get('selectedReadOrder') != list(strings.READ_ORDER)
            or children['blackboardString'].get('nativeInputs') != native['nativeInputs']
            or children['findSettings'].get('status') != 'validated'
            or children['findSettings'].get('nativeInputs') != native['nativeInputs']
            or not source or not isinstance(data, bytes) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.action:native-or-source')
    reader = Reader(data, source, end); reader.pos = start
    reader.nested_union_tag((tag,), 'advanced-buff-id-action'); reader.header(len(parent.FIELD_NAMES))
    fields = []
    for name, kind in zip(parent.FIELD_NAMES, parent.READ_KINDS, strict=True):
        a = reader.pos; value = {}
        if kind in ('bool-byte', 'scalar32'):
            value['rawHex'] = reader.take(1 if kind == 'bool-byte' else 4, name).hex().upper()
        elif kind == 'byte-payload':
            reader.byte_payload(); value['rawHex'] = data[a:reader.pos].hex().upper()
        elif name == 'buffIdList':
            count = reader.count(1, reserve=5, nullable=True); elements = []
            for _ in range(max(0, count)):
                begin = reader.pos; reader.paired_payload()
                child = strings.decode_blackboard_string_value(
                    data, source=source, logical_sha256=digest, start=begin, end=reader.pos,
                    native_validation=children['blackboardString'])
                if child.get('wholeStoredSpanExact') is not True:
                    raise ValueError(f'{LABEL}.list:child-incomplete')
                elements.append({'typeName': contract['childTypeName'], **child})
            value['child'] = {'start': a, 'end': reader.pos, 'count': count, 'elements': elements,
                              'wholeStoredSpanExact': True, 'recursiveNamedSchemaExact': True}
        elif name == 'query':
            reader.query_profile()
            value['child'] = query.decode_query_value(data, source=source, digest=digest, start=a,
                                                      end=reader.pos, native=children['findSettings'])
        else:
            raise ValueError(f'{LABEL}.action:unsupported-member={name}')
        fields.append({'fieldName': name, 'kind': kind, 'start': a, 'end': reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.action:end={reader.pos}; expected={end}')
    return {'namedFields': fields, 'recursiveStoredSchemaExact': True}
