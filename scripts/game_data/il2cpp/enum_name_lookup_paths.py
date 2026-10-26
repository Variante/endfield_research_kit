"""Current placeholder name-key, found-slot and record-class source paths.

The complete selected warm lookup preserves its namespace/name inputs in a
tag-zero key, rejects the actual table-end iterator, reverses the selected
metadata-record geometry and forwards the record-class resolver's return.
The selected nonempty-table found-slot path hashes the literal ASCII request,
compares both strings byte-for-byte including their terminators, and returns
that same slot. Record insertion's core-image path constructs the same key
from the actual metadata record and passes its unchanged record pointer as
payload. The record-class cache has separate minus-one, hit and cold paths;
the cold path calls the independently owned actual constructor with the same
index and publishes its result in that index's cache slot.

These are conditional native transfers. Table construction/population,
first-probe occupancy, coherent cache contents, compatible normal mutex/helper
returns and disjoint stable metadata/table storage are explicit requirements.
Neither runtime startup execution nor all collision/rebuild paths are claimed.
Names alone do not establish a live class, formatter or MethodInfo. Concrete
enum callbacks, collection framing and whole owners remain unadmitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.record_index_geometry import prove_record_index_geometry

SCHEMA='endfield.enum-name-lookup-paths.v1'
LABEL='enumNameLookupPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _ascii(value):
    need('bounded-nonempty-ASCII-name',type(value)is bytes and 0<len(value)<=128 and all(0<b<128 for b in value))


def _hash_loop(g,value,*,name):
    _ascii(value);iteration=g.at
    for i in range(0,len(value),2):
        if name:g.take('4d6bc921','480fbec0','4c33c8','480fbe4101','84c0')
        else:g.take('4d6bc021','480fbec9','4c33c1','480fbe4801','84c9')
        g.branch('74',i+1==len(value),1)
        if i+1==len(value):return
        if name:g.take('486bd221','4883c102','4833d0','0fb601','84c0')
        else:g.take('486bd221','4883c002','4833d1','0fb608','84c9')
        back=g.relative('75',1);need('same-byte-pair-hash-backedge',back==iteration)
        if i+2<len(value):g.at=back


def _equal_loop(g,value):
    _ascii(value);iteration=g.at
    for byte in value+b'\0':
        g.take('0fb610','420fb60c00','2bd1');g.branch('75',False,1)
        g.take('48ffc0','85c9');back=g.relative('75',1)
        need('same-byte-equality-backedge',back==iteration)
        if byte:g.at=back


def find_program(regions,entry,*,namespace=b'System',name=b'Int32Enum'):
    """Complete first occupied matching-slot path; no table-population claim."""
    _ascii(namespace);_ascii(name);g=BytesPath(regions,entry)
    g.take('4055','4156','4157','4883ec30','488b4148','4d8bf8','4c8bf2','488be9','483b4140');g.branch('0f84',False)
    g.take('48895c2450','41b805150000','4889742458','458bc8','48897c2460','418bd0','4c89642428',
        '4c8b6150','498b4f10','49ffcc','4c896c2420','4533ed','0fb601','84c0');g.branch('74',False,1)
    g.take('0f1f440000');_hash_loop(g,name,name=True)
    g.take('498b4708','4c69d2658b585d','0fb608','498bd0','4d03d1','84c9');g.branch('74',False,1)
    g.take('6690');_hash_loop(g,namespace,name=False)
    g.take('488b5d78','48c7c6ffffffff','8b7d58','4869c2658b585d','4903c0','4c69d8dba2fa1c','4d03da',
        '4d23dc','4d8bcb','49c1e105','413b3c19');g.branch('75',True,1)
    g.take('48837d4000');g.branch('0f87',False)
    g.take('4d8bcb','49c1e105','418b0419','413907');g.branch('75',False,1)
    g.take('41833f00');g.branch('0f84',True)
    g.take('498b4708','4d8b441908','4c2bc0','0f1f4000');_equal_loop(g,namespace)
    g.take('85d2');g.branch('0f85',False)
    g.take('498b4710','4d8b441910','4c2bc0','660f1f840000000000');_equal_loop(g,name)
    g.take('85d2');g.branch('0f84',True)
    g.take('488b5550','4c8bc3','4983fbff');g.branch('74',False,1)
    g.take('49c1e305','48c1e205','4803d3','498d0c1b','4c8b642428','488b7c2460','488b742458',
        '488b5c2450','4c8b6c2420','49895610','49894e08','49892e','498bc6','4883c430','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,namespaceAscii=namespace.decode('ascii'),nameAscii=name.decode('ascii'),
        incomingArguments=dict(rcx='table',rdx='iterator output',r8='tag-zero namespace/name key'),
        keyTag=0,keyNamespaceOffset=8,keyNameOffset=16,slotBytes=32,slotNamespaceOffset=8,slotNameOffset=16,
        tableCapacityOffset=80,tableSlotsOffset=120,comparisonIncludesBothNullTerminators=True,
        iteratorTableOffset=0,iteratorSlotOffset=8,iteratorEndOffset=16,returnedOutputPointerUnchanged=True,
        matchingSlotIndexMustNotBeMinusOne=True,selectedFirstOccupiedSlotMustMatch=True,deletedSlotCountMustBeZero=True,
        tableMustBeNonempty=True,opaqueCalls=0,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        tablePopulationProved=False,collisionAndRebuildPathsProved=False)


def lookup_program(regions,entry,*,record_bytes,records):
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','56','57','4157','4883ec50','498bf0','488bea','488bd9','4883793000')
    g.branch('0f85',True)
    g.take('c744242000000000','48896c2428','4889742430','4c8d442420','488d542438','488b4b30');find=g.relative('e8')
    g.take('488b4330','488b4850','48c1e105','48034878','4c8b442440','4c3bc1');g.branch('74',False,1)
    header=g.relative('488b05');g.take('486388');header_field=int.from_bytes(g.read(4),'little',signed=True)
    g.take('4d8b4018','4c2bc1');metadata=g.relative('4c2b05');g.take('48b8')
    multiplier=int.from_bytes(g.read(8),'little',signed=True)
    g.take('49f7e8','4903d0','48c1fa');shift=int.from_bytes(g.read(1),'little')
    g.take('488bca','48c1e93f','4803ca');resolve=g.relative('e8');g.jump('eb',1)
    g.take('488b5c2478','488bac2480000000','4883c450','415f','5f','5e','c3')
    return dict(selectedBytes=g.seen,findTarget=find,recordClassTarget=resolve,tableHolderOffset=48,
        keyTag=0,keyNamespaceFromEntryRdx=True,keyNameFromEntryR8=True,foundIteratorRequired=True,
        iteratorSlotOutputOffset=64,slotRecordOffset=24,metadataHeaderCell=header,metadataBaseCell=metadata,
        headerOffsetField=header_field,recordBytes=record_bytes,
        recordIndexGeometry=prove_record_index_geometry(multiplier=multiplier,shift=shift,record_bytes=record_bytes,records=records),
        resolverEcx='exact index of selected slot metadata record',resolverResultReturnedUnchanged=True,
        normalReturn=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r15'],
        selectedImageNameTableMustBeInitialized=True,slotPayloadIsValidSelectedMetadataRecordRequired=True)


def record_class_program(regions,entry,*,mode):
    need('literal-record-cache-path',mode in('minus-one','hit','cold')and type(mode)is str)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','4863d9','83fbff');g.branch('75',mode!='minus-one',1)
    if mode=='minus-one':
        g.take('33c0','488b5c2430','4883c420','5f','c3')
        return dict(selectedBytes=g.seen,recordIndex=-1,returnedRax=0,normalReturn=True,entryRspRestored=True,opaqueCalls=0)
    cache=g.relative('488b05');g.take('48833cd800');g.branch('75',mode=='hit',1)
    facts={}
    if mode=='cold':
        mutex=g.relative('488d3d');g.take('48897c2438','488bcf');lock=g.relative('e8');g.take('90')
        need('same-cache-at-locked-recheck',g.relative('488b05')==cache)
        g.take('48833cd800');g.branch('75',False,1)
        g.take('8bcb');ctor=g.relative('e8');need('same-cache-at-constructor-publication',g.relative('488b0d')==cache)
        g.take('488904d9');depth=g.relative('8b05');g.take('85c0');g.branch('7e',False,1)
        g.take('83f801');g.branch('75',False,1)
        g.take('33c0');thread=g.relative('488905');need('same-lock-depth-clear',g.relative('8905')==depth)
        g.take('488bcf');unlock=g.relative('e8');g.jump('eb',1)
        facts=dict(mutexCell=mutex,lockTarget=lock,constructorTarget=ctor,unlockTarget=unlock,lockDepthCell=depth,
            lockThreadCell=thread,selectedLockDepth=1,constructorEcx='unchanged incoming signed record index',
            unchangedConstructorResultStoredToSameIndex=True,cacheStableAcrossNormalUnlockRequired=True)
    need('same-returned-record-cache-cell',g.relative('488b05')==cache)
    g.take('488b04d8','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,mode=mode,cacheCell=cache,cachePointerStride=8,
        returnedValue='fresh cache[signed incoming record index]',validRecordIndexRequired=True,
        coherentNonaliasingCacheRequired=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],**facts)


def insert_key_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4885d2');g.branch('0f84',False)
    g.take('48895c2408','57','4883ec70','837a0cff','488bda','488bf9');g.branch('75',False,1)
    core_image=g.relative('483b0d');g.branch('74',True,1)
    header=g.relative('4c8b05');g.take('488d542450','48634b04','c744243000000000','48895c2448','49634018')
    metadata=g.relative('480305');g.take('4803c8','49634018')
    need('same-metadata-string-base-cell',g.relative('480305')==metadata)
    g.take('4c8d442430','48894c2420','48630b','4803c8','48894c2428','0f10442420','488b4f30','0f11442438')
    insert=g.relative('e8');g.take('488b9c2480000000','4883c470','5f','c3')
    return dict(selectedBytes=g.seen,coreImageCell=core_image,selectedImageMustEqualCoreCell=True,
        recordMustBeNonnull=True,recordDeclaringTypeIndexMustBeMinusOne=True,recordNameIndexOffset=0,recordNamespaceIndexOffset=4,
        metadataHeaderCell=header,metadataBaseCell=metadata,stringSectionHeaderOffset=24,
        insertTarget=insert,tableHolderOffset=48,keyTag=0,keyNamespaceOffset=8,keyNameOffset=16,
        payloadOffset=24,payloadUnchangedIncomingMetadataRecord=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],insertHelperSemanticsProved=False)


def _owned_graph(image,target):
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.type_data_initialization_control import _complete
    body=owned(image,target);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));graph=_complete(rows,target)
    graph['edges']={at:sorted(v)for at,v in graph['edges'].items()}
    return body,graph


def derive(image,pins,**key_arguments):
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    enum_variant=key_arguments.get("enum_variant");variant=select(enum_variant)
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_argument_interner_paths import derive as interner_source
    _publication_gate(image,pins);md=image.metadata
    prior=interner_source(image,pins,**key_arguments);placeholder=prior['proof']['placeholderTypeSource']
    selected=placeholder['proof']['argumentKeySource']['proof']['normalizerSelection']
    publication=selected['proof']['placeholderPublication'];target=publication['classLookup']
    lookup,lookup_graph=_owned_graph(image,target)
    transfer=lookup_program(lookup['regions'],target,record_bytes=md.type_record_size,records=len(md.types))
    find,find_graph=_owned_graph(image,transfer['findTarget']);found=find_program(find['regions'],find['pointer'],name=variant['placeholderName'])
    resolver,resolver_graph=_owned_graph(image,transfer['recordClassTarget'])
    cache=[record_class_program(resolver['regions'],resolver['pointer'],mode=mode)for mode in('minus-one','hit','cold')]
    fields=selected['proof']['classFieldSource'];need('same-independent-selected-class-constructor',
        cache[2]['constructorTarget']==fields['proof']['actualColdClassConstructor']['target'])
    fixup=fields['proof']['typeDataFixup']['proof']['fixup']
    need('same-selected-metadata-record-geometry',all(transfer[key]==fixup[key]for key in('metadataHeaderCell','metadataBaseCell','headerOffsetField','recordBytes')))
    # Both cold table loops call the same record-to-name insertion entry. Its
    # complete family/CFG is freshly decoded; no raw E8 candidate grants scope.
    calls=[]
    for at,raw in lookup['regions']:
        pattern=bytes.fromhex('488bcbe8');offset=raw.find(pattern)
        while offset>=0:
            site=at+offset+3;calls.append(dict(site=site,target=site+5+int.from_bytes(raw[offset+4:offset+8],'little',signed=True)))
            offset=raw.find(pattern,offset+1)
    need('same-actual-two-record-insertion-calls',len(calls)==2 and len({r['target']for r in calls})==1)
    insertion,insertion_graph=_owned_graph(image,calls[0]['target']);key=insert_key_program(insertion['regions'],insertion['pointer'])
    need('same-actual-metadata-base-cells-for-insert-key',all(key[k]==transfer[k]for k in('metadataHeaderCell','metadataBaseCell')))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(internerSource=prior,lookupWindows=lookup['windows'],lookupCfg=lookup_graph,selectedWarmLookup=transfer,
            findWindows=find['windows'],findCfg=find_graph,selectedFoundSlot=found,recordClassWindows=resolver['windows'],
            recordClassCfg=resolver_graph,recordClassPaths=cache,actualInsertionCalls=calls,
            insertKeyWindows=insertion['windows'],insertKeyCfg=insertion_graph,selectedInsertKey=key),
        selectedNameKeyComparisonsAndRecordClassTransfersProved=True,initializedNameTablePopulationProved=False,
        placeholderLookupResultIdentityProved=False,initializedInternerResultIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete owned lookup/find/record-class/insert-key instruction partitions, CFGs and normal frames; complete selected warm lookup, byte-equal found slot, core-image insertion key, and cold/hit/-1 cache paths.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Name table keys, metadata records and class-cache representation.',
            unresolved=['name table insertion/population/collision and initialized cache identity','opaque helper alias preservation and startup execution',
                'interner static registration/canonical identity','actual nominal formatter/provider/MethodInfo callback selection','wire/parent/EOF']))))
