"""Selected raw local-index request and returned-bits temporary transfer."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _address,_require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_local_request(rows,*,pointer,normal_pointer,operands):
    o=operands
    expected=[b'\x49\x8b\xcf','predicate',b'\x48\x8b\x8c\x24'+struct.pack('<i',o['actionReferenceLocalDisp32']),b'\x84\xc0','zero-byte',
              b'\x4c\x89\x74\x24\x40',b'\x48\x8d\x44\x24'+bytes([o['outBoolLocalDisp8']]),b'\x48\x89\x44\x24\x38',b'\x4c\x89\x6c\x24\x30',
              b'\x48\x8d\x84\x24'+struct.pack('<i',o['opaqueLocalBufferDisp32']),b'\x48\x89\x44\x24\x28',
              b'\x8b\x84\x24'+struct.pack('<i',o['indexLocalDisp32']),b'\x89\x44\x24\x20',b'\x4c\x8b\xce',b'\x4c\x8b\x44\x24'+bytes([o['attackerLocalDisp8']]),b'\x49\x8b\xd7','normal',
              b'\x66\x48\x0f\x6e\xc8',b'\x0f\x28\xf1','continuation']
    _require(len(rows)>=len(expected),'process-local-index-length','complete scoped request/temporary',len(rows))
    address=pointer;calls={};excluded=None;continuation=None
    for row,encoding in zip(rows,expected):
        raw=bytes.fromhex(row['bytes']);_require(_address(row)==address,'process-local-index-contiguity',hex(address),row['va'])
        if encoding in ('predicate','normal','continuation'):
            opcode=b'\xe9' if encoding=='continuation' else b'\xe8'
            _require(len(raw)==5 and raw[:1]==opcode,'process-local-index-transfer',[encoding,opcode.hex()],raw.hex())
            target=relative_branch_target(raw,address,source='processLocalIndex')
            if encoding=='normal':_require(target==normal_pointer,'process-local-index-normal-entry',hex(normal_pointer),hex(target))
            if encoding=='continuation':continuation=target
            else:calls[encoding]=hex(target)
        elif encoding=='zero-byte':
            _require(len(raw)==2 and raw[:1]==b'\x75','process-local-index-predicate','JNE excludes nonzero AL',raw.hex())
            excluded=address+2+int.from_bytes(raw[1:],'little',signed=True)
        else:_require(raw==encoding,'process-local-index-instruction',encoding.hex(),raw.hex())
        address+=len(raw)
    _require(excluded not in {_address(r) for r in rows[:len(expected)]} and continuation not in {_address(r) for r in rows[:len(expected)]},
             'process-local-index-excluded-boundaries','outside scoped fragment',[excluded,continuation])
    return {'fragmentEntry':hex(pointer),'selectedInstructionCount':len(expected),'indexReadWidthBytes':4,
            'anonymousPackBufferDisp32':o['opaqueLocalBufferDisp32'],'anonymousOutBoolLocalDisp8':o['outBoolLocalDisp8'],'anonymousIndexLocalDisp32':o['indexLocalDisp32'],'indexSource':'anonymous local current-SP displacement, not a named input parameter or observed counter',
            'unitSource':'conditional entry RSI full64','receiverSource':'anonymous local full64 action reference',
            'requestIndexCallerStoreOffset':32,'expectedNormalIndexEntryOffset':40,'actualCalls':calls,
            'resultToTemp':'normal RAX low64 -> MOVQ XMM1 -> MOVAPS XMM6','returnedBitsToTemporaryProved':True,
            'excludedNonzeroByteTarget':hex(excluded),'temporaryContinuation':hex(continuation),
            'wholeProcessDamagePathProved':False,'localCounterInitAndWriterJoinProved':False,'producerConsumerIndexJoinProved':False}


def raw_request_rows(raw,*,pointer):
    """Partition only this fragment; do not decode preceding Process instructions."""
    widths=(3,5,8,2,2,5,5,5,5,8,5,7,4,3,5,3,5,5,3,5)
    rows=[];at=0
    for width in widths:
        _require(at+width<=len(raw),'process-local-raw-truncated',at+width,len(raw))
        rows.append({'va':hex(pointer+at),'bytes':raw[at:at+width].hex()});at+=width
    return rows


def require_reference_proxy(raw,actual,expected,kind,role):
    _require(len(raw)==16 and actual==expected and raw[10]==kind and raw[11]&0x7f==0x20,
             'process-local-reference-proxy',[role,expected,kind,'explicit unpinned ref'],raw.hex())


def local_storage_conditions(current_rsp,program,pack_storage_bytes):
    """Concrete relative ranges, conditional on valid storage; no local values inferred."""
    _require(type(current_rsp) is int and type(pack_storage_bytes) is int and pack_storage_bytes>0,
             'process-local-storage-inputs','integer SP and positive value storage size',[current_rsp,pack_storage_bytes])
    ranges={'indexSource':(current_rsp+program['indexLocalDisp32'],4),
            'attackerSource':(current_rsp+program['attackerLocalDisp8'],8),
            'actionSource':(current_rsp+program['actionReferenceLocalDisp32'],8),
            'outBool':(current_rsp+program['outBoolLocalDisp8'],1),
            'packStorage':(current_rsp+program['opaqueLocalBufferDisp32'],pack_storage_bytes),
            'outgoingIndex':(current_rsp+32,4),'outgoingPackProxy':(current_rsp+40,8),
            'outgoingDetails':(current_rsp+48,8),'outgoingBoolProxy':(current_rsp+56,8),'outgoingOpaqueContext':(current_rsp+64,8)}
    valid=all(0<=address and address+width<=1<<64 for address,width in ranges.values())
    pairs={}
    for left,(a,n) in ranges.items():
        for right,(b,m) in ranges.items():
            if left<right:pairs[left+'/'+right]=valid and (a+n<=b or b+m<=a)
    return {'validNonwrappingRanges':valid,'actualRanges':{k:{'address':a,'widthBytes':n} for k,(a,n) in ranges.items()},
            'pairwiseDisjoint':pairs,'allDisjoint':valid and all(pairs.values()),
            'storageValidityOrValueInitializationObserved':False}


def check_process_local(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    caller=index.body(spec['type'],spec['method']);callee=index.body(spec['type'],spec['calleeMethod'])
    _require(consumer_proof.get('symbol')==callee.symbol and consumer_proof.get('claim')=='snapshotCacheIndexToReturn',
             'process-local-fresh-consumer',callee.symbol,consumer_proof.get('symbol'))
    selected=NativeReferenceContext(index.image,index=index)
    _require(not selected.is_value_type(spec['type']),'process-local-this-class','ordinary action class',spec['type'])
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(callee.pointer,()) if f"{r.get('type')}.{r.get('method')}"==callee.symbol]
    _require(bool(methods) and all(not m.flags&0x10 for m in methods),'process-local-instance-abi','normal instance method',callee.symbol)
    for method in methods:
        require_ordinary_type(selected,_parameter(selected,method,'index').type_index,'int','Process.normal.index')
        require_ordinary_type(selected,_parameter(selected,method,'damageUnit').type_index,spec['unitType'],'Process.normal.unit',reference_kind=0x12)
        for name in ('target','attacker'):require_ordinary_type(selected,_parameter(selected,method,name).type_index,spec['abilityType'],'Process.normal.'+name,reference_kind=0x12)
        require_ordinary_type(selected,_parameter(selected,method,'serverDetails').type_index,spec['detailsType'],'Process.normal.details',reference_kind=0x12)
        require_ordinary_value_type(selected,method.return_type,spec['returnType'],'Process.normal.return')
        for name,typ,kind in (('calcSucceed','bool',0x02),('damagePackData',spec['packType'],0x11)):
            parameter=_parameter(selected,method,name);raw=index.pe.bytes_at_va(selected.type_pointer(parameter.type_index),16)
            require_reference_proxy(raw,selected.type_name(parameter.type_index),typ,kind,name)
    locations={'this':('register','rcx'),'target':('register','rdx'),'attacker':('register','r8'),'damageUnit':('register','r9'),
               'index':('stack',40),'damagePackData':('stack',48),'serverDetails':('stack',56),'calcSucceed':('stack',64)}
    for name,expected in locations.items():
        actual=index.parameter_location(callee.pointer,callee.symbol,name)
        _require(actual==expected,'process-local-actual-callee-slot',[name,expected],actual)
    _require(caller.pointer in index.extents and 0<index.extents[caller.pointer]-caller.pointer<=65536,
             'process-local-owned-search','bounded exact caller pdata extent',hex(caller.pointer))
    raw=index.pe.bytes_at_va(caller.pointer,index.extents[caller.pointer]-caller.pointer)
    # Anchor is only a candidate locator; the complete raw program below authenticates it.
    anchor=b'\x49\x8b\xcf\xe8';positions=[at for at in range(len(raw)) if raw.startswith(anchor,at)];matches=[]
    for at in positions:
        try:
            rows=raw_request_rows(raw[at:],pointer=caller.pointer+at)
            proof=check_local_request(rows,pointer=caller.pointer+at,normal_pointer=callee.pointer,operands=spec['anonymousProgram'])
        except ValueError:continue
        matches.append(proof)
    _require(len(matches)==1,'process-local-unique-program','one exact raw request/result fragment',len(matches))
    return {**matches[0],'symbol':caller.symbol,'claim':'snapshotProcessLocalIndexNormalRequestAndTemporary',
            'selectedCallee':callee.symbol,'boundary':'One exact owned raw fragment, conditional entry and normally returned unnamed predicate AL zero, transfers an anonymous current-SP Int32 local into the fresh normal consumer index stack slot. Full reference register/stack transfers and ordinary callee ABI, plus explicit unpinned Bool and value ref proxies, are checked. Returned RAX low64 bits pass through MOVQ XMM1 and MOVAPS XMM6 before the exact outgoing continuation. Sources must contain valid typed references; current-SP locals, outgoing slots, pointed Bool/value storage and frame must be valid and mutually noninterfering throughout normal Win64 provider/callee returns. No full Process entry-to-fragment CFG, frame continuity, local counter initialization/all writers, pointed value contents, snapshot compact-index equality or live/final damage is proved.'}
