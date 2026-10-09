"""Check the selected same-element Array.Copy byte-argument/return path.

The bulk callee is authenticated but its byte-copy implementation is a separate
proof. Runtime array classes, strides and helper branch outcomes stay explicit
conditions; no amount of argument forwarding admits old-value preservation.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.integer_addressing import decode_address_integer_instructions
from scripts.game_data.il2cpp.integer_registers import decode_integer_register_instructions
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data import buff_effect_line_center_population_native as population_owner
from scripts.game_data import buff_effect_line_center_points_native as point_owner

SCHEMA = 'endfield.buff-effect-line-center-copy-arguments-native-contract.v1'
LABEL = 'buffEffectLineCenterCopyArguments'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_copy_arguments_native.json'


def _fail(check, expected, actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _negative(g):
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    if len(raw) == 2 and raw[0] == 0x78: relative = raw[1:]
    elif len(raw) == 6 and raw[:2] == b'\x0f\x88': relative = raw[2:]
    else: g.fail('negative-branch', 'signed JS', row)
    target = at + len(raw) + int.from_bytes(relative, 'little', signed=True)
    if row['text'] not in (f'js 0x{target:x}', f'jcc 0x{target:x}'):
        g.fail('negative-branch-decoding', hex(target), row)
    return {**row, 'target': target}


def _outer(rows, fast_pointer):
    g = ProgramGrammar(rows, label=LABEL + '.arrayCopy')
    g.take('mov [rsp+0x10], rbx', 'mov [rsp+0x18], rsi', 'push rdi', 'push r12', 'push r13',
        'push r14', 'push r15', 'sub rsp, 0x70', 'mov r15d, r9d', 'mov rbx, r8',
        'mov r14d, edx', 'mov rdi, rcx', 'mov [rsp+0x60], 0x0', 'test rcx, rcx')
    rejected = [g.branch('je')]
    g.take('test rbx, rbx'); rejected.append(g.branch('je'))
    g.take('mov esi, [rsp+0xc0]', 'test esi, esi'); rejected.append(_negative(g))
    g.take('mov rdx, [rcx]', 'mov rax, [r8]', 'movzx ecx, [rax+0x134]', 'cmp [rdx+0x134], cl')
    rejected.append(g.branch('jne'))
    g.take('test r14d, r14d'); rejected.append(_negative(g))
    g.take('test r9d, r9d'); rejected.append(_negative(g))
    g.take('mov [rsp+0x20], esi', 'mov edx, r14d', 'mov rcx, rdi')
    call = g.call(fast_pointer); g.take('test al, al'); fallback = g.branch('je')
    g.take('lea r11, [rsp+0x70]', 'mov rbx, [r11+0x38]', 'mov rsi, [r11+0x40]', 'mov rsp, r11',
        'pop r15', 'pop r14', 'pop r13', 'pop r12', 'pop rdi', 'ret'); g.finish()
    return {'selectedEntryAndTrueReturnChecked': True, 'fastCall': call,
        'managedArgumentForwarding': {'source': 'incoming RCX', 'sourceIndex': 'incoming EDX',
            'destination': 'incoming R8', 'destinationIndex': 'incoming R9D', 'length': 'incoming fifth Int32 stack argument'},
        'errorEdges': rejected, 'falseResultFallback': fallback, 'errorAndFallbackImplementationsProved': False}


def _initial(rows):
    g = ProgramGrammar(rows, label=LABEL + '.fastPrefix')
    g.take('mov [rsp+0x10], rbx', 'mov [rsp+0x20], r9d', 'mov [rsp+0x18], r8', 'mov [rsp+0x8], rcx',
        'push rbp', 'push rsi', 'push rdi', 'push r12', 'push r13', 'push r14', 'push r15', 'sub rsp, 0x30',
        'movsxd r14, r9d', 'mov r12, r8', 'movsxd r15, edx', 'mov rdi, rcx', 'mov r11, [rcx]',
        'mov rax, [r8]', 'movzx r10d, [rax+0x134]', 'cmp [r11+0x134], r10b')
    refused = [g.branch('jne')]
    g.take('cmp [rcx+0x10], 0x0'); refused.append(g.branch('jne'))
    g.take('cmp [r8+0x10], 0x0'); refused.append(g.branch('jne'))
    g.take('movsxd r13, [rsp+0x90]', 'lea eax, [r14+r13*1]', 'cmp eax, [r8+0x18]')
    refused.append(g.branch('ja'))
    g.take('lea eax, [r15+r13*1]', 'cmp eax, [rcx+0x18]'); refused.append(g.branch('ja'))
    g.take('mov rbp, [r11+0x40]', 'mov rax, [r8]', 'mov rbx, [rax+0x40]')
    special = g.pattern(r'cmp rbp, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    selected = g.branch('jne'); g.finish()
    if len({row['target'] for row in refused}) != 1:
        g.fail('one-false-result-edge', 'one checked refusal target', refused)
    return {'selectedPrefixChecked': True, 'refusalEdges': refused, 'ordinaryElementClassEdge': selected,
        'anonymousClassComparison': special, 'boundsArithmeticBits': 32,
        'lengthCarrier': 'R13 = sign extension of fifth Int32 argument',
        'sourceIndexCarrier': 'R15 = sign extension of source Int32 index',
        'destinationIndexCarrier': 'R14 = sign extension of destination Int32 index',
        'runtimeArrayClassOrShapeMeaningProved': False}


def _same(rows):
    g = ProgramGrammar(rows, label=LABEL + '.sameElement')
    g.take('cmp rbp, rbx'); edge = g.branch('je'); g.finish()
    return edge


def _arguments(rows, bulk_pointer):
    g = ProgramGrammar(rows, label=LABEL + '.bulkArguments')
    g.take('mov rax, [r12]', 'movsxd rbx, [rax+0x100]', 'mov r8, rbx', 'imul r8, r13',
        'mov rax, rbx', 'imul rax, r15', 'mov rdx, [rsp+0x70]', 'add rdx, 0x20', 'add rdx, rax',
        'mov rcx, rbx', 'movsxd rax, r14d', 'imul rcx, rax', 'add rcx, 0x20', 'add rcx, r12')
    call = g.call(bulk_pointer); g.finish()
    for row in rows:
        if row['text'].startswith(('imul ', 'add rdx, rax', 'add rcx, r12')):
            if row.get('integerOperation', {}).get('bits') != 64:
                g.fail('byte-address-arithmetic-width', 'decoded qword arithmetic', row)
    return {'selectedArgumentBlockChecked': True, 'call': call,
        'byteCount': 'int64(length) * int64(runtime destination-class Int32 stride)',
        'sourceByteAddress': 'entry source reference + 32 + int64(source index) * stride',
        'destinationByteAddress': 'entry destination reference + 32 + int64(destination index) * stride',
        'integerArithmeticBits': 64, 'runtimeStrideProved': False, 'bulkCopyImplementationProved': False}


def _post(rows):
    g = ProgramGrammar(rows, label=LABEL + '.postCopy')
    flag = g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x0')
    if bytes.fromhex(flag['bytes'])[:2] != b'\x83\x3d':
        g.fail('post-flag-width', 'dword RIP-relative zero comparison', flag)
    g.branch('je', 'true')
    g.take('mov r8, rbx', 'movsxd rax, r14d', 'imul r8, rax', 'add r8, 0x20', 'add r8, r12',
        'shr r8, 0xc', 'and r8d, 0x1fffff', 'mov eax, r8d', 'shr rax, 0x6')
    bitmap = g.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('lea rdx, [rcx+rax*8]', 'and r8d, 0x3f', 'prefetch [rdx]', 'nop', 'nop')
    g.mark('retry'); g.take('mov rax, [rdx]', 'mov rcx, rax')
    bts = g.take('bts rcx, r8'); cas = g.take('lock cmpxchg [rdx], rcx')
    if bytes.fromhex(bts['bytes']) != bytes.fromhex('4C0FABC1') or bytes.fromhex(cas['bytes']) != bytes.fromhex('F0480FB10A'):
        g.fail('static-bitset-atomic-width', 'qword BTS and locked qword CMPXCHG', {'bts': bts, 'cas': cas})
    g.branch('jne', 'retry')
    g.mark('true'); g.take('mov al, 0x1'); edge = g.branch('jmp'); g.finish()
    return {'completeSelectedPostCallBlockChecked': True, 'flagRead': flag, 'staticBitsetBaseInstruction': bitmap,
        'optionalWrite': 'one qword compare/exchange in the static bitset; retries until success',
        'staticBitsetExtentBytes': 262144, 'trueReturnEdge': edge,
        'bulkCalleeNonvolatilePreservationRequired': ['rbx', 'r12', 'r14'],
        'staticBitsetDisjointFromArrayPayloadsRequired': True, 'runtimeRetryTerminationProved': False}


def _epilogue(rows):
    g = ProgramGrammar(rows, label=LABEL + '.fastEpilogue')
    g.take('mov rbx, [rsp+0x78]', 'add rsp, 0x30', 'pop r15', 'pop r14', 'pop r13',
        'pop r12', 'pop rdi', 'pop rsi', 'pop rbp', 'ret'); g.finish()
    return {'completeSelectedReturnFrameChecked': True, 'ALPreserved': True}


def _contract():
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (contract.get('scope') != 'conditional-same-element-bulk-arguments-and-post-copy-return'
            or set(contract.get('programs', {})) != {'arrayCopy', 'fastHelper', 'bulk'}
            or set(contract.get('blocks', {})) != {'outer', 'initial', 'same', 'arguments', 'post', 'epilogue'}):
        _fail('contract-blocks', 'six selected blocks', list(contract.get('blocks', {})))
    return contract


def _validate_image(image, contract):
    index = BodyIndex(image); selected = NativeReferenceContext(image, index=index); base = image.pe.image_base
    parent = population_owner._contract()
    if parent['nativeInputs'] != contract['nativeInputs']:
        _fail('same-parent-build', parent['nativeInputs'], contract['nativeInputs'])
    for role, program in contract['programs'].items():
        pointer = base + program['entryRva']
        owned = sorted(set([(pointer, index.extents.get(pointer, 0))] +
            [(at, at + size) for at, size in index.chained_fragments.get(pointer, ())]))
        actual = [(base + w['startRva'], base + w['endRva']) for w in program['windows']]
        if actual != owned: _fail('owned-windows:' + role, actual, owned)
        image.check_windows(program['windows'], label=LABEL)
    copy_pointer = base + contract['programs']['arrayCopy']['entryRva']
    if copy_pointer != base + parent['callTargets']['arrayCopy']:
        _fail('parent-copy-call', parent['callTargets']['arrayCopy'], copy_pointer - base)
    declaration = population_owner._array_copy_declaration(image, index, selected, copy_pointer)
    cap = parent['programs']['setCapacity']; image.check_windows(cap['windows'], label=LABEL)
    capacity = population_owner._set_capacity(*[
        decode_integer_register_instructions(image.mapper, image.window_bytes(w), base + w['startRva']) for w in cap['windows']],
        {role: base + rva for role, rva in parent['callTargets'].items()})
    rows = {}
    for role, block in contract['blocks'].items():
        program = contract['programs'][block['program']]
        if not any(w['startRva'] <= block['startRva'] < block['endRva'] <= w['endRva'] for w in program['windows']):
            _fail('owned-block:' + role, program['windows'], block)
        raw = image.window_bytes(block)
        rows[role] = decode_address_integer_instructions(image.mapper, raw, base + block['startRva'])
    fast_pointer = base + contract['programs']['fastHelper']['entryRva']
    bulk_pointer = base + contract['programs']['bulk']['entryRva']
    if contract['blocks']['outer']['startRva'] != copy_pointer - base or contract['blocks']['initial']['startRva'] != fast_pointer - base:
        _fail('called-selected-prefix', 'actual caller and actual helper entry', contract['blocks'])
    outer = _outer(rows['outer'], fast_pointer); initial = _initial(rows['initial'])
    same = _same(rows['same']); arguments = _arguments(rows['arguments'], bulk_pointer)
    post = _post(rows['post']); epilogue = _epilogue(rows['epilogue'])
    for edge, role in [(initial['ordinaryElementClassEdge'], 'same'), (same, 'arguments'), (post['trueReturnEdge'], 'epilogue')]:
        if edge['target'] != base + contract['blocks'][role]['startRva']:
            _fail('selected-edge:' + role, contract['blocks'][role]['startRva'], edge)
    if contract['blocks']['arguments']['endRva'] != contract['blocks']['post']['startRva']:
        _fail('post-call-fallthrough', contract['blocks']['arguments']['endRva'], contract['blocks']['post']['startRva'])
    if contract['blocks']['same']['startRva'] != initial['ordinaryElementClassEdge']['target'] - base:
        _fail('class-selection-entry', initial['ordinaryElementClassEdge'], contract['blocks']['same'])
    return {'arrayCopyDeclaration': declaration, 'parentCapacity': capacity, 'outer': outer, 'initial': initial,
        'sameElementEdge': same, 'arguments': arguments, 'postCopy': post, 'epilogue': epilogue,
        'sameElementBulkArgumentsProved': True, 'selectedPostCopyTrueReturnProved': True,
        'oldCountToBulkByteLengthJoinProved': True, 'bulkOwnedBytesAuthenticated': sum(w['endRva'] - w['startRva'] for w in contract['programs']['bulk']['windows']),
        'bulkCopyImplementationProved': False, 'runtimeStrideProved': False,
        'existingValuesPreservedAcrossResizeProved': False, 'runtimeExecutionObserved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches(): return {'status': 'mismatched', 'detail': 'Selected UnityPlayer missing or different', 'nativeInputs': pins}
    result = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not matches():
        return {'status': 'mismatched', 'detail': 'Selected native inputs changed during copy-argument validation', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, **result, 'evidenceBoundary': contract['evidenceBoundary']}
