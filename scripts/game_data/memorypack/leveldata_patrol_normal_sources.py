"""Atomic fresh Patrol normal-source supplement composition.

Selected normal source programs are joined by exact values, requests, byte
windows and full parent identities. Native callees still lacking effect proofs
are named separately from runtime identity, capacity and activation conditions.
No report-file input or whole consumer/runtime authority is accepted here.
"""
import copy
import hashlib
import json

SCHEMA='endfield.story-patrol-offline-normal-sources.v2'
ROLES={'lookup','concat','pathHash','pathLock','prefix','byteHash','dataPath','encoding','bufferPool','resourceLookup','resourceHandles','resourceIds','stringScope','resourceValidity','handleGet',
 'initHelpers','checkpointHelpers','checkpointOutput','checkpointValues','checkpointCallees','radioQuery','radioRequest',
 'resourceRequest','retention','radioSend','eventAtomic'}


def need(check,condition):
 if not condition:raise ValueError('storyPatrolNormal.'+check)


def norm(value):return json.loads(json.dumps(value))


def raw(proof):
 windows=proof['sourceWindows'];regions=proof['sourceRegions']
 need('same-owned-window-region-set',bool(windows)and len(windows)==len(regions))
 base=regions[0][0]-windows[0]['startRva'];out=[]
 for window,(at,encoded)in zip(windows,regions):
  value=bytes.fromhex(encoded)
  need('full-owned-window-bytes',window['startRva']==at-base and window['endRva']==at-base+len(value)and
   window['sha256']==hashlib.sha256(value).hexdigest().upper())
  out.append((at,value))
 return base,out


def _source(source,pins,schema,status,flags):
 need('same-owned-source-envelope:'+schema,isinstance(source,dict)and source.get('schema')==schema and
  source.get('status')==status and source.get('nativeInputs')==pins)
 need('no-unproved-runtime-or-whole-promotion:'+schema,source.get('runtimeInvocationObserved')is False and
  source.get('playbackProved')is False and all(source.get(k)is True for k in flags))


def _local_replay(owners,pins):
 from scripts.game_data.memorypack import leveldata_patrol_lookup_sources as lookup
 from scripts.game_data.memorypack import leveldata_patrol_path_sources as path
 from scripts.game_data.memorypack import leveldata_patrol_hash_sources as hashing
 from scripts.game_data.memorypack import leveldata_patrol_asset_sources as asset
 from scripts.game_data.memorypack import leveldata_patrol_resource_sources as resource
 from scripts.game_data.memorypack import leveldata_patrol_resource_lookup_sources as search
 from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as prepare
 from scripts.game_data.il2cpp import ready_context_sources
 lo=owners['lookup'];ha=owners['pathHash'];se=owners['resourceLookup']
 _source(lo,pins,lookup.SCHEMA,'validated-conditional-warm-lookup-caller-sources',
  ['selectedGenericPathHandleForwarderArgumentsAndFramesProved','selectedUnityNullComparisonSourceProved'])
 p=lo['proof'];field=p['nominalCachedPointerField'];need('own-Unity-native-pointer-field',field[:2]==['UnityEngine.Object','nint'])
 for role,parser in(('concat-path',lookup.concat_program),('process-path',lookup.path_program),('Get',lookup.get_program)):
  b,regions=raw(p['sources'][role]);actual=parser(regions,b+p['sources'][role]['entryRva'])
  need('exact-warm-forwarder-replay:'+role,norm(actual)==p['programs'][role]and
   actual['tailTargetVa']-b==p['tailChildren'][role]['entryRva'])
 b,regions=raw(p['sources']['Unity-object-not-equal-null']);entry=b+p['sources']['Unity-object-not-equal-null']['entryRva']
 need('exact-Unity-null-alternatives',norm([lookup.unity_program(regions,entry,nonnull=n,cached_nonzero=c,cached_offset=field[2])
  for n,c in((False,False),(True,False),(True,True))])==p['programs']['Unity-object-not-equal-null'])
 _source(ha,pins,hashing.SCHEMA,'validated-conditional-managed-path-hash-source',['selectedManagedUtf16HashSourceAndLoopProved'])
 hp=ha['proof'];pa=hp['pathSource'];_source(pa,pins,path.SCHEMA,'validated-conditional-warm-nonhash-path-source',
  ['selectedPathArgumentsCachePairAndResultFrameProved'])
 pp=pa['proof'];need('independent-path-and-lookup-source-equality',pp['lookupSource']==lo)
 b,regions=raw(pp);entry=pp['program']['entry']
 need('exact-both-prefix-and-lock-source-replays',norm([path.program(regions,entry),path.program(regions,entry,hash_prefix=True,lock_taken=False),
  path.program(regions,entry,hash_prefix=True,lock_taken=True)])==pp['programs']and pp['programs'][0]==pp['program'])
 need('actual-hash-string-cache-type',pp['cacheField']['typeName']=='System.ValueTuple`2<long,string>')
 ordinary=pp['children']['ordinary'];ob,oregions=raw(ordinary);fields=pp['nominalStringFields']
 need('exact-managed-String-fields',fields['_stringLength'][:2]==['System.String','int']and fields['_firstChar'][:2]==['System.String','char'])
 need('exact-ordinary-string-null-empty-pointer-source',norm([path.ordinary_program(oregions,ob+ordinary['entryRva'],nonnull=n,nonempty=z,
  length_offset=fields['_stringLength'][2],char_offset=fields['_firstChar'][2])for n,z in((False,False),(True,False),(True,True))])==pp['ordinaryPrograms'])
 data=pp['children']['hash-path'];db,dregions=raw(data)
 need('exact-data-path-tail-source',norm(path.data_program(dregions,db+data['entryRva']))==pp['dataProgram'])
 b,regions=raw(hp);entry=pp['ordinaryPrograms'][-1]['hashTargetVa']
 need('exact-hash-bytes-fold-and-loop',norm([hashing.program(regions,entry,first_zero=a,second_zero=z)
  for a,z in((True,False),(False,True),(False,False))])==hp['programs']and hp['codeUnitFold']==hashing.fold_proof()and hp['loopInduction']==hashing.loop_induction())
 _source(se,pins,search.SCHEMA,'validated-conditional-resource-bucket-search-source',['selectedResourceHashBucketSearchAndResultProved'])
 sp=se['proof'];re=sp['resourceSource'];_source(re,pins,resource.SCHEMA,'validated-conditional-resource-request-caller-source',
  ['selectedNormalResourceArgumentsHandleCopiesAndFramesProved'])
 rp=re['proof'];asrc=rp['assetSource'];_source(asrc,pins,asset.SCHEMA,'validated-conditional-asset-tryload-inline-source',
  ['selectedInterfaceAndInlineTryLoadHandleTransferSourceProved'])
 ap=asrc['proof'];need('independent-asset-and-lookup-source-equality',ap['lookupSource']==lo)
 b,regions=raw(ap);entry=ap['programs'][0]['entry'];root,=[f for f in ap['loaderSource']['proof']['parameterFields']
  if f['field']['field'][:2]==['Beyond.Resource.SimpleAssetLoader','Beyond.Resource.RootCategory']]
 need('own-category-byte',root['bytes']==1 and root['backingType']=='byte')
 need('six-complete-asset-interface-and-Bool-programs',norm([asset.program(regions,entry,loaded=l,matched=m,miss_one=n,
  root_category_offset=root['fieldOffset'])for l in(False,True)for m,n in((True,False),(True,True),(False,False))])==ap['programs'])
 prep=ap['children']['prepare-receiver-class'];prepare.validate(prep['preparationSource'],pins)
 need('actual-preparation-source-entry',prep['entryRva']==prep['preparationSource']['actualEntryRva'])
 b,regions=raw(rp);entry=rp['programs'][0]['entry']
 need('four-complete-resource-output-programs',norm([resource.program(regions,entry,available=a,requested=r,created_valid=v)
  for a,r,v in((False,False,False),(True,False,False),(True,True,False),(True,True,True))])==rp['programs'])
 b,regions=raw(sp);entry=sp['programs'][0]['entry'];programs=[search.program(regions,entry,division=d,failures=n,found=f)
  for d in('magic','div')for n in range(4)for f in(False,True)]
 need('full-native-bucket-source-replay',norm(programs)==sp['programs']and norm(search.induction(programs))==sp['recordInduction'])
 p=programs[0];need('all-u64-quotient-arithmetic',search.quotient_proof(p['divisor'],p['multiplier'],p['shift'])==sp['quotientArithmetic'])
 ready_context_sources.validate(sp['metadataHelper'],pins)
 need('actual-search-metadata-identity-source-target',{c['targetVa']-b for p in programs for c in p['metadataCalls']}==
  {sp['metadataHelper']['actualEntryRva']})
 return asrc,ha


def compose(base_source,pins,owners):
 from scripts.game_data.memorypack import leveldata_patrol_offline_sources as base_owner
 from scripts.game_data.memorypack import leveldata_patrol_init_helper_sources as init
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as checkpoint
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_output_sources as output
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_value_sources as values
 from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as handles
 from scripts.game_data.memorypack import leveldata_patrol_resource_id_sources as resource_ids
 from scripts.game_data.memorypack import leveldata_patrol_string_scope_sources as string_scope
 from scripts.game_data.memorypack import leveldata_patrol_prefix_sources as prefix
 from scripts.game_data.memorypack import leveldata_patrol_byte_hash_sources as byte_hash
 from scripts.game_data.memorypack import leveldata_patrol_data_path_sources as data_path,leveldata_patrol_encoding_sources as encoding
 from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as validity,leveldata_patrol_checkpoint_pool_sources as callees
 from scripts.game_data.memorypack import leveldata_patrol_get_sources as handle_get
 from scripts.game_data.memorypack import leveldata_patrol_concat_sources as concat
 from scripts.game_data.memorypack import leveldata_patrol_buffer_pool_sources as buffer_pool
 from scripts.game_data.memorypack import leveldata_patrol_path_lock_sources as path_lock
 from scripts.game_data.memorypack import leveldata_patrol_radio_query_sources as radio_query
 from scripts.game_data.memorypack import leveldata_patrol_radio_request_sources as radio_request
 from scripts.game_data.memorypack import leveldata_patrol_request_sources as resource_request
 from scripts.game_data.memorypack import leveldata_patrol_retention_sources as retention
 from scripts.game_data.memorypack import leveldata_patrol_radio_send_sources as radio_send
 from scripts.game_data.memorypack import leveldata_patrol_event_atomic_sources as event_atomic
 need('exact-normal-owner-set',isinstance(owners,dict)and set(owners)==ROLES)
 need('exact-base-selected-heap-chain',base_source.get('schema')==base_owner.SCHEMA and base_source.get('nativeInputs')==pins and
  base_source.get('status')=='validated-conditional-composed-offline-source-chain'and base_source.get('finitePointCountLimit')==4096 and
  base_source.get('sourceJoins',{}).get('conditionalWarmHeapBackendAndCurrentFillSourcesJoined')is True)
 need('complete-base-source-composition-replay',base_owner.compose({k:base_source['sources'][k]for k in base_owner.OWNER_NAMES},pins,
  heap=base_source['sources']['heap'])==base_source)
 base_owner._same_pins(owners,pins,'normalSources');asrc,hashing=_local_replay(owners,pins)
 initial=owners['initHelpers'];init.validate(initial,pins);check=owners['checkpointHelpers'];checkpoint.validate(check)
 output_source=owners['checkpointOutput'];output.validate(output_source)
 value_source=owners['checkpointValues'];values.validate(value_source,pins)
 need('same-fresh-checkpoint-value-helper-source',value_source['proof']['checkpointSource']==check)
 handle_source=owners['resourceHandles'];handles.validate(handle_source,pins)
 need('same-fresh-resource-handle-caller-parent',handle_source['proof']['resourceLookupSource']==owners['resourceLookup'])
 id_source=owners['resourceIds'];resource_ids.validate(id_source,pins)
 need('same-fresh-resource-constructor-and-ID-caller',id_source['proof']['resourceHandleSource']==handle_source)
 scope_source=owners['stringScope'];string_scope.validate(scope_source,pins)
 need('same-fresh-request-temporary-string-scope',scope_source['proof']['resourceHandleSource']==handle_source)
 request_source=owners['resourceRequest'];resource_request.validate(request_source,pins)
 need('same-fresh-all-direct-request-effects',request_source['proof']['loadSource']['proof']['manifestSource']['proof']['resourceHandleSource']==handle_source
  and request_source['proof']['stringScopeSource']==scope_source)
 prefix_source=owners['prefix'];prefix.validate(prefix_source,pins)
 need('same-fresh-prefix-path-hash-and-lookup',prefix_source['proof']['hashSource']==owners['pathHash'])
 byte_source=owners['byteHash'];byte_hash.validate(byte_source,pins)
 need('same-fresh-byte-hash-path-parent',byte_source['proof']['pathHashSource']==owners['pathHash'])
 data_source=owners['dataPath'];data_path.validate(data_source,pins)
 need('same-fresh-data-path-byte-hash',data_source['proof']['byteHashSource']==byte_source)
 encoding_source=owners['encoding'];encoding.validate(encoding_source,pins)
 need('same-fresh-encoding-data-caller',encoding_source['proof']['dataPathSource']==data_source)
 pool_source=owners['bufferPool'];buffer_pool.validate(pool_source,pins)
 need('same-fresh-byte-pool-data-caller',pool_source['proof']['dataPathSource']==data_source)
 validity_source=owners['resourceValidity'];validity.validate(validity_source,pins)
 need('same-fresh-resource-validity-parent',validity_source['proof']['resourceSource']==owners['resourceLookup']['proof']['resourceSource'])
 get_source=owners['handleGet'];handle_get.validate(get_source,pins)
 need('same-fresh-positive-Get-and-validity',get_source['proof']['resourceValiditySource']==validity_source)
 retention_source=owners['retention'];retention.validate(retention_source,pins)
 need('same-fresh-complete-retention-and-validity',retention_source['proof']['retainSource']['proof']['resourceValiditySource']==validity_source)
 concat_source=owners['concat'];concat.validate(concat_source,pins)
 need('same-fresh-concat-lookup',concat_source['proof']['callerSource']['proof']['lookupSource']==owners['lookup'])
 lock_source=owners['pathLock'];path_lock.validate(lock_source,pins)
 need('same-fresh-path-monitor-caller',lock_source['proof']['pathSource']==owners['pathHash']['proof']['pathSource'])
 query_source=owners['radioQuery'];radio_query.validate(query_source,pins)
 need('same-fresh-range-radio-consumer',query_source['proof']['rangeSource']==base_source['sources']['range'])
 radio_source=owners['radioRequest'];radio_request.validate(radio_source,pins)
 need('same-fresh-range-radio-request-consumer',radio_source['proof']['rangeSource']==base_source['sources']['range'])
 send_source=owners['radioSend'];radio_send.validate(send_source,pins)
 need('same-fresh-radio-send-and-dispatch-parent',send_source['proof']['dispatcherSource']['proof']['parentRadioRequest']==radio_source)
 callee_source=owners['checkpointCallees'];callees.validate(callee_source)
 need('same-fresh-checkpoint-storage-helper',callee_source['proof']['storageSource']['proof']['calleeSource']['proof']['parent']==check)
 event_source=owners['eventAtomic'];event_atomic.validate(event_source,pins)
 need('same-fresh-atomic-event-checkpoint-helper',event_source['proof']['dispatchSource']['proof']['parent']==check)
 need('selected-finite-event-effects-without-authored-or-runtime-promotion',event_source.get('selectedNormalEventSourceEffectsProved')is True and
  event_source.get('authoredActionEffectsProved')is False and event_source.get('allNativeAlternativesProved')is False and
  event_source.get('runtimeInvocationObserved')is False and event_source.get('playbackProved')is False)
 for source,owner,status in((initial,init,'validated-conditional-init-helper-source-slices'),
  (check,checkpoint,'validated-conditional-checkpoint-helper-selected-programs'),
  (output_source,output,'validated-conditional-direct-output-request-sources')):
  _source(source,pins,owner.SCHEMA,status,[])
 need('same-fresh-checkpoint-output-helper-source',output_source['proof']['helperSource']==check)
 need('same-fresh-loader-and-actual-lookup-construction',asrc['proof']['loaderSource']==base_source['sources']['loader']and
  owners['lookup']['proof']['leadSource']==base_source['sources']['loader']['proof']['controllerConstruction']['proof']['lead'])
 need('same-fresh-Init-caller-and-installed-value',initial['proof']['initializerSource']==base_source['sources']['initializer'])
 helpers=base_source['sources']['helpers'];need('same-fresh-checkpoint-producer-and-filter-callers',
  check['proof']['producerSource']==helpers['lookupThunk']['actualProducer']and check['proof']['filterSource']==helpers['baseProcess']['actualFilter'])
 out=copy.deepcopy(base_source);out.update(schema=SCHEMA,status='validated-conditional-composed-normal-patrol-source-chain',
  normalSources=copy.deepcopy(owners),selectedNormalSourceJoinsProved=True,offlineEvidenceExhausted=True,
  offlineEvidenceExhaustionDomain='selected-finite-normal-source-path-only')
 out['sourceJoins'].update(actualPathHashAndStaticCacheSourcesJoined=True,actualAssetInterfaceHandleAndResourceCallerSourcesJoined=True,
  actualDefaultNativeResourceBucketSearchJoined=True,actualEligibilityEntityAndConfigLookupSourcesJoined=True,
  actualCheckpointTypedHelperAndReceiverSourcesJoined=True,actualDirectOutputPredicateSetterAndDelegateSourcesJoined=True,
  actualEntityObjectPointerAndValueAdapterSourcesJoined=True,actualCachedServiceAndCreateHandleCallerSourcesJoined=True,
  actualSelectedAsciiPrefixComparisonSourcesJoined=True,actualZeroThrough127ByteHashArithmeticSourcesJoined=True,
  actualDataPathPoolRequestsAndWholeFrameJoined=True,actualSelectedAsciiEncodingEffectsJoined=True,
  actualResourceValidityTableGetterAndMembershipEffectsJoined=True,actualCheckpointVariableStorageAndResetEffectsJoined=True,
  actualGenericHandleGetInterfaceCacheAndSelectedGetterSourcesJoined=True,actualBoundedThreeStringConcatEffectsJoined=True,
  actualCachedBytePoolRentReturnAndGuardSourcesJoined=True,actualExistingMonitorAcquireQueryAndReleaseEffectsJoined=True,
  actualRangeRadioOrdinalStringQueryEffectsJoined=True,actualRadioPayloadAndClosedRequestSourcesJoined=True,
  actualHandleConstructorCounterAndMembershipEffectsJoined=True,actualTemporaryStringBlockPoolAndCleanupEffectsJoined=True,
  actualCachedRequestManifestKeyLookupAndStateTwoReturnEffectsJoined=True,
  actualWholeHandleNestedHashAndSpareRetentionEffectsJoined=True,actualRadioSendFullFramesAndNoLuaKeyReturnJoined=True,
  actualEventPoolCollectionCopyTypedBindingAndManagerPostambleEffectsJoined=True)
 out['unprovedNativeSourceFrontiers']=[]
 out['nonselectedNativeSourceAlternatives']=[
  dict(role='cold-and-mutable-setup',required='Cold MethodInfo/class/cache construction, exhausted allocation, pool/array growth, table creation/history, lazy Config indexing/logging, replacement/custom-comparer/exceptional and other collector/acceleration paths are outside the selected ready/spare-storage domain.'),
  dict(role='other-input-and-resource-domains',required='Unicode/culture comparisons and encoding, longer inputs, temporary-string creation, resource-cache miss/new-proxy construction, other proxy states and scheduling, arbitrary getter callbacks and nonempty Lua-key/Lua-present branches remain separate native alternatives. No selected source flag admits them.'),
  dict(role='other-event-and-action-paths',required='Fresh Event factory/Activator constructor invocation, cold or exhausted pools, different prior dictionary histories, nonempty recursive executor child lists, other cursor/action schedules and optimized or different callbacks remain nonselected native alternatives. Existing reset/constructor body proofs do not establish those invocations or histories.')]
 out['runtimeCaptureRequirements']=[
  dict(role='controller-and-resource-selection',required='Capture the actual controller/config/Core/lead/asset identities, installed field, selected class/MethodInfo/callbacks, current cache/table entries and source-domain predicates at the matching calls. Static source equality does not observe these values.'),
  dict(role='checkpoint-and-output-activation',required='Capture initialized current storage/pools, typed Param receiver/output binding and actual dynamic setter target/property effect, event registration/callback targets, checkpoint production/delivery and action-map/executor selection.'),
  dict(role='radio-and-playback',required='Capture actual CombineKey bits, EventData payload, current singleton/dispatcher/listener identities and selected delegate target/effect, Lua-key absence and the downstream audio request/playback relationship. No installed nominal method alone establishes live callback identity.')]
 out['runtimeConditions']+=['Actual loaded native resource index, valid bounded stable bucket/record data, chosen backend/service/interface/MethodInfo and live asset/type/handle identities must satisfy the proved source conditions; no such runtime identity is observed.']
 out['runtimeConditions']+=['The selected prefix domain uses ASCII first-five slices; the selected byte-hash domain uses0..127 bytes and a stable compatible secret array of at least128 bytes. Actual callback, input length, secret contents and these runtime selections are not observed.']
 out['runtimeConditions']+=['The concat domain requires total UTF16 length at most128 and the owned ready Type/provider/TLS/builder/cache identities. The data domain requires ASCII code units0..127, actual selected UTF8 callback/MethodInfo pairs, cached byte-pool request1..128, same-thread compatible TLS buffer and no intervening mutation of its cleared slot. No live cached object, callback, thread selection or buffer capacity is observed.']
 out['runtimeConditions']+=['Handle ID construction requires the selected compatible actual proxy/class/discriminator and collector/logging state. Int32 membership uses coherent bounded stable chains and spare storage; promotion uses an existing empty pooled set with capacity at least8. The counter source is modulo32-bit arithmetic, with no uniqueness or atomicity grant.']
 out['runtimeConditions']+=['Temporary UnSafeString scope uses a spare existing block with an empty string stack, an initially empty active block stack with spare capacity, coherent static storage and the actual selected HgStringBlock Dispose callback/MethodInfo. No temporary string is created on this selected request path.']
 out['runtimeConditions']+=['Cached resource request requires the first exact manifest-key hit and selected seeded RuntimeType/key cache hit, bounded stable native records and Int64/reference chains, unchanged Type/callback/import identities, the bounded positive operation counter and literal proxy state2. Whole-handle retention requires the independently proved nested boxed callbacks and spare HashSet storage, without any observed live hash or retention success.']
 out['runtimeConditions']+=['Radio SendGlobal uses ready Singleton<EventManager>/method contexts, the same nonnull EventDispatcher and selected handler/list paths, valid Play56/Stop8 locals and a nonnull Lua-key set whose actual Contains storage is null. Actual bound listener targets, mutation/effects and audio playback remain unobserved.']
 out['runtimeConditions']+=['The finite event domain uses one coherent tracked executor and context, actual false-force header/callback selections, distinct incoming/cached EventParams with the proved prior Clear/reuse history, spare typed dictionaries and queues, empty child-executor list, and the exact first-tick action state. Time delta and callback-preserved/published state must satisfy the manager source conditions together. Actual listeners, authored action callbacks, dictionary/pool contents, output property effects, controller activation and playback remain capture requirements.']
 out['evidenceBoundary']=dict(exact='Fresh independent normal source components, complete byte replay and exact loader/lead/Init/producer/filter identities composed atomically under one selected native input set.',
  conditional='The selected finite normal source path has no remaining direct native-source frontier under all recorded component conditions. Exhaustion refers only to that selected domain; it does not admit other native alternatives or actual authored callbacks.',
  unresolved='Live identity, callback selection/effects, mutable table and pool history, activation and playback still require concrete runtime capture; separately listed nonselected native alternatives remain outside this source grant.')
 return out


def derive(image,pins,*,base_source,stage=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_prefix_sources as prefix,leveldata_patrol_resource_handle_sources as handles
 from scripts.game_data.memorypack import leveldata_patrol_init_helper_sources as initial,leveldata_patrol_checkpoint_output_sources as output
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_value_sources as values
 from scripts.game_data.memorypack import leveldata_patrol_byte_hash_sources as byte_hash
 from scripts.game_data.memorypack import leveldata_patrol_encoding_sources as encoding,leveldata_patrol_resource_validity_sources as validity
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_pool_sources as callees
 from scripts.game_data.memorypack import leveldata_patrol_get_sources as handle_get
 from scripts.game_data.memorypack import leveldata_patrol_concat_sources as concat
 from scripts.game_data.memorypack import leveldata_patrol_buffer_pool_sources as buffer_pool
 from scripts.game_data.memorypack import leveldata_patrol_path_lock_sources as path_lock
 from scripts.game_data.memorypack import leveldata_patrol_radio_query_sources as radio_query
 from scripts.game_data.memorypack import leveldata_patrol_radio_request_sources as radio_request
 from scripts.game_data.memorypack import leveldata_patrol_resource_id_sources as resource_ids
 from scripts.game_data.memorypack import leveldata_patrol_string_scope_sources as string_scope
 from scripts.game_data.memorypack import leveldata_patrol_request_sources as resource_request
 from scripts.game_data.memorypack import leveldata_patrol_retention_sources as retention
 from scripts.game_data.memorypack import leveldata_patrol_radio_send_sources as radio_send
 from scripts.game_data.memorypack import leveldata_patrol_event_atomic_sources as event_atomic
 _publication_gate(image,pins);owners={}
 for role,owner in(('concat',concat),('pathLock',path_lock),('radioQuery',radio_query),('radioSend',radio_send),('prefix',prefix),('encoding',encoding),('bufferPool',buffer_pool),('resourceIds',resource_ids),('resourceRequest',resource_request),('retention',retention),('handleGet',handle_get),('initHelpers',initial),
  ('checkpointOutput',output),('checkpointValues',values),('checkpointCallees',callees),('eventAtomic',event_atomic)):
  if stage is not None:stage(role,'deriving')
  owners[role]=owner.derive(image,pins)
  if stage is not None:stage(role,'derived')
 owners['resourceHandles']=owners['resourceIds']['proof']['resourceHandleSource']
 owners['stringScope']=owners['resourceRequest']['proof']['stringScopeSource']
 owners['radioRequest']=owners['radioSend']['proof']['dispatcherSource']['proof']['parentRadioRequest']
 owners['resourceLookup']=owners['resourceHandles']['proof']['resourceLookupSource']
 owners['resourceValidity']=owners['handleGet']['proof']['resourceValiditySource']
 owners['dataPath']=owners['encoding']['proof']['dataPathSource']
 owners['byteHash']=owners['dataPath']['proof']['byteHashSource']
 owners['pathHash']=owners['prefix']['proof']['hashSource']
 owners['lookup']=owners['resourceLookup']['proof']['resourceSource']['proof']['assetSource']['proof']['lookupSource']
 owners['checkpointHelpers']=owners['checkpointOutput']['proof']['helperSource']
 result=compose(base_source,pins,owners);_publication_gate(image,pins);return result
