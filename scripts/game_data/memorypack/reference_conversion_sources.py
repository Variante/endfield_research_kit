"""Complete selected reference conversion programs under explicit type selection.

The programs own branches, stack slots and arguments through RET. Concrete
provider returns and inflated runtime contexts remain conditions; this module
never chooses them, infers a wire width or grants an enclosing list admission.
"""
from __future__ import annotations

import re
import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.buffered_owned_sources import _memory, _move, VOLATILE

LOCAL_OPS = {
    '32C0': 'xor al, al',
    'F6803801000001': 'test byte [rax+0x138], 1',
    '480307': 'add rax, [rdi]', '4803C9': 'add rcx, rcx',
    '4803D2': 'add rdx, rdx', '03C5': 'add eax, ebp',
    '4898': 'cdqe', '4803C6': 'add rax, rsi',
}


def _target(at: int, raw: bytes) -> int:
    offset = 2 if raw[:1] == b'\x0f' else 1
    return at + len(raw) + int.from_bytes(raw[offset:], 'little', signed=True)


def validate_program(image: Any, proof: dict, *, fail: Callable,
                     extra_opcodes: dict[str,str] | None = None) -> list[dict]:
    """Authenticate complete instructions and every selected edge, loops included."""
    windows, program = proof['codeWindows'], proof['program']
    opcodes = dict(LOCAL_OPS)
    for raw, text in (extra_opcodes or {}).items():
        if raw in opcodes and opcodes[raw] != text:
            fail('conversion-opcode-conflict', opcodes[raw], text)
        opcodes[raw] = text
    if not windows or not 1 <= len(program) <= 2048:
        fail('conversion-program-size', 'bounded windows and selected trace', len(program))
    image.check_windows(windows, label='referenceConversionSource')
    if program[0][0] != windows[0]['startRva'] or program[-1][1] != 'C3':
        fail('conversion-entry-return', 'physical entry through RET', [program[0], program[-1]])
    rows = []
    for at, raw_hex in program:
        raw = bytes.fromhex(raw_hex)
        if not raw or not any(w['startRva'] <= at < at + len(raw) <= w['endRva'] for w in windows):
            fail('conversion-program-owner', 'one selected owned window', [at, raw_hex])
        image.check_instruction_windows([[at, raw_hex]], label='referenceConversionSource')
        if raw_hex in opcodes:
            row = {'va':hex(image.pe.image_base + at), 'bytes':raw_hex, 'text':opcodes[raw_hex]}
        else:
            decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
            if len(decoded) != 1 or 'db ' in decoded[0]['text']:
                fail('conversion-complete-instruction', 'understood complete instruction', [at,raw_hex])
            row = decoded[0]
        rows.append(row)
    for (at, raw_hex), following in zip(program, program[1:]):
        raw = bytes.fromhex(raw_hex); allowed = {at + len(raw)}
        if raw[0] in (0xe9,0xeb):
            allowed = {_target(at,raw)}
        elif (len(raw) == 2 and 0x70 <= raw[0] <= 0x7f
              or len(raw) == 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f):
            allowed.add(_target(at,raw))
        elif raw[0] in (0xc3,0xcc):
            allowed = set()
        if following[0] not in allowed:
            fail('conversion-selected-edge', sorted(allowed), following)
    return rows


def _profile(image: Any, proof: dict, expected: list, *, fail: Callable) -> None:
    validate_program(image, proof, fail=fail)
    if len(proof['program']) != len(expected):
        fail('conversion-profile-size', len(expected), len(proof['program']))
    for n, (row,wanted) in enumerate(zip(proof['program'],expected,strict=True)):
        if wanted is not None and row[1] != wanted:
            fail('conversion-profile-transfer', {'position':n,'bytes':wanted},row)


def _comparisons(proof: dict, positions: list, pointer_rvas: list, *,
                 opcode: bytes, taken: bool, fail: Callable) -> list[int]:
    targets = []
    for position in positions:
        n, branch_n = position if isinstance(position,tuple) else (position,position + 2)
        at, raw_hex = proof['program'][n]; raw = bytes.fromhex(raw_hex)
        branch_at, branch_hex = proof['program'][branch_n]; branch = bytes.fromhex(branch_hex)
        if raw[:3] != b'\x48\x8d\x05' or len(raw) != 7 or branch[:len(opcode)] != opcode:
            fail('conversion-pointer-guard', 'RIP LEA and actual conditional branch', [at,raw_hex,branch_hex])
        candidate = at + 7 + int.from_bytes(raw[3:], 'little', signed=True)
        next_at = proof['program'][branch_n + 1][0]
        if (candidate in pointer_rvas or next_at != (_target(branch_at,branch) if taken else branch_at + len(branch))):
            fail('conversion-concrete-fallback', 'concrete pointer differs from optimized candidates', [candidate,pointer_rvas,next_at])
        targets.append(candidate)
    return targets


def validate_formatter_dispatch(image: Any, proof: dict, pointer_rvas: list, *,
                                fail: Callable) -> dict:
    """Slot five loads receiver vtable method/MethodInfo and forwards all refs."""
    expected = ['48895C2408','55','56','57','4154','4155','4156','4157','4881EC80000000',
        '4D8BE9','4D8BF8','488BFA','0FB7D9','488B0A',None,'488D4314','48C1E004',
        '480307','4C8B10','488B5808','48899C24D8000000',None,'4C3BD0',None,
        None,'4C3BD0',None,None,'4C3BD0',None,'4C8BCB','4D8BC5','498BD7','488BCF',
        '41FFD2','488B9C24C0000000','4881C480000000','415F','415E','415D','415C','5F','5E','5D','C3']
    _profile(image,proof,expected,fail=fail)
    comparisons = _comparisons(proof,[21,24,27],pointer_rvas,opcode=b'\x0f\x85',taken=True,fail=fail)
    call_at, raw_hex = proof['program'][14];raw = bytes.fromhex(raw_hex)
    if len(raw) != 5 or raw[0] != 0xe8:
        fail('conversion-class-prepare-call', 'actual relative class helper', [call_at,raw_hex])
    return {'slot':5,'receiverRegister':'rcx','readerRegister':'rdx','outputRegister':'r8',
            'companionRegister':'r9','optimizedPointerRvas':comparisons,
            'classPrepareHelperRva':_target(call_at,raw)}


def validate_interface_conversion(image: Any, proof: dict, getter_rvas: list, *,
                                  fail: Callable) -> dict:
    """Two exact interface-table probes, slot-zero getter and preserved RAX."""
    expected = ['4053','55','56','57','4155','4883EC40','498B30','498BF8','0FB7E9','488BDA','488BCE',None,
        '440FB78630010000','4533ED','410FB7C5','66453BE8',None,'488B96B0000000',
        '0FB7C8','4803C9','48391CCA',None,'66FFC0','66413BC0',None,
        '0FB7C8','4803C9','48391CCA',None,'0FB7D0','488B86B0000000','4803D2','8B44D008',
        '03C5','4898','4883C014','48C1E004','4803C6','4C8B00','488B5808',None,
        '4C89742478','4C89BC2488000000','4C3BC0',None,None,'4C3BC0',None,None,'4C3BC0',None,
        '488BD3','488BCF','41FFD0','4C8BBC2488000000','4C8B742478','4883C440','415D','5F','5E','5D','5B','C3']
    _profile(image,proof,expected,fail=fail)
    for n, opcode, take in ((16,b'\x73',False),(21,b'\x74',False),(24,b'\x72',True),(28,b'\x74',True)):
        at, raw_hex = proof['program'][n];raw = bytes.fromhex(raw_hex)
        if raw[:1] != opcode or proof['program'][n + 1][0] != (_target(at,raw) if take else at + len(raw)):
            fail('conversion-interface-probe-edge', {'position':n,'taken':take},[at,raw_hex])
    if proof['program'][25] != proof['program'][18] or proof['program'][28] != proof['program'][21]:
        fail('conversion-interface-loop', 'same lookup/compare revisited at ordinal one', proof['program'][18:29])
    comparisons = _comparisons(proof,[(40,44),45],getter_rvas,opcode=b'\x74',taken=False,fail=fail)
    comparisons += _comparisons(proof,[48],getter_rvas,opcode=b'\x0f\x84',taken=False,fail=fail)
    at, raw_hex = proof['program'][11];raw = bytes.fromhex(raw_hex)
    if len(raw) != 5 or raw[0] != 0xe8:
        fail('conversion-interface-class-call','actual relative helper',[at,raw_hex])
    return {'interfaceOrdinal':1,'interfaceMethodSlot':0,'interfacePairBytes':16,
            'optimizedPointerRvas':comparisons,'classPrepareHelperRva':_target(at,raw),
            'getterReceiverRegister':'rcx','getterCompanionRegister':'rdx','returnRegister':'rax'}


def _canonical(register: str) -> str:
    aliases = {'eax':'rax','ax':'rax','al':'rax','ah':'rax','ecx':'rcx','cx':'rcx','cl':'rcx',
        'edx':'rdx','dx':'rdx','dl':'rdx','ebx':'rbx','bx':'rbx','bl':'rbx','esi':'rsi','si':'rsi',
        'edi':'rdi','di':'rdi','ebp':'rbp','bp':'rbp','esp':'rsp'}
    return aliases.get(register,re.sub(r'^(r\d+)[dwb]$',r'\1',register))


def _qword(raw: bytes) -> bool:
    """REX.W establishes a qword operand; an opcode bit never does."""
    at = 0
    while at < len(raw) and raw[at] in (0x66,0xf2,0xf3):
        at += 1
    return at < len(raw) and 0x48 <= raw[at] <= 0x4f


def _integer_write(raw: bytes, *, immediate: bool) -> int | None:
    """Return a complete GPR literal, withholding partial 8/16-bit writes.

    A 32-bit destination zero-extends; REX.W C7 sign-extends its imm32.
    The subset mapper's register spelling is insufficient for that distinction.
    None deliberately destroys a saved pointer identity after a partial write.
    """
    at = 0
    word = raw[:1] == b'\x66'
    if word:
        at += 1
    rex = raw[at] if at < len(raw) and 0x40 <= raw[at] <= 0x4f else 0
    if rex:
        at += 1
    if at >= len(raw):
        return None
    opcode = raw[at]
    width = 64 if rex & 8 else 16 if word else 32
    if not immediate:
        return 0 if opcode in (0x31, 0x33) and width >= 32 else None
    if 0xb8 <= opcode <= 0xbf:
        size = width // 8
        return int.from_bytes(raw[at + 1:], 'little') if width >= 32 and len(raw) == at + 1 + size else None
    if (opcode == 0xc7 and width >= 32 and len(raw) == at + 6
            and raw[at + 1] & 0xf8 == 0xc0):
        return int.from_bytes(raw[at + 2:], 'little', signed=width == 64) & ((1 << 64) - 1)
    return None


def _data_memory(raw: bytes, opcode: bytes) -> dict | None:
    operand = _memory(raw,opcode)
    if operand is not None:
        return operand
    # No-index SIB encodes [r12], distinct from a frame-relative [rsp+disp].
    if (len(raw) == 4 and 0x48 <= raw[0] <= 0x4f and raw[0] & 1
            and raw[1:2] == opcode and raw[2] & 0xc7 == 4 and raw[3] == 0x24):
        names = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*(f'r{i}'for i in range(8,16)))
        reg = ((raw[2] >> 3) & 7) + (8 if raw[0] & 4 else 0)
        return {'register':names[reg],'base':'r12','offset':0}
    return None


def validate_conversion_context(image: Any, context: dict, entries: Any, *,
                                fail: Callable) -> dict:
    """Join static RGCTX payload indices to reciprocal class VAR owners.

    The caller authenticates the complete context range first. These static
    identities constrain a supplied inflated context; they do not observe it.
    """
    selected = NativeReferenceContext(image)
    owner = image.metadata.types[context['definition']]
    section = image.metadata.sections['genericContainers']
    at = section.offset + owner.generic_container_index * 16
    if (context['isMethod'] or context['typeName'] != 'Beyond.MemoryPack.GenericMemoryPackFormatter`2'
            or image.type_name(owner.index) != context['typeName']
            or owner.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16):
        fail('conversion-context-owner', 'owned adapter class context', context['definition'])
    owner_index, count, is_method, start = struct.unpack_from('<iiii', image.metadata.buf, at)
    if (owner_index, count, is_method) != (owner.index, 2, 0) or start < 0:
        fail('conversion-context-container', 'two owned class parameters', [owner_index,count,is_method,start])
    containers = [td.generic_container_index for td in image.metadata.types]
    for ordinal in range(2):
        identity = type_parameter_owner(image.metadata.buf, start + ordinal, containers, source='referenceConversionSource')
        if identity['typeIndex'] != owner.index or identity['ordinal'] != ordinal:
            fail('conversion-var-owner', [owner.index,ordinal], identity)

    slots = {row['relativeSlot']:row for row in context['entries']}
    if len(slots) != len(context['entries']) or any(n not in slots for n in (4,5,6,8,9)):
        fail('conversion-context-slots', 'unique provider/formatter/interface method slots', sorted(slots))

    def payload(slot, kind):
        row = slots[slot];raw = bytes.fromhex(row['rawHex'])
        if (len(raw) != 16 or int.from_bytes(raw[:4],'little') != kind or row['kind'] != kind
                or image.pe.u32_at_va(int.from_bytes(raw[8:],'little')) != row['index']):
            fail('conversion-context-payload', {'slot':slot,'kind':kind,'index':row['index']},row)
        return row

    def argument(instance, ordinal):
        arguments = image.instantiations.resolve(instance).arguments
        if len(arguments) != 1:
            fail('conversion-context-arity', 'one owned class VAR argument', len(arguments))
        raw = image.pe.bytes_at_va(arguments[0].type_pointer_va,16)
        if raw[10:12] != b'\x13\x00' or int.from_bytes(raw[:8],'little') != start + ordinal:
            fail('conversion-context-var', {'ordinal':ordinal,'parameterIndex':start+ordinal},raw.hex())
        return arguments[0].type_pointer_va

    method_instances = {}
    for slot, type_name, method_name, ordinal, class_argument in (
            (4,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',1,False),
            (6,'MemoryPack.MemoryPackFormatter`1','Deserialize',1,True),
            (9,'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1','GetValue',0,True)):
        row = payload(slot,3);index = row['index']
        if type(index) is not int or not 0 <= index < len(entries.specs):
            fail('conversion-method-spec-range', 'selected MethodSpec index', index)
        spec = entries.specs[index];method = image.metadata.methods[spec[0]]
        ci, mi = spec[1:]
        instance = ci if class_argument else mi
        if (list(spec) != row['methodSpec'] or (mi if class_argument else ci) != -1
                or image.type_name(method.declaring_type) != type_name
                or image.metadata.string(method.name_index) != method_name):
            fail('conversion-context-method', [type_name,method_name], [spec,row])
        method_instances[slot] = (instance,argument(instance,ordinal))

    for slot, type_name, method_slot, ordinal in (
            (5,'MemoryPack.MemoryPackFormatter`1',4,1),
            (8,'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',9,0)):
        row = payload(slot,2);raw = image.pe.bytes_at_va(selected.type_pointer(row['index']),16)
        if raw[10:12] != b'\x15\x00':
            fail('conversion-context-generic-type', 'undecorated reference instantiation', raw.hex())
        definition_pointer, instance_pointer = struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
        definition = image.pe.bytes_at_va(definition_pointer,16)
        if definition[10:12] != b'\x12\x00' or image.type_name(int.from_bytes(definition[:8],'little')) != type_name:
            fail('conversion-context-generic-definition', type_name, definition.hex())
        instance = image.instantiations.resolve_pointer(instance_pointer)
        if (instance.index,argument(instance.index,ordinal)) != method_instances[method_slot]:
            fail('conversion-context-instance-join', method_instances[method_slot], instance.as_dict())
    if method_instances[4] != method_instances[6]:
        fail('conversion-provider-deserialize-argument', 'same owned wrapper parameter', method_instances)
    return {'originalParameterOrdinal':0,'wrapperParameterOrdinal':1,
            'authenticatedRelativeSlots':[4,5,6,8,9],'runtimeInflationObserved':False}


def validate_nonnull_transfer(image: Any, proof: dict, calls: dict, *,
                              null_wrapper: bool, fail: Callable) -> dict:
    """Track saved reader/companion reloads, incoming wrap and original output."""
    rows = validate_program(image,proof,fail=fail)
    registers = {'rcx':'reader','rdx':'originalOut','r8':'incomingWrap','r9':'companion'}
    slots = {}; sp = 0; dispatched = []; converted = []; outputs = []; reloads = []; wrapper_guard = None
    context_slots = {0x20:'wrapperFormatterContext',0x40:'originalConversionInterface'}
    for n, ((at,raw_hex), row) in enumerate(zip(proof['program'],rows,strict=True)):
        raw = bytes.fromhex(raw_hex); text = row['text']
        stack_move = re.fullmatch(r'mov (\[rsp\+0x([0-9a-f]+)\]), ([a-z0-9]+)',text)
        stack_read = re.fullmatch(r'mov ([a-z0-9]+), \[rsp\+0x([0-9a-f]+)\]',text)
        stack_lea = re.fullmatch(r'lea ([a-z0-9]+), \[rsp\+0x([0-9a-f]+)\]',text)
        if text.startswith('push '):
            sp -= 8;slots[sp] = registers.get(text[5:]);continue
        if text.startswith('pop '):
            registers[text[4:]] = slots.get(sp);sp += 8;continue
        if text.startswith(('sub rsp, 0x','add rsp, 0x')):
            delta = int(text.split('0x')[1],16);sp += delta if text.startswith('add') else -delta;continue
        if stack_move:
            offset = sp + int(stack_move[2],16)
            if offset in (8,24,32) and offset in slots:
                fail('conversion-owned-stack-overwrite','entry reader/wrap/companion saved exactly once',[at,raw_hex])
            slots[offset] = registers.get(stack_move[3]) if _qword(raw) else None;continue
        if stack_read:
            register, offset = stack_read[1],sp + int(stack_read[2],16)
            value = slots.get(offset);registers[_canonical(register)] = value if _qword(raw) else None
            if value == 'reader':reloads.append(at)
            continue
        if stack_lea:
            registers[stack_lea[1]] = ('stack',sp + int(stack_lea[2],16));continue
        move = _move(raw)
        if move:
            registers[move[0]] = registers.get(move[1]);continue
        load = _data_memory(raw,b'\x8b')
        if load:
            value = registers.get(load['base']);offset = load['offset'];result = None
            if _qword(raw):
                if (value,offset) == ('companion',0x20):result = 'adapterClass'
                elif (value,offset) == ('adapterClass',0xc0):result = 'adapterContext'
                elif value == 'adapterContext':result = context_slots.get(offset)
            registers[load['register']] = result;continue
        store = _data_memory(raw,b'\x89')
        if store:
            destination = registers.get(store['base']);value = registers.get(store['register'])
            if destination == 'originalOut':
                if not _qword(raw) or store['offset'] != 0 or value != (0 if null_wrapper else 'originalGetterValue'):
                    fail('conversion-original-output-value','one owned original ref store',[at,raw_hex,value])
                outputs.append(at)
            elif destination in ('reader','companion','incomingWrap','wrapperOutput'):
                fail('conversion-unowned-reference-write', 'owned output only', [at,raw_hex,destination])
            continue
        if re.fullmatch(r'xor ([a-z0-9]+), \1',text):
            registers[_canonical(text.split()[1][:-1])] = _integer_write(raw, immediate=False);continue
        is_call = raw[0] == 0xe8 or text.startswith('call ')
        if is_call:
            target = _target(at,raw) if raw[0] == 0xe8 and len(raw) == 5 else None
            if target == calls['formatterResult']:
                returned = 'selectedConcreteFormatter'
            elif target == calls['formatterDispatch']:
                if (registers.get('rcx') != 5 or registers.get('rdx') != 'selectedConcreteFormatter'
                        or registers.get('r8') != 'reader' or registers.get('r9') != ('stack',24)
                        or slots.get(24) != 'incomingWrap' or slots.get(8) != 'reader'):
                    fail('conversion-formatter-reader-wrap-arguments','slot five, selected receiver, same reader, preserved by-value wrap slot',registers)
                slots[24] = 'wrapperOutput';dispatched.append(at);returned = None
            elif target == calls['interfaceConversion']:
                if (registers.get('rcx') != 0 or registers.get('rdx') != 'originalConversionInterface'
                        or registers.get('r8') != 'wrapperOutput' or registers.get('r12') != 'originalOut'):
                    fail('conversion-interface-wrapper-arguments','slot zero, original typed interface and same wrapper',registers)
                converted.append(at);returned = 'originalGetterValue'
            else:
                for value in (registers.get(r)for r in('rcx','rdx','r8','r9')):
                    if isinstance(value,tuple) and value in(('stack',8),('stack',24),('stack',32)):
                        fail('conversion-owned-slot-escape','owned slots reach only their reviewed formatter call',[at,registers])
                    if value in ('reader','originalOut'):
                        fail('conversion-owned-reference-escape','owned byrefs reach only their reviewed call',[at,registers])
                returned = None
            for register in VOLATILE:registers.pop(register,None)
            registers['rax'] = returned;continue
        immediate = re.fullmatch(r'mov ([a-z0-9]+), 0x([0-9a-f]+)',text)
        if immediate:
            registers[_canonical(immediate[1])] = _integer_write(raw, immediate=True);continue
        test = re.fullmatch(r'test ([a-z0-9]+), \1',text)
        if test and registers.get(test[1]) == 'wrapperOutput':
            if not _qword(raw) or wrapper_guard is not None:
                fail('conversion-wrapper-null-guard', 'one full-width wrapper null test', [at,raw_hex])
            if not dispatched or n + 2 >= len(proof['program']):
                fail('conversion-wrapper-null-guard', 'wrapper test after dispatch with successor', at)
            branch_at, branch_hex = proof['program'][n+1];branch = bytes.fromhex(branch_hex)
            if branch[0] != 0x75 or proof['program'][n+2][0] != (branch_at + len(branch) if null_wrapper else _target(branch_at,branch)):
                fail('conversion-wrapper-null-edge', 'selected wrapper zero/nonzero branch', [branch_at,branch_hex])
            wrapper_guard = at
        written = (row.get('write')or{}).get('register')
        if written:registers.pop(_canonical(written),None)
    if sp != 0 or len(dispatched) != 1 or len(outputs) != 1 or len(converted) != (0 if null_wrapper else 1) or not reloads or wrapper_guard is None:
        fail('conversion-complete-owned-path','balanced frame, one dispatch/store and required conversion/reload',
             {'stack':sp,'dispatch':dispatched,'stores':outputs,'conversion':converted,'readerReloads':reloads})
    return {'readerReloads':reloads,'formatterDispatch':dispatched[0],
            'originalOutputStore':outputs[0],'nullWrapperOutput':null_wrapper,
            'byValueWrapEntrySlot':24,'originalValueInterfaceCall':converted[0] if converted else None}
