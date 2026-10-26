"""Own System.Type registry programs; string semantics are never imported.

Two complete byte grammars are physically the same reference-key programs as
the string lane. Only their checked instruction spans and storage geometry are
reused below. The System.Type declarations, callbacks and equality are separate.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_programs as shared


def need(check,condition):
    if not condition:raise ValueError('patrolTypeDictionary.'+check)


def find_program(regions,entry,*,hash_invoke,comparer_getter,equality_invoke,failures=(),found=True,buckets_present=True):
    p=shared.find_string_program(regions,entry,hash_invoke=hash_invoke,comparer_getter=comparer_getter,
        equality_invoke=equality_invoke,failures=failures,found=found,buckets_present=buckets_present)
    return dict(selectedBytes=p['selectedBytes'],failedProbePrograms=p['failedProbePrograms'],
        failedProbes=p['failedProbes'],found=found,bucketsPresent=buckets_present,
        comparerRequiredNull=True,bucketFieldOffset=16,entryArrayFieldOffset=24,comparerFieldOffset=48,
        entryStride=24,entryHashOffset=0,entryNextOffset=4,entryKeyOffset=8,entryValueOffset=16,
        referenceKeyBytes=8,hashMask=2147483647,hashSelector=2,equalitySelector=8,
        sameInputReferenceKeyPassed=True,selectedHashAndEqualityEffectsRequired=True,
        noDictionaryWrites=True,entryRspRestored=p['entryRspRestored'],
        restoredNonvolatiles=p['restoredNonvolatiles'],nominalKeyGrammarImported=False,
        pointerEquivalenceClaimed=False)


def find_paths(regions,entry,*,hash_invoke,comparer_getter,equality_invoke,count_limit=4096):
    import itertools
    need('finite-own-Type-chain',type(count_limit)is int and 3<=count_limit<=4096)
    args=dict(hash_invoke=hash_invoke,comparer_getter=comparer_getter,equality_invoke=equality_invoke)
    paths=[find_program(regions,entry,**args,failures=f,found=found)
        for n in range(4)for f in itertools.product(('hash','key'),repeat=n)for found in(False,True)]
    paths.append(find_program(regions,entry,**args,found=False,buckets_present=False))
    arms={}
    for reason in('hash','key'):
        values=[a['selectedBytes']for p in paths for a in p['failedProbePrograms']if a['reason']==reason]
        need('same-failed-Type-chain-arm-'+reason,values and all(v==values[0]for v in values));arms[reason]=values[0]
    return dict(witnesses=paths,countLimit=count_limit,failedProbeArms=arms,
        induction=dict(counterInitial=0,counterIncrement=1,counterRegister='r12d',entryStride=24,nextIndexOffset=4,
            exactHashAndPointerEqualityEffectsRequired=True,stableValidAcyclicChainRequired=True,
            invariant='Every failed hash/key arm loads the same entry next index, compares the preserved counter with the stable entry-array length, increments once and returns to the exact shared loop. The first matching hash and reference-equality result returns its unchanged entry index; exhaustion returns minus one.'),
        runtimeTableSelectionObserved=False)


def try_get_program(regions,entry,*,find,found):
    p=shared.try_get_program(regions,entry,find=find,found=found)
    return dict(selectedBytes=p['selectedBytes'],found=found,findEntryContextSlot=22,
        sameDictionaryAndReferenceKeyPassed=True,entryStride=24,entryValueOffset=16,
        outputBytes=8,output=p['output'],returnedBool=found,
        collectorDisabledFlagVa=p['collectorDisabledFlagVa'],entryRspRestored=True,
        restoredNonvolatiles=p['restoredNonvolatiles'],findEntryEffectsRequired=True,
        nominalKeyGrammarImported=False)


def self_type_program(regions,entry):
    g=BytesPath(regions,entry);g.take('488bc1','c3')
    return dict(selectedBytes=g.seen,returnsSameIncomingTypeReference=True,calls=0,memoryWrites=0,
        entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def runtime_type_equals_program(regions,entry):
    g=BytesPath(regions,entry);g.take('483bd1','0f94c0','c3')
    return dict(selectedBytes=g.seen,result='incoming RCX and RDX references equal',
        calls=0,memoryWrites=0,entryRspAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False)


def runtime_type_hash_program(regions,entry,*,prepare,self_getter):
    g=BytesPath(regions,entry)
    g.take('48895c2410','48894c2408','55','56','57','4154','4155','4156','4157','488d6c24d9','4881eca0000000',
        '488bd9','488b09');g.call(prepare)
    g.take('488b03','4c8b80c0030000','488b90c8030000');excluded=[]
    for _ in range(2):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch('0f85',True)
    excluded.append(g.relative('488d05'));g.take('488bcb','4c3bc0');g.branch('75',True,1)
    need('actual-RuntimeType-self-getter',self_getter not in excluded)
    g.take('41ffd0','4c8bf8');type_class=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4d85ff');g.branch('74',False,1)
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4c3bfb');g.branch('74',True,1)
    g.take('8b4310','488b9c24e8000000','4881c4a0000000','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selectedUnderlyingSystemTypeCallbackRequired=self_getter,
        underlyingSystemTypeSelector=40,excludedUnderlyingCallbacks=excluded,
        ownSelfGetterEffectsRequired=True,TypeClassCellVa=type_class,TypeClassReadyRequired=True,
        returnsReceiverFieldLow32Offset=16,stableReceiverTypeHandleRequired=True,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def runtime_type_hash_invoker_program(regions,entry,*,prepare,callback,self_getter):
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec50','4c8bf2','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','498b06','4c8b04c8','488b54c808')
    need('selected-RuntimeType-hash-inline-callback',g.relative('488d05')==callback)
    g.take('4c3bc0');g.branch('0f85',False)
    g.take('498b0e');g.call(prepare)
    g.take('498b06','4c8b80c0030000','488b90c8030000');excluded=[]
    for _ in range(2):
        excluded.append(g.relative('488d05'));g.take('4c3bc0');g.branch('0f85',True)
    excluded.append(g.relative('488d05'));g.take('498bce','4c3bc0');g.branch('75',True,1)
    need('same-RuntimeType-self-getter-outside-alternatives',self_getter not in excluded)
    g.take('41ffd0','488bd8');type_class=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4885db');g.branch('74',False,1)
    g.take('83b9e000000000');g.branch('75',True,1)
    g.take('493bde');g.branch('74',True,1)
    g.take('418b4610');g.jump('e9')
    g.take('488b9c2490000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selector=2,selectedRuntimeTypeHashCallbackRequired=callback,
        selectedUnderlyingSystemTypeCallbackRequired=self_getter,ownSelfGetterEffectsRequired=True,
        TypeClassCellVa=type_class,returnsIncomingReceiverFieldLow32Offset=16,
        stableReceiverTypeHandleRequired=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def erased_reference_equals_program(regions,entry,*,invoke):
    g=BytesPath(regions,entry);g.take('4885d2');g.branch('74',False,1)
    g.take('4d85c0');g.branch('74',False,1)
    g.take('33c9');need('own-reference-comparer-tail',g.relative('e9')==invoke)
    return dict(selectedBytes=g.seen,selector=0,bothKeyReferencesRequiredNonNull=True,
        sameKeyReferencesPassed=True,entryRspAndNonvolatilesUntouched=True,
        canonicalClosedComparerPointerEquivalenceProved=False)


def comparer_equals_invoker_program(regions,entry,*,prepare,callback,invoke):
    p=shared.comparer_equals_invoker_program(regions,entry,prepare=prepare,callback=callback,invoke=invoke)
    return dict(selectedBytes=p['selectedBytes'],selector=8,selectedErasedBodyRequired=callback,
        bothKeyReferencesRequiredNonNull=True,nestedSelector=0,sameBothKeyReferencesPassed=True,
        returnedBoolBitsUnchanged=True,entryRspRestored=True,
        restoredNonvolatiles=p['restoredNonvolatiles'],canonicalClosedComparerPointerEquivalenceProved=False,
        actualSelectedClosedSystemTypeComparerBodyCompatibilityRequired=True)


def runtime_type_equals_invoker_program(regions,entry,*,prepare,callback):
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec40','498bf0','488bfa','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','4803c9','488b07','4c8b0cc8','4c8b44c808');excluded=[]
    excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('75',True,1)
    excluded.append(g.relative('488d05'));g.take('4c3bc8');g.branch('74',False,1)
    need('selected-RuntimeType-Equals-inline-callback',g.relative('488d05')==callback and callback not in excluded)
    g.take('4c3bc8');g.branch('0f85',False)
    g.take('483bf7','0f94c0');g.jump('eb',1)
    g.take('488b9c2480000000','4883c440','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selector=0,selectedRuntimeTypeEqualsCallbackRequired=callback,
        result='same incoming first and second reference equal',excludedCallbacks=excluded,
        entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])
