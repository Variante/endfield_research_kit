"""Current pooled LevelSpawnerInstData source and independent list parent."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.LevelSpawnerInstData'
FIELDS=(('belongLevelScriptId','ulong',24),('configId','string',56),
    ('enableWaveDieEvent','bool',64),('position','UnityEngine.Vector3',32),
    ('rotation','UnityEngine.Vector3',44),('spawnerId','ulong',16))


def record_program(regions,entry,o,s,*,null=False,new=False):
    if type(null)is not bool or type(new)is not bool:raise ValueError('levelSpawner.literal-profile')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('levelSpawner.reader-layout')
    g=BytesPath(regions,entry);reads=[];allocation=None;typed=[]
    def guard():
        p=bytes(g.bytes.get(g.at+i,0)for i in range(2))
        if p==b'\x0f\x84':g.branch('0f84',False)
        else:g.branch('74',False,1)
    def holder(final=False):
        g.take('4885ff'if final else'4885f6');guard()
        g.take('488b4f10'if final else'488b4e10','4885c9');guard()
    def call(role):
        at=g.at;g.call(s[role]);return at
    g.take('48895c2408','48896c2410','4889742418','57','4883ec30')
    ready=flag(g);g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080feff');g.branch('0f84',null)
    if null:
        g.take('488bcf','48c70700000000');call('barrier');g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
            call('allocate');g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');call('constructor')
            g.take('488bcf','48892f');call('barrier');g.take('90');g.jump('e9')
        g.take('4080fe06');g.branch('0f85',False)
        g.take('488b37','488bcb');at=call('uint64');holder();g.take('48894118')
        reads.append(dict(fieldName='belongLevelScriptId',sourceCall=at,kind='uint64'))
        g.take('488bcb','488b37');at=call('pool');holder();g.take('48894138','4883c138');call('barrier')
        reads.append(dict(fieldName='configId',sourceCall=at,kind='pool'))
        g.take('488b37','488bcb');at=call('bool');holder();g.take('884140')
        reads.append(dict(fieldName='enableWaveDieEvent',sourceCall=at,kind='bool'))
        g.take('488bd3');typed.append(dict(instruction=g.at,cell=g.relative('4c8b05')))
        g.take('488d4c2420','488b37');at=call('vector3');holder()
        g.take('f20f10442420','488bd3','8b442428','f20f114120','894128')
        reads.append(dict(fieldName='position',sourceCall=at,kind='vector3',typedUsage=typed[-1]))
        g.take('488d4c2420');typed.append(dict(instruction=g.at,cell=g.relative('4c8b05')))
        g.take('488b37');at=call('vector3');holder()
        g.take('f20f10442420','8b442428','f20f11412c','894134')
        reads.append(dict(fieldName='rotation',sourceCall=at,kind='vector3',typedUsage=typed[-1]))
        g.take('488bcb','488b3f');at=call('uint64');holder(final=True);g.take('48894110')
        reads.append(dict(fieldName='spawnerId',sourceCall=at,kind='uint64'))
    g.take('488b5c2440','488b6c2448','488b742450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=ready,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,orderedReads=reads,headerBytes=1,memberCount=None if null else 6,
        positiveWireBytes=None if null else 46,nullWireBytes=1,normalReturn=True,entryFrameRestored=True,
        sameReader=True,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def constructor_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
    g.call(s['allocate']);g.take('4885c0');g.branch('74',False,1)
    g.take('488d4b10','48894310','4883c420','5b')
    if g.relative('e9')!=s['barrier']:raise ValueError('levelSpawner.constructor-barrier')
    return dict(selectedBytes=g.seen,initializedFlag=ready,typedAllocation=allocation,
        originalHolderOffset=16,normalTailReturn=True)


def derive(image,pins,leveldata):
    """Compose exact current record, registered reference adapter and own parent."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_source_helper
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.vector3_source import validate_vector3_source
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda k,e,a:scalar.need('levelSpawner',k,e,a)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    need('members',[(n,t)for n,t,_ in FIELDS],[(m.name,m.declared_type)for m in wrapper.members])
    need('fields',[(TYPE,t,o)for _,t,o in FIELDS],[ctx.field(TYPE+'::'+n)for n,_,_ in FIELDS])
    need('reference-original',False,ctx.is_value_type(TYPE))
    mm=methods(image,wrapper);source=owned(image,image.method_pointer_va(mm['Deserialize']))
    ctor=owned(image,image.method_pointer_va(mm['.ctor']));offsets=scalar.reader_offsets(image,'levelSpawner')
    s=dict(uint64=_body_target(source,'mov [rcx+0x18], rax',before=True),
        pool=_body_target(source,'mov [rcx+0x38], rax',before=True),
        bool=_body_target(source,'mov [rcx+0x40], al',before=True),
        vector3=_body_target(source,'movsd [rcx+0x20], xmm0',before=True),
        constructor=ctor['pointer'],barrier=_body_target(source,'add rcx, 0x38'),
        allocate=_body_target(ctor,'test rax, rax',before=True))
    programs=[record_program(source['regions'],source['pointer'],offsets,s,**p)
        for p in(dict(null=True),dict(new=True),dict(new=False))]
    constructor=constructor_program(ctor['regions'],ctor['pointer'],s)
    allocations=[]
    for role,allocation,type_name in(('wrapper',programs[1]['typedAllocation'],wrapper.name),
            ('original',constructor['typedAllocation'],TYPE)):
        usage=derive_typed_usage_context(image,allocation['instruction']-base,label='levelSpawner.'+role)
        need('typed-allocation:'+role,(1,type_name),(usage['tag'],usage['typeName']));allocations.append(usage)
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
    record=vector_recorder(image);primitives={}
    for role,width in(('uint64',8),('bool',1)):
        body=record(s[role]-base)
        checked=scalar.boolean_source(image,body,offsets,'levelSpawner.bool')if width==1 else scalar.integer_source(image,body,offsets,'levelSpawner.uint64',width=8)
        primitives[role]=dict(source=body,proof=checked)
    pool=pooled_source_helper.validate_on_image(image,s['pool'],pins)
    vector=[]
    for read in programs[-1]['orderedReads']:
        if read['kind']!='vector3':continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelSpawner.vector3')
        vector.append(dict(typedRequest=usage,source=validate_vector3_source(image,usage,s['vector3']-base)))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    field,read=[(f,r)for f,r in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True)if f['name']=='spawners'][0]
    need('same-LevelData-pins',pins,leveldata['nativeInputs'])
    usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelSpawner.parent')
    collection=derive_reference_list_component(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=2)
    body=owned(image,collection['entry']['pointer'])
    total=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    induction=reference_list_induction(body['regions'],body['pointer'],dict(offsets,totalLength=total),
        {k:base+v for k,v in collection['symbols'].items()})
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=TYPE,profile=pair,
        sourceWindows=source['windows'],programs=programs,constructorWindows=ctor['windows'],
        constructor=constructor,getter=getter,typedAllocations=allocations,adapter=adapter,
        primitives=primitives,pool=pool,vector3=vector,barrier=dict(source=barrier,proof=barrier_proof),
        symbolRvas={k:v-base for k,v in s.items()},parent=dict(field=field,source=read,typedRequest=usage),
        collection=collection,positiveCountInduction=induction,
        capability=dict(closedListType=field['typeName'],countLimit=16384,
            headerBytes=4,recordMemberCount=6,recordWireBytes=46,recordNullBytes=1,
            wholeGrammarAdmitted=True),wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
