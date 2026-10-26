"""Authenticate Call.UpdateReference's complete frame-to-updater bridge.

The incoming Int32 argument index is sign extended and scaled by twelve with
native address arithmetic. The descriptor pointer uses Call.argumentBase;
the managed array uses Call.managedStack. The evaluation base comes instead
from a fresh ThreadStackInfo.get_Stack request and that holder's unmanaged Base.
Call.evaluationStackBase is not read. Equivalence between these saved and
current bases, arrays and thread holders is unobserved.

The caller forwards the incoming object, VM and Type to the existing static
EvaluationStackOperation.UpdateReference program. It checks the returned thread
holder and UnmanagedStack pointers for null, but has no local argument-index
bounds guard or Base-null guard. No Call field store occurs in this caller.
Conditional target effects belong to referenceUpdateRules. Descriptor validity,
capacity, aliases, thread selection, helper mutation and execution remain open.

The complete body, named/raw carriers, boxed-to-unboxed field offsets and encoded
thread-Type cell are authenticated before these requests are exposed. The lazy
byte is mapped storage, with no claimed runtime value. All native identities
and hashes are inherited from reviewed JSON and explicit selected inputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_reference_helper_rules import _address, _mapped_span
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier
from scripts.game_data.ifix_vm_object_opcode_rules import _signature, _method_declaration, _cell_declaration


class CallReferenceUpdateRuleError(ValueError):
    """A frame reference-update claim lacks its complete caller witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise CallReferenceUpdateRuleError('call-reference-update.' + detail)


_METHOD_REFS = {
    'callUpdate': 'reflectionInvokerRules.methods.updateReference',
    'stackGet': 'callOpcodeRules.methods.stackGet',
    'update': 'initobjStackEffect.updateReferenceMethod',
}
_METHODS = {
    'callUpdate': ('IFix.Core.Call', 'UpdateReference', ['int', 'object', 'IFix.Core.VirtualMachine', 'System.Type'], 'void', False),
    'stackGet': ('IFix.Core.ThreadStackInfo', 'get_Stack', [], 'IFix.Core.ThreadStackInfo', True),
    'update': ('IFix.Core.EvaluationStackOperation', 'UpdateReference', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'IFix.Core.VirtualMachine', 'System.Type'], 'void', True),
}
_HELPER_REFS = {
    'typeInitialize': 'referenceUpdateRules.helpers.typeInitialize',
    'classInitialize': 'newFieldRules.helpers.classInitialize',
    'nullFailure': 'referenceUpdateRules.helpers.nullFailure',
}
_EFFECTS = {
    'index': 'signextend-incoming-Int32;descriptor=Call.argumentBase+12*index-native64-address-arithmetic',
    'base': 'fresh-get_Stack-result.UnmanagedStack.Base;Call.evaluationStackBase-not-read',
    'managed': 'Call.managedStack;thread-ManagedStack-not-read',
    'forward': 'UpdateReference(current-thread-Base,descriptor,saved-managed-array,incoming-object,incoming-VM,incoming-Type);hidden-MethodInfo-zero',
    'guard': 'null-thread-holder-or-null-UnmanagedStack:nullFailure-request-and-INT3-if-returned;no-local-index-bounds-or-Base-null-guard',
    'storage': 'no-explicit-Call-field-store;updater-target-effects-owned-by-referenceUpdateRules',
}
_CLAIMS = {
    'schema': 'endfield.ifix-vm-call-reference-update-rules.v1',
    'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'methodRefs': _METHOD_REFS, 'helperRefs': _HELPER_REFS,
    'layoutRef': 'callOpcodeRules.fieldLayouts',
    'baseFieldRef': 'stackConstructionRules.additionalFields',
    'usageRef': 'callOpcodeRules.usageCells.threadType',
    'objectHeaderBytes': 16, 'valueBytes': 12, 'effects': _EFFECTS,
    'programBoundary': 'complete-Call-UpdateReference-body-including-local-null-terminal',
    'storageBoundary': 'valid-stable-Call-thread-holder-and-unmanaged-records;descriptor-bounds-wrap-and-live-aliases-unobserved',
    'baseJoinBoundary': 'current-thread-Base-versus-Call-saved-evaluationStackBase-and-managed-array-identity-unobserved',
    'calleeBoundary': 'normal-request-return-without-unmodelled-mutation;thread-selection-init-updater-targets-and-unwind-unobserved',
    'lazyBoundary': 'mapped-anonymous-byte;runtime-initialization-state-unobserved',
}
_FIELDS = {
    'IFix.Core.Call': (True, {'argumentBase': 'IFix.Core.Value*', 'evaluationStackBase': 'IFix.Core.Value*',
        'managedStack': 'object[]', 'currentTop': 'IFix.Core.Value*', 'topWriteBack': 'IFix.Core.Value**'}),
    'IFix.Core.ThreadStackInfo': (False, {'UnmanagedStack': 'IFix.Core.UnmanagedStack*'}),
    'IFix.Core.UnmanagedStack': (True, {'Base': 'IFix.Core.Value*'}),
}


def _claims(spec: dict) -> None:
    _need(isinstance(spec, dict) and all(type(spec.get(k)) is type(v) and spec.get(k) == v
          for k, v in _CLAIMS.items()), 'unsupported schema/reference/effect/boundary')


def _fields(image: Any, spec: dict, contract: dict) -> dict[str, dict[str, int]]:
    layouts = _ref(contract, spec['layoutRef']); extras = _ref(contract, spec['baseFieldRef']); md = image.metadata; result = {}
    for owner_name, (value, wanted) in _FIELDS.items():
        owners = [t for t in md.types if md.type_full_name(t) == owner_name]
        _need(len(owners) == 1 and bool(owners[0].bitfield & 1) == value, 'named owner/value kind differs: ' + owner_name)
        owner = owners[0]; definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
        if owner_name == 'IFix.Core.Call': _need(set(definitions) == set(wanted), 'complete Call field set differs')
        offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index); result[owner_name] = {}
        container = extras[owner_name] if owner_name == 'IFix.Core.UnmanagedStack' else layouts[owner_name]['fields']
        if owner_name != 'IFix.Core.UnmanagedStack':
            _need(layouts[owner_name].get('type') == owner_name and layouts[owner_name].get('isValueType') is value, 'declared owner kind differs')
        for name, typ in wanted.items():
            row = container[name]; offset = row.get('offset'); f = definitions.get(name)
            _need(f is not None and row.get('type') == typ and type(offset) is int and 16 <= offset < 128
                  and offsets.get(name) == offset and _type(image, f.type_index) == typ, 'named field/offset differs: ' + name)
            if 'static' in row: _need(row['static'] is False, 'declared static field differs: ' + name)
            pointer = image.pe.u64_at_va(_rva(image.registration['types']) + f.type_index * 8); _carrier(image, pointer, typ)
            _need(not int.from_bytes(image.pe.bytes_at_va(pointer, 16)[8:10], 'little') & 16, 'static field carrier differs: ' + name)
            result[owner_name][name] = offset - spec['objectHeaderBytes'] if value else offset
    _need(result['IFix.Core.Call']['argumentBase'] == 0 and result['IFix.Core.UnmanagedStack']['Base'] == 0,
          'zero-displacement unboxed fields differ')
    return result


def _cells(image: Any, spec: dict, contract: dict) -> dict[str, int]:
    row = _ref(contract, spec['usageRef']); at = _address(row['cellRva'], 'threadType'); raw = image.pe.bytes_at_va(image.pe.image_base + at, 8)
    declared = row.get('rawHex', row.get('hex'))
    if declared is None: declared = _rva(row['encodedWord']).to_bytes(8, 'little').hex()
    _need(raw == bytes.fromhex(declared) and type(row.get('usageTag')) is int and row['usageTag'] == 1, 'thread-Type encoded bytes/tag differ')
    index = unresolved_usage_index(raw, image.registration['typesCount'], tag=1, source='call-reference-update.threadType', offset=at)
    pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8); _carrier(image, pointer, 'IFix.Core.ThreadStackInfo')
    _cell_declaration(row, 'IFix.Core.ThreadStackInfo', index, image.pe.bytes_at_va(pointer, 16))
    lazy = spec['lazyFlag']; _need(set(lazy) == {'rva', 'identity'} and lazy['identity'] == 'anonymous-native-byte', 'lazy flag declaration differs')
    flag = _address(lazy['rva'], 'lazyFlag'); _mapped_span(image, flag, 1, 'lazyFlag')
    return dict(threadType=at, lazyFlag=flag)


def _program(at: int, targets: dict[str, int], cells: dict[str, int], fields: dict[str, dict[str, int]]) -> bytes:
    p = _Program(at)
    p.add('48895c240848896c24104889742418574883ec40'); p.rip('803d', cells['lazyFlag'], b'\0')
    p.add('498bf9498bf04863ea488bd9'); p.branch(0x75, 'initialized')
    p.rip('488d0d', cells['threadType']); p.call(targets['typeInitialize']); p.rip('c605', cells['lazyFlag'], b'\1')
    p.mark('initialized'); p.rip('488b0d', cells['threadType']); p.call(targets['classInitialize']); p.add('33c9'); p.call(targets['stackGet'])
    p.add('4885c0'); p.branch(0x74, 'null'); p.add('488b48'); p.byte(fields['IFix.Core.ThreadStackInfo']['UnmanagedStack'])
    p.add('4885c9'); p.branch(0x74, 'null')
    p.add('488b03488d146d000000004883642430004803d54c8b43'); p.byte(fields['IFix.Core.Call']['managedStack'])
    p.add('4c8bce488b09488d1490488b442470488944242848897c2420'); p.call(targets['update'])
    p.add('488b5c2450488b6c2458488b7424604883c4405fc3'); p.mark('null'); p.call(targets['nullFailure']); p.add('cc')
    return p.finish()


def validate_call_reference_update_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Prove the frame caller on an already explicitly gated NativeImage."""
    _claims(spec); fields = _fields(image, spec, contract); cells = _cells(image, spec, contract); targets = {}; rows = {}
    for role, identity in _METHODS.items():
        row = dict(_ref(contract, _METHOD_REFS[role])); _method_declaration(row, identity); _signature(image, identity)
        if 'returnType' in row: _need(row['returnType'] == identity[3], 'declared method return differs: ' + role)
        targets[role] = _identity(image, row, identity, role, extents); rows[role] = row
    for role, path in _HELPER_REFS.items():
        row = _ref(contract, path); count = row['byteCount']; _need(type(count) is int and 0 < count <= 4096, 'helper extent differs: ' + role)
        at = _address(row['rva'], role); _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    row = rows['callUpdate']; at = targets['callUpdate']
    _expect(image.pe.bytes_at_va(image.pe.image_base + at, row['bodyBytes']), _program(at, targets, cells, fields), 'complete Call.UpdateReference')
    return dict(status='validated_conditional_call_reference_update_rules', evidenceBoundary='conditional', executionBoundary='unobserved',
                bodyBytes=row['bodyBytes'], effects=spec['effects'], baseJoinBoundary=spec['baseJoinBoundary'], calleeBoundary=spec['calleeBoundary'])


def validate_selected_call_reference_update_rules(contract: dict, *, gameassembly: Path | None,
                                                  metadata: Path | None, spec: dict | None = None) -> dict:
    if gameassembly is None or metadata is None: return dict(status='missing', detail='explicit native paths required')
    n = contract['nativeInputs']; _need(bool(n.get('gameAssemblySha256')) and bool(n.get('globalMetadataSha256')), 'native hashes required')
    gate = check_installed_native_inputs(n['gameAssemblySha256'], n['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return dict(status=gate.status, detail=gate.detail)
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.call-reference-update')
    return validate_call_reference_update_rules(image, contract['callReferenceUpdateRules'] if spec is None else spec,
                                                contract, image.mapper.pdata_function_extents(image.pe))
