"""Exact init/rollback/count control under a zero-counter valid-prefix domain."""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _global
from .integer_addressing import decode_lea_address

LABEL='nameCacheHandlerLifecycleControl'


def cleanup_indices(counter,slots):
    if type(counter) is not int or type(slots) is not int or not 0<=counter<=slots<=1<<16:
        raise ValueError(LABEL+'.valid-initialized-prefix-domain')
    return list(range(counter-1,-1,-1))


def initialize_trace(results,*,slots,initial_counter=0):
    if type(initial_counter) is not int or initial_counter!=0 or type(slots) is not int or not 0<slots<=1<<16:
        raise ValueError(LABEL+'.conditional-zero-counter-domain')
    inputs=iter(results);successes=0
    for index in range(slots):
        try:result=next(inputs)
        except StopIteration:return {'kind':'unresolved','successfulPrefix':successes,'counter':successes}
        if type(result) is not int or not 0<=result<1<<32:raise ValueError(LABEL+'.eax-result-domain')
        if result==0:return {'kind':'failure','failedIndex':index,'returnAl':0,'successfulPrefix':successes,
            'deletedIndices':cleanup_indices(successes,slots),'counter':0}
        successes+=1
    return {'kind':'success','returnAl':1,'successfulPrefix':successes,'deletedIndices':[],'counter':slots}


def _array(g,register,address):
    row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_lea_address(raw,0,int(row['va'],16))
    f=parsed[0]['addressOperation'] if parsed and parsed[1]==len(raw) else {}
    if (f.get('destination'),f.get('destinationBits'),f.get('ripRelative'),f.get('absoluteAddress'))!=(register,64,True,address):g.fail('array-address',(register,address),row)


def _step(g,operation,address):
    row=g.row();f=row.get('memoryStepOperation',{});a=f.get('destinationAddress',{})
    if (f.get('operation'),f.get('bits'),f.get('memoryReadBytes'),f.get('memoryWriteBytes'),a.get('ripRelative'),a.get('absoluteAddress'),f.get('locked'))!=(operation,32,4,4,True,address,False):g.fail('counter-step',(operation,address),row)


def validate_handler_lifecycle(programs,*,image_base,contract):
    c=contract;base=image_base
    if set(programs)!={'initializer','cleanup','initProxy'} or set(c['functions'])!=set(programs):raise ValueError(LABEL+'.function-membership')
    if (c['layout']['strideBytes'],c['layout']['slots'],c['layout']['spinCount'],c['layout']['flags'])!=(40,15,4000,0):raise ValueError(LABEL+'.selected-loop-layout')
    graphs={role:_complete(programs[role],base+c['functions'][role]['entryRva']) for role in ('initializer','cleanup')}
    array=base+c['arrayBaseRva'];counter=base+c['counterRva'];slots=c['layout']['slots']
    g=_Grammar(programs['initializer'],label=LABEL+'.initialize')
    g.take('push rbx','sub rsp, 0x20','xor ebx, ebx');g.mark('loop');_array(g,'rdx',array)
    g.take('xor r8d, r8d','lea rcx, [rbx+rbx*4]','lea rcx, [rdx+rcx*8]',f'mov edx, 0x{c["layout"]["spinCount"]:x}')
    g.call(base+c['functions']['initProxy']['entryRva']);g.take('test eax, eax');g.branch('je','failure')
    _step(g,'inc',counter);g.take('inc ebx',f'cmp ebx, 0x{slots:x}');g.branch('jb','loop')
    g.take('mov al, 0x1');g.branch('jmp','restore');g.mark('failure');g.take('xor ecx, ecx');g.call(base+c['functions']['cleanup']['entryRva']);g.take('xor al, al')
    g.mark('restore');g.take('add rsp, 0x20','pop rbx','ret');g.finish()
    g=_Grammar(programs['cleanup'],label=LABEL+'.cleanup');g.take('push rbx','sub rsp, 0x20');_global(g,'ebx',4,counter);g.branch('jmp','test')
    g.mark('delete');_array(g,'rax',array);g.take('dec ebx','lea rcx, [rbx+rbx*4]','lea rcx, [rax+rcx*8]')
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)!=6 or raw[:2]!=bytes.fromhex('FF15') or at+6+int.from_bytes(raw[2:],'little',signed=True)!=base+c['deleteImportSlotRva']:g.fail('delete-import',c['deleteImportSlotRva'],row)
    _step(g,'dec',counter);g.mark('test');g.take('test ebx, ebx');g.branch('jne','delete');g.take('mov al, 0x1','add rsp, 0x20','pop rbx','ret');g.finish()
    rows=programs['initProxy']
    if len(rows)!=1:raise ValueError(LABEL+'.init-proxy-inventory')
    row=rows[0];raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)!=7 or raw[:3]!=bytes.fromhex('48FF25') or at+7+int.from_bytes(raw[3:],'little',signed=True)!=base+c['initImportSlotRva']:raise ValueError(LABEL+'.init-proxy-tail')
    imports={r['slotRva']:r for r in c['importDeclaration']['selectedImports']}
    for slot,symbol in ((c['initImportSlotRva'],'InitializeCriticalSectionEx'),(c['deleteImportSlotRva'],'DeleteCriticalSection')):
        row=imports.get(slot,{})
        if (row.get('libraryName'),row.get('symbolName'))!=('KERNEL32.dll',symbol):raise ValueError(LABEL+'.import-identity:'+symbol)
    return {'status':'conditional-zero-counter-init-prefix-and-rollback-control-proved',
        'codeInstructions':sum(len(rr) for rr in programs.values()),'slots':slots,'spinCountArgument':4000,'flagsArgument':0,
        'sameArrayAddressForInitAndCleanupProved':True,'nonzeroEaxIncrementsCounterAndAdvancesIndexProved':True,
        'zeroEaxSelectsCleanupThenFalseAlProved':True,'cleanupDeletesReverseCounterPrefixProved':True,
        'conditionalSuccessCounterEqualsSlotCountProved':True,'conditionalFailureCounterReturnsZeroProved':True,
        'onlyAlReturnResultProved':True,'fullRaxBooleanReturnProved':False,
        'counterZeroOnActualEntryProved':False,'initializedObjectsOrLifecycleInvocationObserved':False,
        'actualUseAfterSuccessfulInitializationProved':False,'concurrentCounterOrObjectIsolationProved':False,
        'liveImportBindingsProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,
        'conditions':c['conditionalDomain']}
