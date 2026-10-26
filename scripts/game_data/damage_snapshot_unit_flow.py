"""Prove raw indexed unit-pointer transfer into the checked snapshot flag graph."""
from __future__ import annotations
from scripts.game_data.damage_snapshot_cache_flow import _address,_require
from scripts.game_data.damage_snapshot_abi import require_ordinary_field
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def indexed_unit_address(index,base,payload):
    valid=type(index) is int and 0<=index<=0x7fffffff and type(base) is int and 0<=base<1<<64 and type(payload) is int and payload>=0
    result=base+payload+index*8 if valid else None
    return {'signedIndex':index,'address':result,'widthBytes':8,'validNonwrappingAddress':bool(valid and result<=((1<<64)-8))}


def check_unit_program(rows,*,start,skip_entry,flag_offset,root_child,slots):
    values=[root_child['actionRootDisp8'],root_child['rootCollectionDisp8'],flag_offset,*slots.values()]
    _require(all(type(v) is int and 0<=v<=127 for v in values),'snapshot-unit-operands','positive anonymous disp8',values)
    root=root_child['actionRootDisp8'];child=root_child['rootCollectionDisp8']
    count=slots['carrierCountDwordDisp8'];array=slots['carrierArrayReferenceDisp8'];length=slots['arrayBoundDwordDisp8'];payload=slots['arrayPayloadDisp8']
    expected=[b'\x48\x8b\x4f'+bytes([root]),b'\x48\x85\xc9','nonnull-root',b'\x48\x8b\x49'+bytes([child]),b'\x48\x85\xc9','nonnull-carrier',
              b'\x3b\x71'+bytes([count]),'unsigned-count',b'\x48\x8b\x51'+bytes([array]),b'\x48\x85\xd2','nonnull-array',
              b'\x3b\x72'+bytes([length]),'unsigned-array',b'\x48\x63\xc6',b'\x48\x8b\x5c\xc2'+bytes([payload]),b'\x48\x85\xdb','nonnull-unit',
              b'\x44\x38\x6b'+bytes([flag_offset])]
    _require(len(rows)>=len(expected),'snapshot-unit-length','complete pointer-to-flag graph',len(rows))
    address=start;excluded={}
    for n,(row,encoding) in enumerate(zip(rows,expected)):
        raw=bytes.fromhex(row['bytes']);_require(_address(row)==address,'snapshot-unit-contiguity',hex(address),row['va'])
        if isinstance(encoding,str):
            opcode=b'\x0f\x83' if encoding.startswith('unsigned') else b'\x0f\x84'
            _require(len(raw)==6 and raw[:2]==opcode,'snapshot-unit-condition',[encoding,opcode.hex()],raw.hex())
            excluded[encoding]=hex(address+6+int.from_bytes(raw[2:],'little',signed=True))
        else:_require(raw==encoding,'snapshot-unit-instruction',encoding.hex(),raw.hex())
        if n==17:_require(address==skip_entry,'snapshot-unit-skip-join',hex(skip_entry),hex(address))
        address+=len(raw)
    _require(all(int(t,16) not in {_address(r) for r in rows[:18]} for t in excluded.values()),'snapshot-unit-excluded-targets','outside selected graph',excluded)
    return {'unitLoadGraphEntry':hex(start),'snapshotFlagEntry':hex(skip_entry),'selectedInstructionCount':18,
            'unsignedBoundsWidthBits':32,'indexSignExtension':'Int32 ESI to Int64 RAX',
            'elementReadWidthBytes':8,'elementAddressExpression':'arrayBase + payload + signExtend(Int32(ESI))*8',
            'anonymousRootChildOperands':dict(root_child),'anonymousElementSlots':dict(slots),
            'excludedTargets':excluded,'explicitCalls':[],'explicitMemoryStores':[],
            'actualManagedArrayOrUnitClassParityProved':False,'producerConsumerIndexJoinProved':False}


def check_snapshot_unit(index,count_proof,skip_proof,spec):
    _require(count_proof.get('claim')=='snapshotCountRequestNullHelperToProducerReturn' and skip_proof.get('claim')=='snapshotFlagSkipAppendContinuation',
             'snapshot-unit-dependencies','fresh count request and flag graph',[count_proof.get('claim'),skip_proof.get('claim')])
    body=index.body(spec['type'],spec['method']);_require(body.symbol==count_proof['symbol']==skip_proof['symbol'],'snapshot-unit-same-body','same producer',body.symbol)
    selected=NativeReferenceContext(index.image,index=index);owner,typ,offset=selected.field(spec['snapshotField'])
    _require(owner==spec['unitType'] and typ=='bool','snapshot-unit-flag-owner',[spec['unitType'],'bool'],[owner,typ])
    _require(count_proof['requestedMethodArgument']==owner,'snapshot-unit-count-formal-owner',owner,count_proof['requestedMethodArgument'])
    require_ordinary_field(selected,spec['snapshotField'],'bool','snapshot.unit.flag')
    start=int(skip_proof['loopTarget'],16);matches=[n for n,r in enumerate(body.rows) if _address(r)==start]
    _require(len(matches)==1,'snapshot-unit-loop-target','one complete loop instruction',matches)
    proof=check_unit_program(body.rows[matches[0]:],start=start,skip_entry=int(skip_proof['skipEntry'],16),flag_offset=offset,
        root_child=count_proof['anonymousRootChildOperands'],slots=spec['anonymousElementSlots'])
    return {**proof,'symbol':body.symbol,'claim':'snapshotRawIndexedUnitPointerToFlag',
            'boundary':'At the exact checked flag graph loop target, the same anonymous action-root/child displacements used by the count request feed a raw carrier. Nonnull carrier/array and two unsigned Int32 bounds precede sign extension of ESI and an exact eight-byte element read into RBX; nonnull RBX reaches the same named snapshot-flag offset checked by the fresh skip graph. This selected path makes no calls or explicit stores. With nonnegative Int32 carrier/array bounds and valid nonwrapping storage, its address is arrayBase+payload+index*8. Valid live action/unit roles and matching class/ABI remain conditions: anonymous slots do not name List fields, certify managed array layout or prove that loaded pointers are DamageUnit instances. Same-address/root continuity requires no intervening mutation; nonnull count semantics, complete loop, cache order, actual consumer index equality and final output remain unresolved.'}
