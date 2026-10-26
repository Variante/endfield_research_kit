"""Conditional byte-overlap equations for negative storey field callees.

An authenticated instanceFieldRules audit supplies the complete native Ldfld
and Stfld programs. Both snapshot 12 source bytes, copy them to the destination,
then read the source tag again. Partial overlap can change that tag. The
managed branch rebases destination.Value1; Stfld then reads source.Value1 anew.
There is no Clone predicate or second tag read after rebasing in either callee.

This pure calculation uses hypothetical bytes and a signed destination-minus-
source displacement. It never reads process storage or selects actual aliases.
Normal helper returns, stable selected addresses, readable/writable storage and
separation from object headers, native frame and managed storage are hypotheses.
Managed array reads/stores are conditional symbolic requests: identity, bounds,
assignment, GC effects, helper mutation and concrete references remain open.
"""
from __future__ import annotations

from typing import Any


class InstanceByteAliasRuleError(ValueError):
    """A byte equation lacks its native prerequisite or bounded hypotheses."""


_METHOD_TYPES = ['int', 'IFix.Core.Value*', 'IFix.Core.Value*', 'object[]']
_RULES = {
    'snapshot': 'read-source-qword-at0-and-dword-at8-before-first-destination-Value-store',
    'copy': 'write-snapshotted-qword-at-destination0-then-snapshotted-dword-at-destination8',
    'tagPredicate': 'reread-source-dword-at0-after-copy;interpret-signed-Int32;managed-branch-iff-tag>=Object8',
    'rebase': 'only-on-managed-branch;write-destination-dword-at4;Stfld=fieldIndex;Ldfld=evaluation-position-low32',
    'Stfld': 'reread-source-dword-at4-after-rebase;signextend-for-address;unsigned-low32-array-bounds-guard;capture-managedStack-reference-before-assignmentCheck-and-managedStore-request-to-managedFields[fieldIndex]',
    'Ldfld': 'select-managedFields[fieldIndex]-independent-of-current-source.Value1;unsigned-low32-array-bounds-guard;capture-reference-before-assignmentCheck-and-managedStore-request-to-managedStack[evaluationPosition]',
    'tagAfterRebase': 'expose-current-source-tag-bytes;no-second-source-tag-read-or-branch-reselection-in-complete-callees',
    'clone': 'no-Clone-request-or-predicate-in-complete-Ldfld-Stfld-callees',
    'clear': 'no-explicit-managed-reference-clear-in-complete-Ldfld-Stfld-callees',
}
_ASSUMPTIONS = [
    'valid-selected-AnonymousStorey-receiver-and-two-readable-writable-12-byte-Value-descriptors',
    'signed-destination-minus-source-byte-displacement-within-minus11-through-plus11-without-address-wrap',
    'reloaded-unmanagedFields-array-and-selected-field-address-unchanged-across-copy-and-rebase',
    'Value-writes-disjoint-from-receiver-array-headers-native-frame-and-managed-array-storage',
    'stable-storage-no-concurrent-mutation-and-normal-nonmutating-helper-returns-are-conditional-hypotheses',
    'nonnegative-Int32-evaluation-position-and-field-index-are-caller-supplied-hypotheses-without-array-capacity-proof',
]
_CLAIMS = {
    'schema': 'endfield.ifix-vm-instance-byte-alias-rules.v1',
    'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'sourceRef': 'instanceFieldRules', 'sourceSchema': 'endfield.ifix-vm-instance-field-rules.v1',
    'methodRefs': {'Ldfld': 'instanceFieldRules.methods.Ldfld', 'Stfld': 'instanceFieldRules.methods.Stfld'},
    'slotBytes': 12, 'displacementMin': -11, 'displacementMax': 11,
    'rules': _RULES, 'assumptions': _ASSUMPTIONS,
    'scope': 'complete-AnonymousStorey-Ldfld-Stfld-callees-after-valid-negative-Execute-receiver-selection',
    'runtimeAliasSelection': 'unobserved',
    'managedArrayBoundary': 'identity-overlap-storage-bounds-and-helper-outcomes-unobserved;roles-kept-distinct',
    'fileTableJoinBoundary': 'not-asserted',
}
_CASES = {
    'Ldfld': 'post-copy-source-tag-controls-rebase-and-managedFields[fieldIndex]-request',
    'Stfld': 'post-copy-source-tag-controls-rebase;post-rebase-source.Value1-selects-managedStack-request',
}


def _need(ok: bool, detail: str) -> None:
    if not ok:
        raise InstanceByteAliasRuleError('instance-byte-alias.' + detail)


def _declaration(spec: dict[str, Any]) -> None:
    _need(type(spec) is dict and all(type(spec.get(k)) is type(v) and spec.get(k) == v
                                  for k, v in _CLAIMS.items()), 'unsupported schema/proof/boundary')
    cases = spec.get('cases')
    _need(type(cases) is dict and set(cases) == set(_CASES), 'case catalog differs')
    for name, expression in _CASES.items():
        case = cases[name]
        _need(type(case) is dict and set(case) == {'opcodeId', 'expression'}
              and type(case.get('opcodeId')) is int and 0 <= case['opcodeId'] <= 0x7fffffff
              and case.get('expression') == expression, 'case declaration differs: ' + name)


def validate_instance_byte_alias_rules(spec: dict[str, Any], source: dict[str, Any],
                                      source_audit: dict[str, Any]) -> dict[str, Any]:
    """Require the caller's same-image complete native instance-field proof.

    The parent owns native gating and the finite method grammars. This derived
    group neither reopens those inputs nor substitutes a hash-only audit for
    the selected proof. The source audit is supplied by that authenticated
    validator, never obtained from hypothetical byte inputs.
    """
    _declaration(spec)
    _need(type(source) is dict and type(source_audit) is dict, 'selected complete native source proof required')
    _need(source.get('schema') == spec['sourceSchema'] and source.get('scope') == 'negative-instance-fields-only'
          and source.get('evidenceBoundary') == 'conditional' and source.get('executionBoundary') == 'unobserved'
          and source_audit.get('status') == 'validated_conditional_instance_field_rules'
          and source_audit.get('storeyMethods') == ['Ldfld', 'Stfld', 'Get', 'Set']
          and type(source_audit.get('managedTagThreshold')) is int and source_audit['managedTagThreshold'] == 8
          and source_audit.get('evidenceBoundary') == 'conditional'
          and source_audit.get('executionBoundary') == 'unobserved', 'selected complete native source proof required')
    _need(type(source.get('slotBytes')) is int and source['slotBytes'] == 12
          and source.get('fileTableJoinBoundary') == source_audit.get('fileTableJoinBoundary') == 'not-asserted'
          and source.get('consumedManagedClear') == source_audit.get('consumedManagedClear')
          == 'none-explicit-in-selected-negative-route', 'source slot/clear/file boundary differs')
    fields = source.get('fieldLayout', {})
    _need(fields.get('type') == 'IFix.Core.AnonymousStorey'
          and fields.get('fields') == {'unmanagedFields': {'offset': 16, 'type': 'IFix.Core.Value[]'},
                                      'managedFields': {'offset': 24, 'type': 'object[]'}}, 'source storage layout differs')
    rows = source.get('rules', []); audits = source_audit.get('entries', [])
    _need(len(rows) == len(audits) == 2
          and {r.get('opcode') for r in rows} == {r.get('opcode') for r in audits} == set(_CASES),
          'source negative route proof missing/duplicate')
    for name in _CASES:
        row = next(r for r in rows if r['opcode'] == name); audit = next(r for r in audits if r['opcode'] == name)
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
              and method.get('parameterTypes') == _METHOD_TYPES and method.get('returnTypeName') == 'void'
              and type(method.get('bodyBytes')) is int and method['bodyBytes'] > 0,
              'source complete storey method differs: ' + name)
        for key in ('static', 'generic'):
            _need(key not in method or (type(method[key]) is bool and method[key] is False),
                  'source method kind differs: ' + name + '.' + key)
    return dict(status='validated_conditional_instance_byte_alias_rules', sourceRef=spec['sourceRef'],
                methodRefs=dict(spec['methodRefs']), rules=dict(_RULES), assumptions=list(_ASSUMPTIONS),
                displacementRange=[-11, 11], displacementCaseCount=23, descriptorBytes=12,
                runtimeAliasSelection='unobserved', managedArrayBoundary=spec['managedArrayBoundary'],
                evidenceBoundary='conditional', executionBoundary='unobserved',
                unresolved=['actual-Value-address-displacement-and-bytes', 'stable-selected-storage-premises',
                            'managed-array-identity-overlap-bounds-and-reference-values', 'helper-mutation-and-outcomes',
                            'outer-receiver-conversion-Clone-and-later-cleanup', 'actual-execution'])


def _word(raw: bytes) -> int:
    return int.from_bytes(raw, 'little', signed=True)


def derive_instance_byte_alias_effect(operation: str, *, source_bytes: bytes | bytearray,
                                      displacement: int, rebase_index: int, field_index: int) -> dict[str, Any]:
    """Compute a hypothetical overlapping descriptor effect, never a live alias.

    displacement equals destinationAddress-sourceAddress. The signed tag read
    occurs after both copy stores. On the managed branch the destination dword
    at4 is rebased before Stfld's fresh source dword read. Ldfld does not read
    source.Value1 for managed selection. Index bits and signed address indexes
    are retained without declaring a successful runtime bounds check.
    """
    _need(operation in _CASES, 'unsupported operation')
    _need(type(source_bytes) in (bytes, bytearray) and len(source_bytes) == 12, 'expected exactly12 hypothetical source bytes')
    _need(type(displacement) is int and -11 <= displacement <= 11, 'expected overlapping byte displacement minus11 through plus11')
    for role, value in [('field_index', field_index), ('rebase_index', rebase_index)]:
        _need(type(value) is int and 0 <= value < (1 << 31), 'expected nonnegative Int32 hypothetical index: ' + role)
    _need(operation != 'Stfld' or rebase_index == field_index, 'Stfld rebase index must equal field index')
    snapshot = bytes(source_bytes)
    # A finite hypothetical byte map represents the union of the two Value
    # ranges. Only the source is read initially; all destination bytes are
    # overwritten from the pre-write snapshot, never from mutated source bytes.
    memory = dict(enumerate(snapshot)); origins = {i: ('source', i) for i in range(12)}
    events = ['snapshot-source-qword-at0', 'snapshot-source-dword-at8',
              'write-destination-qword-at0', 'write-destination-dword-at8']
    for start, end in ((0, 8), (8, 12)):
        for i in range(start, end):
            memory[displacement+i] = snapshot[i]; origins[displacement+i] = ('source', i)
    copied_source = bytes(memory[i] for i in range(12))
    copied_origins = [dict(origin=origins[i][0], byte=origins[i][1]) for i in range(12)]
    guard_tag = _word(copied_source[:4]); managed = guard_tag >= 8
    events.append('reread-source-tag-after-copy-signed32')
    read = None; store = None; selected_index = None
    if managed:
        events.append('write-destination-Value1-rebase')
        replacement = rebase_index.to_bytes(4, 'little')
        for i in range(4):
            memory[displacement+4+i] = replacement[i]; origins[displacement+4+i] = ('rebase', i)
        source_after_rebase = bytes(memory[i] for i in range(12))
        if operation == 'Stfld':
            events.append('reread-source-Value1-after-rebase-signed32')
            selected_index = _word(source_after_rebase[4:8]); source_role = 'managedStack'; target_role = 'managedFields'; target_index = field_index
        else:
            selected_index = field_index; source_role = 'managedFields'; target_role = 'managedStack'; target_index = rebase_index
        events.extend(['selected-array-bounds-guard-unsigned-low32',
                       'capture-selected-managed-reference-on-normal-bounds-path',
                       'request-assignmentCheck', 'request-managedStore'])
        read = dict(arrayRole=source_role, indexSigned=selected_index, boundsIndexUnsigned=selected_index & 0xffffffff,
                    referenceTerm='incoming-' + source_role + '[' + str(selected_index) + ']',
                    boundary='conditional-valid-readable-storage-and-normal-unsigned-bounds-path')
        store = dict(arrayRole=target_role, indexSigned=target_index, referenceTerm=read['referenceTerm'],
                     boundary='ordered-request-only;assignment-and-helper-outcome-unobserved')
    final_source = bytes(memory[i] for i in range(12))
    final_destination = bytes(memory[displacement+i] for i in range(12))
    return dict(operation=operation, displacement=displacement, sourceSnapshotHex=snapshot.hex().upper(),
                sourceAfterCopyHex=copied_source.hex().upper(), sourceAfterCopyOrigins=copied_origins,
                sourceAfterRebaseHex=final_source.hex().upper(),
                sourceAfterRebaseOrigins=[dict(origin=origins[i][0], byte=origins[i][1]) for i in range(12)],
                destinationAfterHex=final_destination.hex().upper(), sourceTagBefore=_word(snapshot[:4]),
                sourceTagAtManagedPredicate=guard_tag, sourceTagAfterRebase=_word(final_source[:4]),
                sourceValue1Before=_word(snapshot[4:8]), sourceValue1AfterCopy=_word(copied_source[4:8]),
                sourceValue1AfterRebase=_word(final_source[4:8]), managedBranch=managed,
                branchSelectionBoundary='one-post-copy-signed-tag-read;no-reselection-after-rebase',
                destinationValue1=_word(final_destination[4:8]),
                selectedManagedReadIndex=selected_index, managedRead=read, managedStoreRequest=store,
                managedArrayIdentity=None, managedArrayOverlap=None, observedManagedWrites=[],
                cloneRequest='none-in-complete-selected-storey-callee', clonePredicateRead='absent',
                explicitManagedClears=[], events=events, assumptions=list(_ASSUMPTIONS),
                inputBoundary='caller-supplied-hypothetical-byte-vector-displacement-and-indexes',
                evidenceBoundary='conditional', executionBoundary='unobserved')
