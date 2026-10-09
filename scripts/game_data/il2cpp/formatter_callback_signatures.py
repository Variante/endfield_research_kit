"""Prove declared formatter inheritance, slot and closed argument substitution.

This checks selected metadata and typed allocation/constructor declarations.
It does not substitute a metadata vtable for the receiver's live native vtable,
or assume an unregistered closed MethodInfo has a particular shared pointer.
"""
from __future__ import annotations
import struct
from typing import Any, Callable
from .context import type_parameter_owner
from .reference_layouts import NativeReferenceContext
from .formatter_composition import _vtable, validate_typed_usage_context


def validate_adapter_callback_signature(image: Any, spec: dict, eager: dict,
                                        base_deserialize: int, *, fail: Callable) -> dict:
    selected = NativeReferenceContext(image); metadata = image.metadata
    section = metadata.sections['genericContainers']
    containers = [td.generic_container_index for td in metadata.types]
    def container(td, count):
        at = section.offset + td.generic_container_index * 16
        if td.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
            fail('callback-container-range', 'selected bounded class generic container', td.index)
        owner, actual_count, is_method, start = struct.unpack_from('<iiii', metadata.buf, at)
        if (owner, actual_count, is_method) != (td.index, count, 0) or start < 0:
            fail('callback-container-owner', [td.index, count, 0], [owner, actual_count, is_method, start])
        for ordinal in range(count):
            actual = type_parameter_owner(metadata.buf, start + ordinal, containers, source='formatterCallbackSignature')
            if actual['typeIndex'] != td.index or actual['ordinal'] != ordinal:
                fail('callback-reciprocal-var', [td.index, ordinal], actual)
        return start
    adapter = selected.index.types[spec['typeName']]
    if (adapter.index != spec['typeDefinition'] or adapter.flags != spec['flags']
            or adapter.flags & 0x80 or not adapter.flags & 0x100 or selected.is_value_type(spec['typeName'])):
        fail('callback-adapter-owner', 'same selected sealed nonabstract reference adapter', spec)
    start = container(adapter, 2)
    if type(spec['returnTypeFlags']) is not int or spec['returnTypeFlags'] not in (0, 0x80):
        fail('callback-void-record-flags', 'selected void record without byref, pinned or modifiers', spec['returnTypeFlags'])
    method_row = spec['deserializeMethod']; image.validate_method_row(method_row, label='formatterCallbackSignature')
    method = metadata.methods[method_row[0]]
    base_method = metadata.methods[base_deserialize]
    base = metadata.types[base_method.declaring_type]
    if image.type_name(base.index) != spec['baseFormatterType'] or selected.is_value_type(spec['baseFormatterType']):
        fail('callback-parent-owner', spec['baseFormatterType'], image.type_name(base.index))
    base_start = container(base, 1)
    def signature(m, owner, variable):
        parameters = metadata.parameters_for(m)
        result = image.pe.bytes_at_va(selected.type_pointer(m.return_type), 16)
        if (m.declaring_type != owner.index or metadata.string(m.name_index) != 'Deserialize'
                or m.flags & 0x10 or not m.flags & 0x40 or m.generic_container_index >= 0
                or m.slot != spec['slot'] or len(parameters) != 2
                or len(result) != 16 or result[10:12] != bytes((1, spec['returnTypeFlags']))):
            fail('callback-deserialize-abi', 'instance virtual void slot with two byrefs and no method generics',
                 {'method': m.index, 'owner': m.declaring_type,
                  'name': metadata.string(m.name_index), 'flags': m.flags,
                  'genericContainerIndex': m.generic_container_index, 'slot': m.slot,
                  'parameterCount': len(parameters), 'returnTypeRecordHex': result.hex()})
        reader = image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index), 16)
        value = image.pe.bytes_at_va(selected.type_pointer(parameters[1].type_index), 16)
        reader_definition = selected.index.types['MemoryPack.MemoryPackReader'].index
        if (len(reader) != 16 or reader[10:12] != b'\x11\x20'
                or int.from_bytes(reader[:8], 'little') != reader_definition
                or not selected.is_value_type('MemoryPack.MemoryPackReader')
                or len(value) != 16 or value[10:12] != b'\x13\x20'
                or int.from_bytes(value[:8], 'little') != variable):
            fail('callback-byref-ownership', 'same unboxed Reader and owner VAR ordinal zero byref',
                {'reader': reader.hex(), 'value': value.hex()})
    signature(method, adapter, start); signature(base_method, base, base_start)
    _vtable(image, adapter.index, spec['slot'], method.index, 'formatterCallbackSignature')
    if base_method.flags != spec['baseMethodFlags'] or not base_method.flags & 0x400:
        fail('callback-base-abstract-declaration', 'same selected abstract base method', base_method.flags)
    vtable = metadata.sections['vtableMethods']
    at = vtable.offset + (base.vtable_start + spec['slot']) * 4
    if not (0 <= spec['slot'] < base.vtable_count and vtable.offset <= at <= vtable.offset + vtable.size - 4):
        fail('callback-base-slot-range', 'bounded base metadata slot', [base.index, spec['slot']])
    base_word = struct.unpack_from('<I', metadata.buf, at)[0]
    if type(spec['baseSlotWord']) is not int or base_word != spec['baseSlotWord']:
        fail('callback-base-slot-encoding', spec['baseSlotWord'], base_word)
    parent = image.pe.bytes_at_va(selected.type_pointer(adapter.parent_index), 16)
    if len(parent) != 16 or parent[10:12] != b'\x15\x00':
        fail('callback-parent-reference', 'undecorated generic reference parent', parent.hex())
    parent_definition, parent_inst = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(parent[:8], 'little'), 16))
    leaf = image.pe.bytes_at_va(parent_definition, 16)
    args = image.instantiations.resolve_pointer(parent_inst).arguments
    if len(leaf) != 16 or leaf[10:12] != b'\x12\x00' or int.from_bytes(leaf[:8], 'little') != base.index or len(args) != 1:
        fail('callback-parent-substitution', 'same declared formatter base with one argument', parent.hex())
    raw_arg = image.pe.bytes_at_va(args[0].type_pointer_va, 16)
    if len(raw_arg) != 16 or raw_arg[10:12] != b'\x13\x00' or int.from_bytes(raw_arg[:8], 'little') != start:
        fail('callback-parent-var', 'same adapter original VAR ordinal zero', raw_arg.hex())
    for usage in (eager['allocation'], eager['constructor']):
        validate_typed_usage_context(image, usage, label='formatterCallbackSignature')
    original, wrapper = eager['originalType'], eager['wrapperType']
    if (eager['constructor']['typeName'] != spec['typeName']
            or eager['constructor']['classArguments'] != [original, wrapper]
            or eager['constructor']['methodArguments'] != []):
        fail('callback-closed-constructor', 'same original/wrapper ordered closed class arguments', eager['constructor'])
    allocation = image.pe.bytes_at_va(selected.type_pointer(eager['allocation']['typeIndex']), 16)
    if len(allocation) != 16 or allocation[10:12] != b'\x15\x00':
        fail('callback-closed-allocation', 'undecorated generic reference allocation', allocation.hex())
    allocation_definition, allocation_inst = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(allocation[:8], 'little'), 16))
    definition = image.pe.bytes_at_va(allocation_definition, 16)
    arguments = image.instantiations.resolve_pointer(allocation_inst).arguments
    if (len(definition) != 16 or definition[10:12] != b'\x12\x00'
            or int.from_bytes(definition[:8], 'little') != adapter.index or len(arguments) != 2):
        fail('callback-closed-allocation-owner', 'same adapter definition with two ordered arguments', allocation.hex())
    names = []
    for arg, name in zip(arguments, (original, wrapper), strict=True):
        raw = image.pe.bytes_at_va(arg.type_pointer_va, 16)
        if (len(raw) != 16 or raw[10:12] != b'\x12\x00'
                or image.type_name(int.from_bytes(raw[:8], 'little')) != name or selected.is_value_type(name)):
            fail('callback-closed-reference-argument', name, raw.hex())
        names.append(name)
    if eager['allocation']['typeName'] != spec['typeName'] + '<' + ','.join(names) + '>':
        fail('callback-closed-allocation-name', 'same exact complete closed identity', eager['allocation']['typeName'])
    return {'adapterType': spec['typeName'], 'originalType': original, 'wrapperType': wrapper,
        'slot': spec['slot'], 'deserializeDefinition': method.index, 'baseDeserializeDefinition': base_method.index,
        'declaredAdapterSlotAndABIProved': True, 'reciprocalOriginalParentSubstitutionProved': True,
        'baseMethodAbstract': True, 'baseSlotWord': base_word,
        'baseSlotEncodingInterpretedAsCallbackTarget': False,
        'closedEagerArgumentOrderProved': True, 'readerByrefSameUnboxedType': True,
        'originalOutputByrefSameClosedReferenceType': True,
        'actualRuntimeVtableOrMethodInfoObserved': False, 'callbackCursorEqualityProved': False}
