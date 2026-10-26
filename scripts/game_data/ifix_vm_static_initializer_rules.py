"""Authenticate static-field constructor suppression and the index Execute bridge.

checkCctorExecute reads the selected constructor ID, returns for a negative ID,
and writes -1 to every equal table entry before requesting that constructor.
The complete five-argument Execute overload selects unmanagedCodes[methodId]
and forwards the three stack carriers, argsCount, methodId, zero refCount and a
null topWriteBack to the interpreter. Constructor completion, live table state,
concurrent mutation, aliasing and exception delivery remain unobserved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_object_opcode_rules import _signature, _method_declaration
from scripts.game_data.ifix_vm_anonymous_storey_rules import _named_carrier
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class StaticInitializerRuleError(ValueError):
    """A constructor suppression claim lacks its selected witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok:
        raise StaticInitializerRuleError('static-initializer.' + detail)


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k)) is type(v) and spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported declaration')
    _need(set(spec.get('methods', {})) == {'executeByIndex'}, 'owned method set differs')


def _program(role: str, at: int, targets: dict[str, int]) -> bytes:
    p = _Program(at)
    if role == 'checkCctor':
        p.add('4883ec484c8bd1488b89880000004885c9'); p.branch(0x74, 'null')
        p.add('3b5118'); p.branch(0x73, 'bounds')
        p.add('4863c2448b5c81204585db'); p.branch(0x78, 'return')
        p.add('33d2'); p.mark('scan'); p.add('498b82880000004885c0'); p.branch(0x74, 'null')
        p.add('3b5018'); p.branch(0x7d, 'invoke'); p.add('488bc8'); p.branch(0x73, 'bounds')
        p.add('4863c244395c8120'); p.branch(0x75, 'increment'); p.add('4863c2834c8120ff')
        p.mark('increment'); p.add('ffc2'); p.branch(0xeb, 'scan')
        p.mark('invoke'); p.add('488364243000418bd3488b442470498bca83642428004889442420')
        p.call(targets['executeByIndex']); p.mark('return'); p.add('4883c448c3')
        p.mark('bounds'); p.call(targets['boundsFailure']); p.add('cc')
        p.mark('null'); p.call(targets['nullFailure']); p.add('cc')
    elif role == 'executeByIndex':
        p.add('4883ec58488b41184c63d24e8b1cd033c048894424484889442440894424388b84248800000089542430498bd389442428488b8424800000004889442420')
        p.call(targets['execute']); p.add('4883c458c3')
    else:
        _need(False, 'unknown finite program')
    return p.finish()


def _layouts(image: Any, contract: dict) -> None:
    md = image.metadata
    owners = [t for t in md.types if md.type_full_name(t) == 'IFix.Core.VirtualMachine']
    _need(len(owners) == 1 and not owners[0].bitfield & 1, 'VM owner differs')
    owner = owners[0]; offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index)
    fields = {md.string(f.name_index): f for f in md.fields_for(owner)}
    for name, typ, offset, path in [('cctors', 'int[]', 136, _CLAIMS['fieldRefs']['cctors']), ('unmanagedCodes', 'IFix.Core.Instruction**', 24, _CLAIMS['fieldRefs']['unmanagedCodes'])]:
        declared = _ref(contract, path)
        if name == 'cctors':
            _need(declared.get('type') == typ, 'declared field type differs: ' + name)
            declared = declared.get('offset')
        else:
            declared = declared.get(name)
        _need(type(declared) is int and declared == offset, 'declared field offset differs: ' + name)
        field = fields.get(name)
        _need(field is not None and offsets.get(name) == offset and _type(image, field.type_index) == typ, 'named field differs: ' + name)
        pointer = image.pe.u64_at_va(_rva(image.registration['types']) + field.type_index * 8)
        raw = image.pe.bytes_at_va(pointer, 16)
        _need(not int.from_bytes(raw[8:10], 'little') & 0x10, 'static field differs: ' + name)
        _named_carrier(image, pointer, typ)


def _execute_carriers(image: Any, identity: tuple) -> None:
    owner, name, params, returned, _ = identity; md = image.metadata
    matches = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
               if md.string(m.name_index) == name and m.parameter_count == len(params)
               and [_type(image, p.type_index) for p in md.parameters_for(m)] == params]
    _need(len(matches) == 1, 'named Execute overload differs')
    method = matches[0]
    for index, typ in [(p.type_index, typ) for p, typ in zip(md.parameters_for(method), params)] + [(method.return_type, returned)]:
        pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
        _named_carrier(image, pointer, typ)


def validate_static_initializer_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Validate inside an already authenticated selected image."""
    _claims(spec); _layouts(image, contract); targets = {}; rows = {}
    for role, identity in _METHODS.items():
        row = spec['methods'][role] if role == 'executeByIndex' else _ref(contract, _CLAIMS['methodRefs'][role])
        normalized = dict(row); normalized.setdefault('parameterCount', len(identity[2]))
        _method_declaration(normalized, identity)
        if role == 'execute': _execute_carriers(image, identity)
        else: _signature(image, identity)
        targets[role] = _identity(image, normalized, identity, role, extents)
        rows[role] = normalized
    for role, path in _CLAIMS['helperRefs'].items():
        row = _ref(contract, path); count = row['byteCount']
        _need(type(count) is int and 0 < count <= 4096, 'helper extent differs: ' + role)
        at = _rva(row['rva']); _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    for role in ('checkCctor', 'executeByIndex'):
        row = rows[role]; raw = image.pe.bytes_at_va(image.pe.image_base + targets[role], row['bodyBytes'])
        _expect(raw, _program(role, targets[role], targets), role)
    return dict(status='validated_conditional_static_initializer_rules', methodCount=2,
                selection=spec['selection'], mutation=spec['mutation'], invocation=spec['invocation'],
                storageBoundary=spec['storageBoundary'], failureBoundary=spec['failureBoundary'],
                executionBoundaryDetail=spec['executionBoundaryDetail'], evidenceBoundary='conditional', executionBoundary='unobserved')


def validate_selected_static_initializer_rules(contract: dict, *, gameassembly: Path | None, metadata: Path | None, spec: dict | None = None) -> dict:
    """Fail closed before opening an image when the explicit native pair differs."""
    if gameassembly is None or metadata is None: return dict(status='missing', detail='explicit native paths required')
    inputs = contract['nativeInputs']; _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'native hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return dict(status=gate.status, detail=gate.detail)
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.static-initializer')
    return validate_static_initializer_rules(image, contract['staticInitializerRules'] if spec is None else spec, contract, image.mapper.pdata_function_extents(image.pe))


_CLAIMS = dict(
    schema='endfield.ifix-vm-static-initializer-rules.v1', evidenceBoundary='conditional', executionBoundary='unobserved',
    methodRefs=dict(checkCctor='negativeFieldRules.checkCctorMethod', execute='consumer'),
    helperRefs=dict(boundsFailure='referenceUpdateRules.helpers.boundsFailure', nullFailure='referenceUpdateRules.helpers.nullFailure'),
    fieldRefs=dict(cctors='negativeFieldRules.vmFields.fields.cctors', unmanagedCodes='fieldOffsets'),
    selection='unsigned-fieldId-bounds;negative-selected-cctor:normal-return;nonnegative:scan-table',
    mutation='each-entry-equal-selected-cctor-becomes-minus-one-before-Execute-request',
    invocation='selected-cctor;caller-argumentBase-managedStack-evaluationBase;argsCount-zero;refCount-zero;topWriteBack-null',
    storageBoundary='valid-stable-cctors-and-unmanagedCodes-arrays;concurrent-change-aliasing-and-helper-mutation-unobserved',
    failureBoundary='null-or-bounds-helper-request-followed-by-INT3;abnormal-transfer-unobserved',
    executionBoundaryDetail='constructor-completion-and-exception-transfer-unobserved;no-rollback-store-in-selected-helper',
)
_METHODS = dict(
    checkCctor=('IFix.Core.VirtualMachine', 'checkCctorExecute', ['int', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*'], 'void', False),
    executeByIndex=('IFix.Core.VirtualMachine', 'Execute', ['int', 'IFix.Core.Value*', 'object[]', 'IFix.Core.Value*', 'int'], 'IFix.Core.Value*', False),
    execute=('IFix.Core.VirtualMachine', 'Execute', _EXECUTE_TYPES, 'IFix.Core.Value*', False),
)
