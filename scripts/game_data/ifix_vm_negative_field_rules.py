"""Authenticate and project negative Ldsfld/Stsfld operands in the selected VM.

Negative signed Operands take a distinct internal-static-field route. An exact
Int32 ADD leaf adds one, and NEG produces the nonnegative index ``~Operand``.
Both branches call checkCctorExecute with that index. Ldsfld fetches staticFields
and staticFieldTypes, calls PushObject at the current top, and advances one slot.
Stsfld converts the preceding slot with ToObject (valueTypeClone=true), stores
its return in staticFields, clears the consumed managed slot, and removes one
slot. These effects are conditional on the selected path returning normally.

The validator checks selected metadata, complete referenced methods, dispatcher
selection, native windows, helper identities and byte-level programs. Callers
must authenticate the explicit native pair and complete Execute body first;
the selected-input wrapper supplies that gate for standalone callers.

Runtime array contents/bounds, initializer dispatch/completion, conversion
outcomes, stack capacity and actual execution remain unobserved. No file-order
loader join is asserted here. Negative Ldfld/Stfld and anonymous-storey field
semantics remain outside this group; the raw anonymous-storey framing reader is
not widened. Projection describes authored negative operands only.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_delegate_rules import _method


class NegativeFieldRuleError(ValueError):
    """A selected negative-field declaration lacks authenticated evidence."""


_HELPER_REFS = {
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'pointerDifference': 'arithmeticWindows.stackPointerSubtract',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'advancePointer': 'basicOpcodeRules.helpers.advancePointer',
}
_TAIL_REFS = {name: 'basicOpcodeRules.sharedWindows.'+name for name in
              ('zeroRegister', 'slotWidth', 'loopState', 'integerStore', 'pushAdvance', 'pushTopCommit', 'pcAdvance')}
_METHOD_REFS = {
    'pushObject': ('reflectionDispatch.methods.evaluationPush', 'PushObject',
                   ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'System.Type']),
    'toObject': ('constrainedTypeOperand.stackEffect.toObjectMethod', 'ToObject',
                 ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'System.Type', 'IFix.Core.VirtualMachine', 'bool']),
}
_CLAIMS = {
    'Ldsfld': ('fetch-staticFields-and-staticFieldTypes-call-PushObject-and-advance-top', 1),
    'Stsfld': ('ToObject-with-clone-store-staticFields-clear-managed-slot-and-rewind-top', -1),
}
_FIELD_TYPES = {'staticFields': 'object[]', 'staticFieldTypes': 'System.Type[]', 'cctors': 'int[]'}
_DIVIDE_SLOT = bytes.fromhex('488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d0')
_EXECUTE_TYPES = ['IFix.Core.Instruction*', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*', 'int', 'int', 'int', 'IFix.Core.Value**']


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _fail(label: str, detail: str) -> None:
    raise NegativeFieldRuleError(f'negative-field.{label}: {detail}')


def _ref(contract: dict[str, Any], path: str) -> dict[str, Any]:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            found = [item for item in row if item.get('name', item.get('role', item.get('opcode'))) == key]
            if len(found) != 1:
                _fail('references', f'missing or ambiguous {path}')
            row = found[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            _fail('references', f'missing {path}')
    if not isinstance(row, dict):
        _fail('references', f'unsupported {path}')
    return row


def _slice(raw: bytes, base: int, site: int, size: int, label: str) -> bytes:
    offset = site-base
    if size < 1 or not 0 <= offset <= len(raw)-size:
        _fail(label, f'outside authenticated body rva={site:#x} byteCount={size}')
    return raw[offset:offset+size]


def _hash(raw: bytes, row: dict[str, Any], label: str) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != row['sha256'].upper() or ('hex' in row and raw != bytes.fromhex(row['hex'])):
        _fail(label, f"native bytes differ expectedSha256={row['sha256']} actualSha256={actual}")


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    if raw != expected:
        offset = next((i for i, pair in enumerate(zip(raw, expected)) if pair[0] != pair[1]), min(len(raw), len(expected)))
        _fail(label, f'program differs offset={offset:#x} expectedBytes={len(expected)} actualBytes={len(raw)}')


def _relative(program: _Program, prefix: str, target: int) -> None:
    opcode = bytes.fromhex(prefix)
    displacement = target-(program.base+len(program.raw)+len(opcode)+4)
    program.add(opcode+displacement.to_bytes(4, 'little', signed=True))


def _rules(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (spec.get('schema') != 'endfield.ifix-vm-negative-field-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('scope') != 'negative-static-fields-only'
            or spec.get('slotBytes') != 12 or spec.get('instructionBytes') != 8
            or spec.get('fileTableJoinBoundary') != 'not-asserted'
            or spec.get('instanceFieldBoundary') != 'negative-Ldfld-Stfld-and-anonymous-storey-semantics-unresolved'
            or spec.get('initializerBoundary') != 'callee-internal-dispatch-and-completion-unresolved'
            or spec.get('conversionBoundary') != 'result-tag-and-conversion-outcome-unobserved'):
        _fail('claims', 'unsupported schema, scope or boundary')
    rows = spec.get('rules', [])
    rules = {row.get('opcode'): row for row in rows}
    if len(rows) != len(rules) or set(rules) != set(_CLAIMS):
        _fail('rules', 'missing, duplicate or unsupported opcode rule')
    for name, row in rules.items():
        if (row.get('selectedWhen') != 'signed-Operand-negative'
                or row.get('operandMeaning') != 'bitwise-complement-index-of-internal-static-field'
                or (row.get('effect'), row.get('stackDeltaSlots')) != _CLAIMS[name]
                or row.get('nonnegativeTargetRef') != 'tableOperandClaims.'+name):
            _fail(name, 'unsupported selection, operand or stack claim')
    return rules


def _vm_fields(image: Any, spec: dict[str, Any]) -> dict[str, int]:
    row = spec['vmFields']
    if row.get('type') != 'IFix.Core.VirtualMachine' or set(row.get('fields', {})) != set(_FIELD_TYPES):
        _fail('fields', 'unsupported owner or field set')
    md, pe = image.metadata, image.pe
    owners = [owner for owner in md.types if md.type_full_name(owner) == row['type']]
    if len(owners) != 1:
        _fail('fields', f'expected one metadata owner, actual={len(owners)}')
    owner = owners[0]
    offsets = runtime_type_field_offsets(md, pe, image.registration, owner.index)
    fields = {md.string(field.name_index): field for field in md.fields_for(owner)}
    result = {}
    for name, expected_type in _FIELD_TYPES.items():
        declared = row['fields'][name]
        field = fields.get(name)
        if field is None or declared.get('type') != expected_type or offsets.get(name) != declared.get('offset'):
            _fail('fields.'+name, f"layout differs expectedOffset={declared.get('offset')} actualOffset={offsets.get(name)}")
        pointer = pe.u64_at_va(_rva(image.registration['types'])+field.type_index*8)
        if runtime_type_name(pe, md, pointer) != expected_type:
            _fail('fields.'+name, 'metadata field type differs')
        result[name] = declared['offset']
    return result


def _load_program(base: int, nonnegative: int, fields: dict[str, int], targets: dict[str, int], push_tail: int) -> bytes:
    p = _Program(base)
    p.add('498bce'); p.call(targets['nullCheck'])
    p.add('49637e04413bfd'); _relative(p, '0f8d', nonnegative)
    p.add('ba010000008bcf'); p.call(targets['int32Add']); p.add('8bd8f7db')
    p.add('4c896c2428488b84241004000048894424204d8bcf4d8bc48bd34c8bb424f0030000498bce')
    p.call(targets['checkCctor'])
    p.add('498bbe'); p.add(fields['staticFields'].to_bytes(4, 'little'))
    p.add('488bcf'); p.call(targets['nullCheck']); p.add('4863d3488bcf'); p.call(targets['arrayFetch'])
    p.add('488bf0498b7e'); p.byte(fields['staticFieldTypes'])
    p.add('488bcf'); p.call(targets['nullCheck']); p.add('4863d3488bcf'); p.call(targets['arrayFetch'])
    p.add('4c896c242848894424204c8bce4d8bc7498bd4488b8c2410040000')
    p.call(targets['pushObject']); _relative(p, 'e9', push_tail)
    return p.finish()


def _store_program(base: int, nonnegative: int, fields: dict[str, int], targets: dict[str, int], store_tail: int) -> bytes:
    p = _Program(base)
    p.add('498bce'); p.call(targets['nullCheck'])
    p.add('4d637604453bf5'); _relative(p, '0f8d', nonnegative)
    p.add('ba01000000418bce'); p.call(targets['int32Add']); p.add('8bf8f7df')
    p.add('4c896c242848895c24204d8bcf4d8bc48bd74c8bb424f0030000498bce'); p.call(targets['checkCctor'])
    p.add('498bb6'); p.add(fields['staticFields'].to_bytes(4, 'little'))
    p.add('498b5e'); p.byte(fields['staticFieldTypes']); p.add('488bcb'); p.call(targets['nullCheck'])
    p.add('4863d7488bcb'); p.call(targets['arrayFetch']); p.add('488bd8ba0c000000498bcc')
    p.call(targets['subtractSlot'])
    p.add('4c896c2430c6442428014c897424204c8bcb4d8bc7488bd0488b8c2410040000')
    p.call(targets['toObject']); p.add('488bd8488bce'); p.call(targets['nullCheck'])
    p.add('488bd3488bce'); p.call(targets['assignmentCheck'])
    p.add('4863d74c8bc3488bce'); p.call(targets['managedStore']); _relative(p, 'e9', store_tail)
    return p.finish()


def _pop_program(base: int, targets: dict[str, int], top_subtract: int) -> bytes:
    p = _Program(base)
    p.add('be0c0000008bd6498bcc'); p.call(targets['subtractSlot'])
    p.add('488b9c2410040000488bd3488bc8'); p.call(targets['pointerDifference'])
    p.add('498bcf'); p.call(targets['nullCheck']); p.add('33d2498bcf'); p.call(targets['assignmentCheck'])
    p.add('8bd6498bcc'); p.call(targets['subtractSlot']); p.add('488bd3488bc8'); p.call(targets['pointerDifference'])
    p.add(_DIVIDE_SLOT); p.add('4533c0498bcf'); p.call(targets['managedStore']); _relative(p, 'e9', top_subtract)
    return p.finish()


def validate_negative_field_rules(image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
                                  opcode_ids: dict[str, int], contract: dict[str, Any],
                                  extents: dict[int, int]) -> dict[str, Any]:
    """Authenticate the two negative static routes after the selected build gate."""
    rules = _rules(spec)
    if spec.get('helperRefs') != _HELPER_REFS or spec.get('tailRefs') != _TAIL_REFS:
        _fail('references', 'unsupported parent helper or tail references')
    fields = _vm_fields(image, spec)
    targets = {}
    for name, path in _HELPER_REFS.items():
        helper = _ref(contract, path)
        raw = image.pe.bytes_at_va(image.pe.image_base+_rva(helper['rva']), helper['byteCount'])
        _hash(raw, helper, 'helpers.'+name)
        targets[name] = _rva(helper['rva'])
    new_helpers = {row.get('name'): row for row in spec['helpers']}
    if len(new_helpers) != len(spec['helpers']) or set(new_helpers) != {'int32Add', 'nullCheck'}:
        _fail('helpers', 'missing, duplicate or unsupported helpers')
    for name, helper in new_helpers.items():
        raw = image.pe.bytes_at_va(image.pe.image_base+_rva(helper['rva']), helper['byteCount'])
        _hash(raw, helper, 'helpers.'+name)
        if name == 'int32Add':
            _expect(raw, bytes.fromhex('8d0411c3'), 'helpers.int32Add')
        elif len(raw) != 20 or raw[:14] != bytes.fromhex('4883ec284885c974054883c428c3') or raw[14] != 0xe8 or raw[-1] != 0xcc:
            _fail('helpers.nullCheck', 'unsupported non-null normal-return leaf')
        targets[name] = _rva(helper['rva'])
    if spec.get('methodRefs') != {name: values[0] for name, values in _METHOD_REFS.items()}:
        _fail('methods', 'unsupported parent method references')
    for role, (path, name, params) in _METHOD_REFS.items():
        row = dict(_ref(contract, path), parameterTypes=params)
        if (row.get('type'), row.get('method'), row.get('parameterCount')) != ('IFix.Core.EvaluationStackOperation', name, len(params)):
            _fail('methods.'+role, 'unsupported method identity')
        targets[role] = _method(image, row, extents)
    cctor = spec['checkCctorMethod']
    if (cctor.get('type'), cctor.get('method'), cctor.get('parameterTypes')) != ('IFix.Core.VirtualMachine', 'checkCctorExecute', ['int', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*']):
        _fail('methods.checkCctor', 'unsupported initializer method identity')
    targets['checkCctor'] = _method(image, cctor, extents)
    cctor_raw = image.pe.bytes_at_va(image.pe.image_base+targets['checkCctor'], cctor['bodyBytes'])
    _expect(_slice(cctor_raw, targets['checkCctor'], _rva(spec['cctorTableReadRva']), 7, 'cctorTableRead'),
            bytes.fromhex('488b89')+fields['cctors'].to_bytes(4, 'little'), 'cctorTableRead')
    tails = {name: _ref(contract, path) for name, path in _TAIL_REFS.items()}
    for name, row in tails.items():
        _hash(_slice(body, body_rva, _rva(row['rva']), row['byteCount'], 'tails.'+name), row, 'tails.'+name)
    _expect(_slice(body, body_rva, _rva(tails['zeroRegister']['rva']), 3, 'zeroRegister'), bytes.fromhex('4533ed'), 'zeroRegister')
    _expect(_slice(body, body_rva, _rva(tails['slotWidth']['rva']), 5, 'slotWidth'), bytes.fromhex('be0c000000'), 'slotWidth')
    shared = {row.get('name'): row for row in spec['sharedWindows']}
    if len(shared) != len(spec['sharedWindows']) or set(shared) != {'pushTail', 'popTail', 'topSubtract'}:
        _fail('sharedWindows', 'missing, duplicate or unsupported tail windows')
    for name, row in shared.items():
        _hash(_slice(body, body_rva, _rva(row['rva']), row['byteCount'], name), row, name)
    p = _Program(_rva(shared['pushTail']['rva']))
    p.add('be0c000000'); _relative(p, 'e9', _rva(tails['integerStore']['rva'])+25)
    _expect(bytes.fromhex(shared['pushTail']['hex']), p.finish(), 'pushTail')
    _expect(bytes.fromhex(shared['popTail']['hex']), _pop_program(_rva(shared['popTail']['rva']), targets, _rva(shared['topSubtract']['rva'])), 'popTail')
    p = _Program(_rva(shared['topSubtract']['rva']))
    p.add('8bd6498bcc'); p.call(targets['subtractSlot']); _relative(p, 'e9', _rva(tails['pushTopCommit']['rva']))
    _expect(bytes.fromhex(shared['topSubtract']['hex']), p.finish(), 'topSubtract')
    p = _Program(_rva(tails['integerStore']['rva'])+25)
    p.add('498bcc'); _relative(p, 'e9', _rva(tails['pushAdvance']['rva']))
    _expect(_slice(body, body_rva, p.base, len(p.raw), 'pushForward'), p.finish(), 'pushForward')
    p = _Program(_rva(tails['pushAdvance']['rva']))
    p.add('8bd6'); p.call(targets['advancePointer']); _relative(p, 'e9', _rva(tails['pushTopCommit']['rva']))
    _expect(_slice(body, body_rva, p.base, len(p.raw), 'pushAdvance'), p.finish(), 'pushAdvance')
    checked = []
    for name, row in rules.items():
        if row['opcodeId'] != opcode_ids.get(name):
            _fail(name, 'opcode enum ID differs')
        entry = resolve_dispatch_entry(body, body_rva, _rva(contract['basicOpcodeRules']['dispatchStartRva']), opcode_ids[name])
        if entry != _rva(row['entryRva']):
            _fail(name, f"dispatcher entry differs expected={row['entryRva']} actual={entry:#x}")
        parent = _ref(contract, row['nonnegativeTargetRef'])
        if parent.get('selectedWhen') != 'nonnegativeOperand' or parent.get('opcodeId') != row['opcodeId']:
            _fail(name, 'nonnegative selector reference differs')
        nonnegative = _rva(row['nonnegativeTargetRva'])
        if name == 'Ldsfld':
            _expect(_slice(body, body_rva, nonnegative, 8, 'Ldsfld.nonnegativeVmRestore'),
                    bytes.fromhex('4c8bb424f0030000'), 'Ldsfld.nonnegativeVmRestore')
            if nonnegative+8 != _rva(parent['tableReadRva']):
                _fail(name, 'nonnegative VM restore does not reach the parent field read')
        elif nonnegative != _rva(parent['tableReadRva']):
            _fail(name, 'nonnegative target differs from the parent field read')
        window = row['window']
        if _rva(window['rva']) != entry:
            _fail(name, 'window is not the selected dispatch entry')
        raw = _slice(body, body_rva, entry, window['byteCount'], name)
        _hash(raw, window, name)
        expected = (_load_program(entry, nonnegative, fields, targets, _rva(shared['pushTail']['rva'])) if name == 'Ldsfld'
                    else _store_program(entry, nonnegative, fields, targets, _rva(spec['storePopJoinRva'])))
        _expect(raw, expected, name)
        if name == 'Stsfld':
            # The intermediate shared entry is an unconditional short jump to
            # popTail. It is shared with the reflection-positive store path.
            site = _rva(spec['storePopJoinRva'])
            displacement = _rva(shared['popTail']['rva'])-site-2
            if not -128 <= displacement <= 127:
                _fail('storePopJoin', 'unsupported short jump distance')
            _expect(_slice(body, body_rva, site, 2, 'storePopJoin'), b'\xeb'+displacement.to_bytes(1, 'little', signed=True), 'storePopJoin')
        checked.append(dict(opcode=name, opcodeId=row['opcodeId'], entryRva=hex(entry), stackDeltaSlots=row['stackDeltaSlots']))
    return {
        'status': 'validated_conditional_negative_static_fields', 'entries': checked,
        'operandMeaning': 'signed-negative-Operand -> -(Operand+1) -> internal static field index',
        'runtimeTables': ['staticFields', 'staticFieldTypes', 'cctors'],
        'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
        'fileTableJoinBoundary': 'not-asserted',
        'unresolved': ['runtime-static-array-values-and-bounds', 'initializer-dispatch-and-completion',
                       'conversion-result-and-tag', 'stack-availability-and-capacity', 'actual-execution',
                       'negative-instance-field-and-anonymous-storey-semantics'],
    }


def project_negative_field_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Project authored static negatives; the caller retains the passing native gate."""
    rules = _rules(spec)
    projected = []
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name = instruction['name']
            if name not in rules:
                continue
            rule = rules[name]
            if instruction['opcode'] != rule['opcodeId']:
                _fail(name, 'decoded opcode differs from rule')
            operand = instruction['operandUnsigned']
            if type(operand) is not int or not 0 <= operand <= 0xffffffff:
                _fail(name, 'invalid unsigned Int32 operand')
            signed = operand if operand < 0x80000000 else operand-0x100000000
            if 'operandSigned' in instruction and (type(instruction['operandSigned']) is not int or instruction['operandSigned'] != signed):
                _fail(name, f"inconsistent signed Int32 operand expected={signed} actual={instruction['operandSigned']}")
            if operand < 0x80000000:
                continue
            projected.append({
                'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'], 'offset': instruction['offset'],
                'opcode': name, 'operandUnsigned': operand, 'operandSigned': signed,
                'internalStaticFieldIndex': -signed-1, 'runtimeTables': ['staticFields', 'staticFieldTypes', 'cctors'],
                'effect': rule['effect'], 'stackDeltaSlots': rule['stackDeltaSlots'], 'normalNextInstructionDelta': 1,
                'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved', 'fileTableJoinBoundary': 'not-asserted',
                'initializerBoundary': spec['initializerBoundary'], 'conversionBoundary': spec['conversionBoundary'],
                'runtimeSelectionBoundary': 'static-array-bounds-values-and-stack-unobserved',
            })
    return projected


def validate_selected_negative_field_rules(contract: dict[str, Any], *, gameassembly: Path,
                                           metadata: Path) -> dict[str, Any]:
    """Authenticate only explicitly selected inputs, then validate selected routes."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    if not inputs.get('gameAssemblySha256') or not inputs.get('globalMetadataSha256'):
        _fail('nativeInputs', 'selected native hashes are required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated':
        return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.negativeFields')
    extents = image.mapper.pdata_function_extents(image.pe)
    consumer = dict(contract['consumer'], parameterTypes=_EXECUTE_TYPES)
    if (consumer.get('type'), consumer.get('method'), consumer.get('parameterCount')) != ('IFix.Core.VirtualMachine', 'Execute', 8):
        _fail('consumer', 'unsupported interpreter identity')
    base = _method(image, consumer, extents)
    body = image.pe.bytes_at_va(image.pe.image_base+base, consumer['bodyBytes'])
    ids = {row['name']: row['id'] for row in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.Code')}
    return validate_negative_field_rules(image, contract['negativeFieldRules'], body, base, ids, contract, extents)
