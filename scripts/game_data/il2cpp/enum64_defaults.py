"""Decode fixed-width Int64/UInt64 enum defaults from an authenticated build.

Unlike the metadata's compressed Int32 constants, these are eight raw
little-endian bytes. Backing and each default primitive must agree; no fallback
to another width or interpretation is admitted.
"""
from __future__ import annotations

from scripts.game_data.il2cpp.protocol import runtime_type_name


def native_enum64_members(metadata, defaults, pe, registration, type_name):
    owners = [td for td in metadata.types if metadata.type_full_name(td) == type_name]
    if len(owners) != 1:
        raise ValueError(f'enum64 owner missing or ambiguous: {type_name}')
    fields = list(metadata.fields_for(owners[0]))
    backing = [f for f in fields if metadata.string(f.name_index) == 'value__']
    if len(backing) != 1:
        raise ValueError(f'enum64 backing missing or ambiguous: {type_name}')

    def primitive(index):
        if not 0 <= index < int(registration['typesCount']):
            raise ValueError(f'enum64 primitive outside type table: {type_name}:{index}')
        pointer = pe.u64_at_va(int(registration['types'], 16) + index * 8)
        if not pointer:
            raise ValueError(f'enum64 primitive pointer missing: {type_name}:{index}')
        return runtime_type_name(pe, metadata, pointer)

    kind = primitive(backing[0].type_index)
    if kind not in ('long', 'ulong'):
        raise ValueError(f'enum64 unsupported backing: {type_name}:{kind}')
    section = metadata.sections['fieldAndParameterDefaultValueData']
    rows = []
    for field in fields:
        name = metadata.string(field.name_index)
        if name == 'value__' or field.index not in defaults:
            continue
        default_type, data_index = defaults[field.index]
        if primitive(default_type) != kind:
            raise ValueError(f'enum64 member primitive differs: {type_name}.{name}')
        start = section.offset + data_index
        end = start + 8
        if not section.offset <= start < end <= section.offset + section.size or end > len(metadata.buf):
            raise ValueError(f'enum64 member exceeds blob: {type_name}.{name}')
        rows.append({'id': int.from_bytes(metadata.buf[start:end], 'little', signed=kind == 'long'),
                     'name': name, 'fieldIndex': field.index, 'token': f'0x{field.token:08x}'})
    return sorted(rows, key=lambda row: (row['id'], row['name']))
