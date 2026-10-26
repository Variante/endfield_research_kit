"""Fresh checkpoint-to-event dispatch programs and exact callback seams.

Runtime listener registration, ObjectPtr UID results, callback identities and
action-map selection are conditions. No game process or saved report supplies
authority, and dispatch requests are distinct from observed action execution.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets
from scripts.game_data.memorypack import leveldata_patrol_event_programs as entry_programs
from scripts.game_data.memorypack import leveldata_patrol_event_dispatch_programs as dispatch
from scripts.game_data.memorypack.leveldata_patrol_concat_string_sources import string_rows

SCHEMA='endfield.story-patrol-event-dispatch-sources.v4'
MANAGER='Beyond.Gameplay.Core.LevelEventManager'
KEYS='Beyond.Gameplay.Core.GameLevelEventUtils'
LISTENER_MODES=('exhausted','free','invalid','null','other-kind','no-delegate','delegate',
    'invalid-trigger','null-trigger','inactive-trigger','script')
TRIGGER_MODES=('exhausted','invalid','null','other-kind','no-action','predicate-false','delegate',
    'invalid-trigger','null-trigger','inactive-trigger','event-mismatch','missing-action','script')


def need(check,condition,detail=None):
    if not condition:raise ValueError('patrolEventSource.'+check+':'+str(detail)[:700])


def norm(value):return json.loads(json.dumps(value))


def actual_calls(packet,base,mapper=None):
    rows=string_rows(packet,base,mapper)
    return [(int(r['va'],16),int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True))
        for r in rows if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232]


def _callee(packet,base,mapper=None):
    calls=actual_calls(packet,base,mapper)
    need('actual-selected-child-call',bool(calls))
    return calls[0][1]


def _programs(proof,base):
    sources=proof['sources']
    def raw(role):return packets.regions(sources[role],base)
    def at(role):return base+sources[role]['entryRva']
    symbols={k:at(k)for k in('key','listener','trigger')}
    raises=[entry_programs.raise_event(raw('raise'),at('raise'),symbols,released=a,key_found=b,listener=c)
        for a,b,c in((True,False,False),(False,False,False),(False,True,False),(False,True,True))]
    key=entry_programs.try_key(raw('key'),at('key'),cache=at('keyCache'))
    cache=entry_programs.key_cache(raw('keyCache'),at('keyCache'),initialize=at('keyReady'))
    ready=entry_programs.key_ready(raw('keyReady'),at('keyReady'))
    need('same-own-ready-key-class',key['classCellVa']==cache['classCellVa']==ready['classCellVa'])
    listener_setups=[entry_programs.listener_setup(raw('listener'),at('listener'),found=f)for f in(False,True)]
    trigger_setups=[entry_programs.trigger_setup(raw('trigger'),at('trigger'),found=f)for f in(False,True)]
    ls=listener_setups[-1];ts=trigger_setups[-1]
    la=dict(barrier=ls['actualCalls']['barrier']['targetVa'],valid=at('valid'))
    listener_loops=[dispatch.listener_loop(raw('listener'),ls['continuationInstructionVa'],la,mode=m)for m in LISTENER_MODES]
    need('all-listener-loop-return-edges',all(v['continuationVa']==ls['continuationInstructionVa']for v in listener_loops
        if v['mode']in('invalid','null','other-kind','no-delegate','invalid-trigger','null-trigger','inactive-trigger')))
    returns=[dispatch.listener_return(raw('listener'),v['continuationVa'],false=v['mode']=='exhausted')
        for v in listener_loops if v['mode']in('exhausted','delegate','script')]
    ta=dict(valid=at('valid'),action=at('action'),eventType=at('eventType'),invokeExecutor=at('invokeExecutor'))
    trigger_loops=[dispatch.trigger_loop(raw('trigger'),ts['continuationInstructionVa'],ta,mode=m,
        filter_present=f)for m in TRIGGER_MODES for f in((False,True)if m in('delegate','no-action')else(True,))]
    need('all-trigger-loop-back-edges',all(v['continuationVa']==ts['continuationInstructionVa']for v in trigger_loops if v['mode']!='exhausted'))
    action=dispatch.ordinary_action(raw('action'),at('action'))
    header_dispatch=[dispatch.uint_slot(raw('eventType'),at('eventType'),slot=slot,callback=at(role))
        for slot,role in((15,'levelHeader'),(26,'checkpointHeader'))]
    header=dispatch.level_header_enum(raw('levelHeader'),at('levelHeader'),dispatch_target=at('eventType'))
    checkpoint_key=dispatch.checkpoint_header_key(raw('checkpointHeader'),at('checkpointHeader'))
    need('same-exact-checkpoint-event-enum',checkpoint_key['returnedUInt32']==proof['parent']['proof']['producerSource']['eventKey']['program']['result'])
    executor_programs=[dispatch.invoke_executor(raw('invokeExecutor'),at('invokeExecutor'),invoked=invoked,
        delayed=delay,next_frame=next_frame)for invoked in(False,True)for delay,next_frame in((False,False),(True,False),(True,True))]
    executor_programs.append(dispatch.invoke_executor(raw('invokeExecutor'),at('invokeExecutor'),invoked=True,removed=True))
    count_limit=4096
    need('finite-all-snapshot-indices',all(0<=i<count<=count_limit and 32+16*i+16<=32+16*count
        for count in range(1,count_limit+1)for i in(0,count-1)))
    return dict(raisePrograms=raises,keyProgram=key,keyCache=cache,keyReady=ready,
        listenerSetups=listener_setups,listenerLoops=listener_loops,listenerReturns=returns,
        triggerSetups=trigger_setups,triggerLoops=trigger_loops,ordinaryAction=action,
        headerDispatch=header_dispatch,levelHeader=header,checkpointHeader=checkpoint_key,executorCallerPrograms=executor_programs,
        iteration=dict(countLimit=count_limit,snapshotElementBytes=16,innerDictionaryEntryBytes=32,
            listenerFreeSlotStep=1,triggerIndexStep=1,
            listenerVersionGuardBeforeEachValue=True,triggerSnapshotCountStableRequired=True,
            listenerResult='first valid eligible delegate/script listener, or false after all used/free slots',
            triggerOrder='ascending private snapshot index, each entry at most once; every selected loop path advances one',
            callbackValues='same incoming EventParams reference, event enum and header start-node ID as separately replayed',
            runtimeRegistrationOrInvocationObserved=False))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    _publication_gate(image,pins);base=image.pe.image_base;parent=packets.derive(image,pins)
    producer=parent['proof']['producerSource'];sources={}
    sources['raise']=packets.packet(image,base+producer['symbolRvas']['raiseEvent'])
    targets=[v for _,v in actual_calls(sources['raise'],base,image.mapper)]
    need('complete-actual-entry-call-domain',len(targets)>=3)
    for role,target in zip(('key','listener','trigger'),targets[:3]):sources[role]=packets.packet(image,target)
    sources['keyCache']=packets.packet(image,_callee(sources['key'],base,image.mapper))
    sources['keyReady']=packets.packet(image,_callee(sources['keyCache'],base,image.mapper))
    trigger=entry_programs.trigger_setup(packets.regions(sources['trigger'],base),base+sources['trigger']['entryRva'])
    # The full selected loop grammar authenticates these actual E8 operands;
    # capture candidate bodies at their byte-pattern sites before replay.
    rows=string_rows(sources['trigger'],base,image.mapper)
    patterns=dict(valid='e8',action='498bd4488b4f38',eventType='b90f000000',invokeExecutor='4d8bc4488bd7498bce')
    from scripts.game_data.memorypack.leveldata_patrol_concat_string_sources import locate
    for role,prefix in patterns.items():
        if role=='valid':
            candidates=[r for r in rows if bytes.fromhex(r['bytes'])==bytes.fromhex('488d8c2488000000')]
            need('unique-own-listener-validity-call',len(candidates)==1)
            call_at=int(candidates[0]['va'],16)+len(bytes.fromhex(candidates[0]['bytes']))
        else:call_at=locate(sources['trigger'],base,prefix)+len(bytes.fromhex(prefix))
        regions=packets.regions(sources['trigger'],base);cells={at+i:b for at,raw in regions for i,b in enumerate(raw)}
        call_raw=bytes(cells[call_at+i]for i in range(5));need('exact-loop-E8-'+role,call_raw[:1]==b'\xe8')
        sources[role]=packets.packet(image,call_at+5+int.from_bytes(call_raw[1:],'little',signed=True))
    ctx=NativeReferenceContext(image);md=image.metadata;methods={}
    header_methods={}
    for role,owner,name,slot in(('levelHeader','Beyond.Gameplay.Actions.LevelEventHeader','get_eventKeyEnum',15),
        ('checkpointHeader','Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach','get_eventKey',26)):
        m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name]
        target=image.method_pointer_va(m);sources[role]=packets.packet(image,target)
        need('own-virtual-UInt32-header-getter-'+role,m.slot==slot and bool(m.flags&64)and not m.flags&16 and m.parameter_count==0 and ctx.type_name(m.return_type)==('uint'if role=='levelHeader'else'Beyond.Gameplay.Core.GameLevelEvent'))
        _vtable(image,m.declaring_type,slot,m.index,'patrolEvent.'+role)
        header_methods[role]=dict(method=[m.index,owner,name,target-base],slot=slot,result=ctx.type_name(m.return_type),parameters=[])
    concrete=ctx.index.types['Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach']
    need('own-checkpoint-LevelEventHeader-parent',ctx.parent('Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach')=='Beyond.Gameplay.Actions.LevelEventHeader')
    _vtable(image,concrete.index,15,header_methods['levelHeader']['method'][0],'patrolEvent.checkpoint-inherited-header')
    expected=dict(raise_=(MANAGER,'RaiseLevelEvent'),key=(KEYS,'TryGetKey'),listener=(MANAGER,'HasEventListener'),
        trigger=(MANAGER,'_DoTryInvokeEventActionTriggerList'),keyCache=(KEYS,'get_gameLevelEventKeyCache'),keyReady=(KEYS,'_InitKeyCache'),
        invokeExecutor=('Beyond.Gameplay.Actions.ActionExecutorManager','_InvokeExecutor'))
    for label,(owner,name)in expected.items():
        role='raise'if label=='raise_'else label;target=base+sources[role]['entryRva']
        found=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and image.method_pointer_va(m)==target]
        need('own-actual-method-'+role,len(found)==1)
        m=found[0];methods[role]=dict(method=[m.index,owner,name,target-base],parameters=[ctx.type_name(p.type_index)for p in md.parameters_for(m)],
            result=ctx.type_name(m.return_type),static=bool(m.flags&16))
    hierarchy={name:ctx.parent(name)for name in('Beyond.Gameplay.Actions.EventActionTrigger','Beyond.Gameplay.Actions.ActionHeader')}
    proof=dict(parent=parent,sources=sources,methods=methods,headerMethods=header_methods,hierarchy=hierarchy)
    proof['programs']=_programs(proof,base);usages={}
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    proof['headerPreparation']=preparation.derive(image,pins,target=proof['programs']['headerDispatch'][0]['prepareTargetVa'])
    for role,program in(('key',proof['programs']['keyProgram']),('keyCache',proof['programs']['keyCache']),('keyReady',proof['programs']['keyReady'])):
        site=program['classUsageInstructionVa'];usages[role]=derive_typed_usage_context(image,site-base,label='patrolEvent.'+role)
        need('own-key-class-usage-'+role,(usages[role].get('tag'),usages[role].get('typeName'))==(1,KEYS))
    fields={}
    for owner in(KEYS,MANAGER,MANAGER+'+EventListener','Beyond.Gameplay.Core.GameWorld','Beyond.Gameplay.GameInstance',
        'Beyond.Gameplay.Actions.EventActionTrigger','Beyond.Gameplay.Actions.ActionContext',
        'Beyond.Gameplay.Actions.ActionExecutor','Beyond.Gameplay.NodeBase','Beyond.Gameplay.Actions.ActionMapRuntime'):
        td=ctx.index.types[owner];offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        fields[owner]=[dict(name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),static=bool(ctx.field_attributes(f.type_index)&16),
            offset=offsets[md.string(f.name_index)])for f in md.fields_for(td)]
    proof.update(keyClassUsages=usages,nominalFields=fields,imageBase=base)
    result=norm(dict(schema=SCHEMA,status='validated-conditional-event-dispatch-transfer-sources',nativeInputs=pins,proof=proof,
        selectedEntryListenerAndDispatchTransfersProved=True,selectedActionExecutorCallerFramesProved=True,collectionAndLifetimeEffectsProved=False,
        actionExecutorEffectsProved=False,wholeCheckpointProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual checkpoint E8, own event-manager/key/cache declarations and bytes, release/listener guards, complete loop cases, exact delegate and action-executor request arguments and source state stores.',
            conditional=__doc__,unresolved=['collection lookup/snapshot/pool/disposal supplement','ActionExecutor request helper and dynamic action-map/callback selection','actual initialized cache/UID/registration/provider/lifetime/activation and playback'])))
    validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
    need('schema-native-inputs',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins and
        value.get('status')=='validated-conditional-event-dispatch-transfer-sources')
    p=value['proof'];base=p['imageBase'];parent=p['parent'];packets.validate(parent)
    need('exact-state-and-header-field-inheritance',p['hierarchy']=={
        'Beyond.Gameplay.Actions.EventActionTrigger':'Beyond.Gameplay.Actions.ActionExecutor',
        'Beyond.Gameplay.Actions.ActionHeader':'Beyond.Gameplay.NodeBase'})
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    preparation.validate(p['headerPreparation'],pins)
    need('same-parent-pins-and-actual-event-E8',parent['nativeInputs']==pins and
        p['sources']['raise']['entryRva']==parent['proof']['producerSource']['symbolRvas']['raiseEvent'])
    for source in p['sources'].values():packets.verify_packet(source)
    expected=dict(raise_=(MANAGER,'RaiseLevelEvent'),key=(KEYS,'TryGetKey'),listener=(MANAGER,'HasEventListener'),
        trigger=(MANAGER,'_DoTryInvokeEventActionTriggerList'),keyCache=(KEYS,'get_gameLevelEventKeyCache'),keyReady=(KEYS,'_InitKeyCache'),
        invokeExecutor=('Beyond.Gameplay.Actions.ActionExecutorManager','_InvokeExecutor'))
    need('complete-exact-nominal-method-role-set',set(p['methods'])=={'raise'if r=='raise_'else r for r in expected})
    for label,identity in expected.items():
        role='raise'if label=='raise_'else label;row=p['methods'][role]['method']
        need('same-actual-nominal-method-'+role,tuple(row[1:3])==identity and row[3]==p['sources'][role]['entryRva'])
    for role,owner,name,slot,result in(('levelHeader','Beyond.Gameplay.Actions.LevelEventHeader','get_eventKeyEnum',15,'uint'),
        ('checkpointHeader','Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach','get_eventKey',26,'Beyond.Gameplay.Core.GameLevelEvent')):
        row=p['headerMethods'][role]
        need('same-actual-header-declaration-'+role,row['method'][1:]==[owner,name,p['sources'][role]['entryRva']]and row['slot']==slot and row['result']==result and row['parameters']==[])
    need('complete-byte-program-replay',norm(_programs(p,base))==p['programs'])
    need('same-actual-header-class-preparation',all(r['prepareTargetVa']-base==p['headerPreparation']['actualEntryRva']for r in p['programs']['headerDispatch']))
    fields=p['nominalFields']
    def field(owner,name,type_name,offset,static):
        need('own-field-'+owner+'.'+name,dict(name=name,typeName=type_name,offset=offset,static=static)in fields[owner])
    field(KEYS,'s_keyCacheInited','bool',1,True);field(KEYS,'s_gameLevelEventKeyCache','Beyond.CombineKey[]',24,True)
    field(MANAGER,'m_markReleased','bool',128,False)
    field('Beyond.Gameplay.Core.GameWorld','eventManager',MANAGER,64,True)
    field('Beyond.Gameplay.GameInstance','actionManager','Beyond.Gameplay.Actions.ActionExecutorManager',40,True)
    field('Beyond.Gameplay.Actions.ActionExecutor','startNodeID','int',24,False)
    field('Beyond.Gameplay.Actions.ActionExecutor','onFinishCallback','System.Action',136,False)
    field('Beyond.Gameplay.Actions.ActionExecutor','needRecycle','bool',126,False)
    field('Beyond.Gameplay.NodeBase','_ID','int',16,False)
    field('Beyond.Gameplay.Actions.ActionContext','actionMap','Beyond.Gameplay.Actions.ActionMapRuntime',112,False)
    field('Beyond.Gameplay.Actions.ActionMapRuntime','nodeArray','Beyond.Gameplay.NodeBase[]',32,False)
    listener=MANAGER+'+EventListener'
    field(listener,'<type>k__BackingField',listener+'+Type',24,False)
    field(listener,'<trigger>k__BackingField','Beyond.ObjectPtr`1<Beyond.Gameplay.Actions.EventActionTrigger>',40,False)
    field(listener,'<action>k__BackingField',MANAGER+'+OnEventAction',56,False)
    field(listener,'<secondFilter>k__BackingField',MANAGER+'+DoSecondFilter',64,False)
    need('conditional-source-grants',value.get('selectedEntryListenerAndDispatchTransfersProved')is True and value.get('selectedActionExecutorCallerFramesProved')is True and all(value.get(k)is False for k in
        ('collectionAndLifetimeEffectsProved','actionExecutorEffectsProved','wholeCheckpointProved','runtimeInvocationObserved','playbackProved')))
    return value
