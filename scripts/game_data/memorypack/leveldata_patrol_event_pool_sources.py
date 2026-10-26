"""Selected EventParams ObjectPool callbacks and scope disposal effects.

Erased pool callback source is checked independently, with actual closed Event
selection conditional. Fresh dictionary initial state remains a named boundary.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_event_recycler_sources as recycler
from scripts.game_data.memorypack import leveldata_patrol_event_pool_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_pool_dispatch_programs as dispatch
from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_programs as cleanup_programs
from scripts.game_data.memorypack import leveldata_patrol_event_params_sources as scope
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_storage_sources as capture

SCHEMA='endfield.story-patrol-event-pool-callback-sources.v1'


def need(check,condition):
    if not condition:raise ValueError('patrolEventPoolSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _metadata(image):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    ctx=NativeReferenceContext(image);ge=GenericEntries(image);result={}
    fields=[f for f in image.metadata.fields_for(ctx.index.types[scope.OBJECT_POOL])
        if image.metadata.string(f.name_index)=='m_stack']
    need('one-own-object-pool-stack-declaration',len(fields)==1)
    result['objectPoolStackDeclaration']=dict(name='m_stack',typeName=ctx.type_name(fields[0].type_index),
        declaringType=scope.OBJECT_POOL,instantiatedFieldOffsetClaimed=False)
    for role,name in(('allocate','_OnAllocate'),('recycle','_OnRecycle')):
        m=source._single_method(ctx,scope.OBJECT_POOL,name,1)
        rows=ge.observe(m.index,['object'],[])
        need('own-erased-pool-callback-body-'+role,len(rows)==1 and rows[0].get('pointer'))
        result[role]=dict(method=[m.index,scope.OBJECT_POOL,name],parameters=source._parameter_type(ctx,m),
            returns=ctx.type_name(m.return_type),registration=rows[0],
            actualEventClosedRegistrations=ge.observe(m.index,[scope.EVENT],[]),canonicalClosedEventPointerEquivalenceProved=False)
    interface=ctx.index.types['Beyond.PoolCore.IReusable'];md=image.metadata
    result['interfaceMethods']=[dict(index=m.index,name=md.string(m.name_index),slot=m.slot,
        parameters=source._parameter_type(ctx,m),returns=ctx.type_name(m.return_type))for m in md.methods_for(interface)]
    return result


def require_metadata(m):
    need('actual-declared-object-stack',m['objectPoolStackDeclaration']==dict(name='m_stack',
        typeName='System.Collections.Generic.Stack`1<object>',declaringType=scope.OBJECT_POOL,instantiatedFieldOffsetClaimed=False))
    for role,name in(('allocate','_OnAllocate'),('recycle','_OnRecycle')):
        row=m[role];need('own-pool-callback-signature-'+role,row['method'][1:]==[scope.OBJECT_POOL,name]
            and row['parameters']==['object']and row['returns']=='void'
            and row['method'][0]in row['registration']['methodDefinitionIndices']
            and row['canonicalClosedEventPointerEquivalenceProved']is False)
    rows=m['interfaceMethods'];need('own-two-IReusable-methods',len(rows)==2
        and[(r['name'],r['parameters'],r['returns'])for r in rows]==[('OnAllocate',[],'void'),('OnRecycle',[],'void')])
    return m


def _replay(p,base,symbols,parent):
    r=lambda n:helpers.regions(p[n],base);e=lambda n:base+p[n]['entryRva'];s={k:base+v for k,v in symbols.items()}
    clear=parent['proof']['clearSource'];cp=clear['proof']['packets']
    callbacks=dict(allocate=base+cp['blackboardAllocate']['entryRva'],recycle=base+cp['reusableRecycle']['entryRva'])
    wrappers={role:cleanup_programs.object_pool_callback_program(r(role+'Callback'),e(role+'Callback'),
        compatible=e('compatible'),dispatch=e(role+'Dispatch'),recycle=role=='recycle')for role in callbacks}
    # The complete wrapper grammar consumes save5/push1/sub4 before this load.
    for role in callbacks:wrappers[role]['interfaceClassSiteVa']=e(role+'Callback')+10
    paths={};inductions={}
    for role,callback in callbacks.items():
        paths[role],inductions[role]=dispatch.paths(r(role+'Dispatch'),e(role+'Dispatch'),recycle=role=='recycle',
            prepare=s['prepare'],callback=callback)
    return dict(recycle=[programs.recycle_program(r('genericRecycle'),e('genericRecycle'),context_type=s['context_type'],
            type_from_context=s['type_from_context'],action=e('action'),push=e('push'),below_max=ma,below_min=mi)
            for ma,mi in((True,False),(False,True),(False,False))],
        callbackWrappers=wrappers,interfaceDispatch=paths,interfaceInduction=inductions,
        compatible=[dispatch.interface_compatibility_program(r('compatible'),e('compatible'),ready_type=e('readyType'),
            prepare=s['prepare_inner'],misses=n)for n in range(4)],readyType=dispatch.ready_type_program(r('readyType'),e('readyType')),
        recycleAction=scope.programs.action_program(r('action'),e('action'),callback=e('recycleCallback')),
        push=cleanup_programs.stack_push_program(r('push'),e('push')),
        virtualClear=scope.programs.virtual_event_program(r('virtualInvoke'),e('virtualInvoke'),prepare=s['prepare'],
            callback=base+cp['clear']['entryRva'],slot=10),
        virtualRecycle=scope.programs.virtual_event_program(r('virtualInvoke'),e('virtualInvoke'),prepare=s['prepare'],
            callback=base+clear['proof']['scopeSource']['proof']['packets']['recycle']['entryRva'],slot=9))


def _usage_gates(usages,programs,base):
    for role in('allocate','recycle'):
        for key in('wrapper','dispatch'):
            u=usages[role+key];p=programs['callbackWrappers'][role]if key=='wrapper'else programs['interfaceDispatch'][role][0]
            need('own-IReusable-usage-'+role+key,u['tag']==1 and u['typeName']=='Beyond.PoolCore.IReusable'
                and u['instructionRva']==p['interfaceClassSiteVa']-base)
    p=programs['recycle'][0];u=usages['push']
    need('own-declared-object-Stack-Push',u['typeName']=='System.Collections.Generic.Stack`1'and u['methodName']=='Push'
        and u['classArguments']==['object']and u['methodArguments']==[]
        and programs['push']['incomingMethodInfoNotReadOnSelectedPath']is True
        and u['instructionRva']==p['stackPushMethodInfoSiteVa']-base)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    _publication_gate(image,pins);parent=recycler.derive(image,pins);base=image.pe.image_base
    clear=parent['proof']['clearSource'];sp=clear['proof']['scopeSource']['proof'];meta=require_metadata(_metadata(image));p={}
    p['genericRecycle']=sp['packets']['generic_recycle'];p['action']=sp['packets']['action'];p['virtualInvoke']=sp['packets']['virtual_invoke']
    p['push']=parent['proof']['packets']['push']
    for role in('allocate','recycle'):
        p[role+'Callback']=source._body(image,meta[role]['registration']['pointer'])
        p[role+'Dispatch']=source._body(image,scope._tail(p[role+'Callback'],base))
    p['compatible']=source._body(image,scope._at_call(p['allocateCallback'],base,39))
    calls=[t for a,t in source._calls(p['compatible'],base)]
    need('actual-interface-ready-and-preparation-calls',len(calls)>=4 and calls[0]==calls[1]and calls[2]==calls[3])
    p['readyType']=source._body(image,calls[0])
    old=parent['proof']['poolSource'];classes=old['proof']['storageSource']['proof']['classes']
    symbols=dict(prepare=base+classes['preparation']['entryRva'],prepare_inner=calls[2],
        context_type=base+parent['proof']['symbolRvas']['context_type'],type_from_context=base+parent['proof']['symbolRvas']['type_from_context'])
    need('same-preparation-inner',symbols['prepare_inner']==base+classes['preparationInnerRva'])
    symbol_rvas={k:v-base for k,v in symbols.items()};facts=_replay(p,base,symbol_rvas,parent)
    sites={role+key:(facts['callbackWrappers'][role]['interfaceClassSiteVa']if key=='wrapper'
            else facts['interfaceDispatch'][role][0]['interfaceClassSiteVa'])for role in('allocate','recycle')for key in('wrapper','dispatch')}
    sites['push']=facts['recycle'][0]['stackPushMethodInfoSiteVa']
    usages={k:derive_typed_usage_context(image,at-base,label='patrolEventPool.'+k)for k,at in sites.items()}
    _usage_gates(usages,facts,base)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-event-pool-callback-effects',nativeInputs=pins,
        proof=dict(imageBase=base,recyclerSource=parent,metadata=meta,packets=p,symbolRvas=symbol_rvas,programs=facts,usages=usages),
        selectedEventResetAndRecycleCallbackEffectsProved=True,selectedOrdinaryVariableClearEffectsProved=True,
        selectedLastScopeDisposalEffectsProved=True,freshEventDictionaryInitializationProved=False,
        completeAllAllocationBranchesEventParamsEffectsProved=False,canonicalClosedEventPointerEquivalenceProved=False,
        runtimePoolOrCallbackSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Own Clear+ordinary variable recycle+full dictionaries zero-fill; inherited Event reset/recycle callback programs; actual ObjectPool retention/drop and same-reference Stack.Push; Clear-before-Recycle and last Scope16 removal.',
            conditional='Selected existing Event pool and typed MethodInfos, exact delegates/interface callback pairs, source-derived discriminator fallback interval and stable matching interface tables; ready class metadata, disabled collector, valid bounded dictionaries/stacks and spare capacity; successful ordinary allocations/corresponding typed values remain conditional.',
            unresolved=['fresh Event dictionary count/buckets/entries initialization beyond constructors that only set comparer state','cold ScopeStack/list growth and missing/cold pool/registry paths','actual runtime pool/callback/capacity/allocator selection, event dispatch and playback'])))
    validate(value);_publication_gate(image,pins);return value


def validate(value):
    need('own-schema-status',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-event-pool-callback-effects')
    p=value['proof'];parent=p['recyclerSource'];recycler.validate(parent);base=p['imageBase']
    need('same-native-parent',parent['nativeInputs']==value['nativeInputs']and parent['proof']['imageBase']==base)
    require_metadata(p['metadata'])
    for packet in p['packets'].values():helpers.verify_packet(packet)
    expected=_replay(p['packets'],base,p['symbolRvas'],parent)
    need('all-actual-pool-programs-replay',norm(expected)==p['programs']);_usage_gates(p['usages'],expected,base)
    sp=parent['proof']['clearSource']['proof']['scopeSource']['proof']
    for key,oldkey in(('genericRecycle','generic_recycle'),('action','action'),('virtualInvoke','virtual_invoke')):
        need('same-actual-scope-source-'+key,p['packets'][key]==sp['packets'][oldkey])
    for role in('allocate','recycle'):
        need('same-authenticated-erased-callback-'+role,p['metadata'][role]['registration']['pointer']==base+p['packets'][role+'Callback']['entryRva'])
    need('exact-source-flags-with-open-fresh-state',all(value[k]is True for k in('selectedEventResetAndRecycleCallbackEffectsProved','selectedOrdinaryVariableClearEffectsProved','selectedLastScopeDisposalEffectsProved'))
        and all(value[k]is False for k in('freshEventDictionaryInitializationProved','completeAllAllocationBranchesEventParamsEffectsProved',
            'canonicalClosedEventPointerEquivalenceProved','runtimePoolOrCallbackSelectionObserved','runtimeInvocationObserved','playbackProved')))
    return value
