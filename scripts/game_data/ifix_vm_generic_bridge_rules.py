"""Prove registered generic Action/Func bridges without invoking a delegate.

The parent authenticates the selected inputs, declared generic catalog and
nongeneric bridge. This component joins the nine generic MethodDefs to stored
all-object MethodSpecs and their registered native bodies. These static joins
do not select the context of a delegate created by runtime reflection.

Every body obtains a 40-byte Call from Begin, optionally pushes anonObj when
pushSelf is nonzero, pushes p1..pN in order and requests Execute with the stored
methodId, N+extraArgNum and refCount=0. Func then calls GetObject(offset=0),
queries the last method-generic context entry, and forwards its result with the
captured object to the reference-cast helper. Context preparation/type-query
and cast results are authenticated call boundaries, not interpreted outcomes.

GetObject independently computes argumentBase+signedOffset*12. It reads the
managed reference using that Value's Value1, saves it, clears the physical
slot's evaluation-base-relative managed position and returns the saved object.
It does not inspect the Value tag. Thus its read and clear indexes can differ;
clearing does not erase the saved return reference. Valid storage, helper
mutation, generic sharing, runtime type/argument contents, cast success and
interpreter completion remain unobserved.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

from scripts.game_data.il2cpp.context import generic_method_candidates
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_type_field_offsets


class GenericBridgeRuleError(ValueError):
    """A generic bridge declaration lacks its selected native witness."""


_PARENT_REFS = {name: 'delegateBridgeRules.methods.' + name for name in ('begin', 'pushObject', 'executeBridge')}
_FIELD_TYPES = {'virtualMachine': 'IFix.Core.VirtualMachine', 'methodId': 'int', 'anonObj': 'object',
                'pushSelf': 'bool', 'extraArgNum': 'int'}
_CALL_FIELDS = {'argumentBase': 'IFix.Core.Value*', 'evaluationStackBase': 'IFix.Core.Value*',
                'managedStack': 'object[]', 'currentTop': 'IFix.Core.Value*', 'topWriteBack': 'IFix.Core.Value**'}
_HELPERS = {'contextPrepare', 'contextType', 'referenceCast', 'nullFailure', 'metadataInitialize', 'boundsFailure'}


def _need(ok: bool, label: str) -> None:
    if not ok:
        raise GenericBridgeRuleError('generic-bridge.' + label)


def _rva(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _ref(contract: dict, path: str) -> Any:
    row = contract
    for key in path.split('.'):
        if isinstance(row, list):
            matches = [item for item in row if item.get('role', item.get('name')) == key]
            _need(len(matches) == 1, path + ': missing/ambiguous reference')
            row = matches[0]
        else:
            _need(isinstance(row, dict) and key in row, path + ': missing reference')
            row = row[key]
    _need(isinstance(row, (dict, list)), path + ': malformed reference')
    return row


def _type(image: Any, index: int, *, byref: bool = False) -> str:
    _need(type(index) is int and 0 <= index < image.registration['typesCount'], 'type-index: outside registration')
    pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    _need(len(raw) == 16 and bool(raw[11] & 0x20) == byref, 'type-carrier: byref bit differs')
    return runtime_type_name(image.pe, image.metadata, pointer)


def _body(image: Any, row: dict, extents: dict[int, int], label: str) -> tuple[int, bytes]:
    base = _rva(row['rva']); size = row.get('bodyBytes', row.get('byteCount'))
    _need(type(size) is int and 0 < size <= 65536 and extents.get(image.pe.image_base + base) == image.pe.image_base + base + size,
          label + ': complete native extent differs')
    raw = image.pe.bytes_at_va(image.pe.image_base + base, size)
    actual = hashlib.sha256(raw).hexdigest().upper()
    expected = row.get('bodySha256', row.get('sha256'))
    _need(actual == str(expected).upper(), label + f': body hash differs expected={expected} actual={actual}')
    return base, raw


def _context_type_leaf(image: Any, row: dict, extents: dict[int, int]) -> tuple[int, bytes]:
    """Cover the complete no-unwind leaf: two return paths and one tail jump."""
    base = _rva(row['rva'])
    _need(row.get('extentKind') == 'complete-leaf-control-program' and row.get('bodyBytes') == 20
          and image.pe.image_base + base not in extents, 'contextType: leaf extent differs')
    raw = image.pe.bytes_at_va(image.pe.image_base + base, 20)
    _need(hashlib.sha256(raw).hexdigest().upper() == str(row['bodySha256']).upper(), 'contextType: leaf hash differs')
    expected = bytes.fromhex('f68138010000017405488bc1eb05e9')
    expected += (_rva(row['tailTargetRva']) - base - 19).to_bytes(4, 'little', signed=True) + b'\xc3'
    _expect(raw, expected, 'contextType')
    return base, raw


def _identity(image: Any, row: dict, label: str, extents: dict[int, int]) -> tuple[int, bytes]:
    expected = {
        'begin': ('IFix.Core.Call', 'Begin', [], 'IFix.Core.Call', True, set()),
        'pushObject': ('IFix.Core.Call', 'PushObject', ['object'], 'void', False, set()),
        'executeBridge': ('IFix.Core.VirtualMachine', 'Execute', ['int', 'IFix.Core.Call', 'int', 'int'], 'void', False, {1}),
        'getObject': ('IFix.Core.Call', 'GetObject', ['int'], 'object', False, set()),
    }[label]
    owner, name, params, result, static, byref = expected
    _need((row.get('type'), row.get('method'), row.get('parameterCount')) == (owner, name, len(params))
          and row.get('parameterTypes') == params and row.get('returnTypeName') == result
          and row.get('static') == static and row.get('generic') is False, label + ': named identity differs')
    md = image.metadata
    matches = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
               if md.string(m.name_index) == name and m.parameter_count == len(params)
               and [_type(image, p.type_index, byref=i in byref) for i, p in enumerate(md.parameters_for(m))] == params]
    _need(len(matches) == 1, label + ': exact metadata overload missing/ambiguous')
    method = matches[0]
    _need('methodIndex' not in row or row['methodIndex'] == method.index, label + ': declared method index differs')
    _need(_type(image, method.return_type) == result and bool(method.flags & 0x10) == static
          and method.generic_container_index == -1 and method.token == _rva(row['token']), label + ': return/kind/token differs')
    base, raw = _body(image, row, extents, label)
    _need(image.method_pointer_va(method) == image.pe.image_base + base, label + ': registered pointer differs')
    return base, raw


def _program(base: int, pattern: tuple, targets: dict[str, int]) -> bytes:
    raw = bytearray()
    for item in pattern:
        if isinstance(item, str):
            raw += bytes.fromhex(item)
        else:
            kind, name = item
            _need(kind == 'call', 'program: unsupported grammar token')
            raw += b'\xe8' + (targets[name] - base - len(raw) - 5).to_bytes(4, 'little', signed=True)
    return bytes(raw)


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    offset = next((i for i, pair in enumerate(zip(raw, expected)) if pair[0] != pair[1]), min(len(raw), len(expected)))
    _need(raw == expected, label + f': complete argument/control program differs offset={offset:#x} '
          f'expected={expected[offset:offset+12].hex()} actual={raw[offset:offset+12].hex()} '
          f'expectedBytes={len(expected)} actualBytes={len(raw)}')


def _declaration(spec: dict) -> None:
    _need(spec.get('schema') == 'endfield.ifix-vm-generic-bridge-rules.v1'
          and spec.get('evidenceBoundary') == 'conditional' and spec.get('executionBoundary') == 'unobserved'
          and spec.get('catalogRef') == 'genericDelegateCatalogRules.declaredCatalog'
          and spec.get('parentMethodRefs') == _PARENT_REFS and spec.get('refCount') == 0
          and spec.get('argumentOrder') == 'optional-anonObj-then-p1-through-pN'
          and spec.get('argsCount') == 'parameterCount-plus-extraArgNum'
          and spec.get('instantiationBoundary') == 'registered-all-object-context-runtime-sharing-unobserved'
          and spec.get('resultBoundary') == 'GetObject-offset-zero-then-last-generic-context-type-and-reference-cast'
          and spec.get('getObjectBoundary') == 'read-Value1-managed-index-save-reference-clear-physical-slot-position-return-saved-reference',
          'unsupported schema/claim/boundary')


def validate_generic_bridge_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Authenticate registered generic bridges after the parent's explicit gates."""
    _declaration(spec)
    targets = {}
    for label, path in _PARENT_REFS.items():
        targets[label], _ = _identity(image, _ref(contract, path), label, extents)
    get_base, get_raw = _identity(image, spec['getObjectMethod'], 'getObject', extents)
    targets['getObject'] = get_base
    _need(set(spec.get('helpers', {})) == _HELPERS, 'helpers: missing/unknown declarations')
    for name, row in spec['helpers'].items():
        targets[name], _ = (_context_type_leaf(image, row, extents) if name == 'contextType'
                            else _body(image, row, extents, name))
        _need(row.get('evidenceBoundary') == 'unresolved', name + ': helper outcome must remain unresolved')
    store = _ref(contract, 'constrainedTypeOperand.stackEffect.managedStackStoreHelper')
    targets['managedStore'] = _rva(store['rva'])
    store_raw = image.pe.bytes_at_va(image.pe.image_base + targets['managedStore'], store['byteCount'])
    _need(len(store_raw) == 23 and hashlib.sha256(store_raw).hexdigest().upper() == store['sha256'].upper()
          and store_raw[:7] == bytes.fromhex('4883ec283b5118') and store_raw[7] == 0x73
          and store_raw[16:21] == bytes.fromhex('4c8944d120'), 'managedStore: guarded replacement store window differs')
    init = spec['getObjectInitialization']
    def rip(prefix: str, at: int, target: int, suffix: bytes = b'') -> bytes:
        code = bytes.fromhex(prefix)
        return code + (target - at - len(code) - 4 - len(suffix)).to_bytes(4, 'little', signed=True) + suffix
    expected = (bytes.fromhex('48895c2408574883ec20')
        + rip('803d', get_base+10, _rva(init['flagRva']), b'\x00')
        + bytes.fromhex('488bd94863fa7513')
        + rip('488d0d', get_base+25, _rva(init['cellRva']))
        + _program(get_base+32, (('call','metadataInitialize'),), targets)
        + rip('c605', get_base+37, _rva(init['flagRva']), b'\x01')
        + _program(get_base+44, _GET_OBJECT, targets))
    _expect(get_raw, expected, 'getObject')
    call_layout = _ref(contract, 'delegateBridgeRules.fieldLayouts.call')
    call_owners = [t for t in image.metadata.types if image.metadata.type_full_name(t) == 'IFix.Core.Call']
    _need(len(call_owners) == 1 and call_owners[0].bitfield & 1, 'layout: Call value-type owner differs')
    call_offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, call_owners[0].index)
    _need(call_layout.get('fieldOffsets') == call_offsets == {'argumentBase':16,'evaluationStackBase':24,
          'managedStack':32,'currentTop':40,'topWriteBack':48}, 'layout: Call unboxed fields differ')
    call_fields = {image.metadata.string(f.name_index): f for f in image.metadata.fields_for(call_owners[0])}
    _need(all(name in call_fields and _type(image, call_fields[name].type_index) == typ for name, typ in _CALL_FIELDS.items()),
          'layout: Call field types differ')
    layout = _ref(contract, 'delegateBridgeRules.fieldLayouts.genericDelegate')
    owners = [t for t in image.metadata.types if image.metadata.type_full_name(t) == 'IFix.Core.GenericDelegate']
    _need(len(owners) == 1, 'layout: GenericDelegate owner missing/ambiguous')
    actual = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owners[0].index)
    _need(layout.get('fieldOffsets') == actual == {'virtualMachine':16,'methodId':24,'anonObj':32,'pushSelf':40,'extraArgNum':44},
          'layout: bridge field offsets differ')
    fields = {image.metadata.string(f.name_index): f for f in image.metadata.fields_for(owners[0])}
    _need(all(name in fields and _type(image, fields[name].type_index) == typ for name, typ in _FIELD_TYPES.items()),
          'layout: bridge field types differ')
    rows = spec.get('variants', [])
    mapped = {row.get('name'): row for row in rows}
    _need(len(mapped) == len(rows) and set(mapped) == set(_PATTERNS), 'variants: missing/duplicate/unknown bodies')
    pe, reg, md = image.pe, image.registration, image.metadata
    specs = pe.bytes_at_va(_rva(reg['methodSpecs']), reg['methodSpecsCount'] * 12)
    table = pe.bytes_at_va(_rva(reg['genericMethodTable']), reg['genericMethodTableCount'] * 16)
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    checked = []
    for name, row in mapped.items():
        method_name, count = name[:-1], int(name[-1])
        declarations = [m for m in md.methods_for(owners[0]) if md.string(m.name_index) == method_name and m.parameter_count == count]
        _need(len(declarations) == 1, name + ': catalog definition missing/ambiguous')
        method = declarations[0]
        _need(method.index == row['methodIndex'] and method.token == _rva(row['token'])
              and method.flags & 7 == 6 and not method.flags & 0x10 and method.generic_container_index >= 0,
              name + ': public instance generic definition differs')
        catalog = [r for r in _ref(contract, spec['catalogRef']) if r['method'] == method_name and len(r['parameterTypes']) == count]
        _need(len(catalog) == 1 and _rva(catalog[0]['token']) == method.token, name + ': inherited declared catalog differs')
        index = row['methodSpecIndex']
        _need(type(index) is int and 0 <= index < reg['methodSpecsCount'], name + ': MethodSpec index outside table')
        definition, class_inst, method_inst = struct.unpack_from('<iii', specs, index * 12)
        _need(definition == method.index and class_inst == -1 and method_inst >= 0, name + ': MethodSpec definition/context differs')
        args = image.instantiations.resolve(method_inst).arguments
        _need(len(args) == count + (method_name == 'Func') and all(len(bytes.fromhex(a.raw_type_record_hex)) == 16
              and not bytes.fromhex(a.raw_type_record_hex)[11] & 0x20
              and runtime_type_name(pe, md, a.type_pointer_va) == 'object' for a in args),
              name + ': exact non-byref all-object instantiation differs')
        candidates = generic_method_candidates(table, reg['genericMethodTableCount'], reg['methodSpecsCount'], {index},
            code['genericMethodPointersCount'], code['invokerPointersCount'], source='generic-bridge.'+name,
            offset=_rva(reg['genericMethodTable']))
        _need(len(candidates) == 1 and candidates[0]['tableIndex'] == row['tableIndex']
              and candidates[0]['rawHex'] == row['tableRecordHex'], name + ': exact registered candidate differs')
        pointer = pe.u64_at_va(_rva(code['genericMethodPointers']) + candidates[0]['indices'][0] * 8)
        base, raw = _body(image, row, extents, name)
        _need(pointer == pe.image_base + base, name + ': registered generic body pointer differs')
        _expect(raw, _program(base, _PATTERNS[name], targets), name)
        checked.append({'method':method_name, 'parameterCount':count, 'argsCount':'parameterCount-plus-extraArgNum',
                        'argumentOrder':['optional-anonObj', *['p'+str(i+1) for i in range(count)]], 'refCount':0,
                        'result':'none' if method_name == 'Action' else spec['resultBoundary']})
    return {'status':'validated_conditional_registered_generic_bridges', 'variants':checked,
            'getObjectBoundary':spec['getObjectBoundary'], 'evidenceBoundary':'conditional','executionBoundary':'unobserved',
            'unresolved':['runtime-reflection-selected-instantiation-and-sharing','incoming-receiver-and-arguments',
                          'helper-induced-mutation-and-context-results','result-slot-tag-and-storage','reference-cast-success',
                          'interpreter-completion-and-actual-delegate-invocation']}


_GET_OBJECT = (
    '488b03488d147f488b4b104c8d04904d85c07452496340044885c974493b41187206',
    ('call','boundsFailure'),
    'cc488b7cc1204885c974344c2b430848b8abaaaaaaaaaaaa2a49f7e848d1fa4c8bc249c1e83f4903d04533c0',
    ('call','managedStore'),
    '488b5c2430488bc74883c4205fc3',
    ('call','nullFailure'), 'cc',
)


_PATTERNS = {
    'Action1': (
        '48895c2408574881ec800000004983783800488bfa488bd97508498bc8',
        ('call', 'contextPrepare'),
        '0f57c0488d4c245833c033d20f1144243048894424500f11442440',
        ('call', 'begin'),
        '807b28000f10000f114424300f1048100f114c2440f20f104020f20f114424507411488b5320488d4c24304533c0',
        ('call', 'pushObject'),
        '4533c0488d4c2430488bd7',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d442430836424200041ffc18b5318',
        ('call', 'executeBridge'),
        '488b9c24900000004881c4800000005fc3',
    ),
    'Action2': (
        '48895c24084889742410574881ec800000004983793800498bf8488bf2488bd97508498bc9',
        ('call', 'contextPrepare'),
        '0f57c0488d4c245833c033d20f1144243048894424500f11442440',
        ('call', 'begin'),
        '807b28000f10000f114424300f1048100f114c2440f20f104020f20f114424507411488b5320488d4c24304533c0',
        ('call', 'pushObject'),
        '4533c0488d4c2430488bd6',
        ('call', 'pushObject'),
        '4533c0488d4c2430488bd7',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d44243083642420004183c1028b5318',
        ('call', 'executeBridge'),
        '4c8d9c2480000000498b5b10498b7318498be35fc3',
    ),
    'Action3': (
        '488bc44889580848897010488978184c89702055488bec4881ec80000000488bd9498bf9488b4d30498bf04c8bf248837938007505',
        ('call', 'contextPrepare'),
        '0f57c0488d4dd833c033d20f1145b0488945d00f1145c0',
        ('call', 'begin'),
        '807b28000f10000f1145b00f1048100f114dc0f20f104020f20f1145d07410488b5320488d4db04533c0',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd7',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d45b083642420004183c1038b5318',
        ('call', 'executeBridge'),
        '4c8d9c2480000000498b5b10498b7318498b7b204d8b7328498be35dc3',
    ),
    'Action4': (
        '488bc44889580848897010488978184c89702055488bec4881ec80000000488bd9498bf9488b4d38498bf04c8bf248837938007505',
        ('call', 'contextPrepare'),
        '0f57c0488d4dd833c033d20f1145b0488945d00f1145c0',
        ('call', 'begin'),
        '807b28000f10000f1145b00f1048100f114dc0f20f104020f20f1145d07410488b5320488d4db04533c0',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd7',
        ('call', 'pushObject'),
        '488b5530488d4db04533c0',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d45b083642420004183c1048b5318',
        ('call', 'executeBridge'),
        '4c8d9c2480000000498b5b10498b7318498b7b204d8b7328498be35dc3',
    ),
    'Func0': (
        '48895c2408574881ec8000000048837a3800488bfa488bd97508488bca',
        ('call', 'contextPrepare'),
        '0f57c0488d4c245833c033d20f1144243048894424500f11442440',
        ('call', 'begin'),
        '807b28000f10000f114424300f1048100f114c2440f20f104020f20f114424507411488b5320488d4c24304533c0',
        ('call', 'pushObject'),
        '488b4b104885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d442430448b4b2c8b53188364242000',
        ('call', 'executeBridge'),
        '4533c0488d4c243033d2',
        ('call', 'getObject'),
        '488b4f38488bd8488b09',
        ('call', 'contextType'),
        '488bd0488bcb',
        ('call', 'referenceCast'),
        '488b9c24900000004881c4800000005fc3',
    ),
    'Func1': (
        '48895c24084889742410574881ec800000004983783800498bf8488bf2488bd97508498bc8',
        ('call', 'contextPrepare'),
        '0f57c0488d4c245833c033d20f1144243048894424500f11442440',
        ('call', 'begin'),
        '807b28000f10000f114424300f1048100f114c2440f20f104020f20f114424507411488b5320488d4c24304533c0',
        ('call', 'pushObject'),
        '4533c0488d4c2430488bd6',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d4424308b531841ffc18364242000',
        ('call', 'executeBridge'),
        '4533c0488d4c243033d2',
        ('call', 'getObject'),
        '488b4f38488bd8488b4908',
        ('call', 'contextType'),
        '488bd0488bcb',
        ('call', 'referenceCast'),
        '4c8d9c2480000000498b5b10498b7318498be35fc3',
    ),
    'Func2': (
        '488bc44889580848897010488978184c89702055488bec4881ec800000004983793800498bf9498bf04c8bf2488bd97508498bc9',
        ('call', 'contextPrepare'),
        '0f57c0488d4dd833c033d20f1145b0488945d00f1145c0',
        ('call', 'begin'),
        '807b28000f10000f1145b00f1048100f114dc0f20f104020f20f1145d07410488b5320488d4db04533c0',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd6',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d45b08b53184183c1028364242000',
        ('call', 'executeBridge'),
        '4533c0488d4db033d2',
        ('call', 'getObject'),
        '488b4f38488bd8488b4910',
        ('call', 'contextType'),
        '488bd0488bcb',
        ('call', 'referenceCast'),
        '4c8d9c2480000000498b5b10498b7318498b7b204d8b7328498be35dc3',
    ),
    'Func3': (
        '48895c2408488974241048897c24185541564157488bec4881ec80000000488b7d40498bf14d8bf04c8bfa488bd948837f38007508488bcf',
        ('call', 'contextPrepare'),
        '0f57c0488d4dd833c033d20f1145b0488945d00f1145c0',
        ('call', 'begin'),
        '807b28000f10000f1145b00f1048100f114dc0f20f104020f20f1145d07410488b5320488d4db04533c0',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd7',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd6',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d45b08b53184183c1038364242000',
        ('call', 'executeBridge'),
        '4533c0488d4db033d2',
        ('call', 'getObject'),
        '488b4f38488bd8488b4918',
        ('call', 'contextType'),
        '488bd0488bcb',
        ('call', 'referenceCast'),
        '4c8d9c2480000000498b5b20498b7328498b7b30498be3415f415e5dc3',
    ),
    'Func4': (
        '48895c2408488974241048897c24185541564157488bec4881ec80000000488b7d48498bf14d8bf04c8bfa488bd948837f38007508488bcf',
        ('call', 'contextPrepare'),
        '0f57c0488d4dd833c033d20f1145b0488945d00f1145c0',
        ('call', 'begin'),
        '807b28000f10000f1145b00f1048100f114dc0f20f104020f20f1145d07410488b5320488d4db04533c0',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd7',
        ('call', 'pushObject'),
        '4533c0488d4db0498bd6',
        ('call', 'pushObject'),
        '4533c0488d4db0488bd6',
        ('call', 'pushObject'),
        '488b5540488d4db04533c0',
        ('call', 'pushObject'),
        '488b4b10448b4b2c4885c97506',
        ('call', 'nullFailure'),
        'cc4883642428004c8d45b08b53184183c1048364242000',
        ('call', 'executeBridge'),
        '4533c0488d4db033d2',
        ('call', 'getObject'),
        '488b4f38488bd8488b4920',
        ('call', 'contextType'),
        '488bd0488bcb',
        ('call', 'referenceCast'),
        '4c8d9c2480000000498b5b20498b7328498b7b30498be3415f415e5dc3',
    ),
}
