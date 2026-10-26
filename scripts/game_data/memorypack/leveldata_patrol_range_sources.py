"""Finite complete Patrol range-handler source paths; helpers join separately."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_patrol_radio_sources import displacement,CONTROLLER
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def range_program(regions,entry,fields,symbols,*,already_played,near,query=True):
    """Ordered finite distance cases with ready classes and absent replacement.

    This authenticates the caller's arguments and selected writes only. Named
    position/math/query/request callees need their own ABI and source joins;
    their effects cannot follow from labels in ``symbols``.
    """
    if any(type(value)is not bool for value in(already_played,near,query)):
        raise ValueError('patrolRange.literal-path')
    d=lambda key:displacement(fields[key],4)
    g=BytesPath(regions,entry);events=[];classes=[]
    def usage():
        at=g.at;cell=g.relative('488b0d');classes.append(dict(instruction=at,cell=cell))
    def request_arguments(begin,receiver):
        g.take('4533c9','48c744242000000000')
        if begin:g.take('41b8ffffffff','b201',receiver)
        else:g.take('33d2','41b8ffffffff',receiver)
        site=g.at;g.call(symbols['play']);events.append(dict(kind='play',site=site,fromBegin=begin,
            index=-1,noFlushAfterLoading=False,implicitMethodInfo=None))
    g.take('4053','4883ec60');root=g.relative('488b05')
    g.take('488bd9','488b4838','4885c9');g.branch('0f85',False)
    g.take('8b83'+d('radioIndex'),'3983'+d('actionIndex'));g.branch('0f84',True)
    g.take('4883bb'+d('radioId')+'00');g.branch('0f84',False)
    g.take('0f57c0','0f2f83'+d('radius'));g.branch('0f83',False)
    usage();g.take('83b9e000000000');g.branch('75',True,1)
    g.take('33c9');g.call(symbols['player'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('488b50'+displacement(fields['playerEntity'],1),'4885d2');g.branch('0f84',False)
    g.take('4533c0','488d4c2450');g.call(symbols['position'])
    g.take('488b8b'+d('entity'),'4885c9');g.branch('0f84',False)
    g.take('488b89'+d('transform'),'4885c9');g.branch('0f84',False)
    g.take('f20f1081'+d('worldPosition'),'4c8d442430','8b89'+d('worldPositionZ'),
        '488d542440','f20f11442430','f20f1000','8b4008','894c2438','488d4c2450',
        'f20f11442440','89442448');g.call(symbols['subtract'])
    g.take('488d4c2440','f20f1018','8b4008','f20f115c2440','89442448');g.call(symbols['squared'])
    g.take('80bb'+d('hasPlayed')+'00','f30f109b'+d('radius'),'f30f59db');g.branch('0f84',not already_played)
    if not already_played:
        g.take('0f2fd8');g.branch('0f82',not near)
        if near:
            usage();g.take('48897c2470','488bbb'+d('radioId'),'83b9e000000000');g.branch('75',True,1)
            request_arguments(True,'488bcf')
            g.take('488b7c2470','c683'+d('hasPlayed')+'01');g.jump('e9')
    else:
        g.take('0f2fd8');usage();g.branch('73',near,1)
        g.take('83b9e000000000');g.branch('75',True,1)
        g.take('488b89b8000000','4533c0','488b93'+d('radioId'),'488b4950')
        site=g.at;g.call(symbols['queryNear'if near else'queryFar'])
        events.append(dict(kind='query-near'if near else'query-far',site=site,result=query))
        g.take('84c0');g.branch('0f84',not query)
        if query:
            usage();g.take('488b9b'+d('radioId'),'83b9e000000000');g.branch('75',True,1)
            if near:request_arguments(False,'488bcb')
            else:
                g.take('33d2','488bcb');site=g.at;g.call(symbols['stop']);events.append(dict(kind='stop',site=site,implicitMethodInfo=None))
            g.take('90');g.jump('e9')
    g.take('4883c460','5b','c3')
    return dict(selectedBytes=g.seen,optionalCallbackRootCell=root,classes=classes,
        alreadyPlayed=already_played,orderedNear=near,queryResult=query if already_played else None,
        events=events,initialPlayStateWritten=not already_played and near,
        sameAuthoredRadioIdToRequests=True,normalReturn=True,
        helperEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        condition='Exact initialized source path with optional callback receiver absent, matching action index, nonnull radio and entity/transform/player sources, positive finite radius and finite ordered positions. Selected helper/class/provider/query/request ABIs return normally and preserve nonvolatile registers. Callee semantics, live dispatch and playback remain separate.')


def subtract_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('f30f1002','f30f104a04','f3410f5c00','f3410f5c4804','f30f105208','f3410f5c5008',
        '0f14c1','f20f1101','f30f115108','488bc1','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,outputBytes=12,resultPointer='incoming RCX',
        orderedOperations=['a.x-b.x','a.y-b.y','a.z-b.z'],inputPointers=['rdx','r8'],
        physicalFunctionExtentProved=False)


def squared_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('6690','f30f104904','f30f1001','f30f105108','f30f59c0','f30f59c9','f30f59d2',
        'f30f58c1','f30f58c2','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,resultRegister='xmm0-low32',
        orderedOperations=['x*x','y*y','z*z','(x*x+y*y)+z*z'],inputPointer='rcx',
        physicalFunctionExtentProved=False)


def position_program(regions,entry,*,root_offset,position_offset):
    g=BytesPath(regions,entry);d=lambda n:displacement(n,4)
    g.take('4053','4883ec30');replacement=g.relative('488b05')
    g.take('488bd9','488b4868','4885c9');g.branch('0f85',False)
    g.take('488b82'+d(root_offset),'4885c0');g.branch('74',False,1)
    g.take('f20f1080'+d(position_offset),'8b88'+d(position_offset+8),'f20f1103','894b08',
        '488bc3','4883c430','5b','c3')
    return dict(selectedBytes=g.seen,optionalCallbackRootCell=replacement,
        rootOffset=root_offset,positionOffset=position_offset,unchangedOutputBytes=12,
        resultPointer='incoming RCX',normalReturn=True,helperCalls=0,
        condition='Compatible nonnull incoming RDX Entity and its RootComponent; absent replacement receiver; disjoint hidden RCX output12.')


def player_program(regions,entry,*,instance_offset,player_offset):
    g=BytesPath(regions,entry)
    g.take('4883ec28');replacement=g.relative('488b05')
    g.take('488bd1','488b4808','4885c9');g.branch('0f85',False)
    classes=[]
    def usage():
        at=g.at;cell=g.relative('488b0d');classes.append(dict(instruction=at,cell=cell))
    usage();g.take('83b9e000000000');g.branch('74',False,1)
    metadata=flag(g);g.branch('74',False,1)
    usage();g.take('83b9e000000000');g.branch('74',False,1)
    third=dict(instruction=g.at,cell=g.relative('488b05'));classes.append(third)
    g.take('488b80b8000000')
    if instance_offset==0:g.take('488b00')
    else:g.take('488b80'+displacement(instance_offset,4))
    g.take('4885c0');g.branch('74',False,1)
    g.take('488b40'+displacement(player_offset,1),'4883c428','c3')
    if len({r['cell']for r in classes})!=1:raise ValueError('patrolRange.same-GameInstance-class-cell')
    return dict(selectedBytes=g.seen,optionalCallbackRootCell=replacement,metadataReadyFlag=metadata,
        classes=classes,staticInstanceOffset=instance_offset,playerOffset=player_offset,
        normalReturn=True,helperCalls=0,resultRegister='rax',
        condition='Initialized GameInstance static storage and metadata, nonnull selected instance and absent replacement receiver. Exact static instance and named playerController field are separately authenticated.')


def derive(image,pins):
    import json,hashlib
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_member_sources import layout as vector_layout
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda key,expected,actual:scalar.need('patrolRange',key,expected,actual)
    def method(owner,name,parameters,returned,static):
        m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name
            and [ctx.type_name(p.type_index)for p in md.parameters_for(m)]==parameters]
        need('named-method-ABI:'+owner+'::'+name,(returned,static),(ctx.type_name(m.return_type),bool(m.flags&16)))
        def ordinary(index,type_name):
            kind,reference={'void':(1,False),'bool':(2,False),'int':(8,False),'float':(12,False),
                'string':(14,True),'UnityEngine.Vector3':(17,False)}.get(type_name,(18,True))
            scalar.ordinary(image,ctx.type_pointer(index),kind,'patrolRange.method-type',reference=reference)
        ordinary(m.return_type,returned)
        for p,type_name in zip(md.parameters_for(m),parameters,strict=True):ordinary(p.type_index,type_name)
        return m
    entity='Beyond.Gameplay.Core.Entity';player='Beyond.Gameplay.Core.PlayerController'
    root='Beyond.Gameplay.Core.RootComponent';game='Beyond.Gameplay.GameInstance';vector='UnityEngine.Vector3'
    methods=dict(player=method(game,'get_playerController',[],player,True),
        position=method(entity,'get_position',[],vector,False),
        subtract=method(vector,'op_Subtraction',[vector,vector],vector,True),
        squared=method(vector,'get_sqrMagnitude',[],'float',False),
        queryFar=method('System.String','Equals',['string','string'],'bool',True),
        queryNear=method('System.String','op_Inequality',['string','string'],'bool',True),
        play=method('Beyond.Gameplay.Actions.GameAction','PlayRadio',['string','bool','int','bool'],'void',True),
        stop=method('Beyond.Gameplay.Actions.GameAction','StopRadio',['string'],'void',True))
    symbols={key:image.method_pointer_va(m)for key,m in methods.items()}
    def unique_field(owner,type_name,*,offset=None,static=False):
        td=ctx.index.types[owner];offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        rows=[]
        for field in md.fields_for(td):
            name=md.string(field.name_index)
            if (bool(ctx.field_attributes(field.type_index)&16)==static and ctx.type_name(field.type_index)==type_name
                    and(offset is None or offsets[name]==offset)):
                scalar.ordinary(image,ctx.type_pointer(field.type_index),17 if type_name==vector else 18,
                    'patrolRange.owned-field',reference=type_name!=vector)
                rows.append(dict(owner=owner,name=name,typeName=type_name,offset=offsets[name],static=static))
        need('unique-owned-field:'+owner+'::'+type_name,1,len(rows));return rows[0]
    field_proofs={}
    def named(key,owner,name,type_name):
        field=ctx.field(owner+'::'+name);need('named-field:'+name,(owner,type_name),field[:2])
        field_proofs[key]=dict(owner=owner,name=name,typeName=type_name,offset=field[2],static=False)
        return field[2]
    fields={key:named(key,CONTROLLER,name,type_name)for key,name,type_name in(
        ('radioIndex','m_radioActionIdx','int'),('actionIndex','m_actionIdx','int'),
        ('radioId','m_radioInRange','string'),('radius','m_range','float'),
        ('entity','m_entity',entity),('hasPlayed','m_hasPlayRadio','bool'))}
    for key,owner,type_name in(('playerEntity',player,entity),('transform',entity,root)):
        field_proofs[key]=unique_field(owner,type_name);fields[key]=field_proofs[key]['offset']
    position=owned(image,symbols['position'])
    reads=[raw for row in position['rows']if len(raw:=bytes.fromhex(row['bytes']))==8 and raw[:4]==bytes.fromhex('f20f1080')]
    need('one-actual-position-read',1,len(reads));offset=int.from_bytes(reads[0][4:],'little',signed=True)
    field_proofs['worldPosition']=unique_field(root,vector,offset=offset)
    fields['worldPosition']=offset;fields['worldPositionZ']=offset+8
    vector_proof=vector_layout(image,ctx,vector)
    need('independently-owned-Vector3-value12',(12,False),(vector_proof['managedBytes'],vector_proof['wireReadAdmitted']))
    field_proofs['staticInstance']=unique_field(game,game,static=True)
    field_proofs['playerController']=unique_field(game,player)
    player_source=owned(image,symbols['player'])
    player_checked=player_program(player_source['regions'],player_source['pointer'],
        instance_offset=field_proofs['staticInstance']['offset'],player_offset=field_proofs['playerController']['offset'])
    player_classes=[derive_typed_usage_context(image,row['instruction']-base,label='patrolRange.playerClass')
        for row in player_checked['classes']]
    need('three-exact-GameInstance-classes',[(1,game)]*3,[(r['tag'],r['typeName'])for r in player_classes])
    helpers=dict(position=dict(windows=position['windows'],program=position_program(position['regions'],position['pointer'],
        root_offset=fields['transform'],position_offset=offset)),
        player=dict(windows=player_source['windows'],program=player_checked,classes=player_classes))
    for key,program in(('subtract',subtract_program),('squared',squared_program)):
        raw=image.pe.bytes_at_va(symbols[key],128);checked=program([(symbols[key],raw)],symbols[key])
        end=max(at+len(bytes.fromhex(h))for at,h in checked['selectedBytes'])
        helpers[key]=dict(program=checked,reachableWindow=dict(startRva=symbols[key]-base,endRva=end-base,
            sha256=hashlib.sha256(image.pe.bytes_at_va(symbols[key],end-symbols[key])).hexdigest().upper()),
            metadataEntryProved=True,physicalFunctionExtentProved=False)
    consumer=method(CONTROLLER,'_ProcessRadioInRange',[],'void',False)
    source=owned(image,image.method_pointer_va(consumer));programs=[]
    for already,near,query in((False,False,False),(False,True,True),(True,False,False),(True,False,True),(True,True,False),(True,True,True)):
        checked=range_program(source['regions'],source['pointer'],fields,symbols,already_played=already,near=near,query=query)
        classes=[derive_typed_usage_context(image,row['instruction']-base,label='patrolRange.callerClass')for row in checked['classes']]
        expected=[game]+(['Beyond.Gameplay.Actions.GameAction']if not already and near else
            ['Beyond.Gameplay.NarrativeUtils']+(['Beyond.Gameplay.Actions.GameAction']if query else[])if already else[])
        need('actual-caller-class-identities',[(1,name)for name in expected],[(r['tag'],r['typeName'])for r in classes])
        programs.append(dict(program=checked,classes=classes))
    return json.loads(json.dumps(dict(nativeInputs=pins,method=[consumer.index,CONTROLLER,'_ProcessRadioInRange',source['pointer']-base],
        windows=source['windows'],fields=field_proofs,vectorLayout=vector_proof,helpers=helpers,
        namedMethods={key:[m.index,image.type_name(m.declaring_type),md.string(m.name_index),symbols[key]-base]for key,m in methods.items()},
        programs=programs,initialRangeRequestSourceProved=True,repeatStringQueryEffectsProved=False,
        actionDispatchProved=False,wholeOwnerAdmitted=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary='Exact first-request source with nominal player/entity positions and selected Vector3 subtraction/squared-length programs; initialized absent-replacement and ordered finite geometry required. Other branch callees supply conditional query results only; live execution, action dispatch, actual String comparison effects and playback are not observed.')))
