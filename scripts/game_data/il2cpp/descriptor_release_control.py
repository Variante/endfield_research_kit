"""Complete null/heap/error routing below observed OS binding or success."""
from __future__ import annotations
from .descriptor_cache_lookup_control import _complete_graph,_at
from .owned_partition import BranchGrammar,rip_load
from .initializer_control import control_transfer


def validate_release_tail(rows,*,entry_va,target_va):
    if len(rows)!=1 or int(rows[0]['va'],16)!=entry_va:raise ValueError('descriptorReleaseTail.entry-program')
    g=BranchGrammar(rows,label='descriptorReleaseTail');g.labels={'target':target_va};g.branch('jmp','target');g.finish()
    return {'instructionsChecked':1,'tailTargetVa':target_va,'generalRegistersPreservedBeforeTail':True,
        'stackAndFlagsPreservedBeforeTail':True,'memoryWritesBeforeTail':0,
        'physicalFunctionExtentProved':False,'destinationEffectsProvedByTailAlone':False,'runtimeExecutionKnown':False}


def validate_descriptor_release_control(rows,*,image_base,function,labels,globals,calls,imports):
    base=image_base;edges,frames,checked_calls,stores=_complete_graph(rows,base,function)
    g=BranchGrammar(rows,label='descriptorReleaseControl');g.labels={k:base+v for k,v in labels.items()}
    g.take('test rcx, rcx');g.branch('je','nullReturn')
    g.take('push rbx','sub rsp, 0x20','mov r8, rcx','xor edx, edx');rip_load(g,'rcx',base+globals['heapHandle'])
    def imported(role):
        r=g.row();flow=control_transfer(r)
        if flow.get('kind')!='indirectCall' or flow.get('cell')!=base+imports[role]['iatCellRva']:
            g.fail('imported-call-cell',imports[role]['iatCellRva'],r)
    imported('heapOperation');g.take('test eax, eax');g.branch('jne','restore')
    imported('lastError');g.take('mov ecx, eax');g.call(base+calls['errorConversionCandidate'])
    g.take('mov ebx, eax');g.call(base+calls['errorSlotCandidate']);g.take('mov [rax], ebx')
    _at(g,'restore');g.take('add rsp, 0x20','pop rbx');_at(g,'nullReturn');g.take('ret');g.finish()
    expected=[('heapOperation','HeapFree'),('lastError','GetLastError')]
    for role,name in expected:
        if imports[role]['name']!=name or imports[role]['dll'].lower()!='kernel32.dll':
            raise ValueError('descriptorReleaseControl.import-declaration:'+role)
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,
        'nullInputSkipsHeapAndErrorCalls':True,'heapCallArguments':{'rcx':'fresh heap-handle global QWORD','rdx':0,'r8':'entry pointer'},
        'declaredHeapImport':'KERNEL32.dll!HeapFree','declaredErrorImport':'KERNEL32.dll!GetLastError',
        'nonzeroHeapEaxSkipsErrorPath':True,'zeroHeapEaxReadsLastError':True,
        'errorCodeTransferBits':32,'errorConversionReturnSavedInEbx':True,
        'errorSlotWrite':{'bytes':4,'address':'error-slot helper full RAX return','value':'saved conversion helper EAX'},
        'errorHelpersAlgorithmProved':False,'wholeFunctionBooleanReturnProved':False,'runtimeIatBindingsObserved':False,
        'heapHandleAndPointerOwnershipProved':False,'releaseSucceededProved':False,'runtimeExecutionKnown':False,
        'calls':checked_calls,'explicitStores':stores,'frameStates':frames,
        'conditions':'Normally bound documented imports, valid heap/pointer ownership for interpreting HeapFree, normal ABI-preserving error helpers and a valid writable four-byte returned slot. The recorded program does not establish actual binding, input ownership or successful execution.'}
