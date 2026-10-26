"""Selected native ValueType field hashing and ordinary value boxing effects.

Runtime class/cache/thread/storage and callback selections remain explicit
conditions. These parsers authenticate actual instruction paths, not live state.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check, condition):
    if not condition:
        raise ValueError('patrolValueHash.' + check)


def internal(regions, entry, *, field_kinds=(17,), boxed_count=None):
    need('finite-field-kinds', type(field_kinds) is tuple and 1 <= len(field_kinds) <= 64
         and all(type(k) is int and k in (8, 17) for k in field_kinds))
    count = sum(k == 17 for k in field_kinds)
    need('positive-boxed-fields', count > 0 and (boxed_count is None or type(boxed_count) is int and boxed_count == count))
    g = BytesPath(regions, entry); calls = []; sites = {}; boxes = []
    def call(role):
        at = g.at; target = g.relative('e8'); calls.append(dict(role=role, instructionVa=at, targetVa=target)); return target
    g.take('4889542410','55','53','56','57','4154','4155','4156','4157','4883ec38','488d6c2420',
           '488b39','4533f6','4c8bef','44897560','49c1ed03','33f6','4c8be1','4c896d70','6639b726010000')
    g.branch('0f84', False); g.take('4533ff','4533d2','4c895578','48baf0ffffffffffff0f'); loop = g.at
    boxed = 0
    for index, kind in enumerate(field_kinds):
        g.take('4d85ff'); g.branch('75', index != 0, 1)
        if index == 0:
            g.take('488bcf'); call('prepareFields'); g.take('664439bf26010000'); g.branch('0f84',False)
            g.take('4c8bbf80000000','48baf0ffffffffffff0f','498bdf'); g.at = g.relative('eb',1)
        else:
            g.take('0fb78726010000','498d4f20','48c1e005','4c8bf9','48038780000000','483bc8')
            g.branch('0f83',False);g.take('488bd9')
        g.take('4885db');g.branch('0f84',False);g.take('488b4308','f6400810');g.branch('75',False,1)
        g.take('0fbe480a','83f909');g.branch('7c',kind < 9,1)
        if kind >= 9:
            g.take('83f90e');g.branch('7c',False,1)
        g.take('83e908');g.branch('0f84',kind == 8)
        if kind == 8:
            g.take('48634318','46332c20');back=g.relative('e9');need('same-field-loop',back==loop);g.at=back
            continue
        g.take('83e906');g.branch('0f84',False);g.take('83f901');g.branch('74',False,1)
        g.take('4885f6');g.branch('75',boxed != 0,1)
        if boxed == 0:
            g.take('0fb78726010000','48c1e003','488d480f','483bc8');g.branch('77',True,1)
            g.take('4883e1f0','488bc1');call('stackProbe');g.take('482be1','488d742420')
        sites['threadIndexPointerCellVa']=g.relative('488b0d');g.take('8b09')
        at=g.at;sites['threadGetterIatCellVa']=g.relative('ff15');sites['threadGetterInstructionVa']=at
        g.take('4c8bf0','4885c0');g.branch('75',True,1);g.take('4d8bc6','498bd4','488bcb')
        call('boxField');boxes.append(dict(fieldIndex=index,fieldKind=kind,outputArrayIndex=boxed))
        g.take('488b4d78','448b7560','41ffc6','44897560','488904ce','48ffc1','48894d78')
        back=g.relative('e9');g.at=back;g.take('48baf0ffffffffffff0f');need('same-field-loop',g.at==loop);boxed+=1
    g.take('4d85ff');g.branch('75',True,1)
    g.take('0fb78726010000','498d4f20','48c1e005','4c8bf9','48038780000000','483bc8');g.branch('0f83',True)
    g.take('4c896d70','4885f6');g.branch('0f84',False)
    sites['objectClassCellVa']=g.relative('488b0d')
    g.take('bb01000000','4d63fe','8bd3','4533c0','4c897d00');call('arrayClass')
    g.take('488bc8','4c8bf0');call('prepareArray')
    g.take('4981ffffffff7f');g.branch('0f87',False)
    g.take('418bbe00010000');sites['allocationTableBaseVa']=g.relative('4c8d25')
    g.take('490fafff','4883c720','41f6863801000020');g.branch('75',True,1)
    g.take('498b4640','83782800');g.branch('0f8d',True)
    g.take('49837e0800','488bcf');g.branch('74',False,1)
    g.take('498bd6');call('allocateReferences');g.at=g.relative('eb',1)
    g.take('488bd8')
    sites['profilerFlagsCellVa']=g.relative('f605')+1;g.take('80','4c897b18');g.branch('74',True,1)
    collector=g.relative('833d')+1;g.take('00','488b4568','488918');g.branch('74',True,1)
    g.take('4c8b5578','4d85d2');g.branch('0f8e',False)
    g.take('4c8b6d68','41b920000000','4c2bce','6666660f1f840000000000');copy=g.at
    for index in range(count):
        g.take('4d8b4500','488b06','4d03c1','4c03c6');need('same-copy-collector',g.relative('833d')+1==collector)
        g.take('00','498900');g.branch('74',True,1);g.take('4883c608','4983ea01')
        g.branch('75',index+1<count,1)
        if index+1<count:need('same-array-copy-loop',g.at==copy)
    g.take('4c8b6d70');g.at=g.relative('eb',1)
    g.take('418bc5','488d6518','415f','415e','415d','415c','5f','5e','5b','5d','c3')
    return dict(selectedBytes=g.seen,calls=calls,sites=sites,fieldKinds=list(field_kinds),fieldInfoStride=32,
        fieldTypeOffset=8,fieldValueOffsetOffset=24,typeKindOffset=10,staticAttributeMask=16,boxedFields=boxes,
        objectCount=count,hashSeed='low32(actual box class pointer >>3)',int32FieldEffect='XOR same stored Int32 bits',
        scratchBytes=((len(field_kinds)*8+15)//16)*16,arrayBytes=32+8*count,arrayLengthOffset=24,arrayDataOffset=32,
        selectedArrayElementClass='System.Object',selectedArrayClassGcDescriptorRequiredNonnull=True,
        effect='publish cached Object[] with each actual boxed field in metadata order; return native seed XOR Int32 fields',
        selectedThreadStateRequiredNonnull=True,selectedArrayClassElementBytes=8,selectedSpareReferenceBlockRequired=True,
        selectedUnusedArrayStorageRequiredZero=True,collectorRequiredDisabled=True,entryRspRestored=True,allNonvolatilesRestored=True)


def box_field(regions,entry,*,payload_bytes=4):
    need('finite-ordinary-payload',type(payload_bytes)is int and payload_bytes in(1,4,20))
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('4055','57','4156','4883ec30','488d6c2430','48895d28','488bfa','488bd9','48897530','488b4908','b201','498bf0');call('classFromType')
    g.take('4c8b4b08','4c8bf0','41f6410840');g.branch('0f84',True)
    g.take('41f6410810','48635318');g.branch('74',True,1)
    g.take('488d3417','498bce');call('prepareClass');g.take('41837e2800');g.branch('7c',True,1)
    g.take('49837e6000');g.branch('74',True,1)
    g.take('49639ef8000000','498bce');call('newObject')
    g.take('488bf8','4883c3f0','488bd6','488d4f10','4c8bc3');call('copyPayload')
    collector=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('488b5d28','488bc7','488b7530','488be5','415e','5f','5d','c3')
    return dict(selectedBytes=g.seen,calls=calls,payloadBytes=payload_bytes,fieldInfoOffset=24,boxedValueOffset=16,
        selectedInstanceBytes=16+payload_bytes,collectorCellVa=collector,
        effect='copy exactly class.instanceSize-16 field bytes from actual source box+FieldInfo.offset to fresh box+16',
        fieldRequiredInstanceNonThreadStatic=True,fieldClassRequiredNonNullableValue=True,
        entryRspRestored=True,allNonvolatilesRestored=True)


def ready_fields(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','f6813901000001');g.branch('75',True,1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,classFlagOffset=313,readyMask=1,returnsUnchangedClass=True,nonFrameWrites=0,calls=[])


def ready_class(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bd9','f6813801000002');g.branch('0f85',True)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,classFlagOffset=312,readyMask=2,nonFrameWrites=0,calls=[],entryRspRestored=True)


def stack_probe(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec10','4c891424','4c895c2408','4d33db','4c8d542418','4c2bd0',
        '4d0f42d3','654c8b1c2510000000','4d3bd3');g.branch('73',True,1)
    g.take('4c8b1424','4c8b5c2408','4883c410','c3')
    return dict(selectedBytes=g.seen,selectedRequestWithinCommittedStack=True,raxAndRcxUnchanged=True,
        nonFrameWrites=0,allNonvolatilesRestored=True,entryRspRestored=True)


def new_object(regions,entry,*,payload_bytes=4):
    need('finite-ordinary-payload',type(payload_bytes)is int and payload_bytes in(1,4,20))
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('4053','57','4883ec58','488bf9');call('prepareClass')
    g.take('48837f6000');g.branch('74',True,1)
    g.take('f6873801000020');g.branch('0f85',False)
    g.take('8b8ff8000000');call('allocatePlain')
    g.take('33c9','488bd8','488938','4c8d4810','48894808','81bff800000080000000','448b87f8000000');g.branch('73',False,1)
    g.take('4903c0','4c8bc0','4d2bc1','4983c007','49c1e803','4c3bc8','4c0f47c1','4d85c0');g.branch('74',False,1)
    g.take('49c1e003','33d2','498bc9');call('zero')
    counter=g.relative('f048ff05');g.at=g.relative('e9')
    g.take('f6873901000002');g.branch('74',True,1)
    profiler=g.relative('f605')+1;g.take('80');g.branch('74',True,1)
    g.take('488bcf');call('classInit');g.take('488bc3','4883c458','5f','5b','c3')
    return dict(selectedBytes=g.seen,calls=calls,payloadBytes=payload_bytes,instanceBytes=16+payload_bytes,
        actualZeroBytes=((payload_bytes+7)//8)*8,allocationCounterCellVa=counter,profilerFlagsCellVa=profiler,
        selectedClassRequiredNonNullableAndReferenceFree=True,selectedClassRequiredNoFinalizer=True,
        effect='allocate spare block, set same class and zero monitor, zero rounded payload, return same box',
        entryRspRestored=True,allNonvolatilesRestored=True)


def allocate_plain(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','56','57','4154','4155','4883ec20','4533ed');base=g.relative('4c8d25')
    mode=g.relative('833d')+1;g.take('01','418bfd','b803000000','488bf1','0f44f8','4881f900080000');g.branch('0f87',False)
    lock=g.relative('44392d');g.branch('74',True,1)
    g.take('498b8cf4');sizes=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('8bc7','48c1e005','4a8b8420');pool=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('488b1cc8','4c8d04c8','4885db');g.branch('74',False,1)
    g.take('85ff');g.branch('74',True,1)
    g.take('488b13','498910','48c1e104');counter=g.relative('48010d')
    need('same-unlocked-state',g.relative('44392d')==lock);g.branch('0f84',True)
    g.take('488bc3','4883c420','415d','415c','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,imageBase=base,modeCellVa=mode,lockCellVa=lock,accountingCellVa=counter,
        sizeClassIndexTableVa=sizes,poolTableVa=pool,selectedMode=0,
        maximumRequestBytes=2048,effect='pop nonnull same-size-class plain block; account sizeClassIndex*16; return same block',
        selectedSpareBlockRequired=True,actualSizeClassAndPoolStateObserved=False,entryRspRestored=True,allNonvolatilesRestored=True)


def allocate_references(regions,entry):
    g=BytesPath(regions,entry);g.take('4055','56','57','4154','4157','4883ec20')
    mode=g.relative('833d')+1;g.take('01','4c8bfa','488bf1');g.branch('75',True,1)
    free=g.relative('488b3d');flags=g.relative('8b2d');g.take('48895c2458');base=g.relative('4c8d25')
    g.take('4881fe00080000');g.branch('0f87',False)
    lock=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('498b8cf4');sizes=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('488b1ccf','4885db');g.branch('0f85',True)
    g.take('488b03','488904cf','48c1e104');counter=g.relative('48010d')
    need('same-unlocked-reference-allocation',g.relative('833d')+1==lock);g.take('00','4c893b');g.branch('74',True,1)
    collector=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('488bc3');allocation=g.relative('f048ff05')
    g.take('488b5c2458','4883c420','415f','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,imageBase=base,modeCellVa=mode,freeListCellVa=free,flagsCellVa=flags,
        lockCellVa=lock,collectorCellVa=collector,accountingCellVa=counter,allocationCounterCellVa=allocation,
        sizeClassIndexTableVa=sizes,maximumRequestBytes=2048,
        effect='pop nonnull reference block of selected size class; install same incoming class; account and return same block',
        selectedSpareBlockRequired=True,unusedMonitorBoundsAndPayloadRequiredZero=True,actualStateObserved=False,
        entryRspRestored=True,allNonvolatilesRestored=True)


def class_from_type(regions,entry,*,jump_target=None):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','0fbe410a');base=g.relative('4c8d05')
    g.take('488bd9','83f80f');g.branch('7c',False,1);g.take('83f816');g.branch('7d',False,1)
    g.take('0fbe430a','83f812');g.branch('75',True,1);g.take('83e80f','83f80f');g.branch('0f87',False)
    g.take('4898','418b8c80');table=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4903c8','ffe1');g.at=table+8;selected=base+int.from_bytes(g.read(4),'little')
    need('actual-kind17-table-selection',jump_target is None or jump_target==selected);jump_target=selected;g.at=jump_target
    g.take('488bcb','4883c420','5b');target=g.relative('e9')
    return dict(selectedBytes=g.seen,imageBase=base,selectedTypeKind=17,jumpTableCellVa=table+8,
        selectedJumpTargetVa=jump_target,ordinaryClassTargetVa=target,returnsActualResolvedClass=True,entryRspRestored=True)


def ordinary_class(regions,entry):
    g=BytesPath(regions,entry);g.take('4885c9');g.branch('74',False,1);g.take('488b09');at=g.at;target=g.relative('e9')
    return dict(selectedBytes=g.seen,classDefinitionCall=dict(instructionVa=at,targetVa=target),
        effect='tail resolve original ordinary type.data',typeRequiredNonnull=True)


def boxed_id_hash(regions,entry,*,asset=True):
    need('literal-id-profile',type(asset)is bool);g=BytesPath(regions,entry)
    if asset:
        g.take('4053','4883ec20');root=g.relative('488b05');g.take('488d5910','488b4878','4885c9');g.branch('0f85',False)
        ready=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
        g.take('8b03','4883c420','5b','c3')
    else:g.take('8b4110','c3');root=ready=None
    return dict(selectedBytes=g.seen,boxedPayloadOffset=16,output='unchanged stored Int32 bits',replacementRootCellVa=root,
        initializedClassCellVa=ready,entryRspRestored=True,normalReturn=True,liveCallbackSelectionObserved=False)


def enum_byte_hash(regions,entry):
    g=BytesPath(regions,entry);g.take('488b01','488b4040');cells=[]
    # Actual Enum body compares its element-class identity with each primitive
    # class. The Byte identity is the second comparison and precedes wider loads.
    cells.append(g.relative('483b05'));g.branch('74',False,1)
    byte=g.relative('483b05');g.branch('74',True,1);g.take('0fb64110','c3')
    return dict(selectedBytes=g.seen,otherPrimitiveClassCells=cells,byteClassCellVa=byte,boxedPayloadOffset=16,
        effect='zero extend same boxed Byte value to Int32',selectedUnderlyingClassRequiredByte=True,
        liveEnumClassOrCallbackSelectionObserved=False,entryRspRestored=True)


def initialized_class(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2418','4889742420','55','57','4154','4156','4157','488bec','4883ec70',
        '0f29742460','488bf1','4533f6','44897530','4439b1e0000000');g.branch('0f85',True)
    g.take('4c8d5c2470','498b5b40','498b7348','0f28742460','498be3','415f','415e','415c','5f','5d','c3')
    return dict(selectedBytes=g.seen,initializedFlagOffset=224,selectedFlagRequiredNonnull=True,
        calls=[],nonFrameWrites=0,allNonvolatilesIncludingXmm6Restored=True,entryRspRestored=True)


def array_class(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157',
        '4883ec60','8bea','4c8bf1','33db','8bf3','410fb6c0','83fa01','0f46f0','440fb6c6')
    at=g.at;target=g.relative('e8');g.take('4885c0');g.branch('0f85',True)
    g.take('4c8d5c2460','498b5b30','498b6b38','498b7340','498be3','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,lookupCall=dict(instructionVa=at,targetVa=target),rank=1,bounds=False,
        selectedCacheHitRequired=True,returnsSameCachedClass=True,allNonvolatilesRestored=True,entryRspRestored=True)


def array_lookup(regions,entry):
    g=BytesPath(regions,entry);g.take('4c8bdc','49895b10','49894b08','55','56','57','4154','4155','4156','4157',
        '4883ec50','448bea','488bd9','83fa01');g.branch('0f87',False);g.take('4584c0');g.branch('0f85',False)
    g.take('33ed','896c2420','49894ba0');lock=g.relative('488d05');g.take('49894320')
    need('same-cache-mutex',g.relative('488b0d')==lock);lock_call=g.relative('ff15');g.take('90','4c8d442420','488d542430')
    cache=g.relative('488d0d');at=g.at;find=g.relative('e8');capacity=g.relative('488b05')
    g.take('488d0c40');slots=g.relative('488b05');g.take('488d14c8','488b5c2438','483bda');g.branch('74',False,1)
    g.take('488b5b10');need('same-unlock-cache-mutex',g.relative('488b0d')==lock);unlock=g.relative('ff15')
    g.take('90','488bc3');g.at=g.relative('e9')
    g.take('488b9c2498000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,findCall=dict(instructionVa=at,targetVa=find),lockCellVa=lock,
        lockIatCellVa=lock_call,unlockIatCellVa=unlock,cacheVa=cache,capacityCellVa=capacity,slotsCellVa=slots,
        cacheEntryStride=24,elementClassKey='same incoming System.Object class',keyHashMarker=0,
        effect='return actual matching cache entry value at16 after balanced selected OS mutex acquire/release',
        dynamicExternalMutexEffectsRequired=True,allNonvolatilesRestored=True,entryRspRestored=True)


def type_hash(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','480fbe410a','8b5908','4869d0dba2fa1c','0fb6410a',
        '48c1eb1d','83e301','4803da','3c12');g.branch('75',True,1)
    g.take('3c11');g.branch('74',False,1);g.take('3c15');g.branch('74',False,1)
    g.take('3c1d');g.branch('74',False,1);g.take('3c0f');g.branch('74',False,1)
    g.take('488bc3','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,typeKind=28,byrefBit=29,multiplier=486187739,
        effect='(kind*multiplier + byrefBit) modulo2^64 for primitive System.Object type',entryRspRestored=True)


def type_equals(regions,entry,*,jump_target=None):
    g=BytesPath(regions,entry);g.take('4883ec28','4c8bda','48895c2430');base=g.relative('488d15')
    g.take('4c8bd1','66660f1f840000000000','410fb6430a','4138420a');g.branch('0f85',False)
    g.take('418b4308','418b4a08','c1e81d','c1e91d','83e001','83e101','3bc8');g.branch('0f85',False)
    g.take('410fbe420a','83c0f1','83f80f');g.branch('0f87',False)
    g.take('4898','8b8c82');table=base+int.from_bytes(g.read(4),'little',signed=True);g.take('4803ca','ffe1')
    g.at=table+52;selected=base+int.from_bytes(g.read(4),'little')
    need('actual-kind28-table-selection',jump_target is None or jump_target==selected);jump_target=selected;g.at=jump_target
    g.take('33c0','488b5c2430','4883c428','c3')
    return dict(selectedBytes=g.seen,typeKind=28,jumpTableCellVa=table+52,selectedJumpTargetVa=jump_target,
        effect='return zero for same primitive System.Object kind28 and same byrefBit',entryRspRestored=True)


def array_find(regions,entry):
    g=BytesPath(regions,entry);calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('4053','55','56','4883ec40','488b4140','498be8','488bf2','488bd9','483b4138');g.branch('0f84',False)
    g.take('48897c2468','4533c0','4c89642438','4c896c2430','4c89742428','4c897c2420','4c8b7948','488b4d08',
        '49ffcf','4883c120','4c89442460');call('typeHash')
    g.take('4c8b7368','488bf8','448b6350','4c8b6d08','48c7442478ffffffff','4923ff','488d047f','453b24c6');g.branch('75',True,1)
    g.take('48837b3800');g.branch('0f87',False)
    g.take('488d047f','498d14c6','418b04c6','394500');g.branch('75',False,1)
    g.take('837d0000');g.branch('75',False,1)
    g.take('488b5208','498d4d20','4883c220');call('typeEquals')
    g.take('85c0');g.branch('0f85',False)
    g.take('4c8b4348','4d8bce','4883ffff');g.branch('74',False,1)
    g.take('488d0c7f','4b8d0440','498d14ce','498d0cc6','4c8b742428','488bc6','4c8b6c2430',
        '4c8b642438','488b7c2468','4c8b7c2420','48894e10','48895608','48891e','4883c440','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,calls=calls,entryStride=24,selectedCountRequiredPositive=True,
        selectedTombstoneCountRequiredZero=True,selectedFirstSlotKeyRequiredActualObjectClass=True,
        output='same container, exact found entry and end-entry pointer',entryRspRestored=True,allNonvolatilesRestored=True)


def definition_class(regions,entry):
    g=BytesPath(regions,entry);runtime=g.relative('488b05');g.take('486390a0000000','48b865210b59c84216b2','482bca')
    rows=g.relative('482b0d');g.take('48f7e9','4803d1','48c1fa06','488bca','48c1e93f','4803ca')
    resolver=g.relative('e9');g.at=resolver
    g.take('48895c2408','57','4883ec20','4863d9','83fbff');g.branch('75',True,1)
    cache=g.relative('488b05');g.take('48833cd800');g.branch('75',True,1)
    need('same-class-cache',g.relative('488b05')==cache)
    g.take('488b04d8','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataRuntimeCellVa=runtime,typeDefinitionRowsCellVa=rows,
        classCacheCellVa=cache,classResolverTargetVa=resolver,typeDefinitionBytes=92,
        effect='derive signed index of actual type-definition row and return same nonnull indexed cached class',
        selectedTypeDefinitionIndexRequiredInBounds=True,selectedClassCacheEntryRequiredActualNamedClass=True,
        classConstructionOrLiveCacheObserved=False,entryRspRestored=True,allNonvolatilesRestored=True)


def zero_payload(regions,entry,*,count=8):
    need('finite-box-zero-size',type(count)is int and count in(8,24))
    g=BytesPath(regions,entry);g.take('488bc1','4c8bc9');base=g.relative('4c8d15')
    g.take('0fb6d2','49bb0101010101010101','4c0fafda','66490f6ec3','4983f80f');g.branch('0f87',count>15)
    table=None;target=None
    if count==8:
        g.take('0f1f00','4903c8','478b8c82');table=base+int.from_bytes(g.read(4),'little')
        g.take('4d03ca','41ffe1');g.at=table+count*4;target=base+int.from_bytes(g.read(4),'little');g.at=target
        g.take('4c8959f8','c3');writes=[[0,8]]
    else:
        g.take('660f6cc0','4983f820');g.branch('77',False,1);g.take('f30f7f01','f3420f7f4401f0','c3');writes=[[0,16],[8,24]]
    return dict(selectedBytes=g.seen,count=count,writeRanges=writes,byteValueRequiredZero=True,
        jumpTableVa=table,selectedTableTargetVa=target,returnsOriginalDestination=True,entryRspRestored=True)
