"""Source-bound target/mask condition storage with independent recursive children.

The two six-member parents keep their distinct source order. Raw mask bits and
complete stored objects do not establish a live predicate or selected target.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import stored_plan_values as stored
from scripts.game_data.memorypack.source_bound_stored_tree import bind_source_named_tree

LABEL = 'buffTargetMaskConditions'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_target_mask_conditions_native.json'
CHILDREN = ('target', 'direction', 'selector', 'directionTargets')
WIDTHS = {'byte': 1, 'scalar32': 4}
COMMON = [('isEnable', 'byte'), ('priorityLevel', 'scalar32'),
          ('priorityOffset', 'scalar32'), ('serverActionIndex', 'scalar32')]


def _contract():
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-target-mask-conditions-native-contract.v1',
        status='exact-current-build', label=LABEL)
    suffixes = {'checkWeaponType': [('checkTarget', 'target-profile'), ('weaponTypes', 'scalar32')],
                'checkEnemyRank': [('enemyRankSet', 'scalar32'), ('target', 'target')]}
    if (set(value.get('records', {})) != set(suffixes)
            or len(value.get('actionDispatch', {})) != len(suffixes)
            or set(value['actionDispatch'].values()) != set(suffixes)
            or value.get('childType') != 'Beyond.Gameplay.Core.TargetSettings'):
        raise ValueError(f'{LABEL}.contract:shape')
    for key, record in value['records'].items():
        if (record.get('inheritedMemberCount') != 4
                or [(m['fieldName'], m['kind']) for m in record['members']] != COMMON + suffixes[key]
                or any(m['kind'] in ('target', 'target-profile') and
                       (m['declaredType'] != value['childType'] or m.get('sourceContextInstructionRva') is None)
                       for m in record['members'])):
            raise ValueError(f'{LABEL}.contract:ordered-target-and-mask={key}')
    return value


def supported_tags():
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(contract):
    return {key: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in record['members']]
            for key, record in contract['records'].items()}


def _fail(check, expected, actual, *, record='', field=''):
    contract = _contract()
    source = CONTRACTS_DIR / (contract['records'][record]['sourceContract'] if record else CONTRACT_PATH.name)
    error = CensusGateError(f'{LABEL}.{check}', source=source.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract['nativeInputs'])
    raise error


def _target_definition(contract, children):
    for key in CHILDREN:
        child = children.get(key, {})
        if child.get('status') != 'validated' or child.get('nativeInputs') != contract['nativeInputs']:
            raise ValueError(f'{LABEL}.native:child-build={key}')
    target = children['target']; registry = target.get('_registry'); definition = target.get('targetDefinition')
    if registry is None or registry.wrapped_names.get(definition) != contract['childType']:
        raise ValueError(f'{LABEL}.native:independent-target-wrapper')
    return definition


def _bindings(contract, definition, runtime_definition):
    bindings = {}
    for key, record in contract['records'].items():
        source = json.loads((CONTRACTS_DIR / record['sourceContract']).read_bytes())
        member = next(m for m in record['members'] if m['kind'] in ('target', 'target-profile'))
        contexts = [c for c in source['nestedContexts'] if c['instructionRva'] == member['sourceContextInstructionRva']]
        if (len(contexts) != 1 or contexts[0]['typeDefinition'] != runtime_definition
                or contexts[0]['typeName'] != member['declaredType'] or member['declaredType'] != contract['childType']):
            _fail('parent-target-context', contract['childType'], contexts, record=key, field=member['fieldName'])
        bindings[key] = {'fieldName': member['fieldName'], 'kind': member['kind'], 'sourceContext': contexts[0],
            'targetWrapperDefinition': definition, 'runtimeTargetDefinition': runtime_definition}
    return bindings


def validate_current_native_contract(*, children: dict[str, Any],
                                    gameassembly: Path | None = None, metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    definition = _target_definition(contract, children)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', pins['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    fields = [f for f in image.metadata.fields_for(image.metadata.types[definition])
              if image.metadata.string(f.name_index) == '__instance']
    if len(fields) != 1:
        _fail('target-wrapper-instance', 'one __instance field', len(fields))
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + fields[0].type_index * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    runtime_definition = int.from_bytes(raw[:8], 'little')
    if raw[10:12] != b'\x12\x00' or image.type_name(runtime_definition) != contract['childType']:
        _fail('target-wrapper-runtime-class', contract['childType'], raw.hex().upper())
    proved = {}; audits = {}
    for key, record in contract['records'].items():
        path = CONTRACTS_DIR / record['sourceContract']; source = json.loads(path.read_bytes())
        audits[key] = buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        proved.update(named.validate_named_records(image, source, {key: record}, label=LABEL, fail=_fail))
    bindings = _bindings(contract, definition, runtime_definition)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract['actionDispatch'].items():
        record = contract['records'][key]; route = routes.get(int(tag))
        if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
                or route.wrapper_name != record['wrapperTypeName']
                or list(route.member_order) != [m['fieldName'] for m in record['members']]
                or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
            _fail('dispatcher-members', record['wrapperTypeName'], None if route is None else route.row(), record=key)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', pins['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': contract['actionDispatch'], 'targetDefinition': definition,
        'runtimeTargetDefinition': runtime_definition, 'parentTargetBindings': bindings,
        'sourceAudits': audits, 'evidenceBoundary': contract['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder=None, depth: int = 0):
    contract = _contract(); children = native_validation.get('children', {})
    packet = children.get('targetMaskConditions', {})
    if (native_validation.get('status') != 'validated' or packet.get('status') != 'validated'
            or native_validation.get('nativeInputs') != contract['nativeInputs']
            or packet.get('nativeInputs') != contract['nativeInputs']
            or packet.get('recordMembers') != _members(contract) or packet.get('actionDispatch') != contract['actionDispatch']
            or type(tag) is not int or str(tag) not in contract['actionDispatch']
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}.decode:depth-limit')
    definition = _target_definition(contract, children)
    if (definition != packet.get('targetDefinition') or _bindings(contract, definition,
            packet.get('runtimeTargetDefinition')) != packet.get('parentTargetBindings')):
        raise ValueError(f'{LABEL}.decode:parent-target-binding-drift')
    prefix = bytes((tag,)) if tag < 250 else b'\xfa' + struct.pack('<H', tag)
    if data[start:start + len(prefix)] != prefix:
        raise ValueError(f'{LABEL}.decode:physical-union-tag')
    record = contract['records'][contract['actionDispatch'][str(tag)]]
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'target-mask-condition') != tag:
        raise ValueError(f'{LABEL}.decode:unexpected-null-union')
    null = reader.peek() == 255; fields = []
    if null:
        reader.take(1, 'null-condition-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin = reader.pos; kind = member['kind']; child = None; binding = None
            if kind in WIDTHS:
                tree = stored.fixed_node(reader.take(WIDTHS[kind], member['fieldName']))
            else:
                reader.target_profile()
                if data[begin:reader.pos] == b'\xff':
                    child = {'start': begin, 'end': reader.pos, 'status': 'exact-null', 'recursiveStoredSchemaExact': True}
                    tree = stored.object_node([], null=True)
                else:
                    if not callable(target_decoder):
                        raise ValueError(f'{LABEL}.decode:independent-target-required')
                    child = target_decoder(data, source, digest,
                        {'fieldName': member['fieldName'], 'start': begin, 'end': reader.pos}, children, depth=depth)
                    tree = stored.decode_stored_plan(data, source=source, digest=digest, start=begin, end=reader.pos,
                        definition=definition, registry=children['target']['_registry'])['storedTree']
                if child.get('recursiveStoredSchemaExact') is not True or (child.get('start'), child.get('end')) != (begin, reader.pos):
                    raise ValueError(f'{LABEL}.decode:incomplete-target-or-span')
                binding = bind_source_named_tree(child, tree)
            if stored.encode_stored_node(tree) != data[begin:reader.pos]:
                raise ValueError(f'{LABEL}.decode:field-reencode')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'], 'kind': kind,
                'start': begin, 'end': reader.pos, 'storedValue': tree, 'nativeChildReceipt': child, 'sourceTreeBinding': binding})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:required-action-end expected={end} actual={reader.pos}')
    receipt = {'schema': 'endfield.buff-target-mask-condition-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'tag': tag, 'typeName': record['runtimeTypeName'],
        'start': start, 'end': end, 'null': null, 'namedFields': fields,
        'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
    if encode_action(receipt) != data[start:end]:
        raise ValueError(f'{LABEL}.decode:whole-action-reencode')
    return receipt


def encode_action(receipt):
    contract = _contract(); tag = receipt['tag']; fields = receipt['namedFields']
    if type(tag) is not int or str(tag) not in contract['actionDispatch']:
        raise ValueError(f'{LABEL}.encode:current-tag')
    prefix = bytes((tag,)) if tag < 250 else b'\xfa' + struct.pack('<H', tag)
    if receipt.get('null') is True:
        if fields:
            raise ValueError(f'{LABEL}.encode:null-fields')
        return prefix + b'\xff'
    members = contract['records'][contract['actionDispatch'][str(tag)]]['members']
    if [(f['fieldName'], f['kind']) for f in fields] != [(m['fieldName'], m['kind']) for m in members]:
        raise ValueError(f'{LABEL}.encode:every-current-field-required')
    return prefix + bytes((len(members),)) + b''.join(stored.encode_stored_node(f['storedValue']) for f in fields)
