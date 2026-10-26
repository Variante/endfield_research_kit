"""Complete null-zero/count-delegation programs with independent call styles.

These programs consume an opaque current context and dispatch result. Matching
arguments establishes conditional behavior, not equality of entry identities,
runtime RGCTX meaning, a selected interface getter or an array length.
"""
from __future__ import annotations

import hashlib


def prove_null_safe_count_program(raw: bytes, *, entry_va: int,
        initialize_va: int, context_slot_helper_va: int, dispatch_va: int,
        variant: str) -> dict:
    if (not isinstance(raw,bytes) or variant not in ('direct-tail','canonical-call')
            or any(type(v) is not int or not 0<v<1<<64 for v in
                (entry_va,initialize_va,context_slot_helper_va,dispatch_va))
            or entry_va+len(raw)>=1<<64):
        raise ValueError('null-safe-count.input: exact bytes, bounded addresses and explicit variant required')
    rows=[];offset=0
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'null-safe-count.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def branch(opcode,target,meaning,*,short=False):
        nonlocal offset
        prefix=bytes.fromhex(opcode);size=len(prefix)+(1 if short else 4);actual=raw[offset:offset+size]
        if len(actual)!=size or actual[:len(prefix)]!=prefix:
            raise ValueError(f'null-safe-count.branch-opcode: offset={offset} expected={opcode} actual={actual.hex().upper()}')
        dest=entry_va+offset+size+int.from_bytes(actual[len(prefix):],'little',signed=True)
        if dest!=target:
            raise ValueError(f'null-safe-count.branch-target: offset={offset} expected={target:#x} actual={dest:#x}')
        rows.append({'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=size
    literal('48895C2408','save incoming rbx in entry home slot +8')
    literal('57','push incoming rdi')
    literal('4883EC20','allocate 32 bytes; current rsp = entry rsp -40')
    literal('48837A3800','compare opaque context qword at incoming rdx+56 with zero')
    if variant=='direct-tail':
        literal('488BFA','rdi = incoming rdx context')
        literal('488BD9','rbx = incoming rcx list')
        branch('74',entry_va+76,'zero context slot enters initializer',short=True)
        literal('4885DB','test saved list')
        branch('74',entry_va+63,'null list enters zero-result return',short=True)
        literal('488B4F38','rcx = opaque current context+56 qword')
        literal('488B09','rcx = first qword at that pointer')
        branch('E8',context_slot_helper_va,'call selected opaque context-slot helper')
        literal('33C9','zero full rcx dispatch slot argument')
        literal('4C8BC3','r8 = original list')
        literal('488BD0','rdx = context-slot helper result')
        literal('488B5C2430','restore incoming rbx from entry home slot +8')
        literal('4883C420','release local allocation')
        literal('5F','restore incoming rdi and original entry rsp')
        branch('E9',dispatch_va,'tail jump preserving original return address and arguments')
        literal('488B5C2430','null path restores incoming rbx from same home slot')
        literal('33C0','null list returns eax zero, zero extending full rax')
        literal('4883C420','null path releases local allocation')
        literal('5F','null path restores incoming rdi and original entry rsp')
        literal('C3','null path returns to original return address')
        literal('488BCF','rcx = original context for initializer')
        branch('E8',initialize_va,'call selected context initializer')
        branch('EB',entry_va+23,'rejoin original list test after initialization',short=True)
    else:
        literal('488BDA','rbx = incoming rdx context')
        literal('488BF9','rdi = incoming rcx list')
        branch('75',entry_va+31,'nonzero context slot skips initialization',short=True)
        literal('488BCA','rcx = original context for initializer')
        branch('E8',initialize_va,'call the same selected context initializer')
        literal('4885FF','test saved list')
        branch('75',entry_va+40,'nonnull list enters dispatch setup',short=True)
        literal('33C0','null list returns eax zero, zero extending full rax')
        branch('EB',entry_va+65,'null list enters common saved-frame return',short=True)
        literal('488B4B38','rcx = opaque current context+56 qword')
        literal('488B09','rcx = first qword at that pointer')
        branch('E8',context_slot_helper_va,'call the same selected opaque context-slot helper')
        literal('33C9','zero full rcx dispatch slot argument')
        literal('4C8BC7','r8 = original list')
        literal('488BD0','rdx = context-slot helper result')
        branch('E8',dispatch_va,'call dispatch with selected slot/context/list arguments')
        literal('488B5C2430','restore incoming rbx from entry home slot +8')
        literal('4883C420','release local allocation without changing dispatch rax')
        literal('5F','restore incoming rdi and original entry rsp')
        literal('C3','return null-zero or dispatch rax to original return address')
    if offset!=len(raw):raise ValueError(f'null-safe-count.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-null-zero-and-count-delegation-program-proved','variant':variant,
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'incomingArguments':{'list':'rcx','opaqueContext':'rdx'},'opaqueContextSlotOffset':56,
        'initializerBeforeNullListTestWhenSlotZero':True,'nullListReturnsFullRaxZero':True,
        'nonnullDispatchArguments':{'rcx':'zero','rdx':'context helper return rax','r8':'original list'},
        'nonnullReturnSource':'selected dispatch rax after normal return',
        'dispatchTransfer':'tail-jump' if variant=='direct-tail' else 'call-then-return',
        'frame':{'rspFromEntryRsp':-40,'savedRbxEntryHomeOffset':8,'restoredRdi':True,
            'originalReturnAddressRetained':True},
        'contextHelperResultTypeOrRuntimeSlotMeaningProved':False,'selectedInterfaceGetterProved':False,
        'nonnullReturnedCountOrArrayLengthProved':False,'runtimeMethodInfoOrExecutionKnown':False,
        'conditions':['Current caller authenticates full original program and selected targets',
            'Readable current context/slot and required pointee, valid writable frame/home memory',
            'Initializer and context helper return normally, preserve Win64 nonvolatile registers and required frame memory',
            'Dispatch returns normally under its corresponding Win64 call or tail-call frame and argument conditions',
            'No incompatible callee, concurrent or aliased writes; no runtime context or interface identity inferred from static bytes'],
        'evidenceBoundary':'Every byte, context/list branches, zero return, exact delegated arguments and saved-frame return transfer. Canonical registration and actual-entry identity remain distinct; dispatch selection/result and array length are separate proofs.'}
