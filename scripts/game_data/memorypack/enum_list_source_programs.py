"""Exact selected enum-placeholder list programs, without nominal admission.

The source owner must independently select the actual ListFormatter method,
complete owned byte partitions, original nominal class/MethodInfo contexts and
the element callback. These pure programs prove signed four-byte count framing,
the actual unchanged Reader/local/Add transfers and bounded loop witnesses.
They do not select a nominal enum, observe a live registry, or infer wire width
from a managed layout. New-list allocation/capacity effects, initialized own
contexts, spare storage and normal helper/disabled-collector effects remain
conditions. The caller rejects counts below -1 or above its finite bound.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


LABEL='enumListSourcePrograms'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def constructor(regions,entry,*,cold=False):
    need('literal-constructor-path',type(cold)is bool)
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4220','488b88c0000000','488b4138','4883782000')
    g.branch('0f84',cold)
    if cold:
        g.take('488b4220','488b88c0000000','488b4138','ff10','90');g.jump('e9')
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,cold=cold,baseConstructorContextSlot=7,
        methodInfoClassOffset=32,classRgctxOffset=192,receiverUnchanged=True,
        noInstanceStoresOnSelectedPath=True,actualBaseConstructorIndirectCall=cold,
        entryRspRestored=True,normalReturn=True)


def disabled_barrier(regions,entry):
    """Only the actual guard/copy/JE/RET slices; no invented whole extent."""
    g=BytesPath(regions,entry);flag=g.relative('833d')+1
    g.take('00','4c8bc1');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,disabledFlagCell=flag,disabledFlagMustBeZero=True,
        incomingRcxCopiedToR8=True,memoryWrites=0,selectedCalls=0,
        entryRspRestored=True,normalReturn=True,fullPhysicalExtentProved=False)


def list_program(regions,entry,symbols,*,count=0,new=False):
    need('literal-count-mode',type(count)is int and -1<=count<=3 and type(new)is bool)
    g=BytesPath(regions,entry)
    g.take('4053','57','4154','4157','4883ec38','4c8bfa','4533e4','498bcf',
        '4489642420','488d542420','4489642468','498bd9','498bf8')
    g.call(symbols['header']);g.take('84c0');g.branch('0f84',count==-1)
    element_sites=[];provider_cell=None
    if count==-1:
        g.take('488bcf','4c8927');g.call(symbols['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889742470','48896c2460','4c896c2478','4c89742430',
            '8b742420','4c3927');g.branch('0f85',not new)
        if new:
            g.take('488b4b20','33d2','488b89c0000000');g.call(symbols['resolveClass'])
            g.take('488bc8');g.call(symbols['allocate']);g.take('488be8','4885c0')
            g.branch('0f84',False)
            g.take('488b4b20','488b91c0000000','488b4a08','4c396120')
            g.branch('0f84',False)
            g.take('488b4320','8bd6','488bcd','4c8b80c0000000','4d8b4008')
            g.call(symbols['capacity']);g.take('488bcf','48892f');g.call(symbols['barrier'])
        else:
            g.take('488b4320','488b2f','488b88c0000000','488b4110','4c396020')
            g.branch('0f84',False)
            g.take('ff451c','44896518');g.jump('e9')
        provider_cell=g.relative('488b0d');g.take('4439a1e0000000');g.branch('0f84',False)
        g.take('488b4320','488b88c0000000','488b4918')
        g.call(symbols['elementProvider']);g.take('488be8','458bf4','85f6')
        g.branch('7f',count>0,1)
        for i in range(count):
            g.take('4489642468','4885ed');g.branch('74',False,1)
            g.take('4c8d4c2468','4d8bc7','488bd5')
            element_sites.append(g.at);g.call(symbols['elementDispatch'])
            g.take('4c8b27','448b6c2468','4d85e4');g.branch('74',False,1)
            g.take('488b4320','4c8b80c0000000','498b4030','4883782000')
            g.branch('0f84',False)
            g.take('488b4320','418bd5','498bcc','4c8b80c0000000','4d8b4030')
            g.call(symbols['add']);g.take('41ffc6','41bc00000000','443bf6')
            g.branch('7c',i+1<count,1)
        if count:g.jump('e9')
        g.take('4c8b6c2478','488b6c2460','4c8b742430','488b742470')
    g.take('4883c438','415f','415c','5f','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,
        elementCallbacks=len(element_sites),elementCallbackSites=element_sites,
        providerClassCell=provider_cell,headerWireBytes=4,signedCountBits=32,
        nullCount=-1,reader='unchanged incoming RDX saved R15 to element R8',
        output='incoming R8 saved RDI; unchanged actual list to typed Add RCX',
        elementTransfer='zero DWORD RSP+104 -> callback R9 -> R13D -> Add EDX',
        constructorCapacity='unchanged signed count saved ESI to EDX',
        counter='r14d',savedCount='esi',elementWidthInferredFromMetadata=False,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True)


def buffered_header(regions,entry,offsets):
    keys=('currentPtr','bufferLength','advancedCount','consumed','totalLength')
    need('named-distinct-bounded-reader-offsets',set(offsets)==set(keys)
        and all(type(offsets[k])is int and 0<offsets[k]<128 for k in keys)
        and len(set(offsets.values()))==5)
    cur,rem,adv,used,total=(bytes((offsets[k],)).hex()for k in keys)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'04',
        '488bfa','488bd9');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b08','890f','8b73'+rem,'83c6fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,
        '486343'+used,'488b4b'+total,'448b07','482bc8','4963c0','483bc8')
    g.branch('0f8c',False)
    g.take('488b5c2430','4183f8ff','488b742438','0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=4,signedCountBits=32,
        output='incoming RDX signed raw DWORD',resultRegister='al',
        returnPredicate='unchanged count != -1',readerCounterAdvances=4,
        allPositiveElementBytesGuaranteed=False,otherNegativeCountsRejected=False,
        entryRspRestored=True,normalReturn=True)


def spare_add(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','ff411c','488bd9',
        '488b4910','498bf0','8bfa','4c634b18','4885c9')
    g.branch('74',False,1);g.take('443b4918');g.branch('73',False,1)
    g.take('418d4101','894318','443b4918');g.branch('73',False,1)
    g.take('4289548920','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,rawElementBitsPreserved=32,arrayStride=4,
        incomingElement='edx',listItemsSlot=16,countSlot=24,versionSlot=28,
        spareCapacityRequired=True,entryRspRestored=True,normalReturn=True)


def element_provider(regions,entry,*,cold_context=False):
    need('literal-provider-context-path',type(cold_context)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9')
    g.branch('74',cold_context,1)
    metadata_cells=[];metadata=None;initialize=None
    if cold_context:
        for _ in range(2):
            metadata_cells.append(g.relative('488d0d'));actual=g.relative('e8')
            need('same-provider-metadata-helper',metadata in(None,actual));metadata=actual
        g.take('48837f3800');g.branch('0f85',False)
        g.take('488bcf');initialize=g.relative('e8');g.jump('e9')
    type_cell=g.relative('488b0d')
    g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');type_handle=g.relative('e8')
    provider_cell=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');backend=g.relative('e8')
    g.take('488b4f38','ba01000000','488bd8');resolve_class=g.relative('e8')
    g.take('4885db');g.branch('0f84',False)
    g.take('488b0b','488bd0');assignable=g.relative('e8')
    g.take('84c0');g.branch('0f84',False)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    need('provider-cold-hot-same-usage-classes',not cold_context or metadata_cells==[provider_cell,type_cell])
    return dict(selectedBytes=g.seen,entry=entry,coldContext=cold_context,
        metadataUsageCells=metadata_cells,actualMetadataInitializer=metadata,
        actualMethodContextInitializer=initialize,systemTypeClassCell=type_cell,
        providerClassCell=provider_cell,actualTypeFromHandle=type_handle,actualBackend=backend,
        actualClassContextSlotResolver=resolve_class,actualAssignableCheck=assignable,
        methodInfoContextOffset=56,nominalCarrierContextSlot=0,expectedFormatterClassContextSlot=1,
        sameOriginalMethodInfoPreserved=True,sameBackendReferenceReturnedUnchanged=True,
        nonnullCompatibleFormatterRequired=True,entryRspRestored=True,normalReturn=True)


def register_list(regions,entry,*,cold_context=False):
    need('literal-register-context-path',type(cold_context)is bool)
    g=BytesPath(regions,entry)
    g.take('4053','57','4156','4883ec40','48837a3800','488bda','4c8bf1')
    g.branch('75',not cold_context,1)
    metadata_cells=[];metadata=None;initialize=None
    if cold_context:
        for _ in range(3):
            metadata_cells.append(g.relative('488d0d'));actual=g.relative('e8')
            need('same-register-metadata-helper',metadata in(None,actual));metadata=actual
        g.take('48837b3800');g.branch('0f84',True)
        g.take('488bcb');initialize=g.relative('e8');g.jump('e9')
    provider=g.relative('488b05');g.take('83b8e000000000');g.branch('0f84',False)
    type_cell=g.relative('488b0d')
    g.take('488b80b8000000','488b5b38','83b9e000000000','488b7818','488b1b')
    g.branch('0f84',False);g.take('33d2','488bcb');type_handle=g.relative('e8')
    g.take('488bd8','4885ff');g.branch('0f84',False)
    g.take('48896c2468');dictionary_site=g.at;dictionary=g.relative('488b2d')
    g.take('48c744246000000000','4885c0');g.branch('0f84',False)
    g.take('4889742470','488b7718','4885f6');g.branch('0f84',False)
    g.take('488b4d20','ba0c000000','488b89c0000000');slot=g.relative('e8')
    g.take('488bd0','b901000000','4c8bcb','4c8bc6');hashing=g.relative('e8')
    g.take('488b4d20','8bf0','488b91c0000000','488b4a78','4883792000');g.branch('0f84',False)
    g.take('488b5520','4d8bce','488bcf','4c8b82c0000000','488bd3','498b4078','448bc6',
        '4889442438','488d442460','4889442430','c644242801','c644242001')
    insert=g.relative('e8')
    g.take('488b742470','488b6c2468','4883c440','415e','5f','5b','c3')
    need('same-register-cold-hot-metadata-classes',not cold_context or metadata_cells==[dictionary,provider,type_cell])
    return dict(selectedBytes=g.seen,entry=entry,coldContext=cold_context,
        metadataUsageCells=metadata_cells,actualMetadataInitializer=metadata,
        actualMethodContextInitializer=initialize,providerClassCell=provider,
        systemTypeClassCell=type_cell,actualTypeFromHandle=type_handle,
        dictionaryMethodUsageInstruction=dictionary_site,dictionaryMethodInfoCell=dictionary,
        actualClassContextSlotResolver=slot,actualHashHelper=hashing,actualInsertion=insert,
        nominalCarrierMethodContextSlot=0,methodInfoContextOffset=56,
        dictionaryHashContextSlot=12,dictionaryInsertionContextSlot=15,
        registryStaticFieldsOffset=184,registryDictionaryFieldOffset=24,
        sameIncomingFormatterReferencePassedUnchanged=True,
        insertionKey='System.Type from own Register<List<nominal enum>> method context slot0',
        insertionValue='unchanged incoming RCX formatter preserved R14',
        entryRspRestored=True,normalReturn=True)
