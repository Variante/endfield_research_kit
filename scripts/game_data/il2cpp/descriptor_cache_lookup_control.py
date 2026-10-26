"""Complete triple-key probe control; no cache history or live selection claim."""
from __future__ import annotations
from .field_setup_control import _graph,_frames
from .initializer_control import control_transfer,memory_effect
from .owned_partition import BranchGrammar,rip_load
from .field_construction_control import _lea

LABEL='descriptorCacheLookupControl'


def _complete_graph(rows,base,function):
    f=dict(function);branches=[];calls=[];stores=[];returns=[];traps=[]
    for row in rows:
        at=int(row['va'],16);flow=control_transfer(row);kind=flow['kind']
        if kind in ('jump','conditional'):branches.append({'siteRva':at-base,**flow})
        elif kind in ('call','indirectCall','registerCall'):calls.append({'siteRva':at-base,**flow})
        elif kind=='return':returns.append(at-base)
        elif kind=='trap':traps.append(at-base)
        effect=memory_effect(row)
        if effect:stores.append({'siteRva':at-base,**effect})
    f.update(localBranches=branches,calls=calls,explicitStores=stores,returnRvas=returns,trapRvas=traps)
    edges,calls,stores=_graph(rows,base,f)
    return edges,_frames(rows,edges,base,f),calls,stores


def _slice(rows,base,window):
    a,b=(base+x for x in window)
    selected=[r for r in rows if a<=int(r['va'],16)<b]
    if not selected or int(selected[0]['va'],16)!=a or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes']))!=b:
        raise ValueError(LABEL+'.segment-extent')
    return BranchGrammar(selected,label=LABEL)


def _at(g,label):
    if g.cursor>=len(g.rows) or int(g.rows[g.cursor]['va'],16)!=g.labels[label]:
        g.fail('semantic-label:'+label,g.labels[label],g.rows[g.cursor:] or 'end')


def validate_descriptor_cache_lookup_control(rows,*,image_base,function,segments,labels,globals,calls):
    base=image_base
    admitted=set()
    for window in segments.values():
        a,b=(base+x for x in window)
        admitted.update(int(r['va'],16) for r in rows if a<=int(r['va'],16)<b)
    if admitted!={int(r['va'],16) for r in rows}:raise ValueError(LABEL+'.semantic-program-coverage')
    edges,frames,checked_calls,stores=_complete_graph(rows,base,function)
    if any(base+rva not in edges for rva in labels.values()):raise ValueError(LABEL+'.label-boundary')
    g=_slice(rows,base,segments['primary']);g.labels={k:base+v for k,v in labels.items()}
    g.take('mov [rsp+0x8], rcx','push rbx','push rbp','push r15','sub rsp, 0x30')
    rip_load(g,'rbp',base+globals['auxiliaryCount']);g.take('mov rbx, r8')
    g.take(f'cmp qword [rip => 0x{base+globals["storedCount"]:x}], rbp','mov r15, rdx');g.branch('je','empty')
    g.take('mov rdx, [r8+0x8]','xor r10d, r10d','mov [rsp+0x58], rsi')
    r=g.row()
    # This is an observed DWORD marker, without assigning a container enum name.
    expected=base+globals['marker']
    fact=r.get('memoryOperation',{});a=fact.get('address',{})
    if (fact.get('direction'),fact.get('register'),fact.get('registerBits'),a.get('absoluteAddress'))!=('load','esi',32,expected):
        g.fail('marker-load',expected,r)
    g.take('mov [rsp+0x60], rdi','mov rax, [rdx]');rip_load(g,'rdi',base+globals['begin'])
    g.take('mov [rsp+0x68], r12');rip_load(g,'r12',base+globals['sentinelTriple'])
    g.take('mov ecx, [rax+0x48]','mov rax, [rdx+0x8]','shr rax, 0x3','add rcx, rax',
        'mov [rsp+0x28], r13','mov rax, [rdx+0x10]','mov r13, rdx','imul r9, rcx, 0x1cfaa2db',
        'mov [rsp+0x20], r14')
    rip_load(g,'r14',base+globals['capacity'])
    g.take('shr rax, 0x3','add r9, rax','mov qword [rsp+0x50], -0x1','lea r11, [r14-0x1]')
    _at(g,'mask');g.take('and r9, r11','mov rax, r9','add rax, rax','cmp esi, dword [rdi+rax*8]');g.branch('jne','afterSentinel')
    g.take('test esi, esi');g.branch('jne','miss')
    g.take('mov rcx, [rdi+rax*8+0x8]','mov rax, [rcx]','cmp qword [r12], rax');g.branch('jne','afterSentinel')
    g.take('mov rax, [rcx+0x8]','cmp qword [r12+0x8], rax');g.branch('jne','sentinelMismatch')
    g.take('mov rax, [rcx+0x10]','cmp qword [r12+0x10], rax');g.branch('jne','sentinelMismatch')
    g.take('mov al, 0x1');_at(g,'sentinelTest');g.take('test al, al');g.branch('jne','miss')
    _at(g,'afterSentinel');g.take('test rbp, rbp');g.branch('jne','coldProbe')
    _at(g,'matching')
    g.take('mov rcx, r9','add rcx, rcx','mov eax, [rdi+rcx*8]','cmp dword [rbx], eax');g.branch('jne','advance')
    g.take('cmp dword [rbx], 0x0');g.branch('jne','choose')
    g.take('mov rdx, [rdi+rcx*8+0x8]','mov rax, [rdx]','cmp qword [r13], rax');g.branch('jne','advance')
    g.take('mov rax, [rdx+0x8]','cmp qword [r13+0x8], rax');g.branch('jne','queryMismatch')
    g.take('mov rax, [rdx+0x10]','cmp qword [r13+0x10], rax');g.branch('jne','queryMismatch')
    g.take('mov al, 0x1');_at(g,'queryTest');g.take('test al, al');g.branch('jne','choose')
    _at(g,'advance');g.take('inc r10','add r9, r10');g.branch('jmp','mask')
    _at(g,'choose');g.take('cmp r9, -0x1');g.branch('jne','hit')
    _at(g,'miss')
    g.take('mov rax, r14','shl r14, 0x4','shl rax, 0x4','add rax, rdi','add r14, rdi',
        'mov [r15+0x10], rax','mov [r15+0x8], r14')
    _at(g,'epilogue');g.take('mov r13, [rsp+0x28]')
    _lea(g,'rcx',rip=base+globals['table'])
    g.take('mov r12, [rsp+0x68]','mov rax, r15','mov rdi, [rsp+0x60]','mov rsi, [rsp+0x58]',
        'mov r14, [rsp+0x20]','mov [r15], rcx','add rsp, 0x30','pop r15','pop rbp','pop rbx','ret')
    _at(g,'hit');g.take('shl r14, 0x4','add r14, rdi','shl r9, 0x4','add r9, rdi',
        'mov [r15+0x10], r14','mov [r15+0x8], r9');g.branch('jmp','epilogue')
    _at(g,'sentinelMismatch');g.take('xor al, al');g.branch('jmp','sentinelTest')
    _at(g,'queryMismatch');g.take('xor al, al');g.branch('jmp','queryTest')
    _at(g,'empty');g.call(base+calls['emptyHandler']);g.take('mov rax, r15','add rsp, 0x30','pop r15','pop rbp','pop rbx','ret');g.finish()
    g=_slice(rows,base,segments['coldProbe']);g.labels={k:base+v for k,v in labels.items()}
    _at(g,'coldProbe');g.take('mov r8, r9');_lea(g,'rdx',rip=base+globals['probeData'])
    g.take('shl r8, 0x4','add r8, rdi');g.call(base+calls['probeHelper'])
    g.take('test al, al');g.branch('je','matching')
    g.take('cmp qword [rsp+0x50], -0x1');g.branch('jne','advance')
    g.take('mov [rsp+0x50], r9');g.branch('jmp','advance');g.finish()
    return {'completeInstructions':len(rows),'completeControlAndFramesChecked':True,
        'queryWrapperInput':'entry R8','outputInputAndReturn':'entry RDX','queryPointerWrapperOffset':8,
        'zeroFlagExplicitProbeHitRequiresThreeQwordEquality':True,'comparedQwordOffsets':[0,8,16],
        'nonzeroWrapperFlagMayBypassTripleEquality':True,'containerEntryStride':16,'entryValuePointerOffset':8,
        'outputTablePointerOffset':0,'outputCurrentPointerOffset':8,'outputEndPointerOffset':16,
        'missStoresCurrentEqualToEnd':True,'hitStoresSelectedCurrentAndEnd':True,
        'emptyHandlerOutputEffectsProved':False,'allCallerHitsRequireTripleEqualityProved':False,
        'probeHelperEffectsProved':False,'terminationProved':False,
        'hashFirstPointeeDwordOffset':72,'hashPointerShift':3,'hashMultiplier':0x1cfaa2db,
        'probeStep':'increment R10, add it to R9, mask R9 by current R11; R11 is initially capacity minus one',
        'probeHelperR9R10R11EffectsProved':False,
        'calls':checked_calls,'explicitStores':stores,'frameStates':frames,'runtimeExecutionKnown':False,
        'conditions':'Readable coherent table, wrapper and triples; zero wrapper flag for the equality claim; normal Win64 nonvolatile/stack-preserving callees; valid disjoint output/frame storage. Helper mutations, concurrent changes and later pointee stability remain separate obligations.'}


def validate_descriptor_cache_argument_bridge(rows,*,image_base,composition,lookup,segments,lookup_rva,insertion_rva,globals,new_descriptor_rva):
    """Join physical temporary key, wrapper and iterator-output frame regions."""
    base=image_base
    g=_slice(rows,base,segments['lookupArguments'])
    g.take('xor r15d, r15d','mov [rsp+0x20], r15d','lea rax, [rsp+0x30]',
        'mov [rsp+0x28], rax','lea r8, [rsp+0x20]','lea rdx, [rsp+0x48]')
    lookup_site=int(g.call(base+lookup_rva)['va'],16);g.finish()
    g=_slice(rows,base,segments['selectResult']);g.labels={'newDescriptor':base+new_descriptor_rva}
    rip_load(g,'rax',base+globals['capacity']);g.take('shl rax, 0x4',
        f'add rax, qword [rip => 0x{base+globals["begin"]:x}]','mov rdi, [rsp+0x50]','cmp rdi, rax')
    g.branch('je','newDescriptor');g.take('mov rdi, [rdi+0x8]');g.branch('jmp');g.finish()
    g=_slice(rows,base,segments['insertionArguments'])
    g.take('mov [rsp+0x20], r15d','mov [rsp+0x28], rax','lea r8, [rsp+0x20]','lea rdx, [rsp+0x48]')
    g.call(base+insertion_rva);g.finish()
    frame=composition['frameStates'][lookup_site]
    initial=int(next(r['va'] for r in rows if r['text']=='mov [r11-0x58], rcx'),16)
    key_frame=composition['frameStates'][initial]
    if key_frame[2] is None or [key_frame[2]+n-frame[0] for n in (-88,-80,-72)]!=[48,56,64]:
        raise ValueError(LABEL+'.temporary-key-frame-join')
    if lookup['outputCurrentPointerOffset']!=8 or lookup['queryPointerWrapperOffset']!=8:
        raise ValueError(LABEL+'.lookup-layout-join')
    return {'lookupWrapperFlag':0,'lookupTemporaryTripleRspOffsets':[48,56,64],
        'lookupWrapperRspOffset':32,'lookupOutputRspOffset':72,'lookupCurrentRspOffset':80,
        'insertionWrapperFlag':0,'insertionWrapperPointee':'saved allocation return',
        'initialTemporaryTripleSources':['entry RCX','entry RDX','entry R8'],
        'temporaryKeyContentsSurviveEarlierCallsProved':False,'insertionEffectsProved':False,
        'conditions':'The initialized local temporary key and zero wrapper flag remain coherent across intervening opaque calls and lookup; valid disjoint frame/output/table storage. Actual hit/current/global stability after return is not implied.'}
