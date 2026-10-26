"""Selected offline event dictionary, opaque listener snapshot and pool effects.

Canonical generic bodies retain their actual registration arguments. Their use
on the closed EventListener storage is an explicit target/MethodInfo and layout
condition, never a pointer alias or a closed-formatter admission.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_event_collection_programs as paths

SCHEMA='endfield.story-patrol-event-collection-sources.v1'
MANAGER='Beyond.Gameplay.Core.LevelEventManager'
LISTENER=MANAGER+'+EventListener'
PTR='Beyond.ObjectPtr`1<'+LISTENER+'>'
CANONICAL_PTR='Beyond.ObjectPtr`1<object>'
DICT='System.Collections.Generic.Dictionary`2'
INNER=DICT+'<uint,'+PTR+'>'
LIST='System.Collections.Generic.List`1'
POOL='Beyond.PoolCore.ListPool`1'
POOLED='Beyond.PoolCore.PooledList`1'
OBJECT_POOL='Beyond.PoolCore.ObjectPool`1'


def need(check,condition):
    if not condition:raise ValueError('patrolEventCollectionSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def packet(image,at,span=None):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import packet as owned
    if span is None:return dict(**owned(image,at),boundary='complete-native-owned-family')
    base=image.pe.image_base;b=image.pe.bytes_at_va(at,span)
    return dict(entryRva=at-base,regions=[[at-base,b.hex().upper()]],windows=[dict(startRva=at-base,endRva=at-base+span,
        sha256=hashlib.sha256(b).hexdigest().upper())],boundary='actual-selected-span-no-physical-extent')


def raw(own,base):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import verify_packet,regions
    verify_packet(own);return regions(own,base)


def _scope_target(own,base):
    found=[];marker=bytes.fromhex('488d8c2480000000e8')
    for a,b in raw(own,base):
        for i in range(len(b)-12):
            if b[i:i+len(marker)]==marker:found.append(a+i+13+int.from_bytes(b[i+9:i+13],'little',signed=True))
    need('one-actual-Scope-dispose-site',len(found)==1);return found[0]


def _callback_requirements(p):
    return {role:dict(callbackTargetRva=c['source']['entryRva'],callbackMethodDefinition=c['method'][0],
        methodInfoMethodDefinition=c['method'][0],declaringType=c['method'][1],methodName=c['method'][2],
        actualCanonicalClassArguments=c['classArguments'],requiredClosedPayload=PTR,requiredPayloadBytes=16,
        compatibleClosedStorageRequired=True,selectionObserved=False,canonicalPointerEquivalenceProved=False,
        closedRegistrationAdmitted=False)for role,c in p['callbacks'].items()}


def _canonical(image,ctx,ge,owner,name,args,nargs,*,var=False):
    md=image.metadata;td=ctx.index.types[owner]
    ms=[m for m in md.methods_for(td)if md.string(m.name_index)==name and m.parameter_count==nargs
        and(not var or ctx.type_name(list(md.parameters_for(m))[0].type_index).startswith('VAR['))]
    need('unique-own-canonical-declaration:'+owner+'.'+name,len(ms)==1);m,=ms
    rows=ge.observe(m.index,args,[]);nonnull=[r for r in rows if r['pointer']]
    need('one-actual-canonical-registration:'+owner+'.'+name,len(nonnull)==1)
    return dict(method=[m.index,owner,name],slot=m.slot,parameters=[ctx.type_name(v.type_index)for v in md.parameters_for(m)],
        classArguments=args,methodArguments=[],registrations=rows,source=packet(image,nonnull[0]['pointer']),
        canonicalPointerEquivalenceProved=False,closedRegistrationAdmitted=False)


def _programs(p):
    from scripts.game_data.memorypack.int_list_sources import initialized_class
    from scripts.game_data.memorypack import leveldata_patrol_proxy_storage_programs as storage
    base=p['imageBase'];h=p['helpers'];rr={k:raw(v,base)for k,v in h.items()}
    def one(key,fn,**kw):return fn(rr[key],base+h[key]['entryRva'],**kw)
    result=dict(find=[one('findEntry',paths.find_entry,**kw)for kw in(
        dict(empty=True),dict(hit=False),dict(),dict(misses=(False,),hit=False),dict(misses=(True,),hit=False),
        dict(misses=(False,True)),dict(misses=(True,False)),dict(special_bucket=True),dict(special_bucket=True,misses=(False,True)))],
        tryGet=[one('tryGet',paths.try_get_value,found=f)for f in(False,True)],values=one('values',paths.cached_values),
        pool=one('pool',paths.list_pool_allocate),addRange=one('addRange',paths.add_range),comparer=one('comparer',paths.default_comparer),
        allocate=[one('allocate',paths.spare_pool_allocate,spare_count=n)for n in(1,2,4096)],
        clear=[one('clear',paths.list_clear,old_count=n)for n in(0,1,2,4096)],
        insert=[one('insert',paths.insert_range_snapshot,count=n,interface_steps=i)for n in(0,1,2,3,4096)for i in(0,1,2)],
        scope=[one('scope',paths.scope_dispose,nonnull=f)for f in(False,True)],
        countDispatch=[one('countDispatch',paths.interface_effect_dispatch,kind='count',interface_steps=i)for i in(0,1,2)],
        disposeDispatch=[one('disposeDispatch',paths.interface_effect_dispatch,kind='dispose',interface_steps=i)for i in(0,1,2)],
        count=one('count',paths.values_count),copy=[one('copy',paths.values_copy_to,active=a)for a in((),(True,),(False,),
            (True,False),(False,True),(True,False,True),(True,True,True))],
        dispose=one('dispose',paths.pooled_list_dispose),recycle=[one('recycle',paths.recycle,release=f)for f in(False,True)],
        invoke=one('invoke',paths.release_invoke),release=one('release',paths.release_lambda),
        releaseClear=[one('releaseClear',paths.list_clear,old_count=n)for n in(0,1,2,4096)],push=one('push',paths.stack_push),
        barrier=one('barrier',paths.disabled_barrier),rep=one('rep',paths.rep_zero),
        repDispatch=[one('zero',paths.rep_dispatch,sse=sse)for sse in(False,True)],
        compatible=[storage.compatible_interface_program(BytesPath(rr['compatible'],base+h['compatible']['entryRva']),interface_steps=i)for i in(0,1,2)],
        prepare={k:storage.ready_program(BytesPath(rr['prepare'+k.title()],base+h['prepare'+k.title()]['entryRva']),role=k)for k in('type','offsets','interfaces')})
    result['indexed']=initialized_class(rr['indexed']+rr['indexedReady'],base+h['indexed']['entryRva'],indexed=True)
    # Fill code's immutable tables are data regions, independently hashed.
    zeros=rr['zero']+[(base+v['entryRva'],bytes.fromhex(v['regions'][0][1]))for v in p['zeroTables']]
    result['zero']=[paths.zero_fill(zeros,base+h['zero']['entryRva'],image_base=base,count=n,alignment=a,mode=m)
        for n in(16,32,48,128,144,256,272,288,512,65536)for a in(0,1,15,16,31)for m in('sse','avx','nt')
        if m!='nt'or n<=32 or n-(32-a)>256]
    # Each byte program above ran; repeated selected rows are presentation only.
    def compact(v):
        if isinstance(v,dict):return {k:compact(x)for k,x in v.items()if k!='selectedBytes'}
        if isinstance(v,list):return [compact(x)for x in v]
        return v
    return norm(compact(result))


def _calls(programs):
    for g in programs['find']:
        for c in g['calls']:yield 'comparer'if c['role']=='defaultComparer'else'preparation',c['targetVa']
    for g in programs['tryGet']:yield 'findEntry',g['findEntryTargetVa']
    for g in(programs['pool'],programs['comparer']):
        for c in g['calls']:yield 'ready'if c['role']=='readyContext'else'indexed',c['targetVa']
    yield 'allocate',programs['pool']['backendTargetVa'];yield 'insert',programs['addRange']['insertRangeTargetVa']
    for g in programs['clear']+programs['releaseClear']:
        if g['zeroCall']:yield 'zero',g['zeroCall']['targetVa']
    for g in programs['insert']:
        for c in g['calls']:
            role={'indexedContext':'indexed','compatibleCollection':'compatible','collectionCount':'countDispatch','prepareCollection':'preparation'}[c['role']]
            yield role,c['targetVa']
    for g in programs['scope']:
        if g['tailTargetVa']:yield 'disposeDispatch',g['tailTargetVa']
    for g in programs['countDispatch']+programs['disposeDispatch']:yield 'preparation',g['preparationTargetVa']
    yield 'recycle',programs['dispose']['recycleTargetVa']
    for g in programs['recycle']:
        if g['releaseAction']:yield 'invoke',g['releaseAction']['targetVa']
        yield 'push',g['stackPush']['targetVa']
    yield 'releaseClear',programs['release']['clearTargetVa']
    for g in programs['repDispatch']:yield 'rep',g['repTargetVa']
    for g in programs['copy']:
        if g['outputBarrier']:yield 'barrier',g['outputBarrier']['targetVa']
    for g in programs['compatible']:
        for c in g['calls']:yield {'prepareType':'prepareType','prepareOffsets':'prepareOffsets','prepareInterfaces':'prepareInterfaces'}[c['role']],c['targetVa']


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_event_programs as enclosing,leveldata_patrol_proxy_storage_programs as storage
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    callers={};h={};targets={}
    def add(role,at,span=None):
        need('one-actual-target:'+role,role not in targets or targets[role]==at);targets[role]=at;h[role]=packet(image,at,span);return raw(h[role],base)
    for role,name,prover in(('listener','HasEventListener',enclosing.listener_setup),('trigger','_DoTryInvokeEventActionTriggerList',enclosing.trigger_setup)):
        methods=[m for m in md.methods_for(ctx.index.types[MANAGER])if md.string(m.name_index)==name]
        need('one-own-enclosing-method:'+name,len(methods)==1);m,=methods;at=image.method_pointer_va(m);own=packet(image,at);g=prover(raw(own,base),at)
        callers[role]=dict(method=[m.index,MANAGER,name,at-base],source=own,program=g,
            typedRequests={k:derive_typed_usage_context(image,u['instructionVa']-base,label='patrolEventCollection.'+k)for k,u in g['typedUsageSites'].items()})
        for key,c in g['actualCalls'].items():
            if key in('barrier','barrierAgain'):continue
            mapped={'dictionaryFindEntry':'findEntry','dictionaryTryGetValue':'tryGet','dictionaryValues':'values',
                'listPoolAllocate':'pool','listClear':'clear','listAddRange':'addRange'}[key]
            add(mapped,c['targetVa'])
    add('scope',_scope_target(callers['trigger']['source'],base),29)
    for role,fn,child,field in(('pool',paths.list_pool_allocate,'allocate','backendTargetVa'),
        ('addRange',paths.add_range,'insert','insertRangeTargetVa'),('clear',paths.list_clear,'zero','zeroCall'),
        ('scope',paths.scope_dispose,'disposeDispatch','tailTargetVa')):
        g=fn(raw(h[role],base),targets[role],**({'old_count':1}if role=='clear'else{}));v=g[field];add(child,v['targetVa']if isinstance(v,dict)else v)
    find=paths.find_entry(raw(h['findEntry'],base),targets['findEntry'])
    prep={c['targetVa']for c in find['calls']if c['role']=='prepareComparer'};need('one-own-prepare-comparer',len(prep)==1)
    prepared=preparation.derive(image,pins,target=next(iter(prep)))
    add('comparer',next(c['targetVa']for c in find['calls']if c['role']=='defaultComparer'))
    pool=paths.list_pool_allocate(raw(h['pool'],base),targets['pool']);ready_at=next(c['targetVa']for c in pool['calls']if c['role']=='readyContext')
    ready=ready_context_sources.derive(image,pins,entry=ready_at)
    at=next(c['targetVa']for c in pool['calls']if c['role']=='indexedContext');add('indexed',at,15)
    g=BytesPath(raw(h['indexed'],base),at);g.take('488bc1','4863ca','488b0cc8');add('indexedReady',g.relative('e9'),20)
    insert=paths.insert_range_snapshot(raw(h['insert'],base),targets['insert'])
    for c in insert['calls']:
        if c['role']=='compatibleCollection':add('compatible',c['targetVa'])
        elif c['role']=='collectionCount':add('countDispatch',c['targetVa'])
    compatible=storage.compatible_interface_program(BytesPath(raw(h['compatible'],base),targets['compatible']))
    for c in compatible['calls']:add(c['role'],c['targetVa'])
    callbacks={role:_canonical(image,ctx,ge,owner,name,args,nargs,var=var)for role,owner,name,args,nargs,var in(
        ('copy',DICT+'+ValueCollection','CopyTo',['uint',CANONICAL_PTR],2,False),
        ('count',DICT+'+ValueCollection','get_Count',['uint',CANONICAL_PTR],0,False),
        ('dispose',POOLED,'Dispose',[CANONICAL_PTR],0,False),
        ('recycle',OBJECT_POOL,'Recycle',['object'],1,True),
        ('release',POOL+'+<>c','<.cctor>b__7_0',[CANONICAL_PTR],1,False))}
    for k,v in callbacks.items():h[k]=v['source'];targets[k]=base+v['source']['entryRva']
    recycle=paths.recycle(raw(h['recycle'],base),targets['recycle'])
    add('invoke',recycle['releaseAction']['targetVa']);add('push',recycle['stackPush']['targetVa'])
    release=paths.release_lambda(raw(h['release'],base),targets['release']);add('releaseClear',release['clearTargetVa'])
    copy=paths.values_copy_to(raw(h['copy'],base),targets['copy']);barrier=copy['outputBarrier']['targetVa'];prefix=image.pe.bytes_at_va(barrier,12)
    g=BytesPath([(barrier,prefix)],barrier);g.relative('833d');g.take('00','4c8bc1');ret=g.relative('74',1)
    # The two selected leaf spans are declared individually, never a fake extent.
    h['barrier']=packet(image,barrier,12);tail=packet(image,ret,1);h['barrier']['regions']+=tail['regions'];h['barrier']['windows']+=tail['windows'];targets['barrier']=barrier
    zeros=raw(h['zero'],base);entry=targets['zero'];g=BytesPath(zeros,entry)
    g.take('488bc1','4c8bc9');need('zero-own-image-base',g.relative('4c8d15')==base)
    # Discover all three table displacements from their actual instruction bytes.
    tables=[]
    for a,b in zeros:
        start=0
        while True:
            i=b.find(bytes.fromhex('478b9c9a'),start)
            if i<0:break
            rva=int.from_bytes(b[i+4:i+8],'little');tables.append(packet(image,base+rva,36));start=i+8
    need('exact-three-owned-zero-tables',len(tables)==3 and len({v['entryRva']for v in tables})==3)
    # REP dispatch is selected by an emitted external conditional target.
    rep=[]
    for a,b in zeros:
        for i in range(len(b)-5):
            if b[i:i+2]==bytes.fromhex('0f85'):
                target=a+i+6+int.from_bytes(b[i+2:i+6],'little',signed=True)
                if not any(x<=target<x+len(y)for x,y in zeros):rep.append(target)
    need('one-shared-external-REP-tail',len(set(rep))==1);add('rep',rep[0],16)
    fields={}
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    for name in('Beyond.CombineKey',MANAGER,'Beyond.ObjectPtrUtility'):
        td=ctx.index.types[name];offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        fields[name]=dict(typeDefinition=td.index,fields=[dict(name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),
            offset=offsets.get(md.string(f.name_index)),static=bool(ctx.field_attributes(f.type_index)&16))for f in md.fields_for(td)])
    proof=dict(imageBase=base,callers=callers,helpers=h,callbacks=callbacks,zeroTables=tables,fields=fields,
        readyContext=ready,classPreparation=prepared)
    proof['programs']=_programs(proof)
    proof['requiredRuntimeCallbacks']=_callback_requirements(proof)
    proof['releaseStackRequest']=derive_typed_usage_context(image,recycle['stackPush']['instructionVa']-10-base,label='patrolEventCollection.actualStackPush')
    # The actual instruction is recorded by the program, rather than inferred by
    # offsets in a different generic instantiation.
    for at,b in raw(h['recycle'],base):
        marker=bytes.fromhex('4c8b05')
        for i in range(len(b)-6):
            if at+i+7+int.from_bytes(b[i+3:i+7],'little',signed=True)==recycle['stackPush']['methodInfoCellVa']and b[i:i+3]==marker:
                proof['releaseStackRequest']=derive_typed_usage_context(image,at+i-base,label='patrolEventCollection.actualStackPush')
    value=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-event-collection-sources',nativeInputs=pins,proof=proof,
        selectedDictionaryLookupEffectsProved=True,selectedOpaque16SnapshotEffectsProved=True,selectedPoolReleaseEffectsProved=True,
        countRange=[0,4096],canonicalPointerEquivalenceProved=False,closedRegistrationAdmitted=False,
        runtimeCallbackSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,
        conditions=['Exact manager field136 and closed CombineKey/UInt32/ObjectPtr<EventListener> requests; coherent ready contexts and normal Win64 ABI. Default comparer and inline raw-DWORD equality select the proved lookup path.',
            'Valid acyclic stable dictionary storage, count and free slots within4096. Cached ValueCollection already nonnull; snapshot source entries/count/version stay stable. Physical entries are32 bytes; the selected opaque listener payload is16 bytes. No live table is inspected.',
            'The actual Count, CopyTo, IDisposable, pooled Dispose, Recycle and OnRelease targets and MethodInfos select these independently owned canonical bodies with compatible closed storage. Canonical registration rows retain their object arguments; no canonical pointer or nominal alias and no closed registration admission follows.',
            'A nonnull spare pooled list and backing capacity at least the snapshot size; pool OnGet is null. Clear operates on rank1 zero-based arrays with element size16. Recycler has spare capacity and the selected release lambda calls its own Clear. Disabled collector and coherent ready flags/classes are required.',
            'Zero-fill selected CPU/threshold mode or REP path, valid disjoint writable storage, normal direction flag, and current native code/data. Cold initialization, cache creation, pool construction, array growth, invalid/cyclic storage, changed live callbacks and runtime event dispatch remain outside this source grant.']))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_event_programs as enclosing,leveldata_patrol_class_preparation_sources as preparation
    from scripts.game_data.il2cpp import ready_context_sources
    need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-patrol-event-collection-sources'
        and value.get('nativeInputs')==pins and same(value.get('countRange'),[0,4096])
        and all(value.get(k)is True for k in('selectedDictionaryLookupEffectsProved','selectedOpaque16SnapshotEffectsProved','selectedPoolReleaseEffectsProved'))
        and all(value.get(k)is False for k in('canonicalPointerEquivalenceProved','closedRegistrationAdmitted','runtimeCallbackSelectionObserved','runtimeInvocationObserved','playbackProved')))
    p=value['proof'];base=p['imageBase'];h=p['helpers'];need('image-base',type(base)is int and base>=1<<32)
    ready_context_sources.validate(p['readyContext'],pins);preparation.validate(p['classPreparation'],pins)
    programs=_programs(p);need('complete-pure-selected-source-replay',same(programs,p['programs']))
    need('explicit-selected-callback-identities-and-unaliased-boundary',same(p['requiredRuntimeCallbacks'],_callback_requirements(p)))
    expected={'findEntry','tryGet','values','pool','clear','addRange','scope','allocate','insert','zero','disposeDispatch','comparer',
        'indexed','indexedReady','compatible','countDispatch','prepareType','prepareOffsets','prepareInterfaces','copy','count','dispose',
        'recycle','release','invoke','push','releaseClear','barrier','rep'}
    need('finite-helper-roles',set(h)==expected)
    for role,at in _calls(programs):
        target=base+(p['readyContext']['actualEntryRva']if role=='ready'else p['classPreparation']['actualEntryRva']if role=='preparation'else h[role]['entryRva'])
        need('exact-actual-child-call:'+role,at==target)
    for role,name,prover in(('listener','HasEventListener',enclosing.listener_setup),('trigger','_DoTryInvokeEventActionTriggerList',enclosing.trigger_setup)):
        c=p['callers'][role];need('exact-own-named-enclosing-method',c['method'][1:3]==[MANAGER,name]and c['method'][3]==c['source']['entryRva']and type(c['method'][0])is int)
        g=norm(prover(raw(c['source'],base),base+c['source']['entryRva']));need('actual-enclosing-setup-replay',same(g,c['program']))
        need('all-and-only-actual-caller-typed-sites',set(c['typedRequests'])==set(g['typedUsageSites']))
        for key,u in c['typedRequests'].items():
            s=g['typedUsageSites'][key];_usage(c['source'],base,s['instructionVa'],s['cellVa'],u)
            if key=='listPoolClass':need('actual-closed-pool-class',u['tag']==1 and u['typeName']==POOL+'<'+PTR+'>');continue
            own,args,method={
                'dictionaryMethod':(DICT,['Beyond.CombineKey',INNER],'TryGetValue'),
                'dictionaryTryGetValue':(DICT,['Beyond.CombineKey',INNER],'TryGetValue'),
                'dictionaryValues':(DICT,['uint',PTR],'get_Values'),
                'listPoolAllocate':(POOL,[PTR],'Allocate'),'listClear':(LIST,[PTR],'Clear'),'listAddRange':(LIST,[PTR],'AddRange')}[key]
            need('exact-unretagged-closed-request',u['tag']==6 and same([u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']],[own,method,args,[]]))
        for key,c in g['actualCalls'].items():
            if key in('barrier','barrierAgain'):continue
            mapped={'dictionaryFindEntry':'findEntry','dictionaryTryGetValue':'tryGet','dictionaryValues':'values','listPoolAllocate':'pool','listClear':'clear','listAddRange':'addRange'}[key]
            need('actual-enclosing-E8-target',c['targetVa']==base+h[mapped]['entryRva'])
    need('exact-canonical-callback-roles',set(p['callbacks'])=={'copy','count','dispose','recycle','release'})
    for role,owner,name,args,nargs,slot in(('copy',DICT+'+ValueCollection','CopyTo',['uint',CANONICAL_PTR],2,9),
        ('count',DICT+'+ValueCollection','get_Count',['uint',CANONICAL_PTR],0,17),('dispose',POOLED,'Dispose',[CANONICAL_PTR],0,35),
        ('recycle',OBJECT_POOL,'Recycle',['object'],1,65535),('release',POOL+'+<>c','<.cctor>b__7_0',[CANONICAL_PTR],1,65535)):
        c=p['callbacks'][role];need('own-canonical-declaration-not-alias',c['method'][1:]==[owner,name]and type(c['method'][0])is int
            and type(c['slot'])is int and c['slot']==slot and len(c['parameters'])==nargs and same(c['classArguments'],args)
            and c['methodArguments']==[]and c['canonicalPointerEquivalenceProved']is False and c['closedRegistrationAdmitted']is False
            and same(c['source'],h[role]))
        rows=[r for r in c['registrations']if r['pointer']];need('one-actual-canonical-row',len(rows)==1)
        r,=rows;need('canonical-row-actual-method-and-pointer',r['pointer']==base+h[role]['entryRva']and c['method'][0]in r['methodDefinitionIndices']
            and r['runtimeSelectionObserved']is False and r['methodInstantiation']['index']==-1)
        ms=r['registration']['rawHex'];need('actual-canonical-table-row',len(bytes.fromhex(ms))==16
            and int.from_bytes(bytes.fromhex(ms)[:4],'little')==r['methodSpecIndex']
            and r['registration']['methodSpecIndex']==r['methodSpecIndex'])
    need('exact-selected-callback-not-excluded-inline',base+h['release']['entryRva']not in programs['invoke']['excludedInlineTargets']
        and base+h['count']['entryRva']not in programs['countDispatch'][0]['excludedInlineTargets']
        and base+h['dispose']['entryRva']not in programs['disposeDispatch'][0]['excludedInlineTargets']
        and all(base+h['copy']['entryRva']not in g['copyToExcludedInlineTargets']for g in programs['insert']))
    need('actual-Scope-E8-from-complete-trigger',_scope_target(p['callers']['trigger']['source'],base)==base+h['scope']['entryRva'])
    u=p['releaseStackRequest'];site=programs['recycle'][1]['stackPush'];_usage(h['recycle'],base,base+u['instructionRva'],site['methodInfoCellVa'],u)
    need('actual-object-stack-request-retained',same([u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']],['System.Collections.Generic.Stack`1','Push',['object'],[]]))
    need('three-distinct-selected-zero-tables',len(p['zeroTables'])==3 and len({t['entryRva']for t in p['zeroTables']})==3)
    for t in p['zeroTables']:raw(t,base);need('exact-zero-jump-table-span',t['boundary']=='actual-selected-span-no-physical-extent'
        and len(t['regions'])==1 and t['entryRva']==t['regions'][0][0]and len(bytes.fromhex(t['regions'][0][1]))==36)
    need('zero-tables-actually-read-by-selected-code',set(g['selectedJumpTableRva']for g in programs['zero']if g['selectedJumpTableRva']is not None)=={t['entryRva']for t in p['zeroTables']})
    need('REP-dispatch-own-image-base',all(g['imageBaseVa']==base for g in programs['repDispatch']))
    for role,span in(('scope',29),('indexed',15),('indexedReady',20),('rep',16)):
        need('declared-selected-span:'+role,h[role]['boundary']=='actual-selected-span-no-physical-extent'and len(h[role]['regions'])==1 and len(bytes.fromhex(h[role]['regions'][0][1]))==span)
    need('separate-barrier-spans-no-physical-extent',h['barrier']['boundary']=='actual-selected-span-no-physical-extent'
        and sorted(len(bytes.fromhex(v))for a,v in h['barrier']['regions'])==[1,12])
    for role in set(h)-{'scope','indexed','indexedReady','barrier','rep'}:need('complete-owned-helper:'+role,h[role]['boundary']=='complete-native-owned-family')
    need('one-disabled-collector',programs['tryGet'][1]['collectorFlagVa']==programs['allocate'][0]['collectorFlagVa']
        ==programs['push']['collectorCellVa']==programs['recycle'][0]['collectorCellVa']==programs['barrier']['collectorCellVa'])
    fields=p['fields'];need('finite-nominals',set(fields)=={'Beyond.CombineKey',MANAGER,'Beyond.ObjectPtrUtility'})
    for owner,field,typename,offset,static in(('Beyond.CombineKey','m_index','int',16,False),(MANAGER,'m_eventListeners',DICT+'<Beyond.CombineKey,'+INNER+'>',136,False)):
        # Dictionary source effects use actual physical offsets; metadata proves
        # the exact named enclosing storage independently of open generic fields.
        fs=[v for v in fields[owner]['fields']if v['typeName']==typename and v['static']is static and type(v['offset'])is int and v['offset']==offset]
        need('exact-owned-nominal-field:'+owner,len(fs)==1 and (owner!= 'Beyond.CombineKey'or fs[0]['name']==field))
    return dict(selectedDictionaryLookupEffectsProved=True,selectedOpaque16SnapshotEffectsProved=True,selectedPoolReleaseEffectsProved=True,
        canonicalPointerEquivalenceProved=False,closedRegistrationAdmitted=False,runtimeInvocationObserved=False,playbackProved=False)


def _usage(own,base,at,cell,u):
    cells={a+i:b for a,bb in raw(own,base)for i,b in enumerate(bb)}
    need('actual-usage-coordinate',type(u['instructionRva'])is int and at==base+u['instructionRva']and u['usageCellRva']==cell-base)
    b=bytes(cells[at+i]for i in range(7));need('exact-actual-typed-instruction',b.hex().upper()==u['instructionHex'].upper()
        and b[:3]in(bytes.fromhex('488b05'),bytes.fromhex('488b0d'),bytes.fromhex('488b15'),bytes.fromhex('488b3d'),bytes.fromhex('4c8b05'),bytes.fromhex('4c8b0d'))
        and at+7+int.from_bytes(b[3:],'little',signed=True)==cell)
    word=int.from_bytes(bytes.fromhex(u['usageRawHex']),'little');need('typed-carrier-tag',word&1==1 and word>>29==u['tag'])
    if u['tag']==6:need('actual-MethodSpec-index',(word&((1<<29)-1))>>1==u['methodSpecIndex']and len(u['methodSpec'])==3)
    else:need('actual-type-index',u['tag']==1 and(word&((1<<29)-1))>>1==u['typeIndex'])
