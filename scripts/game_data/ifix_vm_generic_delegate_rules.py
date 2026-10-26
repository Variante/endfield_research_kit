"""Authenticate the generic fallback's conditional signature selection.

The parent owns selected native-input and complete Create-body authentication.
This helper checks the cache probe, Invoke reflection queries, rejection branches,
the ParameterInfo callback and its cached null creator against reviewed windows.
On a cache miss, normal reflection results reject a non-void value-type return,
more than four parameters, or any value-type/by-reference parameter. Rejection
selects a creator whose reviewed leaf returns null; that creator is cached by
delegate Type. A hit skips signature selection, including a cached rejection.

The accepted path selects genericAction[0] for zero-parameter void signatures,
otherwise genericAction[count] or genericFunc[count] according to the void
comparison. Those are conditional array selections, not recovered array contents
or a proof that MakeGenericMethod/Delegate.CreateDelegate succeeds. Lazy LINQ
catalog creation, runtime cache contents, generic sharing and actual invocation
remain unresolved. A stored MethodSpec is the context passed to a shared helper;
it is never promoted to a live MethodInfo or runtime sharing selection.
"""

from __future__ import annotations

import hashlib
import re
import struct
from typing import Any

from scripts.game_data.il2cpp.context import (
    generic_method_candidates, literal_record, method_parameter_owner, rip_qword_load_target,
    type_parameter_owner, unresolved_usage_index, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_rules import _method


class GenericDelegateRuleError(ValueError):
    """A generic delegate selection lacks its reviewed native witness."""


_WINDOWS = ('cacheLookup', 'invokeShape', 'parameterPredicate', 'zeroActionChoice',
            'genericTableChoice', 'rejectionCreator', 'cacheStoreAndAdapter')
_METHODS = {
    'getMethod': ('System.Type', 'GetMethod', ('string',)),
    'isValueType': ('System.Type', 'get_IsValueType', ()),
    'isByRef': ('System.Type', 'get_IsByRef', ()),
    'getTypeFromHandle': ('System.Type', 'GetTypeFromHandle', ('System.RuntimeTypeHandle',)),
    'parameterPredicate': ('IFix.Core.GenericDelegateFactory', '<Create>m__4', ('System.Reflection.ParameterInfo',)),
    'nullCreator': ('IFix.Core.GenericDelegateFactory', '<Create>m__5', ('IFix.Core.GenericDelegate',)),
}
_VIRTUALS = {
    'getParameters': ('System.Reflection.MethodBase', 'GetParameters', 18),
    'returnType': ('System.Reflection.MethodInfo', 'get_ReturnType', 43),
}
_FIELDS = {
    'IFix.Core.GenericDelegateFactory': {
        'genericAction': 'System.Reflection.MethodInfo[]', 'genericFunc': 'System.Reflection.MethodInfo[]',
        'genericDelegateCreatorCache': 'System.Collections.Generic.Dictionary`2<System.Type,System.Func`2<IFix.Core.GenericDelegate,System.Delegate>>',
        '<>f__am$cache4': 'System.Func`2<System.Reflection.ParameterInfo,bool>',
        '<>f__am$cache5': 'System.Func`2<IFix.Core.GenericDelegate,System.Delegate>',
    },
    'System.Reflection.ParameterInfo': {'ClassImpl': 'System.Type'},
}
_CONTEXTS = {
    'cacheLookup': ('System.Collections.Generic.Dictionary`2', 'TryGetValue',
                    ('System.Type', 'System.Func`2<IFix.Core.GenericDelegate,System.Delegate>'), ()),
    'cacheStore': ('System.Collections.Generic.Dictionary`2', 'set_Item',
                   ('System.Type', 'System.Func`2<IFix.Core.GenericDelegate,System.Delegate>'), ()),
    'anyParameter': ('System.Linq.Enumerable', 'Any', (), ('System.Reflection.ParameterInfo',)),
}
_WITNESSES = {
    'zeroRegister': '4533e4', 'cacheOutAddress': '4c8d442430', 'cacheKey': '488b5510',
    'getParametersSlot': 'b912000000488bd0', 'returnTypeSlot': 'b92b000000498bd7',
    'nonValueTypeContinue': '84c07436', 'voidComparison': '483bf8',
    'parameterLimit': '837e1804', 'anyArguments': '488b5138488bce',
    'zeroParameterCompare': '44396618', 'funcCountIndex': '48634618',
    'funcMethodFetch': '498b7cc020', 'actionCountIndex': '48634618',
    'actionMethodFetch': '488b7cc220', 'zeroActionFetch': '488b4020',
    'rejectedCreator': '488b5940', 'cacheValueSave': '48895c2430',
    'cacheStoreArguments': '4c8b442430488b5510',
    'factoryAdapterArguments': '4d8bcd4c89642420448bc6498bd6488bc8',
    'creatorHelperArguments': '4533c0488bd3488bcf',
    'predicateParameterField': '488b4918', 'predicateRepeatField': '488b4b18',
    'predicateTrue': 'b0014883c4205bc3',
}
_EDGES = {
    'cacheLookupCall': ('call', 'cacheLookupHelper'),
    'cacheHit': ('jne', 'adapterEntry'),
    'getInvoke': ('call', 'getMethod'),
    'getParameters': ('call', 'parameterQueryHelper'),
    'getReturnType': ('call', 'returnQueryHelper'),
    'returnIsValueType': ('call', 'isValueType'),
    'getVoidType': ('call', 'getTypeFromHandle'),
    'rejectValueReturn': ('jne', 'rejectionCreator'),
    'rejectParameterCount': ('jg', 'rejectionCreator'),
    'anyParameter': ('call', 'anyParameterHelper'),
    'rejectAnyParameter': ('jne', 'rejectionCreator'),
    'notZeroActionReturn': ('jne', 'genericPathEntry'),
    'notZeroActionCount': ('jne', 'genericPathEntry'),
    'chooseActionArray': ('je', 'actionArrayEntry'),
    'predicateValueType': ('call', 'isValueType'),
    'predicateFalseThenByRef': ('je', 'predicateByRefEntry'),
    'predicateByRef': ('call', 'isByRef'),
    'cacheStoreCall': ('call', 'cacheStoreHelper'),
}
_FIELD_USES = {
    'cacheLookupField': ('IFix.Core.GenericDelegateFactory', 'genericDelegateCreatorCache', '488b4a'),
    'funcArrayField': ('IFix.Core.GenericDelegateFactory', 'genericFunc', '4c8b41'),
    'rejectedCreator': ('IFix.Core.GenericDelegateFactory', '<>f__am$cache5', '488b59'),
    'anyArguments': ('IFix.Core.GenericDelegateFactory', '<>f__am$cache4', '488b51'),
    'predicateParameterField': ('System.Reflection.ParameterInfo', 'ClassImpl', '488b49'),
    'predicateRepeatField': ('System.Reflection.ParameterInfo', 'ClassImpl', '488b4b'),
}
_TARGETS = {'adapterEntry': '488b0d', 'genericPathEntry': '488b0d',
            'actionArrayEntry': 'e8', 'predicateByRefEntry': '488b4b18'}


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _named(rows: list[dict[str, Any]], expected: Any, label: str) -> dict[str, dict[str, Any]]:
    mapped = {r.get('name'): r for r in rows}
    if len(mapped) != len(rows) or set(mapped) != set(expected):
        raise GenericDelegateRuleError(f'generic-delegate.{label}: missing/duplicate/unknown declarations')
    return mapped


def _slice(raw: bytes, base: int, site: int, size: int, label: str) -> bytes:
    at = site-base
    if size < 1 or not 0 <= at <= len(raw)-size:
        raise GenericDelegateRuleError(f'generic-delegate.{label}: outside authenticated body')
    return raw[at:at+size]


def _hash(raw: bytes, row: dict[str, Any], label: str) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != row['sha256'].upper() or raw != bytes.fromhex(row['hex']):
        raise GenericDelegateRuleError(f"generic-delegate.{label}: expectedSha256={row['sha256']} actualSha256={actual}")


def _identity(image: Any, row: dict[str, Any], expected: tuple, *, virtual: bool = False) -> Any:
    type_name, name, params = expected[:3]
    if (row.get('type'), row.get('method')) != (type_name, name):
        raise GenericDelegateRuleError(f'generic-delegate.{row.get("name")}: unsupported method claim')
    owners = [t for t in image.metadata.types if image.metadata.type_full_name(t) == type_name]
    found = []
    for owner in owners:
        for m in image.metadata.methods_for(owner):
            if image.metadata.string(m.name_index) != name:
                continue
            types = [runtime_type_name(image.pe, image.metadata, image.pe.u64_at_va(_rva(image.registration['types'])+p.type_index*8)) for p in image.metadata.parameters_for(m)]
            if virtual or types == list(params):
                found.append(m)
    if len(found) != 1:
        raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: expected one method, actual={len(found)}')
    m = found[0]
    if m.token != _rva(row['token']) or m.parameter_count != row['parameterCount']:
        raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: method token/signature differs')
    if virtual:
        if m.slot != params or row.get('slot') != params or m.parameter_count != 0:
            raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: virtual slot differs')
    elif row.get('parameterTypes') != list(params) or image.method_pointer_va(m)-image.pe.image_base != _rva(row['rva']):
        raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: registered method pointer differs')
    return m


def _fields(image: Any, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped = {row.get('type'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(_FIELDS):
        raise GenericDelegateRuleError('generic-delegate.fields: unsupported owner set')
    md, pe, reg = image.metadata, image.pe, image.registration
    for name, expected in _FIELDS.items():
        owners = [t for t in md.types if md.type_full_name(t) == name]
        fields = mapped[name]['fields']
        if len(owners) != 1 or set(fields) != set(expected):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: field set differs')
        offsets = runtime_type_field_offsets(md, pe, reg, owners[0].index)
        actual_fields = {md.string(f.name_index): f for f in md.fields_for(owners[0])}
        for field, type_name in expected.items():
            row = fields[field]
            if field not in actual_fields or row.get('offset') != offsets.get(field) or row.get('type') != type_name:
                raise GenericDelegateRuleError(f'generic-delegate.{name}.{field}: layout differs')
            f = actual_fields[field]
            if runtime_type_name(pe, md, pe.u64_at_va(_rva(reg['types'])+f.type_index*8)) != type_name:
                raise GenericDelegateRuleError(f'generic-delegate.{name}.{field}: type differs')
    return {name: row['fields'] for name, row in mapped.items()}


def _context_signature(image: Any, method: Any, role: str) -> None:
    """Authenticate open generic signature/VAR ownership before a context join."""
    md, pe, reg = image.metadata, image.pe, image.registration
    if bool(method.flags & 0x10) != (role == 'anyParameter'):
        raise GenericDelegateRuleError(f'generic-delegate.{role}: static/instance signature differs')
    params = md.parameters_for(method)
    if method.parameter_count != 2 or len(params) != 2:
        raise GenericDelegateRuleError(f'generic-delegate.{role}: expected two-parameter overload')
    pointers = [pe.u64_at_va(_rva(reg['types'])+p.type_index*8) for p in params]
    raw = [pe.bytes_at_va(p, 16) for p in pointers]
    expected_return = 'void' if role == 'cacheStore' else 'bool'
    return_pointer = pe.u64_at_va(_rva(reg['types'])+method.return_type*8)
    if (runtime_type_name(pe, md, return_pointer) != expected_return
        or pe.bytes_at_va(return_pointer, 16)[11] & 0x20):
        raise GenericDelegateRuleError(f'generic-delegate.{role}: generic method return type differs')
    byref = [bool(struct.unpack_from('<I', r, 8)[0] & (1 << 29)) for r in raw]
    if byref != ([False, True] if role == 'cacheLookup' else [False, False]):
        raise GenericDelegateRuleError(f'generic-delegate.{role}: generic parameter by-reference flags differ')
    if role == 'anyParameter':
        names = [runtime_type_name(pe, md, p) for p in pointers]
        match = re.fullmatch(r'System\.Collections\.Generic\.IEnumerable`1<MVAR\[(\d+)\]>', names[0])
        if match is None or names[1] != f'System.Func`2<MVAR[{match.group(1)}],bool>':
            raise GenericDelegateRuleError('generic-delegate.anyParameter: predicate-taking generic signature differs')
        owner = method_parameter_owner(md.buf, int(match.group(1)), [m.generic_container_index for m in md.methods], source='generic-delegate.Any-signature')
        if owner['methodIndex'] != method.index or owner['ordinal'] != 0:
            raise GenericDelegateRuleError('generic-delegate.anyParameter: MVAR owner/ordinal differs')
    else:
        containers = [t.generic_container_index for t in md.types]
        for ordinal, record in enumerate(raw):
            if record[10] != 0x13:
                raise GenericDelegateRuleError(f'generic-delegate.{role}: dictionary argument is not VAR')
            index = int.from_bytes(record[:8], 'little')
            owner = type_parameter_owner(md.buf, index, containers, source='generic-delegate.Dictionary-signature')
            if owner['typeIndex'] != method.declaring_type or owner['ordinal'] != ordinal:
                raise GenericDelegateRuleError(f'generic-delegate.{role}: VAR owner/ordinal differs')


def _usage(image: Any, row: dict[str, Any], body: bytes, base: int) -> int | None:
    label = row['name']
    site = _rva(row['loadRva'])
    cell = rip_qword_load_target(_slice(body, base, site, 7, label), site, source='generic-delegate.'+label)
    if cell != _rva(row['cellRva']):
        raise GenericDelegateRuleError(f'generic-delegate.{label}: usage load target differs')
    raw = image.pe.bytes_at_va(image.pe.image_base+cell, 8)
    if raw.hex().upper() != row['rawHex'].upper():
        raise GenericDelegateRuleError(f'generic-delegate.{label}: usage cell differs')
    md, pe, reg = image.metadata, image.pe, image.registration
    tag = row['tag']
    if label in _CONTEXTS:
        records_va = _rva(reg['methodSpecs'])
        record = usage_method_spec(raw, pe.bytes_at_va(records_va, reg['methodSpecsCount']*12), len(md.methods),
                                   reg['genericInstsCount'], source='generic-delegate.'+label,
                                   usage_offset=pe.image_base+cell, records_offset=records_va)
        m = md.methods[record['definition']]
        class_args = _argument_names(image, record['classInstantiationIndex'])
        method_args = _argument_names(image, record['methodInstantiationIndex'])
        expected = _CONTEXTS[label]
        if (tag, md.type_full_name(md.types[m.declaring_type]), md.string(m.name_index), tuple(class_args), tuple(method_args)) != (6, *expected):
            raise GenericDelegateRuleError(f'generic-delegate.{label}: MethodSpec identity/context differs')
        if m.parameter_count != 2:
            raise GenericDelegateRuleError(f'generic-delegate.{label}: expected two-parameter overload')
        _context_signature(image, m, label)
        return record['definition']
    elif label in ('factoryType', 'voidType'):
        expected_tag, expected_type = (1, 'IFix.Core.GenericDelegateFactory') if label == 'factoryType' else (2, 'void')
        idx = unresolved_usage_index(raw, reg['typesCount'], tag=expected_tag, source='generic-delegate.'+label, offset=cell)
        pointer = pe.u64_at_va(_rva(reg['types'])+idx*8)
        if (tag != expected_tag or pe.bytes_at_va(pointer, 16)[11] & 0x20
            or runtime_type_name(pe, md, pointer) != expected_type):
            raise GenericDelegateRuleError(f'generic-delegate.{label}: type-cell identity differs')
    elif label == 'invokeName':
        table, pool = md.sections['stringLiteral'], md.sections['stringLiteralData']
        idx = unresolved_usage_index(raw, table.size//8, tag=5, source='generic-delegate.'+label, offset=cell)
        at = table.offset+idx*8
        start, size = literal_record(md.buf[at:at+8], pool.size, source='generic-delegate.Invoke', offset=at)
        if tag != 5 or md.buf[pool.offset+start:pool.offset+start+size] != b'Invoke':
            raise GenericDelegateRuleError('generic-delegate.invokeName: literal differs')
    else:
        expected_name = '<Create>m__4' if label == 'predicateMethod' else '<Create>m__5'
        idx = unresolved_usage_index(raw, len(md.methods), tag=3, source='generic-delegate.'+label, offset=cell)
        m = md.methods[idx]
        if tag != 3 or (md.type_full_name(md.types[m.declaring_type]), md.string(m.name_index)) != ('IFix.Core.GenericDelegateFactory', expected_name):
            raise GenericDelegateRuleError(f'generic-delegate.{label}: callback method identity differs')
    return None


def _argument_names(image: Any, index: int) -> list[str]:
    args = image.instantiations.resolve(index).arguments
    for arg in args:
        raw = bytes.fromhex(arg.raw_type_record_hex)
        if len(raw) != 16 or raw[11] & 0x20:
            raise GenericDelegateRuleError('generic-delegate.MethodSpec: by-reference argument carrier differs')
    return [runtime_type_name(image.pe, image.metadata, a.type_pointer_va) for a in args]


def _generic_targets(image: Any, definitions: dict[str, int], helpers: dict[str, dict[str, Any]]) -> None:
    """Prove registered MethodDef-family membership, never exact-context sharing."""
    pe, reg = image.pe, image.registration
    raw_specs = pe.bytes_at_va(_rva(reg['methodSpecs']), reg['methodSpecsCount']*12)
    selected = {i: definition for i, (definition, _class, _method) in enumerate(struct.iter_unpack('<iii', raw_specs))
                if definition in definitions.values()}
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    base = _rva(reg['genericMethodTable'])
    candidates = generic_method_candidates(
        pe.bytes_at_va(base, reg['genericMethodTableCount']*16), reg['genericMethodTableCount'],
        reg['methodSpecsCount'], set(selected), code['genericMethodPointersCount'], code['invokerPointersCount'],
        source='generic-delegate.registered-target-families', offset=base,
    )
    family_targets: dict[int, set[int]] = {}
    for row in candidates:
        pointer = pe.u64_at_va(_rva(code['genericMethodPointers'])+row['indices'][0]*8)
        family_targets.setdefault(selected[row['methodSpecIndex']], set()).add(pointer-pe.image_base)
    helper_names = {'cacheLookup': 'cacheLookupHelper', 'cacheStore': 'cacheStoreHelper', 'anyParameter': 'anyParameterHelper'}
    for name, definition in definitions.items():
        target = _rva(helpers[helper_names[name]]['rva'])
        if target not in family_targets.get(definition, set()):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: direct target lacks registered MethodDef-family candidate')


def _edge(raw: bytes, base: int, row: dict[str, Any], targets: dict[str, int]) -> None:
    kind, target = _EDGES[row['name']]
    if (row.get('kind'), row.get('target')) != (kind, target):
        raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: unsupported control claim')
    prefix = {'call': b'\xe8', 'jne': b'\x0f\x85', 'je': b'\x0f\x84', 'jg': b'\x0f\x8f'}[kind]
    site = _rva(row['rva'])
    first = _slice(raw, base, site, 1, row['name'])
    short = {'jne': b'\x75', 'je': b'\x74', 'jg': b'\x7f'}.get(kind)
    if first == short:
        instruction = _slice(raw, base, site, 2, row['name'])
        actual = site+2+int.from_bytes(instruction[1:], 'little', signed=True)
    else:
        size = len(prefix)+4
        instruction = _slice(raw, base, site, size, row['name'])
        actual = site+size+int.from_bytes(instruction[len(prefix):], 'little', signed=True) if instruction.startswith(prefix) else None
    if actual != targets[target]:
        raise GenericDelegateRuleError(f'generic-delegate.{row["name"]}: expectedTarget={targets[target]:#x} actualTarget={actual}')


def validate_generic_delegate_rules(image: Any, spec: dict[str, Any], contract: dict[str, Any], extents: dict[int, int]) -> dict[str, Any]:
    """Validate native selection rules after the parent's explicit native gate."""
    if (spec.get('schema') != 'endfield.ifix-vm-generic-delegate-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('factoryMethodRef') != 'delegateConstruction.methodCalls.genericFallback'
            or spec.get('parameterLimit') != 4 or spec.get('rejectReturn') != 'value-type-except-void'
            or spec.get('rejectParameter') != 'value-type-or-by-reference'
            or spec.get('cacheKey') != 'delegate-Type' or spec.get('rejectedCreatorResult') != 'null'
            or spec.get('catalogBoundary') != 'runtime-array-contents-and-reflection-unresolved'):
        raise GenericDelegateRuleError('generic-delegate: unsupported schema/selection/boundary')
    method = next(row for row in contract['delegateConstruction']['methodCalls'] if row['role'] == 'genericFallback')
    base = _method(image, method, extents)
    body = image.pe.bytes_at_va(image.pe.image_base+base, method['bodyBytes'])
    windows = _named(spec['windows'], _WINDOWS, 'windows')
    for name, row in windows.items():
        _hash(_slice(body, base, _rva(row['rva']), row['byteCount'], name), row, name)
    fields = _fields(image, spec['fieldLayouts'])
    methods = _named(spec['methods'], _METHODS, 'methods')
    for name, row in methods.items():
        _identity(image, row, _METHODS[name])
    virtuals = _named(spec['virtualMethods'], _VIRTUALS, 'virtualMethods')
    for name, row in virtuals.items():
        _identity(image, row, _VIRTUALS[name], virtual=True)
    predicate = methods['parameterPredicate']
    predicate_raw = image.pe.bytes_at_va(image.pe.image_base+_rva(predicate['rva']), predicate['bodyBytes'])
    if extents.get(image.pe.image_base+_rva(predicate['rva'])) != image.pe.image_base+_rva(predicate['rva'])+predicate['bodyBytes']:
        raise GenericDelegateRuleError('generic-delegate.parameterPredicate: native extent differs')
    _hash(predicate_raw, {'sha256': predicate['bodySha256'], 'hex': predicate['hex']}, 'parameterPredicate')
    null = methods['nullCreator']
    null_raw = image.pe.bytes_at_va(image.pe.image_base+_rva(null['rva']), 3)
    if null.get('bodyBytes') != 3 or null_raw != b'\x33\xc0\xc3':
        raise GenericDelegateRuleError('generic-delegate.nullCreator: exact zero-return leaf differs')
    _hash(null_raw, {'sha256': null['bodySha256'], 'hex': null['hex']}, 'nullCreator')
    witnesses = _named(spec['witnesses'], _WITNESSES, 'witnesses')
    for name, row in witnesses.items():
        raw, start = (predicate_raw, _rva(predicate['rva'])) if name.startswith('predicate') else (body, base)
        if _slice(raw, start, _rva(row['rva']), len(bytes.fromhex(_WITNESSES[name])), name) != bytes.fromhex(_WITNESSES[name]):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: semantic witness differs')
    field_uses = _named(spec['fieldUses'], _FIELD_USES, 'fieldUses')
    for name, (owner, field, prefix) in _FIELD_USES.items():
        raw, start = (predicate_raw, _rva(predicate['rva'])) if name.startswith('predicate') else (body, base)
        offset = fields[owner][field]['offset']
        if not 0 <= offset <= 127 or _slice(raw, start, _rva(field_uses[name]['rva']), 4, name) != bytes.fromhex(prefix)+bytes([offset]):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: named field access differs')
    if fields['IFix.Core.GenericDelegateFactory']['genericAction']['offset'] != 0:
        raise GenericDelegateRuleError('generic-delegate.genericAction: zero-displacement field differs')
    usages = _named(spec['usageCells'], (*_CONTEXTS, 'factoryType', 'voidType', 'invokeName', 'predicateMethod', 'nullCreatorMethod'), 'usageCells')
    definitions = {}
    for row in usages.values():
        definition = _usage(image, row, body, base)
        if row['name'] in _CONTEXTS:
            definitions[row['name']] = definition
    helpers = _named(spec['helpers'], ('cacheLookupHelper', 'cacheStoreHelper', 'anyParameterHelper', 'parameterQueryHelper', 'returnQueryHelper'), 'helpers')
    for name, row in helpers.items():
        pointer = image.pe.image_base+_rva(row['rva'])
        if extents.get(pointer) != pointer+row['byteCount']:
            raise GenericDelegateRuleError(f'generic-delegate.{name}: native extent differs')
        _hash(image.pe.bytes_at_va(pointer, row['byteCount']), row, name)
    _generic_targets(image, definitions, helpers)
    for name in ('parameterQueryHelper', 'returnQueryHelper'):
        row = helpers[name]
        helper_raw = image.pe.bytes_at_va(image.pe.image_base+_rva(row['rva']), row['byteCount'])
        witness = _slice(helper_raw, _rva(row['rva']), _rva(row['slotProgramRva']), 3, name+'.slot')
        if witness != bytes.fromhex('0fb7d9'):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: unsigned interface slot source differs')
        expected = bytes.fromhex('488d431448c1e0044803074c8b00488b5008')
        selection = _slice(helper_raw, _rva(row['rva']), _rva(row['vtableProgramRva']), len(expected), name+'.vtable')
        if selection != expected:
            raise GenericDelegateRuleError(f'generic-delegate.{name}: slot*16/class-vtable program differs')
    targets = {name: _rva(row['rva']) for name, row in methods.items()}
    targets.update({name: _rva(row['rva']) for name, row in helpers.items()})
    if set(spec['targets']) != set(_TARGETS):
        raise GenericDelegateRuleError('generic-delegate.targets: unsupported target set')
    for name, prefix in _TARGETS.items():
        raw, start = (predicate_raw, _rva(predicate['rva'])) if name.startswith('predicate') else (body, base)
        if _slice(raw, start, _rva(spec['targets'][name]), len(bytes.fromhex(prefix)), name) != bytes.fromhex(prefix):
            raise GenericDelegateRuleError(f'generic-delegate.{name}: target entry differs')
    targets.update({name: _rva(value) for name, value in spec['targets'].items()})
    targets['rejectionCreator'] = _rva(windows['rejectionCreator']['rva'])
    edges = _named(spec['controlEdges'], _EDGES, 'controlEdges')
    for name, row in edges.items():
        raw, start = (predicate_raw, _rva(predicate['rva'])) if name.startswith('predicate') else (body, base)
        _edge(raw, start, row, targets)
    return {'status': 'validated_conditional_generic_delegate_selection', 'parameterLimit': 4,
            'rejectReturn': spec['rejectReturn'], 'rejectParameter': spec['rejectParameter'],
            'cacheKey': 'delegate-Type', 'cacheHit': 'skip-signature-selection',
            'sharedHelperIdentity': 'registered-MethodDef-family-with-stored-typed-context',
            'rejectedCreatorResult': 'null', 'acceptedSelection': 'zero-void-action[0]-otherwise-void-action[count]-or-func[count]',
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['lazy-catalog-content-and-order', 'runtime-cache-and-signature-results',
                           'reflection-construction-success', 'runtime-generic-sharing', 'actual-invocation']}
