"""Complete conditional reference-cache hit and miss program.

The miss producer and tail notification remain opaque selected callees. A hit
contains no call and performs no explicit object-field write. This does not
prove synchronization, the producer's returned object or notification effects.
"""
from __future__ import annotations

import hashlib


def prove_lazy_reference_cache(raw: bytes, *, entry_va: int, producer_va: int,
        notification_va: int, field_offset: int) -> dict:
    if (not isinstance(raw,bytes) or type(field_offset) is not int or not 0<field_offset<128
            or any(type(v) is not int or not 0<v<1<<64 for v in (entry_va,producer_va,notification_va))
            or entry_va+len(raw)>=1<<64):
        raise ValueError('lazy-reference-cache.input: exact bytes, bounded addresses and positive field offset required')
    rows=[];offset=0
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:raise ValueError(f'lazy-reference-cache.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def branch(op,target,meaning,short=False):
        nonlocal offset
        prefix=bytes.fromhex(op);size=len(prefix)+(1 if short else 4);actual=raw[offset:offset+size]
        if len(actual)!=size or actual[:len(prefix)]!=prefix:
            raise ValueError(f'lazy-reference-cache.branch-opcode: offset={offset} expected={op} actual={actual.hex().upper()}')
        destination=entry_va+offset+size+int.from_bytes(actual[len(prefix):],'little',signed=True)
        if destination!=target:raise ValueError(f'lazy-reference-cache.branch-target: offset={offset} expected={target:#x} actual={destination:#x}')
        rows.append({'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=size
    field=f'{field_offset:02X}'
    literal('4053','push incoming rbx')
    literal('4883EC20','allocate 32-byte call frame')
    literal('488379'+field+'00','compare opaque reference qword at rcx+field with zero')
    literal('488BD9','save incoming receiver in nonvolatile rbx')
    branch('75',entry_va+41,'nonzero reference enters no-call/no-field-write hit return',True)
    literal('33D2','zero optional producer context in full rdx')
    branch('E8',producer_va,'call selected producer with original receiver rcx')
    literal('488D4B'+field,'rcx = address of selected receiver reference slot')
    literal('488943'+field,'store returned rax qword into selected reference slot')
    literal('4883C420','release local frame on miss')
    literal('5B','restore incoming rbx and original entry rsp on miss')
    branch('E9',notification_va,'tail notify with slot address and original return address')
    literal('4883C420','release local frame on hit')
    literal('5B','restore incoming rbx and original entry rsp on hit')
    literal('C3','hit returns without a call or explicit receiver-field write')
    if offset!=len(raw):raise ValueError(f'lazy-reference-cache.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-reference-cache-hit-and-miss-program-proved','programBytes':len(raw),
        'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,'receiverRegister':'rcx',
        'fieldOffset':field_offset,'fieldReadBits':64,'fieldWriteBits':64,
        'hitCondition':'selected field qword is nonzero','hitCalls':0,'hitExplicitReceiverFieldWrites':0,
        'missProducerArguments':{'rcx':'original receiver','rdx':'zero'},
        'missReferenceWriteSource':'producer return rax','missNotificationArgument':{'rcx':'receiver reference slot address'},
        'frame':{'rspFromEntryRsp':-40,'restoredRbx':True,'originalReturnAddressRetained':True},
        'producerReturnedObjectOrWritesProved':False,'notificationEffectsProved':False,
        'cachedContentsOrConcurrentStabilityProved':False,'runtimeExecutionKnown':False,
        'conditions':['Selected current complete bytes, receiver declaration and authenticated field/callee joins',
            'Valid readable receiver field and writable frame/slot; no incompatible alias or concurrent writes',
            'Producer returns normally, preserves Win64 nonvolatile rbx and required frame; notification has valid tail-call frame',
            'The hit conclusion concerns this complete program only; no synchronization or global absence of writers is inferred'],
        'evidenceBoundary':'Exact cache branch, call-free hit, producer arguments, returned-reference store, notification slot and restored-frame transfers. Producer/notification effects, cached contents and runtime stability are separate proofs.'}
