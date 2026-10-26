"""Own the split-cold reference Param<List<PosRot>> caller and factories.

This proves reference transfer, never substitutes PosRot's independent MC2
value/list grammar or the outer Param canonical callback.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

VALUE = 'System.Collections.Generic.List`1<Beyond.PosRot>'
TYPE = 'Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
SCHEMA = 'endfield.posrot-list-param-parent-source.v1'


def need(check, condition):
    if not condition:
        raise ValueError('posrotListParam.'+check)


def reader_program(regions, entry, *, existing, ff):
    need('literal-four-path-selection', type(existing) is bool and type(ff) is bool)
    g = BytesPath(regions, entry); calls = {}; allocation = None; context = None
    g.take('48895c2418', '57', '4883ec20'); flag = g.relative('803d')+1
    g.take('00', '488bda', '488bf9'); g.branch('0f84', False)
    g.take('488d542430', 'c644243000', '488bcf')
    header = g.relative('e8'); g.take('84c0'); g.branch('0f84', ff)
    if ff:
        g.take('488bcb', '48c70300000000'); barrier = g.relative('e8')
        g.take('90'); g.jump('e9')
    else:
        g.take('4889742438', '48833b00'); g.branch('0f84', not existing)
        barrier = None
        if not existing:
            at = g.at; cell = g.relative('488b0d'); allocator = g.relative('e8')
            g.take('488bf0', '4885c0'); g.branch('0f84', False)
            g.take('33d2', '488bc8'); constructor = g.relative('e8')
            allocation = dict(instructionVa=at, cellVa=cell, targetVa=allocator, constructorVa=constructor)
            g.take('488bcb', '488933'); barrier = g.relative('e8'); g.take('90'); g.jump('e9')
        g.take('0fb6742430', '4080fe04'); g.branch('0f85', False)
        at = g.at; cell = g.relative('488b15'); context = dict(instructionVa=at, cellVa=cell)
        g.take('488bcf', '488b33'); callsite = g.at; calls['constValue'] = g.relative('e8')
        context['callInstructionVa'] = callsite
        g.take('4885f6'); g.branch('74', False, 1)
        g.take('4533c0', '488bd0', '488bce'); calls['setConstValue'] = g.relative('e8')
        for name in ('idRef', 'paramSource'):
            g.take('488b33', '488bcf'); calls[name] = g.relative('e8')
            g.take('4885f6'); g.branch('74', False, 1)
            g.take('4533c0', '8bd0', '488bce'); calls['set'+name[0].upper()+name[1:]] = g.relative('e8')
        g.take('488b1b', '488bcf'); calls['path'] = g.relative('e8')
        g.take('4885db'); g.branch('74', False, 1)
        g.take('4533c0', '488bd0', '488bcb'); calls['setPath'] = g.relative('e8')
        g.take('488b742438')
    g.take('488b5c2440', '4883c420', '5f', 'c3')
    return dict(selectedBytes=g.seen, existing=existing, wrapperNull=ff, sourceCalls=calls,
        allocation=allocation, constantContext=context, initializedFlagVa=flag,
        headerTargetVa=header, barrierTargetVa=barrier, memberCount=4,
        constantStoredBytes=8, constantResultRegister='rax', constantSetterArgumentRegister='rdx',
        constantWireGrammarAdmitted=False, constantListElementsAdmitted=False,
        frameBytes=40, calleeHomeByteRange=[0, 32], headerLocalRspOffset=48,
        savedEntryHomes=dict(rbx=[24, 32], **({} if ff else dict(rsi=[16, 24]))),
        nonvolatileRsiUntouched=ff, pushedNonvolatiles=['rdi'],
        sameReaderAndOutput=True, entryRspRestored=True, allNonvolatilesRestored=True,
        normalReturn=True, nullOutputBytes=8 if ff else 0, nullOutputIsZero=ff,
        initializedMetadataRequired=True, compatibleCallsRequired=True)


def factory_program(regions, entry, *, id_ref_offset):
    need('bounded-own-idRef-offset', type(id_ref_offset) is int and 16 <= id_ref_offset < 128)
    g = BytesPath(regions, entry)
    g.take('4053', '4883ec20'); flag = g.relative('803d')+1; g.take('00', '488bd9')
    branch = g.bytes.get(g.at); need('exact-factory-metadata-branch', branch in (0x74, 0x75))
    split = branch == 0x74; g.branch('74' if split else '75', not split, 1)
    at = g.at; cell = g.relative('488b0d'); allocator = g.relative('e8')
    g.take('4885c0'); g.branch('74' if split else '75', not split, 1)
    g.take('c740'+bytes((id_ref_offset,)).hex()+'ffffffff', '488d4b10', '48894310', '4883c420', '5b')
    barrier = g.relative('e9')
    return dict(selectedBytes=g.seen, allocationInstructionVa=at, allocationCellVa=cell,
        allocatorTargetVa=allocator, barrierTargetVa=barrier, idRefOffset=id_ref_offset, defaultIdRef=-1,
        holderOffset=16, wholeOriginalReferenceStored=True, initializedFlagVa=flag,
        entryRspRestored=True, allNonvolatilesRestored=True, normalReturn=True,
        zeroInitializedTypedAllocationRequired=True, initializedMetadataRequired=True)


def _record_body(body, base, method):
    return dict(methodIndex=method.index, pointerRva=body['pointer']-base,
        instructions=[[int(r['va'], 16)-base, bytes.fromhex(r['bytes']).hex().upper()] for r in body['rows']],
        sourceWindows=body['windows'], sourceRegions=[[a, raw.hex().upper()] for a, raw in body['regions']])


def derive_parent(image, pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent, closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer, primitive_param as primitive, scalar_param_native as scalar, pooled_source_helper
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.levelscript_script_task_param_sources import _record
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.levelscript_family_regenerate import Build
    _publication_gate(image, pins); base = image.pe.image_base; ctx = NativeReferenceContext(image)
    wrappers = [w for w in derive_from_image(image).values() if w.wrapped_type == TYPE]
    need('one-own-Param-wrapper', len(wrappers) == 1); wrapper = wrappers[0]
    need('exact-four-members', [(m.name, m.declared_type) for m in wrapper.members] ==
        [('constValue', VALUE), ('idRef', 'int'), ('paramSource', 'int'), ('path', 'string')])
    need('own-wrapper-holder', ctx.field(wrapper.name+'::__instance') == (wrapper.name, TYPE, 16))
    methods = pointer.methods(image, wrapper); records = {}; slots = {}; bodies = {}
    declarations = dict(constValue=(VALUE, 21, True), idRef=('int', 8, False), paramSource=('int', 8, False), path=('string', 14, True))
    for name in ('.ctor', 'CreateInstance', 'GetValue', 'Deserialize', *('set___'+m.name+'__' for m in wrapper.members)):
        method = methods[name]; target = image.method_pointer_va(method)
        if name == 'GetValue':
            leaf = pointer.leaf(image, target, ['488B4110', 'C3'])
            records[name] = dict(methodIndex=method.index, pointerRva=target-base, **{k:v for k,v in leaf.items() if k != 'entryRva'})
        else:
            body = pointer.owned(image, target); bodies[name] = body; records[name] = _record_body(body, base, method)
        if name == 'Deserialize':
            primitive.reader_abi(image, ctx, method, wrapper); continue
        scalar.owned_method_abi(image, ctx, method.index, wrapper.type_definition,
            (TYPE, 21, True) if name == 'GetValue' else ('void', 1, False),
            [declarations[name[6:-2]]] if name.startswith('set___') else [], 'posrotListParam.'+name)
        if name.startswith('set___'):
            field = name[6:-2]; rows = records[name]['instructions']; reference = field in ('constValue', 'path')
            at = (4 if bytes.fromhex(rows[3][1])[0] == 0x74 else 6) if reference else 6
            slots[field] = bytes.fromhex(rows[at][1])[-1]
            scalar.parameter_setter(image, rows, name='path' if reference else field, slot=slots[field],
                width=8 if reference else 4, label='posrotListParam')
    occupied = [i for f, size in (('constValue', 8), ('idRef', 4), ('paramSource', 4), ('path', 8)) for i in range(slots[f], slots[f]+size)]
    need('own-disjoint-Original-fields', len(set(occupied)) == 24 and all(16 <= n < 128 for n in occupied))
    body = bodies['Deserialize']; programs = [reader_program(body['regions'], body['pointer'], existing=e, ff=f)
        for e, f in ((False, False), (True, False), (False, True), (True, True))]
    positive = programs[0]; calls = positive['sourceCalls']
    need('same-both-positive-callees', calls == programs[1]['sourceCalls'])
    need('own-four-named-setters', all(calls['set'+f[0].upper()+f[1:]] == image.method_pointer_va(methods['set___'+f+'__']) for f in slots))
    allocation = {}; factories = {}; getter_carrier = closed_generic_reference_extent(ctx, methods['GetValue'].return_type)
    for name in ('.ctor', 'CreateInstance'):
        own = bodies[name]; program = factory_program(own['regions'], own['pointer'], id_ref_offset=slots['idRef'])
        usage = derive_typed_usage_context(image, program['allocationInstructionVa']-base, label='posrotListParam.Original')
        need('own-Original-class-allocation', type(usage.get('tag')) is int and usage['tag'] == 1 and usage['typeName'] == TYPE)
        carrier = closed_generic_reference_pointer_extent(ctx, ctx.type_pointer(usage['typeIndex']))
        left = bytes.fromhex(carrier['declaredTypeRecordHex']); right = bytes.fromhex(getter_carrier['declaredTypeRecordHex'])
        need('same-closed-Original-getter-carrier', carrier['type'] == getter_carrier['type'] == TYPE
            and carrier['argumentTypes'] == getter_carrier['argumentTypes'] == [VALUE]
            and carrier['definitionTypeIndex'] == getter_carrier['definitionTypeIndex'] == ctx.index.types['Beyond.Gameplay.Actions.Param`1'].index
            and left[:8] == right[:8] and left[10:12] == right[10:12] == bytes((21, 0)))
        allocation[name] = usage; factories[name] = dict(program=program, typedAllocation=usage, closedCarrier=carrier)
    need('same-two-Original-cells', allocation['.ctor']['usageCellRva'] == allocation['CreateInstance']['usageCellRva'])
    parameter = dict(methods=records, ownedFieldSlots=slots, allocationContext=allocation['.ctor'])
    scalar.allocation_bridge(image, ctx, parameter, 'posrotListParam')
    new = positive['allocation']; wrapper_usage = derive_typed_usage_context(image, new['instructionVa']-base, label='posrotListParam.wrapper')
    need('own-wrapper-construction', (wrapper_usage['tag'], wrapper_usage['typeName']) == (1, wrapper.name)
        and new['constructorVa'] == image.method_pointer_va(methods['.ctor'])
        and all(f['program']['allocatorTargetVa'] == new['targetVa'] for f in factories.values()))
    usage = derive_typed_usage_context(image, positive['constantContext']['instructionVa']-base, label='posrotListParam.constant')
    bound = bind_typed_read(image, usage, method_name='ReadPackable', argument=VALUE, kind=21, reference=True)
    Build(image, pins).prove_named_target(calls['constValue'], 'MemoryPack.MemoryPackReader', 'ReadPackable', result_abi='reference')
    helper = dict(targetRva=calls['constValue']-base, owner='MemoryPack.MemoryPackReader', methodName='ReadPackable',
        resultAbi='reference', actualNamedOrReviewedCloneSourceProved=True, pointerAliasClaimed=False)
    offsets = scalar.reader_offsets(image, 'posrotListParam'); header = _record(image, positive['headerTargetVa'])
    primitive.object_header_source(image, header, offsets)
    need('same-both-Int32-reads', calls['idRef'] == calls['paramSource'])
    integer = _record(image, calls['idRef']); scalar.integer_source(image, integer, offsets, 'posrotListParam.integer')
    pooled = pooled_source_helper.validate_on_image(image, calls['path'], pins)
    def tail(name):
        rows = records[name]['instructions']; at = 9 if bytes.fromhex(rows[3][1]) == bytes.fromhex('7506') else 7
        rva, encoded = rows[at]; raw = bytes.fromhex(encoded)
        need('exact-reference-setter-tail', len(raw) == 5 and raw[0] == 0xe9)
        return base+rva+5+int.from_bytes(raw[1:], 'little', signed=True)
    barrier = tail('set___path__')
    need('same-all-output-and-field-barriers', all(p['barrierTargetVa'] == barrier for p in (programs[0], programs[2], programs[3]))
        and tail('set___constValue__') == barrier and all(f['program']['barrierTargetVa'] == barrier for f in factories.values()))
    collector = _barrier(image, barrier); _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, nativeInputs=pins, typeName=TYPE, valueType=VALUE,
        parent=records['Deserialize'], typedRead=usage, typedReadBinding={k:v for k,v in bound.items() if k != 'argumentPointer'},
        typedReadTargetRva=calls['constValue']-base, namedReadPackableHelper=helper,
        ownedMethods=records, parameter=parameter, programs=programs, factories=factories,
        wrapperAllocation=wrapper_usage, integerSource=integer, pooledPath=pooled, parentHeader=header, collector=collector,
        barrierTargetRva=barrier-base, sourceWindows=body['windows'], sourceRegions=[[a, raw.hex().upper()] for a, raw in body['regions']],
        fullFourPathParentSourceProved=True, bothTypedOriginalFactoriesProved=True,
        constantWireGrammarAdmitted=False, canonicalParamAdapterAdmitted=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        condition='Initialized exact compatible wrapper/Original and typed successful zero-initialized allocations, sufficient buffered input, matching StringPool, normal compatible calls, disabled collector, and disjoint storage. PosRot/list grammar and canonical outer callback remain independently required.')))
