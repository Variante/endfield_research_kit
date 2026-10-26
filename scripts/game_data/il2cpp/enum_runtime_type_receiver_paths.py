"""Current TypeFromHandle receiver/cache and RuntimeType class-cell transfers.

The complete selected TypeFromHandle body is independently partitioned and
checked for its CFG and normal frames. Its null path returns null. Under the
explicit initialized System.Type/cache conditions, the selected occupied-hit
path returns the actual indexed cached object; the selected empty-cache path
passes the freshly loaded RuntimeType class cell to the actual allocator,
stores the requested class's byval carrier in the returned object's payload,
publishes that unchanged object through the actual cache slot and returns it.
The startup name/namespace/image request publishing that same class cell is
selected from its actual enclosing unwind-owned body, then joined to the
independently proved name lookup, record cache and class-constructor sources.

These are conditional native transfers. Startup execution, name-table/cache
population, allocator class-header semantics, class initialization and virtual
slot contents, sufficient disjoint cache storage, normal opaque mutex/insert/
collector effects and no intervening alias mutation remain requirements.
Neither a literal RuntimeType name nor an unchanged carrier establishes the
live nominal receiver, closed MethodInfo/RGCTX or formatter callback. No enum
wire grammar, enclosing parent or whole owner is admitted.
"""
import bisect
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-runtime-type-receiver-paths.v1'
LABEL='enumRuntimeTypeReceiverPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _prefix(g,*,null=False):
    g.take('48895c2410','55','56','57','4154','4155','4156','4157','4883ec60','488bd9','4885c9')
    g.branch('0f84',null)
    if null:return {}
    static_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('b201','488bcb');class_helper=g.relative('e8');g.take('4c8d7820');cache=g.relative('488b1d')
    g.take('488b8b80000000');lock=g.relative('ff15');g.take('90','488b4340','483b4338')
    return dict(systemTypeClassCell=static_class,classHelperTarget=class_helper,cacheCell=cache,
        lockIatCell=lock,requestedTypeRegister='r15',requestedType='actual class-helper return +32',
        classHelperRcx='unchanged incoming type handle',classHelperDl=1,
        initializedSystemTypeClassRequired=True,nonnullClassHelperReturnRequired=True)


def _return(g):
    g.take('488b9c24a8000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')


def handle_program(regions,entry,*,mode,symbols=None):
    """Complete literal null, first occupied hit or empty-cache fresh path."""
    need('literal-receiver-path',type(mode)is str and mode in('null','hit','empty-new'))
    if mode=='hit':
        from scripts.game_data.memorypack.formatter_provider_success_sources import type_from_handle
        need('explicit-independently-owned-cache-symbols',type(symbols)is dict
            and set(symbols)=={'classFromType','hash','compare'}
            and all(type(v)is int and v>0 for v in symbols.values()))
        source=type_from_handle(regions,entry,symbols);cache=source['cache']
        return dict(selectedBytes=source['selectedBytes'],mode=mode,
            systemTypeClassCell=source['typeClassCell'],cacheCell=cache['cacheGlobalCell'],
            actualIndependentlyProvedSymbols=symbols,selectedExistingCacheSource=source,
            cacheMustBeNonempty=True,deletedCountMustBeZero=True,firstOccupiedSlotMustMatch=True,
            sentinelMustDifferFromOccupiedTagZero=True,comparisonMustReturnZero=True,
            slotBytes=cache['entryStride'],slotTypeOffset=cache['entryKeyOffset'],
            slotIndexOffset=cache['entryValueIndexOffset'],valueArrayOffset=cache['valueTableOffset'],
            valueStride=8,returnedValue='unchanged cache value-array[matched slot index]',
            actualCachedObjectClassIdentityProved=False,normalReturn=True,entryRspRestored=True,
            allWin64NonvolatilesRestored=True,normalAbiPreservingCallsRequired=True,
            coherentDisjointCacheAndPayloadStorageRequired=True)
    g=BytesPath(regions,entry);facts=_prefix(g,null=mode=='null')
    if mode=='null':
        g.take('33c0');g.jump('e9');_return(g)
        return dict(selectedBytes=g.seen,mode=mode,nonnullHandleRequired=False,returnedRax=0,
            normalReturn=True,entryRspRestored=True,allWin64NonvolatilesRestored=True,opaqueCalls=0)
    g.branch('0f84',mode=='empty-new')
    if mode=='empty-new':
        # Both reads are actual empty-table end iterators. No first-probe,
        # callback, collision or race-winner semantics is silently substituted.
        g.take('488b4348','488d0c40','488b4368','488d14c8');g.jump('e9')
        g.take('488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('74',True,1)
        g.take('488b8b80000000');unlock=g.relative('ff15');g.take('90')
        class_cell=g.relative('488b0d');allocate=g.relative('e8');g.take('488be8','4c897810')
        need('same-cache-before-fresh-insertion',g.relative('4c8b35')==facts['cacheCell'])
        g.take('498d9e80000000','48899c24b0000000','488b0b');insertion_lock=g.relative('ff15')
        g.take('90','498b4640','493b4638');g.branch('0f84',True)
        g.take('498b4648','488d0c40','498b4668','488d14c8');g.jump('e9')
        g.take('498b4648','488d0c40','498b4668','488d0cc8','483bd1');g.branch('0f85',False)
        g.take('49837e7800');g.branch('0f84',False)
        g.take('498b4640','492b4638','493b4678');g.branch('0f84',False)
        g.take('498b7e40','492b7e38','c744242000000000','4c897c2428','48897c2430',
            '4c8d442420','488d542438','498bce');insert=g.relative('e8')
        g.take('498b4670','48892cf8','498b4e70','488d0cf9');collector=g.relative('e8')
        g.take('90','488b0b');insertion_unlock=g.relative('ff15');g.take('90');g.jump('e9')
        g.take('488bc5');_return(g)
        path=dict(unlockIatCell=unlock,runtimeTypeClassCell=class_cell,allocationTarget=allocate,
            allocationRcx='fresh unchanged RuntimeType class-cell value',allocatedReferenceRegister='rbp',
            payloadOffset=16,payloadValue='unchanged requested type carrier in r15',
            insertionLockIatCell=insertion_lock,insertionUnlockIatCell=insertion_unlock,
            insertTarget=insert,collectorTarget=collector,keyTag=0,keyTypeOffset=8,keyIndexOffset=16,
            valueArrayOffset=112,valueStride=8,returnedValue='unchanged actual allocation return',
            bothSelectedCacheReadsEmptyRequired=True,deletedCountMustBeZero=True,
            cacheCapacityMustExceedSizeMinusDeleted=True,nonnullAllocationRequired=True,
            actualAllocatorObjectHeaderSemanticsProved=False,cacheInsertEffectsProved=False,
            interveningRaceAndAliasEffectsProved=False)
    return dict(selectedBytes=g.seen,mode=mode,**facts,**path,normalReturn=True,entryRspRestored=True,
        allWin64NonvolatilesRestored=True,normalAbiPreservingCallsRequired=True,
        coherentDisjointCacheAndPayloadStorageRequired=True)


def constructor_self_program(regions,entry):
    """Exact post-allocation self field, not a constructed-class identity."""
    g=BytesPath(regions,entry);allocator=g.relative('e8');image_count=g.relative('448b0d')
    g.take('33ed','488bd8','448bc5','48894078')
    return dict(selectedBytes=g.seen,allocationTarget=allocator,imageCountCell=image_count,
        classSelfOffset=120,source='unchanged actual allocation return rax',
        sameAllocatedReferenceStored=True,opaqueCallsBetweenAllocationAndSelfStore=0,
        initializedClassOrVirtualSlotsProved=False)


def _owned_at(image,site):
    """Select a primary solely by exact declared unwind interval membership."""
    base=image.pe.image_base;entries=image.unwind_index.entries;starts=sorted(entries)
    index=bisect.bisect_right(starts,site-base)-1
    need('source-in-declared-unwind-interval',index>=0 and entries[starts[index]][0]<=site-base<entries[starts[index]][1])
    from scripts.game_data.memorypack.pointer_param import owned
    return owned(image,base+image.unwind_index.resolve(starts[index]))


def bind_publication(publication,cold,independent_publication):
    need('same-exact-allocator-class-cell',publication['resultCell']==cold['runtimeTypeClassCell'])
    need('same-independently-proved-name-lookup-and-core-image',
        publication['classLookup']==independent_publication['classLookup']
        and publication['assemblyCell']==independent_publication['assemblyCell'])


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_name_lookup_paths import derive as name_source,find_program
    from scripts.game_data.il2cpp.enum_provider_open_list_mapping import derive as mapping_source
    from scripts.game_data.il2cpp.enum_normalizer_selection_paths import publication_program
    from scripts.game_data.il2cpp.enum_plain_method_descriptor_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.levelscript_two_routes_native import _window
    _publication_gate(image,pins);prior=name_source(image,pins,**arguments);mapping=mapping_source(image,pins)
    target=mapping['proof']['selectedMappingSlice']['typeFromHandleTarget'];body=owned(image,target)
    rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));graph,padding=complete_program(body['regions'],rows,target)
    cold=handle_program(body['regions'],target,mode='empty-new')
    independent=prior['proof']['internerSource']['proof']['selectedHit']
    symbols=dict(classFromType=cold['classHelperTarget'],hash=independent['hashTarget'],compare=independent['compareTarget'])
    programs={mode:handle_program(body['regions'],target,mode=mode,symbols=symbols)for mode in('null','hit')}
    programs['empty-new']=cold
    cold=programs['empty-new'];selected=prior['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']
    startup=_owned_at(image,selected['proof']['placeholderPublication']['selectedBytes'][0][0]);startup_rows=[]
    for at,raw in startup['regions']:startup_rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL+'.startup')
    candidates=[]
    for row in startup_rows:
        if bytes.fromhex(row['bytes'])[:3]!=bytes.fromhex('4c8d05'):continue
        site=int(row['va'],16)
        # A candidate must have the exact complete request/store grammar and
        # publish the independently selected allocator's class cell.
        try:source=publication_program(startup['regions'],site)
        except ValueError:continue
        if source['resultCell']==cold['runtimeTypeClassCell']:candidates.append(source)
    need('one-actual-RuntimeType-class-cell-publisher',len(candidates)==1);publication,=candidates
    need('actual-RuntimeType-System-request',image.pe.bytes_at_va(publication['nameAddress'],12)==b'RuntimeType\0'
        and image.pe.bytes_at_va(publication['namespaceAddress'],7)==b'System\0')
    bind_publication(publication,cold,selected['proof']['placeholderPublication'])
    finder=owned(image,prior['proof']['selectedWarmLookup']['findTarget'])
    runtime_find=find_program(finder['regions'],finder['pointer'],name=b'RuntimeType')
    ctx=NativeReferenceContext(image);td=ctx.index.types['System.RuntimeType']
    need('actual-reference-RuntimeType-definition',not ctx.is_value_type('System.RuntimeType') and not td.flags&0x20)
    fields=selected['proof']['classFieldSource'];ctor=owned(image,fields['proof']['actualColdClassConstructor']['target'])
    need('same-independent-actual-class-helper',cold['classHelperTarget']==fields['proof']['constructor']['elements'][1]['helperTarget'])
    prefix=fields['proof']['constructor']['prefix'];self_source=constructor_self_program(ctor['regions'],prefix['allocatorSite'])
    need('same-independent-class-allocation-source',self_source['allocationTarget']==prefix['allocatorTarget'])
    publication_window=_window(image,publication['selectedBytes'][0][0],publication['end'],
        'Exact RuntimeType/System/core-image request and unchanged class-cell publication; startup execution/return unproved')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(nameAndInternerSource=prior,openListMapSource=mapping,typeFromHandleWindows=body['windows'],
            typeFromHandleCfg=graph,typeFromHandlePadding=padding,typeFromHandlePaths=programs,
            startupOwnedWindows=startup['windows'],startupInstructionPartitionChecked=True,
            startupCompleteControlAndReturnProved=False,runtimeTypePublication=publication,
            runtimeTypePublicationWindow=publication_window,runtimeTypeFoundSlot=runtime_find,
            runtimeTypeDefinition=td.index,classConstructorSelf=self_source,classConstructorWindows=ctor['windows']),
        exactRequestedCarrierAndSelectedReceiverTransfersProved=True,initializedRuntimeTypeReceiverClassIdentityProved=False,
        actualVirtualSlotOrClosedContextProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current TypeFromHandle partition/CFG/frames and selected null/hit/empty-new paths; actual startup publisher, independently selected RuntimeType name comparison and constructor self store.',
            conditional=__doc__,structuralOnly='Requested type carrier, reflection-object payload, class cell and cache-slot source transfers.',
            unresolved=['startup execution/name table/cache and allocator class-header identity','class initialization/virtual slots and actual MethodInfo/RGCTX',
                'opaque cache insert/collector/mutex effects and alias/race coherence','actual nominal enum formatter callback','wire/parent/EOF']))))
