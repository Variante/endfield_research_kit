"""Projection of authored ModelView normal-audio behavior into trigger rows.

``authored_components`` owns the versioned MemoryPack and InteractiveTable
decoders.  This module only projects those decoded rows onto the existing
Event/media shards; it does not decode serialized input or infer an object
owner from an InteractiveTable association.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from . import identifiers, native_evidence


_MEDIA_REF_FIELDS = (
    "id", "mediaId", "src", "rel", "format", "duration",
    "audioDialogPath", "speakerChannel", "audioCategory", "audioScope",
    "sourceLanguage",
)


def _media_ref(media: dict[str, Any]) -> dict[str, Any]:
    return {
        key: media[key]
        for key in _MEDIA_REF_FIELDS
        if media.get(key) not in (None, "", [])
    }


def _event_rows_by_hash(
    event_rows: Iterable[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        try:
            event_hash = int(event.get("hash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        by_hash[event_hash].append(event)
    return by_hash


def _context_event_hash(context_key: Any, row: dict[str, Any]) -> int | None:
    value = row.get("eventHash")
    if isinstance(value, int) and not isinstance(value, bool):
        return value & 0xFFFFFFFF
    text = str(context_key or "")
    if text.startswith("#0x"):
        try:
            return int(text[1:], 16) & 0xFFFFFFFF
        except ValueError:
            return None
    return None


def project_model_view_state_audio_trigger_contexts(
    model_view_semantics: dict[str, Any] | None,
    event_rows: Iterable[dict[str, Any]],
    *,
    native_context: native_evidence.NativeAudioEvidence | None = None,
) -> list[dict[str, Any]]:
    """Project only tag-0x0001 normal Event behaviors.

    The result deliberately carries four independent evidence surfaces:
    ``authoredDefinition`` (serialized request and controller chain),
    ``wwiseMediaCandidates`` (all possible decoded leaves), ``runtimeBranch``
    (selection unresolved), and ``activation`` (behavior execution
    unobserved).  A validated native route is attached only when the selected
    metadata/GameAssembly pair passes the shared gate and the production PE
    body/direct-call audit succeeds.
    """

    if not isinstance(model_view_semantics, dict):
        return []
    by_hash = _event_rows_by_hash(event_rows)
    native_route = None
    native_route_diagnostic: dict[str, Any] | None = None
    if native_context is not None:
        native_route = native_evidence.model_view_state_audio_native_route(native_context)
        if native_route is None:
            # Keep the reason bounded and attached to the authored row.  The
            # route itself remains suppressed, while callers can distinguish
            # a missing input from catalog/body/direct-call drift.
            native_route_diagnostic = native_evidence.audit_model_view_state_audio_native_route(
                native_context
            )
    contexts: list[dict[str, Any]] = []
    seen_trigger_ids: set[str] = set()
    for context_key, authored_rows in (model_view_semantics.get("eventContexts") or {}).items():
        if not isinstance(authored_rows, list):
            continue
        for occurrence_index, authored in enumerate(authored_rows):
            if not isinstance(authored, dict):
                continue
            # The decoder already classifies these rows.  Re-check the union
            # tag here so future/incorrect classifications cannot promote
            # positioned (0x0002) or custom controls into normal Events.
            raw_tag = authored.get("behaviorTag")
            try:
                tag = (
                    int(raw_tag)
                    if not isinstance(raw_tag, bool)
                    else -1
                )
            except (TypeError, ValueError):
                tag = -1
            if (
                tag != 0x0001
                or authored.get("kind") != "modelViewStateAudioEvent"
                or authored.get("isCustom")
            ):
                continue
            event_hash = _context_event_hash(context_key, authored)
            if event_hash is None:
                continue
            matching_events = by_hash.get(event_hash, [])
            # Event rows are normally guaranteed by build_event_rows.  Keep a
            # context only when an exact Event identity is available so an
            # authored row cannot silently become a guessed Wwise identity.
            for event in matching_events:
                event_id = str(event.get("id") or "").strip()
                if not event_id:
                    event_id = identifiers.event_hash_context_key(event_hash)
                media_refs = [
                    _media_ref(media)
                    for media in event.get("media") or []
                    if isinstance(media, dict) and _media_ref(media)
                ]
                controller_id = str(authored.get("controllerId") or authored.get("ownerId") or "")
                source_file = str(authored.get("sourceFile") or "")
                semantic_path = str(authored.get("semanticPath") or "")
                trigger_id = ":".join((
                    "model-view-state-audio",
                    event_id,
                    controller_id or "unknown-controller",
                    source_file or "unknown-file",
                    str(occurrence_index),
                ))
                # A malformed/duplicated Event shard can produce the same
                # event identity for one authored occurrence more than once.
                # Keep the first row in deterministic input order; duplicate
                # trigger IDs would otherwise make media joins over-count.
                if trigger_id in seen_trigger_ids:
                    continue
                seen_trigger_ids.add(trigger_id)
                authored_definition = {
                    "sourceKind": "ModelViewStateControllerData",
                    "behaviorUnionTag": tag,
                    "behaviorUnionTagHex": "0x0001",
                    "behaviorType": authored.get("behaviorType"),
                    "behaviorKind": authored.get("behaviorKind"),
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "normalAudioId": authored.get("normalAudioId"),
                    "audioNodeName": authored.get("audioNodeName"),
                    "eAudioTriggerState": authored.get("eAudioTriggerState"),
                    "isDirectlyPlay": authored.get("isDirectlyPlay"),
                    "stopOnEnd": authored.get("stopOnEnd"),
                    "transitionTime": authored.get("transitionTime"),
                    "behaviorTime": authored.get("behaviorTime"),
                    "modelAnimatorIndex": authored.get("modelAnimatorIndex"),
                    "modelAnimatorName": authored.get("modelAnimatorName"),
                    "layerIndex": authored.get("layerIndex"),
                    "layerFsmIndex": authored.get("layerFsmIndex"),
                    "layerName": authored.get("layerName"),
                    "stateIndex": authored.get("stateIndex"),
                    "stateName": authored.get("stateName"),
                    "stateType": authored.get("stateType"),
                    "behaviorIndex": authored.get("behaviorIndex"),
                    "semanticPath": semantic_path,
                    "controllerId": controller_id,
                    "ownerKind": "modelViewStateController",
                    "interactiveAssociation": {
                        "templateIds": authored.get("interactiveTemplateIds") or [],
                        "templatePaths": authored.get("interactiveTemplatePaths") or [],
                        "consumerIds": authored.get("interactiveConsumerIds") or [],
                        "status": authored.get("templateAssociationStatus")
                        or "unlinked",
                        "ownerPromotion": "notAnOwnerProof",
                    },
                }
                runtime_branch = {
                    "status": "unresolved",
                    "selectionStatus": "wwiseEventBranchSelectionUnobserved",
                    "possibleMediaCount": len(media_refs),
                    "nativeRouteStatus": (
                        "exactCurrentBuildRoute"
                        if native_route is not None
                        else "nativeRouteUnavailable"
                    ),
                }
                activation = {
                    "status": "unobserved",
                    "reason": authored.get("runtimeActivationStatus")
                    or "modelViewStateBehaviorExecutionNotObserved",
                    "behaviorTime": authored.get("behaviorTime"),
                }
                row: dict[str, Any] = {
                    "triggerId": trigger_id,
                    "semanticKind": "modelViewStateAudioEvent",
                    "triggerRole": "authoredModelViewStateNormalEventRequest",
                    "situation": {
                        "eventId": event_id,
                        "eventHash": event_hash,
                        "controllerId": controller_id,
                        "modelAnimatorIndex": authored.get("modelAnimatorIndex"),
                        "modelAnimatorName": authored.get("modelAnimatorName"),
                        "layerIndex": authored.get("layerIndex"),
                        "layerFsmIndex": authored.get("layerFsmIndex"),
                        "layerName": authored.get("layerName"),
                        "stateIndex": authored.get("stateIndex"),
                        "stateName": authored.get("stateName"),
                        "stateType": authored.get("stateType"),
                        "behaviorIndex": authored.get("behaviorIndex"),
                        "behaviorTime": authored.get("behaviorTime"),
                        "semanticPath": semantic_path,
                    },
                    "meaning": {
                        "eventId": event_id,
                        "category": event.get("category"),
                        "foundInWwise": bool(event.get("foundInWwise")),
                        "playbackRole": event.get("playbackRole"),
                        "possibleMediaCount": event.get("possibleMediaCount", len(media_refs)),
                    },
                    "authoredDefinition": authored_definition,
                    "wwiseMediaCandidates": media_refs,
                    "runtimeBranch": runtime_branch,
                    "activation": activation,
                    "action": {
                        "normalAudioId": authored.get("normalAudioId"),
                        "audioNodeName": authored.get("audioNodeName"),
                        "isDirectlyPlay": authored.get("isDirectlyPlay"),
                        "stopOnEnd": authored.get("stopOnEnd"),
                        "transitionTime": authored.get("transitionTime"),
                        "runtimeActivationStatus": activation["reason"],
                    },
                    "owner": {
                        "ownerKind": "modelViewStateController",
                        "controllerId": controller_id,
                        "ownerPromotionStatus": "interactiveTableAssociationNotOwner",
                        "sourceFile": source_file,
                        "sourcePaths": authored.get("sourcePaths") or [],
                        "sourceRoots": authored.get("sourceRoots") or [],
                        "sourceFingerprints": authored.get("sourceFingerprints") or [],
                        "schemaMappingId": authored.get("schemaMappingId"),
                        "runtimeMappingId": authored.get("runtimeMappingId"),
                        "schemaStatus": authored.get("schemaStatus"),
                    },
                    "selection": {
                        "triggerBindingStatus": "exactModelViewStateNormalEventBehavior",
                        "mediaSelectionStatus": (
                            "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                        ),
                        "runtimeSelectionStatus": runtime_branch["selectionStatus"],
                    },
                    "mediaRefs": media_refs,
                    "evidence": {
                        "definition": "exactDecodedModelViewStateAudioBehavior",
                        "owner": "exactModelLayerStateBehaviorOwnerChain",
                        "media": "wwiseEventMediaCandidates",
                        "runtimeBranch": "wwiseBranchSelectionUnobserved",
                        "activation": activation["reason"],
                        "requestEvidence": authored.get("triggerRequestEvidence") or [],
                    },
                    "runtimeActivationStatus": activation["reason"],
                    "sourceRefs": [
                        value for value in (
                            source_file, semantic_path, *(
                                authored.get("sourcePaths") or []
                            ),
                        ) if isinstance(value, str) and value
                    ],
                }
                if native_route is not None:
                    row["nativeRoute"] = native_route
                elif native_route_diagnostic is not None:
                    row["nativeRouteDiagnostic"] = {
                        "status": native_route_diagnostic.get("status"),
                        "reason": str(native_route_diagnostic.get("reason") or "")[:1000],
                    }
                contexts.append(row)
    contexts.sort(key=lambda row: str(row.get("triggerId") or ""))
    return contexts


__all__ = ["project_model_view_state_audio_trigger_contexts"]
