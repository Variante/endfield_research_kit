"""Authenticate UpdateReference's conditional reference-target requests.

The selected static method preserves the incoming base, descriptor, managed
array, replacement object and VM before selecting the descriptor's ValueType.
StackReference reads the pointer stored across Value1/Value2 and forwards that
target with the incoming object and Type to the parent's PushObject method.
StaticFieldReference uses Value1: nonnegative indexes read fieldInfos, whereas
negative indexes store into staticFields at the Int32 complement of Value1.
FieldReference uses Value2 for the same reflected/internal field selection and
Value1 for the owner in managedStack. A reflected FieldInfo compared equal to
null selects newFieldInfos.get_Item; other rows request FieldInfo.SetValue.
Both request the incoming replacement object. Static setters receive null as
the owner; instance setters receive the selected managed owner. Negative
instance fields forward complement(Value2), object, Type and VM to the parent's
AnonymousStorey.Set identity, whose implementation belongs to instance rules.

ArrayReference forwards the cast managedStack[Value1] result, incoming object
and Value2 to Array.SetValue(object,int). ChainFieldReference selects FieldAddr
at the descriptor's own base-relative slot index and forwards its Object and
FieldIdList, the list length minus one, Value2 != -1 and both VM field tables
to mSet. The recursive mSet implementation remains unresolved here. The
dispatcher's other tags return without issuing these target requests.

The full finite UpdateReference grammar authenticates every instruction,
including null/bounds exits, shared setter tails and argument reloads. Typed
Dictionary MethodSpec arguments and reciprocal VAR ordinals identify a stored
context; registered MethodDef-family membership identifies the direct helper
without selecting runtime generic sharing. Native input selection belongs to
the caller, or the explicit-path standalone wrapper below. Normal completion,
descriptor/array stability, cast/reflection success, target values, alias
mutation and actual execution remain unobserved. These are conditional target
expressions, never a receipt that a runtime reference was successfully updated.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import (
    generic_method_candidates, type_parameter_owner, unresolved_usage_index, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_delegate_rules import _method as _parent_method


class ReferenceUpdateRuleError(ValueError):
    """A reference-update claim lacks its selected native witness."""


_METHOD_REFS = {
    'update': 'initobjStackEffect.updateReferenceMethod',
    'pushObject': 'initobjStackEffect.pushObjectMethod',
    'anonymousSet': 'instanceFieldRules.methods.Set',
}
_METHODS = {
    'update': ('IFix.Core.EvaluationStackOperation', 'UpdateReference',
               ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'IFix.Core.VirtualMachine', 'System.Type'], 'void', True),
    'pushObject': ('IFix.Core.EvaluationStackOperation', 'PushObject',
                   ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'System.Type'], 'void', True),
    'anonymousSet': ('IFix.Core.AnonymousStorey', 'Set', ['int', 'object', 'System.Type', 'IFix.Core.VirtualMachine'], 'void', False),
    'fieldEqual': ('System.Reflection.FieldInfo', 'op_Equality', ['System.Reflection.FieldInfo', 'System.Reflection.FieldInfo'], 'bool', True),
    'fieldSet': ('System.Reflection.FieldInfo', 'SetValue', ['object', 'object'], 'void', False),
    'newFieldSet': ('IFix.Core.NewFieldInfo', 'SetValue', ['object', 'object'], 'void', False),
    'arraySet': ('System.Array', 'SetValue', ['object', 'int'], 'void', False),
    'chainSet': ('IFix.Core.EvaluationStackOperation', 'mSet', ['bool', 'object', 'object', 'int', 'int[]',
        'System.Reflection.FieldInfo[]', 'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>'], 'void', True),
}
_HELPER_REFS = {'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
                'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck'}
_HELPERS = ('typeInitialize', 'cast', 'boundsFailure', 'nullFailure', 'dictionaryItem')
_FIELDS = {'IFix.Core.VirtualMachine': {'fieldInfos': 'System.Reflection.FieldInfo[]',
        'newFieldInfos': 'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>', 'staticFields': 'object[]'},
    'IFix.Core.FieldAddr': {'Object': 'object', 'FieldIdList': 'int[]'}}
_TAGS = {'StackReference': 4, 'StaticFieldReference': 5, 'FieldReference': 6, 'ChainFieldReference': 7,
         'Object': 8, 'ValueType': 9, 'ArrayReference': 10}
_USAGES = {'arrayType': 'System.Array', 'anonymousType': 'IFix.Core.AnonymousStorey',
           'chainType': 'IFix.Core.FieldAddr', 'instanceDictionary': 'get_Item', 'staticDictionary': 'get_Item'}
_ROUTES = {
    'StackReference': ('descriptor.pointer-at-Value1', 'PushObject(base,target,managed,obj,type)'),
    'FieldReference': ('Value2>=0:fieldInfos[Value2]-or-newFieldInfos[Value2];Value2<0:AnonymousStorey.Set(~Value2)',
                       'owner=managed[Value1];replacement=obj'),
    'StaticFieldReference': ('Value1>=0:fieldInfos[Value1]-or-newFieldInfos[Value1];Value1<0:staticFields[~Value1]',
                             'owner=null;replacement=obj'),
    'ArrayReference': ('cast-Array(managed[Value1])', 'Array.SetValue(obj,Value2)'),
    'ChainFieldReference': ('cast-FieldAddr(managed[(descriptor-base)/12])',
                            'mSet(Value2!=-1,FieldAddr.Object,obj,FieldIdList.Length-1,FieldIdList,fieldInfos,newFieldInfos)'),
}


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _need(ok: bool, label: str) -> None:
    if not ok:
        raise ReferenceUpdateRuleError('reference-update.' + label)


def _named(rows: list[dict], names: Any, label: str) -> dict[str, dict]:
    mapped = {row.get('name'): row for row in rows}
    _need(len(mapped) == len(rows) and set(mapped) == set(names), label + ': missing/duplicate/unknown declarations')
    return mapped


def _ref(contract: dict, path: str) -> dict:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            selected = [item for item in row if item.get('name', item.get('role')) == key]
            _need(len(selected) == 1, 'references: missing/ambiguous ' + path)
            row = selected[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            _need(False, 'references: missing ' + path)
    _need(isinstance(row, dict), 'references: invalid ' + path)
    return row


def _hash(raw: bytes, row: dict, label: str) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    _need(len(raw) == row['byteCount'] and actual == row['sha256'].upper()
          and ('hex' not in row or raw == bytes.fromhex(row['hex'])),
          label + f": native bytes differ expectedSha256={row['sha256']} actualSha256={actual}")


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    if raw != expected:
        offset = next((i for i, (actual, wanted) in enumerate(zip(raw, expected)) if actual != wanted), min(len(raw), len(expected)))
        _need(False, label + f': program differs offset={offset:#x} expectedBytes={len(expected)} actualBytes={len(raw)} '
              + f'expected={expected[offset:offset+16].hex()} actual={raw[offset:offset+16].hex()}')


def _type_pointer(image: Any, index: int) -> int:
    _need(type(index) is int and 0 <= index < image.registration['typesCount'], 'type index outside registration')
    return image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)


def _type(image: Any, index: int) -> str:
    pointer = _type_pointer(image, index)
    _need(not image.pe.bytes_at_va(pointer, 16)[11] & 0x20, 'unexpected by-reference type carrier')
    return runtime_type_name(image.pe, image.metadata, pointer)


def _identity(image: Any, row: dict, role: str, extents: dict[int, int]) -> tuple[int, bytes]:
    owner, name, params, returned, static = _METHODS[role]
    _need((row.get('type'), row.get('method'), row.get('parameterCount')) == (owner, name, len(params)), role + ': method identity differs')
    md = image.metadata
    selected = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
                if md.string(m.name_index) == name and m.parameter_count == len(params)
                and [_type(image, p.type_index) for p in md.parameters_for(m)] == params]
    _need(len(selected) == 1, role + ': expected one named overload')
    method = selected[0]
    _need(_type(image, method.return_type) == returned and bool(method.flags & 0x10) == static
          and method.generic_container_index == -1, role + ': return/static/generic signature differs')
    if 'parameterTypes' in row:
        _need(row['parameterTypes'] == params, role + ': declared parameters differ')
    rva = _parent_method(image, dict(row, parameterTypes=params), extents)
    return rva, image.pe.bytes_at_va(image.pe.image_base + rva, row['bodyBytes'])


def _layouts(image: Any, rows: list[dict], value: dict) -> dict[str, dict[str, int]]:
    mapped = {row.get('type'): row for row in rows}
    _need(len(rows) == len(mapped) and set(mapped) == set(_FIELDS), 'fields: owner set differs')
    md = image.metadata; result = {}
    for name, expected in _FIELDS.items():
        owners = [t for t in md.types if md.type_full_name(t) == name]
        _need(len(owners) == 1 and set(mapped[name]['fields']) == set(expected), name + ': field owner/set differs')
        owner = owners[0]; offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index)
        definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
        result[name] = {}
        for field, typ in expected.items():
            row = mapped[name]['fields'][field]
            _need(field in definitions and row.get('type') == typ and _type(image, definitions[field].type_index) == typ
                  and row.get('offset') == offsets.get(field), name + '.' + field + ': named layout differs')
            result[name][field] = row['offset']
    owners = [t for t in md.types if md.type_full_name(t) == 'IFix.Core.Value']
    _need(value.get('type') == 'IFix.Core.Value' and len(owners) == 1 and owners[0].bitfield & 1,
          'Value: expected one value-type owner')
    offsets = runtime_type_field_offsets(md, image.pe, image.registration, owners[0].index)
    _need({n: offsets.get(n) for n in ('Type', 'Value1', 'Value2')} == value['fieldOffsets'] == {'Type': 16, 'Value1': 20, 'Value2': 24},
          'Value: boxed-to-unmanaged field offsets differ')
    definitions = {md.string(f.name_index): f for f in md.fields_for(owners[0])}
    _need(value.get('enumType') == 'IFix.Core.ValueType'
          and all(name in definitions and _type(image, definitions[name].type_index) == typ
                  for name, typ in {'Type': 'IFix.Core.ValueType', 'Value1': 'int', 'Value2': 'int'}.items()),
          'Value: named descriptor field types differ')
    return result


def _dictionary_signature(image: Any, method: Any) -> None:
    md = image.metadata; params = md.parameters_for(method)
    _need(method.parameter_count == len(params) == 1 and not method.flags & 0x10 and method.generic_container_index == -1,
          'dictionary: instance one-parameter overload differs')
    for ordinal, index in enumerate([params[0].type_index, method.return_type]):
        raw = image.pe.bytes_at_va(_type_pointer(image, index), 16)
        _need(raw[10] == 0x13 and not raw[11] & 0x20, 'dictionary: expected non-byref VAR carrier')
        owner = type_parameter_owner(md.buf, int.from_bytes(raw[:8], 'little'), [t.generic_container_index for t in md.types], source='reference-update.dictionary')
        _need(owner['typeIndex'] == method.declaring_type and owner['ordinal'] == ordinal
              and struct.unpack_from('<i', bytes.fromhex(owner['containerRawHex']), 4)[0] == 2,
              'dictionary: reciprocal VAR owner/ordinal/arity differs')


def _usage(image: Any, row: dict) -> int | None:
    name = row['name']; cell = _rva(row['cellRva']); raw = image.pe.bytes_at_va(image.pe.image_base + cell, 8)
    _need(raw == bytes.fromhex(row['rawHex']) and row.get('identity') == _USAGES[name], name + ': usage identity/bytes differ')
    md, reg = image.metadata, image.registration
    if name in ('arrayType', 'anonymousType', 'chainType'):
        idx = unresolved_usage_index(raw, reg['typesCount'], tag=1, source='reference-update.' + name, offset=cell)
        _need(_type(image, idx) == _USAGES[name], name + ': cast type differs')
        return None
    at = _rva(reg['methodSpecs'])
    record = usage_method_spec(raw, image.pe.bytes_at_va(at, reg['methodSpecsCount'] * 12), len(md.methods),
        reg['genericInstsCount'], source='reference-update.' + name, usage_offset=image.pe.image_base + cell, records_offset=at)
    method = md.methods[record['definition']]
    args = image.instantiations.resolve(record['classInstantiationIndex']).arguments
    for arg in args:
        raw_type = bytes.fromhex(arg.raw_type_record_hex)
        _need(len(raw_type) == 16 and not raw_type[11] & 0x20, name + ': by-reference/malformed generic argument')
    names = [runtime_type_name(image.pe, md, arg.type_pointer_va) for arg in args]
    _need(md.type_full_name(md.types[method.declaring_type]) == 'System.Collections.Generic.Dictionary`2'
          and md.string(method.name_index) == 'get_Item' and names == ['int', 'IFix.Core.NewFieldInfo']
          and record['methodInstantiationIndex'] == -1, name + ': Dictionary MethodSpec context differs')
    _dictionary_signature(image, method)
    return record['definition']


def _dictionary_target(image: Any, definition: int, target: int) -> None:
    pe, reg = image.pe, image.registration
    specs = pe.bytes_at_va(_rva(reg['methodSpecs']), reg['methodSpecsCount'] * 12)
    selected = {j for j, (d, _c, _m) in enumerate(struct.iter_unpack('<iii', specs)) if d == definition}
    code = image.mapper.code_registration_summary(pe, image.code_registration); at = _rva(reg['genericMethodTable'])
    candidates = generic_method_candidates(pe.bytes_at_va(at, reg['genericMethodTableCount'] * 16), reg['genericMethodTableCount'],
        reg['methodSpecsCount'], selected, code['genericMethodPointersCount'], code['invokerPointersCount'], source='reference-update.dictionary-target', offset=at)
    pointers = {pe.u64_at_va(_rva(code['genericMethodPointers']) + row['indices'][0] * 8) - pe.image_base for row in candidates}
    _need(target in pointers, 'dictionary: direct target lacks registered MethodDef-family candidate')


# Every fixed encoding expresses argument movement, a native field access or
# finite dispatch/control rule. Build-specific edge targets stay in the data.
_BLOCKS = {
    'dispatch': ('4885db', ('je', 'nullExit'), '8b0b83e904', ('je', 'stack'),
        '83e901', ('je', 'static'), '83e901', ('je8', 'field'), '83e901', ('je8', 'field'),
        '83e901', ('je8', 'return'), '83e901', ('je8', 'return'), '83f901', ('jne8', 'return')),
    'array': ('486343044885ff', ('je', 'nullExit'), '3b4718', ('jae', 'boundsExit'),
        ('rip', '488b15', 'arrayType'), '488b4cc720', ('call', 'cast'), '4885c0', ('je', 'nullExit'),
        '448b43084533c9488bd5488bc8', ('call', 'arraySet')),
    'return': ('488b5c2450488b6c2458488b742460488b7c24684883c440415ec3',),
    'field': ('833b07', ('je', 'chain'), '837b0800', ('jge8', 'fieldPositive')),
    'fieldNegative': ('486343044885ff', ('je', 'nullExit'), '3b4718', ('jae', 'boundsExit'),
        ('rip', '488b15', 'anonymousType'), '488b4cc720', ('call', 'cast'), '8b53084885c0', ('je', 'nullExit'),
        '488364242800f7d24c8b4c24784c8bc5488bc84889742420', ('call', 'anonymousSet'), ('jump8', 'return')),
    'fieldPositive': ('4885f6', ('je', 'nullExit'), ('field8', '488b4e', 'vm', 'fieldInfos'),
        '486343084885c9', ('je', 'nullExit'), '3b4118', ('jae', 'boundsExit'),
        '4c8b74c1204533c0498bce33d2', ('call', 'fieldEqual'), '84c0', ('jne8', 'fieldNew')),
    'fieldReflected': ('486343044885ff', ('je', 'nullExit'), '3b4718', ('jae', 'boundsExit'),
        '4d85f6', ('je', 'nullExit'), '488b54c7204533c9498bce', ('jump', 'reflectedSet')),
    'fieldNew': (('field8', '488b4e', 'vm', 'newFieldInfos'), '4885c9', ('je', 'nullExit'),
        ('rip', '4c8b05', 'instanceDictionary'), '8b5308', ('call', 'dictionaryItem'),
        '48634b044885ff', ('je', 'nullExit'), '3b4f18', ('jae', 'boundsExit'),
        '4885c0', ('je', 'nullExit'), '488b54cf204533c9', ('jump', 'newSet')),
    'chain': ('4885ff', ('je', 'nullExit'), '488bcb48b8abaaaaaaaaaaaa2a492bce48f7e9488bca48d1f9'
        '488bc148c1e83f4803c83b4f18', ('jae', 'boundsExit'), ('rip', '488b15', 'chainType'),
        '488b4ccf20', ('call', 'cast'), '4885c0', ('je', 'nullExit'),
        ('field8', '4c8b50', 'chain', 'FieldIdList'), ('field8', '488b50', 'chain', 'Object'),
        '4d85d2', ('je', 'nullExit'), '4885f6', ('je', 'nullExit'),
        ('field8', '4c8b46', 'vm', 'fieldInfos'), '458b4a18', ('field8', '488b46', 'vm', 'newFieldInfos'),
        '41ffc9837b08ff0f95c148836424380048894424304c894424284c8bc54c89542420',
        ('call', 'chainSet'), ('jump', 'return')),
    'static': ('8b7b044885f6', ('je', 'nullExit'), '85ff', ('jns8', 'staticPositive')),
    'staticNegative': (('field32', '488b9e', 'vm', 'staticFields'), '4885db', ('je', 'nullExit'),
        '488bd5488bcb', ('call', 'assignmentCheck'), 'f7d74c8bc54863d7488bcb',
        ('call', 'managedStore'), ('jump', 'return')),
    'staticPositive': (('field8', '488b4e', 'vm', 'fieldInfos'), '486343044885c9', ('je', 'nullExit'),
        '3b4118', ('jb8', 'staticRow')),
    'boundsExit': (('call', 'boundsFailure'), 'cc'),
    'staticRow': ('488b7cc1204533c0488bcf33d2', ('call', 'fieldEqual'), '84c0', ('jne8', 'staticNew')),
    'staticReflected': ('4885ff', ('je8', 'nullExit'), '4533c9488bcf33d2'),
    'reflectedSet': ('4c8bc5', ('call', 'fieldSet'), ('jump', 'return')),
    'staticNew': (('field8', '488b4e', 'vm', 'newFieldInfos'), '4885c9', ('je8', 'nullExit'),
        ('rip', '4c8b05', 'staticDictionary'), '8b5304', ('call', 'dictionaryItem'),
        '4885c0', ('je8', 'nullExit'), '4533c933d2'),
    'newSet': ('4c8bc5488bc8', ('call', 'newFieldSet'), ('jump', 'return')),
    'stack': ('488b4424784c8bcd4883642428004c8bc7488b5304498bce4889442420', ('call', 'pushObject'), ('jump', 'return')),
    'nullExit': (('call', 'nullFailure'), 'cc'),
}
_NEAR = {'je': '0f84', 'jae': '0f83', 'jump': 'e9'}
_SHORT = {'je8': 0x74, 'jne8': 0x75, 'jge8': 0x7d, 'jump8': 0xeb, 'jns8': 0x79, 'jb8': 0x72}


def _program(base: int, targets: dict[str, int], fields: dict[str, dict[str, int]], cells: dict[str, int], init: dict) -> tuple[bytes, dict[str, int]]:
    p = _Program(base); near = []
    p.add('488bc44889580848896810488970184889782041564883ec40')
    p.rip('803d', _rva(init['flagRva']), b'\x00')
    p.add('498be9488b742470498bf8488bda4c8bf1'); p.branch(0x75, 'dispatch')
    _need(len(init['cellRvas']) == 5, 'initialization: expected finite cell list')
    for cell in init['cellRvas']:
        p.rip('488d0d', _rva(cell)); p.call(targets['typeInitialize'])
    p.rip('c605', _rva(init['flagRva']), b'\x01')
    for label, tokens in _BLOCKS.items():
        p.mark(label)
        for token in tokens:
            if isinstance(token, str):
                p.add(token); continue
            kind, *args = token
            if kind == 'call': p.call(targets[args[0]])
            elif kind == 'rip': p.rip(args[0], cells[args[1]])
            elif kind in ('field8', 'field32'):
                prefix, owner, field = args; offset = fields[owner][field]; p.add(prefix)
                if kind == 'field8': p.byte(offset)
                else: p.add(offset.to_bytes(4, 'little', signed=True))
            elif kind in _SHORT: p.branch(_SHORT[kind], args[0])
            elif kind in _NEAR:
                p.add(_NEAR[kind]); near.append((len(p.raw), args[0])); p.add(bytes(4))
            else: _need(False, 'unknown finite program token')
    for offset, label in near:
        p.raw[offset:offset + 4] = (p.labels[label] - offset - 4).to_bytes(4, 'little', signed=True)
    return p.finish(), {name: base + offset for name, offset in p.labels.items()}


def _field_equal_program(base: int, nonnull_equal: int) -> bytes:
    p = _Program(base)
    p.add('4883ec284c8bc2488bd1493bc8'); p.branch(0x74, 'true')
    p.add('4885c9'); p.branch(0x74, 'false'); p.add('4d85c0'); p.branch(0x75, 'nonnull')
    p.mark('false'); p.add('32c0'); p.mark('return'); p.add('4883c428c3')
    p.mark('true'); p.add('b001'); p.branch(0xeb, 'return')
    p.mark('nonnull'); p.add('33c9'); p.call(nonnull_equal); p.branch(0xeb, 'return')
    return p.finish()


def _claims(spec: dict) -> None:
    _need(spec.get('schema') == 'endfield.ifix-vm-reference-update-rules.v1'
          and spec.get('evidenceBoundary') == 'conditional' and spec.get('executionBoundary') == 'unobserved'
          and spec.get('methodRefs') == _METHOD_REFS and spec.get('helperRefs') == _HELPER_REFS
          and spec.get('valueLayoutRef') == 'constrainedTypeOperand.stackEffect.valueLayout'
          and spec.get('slotBytes') == 12 and spec.get('defaultEffect') == 'return-without-target-request'
          and spec.get('targetBoundary') == 'valid-stable-descriptor-and-storage-with-normal-helper-return'
          and spec.get('chainBoundary') == 'caller-forwarding-only-recursive-mSet-unresolved'
          and spec.get('aliasBoundary') == 'target-values-and-runtime-helper-mutation-unobserved'
          and spec.get('dictionaryBoundary') == 'stored-typed-context-registered-MethodDef-family-runtime-sharing-unresolved',
          'unsupported schema/reference/boundary')
    rows = _named(spec.get('routes', []), _ROUTES, 'routes')
    for name, (target, effect) in _ROUTES.items():
        _need((rows[name].get('target'), rows[name].get('effect')) == (target, effect), name + ': unsupported target expression')
    _need(spec.get('tagMembers') == _TAGS, 'unsupported tag declarations')


def validate_reference_update_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Validate one gated image; root owns prerequisite rule-group validation."""
    _claims(spec)
    members = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.ValueType')}
    _need({name: members.get(name) for name in _TAGS} == _TAGS, 'ValueType dispatch IDs differ')
    fields = _layouts(image, spec['fieldLayouts'], _ref(contract, spec['valueLayoutRef']))
    selected_fields = {'vm': fields['IFix.Core.VirtualMachine'], 'chain': fields['IFix.Core.FieldAddr']}
    targets = {}; bodies = {}; methods = _named(spec['methods'], set(_METHODS) - set(_METHOD_REFS), 'methods')
    for name in _METHODS:
        row = _ref(contract, _METHOD_REFS[name]) if name in _METHOD_REFS else methods[name]
        targets[name], bodies[name] = _identity(image, row, name, extents)
    helpers = _named(spec['helpers'], _HELPERS, 'helpers')
    for name, row in helpers.items():
        target = _rva(row['rva']); size = row['byteCount']
        _need(type(size) is int and 0 < size <= 65536 and extents.get(image.pe.image_base + target) == image.pe.image_base + target + size,
              name + ': exact helper extent differs')
        _hash(image.pe.bytes_at_va(image.pe.image_base + target, size), row, name); targets[name] = target
    for name, path in _HELPER_REFS.items():
        row = _ref(contract, path); target = _rva(row['rva'])
        _hash(image.pe.bytes_at_va(image.pe.image_base + target, row['byteCount']), row, name); targets[name] = target
    usages = _named(spec['usageCells'], _USAGES, 'usages'); definitions = []
    for row in usages.values():
        definition = _usage(image, row)
        if definition is not None: definitions.append(definition)
    _need(len(definitions) == 2 and definitions[0] == definitions[1], 'dictionary: instance/static stored definitions differ')
    _dictionary_target(image, definitions[0], targets['dictionaryItem'])
    expected, labels = _program(targets['update'], targets, selected_fields,
        {name: _rva(row['cellRva']) for name, row in usages.items()}, spec['initialization'])
    _expect(bodies['update'], expected, 'UpdateReference.full-finite-arguments-and-control')
    _expect(bodies['fieldEqual'], _field_equal_program(targets['fieldEqual'], _rva(spec['nonnullFieldEqualityHelperRva'])),
            'fieldEqual.null-comparison')
    # The parent store window includes the guarded element write. Authenticate
    # that instruction too, so an updated hash cannot turn the target request
    # into a write of a different register or descriptor.
    store = _ref(contract, _HELPER_REFS['managedStore'])
    raw = image.pe.bytes_at_va(image.pe.image_base + targets['managedStore'], store['byteCount'])
    _need(len(raw) >= 23 and raw[:7] == bytes.fromhex('4883ec283b5118') and raw[7] == 0x73
          and raw[16:21] == bytes.fromhex('4c8944d120'), 'managedStore: checked replacement element store differs')
    return {'status': 'validated_conditional_reference_update_requests', 'evidenceBoundary': 'conditional',
        'executionBoundary': 'unobserved', 'routes': list(_ROUTES), 'defaultEffect': spec['defaultEffect'],
        'entryRvas': {name: hex(labels[name]) for name in ('stack', 'field', 'static', 'array', 'chain')},
        'fieldInfoNullSelection': 'direct-null-comparison-with-zero-second-operand',
        'targetBoundary': spec['targetBoundary'], 'chainBoundary': spec['chainBoundary'],
        'unresolved': ['runtime-storage-descriptor-and-target-values', 'cast-and-reflection-success',
          'dictionary-result-and-exact-generic-sharing', 'anonymous-set-callee-outcome', 'recursive-mSet-semantics',
          'runtime-helper-alias-mutation', 'actual-execution']}


def validate_selected_reference_update_rules(contract: dict, *, gameassembly: Path, metadata: Path,
                                            spec: dict | None = None) -> dict:
    """Fail closed before opening anything except explicitly selected inputs."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'nativeInputs: selected hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
                                        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated':
        return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.referenceUpdate')
    return validate_reference_update_rules(image, contract['referenceUpdateRules'] if spec is None else spec,
                                           contract, image.mapper.pdata_function_extents(image.pe))
