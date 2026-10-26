"""Ordinary declared types and the concrete Param generic-definition bridge."""
from __future__ import annotations

import struct

from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.scalar_param_native import need

PARAM_TYPE = 'Beyond.Gameplay.Actions.Param`1'


def type_record(image, context, index):
    return image.pe.bytes_at_va(context.type_pointer(index), 16)


def ordinary(raw, kind, label, *, byref=False):
    need(label, 'recordSize', 16, len(raw))
    need(label, 'typeKind', kind, raw[10])
    need(label, 'typeFlags', 0x20 if byref else 0, raw[11] & 0x7f)


def param_reference(image, raw, argument_kind, argument_index=None):
    ordinary(raw, 0x15, 'paramValue.paramReference')
    need('paramValue.paramReference', 'referenceMarker', 0, raw[11] & 0x80)
    base, inst = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
    definition_raw = image.pe.bytes_at_va(base, 16)
    ordinary(definition_raw, 0x12, 'paramValue.paramDefinition')
    need('paramValue.paramDefinition', 'referenceMarker', 0, definition_raw[11] & 0x80)
    definition = int.from_bytes(definition_raw[:8], 'little')
    need('paramValue.paramReference', 'definition', PARAM_TYPE, image.type_name(definition))
    context = NativeReferenceContext(image)
    fields = [field for field in image.metadata.fields_for(image.metadata.types[definition])
              if image.metadata.string(field.name_index) == 'constValue']
    need('paramValue.paramReference', 'constantFields', 1, len(fields))
    constant_raw = type_record(image, context, fields[0].type_index)
    ordinary(constant_raw, 0x13, 'paramValue.classVariable')
    owner = type_parameter_owner(image.metadata.buf, int.from_bytes(constant_raw[:8], 'little'),
                                 [td.generic_container_index for td in image.metadata.types], source='paramValue.classVariable')
    need('paramValue.classVariable', 'owner', definition, owner['typeIndex'])
    need('paramValue.classVariable', 'ordinal', 0, owner['ordinal'])
    need('paramValue.classVariable', 'arity', 1, struct.unpack_from('<i', bytes.fromhex(owner['containerRawHex']), 4)[0])
    arguments = image.instantiations.resolve_pointer(inst).arguments
    need('paramValue.paramReference', 'argumentCount', 1, len(arguments))
    argument_raw = image.pe.bytes_at_va(arguments[0].type_pointer_va, 16)
    ordinary(argument_raw, argument_kind, 'paramValue.paramArgument')
    if argument_index is not None:
        need('paramValue.paramReference', 'formalArgument', argument_index, int.from_bytes(argument_raw[:8], 'little'))
    return definition
