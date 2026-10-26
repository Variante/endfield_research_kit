"""Authenticate the complete ReflectionMethodInvoker constructor offline.

The constructor records GetParameters' stored length, requests two Boolean
arrays and one Type array, then walks the returned parameter array in ascending
signed Int32 order. Each out flag is Out without In. Each ref flag follows the
named IsByRef request; rawTypes receives ClassImpl or its requested element Type.
Parameter records and fields are fetched again at the native read sites.

After storing the input MethodBase, the constructor selects MethodInfo return
Type versus ConstructorInfo/declaring Type, records return presence, and stores
the low-byte IsStatic result XOR one as hasThis. Nullable handling compares the
requested generic definition with Nullable<T>'s Type handle. HasValue and Value
use separate name requests; a nullable match enables the Value query even when
the first name comparison failed. They are not proved mutually exclusive.

The finite grammar includes all lazy initialization, local failure branches,
casts, writes, barriers, loop edges and the epilogue. Encoded metadata cells,
deep non-byref carriers, virtual identities and complete native extent precede
the conditional effects. Allocation defaults, actual reflection/Type/cast/name
results, helper mutation, aliases, GC completion and invocation remain open.
The lazy flag can be a mapped virtual-only byte; no live value is invented.
Native identities and hashes are inherited or kept in reviewed JSON.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index, literal_record
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_type_field_offsets, enum_members, field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier, _signature, _method_declaration, _cell_declaration
from scripts.game_data.ifix_vm_reference_helper_rules import _address, _mapped_span


class ReflectionInvokerConstructorRuleError(ValueError):
    """A constructor declaration exceeds its selected native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise ReflectionInvokerConstructorRuleError('reflection-constructor.' + detail)


_METHOD_REFS = {
    'constructor': 'reflectionDispatch.methods.reflectionConstructor',
    'isByRef': 'genericDelegateFactoryRules.methods.isByRef',
    'isConstructor': 'reflectionDispatch.methods.isConstructor',
    'isStatic': 'reflectionDispatch.methods.isStatic',
    'getTypeFromHandle': 'genericDelegateFactoryRules.methods.getTypeFromHandle',
    'stringEquality': 'genericDelegateCatalogRules.methods.stringEquality',
}
_METHODS = {
    'constructor': ('IFix.Core.ReflectionMethodInvoker', '.ctor', ['System.Reflection.MethodBase'], 'void', False),
    'isByRef': ('System.Type', 'get_IsByRef', [], 'bool', False),
    'isConstructor': ('System.Reflection.MethodBase', 'get_IsConstructor', [], 'bool', False),
    'isStatic': ('System.Reflection.MethodBase', 'get_IsStatic', [], 'bool', False),
    'getTypeFromHandle': ('System.Type', 'GetTypeFromHandle', ['System.RuntimeTypeHandle'], 'System.Type', True),
    'stringEquality': ('System.String', 'Equals', ['string', 'string'], 'bool', True),
}
_HELPER_REFS = {
    'typeInitialize': 'referenceUpdateRules.helpers.typeInitialize',
    'writeBarrier': 'delegateBridgeRules.referenceWriteBarrier',
    'parameterQuery': 'genericDelegateFactoryRules.helpers.parameterQueryHelper',
    'arrayAllocate': 'objectConversionRules.helpers.arrayAllocate',
    'returnQuery': 'genericDelegateFactoryRules.helpers.returnQueryHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'arrayStore': 'genericDelegateBindingRules.helpers.singletonStore',
    'boundsFailure': 'referenceUpdateRules.helpers.boundsFailure',
    'nullFailure': 'referenceUpdateRules.helpers.nullFailure',
    'cast': 'referenceUpdateRules.helpers.cast',
    'classInitialize': 'newFieldRules.helpers.classInitialize',
    'typePredicate': 'objectConversionRules.helpers.typePredicate',
    'nameInvoke': 'virtualDispatchRules.helpers.nameInvoke',
}
_VIRTUAL_REFS = {
    'getParameters': 'genericDelegateFactoryRules.virtualMethods.getParameters',
    'returnType': 'genericDelegateFactoryRules.virtualMethods.returnType',
    'elementType': 'arrayRules.elementType',
    'declaringType': 'referenceAddressRules.virtualMethods.declaringType',
    'name': 'virtualDispatchRules.virtualMethods.name',
}
_VIRTUALS = {
    'getParameters': ('System.Reflection.MethodBase', 'GetParameters', [], 'System.Reflection.ParameterInfo[]', False, 18),
    'returnType': ('System.Reflection.MethodInfo', 'get_ReturnType', [], 'System.Type', False, 43),
    'elementType': ('System.Type', 'GetElementType', [], 'System.Type', False, 57),
    'declaringType': ('System.Reflection.MemberInfo', 'get_DeclaringType', [], 'System.Type', False, 9),
    'name': ('System.Reflection.MemberInfo', 'get_Name', [], 'string', False, 8),
    'isGenericType': ('System.Type', 'get_IsGenericType', [], 'bool', False, 50),
    'genericDefinition': ('System.Type', 'GetGenericTypeDefinition', [], 'System.Type', False, 59),
}
_USAGE_REFS = {
    'boolArray': 'arrayRules.usageCells.boolArray',
    'methodInfo': 'delegateConstruction.methodInfoType',
    'typeArray': 'genericDelegateBindingRules.usages.returnSingletonType',
    'systemType': 'objectConversionRules.usageCells.class_System_Type',
    'voidHandle': 'genericDelegateFactoryRules.usageCells.voidType',
}
_CELLS = {
    'boolArray': (1, 'bool[]'), 'constructorInfo': (1, 'System.Reflection.ConstructorInfo'),
    'methodInfo': (1, 'System.Reflection.MethodInfo'), 'nullableHandle': (2, 'System.Nullable`1'),
    'typeArray': (1, 'System.Type[]'), 'systemType': (1, 'System.Type'), 'voidHandle': (2, 'void'),
    'hasValueName': (5, 'get_HasValue'), 'valueName': (5, 'get_Value'),
}
_FIELDS = {
    'paramCount': 'int', 'hasThis': 'bool', 'hasReturn': 'bool', 'refFlags': 'bool[]',
    'outFlags': 'bool[]', 'rawTypes': 'System.Type[]', 'method': 'System.Reflection.MethodBase',
    'ctor': 'System.Reflection.ConstructorInfo', 'returnType': 'System.Type',
    'isNullableHasValue': 'bool', 'isNullableValue': 'bool',
}
_PARAM_FIELDS = {'AttrsImpl': 'System.Reflection.ParameterAttributes', 'ClassImpl': 'System.Type'}
_EFFECTS = {
    'initialization': 'zero-ctor-and-returnType-with-barriers;zero-adjacent-nullable-flags;lazy-flag-selects-nine-typeInitialize-requests',
    'allocation': 'paramCount=GetParameters-stored-Int32-length;allocate-refFlags-outFlags-rawTypes-from-fresh-paramCount-loads',
    'loop': 'ascending-wrapping-Int32-index;fresh-signed-index<parameter-length-loop-test;unsigned-access-bounds-tests',
    'outFlag': '(!In)&&Out;native-byte-attributes-test;write-before-IsByRef-request',
    'refAndType': 'IsByRef-AL-zero:refFlags[i]=0,rawTypes[i]=ClassImpl;otherwise:refFlags[i]=1,rawTypes[i]=GetElementType(ClassImpl)',
    'method': 'store-original-MethodBase-after-parameter-loop;nonconstructor:cast-MethodInfo-and-query-returnType;constructor:store-cast-ConstructorInfo-and-query-declaringType',
    'returnPresence': 'nonconstructor:returnType-pointer!=GetTypeFromHandle(void)-pointer;constructor:one',
    'thisPresence': 'low-byte-IsStatic-result-XOR-one;no-additional-normalization',
    'nullable': 'declaringType-IsGenericType-AL-nonzero-and-requested-genericDefinition-pointer-equals-Nullable-handle-Type;then-separate-Name/Equals-requests-for-get_HasValue-and-get_Value',
    'nullableFlags': 'nonmatch:both-zero;match:HasValue-comparison-normalized-to-zero-or-one,Value-comparison-low-byte;second-name-request-independent-of-first-match',
    'failures': 'local-nullFailure-or-boundsFailure-request;INT3-if-returned',
}
_CLAIMS = {
    'schema': 'endfield.ifix-vm-reflection-invoker-constructor-rules.v1',
    'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'methodRefs': _METHOD_REFS, 'helperRefs': _HELPER_REFS, 'virtualRefs': _VIRTUAL_REFS,
    'usageRefs': _USAGE_REFS, 'effects': _EFFECTS,
    'programBoundary': 'complete-constructor-body-including-local-failure-terminals',
    'storageBoundary': 'valid-stable-receiver-parameter-records-and-arrays;runtime-aliases-and-unmodelled-helper-mutation-unobserved',
    'calleeBoundary': 'normal-request-returns;allocation-reflection-Type-cast-name-assignment-GC-and-failure-transfer-outcomes-unobserved',
    'lazyBoundary': 'mapped-anonymous-byte;runtime-initialization-state-unobserved',
    'virtualBoundary': 'named-slot-requests;runtime-implementation-and-returned-values-unobserved',
}


def _claims(spec: dict) -> None:
    _need(isinstance(spec, dict) and all(type(spec.get(k)) is type(v) and spec.get(k) == v
          for k, v in _CLAIMS.items()), 'unsupported schema/reference/effect/boundary')
    _need(set(spec.get('virtualMethods', {})) == set(_VIRTUALS) - set(_VIRTUAL_REFS), 'owned virtual catalog differs')
    _need(set(spec.get('usageCells', {})) == set(_CELLS) - set(_USAGE_REFS), 'owned usage catalog differs')
    _need(spec.get('parameterAttributeBits') == {'In': 1, 'Out': 2}
          and all(type(x) is int for x in spec['parameterAttributeBits'].values()), 'parameter attribute masks differ')


def _named_carrier(image: Any, pointer: int, typ: str) -> None:
    if typ in ('System.Reflection.ParameterAttributes', 'System.Nullable`1'):
        raw = image.pe.bytes_at_va(pointer, 16)
        _need(len(raw) == 16 and raw[10] == 0x11 and not raw[11] & 0x20,
              'value-definition carrier differs: ' + typ)
        owners = [t for t in image.metadata.types if image.metadata.type_full_name(t) == typ]
        _need(len(owners) == 1 and owners[0].bitfield & 1, 'value-definition owner differs: ' + typ)
    else:
        _carrier(image, pointer, typ)
    _need(runtime_type_name(image.pe, image.metadata, pointer) == typ, 'carrier identity differs: ' + typ)


def _declaration_flags(image: Any, row: dict, identity: tuple, *, virtual: bool = False) -> None:
    """Optional provenance fields cannot contradict the named declaration."""
    owner, name, params, returned, static = identity[:5]
    methods = [m for t in image.metadata.types if image.metadata.type_full_name(t) == owner
               for m in image.metadata.methods_for(t) if image.metadata.string(m.name_index) == name
               and m.parameter_count == len(params)
               and [_type(image, p.type_index) for p in image.metadata.parameters_for(m)] == params]
    _need(len(methods) == 1, 'declaration overload differs: ' + name); method = methods[0]
    if 'returnType' in row: _need(row['returnType'] == returned, 'declared return carrier differs: ' + name)
    if 'flags' in row: _need(_address(row['flags'], 'method.flags') == method.flags, 'declared method flags differ: ' + name)
    if 'genericContainerIndex' in row:
        _need(type(row['genericContainerIndex']) is int and row['genericContainerIndex'] == method.generic_container_index == -1,
              'declared generic container differs: ' + name)
    if 'slot' in row: _need(type(row['slot']) is int and row['slot'] == method.slot, 'declared slot differs: ' + name)
    if 'parameterTypes' in row: _need(row['parameterTypes'] == params, 'declared parameters differ: ' + name)
    if virtual: _need(method.flags & 0x40, 'metadata virtual flag differs: ' + name)


def _layout(image: Any, row: dict, owner_name: str, wanted: dict[str, str], *, complete: bool) -> dict[str, int]:
    md = image.metadata; owners = [t for t in md.types if md.type_full_name(t) == owner_name]
    _need(row.get('type') == owner_name and row.get('isValueType') is False
          and len(owners) == 1 and not owners[0].bitfield & 1, 'reference owner differs: ' + owner_name)
    owner = owners[0]; definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
    _need(set(row.get('fields', {})) == set(wanted) and (not complete or set(definitions) == set(wanted)),
          'field set differs: ' + owner_name)
    offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index); result = {}
    for name, typ in wanted.items():
        declaration = row['fields'][name]; definition = definitions.get(name); offset = declaration.get('offset')
        _need(definition is not None and declaration.get('type') == typ and type(offset) is int
              and 16 <= offset < 128 and offsets.get(name) == offset and _type(image, definition.type_index) == typ,
              'field identity/offset differs: ' + name)
        pointer = image.pe.u64_at_va(_rva(image.registration['types']) + definition.type_index * 8)
        _named_carrier(image, pointer, typ); raw = image.pe.bytes_at_va(pointer, 16)
        _need(not int.from_bytes(raw[8:10], 'little') & 16, 'static field differs: ' + name)
        if 'rawTypeHex' in declaration: _need(raw == bytes.fromhex(declaration['rawTypeHex']), 'declared field raw carrier differs: ' + name)
        result[name] = offset
    if complete:
        _need(len(set(result.values())) == len(result) and result['isNullableValue'] == result['isNullableHasValue'] + 1,
              'distinct fields/adjacent nullable flags differ')
    return result


def _cells(image: Any, spec: dict, contract: dict) -> dict[str, int]:
    result = {}; md = image.metadata
    for role, (tag, typ) in _CELLS.items():
        row = _ref(contract, _USAGE_REFS[role]) if role in _USAGE_REFS else spec['usageCells'][role]
        at = _address(row['cellRva'], role); raw = image.pe.bytes_at_va(image.pe.image_base + at, 8)
        declaration = row.get('rawHex', row.get('hex'))
        if declaration is None: declaration = _rva(row['encodedWord']).to_bytes(8, 'little').hex()
        _need(raw == bytes.fromhex(declaration), 'encoded cell bytes differ: ' + role)
        _need(('usageTag' in row or 'tag' in row) and all(type(row[k]) is int and row[k] == tag for k in ('tag', 'usageTag') if k in row),
              'encoded cell tag differs: ' + role)
        if tag in (1, 2):
            index = unresolved_usage_index(raw, image.registration['typesCount'], tag=tag, source='reflection-constructor.' + role, offset=at)
            pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
            _named_carrier(image, pointer, typ); _cell_declaration(row, typ, index, image.pe.bytes_at_va(pointer, 16))
        else:
            table, pool = md.sections['stringLiteral'], md.sections['stringLiteralData']
            index = unresolved_usage_index(raw, table.size // 8, tag=5, source='reflection-constructor.literal', offset=at)
            off = table.offset + index * 8
            start, count = literal_record(md.buf[off:off + 8], pool.size, source='reflection-constructor.literal', offset=off)
            _need(md.buf[pool.offset + start:pool.offset + start + count] == typ.encode(), 'name literal differs: ' + role)
            _cell_declaration(row, typ)
        result[role] = at
    lazy = spec['lazyFlag']; _need(set(lazy) == {'rva', 'identity'} and lazy.get('identity') == 'anonymous-native-byte', 'lazy flag declaration differs')
    result['lazyFlag'] = _address(lazy['rva'], 'lazyFlag'); _mapped_span(image, result['lazyFlag'], 1, 'lazyFlag')
    return result


def _program(at: int, targets: dict[str, int], cells: dict[str, int], fields: dict[str, int],
             param_fields: dict[str, int], slots: dict[str, int]) -> bytes:
    p = _Program(at); edges = []
    for token in _PROGRAM:
        if isinstance(token, str): p.add(token); continue
        kind, *args = token
        if kind == 'label': p.mark(args[0])
        elif kind == 'call': p.call(targets[args[0]])
        elif kind == 'rip': p.rip(args[0], cells[args[1]])
        elif kind in ('field', 'paramField'):
            p.add(args[0]); p.byte((fields if kind == 'field' else param_fields)[args[1]])
            if len(args) > 2: p.add(args[2])
        elif kind in ('slot', 'slotDelta'):
            p.add(args[0]); value = slots[args[1]] - slots[args[2]] if kind == 'slotDelta' else slots[args[1]]
            p.add(value.to_bytes(1 if kind == 'slotDelta' else 4, 'little', signed=False))
        elif kind == 'edge':
            prefix = bytes.fromhex(args[0]); width = 1 if len(prefix) == 1 and prefix != b'\xe9' else 4
            p.add(prefix); edges.append((len(p.raw), width, args[1])); p.add(bytes(width))
        else: _need(False, 'unknown finite program token')
    for off, width, label in edges:
        _need(label in p.labels, 'missing finite label: ' + label)
        p.raw[off:off + width] = (p.labels[label] - off - width).to_bytes(width, 'little', signed=True)
    return bytes(p.raw)


def validate_reflection_invoker_constructor_rules(image: Any, spec: dict, contract: dict,
                                                  extents: dict[int, int]) -> dict:
    """Prove the complete constructor on an already explicitly gated image."""
    _claims(spec); fields = _layout(image, spec['fieldLayout'], 'IFix.Core.ReflectionMethodInvoker', _FIELDS, complete=True)
    param_fields = _layout(image, spec['parameterInfoLayout'], 'System.Reflection.ParameterInfo', _PARAM_FIELDS, complete=False)
    values = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'System.Reflection.ParameterAttributes')}
    _need(all(type(values.get(k)) is int and values[k] == v for k, v in spec['parameterAttributeBits'].items()), 'named In/Out enum values differ')
    targets = {}; rows = {}
    for role, identity in _METHODS.items():
        row = dict(_ref(contract, _METHOD_REFS[role])); row.setdefault('parameterCount', len(identity[2]))
        _method_declaration(row, identity); _signature(image, identity); _declaration_flags(image, row, identity)
        targets[role] = _identity(image, row, identity, role, extents, body_required=role == 'constructor'); rows[role] = row
    slots = {}
    for role, identity in _VIRTUALS.items():
        row = dict(_ref(contract, _VIRTUAL_REFS[role]) if role in _VIRTUAL_REFS else spec['virtualMethods'][role])
        for key, value in [('parameterCount', len(identity[2])), ('virtualSlot', row.get('slot', identity[5])),
                           ('returnTypeName', row.get('returnType', identity[3])), ('static', identity[4]), ('generic', False)]: row.setdefault(key, value)
        _method_declaration(row, identity, virtual=True); _signature(image, identity[:5]); _declaration_flags(image, row, identity, virtual=True)
        slots[role] = _identity(image, row, identity[:5], role, extents, virtual_slot=identity[5])
    for role, path in _HELPER_REFS.items():
        row = _ref(contract, path); count = row['byteCount']; _need(type(count) is int and 0 < count <= 4096, 'helper extent differs: ' + role)
        at = _address(row['rva'], role); _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    cells = _cells(image, spec, contract); row = rows['constructor']; at = targets['constructor']
    _expect(image.pe.bytes_at_va(image.pe.image_base + at, row['bodyBytes']), _program(at, targets, cells, fields, param_fields, slots), 'complete constructor')
    return dict(status='validated_conditional_reflection_invoker_constructor_rules', evidenceBoundary='conditional', executionBoundary='unobserved',
                methodCount=1, bodyBytes=row['bodyBytes'], virtualMethodCount=len(slots), fieldLayout=spec['fieldLayout'],
                effects=spec['effects'], storageBoundary=spec['storageBoundary'], calleeBoundary=spec['calleeBoundary'])


def validate_selected_reflection_invoker_constructor_rules(contract: dict, *, gameassembly: Path | None,
                                                         metadata: Path | None, spec: dict | None = None) -> dict:
    if gameassembly is None or metadata is None: return dict(status='missing', detail='explicit native paths required')
    n = contract['nativeInputs']; _need(bool(n.get('gameAssemblySha256')) and bool(n.get('globalMetadataSha256')), 'native hashes required')
    gate = check_installed_native_inputs(n['gameAssemblySha256'], n['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return dict(status=gate.status, detail=gate.detail)
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.reflection-constructor')
    return validate_reflection_invoker_constructor_rules(image, contract['reflectionInvokerConstructorRules'] if spec is None else spec,
                                                        contract, image.mapper.pdata_function_extents(image.pe))


# A relocatable instruction grammar, not a build address/hash catalog. Field
# displacements and selected virtual slots come from authenticated declarations.
_PROGRAM = ('48895c240848896c241048897424185741544155415641574883ec2033f64c8bf2',
 ('rip', '403835', 'lazyFlag'),
 '488be9448d7e01',
 ('edge', '75', 'initializeFields'),
 ('rip', '488d0d', 'boolArray'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'constructorInfo'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'methodInfo'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'nullableHandle'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'typeArray'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'systemType'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'voidHandle'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'hasValueName'),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'valueName'),
 ('call', 'typeInitialize'),
 ('rip', '44883d', 'lazyFlag'),
 ('label', 'initializeFields'),
 ('field', '488d4d', 'ctor'),
 ('field', '488975', 'ctor'),
 ('call', 'writeBarrier'),
 ('field', '488d4d', 'returnType'),
 ('field', '488975', 'returnType'),
 ('call', 'writeBarrier'),
 ('field', '668975', 'isNullableHasValue'),
 '4d85f6',
 ('edge', '0f84', 'nullFailure'),
 ('slot', 'b9', 'getParameters'),
 '498bd6',
 ('call', 'parameterQuery'),
 '488bf84885c0',
 ('edge', '0f84', 'nullFailure'),
 '8b4018',
 ('field', '8945', 'paramCount'),
 '8bd0',
 ('rip', '488b0d', 'boolArray'),
 ('call', 'arrayAllocate'),
 ('field', '488d4d', 'refFlags'),
 ('field', '488945', 'refFlags'),
 ('call', 'writeBarrier'),
 ('field', '8b55', 'paramCount'),
 ('rip', '488b0d', 'boolArray'),
 ('call', 'arrayAllocate'),
 ('field', '488d4d', 'outFlags'),
 ('field', '488945', 'outFlags'),
 ('call', 'writeBarrier'),
 ('field', '8b55', 'paramCount'),
 ('rip', '488b0d', 'typeArray'),
 ('call', 'arrayAllocate'),
 ('field', '488d4d', 'rawTypes'),
 ('field', '488945', 'rawTypes'),
 ('call', 'writeBarrier'),
 '8bde',
 ('label', 'parameterLoop'),
 '3b5f18',
 ('edge', '0f8d', 'methodSetup'),
 ('field', '488b55', 'outFlags'),
 ('edge', '0f83', 'boundsFailure'),
 '4863c3488b4cc7204885c9',
 ('edge', '0f84', 'nullFailure'),
 ('paramField', '448479', 'AttrsImpl', ''),
 ('edge', '76', 'noIn'),
 '8bce',
 ('edge', 'eb', 'outStore'),
 ('label', 'noIn'),
 '4863c3488b4cc720',
 ('paramField', 'f641', 'AttrsImpl', '02'),
 '0f97c1',
 ('label', 'outStore'),
 '4885d2',
 ('edge', '0f84', 'nullFailure'),
 '3b5a18',
 ('edge', '0f83', 'boundsFailure'),
 '4863c3884c10203b5f18',
 ('edge', '0f83', 'boundsFailure'),
 '4863c3488b4cc7204885c9',
 ('edge', '0f84', 'nullFailure'),
 ('paramField', '488b49', 'ClassImpl'),
 '4885c9',
 ('edge', '0f84', 'nullFailure'),
 '33d2',
 ('call', 'isByRef'),
 ('field', '488b4d', 'refFlags'),
 '84c0',
 ('edge', '75', 'byRef'),
 '4885c9',
 ('edge', '0f84', 'nullFailure'),
 '3b5918',
 ('edge', '0f83', 'boundsFailure'),
 '4863c34088740820',
 ('field', '4c8b65', 'rawTypes'),
 '3b5f18',
 ('edge', '0f83', 'boundsFailure'),
 '4863c34c8b6cc7204d85ed',
 ('edge', '0f84', 'nullFailure'),
 ('paramField', '4d8b6d', 'ClassImpl'),
 ('edge', 'eb', 'typeStore'),
 ('label', 'byRef'),
 '4885c9',
 ('edge', '0f84', 'nullFailure'),
 '3b5918',
 ('edge', '73', 'boundsFailure'),
 '4863c344887c0820',
 ('field', '4c8b65', 'rawTypes'),
 '3b5f18',
 ('edge', '73', 'boundsFailure'),
 '4863c3488b4cc7204885c9',
 ('edge', '0f84', 'nullFailure'),
 ('paramField', '488b51', 'ClassImpl'),
 '4885d2',
 ('edge', '0f84', 'nullFailure'),
 ('slot', 'b9', 'elementType'),
 ('call', 'returnQuery'),
 '4c8be8',
 ('label', 'typeStore'),
 '4d85e4',
 ('edge', '0f84', 'nullFailure'),
 '498bd5498bcc',
 ('call', 'assignmentCheck'),
 '4863d34d8bc5498bcc',
 ('call', 'arrayStore'),
 '4103df',
 ('edge', 'e9', 'parameterLoop'),
 ('label', 'boundsFailure'),
 ('call', 'boundsFailure'),
 'cc',
 ('label', 'methodSetup'),
 ('field', '488d4d', 'method'),
 ('field', '4c8975', 'method'),
 ('call', 'writeBarrier'),
 '33d2498bce',
 ('call', 'isConstructor'),
 ('slot', '41bc', 'declaringType'),
 '498bce84c0',
 ('edge', '75', 'constructorCase'),
 ('rip', '488b15', 'methodInfo'),
 ('call', 'cast'),
 '4885c0',
 ('edge', '0f84', 'nullFailure'),
 ('rip', '488b15', 'methodInfo'),
 '498bce',
 ('call', 'cast'),
 '488bd0',
 ('slotDelta', '418d4c24', 'returnType', 'declaringType'),
 ('call', 'returnQuery'),
 ('field', '488d4d', 'returnType'),
 ('field', '488945', 'returnType'),
 ('call', 'writeBarrier'),
 ('rip', '488b0d', 'systemType'),
 ('field', '488b7d', 'returnType'),
 ('rip', '488b1d', 'voidHandle'),
 ('call', 'classInitialize'),
 '33d2488bcb',
 ('call', 'getTypeFromHandle'),
 '483bf80f95c0',
 ('edge', 'eb', 'returnPresence'),
 ('label', 'constructorCase'),
 ('rip', '488b15', 'constructorInfo'),
 ('call', 'cast'),
 ('field', '488945', 'ctor'),
 '498bce',
 ('rip', '488b15', 'constructorInfo'),
 ('call', 'cast'),
 ('field', '488d4d', 'ctor'),
 ('call', 'writeBarrier'),
 '418bcc498bd6',
 ('call', 'returnQuery'),
 ('field', '488d4d', 'returnType'),
 ('field', '488945', 'returnType'),
 ('call', 'writeBarrier'),
 '418ac7',
 ('label', 'returnPresence'),
 '33d2',
 ('field', '8845', 'hasReturn'),
 '498bce',
 ('call', 'isStatic'),
 '4132c7418bcc498bd6',
 ('field', '8845', 'hasThis'),
 ('call', 'returnQuery'),
 '4885c0',
 ('edge', '0f84', 'nullFailure'),
 ('slot', 'b9', 'isGenericType'),
 '488bd0',
 ('call', 'typePredicate'),
 ('slot', '41bd', 'name'),
 '84c0',
 ('edge', '74', 'nullableAbsent'),
 '418bcc498bd6',
 ('call', 'returnQuery'),
 '4885c0',
 ('edge', '0f84', 'nullFailure'),
 ('slotDelta', '418d4d', 'genericDefinition', 'name'),
 '488bd0',
 ('call', 'returnQuery'),
 ('rip', '488b0d', 'systemType'),
 '488bf8',
 ('rip', '488b1d', 'nullableHandle'),
 ('call', 'classInitialize'),
 '33d2488bcb',
 ('call', 'getTypeFromHandle'),
 '483bf8',
 ('edge', '75', 'nullableAbsent'),
 '418bcd498bd6',
 ('call', 'nameInvoke'),
 ('rip', '488b15', 'hasValueName'),
 '4533c0488bc8',
 ('call', 'stringEquality'),
 '84c0',
 ('edge', '74', 'hasValueFalse'),
 '418ac7',
 ('edge', 'eb', 'hasValueStore'),
 ('label', 'nullableAbsent'),
 '448afe',
 ('label', 'hasValueFalse'),
 '408ac6',
 ('label', 'hasValueStore'),
 ('field', '8845', 'isNullableHasValue'),
 '4584ff',
 ('edge', '74', 'epilogue'),
 '418bcd498bd6',
 ('call', 'nameInvoke'),
 ('rip', '488b15', 'valueName'),
 '4533c0488bc8',
 ('call', 'stringEquality'),
 '408af0',
 ('label', 'epilogue'),
 '488b5c2450',
 ('field', '408875', 'isNullableValue'),
 '488b6c2458488b7424604883c420415f415e415d415c5fc3',
 ('label', 'nullFailure'),
 ('call', 'nullFailure'),
 'cc')
