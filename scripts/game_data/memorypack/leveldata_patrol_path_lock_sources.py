"""Actual path-hash monitor's selected existing-record native state effects.

Warm recursive and unowned existing-record acquisitions, same-thread query,
recursive release and final no-waiter release are independent complete byte
programs. OS thread/event import identity, valid monitor storage, bounded CAS
success and incoming ownership remain explicit conditions, never live evidence.
"""
from scripts.game_data.memorypack import leveldata_patrol_path_lock_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-path-lock-sources.v1'


def need(check,condition):
 if not condition:raise ValueError('patrolPathLockSources.'+check)


def _programs(p):
 base=p['imageBase'];h=p['helpers'];raw={k:packets.raw(v,base)for k,v in h.items()}
 return packets.norm(dict(acquire=[programs.acquire(raw['acquire'],base+h['acquire']['entryRva'],recursive=r)for r in(False,True)],
  recursiveRelease=programs.release_recursive(raw['release'],base+h['release']['entryRva']),
  finalRelease=[programs.release_last(raw['release'],base+h['release']['entryRva'],failed_pushes=n)for n in range(4)],
  query=programs.query_monitor(raw['query'],base+h['query']['entryRva'])))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
 from scripts.game_data.memorypack import leveldata_patrol_path_sources as parent
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins);h={}
 for role,key in(('acquire','acquireCall'),('release','releaseCall')):
  h[role]=packets.packet(image,source['proof']['programs'][-1][key]['targetVa'])
 release=programs.release_recursive(packets.raw(h['release'],base),base+h['release']['entryRva'])
 h['query']=packets.packet(image,release['queryMonitorCall']['targetVa'])
 proof=dict(imageBase=base,pathSource=source,helpers=h);proof['programs']=_programs(proof)
 slots={proof['programs']['query']['currentThreadIatCell']-base,proof['programs']['finalRelease'][0]['signalIatCell']-base}
 proof['imports']=resolve_named_import_slots(image.pe,slots)
 result=packets.norm(dict(schema=SCHEMA,status='validated-conditional-existing-monitor-sources',nativeInputs=pins,proof=proof,
  selectedExistingMonitorAcquireAndReleaseEffectsProved=True,sameThreadMonitorQueryAndWholeFramesProved=True,
  coldMonitorAllocationOrContentionProved=False,liveMonitorOwnershipObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Actual named imports retain GetCurrentThreadId and ResetEvent identity/ABI and return normally; the on-disk import declarations do not observe live IAT targets or OS behavior.',
   'The selected nonnull lock object has a valid stable existing monitor pointer. Recursive mode is owned by the actual zero-extended current thread ID, with a positive nonoverflowing recursion count. Uncontended mode has zero owner and initialized recursion1; the owner CAS succeeds and the full64-bit object monitor pointer recheck remains equal.',
   'Final release uses the same current-thread monitor at recursion1, zero waiters and null alternative field48. The initial paired snapshot CAS fails without a write, then the actual free-list push succeeds after at most64 failed attempts under valid aligned stable storage. The monitor is retired, its owner set to minus one, and the exact pointer/sequence pair is published; no cold free-list history is inferred.',
   'The caller preserves the same lock object, and no unrelated aliases change ownership or fields between the joined acquire/query/release. Cold monitor creation, blocking/waiting, contention beyond the stated bound, failures and alternative release branches remain nonselected.']))
 validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
 from scripts.game_data.memorypack import leveldata_patrol_path_sources as parent
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-existing-monitor-sources'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedExistingMonitorAcquireAndReleaseEffectsProved','sameThreadMonitorQueryAndWholeFramesProved'))
  and all(value.get(k)is False for k in('coldMonitorAllocationOrContentionProved','liveMonitorOwnershipObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];source=p['pathSource'];need('same-input-path-parent',source['nativeInputs']==pins
  and source['schema']==parent.SCHEMA and source['status']=='validated-conditional-warm-nonhash-path-source')
 own=source['proof'];rr=packets.raw(dict(entryRva=own['programs'][0]['entry']-base,windows=own['sourceWindows'],
  regions=[[a-base,h]for a,h in own['sourceRegions']]),base)
 need('actual-parent-complete-path-replay',packets.norm([parent.program(rr,own['programs'][0]['entry']),
  parent.program(rr,own['programs'][0]['entry'],hash_prefix=True,lock_taken=False),
  parent.program(rr,own['programs'][0]['entry'],hash_prefix=True,lock_taken=True)])==own['programs'])
 need('own-exact-helper-roles',set(p['helpers'])=={'acquire','release','query'});actual=_programs(p)
 need('all-monitor-programs-replayed',actual==p['programs'])
 path=source['proof']['programs'][-1]
 for role,key in(('acquire','acquireCall'),('release','releaseCall')):
  need('actual-parent-lock-callee:'+role,path[key]['targetVa']==base+p['helpers'][role]['entryRva'])
 query=base+p['helpers']['query']['entryRva']
 need('actual-same-thread-monitor-query',actual['recursiveRelease']['queryMonitorCall']['targetVa']==query
  and all(v['queryMonitorCall']['targetVa']==query for v in actual['finalRelease']))
 need('same-current-thread-import',len({v['currentThreadIatCell']for v in actual['acquire']}|{actual['query']['currentThreadIatCell']})==1)
 expected={actual['query']['currentThreadIatCell']-base:'GetCurrentThreadId',actual['finalRelease'][0]['signalIatCell']-base:'ResetEvent'}
 imports=p['imports']['selectedImports'];need('actual-owned-OS-import-declarations',len(imports)==2 and {v['slotRva']:v['symbolName']for v in imports}==expected
  and all(v['libraryName'].lower()=='kernel32.dll'and v['onDiskUnboundIatEqualsLookupProved']is True
   and v['liveIatValueOrCalleeSelected']is False for v in imports))
 need('same-paired-free-list-cell',len({v['freeListCellVa']for v in actual['finalRelease']})==1
  and actual['finalRelease'][0]['freeListCellVa']%16==0)
 return value
