"""Selected EffectLineCenter source transfers to inherited and concrete Data.

This owner proves the nineteen source/setter paths and the FF null return.
Bounded action values additionally require independently validated child
owners. Stored spans do not establish collection cursors or gameplay execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.action_dispatcher import RIP_QWORD_LOADS
from scripts.game_data.memorypack import buffered_owned_sources as buffered
from scripts.game_data.memorypack import inherited_reference_sources as inherited
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import setter_output_sources as setters
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vectors
from scripts.game_data.memorypack import buff_target_settings_child_receipt as targets
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT

LABEL = 'buffEffectLineCenterAction'
SCHEMA = 'endfield.buff-effect-line-center-action-native-contract.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_action_native.json'
FIELD_NAMES = ('isEnable', 'priorityLevel', 'priorityOffset', 'serverActionIndex',
    'bigEffectName', 'bigEffectTarget', 'effectActionCfg', 'effectSource',
    'forceMainBody', 'guardLodSource', 'isCreateWithSourceModelActive',
    'isMainCharacterActive', 'isShowBigEffect', 'isTargetMainCharacterActive',
    'playOnHittableObjects', 'saveEffectIdToBlackboard', 'targetSettings',
    'useGuardLodSourceOverride', 'effectCenter')
FIELD_KINDS = ('byte', 'scalar32', 'scalar32', 'scalar32', 'byte-payload',
    'target', 'effect-config', 'target', 'byte', 'target', 'byte', 'byte',
    'byte', 'byte', 'byte', 'byte-payload', 'target', 'byte', 'target')


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status='exact-current-build', label=LABEL)
    r = c['record']
    if (c.get('scope') != 'selected-nineteen-source-fields-and-null-return'
            or tuple(m['fieldName'] for m in r['members']) != FIELD_NAMES
            or tuple(m['kind'] for m in r['members']) != FIELD_KINDS
            or r['inheritedMemberCount'] != 18
            or r['runtimeTypeName'] != 'Beyond.Gameplay.EffectLineCenterAction+Data'
            or set(r['nullReturn']) != {'window', 'program', 'returnProgram'}
            or set(c['dependencies']) != {'primitiveSources', 'readValue', 'effectConfig', 'effectVectors'}
            or c['dependencies']['effectConfig'] != vectors.config.CONTRACT_PATH.name
            or c['dependencies']['effectVectors'] != vectors.CONTRACT_PATH.name):
        _fail('contract-shape', 'nineteen distinct source fields, eighteen inherited', r)
    for member in r['members']:
        declared = {'target': 'Beyond.Gameplay.Core.TargetSettings',
            'effect-config': 'Beyond.Gameplay.EffectActionCfg', 'byte-payload': 'string', 'byte': 'bool'}.get(member['kind'])
        if declared is not None and member['declaredType'] != declared:
            _fail('contract-field-type', declared, member)
    return c


def _patterns(image: Any, window: dict, rows: list, patterns: list[str]) -> None:
    references._program(image, window, rows, _fail)
    expected = patterns.copy()
    for i, pattern in enumerate(expected):
        if pattern == 'jne':
            raw = bytes.fromhex(rows[i][1])
            if not (len(raw) == 2 and raw[0] == 0x75
                    or len(raw) == 6 and raw[:2] == b'\x0f\x85'):
                _fail('nonzero-branch', 'complete JNE rel8/rel32', rows[i])
            expected[i] = rows[i][1]
    inherited._program(image, rows, expected, fail=_fail)


def _layout(image: Any, record: dict, selected: Any) -> tuple[list, list, int]:
    runtime = inherited._ancestry(image, record['runtimeTypeDefinition'])
    wrapper = inherited._ancestry(image, record['wrapperTypeDefinition'])
    inherited._ancestry_matches(runtime, record['runtimeAncestry'], _fail)
    inherited._ancestry_matches(wrapper, record['wrapperAncestry'], _fail)
    if (len(runtime) != 3 or len(wrapper) != 3
            or [r['name'] for r in runtime] != [r['wrappedType'] for r in record['wrapperRuntimeOwners']]
            or [r['name'] for r in wrapper] != [r['wrapperName'] for r in record['wrapperRuntimeOwners']]):
        _fail('paired-ancestry', 'three selected wrapper/runtime owners', [runtime, wrapper])
    instance_owner = wrapper[-1]['name']
    instance = selected.field(instance_owner + '::___instance')
    if instance[:2] != (instance_owner, runtime[-1]['name']) or not 16 <= instance[2] < 128:
        _fail('root-instance-slot', 'metadata-owned root ActionData reference', instance)
    for member in record['members']:
        fields = [(r, f) for r in runtime for f in r['fields'] if f['name'] == member['fieldName']]
        method = image.metadata.methods[member['setterMethod'][0]]
        parameters = image.metadata.parameters_for(method)
        image.validate_method_row(member['setterMethod'], label=LABEL)
        if (len(fields) != 1 or fields[0][0]['name'] != member['fieldOwner']
                or fields[0][1]['type']['name'] != member['declaredType']
                or member['setterMethod'][1] not in [r['name'] for r in wrapper]
                or method.flags & 0x10 or len(parameters) != 1
                or selected.type_name(parameters[0].type_index) != member['declaredType']
                or selected.type_name(method.return_type) != 'void'):
            _fail('owned-setter-field', member['fieldName'], [fields, member['setterMethod']])
        pair = next(r for r in record['wrapperRuntimeOwners'] if r['wrapperName'] == member['setterMethod'][1])
        if pair['wrappedType'] != member['fieldOwner']:
            _fail('setter-runtime-owner', member['fieldOwner'], pair)
    return runtime, wrapper, instance[2]


def _init_guard(row: list) -> None:
    raw = bytes.fromhex(row[1])
    if len(raw) != 7 or raw[:2] != b'\x80\x3d' or raw[-1] != 0:
        _fail('initialization-guard', 'byte RIP-relative compare with zero', row)


def _route_usage(image: Any, route: dict) -> None:
    if route['routeWindow']['startRva'] != route['switchTargetRva']:
        _fail('route-entry', route['switchTargetRva'], route['routeWindow'])
    image.nested_usage_cell({'instructionRva': route['switchTargetRva'],
        'cellRva': route['usageCellRva'], 'usageRawHex': route['usageRawHex']},
        label=LABEL, load_prefixes=RIP_QWORD_LOADS)


def _setter(image: Any, record: dict, member: dict, root_slot: int,
            selected: Any, barrier: int) -> None:
    proof = member['setterTransfer']
    rows = proof['setterProgram']
    offset = selected.field(member['fieldOwner'] + '::' + member['fieldName'])[2]
    owner = member['setterMethod'][1]
    if owner == record['wrapperRuntimeOwners'][-1]['wrapperName']:
        op = '88' if member['kind'] == 'byte' else '89'
        patterns = ['4883EC28', f'488B41{root_slot:02X}', '4885C0', 'je8',
            f'{op}50{offset:02X}', '4883C428', 'C3']
    elif owner == record['wrapperRuntimeOwners'][1]['wrapperName']:
        cache = selected.field(owner + '::__realInstance')
        if cache[1] != member['fieldOwner'] or not 16 <= cache[2] < 128 or not 16 <= offset < 128:
            _fail('inherited-cache-slot', 'owned base Data/cache disp8 fields', [cache, offset])
        _init_guard(rows[2])
        reference = member['kind'] != 'byte'
        patterns = ['4056', '4883EC20', rows[2][1], '488BF2' if reference else '0FB6F2',
            '48895C2430', '488BD9', 'je8', f'48837B{cache[2]:02X}00', 'je8',
            f'488B43{root_slot:02X}', f'483943{cache[2]:02X}', 'jne',
            f'488B4B{cache[2]:02X}' if reference else f'488B43{cache[2]:02X}',
            '488B5C2430', '4885C9' if reference else '4885C0', 'je8',
            f'488971{offset:02X}' if reference else f'408870{offset:02X}']
        patterns += ([f'4883C1{offset:02X}', '4883C420', '5E', rows[-1][1]]
                     if reference else ['4883C420', '5E', 'C3'])
        if reference and (bytes.fromhex(rows[-1][1])[0] != 0xE9 or inherited._target(rows[-1]) != barrier):
            _fail('base-reference-barrier', barrier, rows[-1])
    else:
        getter = record['getter']
        if owner != record['wrapperTypeName'] or member['kind'] != 'target' or not 128 <= offset < 0x80000000:
            _fail('concrete-reference-owner', 'derived target with disp32 field', member)
        disp = offset.to_bytes(4, 'little').hex().upper()
        patterns = ['4053', '4883EC20', '488BDA', '33D2', 'call', '4885C0', 'je8',
            '488D88' + disp, '488998' + disp, '4883C420', '5B', rows[-1][1]]
        inherited._call(rows[4], getter['method'][3], fail=_fail)
        if bytes.fromhex(rows[-1][1])[0] != 0xE9 or inherited._target(rows[-1]) != barrier:
            _fail('concrete-reference-barrier', barrier, rows[-1])
    _patterns(image, proof['setterWindow'], rows, patterns)
    if rows[0][0] != member['setterMethod'][3]:
        _fail('setter-entry', member['setterMethod'], rows[0])


def _null_return(image: Any, record: dict, barrier: int) -> None:
    """The FF header branch clears the original ref output and returns normally."""
    proof = record['nullReturn']; program = proof['program']; window = proof['window']
    header_branch = record['headerCallProgram'][-1]
    raw = bytes.fromhex(header_branch[1])
    if (len(raw) != 6 or raw[:2] != b'\x0f\x84'
            or inherited._target(header_branch) != window['startRva']):
        _fail('null-header-branch', 'JE from header AL false to selected clear', header_branch)
    _patterns(image, window, program, ['488BCB', '48C70300000000', 'call', '90', program[-1][1]])
    inherited._call(program[2], barrier, fail=_fail)
    tail = bytes.fromhex(program[-1][1])
    epilogue = proof['returnProgram']
    if (len(tail) != 5 or tail[0] != 0xe9
            or program[0][0] != window['startRva']
            or program[-1][0] + len(tail) != window['endRva']
            or epilogue != record['returnProgram'][1:]
            or inherited._target(program[-1]) != epilogue[0][0]):
        _fail('null-complete-return-join', 'clear, barrier, jump to saved RBX/RDI frame and RET', proof)
    _patterns(image, record['window'], epilogue, ['488B5C2440', '4883C420', '5F', 'C3'])


def _child_bindings(image: Any, c: dict, children: dict) -> list[dict]:
    """Join closed source types to the actual child wrapper instance types."""
    target = children.get('target', {}); vector = children.get('effectVectors', {})
    config = vector.get('effectConfigNative', {}); selected = NativeReferenceContext(image)
    config_contract = vectors.config._contract()
    for name, row in (('target', target), ('effectVectors', vector), ('effectConfig', config)):
        if row.get('status') != 'validated':
            _fail(f'recursive-child-status:{name}', 'validated', row.get('status'))
        if row.get('nativeInputs') != c['nativeInputs']:
            _fail(f'recursive-child-inputs:{name}', c['nativeInputs'], row.get('nativeInputs'))
    plan = target.get('planAudit', {})
    if plan.get('status') != 'validated':
        _fail('target-child-plan-status', 'validated', plan.get('status'))
    # The metadata-owned wrapper plan authenticates these two inputs. Its
    # target owner above separately authenticates the full three-input build.
    plan_inputs = {key: c['nativeInputs'][key]
                   for key in ('GameAssembly.dll', 'global-metadata.dat')}
    actual_plan_inputs = plan.get('nativeInputs')
    if (not isinstance(actual_plan_inputs, dict) or actual_plan_inputs.keys() != plan_inputs.keys()
            or any(not isinstance(actual_plan_inputs[key], str)
                   or actual_plan_inputs[key].upper() != value.upper()
                   for key, value in plan_inputs.items())):
        _fail('target-child-plan-inputs', plan_inputs, actual_plan_inputs)
    vector_contract = vectors._contract()
    for name, contract in (('effectConfig', config_contract), ('effectVectors', vector_contract)):
        if contract['nativeInputs'] != c['nativeInputs']:
            _fail(f'recursive-child-contract-inputs:{name}', c['nativeInputs'], contract['nativeInputs'])
    expected_order = [dict(fieldName=r['fieldName'], kind=r['kind'])
                      for r in config_contract['readOrder']]
    if config.get('readOrder') != expected_order:
        _fail('effect-config-child-read-order', expected_order, config.get('readOrder'))
    if vector.get('vectorMemberNames') != ['x', 'y', 'z']:
        _fail('effect-vector-child-members', ['x', 'y', 'z'], vector.get('vectorMemberNames'))
    if vector.get('vectorParentFields') != vector_contract['vectorParentFields']:
        _fail('effect-vector-child-parent-fields', vector_contract['vectorParentFields'],
              vector.get('vectorParentFields'))
    registry = target.get('_registry'); definition = target.get('targetDefinition')
    if (registry is None or definition not in registry.plans
            or [m.name for m in registry.plans[definition]] != target.get('targetMemberNames')):
        _fail('target-child-plan', 'authenticated ordered child plan', definition)
    result = []
    for member in c['record']['members']:
        if member['kind'] not in ('target', 'effect-config'): continue
        context = member['sourceContext']
        child_definition = definition if member['kind'] == 'target' else config_contract['wrapperTypeDefinition']
        wrapper = image.metadata.types[child_definition]
        fields = [f for f in image.metadata.fields_for(wrapper)
            if image.metadata.string(f.name_index) in ('__instance', '___instance')]
        if len(fields) != 1:
            _fail('child-instance-owner', 'one actual child wrapper instance field', child_definition)
        raw = image.pe.bytes_at_va(selected.type_pointer(fields[0].type_index), 16)
        if (len(raw) != 16 or raw[10] not in (0x11, 0x12) or raw[11] != 0
                or int.from_bytes(raw[8:10], 'little') & 0x10
                or int.from_bytes(raw[:8], 'little') != context['typeDefinition']
                or image.type_name(context['typeDefinition']) != member['declaredType']
                or selected.type_name(fields[0].type_index) != member['declaredType']):
            _fail('closed-child-runtime-identity', context, raw.hex())
        if (member['kind'] == 'target' and registry.wrapped_names.get(child_definition) != member['declaredType']
                or member['kind'] == 'effect-config' and
                (context['typeDefinition'] != config_contract['runtimeTypeDefinition']
                 or member['declaredType'] != config_contract['runtimeTypeName'])):
            _fail('child-runtime-owner-join', member, child_definition)
        result.append({'fieldName': member['fieldName'], 'kind': member['kind'],
            'runtimeTypeDefinition': context['typeDefinition'],
            'childWrapperTypeDefinition': child_definition})
    if len(result) != 6 or sum(r['kind'] == 'target' for r in result) != 5:
        _fail('recursive-child-cardinality', 'five targets and one effect configuration', result)
    return result


def _validate_image(image: Any, c: dict, string_helpers: list[int]) -> dict:
    primitives, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependencies']['primitiveSources'],
        schema='endfield.buff-pick-target-action-native-contract.v1', status='exact-current-build', label=LABEL)
    shared = read_value._contract()
    if (c['dependencies']['readValue'] != read_value.CONTRACT_PATH.name
            or any(d['nativeInputs'] != c['nativeInputs'] for d in (primitives, shared))):
        _fail('dependency-build', c['nativeInputs'], [primitives['nativeInputs'], shared['nativeInputs']])
    read_value._validate_image(image, shared)
    _route_usage(image, c['dispatcher'])
    image.validate_dispatcher(c['dispatcher'], label=LABEL)
    image.check_windows(c['codeWindows'], label=LABEL)
    record = c['record']; selected = NativeReferenceContext(image)
    wrapper = derive_from_image(image).get(record['wrapperTypeDefinition'])
    expected = [(m['fieldName'], m['setterMethod'][0], m['declaredType']) for m in record['members']]
    if (wrapper is None or wrapper.name != record['wrapperTypeName']
            or wrapper.wrapped_type != record['runtimeTypeName']
            or len(wrapper.inherited_members) != record['inheritedMemberCount']
            or [(m.name, m.method_index, m.declared_type) for m in wrapper.members] != expected
            or record['wrapperTypeDefinition'] != c['dispatcher']['wrapperTypeDefinition']
            or record['wrapperTypeName'] != c['dispatcher']['wrapperName']):
        _fail('generated-members-and-route', expected, None if wrapper is None else wrapper.row())
    for member, derived in zip(record['members'], wrapper.members, strict=True):
        width = {'byte': 1, 'scalar32': 4}.get(member['kind'])
        if width is not None and derived.width != width:
            _fail('primitive-declared-width', width, derived.row())
    _, _, slot = _layout(image, record, selected)
    offsets = {k: selected.field('MemoryPack.MemoryPackReader::' + k)[2] - 16
        for k in primitives['readerFieldsUnboxedOffsets']}
    if offsets != primitives['readerFieldsUnboxedOffsets']:
        _fail('reader-layout', primitives['readerFieldsUnboxedOffsets'], offsets)
    image.check_windows([primitives['int32Source']['window'], primitives['byteSource']['window']], label=LABEL)
    buffered.validate_int32_source(image, primitives['int32Source'], offsets, fail=_fail)
    header = buffered.validate_object_header_source(image, primitives['objectHeader'], offsets, fail=_fail)
    setters.validate_primitive_source(image, {'codeWindows': [primitives['byteSource']['window']]},
        primitives['byteSource']['member'], fail=_fail)
    normal = record['window']; image.validate_method_row(record['readerMethod'], label=LABEL)
    setters._parent(image, normal, record, record['setterOutputSource'], _fail)
    _init_guard(record['entryProgram'][3])
    _patterns(image, normal, record['entryProgram'],
        ['48895C2418', '57', '4883EC20', record['entryProgram'][3][1], '488BDA', '488BF9', 'je32'])
    _patterns(image, normal, record['headerCallProgram'], ['488D542438', '488BCF', 'call', '84C0', 'je32'])
    inherited._call(record['headerCallProgram'][2], primitives['objectHeader']['window']['startRva'], fail=_fail)
    _patterns(image, normal, record['headerComparisonProgram'], ['0FB6742438', f'4080FE{len(FIELD_NAMES):02X}', 'jne'])
    if record['headerComparisonProgram'][-1][0] + 6 != record['members'][0]['setterTransfer']['argumentProgram'][0][0]:
        _fail('header-member-join', 'header comparison immediately precedes first field', record['headerComparisonProgram'])
    _patterns(image, normal, record['returnProgram'], ['488B742430', '488B5C2440', '4883C420', '5F', 'C3'])
    getter = record['getter']; g = getter['program']; image.validate_method_row(getter['method'], label=LABEL)
    gm = image.metadata.methods[getter['method'][0]]
    cache = selected.field(record['wrapperTypeName'] + '::__realInstance')
    _init_guard(g[2])
    if (getter['method'][1:3] != [record['wrapperTypeName'], 'get___instance'] or gm.flags & 0x10
            or gm.parameter_count or selected.type_name(gm.return_type) != record['runtimeTypeName']
            or cache[1] != record['runtimeTypeName'] or not 16 <= cache[2] < 128):
        _fail('concrete-getter-ABI', 'owned concrete Data cache getter', getter)
    _patterns(image, getter['window'], g, ['4053', '4883EC20', g[2][1], '488BD9', 'je8',
        f'48837B{cache[2]:02X}00', 'je32', f'488B43{slot:02X}', f'483943{cache[2]:02X}',
        'jne', f'488B43{cache[2]:02X}', '4883C420', '5B', 'C3'])
    if g[0][0] != getter['method'][3]: _fail('getter-entry', getter['method'], g[0])
    previous = record['members'][0]['setterTransfer']['argumentProgram'][0][0]
    for i, member in enumerate(record['members']):
        args = member['setterTransfer']['argumentProgram']
        if args[0][0] != previous: _fail('source-field-contiguity', previous, args[0])
        previous = member['assignment']['rva'] + 5
        context = member.get('sourceContext')
        if context is not None:
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=_fail)
        if member['kind'] == 'byte': target = primitives['byteSource']['window']['startRva']
        elif member['kind'] == 'scalar32': target = primitives['int32Source']['window']['startRva']
        elif member['kind'] == 'byte-payload':
            target = member['sourceCall']['targetRva']
            if target not in string_helpers: _fail('string-source', string_helpers, target)
        else:
            if context is None: _fail('typed-child-required', member['declaredType'], context)
            references._return_type(image, context, _fail)
            target = shared['calledEntryRva']
        if member['sourceCall']['targetRva'] != target: _fail('source-physical-helper', target, member['sourceCall'])
        setters._bridge(image, normal, member, final=i == len(FIELD_NAMES)-1, context=context, fail=_fail)
        assignment = member['assignment']
        named.check_call(image, assignment, label=LABEL, fail=_fail)
        if assignment['targetRva'] != member['setterMethod'][3]:
            _fail('source-setter-identity', member['setterMethod'], assignment)
        _setter(image, record, member, slot, selected, c['barrierTarget'])
    if (previous != record['returnProgram'][0][0]
            or record['returnProgram'][-1][0] + 1 != normal['endRva']):
        _fail('complete-source-return', 'final setter immediately through complete normal RET', previous)
    barrier_contract, _ = read_reviewed_contract(CONTRACTS_DIR / shared['dependencies']['sourceWrappers'],
        schema='endfield.buff-timeline-source-wrappers-native-contract.v1', status='exact-current-build', label=LABEL)
    if c['barrierTarget'] != barrier_contract['barrierProgram']['program'][0][0]:
        _fail('shared-write-barrier', barrier_contract['barrierProgram'], c['barrierTarget'])
    _null_return(image, record, c['barrierTarget'])
    return {'fieldsForwardedToOwnedData': len(FIELD_NAMES), 'inheritedFields': record['inheritedMemberCount'],
        'distinctRuntimeOwners': 3, 'completeOrdinarySourceReturn': True,
        'objectHeader': header, 'nullOutputReferenceClear': True, 'completeNullSourceReturn': True,
        'storedActionGrammarAdmitted': False, 'runtimeExecutionObserved': False,
        'condition': 'initialized normal path, coherent non-null wrapper/cache and normally returning native calls'}


def validate_current_native_contract(*, children: dict | None = None,
        gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def match() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not match():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
            'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins}
    utf8 = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if utf8.get('status') != 'validated' or utf8.get('nativeInputs') != pins:
        _fail('string-source-native', pins, utf8)
    image = open_native_image(gate.gameassembly, gate.metadata)
    summary = _validate_image(image, c, utf8['sourceHelpers'])
    bindings = _child_bindings(image, c, children) if children is not None else None
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not match():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
            'detail': 'native inputs changed during source proof', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, 'unionTag': c['dispatcher']['unionTag'],
        'memberNames': list(FIELD_NAMES), 'summary': summary, 'childBindings': bindings,
        'evidenceBoundary': c['evidenceBoundary']}


def supported_tags() -> frozenset[int]:
    return frozenset((int(_contract()['dispatcher']['unionTag']),))


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
        tag: int, native_validation: dict, target_decoder: Callable, depth: int = 0) -> dict:
    c = _contract(); children = native_validation.get('children', {})
    audit = children.get('effectLineCenter', {})
    expected = [{'fieldName': m['fieldName'], 'kind': m['kind'],
        'runtimeTypeDefinition': m['sourceContext']['typeDefinition']}
        for m in c['record']['members'] if m['kind'] in ('target', 'effect-config')]
    bindings = audit.get('childBindings')
    if (any(row.get('status') != 'validated' or row.get('nativeInputs') != c['nativeInputs']
            for row in (native_validation, audit, children.get('target', {}), children.get('effectVectors', {})))
            or tag != c['dispatcher']['unionTag'] or audit.get('unionTag') != tag
            or audit.get('memberNames') != list(FIELD_NAMES)
            or not isinstance(bindings, list)
            or [{k: r.get(k) for k in ('fieldName', 'kind', 'runtimeTypeDefinition')} for r in bindings] != expected
            or any(type(r.get('childWrapperTypeDefinition')) is not int for r in bindings)
            or any(r['childWrapperTypeDefinition'] != (children['target'].get('targetDefinition')
                if r['kind'] == 'target' else vectors.config._contract()['wrapperTypeDefinition']) for r in bindings)
            or audit.get('summary', {}).get('nullOutputReferenceClear') is not True
            or audit.get('summary', {}).get('completeNullSourceReturn') is not True):
        raise ValueError(f'{LABEL}:native-not-validated')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}:depth-limit')
    if (not isinstance(source, str) or not source or not isinstance(data, bytes)
            or not isinstance(digest, str) or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data) or hashlib.sha256(data).hexdigest().upper() != digest.upper()):
        raise ValueError(f'{LABEL}:source-range-or-hash')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'effect-line-center-action') != tag:
        raise ValueError(f'{LABEL}:physical-tag')
    fields = []
    if reader.peek() == 255:
        reader.take(1, 'null-effect-line-center-wrapper')
    else:
        reader.header(len(FIELD_NAMES))
        for member in c['record']['members']:
            at = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte', 'scalar32'):
                reader.take(1 if kind == 'byte' else 4, 'effect-line-center.' + member['fieldName'])
            elif kind == 'byte-payload': reader.byte_payload()
            elif kind == 'target':
                reader.target_profile(); extent = {'start': at, 'end': reader.pos}
                if data[at] == 255:
                    child = targets.decode_target_settings_value(data, source=source,
                        logical_sha256=digest, **extent, native_validation=children['target'])
                    if child.get('status') != 'exact-null' or child.get('wholeStoredSpanExact') is not True:
                        raise ValueError(f'{LABEL}:target-null-proof')
                    child = {**child, 'isNull': True, 'recursiveStoredSchemaExact': True}
                else:
                    child = target_decoder(data, source, digest, extent, children, depth=depth)
                if child.get('recursiveStoredSchemaExact') is not True or [child.get('start'), child.get('end')] != [at, reader.pos]:
                    raise ValueError(f'{LABEL}:target-recursive-span')
                value = {'child': child}
            elif kind == 'effect-config':
                reader.effect_configuration_profile()
                child = vectors.decode_effect_config_value(data, source=source, logical_sha256=digest,
                    start=at, end=reader.pos, native_validation=children['effectVectors'])
                if child.get('recursiveStoredSchemaExact') is not True or [child.get('start'), child.get('end')] != [at, reader.pos]:
                    raise ValueError(f'{LABEL}:config-recursive-span')
                value = {'child': child}
            else: raise ValueError(f'{LABEL}:unsupported-kind')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                'kind': kind, 'start': at, 'end': reader.pos, 'rawHex': data[at:reader.pos].hex().upper(), **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}:action-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-effect-line-center-action-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'start': start, 'end': end, 'tag': tag,
        'typeName': c['record']['runtimeTypeName'], 'namedFields': fields, 'isNull': not fields,
        'wholeActionByteSpanExact': True, 'recursiveStoredSchemaExact': True,
        'wholeBuffDataExact': False, 'runtimeMeaningExact': False,
        'targetSelectionObserved': False, 'effectExecutionObserved': False}
