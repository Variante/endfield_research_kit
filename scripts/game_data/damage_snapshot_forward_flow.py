"""Forward the ByType incoming index/unit and returned bits on one complete path."""
from __future__ import annotations
import struct
from scripts.game_data.damage_snapshot_cache_flow import _address,_require
from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_signature,require_ordinary_value_type
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def out_storage_disjoint(out_pointer,entry_rsp,index_offset,unit_offset,frame_allocation,callee_index_offset):
    _require(all(type(v) is int for v in (out_pointer,entry_rsp,index_offset,unit_offset,frame_allocation,callee_index_offset)),
             'snapshot-forward-storage-inputs','integer raw addresses/offsets',[out_pointer,entry_rsp,index_offset,unit_offset,frame_allocation,callee_index_offset])
    ranges={'outgoingIndex':(entry_rsp-frame_allocation-8+callee_index_offset-8,4),'index':(entry_rsp+index_offset,4),'unit':(entry_rsp+unit_offset,8),
            'returnAddress':(entry_rsp,8),'savedRdi':(entry_rsp+8,8),'savedRbx':(entry_rsp+16,8),
            'savedRbp':(entry_rsp+24,8),'savedRsi':(entry_rsp+32,8),'savedR14':(entry_rsp-8,8)}
    valid=0<=out_pointer<1<<64 and all(0<=a and a+n<=1<<64 for a,n in ranges.values())
    disjoint={k:bool(valid and (out_pointer+1<=a or a+n<=out_pointer)) for k,(a,n) in ranges.items()}
    return {'outWriteWidthBytes':1,'validNonwrappingRanges':valid,'protectedRanges':ranges,
            'disjointConditions':disjoint,'allProtectedRangesDisjoint':valid and all(disjoint.values())}


def check_forward_program(rows,*,pointer,first_end,normal_end,return_end,index_entry,unit_entry,out_entry,callee_index_entry,patch_pointer,normal_pointer,program):
    frame=program['frameAllocation'];flag=program['opaqueCarrierDwordDisp32']
    _require(type(frame) is int and 80<=frame<=111 and frame%16==0 and type(flag) is int and 0<=flag<=0x7fffffff,
             'snapshot-forward-operands','aligned positive frame and anonymous carrier displacement',[frame,flag])
    _require(all(type(program.get(k)) is int and 0<=program[k]<=0x7fffffff for k in ('opaqueIncomingPointerOneCurrentOffset','opaqueIncomingPointerTwoCurrentOffset')),
             'snapshot-forward-opaque-stack-operands','bounded anonymous stack offsets',program)
    delta=frame+8;saved_rdi=frame+16;index_current=index_entry+delta;unit_current=unit_entry+delta;out_current=out_entry+delta
    callee_store=callee_index_entry-8
    _require(all(type(v) is int and 0<=v<=0x7fffffff for v in (index_current,unit_current,out_current)) and 0<=callee_store<=127,
             'snapshot-forward-stack-operands','bounded input loads and callee store',[index_current,unit_current,out_current,callee_store])
    expected=[b'\x48\x89\x5c\x24\x10',b'\x48\x89\x6c\x24\x18',b'\x48\x89\x74\x24\x20',b'\x41\x56',b'\x48\x83\xec'+bytes([frame]),
              b'\x48\x8b\xda',b'\x48\x8b\xf1',b'\x33\xd2','patch-id',b'\x45\x0f\xb6\xf1',b'\x49\x8b\xe8','patch-call',b'\x84\xc0','false-patch',
              b'\x48\x89\x7c\x24'+bytes([saved_rdi]),b'\x48\x8b\xbc\x24'+struct.pack('<i',out_current),b'\xc6\x07\x01','carrier-one',
              b'\x83\xb9'+struct.pack('<i',flag)+b'\x00','carrier-one-nonzero',b'\x48\x8b\xcb','predicate-one-call',b'\x84\xc0','predicate-one-zero',
              'carrier-two',b'\x83\xb9'+struct.pack('<i',flag)+b'\x00','carrier-two-nonzero',b'\x48\x8b\xcb','predicate-two-call',b'\x48\x8b\xce',b'\x84\xc0','predicate-two-zero',
              b'\x48\x8b\x84\x24'+struct.pack('<i',program['opaqueIncomingPointerOneCurrentOffset']),b'\x4c\x8b\xc5',b'\x4c\x8b\x8c\x24'+struct.pack('<i',unit_current),b'\x48\x8b\xd3',
              b'\x48\xc7\x44\x24\x40\x00\x00\x00\x00',b'\x48\x89\x7c\x24\x38',b'\x48\x89\x44\x24\x30',
              b'\x48\x8b\x84\x24'+struct.pack('<i',program['opaqueIncomingPointerTwoCurrentOffset']),b'\x48\x89\x44\x24\x28',
              b'\x8b\x84\x24'+struct.pack('<i',index_current),b'\x89\x44\x24'+bytes([callee_store]),'normal-call',
              b'\x66\x48\x0f\x6e\xc8',b'\x48\x8b\x7c\x24'+bytes([saved_rdi]),b'\x66\x48\x0f\x7e\xc8',b'\x4c\x8d\x5c\x24'+bytes([frame]),
              b'\x49\x8b\x5b\x18',b'\x49\x8b\x6b\x20',b'\x49\x8b\x73\x28',b'\x49\x8b\xe3',b'\x41\x5e',b'\xc3']
    _require(len(rows)>=len(expected),'snapshot-forward-length','complete selected entry-to-RET',len(rows))
    address=pointer;calls={};excluded={};loads={};request=None
    for n,(row,encoding) in enumerate(zip(rows,expected)):
        raw=bytes.fromhex(row['bytes']);_require(_address(row)==address,'snapshot-forward-contiguity',hex(address),row['va'])
        if n<14:_require(address+len(raw)<=first_end,'snapshot-forward-entry-owned-range','first exact prefix',row['va'])
        elif n<47:_require(first_end<=address and address+len(raw)<=normal_end,'snapshot-forward-normal-owned-range','second exact fragment',row['va'])
        else:_require(normal_end<=address and address+len(raw)<=return_end,'snapshot-forward-return-owned-range','third exact RET fragment',row['va'])
        if n==47:_require(address==normal_end,'snapshot-forward-return-fragment-join',hex(normal_end),hex(address))
        if n==14:_require(address==first_end,'snapshot-forward-fragment-join',hex(first_end),hex(address))
        if encoding=='patch-id':
            _require(len(raw)==5 and raw[:1]==b'\xb9','snapshot-forward-patch-id','MOV ECX imm32',raw.hex());request=int.from_bytes(raw[1:],'little')
        elif isinstance(encoding,str) and encoding.endswith('-call'):
            _require(len(raw)==5 and raw[:1]==b'\xe8','snapshot-forward-call','direct CALL',raw.hex())
            target=relative_branch_target(raw,address,source='snapshotIndexForward');calls[encoding]=hex(target)
            if encoding in ('patch-call','normal-call'):
                wanted=patch_pointer if encoding=='patch-call' else normal_pointer
                _require(target==wanted,'snapshot-forward-target',[encoding,hex(wanted)],hex(target))
        elif encoding in ('carrier-one','carrier-two'):
            _require(len(raw)==7 and raw[:3]==b'\x48\x8b\x0d','snapshot-forward-carrier-load','RCX RIP qword',raw.hex());loads[encoding]=row['va']
        elif isinstance(encoding,str):
            opcode=b'\x0f\x84' if encoding.endswith('nonzero') else b'\x75' if encoding=='predicate-two-zero' else b'\x0f\x85'
            size=2 if len(opcode)==1 else 6
            _require(len(raw)==size and raw[:len(opcode)]==opcode,'snapshot-forward-condition',[encoding,opcode.hex()],raw.hex())
            excluded[encoding]=hex(address+size+int.from_bytes(raw[len(opcode):],'little',signed=True))
        else:_require(raw==encoding,'snapshot-forward-instruction',encoding.hex(),raw.hex())
        address+=len(raw)
    _require(address==return_end,'snapshot-forward-owned-ret-end',hex(return_end),hex(address))
    _require(all(int(t,16) not in {_address(r) for r in rows[:len(expected)]} for t in excluded.values()),
             'snapshot-forward-excluded-targets','outside selected returning path',excluded)
    return {'entry':hex(pointer),'selectedReturnEnd':hex(address),'selectedInstructionCount':len(expected),
            'firstOwnedPrefixEnd':hex(first_end),'secondOwnedFragmentEnd':hex(normal_end),'thirdOwnedReturnEnd':hex(return_end),'wholeByTypeFunctionOwnershipProved':False,
            'incomingIndexEntryStackOffset':index_entry,'checkedSpDeltaBeforeCall':delta,'incomingIndexCurrentStackOffset':index_current,
            'indexLoadWidthBytes':4,'indexCallerStoreOffset':callee_store,'indexCalleeEntryStackOffset':callee_index_entry,
            'incomingUnitEntryStackOffset':unit_entry,'unitReceiverTransferWidthBytes':8,'unitCalleeRegister':'r9',
            'sameThisRegisterChain':'incoming RCX -> nonvolatile RSI -> normal RCX',
            'returnedBitsTransfer':'normal RAX low64 -> MOVQ XMM1 -> full RAX -> complete restoring RET',
            'patchRequestImmediate':request,'actualCalls':calls,'anonymousCarrierLoads':loads,'excludedTargets':excluded,
            'rawPredicateResultConditions':'each normally returned AL byte equals zero; no Bool/classification ABI inferred',
            'initialOutByteStoreWidthBytes':1,'producerConsumerIndexJoinProved':False}


def _parameter(selected,method,name):
    meta=selected.image.metadata;matches=[p for p in meta.parameters_for(method) if meta.string(p.name_index)==name]
    _require(len(matches)==1,'snapshot-forward-parameter',[name,1],len(matches));return matches[0]


def check_snapshot_forward(index,consumer_proof,spec):
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','snapshot-forward-consumer-proof','fresh normal consumer cache proof',consumer_proof.get('claim'))
    caller=index.body(spec['type'],spec['method']);callee=index.body(spec['type'],spec['calleeMethod'])
    _require(callee.symbol==consumer_proof['symbol'],'snapshot-forward-same-consumer',consumer_proof['symbol'],callee.symbol)
    selected=NativeReferenceContext(index.image,index=index);owner,typ,_=selected.field(spec['snapshotField'])
    _require(owner==spec['unitType'] and typ=='bool','snapshot-forward-unit-owner',[spec['unitType'],'bool'],[owner,typ])
    for body in (caller,callee):
        methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
        _require(bool(methods) and all(not m.flags&0x10 for m in methods),'snapshot-forward-instance-abi','named instance methods',body.symbol)
        for m in methods:
            require_ordinary_type(selected,_parameter(selected,m,'index').type_index,'int',body.symbol+'.index')
            require_ordinary_type(selected,_parameter(selected,m,'damageUnit').type_index,owner,body.symbol+'.unit',reference_kind=0x12)
            for name in ('target','attacker'):require_ordinary_type(selected,_parameter(selected,m,name).type_index,spec['abilityType'],body.symbol+'.'+name,reference_kind=0x12)
            require_ordinary_value_type(selected,m.return_type,spec['returnType'],body.symbol+'.return')
            out=_parameter(selected,m,'calcSucceed');raw=index.pe.bytes_at_va(selected.type_pointer(out.type_index),16)
            _require(len(raw)==16 and selected.type_name(out.type_index)=='bool' and raw[10]==0x02 and raw[11]&0x7f==0x20,
                     'snapshot-forward-out-reference-abi','explicit unpinned ordinary Bool ref proxy',raw.hex())
    _require(not selected.is_value_type(spec['type']),'snapshot-forward-this-class','ordinary action reference class',spec['type'])
    for name,register in (('this','rcx'),('target','rdx'),('attacker','r8')):
        _require(all(index.parameter_location(b.pointer,b.symbol,name)==('register',register) for b in (caller,callee)),
                 'snapshot-forward-reference-register',[name,register],[index.parameter_location(b.pointer,b.symbol,name) for b in (caller,callee)])
    unit_location=index.parameter_location(caller.pointer,caller.symbol,'damageUnit');idx_location=index.parameter_location(caller.pointer,caller.symbol,'index');out_location=index.parameter_location(caller.pointer,caller.symbol,'calcSucceed')
    callee_index=index.parameter_location(callee.pointer,callee.symbol,'index')
    _require(all(p[0]=='stack' and type(p[1]) is int for p in (unit_location,idx_location,out_location,callee_index)),
             'snapshot-forward-stack-abi','explicit named stack offsets',[unit_location,idx_location,out_location,callee_index])
    _require(index.parameter_location(callee.pointer,callee.symbol,'damageUnit')==('register','r9'),'snapshot-forward-callee-unit-abi',['register','r9'],index.parameter_location(callee.pointer,callee.symbol,'damageUnit'))
    _require(caller.pointer in index.extents,'snapshot-forward-owned-entry','first exact pdata prefix',hex(caller.pointer));first_end=index.extents[caller.pointer]
    _require(first_end in index.extents,'snapshot-forward-second-fragment','adjacent exact pdata fragment',hex(first_end));normal_end=index.extents[first_end]
    _require(normal_end in index.extents,'snapshot-forward-return-fragment','adjacent exact RET fragment',hex(normal_end));return_end=index.extents[normal_end]
    _require(0<first_end-caller.pointer<=1024 and 0<normal_end-first_end<=4096 and 0<return_end-normal_end<=512,'snapshot-forward-owned-bounds','bounded exact adjacent fragments',[caller.pointer,first_end,normal_end,return_end])
    rows=caller.rows;_require(len(rows)>=12,'snapshot-forward-patch-available','selected entry program',len(rows))
    patch=relative_branch_target(bytes.fromhex(rows[11]['bytes']),_address(rows[11]),source='snapshotForwardPatch')
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(patch,()) if f"{r.get('type')}.{r.get('method')}"==spec['patchMethod']]
    _require(bool(methods) and all(m.flags&0x10 for m in methods),'snapshot-forward-patch-identity','named static IFix',len(methods))
    for m in methods:require_ordinary_signature(selected,m,['int'],'bool','snapshot.forward.IFix')
    proof=check_forward_program(rows,pointer=caller.pointer,first_end=first_end,normal_end=normal_end,return_end=return_end,index_entry=idx_location[1],unit_entry=unit_location[1],out_entry=out_location[1],callee_index_entry=callee_index[1],patch_pointer=patch,normal_pointer=callee.pointer,program=spec['anonymousProgram'])
    end=int(proof['selectedReturnEnd'],16)
    _require(b''.join(bytes.fromhex(r['bytes']) for r in rows[:proof['selectedInstructionCount']])==index.pe.bytes_at_va(caller.pointer,end-caller.pointer),
             'snapshot-forward-byte-coverage','complete selected raw byte partition',end-caller.pointer)
    return {**proof,'symbol':caller.symbol,'claim':'snapshotByTypeIndexUnitAndResultForward',
            'selectedCallee':callee.symbol,'unitType':owner,
            'boundary':'The complete selected false-IFix/nonzero-anonymous-carrier/zero-AL-predicate path forwards the named ordinary incoming Int32 index and ordinary unit reference into the exact fresh normal consumer ABI slots, preserves this/target/attacker through nonvolatile register chains, and passes normally returned low64 result bits through full MOVQ transfers and a complete restoring RET. The out parameter has a separate checked explicit Bool reference-proxy ABI; its byte store requires the actual destination range disjoint from incoming/outgoing index, incoming unit, return address and saved-frame slots, and all providers/callees must leave those sources/frame/storage unchanged under normal Win64 return. Predicate calls are unnamed actual targets: AL zero is not Bool/type-classification semantics. Three exact adjacent owned fragments cover this selected returning path; other fragments/branches and whole-function ownership are not inferred. Actual top-level caller index selection, live cache/compact index equality, provider values and final output remain unresolved.'}
