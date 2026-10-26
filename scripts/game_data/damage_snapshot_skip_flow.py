"""Prove the snapshot-flag skip/append continuation graph, not index equality."""
from __future__ import annotations

from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.damage_snapshot_abi import require_ordinary_field
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_skip_program(rows, *, start, flag_offset, append_entry, continuation, return_entry):
    _require(type(flag_offset) is int and 0<=flag_offset<128,'snapshot-skip-flag-offset','positive disp8',flag_offset)
    expected=[b'\x44\x38\x6b'+bytes([flag_offset]),'append-edge',b'\xff\xc6',b'\x41\x3b\xf6','loop-edge',
              b'\x0f\x28\x74\x24\x60',b'\x4c\x8d\x5c\x24\x70',b'\x49\x8b\x5b\x30',
              b'\x49\x8b\x6b\x38',b'\x49\x8b\x73\x40',b'\x49\x8b\xe3',
              b'\x41\x5f',b'\x41\x5e',b'\x41\x5d',b'\x41\x5c',b'\x5f',b'\xc3']
    _require(len(rows)>=len(expected),'snapshot-skip-length','complete skip and RET',len(rows))
    address=start;loop=None
    for n,(row,encoding) in enumerate(zip(rows,expected)):
        raw=bytes.fromhex(row['bytes'])
        _require(_address(row)==address,'snapshot-skip-contiguity',hex(address),row['va'])
        if encoding in ('append-edge','loop-edge'):
            edge=_edge(row)
            opcode=b'\x75' if encoding=='append-edge' else b'\x7c'
            _require(len(raw)==2 and raw[:1]==opcode and edge is not None,'snapshot-skip-condition',opcode.hex(),raw.hex())
            target=address+2+int.from_bytes(raw[1:],'little',signed=True)
            _require(edge[0]==target,'snapshot-skip-decoded-edge',hex(target),edge)
            if encoding=='append-edge':
                _require(target==append_entry,'snapshot-skip-append-entry',hex(append_entry),hex(target))
            else:
                _require(target<start,'snapshot-skip-backedge','earlier loop header',hex(target));loop=target
        else:
            _require(raw==encoding,'snapshot-skip-instruction',encoding.hex(),raw.hex())
        if n==2:_require(address==continuation,'snapshot-skip-shared-continuation',hex(continuation),hex(address))
        if n==5:_require(address==return_entry,'snapshot-skip-shared-return',hex(return_entry),hex(address))
        address+=len(raw)
    return {'skipEntry':hex(start),'iterationContinuation':hex(continuation),'loopTarget':hex(loop),
            'returnEntry':hex(return_entry),'appendFragmentEntry':hex(append_entry),
            'selectedInstructionCount':len(expected),'iterationIncrementWidthBits':32,
            'iterationIncrementZeroExtendsRsi':True,'loopComparison':'signed Int32 incremented ESI < R14D',
            'skipPathCalls':[],'skipPathMemoryStores':[],'producerConsumerIndexJoinProved':False}


def check_snapshot_skip(index, append_proof, clear_proof, spec):
    _require(append_proof.get('claim')=='snapshotSimpleValueToAppendRequest' and clear_proof.get('claim')=='snapshotIncomingThisCacheReset',
             'snapshot-skip-dependencies','fresh append and entry/RET proofs',[append_proof.get('claim'),clear_proof.get('claim')])
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==append_proof['symbol']==clear_proof['symbol'] and body.pointer==int(clear_proof['entry'],16),
             'snapshot-skip-same-body','same producer selected body',body.symbol)
    selected=NativeReferenceContext(index.image,index=index)
    owner,flag_type,offset=selected.field(spec['snapshotField'])
    _require(owner==spec['unitType'] and flag_type=='bool','snapshot-skip-flag-owner',[spec['unitType'],'bool'],[owner,flag_type])
    require_ordinary_field(selected,spec['snapshotField'],'bool','snapshot.skipFlag')
    matches=[n for n,r in enumerate(body.rows) if bytes.fromhex(r['bytes'])==b'\x44\x38\x6b'+bytes([offset])]
    _require(len(matches)==1,'snapshot-skip-selection','one exact RBX flag compare',len(matches))
    proof=check_skip_program(body.rows[matches[0]:],start=_address(body.rows[matches[0]]),flag_offset=offset,
        append_entry=int(append_proof['fragmentEntry'],16),continuation=int(append_proof['continuation'],16),
        return_entry=int(clear_proof['nullTargetReturn'],16))
    _require(any(_address(r)==int(proof['loopTarget'],16) for r in body.rows),
             'snapshot-skip-loop-boundary','complete selected body instruction',proof['loopTarget'])
    return {**proof,'symbol':body.symbol,'claim':'snapshotFlagSkipAppendContinuation',
            'fragmentEntryConditions':{'rbx':owner,'r13b':0,'esi':'conditional iteration counter','r14d':'conditional signed loop bound'},
            'boundary':'The checked zero snapshot flag skips the append fragment and reaches a raw 32-bit INC ESI with RSI zero extension, then signed Int32 CMP/JL either returns to a checked earlier instruction boundary or enters the complete previously proved producer RET. Nonzero flag reaches the exact fresh simple-append fragment entry, whose checked continuation reaches that same increment. The selected skip path makes no calls or explicit memory stores. Valid live unit/frame, R13B zero and register-entry roles remain conditions. Counter initialization, unit-list ownership, loop-header behavior, non-simple branches, overflow-free ordinal interpretation, cache order and actual consumer-index equality remain unresolved.'}
