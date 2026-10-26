"""Compose independently authenticated selected event and executor source effects.

Every component is derived from the same selected image. Exact byte packets and
producer facts join the components; a matching name or address alone cannot
establish the join. Runtime objects, selected callbacks and activation remain
conditions, and no callback's authored behavior or playback is inferred here.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_event_sources as dispatch
from scripts.game_data.memorypack import leveldata_patrol_event_collection_sources as collections
from scripts.game_data.memorypack import leveldata_patrol_event_initialization_sources as initialization

SCHEMA='endfield.story-patrol-event-atomic-sources.v1'
STATUS='validated-conditional-composed-event-executor-sources'


def need(check,condition,detail=None):
    if not condition:raise ValueError('patrolEventAtomic.'+check+(':'+str(detail)[:1000]if detail is not None else''))


def norm(value):return json.loads(json.dumps(value))


def same(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def same_packet(a,b):
    return all(k in a and k in b and same(a[k],b[k])for k in('entryRva','windows','regions'))


def join_packet(check,actual,expected):
    def identity(p):return dict(entryRva=p.get('entryRva'),windows=p.get('windows',[])[:3],
        regionBytes=[len(h)//2 for _,h in p.get('regions',[])[:3]])
    need(check,same_packet(actual,expected),dict(expected=identity(expected),actual=identity(actual)))


def _scope(pool):
    return pool['proof']['recyclerSource']['proof']['clearSource']['proof']['scopeSource']


def _joins(proof,pins):
    d=proof['dispatchSource'];c=proof['collectionSource'];i=proof['initializationSource']
    e=proof['executorSource'];a=proof['copySource'];m=proof['managerSource'];k=proof['keySource'];l=proof['cachedStringLifecycleSource']
    components=(d,c,i,e,a,m,k,l)
    need('same-selected-native-inputs',all(v['nativeInputs']==pins for v in components),
        {v.get('schema'):v.get('nativeInputs')for v in components if v.get('nativeInputs')!=pins})
    base=d['proof']['imageBase']
    need('own-image-base',proof['imageBase']==base)
    need('same-selected-image-base',all(v['proof']['imageBase']==base for v in components))
    dp=d['proof'];cp=c['proof'];ip=i['proof'];ep=e['proof'];ap=a['proof'];mp=m['proof'];kp=k['proof'];lp=l['proof']
    pool=ip['eventPoolSource'];scope=_scope(pool);producer=dp['parent']['proof']['producerSource']
    need('same-exact-checkpoint-producer',same(scope['proof']['parentProducer'],producer))
    need('same-exact-copy-event-pool',same(ap['eventPoolSource'],pool))
    need('same-exact-key-variable-pool',same(kp['poolSource'],pool['proof']['recyclerSource']['proof']['poolSource']))
    need('same-exact-manager-executor-effects',same(mp['executorSource'],e))
    need('same-exact-manager-collection-effects',same(mp['poolSupportSource'],c))
    need('same-exact-cached-string-key-effects',same(lp['keySource'],k))
    need('same-exact-cached-string-event-pool',same(lp['eventPoolSource'],pool))
    seams=[]
    for role in('listener','trigger'):
        join_packet('same-complete-collection-caller-'+role,cp['callers'][role]['source'],dp['sources'][role])
        setup=dp['programs'][role+'Setups'][-1]
        need('same-complete-collection-setup-'+role,same(cp['callers'][role]['program'],setup))
        seams.append(role+' actual caller bytes and complete setup program')
    join_packet('same-exact-executor-manager-caller',ep['enclosingSource'],dp['sources']['invokeExecutor'])
    join_packet('same-exact-manager-postamble-caller',mp['enclosingSource'],dp['sources']['invokeExecutor'])
    join_packet('same-exact-try-invoke-child',mp['sources']['tryInvoke'],ep['sources']['tryInvoke'])
    join_packet('same-exact-assign-child',ep['sources']['assign'],ap['assignPacket'])
    join_packet('copy-assign-packet-self-consistent',ap['assignPacket'],ap['packets']['assign'])
    join_packet('same-exact-event-key-set-child',ep['sources']['eventKeySet'],kp['sources']['set'])
    need('same-exact-event-key-typed-request',same(ep['typedUsages']['eventKeySet'],kp['typedUsage']))
    join_packet('same-exact-event-key-enclosing-caller',ep['sources']['tryInvoke'],kp['enclosingSource'])
    need('all-selected-direct-effect-grants',e.get('selectedNormalDirectEffectsProved')is True
        and a.get('selectedExecutorCachedDeepCopyEffectsProved')is True
        and a.get('selectedOrdinaryVariableCopyAndDictionaryInsertEffectsProved')is True
        and m.get('selectedNormalManagerPostambleEffectsProved')is True
        and k.get('selectedEventKeyStringStoreEffectsProved')is True
        and k.get('selectedActualEventKeyHashAndCollisionEffectsProved')is True
        and l.get('selectedCachedStringClearAndRecycleEffectsProved')is True)
    main=ep['programs']['tryInvoke'];state=mp['crossStageState'];post=ap['postAssignDictionaryState']
    scripts=[v for v in dp['programs']['triggerLoops']if v['mode']=='script']
    need('coherent-actual-false-force-chain',scripts and all(v['executorArguments']['r9d']==0 for v in scripts)
        and main['selectedForceFlag']is False and state['forceInputRequired']is False)
    need('coherent-same-success-state-at-first-tick',same(state['tryInvokeSuccessState'],main['successState'])
        and state['selectedFirstTickStateCompatible']is True and state['outputDelayRequired']is False
        and state['trackedExecutorUidRequiredNonzero']is True and state['liveStateObserved']is False)
    need('coherent-copied-key-absence-before-insert',post['conditionalSourcePostcondition']is True
        and post['observedRuntimeFact']is False and post['guaranteedAbsentKeys']==['@event_key']
        and post['noOtherDestinationEntries']is True and post['freeCount']==0 and post['freeList']==-1
        and post['possibleKeys']==list(ap['domain']['keys'])and'@event_key'not in post['possibleKeys']
        and post['subsequentInsertRequiresOneAdditionalSpareSlot']is True
        and post['noNewKeyWriterBetweenCopyAndSubsequentLookupRequired']is True)
    key_strings=kp['programs']['eventKeyStrings']
    need('same-event-key-collision-and-copied-domain',
        key_strings['collisionEquality']['allowedExistingKeys']==sorted(post['possibleKeys'])
        and key_strings['collisionEquality']['missingNewKeyRequired']is True
        and key_strings['collisionEquality']['equalsResultOnAnyHashCollision']is False
        and key_strings['originalCheckpointKeyDomainChanged']is False)
    mixed=lp['dictionaryState']
    need('same-mixed-key-domain-and-clear-postcondition',set(mixed['selectedPreClearKeys'])==set(post['possibleKeys'])|{'@event_key'}
        and mixed['eventKeyType']=='string'and mixed['eventKeyStoredBytes']==kp['programs']['value']['valueBytes']
        and mixed['afterClear']==dict(count=0,freeCount=0,freeList=-1,usedEntriesCleared=True)
        and mixed['observedRuntimeState']is False)
    # The ordinary listener and script paths complete before the producer's
    # scope is disposed. The copy owner separately requires disjoint source and
    # destination containers and pool-owned copies, so clearing the producer
    # cannot be used as proof that the destination was cleared or retained.
    return dict(producer='same complete fresh producer fact across checkpoint and Event scope',
        collectionSeams=seams,executor='same complete manager and TryToInvoke source packets',
        assignment='same complete _AssignEventParams packet and independently proved distinct-container copy',
        eventKey='same complete SetValue<string> caller, typed request and selected missing-key variable pool effects',
        lifetime='same complete Event pool source across initialization, reset/recycle and executor copy',
        cachedStringLifecycle='same key and Event pool facts, exact mixed key domain, string cleanup and warm Type resolution',
        wholeRepeatedEventCycleProved=False,
        crossStageState='actual false force, nonzero UID, exact success-to-Tick state and copied-key absence',
        eventKeyExtraSpareEntriesRequired=1,
        sameSelectedExecutorContextActionMapAndMappedHeaderRequired=True,
        cachedDestinationAndOriginalProducerRemainDistinctRequired=True,
        interveningCallbacksMustPreserveCopiedKeyDomainAndCapacity=True,
        sourceValidation='each component replays its own authenticated bytes before these equality joins',
        authoredCallbackEffectsProved=False,runtimeSelectionObserved=False)


def _owners():
    from scripts.game_data.memorypack import leveldata_patrol_executor_sources as executor
    from scripts.game_data.memorypack import leveldata_patrol_executor_copy_sources as copy
    from scripts.game_data.memorypack import leveldata_patrol_manager_sources as manager
    from scripts.game_data.memorypack import leveldata_patrol_executor_key_sources as key
    from scripts.game_data.memorypack import leveldata_patrol_cached_string_lifecycle_sources as cached_string
    return executor,copy,manager,key,cached_string


def _flags(value):
    need('conditional-source-flags',all(value.get(k)is True for k in('selectedNormalEventSourceEffectsProved',
        'selectedCollectionAndScopeLifetimeEffectsProved','selectedActionExecutorCallerAndCopyEffectsProved'))
        and all(value.get(k)is False for k in('wholeCheckpointProved','wholeRepeatedEventCycleProved','authoredActionEffectsProved',
            'allNativeAlternativesProved','runtimeInvocationObserved','playbackProved')))


def compose(dispatch_source,collection_source,initialization_source,executor_source,copy_source,manager_source,key_source,cached_string_source,pins):
    proof=dict(imageBase=dispatch_source['proof']['imageBase'],dispatchSource=dispatch_source,collectionSource=collection_source,
        initializationSource=initialization_source,executorSource=executor_source,
        copySource=copy_source,managerSource=manager_source,keySource=key_source,cachedStringLifecycleSource=cached_string_source)
    proof['joins']=_joins(proof,pins)
    value=norm(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,proof=proof,
        selectedNormalEventSourceEffectsProved=True,selectedCollectionAndScopeLifetimeEffectsProved=True,
        selectedActionExecutorCallerAndCopyEffectsProved=True,
        wholeCheckpointProved=False,wholeRepeatedEventCycleProved=False,authoredActionEffectsProved=False,allNativeAlternativesProved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Independently authenticated checkpoint dispatch, selected collection snapshot and recycling, Event reset/disposal, manager and executor direct source, distinct-container typed-value copy, cached string cleanup and warm Type resolution, joined by complete fresh source packets and producer facts.',
            conditional='All component conditions must hold together: coherent ready classes and MethodInfos; the same selected executor, context, action map and mapped header across both arrays; actual compatible listener and action callbacks; stable finite tables, arrays and queues with spare capacity; nonzero coherent ObjectPtr identities; selected pool ownership and disjoint copy containers. The cached dictionary has one spare entry beyond all copied keys, and intervening callbacks preserve that domain and capacity. Ordinary callback ABI, normal returns, disabled collector and the stated selected branches are required. No runtime state is read.',
            unresolved=['actual listener/header/action-map identity and callback selection, registration, activation and completion',
                'authored action effects and actual host/controller ownership or playback',
                'nonselected allocation, cold/growth, alternate scheduling and callback-specialized source branches'])))
    validate(value,pins);return value


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    executor,copy,manager,key,cached_string=_owners();_publication_gate(image,pins)
    value=compose(dispatch.derive(image,pins),collections.derive(image,pins),initialization.derive(image,pins),
        executor.derive(image,pins),copy.derive(image,pins),manager.derive(image,pins),key.derive(image,pins),cached_string.derive(image,pins),pins)
    _publication_gate(image,pins);return value


def validate(value,pins):
    need('own-schema-status-and-native-inputs',value.get('schema')==SCHEMA and value.get('status')==STATUS
        and value.get('nativeInputs')==pins)
    _flags(value);p=value['proof'];executor,copy,manager,key,cached_string=_owners()
    dispatch.validate(p['dispatchSource'],pins);collections.validate(p['collectionSource'],pins)
    initialization.validate(p['initializationSource'])
    executor.validate(p['executorSource'],pins);copy.validate(p['copySource'],pins);manager.validate(p['managerSource'],pins)
    key.validate(p['keySource'],pins)
    cached_string.validate(p['cachedStringLifecycleSource'],pins)
    need('complete-source-equality-joins',same(p['joins'],_joins(p,pins)))
    return value
