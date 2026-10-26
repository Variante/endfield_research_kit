"""Authenticate the bounded, non-generic GenericDelegate Action bridge.

The selected constructor stores the VM, method ID and bound object. Its two
receiver flags are both derived from ``anonObj != null``: ``pushSelf`` is a
Boolean and ``extraArgNum`` is the same Boolean widened to Int32. Action()
obtains a Call from Call.Begin(), optionally pushes that object, then calls
Execute(methodId, ref call, extraArgNum, 0). The four-argument Execute overload
forwards the Call's stack fields and the selected unmanagedCodes entry to the
main interpreter. For this bridge, refCount is zero, so argumentBase is unchanged.

These are conditional native program rules, authenticated against explicitly
selected binaries and metadata. They do not establish invocation, factory
selection, receiver contents, a valid method ID, stack availability/capacity,
or successful interpreter completion. Generic Action/Func instantiations are
outside this helper. Addresses and body hashes belong to the reviewed contract.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import (
    enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name,
)


class DelegateBridgeRuleError(ValueError):
    """The selected delegate bridge lacks its reviewed native witness."""


def _number(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _fail(label: str, detail: str) -> None:
    raise DelegateBridgeRuleError(f'delegateBridge.{label}: {detail}')


class _Program:
    """Build a small reviewed x64 program with relocatable calls and branches."""

    def __init__(self, base: int):
        self.base = base
        self.raw = bytearray()
        self.fixups: list[tuple[int, str]] = []
        self.labels: dict[str, int] = {}

    def add(self, raw: str | bytes) -> None:
        self.raw.extend(bytes.fromhex(raw) if isinstance(raw, str) else raw)

    def byte(self, value: int) -> None:
        if not 0 <= value <= 127:
            _fail('layout', f'unsupported positive disp8={value}')
        self.raw.append(value)

    def call(self, target: int) -> None:
        displacement = target - (self.base + len(self.raw) + 5)
        self.add(b'\xe8' + displacement.to_bytes(4, 'little', signed=True))

    def rip(self, prefix: str, target: int, suffix: bytes = b'') -> None:
        raw = bytes.fromhex(prefix)
        displacement = target - (self.base + len(self.raw) + len(raw) + 4 + len(suffix))
        self.add(raw + displacement.to_bytes(4, 'little', signed=True) + suffix)

    def branch(self, opcode: int, label: str) -> None:
        self.add(bytes((opcode, 0)))
        self.fixups.append((len(self.raw) - 1, label))

    def mark(self, label: str) -> None:
        self.labels[label] = len(self.raw)

    def finish(self) -> bytes:
        for offset, label in self.fixups:
            displacement = self.labels[label] - offset - 1
            if not -128 <= displacement <= 127:
                _fail('program', f'unsupported short branch={label}')
            self.raw[offset] = displacement & 255
        return bytes(self.raw)


def _signature(image: Any, method: Any) -> tuple[list[str], list[str], str]:
    table = _number(image.registration['types'])
    parameters = image.metadata.parameters_for(method)
    pointers = [image.pe.u64_at_va(table + p.type_index * 8) for p in parameters]
    return (
        [runtime_type_name(image.pe, image.metadata, pointer) for pointer in pointers],
        [image.metadata.string(p.name_index) for p in parameters],
        runtime_type_name(image.pe, image.metadata, image.pe.u64_at_va(table + method.return_type * 8)),
    )


def _method(image: Any, row: dict[str, Any], extents: dict[int, int], role: str) -> tuple[int, bytes]:
    candidates = [method for owner in image.metadata.types
                  if image.metadata.type_full_name(owner) == row['type']
                  for method in image.metadata.methods_for(owner)
                  if image.metadata.string(method.name_index) == row['method']
                  and method.parameter_count == row['parameterCount']]
    expected = (row['parameterTypes'], row['parameterNames'], row['returnTypeName'])
    candidates = [method for method in candidates if _signature(image, method) == expected]
    if len(candidates) != 1:
        _fail(role, f'expected one metadata signature, actual={len(candidates)}')
    method = candidates[0]
    if bool(method.flags & 0x10) != row['static'] or (method.generic_container_index >= 0) != row['generic']:
        _fail(role, 'static/generic metadata flags differ')
    pointer = image.method_pointer_va(method)
    rva = pointer - image.pe.image_base
    if method.token != _number(row['token']) or rva != _number(row['rva']):
        _fail(role, f"token or registered pointer differs expectedRva={row['rva']} actualRva={rva:#x}")
    end = extents.get(pointer)
    if end is None or end - pointer != row['bodyBytes']:
        _fail(role, f"native extent differs expectedBytes={row['bodyBytes']} actualBytes={None if end is None else end-pointer}")
    raw = image.pe.bytes_at_va(pointer, end-pointer)
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != row['bodySha256'].upper():
        _fail(role, f"native bytes differ expectedSha256={row['bodySha256']} actualSha256={actual}")
    return rva, raw


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    if raw != expected:
        offset = next((index for index, pair in enumerate(zip(raw, expected)) if pair[0] != pair[1]), min(len(raw), len(expected)))
        _fail(label, f'program differs offset={offset:#x} expectedBytes={len(expected)} actualBytes={len(raw)}')


def _layout(image: Any, row: dict[str, Any], role: str) -> dict[str, int]:
    owners = [owner for owner in image.metadata.types if image.metadata.type_full_name(owner) == row['type']]
    if len(owners) != 1:
        _fail(role, f'expected one metadata type, actual={len(owners)}')
    owner = owners[0]
    if bool(owner.bitfield & 1) != row['isValueType']:
        _fail(role, 'value-type metadata flag differs')
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
    actual = {name: offsets.get(name) for name in row['fieldOffsets']}
    if actual != row['fieldOffsets']:
        _fail(role, f"field offsets differ expected={row['fieldOffsets']} actual={actual}")
    return actual


def _constructor_program(base: int, fields: dict[str, int], barrier: int) -> bytes:
    p = _Program(base)
    p.add('4883ec284c8bd9488951'); p.byte(fields['virtualMachine'])
    p.add('4883c1'); p.byte(fields['virtualMachine']); p.add('458bd0'); p.call(barrier)
    p.add('498d4b'); p.byte(fields['anonObj']); p.add('458953'); p.byte(fields['methodId'])
    p.add('4d894b'); p.byte(fields['anonObj']); p.call(barrier)
    p.add('4d85c90f95c0418843'); p.byte(fields['pushSelf'])
    p.add('0fb6c0418943'); p.byte(fields['extraArgNum']); p.add('4883c428c3')
    return p.finish()


def _action_program(base: int, fields: dict[str, int], targets: dict[str, int], null_fail: int) -> bytes:
    p = _Program(base)
    p.add('40534881ec800000000f57c0488bd933c0488d4c245833d248894424500f114424300f11442440')
    p.call(targets['begin'])
    p.add('807b'); p.byte(fields['pushSelf']); p.add('000f10000f114424300f1048100f114c2440f20f104020f20f11442450')
    p.branch(0x74, 'receiverDone')
    p.add('488b53'); p.byte(fields['anonObj']); p.add('488d4c24304533c0'); p.call(targets['pushObject'])
    p.mark('receiverDone')
    p.add('488b4b'); p.byte(fields['virtualMachine']); p.add('4885c9'); p.branch(0x75, 'execute')
    p.call(null_fail); p.add('cc'); p.mark('execute')
    p.add('4883642428004c8d4424308364242000448b4b'); p.byte(fields['extraArgNum'])
    p.add('8b53'); p.byte(fields['methodId']); p.call(targets['executeBridge'])
    p.add('4881c4800000005bc3')
    return p.finish()


def _execute_program(base: int, fields: dict[str, int], codes_offset: int, consumer: int) -> bytes:
    p = _Program(base)
    p.add('48895c2408574883ec50488364244800498bf84c639c2480000000498b00')
    p.add('4863da488b51'); p.byte(codes_offset)
    # r10 = 3*refCount, r8 = argumentBase + 4*r10, hence +12*refCount.
    p.add('4f8d145b4e8d0490488b47'); p.byte(fields['topWriteBack'])
    p.add('4889442440488b47'); p.byte(fields['evaluationStackBase'])
    p.add('488b14da44895c2438895c243044894c24284c8b4f'); p.byte(fields['managedStack'])
    p.add('4889442420'); p.call(consumer)
    p.add('488b5c24604883c4505fc3')
    return p.finish()


def _barrier_program(row: dict[str, Any]) -> bytes:
    p = _Program(_number(row['rva']))
    p.rip('833d', _number(row['enableCellRva']), b'\0')
    p.add('4c8bc1'); p.branch(0x74, 'return')
    p.add('49c1e80c'); p.rip('488d0d', _number(row['bitmapRootRva']))
    p.add('4181e0ffff1f00418bc048c1e8064183e03f488d14c10f0d0a')
    p.mark('retry'); p.add('488b02488bc84c0fabc1f0480fb10a'); p.branch(0x75, 'retry')
    p.mark('return'); p.add('c3')
    return p.finish()


def validate_delegate_bridge_rules(image: Any, spec: dict[str, Any], contract: dict[str, Any],
                                   extents: dict[int, int]) -> dict[str, Any]:
    """Check selected metadata, complete bridge methods and receiver-slot writes.

    The caller must first authenticate contract.nativeInputs against the explicit
    NativeImage paths. ``validate_selected_delegate_bridge_rules`` supplies that
    gate for standalone callers.
    """
    if (spec.get('schema') != 'endfield.ifix-vm-delegate-bridge-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('variant') != 'non-generic-zero-argument-Action'
            or spec.get('receiverRule') != 'pushSelf-and-extraArgNum-equal-anonObj-nonNull'
            or spec.get('refCount') != 0 or spec.get('callObjectHeaderBytes') != 16
            or spec.get('callValueBytes') != 40
            or spec.get('valueLayoutRef') != 'constrainedTypeOperand.stackEffect.valueLayout'
            or spec.get('managedStoreHelperRef') != 'constrainedTypeOperand.stackEffect.managedStackStoreHelper'):
        _fail('claims', 'unsupported schema, receiver, variant or stack claim')
    roles = ('constructor', 'action', 'begin', 'pushObject', 'executeBridge')
    if tuple(row['role'] for row in spec['methods']) != roles:
        _fail('methods', 'missing, reordered or duplicate method roles')
    identities = {
        'constructor': ('IFix.Core.GenericDelegate', '.ctor', ['IFix.Core.VirtualMachine', 'int', 'object'], 'void', False),
        'action': ('IFix.Core.GenericDelegate', 'Action', [], 'void', False),
        'begin': ('IFix.Core.Call', 'Begin', [], 'IFix.Core.Call', True),
        'pushObject': ('IFix.Core.Call', 'PushObject', ['object'], 'void', False),
        'executeBridge': ('IFix.Core.VirtualMachine', 'Execute', ['int', 'IFix.Core.Call', 'int', 'int'], 'void', False),
    }
    methods = {}
    for row in spec['methods']:
        role = row['role']
        identity = (row['type'], row['method'], row['parameterTypes'], row['returnTypeName'], row['static'])
        if identity != identities[role] or row['generic'] or row['parameterCount'] != len(row['parameterTypes']):
            _fail(role, 'unsupported method identity')
        methods[role] = _method(image, row, extents, role)
    if set(spec['fieldLayouts']) != {'genericDelegate', 'call', 'virtualMachine'}:
        _fail('layout', 'missing or unsupported field-layout role')
    expected_fields = {
        'genericDelegate': ('IFix.Core.GenericDelegate', False, {'virtualMachine', 'methodId', 'anonObj', 'pushSelf', 'extraArgNum'}),
        'call': ('IFix.Core.Call', True, {'argumentBase', 'evaluationStackBase', 'managedStack', 'currentTop', 'topWriteBack'}),
        'virtualMachine': ('IFix.Core.VirtualMachine', False, {'unmanagedCodes'}),
    }
    layouts = {}
    for role, row in spec['fieldLayouts'].items():
        if (row['type'], row['isValueType'], set(row['fieldOffsets'])) != expected_fields[role]:
            _fail(role, 'unsupported field layout')
        layouts[role] = _layout(image, row, role)
    call_fields = {name: offset-spec['callObjectHeaderBytes'] for name, offset in layouts['call'].items()}
    if call_fields != dict(argumentBase=0, evaluationStackBase=8, managedStack=16, currentTop=24, topWriteBack=32):
        _fail('call', 'unsupported unboxed Call layout')
    barrier = spec['referenceWriteBarrier']
    barrier_raw = image.pe.bytes_at_va(image.pe.image_base+_number(barrier['rva']), barrier['byteCount'])
    if hashlib.sha256(barrier_raw).hexdigest().upper() != barrier['sha256'].upper():
        _fail('referenceWriteBarrier', 'native bytes differ')
    # This entire leaf program cannot clobber the constructor's r9/r10/r11.
    _expect(barrier_raw, _barrier_program(barrier), 'referenceWriteBarrier')
    targets = {role: value[0] for role, value in methods.items()}
    _expect(methods['constructor'][1], _constructor_program(targets['constructor'], layouts['genericDelegate'], _number(barrier['rva'])), 'constructor')
    _expect(methods['action'][1], _action_program(targets['action'], layouts['genericDelegate'], targets, _number(spec['nullFailureTargetRva'])), 'action')
    consumer = dict(contract['consumer'])
    if (consumer.get('type'), consumer.get('method'), consumer.get('parameterCount')) != ('IFix.Core.VirtualMachine', 'Execute', 8):
        _fail('interpreter', 'unsupported consumer identity')
    consumer.update(parameterTypes=['IFix.Core.Instruction*', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*', 'int', 'int', 'int', 'IFix.Core.Value**'],
                    returnTypeName='IFix.Core.Value*', static=False, generic=False)
    consumer_rva, _ = _method(image, consumer, extents, 'interpreter')
    _expect(methods['executeBridge'][1], _execute_program(targets['executeBridge'], call_fields, layouts['virtualMachine']['unmanagedCodes'], consumer_rva), 'executeBridge')
    value_layout = contract['constrainedTypeOperand']['stackEffect']['valueLayout']
    value_offsets = _layout(image, dict(value_layout, isValueType=True), 'value')
    if (contract['entryHeader']['slotBytes'] != 12
            or value_offsets != {'Type': 16, 'Value1': 20, 'Value2': 24}
            or value_layout['objectMember'] != {'name': 'Object', 'id': 8}):
        _fail('value', 'unsupported Value slot layout')
    members = enum_members(image.metadata, field_defaults(image.metadata), value_layout['enumType'])
    if [row['id'] for row in members if row['name'] == 'Object'] != [8]:
        _fail('value', 'Object enum member differs')
    # PushObject: signed byte-span /12 computes Value1; the managed store uses
    # that index and the input object; currentTop then advances by one slot.
    push_rva, push_raw = methods['pushObject']
    windows = spec['pushObjectWindows']
    if tuple(row['name'] for row in windows) != ('slotIndex', 'slotStores', 'managedStore', 'advance'):
        _fail('pushObject', 'missing, reordered or duplicate slot windows')
    expected_windows = (
        bytes.fromhex('4c8b411848b8abaaaaaaaaaaaa2a4c2b4108488bea49f7e8488bd9488bf248d1fe488bc648c1e83f4803f0'),
        bytes.fromhex('c70008000000488b41184885c0743f897004488b7910'),
        bytes.fromhex('4863d64c8bc5488bcf'),
        bytes.fromhex('488343180c'),
    )
    for row, expected in zip(windows, expected_windows):
        offset = _number(row['rva'])-push_rva
        if not 0 <= offset <= len(push_raw)-len(expected) or row['byteCount'] != len(expected):
            _fail('pushObject.'+row['name'], 'window outside authenticated body')
        _expect(push_raw[offset:offset+len(expected)], expected, 'pushObject.'+row['name'])
    store = contract['constrainedTypeOperand']['stackEffect']['managedStackStoreHelper']
    store_raw = image.pe.bytes_at_va(image.pe.image_base+_number(store['rva']), store['byteCount'])
    if hashlib.sha256(store_raw).hexdigest().upper() != store['sha256'].upper() or store_raw[16:21] != bytes.fromhex('4c8944d120'):
        _fail('managedStore', 'managed array store witness differs')
    site = _number(spec['pushObjectManagedStoreCallRva'])
    offset = site-push_rva
    raw = push_raw[offset:offset+5] if 0 <= offset <= len(push_raw)-5 else b''
    target = site+5+int.from_bytes(raw[1:], 'little', signed=True) if len(raw) == 5 and raw[0] == 0xe8 else None
    if target != _number(store['rva']):
        _fail('managedStore', f"call target differs expected={store['rva']} actual={target}")
    return {
        'status': 'validated_conditional_delegate_bridge', 'evidenceBoundary': 'conditional',
        'executionBoundary': 'unobserved', 'variant': spec['variant'],
        'constructor': 'stores-VM-methodId-anonObj-and-nonNull-receiver-flags',
        'action': 'Call.Begin-optional-bound-receiver-push-Execute',
        'argsCount': 'extraArgNum (0 or 1 on selected constructor path)', 'refCount': 0,
        'unresolved': ['actual-delegate-invocation', 'factory-selection-and-generic-variants',
                       'bound-receiver-and-methodId-validity', 'Call.Begin-stack-availability-and-capacity',
                       'interpreter-entry-and-successful-completion'],
    }


def validate_selected_delegate_bridge_rules(contract: dict[str, Any], *, gameassembly: Path,
                                            metadata: Path) -> dict[str, Any]:
    """Fail closed before opening native evidence, using explicit paths only."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    if not inputs.get('gameAssemblySha256') or not inputs.get('globalMetadataSha256'):
        _fail('nativeInputs', 'selected build hashes are required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
                                         gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated':
        return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.delegateBridge')
    extents = image.mapper.pdata_function_extents(image.pe)
    return validate_delegate_bridge_rules(image, contract['delegateBridgeRules'], contract, extents)
