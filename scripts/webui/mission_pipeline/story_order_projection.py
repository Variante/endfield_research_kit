"""Compact source Story-order evidence for Mission Pipeline payloads."""
from __future__ import annotations

from typing import Any


def update_story_order_summary(
    summary: dict[str, Any],
    order_row: dict[str, Any],
) -> None:
    order_summary = order_row.get("summary") or {}
    mappings = {
        "storyOrderSceneCount": "sceneCount",
        "storyOrderStrongEdgeCount": "strongEdgeCount",
        "storyOrderCycleCount": "cycleCount",
        "storyOrderNativeBranchCount": "nativeControlBranchCount",
        "storyOrderNativeMergeCount": "nativeControlMergeCount",
        "storyOrderNativeTransitionCount": "nativeControlPathTransitionEdgeCount",
        "storyOrderQuestSucceedLifecycleCount": "questSucceedLifecycleEdgeCount",
        "storyOrderNativeTransitionStepCount": "nativeControlPathTransitionStepCount",
        "storyOrderNativeNamedActionEndpointCount": "nativeControlPathNamedActionEndpointCount",
        "storyOrderNativeUnresolvedActionEndpointCount": "nativeControlPathUnresolvedActionEndpointCount",
        "storyOrderNativeBranchingTransitionCount": "nativeControlPathBranchingTransitionEdgeCount",
        "storyOrderNativeOrderedSequenceCount": "nativeOrderedSequenceCount",
        "storyOrderNativeOrderedSequenceContextCount": "nativeOrderedSequenceContextCount",
        "storyOrderNativeRelatedActionTopologyCount": "nativeRelatedActionTopologyCount",
        "storyOrderNativeSerializedBranchGroupCount": "nativeSerializedBranchGroupCount",
        "storyOrderNativeSerializedBranchArmCount": "nativeSerializedBranchArmCount",
        "storyOrderNativeSerializedPlaybackArmCount": "nativeSerializedPlaybackArmCount",
        "storyOrderNativeSerializedMultiPlaybackBranchCount": "nativeSerializedMultiPlaybackBranchCount",
        "storyOrderNativeSerializedBranchContextCount": "nativeSerializedBranchContextCount",
        "storyOrderNativeSerializedBranchContextStoryCount": "nativeSerializedBranchContextStoryCount",
        "storyOrderNativeSerializedBranchContextMultiPlaybackCount": "nativeSerializedBranchContextMultiPlaybackCount",
        "storyOrderNativeSerializedBranchContextRelatedFileCount": "nativeSerializedBranchContextRelatedFileCount",
        "storyOrderNativeSerializedNestedControlCount": "nativeSerializedNestedControlCount",
        "storyOrderNativeSerializedNestedControlFamilyCounts": "nativeSerializedNestedControlFamilyCounts",
        "storyOrderNativeSerializedNestedControlArmSchemaUnavailableCount": "nativeSerializedNestedControlArmSchemaUnavailableCount",
        "storyOrderNativeSerializedNestedPlaybackArmCount": "nativeSerializedNestedPlaybackArmCount",
        "storyOrderNativeSerializedNestedMultiPlaybackControlCount": "nativeSerializedNestedMultiPlaybackControlCount",
        "storyOrderNativeSerializedNestedPlaybackControlCount": "nativeSerializedNestedPlaybackControlCount",
        "storyOrderNativeSerializedNestedPlaybackPredicateGapCount": "nativeSerializedNestedPlaybackPredicateGapCount",
        "storyOrderNativeSerializedNestedControlReferenceCount": "nativeSerializedNestedControlReferenceCount",
        "storyOrderNativeSerializedNestedArmCount": "nativeSerializedNestedArmCount",
        "storyOrderNativeSerializedNestedExactActiveArmCount": "nativeSerializedNestedExactActiveArmCount",
        "storyOrderNativeSerializedNestedInactiveArmCount": "nativeSerializedNestedInactiveArmCount",
        "storyOrderNativeSerializedNestedRuntimeTerminalArmCount": "nativeSerializedNestedRuntimeTerminalArmCount",
        "storyOrderNativeSerializedNestedUnavailableArmCount": "nativeSerializedNestedUnavailableArmCount",
        "storyOrderNativeSerializedBranchPredicateConflictCount": "nativeSerializedBranchPredicateConflictCount",
        "storyOrderNativeNamedPredicateCount": "nativeNamedPredicateCount",
        "storyOrderNativeInlinePredicateCount": "nativeInlinePredicateCount",
        "storyOrderNativeSemanticPredicateCount": "nativeSemanticPredicateCount",
        "storyOrderNativeClassOnlyPredicateCount": "nativeClassOnlyPredicateCount",
        "storyOrderNativeUnresolvedPredicateCount": "nativeUnresolvedPredicateCount",
        "storyOrderQuestForkCount": "questForkCount",
        "storyOrderQuestMergeCount": "questMergeCount",
        "storyOrderDialogConditionalBranchCount": "dialogConditionalBranchCount",
        "storyOrderDialogConditionalBranchArmCount": "dialogConditionalBranchArmCount",
        "storyOrderDialogConditionalBranchValidationFailureCount": "dialogConditionalBranchValidationFailureCount",
        "storyOrderDialogTreeBranchNodeCount": "dialogTreeBranchNodeCount",
        "storyOrderDialogTreeBranchNodeArmCount": "dialogTreeBranchNodeArmCount",
        "storyOrderDialogTreeBranchNodeValidationFailureCount": "dialogTreeBranchNodeValidationFailureCount",
        "storyOrderDialogTreeIfNodeCount": "dialogTreeIfNodeCount",
        "storyOrderDialogTreeIfNodeArmCount": "dialogTreeIfNodeArmCount",
        "storyOrderDialogTreeIfNodeValidationFailureCount": "dialogTreeIfNodeValidationFailureCount",
        "storyOrderDialogLineOptionBinaryValidatedGroupCount": "dialogLineOptionBinaryValidatedGroupCount",
        "storyOrderDialogLineOptionBinaryValidationFailureCount": "dialogLineOptionBinaryValidationFailureCount",
        "storyOrderDialogLineOptionRelatedFileCount": "dialogLineOptionRelatedFileCount",
    }
    for target, source in mappings.items():
        summary[target] = int(order_summary.get(source) or 0)
    cross_reference = order_row.get("crossReference") or {}
    if isinstance(cross_reference, dict):
        summary["storyOrderCrossReferenceStrictEdgeCount"] = int(
            cross_reference.get("strictEdgeCount") or 0
        )
        summary["storyOrderCrossReferenceOverrideDisagreeCount"] = int(
            (cross_reference.get("override") or {}).get("disagrees") or 0
        )
        summary["storyOrderCrossReferenceOcrDisagreeCount"] = int(
            (cross_reference.get("ocr") or {}).get("disagrees") or 0
        )
        summary["storyOrderCrossReferenceConflictCount"] = int(
            cross_reference.get("conflictCount") or 0
        )


def _cross_reference_status_counts(
    counts: dict[str, Any] | None,
    reference: str,
) -> dict[str, int]:
    counts = counts or {}
    return {
        status: int(counts.get(f"{reference}_{status}") or 0)
        for status in ("agrees", "disagrees", "uncovered")
    }


def compact_story_order_cross_reference(
    mission_row: dict[str, Any],
    cross_reference: dict[str, Any],
) -> dict[str, Any]:
    """Attach diagnostic override/OCR comparison without changing evidence."""
    counts = mission_row.get("counts") or {}
    disagreement_edges: list[dict[str, Any]] = []
    for edge in mission_row.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        override = edge.get("override") or {}
        ocr = edge.get("ocr") or {}
        if (
            override.get("status") != "disagrees"
            and ocr.get("status") != "disagrees"
            and not edge.get("crossReferenceConflict")
        ):
            continue
        disagreement_edges.append({
            "from": str(edge.get("from") or ""),
            "to": str(edge.get("to") or ""),
            "kind": str(edge.get("kind") or "sourceEdge"),
            "override": {
                "status": str(override.get("status") or "uncovered"),
                "fromIndex": override.get("fromIndex"),
                "toIndex": override.get("toIndex"),
                "missing": [
                    str(value)
                    for value in override.get("missing") or []
                    if value
                ],
            },
            "ocr": {
                "status": str(ocr.get("status") or "uncovered"),
                "fromIndex": ocr.get("fromIndex"),
                "toIndex": ocr.get("toIndex"),
                "missing": [
                    str(value)
                    for value in ocr.get("missing") or []
                    if value
                ],
            },
            "crossReferenceConflict": bool(edge.get("crossReferenceConflict")),
            "orderEvidence": False,
        })
    disagreement_edges.sort(
        key=lambda edge: (
            str(edge.get("from") or ""),
            str(edge.get("to") or ""),
            str(edge.get("kind") or ""),
        )
    )
    return {
        "schema": str(cross_reference.get("_schema") or ""),
        "status": "cross_reference_only",
        "strictEdgeCount": int(mission_row.get("strictEdgeCount") or 0),
        "override": _cross_reference_status_counts(counts, "override"),
        "ocr": _cross_reference_status_counts(counts, "ocr"),
        "conflictCount": sum(
            bool(edge.get("crossReferenceConflict"))
            for edge in mission_row.get("edges") or []
            if isinstance(edge, dict)
        ),
        "disagreementEdges": disagreement_edges,
        "policy": (
            "Only strict source partial-order edges are evidence. Manual "
            "override and OCR lists are diagnostic cross-references; they "
            "never create, strengthen, weaken, or remove an edge."
        ),
        "reportJson": str(cross_reference.get("reportJson") or ""),
        "reportMarkdown": str(cross_reference.get("reportMarkdown") or ""),
        "orderEvidence": False,
    }


def compact_story_order_cross_reference_index(
    cross_reference: dict[str, Any],
) -> dict[str, Any]:
    """Keep the global index compact while retaining the full report on disk."""
    return {
        "schema": str(cross_reference.get("_schema") or ""),
        "status": "cross_reference_only",
        "policy": cross_reference.get("policy") or {},
        "inputs": cross_reference.get("inputs") or {},
        "summary": cross_reference.get("summary") or {},
        "reportJson": str(cross_reference.get("reportJson") or ""),
        "reportMarkdown": str(cross_reference.get("reportMarkdown") or ""),
        "orderEvidence": False,
    }
