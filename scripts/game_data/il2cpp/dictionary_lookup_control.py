"""Own anonymous lookup control and the ordinary disabled-barrier output.

The word producer and predicate remain opaque calls. Layout members describe
observed storage expressions, not independently named closed generic fields.
"""
from __future__ import annotations
import hashlib
import struct
from typing import Any

from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.signed_division import decode_signed_integer_instructions
from scripts.game_data.memorypack.reference_conversion_sources import LOCAL_OPS


def validate_lookup_control(index: Any, c: dict) -> dict:
    pe = index.pe; base = pe.image_base; entry = base + c['entryRva']
    actual = sorted(set([(entry, index.extents[entry])] + [
        (start, start + size) for start, size in index.chained_fragments.get(entry, [])]))
    expected = [(base + w['startRva'], base + w['endRva']) for w in c['codeWindows']]
    if actual != expected:
        raise ValueError(f'dictionaryLookupControl.owned-fragments: expected={expected} actual={actual}')

    class Fallback:
        def decode_one_x64(self, raw, offset, start_va):
            for raw_hex, text in LOCAL_OPS.items():
                opcode = bytes.fromhex(raw_hex)
                if raw[offset:offset+len(opcode)] == opcode:
                    return {'offset':offset, 'va':hex(start_va+offset), 'bytes':opcode.hex(' '),
                            'text':text}, offset + len(opcode)
            return index.mapper.decode_one_x64(raw, offset, start_va)

    rows = []
    for window in c['codeWindows']:
        start = base + window['startRva']
        raw = pe.bytes_at_va(start, window['endRva'] - window['startRva'])
        if hashlib.sha256(raw).hexdigest().upper() != window['sha256'].upper():
            raise ValueError(f'dictionaryLookupControl.code-window: startRva={window["startRva"]}')
        decoded = decode_signed_integer_instructions(Fallback(), raw, start)
        if any('db ' in row['text'] for row in decoded):
            raise ValueError('dictionaryLookupControl.unknown-instruction')
        rows.extend(decoded)
    g = ProgramGrammar(rows, label='dictionaryLookupControl')
    layout = c['layout']; calls = c['calls']
    def mem(register, field): return f'[{register}+0x{layout[field]:x}]'
    def call(role): return g.call(base + calls[role])
    def locked_stack_order():
        row = g.take('or [rsp], 0x0')
        if bytes.fromhex(row['bytes']) != bytes.fromhex('f0830c2400'):
            g.fail('locked-stack-order', 'LOCK OR DWORD [rsp],0', row)
    def prepare(label):
        row = g.take(f'test byte {mem("rax","preparedFlags")}, 1')
        # This local decoder records only this exact byte-width flag test.
        if not row['bytes'].startswith('f6 80'):
            g.fail('prepared-flag-width', 'byte test', row)
        g.branch('jne', label); g.take('mov rcx, rax'); call('prepareCarrier'); g.mark(label)
    def zero_guard(register, label):
        g.take(f'test {register}, {register}'); g.branch('je', label)

    g.take('push rbx','push rdi','push r12','push r14','sub rsp, 0x38',
           'mov rbx, r9','mov rdi, r8','mov r12, rdx','mov r14, rcx')
    zero_guard('rdx','nullKey')
    g.take('mov [rsp+0x70], rsi', f'mov rsi, {mem("rcx","comparer")}')
    zero_guard('rsi','earlyNullComparer')
    g.take(f'mov rax, {mem("r9","methodContext")}', 'mov [rsp+0x78], r13',
           'mov [rsp+0x30], r15', f'mov rcx, {mem("rax","genericContext")}',
           f'mov rax, {mem("rcx","comparerContext")}')
    prepare('wordProducerReady')
    g.take('mov ecx, 0x1','mov r9, r12','mov r8, rsi','mov rdx, rax'); call('keyWordProducer')
    g.take(f'mov rcx, {mem("rbx","methodContext")}', 'mov r15d, eax',
           f'mov rdx, {mem("rcx","genericContext")}', f'mov rcx, {mem("rdx","tablesContext")}',
           f'cmp {mem("rcx","methodContext")}, 0x0')
    g.branch('jne','contextReady')
    g.take(f'mov rcx, {mem("rbx","methodContext")}', f'mov rdx, {mem("rcx","genericContext")}',
           f'mov rcx, {mem("rdx","tablesContext")}', 'call [rcx]')
    if bytes.fromhex(rows[g.cursor-1]['bytes']) != b'\xff\x11':
        g.fail('context-call', 'qword call [rcx]', rows[g.cursor-1])
    g.mark('contextReady')
    g.take(f'mov rcx, {mem("rbx","methodContext")}', f'mov rbx, {mem("r14","tables")}',
           'mov [rsp+0x60], rbp', f'mov rdx, {mem("rcx","genericContext")}',
           f'mov r13, {mem("rdx","tablesContext")}')
    locked_stack_order(); zero_guard('rbx','nullStorage')
    g.take(f'mov rsi, {mem("rbx","bucketStorage")}'); zero_guard('rsi','nullStorage')
    g.take(f'mov rax, {mem("r13","methodContext")}', f'mov rcx, {mem("rax","genericContext")}',
           f'mov rax, {mem("rcx","arrayContext")}')
    prepare('arrayCarrierReady')
    g.take(f'cmp {mem("rax","initialized")}, 0x0'); g.branch('jne','arrayInitialized')
    g.take('mov rcx, rax'); call('initializeCarrier'); g.mark('arrayInitialized')
    g.take(f'mov rbx, {mem("rbx","bucketStorage")}'); zero_guard('rbx','nullStorage')
    g.take('mov eax, r15d')
    bit = g.take('btr eax, 0x1f')['bitResetOperation']
    extension = g.take('cdq')['dividendExtensionOperation']
    division = g.take(f'idiv dword {mem("rsi","arrayCount")}')['signedDivisionOperation']
    if (bit['bits'] != 32 or bit['selectedBit'] != 31 or not bit['zeroExtendsTo64']
            or extension['bits'] != 32 or division['bits'] != 32
            or division['remainderRegister'] != 'edx' or division['quotientRegister'] != 'eax'):
        g.fail('signed-index-dataflow', '32-bit sign-cleared word/CDQ/IDIV remainder EDX', [bit,extension,division])
    row = g.take(f'cmp edx, {mem("rbx","arrayCount")}')
    if bytes.fromhex(row['bytes'])[0] != 0x3b:
        g.fail('index-compare-width', 'unprefixed dword CMP', row)
    # ProgramGrammar's older branch subset does not claim unsigned JAE.
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
    if len(raw) != 6 or raw[:2] != b'\x0f\x83': g.fail('unsigned-index-guard', 'near JAE', row)
    target = at + 6 + int.from_bytes(raw[2:],'little',signed=True)
    if row['text'] not in (f'jcc 0x{target:x}',f'jae 0x{target:x}'):
        g.fail('index-guard-decoding', hex(target), row)
    g.edges.append((target,'boundsError',row))
    g.take('movsxd rax, edx',
           f'mov rbx, [rbx+0x{layout["arrayElements"]:x}+rax*{layout["arrayElementScale"]}]')
    if layout['arrayElementScale'] != 8:
        g.fail('reference-slot-width', 'qword pointer-sized scale 8', layout['arrayElementScale'])
    locked_stack_order(); zero_guard('rbx','miss'); g.take('nop')
    g.mark('nodeLoop'); g.take(f'cmp r15d, {mem("rbx","nodeWord")}'); g.branch('jne','nextNode')
    g.take(f'mov rsi, {mem("r14","comparer")}', f'mov rbp, {mem("rbx","nodeKey")}')
    zero_guard('rsi','nullStorage')
    g.take(f'mov rax, {mem("r13","methodContext")}', f'mov rcx, {mem("rax","genericContext")}',
           f'mov rax, {mem("rcx","comparerContext")}')
    prepare('predicateReady')
    g.take('xor ecx, ecx','mov [rsp+0x20], r12','mov r9, rbp','mov r8, rsi','mov rdx, rax')
    call('candidatePredicate'); g.take('test al, al'); g.branch('jne','hit')
    g.mark('nextNode'); g.take(f'mov rbx, {mem("rbx","nodeNext")}')
    locked_stack_order(); g.take('test rbx, rbx'); g.branch('jne','nodeLoop')
    g.mark('miss'); g.take('xor eax, eax','mov [rdi], rax')
    g.mark('epilogue')
    g.take('mov rbp, [rsp+0x60]','mov r13, [rsp+0x78]','mov r15, [rsp+0x30]',
           'mov rsi, [rsp+0x70]','add rsp, 0x38','pop r14','pop r12','pop rdi','pop rbx','ret')
    g.mark('hit'); row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
    if len(raw) != 7 or raw[:2] != b'\x83\x3d' or raw[-1] != 0:
        g.fail('barrier-zero-guard', 'dword RIP compare against zero', row)
    cell = at + 7 + struct.unpack_from('<i',raw,2)[0]
    if cell != base + c['barrierFlagCellRva']:
        g.fail('barrier-flag-cell', c['barrierFlagCellRva'],cell-base)
    g.take(f'mov rax, {mem("rbx","nodeValue")}', 'mov [rdi], rax'); g.branch('je','success')
    # The active branch is inventoried for branch ownership; its atomic/global
    # effects and reference lifetime are not part of this disabled-flag proof.
    g.take('shr rdi, 0xc'); g.pattern(r'lea rcx, \[rip.*\]')
    g.take('and edi, 0x1fffff','mov eax, edi','shr rax, 0x6','and edi, 0x3f',
           'lea rdx, [rcx+rax*8]','prefetch [rdx]','nop','nop')
    g.mark('activeBarrierLoop'); g.take('mov rax, [rdx]','mov rcx, rax','bts rcx, rdi',
                                       'lock cmpxchg [rdx], rcx')
    g.branch('jne','activeBarrierLoop'); g.mark('success')
    g.take('mov al, 0x1'); g.branch('jmp','epilogue')
    g.mark('nullKey')
    g.take(f'mov rax, {mem("r9","methodContext")}', f'mov rcx, {mem("rax","genericContext")}',
           f'mov rcx, {mem("rcx","arrayContext")}'); call('keyErrorCarrier')
    g.take(f'cmp {mem("rax","initialized")}, 0x0'); g.branch('jne','keyErrorReady')
    g.take('mov rcx, rax'); call('initializeCarrier'); g.mark('keyErrorReady')
    g.take(f'mov rax, {mem("rbx","methodContext")}',f'mov rcx, {mem("rax","genericContext")}',
           f'mov rcx, {mem("rcx","keyErrorContext")}'); call('throwKeyError'); g.take('int3')
    g.mark('earlyNullComparer'); call('nullError'); g.take('int3')
    g.mark('boundsError'); call('boundsError'); g.take('int3')
    g.mark('nullStorage'); call('nullError'); g.take('int3'); g.finish()
    return {'completeOwnedInstructionGrammarChecked':True,'checkedInstructions':len(rows),
        'sameStableBucketAddressExpressionProved':True,'originalWordRetainedForNodeComparison':True,
        'signClearedDwordRemainderIndexProved':True,'unsignedRemainderGuardProved':True,
        'conditionalNodeChainAndPredicateArgumentsProved':True,'conditionalMissClearsOutputAndReturnsFalse':True,
        'conditionalHitCopiesNodeValueAndReturnsTrue':True,'normalFrameAndNonvolatileRestorationProved':True,
        'wordProducerAndPredicateMeaningProved':False,'closedGenericLayoutMeaningProved':False,
        'activeBarrierEffectsProved':False,'liveDictionaryContentsProved':False,
        'conditions':['valid stable compatible storage and nonnull receiver/key/context/comparer/carriers',
            'carrier/helper calls return normally with ABI-preserved nonvolatile registers and compatible results',
            'positive signed dword divisor and compatible pointer-sized slots',
            'finite stable node chain; candidate predicate is selected only by its actual AL result',
            'disabled barrier flag for hit return; valid disjoint byref output and readable stack/reference storage'],
        'ordinaryIndexEquation':'(originalWord AND 0x7fffffff) % positiveSignedDivisor',
        'runtimeRegistrationStateJoined':False,'actualArrayCallbackTargetProved':False,
        'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
