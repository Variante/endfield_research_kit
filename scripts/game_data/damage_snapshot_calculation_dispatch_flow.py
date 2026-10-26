"""Actual callback forwarding and named Definite-entry equality selection.

Runtime class/vtable interpretation is conditional, separately from the raw
carrier reads, actual pointer comparison and complete selected normal return.
"""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_dispatch_rows(parts,function_offset,info_offset,definite_pointer):
    _require(len(parts)==3,'calculation-dispatch-parts',3,len(parts))
    _require(all(type(v) is int and 0<=v<2**31 for v in (function_offset,info_offset)),
             'calculation-dispatch-carrier-offsets','bounded positive disp32',[function_offset,info_offset])
    dword=lambda n:n.to_bytes(4,'little').hex()
    forms=[['48895c2408','4889742410','57','4883ec70','488b0a','498bf9','0f29742460',
            '498bf0','0f297c2450','488bda','opaque-call','488b03',
            '4c8b90'+dword(function_offset),'488b88'+dword(info_offset),'definite-address','4c3bd0','unequal-selected'],
           ['488b8424c0000000','4c8bc7','4c8b8c24a0000000','488bd6','48894c2440','488bcb','4889442438',
            '488b8424b8000000','4889442430','488b8424b0000000','4889442428',
            '488b8424a8000000','4889442420','41ffd2','66480f6ec0','footer-jump'],
           ['0f28742460','4c8d5c2470','498b5b10','66480f7ec0','498b7318','0f287c2450','498be3','5f','c3']]
    ranges=[];edges={};opaque=None;comparison=None
    for rows,expected in zip(parts,forms):
        _require(len(rows)==len(expected),'calculation-dispatch-row-count',len(expected),len(rows));start=int(rows[0]['va'],16);at=start
        for row,form in zip(rows,expected):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'calculation-dispatch-contiguity',hex(at),row['va'])
            if form=='opaque-call':
                _require(len(raw)==5 and raw[0]==0xe8,'calculation-dispatch-opaque-call','direct CALL',raw.hex())
                opaque=relative_branch_target(raw,at,source='calculationDispatch')
            elif form=='definite-address':
                _require(len(raw)==7 and raw[:3]==bytes.fromhex('488d05'),'calculation-dispatch-comparison-lea','complete RIP LEA RAX',raw.hex())
                comparison=at+7+int.from_bytes(raw[3:],'little',signed=True)
                _require(comparison==definite_pointer,'calculation-dispatch-named-comparison',definite_pointer,comparison)
            elif form in ('unequal-selected','footer-jump'):
                opcode=0x75 if form=='unequal-selected' else 0xeb
                _require(len(raw)==2 and raw[0]==opcode,'calculation-dispatch-selected-edge',hex(opcode),raw.hex())
                edges[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
            else:_require(raw==bytes.fromhex(form),'calculation-dispatch-instruction',form,raw.hex())
            at+=len(raw)
        ranges.append((start,at))
    _require(edges['unequal-selected']==ranges[1][0] and edges['footer-jump']==ranges[2][0],
             'calculation-dispatch-selected-links',[r[0] for r in ranges[1:]],[edges['unequal-selected'],edges['footer-jump']])
    _require(all(b<=c or d<=a for n,(a,b) in enumerate(ranges) for c,d in ranges[n+1:]),
             'calculation-dispatch-separated-spans','nonoverlapping selected spans',ranges)
    return {'selectedSpans':[[hex(a),hex(b)] for a,b in ranges],'selectedByteCount':sum(b-a for a,b in ranges),
            'opaquePreDispatchCall':hex(opaque),'comparisonEntry':hex(comparison),'actualFunctionCarrierDisplacement':function_offset,
            'actualInfoCarrierDisplacement':info_offset,'actualIndirectCall':'CALL R10 loaded after opaque call',
            'helperReceiverInput':'RDX -> RBX; receiver first qword is read before and again after opaque call',
            'normalCallbackReturnTransfer':'RAX.low64 -> XMM0.low64 -> full common restoring RET -> RAX.low64',
            'frameDeltaBytes':120,'normalRetStackDeltaBytes':8,'runtimeSubtypeObserved':False,'actualCallbackNamed':False,
            'equalComparisonInlinePathProved':False,'managedHelperIdentityProved':False}


def check_caller_rows(rows,unit_offset,program,helper_pointer,blackboard_pointer):
    _require(type(unit_offset) is int and 0<=unit_offset<128,'calculation-dispatch-unit-offset','typed positive disp8',unit_offset)
    byte=lambda n:bytes([n]).hex();dword=lambda n:n.to_bytes(4,'little').hex()
    _require(all(type(program[k]) is int and 0<=program[k]<128 for k in ('anonymousContextCarrierDisp8','anonymousArrayOneDisp8'))
             and type(program['anonymousArrayTwoDisp32']) is int and 0<=program['anonymousArrayTwoDisp32']<2**31,
             'calculation-dispatch-anonymous-caller-offsets','bounded actual anonymous operands',program)
    forms=['488b5b'+byte(unit_offset),'33d2','488bce','blackboard-call',
           '488b4e'+byte(program['anonymousContextCarrierDisp8']),'4c8be0','4885c9','context-null-excluded','opaque-context-call',
           '4c8b47'+byte(program['anonymousArrayOneDisp8']),'4d8bce','488b8f'+dword(program['anonymousArrayTwoDisp32']),
           '488bd3','4c897c2440','48894c2438','4c89442430','4c8bc5','4889442428','4c89642420','helper-call']
    _require(len(rows)==len(forms),'calculation-dispatch-caller-count',len(forms),len(rows));start=int(rows[0]['va'],16);at=start;calls={};excluded=None
    for row,form in zip(rows,forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'calculation-dispatch-caller-contiguity',hex(at),row['va'])
        if form.endswith('-call'):
            _require(len(raw)==5 and raw[0]==0xe8,'calculation-dispatch-caller-call','direct CALL',raw.hex())
            target=relative_branch_target(raw,at,source='calculationDispatchCaller');calls[form]=hex(target)
            if form=='helper-call':_require(target==helper_pointer,'calculation-dispatch-caller-target',helper_pointer,target)
            if form=='blackboard-call':_require(target==blackboard_pointer,'calculation-dispatch-caller-blackboard',blackboard_pointer,target)
        elif form=='context-null-excluded':
            _require(len(raw)==2 and raw[0]==0x74,'calculation-dispatch-context-edge','JE short',raw.hex());excluded=at+2+int.from_bytes(raw[1:],'little',signed=True)
        else:_require(raw==bytes.fromhex(form),'calculation-dispatch-caller-instruction',form,raw.hex())
        at+=len(raw)
    _require(not start<=excluded<at,'calculation-dispatch-context-excluded','outside complete caller request span',excluded)
    return {'callerRequestSpan':[hex(start),hex(at)],'callerCalls':calls,
            'calleeReceiverRegister':'RDX from retained typed atkCalculation field; RCX entry is not receiver',
            'callerUnitReceiverOriginProved':False,'opaqueContextReturnTypeProved':False,
            'callerPackArrayLayoutProved':False}


def check_calculation_dispatch(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_field
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','calculation-dispatch-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index)
    owner,method=consumer_proof['symbol'].rsplit('.',1);reference=index.body(owner,method)
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    result_records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(reference.symbol,reference.pointer)]
    declarations=[];slots=[]
    for typ in [spec['baseType'],spec['comparisonType']]:
        td=index.types[typ];named=[m for m in index.metadata.methods_for(td) if index.metadata.string(m.name_index)==spec['method']]
        _require(len(named)==1,'calculation-dispatch-method-definition','unique named Evaluate',typ)
        m=named[0]
        _require(not m.flags&0x10 and bool(m.flags&0x40) and m.slot!=0xffff and len(index.metadata.parameters_for(m))==7,
                 'calculation-dispatch-prototype','ordinary instance virtual seven arguments',[typ,m.flags,m.slot])
        _require(not selected.is_value_type(typ),'calculation-dispatch-reference-owner','named reference owner',typ)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'dispatch.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),result_records)
        for name,argtype in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,argtype,'dispatch.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'dispatch.'+name)
        slots.append(m.slot);declarations.append(typ+'.'+spec['method'])
    _require(slots[0]==slots[1],'calculation-dispatch-same-metadata-slot',slots[0],slots[1])
    _require(selected.parent(spec['comparisonType'])==spec['baseType'],'calculation-dispatch-comparison-parent',spec['baseType'],selected.parent(spec['comparisonType']))
    comparison=index.body(spec['comparisonType'],spec['method'])
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(comparison.pointer,comparison.symbol,name)==('register',register),
                 'calculation-dispatch-evaluate-register',[name,register],index.parameter_location(comparison.pointer,comparison.symbol,name))
    expected_stack={'context':40,'attackerOverrideAttributes':48,'defenderOverrideAttributes':56,'argsForServer':64}
    for name,offset in expected_stack.items():
        _require(index.parameter_location(comparison.pointer,comparison.symbol,name)==('stack',offset),
                 'calculation-dispatch-evaluate-stack',[name,offset],index.parameter_location(comparison.pointer,comparison.symbol,name))
    layout=spec['declaredRuntimeCarrierLayout'];base=layout['vtableBaseBytes'];stride=layout['entryStrideBytes'];info=layout['infoWithinEntryBytes']
    _require(all(type(v) is int for v in (base,stride,info)) and 0<=base<2**31 and base%8==0
             and 0<stride<2**31 and stride%8==0 and 8<=info and info+8<=stride and info%8==0 and 0<=slots[0]<65535,
             'calculation-dispatch-declared-layout','bounded declaration with distinct eight-byte entries',[base,stride,info])
    function_offset=base+stride*slots[0];info_offset=function_offset+info
    caller=index.body(spec['callerType'],spec['callerMethod'])
    _require(caller.symbol==consumer_proof['symbol'],'calculation-dispatch-fresh-caller',consumer_proof['symbol'],caller.symbol)
    candidates=[]
    for n,row in enumerate(caller.rows):
        raw=bytes.fromhex(row['bytes'])
        if len(raw)==5 and raw[0]==0xe8:
            target=relative_branch_target(raw,int(row['va'],16),source='calculationDispatchCandidate')
            if index.pe.bytes_at_va(target,18)==bytes.fromhex('48895c24084889742410574883ec70488b0a'):candidates.append((n,target))
    _require(len(candidates)==1,'calculation-dispatch-physical-candidate','unique actual call with complete helper prefix',candidates)
    call_index,helper=candidates[0]
    prefix=partition(index.pe.bytes_at_va(helper,71),helper,(5,5,1,4,3,3,5,3,5,3,5,3,7,7,7,3,2))
    edge=bytes.fromhex(prefix[-1]['bytes']);edge_va=int(prefix[-1]['va'],16)
    _require(edge[:1]==b'\x75','calculation-dispatch-unequal-edge','actual JNE',edge.hex())
    callback_va=edge_va+2+int.from_bytes(edge[1:],'little',signed=True)
    callback=partition(index.pe.bytes_at_va(callback_va,84),callback_va,(8,3,8,3,5,3,5,8,5,8,5,8,5,3,5,2))
    jump=bytes.fromhex(callback[-1]['bytes']);jump_va=int(callback[-1]['va'],16)
    _require(jump[:1]==b'\xeb','calculation-dispatch-footer-edge','actual JMP short',jump.hex())
    footer_va=jump_va+2+int.from_bytes(jump[1:],'little',signed=True)
    footer=partition(index.pe.bytes_at_va(footer_va,33),footer_va,(5,5,4,5,4,5,3,1,1))
    proof=check_dispatch_rows([prefix,callback,footer],function_offset,info_offset,comparison.pointer)
    _require(index.extents.get(helper)==callback_va+84,'calculation-dispatch-full-physical-extent','actual complete helper pdata extent ends after callback resume JMP',index.extents.get(helper))
    ranges=check_physical_coverage(index.extents,[prefix,callback,footer])
    _require(call_index>=19,'calculation-dispatch-caller-source-window','complete bounded caller request window',call_index)
    request=caller.rows[call_index-19:call_index+1]
    field_owner,field_type,field_offset=selected.field(spec['calculationField'])
    _require((field_owner,field_type)==(spec['unitType'],spec['baseType']),'calculation-dispatch-field-owner',[spec['unitType'],spec['baseType']],[field_owner,field_type])
    require_ordinary_field(selected,spec['calculationField'],spec['baseType'],'dispatch.receiverField')
    blackboard=relative_branch_target(bytes.fromhex(request[3]['bytes']),int(request[3]['va'],16),source='calculationDispatchBlackboard')
    _check_named_provider(index,blackboard,spec['blackboardGetter'],[],spec['referenceParameters']['blackboard'],is_static=False)
    getter_owner=spec['blackboardGetter'].rsplit('.',1)[0];current=spec['callerType'];chain=[]
    while current!=getter_owner and len(chain)<8:
        parent=selected.parent(current)
        _require(parent and parent not in chain,'calculation-dispatch-blackboard-ancestor',getter_owner,[current,parent])
        chain.append(parent);current=parent
    _require(current==getter_owner,'calculation-dispatch-blackboard-ancestor',getter_owner,chain)
    caller_proof=check_caller_rows(request,field_offset,spec['anonymousCallerProgram'],helper,blackboard)
    check_physical_coverage(index.extents,[request])
    for part in (prefix,callback,footer,request):
        raw=b''.join(bytes.fromhex(r['bytes']) for r in part);start=int(part[0]['va'],16)
        _require(index.pe.bytes_at_va(start,len(raw))==raw,'calculation-dispatch-raw-partition','complete selected raw byte partition',hex(start))
    return {**proof,**caller_proof,'symbol':caller.symbol,'claim':'calculationIndirectCallbackAndNamedDefiniteEntrySelection',
            'selectedPhysicalPdataRanges':ranges,'metadataVirtualSlot':slots[0],'ordinaryNamedPrototypeDeclarations':declarations,
            'declaredRuntimeCarrierLayout':layout,'runtimeLayoutObserved':False,'managedSelectedUnwindFamilyProved':False,
            'forwardedOrdinaryArguments':{'receiver':'helper RDX -> callback RCX','attacker':'helper R8 -> callback RDX','defender':'helper R9 -> callback R8',
                'blackboard':'helper entry stack40 -> callback R9','context':'helper entry stack48 -> callback entry stack40',
                'attackerOverrideAttributes':'helper entry stack56 -> callback entry stack48','defenderOverrideAttributes':'helper entry stack64 -> callback entry stack56',
                'argsForServer':'helper entry stack72 -> callback entry stack64','hiddenMethodInfo':'actual info carrier -> callback entry stack72'},
            'evidenceTiers':{'exact':'raw selected carrier reads, actual load displacements, argument transfers and full RET',
                'direct':'actual pointer comparison against selected named DefiniteValue.Evaluate entry; actual indirect CALL uses the loaded R10',
                'conditional':'Evaluate virtual-request interpretation requires declared runtime layout, compatible runtime class/prototype/parity/MethodInfo and normal noninterference'},
            'boundary':'Actual selected non-equal helper path rereads the receiver first-qword carrier after an opaque pre-dispatch call, loads two actual carrier slots, compares the function bits with the selected named DefiniteValue.Evaluate entry, forwards seven ordinary arguments plus hidden MethodInfo to CALL R10, and restores its frame/nonvolatile registers/SIMD before returning unchanged normal callback low64 bits. The bounded caller request independently loads typed DamageUnit.atkCalculation into retained RBX and passes it in RDX; helper RCX entry is not receiver. Caller local Unit/this/actor/frame origins, opaque context return validity and anonymous pack carriers remain conditions; normal Win64 calls must preserve carriers and saved storage. Ordinary metadata Evaluate prototypes and slot agree, but interpreting the two offsets as that virtual slot requires the JSON-declared runtime layout and compatible live runtime class/prototype/parity/MethodInfo. No live subtype, callback name, helper managed identity, opaque pre-dispatch semantics, class initialization, caller pack layout, equal-target inline arithmetic or final value is inferred.'}
