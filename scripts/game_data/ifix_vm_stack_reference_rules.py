"""Prove a one-hop IFix StackReference decoder from selected native bytes.

The caller authenticates explicit installed inputs, complete Execute and the
existing Ldloca/basic/update/copy rules. A qword spanning Value1 and Value2 is
an address representation, not evidence that the address contains valid memory.
This helper authenticates the resolver's complete effect grammar and only the
already-reviewed Conv_I8 consumer and UpdateReference pointer-load join.
No pointed memory is read or executed by the validator or projector.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index
from scripts.game_data.il2cpp.protocol import (
    enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name,
)


class StackReferenceRuleError(ValueError):
    """A reference decoder claim differs from its selected native evidence."""


_METHOD_REFS = {
    'resolve': 'basicOpcodeRules.preconversionMethod',
    'clone': 'slotCopyRules.methods.clone',
    'runtimeException': 'delegateConstruction.methodCalls.nullFallbackException',
    'update': 'initobjStackEffect.updateReferenceMethod',
}
_METHOD_SIGNATURES = {
    'resolve': ('IFix.Core.VirtualMachine', 'resolveStackReference', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]']),
    'clone': ('IFix.Core.ObjectClone', 'Clone', ['object']),
    'runtimeException': ('IFix.Core.VirtualMachine', 'throwRuntimeException', ['System.Exception', 'bool']),
    'update': ('IFix.Core.EvaluationStackOperation', 'UpdateReference', ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'IFix.Core.VirtualMachine', 'System.Type']),
}
_HELPER_REFS = {
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'postStore': 'delegateBridgeRules.referenceWriteBarrier',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'nonnull': 'slotCopyRules.nonnullHelper',
}
_BINDINGS = {'zeroBoxedResult': '33db498bf9', 'valueBaseVmArguments': '498be8488bf24c8bf1'}
_CASES = {
    'incoming-tag!=StackReference=4': 'return-without-resolver-slot-or-managed-store',
    'incoming-tag=4-and-pointer=0': 'InvalidProgramException-message-route-throwRuntimeException-then-INT3',
    'copied-tag=Object=8': 'read-managedStack[target.Value1-at-read]; store-at-destination-position; rebase-Value1',
    'copied-tag=ValueType=9': 'null-or-Clone-return; store-at-destination-position; rebase-Value1',
    'other-copied-tag': 'return-copied-12-byte-Value-without-another-dereference-or-managed-store',
}
_PREFIX = {'call': b'\xe8', 'jump8': b'\xeb', 'je8': b'\x74', 'jne8': b'\x75',
           'je': b'\x0f\x84', 'jne': b'\x0f\x85'}
_LOADS = {'nullType': b'\x48\x8b\x0d', 'nullLiteral': b'\x48\x8b\x15'}
# Complete effect blocks, including the fail-stop null route. Registers and
# field offsets are encoding rules; build addresses/hashes live in the contract.
_BLOCKS = {
    'incoming': ('833e04', ('jne', 'normalReturn'), '4c8b46044d85c0', ('je', 'nullRoute')),
    'copyAndCases': ('418b4008488bcef2410f1000482bcdf20f1106894608'
                     '48b8abaaaaaaaaaaaa2a48f7e9488bea48d1fd488bc548c1e83f4803e8'
                     '833e08', ('je8', 'object'), '833e09', ('jne8', 'normalReturn')),
    'boxed': ('4963400448395cc720', ('je8', 'managedStore'),
              '496340044533c0498b4e10488b54c720', ('call', 'clone'), '488bd8'),
    'managedStore': ('488bd3488bcf', ('call', 'assignmentCheck'),
                     '4863cd48895ccf204883c104488d0ccf'),
    'managedCommit': (('call', 'postStore'), '896e04'),
    'normalReturn': ('488b5c2430488b6c2438488b742440488b7c24484883c420415ec3',),
    'object': ('49634004488bcf488b5cc720488bd3', ('call', 'assignmentCheck'),
               '4863c548895cc7204883c004488d0cc7', ('jump8', 'managedCommit')),
    'nullRoute': (('load', 'nullType'), ('call', 'nullObjectHelper'), ('load', 'nullLiteral'),
                  '4533c0488bc8488bd8', ('call', 'nullConstructor'),
                  '4533c941b001488bd3498bce', ('call', 'runtimeException'), 'cc'),
    'consumerInput': ('8bd6498bcc', ('call', 'subtractSlot'),
                      '488bd84c896c24204d8bcf4c8b842410040000488bd0488bcf', ('call', 'resolve')),
    'consumerTagRead': ('488bcb', ('call', 'nonnull'), '8b0b'),
}
_EFFECT_CHAIN = ('incoming', 'copyAndCases', 'boxed', 'managedStore', 'managedCommit', 'normalReturn', 'object', 'nullRoute')
_MESSAGE = b'resolveStackReference: StackReference points to null'


def _rva(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _ref(contract: dict[str, Any], path: str) -> dict[str, Any]:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            found = [r for r in row if r.get('name', r.get('role')) == key]
            if len(found) != 1:
                raise StackReferenceRuleError(f'stack-reference.{path}: missing/ambiguous reference')
            row = found[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            raise StackReferenceRuleError(f'stack-reference.{path}: missing reference')
    if not isinstance(row, dict):
        raise StackReferenceRuleError(f'stack-reference.{path}: invalid reference')
    return row


def _named(rows: list[dict[str, Any]], names: Any, label: str) -> dict[str, dict[str, Any]]:
    mapped = {row.get('name'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(names):
        raise StackReferenceRuleError(f'stack-reference.{label}: missing/duplicate/unknown declarations')
    return mapped


def _slice(raw: bytes, base: int, site: int, size: int, label: str) -> bytes:
    offset = site - base
    if size < 1 or not 0 <= offset <= len(raw) - size:
        raise StackReferenceRuleError(f'stack-reference.{label}: outside selected body rva={site:#x} bytes={size}')
    return raw[offset:offset + size]


def _hash(raw: bytes, row: dict[str, Any], label: str, key: str = 'sha256') -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != str(row[key]).upper():
        raise StackReferenceRuleError(f'stack-reference.{label}: mismatched expectedSha256={row[key]} actualSha256={actual}')


def _declaration(spec: dict[str, Any]) -> None:
    if (spec.get('schema') != 'endfield.ifix-vm-stack-reference-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional' or spec.get('executionBoundary') != 'unobserved'
            or spec.get('methodRefs') != _METHOD_REFS or spec.get('helperRefs') != _HELPER_REFS
            or spec.get('producerEvidenceRef') != 'initobjStackEffect'
            or spec.get('valueLayoutRef') != 'constrainedTypeOperand.stackEffect.valueLayout'
            or spec.get('slotBytes') != 12 or spec.get('pointerBytes') != 8
            or spec.get('pointerPayloadOffset') != 4 or spec.get('pointerWordOrder') != ['Value1-low32', 'Value2-high32']
            or spec.get('dereferenceDepth') != 1 or spec.get('cases') != _CASES
            or spec.get('pointerValidityBoundary') != 'unobserved' or spec.get('overlapBoundary') != 'unresolved'
            or spec.get('cloneResultBoundary') != 'returned-object-unobserved'):
        raise StackReferenceRuleError('stack-reference: unsupported schema/encoding/effect/boundary')
    ids = spec.get('opcodeIds', {})
    if set(ids) != {'Ldloca', 'Conv_I8', 'StackSpace'} or any(type(value) is not int or value < 0 for value in ids.values()):
        raise StackReferenceRuleError('stack-reference: unsupported opcode declarations')


def decode_pointer_words(value1_bits: int, value2_bits: int) -> int:
    """Combine two unsigned words as representation only; never read memory."""
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in (value1_bits, value2_bits)):
        raise StackReferenceRuleError('stack-reference.pointer-words: expected two unsigned int32 bit patterns')
    return value1_bits | value2_bits << 32


def _block(raw: bytes, base: int, name: str, targets: dict[str, int]) -> None:
    cursor = 0
    for token in _BLOCKS[name]:
        if isinstance(token, str):
            expected = bytes.fromhex(token)
            if raw[cursor:cursor + len(expected)] != expected:
                raise StackReferenceRuleError(f'stack-reference.{name}: unsupported shape at {base+cursor:#x}')
            cursor += len(expected)
        elif token[0] == 'load':
            target = token[1]
            code = raw[cursor:cursor + 7]
            actual = (base + cursor + 7 + int.from_bytes(code[3:], 'little', signed=True)
                      if len(code) == 7 and code.startswith(_LOADS[target]) else None)
            if actual != targets[target]:
                raise StackReferenceRuleError(f'stack-reference.{name}: {target} usage-cell target differs')
            cursor += 7
        else:
            kind, target = token
            prefix = _PREFIX[kind]
            count = len(prefix) + (1 if kind.endswith('8') else 4)
            code = raw[cursor:cursor + count]
            actual = (base + cursor + count + int.from_bytes(code[len(prefix):], 'little', signed=True)
                      if len(code) == count and code.startswith(prefix) else None)
            if actual != targets[target]:
                raise StackReferenceRuleError(f'stack-reference.{name}: {kind}->{target} expected={targets[target]:#x} actual={actual}')
            cursor += count
    if cursor != len(raw):
        raise StackReferenceRuleError(f'stack-reference.{name}: trailing/short effect block bytes={len(raw)} parsed={cursor}')


def _method(image: Any, row: dict[str, Any], owner: str, name: str, params: list[str], extents: dict[int, int], label: str) -> tuple[bytes, int]:
    md, pe = image.metadata, image.pe
    def type_name(index: int) -> str:
        pointer = pe.u64_at_va(_rva(image.registration['types']) + index * 8)
        if pe.bytes_at_va(pointer, 16)[11] & 0x20:
            raise StackReferenceRuleError(f'stack-reference.{label}: byref method carrier differs')
        return runtime_type_name(pe, md, pointer)
    candidates = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
                  if md.string(m.name_index) == name and [type_name(p.type_index) for p in md.parameters_for(m)] == params]
    if len(candidates) != 1 or (row.get('type'), row.get('method')) != (owner, name):
        raise StackReferenceRuleError(f'stack-reference.{label}: named method identity missing/ambiguous')
    m = candidates[0]
    result = 'object' if label == 'clone' else 'void'
    if (m.token != _rva(row['token']) or m.parameter_count != len(params)
            or bool(m.flags & 0x10) != (label == 'update') or type_name(m.return_type) != result
            or label == 'resolve' and [md.string(p.name_index) for p in md.parameters_for(m)] != ['value', 'stackBase', 'managedStack']):
        raise StackReferenceRuleError(f'stack-reference.{label}: metadata token/signature/kind differs')
    at = _rva(row['rva'])
    image.validate_method_row([m.index, owner, name, at], label='stack-reference.' + label)
    count = int(row['bodyBytes']);start = pe.image_base + at
    if extents.get(start) != start + count:
        raise StackReferenceRuleError(f'stack-reference.{label}: complete pdata extent differs')
    raw = pe.bytes_at_va(start, count)
    _hash(raw, row, label + '.body', 'bodySha256')
    return raw, at


def validate_stack_reference_rules(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], contract: dict[str, Any], extents: dict[int, int],
) -> dict[str, Any]:
    """Prove native one-hop rules within the caller's selected input/producer gate."""
    _declaration(spec)
    layout = _ref(contract, spec['valueLayoutRef'])
    owners = [row for row in image.metadata.types if image.metadata.type_full_name(row) == 'IFix.Core.Value']
    if (len(owners) != 1 or layout.get('type') != 'IFix.Core.Value'
            or layout.get('fieldOffsets') != {'Type': 16, 'Value1': 20, 'Value2': 24}
            or runtime_type_field_offsets(image.metadata, image.pe, image.registration, owners[0].index) != layout['fieldOffsets']):
        raise StackReferenceRuleError('stack-reference: Value layout differs')
    tags = {row['name']: row['id'] for row in enum_members(image.metadata, field_defaults(image.metadata), 'IFix.Core.ValueType')}
    expected_tags = {'StackReference': 4, 'Object': 8, 'ValueType': 9}
    if spec.get('valueTypeMembers') != expected_tags or any(tags.get(key) != value for key, value in expected_tags.items()):
        raise StackReferenceRuleError('stack-reference: Value tag comparisons differ')
    selected, targets = {}, {}
    for label, path in _METHOD_REFS.items():
        owner, name, params = _METHOD_SIGNATURES[label]
        selected[label] = _method(image, _ref(contract, path), owner, name, params, extents, label)
        targets[label] = selected[label][1]
    for label, path in _HELPER_REFS.items():
        row = _ref(contract, path)
        at, count = _rva(row['rva']), int(row['byteCount'])
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, path)
        targets[label] = at
    null = spec['nullConstructor']
    selected['nullConstructor'] = _method(image, null, 'System.InvalidProgramException', '.ctor', ['string'], extents, 'nullConstructor')
    targets['nullConstructor'] = selected['nullConstructor'][1]
    opaque = spec['nullObjectHelper']
    if opaque.get('evidenceBoundary') != 'unresolved':
        raise StackReferenceRuleError('stack-reference.nullObjectHelper: child outcome must remain unresolved')
    at = _rva(opaque['rva']);count = int(opaque['byteCount'])
    _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), opaque, 'nullObjectHelper')
    targets['nullObjectHelper'] = at
    cells = _named(spec['nullCells'], ('nullType', 'nullLiteral'), 'nullCells')
    for label, row in cells.items():
        at = _rva(row['cellRva']);raw = image.pe.bytes_at_va(image.pe.image_base + at, 8)
        if raw.hex().upper() != row['rawHex'].upper():
            raise StackReferenceRuleError(f'stack-reference.{label}: stored usage cell differs')
        targets[label] = at
        if label == 'nullType':
            index = unresolved_usage_index(raw, image.registration['typesCount'], tag=1, source='stack-reference.nullType', offset=at)
            pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
            if image.pe.bytes_at_va(pointer, 16)[11] & 0x20 or runtime_type_name(image.pe, image.metadata, pointer) != 'System.InvalidProgramException':
                raise StackReferenceRuleError('stack-reference.nullType: exception type carrier differs')
        else:
            md = image.metadata;table, pool = md.sections['stringLiteral'], md.sections['stringLiteralData']
            index = unresolved_usage_index(raw, table.size // 8, tag=5, source='stack-reference.nullLiteral', offset=at)
            offset = table.offset + index * 8
            start, size = literal_record(md.buf[offset:offset+8], pool.size, source='stack-reference.nullLiteral', offset=offset)
            if md.buf[pool.offset+start:pool.offset+start+size] != _MESSAGE:
                raise StackReferenceRuleError('stack-reference.nullLiteral: exception message differs')
    resolver, resolver_base = selected['resolve']
    blocks = _named(spec['blocks'], _BLOCKS, 'blocks')
    targets.update({name: _rva(row['rva']) for name, row in blocks.items()})
    bindings = _named(spec['argumentBindings'], _BINDINGS, 'argumentBindings')
    for label, row in bindings.items():
        at = _rva(row['rva']);expected = bytes.fromhex(_BINDINGS[label])
        if _slice(resolver, resolver_base, at, len(expected), label) != expected or at + len(expected) > targets['incoming']:
            raise StackReferenceRuleError(f'stack-reference.{label}: argument binding differs')
    for name, row in blocks.items():
        raw, base = (body, body_rva) if name.startswith('consumer') else selected['resolve']
        window = _slice(raw, base, targets[name], row['byteCount'], name)
        _hash(window, row, name)
        _block(window, targets[name], name, targets)
    for previous, following in zip(_EFFECT_CHAIN, _EFFECT_CHAIN[1:]):
        if targets[previous] + blocks[previous]['byteCount'] != targets[following]:
            raise StackReferenceRuleError(f'stack-reference.{previous}: noncontiguous effect boundary')
    if (targets['nullRoute'] + blocks['nullRoute']['byteCount'] != resolver_base + len(resolver)
            or targets['consumerInput'] + blocks['consumerInput']['byteCount'] != targets['consumerTagRead']):
        raise StackReferenceRuleError('stack-reference: final body/consumer boundary differs')
    producer = _ref(contract, spec['producerEvidenceRef'])
    if producer.get('addressProducer') != 'Ldloca' or producer.get('referenceValueType') != {'enumType': 'IFix.Core.ValueType', 'name': 'StackReference', 'id': 4}:
        raise StackReferenceRuleError('stack-reference: inherited local-address producer differs')
    producer_rows = {r['name']: r for r in producer['witnesses']}
    for label, expected_hex, source in (
        ('ldlocaAddressStore', '4989442404', (body, body_rva)),
        ('ldlocaReferenceTag', '41c7042404000000', (body, body_rva)),
        ('stackReferenceTargetSlot', '488b5304', selected['update']),
    ):
        row = producer_rows.get(label)
        if row is None or row.get('hex') != expected_hex or _slice(*source, _rva(row['rva']), len(bytes.fromhex(expected_hex)), label) != bytes.fromhex(expected_hex):
            raise StackReferenceRuleError(f'stack-reference.{label}: inherited pointer encoding differs')
    entries = {}
    for name, at in (('Ldloca', _rva(spec['producerEntryRva'])), ('Conv_I8', targets['consumerInput'])):
        if spec['opcodeIds'][name] != opcode_ids.get(name):
            raise StackReferenceRuleError(f'stack-reference.{name}: opcode enum differs')
        actual = resolve_dispatch_entry(body, body_rva, _rva(spec['dispatchStartRva']), spec['opcodeIds'][name])
        if actual != at:
            raise StackReferenceRuleError(f'stack-reference.{name}: finite dispatch entry differs actual={actual:#x}')
        entries[name] = hex(actual)
    if spec['opcodeIds']['StackSpace'] != opcode_ids.get('StackSpace') or spec['opcodeIds']['StackSpace'] != contract['entryHeader']['opcodeId']:
        raise StackReferenceRuleError('stack-reference: authored frame-header enum differs')
    return {'status': 'validated_conditional_one_hop_stack_reference_rules', 'entries': entries,
            'pointerRepresentation': 'unsigned-Value1-low32-plus-Value2-high32; qword-at-unboxed-offset4',
            'dereferenceDepth': 1, 'cases': dict(_CASES), 'updateJoin': 'same-qword-pointer-load; inherited-UpdateReference-rule',
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['pointed-storage-validity-and-observed-Value', 'managed-index-validity-and-contents',
                           'overlap-and-helper-mutation', 'Clone-return-identity', 'actual-stack-values-and-patch-execution']}


def project_stack_reference_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose producer encoding and decoder alternatives, without stack simulation."""
    _declaration(spec)
    rows = []
    for method in decoded['methods']:
        instructions = method['instructions'];first = instructions[0] if instructions else None
        local_count = None
        if first is not None and first['name'] == 'StackSpace':
            raw = first['operandUnsigned']
            if type(raw) is not int or not 0 <= raw <= 0xffffffff or first['opcode'] != spec['opcodeIds']['StackSpace']:
                raise StackReferenceRuleError('stack-reference.projection: malformed frame header')
            local_count = raw >> 16
            if local_count >= 0x8000:
                local_count = None
        for instruction in instructions:
            name = instruction['name']
            if name not in ('Ldloca', 'Conv_I8'):
                continue
            raw = instruction['operandUnsigned']
            if type(raw) is not int or not 0 <= raw <= 0xffffffff or instruction['opcode'] != spec['opcodeIds'][name]:
                raise StackReferenceRuleError(f'stack-reference.projection.{name}: invalid operand/opcode')
            signed = raw if raw < 0x80000000 else raw - 0x100000000
            if 'operandSigned' in instruction and instruction['operandSigned'] != signed:
                raise StackReferenceRuleError(f'stack-reference.projection.{name}: inconsistent signed operand')
            row = {'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'], 'offset': instruction['offset'],
                   'opcode': name, 'operandUnsigned': raw, 'operandSigned': signed,
                   'pointerWordOrder': list(spec['pointerWordOrder']), 'runtimePointer': None,
                   'pointerValidityBoundary': 'unobserved', 'overlapBoundary': 'unresolved',
                   'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved'}
            if name == 'Ldloca':
                status = ('negative-index' if signed < 0 else 'frame-header-unresolved' if local_count is None else
                          'authored-local-range' if signed < local_count else 'out-of-range')
                row.update({'operandMeaning': 'whole-signed-int32-local-index', 'slotIndex': signed,
                            'localSlotCount': local_count, 'slotRangeStatus': status, 'resultTag': 'StackReference',
                            'pointerExpression': 'localBase+operand*12', 'stackDeltaSlots': 1,
                            'selectedWhen': 'inherited-Ldloca-route-with-valid-frame-and-normal-helper-returns'})
                if status in ('negative-index', 'out-of-range'):
                    row['diagnostic'] = {'check': 'authored-local-index', 'actual': signed,
                                         'expected': {'minimum': 0, 'exclusiveMaximum': local_count},
                                         'scope': f"method={method['index']} instruction={instruction['index']}"}
            else:
                row.update({'operandMeaning': 'unused-by-selected-resolver-input-path',
                            'resolverInput': 'original-top-minus-one', 'dereferenceDepth': 1,
                            'incomingReferenceTag': None, 'copiedTargetTag': None, 'conditionalCases': dict(_CASES),
                            'postResolverTag': 'normal-return-slot-tag; conversion-rules-owned-by-basicOpcodeRules',
                            'referenceProducerJoin': 'runtime-stack-value-unobserved',
                            'selectedWhen': 'selected-Conv_I8-entry-and-resolver-returns-normally'})
            rows.append(row)
    return rows
