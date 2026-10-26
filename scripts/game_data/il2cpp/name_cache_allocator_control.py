"""Exact allocator wrapper arguments, retry control and conditional returns.

Static import declarations do not prove live bindings or imported/callback
effects. No successful allocation, retry termination or cache isolation follows.
"""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory, _global
from .integer_addressing import decode_lea_address

LABEL='nameCacheAllocatorControl'


def allocation_trace(request, heap_results, retry_results=(), *, max_request, retry_gate, max_trace_steps=10000):
    """Bounded wrapper model; exhausted input means unresolved execution."""
    if type(request) is not int or not 0<=request<1<<64 or type(retry_gate) is not int or not 0<=retry_gate<1<<32:
        raise ValueError(LABEL+'.trace-domain')
    if type(max_request) is not int or not 0<=max_request<1<<64:
        raise ValueError(LABEL+'.max-request-domain')
    if type(max_trace_steps) is not int or max_trace_steps<=0:
        raise ValueError(LABEL+'.trace-bound-domain')
    size=max(request,1);allocations=0;handlers=0
    if request>max_request:return {'kind':'failure','returnWord':0,'errorWord':12,'heapCalls':0,'handlerCalls':0,'requestedBytes':size}
    results=iter(heap_results);retries=iter(retry_results)
    while True:
        if allocations>=max_trace_steps:return {'kind':'unresolved','heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size,'modelBoundExceeded':True}
        try:result=next(results)
        except StopIteration:return {'kind':'unresolved','heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size}
        if type(result) is not int or not 0<=result<1<<64:raise ValueError(LABEL+'.heap-result-domain')
        allocations+=1
        if result:return {'kind':'success','returnWord':result,'heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size}
        if retry_gate==0:return {'kind':'failure','returnWord':0,'errorWord':12,'heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size}
        try:retry=next(retries)
        except StopIteration:return {'kind':'unresolved','heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size}
        if type(retry) is not int or not 0<=retry<1<<32:raise ValueError(LABEL+'.retry-result-domain')
        handlers+=1
        if retry==0:return {'kind':'failure','returnWord':0,'errorWord':12,'heapCalls':allocations,'handlerCalls':handlers,'requestedBytes':size}


def _tail(rows,c,base):
    if len(rows)!=1:raise ValueError(LABEL+'.tail-inventory')
    row=rows[0];b=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    target=base+c['functions']['allocatorWrapper']['entryRva']
    if len(b)!=5 or b[0]!=0xe9 or at+5+int.from_bytes(b[1:],'little',signed=True)!=target or row['text']!=f'jmp {hex(target)}':
        raise ValueError(LABEL+'.tail-target')


def _wrapper(rows,c,base):
    g=_Grammar(rows,label=LABEL+'.wrapper');external=c['externalCalls'];constants=c['constants']
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx',f'cmp rcx, {hex(constants["maxRequest"]-(1<<64))}')
    g.branch('ja','failure');g.take('test rcx, rcx','mov eax, 0x1','cmove rbx, rax');g.branch('jmp','allocate')
    g.mark('retry');g.call(base+c['functions']['retryGate']['entryRva']);g.take('test eax, eax');g.branch('je','failure')
    g.take('mov rcx, rbx');g.call(base+c['functions']['retryHandler']['entryRva']);g.take('test eax, eax');g.branch('je','failure')
    g.mark('allocate');_global(g,'rcx',8,base+c['globals']['heapHandleCell']);g.take('mov r8, rbx','xor edx, edx')
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)!=6 or raw[:2]!=bytes.fromhex('FF15') or at+6+int.from_bytes(raw[2:],'little',signed=True)!=base+c['heapImport']['slotRva']:
        g.fail('heap-import-slot',c['heapImport']['slotRva'],row)
    g.take('test rax, rax');g.branch('je','retry');g.branch('jmp','restore')
    g.mark('failure');g.call(base+c['functions']['errorCell']['entryRva'])
    g.take(f'mov dword [rax], 0x{constants["errorWord"]:x}','xor eax, eax')
    g.mark('restore');g.take('add rsp, 0x20','pop rbx','ret');g.finish()


def _gate(rows,c,base):
    g=_Grammar(rows,label=LABEL+'.gate');_global(g,'eax',4,base+c['globals']['retryGateCell']);g.take('nop','ret');g.finish()


def _handler(rows,c,base):
    g=_Grammar(rows,label=LABEL+'.handler');external=c['externalCalls']
    _memory(g,'store','rbx',8,'rsp',8);g.take('push rdi','sub rsp, 0x20','mov rdi, rcx')
    g.call(base+external['handlerGetter']);g.take('xor ebx, ebx','test rax, rax');g.branch('je','restore')
    g.take('mov rcx, rdi');g.call(base+external['callbackDispatch']);g.take('test eax, eax','setne bl','mov eax, ebx')
    g.mark('restore');_memory(g,'load','rbx',8,'rsp',48);g.take('add rsp, 0x20','pop rdi','ret');g.finish()


def _error(rows,c,base):
    g=_Grammar(rows,label=LABEL+'.error');g.take('sub rsp, 0x28');g.call(base+c['externalCalls']['errorContext'])
    g.take('mov rcx, rax');row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_lea_address(raw,0,int(row['va'],16))
    f=parsed[0]['addressOperation'] if parsed and parsed[1]==len(raw) else {}
    if (f.get('destination'),f.get('destinationBits'),f.get('ripRelative'),f.get('absoluteAddress'))!=('rdx',64,True,base+c['globals']['errorFallback']):
        g.fail('static-error-fallback',c['globals']['errorFallback'],row)
    g.take(f'add rax, 0x{c["constants"]["errorContextOffset"]:x}','test rcx, rcx','cmove rax, rdx','add rsp, 0x28','ret');g.finish()


def validate_name_cache_allocator(programs, *, image_base, contract):
    c=contract;roles={'allocatorProxy','allocatorWrapper','retryGate','retryHandler','errorCell'}
    if set(programs)!=roles or set(c['functions'])!=roles:raise ValueError(LABEL+'.function-membership')
    if c['constants']!={'maxRequest':(1<<64)-32,'errorWord':12,'errorContextOffset':32}:
        raise ValueError(LABEL+'.wrapper-constant-domain')
    if (c['heapImport']['libraryName'],c['heapImport']['symbolName'])!=('KERNEL32.dll','HeapAlloc'):
        raise ValueError(LABEL+'.static-heap-import-identity')
    _tail(programs['allocatorProxy'],c,image_base)
    graphs={role:_complete(rows,image_base+c['functions'][role]['entryRva']) for role,rows in programs.items() if role!='allocatorProxy'}
    if graphs['retryGate']['calls'] or graphs['retryGate']['stores'] or graphs['retryGate']['traps']:
        raise ValueError(LABEL+'.readonly-retry-gate')
    _wrapper(programs['allocatorWrapper'],c,image_base);_gate(programs['retryGate'],c,image_base)
    _handler(programs['retryHandler'],c,image_base);_error(programs['errorCell'],c,image_base)
    failure=allocation_trace(1024,[0],max_request=c['constants']['maxRequest'],retry_gate=0)
    assert failure['kind']=='failure' and failure['returnWord']==0
    return {'status':'complete-conditional-allocator-wrapper-and-helper-control-proved',
        'codeInstructions':sum(len(rr) for rr in programs.values()),
        'actualAllocatorProxyTailJoinProved':True,'staticHeapImportAndWin64ArgumentOriginsProved':True,
        'heapFlagsWord':0,'zeroRequestSubstitutesOneByteProved':True,'unsignedOversizeGuardBeforeHeapCallProved':True,
        'firstNonzeroHeapResultReturnedUnmodifiedProved':True,'zeroHeapResultSelectsRetryGateThenHandlerProved':True,
        'zeroGateOrHandlerSelectsErrorWriteAndNullReturnProved':True,'errorStoreBytes':4,'errorWord':12,
        'readonlyRetryGateReturnsFreshDwordZeroExtendedProved':True,
        'handlerNullGetterReturnsZeroWithoutCallbackProved':True,'handlerNonzeroGetterPassesSizeAndBooleanizesCallbackEaxProved':True,
        'errorCellReturnsFreshContextOffsetOrStaticFallbackProved':True,
        'boundedNullReturnCounterexample':failure,'unconditionalSuccessfulAllocationProved':False,
        'retryTerminationProved':False,'liveHeapHandleOrIatBindingProved':False,'importedHeapImplementationExecuted':False,
        'handlerGetterAndCallbackEffectsProved':False,'errorContextEffectsProved':False,'cacheNoninterferenceProved':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'conditions':c['conditionalDomain']}
