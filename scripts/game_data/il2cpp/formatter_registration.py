"""Authenticate static formatter objects, keys and concrete forwarding paths.

Callers own build gates and stored grammars. These bounded Win64 programs
describe arguments at static calls under ordinary ABI preservation. They do
not establish that initialization ran or that a stateful provider returned
the registered object. A shared generic entry retains its concrete context.
"""
from __future__ import annotations

import re
import struct
from typing import Any

from .formatter_composition import validate_typed_usage_context
from .reference_layouts import NativeReferenceContext


def _rows(image: Any, window: dict, count: int, label: str) -> list[dict]:
    if (type(window['startRva']) is not int or type(window['endRva']) is not int
            or not 0 < window['endRva'] - window['startRva'] <= 2048):
        raise ValueError(f'{label}.contract:program-window')
    image.check_windows([window], label=label)
    start = image.pe.image_base + window['startRva']
    raw = image.pe.bytes_at_va(start, window['endRva'] - window['startRva'])
    rows = image.mapper.decode_x64_subset(raw, start, stop_offset=len(raw))
    if (len(rows) != count or not rows or int(rows[0]['va'], 16) != start
            or int(rows[-1]['va'], 16) + len(bytes.fromhex(rows[-1]['bytes'])) != start + len(raw)
            or any('db ' in row['text'] for row in rows)):
        raise ValueError(f'{label}.native:complete-program={count}')
    return rows


def _at(image: Any, row: dict) -> int:
    return int(row['va'], 16) - image.pe.image_base


def _target(image: Any, row: dict, opcode: int, label: str) -> int:
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 5 or raw[0] != opcode:
        raise ValueError(f'{label}.native:relative-call-or-jump')
    return _at(image, row) + 5 + struct.unpack_from('<i', raw, 1)[0]


def _stack_slot(row: dict, label: str) -> tuple[str, int]:
    match = re.fullmatch(r'mov (\[rsp\+0x([0-9a-f]+)\]), rax', row['text'])
    if not match:
        raise ValueError(f'{label}.native:object-stack-slot')
    offset = int(match[2], 16)
    if offset < 0x20 or offset % 8:
        raise ValueError(f'{label}.native:object-stack-slot-alignment')
    return match[1], offset


def validate_eager_wrap_registration(image: Any, flow: dict, *, label: str) -> None:
    """Prove a concrete adapter and original key reach RegisterWrap together."""
    rows = _rows(image, flow['window'], 18, label)
    allocation, constructor, key = (flow[k] for k in ('allocation', 'constructor', 'key'))
    for usage in (allocation, constructor, key):
        validate_typed_usage_context(image, usage, label=label)
    if (allocation['tag'] != 1 or constructor['tag'] != 6 or key['tag'] != 2
            or constructor['typeName'] != 'Beyond.MemoryPack.GenericMemoryPackFormatter`2'
            or constructor['methodName'] != '.ctor'
            or constructor['classArguments'] != [flow['originalType'], flow['wrapperType']]
            or constructor['methodArguments'] != []
            or key['typeName'] != flow['originalType']):
        raise ValueError(f'{label}.native:eager-concrete-context')
    for at, usage, prefix in ((0, allocation, '488B0D'), (5, constructor, '488B15'), (8, key, '488B05')):
        if (_at(image, rows[at]) != usage['instructionRva']
                or not bytes.fromhex(rows[at]['bytes']).hex().upper().startswith(prefix)):
            raise ValueError(f'{label}.native:eager-usage-register={at}')
    selected = NativeReferenceContext(image)
    pointer = selected.type_pointer(allocation['typeIndex'])
    raw = image.pe.bytes_at_va(pointer, 16)
    if raw[10] != 0x15:
        raise ValueError(f'{label}.native:eager-adapter-kind')
    _, argument_pointer = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
    instance = image.instantiations.resolve_pointer(argument_pointer)
    if (instance.index != constructor['methodSpec'][1] or len(instance.arguments) != 2
            or selected.type_pointer(key['typeIndex']) != instance.arguments[0].type_pointer_va
            or allocation['typeName'] != 'Beyond.MemoryPack.GenericMemoryPackFormatter`2<' + ','.join(constructor['classArguments']) + '>'):
        raise ValueError(f'{label}.native:eager-original-key-pointer')
    obj, obj_at = _stack_slot(rows[2], label)
    original, original_at = _stack_slot(rows[9], label)
    resolved, resolved_at = _stack_slot(rows[13], label)
    if len({obj_at, original_at, resolved_at}) != 3:
        raise ValueError(f'{label}.native:eager-overlapping-slots')
    for at, expected in {3:f'mov rcx, {obj}', 6:f'mov rcx, {obj}', 10:'xor edx, edx',
                         11:f'mov rcx, {original}', 14:'xor r8d, r8d',
                         15:f'mov rdx, {resolved}', 16:f'mov rcx, {obj}'}.items():
        if rows[at]['text'] != expected:
            raise ValueError(f'{label}.native:eager-object-key-flow={at}')
    for at, name in ((1,'allocation'), (4,'objectCheck'), (7,'constructor'), (12,'typeFromHandle'), (17,'registerWrap')):
        if _target(image, rows[at], 0xe8, label) != flow['actualCalls'][name]:
            raise ValueError(f'{label}.native:eager-call={name}')
    helpers = flow['helperMethods']
    for name, owner, method_name, parameters, returned in (
            ('typeFromHandle', 'System.Type', 'GetTypeFromHandle', ['System.RuntimeTypeHandle'], 'System.Type'),
            ('registerWrap', 'MemoryPack.MemoryPackFormatterProvider', 'RegisterWrap',
             ['MemoryPack.IMemoryPackFormatter', 'System.Type'], 'void')):
        row = helpers[name]; image.validate_method_row(row, label=label)
        method = image.metadata.methods[row[0]]
        if (row[1:3] != [owner, method_name] or row[3] != flow['actualCalls'][name]
                or not method.flags & 0x10 or selected.type_name(method.return_type) != returned
                or [selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)] != parameters):
            raise ValueError(f'{label}.native:eager-helper-identity={name}')
    thunk = flow['constructorThunk']; thunk_rows = _rows(image, thunk['window'], 2, label)
    usage = thunk['context']; validate_typed_usage_context(image, usage, label=label)
    if (thunk['window']['startRva'] != flow['actualCalls']['constructor']
            or _at(image, thunk_rows[0]) != usage['instructionRva']
            or bytes.fromhex(thunk_rows[0]['bytes'])[:3] != b'\x48\x8b\x15'
            or usage['tag'] != 6 or usage['methodSpecIndex'] != constructor['methodSpecIndex']
            or usage['methodSpec'] != constructor['methodSpec']
            or usage['classArguments'] != constructor['classArguments']
            or _target(image, thunk_rows[1], 0xe9, label) != thunk['sharedTargetRva']):
        raise ValueError(f'{label}.native:eager-constructor-thunk-context')


def validate_wrapper_formatter_registration(image: Any, flow: dict, *, label: str) -> None:
    """Check the allocated concrete wrapper formatter reaches Register<Wrapper>."""
    rows = _rows(image, flow['window'], 15, label)
    allocation, provider, registration = (flow[k] for k in ('allocation', 'provider', 'registration'))
    for usage in (allocation, provider, registration):
        validate_typed_usage_context(image, usage, label=label)
    if (allocation['tag'] != 1 or allocation['typeName'] != flow['formatterType']
            or provider['tag'] != 1 or provider['typeName'] != 'MemoryPack.MemoryPackFormatterProvider'
            or registration['tag'] != 6 or registration['typeName'] != provider['typeName']
            or registration['methodName'] != 'Register' or registration['classArguments'] != []
            or registration['methodArguments'] != [flow['wrapperType']]):
        raise ValueError(f'{label}.native:wrapper-registration-identity')
    selected = NativeReferenceContext(image)
    formatter = image.metadata.types[flow['formatterDefinition']]
    wrapper = image.metadata.types[flow['wrapperDefinition']]
    registered = image.instantiations.resolve(registration['methodSpec'][2]).arguments
    if (selected.type_pointer(allocation['typeIndex']) != selected.type_pointer(formatter.byval_type_index)
            or len(registered) != 1
            or registered[0].type_pointer_va != selected.type_pointer(wrapper.byval_type_index)):
        raise ValueError(f'{label}.native:wrapper-registration-type-pointer')
    for at, usage, prefix in ((0,allocation,'488B0D'), (8,provider,'488B0D'), (12,registration,'488B15')):
        if _at(image, rows[at]) != usage['instructionRva'] or not bytes.fromhex(rows[at]['bytes']).hex().upper().startswith(prefix):
            raise ValueError(f'{label}.native:wrapper-registration-usage={at}')
    for at, expected in {2:'mov rbx, rax',3:'test rax, rax',5:'xor edx, edx',6:'mov rcx, rax',
                         9:'cmp [rcx+0xe0], 0x0',13:'mov rcx, rbx'}.items():
        if rows[at]['text'] != expected:
            raise ValueError(f'{label}.native:wrapper-registration-object-flow={at}')
    branch = bytes.fromhex(rows[10]['bytes'])
    null_guard = bytes.fromhex(rows[4]['bytes'])
    is_je = (len(null_guard) == 2 and null_guard[0] == 0x74
             or len(null_guard) == 6 and null_guard[:2] == b'\x0f\x84')
    if (not is_je or len(branch) != 2 or branch[0] != 0x75
            or _at(image, rows[10]) + 2 + int.from_bytes(branch[1:], 'little', signed=True) != _at(image, rows[12])):
        raise ValueError(f'{label}.native:wrapper-registration-class-init-path')
    for at, key in ((1,'allocation'),(7,'constructor'),(11,'classInit'),(14,'registration')):
        if _target(image, rows[at], 0xe8, label) != flow['actualCalls'][key]:
            raise ValueError(f'{label}.native:wrapper-registration-call={key}')
    image.validate_method_row(flow['constructorMethod'], label=label)
    if (flow['constructorMethod'][1:3] != [flow['formatterType'], '.ctor']
            or flow['constructorMethod'][3] != flow['actualCalls']['constructor']
            or image.metadata.methods[flow['constructorMethod'][0]].declaring_type != formatter.index):
        raise ValueError(f'{label}.native:wrapper-registration-constructor')


def validate_reference_wrapper_forwarding(image: Any, record: dict, *, label: str) -> None:
    """Authenticate a typed reference getter and the warmed formatter tail path."""
    selected = NativeReferenceContext(image)
    for name in ('getterMethod','formatterMethod','sourceMethod'):
        image.validate_method_row(record[name], label=label)
    original, wrapper = record['originalType'], record['wrapperType']
    if (selected.is_value_type(original) or selected.is_value_type(wrapper)
            or selected.field(wrapper + '::__instance') != (wrapper, original, 16)):
        raise ValueError(f'{label}.native:reference-wrapper-instance')
    getter = image.metadata.methods[record['getterMethod'][0]]
    if getter.flags & 0x10 or getter.parameter_count or selected.type_name(getter.return_type) != original:
        raise ValueError(f'{label}.native:reference-wrapper-getter-declaration')
    getter_rows = _rows(image, record['getterWindow'], 2, label)
    if ([bytes.fromhex(row['bytes']) for row in getter_rows] != [b'\x48\x8b\x41\x10', b'\xc3']
            or record['getterWindow']['startRva'] != record['getterMethod'][3]):
        raise ValueError(f'{label}.native:reference-wrapper-getter-program')
    for method_key, is_static in (('formatterMethod',False),('sourceMethod',True)):
        method = image.metadata.methods[record[method_key][0]]
        parameters = image.metadata.parameters_for(method)
        if (bool(method.flags & 0x10) != is_static or selected.type_name(method.return_type) != 'void'
                or len(parameters) != 2
                or [selected.type_name(p.type_index) for p in parameters] != ['MemoryPack.MemoryPackReader', wrapper]
                or any(not image.pe.bytes_at_va(selected.type_pointer(p.type_index),16)[11] & 0x20 for p in parameters)):
            raise ValueError(f'{label}.native:reference-wrapper-reader-declaration={method_key}')
    rows = _rows(image, record['forwardWindow'], 17, label)
    if record['forwardWindow']['startRva'] != record['formatterMethod'][3]:
        raise ValueError(f'{label}.native:reference-wrapper-forward-entry')
    for at, expected in {0:'mov [rsp+0x8], rbx',1:'push rdi',2:'sub rsp, 0x20',
                         4:'mov rbx, r8',5:'mov rdi, rdx',8:'cmp [rcx+0xe0], 0x0',
                         10:'xor r8d, r8d',11:'mov rdx, rbx',12:'mov rcx, rdi',
                         13:'mov rbx, [rsp+0x30]',14:'add rsp, 0x20',15:'pop rdi'}.items():
        if rows[at]['text'] != expected:
            raise ValueError(f'{label}.native:reference-wrapper-reader-output-flow={at}')
    if (not rows[3]['text'].startswith('cmp [rip+') or not rows[3]['text'].endswith(', 0x0')
            or not rows[7]['text'].startswith('mov rcx, [rip+')
            or any(not rows[n]['text'].startswith('je ') for n in (6,9))
            or _target(image, rows[16], 0xe9, label) != record['sourceMethod'][3]):
        raise ValueError(f'{label}.native:reference-wrapper-conditional-forward')
