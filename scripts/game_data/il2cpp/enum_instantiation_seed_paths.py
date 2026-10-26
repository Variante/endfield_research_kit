"""Selected static-instantiation seed loop and exact count1 insert/duplicate.

The current metadata phase visits the selected registration's pointer-array
slots in increasing index order and supplies each slot's address to its actual
insertion helper. Complete source partitions/CFGs/normal frames are checked.
The source-owned count1 insert path publishes the unchanged registered pointer;
the exact equal-key duplicate path leaves that slot unchanged and returns
false. Both independently use the same argument hash/comparator as lookup.
The complete static table is examined for every content-equivalent placeholder
argument, rather than assuming a unique key from a name or pointer address.

The selected insertion paths require initialized markers, adequate capacity,
no tombstones, a selected first empty/equal slot, compatible normal mutex calls
and disjoint stable storage. Reservation, resize, collision-loop completion,
full initialized-map contents, method-table population and actual provider or
MethodInfo callback remain separate obligations. No enum wire grammar follows.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-instantiation-seed-paths.v1'
LABEL='enumInstantiationSeedPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def seed_loop_program(regions,entry):
    g=BytesPath(regions,entry);g.take('8bfb');registration=g.relative('488b05')
    g.take('395810');g.branch('7e',False,1);g.take('0f1f840000000000');iteration=g.at
    g.take('4863cf','488b4018','488d14c8');site=g.at;insert=g.relative('e8')
    g.take('ffc7');need('same-registration-reload',g.relative('488b05')==registration)
    g.take('3b7810');back=g.relative('7c',1);need('same-increasing-seed-backedge',back==iteration)
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,registrationCell=registration,
        genericInstantiationCountOffset=16,genericInstantiationPointersOffset=24,pointerStride=8,
        initialEbxMustBeZero=True,counterRegister='edi',initialCounter=0,step=1,
        signedCountPositiveRequired=True,tableStableAndCountBelow2Pow31Required=True,
        insertionCallSite=site,insertionTarget=insert,insertionRdx='address of actual registration pointer-array slot[index]',
        callbackReceivesSlotAddressNotInlineInstantiation=True,iterationOrder='increasing registration index',
        wholeMetadataPhaseReturnProved=False)


def insertion_program(regions,entry,*,duplicate=False):
    need('literal-insertion-path',type(duplicate)is bool);g=BytesPath(regions,entry)
    g.take('48894c2408','53','55','56','57','4154','4155','4156','4157','4881eca8000000','488bda')
    mutex=g.relative('488d05');g.take('4889442428');need('same-lock-cell',g.relative('488b0d')==mutex)
    lock=g.relative('ff15');g.take('90','4c8b33','4c89b42400010000')
    marker=g.relative('803d')+1;g.take('00');g.branch('0f85',False)
    occupied=g.relative('488b35');g.take('4889b42408010000','4883fefe');g.branch('0f83',False)
    capacity=g.relative('4c8b1d');g.take('4983fb04');g.branch('0f82',False)
    g.take('488d4601');threshold=g.relative('483b05');g.branch('0f87',False)
    g.take('33ff','4d8d63ff','4c89642420','418b1e','458b06','4d85c0');g.branch('74',False,1)
    g.take('4d8b4e08');hash_loop=g.at;g.take('498b09');hashing=g.relative('e8')
    g.take('4869dbdba2fa1c','4803d8','4d8d4908','4983e801');back=g.relative('75',1)
    need('same-counted-hash-backedge',back==hash_loop)
    g.take('49c7c7ffffffff','4c89bc24f0000000','418b16','48899424f8000000')
    slots=g.relative('488b35');deleted=g.relative('4c8b2d');g.take('4923dc','488bc3','4803c0')
    sentinel=g.relative('488b0d');g.take('3b0cc6');g.branch('75',duplicate,1)
    compared=None
    if duplicate:
        g.take('4d85ed');g.branch('0f85',False)
        g.take('488bc3','4803c0','833cc600');g.branch('75',False,1)
        g.take('488b4cc608','3b11');g.branch('75',False,1)
        g.take('33ed','4885d2');g.branch('74',False,1)
        g.take('4d8b7608','4c8b7908','4d2bfe');comparison_loop=g.at
        g.take('4b8b1437','498b0e');site=g.at;target=g.relative('e8')
        g.take('85c0');g.branch('74',True,1)
        g.take('48ffc5','4983c608','483bac24f8000000');back=g.relative('72',1)
        need('same-counted-comparison-backedge',back==comparison_loop)
        g.take('49c7c7ffffffff','493bdf');g.branch('0f85',True)
        g.take('32db');g.jump('e9')
        compared=dict(site=site,target=target,rcx='registered incoming instantiation argument[0]',
            rdx='existing candidate argument[0]',returnedZeroRequired=True)
    else:
        g.take('85c9');g.branch('0f85',True)
        g.take('4983ffff');g.branch('75',False,1)
        g.take('4c8bfb');g.jump('eb',1)
        g.take('488b9c2408010000','488bc3','492bc5','48b9ffffffffffffff0f','483bc1');g.branch('0f83',False)
        g.take('4d85ed');g.branch('0f85',False)
        g.take('48ffc3');need('same-occupied-count-publication',g.relative('48891d')==occupied)
        g.take('4d03ff','42c704fe00000000','488b842400010000','4a8944fe08','b301')
    need('same-unlock-cell',g.relative('488b0d')==mutex);unlock=g.relative('ff15')
    g.take('90','0fb6c3','4881c4a8000000','415f','415e','415d','415c','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,inputCount=1,duplicate=duplicate,mutexCell=mutex,lockIatCell=lock,unlockIatCell=unlock,
        initializedMarkerCell=marker,markerByteMustBeZero=True,occupiedCountCell=occupied,capacityCell=capacity,
        capacityAtLeastFourRequired=True,capacityThresholdCell=threshold,capacityThresholdSufficientRequired=True,
        slotsCell=slots,deletedCountCell=deleted,deletedCountMustBeZero=True,sentinelCell=sentinel,
        sentinelNonzeroRequired=not duplicate,actualHashTarget=hashing,actualComparison=compared,
        slotBytes=16,slotTagOffset=0,slotPointerOffset=8,
        unchangedIncomingRegisteredPointerPublished=not duplicate,existingEqualSlotNotReplaced=duplicate,
        returnedLowByte=0 if duplicate else 1,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        reservationResizeCollisionAndTablePopulationProved=False)


def complete_program(regions,rows,entry,*,recursive_calls=None,memory_effect_decoder=None):
    from scripts.game_data.il2cpp.owned_partition import check_byte_partition,checked_rows
    from scripts.game_data.il2cpp.type_data_initialization_control import _complete,_flow
    pieces=[(int(row['va'],16),int(row['va'],16)+len(bytes.fromhex(row['bytes'])),'instruction')for row in rows]
    check_byte_partition([(at,at+len(raw))for at,raw in regions],pieces,LABEL)
    for at,raw in regions:
        checked_rows([row for row in rows if at<=int(row['va'],16)<at+len(raw)],raw,LABEL)
    incoming=set()
    for row in rows:
        flow=_flow(row,{},{});kind=flow['kind'];at=int(row['va'],16)
        if kind in('next','call','opaqueCall','indirectCall','registerCall','conditional'):incoming.add(at+len(bytes.fromhex(row['bytes'])))
        if kind in('conditional','jump'):incoming.add(flow['target'])
    # Keep every decoded byte. Only an unreferenced final CC of an actual
    # owned range is classified as padding, never a gap or a reachable trap.
    padding=[row for row in rows if bytes.fromhex(row['bytes'])==b'\xcc'and int(row['va'],16)not in incoming
        and int(row['va'],16)!=entry and any(int(row['va'],16)==at+len(raw)-1 for at,raw in regions)]
    code=[row for row in rows if row not in padding];graph=_complete(code,entry,recursive_calls=recursive_calls,
        memory_effect_decoder=memory_effect_decoder)
    graph['edges']={at:sorted(v)for at,v in graph['edges'].items()}
    return graph,padding


def _complete_family(image,target):
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.enum_initialization_instructions import decode_enum_initialization_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    body=owned(image,target);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode_enum_initialization_instructions(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));graph,padding=complete_program(body['regions'],rows,target)
    return body,rows,graph,padding


def derive(image,pins,*,selection_entry,primitive_entry,**key_arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_method_pointer_selection import derive as selection_source
    from scripts.game_data.il2cpp.class_creation_control import _dominators
    from scripts.game_data.il2cpp.class_enum_fields_control import _no_register_write
    _publication_gate(image,pins);base=image.pe.image_base
    prior=selection_source(image,pins,selection_entry=selection_entry,primitive_entry=primitive_entry,**key_arguments)
    publication=prior['proof']['registrationAliasPublication'];start=publication['end']
    g=BytesPath([(start,image.pe.bytes_at_va(start,19))],start);g.relative('488d05');g.relative('488905');phase=g.relative('e8')
    body,rows,graph,padding=_complete_family(image,phase)
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    site=unique(body['regions'],bytes.fromhex('8bfb488b05'));loop=seed_loop_program(body['regions'],site)
    need('same-selected-metadata-registration-alias',loop['registrationCell']==publication['metadataRegistrationAliasCell'])
    prefix=BytesPath(body['regions'],phase)
    prefix.take('48895c2418','4889742420','55','57','4156','488d6c24b9','4881ec90000000');zero=prefix.at;prefix.take('33db')
    by={int(row['va'],16):i for i,row in enumerate(rows)}
    _no_register_write(rows,by[zero]+1,by[site],'rbx',calls_allowed=True)
    dom=_dominators({int(at):set(v)for at,v in graph['edges'].items()},phase)
    success=unique(body['regions'],bytes.fromhex('b0014c8d9c2490000000'))
    need('registration-seed-loop-dominates-successful-phase-return',site in dom[success]and zero in dom[site])
    inserted,insert_rows,insert_graph,insert_padding=_complete_family(image,loop['insertionTarget'])
    programs=[insertion_program(inserted['regions'],inserted['pointer'],duplicate=duplicate)for duplicate in(False,True)]
    primitive=prior['proof']['primitiveNormalizerSource'];interner=primitive['proof']['nameAndInternerSource']['proof']['internerSource']
    selected=interner['proof']['selectedHit'];keys=interner['proof']['placeholderTypeSource']['proof']['argumentKeySource']
    need('same-independently-owned-argument-hash-comparator-and-table',all(p['actualHashTarget']==selected['hashTarget']
        and p['slotsCell']==selected['slotsCell']and p['mutexCell']==selected['entryPrefix']['mutexCell']for p in programs)
        and programs[1]['actualComparison']['target']==selected['compareTarget'])
    placeholder=interner['proof']['placeholderTypeSource']['proof']['placeholder'];wanted=placeholder['typeDefinition']
    count=image.registration['genericInstsCount'];need('bounded-complete-static-instantiations',type(count)is int and 0<count<=1_000_000)
    need('actual-selected-registration-pointer-array-layout',int.from_bytes(image.pe.bytes_at_va(image.metadata_registration+16,4),'little')==count
        and image.pe.u64_at_va(image.metadata_registration+24)==int(image.registration['genericInsts'],16))
    equivalents=[]
    for index in range(count):
        inst=image.instantiations.resolve(index)
        if len(inst.arguments)!=1:continue
        argument,=inst.arguments;raw=bytes.fromhex(argument.raw_type_record_hex)
        if raw[10]!=17 or (int.from_bytes(raw[8:12],'little')>>29)&1 or int.from_bytes(raw[:8],'little')!=wanted:continue
        equivalents.append(inst.as_dict())
        need('bounded-equivalent-placeholder-keys',len(equivalents)<=64)
    need('actual-equivalent-placeholder-registration-present',bool(equivalents))
    expected=interner['proof']['placeholderTypeSource']['proof']['registeredPlaceholderEntries']
    need('selected-placeholder-is-first-equivalent-static-instantiation',all(
        item['registration']['classInstantiation']['record_va']==equivalents[0]['record_va']for item in expected))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(methodSelectionSource=prior,metadataPhaseWindows=body['windows'],metadataPhaseCfg=graph,
            metadataPhasePadding=padding,selectedSeedLoop=loop,zeroCounterOrigin=zero,successfulPhaseReturnFlag=success,
            insertionWindows=inserted['windows'],insertionCfg=insert_graph,insertionPadding=insert_padding,
            insertionPaths=programs,allEquivalentStaticPlaceholderInstantiations=equivalents,
            completeStaticInstantiationCount=count),
        actualRegistrationPointerArraySeedLoopProved=True,firstEquivalentStaticPlaceholderMatchesSelectedRegistration=True,
        initializedArgumentTablePopulationProved=False,initializedMethodKeyTableIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete current metadata-phase/insertion instruction partitions and CFGs/normal frames with only unreferenced range-final CC classified as padding; selected increasing registration seed loop, exact count1 insert/duplicate programs, independent hash/comparison joins and complete static equivalent-key inventory.',
            conditional=__doc__,structuralOnly='Static generic-instantiation registration and runtime argument table.',
            unresolved=['reservation/resize/collision induction and full initialized argument-table state',
                'method-key table population and actual nominal provider/MethodInfo callback binding','startup execution/opaque cache aliases','wire/parent/EOF']))))
