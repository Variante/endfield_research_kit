"""Owned byref ReadPackable/ReadValue parameters and formatter slot joins.

The caller authenticates complete current RGCTX ranges. These checks join the
two owned MVARs to the independently checked provider and formatter ABI; they
do not observe runtime context inflation or assign names to physical entries.
"""
from __future__ import annotations
import struct
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def validate_byref_contexts(image, packable, reader, entries, return_context, *, fail):
    meta = image.metadata; types = NativeReferenceContext(image)
    section = meta.sections['genericContainers']

    def parameter(pointer, start, *, byref=False):
        raw = image.pe.bytes_at_va(pointer, 16)
        if raw[10:12] != bytes((0x1e, 0x20 if byref else 0)) or int.from_bytes(raw[:8], 'little') != start:
            fail('byref-owned-parameter', [start, byref], raw.hex())

    def owner(row, name):
        m = meta.methods[row['definition']]; params = meta.parameters_for(m)
        at = section.offset+m.generic_container_index*16
        result = image.pe.bytes_at_va(types.type_pointer(m.return_type), 16)
        if (row.get('isMethod') is not True or row['typeName'] != 'MemoryPack.MemoryPackReader'
                or image.type_name(m.declaring_type) != row['typeName'] or meta.string(m.name_index) != name
                or m.flags & 0x10 or m.generic_container_index < 0 or len(params) != 1
                or not section.offset <= at <= section.offset+section.size-16
                or result[10] != 1 or result[11] & 0x20 or types.type_name(m.return_type) != 'void'):
            fail('byref-reader-abi', 'instance generic void Reader.'+name+' with one byref parameter',
                {'definition': m.index, 'declaringType': image.type_name(m.declaring_type),
                    'methodName': meta.string(m.name_index), 'flags': m.flags,
                    'genericContainerIndex': m.generic_container_index, 'parameterCount': len(params),
                    'returnTypeRecordHex': result.hex().upper(), 'declaredContext': row})
        definition, count, is_method, start = struct.unpack_from('<iiii', meta.buf, at)
        identity = method_parameter_owner(meta.buf, start, [m.generic_container_index for m in meta.methods], source='packableByref')
        if (definition, count, is_method) != (m.index, 1, 1) or identity['methodIndex'] != m.index or identity['ordinal'] != 0:
            fail('byref-reciprocal-mvar', [m.index, 1, 1, 0], identity)
        parameter(types.type_pointer(params[0].type_index), start, byref=True)
        return start

    def slots(row, kinds):
        if [r['relativeSlot'] for r in row['entries']] != list(range(len(kinds))):
            fail('byref-complete-context-slots', kinds, row['entries'])
        for r, kind in zip(row['entries'], kinds, strict=True):
            raw = bytes.fromhex(r['rawHex'])
            if (len(raw) != 16 or r['kind'] != kind or int.from_bytes(raw[:4], 'little') != kind
                    or image.pe.u32_at_va(int.from_bytes(raw[8:], 'little')) != r['index']):
                fail('byref-context-payload', kind, r)
        return row['entries']

    def argument(instance, start):
        args = image.instantiations.resolve(instance).arguments
        if len(args) != 1: fail('byref-context-arity', 1, len(args))
        parameter(args[0].type_pointer_va, start)

    packable_var = owner(packable, 'ReadPackable'); reader_var = owner(reader, 'ReadValue')
    ps = slots(packable, [3]); rs = slots(reader, [3, 2, 3])
    nested = entries.specs[ps[0]['index']]
    if list(nested) != ps[0]['methodSpec'] or nested[:2] != (reader['definition'], -1):
        fail('byref-packable-read-value-owner', reader['definition'], nested)
    argument(nested[2], packable_var)
    provider = entries.specs[rs[0]['index']]; deserialize = entries.specs[rs[2]['index']]
    if (list(provider) != rs[0]['methodSpec'] or provider[:2] != (return_context['providerMethodDefinition'], -1)
            or list(deserialize) != rs[2]['methodSpec']
            or deserialize != (return_context['formatterDeserializeDefinition'], provider[2], -1)
            or return_context['formatterSlot'] != 5 or return_context['providerKeyAndResultOwned'] is not True):
        fail('byref-provider-formatter-abi-join', return_context, [provider, deserialize])
    argument(provider[2], reader_var)
    raw = image.pe.bytes_at_va(types.type_pointer(rs[1]['index']), 16)
    if raw[10:12] != b'\x15\x00': fail('byref-formatter-kind', 'undecorated reference instantiation', raw.hex())
    definition_ptr, instance_ptr = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
    definition = image.pe.bytes_at_va(definition_ptr, 16)
    if (definition[10:12] != b'\x12\x00'
            or image.type_name(int.from_bytes(definition[:8], 'little')) != 'MemoryPack.MemoryPackFormatter`1'):
        fail('byref-formatter-owner', 'MemoryPackFormatter reference class', definition.hex())
    instance = image.instantiations.resolve_pointer(instance_ptr)
    if instance.index != provider[2]: fail('byref-exact-formatter-instance', provider[2], instance.index)
    argument(instance.index, reader_var)
    return {'packableDefinition': packable['definition'], 'readerDefinition': reader['definition'],
        'providerDefinition': return_context['providerMethodDefinition'],
        'formatterDeserializeDefinition': return_context['formatterDeserializeDefinition'], 'formatterSlot': 5,
        'sameOwnedMethodParameterToProviderAndFormatter': True, 'runtimeInflationObserved': False}
