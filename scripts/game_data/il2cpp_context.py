"""Bounded IL2CPP generic-instantiation pointer-table decoding.

The caller must authenticate the native inputs and registration ABI, and supply
a raw-backed PE reader. This module does not select a runtime MethodInfo,
formatter, serialized field, or source cursor.
"""
from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from typing import Callable


class ContextError(ValueError):
    def __init__(self, source: str, offset: int, expected: object, actual: object):
        self.diagnostics = {"source": source, "offset": offset,
                            "expected": expected, "actual": actual}
        super().__init__(f"{source}: offset=0x{offset:X} expected={expected!r} actual={actual!r}")


@dataclass(frozen=True)
class GenericArgument:
    index: int
    type_pointer_va: int
    raw_type_record_hex: str


@dataclass(frozen=True)
class GenericInstantiation:
    index: int
    table_slot_va: int | None
    record_va: int | None
    argument_vector_va: int | None
    padding_hex: str
    arguments: tuple[GenericArgument, ...]

    def as_dict(self) -> dict:
        return asdict(self)


class GenericInstantiationTable:
    """Snapshot a pointer array, then dereference each requested 16-byte record.

    In particular, table + index*16 is NOT the record address. Preserve that
    distinction even when adjacent bytes happen to resemble a valid record.
    """

    def __init__(self, read_raw: Callable[[int, int], bytes], table_va: int,
                 count: int, *, source: str, max_arguments: int = 64):
        self.read_raw = read_raw
        self.source = source
        self.table_va = table_va
        self.count = count
        self.max_arguments = max_arguments
        if type(table_va) is not int or not 0 <= table_va < (1 << 64):
            raise ContextError(source, 0, "unsigned 64-bit table address", table_va)
        if type(count) is not int or not 0 <= count <= 1_000_000:
            raise ContextError(source, table_va, "pointer count in [0, 1000000]", count)
        if type(max_arguments) is not int or not 0 <= max_arguments <= 1_000_000:
            raise ContextError(source, table_va, "bounded nonnegative argument limit", max_arguments)
        self.pointer_bytes = self._read(table_va, count * 8) if count else b""

    def _read(self, va: int, size: int) -> bytes:
        if type(va) is not int or not 0 < va < (1 << 64) or size < 0 or size > (1 << 64) - va:
            raise ContextError(self.source, va if type(va) is int else 0,
                               "non-null bounded 64-bit raw range", (va, size))
        try:
            data = self.read_raw(va, size)
        except (ValueError, OSError, struct.error) as error:
            raise ContextError(self.source, va, f"{size} raw-backed bytes", str(error)) from error
        if len(data) != size:
            raise ContextError(self.source, va, size, len(data))
        return data

    def resolve(self, index: int) -> GenericInstantiation:
        if type(index) is not int or index < -1 or index >= self.count:
            raise ContextError(self.source, self.table_va, f"index -1 or [0, {self.count})", index)
        if index == -1:
            return GenericInstantiation(index, None, None, None, "", ())
        slot = self.table_va + index * 8
        pointer = struct.unpack_from("<Q", self.pointer_bytes, index * 8)[0]
        record = self._read(pointer, 16)
        count = struct.unpack_from("<I", record)[0]
        vector = struct.unpack_from("<Q", record, 8)[0]
        if count > self.max_arguments:
            raise ContextError(self.source, pointer, f"argument count <= {self.max_arguments}", count)
        pointers = self._read(vector, count * 8) if count else b""
        args = []
        for ordinal in range(count):
            type_pointer = struct.unpack_from("<Q", pointers, ordinal * 8)[0]
            raw_type = self._read(type_pointer, 16)
            args.append(GenericArgument(ordinal, type_pointer, raw_type.hex().upper()))
        return GenericInstantiation(index, slot, pointer, vector,
                                    record[4:8].hex().upper(), tuple(args))


def method_parameter_owner(metadata: bytes, index: int, method_containers: list[int],
                           *, source: str) -> dict:
    """Validate both directions of an MVAR owner join under the gated metadata ABI."""
    def section(slot):
        header = 8 + slot * 8
        if header + 8 > len(metadata):
            raise ContextError(source, header, 'complete section pair', len(metadata))
        offset, size = struct.unpack_from('<II', metadata, header)
        if size % 16 or offset < 128 or offset > len(metadata) or size > len(metadata) - offset:
            raise ContextError(source, header, 'bounded 16-byte record section', (offset, size))
        return offset, size // 16
    parameter_base, parameter_count = section(12)
    container_base, container_count = section(14)
    if max(parameter_base, container_base) < min(parameter_base + parameter_count * 16,
                                                container_base + container_count * 16):
        raise ContextError(source, container_base, 'nonoverlapping parameter/container sections',
                           (parameter_base, parameter_count, container_base, container_count))
    if type(index) is not int or not 0 <= index < parameter_count:
        raise ContextError(source, parameter_base, f'parameter index in [0,{parameter_count})', index)
    parameter_offset = parameter_base + index * 16
    owner, name, constraints_start, constraints_count, ordinal, flags = struct.unpack_from('<iihhHH', metadata, parameter_offset)
    if not 0 <= owner < container_count:
        raise ContextError(source, parameter_offset, 'bounded container index', owner)
    container_offset = container_base + owner * 16
    method, argc, is_method, start = struct.unpack_from('<iiii', metadata, container_offset)
    if (is_method != 1 or argc < 0 or start < 0 or start + argc > parameter_count
            or not start <= index < start + argc or ordinal != index - start):
        raise ContextError(source, container_offset, 'method container with reciprocal parameter range and ordinal',
                           (method, argc, is_method, start, index, ordinal))
    if not 0 <= method < len(method_containers) or method_containers[method] != owner:
        raise ContextError(source, container_offset, 'reciprocal method/container identity', (method, owner))
    return {'parameterIndex': index, 'parameterOffset': parameter_offset,
            'parameterRawHex': metadata[parameter_offset:parameter_offset+16].hex().upper(),
            'containerIndex': owner, 'containerOffset': container_offset,
            'containerRawHex': metadata[container_offset:container_offset+16].hex().upper(),
            'methodIndex': method, 'ordinal': ordinal,
            'boundary': 'Exact reciprocal identity only; constraints and names remain uninterpreted.'}


def type_image_owners(metadata: bytes, type_count: int, *, source: str) -> list[int]:
    """Exact partition of type indices by gated 40-byte image definitions.

    Native initialization copies each image's type start/count to its directory
    carrier. Overlaps are ambiguous, even if native lookup would choose one.
    Other image fields remain uninterpreted here.
    """
    if type(type_count) is not int or not 0 <= type_count <= 1_000_000:
        raise ContextError(source, 0xA8, 'bounded type count', type_count)
    if len(metadata) < 0xB0:
        raise ContextError(source, 0xA8, 'complete image section pair', len(metadata))
    offset, size = struct.unpack_from('<II', metadata, 0xA8)
    if offset < 0xB0 or offset > len(metadata) or size > len(metadata)-offset or size % 40:
        raise ContextError(source, 0xA8, 'bounded 40-byte image section', (offset, size))
    owners = [-1] * type_count
    for image_index in range(size // 40):
        row = offset + image_index * 40
        start, count = struct.unpack_from('<iI', metadata, row+8)
        if count == 0 and start == -1:
            continue
        if start < 0 or start > type_count or count > type_count-start:
            raise ContextError(source, row+8, f'type interval within [0,{type_count})', (start, count))
        for index in range(start, start+count):
            if owners[index] != -1:
                raise ContextError(source, row+8, 'unambiguous image owner',
                                   {'typeIndex': index, 'candidateImages': [owners[index], image_index]})
            owners[index] = image_index
    if -1 in owners:
        raise ContextError(source, offset, 'complete type/image partition', {'uncoveredTypeIndex':owners.index(-1)})
    return owners


def match_image_modules(image_names: list[str], modules: list[tuple[str, int]], *, source: str) -> dict[str, int]:
    """Fail closed on duplicate names; do not reproduce native last-match wins."""
    if len(set(image_names)) != len(image_names):
        raise ContextError(source, 0, 'unique metadata image names', image_names)
    found = {}
    for index, (name, pointer) in enumerate(modules):
        if not isinstance(name, str) or not name or type(pointer) is not int or not 0 < pointer < 1 << 64:
            raise ContextError(source, index*8, 'named non-null module pointer', (name, pointer))
        if name in found:
            raise ContextError(source, index*8, 'unambiguous module name',
                               {'name':name, 'candidatePointers':[found[name],pointer]})
        found[name] = pointer
    if set(found) != set(image_names):
        raise ContextError(source, 0, 'complete image/module name correspondence',
                           {'missing':sorted(set(image_names)-set(found)), 'unexpected':sorted(set(found)-set(image_names))})
    return found
