"""Exact broadcast-Single Vector3 defaults in reachable constructor leaves.

This owns a current nominal field and its initialization bits. It does not
infer serialized width, execute the constructor, or claim physical extent.
"""
import hashlib

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


LABEL = 'generatedVectorDefaultSource'
TYPE = 'UnityEngine.Vector3'


def need(key, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + key + ':' + str(detail)[:700])


def leaf_program(data, entry):
    """Own the call-free RCX field store, with every Single bit unchanged."""
    need('bounded-current-leaf', type(data) is bytes and 0 < len(data) <= 128 and type(entry) is int)
    g = BytesPath([(entry, data)], entry)
    site = g.at
    constant = g.relative('f30f1015')
    g.take('0f28c2', '0f14c2', 'f20f1141')
    offset = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('f30f1151')
    last = int.from_bytes(g.read(1), 'little', signed=True)
    need('same-owned-contiguous-three-lanes', 16 <= offset <= 119 and last == offset + 8, (offset, last))
    g.take('c3')
    return dict(selectedBytes=g.seen, programBytes=g.at-entry,
                constantInstructionVa=site, constantAddress=constant,
                fieldOffset=offset, managedFieldBytes=12,
                sourceSingleLanes=[0, 0, 0], storedFieldSlices=[[0, 8], [8, 4]],
                everySingleBitPreserved=True, callFree=True, normalReturn=True,
                sameReceiverRcx=True, stackUnchanged=True,
                integerRegistersPreserved=['rcx', 'rdx', 'r8', 'r9', 'rbx', 'rbp', 'rsi', 'rdi', 'r12', 'r13', 'r14', 'r15'],
                volatileVectorWrites=['xmm0', 'xmm2'], physicalFunctionExtentProved=False)


def value_program(data, entry):
    """The current hidden Vector3 helper, preserving allocated RDX/R9."""
    need('bounded-current-value-helper', type(data) is bytes and 0 < len(data) <= 128 and type(entry) is int)
    g = BytesPath([(entry, data)], entry)
    constant = g.relative('f30f1015')
    g.take('0f28c2', '0f14c2', 'f20f1101', 'f30f115108', '488bc1', 'c3')
    return dict(selectedBytes=g.seen, programBytes=g.at-entry, constantAddress=constant,
                managedOutputBytes=12, hiddenOutputRegister='rcx', sameOutputReturnedInRax=True,
                storedOutputSlices=[[0, 8], [8, 4]], sourceSingleLanes=[0, 0, 0],
                everySingleBitPreserved=True, callFree=True, normalReturn=True,
                stackUnchanged=True, allocatedRdxPreserved=True, allocatedR9Preserved=True,
                allNonvolatileRegistersUnchanged=True, physicalFunctionExtentProved=False)


def constructor_program(regions, entry, barrier, *, base_slot, cache_slot, base_ctor):
    """Typed allocation, inline Vector3 defaults, two whole holders and tail."""
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('independent-base-constructor-and-holder-domain', type(base_ctor) is int and base_ctor > 0
         and 16 <= base_slot < cache_slot < 128)
    b, c = bytes((base_slot,)).hex(), bytes((cache_slot,)).hex()
    g = BytesPath(regions, entry)
    g.take('4057', '4883ec20')
    flag = lifecycle._direct_flag(g, '803d')
    g.take('488bf9')
    lifecycle._initialized(g)
    site = g.at
    ancestor = dict(site=site, cell=g.relative('488b0d'))
    g.take('83b9e000000000')
    lifecycle._initialized(g)
    g.take('33d2', '488bcf')
    g.call(base_ctor)
    site = g.at
    allocation = dict(site=site, cell=g.relative('488b0d'))
    allocator = g.relative('e8')
    g.take('4c8bc8', '4885c0')
    lifecycle._nonnull(g)
    constant = g.relative('f30f1015')
    g.take('48895c2430', '0f28c2', '488d4f'+c, '0f14c2', 'f20f1140')
    field = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('f30f1150')
    last = int.from_bytes(g.read(1), 'little', signed=True)
    need('same-Original-three-lane-field', 16 <= field <= 119 and last == field+8)
    g.take('488947'+c)
    g.call(barrier)
    g.take('488d4f'+b, '4c894f'+b)
    g.call(barrier)
    g.take('488b5f'+b)
    usages, casts = [], []
    for index in range(2):
        at = g.at
        usages.append(dict(site=at, cell=g.relative('488b15')))
        if not index:
            g.take('488bcb')
        casts.append(g.relative('e8'))
        if not index:
            g.take('488947'+c, '488bcb')
    need('same-current-allocation-and-both-casts', len(set(casts)) == 1 and all(u['cell'] == allocation['cell'] for u in usages))
    g.take('488d4f'+c, '488b5c2430', '4883c420', '5f')
    need('same-restored-tail-barrier', g.relative('e9') == barrier)
    return dict(selectedBytes=g.seen, initializedFlag=flag, constructor=True,
                allocation=allocation, allocationTarget=allocator, baseClassUsage=ancestor, baseReady=None,
                baseConstructorTarget=base_ctor, instanceSetter=None,
                inlineHolderWrites=[dict(offset=o,bytes=8,sameAllocatedReference=True) for o in (cache_slot,base_slot)],
                strictCast=casts[0], classUsages=usages, baseHolderOffset=base_slot, typedCacheOffset=cache_slot,
                originalConstructorCalled=False, originalConstructorTarget=None,
                originalConstructorEffectsProved=False, normalReturnViaBarrier=True,
                vectorDefaultInitialization=dict(mode='inline-broadcast-Single', constantAddress=constant,
                    fieldOffset=field, bytes=12, storedSlices=[[0,8],[8,4]], everySingleBitPreserved=True),
                entryRspRestored=True, nonvolatileRegistersRestored=['rbx','rdi'])


def factory_program(regions, entry, barrier, *, base_slot, cache_slot):
    """Fresh typed Original, owned hidden helper, field copy and holder setter."""
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('finite-current-holder-domain', 16 <= base_slot < cache_slot < 128)
    b, c = bytes((base_slot,)).hex(), bytes((cache_slot,)).hex()
    g = BytesPath(regions, entry)
    g.take('48895c2408', '57', '4883ec30')
    flag = lifecycle._direct_flag(g,'803d')
    g.take('488bf9')
    lifecycle._initialized(g)
    site = g.at
    allocation = dict(site=site,cell=g.relative('488b0d'))
    allocator = g.relative('e8')
    g.take('488bd0','4885c0')
    lifecycle._nonnull(g)
    g.take('488d4c2420')
    helper_site = g.at
    helper = g.relative('e8')
    g.take('4533c0','8b4808','f20f1000','f20f1142')
    field = int.from_bytes(g.read(1),'little',signed=True)
    g.take('894a')
    last = int.from_bytes(g.read(1),'little',signed=True)
    need('same-helper-output-three-lane-field',16 <= field <= 119 and last == field+8)
    g.take('488bcf')
    setter = g.relative('e8')
    g.take('488b5f'+b)
    usages, casts = [], []
    for index in range(2):
        at = g.at
        usages.append(dict(site=at,cell=g.relative('488b15')))
        if not index:
            g.take('488bcb')
        casts.append(g.relative('e8'))
        if not index:
            g.take('488947'+c,'488bcb')
    need('factory-same-current-allocation-and-casts',len(set(casts)) == 1 and all(u['cell'] == allocation['cell'] for u in usages))
    g.take('488d4f'+c,'488b5c2440','4883c430','5f')
    need('factory-same-restored-tail-barrier',g.relative('e9') == barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=False,allocation=allocation,allocationTarget=allocator,
                baseClassUsage=None,baseReady=None,instanceSetter=setter,inlineHolderWrites=None,
                strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
                originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,
                normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
                vectorDefaultInitialization=dict(mode='owned-hidden-Vector3-helper',helperTarget=helper,
                    helperCallVa=helper_site,outputLocal=32,allocatedOriginalRegister='rdx',fieldOffset=field,
                    bytes=12,storedSlices=[[0,8],[8,4]],everySingleBitPreserved=True))


def _ancestry(ctx, name):
    owners = []
    while name not in ('', 'object', 'System.Object'):
        need('bounded-current-class-ancestry', name not in owners and len(owners) < 32)
        owners.append(name)
        name = ctx.parent(name)
    return owners


def derive_original(image, pins, *, original_type):
    """Freshly bind the complete leaf to its exact metadata-owned Vector3."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_member_sources import layout

    _publication_gate(image, pins)
    ctx = NativeReferenceContext(image)
    md, base = image.metadata, image.pe.image_base
    choices = image.named_type_definitions.get(original_type, ())
    need('one-current-original-definition', len(choices) == 1)
    owner = choices[0]
    need('current-nongeneric-reference-original', not ctx.is_value_type(original_type) and owner.generic_container_index < 0)
    methods = [m for m in md.methods_for(owner)
               if md.string(m.name_index) == '.ctor' and m.parameter_count == 0]
    need('one-metadata-owned-zero-argument-constructor', len(methods) == 1)
    method = methods[0]
    scalar.owned_method_abi(image, ctx, method.index, owner.index, ('void', 1, False), [], LABEL+'.constructor')
    need('nongeneric-constructor', method.generic_container_index < 0)
    entry = image.method_pointer_va(method)
    data = image.pe.bytes_at_va(entry, 128)
    mixed = data[8:10] == bytes.fromhex('c781')
    if mixed:
        from scripts.game_data.memorypack.generated_mixed_vector_default_sources import leaf_program as mixed_leaf
        program = mixed_leaf(data, entry)
    else:
        program = leaf_program(data, entry)
    fields = []
    scalar_fields = []
    for typename in _ancestry(ctx, original_type):
        for field in md.fields_for(ctx.index.types[typename]):
            if ctx.field_attributes(field.type_index) & 16:
                continue
            name = md.string(field.name_index)
            fact = ctx.field(typename+'::'+name)
            if fact[2] == program['fieldOffset']:
                need('exact-nominal-Vector3-field', fact[1] == TYPE, fact)
                scalar.ordinary(image, ctx.type_pointer(field.type_index), 17, LABEL+'.field')
                fields.append(fact)
            if mixed and fact[2] == program['scalarDefaultInitialization']['offset']:
                need('exact-owned-DWORD-scalar-field', fact[1] in ('int', 'uint'), fact)
                scalar.ordinary(image, ctx.type_pointer(field.type_index), 8 if fact[1] == 'int' else 9, LABEL+'.scalarField')
                scalar_fields.append(fact)
    need('one-current-owned-field', len(fields) == 1, fields)
    need('one-current-owned-scalar-default-field', not mixed or len(scalar_fields) == 1, scalar_fields)
    nominal = layout(image, ctx, TYPE)
    constant = image.pe.bytes_at_va(program['constantAddress'], 4)
    length = program['programBytes']
    _publication_gate(image, pins)
    result = dict(schema='endfield.generated-vector-default-source.v1', status='validated', nativeInputs=dict(pins),
                originalType=original_type, method=[method.index, original_type, '.ctor', entry-base],
                program=program, field=fields[0], layout=nominal,
                codeWindows=[dict(startRva=entry-base, endRva=entry-base+length,
                                  sha256=hashlib.sha256(data[:length]).hexdigest().upper())],
                constantData=dict(startRva=program['constantAddress']-base,
                                  endRva=program['constantAddress']-base+4,
                                  hex=constant.hex().upper(), sha256=hashlib.sha256(constant).hexdigest().upper()),
                storedFieldHex=constant.hex().upper()*3,
                completeReachableEntryProgramProved=True, physicalFunctionExtentProved=False,
                exclusiveMethodPointerOwnershipClaimed=False, constructorInvocationObserved=False,
                wireGrammarAdmitted=False, wrapperFactoryAdmitted=False,
                evidenceBoundary=dict(exact='Current metadata-owned constructor entry, exact inherited nominal Vector3 field/layout, RIP constant bytes and complete call-free three-Single initialization program.',
                    conditional='Valid writable current Original receiver and stable readable constant source; runtime execution is not observed.',
                    unresolved=['wrapper constructor and CreateInstance composition', 'physical function extent', 'serialized fields and grammar']))
    if mixed:
        result['scalarDefaultField'] = scalar_fields[0]
        result['scalarDefaultInitialization'] = program['scalarDefaultInitialization']
    return result


def derive_value_helper(image, pins, *, source_target):
    """Bind the actual named static getter to its independently parsed leaf."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_member_sources import layout
    _publication_gate(image,pins)
    ctx=NativeReferenceContext(image)
    md,base=image.metadata,image.pe.image_base
    td=ctx.index.types[TYPE]
    selected=[m for m in md.methods_for(td) if md.string(m.name_index)=='get_one'
              and image.method_pointer_va(m)==source_target]
    need('one-actual-owned-Vector3-helper',len(selected)==1)
    method=selected[0]
    need('static-nongeneric-noarg-value-helper',bool(method.flags&16) and method.generic_container_index<0
         and method.parameter_count==0 and not list(md.parameters_for(method)) and ctx.type_name(method.return_type)==TYPE)
    scalar.ordinary(image,ctx.type_pointer(method.return_type),17,LABEL+'.valueHelperReturn')
    nominal=layout(image,ctx,TYPE)
    data=image.pe.bytes_at_va(source_target,128)
    program=value_program(data,source_target)
    constant=image.pe.bytes_at_va(program['constantAddress'],4)
    _publication_gate(image,pins)
    return dict(method=[method.index,TYPE,'get_one',source_target-base],layout=nominal,program=program,
                codeWindows=[dict(startRva=source_target-base,endRva=source_target-base+program['programBytes'],
                                  sha256=hashlib.sha256(data[:program['programBytes']]).hexdigest().upper())],
                constantData=dict(startRva=program['constantAddress']-base,endRva=program['constantAddress']-base+4,
                                  hex=constant.hex().upper(),sha256=hashlib.sha256(constant).hexdigest().upper()),
                storedValueHex=constant.hex().upper()*3,physicalFunctionExtentProved=False,
                sourceInvocationObserved=False,wireGrammarAdmitted=False)


def bind_initialization(image,pins,original_type,program,barrier):
    """Re-prove current Original bits and the inline/helper source independently."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins)
    original=derive_original(image,pins,original_type=original_type)
    record=program['vectorDefaultInitialization']
    need('same-independent-current-nominal-field',record['fieldOffset']==original['field'][2]
         and record['bytes']==original['layout']['managedBytes']==12
         and record['storedSlices']==[[0,8],[8,4]] and record['everySingleBitPreserved'] is True)
    helper=None
    if record['mode']=='inline-broadcast-Single':
        bits=image.pe.bytes_at_va(record['constantAddress'],4).hex().upper()*3
    else:
        need('finite-current-default-source',record['mode']=='owned-hidden-Vector3-helper')
        helper=derive_value_helper(image,pins,source_target=record['helperTarget'])
        need('helper-preserves-allocated-Original-RDX',helper['program']['allocatedRdxPreserved'] is True)
        bits=helper['storedValueHex']
    need('same-independent-constructor-default-bits',bits==original['storedFieldHex'])
    if 'scalarDefaultInitialization' in original:
        selected = program.get('scalarDefaultInitialization', {})
        expected = original['scalarDefaultInitialization']
        need('same-independent-owned-scalar-default',
             all(selected.get(key) == expected[key] for key in ('offset', 'bytes', 'constantHex'))
             and selected.get('bytes') == 4 and original['scalarDefaultField'][2] == selected.get('offset'))
    else:
        need('no-unowned-scalar-default', 'scalarDefaultInitialization' not in program)
    collector=_barrier(image,barrier)
    _publication_gate(image,pins)
    return dict(originalConstructor=original,valueHelper=helper,currentCollector=collector,
                identicalNominalDefaultBits=True,wrapperFactorySourceSelected=True,
                initializedSourceRuntimeOutcomeObserved=False,wireGrammarAdmitted=False)
