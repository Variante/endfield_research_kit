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

    def resolve_pointer(self, pointer: int) -> GenericInstantiation:
        """Join a carrier's raw pointer without silently choosing an alias."""
        if type(pointer) is not int or not 0 < pointer < 1 << 64:
            raise ContextError(self.source, self.table_va, 'non-null instantiation pointer', pointer)
        candidates = [i for i, (value,) in enumerate(struct.iter_unpack('<Q', self.pointer_bytes))
                      if value == pointer]
        if len(candidates) != 1:
            raise ContextError(self.source, pointer, 'one registered instantiation identity',
                               {'candidateIndices': candidates})
        return self.resolve(candidates[0])


def generic_type_carrier(type_raw: bytes, carrier_raw: bytes, base_raw: bytes,
                         *, type_pointer: int, type_count: int, source: str) -> dict:
    """Decode authenticated tag-15 carrier windows, preserving unknown bytes.

    The caller must read carrier_raw at type_raw.data and base_raw at its first
    pointer with a raw-backed reader. Instantiation dereferencing is separate.
    The 32-byte window is not a certified allocation extent. Only its two
    leading pointers are interpreted; the remaining 16 bytes stay opaque.
    No runtime replacement, class initialization or field meaning is implied.
    """
    for label, raw, size in (('type', type_raw, 16), ('carrier', carrier_raw, 32), ('base', base_raw, 16)):
        if len(raw) != size:
            raise ContextError(source, type_pointer, f'exact {size}-byte {label} range', len(raw))
    if type(type_count) is not int or not 0 <= type_count <= 1_000_000:
        raise ContextError(source, type_pointer, 'bounded type-definition count', type_count)
    carrier_pointer = struct.unpack_from('<Q', type_raw)[0]
    base_pointer, inst_pointer = struct.unpack_from('<QQ', carrier_raw)
    if type_raw[10] != 0x15 or base_raw[10] != 0x12 or not all((carrier_pointer, base_pointer, inst_pointer)):
        raise ContextError(source, type_pointer, 'tag-15 carrier with non-null base/class-inst pointers and tag-12 base',
                           (type_raw[10], base_raw[10], carrier_pointer, base_pointer, inst_pointer))
    definition = struct.unpack_from('<Q', base_raw)[0]
    if definition >= type_count:
        raise ContextError(source, base_pointer, f'on-disk definition index in [0,{type_count})', definition)
    return {'typePointerVa': type_pointer, 'typeRawHex': type_raw.hex().upper(),
            'carrierPointerVa': carrier_pointer, 'carrierRawHex': carrier_raw.hex().upper(),
            'basePointerVa': base_pointer, 'baseRawHex': base_raw.hex().upper(),
            'baseDefinitionIndex': definition, 'classInstantiationPointerVa': inst_pointer,
            'opaqueCarrierTailHex': carrier_raw[16:].hex().upper()}


def select_rgctx_range(raw: bytes, entry_count: int, token: int, *, source: str, offset: int) -> tuple[int, int]:
    """Select one bounded token range, without claiming an RGCTX partition."""
    if len(raw) % 12 or type(entry_count) is not int or not 0 <= entry_count <= 1_000_000:
        raise ContextError(source, offset, '12-byte ranges and bounded entry count', (len(raw), entry_count))
    matches = []
    for index, (actual_token, start, count) in enumerate(struct.iter_unpack('<III', raw)):
        if start > entry_count or count > entry_count-start:
            raise ContextError(source, offset+index*12+4, f'entry range within [0,{entry_count})', (start,count))
        if actual_token == token:
            matches.append((start,count))
    if len(matches) != 1:
        raise ContextError(source, offset, 'one unambiguous token range', {'token':token,'candidates':matches})
    return matches[0]


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


def method_spec_usage_index(raw: bytes, count: int, *, source: str, offset: int) -> int:
    """Decode only an unresolved tag-6 usage cell under the authenticated ABI.

    An aligned live pointer, another tag, or extra bytes are not alternative
    layouts. This does not assert that runtime initialization has executed.
    """
    return unresolved_usage_index(raw, count, tag=6, source=source, offset=offset)


def unresolved_usage_index(raw: bytes, count: int, *, tag: int, source: str, offset: int) -> int:
    """Exact on-disk encoding only; tag identity does not prove live resolution.

    The caller supplies the independently gated target table and expected tag.
    Resolved pointers, other tags, truncated cells and implicit tails fail closed.
    """
    if type(tag) is not int or tag not in (1, 2, 3, 6):
        raise ContextError(source, offset, 'supported usage tag in (1,2,3,6)', tag)
    if len(raw) != 8:
        raise ContextError(source, offset, 'exact eight-byte usage cell', len(raw))
    if type(count) is not int or not 0 <= count <= 1_000_000:
        raise ContextError(source, offset, 'bounded usage target count', count)
    word = struct.unpack('<Q', raw)[0]
    if word > 0xFFFFFFFF or not word & 1 or word >> 29 != tag:
        raise ContextError(source, offset, f'unresolved 32-bit tag-{tag} usage encoding', hex(word))
    index = (word >> 1) & 0x0FFFFFFF
    if index >= count:
        raise ContextError(source, offset, f'usage target index in [0,{count})', index)
    return index


def rip_qword_load_target(raw: bytes, address: int, *, source: str) -> int:
    """Decode one exact x64 MOV r64,[RIP+disp32], not arbitrary machine code.

    The caller must independently prove this is an instruction boundary.
    No target read or live pointer is inferred by this address calculation.
    """
    if type(address) is not int or not 0 <= address <= (1 << 64)-8:
        raise ContextError(source, 0, 'bounded seven-byte instruction address', address)
    if len(raw) != 7:
        raise ContextError(source, address, 'exact seven-byte RIP qword load', len(raw))
    if raw[0] not in (0x48,0x4C) or raw[1] != 0x8B or raw[2] & 0xC7 != 5:
        raise ContextError(source, address, 'MOV r64,[RIP+disp32]', raw.hex().upper())
    target = address+7+struct.unpack_from('<i',raw,3)[0]
    if not 0 <= target <= (1 << 64)-8:
        raise ContextError(source, address, 'bounded eight-byte target address', target)
    return target


def class_sharing_branch(compare: bytes, compare_address: int, load: bytes,
                         load_address: int, advance: bytes, *, source: str) -> int:
    """Verify the gated class-tag branch, returning an anonymous global address.

    This connects instructions only, not the global's initialized value/type.
    Surrounding reachability and argument-vector ABI belong to the native gate.
    """
    if type(compare_address) is not int or not 0 <= compare_address <= (1 << 64)-11:
        raise ContextError(source, 0, 'bounded ten-byte compare/branch address', compare_address)
    if len(compare) != 10 or compare[:6] != bytes.fromhex('80790A120F84'):
        raise ContextError(source, compare_address, 'exact class-tag comparison and near JE', compare.hex().upper())
    destination = compare_address+10+struct.unpack_from('<i',compare,6)[0]
    if destination != load_address:
        raise ContextError(source, compare_address+6, 'branch to canonical-carrier load',
                           {'expectedTarget':load_address,'actualTarget':destination})
    if load[:3] != bytes.fromhex('488B1D') or advance != bytes.fromhex('4883C320'):
        raise ContextError(source, load_address, 'RBX RIP load followed by add RBX,0x20',
                           {'load':load.hex().upper(),'advance':advance.hex().upper()})
    return rip_qword_load_target(load,load_address,source=source)


def named_top_level_type(metadata: bytes, image_name: bytes, namespace: bytes,
                         name: bytes, *, source: str) -> dict:
    """Exact selected-build metadata identity, not a simulated runtime name cache.

    Only 92-byte type definitions and 40-byte image definitions are accepted.
    Exported/forwarded types are intentionally not silently joined.
    """
    if len(metadata) < 0xB0:
        raise ContextError(source,0,'complete metadata section header',len(metadata))
    type_base,type_size = struct.unpack_from('<II',metadata,0xA0)
    string_base,string_size = struct.unpack_from('<II',metadata,0x18)
    image_base,image_size=struct.unpack_from('<II',metadata,0xA8)
    for offset,size,label in ((type_base,type_size,'type'),(string_base,string_size,'string')):
        if offset < 0xB0 or offset > len(metadata) or size > len(metadata)-offset:
            raise ContextError(source,offset,f'bounded {label} section',(offset,size))
    if type_size%92:
        raise ContextError(source,type_base,'exact 92-byte type records',type_size)
    owners = type_image_owners(metadata,type_size//92,source=source)
    regions=sorted((offset,offset+size) for offset,size in
                   ((type_base,type_size),(string_base,string_size),(image_base,image_size)) if size)
    for previous,current in zip(regions,regions[1:]):
        if current[0]<previous[1]:
            raise ContextError(source,current[0],'disjoint string/type/image sections',(previous,current))
    def string(index):
        if not 0 <= index < string_size:
            raise ContextError(source,string_base,'bounded metadata string index',index)
        end=metadata.find(b'\0',string_base+index,string_base+string_size)
        if end < 0:
            raise ContextError(source,string_base+index,'NUL within string section','unterminated')
        return metadata[string_base+index:end]
    images=[]
    for i in range(image_size//40):
        row=image_base+i*40
        if string(struct.unpack_from('<i',metadata,row)[0])==image_name:
            images.append(i)
    if len(images)!=1:
        raise ContextError(source,image_base,'unique exact image name',images)
    image_index=images[0]
    image_offset=image_base+image_index*40
    exported_count=struct.unpack_from('<I',metadata,image_offset+20)[0]
    if exported_count:
        raise ContextError(source,image_offset+20,'no unjoined exported types',exported_count)
    matches=[]
    for i,owner in enumerate(owners):
        if owner!=image_index:
            continue
        row=type_base+i*92
        ni,nsi,byval,declaring=struct.unpack_from('<iiii',metadata,row)
        row_name,row_namespace=string(ni),string(nsi)
        if declaring==-1 and row_name==name and row_namespace==namespace:
            if byval<0:
                raise ContextError(source,row+8,'nonnegative byval type index',byval)
            matches.append({'imageIndex':image_index,'typeDefinitionIndex':i,'typeDefinitionOffset':row,
                            'byvalTypeIndex':byval,'typeDefinitionRawHex':metadata[row:row+92].hex().upper()})
    if len(matches)!=1:
        raise ContextError(source,type_base,'unique exact top-level type identity',
                           [m['typeDefinitionIndex'] for m in matches])
    return matches[0]


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
