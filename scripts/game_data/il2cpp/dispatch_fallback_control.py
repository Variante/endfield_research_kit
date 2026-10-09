"""Complete anonymous prepare-entry/tail and resolver argument/result control."""
from __future__ import annotations
import hashlib
from scripts.game_data.il2cpp.integer_source_operands import decode_source_operand_integer_instructions,is_unknown_instruction
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


def _rows(index,start,end,digest):
    raw=index.pe.bytes_at_va(start,end-start)
    if hashlib.sha256(raw).hexdigest().upper()!=digest.upper():raise ValueError('dispatchFallback.code-window')
    rows=decode_source_operand_integer_instructions(index.mapper,raw,start)
    if any(is_unknown_instruction(r) for r in rows):raise ValueError('dispatchFallback.unknown-instruction')
    return rows


def _owned(index,spec):
    base=index.pe.image_base;entry=base+spec['entryRva']
    actual=sorted(set([(entry,index.extents[entry])]+[(a,a+n) for a,n in index.chained_fragments.get(entry,[])]))
    expected=[(base+w['startRva'],base+w['endRva']) for w in spec['codeWindows']]
    if actual!=expected:raise ValueError(f'dispatchFallback.owned-fragments: expected={expected} actual={actual}')
    return [_rows(index,base+w['startRva'],base+w['endRva'],w['sha256']) for w in spec['codeWindows']]


def validate_dispatch_fallback_control(index,c):
    base=index.pe.image_base;l=c['layout'];calls=c['calls'];s=c['prepareEntryTransfer']
    entry=ProgramGrammar(_rows(index,base+s['entryRva'],base+s['endRva'],s['sha256']),label='dispatchFallback.prepareEntry')
    entry.take(f'mov rcx, [rcx+0x{l["prepareArgumentPointer"]:x}]')
    transfer=entry.branch('jmp')
    if transfer['target']!=base+c['programs']['prepareTail']['entryRva'] or transfer['target']!=base+s['targetRva']:
        entry.fail('actual-tail-target',hex(base+s['targetRva']),transfer)
    entry.finish()
    prepare=ProgramGrammar(_owned(index,c['programs']['prepareTail'])[0],label='dispatchFallback.prepareTail')
    prepare.take('push rbx','sub rsp, 0x20','mov rbx, rcx')
    row=prepare.take(f'movzx eax, byte [rcx+0x{l["prepareFirstFlagByte"]:x}]')
    if row['byteMemoryZeroExtensionOperation']['memoryReadBytes']!=1:prepare.fail('flag-read-width',1,row)
    prepare.take('nop',f'test al, 0x{l["prepareFirstFlagMask"]:x}');prepare.branch('je','secondFlag')
    prepare.mark('epilogue');prepare.take('add rsp, 0x20','pop rbx','ret')
    prepare.mark('secondFlag');prepare.take(f'test byte [rcx+0x{l["prepareSecondFlagByte"]:x}], 0x{l["prepareSecondFlagMask"]:x}')
    prepare.branch('jne','epilogue')
    prepare.take(f'lea rcx, [rip+0x{base+c["prepareGlobalRva"]-(int(prepare.rows[prepare.cursor]["va"],16)+7):x} => 0x{base+c["prepareGlobalRva"]:x}]')
    prepare.take('mov [rsp+0x30], rcx');prepare.call(base+calls['prepareFirst'])
    prepare.take('nop','lea rdx, [rsp+0x30]','mov rcx, rbx');prepare.call(base+calls['prepareSecond'])
    prepare.take('nop','mov rcx, [rsp+0x30]');prepare.call(base+calls['prepareThird'])
    prepare.take('nop');prepare.branch('jmp','epilogue');prepare.finish()

    primary,cold=_owned(index,c['programs']['resolver'])
    resolver=ProgramGrammar(primary,label='dispatchFallback.resolver');slow=ProgramGrammar(cold,label='dispatchFallback.resolverCold')
    resolver.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi',
        'sub rsp, 0x20','mov rbx, [rcx]','mov rdi, rcx','mov rcx, rbx','movzx esi, r8w','mov rbp, rdx')
    resolver.call(base+calls['resolverFirst']);resolver.take('test rax, rax');resolver.branch('je','cold')
    resolver.mark('epilogue');resolver.take('mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]',
        'mov rsi, [rsp+0x40]','add rsp, 0x20','pop rdi','ret')
    slow.mark('cold');slow.take(f'test byte [rbx+0x{l["resolverAlternateFlagByte"]:x}], 0x{l["resolverAlternateFlagMask"]:x}')
    slow.branch('je','failure');slow.take(f'cmp [rdi+0x{l["resolverAlternateReceiverField"]:x}], 0x0');slow.branch('je','failure')
    slow.take('movzx r8d, si','mov rdx, rbp','mov rcx, rdi');slow.call(base+calls['resolverAlternate'])
    slow.take('mov rdi, rax','test rax, rax');slow.branch('je','failure')
    slow.take(f'mov rcx, [rax+0x{l["alternateResultContextField"]:x}]',
        f'mov rcx, [rcx+0x{l["alternateResultContextNestedField"]:x}]')
    slow.call(base+calls['alternateResultContinuation']);slow.take('mov rax, rdi');slow.branch('jmp','epilogue')
    slow.mark('failure');slow.take('movzx r8d, si','mov rdx, rbp','mov rcx, rbx')
    slow.call(base+calls['resolverFailure']);slow.take('int3')
    resolver.labels.update(slow.labels);slow.labels.update(resolver.labels);resolver.finish();slow.finish()
    return {'completeOwnedPrepareAndResolverControlChecked':True,
        'checkedInstructions':len(entry.rows)+len(prepare.rows)+len(primary)+len(cold),
        'prepareActualPointerLoadAndTailTransferProved':True,'prepareStoredByteGatesProved':True,
        'prepareConditionalCallArgumentChainProved':True,'prepareSecondChildMayModifyForwardedStackSlot':True,
        'resolverOriginalReceiverContextAndUInt16SelectorProved':True,
        'resolverNonnullFirstOrPermittedAlternateResultReturnedProved':True,
        'resolverFailureCallFollowedByInt3Proved':True,'completeNonvolatileAndStackRestorationProved':True,
        'conditions':['valid stable compatible selected receiver/context/flag/stack/result storage',
            'normal ABI-compatible preparation/search/alternate/continuation child returns'],
        'namedRuntimeClassInterfaceAndSlotMeaningProved':False,'fullResolverDirectChildProved':False,
        'childEffectsOrInitializationMeaningProved':False,'actualRuntimeTargetSelected':False,
        'wordHashAndPredicateEqualityMeaningProved':False,'liveCacheContentsProved':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
