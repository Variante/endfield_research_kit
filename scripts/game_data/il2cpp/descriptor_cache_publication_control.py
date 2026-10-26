"""Complete publication control and selected bidirectional field transfers.

The record's whole packed block is not claimed as an exact swap: selected
bytes return through a partially written stack vector, and thresholds change.
"""
from __future__ import annotations
from .descriptor_cache_insertion_control import _rip_operation,_signed_negative
from .descriptor_cache_lookup_control import _complete_graph,_slice,_at
from .owned_partition import rip_load


def validate_descriptor_cache_publication_control(rows,*,image_base,function,labels,globals):
    base=image_base;edges,frames,calls,stores=_complete_graph(rows,base,function)
    if calls:raise ValueError('descriptorCachePublication.unreviewed-call')
    for row in rows:
        head=row['text'].split(' ')[0]
        if head in ('movsd','movups','movaps'):
            f=row.get('memoryOperation',{});expected=8 if head=='movsd' else 16
            if f.get('memoryBytes')!=expected:raise ValueError('descriptorCachePublication.memory-transfer-width:'+row['va'])
    g=_slice(rows,base,[function['codeWindows'][0]['startRva'],function['codeWindows'][-1]['endRva']])
    g.labels={k:base+v for k,v in labels.items()}
    g.take('sub rsp, 0x28','movups xmm0, [rdx]','mov r8, rdx')
    _rip_operation(g,bytes.fromhex('0f2815'),base+globals['objectBase'])
    _rip_operation(g,bytes.fromhex('0f281d'),base+globals['objectBase']+16)
    _rip_operation(g,bytes.fromhex('0f2905'),base+globals['objectBase'])
    g.take('movups xmm1, [rdx+0x10]');_rip_operation(g,bytes.fromhex('0f290d'),base+globals['objectBase']+16)
    g.take('movups [rdx], xmm2','movups [rdx+0x10], xmm3')
    _rip_operation(g,bytes.fromhex('0fb605'),base+globals['objectBase']+33)
    g.take('movups xmm0, [rdx+0x20]','mov [rsp+0x1], al')
    _rip_operation(g,bytes.fromhex('8b05'),base+globals['objectBase']+40)
    _rip_operation(g,bytes.fromhex('0f2905'),base+globals['objectBase']+32)
    g.take('movsd xmm1, [rdx+0x30]','mov [rsp+0x8], eax');rip_load(g,'rax',base+globals['objectBase']+48)
    g.take('movups xmm0, [rsp]','mov [rsp+0x10], rax')
    _rip_operation(g,bytes.fromhex('f20f110d'),base+globals['objectBase']+48)
    g.take('movsd xmm1, [rsp+0x10]','movups [rdx+0x20], xmm0','movsd [rdx+0x30], xmm1','xorps xmm1, xmm1')
    for offset in (56,64,72):
        g.take(f'mov rax, [rdx+0x{offset:x}]');rip_load(g,'rcx',base+globals['objectBase']+offset)
        _rip_operation(g,bytes.fromhex('488905'),base+globals['objectBase']+offset)
        g.take(f'mov [rdx+0x{offset:x}], rcx')
    g.take('mov eax, [r8+0x50]');_rip_operation(g,bytes.fromhex('8b0d'),base+globals['objectBase']+80)
    rip_load(g,'rdx',base+globals['objectBase']+88)
    _rip_operation(g,bytes.fromhex('8905'),base+globals['objectBase']+80)
    g.take('mov rax, [r8+0x58]');_rip_operation(g,bytes.fromhex('488905'),base+globals['objectBase']+88)
    g.take('mov [r8+0x50], ecx','mov [r8+0x58], rdx','mov rax, [r8+0x60]')
    rip_load(g,'rcx',base+globals['objectBase']+96);_rip_operation(g,bytes.fromhex('488905'),base+globals['objectBase']+96)
    g.take('mov [r8+0x60], rcx');rip_load(g,'rdx',base+globals['objectBase']+72)
    g.take('test rdx, rdx');_signed_negative(g,'globalFirstUnsigned')
    g.take('cvtsi2ss xmm1, rdx');_at(g,'globalFirstScale')
    _rip_operation(g,bytes.fromhex('f30f590d'),base+globals['objectBase']+16)
    g.take('xor ecx, ecx','mov r9, 0x8000000000000000');_rip_operation(g,bytes.fromhex('f30f1005'),base+globals['floatThreshold'])
    g.take('comiss xmm1, xmm0');g.branch('jb','globalFirstConvert')
    g.take('subss xmm1, xmm0','comiss xmm1, xmm0');g.branch('jae','globalFirstConvert');g.take('mov rcx, r9')
    _at(g,'globalFirstConvert');g.take('cvttss2si rax, xmm1','xorps xmm1, xmm1','add rax, rcx')
    _rip_operation(g,bytes.fromhex('488905'),base+globals['objectBase'])
    g.take('test rdx, rdx');_signed_negative(g,'globalSecondUnsigned');g.take('cvtsi2ss xmm1, rdx')
    _at(g,'globalSecondScale');_rip_operation(g,bytes.fromhex('f30f590d'),base+globals['objectBase']+20)
    g.take('xor ecx, ecx','comiss xmm1, xmm0');g.branch('jb','globalSecondConvert')
    g.take('subss xmm1, xmm0','comiss xmm1, xmm0');g.branch('jae','globalSecondConvert');g.take('mov rcx, r9')
    _at(g,'globalSecondConvert');g.take('cvttss2si rax, xmm1')
    r=g.take(f'mov byte [rip => 0x{base+globals["objectBase"]+24:x}], 0x0')
    raw=bytes.fromhex(r['bytes'])
    if len(raw)!=7 or raw[:2]!=b'\xc6\x05' or raw[-1]!=0 or int(r['va'],16)+7+int.from_bytes(raw[2:6],'little',signed=True)!=base+globals['objectBase']+24:
        g.fail('global-byte-clear',globals['objectBase']+24,r)
    g.take('xorps xmm1, xmm1','add rax, rcx');_rip_operation(g,bytes.fromhex('488905'),base+globals['objectBase']+8)
    g.take('mov rdx, [r8+0x48]','test rdx, rdx');_signed_negative(g,'recordFirstUnsigned');g.take('cvtsi2ss xmm1, rdx')
    _at(g,'recordFirstScale');g.take('mulss xmm1, [r8+0x10]','xor ecx, ecx','comiss xmm1, xmm0');g.branch('jb','recordFirstConvert')
    g.take('subss xmm1, xmm0','comiss xmm1, xmm0');g.branch('jae','recordFirstConvert');g.take('mov rcx, r9')
    _at(g,'recordFirstConvert');g.take('cvttss2si rax, xmm1','xorps xmm1, xmm1','add rax, rcx','mov [r8], rax','test rdx, rdx')
    _signed_negative(g,'recordSecondUnsigned');g.take('cvtsi2ss xmm1, rdx')
    _at(g,'recordSecondScale');g.take('mulss xmm1, [r8+0x14]','xor ecx, ecx','comiss xmm1, xmm0');g.branch('jb','recordSecondConvert')
    g.take('subss xmm1, xmm0','comiss xmm1, xmm0');g.branch('jae','recordSecondConvert');g.take('mov rcx, r9')
    _at(g,'recordSecondConvert');g.take('cvttss2si rax, xmm1','mov byte [r8+0x18], 0x0','add rax, rcx','mov [r8+0x8], rax','add rsp, 0x28','ret')
    _at(g,'globalFirstUnsigned');g.take('mov rax, rdx','mov rcx, rdx','shr rcx, 0x1','and eax, 0x1','or rcx, rax','cvtsi2ss xmm1, rcx','addss xmm1, xmm1');g.branch('jmp','globalFirstScale')
    _at(g,'globalSecondUnsigned');g.take('mov rax, rdx','and edx, 0x1','shr rax, 0x1','or rax, rdx','cvtsi2ss xmm1, rax','addss xmm1, xmm1');g.branch('jmp','globalSecondScale')
    _at(g,'recordFirstUnsigned');g.take('mov rax, rdx','mov rcx, rdx','shr rcx, 0x1','and eax, 0x1','or rcx, rax','cvtsi2ss xmm1, rcx','addss xmm1, xmm1');g.branch('jmp','recordFirstScale')
    _at(g,'recordSecondUnsigned');g.take('mov rax, rdx','and edx, 0x1','shr rax, 0x1','or rax, rdx','cvtsi2ss xmm1, rax','addss xmm1, xmm1');g.branch('jmp','recordSecondScale');g.finish()
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,'calls':calls,'explicitStores':stores,
        'frameStates':frames,'recordInput':'entry RDX saved in R8','globalObjectBaseRva':globals['objectBase'],
        'selectedBidirectionalFields':[{'offset':33,'bytes':1},{'offset':40,'bytes':4},{'offset':48,'bytes':8},
            {'offset':56,'bytes':8},{'offset':64,'bytes':8},{'offset':72,'bytes':8},{'offset':80,'bytes':4},
            {'offset':88,'bytes':8},{'offset':96,'bytes':8}],
        'packedBlockOffsetsInitiallyExchanged':[0,16],'thresholdOffsetsLaterOverwritten':[0,8],
        'globalAndRecordByte24Cleared':True,'recordBlock32KnownOldGlobalByteRanges':[[33,34],[40,44]],
        'recordBlock32OtherBytesFromUnmodelledEntryStack':True,'wholeObjectExactSwapProved':False,
        'numericThresholdPolicyProved':False,'atomicPublicationProved':False,'runtimeExecutionKnown':False,
        'conditions':'Valid disjoint record/global/frame storage and coherent source fields. Selected transfers are separate reads/writes; FP environment, concurrent observations and unmodelled stack bytes remain outside their field-value claim.'}
