"""Selected EventParams pool/scope transfers, with explicit callee frontiers.

This owner reads the selected image, never an observation report. Direct source
and caller MethodSpec identity do not assert a canonical value-type adjustor
alias or observe a live pool, delegate, stack or allocator result.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_checkpoint_sources as producer
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_storage_sources as capture
from scripts.game_data.memorypack import leveldata_patrol_event_params_programs as programs

SCHEMA='endfield.story-patrol-event-params-sources.v1'
EVENT='Beyond.Gameplay.Core.EventParams'
STACK='Beyond.ScopeStack`1'
SCOPE=STACK+'+Scope`1'
STATIC_POOL='Beyond.PoolCore.GenericStaticPool`1'
OBJECT_POOL='Beyond.PoolCore.ObjectPool`1'


def need(check,condition):
    if not condition:raise ValueError('patrolEventParamsSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _at_call(packet,base,offset):
    calls=dict(source._calls(packet,base));at=base+packet['entryRva']+offset
    need('actual-owned-call-site-'+str(offset),at in calls);return calls[at]


def _tail(packet,base):
    cells={base+a+i:b for a,h in packet['regions']for i,b in enumerate(bytes.fromhex(h))};matches=[]
    for row in packet['rows']:
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes'])
        need('actual-owned-tail-row',bytes(cells[at+i]for i in range(len(raw)))==raw)
        if len(raw)==5 and raw[0]==233:
            target=at+5+int.from_bytes(raw[1:],'little',signed=True)
            if target not in cells:matches.append(target)
    need('one-owned-external-tail',len(matches)==1);return matches[0]


def _metadata(image,parent):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    ctx=NativeReferenceContext(image);md=image.metadata;symbols=ContextSymbols(image)
    allocate=md.methods[parent['namedCalls']['allocate']['method'][0]]
    scope=ctx.index.types[SCOPE];stack=ctx.index.types[STACK];event=ctx.index.types[EVENT]
    callback=source._single_method(ctx,EVENT+'+<>c','<get_scopeReusableStack>b__2_0',1)
    recycle=source._single_method(ctx,EVENT,'RecycleByPool',0)
    dispose=md.methods[parent['typedRequests']['dispose']['methodSpec'][0]]
    fields=lambda td:[dict(name=md.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)))for f in md.fields_for(td)]
    method=lambda m:dict(index=m.index,owner=image.type_name(m.declaring_type),name=md.string(m.name_index),slot=m.slot,
        parameters=source._parameter_type(ctx,m),returns=ctx.type_name(m.return_type))
    static,=[f for f in md.fields_for(event)if md.string(f.name_index)=='s_scopeReusableStack']
    need('named-static-scope-field-attribute',bool(ctx.field_attributes(static.type_index)&16))
    return dict(eventDefinition=event.index,eventParent=ctx.type_name(event.parent_index),allocate=method(allocate),
        allocateParameter=symbols.type(ctx.type_pointer(md.parameters_for(allocate)[0].type_index)),
        scopeResult=symbols.type(ctx.type_pointer(allocate.return_type)),scopeDefinition=scope.index,scopeFields=fields(scope),
        stackDefinition=stack.index,stackFields=fields(stack),eventStaticField=[EVENT,ctx.type_name(static.type_index),
            runtime_type_field_offsets(md,image.pe,image.registration,event.index)['s_scopeReusableStack']],
        dispose=method(dispose),callback=method(callback),callbackPointerRva=image.method_pointer_va(callback)-image.pe.image_base,
        recycle=method(recycle),recyclePointerRva=image.method_pointer_va(recycle)-image.pe.image_base,
        scopeContext=symbols.context(scope.index),stackContext=symbols.context(stack.index),
        staticPoolContext=symbols.context(ctx.index.types[STATIC_POOL].index),
        objectPoolContext=symbols.context(ctx.index.types[OBJECT_POOL].index))


def require_metadata(value,parent):
    need('own-EventParams-base',value['eventParent']=='Beyond.Gameplay.ParamBlackboard')
    own=value['allocate'];need('own-EventParams-allocation-declaration',own['owner']==EVENT and own['name']=='Allocate'
        and own['index']==parent['namedCalls']['allocate']['method'][0]and own['parameters']==[EVENT]
        and own['returns']==SCOPE+'<'+EVENT+','+EVENT+'>')
    param=value['allocateParameter'];raw=bytes.fromhex(param['rawHex'])
    need('actual-byref-EventParams-out-argument',param['name']==EVENT and raw[10:12]==bytes((18,32)))
    result=value['scopeResult'];raw=bytes.fromhex(result['rawHex'])
    need('own-constructed-value-Scope-result',raw[10]==21 and raw[11]&128
        and result['definition']['name']==SCOPE and len(result['classArguments'])==2
        and all(t['name']==EVENT and bytes.fromhex(t['rawHex'])[10:12]==bytes((18,0))for t in result['classArguments']))
    fields={f['name']:f['type']for f in value['scopeFields']}
    need('only-own-scope-value-and-stack-fields',set(fields)=={'value','stackRef'})
    formal=fields['value'];owner=formal.get('parameterOwner',{})
    need('own-scope-inner-reciprocal-VAR',bytes.fromhex(formal['rawHex'])[10:12]==bytes((19,0))
        and(owner.get('typeIndex'),owner.get('typeName'),owner.get('ordinal'))==(value['scopeDefinition'],SCOPE,1))
    def same_var(a,b):
        ar=bytes.fromhex(a['rawHex']);br=bytes.fromhex(b['rawHex'])
        return ar[:8]==br[:8]and ar[10:]==br[10:]and a.get('parameterOwner')==b.get('parameterOwner')
    ref=fields['stackRef'];need('own-scope-stack-reference',ref['definition']['name']==STACK
        and len(ref['classArguments'])==1 and same_var(ref['classArguments'][0],formal))
    need('own-static-scope-stack-field',value['eventStaticField']==[EVENT,STACK+'<'+EVENT+'>',0])
    need('own-Dispose-declaration',value['dispose']==dict(index=parent['typedRequests']['dispose']['methodSpec'][0],
        owner=SCOPE,name='Dispose',slot=4,parameters=[],returns='void'))
    cb=value['callback'];need('own-scope-before-pop-callback',cb['owner']==EVENT+'+<>c'
        and cb['name']=='<get_scopeReusableStack>b__2_0'and cb['parameters']==[EVENT]and cb['returns']=='void')
    rc=value['recycle'];need('own-EventParams-recycle-declaration',
        (rc['owner'],rc['name'],rc['slot'],rc['parameters'],rc['returns'])==(EVENT,'RecycleByPool',9,[],'void'))
    for field,owner_name,definition in(('scopeContext',SCOPE,value['scopeDefinition']),('stackContext',STACK,value['stackDefinition'])):
        c=value[field];need('own-'+field,c['definition']==definition and c['typeName']==owner_name and c['isMethod']is False)
    slots={r['relativeSlot']:r for r in value['scopeContext']['entries']}
    need('same-scope-PopScope-context',slots[0]['type']['definition']['name']==STACK
        and len(slots[0]['type']['classArguments'])==1 and same_var(slots[0]['type']['classArguments'][0],formal)and slots[1]['kind']==3
        and(slots[1]['typeName'],slots[1]['methodName'])==(STACK,'PopScope')and len(slots[1]['classArguments'])==1
        and same_var(slots[1]['classArguments'][0],formal))
    expected=((1,'get_Count'),(2,'get_Item'),(4,'Add'),(6,'Invoke'),(7,'RemoveAt'))
    slots={r['relativeSlot']:r for r in value['stackContext']['entries']}
    for index,name in expected:
        r=slots[index];need('own-ScopeStack-call-context-'+str(index),r['kind']==3 and r['methodName']==name
            and r['methodArguments']==[]and len(r['classArguments'])==1)
    for key,owner_name in(('staticPoolContext',STATIC_POOL),('objectPoolContext',OBJECT_POOL)):
        c=value[key];need('own-typed-pool-context',c['typeName']==owner_name and c['isMethod']is False)
    slots={r['relativeSlot']:r for r in value['staticPoolContext']['entries']}
    formal=slots[7]['classArguments'][0]
    need('own-GenericStaticPool-ObjectPool-Allocate-context',slots[7]['kind']==3
        and(slots[7]['typeName'],slots[7]['methodName'])==(OBJECT_POOL,'Allocate')and len(slots[7]['classArguments'])==1
        and bytes.fromhex(formal['rawHex'])[10:12]==bytes((19,0))
        and(formal['parameterOwner']['typeIndex'],formal['parameterOwner']['typeName'],formal['parameterOwner']['ordinal'])==
            (value['staticPoolContext']['definition'],STATIC_POOL,0))
    formal=next(r for r in value['objectPoolContext']['entries']if r['relativeSlot']==17)['type']
    need('own-ObjectPool-reciprocal-VAR',bytes.fromhex(formal['rawHex'])[10:12]==bytes((19,0))
        and(formal['parameterOwner']['typeIndex'],formal['parameterOwner']['typeName'],formal['parameterOwner']['ordinal'])==
            (value['objectPoolContext']['definition'],OBJECT_POOL,0))
    for index,name in((13,'get_countAll'),(16,'Invoke'),(18,'CreateInstance'),(19,'set_countAll'),(20,'Invoke')):
        r=next(r for r in value['objectPoolContext']['entries']if r['relativeSlot']==index)
        need('own-ObjectPool-call-context-'+str(index),r['kind']==3 and r['methodName']==name
            and(r['methodArguments']==[formal]and r['classArguments']==[]if index==18
                else r['classArguments']==[formal]and r['methodArguments']==[]))
    return value


def _replay(p,base,symbols):
    r=lambda n:helpers.regions(p[n],base);e=lambda n:base+p[n]['entryRva'];s={k:base+v for k,v in symbols.items()}
    return dict(allocate=programs.allocate_program(r('allocate'),e('allocate'),**{k:s[k]for k in('pool_allocate','barrier','scope_getter','push')}),
        scopeGetter=programs.scope_getter_program(r('scopeGetter'),e('scopeGetter')),
        genericAllocate=programs.generic_allocate_program(r('genericAllocate'),e('genericAllocate'),
            context_type=s['context_type'],type_from_context=s['type_from_context'],allocate=e('objectPoolAllocate')),
        objectPoolAllocate=[programs.object_pool_allocate_program(r('objectPoolAllocate'),e('objectPoolAllocate'),reuse=reuse,
            factory_invoke=s['factory_invoke'],create_instance=s['create_instance'],factory=factory,on_allocate=on_allocate,new_count_larger=larger)
            for reuse in(False,True)for factory in((False,)if reuse else(False,True))for on_allocate in(False,True)
            for larger in((True,)if reuse else(False,True))],
        dispose=[programs.dispose_program(r('dispose'),e('dispose'),context_type=s['dispose_context_type'],pop=e('pop'),barrier=s['barrier'],empty=empty)for empty in(False,True)],
        push=programs.push_program(r('push'),e('push')),
        pop=[programs.pop_program(r('pop'),e('pop'),action_invoke=s['action_thunk'],barrier=s['barrier'],callback=callback)for callback in(False,True)],
        beforePop=[programs.before_pop_program(r('beforePop'),e('beforePop'),invoke=s['virtual_invoke'],empty=empty)for empty in(False,True)],
        action=programs.action_program(r('action'),e('action'),callback=e('beforePop')),
        recycle=programs.recycle_program(r('recycle'),e('recycle'),recycle=s['generic_recycle']),
        barrier=programs.disabled_barrier_program(r('barrier'),e('barrier')))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _publication_gate(image,pins);parent=producer.derive(image,pins);base=image.pe.image_base
    metadata=require_metadata(_metadata(image,parent),parent)
    p={name:source._body(image,base+parent['symbolRvas'][name])for name in('allocate','dispose')}
    p['producer']=source._body(image,base+parent['method'][3])
    calls=[t for a,t in source._calls(p['allocate'],base)]
    symbols=dict(zip(('pool_allocate','barrier','scope_getter','push'),calls[:4]))
    p.update({name:source._body(image,symbols[symbol])for name,symbol in(
        ('genericAllocate','pool_allocate'),('scopeGetter','scope_getter'),('push','push'))})
    p['objectPoolAllocate']=source._body(image,_tail(p['genericAllocate'],base))
    s=[t for a,t in source._calls(p['genericAllocate'],base)]
    symbols.update(context_type=s[0],type_from_context=s[1],
        factory_invoke=_at_call(p['objectPoolAllocate'],base,337),create_instance=_at_call(p['objectPoolAllocate'],base,368))
    d=[t for a,t in source._calls(p['dispose'],base)]
    need('same-selected-dispose-barrier',d[3]==symbols['barrier']);symbols['dispose_context_type']=d[0]
    p['pop']=source._body(image,d[2]);symbols['action_thunk']=_at_call(p['pop'],base,216)
    raw=image.pe.bytes_at_va(symbols['action_thunk'],5);g=BytesPath([(symbols['action_thunk'],raw)],symbols['action_thunk'])
    action=g.relative('e9');p['actionThunk']=capture._fixed_prefix(image,symbols['action_thunk'],5)
    p['action']=source._body(image,action)
    p['beforePop']=source._body(image,image.method_pointer_va(image.metadata.methods[metadata['callback']['index']]))
    bc=source._calls(p['beforePop'],base);symbols['virtual_invoke']=bc[0][1]
    recycle=source._single_method(NativeReferenceContext(image),EVENT,'RecycleByPool',0)
    p['recycle']=source._body(image,image.method_pointer_va(recycle));symbols['generic_recycle']=_tail(p['recycle'],base)
    p['barrier']=capture._prefix(image,symbols['barrier'],[programs.disabled_barrier_program])
    # These actual selected callees are retained even while their internal
    # effects are outside this first scope-transfer stage.
    for name in('factory_invoke','create_instance','generic_recycle','dispose_context_type','virtual_invoke'):
        try:p[name]=source._body(image,symbols[name])
        except(ValueError,KeyError,RuntimeError):p[name]=capture._fixed_prefix(image,symbols[name],256)
    facts=_replay(p,base,{k:v-base for k,v in symbols.items()});usages={}
    for name,entry in(('poolClass',facts['allocate']['poolClassSiteVa']),('poolAllocate',facts['allocate']['poolMethodInfoSiteVa']),
            ('push',facts['allocate']['pushMethodInfoSiteVa']),('scopeClass',facts['scopeGetter']['ownClassSiteVa']),
            ('recycle',facts['recycle']['recycleMethodInfoSiteVa'])):
        usages[name]=derive_typed_usage_context(image,entry-base,label='patrolEventParams.'+name)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-event-params-scope-transfers',nativeInputs=pins,
        proof=dict(imageBase=base,parentProducer=parent,metadata=metadata,packets=p,symbolRvas={k:v-base for k,v in symbols.items()},programs=facts,usages=usages),
        selectedPoolAndScopeTransfersProved=True,selectedLastScopeRemovalProved=True,
        completeEventParamsResetAndDisposalEffectsProved=False,canonicalDisposePointerEquivalenceProved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Fresh actual producer allocation/Dispose requests, own EventParams/ScopeStack contexts, same-reference pool/Scope16 push and last-element removal, before-pop Clear/Recycle selector order and disabled barrier.',
            conditional='Ready owned contexts and classes, same selected live typed pool/delegates, compatible valid stable EventParams and scope storage, disabled collector, adequate existing scope-list capacity, normal ABI and normally returning selected callees.',
            unresolved=['EventParams factory and OnAllocate delegate effects, ClearVariables and sub-blackboard clearing, ObjectPool recycle effects','cold ScopeStack construction and list growth','actual allocation capacity/success, live pool/delegate selection, event dispatch and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-event-params-scope-transfers')
    p=value['proof'];base=p['imageBase'];parent=p['parentProducer'];s=p['symbolRvas'];packets=p['packets'];facts=p['programs']
    need('same-parent-native-inputs',value['nativeInputs']==parent['nativeInputs'])
    require_metadata(p['metadata'],parent)
    for packet in packets.values():helpers.verify_packet(packet)
    need('same-producer-actual-Allocate-and-Dispose',all(packets[k]['entryRva']==parent['symbolRvas'][k]for k in('allocate','dispose')))
    need('same-nominal-callback-and-recycle-pointers',packets['beforePop']['entryRva']==p['metadata']['callbackPointerRva']
        and packets['recycle']['entryRva']==p['metadata']['recyclePointerRva'])
    for packet,symbol in(('genericAllocate','pool_allocate'),('scopeGetter','scope_getter'),('push','push'),
            ('actionThunk','action_thunk'),('barrier','barrier'),('factory_invoke','factory_invoke'),
            ('create_instance','create_instance'),('generic_recycle','generic_recycle'),
            ('dispose_context_type','dispose_context_type'),('virtual_invoke','virtual_invoke')):
        need('same-actual-callee-packet-'+packet,packets[packet]['entryRva']==s[symbol])
    need('complete-producer-native-window-seam',packets['producer']['entryRva']==parent['method'][3]and packets['producer']['windows']==parent['sourceWindows'])
    rebuilt=producer.producer_program(helpers.regions(packets['producer'],base),base+parent['method'][3],
        {k:base+v for k,v in parent['symbolRvas'].items()},entity_offset=parent['nominalFields']['entity'][2],
        patrol_id_offset=parent['nominalFields']['patrolId'][2],event_key=parent['eventKey']['program']['result'])
    need('full-producer-program-replay',norm(rebuilt)==parent['program'])
    need('full-selected-scope-and-pool-replay',norm(_replay(packets,base,s))==facts)
    need('same-owned-actual-pool-tail',_tail(packets['genericAllocate'],base)==base+packets['objectPoolAllocate']['entryRva'])
    g=BytesPath(helpers.regions(packets['actionThunk'],base),base+s['action_thunk'])
    need('same-actual-Action-invoker-tail',g.relative('e9')==base+packets['action']['entryRva'])
    usages=p['usages'];need('actual-pool-class',usages['poolClass']['tag']==1 and usages['poolClass']['typeName']==STATIC_POOL+'<'+EVENT+'>')
    for name,owner,method in(('poolAllocate',STATIC_POOL,'Allocate'),('push',STACK,'PushScopeValue'),('recycle',STATIC_POOL,'Recycle')):
        u=usages[name];need('own-typed-actual-'+name,u['tag']==6 and(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments'])==(owner,method,[EVENT],[]))
    need('own-scope-static-class',usages['scopeClass']['tag']==1 and usages['scopeClass']['typeName']==EVENT)
    for name,site in(('poolClass',facts['allocate']['poolClassSiteVa']),('poolAllocate',facts['allocate']['poolMethodInfoSiteVa']),
            ('push',facts['allocate']['pushMethodInfoSiteVa']),('scopeClass',facts['scopeGetter']['ownClassSiteVa']),('recycle',facts['recycle']['recycleMethodInfoSiteVa'])):
        need('exact-own-request-site-'+name,usages[name]['instructionRva']==site-base)
    need('same-actual-Dispose-typed-request',parent['typedRequests']['dispose']['typeName']==SCOPE
        and parent['typedRequests']['dispose']['methodName']=='Dispose'and parent['typedRequests']['dispose']['classArguments']==[EVENT,EVENT]
        and parent['typedRequests']['dispose']['methodArguments']==[])
    need('scope-source-only-flags',value['selectedPoolAndScopeTransfersProved']is True and value['selectedLastScopeRemovalProved']is True
        and all(value[k]is False for k in('completeEventParamsResetAndDisposalEffectsProved','canonicalDisposePointerEquivalenceProved','runtimeInvocationObserved','playbackProved')))
    return value
