"""Conditional source RAX to setter RDX across a nonzero-receiver guard.

The caller authenticates the enclosing reader, actual source/setter CALLs and
this complete bridge. INT3 interception and other helper effects are excluded.
"""
from __future__ import annotations


def validate_reference_setter_guard_bridge(raw: bytes, *, start_va: int, setter_site_va: int,
                                          error_target_va: int) -> dict:
    label='referenceSetterGuardBridge'
    if not isinstance(raw,bytes) or type(start_va) is not int or type(setter_site_va) is not int or type(error_target_va) is not int:
        raise ValueError(label+'.input-domain')
    if len(raw)!=20 or setter_site_va!=start_va+len(raw):raise ValueError(label+'.complete-bridge-extent')
    if raw[:5]!=bytes.fromhex('4885DB7506'):raise ValueError(label+'.nonnull-rbx-branch')
    if raw[5]!=0xe8 or start_va+10+int.from_bytes(raw[6:10],'little',signed=True)!=error_target_va:raise ValueError(label+'.actual-error-call')
    if raw[10]!=0xcc:raise ValueError(label+'.error-fallthrough-trap')
    if raw[11:]!=bytes.fromhex('4533C0488BD0488BCB'):raise ValueError(label+'.setter-argument-origin')
    return {'status':'nonnull-receiver-source-return-to-setter-arguments-proved','bytesChecked':20,
        'normalSourceRaxPreservedIntoSetterRdxProved':True,'setterReceiverIsGuardedRbxProved':True,
        'setterR8dIsZeroProved':True,'zeroReceiverHasNoOrdinarySetterContinuationProved':True,
        'errorHelperReturnValueCanBeUsedAsSetterInputProved':False,'setterInvokedOrEffectObserved':False,
        'conditions':'Normal source-helper return and architectural control without INT3 interception; nonzero valid receiver is required for ordinary setter continuation.'}
