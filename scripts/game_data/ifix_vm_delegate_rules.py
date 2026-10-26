"""Authenticate IFix's conditional two-slot delegate construction path.

This family helper reads selected native evidence only. It does not emulate a
patch, select a wrapper implementation, or observe a delegate being invoked.
"""

from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry


class DelegateRuleError(ValueError):
    """A selected delegate rule lacks its reviewed native witness."""


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _window(body: bytes, base: int, row: dict[str, Any]) -> bytes:
    start = _rva(row['rva']) - base
    size = row['byteCount']
    label = 'delegate.' + row['name']
    if not isinstance(size, int) or size < 1 or not 0 <= start <= len(body) - size:
        raise DelegateRuleError(f'{label}: outside authenticated Execute body')
    raw = body[start:start + size]
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != row['sha256'].upper() or raw != bytes.fromhex(row['hex']):
        raise DelegateRuleError(f"{label}: native bytes differ expectedSha256={row['sha256']} actualSha256={actual}")
    return raw


def _call(body: bytes, base: int, site: str, target: int, label: str) -> None:
    rva = _rva(site)
    offset = rva - base
    raw = body[offset:offset + 5] if 0 <= offset <= len(body) - 5 else b''
    actual = rva + 5 + int.from_bytes(raw[1:], 'little', signed=True) if len(raw) == 5 and raw[0] == 0xe8 else None
    if actual != target:
        raise DelegateRuleError(f'delegate.{label}: expectedTarget={target:#x} actualTarget={actual}')


def _branch(body: bytes, base: int, row: dict[str, Any], *, jump: bool = False) -> None:
    site = _rva(row['rva'])
    offset = site - base
    prefix = b'\xe9' if jump else {'equal': b'\x0f\x84', 'notEqual': b'\x0f\x85'}[row['condition']]
    if not jump and 0 <= offset < len(body) and body[offset] == {'equal': 0x74, 'notEqual': 0x75}[row['condition']]:
        raw = body[offset:offset + 2]
        actual = site + 2 + int.from_bytes(raw[1:], 'little', signed=True) if len(raw) == 2 else None
        if actual != _rva(row['targetRva']):
            raise DelegateRuleError(f"delegate.{row['name']}: short branch differs expectedTarget={row['targetRva']} actualTarget={actual}")
        return
    size = len(prefix) + 4
    raw = body[offset:offset + size] if 0 <= offset <= len(body) - size else b''
    actual = site + size + int.from_bytes(raw[len(prefix):], 'little', signed=True) if raw.startswith(prefix) and len(raw) == size else None
    if actual != _rva(row['targetRva']):
        raise DelegateRuleError(f"delegate.{row['name']}: branch differs expectedTarget={row['targetRva']} actualTarget={actual}")


def _method(image: Any, row: dict[str, Any], extents: dict[int, int]) -> int:
    metadata = image.metadata
    candidates = []
    for owner in metadata.types:
        if metadata.type_full_name(owner) != row['type']:
            continue
        for method in metadata.methods_for(owner):
            if metadata.string(method.name_index) != row['method'] or method.parameter_count != row['parameterCount']:
                continue
            types = [runtime_type_name(image.pe, metadata, image.pe.u64_at_va(int(image.registration['types'], 16) + p.type_index * 8)) for p in metadata.parameters_for(method)]
            if types == row['parameterTypes']:
                candidates.append(method)
    label = f"delegate.{row['type']}.{row['method']}"
    if len(candidates) != 1:
        raise DelegateRuleError(f'{label}: expected one signature, actual={len(candidates)}')
    method = candidates[0]
    pointer = image.method_pointer_va(method)
    rva = pointer - image.pe.image_base
    if method.token != _rva(row['token']) or rva != _rva(row['rva']):
        raise DelegateRuleError(f'{label}: token or registered pointer differs')
    end = extents.get(pointer)
    if end is None or end - pointer != row['bodyBytes']:
        raise DelegateRuleError(f'{label}: native extent differs')
    actual = hashlib.sha256(image.pe.bytes_at_va(pointer, end - pointer)).hexdigest().upper()
    if actual != row['bodySha256'].upper():
        raise DelegateRuleError(f"{label}: expectedSha256={row['bodySha256']} actualSha256={actual}")
    return rva


def validate_delegate_rules(image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
                            opcode_ids: dict[str, int], contract: dict[str, Any],
                            extents: dict[int, int]) -> dict[str, Any]:
    """Check the selected constructor branch, arguments, null fallbacks and tail."""
    if (spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('opcode') != 'Newobj' or spec.get('opcodeId') != opcode_ids.get('Newobj')
            or spec.get('slotBytes') != contract['entryHeader']['slotBytes']
            or (spec.get('inputSlots'), spec.get('outputSlots')) != (2, 1)
            or spec.get('resultTag') != 'preserved-target-slot-tag'
            or spec.get('selection') != 'resolved-declaring-type-base-is-System.MulticastDelegate'):
        raise DelegateRuleError('delegate: unsupported constructor or stack claim')
    expected_names = ('slotWidth', 'zeroLocal', 'inputSlotsAndTarget', 'targetSlotIndexAndClear',
                      'integerTagChoice', 'methodInfoPath', 'wrapperPath', 'genericFallback',
                      'nullFallbackException', 'resultAndTop')
    if tuple(row['name'] for row in spec['executeWindows']) != expected_names:
        raise DelegateRuleError('delegate: missing, duplicate or reordered Execute windows')
    windows = {row['name']: _window(body, body_rva, row) for row in spec['executeWindows']}
    if windows['slotWidth'] != b'\xbe' + spec['slotBytes'].to_bytes(4, 'little') or windows['zeroLocal'] != b'\x45\x33\xed\x4c\x89\x6c\x24\x68':
        raise DelegateRuleError('delegate: slot stride or zero comparison source differs')
    selector = contract['newobjSelector']
    entry = resolve_dispatch_entry(body, body_rva, _rva(contract['basicOpcodeRules']['dispatchStartRva']), opcode_ids['Newobj'])
    if entry != _rva(spec['entryRva']):
        raise DelegateRuleError(f"delegate: dispatch entry differs expected={spec['entryRva']} actual={entry:#x}")
    start = _rva(selector['pointerEquality']['nonDelegateBranchRva']) + 6
    if _rva(spec['executeWindows'][2]['rva']) != start:
        raise DelegateRuleError('delegate: entry is not the reviewed selector fallthrough')
    parent = contract['constrainedTypeOperand']['stackEffect']
    refs = (('valueLayoutRef', 'constrainedTypeOperand.stackEffect.valueLayout'),
            ('pointerHelperRef', 'constrainedTypeOperand.stackEffect.priorPointerHelper'),
            ('managedStoreHelperRef', 'constrainedTypeOperand.stackEffect.managedStackStoreHelper'))
    if any(spec.get(key) != expected for key, expected in refs):
        raise DelegateRuleError('delegate: unsupported shared layout/helper reference')
    layout = parent['valueLayout']
    owners = [row for row in image.metadata.types if image.metadata.type_full_name(row) == layout['type']]
    if len(owners) != 1 or runtime_type_field_offsets(image.metadata, image.pe, image.registration, owners[0].index) != layout['fieldOffsets']:
        raise DelegateRuleError('delegate: Value field layout differs')
    members = enum_members(image.metadata, field_defaults(image.metadata), layout['enumType'])
    selected = [row for row in members if row['name'] == spec['integerMember']['name']]
    if len(selected) != 1 or selected[0]['id'] != spec['integerMember']['id'] or selected[0]['id'] != 0:
        raise DelegateRuleError('delegate: Integer tag differs from zero comparison')
    vm_owner = [row for row in image.metadata.types if image.metadata.type_full_name(row) == contract['consumer']['type']]
    field = spec['wrappersManagerField']
    if len(vm_owner) != 1 or runtime_type_field_offsets(image.metadata, image.pe, image.registration, vm_owner[0].index).get(field['name']) != field['offset']:
        raise DelegateRuleError('delegate: wrapper-manager field differs')
    cast = spec['methodInfoType']
    site = _rva(cast['loadRva'])
    offset = site - body_rva
    load = body[offset:offset + 7] if 0 <= offset <= len(body) - 7 else b''
    if len(load) != 7 or load[:3] != b'\x48\x8b\x15':
        raise DelegateRuleError('delegate: MethodInfo cast lacks its type-cell load')
    cell = site + 7 + int.from_bytes(load[3:], 'little', signed=True)
    if cell != _rva(cast['cellRva']):
        raise DelegateRuleError('delegate: MethodInfo cast type-cell target differs')
    raw = image.pe.bytes_at_va(image.pe.image_base + cell, 8)
    if int.from_bytes(raw, 'little') != _rva(cast['encodedWord']):
        raise DelegateRuleError('delegate: MethodInfo cast encoded type differs')
    index = unresolved_usage_index(raw, image.registration['typesCount'], tag=cast['usageTag'], source='delegate MethodInfo cast', offset=cell)
    type_pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + index * 8)
    if index != cast['registeredTypeIndex'] or runtime_type_name(image.pe, image.metadata, type_pointer) != cast['typeName']:
        raise DelegateRuleError('delegate: MethodInfo cast resolves to a different type')
    expected_division = bytes.fromhex('488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d0')
    if tuple(row['name'] for row in spec['slotIndexPrograms']) != ('target', 'method', 'result'):
        raise DelegateRuleError('delegate: slot-index programs missing or duplicated')
    if any(_window(body, body_rva, row) != expected_division for row in spec['slotIndexPrograms']):
        raise DelegateRuleError('delegate: signed byte-span division by twelve differs')
    helper = spec['receiverDispatcher']
    helper_rva = _rva(helper['rva'])
    helper_pointer = image.pe.image_base + helper_rva
    if extents.get(helper_pointer) != helper_pointer + helper['byteCount']:
        raise DelegateRuleError('delegate: receiver dispatcher extent differs')
    actual = hashlib.sha256(image.pe.bytes_at_va(helper_pointer, helper['byteCount'])).hexdigest().upper()
    if actual != helper['sha256'].upper():
        raise DelegateRuleError(f"delegate.receiverDispatcher: expectedSha256={helper['sha256']} actualSha256={actual}")
    call_targets = {
        'methodSlotSubtract': _rva(parent['priorPointerHelper']['rva']),
        'targetSlotSubtract': _rva(parent['priorPointerHelper']['rva']),
        'receiverDispatcher': helper_rva,
    }
    call_targets.update({name: _rva(next(row for row in contract['arithmeticWindows'] if row['name'] == 'stackPointerSubtract')['rva']) for name in ('targetSlotSpan', 'targetClearSpan', 'methodClearSpan', 'resultSlotSpan')})
    call_targets.update({name: _rva(parent['managedStackStoreHelper']['rva']) for name in ('targetManagedClear', 'methodManagedClear', 'resultManagedStore')})
    if set(spec['calls']) != set(call_targets):
        raise DelegateRuleError('delegate: unsupported helper-call set')
    for name, target in call_targets.items():
        _call(body, body_rva, spec['calls'][name], target, name)
    if tuple(row['role'] for row in spec['methodCalls']) != ('reflectionDelegate', 'genericFallback', 'nullFallbackException'):
        raise DelegateRuleError('delegate: missing or reordered named construction calls')
    for row in spec['methodCalls']:
        _call(body, body_rva, row['callRva'], _method(image, row, extents), row['role'])
    if tuple(row['name'] for row in spec['branches']) != ('integerTag', 'wrapperNonNull', 'genericNonNull') or tuple(row['name'] for row in spec['jumps']) != ('reflectionResult', 'redispatch'):
        raise DelegateRuleError('delegate: constructor branch set differs')
    for row in spec['branches']:
        _branch(body, body_rva, row)
    for row in spec['jumps']:
        _branch(body, body_rva, row, jump=True)
    return {'status': 'validated_conditional_delegate_construction', 'inputSlots': 2, 'outputSlots': 1,
            'integerPath': 'receiver-dispatch-then-null-only-generic-fallback',
            'otherTagPath': 'MethodInfo-cast-then-Delegate.CreateDelegate',
            'resultTag': spec['resultTag'], 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['incoming-stack-values-and-tags', 'wrapper-selection-and-factory-result', 'reflection-success', 'actual-patch-entry-and-invocation']}
