"""Authenticate complete selected Initobj and Constrained caller programs.

Initobj rewinds evaluation top by one slot, selects externTypes using the signed
Operand, requests Activator.CreateInstance(Type), and forwards its result and
the selected Type to UpdateReference. On normal return it clears the consumed
slot's physical managed cell only when that slot's tag is at least Object (8).
The reference tag and payload are otherwise left to the updater; its target
selection remains owned by referenceUpdateRules.

Constrained's selected dispatcher guard leaves ECX equal to one. Its first
pointer subtraction therefore requests the preceding eight-byte instruction.
That instruction's signed Operand selects top - 12 - Operand*12. The caller
requests ToObject with clone=true, writes the returned object into the selected
slot's physical managed cell, then writes that index and Object tag to the slot.
It leaves evaluation top unchanged. Both callers normally advance one authored
instruction; no adjacency, patch loading, invocation or runtime values are
inferred. Storage stability, helper returns, clone/update effects, aliasing and
exception transfer remain conditional on their separately owned dependencies.

Only relocatable native grammars live here. Named identities, hashes and native
addresses are inherited from the parent contract or the reviewed caller group.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _slice, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier, _signature
from scripts.game_data.ifix_vm_indirect_opcode_rules import _carrier_label
from scripts.game_data.ifix_vm_conversion_opcode_rules import _value_layout
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry


class InitConstrainedRuleError(ValueError):
    """A selected caller claim lacks its reviewed native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise InitConstrainedRuleError('init-constrained.' + detail)


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k)) is type(v) and spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    _need(set(spec.get('rules', {})) == set(_RULES) and set(spec.get('blocks', {})) == set(_PROGRAMS), 'rule/block set differs')
    for name, expected in _RULES.items():
        row = spec['rules'][name]
        _need(type(row.get('opcodeId')) is int and all(type(row.get(k)) is type(v) and row.get(k) == v for k, v in expected.items()), 'rule recipe differs: ' + name)


def _program(tokens: tuple, at: int, targets: dict[str, int]) -> bytes:
    p = _Program(at)
    for token in tokens:
        if isinstance(token, str): p.add(token); continue
        kind, *args = token
        if kind == 'call': p.call(targets[args[0]])
        elif kind == 'branch':
            prefix = bytes.fromhex(args[0]); width = 1 if len(prefix) == 1 and prefix != b'\xe9' else 4
            p.add(prefix + (targets[args[1]] - (at + len(p.raw) + len(prefix) + width)).to_bytes(width, 'little', signed=True))
        else: _need(False, 'unknown finite token')
    return p.finish()


def _layouts(image: Any, contract: dict) -> None:
    _value_layout(image, contract); md = image.metadata
    for ownername, value_type, fields in [
        ('IFix.Core.Instruction', True, {'Code': ('IFix.Core.Code', 16), 'Operand': ('int', 20)}),
        ('IFix.Core.VirtualMachine', False, {'externTypes': ('System.Type[]', 72)}),
    ]:
        owners = [t for t in md.types if md.type_full_name(t) == ownername]
        _need(len(owners) == 1 and bool(owners[0].bitfield & 1) == value_type, 'field owner differs: ' + ownername)
        owner = owners[0]; offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index)
        definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
        for name, (typ, offset) in fields.items():
            definition = definitions.get(name)
            _need(definition is not None and offsets.get(name) == offset and _type(image, definition.type_index) == typ, 'named field differs: ' + ownername + '.' + name)
            pointer = image.pe.u64_at_va(_rva(image.registration['types']) + definition.type_index * 8)
            raw = image.pe.bytes_at_va(pointer, 16)
            _need(not int.from_bytes(raw[8:10], 'little') & 0x10, 'static field differs: ' + name)
            if name == 'externTypes': _carrier(image, pointer, typ)
            else: _need(raw[10] == (0x11 if name == 'Code' else 0x08), 'stored Instruction carrier kind differs: ' + name)
        if ownername == 'IFix.Core.Instruction': _need(set(definitions) == set(fields) and offsets == {k: v[1] for k, v in fields.items()}, 'Instruction stored layout differs')
    _need(type(contract['fieldOffsets']['externTypes']) is int and contract['fieldOffsets']['externTypes'] == 72, 'inherited externTypes offset differs')
    tags = {r['name']: r['id'] for r in enum_members(md, field_defaults(md), 'IFix.Core.ValueType')}
    _need(type(tags.get('Object')) is int and tags['Object'] == 8, 'Object tag differs')


def _method(image: Any, row: dict, identity: tuple, role: str, extents: dict[int, int]) -> int:
    normalized = dict(row)
    _need(type(row.get('parameterCount')) is int, 'declared method count differs: ' + role)
    for key, value in [('returnTypeName', identity[3]), ('static', identity[4]), ('generic', False)]:
        if key in row: _need(type(row[key]) is type(value) and _carrier_label(row[key]) == value, 'method declaration differs: ' + role + '.' + key)
    if 'parameterTypes' in row: _need(type(row['parameterTypes']) is list and [_carrier_label(t) for t in row['parameterTypes']] == identity[2], 'declared method parameters differ: ' + role)
    _signature(image, identity)
    at = _identity(image, normalized, identity, role, extents, body_required=role != 'createInstance')
    if role == 'createInstance':
        raw = bytes.fromhex(row['entryBytes'])
        _need(0 < len(raw) <= 32, 'Activator entry window unbounded')
        _expect(image.pe.bytes_at_va(image.pe.image_base + at, len(raw)), raw, 'Activator inherited entry')
    return at


def validate_init_constrained_rules(image: Any, spec: dict, body: bytes, body_rva: int, opcode_ids: dict[str, int], contract: dict, extents: dict[int, int]) -> dict:
    """Authenticate within the parent's selected image and complete Execute body."""
    _claims(spec); _layouts(image, contract); targets = {}
    for role, identity in _METHODS.items(): targets[role] = _method(image, _ref(contract, _CLAIMS['methodRefs'][role]), identity, role, extents)
    for role, path in _CLAIMS['helperRefs'].items():
        row = _ref(contract, path); count = row['byteCount']; at = _rva(row['rva'])
        _need(type(count) is int and 0 < count <= 4096, 'helper window differs: ' + role)
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    for role, shape in _LEAVES.items(): _expect(image.pe.bytes_at_va(image.pe.image_base + targets[role], len(bytes.fromhex(shape))), bytes.fromhex(shape), role)
    for role, path in _CLAIMS['tailRefs'].items():
        row = _ref(contract, path); count = row['byteCount']; at = _rva(row['rva'])
        _need(type(count) is int and 0 < count <= 4096, 'tail window differs: ' + role)
        _hash(_slice(body, body_rva, at, count, role), row, role); targets[role] = at
    targets['restorePc'] = targets['pcAdvance'] - 5
    _expect(_slice(body, body_rva, targets['restorePc'], 5, 'restorePc'), bytes.fromhex('be0c000000'), 'restorePc')
    _expect(_slice(body, body_rva, targets['popCommit'], 10, 'popCommit'), _program(('4c89642460', ('branch', 'e9', 'pcAdvance')), targets['popCommit'], targets), 'popCommit')
    for role, shape in [('zeroRegister', '4533ed'), ('slotWidth', 'be0c000000')]:
        row = _ref(contract, 'basicOpcodeRules.sharedWindows.' + role); at = _rva(row['rva'])
        _hash(_slice(body, body_rva, at, row['byteCount'], role), row, role)
        _expect(_slice(body, body_rva, at, row['byteCount'], role), bytes.fromhex(shape), role)
    targets.update({name: _rva(row['rva']) for name, row in spec['blocks'].items()})
    for name, row in spec['blocks'].items():
        at = targets[name]; count = row['byteCount']; _need(type(count) is int and 0 < count <= 4096, 'block extent differs: ' + name)
        raw = _slice(body, body_rva, at, count, name); _hash(raw, row, name)
        _expect(raw, _program(_PROGRAMS[name], at, targets), name)
        _need(row.get('next') == _NEXT[name], 'graph continuation differs: ' + name)
        if _NEXT[name] is not None: _need(at + count == targets[_NEXT[name]], 'noncontiguous fallthrough: ' + name)
    actual = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.Code')}
    _need(actual == opcode_ids, 'Code enum differs')
    dispatch = contract['dispatchRules']; ex = dispatch['extensions']; entries = {_rva(r['entryRva']) for r in dispatch['entryPoints']}
    for name, row in spec['rules'].items():
        _need(row['opcodeId'] == actual[name], 'Code ID differs: ' + name)
        entry = resolve_selected_dispatch_entry(body, body_rva, _rva(contract['basicOpcodeRules']['dispatchStartRva']), actual[name], zero_compare_rva=_rva(ex['zeroCompare']['rva']), sub_esi_rva=_rva(ex['subEsi']['rva']), entry_rvas=entries)
        _need(entry == targets[row['entryBlock']], 'selected entry differs: ' + name)
    return dict(status='validated_conditional_init_constrained_rules', ruleCount=2, finiteBlockCount=len(_PROGRAMS), rules=project_init_constrained_rules(None, spec), evidenceBoundary='conditional', executionBoundary='unobserved')


def project_init_constrained_rules(instructions: list[dict] | None, spec: dict) -> list[dict]:
    """Project requested Type indexes without inventing previous-instruction data."""
    _claims(spec); result = []; selected = [dict(opcode=n, **r) for n, r in spec['rules'].items()] if instructions is None else instructions
    for ins in selected:
        name = ins.get('opcode')
        if name not in _RULES: continue
        row = spec['rules'][name]; _need(type(ins.get('opcodeId')) is int and ins['opcodeId'] == row['opcodeId'], 'authored Code ID differs: ' + name)
        extra = {}
        if instructions is not None:
            operand = ins.get('operand'); _need(type(operand) is int and 0 <= operand <= 0xffffffff, 'invalid authored Int32 operand: ' + name)
            signed = operand if operand < 0x80000000 else operand - 0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned'] == signed, 'inconsistent signed operand: ' + name)
            extra = dict(operandUnsigned=operand, operandSigned=signed, externTypeIndex=signed)
        result.append(dict(opcode=name, opcodeId=row['opcodeId'], **extra, **_RULES[name], normalNextInstructionDelta=1, runtimeResult='unobserved', evidenceBoundary='conditional', executionBoundary='unobserved', **{k: spec[k] for k in ('calleeBoundary', 'storageBoundary', 'aliasBoundary', 'exceptionBoundary', 'fileTableJoinBoundary')}))
    return result


def validate_selected_init_constrained_rules(contract: dict, *, gameassembly: Path | None, metadata: Path | None, spec: dict | None = None) -> dict:
    """Fail closed before opening any image when explicit selected inputs fail."""
    if gameassembly is None or metadata is None: return dict(status='missing', detail='explicit native paths required', rules=[])
    inputs = contract['nativeInputs']; _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'native hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return dict(status=gate.status, detail=gate.detail, rules=[])
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.init-constrained'); extents = image.mapper.pdata_function_extents(image.pe)
    at = _identity(image, contract['consumer'], ('IFix.Core.VirtualMachine', 'Execute', _EXECUTE_TYPES, 'IFix.Core.Value*', False), 'Execute', extents)
    body = image.pe.bytes_at_va(image.pe.image_base + at, contract['consumer']['bodyBytes'])
    ids = {r['name']: r['id'] for r in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.Code')}
    return validate_init_constrained_rules(image, contract['initConstrainedRules'] if spec is None else spec, body, at, ids, contract, extents)


_CLAIMS = dict(
    schema='endfield.ifix-vm-init-constrained-rules.v1', evidenceBoundary='conditional', executionBoundary='unobserved',
    scope='complete-Initobj-Constrained-caller-programs', slotBytes=12, instructionBytes=8,
    calleeBoundary='Activator-and-ToObject-results-and-UpdateReference-target-effects-remain-owned-and-unobserved',
    storageBoundary='valid-stable-instruction-slots-evaluation-storage-managed-array-and-externTypes;normal-returns-required',
    aliasBoundary='runtime-storage-overlap-and-callee-mutation-unobserved', exceptionBoundary='helper-exception-transfer-and-external-EH-unobserved',
    fileTableJoinBoundary='ordered-externTypes-loader-owned-by-parent;anonymousStoreyInfos-framing-not-asserted',
    methodRefs=dict(createInstance='initobjStackEffect.createInstanceMethod', updateReference='initobjStackEffect.updateReferenceMethod', toObject='constrainedTypeOperand.stackEffect.toObjectMethod'),
    helperRefs=dict(subtractSlot='constrainedTypeOperand.stackEffect.priorPointerHelper', pointerDifference='arithmeticWindows.stackPointerSubtract', multiply='arithmeticWindows.signedSlotMultiply', nullCheck='negativeFieldRules.helpers.nullCheck', arrayFetch='initobjTypeOperand.consumerRowFetchHelper', assignmentCheck='functionPointerRules.helpers.assignmentCheck', managedStore='basicOpcodeRules.helpers.managedStore'),
    tailRefs=dict(pcAdvance='basicOpcodeRules.sharedWindows.pcAdvance', popCommit='arithmeticRules.blocks.remTopCommit', default='dispatchRules.blocks.default'),
)
_METHODS = dict(
    createInstance=('System.Activator', 'CreateInstance', ['System.Type'], 'object', True),
    updateReference=('IFix.Core.EvaluationStackOperation', 'UpdateReference', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'IFix.Core.VirtualMachine', 'System.Type'], 'void', True),
    toObject=('IFix.Core.EvaluationStackOperation', 'ToObject', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'System.Type', 'IFix.Core.VirtualMachine', 'bool'], 'object', True),
)
_LEAVES = dict(subtractSlot='4863c2482bc8488bc1c3', pointerDifference='482bca488bc1c3', multiply='4863c2480fafc1c3')
_RULES = dict(
    Initobj=dict(entryBlock='initobj', selector='signed-externType-index', recipe='top-minus-one;Activator.CreateInstance(Type);UpdateReference(result,Type);tag-at-least-8:clear-consumed-physical-managed-cell', normalTopDelta=-1, managedClear='conditional-consumed-slot-physical-index'),
    Constrained=dict(entryBlock='constrained', selector='signed-externType-index', recipe='previous-instruction-Operand-selects-top-minus-one-minus-signed-Operand;ToObject-clone-true;managed-physical-index-store;Object+index-slot-writes', normalTopDelta=0, managedClear='none-explicit;selected-managed-cell-overwritten'),
)
_NEXT = dict(initobj='initobjClear', initobjClear=None, constrainedGuard='constrained', constrained=None)
_PROGRAMS = dict(
    initobj=('8bd6498bcc', ('call', 'subtractSlot'), '4c8be04889442458488b5f48498bce', ('call', 'nullCheck'), '49637e04488bcb', ('call', 'nullCheck'), '488bd7488bcb', ('call', 'arrayFetch'), '488bd833d2488bc8', ('call', 'createInstance'), '4c896c243048895c2428488b8c24f003000048894c24204c8bc84d8bc7498bd4488b9c2410040000488bcb', ('call', 'updateReference'), '498bcc', ('call', 'nullCheck'), '41833c2408', ('branch', '0f8c', 'popCommit')),
    initobjClear=('488bd3498bcc', ('call', 'pointerDifference'), '498bcf', ('call', 'nullCheck'), '33d2498bcf', ('call', 'assignmentCheck'), '488bd3498bcc', ('call', 'pointerDifference'), '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf', ('call', 'managedStore'), ('branch', 'e9', 'popCommit')),
    constrainedGuard=('83f901', ('branch', '0f85', 'default')),
    constrained=('8d5107498bce', ('call', 'subtractSlot'), '488bf0488b5f48498bce', ('call', 'nullCheck'), '49637e04488bcb', ('call', 'nullCheck'), '488bd7488bcb', ('call', 'arrayFetch'), '488bf8488bce', ('call', 'nullCheck'), '48634e04be0c0000008bd6', ('call', 'multiply'), '488bd88bd6498bcc', ('call', 'subtractSlot'), '488bd3488bc8', ('call', 'pointerDifference'), '488bd84c896c2430c644242801488b8424f003000048894424204c8bcf4d8bc7488bd3488bbc2410040000488bcf', ('call', 'toObject'), '488bf0488bd7488bcb', ('call', 'pointerDifference'), '488bc848b8abaaaaaaaaaaaa2a48f7e9488bfa48d1ff488bc748c1e83f4803f8498bcf', ('call', 'nullCheck'), '488bd6498bcf', ('call', 'assignmentCheck'), '4863d74c8bc6498bcf', ('call', 'managedStore'), '488bcb', ('call', 'nullCheck'), '897b04488bcb', ('call', 'nullCheck'), 'c70308000000', ('branch', 'e9', 'restorePc')),
)
