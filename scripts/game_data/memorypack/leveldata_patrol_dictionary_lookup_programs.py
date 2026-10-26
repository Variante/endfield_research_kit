"""Exact selected Int32/reference lookup programs used by Patrol Init.

These are conditional read-only dictionary paths, not a reconstructed runtime
table. The default comparer, callback, coherent contexts and valid stable
bucket/entry state must match the separately joined source witnesses.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def need(check,condition):
    if not condition:raise ValueError('patrolDictionaryLookup.'+check)


def equality_program(regions,entry):
    g=BytesPath(regions,entry);g.take('413bd0','0f94c0','c3')
    return dict(selectedBytes=g.seen,keyBits=32,equalsInputs='EDX and R8D',returnsTrueIffCompleteInt32BitsEqual=True,
        memoryWrites=0,calls=0,entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def preparation_program(regions,entry,*,inner,mode='initialized'):
    need('finite-ready-class-mode',mode in('initialized','being-initialized'))
    g=BytesPath(regions,entry);g.take('488b4978');need('actual-preparation-descriptor-tail',g.relative('e9')==inner);g.at=inner
    g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec30','488bd9','0fb6813a010000','90','a808')
    g.branch('0f85',mode=='initialized')
    if mode!='initialized':g.take('f6813901000020');g.branch('0f85',True)
    g.take('488b9c2480000000','4883c430','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,mode=mode,descriptorFieldOffset=120,
        selectedDescriptorFlagOffset=314 if mode=='initialized'else 313,selectedFlagMask=8 if mode=='initialized'else 32,
        nonframeMemoryWrites=0,opaqueCalls=0,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        condition='Valid stable class/descriptor pointer and the selected initialized/being-initialized flag already set. No cold method-table setup or actual runtime class selection is inferred.')


def find_program(regions,entry,*,comparer_getter,prepare,equality,failures=(),found=True,buckets_present=True):
    need('finite-witness-and-branches',isinstance(failures,(tuple,list))and len(failures)<=3 and all(k in('hash','key')for k in failures)
        and type(found)is bool and type(buckets_present)is bool and(buckets_present or(not failures and not found)))
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','4889742420','57','4154','4155','4156','4157','4883ec30',
        '4d8be0','448bf2','488b7910','bbffffffff','488b7118','4885ff');g.branch('0f84',not buckets_present)
    iterations=[]
    if buckets_present:
        g.take('488b6930','4885ed');g.branch('0f85',False)
        g.take('8bea','0fbaf51f','8bc5','99','f77f18','3b5718');g.branch('0f83',False)
        g.take('660f1f440000','4863da','33d2','89542460','8b5c9f20','ffcb','4885f6');g.branch('0f84',False);loop=g.at
        for index,reason in enumerate([*failures,None]):
            need('same-chain-loop-entry',g.at==loop);begin=len(g.seen)
            g.take('3b5e18');miss=reason is None and not found
            g.branch('73',miss,1)
            if miss:break
            g.take('4863c3','488d0c40','396cce20');g.branch('0f85',reason=='hash')
            if reason!='hash':
                g.take('498b442420','488b88c0000000','488b4910');g.call(comparer_getter)
                g.take('488bf8','3b5e18');g.branch('0f83',False)
                g.take('4863c3','488d0c40','448b7cce28','4885ff');g.branch('0f84',False)
                g.take('488b0f');g.call(prepare)
                g.take('488b07','4c8b90c0010000','4c8ba8c8010000')
                need('same-exact-selected-Int32-equality-callback',g.relative('488d05')==equality)
                g.take('4c3bd0');g.branch('75',False,1)
                g.take('453bfe','0f94c0','84c0');g.branch('0f84',reason=='key')
                if reason=='key':g.take('8b542460');g.jump('e9')
            if reason is not None:
                g.take('3b5e18');g.branch('73',False,1)
                g.take('4863c3','488d1c40','8b5cde24','3b5618');g.branch('0f8d',False)
                g.take('ffc2','89542460');g.jump('e9')
                iterations.append(dict(reason=reason,selectedBytes=g.seen[begin:],nextEntryOffset=4,counterHomeRsp=[96,100],counterIncrement=1))
    g.take('488b6c2470','8bc3','488b5c2468','488b742478','4883c430','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,failedProbes=list(failures),found=found,bucketsPresent=buckets_present,
        failedProbePrograms=iterations,bucketArrayField=16,entryArrayField=24,comparerField=48,
        keyBits=32,hashMask=2147483647,bucketCellBytes=4,bucketStoresIndexPlusOne=True,
        entryStride=24,entryHashOffset=0,entryNextOffset=4,entryKeyOffset=8,entryValueOffset=16,
        returnedIndex='matching nonnegative entry index'if found else-1,
        noDictionaryWrites=True,counterHomeRsp=[96,100],entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        condition='Default comparer field null; valid stable typed Int32/reference bucket and entry arrays, positive bucket length, valid nonnegative stored hash and entry geometry; selected equality callback matches actual raw Int32 equality. Each failed probe advances exact signed next-index and increments a disjoint preserved counter. Normal context/comparer/preparation ABI; sufficient acyclic finite chain and no concurrent mutation.')


def find_paths(regions,entry,*,comparer_getter,prepare,equality,count_limit=4096):
    import itertools
    need('bounded-chain-induction-domain',type(count_limit)is int and 3<=count_limit<=4096)
    paths=[find_program(regions,entry,comparer_getter=comparer_getter,prepare=prepare,equality=equality,
        failures=failures,found=found)for count in range(4)for failures in itertools.product(('hash','key'),repeat=count)for found in(False,True)]
    paths.append(find_program(regions,entry,comparer_getter=comparer_getter,prepare=prepare,equality=equality,found=False,buckets_present=False))
    arms={}
    for reason in('hash','key'):
        bodies=[step['selectedBytes']for p in paths for step in p['failedProbePrograms']if step['reason']==reason]
        need('same-exact-failed-probe-body-'+reason,bool(bodies)and all(b==bodies[0]for b in bodies))
        arms[reason]=bodies[0]
    certificate=dict(schema='endfield.patrol-int32-dictionary-chain-induction.v1',countLimit=count_limit,
        failedProbeArms=arms,allMixedWitnessesThroughThree=True,counterHomeRsp=[96,100],counterIncrement=1,
        nextIndexEntryOffset=4,keyBits=32,entryStride=24,noInt32CounterOverflow=count_limit<2**31-1,
        invariant='At the shared loop entry, EBX is the current signed chain index and EDX equals the number of prior failed probes, with the same counter saved at RSP+96. Either hash or key mismatch reads the exact next index from the same entry, checks the cycle bound against stable entry-array length, increments once, saves it and returns to this entry. The key arm restores the saved counter after helpers. Thus any mixed valid acyclic chain within the bound terminates at the first exact hash/key match or the negative end index, using the independently proved complete found/miss return.',
        conditions='Typed stable nonconcurrently mutated Int32/reference dictionary with valid bucket/entry hash-chain invariants, finite chain within countLimit and Int32 array length; exact current equality callback and coherent ready contexts. Helpers preserve the disjoint saved counter and nonvolatile dictionary/index state. Custom comparer, cycle/invalid storage, cold setup and larger chains remain separate.')
    return paths,certificate


def try_get_program(regions,entry,*,find,found):
    need('literal-TryGet-result',type(found)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b4120','498bf9','498bd8','8bf2','488be9',
        '4c8b90c0000000','498b82b0000000','4883782000');g.branch('75',True,1)
    g.take('488b4720','8bd6','488bcd','4c8b80c0000000','4d8b80b0000000');g.call(find)
    g.take('4863f0','85c0');g.branch('79',found,1)
    collector=None
    if found:
        g.take('488b7d18','4885ff');g.branch('74',False,1)
        g.take('3b7718');g.branch('73',False,1)
        collector=flag(g,'833d')
        g.take('488d0c76','488d04cf','488b44cf30','488903');g.branch('74',True,1)
        g.take('b001')
    else:
        g.take('33c0','488903');g.jump('eb',1)
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,found=found,findEntryMethodInfoSlot=22,sameDictionaryAndInt32KeyPassed=True,
        entryStride=24,entryValueOffset=16,outputBytes=8,output='unchanged selected entry reference'if found else'zero reference',
        returnedBool=found,collectorDisabledFlagVa=collector,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        runtimeLookupObserved=False)


def entity_table_program(regions,entry,*,try_get,found,replacement_present=False):
    need('literal-entity-table-mode',type(found)is bool and type(replacement_present)is bool)
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8b5070','4d85d2');g.branch('0f85',replacement_present)
    if replacement_present:
        g.take('498b82e00a0000','4885c0');g.branch('0f84',True)
    g.take('488b89b8000000','48c744244800000000','4885c9');g.branch('74',False,1)
    context_site=g.at;context=g.relative('4c8b0d');g.take('4c8d442448');g.call(try_get)
    g.take('84c0');g.branch('74',not found,1)
    if found:g.take('488b442448')
    else:g.take('33c0')
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,selectedReplacementAbsentRequired=True,
        dictionaryFieldOffset=184,contextInstructionVa=context_site,contextCellVa=context,
        sameIncomingInt32KeyPassed=True,referenceOutputLocalInitiallyZero=True,referenceOutputLocalFromRsp=[72,80],
        found=found,returnedReference='same TryGet output reference'if found else'zero reference',
        entryRspRestored=True,nonnullTypedDictionaryRequired=True)
