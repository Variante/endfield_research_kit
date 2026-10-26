"""Actual provider reflection arguments and ordinary virtual-pair transfers.

The selected provider path passes its actual map lookup result and the
unchanged requested Type's generic-argument array to virtual MakeGenericType
slot168. The complete helper restores its frame and tail-calls the receiver
class's actual callback/MethodInfo pair with that same receiver and array.
Its nine-byte class-preparation tail loads the class's independently proved
self field and transfers to the complete current class-initialization body.
That body's selected ordinary direct-method iteration stores its actual
MethodInfo and that MethodInfo's direct target in the same two pair words.
The actual per-slot metadata accessor uses the same selected metadata base/
header cells and vtable table section. Both named metadata slot declarations
are checked independently; no live slot is inferred from the names.

Conditions include coherent initialized nominal receiver/class/metadata and
dictionary results, selected direct nonnull method entries, compatible normal
callee effects, stable class counters and disjoint storage. Other class setup
branches are fully partitioned/CFG-checked but their semantic effects are not
admitted. The encoded method resolver, actual initialized MethodInfo/RGCTX,
reflection construction result and concrete enum callback remain separate.
No enum element width, list grammar, parent or whole-owner admission follows.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-reflection-dispatch-paths.v1'
LABEL='enumReflectionDispatchPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def provider_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec30')
    flag=g.relative('803d')+1;g.take('00','488bfa','488bd9');g.branch('75',True,1)
    g.take('48c744244000000000','4885db');g.branch('74',False,1)
    g.take('b934000000','488bd3');is_generic=g.relative('e8');g.take('84c0');g.branch('74',False,1)
    g.take('b93d000000','488bd3');definition=g.relative('e8');g.take('4885ff');g.branch('74',False,1)
    g.take('488d4c2440','4c8bc8','4c8bc7','48894c2420');lookup=g.relative('e8')
    g.take('84c0');g.branch('74',False,1)
    g.take('488b7c2440','b93f000000','488bd3');arguments=g.relative('e8')
    g.take('4885ff');g.branch('74',False,1)
    g.take('b9a8000000','4c8bc0','488bd7');call=g.at;make=g.relative('e8')
    g.take('488b5c2448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,initializedUsageFlagCell=flag,initializedUsageFlagMustBeNonzero=True,
        actualCalls=dict(isGenericType=is_generic,genericDefinition=definition,mapLookup=lookup,
            genericArguments=arguments,makeGenericType=make),makeGenericTypeCall=call,
        virtualSlots=dict(isGenericType=52,genericDefinition=61,genericArguments=63,makeGenericType=168),
        mapLookupArguments=dict(r8='unchanged incoming map',r9='actual generic-definition Type result',
            fifthArgument='address of owned stack+64 Type output'),
        makeGenericTypeArguments=dict(ecx=168,rdx='actual map output Type',r8='requested Type generic-arguments result'),
        requestedTypeNonnullAndGenericRequired=True,mapNonnullAndLookupSuccessRequired=True,
        mappedFormatterTypeNonnullRequired=True,actualConstructedTypeResultReturnedUnchanged=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True,
        reflectionAndDictionaryResultIdentityProved=False)


def make_generic_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488b0a','498bd8','488bfa')
    prepare=g.relative('e8');g.take('4c8b07','488bd3','488bcf','498b80c00b0000','4d8b80c80b0000',
        '488b5c2430','4883c420','5f','48ffe0')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,classPreparationTarget=prepare,
        incomingReceiver='rdx',incomingTypeArray='r8',classPointerOffset=0,virtualSlot=168,
        callbackPairOffset=3008,methodInfoPairOffset=3016,pairBase=320,pairStride=16,
        outgoingArguments=dict(rcx='unchanged incoming Type receiver',rdx='unchanged incoming Type[]',
            r8='fresh actual receiver class slot168 MethodInfo'),
        actualTailRegister='rax',entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],
        wholeSelectedHelperProgramProved=True,actualTargetIdentityProved=False)


def preparation_program(regions,entry,*,self_offset):
    need('same-source-proved-self-offset',type(self_offset)is int and self_offset==120)
    g=BytesPath(regions,entry);g.take('488b4978');target=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,classSelfOffset=self_offset,
        classInitializationTarget=target,sameClassRequiredAtSelfField=True,
        entryRspAndAllOtherArgumentsUnchanged=True,fullUnwindExtentProved=False)


def ordinary_iteration_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0fb7d7','488bcb');lookup=g.relative('e8')
    g.take('488bd0','0fb7cf','4803c9','488984cb48010000','4885c0');g.branch('74',False,1)
    g.take('4883780800');g.branch('74',False,1)
    g.take('f6405402');g.branch('74',True,1)
    g.take('4c8b4008','0fb7c7','4883c014','4803c0','4c8904c3');g.jump('eb',1)
    increment=g.at;g.take('66ffc7','663bbb2c010000');back=g.relative('0f82')
    need('same-ordinary-virtual-slot-loop',back==entry)
    return dict(selectedBytes=g.seen,entry=entry,methodLookupTarget=lookup,slotRegister='di',slotBits=16,
        classRegister='rbx',methodInfoRegister='rax',methodInfoStoreBase=328,callbackStoreBase=320,pairStride=16,
        actualMethodInfoStoredUnchanged=True,directTargetMethodOffset=8,directTargetStoredUnchanged=True,
        selectedMethodNonnullAndDirectTargetNonnullRequired=True,methodFlagOffset=84,methodFlagMask=2,
        selectedMethodFlagMaskMustBeZero=True,methodCountClassOffset=300,
        incrementInstruction=increment,slotStep=1,backedge=back,
        counterStartsAtZeroAndStableWordCountRequired=True,opaqueHelperAliasEffectsProved=False)


def metadata_slot_program(regions,entry):
    g=BytesPath(regions,entry);g.take('488b4168');metadata=g.relative('488b0d')
    g.take('448b4038');header=g.relative('488b05');g.take('4403c2','48639090000000','4803ca','428b0c81')
    resolve=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,metadataBaseCell=metadata,metadataHeaderCell=header,
        classMetadataRecordOffset=104,vtableStartRecordOffset=56,vtableSectionHeaderOffset=144,
        vtableWordBytes=4,slotSource='incoming zero-extended unsigned slot EDX',
        resolverTarget=resolve,encodedMethodArgument='unchanged actual metadata vtable DWORD in ECX',
        boundedValidClassAndSlotRequired=True,entryRspUnchanged=True,fullUnwindExtentProved=False)


def decode(mapper,data,entry):
    from scripts.game_data.il2cpp.string_source_instructions import decode_al_immediate_compare,decode_memory_register_add
    from scripts.game_data.il2cpp.enum_plain_method_descriptor_paths import decode as inherited
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_al_immediate_compare(raw,offset,at)or decode_memory_register_add(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return inherited(Fallback(),data,entry)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_runtime_type_receiver_paths import derive as receiver_source
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.protocol import load_metadata_helper
    from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.levelscript_two_routes_native import _window
    _publication_gate(image,pins);prior=receiver_source(image,pins,**arguments);ctx=NativeReferenceContext(image);md=image.metadata
    methods=[m for m in md.methods_for(ctx.index.types['MemoryPack.MemoryPackFormatterProvider'])
        if md.string(m.name_index)=='TryCreateGenericFormatterType'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['System.Type','System.Collections.Generic.IDictionary`2<System.Type,System.Type>']]
    need('one-current-exact-provider-method',len(methods)==1);method,=methods
    source=owned(image,image.method_pointer_va(method));provider=provider_program(source['regions'],source['pointer'])
    def graph(body):
        rows=[]
        for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
        rows.sort(key=lambda r:int(r['va'],16));cfg,padding=complete_program(body['regions'],rows,body['pointer'])
        return cfg,padding
    provider_graph,provider_padding=graph(source)
    helper=owned(image,provider['actualCalls']['makeGenericType']);make=make_generic_program(helper['regions'],helper['pointer'])
    check_byte_partition([(a,a+len(raw))for a,raw in helper['regions']],
        [(a,a+len(bytes.fromhex(raw)),'instruction')for a,raw in make['selectedBytes']],LABEL+'.complete-helper')
    prepare_entry=make['classPreparationTarget'];prepare_raw=image.pe.bytes_at_va(prepare_entry,9)
    prepare=preparation_program([(prepare_entry,prepare_raw)],prepare_entry,
        self_offset=prior['proof']['classConstructorSelf']['classSelfOffset'])
    initialization=owned(image,prepare['classInitializationTarget']);class_graph,class_padding=graph(initialization)
    iteration=ordinary_iteration_program(initialization['regions'],unique(initialization['regions'],bytes.fromhex('0fb7d7488bcbe8')))
    lookup_entry=iteration['methodLookupTarget'];lookup_raw=image.pe.bytes_at_va(lookup_entry,44)
    lookup=metadata_slot_program([(lookup_entry,lookup_raw)],lookup_entry)
    selected=prior['proof']['nameAndInternerSource']['proof']['selectedWarmLookup']
    need('same-independent-current-metadata-cells',all(lookup[k]==selected[k]for k in('metadataBaseCell','metadataHeaderCell')))
    section=md.sections['vtableMethods'];header_offset=8+list(md.sections).index('vtableMethods')*8
    need('same-actual-vtable-section-header',header_offset==lookup['vtableSectionHeaderOffset']
        and struct.unpack_from('<i',md.buf,header_offset)[0]==section.offset and section.size%4==0)
    catalog=load_metadata_helper(METADATA_HELPER_PATH);slot_methods=[]
    for name in('System.Type','System.RuntimeType'):
        td=ctx.index.types[name];candidates=[m for m in md.methods_for(td)if md.string(m.name_index)=='MakeGenericType'
            and m.slot==make['virtualSlot']and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['System.Type[]']]
        need('one-actual-virtual-MakeGenericType-definition',len(candidates)==1);selected_method,=candidates
        need('same-ordinary-virtual-signature',not selected_method.flags&0x10 and selected_method.flags&0x40
            and ctx.type_name(selected_method.return_type)=='System.Type')
        _vtable(image,td.index,make['virtualSlot'],selected_method.index,LABEL)
        # Check the selected stored type record's exact parser column as well
        # as the named metadata model. No class-record offset is inferred.
        types=md.sections['typeDefinitions'];start=types.offset+td.index*md.type_record_size
        prefix=catalog.parse_type_reference_prefix(md.buf,start,md.type_record_size)
        tail=catalog.parse_type_layout_tail(md.buf,prefix[-1],md.type_record_size)
        need('actual-vtable-start-column',prefix[-1]-start+4+6*4==lookup['vtableStartRecordOffset']
            and struct.unpack_from('<i',md.buf,start+lookup['vtableStartRecordOffset'])[0]==td.vtable_start==tail[1][6])
        slot_methods.append(dict(method=[selected_method.index,name,'MakeGenericType'],slot=selected_method.slot,
            typeDefinition=td.index,vtableStart=td.vtable_start,vtableCount=td.vtable_count,
            rawVtableWord=struct.unpack_from('<I',md.buf,section.offset+(td.vtable_start+selected_method.slot)*4)[0]))
    chain=[];name='System.RuntimeType'
    for _ in range(16):
        name=ctx.parent(name);chain.append(name)
        if name=='System.Type':break
    validate_reference_ancestor_chain(ctx,'System.RuntimeType',chain,'System.Type')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(receiverSource=prior,providerMethod=[method.index,'MemoryPack.MemoryPackFormatterProvider','TryCreateGenericFormatterType'],
            providerWindows=source['windows'],providerCfg=provider_graph,providerPadding=provider_padding,selectedProviderPath=provider,
            helperWindows=helper['windows'],makeGenericType=make,classPreparation=prepare,
            classPreparationWindow=_window(image,prepare_entry,prepare['end'],'Exact observed nine-byte self-load/E9 tail; no unwind extent claim'),
            classInitializationWindows=initialization['windows'],classInitializationCfg=class_graph,classInitializationPadding=class_padding,
            ordinaryMethodIteration=iteration,metadataSlot=lookup,
            metadataSlotWindow=_window(image,lookup_entry,lookup['end'],'Exact observed metadata-slot accessor and E9; no unwind extent claim'),
            selectedSlotMethods=slot_methods,runtimeTypeAncestorChain=chain),
        exactProviderAndVirtualPairTransfersProved=True,initializedReceiverVirtualSlotIdentityProved=False,
        actualNominalClosedMethodInfoAndRgctxProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete selected provider/helper/class-initialization source partitions and normal CFG/frames; actual receiver/array/MethodInfo tail, ordinary pair stores and metadata slot accessor/definitions.',
            conditional=__doc__,structuralOnly='Reflection call arguments and ordinary class virtual-pair representation.',
            unresolved=['initialized receiver/class identity and metadata resolver semantics','actual nominal MethodInfo/RGCTX and reflection construction return',
                'dictionary/provider/alias/history effects','concrete enum formatter callback','wire/parent/EOF']))))
