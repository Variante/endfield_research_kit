"""Authenticate the IFix Integer delegate path's named interface dispatcher.

The caller supplies one explicitly selected, native-input-gated NativeImage.
The receiver dispatcher loads an anonymous word from the receiver's class,
subtracts its reviewed selection base, and uses an unsigned range check and
jump table. Every admitted table target must be a complete direct-call case
that clears the hidden MethodInfo argument, preserves receiver/Type/id/anon,
and joins the same return epilogue. Table and case extents are exact; omitted,
duplicated, reordered or intervening unreviewed routes are refused.

Each direct target is identified by metadata image, type definition, signature,
token and registered method pointer. The implementation's unique named static
interface-offset record and effective vtable slot must select that same method.
Image identity matters because generated wrapper types reuse their full name
across assemblies. A name match alone cannot choose an implementation.

The out-of-range path shuffles the same arguments into the fallback. Its
authenticated type cell names the WrappersManager interface and its abstract
CreateDelegate(Type, int, object) declaration at slot zero. The fallback's local
interface-comparison loop either uses the matched signed interface offset or
requests the same zero slot from a child. Both branches join the pair-loading
tail, which restores receiver/Type/id/anon and forwards the pair's second qword
as the hidden argument before the indirect tail call.

Static interface declarations and local native argument forwarding do not
authenticate a live class selector, interface array, child returned pair or
wrapper manager choice. Delegate construction and invocation remain unobserved.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_name


class WrapperDispatchRuleError(ValueError):
    """The reviewed wrapper-dispatch witness differs from the selected image."""


def _number(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else value


def _require(ok: bool, label: str) -> None:
    if not ok:
        raise WrapperDispatchRuleError('wrapperDispatch.' + label)


def _raw(image: Any, row: dict[str, Any], extents: dict[int, int]) -> bytes:
    rva, size = _number(row['rva']), row['byteCount']
    _require(type(rva) is int and rva >= 0 and type(size) is int and 0 < size <= 65536,
             row['name'] + ': invalid native range')
    pointer = image.pe.image_base + rva
    _require(extents.get(pointer) == pointer + size, row['name'] + ': native extent differs')
    raw = image.pe.bytes_at_va(pointer, size)
    actual = hashlib.sha256(raw).hexdigest().upper()
    _require(len(raw) == size and raw == bytes.fromhex(row['hex']) and actual == row['sha256'].upper(),
             row['name'] + f": native bytes differ expectedSha256={row['sha256']} actualSha256={actual}")
    return raw


def _slice(raw: bytes, base: int, start: int, size: int) -> bytes:
    offset = start - base
    _require(type(size) is int and size >= 0 and 0 <= offset <= len(raw) - size,
             'instruction range outside authenticated body')
    return raw[offset:offset + size]


def _rel(opcode: bytes, site: int, target: int) -> bytes:
    delta = target - site - len(opcode) - 4
    _require(-(1 << 31) <= delta < (1 << 31), 'relative target outside signed 32-bit range')
    return opcode + struct.pack('<i', delta)


def _type_name(image: Any, index: int) -> str:
    _require(type(index) is int and 0 <= index < image.registration['typesCount'], 'registered type index outside table')
    pointer = image.pe.u64_at_va(_number(image.registration['types']) + index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def _method(image: Any, row: dict[str, Any], *, interface: bool = False) -> Any:
    metadata = image.metadata
    _require(row.get('method') == 'CreateDelegate'
             and row.get('parameterTypes') == ['System.Type', 'int', 'object']
             and row.get('returnType') == 'System.Delegate', 'unsupported CreateDelegate signature claim')
    index = row['definitionIndex']
    _require(type(index) is int and 0 <= index < len(metadata.types), 'type definition outside metadata')
    owner = metadata.types[index]
    image_name = metadata.string(metadata.images[image.owners[index]].name_index)
    _require(image_name == row['image'] and metadata.type_full_name(owner) == row['type'],
             'image-qualified type identity differs')
    methods = [method for method in metadata.methods_for(owner)
               if metadata.string(method.name_index) == 'CreateDelegate'
               and method.parameter_count == 3
               and [_type_name(image, p.type_index) for p in metadata.parameters_for(method)] == ['System.Type', 'int', 'object']]
    _require(len(methods) == 1, 'expected one image-qualified CreateDelegate signature')
    method = methods[0]
    _require(method.index == row['methodIndex'] and method.token == _number(row['token'])
             and method.slot == row['slot'] and _type_name(image, method.return_type) == 'System.Delegate',
             'CreateDelegate method identity or slot differs')
    _require([metadata.string(p.name_index) for p in metadata.parameters_for(method)] == ['type', 'id', 'anon'],
             'CreateDelegate argument order differs')
    pointer = image.method_pointer_va(method)
    if interface:
        _require(owner.flags & 0x20 != 0 and method.flags & 0x400 != 0 and pointer == 0,
                 'named declaration is not an abstract interface method')
    else:
        _require(not owner.flags & 0x20 and not method.flags & 0x400
                 and pointer == image.pe.image_base + _number(row['rva']),
                 'registered implementation pointer differs')
    return method


def _interface_slot(image: Any, row: dict[str, Any], interface: dict[str, Any]) -> None:
    metadata = image.metadata
    owner = metadata.types[row['definitionIndex']]
    section = metadata.sections['interfaceOffsets']
    start, size = section.offset + owner.interface_offsets_start * 8, owner.interface_offsets_count * 8
    _require(owner.interface_offsets_count > 0 and section.offset <= start <= section.offset + section.size - size,
             'static interface-offset records outside metadata')
    pairs = list(struct.iter_unpack('<ii', metadata.buf[start:start + size]))
    selected = [offset for type_index, offset in pairs if type_index == interface['registeredTypeIndex']]
    _require(selected == [row['interfaceOffset']], 'unique named static interface offset differs')
    effective = row['interfaceOffset'] + interface['method']['slot']
    _require(effective == row['slot'] and 0 <= effective < owner.vtable_count,
             'effective static vtable slot differs')
    section = metadata.sections['vtableMethods']
    start = section.offset + (owner.vtable_start + effective) * 4
    _require(section.offset <= start <= section.offset + section.size - 4, 'static vtable entry outside metadata')
    word = struct.unpack_from('<I', metadata.buf, start)[0]
    _require(word == (0x60000000 | (row['methodIndex'] << 1) | 1), 'static vtable CreateDelegate identity differs')


def validate_wrapper_dispatch_rules(image: Any, spec: dict[str, Any], extents: dict[int, int],
                                    parent_dispatcher: dict[str, Any]) -> dict[str, Any]:
    """Check every table route and the slot-zero fallback, preserving live gaps."""
    _require(spec.get('schema') == 'endfield.ifix-vm-wrapper-dispatch-rules.v1'
             and spec.get('evidenceBoundary') == 'conditional'
             and spec.get('executionBoundary') == 'unobserved'
             and spec.get('runtimeSelection') == 'unobserved'
             and spec.get('selectorMeaning') == 'anonymous-runtime-class-word'
             and spec.get('argumentOrder') == ['receiver', 'System.Type', 'int', 'object'],
             'unsupported schema, boundary or argument claim')
    dispatcher, fallback = spec['dispatcher'], spec['fallback']
    _require(dispatcher['name'] == 'receiverDispatcher' and fallback['name'] == 'slotZeroFallback', 'native body labels differ')
    _require(all(dispatcher[k] == parent_dispatcher[k] for k in ('rva', 'byteCount', 'sha256')),
             'parent receiver-dispatcher reference differs')
    d = _raw(image, dispatcher, extents)
    f = _raw(image, fallback, extents)
    db, fb = _number(dispatcher['rva']), _number(fallback['rva'])
    interface = spec['interface']
    _require(interface['method']['type'] == 'IFix.Core.WrappersManager'
             and interface['method']['slot'] == 0, 'unsupported named interface or slot')
    _method(image, interface['method'], interface=True)
    cell = interface['typeCell']
    cell_rva = _number(cell['rva'])
    usage = image.pe.bytes_at_va(image.pe.image_base + cell_rva, 8)
    _require(usage == bytes.fromhex(cell['rawHex']), 'interface type-cell bytes differ')
    index = unresolved_usage_index(usage, image.registration['typesCount'], tag=1,
                                   source='IFix wrapper interface', offset=cell_rva)
    _require(index == interface['registeredTypeIndex'] and _type_name(image, index) == 'IFix.Core.WrappersManager',
             'interface type-cell resolves to a different type')
    type_pointer = image.pe.u64_at_va(_number(image.registration['types']) + index * 8)
    _require(image.pe.u64_at_va(type_pointer) == interface['method']['definitionIndex'],
             'interface type-cell definition differs')

    selection = spec['selection']
    count, first = selection['entryCount'], selection['firstSelectorWord']
    _require(type(count) is int and 1 <= count <= 128 and type(first) is int and 0 <= first < (1 << 31),
             'bounded dispatcher selection differs')
    table, out, join = map(_number, (selection['tableRva'], selection['fallbackRva'], selection['joinRva']))
    offset = selection['classWordOffset']
    _require(type(offset) is int and 0 <= offset < (1 << 31), 'invalid anonymous class-word offset')
    prefix = (b'\x48\x83\xec\x38\x48\x8b\x01\x44\x8b\x90' + struct.pack('<I', offset)
              + b'\x41\x81\xc2' + struct.pack('<i', -first)
              + b'\x41\x83\xfa' + bytes([count - 1])
              + _rel(b'\x0f\x87', db + 25, out)
              + b'\x49\x63\xc2' + _rel(b'\x4c\x8d\x1d', db + 34, 0)
              + b'\x45\x8b\x94\x83' + struct.pack('<I', table)
              + b'\x4d\x03\xd3\x41\xff\xe2')
    _require(_slice(d, db, db, len(prefix)) == prefix, 'dispatcher receiver/range/table program differs')
    cases = spec['cases']
    _require(len(cases) == count and len({r['methodIndex'] for r in cases}) == count,
             'missing or duplicated implementation cases')
    cursor = db + len(prefix)
    table_bytes = _slice(d, db, table, count * 4)
    for ordinal, row in enumerate(cases):
        target = struct.unpack_from('<I', table_bytes, ordinal * 4)[0]
        _require(row['selectorWord'] == first + ordinal and _number(row['caseRva']) == target == cursor,
                 'case order or jump-table target differs')
        _method(image, row)
        _interface_slot(image, row, interface)
        expected = b'\x48\x83\x64\x24\x20\x00' + _rel(b'\xe8', cursor + 6, _number(row['rva']))
        _require(_slice(d, db, cursor, len(expected)) == expected, 'case arguments, hidden zero or call differs')
        cursor += len(expected)
        opcode = _slice(d, db, cursor, 1)
        if opcode == b'\xeb':
            delta = join - cursor - 2
            _require(-128 <= delta <= 127 and _slice(d, db, cursor, 2) == b'\xeb' + struct.pack('<b', delta),
                     'case short return join differs')
            cursor += 2
        else:
            _require(_slice(d, db, cursor, 5) == _rel(b'\xe9', cursor, join), 'case near return join differs')
            cursor += 5
    _require(cursor == out, 'unreviewed code between cases and fallback')
    shuffle = b'\x4c\x89\x4c\x24\x28\x4c\x8b\xca\x44\x89\x44\x24\x20\x4c\x8b\xc1' + _rel(b'\xe8', out + 16, fb)
    _require(out + len(shuffle) == join and _slice(d, db, out, len(shuffle)) == shuffle,
             'fallback Type/id/anon/receiver argument shuffle differs')
    _require(table == join + 7 and _slice(d, db, join, 7) == b'\x48\x83\xc4\x38\xc3\x66\x90'
             and table + count * 4 == db + len(d), 'dispatcher return or table extent differs')

    # Complete selected fallback grammar. Its local hit and miss paths join at
    # the same pair load; unknown runtime arrays or child outcomes stay open.
    helpers = fallback['helpers']
    expected_f = (bytes.fromhex('48895c240848896c24104889742418574883ec30498b18498be9')
                  + _rel(b'\x48\x8b\x35', fb + 26, cell_rva)
                  + bytes.fromhex('488bcb498bf8') + _rel(b'\xe8', fb + 39, _number(helpers['prepareClass']))
                  + bytes.fromhex('440fb7833001000033c966413bc8731c488b93b00000000fb7c14803c0483934c2744a66ffc166413bc872eb4533c0488bd6488bcf')
                  + _rel(b'\xe8', fb + 97, _number(helpers['slotResolver']))
                  + bytes.fromhex('4c8b10488bd5488b4008488bcf4c8b4c2468448b4424604889442460488b5c2440488b6c2448488b7424504883c4305f49ffe20fb7c94803c9486344ca084883c01448c1e0044803c3ebb5'))
    _require(f == expected_f, 'fallback interface lookup, slot-zero request or argument forwarding differs')
    return {'status': 'validated_conditional_wrapper_dispatch', 'method': 'IFix.Core.WrappersManager.CreateDelegate',
            'interfaceSlot': 0, 'argumentOrder': ['receiver', 'System.Type', 'int', 'object'],
            'directImplementationCount': count, 'fallback': 'same-interface-slot-zero',
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['runtime-wrapper-manager-selection', 'runtime-class-selector-and-interface-array-identity',
                           'slot-resolver-returned-pair', 'wrapper-result-and-actual-delegate-invocation']}
