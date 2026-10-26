"""Owned zero-Vector3 and Boolean defaults in current cached factories.

The XOR/unpack leaf and the hidden named get_zero source are separate byte
proofs. Their current field identities and bits must agree before the factory
is admitted. This supplies no serialized width or runtime execution claim.
"""
import hashlib

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL = 'generatedZeroVectorFactory'
TYPE = 'UnityEngine.Vector3'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:700])


def _zero(g):
    g.take('0f57d2', '0f57c0')


def leaf_program(data, entry):
    need('bounded-complete-leaf', type(data) is bytes and 0 < len(data) <= 128 and type(entry) is int)
    g = BytesPath([(entry, data)], entry)
    _zero(g)
    at = g.at
    g.take('c641')
    boolean = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('01', '0f14c2', 'f20f1141')
    field = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('f30f1191')
    last = int.from_bytes(g.read(4), 'little', signed=True)
    need('exact-disjoint-positive-field-lanes', 16 <= boolean < 128 and 120 <= field < 128
         and last == field + 8 and not field <= boolean < field + 12)
    g.take('c3')
    return dict(selectedBytes=g.seen, programBytes=g.at-entry, fieldOffset=field,
        managedFieldBytes=12, storedFieldSlices=[[0, 8], [8, 4]], storedFieldHex='00'*12,
        scalarDefaultInitialization=dict(instructionVa=at, offset=boolean, bytes=1, constantHex='01'),
        callFree=True, normalReturn=True, sameReceiverRcx=True, stackUnchanged=True,
        allIntegerRegistersUnchanged=True, allNonvolatileRegistersUnchanged=True,
        volatileVectorWrites=['xmm0', 'xmm2'], physicalFunctionExtentProved=False)


def value_program(data, entry):
    need('bounded-hidden-zero-helper', type(data) is bytes and 0 < len(data) <= 128 and type(entry) is int)
    g = BytesPath([(entry, data)], entry)
    _zero(g)
    g.take('0f14c2', 'f20f1101', 'f30f115108', '488bc1', 'c3')
    return dict(selectedBytes=g.seen, programBytes=g.at-entry, managedOutputBytes=12,
        hiddenOutputRegister='rcx', sameOutputReturnedInRax=True, storedValueHex='00'*12,
        storedOutputSlices=[[0, 8], [8, 4]], allocatedRdxPreserved=True,
        allNonvolatileRegistersUnchanged=True, callFree=True, normalReturn=True,
        stackUnchanged=True, physicalFunctionExtentProved=False)


def program(regions, entry, barrier, *, ctor, base_slot, cache_slot):
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('finite-cached-holder-domain', type(ctor) is bool and 16 <= base_slot < cache_slot < 128)
    b, c = bytes((base_slot,)).hex(), bytes((cache_slot,)).hex()
    g = BytesPath(regions, entry)
    g.take('48895c2408', '57', '4883ec30')
    flag = lifecycle._direct_flag(g, '803d')
    g.take('488bf9')
    lifecycle._initialized(g)
    ancestor = ready = None
    if ctor:
        at = g.at
        ancestor = dict(site=at, cell=g.relative('488b0d'))
        ready = g.relative('e8')
    at = g.at
    allocation = dict(site=at, cell=g.relative('488b0d'))
    allocator = g.relative('e8')
    g.take('488bd0', '4885c0')
    lifecycle._nonnull(g)
    g.take('488d4c2420')
    helper_site = g.at
    helper = g.relative('e8')
    g.take('4533c0', '8b4808', 'f20f1000', 'f20f1142')
    field = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('898a')
    last = int.from_bytes(g.read(4), 'little', signed=True)
    g.take('488bcf')
    scalar_site = g.at
    g.take('c642')
    boolean = int.from_bytes(g.read(1), 'little', signed=True)
    g.take('01')
    need('same-disjoint-complete-current-defaults', 16 <= boolean < 128 and 120 <= field < 128
         and last == field+8 and not field <= boolean < field+12)
    setter = g.relative('e8')
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
    need('both-casts-current-allocation-class', len(set(casts)) == 1
         and all(u['cell'] == allocation['cell'] for u in usages))
    g.take('488d4f'+c, '488b5c2440', '4883c430', '5f')
    need('restored-tail-barrier', g.relative('e9') == barrier)
    return dict(selectedBytes=g.seen, initializedFlag=flag, constructor=ctor,
        allocation=allocation, allocationTarget=allocator, baseClassUsage=ancestor, baseReady=ready,
        instanceSetter=setter, inlineHolderWrites=None, strictCast=casts[0], classUsages=usages,
        baseHolderOffset=base_slot, typedCacheOffset=cache_slot,
        originalConstructorCalled=False, originalConstructorTarget=None,
        originalConstructorEffectsProved=False, baseConstructorTarget=None,
        vectorDefaultInitialization=dict(mode='owned-hidden-zero-Vector3-helper', helperTarget=helper,
            helperCallVa=helper_site, outputLocal=32, allocatedOriginalRegister='rdx',
            fieldOffset=field, bytes=12, storedSlices=[[0, 8], [8, 4]]),
        scalarDefaultInitialization=dict(instructionVa=scalar_site, offset=boolean, bytes=1, constantHex='01'),
        factoryProfile='cached-owned-zero-Vector3-and-Boolean-default.v1',
        normalReturnViaBarrier=True, entryRspRestored=True, nonvolatileRegistersRestored=['rbx', 'rdi'])


def _window(base, entry, data, program):
    length = program['programBytes']
    return dict(startRva=entry-base, endRva=entry-base+length,
                sha256=hashlib.sha256(data[:length]).hexdigest().upper(),
                boundary='complete reachable call-free entry; physical function extent unproved')


def derive_original(image, pins, *, original_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_default_sources import _ancestry
    from scripts.game_data.memorypack.generated_vector_member_sources import layout
    _publication_gate(image, pins)
    ctx, md, base = NativeReferenceContext(image), image.metadata, image.pe.image_base
    choices = image.named_type_definitions.get(original_type, ())
    need('one-current-reference-original', len(choices) == 1 and not ctx.is_value_type(original_type))
    td = choices[0]
    need('nongeneric-original', td.generic_container_index < 0)
    methods = [m for m in md.methods_for(td) if md.string(m.name_index) == '.ctor' and m.parameter_count == 0]
    need('one-owned-noarg-constructor', len(methods) == 1)
    method = methods[0]
    scalar.owned_method_abi(image, ctx, method.index, td.index, ('void', 1, False), [], LABEL+'.ctor')
    entry = image.method_pointer_va(method)
    data = image.pe.bytes_at_va(entry, 128)
    selected = leaf_program(data, entry)
    fields, booleans = [], []
    for owner in _ancestry(ctx, original_type):
        for field in md.fields_for(ctx.index.types[owner]):
            if ctx.field_attributes(field.type_index) & 16:
                continue
            fact = ctx.field(owner+'::'+md.string(field.name_index))
            if fact[2] == selected['fieldOffset']:
                need('actual-owned-Vector3-field', fact[1] == TYPE)
                scalar.ordinary(image, ctx.type_pointer(field.type_index), 17, LABEL+'.Vector3')
                fields.append(fact)
            if fact[2] == selected['scalarDefaultInitialization']['offset']:
                need('actual-owned-Boolean-field', fact[1] == 'bool')
                scalar.ordinary(image, ctx.type_pointer(field.type_index), 2, LABEL+'.bool')
                booleans.append(fact)
    need('exact-one-field-per-store', len(fields) == len(booleans) == 1, (fields, booleans))
    nominal = layout(image, ctx, TYPE)
    _publication_gate(image, pins)
    return dict(schema='endfield.generated-zero-vector-default-source.v1', status='validated',
        nativeInputs=dict(pins), originalType=original_type,
        method=[method.index, original_type, '.ctor', entry-base], program=selected,
        field=fields[0], scalarDefaultField=booleans[0], layout=nominal,
        codeWindows=[_window(base, entry, data, selected)], storedFieldHex='00'*12,
        scalarDefaultInitialization=selected['scalarDefaultInitialization'],
        completeReachableEntryProgramProved=True, physicalFunctionExtentProved=False,
        constructorInvocationObserved=False, wireGrammarAdmitted=False, wrapperFactoryAdmitted=False)


def bind_initialization(image, pins, original_type, selected, barrier):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_member_sources import layout
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image, pins)
    original = derive_original(image, pins, original_type=original_type)
    vector = selected['vectorDefaultInitialization']
    boolean = selected['scalarDefaultInitialization']
    need('same-independent-current-field-defaults', vector['mode'] == 'owned-hidden-zero-Vector3-helper'
         and vector['fieldOffset'] == original['field'][2] and vector['bytes'] == original['layout']['managedBytes'] == 12
         and vector['storedSlices'] == [[0, 8], [8, 4]] and
         all(boolean[k] == original['scalarDefaultInitialization'][k] for k in ('offset', 'bytes', 'constantHex')))
    ctx, md, base = NativeReferenceContext(image), image.metadata, image.pe.image_base
    helper = vector['helperTarget']
    methods = [m for m in md.methods_for(ctx.index.types[TYPE])
               if md.string(m.name_index) == 'get_zero' and image.method_pointer_va(m) == helper]
    need('one-actual-owned-named-zero-helper', len(methods) == 1)
    method = methods[0]
    need('static-nongeneric-noarg-Vector3-helper', bool(method.flags & 16)
         and method.generic_container_index < 0 and method.parameter_count == 0
         and ctx.type_name(method.return_type) == TYPE and not list(md.parameters_for(method)))
    scalar.ordinary(image, ctx.type_pointer(method.return_type), 17, LABEL+'.zeroReturn')
    nominal = layout(image, ctx, TYPE)
    need('same-independently-owned-helper-layout', nominal == original['layout'])
    data = image.pe.bytes_at_va(helper, 128)
    proof = value_program(data, helper)
    need('same-independent-zero-bits-and-RDX', proof['storedValueHex'] == original['storedFieldHex']
         and proof['allocatedRdxPreserved'] is True)
    collector = _barrier(image, barrier)
    _publication_gate(image, pins)
    return dict(originalConstructor=original, valueHelper=dict(method=[method.index, TYPE, 'get_zero', helper-base],
        layout=nominal, program=proof, codeWindows=[_window(base, helper, data, proof)]),
        currentCollector=collector, identicalNominalDefaultBits=True,
        wrapperFactorySourceSelected=True, initializedSourceRuntimeOutcomeObserved=False,
        ancestorClassReadyNormalReturnRequired=selected.get('baseReady') is not None,
        originalManagedConstructorInvoked=False, wireGrammarAdmitted=False)
