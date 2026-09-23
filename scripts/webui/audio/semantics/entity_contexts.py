"""Per-entity audio semantics: characters, NPCs, patrols, spawners, footsteps.

Collects the authored audio each entity kind carries -- interaction phases,
patrol sub-actions, ability voices, spawner pre-warnings, and the custom
footstep model. Ownership is authored, not observed."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from scripts.webui.audio.semantics import build_contracts
from scripts.webui.audio.semantics import context_utils
from scripts.webui.audio.semantics import event_projection
from scripts.webui.audio.semantics import identifiers
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from scripts.webui.audio.semantics.context_utils import append_context as _append_context
from scripts.webui.audio.semantics.context_utils import load_json as load_json
from scripts.source_paths import ExportLayout

MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 = build_contracts.MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256

CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256 = build_contracts.CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256

CUSTOM_FOOTSTEP_NATIVE_ANCHORS = (
    {
        "type": "CustomFootStepEvent",
        "method": "ParseIntParameter",
        "token": "0x0600cf1f",
        "virtualAddress": "0x18378d410",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_OnCustomFootStepWithStringSpan",
        "token": "0x0600cf33",
        "virtualAddress": "0x18378c4a0",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_EnqueueFootStep",
        "token": "0x0600cf34",
        "virtualAddress": "0x18378d480",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_GetGroundInfo",
        "token": "0x0600cf36",
        "virtualAddress": "0x1832894e0",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_SyncGroundInfo",
        "token": "0x0600cf38",
        "virtualAddress": "0x183289390",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_ProcessFootStep",
        "token": "0x0600cf3a",
        "virtualAddress": "0x183289920",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_SetAudioMaterialType",
        "token": "0x0600cf3b",
        "virtualAddress": "0x183287770",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_SetAudioWaterDepth",
        "token": "0x0600cf3c",
        "virtualAddress": "0x183289190",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "FootStepHandler",
        "method": "_SetAudioMatSwitch",
        "token": "0x0600cf3d",
        "virtualAddress": "0x1832878f0",
        "evidence": "exactCurrentGameAssembly",
    },
    {
        "type": "NPCAnimatorMono",
        "method": "OnCustomFootStep",
        "token": "0x0600d0e2",
        "virtualAddress": "0x1832881e0",
        "evidence": "exactCurrentGameAssemblyLegacyReceiver",
    },
)


# The runtime fields the footstep receiver reads, by type and field name; the
# token and offset are the reviewed build's and are re-derived on any other.
CUSTOM_FOOTSTEP_FIELD_ANCHORS = (
    {"type": "FootStepConfig", "field": "footstepAudioSwitch", "token": "0x04001386",
     "offset": "0x20", "meaning": "surface enum to AudioId"},
    {"type": "FootStepConfig", "field": "footstepAudioCustomTypeSwitch", "token": "0x04001387",
     "offset": "0x28", "meaning": "GameplayTag to AudioId"},
    {"type": "WaterInteractSettings", "field": "waterDepthRtpc", "token": "0x040053b5",
     "offset": "0x74", "meaning": "water-depth RTPC AudioId"},
)

normalize_posix = context_utils.normalize_posix

def _attach_custom_footstep_parameters(
    context: dict[str, Any], evidence_rows: Iterable[dict[str, Any]]
) -> None:
    variants = event_projection.aggregate_custom_footstep_parameter_variants(
        evidence_rows
    )
    if not variants:
        return
    context["customFootstepOccurrenceCount"] = sum(
        int(variant["occurrenceCount"]) for variant in variants
    )
    context["customFootstepParameterVariants"] = variants

def build_custom_footstep_model(
    events: Iterable[dict[str, Any]],
    webui_root: Path,
    language: str,
    native_context: Any = None,
) -> dict[str, Any]:
    # Anchors name methods and fields of one build: the reviewed ones on that
    # build, the ones re-derived by name on another measured build, none else.
    if native_context is not None and native_context.validated:
        native_anchors, field_anchors = CUSTOM_FOOTSTEP_NATIVE_ANCHORS, CUSTOM_FOOTSTEP_FIELD_ANCHORS
        status = "exactCurrentBuildStaticEvidence"
        game_assembly_sha256, metadata_sha256 = CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256, MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256
    else:
        from scripts.webui.audio.semantics import native_callsite_rederivation

        rederived = (
            native_callsite_rederivation.current_routes(native_context)["customFootstep"]
            if native_context is not None else None
        ) or {}
        native_anchors = rederived.get("nativeAnchors") or ()
        field_anchors = rederived.get("fieldAnchors") or ()
        status = (
            "anchorsRederivedByNameReviewedSemanticsFromPreviousBuild" if rederived
            else "nativeAnchorsUnavailable"
        )
        game_assembly_sha256 = native_context.gameassembly_sha256 if rederived else None
        metadata_sha256 = native_context.metadata_sha256 if rederived else None
    event_rows = [
        event for event in events
        if isinstance(event, dict) and event.get("customFootstepParameterVariants")
    ]
    variants = event_projection.aggregate_custom_footstep_context_variants(
        context
        for event in event_rows
        for context in event.get("contexts") or []
        if isinstance(context, dict)
    )
    side_counts: Counter[str] = Counter()
    vfx_counts: Counter[str] = Counter()
    filter_counts: Counter[str] = Counter()
    float_counts: Counter[str] = Counter()
    for variant in variants:
        count = int(variant.get("occurrenceCount") or 0)
        side_counts[str(variant.get("footSide") or "Unknown")] += count
        vfx_counts[str(variant.get("vfxType") or "Unknown")] += count
        filter_counts[str(variant.get("playbackFilter") or "Unknown")] += count
        float_counts[str(variant.get("rawFloat"))] += count

    gameplay_path = webui_root / f"data/lang/{language}/gameplay/sound_effects.json"
    gameplay_payload = load_json(gameplay_path, {})
    evidence_name = str(gameplay_payload.get("animationEvidencePath") or "")
    evidence_path = gameplay_path.with_name(evidence_name) if evidence_name else None
    fingerprint: dict[str, Any] = {}
    source_callback_count = 0
    source_clip_ids: set[str] = set()
    source_authored_event_ids: set[str] = set()
    if evidence_path and evidence_path.is_file():
        data = evidence_path.read_bytes()
        fingerprint = {
            "path": normalize_posix(evidence_path.relative_to(webui_root)),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        source_payload = json.loads(data)
        source_event_groups: list[list[Any]] = []
        for bucket_name in ("characters", "enemies"):
            bucket = source_payload.get(bucket_name) if isinstance(source_payload, dict) else None
            if isinstance(bucket, dict):
                source_event_groups.extend(
                    events for events in bucket.values() if isinstance(events, list)
                )
        if isinstance(source_payload, dict) and isinstance(source_payload.get("ownerUnresolved"), list):
            source_event_groups.append(source_payload["ownerUnresolved"])
        for source_events in source_event_groups:
            for source_event in source_events:
                if not isinstance(source_event, dict):
                    continue
                for evidence in source_event.get("evidence") or []:
                    if not isinstance(evidence, dict) or evidence.get("function") != "OnCustomFootStep":
                        continue
                    source_callback_count += 1
                    clip_id = str(evidence.get("clipSource") or evidence.get("clip") or "")
                    if clip_id:
                        source_clip_ids.add(clip_id)
                    authored_event_id = str(evidence.get("authoredEventId") or source_event.get("id") or "")
                    if authored_event_id:
                        source_authored_event_ids.add(authored_event_id)

    context_rows = [
        context
        for event in event_rows
        for context in event.get("contexts") or []
        if isinstance(context, dict) and context.get("customFootstepParameterVariants")
    ]
    owner_kind_counts = Counter(
        "character" if context.get("kind") == "characterAnimation"
        else "enemy" if context.get("kind") == "enemyAnimation"
        else "ownerUnresolved"
        for context in context_rows
    )
    occurrence_owner_kind_counts = Counter()
    for context in context_rows:
        kind = (
            "character" if context.get("kind") == "characterAnimation"
            else "enemy" if context.get("kind") == "enemyAnimation"
            else "ownerUnresolved"
        )
        occurrence_owner_kind_counts[kind] += int(context.get("customFootstepOccurrenceCount") or 0)
    return {
        "status": status,
        "callback": "OnCustomFootStep",
        "gameAssemblySha256": game_assembly_sha256,
        "metadataSha256": metadata_sha256,
        "sourceFingerprint": fingerprint,
        "parameterMasks": {"footSide": "0x03", "vfxType": "0x1c", "playbackFilter": "0xe0"},
        "runtimeVfxWeightThreshold": (
            event_projection.CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD
        ),
        "nativeAnchors": [dict(anchor) for anchor in native_anchors],
        "runtimeFieldAnchors": [dict(anchor) for anchor in field_anchors],
        "corpus": {
            "eventCount": len(event_rows),
            "authoredEventIdCount": len(source_authored_event_ids) or len(event_rows),
            "animationClipCount": len(source_clip_ids),
            "contextCount": len(context_rows),
            "occurrenceCount": sum(int(row.get("occurrenceCount") or 0) for row in variants),
            "sourceOccurrenceCount": source_callback_count,
            "parameterVariantCount": len(variants),
            "contextOwnerKinds": dict(sorted(owner_kind_counts.items())),
            "occurrenceOwnerKinds": dict(sorted(occurrence_owner_kind_counts.items())),
            "footSides": dict(sorted(side_counts.items())),
            "vfxTypes": dict(sorted(vfx_counts.items())),
            "playbackFilters": dict(sorted(filter_counts.items())),
            "rawFloats": dict(sorted(float_counts.items())),
        },
        "runtimeSelectorBoundary": (
            "FootStepHandler selects the packed left/right foot and raycasts ground. Surface type "
            "selects FootStepConfig.footstepAudioSwitch, a custom tag selects "
            "footstepAudioCustomTypeSwitch, and _SetAudioMatSwitch posts the chosen AudioId through "
            "AudioAdapter._PostEvent (it is not a direct SetSwitch call). Water writes 1.0 for decal "
            "water, 0.0 when leaving water, or bounded sensor-relative height through "
            "WaterInteractSettings.waterDepthRtpc. Static evidence does not map any of those values "
            "to a particular Wwise switch child; legacy NPCAnimatorMono ignores packed int/float."
        ),
        "evidenceBoundary": (
            "The packed callback fields and stock-client filter/VFX thresholds are exact native "
            "semantics. AnimationClip rows prove authored requests, not which receiver ran, the "
            "sampled ground material or water depth, callback execution, or a selected Wwise leaf."
        ),
    }

def collect_gameplay_contexts(webui_root: Path, language: str) -> dict[str, list[dict[str, Any]]]:
    gameplay_path = webui_root / f"data/lang/{language}/gameplay/sound_effects.json"
    payload = load_json(gameplay_path, {})
    evidence_path = str(payload.get("animationEvidencePath") or "") if isinstance(payload, dict) else ""
    animation_evidence = load_json(gameplay_path.with_name(evidence_path), {}) if evidence_path else {}
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for reference in payload.get("authoredConfigEventReferences") or []:
        if not isinstance(reference, dict):
            continue
        context = {
            "kind": "gameplayConfigAudioReference",
            "semanticRole": "authoredGameplayConfigAudioReference",
            "configKind": str(reference.get("configKind") or ""),
            "configId": str(reference.get("configId") or ""),
            "confidence": "direct",
            "playbackPlacementStatus": "authoredConfigAudioReference",
            "triggerBindingStatus": "exactMemoryPackLengthPrefixedAudioEventString",
            "triggerRequestEvidence": ["exactMemoryPackLengthPrefixedAudioEventString"],
            "triggerSourcePaths": list(reference.get("sourcePaths") or []),
            "triggerRuntimeActivationStatuses": ["configRuntimeExecutionNotObserved"],
            "ownerLinkStatus": "unresolved",
        }
        _append_context(contexts, seen, reference.get("eventId"), context)
    for action in payload.get("authoredPlaySoundActions") or []:
        if not isinstance(action, dict):
            continue
        context = {
            "kind": "buffPlaySoundAction",
            "confidence": "direct",
            "semanticRole": "authoredAbilitySoundAction",
            "triggerRequestEvidence": ["exactAuthoredPlaySoundAction"],
            "triggerRuntimeActivationStatuses": ["authoredFrameWindowRecoveredConditionUnresolved"],
            "triggerRelationTypes": ["buffPlaySoundAction"],
            "triggerEvidenceKinds": ["buffPlaySoundActionData"],
            "triggerBuffIds": [str(action.get("buffId") or "")],
            "triggerSourcePaths": list(action.get("sourcePaths") or []),
            "triggerPlaySoundActionCount": 1,
            "triggerPlaySoundActions": [action],
        }
        _append_context(contexts, seen, action.get("eventId"), context)
    for owner_kind, bucket_name in (("character", "characters"), ("enemy", "enemies")):
        bucket = payload.get(bucket_name) if isinstance(payload, dict) else None
        if not isinstance(bucket, dict):
            continue
        for owner_id, owner in bucket.items():
            if not isinstance(owner, dict):
                continue
            groups = owner.get("groups") if owner_kind == "character" else {"": owner}
            if not isinstance(groups, dict):
                continue
            for group_id, group in groups.items():
                if not isinstance(group, dict):
                    continue
                for event in group.get("events") or []:
                    if not isinstance(event, dict):
                        continue
                    trigger_bindings = [
                        binding for binding in event.get("triggerBindings") or []
                        if isinstance(binding, dict)
                    ]
                    trigger_play_sound_actions: list[dict[str, Any]] = []
                    seen_trigger_actions: set[str] = set()
                    for binding in trigger_bindings:
                        for action in binding.get("playSoundActions") or []:
                            if not isinstance(action, dict):
                                continue
                            marker = json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                            if marker in seen_trigger_actions:
                                continue
                            seen_trigger_actions.add(marker)
                            trigger_play_sound_actions.append(action)
                    context = {
                        "kind": "characterSkill" if owner_kind == "character" else "enemySkill",
                        "ownerId": owner_id,
                        "confidence": (
                            "direct" if event.get("triggerBindingStatus") in {"exactSkillConfig", "exactEnemyBornBuffConfig"}
                            else group.get("ownershipConfidence") or owner.get("ownershipConfidence") or ""
                        ),
                        "triggerBindingStatus": event.get("triggerBindingStatus") or "",
                        "triggerBindingCount": len(trigger_bindings),
                        "triggerRequestEvidence": sorted({
                            str(binding.get("requestEvidence") or "")
                            for binding in trigger_bindings
                            if binding.get("requestEvidence")
                        })[:4],
                        "triggerRuntimeActivationStatuses": sorted({
                            str(binding.get("runtimeActivationStatus") or "")
                            for binding in trigger_bindings
                            if binding.get("runtimeActivationStatus")
                        })[:4],
                        "triggerRelationTypes": list(event.get("triggerRelationTypes") or [])[:8],
                        "triggerOwnershipMethods": sorted({
                            str(binding.get("ownershipMethod") or "")
                            for binding in trigger_bindings
                            if binding.get("ownershipMethod")
                        })[:8],
                        "triggerEvidenceKinds": sorted({
                            str(kind)
                            for binding in trigger_bindings
                            for kind in binding.get("evidenceKinds") or []
                            if str(kind)
                        })[:8],
                        "triggerBuffIds": sorted({
                            str(buff_id)
                            for binding in trigger_bindings
                            for buff_id in binding.get("buffIds") or []
                            if str(buff_id)
                        })[:12],
                        "triggerSourcePaths": sorted({
                            str(path)
                            for binding in trigger_bindings
                            for path in binding.get("sourcePaths") or []
                            if str(path)
                        })[:12],
                    }
                    if trigger_play_sound_actions:
                        context["triggerPlaySoundActionCount"] = len(trigger_play_sound_actions)
                    if group_id:
                        context["groupId"] = group_id
                    skill_ids = event.get("sourceSkillIds") or group.get("skillIds") or owner.get("skillIds")
                    if skill_ids:
                        context["skillIds"] = list(skill_ids)[:12]
                    _append_context(contexts, seen, event.get("id"), context)
            evidence_bucket = animation_evidence.get(bucket_name) if isinstance(animation_evidence, dict) else None
            animation_events = (
                evidence_bucket.get(owner_id)
                if isinstance(evidence_bucket, dict) and isinstance(evidence_bucket.get(owner_id), list)
                else owner.get("animationEvents") or []
            )
            for event in animation_events:
                if not isinstance(event, dict):
                    continue
                evidence = event.get("evidence") or []
                context = {
                    "kind": "characterAnimation" if owner_kind == "character" else "enemyAnimation",
                    "ownerId": owner_id,
                    "confidence": owner.get("animationOwnershipConfidence") or "inferred",
                    "actionKinds": list(event.get("actionKinds") or [])[:8],
                    "animationFunctions": list(event.get("animationFunctions") or [])[:8],
                    "animationClipContexts": list(event.get("animationClipContexts") or [])[:8],
                    "animationClips": list(event.get("sourceAnimationClips") or [])[:12],
                    "animationOccurrenceCount": len(evidence),
                    "animationOwnerCount": int(event.get("animationOwnerCount") or 0),
                    "animationOwnershipScope": event.get("animationOwnershipScope") or "",
                    "possibleMediaScope": event.get("possibleMediaScope") or "",
                    "clipReachability": event.get("clipReachability") or "unresolved",
                    "animatorControllerCount": int(event.get("animatorControllerCount") or 0),
                    "animatorControllerContexts": list(event.get("animatorControllerContexts") or [])[:12],
                    "animatorControllerReachableClipCount": int(
                        event.get("animatorControllerReachableClipCount") or 0
                    ),
                    "animatorControllerUnresolvedClipCount": int(
                        event.get("animatorControllerUnresolvedClipCount") or 0
                    ),
                    "authoredEventIds": list(event.get("authoredEventIds") or [])[:8],
                }
                _attach_custom_footstep_parameters(context, evidence)
                _append_context(contexts, seen, event.get("id"), context)
    for event in animation_evidence.get("ownerUnresolved") or []:
        if not isinstance(event, dict):
            continue
        evidence = [row for row in event.get("evidence") or [] if isinstance(row, dict)]
        context = {
            "kind": "animationCallbackOwnerUnresolved",
            "confidence": "exactCallbackOwnerUnresolved",
            "semanticRole": "authoredAnimationAudioCallback",
            "ownerStatus": "unresolved",
            "actionKinds": list(event.get("actionKinds") or [])[:8],
            "animationFunctions": list(event.get("animationFunctions") or [])[:8],
            "animationClipContexts": list(event.get("animationClipContexts") or [])[:8],
            "animationClips": list(event.get("sourceAnimationClips") or [])[:12],
            "animationOccurrenceCount": len(evidence),
            "clipReachability": event.get("clipReachability") or "unresolved",
            "animatorControllerCount": int(event.get("animatorControllerCount") or 0),
            "animatorControllerContexts": list(event.get("animatorControllerContexts") or [])[:12],
            "animatorControllerReachableClipCount": int(
                event.get("animatorControllerReachableClipCount") or 0
            ),
            "animatorControllerUnresolvedClipCount": int(
                event.get("animatorControllerUnresolvedClipCount") or 0
            ),
            "authoredEventIds": list(event.get("authoredEventIds") or [])[:8],
            "sourcePaths": sorted({
                str(row.get("clipSource") or "")
                for row in evidence
                if str(row.get("clipSource") or "")
            })[:12],
        }
        _attach_custom_footstep_parameters(context, evidence)
        _append_context(contexts, seen, event.get("id"), context)
    return dict(contexts)

def collect_spawner_pre_warn_semantics(
    export_root: Path,
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact current SpawnerEnemyLibraryItem pre-warning Events."""
    if decoder is None:
        from scripts.game_data.spawner_binary import decode_spawner_enemy_library
        decoder = decode_spawner_enemy_library

    spawner_root: Path | None = None
    source_root = ""
    for candidate_root in ("game",):
        candidate = ExportLayout(export_root).game / "Json/SpawnerConfig"
        if candidate.is_dir():
            spawner_root = candidate
            source_root = candidate_root
            break

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    failures: list[dict[str, str]] = []
    source_files = 0
    decoded_files = 0
    enemy_rows = 0
    pre_warn_contexts = 0
    if spawner_root is not None:
        for path in sorted(spawner_root.rglob("*.json"), key=lambda item: item.as_posix().lower()):
            if not path.is_file():
                continue
            source_files += 1
            source = normalize_posix(path.relative_to(export_root))
            try:
                data = path.read_bytes()
                decoded = decoder(data)
            except (OSError, ValueError) as exc:
                if len(failures) < 16:
                    failures.append({"source": source, "error": str(exc)})
                continue
            if not isinstance(decoded, dict) or not isinstance(decoded.get("enemyLibrary"), list):
                if len(failures) < 16:
                    failures.append({"source": source, "error": "decoder returned no enemyLibrary"})
                continue
            decoded_files += 1
            fingerprint = hashlib.sha256(data).hexdigest()
            config_id = str(decoded.get("configId") or path.stem)
            schema_mapping_id = str(decoded.get("schemaMappingId") or "")
            schema_status = str(decoded.get("schemaStatus") or "")
            for enemy in decoded["enemyLibrary"]:
                if not isinstance(enemy, dict):
                    continue
                enemy_rows += 1
                authored_event_id = str(enemy.get("preWarnAudioEventKey") or "").strip()
                if not authored_event_id:
                    continue
                row_index = int(enemy.get("index") or 0)
                born_buff_ids = sorted({
                    str(buff.get("buffId") or "")
                    for buff in enemy.get("bornBuffList") or []
                    if isinstance(buff, dict) and buff.get("buffId")
                })
                context = {
                    "kind": "spawnerPreWarnAudio",
                    "ownerId": str(enemy.get("enemyId") or ""),
                    "confidence": "direct",
                    "semanticRole": "authoredSpawnerEnemyPreWarning",
                    "authoredEventId": authored_event_id,
                    "spawnerConfigId": config_id,
                    "enemyLibraryIndex": row_index,
                    "enemyId": str(enemy.get("enemyId") or ""),
                    "bornTemplateId": str(enemy.get("bornTemplateId") or ""),
                    "enemyLevel": enemy.get("enemyLevel"),
                    "spawnerEnemyKey": str(enemy.get("key") or ""),
                    "preWarnTime": enemy.get("preWarnTime"),
                    "preWarnEffectKey": str(enemy.get("preWarnEffectKey") or ""),
                    "preWarnEffectFixedRotation": list(enemy.get("preWarnEffectFixedRotation") or []),
                    "bornBuffIds": born_buff_ids,
                    "source": source,
                    "sourceRoot": source_root,
                    "sourcePaths": [source],
                    "sourceFingerprint": fingerprint,
                    "sourceOffset": enemy.get("sourceOffset"),
                    "path": f"enemyLibrary[{row_index}].preWarnAudioEventKey",
                    "semanticPath": "SpawnerConfig.enemyLibrary.preWarnAudioEventKey",
                    "schemaMappingId": schema_mapping_id,
                    "schemaStatus": schema_status,
                    "triggerRequestEvidence": ["serializedSpawnerEnemyLibraryItemPreWarnAudioEventKey"],
                    "triggerRuntimeActivationStatuses": ["runtimeSpawnerPreWarningConditionRequired"],
                    "runtimeActivationStatus": "spawnerPreWarningExecutionNotObserved",
                }
                _append_context(contexts, seen, authored_event_id, context)
                pre_warn_contexts += 1

    stats = {
        "status": (
            "unavailable" if spawner_root is None
            else "complete" if decoded_files == source_files
            else "partial"
        ),
        "sourceRoot": source_root,
        "sourceFiles": source_files,
        "decodedFiles": decoded_files,
        "failedFiles": source_files - decoded_files,
        "enemyRows": enemy_rows,
        "preWarnAudioContexts": pre_warn_contexts,
        "distinctPreWarnAudioEvents": len(contexts),
        "failureSamples": failures,
        "evidenceBoundary": (
            "The current mc13 SpawnerEnemyLibraryItem field proves an authored enemy-spawn "
            "pre-warning Event request, timing value, effect key, enemy/template, and source row. "
            "It does not prove that the spawner ran or that a Wwise branch played. Non-null "
            "bornBehaviorData is rejected because no current authored fixture exercises it."
        ),
    }
    return {"eventContexts": dict(contexts), "stats": stats}

def collect_patrol_sub_action_audio_semantics(
    export_root: Path,
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact authored ``PatrolSubPlayAudioData`` Event requests."""
    if decoder is None:
        from scripts.webui.story.level_bindings import decode_leveldata_npc_patrol_list
        decoder = decode_leveldata_npc_patrol_list

    leveldata_root: Path | None = None
    source_root = ""
    for candidate_root in ("game",):
        candidate = ExportLayout(export_root).game / "Json/LevelData"
        if candidate.is_dir():
            leveldata_root = candidate
            source_root = candidate_root
            break

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    failures: list[dict[str, str]] = []
    source_files = 0
    decoded_files = 0
    no_nonempty_patrol_files = 0
    patrol_rows = 0
    patrol_points = 0
    patrol_actions = 0
    play_audio_contexts = 0
    if leveldata_root is not None:
        for path in sorted(leveldata_root.rglob("*.json"), key=lambda item: item.as_posix().lower()):
            if not path.is_file():
                continue
            source_files += 1
            source = normalize_posix(path.relative_to(export_root))
            try:
                data = path.read_bytes()
                decoded = decoder(data)
            except (OSError, ValueError) as exc:
                if len(failures) < 16:
                    failures.append({"source": source, "error": str(exc)})
                continue
            if not isinstance(decoded, dict) or not isinstance(decoded.get("patrols"), list):
                if len(failures) < 16:
                    failures.append({"source": source, "error": "decoder returned no patrols list"})
                continue
            if decoded.get("status") == "noNonemptyTypedPatrolList":
                no_nonempty_patrol_files += 1
                continue
            if decoded.get("status") != "exactNonemptyTypedPatrolList":
                if len(failures) < 16:
                    failures.append({"source": source, "error": "decoder returned an unsupported status"})
                continue
            decoded_files += 1
            fingerprint = hashlib.sha256(data).hexdigest()
            schema_mapping_id = str(decoded.get("schemaMappingId") or "")
            for patrol in decoded["patrols"]:
                if not isinstance(patrol, dict):
                    continue
                patrol_rows += 1
                patrol_id = int(patrol.get("patrolId") or 0)
                patrol_index = int(patrol.get("patrolIndex") or 0)
                for point in patrol.get("points") or []:
                    if not isinstance(point, dict):
                        continue
                    patrol_points += 1
                    point_index = int(point.get("pointIndex") or 0)
                    for action_index, action in enumerate(point.get("actions") or []):
                        if not isinstance(action, dict):
                            continue
                        patrol_actions += 1
                        sub_action = action.get("subActionData")
                        if not (
                            action.get("type") == 11
                            and action.get("subActionDataUnionTag") == 1
                            and isinstance(sub_action, dict)
                            and sub_action.get("kind") == "PatrolSubPlayAudioData"
                        ):
                            continue
                        event_hash = int(sub_action.get("audioEventHash") or 0) & 0xFFFFFFFF
                        if not event_hash:
                            continue
                        signed_value = int(sub_action.get("audioEventId") or 0)
                        event_hex = f"0x{event_hash:08x}"
                        context = {
                            "kind": "patrolSubActionPlayAudio",
                            "ownerId": f"patrol:{patrol_id}",
                            "confidence": "direct",
                            "semanticRole": "authoredNpcPatrolPointAudio",
                            "eventHash": event_hash,
                            "eventHex": event_hex,
                            "signedValue": signed_value,
                            "patrolId": patrol_id,
                            "patrolIndex": patrol_index,
                            "pointIndex": point_index,
                            "actionIndex": action_index,
                            "patrolSubActionType": 11,
                            "subActionUnionTag": 1,
                            "subActionUnionTagHex": "0x01",
                            "waitTime": action.get("waitTime"),
                            "source": source,
                            "sourceRoot": source_root,
                            "sourcePaths": [source],
                            "sourceFingerprint": fingerprint,
                            "sourceOffset": action.get("recordOffset"),
                            "path": (
                                f"npcPatrolData[{patrol_index}].points[{point_index}]"
                                f".actions[{action_index}].subActionData.audioEventId"
                            ),
                            "semanticPath": "LevelData.npcPatrolData.points.actions.PatrolSubPlayAudioData.audioEventId",
                            "schemaMappingId": schema_mapping_id,
                            "schemaStatus": "exactCurrentMemoryPackCursor",
                            "triggerRequestEvidence": ["serializedPatrolSubPlayAudioDataAudioId"],
                            "triggerRuntimeActivationStatuses": ["runtimePatrolPointActionExecutionRequired"],
                            "runtimeActivationStatus": "patrolPointActionExecutionNotObserved",
                            "nativeConsumer": (
                                "NewNpcAIPatrolController._PlayAudioSubAction "
                                "(token 0x0600aedb)"
                            ),
                        }
                        _append_context(
                            contexts,
                            seen,
                            identifiers.event_hash_context_key(event_hash),
                            context,
                        )
                        play_audio_contexts += 1

    failed_files = source_files - decoded_files - no_nonempty_patrol_files
    stats = {
        "status": (
            "unavailable" if leveldata_root is None
            else "complete" if failed_files == 0
            else "partial"
        ),
        "sourceRoot": source_root,
        "sourceFiles": source_files,
        "decodedFiles": decoded_files,
        "noNonemptyTypedPatrolListFiles": no_nonempty_patrol_files,
        "failedFiles": failed_files,
        "patrolRows": patrol_rows,
        "patrolPoints": patrol_points,
        "patrolActions": patrol_actions,
        "playAudioContexts": play_audio_contexts,
        "distinctPlayAudioEvents": len(contexts),
        "failureSamples": failures,
        "evidenceBoundary": (
            "A fully consumed current LevelData/43 member-31 NpcPatrolData/9 -> point/3 -> "
            "PatrolSubAction/26 tag-1 PatrolSubPlayAudioData/1 row proves an authored "
            "patrol-point Event request and exact patrol/point/action source. It does not prove "
            "that the patrol reached the point, the action executed, or any Wwise media branch played. "
            "Files without a unique non-empty typed patrol frame remain explicitly empty; drift and "
            "ambiguous frames fail closed."
        ),
    }
    return {"eventContexts": dict(contexts), "stats": stats}

def collect_char_interact_audio_semantics(
    export_root: Path,
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact numeric AudioEvent actions from current interaction performs."""
    if decoder is None:
        from scripts.game_data.char_interact_perform_binary import (
            decode_char_interact_audio_actions,
        )
        decoder = decode_char_interact_audio_actions

    roots = ("game",)
    relative_versions: dict[str, list[tuple[str, Path, str]]] = defaultdict(list)
    for source_root in roots:
        root = (
            ExportLayout(export_root).game
            / "Json/CharInteractPerformCfgs"
        )
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json"), key=lambda item: item.name.lower()):
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            relative_versions[path.name].append((source_root, path, digest))

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    failures: list[dict[str, Any]] = []
    candidate_owners = 0
    decoded_owners = 0
    action_count = 0
    phase_counts: Counter[str] = Counter()
    audio_ids: set[int] = set()
    mirror_mismatches = 0
    for relative_name, versions in sorted(relative_versions.items()):
        roots_present = {row[0] for row in versions}
        digests = {row[2] for row in versions}
        if roots_present != set(roots) or len(digests) != 1:
            mirror_mismatches += 1
            if len(failures) < 16:
                failures.append({
                    "source": relative_name,
                    "error": "StreamingAssets/Persistent mirror missing or changed",
                    "sourceRoots": sorted(roots_present),
                    "sourceSha256": sorted(digests),
                })
            continue
        source_root, path, digest = versions[0]
        data = path.read_bytes()
        if bytes((0x02, 0x0F)) not in data:
            continue
        candidate_owners += 1
        try:
            rows = decoder(data)
        except (OSError, ValueError) as exc:
            if len(failures) < 16:
                failures.append({"source": relative_name, "error": str(exc)})
            continue
        if not isinstance(rows, list) or not rows:
            if len(failures) < 16:
                failures.append({
                    "source": relative_name,
                    "error": "candidate owner returned no bounded AudioEvent actions",
                })
            continue
        decoded_owners += 1
        source_paths = [
            normalize_posix(version_path.relative_to(export_root))
            for _root, version_path, _digest in versions
        ]
        owner_id = path.stem
        for row in rows:
            if not isinstance(row, dict):
                continue
            event_hash = int(row.get("audioEvent") or 0) & 0xFFFFFFFF
            if not event_hash:
                continue
            placement = str(row.get("placement") or "")
            action_index = int(row.get("actionIndex") or 0)
            action_count += 1
            phase_counts[placement] += 1
            audio_ids.add(event_hash)
            context = {
                "kind": "charInteractAudioEvent",
                "ownerId": owner_id,
                "confidence": "direct",
                "semanticRole": "authoredCharacterInteractionAudioEvent",
                "charInteractPerformId": owner_id,
                "actionPhase": placement,
                "actionIndex": action_index,
                "logicId": row.get("logicId"),
                "delay": row.get("delay"),
                "duration": row.get("duration"),
                "devOnly": bool(row.get("devOnly")),
                "useEvent": bool(row.get("useEvent")),
                "eventId": str(row.get("eventId") or ""),
                "attachedActorType": row.get("attachedActorType"),
                "charIndex": row.get("charIndex"),
                "endStop": bool(row.get("endStop")),
                "is2D": bool(row.get("is2D")),
                "eventHash": event_hash,
                "eventHex": f"0x{event_hash:08x}",
                "source": source_paths[0],
                "sourceRoot": source_root,
                "sourcePaths": source_paths,
                "sourceFingerprint": digest,
                "sourceSha256": digest,
                "sourceOffset": row.get("sourceOffset"),
                "endOffset": row.get("endOffset"),
                "path": f"{placement}[{action_index}].audioEvent",
                "semanticPath": (
                    f"CharInteractPerformRuntimeCfg.{placement}[{action_index}]"
                    ".AudioEventActData.audioEvent"
                ),
                "unionTag": row.get("unionTag"),
                "unionTagHex": row.get("unionTagHex"),
                "serializedMemberCount": row.get("memberCount"),
                "schemaMappingId": row.get("schemaMappingId"),
                "unionMappingId": row.get("unionMappingId"),
                "schemaStatus": row.get("schemaStatus"),
                "triggerBindingStatus": "exactCharInteractPerformConfig",
                "triggerRequestEvidence": [
                    "serializedCharInteractPerformAudioEventActDataAudioEvent"
                ],
                "triggerRuntimeActivationStatuses": [
                    "charInteractPerformRuntimeExecutionNotObserved"
                ],
                "runtimeActivationStatus": (
                    "charInteractPerformRuntimeExecutionNotObserved"
                ),
                "runtimeOwnerStatus": "authoredPerformConfigOwnerOnly",
                "attachedActorResolutionStatus": "runtimeActorResolutionNotObserved",
            }
            _append_context(
                contexts, seen, identifiers.event_hash_context_key(event_hash), context
            )

    stats = {
        "status": (
            "unavailable" if not relative_versions
            else "complete" if not failures and decoded_owners == candidate_owners
            else "partial"
        ),
        "physicalFiles": sum(len(rows) for rows in relative_versions.values()),
        "ownerFiles": len(relative_versions),
        "mirrorMismatches": mirror_mismatches,
        "candidateOwners": candidate_owners,
        "decodedOwners": decoded_owners,
        "audioEventActions": action_count,
        "distinctAudioIds": len(audio_ids),
        "actionPhaseCounts": dict(sorted(phase_counts.items())),
        "failureSamples": failures,
        "evidenceBoundary": (
            "The exact current 27-member CharInteractPerformRuntimeCfg, counted action-list "
            "phase, tag-0x02/member-15 AudioEventActData, and numeric AudioId prove an "
            "authored request owned by the perform config. They do not prove that the "
            "perform executed, which runtime actor was attached, that AudioId resolved to "
            "a loaded Wwise Event, or that a Wwise media branch played."
        ),
    }
    return {"eventContexts": dict(contexts), "stats": stats}

ABILITY_VOICE_TRIGGER_PREFIX = b"\xfa\x7c\x01\x08"

ABILITY_VOICE_TRIGGER_MAPPING_ID = (
    "gameassembly-2026-08-13-ability-voice-trigger-action-0x017c"
)

ABILITY_VOICE_TRIGGER_KEY_RE = re.compile(r"^[a-z0-9_]{1,128}$")

ABILITY_VOICE_OWNER_RE = re.compile(
    r"^((?:chr|eny)_\d{4}_[a-z0-9]+)(?:_|$)",
    re.IGNORECASE,
)

def collect_ability_voice_trigger_contexts(
    export_root: Path,
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Join exact SkillData VoiceTriggerAction records to compatible Events.

    Current ``AbilityActionData`` union tag ``0x017c`` has eight members. The
    generated MemoryPack setter order after the four inherited action members
    is ``_canInterruptTimeMs``, ``_speakerType``, ``_triggerKey``, then
    ``targetSettings``. ``VoiceTriggerAction.ExecuteInternal`` passes that
    trigger key and the resolved target entity to ``VoiceManager.ResponseOnEntity``.

    Live response selection can still apply cooldown, probability, speaker,
    and target rules. We therefore admit only the unique current
    AudioDialog/Wwise identity named exactly
    ``<SkillData owner>_<triggerKey>_sv`` and keep it as an authored possible
    trigger rather than claiming observed playback.
    """

    aliases_by_name = {
        str(row.get("name") or "").strip().casefold(): row
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    }
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    source_root = (
        ExportLayout(export_root).json_dir / "SkillData"
    )
    if not source_root.is_dir() or not aliases_by_name:
        return {}

    for path in sorted(source_root.glob("*.json"), key=lambda item: item.name):
        owner_match = ABILITY_VOICE_OWNER_RE.match(path.stem)
        if owner_match is None:
            continue
        owner_id = owner_match.group(1).casefold()
        try:
            data = path.read_bytes()
        except OSError:
            continue
        source_path = normalize_posix(path.relative_to(export_root))
        source_sha256 = hashlib.sha256(data).hexdigest()
        offset = 0
        while True:
            action_offset = data.find(ABILITY_VOICE_TRIGGER_PREFIX, offset)
            if action_offset < 0:
                break
            offset = action_offset + 1
            payload_offset = action_offset + len(ABILITY_VOICE_TRIGGER_PREFIX)
            # bool + inherited 3*i32 + interrupt + speaker + string length
            if payload_offset + 25 > len(data):
                continue
            enabled = data[payload_offset]
            if enabled not in (0, 1):
                continue
            try:
                (
                    priority_level,
                    priority_offset,
                    server_action_index,
                    can_interrupt_time_ms,
                    speaker_type,
                    trigger_length,
                ) = struct.unpack_from("<iiiiii", data, payload_offset + 1)
            except struct.error:
                continue
            trigger_start = payload_offset + 25
            trigger_end = trigger_start + trigger_length
            if (
                enabled != 1
                or abs(priority_level) > 1_000_000
                or abs(priority_offset) > 1_000_000
                or abs(server_action_index) > 1_000_000
                or can_interrupt_time_ms < -1
                or can_interrupt_time_ms > 3_600_000
                or speaker_type < 0
                or speaker_type > 255
                or trigger_length < 1
                or trigger_length > 128
                or trigger_end > len(data)
            ):
                continue
            try:
                trigger_key = data[trigger_start:trigger_end].decode("ascii")
            except UnicodeDecodeError:
                continue
            if ABILITY_VOICE_TRIGGER_KEY_RE.fullmatch(trigger_key) is None:
                continue
            event_name = f"{owner_id}_{trigger_key}_sv"
            alias = aliases_by_name.get(event_name.casefold())
            if not isinstance(alias, dict):
                continue
            context = {
                "kind": "abilityVoiceTriggerAction",
                "confidence": "direct",
                "semanticRole": "authoredAbilityVoiceResponseTrigger",
                "playbackPlacementStatus": "authoredPossibleTrigger",
                "triggerBindingStatus": (
                    "exactAbilityVoiceTriggerAndUniqueOwnerEventIdentity"
                ),
                "configKind": "SkillData",
                "configId": path.stem,
                "ownerId": owner_id,
                "sourcePath": source_path,
                "sourcePaths": [source_path],
                "sourceSha256": source_sha256,
                "actionOffset": action_offset,
                "actionOffsetHex": f"0x{action_offset:x}",
                "actionUnionTag": "0x017c",
                "serializedMemberCount": 8,
                "nativeMappingId": ABILITY_VOICE_TRIGGER_MAPPING_ID,
                "isEnabled": True,
                "priorityLevel": priority_level,
                "priorityOffset": priority_offset,
                "serverActionIndex": server_action_index,
                "canInterruptTimeMs": can_interrupt_time_ms,
                "speakerType": speaker_type,
                "triggerKey": trigger_key,
                "eventName": str(alias.get("name") or event_name),
                "eventHash": alias.get("eventHash"),
                "eventNameEvidence": alias.get("evidence"),
                "eventSelectionStatus": (
                    "uniqueSkillOwnerTriggerCompatibleAudioDialogWwiseEvent;"
                    "responsiveRuntimeSelectionUnobserved"
                ),
                "runtimeRoute": (
                    "VoiceTriggerAction.ExecuteInternal -> "
                    "VoiceManager.ResponseOnEntity -> VoiceResponseProcessor -> "
                    "VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice"
                ),
                "runtimeActivationStatus": (
                    "abilityActionExecutionTargetResolutionAndResponseSelectionUnobserved"
                ),
                "triggerRequestEvidence": [
                    "exactAbilityActionDataUnionTagAndMemberCount",
                    "exactVoiceTriggerActionMemoryPackSetterOrder",
                    "currentGameAssemblyResponseOnEntityCall",
                    "exactAudioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                ],
            }
            _append_context(contexts, seen, event_name, context)
    return dict(contexts)
