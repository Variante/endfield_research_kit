"""Complete source-bound MoveTo stored records, separate from runtime state.

The caller supplies authenticated selected child returns. Structural metadata
trees are joined to the source-proved recursive receipts, never used alone to
admit a child. Compatible default formatter bindings remain conditions.
"""
from __future__ import annotations

import hashlib
import ast
import argparse
import datetime
import json
import struct
from pathlib import Path
from typing import Any
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.common import check_installed_native_inputs
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_plans import load_registry
from scripts.game_data.memorypack import buff_move_to_source as source_owner
from scripts.game_data.memorypack import buff_move_to_subspeed as subspeed
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vectors
from scripts.game_data.memorypack import stored_plan_values as stored
from scripts.game_data.memorypack import buff_target_settings_child_receipt as targets
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as directions
from scripts.game_data.memorypack import buff_selector_data_child_receipt as selectors
from scripts.game_data.memorypack import buff_direction_target_children as direction_targets
from scripts.game_data.memorypack import buff_selector_fixed_point_finder as fixed_point

LABEL = 'buffMoveTo'
SCHEMA = 'endfield.buff-move-to-stored-receipt.v1'
CONTRACT_PATH = source_owner.CONTRACT_PATH
WIDTHS = {'byte': 1, 'scalar32': 4, 'raw4': 4, 'raw12': 12}
CHILD_READERS = {'scalar-payload': 'scalar_payload', 'byte-payload': 'byte_payload',
    'curve': 'curve_profile', 'vector-payload': 'vector_payload', 'target': 'target_profile',
    'scalar-payload-curve-profile': 'scalar_payload_curve_profile'}
REQUIRED_CHILDREN = ('effectVectors', 'target', 'direction', 'selector',
                     'directionTargets', 'fixedPointFinder')


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1400], actual=str(actual)[:1800])
    error.diagnostic.update(validator=LABEL, check=check)
    raise error


def _record():
    contract = source_owner._contract()
    record = contract['records']['moveTo']
    return contract, record, int(next(iter(contract['actionDispatch'])))


def supported_tags() -> frozenset[int]:
    return frozenset((int(tag) for tag in source_owner._contract()['actionDispatch']))


def compose_native_bindings(contract: dict, record: dict, tag: int, components: dict) -> dict:
    pins = contract['nativeInputs']
    parent, child = components['parentSource'], components['subSpeed']
    if any(packet.get('status') != 'validated' or packet.get('nativeInputs') != pins for packet in (parent, child)):
        _fail('parent-subSpeed-build', pins, [parent.get('status'), child.get('status')])
    for key in ('source', 'lifecycle', 'adapters', 'doubleData', 'curve', 'string'):
        packet = child['components'].get(key, {})
        if packet.get('status') != 'validated' or packet.get('nativeInputs') != pins:
            _fail('subSpeed-component-build', {'component': key, 'nativeInputs': pins}, packet.get('status'))
    expected = [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in record['members']]
    if parent['recordMembers'].get('moveTo') != expected or parent['actionDispatch'] != contract['actionDispatch']:
        _fail('complete-parent-source-order', expected, parent.get('recordMembers'))
    lifecycle = child['components']['lifecycle']['summary']['records']['moveTo']['source']
    lifecycle_programs = subspeed.lifecycle._contract()['records']['moveTo']['programs']
    expected_null_returns = sum(name.startswith('null') for name in lifecycle_programs)
    expected_normal_returns = sum(name.startswith('normal') for name in lifecycle_programs)
    if (lifecycle['memberCount'] != len(expected) or not lifecycle['currentFieldProgramJoined']
            or not lifecycle['nullClearsWrapperReference'] or expected_null_returns < 1 or expected_normal_returns < 1
            or lifecycle['completeNullReturns'] != expected_null_returns
            or lifecycle['completeNormalReturns'] != expected_normal_returns):
        _fail('complete-parent-wrapper-returns', 'complete null and both normal parent returns', lifecycle)
    route = child['components']['adapters']['summary']['records']['moveTo']
    if (route['originalType'] != record['runtimeTypeName'] or route['wrapperType'] != record['wrapperTypeName']
            or not route['staticOriginalAdapterRegistrationProved']
            or not route['typedInterfaceLookup']['completeCallerReturnProved']
            or not route['wrapperReaderRoute']['completeCallerFrameRestoredBeforeTail']):
        _fail('parent-default-original-adapter', record['runtimeTypeName'], route)
    subspeed._validate_decode(child)
    context = components['children']
    for key in ('effectVectors', 'target', 'direction', 'selector', 'directionTargets', 'fixedPointFinder'):
        if context.get(key, {}).get('status') != 'validated' or context[key].get('nativeInputs') != pins:
            _fail('selected-child-build', {'component': key, 'nativeInputs': pins}, context.get(key, {}).get('status'))
    registry = context['target']['_registry']
    bindings = {}
    vector_definition = vectors._contract()['vectorWrapperTypeDefinition']
    kinds = {'scalar-payload': subspeed.DOUBLE_TYPE, 'byte-payload': 'string',
        'curve': 'UnityEngine.AnimationCurve', 'vector-payload': registry.wrapped_names[vector_definition],
        'target': registry.wrapped_names[context['target']['targetDefinition']],
        'scalar-payload-curve-profile': subspeed._record()[1]['runtimeTypeName']}
    for member in record['members']:
        kind = member['kind']
        if kind not in WIDTHS and kinds.get(kind) != member['declaredType']:
            _fail('parent-typed-child', {'kind': kind, 'type': kinds.get(kind)}, member)
        if kind == 'byte-payload' and member['sourceCall']['targetRva'] not in child['components']['string']['sourceHelpers']:
            _fail('parent-actual-string-helper', child['components']['string']['sourceHelpers'], member['sourceCall'])
        if kind == 'vector-payload': bindings[member['fieldName']] = vector_definition
        if kind == 'target': bindings[member['fieldName']] = context['target']['targetDefinition']
    if registry.roots.get(tag) != record['wrapperTypeDefinition']:
        _fail('parent-current-union-wrapper', record['wrapperTypeDefinition'], registry.roots.get(tag))
    return {'unionTag': tag, 'memberCount': len(expected), 'memberNames': [m['fieldName'] for m in record['members']],
        'memberKinds': [m['kind'] for m in record['members']], 'declaredTypes': [m['declaredType'] for m in record['members']],
        'childDefinitions': bindings, 'completeParentWrapperReturnsProved': True,
        'defaultOriginalWrapperAdapterRouteJoined': True, 'storedChildGrammarBindingsProved': True,
        'actualSourceCallbackCursorEqualityProved': False, 'actualProviderSelectionProved': False,
        'finalAccumulatedInstanceStateProved': False}


def _double_tree(receipt: dict) -> dict:
    if receipt['childNull']:
        return stored.object_node([], null=True)
    fields = receipt['fields']
    if [field['fieldName'] for field in fields] != ['blackboardKey', 'useBlackboardKey', 'value']:
        _fail('double-named-fields', 'key, raw Boolean and raw Float32', fields)
    return stored.object_node([
        {'fieldName': fields[0]['fieldName'], 'value': stored.string_node(fields[0]['storedValue'])},
        {'fieldName': fields[1]['fieldName'], 'value': stored.fixed_node(bytes((fields[1]['wireRawByte'],)), scalar='bool')},
        {'fieldName': fields[2]['fieldName'], 'value': stored.fixed_node(bytes.fromhex(fields[2]['rawBitsHex']), scalar='float32')}])


def _curve_tree(receipt: dict) -> dict:
    if receipt['null']:
        return stored.object_node([], null=True)
    fields = receipt['namedFields']
    keys = []
    for key in fields[2]['elements']:
        members = [{'fieldName': field['fieldName'], 'value': stored.fixed_node(bytes.fromhex(field['rawHex']), scalar='float32')}
                   for field in key['namedFields']]
        keys.append({'kind': 'struct', 'memberOrder': [m['fieldName'] for m in members], 'members': members})
    return stored.object_node([
        {'fieldName': fields[0]['fieldName'], 'value': stored.fixed_node(bytes.fromhex(fields[0]['rawHex']))},
        {'fieldName': fields[1]['fieldName'], 'value': stored.fixed_node(bytes.fromhex(fields[1]['rawHex']))},
        {'fieldName': fields[2]['fieldName'], 'value': {'kind': 'list', 'count': receipt['keyCount'], 'elements': keys}}])


def _bind_recursive_tree(receipt: dict, tree: dict) -> int:
    """Every source-named object must match a complete metadata tree object."""
    objects = []
    def nodes(value):
        if isinstance(value, dict):
            if value.get('kind') == 'object' and not value.get('null'): objects.append(value)
            for child in value.values(): nodes(child)
        elif isinstance(value, list):
            for child in value: nodes(child)
    nodes(tree)
    compared = 0
    def receipts(value):
        nonlocal compared
        if isinstance(value, dict):
            fields = next((value.get(key) for key in ('namedMembers', 'namedFields', 'fields')
                           if isinstance(value.get(key), list) and value[key]), None)
            if fields and all(isinstance(field, dict) and ('fieldName' in field or 'name' in field)
                              and 'start' in field and 'end' in field for field in fields):
                expected = [(field.get('fieldName', field.get('name')), field['start'], field['end']) for field in fields]
                matches = [node for node in objects if [(m['fieldName'], m['start'], m['end']) for m in node['members']] == expected]
                if len(matches) != 1: _fail('recursive-source-metadata-field-boundaries', expected, len(matches))
                for field, member in zip(fields, matches[0]['members'], strict=True):
                    node = member['value']
                    if 'rawHex' in field or 'rawBitsHex' in field:
                        raw = field.get('rawHex', field.get('rawBitsHex'))
                        if stored.encode_stored_node(node).hex().upper() != raw.upper():
                            _fail('recursive-source-wire-value', raw, node)
                    if 'rawByte' in field and stored.encode_stored_node(node) != bytes((field['rawByte'],)):
                        _fail('recursive-source-wire-byte', field['rawByte'], node)
                    if 'rawPayloadHex' in field:
                        payload = None if node.get('byteLength') == -1 else node.get('payloadHex')
                        if node.get('kind') != 'string' or payload != field['rawPayloadHex']:
                            _fail('recursive-source-wire-string', field['rawPayloadHex'], node)
                compared += 1
            for child in value.values(): receipts(child)
        elif isinstance(value, list):
            for child in value: receipts(child)
    receipts(receipt)
    if not compared and not tree.get('null'):
        _fail('recursive-named-source-objects', 'at least one matching source-named object', compared)
    return compared


def decode_move_to(data: bytes, *, source: str, digest: str, start: int, end: int,
                   native_validation: dict, target_decoder=None) -> dict:
    contract, record, tag = _record()
    if native_validation.get('status') != 'validated' or native_validation.get('nativeInputs') != contract['nativeInputs']:
        _fail('decode-current-native', contract['nativeInputs'], native_validation.get('status'))
    components = native_validation['components']
    summary = compose_native_bindings(contract, record, tag, components)
    if native_validation['summary'] != summary:
        _fail('decode-complete-source-bindings', summary, native_validation['summary'])
    if (not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        _fail('decode-source-or-span', 'authenticated original and bounded nonempty action span', [source, start, end])
    reader = Reader(data, source, end)
    reader.pos = start
    lead = reader.peek()
    tag_width = 3 if lead == 250 else 1
    raw_tag = reader.take(tag_width, 'MoveTo-union-tag')
    actual_tag = struct.unpack_from('<H', raw_tag, 1)[0] if tag_width == 3 else raw_tag[0]
    if actual_tag != tag: _fail('decode-current-union-tag', tag, actual_tag)
    if reader.peek() == 255:
        reader.take(1, 'null-MoveTo-wrapper')
        null, fields = True, []
    else:
        reader.header(len(record['members']))
        null, fields = False, []
        child_native = components['subSpeed']
        child_components = child_native['components']
        context = components['children']
        for member in record['members']:
            begin, kind = reader.pos, member['kind']
            if kind in WIDTHS:
                wire = stored.fixed_node(reader.take(WIDTHS[kind], member['fieldName']))
                child = None
            else:
                getattr(reader, CHILD_READERS[kind])()
                kwargs = dict(source=source, digest=digest, start=begin, end=reader.pos)
                if kind == 'scalar-payload':
                    child = subspeed.doubles.decode_data(data, source=source, digest=digest, child_start=begin, child_end=reader.pos,
                        native_validation=child_components['doubleData'], scalar_native_validation=child_components['scalar'])
                    wire = _double_tree(child)
                elif kind == 'byte-payload':
                    child = subspeed.strings.decode_source_string(data, **kwargs,
                        source_helper_rva=member['sourceCall']['targetRva'], native_validation=child_components['string'])
                    wire = stored.string_node(child['value'])
                elif kind == 'curve':
                    child = subspeed.curves.decode_curve(data, **kwargs, native_validation=child_components['curve'])
                    wire = _curve_tree(child)
                elif kind == 'scalar-payload-curve-profile':
                    child = subspeed.decode_subspeed_child(data, **kwargs, native_validation=child_native)
                    wire = {'kind': 'subSpeed', 'receipt': child}
                else:
                    field = {'fieldName': member['fieldName'], 'start': begin, 'end': reader.pos}
                    if kind == 'target' and data[begin:reader.pos] != b'\xff' and target_decoder is None:
                        from scripts.game_data.memorypack.buff_recursive_actions import recursive_target
                        target_decoder = recursive_target
                    child = (vectors.decode_blackboard_vector3_value(data, source=source, logical_sha256=digest,
                        start=begin, end=reader.pos, native_validation=context['effectVectors']) if kind == 'vector-payload'
                        else ({'start': begin, 'end': reader.pos, 'status': 'exact-null', 'recursiveStoredSchemaExact': True}
                              if data[begin:reader.pos] == b'\xff' else target_decoder(data, source, digest, field, context)))
                    if child.get('recursiveStoredSchemaExact') is not True:
                        _fail('recursive-child-completeness', True, child)
                    tree = stored.decode_stored_plan(data, **kwargs, definition=summary['childDefinitions'][member['fieldName']],
                        registry=context['target']['_registry'])
                    _bind_recursive_tree(child, tree['storedTree'])
                    wire = tree['storedTree']
            encoded = subspeed.encode_subspeed_child(wire['receipt']) if wire['kind'] == 'subSpeed' else stored.encode_stored_node(wire)
            if encoded != data[begin:reader.pos]: _fail('field-named-reencode', member['fieldName'], [begin, reader.pos])
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'], 'kind': kind,
                           'start': begin, 'end': reader.pos, 'storedValue': wire, 'nativeChildReceipt': child})
    if reader.pos != end: _fail('complete-parent-end', end, reader.pos)
    result = {'schema': SCHEMA, 'source': source, 'logicalSha256': digest.upper(), 'start': start, 'end': end,
        'unionTag': tag, 'tagWidth': tag_width, 'null': null, 'memberCount': None if null else len(fields),
        'namedFields': fields, 'recursiveStoredSchemaExact': True, 'wholeStoredSpanExact': True,
        'defaultFormatterRouteConditional': True, 'actualSourceCallbackCursorEqualityProved': False,
        'actualProviderSelectionProved': False, 'finalAccumulatedInstanceStateProved': False,
        'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
    if encode_move_to(result) != data[start:end]: _fail('complete-named-reencode', 'exact original stored action', [start, end])
    result['namedFieldReencodeExact'] = True
    return result


def encode_move_to(receipt: dict) -> bytes:
    contract, record, tag = _record()
    if receipt.get('schema') != SCHEMA or receipt.get('unionTag') != tag or receipt.get('tagWidth') not in (1, 3):
        _fail('encode-current-schema-tag', SCHEMA, receipt.get('schema'))
    prefix = bytes((tag,)) if receipt['tagWidth'] == 1 else b'\xfa' + struct.pack('<H', tag)
    fields = receipt['namedFields']
    if receipt['null']:
        if fields or receipt['memberCount'] is not None: _fail('encode-null-fields', [], fields)
        return prefix + b'\xff'
    if (receipt['memberCount'] != len(record['members']) or
            [(f['fieldName'], f['kind'], f['declaredType']) for f in fields] !=
            [(m['fieldName'], m['kind'], m['declaredType']) for m in record['members']]):
        _fail('encode-complete-named-field-order', 'every current generated member in order', fields)
    return prefix + bytes((len(fields),)) + b''.join(
        subspeed.encode_subspeed_child(field['storedValue']['receipt']) if field['storedValue']['kind'] == 'subSpeed'
        else stored.encode_stored_node(field['storedValue']) for field in fields)


def _source_paths() -> set[Path]:
    paths = set(_package_import_closure(Path(__file__))) | subspeed._proof_paths() | {Path(__file__), CONTRACT_PATH}
    pending = set()
    for path in paths:
        if path.suffix != '.py': continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                name = node.value
                if name.endswith('.json') and Path(name).name == name and (CONTRACTS_DIR / name).is_file():
                    pending.add(CONTRACTS_DIR / name)
    def references(value):
        if isinstance(value, (list, tuple)):
            for child in value: yield from references(child)
        elif isinstance(value, dict):
            for child in value.values(): yield from references(child)
        elif isinstance(value, str) and Path(value).name == value and value.endswith('.json') and (CONTRACTS_DIR / value).is_file():
            yield CONTRACTS_DIR / value
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen: continue
        seen.add(path)
        pending.update(set(references(json.loads(path.read_bytes()))) - seen)
    return paths | seen


def _unpack_return(node):
    kind, value = node['t'], node['v']
    if kind == 'p': return value
    if kind == 'd': return {_unpack_return(k): _unpack_return(v) for k, v in value}
    return {'l': list, 't': tuple, 's': set, 'f': frozenset}[kind](_unpack_return(v) for v in value)


def _selected_cached_children(cache_path: Path, receipt_path: Path, pins: dict, *, gameassembly: Path, metadata: Path):
    """Reuse only unchanged four selected returns, not the full old cache scope."""
    cache = json.loads(cache_path.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    if (receipt.get('status') != 'completed' or receipt.get('exitCode') != 0
            or receipt.get('nativeChildrenCache') != _fingerprint(cache_path)
            or cache.get('status') != 'current-validated-native-cache'
            or cache.get('nativeInputs') != pins or cache.get('validatorReturnUnchanged') is not True
            or cache.get('frozenImplementation') != receipt.get('frozenImplementation')):
        _fail('authenticated-selected-child-cache', 'completed unchanged selected-build return and authenticated output bytes', cache_path)
    frozen = {row['path']: row for row in cache['frozenImplementation']}
    checked = {}
    for module in (vectors, targets, directions, selectors):
        for path in _package_import_closure(Path(module.__file__)):
            actual = _fingerprint(path)
            if frozen.get(actual['path']) != actual:
                _fail('selected-child-source-drift', frozen.get(actual['path']), actual)
            checked[actual['path']] = actual
    for row in cache['frozenImplementation']:
        if '/scripts/game_data/contracts/' in row['path']:
            actual = _fingerprint(Path(row['path']))
            if actual != row: _fail('selected-child-contract-drift', row, actual)
            checked[actual['path']] = actual
    old = _unpack_return(cache['typedReturns']['buff_recursive_actions'])['children']
    children = {key: old[key] for key in ('effectVectors', 'target', 'direction', 'selector')}
    registry, audit = load_registry(gameassembly=gameassembly, metadata=metadata)
    if audit.get('status') != 'validated': _fail('selected-executable-registry', 'validated current selected pair', audit)
    for key in ('target', 'direction', 'selector'): children[key]['_registry'] = registry
    children['directionTargets'] = direction_targets.validate_current_native_contract(children=children, gameassembly=gameassembly, metadata=metadata)
    children['fixedPointFinder'] = fixed_point.validate_current_native_contract(selector_native=children['selector'],
        vector_native=children['effectVectors'], gameassembly=gameassembly, metadata=metadata)
    return children, {'source': _fingerprint(cache_path), 'completionReceipt': _fingerprint(receipt_path),
        'selectedUnchangedReturns': ['effectVectors', 'target', 'direction', 'selector'],
        'selectedSourceAndContractPins': sorted(checked.values(), key=lambda row: row['path']),
        'completeCachedValidatorScopeClaimedCurrent': False,
        'directionTargetAndFixedPointJoinsFreshlyValidated': True}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path,
                                     children: dict | None = None,
                                     children_cache: Path | None = None,
                                     children_cache_receipt: Path | None = None) -> dict:
    contract, record, tag = _record()
    pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll differs', 'nativeInputs': pins}
    if children is not None and (children_cache is not None or children_cache_receipt is not None):
        _fail('one-selected-child-provider', 'fresh child returns or an authenticated cache/receipt pair', 'both supplied')
    if children is None and (children_cache is None or children_cache_receipt is None):
        _fail('selected-child-provider', 'fresh child returns or both explicit cache paths', None)
    paths = _source_paths() | {Path(gate.gameassembly), Path(gate.metadata), unity}
    if children_cache is not None: paths.update((children_cache, children_cache_receipt))
    before = [_fingerprint(path) for path in sorted(paths)]
    reuse = None
    if children is None:
        children, reuse = _selected_cached_children(children_cache, children_cache_receipt, pins,
            gameassembly=gate.gameassembly, metadata=gate.metadata)
    missing = [key for key in REQUIRED_CHILDREN if key not in children]
    if missing: _fail('selected-child-context', REQUIRED_CHILDREN, missing)
    # Retain only owned dependencies. The caller's action registry subsequently
    # stores this return, so retaining that registry would create a cycle.
    children = {key: children[key] for key in REQUIRED_CHILDREN}
    components = {'parentSource': source_owner.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata),
        'subSpeed': subspeed.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata), 'children': children}
    summary = compose_native_bindings(contract, record, tag, components)
    for row in before:
        actual = _fingerprint(Path(row['path']))
        if actual != row: _fail('source-drift', row, actual)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity.is_file() or _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return {'status': after.status if after.status != 'validated' else 'mismatched',
            'detail': 'native inputs changed during complete MoveTo composition', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, 'proofSources': before, 'summary': summary,
        'components': components, 'selectedChildReuse': reuse, 'wholeActionAdmitted': False, 'wholeRootAdmitted': False,
        'runtimeExecutionKnown': False, 'evidenceBoundary': {
            'exact': 'Current parent source order, typed children, complete selected parent/sub-wrapper returns and default adapter/union joins; source-proved recursive child receipts bind named metadata value trees.',
            'conditional': 'Compatible initialized contexts, default formatter/union binding and ordinary typed child returns on selected buffered/disabled-barrier paths.',
            'unresolved': 'Other member variants, actual provider/MethodInfo/callback cursors, final accumulated state, barriers/engine/allocation effects, failure/refill and whole Buff roots.'}}


def restore_report_registry(packet: dict, *, gameassembly: Path, metadata: Path) -> dict:
    """Restore non-JSON registry objects only from explicit authenticated inputs."""
    contract, _record_value, _tag = _record()
    if packet.get('status') != 'validated' or packet.get('nativeInputs') != contract['nativeInputs']:
        _fail('restore-current-report', contract['nativeInputs'], packet.get('status'))
    for row in packet['proofSources']:
        if _fingerprint(Path(row['path'])) != row: _fail('restore-report-source-drift', row, row['path'])
    inputs = contract['nativeInputs']
    gate = check_installed_native_inputs(inputs['GameAssembly.dll'], inputs['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': _fail('restore-selected-native', 'validated', gate.status)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or _fingerprint(unity)['sha256'] != inputs['UnityPlayer.dll']:
        _fail('restore-UnityPlayer', inputs['UnityPlayer.dll'], 'missing-or-mismatched')
    registry, audit = load_registry(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if audit.get('status') != 'validated': _fail('restore-registry', 'validated', audit)
    for key in ('target', 'direction', 'selector'): packet['components']['children'][key]['_registry'] = registry
    return packet


def _json_return(value):
    if isinstance(value, dict): return {key: _json_return(child) for key, child in value.items() if key != '_registry'}
    if isinstance(value, (list, tuple, set, frozenset)): return [_json_return(child) for child in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--children-cache', type=Path, required=True)
    parser.add_argument('--children-cache-receipt', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if not args.report.resolve().is_relative_to(Path(__file__).resolve().parents[3] / 'reports'):
        parser.error('--report must be inside reports/')
    result = validate_current_native_contract(gameassembly=args.gameassembly, metadata=args.metadata,
        children_cache=args.children_cache.resolve(), children_cache_receipt=args.children_cache_receipt.resolve())
    if result['status'] != 'validated':
        print(json.dumps({'status': result['status'], 'detail': result.get('detail'), 'reportPreserved': True}), flush=True)
        return
    result.update(schema='endfield.buff-move-to-composition-validation.v1',
        checkedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(_json_return(result), indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'summary': result['summary'], 'proofSources': len(result['proofSources'])}), flush=True)


if __name__ == '__main__':
    main()
