"""Full selected construction and MC2/FF source for closed ParamOutput<T>."""
import hashlib
import json

from scripts.game_data.memorypack.levelscript_action_output_programs import factory_program, reader_program

SCHEMA = 'endfield.action-output-full-source.v1'


def need(check, condition):
    if not condition:
        raise ValueError('actionOutputSource.'+check)


def _equal(left, right):
    return json.dumps(left, sort_keys=True, separators=(',', ':')) == json.dumps(right, sort_keys=True, separators=(',', ':'))


def _calls(program):
    result = {}
    for call in program['calls']:
        role = call['role']; target = call['targetVa']
        need('stable-source-call.'+role, role not in result or result[role] == target)
        result[role] = target
    return result


def _regions(packet, base):
    need('source-packet', type(packet.get('entryVa')) is int and type(base) is int)
    result = []; windows = packet.get('sourceWindows', [])
    need('full-region-and-window-count', len(packet.get('sourceRegions', [])) == len(windows) > 0)
    covered = set()
    for (at, encoded), window in zip(packet['sourceRegions'], windows):
        raw = bytes.fromhex(encoded)
        need('full-owned-source-window', type(at) is int and raw and at-base == window.get('startRva')
             and at+len(raw)-base == window.get('endRva')
             and hashlib.sha256(raw).hexdigest().upper() == window.get('sha256'))
        addresses = set(range(at, at+len(raw)))
        need('disjoint-source-regions', not covered.intersection(addresses)); covered.update(addresses)
        result.append((at, raw))
    need('owned-entry', packet['entryVa'] in covered)
    return result


def verify(source, pins):
    need('full-source-schema-and-pins', source.get('schema') == SCHEMA and source.get('nativeInputs') == pins
         and source.get('fourPathWrapperSourceProved') is True and source.get('factoryAndOriginalHolderProved') is True
         and source.get('typeArgumentSerialized') is False)
    packets = source['packets']; base = source['imageBase']
    programs = [reader_program(_regions(packets['Deserialize'], base), packets['Deserialize']['entryVa'], existing=e, null=n)
                for e in (False, True) for n in (False, True)]
    need('all-four-reader-programs', _equal(source.get('programs'), programs))
    factories = {name: factory_program(_regions(packets[name], base), packets[name]['entryVa'])
                 for name in ('.ctor', 'CreateInstance')}
    need('both-factory-programs', _equal(source.get('factoryPrograms'), factories))
    calls = _calls(programs[0])
    need('same-all-path-callees', all(calls[k] == v for program in programs for k, v in _calls(program).items()))
    need('fresh-own-wrapper-constructor', calls['wrapperConstructor'] == packets['.ctor']['entryVa'])
    expected = source['selectedSourceTargets']
    need('own-header-target-pool-and-setters', all(calls[k]-base == expected[k]
         for k in ('header', 'target', 'path', 'setTarget', 'setPath', 'barrier')))
    getter = packets['GetValue']; getter_regions = _regions(getter, base)
    need('whole-reference-getter', len(getter_regions) == 1 and getter_regions[0][0] == getter['entryVa']
         and getter_regions[0][1] == bytes.fromhex('488b4110c3'))
    allocation = source['allocationSources']; holder_cell = None
    for name, program in factories.items():
        usage = allocation[name]
        need('own-Original-allocation', type(usage.get('tag')) is int and usage['tag'] == 1
             and usage.get('typeName') == source['typeName']
             and usage.get('instructionRva') == program['allocationInstructionVa']-base
             and usage.get('usageCellRva') == program['allocationCellVa']-base)
        carrier = source['allocationCarriers'][name]; getter_carrier = source['getterCarrier']
        raw = bytes.fromhex(carrier.get('declaredTypeRecordHex', ''))
        getter_raw = bytes.fromhex(getter_carrier.get('declaredTypeRecordHex', ''))
        need('same-owned-constructed-Original-carrier', carrier.get('type') == source['typeName']
             and carrier.get('definitionTypeIndex') == getter_carrier.get('definitionTypeIndex')
             and carrier.get('argumentTypes') == getter_carrier.get('argumentTypes')
             and len(raw) == len(getter_raw) == 16 and raw[:8] == getter_raw[:8]
             and raw[10:12] == getter_raw[10:12] == bytes((21, 0)))
        holder_cell = program['allocationCellVa'] if holder_cell is None else holder_cell
        need('same-Original-cell-allocator-and-barrier', program['allocationCellVa'] == holder_cell
             and _calls(program)['allocateOriginal'] == calls['allocateWrapper']
             and program['barrierTargetVa'] == calls['barrier'])
    wrapper_usage = allocation['wrapper']; wrapper = programs[0]['wrapperAllocation']
    need('own-wrapper-allocation', (wrapper_usage.get('tag'), wrapper_usage.get('typeName')) == (1, source['wrapperName'])
         and wrapper_usage.get('instructionRva') == wrapper['instructionVa']-base
         and wrapper_usage.get('usageCellRva') == wrapper['typeCellVa']-base)
    need('explicit-normal-allocation-condition', source.get('normalTypedZeroInitializedAllocationRequired') is True
         and source.get('initializedMetadataRequired') is True and source.get('runtimeAllocationObserved') is False)
    return source


def derive(image, pins, *, wrapper, packets, existing):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_pointer_extent, closed_generic_reference_extent
    from scripts.game_data.memorypack import pointer_param as pointer, scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    base = image.pe.image_base; ctx = NativeReferenceContext(image); methods = pointer.methods(image, wrapper)
    selected = {name: packets[name]['packet'] for name in ('.ctor', 'CreateInstance', 'GetValue', 'Deserialize')}
    for name, packet in selected.items():
        _regions(packet, base)
        image.check_windows(packet['sourceWindows'], label='actionOutputSource.'+name)
        need('named-method-entry.'+name, packet['entryVa'] == image.method_pointer_va(methods[name]))
    for name in ('.ctor', 'CreateInstance'):
        scalar.owned_method_abi(image, ctx, methods[name].index, wrapper.type_definition, ('void', 1, False), [], 'actionOutputSource.'+name)
    programs = [reader_program(_regions(selected['Deserialize'], base), selected['Deserialize']['entryVa'], existing=e, null=n)
                for e in (False, True) for n in (False, True)]
    factories = {name: factory_program(_regions(selected[name], base), selected[name]['entryVa'])
                 for name in ('.ctor', 'CreateInstance')}
    allocation = {}; carriers = {}; getter_carrier = closed_generic_reference_extent(ctx, methods['GetValue'].return_type)
    for name, program in factories.items():
        usage = derive_typed_usage_context(image, program['allocationInstructionVa']-base, label='actionOutputSource.Original')
        need('Original-class-allocation-usage', type(usage.get('tag')) is int and usage['tag'] == 1)
        carrier = closed_generic_reference_pointer_extent(ctx, ctx.type_pointer(usage['typeIndex']))
        need('own-constructed-reference-Original', carrier['type'] == wrapper.wrapped_type and carrier['bytes'] == 8
             and carrier['definitionTypeIndex'] == ctx.index.types['Beyond.Gameplay.Actions.ParamOutput`1'].index)
        allocation[name] = usage
        carriers[name] = carrier
    allocation['wrapper'] = derive_typed_usage_context(image, programs[0]['wrapperAllocation']['instructionVa']-base, label='actionOutputSource.wrapper')
    targets = dict(header=existing['targets']['header'], target=existing['targets']['paramTarget'], path=existing['targets']['path'],
        setTarget=existing['methods']['set___paramTarget__']['pointerRva'], setPath=existing['methods']['set___path__']['pointerRva'],
        barrier=existing['barrierTargetRva'])
    collector = _barrier(image, base+targets['barrier'])
    source = dict(schema=SCHEMA, nativeInputs=pins, typeName=wrapper.wrapped_type, wrapperName=wrapper.name,
        imageBase=base, packets=selected, programs=programs, factoryPrograms=factories, allocationSources=allocation,
        allocationCarriers=carriers, getterCarrier=getter_carrier,
        selectedSourceTargets=targets, collector=collector,
        fourPathWrapperSourceProved=True, factoryAndOriginalHolderProved=True, typeArgumentSerialized=False,
        normalTypedZeroInitializedAllocationRequired=True, initializedMetadataRequired=True,
        runtimeAllocationObserved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        condition='Ready exact typed zero-initialized allocation and sufficient capacity, valid initialized metadata, normal compatible own constructors/reader helpers, disabled collector, selected canonical callback and disjoint storage. T is not serialized or written back by this source.')
    verify(source, pins)
    return source
