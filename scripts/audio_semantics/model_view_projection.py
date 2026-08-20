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
    """Project normal and positioned ModelView trigger/control evidence.

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
    normal_route = None
    positioned_route = None
    diagnostics: dict[str, dict[str, Any]] = {}
    if native_context is not None:
        normal_route = native_evidence.model_view_state_audio_native_route(native_context)
        positioned_route = native_evidence.model_view_positioned_audio_native_route(native_context)
        if normal_route is None:
            diagnostics["normal"] = native_evidence.audit_model_view_state_audio_native_route(native_context)
        if positioned_route is None:
            diagnostics["positioned"] = native_evidence.audit_model_view_positioned_audio_native_route(native_context)

    contexts: list[dict[str, Any]] = []
    seen_trigger_ids: set[str] = set()

    def common_definition(authored: dict[str, Any], tag: int, *, event_hash: int | None = None) -> dict[str, Any]:
        controller_id = str(authored.get("controllerId") or authored.get("ownerId") or "")
        definition: dict[str, Any] = {
            "sourceKind": "ModelViewStateControllerData",
            "behaviorUnionTag": tag,
            "behaviorUnionTagHex": f"0x{tag:04x}",
            "behaviorType": authored.get("behaviorType"),
            "behaviorKind": authored.get("behaviorKind"),
            "normalAudioId": authored.get("normalAudioId"),
            "audioNodeName": authored.get("audioNodeName"),
            "customAudioId": authored.get("customAudioId"),
            "eAudioTriggerState": authored.get("eAudioTriggerState"),
            "isCustom": authored.get("isCustom"),
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
            "semanticPath": str(authored.get("semanticPath") or ""),
            "controllerId": controller_id,
            "ownerKind": "modelViewStateController",
            "interactiveAssociation": {
                "templateIds": authored.get("interactiveTemplateIds") or [],
                "templatePaths": authored.get("interactiveTemplatePaths") or [],
                "consumerIds": authored.get("interactiveConsumerIds") or [],
                "status": authored.get("templateAssociationStatus") or "unlinked",
                "ownerPromotion": "notAnOwnerProof",
            },
        }
        if event_hash is not None:
            definition["eventHash"] = event_hash
            definition["eventHex"] = f"0x{event_hash:08x}"
        return definition

    def owner(authored: dict[str, Any]) -> dict[str, Any]:
        return {
            "ownerKind": "modelViewStateController",
            "controllerId": str(authored.get("controllerId") or authored.get("ownerId") or ""),
            "ownerPromotionStatus": "interactiveTableAssociationNotOwner",
            "sourceFile": authored.get("sourceFile") or "",
            "sourcePaths": authored.get("sourcePaths") or [],
            "sourceRoots": authored.get("sourceRoots") or [],
            "sourceFingerprints": authored.get("sourceFingerprints") or [],
            "schemaMappingId": authored.get("schemaMappingId"),
            "runtimeMappingId": authored.get("runtimeMappingId"),
            "schemaStatus": authored.get("schemaStatus"),
        }

    # Event contexts contain tag-0x0001 normal events and only the direct
    # tag-0x0002 branch.  The collector deliberately keeps positioned
    # controls in a separate list, so a future malformed input cannot promote
    # them merely by carrying a nonzero normalAudioId.
    for context_key, authored_rows in (model_view_semantics.get("eventContexts") or {}).items():
        if not isinstance(authored_rows, list):
            continue
        for occurrence_index, authored in enumerate(authored_rows):
            if not isinstance(authored, dict):
                continue
            try:
                tag = int(authored.get("behaviorTag")) if not isinstance(authored.get("behaviorTag"), bool) else -1
            except (TypeError, ValueError):
                tag = -1
            is_position = tag == 0x0002
            if tag == 0x0001:
                if authored.get("kind") != "modelViewStateAudioEvent" or authored.get("isCustom"):
                    continue
            elif is_position:
                # A positioned Event is promoted only from the exact current
                # collector shape.  Old caches sometimes carried a tag-2 row
                # under the normal kind or used the context key as its only
                # hash; those rows fail closed instead of gaining media.
                normal_audio_id = authored.get("normalAudioId")
                if (
                    authored.get("kind") != "modelViewStatePositionAudioEvent"
                    or authored.get("isCustom") is not False
                    or authored.get("isDirectlyPlay") is not True
                    or not isinstance(normal_audio_id, int)
                    or isinstance(normal_audio_id, bool)
                    or normal_audio_id == 0
                ):
                    continue
            else:
                continue
            event_hash = (
                int(authored["normalAudioId"]) & 0xFFFFFFFF
                if is_position
                else _context_event_hash(context_key, authored)
            )
            if event_hash is None:
                continue
            for event in by_hash.get(event_hash, []):
                event_id = str(event.get("id") or "").strip() or identifiers.event_hash_context_key(event_hash)
                media_refs = [
                    _media_ref(media) for media in event.get("media") or []
                    if isinstance(media, dict) and _media_ref(media)
                ]
                controller_id = str(authored.get("controllerId") or authored.get("ownerId") or "")
                source_file = str(authored.get("sourceFile") or "")
                semantic_path = str(authored.get("semanticPath") or "")
                trigger_id = ":".join((
                    "model-view-positioned-audio" if is_position else "model-view-state-audio",
                    event_id, controller_id or "unknown-controller",
                    source_file or "unknown-file", str(occurrence_index),
                ))
                if trigger_id in seen_trigger_ids:
                    continue
                seen_trigger_ids.add(trigger_id)
                activation_reason = authored.get("runtimeActivationStatus") or "modelViewStateBehaviorExecutionNotObserved"
                selection_status = (
                    "directPositionEventWwiseSelectionUnobserved"
                    if is_position else "wwiseEventBranchSelectionUnobserved"
                )
                row: dict[str, Any] = {
                    "triggerId": trigger_id,
                    "semanticKind": "modelViewStatePositionAudioEvent" if is_position else "modelViewStateAudioEvent",
                    "triggerRole": "authoredModelViewStateDirectPositionEventRequest" if is_position else "authoredModelViewStateNormalEventRequest",
                    "situation": {
                        "eventId": event_id, "eventHash": event_hash, "controllerId": controller_id,
                        "modelAnimatorIndex": authored.get("modelAnimatorIndex"),
                        "modelAnimatorName": authored.get("modelAnimatorName"),
                        "layerIndex": authored.get("layerIndex"), "layerFsmIndex": authored.get("layerFsmIndex"),
                        "layerName": authored.get("layerName"), "stateIndex": authored.get("stateIndex"),
                        "stateName": authored.get("stateName"), "stateType": authored.get("stateType"),
                        "behaviorIndex": authored.get("behaviorIndex"), "behaviorTime": authored.get("behaviorTime"),
                        "semanticPath": semantic_path,
                    },
                    "meaning": {
                        "eventId": event_id, "category": event.get("category"),
                        "foundInWwise": bool(event.get("foundInWwise")),
                        "playbackRole": event.get("playbackRole"),
                        "possibleMediaCount": event.get("possibleMediaCount", len(media_refs)),
                    },
                    "authoredDefinition": common_definition(authored, tag, event_hash=event_hash),
                    "wwiseMediaCandidates": media_refs,
                    "runtimeBranch": {
                        "status": "unresolved", "selectionStatus": selection_status,
                        "possibleMediaCount": len(media_refs),
                        "downstreamStatus": "individuallyAuditedEndpointsConnectionUnresolved" if is_position else "WwiseSelectionUnobserved",
                        "nativeRouteStatus": "exactCurrentBuildPositionedRoute" if is_position and positioned_route is not None else (
                            "exactCurrentBuildRoute" if not is_position and normal_route is not None else "nativeRouteUnavailable"
                        ),
                    },
                    "activation": {"status": "unobserved", "reason": activation_reason, "behaviorTime": authored.get("behaviorTime")},
                    "action": {
                        "normalAudioId": authored.get("normalAudioId"), "audioNodeName": authored.get("audioNodeName"),
                        "isDirectlyPlay": authored.get("isDirectlyPlay"), "stopOnEnd": authored.get("stopOnEnd"),
                        "transitionTime": authored.get("transitionTime"),
                        "playbackSink": "AudioManager.PlaySoundAtPosition" if is_position else None,
                        "playbackSinkStatus": "nativeTargetAndBodyVerified" if is_position else None,
                        "audioHandleField": "self+0x28 m_audioHandle" if is_position else None,
                        "audioHandleWriteStatus": (
                            positioned_route.get("fieldContract", {}).get("audioHandleWrite", {}).get("status")
                            if is_position and positioned_route is not None
                            else "unavailable" if is_position else None
                        ),
                        "runtimeActivationStatus": activation_reason,
                    },
                    "owner": owner(authored),
                    "selection": {
                        "triggerBindingStatus": "exactModelViewStatePositionedDirectEventBehavior" if is_position else "exactModelViewStateNormalEventBehavior",
                        "mediaSelectionStatus": "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate",
                        "runtimeSelectionStatus": selection_status,
                    },
                    "mediaRefs": media_refs,
                    "evidence": {
                        "definition": "exactDecodedModelViewStatePositionedDirectBranch" if is_position else "exactDecodedModelViewStateAudioBehavior",
                        "owner": "exactModelLayerStateBehaviorOwnerChain",
                        "media": "wwiseEventMediaCandidates",
                        "runtimeBranch": selection_status,
                        "activation": activation_reason,
                        "requestEvidence": authored.get("triggerRequestEvidence") or [],
                    },
                    "runtimeActivationStatus": activation_reason,
                    "sourceRefs": [
                        value for value in (source_file, semantic_path, *(authored.get("sourcePaths") or []))
                        if isinstance(value, str) and value
                    ],
                }
                route = positioned_route if is_position else normal_route
                diagnostic = diagnostics.get("positioned" if is_position else "normal")
                if route is not None:
                    row["nativeRoute"] = route
                elif diagnostic is not None:
                    row["nativeRouteDiagnostic"] = {
                        "status": diagnostic.get("status"),
                        "reason": str(diagnostic.get("reason") or "")[:1000],
                    }
                contexts.append(row)

    # Controls are useful trigger context, but are never joined to Event rows
    # and never expose media candidates or event ownership.
    control_rows = list(model_view_semantics.get("positionedControls") or [])
    for occurrence_index, authored in enumerate(control_rows):
        if not isinstance(authored, dict):
            continue
        branch = str(authored.get("controlBranch") or "")
        if branch not in {"customStateSwitch", "entityStateSwitch"}:
            continue
        controller_id = str(authored.get("controllerId") or authored.get("ownerId") or "")
        source_file = str(authored.get("sourceFile") or "")
        semantic_path = str(authored.get("semanticPath") or "")
        trigger_id = ":".join(("model-view-positioned-control", branch, controller_id or "unknown-controller", source_file or "unknown-file", str(occurrence_index)))
        if trigger_id in seen_trigger_ids:
            continue
        seen_trigger_ids.add(trigger_id)
        native_method = "TrySwitchAudioCustomState" if branch == "customStateSwitch" else "TrySwitchAudioState"
        control_definition = common_definition(authored, 0x0002)
        control_definition.pop("ownerKind", None)
        control_definition["controllerEvidence"] = {
            "controllerId": controller_id,
            "ownerStatus": "notAnOwnerProof",
            "interactiveAssociation": control_definition.pop("interactiveAssociation", {}),
        }
        contexts.append({
            "triggerId": trigger_id,
            "semanticKind": "modelViewStatePositionedCustomStateControl" if branch == "customStateSwitch" else "modelViewStatePositionedEntityStateControl",
            "triggerRole": "authoredModelViewStatePositionedControl",
            "situation": {
                "controllerId": controller_id,
                "controlBranch": branch,
                "controlValue": authored.get("controlValue"),
                "stateValue": authored.get("stateValue") if branch == "entityStateSwitch" else None,
                "eAudioTriggerState": authored.get("eAudioTriggerState"),
                "modelLevel": authored.get("modelLevel") if branch == "entityStateSwitch" else None,
                "semanticPath": semantic_path,
            },
            "meaning": {
                "category": "control",
                "foundInWwise": False,
                "playbackRole": "controlOnly",
                "wwiseEventStatus": "notPromotedToEvent",
            },
            "authoredDefinition": control_definition,
            "wwiseMediaCandidates": [],
            "runtimeBranch": {
                "status": "unresolved",
                "selectionStatus": "positionedControlExecutionUnobserved",
                "nativeControlMethod": native_method,
                "nativeRouteStatus": "exactCurrentBuildPositionedRoute" if positioned_route is not None else "nativeRouteUnavailable",
            },
            "activation": {"status": "unobserved", "reason": authored.get("runtimeActivationStatus") or "modelViewStateBehaviorExecutionNotObserved"},
            "action": {
                "controlBranch": branch,
                "controlValue": authored.get("controlValue"),
                "customAudioId": authored.get("customAudioId"),
                "stateValue": authored.get("stateValue") if branch == "entityStateSwitch" else None,
                "eAudioTriggerState": authored.get("eAudioTriggerState"),
                "modelLevel": authored.get("modelLevel") if branch == "entityStateSwitch" else None,
                "nativeControlMethod": native_method,
                "runtimeActivationStatus": "positionedControlExecutionUnobserved",
            },
            "controllerEvidence": {
                "controllerId": controller_id,
                "ownerStatus": "notAnOwnerProof",
                "sourceFile": source_file,
                "semanticPath": semantic_path,
            },
            "selection": {
                "triggerBindingStatus": "exactModelViewStatePositionedControlBranch",
                "mediaSelectionStatus": "notApplicableControlOnly",
                "runtimeSelectionStatus": "positionedControlExecutionUnobserved",
            },
            "mediaRefs": [],
            "evidence": {
                "definition": authored.get("evidence") or "exactDecodedModelViewStatePositionedControlBranch",
                "owner": "exactModelLayerStateBehaviorOwnerChain",
                "media": "controlOnlyNoWwiseEventCandidate",
                "runtimeBranch": "positionedControlExecutionUnobserved",
            },
            "runtimeActivationStatus": "positionedControlExecutionUnobserved",
            "sourceRefs": [value for value in (source_file, semantic_path, *(authored.get("sourcePaths") or [])) if isinstance(value, str) and value],
        })
        if positioned_route is not None:
            contexts[-1]["nativeRoute"] = positioned_route
        elif diagnostics.get("positioned") is not None:
            contexts[-1]["nativeRouteDiagnostic"] = {
                "status": diagnostics["positioned"].get("status"),
                "reason": str(diagnostics["positioned"].get("reason") or "")[:1000],
            }
    contexts.sort(key=lambda row: str(row.get("triggerId") or ""))
    return contexts


__all__ = ["project_model_view_state_audio_trigger_contexts"]
