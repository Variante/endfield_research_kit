"""Source-bound AI marker and AI-to-skill-blackboard stored actions.

Double and TargetSettings retain their independent recursive owners. The
GameplayTag width uses an independently checked source proof by reference.
Stored fields do not observe a marker effect or a blackboard conversion.
"""
from __future__ import annotations
import copy
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import stored_plan_values as stored
from scripts.game_data.memorypack.source_bound_stored_tree import bind_source_named_tree
from scripts.game_data.memorypack import buff_adding_cooldown as scalars

LABEL = 'buffAIMarkerBlackboardActions'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_ai_marker_blackboard_actions_native.json'
SCHEMA = 'endfield.buff-ai-marker-blackboard-actions-native-contract.v1'
CHILDREN = ('effectVectors', 'target', 'direction', 'selector', 'directionTargets')
WIDTHS = {'byte': 1, 'scalar32': 4}
COMMON = [('isEnable', 'byte'), ('priorityLevel', 'scalar32'), ('priorityOffset', 'scalar32'), ('serverActionIndex', 'scalar32')]


def _contract():
    value, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (set(value.get('records', {})) != {'addAIMarker', 'saveValueFromAIBlackboard'}
            or value.get('actionDispatch') != {'7': 'addAIMarker', '322': 'saveValueFromAIBlackboard'}
            or set(value.get('childTypes', {})) != {'double', 'target'}
            or len(set(value['childTypes'].values())) != 2):
        raise ValueError(f'{LABEL}.contract:shape')
    for key, record in value['records'].items():
        members = record['members']
        if record['inheritedMemberCount'] != 4 or [(m['fieldName'], m['kind']) for m in members[:4]] != COMMON:
            raise ValueError(f'{LABEL}.contract:inherited-prefix={key}')
        for member in members:
            kind = member['kind']
            if kind in WIDTHS or kind == 'byte-payload':
                continue
            allowed = {'scalar-payload': value['childTypes']['double'],
                       'target': value['childTypes']['target'], 'target-profile': value['childTypes']['target']}
            if kind not in allowed or member['declaredType'] != allowed[kind] or member.get('sourceContextInstructionRva') is None:
                raise ValueError(f'{LABEL}.contract:typed-child={key}.{member["fieldName"]}')
    return value


def supported_tags():
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(contract):
    return {key: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in record['members']]
            for key, record in contract['records'].items()}


def _contract_file(name):
    if not isinstance(name, str) or Path(name).name != name or not name.endswith('.json'):
        raise ValueError(f'{LABEL}.native:contract-basename-required')
    return CONTRACTS_DIR / name


def _source_record(contract, record):
    """Resolve reviewed dependencies without copying their catalog into ours."""
    path = _contract_file(record['sourceContract'])
    source = json.loads(path.read_bytes()); resolved = copy.deepcopy(record)
    for member in resolved['members']:
        reference = member.get('unmanagedSourceRef')
        if reference is None:
            continue
        owner = json.loads(_contract_file(reference['contract']).read_bytes())
        if owner.get('nativeInputs') != contract['nativeInputs']:
            raise ValueError(f'{LABEL}.native:unmanaged-owner-build={member["fieldName"]}')
        selected = [m for m in owner['records'][reference['record']]['members'] if m['fieldName'] == reference['field']]
        if (len(selected) != 1 or selected[0]['declaredType'] != member['declaredType']
                or selected[0]['kind'] != member['kind'] or not isinstance(selected[0].get('unmanagedSource'), dict)):
            raise ValueError(f'{LABEL}.native:unmanaged-owner-field={member["fieldName"]}')
        proof = selected[0]['unmanagedSource']
        if proof['windowStartRva'] != member['sourceCall']['targetRva'] or proof['width'] != WIDTHS.get(member['kind']):
            raise ValueError(f'{LABEL}.native:unmanaged-source-call={member["fieldName"]}')
        helper = json.loads(_contract_file(reference['helperWindowContract']).read_bytes())
        windows = [w for w in helper['codeWindows'] if w['startRva'] == proof['windowStartRva']]
        if len(windows) != 1:
            raise ValueError(f'{LABEL}.native:unique-unmanaged-helper-window={member["fieldName"]}')
        member['unmanagedSource'] = copy.deepcopy(proof)
        source = {**source, 'codeWindows': [*source['codeWindows'], *windows]}
    return path, source, resolved


def _definitions(contract, children):
    for key in CHILDREN:
        packet = children.get(key, {})
        if packet.get('status') != 'validated' or packet.get('nativeInputs') != contract['nativeInputs']:
            raise ValueError(f'{LABEL}.native:child-build={key}')
    scalar = children['effectVectors'].get('scalarNative', {})
    if (scalar.get('status') != 'validated'
            or scalar.get('selectedReadOrder') != ['blackboardKey', 'useBlackboardKey', 'value']):
        raise ValueError(f'{LABEL}.native:independent-child-source-order')
    registry = children['target'].get('_registry')
    if registry is None:
        raise ValueError(f'{LABEL}.native:source-bound-registry-required')
    definitions = {}
    for key, name in contract['childTypes'].items():
        found = [definition for definition, wrapped in registry.wrapped_names.items()
                 if wrapped == name and definition in registry.plans]
        if len(found) != 1:
            raise ValueError(f'{LABEL}.native:unique-child-wrapper={key}')
        definitions[key] = found[0]
    if definitions['target'] != children['target'].get('targetDefinition'):
        raise ValueError(f'{LABEL}.native:target-definition')
    return definitions


def _runtime_definitions(image, definitions):
    double_contract = scalars._contract()
    double_source = json.loads(scalars.ROOT_CONTRACT_PATH.read_bytes())
    double = double_source['nestedContexts'][double_contract['rootContextIndex']]
    target_fields = [field for field in image.metadata.fields_for(image.metadata.types[definitions['target']])
                     if image.metadata.string(field.name_index) == '__instance']
    if len(target_fields) != 1:
        raise ValueError(f'{LABEL}.native:target-wrapper-instance')
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + target_fields[0].type_index * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if raw[10:12] != b'\x12\x00':
        raise ValueError(f'{LABEL}.native:target-runtime-class')
    return {'double': double['typeDefinition'], 'target': int.from_bytes(raw[:8], 'little')}


def _bindings(contract, runtime):
    if (not isinstance(runtime, dict) or set(runtime) != set(contract['childTypes'])
            or any(type(value) is not int or value < 0 for value in runtime.values())):
        raise ValueError(f'{LABEL}.native:complete-child-runtime-identities-required')
    result = {}
    for key, record in contract['records'].items():
        source = json.loads(_contract_file(record['sourceContract']).read_bytes()); fields = {}
        for member in record['members']:
            if member['kind'] in WIDTHS or member['kind'] == 'byte-payload':
                continue
            child = next(name for name, declared in contract['childTypes'].items() if declared == member['declaredType'])
            selected = [context for context in source['nestedContexts']
                        if context['instructionRva'] == member['sourceContextInstructionRva']]
            if (len(selected) != 1 or selected[0]['typeDefinition'] != runtime[child]
                    or selected[0]['typeName'] != member['declaredType']):
                raise ValueError(f'{LABEL}.native:parent-closed-child-context={key}.{member["fieldName"]}')
            fields[member['fieldName']] = {'child': child, 'context': selected[0]}
        result[key] = fields
    return result


def validate_current_native_contract(*, children: dict[str, Any], gameassembly: Path | None = None,
                                    metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    definitions = _definitions(contract, children)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        raise ValueError(f'{LABEL}.native:UnityPlayer.dll')
    image = open_native_image(gate.gameassembly, gate.metadata)
    runtime = _runtime_definitions(image, definitions)
    for key, definition in runtime.items():
        if image.type_name(definition) != contract['childTypes'][key]:
            raise ValueError(f'{LABEL}.native:independently-owned-child-type={key}')
    proved = {}; audits = {}
    def fail(check, expected, actual, **details):
        raise ValueError(f'{LABEL}.native:{check}:expected={str(expected)[:900]},actual={str(actual)[:900]},details={details}')
    for key, record in contract['records'].items():
        path, source, resolved = _source_record(contract, record)
        audits[key] = buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
                                           image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        proved.update(named.validate_named_records(image, source, {key: resolved}, label=LABEL, fail=fail))
    bindings = _bindings(contract, runtime)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract['actionDispatch'].items():
        record = contract['records'][key]; route = routes.get(int(tag))
        if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
                or route.wrapper_name != record['wrapperTypeName']
                or list(route.member_order) != [m['fieldName'] for m in record['members']]
                or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
            raise ValueError(f'{LABEL}.native:current-dispatcher={key}')
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        raise ValueError(f'{LABEL}.native:UnityPlayer.dll-after')
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved, 'actionDispatch': contract['actionDispatch'],
            'childDefinitions': definitions, 'childRuntimeDefinitions': runtime, 'parentChildBindings': bindings,
            'sourceAudits': audits, 'evidenceBoundary': contract['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], depth: int = 0, target_decoder=None):
    contract = _contract(); children = native_validation.get('children', {}); packet = children.get('aiMarkerBlackboard', {})
    if (native_validation.get('status') != 'validated' or packet.get('status') != 'validated'
            or native_validation.get('nativeInputs') != contract['nativeInputs'] or packet.get('nativeInputs') != contract['nativeInputs']
            or packet.get('recordMembers') != _members(contract) or packet.get('actionDispatch') != contract['actionDispatch']
            or type(tag) is not int or str(tag) not in contract['actionDispatch']
            or not isinstance(data, bytes) or not isinstance(source, str) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}.decode:depth-limit')
    definitions = _definitions(contract, children)
    if (definitions != packet.get('childDefinitions')
            or _bindings(contract, packet.get('childRuntimeDefinitions', {})) != packet.get('parentChildBindings')):
        raise ValueError(f'{LABEL}.decode:parent-child-binding-drift')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'ai-marker-blackboard') != tag:
        raise ValueError(f'{LABEL}.decode:physical-union-tag')
    tag_width = reader.pos - start
    key = contract['actionDispatch'][str(tag)]; record = contract['records'][key]
    null = reader.peek() == 255; fields = []
    if null:
        reader.take(1, 'null-parent-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin = reader.pos; kind = member['kind']; child = None; binding = None
            if kind in WIDTHS:
                tree = stored.fixed_node(reader.take(WIDTHS[kind], member['fieldName']))
            elif kind == 'byte-payload':
                reader.byte_payload(); count = struct.unpack_from('<i', data, begin)[0]; raw = data[begin + 4:reader.pos]
                try:
                    value = None if count == -1 else raw.decode('utf-8', 'strict'); valid = True
                except UnicodeDecodeError:
                    value, valid = None, False
                tree = {'kind': 'string', 'byteLength': count, 'payloadHex': raw.hex().upper(), 'utf8Valid': valid, 'utf8Value': value}
            else:
                child_key = packet['parentChildBindings'][key][member['fieldName']]['child']
                if kind == 'scalar-payload':
                    reader.scalar_payload()
                    scalar = scalars.decode_adding_cooldown(data, begin, reader.pos,
                                                           native_validation=children['effectVectors']['scalarNative'])
                    child = {**scalar, 'start': scalar['startOffset'], 'end': scalar['consumedEnd'],
                             'recursiveStoredSchemaExact': scalar.get('wholeValueExact') is True}
                else:
                    reader.target_profile()
                    if data[begin:reader.pos] == b'\xff':
                        child = {'start': begin, 'end': reader.pos, 'status': 'exact-null', 'recursiveStoredSchemaExact': True}
                    else:
                        if not callable(target_decoder):
                            raise ValueError(f'{LABEL}.decode:independent-target-required')
                        child = target_decoder(data, source, digest, {'fieldName': member['fieldName'], 'start': begin, 'end': reader.pos},
                                               children, depth=depth)
                if child.get('recursiveStoredSchemaExact') is not True or (child.get('start'), child.get('end')) != (begin, reader.pos):
                    raise ValueError(f'{LABEL}.decode:incomplete-child-or-span={member["fieldName"]}')
                tree = stored.decode_stored_plan(data, source=source, digest=digest, start=begin, end=reader.pos,
                    definition=definitions[child_key], registry=children['target']['_registry'])['storedTree']
                binding = bind_source_named_tree(child, tree)
            if stored.encode_stored_node(tree) != data[begin:reader.pos]:
                raise ValueError(f'{LABEL}.decode:field-reencode={member["fieldName"]}')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'], 'kind': kind,
                           'start': begin, 'end': reader.pos, 'storedValue': tree, 'nativeChildReceipt': child, 'sourceTreeBinding': binding})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:required-parent-end expected={end} actual={reader.pos}')
    receipt = {'schema': 'endfield.buff-ai-marker-blackboard-action-receipt.v1', 'source': source, 'logicalSha256': digest.upper(),
               'tag': tag, 'tagWidth': tag_width, 'typeName': record['runtimeTypeName'], 'start': start, 'end': end,
               'null': null, 'namedFields': fields, 'recursiveStoredSchemaExact': True,
               'runtimeMeaningExact': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
    if encode_action(receipt) != data[start:end]:
        raise ValueError(f'{LABEL}.decode:whole-parent-reencode')
    return receipt


def encode_action(receipt):
    contract = _contract(); tag = receipt['tag']; fields = receipt['namedFields']; width = receipt['tagWidth']
    if (type(tag) is not int or str(tag) not in contract['actionDispatch'] or type(width) is not int
            or width not in (1, 3) or width == 1 and tag >= 250):
        raise ValueError(f'{LABEL}.encode:current-tag-or-width')
    prefix = bytes((tag,)) if width == 1 else b'\xfa' + struct.pack('<H', tag)
    if receipt.get('null') is True:
        if fields:
            raise ValueError(f'{LABEL}.encode:null-fields')
        return prefix + b'\xff'
    members = contract['records'][contract['actionDispatch'][str(tag)]]['members']
    if [(f['fieldName'], f['kind']) for f in fields] != [(m['fieldName'], m['kind']) for m in members]:
        raise ValueError(f'{LABEL}.encode:every-current-field-required')
    return prefix + bytes((len(members),)) + b''.join(stored.encode_stored_node(f['storedValue']) for f in fields)
