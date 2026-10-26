"""Composed selected checkpoint callees, including typed pool reset effects.

The actual allocator must return compatible valid writable storage on its
normal path. No zero-state assumption is taken from it: the independently
proved OnAllocate programs establish every field consumed by the subsequent
checkpoint value update. Runtime pool/vtable/table selection is conditional.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as callees
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_storage_sources as storage
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_pool_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers

SCHEMA='endfield.story-patrol-checkpoint-callee-effects.v1'
POOL='Beyond.Gameplay.ParamVariablePool`1'
VARIABLE=callees.VARIABLE


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointPoolSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _actual_symbols(packet,base):
    calls=callees._calls(packet,base)
    # These call ordinals are properties of this fully replayed finite body;
    # no address, method-name proximity or equal-width substitution is used.
    need('complete-selected-Allocate-call-profile',len(calls)>=19)
    result={name:calls[index][1]for name,index in
        (('context_type',0),('singleton',1),('pop',8),('reset_invoke',9),('type_from_context',15),('object_new',16))}
    need('one-own-context-type-target',all(calls[i][1]==result['context_type']for i in(0,2,3,4,6,7,10,12,14,17,18)))
    need('one-own-singleton-target',all(calls[i][1]==result['singleton']for i in(1,5,11,13)))
    return result


def _metadata(image,source):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    ctx=NativeReferenceContext(image);md=image.metadata;symbols=ContextSymbols(image);pool=ctx.index.types[POOL]
    allocate=callees._single_method(ctx,POOL,'Allocate',1)
    need('own-bool-reuse-input',callees._parameter_type(ctx,allocate)==['bool'])
    parameter,=md.parameters_for(allocate);ctx.require_ordinary_kind(parameter.type_index,2)
    generic=callees._single_method(ctx,VARIABLE,'OnAllocate',0);base=callees._single_method(ctx,callees.BASE_VARIABLE,'OnAllocate',0)
    need('own-reset-virtual-signatures',all(m.slot==7 and ctx.type_name(m.return_type)=='void'for m in(generic,base)))
    constructor=callees._single_method(ctx,VARIABLE,'.ctor',0)
    need('own-empty-constructor-signature',ctx.type_name(constructor.return_type)=='void')
    new_contexts={}
    for kind,c in source['proof']['creates'].items():
        row=next(e for e in c['context']['entries']if e['relativeSlot']==1)
        new_contexts[kind]=symbols.context(row['methodSpec'][0],is_method=True)
    return dict(poolDefinition=pool.index,poolContext=symbols.context(pool.index),
        allocateMethod=[allocate.index,POOL,'Allocate'],typedResetMethod=[generic.index,VARIABLE,'OnAllocate'],
        baseResetMethod=[base.index,callees.BASE_VARIABLE,'OnAllocate'],constructorMethod=[constructor.index,VARIABLE,'.ctor'],
        poolFields=[dict(name=md.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)))for f in md.fields_for(pool)],
        newVariableContexts=new_contexts,
        destinationFields={name:list(ctx.field(callees.BASE_VARIABLE+'::'+field))for name,field in
            (('realType','<realType>k__BackingField'),('valueType','<valueType>k__BackingField'))})


def _require_metadata(value,source):
    context=value['poolContext'];need('own-current-pool-context',context['definition']==value['poolDefinition']and context['typeName']==POOL and context['isMethod']is False)
    slots={e['relativeSlot']:e for e in context['entries']}
    expected={9:('Beyond.Singleton`1','get_instance'),10:('System.Collections.Generic.Stack`1','get_Count'),
        11:('System.Collections.Generic.Stack`1','Pop'),13:(VARIABLE,'.ctor')}
    for index,names in expected.items():
        slot=slots[index];need('exact-pool-call-context-'+str(index),slot['kind']==3 and(slot['typeName'],slot['methodName'])==names)
    pointer=slots[12]['type'];args=pointer['classArguments']
    need('exact-typed-pool-result-formal',slots[12]['kind']==2 and pointer['definition']['name']==VARIABLE
        and len(args)==1 and args[0]['parameterOwner']['typeIndex']==value['poolDefinition']
        and args[0]['parameterOwner']['ordinal']==0 and args[0]['parameterOwner']['typeName']==POOL)
    need('constructor-context-identity',slots[13]['methodSpec'][0]==value['constructorMethod'][0]
        and slots[13]['classArguments']==args and slots[13]['methodArguments']==[])
    need('named-result-discriminator-fields',value['destinationFields']=={
        'realType':[callees.BASE_VARIABLE,'Beyond.GEnums.ParamRealType',32],
        'valueType':[callees.BASE_VARIABLE,'Beyond.GEnums.ParamValueType',36]})
    need('exact-three-NewParamVariable-contexts',set(value['newVariableContexts'])==set(source['proof']['creates']))
    for kind,c in source['proof']['creates'].items():
        own=value['newVariableContexts'][kind];definition=next(e for e in c['context']['entries']if e['relativeSlot']==1)['methodSpec'][0]
        need('own-NewParamVariable-context',own['definition']==definition and(own['typeName'],own['methodName'])==(callees.BLACKBOARD,'NewParamVariable'))
        allocate=next(e for e in own['entries']if e['relativeSlot']==0)
        need('own-NewParamVariable-Allocate-method',allocate['kind']==3 and allocate['methodSpec'][0]==value['allocateMethod'][0]
            and(allocate['typeName'],allocate['methodName'])==(POOL,'Allocate')and len(allocate['classArguments'])==1)
        formal=allocate['classArguments'][0];raw=bytes.fromhex(formal['rawHex'])
        need('own-Allocate-method-MVAR',raw[10]==30 and raw[11]==0
            and(formal['parameterOwner']['methodIndex'],formal['parameterOwner']['ordinal'])==(definition,0))
        setter=next(e for e in own['entries']if e['relativeSlot']==4)
        need('own-property-setter-context',setter['kind']==3 and(setter['typeName'],setter['methodName'])==(VARIABLE,'set_value')
            and setter['methodSpec'][0]==source['proof']['nominal']['methods']['set_value']['index']
            and setter['classArguments']==[formal]and setter['methodArguments']==[])
    return value


def _ctor_program(regions,entry):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    g=BytesPath(regions,entry);g.take('c20000')
    return dict(selectedBytes=g.seen,memoryWrites=0,calls=0,entryRspAndNonvolatilesUntouched=True,
        physicalFunctionExtentProved=False,canonicalPhysicalMethodUniquenessClaimed=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    _publication_gate(image,pins);table=storage.derive(image,pins);source=table['proof']['calleeSource'];base=image.pe.image_base
    metadata=_require_metadata(_metadata(image,source),source);ge=GenericEntries(image)
    target=source['proof']['creates']['Beyond.Gameplay.Core.EntityPtr']['symbolRvas']['allocate'];allocate=callees._body(image,base+target)
    need('all-three-own-actual-allocation-targets',all((c['newVariable']['symbolRvas']['allocate']if c['newVariable']else c['symbolRvas']['allocate'])==target for c in source['proof']['creates'].values()))
    symbols=_actual_symbols(allocate,base)
    paths=[programs.allocate_program(helpers.regions(allocate,base),base+target,**symbols,reuse=reuse)for reuse in(False,True)]
    singleton=callees._body(image,symbols['singleton']);pop=callees._body(image,symbols['pop']);invoke=callees._body(image,symbols['reset_invoke'])
    allocator=callees._body(image,symbols['object_new'])
    base_reset=callees._body(image,image.method_pointer_va(image.metadata.methods[metadata['baseResetMethod'][0]]))
    base_program=programs.base_reset_program(helpers.regions(base_reset,base),base+base_reset['entryRva'])
    resets={};registrations={};constructors={}
    prepare=base+table['proof']['classes']['preparation']['entryRva']
    for kind in callees.programs.KINDS:
        rows=ge.observe(metadata['allocateMethod'][0],[kind],[])
        need('own-closed-Allocate-registration',len(rows)==1 and rows[0]['pointer']==base+target)
        registrations[kind]=rows[0]
        rows=ge.observe(metadata['typedResetMethod'][0],[kind],[])
        need('own-closed-OnAllocate-registration',len(rows)==1 and rows[0].get('pointer'))
        reset=callees._body(image,rows[0]['pointer'])
        resets[kind]=dict(registration=rows[0],packet=reset,
            program=programs.typed_reset_program(helpers.regions(reset,base),base+reset['entryRva'],kind=kind,base_reset=base+base_reset['entryRva']),
            invocationProgram=programs.reset_invoker_program(helpers.regions(invoke,base),base+invoke['entryRva'],prepare=prepare,callback=rows[0]['pointer']))
        rows=ge.observe(metadata['constructorMethod'][0],[kind],[])
        need('own-closed-empty-constructor-registration',len(rows)==1 and rows[0].get('pointer'))
        ctor=callees._leaf(image,rows[0]['pointer'],_ctor_program)
        constructors[kind]=dict(registration=rows[0],packet=ctor,program=_ctor_program(helpers.regions(ctor,base),base+ctor['entryRva']))
    value=norm(dict(schema=SCHEMA,status='validated-conditional-checkpoint-callee-effects',nativeInputs=pins,
        proof=dict(imageBase=base,storageSource=table,metadata=metadata,allocate=allocate,allocateRegistrations=registrations,
            symbolRvas={k:v-base for k,v in symbols.items()},allocatePrograms=paths,singleton=singleton,
            singletonProgram=programs.singleton_program(helpers.regions(singleton,base),base+singleton['entryRva'],context_type=symbols['context_type'],type_from_context=symbols['type_from_context']),
            stackPop=pop,stackPopProgram=programs.stack_pop_program(helpers.regions(pop,base),base+pop['entryRva']),
            resetInvoker=invoke,baseReset=base_reset,baseResetProgram=base_program,resets=resets,constructors=constructors,
            actualObjectAllocator=allocator,actualObjectAllocatorEffectsProved=False),
        selectedPoolCreationAndResetProgramsProved=True,selectedNoObserverValueStoreAndGetEffectsProved=True,
        selectedStringDictionaryLookupAndModeOneMutationEffectsProved=True,
        selectedCheckpointCalleeEffectsProved=True,zeroStateAssumedFromAllocator=False,
        allocationSuccessOrWritableCapacityObserved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Fresh exact helper-parent seam; typed Allocate/Stack.Pop/singleton/slot7 callback/empty ctor paths; complete base reset and all4/12/40 value resets; mode1 table lookup/update/spare insertion and whole value getter/setter source effects.',
            conditional='Same selected closed MethodInfo/class/vtable callbacks, warm pool/singleton/class metadata and valid stable typed storage; normal actual allocator returns compatible valid writable storage for its actual selected class. OnAllocate, rather than an allocator zero-state assumption, establishes key/event/counter/value state. Matching original replacement selection, disabled collector and all bounded dictionary/string callback conditions remain required.',
            unresolved=['actual heap allocation success/capacity and live pool/callback/table selection','dictionary cold initialization/resize/free-list reuse and nonselected observer/replacement paths','actual checkpoint event activation, controller ownership and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    need('schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-checkpoint-callee-effects')
    p=value['proof'];storage.validate(p['storageSource']);base=p['imageBase'];source=p['storageSource']['proof']['calleeSource']
    need('same-native-inputs-and-image',value['nativeInputs']==p['storageSource']['nativeInputs']and base==p['storageSource']['proof']['imageBase'])
    _require_metadata(p['metadata'],source)
    for name in('allocate','singleton','stackPop','resetInvoker','baseReset','actualObjectAllocator'):helpers.verify_packet(p[name])
    symbols={k:base+v for k,v in p['symbolRvas'].items()};need('exact-actual-allocation-symbols',symbols==_actual_symbols(p['allocate'],base))
    need('same-actual-Allocate-entry-all-created-values',all(
        (v['newVariable']['symbolRvas']['allocate']if v['newVariable']else v['symbolRvas']['allocate'])==p['allocate']['entryRva']
        for v in source['proof']['creates'].values()))
    expected=[programs.allocate_program(helpers.regions(p['allocate'],base),base+p['allocate']['entryRva'],**symbols,reuse=r)for r in(False,True)]
    need('full-pool-program-replay',norm(expected)==p['allocatePrograms'])
    need('actual-allocator-body-target',p['actualObjectAllocator']['entryRva']==p['symbolRvas']['object_new']and p['actualObjectAllocatorEffectsProved']is False)
    need('own-context-type-source-seam',p['symbolRvas']['context_type']==p['storageSource']['proof']['classes']['contextTypeInnerRva']
        and p['symbolRvas']['type_from_context']==p['storageSource']['proof']['classes']['contextType']['entryRva'])
    need('singleton-program-replay',norm(programs.singleton_program(helpers.regions(p['singleton'],base),symbols['singleton'],context_type=symbols['context_type'],type_from_context=symbols['type_from_context']))==p['singletonProgram'])
    need('stack-Pop-program-replay',norm(programs.stack_pop_program(helpers.regions(p['stackPop'],base),symbols['pop']))==p['stackPopProgram'])
    need('base-reset-program-replay',norm(programs.base_reset_program(helpers.regions(p['baseReset'],base),base+p['baseReset']['entryRva']))==p['baseResetProgram'])
    need('same-three-typed-pool-domains',set(p['resets'])==set(p['constructors'])==set(p['allocateRegistrations'])==set(callees.programs.KINDS))
    prepare=base+p['storageSource']['proof']['classes']['preparation']['entryRva']
    for kind,r in p['resets'].items():
        helpers.verify_packet(r['packet']);registration=r['registration']
        need('own-reset-registration-and-pool-argument',registration['pointer']==base+r['packet']['entryRva']
            and p['metadata']['typedResetMethod'][0]in registration['methodDefinitionIndices']
            and registration['classInstantiation']==source['proof']['values'][kind]['methods']['SetValue']['registration']['classInstantiation'])
        need('closed-Allocate-entry',p['allocateRegistrations'][kind]['pointer']==base+p['allocate']['entryRva']
            and p['allocateRegistrations'][kind]['classInstantiation']==registration['classInstantiation']
            and p['metadata']['allocateMethod'][0]in p['allocateRegistrations'][kind]['methodDefinitionIndices'])
        need('typed-reset-program-replay',norm(programs.typed_reset_program(helpers.regions(r['packet'],base),registration['pointer'],kind=kind,base_reset=base+p['baseReset']['entryRva']))==r['program'])
        need('typed-reset-invoker-replay',norm(programs.reset_invoker_program(helpers.regions(p['resetInvoker'],base),symbols['reset_invoke'],prepare=prepare,callback=registration['pointer']))==r['invocationProgram'])
        ctor=p['constructors'][kind];helpers.verify_packet(ctor['packet'])
        need('own-closed-empty-ctor',ctor['registration']['classInstantiation']==registration['classInstantiation']
            and p['metadata']['constructorMethod'][0]in ctor['registration']['methodDefinitionIndices']
            and ctor['registration']['pointer']==base+ctor['packet']['entryRva'])
        need('own-ctor-no-effect-program-replay',norm(_ctor_program(helpers.regions(ctor['packet'],base),base+ctor['packet']['entryRva']))==ctor['program'])
    need('selected-source-flags-without-runtime-grant',all(value[k]is True for k in
        ('selectedPoolCreationAndResetProgramsProved','selectedNoObserverValueStoreAndGetEffectsProved','selectedStringDictionaryLookupAndModeOneMutationEffectsProved','selectedCheckpointCalleeEffectsProved'))
        and all(value[k]is False for k in('zeroStateAssumedFromAllocator','allocationSuccessOrWritableCapacityObserved','runtimeInvocationObserved','playbackProved')))
    return value
