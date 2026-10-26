"""Connect zero initialization, positive bound and selected iteration counter edges."""
from __future__ import annotations
from scripts.game_data.damage_snapshot_cache_flow import _address,_require


def conditional_iteration_step(index,bound):
    _require(type(index) is int and type(bound) is int and 0<=index<bound<=0x7fffffff,
             'snapshot-iteration-positive-range','0 <= index < positive Int32 bound',[index,bound])
    result=index+1
    return {'index':index,'nextIndex':result,'continueSignedLessThan':result<bound,'int32Overflow':False}


def check_iteration_connections(rows,counter,count,unit,skip,append,operands):
    expected_claims=((counter,'snapshotResetZeroToCounterInitialization'),(count,'snapshotCountRequestNullHelperToProducerReturn'),
                     (unit,'snapshotRawIndexedUnitPointerToFlag'),(skip,'snapshotFlagSkipAppendContinuation'),(append,'snapshotSimpleValueToAppendRequest'))
    _require(all(p.get('claim')==name for p,name in expected_claims),'snapshot-iteration-proof-groups','fresh separate path proofs',[p.get('claim') for p,_ in expected_claims])
    _require(len({p['symbol'] for p,_ in expected_claims})==1,'snapshot-iteration-same-body','same selected producer',[p['symbol'] for p,_ in expected_claims])
    init=int(counter['counterInitialization'],16);call_start=int(count['callerEntry'],16);unit_start=int(unit['unitLoadGraphEntry'],16)
    matches=[n for n,r in enumerate(rows) if _address(r)==init]
    _require(len(matches)==1,'snapshot-iteration-init-boundary','complete initialization instruction',matches)
    n=matches[0];_require(bytes.fromhex(rows[n]['bytes'])==b'\x41\x8b\xf5','snapshot-iteration-zero-assignment','MOV ESI,R13D',rows[n]['bytes'])
    vector=operands['localVectorDisp8'];destination=operands['opaqueActionVectorDisp8']
    _require(all(type(x) is int and 0<=x<=127 for x in (vector,destination)),'snapshot-iteration-interim-operands','positive anonymous disp8',[vector,destination])
    expected=[b'\x48\x89\x44\x24'+bytes([vector]),b'\x0f\x10\x44\x24'+bytes([vector]),b'\x0f\x11\x47'+bytes([destination])]
    address=init+3
    for row,encoding in zip(rows[n+1:n+4],expected):
        raw=bytes.fromhex(row['bytes']);_require(_address(row)==address and raw==encoding,'snapshot-iteration-interim-instruction',[hex(address),encoding.hex()],[row['va'],raw.hex()]);address+=len(raw)
    _require(len(rows[n+1:n+4])==3 and address==call_start,'snapshot-iteration-count-entry-join',hex(call_start),hex(address))
    calls=[k for k,r in enumerate(rows) if _address(r)==call_start];_require(len(calls)==1,'snapshot-iteration-count-boundary','complete fresh caller entry',calls)
    last=rows[calls[0]+count['callerInstructionCount']-1];raw=bytes.fromhex(last['bytes'])
    _require(len(raw)==2 and raw[:1]==b'\x7e' and _address(last)+len(raw)==unit_start,
             'snapshot-iteration-positive-fallthrough','signed JLE false reaches fresh unit entry',[last['va'],raw.hex(),hex(unit_start)])
    _require(int(skip['loopTarget'],16)==unit_start and skip['iterationContinuation']==append['continuation'],
             'snapshot-iteration-transition-joins','same loop entry and increment continuation',[skip['loopTarget'],unit['unitLoadGraphEntry'],skip['iterationContinuation'],append['continuation']])
    _require(counter['counterInitialValue']==0 and counter['counterWriteWidthBits']==32 and skip['iterationIncrementWidthBits']==32,
             'snapshot-iteration-counter-width','zero Init32 and Inc32',[counter['counterInitialValue'],counter['counterWriteWidthBits'],skip['iterationIncrementWidthBits']])
    return {'counterInitialization':hex(init),'firstUnitReadEntry':hex(unit_start),'positiveBoundRegister':'r14d',
            'firstCounterValue':0,'counterRegister':'esi','interimInstructionCount':3,
            'selectedCounterModel':'For positive Int32 N and normally returning selected skip/simple paths, ESI starts at zero and increases by one until the signed comparison reaches N; excluded guards/branches invalidate this model.',
            'fullProducerAllBranchesProved':False,'cacheIndexEqualsCounterProved':False,'producerConsumerIndexJoinProved':False}


def check_snapshot_iteration(index,counter,count,unit,skip,append,spec):
    body=index.body(spec['type'],spec['method'])
    proof=check_iteration_connections(body.rows,counter,count,unit,skip,append,spec['anonymousInterimOperands'])
    _require(body.symbol==counter['symbol'],'snapshot-iteration-body','selected producer',body.symbol)
    return {**proof,'symbol':body.symbol,'claim':'snapshotZeroCounterPositiveBoundIterationConnections',
            'boundary':'The fresh zero counter assignment reaches the fresh count caller through exactly three complete instructions that do not write the counter. A positive ordinary Int32 count result selects its signed JLE fallthrough to the exact fresh unit-load entry. The fresh skip and selected simple-append continuations join the same 32-bit increment and signed backedge. Under normal Win64 nonvolatile RSI/R14 preservation, valid/noninterfering frame/storage, positive Int32 bound and every selected guard/simple path, the counter visits zero through bound-minus-one without Int32 overflow. These are conditional selected graph connections, not complete producer/all-branch or nonnull count semantics. Anonymous interim stores do not prove a field schema; cache positions, actual consumer index equality, live provider values and final damage remain open.'}
