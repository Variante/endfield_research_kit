"""Exact BlackboardBuffId descendant of the selected string/string base.

The inherited field setters are composed from a fresh BlackboardString proof.
Constructed generic names are never installed as aliases for an open TypeDef.
The child has its own cache32, while the base cache24 remains a distinct value.
Its Original constructor is an exact receiver-preserving tail into the named
BlackboardString constructor. The MC3 wire is pooled key4, Boolean1, pooled
value4; neither its name nor either managed cache supplies that grammar.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull

TYPE='Beyond.Gameplay.Core.Conditions.BlackboardBuffId'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_BlackboardBuffIdForMemoryPack'
CAPABILITY='skill-blackboard-buff-id'


def need(key,condition,detail=None):
    if not condition:raise ValueError('blackboardBuffIdSource.'+key+':'+str(detail)[:700])


def call(g,s,role):
    at=g.at;target=g.relative('e8')
    need('exact-call:'+role,target==s[role],dict(instructionVa=at,expectedTargetVa=s[role],actualTargetVa=target))


def constructor_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('0f84',False)
    at=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('33d2','488bcb');call(g,s,'baseConstructor')
    allocation=g.at;alloc_cell=g.relative('488b0d');call(g,s,'allocate');g.take('488bf8','4885c0');null_exit=_nonnull(g)
    g.take('33d2','488bc8');call(g,s,'originalConstructor')
    g.take('4533c0','488bd7','488bcb');call(g,s,'instanceSetter')
    g.take('488b7b10');first=g.at;concrete=g.relative('488b15');g.take('488bcf');call(g,s,'strictCast')
    g.take('48894320','488bcf');second=g.at;need('buffId-constructor-same-class',g.relative('488b15')==concrete)
    call(g,s,'strictCast');g.take('488d4b20','488b5c2430','4883c420','5f')
    need('buffId-constructor-tail',g.relative('e9')==s['barrier'])
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,baseClassUsage=dict(instruction=at,cell=cell),
        allocationUsage=dict(instruction=allocation,cell=alloc_cell),concreteClassUsages=[dict(instruction=first,cell=concrete),dict(instruction=second,cell=concrete)],
        originalHolderOffset=16,typedCacheOffset=32,ownCacheAndBaseHolderReceiveSameOriginal=True,
        inheritedCache24Equated=False,ownedAllocationNullExit=null_exit,normalReturnViaBarrier=True,entryRspRestored=True)


def factory_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('75',True,1);at=g.at;cell=g.relative('488b0d');call(g,s,'allocate')
    g.take('488bd8','4885c0');null_exit=_nonnull(g)
    g.take('33d2','488bcb');call(g,s,'originalConstructor')
    g.take('4533c0','488bd3','488bcf');call(g,s,'instanceSetter')
    g.take('488b5f10');first=g.at;concrete=g.relative('488b15');g.take('488bcb');call(g,s,'strictCast')
    g.take('48894720','488bcb');second=g.at;need('buffId-factory-same-class',g.relative('488b15')==concrete)
    call(g,s,'strictCast');g.take('488d4f20','488b5c2430','4883c420','5f')
    need('buffId-factory-tail',g.relative('e9')==s['barrier'])
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,allocationUsage=dict(instruction=at,cell=cell),
        concreteClassUsages=[dict(instruction=first,cell=concrete),dict(instruction=second,cell=concrete)],
        originalHolderOffset=16,typedCacheOffset=32,ownCacheAndBaseHolderReceiveSameOriginal=True,
        inheritedCache24Equated=False,ownedAllocationNullExit=null_exit,normalReturnViaBarrier=True,entryRspRestored=True)


def instance_setter_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895120','4883c120','4c8bca');g.call(barrier)
    g.take('498d4a10','4d894a10','4883c428');need('buffId-setter-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,originalHolderOffset=16,typedCacheOffset=32,wholeIncomingRdxStoredUnchanged=True,
        requiredPreservedAcrossDisabledBarrier=['r9','r10'],inheritedCache24Equated=False,
        normalReturnViaBarrier=True,entryRspRestored=True)


def prepare_program(regions,entry,s,*,cache_empty=False,original_null=False):
    need('buffId-literal-prehook-paths',all(type(x)is bool for x in(cache_empty,original_null))and(cache_empty or not original_null))
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1);g.take('48837b2000');g.branch('0f84',cache_empty)
    usages=[]
    if cache_empty:
        g.take('48837b1000');g.branch('0f84',original_null)
        if not original_null:
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.take('48897c2430','488b7b10','488bcf');g.call(s['cast']);g.take('48894320','488bcf')
            at=g.at;need('buffId-prehook-same-class',g.relative('488b15')==cell);usages.append(dict(instruction=at,cell=cell))
            g.call(s['cast']);g.take('488d4b20');g.call(s['barrier']);g.take('488b7c2430');g.jump('e9')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheEmpty=cache_empty,originalNull=original_null if cache_empty else None,
        concreteClassUsages=usages,originalHolderOffset=16,typedCacheOffset=32,originalHolderUnchanged=True,
        noReaderArgument=True,normalReturn=True,entryRspRestored=True,wireBytes=0)


def reader_program(regions,entry,s,*,new=False,null=False):
    need('buffId-literal-reader-paths',type(new)is bool and type(null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False)
    g.take('488b0b','c644243800','4885c9');g.branch('74',new,1)
    if not new:g.take('33d2');g.call(s['prepare'])
    g.take('488d542438','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
    allocation=None;nulls=[]
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742430','48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');allocation=dict(instruction=at,cell=cell)
            g.call(s['allocate']);g.take('488bf0','4885c0');nulls.append(_nonnull(g))
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('0fb6742438','4080fe03');g.branch('0f85',False)
        for ordinal,(source,setter)in enumerate((('pool','keySetter'),('boolean','useSetter'),('pool','valueSetter'))):
            g.take('488b1b'if ordinal==2 else'488b33','488bcf');g.call(s[source])
            g.take('4885db'if ordinal==2 else'4885f6');nulls.append(_nonnull(g))
            g.take('4533c0','0fb6d0'if ordinal==1 else'488bd0','488bcb'if ordinal==2 else'488bce');g.call(s[setter])
        g.take('488b742430')
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,memberCount=None if null else 3,
        orderedFields=[]if null else['blackboardKey','useBlackboardKey','value'],newAllocationUsage=allocation,
        actualPrepareTarget=s['prepare'],prepareReceivesNoReader=True,wireBytes=1 if null else 10,ownedNullExits=nulls,
        normalReturn=True,entryRspRestored=True,childGrammarsAdmitted=False)


def original_tail_program(raw,entry,target,*,role='original-constructor'):
    need('buffId-literal-tail-role',role in('original-constructor','typed-instance-getter'))
    need('buffId-exact-original-ctor-tail',len(raw)==7 and raw[:3]==b'\x33\xd2\xe9'
        and entry+7+int.from_bytes(raw[3:],'little',signed=True)==target)
    return dict(selectedBytes=[[entry,raw.hex().upper()]],receiverRcxUnchanged=True,unusedMethodInfoEdxZero=True,
        exactNamedTarget=target,targetRole=role,normalReturnViaNamedTarget=True,stackAndNonvolatilesUnchanged=True,
        physicalExtentProved=False,serializedBytes=0)


def derive(image,pins):
    """Fresh exact nominal descendant source; no constructed TypeDef alias."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack import skill_blackboard_string_sources as strings
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_root_buff_input_sources import derived_cached_getter_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    ancestor=strings.derive(image,pins);ap=ancestor['proof']
    need('fresh-string-base',(ancestor['nativeInputs'],ap['closedBase']['name'])==(pins,strings.BASE))
    need('exact-descendant-lineage',(ctx.parent(TYPE),ctx.parent(WRAPPER))==(strings.TYPE,strings.WRAPPER))
    need('reference-original-not-value',not ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE))
    td=ctx.index.types[TYPE]
    need('no-unproved-added-original-fields',not[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16])
    need('distinct-owned-cache32',ctx.field(WRAPPER+'::__realInstance')==(WRAPPER,TYPE,32))
    cache,=[f for f in md.fields_for(ctx.index.types[WRAPPER])if md.string(f.name_index)=='__realInstance']
    scalar.ordinary(image,ctx.type_pointer(cache.type_index),18,'blackboardBuffId.cache32',reference=True)
    wrapper=_selected_wrapper(image,WRAPPER);need('own-reference-wrapper',wrapper.wrapped_type==TYPE and not wrapper.wrapped_is_value_type)
    expected=[('blackboardKey','string'),('useBlackboardKey','bool'),('value','string')]
    need('actual-three-closed-members',[(m.name,m.declared_type)for m in wrapper.members]==expected)
    closed=[]
    for member,owned in zip(wrapper.members,ap['baseSetters'],strict=True):
        need('same-actual-closed-base-setter',member.declaring_wrapper==strings.BASE_WRAPPER
            and member.method_index==owned['method'][0]and owned['declaredBaseField']==member.name
            and owned['closedFieldType']==member.declared_type)
        closed.append(dict(member=member.row(),closedBaseField=owned))
    mm=pointer.methods(image,wrapper)
    bodies={n:pointer.owned(image,image.method_pointer_va(mm[n]))for n in('.ctor','CreateInstance','get___instance','set___instance','OnDeserialized','Deserialize')}
    for name in('.ctor','CreateInstance','OnDeserialized','get___instance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,True)if name in('get___instance','GetValue')else('void',1,False),[],'blackboardBuffId.'+name)
    scalar.owned_method_abi(image,ctx,mm['set___instance'].index,wrapper.type_definition,('void',1,False),[(TYPE,18,True)],'blackboardBuffId.instanceSetter')
    primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    om,=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,om.index,td.index,('void',1,False),[],'blackboardBuffId.originalConstructor')
    original_pointer=image.method_pointer_va(om);original_raw=image.pe.bytes_at_va(original_pointer,7)
    original=original_tail_program(original_raw,original_pointer,ap['originalConstructor']['selectedBytes'][0][0])
    symbols=dict(baseConstructor=ap['constructor']['selectedBytes'][0][0],allocate=ap['constructor']['allocate'],
        originalConstructor=ap['originalConstructor']['selectedBytes'][0][0],instanceSetter=bodies['set___instance']['pointer'],
        strictCast=ap['strictCasts'][0]['selectedBytes'][0][0],cast=ap['casts'][0]['selectedBytes'][0][0],
        barrier=base+ap['barrierWindows']['program'][0][0],prepare=bodies['OnDeserialized']['pointer'],
        constructor=bodies['.ctor']['pointer'],pool=base+ap['primitiveSources']['pool']['sourceHelpers'][0],
        boolean=base+ap['primitiveSources']['boolean']['pointerRva'])
    body=bodies['Deserialize'];symbols['header']=BytesPath(body['regions'],body['pointer']+57).relative('e8')
    for member,owned in zip(wrapper.members,closed,strict=True):
        key={'blackboardKey':'keySetter','useBlackboardKey':'useSetter','value':'valueSetter'}[member.name]
        symbols[key]=base+owned['closedBaseField']['method'][3]
    constructor=constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],symbols)
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'],symbols)
    setter=instance_setter_program(bodies['set___instance']['regions'],bodies['set___instance']['pointer'],symbols['barrier'])
    getters=[derived_cached_getter_program(bodies['get___instance']['regions'],bodies['get___instance']['pointer'],symbols,
        cache=state,cache_offset=32)for state in('coherent','empty','stale')]
    prepares=[prepare_program(bodies['OnDeserialized']['regions'],bodies['OnDeserialized']['pointer'],symbols,**p)
        for p in({},{'cache_empty':True},{'cache_empty':True,'original_null':True})]
    readers=[reader_program(body['regions'],body['pointer'],symbols,**p)for p in({},{'new':True},{'null':True},{'new':True,'null':True})]
    getter_pointer=image.method_pointer_va(mm['GetValue']);getter_raw=image.pe.bytes_at_va(getter_pointer,7)
    getter=original_tail_program(getter_raw,getter_pointer,bodies['get___instance']['pointer'],role='typed-instance-getter')
    typed=[]
    def own_class(usage,name):
        fact=derive_typed_usage_context(image,usage['instruction']-base,label='blackboardBuffId.class')
        need('exact-typed-class',(fact['tag'],fact['typeName'])==(1,name));typed.append(fact)
    own_class(constructor['baseClassUsage'],strings.WRAPPER)
    own_class(constructor['allocationUsage'],TYPE);own_class(factory['allocationUsage'],TYPE)
    for program in[constructor,factory]+getters+prepares:
        for usage in program.get('concreteClassUsages',[]):own_class(usage,TYPE)
    for program in readers:
        if program['newAllocationUsage']:own_class(program['newAllocationUsage'],WRAPPER)
    header=vector_recorder(image)(symbols['header']-base)
    primitive_param.object_header_source(image,header,scalar.reader_offsets(image,'blackboardBuffId'))
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-actual-conversion-getter',adapter['getterMethod'][0]==mm['GetValue'].index and adapter['getterMethod'][3]==getter_pointer-base)
    need('same-actual-static-reader',adapter['pairForwarder']['readerMethod']==[mm['Deserialize'].index,WRAPPER,'Deserialize',body['pointer']-base])
    reader=ap['referenceReaders']
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,positiveWireBytes=10,nullWireBytes=1,
        orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
            ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','pooled-string','byte-payload'))],
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,callbackSelectionConditional=True,
        wholeSkillDataAdmitted=False)
    def bounded(at,raw,label):return dict(startRva=at-base,endRva=at-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),
        boundary=label+' exact seven-byte tail; target source owned separately, no physical extent claim')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-buff-id-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-buff-id',typeName=TYPE,wrapperName=WRAPPER,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
        proof=dict(stringAncestor=ancestor,closedSetters=closed,constructor=constructor,factory=factory,instanceSetter=setter,
            originalConstructor=original,getterEntry=getter,getters=getters,prepares=prepares,readerPrograms=readers,
            typedClassUsages=typed,headerSource=header,pair=pair,adapter=adapter,referenceReaders=reader,
            sourceWindows={n:b['windows']for n,b in bodies.items()},boundedEntryWindows=[bounded(original_pointer,original_raw,'Original ctor'),bounded(getter_pointer,getter_raw,'GetValue')],
            actualOriginalInitialization=dict(wrapperConstructorCallsNamedBaseDirectly=True,initializerOwner=strings.TYPE,
                initializerTargetRva=symbols['originalConstructor']-base,ownOriginalEntryTargetRva=original_pointer-base,
                ownOriginalEntryInvokedByWrapper=False,pointerEqualityInferred=False,ownEntryTailDelegatesToSameInitializer=True),
            inheritedCache24Equated=False,wholeOwnerAdmitted=False),
        evidenceBoundary=dict(exact='Own MC3/new/FF full caller, named closed-string setters, distinct holder16/cache32, both constructors/factory, exact compatible cast/getter/prehook and ordinary adapter identity.',
            conditional='Fresh compatible initialized contexts/callbacks, typed zeroed allocation, disabled noninterfering collector, sufficiently buffered disjoint storage and independent exported StringPool.',
            structuralOnly='Stored key/flag/string; no evaluated Buff id or runtime blackboard value.',
            unresolved=['runtime provider/callback choice and evaluation','enclosing owner and physical EOF']))))
