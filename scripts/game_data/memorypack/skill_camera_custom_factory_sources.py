"""Exact typed ScriptableObject factory transport for CustomConfig's holder.

The wrapper's factory is a closed ScriptableObject.CreateInstance<T> call,
not an observed direct managed allocation or Original constructor invocation.
Its initialized generic context supplies T to the Type conversion and to the
final checked cast. The selected successful cast returns the unchanged engine
factory result, which the wrapper stores only at its own holder16 before the
disabled barrier tail. Null and throwing/cast-failure alternatives are distinct.

Matching coherent inflated generic contexts, normal compatible Type/Unity
ICall/class/cast helpers, initialized engine object storage and stable disjoint
frames remain conditions. Unity initialization and the managed Original .ctor
are not inferred from a named API or a list default. This source transport
supplies no child grammar, camera behavior, enclosing action or EOF.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_camera_custom_config_sources import TYPE,WRAPPER


def wrapper_program(regions,entry,*,factory,barrier):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1;g.take('00','488bd9');g.branch('75',True,1)
    site=g.at;cell=g.relative('488b0d');g.call(factory)
    g.take('488d4b10','48894310','4883c420','5b')
    need('camera-custom-restored-holder-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,readyFlag=flag,typedFactoryUsage=dict(instruction=site,cell=cell),
        typedFactoryTarget=factory,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameFactoryReference=True)],
        sameTypedFactoryResultStored=True,entryRspRestored=True,allNonvolatilesRestored=True,
        normalReturnViaBarrier=True,managedOriginalConstructorInvoked=False,directManagedAllocationClaimed=False)


def factory_program(regions,entry,s):
    """Initialized generic context/class; opaque engine result reaches cast."""
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    class_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('74',False,1)
    g.take('33d2','488bcb');g.call(s['typeFromHandle']);g.take('4533c0','b201','488bc8');g.call(s['engineCreate'])
    g.take('488bd8','488b4f38','ba01000000');g.call(s['contextEntry'])
    g.take('488bd0','488bcb','488b5c2430','4883c420','5f')
    need('camera-custom-checked-cast-tail',s['checkedCast'],g.relative('e9'))
    return dict(selectedBytes=g.seen,readyClassCell=class_cell,contextPointerOffset=56,typeClassSlot=0,
        checkedCastClassLookupIndex=1,typeFromHandleTarget=s['typeFromHandle'],engineCreateTarget=s['engineCreate'],
        engineInitializeAndReset=True,sameEngineResultPassedToCast=True,sameEntryMethodInfoUsedForTypeAndCast=True,
        entryRspRestoredBeforeTail=True,allNonvolatilesRestoredBeforeTail=True,
        managedOriginalConstructorInvoked=False,engineCreationSemanticsProved=False)


def checked_cast_success_program(regions,entry,*,compatible):
    """Complete nonnull/success path; its compatibility predicate stays owned."""
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1)
    g.take('4889742430','488b31','488bcf','488bd6');g.call(compatible);g.take('84c0');g.branch('74',False,1)
    g.take('488b742430','488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,sameIncomingObjectReturned=True,entryRspRestored=True,
        predicateMustReturnTrue=True,actualInputClassCompatibilityObserved=False)


def engine_program(regions,entry,*,cold=False):
    """Actual bool/Type argument restoration before the engine ICall tail."""
    need('camera-custom-literal-engine-cache-path',True,type(cold)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');cell=g.relative('488b05')
    g.take('0fb6da','488bf9','4885c0');g.branch('74',cold,1);literal=None;resolve=None
    if cold:
        literal=g.relative('488d0d');resolve=g.relative('e8');g.take('4885c0');g.branch('0f84',False)
        need('camera-custom-same-engine-Icall-cache-cell',cell,g.relative('488905'));g.jump('eb',1)
    g.take('0fb6d3','488bcf','488b5c2430','4883c420','5f','48ffe0')
    return dict(selectedBytes=g.seen,icallCell=cell,literalPointer=literal,resolverTarget=resolve,
        sameIncomingTypeAndNormalizedBoolPassed=True,entryRspRestoredBeforeTail=True,
        sameSelectedEngineCallbackUsed=True,engineImplementationIdentityProved=False)


def _calls(source):
    result=[]
    for row in source['rows']:
        raw=bytes.fromhex(row['bytes'])
        if len(raw)==5 and raw[0]==0xe8:
            site=int(row['va'],16);result.append((site,site+5+int.from_bytes(raw[1:],'little',signed=True)))
    return result


def prove(image,ctx,wrapper,body,symbols,original_ctor,*,pins):
    """Fresh finite callable proof, never a substitute prevalidated object."""
    if(wrapper.name,wrapper.wrapped_type)!=(WRAPPER,TYPE):return NotImplemented
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.generated_lifecycle_sources import _initialized_indexer
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    md=image.metadata;base=image.pe.image_base
    need('camera-custom-scriptable-original-parent','UnityEngine.ScriptableObject',ctx.parent(TYPE))
    candidates=[]
    for index,row in enumerate(body['rows'][:-1]):
        raw=bytes.fromhex(row['bytes']);following=body['rows'][index+1];call=bytes.fromhex(following['bytes'])
        if len(raw)!=7 or raw[:3]!=bytes.fromhex('488b0d')or len(call)!=5 or call[0]!=0xe8:continue
        usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='cameraCustomFactory.actualFactory')
        if(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))!=(6,'UnityEngine.ScriptableObject','CreateInstance',[],[TYPE]):continue
        at=int(following['va'],16);candidates.append((row,usage,at+5+int.from_bytes(call[1:],'little',signed=True)))
    need('camera-custom-one-actual-closed-Scriptable-factory',True,len(candidates)==1)
    row,usage,target=candidates[0];validate_typed_usage_context(image,usage,label='cameraCustomFactory')
    definition=md.methods[usage['methodSpec'][0]]
    need('camera-custom-factory-owned-static-noarg-generic',True,definition.flags&16 and definition.parameter_count==0
        and definition.generic_container_index>=0 and md.type_full_name(md.types[definition.declaring_type])=='UnityEngine.ScriptableObject'
        and md.string(definition.name_index)=='CreateInstance')
    symbolic=ContextSymbols(image);formal=symbolic.type(ctx.type_pointer(definition.return_type))
    owner=formal.get('parameterOwner',{})
    need('camera-custom-factory-own-MVAR-result',True,owner.get('methodIndex')==definition.index and owner.get('ordinal')==0
        and bytes.fromhex(formal['rawHex'])[10:12]==bytes((30,0)))
    context=symbolic.context(definition.index,is_method=True,slots=[0,1])
    need('camera-custom-two-owned-typed-context-slots',True,[e['relativeSlot']for e in context['entries']]==[0,1]
        and[e['kind']for e in context['entries']]==[1,2])
    for entry in context['entries']:
        parameter=entry['type'].get('parameterOwner',{})
        need('camera-custom-both-context-entries-are-own-T',True,parameter.get('methodIndex')==definition.index and parameter.get('ordinal')==0)
    factory=owned(image,target);calls=_calls(factory)
    need('camera-custom-complete-generic-factory-calls',True,len(calls)==5)
    s=dict(typeFromHandle=calls[0][1],engineCreate=calls[1][1],contextEntry=calls[2][1])
    # A complete parser obtains the actual restored checked-cast tail itself.
    tail,=[r for r in factory['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe9]
    at=int(tail['va'],16);s['checkedCast']=at+5+int.from_bytes(bytes.fromhex(tail['bytes'])[1:],'little',signed=True)
    transfer=factory_program(factory['regions'],target,s)
    native_type,=[t for t in image.named_type_definitions['System.Type']]
    type_methods=[m for m in md.methods_for(native_type)if md.string(m.name_index)=='GetTypeFromHandle'
        and image.method_pointer_va(m)==s['typeFromHandle']]
    need('camera-custom-named-actual-Type-handle-helper',True,len(type_methods)==1)
    method,=type_methods
    need('camera-custom-Type-handle-ABI',True,method.flags&16 and ctx.type_name(method.return_type)=='System.Type'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(method)]==['System.RuntimeTypeHandle'])
    engine_methods=[m for m in md.methods_for(ctx.index.types['UnityEngine.ScriptableObject'])
        if md.string(m.name_index)=='CreateScriptableObjectInstanceFromType'and image.method_pointer_va(m)==s['engineCreate']]
    need('camera-custom-named-actual-engine-helper',True,len(engine_methods)==1)
    method,=engine_methods
    need('camera-custom-engine-Type-bool-ABI',True,method.flags&16 and ctx.type_name(method.return_type)=='UnityEngine.ScriptableObject'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(method)]==['System.Type','bool'])
    engine=owned(image,s['engineCreate']);engine_paths=[engine_program(engine['regions'],engine['pointer'],cold=c)for c in(False,True)]
    literal=engine_paths[1]['literalPointer'];raw=image.pe.bytes_at_va(literal,128).split(b'\0',1)[0]+b'\0'
    expected=b'UnityEngine.ScriptableObject::CreateScriptableObjectInstanceFromType(System.Type,System.Boolean)\0'
    need('camera-custom-exact-engine-Icall-name',expected,raw)
    indexer=_initialized_indexer(image,s['contextEntry'])
    cast=owned(image,s['checkedCast']);compatibility=_calls(cast)
    need('camera-custom-owned-cast-compatibility-call',True,len(compatibility)>=1)
    cast_program=checked_cast_success_program(cast['regions'],cast['pointer'],compatible=compatibility[0][1])
    program=wrapper_program(body['regions'],body['pointer'],factory=target,barrier=symbols['barrier'])
    need('camera-custom-same-actual-factory-context-site',int(row['va'],16),program['typedFactoryUsage']['instruction'])
    barrier_windows,barrier,_=_fast_barrier(image,symbols['barrier'])
    need('camera-custom-same-disabled-collector',symbols['disabled'],base+barrier['disabledFlagRva'])
    program.update(typedFactoryMode='scriptable-object-generic',factoryUsageInstruction=[int(row['va'],16)-base,bytes.fromhex(row['bytes']).hex().upper()],
        factoryTargetVa=target,originalReferenceStoredUnchanged=True,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)])
    return dict(program=program,proof=dict(nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalManagedConstructorInvoked=False,
        opaqueUnityInitializationRequired=True,typedFactoryRequest=usage,formalResult=formal,context=context,
        factoryWindows=factory['windows'],factoryProgram=transfer,engineWindows=engine['windows'],enginePrograms=engine_paths,
        engineIcallLiteral=dict(rva=literal-base,rawHex=raw.hex().upper()),castWindows=cast['windows'],castProgram=cast_program,
        initializedClassIndexer=indexer,barrierWindows=barrier_windows,barrierProgram=barrier,
        runtimeEngineCallbackOrObjectInitializationObserved=False,originalManagedConstructorEffectsProved=False,condition=__doc__))
