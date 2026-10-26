"""Current LevelData's complete ordered normal source, without child admission."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

ORIGINAL='Beyond.Gameplay.LevelData'
FIELDS=(
    'airWalls','aiTransData','autoSpawnedInteractives','blackbox','buildableCondition',
    'cameraPoses','charPatrol','doodadGroup','dynamicOccludeAreas','enemies','enemyGroup',
    'enemyPatrol','environmentVolumes','factoryMines','factoryPredefineData','factoryRegions',
    'functionArea','guideHints','interactiveLockData','interactives','levelIdNum',
    'levelScriptBriefDataDict','levelScriptDataPathDict','levelUIs','levelWideConfigs',
    'mapVolumeDatas','missionAreas','npcAttractPointData','npcClusters','npcGroup','npcPatrol',
    'npcs','patrols','predefinedParams','riftVolumes','safeZone','sceneId','sludgeDatas',
    'spawners','specificData','splines','waterVolumes','worldWayPointData',
)
VALUE_FIELDS=frozenset(('blackbox','buildableCondition','factoryPredefineData',
    'functionArea','safeZone','specificData'))


def owner_program(regions,entry,fields,offsets):
    """Authenticate all 43 same-reader calls/stores and the complete return."""
    if [f['name']for f in fields]!=list(FIELDS):raise ValueError('leveldataOwner.ordered-fields')
    if offsets!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('leveldataOwner.reader-layout')
    if any(type(f['offset'])is not int or not 16<=f['offset']<4096 for f in fields):
        raise ValueError('leveldataOwner.field-offset')
    g=BytesPath(regions,entry);reads=[];barriers=[]
    peek=lambda n=3:bytes(g.bytes.get(g.at+i,0)for i in range(n)).hex()
    def guard():
        if peek(2)=='0f84':g.branch('0f84',False)
        else:g.branch('74',False,1)
    def slot(short,long,offset):
        g.take(short+bytes((offset,)).hex()if offset<128 else long+offset.to_bytes(4,'little').hex())
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    initialized=g.relative('803d')+1;g.take('00','488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080feff');g.branch('0f84',False)
    g.take('48833f00');g.branch('0f84',False)
    header=g.at;g.take('4080fe2b');g.branch('0f85',False)
    for index,field in enumerate(fields):
        setup=[];context=None;start=g.at;final=field['name']=='worldWayPointData'
        while peek()in('488b15','488bcb','488b37','488b3f'):
            prefix=peek()
            if prefix=='488b15':
                if context is not None:raise ValueError('leveldataOwner.duplicate-typed-context')
                context=dict(instruction=g.at,cell=g.relative(prefix))
            else:g.take(prefix)
            setup.append(prefix)
        primitive=field['name']in('levelIdNum','sceneId')
        expected=['488bcb','488b3f'if final else'488b37']+([]if primitive else['488b15'])
        if sorted(setup)!=sorted(expected):raise ValueError('leveldataOwner.same-reader-holder:'+field['name'])
        call=g.at;target=g.relative('e8')
        g.take('4885ff'if final else'4885f6');guard()
        g.take('488b4f10'if final else'488b4e10','4885c9');guard()
        offset=field['offset']
        if field['name']=='levelIdNum':slot('8941','8981',offset)
        else:
            slot('488941','488981',offset)
            # The exact +128 address is encoded as subtraction of -128.
            if offset==128:g.take('4883e980')
            else:slot('4883c1','4881c1',offset)
            if not final:barriers.append(g.relative('e8'))
        reads.append(dict(memberIndex=index,fieldName=field['name'],sourceStart=start,
            sourceCall=call,sourceTarget=target,typedUsage=context,storeOffset=offset,
            kind='int32'if field['name']=='levelIdNum'else'pool'if field['name']=='sceneId'else'reference'))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    tail=g.relative('e9')
    if len(set(barriers))!=1 or tail!=barriers[0]:raise ValueError('leveldataOwner.same-tail-barrier')
    return dict(originalType=ORIGINAL,memberCount=43,headerBytes=1,memberHeader=header,
        initializedFlag=initialized,orderedReads=reads,selectedBytes=g.seen,
        barrierTarget=tail,existingWrapper=True,entryReader='rcx',entryWrapperOutput='rdx',
        entryFrameRestored=True,normalReturnViaBarrier=True,childGrammarAdmitted=False,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False,
        condition='Initialized current generated reader, existing compatible wrapper/original, '
        'sufficient stable disjoint buffered bytes/storage, disabled collector and normal exact '
        'typed child effects. Creation/refill/error/active collector/live provider choice remain separate.')


def derive(image,pins):
    """Re-prove metadata, full normal body, primitive sources and typed joins."""
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import methods,owned
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    build=Build(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base
    need=lambda k,e,a:scalar.need('leveldataOwner',k,e,a)
    wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==ORIGINAL]
    need('reference-original',False,ctx.is_value_type(ORIGINAL))
    need('reference-holder',(wrapper.name,ORIGINAL,16),ctx.field(wrapper.name+'::__instance'))
    need('metadata-order',list(FIELDS),[m.name for m in wrapper.members])
    fields=[]
    for member in wrapper.members:
        owner=build.wrappers[member.declaring_wrapper].wrapped_type
        actual=ctx.field(owner+'::'+member.name)
        need('field-type:'+member.name,member.declared_type,actual[1])
        fields.append(dict(name=member.name,typeName=member.declared_type,offset=actual[2]))
    method=methods(image,wrapper)['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
    body=owned(image,image.method_pointer_va(method));offsets=scalar.reader_offsets(image,'leveldataOwner')
    program=owner_program(body['regions'],body['pointer'],fields,offsets);usages=[];primitive={}
    record=vector_recorder(image)
    for field,read in zip(fields,program['orderedReads'],strict=True):
        target=read['sourceTarget']
        if read['typedUsage']is not None:
            usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataOwner')
            expected='ReadValue'if field['name']in VALUE_FIELDS else'ReadPackable'
            need('exact-typed-request:'+field['name'],
                (6,'MemoryPack.MemoryPackReader',expected,[],[field['typeName']]),
                tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
            build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.'+expected,result_abi='reference')
            usages.append(usage)
        elif field['name']=='sceneId':primitive['pool']=pooled_source_helper.validate_on_image(image,target,pins)
        else:
            need('int32-field','int',field['typeName'])
            source=record(target-base)
            primitive['int32']=dict(targetRva=target-base,source=source,
                proof=scalar.integer_source(image,source,offsets,'leveldataOwner.int32',width=4))
    barrier,barrier_proof,_=_fast_barrier(image,program['barrierTarget'])
    return json.loads(json.dumps(dict(nativeInputs=pins,wrapperName=wrapper.name,
        method=[method.index,wrapper.name,'Deserialize',body['pointer']-base],fields=fields,
        sourceWindows=body['windows'],program=program,typedUsages=usages,
        primitiveSources=primitive,barrier=dict(source=barrier,proof=barrier_proof),
        childGrammarAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
