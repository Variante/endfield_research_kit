"""Selected existing-record monitor acquisition and recursive release paths.

Actual atomic widths, same-thread predicates and untouched frame obligations are
explicit. No cold monitor allocation, contention/waiting or live ownership is
inferred from the path-hash caller's lock request.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
 if not condition:raise ValueError('patrolPathLock.'+check)


def acquire(regions,entry,*,recursive=True):
 need('literal-acquisition-mode',type(recursive)is bool)
 g=BytesPath(regions,entry)
 g.take('4053','56','57','4154','4155','4156','4157','4883ec60','448bfa','488bf1');thread=g.relative('ff15')
 g.take('448be0','4533f6','4c8b6c2448','498bde','f0480fc15e08','48899c24a0000000','4885db');g.branch('0f85',True)
 g.take('488b4308','90','493bc4');g.branch('75',not recursive,1)
 if recursive:g.take('ff4314')
 else:
  g.take('33c0','f04c0fb16308');g.branch('75',False,1)
  g.take('498bc6','f0480fc14608','483bc3');g.branch('74',True,1)
 g.take('b001','4883c460','415f','415e','415d','415c','5f','5e','5b','c3')
 return dict(selectedBytes=g.seen,currentThreadIatCell=thread,recursive=recursive,objectMonitorPointerOffset=8,
  monitorOwnerOffset=8,monitorOwnerBytes=8,monitorRecursionOffset=20,monitorRecursionBytes=4,
  atomicPointerRead='LOCK XADD QWORD object+8 with zero; returns unchanged prior pointer',
  selectedExistingMonitorNonnullRequired=True,
  selectedOwnerCondition='current thread ID zero-extended to64'if recursive else'zero owner; first CAS succeeds and same object monitor pointer remains stable',
  effect='recursion DWORD +=1 modulo2^32'if recursive else'owner QWORD := zero-extended current thread ID; prior initialized recursion remains1',
  positiveNonoverflowingRecursionRequired=recursive,full64MonitorPointerRecheck=not recursive,
  returnBool=True,normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,actualRuntimeOwnershipObserved=False)


def release_recursive(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec30','488bd9','4885c9');g.branch('0f84',False)
 g.take('48897c2440');at=g.at;query=g.relative('e8')
 g.take('488bf8','8b4814','ffc9','85c9');g.branch('7e',False,1)
 g.take('488b7c2440','894814','4883c430','5b','c3')
 return dict(selectedBytes=g.seen,queryMonitorCall=dict(instructionVa=at,targetVa=query),sameIncomingObjectPassedToQuery=True,
  selectedReturnedMonitorNonnullRequired=True,recursionBeforeRequiredAtLeast2=True,monitorRecursionOffset=20,
  effect='same monitor.recursion DWORD := previous value-1',normalReturn=True,entryRspRestored=True,
  allNonvolatilesRestored=True,actualRuntimeOwnershipObserved=False)


def query_monitor(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','33db','f0480fc15908','4885db');g.branch('74',False,1)
 thread=g.relative('ff15');g.take('8bc8','488b4308','90','483bc1');g.branch('74',True,1)
 g.take('488bc3','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,currentThreadIatCell=thread,objectMonitorPointerOffset=8,
  atomicPointerRead='LOCK XADD QWORD object+8 with zero; returns unchanged prior pointer',
  selectedSameThreadOwnerRequired=True,returnsSameObjectMonitorUnchanged=True,
  normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,actualRuntimeOwnershipObserved=False)


def release_last(regions,entry,*,failed_pushes=0):
 need('finite-stable-free-list-push',type(failed_pushes)is int and 0<=failed_pushes<=64)
 g=BytesPath(regions,entry);g.take('4053','4883ec30','488bd9','4885c9');g.branch('0f84',False)
 g.take('48897c2440');at=g.at;query=g.relative('e8')
 g.take('488bf8','8b4814','ffc9','85c9');g.branch('7e',True,1)
 g.take('8b4020','90','85c0');g.branch('74',True,1)
 g.take('33c0','48394730');g.branch('74',True,1)
 g.take('48874308','488b4f28','488b09');signal=g.relative('ff15')
 g.take('8b4720','90','85c0');g.branch('74',True,1)
 g.take('488b4c2428','488b5c2420','488bd1','488bc3','48c74708ffffffff')
 seed=g.relative('f0480fc70d')
 g.take('4889542428','4889442420','0f28442420','660f7f442420','488b542428','4c8b442420','0f1f8000000000')
 head=g.at
 for n in range(failed_pushes+1):
  need('same-free-list-loop-head',g.at==head)
  g.take('4c8907','488d4a01','488bdf','498bc0');need('same-paired-free-list',g.relative('f0480fc70d')==seed)
  g.take('4c8bc0','4889442420','0f94c0','4889542428','3c01');g.branch('75',n<failed_pushes,1)
 g.take('488b7c2440','4883c430','5b','c3')
 return dict(selectedBytes=g.seen,queryMonitorCall=dict(instructionVa=at,targetVa=query),signalIatCell=signal,
  sameIncomingObjectPassedToQuery=True,selectedReturnedMonitorNonnullRequired=True,recursionBeforeRequiredOne=True,
  waiterCountOffset=32,selectedWaiterCountRequiredZero=True,selectedAlternativeField48RequiredZero=True,
  objectMonitorPointerClearedToNull=True,monitorOwnerOffset=8,monitorOwnerStoredMinusOne=True,
  freeListCellVa=seed,freeListPairBytes=16,freeListHeadBytes=8,freeListSequenceBytes=8,
  initialSnapshotCmpxchg16bRequiredFail=True,failedPushes=failed_pushes,
  freeListEffect='monitor.next:=old head; paired LOCK CMPXCHG16B publishes same monitor head and old sequence+1 modulo2^64',
  signalNormalReturnRequired=True,normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,actualRuntimeOwnershipObserved=False)
