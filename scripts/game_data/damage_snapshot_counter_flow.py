"""Carry the fresh producer reset zero into counter initialization on one path."""
from __future__ import annotations
import struct
from scripts.game_data.damage_snapshot_cache_flow import _address,_require
from scripts.game_data.damage_snapshot_abi import require_ordinary_signature
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def check_counter_program(rows,*,start,patch_pointer,program):
    keys=('opaqueRootPointerDisp8','opaqueInnerPointerDisp32','opaquePayloadPointerDisp8','localVectorDisp8','localFlagDisp8')
    for key in keys:
        limit=0x7fffffff if key.endswith('Disp32') else 127
        _require(type(program.get(key)) is int and 0<=program[key]<=limit,'snapshot-counter-declaration',[key,limit],program.get(key))
    root=program[keys[0]];inner=program[keys[1]];payload=program[keys[2]];vector=program[keys[3]];flag=program[keys[4]]
    expected=[b'\x0f\x57\xc0',b'\x33\xd2','request-id',b'\x0f\x11\x44\x24'+bytes([vector]),'patch-call',b'\x84\xc0','false-patch',
              b'\x48\x8b\x45'+bytes([root]),b'\x48\x85\xc0','nonnull-root',b'\x48\x8b\x80'+struct.pack('<i',inner),
              b'\x48\x85\xc0','null-inner',b'\x41\x8b\xcd',b'\x48\x8b\x45'+bytes([root]),b'\x85\xc9',
              b'\x0f\x95\x44\x24'+bytes([flag]),b'\x48\x85\xc0','nonnull-root-again',b'\x48\x8b\x40'+bytes([payload]),b'\x41\x8b\xf5']
    _require(len(rows)>=len(expected),'snapshot-counter-length','complete selected zero-transfer',len(rows))
    address=start;excluded={};request=None
    for row,encoding in zip(rows,expected):
        raw=bytes.fromhex(row['bytes']);_require(_address(row)==address,'snapshot-counter-contiguity',hex(address),row['va'])
        if encoding=='request-id':
            _require(len(raw)==5 and raw[:1]==b'\xb9','snapshot-counter-request','MOV ECX immediate',raw.hex());request=int.from_bytes(raw[1:],'little')
        elif encoding=='patch-call':
            _require(len(raw)==5 and raw[:1]==b'\xe8','snapshot-counter-call','direct CALL',raw.hex())
            actual=relative_branch_target(raw,address,source='snapshotCounter')
            _require(actual==patch_pointer,'snapshot-counter-patch-entry',hex(patch_pointer),hex(actual))
        elif isinstance(encoding,str):
            op=b'\x0f\x85' if encoding in ('false-patch','null-inner') else b'\x0f\x84'
            _require(len(raw)==6 and raw[:2]==op,'snapshot-counter-condition',[encoding,op.hex()],raw.hex())
            excluded[encoding]=hex(address+6+int.from_bytes(raw[2:],'little',signed=True))
        else:_require(raw==encoding,'snapshot-counter-instruction',encoding.hex(),raw.hex())
        address+=len(raw)
    addresses={_address(r) for r in rows[:len(expected)]}
    _require(all(int(target,16) not in addresses for target in excluded.values()),'snapshot-counter-excluded-edges','outside selected fallthrough',excluded)
    return {'zeroTransferEntry':hex(start),'counterInitialization':rows[len(expected)-1]['va'],
            'selectedInstructionCount':len(expected),'patchRequestImmediate':request,'excludedTargets':excluded,
            'counterRegister':'esi','counterInitialValue':0,'counterWriteWidthBits':32,'counterZeroExtendsRsi':True,
            'opaquePayloadMeaningProved':False,'producerConsumerIndexJoinProved':False}


def check_snapshot_counter(index,clear_proof,spec):
    _require(clear_proof.get('claim')=='snapshotIncomingThisCacheReset','snapshot-counter-clear-proof','fresh R13D zero/reset proof',clear_proof.get('claim'))
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==clear_proof['symbol'] and body.pointer==int(clear_proof['entry'],16),'snapshot-counter-same-body','fresh reset producer',body.symbol)
    matches=[n for n,r in enumerate(body.rows) if _address(r)==int(clear_proof['resetStore'],16)]
    _require(len(matches)==1,'snapshot-counter-reset-boundary','fresh reset store instruction',matches)
    fragment=body.rows[matches[0]+1:]
    _require(len(fragment)>=21,'snapshot-counter-available','complete following fragment',len(fragment))
    reset_row=body.rows[matches[0]]
    _require(_address(fragment[0])==_address(reset_row)+len(bytes.fromhex(reset_row['bytes'])),
             'snapshot-counter-reset-fallthrough','immediately after fresh reset store',fragment[0]['va'])
    call=fragment[4];raw=bytes.fromhex(call['bytes']);patch=relative_branch_target(raw,_address(call),source='snapshotCounterPatch')
    selected=NativeReferenceContext(index.image,index=index)
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(patch,())
             if f"{r.get('type')}.{r.get('method')}"==spec['patchMethod']]
    _require(bool(methods) and all(m.flags&0x10 for m in methods),'snapshot-counter-patch-identity','named static IFix guard',len(methods))
    for method in methods:require_ordinary_signature(selected,method,['int'],'bool','snapshot.counter.IFix')
    proof=check_counter_program(fragment,start=_address(fragment[0]),patch_pointer=patch,program=spec['anonymousOperands'])
    return {**proof,'symbol':body.symbol,'claim':'snapshotResetZeroToCounterInitialization',
            'boundary':'The complete selected fallthrough after the fresh cache reset retains its proved R13D zero through a normally returning ordinary static Bool/Int32 IFix guard and explicit false-patch, nonnull opaque root and null inner-reference branches. No selected instruction writes R13. MOV ECX,R13D and SETNE yield a zero local flag, and MOV ESI,R13D initializes the iteration counter to zero with RSI zero extension. Opaque pointer/payload loads and local stores do not name a selector or payload schema. Valid unchanged frame/carriers, callee noninterference and normal Win64 nonvolatile preservation remain conditions. Other branches, source-count semantics, full loop/order, actual consumer index equality and live final output remain open.'}
