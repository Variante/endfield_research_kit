"""Authenticate the VM's conditional array-reference getter/setter recipes.

Both helpers try int, float, double, byte, bool, long, ulong, sbyte, short,
ushort, char and uint array cells in exactly that order. Each request passes
the original object to the inherited opaque type predicate; the first nonnull
return chooses a native fast path. The full finite programs authenticate this
selection, initialization requests and every null/bounds/return join. Runtime
predicate results and whether an object is a valid array remain unobserved.

The getter's primitive paths set Integer/Float/Double/Long and store the raw
width at Value1; signed byte/short loads extend their sign, unsigned byte/word
loads extend zero, and Boolean loads normalize any nonzero byte to one. The
getter sets the result tag before the unsigned Int32 index bounds check. It
does not clear or write managedStack on these primitive paths. Its remaining
route requests two Array casts, Array.GetValue(index), GetType on the original
object and the named GetElementType virtual slot, then inherited PushObject
with the incoming base, value pointer, managed array and returned value/type.

The setter reads the incoming payload without consulting its Type and writes
only the selected array element's width. Boolean stores normalize a nonzero
Int32; byte/word stores keep the low width, floating stores retain raw payload.
Primitive stores do not clear or write the managed stack or mutate the Value
descriptor. The fallback requests GetType/GetElementType, then ToObject with
the incoming base, value pointer, managed array, returned Type, this VM and
clone=true. Only afterward does it request two Array casts and SetValue with
the converted replacement and the original index. This differs from ordinary
Stelem_Any's clone=false request. Callee outcomes are inherited or unresolved.

The index is sign-extended before addressing, while native bounds comparisons
use its low unsigned Int32 against array+0x18. Valid stable storage and normal
helper returns without unmodelled mutation are required for the target/read
expressions. Runtime aliases, bounds, input tags/values, reflection/cast/type
selection, allocation/GC and actual execution are unobserved. Type and method
catalogs are reused from the ordinary array/parent groups; only these two named
VM bodies and their per-method initialization flag sites are declared here.
Native addresses/hashes stay in reviewed JSON, not this algorithm module.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_name
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _identity
from scripts.game_data.ifix_vm_reference_update_rules import _ref, _rva, _hash, _expect, _type, _type_pointer
from scripts.game_data.ifix_vm_array_rules import _cell_type, _layouts, _METHODS as _ARRAY_METHODS, _VIRTUAL


class ArrayReferenceRuleError(ValueError):
    """An array-reference helper lacks its selected native witness."""


_SIGNATURE = ['object', 'int', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*']
_METHODS = {name: ('IFix.Core.VirtualMachine', name, _SIGNATURE, 'void', False) for name in ('arrayGet', 'arraySet')}
_METHOD_REFS = {
    'arrayGetValue': 'chainFieldRules.methods.arrayGet', 'arraySetValue': 'referenceUpdateRules.methods.arraySet',
    'objectGetType': 'functionPointerRules.helpers.objectGetType', 'pushObject': 'initobjStackEffect.pushObjectMethod',
    'toObject': 'constrainedTypeOperand.stackEffect.toObjectMethod',
}
_HELPER_REFS = {
    'tryTypeRuntime': 'arrayRules.helpers.tryTypeRuntime', 'cast': 'referenceUpdateRules.helpers.cast',
    'virtualTypeQuery': 'genericDelegateFactoryRules.helpers.returnQueryHelper',
    'typeInitialize': 'referenceUpdateRules.helpers.typeInitialize', 'boundsFailure': 'referenceUpdateRules.helpers.boundsFailure',
    'nullFailure': 'referenceUpdateRules.helpers.nullFailure',
}
_SELECTION = ('intArray', 'floatArray', 'doubleArray', 'byteArray', 'boolArray', 'longArray', 'ulongArray',
              'sbyteArray', 'shortArray', 'ushortArray', 'charArray', 'uintArray')
_USAGE_REFS = {n: 'arrayRules.usageCells.' + n for n in _SELECTION}
_USAGE_REFS['arrayType'] = 'referenceUpdateRules.usageCells.arrayType'
_CLAIMS = {
    'schema': 'endfield.ifix-vm-array-reference-rules.v1', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'methodRefs': _METHOD_REFS, 'helperRefs': _HELPER_REFS, 'usageRefs': _USAGE_REFS,
    'valueLayoutRef': 'constrainedTypeOperand.stackEffect.valueLayout', 'elementTypeRef': 'arrayRules.elementType',
    'selectionOrder': list(_SELECTION), 'selectionBoundary': 'typed-cells-and-first-nonnull-runtime-predicate-result-unobserved',
    'getterRecipe': 'primitive-width-tag-store-or-Array.GetValue-GetType-GetElementType-PushObject-fallback',
    'setterRecipe': 'primitive-width-store-without-tag-read-or-GetType-GetElementType-ToObject-clone-true-Array.SetValue-fallback',
    'primitiveManagedEffect': 'no-managedStack-clear-or-write',
    'storageBoundary': 'valid-stable-storage-and-normal-helper-returns-without-unmodelled-mutation',
    'aliasBoundary': 'actual-overlap-helper-mutation-and-runtime-values-unobserved',
    'calleeBoundary': 'inherited-runtime-callee-outcomes-and-Type-implementation-unresolved',
    'exceptionBoundary': 'authenticated-null-and-unsigned-bounds-request-exits;runtime-outcomes-unobserved',
    'tagMembers': {'Integer': 0, 'Long': 1, 'Float': 2, 'Double': 3},
}


def _need(ok: bool, label: str) -> None:
    if not ok: raise ArrayReferenceRuleError('ifix-array-reference.' + label)


def _signature(image: Any, row: dict) -> None:
    md = image.metadata
    selected = [m for t in md.types if md.type_full_name(t) == 'IFix.Core.VirtualMachine' for m in md.methods_for(t)
                if md.string(m.name_index) == row['method'] and m.parameter_count == 5
                and [_type(image, p.type_index) for p in md.parameters_for(m)] == _SIGNATURE]
    _need(len(selected) == 1, 'method: one named overload required'); method = selected[0]
    indexes = [p.type_index for p in md.parameters_for(method)] + [method.return_type]
    for n, (index, kind) in enumerate(zip(indexes, (0x1c, 0x08, 0x0f, 0x1d, 0x0f, 0x01))):
        raw = image.pe.bytes_at_va(_type_pointer(image, index), 16)
        _need(len(raw) == 16 and raw[10] == kind and not raw[11] & 0x20, 'method: primitive/pointer/array/by-reference carrier differs')
        if n in (2, 3, 4):
            element = int.from_bytes(raw[:8], 'little'); carrier = image.pe.bytes_at_va(element, 16)
            _need(len(carrier) == 16 and carrier[10] == (0x1c if n == 3 else 0x11) and not carrier[11] & 0x20,
                  'method: nested pointer/array/by-reference carrier differs')
            _need(runtime_type_name(image.pe, md, element) == ('object' if n == 3 else 'IFix.Core.Value'), 'method: nested named carrier differs')


_PROGRAMS = {'arrayGet': ['48895c240848896c24104889742418574883ec3033ff4963f0',
              ('rip', '40383d', 'flag', ''),
              '498bd9488bea',
              ('edge', '0f85', 'select'),
              ('rip', '488d0d', 'boolArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'byteArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'charArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'doubleArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'shortArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'intArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'longArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'arrayType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'sbyteArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'floatArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'ushortArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'uintArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'ulongArray', ''),
              ('call', 'typeInitialize'),
              ('rip', 'c605', 'flag', '01'),
              ('label', 'select'),
              ('rip', '488b15', 'intArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'intGuard'),
              ('rip', '488b15', 'floatArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'floatTag'),
              ('rip', '488b15', 'doubleArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'doubleTag'),
              ('rip', '488b15', 'byteArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'unsignedByte'),
              ('rip', '488b15', 'boolArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'boolRead'),
              ('rip', '488b15', 'longArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'longTag'),
              ('rip', '488b15', 'ulongArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'longTag'),
              ('rip', '488b15', 'sbyteArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'signedByte'),
              ('rip', '488b15', 'shortArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'signedWord'),
              ('rip', '488b15', 'ushortArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'unsignedWord'),
              ('rip', '488b15', 'charArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'unsignedWord'),
              ('rip', '488b15', 'uintArray', ''),
              '488bcd',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'intGuard'),
              ('rip', '488b15', 'arrayType', ''),
              '488bcd',
              ('call', 'cast'),
              '4885c0',
              ('edge', '0f84', 'nullExit'),
              ('rip', '488b15', 'arrayType', ''),
              '488bcd',
              ('call', 'cast'),
              '488bc84533c08bd6',
              ('call', 'arrayGetValue'),
              '488bf04885ed',
              ('edge', '0f84', 'nullExit'),
              '33d2488bcd',
              ('call', 'objectGetType'),
              '4885c0',
              ('edge', '0f84', 'nullExit'),
              'b939000000488bd0',
              ('call', 'virtualTypeQuery'),
              '4c8b4424604c8bce488b4c2468488bd348897c24284889442420',
              ('call', 'pushObject'),
              ('edge', 'eb', 'return'),
              ('label', 'intRead'),
              '893b',
              ('label', 'intReadBounds'),
              '3b7018',
              ('edge', '0f83', 'boundsExit'),
              '8b4cb020',
              ('label', 'intStore'),
              '894b04',
              ('label', 'return'),
              '488b5c2440488b6c2448488b7424504883c4305fc3',
              ('label', 'unsignedWord'),
              '4885db',
              ('edge', '0f84', 'nullExit'),
              '893b3b7018',
              ('edge', '0f83', 'boundsExit'),
              '0fb74c7020',
              ('edge', 'eb', 'intStore'),
              ('label', 'signedWord'),
              '4885db',
              ('edge', '0f84', 'nullExit'),
              '893b3b7018',
              ('edge', '0f83', 'boundsExit'),
              '0fbf4c7020',
              ('edge', 'eb', 'intStore'),
              ('label', 'signedByte'),
              '4885db',
              ('edge', '0f84', 'nullExit'),
              '893b3b7018',
              ('edge', '0f83', 'boundsExit'),
              '0fbe4c0620',
              ('edge', 'eb', 'intStore'),
              ('label', 'longTag'),
              '4885db',
              ('edge', '74', 'nullExit'),
              'c70301000000',
              ('edge', 'eb', 'wideBounds'),
              ('label', 'boolRead'),
              '4885db',
              ('edge', '74', 'nullExit'),
              '893b3b7018',
              ('edge', '73', 'boundsExit'),
              '40387c0620400f95c7897b04',
              ('edge', 'e9', 'return'),
              ('label', 'unsignedByte'),
              '4885db',
              ('edge', '74', 'nullExit'),
              '893b3b7018',
              ('edge', '73', 'boundsExit'),
              '0fb64c0620',
              ('edge', 'e9', 'intStore'),
              ('label', 'doubleTag'),
              '4885db',
              ('edge', '74', 'nullExit'),
              'c70303000000',
              ('label', 'wideBounds'),
              '3b7018',
              ('edge', '73', 'boundsExit'),
              '488b4cf02048894b04',
              ('edge', 'e9', 'return'),
              ('label', 'floatTag'),
              '4885db',
              ('edge', '74', 'nullExit'),
              'c70302000000',
              ('edge', 'e9', 'intReadBounds'),
              ('label', 'intGuard'),
              '4885db',
              ('edge', '0f85', 'intRead'),
              ('label', 'nullExit'),
              ('call', 'nullFailure'),
              'cc',
              ('label', 'boundsExit'),
              ('call', 'boundsFailure'),
              'cc'],
 'arraySet': ['48895c240848896c24104889742418574883ec40',
              ('rip', '803d', 'flag', '00'),
              '498bf94963d8488bf2488be9',
              ('edge', '0f85', 'select'),
              ('rip', '488d0d', 'boolArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'byteArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'charArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'doubleArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'shortArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'intArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'longArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'arrayType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'sbyteArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'floatArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'ushortArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'uintArray', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'ulongArray', ''),
              ('call', 'typeInitialize'),
              ('rip', 'c605', 'flag', '01'),
              ('label', 'select'),
              ('rip', '488b15', 'intArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'intGuard'),
              ('rip', '488b15', 'floatArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'floatWrite'),
              ('rip', '488b15', 'doubleArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'doubleWrite'),
              ('rip', '488b15', 'byteArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'byteRead'),
              ('rip', '488b15', 'boolArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'boolRead'),
              ('rip', '488b15', 'longArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'wideWrite'),
              ('rip', '488b15', 'ulongArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'wideWrite'),
              ('rip', '488b15', 'sbyteArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'byteRead'),
              ('rip', '488b15', 'shortArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'wordWrite'),
              ('rip', '488b15', 'ushortArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'wordWrite'),
              ('rip', '488b15', 'charArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'wordWrite'),
              ('rip', '488b15', 'uintArray', ''),
              '488bce',
              ('call', 'tryTypeRuntime'),
              '4885c0',
              ('edge', '0f85', 'intGuard'),
              '4885f6',
              ('edge', '0f84', 'nullExit'),
              '33d2488bce',
              ('call', 'objectGetType'),
              '4885c0',
              ('edge', '0f84', 'nullExit'),
              'b939000000488bd0',
              ('call', 'virtualTypeQuery'),
              '4883642430004c8bc84c8b442470488bd7488b4c2478c64424280148896c2420',
              ('call', 'toObject'),
              ('rip', '488b15', 'arrayType', ''),
              '488bce488bf8',
              ('call', 'cast'),
              '4885c0',
              ('edge', '0f84', 'nullExit'),
              ('rip', '488b15', 'arrayType', ''),
              '488bce',
              ('call', 'cast'),
              '488bc84533c9448bc3488bd7',
              ('call', 'arraySetValue'),
              ('edge', 'eb', 'return'),
              ('label', 'intRead'),
              '8b57043b5818',
              ('edge', '0f83', 'boundsExit'),
              '89549820',
              ('label', 'return'),
              '488b5c2450488b6c2458488b7424604883c4405fc3',
              ('label', 'wordWrite'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              '8b57043b5818',
              ('edge', '73', 'boundsExit'),
              '6689545820',
              ('edge', 'eb', 'return'),
              ('label', 'wideWrite'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              '488b57043b5818',
              ('edge', '73', 'boundsExit'),
              '488954d820',
              ('edge', 'eb', 'return'),
              ('label', 'boolRead'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              '837f04000f95c2',
              ('edge', 'eb', 'byteWrite'),
              ('label', 'byteRead'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              '8b5704',
              ('label', 'byteWrite'),
              '3b5818',
              ('edge', '73', 'boundsExit'),
              '88540320',
              ('edge', 'eb', 'return'),
              ('label', 'doubleWrite'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              'f20f1047043b5818',
              ('edge', '73', 'boundsExit'),
              'f20f1144d820',
              ('edge', 'eb', 'return'),
              ('label', 'floatWrite'),
              '4885ff',
              ('edge', '74', 'nullExit'),
              'f30f1047043b5818',
              ('edge', '73', 'boundsExit'),
              'f30f11449820',
              ('edge', 'e9', 'return'),
              ('label', 'intGuard'),
              '4885ff',
              ('edge', '0f85', 'intRead'),
              ('label', 'nullExit'),
              ('call', 'nullFailure'),
              'cc',
              ('label', 'boundsExit'),
              ('call', 'boundsFailure'),
              'cc']}



def _program(base: int, tokens: Any, targets: dict[str, int], cells: dict[str, int], flag: int) -> bytes:
    p = _Program(base); labels = {}; fixups = []
    for token in tokens:
        if isinstance(token, str): p.add(token); continue
        kind, *args = token
        if kind == 'label':
            _need(args[0] not in labels, 'duplicate finite label'); labels[args[0]] = len(p.raw)
        elif kind == 'call': p.call(targets[args[0]])
        elif kind == 'rip': p.rip(args[0], flag if args[1] == 'flag' else cells[args[1]], bytes.fromhex(args[2]))
        elif kind == 'edge':
            prefix = bytes.fromhex(args[0]); width = 1 if len(prefix) == 1 and prefix != b'\xe9' else 4
            p.add(prefix); fixups.append((len(p.raw), width, args[1])); p.add(bytes(width))
        else: _need(False, 'unknown finite program token')
    for at, width, label in fixups:
        _need(label in labels, 'missing finite label'); delta = labels[label] - at - width
        _need(-(1 << (width * 8 - 1)) <= delta < (1 << (width * 8 - 1)), 'finite edge outside encoded width')
        p.raw[at:at + width] = delta.to_bytes(width, 'little', signed=True)
    return p.finish()


def validate_array_reference_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Validate the gated selected image; parent owns prerequisite group proofs."""
    _need(all(spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    _need(set(spec['methods']) == set(_METHODS) and set(spec['initializationFlags']) == set(_METHODS), 'method/initialization declaration set differs')
    tags = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.ValueType')}
    _need(all(tags.get(n) == v for n, v in _CLAIMS['tagMembers'].items()), 'ValueType: selected tags differ')
    _layouts(image, contract['arrayRules'], contract)
    targets = {}; bodies = {}
    for name, identity in _METHODS.items():
        row = spec['methods'][name]
        _need(row.get('parameterTypes') == _SIGNATURE and row.get('returnType') == 'void', 'method: declared signature differs')
        _signature(image, row); targets[name] = _identity(image, row, identity, name, extents)
        bodies[name] = image.pe.bytes_at_va(image.pe.image_base + targets[name], row['bodyBytes'])
    for name, path in _HELPER_REFS.items():
        row = _ref(contract, path); at = _rva(row['rva'])
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, row['byteCount']), row, name); targets[name] = at
    for name, path in _METHOD_REFS.items():
        row = dict(_ref(contract, path))
        if 'byteCount' in row: row.setdefault('bodyBoundary', 'entry-window-callee-outcome-unresolved')
        identity = _ARRAY_METHODS[{'arrayGetValue': 'arrayGet', 'arraySetValue': 'arraySet'}.get(name, name)]
        targets[name] = _identity(image, row, identity, name, extents)
    _identity(image, _ref(contract, spec['elementTypeRef']), _VIRTUAL, 'elementType', extents, virtual_slot=57, body_required=False)
    cells = {}
    for name, path in _USAGE_REFS.items():
        row = _ref(contract, path); identity = 'System.Array' if name == 'arrayType' else name[:-5] + '[]'
        _cell_type(image, dict(row, usageTag=1) if name == 'arrayType' else row, identity); cells[name] = _rva(row['cellRva'])
    for name, tokens in _PROGRAMS.items():
        expected = _program(targets[name], tokens, targets, cells, _rva(spec['initializationFlags'][name]))
        _expect(bodies[name], expected, 'arrayReference.' + name + '.full-finite-selection-access-and-fallback')
    return {'status': 'validated_conditional_array_reference_recipes', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            **{k: spec[k] for k in ('selectionOrder', 'selectionBoundary', 'getterRecipe', 'setterRecipe', 'primitiveManagedEffect',
                                  'storageBoundary', 'aliasBoundary', 'calleeBoundary', 'exceptionBoundary')},
            'unresolved': ['runtime-array-types-shape-bounds-and-values', 'runtime-predicate-selection-and-Type-implementation',
                'runtime-overlap-and-unmodelled-helper-mutation', 'Array-API-reflection-and-cast-results',
                'ToObject-and-PushObject-outcomes', 'initialization-state-and-GC', 'actual-execution']}


def validate_selected_array_reference_rules(contract: dict, *, gameassembly: Path, metadata: Path, spec: dict | None = None) -> dict:
    """Fail closed on a missing/mismatched explicit selected native pair."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'nativeInputs: selected hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.arrayReferences')
    return validate_array_reference_rules(image, contract['arrayReferenceRules'] if spec is None else spec, contract, image.mapper.pdata_function_extents(image.pe))
