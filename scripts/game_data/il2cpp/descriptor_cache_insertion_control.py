"""Complete anonymous cache insertion graph and selected field/write flows."""
from __future__ import annotations
from .register_rotates import decode_rotate_instructions
from .scalar_double_memory import decode_scalar_double_memory_move
from .descriptor_cache_lookup_control import _complete_graph,_slice,_at
from .owned_partition import rip_load
from .field_construction_control import _lea
from .initializer_control import control_transfer


def decode_insertion_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            decoded=decode_scalar_double_memory_move(raw,offset,at)
            return decoded if decoded is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_rotate_instructions(Fallback(),data,start_va)


def _rip_operation(g,prefix,target):
    r=g.row();raw=bytes.fromhex(r['bytes']);at=int(r['va'],16)
    if len(raw)!=len(prefix)+4 or raw[:len(prefix)]!=prefix or at+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)!=target:
        g.fail('selected-rip-operation',(prefix.hex(),target),r)


def _signed_negative(g,label):
    r=g.row();flow=control_transfer(r)
    if flow.get('kind')!='conditional' or flow.get('conditionCode')!=8:g.fail('branch-predicate','SF=1',r)
    g.edges.append((flow['target'],label,r))


def validate_descriptor_cache_insertion_control(rows,*,image_base,function,segments,labels,globals,calls,probe):
    base=image_base
    admitted={int(r['va'],16) for r in rows for a,b in segments.values() if base+a<=int(r['va'],16)<base+b}
    if admitted!={int(r['va'],16) for r in rows}:raise ValueError('descriptorCacheInsertion.semantic-program-coverage')
    edges,frames,checked_calls,stores=_complete_graph(rows,base,function)
    if not {'r9','r10','r11'}<=set(probe['preservedRegisters']) or probe['memoryWrites']!=0:
        raise ValueError('descriptorCacheInsertion.probe-effects-not-joined')
    g=_slice(rows,base,segments['primary']);g.labels={k:base+v for k,v in labels.items()}
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi',
        'push rdi','push r12','push r13','push r14','push r15','sub rsp, 0xb0','mov rdi, r8','mov r14, rdx')
    g.take(f'cmp byte [rip => 0x{base+globals["initializationFlag"]:x}], 0x0');g.branch('jne','initialization')
    _at(g,'loadCount');rip_load(g,'rbx',base+globals['storedCount']);g.take('cmp rbx, -0x2');g.branch('jae','countTrap')
    _lea(g,'r15',rip=base+globals['table']);rip_load(g,'rsi',base+globals['capacity'])
    g.take('cmp rsi, 0x4');g.branch('jb','growth')
    g.take('lea rax, [rbx+0x1]',f'cmp rax, qword [rip => 0x{base+globals["table"]:x}]');g.branch('ja','growth')
    _at(g,'hash');g.take('xor r10d, r10d','lea r11, [rsi-0x1]','mov rdx, [rdi+0x8]',
        'mov rax, [rdx]','mov ecx, [rax+0x48]','mov rax, [rdx+0x8]','shr rax, 0x3',
        'add rcx, rax','imul r9, rcx, 0x1cfaa2db','mov rax, [rdx+0x10]','shr rax, 0x3',
        'add r9, rax','mov r12, -0x1','mov r8, rdx')
    rip_load(g,'r15',base+globals['begin']);rip_load(g,'r13',base+globals['sentinelTriple'])
    rip_load(g,'rsi',base+globals['marker']);rip_load(g,'rbp',base+globals['auxiliaryCount'])
    _at(g,'mask');g.take('and r9, r11','mov rax, r9','add rax, rax','cmp esi, dword [r15+rax*8]');g.branch('jne','afterSentinel')
    g.take('test esi, esi');g.branch('jne','selectNewSlot')
    g.take('mov rcx, [r15+rax*8+0x8]','mov rax, [rcx]','cmp qword [r13], rax');g.branch('jne','afterSentinel')
    g.take('mov rax, [rcx+0x8]','cmp qword [r13+0x8], rax');g.branch('jne','sentinelMismatch')
    g.take('mov rax, [rcx+0x10]','cmp qword [r13+0x10], rax');g.branch('jne','sentinelMismatch')
    g.take('mov al, 0x1');_at(g,'sentinelTest');g.take('test al, al');g.branch('jne','selectNewSlot')
    _at(g,'afterSentinel');g.take('test rbp, rbp');g.branch('jne','probeCandidate')
    _at(g,'matching');g.take('mov rcx, r9','add rcx, rcx','mov eax, [r15+rcx*8]','cmp dword [rdi], eax');g.branch('je','markerMatched')
    _at(g,'advance');g.take('inc r10','add r9, r10');g.branch('jmp','mask')
    _at(g,'markerMatched');g.take('cmp dword [rdi], 0x0');g.branch('jne','chooseExisting')
    g.take('mov rdx, [r15+rcx*8+0x8]','mov rax, [rdx]','cmp qword [r8], rax');g.branch('jne','advance')
    g.take('mov rax, [rdx+0x8]','cmp qword [r8+0x8], rax');g.branch('jne','queryMismatch')
    g.take('mov rax, [rdx+0x10]','cmp qword [r8+0x10], rax');g.branch('jne','queryMismatch')
    g.take('mov al, 0x1');_at(g,'queryTest');g.take('test al, al');g.branch('je','advance')
    _at(g,'chooseExisting');g.take('mov r12, -0x1','cmp r9, r12');g.branch('je','newCapacityCheck');g.branch('jmp','existingOutput')
    _at(g,'selectNewSlot');g.take('cmp r12, -0x1');g.branch('jne','newCapacityCheck');g.take('mov r12, r9')
    _at(g,'newCapacityCheck');g.take('mov rax, rbx','sub rax, rbp','mov rcx, 0xfffffffffffffff','cmp rax, rcx');g.branch('jae','sizeTrap')
    g.take('test rbp, rbp');g.branch('jne','probeReplacement')
    _at(g,'incrementCount');g.take('inc rbx');_rip_operation(g,bytes.fromhex('48891d'),base+globals['storedCount'])
    _at(g,'writeEntry');g.take('mov rcx, r12','add rcx, rcx','mov eax, [rdi]','mov [r15+rcx*8], eax',
        'mov rax, [rdi+0x8]','mov [r15+rcx*8+0x8], rax')
    _lea(g,'rax',rip=base+globals['table']);g.take('mov [rsp+0x20], rax','shl r12, 0x4',
        f'add r12, qword [rip => 0x{base+globals["begin"]:x}]','mov [rsp+0x28], r12')
    rip_load(g,'rax',base+globals['capacity']);g.take('shl rax, 0x4',f'add rax, qword [rip => 0x{base+globals["begin"]:x}]','mov cl, 0x1')
    _at(g,'output');g.take('mov [rsp+0x30], rax')
    for text,direction,width in [('movsd xmm0, [rsp+0x30]','load',8),('movsd [rsp+0x30], xmm0','store',8),
            ('movups xmm1, [rsp+0x20]','load',16),('movq [r14], xmm1','store',8)]:
        r=g.take(text);f=r.get('memoryOperation',{})
        if (f.get('direction'),f.get('memoryBytes'))!=(direction,width):g.fail('output-transfer-width',(direction,width),r)
    r=g.take('psrldq xmm1, 0x8')
    if bytes.fromhex(r['bytes'])!=bytes.fromhex('66 0f 73 d9 08'):g.fail('qword-vector-shift',8,r)
    r=g.take('movq [r14+0x8], xmm1')
    if r.get('memoryOperation',{}).get('memoryBytes')!=8:g.fail('current-pointer-transfer-width',8,r)
    g.take('mov rax, [rsp+0x30]','mov [r14+0x10], rax','mov [r14+0x18], cl','mov rax, r14',
        'lea r11, [rsp+0xb0]','mov rbx, [r11+0x30]','mov rbp, [r11+0x38]','mov rsi, [r11+0x40]',
        'mov rsp, r11','pop r15','pop r14','pop r13','pop r12','pop rdi','ret')
    _at(g,'sentinelMismatch');g.take('xor al, al');g.branch('jmp','sentinelTest')
    _at(g,'queryMismatch');g.take('xor al, al');g.branch('jmp','queryTest')
    _at(g,'growth');g.take('lea rdx, [rbx+0x1]','xor r8d, r8d','mov rcx, r15');g.call(base+calls['capacityCandidate'])
    g.take('cmp rax, rsi');g.branch('jbe','hash')
    g.take('mov rdx, rbx');rip_load(g,'rbp',base+globals['auxiliaryCount'])
    g.take('sub rdx, rbp','inc rdx','mov r8, rsi');g.call(base+calls['capacityCandidate'])
    g.take('mov rsi, rax','mov rcx, rbp','shr rcx, 0x2','mov rdx, rbx','sub rdx, rcx','inc rdx','xor r8d, r8d','mov rcx, r15')
    g.call(base+calls['capacityCandidate']);g.take('cmp rsi, rax');g.branch('jb','floatGrowth')
    _at(g,'buildReplacement');g.take('mov r8, rsi','lea rcx, [rsp+0x40]');g.call(base+calls['replacementCandidate'])
    g.take('lea rdx, [rsp+0x40]');g.call(base+calls['publishCandidate']);g.take('nop','mov rcx, [rsp+0xa0]','test rcx, rcx');g.branch('je','reloadAfterGrowth')
    g.call(base+calls['releaseCandidate']);g.take('nop')
    _at(g,'reloadAfterGrowth');rip_load(g,'rsi',base+globals['capacity']);rip_load(g,'rbx',base+globals['storedCount']);g.branch('jmp','hash');g.finish()
    g=_slice(rows,base,segments['cold']);g.labels={k:base+v for k,v in labels.items()}
    _at(g,'initialization');g.call(base+calls['initializationCandidate']);g.take('nop');g.branch('jmp','loadCount')
    _at(g,'countTrap');g.take('mov ecx, 0xffffffff');g.call(base+calls['errorCandidate']);g.take('int3')
    _at(g,'floatGrowth');g.take('mov rax, 0x7fffffffffffffff','cmp rsi, rax');g.branch('jae','buildReplacement')
    g.take('lea rcx, [rsi+rsi*1]','xorps xmm0, xmm0','test rcx, rcx');_signed_negative(g,'unsignedFloat')
    g.take('cvtsi2ss xmm0, rcx');g.branch('jmp','floatScale')
    _at(g,'unsignedFloat');g.take('mov rax, rcx','shr rax, 0x1','and ecx, 0x1','or rax, rcx','cvtsi2ss xmm0, rax','addss xmm0, xmm0')
    _at(g,'floatScale');_rip_operation(g,bytes.fromhex('f30f5905'),base+globals['floatFactor'])
    g.take('xor ecx, ecx');_rip_operation(g,bytes.fromhex('f30f100d'),base+globals['floatThreshold'])
    g.take('comiss xmm0, xmm1');g.branch('jb','floatToInteger')
    g.take('subss xmm0, xmm1','comiss xmm0, xmm1');g.branch('jae','floatToInteger')
    g.take('mov rax, 0x8000000000000000','mov rcx, rax')
    _at(g,'floatToInteger');g.take('cvttss2si rax, xmm0','add rax, rcx','sub rbx, rbp','inc rbx','cmp rbx, rax');g.branch('jb','buildReplacement')
    g.take('add rsi, rsi');g.branch('jmp','buildReplacement')
    _at(g,'probeCandidate');g.take('mov r8, r9','shl r8, 0x4','add r8, r15');_lea(g,'rdx',rip=base+globals['probeData'])
    g.call(base+calls['probe']);g.take('mov r8, [rdi+0x8]','test al, al');g.branch('je','matching')
    g.take('cmp r12, -0x1');g.branch('jne','advance');g.take('mov r12, r9');g.branch('jmp','advance')
    _at(g,'existingOutput');_lea(g,'rax',rip=base+globals['table'])
    g.take('mov [rsp+0x20], rax','shl r9, 0x4','add r9, r15','mov [rsp+0x28], r9')
    rip_load(g,'rax',base+globals['capacity']);g.take('shl rax, 0x4','add rax, r15','xor cl, cl');g.branch('jmp','output')
    _at(g,'sizeTrap');g.take('mov ecx, 0xffffffff');g.call(base+calls['errorCandidate']);g.take('int3')
    _at(g,'probeReplacement');g.take('mov r8, r12','shl r8, 0x4','add r8, r15');_lea(g,'rdx',rip=base+globals['probeData'])
    g.call(base+calls['probe']);g.take('test al, al');g.branch('je','incrementCount')
    g.take('dec rbp');_rip_operation(g,bytes.fromhex('48892d'),base+globals['auxiliaryCount']);g.branch('jmp','writeEntry');g.finish()
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,
        'inputWrapper':'entry R8 saved in RDI','outputInputAndReturn':'entry RDX saved in R14',
        'entryStrideBytes':16,'writtenEntryFields':[{'offset':0,'bytes':4,'source':'fresh wrapper marker DWORD'},
            {'offset':8,'bytes':8,'source':'fresh wrapper value pointer'}],
        'outputFields':{'table':0,'current':8,'end':16,'insertedByte':24},'newPathInsertedByte':1,'existingPathInsertedByte':0,
        'newCountOrAuxiliaryCounterStoreBeforeEntryWrite':True,'probePreservesLoopRegisters':True,
        'probeReloadsQueryPointerAfterCall':True,'scalarEndCopyBytes':8,'vectorTableCurrentCopyBytes':16,
        'floatingGrowthNumericPolicyProved':False,'growthHelperEffectsProved':False,'terminationProved':False,
        'existingPathAvoidsLocalEntryOverwrite':True,'callerAdoptsExistingEntryValueProved':False,
        'allocationValuePointerSurvivesOpaqueCallsProved':False,'runtimeExecutionKnown':False,
        'calls':checked_calls,'explicitStores':stores,'frameStates':frames,
        'conditions':'Readable coherent wrapper/triples, valid table/index/capacity storage and disjoint writable entry/output/frame regions. Normal Win64 nonvolatile/stack-preserving opaque callees; the proved probe has separate exact register effects. Callback/global mutations, resize/initialization effects, FP environment, bounds and later pointer/content stability remain separate obligations.'}
