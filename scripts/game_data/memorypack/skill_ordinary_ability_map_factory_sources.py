"""Own the map's typed empty Sequence array construction, separate from wire.

The concrete wrapper constructor inlines its Original constructor's empty
SequenceActionData array allocation. Both pass the independently selected
array class in RCX and zero in EDX to the same actual array allocator used by
the freshly owned ReadArray source. They store the returned reference only
at the named actions field and restore their frames before the disabled
barrier tail. CreateInstance calls that exact owned Original constructor.
Ready class/usage cells, compatible normal typed zeroed object and empty-array
allocation, normal Win64 helper effects, disabled collector and stable disjoint
storage are conditions. Default arrays supply no wire count or element grammar;
live allocation/provider selection and enclosing ownership remain unresolved.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.AbilityActionMap'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityActionMapForMemoryPack'
SEQUENCE='Beyond.Gameplay.Core.SequenceActionData'


def wrapper_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g,prefix='803d')
    g.take('488bf9');g.branch('74',False,1)
    at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('74',False,1)
    array_at=g.at;array_cell=g.relative('488b0d');g.take('33d2');g.call(s['arrayAllocate'])
    g.take('488d4b18','48894318');g.call(s['barrier'])
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    need('ordinary-map-wrapper-restored-tail',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadata=ready,allocation=dict(site=at,cell=cell),allocationTarget=s['allocate'],
        arrayClassUsage=dict(site=array_at,cell=array_cell),arrayAllocationTarget=s['arrayAllocate'],arrayLengthArgument=0,
        actionsFieldOffset=24,baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        sameAllocatedOriginalStored=True,originalConstructorInvoked=False,entryRspRestored=True,allNonvolatilesRestored=True,
        normalReturnViaBarrier=True,restoredNonvolatileRegisters=['rbx','rdi'],wireBytes=0)


def original_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','33d2')
    at=g.at;cell=g.relative('488b0d');g.call(s['arrayAllocate'])
    g.take('488d4b18','48894318','4883c420','5b')
    need('ordinary-map-original-restored-tail',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,arrayClassUsage=dict(site=at,cell=cell),arrayAllocationTarget=s['arrayAllocate'],
        arrayLengthArgument=0,actionsFieldOffset=24,sameIncomingOriginalStored=True,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,
        restoredNonvolatileRegisters=['rbx'],wireBytes=0)


def prepare(image,pins):
    """Fresh own actual array source; no ordinary map or child admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.pointer_param import methods,owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_passive_map_sources import map_program
    from scripts.game_data.memorypack.skill_reference_array_sources import derive as array_derive
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('ordinary-map-factory-exact-original',TYPE,wrapper.wrapped_type)
    fields={name:ctx.field(TYPE+'::'+name)for name in('abilityEvent','actions')}
    need('ordinary-map-factory-own-array-field',(TYPE,SEQUENCE+'[]',24),fields['actions'])
    body=owned(image,image.method_pointer_va(methods(image,wrapper)['Deserialize']))
    program=map_program(body['regions'],body['pointer'],scalar.reader_offsets(image,'ordinaryMapFactory'),{k:v[2]for k,v in fields.items()})
    request=derive_typed_usage_context(image,program['typedContexts'][1]['instruction']-base,label='ordinaryMapFactory.array')
    array=array_derive(image,pins,typed_request=request,call_target=program['sourceCalls'][1]['target'],element_type=SEQUENCE,count_limit=10000)
    _publication_gate(image,pins)
    return dict(nativeInputs=pins,actualMapExistingSource=dict(method=body['pointer']-base,codeWindows=body['windows'],program=program),
        actualArraySource=array,ordinaryMapAdmitted=False,childGrammarAdmitted=False)


def prove(image,ctx,wrapper,body,symbols,original_ctor,*,prepared):
    """Callable-only finite factory hook; its preparation is freshly derived."""
    if(wrapper.name,wrapper.wrapped_type)!=(WRAPPER,TYPE):return NotImplemented
    from scripts.game_data.memorypack import generated_member_sources as members,generated_lifecycle_sources as lifecycle
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    md=image.metadata;base=image.pe.image_base;td=ctx.index.types[TYPE];array=prepared['actualArraySource']
    need('ordinary-map-prepared-actual-array',True,array.get('status')=='validated-conditional-reference-array-component'
        and array.get('elementType')==SEQUENCE and array.get('elementValueType')is False
        and array.get('closedArrayType')==SEQUENCE+'[]'and prepared.get('ordinaryMapAdmitted')is False
        and prepared.get('childGrammarAdmitted')is False)
    need('ordinary-map-owned-noarg-constructor',True,original_ctor is not None and original_ctor.declaring_type==td.index
        and md.string(original_ctor.name_index)=='.ctor'and original_ctor.parameter_count==0 and original_ctor.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,original_ctor.index,td.index,('void',1,False),[],'ordinaryMapFactory.originalCtor')
    need('ordinary-map-owned-actions-field',(TYPE,SEQUENCE+'[]',24),ctx.field(TYPE+'::actions'))
    field,=[f for f in md.fields_for(td)if md.string(f.name_index)=='actions']
    scalar.ordinary(image,ctx.type_pointer(field.type_index),29,'ordinaryMapFactory.actionsField',reference=True)
    field_raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    field_element=image.pe.bytes_at_va(int.from_bytes(field_raw[:8],'little'),16)
    need('ordinary-map-field-actual-CLASS-element',(bytes((18,0)),ctx.index.types[SEQUENCE].index),
        (field_element[10:12],int.from_bytes(field_element[:8],'little')))
    original=members._body(image,image.method_pointer_va(original_ctor));s=dict(symbols,arrayAllocate=base+array['helperRvas']['arrayAllocate'])
    constructor=original_program(original['regions'],original['pointer'],s)
    method,=[m for m in md.methods_for(md.types[wrapper.type_definition])if image.method_pointer_va(m)==body['pointer']
        and md.string(m.name_index)in('.ctor','CreateInstance')]
    name=md.string(method.name_index)
    if name=='.ctor':program=wrapper_program(body['regions'],body['pointer'],s)
    else:
        program=lifecycle.called_original_factory_program(body['regions'],body['pointer'],dict(s,constructor=original['pointer']))
        program.update(sameAllocatedOriginalStored=True,entryRspRestored=True,allNonvolatilesRestored=True)
    usages={}
    for role,site in [('original',constructor['arrayClassUsage'])]+([('wrapper',program['arrayClassUsage'])]if name=='.ctor'else[]):
        usage=derive_typed_usage_context(image,site['site']-base,label='ordinaryMapFactory.'+role)
        need('ordinary-map-exact-array-class:'+role,(1,SEQUENCE+'[]'),(usage['tag'],usage['typeName']))
        pointer=ctx.type_pointer(usage['typeIndex']);scalar.ordinary(image,pointer,29,'ordinaryMapFactory.arrayClass',reference=True)
        raw=image.pe.bytes_at_va(pointer,16);element_raw=image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16)
        need('ordinary-map-exact-ordinary-array-element:'+role,(bytes((18,0)),ctx.index.types[SEQUENCE].index),
            (element_raw[10:12],int.from_bytes(element_raw[:8],'little')))
        usages[role]=usage
    if name=='.ctor':need('ordinary-map-same-array-class-cell',constructor['arrayClassUsage']['cell'],program['arrayClassUsage']['cell'])
    barrier_windows,barrier,_=_fast_barrier(image,symbols['barrier'])
    need('ordinary-map-same-disabled-collector',symbols['disabled'],base+barrier['disabledFlagRva'])
    constructor=dict(method=[original_ctor.index,TYPE,'.ctor',original['pointer']-base],sourceFamily=original['family'],
        codeWindows=original['windows'],program=constructor,typedArrayClassUsages=usages,
        actionsField=dict(typeName=SEQUENCE+'[]',fieldOffset=24,rawTypeHex=field_raw.hex().upper(),rawElementHex=field_element.hex().upper()))
    return dict(program=program,originalConstructor=constructor,proof=dict(typeName=TYPE,wrapperName=WRAPPER,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalConstructor=constructor,
        actualArrayAllocationHelperRva=s['arrayAllocate']-base,independentActualArraySource=prepared,
        barrierWindows=barrier_windows,barrierProgram=barrier,normalTypedEmptyArrayAllocationRequired=True,
        initialEventUsesFreshZeroedAllocation=True,constructorDefaultsSupplyWireFraming=False,condition=__doc__))
