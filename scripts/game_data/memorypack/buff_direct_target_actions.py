"""Shared adapter for reviewed direct fields plus one TargetSettings."""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named

LABEL = 'buffDirectTargetActions'
SCHEMA = 'endfield.buff-direct-target-action-receipt.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_direct_target_actions_native.json'
_KINDS = {'byte': 'byte', 'scalar32': 'raw4', 'bytePayload': 'payload',
          'target': 'target', 'target-profile': 'target'}


def _contracts():
    contract = json.loads(CONTRACT_PATH.read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract['catalogContract']).read_bytes())
    expected = {'GameAssembly.dll': catalog['nativeInputs']['gameAssemblySha256'],
                'global-metadata.dat': catalog['nativeInputs']['metadataSha256']}
    if (contract.get('schema') != 'endfield.buff-direct-target-actions-native-contract.v2'
            or contract.get('status') != 'exact-current-build'
            or set(contract.get('nativeInputs', {})) != set(expected) | {'UnityPlayer.dll'}
            or any(contract['nativeInputs'].get(name) != value for name, value in expected.items())
            or set(contract.get('namedRecords', {})) != {'forceHideHeadBar', 'recoverFromPoiseBreak'}):
        raise ValueError(f'{LABEL}.contract:shape-or-inputs')
    seen = set()
    for spec in contract['routes']:
        tag = spec['unionTag']; reviewed = catalog['families']['AbilityActionData'][tag]
        source = json.loads((CONTRACTS_DIR / spec['sourceContract']).read_bytes())
        kinds = source['anonymousReadOrder'][spec['sourceReadOrder']]
        if (type(tag) is not int or tag in seen or reviewed['tag'] != tag
                or reviewed['wrappedType'] != spec['wrappedType'] or reviewed['memberCount'] != len(kinds)
                or source.get('schemaVersion') != 1 or any(k not in _KINDS for k in kinds)
                or [i for i, k in enumerate(kinds) if _KINDS[k] == 'target'] != [spec['targetFieldIndex']]
                or len(spec['sourceContextIndices']) != len(spec['contextMemberIndices'])):
            raise ValueError(f'{LABEL}.contract:route={tag}')
        seen.add(tag)
        if 'namedRecord' in spec:
            record = contract['namedRecords'][spec['namedRecord']]
            if (record['sourceContract'] != spec['sourceContract']
                    or record['sourceReadOrder'] != spec['sourceReadOrder']
                    or record['runtimeTypeName'] != spec['wrappedType']
                    or [m['kind'] for m in record['members']] != kinds
                    or record['members'][spec['targetFieldIndex']]['fieldName'] != spec['targetFieldName']
                    or record['members'][spec['targetFieldIndex']]['declaredType'] != 'Beyond.Gameplay.Core.TargetSettings'):
                raise ValueError(f'{LABEL}.contract:named-route={tag}')
    if {spec.get('namedRecord') for spec in contract['routes'] if 'namedRecord' in spec} != set(contract['namedRecords']):
        raise ValueError(f'{LABEL}.contract:named-route-set')
    return contract, catalog


def supported_tags():
    return frozenset(row['unionTag'] for row in _contracts()[0]['routes'])


def _fail(check, *, tag, source, expected, actual, record='', field=''):
    error = CensusGateError(f'{LABEL}.{check}', source=source, expected=expected, actual=actual)
    error.diagnostic.update(unionTag=tag, validator=LABEL, record=record, field=field)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract():
    contract, catalog = _contracts(); expected = contract['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'check': 'native-inputs', 'nativeInputs': expected}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if 'UnityPlayer.dll' in expected:
        actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else 'missing'
        if actual != expected['UnityPlayer.dll']:
            _fail('UnityPlayer.dll', tag=None, source=CONTRACT_PATH.as_posix(), expected=expected['UnityPlayer.dll'], actual=actual)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if (audit.get('status') != 'validated' or any(str(audit.get('nativeInputs', {}).get(k, '')).upper() != expected[k]
                                                for k in ('GameAssembly.dll', 'global-metadata.dat'))):
        _fail('dispatcher-native-inputs', tag=None, source=CONTRACT_PATH.as_posix(), expected=expected,
              actual={'status': audit.get('status'), 'nativeInputs': audit.get('nativeInputs')})
    image = open_native_image(gate.gameassembly, gate.metadata); proved = {}
    for spec in contract['routes']:
        tag = spec['unionTag']; path = CONTRACTS_DIR / spec['sourceContract']
        source = json.loads(path.read_bytes()); kinds = source['anonymousReadOrder'][spec['sourceReadOrder']]
        route = routes.get(tag); reviewed = catalog['families']['AbilityActionData'][tag]
        fail = lambda check, wanted, actual: _fail(check, tag=tag, source=path.as_posix(), expected=wanted, actual=actual)
        if (route is None or route.status != 'resolved' or route.wrapper_name != reviewed['wrapperName']
                or route.inherited_member_count != 4 or len(route.member_order) != len(kinds)):
            fail('dispatcher-wrapper', {'wrapper': reviewed['wrapperName'], 'members': len(kinds)},
                 None if route is None else {'status': route.status, 'wrapper': route.wrapper_name})
        selected_contexts = [source['nestedContexts'][i] for i in spec['sourceContextIndices']]
        expected_types = [route.member_declared_types[i] for i in spec['contextMemberIndices']]
        actual_types = [row['typeName'] for row in selected_contexts]
        if expected_types != actual_types:
            fail('typed-source-contexts', expected_types, actual_types)
        for index, (kind, actual, width) in enumerate(zip(kinds, route.member_kinds, route.member_widths, strict=True)):
            primitive = _KINDS[kind]
            valid = ((primitive == 'byte' and actual == 'bool' and width == 1)
                     or (primitive == 'raw4' and actual in ('enum', 'scalar32', 'float32') and width == 4)
                     or (primitive == 'payload' and actual == 'string')
                     or (primitive == 'target' and actual == 'object'))
            if not valid:
                fail('source-field-kind', {'index': index, 'sourceKind': kind}, {'kind': actual, 'width': width})
        target_index = spec['targetFieldIndex']
        if (route.member_order[target_index] != spec['targetFieldName']
                or route.member_declared_types[target_index] != 'Beyond.Gameplay.Core.TargetSettings'):
            fail('target-parent-field', [spec['targetFieldName'], 'Beyond.Gameplay.Core.TargetSettings'],
                 [route.member_order[target_index], route.member_declared_types[target_index]])
        for row in source['methods']:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(source['codeWindows'], label=LABEL)
        bodies = [row for row in source['methods'] if row[1] == reviewed['wrapperName'] and row[2] == 'Deserialize']
        if len(bodies) != 1:
            fail('parent-source-reader', 'one exact generated source reader', bodies)
        normal = next(row for row in source['codeWindows'] if row['startRva'] == bodies[0][3])
        for context in selected_contexts:
            if not normal['startRva'] <= context['instructionRva'] < normal['endRva']:
                fail('parent-context-range', [normal['startRva'], normal['endRva']], context['instructionRva'])
            cell, usage = image.nested_usage_cell(context, label=LABEL)
            index = method_spec_usage_index(usage, image.registration['methodSpecsCount'], source=str(image.gameassembly), offset=cell)
            if index != context['methodSpecIndex']:
                fail('method-spec-index', context['methodSpecIndex'], index)
            spec_value = struct.unpack('<iii', image.pe.bytes_at_va(int(image.registration['methodSpecs'], 16) + index * 12, 12))
            instance = image.instantiations.resolve(spec_value[2])
            actual = {'methodSpec': list(spec_value), 'typeName': image.type_name(context['typeDefinition']),
                      'argumentRawHex': [a.raw_type_record_hex for a in instance.arguments]}
            wanted = {'methodSpec': context['methodSpec'], 'typeName': context['typeName'],
                      'argumentRawHex': [context['argumentRawHex']]}
            if actual != wanted:
                fail('method-spec-type', wanted, actual)
        named_members = None
        if 'namedRecord' in spec:
            key = spec['namedRecord']; record = contract['namedRecords'][key]
            if (route.wrapper_name != record['wrapperTypeName']
                    or list(route.member_order) != [m['fieldName'] for m in record['members']]
                    or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
                fail('named-dispatcher-members', record['runtimeTypeName'], list(route.member_order))
            buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
                image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
            def named_fail(check, wanted, actual, *, record='', field=''):
                _fail(check, tag=tag, source=path.as_posix(), expected=str(wanted)[:1024],
                    actual=str(actual)[:1024], record=record, field=field)
            named_members = named.validate_named_records(image, source, {key:record},
                label=LABEL, fail=named_fail)[key]
        proved[tag] = {'status': 'validated', 'nativeInputs': expected, 'unionTag': tag,
                       'memberCount': len(kinds), 'memberNames': list(route.member_order), 'readKinds': kinds,
                       'typeName': reviewed['wrappedType'], 'targetBinding': {'fieldName': spec['targetFieldName'],
                       'index': target_index, 'declaredType': 'Beyond.Gameplay.Core.TargetSettings', 'kind': kinds[target_index]}}
        if named_members is not None:
            proved[tag].update(sourceRecord=spec['namedRecord'], recordMembers=named_members)
    after = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'check':'native-inputs-after', 'nativeInputs':expected}
    if 'UnityPlayer.dll' in expected and hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', tag=None, source=CONTRACT_PATH.as_posix(), expected=expected['UnityPlayer.dll'], actual='mismatched')
    return {'status': 'validated', 'nativeInputs': expected, 'routes': proved}


def decode_action(data, *, source, logical_sha256, start, end, tag, native_validation):
    contract, catalog = _contracts(); specs = [r for r in contract['routes'] if r['unionTag'] == tag]
    if len(specs) != 1:
        raise ValueError(f'{LABEL}:unsupported-tag={tag}')
    spec = specs[0]; native = native_validation
    source_contract = json.loads((CONTRACTS_DIR / spec['sourceContract']).read_bytes())
    kinds = source_contract['anonymousReadOrder'][spec['sourceReadOrder']]
    binding = {'fieldName': spec['targetFieldName'], 'index': spec['targetFieldIndex'],
               'declaredType': 'Beyond.Gameplay.Core.TargetSettings', 'kind': kinds[spec['targetFieldIndex']]}
    if 'namedRecord' in spec:
        record = contract['namedRecords'][spec['namedRecord']]
        members = [{'fieldName':m['fieldName'], 'kind':m['kind']} for m in record['members']]
        if (native.get('sourceRecord') != spec['namedRecord'] or native.get('recordMembers') != members
                or native.get('memberNames') != [m['fieldName'] for m in record['members']]):
            raise ValueError(f'{LABEL}:named-native-not-validated')
    if (native.get('status') != 'validated' or native.get('nativeInputs') != contract['nativeInputs']
            or native.get('unionTag') != tag or native.get('memberCount') != len(kinds)
            or native.get('readKinds') != kinds or len(native.get('memberNames', [])) != len(kinds)
            or native.get('typeName') != spec['wrappedType'] or native.get('targetBinding') != binding):
        raise ValueError(f'{LABEL}:native-not-validated')
    if (not source or not isinstance(data, bytes) or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data) or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()):
        raise ValueError(f'{LABEL}:source-range-or-hash')
    reader = Reader(data, source, end); reader.pos = start
    if 'namedRecord' in spec:
        if reader.nested_union_tag((tag,), 'direct-target-action') != tag:
            raise ValueError(f'{LABEL}:physical-tag')
    else:
        tag_bytes = bytes((tag,)) if tag < 0xFA else b'\xfa' + struct.pack('<H', tag)
        if reader.take(len(tag_bytes), 'union-tag') != tag_bytes:
            raise ValueError(f'{LABEL}:physical-tag')
    if 'namedRecord' in spec and reader.peek() == 255:
        reader.take(1, 'null-action-wrapper')
        if reader.pos != end:
            raise ValueError(f'{LABEL}:action-end={reader.pos}; expected={end}')
        return {'schema':SCHEMA, 'source':source, 'logicalSha256':logical_sha256.upper(),
            'tag':tag, 'start':start, 'end':end, 'status':'exact-null-wrapper', 'isNull':True,
            'memberCount':0, 'typeName':native['typeName'], 'namedFields':[],
            'wholeActionByteSpanExact':True, 'recursiveNamedSchemaExact':False, 'wholeBuffDataExact':False}
    reader.header(native['memberCount']); fields = []
    for name, kind in zip(native['memberNames'], kinds, strict=True):
        begin = reader.pos; primitive = _KINDS[kind]
        if primitive == 'target':
            reader.target_profile()
        elif primitive == 'payload':
            reader.byte_payload()
        else:
            reader.take(1 if primitive == 'byte' else 4, kind)
        fields.append({'fieldName': name, 'kind': kind, 'start': begin, 'end': reader.pos,
            **({'rawHex':data[begin:reader.pos].hex().upper()} if primitive in ('byte','raw4') else {})})
    if reader.pos != end:
        raise ValueError(f'{LABEL}:action-end={reader.pos}; expected={end}')
    return {'schema': SCHEMA, 'source': source, 'logicalSha256': logical_sha256.upper(), 'tag': tag,
            'start': start, 'end': end, 'status': 'named-wrapper-exact-span', 'memberCount': len(fields),
            'typeName': native['typeName'], 'namedFields': fields, 'wholeActionByteSpanExact': True,
            'recursiveNamedSchemaExact': False, 'wholeBuffDataExact': False}
