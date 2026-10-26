"""Derive whole-slot alias consequences from authenticated IFix copy/store rules.

This is a conditional storage calculation, not a VM interpreter or a runtime
capture. The caller first authenticates slotCopyRules against selected native
inputs. A source and destination either denote the same complete 12-byte Value
or distinct nonoverlapping Values. Pointer differences, array bounds and the
absence of helper-induced mutations are hypotheses, not recovered stack facts.

copy/store snapshot the source's 12 bytes before writing the destination. A
self-copy consequently preserves those bits until a later Value1 rebase. The
FieldReference store path is different from the object path: it rebases
dst.Value1 BEFORE reading src.Value1. For the same Value slot its managed read
therefore uses the destination position, even if incoming Value1 was different.
Object/ValueType selection happens before rebase; ChainFieldReference reads the
source's physical managed position. A copied Object keeps Value1 and therefore
shares its managed index. Rebase creates no object-identity separation: Clone's
return is unobserved, and every other reference assignment forwards the selected
object. Stloc clears the source's physical managed position AFTER store, which
can erase a self-store or a reference shared through that index.

The public calculation uses hypothetical slot positions and symbolic incoming
managed references. It rejects partial/unaligned storage rather than assigning
it a whole-slot result. No recursive dereference, concrete object identity,
successful helper execution or patch invocation follows from these equations.
"""
from __future__ import annotations

from typing import Any


class SlotAliasRuleError(ValueError):
    """An alias declaration exceeds its inherited proof or storage hypotheses."""


_ASSUMPTIONS = [
    'same-complete-Value-or-distinct-nonoverlapping-complete-Values',
    'aligned-12-byte-slot-positions-and-valid-managed-indexes',
    'selected-helper-calls-return-normally-without-mutating-Value-or-managed-storage',
]
_PROOF_REFS = [
    'copy.raw', 'copy.chain', 'copy.boxed', 'copy.rebase',
    'store.raw', 'store.chain', 'store.field', 'store.object', 'store.plain', 'store.rebase',
]
_CLAIMS = {
    'initialSnapshot': 'all-12-source-bytes-read-before-first-destination-write',
    'copyObject': 'preserve-Value1-and-share-incoming-managed-index',
    'copyValueType': 'select-null-or-Clone-return-before-rebase',
    'storeObject': 'select-source-managed-reference-before-rebase',
    'storeField': 'rebase-destination-Value1-before-read-source-Value1',
    'chain': 'read-source-physical-managed-position-and-write-destination-position',
    'stloc': 'clear-source-physical-managed-position-after-store',
    'objectIdentity': 'forwarded-reference-or-unobserved-Clone-return',
}


def _declaration(spec: dict[str, Any]) -> None:
    if (spec.get('schema') != 'endfield.ifix-vm-slot-alias-rules.v1'
            or spec.get('evidenceBoundary') != 'conditional'
            or spec.get('executionBoundary') != 'unobserved'
            or spec.get('sourceRef') != 'slotCopyRules'
            or spec.get('sourceSchema') != 'endfield.ifix-vm-slot-copy-rules.v1'
            or spec.get('proofBlockNames') != _PROOF_REFS
            or spec.get('claims') != _CLAIMS or spec.get('assumptions') != _ASSUMPTIONS
            or spec.get('partialOverlapBoundary') != 'unresolved'
            or spec.get('runtimeAliasSelection') != 'unobserved'):
        raise SlotAliasRuleError('slot-alias: unsupported schema/proof/boundary declaration')


def validate_slot_alias_rules(
    spec: dict[str, Any], source: dict[str, Any], source_audit: dict[str, Any],
) -> dict[str, Any]:
    """Require the earlier selected-native copy/store proof before deriving aliases."""
    _declaration(spec)
    if (source.get('schema') != spec['sourceSchema']
            or source_audit.get('status') != 'validated_conditional_slot_copy_rules'
            or source_audit.get('completeHelperBodies') != ['copy', 'store', 'clone']
            or source_audit.get('evidenceBoundary') != 'conditional'
            or source_audit.get('executionBoundary') != 'unobserved'):
        raise SlotAliasRuleError('slot-alias.source: selected-native copy/store proof required')
    blocks = source.get('blocks', [])
    names = [row.get('name') for row in blocks]
    if len(names) != len(set(names)) or any(name not in names for name in _PROOF_REFS):
        raise SlotAliasRuleError('slot-alias.source: ordered effect block missing/duplicate')
    if (source.get('initialValueCopy') != '12-byte-Type-Value1-Value2-before-tag-branches'
            or source.get('slotBytes') != 12
            or source.get('valueTypeMembers') != {'FieldReference': 6, 'ChainFieldReference': 7, 'Object': 8, 'ValueType': 9}
            or source.get('storeCases', {}).get('FieldReference=6')
                != 'rebase-dst.Value1-before-reading-src.Value1; copy-selected-managed-reference'
            or source.get('tailWindowRefs', {}).get('managedClear') != 'basicOpcodeRules.sharedWindows.managedClear'):
        raise SlotAliasRuleError('slot-alias.source: inherited snapshot/tag/ordering/clear differs')
    return {'status': 'validated_conditional_whole_slot_alias_rules',
            'sourceRef': spec['sourceRef'], 'claims': dict(_CLAIMS),
            'proofBlockNames': list(_PROOF_REFS), 'assumptions': list(_ASSUMPTIONS),
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['runtime-slot-and-managed-index-relations', 'partial-or-unaligned-Value-overlap',
                           'helper-induced-storage-mutation', 'Clone-return-identity', 'recursive-reference-aliases']}


def derive_slot_alias_effect(
    operation: str, *, source_tag: int, source_value1: int,
    source_position: int, destination_position: int,
    storage_relation: str = 'whole-slots',
) -> dict[str, Any]:
    """Calculate a hypothetical ordered effect with symbolic managed references.

    Positions are valid evaluation-base-relative whole-slot indexes supplied by
    the caller, never indexes inferred from patch instructions. Value2 and Type
    are copied unchanged. Clone terms keep the unknown null/clone selection.
    """
    if operation not in ('copy', 'store', 'Stloc'):
        raise SlotAliasRuleError(f'slot-alias.operation: unsupported {operation!r}')
    if storage_relation != 'whole-slots':
        raise SlotAliasRuleError('slot-alias.storage: partial/unaligned overlap unresolved')
    for name, value in (('source_tag', source_tag), ('source_value1', source_value1)):
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise SlotAliasRuleError(f'slot-alias.{name}: expected signed int32')
    for name, value in (('source_position', source_position), ('destination_position', destination_position)):
        if type(value) is not int or not 0 <= value < (1 << 31):
            raise SlotAliasRuleError(f'slot-alias.{name}: expected nonnegative int32 slot position')

    same = source_position == destination_position
    dst_value1 = source_value1
    read_index = None
    clone = False
    if source_tag == 7:
        read_index = source_position
    elif operation == 'copy' and source_tag == 9:
        read_index, clone, dst_value1 = source_value1, True, destination_position
    elif operation != 'copy' and source_tag >= 8:
        read_index, clone, dst_value1 = source_value1, source_tag == 9, destination_position
    elif operation != 'copy' and source_tag == 6:
        dst_value1 = destination_position
        read_index = destination_position if same else source_value1
    if read_index is not None and read_index < 0:
        raise SlotAliasRuleError(f'slot-alias.managed-read: invalid hypothetical index={read_index}')
    reference = (None if read_index is None else
                 {'kind': 'null-or-Clone-return' if clone else 'incoming-managed-reference', 'index': read_index})
    writes = [] if reference is None else [{'index': destination_position, 'reference': reference}]
    clears = [source_position] if operation == 'Stloc' else []
    final_writes = [row for row in writes if row['index'] not in clears]
    src_value1_after = dst_value1 if same else source_value1

    def owner_index(position: int, value1: int) -> int | None:
        return position if source_tag == 7 else value1 if source_tag == 6 or source_tag >= 8 else None

    def final_reference(index: int | None) -> dict[str, Any] | None:
        if index is None:
            return None
        if index in clears:
            return {'kind': 'null'}
        for row in final_writes:
            if row['index'] == index:
                return dict(row['reference'])
        return {'kind': 'incoming-managed-reference', 'index': index}

    src_index = owner_index(source_position, src_value1_after)
    dst_index = owner_index(destination_position, dst_value1)
    if any(index is not None and index < 0 for index in (src_index, dst_index)):
        raise SlotAliasRuleError('slot-alias.managed-owner: invalid hypothetical index')
    return {'operation': operation, 'valueSlotRelation': 'same-slot' if same else 'distinct-nonoverlapping-slots',
            'destinationTypeEffect': 'preserve-source-bits', 'destinationValue2Effect': 'preserve-source-bits',
            'destinationValue1': dst_value1, 'sourceValue1After': src_value1_after,
            'managedReadIndex': read_index, 'managedWritesBeforeClear': writes, 'managedClears': clears,
            'finalManagedWrites': final_writes, 'sourceOwnerReferenceAfter': final_reference(src_index),
            'destinationOwnerReferenceAfter': final_reference(dst_index),
            'sharedManagedIndexAfter': None if src_index is None else src_index == dst_index,
            'inputBoundary': 'caller-supplied-hypothetical-whole-slot-positions',
            'assumptions': list(_ASSUMPTIONS), 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved'}


def project_slot_alias_rules(rows: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach the finite alias alternatives without selecting a live relation."""
    _declaration(spec)
    result = []
    for row in rows:
        if row.get('opcode') not in ('Ldarg', 'Ldloc', 'Stloc', 'Dup'):
            raise SlotAliasRuleError('slot-alias.projection: unsupported inherited opcode')
        result.append({**row, 'wholeSlotAliasRulesRef': 'audit.slotAliasRules',
                       'wholeSlotAliasBoundary': 'same-or-distinct-whole-slots-under-stable-storage-assumptions',
                       'runtimeSlotAliasRelation': None, 'runtimeManagedIndexAliasRelation': None,
                       'partialOverlapBoundary': 'unresolved'})
    return result
