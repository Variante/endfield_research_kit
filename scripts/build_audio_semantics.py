#!/usr/bin/env python3
"""Build compact WebUI data for Endfield audio semantics.

The normal audio index under ``export_full/structured/Audio/<LANG>`` is the
lossless recovery surface and can be tens of megabytes.  This builder keeps
that file authoritative, then publishes a compact overview plus lazy event and
media shards for the Audio page.  Installed IL2CPP metadata is optional:
when present, selected runtime-system types and members are validated against
the current binary metadata instead of being asserted from a stale snapshot.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import tempfile
import re
import shutil
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


if __package__ == "scripts":
    from scripts.common import sha256_file as file_sha256
    from .audio_semantics.mono_behaviour import build_runtime_model, collect_metadata_event_symbol_aliases, collect_mono_behaviour_audio_id_contexts, AUDIO_MUSIC_NATIVE_TRANSITION_REGISTRATIONS
    from .audio_semantics.timeline import build_timeline_audio_cue_contexts, collect_timeline_audio_ownership, enrich_timeline_audio_ownership_from_raw_json, merge_timeline_audio_ownership, normalize_levelsequence_audio_id
    from .audio_semantics.levelscript import attach_levelscript_radio_contexts, collect_levelscript_audio_semantics
    from .audio_semantics.media_rows import annotate_media_event_contexts, annotate_media_post_process_effect_chains, annotate_media_trigger_contexts, annotate_media_trigger_semantic_categories, build_media_rows, split_media_row
    from .audio_semantics.trigger_contexts import build_trigger_context_catalog
    from scripts.audio_semantics import (
        authored_components,
        context_utils,
        dialog_lifecycle,
        event_projection,
        event_summary,
        identifiers,
        interactive_components,
        managed_literals,
        media_ownership,
        model_view_projection,
        native_evidence,
        purpose,
        responsive_voice,
        rtpc_alignment,
        runtime_observations,
        scene_backgrounds,
        table_contexts,
        build_contracts,
        voice_requests,
    )
    from scripts.animestudio_index_io import (
        ObjectIndexUnavailable,
        iter_published_objects,
        published_object_index_path,
    )
elif not __package__:
    from common import sha256_file as file_sha256
    from audio_semantics.mono_behaviour import build_runtime_model, collect_metadata_event_symbol_aliases, collect_mono_behaviour_audio_id_contexts, AUDIO_MUSIC_NATIVE_TRANSITION_REGISTRATIONS
    from audio_semantics.timeline import build_timeline_audio_cue_contexts, collect_timeline_audio_ownership, enrich_timeline_audio_ownership_from_raw_json, merge_timeline_audio_ownership, normalize_levelsequence_audio_id
    from audio_semantics.levelscript import attach_levelscript_radio_contexts, collect_levelscript_audio_semantics
    from audio_semantics.media_rows import annotate_media_event_contexts, annotate_media_post_process_effect_chains, annotate_media_trigger_contexts, annotate_media_trigger_semantic_categories, build_media_rows, split_media_row
    from audio_semantics.trigger_contexts import build_trigger_context_catalog
    from audio_semantics import (
        authored_components,
        context_utils,
        dialog_lifecycle,
        event_projection,
        event_summary,
        identifiers,
        interactive_components,
        managed_literals,
        media_ownership,
        model_view_projection,
        native_evidence,
        purpose,
        responsive_voice,
        rtpc_alignment,
        runtime_observations,
        scene_backgrounds,
        table_contexts,
        build_contracts,
        voice_requests,
    )
    from animestudio_index_io import (
        ObjectIndexUnavailable,
        iter_published_objects,
        published_object_index_path,
    )
else:  # pragma: no cover - this file has exactly two supported identities.
    raise ImportError("import as scripts.build_audio_semantics or run the script directly")


MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 = build_contracts.MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256
CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256 = build_contracts.CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256
AUDIO_MUSIC_NATIVE_STATE_GROUPS = build_contracts.AUDIO_MUSIC_NATIVE_STATE_GROUPS

AUDIO_SEMANTIC_SCHEMA_VERSION = context_utils.AUDIO_SEMANTIC_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_METADATA_REL = Path("il2cpp_data/Metadata/global-metadata.dat")

CATEGORY_LABELS = {
    "sfx": "Sound effects",
    "music": "Background music",
    "cue": "Audio cues",
    "ambience": "Ambience",
    "ui": "UI",
    "voice": "Voice",
    "control": "Controls / haptics",
    "unknown": "Unclassified",
}

PROJECTILE_DATA_REL = Path("data/gameplay/projectiles.json")
PROJECTILE_SOUND_PHASES = {
    "launchSound": "launch",
    "loopSound": "loop",
    "reachSound": "reach",
    "hitSound": "hit",
    "blockSound": "block",
    "finishedSound": "finish",
    "sizzleSound": "proximitySizzle",
}
# HIRC type numbers follow the object-family layout observed in the current
# Endfield banks.  The event payload preserves the raw numeric type as the
# authoritative value; these names are presentation labels, not a claim that
# selection behavior was evaluated offline.
SELECTION_HIRC_TYPES = frozenset({5, 6, 12, 13})


# These are static managed-metadata surfaces for the string-key Timeline
# event carriers.  They describe the methods and serialized controls that can
# consume a clip; they do not claim that a Director evaluated the clip or that
# Wwise received a PostEvent.  Keep the full contract in the compact index
# coverage and attach only the stable id to each occurrence.


LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS = (
    {
        "id": "onAudioStateChanged",
        "semanticKind": "levelEventCondition",
        "relationType": "observesAudioStateTransition",
        "type": "Beyond.Gameplay.Actions.LevelEvent.OnAudioStateChanged",
        "unionTag": 0x0048,
        "unionTagHex": "0x0048",
        "eventKey": 148,
        "fields": ("_expectFromState", "_expectToState", "_fromStateMask", "_toStateMask"),
        "predicate": (
            "(from & fromMask) == (expectFrom & fromMask) && "
            "(to & toMask) == (expectTo & toMask)"
        ),
        "authoredOccurrenceCount": 0,
        "authoredOccurrenceStatus": "absentFromCurrentActiveLevelScriptOverlay",
        "runtimeExecutionStatus": "notObserved",
        "playbackRequestStatus": "notApplicableTriggerInput",
    },
    {
        "id": "onMusicBeatEvent",
        "semanticKind": "levelEventCondition",
        "relationType": "observesMusicCallbackMask",
        "type": "Beyond.Gameplay.Actions.LevelEvent.OnMusicBeatEvent",
        "unionTag": 0x007A,
        "unionTagHex": "0x007a",
        "eventKey": 44,
        "fields": ("_beatType",),
        "predicate": "(authoredCallbackMask & runtimeCallbackMask) != 0",
        "authoredOccurrenceCount": 0,
        "authoredOccurrenceStatus": "absentFromCurrentActiveLevelScriptOverlay",
        "runtimeExecutionStatus": "producerAndExecutionUnresolved",
        "playbackRequestStatus": "notApplicableTriggerInput",
    },
)

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
















# The enum member names below are not display guesses.  They are the managed
# names recovered from the current Gameplay.Beyond metadata and their value
# ids are the exact FNV-1/UTF-16 hashes used by AudioHashGenerator.Compute.
# Keeping the enum member, hash input, and id together makes the distinction
# between a state *group* and a state *value* explicit in the WebUI catalog.




# These are exact immediate values observed at current GameAssembly callsites.
# ManualSet* is intentionally separate: its EBX/EDX input is supplied by the
# caller at runtime, so the binary proves the route but not a fixed value.






# These ids are joined twice: first to the typed v150 type-6 selector tails in
# the shipped banks, then to exact current GameAssembly setter callsites.  A
# semantic role is deliberately not an authored Wwise group name.  The three
# inferred rows remain visibly weaker than the two exact runtime setter rows.
AUDIO_RUNTIME_SELECTOR_GROUPS = (
    {
        "groupId": 0x7ACDACAF,
        "groupIdHex": "0x7acdacaf",
        "groupType": "switch",
        "semanticRole": "factoryRemoteNodeMode",
        "semanticLabel": "Factory remote node mode",
        "semanticEvidence": "exactNativeSetterAndValueMapping",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeScope": "audioObject",
        "runtimeSetter": {
            "callerType": "Beyond.Gameplay.Audio.AudioRemoteFactoryBridge",
            "callerMethod": "UpdateNodeMode",
            "callerMethodIndex": 39714,
            "callerToken": "0x06009b23",
            "setSwitchCallVirtualAddress": "0x1850ffa6d",
            "setter": "Beyond.Audio.AudioAdapter.SetSwitch(uint,uint,ulong)",
            "audioObjectIdSource": {
                "method": "Beyond.Audio.AudioObject.get_audioObjectId",
                "methodIndex": 39038,
                "token": "0x0600987f",
                "virtualAddress": "0x1832d2360",
            },
        },
        "valueResolver": {
            "method": "GetAudioStateValueFromNodeMode",
            "methodIndex": 39759,
            "token": "0x06009b50",
            "virtualAddress": "0x186ae7b18",
        },
        "values": (
            # UpdateNodeMode receives the bit-valued NodeMode input, then
            # GetAudioStateValueFromNodeMode returns the Wwise value hash. The
            # mapping is literal in the current GameAssembly body; these are
            # not merely guessed FNV names. Keep both ids so the UI cannot
            # mistake the managed input for the Wwise branch value.
            {
                "valueId": 1,
                "valueIdHex": "0x00000001",
                "semanticName": "Normal",
                "resolvedValueId": 0x4527C498,
                "resolvedValueIdHex": "0x4527c498",
                "resolvedValueName": "normal",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 2,
                "valueIdHex": "0x00000002",
                "semanticName": "Liquid",
                "resolvedValueId": 0xF3A9ACD5,
                "resolvedValueIdHex": "0xf3a9acd5",
                "resolvedValueName": "liquid",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 4,
                "valueIdHex": "0x00000004",
                "semanticName": "Gas",
                "resolvedValueId": 0x228CF0D8,
                "resolvedValueIdHex": "0x228cf0d8",
                "resolvedValueName": "gas",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 8,
                "valueIdHex": "0x00000008",
                "semanticName": "GasLiquid",
                "resolvedValueId": 0xFB9CA5C8,
                "resolvedValueIdHex": "0xfb9ca5c8",
                "resolvedValueName": "gasliquid",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 16,
                "valueIdHex": "0x00000010",
                "semanticName": "GasTransition",
                "resolvedValueId": 0x59A68236,
                "resolvedValueIdHex": "0x59a68236",
                "resolvedValueName": "gastrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 32,
                "valueIdHex": "0x00000020",
                "semanticName": "LiquidTransition",
                "resolvedValueId": 0x2F715D31,
                "resolvedValueIdHex": "0x2f715d31",
                "resolvedValueName": "liquidtrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 64,
                "valueIdHex": "0x00000040",
                "semanticName": "SolidTransition",
                "resolvedValueId": 0x8353CA3C,
                "resolvedValueIdHex": "0x8353ca3c",
                "resolvedValueName": "solidtrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
        ),
        "valueResolverStatus": "exactAllSevenInputsMapToWwiseValueHashes",
        "valueResolverZeroResultStatus": "unknownOrZeroNodeModeReturnsZeroAndCallerSkipsSetSwitch",
        "runtimeObservationStatus": "staticSetterCallsiteExactLiveValueNotObserved",
    },
    {
        "groupId": 0xF6699CF4,
        "groupIdHex": "0xf6699cf4",
        "groupType": "state",
        "semanticRole": "gamepadMotionBackend",
        "semanticLabel": "Gamepad motion-output backend",
        "semanticEvidence": "exactNativeStateSetterCallsites",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeScope": "global",
        "runtimeSetter": {
            "callerType": "Beyond.Gameplay.Audio.AudioGamePadManager",
            "calls": (
                {
                    "method": "_TryAddXInputMotionOutput",
                    "setStateCallVirtualAddress": "0x186ad04e2",
                    "valueId": 0x1A9FC91F,
                    "semanticName": "XInput",
                },
                {
                    "method": "_TryRefreshScePadHandle",
                    "setStateCallVirtualAddress": "0x186ad069c",
                    "valueId": 0x1B9ABDB1,
                    "semanticName": "ScePad",
                },
            ),
            "setterHelperVirtualAddress": "0x183a0cb70",
            "setterMethodIndex": 446543,
            "setterToken": "0x06000ac9",
            "setterVirtualAddress": "0x183a0cbd0",
            "setter": "AkSoundEngine.SetState(uint,uint)",
        },
        "values": (
            {"valueId": 0x1A9FC91F, "valueIdHex": "0x1a9fc91f", "semanticName": "XInput", "semanticEvidence": "exactNativeCallConstant"},
            {"valueId": 0x1B9ABDB1, "valueIdHex": "0x1b9abdb1", "semanticName": "ScePad", "semanticEvidence": "exactNativeCallConstant"},
            {"valueId": 0x2CA33BDB, "valueIdHex": "0x2ca33bdb", "semanticNameStatus": "unresolved"},
            {"valueId": 0xE59CC828, "valueIdHex": "0xe59cc828", "semanticNameStatus": "unresolved"},
        ),
        "runtimeObservationStatus": "staticSetterCallsitesExactLiveBackendNotObserved",
    },
    {
        "groupId": 0x706B5267,
        "groupIdHex": "0x706b5267",
        "semanticRole": "voiceIdentitySelector",
        "semanticLabel": "Character / NPC voice identity selector",
        "semanticEvidence": "highConfidenceEventAndNpcWwiseIdCorrelation",
        "authoredGroupNameStatus": "unrecovered",
        "eventCount": 1601,
        "voiceEventCount": 1442,
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
    {
        "groupId": 0xDFF0BCCC,
        "groupIdHex": "0xdff0bccc",
        "semanticRole": "surfaceMaterialSelector",
        "semanticLabel": "Surface / material selector",
        "semanticEvidence": "highConfidenceHashedValueVocabularyCorrelation",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
    {
        "groupId": 0x3C9C2C56,
        "groupIdHex": "0x3c9c2c56",
        "semanticRole": "localRemoteRoutingSelector",
        "semanticLabel": "Local / remote audio routing selector",
        "semanticEvidence": "highConfidenceExactLocalRemoteValueHashMatches",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
)


def wwise_selector_group_catalog() -> tuple[dict[str, Any], ...]:
    """Return runtime selector rows plus exact music-state enum joins.

    The native selector rows above come from direct current-build setter or
    correlation evidence.  Music state groups are a separate exact metadata
    surface, but their hashes also occur in serialized v150 SetState actions
    and type-6 selector packages.  Publishing them in the same catalog lets
    both surfaces use the same conservative ID join without inventing Wwise
    authored names.
    """

    rows: list[dict[str, Any]] = [dict(row) for row in AUDIO_RUNTIME_SELECTOR_GROUPS]
    for raw in AUDIO_MUSIC_NATIVE_STATE_GROUPS:
        row = dict(raw)
        recovered_name = str(row.get("recoveredName") or "").strip()
        role = str(row.get("role") or "musicState")
        row.setdefault("groupType", "state")
        row["semanticRole"] = f"musicState:{role}"
        row["semanticLabel"] = (
            f"Music state / {recovered_name}"
            if recovered_name
            else f"Music state / {role}"
        )
        row["semanticEvidence"] = "exactCurrentMetadataEnumAndNativeSetter"
        row.setdefault(
            "authoredGroupNameStatus",
            "recoveredExactHash" if recovered_name else "unrecovered",
        )
        row.setdefault("runtimeScope", "global")
        row.setdefault(
            "runtimeObservationStatus",
            "staticSetterCallsitesExactLiveStateNotObserved",
        )
        values: list[dict[str, Any]] = []
        for raw_value in row.get("values") or ():
            value = dict(raw_value)
            member = str(value.get("member") or "").strip()
            if member and not value.get("semanticName"):
                value["semanticName"] = member
            value.setdefault(
                "semanticEvidence",
                value.get("resolution")
                or "exactCurrentMetadataEnumMemberFNV1Utf16Hash",
            )
            values.append(value)
        row["values"] = values
        rows.append(row)
    return tuple(rows)












normalize_posix = context_utils.normalize_posix
_append_context = context_utils.append_context
load_json = context_utils.load_json
json_dump = context_utils.json_dump


# The media catalog is fetched and parsed as a single JSON string by the WebUI
# audio view, and V8 caps strings at ~512MB, so a one-file catalog stops loading
# entirely once it outgrows that. Split it into shards of this many rows
# (~65MB each at current row sizes) and let the view concatenate them.
MEDIA_SHARD_ROWS = 8000


# Bulky per-media arrays that only the detail pane reads.  Together these are
# ~80% of the media catalog, so keeping them out of the list rows is what makes
# the media tab affordable to hold in a browser heap; the WebUI fetches them on
# demand from `media_details/` the same way it already does for events.




def prune_stale_detail_shards(root: Path, keep: Iterable[str]) -> None:
    """Delete detail shards under `root` that this run did not write."""
    if not root.is_dir():
        return
    kept = {PurePosixPath(name).name for name in keep}
    for path in root.glob("*.json"):
        if path.name not in kept:
            path.unlink()


def prune_stale_shards(root: Path, stem: str, keep: Iterable[str]) -> None:
    """Delete `<stem>.json` / `<stem>.NNN.json` files not in `keep`."""
    kept = {str(name) for name in keep}
    for path in [root / f"{stem}.json", *root.glob(f"{stem}.[0-9][0-9][0-9].json")]:
        if path.name not in kept and path.exists():
            path.unlink()






































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
    events: Iterable[dict[str, Any]], webui_root: Path, language: str
) -> dict[str, Any]:
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
        "status": "exactCurrentBuildStaticEvidence",
        "callback": "OnCustomFootStep",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "metadataSha256": MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256,
        "sourceFingerprint": fingerprint,
        "parameterMasks": {"footSide": "0x03", "vfxType": "0x1c", "playbackFilter": "0xe0"},
        "runtimeVfxWeightThreshold": (
            event_projection.CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD
        ),
        "nativeAnchors": [dict(anchor) for anchor in CUSTOM_FOOTSTEP_NATIVE_ANCHORS],
        "runtimeFieldAnchors": [
            {
                "type": "FootStepConfig",
                "field": "footstepAudioSwitch",
                "token": "0x04001386",
                "offset": "0x20",
                "meaning": "surface enum to AudioId",
            },
            {
                "type": "FootStepConfig",
                "field": "footstepAudioCustomTypeSwitch",
                "token": "0x04001387",
                "offset": "0x28",
                "meaning": "GameplayTag to AudioId",
            },
            {
                "type": "WaterInteractSettings",
                "field": "waterDepthRtpc",
                "token": "0x040053b5",
                "offset": "0x74",
                "meaning": "water-depth RTPC AudioId",
            },
        ],
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


def collect_projectile_contexts(webui_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Recover exact projectile lifecycle sound slots as uint32 Event contexts."""

    payload = load_json(webui_root / PROJECTILE_DATA_REL, {})
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        projectile_id = str(entry.get("id") or "")
        projectile_key = str(entry.get("key") or "")
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        template = entry.get("template") if isinstance(entry.get("template"), dict) else {}
        authored_skill_ids = sorted({
            str(skill_id)
            for field in (
                "activeSkillIds", "passiveSkillIds", "normalAttackIds",
                "normalAttackList", "enabledBreakingNormalAttacks",
                "enabledPassiveSkills",
            )
            for skill_id in template.get(field) or []
            if str(skill_id)
        })
        for field, phase in PROJECTILE_SOUND_PHASES.items():
            value = (entry.get("sounds") or {}).get(field)
            raw = value.get("value") if isinstance(value, dict) else value
            if not isinstance(raw, int) or not raw:
                continue
            event_hash = raw & 0xFFFFFFFF
            context = {
                "kind": "projectileSoundField",
                "confidence": "direct",
                "semanticRole": "authoredProjectileLifecycleSound",
                "projectileId": projectile_id,
                "projectileKey": projectile_key,
                "soundField": field,
                "triggerPhase": phase,
                "signedValue": raw,
                "eventHash": event_hash,
                "eventHex": f"0x{event_hash:08x}",
                "runtimeActivationStatus": "projectileLifecycleExecutionNotObserved",
                "sourceRoot": str(source.get("root") or ""),
                "sourcePathId": str(source.get("pathId") or ""),
                "sourceJsonPath": str(source.get("jsonPath") or ""),
                "sourceFile": str(source.get("sourceFile") or ""),
                "sourceOffset": source.get("sourceOffset"),
                "sourceVfsPath": str(source.get("vfsPath") or ""),
                "sourceFingerprint": str(source.get("rawDataSha256") or ""),
                "semanticPath": f"ProjectileComponentData.tail.structuredRemainingTail.postAlertEffectSoundTail.{field}",
            }
            if field == "sizzleSound":
                context["sizzleSoundTriggerDistance"] = (entry.get("sounds") or {}).get("sizzleSoundTriggerDistance")
                context["ringProjectileSoundSmoothFactor"] = (entry.get("sounds") or {}).get("ringProjectileSoundSmoothFactor")
            if authored_skill_ids:
                context["authoredSkillIds"] = authored_skill_ids[:16]
                context["skillOwnershipStatus"] = "projectileTemplateReferenceOnly"
            _append_context(contexts, seen, identifiers.event_hash_context_key(event_hash), context)
    return dict(contexts)


def collect_spawner_pre_warn_semantics(
    export_root: Path,
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact current SpawnerEnemyLibraryItem pre-warning Events."""
    if decoder is None:
        if __package__ == "scripts":
            from scripts.story_builder.spawner_binary import decode_spawner_enemy_library
        else:
            from story_builder.spawner_binary import decode_spawner_enemy_library
        decoder = decode_spawner_enemy_library

    spawner_root: Path | None = None
    source_root = ""
    for candidate_root in ("StreamingAssets", "Persistent"):
        candidate = export_root / "structured" / candidate_root / "Data/Json/SpawnerConfig"
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
        if __package__ == "scripts":
            from scripts.story_builder.level_bindings import decode_leveldata_npc_patrol_list
        else:
            from story_builder.level_bindings import decode_leveldata_npc_patrol_list
        decoder = decode_leveldata_npc_patrol_list

    leveldata_root: Path | None = None
    source_root = ""
    for candidate_root in ("Persistent", "StreamingAssets"):
        candidate = export_root / "structured" / candidate_root / "Data/Json/LevelData"
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
        if __package__ == "scripts":
            from scripts.story_builder.char_interact_perform_binary import (
                decode_char_interact_audio_actions,
            )
        else:
            from story_builder.char_interact_perform_binary import (
                decode_char_interact_audio_actions,
            )
        decoder = decode_char_interact_audio_actions

    roots = ("StreamingAssets", "Persistent")
    relative_versions: dict[str, list[tuple[str, Path, str]]] = defaultdict(list)
    for source_root in roots:
        root = (
            export_root / "structured" / source_root
            / "Data/Json/CharInteractPerformCfgs"
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

































# The two action records below are the only current-build LevelScript actions
# whose serialized ``_levelSeqId`` is a direct Timeline identity.  Keep this
# table deliberately small: a same-looking string in another union is not
# enough to promote an AudioEventPlayable to an authored trigger.
LEVELSEQUENCE_PLAY_ACTION_DEFINITIONS = {
    (0x0360, 0x0F): {
        "action": "PlayLevelSequence",
        "nativeMappingId": "PlayLevelSequenceAction.memberCount15",
        "serializedField": "_levelSeqId",
    },
    (0x0361, 0x12): {
        "action": "PlayLevelSequenceAndControlSceneObjects",
        "nativeMappingId": (
            "PlayLevelSequenceAndControlSceneObjectsAction.memberCount18"
        ),
        "serializedField": "_levelSeqId",
    },
}




def _active_levelscript_overlay(
    export_root: Path,
    *,
    levelscript_root: Path | None = None,
) -> dict[str, tuple[str, Path]]:
    """Return the active Persistent-over-Streaming LevelScript files."""

    if levelscript_root is not None:
        root = Path(levelscript_root)
        return {
            path.relative_to(root).as_posix(): ("fixture", path)
            for path in sorted(root.rglob("*.json"))
        }
    overlay: dict[str, tuple[str, Path]] = {}
    for source_root in ("StreamingAssets", "Persistent"):
        root = (
            export_root / "structured" / source_root / "Data" / "Json"
            / "LevelScriptData"
        )
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            overlay[path.relative_to(root).as_posix()] = (source_root, path)
    return overlay


def _levelsequence_fields_from_decoded_detail(detail: Any) -> list[dict[str, Any]]:
    """Extract the unique tagged levelseq field from a validated action payload."""

    if not isinstance(detail, dict):
        return []
    fields: list[dict[str, Any]] = []
    for field in detail.get("taggedFields") or []:
        if not isinstance(field, dict) or field.get("type") != "string":
            continue
        value = str(field.get("value") or "").strip()
        if value.startswith("levelseq_") and not any(
            row.get("value") == value for row in fields
        ):
            fields.append({
                "value": value,
                "offset": str(field.get("offset") or ""),
            })
    return fields if len(fields) == 1 else []


def _levelsequence_ids_from_decoded_detail(detail: Any) -> list[str]:
    """Compatibility helper returning only an unambiguous levelseq id."""

    return [str(row.get("value") or "") for row in _levelsequence_fields_from_decoded_detail(detail)]


def collect_levelsequence_play_actions(
    export_root: Path,
    *,
    levelscript_root: Path | None = None,
    decode_file: Any | None = None,
) -> dict[str, Any]:
    """Collect exact active-overlay PlayLevelSequence id records.

    The parser intentionally requires the current union tag/member count and
    a tagged ``levelseq_*`` string.  It does not claim that the action ran or
    that a Timeline Director eventually posted the Wwise Event.
    """

    if decode_file is None:
        if __package__ == "scripts":
            from scripts.story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_record_semantic_key,
            )
        else:
            from story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_record_semantic_key,
            )

        def decode_file(_path: Path, data: bytes) -> dict[str, Any]:
            records = extract_levelscript_uid_records(data)
            rows: list[dict[str, Any]] = []
            target_count = 0
            for index, record in enumerate(records):
                key = levelscript_record_semantic_key(record)
                definition = LEVELSEQUENCE_PLAY_ACTION_DEFINITIONS.get(key)
                if not definition:
                    continue
                target_count += 1
                member_count = int(record.get("serializedMemberCount") or 0)
                if member_count != key[1]:
                    continue
                next_start = (
                    int(records[index + 1].get("start") or 0)
                    if index + 1 < len(records)
                    else len(data)
                )
                try:
                    detail = decode_levelscript_record_payload(
                        data, record, next_start=next_start
                    )
                except (ValueError, IndexError, struct.error):
                    continue
                fields = _levelsequence_fields_from_decoded_detail(detail)
                for field in fields:
                    value = str(field.get("value") or "")
                    rows.append({
                        "record": record,
                        "recordIndex": index,
                        "definition": definition,
                        "levelSequenceId": value,
                        "levelSequenceFieldOffset": field.get("offset"),
                    })
            return {"targetCount": target_count, "rows": rows}

    actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    overlay = _active_levelscript_overlay(
        export_root, levelscript_root=levelscript_root
    )
    target_records = 0
    decoded_records = 0
    decode_failures = 0
    source_files_with_actions = 0
    for relative_path, (source_root, path) in sorted(overlay.items()):
        try:
            data = path.read_bytes()
            decoded = decode_file(path, data) or {}
        except (OSError, ValueError, struct.error):
            decode_failures += 1
            continue
        target_records += int(decoded.get("targetCount") or 0)
        rows = decoded.get("rows") or []
        if rows:
            source_files_with_actions += 1
        try:
            source_path = normalize_posix(path.relative_to(export_root))
        except ValueError:
            source_path = normalize_posix(path)
        source_sha256 = hashlib.sha256(data).hexdigest()
        levelscript_id = str(PurePosixPath(relative_path).with_suffix(""))
        for row in rows:
            if not isinstance(row, dict):
                continue
            sequence_id = str(row.get("levelSequenceId") or "").strip()
            definition = row.get("definition")
            record = row.get("record") if isinstance(row.get("record"), dict) else {}
            if not sequence_id or not isinstance(definition, dict):
                continue
            decoded_records += 1
            action = str(definition.get("action") or "")
            actions[sequence_id].append({
                "action": action,
                "levelSequenceId": sequence_id,
                "levelScriptId": levelscript_id,
                "sourceRoot": source_root,
                "sourcePath": source_path,
                "sourceSha256": source_sha256,
                "recordIndex": row.get("recordIndex"),
                "recordStart": int(record.get("start") or 0),
                "recordUid": str(record.get("uid") or ""),
                "recordLocalId": record.get("localId"),
                "unionTag": record.get("unionTag"),
                "serializedMemberCount": record.get("serializedMemberCount"),
                "nativeMappingId": str(definition.get("nativeMappingId") or ""),
                "serializedField": str(definition.get("serializedField") or "_levelSeqId"),
                "levelSequenceFieldOffset": str(row.get("levelSequenceFieldOffset") or ""),
                "evidence": "exactCurrentActiveLevelScriptMemoryPackLevelSeqId",
                "runtimeActivationStatus": "playLevelSequenceActionExecutionNotObserved",
            })
    for rows in actions.values():
        rows.sort(key=lambda row: (
            str(row.get("sourcePath") or ""),
            int(row.get("recordStart") or 0),
        ))
    return {
        "actionsByLevelSequenceId": dict(actions),
        "stats": {
            "sourceFiles": len(overlay),
            "sourceFilesWithPlayLevelSequenceActions": source_files_with_actions,
            "playLevelSequenceActionRecords": decoded_records,
            "playLevelSequenceTargetRecords": target_records,
            "uniquePlayLevelSequenceIds": len(actions),
            "decodeFailures": decode_failures,
        },
        "evidenceBoundary": (
            "Current active Persistent-over-Streaming LevelScript union tags and member counts, "
            "plus tagged levelseq_* strings, prove authored _levelSeqId records. They do not prove "
            "PlayLevelSequence execution, Director activation, or Wwise posting."
        ),
    }
































def build_levelsequence_audio_contexts(
    event_ids: Iterable[str],
    ownership: dict[str, Any],
    play_actions: dict[str, Any],
) -> dict[str, Any]:
    """Build bounded exact/inferred/gap context rows for target Events."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    occurrences_by_event = ownership.get("occurrencesByEvent") or {}
    actions_by_id = play_actions.get("actionsByLevelSequenceId") or {}
    stats = Counter()
    context_event_ids: set[str] = set()
    exact_action_event_ids: set[str] = set()
    inferred_trigger_event_ids: set[str] = set()
    target_ids = sorted({str(value or "").strip().lower() for value in event_ids if str(value or "").strip()})
    for event_id in target_ids:
        occurrences = [row for row in occurrences_by_event.get(event_id) or [] if isinstance(row, dict)]
        if not occurrences:
            _append_context(contexts, seen, event_id, {
                "kind": "levelSequenceAudio",
                "semanticRole": "timelineAudioOwnershipGap",
                "confidence": "gap",
                "ownershipEvidenceLevel": "gap",
                "triggerEvidenceLevel": "gap",
                "timelineOwnershipStatus": "timelineCarrierMissingFromCurrentObjectIndex",
                "triggerBindingStatus": "timelineCarrierMissingFromCurrentObjectIndex",
                "triggerRole": "PlayLevelSequence",
                "runtimeActivationStatus": "timelineAudioCarrierNotFound",
                "triggerRuntimeActivationStatuses": [
                    "timelineCarrierMissingFromCurrentObjectIndex",
                    "playLevelSequenceTriggerUnresolved",
                    "audioEventRuntimePlaybackUnobserved",
                ],
                "triggerRequestEvidence": [
                    "canonicalEventWithPossibleWwiseMedia",
                    "currentObjectIndexCarrierSearch",
                ],
                "triggerEvidenceKinds": ["levelSequenceAudioOwnershipGap"],
                "evidenceBoundary": "No AudioEventPlayable/Track carrier was found in the current object index; no Timeline or Director owner is claimed.",
            })
            stats["eventsWithoutTimelineCarrier"] += 1
            context_event_ids.add(event_id)
            continue
        for occurrence in occurrences:
            sequence_id = str(occurrence.get("timelineAssetNameBase") or "")
            action_rows = [row for row in actions_by_id.get(sequence_id) or [] if isinstance(row, dict)]
            director_rows = [row for row in occurrence.get("playableDirectors") or [] if isinstance(row, dict)]
            has_director = bool(director_rows)
            has_action = bool(action_rows)
            confidence = "exact" if has_director and has_action else "inferred"
            trigger_status = (
                "exactLevelSequenceIdJoin" if has_action
                else "timelineParentNotLevelSequence" if not sequence_id
                else "timelineDirectorPlaybackTriggerUnresolved"
            )
            ownership_status = (
                "exactTimelineDirectorOwner" if has_director
                else "exactTimelineOwnerDirectorUnresolved"
            )
            context = {
                "kind": "levelSequenceAudio",
                "semanticRole": "authoredTimelineAudioEvent",
                "confidence": confidence,
                "ownershipEvidenceLevel": "exactSerializedTimelineCarrier",
                "triggerEvidenceLevel": "exact" if has_action else "inferred",
                "timelineOwnershipStatus": ownership_status,
                "triggerBindingStatus": trigger_status,
                "triggerRole": "PlayLevelSequence" if sequence_id else "TimelineAssetPlayback",
                "runtimeActivationStatus": "playableDirectorRuntimeExecutionNotObserved",
                "triggerRuntimeActivationStatuses": [
                    "playLevelSequenceActionExecutionNotObserved" if has_action else (
                        "playLevelSequenceTriggerUnresolved" if sequence_id
                        else "timelineParentTriggerUnresolved"
                    ),
                    "playableDirectorRuntimeExecutionNotObserved" if has_director else "playableDirectorLinkUnresolved",
                    "audioEventRuntimePlaybackUnobserved",
                ],
                "triggerRequestEvidence": [
                    (
                        "exactDialogAudioEventPlayableAudioIdScalar"
                        if occurrence.get("audioPlayableKeyStatus") == "exactDialogAudioEventPlayableAudioIdScalar"
                        else "exactAudioEventPlayableScalar"
                        if occurrence.get("audioPlayableKeyStatus") == "exactAudioEventPlayableScalar"
                        else "exactTimelineTrackDisplayName"
                    ),
                    (
                        "exactTimelineDisplayNameHashEqualsSerializedAudioId"
                        if occurrence.get("authoredEventNameEvidence")
                        else "authoredEventNameNotRecovered"
                    ),
                    "exactTimelineTrackPPtr",
                    "exactTimelineParentPPtr",
                    "exactPlayableDirectorPlayableAssetPPtr" if has_director else "playableDirectorPPtrUnresolved",
                    "exactLevelScriptPlayLevelSequenceId" if has_action else (
                        "levelScriptPlayLevelSequenceIdUnresolved" if sequence_id
                        else "notALevelSequenceParent"
                    ),
                ],
                "triggerEvidenceKinds": [
                    "AudioEventPlayable",
                    "TimelineTrack",
                    "PlayableDirector" if has_director else "PlayableDirectorUnresolved",
                    "LevelScriptPlayLevelSequence" if has_action else (
                        "LevelScriptPlayLevelSequenceUnresolved" if sequence_id
                        else "NonLevelSequenceTimelineParent"
                    ),
                ],
                "levelSequenceId": sequence_id,
                "timelineParentNameStatus": occurrence.get("timelineParentNameStatus") or (
                    "exactLevelSequenceAudioSuffix" if sequence_id else "nonLevelSequenceTimelineParent"
                ),
                "levelScriptActionCount": len(action_rows),
                "levelScriptIds": sorted({
                    str(row.get("levelScriptId") or "")
                    for row in action_rows
                    if str(row.get("levelScriptId") or "")
                }),
                "levelScriptSourcePaths": sorted({
                    str(row.get("sourcePath") or "")
                    for row in action_rows
                    if str(row.get("sourcePath") or "")
                }),
                "levelSequenceFieldOffsets": sorted({
                    str(row.get("levelSequenceFieldOffset") or "")
                    for row in action_rows
                    if str(row.get("levelSequenceFieldOffset") or "")
                }),
                "levelScriptEvidence": action_rows,
                "timelineAssetName": occurrence.get("timelineAssetName"),
                "timelineAssetNameBase": sequence_id,
                "timelineAssetSerializedFile": occurrence.get("timelineAssetSerializedFile"),
                "timelineAssetPathId": occurrence.get("timelineAssetPathId"),
                "timelineAssetSource": occurrence.get("timelineAssetSource"),
                "timelineAssetSourceOffset": occurrence.get("timelineAssetSourceOffset"),
                "timelineTrackName": occurrence.get("timelineTrackName"),
                "timelineClipIndex": occurrence.get("timelineClipIndex"),
                "timelineTrackSerializedFile": occurrence.get("timelineTrackSerializedFile"),
                "timelineTrackPathId": occurrence.get("timelineTrackPathId"),
                "timelineTrackSource": occurrence.get("timelineTrackSource"),
                "timelineTrackSourceOffset": occurrence.get("timelineTrackSourceOffset"),
                "audioPlayableType": occurrence.get("audioPlayableType"),
                "audioPlayableRuntimeContractId": occurrence.get(
                    "audioPlayableRuntimeContractId"
                ),
                "audioPlayableKeyStatus": occurrence.get("audioPlayableKeyStatus"),
                "authoredEventName": occurrence.get("authoredEventName"),
                "authoredEventNameEvidence": occurrence.get("authoredEventNameEvidence"),
                "audioPlayableSerializedFile": occurrence.get("audioPlayableSerializedFile"),
                "audioPlayablePathId": occurrence.get("audioPlayablePathId"),
                "timelineClipDisplayName": occurrence.get("timelineClipDisplayName"),
                "timelineClipStartSec": occurrence.get("timelineClipStartSec"),
                "timelineClipDurationSec": occurrence.get("timelineClipDurationSec"),
                "timelineClipEndSec": occurrence.get("timelineClipEndSec"),
                "timelineClipInSec": occurrence.get("timelineClipInSec"),
                "timelineClipTimeScale": occurrence.get("timelineClipTimeScale"),
                "timelineClipEaseInDurationSec": occurrence.get("timelineClipEaseInDurationSec"),
                "timelineClipEaseOutDurationSec": occurrence.get("timelineClipEaseOutDurationSec"),
                "timelineClipBlendInDurationSec": occurrence.get("timelineClipBlendInDurationSec"),
                "timelineClipBlendOutDurationSec": occurrence.get("timelineClipBlendOutDurationSec"),
                "timelineClipOptionIndex": occurrence.get("timelineClipOptionIndex"),
                "timelineClipTimingEvidence": occurrence.get("timelineClipTimingEvidence"),
                "timelineTrackRawJsonPath": occurrence.get("timelineTrackRawJsonPath"),
                "audioPlayableIsCue": occurrence.get("audioPlayableIsCue"),
                "audioPlayableStopEventAtClipEnd": occurrence.get("audioPlayableStopEventAtClipEnd"),
                "audioPlayableStopEventAtClipEndKey": occurrence.get("audioPlayableStopEventAtClipEndKey"),
                "audioPlayableFadeOutMs": occurrence.get("audioPlayableFadeOutMs"),
                "audioPlayableEnableSeek": occurrence.get("audioPlayableEnableSeek"),
                "audioPlayableUseBindingObject": occurrence.get("audioPlayableUseBindingObject"),
                "audioPlayableIs2D": occurrence.get("audioPlayableIs2D"),
                "audioPlayableStopOnDisable": occurrence.get("audioPlayableStopOnDisable"),
                "audioMusicActionType": occurrence.get("audioMusicActionType"),
                "audioMusicActionTypeLabel": occurrence.get("audioMusicActionTypeLabel"),
                "audioMusicTriggerOnSkip": occurrence.get("audioMusicTriggerOnSkip"),
                "audioMusicTriggerOnSkipLabel": occurrence.get("audioMusicTriggerOnSkipLabel"),
                "audioPlayableControlEvidence": occurrence.get("audioPlayableControlEvidence"),
                "audioPlayableRawJsonPath": occurrence.get("audioPlayableRawJsonPath"),
                "playableDirectorCount": len(director_rows),
                "playableDirectorNames": [
                    str(row.get("playableDirectorName") or "")
                    for row in director_rows
                    if str(row.get("playableDirectorName") or "")
                ],
                "playableDirectorPathIds": [
                    row.get("playableDirectorPathId")
                    for row in director_rows
                    if row.get("playableDirectorPathId") is not None
                ],
                "directorEvidence": director_rows,
                "timelineEvidence": [
                    occurrence.get("evidence"),
                    occurrence.get("audioPlayableKeyStatus"),
                    occurrence.get("timelineClipTimingEvidence"),
                    occurrence.get("audioPlayableControlEvidence"),
                ],
                "evidence": "exactSerializedTimelineDirectorChain" if has_director else "exactSerializedTimelineCarrier",
                "evidenceBoundary": (
                    "Static Timeline/Director and LevelScript identity joins are exact, but runtime "
                    "action execution, Director activation, and Wwise playback are not observed."
                ),
            }
            _append_context(contexts, seen, event_id, context)
            stats["timelineContexts"] += 1
            context_event_ids.add(event_id)
            if has_action:
                exact_action_event_ids.add(event_id)
            else:
                inferred_trigger_event_ids.add(event_id)
            if has_director:
                stats["contextsWithPlayableDirector"] += 1
            else:
                stats["contextsWithoutPlayableDirector"] += 1
        if len(occurrences) > 1:
            stats["eventsWithMultipleTimelineOccurrences"] += 1
    stats["targetEvents"] = len(target_ids)
    stats["eventsWithTimelineContext"] = len(context_event_ids)
    stats["eventsWithExactLevelSequenceAction"] = len(exact_action_event_ids)
    stats["eventsWithInferredTimelineTrigger"] = len(inferred_trigger_event_ids)
    stats["eventsWithAnyTimelineCarrier"] = sum(bool(occurrences_by_event.get(event_id)) for event_id in target_ids)
    stats["eventsWithAnyContext"] = sum(bool(contexts.get(event_id)) for event_id in target_ids)
    return {
        "eventContexts": dict(contexts),
        "stats": dict(stats),
        "evidenceBoundary": (
            "Exact serialized Timeline ownership is separated from exact static LevelScript id joins. "
            "Rows without a carrier remain an explicit gap; inferred rows never claim runtime execution "
            "or selected Wwise media."
        ),
    }
















































































def merge_contexts(*sources: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        for event_id, rows in source.items():
            for row in rows:
                _append_context(merged, seen, event_id, row)
    return dict(merged)


def cutscene_contexts(cutscene_events: dict[str, list[str]] | None) -> dict[str, list[dict[str, Any]]]:
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for story_key, events in (cutscene_events or {}).items():
        for event_id in events:
            _append_context(contexts, seen, event_id, {
                "kind": "cutsceneTimeline",
                "storyKey": story_key,
                "evidence": "authoredTimelineOrLevelSequence",
            })
    return dict(contexts)


def lua_audio_contexts(audio_index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Expose exact decrypted Lua PostEvent literals without claiming execution."""
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for row in audio_index.get("luaAudioReferences") or []:
        if not isinstance(row, dict) or row.get("kind") != "luaPostEvent":
            continue
        event_id = str(row.get("name") or "").strip().lower()
        if not event_id:
            continue
        _append_context(contexts, seen, event_id, {
            "kind": "luaPostEvent",
            "source": row.get("source"),
            "line": row.get("line"),
            "expression": row.get("expression"),
            "method": row.get("method"),
            "eventHash": row.get("hash"),
            "evidence": "exactDecryptedLuaPostEventLiteral",
            "runtimeActivationStatus": "luaBranchExecutionNotObserved",
        })
    return dict(contexts)




def voice_table_event_contexts(
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Expose typed voice Event fields without claiming a live selection."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    kind_by_route = {
        "voiceDefaultEvent": "voiceDefaultWwiseEvent",
        "narratingChannelEvent": "voiceNarratingChannelEvent",
        "radioChannelEvent": "voiceRadioChannelEvent",
        "voiceDefinitionOverrideEvent": "audioDialogOverrideWwiseEvent",
        "responsiveVoiceEventTemplate": "responsiveVoiceEventTemplate",
    }
    for alias in audio_index.get("voiceTableWwiseEventAliases") or []:
        if not isinstance(alias, dict):
            continue
        event_id = str(alias.get("name") or "").strip().lower()
        if not event_id:
            continue
        for usage in alias.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            route_kind = str(usage.get("routeKind") or "")
            _append_context(contexts, seen, event_id, {
                "kind": kind_by_route.get(route_kind, "voiceTableWwiseEvent"),
                "table": usage.get("table"),
                "field": usage.get("field"),
                "routeKind": route_kind,
                "eventHash": alias.get("eventHash"),
                "eventHashHex": alias.get("eventHashHex"),
                "occurrenceCount": int(usage.get("occurrenceCount") or 0),
                "rowPathSamples": usage.get("rowPathSamples") or [],
                "rowPathsTruncated": bool(usage.get("rowPathsTruncated")),
                "sources": usage.get("sources") or [],
                "evidence": alias.get("evidence") or "typedVoiceTableEventFieldHashEqualsCurrentWwiseEventId",
                "runtimeRoute": usage.get("runtimeRoute"),
                "runtimeSelectionStatus": "authoredRoutePresentLiveVoiceAndBranchSelectionUnobserved",
                "playbackPlacementStatus": "authoredPossibleTrigger",
            })
    return dict(contexts)


def typed_ui_table_event_contexts(
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Expose exact table-to-Lua audio routes without claiming execution."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    kind_by_route = {
        "uiAnimationOpenEvent": "uiAnimationOpenEvent",
        "activityPushPopupBgmEvent": "activityPushPopupBgmEvent",
        "activityCenterBgmEvent": "activityCenterBgmEvent",
        "uiVideoAudioEvent": "uiVideoAudioEvent",
        "domainRegionSwitchEvent": "domainRegionSwitchEvent",
        "domainUpgradeAnimationEvent": "domainUpgradeAnimationEvent",
    }
    for alias in audio_index.get("typedUiTableWwiseEventAliases") or []:
        if not isinstance(alias, dict):
            continue
        event_id = str(alias.get("name") or "").strip().lower()
        if not event_id:
            continue
        for usage in alias.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            route_kind = str(usage.get("routeKind") or "")
            _append_context(contexts, seen, event_id, {
                "kind": kind_by_route.get(route_kind, "typedUiTableWwiseEvent"),
                "table": usage.get("table"),
                "field": usage.get("field"),
                "routeKind": route_kind,
                "eventHash": alias.get("eventHash"),
                "eventHashHex": alias.get("eventHashHex"),
                "occurrenceCount": int(usage.get("occurrenceCount") or 0),
                "rowPathSamples": usage.get("rowPathSamples") or [],
                "rowPathsTruncated": bool(usage.get("rowPathsTruncated")),
                "sources": usage.get("sources") or [],
                "consumerEvidence": usage.get("consumerEvidence") or [],
                "evidence": alias.get("evidence") or "typedTableGetterAndLuaAudioConsumerHashEqualsCurrentWwiseEventId",
                "runtimeRoute": usage.get("runtimeRoute"),
                "runtimeExecutionStatus": "authoredLuaAudioCallsiteBranchExecutionUnobserved",
                "playbackPlacementStatus": "authoredPossibleTrigger",
            })
    return dict(contexts)


def sns_voice_event_contexts(
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Expose exact SNS Voice-node click playback without claiming a click."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for alias in audio_index.get("snsVoiceWwiseEventAliases") or []:
        if not isinstance(alias, dict):
            continue
        event_id = str(alias.get("name") or "").strip().lower()
        if not event_id:
            continue
        for usage in alias.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            _append_context(contexts, seen, event_id, {
                "kind": "snsVoiceMessageEvent",
                "table": usage.get("table"),
                "dialogId": usage.get("dialogId"),
                "contentId": usage.get("contentId"),
                "contentType": usage.get("contentType"),
                "contentTypeName": usage.get("contentTypeName"),
                "contentParamIndex": usage.get("contentParamIndex"),
                "speaker": usage.get("speaker"),
                "durationSeconds": usage.get("durationSeconds"),
                "eventHash": alias.get("eventHash"),
                "eventHashHex": alias.get("eventHashHex"),
                "sources": usage.get("sources") or [],
                "consumerEvidence": [
                    "SNSDialogContentCoreCell.lua:13-23,216-220",
                    "SNSContentVoice.lua:48-76",
                ],
                "evidence": alias.get("evidence") or "snsVoiceContentTypeAndLuaPostEventHashEqualsCurrentWwiseEventId",
                "runtimeRoute": "SNS Voice cell click -> contentParam[0] -> AudioAdapter.PostEvent; timer/disable -> StopByPlayingId",
                "runtimeExecutionStatus": "authoredClickHandlerExecutionUnobserved",
                "playbackPlacementStatus": "authoredPossibleTrigger",
            })
    return dict(contexts)


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
        export_root / "structured" / "Persistent" / "Data" / "Json"
        / "SkillData"
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










def collect_webui_cutscene_events(webui_root: Path, language: str) -> dict[str, list[str]]:
    """Reuse authored cutscene event lists already published by Story builds."""

    out: dict[str, list[str]] = {}
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    for path in sorted(conv_root.glob("*.json")):
        payload = load_json(path, {})
        cutscene = payload.get("cutscene") if isinstance(payload, dict) else None
        if not isinstance(cutscene, dict):
            continue
        events = [
            str(value or "").strip()
            for value in cutscene.get("audioEvents") or []
            if str(value or "").strip()
        ]
        if events:
            out[str(payload.get("key") or path.stem)] = events
    return out


def merge_cutscene_event_maps(
    *sources: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    """Merge authored cutscene evidence without losing source-only placements."""

    out: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        if not isinstance(source, dict):
            continue
        for story_key, values in source.items():
            key = str(story_key or "").strip()
            if not key or not isinstance(values, list):
                continue
            for value in values:
                event_id = str(value or "").strip()
                marker = event_id.lower()
                if not marker or marker in seen[key]:
                    continue
                seen[key].add(marker)
                out.setdefault(key, []).append(event_id)
    return out


def managed_literal_contexts(
    metadata_path: Path | None,
    *,
    native_context: native_evidence.NativeAudioEvidence,
    current_wwise_event_hashes: set[int] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    names = [
        name for name in identifiers.collect_metadata_audio_literals(metadata_path)
        if not identifiers.is_rtpc_parameter_name(name)
    ]
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    callsite_contexts: dict[str, dict[str, Any]] = {}
    metadata_fingerprint = native_context.metadata_sha256
    gameassembly_fingerprint = native_context.gameassembly_sha256
    if native_context.validated:
        callsite_contexts = managed_literals.MANAGED_AUDIO_CALLSITE_CONTEXTS
    for name in names:
        event_hash = identifiers.audio_hash_generator_compute(name)
        if (
            current_wwise_event_hashes is not None
            and event_hash not in current_wwise_event_hashes
        ):
            continue
        callsite = callsite_contexts.get(name.lower())
        context = {
            "kind": "binaryManagedLiteralCallsite" if callsite else "binaryManagedLiteral",
            "literal": name,
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
            "evidence": (
                "exactManagedStringLiteralCurrentWwiseEventHashAndNativePlaybackCallsite"
                if callsite else "exactManagedStringLiteralAndCurrentWwiseEventHash"
            ),
            "playbackPlacementStatus": (
                "exactManagedNativePlaybackCallsite"
                if callsite else "identityOnlyManagedStringLiteral"
            ),
            "runtimeConsumerStatus": (
                "exactCurrentBuildNativeConsumer"
                if callsite else "consumerCallsiteUnresolved"
            ),
        }
        if callsite:
            context.update(callsite)
            context.update({
                "metadataSha256": metadata_fingerprint,
                "gameAssemblySha256": gameassembly_fingerprint,
                "runtimeExecutionStatus": "runtimeBranchExecutionUnobserved",
            })
        _append_context(contexts, seen, name, context)
    return dict(contexts), names




























def _compact_levelscript_control_rows(rows: Any) -> list[dict[str, Any]]:
    """Keep lifecycle detail lazy; retain only bounded control-row fields."""
    output: list[dict[str, Any]] = []
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        output.append({
            key: value
            for key, value in row.items()
            if key != "levelScriptAudioLifecycle"
        })
    return output


def build_audio_semantic_data(
    audio_index: dict[str, Any],
    *,
    language: str,
    export_root: Path,
    webui_root: Path,
    metadata_path: Path | None = None,
    gameassembly_path: Path | None = None,
    cutscene_events: dict[str, list[str]] | None = None,
    runtime_trace_bundle: Path | None = None,
) -> dict[str, Any]:
    language = language.upper()
    native_context = native_evidence.validate_native_audio_evidence(
        metadata_path,
        gameassembly_path,
    )
    # Several legacy projections read the broad HIRC summary with ``.get``.
    # Keep their working view bounded when an older/corrupt index has a
    # malformed summary, while retaining the original for the strict RTPC
    # validator and fail-closed publication below.
    alignment_audio_index = audio_index
    if not isinstance(audio_index, dict):
        audio_index = {}
    else:
        raw_hirc_summary = audio_index.get("hircSummary")
        if not isinstance(raw_hirc_summary, dict):
            audio_index = dict(audio_index)
            audio_index["hircSummary"] = {}
        elif not isinstance(raw_hirc_summary.get("postProcessSummary"), dict):
            audio_index = dict(audio_index)
            safe_hirc_summary = dict(raw_hirc_summary)
            safe_hirc_summary["postProcessSummary"] = {}
            audio_index["hircSummary"] = safe_hirc_summary
    if cutscene_events is None:
        cached_cutscene_events = audio_index.get("cutsceneAudioEvents")
        # The persisted map is the exact binary placement evidence. Published
        # Story cards are only a compatibility fallback for older indexes;
        # merging them would re-add line-bound audio whose purpose is already
        # known and multiply generic timeline contexts across aliases.
        cutscene_events = (
            merge_cutscene_event_maps(cached_cutscene_events)
            if isinstance(cached_cutscene_events, dict) and cached_cutscene_events
            else collect_webui_cutscene_events(webui_root, language)
        )
    runtime_model = build_runtime_model(metadata_path, export_root)
    current_wwise_event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in audio_index.get("wwiseEventInventory") or []
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    try:
        scene_background_semantics = scene_backgrounds.collect_scene_background_semantics(
            export_root,
            audio_index,
        )
    except scene_backgrounds.SceneBackgroundError as exc:
        scene_background_semantics = {
            "schemaVersion": scene_backgrounds.SCHEMA_VERSION,
            "status": "unavailable",
            "error": str(exc),
            "sources": [],
            "counts": {},
            "scenes": [],
            "unresolvedSceneDefinitions": [],
            "audioMaps": [],
            "sceneEmitters": [],
            "eventContexts": {},
            "evidenceBoundary": (
                "Scene background semantics were withheld because the published "
                f"AnimeStudio object-index gate failed: {exc}"
            ),
        }
    metadata_event_symbol_catalog = collect_metadata_event_symbol_aliases(
        metadata_path,
        current_wwise_event_hashes,
    )
    mono_behaviour_audio_id_semantics = collect_mono_behaviour_audio_id_contexts(
        export_root,
        current_wwise_event_hashes,
    )
    literal_context_index, managed_literal_names = managed_literals.collect_contexts(
        metadata_path,
        native_context=native_context,
        current_wwise_event_hashes=current_wwise_event_hashes,
    )
    cue_semantics = table_contexts.collect_audio_cue_semantics(
        export_root,
        native_context=native_context,
    )
    global_controls = table_contexts.collect_audio_global_control_semantics(
        export_root, cue_semantics
    )
    spawner_semantics = collect_spawner_pre_warn_semantics(export_root)
    patrol_semantics = collect_patrol_sub_action_audio_semantics(export_root)
    char_interact_semantics = collect_char_interact_audio_semantics(export_root)
    physics_audio_semantics = authored_components.collect_physics_audio_semantics(
        export_root
    )
    model_view_semantics = authored_components.collect_model_view_state_audio_semantics(
        export_root
    )
    # Metadata-derived RTPC names are native/static facts.  Keep them behind
    # the same explicit selected metadata + GameAssembly gate as the static
    # six-field alignment; serialized table controls remain available when the
    # gate is unavailable.
    managed_rtpc_parameters = [{
        "kind": "rtpcParameter",
        "parameterName": name,
        "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
        "evidence": "exactManagedStringLiteral",
        "evidenceClass": "authoredStatic",
        "wwiseEventStatus": "notApplicable",
    } for name in (
        identifiers.collect_metadata_audio_literals(metadata_path)
        if native_context.validated and native_context.gate_verified
        else []
    ) if identifiers.is_rtpc_parameter_name(name)]
    rtpc_names_by_hex: dict[str, str] = {}
    rtpc_name_collisions: set[str] = set()
    for row in managed_rtpc_parameters:
        parameter_name = str(row.get("parameterName") or "").strip()
        if not parameter_name:
            continue
        parameter_hex = f"0x{identifiers.audio_hash_generator_compute(parameter_name):08x}"
        previous = rtpc_names_by_hex.get(parameter_hex)
        if previous and previous.casefold() != parameter_name.casefold():
            rtpc_name_collisions.add(parameter_hex)
        else:
            rtpc_names_by_hex[parameter_hex] = parameter_name
    for parameter_hex in rtpc_name_collisions:
        rtpc_names_by_hex.pop(parameter_hex, None)
    levelscript_semantics = collect_levelscript_audio_semantics(
        export_root,
        cue_semantics=cue_semantics,
    )
    responsive_voice_contexts = responsive_voice.collect_responsive_voice_contexts(
        export_root,
        audio_index,
        native_context=native_context,
    )
    ability_voice_trigger_contexts = collect_ability_voice_trigger_contexts(
        export_root,
        audio_index,
    )
    native_voice_trigger_contexts = voice_requests.collect_native_voice_trigger_contexts(
        audio_index,
        native_context,
    )
    animation_voice_trigger_contexts = voice_requests.collect_animation_voice_trigger_contexts(
        export_root,
        audio_index,
        native_context,
    )
    voice_table_contexts = voice_table_event_contexts(audio_index)
    typed_ui_table_contexts = typed_ui_table_event_contexts(audio_index)
    sns_voice_contexts = sns_voice_event_contexts(audio_index)
    base_contexts = merge_contexts(
        collect_gameplay_contexts(webui_root, language),
        collect_projectile_contexts(webui_root),
        spawner_semantics.get("eventContexts") or {},
        patrol_semantics.get("eventContexts") or {},
        char_interact_semantics.get("eventContexts") or {},
        physics_audio_semantics.get("eventContexts") or {},
        model_view_semantics.get("eventContexts") or {},
        scene_background_semantics.get("eventContexts") or {},
        mono_behaviour_audio_id_semantics.get("eventContexts") or {},
        levelscript_semantics.get("eventContexts") or {},
        table_contexts.collect_table_contexts(
            export_root,
            runtime_model,
            cue_semantics=cue_semantics,
            global_controls=global_controls,
        ),
        cutscene_contexts(cutscene_events),
        lua_audio_contexts(audio_index),
        literal_context_index,
        responsive_voice_contexts,
        ability_voice_trigger_contexts,
        native_voice_trigger_contexts,
        animation_voice_trigger_contexts,
        voice_table_contexts,
        typed_ui_table_contexts,
        sns_voice_contexts,
    )
    candidate_counts: Counter[str] = Counter()
    candidate_hash_contexts: dict[str, set[str]] = defaultdict(set)
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        event_id = str(entry.get("eventId") or entry.get("id") or "").strip().lower()
        if event_id:
            candidate_counts[event_id] += 1
            try:
                event_hash = int(entry.get("eventHash")) & 0xFFFFFFFF
            except (TypeError, ValueError):
                event_hash = None
            if event_hash is not None:
                candidate_hash_contexts[event_id].add(identifiers.event_hash_context_key(event_hash))
    timeline_target_event_ids = {
        event_id for event_id, count in candidate_counts.items()
        if count > 0
        and event_id not in base_contexts
        and not any(key in base_contexts for key in candidate_hash_contexts.get(event_id, set()))
    }
    levelsequence_play_actions = collect_levelsequence_play_actions(export_root)
    timeline_ownership_parts: list[dict[str, Any]] = []
    object_index_root = export_root / "recovered" / "AnimeStudio-cli"
    streaming_mono_index = (
        object_index_root / "StreamingAssets" / "object_index" / "parts"
        / "StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl"
    )
    streaming_director_index = (
        object_index_root / "StreamingAssets" / "object_index" / "parts"
        / "StreamingAssets_animestudio_json_by_type_PlayableDirector.jsonl"
    )
    if streaming_mono_index.is_file():
        timeline_ownership_parts.append(collect_timeline_audio_ownership(
            export_root,
            event_ids=timeline_target_event_ids,
            mono_path=streaming_mono_index,
            director_path=streaming_director_index,
        ))
    persistent_mono_index = (
        object_index_root / "Persistent" / "object_index" / "parts"
        / "Persistent_animestudio_json_by_type_MonoBehaviour.jsonl"
    )
    persistent_director_index = (
        object_index_root / "Persistent" / "object_index" / "parts"
        / "Persistent_animestudio_json_by_type_PlayableDirector.jsonl"
    )
    if persistent_mono_index.is_file():
        # Persistent carries the story Timeline assets that are absent from
        # the StreamingAssets-only semantic pass.  Scan all authored Event
        # keys so a key missing from the current Wwise index remains visible
        # as an explicit authored request rather than disappearing.
        timeline_ownership_parts.append(collect_timeline_audio_ownership(
            export_root,
            event_ids=None,
            mono_path=persistent_mono_index,
            director_path=persistent_director_index,
        ))
    if timeline_ownership_parts:
        timeline_ownership = merge_timeline_audio_ownership(timeline_ownership_parts)
        timeline_ownership = enrich_timeline_audio_ownership_from_raw_json(
            export_root,
            timeline_ownership,
        )
        timeline_ownership["objectIndexSources"] = [
            source
            for source, path in (
                ("StreamingAssets", streaming_mono_index),
                ("Persistent", persistent_mono_index),
            )
            if path.is_file()
        ]
    else:
        timeline_ownership = collect_timeline_audio_ownership(
            export_root,
            event_ids=timeline_target_event_ids,
        )
    timeline_context_event_ids = timeline_target_event_ids | {
        str(event_id or "").strip().lower()
        for event_id in (timeline_ownership.get("occurrencesByEvent") or {})
        if str(event_id or "").strip()
    }
    timeline_cue_semantics = build_timeline_audio_cue_contexts(
        timeline_ownership,
        cue_semantics,
    )
    levelsequence_semantics = build_levelsequence_audio_contexts(
        timeline_context_event_ids,
        timeline_ownership,
        levelsequence_play_actions,
    )
    contexts = merge_contexts(
        base_contexts,
        levelsequence_semantics.get("eventContexts") or {},
        timeline_cue_semantics.get("eventContexts") or {},
    )
    context_kind_counts = Counter(
        str(context.get("kind") or "unknown")
        for rows in contexts.values()
        for context in rows
        if isinstance(context, dict)
    )
    context_kind_event_counts = Counter(
        kind
        for rows in contexts.values()
        for kind in {
            str(context.get("kind") or "unknown")
            for context in rows
            if isinstance(context, dict)
        }
    )
    wwise_selector_groups = wwise_selector_group_catalog()
    events, media_to_events, banks = event_projection.build_event_rows(
        audio_index,
        contexts,
        selector_groups=wwise_selector_groups,
        rtpc_names_by_hex=rtpc_names_by_hex,
        metadata_event_symbols=metadata_event_symbol_catalog.get("entries") or [],
    )
    # Scene-global attribution is a compact projection of the already merged
    # scene catalog and Event contexts.  The domain helper owns the exact
    # producer/scene gates; this entrypoint only wires collected data through.
    for event in events:
        event.update(scene_backgrounds.project_scene_global_compact_attribution(
            event.get("contexts") or [],
            scene_background_semantics,
            contexts_truncated=event.get("contextsTruncated") is not False,
        ))
        event.update(scene_backgrounds.project_scene_emitter_compact_attribution(
            event.get("contexts") or [],
            scene_background_semantics,
            scene_background_semantics.get("streamingInstanceCatalog"),
        ))
    # Full AudioCue ASTs are detail-only.  Event list rows remain compact;
    # ``event_summary`` intentionally does not project this payload.
    for event in events:
        cue_detail = table_contexts.audio_cue_expression_detail_for_contexts(
            event.get("contexts") or [], cue_semantics
        )
        if cue_detail:
            event["audioCueExpressionDetail"] = cue_detail
    character_audio_catalog = (
        media_ownership.collect_character_audio_identity_catalog(export_root)
    )
    animation_action_ownership = (
        media_ownership.annotate_event_animation_action_identity(events)
    )
    animation_callback_ownership = (
        media_ownership.annotate_event_animation_callback_links(
            events, export_root=export_root
        )
    )
    character_audio_ownership = (
        media_ownership.annotate_event_character_audio_identity(
            events,
            character_audio_catalog,
        )
    )
    action_control_evidence_by_event = {
        str(event.get("id") or ""): list(event.get("evidence") or [])
        for event in events
        if str(event.get("id") or "")
    }
    wwise_action_control_catalog = event_projection.annotate_wwise_action_control_evidence(
        action_control_evidence_by_event,
        wwise_selector_groups,
        rtpc_names_by_hex,
    )
    wwise_initial_rtpc_catalog = event_projection.build_initial_rtpc_parameter_catalog(
        events
    )
    shared_play_target_event_count = purpose.annotate_shared_wwise_play_targets(events)
    shared_media_leaf_event_count = purpose.annotate_shared_wwise_media_leaves(events)
    shared_media_leaf_category_event_count = sum(
        row.get("categoryEvidence") == "exactCompleteWwiseMediaLeafSetCategory"
        for row in events
    )
    authored_name_category_event_count = sum(
        bool(row.get("categoryNameEvidence"))
        for row in events
    )
    media = build_media_rows(
        audio_index,
        media_to_events,
        {
            str(event.get("id") or ""): str(event.get("category") or "unknown")
            for event in events
            if event.get("id")
        },
        event_rows=events,
    )
    runtime_observation_projection = (
        runtime_observations.apply_verified_runtime_observations(
            events,
            media,
            runtime_trace_bundle,
            expected_language=language,
        )
    )
    character_namespace_gameplay = (
        media_ownership.project_character_namespace_gameplay_audio(events)
    )
    static_rtpc_alignment = rtpc_alignment.build_static_rtpc_alignment(
        alignment_audio_index,
        events,
        media,
        native_context=native_context,
    )
    radio_catalog = attach_levelscript_radio_contexts(
        media,
        export_root,
        levelscript_semantics,
    )
    trigger_context_catalog = build_trigger_context_catalog(
        events,
        media,
        webui_root,
        language,
        export_root=export_root,
        levelscript_semantics=levelscript_semantics,
        mono_behaviour_audio_id_contexts=(
            mono_behaviour_audio_id_semantics.get("eventContexts") or {}
        ),
        model_view_semantics=model_view_semantics,
        native_context=native_context,
    )
    media_trigger_context_counts = annotate_media_trigger_contexts(
        media,
        trigger_context_catalog,
    )
    media_trigger_semantic_category_counts = annotate_media_trigger_semantic_categories(
        media,
        trigger_context_catalog,
    )
    media_post_process_counts = {
        "mediaWithPostProcessDirectEffects": sum(
            bool(row.get("postProcessDirectEffectCount"))
            for row in media
        ),
        "mediaPostProcessDirectEffectOccurrences": sum(
            int(row.get("postProcessDirectEffectOccurrences") or 0)
            for row in media
        ),
        "mediaWithPostProcessRtpcControls": sum(
            bool(row.get("postProcessRtpcControlCount"))
            for row in media
        ),
        "mediaPostProcessRtpcControlCount": sum(
            int(row.get("postProcessRtpcControlCount") or 0)
            for row in media
        ),
        "mediaWithPostProcessStateControls": sum(
            bool(row.get("postProcessStateControlCount"))
            for row in media
        ),
        "mediaPostProcessStateControlCount": sum(
            int(row.get("postProcessStateControlCount") or 0)
            for row in media
        ),
        "mediaWithPostProcessEffectChain": sum(
            bool(row.get("postProcessEffectChainCount"))
            for row in media
        ),
        "mediaPostProcessEffectChainCount": sum(
            int(row.get("postProcessEffectChainCount") or 0)
            for row in media
        ),
        "mediaWithPostProcessBusControls": sum(
            bool(row.get("postProcessBusControlCount"))
            for row in media
        ),
        "mediaPostProcessBusControlCount": sum(
            int(row.get("postProcessBusControlCount") or 0)
            for row in media
        ),
        "mediaPostProcessBusRtpcCurveCount": sum(
            int(control.get("rtpcCurveCount") or 0)
            for row in media
            for control in row.get("postProcessBusControls") or ()
            if isinstance(control, dict)
        ),
        "mediaPostProcessBusStateValueCount": sum(
            int(control.get("stateValueCount") or 0)
            for row in media
            for control in row.get("postProcessBusControls") or ()
            if isinstance(control, dict)
        ),
        "mediaWithPostProcessBusDucking": sum(
            bool(row.get("postProcessBusDuckCount"))
            for row in media
        ),
        "mediaPostProcessBusDuckBusCount": sum(
            int(row.get("postProcessBusDuckCount") or 0)
            for row in media
        ),
        "mediaPostProcessBusDuckReferenceCount": sum(
            int(duck.get("duckCount") or 0)
            for row in media
            for duck in row.get("postProcessBusDucks") or ()
            if isinstance(duck, dict)
        ),
        "mediaWithPostProcessAuxSends": sum(
            bool(row.get("postProcessAuxSendCount"))
            for row in media
        ),
        "mediaPostProcessAuxSendCount": sum(
            int(row.get("postProcessAuxSendCount") or 0)
            for row in media
        ),
        "mediaPostProcessAuxSendOccurrences": sum(
            int(row.get("postProcessAuxSendOccurrences") or 0)
            for row in media
        ),
        "mediaWithPostProcessProperties": sum(
            bool(row.get("postProcessPropertyCount"))
            for row in media
        ),
        "mediaPostProcessPropertyCount": sum(
            int(row.get("postProcessPropertyCount") or 0)
            for row in media
        ),
        "mediaPostProcessPropertyOccurrences": sum(
            int(row.get("postProcessPropertyOccurrences") or 0)
            for row in media
        ),
        "mediaWithPostProcessRanges": sum(
            bool(row.get("postProcessRangeCount"))
            for row in media
        ),
        "mediaPostProcessRangeCount": sum(
            int(row.get("postProcessRangeCount") or 0)
            for row in media
        ),
        "mediaPostProcessRangeOccurrences": sum(
            int(row.get("postProcessRangeOccurrences") or 0)
            for row in media
        ),
        "mediaWithWwiseMediaGraphEvidence": sum(
            bool(row.get("wwiseMediaGraphEvidence"))
            for row in media
        ),
        "mediaWwiseMediaSelectionPathCount": sum(
            int(row.get("wwiseMediaSelectionPathCount") or 0)
            for row in media
        ),
        "mediaWithEventContextSummary": sum(
            bool(row.get("eventContextSummaryEvidence"))
            for row in media
        ),
        "mediaEventContextSummaryCount": sum(
            int(row.get("eventContextCount") or 0)
            for row in media
        ),
    }
    media_playback_location_counts = purpose.annotate_media_playback_locations(
        media,
        events,
    )
    media_coarse_ownership = media_ownership.annotate_media_coarse_ownership(
        media,
        scene_background_semantics,
        event_rows=events,
    )
    ai_bark_catalog = responsive_voice.build_ai_bark_catalog(
        export_root,
        audio_index,
        media,
        native_context=native_context,
    )
    custom_footstep_model = build_custom_footstep_model(events, webui_root, language)
    spawner_event_rows = [
        row for row in events
        if any(
            isinstance(context, dict) and context.get("kind") == "spawnerPreWarnAudio"
            for context in row.get("contexts") or []
        )
    ]
    patrol_event_rows = [
        row for row in events
        if any(
            isinstance(context, dict) and context.get("kind") == "patrolSubActionPlayAudio"
            for context in row.get("contexts") or []
        )
    ]
    char_interact_event_rows = [
        row for row in events
        if any(
            isinstance(context, dict) and context.get("kind") == "charInteractAudioEvent"
            for context in row.get("contexts") or []
        )
    ]
    physics_audio_event_rows = [
        row for row in events
        if any(
            isinstance(context, dict) and context.get("kind") == "physicsAudioComponentEvent"
            for context in row.get("contexts") or []
        )
    ]
    model_view_event_rows = [
        row for row in events
        if any(
            isinstance(context, dict)
            and context.get("kind") in {
                "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent"
            }
            for context in row.get("contexts") or []
        )
    ]

    named_event_ids = {
        str(value or "").strip().lower()
        for value in audio_index.get("eventNames") or []
        if str(value or "").strip()
    }
    event_categories = Counter(str(row.get("category") or "unknown") for row in events)
    media_categories = Counter(str(row.get("audioCategory") or "unknown") for row in media)
    media_semantic_categories = Counter(
        str(row.get("semanticCategory") or "unknown") for row in media
    )
    media_relations = Counter(
        str(relation)
        for row in events
        for relation in row.get("mediaRelationTypes") or []
    )
    linked_events = sum(1 for row in events if row.get("foundInWwise"))
    selection_events = sum(1 for row in events if row.get("selectionContainerTypes"))
    managed_literal_keys = {name.lower() for name in managed_literal_names}
    managed_literal_hirc_matches = sum(
        1 for row in events
        if row.get("id") in managed_literal_keys and row.get("foundInWwise")
    )
    table_event_hashes = {
        int(value) & 0xFFFFFFFF
        for value in audio_index.get("tableEventHashes") or []
        if isinstance(value, int)
    }
    table_event_hash_matches = sum(
        1 for row in events
        if isinstance(row.get("hash"), int)
        and (int(row["hash"]) & 0xFFFFFFFF) in table_event_hashes
        and row.get("foundInWwise")
    )
    runtime_systems = runtime_model.get("systems") or []
    runtime_layers = Counter(str(row.get("layer") or "unknown") for row in runtime_systems)
    trigger_status_context_counts = Counter(
        str(context.get("triggerBindingStatus") or "")
        for row in events
        for context in row.get("contexts") or []
        if isinstance(context, dict) and context.get("triggerBindingStatus")
    )
    trigger_status_event_counts = Counter(
        status
        for row in events
        for status in {
            str(context.get("triggerBindingStatus") or "")
            for context in row.get("contexts") or []
            if isinstance(context, dict) and context.get("triggerBindingStatus")
        }
    )
    play_sound_action_contexts = sum(
        context.get("kind") == "buffPlaySoundAction"
        for row in events
        for context in row.get("contexts") or []
        if isinstance(context, dict) and context.get("triggerPlaySoundActionCount")
    )
    play_sound_action_events = sum(
        any(
            isinstance(context, dict)
            and context.get("kind") == "buffPlaySoundAction"
            and context.get("triggerPlaySoundActionCount")
            for context in row.get("contexts") or []
        )
        for row in events
    )
    play_sound_action_occurrences = sum(
        int(context.get("triggerPlaySoundActionCount") or 0)
        for row in events
        for context in row.get("contexts") or []
        if isinstance(context, dict) and context.get("kind") == "buffPlaySoundAction"
    )
    wwise_source_reference_counts: Counter[str] = Counter()
    wwise_source_event_counts: Counter[str] = Counter()
    wwise_source_plugin_counts: Counter[str] = Counter()
    for event in events:
        event_source_kinds: set[str] = set()
        for evidence in event.get("evidence") or []:
            if not isinstance(evidence, dict):
                continue
            summary = evidence.get("sourceObjectSummary") or {}
            if not isinstance(summary, dict):
                continue
            for source_kind, count in (summary.get("sourceKindCounts") or {}).items():
                source_kind = str(source_kind or "unknown")
                wwise_source_reference_counts[source_kind] += int(count or 0)
                if count:
                    event_source_kinds.add(source_kind)
            for plugin_id, count in (summary.get("pluginCounts") or {}).items():
                wwise_source_plugin_counts[str(plugin_id)] += int(count or 0)
        for source_kind in event_source_kinds:
            wwise_source_event_counts[source_kind] += 1

    out_root = webui_root / f"data/lang/{language}/audio"
    events_name = "events.json"
    media_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    media_summaries: list[dict[str, Any]] = []
    for row in media:
        summary_row, detail_row = split_media_row(row)
        if detail_row:
            bucket_value = int(
                hashlib.sha256(str(row.get("id") or "").encode("utf-8")).hexdigest()[:8], 16
            ) & 0x3F
            detail_shard = f"media_details/{bucket_value:02x}.json"
            summary_row["detailShard"] = detail_shard
            media_details[detail_shard].append(detail_row)
        media_summaries.append(summary_row)
    media_names = [
        f"media.{index:03d}.json"
        for index in range(max(1, math.ceil(len(media_summaries) / MEDIA_SHARD_ROWS)))
    ]
    event_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_summaries: list[dict[str, Any]] = []
    for row in events:
        bucket_value = int(row.get("hash") or int(hashlib.sha256(str(row.get("id") or "").encode("utf-8")).hexdigest()[:8], 16)) & 0x3F
        detail_shard = f"event_details/{bucket_value:02x}.json"
        event_details[detail_shard].append(row)
        event_summaries.append(event_summary.event_summary_row(row, detail_shard))
    for detail_shard, detail_rows in event_details.items():
        json_dump(out_root / detail_shard, {
            "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
            "language": language,
            "events": detail_rows,
        })
    json_dump(out_root / events_name, {
        "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
        "language": language,
        "events": event_summaries,
    })
    for detail_shard, detail_rows in media_details.items():
        json_dump(out_root / detail_shard, {
            "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
            "language": language,
            "media": detail_rows,
        })
    for index, media_name in enumerate(media_names):
        json_dump(out_root / media_name, {
            "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
            "language": language,
            "media": media_summaries[index * MEDIA_SHARD_ROWS:(index + 1) * MEDIA_SHARD_ROWS],
        })
    # Drop the pre-sharding single file and any shards left over from a larger
    # previous run so stale rows cannot resurface.
    prune_stale_shards(out_root, "media", keep=media_names)
    prune_stale_detail_shards(out_root / "media_details", keep=media_details)
    trigger_context_name = "trigger_contexts.json"
    json_dump(out_root / trigger_context_name, trigger_context_catalog)
    scene_background_name = "scene_backgrounds.json"
    json_dump(out_root / scene_background_name, {
        key: value
        for key, value in scene_background_semantics.items()
        if key != "eventContexts"
    })
    scene_global_exact_events = [
        event for event in events
        if event.get("sceneGlobalContextStatus") == "exact"
    ]
    scene_global_unavailable_events = [
        event for event in events
        if event.get("sceneGlobalContextStatus") == "unavailable"
    ]
    scene_global_exact_context_count = sum(
        sum(
            context.get("kind") == "sceneGlobalAudioEvent"
            for context in event.get("contexts") or ()
            if isinstance(context, dict)
        )
        for event in scene_global_exact_events
    )
    scene_global_exact_scene_ids = {
        str(scene_id)
        for event in scene_global_exact_events
        for scene_id in event.get("sceneGlobalSceneIds") or ()
        if str(scene_id)
    }
    scene_emitter_exact_events = [
        event for event in events
        if event.get("sceneEmitterAttributionStatus") == "exactSceneAttribution"
    ]
    scene_emitter_prefab_local_events = [
        event for event in events
        if event.get("sceneEmitterAttributionStatus") == "prefabLocalSceneUnresolved"
    ]
    scene_emitter_unavailable_events = [
        event for event in events
        if event.get("sceneEmitterAttributionStatus") in {
            "sceneEmitterAttributionUnavailable",
            "sceneEmitterAttributionConflict",
        }
    ]
    scene_emitter_exact_scene_ids = {
        str(scene_id)
        for event in scene_emitter_exact_events
        for scene_id in event.get("sceneEmitterSceneIds") or ()
        if str(scene_id)
    }

    # The raw audio index can be reused from an older build and may contain
    # native/static GameParameter names that were produced without this
    # semantic run's explicit native gate.  Keep numeric HIRC evidence, but
    # withhold those names from the published semantic HIRC summary unless the
    # complete static six-name contract was validated.  This is keyed to the
    # domain result rather than just the native context: a validated binary
    # paired with stale/malformed serialized metadata must not leak old names.
    raw_hirc_summary = (
        alignment_audio_index.get("hircSummary")
        if isinstance(alignment_audio_index, dict)
        else None
    )
    published_hirc_summary = copy.deepcopy(raw_hirc_summary)
    alignment_status = str(static_rtpc_alignment.get("status") or "malformed")
    if alignment_status != "validated":
        if not isinstance(published_hirc_summary, dict):
            published_hirc_summary = {
                "status": "malformed",
                "postProcessSummary": {},
            }
        published_processing = published_hirc_summary.get("postProcessSummary")
        if not isinstance(published_processing, dict):
            published_processing = {}
            published_hirc_summary["postProcessSummary"] = published_processing
        published_processing["gameParameterNameEvidence"] = {
            "status": alignment_status,
            "entries": [],
            "evidenceBoundary": static_rtpc_alignment.get("evidenceBoundary") or "",
            "nativeGate": copy.deepcopy(
                static_rtpc_alignment.get("nativeGate") or {}
            ),
        }

    payload = {
        "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
        "audioCueExpressionSchemaVersion": int(
            cue_semantics.get("audioCueExpressionSchemaVersion")
            or table_contexts.AUDIO_CUE_EXPRESSION_SCHEMA_VERSION
        ),
        "generated": audio_index.get("generated") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "debugOnly": False,
        "sourceIndex": f"export_full/structured/Audio/{language}/index.json",
        "sourceIndexFingerprint": {
            "generated": audio_index.get("generated"),
            "eventEvidenceSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
            "counts": audio_index.get("counts") or {},
        },
        "metadataEventSymbolAliases": metadata_event_symbol_catalog,
        "shards": {
            "events": events_name,
            "media": media_names,
            "sceneBackgrounds": scene_background_name,
        },
        "triggerContexts": {
            "shard": trigger_context_name,
            "schemaVersion": trigger_context_catalog.get("schemaVersion"),
            "counts": trigger_context_catalog.get("counts") or {},
            "coverage": trigger_context_catalog.get("coverage") or {},
            "evidenceBoundary": trigger_context_catalog.get("evidenceBoundary") or "",
        },
        "eventDetailShardCount": len(event_details),
        "counts": {
            "decodedMedia": len(media),
            **media_trigger_context_counts,
            **media_trigger_semantic_category_counts,
            **media_post_process_counts,
            **{
                key: value
                for key, value in media_coarse_ownership.items()
                if key not in {"schemaVersion", "evidenceBoundary"}
            },
            **{
                key: value
                for key, value in animation_action_ownership.items()
                if key not in {"schemaVersion", "evidenceBoundary"}
            },
            "namedEvents": len(named_event_ids),
            "wwiseEventObjectHashes": sum(
                row.get("foundInWwise") for row in events
            ),
            "wwiseEventObjectOccurrences": len(audio_index.get("wwiseEventInventory") or []),
            "wwiseEventObjectsWithoutRecoveredAuthoredTrigger": sum(
                row.get("eventIdentityStatus") == "wwiseObjectWithoutRecoveredTriggerName"
                for row in events
            ),
            "audioDialogWwiseEventAliases": len(
                audio_index.get("audioDialogWwiseEventAliases") or []
            ),
            "voiceTableWwiseEventAliases": len(
                audio_index.get("voiceTableWwiseEventAliases") or []
            ),
            "typedUiTableWwiseEventAliases": len(
                audio_index.get("typedUiTableWwiseEventAliases") or []
            ),
            "snsVoiceWwiseEventAliases": len(
                audio_index.get("snsVoiceWwiseEventAliases") or []
            ),
            "skillIdDictionaryWwiseEventAliases": len(
                audio_index.get("skillIdDictionaryWwiseEventAliases") or []
            ),
            "grammarRecoveredWwiseEventNames": len(
                audio_index.get("grammarRecoveredWwiseEventNames") or []
            ),
            "grammarRecoveredWwiseEventNameIsolatedPreimages": len(
                (audio_index.get("grammarEventNameRecovery") or {}).get("isolatedEntries") or []
            ),
            "grammarRecoveredWwiseEventNameExpectedCoincidences": float(
                (audio_index.get("grammarEventNameRecovery") or {}).get(
                    "expectedCoincidentalPreimages"
                )
                or 0.0
            ),
            "purposeUnknownEvents": sum(
                row.get("purposeInvestigationPriority") == "highest"
                for row in events
            ),
            "purposePartialEvents": sum(
                row.get("purposeInvestigationPriority") == "secondary"
                for row in events
            ),
            "purposeKnownEvents": sum(
                row.get("purposeInvestigationPriority") == "resolved"
                for row in events
            ),
            "purposeUnknownMedia": sum(
                row.get("purposeInvestigationPriority") == "highest"
                for row in media
            ),
            "purposePartialMedia": sum(
                row.get("purposeInvestigationPriority") == "secondary"
                for row in media
            ),
            "purposeKnownMedia": sum(
                row.get("purposeInvestigationPriority") == "resolved"
                for row in media
            ),
            "purposeStoryTerminalMedia": sum(
                row.get("purposeInvestigationPriority") == "resolvedTerminal"
                for row in media
            ),
            "authoredEventsUnresolvedToWwise": sum(
                not row.get("foundInWwise") for row in events
            ),
            "mediaPlaybackLocationUnknown": media_playback_location_counts.get("unknown", 0),
            "recoveredOrphanExternalMediaIdentities": sum(
                row.get("externalMediaIdentityStatus") == "recoveredAuthoredPathHash"
                for row in media
            ),
            "mediaWithEventRelationOnly": media_playback_location_counts.get("eventRelationOnly", 0),
            "mediaWithAuthoredEventContext": media_playback_location_counts.get("authoredEventContext", 0),
            "directDialogMedia": media_playback_location_counts.get("directDialogMedia", 0),
            "sharedPlayableCharacterAnimationEvents": sum(
                int(row.get("playableCharacterAnimationOwnerCount") or 0) > 1
                for row in events
            ),
            "footstepSystemEvents": sum(
                "OnCustomFootStep" in (row.get("animationFunctions") or [])
                for row in events
            ),
            "customFootstepCallbackOccurrences": (
                custom_footstep_model.get("corpus") or {}
            ).get("occurrenceCount", 0),
            "customFootstepParameterVariants": (
                custom_footstep_model.get("corpus") or {}
            ).get("parameterVariantCount", 0),
            "metadataEventSymbolAliases": int(
                metadata_event_symbol_catalog.get("matchCount") or 0
            ),
            "luaPostEventNames": context_kind_event_counts.get("luaPostEvent", 0),
            "luaPostEventContexts": context_kind_counts.get("luaPostEvent", 0),
            "runtimeSystems": len(runtime_systems),
            "projectileSoundEvents": context_kind_event_counts.get("projectileSoundField", 0),
            "spawnerPreWarnAudioEvents": context_kind_event_counts.get("spawnerPreWarnAudio", 0),
            "spawnerPreWarnAudioContexts": context_kind_counts.get("spawnerPreWarnAudio", 0),
            "spawnerPreWarnAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in spawner_event_rows
            ),
            "spawnerPreWarnAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in spawner_event_rows
            ),
            "patrolSubActionPlayAudioEvents": context_kind_event_counts.get("patrolSubActionPlayAudio", 0),
            "patrolSubActionPlayAudioContexts": context_kind_counts.get("patrolSubActionPlayAudio", 0),
            "patrolSubActionPlayAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in patrol_event_rows
            ),
            "patrolSubActionPlayAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in patrol_event_rows
            ),
            "charInteractAudioEvents": context_kind_event_counts.get("charInteractAudioEvent", 0),
            "charInteractAudioContexts": context_kind_counts.get("charInteractAudioEvent", 0),
            "charInteractAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in char_interact_event_rows
            ),
            "charInteractAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in char_interact_event_rows
            ),
            "physicsAudioEvents": context_kind_event_counts.get("physicsAudioComponentEvent", 0),
            "physicsAudioEventContexts": context_kind_counts.get("physicsAudioComponentEvent", 0),
            "physicsAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in physics_audio_event_rows
            ),
            "physicsAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in physics_audio_event_rows
            ),
            "physicsAudioRtpcControls": len(physics_audio_semantics.get("rtpcParameters") or []),
            "physicsAudioConsumerIdentities": (physics_audio_semantics.get("stats") or {}).get("physicsAudioConsumerIdentities") or 0,
            "modelViewStateAudioEvents": context_kind_event_counts.get("modelViewStateAudioEvent", 0)
                + context_kind_event_counts.get("modelViewStatePositionAudioEvent", 0),
            "modelViewStateAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in model_view_event_rows
            ),
            "modelViewStateAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in model_view_event_rows
            ),
            "modelViewStatePositionedControls": context_kind_counts.get("modelViewStatePositionedCustomStateControl", 0)
                + context_kind_counts.get("modelViewStatePositionedEntityStateControl", 0),
            "modelViewStateSpatialControls": len(model_view_semantics.get("spatialControls") or []),
            "modelViewStateCustomAudioControls": len(model_view_semantics.get("customAudioControls") or []),
            "levelScriptAudioCueInvocations": len(levelscript_semantics.get("cueInvocations") or []),
            "levelScriptDynamicAudioBindings": len(levelscript_semantics.get("dynamicEventBindings") or []),
            "radioTableDefinitions": (radio_catalog.get("counts") or {}).get("radioTableDefinitions", 0),
            "radioTableLines": (radio_catalog.get("counts") or {}).get("radioTableLines", 0),
            "levelScriptAudioControls": len(levelscript_semantics.get("controlActions") or []),
            "levelScriptDynamicControlBindings": len(levelscript_semantics.get("dynamicControlBindings") or []),
            "authoredPlaySoundActionEvents": play_sound_action_events,
            "authoredPlaySoundActionOccurrences": play_sound_action_occurrences,
            "exactSkillConfigTriggerEvents": trigger_status_event_counts.get("exactSkillConfig", 0),
            "exactSkillConfigTriggerContexts": trigger_status_context_counts.get("exactSkillConfig", 0),
            "triggerContexts": int(
                (trigger_context_catalog.get("counts") or {}).get("total") or 0
            ),
        },
        "coverage": {
            "eventCategories": dict(sorted(event_categories.items())),
            "mediaCategories": dict(sorted(media_categories.items())),
            "eventMediaRelations": dict(sorted(media_relations.items())),
            "runtimeLayers": dict(sorted(runtime_layers.items())),
            "contextKinds": dict(sorted(context_kind_counts.items())),
        },
        "categories": [
            {"id": key, "label": label, "eventCount": event_categories.get(key, 0), "mediaCount": media_categories.get(key, 0)}
            for key, label in CATEGORY_LABELS.items()
        ],
        "banks": banks,
        "hircSummary": published_hirc_summary,
        "customFootstepModel": custom_footstep_model,
        "triggerCatalog": {
            "aiBark": ai_bark_catalog,
            "enemyTriggerVoiceAction": (
                native_evidence.ENEMY_TRIGGER_VOICE_ACTION_NATIVE
                if native_context.validated
                else native_context.unavailable_contract(
                    str(native_evidence.ENEMY_TRIGGER_VOICE_ACTION_NATIVE["nativeMappingId"])
                )
            ),
            "spawnerPreWarnAudio": spawner_semantics.get("stats") or {},
            "patrolSubActionPlayAudio": patrol_semantics.get("stats") or {},
            "charInteractAudio": char_interact_semantics.get("stats") or {},
            "physicsAudio": {
                **(physics_audio_semantics.get("stats") or {}),
                "definitions": physics_audio_semantics.get("definitions") or [],
            },
            "modelViewStateAudio": model_view_semantics.get("stats") or {},
            "sceneBackgroundAudio": {
                "status": scene_background_semantics.get("status"),
                "shard": scene_background_name,
                **(scene_background_semantics.get("counts") or {}),
                "evidenceBoundary": (
                    scene_background_semantics.get("evidenceBoundary") or ""
                ),
            },
            "mediaCoarseOwnership": media_coarse_ownership,
            "characterAudioNameIdentity": character_audio_ownership,
            "animationCallbackLink": animation_callback_ownership,
            "animationActionNameMatch": animation_action_ownership,
            "monoBehaviourAudioId": mono_behaviour_audio_id_semantics.get("stats") or {},
            "levelScriptAudio": levelscript_semantics.get("stats") or {},
            "levelSequenceAudio": {
                **(levelsequence_play_actions.get("stats") or {}),
                **(timeline_ownership.get("stats") or {}),
                **(levelsequence_semantics.get("stats") or {}),
                "targetEventCount": len(timeline_context_event_ids),
                "evidenceBoundary": levelsequence_semantics.get("evidenceBoundary") or "",
                "playActionEvidenceBoundary": levelsequence_play_actions.get("evidenceBoundary") or "",
                "timelineOwnershipEvidenceBoundary": timeline_ownership.get("evidenceBoundary") or "",
                "timelineCueStats": timeline_cue_semantics.get("stats") or {},
                "timelineCueEvidenceBoundary": timeline_cue_semantics.get("evidenceBoundary") or "",
            },
            "levelScriptRadio": radio_catalog,
            "triggerContext": {
                **(trigger_context_catalog.get("counts") or {}),
                "shard": trigger_context_name,
                "coverage": trigger_context_catalog.get("coverage") or {},
                "evidenceBoundary": trigger_context_catalog.get("evidenceBoundary") or "",
            },
        },
        "controlCatalog": {
            "schemaVersion": 2,
            "audioCueExpressionSchemaVersion": int(
                cue_semantics.get("audioCueExpressionSchemaVersion")
                or table_contexts.AUDIO_CUE_EXPRESSION_SCHEMA_VERSION
            ),
            "audioCueNativeContract": cue_semantics.get("audioCueNativeContract") or {},
            "counts": {
                "audioCueDefinitions": len(cue_semantics.get("cueDefinitions") or {}),
                "audioCueBehaviorEventContexts": sum(
                    len(rows) for rows in (cue_semantics.get("eventContexts") or {}).values()
                ),
                "audioCueExpressionOperands": len(cue_semantics.get("expressionOperands") or []),
                "audioCueExpressionStringLiterals": sum(
                    int((definition.get("expressionNodeClassCounts") or {}).get("stringLiteral", 0))
                    for definition in (cue_semantics.get("cueDefinitions") or {}).values()
                    if isinstance(definition, dict)
                ),
                "audioCueVariableNameCandidates": sum(
                    int((definition.get("expressionNodeClassCounts") or {}).get("authoredVariableNameCandidate", 0))
                    for definition in (cue_semantics.get("cueDefinitions") or {}).values()
                    if isinstance(definition, dict)
                ),
                "audioCueExpressionNodes": sum(
                    int(definition.get("expressionNodeCount") or 0)
                    for definition in (cue_semantics.get("cueDefinitions") or {}).values()
                    if isinstance(definition, dict)
                ),
                "audioCueExpressionDiagnostics": sum(
                    int(definition.get("expressionDiagnosticCount") or 0)
                    for definition in (cue_semantics.get("cueDefinitions") or {}).values()
                    if isinstance(definition, dict)
                ),
                "audioGlobalMusicCueRefs": len(global_controls.get("audioGlobalMusicCueRefs") or []),
                "audioGlobalMusicCueRefsResolved": sum(
                    row.get("definitionStatus") == "resolved"
                    for row in global_controls.get("audioGlobalMusicCueRefs") or []
                ),
                "rtpcParameters": len(global_controls.get("rtpcParameters") or []) + len(managed_rtpc_parameters),
                "physicsAudioRtpcParameters": len(physics_audio_semantics.get("rtpcParameters") or []),
                "modelViewStateRtpcParameters": len(model_view_semantics.get("rtpcParameters") or []),
                "modelViewStateSpatialControls": len(model_view_semantics.get("spatialControls") or []),
                "modelViewStateCustomAudioControls": len(model_view_semantics.get("customAudioControls") or []),
                "modelViewStatePositionedControls": len(model_view_semantics.get("positionedControls") or []),
                "levelScriptAudioCueInvocations": len(levelscript_semantics.get("cueInvocations") or []),
                "levelScriptAudioCueInvocationsResolved": (
                    (levelscript_semantics.get("stats") or {}).get("cueDefinitionStatusCounts") or {}
                ).get("resolved", 0),
                "levelScriptAudioCueInvocationsMissing": (
                    (levelscript_semantics.get("stats") or {}).get("cueDefinitionStatusCounts") or {}
                ).get("missing", 0),
                "levelScriptAudioCueBehaviorEventContexts": (
                    (levelscript_semantics.get("stats") or {}).get("cueBehaviorEventContexts") or 0
                ),
                "levelScriptDynamicAudioBindings": len(levelscript_semantics.get("dynamicEventBindings") or []),
                "levelScriptResolvedDynamicAudioBindings": len(
                    levelscript_semantics.get("resolvedDynamicEventBindings") or []
                ),
                "levelScriptAudioControls": len(levelscript_semantics.get("controlActions") or []),
                "levelScriptDynamicControlBindings": len(levelscript_semantics.get("dynamicControlBindings") or []),
                "timelineAudioCueInvocations": len(timeline_cue_semantics.get("invocations") or []),
                "timelineAudioCueInvocationsResolved": (
                    (timeline_cue_semantics.get("stats") or {}).get("timelineCueInvocationsResolved", 0)
                ),
                "timelineAudioCueInvocationsMissing": (
                    (timeline_cue_semantics.get("stats") or {}).get("timelineCueInvocationsMissing", 0)
                ),
                "levelEventAudioConditionDefinitions": len(LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS),
                "levelEventAudioConditionAuthoredOccurrences": sum(
                    int(row.get("authoredOccurrenceCount") or 0)
                    for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
                ),
                "wwiseSelectorGroupsCensused": 56,
                "wwiseSelectorGroupsWithRuntimeSetter": 2,
                "wwiseSelectorGroupsWithSemanticInference": 3,
                "wwiseSelectorGroupsPublished": len(wwise_selector_groups),
                "wwiseMusicStateGroupsPublished": len(AUDIO_MUSIC_NATIVE_STATE_GROUPS),
                "wwiseSelectorPackageValuesCensused": 234,
                "wwiseSelectorValuesWithMetadataStringMatch": 67,
                "wwiseSelectorValuesWithoutRecoveredString": 167,
                "wwiseActionControlCount": wwise_action_control_catalog.get("actionCount", 0),
                "wwiseActionControlTypedExactCount": wwise_action_control_catalog.get("typedExactActionCount", 0),
                "wwiseActionControlGroupSemanticMatchCount": wwise_action_control_catalog.get("groupSemanticMatchCount", 0),
                "wwiseActionControlValueSemanticMatchCount": wwise_action_control_catalog.get("valueSemanticMatchCount", 0),
                "wwiseActionControlInitialRtpcIdMatchCount": wwise_action_control_catalog.get("sharedRtpcParameterIdMatchCount", 0),
                "wwiseActionControlInitialRtpcIdCount": wwise_action_control_catalog.get("sharedRtpcParameterIdCount", 0),
                "wwiseActionControlNamedInitialRtpcMatchCount": wwise_action_control_catalog.get("namedInitialRtpcMatchCount", 0),
                "wwiseInitialRtpcNamedParameterCount": len(wwise_initial_rtpc_catalog),
                "wwiseInitialRtpcNamedCurveCount": sum(
                    int(row.get("curveCount") or 0)
                    for row in wwise_initial_rtpc_catalog
                ),
                "staticRtpcAlignmentParameterCount": int(
                    (static_rtpc_alignment.get("counts") or {}).get(
                        "staticParameterCount", 0
                    )
                ),
                "staticRtpcAlignmentMatchedParameterCount": int(
                    (static_rtpc_alignment.get("counts") or {}).get(
                        "serializedHircMatchedParameterCount", 0
                    )
                ),
                "staticRtpcAlignmentSetControlCount": int(
                    (static_rtpc_alignment.get("counts") or {}).get(
                        "setGameParameterControlCount", 0
                    )
                ),
                "staticRtpcAlignmentResetControlCount": int(
                    (static_rtpc_alignment.get("counts") or {}).get(
                        "resetGameParameterControlCount", 0
                    )
                ),
            },
            "audioGlobalMusicCueRefs": global_controls.get("audioGlobalMusicCueRefs") or [],
            "rtpcParameters": (global_controls.get("rtpcParameters") or []) + managed_rtpc_parameters,
            "physicsAudioRtpcParameters": physics_audio_semantics.get("rtpcParameters") or [],
            "modelViewStateRtpcParameters": model_view_semantics.get("rtpcParameters") or [],
            "modelViewStateSpatialControls": model_view_semantics.get("spatialControls") or [],
            "modelViewStateCustomAudioControls": model_view_semantics.get("customAudioControls") or [],
            "modelViewStatePositionedControls": model_view_semantics.get("positionedControls") or [],
            "levelScriptAudioCueInvocations": _compact_levelscript_control_rows(
                levelscript_semantics.get("cueInvocations")
            ),
            "levelScriptDynamicAudioBindings": _compact_levelscript_control_rows(
                levelscript_semantics.get("dynamicEventBindings")
            ),
            "levelScriptResolvedDynamicAudioBindings": (
                _compact_levelscript_control_rows(
                    levelscript_semantics.get("resolvedDynamicEventBindings")
                )
            ),
            "levelScriptAudioControls": _compact_levelscript_control_rows(
                levelscript_semantics.get("controlActions")
            ),
            "levelScriptDynamicControlBindings": _compact_levelscript_control_rows(
                levelscript_semantics.get("dynamicControlBindings")
            ),
            "timelineAudioCueInvocations": timeline_cue_semantics.get("invocations") or [],
            "levelEventAudioConditions": [
                dict(row) for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
            ],
            "wwiseSelectorGroups": [
                dict(row) for row in wwise_selector_groups
            ],
            "wwiseActionControls": wwise_action_control_catalog,
            "wwiseInitialRtpcParameters": wwise_initial_rtpc_catalog,
            "staticRtpcAlignment": static_rtpc_alignment,
            "evidenceBoundary": "Cue behavior exprType=3 values, constant LevelScript Event parameters, LevelScript cue names joined by the native AudioHashGenerator to exact cue behavior expressions, non-empty PhysicsAudio Event properties, and normal ModelView Event plus positioned direct-position hashes are authored requests. Positioned custom/entity state rows are typed controls only and never Event ownership. Metadata-named InitialRTPC rows are exact ID/hash joins that preserve authored curve targets and controlled properties; they do not observe live RTPC updates or audibility. PhysicsAudio/ModelView RTPC names, ModelView spatial/custom-audio rows, cue/action execution, handler conditions, exprType=8 strings, dynamic Params, state/variable writes, playback handles, placeholder-music ids, unresolved cue hashes, and musicCue* values remain typed controls or unresolved runtime state. LevelEvent OnAudioStateChanged and OnMusicBeatEvent are current-build trigger-input definitions, not playback requests; exhaustive active-overlay scanning found zero authored occurrences. Two non-music Wwise selector groups have exact native setter callsites; three more have high-confidence semantic correlation only, and ten music State groups have exact current-metadata/native-setter joins. None reveal a live value, selected branch, or authored group name.",
        },
        "runtimeModel": runtime_model,
        "runtimeObservations": runtime_observation_projection,
        "evidenceBoundary": {
            "decodedMedia": "A decoded FLAC/WAV/WEM is a source media object, not proof that it played.",
            "eventMedia": "Possible media leaves use typed Wwise v150 Event -> Action -> reciprocal Children -> Sound/MusicTrack AkBankSourceData edges. Ordinary Codec sources may join decoded media; External Source codec and synthesized Source-plugin records remain non-media playback sources. Play roots and random/sequence/switch/layer relations are preserved; runtime selection and source instantiation are not evaluated. Unsupported plugins, music nodes, and unparsed child structures fail closed.",
            "mediaPostProcess": "Media post-process route summaries join each possible Event media leaf to the Event evidence's exact serialized output-bus path. Bus IDs and unresolved processing IDs are references into the HIRC bus catalog; runtime branch selection, inherited effective settings, live bypass/RTPC/State values, platform DSP, and audibility remain unresolved.",
            "mediaTriggerContexts": "Media rows join serialized trigger_contexts.json mediaRefs to exact trigger semantic kinds, roles, owner/situation values, and selection/activation statuses. This is an authored request or placement summary; runtime execution and live branch choice remain unobserved.",
            "authoredContext": "Table, Timeline, SkillData, and BuffData references prove authored consumers, not a live playback trace.",
            "animationOwnership": "An AnimationClip callback proves that the owned clip requests the Event. If the same Event is used by multiple playable characters, its complete Wwise leaf graph is a shared selector surface and is not character-specific media ownership.",
            "customFootstepCallbacks": custom_footstep_model.get("evidenceBoundary") or "",
            "authoredEventHash": "Signed table integers are normalized to uint32 only in event-designated fields; row and field prove semantic ownership even when no string name is known.",
            "projectileSound": "A nonzero decoded projectile sound slot proves the projectile lifecycle field references the uint32 Wwise Event. It does not prove that the projectile was spawned, that the lifecycle phase executed, or which Wwise media branch was selected.",
            "spawnerPreWarnAudio": "The current mc13 SpawnerEnemyLibraryItem preWarnAudioEventKey proves an authored enemy-spawn pre-warning request and its row-local timing/effect/enemy/template source. It does not prove that the spawner executed or that a Wwise branch played; unresolved authored names remain visible.",
            "patrolSubActionPlayAudio": (patrol_semantics.get("stats") or {}).get("evidenceBoundary") or "",
            "charInteractAudio": (char_interact_semantics.get("stats") or {}).get("evidenceBoundary") or "",
            "physicsAudio": physics_audio_semantics.get("evidenceBoundary") or "",
            "modelViewStateAudio": model_view_semantics.get("evidenceBoundary") or "",
            "sceneBackgroundAudio": (
                scene_background_semantics.get("evidenceBoundary") or ""
            ),
            "mediaCoarseOwnership": media_coarse_ownership.get(
                "evidenceBoundary", ""
            ),
            "characterAudioNameIdentity": character_audio_ownership.get(
                "evidenceBoundary", ""
            ),
            "animationCallbackLink": animation_callback_ownership.get(
                "evidenceBoundary", ""
            ),
            "animationActionNameMatch": animation_action_ownership.get(
                "evidenceBoundary", ""
            ),
            "monoBehaviourAudioId": mono_behaviour_audio_id_semantics.get("evidenceBoundary") or "",
            "levelScriptAudio": levelscript_semantics.get("evidenceBoundary") or "",
            "levelSequenceAudio": (
                (levelsequence_semantics.get("evidenceBoundary") or "")
                + " "
                + (levelsequence_play_actions.get("evidenceBoundary") or "")
                + " "
                + (timeline_ownership.get("evidenceBoundary") or "")
                + " "
                + (timeline_cue_semantics.get("evidenceBoundary") or "")
            ).strip(),
            "levelScriptRadio": radio_catalog.get("evidenceBoundary") or "",
            "levelEventAudioConditions": "OnAudioStateChanged and OnMusicBeatEvent are exact current-build LevelEvent condition definitions. The active Persistent-over-Streaming LevelScript overlay contains zero authored occurrences, and neither condition is a Wwise playback request.",
            "audioCue": "Only behaviourExpr exprType=3 string values are Event requests. exprType=8 strings are runtime cue-variable operands; AudioGlobal musicCue fields are cue references, and RTPC names are control parameters.",
            "runtimeMetadata": (
                "IL2CPP names prove shipped system structure. Selected current-build native call chains "
                "prove static request routing, asynchronous Event preparation, Wwise posting, and playing-id "
                "lifetime handling; they are not a live execution trace, active state, or selected media leaf."
            ),
            "runtimeObservations": runtime_observation_projection.get(
                "evidenceBoundary", ""
            ),
        },
    }
    gameplay_sound_effects_path = (
        webui_root / f"data/lang/{language}/gameplay/sound_effects.json"
    )
    conversation_dir = webui_root / f"data/lang/{language}/conv"
    conversation_ids = {
        path.stem for path in conversation_dir.glob("*.json") if path.is_file()
    }
    dialog_lifecycle_story = dialog_lifecycle.project_story_lifecycle_audio(
        trigger_context_catalog.get("contexts") or (),
        conversation_ids,
    )
    previous_audio_index = load_json(out_root / "index.json", {})
    previous_lifecycle_ids = set(
        ((previous_audio_index.get("storyDialogLifecycleAudio") or {}).get(
            "conversationIds"
        ) or ())
        if isinstance(previous_audio_index, dict)
        else ()
    )
    lifecycle_by_conversation = dialog_lifecycle_story.get("conversations") or {}
    for conversation_id in sorted(previous_lifecycle_ids | set(lifecycle_by_conversation)):
        conversation_path = conversation_dir / f"{conversation_id}.json"
        conversation = load_json(conversation_path, {})
        if not isinstance(conversation, dict) or not conversation:
            continue
        rows = lifecycle_by_conversation.get(conversation_id) or []
        if rows:
            conversation["dialogLifecycleAudio"] = rows
        else:
            conversation.pop("dialogLifecycleAudio", None)
        json_dump(conversation_path, conversation)
    payload["storyDialogLifecycleAudio"] = {
        "schemaVersion": dialog_lifecycle_story.get("schemaVersion"),
        "counts": dialog_lifecycle_story.get("counts") or {},
        "conversationIds": sorted(lifecycle_by_conversation),
        "evidenceBoundary": dialog_lifecycle_story.get("evidenceBoundary") or "",
    }
    gameplay_sound_effects = load_json(gameplay_sound_effects_path, {})
    if isinstance(gameplay_sound_effects, dict) and gameplay_sound_effects:
        gameplay_characters = gameplay_sound_effects.setdefault("characters", {})
        gameplay_enemies = gameplay_sound_effects.setdefault("enemies", {})
        for gameplay_character in gameplay_characters.values():
            if isinstance(gameplay_character, dict):
                gameplay_character.pop("authoredNamespaceEvents", None)
        for character_id, namespace_events in (
            character_namespace_gameplay.get("characters") or {}
        ).items():
            gameplay_characters.setdefault(character_id, {})[
                "authoredNamespaceEvents"
            ] = namespace_events
        enemy_namespace_gameplay = (
            media_ownership.project_enemy_namespace_gameplay_audio(
                events,
                gameplay_enemies.keys(),
            )
        )
        enemy_native_voice_responses = (
            media_ownership.project_enemy_native_voice_response_audio(
                events,
                gameplay_enemies.keys(),
            )
        )
        enemy_response_candidates = (
            media_ownership.project_enemy_response_candidate_audio(
                events,
                gameplay_enemies.keys(),
            )
        )
        character_native_voice_responses = (
            media_ownership.project_character_native_voice_response_audio(
                events,
                (
                    row.get("characterId")
                    for row in character_audio_catalog.get("characters") or ()
                    if isinstance(row, dict)
                ),
            )
        )
        for gameplay_character in gameplay_characters.values():
            if isinstance(gameplay_character, dict):
                gameplay_character.pop("nativeVoiceResponseEvents", None)
        for character_id, response_events in (
            character_native_voice_responses.get("characters") or {}
        ).items():
            gameplay_characters.setdefault(character_id, {})[
                "nativeVoiceResponseEvents"
            ] = response_events
        for gameplay_enemy in gameplay_enemies.values():
            if isinstance(gameplay_enemy, dict):
                gameplay_enemy.pop("authoredNamespaceEvents", None)
                gameplay_enemy.pop("nativeVoiceResponseEvents", None)
                gameplay_enemy.pop("enemyResponseCandidateEvents", None)
        for enemy_id, namespace_events in (
            enemy_namespace_gameplay.get("enemies") or {}
        ).items():
            gameplay_enemies.setdefault(enemy_id, {})[
                "authoredNamespaceEvents"
            ] = namespace_events
        for enemy_id, response_events in (
            enemy_native_voice_responses.get("enemies") or {}
        ).items():
            gameplay_enemies.setdefault(enemy_id, {})[
                "nativeVoiceResponseEvents"
            ] = response_events
        for enemy_id, response_events in (
            enemy_response_candidates.get("enemies") or {}
        ).items():
            gameplay_enemies.setdefault(enemy_id, {})[
                "enemyResponseCandidateEvents"
            ] = response_events
        gameplay_sound_effects["schemaVersion"] = 10
        gameplay_sound_effects["characterNamespaceAudio"] = {
            "schemaVersion": character_namespace_gameplay.get("schemaVersion"),
            "counts": character_namespace_gameplay.get("counts") or {},
            "evidenceBoundary": (
                character_namespace_gameplay.get("evidenceBoundary") or ""
            ),
        }
        gameplay_sound_effects["enemyNamespaceAudio"] = {
            "schemaVersion": enemy_namespace_gameplay.get("schemaVersion"),
            "counts": enemy_namespace_gameplay.get("counts") or {},
            "evidenceBoundary": enemy_namespace_gameplay.get("evidenceBoundary") or "",
        }
        gameplay_sound_effects["enemyNativeVoiceResponses"] = {
            "schemaVersion": enemy_native_voice_responses.get("schemaVersion"),
            "counts": enemy_native_voice_responses.get("counts") or {},
            "evidenceBoundary": (
                enemy_native_voice_responses.get("evidenceBoundary") or ""
            ),
        }
        gameplay_sound_effects["characterNativeVoiceResponses"] = {
            "schemaVersion": character_native_voice_responses.get("schemaVersion"),
            "counts": character_native_voice_responses.get("counts") or {},
            "evidenceBoundary": (
                character_native_voice_responses.get("evidenceBoundary") or ""
            ),
        }
        gameplay_sound_effects["enemyResponseCandidates"] = {
            "schemaVersion": enemy_response_candidates.get("schemaVersion"),
            "counts": enemy_response_candidates.get("counts") or {},
            "evidenceBoundary": enemy_response_candidates.get("evidenceBoundary") or "",
        }
        gameplay_counts = gameplay_sound_effects.setdefault("counts", {})
        for key, value in (character_namespace_gameplay.get("counts") or {}).items():
            gameplay_counts[f"characterNamespace{key[0].upper()}{key[1:]}"] = value
        for key, value in (enemy_namespace_gameplay.get("counts") or {}).items():
            gameplay_counts[f"enemyNamespace{key[0].upper()}{key[1:]}"] = value
        for key, value in (enemy_native_voice_responses.get("counts") or {}).items():
            gameplay_counts[f"enemyNativeVoice{key[0].upper()}{key[1:]}"] = value
        for key, value in (
            character_native_voice_responses.get("counts") or {}
        ).items():
            gameplay_counts[f"characterNativeVoice{key[0].upper()}{key[1:]}"] = value
        for key, value in (enemy_response_candidates.get("counts") or {}).items():
            gameplay_counts[f"enemyResponseCandidate{key[0].upper()}{key[1:]}"] = value
        json_dump(gameplay_sound_effects_path, gameplay_sound_effects)
    json_dump(out_root / "index.json", payload)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--webui-root", type=Path, default=DEFAULT_WEBUI_ROOT)
    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help=(
            "Selected Endfield_Data root for the native evidence gate. If omitted, "
            "native callsite/runtime claims remain unavailable."
        ),
    )
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument(
        "--runtime-trace-bundle",
        type=Path,
        default=None,
        help="Optional verified audio runtime-trace JSON bundle to project onto Event/media rows.",
    )
    args = parser.parse_args(argv)
    if args.metadata is None and args.game_root is not None:
        installed = args.game_root / DEFAULT_METADATA_REL
        args.metadata = installed if installed.is_file() else None
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = str(args.language or "CN").upper()
    index_path = args.export_root / f"structured/Audio/{language}/index.json"
    audio_index = load_json(index_path, {})
    if not isinstance(audio_index, dict) or not audio_index:
        raise SystemExit(f"Audio index not found or invalid: {index_path}")
    payload = build_audio_semantic_data(
        audio_index,
        language=language,
        export_root=args.export_root.resolve(),
        webui_root=args.webui_root.resolve(),
        metadata_path=args.metadata.resolve() if args.metadata else None,
        gameassembly_path=(
            (args.game_root.parent / "GameAssembly.dll").resolve()
            if args.game_root is not None
            else None
        ),
        runtime_trace_bundle=(
            args.runtime_trace_bundle.resolve()
            if args.runtime_trace_bundle is not None
            else None
        ),
    )
    print(
        "Audio semantic WebUI data:"
        f" {payload['counts']['eventRecords']:,} Event records"
        f" ({payload['counts']['namedEvents']:,} authored names),"
        f" {payload['counts']['decodedMedia']:,} media,"
        f" {payload['counts']['runtimeSystems']:,} runtime systems"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
