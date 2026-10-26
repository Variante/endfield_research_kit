"""Authenticate IFix array construction, length, loads and stores offline.

Newarr selects VM.externTypes with the signed authored Operand and requests
Array.CreateInstance(Type,int) with the top slot's low Int32. Its returned
object is stored at the slot's physical evaluation-base index, truncated to
Int32 for this particular managed store; the slot becomes Object/that index.
Ldlen fetches the array through Value1, clears the slot's physical managed
entry, sets Integer and stores the returned Array.get_Length Int32.

Loads replace the lower of array/index with the result and pop one slot.
Primitive loads first clear the array slot's physical managed entry. I1 tries
sbyte then bool, U1 byte then bool; Boolean reads normalize any nonzero byte
to one. I2 tries short then ushort and U2 char then ushort, extending the
selected word with the matching sign. I4 and U4 read int and uint raw low
words. I8 tries long then ulong and I tries nint then nuint, storing raw
64-bit words and Long. R4/R8 read their matching float/double array and tag.
The finite fallback misses for I/I8/I1/U1/I2/U2 retain the previous payload
after the tag, clear and pop; they do not manufacture zero or an exception.

Ldelem_Ref reads object[], stores the returned reference at the destination's
physical managed index and rewrites Value1, while retaining the original tag.
It does not clear the consumed index slot's managed entry. Ldelem_Any requests
Array.GetValue(int), then the named GetElementType virtual slot on GetType's
result, and forwards the value/type to the inherited PushObject recipe. Any
uses the runtime array element type; its authored Operand is not read.

Stores consume array/index/value and pop three slots. Numeric stores read the
value payload directly, clear only the array slot's physical managed entry,
then try the typed array helpers: I1 sbyte/bool/byte, I2 short/ushort/char,
I4 int/uint, I8 long/ulong and I nint/nuint. Boolean stores normalize a nonzero
Int32 to one; byte/word/dword stores keep the low width. R4/R8 use matching
floating payloads. A complete type-selection miss skips the element write but
still clears/pops. Native integer stores request the named IntPtr(long) or
UIntPtr(ulong) constructor and store the post-call local's raw 64-bit word;
UIntPtr constructor success is not established by the caller recipe.

Stelem_Ref requires the value tag Object before fetching its managed Value1,
requests assignment checking and a reference store, then clears the physical
array and value managed entries. Its other-tag branch leaves this proof at an
authenticated opaque shared exception entry. Stelem_Any requests GetType and
GetElementType, forwards the value slot to inherited ToObject with clone=false,
requests Array.SetValue, and clears the physical array/value entries afterward.
Reference/Any stores capture replacement before clearing; runtime overlap and
unmodelled helper mutation are not resolved.

Complete finite caller grammars include every selected branch, fallback and
top join up to the inherited PC advance. Access grammars prove unsigned Int32
bounds tests, native width/scale and data offset. Typed cells authenticate
SZARRAY and primitive element carriers, including nested by-reference flags.
The array type predicate is an opaque runtime helper reached through a proved
trampoline; only its null/non-null return controls the recorded alternatives.
The named GetElementType slot and dispatcher prefix are authenticated without
selecting a runtime Type implementation. Native inputs, addresses and hashes
belong to reviewed JSON; no runtime values, array validity, reflection/cast/
allocation success, GC effects or actual VM execution are observed. Recipes
require valid stable storage and normal helper returns without unmodelled
mutation. Existing parent methods/groups own ToObject, PushObject and PC state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_delegate_rules import _method as _parent_method
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_reference_address_rules import _identity, _slice
from scripts.game_data.ifix_vm_reference_update_rules import _ref, _rva, _hash, _expect, _type, _type_pointer


class ArrayRuleError(ValueError):
    """An array recipe lacks its selected native witness."""


_HELPER_REFS = {
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'pointerDifference': 'arithmeticWindows.stackPointerSubtract',
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'arrayFetch32': 'functionPointerRules.helpers.int32ArrayFetch',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'nullCheck': 'negativeFieldRules.helpers.nullCheck',
    'cast': 'referenceUpdateRules.helpers.cast',
    'boundsFailure': 'referenceUpdateRules.helpers.boundsFailure',
    'virtualTypeQuery': 'genericDelegateFactoryRules.helpers.returnQueryHelper',
    'classInitialize': 'objectConversionRules.helpers.classInitialize',
}
_METHOD_REFS = {
    'arrayGet': 'chainFieldRules.methods.arrayGet',
    'arraySet': 'referenceUpdateRules.methods.arraySet',
    'objectGetType': 'functionPointerRules.helpers.objectGetType',
    'pushObject': 'initobjStackEffect.pushObjectMethod',
    'toObject': 'constrainedTypeOperand.stackEffect.toObjectMethod',
}
_TAIL_REFS = {
    'slotPcTail': 'functionPointerRules.slotPcTail',
    'pcAdvance': 'basicOpcodeRules.sharedWindows.pcAdvance',
    'popTopCommit': 'basicOpcodeRules.sharedWindows.pushTopCommit',
    'zeroRegister': 'basicOpcodeRules.sharedWindows.zeroRegister',
    'slotWidth': 'basicOpcodeRules.sharedWindows.slotWidth',
    'loopState': 'basicOpcodeRules.sharedWindows.loopState',
}
_METHODS = {
    'arrayCreate': ('System.Array', 'CreateInstance', ['System.Type', 'int'], 'System.Array', True),
    'arrayLength': ('System.Array', 'get_Length', [], 'int', False),
    'arrayGet': ('System.Array', 'GetValue', ['int'], 'object', False),
    'arraySet': ('System.Array', 'SetValue', ['object', 'int'], 'void', False),
    'objectGetType': ('System.Object', 'GetType', [], 'System.Type', False),
    'intPtrCtor': ('System.IntPtr', '.ctor', ['long'], 'void', False),
    'uintPtrCtor': ('System.UIntPtr', '.ctor', ['ulong'], 'void', False),
    'intPtrInt64': ('System.IntPtr', 'ToInt64', [], 'long', False),
    'uintPtrUInt64': ('System.UIntPtr', 'ToUInt64', [], 'ulong', False),
    'pushObject': ('IFix.Core.EvaluationStackOperation', 'PushObject', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'System.Type'], 'void', True),
    'toObject': ('IFix.Core.EvaluationStackOperation', 'ToObject', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'System.Type', 'IFix.Core.VirtualMachine', 'bool'], 'object', True),
}
_VIRTUAL = ('System.Type', 'GetElementType', [], 'System.Type', False)
_HELPERS = ('tryArrayType', 'tryTypeRuntime', 'arrayFetch8', 'arrayFetch16', 'arrayAddress64',
            'arrayFetchR4', 'arrayFetchR8', 'arrayStore8', 'arrayStore16', 'arrayStore32',
            'arrayStore64', 'arrayStoreBool', 'arrayStoreR4', 'arrayStoreR8')
_TYPE_CODES = {'bool': 0x02, 'char': 0x03, 'sbyte': 0x04, 'byte': 0x05, 'short': 0x06, 'ushort': 0x07,
               'int': 0x08, 'uint': 0x09, 'long': 0x0a, 'ulong': 0x0b, 'float': 0x0c, 'double': 0x0d,
               'nint': 0x18, 'nuint': 0x19, 'object': 0x1c}
_CELLS = {name + 'Array': name + '[]' for name in _TYPE_CODES if name not in ('nint', 'nuint', 'object')}
_CELLS.update(intPtrArray='nint[]', uintPtrArray='nuint[]', objectArray='object[]', uintPtrType='nuint')
_CLAIMS = {
    'schema': 'endfield.ifix-vm-array-rules.v1', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'slotBytes': 12, 'instructionBytes': 8, 'pointerBytes': 8,
    'valueLayoutRef': 'constrainedTypeOperand.stackEffect.valueLayout', 'dispatchRef': 'dispatchRules',
    'usageRefs': {'arrayType': 'referenceUpdateRules.usageCells.arrayType'},
    'helperRefs': _HELPER_REFS, 'methodRefs': _METHOD_REFS, 'tailRefs': _TAIL_REFS,
    'storageBoundary': 'valid-stable-storage-and-normal-helper-returns-without-unmodelled-mutation',
    'aliasBoundary': 'runtime-overlap-helper-mutation-and-concurrent-state-unobserved',
    'typeSelectionBoundary': 'typed-cells-and-null-predicate-branches;runtime-type-helper-results-unobserved',
    'virtualBoundary': 'named-GetElementType-slot-and-shared-dispatch-prefix;runtime-Type-implementation-unobserved',
    'exceptionBoundary': 'Stelem_Ref-other-tag-enters-opaque-shared-exception-route;outcome-unresolved',
    'calleeBoundary': 'Array-API-ToObject-PushObject-and-UIntPtr-constructor-outcomes-inherited-or-unresolved',
    'fileTableJoinBoundary': 'Newarr-reuses-parent-externTypes;other-array-opcode-Operands-unread',
    'tagMembers': {'Integer': 0, 'Long': 1, 'Float': 2, 'Double': 3, 'Object': 8},
}
_RULES = {
    'Newarr': ('signed-Operand-selects-externTypes', 'request-array-create;store-returned-object-at-truncated-physical-index;Object-and-index', 0),
    'Ldlen': ('unread', 'fetch-managed-Value1;clear-physical;Integer-and-returned-length', 0),
    'Ldelem_I1': ('unread', 'clear-physical;Integer;sbyte-sign-extend-or-normalized-bool;miss-retains-payload', -1),
    'Ldelem_U1': ('unread', 'clear-physical;Integer;byte-zero-extend-or-normalized-bool;miss-retains-payload', -1),
    'Ldelem_I2': ('unread', 'clear-physical;Integer;short-sign-extend-or-ushort-zero-extend;miss-retains-payload', -1),
    'Ldelem_U2': ('unread', 'clear-physical;Integer;char-or-ushort-zero-extend;miss-retains-payload', -1),
    'Ldelem_I4': ('unread', 'clear-physical;Integer;int-raw32', -1),
    'Ldelem_U4': ('unread', 'clear-physical;Integer;uint-raw32', -1),
    'Ldelem_I8': ('unread', 'clear-physical;Long;long-or-ulong-raw64;miss-retains-payload', -1),
    'Ldelem_I': ('unread', 'clear-physical;Long;nint-or-nuint-raw64;miss-retains-payload', -1),
    'Ldelem_R4': ('unread', 'clear-physical;Float;float-raw32', -1),
    'Ldelem_R8': ('unread', 'clear-physical;Double;double-raw64', -1),
    'Ldelem_Ref': ('unread', 'object-array-read;managed-physical-replacement-and-Value1;tag-retained', -1),
    'Ldelem_Any': ('unread', 'Array.GetValue-and-runtime-element-type;inherited-PushObject', -1),
    'Stelem_I1': ('unread', 'clear-array-physical;sbyte-low8-or-normalized-bool-or-byte-low8;miss-skips-write', -3),
    'Stelem_I2': ('unread', 'clear-array-physical;short-or-ushort-or-char-low16;miss-skips-write', -3),
    'Stelem_I4': ('unread', 'clear-array-physical;int-or-uint-raw32;miss-skips-write', -3),
    'Stelem_I8': ('unread', 'clear-array-physical;long-or-ulong-raw64;miss-skips-write', -3),
    'Stelem_I': ('unread', 'clear-array-physical;nint-or-nuint-constructor-postcall-local-raw64;miss-skips-write', -3),
    'Stelem_R4': ('unread', 'clear-array-physical;float-raw32', -3),
    'Stelem_R8': ('unread', 'clear-array-physical;double-raw64', -3),
    'Stelem_Ref': ('unread', 'Object-tag-required;managed-Value1-reference-store;clear-array-and-value-physical', -3),
    'Stelem_Any': ('unread', 'runtime-element-type;ToObject-clone-false;Array.SetValue;clear-array-and-value-physical', -3),
}


def _need(ok: bool, label: str) -> None:
    if not ok: raise ArrayRuleError('ifix-array.' + label)


def _named(rows: list[dict], names: Any, label: str) -> dict[str, dict]:
    result = {r.get('name'): r for r in rows}
    _need(len(result) == len(rows) and set(result) == set(names), label + ': missing/duplicate/unknown declarations')
    return result


def _cell_type(image: Any, row: dict, identity: str) -> None:
    at = _rva(row['cellRva']); raw = image.pe.bytes_at_va(image.pe.image_base + at, 8)
    _need(raw == bytes.fromhex(row['rawHex']) and row.get('usageTag') == 1 and row.get('identity') == identity,
          'cell: stored bytes/declaration differ')
    idx = unresolved_usage_index(raw, image.registration['typesCount'], tag=1, source='ifix-array.type', offset=at)
    pointer = _type_pointer(image, idx); carrier = image.pe.bytes_at_va(pointer, 16)
    _need(len(carrier) == 16 and not carrier[11] & 0x20, 'cell: malformed/by-reference type carrier')
    if identity.endswith('[]'):
        _need(carrier[10] == 0x1d, 'cell: expected SZARRAY kind')
        element = int.from_bytes(carrier[:8], 'little'); element_raw = image.pe.bytes_at_va(element, 16)
        _need(len(element_raw) == 16 and not element_raw[11] & 0x20
              and element_raw[10] == _TYPE_CODES[identity[:-2]], 'cell: primitive element kind/by-reference flag differs')
    else:
        _need(carrier[10] == (0x12 if identity == 'System.Array' else _TYPE_CODES[identity]), 'cell: selected type kind differs')
    _need(runtime_type_name(image.pe, image.metadata, pointer) == identity, 'cell: selected type differs')


def _own_signature(image: Any, row: dict, identity: tuple) -> None:
    """Names alone cannot turn a class carrier into a value/primitive carrier."""
    owner, name, params, returned, _static = identity; md = image.metadata
    matches = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
               if md.string(m.name_index) == name and m.parameter_count == len(params)
               and [_type(image, p.type_index) for p in md.parameters_for(m)] == params]
    _need(len(matches) == 1, 'named signature: unique selected overload required')
    method = matches[0]; codes = {'System.Type': 0x12, 'System.Array': 0x12, 'void': 0x01,
                                 'int': 0x08, 'long': 0x0a, 'ulong': 0x0b}
    pairs = [(p.type_index, expected) for p, expected in zip(md.parameters_for(method), params)] + [(method.return_type, returned)]
    for index, expected in pairs:
        raw = image.pe.bytes_at_va(_type_pointer(image, index), 16)
        _need(len(raw) == 16 and raw[10] == codes[expected] and not raw[11] & 0x20,
              'named signature: primitive/class kind or by-reference flag differs')


def _layouts(image: Any, spec: dict, contract: dict) -> int:
    row = spec['externTypesField']; md = image.metadata
    _need(row.get('type') == 'System.Type[]' and row.get('owner') == 'IFix.Core.VirtualMachine'
          and row.get('field') == 'externTypes', 'externTypes: declaration differs')
    owners = [t for t in md.types if md.type_full_name(t) == row['owner']]
    _need(len(owners) == 1, 'externTypes: unique owner required')
    owner = owners[0]; definitions = [f for f in md.fields_for(owner) if md.string(f.name_index) == row['field']]
    _need(len(definitions) == 1 and _type(image, definitions[0].type_index) == row['type'], 'externTypes: field type differs')
    carrier = image.pe.bytes_at_va(_type_pointer(image, definitions[0].type_index), 16)
    _need(not int.from_bytes(carrier[8:10], 'little') & 0x10 and carrier[10] == 0x1d, 'externTypes: static/array carrier differs')
    elem = image.pe.bytes_at_va(int.from_bytes(carrier[:8], 'little'), 16)
    _need(len(elem) == 16 and elem[10] == 0x12 and not elem[11] & 0x20, 'externTypes: element carrier differs')
    actual = runtime_type_field_offsets(md, image.pe, image.registration, owner.index)['externTypes']
    _need(type(row.get('offset')) is int and actual == row['offset'] and 0 <= actual <= 127, 'externTypes: selected offset differs')
    value = _ref(contract, _CLAIMS['valueLayoutRef']); value_owners = [t for t in md.types if md.type_full_name(t) == 'IFix.Core.Value']
    _need(value.get('type') == 'IFix.Core.Value' and len(value_owners) == 1 and value_owners[0].bitfield & 1,
          'Value: parent value-type owner differs')
    value_owner = value_owners[0]; offsets = runtime_type_field_offsets(md, image.pe, image.registration, value_owner.index)
    wanted = {'Type': 16, 'Value1': 20, 'Value2': 24}
    _need(value.get('fieldOffsets') == wanted and all(offsets.get(n) == v for n, v in wanted.items()), 'Value: selected slot offsets differ')
    definitions = {md.string(f.name_index): f for f in md.fields_for(value_owner)}
    _need(all(n in definitions and _type(image, definitions[n].type_index) == t for n, t in
              {'Type': 'IFix.Core.ValueType', 'Value1': 'int', 'Value2': 'int'}.items()), 'Value: named field carriers differ')
    for name, kind in {'Type': 0x11, 'Value1': 0x08, 'Value2': 0x08}.items():
        raw = image.pe.bytes_at_va(_type_pointer(image, definitions[name].type_index), 16)
        _need(raw[10] == kind and not int.from_bytes(raw[8:10], 'little') & 0x10,
              'Value: primitive/enum/static field carrier differs')
    return actual


_BLOCKS = {'Ldelem_I': [('label', 'Ldelem_I'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '488bc8',
              ('call', 'nullCheck'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '4c6370048bd6498bcc',
              ('call', 'subtractSlot'),
              '8bd6488bc8',
              ('call', 'subtractSlot'),
              '488bf8488bc8',
              ('call', 'nullCheck'),
              '48635f04498bcf',
              ('call', 'nullCheck'),
              '488bd3498bcf',
              ('call', 'arrayFetch'),
              '488bf0488b9c2410040000488bd3488bcf',
              ('call', 'pointerDifference'),
              '498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'assignmentCheck'),
              '488bd3488bcf',
              ('call', 'pointerDifference'),
              '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
              ('call', 'managedStore'),
              'ba0c000000498bcc',
              ('call', 'subtractSlot'),
              '4c8be048894424584889442460488bcf',
              ('call', 'nullCheck'),
              'c70701000000',
              ('rip', '488b15', 'intPtrArray'),
              '488bce',
              ('call', 'tryArrayType'),
              '488bd8493bc5',
              ('edge', '0f85', 'nativeIntegerSigned'),
              ('rip', '488b15', 'uintPtrArray'),
              '488bce',
              ('call', 'tryArrayType'),
              '488bd8493bc5',
              ('edge', '74', 'slotPcTail'),
              '488bcf',
              ('call', 'nullCheck'),
              '488bcb',
              ('call', 'nullCheck'),
              ('rip', '488b0d', 'uintPtrType'),
              ('call', 'classInitialize'),
              '498bd6488bcb',
              ('call', 'arrayAddress64'),
              '33d2488bc8',
              ('call', 'uintPtrUInt64'),
              ('label', 'nativeIntegerPayloadStore'),
              '48894704'],
 'nativeIntegerSigned': [('label', 'nativeIntegerSigned'),
                         '488bcf',
                         ('call', 'nullCheck'),
                         '488bcb',
                         ('call', 'nullCheck'),
                         '498bd6488bcb',
                         ('call', 'arrayAddress64'),
                         '33d2488bc8',
                         ('call', 'intPtrInt64'),
                         ('edge', 'e9', 'nativeIntegerPayloadStore')],
 'Stelem_Any': [('label', 'Stelem_Any'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '4c8bf88bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '488bc8',
                ('call', 'nullCheck'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '8b7004ba0c000000498bcc',
                ('call', 'subtractSlot'),
                '4c8bf0498bcf',
                ('call', 'nullCheck'),
                '49635f044c8ba42408040000498bcc',
                ('call', 'nullCheck'),
                '488bd3498bcc',
                ('call', 'arrayFetch'),
                ('rip', '488b15', 'arrayType'),
                '488bc8',
                ('call', 'cast'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '33d2488bcb',
                ('call', 'objectGetType'),
                '488bf8488bc8',
                ('call', 'nullCheck'),
                'b939000000488bd7',
                ('call', 'virtualTypeQuery'),
                '4c896c243044886c2428488b8c24f003000048894c24204c8bc84d8bc4498bd6488b8c2410040000',
                ('call', 'toObject'),
                '488bf8488bcb',
                ('call', 'nullCheck'),
                '4533c9448bc6488bd7488bcb',
                ('call', 'arraySet'),
                '488b9c2410040000488bd3498bcf',
                ('call', 'pointerDifference'),
                '498bcc',
                ('call', 'nullCheck'),
                '33d2498bcc',
                ('call', 'assignmentCheck'),
                '488bd3498bcf',
                ('call', 'pointerDifference'),
                '488bc848bfabaaaaaaaaaaaa2a488bc748f7e948d1fa488bc248c1e83f4803d04533c0498bcc',
                ('call', 'managedStore'),
                '488bd3498bce',
                ('call', 'pointerDifference'),
                '498bcc',
                ('call', 'nullCheck'),
                '33d2498bcc',
                ('call', 'assignmentCheck'),
                '498bce',
                ('label', 'valueClear'),
                '488bd3',
                ('call', 'pointerDifference'),
                '488bc8488bc748f7e948d1fa488bc248c1e83f4803d04533c0498bcc',
                ('call', 'managedStore'),
                '4d8be74c897c24584c897c2460',
                ('edge', 'e9', 'slotPcTail')],
 'floatStorePcJoin': [('label', 'floatStorePcJoin'), ('edge', 'e9', 'pcAdvance')],
 'loadPop': [('label', 'loadPop'),
             'be0c0000008bd6498bcc',
             ('call', 'subtractSlot'),
             ('edge', 'e9', 'popTopCommit')],
 'Ldelem_R8': [('label', 'Ldelem_R8'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4863700441be0c000000418bd6498bcc',
               ('call', 'subtractSlot'),
               '418bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'doubleArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bf8488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '418bd6498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               'c70303000000488bcb',
               ('call', 'nullCheck'),
               '488bcf',
               ('call', 'nullCheck'),
               '488bd6488bcf',
               ('call', 'arrayFetchR8'),
               'f20f114304',
               ('label', 'primitiveLoadPcJoin'),
               '418bf6',
               ('edge', 'e9', 'pcAdvance')],
 'lengthStore': [('label', 'lengthStore'),
                 '488bcb',
                 ('call', 'nullCheck'),
                 '897b04',
                 ('edge', 'e9', 'pcAdvance')],
 'Ldlen': [('label', 'Ldlen'),
           '8bd6498bcc',
           ('call', 'subtractSlot'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '48637b04498bcf',
           ('call', 'nullCheck'),
           '488bd7498bcf',
           ('call', 'arrayFetch'),
           ('rip', '488b15', 'arrayType'),
           '488bc8',
           ('call', 'cast'),
           '488bf84c8bb42410040000498bd6488bcb',
           ('call', 'pointerDifference'),
           '498bcf',
           ('call', 'nullCheck'),
           '33d2498bcf',
           ('call', 'assignmentCheck'),
           '498bd6488bcb',
           ('call', 'pointerDifference'),
           '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
           ('call', 'managedStore'),
           '488bcb',
           ('call', 'nullCheck'),
           '44892b488bcf',
           ('call', 'nullCheck'),
           '33d2488bcf',
           ('call', 'arrayLength'),
           '8bf8',
           ('edge', 'e9', 'lengthStore')],
 'Ldelem_I8': [('label', 'Ldelem_I8'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c6370048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               '488bf0488bbc2410040000488bd7488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd7488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               'ba0c000000498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               'c70301000000',
               ('rip', '488b15', 'longArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '75', 'longRead'),
               ('rip', '488b15', 'ulongArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bcf',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch'),
               ('label', 'longStore'),
               '48894304',
               ('edge', 'e9', 'slotPcTail'),
               ('label', 'longRead'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bcf',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch'),
               ('edge', 'eb', 'longStore')],
 'Stelem_Ref': [('label', 'Stelem_Ref'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '4c8bf88bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '488bc8',
                ('call', 'nullCheck'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '4c6370048bd6498bcc',
                ('call', 'subtractSlot'),
                '488bf0498bcf',
                ('call', 'nullCheck'),
                '49635f044c8ba42408040000498bcc',
                ('call', 'nullCheck'),
                '488bd3498bcc',
                ('call', 'arrayFetch'),
                ('rip', '488b15', 'objectArray'),
                '488bc8',
                ('call', 'tryArrayType'),
                '488bf8488bce',
                ('call', 'nullCheck'),
                '833e08',
                ('edge', '0f85', 'badReferenceTag'),
                '488bce',
                ('call', 'nullCheck'),
                '48635e04498bcc',
                ('call', 'nullCheck'),
                '488bd3498bcc',
                ('call', 'arrayFetch'),
                '488bd8488bcf',
                ('call', 'nullCheck'),
                '488bd3488bcf',
                ('call', 'assignmentCheck'),
                '498bd64c8bc3488bcf',
                ('call', 'managedStore'),
                '488b9c2410040000488bd3498bcf',
                ('call', 'pointerDifference'),
                '498bcc',
                ('call', 'nullCheck'),
                '33d2498bcc',
                ('call', 'assignmentCheck'),
                '488bd3498bcf',
                ('call', 'pointerDifference'),
                '488bc848bfabaaaaaaaaaaaa2a488bc748f7e948d1fa488bc248c1e83f4803d04533c0498bcc',
                ('call', 'managedStore'),
                '488bd3488bce',
                ('call', 'pointerDifference'),
                '498bcc',
                ('call', 'nullCheck'),
                '33d2498bcc',
                ('call', 'assignmentCheck'),
                '488bce',
                ('edge', 'e9', 'valueClear')],
 'Ldelem_U1': [('label', 'Ldelem_U1'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c6370048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               '488bf0488bbc2410040000488bd7488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd7488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               'ba0c000000498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b',
               ('rip', '488b15', 'byteArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '75', 'unsignedByteRead'),
               ('label', 'unsignedByteFallback'),
               ('rip', '488b15', 'boolArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch8'),
               '418bfd413ac5400f95c7',
               ('label', 'integerStore'),
               '488bcb',
               ('call', 'nullCheck'),
               '897b04',
               ('edge', 'e9', 'slotPcTail'),
               ('label', 'unsignedByteRead'),
               '488bcf',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch8'),
               '0fb6f8',
               ('label', 'join39'),
               ('edge', 'eb', 'integerStore')],
 'Stelem_R8': [('label', 'Stelem_R8'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               'f20f1070048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '486378048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'doubleArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bd84c8bb42410040000498bd6498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '498bd6498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460488bcb',
               ('call', 'nullCheck'),
               '488bd70f28d6488bcb',
               ('call', 'arrayStoreR8'),
               ('edge', 'e9', 'floatStorePcJoin')],
 'Ldelem_I1': [('label', 'Ldelem_I1'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c6370048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               '488bf0488bbc2410040000488bd7488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd7488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               'ba0c000000498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b',
               ('rip', '488b15', 'sbyteArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '0f84', 'unsignedByteFallback'),
               '488bc8',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch8'),
               '0fbef8',
               ('edge', 'e9', 'join39')],
 'Ldelem_U4': [('label', 'Ldelem_U4'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4863700441be0c000000418bd6498bcc',
               ('call', 'subtractSlot'),
               '418bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'uintArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bf8488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '418bd6498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b488bcf',
               ('call', 'nullCheck'),
               '488bd6488bcf',
               ('call', 'arrayFetch32'),
               ('label', 'integerReadStore'),
               '8bf8488bcb',
               ('call', 'nullCheck'),
               '897b04',
               ('edge', 'e9', 'primitiveLoadPcJoin')],
 'Stelem_I2': [('label', 'Stelem_I2'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '448b70048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '48637004bb0c0000008bd3498bcc',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               '488bf8488b9c2410040000488bd3498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd3498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460',
               ('rip', '488b15', 'shortArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'shortStore'),
               ('rip', '488b15', 'ushortArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'ushortStore'),
               ('rip', '488b15', 'charArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '488bd6450fb7c6488bcb',
               ('call', 'arrayStore16'),
               ('label', 'primitiveStorePcJoin'),
               ('edge', 'e9', 'slotPcTail'),
               ('label', 'ushortStore'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bd6450fb7c6488bcb',
               ('call', 'arrayStore16'),
               ('edge', 'eb', 'primitiveStorePcJoin'),
               ('label', 'shortStore'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bd6450fb7c6488bcb',
               ('call', 'arrayStore16'),
               ('edge', 'eb', 'primitiveStorePcJoin')],
 'Newarr': [('label', 'Newarr'),
            ('field', '488b5f', 'externTypes'),
            '498bce',
            ('call', 'nullCheck'),
            '49637e04488bcb',
            ('call', 'nullCheck'),
            '488bd7488bcb',
            ('call', 'arrayFetch'),
            '488bf0ba0c000000498bcc',
            ('call', 'subtractSlot'),
            '488bd8488b942410040000488bc8',
            ('call', 'pointerDifference'),
            '488bc848b8abaaaaaaaaaaaa2a48f7e9488bfa48d1ff488bc748c1e83f4803f8488bcb',
            ('call', 'nullCheck'),
            '4533c08b5304488bce',
            ('call', 'arrayCreate'),
            '488bf0498bcf',
            ('call', 'nullCheck'),
            '488bd6498bcf',
            ('call', 'assignmentCheck'),
            '4863d74c8bc6498bcf',
            ('call', 'managedStore'),
            '488bcb',
            ('call', 'nullCheck'),
            'c70308000000',
            ('edge', 'e9', 'integerStore')],
 'Ldelem_Any': [('label', 'Ldelem_Any'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '488bf0bb0c0000008bd3498bcc',
                ('call', 'subtractSlot'),
                '488bc8',
                ('call', 'nullCheck'),
                '8bd3498bcc',
                ('call', 'subtractSlot'),
                '8b7804488bce',
                ('call', 'nullCheck'),
                '48635e04498bcf',
                ('call', 'nullCheck'),
                '488bd3498bcf',
                ('call', 'arrayFetch'),
                ('rip', '488b15', 'arrayType'),
                '488bc8',
                ('call', 'cast'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '4533c08bd7488bcb',
                ('call', 'arrayGet'),
                '488bf8488bcb',
                ('call', 'nullCheck'),
                '33d2488bcb',
                ('call', 'objectGetType'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                'b939000000488bd3',
                ('call', 'virtualTypeQuery'),
                '4c896c242848894424204c8bcf4d8bc7488bd6488b8c2410040000',
                ('call', 'pushObject'),
                ('edge', 'e9', 'loadPop')],
 'Stelem_I': [('label', 'Stelem_I'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '488bc8',
              ('call', 'nullCheck'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '4c8b70048bd6498bcc',
              ('call', 'subtractSlot'),
              '8bd6488bc8',
              ('call', 'subtractSlot'),
              '488bc8',
              ('call', 'nullCheck'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '8bd6488bc8',
              ('call', 'subtractSlot'),
              '48637004bb0c0000008bd3498bcc',
              ('call', 'subtractSlot'),
              '8bd3488bc8',
              ('call', 'subtractSlot'),
              '8bd3488bc8',
              ('call', 'subtractSlot'),
              '4c8be04889442458488bc8',
              ('call', 'nullCheck'),
              '49635c2404498bcf',
              ('call', 'nullCheck'),
              '488bd3498bcf',
              ('call', 'arrayFetch'),
              '488bf8488b9c2410040000488bd3498bcc',
              ('call', 'pointerDifference'),
              '498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'assignmentCheck'),
              '488bd3498bcc',
              ('call', 'pointerDifference'),
              '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
              ('call', 'managedStore'),
              '4c89642460',
              ('rip', '488b15', 'intPtrArray'),
              '488bcf',
              ('call', 'tryArrayType'),
              '488bd8493bc5',
              ('edge', '75', 'intPtrStore'),
              ('rip', '488b15', 'uintPtrArray'),
              '488bcf',
              ('call', 'tryArrayType'),
              '488bd8493bc5',
              ('edge', '0f84', 'slotPcTail'),
              '488bc8',
              ('call', 'nullCheck'),
              '4c89ac24880100004533c0498bd6488d8c2488010000',
              ('call', 'uintPtrCtor'),
              '488bbc2488010000488bd6488bcb',
              ('call', 'arrayAddress64'),
              ('label', 'nativeIntegerStore'),
              '488938',
              ('edge', 'e9', 'slotPcTail'),
              ('label', 'intPtrStore'),
              '488bcb',
              ('call', 'nullCheck'),
              '4c89ac24900100004533c0498bd6488d8c2490010000',
              ('call', 'intPtrCtor'),
              '488bbc2490010000488bd6488bcb',
              ('call', 'arrayAddress64'),
              ('edge', 'eb', 'nativeIntegerStore')],
 'Stelem_R4': [('label', 'Stelem_R4'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               'f30f1070048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '486378048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'floatArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bd84c8bb42410040000498bd6498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '498bd6498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460488bcb',
               ('call', 'nullCheck'),
               '488bd70f28d6488bcb',
               ('call', 'arrayStoreR4'),
               ('edge', 'e9', 'floatStorePcJoin')],
 'Stelem_I1': [('label', 'Stelem_I1'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '448b70048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '48637004bb0c0000008bd3498bcc',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               '488bf8488b9c2410040000488bd3498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd3498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460',
               ('rip', '488b15', 'byteArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'sbyteStore'),
               ('rip', '488b15', 'boolArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'boolStore'),
               ('rip', '488b15', 'sbyteArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '488bd6458ac6488bcb',
               ('call', 'arrayStoreBool'),
               ('edge', 'e9', 'primitiveStorePcJoin'),
               ('label', 'boolStore'),
               '488bcb',
               ('call', 'nullCheck'),
               '418bc5453bf50f94c0413bc5410f94c0488bd6488bcb',
               ('call', 'arrayStore8'),
               ('edge', 'e9', 'primitiveStorePcJoin'),
               ('label', 'sbyteStore'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bd6458ac6488bcb',
               ('call', 'arrayStore8'),
               ('edge', 'e9', 'primitiveStorePcJoin')],
 'Ldelem_I2': [('label', 'Ldelem_I2'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c6370048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               '488bf0488bbc2410040000488bd7488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd7488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               'ba0c000000498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b',
               ('rip', '488b15', 'shortArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '75', 'shortRead'),
               ('label', 'ushortFallback'),
               ('rip', '488b15', 'charArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch16'),
               ('label', 'shortExtend'),
               '0fb7f8',
               ('edge', 'e9', 'join39'),
               ('label', 'shortRead'),
               '488bcf',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch16'),
               '0fbff8',
               ('edge', 'e9', 'join39')],
 'Ldelem_R4': [('label', 'Ldelem_R4'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4863700441be0c000000418bd6498bcc',
               ('call', 'subtractSlot'),
               '418bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'floatArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bf8488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '418bd6498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               'c70302000000488bcb',
               ('call', 'nullCheck'),
               '488bcf',
               ('call', 'nullCheck'),
               '488bd6488bcf',
               ('call', 'arrayFetchR4'),
               'f30f114304',
               ('edge', 'e9', 'primitiveLoadPcJoin')],
 'Ldelem_I4': [('label', 'Ldelem_I4'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4863700441be0c000000418bd6498bcc',
               ('call', 'subtractSlot'),
               '418bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               ('rip', '488b15', 'intArray'),
               '488bc8',
               ('call', 'tryArrayType'),
               '488bf8488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488b942410040000488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '418bd6498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b488bcf',
               ('call', 'nullCheck'),
               '488bd6488bcf',
               ('call', 'arrayFetch32'),
               ('edge', 'e9', 'integerReadStore')],
 'Ldelem_Ref': [('label', 'Ldelem_Ref'),
                '8bd6498bcc',
                ('call', 'subtractSlot'),
                '8bd6488bc8',
                ('call', 'subtractSlot'),
                '488bf0bb0c0000008bd3498bcc',
                ('call', 'subtractSlot'),
                '488bc8',
                ('call', 'nullCheck'),
                '8bd3498bcc',
                ('call', 'subtractSlot'),
                '4c637004488b942410040000488bce',
                ('call', 'pointerDifference'),
                '488bc848b8abaaaaaaaaaaaa2a48f7e9488bfa48d1ff488bc748c1e83f4803f8488bce',
                ('call', 'nullCheck'),
                '48635e04498bcf',
                ('call', 'nullCheck'),
                '488bd3498bcf',
                ('call', 'arrayFetch'),
                ('rip', '488b15', 'objectArray'),
                '488bc8',
                ('call', 'tryArrayType'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '498bd6488bcb',
                ('call', 'arrayFetch'),
                '488bd8498bcf',
                ('call', 'nullCheck'),
                '488bd3498bcf',
                ('call', 'assignmentCheck'),
                '4c8bc3488bd7498bcf',
                ('call', 'managedStore'),
                '488bce',
                ('call', 'nullCheck'),
                '897e04',
                ('edge', 'e9', 'loadPop')],
 'Ldelem_U2': [('label', 'Ldelem_U2'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c6370048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '48637b04498bcf',
               ('call', 'nullCheck'),
               '488bd7498bcf',
               ('call', 'arrayFetch'),
               '488bf0488bbc2410040000488bd7488bcb',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd7488bcb',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               'ba0c000000498bcc',
               ('call', 'subtractSlot'),
               '4c8be048894424584889442460488bcb',
               ('call', 'nullCheck'),
               '44892b',
               ('rip', '488b15', 'ushortArray'),
               '488bce',
               ('call', 'tryArrayType'),
               '488bf8493bc5',
               ('edge', '0f84', 'ushortFallback'),
               '488bc8',
               ('call', 'nullCheck'),
               '498bd6488bcf',
               ('call', 'arrayFetch16'),
               ('edge', 'e9', 'shortExtend')],
 'Stelem_I4': [('label', 'Stelem_I4'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '448b70048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '48637004bb0c0000008bd3498bcc',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               '488bf8488b9c2410040000488bd3498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd3498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460',
               ('rip', '488b15', 'intArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'int32Store'),
               ('rip', '488b15', 'uintArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '488bd6458bc6488bcb',
               ('call', 'arrayStore32'),
               ('edge', 'e9', 'primitiveStorePcJoin'),
               ('label', 'int32Store'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bd6458bc6488bcb',
               ('call', 'arrayStore32'),
               ('edge', 'e9', 'primitiveStorePcJoin')],
 'Stelem_I8': [('label', 'Stelem_I8'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '4c8b70048bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '488bc8',
               ('call', 'nullCheck'),
               '8bd6498bcc',
               ('call', 'subtractSlot'),
               '8bd6488bc8',
               ('call', 'subtractSlot'),
               '48637004bb0c0000008bd3498bcc',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '8bd3488bc8',
               ('call', 'subtractSlot'),
               '4c8be04889442458488bc8',
               ('call', 'nullCheck'),
               '49635c2404498bcf',
               ('call', 'nullCheck'),
               '488bd3498bcf',
               ('call', 'arrayFetch'),
               '488bf8488b9c2410040000488bd3498bcc',
               ('call', 'pointerDifference'),
               '498bcf',
               ('call', 'nullCheck'),
               '33d2498bcf',
               ('call', 'assignmentCheck'),
               '488bd3498bcc',
               ('call', 'pointerDifference'),
               '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
               ('call', 'managedStore'),
               '4c89642460',
               ('rip', '488b15', 'longArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '75', 'int64Store'),
               ('rip', '488b15', 'ulongArray'),
               '488bcf',
               ('call', 'tryArrayType'),
               '488bd8493bc5',
               ('edge', '0f84', 'slotPcTail'),
               '488bc8',
               ('call', 'nullCheck'),
               '488bd64d8bc6488bcb',
               ('call', 'arrayStore64'),
               ('edge', 'e9', 'primitiveStorePcJoin'),
               ('label', 'int64Store'),
               '488bcb',
               ('call', 'nullCheck'),
               '488bd64d8bc6488bcb',
               ('call', 'arrayStore64'),
               ('edge', 'e9', 'primitiveStorePcJoin')]}



def _token_size(token: Any) -> int:
    if isinstance(token, str): return len(bytes.fromhex(token))
    kind, *args = token
    if kind == 'label': return 0
    if kind == 'call': return 5
    if kind == 'rip': return len(bytes.fromhex(args[0])) + 4
    if kind == 'field': return len(bytes.fromhex(args[0])) + 1
    if kind == 'edge': return len(bytes.fromhex(args[0])) + (1 if len(args[0]) == 2 and args[0] != 'e9' else 4)
    _need(False, 'unknown finite token')


def _label_map(windows: dict[str, dict]) -> dict[str, int]:
    result = {}
    for name, tokens in _BLOCKS.items():
        at = _rva(windows[name]['rva'])
        for token in tokens:
            if not isinstance(token, str) and token[0] == 'label':
                _need(token[1] not in result, 'duplicate finite label'); result[token[1]] = at
            at += _token_size(token)
        _need(at - _rva(windows[name]['rva']) == windows[name]['byteCount'], name + ': finite window size differs')
    return result


def _program(tokens: Any, at: int, targets: dict[str, int], cells: dict[str, int], field_offset: int) -> bytes:
    p = _Program(at)
    for token in tokens:
        if isinstance(token, str): p.add(token); continue
        kind, *args = token
        if kind == 'label': continue
        if kind == 'call': p.call(targets[args[0]])
        elif kind == 'rip': p.rip(args[0], cells[args[1]])
        elif kind == 'field': p.add(args[0]); p.byte(field_offset)
        elif kind == 'edge':
            prefix = bytes.fromhex(args[0]); width = 1 if len(prefix) == 1 and prefix != b'\xe9' else 4
            d = targets[args[1]] - at - len(p.raw) - len(prefix) - width
            _need(-(1 << (width * 8 - 1)) <= d < (1 << (width * 8 - 1)), 'finite edge outside encoded width')
            p.add(prefix + d.to_bytes(width, 'little', signed=True))
        else: _need(False, 'unknown finite program token')
    return p.finish()


_ACCESS = {
    'arrayFetch': ('jae', '488b44d120'), 'arrayFetch32': ('jae', '8b449120'),
    'arrayFetch8': ('jae', '0fb6440a20'), 'arrayFetch16': ('jae', '0fb7445120'),
    'arrayFetchR4': ('jae', 'f30f10449120'), 'arrayFetchR8': ('jae', 'f20f1044d120'),
    'arrayStore8': ('jae', '4488440a20'), 'arrayStore16': ('jae', '664489445120'),
    'arrayStore32': ('jae', '4489449120'), 'arrayStore64': ('jae', '4c8944d120'),
    'arrayStoreR4': ('jae', 'f30f11549120'), 'arrayStoreR8': ('jae', 'f20f1154d120'),
    'arrayStoreBool': ('jb', '4488440a20'), 'arrayAddress64': ('jb', '488d4204488d04c1'),
}


def _access_program(name: str, at: int, bounds: int) -> bytes:
    branch, access = _ACCESS[name]; p = _Program(at); p.add('4883ec283b5118')
    if branch == 'jae':
        p.branch(0x73, 'failure'); p.add(access + '4883c428c3'); p.mark('failure'); p.call(bounds); p.add('cc')
    else:
        p.branch(0x72, 'access'); p.call(bounds); p.add('cc'); p.mark('access'); p.add(access + '4883c428c3')
    return p.finish()


def validate_array_rules(image: Any, spec: dict, body: bytes, body_rva: int, opcode_ids: dict[str, int],
                         contract: dict, extents: dict[int, int]) -> dict:
    """Validate an authenticated image after parent prerequisite groups."""
    _need(all(spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    rows = {r.get('opcode'): r for r in spec['rules']}
    _need(len(rows) == len(spec['rules']) and set(rows) == set(_RULES), 'rules: missing/duplicate/unknown declarations')
    for name, (meaning, effect, delta) in _RULES.items():
        _need((rows[name].get('operandMeaning'), rows[name].get('effect'), rows[name].get('stackDeltaSlots')) ==
              (meaning, effect, delta), name + ': unsupported effect')
    members = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.Code')}
    _need(members == opcode_ids and all(n in members for n in _RULES), 'Code: selected enum differs')
    tags = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.ValueType')}
    _need(all(tags.get(n) == v for n, v in _CLAIMS['tagMembers'].items()), 'ValueType: selected tags differ')
    field_offset = _layouts(image, spec, contract); targets = {}
    for name, path in {**_HELPER_REFS, **_TAIL_REFS}.items():
        row = _ref(contract, path); at = _rva(row['rva']); count = row['byteCount']
        raw = _slice(body, body_rva, at, count, name) if name in _TAIL_REFS else image.pe.bytes_at_va(image.pe.image_base + at, count)
        _hash(raw, row, name); targets[name] = at
    helper_rows = _named(spec['helpers'], _HELPERS, 'helpers')
    for name, row in helper_rows.items():
        at = _rva(row['rva']); count = row['byteCount']
        _need(type(count) is int and 0 < count <= 65536, name + ': invalid helper window size')
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, name); targets[name] = at
    methods = _named(spec['methods'], set(_METHODS) - set(_METHOD_REFS), 'methods')
    for name, identity in _METHODS.items():
        row = methods[name] if name in methods else _ref(contract, _METHOD_REFS[name])
        # Existing entry windows were already owned/authenticated by the parent.
        declaration = dict(row)
        if 'byteCount' in declaration: declaration.setdefault('bodyBoundary', 'entry-window-callee-outcome-unresolved')
        if name in methods:
            _need(row.get('returnType') == identity[3] and row.get('parameterTypes') == identity[2], name + ': declared signature differs')
            _own_signature(image, row, identity)
        targets[name] = _identity(image, declaration, identity, name, extents)
    _identity(image, spec['elementType'], _VIRTUAL, 'elementType', extents, virtual_slot=57, body_required=False)
    _need(spec['elementType'].get('returnType') == 'System.Type', 'elementType: declared return differs')
    cells = {}
    for name, row in _named(spec['usageCells'], _CELLS, 'usageCells').items():
        _cell_type(image, row, _CELLS[name]); cells[name] = _rva(row['cellRva'])
    inherited = _ref(contract, _CLAIMS['usageRefs']['arrayType'])
    _cell_type(image, dict(inherited, usageTag=1), 'System.Array'); cells['arrayType'] = _rva(inherited['cellRva'])
    for name in _ACCESS:
        expected = _access_program(name, targets[name], targets['boundsFailure'])
        _expect(image.pe.bytes_at_va(image.pe.image_base + targets[name], len(expected)), expected, 'array.' + name + '.finite-width-and-bounds')
    for name, shape in {'subtractSlot': '4863c2482bc8488bc1c3', 'pointerDifference': '482bca488bc1c3',
                        'intPtrCtor': '488911c3', 'intPtrInt64': '6690488b01c3', 'uintPtrUInt64': '488b01c3'}.items():
        expected = bytes.fromhex(shape)
        _expect(image.pe.bytes_at_va(image.pe.image_base + targets[name], len(expected)), expected, 'array.' + name + '.finite-payload')
    p = _Program(targets['tryArrayType']); p.rip('e9', targets['tryTypeRuntime'])
    _expect(image.pe.bytes_at_va(image.pe.image_base + targets['tryArrayType'], len(p.raw)), p.finish(), 'array.type-predicate-trampoline')
    # Prove the inherited managed-store prefix's bounds and raw reference write;
    # the GC/barrier continuation is explicitly outside this recipe.
    p = _Program(targets['managedStore']); p.add('4883ec283b5118735d'); p.rip('833d', _rva(spec['managedStoreBarrierFlagRva']), b'\0')
    p.add('4c8944d120744a')
    _expect(image.pe.bytes_at_va(image.pe.image_base + targets['managedStore'], len(p.raw)), p.finish(), 'array.managedStore.guarded-write-prefix')
    # The shared query dispatcher can have fast paths; only its common prefix is
    # used to identify the slot pair and hidden MethodInfo, never its outcome.
    query = _ref(contract, _HELPER_REFS['virtualTypeQuery']); at = _rva(query['vtableProgramRva'])
    prefix = bytes.fromhex('488d431448c1e0044803074c8b00488b5008')
    _expect(image.pe.bytes_at_va(image.pe.image_base + at, len(prefix)), prefix,
            'array.virtual-query.slot-prefix')
    for name, shape in {'zeroRegister': '4533ed', 'slotWidth': 'be0c000000', 'slotPcTail': 'be0c000000',
                        }.items():
        _expect(_slice(body, body_rva, targets[name], len(bytes.fromhex(shape)), name), bytes.fromhex(shape), 'array.' + name)
    p = _Program(targets['loopState']); p.add('488b9c2410040000498bce'); p.call(targets['nullCheck']); p.add('418b0e894c2470')
    _expect(_slice(body, body_rva, targets['loopState'], len(p.raw), 'loopState'), p.finish(), 'array.loop-state')
    p = _Program(targets['popTopCommit']); p.add('4c8be048894424584889442460'); p.rip('e9', targets['pcAdvance'])
    _expect(_slice(body, body_rva, targets['popTopCommit'], len(p.raw), 'popTopCommit'), p.finish(), 'array.pop-top-join')
    boundary = spec['badReferenceTag']; targets['badReferenceTag'] = _rva(boundary['rva'])
    _need(boundary.get('evidenceBoundary') == 'unresolved' and boundary.get('byteCount') == 12,
          'other-tag exception boundary differs')
    _hash(_slice(body, body_rva, targets['badReferenceTag'], boundary['byteCount'], 'badReferenceTag'), boundary, 'badReferenceTag')
    windows = _named(spec['executeWindows'], _BLOCKS, 'executeWindows'); labels = _label_map(windows); targets.update(labels)
    # Overlapping declarations could otherwise let an edge witness be read from
    # a different native range than its named body.
    spans = sorted((_rva(r['rva']), _rva(r['rva']) + r['byteCount']) for r in windows.values())
    _need(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), 'overlapping finite execute windows')
    for name, row in windows.items():
        at = _rva(row['rva']); raw = _slice(body, body_rva, at, row['byteCount'], name); _hash(raw, row, name)
        _expect(raw, _program(_BLOCKS[name], at, targets, cells, field_offset), 'array.' + name + '.full-finite-caller')
    dispatch = contract['dispatchRules']; entry_set = {_rva(r['entryRva']) for r in dispatch['entryPoints']}
    for name, row in rows.items():
        selected = resolve_selected_dispatch_entry(body, body_rva, _rva(contract['basicOpcodeRules']['dispatchStartRva']), opcode_ids[name],
            zero_compare_rva=_rva(dispatch['extensions']['zeroCompare']['rva']), sub_esi_rva=_rva(dispatch['extensions']['subEsi']['rva']), entry_rvas=entry_set)
        _need(row.get('opcodeId') == opcode_ids[name] and selected == _rva(row['entryRva']) == labels[name], name + ': selected entry differs')
    return {'status': 'validated_conditional_array_recipes', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'rules': [{k: row[k] for k in ('opcode', 'operandMeaning', 'effect', 'stackDeltaSlots')} for row in spec['rules']],
            'entryRvas': {n: hex(labels[n]) for n in _RULES},
            'unresolved': ['runtime-array-shape-bounds-types-and-values', 'runtime-overlap-and-helper-mutation',
                'type-predicate-and-Type-virtual-implementation', 'reflection-allocation-and-Array-API-outcomes',
                'ToObject-and-PushObject-callee-outcomes', 'UIntPtr-constructor-outcome', 'GC-and-write-barrier-state',
                'Stelem_Ref-other-tag-exception-route-outcome', 'actual-execution']}


def project_array_rules(decoded: dict, spec: dict) -> list[dict]:
    """Project authored occurrences after native validation, without stack values."""
    _need(all(spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    rows = {r.get('opcode'): r for r in spec['rules']}
    _need(len(rows) == len(spec['rules']) and set(rows) == set(_RULES), 'rules: missing/duplicate/unknown declarations')
    for name, recipe in _RULES.items():
        row = rows[name]
        _need((row.get('operandMeaning'), row.get('effect'), row.get('stackDeltaSlots')) == recipe, name + ': unsupported effect')
    result = []
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name = instruction['name']
            if name not in rows: continue
            row = rows[name]; operand = instruction['operandUnsigned']
            _need(type(operand) is int and 0 <= operand <= 0xffffffff and instruction['opcode'] == row['opcodeId'],
                  name + ': malformed operand/opcode')
            signed = operand if operand < 0x80000000 else operand - 0x100000000
            _need('operandSigned' not in instruction or type(instruction['operandSigned']) is int and instruction['operandSigned'] == signed,
                  name + ': inconsistent signed operand')
            out = {'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'], 'offset': instruction['offset'],
                   'opcode': name, 'operandUnsigned': operand, 'operandSigned': signed, 'operandMeaning': row['operandMeaning'],
                   'operandConsumedByThisOpcode': name == 'Newarr', 'effect': row['effect'], 'stackDeltaSlots': row['stackDeltaSlots'],
                   'stackDeltaBoundary': 'modeled-normal-return-array-route;other-tag-exception-path-unresolved',
                   'normalNextInstructionDelta': 1, 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
                   **{k: spec[k] for k in ('storageBoundary', 'aliasBoundary', 'typeSelectionBoundary', 'virtualBoundary',
                                          'exceptionBoundary', 'calleeBoundary', 'fileTableJoinBoundary')}}
            if name == 'Newarr':
                out.update(externTypeIndex=signed, externTypeSelectionBoundary='runtime-externTypes-row-validity-and-Type-unobserved')
            result.append(out)
    return result


def validate_selected_array_rules(contract: dict, *, gameassembly: Path, metadata: Path, spec: dict | None = None) -> dict:
    """Fail closed before opening anything except the explicit selected pair."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'nativeInputs: selected hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.arrays'); extents = image.mapper.pdata_function_extents(image.pe)
    consumer = dict(contract['consumer'], parameterTypes=_EXECUTE_TYPES); at = _parent_method(image, consumer, extents)
    body = image.pe.bytes_at_va(image.pe.image_base + at, consumer['bodyBytes'])
    ids = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.Code')}
    return validate_array_rules(image, contract['arrayRules'] if spec is None else spec, body, at, ids, contract, extents)
