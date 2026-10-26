"""Prove the selected snapshot-cache read-to-return path, not its producer.

This recognizes one complete native instruction program. Addresses and field
offsets come from the selected build. Changed compiler programs fail closed.
Other paths, getter internals and live receiver/context validity stay separate.
"""
from __future__ import annotations

from scripts.game_data.damage_snapshot_abi import (require_ordinary_type, require_ordinary_signature, require_ordinary_pointer, require_ordinary_field, require_ordinary_value_type, require_ordinary_type_var)

import re
import struct
from typing import Any

from scripts.game_data.il2cpp.context import (
    method_spec_record, method_spec_usage_index, relative_branch_target,
    rip_qword_load_target,
)
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def _require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise ValueError(f'{check}: expected={expected!r} actual={actual!r}')


def _address(row: dict) -> int:
    return int(row['va'], 16)


def _check_encoding(row: dict) -> None:
    """Check the ISA encodings of this bounded compiler program, not hashes."""
    text = row['text']; raw = bytes.fromhex(row['bytes'])
    forms = {
        'mov [rsp+0x8], rbx': '48 89 5c 24 08',
        'mov [rsp+0x10], rbp': '48 89 6c 24 10',
        'mov [rsp+0x18], rsi': '48 89 74 24 18',
        'mov [rsp+0x20], rdi': '48 89 7c 24 20',
        'push r12': '41 54', 'push r14': '41 56', 'push r15': '41 57',
        'sub rsp, 0x70': '48 83 ec 70',
        'mov rdi, [rsp+0xb8]': '48 8b bc 24 b8 00 00 00',
        'mov r14, rdx': '4c 8b f2', 'mov rsi, rcx': '48 8b f1',
        'movaps [rsp+0x60], xmm6': '0f 29 74 24 60',
        'movaps [rsp+0x50], xmm7': '0f 29 7c 24 50',
        'xor edx, edx': '33 d2', 'mov rbx, r9': '49 8b d9',
        'mov rbp, r8': '49 8b e8', 'test al, al': '84 c0',
        'test rbx, rbx': '48 85 db', 'test rcx, rcx': '48 85 c9',
        'movaps xmm6, xmm0': '0f 28 f0', 'movq rax, xmm6': '66 48 0f 7e f0',
        'movaps xmm6, [rsp+0x60]': '0f 28 74 24 60',
        'lea r11, [rsp+0x70]': '4c 8d 5c 24 70',
        'mov rbx, [r11+0x20]': '49 8b 5b 20', 'mov rbp, [r11+0x28]': '49 8b 6b 28',
        'mov rsi, [r11+0x30]': '49 8b 73 30', 'mov rdi, [r11+0x38]': '49 8b 7b 38',
        'movaps xmm7, [rsp+0x50]': '0f 28 7c 24 50', 'mov rsp, r11': '49 8b e3',
        'pop r15': '41 5f', 'pop r14': '41 5e', 'pop r12': '41 5c', 'ret': 'c3',
    }
    expected = bytes.fromhex(forms[text]) if text in forms else None
    if match := re.fullmatch(r'mov ecx, (0x[0-9a-f]+)', text):
        expected = b'\xb9' + struct.pack('<I', int(match[1], 16))
    elif match := re.fullmatch(r'mov edx, \[rsp\+(0x[0-9a-f]+)\]', text):
        expected = b'\x8b\x94\x24' + struct.pack('<i', int(match[1], 16))
    elif match := re.fullmatch(r'(mov rcx, \[rsi|cmp \[rbx)\+(0x[0-9a-f]+)\](?:, al)?', text):
        displacement = int(match[2], 16)
        _require(0 <= displacement < 128, 'program-field-displacement', 'positive disp8', displacement)
        expected = (b'\x48\x8b\x4e' if match[1].startswith('mov') else b'\x38\x43') + bytes([displacement])
    elif match := re.fullmatch(r'call (0x[0-9a-f]+)', text):
        actual = relative_branch_target(raw, _address(row), source='damageSnapshotCache')
        _require(raw[0] == 0xe8 and actual == int(match[1], 16), 'program-call-target', match[1], hex(actual))
        return
    elif match := re.fullmatch(r'j(?:cc|e|ne|mp) (0x[0-9a-f]+)', text):
        edge = _edge(row)
        _require(edge is not None and edge[0] == int(match[1], 16), 'program-edge-text', match[1], edge)
        return
    elif match := re.fullmatch(r'mov r8, \[rip\+0x[0-9a-f]+ => (0x[0-9a-f]+)\]', text):
        target = rip_qword_load_target(raw, _address(row), source='damageSnapshotCache')
        _require(raw[:3] == b'\x4c\x8b\x05' and target == int(match[1], 16), 'program-rip-load', match[1], hex(target))
        return
    _require(expected is not None and raw == expected, 'program-encoding',
             None if expected is None else expected.hex(), raw.hex())


def check_return_program(rows: list[dict], *, pointer: int, cache_offset: int,
                         snapshot_offset: int, index_entry_offset: int,
                         patch_pointer: int, getter_pointer: int) -> dict:
    """Check entry aliases, guard edges, cache/index arguments and full return.

    Only the false patch guard, nonnull unit/cache and true snapshot flag path
    is followed. The normal call is assumed to return under Win64 preservation.
    Every selected instruction and edge is checked; unselected code is not.
    """
    positions = {_address(row): n for n, row in enumerate(rows)}
    _require(len(positions) == len(rows), 'program-addresses', 'unique', len(positions))

    def sequence(start: int, expected: list[str]) -> list[dict]:
        _require(start in positions, 'program-start', 'instruction boundary', hex(start))
        selected = rows[positions[start]:positions[start] + len(expected)]
        _require(len(selected) == len(expected), 'program-length', len(expected), len(selected))
        next_address = start
        for row, pattern in zip(selected, expected):
            _require(_address(row) == next_address, 'program-contiguity', hex(next_address), row['va'])
            _require(re.fullmatch(pattern, row['text']) is not None,
                     'program-instruction', pattern, row['text'])
            _check_encoding(row)
            raw = bytes.fromhex(row['bytes'])
            _require(0 < len(raw) <= 15, 'program-instruction-size', '1..15', len(raw))
            next_address += len(raw)
        return selected

    def branch(row: dict, opcode: bytes) -> int:
        raw = bytes.fromhex(row['bytes'])
        _require(raw.startswith(opcode), 'program-edge-condition', opcode.hex(), raw.hex())
        edge = _edge(row)
        _require(edge is not None, 'program-edge', 'complete relative branch', raw.hex())
        return edge[0]

    prefix = sequence(pointer, [
        r'mov \[rsp\+0x8\], rbx', r'mov \[rsp\+0x10\], rbp',
        r'mov \[rsp\+0x18\], rsi', r'mov \[rsp\+0x20\], rdi',
        'push r12', 'push r14', 'push r15', r'sub rsp, 0x70',
        r'mov rdi, \[rsp\+0xb8\]', 'mov r14, rdx', 'mov rsi, rcx',
        r'movaps \[rsp\+0x60\], xmm6', 'xor edx, edx',
        r'movaps \[rsp\+0x50\], xmm7', r'mov ecx, 0x[0-9a-f]+',
        'mov rbx, r9', 'mov rbp, r8', f'call {patch_pointer:#x}',
        'test al, al', r'j(?:cc|ne) 0x[0-9a-f]+',
        'test rbx, rbx', r'j(?:cc|e) 0x[0-9a-f]+',
        rf'cmp \[rbx\+{snapshot_offset:#x}\], al', r'j(?:cc|ne) 0x[0-9a-f]+',
    ])
    patch_edge = branch(prefix[19], b'\x0f\x85')
    unit_null = branch(prefix[21], b'\x0f\x84')
    snapshot_start = branch(prefix[23], b'\x0f\x85')
    # Three eight-byte pushes plus the checked 0x70 frame allocation.
    index_stack_offset = index_entry_offset + 3 * 8 + 0x70
    snapshot = sequence(snapshot_start, [
        rf'mov rcx, \[rsi\+{cache_offset:#x}\]', 'test rcx, rcx',
        r'j(?:cc|e) 0x[0-9a-f]+',
        r'mov r8, \[rip\+0x[0-9a-f]+ => 0x[0-9a-f]+\]',
        rf'mov edx, \[rsp\+{index_stack_offset:#x}\]',
        f'call {getter_pointer:#x}', 'movaps xmm6, xmm0', r'jmp 0x[0-9a-f]+',
    ])
    cache_null = branch(snapshot[2], b'\x0f\x84')
    return_start = branch(snapshot[7], b'\xeb')
    epilogue = sequence(return_start, [
        'movq rax, xmm6', r'movaps xmm6, \[rsp\+0x60\]',
        r'lea r11, \[rsp\+0x70\]', r'mov rbx, \[r11\+0x20\]',
        r'mov rbp, \[r11\+0x28\]', r'mov rsi, \[r11\+0x30\]',
        r'mov rdi, \[r11\+0x38\]', r'movaps xmm7, \[rsp\+0x50\]',
        'mov rsp, r11', 'pop r15', 'pop r14', 'pop r12', 'ret',
    ])
    selected_addresses = {_address(row) for row in prefix + snapshot + epilogue}
    for edge in (patch_edge, unit_null, cache_null):
        _require(edge not in selected_addresses, 'excluded-edge', 'outside selected trace', hex(edge))
    _require(snapshot_start not in {_address(row) for row in prefix + epilogue},
             'snapshot-entry', 'separate selected block', hex(snapshot_start))
    return {'selectedInstructionCount': len(selected_addresses),
            'snapshotEntry': hex(snapshot_start), 'returnEntry': hex(return_start),
            'getterCall': snapshot[5]['va'], 'usageLoad': snapshot[3],
            'indexEntryStackOffset': index_entry_offset,
            'indexFrameStackOffset': index_stack_offset,
            'excludedTargets': [hex(edge) for edge in (patch_edge, unit_null, cache_null)]}


def check_cache_return(index, spec: dict) -> dict:
    """Bind the selected instruction path to named types and a closed getter."""
    body = index.body(spec['type'], spec['method'])
    selected = NativeReferenceContext(index.image, index=index)
    owner, cache_type, cache_offset = selected.field(spec['cacheField'])
    _require(owner == spec['type'] and cache_type == 'System.Collections.Generic.List`1<double>',
             'cache-field-type', [spec['type'], 'System.Collections.Generic.List`1<double>'], [owner, cache_type])
    snapshot_owner, snapshot_type, snapshot_offset = selected.field(spec['snapshotField'])
    _require(snapshot_type == 'bool', 'snapshot-field-type', 'bool', snapshot_type)
    require_ordinary_field(selected,spec['cacheField'],cache_type,'consumer.cacheField')
    require_ordinary_field(selected,spec['snapshotField'],'bool','consumer.snapshotField')
    _require(index.parameter_location(body.pointer, body.symbol, 'this') == ('register', 'rcx'),
             'incoming-this', ['register', 'rcx'], index.parameter_location(body.pointer, body.symbol, 'this'))
    _require(index.parameter_location(body.pointer, body.symbol, 'damageUnit') == ('register', 'r9'),
             'incoming-unit', ['register', 'r9'], index.parameter_location(body.pointer, body.symbol, 'damageUnit'))
    kind, index_offset = index.parameter_location(body.pointer, body.symbol, 'index')
    _require(kind == 'stack' and isinstance(index_offset, int), 'incoming-index', 'stack Int32', [kind, index_offset])
    native_methods = [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer[body.pointer]
                      if f"{r['type']}.{r['method']}" == body.symbol]
    for method in native_methods:
        parameters = index.metadata.parameters_for(method)
        names = {index.metadata.string(p.name_index): selected.type_name(p.type_index) for p in parameters}
        for p in parameters:
            name=index.metadata.string(p.name_index)
            if name in ('index','damageUnit'):
                require_ordinary_type(selected,p.type_index,'int' if name=='index' else snapshot_owner,'consumer.'+name)
        require_ordinary_value_type(selected,method.return_type,spec['returnType'],'consumer.return')
        _require(names.get('index') == 'int', 'incoming-index-type', 'int', names.get('index'))
        _require(names.get('damageUnit') == snapshot_owner, 'incoming-unit-type', snapshot_owner, names.get('damageUnit'))
        _require(selected.type_name(method.return_type) == spec['returnType'],
                 'return-type', spec['returnType'], selected.type_name(method.return_type))
    result_td = index.types[spec['returnType']]
    instance_fields = [f for f in index.metadata.fields_for(result_td) if not selected.field_attributes(f.type_index) & 0x10]
    _require(selected.is_value_type(spec['returnType']) and len(instance_fields) == 1,
             'return-value-layout', 'value type with one instance field', len(instance_fields))
    _require(selected.field(spec['valueField']) == (spec['returnType'], 'double', 16),
             'return-value-field', [spec['returnType'], 'double', 16], selected.field(spec['valueField']))
    registration = index.image.registration
    size_cell = int(registration['typeDefinitionsSizes'], 16) + result_td.index * 8
    size_pointer = index.pe.u64_at_va(size_cell)
    size = index.pe.bytes_at_va(size_pointer, 16)
    _require(int.from_bytes(size[:4], 'little') == 24, 'return-boxed-size', 24, int.from_bytes(size[:4], 'little'))
    getter = index.body('System.Collections.Generic.List`1', 'get_Item', class_arguments=['System.Double'])
    aliases = index.names_by_pointer[getter.pointer]
    _require(all(row.get('type') == 'System.Collections.Generic.List`1' and row.get('method') == 'get_Item'
                 and [a['typeName'] for a in row.get('classInstantiation', {}).get('arguments', [])] == ['System.Double']
                 for row in aliases), 'getter-closed-identity', 'only List<Double>.get_Item', aliases)
    first_call = next((row for row in body.rows if row['text'].startswith('call ')), None)
    _require(first_call is not None, 'patch-call', 'direct entry call', first_call)
    patch_pointer = int(first_call['text'].split()[1], 16)
    patch_methods = [index.metadata.methods[row['methodIndex']]
                     for row in index.names_by_pointer.get(patch_pointer, ())
                     if row.get('type') == 'IFix.WrappersManagerImpl' and row.get('method') == 'IsPatched']
    _require(bool(patch_methods), 'patch-call-identity', 'IsPatched', hex(patch_pointer))
    for method in patch_methods:
        parameter_types = [selected.type_name(p.type_index) for p in index.metadata.parameters_for(method)]
        _require(bool(method.flags & 0x10) and parameter_types == ['int']
                 and selected.type_name(method.return_type) == 'bool',
                 'patch-call-signature', 'static bool IsPatched(int)', parameter_types)
        require_ordinary_signature(selected,method,['int'],'bool','consumer.IFix')
    proof = check_return_program(body.rows, pointer=body.pointer, cache_offset=cache_offset,
                                 snapshot_offset=snapshot_offset, index_entry_offset=index_offset,
                                 patch_pointer=patch_pointer, getter_pointer=getter.pointer)
    usage = proof.pop('usageLoad')
    usage_raw = bytes.fromhex(usage['bytes'])
    _require(usage_raw[:3] == b'\x4c\x8b\x05', 'method-info-load', 'R8 RIP qword', usage_raw.hex())
    cell = rip_qword_load_target(usage_raw, _address(usage), source='damageSnapshotCache')
    spec_index = method_spec_usage_index(index.pe.bytes_at_va(cell, 8), registration['methodSpecsCount'],
                                       source='damageSnapshotCache', offset=cell)
    spec_va = int(registration['methodSpecs'], 16) + spec_index * 12
    definition, class_inst, method_inst = method_spec_record(index.pe.bytes_at_va(spec_va, 12),
        len(index.metadata.methods), registration['genericInstsCount'], source='damageSnapshotCache', offset=spec_va)
    _require(any(row.get('methodSpecIndex') == spec_index and row.get('methodIndex') == definition
                 for row in aliases), 'getter-method-spec', 'closed getter registration', [spec_index, definition])
    getter_method=index.metadata.methods[definition]
    require_ordinary_type_var(selected,getter_method.return_type,getter_method.declaring_type,0,'getter.return')
    require_ordinary_type(selected,index.metadata.parameters_for(getter_method)[0].type_index,'int','getter.index')
    for a in index.image.instantiations.resolve(class_inst).arguments:
        require_ordinary_pointer(selected,a.type_pointer_va,runtime_type_name(index.pe,index.metadata,a.type_pointer_va),'double','getter.classArg0')
    arguments = [runtime_type_name(index.pe, index.metadata, a.type_pointer_va)
                 for a in index.image.instantiations.resolve(class_inst).arguments]
    _require(arguments == ['double'] and method_inst == -1, 'getter-context', [['double'], -1], [arguments, method_inst])
    return {**proof, 'symbol': body.symbol, 'claim': 'snapshotCacheIndexToReturn',
            'cacheField': spec['cacheField'], 'cacheType': cache_type,
            'getterMethodSpecIndex': spec_index, 'getterUsageCell': hex(cell),
            'boundary': 'Selected false-IFix, nonnull unit/cache, true snapshot path: incoming this cache and incoming Int32 index reach the closed Double getter, and its normally returned XMM0 bits reach RAX as the sole CalcResult Double value. Getter internals, valid live object/context, cache producer and live path selection remain conditional.'}
