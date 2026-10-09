"""Bounded buffered reads carried directly to metadata-owned reference Data.

The selected contract supplies code locations and programs. This algorithm
checks actual instruction successors, pointer ownership and value transfers;
ordinary nonvolatile preservation across returning calls stays conditional.
It does not choose a live formatter or infer wire widths from object sizes.
"""
from __future__ import annotations

from typing import Any, Callable

from scripts.game_data.il2cpp.body_claims import _writes_register
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import struct_output_sources as structs
from scripts.game_data.memorypack import inherited_reference_sources as inherited

REGISTERS = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
             *(f'r{i}' for i in range(8, 16)))
VOLATILE = frozenset(('rax', 'rcx', 'rdx', 'r8', 'r9', 'r10', 'r11',
                      *(f'xmm{i}' for i in range(6))))
LABEL = 'bufferedOwnedSource'


def _memory(raw: bytes, opcode: bytes) -> dict[str, Any] | None:
    """Decode only unsized-base, disp8/disp32 operands used by these profiles."""
    at = 0
    prefix = raw[0] if raw[0] in (0xf3, 0xf2) else 0
    if prefix:
        at += 1
    rex = raw[at] if at < len(raw) and 0x40 <= raw[at] <= 0x4f else 0
    if rex:
        at += 1
    if raw[at:at + len(opcode)] != opcode:
        return None
    at += len(opcode)
    if at >= len(raw):
        return None
    modrm = raw[at]; at += 1
    mode, rm = modrm >> 6, modrm & 7
    if rm == 4 or mode not in (0, 1, 2) or mode == 0 and rm == 5:
        return None
    width = 0 if mode == 0 else 1 if mode == 1 else 4
    if len(raw) != at + width:
        return None
    register = ((modrm >> 3) & 7) + (8 if rex & 4 else 0)
    return {'register': REGISTERS[register], 'registerIndex': register,
            'base': REGISTERS[rm + (8 if rex & 1 else 0)],
            'offset': int.from_bytes(raw[at:], 'little', signed=True) if width else 0,
            'rex': rex, 'prefix': prefix}


def _move(raw: bytes) -> tuple[str, str] | None:
    if (len(raw) != 3 or not 0x48 <= raw[0] <= 0x4f
            or raw[1] not in (0x8b, 0x89) or raw[2] >> 6 != 3):
        return None
    reg = ((raw[2] >> 3) & 7) + (8 if raw[0] & 4 else 0)
    rm = (raw[2] & 7) + (8 if raw[0] & 1 else 0)
    return ((REGISTERS[reg], REGISTERS[rm]) if raw[1] == 0x8b
            else (REGISTERS[rm], REGISTERS[reg]))


def _program(image: Any, window: dict, program: list, fail: Callable) -> list[dict]:
    """Authenticate each complete instruction and its selected local successor."""
    if not isinstance(program, list) or not 1 <= len(program) <= 2048:
        fail('program-count', 'bounded nonempty selected program', program)
    rows = []
    seen = set()
    for item in program:
        if not isinstance(item, list) or len(item) != 2 or type(item[0]) is not int:
            fail('program-row', '[RVA, complete instruction hex]', item)
        at, hex_value = item; raw = bytes.fromhex(hex_value)
        if (not raw or at in seen or not window['startRva'] <= at < at + len(raw) <= window['endRva']):
            fail('program-boundary', window, item)
        seen.add(at)
        image.check_instruction_windows([item], label=LABEL)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or decoded[0]['text'].startswith('db'):
            fail('program-instruction', 'one understood complete instruction', item)
        rows.append(decoded[0])
    for (at, hex_value), following in zip(program, program[1:]):
        raw = bytes.fromhex(hex_value); fallthrough = at + len(raw)
        allowed = {fallthrough}
        if raw[0] in (0xe9, 0xeb):
            if len(raw) != (5 if raw[0] == 0xe9 else 2):
                fail('program-jump-width', 'complete jump', [at, hex_value])
            allowed = {fallthrough + int.from_bytes(raw[1:], 'little', signed=True)}
        elif 0x70 <= raw[0] <= 0x7f and len(raw) == 2:
            allowed.add(fallthrough + int.from_bytes(raw[1:], 'little', signed=True))
        elif raw[:1] == b'\x0f' and len(raw) == 6 and 0x80 <= raw[1] <= 0x8f:
            allowed.add(fallthrough + int.from_bytes(raw[2:], 'little', signed=True))
        elif raw[0] in (0xc3, 0xcc):
            allowed = set()
        if following[0] not in allowed:
            fail('program-successor', sorted(allowed), following)
    return rows


def validate_object_header_source(image: Any, proof: dict, offsets: dict, *, fail: Callable) -> dict:
    """Buffered original byte to caller slot; FF comparison to the returned AL.

    This covers the complete ordinary frame. Refills and negative remaining
    counts leave this selected window and remain separate conditional paths.
    """
    pointer, remaining, advanced, consumed = (f'{offsets[n]:02X}' for n in
        ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    expected = ['48895C2408', '4889742410', '57', '4883EC20', f'8379{remaining}01',
        '488BF2', '488BD9', 'jl32', f'488B43{pointer}', '0FB608', '880E',
        f'8B7B{remaining}', '83EF01', 'js32', f'48FF43{pointer}', f'FF43{advanced}',
        f'FF43{consumed}', f'897B{remaining}', '803EFF', '488B5C2430',
        '488B742438', '0F95C0', '4883C420', '5F', 'C3']
    program, window = proof['program'], proof['window']
    image.check_windows([window], label=LABEL)
    references._program(image, window, program, fail)
    inherited._program(image, program, expected, fail=fail)
    if program[0][0] != window['startRva'] or program[-1][0] + 1 != window['endRva']:
        fail('object-header-full-frame', 'owned entry through RET', proof)
    for index, prefix in ((7, b'\x0f\x8c'), (13, b'\x0f\x88')):
        row = program[index]; raw = bytes.fromhex(row[1])
        target = inherited._target(row)
        if len(raw) != 6 or raw[:2] != prefix or window['startRva'] <= target < window['endRva']:
            fail('object-header-external-cold-branch', prefix.hex(), row)
    return {'directBytes': 1, 'outputBits': 8, 'nullByte': 255,
        'trueRegister': 'AL', 'completeOrdinaryReturn': True}


def validate_int32_source(image: Any, proof: dict, offsets: dict, *, fail: Callable) -> None:
    """Complete physical Int32 buffered return, including four cursor bytes."""
    program = proof['program']; window = proof['window']
    image.check_windows([window], label=LABEL)
    pointer, remaining, advanced, consumed = (offsets[n] for n in
        ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    expected = ['48895C2408', '4889742410', '57', '4883EC20', f'8379{remaining:02X}04',
        '488BD9', None, f'488B43{pointer:02X}', '8B30', f'8B7B{remaining:02X}', '83EF04', None,
        f'488343{pointer:02X}04', f'8343{advanced:02X}04', f'8343{consumed:02X}04',
        f'897B{remaining:02X}', '488B5C2430', '8BC6', '488B742438', '4883C420', '5F', 'C3']
    if len(program) != len(expected) or program[0][0] != window['startRva']:
        fail('int32-complete-program', len(expected), program)
    _program(image, window, program, fail)
    for position, ((at, actual), wanted) in enumerate(zip(program, expected, strict=True)):
        if wanted is not None:
            if actual != wanted:
                fail('int32-instruction', wanted, [at, actual])
        else:
            raw = bytes.fromhex(actual); prefix = b'\x0f\x8c' if position == 6 else b'\x0f\x88'
            target = at + len(raw) + int.from_bytes(raw[2:], 'little', signed=True)
            if len(raw) != 6 or raw[:2] != prefix or window['startRva'] <= target < window['endRva']:
                fail('int32-external-cold-branch', prefix.hex(), [at, actual])
    if program[-1][0] + 1 != window['endRva']:
        fail('int32-return-end', window['endRva'], program[-1])


def validate_inline_cursor(image: Any, window: dict, member: dict, offsets: dict,
                           *, fail: Callable) -> None:
    """Read four original bytes, subtract remaining and commit all counters."""
    program = member['cursorProgram']; _program(image, window, program, fail)
    codes = [r[1] for r in program]
    if codes[0] != f'488B43{offsets["currentPtr"]:02X}' or program[1][0] != member['sourceReadRva']:
        fail('inline-buffer-source', 'actual original buffer pointer then field read', program[:2])
    load = _memory(bytes.fromhex(codes[1]), b'\x8b') or _memory(bytes.fromhex(codes[1]), b'\x0f\x10')
    if (load is None or load['base'] != 'rax' or load['offset'] != 0 or load['rex'] & 8
            or member['declaredType'] == 'float' and load['prefix'] != 0xf3
            or member['declaredType'] == 'int' and load['prefix']):
        fail('inline-four-byte-load', member['declaredType'], codes[1])
    if len(program) != 9:
        fail('inline-cursor-program-count', 9, program)
    remaining = _memory(bytes.fromhex(codes[2]), b'\x8b')
    if (remaining is None or remaining['base'] != 'rbx'
            or remaining['offset'] != offsets['bufferLength'] or remaining['rex'] or remaining['prefix']):
        fail('inline-remaining-load', offsets['bufferLength'], codes[2])
    register = remaining['registerIndex']
    expected = [bytes((0x83, 0xe8 | register, 4)).hex().upper(), codes[4],
        f'488343{offsets["currentPtr"]:02X}04', f'8343{offsets["advancedCount"]:02X}04',
        f'8343{offsets["consumed"]:02X}04', bytes((0x89, 0x43 | register << 3, offsets['bufferLength'])).hex().upper()]
    branch = bytes.fromhex(codes[4])
    if (codes[3:] != expected or len(branch) != 2 or branch[0] != 0x79
            or program[4][0] + 2 + int.from_bytes(branch[1:], 'little', signed=True) != program[5][0]):
        fail('inline-cursor-commit', 'subtract four; JNS to pointer/advanced/consumed/remaining commits', program)


def validate_owned_program(image: Any, record: dict, offsets: dict, *, fail: Callable) -> list[dict]:
    """One selected entry-to-last-store program must prove every ordered field."""
    selected = NativeReferenceContext(image)
    image.validate_method_row(record['readerMethod'], label=LABEL)
    structs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    if (image.type_name(record['runtimeTypeDefinition']) != record['runtimeTypeName']
            or selected.field(record['wrapperTypeName'] + '::__instance') !=
            (record['wrapperTypeName'], record['runtimeTypeName'], 16)):
        fail('owned-instance-type', 'exact typed wrapper instance at sixteen', record['wrapperTypeName'])
    program = record['positiveProgram']; window = record['sourceWindow']
    image.check_windows([window], label=LABEL)
    rows = _program(image, window, program, fail)
    if program[0][0] != record['readerMethod'][3] or program[-1][0] != record['members'][-1]['storeRva']:
        fail('owned-program-extent', 'actual entry through final field store', [program[0], program[-1]])
    calls = {}; contexts = {}; fields = {}; inline = {}
    for member in record['members']:
        field = selected.field(record['runtimeTypeName'] + '::' + member['fieldName'])
        if field != (record['runtimeTypeName'], member['declaredType'], member['fieldOffset']):
            fail('owned-field', member, field)
        if member['storeRva'] in fields or member['sourceReadRva'] in calls or member['sourceReadRva'] in inline:
            fail('owned-member-bijection', 'distinct source and destination instructions', member)
        fields[member['storeRva']] = member
        if member['kind'] == 'inline-original-buffer-load':
            validate_inline_cursor(image, window, member, offsets, fail=fail)
            inline[member['sourceReadRva']] = member
        else:
            named.check_call(image, member['sourceCall'], label=LABEL, fail=fail)
            calls[member['sourceReadRva']] = member
        if 'sourceContext' in member:
            context = member['sourceContext']
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=fail)
            references._return_type(image, context, fail)
            contexts[context['instructionRva']] = member
    pointers = {'rcx': 'reader', 'rdx': 'ref-wrapper'}; values = {}; stores = []; reads = []
    for (at, raw_hex), row in zip(program, rows, strict=True):
        raw = bytes.fromhex(raw_hex)
        if at in contexts:
            member = contexts[at]
            if not raw.startswith(b'\x48\x8b\x15'):
                fail('owned-source-context-register', 'RDX exact closed context', raw_hex)
            pointers['rdx'] = ('context', member['sourceContext']['instructionRva'])
            values.pop('rdx', None); continue
        store = _memory(raw, b'\x89') or _memory(raw, b'\x88') or _memory(raw, b'\x0f\x11')
        if store and pointers.get(store['base']) == 'data':
            member = fields.get(at)
            register = 'xmm' + str(store['registerIndex']) if store['prefix'] == 0xf3 else store['register']
            width = 64 if store['rex'] & 8 else 8 if raw[0] == 0x88 else 32
            value = values.get(register)
            if (member is None or store['offset'] != member['fieldOffset'] or width != member['widthBits']
                    or value != (member['sourceReadRva'], member['declaredType'], member['widthBits'])):
                fail('owned-source-to-field', member, [at, store, value])
            stores.append(member['fieldName'])
        if row['text'].startswith('call '):
            member = calls.get(at)
            if member:
                context = member.get('sourceContext')
                if (pointers.get('rcx') != 'reader' or context is not None
                        and pointers.get('rdx') != ('context', context['instructionRva'])):
                    fail('owned-reader-context-arguments', 'reader RCX and exact closed context RDX', pointers)
                reads.append(member['fieldName'])
            for register in VOLATILE:
                pointers.pop(register, None); values.pop(register, None)
            if member:
                values['rax'] = (member['sourceReadRva'], member['declaredType'], member['widthBits'])
            continue
        move = _move(raw)
        if move:
            dst, src = move; pointer = pointers.get(src); value = values.get(src)
            pointers.pop(dst, None); values.pop(dst, None)
            if pointer is not None: pointers[dst] = pointer
            if value is not None: values[dst] = value
            continue
        load = _memory(raw, b'\x8b'); vector = _memory(raw, b'\x0f\x10')
        if load or vector:
            load = load or vector
            dst = 'xmm' + str(load['registerIndex']) if vector and load['prefix'] == 0xf3 else load['register']
            origin = pointers.get(load['base']); pointers.pop(dst, None); values.pop(dst, None)
            if load['rex'] & 8:
                if origin == 'ref-wrapper' and load['offset'] == 0: pointers[dst] = 'wrapper'
                elif origin == 'wrapper' and load['offset'] == 16: pointers[dst] = 'data'
                elif origin == 'reader' and load['offset'] == offsets['currentPtr']: pointers[dst] = 'reader-buffer'
            elif at in inline:
                member = inline[at]
                if origin != 'reader-buffer' or load['offset'] != 0:
                    fail('owned-inline-source', 'actual original buffer', [at, origin])
                values[dst] = (at, member['declaredType'], 32); reads.append(member['fieldName'])
            continue
        for register in set(pointers) | set(values):
            if _writes_register(row, register):
                pointers.pop(register, None); values.pop(register, None)
    expected = [m['fieldName'] for m in record['members']]
    if reads != expected or stores != expected:
        fail('owned-ordered-complete-fields', expected, {'reads': reads, 'stores': stores})
    return [{'fieldName': m['fieldName'], 'declaredType': m['declaredType'], 'kind': m['kind']}
            for m in record['members']]
