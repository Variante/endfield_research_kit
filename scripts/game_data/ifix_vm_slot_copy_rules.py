"""Authenticate IFix slot copies without interpreting a runtime VM stack.

The caller owns the explicit native-input, complete Execute, frame-header and
basic-tail gates. This module checks selected dispatch paths, named copy/store
methods and their complete effect blocks. Projections state authored pointer
expressions and conditional tag rules only. Clone returns, managed contents,
valid storage and reference dereferencing/aliasing remain runtime joins.

Both helpers first copy all 12 Value bytes. copy then special-cases ValueType
and ChainFieldReference; ordinary Object values retain their copied Value1.
store rebases tags at or above Object and additionally handles FieldReference
and ChainFieldReference below that threshold. Its FieldReference branch rewrites
dst.Value1 before reading src.Value1, so overlapping slots cannot be treated as
an ordinary independent copy. Stloc clears the consumed evaluation reference.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.il2cpp.protocol import (
    enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name,
)


class SlotCopyRuleError(ValueError):
    """A slot-copy declaration does not match its selected native evidence."""


_CLAIMS = {
    'Ldarg': ('whole-signed-int32-argument-index', 'argumentBase+operand*12', 'original-top', 'copy', 1),
    'Ldloc': ('whole-signed-int32-local-index', 'localBase+operand*12', 'original-top', 'copy', 1),
    'Stloc': ('whole-signed-int32-local-index', 'original-top-minus-one', 'localBase+operand*12', 'store', -1),
    'Dup': ('unused-by-selected-copy-path', 'original-top-minus-one', 'original-top', 'copy', 1),
}
_REFS = {
    'slotMultiply': 'arithmeticWindows.signedSlotMultiply',
    'pointerAdd': 'arithmeticWindows.pointerAdd',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'postStore': 'delegateBridgeRules.referenceWriteBarrier',
}
_TAIL_REFS = {name: 'basicOpcodeRules.sharedWindows.' + name for name in
              ('loopState', 'zeroRegister', 'slotWidth', 'pcAdvance', 'pushAdvance',
               'pushTopCommit', 'integerStore', 'managedClear')}
_METHODS = {
    'copy': ('IFix.Core.VirtualMachine', 'copy', ['stackBase', 'dst', 'src', 'managedStack'],
             ['IFix.Core.Value*', 'IFix.Core.Value*', 'IFix.Core.Value*', 'object[]'], 'void'),
    'store': ('IFix.Core.VirtualMachine', 'store', ['stackBase', 'dst', 'src', 'managedStack'],
              ['IFix.Core.Value*', 'IFix.Core.Value*', 'IFix.Core.Value*', 'object[]'], 'void'),
    'clone': ('IFix.Core.ObjectClone', 'Clone', ['obj'], ['object'], 'object'),
}
_BINDINGS = {
    'copy': {'zeroResult': '33ff', 'sourceArgument': '498bd9',
             'destinationBaseVmArguments': '498bf04c8bfa4c8bf1'},
    'store': {'arguments': '498bd94d8bf04c8bfa488bf1'},
    'clone': {},
}
_PREFIX = {'call': b'\xe8', 'jump': b'\xe9', 'jump8': b'\xeb',
           'je8': b'\x74', 'jne8': b'\x75', 'jne': b'\x0f\x85', 'jge': b'\x0f\x8d'}
# Complete effect-block grammars: fixed instruction encodings plus named edges.
# They contain register/field-layout facts, never build addresses or hashes.
_BLOCKS = {
    'entryHomes': ('488bc44c8948204c89401848894808',),
    'managedArgument': ('4d8bf94d8bf04c8be2',),
    'vmRegister': ('488bbc24f0030000',),
    'ldarg': ('498bce', ('call', 'nonnull'), '49634e048bd6', ('call', 'slotMultiply'),
              '488b8c2400040000', ('jump', 'loadAdd')),
    'ldloc': ('498bce', ('call', 'nonnull'), '49634e048bd6', ('call', 'slotMultiply'),
              '488b8c24b8000000'),
    'loadAdd': ('488bd0', ('call', 'pointerAdd')),
    'loadCopy': ('4c896c24284c897c24204c8bc84d8bc4488bd3488bcf', ('call', 'copy'),
                 ('jump8', 'loadAdvance')),
    'loadAdvance': (('jump', 'pushJoin'),),
    'dup': ('8bd6498bcc', ('call', 'subtractSlot'), ('jump', 'loadCopy')),
    'stloc': ('8bd6498bcc', ('call', 'subtractSlot'),
              '4c8be048894424584889442460498bce', ('call', 'nonnull'),
              '49634e048bd6', ('call', 'slotMultiply'),
              '488b8c24b8000000488bd0', ('call', 'pointerAdd'),
              '4c896c24284c897c24204d8bcc4c8bc0488bd3488bcf', ('call', 'store')),
    'copy.raw': ('f20f10038b4308f20f1106894608833e09', ('je8', 'copy.boxed'),
                  '833e07', ('jne', 'copy.return')),
    'copy.chain': ('488b7c2460492bdf49beabaaaaaaaaaaaa2a498bc648f7eb48d1fa'
                    '488bca48c1e93f4803d1488bcf488b5cd720488bd3', ('call', 'assignmentCheck'),
                    '492bf7498bc648f7ee48d1fa488bc248c1e83f4803d048895cd720'
                    '4883c204488d0cd7', ('jump8', 'copy.postStore')),
    'copy.boxed': ('48634304488b6c246048397cc520', ('je8', 'copy.rebase'),
                    '486343044533c0498b4e10488b54c520', ('call', 'clone'), '488bf8'),
    'copy.rebase': ('488bce48b8abaaaaaaaaaaaa2a492bcf48f7e9488bda488bd748d1fb'
                     '488bcb48c1e93f4803d9488bcd895e04', ('call', 'assignmentCheck'),
                     '4863c3488d4d2048897cc520488d0cc1'),
    'copy.postStore': (('call', 'postStore'),),
    'copy.return': ('488b5c2440488b6c2448488b7424504883c420415f415e5fc3',),
    'store.raw': ('f20f10038b4308f2410f11064189460841833e08', ('jge', 'store.object'),
                   '41833e06', ('je8', 'store.field'), '41833e07', ('jne', 'store.return')),
    'store.chain': ('488b7c2460492bdf48bdabaaaaaaaaaaaa2a488bc548f7eb48d1fa'
                     '488bca48c1e93f4803d1488bcf488b5cd720488bd3', ('call', 'assignmentCheck'),
                     '4d2bf7488bc549f7ee48d1fa488bc248c1e83f4803d048895cd720'
                     '4883c204488d0cd7', ('jump', 'store.postStore')),
    'store.field': ('488b7c2460498bce492bcf48b8abaaaaaaaaaaaa2a48f7e9488bcf'
                     '488bf248d1fe488bc648c1e83f4803f04189760448634304'
                     '488b5cc720488bd3', ('call', 'assignmentCheck'),
                     '4863c648895cc720', ('jump8', 'store.postAddress')),
    'store.object': ('41833e09488b7c2460', ('jne8', 'store.plain'),
                      '4863430448837cc72000', ('je8', 'store.plain'),
                      '486343044533c0488b4e10488b54c720', ('call', 'clone'),
                      '488bf0', ('jump8', 'store.rebase')),
    'store.plain': ('48634304488b74c720',),
    'store.rebase': ('498bce48b8abaaaaaaaaaaaa2a492bcf48f7e9488bcf488bda'
                      '488bd648d1fb488bc348c1e83f4803d841895e04', ('call', 'assignmentCheck'),
                      '4863c3488974c720'),
    'store.postAddress': ('4883c004488d0cc7',),
    'store.postStore': (('call', 'postStore'),),
    'store.return': ('488b5c2440488b6c2448488b7424504883c420415f415e5fc3',),
}
_CHAINS = (
    ('ldloc', 'loadAdd', 'loadCopy'),
    ('copy.raw', 'copy.chain', 'copy.boxed', 'copy.rebase', 'copy.postStore', 'copy.return'),
    ('store.raw', 'store.chain', 'store.field', 'store.object', 'store.plain', 'store.rebase',
     'store.postAddress', 'store.postStore', 'store.return'),
)
_COPY_CASES = {
    'ValueType=9': 'null-or-Clone-return; rebase-dst.Value1; write-managedStack[dst-position]',
    'ChainFieldReference=7': 'copy-managedStack[src-position]-to-managedStack[dst-position]; preserve-Value1',
    'other': 'preserve-copied-Value1; no-managed-slot-store',
}
_STORE_CASES = {
    'signed-tag>=Object=8': 'ValueType=9-and-nonnull-calls-Clone-otherwise-read-src.Value1; rebase-dst.Value1; store-selected-reference',
    'FieldReference=6': 'rebase-dst.Value1-before-reading-src.Value1; copy-selected-managed-reference',
    'ChainFieldReference=7': 'copy-managedStack[src-position]-to-managedStack[dst-position]; preserve-Value1',
    'other': 'preserve-copied-Value1; no-managed-slot-store',
}


def _rva(value: Any) -> int:
    return int(value, 16) if isinstance(value, str) else int(value)


def _ref(contract: dict[str, Any], path: str) -> dict[str, Any]:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            matches = [item for item in row if item.get('name') == key]
            if len(matches) != 1:
                raise SlotCopyRuleError(f'slot-copy.reference.{path}: missing/ambiguous')
            row = matches[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            raise SlotCopyRuleError(f'slot-copy.reference.{path}: missing')
    if not isinstance(row, dict):
        raise SlotCopyRuleError(f'slot-copy.reference.{path}: invalid declaration')
    return row


def _named(rows: list[dict[str, Any]], names: Any, label: str) -> dict[str, dict[str, Any]]:
    mapped = {row.get('name'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(names):
        raise SlotCopyRuleError(f'slot-copy.{label}: missing/duplicate/unknown declarations')
    return mapped


def _slice(body: bytes, base: int, at: int, count: int, label: str) -> bytes:
    offset = at - base
    if count < 1 or not 0 <= offset <= len(body) - count:
        raise SlotCopyRuleError(f'slot-copy.{label}: outside selected body rva={at:#x} bytes={count}')
    return body[offset:offset + count]


def _hash(raw: bytes, row: dict[str, Any], label: str, key: str = 'sha256') -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != str(row[key]).upper():
        raise SlotCopyRuleError(f'slot-copy.{label}: mismatched expectedSha256={row[key]} actualSha256={actual}')


def _declaration(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (spec.get('schema') != 'endfield.ifix-vm-slot-copy-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('slotBytes') != 12 or spec.get('instructionBytes') != 8
            or spec.get('cloneResultBoundary') != 'returned-object-unobserved'
            or spec.get('aliasBoundary') != 'reference-dereference-and-overlap-unresolved'
            or spec.get('initialValueCopy') != '12-byte-Type-Value1-Value2-before-tag-branches'
            or spec.get('copyCases') != _COPY_CASES or spec.get('storeCases') != _STORE_CASES):
        raise SlotCopyRuleError('slot-copy: unsupported schema/boundary/copy rules')
    rules = {row.get('opcode'): row for row in spec.get('rules', [])}
    if len(rules) != len(spec.get('rules', [])) or set(rules) != set(_CLAIMS):
        raise SlotCopyRuleError('slot-copy: missing/duplicate/unknown opcode rules')
    for name, row in rules.items():
        if tuple(row.get(key) for key in ('operandMeaning', 'sourceSlot', 'destinationSlot', 'helper', 'stackDeltaSlots')) != _CLAIMS[name]:
            raise SlotCopyRuleError(f'slot-copy.{name}: unsupported operand/effect declaration')
    header = spec.get('entryHeader', {})
    if (set(header) != {'opcode', 'opcodeId', 'localCountHalf', 'evaluationReserveHalf'}
            or header.get('opcode') != 'StackSpace' or type(header.get('opcodeId')) is not int
            or header.get('localCountHalf') != 'signedUpper16' or header.get('evaluationReserveHalf') != 'unsignedLower16'):
        raise SlotCopyRuleError('slot-copy: unsupported authored frame header')
    return rules


def _block(raw: bytes, base: int, name: str, targets: dict[str, int]) -> None:
    cursor = 0
    for instruction in _BLOCKS[name]:
        if isinstance(instruction, str):
            expected = bytes.fromhex(instruction)
            if raw[cursor:cursor + len(expected)] != expected:
                raise SlotCopyRuleError(f'slot-copy.{name}: unsupported shape at {base+cursor:#x}')
            cursor += len(expected)
        else:
            kind, target = instruction
            prefix = _PREFIX[kind]
            width = 1 if kind.endswith('8') else 4
            count = len(prefix) + width
            selected = raw[cursor:cursor + count]
            actual = (base + cursor + count + int.from_bytes(selected[len(prefix):], 'little', signed=True)
                      if len(selected) == count and selected.startswith(prefix) else None)
            if actual != targets[target]:
                raise SlotCopyRuleError(f'slot-copy.{name}: {kind}->{target} expected={targets[target]:#x} actual={actual}')
            cursor += count
    if cursor != len(raw):
        raise SlotCopyRuleError(f'slot-copy.{name}: unexpected trailing/short effect block bytes={len(raw)} parsed={cursor}')


def validate_slot_copy_rules(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], contract: dict[str, Any], extents: dict[int, int],
) -> dict[str, Any]:
    """Authenticate conditional copy effects after the caller's input/frame gates."""
    rules = _declaration(spec)
    if (spec.get('helperRefs') != _REFS or spec.get('tailWindowRefs') != _TAIL_REFS
            or spec.get('valueLayoutRef') != 'constrainedTypeOperand.stackEffect.valueLayout'):
        raise SlotCopyRuleError('slot-copy: unsupported inherited references')
    for key, value in spec['entryHeader'].items():
        if contract['entryHeader'].get(key) != value:
            raise SlotCopyRuleError(f'slot-copy.entryHeader.{key}: inherited declaration differs')
    metadata = image.metadata
    layout = _ref(contract, spec['valueLayoutRef'])
    owners = {name: [row for row in metadata.types if metadata.type_full_name(row) == name]
              for name in ('IFix.Core.Value', 'IFix.Core.VirtualMachine')}
    if any(len(rows) != 1 for rows in owners.values()):
        raise SlotCopyRuleError('slot-copy: Value/VirtualMachine metadata owner missing/ambiguous')
    if (layout.get('type') != 'IFix.Core.Value' or layout.get('fieldOffsets') != {'Type': 16, 'Value1': 20, 'Value2': 24}
            or runtime_type_field_offsets(metadata, image.pe, image.registration, owners['IFix.Core.Value'][0].index) != layout['fieldOffsets']):
        raise SlotCopyRuleError('slot-copy: Value field layout differs')
    tags = {row['name']: row['id'] for row in enum_members(metadata, field_defaults(metadata), 'IFix.Core.ValueType')}
    expected_tags = {'FieldReference': 6, 'ChainFieldReference': 7, 'Object': 8, 'ValueType': 9}
    if spec.get('valueTypeMembers') != expected_tags or any(tags.get(key) != value for key, value in expected_tags.items()):
        raise SlotCopyRuleError(f'slot-copy: tag comparisons differ actual={tags}')
    vm_owner = owners['IFix.Core.VirtualMachine'][0]
    fields = [row for row in metadata.fields_for(vm_owner) if metadata.string(row.name_index) == 'objectClone']
    field_spec = spec.get('objectCloneField', {})
    actual_offset = runtime_type_field_offsets(metadata, image.pe, image.registration, vm_owner.index).get('objectClone')
    pointer = (image.pe.u64_at_va(_rva(image.registration['types']) + fields[0].type_index * 8) if len(fields) == 1 else None)
    if (field_spec != {'type': 'IFix.Core.ObjectClone', 'offset': 16} or actual_offset != 16
            or pointer is None or runtime_type_name(image.pe, metadata, pointer) != field_spec['type']):
        raise SlotCopyRuleError('slot-copy: objectClone field identity/layout differs')
    targets, checked = {}, []
    for name, path in {**_REFS, **_TAIL_REFS}.items():
        row = _ref(contract, path)
        at, count = _rva(row.get('windowRva', row['rva'])), int(row['byteCount'])
        raw = (_slice(body, body_rva, at, count, path) if name in _TAIL_REFS
               else image.pe.bytes_at_va(image.pe.image_base + at, count))
        _hash(raw, row, path)
        targets[name] = _rva(row['rva'])
        checked.append(path)
        shape = {'slotMultiply': '4863c2480fafc1c3', 'pointerAdd': '488d0411c3',
                 'subtractSlot': '4863c2482bc8488bc1c3', 'zeroRegister': '4533ed',
                 'slotWidth': 'be0c000000'}.get(name)
        if shape is not None and raw != bytes.fromhex(shape):
            raise SlotCopyRuleError(f'slot-copy.{name}: unsupported arithmetic/state shape')
    targets['pushJoin'] = targets['integerStore'] + 25
    nonnull = spec['nonnullHelper']
    nonnull_raw = image.pe.bytes_at_va(image.pe.image_base + _rva(nonnull['rva']), int(nonnull['byteCount']))
    _hash(nonnull_raw, nonnull, 'nonnull')
    if len(nonnull_raw) != 20 or nonnull_raw[:14] != bytes.fromhex('4883ec284885c974054883c428c3') or nonnull_raw[-1] != 0xcc or nonnull_raw[14] != 0xe8:
        raise SlotCopyRuleError('slot-copy.nonnull: unsupported normal-return guard')
    targets['nonnull'] = _rva(nonnull['rva'])
    selected = {'Execute': (body, body_rva)}
    methods = _named(spec.get('methods', []), _METHODS, 'methods')
    for name, declaration in methods.items():
        owner, method_name, parameter_names, parameter_types, return_type = _METHODS[name]
        if tuple(declaration.get(key) for key in ('type', 'method', 'parameterNames', 'parameterTypes', 'returnType')) != (owner, method_name, parameter_names, parameter_types, return_type):
            raise SlotCopyRuleError(f'slot-copy.{name}: unsupported method identity')
        at = _rva(declaration['rva'])
        index = image.validate_method_row([declaration['methodIndex'], owner, method_name, at], label='slot-copy.' + name)
        method = metadata.methods[index]
        parameters = list(metadata.parameters_for(method))
        def type_name(type_index: int) -> str:
            type_pointer = image.pe.u64_at_va(_rva(image.registration['types']) + type_index * 8)
            return runtime_type_name(image.pe, metadata, type_pointer)
        if (method.token != _rva(declaration['token']) or method.parameter_count != len(parameter_names)
                or [metadata.string(row.name_index) for row in parameters] != parameter_names
                or [type_name(row.type_index) for row in parameters] != parameter_types or type_name(method.return_type) != return_type):
            raise SlotCopyRuleError(f'slot-copy.{name}: metadata parameters/token/return differ')
        start = image.pe.image_base + at
        count = int(declaration['bodyBytes'])
        if extents.get(start) != start + count:
            raise SlotCopyRuleError(f'slot-copy.{name}: complete pdata body extent differs')
        raw = image.pe.bytes_at_va(start, count)
        _hash(raw, declaration, name + '.body', 'bodySha256')
        selected[name] = raw, at
        targets[name] = at
    blocks = _named(spec.get('blocks', []), _BLOCKS, 'blocks')
    targets.update({name: _rva(row['rva']) for name, row in blocks.items()})
    bindings = _named(spec.get('methodBindings', []), ('copy', 'store', 'clone'), 'methodBindings')
    for name, declarations in bindings.items():
        rows = _named(declarations.get('witnesses', []), _BINDINGS[name], name + '.bindings')
        raw, base = selected[name]
        for label, declaration in rows.items():
            expected = bytes.fromhex(_BINDINGS[name][label])
            at = _rva(declaration['rva'])
            if _slice(raw, base, at, len(expected), name + '.' + label) != expected:
                raise SlotCopyRuleError(f'slot-copy.{name}.{label}: argument binding differs')
            if name != 'clone' and at + len(expected) > targets[name + '.raw']:
                raise SlotCopyRuleError(f'slot-copy.{name}.{label}: argument binding follows raw copy')
    for name, declaration in blocks.items():
        owner = name.split('.')[0] if '.' in name else 'Execute'
        raw, base = selected[owner]
        at, count = targets[name], int(declaration['byteCount'])
        window = _slice(raw, base, at, count, name)
        _hash(window, declaration, name)
        _block(window, at, name, targets)
    for chain in _CHAINS:
        for previous, following in zip(chain, chain[1:]):
            if targets[previous] + blocks[previous]['byteCount'] != targets[following]:
                raise SlotCopyRuleError(f'slot-copy.{previous}: noncontiguous fallthrough to {following}')
    if (targets['entryHomes'] != body_rva or targets['vmRegister'] + blocks['vmRegister']['byteCount'] != targets['loopState']
            or targets['stloc'] + blocks['stloc']['byteCount'] != targets['managedClear']
            or any(targets[name + '.return'] + blocks[name + '.return']['byteCount'] != selected[name][1] + len(selected[name][0]) for name in ('copy', 'store'))):
        raise SlotCopyRuleError('slot-copy: entry/state/clear/return boundary differs')
    entries = []
    for name, declaration in rules.items():
        if declaration['opcodeId'] != opcode_ids.get(name):
            raise SlotCopyRuleError(f'slot-copy.{name}: opcode enum ID differs')
        actual = resolve_dispatch_entry(body, body_rva, _rva(spec['dispatchStartRva']), declaration['opcodeId'])
        if actual != _rva(declaration['entryRva']) or actual != targets[name.lower()]:
            raise SlotCopyRuleError(f'slot-copy.{name}: selected dispatch entry differs actual={actual:#x}')
        entries.append({'opcode': name, 'entryRva': hex(actual), 'helper': declaration['helper'], 'stackDeltaSlots': declaration['stackDeltaSlots']})
    return {'status': 'validated_conditional_slot_copy_rules', 'entries': entries,
            'completeHelperBodies': ['copy', 'store', 'clone'], 'inheritedWindowsChecked': checked,
            'copyCases': dict(_COPY_CASES), 'storeCases': dict(_STORE_CASES),
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['runtime-stack-height-and-frame-storage', 'managed-array-index-validity-and-contents',
                           'Clone-return-identity-and-object-internals', 'reference-dereference-and-alias-semantics',
                           'overlapping-source-destination-especially-FieldReference', 'actual-patch-entry-and-execution']}


def project_slot_copy_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Project authored slot expressions; never reconstruct live stack values."""
    rules = _declaration(spec)
    rows = []
    for method in decoded['methods']:
        instructions = method['instructions']
        first = instructions[0] if instructions else None
        local_count = None
        if first is not None and first['name'] == spec['entryHeader']['opcode']:
            raw = first['operandUnsigned']
            if type(raw) is not int or not 0 <= raw <= 0xffffffff or first['opcode'] != spec['entryHeader']['opcodeId']:
                raise SlotCopyRuleError('slot-copy.projection: malformed authored frame header')
            local_count = (raw >> 16) & 0xffff
            if local_count >= 0x8000:
                local_count -= 0x10000
            if local_count < 0:
                local_count = None
        for instruction in instructions:
            name = instruction['name']
            if name not in rules:
                continue
            rule = rules[name]
            raw = instruction['operandUnsigned']
            if type(raw) is not int or not 0 <= raw <= 0xffffffff or instruction['opcode'] != rule['opcodeId']:
                raise SlotCopyRuleError(f'slot-copy.projection.{name}: malformed operand/opcode ID')
            signed = raw if raw < 0x80000000 else raw - 0x100000000
            if 'operandSigned' in instruction and instruction['operandSigned'] != signed:
                raise SlotCopyRuleError(f'slot-copy.projection.{name}: inconsistent signed operand')
            row = {'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'], 'offset': instruction['offset'],
                   'opcode': name, 'operandUnsigned': raw, 'operandSigned': signed, 'operandMeaning': rule['operandMeaning'],
                   'sourceSlot': rule['sourceSlot'], 'destinationSlot': rule['destinationSlot'], 'helper': rule['helper'],
                   'stackDeltaSlots': rule['stackDeltaSlots'], 'instructionAdvanceBytes': 8,
                   'initialValueCopy': spec['initialValueCopy'], 'typeAndValue2Effect': 'preserve-source-bits',
                   'conditionalCases': dict(_STORE_CASES if name == 'Stloc' else _COPY_CASES),
                   'managedPositionExpression': '(slot-evaluationStackBase)/12',
                   'consumedManagedSlotClear': 'managedStack[(original-top-minus-one-evaluationStackBase)/12]=null' if name == 'Stloc' else 'none',
                   'runtimeSourceTag': None, 'runtimeManagedReference': None, 'aliasBoundary': spec['aliasBoundary'],
                   'cloneResultBoundary': spec['cloneResultBoundary'], 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
                   'selectedWhen': 'valid-slot-and-managed-storage-and-all-selected-helper-calls-return-normally'}
            if name == 'Dup':
                row.update({'slotIndex': None, 'slotRangeStatus': 'runtime-top-minus-one-unobserved', 'localSlotCount': None})
            else:
                domain = 'argument' if name == 'Ldarg' else 'local'
                range_status = ('negative-index' if signed < 0 else
                                'runtime-argsCount-unobserved' if domain == 'argument' else
                                'frame-header-unresolved' if local_count is None else
                                'authored-local-range' if signed < local_count else 'out-of-range')
                row.update({'slotDomain': domain, 'slotIndex': signed, 'slotRangeStatus': range_status,
                            'localSlotCount': local_count if domain == 'local' else None})
                if range_status in ('negative-index', 'out-of-range'):
                    row['diagnostic'] = {'check': 'authored-slot-index', 'actual': signed,
                                         'expected': {'minimum': 0, 'exclusiveMaximum': local_count if domain == 'local' else None},
                                         'scope': f"method={method['index']} instruction={instruction['index']}"}
            rows.append(row)
    return rows
