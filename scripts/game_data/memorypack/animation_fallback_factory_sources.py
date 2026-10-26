"""Own MontageSetSo ScriptableObject factory and restored holder16 transport.

Only instruction-level ScriptableObject transport algorithms are shared with
the camera factory owner. The selected Original, wrapper, actual closed T
MethodInfo, formal return and both reciprocal generic context entries are
derived independently here. No Camera type, layout or factory result supplies
this capability. Unity engine initialization and the Original managed .ctor
remain unobserved; normal compatible engine/cast helpers are conditions.
"""
from scripts.game_data.memorypack import skill_camera_custom_factory_sources as paths

TYPE='Beyond.Gameplay.View.Animation.AnimationMontageSetSo'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_Animation_AnimationMontageSetSoForMemoryPack'


def need(check,condition):
    if not condition:raise ValueError('animationFallbackFactory.'+check)


def prove(image,ctx,wrapper,body,symbols,original_ctor,*,pins):
    """Fresh exact callable factory proof for this one nominal wrapper only."""
    if(wrapper.name,wrapper.wrapped_type)!=(WRAPPER,TYPE):return NotImplemented
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.generated_lifecycle_sources import _initialized_indexer
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);md=image.metadata;base=image.pe.image_base
    original=ctx.index.types[TYPE];wrapper_td=ctx.index.types[WRAPPER]
    need('own-ordinary-ScriptableObject-original',ctx.parent(TYPE)=='UnityEngine.ScriptableObject'
        and not ctx.is_value_type(TYPE)and original.generic_container_index<0)
    scalar.ordinary(image,ctx.type_pointer(original.byval_type_index),18,'animationFallbackFactory.Original',reference=True)
    scalar.ordinary(image,ctx.type_pointer(wrapper_td.byval_type_index),18,'animationFallbackFactory.wrapper',reference=True)
    need('own-declared-holder16',ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16))
    owned_methods=[m for m in md.methods_for(wrapper_td)if md.string(m.name_index)in('.ctor','CreateInstance')
        and image.method_pointer_va(m)==body['pointer']]
    need('actual-own-wrapper-factory-entry',bool(owned_methods)and all(not m.flags&16 and m.parameter_count==0
        and ctx.type_name(m.return_type)=='void'for m in owned_methods))
    candidates=[]
    for index,row in enumerate(body['rows'][:-1]):
        raw=bytes.fromhex(row['bytes']);following=body['rows'][index+1];call=bytes.fromhex(following['bytes'])
        if len(raw)!=7 or raw[:3]!=bytes.fromhex('488b0d')or len(call)!=5 or call[0]!=0xe8:continue
        usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='animationFallbackFactory.actual')
        if tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))!=\
                (6,'UnityEngine.ScriptableObject','CreateInstance',[],[TYPE]):continue
        site=int(following['va'],16);candidates.append((row,usage,site+5+int.from_bytes(call[1:],'little',signed=True)))
    need('one-own-actual-closed-factory',len(candidates)==1);row,usage,target=candidates[0]
    validate_typed_usage_context(image,usage,label='animationFallbackFactory')
    definition=md.methods[usage['methodSpec'][0]]
    need('own-static-noarg-generic-factory',bool(definition.flags&16)and definition.parameter_count==0
        and definition.generic_container_index>=0 and image.type_name(definition.declaring_type)=='UnityEngine.ScriptableObject'
        and md.string(definition.name_index)=='CreateInstance'and usage['methodSpec'][1]==-1)
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    argument_raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-exact-closed-T-carrier',argument_raw[10:12]==bytes((18,0))
        and int.from_bytes(argument_raw[:8],'little')==original.index)
    symbolic=ContextSymbols(image);formal=symbolic.type(ctx.type_pointer(definition.return_type));parameter=formal.get('parameterOwner',{})
    need('own-factory-return-MVAR',bytes.fromhex(formal['rawHex'])[10:12]==bytes((30,0))
        and parameter.get('methodIndex')==definition.index and parameter.get('ordinal')==0)
    context=symbolic.context(definition.index,is_method=True,slots=[0,1])
    need('own-two-reciprocal-factory-slots',[e['relativeSlot']for e in context['entries']]==[0,1]
        and[e['kind']for e in context['entries']]==[1,2])
    for entry in context['entries']:
        parameter=entry.get('type',{}).get('parameterOwner',{})
        need('both-slots-are-own-method-T',parameter.get('methodIndex')==definition.index and parameter.get('ordinal')==0)
    factory=owned(image,target);calls=paths._calls(factory)
    need('complete-own-generic-factory-calls',len(calls)==5)
    s=dict(typeFromHandle=calls[0][1],engineCreate=calls[1][1],contextEntry=calls[2][1])
    tail,=[r for r in factory['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe9]
    at=int(tail['va'],16);s['checkedCast']=at+5+int.from_bytes(bytes.fromhex(tail['bytes'])[1:],'little',signed=True)
    factory_program=paths.factory_program(factory['regions'],target,s)
    type_methods=[m for m in md.methods_for(ctx.index.types['System.Type'])if md.string(m.name_index)=='GetTypeFromHandle'
        and image.method_pointer_va(m)==s['typeFromHandle']]
    need('own-named-actual-Type-helper',len(type_methods)==1);type_method,=type_methods
    need('own-Type-helper-ABI',bool(type_method.flags&16)and ctx.type_name(type_method.return_type)=='System.Type'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(type_method)]==['System.RuntimeTypeHandle'])
    engine_methods=[m for m in md.methods_for(ctx.index.types['UnityEngine.ScriptableObject'])
        if md.string(m.name_index)=='CreateScriptableObjectInstanceFromType'and image.method_pointer_va(m)==s['engineCreate']]
    need('own-named-actual-engine-helper',len(engine_methods)==1);engine_method,=engine_methods
    need('own-engine-helper-ABI',bool(engine_method.flags&16)and ctx.type_name(engine_method.return_type)=='UnityEngine.ScriptableObject'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(engine_method)]==['System.Type','bool'])
    engine=owned(image,s['engineCreate']);engine_programs=[paths.engine_program(engine['regions'],engine['pointer'],cold=c)for c in(False,True)]
    literal=engine_programs[1]['literalPointer'];literal_raw=image.pe.bytes_at_va(literal,128).split(b'\0',1)[0]+b'\0'
    need('own-exact-engine-Icall-name',literal_raw==b'UnityEngine.ScriptableObject::CreateScriptableObjectInstanceFromType(System.Type,System.Boolean)\0')
    indexer=_initialized_indexer(image,s['contextEntry']);cast=owned(image,s['checkedCast']);compatibility=paths._calls(cast)
    need('own-cast-compatibility-call',bool(compatibility));cast_program=paths.checked_cast_success_program(cast['regions'],cast['pointer'],compatible=compatibility[0][1])
    program=paths.wrapper_program(body['regions'],body['pointer'],factory=target,barrier=symbols['barrier'])
    need('same-own-typed-factory-usage',int(row['va'],16)==program['typedFactoryUsage']['instruction'])
    barrier_windows,barrier,_=_fast_barrier(image,symbols['barrier'])
    need('same-own-disabled-collector',symbols['disabled']==base+barrier['disabledFlagRva'])
    program.update(typedFactoryMode='scriptable-object-generic',factoryUsageInstruction=[int(row['va'],16)-base,bytes.fromhex(row['bytes']).hex().upper()],
        factoryTargetVa=target,originalReferenceStoredUnchanged=True,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)])
    def native_regions(source):return[[at-base,raw.hex().upper()]for at,raw in source['regions']]
    result=dict(program=program,proof=dict(schema='endfield.animation-fallback-ScriptableObject-factory.v1',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,originalTypeDefinition=original.index,originalRawTypeHex=argument_raw.hex().upper(),
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalManagedConstructorInvoked=False,
        opaqueUnityInitializationRequired=True,typedFactoryRequest=usage,formalResult=formal,context=context,
        factoryWindows=factory['windows'],factoryRegions=native_regions(factory),factoryProgram=factory_program,
        engineWindows=engine['windows'],engineRegions=native_regions(engine),enginePrograms=engine_programs,
        castWindows=cast['windows'],castRegions=native_regions(cast),castProgram=cast_program,
        wrapperWindows=body['windows'],wrapperRegions=native_regions(body),
        engineIcallLiteral=dict(rva=literal-base,rawHex=literal_raw.hex().upper()),
        helperMethods=dict(typeFromHandle=[type_method.index,'System.Type','GetTypeFromHandle',s['typeFromHandle']-base],
            engine=[engine_method.index,'UnityEngine.ScriptableObject','CreateScriptableObjectInstanceFromType',s['engineCreate']-base]),
        symbolRvas={k:v-base for k,v in s.items()},initializedClassIndexer=indexer,barrierWindows=barrier_windows,barrierProgram=barrier,
        runtimeEngineCallbackOrObjectInitializationObserved=False,originalManagedConstructorEffectsProved=False,condition=__doc__))
    _publication_gate(image,pins);return result
