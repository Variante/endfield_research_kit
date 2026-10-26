"""Fresh selected ActionExecutor normal source effects and callback boundaries.

No receiver, active callback or action invocation is observed. The selected
header/index/constant paths have explicit state predicates; Assign and event-key
storage are separately required source supplements with complete packet seams.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_executor_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_value_sources as objects
from scripts.game_data.memorypack.leveldata_patrol_bundle_cache_sources import _method,_fields

SCHEMA='endfield.story-patrol-executor-sources.v1'
EXECUTOR='Beyond.Gameplay.Actions.ActionExecutor'
CONTEXT='Beyond.Gameplay.Actions.ActionContext'
MAP='Beyond.Gameplay.Actions.ActionMapRuntime'
HEADER='Beyond.Gameplay.Actions.ActionHeader'
NODE='Beyond.Gameplay.NodeBase'
MANAGER='Beyond.Gameplay.Actions.ActionExecutorManager'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'


def need(check,condition):
    if not condition:raise ValueError('patrolExecutorSources.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def actual_calls(packet,base,mapper=None):
    from scripts.game_data.memorypack.leveldata_patrol_concat_string_sources import string_rows
    return [(int(r['va'],16),int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True))
        for r in string_rows(packet,base,mapper)if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232]


def _barrier_packet(image,at):
    b=image.pe.image_base;prefix=image.pe.bytes_at_va(at,12)
    need('literal-disabled-collector-prefix',prefix[:2]==bytes.fromhex('833d')and prefix[6:11]==bytes.fromhex('004c8bc174'))
    tail=at+12+int.from_bytes(prefix[11:12],'little',signed=True)
    need('selected-collector-return-byte',image.pe.bytes_at_va(tail,1)==b'\xc3')
    regions=[[at-b,prefix.hex().upper()],[tail-b,'C3']]
    return dict(entryRva=at-b,boundary='actual-selected-spans-no-physical-extent',regions=regions,
        windows=[dict(startRva=a,endRva=a+len(bytes.fromhex(h)),sha256=hashlib.sha256(bytes.fromhex(h)).hexdigest().upper())for a,h in regions])


def _programs(p):
    h=p['sources'];b=p['imageBase'];rr={k:packets.raw(v,b)for k,v in h.items()}
    def one(k,fn,**kw):return fn(rr[k],b+h[k]['entryRva'],**kw)
    g=dict(tryInvoke=one('tryInvoke',paths.try_invoke),getActionMap=one('getActionMap',paths.action_map),
        getContext=one('getContext',paths.get_context),getHeader=one('getHeader',paths.header_hit),setup=one('setup',paths.setup),
        clean=one('clean',paths.clean),pushExecutor=one('pushExecutor',paths.push_executor),getScopeStack=one('getScopeStack',paths.scope_stack_cached),
        scopePush=one('scopePush',paths.scope_push),scopeDispose=one('scopeDispose',paths.scope_dispose),scopePop=one('scopePop',paths.scope_pop),
        pushContext=one('pushContext',paths.push_context_null),headerProcess=one('headerProcess',paths.header_check),
        paramTryGet=one('paramTryGet',paths.param_constant),waitFind=one('waitFind',paths.wait_find_empty),dictionaryClear=one('dictionaryClear',paths.dictionary_empty_clear),
        barrier=one('barrier',paths.barrier_disabled),
        inequality=[one('inequality',paths.inequality,validity_equal=x)for x in(False,True)])
    ready=b+h['ready']['entryRva'];uid=b+h['uid']['entryRva']
    g['implicit']=[one('implicit',objects.implicit_program,prepare=ready,uid=uid,mode=m)for m in('null','zero-uid','nonnull')]
    g['valid']=[one('valid',objects.valid_program,uid=uid,nonnull=x)for x in(False,True)]
    first=one('uid',paths.reusable_uid,image_base=b)
    g['uid']=[one('uid',paths.reusable_uid,image_base=b,case=i)for i in range(len(first['allSelectedTableIndices']))]
    g['tryInvokePositive']=[one('tryInvoke',paths.try_invoke,start_mode=m)for m in('node-uid-null','node-uid-empty','node-uid-unregistered')]
    g['scopeInduction']=dict(countLimit=4096,elementBytes=16,initialSizeRange=[0,4095],
        invariant='For each initial size n in [0,4095], spare array capacity at least n+1 makes push store exactly16 bytes at32+16*n and set size n+1. Normal pop selects n, stores zero16 at the same address, restores size n, and increments version. No signed arithmetic overflow occurs.',
        spareCapacityAndStableNoPopDelegateRequired=True,
        arithmeticChecked=all(32+16*n+16<=32+16*(n+1)and n+1<=4096 for n in range(4096)))
    g['tryInvoke']['successState']=dict(timer108=0,executeTimeStamp120=0,currentAction112=None,isStarted104=True,isFinished105=False,
        delay124=False,delayAllow125=False,ticking128=False,ticked129=False,
        cursorStack=dict(fieldOffset=64,size=1,element='same header._nextID Int32 bits'),
        previousResultStack=dict(fieldOffset=72,size=1,element=True),iteratedNodeSet=dict(fieldOffset=56,count=0),
        incomingEventParamsCopiedSeparatelyRequired=True)
    for normal in g['tryInvokePositive']:normal['successState']=norm(g['tryInvoke']['successState'])
    return norm(g)


METHODS={
    'tryInvoke':(EXECUTOR,'TryToInvoke',3),'enclosing':(MANAGER,'_InvokeExecutor',3),
    'getActionMap':(EXECUTOR,'get_actionMap',0),'getContext':(EXECUTOR,'get_context',0),
    'getHeader':(MAP,'TryGetHeaderNode',2),'assign':(EXECUTOR,'_AssignEventParams',1),
    'setup':(NODE,'SetupExecutor',1),'clean':(NODE,'Clean',0),'pushExecutor':(EXECUTOR,'_PushScope',1),
    'pushContext':(BLACKBOARD,'PushContext',1),'getScopeStack':(BLACKBOARD,'get_scopeStack',0)}
CALLBACKS={'contextPush':(CONTEXT,'OnPushContext',0,11,'void'),'nodeClean':(NODE,'DoClean',0,11,'void'),
    'eventKey':(HEADER,'get_eventKeyString',0,16,'string'),'headerProcess':(HEADER,'Process',1,21,'bool')}
PROFILES={'getActionMap':paths.action_map,'getContext':paths.get_context,'getHeader':paths.header_hit,
    'setup':paths.setup,'clean':paths.clean,'pushExecutor':paths.push_executor,'pushContext':paths.push_context_null,
    'getScopeStack':paths.scope_stack_cached,'scopePush':paths.scope_push,'scopeDispose':paths.scope_dispose,
    'scopePop':paths.scope_pop,'headerProcess':paths.header_check,'dictionaryClear':paths.dictionary_empty_clear,'paramTryGet':paths.param_constant,'waitFind':paths.wait_find_empty}
USAGES={
    'tryInvoke':{'implicitInfo':('Beyond.ObjectPtr`1','op_Implicit',[EXECUTOR],[]),
        'inequalityInfo':('Beyond.ObjectPtr`1','op_Inequality',[EXECUTOR],[]),
        'site5':('Beyond.ObjectPtr`1','Lock',[CONTEXT],[]),
        'site7':('Beyond.ScopeStack`1','PushScopeValue',[BLACKBOARD],[]),
        'eventKeySet':(BLACKBOARD,'SetValue',[],['string']),
        'site11':('Beyond.Gameplay.Actions.ParamExtensions','GetValue',[],['bool']),
        'site12':('Beyond.ScopeStack`1+Scope`1','Dispose',[BLACKBOARD,BLACKBOARD],[]),
        'site13':('Beyond.ScopeStack`1+Scope`1','Dispose',[EXECUTOR,EXECUTOR],[]),
        'site14':('System.Collections.Generic.List`1','Add',['int'],[]),
        'site17':('System.Collections.Generic.Dictionary`2','Clear',['int','int'],[]),
        'site18':('System.Collections.Generic.List`1','Add',['bool'],[]),
        'site20':('Beyond.ObjectPtr`1','Lock',[CONTEXT],[])}}


def _joins(p,g):
    b=p['imageBase'];h=p['sources']
    for role,program in g.items():
        for r in(program if isinstance(program,list)else[program]):
            for c in r.get('calls',[]):
                target=h[c['role']]['entryRva']if c['role']!='prepare'else p['classPreparation']['actualEntryRva']
                need('actual-call-target:'+role+':'+c['role'],c['targetVa']==b+target)
    need('one-own-implicit-context-ready',all(x['preparationTargetVa']==b+h['ready']['entryRva']and x['uidTargetVa']==b+h['uid']['entryRva']for x in g['implicit']))
    need('same-own-UID-source',all(x['uidTargetVa']==b+h['uid']['entryRva']for x in g['valid']))
    need('actual-enclosing-first-E8',p['enclosingCall']['targetVa']==b+h['tryInvoke']['entryRva'])
    need('same-selected-dispatch-collector',g['barrier']['typedSites']['collector']['cellVa']==g['implicit'][-1]['collectorFlagVa']==g['tryInvoke']['typedSites']['site16']['cellVa'])
    sites=g['tryInvoke']['typedSites'];need('same-absent-replacement-root',len({sites[k]['cellVa']for k in('replacementRoot','site4','site6','site8','site19','site21')})==1)
    need('same-closed-context-usage',sites['site5']['cellVa']==sites['site20']['cellVa'])
    for normal in g['tryInvokePositive']:
        need('positive-main-same-own-Lock-context',normal['typedSites']['nodeSite22']['cellVa']==sites['site5']['cellVa']and normal['typedSites']['nodeSite23']['cellVa']==sites['replacementRoot']['cellVa']and normal['typedSites']['nodeSite24']['cellVa']==g['barrier']['typedSites']['collector']['cellVa'])
        need('positive-main-force-false-and-UID-boundary',normal['selectedForceFlag']is False and normal['nodeUidFieldOffset']==24 and normal['nodeArrayFieldOffset']==32)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);b=image.pe.image_base;ctx=NativeReferenceContext(image);h={};methods={};selected={}
    def add(role,target,span=None):
        need('one-selected-helper-target:'+role,role not in h or b+h[role]['entryRva']==target)
        if role not in h:
            h[role]=_barrier_packet(image,target)if role=='barrier'else packets.packet(image,target,span=20 if role=='ready'else span)
        return h[role]
    for k,(owner,name,arity)in METHODS.items():
        methods[k]=_method(image,ctx,owner,name,arity=arity)
        add(k,b+methods[k]['targetRva'])
    main=paths.try_invoke(packets.raw(h['tryInvoke'],b),b+h['tryInvoke']['entryRva'])
    targets={}
    def discover(v):
        for c in v.get('calls',[]):
            if c['role']=='prepare':
                need('one-class-preparation-target','prepare'not in targets or targets['prepare']==c['targetVa']);targets['prepare']=c['targetVa'];continue
            add(c['role'],c['targetVa'])
    discover(main)
    positive=paths.try_invoke(packets.raw(h['tryInvoke'],b),b+h['tryInvoke']['entryRva'],start_mode='node-uid-unregistered');discover(positive)
    # Discover children from byte-exact normal programs, not RVA inventories.
    pending=list(PROFILES);done=set()
    while pending:
        progress=False
        for k in list(pending):
            if k not in h:continue
            v=PROFILES[k](packets.raw(h[k],b),b+h[k]['entryRva']);selected[k]=v;discover(v);done.add(k);pending.remove(k);progress=True
        need('all-normal-helper-source-targets-reached',progress or not pending)
    calls=actual_calls(h['implicit'],b,image.mapper);need('implicit-ready-UID-call-order',len(calls)>=3)
    add('ready',calls[0][1]);add('uid',calls[1][1]);need('same-two-UID-calls',calls[1][1]==calls[2][1])
    rd=ready_context_sources.derive(image,pins,entry=b+h['ready']['entryRva'])
    prep=preparation.derive(image,pins,target=targets['prepare'])
    enclosing=h.pop('enclosing');calls=actual_calls(enclosing,b,image.mapper);need('enclosing-normal-call-present',bool(calls))
    p=dict(imageBase=b,sources=h,methods=methods,enclosingSource=enclosing,enclosingCall=dict(instructionVa=calls[0][0],targetVa=calls[0][1]),
        classPreparation=prep,readyContext=rd,fields={t:_fields(image,ctx,t,ancestors=True)for t in(EXECUTOR,CONTEXT,MAP,HEADER,NODE,'System.String')})
    p['declaredCallbacks']={k:_method(image,ctx,owner,name,arity=n)for k,(owner,name,n,slot,returns)in CALLBACKS.items()}
    p['programs']=_programs(p);p['typedUsages']={}
    for role,claims in USAGES.items():
        p['typedUsages'][role]={k:derive_typed_usage_context(image,p['programs'][role]['typedSites'][k]['instructionVa']-b,label='patrolExecutor.'+role+'.'+k)for k in claims}
    p['typedUsages']['eventKeySet']=p['typedUsages']['tryInvoke']['eventKeySet']
    site=p['programs']['tryInvokePositive'][-1]['typedSites']['nodeWaitDictionary'];p['typedUsages']['waitDictionary']=derive_typed_usage_context(image,site['instructionVa']-b,label='patrolExecutor.waitDictionary')
    p['requiredCallbacks']=_callbacks(p)
    v=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-executor-source',nativeInputs=pins,proof=p,
        selectedNormalDirectEffectsProved=True,assignAndEventKeyEffectsSeparatelyRequired=True,
        allPossibleExecutorBranchesProved=False,liveBindingObserved=False,runtimeInvocationObserved=False,playbackProved=False))
    validate(v,pins);_publication_gate(image,pins);return v


def _callbacks(p):
    g=p['programs'];b=p['imageBase'];uid=g['uid']
    return dict(virtual=g['tryInvoke']['requiredVirtualCalls']+[dict(owner='same selected header',slot=11,callbackOffset=496,methodInfoOffset=504)],
        headerProcess=dict(slot=21,callbackOffset=656,methodInfoOffset=664,selectedTargetVa=g['headerProcess']['typedSites']['site2']['cellVa'],
            exactInlineByteEffectsProved=True,selectionObserved=False),
        uid=dict(classDiscriminatorOffset=284,allowedSelectedDiscriminators=[x['requiredClassDiscriminator']for x in uid],
            nominalDiscriminatorAliasProved=False,selectionObserved=False),
        declaredSlots=p['declaredCallbacks'],
        methods=dict(compatibleActualMethodInfosRequired=True,actualNamedTargetBodiesRequired=True,canonicalPointerAliasProved=False),
        assign=dict(sourceTargetRva=p['sources']['assign']['entryRva'],sameExecutorAndIncomingEventParams=True,effectsSeparatelyRequired=True),
        eventKeySet=dict(sourceTargetRva=p['sources']['eventKeySet']['entryRva'],methodSpec=p['typedUsages']['eventKeySet']['methodSpec'],
            methodArguments=['string'],sameEventParamsReceiverAndHeaderEventKeyRequired=True,effectsSeparatelyRequired=True))


def validate(v,pins):
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    need('envelope',v.get('schema')==SCHEMA and v.get('nativeInputs')==pins and v.get('status')=='validated-conditional-patrol-executor-source'
        and v.get('selectedNormalDirectEffectsProved')is True and v.get('assignAndEventKeyEffectsSeparatelyRequired')is True
        and all(v.get(k)is False for k in('allPossibleExecutorBranchesProved','liveBindingObserved','runtimeInvocationObserved','playbackProved')))
    p=v['proof'];b=p['imageBase'];need('finite-selected-source-family',set(p['sources'])=={'tryInvoke','getActionMap','getContext','getHeader','assign','setup','clean','pushExecutor','pushContext','getScopeStack','implicit','inequality','valid','scopePush','eventKeySet','headerProcess','paramTryGet','scopeDispose','dictionaryClear','ready','barrier','scopePop','uid','waitFind'})
    g=_programs(p);need('complete-normal-source-replay',same(g,p['programs']));_joins(p,g)
    # A separately named request alias is deliberate for the atomic sibling.
    need('exact-typed-source-role-family',set(p['typedUsages'])==set(USAGES)|{'eventKeySet','waitDictionary'})
    t=dict(p['typedUsages']);t.pop('eventKeySet');t.pop('waitDictionary');q=dict(p);q['typedUsages']=t
    _typed_program_sites(q,g)
    u=p['typedUsages']['waitDictionary'];site=g['tryInvokePositive'][-1]['typedSites']['nodeWaitDictionary']
    need('actual-closed-node-wait-dictionary-request',(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments'])==('System.Collections.Generic.Dictionary`2','TryGetValue',['string','Beyond.ObjectPtr`1<'+EXECUTOR+'>'],[])
        and u['instructionRva']==site['instructionVa']-b and u['usageCellRva']==site['cellVa']-b)
    memory={a+i:x for a,raw in packets.raw(p['sources']['tryInvoke'],b)for i,x in enumerate(raw)};code=bytes.fromhex(u['instructionHex'])
    need('full-node-wait-request-instruction',code==bytes(memory[site['instructionVa']+i]for i in range(len(code))))
    need('event-key-set-request-alias',same(p['typedUsages']['eventKeySet'],p['typedUsages']['tryInvoke']['eventKeySet']))
    preparation.validate(p['classPreparation'],pins);ready_context_sources.validate(p['readyContext'],pins)
    need('same-ready-source',same(p['readyContext']['proof']['sourceRegions'],[[b+a,h.lower()]for a,h in p['sources']['ready']['regions']]))
    need('finite-named-method-family',set(p['methods'])==set(METHODS))
    for k,(owner,name,arity)in METHODS.items():
        m=p['methods'][k];need('literal-method-indices:'+k,all(type(m[z])is int and m[z]>=0 for z in('definition','targetRva','flags','slot')));packet=p['enclosingSource']if k=='enclosing'else p['sources'][k]
        need('exact-named-method:'+k,m['owner']==owner and m['name']==name and len(m['parameters'])==arity and m['targetRva']==packet['entryRva'])
    packets.raw(p['enclosingSource'],b)
    calls=actual_calls(p['enclosingSource'],b);need('exact-first-enclosing-call',calls and p['enclosingCall']==dict(instructionVa=calls[0][0],targetVa=calls[0][1]))
    need('enclosing-first-call-in-owned-bytes',p['enclosingCall']['instructionVa']>=b+p['enclosingSource']['entryRva'])
    mem={a+i:x for a,s in packets.raw(p['enclosingSource'],b)for i,x in enumerate(s)};at=p['enclosingCall']['instructionVa']
    need('actual-first-call-instruction',bytes(mem[at+i]for i in range(5))==b'\xe8'+(p['enclosingCall']['targetVa']-at-5).to_bytes(4,'little',signed=True))
    need('exact-nominal-slot-declarations',set(p['declaredCallbacks'])==set(CALLBACKS))
    for k,(owner,name,n,slot,returns)in CALLBACKS.items():
        m=p['declaredCallbacks'][k]
        need('declared-virtual-slot:'+k,m['owner']==owner and m['name']==name and len(m['parameters'])==n and m['slot']==slot and m['returns']==returns
            and all(type(m[z])is int and m[z]>=0 for z in('definition','targetRva','flags','slot')))
    need('same-own-header-Process-inline-marker',p['declaredCallbacks']['headerProcess']['targetRva']+b==g['headerProcess']['typedSites']['site2']['cellVa'])
    fields=p['fields']
    def field(t,owner,name,kind,offset):return dict(owner=owner,name=name,typeName=kind,offset=offset,static=False)in fields[t]['fields']
    need('own-distinct-action-map-arrays',all(field(MAP,MAP,name,kind,offset)for name,kind,offset in(
        ('nodeArray','Beyond.Gameplay.NodeBase[]',32),('headerArray',HEADER+'[]',40),('actionArray','Beyond.Gameplay.Actions.ActionBase[]',48))))
    need('own-start-and-context-fields',field(NODE,NODE,'_ID','int',16)and field(EXECUTOR,EXECUTOR,'startNodeID','int',24)
        and field(CONTEXT,CONTEXT,'actionMap',MAP,112))
    need('own-positive-node-UID-and-string-length',field(NODE,NODE,'_uid','string',24)and field('System.String','System.String','_stringLength','int',16))
    need('own-context-UID-carriers',all(field(t,'Beyond.ReusableObject','<instanceUid>k__BackingField','uint',16)for t in(EXECUTOR,CONTEXT)))
    need('own-context-wait-map-field',field(CONTEXT,CONTEXT,'executorWaitForPossibleExecutorDict','System.Collections.Generic.Dictionary`2<string,Beyond.ObjectPtr`1<'+EXECUTOR+'>>',104))
    need('actual-event-and-cursor-fields',field(EXECUTOR,EXECUTOR,'<eventParams>k__BackingField','Beyond.Gameplay.Core.EventParams',48)
        and field(EXECUTOR,EXECUTOR,'m_cursorStack','System.Collections.Generic.List`1<int>',64)
        and field(EXECUTOR,EXECUTOR,'m_previousExecuteResultStack','System.Collections.Generic.List`1<bool>',72))
    need('exact-callback-and-child-conditions',same(p['requiredCallbacks'],_callbacks(p)))
    return dict(selectedNormalDirectEffectsProved=True,assignAndEventKeyEffectsSeparatelyRequired=True,
        allPossibleExecutorBranchesProved=False,runtimeInvocationObserved=False)


def _typed_program_sites(p,g):
    need('exact-typed-owner-sites',set(p['typedUsages'])==set(USAGES))
    b=p['imageBase']
    for role,claims in USAGES.items():
        values=p['typedUsages'][role];need('exact-typed-role-sites',set(values)==set(claims))
        memory={a+i:x for a,raw in packets.raw(p['sources'][role],b)for i,x in enumerate(raw)}
        for key,expected in claims.items():
            v=values[key];s=g[role]['typedSites'][key]
            need('actual-own-typed-usage:'+key,(v.get('typeName'),v.get('methodName'),v.get('classArguments'),v.get('methodArguments'))==expected
                and v['instructionRva']==s['instructionVa']-b and v['usageCellRva']==s['cellVa']-b)
            code=bytes.fromhex(v['instructionHex']);need('full-typed-instruction:'+key,code==bytes(memory[s['instructionVa']+i]for i in range(len(code))))
