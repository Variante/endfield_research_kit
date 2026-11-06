"""Selected-image unmanaged layouts, without treating managed size as framing.

Callers must independently prove the wire operation. These layouts only name
the fields inside a proved raw copy, retaining every byte including padding.
"""
from __future__ import annotations

import math
import struct

from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.wrapper_members import _Deriver

PRIMITIVES = {'bool':'?', 'byte':'B', 'sbyte':'b', 'short':'h', 'ushort':'H',
              'char':'H', 'int':'i', 'uint':'I', 'long':'q', 'ulong':'Q',
              'float':'f', 'double':'d'}


class StoredValueLayouts:
    def __init__(self, image):
        self.image = image
        self.deriver = _Deriver(image)
        self.deriver.index_wrappers()
        self.layouts = {}

    def layout(self, name, width, stack=()):
        key = (name, width)
        if key in self.layouts:
            return self.layouts[key]
        if name in stack:
            raise ValueError('storedValueLayout.recursive-value:' + str(name))
        fmt = PRIMITIVES.get(name)
        if fmt:
            if struct.calcsize('<' + fmt) != width:
                raise ValueError('storedValueLayout.scalar-width:' + str(key))
            return dict(typeName=name, bytes=width, format=fmt)
        rows = self.image.named_type_definitions.get(name, ())
        if len(rows) != 1:
            raise ValueError('storedValueLayout.unique-selected-type:' + str(name))
        td = rows[0]; md = self.image.metadata; d = self.deriver
        offsets = runtime_type_field_offsets(md, self.image.pe, self.image.registration, td.index)
        table = int(self.image.registration['typeDefinitionsSizes'], 16)
        ptr = self.image.pe.u64_at_va(table + td.index * 8)
        actual = struct.unpack('<I', self.image.pe.bytes_at_va(ptr, 4))[0] - 16
        if actual != width:
            raise ValueError(f'storedValueLayout.selected-size:{name}:expected={width}:actual={actual}')
        fields = []
        for field in md.fields_for(td):
            attrs = d._field_attributes(field.type_index)
            if attrs is None:
                raise ValueError('storedValueLayout.field-attributes:' + name)
            if attrs & 16:
                continue
            declared = d._declared_type_name(field.type_index)
            field_name = md.string(field.name_index)
            at = offsets[field_name] - 16
            if declared in PRIMITIVES:
                size = struct.calcsize('<' + PRIMITIVES[declared])
            else:
                child = d._type_definition_for(field.type_index)
                if child is None:
                    raise ValueError('storedValueLayout.non-value-field:' + name + '.' + field_name)
                child_ptr = self.image.pe.u64_at_va(table + child * 8)
                size = struct.unpack('<I', self.image.pe.bytes_at_va(child_ptr, 4))[0] - 16
            if not 0 <= at < at + size <= width:
                raise ValueError('storedValueLayout.field-extent:' + name + '.' + field_name)
            fields.append(dict(fieldName=field_name, offset=at,
                               layout=self.layout(declared, size, (*stack, name))))
        if not fields:
            raise ValueError('storedValueLayout.empty-value:' + name)
        result = dict(typeName=name, bytes=width, fields=fields)
        self.layouts[key] = result
        return result

    def read(self, name, raw):
        return project(self.layout(name, len(raw)), raw)


def project(layout, raw):
    if len(raw) != layout['bytes']:
        raise ValueError('storedValueLayout.projection-width')
    if 'format' in layout:
        value = struct.unpack('<' + layout['format'], raw)[0]
        if layout['typeName'] in ('float', 'double'):
            return dict(value=value if math.isfinite(value) else str(value), rawHex=raw.hex())
        if layout['typeName'] == 'bool' and raw not in (b'\0', b'\1'):
            return dict(value=value, rawHex=raw.hex())
        return value
    return dict(typeName=layout['typeName'], rawHex=raw.hex(), fields={
        field['fieldName']: project(field['layout'], raw[field['offset']:field['offset'] + field['layout']['bytes']])
        for field in layout['fields']})
