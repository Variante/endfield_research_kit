"""Derive whole-Value alias equations from authenticated AnonymousStorey bodies.

The selected instanceFieldRules proof supplies complete Ldfld/Stfld programs,
named layouts and negative Execute routes. This group adds a storage calculation
under explicit hypotheses: source and destination are the same complete Value
or distinct nonoverlapping Values, and managed arrays are either identical or
distinct nonoverlapping arrays. Their indexes, bases and actual aliases are
caller-supplied hypotheses; equality of indexes from different bases does not
establish Value aliasing. Partial overlap and helper-induced mutation stay open.

Both storey methods snapshot all 12 source bytes before the first destination
write. For signed tags >= Object, Stfld rebases the stored field's Value1 before
reading the source Value1. An exact whole-Value self-store therefore reads
managedStack[fieldIndex], even if the incoming Value1 differed. Ldfld rebases
the evaluation destination before reading managedFields[fieldIndex]; that read
does not depend on the stored field's Value1. Each selected managed read precedes
the corresponding managed write. No Clone request or explicit managed clear
occurs inside these two complete storey bodies. Lower tags preserve the copied
bits without a managed transfer; their reference meaning is not expanded here.

The equations describe these callee programs after valid receiver selection and
normal, nonmutating helper returns. They do not establish actual VM stack state,
object identity separation, receiver conversion success, recursive aliases,
array bounds, raw anonymous-storey file framing, or patch invocation. The pure
validator requires the caller's selected-native instance proof; it never treats
an arbitrary authored alias or a stored method name as runtime evidence.
"""
from __future__ import annotations

from typing import Any


class InstanceAliasRuleError(ValueError):
    """An instance alias derivation lacks its inherited proof or hypotheses."""


_ASSUMPTIONS = [
    'same-complete-Value-or-distinct-nonoverlapping-complete-Values',
    'aligned-12-byte-Values-valid-field-and-evaluation-positions-and-managed-indexes',
    'same-complete-managed-array-or-distinct-nonoverlapping-managed-arrays',
    'normal-helper-return-without-other-Value-or-managed-storage-mutation',
    'valid-AnonymousStorey-receiver-already-selected',
]
_EFFECTS = {
    'initialSnapshot': 'all-12-source-bytes-before-first-destination-write',
    'tagSelection': 'signed-source-tag-at-least-Object-8-after-initial-copy',
    'Stfld': 'field.Value1=fieldIndex-before-reading-source.Value1',
    'Ldfld': 'destination.Value1=evaluationPosition-before-reading-managedFields[fieldIndex]',
    'managedOrdering': 'selected-managed-read-before-managed-write',
    'managedClear': 'none-explicit-in-complete-storey-Ldfld-Stfld-bodies',
    'cloneRequest': 'none-in-complete-storey-Ldfld-Stfld-bodies',
    'lowerTags': 'preserve-copied-Value-bits-without-managed-transfer',
    'objectIdentity': 'forward-selected-incoming-reference-without-identity-separation-claim',
}
_CLAIMS = {
    'schema': 'endfield.ifix-vm-instance-alias-rules.v1',
    'evidenceBoundary': 'conditional',
    'executionBoundary': 'unobserved',
    'sourceRef': 'instanceFieldRules',
    'sourceSchema': 'endfield.ifix-vm-instance-field-rules.v1',
    'methodRefs': {'Ldfld': 'instanceFieldRules.methods.Ldfld', 'Stfld': 'instanceFieldRules.methods.Stfld'},
    'effects': _EFFECTS,
    'assumptions': _ASSUMPTIONS,
    'scope': 'AnonymousStorey-callee-after-valid-negative-Execute-receiver-selection',
    'partialOverlapBoundary': 'unresolved',
    'runtimeAliasSelection': 'unobserved',
    'fileTableJoinBoundary': 'not-asserted',
}
_CASES = {
    'Ldfld': 'managedFields[fieldIndex] -> managedStack[evaluationPosition]',
    'Stfld': 'managedStack[sameValue?fieldIndex:incomingSource.Value1] -> managedFields[fieldIndex]',
}


def _need(ok: bool, detail: str) -> None:
    if not ok:
        raise InstanceAliasRuleError('instance-alias.' + detail)


def _declaration(spec: dict[str, Any]) -> None:
    _need(isinstance(spec, dict) and all(type(spec.get(k)) is type(v) and spec.get(k) == v
                                      for k, v in _CLAIMS.items()), 'unsupported schema/proof/boundary')
    _need(set(spec.get('cases', {})) == set(_CASES), 'case catalog differs')
    for name, expression in _CASES.items():
        case = spec['cases'][name]
        _need(set(case) == {'opcodeId', 'expression'} and type(case.get('opcodeId')) is int
              and 0 <= case['opcodeId'] <= 0x7fffffff and case.get('expression') == expression,
              'case declaration differs: ' + name)


def validate_instance_alias_rules(spec: dict[str, Any], source: dict[str, Any],
                                  source_audit: dict[str, Any]) -> dict[str, Any]:
    """Require the selected native instance proof before exposing alias equations.

    Parent validation supplies source_audit from the same selected NativeImage
    and contract. This pure derived group does not re-open native inputs or
    duplicate the complete method catalog and its passed body checks.
    """
    _declaration(spec)
    _need(source.get('schema') == spec['sourceSchema']
          and source.get('evidenceBoundary') == 'conditional' and source.get('executionBoundary') == 'unobserved'
          and source_audit.get('status') == 'validated_conditional_instance_field_rules'
          and source_audit.get('storeyMethods') == ['Ldfld', 'Stfld', 'Get', 'Set']
          and type(source_audit.get('managedTagThreshold')) is int and source_audit['managedTagThreshold'] == 8
          and source_audit.get('evidenceBoundary') == 'conditional'
          and source_audit.get('executionBoundary') == 'unobserved', 'selected complete native source proof required')
    _need(type(source.get('slotBytes')) is int and source['slotBytes'] == 12
          and source.get('fileTableJoinBoundary') == 'not-asserted'
          and source.get('consumedManagedClear') == source_audit.get('consumedManagedClear')
              == 'none-explicit-in-selected-negative-route', 'source slot/clear/file boundary differs')
    field = source.get('fieldLayout', {})
    _need(field.get('type') == 'IFix.Core.AnonymousStorey'
          and set(field.get('fields', {})) == {'unmanagedFields', 'managedFields'}
          and field['fields']['unmanagedFields'].get('type') == 'IFix.Core.Value[]'
          and field['fields']['managedFields'].get('type') == 'object[]', 'source storey storage differs')
    rows = source.get('rules', []); names = [row.get('opcode') for row in rows]
    audit_rows = source_audit.get('entries', []); audit_names = [row.get('opcode') for row in audit_rows]
    _need(len(names) == len(set(names)) == 2 and set(names) == set(_CASES)
          and len(audit_names) == len(set(audit_names)) == 2 and set(audit_names) == set(_CASES),
          'source negative route proof missing/duplicate')
    for name in _CASES:
        row = next(row for row in rows if row['opcode'] == name)
        audit = next(row for row in audit_rows if row['opcode'] == name)
        delta = 0 if name == 'Ldfld' else -2
        _need(type(row.get('opcodeId')) is int and row['opcodeId'] == spec['cases'][name]['opcodeId']
              and type(audit.get('opcodeId')) is int and audit['opcodeId'] == row['opcodeId']
              and row.get('selectedWhen') == 'signed-Operand-negative'
              and row.get('operandMeaning') == 'bitwise-complement-storey-field-index'
              and type(row.get('stackDeltaSlots')) is int and row['stackDeltaSlots'] == delta
              and type(audit.get('stackDeltaSlots')) is int and audit['stackDeltaSlots'] == delta
              and audit.get('entryRva') == row.get('entryRva'), 'source negative route differs: ' + name)
        method = source.get('methods', {}).get(name, {})
        _need(method.get('type') == 'IFix.Core.AnonymousStorey' and method.get('method') == name
              and type(method.get('parameterCount')) is int and method['parameterCount'] == 4
              and method.get('parameterTypes') == ['int', 'IFix.Core.Value*', 'IFix.Core.Value*', 'object[]']
              and method.get('returnTypeName') == 'void'
              and type(method.get('bodyBytes')) is int and method['bodyBytes'] > 0,
              'source complete storey method differs: ' + name)
        for key in ('static', 'generic'):
            _need(key not in method or (type(method[key]) is bool and method[key] is False),
                  'source method kind declaration differs: ' + name + '.' + key)
    return dict(status='validated_conditional_instance_alias_rules', sourceRef=spec['sourceRef'],
                methodRefs=dict(spec['methodRefs']), effects=dict(_EFFECTS), assumptions=list(_ASSUMPTIONS),
                runtimeAliasSelection='unobserved', partialOverlapBoundary='unresolved',
                evidenceBoundary='conditional', executionBoundary='unobserved',
                unresolved=['runtime-Value-and-managed-array-alias-relations', 'partial-or-unaligned-overlap',
                            'helper-induced-storage-mutation', 'receiver-conversion-and-array-storage-validity',
                            'lower-tag-recursive-reference-meaning', 'actual-execution'])


def derive_instance_alias_effect(operation: str, *, source_tag: int, source_value1: int,
                                 field_index: int, evaluation_position: int,
                                 value_relation: str = 'distinct-nonoverlapping-Values',
                                 managed_array_relation: str = 'distinct-nonoverlapping-arrays',
                                 storage_relation: str = 'whole-slots') -> dict[str, Any]:
    """Calculate a hypothetical storey effect; positions do not infer aliases.

    field_index is relative to the storey's Value array. evaluation_position is
    relative to the supplied evaluation base. An explicit same-Value hypothesis
    can hold with unequal indexes when the bases differ. Managed references are
    symbolic incoming array cells, including when arrays or indexes are shared.
    """
    _need(operation in _CASES, 'unsupported operation')
    _need(storage_relation == 'whole-slots', 'partial/unaligned Value overlap remains unresolved')
    _need(value_relation in ('same-complete-Value', 'distinct-nonoverlapping-Values'),
          'unsupported Value alias relation')
    _need(managed_array_relation in ('same-complete-array', 'distinct-nonoverlapping-arrays'),
          'partial/unknown managed-array overlap remains unresolved')
    for role, value in [('source_tag', source_tag), ('source_value1', source_value1)]:
        _need(type(value) is int and -(1 << 31) <= value < (1 << 31), 'expected signed Int32: ' + role)
    for role, value in [('field_index', field_index), ('evaluation_position', evaluation_position)]:
        _need(type(value) is int and 0 <= value < (1 << 31), 'expected nonnegative Int32 position: ' + role)
    same_value = value_relation == 'same-complete-Value'
    shared_arrays = managed_array_relation == 'same-complete-array'
    arrays = {name: 'sharedManaged' if shared_arrays else name for name in ('managedStack', 'managedFields')}
    managed = source_tag >= 8
    destination_value1 = (evaluation_position if operation == 'Ldfld' else field_index) if managed else source_value1
    source_value1_after = destination_value1 if same_value else source_value1
    read = None; writes = []; source_owner = None; destination_owner = None
    events = ['snapshot-all-12-source-bytes', 'write-all-12-destination-bytes',
              'read-source-tag-after-initial-copy']
    if managed:
        events.append('write-destination-Value1')
        read_index = field_index if operation == 'Ldfld' or same_value else source_value1
        _need(read_index >= 0, 'invalid hypothetical selected managed read index')
        source_array = 'managedFields' if operation == 'Ldfld' else 'managedStack'
        target_array = 'managedStack' if operation == 'Ldfld' else 'managedFields'
        target_index = evaluation_position if operation == 'Ldfld' else field_index
        read = dict(kind='incoming-managed-reference', array=arrays[source_array], index=read_index)
        writes = [dict(array=arrays[target_array], index=target_index, reference=dict(read))]
        if operation == 'Stfld': events.append('read-source-Value1-after-destination-rebase')
        events.extend(['read-selected-managed-reference', 'write-selected-managed-reference'])
        # Descriptor-associated cells follow current Value1. Ldfld's actual
        # field read instead follows fieldIndex; after an exact Value alias
        # those indexes can differ. This does not assert a later consumer.
        _need(source_value1_after >= 0, 'invalid hypothetical current descriptor managed index')
        source_owner = dict(array=arrays[source_array], index=source_value1_after)
        destination_owner = dict(array=arrays[target_array], index=target_index)
    def final_reference(owner: dict | None) -> dict | None:
        if owner is None: return None
        for write in writes:
            if (owner['array'], owner['index']) == (write['array'], write['index']):
                return dict(write['reference'])
        return dict(kind='incoming-managed-reference', **owner)
    field_cell = dict(array=arrays['managedFields'], index=field_index) if managed else None
    return dict(operation=operation, valueSlotRelation=value_relation, managedArrayRelation=managed_array_relation,
                sourceTag=source_tag, sourceValue1Before=source_value1, sourceValue1After=source_value1_after,
                destinationTypeEffect='preserve-source-bits', destinationValue2Effect='preserve-source-bits',
                destinationValue1=destination_value1, managedRead=read, managedWrites=writes,
                sourceOwner=source_owner, destinationOwner=destination_owner,
                sourceOwnerReferenceAfter=final_reference(source_owner),
                destinationOwnerReferenceAfter=final_reference(destination_owner),
                storeyFieldManagedCell=field_cell, storeyFieldManagedReferenceAfter=final_reference(field_cell),
                descriptorOwnerBoundary='symbolic-cell-at-current-Value1;later-consumer-selection-unobserved',
                sharedManagedCellAfter=None if source_owner is None else source_owner == destination_owner,
                managedClears=[], cloneRequest='none-in-selected-storey-body', events=events,
                lowerTagReferenceBoundary='unresolved',
                inputBoundary='caller-supplied-hypothetical-alias-relations-and-relative-positions',
                assumptions=list(_ASSUMPTIONS), evidenceBoundary='conditional', executionBoundary='unobserved')


def project_instance_alias_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach both hypothetical relations to negative operands without choosing one."""
    _declaration(spec); result = []
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name = instruction['name']
            if name not in _CASES: continue
            operand = instruction['operandUnsigned']
            _need(type(operand) is int and 0 <= operand <= 0xffffffff
                  and type(instruction['opcode']) is int and instruction['opcode'] == spec['cases'][name]['opcodeId'],
                  'malformed opcode/UInt32 operand: ' + name)
            signed = operand if operand < 0x80000000 else operand - 0x100000000
            _need('operandSigned' not in instruction or (type(instruction['operandSigned']) is int
                  and instruction['operandSigned'] == signed), 'inconsistent signed operand: ' + name)
            if signed >= 0: continue
            result.append(dict(vmMethodIndex=method['index'], instructionIndex=instruction['index'],
                               offset=instruction['offset'], opcode=name, operandUnsigned=operand, operandSigned=signed,
                               storeyFieldIndex=~signed, instanceAliasRulesRef='audit.instanceAliasRules',
                               equation=spec['cases'][name]['expression'],
                               runtimeValueAliasRelation=None, runtimeManagedArrayAliasRelation=None,
                               wholeValueAlternatives=['same-complete-Value', 'distinct-nonoverlapping-Values'],
                               managedArrayAlternatives=['same-complete-array', 'distinct-nonoverlapping-arrays'],
                               assumptions=list(_ASSUMPTIONS), partialOverlapBoundary='unresolved',
                               scope=spec['scope'], evidenceBoundary='conditional', executionBoundary='unobserved'))
    return result
