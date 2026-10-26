"""Nominal BuffInput inherited-holder/cache and setter source transfers.

BuffInput's typed cache lives at24 while its actual inherited BuffInputBase
holder lives at16. A coherent cache returns the same original; a stale/empty
cache checks the selected concrete class and refreshes or clears it before
return. The setter preserves incoming bits across that getter and stores into
the actual original field. These paths do not identify a wire grammar or make
an unrelated inherited wrapper interchangeable. Normal compatible class-test,
collector and metadata effects, exact owned nominal contexts and stable
disjoint objects are conditions; runtime invocation remains unobserved.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_record_sources import branch
import json

LABEL='skillRootBuffInputSources'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def cached_getter_program(regions,entry,s,*,cache='coherent',original_null=False,compatible=True):
    """Exact same-wrapper get___instance source, all selected cache states."""
    need('cache-state',True,cache in('coherent','empty','stale'))
    need('literal-getter-paths',True,type(original_null)is bool and type(compatible)is bool)
    need('coherent-cache-nonnull',False,cache=='coherent'and original_null)
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    g.take('48837b1800');g.branch('74',cache=='empty',1)
    if cache!='empty':
        g.take('488b4310','48394318');g.branch('75',cache=='stale',1)
    usages=[]
    if cache!='coherent':
        g.take('48897c2430','488b7b10','4885ff');g.branch('74',original_null,1)
        if original_null:
            g.take('33c0','488d4b18','48894318');g.call(s['barrier'])
            g.take('488b7c2430');g.jump('eb',1)
        else:
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.take('488b0f');g.call(s['assignable']);g.take('84c0');g.branch('74',not compatible,1)
            if compatible:g.take('488bc7')
            else:g.take('33c0');g.jump('eb',1)
            g.take('48894318');at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.take('488b0f');g.call(s['assignable'])
            g.take('488d4b18');g.call(s['barrier']);g.take('488b7c2430');g.jump('eb',1)
            need('same-concrete-class-cell',usages[0]['cell'],usages[1]['cell'])
    g.take('488b4318','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheState=cache,
        originalNull=None if cache=='coherent'else original_null,
        compatible=None if cache=='coherent'or original_null else compatible,
        originalHolderOffset=16,typedCacheOffset=24,concreteClassUsages=usages,
        returnedReference='same nonnull original'if cache=='coherent'or(not original_null and compatible)else'null',
        normalReturn=True,wireBytes=0)


def getter_setter_program(regions,entry,s,*,kind,field_offset):
    """Preserved DL/RDX across exact typed getter, then own original field."""
    need('owned-setter-kind',True,kind in('bool','reference'))
    need('bounded-setter-field',True,type(field_offset)is int and 16<=field_offset<128)
    g=BytesPath(regions,entry);g.take('4053','4883ec20')
    g.take('0fb6da'if kind=='bool'else'488bda','33d2');g.call(s['getter'])
    g.take('4885c0');g.branch('74',False,1)
    slot=bytes((field_offset,)).hex()
    if kind=='bool':
        g.take('8858'+slot,'4883c420','5b','c3');barrier=None
    else:
        g.take('488d48'+slot,'488958'+slot,'4883c420','5b');barrier=g.relative('e9')
        need('actual-reference-setter-barrier',s['barrier'],barrier)
    return dict(selectedBytes=g.seen,kind=kind,fieldOffset=field_offset,
        unchangedInputRegister='dl'if kind=='bool'else'rdx',savedInputRegister='bl'if kind=='bool'else'rbx',
        getterResult='rax exact typed original',storedBytes=1 if kind=='bool'else 8,
        barrier=barrier,normalReturn=True,wireBytes=0)


def buff_input_program(regions,entry,s,*,new=False,null=False):
    """Own MC3/FF including actual existing-wrapper preparation and new path."""
    need('literal-record-paths',True,type(new)is bool and type(null)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2418','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False)
    g.take('488b0b','c644243800','4885c9');g.branch('74',new,1)
    if not new:g.take('33d2');g.call(s['prepare'])
    g.take('488d542438','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None;context=None;events=[]
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742430','48833b00');g.branch('0f84',new)
        if new:
            usage=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
            g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=usage,cell=cell)
        g.take('0fb6742438','4080fe03');g.branch('0f85',False)
        g.take('488b33','488bcf');at=g.at;g.call(s['boolean']);g.take('4885f6');g.branch('74',False,1)
        g.take('4533c0','0fb6d0','488bce');setter=g.at;g.call(s['setAssign'])
        events.append(dict(fieldName='assignBlackboard',kind='bool',sourceCall=at,sourceTarget=s['boolean'],setterCall=setter,setterTarget=s['setAssign']))
        usage=g.at;cell=g.relative('488b15');context=dict(instruction=usage,cell=cell)
        g.take('488bcf','488b33');at=g.at;g.call(s['list']);g.take('4885f6');g.branch('74',False,1)
        g.take('4533c0','488bd0','488bce');setter=g.at;g.call(s['setItems'])
        events.append(dict(fieldName='assignItems',kind='list',sourceCall=at,sourceTarget=s['list'],typedContext=context,setterCall=setter,setterTarget=s['setItems']))
        g.take('488b1b','488bcf');at=g.at;g.call(s['pool']);g.take('4885db');g.branch('74',False,1)
        g.take('4533c0','488bd0','488bcb');setter=g.at;g.call(s['setId'])
        events.append(dict(fieldName='buffId',kind='pooled-string',sourceCall=at,sourceTarget=s['pool'],setterCall=setter,setterTarget=s['setId']))
        g.take('488b742430')
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        memberCount=None if null else 3,orderedFields=events,newAllocationUsage=allocation,
        actualPrepareTarget=s['prepare'],prepareReceivesExistingWrapperOnly=True,
        prepareReceivesNoReader=True,normalReturn=True,entryRspRestored=True,
        childGrammarsAdmitted=False)


def derived_cached_getter_program(regions,entry,s,*,cache='coherent',cache_offset=32):
    """Exact nullable-cast refresh of a distinct named cache24/32 and holder16."""
    need('derived-cache-state',True,cache in('coherent','empty','stale'))
    need('explicit-derived-cache-slot',True,type(cache_offset)is int and cache_offset in(24,32))
    slot=bytes((cache_offset,)).hex()
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    g.take('48837b'+slot+'00');g.branch('0f84',cache=='empty')
    if cache!='empty':g.take('488b4310','483943'+slot);g.branch('0f85',cache=='stale')
    usages=[]
    if cache!='coherent':
        at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
        g.take('48897c2430','488b7b10','488bcf');g.call(s['cast'])
        g.take('488943'+slot,'488bcf');at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
        g.call(s['cast']);g.take('488d4b'+slot);g.call(s['barrier'])
        g.take('488b7c2430');g.jump('e9')
        need('same-derived-class-cell',usages[0]['cell'],usages[1]['cell'])
    g.take('488b43'+slot,'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheState=cache,
        originalHolderOffset=16,typedCacheOffset=cache_offset,concreteClassUsages=usages,
        returnedReference='same original for coherent cache; exact typed nullable cast result on refresh',
        normalReturn=True,wireBytes=0,castHelperSemanticsAdmitted=False)


def typed_cached_constructor_program(regions,entry,s,*,cache_offset=24,base_constructor=False):
    """Whole compatible fresh constructor, preserving distinct inherited caches."""
    need('exact-nominal-cache-slot',True,type(cache_offset)is int and cache_offset in(24,32))
    need('literal-base-constructor-choice',True,type(base_constructor)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('0f84',False)
    base_usage=g.at;base_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    if base_constructor:g.take('33d2','488bcb');g.call(s['baseConstructor'])
    original_usage=g.at;original_cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('488bf8','4885c0');g.branch('0f84',False)
    g.take('33d2','4889742430','488bc8');g.call(s['originalConstructor'])
    slot=bytes((cache_offset,)).hex()
    g.take('488d4b'+slot,'48897b'+slot);g.call(s['barrier'])
    g.take('488d4b10','48897b10');g.call(s['barrier'])
    g.take('488b7b10');class_site=g.at;class_cell=g.relative('488b35')
    g.take('4885ff');g.branch('0f84',False)
    g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('48897b'+slot);again=g.at;again_cell=g.relative('488b35')
    need('constructor-same-concrete-class-cell',class_cell,again_cell)
    g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('488d4b'+slot,'488b742430','488b5c2438','4883c420','5f')
    need('constructor-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheOffset=cache_offset,
        baseClassUsage=dict(instruction=base_usage,cell=base_cell),
        originalClassUsage=dict(instruction=original_usage,cell=original_cell),
        concreteClassUsages=[dict(instruction=class_site,cell=class_cell),dict(instruction=again,cell=again_cell)],
        baseConstructorInvoked=base_constructor,baseHolderOffset=16,
        ownCacheAndBaseHolderReceiveSameOriginal=True,normalReturnViaBarrier=True,
        inheritedOtherCachesNotEquated=True,wireBytes=0)


def prepare_program(regions,entry,s,*,cache_empty=False,original_null=False):
    """OnDeserialized's actual pre-header cache preparation, not a wire read."""
    need('literal-prepare-paths',True,type(cache_empty)is bool and type(original_null)is bool)
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    g.take('48837b1800');g.branch('0f84',cache_empty)
    usages=[]
    if cache_empty:
        g.take('48837b1000');g.branch('0f84',original_null)
        if not original_null:
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.take('48897c2430','488b7b10','488bcf');g.call(s['cast'])
            g.take('48894318','488bcf');at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.call(s['cast']);g.take('488d4b18');g.call(s['barrier'])
            g.take('488b7c2430');g.jump('e9')
            need('prepare-same-concrete-class-cell',usages[0]['cell'],usages[1]['cell'])
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheEmpty=cache_empty,
        originalNull=original_null if cache_empty else None,concreteClassUsages=usages,
        originalHolderOffset=16,typedCacheOffset=24,originalHolderUnchanged=True,
        noReaderArgument=True,wireBytes=0,normalReturn=True,castHelperSemanticsAdmitted=False)


def nullable_class_cast_program(regions,entry,predicate,*,null=False):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','4885c9');g.branch('74',null,1)
    if null:g.take('33c0')
    else:
        g.take('488b09');g.call(predicate)
        g.take('33c9','84c0','480f44d9','488bc3')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,originalNull=null,
        result='null'if null else'original pointer iff exact class predicate AL, otherwise null',
        sameTargetClassPassedToPredicate=True,normalReturn=True)


def compatible_class_program(regions,entry,target_ready):
    """Initialized class flag4/hierarchy predicate, not a name-based cast."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','488bfa','488bd9','0fb6813a010000','90','a804')
    g.branch('75',True,1);g.take('488bcf');g.call(target_ready)
    g.take('0fb68732010000','388332010000');g.branch('72',False,1)
    g.take('0fb6c8','488b83c8000000','48397cc8f8');g.branch('75',False,1)
    g.take('b001','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,result='AL true for actual hierarchy depth/table entry matching exact target class',
        actualClass='incoming rcx preserved rbx',targetClass='incoming rdx preserved rdi',
        initializedActualClassFlagBit=4,hierarchyDepthOffset=306,hierarchyOffset=200,
        normalReturn=True,runtimeHierarchyCoherenceRequired=True)


def derive_buff_input(image,pins):
    """Fresh exact MC3 caller/cache/setters; AssignPair child is still separate."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned,methods,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_fast_barrier
    from scripts.game_data.memorypack import primitive_param,pooled_source_helper,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
    selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    type_name='Beyond.Gameplay.Core.BuffInput';wrapper_name='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputForMemoryPack'
    pair=derive_pair(image,type_name,wrapper_name);w,=[w for w in image.memorypack_wrappers.values()if w.name==wrapper_name]
    need('exact-buff-input-members',[('assignBlackboard','bool'),('assignItems','System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>'),('buffId','string')],
        [(m.name,m.declared_type)for m in w.members])
    need('actual-wrapper-parent','Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputBaseForMemoryPack',ctx.parent(w.name))
    need('actual-original-parent','Beyond.Gameplay.Core.BuffInputBase',ctx.parent(type_name))
    holders={}
    for owner,expected,slot in((ctx.parent(w.name),ctx.parent(type_name),16),(w.name,type_name,24)):
        own=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)in INSTANCE_FIELD_NAMES and not ctx.field_attributes(f.type_index)&16]
        need('unique-owned-instance-cache:'+owner,1,len(own));fd=own[0];name=md.string(fd.name_index)
        actual=ctx.field(owner+'::'+name);need('owned-instance-cache-type-slot',(owner,expected,slot),actual)
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),18,LABEL+'.holder',reference=True)
        holders[owner]=dict(fieldName=name,typeName=expected,offset=slot)
    mm=methods(image,w);primitive_param.reader_abi(image,ctx,mm['Deserialize'],w)
    for name in('GetValue','get___instance'):
        scalar.owned_method_abi(image,ctx,mm[name].index,w.type_definition,(type_name,18,False),[],LABEL+'.'+name)
    s={name:image.method_pointer_va(mm[method])for name,method in dict(getter='get___instance',constructor='.ctor',
        prepare='OnDeserialized',setAssign='set___assignBlackboard__',setItems='set___assignItems__',setId='set___buffId__').items()}
    sources={name:owned(image,target)for name,target in s.items()};sources['reader']=owned(image,image.method_pointer_va(mm['Deserialize']))
    def call(body,offset):
        row,=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('owned-direct-call',(5,232),(len(raw),raw[0]))
        return control_transfer(row)['target']
    s.update(header=call(sources['reader'],57),boolean=call(sources['reader'],106),list=call(sources['reader'],143),
        pool=call(sources['reader'],173),assignable=call(sources['getter'],69),barrier=call(sources['getter'],104),
        allocate=call(sources['constructor'],53))
    original_ctor,=[m for m in md.methods_for(ctx.index.types[type_name])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,original_ctor.index,original_ctor.declaring_type,('void',1,False),[],LABEL+'.originalConstructor')
    for name in('.ctor','OnDeserialized'):
        scalar.owned_method_abi(image,ctx,mm[name].index,w.type_definition,('void',1,False),[],LABEL+'.'+name)
    s['originalConstructor']=image.method_pointer_va(original_ctor)
    casts={control_transfer(row)['target']for i,row in enumerate(sources['prepare']['rows'])if i and
        bytes.fromhex(row['bytes'])[:1]==b'\xe8'and bytes.fromhex(sources['prepare']['rows'][i-1]['bytes'])==bytes.fromhex('488bcf')}
    need('one-actual-nullable-class-cast',1,len(casts));s['cast']=next(iter(casts))
    for role in('assignable','cast'):sources[role]=owned(image,s[role])
    programs=[buff_input_program(sources['reader']['regions'],sources['reader']['pointer'],s,**path)
        for path in({},{'new':True},{'null':True},{'new':True,'null':True})]
    getters=[cached_getter_program(sources['getter']['regions'],s['getter'],s,cache=cache,**path)
        for cache in('coherent','empty','stale')
        for path in(({},)if cache=='coherent'else({},{'original_null':True},{'compatible':False}))]
    constructor=typed_cached_constructor_program(sources['constructor']['regions'],s['constructor'],s)
    prepares=[prepare_program(sources['prepare']['regions'],s['prepare'],s,**path)
        for path in({},{'cache_empty':True},{'cache_empty':True,'original_null':True})]
    offsets=scalar.reader_offsets(image,LABEL);record=vector_recorder(image)
    header=record(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    boolean=record(s['boolean']-base);scalar.boolean_source(image,boolean,offsets,LABEL+'.boolean')
    pool=pooled_source_helper.validate_on_image(image,s['pool'],pins)
    entry=image.method_pointer_va(mm['GetValue'])
    thunk=bytes.fromhex('33D2E9')+(s['getter']-(entry+7)).to_bytes(4,'little',signed=True)
    need('same-wrapper-getvalue-tail',thunk,image.pe.bytes_at_va(entry,7))
    getter_forward=dict(entryRva=entry-base,bytesHex=thunk.hex().upper(),targetRva=s['getter']-base,
        sameWrapperNamedGetter=True,wireBytes=0,physicalExtentProved=False)
    barriers,barrier_proof,_=_fast_barrier(image,s['barrier'])
    typed_classes=[]
    for program in getters+prepares+[constructor]:
        usages=program.get('concreteClassUsages',[])
        if program is constructor:usages=usages+[constructor['originalClassUsage']]
        for u in usages:
            usage=derive_typed_usage_context(image,u['instruction']-base,label=LABEL+'.class')
            need('exact-concrete-class',(1,type_name),(usage['tag'],usage['typeName']))
            scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.class',reference=True)
            typed_classes.append(usage)
    allocation=derive_typed_usage_context(image,programs[1]['newAllocationUsage']['instruction']-base,label=LABEL+'.wrapperAllocation')
    need('new-wrapper-class',(1,w.name),(allocation['tag'],allocation['typeName']))
    original_base=derive_typed_usage_context(image,constructor['baseClassUsage']['instruction']-base,label=LABEL+'.baseClass')
    need('base-wrapper-ready-class',(1,ctx.parent(w.name)),(original_base['tag'],original_base['typeName']))
    typed_list=derive_typed_usage_context(image,programs[0]['orderedFields'][1]['typedContext']['instruction']-base,label=LABEL+'.assignItems')
    bind_typed_read(image,typed_list,method_name='ReadPackable',argument='System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>',kind=21,reference=True)
    clones=ec.clone_facts(image,pins);need('exact-list-reference-clone',clones['ReadPackable']['targetRva'],s['list']-base)
    setters={};fields=[]
    for name,kind,role,offset in(('assignBlackboard','bool','setAssign',24),('assignItems','reference','setItems',32),('buffId','reference','setId',16)):
        actual=ctx.field(type_name+'::'+name);need('named-original-field-offset',offset,actual[2])
        setter=mm[{'setAssign':'set___assignBlackboard__','setItems':'set___assignItems__','setId':'set___buffId__'}[role]]
        scalar.owned_method_abi(image,ctx,setter.index,w.type_definition,('void',1,False),
            [(actual[1],{'assignBlackboard':2,'assignItems':21,'buffId':14}[name],False)],LABEL+'.setter.'+name)
        setters[name]=getter_setter_program(sources[role]['regions'],s[role],s,kind=kind,field_offset=offset)
        fd,=[f for f in md.fields_for(ctx.index.types[type_name])if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),{'assignBlackboard':2,'assignItems':21,'buffId':14}[name],LABEL+'.field',reference=kind=='reference')
        fields.append(dict(fieldName=name,typeName=actual[1],offset=offset))
    cast=[nullable_class_cast_program(sources['cast']['regions'],s['cast'],s['assignable'],null=null)for null in(False,True)]
    target_ready,=[control_transfer(row)['target']for i,row in enumerate(sources['assignable']['rows'])if i and
        bytes.fromhex(row['bytes'])[:1]==b'\xe8'and bytes.fromhex(sources['assignable']['rows'][i-1]['bytes'])==bytes.fromhex('488bcf')]
    predicate=compatible_class_program(sources['assignable']['regions'],s['assignable'],target_ready)
    forwarding=registered_pair(image,pair,w,label=LABEL+'.registered')
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-input-source.v1',nativeInputs=pins,
        status='proved-buff-input-caller-requires-assign-pair-list',typeName=type_name,wrapperName=w.name,
        registeredPair=pair,forwarding=forwarding,programs=programs,getterPrograms=getters,getterForwarder=getter_forward,
        constructorProgram=constructor,preparePrograms=prepares,setterPrograms=setters,fields=fields,holders=holders,
        concreteClassUsages=typed_classes,allocationUsage=allocation,baseClassUsage=original_base,
        booleanSource=boolean,headerSource=header,pooledSource=pool,
        sourceWindows={name:body['windows']for name,body in sources.items()},
        barrier=barriers,barrierProof=barrier_proof,castPrograms=cast,classPredicate=predicate,
        symbolRvas={name:target-base for name,target in s.items()},
        requiredChildJoins=[dict(fieldName='assignItems',typeName='System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>',
            typedRequest=typed_list,sourceTargetRva=s['list']-base,elementGrammarAdmitted=False)],
        positiveAbstractBuffInputBaseAdmitted=False,wholeRecordAdmitted=False,
        evidenceBoundary=dict(exact='BuffInput MC3/FF source, own and inherited typed holders/cache, complete compatible constructor, coherent/empty/stale/nullable cache paths, original class-hierarchy cast, actual pre-header cache preparation, preserved bool/reference setters and selected source returns.',
            conditional=__doc__,unresolved=['positive AssignPair list/value adapter','CreateBuffActionInput sibling and abstract union composition','runtime formatter selection','enclosing root/EOF']))))
