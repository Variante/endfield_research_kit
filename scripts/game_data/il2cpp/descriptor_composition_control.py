"""Complete composition graph and new three-QWORD descriptor stores."""
from __future__ import annotations
from collections import deque
from .field_setup_control import _graph,_frames
from .initializer_control import (control_transfer,memory_effect,_ALIASES,_PARENTS,
    _VOLATILE,_READ_ONLY,_WRITERS,_register_copy)
from .owned_partition import BranchGrammar,rip_load


def _argument_origins(rows, edges, *, entry, allocator_call, cache_load):
    """Join argument origins over actual CFG edges, including all backedges.

    Calls preserve only Win64 nonvolatile registers; unknown writes kill origins.
    A singleton at a store is required, so even one bypass or overwrite refuses it.
    """
    unknown=frozenset({'unknown'});initial=[unknown]*len(_PARENTS)
    for register in ('rcx','rdx','r8'):
        initial[_PARENTS.index(register)]=frozenset({'entry '+register.upper()})
    incoming={entry:tuple(initial)};pending=deque([entry]);by_at={int(r['va'],16):r for r in rows}
    while pending:
        at=pending.popleft();row=by_at[at];values=list(incoming[at])
        kind=control_transfer(row)['kind'];head,_,args=row['text'].partition(' ')
        destination=_ALIASES.get(args.split(',')[0]);raw=bytes.fromhex(row['bytes'])
        if kind in ('call','indirectCall','registerCall'):
            for register in _VOLATILE:values[_PARENTS.index(register)]=unknown
            if at==allocator_call:values[_PARENTS.index('rax')]=frozenset({'allocation return'})
        elif kind in ('jump','conditional','return','trap') or head in _READ_ONLY:pass
        elif head=='lock':
            fact=row.get('lockedMemoryExchangeOperation')
            if fact:
                register='rax' if fact['operation']=='cmpxchg' else _ALIASES.get(fact['sourceRegister'])
                if register not in _PARENTS:raise ValueError('descriptorCompositionControl.locked-register-effect')
                values[_PARENTS.index(register)]=unknown
            else:raise ValueError('descriptorCompositionControl.unreviewed-locked-effect')
        elif head in _WRITERS or head.startswith('cmov'):
            copy=_register_copy(raw) if head=='mov' else None
            if copy:
                target,source=copy;values[_PARENTS.index(target)]=values[_PARENTS.index(source)]
            elif destination is not None:values[_PARENTS.index(destination)]=unknown
            # Memory destinations do not change their address/source registers.
        else:raise ValueError('descriptorCompositionControl.unreviewed-register-effect:'+row['text'])
        if at==cache_load:values[_PARENTS.index('rdi')]=frozenset({'selected cache entry value'})
        output=tuple(values)
        for target in edges[at]:
            old=incoming.get(target);joined=output if old is None else tuple(a|b for a,b in zip(old,output))
            if old!=joined:incoming[target]=joined;pending.append(target)
    return incoming


def validate_descriptor_composition_control(rows, *, image_base, function, segments, allocator_rva, allocator_context_rva):
    f=dict(function);branches=[];calls=[];stores=[];returns=[];traps=[]
    for row in rows:
        at=int(row['va'],16);flow=control_transfer(row);kind=flow['kind']
        if kind in ('jump','conditional'):branches.append({'siteRva':at-image_base,**flow})
        elif kind in ('call','indirectCall','registerCall'):calls.append({'siteRva':at-image_base,**flow})
        elif kind=='return':returns.append(at-image_base)
        elif kind=='trap':traps.append(at-image_base)
        effect=memory_effect(row)
        if effect:stores.append({'siteRva':at-image_base,**effect})
    f.update(localBranches=branches,calls=calls,explicitStores=stores,returnRvas=returns,trapRvas=traps)
    edges,checked_calls,checked_stores=_graph(rows,image_base,f);states=_frames(rows,edges,image_base,f)
    def selected(name):
        a,b=(image_base+x for x in segments[name]);selected=[r for r in rows if a<=int(r['va'],16)<b]
        if not selected or int(selected[0]['va'],16)!=a or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes']))!=b:
            raise ValueError('descriptorCompositionControl.segment-extent:'+name)
        return BranchGrammar(selected,label='descriptorCompositionControl.'+name)
    g=selected('savedInputs');g.take('mov rsi, r8','mov rbp, rdx','mov r14, rcx',
        'mov [r11-0x58], rcx','mov [r11-0x50], rdx','mov [r11-0x48], r8');g.finish()
    g=selected('newDescriptor');g.take('mov r8d, 0x18','mov rdx, rbx')
    rip_load(g,'rcx',image_base+allocator_context_rva)
    allocator_call=int(g.call(image_base+allocator_rva)['va'],16)
    g.take('mov rdi, rax');store_rows=[g.take(text) for text in ('mov [rax], r14','mov [rax+0x8], rbp','mov [rax+0x10], rsi')];g.finish()
    g=selected('cachedDescriptor');cache_load=int(g.take('mov rdi, [rdi+0x8]')['va'],16);g.branch('jmp');g.finish()
    g=selected('return');g.take('mov rax, rdi','lea r11, [rsp+0x70]',
        'mov rbx, [r11+0x28]','mov rbp, [r11+0x30]','mov rsi, [r11+0x38]',
        'mov rsp, r11','pop r15','pop r14','pop rdi','ret');g.finish()
    origins=_argument_origins(rows,edges,entry=image_base+f['entryRva'],allocator_call=allocator_call,cache_load=cache_load)
    flow=[]
    for row,register,source,offset in zip(store_rows,('r14','rbp','rsi'),('RCX','RDX','R8'),(0,8,16)):
        at=int(row['va'],16);state=origins[at]
        if state[_PARENTS.index(register)]!=frozenset({'entry '+source}) or state[_PARENTS.index('rax')]!=frozenset({'allocation return'}):
            raise ValueError('descriptorCompositionControl.store-origin:'+register)
        flow.append({'siteRva':at-image_base,'source':'entry '+source,'allocationOffset':offset})
    return_at=image_base+segments['return'][0]
    expected=frozenset({'allocation return','selected cache entry value'})
    if origins[return_at][_PARENTS.index('rdi')]!=expected:
        raise ValueError('descriptorCompositionControl.return-selection-origin')
    return {'instructionsChecked':len(rows),'completeLocalControlChecked':True,'normalFramesChecked':True,
        'sourceArguments':['entry RCX','entry RDX','entry R8'],'newDescriptorBytesRequested':24,
        'newDescriptorQwordOffsets':[0,8,16],'sameSavedInputsStoredOnNewPath':True,
        'argumentOriginsJoinedOverCompleteCfg':True,'newStoreFieldFlows':flow,
        'normalReturnOrigins':sorted(expected),'descriptorContentsSurviveLaterCallsProved':False,
        'cacheHitSelectedValueOffset':8,'normalReturnSource':'saved RDI selected by hit or allocation path',
        'calls':checked_calls,'explicitStores':checked_stores,'frameStates':states,
        'cacheHitKeyEqualityProvedHere':False,'allocationOrSynchronizationEffectsProved':False,'runtimeExecutionKnown':False,
        'conditions':'Valid writable returned allocation of at least 24 bytes, compatible disjoint key/frame/cache storage and normally returning Win64 nonvolatile/stack-preserving callees. Cache search/insertion, concurrency and pointee contents remain separate obligations.'}
