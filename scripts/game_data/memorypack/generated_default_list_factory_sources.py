"""Owned cached factories with an inlined empty reference-list constructor.

The byte program proves the selected initialized, nonnull, disabled-collector
path. Actual Original/list classes, constructor MethodInfo, reciprocal VAR
context, fields and indexed class helper are joined separately on that image.
No cold, allocation, live context or child wire effects are inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE = 'Beyond.Gameplay.Actions.ServerGameTimeResume'
# These are candidate selectors, not admitted layouts or native proofs. Each
# selected owner must pass the full unchanged caller program and all fresh
# nominal, field, constructor/context and helper joins below.
TYPES = (TYPE, 'Beyond.Gameplay.Actions.RecoverInnMainHud',
         'Beyond.Gameplay.Actions.ServerGameTimePause')
PROFILE = 'initialized-inline-default-list-factory.v1'


def need(check, value, detail=''):
    if not value:
        raise ValueError('generatedDefaultListFactory.'+check+(':'+str(detail)[:600] if detail else ''))


def program(regions, entry, *, ctor, image_base, disabled, base_slot, cache_slot):
    need('literal-roles', type(ctor) is bool and (base_slot,cache_slot)==(16,32)
         and all(type(n) is int and n>0 for n in (image_base,disabled)))
    g=BytesPath(regions,entry)
    g.take('4053','55', *(['56','57','4156','4883ec40'] if ctor else ['4156','4883ec40']))
    flag=g.relative('803d')+1;g.take('00')
    need('own-image-base',g.relative('4c8d35')==image_base)
    g.take('488be9');g.branch('0f85',True)
    ancestor=None;ancestor_ctor=None
    if ctor:
        ancestor=dict(site=g.at,cell=g.relative('488b0d'))
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('33d2','488bcd');ancestor_ctor=g.relative('e8')
    allocation=dict(site=g.at,cell=g.relative('488b0d'))
    if not ctor:g.take('48897c2468')
    allocator=g.relative('e8');g.take('488bd8','4885c0');g.branch('0f84',False)
    defaults=[dict(offset=96,bytes=4,constantHex='FFFFFFFF'),
              dict(offset=84,bytes=4,constantHex='01000000'),
              dict(offset=88,bytes=1,constantHex='01')]
    g.take('c74060ffffffff')
    child=dict(site=g.at,cell=g.relative('488b0d'));g.call(allocator)
    g.take('488bf8','4885c0');g.branch('0f84',False)
    if ctor:
        context=dict(site=g.at,cell=g.relative('488b35'));g.take('33d2')
    else:
        g.take('4889742460','33d2');context=dict(site=g.at,cell=g.relative('488b35'))
    g.take('488b4e20','488b89c0000000');indexer=g.relative('e8')
    g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b4e20','33d2','488b89c0000000');g.call(indexer)
    if not ctor:g.take('488b742460')
    g.take('488b88b8000000','488b01','48894710')
    need('same-list-items-disabled-collector',g.relative('8b05')==disabled)
    g.take('85c0');g.branch('74',True,1)
    # The taken first JE skips the second collector reload. EAX still holds
    # the same tested zero across this whole-reference store.
    g.take('48897b78','85c0');g.branch('74',True,1)
    g.take('4533c0','c7435401000000','488bd3','c6435801','488bcd');setter=g.relative('e8')
    g.take('488b5d10');first=dict(site=g.at,cell=g.relative('488b3d'))
    g.take('4885db');g.branch('0f85' if ctor else '75',True,4 if ctor else 1)
    g.take('488b0b','488bd7');predicate=g.relative('e8');g.take('84c0');g.branch('74',False,1)
    g.take('48895d20');second=dict(site=g.at,cell=g.relative('488b3d'))
    g.take('488b0b','488bd7');g.call(predicate);g.take('84c0');g.branch('74',False,1)
    g.jump('e9' if ctor else 'eb',4 if ctor else 1)
    need('same-cache-disabled-collector',g.relative('833d')+1==disabled)
    g.take('00');g.branch('74',True,1)
    if not ctor:g.take('488b7c2468')
    g.take('4883c440','415e', *(['5f','5e'] if ctor else []),'5d','5b','c3')
    need('same-own-class-cast-cells',first['cell']==second['cell']==allocation['cell'])
    restored=['rbx','rbp','r14','rsi','rdi']
    return dict(selectedBytes=g.seen,factoryProfile=PROFILE,
        holderSourceProfile='rsi-wrapper-rbp-image-base-inline-collector',
        initializedFlag=flag,constructor=ctor,allocation=allocation,allocationTarget=allocator,
        baseClassUsage=ancestor,ancestorClassUsages=[],baseReady=None,baseConstructorTarget=ancestor_ctor,
        instanceSetter=setter,strictCast=None,classUsages=[first,second],
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        inlineStrictCasts=dict(sameBaseReferenceCached=True,successfulPredicateConditional=True,
            runtimePredicateOutcomeObserved=False,predicateTarget=predicate,
            entryRspRestored=True,nonvolatilesRestored=restored),
        originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,
        disabledCollectorCell=disabled,entryRspRestored=True,nonvolatileRegistersRestored=restored,
        originalConstants=defaults,childAllocation=child,childMethodContext=context,
        childReferenceOffset=120,childItemsOffset=16,childClassContextSlot=0,staticEmptyArraySlot=0,
        initializedClassResolver=indexer,childWireGrammarAdmitted=False,
        actualInflatedClassAndContextBindingObserved=False,
        condition='Initialized own metadata/classes and actual closed List constructor context; '
            'nonnull compatible zeroed Original/list allocations, coherent selected static empty array, '
            'successful own class predicates and disabled collector. Cold paths, allocation effects, '
            'live inflated context identity and child wire grammar remain independent.')


def derive_program(image,pins,ctx,wrapper,body,barrier,*,original_chain,wrapper_chain):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    need('finite-current-owner',wrapper.wrapped_type in TYPES)
    base=image.pe.image_base;md=image.metadata
    methods=[m for m in md.methods_for(md.types[wrapper.type_definition])
        if image.method_pointer_va(m)==body['pointer'] and md.string(m.name_index) in ('.ctor','CreateInstance')]
    need('one-owned-current-factory',len(methods)==1)
    collector=_barrier(image,barrier);disabled=base+collector['result']['disabledFlagRva']
    proof=program(body['regions'],body['pointer'],ctor=md.string(methods[0].name_index)=='.ctor',
        image_base=base,disabled=disabled,base_slot=16,cache_slot=32)
    allocation=derive_typed_usage_context(image,proof['childAllocation']['site']-base,label='generatedDefaultListFactory.child')
    request=derive_typed_usage_context(image,proof['childMethodContext']['site']-base,label='generatedDefaultListFactory.context')
    list_type='System.Collections.Generic.List`1<int>';owner=ctx.index.types['System.Collections.Generic.List`1']
    need('own-closed-list-constructor',allocation['tag']==1 and allocation['typeName']==list_type
        and request['tag']==6 and request['typeName']=='System.Collections.Generic.List`1'
        and request['methodName']=='.ctor' and request['classArguments']==['int']
        and request['methodArguments']==[] and request['methodSpec'][2]==-1)
    method=md.methods[request['methodSpec'][0]]
    need('own-nongeneric-constructor-definition',method.declaring_type==owner.index and method.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,method.index,owner.index,('void',1,False),[],'generatedDefaultListFactory.ctor')
    raw=bytes.fromhex(allocation['typeRawHex']);need('constructed-list-class',raw[10:12]==bytes((21,0)))
    carrier=int.from_bytes(raw[:8],'little')
    actual=[a.type_pointer_va for a in image.instantiations.resolve_pointer(image.pe.u64_at_va(carrier+8)).arguments]
    expected=[a.type_pointer_va for a in image.instantiations.resolve(request['methodSpec'][1]).arguments]
    need('same-actual-closed-argument-pointers',len(actual)==1 and actual==expected)
    scalar.ordinary(image,actual[0],8,'generatedDefaultListFactory.Int32')
    context=ContextSymbols(image).context(owner.index)
    slot,=[s for s in context['entries'] if s['relativeSlot']==0]
    shape=slot.get('type',{});args=shape.get('classArguments',[])
    need('reciprocal-constructor-class-context',slot['kind']==2 and shape.get('definition',{}).get('name')=='System.Collections.Generic.List`1'
        and len(args)==1 and args[0].get('parameterOwner',{}).get('typeIndex')==owner.index
        and args[0]['parameterOwner'].get('ordinal')==0)
    static=[f for f in md.fields_for(owner) if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
    need('one-stored-list-static-reference',len(static)==1)
    field=static[0];record=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    need('same-empty-array-formal-VAR',record[10:12]==bytes((29,0))
        and int.from_bytes(record[:8],'little')==args[0]['typePointerVa'])
    fields=[]
    for name in original_chain:
        for f in md.fields_for(ctx.index.types[name]):
            if ctx.field_attributes(f.type_index)&16:continue
            fact=ctx.field(name+'::'+md.string(f.name_index))
            if fact[2]==proof['childReferenceOffset']:
                scalar.ordinary(image,ctx.type_pointer(f.type_index),21,'generatedDefaultListFactory.field',reference=True)
                need('same-nominal-list-field',fact[1]==list_type);fields.append(fact)
    need('one-owned-list-reference-field',len(fields)==1)
    return proof,dict(disabledCollector=collector,
        originalConstants=[life._bind_factory_constant(image,ctx,wrapper.wrapped_type,s) for s in proof['originalConstants']],
        inlineListInitialization=dict(allocation=allocation,constructorMethodInfo=request,classContext=context,
            parentReferenceField=fields[0],staticEmptyArrayField=dict(name=md.string(field.name_index),
                typeName=ctx.type_name(field.type_index),rawTypeHex=record.hex().upper()),
            initializedContextHelper=life._initialized_indexer(image,proof['initializedClassResolver']),
            sameActualClosedArgumentPointers=actual,selectedSource=proof,
            registeredNativeEntryIdentityClaimed=False,openGenericFieldOffsetsUsed=False,
            childWireGrammarAdmitted=False,actualInflatedContextBindingObserved=False))
