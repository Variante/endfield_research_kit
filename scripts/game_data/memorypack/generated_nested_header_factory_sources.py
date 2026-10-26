"""Selected initialized header factories with a fresh validation Param child.

Every selected caller byte, allocation argument, holder/cache write and return
is owned here. Typed allocations, constructed child context, field declarations
and the disabled collector are bound separately on the same selected image.
Cold initialization, collector mutation and live context outcomes are excluded.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.LevelEvent.OnSpecificChairInteract'
PROFILE='initialized-nested-header-inline-collector.v1'


def need(check,value,detail=''):
    if not value:raise ValueError('generatedNestedHeaderFactory.'+check+(':'+str(detail)[:600]if detail else''))


def _boolean_argument(image,pointer):
    from scripts.game_data.memorypack.scalar_param_native import ordinary
    ordinary(image,pointer,2,'generatedNestedHeaderFactory.closedBooleanArgument')
    return image.pe.bytes_at_va(pointer,16)


def program(regions,entry,*,ctor,image_base,disabled,base_slot,cache_slot):
    need('literal-roles',type(ctor)is bool and(base_slot,cache_slot)==(16,40)
        and all(type(n)is int and n>0 for n in(image_base,disabled)))
    g=BytesPath(regions,entry);flags=[];ancestors=[];unused=[]
    if ctor:g.take('488bc4','53','55','56','57','4883ec78')
    else:g.take('48895c2410','55','57','4157','4883ec40')
    flags.append(g.relative('803d')+1);g.take('00')
    need('own-image-base',g.relative('488d2d'if ctor else'4c8d3d')==image_base)
    if ctor:
        g.take('4c896008');unused.append(g.relative('488d3d'))
        g.take('4c897010');unused.append(g.relative('4c8d25'))
        g.take('4c8978d8','488bf1','49bf');g.read(8);g.take('49be');g.read(8)
    else:g.take('488be9')
    g.branch('0f85',True)
    if ctor:
        for _ in range(8):
            site=g.at;cell=g.relative('488b0d');use=dict(site=site,cell=cell)
            if bytes(g.bytes.get(g.at+i,0)for i in range(2))!=bytes.fromhex('83b9'):
                base_allocation=use;allocator=g.relative('e8');break
            g.take('83b9e000000000');g.branch('75',True,1);ancestors.append(use)
            flags.append(g.relative('803d')+1);g.take('00');g.branch('0f85',True)
        else:raise ValueError('generatedNestedHeaderFactory.bounded-ancestors')
        g.take('4c8b7c2470','4c8bb424a8000000','4c8ba424a0000000','4885c0');g.branch('0f84',False)
        need('same-base-disabled-collector',g.relative('833d')+1==disabled)
        g.take('00','c7405401000000','c6405801','48894610');g.branch('74',True,1)
        site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);g.call(allocator)
        g.take('488bd8','4885c0');g.branch('0f84',False)
        g.take('33d2','488bc8');ancestor_ctor=dict(site=g.at,target=g.relative('e8'))
        g.take('4533c0','488bd3','488bce');setter=g.relative('e8')
        g.take('488b5e10');first_site=g.at;first=g.relative('488b3d');g.take('4885db');g.branch('0f85',True)
        store='48895e28';finish=('4883c478','5f','5e','5d','5b','c3')
        nested=None
    else:
        site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell)
        g.take('4889742460');allocator=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
        child_class=dict(site=g.at,cell=g.relative('488b0d'))
        g.take('83b9e000000000');g.branch('75',True,1)
        child_context=dict(site=g.at,cell=g.relative('488b35'))
        g.take('488b4620','f6803801000001');g.branch('75',True,1)
        g.take('488b88c0000000','ba05000000');indexer=g.relative('e8')
        g.take('488bc8');g.call(allocator);g.take('488bd8','4885c0');g.branch('0f84',False)
        g.take('488b4620','f6803801000001');g.branch('75',True,1)
        g.take('488b80c0000000','488b4830','4883792000');g.branch('75',True,1)
        g.take('488b4e20','f6813801000001');g.branch('75',True,1)
        need('same-child-disabled-collector',g.relative('833d')+1==disabled)
        g.take('00','c74324ffffffff','c7431000000000','c6432001','48895f78');g.branch('74',True,1)
        g.take('4533c0','c7475401000000','488bd7','c6475801','488bcd');setter=g.relative('e8')
        g.take('488b5d10');first_site=g.at;first=g.relative('488b3d');g.take('4885db');g.branch('75',True,1)
        store='48895d28';finish=('488b742460','488b5c2468','4883c440','415f','5f','5d','c3')
        nested=dict(classUsage=child_class,contextUsage=child_context,contextIndex=5,indexedClassHelper=indexer,
            referenceOffset=120,rawStores=[dict(offset=36,bytes=4,constantHex='FFFFFFFF'),
                dict(offset=16,bytes=4,constantHex='00000000'),dict(offset=32,bytes=1,constantHex='01')],
            freshZeroedChildAllocationRequired=True,completeSameChildReferenceStored=True,
            genericHeapFieldLayoutAdmitted=False)
        base_allocation=None;ancestor_ctor=None
    g.take('488b0b','488bd7');predicate=g.relative('e8');g.take('84c0');g.branch('74',False,1)
    g.take(store);second_site=g.at;second=g.relative('488b3d');g.take('488b0b','488bd7');g.call(predicate)
    g.take('84c0');g.branch('74',False,1);g.jump('e9')
    need('same-final-disabled-collector',g.relative('833d')+1==disabled)
    g.take('00');g.branch('74',True,1);g.take(*finish)
    need('same-allocated-current-class',first==second==allocation['cell'])
    restored=['rbx','rbp','rsi','rdi','r15']+(['r12','r14']if ctor else[])
    result=dict(selectedBytes=g.seen,factoryProfile=PROFILE,holderSourceProfile='rsi-wrapper-rbp-image-base-inline-collector',
        initializedFlag=flags[0],initializedFlags=flags,constructor=ctor,allocation=allocation,allocationTarget=allocator,
        baseClassUsage=None,ancestorClassUsages=ancestors,baseReady=None,instanceSetter=setter,strictCast=None,
        classUsages=[dict(site=first_site,cell=first),dict(site=second_site,cell=second)],
        inlineStrictCasts=dict(sameBaseReferenceCached=True,successfulPredicateConditional=True,
            runtimePredicateOutcomeObserved=False,predicateTarget=predicate,entryRspRestored=True,nonvolatilesRestored=restored),
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,
        originalConstructorTarget=None,originalConstructorEffectsProved=False,normalReturnViaBarrier=False,
        disabledCollectorCell=disabled,entryRspRestored=True,nonvolatileRegistersRestored=restored,
        baseAllocation=base_allocation,ancestorConstructor=ancestor_ctor,nestedInitialization=nested,
        metadataInitializerExecutionClaimed=False,activeCollectorAdmitted=False,childWireGrammarAdmitted=False,
        unusedInitializerAddresses=unused,
        condition='Initialized exact own metadata/classes/context slots, nonnull typed zeroed allocations, normal '
            'compatible allocation/constructor/indexed-class ABI and disabled collector. Selected class predicates '
            'succeed normally. Actual context binding, cold initialization and runtime execution remain conditional.')
    return result


def derive_program(image,pins,ctx,wrapper,body,barrier,*,original_chain,wrapper_chain):
    """Bind every allocation/context/field role on the caller's selected image."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_extent
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import generated_lifecycle_sources as life
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    need('finite-current-owner',wrapper.wrapped_type==TYPE)
    md=image.metadata;base=image.pe.image_base
    methods=[m for m in md.methods_for(md.types[wrapper.type_definition])
        if image.method_pointer_va(m)==body['pointer']and md.string(m.name_index)in('.ctor','CreateInstance')]
    need('actual-owned-factory',len(methods)==1)
    ctor=md.string(methods[0].name_index)=='.ctor';collector=_barrier(image,barrier)
    proof=program(body['regions'],body['pointer'],ctor=ctor,image_base=base,
        disabled=base+collector['result']['disabledFlagRva'],base_slot=16,cache_slot=40)
    initialization=dict(disabledCollector=collector,normalRuntimeHelpersRequired=True,
        genericHeapFieldLayoutAdmitted=False,childWireGrammarAdmitted=False)
    defaults=[dict(offset=84,bytes=4,constantHex='01000000'),dict(offset=88,bytes=1,constantHex='01')]
    if ctor:
        use=derive_typed_usage_context(image,proof['baseAllocation']['site']-base,label='generatedNestedHeaderFactory.baseAllocation')
        need('owned-reference-ancestor-allocation',use['tag']==1 and use['typeName']in original_chain[1:])
        fields=[]
        for owner in wrapper_chain:
            for field in md.fields_for(ctx.index.types[owner]):
                if ctx.field_attributes(field.type_index)&16:continue
                fact=ctx.field(owner+'::'+md.string(field.name_index))
                if fact[2]==16 and fact[1]==use['typeName']:fields.append(fact)
        need('one-compatible-inherited-holder',len(fields)==1)
        initialization['baseInitialization']=dict(allocation=use,holderField=fields[0],
            constants=[life._bind_factory_constant(image,ctx,use['typeName'],s)for s in defaults],
            overwrittenBeforeNormalReturn=True,wholeSameAllocatedReferenceStored=True)
        actual=proof['ancestorConstructor']['target'];matches=[]
        for owner in original_chain[1:]:
            matches.extend((owner,m)for m in md.methods_for(ctx.index.types[owner])
                if md.string(m.name_index)=='.ctor'and m.parameter_count==0 and image.method_pointer_va(m)==actual)
        need('one-actual-named-ancestor-constructor',len(matches)==1)
        owner,method=matches[0]
        initialization['calledAncestorConstructor']=life._original_constructor(image,ctx,method,owner,pins=pins)
        initialization['calledAncestorConstructor']['selectedCall']=proof['ancestorConstructor']
    else:
        record=proof['nestedInitialization'];fields=[]
        for owner in original_chain:
            for field in md.fields_for(ctx.index.types[owner]):
                if ctx.field_attributes(field.type_index)&16:continue
                fact=ctx.field(owner+'::'+md.string(field.name_index))
                if fact[2]==record['referenceOffset']:fields.append((fact,field))
        need('one-exact-validation-child-field',len(fields)==1)
        field,declared=fields[0];closed=closed_generic_reference_extent(ctx,declared.type_index)
        need('closed-Boolean-Param-child',closed['type']==field[1]=='Beyond.Gameplay.Actions.Param`1<bool>'
            and closed['argumentTypes']==['bool'])
        ready=derive_typed_usage_context(image,record['classUsage']['site']-base,label='generatedNestedHeaderFactory.childClass')
        request=derive_typed_usage_context(image,record['contextUsage']['site']-base,label='generatedNestedHeaderFactory.childContext')
        definition=closed['definitionTypeIndex']
        need('same-closed-child-class',ready['tag']==1 and ready['typeName']==closed['type'])
        need('same-closed-child-context',request['tag']==6 and request['typeName']=='Beyond.Gameplay.Actions.Param`1'
            and request['methodName']=='op_Implicit'and request['methodSpec'][2]==-1
            and request['classArguments']==['bool']and request['methodArguments']==[]
            and md.methods[request['methodSpec'][0]].declaring_type==definition)
        symbols=ContextSymbols(image)
        context=symbols.context(definition,slots=[record['contextIndex']]);slot,=context['entries']
        shape=slot.get('type',{});arguments=shape.get('classArguments',[])
        need('reciprocal-own-Param-context-slot',slot['relativeSlot']==record['contextIndex']==5
            and slot['kind']==2 and shape.get('definition',{}).get('name')=='Beyond.Gameplay.Actions.Param`1'
            and shape['definition'].get('rawHex')==closed['definitionTypeRecordHex']
            and len(arguments)==1 and arguments[0].get('parameterOwner',{}).get('typeIndex')==definition
            and arguments[0]['parameterOwner'].get('ordinal')==0)
        method=md.methods[request['methodSpec'][0]];parameters=list(md.parameters_for(method))
        need('own-nongeneric-implicit-method-shape',method.generic_container_index<0 and method.flags&16
            and method.parameter_count==len(parameters)==1)
        parameter=symbols.type(ctx.type_pointer(parameters[0].type_index))
        returned=symbols.type(ctx.type_pointer(method.return_type))
        need('same-reciprocal-implicit-argument',parameter.get('parameterOwner',{}).get('typeIndex')==definition
            and parameter['parameterOwner'].get('ordinal')==0
            and parameter['typePointerVa']==arguments[0]['typePointerVa']
            and bytes.fromhex(parameter['rawHex'])[10:12]==bytes((19,0)))
        need('same-formal-return-and-context-slot',returned.get('definition',{}).get('rawHex')==closed['definitionTypeRecordHex']
            and returned.get('classArguments')==arguments
            and bytes.fromhex(returned['rawHex'])[10:12]==bytes((21,0)))
        def closed_arguments(pointer):
            raw=image.pe.bytes_at_va(pointer,16)
            need('ordinary-actual-child-class-record',raw[10:12]==bytes((21,0)))
            carrier=int.from_bytes(raw[:8],'little')
            own_definition=image.pe.bytes_at_va(image.pe.u64_at_va(carrier),16)
            need('same-actual-child-class-definition',own_definition.hex().upper()==closed['definitionTypeRecordHex'])
            return [a.type_pointer_va for a in image.instantiations.resolve_pointer(image.pe.u64_at_va(carrier+8)).arguments]
        actual_arguments=[a.type_pointer_va for a in image.instantiations.resolve(request['methodSpec'][1]).arguments]
        need('same-exact-closed-argument-pointers',len(actual_arguments)==1
            and actual_arguments==closed_arguments(ctx.type_pointer(declared.type_index))
            ==closed_arguments(ctx.type_pointer(ready['typeIndex'])))
        bool_record=_boolean_argument(image,actual_arguments[0])
        initialization['childInitialization']=dict(referenceField=field,closedReference=closed,
            classUsage=ready,typedContext=request,classContext=context,
            implicitMethodDeclaration=dict(methodIndex=method.index,parameter=parameter,returned=returned,
                closedArgumentPointers=actual_arguments,closedArgumentRawHex=bool_record.hex().upper()),
            initializedIndexedClassSource=life._initialized_indexer(image,record['indexedClassHelper']),
            rawFreshAllocationStores=record['rawStores'],rawStoreEvidence='structuralOnly',
            genericHeapFieldLayoutAdmitted=False,childConstructorInvoked=False,
            normalZeroedCompatibleClosedParamStorageRequired=True,
            actualRuntimeMethodInfoClassBindingRequired=True,
            selectedContextSlotEqualsClosedChildRequired=True,
            actualInflatedClassAndContextBindingObserved=False)
        initialization['originalConstants']=[life._bind_factory_constant(image,ctx,wrapper.wrapped_type,s)for s in defaults]
    return proof,initialization
