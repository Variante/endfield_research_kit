"""Guarded halving candidate and helper calls; success is not the AL result."""
from __future__ import annotations
from .descriptor_cache_lookup_control import _complete_graph,_slice,_at
from .descriptor_cache_insertion_control import _rip_operation,_signed_negative
from .owned_partition import rip_load


def validate_descriptor_cache_rebuild_request(rows,*,image_base,function,labels,globals,calls):
    base=image_base;edges,frames,checked_calls,stores=_complete_graph(rows,base,function)
    g=_slice(rows,base,[function['codeWindows'][0]['startRva'],function['codeWindows'][-1]['endRva']])
    g.labels={k:base+v for k,v in labels.items()}
    g.take('push rbx','sub rsp, 0x90');rip_load(g,'rcx',base+globals['storedCount'])
    g.take('xor bl, bl',f'sub rcx, qword [rip => 0x{base+globals["auxiliaryCount"]:x}]')
    rip_load(g,'rax',base+globals['threshold']);g.take('test rax, rax');g.branch('je','finish')
    g.take('cmp rcx, rax');g.branch('jae','finish');rip_load(g,'r8',base+globals['capacity'])
    g.take('cmp r8, 0x20');g.branch('jbe','finish')
    g.take('shr r8, 0x1','mov ebx, 0x1','cmp r8, 0x20');g.branch('jbe','build')
    g.take('xorps xmm1, xmm1','test rcx, rcx');_signed_negative(g,'unsignedCount')
    g.take('cvtsi2ss xmm1, rcx');g.branch('jmp','capacityFloat')
    _at(g,'unsignedCount');g.take('mov rax, rcx','and rcx, rbx','shr rax, 0x1','or rax, rcx','cvtsi2ss xmm1, rax','addss xmm1, xmm1')
    _at(g,'capacityFloat');g.take('xorps xmm0, xmm0','test r8, r8');_signed_negative(g,'unsignedCapacity')
    g.take('cvtsi2ss xmm0, r8');g.branch('jmp','scale')
    _at(g,'unsignedCapacity');g.take('mov rcx, r8','mov rax, r8','shr rcx, 0x1','and rax, rbx','or rcx, rax','cvtsi2ss xmm0, rcx','addss xmm0, xmm0')
    _at(g,'scale');_rip_operation(g,bytes.fromhex('f30f5905'),base+globals['floatFactor'])
    g.take('comiss xmm0, xmm1');g.branch('jbe','build')
    g.take('shr r8, 0x1','cmp r8, 0x20');g.branch('ja','capacityFloat')
    _at(g,'build');g.take('lea rcx, [rsp+0x20]');g.call(base+calls['replacement'])
    g.take('lea rdx, [rsp+0x20]');g.call(base+calls['publication'])
    g.take('lea rcx, [rsp+0x20]');g.call(base+calls['cleanup'])
    _at(g,'finish');r=g.take(f'mov byte [rip => 0x{base+globals["requestFlag"]:x}], 0x0')
    raw=bytes.fromhex(r['bytes'])
    if len(raw)!=7 or raw[:2]!=b'\xc6\x05' or raw[-1]!=0 or int(r['va'],16)+7+int.from_bytes(raw[2:6],'little',signed=True)!=base+globals['requestFlag']:
        g.fail('request-byte-clear',globals['requestFlag'],r)
    g.take('mov al, bl','add rsp, 0x90','pop rbx','ret');g.finish()
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,'calls':checked_calls,
        'explicitStores':stores,'frameStates':frames,'unsignedDifferenceSource':'storedCount minus auxiliaryCount modulo 64 bits',
        'requiredGuardConditions':['nonzero threshold','unsigned difference below threshold','initial capacity greater than 32'],
        'firstCandidateShiftBits':1,'candidateAtMost32SkipsFloatLoop':True,'candidateMinimum32UnconditionallyProved':False,
        'temporaryRspOffset':32,'helperSequence':['replacement','publication','cleanup'],
        'normalReturnAl':{'guardExit':0,'helperSequenceNormallyReturns':1},'fullRaxBooleanProved':False,
        'normalReturnClearsRequestByte':True,'returnedOneProvesSuccessfulRebuild':False,
        'floatingSelectionPolicyProved':False,'helperEffectsFullyProved':False,'runtimeExecutionKnown':False,
        'conditions':'Readable coherent globals, valid disjoint temporary/frame storage and normally returning Win64 nonvolatile/stack-preserving callees. AL records the selected path, not allocation/migration/cleanup success; FP policy and live side effects remain separate obligations.'}
