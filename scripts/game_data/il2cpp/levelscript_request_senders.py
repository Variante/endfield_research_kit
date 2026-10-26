"""Selected sender receiver/message references reach the current dispose API."""
import struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
from scripts.game_data.il2cpp.consumer_entry_program import read_ordinary_consumer_entry
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.context import usage_method_spec
from scripts.game_data.il2cpp.memory_moves import decode_memory_move


def require_reference_parameter(context,type_index):
    image=context.image;raw=image.pe.bytes_at_va(context.type_pointer(type_index),16)
    if len(raw)!=16 or raw[10] not in (0x12,0x15):raise ValueError('requestSender.reference-parameter-kind')
    context.require_ordinary_kind(type_index,raw[10]);definition=raw
    if raw[10]==0x15:
        # Parameter attributes include Optional; they are not field Static flags.
        carrier=int.from_bytes(raw[:8],'little');definition=image.pe.bytes_at_va(image.pe.u64_at_va(carrier),16)
        if len(definition)!=16 or definition[10]!=0x12 or definition[11]&0x7f:raise ValueError('requestSender.reference-generic-definition')
    index=int.from_bytes(definition[:8],'little');metadata=image.metadata
    if not 0<=index<len(metadata.types):raise ValueError('requestSender.reference-definition-index')
    owner=metadata.types[index];name=metadata.type_full_name(owner)
    if ((raw[10]==0x15)!=(owner.generic_container_index>=0) or context.is_value_type(name)
            or len(image.named_type_definitions.get(name,()))!=1):raise ValueError('requestSender.unique-reference-definition')


def factory_reference_context(context,generic,program,call,allocator,packet):
    image=context.image;metadata=image.metadata;rows=program['rows'];label='requestSender.factoryReference'
    owner=metadata.types[allocator.declaring_type]
    if (not allocator.flags&0x10 or allocator.generic_container_index<0 or owner.generic_container_index>=0
            or context.is_value_type(metadata.type_full_name(owner)) or list(metadata.parameters_for(allocator))):raise ValueError(label+'.static-generic-zero-parameter-reference-owner')
    section=metadata.sections['genericContainers'];at=section.offset+allocator.generic_container_index*16
    if not section.offset<=at<=section.offset+section.size-16:raise ValueError(label+'.generic-container-range')
    declaration,count,is_method,parameter=struct.unpack_from('<iiii',metadata.buf,at)
    returned=image.pe.bytes_at_va(context.type_pointer(allocator.return_type),16)
    if ((declaration,count,is_method)!=(allocator.index,1,1) or len(returned)!=16 or returned[10]!=0x1e
            or returned[11]&0x7f or int.from_bytes(returned[:8],'little')!=parameter):raise ValueError(label+'.returns-sole-method-parameter')
    position=rows.index(call)
    if position<1:raise ValueError(label+'.context-load')
    load=rows[position-1];raw=bytes.fromhex(load['bytes']);load_at=int(load['va'],16);call_at=int(call['va'],16)
    decoded=decode_memory_move(raw,0,load_at)
    if decoded is None or decoded[1]!=len(raw):raise ValueError(label+'.context-memory-load')
    op=decoded[0]['memoryOperation'];address=op['address']
    if ((op['direction'],op['register'],op['memoryBytes'],op['registerBits'],address.get('ripRelative'))!=('load','rcx',8,64,True)
            or {source for source,targets in program['control']['edges'].items() if call_at in targets}!={load_at}):raise ValueError(label+'.unbypassed-static-methodinfo-load')
    reg=image.registration;table=int(reg['methodSpecs'],16);cell=address['absoluteAddress']
    selected=usage_method_spec(image.pe.bytes_at_va(cell,8),image.pe.bytes_at_va(table,reg['methodSpecsCount']*12),len(metadata.methods),reg['genericInstsCount'],
        source=str(image.gameassembly),usage_offset=cell,records_offset=table)
    if selected['definition']!=allocator.index or selected['classInstantiationIndex']!=-1:raise ValueError(label+'.selected-generic-declaration')
    args,proof=generic.arguments(selected['methodInstantiationIndex'])
    if args!=[packet]:raise ValueError(label+'.selected-packet-argument')
    argument=bytes.fromhex(proof['arguments'][0]['raw_type_record_hex']);definition=int.from_bytes(argument[:8],'little')
    if (len(argument)!=16 or argument[10]!=0x12 or argument[11]&0x7f or len(image.named_type_definitions.get(packet,()))!=1
            or not 0<=definition<len(metadata.types) or metadata.type_full_name(metadata.types[definition])!=packet
            or context.is_value_type(packet)):raise ValueError(label+'.ordinary-concrete-reference-argument')
    packet_type=metadata.types[definition];interfaces=metadata.sections['interfaces'];start=interfaces.offset+packet_type.interfaces_start*4
    if not 0<packet_type.interfaces_count<=64 or not interfaces.offset<=start<=interfaces.offset+interfaces.size-packet_type.interfaces_count*4:
        raise ValueError(label+'.packet-interface-range')
    matches=image.named_type_definitions.get('ProtoBuf.IExtensible',())
    if len(matches)!=1:raise ValueError(label+'.unique-message-interface')
    interface_index=matches[0].index;implemented=[]
    for index in struct.unpack_from('<'+'i'*packet_type.interfaces_count,metadata.buf,start):
        raw=image.pe.bytes_at_va(context.type_pointer(index),16)
        if len(raw)==16 and raw[10]==0x12 and not raw[11]&0x7f and int.from_bytes(raw[:8],'little')==interface_index:implemented.append(index)
    if len(implemented)!=1:raise ValueError(label+'.direct-message-interface')
    canonical=generic.resolve(allocator.index,[],['object']);target=control_transfer(call)['target']
    arg=bytes.fromhex(canonical['methodInstantiation']['arguments'][0]['raw_type_record_hex'])
    if (canonical['pointer']!=target or canonical['registration']['indices'][-1]!=-1 or len(arg)!=16 or arg[10]!=0x1c or arg[11]&0x7f):
        raise ValueError(label+'.canonical-object-entry-and-reference-abi')
    return dict(selectedMethodSpec=selected,selectedPacketArgument=proof,registeredCanonicalObjectEntry=canonical,messageInterfaceType=interface_index,
        evidenceBoundary='conditional',condition='Compiled concrete reference MethodSpec and same-definition ordinary Object-shared AOT entry. Both return representations are reference pointers; instantiated field layout, live MethodInfo selection and allocation success remain unproved.')


def prove_levelscript_request_senders(image):
    index=image.body_index;metadata=image.metadata;context=NativeReferenceContext(image);out={};label='levelscriptRequestSenders'
    owner='Beyond.Gameplay.GameplayNetwork';base='Beyond.Gameplay.BaseNetworkSystem';target=index.body(base,'SendMsgAndDispose')
    validate_reference_ancestor_chain(context,owner,[base],base)
    def declaration(body):
        aliases=[r for r in index.names_by_pointer[body.pointer] if r['type']+'.'+r['method']==body.symbol]
        if len(aliases)!=1:raise ValueError(label+'.unique-declaration:'+body.symbol)
        method=metadata.methods[aliases[0]['methodIndex']];td=metadata.types[method.declaring_type]
        if (method.flags&0x10 or method.generic_container_index>=0 or td.generic_container_index>=0
                or context.is_value_type(metadata.type_full_name(td)) or image.method_pointer_va(method)!=body.pointer
                or context.type_name(method.return_type)!='void'):raise ValueError(label+'.ordinary-instance-void:'+body.symbol)
        context.require_ordinary_kind(method.return_type,1);return method
    target_method=declaration(target);params=list(metadata.parameters_for(target_method))
    if len(params)!=2 or context.type_name(params[0].type_index)!='ProtoBuf.IExtensible':raise ValueError(label+'.message-interface-parameter')
    context.require_ordinary_kind(params[0].type_index,0x12);require_reference_parameter(context,params[0].type_index)
    require_reference_parameter(context,params[1].type_index)
    for role,name in [('active','SendLevelScriptSetActive'),('start','SendLevelScriptSetStart')]:
        body=index.body(owner,name,parameters=['System.UInt64','System.Int32','System.Boolean']);method=declaration(body)
        parameters=list(metadata.parameters_for(method))
        if len(parameters)!=3:raise ValueError(label+'.sender-parameter-count')
        for parameter,wanted,kind in zip(parameters,('ulong','int','bool'),(0x0b,8,2)):
            if context.type_name(parameter.type_index)!=wanted:raise ValueError(label+'.sender-parameter-type')
            context.require_ordinary_kind(parameter.type_index,kind)
        program=read_ordinary_consumer_entry(image,body)
        calls=[row for row in program['rows'] if control_transfer(row)['kind']=='call']
        allocations=[row for row in calls if 'Proto.ProtoBufFactory.Allocate' in index.names_of(control_transfer(row)['target'])]
        sends=[row for row in calls if control_transfer(row)['target']==target.pointer]
        if len(allocations)!=1 or len(sends)!=1:raise ValueError(label+'.unique-allocation-and-send:'+role)
        allocation=allocations[0];send=sends[0]
        aliases=[r for r in index.names_by_pointer[control_transfer(allocation)['target']] if r['type']+'.'+r['method']=='Proto.ProtoBufFactory.Allocate']
        if len(aliases)!=1:raise ValueError(label+'.unique-allocation-declaration')
        allocator=metadata.methods[aliases[0]['methodIndex']]
        factory=factory_reference_context(context,GenericEntries(image),program,allocation,allocator,
            'Proto.CS_SCENE_SET_LEVEL_SCRIPT_'+role.upper())
        refs=check_reference_origins(program['rows'],entry=body.pointer,owned_ranges=program['ranges'],incoming_registers={'rcx':'this'},
            incoming_stack_slots={},selected_call_returns={int(allocation['va'],16):'allocation-result'})
        state=refs['registerOrigins'][int(send['va'],16)]
        if state['rcx']!=['this'] or state['rdx']!=['allocation-result']:raise ValueError(label+'.same-receiver-and-allocation:'+role)
        out[role]=dict(status='validated',sourceMethod=body.symbol,targetMethod=target.symbol,callOffset=int(send['va'],16)-body.pointer,factoryReferenceCall=factory,
            ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,
                ordinaryInstructions=len(program['rows']),unenteredOwnedByteCandidates=program['unenteredOwnedByteCandidates'],exceptionalOrResumptionPathsProved=False),
            incomingReceiverAndFactoryReturnBitsProved=True,evidenceBoundary='conditional',
            condition='Ordinary Win64 callees and typed incoming receiver; the allocation return bits reach the selected send API. Concrete packet/context identity, callee effects, IFix behavior and request success are separate.')
    return out
