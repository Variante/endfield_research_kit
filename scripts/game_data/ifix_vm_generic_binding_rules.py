"""Authenticate accepted IFix generic creators and their reflection arguments.

The caller gates one explicit native image and authenticates the parent factory
selection rules. This helper follows the selected Create body into a parameter
Type projection, the Func-only concatenation with a singleton return Type, and
the common Type-array materialization. It authenticates the non-indexed Select,
Concat and ToArray overloads, reciprocal MVAR owners/ordinals, stored typed
MethodSpecs and registered MethodDef-family call targets. The native operands
put the parameter projection first and the return singleton second. Stored
contexts and static pointer-family membership do not select runtime sharing.

The common binding helper forwards the resulting Type array and selected
MethodInfo to the named MakeGenericMethod virtual slot. Its returned MethodInfo
is stored in the generic creator closure; the zero-argument Action creator
instead stores the parent's directly selected MethodInfo. Both closures capture
the delegate-Type scope. Their normal leaf path preserves the incoming
GenericDelegate as the object argument and tail-calls the named
Delegate.CreateDelegate(Type, object, MethodInfo), clearing its hidden argument.

The validator proves local arguments, capture fields and control joins. Lazy
catalog contents, existing callback-cache contents, enumerator results, live
virtual pairs, creator-constructor/reflection success and invocation remain
unobserved. It does not infer a constructed delegate from these static bodies.
"""
from __future__ import annotations

import hashlib
import re
import struct
from typing import Any

from scripts.game_data.il2cpp.context import (
    generic_method_candidates, method_parameter_owner, rip_qword_load_target,
    unresolved_usage_index, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_rules import _method as _parent_method


class GenericBindingRuleError(ValueError):
    """The selected native evidence does not establish a reviewed binding rule."""


_SCOPE = 'IFix.Core.GenericDelegateFactory+<Create>c__AnonStorey'
_METHODS = {
    'parameterTypeSelector': ('IFix.Core.GenericDelegateFactory', '<Create>m__6', ('System.Reflection.ParameterInfo',), 'System.Type'),
    'zeroClosure': (_SCOPE + '1', '<>m__0', ('IFix.Core.GenericDelegate',), 'System.Delegate'),
    'genericClosure': (_SCOPE + '2', '<>m__0', ('IFix.Core.GenericDelegate',), 'System.Delegate'),
    'makeGenericMethod': ('System.Reflection.MethodInfo', 'MakeGenericMethod', ('System.Type[]',), 'System.Reflection.MethodInfo'),
}
_FIELDS = {
    'IFix.Core.GenericDelegateFactory': {'genericAction': 'System.Reflection.MethodInfo[]', '<>f__am$cache6': 'System.Func`2<System.Reflection.ParameterInfo,System.Type>'},
    _SCOPE + '0': {'delegateType': 'System.Type'},
    _SCOPE + '1': {'methodInfo': 'System.Reflection.MethodInfo', '<>f__ref$0': _SCOPE + '0'},
    _SCOPE + '2': {'methodInfo': 'System.Reflection.MethodInfo', '<>f__ref$0': _SCOPE + '0'},
    'System.Reflection.ParameterInfo': {'ClassImpl': 'System.Type'},
}
_WINDOWS = ('scopeCapture', 'zeroClosure', 'genericClosureCapture', 'parameterProjection', 'returnTypeAppend', 'genericBinding')
_WITNESSES = {
    'inputTypeCapture': '488bd9', 'scopeTypeStore': '488d481048895810',
    'zeroScopeStore': '488d481848896818', 'zeroMethodStore': '488d4f1048894710',
    'zeroCreatorArgs': '4533c9488bd7488bc8', 'genericScopeStore': '488d481848896818',
    'selectorCacheRead': '488b5148', 'projectionArguments': '488bce', 'projectionResult': '4c8be0',
    'singletonLength': 'ba01000000', 'singletonReturnSource': 'b92b000000498bd7',
    'singletonStoreArguments': '4c8bc633d2488bcb', 'concatArguments': '488bd3498bcc',
    'concatResult': '4c8be0', 'toArrayArguments': '498bcc', 'makeGenericArguments': '4c8bc0488bd7',
    'boundMethodStore': '498d4e1049894610', 'genericCreatorArgs': '4533c9498bd6488bc8',
}
_CONTEXTS = {'select': ('Select', ('System.Reflection.ParameterInfo', 'System.Type')),
             'concat': ('Concat', ('System.Type',)), 'toArray': ('ToArray', ('System.Type',))}
_TYPE_USAGES = {'scope': _SCOPE + '0', 'zeroClosureType': _SCOPE + '1', 'genericClosureType': _SCOPE + '2',
                'zeroCreatorType': 'System.Func`2<IFix.Core.GenericDelegate,System.Delegate>',
                'genericCreatorType': 'System.Func`2<IFix.Core.GenericDelegate,System.Delegate>',
                'selectorType': 'System.Func`2<System.Reflection.ParameterInfo,System.Type>',
                'returnSingletonType': 'System.Type[]'}
_METHOD_USAGES = {'selectorMethod': 'parameterTypeSelector', 'zeroClosureMethod': 'zeroClosure', 'genericClosureMethod': 'genericClosure'}


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _need(ok: bool, label: str) -> None:
    if not ok:
        raise GenericBindingRuleError('generic-binding.' + label)


def _named(rows: list[dict[str, Any]], names: Any, label: str) -> dict[str, dict[str, Any]]:
    result = {r.get('name'): r for r in rows}
    _need(len(result) == len(rows) and set(result) == set(names), label + ': missing/duplicate/unknown declarations')
    return result


def _slice(raw: bytes, base: int, site: int, size: int) -> bytes:
    at = site - base
    _need(type(size) is int and size > 0 and 0 <= at <= len(raw) - size, 'native range outside authenticated body')
    return raw[at:at + size]


def _hash(raw: bytes, row: dict[str, Any]) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    _need(len(raw) == row['byteCount'] and raw == bytes.fromhex(row['hex']) and actual == row['sha256'].upper(),
          row.get('name', 'body') + f": native bytes differ expectedSha256={row['sha256']} actualSha256={actual}")


def _body(image: Any, row: dict[str, Any], extents: dict[int, int]) -> bytes:
    pointer, size = image.pe.image_base + _rva(row['rva']), row['byteCount']
    _need(type(size) is int and 0 < size <= 65536 and extents.get(pointer) == pointer + size,
          row.get('name', 'body') + ': native extent differs')
    raw = image.pe.bytes_at_va(pointer, size)
    _hash(raw, row)
    return raw


def _rel(prefix: bytes, site: int, target: int) -> bytes:
    delta = target - site - len(prefix) - 4
    _need(-(1 << 31) <= delta < (1 << 31), 'relative target outside signed range')
    return prefix + struct.pack('<i', delta)


def _type_pointer(image: Any, index: int) -> int:
    _need(type(index) is int and 0 <= index < image.registration['typesCount'], 'type index outside registration')
    return image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)


def _type_name(image: Any, index: int) -> str:
    return runtime_type_name(image.pe, image.metadata, _type_pointer(image, index))


def _byref(image: Any, index: int) -> bool:
    return bool(image.pe.bytes_at_va(_type_pointer(image, index), 16)[11] & 0x20)


def _identity(image: Any, row: dict[str, Any], role: str) -> Any:
    owner_name, method_name, parameters, returned = _METHODS[role]
    _need((row.get('type'), row.get('method'), row.get('parameterTypes'), row.get('returnType')) ==
          (owner_name, method_name, list(parameters), returned), role + ': unsupported method signature claim')
    md = image.metadata
    found = [m for t in md.types if md.type_full_name(t) == owner_name for m in md.methods_for(t)
             if md.string(m.name_index) == method_name and m.parameter_count == len(parameters)
             and [_type_name(image, p.type_index) for p in md.parameters_for(m)] == list(parameters)]
    _need(len(found) == 1, role + ': expected one named signature')
    method = found[0]
    indices = [p.type_index for p in md.parameters_for(method)] + [method.return_type]
    _need(row.get('parameterCount') == len(parameters) and method.generic_container_index == -1
          and all(not struct.unpack_from('<I', image.pe.bytes_at_va(_type_pointer(image, index), 16), 8)[0] & (1 << 29)
                  for index in indices), role + ': arity, generic or by-reference signature differs')
    _need(method.token == _rva(row['token']) and _type_name(image, method.return_type) == returned,
          role + ': method token or return type differs')
    _need(bool(method.flags & 0x10) == (role == 'parameterTypeSelector'), role + ': static/instance method kind differs')
    if role == 'makeGenericMethod':
        _need(method.slot == row['slot'] == 45, role + ': virtual slot differs')
    else:
        _need(image.method_pointer_va(method) == image.pe.image_base + _rva(row['rva']), role + ': registered pointer differs')
    return method


def _fields(image: Any, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped = {r.get('type'): r for r in rows}
    _need(len(mapped) == len(rows) and set(mapped) == set(_FIELDS), 'fields: unsupported owner set')
    md = image.metadata
    for name, fields in _FIELDS.items():
        owners = [t for t in md.types if md.type_full_name(t) == name]
        _need(len(owners) == 1 and set(mapped[name]['fields']) == set(fields), name + ': field owner/set differs')
        owner = owners[0]
        offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index)
        definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
        for field, expected in fields.items():
            row = mapped[name]['fields'][field]
            _need(field in definitions and row.get('offset') == offsets.get(field) and row.get('type') == expected
                  and _type_name(image, definitions[field].type_index) == expected, name + '.' + field + ': named layout differs')
    return {name: row['fields'] for name, row in mapped.items()}


def _context_signature(image: Any, method: Any, role: str) -> None:
    """Disambiguate LINQ overloads and reciprocally authenticate each MVAR."""
    md = image.metadata
    _need(bool(method.flags & 0x10), role + ': LINQ MethodDef is not static')
    params = md.parameters_for(method)
    count = 1 if role == 'toArray' else 2
    _need(method.parameter_count == len(params) == count, role + ': generic overload parameter count differs')
    indices = [p.type_index for p in params] + [method.return_type]
    pointers = [_type_pointer(image, index) for index in indices]
    _need(all(not struct.unpack_from('<I', image.pe.bytes_at_va(p, 16), 8)[0] & (1 << 29) for p in pointers),
          role + ': generic signature has by-reference carrier')
    names = [runtime_type_name(image.pe, md, p) for p in pointers]
    match = re.fullmatch(r'System\.Collections\.Generic\.IEnumerable`1<MVAR\[(\d+)\]>', names[0])
    _need(match is not None, role + ': source is not IEnumerable<MVAR>')
    first = int(match.group(1))
    if role == 'select':
        match = re.fullmatch(r'System\.Func`2<MVAR\[' + str(first) + r'\],MVAR\[(\d+)\]>', names[1])
        _need(match is not None, 'select: non-indexed selector overload differs')
        last = int(match.group(1))
        _need(names[2] == f'System.Collections.Generic.IEnumerable`1<MVAR[{last}]>', 'select: result element differs')
        parameters = [first, last]
    elif role == 'concat':
        _need(names[0] == names[1] == names[2], 'concat: same-element sequence signature differs')
        parameters = [first]
    else:
        _need(role == 'toArray' and names[1] == f'MVAR[{first}][]', 'toArray: element array return differs')
        parameters = [first]
    for ordinal, index in enumerate(parameters):
        owner = method_parameter_owner(md.buf, index, [m.generic_container_index for m in md.methods], source='generic-binding.' + role)
        argc = struct.unpack_from('<i', bytes.fromhex(owner['containerRawHex']), 4)[0]
        _need(owner['methodIndex'] == method.index and owner['ordinal'] == ordinal and argc == len(parameters),
              role + ': reciprocal MVAR owner/ordinal/arity differs')


def _usage(image: Any, row: dict[str, Any], body: bytes, base: int, methods: dict[str, Any]) -> int | None:
    name, site = row['name'], _rva(row['loadRva'])
    cell = rip_qword_load_target(_slice(body, base, site, 7), site, source='generic-binding.' + name)
    _need(cell == _rva(row['cellRva']), name + ': usage load target differs')
    raw = image.pe.bytes_at_va(image.pe.image_base + cell, 8)
    _need(raw == bytes.fromhex(row['rawHex']), name + ': usage cell differs')
    md, reg = image.metadata, image.registration
    if name in _TYPE_USAGES:
        index = unresolved_usage_index(raw, reg['typesCount'], tag=1, source='generic-binding.' + name, offset=cell)
        _need(row['tag'] == 1 and row['identity'] == _TYPE_USAGES[name] and not _byref(image, index)
              and _type_name(image, index) == _TYPE_USAGES[name], name + ': type usage identity differs')
    elif name in _METHOD_USAGES:
        index = unresolved_usage_index(raw, len(md.methods), tag=3, source='generic-binding.' + name, offset=cell)
        _need(row['tag'] == 3 and row['identity'] == _METHOD_USAGES[name] and methods[_METHOD_USAGES[name]].index == index,
              name + ': callback MethodDef identity differs')
    else:
        expected_name, expected_arguments = _CONTEXTS[name]
        records = _rva(reg['methodSpecs'])
        record = usage_method_spec(raw, image.pe.bytes_at_va(records, reg['methodSpecsCount'] * 12), len(md.methods),
                                   reg['genericInstsCount'], source='generic-binding.' + name, usage_offset=image.pe.image_base + cell, records_offset=records)
        method = md.methods[record['definition']]
        class_arguments = image.instantiations.resolve(record['classInstantiationIndex']).arguments
        method_arguments = image.instantiations.resolve(record['methodInstantiationIndex']).arguments
        for argument in (*class_arguments, *method_arguments):
            type_raw = bytes.fromhex(argument.raw_type_record_hex)
            _need(len(type_raw) == 16 and not type_raw[11] & 0x20, name + ': stored generic argument is by-reference or malformed')
        class_args = [runtime_type_name(image.pe, md, a.type_pointer_va) for a in class_arguments]
        args = [runtime_type_name(image.pe, md, a.type_pointer_va) for a in method_arguments]
        _need(row['tag'] == 6 and row['identity'] == expected_name and md.type_full_name(md.types[method.declaring_type]) == 'System.Linq.Enumerable'
              and md.string(method.name_index) == expected_name and not class_args and tuple(args) == expected_arguments,
              name + ': stored MethodSpec identity/context differs')
        _context_signature(image, method, name)
        return record['definition']
    return None


def _generic_targets(image: Any, definitions: dict[str, int], helpers: dict[str, dict[str, Any]]) -> None:
    """Static MethodDef-family membership; exact stored-context sharing stays open."""
    pe, reg = image.pe, image.registration
    raw = pe.bytes_at_va(_rva(reg['methodSpecs']), reg['methodSpecsCount'] * 12)
    selected = {j: d for j, (d, _c, _m) in enumerate(struct.iter_unpack('<iii', raw)) if d in definitions.values()}
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    table = _rva(reg['genericMethodTable'])
    candidates = generic_method_candidates(pe.bytes_at_va(table, reg['genericMethodTableCount'] * 16), reg['genericMethodTableCount'],
                                         reg['methodSpecsCount'], set(selected), code['genericMethodPointersCount'], code['invokerPointersCount'],
                                         source='generic-binding.registered-families', offset=table)
    targets: dict[int, set[int]] = {}
    for row in candidates:
        pointer = pe.u64_at_va(_rva(code['genericMethodPointers']) + row['indices'][0] * 8)
        targets.setdefault(selected[row['methodSpecIndex']], set()).add(pointer - pe.image_base)
    for name, definition in definitions.items():
        _need(_rva(helpers[name]['rva']) in targets.get(definition, set()), name + ': direct target lacks registered MethodDef-family candidate')


def validate_generic_binding_rules(image: Any, spec: dict[str, Any], contract: dict[str, Any], extents: dict[int, int]) -> dict[str, Any]:
    """Prove accepted creator forwarding after the selected native-input gate."""
    _need(spec.get('schema') == 'endfield.ifix-vm-generic-binding-rules.v1' and spec.get('evidenceBoundary') == 'conditional'
          and spec.get('executionBoundary') == 'unobserved' and spec.get('factoryMethodRef') == 'delegateConstruction.methodCalls.genericFallback'
          and spec.get('selectionRef') == 'genericDelegateFactoryRules'
          and spec.get('typeArgumentOrder') == 'parameter-projection-then-return-type-for-Func'
          and spec.get('genericMethodBoundary') == 'runtime-vtable-pair-and-reflection-success-unresolved'
          and spec.get('closureBinding') == 'captured-Type-incoming-GenericDelegate-captured-MethodInfo'
          and spec.get('pipelineBoundary') == 'stored-typed-context-and-registered-MethodDef-family', 'unsupported schema/selection/boundary')
    parent = contract['genericDelegateFactoryRules']
    _need(parent['factoryMethodRef'] == spec['factoryMethodRef'] and parent['evidenceBoundary'] == 'conditional', 'parent selection reference differs')
    factory = next(r for r in contract['delegateConstruction']['methodCalls'] if r['role'] == 'genericFallback')
    delegate = next(r for r in contract['delegateConstruction']['methodCalls'] if r['role'] == 'reflectionDelegate')
    _need((factory['type'], factory['method'], factory['parameterTypes']) ==
          ('IFix.Core.GenericDelegateFactory', 'Create', ['System.Type', 'IFix.Core.VirtualMachine', 'int', 'object'])
          and (delegate['type'], delegate['method'], delegate['parameterTypes']) ==
          ('System.Delegate', 'CreateDelegate', ['System.Type', 'object', 'System.Reflection.MethodInfo']),
          'inherited parent method signature differs')
    base, target = _parent_method(image, factory, extents), _parent_method(image, delegate, extents)
    body = image.pe.bytes_at_va(image.pe.image_base + base, factory['bodyBytes'])
    windows = _named(spec['windows'], _WINDOWS, 'windows')
    for row in windows.values():_hash(_slice(body, base, _rva(row['rva']), row['byteCount']), row)
    fields = _fields(image, spec['fieldLayouts'])
    declarations = _named(spec['methods'], _METHODS, 'methods')
    methods = {name: _identity(image, row, name) for name, row in declarations.items()}
    for name in ('zeroClosure', 'genericClosure'):
        row = declarations[name]['body']; raw = _body(image, row, extents); rb = _rva(row['rva'])
        _need(rb == _rva(declarations[name]['rva']), name + ': body/pointer reference differs')
        layout = fields[_METHODS[name][0]]; link, info = layout['<>f__ref$0']['offset'], layout['methodInfo']['offset']
        dtype = fields[_SCOPE + '0']['delegateType']['offset']
        _need(all(type(v) is int and 0 <= v <= 127 for v in (link, info, dtype)), name + ': unsupported capture displacement')
        expected = (bytes.fromhex('4883ec28488b41') + bytes([link]) + bytes.fromhex('4885c07506')
                    + _rel(b'\xe8', rb + 13, _rva(spec['normalNullFailureHelperRva'])) + b'\xcc'
                    + bytes.fromhex('4c8b41') + bytes([info]) + bytes.fromhex('4533c9488b48') + bytes([dtype])
                    + bytes.fromhex('4883c428') + _rel(b'\xe9', rb + 34, target))
        _need(raw == expected, name + ': captured arguments, hidden zero or delegate tail differs')
    selector = declarations['parameterTypeSelector']; row = selector['body']; raw = _body(image, row, extents); rb = _rva(row['rva'])
    _need(rb == _rva(selector['rva']), 'selector: body/pointer reference differs')
    field = fields['System.Reflection.ParameterInfo']['ClassImpl']['offset']
    _need(0 <= field <= 127 and raw == bytes.fromhex('4883ec284885c97506') + _rel(b'\xe8', rb + 9, _rva(spec['normalNullFailureHelperRva']))
          + b'\xcc' + bytes.fromhex('488b41') + bytes([field]) + bytes.fromhex('4883c428c3'), 'selector: named parameter Type leaf differs')
    witnesses = _named(spec['witnesses'], _WITNESSES, 'witnesses')
    for name, hex_bytes in _WITNESSES.items():
        expected = bytes.fromhex(hex_bytes)
        _need(witnesses[name]['hex'] == hex_bytes and _slice(body, base, _rva(witnesses[name]['rva']), len(expected)) == expected,
              name + ': native forwarding witness differs')
    required_offsets = {(_SCOPE + '0', 'delegateType'):16, (_SCOPE + '1', 'methodInfo'):16, (_SCOPE + '1', '<>f__ref$0'):24,
                        (_SCOPE + '2', 'methodInfo'):16, (_SCOPE + '2', '<>f__ref$0'):24, ('IFix.Core.GenericDelegateFactory', '<>f__am$cache6'):72}
    _need(all(fields[t][f]['offset'] == off for (t, f), off in required_offsets.items()), 'capture/cache witness field offsets differ')
    usages = _named(spec['usages'], (*_TYPE_USAGES, *_METHOD_USAGES, *_CONTEXTS), 'usages')
    definitions = {}
    for name, row in usages.items():
        definition = _usage(image, row, body, base, methods)
        if name in _CONTEXTS:definitions[name] = definition
    helpers = _named(spec['helpers'], (*_CONTEXTS, 'makeGenericMethod', 'singletonStore'), 'helpers')
    for row in helpers.values():_body(image, row, extents)
    _generic_targets(image, definitions, helpers)
    helper = helpers['makeGenericMethod']; rb = _rva(helper['rva']); raw = image.pe.bytes_at_va(image.pe.image_base + rb, helper['byteCount'])
    expected = (bytes.fromhex('48895c2408574883ec20488b0a498bd8488bfa') + _rel(b'\xe8', rb + 19, _rva(spec['makeGenericPrepareHelperRva']))
                + bytes.fromhex('4c8b07488bd3488bcf498b80') + struct.pack('<I', (methods['makeGenericMethod'].slot + 20) * 16)
                + bytes.fromhex('4d8b80') + struct.pack('<I', (methods['makeGenericMethod'].slot + 20) * 16 + 8)
                + bytes.fromhex('488b5c24304883c4205f48ffe0'))
    _need(raw == expected, 'MakeGenericMethod: virtual pair, Type[] forwarding or tail differs')
    store = helpers['singletonStore']; rb = _rva(store['rva']); raw = image.pe.bytes_at_va(image.pe.image_base + rb, store['byteCount'])
    expected = (bytes.fromhex('4883ec283b511873164c8944d120488d0cd14883c1204883c428')
                + _rel(b'\xe9', rb + 26, _rva(spec['arrayWriteBarrierHelperRva']))
                + _rel(b'\xe8', rb + 31, _rva(spec['arrayBoundsFailureHelperRva'])) + b'\xcc')
    _need(raw == expected, 'singletonStore: checked array element store or barrier tail differs')
    calls = _named(spec['calls'], (*_CONTEXTS, 'makeGenericMethod', 'singletonStore', 'returnType'), 'calls')
    for name, row in calls.items():
        _need(row['target'] == (name if name != 'returnType' else 'parent.returnQueryHelper'), name + ': call role differs')
        target = _rva(helpers[name]['rva']) if name != 'returnType' else _rva(next(r for r in parent['helpers'] if r['name']=='returnQueryHelper')['rva'])
        site = _rva(row['rva']);_need(_slice(body, base, site, 5) == _rel(b'\xe8', site, target), name + ': direct call target differs')
    jumps = _named(spec['jumps'], ('zeroCreatorToCache','concatToCommonArray','genericCreatorToCache'), 'jumps')
    join = _rva(next(r for r in parent['windows'] if r['name']=='cacheStoreAndAdapter')['rva'])
    array_join = _rva(windows['genericBinding']['rva'])
    for name, row in jumps.items():
        site = _rva(row['rva']);target = array_join if name=='concatToCommonArray' else join
        _need(_rva(row['targetRva']) == target, name + ': parent join declaration differs')
        raw = _slice(body, base, site, 2)
        if raw[0] == 0xeb:_need(site + 2 + int.from_bytes(raw[1:], 'little', signed=True) == target, name + ': short join differs')
        else:_need(_slice(body, base, site, 5) == _rel(b'\xe9', site, target), name + ': near join differs')
    return {'status':'validated_conditional_generic_creator_binding','typeArgumentProgram':'Select-parameter-Types; Func-only-Concat-with-return-Type-last; common-ToArray',
            'genericMethodRequest':'MethodInfo.MakeGenericMethod(Type[])','closureBinding':'captured-Type,incoming-GenericDelegate,captured-MethodInfo',
            'sharedHelperIdentity':'registered-MethodDef-family-with-stored-typed-context','evidenceBoundary':'conditional','executionBoundary':'unobserved',
            'unresolved':['lazy-catalog-content-and-order','existing-selector-callback-cache','runtime-enumeration-and-type-array-values',
                          'runtime-generic-sharing-and-virtual-pair','creator-constructor-and-reflection-success','actual-delegate-invocation']}
