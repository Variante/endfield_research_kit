"""Actual nominal registry source; dictionary state remains explicit.

The provider's successful registered-formatter lookup must use the same static
registry dictionary and same original System.Type key as nominal registration.
Its returned object is carried unchanged through the generic formatter cast.
Dictionary publication, callback/MethodInfo identity and wire grammar require
separate source joins; a method called Register or a successful managed cast is
insufficient. LOCK OR stack fences are exact read/modify/write instructions,
not invented no-ops, and collector/mutex/callee effects remain conditional.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-registry-publication-paths.v1'
LABEL='enumRegistryPublicationPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def memory_effect(row):
    from scripts.game_data.il2cpp.initializer_control import memory_effect as ordinary
    from scripts.game_data.il2cpp.string_source_instructions import decode_locked_memory_or
    from scripts.game_data.il2cpp.signed_division import decode_signed_divide
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    parsed=decode_locked_memory_or(raw,0,at)
    if parsed is not None or 'lockedMemoryOrOperation'in row:
        actual=row.get('lockedMemoryOrOperation');own,end=parsed if parsed is not None else({},0)
        need('exact-lock-or-stack-dword-zero',end==len(raw)and raw==bytes.fromhex('f0830c2400')
            and own.get('text')==row['text']and row.get('write')is None and own.get('lockedMemoryOrOperation')==actual)
        return dict(kind='lockedMemoryOrOperation',facts=actual)
    if 'signedDivisionOperation'in row or row['text'].startswith('idiv '):
        parsed=decode_signed_divide(raw,0,at);own,end=parsed if parsed is not None else({},0)
        need('exact-readonly-divisor-source',end==len(raw)and own.get('text')==row['text']
            and own.get('signedDivisionOperation')==row.get('signedDivisionOperation')and own.get('write')==row.get('write'))
        return None
    return ordinary(row)


def decode(mapper,data,entry):
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode as inherited
    from scripts.game_data.il2cpp.signed_division import decode_bit_reset,decode_dividend_extension,decode_signed_divide
    from scripts.game_data.il2cpp.string_source_instructions import decode_locked_memory_or
    from scripts.game_data.il2cpp.register_shift_instructions import decode_prefixed_multibyte_nop
    from scripts.game_data.il2cpp.integer_source_operands import decode_byte_memory_test
    from scripts.game_data.il2cpp.integer_effects import decode_immediate_memory_store
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in(decode_bit_reset,decode_dividend_extension,decode_signed_divide,decode_locked_memory_or,
                    decode_prefixed_multibyte_nop,decode_byte_memory_test,decode_immediate_memory_store):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return inherited(Fallback(),data,entry)


def ordinary_program(regions,rows,entry):
    """Keep every owned byte while proving only actual ordinary-entry control."""
    from scripts.game_data.il2cpp.owned_partition import check_byte_partition,checked_rows
    from scripts.game_data.il2cpp.type_data_initialization_control import _flow
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    ranges=[(a,a+len(raw))for a,raw in regions]
    pieces=[(int(r['va'],16),int(r['va'],16)+len(bytes.fromhex(r['bytes'])),'instruction')for r in rows]
    check_byte_partition(ranges,pieces,LABEL)
    for at,raw in regions:checked_rows([r for r in rows if at<=int(r['va'],16)<at+len(raw)],raw,LABEL)
    by={int(r['va'],16):r for r in rows};need('unique-owned-entry-instructions',len(by)==len(rows)and entry in by)
    pending=[entry];reached=set()
    while pending:
        at=pending.pop()
        if at in reached:continue
        need('ordinary-instruction-boundary',at in by);reached.add(at);row=by[at];flow=_flow(row,{},{});kind=flow['kind']
        if kind in('next','call','opaqueCall','indirectCall','registerCall','conditional'):pending.append(at+len(bytes.fromhex(row['bytes'])))
        if kind in('conditional','jump'):pending.append(flow['target'])
        need('finite-ordinary-control-kind',kind in('next','call','opaqueCall','indirectCall','registerCall','conditional','jump','return','trap'))
    selected=[r for r in rows if int(r['va'],16)in reached];selected_regions=[]
    for row in sorted(selected,key=lambda r:int(r['va'],16)):
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes'])
        if selected_regions and selected_regions[-1][0]+len(selected_regions[-1][1])==at:
            old_at,old_raw=selected_regions[-1];selected_regions[-1]=(old_at,old_raw+raw)
        else:selected_regions.append((at,raw))
    graph,padding=complete_program(selected_regions,selected,entry,memory_effect_decoder=memory_effect)
    return dict(completeOwnedBytesPartitioned=True,ordinaryEntryControl=graph,ordinaryPadding=padding,
        ordinaryInstructionCount=len(selected),unenteredOwnedRows=[r for r in rows if int(r['va'],16)not in reached],
        unenteredOwnedByteSemanticsAdmitted=False,exceptionOrResumptionEntryAdmitted=False)


def backend_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bd9');g.branch('75',True,1)
    provider=g.relative('488b0d');g.take('48c744243000000000');ready=g.relative('e8')
    need('same-provider-static-class',g.relative('488b05')==provider)
    g.take('488b88b8000000','488b4918','4885c9');g.branch('0f84',False)
    context_site=g.at;context=g.relative('4c8b0d');g.take('4c8d442430','488bd3');lookup=g.relative('e8')
    g.take('84c0');g.branch('0f85',True)
    g.take('488b442430','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,initializedUsageFlagCell=flag,
        initializedUsageFlagMustBeNonzero=True,providerClassCell=provider,actualClassReadyHelper=ready,
        staticFieldsOffset=184,registryDictionaryOffset=24,lookupUsageInstruction=context_site,
        lookupMethodInfoCell=context,actualDictionaryLookup=lookup,
        lookupArguments=dict(rcx='actual provider staticFields.registry dictionary',rdx='unchanged requested System.Type',
            r8='address of owned initially zero output reference',r9='actual closed dictionary lookup MethodInfo'),
        successfulLookupRequired=True,sameDictionaryResultReturnedUnchanged=True,
        entryRspRestored=True,normalReturn=True,nonvolatilesRestored=['rbx','rdi'],
        dictionaryOrCallbackSemanticsAdmitted=False)


def public_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('74',False,1);provider=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('74',False,1)
    g.take('488bcb','4883c420','5b');target=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,initializedUsageFlagCell=flag,initializedUsageFlagMustBeNonzero=True,
        providerClassCell=provider,providerInitializedFlagOffset=224,providerInitializedFlagMustBeNonzero=True,
        actualBackendTail=target,sameRequestedSystemTypePassedUnchanged=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx'],normalTailTransfer=True,
        actualNamedCanonicalPointerEquivalenceClaimed=False)


def actual_backend_hit_program(regions,entry):
    """Own optimized backend's inline lookup; never aliases the named body."""
    g=BytesPath(regions,entry);g.take('4889542410','55','57','4883ec48')
    flag=g.relative('803d')+1;g.take('00','488bf9');g.branch('75',True,1)
    provider=g.relative('488b05');g.take('48c744246800000000','83b8e000000000');g.branch('75',True,1)
    g.take('488b80b8000000','488b6818','4885ed');g.branch('0f84',False)
    g.take('48895c2470');usage_site=g.at;method_cell=g.relative('488b1d');g.take('4885ff');g.branch('0f84',False)
    g.take('4889742478','4c896c2440','4c89742438','4c897c2430','488b7518','4885f6');g.branch('0f84',False)
    g.take('488b4b20','ba0c000000','488b89c0000000');slot=g.relative('e8')
    g.take('488bd0','b901000000','4c8bcf','4c8bc6');hashing=g.relative('e8')
    g.take('488b4b20','448bf8','488b91c0000000','488b8ae8000000','4883792000');g.branch('75',True,1)
    g.take('488b4b20','488b5d10','488b91c0000000','4c8baae8000000','f0830c2400','4885db');g.branch('0f84',False)
    g.take('488b7310','4885f6');g.branch('0f84',False)
    g.take('498b4d20','ba02000000','488b89c0000000');need('same-actual-backend-class-slot-helper',g.relative('e8')==slot)
    g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b5b10','4885db');g.branch('0f84',False)
    g.take('418bc7','0fbaf01f','99','f77e18','3b5318');g.branch('0f83',False)
    g.take('4863c2','488b5cc320','f0830c2400','4885db');g.branch('74',False,1)
    g.take('660f1f440000','443b7b28');g.branch('75',False,1)
    g.take('488b7518','4c8b7310','4885f6');g.branch('0f84',False)
    g.take('498b4d20','ba0c000000','488b89c0000000');need('same-actual-backend-equality-context-helper',g.relative('e8')==slot)
    g.take('488bd0','48897c2420','33c9','4d8bce','4c8bc6');equality=g.relative('e8')
    g.take('84c0');g.branch('0f85',True)
    collector=g.relative('833d')+1;g.take('00','488b4318','4889442468');g.branch('0f84',True)
    g.take('488b442468','4c8b742438','4c8b6c2440','4c8b7c2430','488b742478','488b5c2470',
        '4883c448','5f','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,initializedUsageFlagCell=flag,initializedUsageFlagMustBeNonzero=True,
        providerClassCell=provider,providerInitializedFlagMustBeNonzero=True,staticFieldsOffset=184,registryDictionaryOffset=24,
        lookupMethodUsageInstruction=usage_site,lookupMethodInfoCell=method_cell,actualContextSlotResolver=slot,
        actualHashHelper=hashing,actualEqualityHelper=equality,inlinedLookupMethodContextSlot=29,
        requestedSystemTypePassedUnchangedToHashAndEquality=True,selectedKeyEqualityResultRequired=True,
        selectedFirstNodeNonnullAndHashEqualRequired=True,nodeKeyOffset=16,nodeValueOffset=24,nodeHashOffset=40,
        hashNormalization='uint32(hash) AND 0x7fffffff',positiveBoundedBucketCountRequired=True,
        collectorFlagCell=collector,collectorFlagMustBeZero=True,
        unchangedSelectedNodeValueReturned=True,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbp','rdi','rbx','rsi','r13','r14','r15'],
        canonicalBodyPointerEquivalenceClaimed=False,actualRegistryStateOrCallbackProved=False)


def insert_empty_program(regions,entry):
    """Exact normal first-empty publication, under stable tables/owned lock."""
    g=BytesPath(regions,entry)
    g.take('488bc4','4c894820','44894018','48895010','48894808',
        '53','56','57','4154','4155','4156','4157','4883ec70','458be0','4c8bf9','4533ed',
        '4489688c','4c896890','44886888','488bb424e8000000','440fb6b424d8000000','0f1f840000000000',
        '498b7f10','f0830c2400','488bdf','48895c2438','4885ff')
    g.branch('0f84',False);g.take('488b7f10','4885ff');g.branch('0f84',False)
    g.take('4885db');g.branch('0f84',False);g.take('488b5b18','4885db');g.branch('0f84',False)
    g.take('488b4e20','ba02000000','488b89c0000000');slot=g.relative('e8')
    g.take('83b8e000000000');g.branch('75',True,1)
    g.take('418bc4','0fbaf01f','99','f77f18','4c63e2','418bc4','99','f77b18',
        '89542434','c68424d800000000','c644243000','4c896c2450',
        '488d442430','4889442458','488d442438','4889442460','488d442434','4889442468','4584f6')
    g.branch('74',False,1);g.take('488b442438','4885c0');g.branch('0f84',False)
    g.take('488b4018','4885c0');g.branch('0f84',False)
    g.take('48634c2434','3b4818');g.branch('0f83',False)
    g.take('488b4cc820','807c243000');g.branch('0f85',False)
    g.take('4885c9');g.branch('0f84',False);g.take('baffffffff');lock=g.relative('e8')
    g.take('88442430','488b4c2438','498b4710','f0830c2400','483bc8');g.branch('0f85',False)
    g.take('488b442438','4885c0');g.branch('0f84',False);g.take('488b5810','4885db');g.branch('0f84',False)
    g.take('443b6318');g.branch('0f83',False);g.take('4a8b5ce320','4885db');g.branch('0f84',True)
    g.take('4885c0');g.branch('0f84',False);g.take('4c8b7010','4d85f6');g.branch('0f84',False)
    g.take('453b6618');g.branch('0f83',False)
    g.take('4f8b7ce620','488b4620','488b88c0000000','488b8148010000','f6803801000001')
    g.branch('75',True,1);g.take('488bc8');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
    g.take('488b4e20','488b91c0000000','488b8a50010000','4883792000');g.branch('75',True,1)
    g.take('488b8424b8000000','48894710');collector=g.relative('8b05');bitmap=g.relative('488d1d')
    g.take('85c0');g.branch('74',True,1)
    g.take('4c8bac24c8000000','4c896f18','85c0');g.branch('74',True,1)
    g.take('f0830c2400','4c897f20');need('same-node-next-collector',g.relative('833d')+1==collector);g.take('00');g.branch('74',True,1)
    g.take('8b8424c0000000','894728','453b6618');g.branch('0f83',False)
    g.take('498d542404','498d14d6','f0830c2400');publication=g.at;g.take('48893a')
    need('same-bucket-publication-collector',g.relative('833d')+1==collector);g.take('00');g.branch('74',True,1)
    g.take('488b442438','4885c0');g.branch('0f84',False)
    g.take('488b4020','f0830c2400','4885c0');g.branch('0f84',False)
    g.take('48634c2434','3b4818');g.branch('0f83',False)
    g.take('488d1488','8b4220','3dfeffff7f');g.branch('0f8f',False);g.take('ffc0','894220')
    g.take('488b4c2438','4885c9');g.branch('0f84',False)
    g.take('488b4920','f0830c2400','4885c9');g.branch('0f84',False)
    g.take('4863542434','3b5118');g.branch('0f83',False)
    g.take('32c0','0fb6f8','41b801000000','4c8bb424b0000000','418b4624','39449120','410f4ff8',
        '4088bc24d8000000','488d4c2458');cleanup=g.relative('e8');g.jump('eb',1)
    g.take('4084ff');g.branch('74',True,1)
    g.take('4c8b8424e0000000','4d8928');need('same-output-reference-collector',g.relative('833d')+1==collector)
    g.take('00');g.branch('74',True,1)
    g.take('b001','4883c470','415f','415e','415d','415c','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,entry=entry,tablesOffset=16,bucketsOffset=16,locksOffset=24,countsPerLockOffset=32,
        arrayLengthOffset=24,arrayDataOffset=32,nodeKeyOffset=16,nodeValueOffset=24,nodeNextOffset=32,nodeHashOffset=40,
        inputHashNormalization='uint32(hash) AND 0x7fffffff',bucketIndex='normalizedHash % positive buckets.Length',
        lockIndex='bucketIndex % positive locks.Length',positiveBoundedBucketAndLockCountsRequired=True,
        actualSlotResolver=slot,actualLockHelper=lock,lockAcquisitionArgument=-1,normalOwnedLockAcquisitionRequired=True,
        sameTablesBeforeAndAfterLockRequired=True,selectedBucketInitiallyEmptyRequired=True,
        actualNodeAllocator=allocate,nodeAllocationContextSlot=41,nodeConstructorContextSlot=42,
        initializedNodeClassAndConstructorRequired=True,nonnullFreshDisjointNodeRequired=True,
        collectorFlagCell=collector,collectorFlagMustBeZero=True,collectorBitmapBase=bitmap,
        bucketPublicationInstruction=publication,unchangedIncomingKeyStoredInNode=True,
        unchangedIncomingFormatterStoredInNode=True,sameNewNodePublishedToActualBucket=True,
        nodeNextEqualsPriorEmptyBucket=True,sameOriginalHashStored=True,selectedCountBelowSignedOverflowRequired=True,
        selectedCountAfterIncrementAtMostDictionaryBudgetRequired=True,actualCleanupHelper=cleanup,
        cleanupPreservesPublishedNodeAndRegistryRequired=True,normalCleanupRequired=True,
        unchangedIncomingFormatterStoredInOutReference=True,returnedLowByte=1,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbx','rsi','rdi','r12','r13','r14','r15'],
        existingKeyUpdateCollisionResizeAndOtherCollectorPathsProved=False)


def lookup_hit_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4053','57','4154','4156','4883ec38','498bd9','498bf8','4c8be2','4c8bf1','4885d2')
    g.branch('0f84',False);g.take('4889742470','488b7118','4885f6');g.branch('0f84',False)
    g.take('498b4920','ba0c000000','4c896c2478','4c897c2430','488b89c0000000');slot=g.relative('e8')
    g.take('488bd0','b901000000','4d8bcc','4c8bc6');hashing=g.relative('e8')
    g.take('488b4b20','448bf8','488b91c0000000','488b8ae8000000','4883792000');g.branch('75',True,1)
    g.take('488b4b20','498b5e10','48896c2460','488b91c0000000','4c8baae8000000','f0830c2400','4885db')
    g.branch('0f84',False);g.take('488b7310','4885f6');g.branch('0f84',False)
    g.take('498b4d20','ba02000000','488b89c0000000');need('same-lookup-context-slot-helper',g.relative('e8')==slot)
    g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b5b10','4885db');g.branch('0f84',False)
    g.take('418bc7','0fbaf01f','99','f77e18','3b5318');g.branch('0f83',False)
    g.take('4863c2','488b5cc320','f0830c2400','4885db');g.branch('74',False,1)
    g.take('443b7b28');g.branch('75',False,1)
    g.take('498b7618','488b6b10','4885f6');g.branch('0f84',False)
    g.take('498b4d20','ba0c000000','488b89c0000000');need('same-key-equality-context-slot-helper',g.relative('e8')==slot)
    g.take('488bd0','4c89642420','33c9','4c8bcd','4c8bc6');equality=g.relative('e8')
    g.take('84c0');g.branch('75',True,1)
    collector=g.relative('833d')+1;g.take('00','488b4318','488907');g.branch('74',True,1)
    g.take('b001');g.jump('eb',1)
    g.take('488b6c2460','4c8b6c2478','4c8b7c2430','488b742470','4883c438','415e','415c','5f','5b','c3')
    return dict(selectedBytes=g.seen,entry=entry,actualContextSlotResolver=slot,actualHashHelper=hashing,
        actualEqualityHelper=equality,hashContextSlot=12,inlinedLookupMethodContextSlot=29,
        dictionaryTablesOffset=16,dictionaryComparerOffset=24,bucketsOffset=16,
        nodeKeyOffset=16,nodeValueOffset=24,nodeHashOffset=40,arrayLengthOffset=24,arrayDataOffset=32,
        inputHashNormalization='uint32(hash) AND 0x7fffffff',bucketIndex='normalizedHash % positive buckets.Length',
        requestedKeyNonnullRequired=True,positiveBoundedBucketCountRequired=True,
        selectedFirstNodeNonnullAndHashEqualRequired=True,selectedKeyEqualityResultRequired=True,
        equalityArguments=dict(r8='actual dictionary comparer',r9='actual selected node.key',
            stack32='unchanged requested System.Type',ecx=0,rdx='actual closed equality MethodInfo'),
        collectorFlagCell=collector,collectorFlagMustBeZero=True,
        actualNodeValueStoredUnchangedToIncomingOutAddress=True,returnedLowByte=1,
        entryRspRestored=True,normalReturn=True,nonvolatilesRestored=['rbx','rdi','r12','r14','rsi','r13','r15','rbp'],
        opaqueEqualityHashOrActualRegistryStateProved=False)


def bind_dictionary_context(context,type_definition):
    dictionary='System.Collections.Concurrent.ConcurrentDictionary`2';entries=context['entries']
    need('bounded-owned-dictionary-context',context['definition']==type_definition and context['count']==len(entries)>42
        and type(type_definition)is int)
    insertion,lookup,node,constructor=[entries[i]for i in(15,29,41,42)]
    for row,name in((insertion,'TryAddInternal'),(lookup,'TryGetValueInternal')):
        need('exact-dictionary-method-role-'+name,row['kind']==3 and row['typeName']==dictionary
            and row['methodName']==name and row['methodArguments']==[])
    arguments=insertion['classArguments'];need('exact-two-dictionary-variables',len(arguments)==2)
    for ordinal,argument in enumerate(arguments):
        owner=argument.get('parameterOwner',{})
        need('reciprocal-dictionary-VAR'+str(ordinal),bytes.fromhex(argument['rawHex'])[10:12]==b'\x13\x00'
            and owner.get('typeIndex')==type_definition and owner.get('ordinal')==ordinal)
    need('lookup-uses-same-owned-VAR-pair',lookup['classArguments']==arguments)
    need('exact-key-comparer-context',entries[12]['kind']==2
        and entries[12]['type']['definition']['name']=='System.Collections.Generic.IEqualityComparer`1'
        and entries[12]['type']['classArguments']==arguments[:1])
    need('exact-owned-node-class-and-constructor',node['kind']==2
        and node['type']['definition']['name']==dictionary+'+Node'and node['type']['classArguments']==arguments
        and bytes.fromhex(node['type']['rawHex'])[10:12]==b'\x15\x00'
        and constructor['kind']==3 and constructor['typeName']==dictionary+'+Node'
        and constructor['methodName']=='.ctor'and constructor['classArguments']==arguments and constructor['methodArguments']==[])
    return dict(dictionaryDefinition=type_definition,keyVariable=arguments[0],valueVariable=arguments[1],
        insertionMethodDefinition=insertion['methodSpec'][0],inlinedLookupMethodDefinition=lookup['methodSpec'][0],
        nodeConstructorMethodDefinition=constructor['methodSpec'][0],exactOwnContextRolesProved=True)


def derive(image,pins,*,enum_types):
    """Re-derive nominal source and actual provider registry roundtrip together."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_nominal_registration_paths import derive as nominal_source,source_rows,_full
    from scripts.game_data.il2cpp.enum_method_rgctx_paths import provider_program
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=nominal_source(image,pins,enum_types=enum_types)
    ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;families={};bodies={}
    def full(role,target):
        body=owned(image,target);rows=source_rows([r for a,raw in body['regions']for r in decode(image.mapper,raw,a)])
        families[role]=dict(windows=body['windows'],program=ordinary_program(body['regions'],rows,target));bodies[role]=body
        return body
    registration=prior['proof']['registerPrograms'][0];insert=full('insertion',registration['actualInsertion'])
    insertion=insert_empty_program(insert['regions'],insert['pointer'])
    site=next(at for at,raw in registration['selectedBytes']if raw=='488b2d')
    setter=derive_typed_usage_context(image,site-base,label=LABEL)
    dictionary='System.Collections.Concurrent.ConcurrentDictionary`2';arguments=['System.Type','MemoryPack.IMemoryPackFormatter']
    need('actual-closed-registry-setter',setter['tag']==6 and setter['typeName']==dictionary
        and setter['methodName']=='set_Item'and setter['classArguments']==arguments and setter['methodArguments']==[])
    symbols=ContextSymbols(image);dictionary_type=ctx.index.types[dictionary]
    static_context=symbols.context(dictionary_type.index,is_method=False);binding=bind_dictionary_context(static_context,dictionary_type.index)
    methods=[m for m in md.methods_for(ctx.index.types['MemoryPack.MemoryPackFormatterProvider'])
        if md.string(m.name_index)=='GetFormatter'and m.generic_container_index>=0 and not md.parameters_for(m)]
    need('one-own-generic-GetFormatter',len(methods)==1);method,=methods
    selected=GenericEntries(image).resolve(method.index,[],['System.Int32Enum'])
    generic=full('genericProvider',selected['pointer']);provider=provider_program(generic['regions'],generic['pointer'])
    public_body=owned(image,provider['actualBackend']);public=public_program(public_body['regions'],public_body['pointer'])
    _,_,families['actualPublicProvider']=_full(image,public_body['pointer'],tail_targets=(public['actualBackendTail'],))
    actual=full('actualInlineBackend',public['actualBackendTail']);backend=actual_backend_hit_program(actual['regions'],actual['pointer'])
    request=derive_typed_usage_context(image,backend['lookupMethodUsageInstruction']-base,label=LABEL)
    need('actual-closed-inline-lookup-context',request['tag']==6 and request['typeName']==dictionary
        and request['methodName']=='TryGetValue'and request['classArguments']==arguments and request['methodArguments']==[])
    need('same-exact-registry-class-and-input-type',registration['providerClassCell']==public['providerClassCell']==backend['providerClassCell']
        and provider['actualProviderClassCell']==backend['providerClassCell'])
    need('same-actual-registry-hash-and-context-helpers',registration['actualHashHelper']==backend['actualHashHelper']
        and registration['actualClassContextSlotResolver']==backend['actualContextSlotResolver']==insertion['actualSlotResolver'])
    need('same-disabled-selected-collector',insertion['collectorFlagCell']==backend['collectorFlagCell'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-conditional-registry-source',nativeInputs=pins,
        proof=dict(nominalRegistrationSource=prior,completeOwnedFamilies=families,selectedEmptyInsertion=insertion,
            actualClosedRegistrySetter=setter,dictionaryStaticContext=static_context,dictionaryContextBinding=binding,
            registeredGenericProvider=selected,selectedGenericProvider=provider,actualPublicProvider=public,
            actualInlineBackend=backend,actualClosedLookup=request),
        sameNominalTypeAndFormatterConditionalRegistryRoundtripProved=True,actualInitializedRegistryStateProved=False,
        actualNominalCallbackOrMethodInfoSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own nominal allocation/ctor/Register requests; actual registry setter/insertion, generic provider/public clone/actual inline lookup full byte partitions and ordinary CFG/frame, and selected unchanged Type/formatter source transfers.',
            conditional=__doc__+' First-empty selected bucket, coherent initialized closed contexts, normal compatible allocation/lock/cleanup/hash/equality/cast effects, stable disjoint registry and collector disabled; no intervening replacement.',
            structuralOnly='Actual dictionary node key/value/hash/link stores; source-defined ordinary entry distinct from unentered finally candidates.',
            unresolved=['registry execution/order/state and helper alias effects','actual nominal class slot5 callback and MethodInfo binding',
                'other insertion/update/collision/resize/collector paths','concrete enum/list/parent/EOF'])),default=_json_set))
