"""Handler-word decoding and file-declared CFG dispatch selection boundaries."""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _global
from .register_rotates import decode_register_rotate,rotate_right64

LABEL='nameCacheHandlerGetterControl'


def decode_handler_word(encoded,cookie):
    if type(encoded) is not int or not 0<=encoded<1<<64 or type(cookie) is not int or not 0<=cookie<1<<64:
        raise ValueError(LABEL+'.qword-domain')
    return rotate_right64(encoded^cookie,cookie&63)


def validate_name_cache_handler_getter(programs,*,image_base,contract):
    c=contract;base=image_base
    if set(programs)!={'handlerGetter','callbackDispatch','fileDefaultDispatch'} or set(c['functions'])!=set(programs):
        raise ValueError(LABEL+'.function-membership')
    selected={r['fieldName']:r for r in c['loadConfigDeclaration']['selectedPointerSlots']}
    if set(selected)!={'SecurityCookie','GuardCFDispatchFunctionPointer'}:
        raise ValueError(LABEL+'.load-config-field-membership')
    if selected['SecurityCookie']['slotRva']!=c['globals']['cookie'] or selected['GuardCFDispatchFunctionPointer']['slotRva']!=c['globals']['dispatchSlot']:
        raise ValueError(LABEL+'.load-config-storage-join')
    if selected['GuardCFDispatchFunctionPointer']['onDiskStoredWord']!=base+c['functions']['fileDefaultDispatch']['entryRva']:
        raise ValueError(LABEL+'.file-default-pointer-join')
    rows=programs['handlerGetter'];graph=_complete(rows,base+c['functions']['handlerGetter']['entryRva'])
    g=_Grammar(rows,label=LABEL+'.getter');g.take('push rbx','sub rsp, 0x20','xor ecx, ecx')
    g.call(base+c['externalCalls']['guardEnter']);g.take('nop')
    _global(g,'rax',8,base+c['globals']['cookie']);g.take('mov ecx, eax','and ecx, 0x3f')
    _global(g,'rbx',8,base+c['globals']['encodedHandler']);g.take('xor rbx, rax')
    row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_register_rotate(raw,0,int(row['va'],16))
    f=parsed[0]['registerRotateOperation'] if parsed and parsed[1]==len(raw) else {}
    if (f.get('operation'),f.get('destinationRegister'),f.get('bits'),f.get('countRegister'),f.get('countMask'))!=('ror','rbx',64,'cl',63):
        g.fail('qword-cookie-rotate',('ror','rbx',64,'cl',63),row)
    g.take('xor ecx, ecx');g.call(base+c['externalCalls']['guardLeave']);g.take('mov rax, rbx','add rsp, 0x20','pop rbx','ret');g.finish()
    if len(graph['calls'])!=2 or graph['traps'] or len(graph['returns'])!=1:raise ValueError(LABEL+'.getter-complete-control')
    rows=programs['callbackDispatch']
    if len(rows)!=1:raise ValueError(LABEL+'.dispatcher-whole-program')
    row=rows[0];raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)!=6 or raw[:2]!=bytes.fromhex('FF25') or at+6+int.from_bytes(raw[2:],'little',signed=True)!=base+c['globals']['dispatchSlot']:
        raise ValueError(LABEL+'.dispatcher-tail-storage')
    rows=programs['fileDefaultDispatch']
    if len(rows)!=1 or bytes.fromhex(rows[0]['bytes'])!=bytes.fromhex('FFE0') or rows[0]['text']!='jmp rax':
        raise ValueError(LABEL+'.file-default-register-tail')
    return {'status':'conditional-handler-word-decoding-and-file-cfg-dispatch-joins-proved',
        'codeInstructions':sum(len(rows) for rows in programs.values()),
        'cookieReadJoinsDeclaredSecurityCookieStorageProved':True,
        'completeGetterReturnsRotatedEncodedXorCookieWordProved':True,
        'bothGuardCallsReceiveZeroEcxProved':True,'getterRestoresNonvolatileRbxAndFrameProved':True,
        'dispatcherSlotJoinsDeclaredGuardCfDispatchStorageProved':True,
        'fileDefaultDispatchTailUsesRaxAndPreservesArgumentsProved':True,
        'decodedWordIsValidCallbackProved':False,'getterGuardHelperEffectsProved':False,
        'cookieAndEncodedWordSameEpochProved':False,'liveCfgDispatchSelectionProved':False,
        'loadedCallbackInvocationProved':False,'callbackEffectsOrCacheNoninterferenceProved':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'conditions':c['conditionalDomain']}
