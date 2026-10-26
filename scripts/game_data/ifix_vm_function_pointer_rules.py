"""Authenticate IFix method-value production without interpreting runtime state.

The caller gates the explicit native pair, authenticates the complete Execute
body and loader table order, and validates the inherited basic-rule tails.
This helper checks reviewed producer windows, finite dispatcher entries and
semantic byte witnesses. Projection joins only authored external signatures.
The unequal-Type resolver and anonymous-storey runtime selection stay open.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import (
    enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name,
)


class FunctionPointerRuleError(ValueError):
    """A function-pointer declaration lacks its selected native witness."""


_CLAIMS = {
    'Ldftn': ('whole-signed-int32-externMethods-index',
              'append-object-slot-containing-declared-external-row', 1),
    'Ldvirtftn': ('whole-signed-int32-externMethods-index',
                  'replace-top-receiver-with-object-method-reference', 0),
    'Ldvirtftn2': ('unsigned-low16-anonymous-storey-vtable-slot',
                   'replace-top-method-slot-with-integer-vtable-entry', 0),
}
_WINDOWS = {
    'Ldftn': ('tagAndManagedSlotIndex', 'wholeOperandExternalMethodFetch', 'managedStoreAndPushTail'),
    'Ldvirtftn': ('receiverAndWholeOperand', 'runtimeTypeOwnerComparison', 'unequalTypeResolver',
                  'resolvedObjectSlotStore', 'declaredObjectSlotStore'),
    'Ldvirtftn2': ('entry',),
}
_HELPER_REFS = {
    'pointerDifference': 'arithmeticWindows.stackPointerSubtract',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'virtualInvoke': 'newobjSelector.virtualInvokeHelper',
    'typeEquality': 'newobjSelector.pointerEquality',
    'advancePointer': 'basicOpcodeRules.helpers.advancePointer',
}
_TAIL_REFS = {name: 'basicOpcodeRules.sharedWindows.' + name for name in
              ('zeroRegister', 'slotWidth', 'pcAdvance', 'pushAdvance', 'pushTopCommit', 'integerStore')}
_NEW_HELPERS = ('objectGetType', 'assignmentCheck', 'typeTest', 'anonymousInfoFetch', 'int32ArrayFetch')
_DIVIDE_SLOT = bytes.fromhex('488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d0')
# Encodings describe the selected register allocation, never a build address.
_WITNESSES = {
    'Ldftn': {
        'objectTag': '41c7042408000000', 'slotIndex': (_DIVIDE_SLOT + bytes.fromhex('4189542404')).hex(),
        'externalField': '488b5f', 'signedOperand': '49637e04',
        'rowFetchArguments': '488bd7488bcb', 'managedStoreArguments': '488bd64c8bc3498bcf',
        'restoreSlotWidth': 'be0c000000',
    },
    'Ldvirtftn': {
        'receiverSlotSelected': '4c8be0', 'receiverManagedIndex': '49635c2404',
        'externalField': '488b5f', 'signedOperand': '49637e04',
        'declaringTypeSlot': 'b909000000', 'typeEqualityResult': '413ac5',
        'cacheField': '488b5f', 'resolvedObjectTag': '41c7042408000000',
        'resolvedSlotIndex': (_DIVIDE_SLOT + bytes.fromhex('4189542404')).hex(),
        'resolvedValue': '488b9c2480000000', 'resolvedManagedStack': '488bb42408040000',
        'managedStoreArguments': '488bd7488bce',
        'managedStoreValue': '4c8bc3', 'restoreOriginalTop': '4c8b642458',
        'declaredObjectTag': '41c7042408000000',
        'declaredSlotIndex': (_DIVIDE_SLOT + bytes.fromhex('4189542404')).hex(),
        'declaredExternalField': '488b58', 'declaredSignedOperand': '48637f04',
        'declaredStoreArguments': '488bd6498bcf',
    },
    'Ldvirtftn2': {
        'unsignedLow16Operand': '450fb77604', 'methodSlotSelected': '488bf0',
        'secondSlotWidth': 'ba0c000000', 'receiverManagedIndex': '48635b04',
        'anonymousInfosField': '488b7f', 'receiverTypeId': '48635b',
        'vtableField': '488b5b', 'vtableFetchArguments': '418bd6488bcb',
        'value1Store': '895e04', 'integerTag': '44892e',
    },
}
_EDGES = {
    'Ldftn': {
        'slotByteDifference': ('call', 'pointerDifference', 0),
        'externalRowFetch': ('call', 'arrayFetch', 0),
        'assignmentCheck': ('call', 'assignmentCheck', 0),
        'managedStore': ('call', 'managedStore', 0),
        'pushTail': ('jump', 'integerStore', 25),
    },
    'Ldvirtftn': {
        'receiverSubtract': ('call', 'subtractSlot', 0),
        'receiverManagedFetch': ('call', 'arrayFetch', 0),
        'externalRowFetch': ('call', 'arrayFetch', 0),
        'runtimeTypeGet': ('call', 'objectGetType', 0),
        'declaringTypeInvoke': ('call', 'virtualInvoke', 0),
        'typeEquality': ('call', 'typeEquality', 0),
        'sameTypeBranch': ('jne', 'declaredObjectSlotStore', 0),
        'resolvedSlotDifference': ('call', 'pointerDifference', 0),
        'resolvedAssignmentCheck': ('call', 'assignmentCheck', 0),
        'resolvedManagedStore': ('call', 'managedStore', 0),
        'resolvedPcTail': ('jump', 'slotPcTail', 0),
        'declaredSlotDifference': ('call', 'pointerDifference', 0),
        'declaredRowFetch': ('call', 'arrayFetch', 0),
        'declaredAssignmentCheck': ('call', 'assignmentCheck', 0),
        'declaredManagedStoreTail': ('jump', 'resolvedManagedStoreValue', 0),
    },
    'Ldvirtftn2': {
        'methodSlotSubtract': ('call', 'subtractSlot', 0),
        'receiverSlotSubtract': ('call', 'subtractSlot', 0),
        'receiverManagedFetch': ('call', 'arrayFetch', 0),
        'receiverTypeTest': ('call', 'typeTest', 0),
        'anonymousInfoFetch': ('call', 'anonymousInfoFetch', 0),
        'vtableInt32Fetch': ('call', 'int32ArrayFetch', 0),
        'pcTail': ('jump', 'slotPcTail', 0),
    },
}
_FIELD_TYPES = {
    'IFix.Core.VirtualMachine': {
        'externMethods': 'System.Reflection.MethodBase[]',
        'overrideCache': 'System.Collections.Generic.Dictionary`2<System.Type,System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,System.Reflection.MethodInfo>>',
        'anonymousStoreyInfos': 'IFix.Core.AnonymousStoreyInfo[]',
    },
    'IFix.Core.AnonymousStorey': {'typeId': 'int'},
    'IFix.Core.AnonymousStoreyInfo': {'VTable': 'int[]'},
}
_FIELD_WITNESSES = {
    'externalField': ('IFix.Core.VirtualMachine', 'externMethods'),
    'declaredExternalField': ('IFix.Core.VirtualMachine', 'externMethods'),
    'cacheField': ('IFix.Core.VirtualMachine', 'overrideCache'),
    'anonymousInfosField': ('IFix.Core.VirtualMachine', 'anonymousStoreyInfos'),
    'receiverTypeId': ('IFix.Core.AnonymousStorey', 'typeId'),
    'vtableField': ('IFix.Core.AnonymousStoreyInfo', 'VTable'),
}


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _slice(body: bytes, base: int, rva: int, count: int, label: str) -> bytes:
    at = rva - base
    if count < 1 or not 0 <= at <= len(body) - count:
        raise FunctionPointerRuleError(f'function-pointer.{label}: outside Execute body rva={rva:#x} bytes={count}')
    return body[at:at + count]


def _ref(contract: dict[str, Any], path: str) -> dict[str, Any]:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            found = [item for item in row if item.get('name', item.get('role')) == key]
            if len(found) != 1:
                raise FunctionPointerRuleError(f'function-pointer: ambiguous/missing contract reference {path}')
            row = found[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            raise FunctionPointerRuleError(f'function-pointer: missing contract reference {path}')
    if not isinstance(row, dict):
        raise FunctionPointerRuleError(f'function-pointer: invalid contract reference {path}')
    return row


def _hash(raw: bytes, row: dict[str, Any], label: str) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != str(row['sha256']).upper():
        raise FunctionPointerRuleError(f"function-pointer.{label}: mismatched expectedSha256={row['sha256']} actualSha256={actual}")


def _named(rows: list[dict[str, Any]], names: Any, label: str) -> dict[str, dict[str, Any]]:
    mapped = {row.get('name'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(names):
        raise FunctionPointerRuleError(f'function-pointer.{label}: missing/duplicate/unknown declarations')
    return mapped


def _rules(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (spec.get('schema') != 'endfield.ifix-vm-function-pointer-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional'
            or spec.get('executionBoundary') != 'unobserved'
            or spec.get('slotBytes') != 12 or spec.get('instructionBytes') != 8
            or spec.get('unequalTypeResultBoundary') != 'unresolved'
            or spec.get('anonymousSelectionBoundary') != 'runtime-typeId-and-vtable-value-unobserved'):
        raise FunctionPointerRuleError('function-pointer: unsupported schema/boundary/width')
    rows = spec.get('rules', [])
    rules = {row.get('opcode'): row for row in rows}
    if len(rows) != len(rules) or set(rules) != set(_CLAIMS):
        raise FunctionPointerRuleError('function-pointer: missing/duplicate/unknown opcode rules')
    for name, row in rules.items():
        if (row.get('operandMeaning'), row.get('stackEffect'), row.get('stackDeltaSlots')) != _CLAIMS[name]:
            raise FunctionPointerRuleError(f'function-pointer.{name}: unsupported operand/stack claim')
        _named(row.get('windows', []), _WINDOWS[name], name + '.windows')
        _named(row.get('witnesses', []), _WITNESSES[name], name + '.witnesses')
        edges = _named(row.get('controlEdges', []), _EDGES[name], name + '.edges')
        for edge_name, edge in edges.items():
            if (edge.get('kind'), edge.get('target'), edge.get('targetOffset', 0)) != _EDGES[name][edge_name]:
                raise FunctionPointerRuleError(f'function-pointer.{name}.{edge_name}: unsupported edge declaration')
    return rules


def _edge(body: bytes, base: int, row: dict[str, Any], targets: dict[str, int], label: str) -> None:
    kind, site = row['kind'], _rva(row['rva'])
    prefix = {'call': b'\xe8', 'jump': b'\xe9', 'jne': b'\x0f\x85'}[kind]
    size = len(prefix) + 4
    raw = _slice(body, base, site, size, label)
    actual = site + size + int.from_bytes(raw[len(prefix):], 'little', signed=True) if raw.startswith(prefix) else None
    expected = targets[row['target']] + row.get('targetOffset', 0)
    if actual != expected:
        raise FunctionPointerRuleError(f'function-pointer.{label}: edge target/shape expected={expected:#x} actual={actual}')


def _metadata_fields(image: Any, spec: dict[str, Any]) -> None:
    declared = spec.get('runtimeFields', {})
    if (set(declared) != set(_FIELD_TYPES) or any(
            set(declared[owner]) != set(fields) or any(
                row.get('type') != fields[field] or type(row.get('offset')) is not int or not 0 <= row['offset'] <= 127
                for field, row in declared[owner].items()) for owner, fields in _FIELD_TYPES.items())):
        raise FunctionPointerRuleError('function-pointer: unsupported runtime field declaration')
    for name, fields in declared.items():
        owners = [row for row in image.metadata.types if image.metadata.type_full_name(row) == name]
        if len(owners) != 1:
            raise FunctionPointerRuleError(f'function-pointer.{name}: expected unique metadata type actual={len(owners)}')
        owner = owners[0]
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
        field_rows = {image.metadata.string(row.name_index): row for row in image.metadata.fields_for(owner)}
        for field_name, declaration in fields.items():
            field = field_rows.get(field_name)
            pointer = (image.pe.u64_at_va(_rva(image.registration['types']) + field.type_index * 8)
                       if field is not None else None)
            actual_type = runtime_type_name(image.pe, image.metadata, pointer) if pointer is not None else None
            if offsets.get(field_name) != declaration['offset'] or actual_type != declaration['type']:
                raise FunctionPointerRuleError(f'function-pointer.{name}.{field_name}: expected={declaration} actualOffset={offsets.get(field_name)} actualType={actual_type}')


def validate_function_pointer_rules(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], contract: dict[str, Any],
) -> dict[str, Any]:
    """Prove three conditional producers against explicit, authenticated inputs."""
    rules = _rules(spec)
    if spec.get('valueLayoutRef') != 'constrainedTypeOperand.stackEffect.valueLayout':
        raise FunctionPointerRuleError('function-pointer: unsupported Value layout reference')
    layout = _ref(contract, spec['valueLayoutRef'])
    owners = [row for row in image.metadata.types if image.metadata.type_full_name(row) == 'IFix.Core.Value']
    if (layout.get('type') != 'IFix.Core.Value' or layout.get('fieldOffsets') != {'Type': 16, 'Value1': 20, 'Value2': 24}
            or len(owners) != 1 or runtime_type_field_offsets(image.metadata, image.pe, image.registration, owners[0].index) != layout['fieldOffsets']):
        raise FunctionPointerRuleError('function-pointer: Value layout differs')
    tags = {row['name']: row['id'] for row in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.ValueType')}
    if spec.get('valueTypeMembers') != {'Integer': 0, 'Object': 8} or tags.get('Integer') != 0 or tags.get('Object') != 8:
        raise FunctionPointerRuleError(f'function-pointer: ValueType Integer/Object differs actual={tags}')
    _metadata_fields(image, spec)
    if spec.get('helperRefs') != _HELPER_REFS or spec.get('tailWindowRefs') != _TAIL_REFS:
        raise FunctionPointerRuleError('function-pointer: unsupported inherited helper/tail references')
    targets, checked = {}, []
    for alias, path in {**_HELPER_REFS, **_TAIL_REFS}.items():
        row = _ref(contract, path)
        rva = _rva(row.get('windowRva', row['rva']))
        count = int(row['byteCount'])
        raw = (_slice(body, body_rva, rva, count, path) if alias in _TAIL_REFS
               else image.pe.bytes_at_va(image.pe.image_base + rva, count))
        _hash(raw, row, path)
        targets[alias] = _rva(row['rva'])
        checked.append(path)
    if (_slice(body, body_rva, targets['zeroRegister'], 3, 'zeroRegister') != bytes.fromhex('4533ed')
            or _slice(body, body_rva, targets['slotWidth'], 5, 'slotWidth') != bytes.fromhex('be0c000000')):
        raise FunctionPointerRuleError('function-pointer: shared zero register or slot stride differs')
    new_helpers = _named(spec.get('helpers', []), _NEW_HELPERS, 'helpers')
    for name, row in new_helpers.items():
        count = int(row['byteCount'])
        if count < 1:
            raise FunctionPointerRuleError(f'function-pointer.{name}: empty helper window')
        raw = image.pe.bytes_at_va(image.pe.image_base + _rva(row['rva']), count)
        _hash(raw, row, name)
        targets[name] = _rva(row['rva'])
        if name == 'int32ArrayFetch' and raw[:18] != bytes.fromhex('4883ec283b511873098b4491204883c428c3'):
            raise FunctionPointerRuleError('function-pointer: unsupported bounded int32 array fetch')
        if name == 'anonymousInfoFetch' and (raw[:9] != bytes.fromhex('4883ec283b51187206')
                                              or raw[15:25] != bytes.fromhex('488b44d1204883c428c3')):
            raise FunctionPointerRuleError('function-pointer: unsupported bounded anonymous-info array fetch')
    getter = new_helpers['objectGetType']
    if (getter.get('type'), getter.get('method'), getter.get('parameterCount')) != ('System.Object', 'GetType', 0):
        raise FunctionPointerRuleError('function-pointer: unsupported runtime Type getter')
    index = image.validate_method_row([getter['methodIndex'], getter['type'], getter['method'], _rva(getter['rva'])], label='function-pointer.Object.GetType')
    method = image.metadata.methods[index]
    if method.parameter_count != 0 or method.token != _rva(getter['token']):
        raise FunctionPointerRuleError('function-pointer.Object.GetType: metadata token/parameters differ')
    declaring = _ref(contract, 'newobjSelector.declaringTypeGetter')
    owner_rows = [owner for owner in image.metadata.types if image.metadata.type_full_name(owner) == 'System.Reflection.MemberInfo']
    methods = [method for owner in owner_rows for method in image.metadata.methods_for(owner)
               if image.metadata.string(method.name_index) == 'get_DeclaringType' and method.parameter_count == 0]
    if ((declaring.get('type'), declaring.get('method'), declaring.get('virtualSlot')) != ('System.Reflection.MemberInfo', 'get_DeclaringType', 9)
            or len(methods) != 1 or methods[0].slot != 9 or methods[0].token != _rva(declaring['token'])):
        raise FunctionPointerRuleError('function-pointer: declaring-Type virtual method differs')
    tail = spec['slotPcTail']
    raw = _slice(body, body_rva, _rva(tail['rva']), int(tail['byteCount']), 'slotPcTail')
    _hash(raw, tail, 'slotPcTail')
    if raw != bytes.fromhex('be0c000000') or _rva(tail['rva']) + len(raw) != targets['pcAdvance']:
        raise FunctionPointerRuleError('function-pointer: slot/pc tail is not adjacent to inherited pc advance')
    targets['slotPcTail'] = _rva(tail['rva'])
    entries = []
    for name, row in rules.items():
        if row['opcodeId'] != opcode_ids.get(name):
            raise FunctionPointerRuleError(f'function-pointer.{name}: enum ID differs')
        entry = resolve_dispatch_entry(body, body_rva, _rva(spec['dispatchStartRva']), row['opcodeId'])
        if entry != _rva(row['entryRva']):
            raise FunctionPointerRuleError(f"function-pointer.{name}: dispatch entry expected={row['entryRva']} actual={entry:#x}")
        windows = _named(row['windows'], _WINDOWS[name], name + '.windows')
        previous_end = entry
        for window_name in _WINDOWS[name]:
            window = windows[window_name]
            rva, count = _rva(window['rva']), int(window['byteCount'])
            if rva != previous_end:
                raise FunctionPointerRuleError(f'function-pointer.{name}.{window_name}: effect windows are not contiguous from entry')
            _hash(_slice(body, body_rva, rva, count, name + '.' + window_name), window, name + '.' + window_name)
            previous_end = rva + count
        witnesses = _named(row['witnesses'], _WITNESSES[name], name + '.witnesses')
        for witness_name, expected_hex in _WITNESSES[name].items():
            at, expected = _rva(witnesses[witness_name]['rva']), bytes.fromhex(expected_hex)
            if witness_name in _FIELD_WITNESSES:
                field_owner, field_name = _FIELD_WITNESSES[witness_name]
                expected += bytes([spec['runtimeFields'][field_owner][field_name]['offset']])
            if not entry <= at <= previous_end - len(expected):
                raise FunctionPointerRuleError(f'function-pointer.{name}.{witness_name}: witness outside effect windows')
            if _slice(body, body_rva, at, len(expected), witness_name) != expected:
                raise FunctionPointerRuleError(f'function-pointer.{name}.{witness_name}: unsupported witness shape')
        local_targets = {**targets, **{key: _rva(value['rva']) for key, value in windows.items()}}
        if name == 'Ldvirtftn':
            local_targets['resolvedManagedStoreValue'] = _rva(witnesses['managedStoreValue']['rva'])
        for edge in row['controlEdges']:
            if not entry <= _rva(edge['rva']) < previous_end:
                raise FunctionPointerRuleError(f"function-pointer.{name}.{edge['name']}: edge outside effect windows")
            _edge(body, body_rva, edge, local_targets, name + '.' + edge['name'])
        entries.append({'opcode': name, 'entryRva': hex(entry), 'stackDeltaSlots': row['stackDeltaSlots']})
    cast = spec['anonymousStoreyType']
    site = _rva(cast['loadRva'])
    raw = _slice(body, body_rva, site, 7, 'anonymousStoreyType')
    if raw[:3] != bytes.fromhex('488b15') or site + 7 + int.from_bytes(raw[3:], 'little', signed=True) != _rva(cast['cellRva']):
        raise FunctionPointerRuleError('function-pointer: anonymous-storey type-cell load differs')
    usage = image.pe.bytes_at_va(image.pe.image_base + _rva(cast['cellRva']), 8)
    if cast.get('usageTag') != 1 or int.from_bytes(usage, 'little') != _rva(cast['encodedWord']):
        raise FunctionPointerRuleError('function-pointer: anonymous-storey encoded type differs')
    index = unresolved_usage_index(usage, image.registration['typesCount'], tag=1, source='function-pointer AnonymousStorey', offset=_rva(cast['cellRva']))
    pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
    if (index != cast['registeredTypeIndex'] or cast['typeName'] != 'IFix.Core.AnonymousStorey'
            or runtime_type_name(image.pe, image.metadata, pointer) != cast['typeName']):
        raise FunctionPointerRuleError('function-pointer: receiver type-test resolves to another type')
    return {'status': 'validated_conditional_function_pointer_rules', 'entries': entries,
            'inheritedWindowsChecked': checked, 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['incoming-stack-values-and-receiver-compatibility', 'unequal-Type-override/cache-result',
                           'anonymous-storey-runtime-typeId-and-VTable-value', 'bounds-and-normal-helper-returns',
                           'MethodInfo-compatibility-and-delegate-binding', 'actual-patch-entry-and-invocation']}


def project_function_pointer_rules(decoded: dict[str, Any], parsed: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Join external signatures; expose receiver-dependent alternatives explicitly."""
    rules = _rules(spec)
    table = parsed['externMethods']
    records = table['records']
    if table['count'] != len(records):
        raise FunctionPointerRuleError('function-pointer projection: external-table count differs')
    rows = []
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name = instruction['name']
            if name not in rules:
                continue
            declaration = rules[name]
            raw = instruction['operandUnsigned']
            if (type(raw) is not int or not 0 <= raw <= 0xffffffff or instruction['opcode'] != declaration['opcodeId']):
                raise FunctionPointerRuleError(f'function-pointer projection.{name}: invalid raw operand or opcode ID')
            signed = raw if raw < 0x80000000 else raw - 0x100000000
            if 'operandSigned' in instruction and instruction['operandSigned'] != signed:
                raise FunctionPointerRuleError(f'function-pointer projection.{name}: inconsistent signed operand')
            row = {'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'],
                   'offset': instruction['offset'], 'opcode': name, 'operandUnsigned': raw, 'operandSigned': signed,
                   'operandMeaning': declaration['operandMeaning'], 'stackEffect': declaration['stackEffect'],
                   'stackDeltaSlots': declaration['stackDeltaSlots'], 'instructionAdvanceBytes': 8,
                   'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
                   'value2Write': 'none-in-reviewed-effect-window',
                   'selectedWhen': 'compatible-stack-and-all-selected-helper-calls-return-normally'}
            if name == 'Ldvirtftn2':
                row.update({'slotIndex': raw & 0xffff, 'resultTag': 'Integer',
                            'methodSlot': 'original-top-minus-one', 'receiverSlot': 'original-top-minus-two',
                            'conditionalStoredSelection': 'anonymousStoreyInfos[receiver.typeId].VTable[slotIndex]',
                            'runtimeTypeId': None, 'runtimeMethodId': None, 'managedStackStore': 'none',
                            'value1Meaning': 'selected-stored-int32-vtable-entry', 'topEffect': 'preserve-original-top',
                            'selectionBoundary': 'runtime-typeId-and-vtable-value-unobserved',
                            'fileTableBoundary': 'nonzero-anonymous-storey-framing-unresolved'})
            else:
                in_range = 0 <= signed < len(records)
                row.update({'externalMethodIndex': signed, 'fileTable': 'externMethods', 'resultTag': 'Object',
                            'externalMethodJoin': 'direct' if in_range else 'out-of-range',
                            'declaredExternalMethod': {'index': signed, 'signature': records[signed]} if in_range else None,
                            'runtimeMethodBase': None,
                            'value1Meaning': 'selected-slot-index-relative-to-evaluationStackBase',
                            'topEffect': 'advance-by-one-slot' if name == 'Ldftn' else 'restore-original-top',
                            'managedStackStore': 'managedStack[(selected-slot-evaluationStackBase)/12]',
                            'methodValueBoundary': 'available-MethodBase-row; MethodInfo-compatibility-unproved'})
                if not in_range:
                    row['diagnostic'] = {'check': 'whole-signed-external-index', 'actual': signed,
                                         'expected': {'minimum': 0, 'exclusiveMaximum': len(records)},
                                         'scope': f"method={method['index']} instruction={instruction['index']}"}
                if name == 'Ldvirtftn':
                    row.update({'receiverSlot': 'original-top-minus-one', 'incomingTypeCheck': 'none-before-managed-index-read',
                                'runtimeTypeComparison': None, 'conditionalRoutes': {
                                    'sameType': 'store-declared-external-MethodBase-row',
                                    'unequalType': 'store-resolver-result-with-override/cache-outcome-unresolved'},
                                'overrideResultBoundary': 'unresolved'})
            rows.append(row)
    return rows
