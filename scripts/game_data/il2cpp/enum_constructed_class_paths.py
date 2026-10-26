"""Constructed-class key representation and actual reflection-result paths.

The selected class-creation family has its entire code/data partition,
three locally based guarded RVA tables, control graph and normal frames
checked. Its selected cached path preserves the incoming generic key and
returns a fresh read of that key's cached-class field after releasing one
recursion level. The independent fresh-allocation prefix stores the unchanged
incoming key in the new class's generic link. The selected byval/byref stores
write kind21 and that same key; publication exchanges the allocation with the
key cache, then reloads the cache. Register origins/dominance are checked over
the complete graph. Publication does not return the pre-exchange allocation
register by assumption.

The separate actual reflection-object helper has its complete owned source,
CFG and normal frames checked. Its first occupied hit returns the indexed
existing object. Its selected empty/no-race path passes the freshly loaded
RuntimeType class to the same proved allocator, stores the unchanged incoming
carrier at payload16, publishes that object and returns it unchanged.

These are source/representation claims with initialized coherent class/key
and cache state, recursive mutex, disjoint sufficient allocation/storage,
matching successful hash/comparison and ordinary noninterfering helpers as
conditions. The actual open-class lookup/recursive creation effects, live
cache history/race winner, reflection object payload/class identity and closed
MethodInfo/RGCTX/callback selection remain unresolved. Managed key/type/class
sizes are never wire widths. No concrete enum/list/parent/whole grammar follows.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-constructed-class-paths.v1'
LABEL='enumConstructedClassPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _json_set(value):
    if type(value)is not set:raise TypeError(LABEL+'.unreviewed-report-value:'+type(value).__name__)
    return sorted(value)


def key_receiver_program(regions,entry):
    g=BytesPath(regions,entry);g.take('488b09');target=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,actualCarrierResolver=target,
        outgoingRcx='unchanged actual incoming generic-key first QWORD',entryFrameUnchanged=True,
        fullUnwindExtentProved=False)


def carrier_receiver_program(regions,entry,*,null):
    need('literal-current-carrier-receiver-path',type(null)is bool)
    g=BytesPath(regions,entry);g.take('4885c9');g.branch('74',null,1)
    if null:
        g.take('33c0');g.jump('eb',1);g.take('c3');target=None
    else:g.take('488b09');target=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,null=null,actualRecordClassProjection=target,
        outgoingRcx=None if null else'unchanged actual incoming carrier first data QWORD',
        returnedRax=0 if null else'actual record-class projection return',entryFrameUnchanged=True,
        fullUnwindExtentProved=False)


def _creation_prefix(g):
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec20','0fb6da')
    origin=g.at;g.take('4c8bf1');receiver=g.relative('e8');g.take('488bf0','4885c0');g.branch('75',True,1)
    mutex=g.relative('4c8d25');g.take('4c89642470');thread=g.relative('ff15');g.take('488bd8')
    owner=g.relative('488b0d');g.take('41bfffffffff','483bc1');g.branch('74',True,1)
    depth=g.relative('8b05');g.take('ffc0');need('same-recursive-depth-write',g.relative('8905')==depth)
    g.take('4533ed','4d396e18')
    return dict(incomingKeyOrigin=origin,actualOpenClassReceiver=receiver,mutex=mutex,threadIatCell=thread,
        ownerCell=owner,depthCell=depth,recursiveOwnerAndPositiveBoundedDepthRequired=True)


def cached_class_program(regions,entry):
    g=BytesPath(regions,entry);facts=_creation_prefix(g);g.branch('0f85',True)
    reload=g.at;g.take('498b5e18','85c0');g.branch('7e',False,1)
    g.take('83f801');g.branch('75',True,1);g.take('ffc8')
    need('same-recursive-release-depth-cell',g.relative('8905')==facts['depthCell'])
    g.take('488bc3','488b5c2460','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,**facts,cacheOffset=24,freshCacheReload=reload,
        returnValue='unchanged fresh incoming generic-key cachedClass read',cachedClassMustBeNonnull=True,
        oneRecursionLevelReleased=True,entryRspRestored=True,allNonvolatilesRestored=True,
        initializedCachedClassIdentityProved=False)


def allocation_prefix(regions,entry):
    g=BytesPath(regions,entry);facts=_creation_prefix(g);g.branch('0f85',False)
    g.take('440fb7862c010000','4983c014','49c1e004','ba01000000')
    context=g.relative('488b0d');call=g.at;allocate=g.relative('e8');origin=g.at
    g.take('488bd8','48894078','488b4e10','48894810','488b4e18','48894818','488b0e','488908',
        '8b8e14010000','898814010000');link=g.at;g.take('4c897060')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,**facts,allocationCall=call,allocationTarget=allocate,
        allocationContextCell=context,allocationCount=1,allocationBytes='(actual open-class vtableCount word +20) <<4',
        sourceVtableCountOffset=300,allocationOrigin=origin,allocationRegister='rbx',classSelfOffset=120,
        unchangedSourceCopies=[dict(offset=16,bytes=8),dict(offset=24,bytes=8),dict(offset=0,bytes=8),dict(offset=276,bytes=4)],
        genericLinkStore=link,genericLinkOffset=96,unchangedIncomingKeyStored=True,
        nonnullSufficientDisjointZeroedAllocationRequired=True,completeNewClassSemanticsProved=False)


def type_carrier_program(regions,entry):
    g=BytesPath(regions,entry);g.take('c6432a15','c6433a15','4c897320','4c897330','814b3800000020',
        '8b4d28','334b28','0fbaf11f','334d28','894b28')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,classRegister='rbx',keyRegister='r14',
        byvalOffset=32,byrefOffset=48,kindByteOffsets=[42,58],storedKind=21,
        dataQwordValue='unchanged actual incoming generic key',byrefDwordBit=29,
        byvalDwordBit31='actual selected source flags bit31; all other current byval bits preserved',
        managedCarrierBytes=16,wireWidthInferred=False)


def publication_program(regions,entry):
    g=BytesPath(regions,entry);g.take('49875e18');depth=g.relative('8b05');mutex=g.relative('4c8d25')
    reload=g.at;g.take('498b5e18')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,cacheOffset=24,incomingKeyRegister='r14',
        exchangeRegister='rbx',exchangeWritesPreviousAllocationAndOverwritesRegisterWithPreviousCache=True,
        followingDepthCell=depth,mutexAddress=mutex,freshCacheReload=reload,
        freshCacheReadNotPreviousExchangeRegister=True,cacheReloadEqualsThisAllocationProved=False)


def _object_prefix(g):
    g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec60','4c8bf1')
    cache=g.relative('488b1d');g.take('488b8b80000000');lock=g.relative('ff15')
    g.take('90','488b4340','483b4338');return cache,lock


def _object_return(g):
    g.take('488b9c24b0000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')


def reflection_object_program(regions,entry,*,empty):
    need('literal-current-object-cache-path',type(empty)is bool)
    g=BytesPath(regions,entry);cache,lock=_object_prefix(g);g.branch('0f84',empty)
    if not empty:
        g.take('4533e4','488b6b48','48ffcd','498bce');hashing=g.relative('e8')
        g.take('488bf8','488b7368','448b7b50','4823fd','488d0c7f','443b3cce');g.branch('75',True,1)
        g.take('48837b3800');g.branch('0f87',False)
        g.take('488d047f','833cc600');g.branch('75',False,1)
        g.take('488b54c608','498bce');compare=g.relative('e8');g.take('85c0');g.branch('75',False,1)
        g.take('4883ffff');g.branch('74',False,1)
        g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('74',False,1)
        g.take('488b4a10','488b4370','488b3cc8','488b8b80000000');unlock=g.relative('ff15')
        g.take('90','488bc7');_object_return(g)
        extra=dict(hashTarget=hashing,compareTarget=compare,unlockIatCell=unlock,
            returnedValue='unchanged indexed existing cached object',firstOccupiedMatchAndZeroDeletedRequired=True,
            comparisonZeroAndValidValueIndexRequired=True,actualCachedPayloadIdentityProved=False)
    else:
        g.take('488b4348','488d0c40','488b4368','488d14c8');g.jump('e9')
        g.take('488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('74',True,1)
        g.take('488b8b80000000');unlock=g.relative('ff15');g.take('90')
        class_cell=g.relative('488b0d');allocate=g.relative('e8');g.take('4c8bf8','4c897010')
        need('same-cache-before-insert',g.relative('488b2d')==cache)
        g.take('488d9d80000000','48899c24a8000000','488b0b');insert_lock=g.relative('ff15')
        g.take('90','488b4540','483b4538');g.branch('0f84',True)
        g.take('488b4548','488d0c40','488b4568','488d14c8');g.jump('e9')
        g.take('488b4548','488d0c40','488b4568','488d0cc8','483bd1');g.branch('0f85',False)
        g.take('48837d7800');g.branch('0f84',False)
        g.take('488b4540','482b4538','483b4578');g.branch('0f84',False)
        g.take('488b7d40','482b7d38','c744242000000000','4c89742428','48897c2430',
            '4c8d442420','488d542438','488bcd');insert=g.relative('e8')
        g.take('488b4d70','4c893cf9','488b4d70','488d0cf9');barrier=g.relative('e8')
        g.take('90','488b0b');insert_unlock=g.relative('ff15');g.take('90','498bc7');g.jump('e9');_object_return(g)
        extra=dict(unlockIatCell=unlock,runtimeTypeClassCell=class_cell,actualAllocator=allocate,
            allocationClassArgument='unchanged freshly loaded RuntimeType class-cell value',payloadOffset=16,
            payloadValue='unchanged incoming generic carrier RCX',returnedValue='unchanged actual allocation result',
            insertLockIatCell=insert_lock,insertUnlockIatCell=insert_unlock,actualInsertTarget=insert,
            actualReferenceBarrier=barrier,bothSelectedCachesEmptyAndNoInterveningRaceRequired=True,
            sufficientValueCapacityAndNonnullDisjointAllocationRequired=True,insertAndAliasEffectsProved=False)
    return dict(selectedBytes=g.seen,entry=entry,empty=empty,cacheCell=cache,lockIatCell=lock,
        cacheEntryBytes=24,keyOffset=8,valueIndexOffset=16,valueTableOffset=112,valueStride=8,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,**extra)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_managed_generic_arguments import derive as argument_source
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.enum_plain_method_descriptor_paths import preserve_until
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.consumer_rva_switches import partition_consumer_rva_switches,ordinary_entry_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.consumer_control import check_consumer_control
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=argument_source(image,pins,**arguments);base=image.pe.image_base
    key=prior['proof']['nativeGenericKeySource'];key_path=key['proof']['count1Programs'][1]
    creation=owned(image,key_path['actualClassCreationTarget']);need('one-owned-class-code-data-interval',len(creation['regions'])==1)
    at,data=creation['regions'][0]
    part=partition_consumer_rva_switches(image.mapper,data,entry=at,image_base=base,
        old_base_registers=('r15',),local_base_registers=('rdx',),destination_registers=('rcx',))
    need('three-explicit-local-image-base-guards',len(part['tables'])==3 and all(t['baseRegister']=='rdx'and t['baseLoad']is not None for t in part['tables']))
    ordinary=ordinary_entry_program(part,entry=at);need('all-class-code-is-ordinary-reachable',not ordinary['nonEntryCode'])
    cached=cached_class_program(creation['regions'],at);allocation=allocation_prefix(creation['regions'],at)
    receiver_entry=cached['actualOpenClassReceiver'];receiver_raw=image.pe.bytes_at_va(receiver_entry,8)
    receiver=key_receiver_program([(receiver_entry,receiver_raw)],receiver_entry)
    carrier_entry=receiver['actualCarrierResolver'];carrier_raw=image.pe.bytes_at_va(carrier_entry,18)
    receivers=[carrier_receiver_program([(carrier_entry,carrier_raw)],carrier_entry,null=n)for n in(False,True)]
    normalizer=key['proof']['receiverSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']
    fixup=normalizer['proof']['classFieldSource']['proof']['typeDataFixup']
    projection_entry=fixup['proof']['projection']['selectedBytes'][0][0]
    need('same-independent-actual-record-class-projection',receivers[0]['actualRecordClassProjection']==projection_entry)
    carrier_rows=checked_rows(decode(image.mapper,carrier_raw,carrier_entry),carrier_raw,LABEL+'.observed-carrier')
    receiver_graph=check_consumer_control(carrier_rows,entry=carrier_entry,owned_ranges=[(carrier_entry,carrier_entry+18)],
        tail_exits={carrier_entry+8:dict(target=projection_entry)})
    carrier=type_carrier_program(creation['regions'],unique(creation['regions'],bytes.fromhex('c6432a15c6433a15')))
    publication=publication_program(creation['regions'],unique(creation['regions'],bytes.fromhex('49875e18')))
    need('same-class-cache-and-recursive-state',publication['cacheOffset']==cached['cacheOffset']
        and publication['followingDepthCell']==cached['depthCell']and publication['mutexAddress']==cached['mutex'])
    need('same-actual-fresh-cache-reload',publication['freshCacheReload']==cached['freshCacheReload'])
    graph=ordinary['control'];rows=ordinary['rows'];origin=allocation['incomingKeyOrigin']
    preservation=[preserve_until(graph,rows,at,origin,publication['entry'],('r14',)),
        preserve_until(graph,rows,at,allocation['allocationOrigin'],carrier['entry'],('rbx',)),
        preserve_until(graph,rows,at,allocation['allocationOrigin'],publication['entry'],('rbx',))]
    reflection=owned(image,key_path['actualReflectionObjectTarget']);object_rows=[]
    for start,raw in reflection['regions']:object_rows+=checked_rows(decode(image.mapper,raw,start),raw,LABEL)
    object_rows.sort(key=lambda r:int(r['va'],16));object_graph,padding=complete_program(reflection['regions'],object_rows,reflection['pointer'])
    objects=[reflection_object_program(reflection['regions'],reflection['pointer'],empty=e)for e in(False,True)]
    type_receiver=key['proof']['receiverSource'];cold=type_receiver['proof']['typeFromHandlePaths']['empty-new']
    hit=type_receiver['proof']['typeFromHandlePaths']['hit']['actualIndependentlyProvedSymbols']
    need('same-independent-reflection-cache-and-RuntimeType-allocation',objects[0]['cacheCell']==objects[1]['cacheCell']==cold['cacheCell']
        and objects[0]['hashTarget']==hit['hash']and objects[0]['compareTarget']==hit['compare']
        and objects[1]['runtimeTypeClassCell']==cold['runtimeTypeClassCell']and objects[1]['actualAllocator']==cold['allocationTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(managedArgumentSource=prior,classWindows=creation['windows'],classCodeData=part,classOrdinaryProgram=ordinary,
            genericKeyReceiver=receiver,carrierReceiverPaths=receivers,carrierReceiverCfg=receiver_graph,
            genericKeyReceiverWindow=_window(image,receiver_entry,receiver_entry+8,'Exact observed key data load/E9; no unwind extent claim'),
            carrierReceiverWindow=_window(image,carrier_entry,carrier_entry+18,'Exact observed null-or-data-load/record-projection tail and return programs; no unwind extent claim'),
            selectedClassCachePath=cached,selectedClassAllocationPrefix=allocation,selectedTypeCarrierStores=carrier,
            selectedClassPublication=publication,classRegisterPreservation=preservation,reflectionWindows=reflection['windows'],
            reflectionCfg=object_graph,reflectionPadding=padding,selectedReflectionPaths=objects),
        incomingGenericKeyClassLinkAndKind21StoresProved=True,conditionalReflectionPayloadAndResultTransfersProved=True,
        actualConstructedClassOrCacheHistoryIdentityProved=False,actualClosedMethodInfoAndRgctxProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete current class3-table code/data and reflection helper source/CFG/frames, selected key/allocation/carrier/publication/cache paths and independently bound reflection cache/class/allocator symbols.',
            conditional=__doc__,structuralOnly='Actual generic-class/key/type carrier and reflection object payload representations.',
            unresolved=['actual open-class lookup and complete new-class/recursive effects','live class/cache/alias/race outcomes',
                'closed MethodInfo/RGCTX and concrete enum callback','wire/list/parent/EOF'])),default=_json_set))
