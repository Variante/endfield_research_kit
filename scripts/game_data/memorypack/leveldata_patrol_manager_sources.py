"""Fresh conditional manager postamble, first tick and queue source effects.

The selected first tick starts with the exact successful TryToInvoke state. It
uses a tracked executor, one cursor/action, and actual ordinary action callback
requests followed by a positive action delay. Callback identity and authored
behavior are conditions; the enclosing direct control and return paths replay
independently. No report is an input and no runtime object is inspected.
"""
import json,math,struct
from scripts.game_data.memorypack import leveldata_patrol_manager_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_event_collection_programs as lists
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets
from scripts.game_data.memorypack.leveldata_patrol_bundle_cache_sources import _method,_fields

SCHEMA='endfield.story-patrol-manager-postamble-sources.v1'
STATUS='validated-conditional-manager-postamble-source-effects'
EXECUTOR='Beyond.Gameplay.Actions.ActionExecutor'
ACTION='Beyond.Gameplay.Actions.ActionBase'
NODE='Beyond.Gameplay.NodeBase'
CONTEXT='Beyond.Gameplay.Actions.ActionContext'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'
PTR='Beyond.ObjectPtr`1<'+EXECUTOR+'>'
LIST='System.Collections.Generic.List`1'
POOL='Beyond.PoolCore.ListPool`1'


def need(check,condition):
    if not condition:raise ValueError('patrolManagerSources.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def same_packet(a,b):return all(k in a and k in b and same(a[k],b[k])for k in('entryRva','regions','windows'))


PROFILES={'onInvoked':paths.on_invoked,'tick':paths.tick,'logicTick':paths.logic_tick,
    'poolAllocate':lists.list_pool_allocate,'poolRecycle':paths.recycle_wrapper,'addRange':lists.add_range,
    'clear':lists.list_clear,'time':paths.time_getter,'timer':paths.timer_predicate,
    'queueAdd':paths.queue_add,'iterationFind':paths.iteration_find,'iterationInsert':paths.iteration_insert,
    'actionEnter':paths.action_enter,'actionExecute':paths.action_execute,'beforeEnter':paths.before_enter,
    'resetExecuteResult':paths.reset_execute_result,'pushActionContext':paths.push_action_context,
    'pushBlackboardContext':paths.push_blackboard_context,'contextPushDispatch':paths.context_push_dispatch,
    'listCount':paths.list_count}
NAMED={'tick':(EXECUTOR,'Tick',1),'logicTick':(EXECUTOR,'_DoLogicTick',1),
    'actionEnter':(ACTION,'Enter',0),'actionExecute':(ACTION,'DoExecute',1),
    'beforeEnter':(NODE,'BeforeEnter',0),'resetExecuteResult':(ACTION,'_ResetExecuteResult',0),
    'pushActionContext':(EXECUTOR,'PushContext',0),'pushBlackboardContext':(BLACKBOARD,'PushContext',1)}


def _programs(p):
    from scripts.game_data.memorypack import leveldata_patrol_event_dispatch_programs as enclosing
    b=p['imageBase'];h=p['sources']
    g={k:f(packets.raw(h[k],b),b+h[k]['entryRva'])for k,f in PROFILES.items()}
    g['insertEmpty']=lists.insert_range_snapshot(packets.raw(h['insert'],b),b+h['insert']['entryRva'],count=0)
    g['poolSpare']=[lists.spare_pool_allocate(packets.raw(h['allocate'],b),b+h['allocate']['entryRva'],spare_count=n)for n in(1,2,4096)]
    g['enclosing']=enclosing.invoke_executor(packets.raw(p['enclosingSource'],b),b+p['enclosingSource']['entryRva'],invoked=True)
    return norm(g)


def _state(p,g):
    s=p['executorSource']['proof']['programs']['tryInvoke']['successState'];required={
        'timer108':0,'executeTimeStamp120':0,'currentAction112':None,'isStarted104':True,'isFinished105':False,
        'delay124':False,'delayAllow125':False,'ticking128':False,'ticked129':False}
    need('coherent-fresh-success-scalar-state',all(k in s and type(s[k])is type(v)and s[k]==v for k,v in required.items()))
    need('actual-false-force-positive-source',p['executorSource']['proof']['programs']['tryInvoke'].get('selectedForceFlag')is False)
    need('coherent-single-cursor-result-and-empty-iteration-state',
        s['cursorStack']==dict(fieldOffset=64,size=1,element='same header._nextID Int32 bits')and
        s['previousResultStack']==dict(fieldOffset=72,size=1,element=True)and
        s['iteratedNodeSet']==dict(fieldOffset=56,count=0))
    return dict(tryInvokeSuccessState=s,tickInputState=g['logicTick']['inputState'],tickOutputState=g['logicTick']['outputState'],
        sameExecutorAndIncomingEventParamsRequired=True,forceInputRequired=False,outputDelayRequired=False,
        trackedExecutorUidRequiredNonzero=True,timeDeltaRequired=0,childExecutorListCountRequired=0,
        actionCallbacksRequiredState=g['logicTick']['selectedState'],
        managerPostTickRequired=dict(isStarted=True,isFinished=False,outputDelay=False),
        queue=dict(fieldOffset=144,spareCapacityRequired=True,valueBytes=16,sameExecutorAndNonzeroUid=True),
        selectedFirstTickStateCompatible=True,liveStateObserved=False)


def _callbacks(p,g):
    c=p['poolSupportSource']['proof'];b=p['imageBase']
    return dict(actionEnter=dict(slot=16,callbackOffset=576,methodInfoOffset=584,
            nominalDeclaration=p['callbackDeclarations']['actionEnter'],ordinaryAbiRequired=True,selectionObserved=False),
        actionExecute=dict(slot=15,callbackOffset=560,methodInfoOffset=568,
            nominalDeclaration=p['callbackDeclarations']['actionExecute'],ordinaryAbiRequired=True,selectionObserved=False),
        contextPush=dict(slot=11,callbackOffset=496,methodInfoOffset=504,
            nominalDeclaration=p['callbackDeclarations']['contextPush'],excludedInlineTargetRvas=[x-b for x in g['contextPushDispatch']['excludedInlineCallbacks']],
            ordinaryAbiRequired=True,selectionObserved=False),
        listCount=dict(targetRva=p['sources']['listCount']['entryRva'],methodDefinition=p['listCountRegistration']['definition'],
            actualCanonicalClassArguments=p['listCountRegistration']['classArguments'],
            requiredClosedList=LIST+'<'+PTR+'>',compatibleClosedStorageRequired=True,
            callbackAndMethodInfoSelectionRequired=True,canonicalPointerEquivalenceProved=False,selectionObserved=False),
        poolRelease=dict(c['requiredRuntimeCallbacks']['release'],requiredClosedPayload=PTR,
            requiredClosedList=LIST+'<'+PTR+'>',requiredPayloadBytes=16),
        poolRecycle=dict(c['requiredRuntimeCallbacks']['recycle'],requiredClosedPayload=LIST+'<'+PTR+'>',
            requiredPayloadBytes=8,requiredClosedElement=PTR,requiredElementBytes=16),
        uid=p['executorSource']['proof']['requiredCallbacks']['uid'],
        authoredCallbackEffectsProved=False,liveCallbackSelectionObserved=False)


def _usage(own,b,site,u):
    need('actual-typed-usage-site',u['instructionRva']==site['instructionVa']-b and u['usageCellRva']==site['cellVa']-b)
    mem={a+i:x for a,s in packets.raw(own,b)for i,x in enumerate(s)};raw=bytes.fromhex(u['instructionHex'])
    need('full-actual-typed-instruction',raw==bytes(mem[site['instructionVa']+i]for i in range(len(raw))))
    encoded=bytes.fromhex(u['usageRawHex']);word=int.from_bytes(encoded,'little')
    need('typed-usage-unresolved-cell',len(encoded)==8 and word>>32==0 and word&1==1 and type(u['tag'])is int and word>>29==u['tag'])
    index=(word&0x1fffffff)>>1
    if u['tag']==6:
        need('typed-methodspec-encoded-index',type(u['methodSpecIndex'])is int and u['methodSpecIndex']==index and
            isinstance(u['methodSpec'],list)and len(u['methodSpec'])==3 and all(type(x)is int for x in u['methodSpec'])and
            u['methodSpec'][0]>=0 and u['methodSpec'][1]>=0 and u['methodSpec'][2]==-1)
    else:
        need('typed-class-encoded-index',u['tag']==1 and type(u['typeIndex'])is int and u['typeIndex']==index and len(bytes.fromhex(u['typeRawHex']))==16)


def _joins(p,g):
    b=p['imageBase'];h=p['sources'];e=p['executorSource']['proof'];c=p['poolSupportSource']['proof']
    def target(role,call):need('exact-actual-E8-or-tail:'+role,call['targetVa']==b+h[role]['entryRva'])
    for key,role in(('tryToInvoke','tryInvoke'),('onInvoked','onInvoked'),('objectPtrImplicit','implicit'),('listAdd','queueAdd')):
        target(role,g['enclosing']['actualCalls'][key])
    for key,role in(('allocate','poolAllocate'),('addRange','addRange'),('clear','clear'),('recycle','poolRecycle'),('time','time'),('tick','tick')):
        target(role,g['onInvoked']['actualCalls'][key])
    target('logicTick',g['tick']['logicTickCall'])
    mapping={'timerBefore':'timer','timerAfter':'timer','pushExecutor':'pushExecutor','contextValid':'valid',
        'contextValidAgain':'valid','executorUid':'uid','executorUidAgain':'uid','actionExecutorValid':'valid',
        'executorValid':'valid','iterationFind':'iterationFind','iterationInsert':'iterationInsert',
        'resetActionIteration':'clean','enter':'actionEnter','execute':'actionExecute','scopeDispose':'scopeDispose'}
    for key,role in mapping.items():target(role,g['logicTick']['actualCalls'][key])
    for key in('actionEnter','actionExecute'):
        for role,call in g[key]['actualCalls'].items():
            if role=='prepare':need('same-actual-class-preparation',call['targetVa']==b+e['classPreparation']['actualEntryRva']);continue
            target('pushActionContext'if role=='pushContext'else role,call)
    target('barrier',dict(targetVa=g['resetExecuteResult']['tailBarrierTargetVa']))
    for key,role in(('getContext','getContext'),('getContextAgain','getContext'),('pushBlackboardContext','pushBlackboardContext'),('implicit','implicit'),('barrier','barrier')):
        target(role,g['pushActionContext']['actualCalls'][key])
    for key,role in(('contextPushDispatch','contextPushDispatch'),('getScopeStack','getScopeStack'),('scopePush','scopePush')):
        target(role,g['pushBlackboardContext']['actualCalls'][key])
    need('same-context-push-class-preparation',g['contextPushDispatch']['prepareTargetVa']==b+e['classPreparation']['actualEntryRva'])
    for key in('pushExecutor','getContext','valid','uid','scopeDispose','scopePush','scopePop','getScopeStack','clean','implicit','ready','barrier'):
        need('same-complete-independently-replayed-executor-helper:'+key,same_packet(h[key],e['sources'][key]))
    support={'poolAllocate':'pool','addRange':'addRange','clear':'clear','allocate':'allocate','insert':'insert',
        'compatible':'compatible','countDispatch':'countDispatch','recycleBackend':'recycle','releaseInvoke':'invoke',
        'release':'release','push':'push'}
    for key,role in support.items():need('same-complete-independently-replayed-pool-helper:'+key,same_packet(h[key],c['helpers'][role]))
    need('same-release-Clear-source',same_packet(h['clear'],c['helpers']['releaseClear']))
    need('actual-pool-Allocate-backend',g['poolAllocate']['backendTargetVa']==b+h['allocate']['entryRva'])
    need('actual-pool-Recycle-backend',g['poolRecycle']['backendTargetVa']==b+h['recycleBackend']['entryRva'])
    need('actual-AddRange-InsertRange-tail',g['addRange']['insertRangeTargetVa']==b+h['insert']['entryRva'])
    for key in('poolAllocate','poolRecycle'):
        for call in g[key]['calls']:
            expected=b+(e['sources']['ready']['entryRva']if call['role']in('ready','readyContext')else c['helpers']['indexed']['entryRva'])
            need('same-actual-ready-indexed',call['targetVa']==expected)
    need('same-Time-singleton-ready-indexed',g['time']['readyTargetVa']==b+h['ready']['entryRva']and
        g['time']['indexedTargetVa']==b+c['helpers']['indexed']['entryRva'])
    uses=p['typedUsages'];own=g['onInvoked']['typedUsageSites'];need('finite-own-OnInvoked-contexts',set(uses['onInvoked'])==set(own))
    for key,u in uses['onInvoked'].items():
        _usage(h['onInvoked'],b,own[key],u)
        if key.startswith('listPoolClass'):
            need('exact-own-ListPool-class',u['tag']==1 and u['typeName']==POOL+'<'+PTR+'>');continue
        owner,name,args={
            'listPoolAllocate':(POOL,'Allocate',[PTR]),'listPoolRecycle':(POOL,'Recycle',[PTR]),
            'listAddRange':(LIST,'AddRange',[PTR]),'listClear':(LIST,'Clear',[PTR]),
            'timeSingleton':('Beyond.ExplicitSingleton`1','get_instance',['Beyond.TimeManager'])}[key]
        need('exact-own-closed-method-request',u['tag']==6 and [u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']]==[owner,name,args,[]])
        d=p['typedDefinitions'][key]
        need('exact-own-MethodSpec-declaration',d['definition']==u['methodSpec'][0]and d['owner']==owner and d['name']==name and
            type(d['flags'])is int and type(d['slot'])is int and len(d['parameters'])==(1 if key in('listPoolRecycle','listAddRange')else 0))
    need('actual-parent-queue-closed-requests',same(p['enclosingSource'],e['enclosingSource']))
    need('same-actual-try-invoke',same_packet(h['tryInvoke'],e['sources']['tryInvoke']))
    need('positive-actual-timer-epsilon',p['epsilon']['entryRva']==g['timer']['epsilonVa']-b and
        len(bytes.fromhex(p['epsilon']['regions'][0][1]))==4)
    epsilon=struct.unpack('<f',bytes.fromhex(p['epsilon']['regions'][0][1]))[0]
    need('finite-positive-timer-epsilon',math.isfinite(epsilon)and epsilon>0)
    packets.raw(p['epsilon'],b)
    return dict(exactCallerAndEverySelectedChildSourceJoined=True,
        ownClosedPoolAndListRequestsProved=True,trackedExecutorAndActionCallbackStateRequired=True,
        emptyChildSnapshotNoRecursiveInvocation=True,firstActionThenPositiveDelayReturnProved=True,
        authoredCallbacksOrRuntimeEffectsProved=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import leveldata_patrol_event_sources as event
    from scripts.game_data.memorypack import leveldata_patrol_event_collection_sources as collection
    from scripts.game_data.memorypack import leveldata_patrol_executor_sources as executor
    _publication_gate(image,pins);b=image.pe.image_base;ctx=NativeReferenceContext(image)
    ex=executor.derive(image,pins);ec=collection.derive(image,pins);ep=ex['proof'];cp=ec['proof'];h={};methods={}
    def add(key,target,span=None):
        need('one-owned-role:'+key,key not in h or h[key]['entryRva']==target-b)
        if key not in h:h[key]=packets.packet(image,target,span=span)
        return h[key]
    h['tryInvoke']=ep['sources']['tryInvoke'];own=ep['enclosingSource']
    main=event.dispatch.invoke_executor(packets.raw(own,b),b+own['entryRva'],invoked=True)
    for key,call in main['actualCalls'].items():
        if key=='tryToInvoke':continue
        add({'objectPtrImplicit':'implicit','listAdd':'queueAdd'}.get(key,key),call['targetVa'])
    on=paths.on_invoked(packets.raw(h['onInvoked'],b),b+h['onInvoked']['entryRva'])
    for key,call in on['actualCalls'].items():add({'allocate':'poolAllocate','recycle':'poolRecycle'}.get(key,key),call['targetVa'])
    tick=paths.tick(packets.raw(h['tick'],b),b+h['tick']['entryRva']);add('logicTick',tick['logicTickCall']['targetVa'])
    logic=paths.logic_tick(packets.raw(h['logicTick'],b),b+h['logicTick']['entryRva'])
    mapping={'timerBefore':'timer','timerAfter':'timer','pushExecutor':'pushExecutor','contextValid':'valid',
        'contextValidAgain':'valid','executorUid':'uid','executorUidAgain':'uid','actionExecutorValid':'valid',
        'executorValid':'valid','iterationFind':'iterationFind','iterationInsert':'iterationInsert',
        'resetActionIteration':'clean','enter':'actionEnter','execute':'actionExecute','scopeDispose':'scopeDispose'}
    for key,role in mapping.items():add(role,logic['actualCalls'][key]['targetVa'])
    for key in('actionEnter','actionExecute'):
        g=PROFILES[key](packets.raw(h[key],b),b+h[key]['entryRva'])
        for role,call in g['actualCalls'].items():
            if role=='prepare':continue
            if role=='barrier':h[role]=ep['sources'][role];continue
            add('pushActionContext'if role=='pushContext'else role,call['targetVa'],20 if role=='ready'else None)
    g=paths.push_action_context(packets.raw(h['pushActionContext'],b),b+h['pushActionContext']['entryRva'])
    for key,call in g['actualCalls'].items():
        role='getContext'if key=='getContextAgain'else key
        if role=='barrier':h[role]=ep['sources'][role]
        else:add(role,call['targetVa'])
    g=paths.push_blackboard_context(packets.raw(h['pushBlackboardContext'],b),b+h['pushBlackboardContext']['entryRva'])
    for role,call in g['actualCalls'].items():add(role,call['targetVa'])
    for key in('scopePop','ready','barrier'):h[key]=ep['sources'][key]
    support={'allocate':'allocate','insert':'insert','compatible':'compatible','countDispatch':'countDispatch',
        'recycleBackend':'recycle','releaseInvoke':'invoke','release':'release','push':'push'}
    for key,role in support.items():h[key]=cp['helpers'][role]
    md=image.metadata;td=ctx.index.types[LIST];cm=[m for m in md.methods_for(td)if md.string(m.name_index)=='get_Count']
    need('one-own-List-count-definition',len(cm)==1);cm,=cm
    rows=GenericEntries(image).observe(cm.index,['Beyond.ObjectPtr`1<object>'],[]);nonzero=[x for x in rows if x['pointer']]
    need('one-independent-List-count-registration',len(nonzero)==1);cr,=nonzero;add('listCount',cr['pointer'],4)
    for key,(owner,name,arity)in NAMED.items():methods[key]=_method(image,ctx,owner,name,arity=arity,target=b+h[key]['entryRva'])
    def declaration(owner,name,n):
        ms=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and m.parameter_count==n]
        need('unique-own-callback-declaration:'+owner+'.'+name,len(ms)==1);m,=ms;ptr=image.method_pointer_va(m)
        return dict(owner=owner,name=name,definition=m.index,slot=m.slot,flags=m.flags,
            parameters=[ctx.type_name(v.type_index)for v in md.parameters_for(m)],returns=ctx.type_name(m.return_type),
            targetRva=ptr-b if ptr else None,actualCallbackSelectionObserved=False)
    callback={key:declaration(owner,name,n)for key,owner,name,n in(
        ('actionEnter',ACTION,'OnEnter',0),('actionExecute',ACTION,'Execute',1),('contextPush',CONTEXT,'OnPushContext',0))}
    timer=paths.timer_predicate(packets.raw(h['timer'],b),b+h['timer']['entryRva'])
    p=dict(imageBase=b,enclosingSource=own,sources=h,methods=methods,executorSource=ex,poolSupportSource=ec,
        epsilon=packets.packet(image,timer['epsilonVa'],span=4),callbackDeclarations=callback,
        listCountRegistration=dict(definition=cm.index,slot=cm.slot,classArguments=['Beyond.ObjectPtr`1<object>'],rows=rows),
        fields={name:_fields(image,ctx,name,ancestors=name not in('Beyond.TimeManager','Beyond.ExplicitSingleton`1'))for name in(EXECUTOR,ACTION,NODE,CONTEXT,'Beyond.TimeManager','Beyond.ExplicitSingleton`1')})
    p['typedUsages']=dict(onInvoked={k:derive_typed_usage_context(image,v['instructionVa']-b,label='patrolManager.'+k)for k,v in on['typedUsageSites'].items()})
    p['typedDefinitions']={}
    for key,u in p['typedUsages']['onInvoked'].items():
        if u['tag']!=6:continue
        m=md.methods[u['methodSpec'][0]]
        p['typedDefinitions'][key]=dict(definition=m.index,owner=image.type_name(m.declaring_type),name=md.string(m.name_index),
            flags=m.flags,slot=m.slot,parameters=[ctx.type_name(v.type_index)for v in md.parameters_for(m)],returns=ctx.type_name(m.return_type))
    from scripts.game_data.il2cpp.context import type_parameter_owner
    singleton=ctx.index.types['Beyond.ExplicitSingleton`1'];sf=[f for f in md.fields_for(singleton)if ctx.field_attributes(f.type_index)&16]
    need('one-declared-static-singleton-field',len(sf)==1);sf,=sf
    fr=image.pe.bytes_at_va(ctx.type_pointer(sf.type_index),16);parameter=int.from_bytes(fr[:8],'little')
    reciprocal=type_parameter_owner(md.buf,parameter,[t.generic_container_index for t in md.types],source='patrolManager.Singleton')
    gm=md.methods[p['typedUsages']['onInvoked']['timeSingleton']['methodSpec'][0]]
    p['singletonContext']=dict(typeDefinition=singleton.index,genericContainer=singleton.generic_container_index,
        fieldDefinition=sf.index,fieldName=md.string(sf.name_index),fieldRawHex=fr.hex().upper(),
        returnRawHex=image.pe.bytes_at_va(ctx.type_pointer(gm.return_type),16).hex().upper(),reciprocal=reciprocal)
    p['programs']=_programs(p);p['crossStageState']=_state(p,p['programs']);p['joins']=_joins(p,p['programs']);p['requiredRuntimeCallbacks']=_callbacks(p,p['programs'])
    v=norm(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,proof=p,
        selectedNormalManagerPostambleEffectsProved=True,selectedFirstTrackedActionTickEffectsProved=True,
        authoredActionEffectsProved=False,allNativeAlternativesProved=False,runtimeInvocationObserved=False,playbackProved=False,
        conditions=['Exact same tracked executor, EventParams and valid stable ActionContext as the successful false-force TryToInvoke; actual class, ready and MethodInfo selections and compatible normal ABI are required.',
            'Nonnull empty child executor list; empty spare pooled List with compatible16-byte ObjectPtr elements; OnGet null and the proved OnRelease Clear callback; spare recycle stack and queue capacity; disabled collector.',
            'One nonnegative initial cursor and true previous result. Iteration Dictionary<Int32,Int32> is initialized empty with positive non-three bucket length, empty selected bucket and spare entry; comparer null.',
            'Time singleton delta is zero. The selected mapped ActionBase already refers to the same nonzero executor UID. Ordinary OnPushContext/DoClean/OnEnter/Execute callbacks preserve the stated executor/table/scope state and return normally; the execute callback publishes the explicit result/next/positive delay state. Authored callback effects and actual selection are not inferred.',
            'All singleton, class, pool, container, callback and registration identities are stable runtime conditions; no live object, activation, scheduling, action execution or playback was observed.']))
    validate(v,pins);_publication_gate(image,pins);return v


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_event_collection_sources as collection
    from scripts.game_data.memorypack import leveldata_patrol_executor_sources as executor
    need('envelope',value.get('schema')==SCHEMA and value.get('status')==STATUS and value.get('nativeInputs')==pins)
    need('conditional-flags',all(value.get(k)is True for k in('selectedNormalManagerPostambleEffectsProved','selectedFirstTrackedActionTickEffectsProved'))and
        all(value.get(k)is False for k in('authoredActionEffectsProved','allNativeAlternativesProved','runtimeInvocationObserved','playbackProved')))
    p=value['proof'];b=p['imageBase'];executor.validate(p['executorSource'],pins);collection.validate(p['poolSupportSource'],pins)
    expected=set(PROFILES)|{'tryInvoke','pushExecutor','valid','uid','clean','scopeDispose','getContext','scopePush','scopePop','getScopeStack','implicit','ready','barrier',
        'allocate','insert','compatible','countDispatch','recycleBackend','releaseInvoke','release','push'}
    need('finite-exact-source-role-set',set(p['sources'])==expected)
    need('same-native-inputs',p['executorSource']['nativeInputs']==p['poolSupportSource']['nativeInputs']==pins)
    need('same-native-image-base',p['executorSource']['proof']['imageBase']==p['poolSupportSource']['proof']['imageBase']==b)
    g=_programs(p);need('full-pure-selected-byte-replay',same(g,p['programs']))
    need('coherent-cross-stage-state',same(_state(p,g),p['crossStageState']))
    need('exact-source-joins',same(_joins(p,g),p['joins']))
    need('runtime-callback-boundary',same(_callbacks(p,g),p['requiredRuntimeCallbacks']))
    need('finite-own-named-methods',set(p['methods'])==set(NAMED))
    need('finite-own-typed-definition-set',set(p['typedDefinitions'])=={k for k,u in p['typedUsages']['onInvoked'].items()if u['tag']==6})
    for key,(owner,name,n)in NAMED.items():
        m=p['methods'][key];need('own-named-target:'+key,m['owner']==owner and m['name']==name and len(m['parameters'])==n and
            m['targetRva']==p['sources'][key]['entryRva']and all(type(m[k])is int and m[k]>=0 for k in('definition','slot','targetRva')))
    need('finite-own-callback-declarations',set(p['callbackDeclarations'])=={'actionEnter','actionExecute','contextPush'})
    for key,owner,name,n,slot in(('actionEnter',ACTION,'OnEnter',0,16),('actionExecute',ACTION,'Execute',1,15),('contextPush',CONTEXT,'OnPushContext',0,11)):
        m=p['callbackDeclarations'][key];need('own-action-callback-slot',m['owner']==owner and m['name']==name and len(m['parameters'])==n and m['slot']==slot and m['returns']=='void')
    need('callback-outside-explicit-inline-context-arms',b+p['callbackDeclarations']['contextPush']['targetRva']not in g['contextPushDispatch']['excludedInlineCallbacks'])
    rows=[x for x in p['listCountRegistration']['rows']if x['pointer']];need('one-own-count-registration',len(rows)==1)
    row,=rows;need('exact-actual-count-pointer-definition',row['pointer']==b+p['sources']['listCount']['entryRva']and
        p['listCountRegistration']['definition']in row['methodDefinitionIndices']and row['runtimeSelectionObserved']is False)
    need('unaliased-canonical-List-count-request',p['listCountRegistration']['classArguments']==['Beyond.ObjectPtr`1<object>']and
        type(p['listCountRegistration']['definition'])is int and p['listCountRegistration']['slot']==34 and
        row['methodInstantiation']['index']==-1 and row['registration']['methodSpecIndex']==row['methodSpecIndex'])
    need('count-callback-outside-dispatch-inline-arms',b+p['sources']['listCount']['entryRva']not in p['poolSupportSource']['proof']['programs']['countDispatch'][0]['excludedInlineTargets'])
    def field(t,owner,name,typ,off):return dict(owner=owner,name=name,typeName=typ,offset=off,static=False)in p['fields'][t]['fields']
    need('own-physical-executor-value-and-list-fields',all(field(EXECUTOR,EXECUTOR,name,typ,off)for name,typ,off in(
        ('subExecutorList',LIST+'<'+PTR+'>',96),('isStarted','bool',104),('isFinished','bool',105),('timer','float',108),
        ('currentAction',ACTION,112),('executeTimeStamp','float',120),('delayToNextTick','bool',124),('<ticking>k__BackingField','bool',128),('<ticked>k__BackingField','bool',129))))
    need('own-action-fields',all(field(ACTION,ACTION,name,typ,off)for name,typ,off in(
        ('m_executeResult','bool',100),('m_finishThread','bool',101),('m_nextID','int',104),('m_reservedID','int',108),('m_delayToNext','float',112),
        ('m_delayToNextTick','bool',116),('m_extraThreadIDList',LIST+'<int>',120),('m_waitForExtraUidList',LIST+'<string>',128))))
    need('own-node-runtime-state-and-executor-storage',all(field(NODE,NODE,name,typ,off)for name,typ,off in(
        ('<executor>k__BackingField',PTR,40),('<context>k__BackingField',CONTEXT,56),('<runTime>k__BackingField','int',72),
        ('<state>k__BackingField',NODE+'+State',76))))
    need('own-time-logic-delta-field',field('Beyond.TimeManager','Beyond.TimeManager','m_scaledLogicDeltaTime','float',44))
    static=[x for x in p['fields']['Beyond.ExplicitSingleton`1']['fields']if x['static']and x['offset']==0]
    need('own-singleton-static-VAR0-reference',len(static)==1 and static[0]['typeName'].startswith('VAR['))
    sc=p['singletonContext'];r=sc['reciprocal'];fr=bytes.fromhex(sc['fieldRawHex']);rr=bytes.fromhex(sc['returnRawHex'])
    container=struct.unpack('<iiii',bytes.fromhex(r['containerRawHex']));parameter=struct.unpack('<iihhHH',bytes.fromhex(r['parameterRawHex']))
    need('reciprocal-singleton-class-VAR0',container==(sc['typeDefinition'],1,0,r['parameterIndex'])and r['typeIndex']==sc['typeDefinition']and
        r['ordinal']==0 and r['containerIndex']==sc['genericContainer']==parameter[0]and parameter[4]==0)
    need('same-owned-singleton-field-and-getter-VAR0',len(fr)==len(rr)==16 and fr[10:12]==rr[10:12]==b'\x13\x00'and
        int.from_bytes(fr[:8],'little')==int.from_bytes(rr[:8],'little')==r['parameterIndex']and
        static[0]['typeName']=='VAR['+str(r['parameterIndex'])+']'and static[0]['name']==sc['fieldName'])
    need('own-explicit-Single-Execute-parameter',p['callbackDeclarations']['actionExecute']['parameters']==['float']and
        p['callbackDeclarations']['actionExecute']['targetRva']is None and p['callbackDeclarations']['actionExecute']['flags']&1024)
    need('conditions-retained',isinstance(value.get('conditions'),list)and len(value['conditions'])==5)
    return dict(selectedNormalManagerPostambleEffectsProved=True,runtimeInvocationObserved=False,playbackProved=False)
