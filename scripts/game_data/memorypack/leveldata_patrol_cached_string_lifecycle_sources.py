"""Conditional cached String-variable Clear/recycle supplement.

The existing three-family owners remain unchanged. Actual String requests are
joined to independently authenticated reference-body callbacks; absent closed
String registrations never establish a pointer alias.
"""
import json

from scripts.game_data.memorypack import leveldata_patrol_cached_string_lifecycle_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_executor_key_sources as key_source
from scripts.game_data.memorypack import leveldata_patrol_event_pool_sources as pools
from scripts.game_data.memorypack import leveldata_patrol_event_recycler_sources as old_recycler
from scripts.game_data.memorypack import leveldata_patrol_event_cleanup_programs as cleanup
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source
from scripts.game_data.memorypack import leveldata_patrol_runtime_type_cache_sources as type_cache

SCHEMA='endfield.story-patrol-cached-string-lifecycle-sources.v1'
STATUS='validated-conditional-cached-string-variable-lifecycle'


def need(check,condition):
    if not condition:raise ValueError('cachedStringLifecycleSources.'+check)


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def norm(v):return json.loads(json.dumps(v))


def _children(p):
    recycler=p['eventPoolSource']['proof']['recyclerSource'];old=recycler['proof']
    return old,old['clearSource']['proof'],p['keySource']['proof']


def _select(registrations,role):
    own=registrations['string'][role];canonical=registrations['object'][role]
    need('bounded-own-String-rows-'+role,len(own['rows'])<=1)
    chosen=own if own['rows']else canonical
    need('one-selected-reference-body-'+role,len(chosen['rows'])==len(chosen['bodies'])==1)
    return chosen['rows'][0],chosen['bodies'][0],not bool(own['rows'])


def _programs(p):
    old,clear,key=_children(p);b=p['imageBase'];pack=old['packets'];sym=old['symbolRvas']
    r=lambda n:packets.regions(pack[n],b);e=lambda n:b+pack[n]['entryRva']
    _,typ,_=_select(p['registrations'],'getType');_,rec,_=_select(p['registrations'],'recycle')
    return dict(
        getType=cleanup.variable_type_program(packets.regions(typ,b),b+typ['entryRva'],from_handle=b+sym['from_handle']),
        getTypeInvoker=cleanup.variable_type_invoker_program(r('typeInvoker'),e('typeInvoker'),prepare=b+sym['prepare'],callback=b+typ['entryRva']),
        recycle=[programs.recycle_interface(r('recycler'),e('recycler'),get_type=e('typeInvoker'),
            context_type=b+sym['context_type'],type_from_context=b+sym['type_from_context'],lookup=e('tryGet'),
            prepare=b+sym['prepare'],callback=b+rec['entryRva'],misses=n)for n in range(4)],
        typedRecycle=cleanup.variable_pool_recycle_program(packets.regions(rec,b),b+rec['entryRva'],
            type_from_context=b+sym['type_from_context'],assignable=e('assignable'),invoke=e('resetInvoker'),singleton=e('singleton'),push=e('push')),
        resetInvoker=cleanup.variable_reset_invoker_program(r('resetInvoker'),e('resetInvoker'),prepare=b+sym['prepare'],callback=e('reset')),
        reset=cleanup.variable_recycle_reset_program(r('reset'),e('reset')),
        stackPush=cleanup.stack_push_program(r('push'),e('push')),
        nextAllocateReset=key['programs']['reset'],
        mixedClear=dict(countLimit=clear['programs']['variables']['countLimit'],
            sameOrdinaryLoopForEveryReturnedValue=True,variableKinds=['int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr','string'],
            maximumSelectedLiveKeys=6,permutationAndSubsetsAllowed=True,
            independentlyProvedMoveNextAndFinalDictionaryFillRequired=True,
            recyclerPreservesEnumeratedDictionaryRequired=True,
            stringConstantValueUntouchedOnRecycle=True,stringConstantValueClearedByNextOnAllocate=True))


def _selections(p):
    out={}
    for role in ('getType','recycle'):
        reg,packet,erased=_select(p['registrations'],role)
        out[role]=dict(selectedCanonicalArguments=['object']if erased else['string'],
            selectedClosedArguments=['string'],pointer=reg['pointer'],sourceEntryRva=packet['entryRva'],
            actualClosedRegistrations=p['registrations']['string'][role]['rows'],
            closedRegistrationAdmitted=not erased,canonicalPointerEquivalenceProved=False,
            actualStringClassAndMethodInfoMustSelectBody=True,runtimeSelectionObserved=False)
    return out


def compose(native,pins):
    p=norm(native);p.pop('nativeInputs',None);p.pop('variableContext',None)
    p['programs']=norm(_programs(p));p['selectedCallbacks']=_selections(p)
    p['dictionaryState']=dict(selectedPreClearKeys=['@event_sender','@event_receiver','id','index','position','@event_key'],
        eventKeyType='string',eventKeyStoredBytes=8,otherValueKinds=['int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr'],
        onlyTheseKeysAndMatchingTypesRequired=True,anySubsetAndOrderAllowed=True,
        countRange=[0,6],afterClear=dict(count=0,freeCount=0,freeList=-1,usedEntriesCleared=True),
        entryCapacityPreserved=True,bucketCapacityPreserved=True,subBlackboardsRequiredEmpty=True,
        previousPoolOwnershipAndDistinctStorageRequired=True,observedRuntimeState=False)
    out=norm(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,proof=p,
        selectedCachedStringClearAndRecycleEffectsProved=True,selectedMixedOrdinaryAndStringClearEffectsProved=True,
        defaultThreeFamilyDomainChanged=False,canonicalStringPointerEquivalenceProved=False,
        runtimePoolOrCallbackSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual String SetValue request and reciprocal contexts; own reference-body type getter and typed recycle; generic interface arm, Type registry lookup, base OnRecycle/reset, spare Stack.Push, full existing Clear enumeration and dictionary fill.',
            conditional='Compatible actual String Type key, closed MethodInfos, variable class, typed pool and callback pair select the independently proved bodies. Pool ownership, finite exact key/type subset, nonzero variable serials, stable disjoint dictionary/stack storage, spare typed stacks, absent replacements, normal returns and disabled collector remain conditions. OnRecycle retains constant value; the independently proved next OnAllocate clears the String reference.',
            unresolved=['actual runtime registry, callback, pool, variable and storage identities','cold/missing registry, stack resize, fresh factory/Activator and special-variable alternatives','actual authored callback effects, activation or playback'])))
    validate(out,pins);return out


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    _publication_gate(image,pins);pool=pools.derive(image,pins);key=key_source.derive(image,pins)
    ctx=NativeReferenceContext(image);ge=GenericEntries(image);metadata=old_recycler.require_metadata(old_recycler._metadata(image));regs={}
    for kind in ('string','object'):
        regs[kind]={}
        for role in ('getType','recycle'):
            rows=ge.observe(metadata[role]['index'],[kind],[])
            regs[kind][role]=dict(rows=rows,bodies=[source._body(image,r['pointer'])for r in rows if r.get('pointer')])
    native=dict(nativeInputs=pins,imageBase=image.pe.image_base,eventPoolSource=pool,keySource=key,
        metadata=metadata,registrations=regs,stringDefinition=dict(index=ctx.index.types['System.String'].index,name='System.String'))
    old=pool['proof']['recyclerSource']['proof']
    native['typeCacheSource']=type_cache.derive(image,pins,entry=image.pe.image_base+old['symbolRvas']['from_handle'])
    value=compose(native,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    need('own-envelope',value.get('schema')==SCHEMA and value.get('status')==STATUS and value.get('nativeInputs')==pins)
    p=value['proof'];pools.validate(p['eventPoolSource']);key_source.validate(p['keySource'],pins)
    need('same-native-pool-and-key',p['eventPoolSource']['nativeInputs']==pins and p['eventPoolSource']['proof']['imageBase']==p['imageBase']==p['keySource']['proof']['imageBase'])
    old,clear,key=_children(p);old_recycler.require_metadata(p['metadata'])
    type_cache.validate(p['typeCacheSource'],pins)
    need('same-actual-TypeFromHandle-child',key_source.same_packet(p['typeCacheSource']['proof']['sources']['handle'],
        clear['recyclerDescendants'][str(old['symbolRvas']['from_handle'])]))
    need('same-fresh-recycler-metadata',same(p['metadata'],old['metadata']))
    need('same-key-variable-pool',same(key['poolSource'],old['poolSource']))
    need('own-String-request',key['typedUsage']['methodArguments']==['string'] and bytes.fromhex(key['literal']['literalHex'])==b'@event_key')
    need('own-String-definition',p['stringDefinition']==dict(name='System.String',
        index=p['typeCacheSource']['proof']['nominalTypes']['string']['typeDefinition']))
    for role in ('getType','recycle'):
        reg,packet,erased=_select(p['registrations'],role);packets.verify_packet(packet)
        args=reg['classInstantiation']['arguments'];method=p['metadata'][role]
        need('own-reference-registration-'+role,len(args)==1 and bytes.fromhex(args[0]['raw_type_record_hex'])[10]==(28 if erased else 14)
            and method['index']in reg['methodDefinitionIndices']and reg['pointer']==p['imageBase']+packet['entryRva']
            and reg['runtimeSelectionObserved']is False and reg['methodInstantiation']['index']==-1)
    expected=_programs(p);need('full-program-replay',same(expected,p['programs']))
    need('selected-callback-shapes',same(_selections(p),p['selectedCallbacks']))
    need('same-type-registry-source-sites',all(r['registryMethodInfoSiteVa']==old['programs']['recycler'][0]['registryMethodInfoSiteVa']
        and r['lookupMethodInfoSiteVa']==old['programs']['recycler'][0]['lookupMethodInfoSiteVa']
        and r['interfaceClassSiteVa']==old['programs']['recycler'][-1]['interfaceClassSiteVa']for r in expected['recycle']))
    need('same-disabled-collector',expected['stackPush']['collectorDisabledFlagVa']==expected['reset']['collectorDisabledFlagVa']
        ==key['programs']['value']['collectorDisabledFlagVa'])
    state=p['dictionaryState'];need('mixed-finite-key-state',state==dict(
        selectedPreClearKeys=['@event_sender','@event_receiver','id','index','position','@event_key'],
        eventKeyType='string',eventKeyStoredBytes=8,otherValueKinds=['int','UnityEngine.Vector3','Beyond.Gameplay.Core.EntityPtr'],
        onlyTheseKeysAndMatchingTypesRequired=True,anySubsetAndOrderAllowed=True,countRange=[0,6],
        afterClear=dict(count=0,freeCount=0,freeList=-1,usedEntriesCleared=True),entryCapacityPreserved=True,
        bucketCapacityPreserved=True,subBlackboardsRequiredEmpty=True,
        previousPoolOwnershipAndDistinctStorageRequired=True,observedRuntimeState=False))
    need('conditional-flags',all(value.get(k)is True for k in('selectedCachedStringClearAndRecycleEffectsProved','selectedMixedOrdinaryAndStringClearEffectsProved'))
        and all(value.get(k)is False for k in('defaultThreeFamilyDomainChanged','canonicalStringPointerEquivalenceProved',
            'runtimePoolOrCallbackSelectionObserved','runtimeInvocationObserved','playbackProved')))
    return value
