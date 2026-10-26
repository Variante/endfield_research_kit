"""Selected encoded-handler replacement formula; invocation/locking stay open."""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _global,_memory
from .register_rotates import rotate_right64,decode_register_rotate
from .name_cache_handler_getter_control import decode_handler_word

LABEL='nameCacheHandlerSetterControl'


def encode_handler_word(word,cookie):
    if type(word) is not int or not 0<=word<1<<64 or type(cookie) is not int or not 0<=cookie<1<<64:
        raise ValueError(LABEL+'.qword-domain')
    return rotate_right64(word,(64-(cookie&63))&63)^cookie


def replace_handler_word(old_encoded,new_word,cookie):
    return {'returnedOldWord':decode_handler_word(old_encoded,cookie),'storedEncodedWord':encode_handler_word(new_word,cookie)}


def _rotate(g,register):
    row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_register_rotate(raw,0,int(row['va'],16))
    f=parsed[0]['registerRotateOperation'] if parsed and parsed[1]==len(raw) else {}
    if (f.get('operation'),f.get('destinationRegister'),f.get('bits'),f.get('countRegister'),f.get('countMask'))!=('ror',register,64,'cl',63):g.fail('rotate-register',register,row)


def validate_handler_setter(rows,*,entry_va,cookie_va,encoded_va,guard_enter_va,guard_leave_va):
    graph=_complete(rows,entry_va);g=_Grammar(rows,label=LABEL)
    _memory(g,'store','rbx',8,'rsp',8);g.take('push rdi','sub rsp, 0x20','mov rdi, rcx','xor ecx, ecx')
    g.call(guard_enter_va);g.take('nop');_global(g,'rdx',8,cookie_va)
    g.take('mov eax, edx','and eax, 0x3f','mov rbx, rdx')
    row=g.row();f=row.get('memoryXorOperation',{});a=f.get('sourceAddress',{})
    if (f.get('destinationRegister'),f.get('bits'),f.get('memoryReadBytes'),f.get('memoryWriteBytes'),a.get('ripRelative'),a.get('absoluteAddress'))!=('rbx',64,8,0,True,encoded_va):g.fail('old-encoded-xor',(cookie_va,encoded_va),row)
    g.take('mov ecx, eax');_rotate(g,'rbx');g.take('mov ecx, 0x40','sub ecx, eax');_rotate(g,'rdi');g.take('xor rdi, rdx')
    row=g.row();f=row.get('memoryOperation',{});a=f.get('address',{})
    if (f.get('direction'),f.get('register'),f.get('memoryBytes'),a.get('ripRelative'),a.get('absoluteAddress'))!=('store','rdi',8,True,encoded_va):g.fail('encoded-store',encoded_va,row)
    g.take('xor ecx, ecx');g.call(guard_leave_va);g.take('mov rax, rbx');_memory(g,'load','rbx',8,'rsp',48);g.take('add rsp, 0x20','pop rdi','ret');g.finish()
    if len(graph['calls'])!=2 or graph['traps'] or len(graph['returns'])!=1:raise ValueError(LABEL+'.whole-control')
    return {'status':'conditional-handler-replacement-and-old-word-return-formula-proved',
        'codeInstructions':len(rows),'oldEncodedReadAndReplacementStoreSameCellProved':True,
        'sameReadCookieUsedForOldDecodeAndNewEncodeProved':True,
        'bothActualGuardCallsReceiveZeroEcxProved':True,
        'setterRestoresFrameAndNonvolatileRegistersProved':True,
        'sameCookieGetterDecoderInvertsStoredEncodingProved':True,
        'setterInvocationObserved':False,'allWriterCoverageProved':False,'guardEffectsOrCommonEpochProved':False,
        'decodedWordIsValidCallbackProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
