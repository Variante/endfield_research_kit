"""Prove the complete RBP-push/RBX-RSI-RDI-R14 save/restore frame profile."""
from __future__ import annotations

import hashlib


def prove_rbp_saved_register_frame(prologue: bytes, epilogue: bytes, *, allocation: int) -> dict:
    """Match entry saves and return restores, preserving the incoming exit AL.

    This proves the two complete byte programs. Ordinary callee stack/nonvolatile
    preservation and absence of interfering caller writes remain obligations.
    """
    if type(allocation) is not int or not 16 <= allocation <= 112 or allocation%16:
        raise ValueError('rbp-frame.allocation: positive aligned signed-byte allocation required')
    if not isinstance(prologue,bytes) or not isinstance(epilogue,bytes):
        raise ValueError('rbp-frame.program: bytes required')
    entry=bytes.fromhex('488BC44889580848897010488978184C89702055488BEC4883EC')+bytes([allocation])
    exit=bytes.fromhex('4C8D5C24')+bytes([allocation])+bytes.fromhex('498B5B10498B7318498B7B204D8B7328498BE35DC3')
    if prologue!=entry or epilogue!=exit:
        raise ValueError('rbp-frame.save-restore-program: complete matching entry and epilogue required')
    return {'schema':'endfield.win64-rbp-saved-frame-proof.v1',
        'entryProgramBytes':len(entry),'epilogueProgramBytes':len(exit),
        'entryProgramSha256':hashlib.sha256(entry).hexdigest().upper(),
        'epilogueProgramSha256':hashlib.sha256(exit).hexdigest().upper(),
        'allocation':allocation,'rbpRelativeToEntryRsp':-8,'allocatedRspRelativeToEntryRsp':-8-allocation,
        'entrySavedQwords':{'rbx':8,'rsi':16,'rdi':24,'r14':32,'rbp':-8},
        'epilogueRestoreOffsetsRelativeToR11':{'rbx':16,'rsi':24,'rdi':32,'r14':40},
        'r11AtEpilogueRelativeToEntryRsp':-8,'rspBeforeRetRelativeToEntryRsp':0,
        'rspAfterRetRelativeToEntryRsp':8,'completeRetPresent':True,'exitAlPreserved':True,
        'entryRspRemainderRequiredForAlignedCalls':8,
        'fifthArgumentFrameSlot':48,'runtimeExecutionKnown':False,
        'evidenceBoundary':'Exact entry/exit programs pair every saved nonvolatile register, restore incoming RBP and stack coordinates and preserve AL through RET. A valid entry stack/return address, normal ABI calls, unchanged allocated RSP at epilogue and unmodified save slots remain conditions; the middle caller program is not proved here.'}
