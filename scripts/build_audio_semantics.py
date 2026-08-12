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
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_METADATA_REL = Path("il2cpp_data/Metadata/global-metadata.dat")
METADATA_HELPER = ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
RUNTIME_CACHE_REL = Path("recovered/audio_semantics/runtime_metadata.json")
METADATA_MAGIC = 0xFAB11BAF
MANAGED_AUDIO_LITERAL_RE = re.compile(
    r"^(?:au|bark|radio)_[A-Za-z0-9_./+:-]+$",
    re.IGNORECASE,
)

EVENT_CATEGORY_PREFIXES = (
    ("au_sfx_", "sfx"),
    ("au_chr_", "sfx"),
    ("au_eny_", "sfx"),
    ("au_monster_", "sfx"),
    ("au_int_", "sfx"),
    ("au_item_", "sfx"),
    ("au_gameplay_", "sfx"),
    ("au_weekraid_", "sfx"),
    ("au_music_", "music"),
    ("au_cue_", "cue"),
    ("au_amb_", "ambience"),
    ("au_env_", "ambience"),
    ("au_fac_amb_", "ambience"),
    ("au_ui_", "ui"),
    ("au_vo_", "voice"),
    ("au_voice_", "voice"),
    ("au_radio_", "voice"),
    ("au_dlg_", "voice"),
    ("au_fac_announcement_", "voice"),
    ("au_global_", "control"),
    ("au_trigger_", "control"),
    ("au_rtpc_", "control"),
    ("au_motion_", "control"),
    ("au_vibration_", "control"),
    ("bark_", "voice"),
    ("radio_", "voice"),
    ("projectile-event:", "sfx"),
)

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

NARRATIVE_AUDIO_TABLE_NAMES = (
    "RemoteCommonTable.json", "AudioCueTable.json", "AudioVoiceExtraData.json",
    "EmotionVoiceConfig.json", "AudioDialogCustomEventTable.json", "AudioDialogConfigs.json",
    "AudioRadioContinueTable.json", "RadioTable.json",
)
AUDIO_CONFIG_TABLE_NAMES = (
    "AudioBattleBuildings.json", "AudioCollection.json", "AudioDrop.json",
    "AudioFactory.json", "AudioFactoryAnnouncement.json", "AudioItemDragAndDrop.json",
    "AudioItemTypeDragAndDrop.json", "AudioLevel.json", "SpaceshipMusicTable.json",
    "SpaceshipAlbumMusicTable.json",
)
AUDIO_TABLE_NAMES = tuple(dict.fromkeys((*NARRATIVE_AUDIO_TABLE_NAMES, *AUDIO_CONFIG_TABLE_NAMES)))
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
AUDIO_HASH_FIELD_RE = re.compile(
    r"(?:^audio[A-Z_]|(?:Audio|Music)?Event(?:s|Ids?)?$|levelInitEvent$|battleMusicTriggerEvent$)",
    re.IGNORECASE,
)

# HIRC type numbers follow the object-family layout observed in the current
# Endfield banks.  The event payload preserves the raw numeric type as the
# authoritative value; these names are presentation labels, not a claim that
# selection behavior was evaluated offline.
HIRC_OBJECT_TYPE_LABELS = {
    2: "sound",
    3: "action",
    4: "event",
    5: "randomSequenceContainer",
    6: "switchContainer",
    7: "actorMixer",
    9: "layer",
    10: "musicSegment",
    11: "musicTrack",
    12: "musicSwitchContainer",
    13: "musicRandomSequenceContainer",
}
SELECTION_HIRC_TYPES = frozenset({5, 6, 12, 13})
AUDIO_SEMANTIC_SCHEMA_VERSION = 44
TRIGGER_CONTEXT_SCHEMA_VERSION = 5
RUNTIME_MODEL_CACHE_SCHEMA_VERSION = 15
RADIO_MEDIA_CONTEXT_LIMIT = 64
RADIO_MEDIA_SEARCH_LIMIT = 96
RADIO_CATALOG_ITEM_LIMIT = 64
MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)

# These are static managed-metadata surfaces for the string-key Timeline
# event carriers.  They describe the methods and serialized controls that can
# consume a clip; they do not claim that a Director evaluated the clip or that
# Wwise received a PostEvent.  Keep the full contract in the compact index
# coverage and attach only the stable id to each occurrence.
TIMELINE_AUDIO_RUNTIME_CONTRACTS = {
    "AudioDlgEventPlayable": {
        "id": "timelineStringEventKey.audioDlg",
        "type": "Beyond.Audio.AudioDlgEventPlayable",
        "behaviourType": "Beyond.Audio.AudioDlgEventPlayableBehaviour",
        "assetToken": "0x02000102",
        "behaviourToken": "0x02000101",
        "requestMethods": [
            {"name": "OnManualFixBehaviourPlay", "token": "0x06000612"},
            {"name": "ShouldPlay", "token": "0x06000617"},
            {"name": "_DoPlayEvent", "token": "0x06000619"},
        ],
        "stopMethods": [
            {"name": "OnManualFixBehaviourPause", "token": "0x06000613"},
            {"name": "OnGraphStop", "token": "0x06000614"},
            {"name": "_DoPlayStopEvent", "token": "0x0600061a"},
            {"name": "_TryStop", "token": "0x0600061c"},
        ],
        "seekMethods": [
            {"name": "MarkForStop", "token": "0x0600060f"},
            {"name": "_TrySeek", "token": "0x06000618"},
        ],
        "serializedControls": [
            "_audioEventKey", "_isCue", "_stopEventAtClipEnd",
            "_stopEventAtClipEndKey", "_fadeOutTime", "_enableSeek",
            "_useBindingObj", "_is2D", "_emitter",
        ],
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
    "AudioEventPlayable": {
        "id": "timelineStringEventKey.audioEvent",
        "type": "Beyond.Audio.AudioEventPlayable",
        "behaviourType": "Beyond.Audio.AudioEventPlayableBehaviour",
        "assetToken": "0x02000104",
        "behaviourToken": "0x02000103",
        "requestMethods": [
            {"name": "OnBehaviourPlay", "token": "0x0600062b"},
            {"name": "ShouldPlay", "token": "0x06000630"},
            {"name": "_DoPlayEvent", "token": "0x06000632"},
        ],
        "stopMethods": [
            {"name": "OnBehaviourPause", "token": "0x0600062c"},
            {"name": "OnGraphStop", "token": "0x0600062d"},
            {"name": "_TryPostExitEvent", "token": "0x06000634"},
            {"name": "_TryStop", "token": "0x06000635"},
        ],
        "seekMethods": [
            {"name": "MarkSkip", "token": "0x06000628"},
            {"name": "_TrySeek", "token": "0x06000631"},
        ],
        "serializedControls": [
            "_audioEventKey", "_stopEventAtClipEnd", "_fadeOutWhenStop",
            "_fadeOutTime", "_enableSeek", "_useBindingObj", "_is2D",
            "_emitter", "_exitAudioEvent",
        ],
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
    "AudioMusicPlayable": {
        "id": "timelineMusicEventKey.audioMusic",
        "type": "Beyond.Gameplay.Audio.AudioMusicPlayable",
        "behaviourType": "Beyond.Gameplay.Audio.AudioMusicPlayableBehaviour",
        "assetToken": "0x02001abc",
        "behaviourToken": "0x02001abb",
        "requestMethods": [
            {"name": "OnBehaviourPlay", "token": "0x06009c63"},
            {"name": "_ShouldPlay", "token": "0x06009c66"},
            {"name": "_TriggerEvent", "token": "0x06009c67"},
        ],
        "skipMethods": [
            {"name": "OnTimelineSkip", "token": "0x06009c62"},
        ],
        "serializedControls": [
            "_audioEventKey", "musicActionType", "triggerOnSkip",
        ],
        "behaviourStateFields": [
            "eventKey", "musicActionType", "triggerOnSkip",
            "m_isMusicEventTriggered", "m_requiredActions",
        ],
        "serializedControlValueLabels": {
            "musicActionType": {
                "0": "DIALOG_MUSIC",
                "1": "NORMAL_MUSIC",
                "2": "CUSTOM_MUSIC",
            },
            "triggerOnSkip": {
                "0": "notTriggeredOnSkip",
                "1": "triggeredOnSkip",
            },
        },
        "controlValueEvidence": (
            "musicActionType labels match the current metadata enum "
            "Beyond.Gameplay.Core.DialogMusicAction+EDialogMusicActionType; "
            "triggerOnSkip is serialized as a current bool field"
        ),
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
}

AUDIO_MUSIC_ACTION_TYPE_LABELS = {
    0: "DIALOG_MUSIC",
    1: "NORMAL_MUSIC",
    2: "CUSTOM_MUSIC",
}
AUDIO_MUSIC_TRIGGER_ON_SKIP_LABELS = {
    0: "notTriggeredOnSkip",
    1: "triggeredOnSkip",
}

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

CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD = 0.5
CUSTOM_FOOTSTEP_SIDE_VALUES = {0x00: "Left", 0x01: "Right", 0x03: "Invalid"}
CUSTOM_FOOTSTEP_VFX_VALUES = {0x00: "None", 0x04: "Step", 0x08: "Jump", 0x0C: "Land"}
CUSTOM_FOOTSTEP_FILTER_VALUES = {
    0x00: "IsMaxWeight",
    0x20: "IsComposeMaxWeight",
    0x40: "CustomWeight",
    0xE0: "ForcePlay",
}
CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
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


def decode_custom_footstep_parameters(raw_int: Any, raw_float: Any) -> dict[str, Any] | None:
    """Decode the exact current-build OnCustomFootStep packed parameters."""

    if isinstance(raw_int, bool) or not isinstance(raw_int, int):
        return None
    if isinstance(raw_float, bool) or not isinstance(raw_float, (int, float)):
        return None
    float_value = float(raw_float)
    if not math.isfinite(float_value):
        return None
    side_bits = raw_int & 0x03
    vfx_bits = raw_int & 0x1C
    filter_bits = raw_int & 0xE0
    foot_side = CUSTOM_FOOTSTEP_SIDE_VALUES.get(side_bits)
    vfx_type = CUSTOM_FOOTSTEP_VFX_VALUES.get(vfx_bits)
    playback_filter = CUSTOM_FOOTSTEP_FILTER_VALUES.get(filter_bits)
    exact = all(value is not None for value in (foot_side, vfx_type, playback_filter))
    is_custom_weight = playback_filter == "CustomWeight"
    return {
        "rawInt": raw_int,
        "rawFloat": float_value,
        "footSide": foot_side or f"Unknown(0x{side_bits:02x})",
        "vfxType": vfx_type or f"Unknown(0x{vfx_bits:02x})",
        "playbackFilter": playback_filter or f"Unknown(0x{filter_bits:02x})",
        "customWeightThreshold": float_value if is_custom_weight else None,
        "runtimeVfxWeightThreshold": CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD,
        "inactiveFloat": not is_custom_weight,
        "floatParameterStatus": (
            "customWeightThreshold" if is_custom_weight else "inactiveForPlaybackFilter"
        ),
        "decodeStatus": "exactCurrentBuild" if exact else "unsupportedMaskedValue",
    }


def aggregate_custom_footstep_parameter_variants(
    evidence_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Count exact callback parameter variants without retaining every clip row."""

    counts: Counter[tuple[int, float]] = Counter()
    for evidence in evidence_rows:
        if not isinstance(evidence, dict) or evidence.get("function") != "OnCustomFootStep":
            continue
        decoded = decode_custom_footstep_parameters(
            evidence.get("intParameter"), evidence.get("floatParameter")
        )
        if decoded is None:
            continue
        counts[(decoded["rawInt"], decoded["rawFloat"])] += 1
    variants = []
    for (raw_int, raw_float), occurrence_count in sorted(counts.items()):
        decoded = decode_custom_footstep_parameters(raw_int, raw_float)
        assert decoded is not None
        variants.append({**decoded, "occurrenceCount": occurrence_count})
    return variants


def aggregate_custom_footstep_context_variants(
    contexts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: Counter[tuple[int, float]] = Counter()
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for variant in context.get("customFootstepParameterVariants") or []:
            decoded = decode_custom_footstep_parameters(
                variant.get("rawInt"), variant.get("rawFloat")
            )
            if decoded is None:
                continue
            counts[(decoded["rawInt"], decoded["rawFloat"])] += int(
                variant.get("occurrenceCount") or 0
            )
    variants = []
    for (raw_int, raw_float), occurrence_count in sorted(counts.items()):
        decoded = decode_custom_footstep_parameters(raw_int, raw_float)
        assert decoded is not None
        variants.append({**decoded, "occurrenceCount": occurrence_count})
    return variants


def runtime_spec(
    type_name: str,
    layer: str,
    meaning: str,
    *,
    fields: Iterable[str] = (),
    methods: Iterable[str] = (),
    enum_values: bool = False,
    serialized_layout: dict[str, Any] | None = None,
    native_anchors: Iterable[dict[str, Any]] = (),
    native_call_chains: Iterable[dict[str, Any]] = (),
    native_state_groups: Iterable[dict[str, Any]] = (),
    native_state_transitions: Iterable[dict[str, Any]] = (),
    runtime_execution_status: str = "",
) -> dict[str, Any]:
    row = {
        "type": type_name,
        "layer": layer,
        "meaning": meaning,
        "fields": tuple(fields),
        "methods": tuple(methods),
        "enumValues": enum_values,
    }
    if serialized_layout:
        row["serializedLayout"] = dict(serialized_layout)
    if native_anchors:
        row["nativeAnchors"] = tuple(dict(value) for value in native_anchors)
    if native_call_chains:
        row["nativeCallChains"] = tuple(dict(value) for value in native_call_chains)
    if native_state_groups:
        row["nativeStateGroups"] = tuple(dict(value) for value in native_state_groups)
    if native_state_transitions:
        row["nativeStateTransitions"] = tuple(
            dict(value) for value in native_state_transitions
        )
    if runtime_execution_status:
        row["runtimeExecutionStatus"] = runtime_execution_status
    return row


def native_playback_stage(
    role: str,
    type_name: str,
    method: str,
    method_index: int | None,
    token: str,
    virtual_address: str,
    relation: str,
) -> dict[str, Any]:
    row = {
        "role": role,
        "type": type_name,
        "method": method,
        "token": token,
        "virtualAddress": virtual_address,
        "relation": relation,
    }
    if method_index is not None:
        row["methodIndex"] = method_index
    return row


AUDIO_MUSIC_NATIVE_STATE_GROUPS = (
    {
        "role": "topLevelMusicMode",
        "field": "MUSIC_STATE_GROUP_ID",
        "groupId": 0xE414D158,
        "groupIdHex": "0xe414d158",
        "recoveredName": "music_state",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicState",
        "setterMethod": "_SetWwiseMusicState",
        "methodIndex": 39631,
        "token": "0x06009ad0",
        "virtualAddress": "0x183a0cb00",
    },
    {
        "role": "worldMap",
        "field": "MUSIC_MAP_STATE_GROUP_ID",
        "groupId": 0xB3D78A5D,
        "groupIdHex": "0xb3d78a5d",
        "recoveredName": "music_map",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicMapState",
        "setterMethod": "_SetWwiseMusicMapState",
        "methodIndex": 39634,
        "token": "0x06009ad3",
        "virtualAddress": "0x186adc08c",
    },
    {
        "role": "battlePhase",
        "field": "BATTLE_MUSIC_STATE_GROUP_ID",
        "groupId": 0x4D9E8C28,
        "groupIdHex": "0x4d9e8c28",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicState",
        "setterMethod": "_SetWwiseBattleMusicState",
        "methodIndex": 39636,
        "token": "0x06009ad5",
        "virtualAddress": "0x1846ab390",
    },
    {
        "role": "battleIntensity",
        "field": "BATTLE_MUSIC_INTENSITY_STATE_GROUP_ID",
        "groupId": 0x2560A0EE,
        "groupIdHex": "0x2560a0ee",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicIntensityState",
        "setterMethod": "_SetWwiseBattleMusicIntensityState",
        "methodIndex": 39638,
        "token": "0x06009ad7",
        "virtualAddress": "0x183a0ca90",
    },
    {
        "role": "mission",
        "field": "MISSION_MUSIC_STATE_GROUP_ID",
        "groupId": 0x3B650E3D,
        "groupIdHex": "0x3b650e3d",
        "recoveredName": "music_mission",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMissionMusicState",
        "setterMethod": "_SetWwiseMissionMusicState",
        "methodIndex": 39640,
        "token": "0x06009ad9",
        "virtualAddress": "0x186adc004",
    },
    {
        "role": "dialog",
        "field": "DIALOG_MUSIC_STATE_GROUP_ID",
        "groupId": 0xA4C62908,
        "groupIdHex": "0xa4c62908",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseDialogMusicState",
        "setterMethod": "_SetWwiseDialogMusicState",
        "methodIndex": 39642,
        "token": "0x06009adb",
        "virtualAddress": "0x186adbef4",
    },
    {
        "role": "cutscene",
        "field": "CUTSCENE_MUSIC_STATE_GROUP_ID",
        "groupId": 0x75C98B29,
        "groupIdHex": "0x75c98b29",
        "recoveredName": "music_cutscene",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseCutsceneMusicState",
        "setterMethod": "_SetWwiseCutsceneMusicState",
        "methodIndex": 39644,
        "token": "0x06009add",
        "virtualAddress": "0x186adbe6c",
    },
    {
        "role": "login",
        "field": "LOGIN_MUSIC_STATE_GROUP_ID",
        "groupId": 0x6401EC38,
        "groupIdHex": "0x6401ec38",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseLoginMusicState",
        "setterMethod": "_SetWwiseLoginMenuMusicState",
        "methodIndex": 39646,
        "token": "0x06009adf",
        "virtualAddress": "0x186adbf7c",
    },
    {
        "role": "meta",
        "field": "META_MUSIC_STATE_GROUP_ID",
        "groupId": 0x654423EE,
        "groupIdHex": "0x654423ee",
        "recoveredName": "music_meta",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMetaMusicState",
        "setterMethod": "_SetWwiseMetaMusicState",
        "methodIndex": 39648,
        "token": "0x06009ae1",
        "virtualAddress": "0x184491300",
    },
    {
        "role": "remoteCommunication",
        "field": "REMOTE_COMM_MUSIC_STATE_GROUP_ID",
        "groupId": 0xC52AA6BC,
        "groupIdHex": "0xc52aa6bc",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseRemoteCommMusicState",
        "setterMethod": "_SetWwiseRemoteCommMusicState",
        "methodIndex": 39650,
        "token": "0x06009ae3",
        "virtualAddress": "0x186adc19c",
    },
)


# The enum member names below are not display guesses.  They are the managed
# names recovered from the current Gameplay.Beyond metadata and their value
# ids are the exact FNV-1/UTF-16 hashes used by AudioHashGenerator.Compute.
# Keeping the enum member, hash input, and id together makes the distinction
# between a state *group* and a state *value* explicit in the WebUI catalog.
_AUDIO_MUSIC_ENUM_VALUES = {
    "topLevelMusicMode": (
        ("UNKNOWN", 0xF9D3523D),
        ("MISSION", 0x166521A5),
        ("LOADING", 0xD505DEBB),
        ("EXPLORING", 0x6CB31EE7),
        ("COMBAT_GENERAL", 0x525E00A0),
        ("COMBAT_BOSS", 0x271CB603),
        ("CUTSCENE", 0x468283E1),
        ("DIALOGUE", 0xEA41209F),
        ("FACTORY", 0x51FBB249),
        ("BASE_MODE_DEFENSE", 0x00FC4659),
        ("DUNGEON", 0x244B0EC9),
        ("NARRATING", 0x36752FA3),
    ),
    "worldMap": (
        ("UNKNOWN", 0xF9D3523D),
        ("TUNDRA", 0x9B54723D),
        ("HONGSHAN", 0xFF51B103),
    ),
    "battlePhase": (
        ("UNKNOWN", 0xF9D3523D),
        ("MAIN_LOOP", 0xE34AF54B),
        ("ENDING", 0xEC675524),
    ),
    "battleIntensity": (
        ("UNKNOWN", 0xF9D3523D),
        ("LOW", 0x2081B4E5),
        ("HIGH", 0xD3A50981),
    ),
    "mission": (("NONE", 0x2CA33BDB),),
    "dialog": (("NONE", 0x2CA33BDB),),
    "cutscene": (("NONE", 0x2CA33BDB),),
    "login": (
        ("NONE", 0x2CA33BDB),
        ("INTRO", 0x4315C729),
        ("THEME", 0x4E9E9BB0),
        ("ENDING", 0xEC675524),
    ),
    "meta": (
        ("NONE", 0x2CA33BDB),
        ("GACHA_CUTSCENE", 0x73A7133C),
        ("GACHA_INTERFACE", 0x854CEF1D),
    ),
    "remoteCommunication": (
        ("NONE", 0x2CA33BDB),
        ("LOOP", 0x292FEA37),
        ("ENDING", 0xEC675524),
    ),
}


def _audio_music_enum_value(member: str, value_id: int) -> dict[str, Any]:
    return {
        "member": member,
        "hashInput": member.lower(),
        "valueId": value_id,
        "valueIdHex": f"0x{value_id:08x}",
        "resolution": "exactCurrentMetadataEnumMemberFNV1Utf16Hash",
    }


# These are exact immediate values observed at current GameAssembly callsites.
# ManualSet* is intentionally separate: its EBX/EDX input is supplied by the
# caller at runtime, so the binary proves the route but not a fixed value.
_AUDIO_MUSIC_STATIC_VALUE_CALLSITES = {
    "topLevelMusicMode": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab06f",
            "valueMember": "COMBAT_GENERAL",
            "valueId": 0x525E00A0,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "OnEnterMainGame",
            "callerMethodIndex": 39513,
            "callVirtualAddress": "0x18449113e",
            "valueMember": "LOADING",
            "valueId": 0xD505DEBB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_TurnToLoadingIfInLoading",
            "callerMethodIndex": 39581,
            "callVirtualAddress": "0x186adc919",
            "valueMember": "LOADING",
            "valueId": 0xD505DEBB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "SwitchToDialogMusic",
            "callerMethodIndex": 39590,
            "callVirtualAddress": "0x186ad9f58",
            "valueMember": "DIALOGUE",
            "valueId": 0xEA41209F,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "worldMap": (
        {
            "callerMethod": None,
            "callerMethodIndex": None,
            "callVirtualAddress": "0x18538585d",
            "valueMember": "TUNDRA",
            "valueId": 0x9B54723D,
            "valueRegister": "edx",
            "ownerResolution": "unresolvedSharedGenericBody",
            "ownerGap": "Direct call target and immediate value are exact; the shared/generated body has no safe metadata owner join.",
        },
    ),
    "battlePhase": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab05f",
            "valueMember": "MAIN_LOOP",
            "valueId": 0xE34AF54B,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "battleIntensity": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab04f",
            "valueMember": "HIGH",
            "valueId": 0xD3A50981,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_CheckLeaveFight",
            "callerMethodIndex": 39486,
            "callVirtualAddress": "0x183a0d06c",
            "valueMember": "LOW",
            "valueId": 0x2081B4E5,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_OnEscapeFromFight",
            "callerMethodIndex": 39491,
            "callVirtualAddress": "0x186adb46c",
            "valueMember": "LOW",
            "valueId": 0x2081B4E5,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "dialog": (
        {
            "callerMethod": "SwitchToDialogMusic",
            "callerMethodIndex": 39590,
            "callVirtualAddress": "0x186ad9f2a",
            "valueMember": "NONE",
            "valueId": 0x2CA33BDB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "remoteCommunication": (
        {
            "callerMethod": "EndRemoteComm",
            "callerMethodIndex": 39599,
            "callVirtualAddress": "0x186ad8240",
            "valueMember": "ENDING",
            "valueId": 0xEC675524,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
}


_AUDIO_MUSIC_RUNTIME_VALUE_CALLSITES = {
    "topLevelMusicMode": (
        {
            "callerMethod": "ManualSetMusicState",
            "callerMethodIndex": 39582,
            "callVirtualAddress": "0x186ad890f",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
    "battlePhase": (
        {
            "callerMethod": "ManualSetBattleMusicState",
            "callerMethodIndex": 39583,
            "callVirtualAddress": "0x186ad88a7",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
    "battleIntensity": (
        {
            "callerMethod": "ManualSetBattleMusicIntensityState",
            "callerMethodIndex": 39584,
            "callVirtualAddress": "0x186ad883f",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
}


AUDIO_MUSIC_NATIVE_STATE_GROUPS = tuple(
    {
        **row,
        "values": tuple(
            _audio_music_enum_value(member, value_id)
            for member, value_id in _AUDIO_MUSIC_ENUM_VALUES[row["role"]]
        ),
        "staticValueCallsites": tuple(
            dict(value) for value in _AUDIO_MUSIC_STATIC_VALUE_CALLSITES.get(row["role"], ())
        ),
        "runtimeValueCallsites": tuple(
            dict(value) for value in _AUDIO_MUSIC_RUNTIME_VALUE_CALLSITES.get(row["role"], ())
        ),
        "binaryEvidence": {
            "status": "exactCurrentBuildStaticEvidence",
            "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
            "metadataSha256": MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256,
        },
    }
    for row in AUDIO_MUSIC_NATIVE_STATE_GROUPS
)


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


AUDIO_MUSIC_NATIVE_TRANSITION_REGISTRATIONS = (
    {
        "stateMask": 0x00000040,
        "stateMaskHex": "0x00000040",
        "stateNames": ("FMV",),
        "registrationCallOffsets": ("0x1d3", "0x28f"),
    },
    {
        "stateMask": 0x00000080,
        "stateMaskHex": "0x00000080",
        "stateNames": ("CUT_SCENE",),
        "registrationCallOffsets": ("0x345", "0x401"),
    },
    {
        "stateMask": 0x00000100,
        "stateMaskHex": "0x00000100",
        "stateNames": ("TRANSITION_CUT_SCENE",),
        "registrationCallOffsets": ("0x4b7", "0x573"),
    },
    {
        "stateMask": 0x00000200,
        "stateMaskHex": "0x00000200",
        "stateNames": ("DIALOG",),
        "registrationCallOffsets": ("0x629", "0x6e5"),
    },
    {
        "stateMask": 0x00000400,
        "stateMaskHex": "0x00000400",
        "stateNames": ("REMOTE_COMM",),
        "registrationCallOffsets": ("0x79b", "0x857"),
    },
    {
        "stateMask": 0x02000000,
        "stateMaskHex": "0x02000000",
        "stateNames": ("LOADING",),
        "registrationCallOffsets": ("0x90d", "0x9c9"),
    },
    {
        "stateMask": 0x04000000,
        "stateMaskHex": "0x04000000",
        "stateNames": ("TELEPORT_LOADING",),
        "registrationCallOffsets": ("0xa7f", "0xb3b"),
    },
    {
        "stateMask": 0x000C0000,
        "stateMaskHex": "0x000c0000",
        "stateNames": ("IN_FACTORY_AREA", "IN_BLACKBOX"),
        "registrationCallOffsets": ("0xbf1", "0xcad"),
    },
    {
        "stateMask": 0x00000002,
        "stateMaskHex": "0x00000002",
        "stateNames": ("FIGHT",),
        "registrationCallOffsets": ("0xd63", "0xe1f"),
    },
)

def _native_transition_callback(
    call_offset: str,
    action_order: int,
    condition_type_raw: int,
    metadata_usage_raw: str,
    method: str,
    method_index: int,
    token: str,
    virtual_address: str,
    *,
    direct_state_setters: Iterable[str] = (),
) -> dict[str, Any]:
    row = {
        "registrationCallOffset": call_offset,
        "actionOrder": action_order,
        "conditionTypeRaw": condition_type_raw,
        "conditionType": "enter" if condition_type_raw == 0 else "leave",
        "metadataUsageRaw": metadata_usage_raw,
        "callbackMethod": method,
        "callbackMethodIndex": method_index,
        "callbackToken": token,
        "callbackVirtualAddress": virtual_address,
        "callbackEvidence": "exactMetadataUsageDelegateTarget",
    }
    if direct_state_setters:
        row["directStateSetters"] = tuple(direct_state_setters)
    return row


_AUDIO_MUSIC_TRANSITION_CALLBACKS = {
    0x00000040: (
        _native_transition_callback(
            "0x1d3", 5, 0, "0x6001354f", "SwitchToDialogMusic", 39590,
            "0x06009aa7", "0x186ad9e74",
            direct_state_setters=("_SetWwiseDialogMusicState", "_SetWwiseMusicState"),
        ),
        _native_transition_callback(
            "0x28f", 1, 1, "0x60013551", "_OnEnterFMV", 39591,
            "0x06009aa8", "0x186adb2e4",
        ),
    ),
    0x00000080: (
        _native_transition_callback(
            "0x345", 5, 0, "0x60013553", "_OnLeaveFMV", 39592,
            "0x06009aa9", "0x186adb5ac",
        ),
        _native_transition_callback(
            "0x401", 1, 1, "0x60013555", "_OnEnterCutscene", 39593,
            "0x06009aaa", "0x186adb204",
        ),
    ),
    0x00000100: (
        _native_transition_callback(
            "0x4b7", 5, 0, "0x60013553", "_OnLeaveFMV", 39592,
            "0x06009aa9", "0x186adb5ac",
        ),
        _native_transition_callback(
            "0x573", 1, 1, "0x60013555", "_OnEnterCutscene", 39593,
            "0x06009aaa", "0x186adb204",
        ),
    ),
    0x00000200: (
        _native_transition_callback(
            "0x629", 5, 0, "0x60013557", "_OnLeaveCutscene", 39594,
            "0x06009aab", "0x186adb4e4",
        ),
        _native_transition_callback(
            "0x6e5", 1, 1, "0x60013559", "_OnEnterDialog", 39595,
            "0x06009aac", "0x186adb274",
        ),
    ),
    0x00000400: (
        _native_transition_callback(
            "0x79b", 5, 0, "0x6001355b", "_OnLeaveDialog", 39596,
            "0x06009aad", "0x186adb548",
        ),
        _native_transition_callback(
            "0x857", 1, 1, "0x6001355d", "_OnEnterRemoteComm", 39597,
            "0x06009aae", "0x186adb354",
        ),
    ),
    0x02000000: (
        _native_transition_callback(
            "0x90d", 5, 0, "0x60013533", "_CancelScheduledAutoRestoreMusicState", 39576,
            "0x06009a99", "0x183a0ced0",
        ),
        _native_transition_callback(
            "0x9c9", 1, 1, "0x60013535", "_OnEnterLoading", 39577,
            "0x06009a9a", "0x183a0c910",
        ),
    ),
    0x04000000: (
        _native_transition_callback(
            "0xa7f", 5, 0, "0x60013537", "_OnLeaveLoading", 39578,
            "0x06009a9b", "0x183a0c800",
        ),
        _native_transition_callback(
            "0xb3b", 1, 1, "0x60013539", "_OnEnterTeleportLoading", 39579,
            "0x06009a9c", "0x184ca4f60",
        ),
    ),
    0x000C0000: (
        _native_transition_callback(
            "0xbf1", 5, 0, "0x6001351b", "_CleanMusicEventDebugHUD", 39564,
            "0x06009a8d", "0x186ada6c8",
        ),
        _native_transition_callback(
            "0xcad", 1, 1, "0x6001351f", "_SwitchToFactoryMusic", 39566,
            "0x06009a8f", "0x184d27690",
        ),
    ),
    0x00000002: (
        _native_transition_callback(
            "0xd63", 5, 0, "0x60013471", "_ClearBattleMusicTimers", 39479,
            "0x06009a38", "0x183a0cc70",
        ),
        _native_transition_callback(
            "0xe1f", 1, 1, "0x60013479", "_StartBattleMusic", 39483,
            "0x06009a3c", "0x1846aafc0",
            direct_state_setters=(
                "_SetWwiseBattleMusicIntensityState", "_SetWwiseBattleMusicState",
                "_SetWwiseMusicState",
            ),
        ),
    ),
}

for _transition_registration in AUDIO_MUSIC_NATIVE_TRANSITION_REGISTRATIONS:
    _registrations = _AUDIO_MUSIC_TRANSITION_CALLBACKS[
        _transition_registration["stateMask"]
    ]
    _transition_registration.update({
        "registrationMethod": "_RegisterStateTransitionActions",
        "registrationMethodIndex": 39571,
        "registrationToken": "0x06009a94",
        "registrationVirtualAddress": "0x183a0d940",
        "registerMethodIndex": 39810,
        "registerToken": "0x06009b83",
        "registerVirtualAddress": "0x183a0e800",
        "registrationCount": len(_registrations),
        "actionOrders": tuple(row["actionOrder"] for row in _registrations),
        "isOneShot": False,
        "conditionInterpretationStatus": "exactSimpleConditionNativeBody",
        "stateNameEvidence": "exactEAudioStateEnumValueMatch",
        "callbackTargetStatus": "exactMetadataUsageDelegateTargets",
        "runtimeObservationStatus": "staticRegistrationNotLiveStateTrace",
        "registrations": _registrations,
    })


AUDIO_PLAYBACK_NATIVE_CALL_CHAINS = {
    "adapterPost": {
        "id": "adapterPostEventToWwise",
        "label": "Event request -> Event bank/cache preparation -> Wwise PostEvent",
        "evidence": "exactCurrentGameAssemblyDirectCallsAndSharedNativeFunctionPointer",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeCallChainNotLivePlaybackTrace",
        "stages": (
            native_playback_stage(
                "request",
                "Beyond.Audio.AudioAdapter",
                "PostEvent(string)",
                479923,
                "0x06000008",
                "0x1846d3f80",
                "Hashes the authored name with AudioHashGenerator.Compute and enters _PostEvent.",
            ),
            native_playback_stage(
                "prepare",
                "Beyond.Audio.AudioAdapter",
                "_PostEvent",
                480010,
                "0x0600005f",
                "0x18328a690",
                "Allocates an internal playing id and payload, then requests Event-owned resources.",
            ),
            native_playback_stage(
                "loadRequest",
                "Beyond.Audio.AudioAssetHelper",
                "_DoLoadEventAsync",
                480201,
                "0x0600011e",
                "0x18328afb0",
                "Tests the Event cache, then enters the Event-id bank load path only when activation returns false.",
            ),
            native_playback_stage(
                "cache",
                "Beyond.Audio.AudioAssetCache",
                "ActivateAsset",
                480175,
                "0x06000104",
                "0x18328ac60",
                "Tests and activates the Event-owned cached resource before any bank load is requested.",
            ),
            native_playback_stage(
                "eventBank",
                "AkSoundEngine",
                "LoadBank(uint, callback, cookie, bankType)",
                446458,
                "0x06000a74",
                "0x183eb0c60",
                "Loads the Event-id bank asynchronously; this path is separate from AudioBankManager's named BankHandle registry.",
            ),
            native_playback_stage(
                "bankCallback",
                "Beyond.Audio.AudioAssetHelper",
                "_OnBankLoadedDoPrepareEvent",
                480211,
                "0x06000128",
                "0x183eb0a70",
                "For the prepare branch, submits exactly one Event id to AkSoundEngine.PrepareEvent with raw preparation type 0.",
            ),
            native_playback_stage(
                "prepareEvent",
                "AkSoundEngine",
                "PrepareEvent(preparationType, eventIds, count, callback, cookie)",
                446489,
                "0x06000a93",
                "0x183eb0bd0",
                "Receives raw preparation type 0, the reusable one-id array, count 1, and the completion callback.",
            ),
            native_playback_stage(
                "prepareDone",
                "Beyond.Audio.AudioAssetHelper",
                "_OnDonePrepareEvent",
                480212,
                "0x06000129",
                "0x183eb0e80",
                "Returns the completed preparation to the waiting Event callback queue.",
            ),
            native_playback_stage(
                "completion",
                "Beyond.Audio.AudioAssetHelper",
                "_TryDequeueAndInvokeCallback",
                480213,
                "0x0600012a",
                "0x18328cf20",
                "Invokes the waiting adapter completion or releases the cached Event and unloads its Event bank on failure/cleanup paths.",
            ),
            native_playback_stage(
                "post",
                "Beyond.Audio.AudioAdapter",
                "_OnEventPreparedDoPostEvent",
                480007,
                "0x0600005c",
                "0x18328c670",
                "Uses native function-pointer slot 0x18f361158 and records internal-to-real playing-id state.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "PostEvent(uint, ulong, flags, callback, cookie)",
                446377,
                "0x06000a23",
                "0x18328c940",
                "Uses the same 0x18f361158 native PostEvent slot and returns the real Wwise playing id.",
            ),
            native_playback_stage(
                "callbackPump",
                "AkCallbackManager",
                "PostCallbacks",
                446952,
                "0x06000c62",
                "0x18328b440",
                "Pumps queued native Wwise callbacks into the managed callback dispatcher.",
            ),
            native_playback_stage(
                "callbackDispatch",
                "AkCallbackManager",
                "_ProcessEventCallback",
                446954,
                "0x06000c64",
                "0x18328cd90",
                "Dispatches callback payload classes by the exact AkCallbackType bit before invoking the adapter callback.",
            ),
            native_playback_stage(
                "callback",
                "Beyond.Audio.AudioAdapter",
                "_OnEventCallback",
                480008,
                "0x0600005d",
                "0x18328d3e0",
                "Handles the dispatched callback; raw callback type 1 is the exact EndOfEvent branch.",
            ),
            native_playback_stage(
                "release",
                "Beyond.Audio.AudioAssetCache",
                "DeactivateAsset",
                480176,
                "0x06000105",
                "0x18328a390",
                "On the callback path gated by raw callback type 1, decrements the Event cache refCount; zero remains pinned or moves toward LRU release.",
            ),
        ),
        "branches": (
            {
                "id": "activatedCache",
                "label": "ActivateAsset returned true",
                "relation": (
                    "The native body tests the solid-loaded Event set and can dequeue the waiting callback "
                    "without entering the LoadBank/PrepareEvent miss path."
                ),
            },
            {
                "id": "eventBankMiss",
                "label": "ActivateAsset returned false",
                "relation": (
                    "The native body calls LoadBank(eventId, callback, null, 0x1e); the bank callback then "
                    "either prepares the one Event id or releases the cache entry and forwards completion."
                ),
            },
            {
                "id": "callbackPayloadCapabilities",
                "label": "Managed Wwise callback payloads",
                "relation": (
                    "The current bridge dispatches EndOfEvent, DynamicSequenceItem, Marker, Duration, "
                    "MusicPlaylistSelect, MusicPlayStarted, MusicSync Beat/Bar/Entry/Exit/Grid/UserCue/Point, "
                    "and MIDIEvent. Callback-info accessors can expose playingID/eventID, duration mediaID/"
                    "audioNodeID, playlist selection, and music-sync type; no live callback sample is captured."
                ),
            },
        ),
        "boundary": (
            "The binary proves the cache/miss branch, Event-id bank load, one-Event PrepareEvent call, "
            "completion callback, Wwise Event post, callback dispatch, playing-id mapping, and EndOfEvent-gated cache deactivation. "
            "It does not prove which branch ran for a captured request, which optional callback types were requested, live switch/state/"
            "RTPC values, or the selected Wwise media leaf."
        ),
    },
    "externalSource": {
        "id": "externalSourcePostToWwise",
        "label": "External file Event request -> Wwise external-source post -> EndOfEvent cleanup",
        "evidence": "exactCurrentGameAssemblyDirectCallsAndDistinctNativeFunctionPointer",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeCallChainNotLivePlaybackTrace",
        "stages": (
            native_playback_stage(
                "request",
                "Beyond.Audio.AudioAdapter",
                "PostEventExternal",
                479931,
                "0x06000010",
                "0x183abf0a0",
                "Accepts an Event plus an external file source and enters the dedicated external-source path.",
            ),
            native_playback_stage(
                "prepareExternal",
                "Beyond.Audio.AudioAdapter",
                "_PostEventWithExternalSource",
                480011,
                "0x06000060",
                "0x183abea70",
                "Builds AkExternalSourceInfo and keeps an external playing/object cleanup mapping.",
            ),
            native_playback_stage(
                "externalCookie",
                "AkExternalSourceInfo",
                "set_iExternalSrcCookie",
                444124,
                "0x06000156",
                "0x183abe910",
                "Sets the authored external-source cookie separately from the Event id.",
            ),
            native_playback_stage(
                "externalFile",
                "AkExternalSourceInfo",
                "set_szFile",
                444128,
                "0x0600015a",
                "0x183abe850",
                "Sets the external audio file path.",
            ),
            native_playback_stage(
                "externalCodec",
                "AkExternalSourceInfo",
                "set_idCodec",
                444126,
                "0x06000158",
                "0x183abe9c0",
                "Sets the codec id used by the external source.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "PostEvent external-source overload",
                446376,
                "0x06000a22",
                "0x183abed90",
                "Crosses dedicated native slot 0x18f361150; ordinary Event posting uses 0x18f361158.",
            ),
            native_playback_stage(
                "callback",
                "Beyond.Audio.AudioAdapter",
                "_OnExternalSourceEventCallback",
                480009,
                "0x0600005e",
                "0x1843c7930",
                "Reads gameObjID and cookie; raw callback type 1 removes the external mapping and starts cleanup.",
            ),
            native_playback_stage(
                "dispose",
                "Beyond.Gameplay.Audio.AudioObject",
                "Dispose",
                39041,
                "0x06009882",
                "0x183765ef0",
                "Disposes the temporary external audio object on the recovered cleanup path.",
            ),
            native_playback_stage(
                "releaseObject",
                "Beyond.Gameplay.Audio.AudioObjectIdDispatcher",
                "ReleaseAudioGameObject",
                39052,
                "0x0600988d",
                "0x183ce31d0",
                "Releases the temporary Wwise game-object identity.",
            ),
        ),
        "boundary": (
            "The external file/cookie/codec route and EndOfEvent cleanup are exact and use a different native PostEvent slot from ordinary "
            "Event media. No current live request, external filename, returned playing id, or decoded external-file content was observed."
        ),
    },
    "playingIdAction": {
        "id": "playingIdActionQueueToWwise",
        "label": "Stop / pause / resume -> real playing id -> Wwise action",
        "evidence": "exactCurrentGameAssemblyDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeCallChainNotLivePlaybackTrace",
        "stages": (
            native_playback_stage(
                "request",
                "Beyond.Audio.AudioAdapter",
                "_ExecuteActionOnPlayingId",
                480012,
                "0x06000061",
                "0x183870420",
                "Uses the real id immediately when mapped; otherwise queues the action.",
            ),
            native_playback_stage(
                "queue",
                "Beyond.Audio.AudioActionQueueHelper",
                "QueueExecuteAction",
                480160,
                "0x060000f5",
                "0x183870520",
                "Retains an early action while Event preparation is still pending.",
            ),
            native_playback_stage(
                "resolve",
                "Beyond.Audio.AudioActionQueueHelper",
                "_ConsumeExecute",
                480165,
                "0x060000fa",
                "0x18328c150",
                "Calls AudioAdapter.TryGetRealPlayingId before consuming the queued action.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "ExecuteActionOnPlayingID",
                446431,
                "0x06000a59",
                "0x1838702c0",
                "Applies the stop, pause, or resume action to the real Wwise playing id.",
            ),
        ),
        "boundary": (
            "The queue explains lifetime control across asynchronous Event preparation; it is not evidence "
            "that a particular authored stop/pause path executed in a captured session."
        ),
    },
    "animationObject": {
        "id": "animationCallbackToObjectPost",
        "label": "Animation callback -> entity audio object -> Event post",
        "evidence": "exactCurrentGameAssemblyDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "authoredCallbackKnownExecutionNotObserved",
        "stages": (
            native_playback_stage(
                "callback",
                "Beyond.Gameplay.View.Animation.AnimatorMono",
                "PostAudioEvent(string, clipIn)",
                53417,
                "0x0600d0aa",
                "0x186c9c2c4",
                "Hashes the AnimationClip string payload and calls the uint overload.",
            ),
            native_playback_stage(
                "route",
                "Beyond.Gameplay.View.Animation.AnimatorMono",
                "PostAudioEvent(uint, clipIn)",
                53418,
                "0x0600d0ab",
                "0x18328e480",
                "Gets the owning Entity audio-object id and posts the Event through AudioAdapter.",
            ),
            native_playback_stage(
                "object",
                "Beyond.Gameplay.Audio.AudioManager",
                "GetAudioObjectId(Entity)",
                38951,
                "0x06009828",
                "0x18328e620",
                "Resolves or begins tracking the entity-scoped audio object.",
            ),
            native_playback_stage(
                "post",
                "Beyond.Audio.AudioAdapter",
                "_PostEvent",
                480010,
                "0x0600005f",
                "0x18328a690",
                "Runs the shared asynchronous Event-post pipeline.",
            ),
        ),
        "boundary": (
            "AnimationClip event time/function/payload are authored facts. Controller reachability and actual "
            "callback execution remain separate evidence, and Wwise leaf selection remains unresolved."
        ),
    },
    "animationPosition": {
        "id": "animationCallbackToPositionPost",
        "label": "Positioned animation callback -> temporary emitter -> Event post",
        "evidence": "exactCurrentGameAssemblyDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "authoredCallbackKnownExecutionNotObserved",
        "stages": (
            native_playback_stage(
                "callback",
                "Beyond.Gameplay.View.Animation.AnimatorMono",
                "PostAudioEventAtPosition(uint, clipIn)",
                53420,
                "0x0600d0ad",
                "0x1847db060",
                "Uses the owning Entity position and requests positioned playback.",
            ),
            native_playback_stage(
                "position",
                "Beyond.Gameplay.Audio.AudioManager",
                "PlaySoundAtPosition(uint, Vector3)",
                38869,
                "0x060097d6",
                "0x183b87c60",
                "Allocates a registered temporary emitter at the requested world position.",
            ),
            native_playback_stage(
                "emitter",
                "Beyond.Gameplay.Audio.AudioTempEmitter",
                "PostAndForget",
                39058,
                "0x06009893",
                "0x183b89730",
                "Posts with the temporary emitter audio-object id through the shared adapter pipeline.",
            ),
            native_playback_stage(
                "post",
                "Beyond.Audio.AudioAdapter",
                "_PostEvent",
                480010,
                "0x0600005f",
                "0x18328a690",
                "Runs the shared asynchronous Event-post pipeline.",
            ),
        ),
        "boundary": (
            "The call chain proves positional routing and emitter lifetime design, not the observed world "
            "position or selected Wwise media leaf in a live session."
        ),
    },
    "skillAction": {
        "id": "skillPlaySoundActionRouting",
        "label": "Skill PlaySound action -> object / weapon / position route -> Event post",
        "evidence": "exactCurrentGameAssemblyDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "authoredActionKnownExecutionConditionUnresolved",
        "stages": (
            native_playback_stage(
                "execute",
                "Beyond.Gameplay.Core.PlaySoundAction",
                "ExecuteInternal",
                57089,
                "0x0600df02",
                "0x183b84de0",
                "Resolves action targets and invokes _DoPlaySound when authored gates permit.",
            ),
            native_playback_stage(
                "route",
                "Beyond.Gameplay.Core.PlaySoundAction",
                "_DoPlaySound",
                57090,
                "0x0600df03",
                "0x183b85950",
                "Chooses target audio object or world-position routing; weapon mount points use the same two posts.",
            ),
            native_playback_stage(
                "objectPost",
                "Beyond.Gameplay.Core.PlaySoundAction",
                "_DoPostEvent",
                57092,
                "0x0600df05",
                "0x183b87700",
                "Hashes the authored Event and calls AudioAdapter._PostEvent with the target audio-object id.",
            ),
            native_playback_stage(
                "positionPost",
                "Beyond.Gameplay.Core.PlaySoundAction",
                "_DoPostEventAtPosition",
                57093,
                "0x0600df06",
                "0x183b879b0",
                "Routes through AudioBattleUtil and a temporary positioned emitter.",
            ),
            native_playback_stage(
                "lifetime",
                "Beyond.Gameplay.Core.PlaySoundAction",
                "_StopAllSoundInstance",
                57099,
                "0x0600df0c",
                "0x183b83650",
                "Stops retained playing ids with the authored fade when action lifetime ends.",
            ),
        ),
        "boundary": (
            "The binary proves the authored action's routing and lifetime machinery. Target selection, action "
            "conditions, and actual execution remain unresolved without a live trace."
        ),
    },
    "levelScript": {
        "id": "levelScriptAudioActionRouting",
        "label": "LevelScript audio action -> GameAction facade -> gameplay audio system",
        "evidence": "exactCurrentGameAssemblyDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "authoredActionKnownExecutionNotObserved",
        "stages": (
            native_playback_stage(
                "global",
                "Beyond.Gameplay.Actions.GameAction",
                "PlayAudio",
                32629,
                "0x06007f76",
                "0x183d40600",
                "Hashes the resolved string parameter and posts on the shared 2D emitter object.",
            ),
            native_playback_stage(
                "position",
                "Beyond.Gameplay.Actions.GameAction",
                "PlayAudioAtPosition",
                32634,
                "0x06007f7b",
                "0x1875e6220",
                "Routes a resolved Event string and callback through AudioManager.PlaySoundAtPosition.",
            ),
            native_playback_stage(
                "target",
                "Beyond.Gameplay.Actions.GameAction",
                "PlayAudioOnTarget",
                32635,
                "0x06007f7c",
                "0x1875e6660",
                "Routes the Event to the target Entity audio component/object.",
            ),
            native_playback_stage(
                "music",
                "Beyond.Gameplay.Actions.GameAction",
                "PostMusicEvent",
                32648,
                "0x06007f89",
                "0x1875e8570",
                "Routes music Events and the pre-action into AudioMusicSystem rather than direct media playback.",
            ),
            native_playback_stage(
                "release",
                "Beyond.Gameplay.Actions.GameAction",
                "StopAudio",
                32649,
                "0x06007f8a",
                "0x1875edfdc",
                "Stops the returned playing id with the authored fade when release behavior requests it.",
            ),
        ),
        "boundary": (
            "Decoded constant or exactly resolved property values identify the request. The static call chain "
            "does not prove script execution, target availability, or the Wwise-selected leaf."
        ),
    },
    "switchSelector": {
        "id": "audioObjectSwitchToWwise",
        "label": "Entity / GameObject Switch -> audio object -> Wwise SetSwitch",
        "evidence": "exactCurrentGameAssemblyDefaultBranchDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticDefaultBranchNotLiveSelectorTrace",
        "stages": (
            native_playback_stage(
                "entity",
                "Beyond.Gameplay.Audio.AudioManager",
                "SetSwitch(Entity, AudioId, AudioId)",
                38949,
                "0x06009826",
                "0x186ac4cb0",
                "Resolves BaseAudioComponent.audioObjectId and forwards the existing uint group/value ids.",
            ),
            native_playback_stage(
                "adapter",
                "Beyond.Audio.AudioAdapter",
                "SetSwitch(uint, uint, ulong)",
                479949,
                "0x06000022",
                "0x18635b9ac",
                "Forwards group id, value id, and the explicit audio-object id without re-hashing AudioId values.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "SetSwitch(uint, uint, ulong)",
                446539,
                "0x06000ac5",
                "0x1853dba54",
                "Crosses the SWIG wrapper and native function-pointer slot 0x18f373598.",
            ),
        ),
        "branches": (
            {
                "id": "gameObjectString",
                "label": "GameObject string route",
                "relation": (
                    "AudioManager.SetSwitch(GameObject,string,string) method 38960 / VA 0x186ac4bb4 "
                    "uses AudioObjectMono.audioObjectId, AudioAdapter method 479950, and the Wwise string "
                    "overload method 446540 / native slot 0x18f3735a0."
                ),
            },
            {
                "id": "typedAudioId",
                "label": "AudioId uint route",
                "relation": "AudioId.op_Implicit returns the stored uint and does not perform another hash.",
            },
        ),
        "boundary": (
            "This proves the current stock binary's default object-scoped setter routes. IFix may replace a "
            "default branch, and no live audio-object id, group value, setter time, or selected HIRC child was observed."
        ),
    },
    "rtpcSelector": {
        "id": "rtpcParameterToWwise",
        "label": "Named / AudioId RTPC -> global or object value -> Wwise SetRTPCValue",
        "evidence": "exactCurrentGameAssemblyDefaultBranchDirectCallsAndNativeSlots",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticDefaultBranchNotLiveParameterTrace",
        "stages": (
            native_playback_stage(
                "request",
                "Beyond.Gameplay.Audio.AudioManager",
                "SetRtpc(string, float, fade)",
                38865,
                "0x060097d2",
                "0x186ac492c",
                "Routes a named global parameter to the adapter.",
            ),
            native_playback_stage(
                "hash",
                "Beyond.Audio.AudioHashGenerator",
                "Compute(string)",
                480228,
                "0x06000139",
                "0x18328dcd0",
                "Computes FNV-1 over UTF-16 code units with ASCII A-Z folding and no whitespace trim.",
            ),
            native_playback_stage(
                "global",
                "Beyond.Audio.AudioAdapter",
                "SetRtpc(uint, float, int)",
                479952,
                "0x06000025",
                "0x18459c560",
                "Uses Wwise global target object id 0x00000000ffffffff.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "SetRTPCValue(uint, float, ulong, int)",
                446505,
                "0x06000aa3",
                "0x183197c40",
                "Crosses native function-pointer slot 0x18f3611a8 with parameter id, value, object id, and fade time.",
            ),
        ),
        "branches": (
            {
                "id": "entityAudioId",
                "label": "Entity AudioId route",
                "relation": (
                    "AudioManager method 38948 resolves BaseAudioComponent.audioObjectId and calls "
                    "AudioAdapter method 479954 with the existing uint parameter id."
                ),
            },
            {
                "id": "entityString",
                "label": "Entity string route",
                "relation": (
                    "AudioManager method 38947 calls AudioAdapter method 479953, which hashes the name before "
                    "the same object-scoped uint route."
                ),
            },
            {
                "id": "globalAudioId",
                "label": "Global AudioId route",
                "relation": (
                    "AudioManager method 38864 calls AudioAdapter method 479952; AudioId supplies the stored uint "
                    "without another hash."
                ),
            },
        ),
        "boundary": (
            "The setter shapes and global/object distinction are exact for the current stock binary default "
            "branches. No live RTPC value, target object, timing, resulting interpolation, or Wwise branch was observed."
        ),
    },
    "musicState": {
        "id": "musicStateGroupToWwise",
        "label": "Music mode -> exact Wwise State Group -> SetState",
        "evidence": "exactCurrentGameAssemblyStateGroupConstantsAndDirectCalls",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeCallChainNotLiveStateTrace",
        "stages": (
            native_playback_stage(
                "select",
                "Beyond.Gameplay.Audio.AudioMusicSystem",
                "_SetWwise*State",
                None,
                "",
                "",
                "Ten group-specific setters pass the enum-backed state value with the exact group constants listed below.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "SetState(uint, uint)",
                446543,
                "0x06000ac9",
                "0x183a0cbd0",
                "Crosses native function-pointer slot 0x18f3611b8 with the exact group and state ids.",
            ),
        ),
        "boundary": (
            "The group hashes, enum state ids, and setter routes are exact for the current binary. "
            "The current value at a particular gameplay frame and the resulting Wwise music branch are not observed."
        ),
    },
    "musicStateTransition": {
        "id": "audioStateTransitionToMusicSetter",
        "label": "Audio lifecycle state registration -> exact callback -> music control / setter",
        "evidence": "exactCurrentGameAssemblyRegistrationDispatchAndMetadataUsageDelegateTargets",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticRegistrationAndDispatchNotLiveStateTrace",
        "stages": (
            native_playback_stage(
                "register",
                "Beyond.Gameplay.Audio.AudioMusicSystem",
                "_RegisterStateTransitionActions",
                39571,
                "0x06009a94",
                "0x183a0d940",
                "Registers 18 persistent no-parameter callbacks as nine paired mask conditions with action orders 5 and 1.",
            ),
            native_playback_stage(
                "registry",
                "Beyond.Gameplay.Audio.AudioStateSystem",
                "RegisterTransitionAction(conditions, Action, isOneShot, actionOrder)",
                39810,
                "0x06009b83",
                "0x183a0e800",
                "Stores each condition and System.Action callback; all 18 metadata-usage delegate targets are resolved below.",
            ),
            native_playback_stage(
                "stateChange",
                "Beyond.Gameplay.Audio.AudioStateSystem",
                "_OnAudioStateChanged",
                39842,
                "0x06009ba3",
                "0x186ae8a90",
                "Dispatches from/to lifecycle-state changes to registered StateChangeAction records.",
            ),
            native_playback_stage(
                "condition",
                "Beyond.Gameplay.Audio.AudioStateSystem+StateChangeAction",
                "HandleStateChange",
                39849,
                "0x06009baa",
                "0x183d8ebb0",
                "Evaluates the registered conditions and invokes the stored callback when they pass.",
            ),
            native_playback_stage(
                "mask",
                "Beyond.Gameplay.Audio.AudioStateSystem+MaskCondition",
                "IsMet",
                39861,
                "0x06009bb6",
                "0x186aeaacc",
                "Condition type 0 is exact enter and type 1 exact leave from the current SimpleCondition.IsMet body.",
            ),
            native_playback_stage(
                "select",
                "Beyond.Gameplay.Audio.AudioMusicSystem",
                "_SetWwise*State",
                None,
                "",
                "",
                "Every registered callback is named; SwitchToDialogMusic and _StartBattleMusic have direct Wwise State setter edges, while the others route through cue/timer/factory control helpers.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "SetState(uint, uint)",
                446543,
                "0x06000ac9",
                "0x183a0cbd0",
                "Writes the exact group and enum-backed state ids across native slot 0x18f3611b8.",
            ),
        ),
        "boundary": (
            "The registration masks, action order, persistence, dispatch types, setters, and SetState boundary "
            "are exact, including all 18 delegate targets and enter/leave condition types. Actual state "
            "transitions, live callback order, indirect cue/timer outcomes, and the selected Wwise music branch remain unobserved."
        ),
    },
}


RUNTIME_SYSTEM_SPECS = (
    runtime_spec(
        "Beyond.Audio.AudioVFSLoader",
        "packages",
        "Loads init, main, audit, language, and hotfix PCK families from the game VFS.",
        fields=(
            "s_loadedInitPckInfo", "s_loadedMainPckInfo", "s_loadedAuditPckInfo",
            "s_loadedLangPckInfo", "s_loadedHotfixPckInfo", "s_pendingLanguageBlock",
        ),
        methods=("TryLoadInitPck", "TryLoadMainPck", "TryLoadLanguagePck", "LoadExtraPckFromPath"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioBankManager",
        "banks",
        (
            "Owns named Wwise BankHandle references and asynchronous load/unload lifetime. Event-owned "
            "banks used by AudioAssetHelper are a separate direct AkSoundEngine path keyed by Event id."
        ),
        fields=("s_loadedBankHandles",),
        methods=("LoadMainPCK", "LoadBankAsync", "UnloadBank", "UnloadAllBanks", "IsBankLoaded"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioAssetCache",
        "banks",
        (
            "Tracks active, least-recently-used cached, and pinned Event resources before the adapter "
            "posts the Event into Wwise."
        ),
        fields=("s_lruUsingEvents", "s_cachedEvents", "s_pinnedEvents"),
        methods=(
            "PinEvent", "UnpinEvent", "ActivateAsset", "DeactivateAsset",
            "ForceReleaseCachedAsset", "GetLeastActiveAssetAndUncache",
        ),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],),
    ),
    runtime_spec(
        "Beyond.Audio.AudioAssetHelper",
        "banks",
        (
            "Prepares, pins, caches, and garbage-collects Event-owned audio resources. On a cache miss it "
            "loads the Event-id bank, prepares exactly one Event id, then completes the adapter callback."
        ),
        fields=(
            "s_memoryBudget", "s_waitingCallbacks", "s_pendingLoadRequests",
            "s_solidLoadedEvents",
        ),
        methods=(
            "LoadEventAsync", "_DoLoadEventAsync", "_OnBankLoadedDoPrepareEvent",
            "_OnDonePrepareEvent", "_TryDequeueAndInvokeCallback", "PinEvent", "UnpinEvent",
            "UnloadEvent", "ReleaseAllCachedEventsSync",
        ),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],),
    ),
    runtime_spec(
        "Beyond.Audio.AudioHashGenerator",
        "wwise_bridge",
        (
            "Converts authored Event, Switch, State, RTPC, and cue names to the uint identifiers used by "
            "the stock Wwise bridge."
        ),
        methods=("Compute",),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["rtpcSelector"],),
    ),
    runtime_spec(
        "Beyond.Audio.AudioAdapter",
        "wwise_bridge",
        (
            "Low-level bridge for Wwise events, states, switches, RTPCs, objects, listeners, and "
            "seek/stop operations. Event posting uses an internal playing id while resources are "
            "prepared, then maps it to the real Wwise playing id."
        ),
        methods=(
            "PostEvent", "PostEventExternal", "StopByPlayingId", "PauseByPlayingId", "ResumeByPlayingId",
            "SetState", "SetSwitch", "SetRtpc", "SeekOnEvent", "RegisterGameObject",
            "UnregisterGameObject", "SetListener", "SetDefaultListener", "SetAudioLanguage",
            "_OnEventPreparedDoPostEvent", "_OnEventCallback", "_OnExternalSourceEventCallback",
            "_PostEvent", "_PostEventWithExternalSource",
            "_ExecuteActionOnPlayingId",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["externalSource"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["playingIdAction"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["switchSelector"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["rtpcSelector"],
        ),
    ),
    runtime_spec(
        "AkCallbackManager",
        "wwise_bridge",
        (
            "Dispatches native Wwise Event, Duration, Marker, playlist, music-sync, MIDI, and source-change "
            "callbacks into managed callback payloads. Callback-info types expose ids and selections, but no live "
            "callback payload was captured."
        ),
        fields=("ms_sourceChangeCallbackPkg",),
        methods=("PostCallbacks", "_ProcessEventCallback", "SetBGMCallback"),
        native_anchors=(
            {"role": "PostCallbacks", "methodIndex": 446952, "token": "0x06000c62", "virtualAddress": "0x18328b440"},
            {"role": "ProcessEventCallback", "methodIndex": 446954, "token": "0x06000c64", "virtualAddress": "0x18328cd90"},
            {"role": "SetBGMCallback", "methodIndex": 446950, "token": "0x06000c60", "virtualAddress": "0x1853cd518"},
            {"role": "eventPlayingId", "type": "AkEventCallbackInfo", "method": "get_playingID", "methodIndex": 444094, "virtualAddress": "0x1853a1688"},
            {"role": "eventId", "type": "AkEventCallbackInfo", "method": "get_eventID", "methodIndex": 444095, "virtualAddress": "0x18328dbf0"},
            {"role": "durationMediaId", "type": "AkDurationCallbackInfo", "method": "get_mediaID", "methodIndex": 444079, "virtualAddress": "0x1853a12a8"},
            {"role": "durationAudioNodeId", "type": "AkDurationCallbackInfo", "method": "get_audioNodeID", "methodIndex": 444078, "virtualAddress": "0x1853a1168"},
            {"role": "playlistSelection", "type": "AkMusicPlaylistCallbackInfo", "method": "get_uPlaylistSelection", "methodIndex": 444488, "virtualAddress": "0x1853a7800"},
            {"role": "musicSyncType", "type": "AkMusicSyncCallbackInfo", "method": "get_musicSyncType", "methodIndex": 444513, "virtualAddress": "0x1853a7af8"},
            {"role": "sourceChange", "type": "AkCallbackSerializer", "method": "AudioSourceChangeCallbackFunc", "methodIndex": 443954, "token": "0x060000ac", "virtualAddress": "0x18539e60c"},
            {"role": "otherAudioPlaying", "type": "AkAudioSourceChangeCallbackInfo", "method": "get_bOtherAudioPlaying", "methodIndex": 443882, "virtualAddress": "0x18539d68c"},
        ),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],),
        runtime_execution_status="callbackCapabilityExactPayloadsNotObserved",
    ),
    runtime_spec(
        "AkSoundEngine",
        "wwise_bridge",
        (
            "Generated Wwise C# bridge. PostEvent crosses the native P/Invoke boundary and returns "
            "the real playing id; ExecuteActionOnPlayingID applies stop/pause/resume to that id."
        ),
        methods=(
            "PostEvent", "LoadBank", "PrepareEvent", "UnloadBank", "ExecuteActionOnPlayingID",
            "SetState", "SetSwitch", "SetRTPCValue",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["externalSource"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["playingIdAction"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["switchSelector"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["rtpcSelector"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["musicState"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["musicStateTransition"],
        ),
    ),
    runtime_spec(
        "Beyond.Audio.AudioActionQueueHelper",
        "wwise_bridge",
        (
            "Queues playing-id actions issued before asynchronous Event preparation has produced "
            "a real Wwise playing id, then resolves and consumes them on later frames."
        ),
        fields=("s_executeActionQueue", "QUEUE_LIFETIME_FRAME"),
        methods=("QueueExecuteAction", "ConsumeQueue", "_ConsumeExecute"),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["playingIdAction"],),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioManager",
        "gameplay_orchestrator",
        "Gameplay-facing audio facade and owner of music, cue, state, listener, spatial, scene, NPC, and factory-related processors.",
        fields=(
            "<listener>k__BackingField", "<stateSystem>k__BackingField",
            "<gameplayStatusSystem>k__BackingField", "<music>k__BackingField",
            "<cueSystem>k__BackingField", "<sceneEmitterProcessor>k__BackingField",
            "<roomManager>k__BackingField", "<npcSystem>k__BackingField",
        ),
        methods=("PostEvent", "PostAudioCue", "SetRtpc", "SetSwitch", "PlaySoundAtPosition", "LoadLevel"),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["switchSelector"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["rtpcSelector"],
        ),
    ),
    runtime_spec(
        "Beyond.Gameplay.View.Animation.AnimatorMono",
        "animation_callbacks",
        (
            "Receives normal and positioned AnimationClip audio callbacks, resolves the owning "
            "entity or a temporary positioned emitter, and tracks returned playing ids for "
            "montage/timeline lifetime control."
        ),
        methods=(
            "PostAudioEvent", "PostAudioEventAtPosition", "_TryStartAudioEventMontageMonitor",
            "TrackAudioForTimelinePlayable", "StopAllAudioForPlayable",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["animationObject"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["animationPosition"],
        ),
    ),
    runtime_spec(
        "Beyond.Gameplay.Actions.GameAction",
        "levelscript_audio",
        (
            "LevelScript-facing facade that routes resolved Event parameters to the global emitter, "
            "a target entity, a world-position emitter, AudioMusicSystem, or playing-id lifetime controls."
        ),
        methods=(
            "PlayAudio", "PlayAudioAtPosition", "PlayAudioOnTarget", "PostAudioCue",
            "PostMusicEvent", "StopAudio", "PauseAudio", "ResumeAudio",
        ),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["levelScript"],),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.PlaySoundAction",
        "skill_actions",
        (
            "Executes authored ability sound actions, retains every returned playing id, "
            "supports object-, position-, and weapon-mount posting, seeks for time dilation, "
            "and stops retained instances with the configured fade when the action ends."
        ),
        fields=(
            "m_audioInstanceIds", "m_startTimestamp", "m_isInTimeDilation",
            "m_isPausingForTimeDilation", "m_timeDilationPassedUnscaledTime",
        ),
        methods=(
            "OnCreate", "ExecuteInternal", "_DoPlaySound", "_PlaySoundByWeaponMountPoint",
            "_DoPostEvent", "_DoPostEventAtPosition", "_IsSourceFromMainCharacter",
            "_InitialSeek", "_TimeDilationSeek", "OnTick", "OnEnd", "_StopAllSoundInstance",
        ),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["skillAction"],),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.PlaySoundAction+PlaySoundActionData",
        "skill_actions",
        (
            "Authored ability sound-request controls: event identity, interrupt and playback seek, "
            "stop/fade lifetime, target/emitter and mount-point routing, weapon routing, and "
            "time-dilation pause/seek thresholds."
        ),
        fields=(
            "_soundEvent", "_stopOnEnd", "_stopFadeDurationMs", "_canInterruptTimeMs",
            "_intrptFadeDurationMs", "_jumpToWhenPlayMs", "_useTempEmitter", "targetSettings",
            "mountPoint", "followMountPoint", "useWeaponMountPoint", "weaponIndex",
            "weaponMountPoint", "useTimeDilationPauseAndSeek", "timeDilationPauseThreshold",
            "timeDilationSeekThreshold", "timeDilationFadeOutDurationMs",
            "timeDilationFadeInDurationMs",
        ),
        methods=("get_actionType", "get_isNonLoopEvent", "get_showTempEmitterWarning"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.CharInteractPerform.AudioEventActData",
        "character_interaction_audio",
        (
            "Authored character-interaction audio action data. The current subtype adds "
            "stop/2D routing, attached-actor type/index, and a numeric AudioId to the "
            "common interaction-action timing fields."
        ),
        fields=("endStop", "is2D", "attachedActorType", "charIndex", "audioEvent"),
        methods=("get_actionType",),
        serialized_layout={
            "ownerType": "Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformRuntimeCfg",
            "ownerMemberCount": 27,
            "unionTag": 2,
            "memberCount": 15,
            "actionPhases": ("bodyTypeActions", "endActions", "loopActions", "preStartActions", "startActions"),
        },
        runtime_execution_status="runtimeNotObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.CharInteractPerform.AudioEventAction",
        "character_interaction_audio",
        (
            "Runtime action class for AudioEventActData. Metadata proves the shipped OnPlay "
            "entry point but not that a recovered perform or Event posted in a live session."
        ),
        methods=("get_audioEventActData", "OnPlay"),
        runtime_execution_status="runtimeNotObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.InteractiveAudioSetting",
        "interactive_audio",
        "Maps interactive model/sub-template identities and lifecycle states to named audio Events.",
        fields=("subTemplateList",),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.InteractiveAudioComponent",
        "interactive_audio",
        (
            "Resolves the serialized interactive-audio map, enters and exits lifecycle states, "
            "and posts the mapped normal or custom audio Event on the interactive object."
        ),
        fields=("m_curState", "m_hasInitConfig", "m_audioData", "m_openAudio", "m_currentLevel"),
        methods=(
            "AssignData", "InitSelf", "_ParseAudioData", "IsAudioStateValid",
            "SwitchAudioCustomState", "SwitchAudioState", "_SwitchState", "_EnterState",
            "_PostAudioEvent", "_ExitState", "_ProcessAudio", "_ProcessCustomAudio",
        ),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.PhysicsAudioComponentData",
        "physics_audio",
        (
            "Authored interactive-object movement, impact, and rotation Event/RTPC settings. "
            "The current MemoryPack payload is one inherited dynamic-property map whose "
            "21 keys are assigned by ApplyProperties."
        ),
        fields=(
            "<needTrackMovement>k__BackingField",
            "<onHitAccelerationSqrThreshold>k__BackingField",
            "<onStartMoveAudioEvent>k__BackingField",
            "<onStopMoveAudioEvent>k__BackingField",
            "<onHitAudioEvent>k__BackingField",
            "<onHitMaxPlayPerMove>k__BackingField",
            "<onHitMinIntervalTime>k__BackingField",
            "<velocitySqrRtpc>k__BackingField",
            "<accelerationSqrRtpc>k__BackingField",
            "<needTrackRotation>k__BackingField",
            "<onRotationLoopAudioEvent>k__BackingField",
            "<onRotationLoopStartAngularVelocitySqr>k__BackingField",
            "<onRotationLoopEndAngularVelocitySqr>k__BackingField",
            "<onRotationOneShotAudioEvent>k__BackingField",
            "<onRotationOneShotTriggerRatio>k__BackingField",
            "<onRotationGroundLoopAudioEvent>k__BackingField",
            "<onRotationGroundLoopStartAngularVelocitySqr>k__BackingField",
            "<onRotationGroundLoopEndAngularVelocitySqr>k__BackingField",
            "<onRotationGroundOneShotAudioEvent>k__BackingField",
            "<onRotationGroundOneShotTriggerRatio>k__BackingField",
            "<angularVelocitySqrRtpc>k__BackingField",
        ),
        methods=("ApplyProperties", "get_interactiveComponentType"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.PhysicsAudioComponent",
        "physics_audio",
        (
            "Runtime component that owns the physics-audio Mono bridge. Static metadata "
            "does not show which configured object was instantiated or updated."
        ),
        fields=("m_audioPhysicsMono",),
        methods=("GetAudioPhysicsMono", "InitSelf", "OnRelease"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.ModelViewStateController.AudioBehavior",
        "model_view_state_audio",
        (
            "Executes the tag-0x0001 state behavior for a normal or custom audio request. "
            "Static metadata and authored data do not prove that Execute ran."
        ),
        fields=(
            "<TriggerTime>k__BackingField", "<CanLoopActive>k__BackingField",
            "m_data", "m_context", "m_audioHandle",
        ),
        methods=("Reset", "Init", "Execute"),
        serialized_layout={
            "dataType": "Beyond.Gameplay.Core.ModelViewStateController.MVSCAudioBehaviorData",
            "unionTag": 1,
            "unionTagHex": "0x0001",
            "memberCount": 14,
            "behaviorType": 1,
            "fields": (
                "audioNodeName", "customAudioId", "eAudioTriggerState", "isCustom",
                "isDirectlyPlay", "normalAudioId", "stopOnEnd", "transitionTime",
            ),
        },
        native_anchors=(
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Core_ModelViewStateController_MVSCAudioBehaviorDataForMemoryPack",
                "methodIndex": 230856,
                "token": "0x06013a24",
                "virtualAddress": "0x183cb08e0",
            },
            {
                "role": "Execute", "methodIndex": 81734,
                "token": "0x06013f47", "virtualAddress": "0x183281ff0",
            },
        ),
        runtime_execution_status="notObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.ModelViewStateController.AudioPositionBehavior",
        "model_view_state_audio",
        (
            "Executes the tag-0x0002 positioned audio behavior. Authored placement and "
            "timing are exact; runtime posting remains unobserved."
        ),
        fields=(
            "<TriggerTime>k__BackingField", "<CanLoopActive>k__BackingField",
            "<CanContinusTrigger>k__BackingField", "m_data", "m_context", "m_audioHandle",
        ),
        methods=("Reset", "Init", "Execute"),
        serialized_layout={
            "dataType": "Beyond.Gameplay.Core.ModelViewStateController.MVSCAudioPositionBehaviourData",
            "unionTag": 2,
            "unionTagHex": "0x0002",
            "memberCount": 14,
            "behaviorType": 8,
            "fields": (
                "audioNodeName", "customAudioId", "eAudioTriggerState", "isCustom",
                "isDirectlyPlay", "normalAudioId", "stopOnEnd", "transitionTime",
            ),
        },
        native_anchors=(
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Core_ModelViewStateController_MVSCAudioPositionBehaviourDataForMemoryPack",
                "methodIndex": 230879,
                "token": "0x06013a3b",
                "virtualAddress": "0x18a061968",
            },
            {
                "role": "Execute", "methodIndex": 81745,
                "token": "0x06013f52", "virtualAddress": "0x1870c7c3c",
            },
        ),
        runtime_execution_status="notObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.ModelViewStateController.AudioRtpcBehavior",
        "model_view_state_audio",
        (
            "Executes the tag-0x0003 RTPC behavior, optionally from continuous/blackboard "
            "state. Runtime RTPC application remains unobserved."
        ),
        fields=(
            "<TriggerTime>k__BackingField", "<CanLoopActive>k__BackingField",
            "m_data", "m_context", "m_prevValue", "m_hasPrevValue",
        ),
        methods=("Reset", "Init", "Execute", "_TrySetRTPC"),
        serialized_layout={
            "dataType": "Beyond.Gameplay.Core.ModelViewStateController.MVSCAudioRTPCBehaviourData",
            "unionTag": 3,
            "unionTagHex": "0x0003",
            "memberCount": 13,
            "behaviorType": 9,
            "fields": (
                "audioNodeName", "audioRTPCSetValue", "audioRTPCValue", "behaviourType",
                "continuousTick", "dependBlackBoard", "dependFloatKey",
            ),
        },
        native_anchors=(
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Core_ModelViewStateController_MVSCAudioRTPCBehaviourDataForMemoryPack",
                "methodIndex": 230901,
                "token": "0x06013a51",
                "virtualAddress": "0x183caf110",
            },
            {
                "role": "Execute", "methodIndex": 81754,
                "token": "0x06013f5b", "virtualAddress": "0x1870c816c",
            },
        ),
        runtime_execution_status="notObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.ModelViewStateController.AudioSpatialAudioBehavior",
        "model_view_state_audio",
        (
            "Executes the tag-0x0004 spatial/portal-audio control. The shipped serialized "
            "type spells SpatialAuido; runtime application remains unobserved."
        ),
        fields=(
            "<TriggerTime>k__BackingField", "<CanLoopActive>k__BackingField",
            "m_data", "m_context", "m_totalTime", "m_directSet",
            "m_targetClosePercentage",
        ),
        methods=("Reset", "Init", "Execute"),
        serialized_layout={
            "dataType": "Beyond.Gameplay.Core.ModelViewStateController.MVSCAudioSpatialAuidoBehaviourData",
            "unionTag": 4,
            "unionTagHex": "0x0004",
            "memberCount": 12,
            "behaviorType": 13,
            "fields": (
                "continuous", "dependBlackBoard", "dependFloatKey", "directSet",
                "targetClosePercentage", "totalTime",
            ),
        },
        native_anchors=(
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Core_ModelViewStateController_MVSCAudioSpatialAuidoBehaviourDataForMemoryPack",
                "methodIndex": 230922,
                "token": "0x06013a66",
                "virtualAddress": "0x183cb1750",
            },
            {
                "role": "Execute", "methodIndex": 81764,
                "token": "0x06013f65", "virtualAddress": "0x1870c8584",
            },
        ),
        runtime_execution_status="notObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Core.InteractiveAudioComponent+EAudioTriggerState",
        "interactive_audio",
        "Exact interactive-object lifecycle states accepted by the runtime audio component.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem",
        "music",
        "Selects music modes and Wwise state groups across exploration, combat, missions, dialogs, cutscenes, factory, loading, and standalone playback.",
        fields=(
            "MUSIC_STATE_GROUP_ID", "MUSIC_MAP_STATE_GROUP_ID", "BATTLE_MUSIC_STATE_GROUP_ID",
            "BATTLE_MUSIC_INTENSITY_STATE_GROUP_ID", "MISSION_MUSIC_STATE_GROUP_ID",
            "DIALOG_MUSIC_STATE_GROUP_ID", "CUTSCENE_MUSIC_STATE_GROUP_ID",
            "LOGIN_MUSIC_STATE_GROUP_ID", "META_MUSIC_STATE_GROUP_ID",
            "REMOTE_COMM_MUSIC_STATE_GROUP_ID",
        ),
        methods=(
            "PostMusicEvent", "StartLoginMusic", "PauseMusic", "ResumeMusic", "StopMusic",
            "SwitchToDialogMusic", "PlayStandaloneMusic", "ManualSetMusicState",
            "ManualSetBattleMusicState", "ManualSetBattleMusicIntensityState",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["musicState"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["musicStateTransition"],
        ),
        native_state_groups=AUDIO_MUSIC_NATIVE_STATE_GROUPS,
        native_state_transitions=AUDIO_MUSIC_NATIVE_TRANSITION_REGISTRATIONS,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicState",
        "music",
        "Top-level authored music modes exposed to the Wwise state system.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicState",
        "music",
        "Battle music phase states.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicIntensityState",
        "music",
        "Battle music intensity states.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicMapState",
        "music",
        "World-map music selector values.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMissionMusicState",
        "music",
        "Mission music sub-state values.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseDialogMusicState",
        "music",
        "Dialog music sub-state values.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseCutsceneMusicState",
        "music",
        "Cutscene music sub-state values.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseLoginMusicState",
        "music",
        "Login music phases.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMetaMusicState",
        "music",
        "Meta/gacha music modes.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseRemoteCommMusicState",
        "music",
        "Remote-communication music phases.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioCueSystem",
        "cues",
        "Resolves named cues with scoped bool/int/float/string variables and default handlers.",
        fields=("m_boolVarDictList", "m_intVarDictList", "m_floatVarDictList", "m_stringVarDictList"),
        methods=("PostCue", "SetBoolVar", "SetIntVar", "SetFloatVar", "SetStringVar", "OnCueTimelinePlayableStop"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioStateSystem",
        "game_state",
        "Converts gameplay and loading/tag state into ordered audio transition actions.",
        fields=("m_orderedActionDictList", "m_currentState", "GAMEPLAY_TAG_CONDITION_LIST"),
        methods=("RegisterTransitionAction", "CurrentHasState", "OnInFactoryAreaMainRegionChanged", "_OnAudioStateChanged"),
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["musicStateTransition"],),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioStateSystem+EAudioState",
        "game_state",
        "High-level audio state flags for combat, dialog, cutscenes, remote communication, factory, and loading.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Actions.LevelEvent.OnAudioStateChanged",
        "level_event_condition",
        (
            "Trigger input that compares masked previous/current EAudioState values. "
            "It observes an audio-state transition and does not post a Wwise Event."
        ),
        fields=("_expectFromState", "_expectToState", "_fromStateMask", "_toStateMask"),
        methods=("get_eventKey", "CollectParams", "Process"),
        serialized_layout={
            "unionTag": 0x0048,
            "unionTagHex": "0x0048",
            "eventKey": 148,
            "authoredOccurrenceCount": 0,
            "parameterType": "Param<EAudioState>",
            "predicate": (
                "(from & fromMask) == (expectFrom & fromMask) && "
                "(to & toMask) == (expectTo & toMask)"
            ),
        },
        native_anchors=(
            {"role": "get_eventKey", "token": "0x0600a10f", "virtualAddress": "0x186aa2ef8"},
            {"role": "Process", "token": "0x0600a10e", "virtualAddress": "0x186aa2d4c"},
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Actions_LevelEvent_OnAudioStateChangedForMemoryPack",
                "virtualAddress": "0x189f88fb4",
            },
            {
                "role": "RaiseLevelEvent148",
                "type": "Beyond.Gameplay.Audio.AudioStateSystem",
                "method": "_OnAudioStateChanged",
                "virtualAddress": "0x186ae8a90",
            },
        ),
        runtime_execution_status="notObservedNoAuthoredOccurrence",
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioStateSystem+MaskCondition",
        "level_event_condition",
        "Exact masked EAudioState equality predicate used by OnAudioStateChanged.",
        methods=("IsMet",),
        native_anchors=(
            {"role": "IsMet", "virtualAddress": "0x186aeaacc"},
        ),
        runtime_execution_status="notObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Actions.LevelEvent.OnMusicBeatEvent",
        "level_event_condition",
        (
            "Trigger input that intersects an authored AudioCallbackType mask with a runtime "
            "music-callback mask. It is a condition, not a playback request."
        ),
        fields=("_beatType",),
        methods=("get_eventKey", "CollectParams", "Process"),
        serialized_layout={
            "unionTag": 0x007A,
            "unionTagHex": "0x007a",
            "eventKey": 44,
            "authoredOccurrenceCount": 0,
            "parameterType": "Param<Beyond.Audio.AudioCallbackType>",
            "predicate": "(authoredCallbackMask & runtimeCallbackMask) != 0",
        },
        native_anchors=(
            {"role": "get_eventKey", "virtualAddress": "0x186ab4184"},
            {"role": "Process", "virtualAddress": "0x186ab4094"},
            {
                "role": "Deserialize",
                "type": "Beyond_Gameplay_Actions_LevelEvent_OnMusicBeatEventForMemoryPack",
                "virtualAddress": "0x189fb176c",
            },
        ),
        runtime_execution_status="producerAndExecutionUnresolvedNoAuthoredOccurrence",
    ),
    runtime_spec(
        "Beyond.Audio.AudioCallbackType",
        "level_event_condition",
        (
            "Callback flags accepted by OnMusicBeatEvent, including music beat, bar, entry, "
            "exit, grid, user-cue, and point masks."
        ),
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioListenerTracker",
        "spatial",
        "Moves the listener differently for gameplay, cinematics, factory top view, and dialog cameras.",
        fields=("m_gameplayTick", "m_cinematicTick", "m_facTopViewTick", "m_dialogTick", "m_currState"),
        methods=("SetListener", "RegisterDialogueListener", "OnFactoryTopViewChanged", "_SetListenerStateFromGameState"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.SpatialAudioManager",
        "spatial",
        "Coordinates acoustic geometry, occluders, rooms, and portals.",
        fields=("m_roomManager", "m_occluderManager", "m_geoManager", "m_portalManager"),
        methods=("PreloadAcousticGeo", "LoadRoom", "LoadPortal", "SetPortalOpenPercentageAtPos"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioSceneEmitterProcessor",
        "world_emitters",
        "Streams and culls single and large authored scene emitters.",
        fields=("m_singleEmitters", "m_largeEmitters", "m_cachedLargeEmitterData"),
        methods=("OnEmitterLoaded", "OnEmitterUnloaded", "_ProcessCulling"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioRoomData",
        "spatial",
        "Room-tone, auxiliary-bus, transmission, reverb, and reflection parameters passed to spatial audio.",
        fields=(
            "roomToneId", "priority", "auxBusId", "parentRoomId", "auxLevel",
            "transmissionLoss", "transitionWidth", "t60DecayTIme", "preDelayTime",
            "reverbLevel", "erLevel", "flags",
        ),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioRemoteFactoryBridge",
        "factory",
        "Posts and updates factory-unit, region, building-state, construction, destruction, and top-view audio.",
        methods=(
            "RegisterAudioFragment", "OnFactoryTopViewChanged", "TriggerFactoryMainRegionAudio",
            "OnBuildingStateChanged", "PlayBuildUpAudio", "PlayDestroyAudio", "PostEventOnUnit",
            "UpdateNodeMode", "GetAudioStateValueFromNodeMode",
        ),
        native_anchors=(
            {
                "role": "objectScopedFactoryNodeModeSwitch",
                "method": "UpdateNodeMode",
                "methodIndex": 39714,
                "token": "0x06009b23",
                "setSwitchCallVirtualAddress": "0x1850ffa6d",
                "groupId": 0x7ACDACAF,
                "groupIdHex": "0x7acdacaf",
            },
            {
                "role": "factoryNodeModeValueResolver",
                "method": "GetAudioStateValueFromNodeMode",
                "methodIndex": 39759,
                "token": "0x06009b50",
                "virtualAddress": "0x186ae7b18",
            },
        ),
        runtime_execution_status="staticSetterAndValueMappingExactLiveModeNotObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioGamePadManager",
        "output_device",
        "Selects the global Wwise gamepad backend and creates/removes Motion and controller-speaker output devices for XInput or ScePad.",
        fields=(
            "m_wwiseMotionOutputDeviceId",
            "m_wwiseControllerSpeakerOutputDeviceId",
        ),
        methods=(
            "_TryAddXInputMotionOutput", "_TryRefreshScePadHandle",
            "_DoOnInputTypeChanged", "_ReAddControllerOutputDevice",
            "_TryRemoveControllerOutputDevice",
        ),
        native_anchors=(
            {
                "role": "xinputStateSetter",
                "method": "_TryAddXInputMotionOutput",
                "token": "0x060099bd",
                "virtualAddress": "0x186ad0468",
                "setStateCallVirtualAddress": "0x186ad04e2",
                "groupId": 0xF6699CF4,
                "groupIdHex": "0xf6699cf4",
                "valueId": 0x1A9FC91F,
                "valueIdHex": "0x1a9fc91f",
            },
            {
                "role": "scePadStateSetter",
                "method": "_TryRefreshScePadHandle",
                "token": "0x060099be",
                "virtualAddress": "0x186ad055c",
                "setStateCallVirtualAddress": "0x186ad069c",
                "groupId": 0xF6699CF4,
                "groupIdHex": "0xf6699cf4",
                "valueId": 0x1B9ABDB1,
                "valueIdHex": "0x1b9abdb1",
            },
            {
                "role": "motionOutputDevice",
                "type": "Beyond.Audio.AudioAdapter+Device",
                "method": "AddOutput",
                "token": "0x06000086",
                "virtualAddress": "0x18635fb54",
                "downstreamType": "AkSoundEngine",
                "downstreamMethod": "AddOutput",
                "downstreamVirtualAddress": "0x1853cf1a8",
            },
            {
                "role": "scePadHandleToDeviceId",
                "type": "Beyond.Audio.AudioAdapter+Device",
                "method": "GetMmDeviceIdFromScePadHandle",
                "token": "0x0600008b",
                "virtualAddress": "0x18635fc34",
            },
            {
                "role": "inputTypeOutputLifecycle",
                "method": "_DoOnInputTypeChanged",
                "token": "0x060099c3",
                "virtualAddress": "0x186ad0068",
            },
        ),
        runtime_execution_status="staticStateAndOutputDeviceCallsitesExactLiveEventToDeviceRoutingNotObserved",
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.VoiceResponseProcessor",
        "responsive_voice",
        "Filters responsive voice through state, random, band-limit, cooldown, and selection gates before queueing playback.",
        methods=("Response", "_HandleStateCheck", "_HandleRandom", "_HandleBandLimit", "_HandleCoolDown", "_HandleSelection"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.VoiceResponseProcessor+EResponseDecideReason",
        "responsive_voice",
        "Explicit success/failure reasons for responsive-voice selection.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Audio.AudioEventPlayable",
        "timeline",
        "Timeline event carrier with stop, fade, seek, binding, 2D/emitter, duration, and exit-event controls.",
        fields=(
            "_audioEventKey", "_stopEventAtClipEnd", "_fadeOutWhenStop", "_fadeOutTime",
            "_enableSeek", "m_eventDuration", "_useBindingObj", "_is2D", "_emitter", "_exitAudioEvent",
        ),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioMusicPlayable",
        "timeline",
        "Timeline music carrier with a named event, action type, and skip behavior.",
        fields=("_audioEventKey", "musicActionType", "triggerOnSkip"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioCuePlayable",
        "timeline",
        "Timeline cue carrier with authored start and end cue names.",
        fields=("_startCueName", "_endCueName"),
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.Utils.AudioBlackScreenBehaviour+ERetainFlag",
        "mix_control",
        "Black-screen transitions independently retain ambience, music, SFX, voice, and UI buses.",
        enum_values=True,
    ),
    runtime_spec(
        "Beyond.Audio.AudioEventType",
        "taxonomy",
        "Engine event taxonomy for SFX, music, state, game-sync, voice, controller, vibration, and global events.",
        enum_values=True,
    ),
)


def normalize_posix(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def load_json(path: Path, fallback: Any) -> Any:
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def collect_metadata_audio_literals(metadata_path: Path | None) -> list[str]:
    """Recover complete audio-like managed string literals from IL2CPP v29+.

    ``stringLiteral`` rows are exact ``<byteLength, dataIndex>`` pairs and the
    referenced UTF-8 bytes live in ``stringLiteralData``.  These strings prove
    that managed code shipped the identifier, not that the corresponding
    event was posted at runtime.  A later exact FNV-1/type-4 HIRC join upgrades
    the row to a named Wwise Event object.
    """

    if metadata_path is None or not metadata_path.is_file():
        return []
    data = metadata_path.read_bytes()
    if len(data) < 24:
        return []
    magic = int.from_bytes(data[0:4], "little")
    version = int.from_bytes(data[4:8], "little")
    if magic != METADATA_MAGIC or version < 29:
        return []
    literal_offset = int.from_bytes(data[8:12], "little")
    literal_size = int.from_bytes(data[12:16], "little", signed=True)
    literal_data_offset = int.from_bytes(data[16:20], "little")
    literal_data_size = int.from_bytes(data[20:24], "little", signed=True)
    if (
        literal_size < 0
        or literal_data_size < 0
        or literal_size % 8
        or literal_offset + literal_size > len(data)
        or literal_data_offset + literal_data_size > len(data)
    ):
        return []

    names: dict[str, str] = {}
    literal_data_end = literal_data_offset + literal_data_size
    for pos in range(literal_offset, literal_offset + literal_size, 8):
        byte_length = int.from_bytes(data[pos : pos + 4], "little")
        data_index = int.from_bytes(data[pos + 4 : pos + 8], "little")
        start = literal_data_offset + data_index
        end = start + byte_length
        if start < literal_data_offset or end > literal_data_end:
            continue
        try:
            value = data[start:end].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if MANAGED_AUDIO_LITERAL_RE.fullmatch(value):
            names.setdefault(value.lower(), value)
    return [names[key] for key in sorted(names)]


def event_category(event_id: Any) -> str:
    value = str(event_id or "").strip().lower()
    for prefix, category in EVENT_CATEGORY_PREFIXES:
        if value.startswith(prefix):
            return category
    return "unknown"


def hashed_event_key(event_hash: int) -> str:
    return f"hashed-event:0x{event_hash & 0xFFFFFFFF:08x}"


def event_hash_context_key(event_hash: int) -> str:
    return f"#0x{event_hash & 0xFFFFFFFF:08x}"


def is_rtpc_parameter_name(value: Any) -> bool:
    return str(value or "").strip().lower().startswith("au_rtpc_")


def compact_media(entry: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "mediaId", "rel", "src", "format", "bytes", "storageRoot",
        "audioScope", "audioCategory", "audioCategoryDetail", "sourceBlock",
        "sourceBlockLabel", "sourceLanguage", "sourceBank", "bankId", "bank",
        "audioDialogKey", "audioDialogPath", "speakerChannel", "voType", "duration",
        "wwiseMediaEvidence", "contentSha256",
        "hotfixMediaReplacement", "mediaResolutionEvidence",
    )
    compact = {key: entry[key] for key in keys if entry.get(key) not in (None, "", [])}
    if compact.get("wwiseMediaEvidence"):
        compact["wwiseMediaEvidence"] = [
            {
                key: row[key]
                for key in (
                    "rootActionIds", "soundObjectCount", "relationTypes",
                    "musicTrackObjectCount", "selectionPaths", "bankId", "bankPackage",
                    "sourceKinds", "pluginIds", "pluginNames", "streamTypes", "sourceBits",
                )
                if row.get(key) not in (None, "", [])
            }
            for row in compact["wwiseMediaEvidence"]
            if isinstance(row, dict)
        ]
    return compact


def compact_container_evidence(rows: Iterable[Any]) -> list[dict[str, Any]]:
    summary: dict[tuple[int, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        object_type = int(row.get("objectType") or 0)
        edge_kind = str(row.get("edgeKind") or "unknown")
        mode_label = str(row.get("modeLabel") or "")
        key = (object_type, edge_kind, mode_label)
        target = summary.setdefault(key, {
            "objectType": object_type,
            "edgeKind": edge_kind,
            "modeLabel": mode_label,
            "nodeCount": 0,
            "childCount": 0,
            "parserConfidence": row.get("parserConfidence"),
        })
        target["nodeCount"] += 1
        target["childCount"] += int(row.get("childCount") or 0)
        if object_type == 5 and row.get("selectorParserStatus"):
            target["randomSequenceNodeCount"] = int(
                target.get("randomSequenceNodeCount") or 0
            ) + 1
            random_status = str(row.get("selectorParserStatus") or "unknown")
            target.setdefault("_randomSequenceParserStatuses", Counter())[random_status] += 1
            if random_status == "typedExactV150PlaylistWeights":
                target["typedRandomSequenceNodeCount"] = int(
                    target.get("typedRandomSequenceNodeCount") or 0
                ) + 1
                target.setdefault("_randomSequenceModes", Counter())[
                    str(row.get("modeLabel") or "unknown")
                ] += 1
                target.setdefault("_randomModes", Counter())[
                    str(row.get("randomModeLabel") or "unknown")
                ] += 1
                target.setdefault("_randomTransitionModes", Counter())[
                    str(row.get("transitionModeLabel") or "unknown")
                ] += 1
                target["randomSequencePlaylistItemCount"] = int(
                    target.get("randomSequencePlaylistItemCount") or 0
                ) + int(row.get("playlistItemCount") or 0)
                membership_status = str(
                    row.get("playlistMembershipStatus") or "unknown"
                )
                target.setdefault("_randomSequenceMembershipStatuses", Counter())[
                    membership_status
                ] += 1
                target["randomSequenceOwnedChildNotInPlaylistCount"] = int(
                    target.get("randomSequenceOwnedChildNotInPlaylistCount") or 0
                ) + len(row.get("ownedChildIdsNotInPlaylist") or [])
                target["randomSequenceDuplicatePlaylistItemCount"] = int(
                    target.get("randomSequenceDuplicatePlaylistItemCount") or 0
                ) + int(row.get("duplicatePlaylistItemCount") or 0)
                if membership_status == "emptyPlaylistOwnedChildrenPreserved":
                    target["randomSequenceEmptyPlaylistNodeCount"] = int(
                        target.get("randomSequenceEmptyPlaylistNodeCount") or 0
                    ) + 1
                if not row.get("childrenOrderMatchesPlaylist", True):
                    target["playlistOrderDiffersFromChildrenCount"] = int(
                        target.get("playlistOrderDiffersFromChildrenCount") or 0
                    ) + 1
                non_default_weights = int(row.get("nonDefaultWeightCount") or 0)
                target["nonDefaultWeightItemCount"] = int(
                    target.get("nonDefaultWeightItemCount") or 0
                ) + non_default_weights
                if non_default_weights:
                    target["nonDefaultWeightNodeCount"] = int(
                        target.get("nonDefaultWeightNodeCount") or 0
                    ) + 1
                if not row.get("uniformWeights", True):
                    target["nonUniformWeightNodeCount"] = int(
                        target.get("nonUniformWeightNodeCount") or 0
                    ) + 1
                avoid_repeat = int(row.get("avoidRepeatCount") or 0)
                target["maxAvoidRepeatCount"] = max(
                    int(target.get("maxAvoidRepeatCount") or 0), avoid_repeat
                )
                if avoid_repeat != 1:
                    target["nonDefaultAvoidRepeatNodeCount"] = int(
                        target.get("nonDefaultAvoidRepeatNodeCount") or 0
                    ) + 1
                if int(row.get("loopCount") or 0) != 1:
                    target["nonDefaultLoopNodeCount"] = int(
                        target.get("nonDefaultLoopNodeCount") or 0
                    ) + 1
                if row.get("globalScope"):
                    target["globalScopeRandomSequenceNodeCount"] = int(
                        target.get("globalScopeRandomSequenceNodeCount") or 0
                    ) + 1
                if row.get("continuous"):
                    target["continuousRandomSequenceNodeCount"] = int(
                        target.get("continuousRandomSequenceNodeCount") or 0
                    ) + 1
                if row.get("resetPlaylistAtEachPlay"):
                    target["resetPlaylistNodeCount"] = int(
                        target.get("resetPlaylistNodeCount") or 0
                    ) + 1
            else:
                target["unresolvedRandomSequenceNodeCount"] = int(
                    target.get("unresolvedRandomSequenceNodeCount") or 0
                ) + 1
        if object_type == 9 and isinstance(row.get("layerTailEvidence"), dict):
            layer = row["layerTailEvidence"]
            target["layerNodeCount"] = int(target.get("layerNodeCount") or 0) + 1
            layer_status = str(layer.get("layerTailParserStatus") or "unknown")
            target.setdefault("_layerParserStatuses", Counter())[layer_status] += 1
            if layer_status == "typedExactV150LayerTail":
                target["typedLayerNodeCount"] = int(
                    target.get("typedLayerNodeCount") or 0
                ) + 1
                confidence = str(row.get("parserConfidence") or "unknown")
                target.setdefault("_layerProofStatuses", Counter())[confidence] += 1
                assignment = str(layer.get("layerAssignmentStatus") or "unknown")
                target.setdefault("_layerAssignmentStatuses", Counter())[assignment] += 1
                target["layerDefinitionCount"] = int(
                    target.get("layerDefinitionCount") or 0
                ) + int(layer.get("layerCount") or 0)
                target["layerInitialRtpcCurveCount"] = int(
                    target.get("layerInitialRtpcCurveCount") or 0
                ) + int(layer.get("initialRtpcCurveCount") or 0)
                target["layerAssociationCount"] = int(
                    target.get("layerAssociationCount") or 0
                ) + int(layer.get("associationCount") or 0)
                target["layerCurvePointCount"] = int(
                    target.get("layerCurvePointCount") or 0
                ) + int(layer.get("curvePointCount") or 0)
                if layer.get("continuousValidation"):
                    target["continuousLayerNodeCount"] = int(
                        target.get("continuousLayerNodeCount") or 0
                    ) + 1
                target["layerAssociationOutsideChildrenCount"] = int(
                    target.get("layerAssociationOutsideChildrenCount") or 0
                ) + len(layer.get("associationChildIdsOutsideChildren") or [])
                for layer_row in layer.get("layers") or []:
                    if not isinstance(layer_row, dict):
                        continue
                    try:
                        target.setdefault("_layerRtpcIds", set()).add(
                            int(layer_row.get("rtpcId")) & 0xFFFFFFFF
                        )
                    except (TypeError, ValueError):
                        pass
                    target.setdefault("_layerRtpcTypes", Counter())[
                        str(layer_row.get("rtpcTypeLabel") or "unknown")
                    ] += 1
            else:
                target["unresolvedLayerNodeCount"] = int(
                    target.get("unresolvedLayerNodeCount") or 0
                ) + 1
        selector = row.get("switchMappingEvidence")
        if not isinstance(selector, dict):
            continue
        target["selectorNodeCount"] = int(target.get("selectorNodeCount") or 0) + 1
        parser_status = str(selector.get("parserStatus") or "unknown")
        parser_counts = target.setdefault("_selectorParserStatuses", Counter())
        parser_counts[parser_status] += 1
        if parser_status != "typedExactV150FlatPackages":
            target["unresolvedSelectorNodeCount"] = int(
                target.get("unresolvedSelectorNodeCount") or 0
            ) + 1
            continue

        target["typedSelectorNodeCount"] = int(
            target.get("typedSelectorNodeCount") or 0
        ) + 1
        group_type = str(selector.get("groupType") or "unknown")
        group_type_counts = target.setdefault("_selectorGroupTypes", Counter())
        group_type_counts[group_type] += 1
        try:
            group_id = int(selector.get("groupId")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            group_id = None
        if group_id is not None:
            target.setdefault("_selectorGroupIds", set()).add(group_id)
        if selector.get("continuousValidation"):
            target["continuousValidationNodeCount"] = int(
                target.get("continuousValidationNodeCount") or 0
            ) + 1

        packages = [
            package for package in selector.get("packages") or []
            if isinstance(package, dict)
        ]
        target["selectorPackageCount"] = int(
            target.get("selectorPackageCount") or 0
        ) + len(packages)
        authored_child_count = int(row.get("childCount") or 0)
        package_value_ids: set[int] = set()
        for package in packages:
            child_ids = [
                value for value in package.get("childIds") or []
                if isinstance(value, int)
            ]
            try:
                package_value_ids.add(int(package.get("valueId")) & 0xFFFFFFFF)
            except (TypeError, ValueError):
                pass
            if child_ids:
                target["nonEmptySelectorPackageCount"] = int(
                    target.get("nonEmptySelectorPackageCount") or 0
                ) + 1
                target["selectorPackageChildReferenceCount"] = int(
                    target.get("selectorPackageChildReferenceCount") or 0
                ) + len(child_ids)
                if authored_child_count and len(set(child_ids)) < authored_child_count:
                    target["strictSubsetSelectorPackageCount"] = int(
                        target.get("strictSubsetSelectorPackageCount") or 0
                    ) + 1
        try:
            default_value_id = int(selector.get("defaultValueId")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            default_value_id = None
        if default_value_id is not None and default_value_id not in package_value_ids:
            target["defaultValueMissingPackageCount"] = int(
                target.get("defaultValueMissingPackageCount") or 0
            ) + 1

        associations = [
            association for association in selector.get("associations") or []
            if isinstance(association, dict)
        ]
        target["selectorAssociationCount"] = int(
            target.get("selectorAssociationCount") or 0
        ) + len(associations)
        switch_mode_counts = target.setdefault("_selectorSwitchModes", Counter())
        for association in associations:
            switch_mode_counts[str(association.get("onSwitchMode") or "unknown")] += 1
            if association.get("isFirstOnly"):
                target["isFirstOnlyAssociationCount"] = int(
                    target.get("isFirstOnlyAssociationCount") or 0
                ) + 1
            if association.get("continuePlayback"):
                target["continuePlaybackAssociationCount"] = int(
                    target.get("continuePlaybackAssociationCount") or 0
                ) + 1
            if int(association.get("fadeOutTimeMs") or 0):
                target["nonzeroFadeOutAssociationCount"] = int(
                    target.get("nonzeroFadeOutAssociationCount") or 0
                ) + 1
            if int(association.get("fadeInTimeMs") or 0):
                target["nonzeroFadeInAssociationCount"] = int(
                    target.get("nonzeroFadeInAssociationCount") or 0
                ) + 1
        for source_key, target_key in (
            ("mappedChildIdsOutsideChildren", "mappedChildOutsideChildrenCount"),
            ("unmappedChildIds", "unmappedSelectorChildCount"),
            ("associationChildIdsOutsideChildren", "associationChildOutsideChildrenCount"),
        ):
            target[target_key] = int(target.get(target_key) or 0) + len(
                selector.get(source_key) or []
            )

    compact_rows: list[dict[str, Any]] = []
    for row in summary.values():
        random_status_counts = row.pop("_randomSequenceParserStatuses", None)
        random_sequence_modes = row.pop("_randomSequenceModes", None)
        random_modes = row.pop("_randomModes", None)
        random_transition_modes = row.pop("_randomTransitionModes", None)
        random_membership_statuses = row.pop(
            "_randomSequenceMembershipStatuses", None
        )
        layer_parser_statuses = row.pop("_layerParserStatuses", None)
        layer_proof_statuses = row.pop("_layerProofStatuses", None)
        layer_assignment_statuses = row.pop("_layerAssignmentStatuses", None)
        layer_rtpc_types = row.pop("_layerRtpcTypes", None)
        layer_rtpc_ids = sorted(row.pop("_layerRtpcIds", set()))
        parser_counts = row.pop("_selectorParserStatuses", None)
        group_type_counts = row.pop("_selectorGroupTypes", None)
        switch_mode_counts = row.pop("_selectorSwitchModes", None)
        group_ids = sorted(row.pop("_selectorGroupIds", set()))
        if random_status_counts:
            row["randomSequenceParserStatuses"] = dict(
                sorted(random_status_counts.items())
            )
        if random_sequence_modes:
            row["randomSequenceModes"] = dict(sorted(random_sequence_modes.items()))
        if random_modes:
            row["randomModes"] = dict(sorted(random_modes.items()))
        if random_transition_modes:
            row["randomTransitionModes"] = dict(
                sorted(random_transition_modes.items())
            )
        if random_membership_statuses:
            row["randomSequenceMembershipStatuses"] = dict(
                sorted(random_membership_statuses.items())
            )
        if layer_parser_statuses:
            row["layerParserStatuses"] = dict(sorted(layer_parser_statuses.items()))
        if layer_proof_statuses:
            row["layerProofStatuses"] = dict(sorted(layer_proof_statuses.items()))
        if layer_assignment_statuses:
            row["layerAssignmentStatuses"] = dict(
                sorted(layer_assignment_statuses.items())
            )
        if layer_rtpc_types:
            row["layerRtpcTypes"] = dict(sorted(layer_rtpc_types.items()))
        if layer_rtpc_ids:
            row["layerRtpcIdCount"] = len(layer_rtpc_ids)
            row["layerRtpcIdsHex"] = [f"0x{value:08x}" for value in layer_rtpc_ids[:24]]
            row["layerRtpcIdsTruncated"] = len(layer_rtpc_ids) > 24
        if parser_counts:
            row["selectorParserStatuses"] = dict(sorted(parser_counts.items()))
        if group_type_counts:
            row["selectorGroupTypes"] = dict(sorted(group_type_counts.items()))
        if switch_mode_counts:
            row["selectorSwitchModes"] = dict(sorted(switch_mode_counts.items()))
        if group_ids:
            row["selectorGroupIdCount"] = len(group_ids)
            row["selectorGroupIdsHex"] = [f"0x{value:08x}" for value in group_ids[:24]]
            row["selectorGroupIdsTruncated"] = len(group_ids) > 24
        compact_rows.append({
            key: value for key, value in row.items()
            if value not in (None, "", [], {})
        })
    return compact_rows


def _metadata_module() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_audio_metadata_helper", METADATA_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load metadata helper: {METADATA_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _runtime_cache_hit(cache: dict[str, Any], sha256: str, size: int) -> dict[str, Any] | None:
    if cache.get("schemaVersion") != RUNTIME_MODEL_CACHE_SCHEMA_VERSION:
        return None
    fingerprint = cache.get("sourceFingerprint") if isinstance(cache, dict) else None
    runtime = cache.get("runtimeModel") if isinstance(cache, dict) else None
    if not isinstance(fingerprint, dict) or not isinstance(runtime, dict):
        return None
    if fingerprint.get("sha256") != sha256 or fingerprint.get("size") != size:
        return None
    return runtime


def _read_compressed_uint32(data: bytes, offset: int) -> int | None:
    """Decode the integer form used by current IL2CPP metadata defaults."""

    if offset < 0 or offset >= len(data):
        return None
    first = data[offset]
    if first < 0x80:
        return first
    if first < 0xC0 and offset + 1 < len(data):
        return ((first & 0x3F) << 8) | data[offset + 1]
    if first < 0xE0 and offset + 3 < len(data):
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3]
        )
    if first == 0xF0 and offset + 4 < len(data):
        return struct.unpack_from(">I", data, offset + 1)[0]
    if first == 0xFE:
        return 0xFFFFFFFE
    if first == 0xFF:
        return 0xFFFFFFFF
    return None


def _metadata_enum_values(module: Any, md: Any, type_def: Any) -> dict[str, int]:
    """Read exact enum constants from field-default records when available."""

    fields = {
        index: md.string(md.fields[index].name_index)
        for index in range(type_def.field_start, type_def.field_start + type_def.field_count)
        if index < len(md.fields)
    }
    default_section = md.sections.get("fieldDefaultValues")
    data_section = md.sections.get("fieldAndParameterDefaultValueData")
    if default_section is None or data_section is None or default_section.size % 12:
        return {}
    out: dict[str, int] = {}
    for offset in range(default_section.offset, default_section.offset + default_section.size, 12):
        field_index, metadata_type_index, data_index = struct.unpack_from("<iii", md.buf, offset)
        field_name = fields.get(field_index)
        if not field_name or field_name == "value__" or data_index < 0:
            continue
        raw = _read_compressed_uint32(md.buf, data_section.offset + data_index)
        if raw is None:
            continue
        type_name = md.type_name_by_metadata_type_index.get(metadata_type_index, "")
        if type_name in {"System.SByte", "System.Int16", "System.Int32", "System.Int64"}:
            value = (raw >> 1) ^ -(raw & 1)
        else:
            value = raw
        out[field_name] = int(value)
    return out


def build_runtime_model(metadata_path: Path | None, export_root: Path) -> dict[str, Any]:
    cache_path = export_root / RUNTIME_CACHE_REL
    if metadata_path is None or not metadata_path.is_file():
        return {
            "status": "degraded",
            "reason": "Installed IL2CPP metadata was unavailable; runtime-system claims were not emitted.",
            "evidenceBoundary": "No current binary metadata was validated.",
            "systems": [],
            "missingTypes": [spec["type"] for spec in RUNTIME_SYSTEM_SPECS],
        }

    size = metadata_path.stat().st_size
    sha256 = file_sha256(metadata_path)
    cached = _runtime_cache_hit(load_json(cache_path, {}), sha256, size)
    if cached is not None:
        return cached

    module = _metadata_module()
    md = module.Metadata(metadata_path)
    types_by_name = {md.type_full_name(row): row for row in md.types}
    systems: list[dict[str, Any]] = []
    missing_types: list[str] = []

    for spec in RUNTIME_SYSTEM_SPECS:
        type_def = types_by_name.get(spec["type"])
        if type_def is None:
            missing_types.append(spec["type"])
            continue
        field_names, method_names = module.member_names(md, type_def)
        field_set = set(field_names)
        method_set = set(method_names)
        expected_fields = list(spec["fields"])
        expected_methods = list(spec["methods"])
        present_fields = (
            [name for name in field_names if name != "value__"]
            if spec["enumValues"]
            else [name for name in expected_fields if name in field_set]
        )
        present_methods = [name for name in expected_methods if name in method_set]
        system = {
            "type": spec["type"],
            "image": md.image_name_by_type_index.get(type_def.index, ""),
            "typeIndex": type_def.index,
            "token": f"0x{type_def.token:08x}",
            "layer": spec["layer"],
            "meaning": spec["meaning"],
            "fields": present_fields,
            "methods": present_methods,
            "missingFields": [name for name in expected_fields if name not in field_set],
            "missingMethods": [name for name in expected_methods if name not in method_set],
            "evidence": "installedIl2cppMetadata",
        }
        for key in ("serializedLayout", "runtimeExecutionStatus"):
            if spec.get(key):
                system[key] = spec[key]
        if spec.get("nativeAnchors"):
            if sha256 == MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256:
                system["nativeAnchors"] = spec["nativeAnchors"]
                system["nativeAnchorStatus"] = "exactCurrentBuild"
            else:
                system["nativeAnchorStatus"] = "omittedMetadataFingerprintMismatch"
        if spec.get("nativeCallChains"):
            if sha256 == MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256:
                system["nativeCallChains"] = spec["nativeCallChains"]
                system["nativeCallChainStatus"] = "exactCurrentBuild"
            else:
                system["nativeCallChainStatus"] = "omittedMetadataFingerprintMismatch"
        if spec.get("nativeStateGroups"):
            if sha256 == MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256:
                system["nativeStateGroups"] = spec["nativeStateGroups"]
                system["nativeStateGroupStatus"] = "exactCurrentBuild"
            else:
                system["nativeStateGroupStatus"] = "omittedMetadataFingerprintMismatch"
        if spec.get("nativeStateTransitions"):
            if sha256 == MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256:
                system["nativeStateTransitions"] = spec["nativeStateTransitions"]
                system["nativeStateTransitionStatus"] = "exactCurrentBuild"
            else:
                system["nativeStateTransitionStatus"] = "omittedMetadataFingerprintMismatch"
        if spec["enumValues"]:
            enum_values = _metadata_enum_values(module, md, type_def)
            if enum_values:
                system["enumValues"] = enum_values
        systems.append(system)

    metadata = module.catalog_metadata_summary(md)
    runtime = {
        "status": "complete" if not missing_types else "partial",
        "reason": "" if not missing_types else "One or more selected runtime types were absent from the current metadata.",
        "metadata": {
            "displayPath": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
            "version": metadata.get("version"),
            "size": size,
            "sha256": sha256,
            "typeCount": metadata.get("typeCount"),
            "methodCount": metadata.get("methodCount"),
            "fieldCount": metadata.get("fieldCount"),
        },
        "evidenceBoundary": (
            "Type, field, method, and enum names are exact current-build IL2CPP metadata. "
            "Selected ModelView anchors and audio playback call chains include method index, token, "
            "virtual address, and the recorded GameAssembly fingerprint only for the matching current "
            "metadata fingerprint. The playback chains are static direct-call evidence from that "
            "GameAssembly, not a live execution trace, active game state, or proof of which Wwise "
            "branch a player heard."
        ),
        "systems": systems,
        "missingTypes": missing_types,
    }
    json_dump(cache_path, {
        "schemaVersion": RUNTIME_MODEL_CACHE_SCHEMA_VERSION,
        "sourceFingerprint": {"sha256": sha256, "size": size},
        "runtimeModel": runtime,
    })
    return runtime


def _append_context(
    contexts: dict[str, list[dict[str, Any]]],
    seen: dict[str, set[str]],
    event_id: Any,
    context: dict[str, Any],
) -> None:
    key = str(event_id or "").strip().lower()
    if not key:
        return
    marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if marker in seen[key]:
        return
    seen[key].add(marker)
    contexts[key].append(context)


def _attach_custom_footstep_parameters(
    context: dict[str, Any], evidence_rows: Iterable[dict[str, Any]]
) -> None:
    variants = aggregate_custom_footstep_parameter_variants(evidence_rows)
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
    variants = aggregate_custom_footstep_context_variants(
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
        "runtimeVfxWeightThreshold": CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD,
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
            _append_context(contexts, seen, event_hash_context_key(event_hash), context)
    return dict(contexts)


def collect_spawner_pre_warn_semantics(
    export_root: Path,
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact current SpawnerEnemyLibraryItem pre-warning Events."""
    if decoder is None:
        try:
            from story_builder.spawner_binary import decode_spawner_enemy_library
        except ImportError:
            from scripts.story_builder.spawner_binary import decode_spawner_enemy_library
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
        try:
            from story_builder.level_bindings import decode_leveldata_npc_patrol_list
        except ImportError:
            from scripts.story_builder.level_bindings import decode_leveldata_npc_patrol_list
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
                            event_hash_context_key(event_hash),
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
        try:
            from story_builder.char_interact_perform_binary import (
                decode_char_interact_audio_actions,
            )
        except ImportError:
            from scripts.story_builder.char_interact_perform_binary import (
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
                contexts, seen, event_hash_context_key(event_hash), context
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


LEVELSCRIPT_AUDIO_EVENT_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "PlayAudiAtPosition": (("key", "play"),),
    "PlayAudio": (("key", "play"),),
    "PlayAudioAndWait": (("eventName", "play"),),
    "PlayAudioOnTarget": (("audioKey", "play"),),
    "PlayStandaloneMusic": (("startEvent", "standaloneStart"), ("stopEvent", "standaloneStop")),
    "PostAudioStatusEvent": (("statusEnterEvent", "statusEnter"), ("statusExitEvent", "statusExit")),
    "PostMusicEvent": (("musicEvent", "post"), ("musicEventOnRelease", "release")),
}


def audio_hash_generator_compute(value: str) -> int:
    """Mirror ``Beyond.Audio.AudioHashGenerator.Compute(string)`` exactly.

    The shipped implementation applies FNV-1 to managed UTF-16 code units,
    folding only ASCII ``A``-``Z`` before each XOR.  Whitespace is significant.
    """

    hash_value = 0x811C9DC5
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    for offset in range(0, len(encoded), 2):
        code_unit = encoded[offset] | (encoded[offset + 1] << 8)
        if 0x41 <= code_unit <= 0x5A:
            code_unit += 0x20
        hash_value = (hash_value * 0x01000193) & 0xFFFFFFFF
        hash_value ^= code_unit
    return hash_value


LEVELSCRIPT_AUDIO_CONTROL_ROLES = {
    "BlockAutoMusicChange": "autoMusicChangeBlock",
    "BlockAutoMusicChangeCancel": "autoMusicChangeBlockCancel",
    "BlockBattleMusic": "battleMusicBlock",
    "BlockResetMusic": "musicResetBlock",
    "CleanAudioCueVar": "cueVariableClean",
    "EnterCustomMusicMode": "customMusicModeEnter",
    "ExitCustomMusicMode": "customMusicModeExit",
    "FlushRadio": "radioFlush",
    "ManualRestoreMusicState": "musicStateRestore",
    "ManualSetMusicState": "musicStateOverride",
    "PlayStandaloneMusic": "standaloneMusicLifecycle",
    "SetAudioCueVar": "cueVariableWrite",
    "StartPlaceholderMusic_DevOnly": "placeholderMusicStart",
    "StopAudio": "playingAudioStop",
    "StopPlaceholderMusic_DevOnly": "placeholderMusicStop",
    "StopVoice": "voiceStop",
    "PostAudioStopAllEnemyVoice": "enemyVoiceStopAll",
    "PlayGlobalResponseVoice": "globalResponseVoicePlay",
    "PlayResponseVoice": "responseVoicePlay",
    "SetAudioGlobalParameter": "globalParameterWrite",
    "SetAudioParameter": "parameterWrite",
    "SetVoiceTriggerLevel": "voiceTriggerLevelWrite",
    "SwitchAIBarkEnable": "aiBarkEnableSwitch",
    "SwitchAudioCustomState": "customAudioStateSwitch",
    "SwitchAudioState": "entityAudioStateSwitch",
    "TriggerBarkVoice": "barkVoiceTrigger",
    "TriggerMainCharVoice": "mainCharacterVoiceTrigger",
    "MuteMusic_DevOnly": "musicMute",
    "UnmuteMusic_DevOnly": "musicUnmute",
}

LEVELSCRIPT_RADIO_ACTION_ROLES = {
    "Play3DRadio": "play3D",
    "Play3DRadioAndWait": "play3DAndWait",
    "PlayRadio": "play",
    "PlayRadioAndWait": "playAndWait",
    "StopRadio": "stop",
}
LEVELSCRIPT_RADIO_ACTION_NAMES = frozenset({
    *LEVELSCRIPT_RADIO_ACTION_ROLES,
    "ToggleClearScreenButRadio",
})


def _load_levelscript_brief_property_sources(
    export_root: Path,
    levelscript_id: str,
    preferred_source_root: str,
    cache: dict[tuple[str, str], tuple[dict[str, Any] | None, str]],
) -> tuple[dict[str, Any] | None, str]:
    """Find one validated LevelScriptBriefData row for a script id.

    LevelScriptData is overlaid by source-root-relative path, while LevelData
    may remain in StreamingAssets when the winning script bytes are from
    Persistent.  Search the winning source first and the other source second;
    only a validated member-22 BriefData dictionary entry is accepted.
    """
    normalized_id = str(levelscript_id or "").replace("\\", "/").strip("/")
    parts = PurePosixPath(normalized_id).parts
    if len(parts) < 2 or not parts[-1].isdigit():
        return None, ""
    level_id = str(parts[-2])
    script_id = int(parts[-1])
    cache_key = (level_id, str(script_id))
    if cache_key in cache:
        return cache[cache_key]

    try:
        from story_builder.level_bindings import (
            parse_leveldata_levelscript_brief_dictionary,
        )
    except ImportError:
        from scripts.story_builder.level_bindings import (
            parse_leveldata_levelscript_brief_dictionary,
        )

    source_roots = [str(preferred_source_root)]
    source_roots.extend(
        source for source in ("StreamingAssets", "Persistent")
        if source not in source_roots
    )
    for source_root in source_roots:
        script_dir = (
            export_root / "structured" / source_root / "Data" / "Json"
            / "LevelScriptData" / level_id
        )
        leveldata_dir = (
            export_root / "structured" / source_root / "Data" / "Json"
            / "LevelData" / level_id
        )
        if not script_dir.is_dir() or not leveldata_dir.is_dir():
            continue
        candidate_script_ids = {
            int(path.stem)
            for path in script_dir.glob("*.json")
            if path.stem.isdigit()
        }
        if script_id not in candidate_script_ids:
            continue
        script_needle = script_id.to_bytes(8, "little", signed=False)
        for leveldata_path in sorted(leveldata_dir.glob("*.json")):
            try:
                data = leveldata_path.read_bytes()
            except OSError:
                continue
            if script_needle not in data:
                continue
            brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                data,
                candidate_script_ids,
            )
            brief = brief_dictionary.get(script_id)
            if not isinstance(brief, dict):
                continue
            source_path = normalize_posix(leveldata_path.relative_to(export_root))
            result = (brief, source_path)
            cache[cache_key] = result
            return result

    result = (None, "")
    cache[cache_key] = result
    return result


def collect_levelscript_audio_semantics(
    export_root: Path,
    *,
    decode_file: Any | None = None,
    cue_semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect exact LevelScript Event/cue requests and dynamic bindings."""

    cue_semantics = cue_semantics or collect_audio_cue_semantics(export_root)
    cue_definitions = cue_semantics.get("cueDefinitions") or {}
    try:
        from story_builder.level_bindings import (
            resolve_levelscript_dynamic_property_string,
            resolve_levelscript_dynamic_property_string_list,
        )
    except ImportError:
        from scripts.story_builder.level_bindings import (
            resolve_levelscript_dynamic_property_string,
            resolve_levelscript_dynamic_property_string_list,
        )

    if decode_file is None:
        try:
            from story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_action_map_membership,
                levelscript_record_semantic_key,
            )
        except ImportError:
            from scripts.story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_action_map_membership,
                levelscript_record_semantic_key,
            )
        target_keys = {
            # Audio ActionBase families registered by the current GameAssembly
            # formatter table.  Keep the member count as part of the key:
            # several non-ActionBase unions reuse the same numeric tag.
            (0x0016, 0x09), (0x0028, 0x09), (0x0029, 0x09), (0x002A, 0x09),
            (0x00B7, 0x08), (0x00E9, 0x08),
            (0x0089, 0x0B), (0x0368, 0x0B), (0x0369, 0x0A), (0x036E, 0x14),
            (0x0306, 0x09), (0x0307, 0x0B),
            (0x034A, 0x14), (0x034B, 0x14), (0x034C, 0x0C),
            (0x034E, 0x0B), (0x034F, 0x10), (0x0352, 0x0C),
            (0x0363, 0x0D), (0x0364, 0x0D), (0x0367, 0x11),
            (0x036B, 0x13),
            (0x0371, 0x0B), (0x0372, 0x08), (0x0373, 0x0C), (0x03D5, 0x0F),
            (0x04A7, 0x0E), (0x04AC, 0x0A), (0x04B4, 0x0B),
            (0x04B5, 0x09), (0x04B7, 0x0A), (0x04BA, 0x09),
            (0x04BC, 0x0B), (0x04CA, 0x09),
        }

        def decode_file(_path: Path, data: bytes) -> dict[str, Any]:
            records = extract_levelscript_uid_records(data)
            _action_map, memberships = levelscript_action_map_membership(data, records)
            rows: list[dict[str, Any]] = []
            string_list_getters: dict[int, dict[str, Any]] = {}
            target_count = 0
            non_action_target_count = 0
            non_action_target_roles: Counter[str] = Counter()
            for index, record in enumerate(records):
                semantic_key = levelscript_record_semantic_key(record)
                action_map_role = str(
                    memberships.get(int(record.get("start") or 0)) or ""
                )
                if (
                    semantic_key == (0x0347, 0x09)
                    and action_map_role.startswith("getterList")
                    and isinstance(record.get("localId"), int)
                ):
                    next_start = (
                        int(records[index + 1].get("start") or 0)
                        if index + 1 < len(records)
                        else len(data)
                    )
                    detail = decode_levelscript_record_payload(
                        data,
                        record,
                        next_start=next_start,
                        action_map_role=action_map_role,
                    )
                    getter = detail.get("listGetValueString")
                    if isinstance(getter, dict):
                        string_list_getters[int(record["localId"])] = {
                            "record": record,
                            "actionMapRole": action_map_role,
                            "getter": getter,
                        }
                    continue
                if semantic_key not in target_keys:
                    continue
                if not action_map_role.startswith("actionList"):
                    non_action_target_count += 1
                    non_action_target_roles[action_map_role or "unknown"] += 1
                    continue
                target_count += 1
                next_start = (
                    int(records[index + 1].get("start") or 0)
                    if index + 1 < len(records)
                    else len(data)
                )
                detail = decode_levelscript_record_payload(
                    data,
                    record,
                    next_start=next_start,
                    action_map_role=memberships.get(int(record.get("start") or 0)),
                )
                audio_action = detail.get("audioAction") if isinstance(detail, dict) else None
                if isinstance(audio_action, dict):
                    rows.append({
                        "record": record,
                        "actionMapRole": str(memberships.get(int(record.get("start") or 0)) or ""),
                        "audioAction": audio_action,
                    })
            return {
                "targetCount": target_count,
                "rows": rows,
                "stringListGetters": string_list_getters,
                "nonActionTargetCount": non_action_target_count,
                "nonActionTargetRoles": dict(non_action_target_roles),
            }

    overlay: dict[str, tuple[str, Path]] = {}
    for source_root in ("StreamingAssets", "Persistent"):
        root = export_root / "structured" / source_root / "Data" / "Json" / "LevelScriptData"
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            overlay[path.relative_to(root).as_posix()] = (source_root, path)

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    cue_invocations: list[dict[str, Any]] = []
    dynamic_event_bindings: list[dict[str, Any]] = []
    resolved_dynamic_event_bindings: list[dict[str, Any]] = []
    radio_invocations: list[dict[str, Any]] = []
    dynamic_radio_bindings: list[dict[str, Any]] = []
    resolved_dynamic_radio_bindings: list[dict[str, Any]] = []
    control_actions: list[dict[str, Any]] = []
    dynamic_control_bindings: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    source_files_with_actions = 0
    target_records = 0
    decoded_records = 0
    decode_failures = 0
    non_action_target_records = 0
    non_action_target_roles: Counter[str] = Counter()
    levelscript_brief_cache: dict[
        tuple[str, str], tuple[dict[str, Any] | None, str]
    ] = {}

    def compact_fields(fields: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(fields, dict):
            return {}
        return {
            str(name): {
                key: value
                for key, value in field.items()
                if key in {
                    "sourceField", "present", "bindingKind", "value", "idRef",
                    "paramSource", "path", "logicId", "slotId", "useSlotId",
                }
                and value not in (None, "", [])
            }
            for name, field in fields.items()
            if isinstance(field, dict)
        }

    for relative_path, (source_root, path) in sorted(overlay.items()):
        try:
            data = path.read_bytes()
            decoded = decode_file(path, data) or {}
        except (OSError, ValueError):
            decode_failures += 1
            continue
        rows = (decoded.get("rows") or []) if isinstance(decoded, dict) else []
        string_list_getters = (
            decoded.get("stringListGetters") or {}
            if isinstance(decoded, dict)
            else {}
        )
        target_records += int(decoded.get("targetCount") or len(rows)) if isinstance(decoded, dict) else len(rows)
        if isinstance(decoded, dict):
            non_action_target_records += int(decoded.get("nonActionTargetCount") or 0)
            for role, count in (decoded.get("nonActionTargetRoles") or {}).items():
                non_action_target_roles[str(role)] += int(count or 0)
        if rows:
            source_files_with_actions += 1
        source_path = normalize_posix(path.relative_to(export_root))
        source_sha256 = hashlib.sha256(data).hexdigest()
        levelscript_id = str(PurePosixPath(relative_path).with_suffix(""))
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            action = row.get("audioAction") if isinstance(row.get("audioAction"), dict) else {}
            record = row.get("record") if isinstance(row.get("record"), dict) else {}
            action_name = str(action.get("action") or "")
            if not action_name:
                continue
            decoded_records += 1
            action_counts[action_name] += 1
            fields = compact_fields(action.get("fields"))
            common = {
                "confidence": "direct",
                "semanticRole": "authoredLevelScriptAudioAction",
                "action": action_name,
                "levelScriptId": levelscript_id,
                "sourceRoot": source_root,
                "sourcePath": source_path,
                "sourceSha256": source_sha256,
                "recordIndex": row_index,
                "recordStart": int(record.get("start") or 0),
                "recordUid": str(record.get("uid") or ""),
                "recordLocalId": record.get("localId"),
                "actionMapRole": str(row.get("actionMapRole") or ""),
                "unionTag": record.get("unionTag"),
                "serializedMemberCount": record.get("serializedMemberCount"),
                "nativeMappingId": str(action.get("nativeMappingId") or ""),
                "payloadShape": str(action.get("payloadShape") or ""),
                "fields": fields,
                "runtimeActivationStatus": "levelScriptActionExecutionNotObserved",
            }
            for binding in action.get("eventBindings") or []:
                if not isinstance(binding, dict) or not str(binding.get("eventName") or ""):
                    continue
                _append_context(contexts, seen, binding["eventName"], {
                    **common,
                    "kind": "levelScriptAudioAction",
                    "eventName": str(binding["eventName"]),
                    "triggerRole": str(binding.get("role") or "play"),
                    "sourceField": str(binding.get("sourceField") or ""),
                })
            for binding in action.get("cueBindings") or []:
                if not isinstance(binding, dict) or not str(binding.get("cueName") or ""):
                    continue
                cue_name = str(binding["cueName"])
                cue_id = audio_hash_generator_compute(cue_name)
                cue_signed_id = cue_id if cue_id < 0x80000000 else cue_id - 0x100000000
                definition = cue_definitions.get(cue_id)
                lookup = {
                    "cueId": cue_id,
                    "cueSignedId": cue_signed_id,
                    "cueHex": f"0x{cue_id:08x}",
                    "cueHashAlgorithm": "fnv1AsciiLowerUtf16CodeUnits",
                    "cueHashEvidence": "nativeAudioHashGeneratorCompute",
                    "definitionStatus": "resolved" if isinstance(definition, dict) else "missing",
                }
                if isinstance(definition, dict):
                    lookup.update({
                        "cueDefinitionSource": str(definition.get("source") or ""),
                        "handlerCount": int(definition.get("handlerCount") or 0),
                        "directHandlerCount": int(definition.get("directHandlerCount") or 0),
                        "levelHandlerCount": int(definition.get("levelHandlerCount") or 0),
                        "behaviorEventCount": len(definition.get("behaviorEvents") or []),
                        "expressionOperandCount": len(definition.get("expressionOperands") or []),
                    })
                cue_invocations.append({
                    **common,
                    "kind": "levelScriptAudioCueInvocation",
                    "cueName": cue_name,
                    "triggerRole": str(binding.get("role") or "invoke"),
                    "sourceField": str(binding.get("sourceField") or ""),
                    **lookup,
                })
                if not isinstance(definition, dict):
                    continue
                for behavior in definition.get("behaviorEvents") or []:
                    if not isinstance(behavior, dict) or not str(behavior.get("eventId") or ""):
                        continue
                    event_name = str(behavior["eventId"])
                    cue_context = {
                        **common,
                        "kind": "levelScriptAudioCueBehaviorEvent",
                        "semanticRole": "authoredLevelScriptCueBehaviorEventRequest",
                        "eventName": event_name,
                        "cueName": cue_name,
                        "triggerRole": str(binding.get("role") or "invoke"),
                        "sourceField": str(binding.get("sourceField") or ""),
                        **lookup,
                        "handlerScope": str(behavior.get("handlerScope") or ""),
                        "handlerIndex": behavior.get("handlerIndex"),
                        "expressionSide": str(behavior.get("expressionSide") or ""),
                        "expressionPath": str(behavior.get("expressionPath") or ""),
                        "exprType": behavior.get("exprType"),
                        "evidence": "exactLevelScriptCueNameRuntimeHashAndCueBehaviorExpression",
                        "triggerRequestEvidence": [
                            "exactLevelScriptAudioCueName",
                            "nativeAudioHashGeneratorCompute",
                            "audioCueBehaviorExprType3",
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "levelScriptActionExecutionNotObserved",
                            "cueInvocationAndExpressionEvaluationRequired",
                        ],
                    }
                    if str(behavior.get("levelId") or ""):
                        cue_context["levelId"] = str(behavior["levelId"])
                    _append_context(contexts, seen, event_name, cue_context)
            for binding in action.get("radioBindings") or []:
                if not isinstance(binding, dict):
                    continue
                radio_id = str(binding.get("radioId") or "").strip()
                if not radio_id:
                    continue
                radio_invocations.append({
                    **common,
                    "kind": "levelScriptRadioTrigger",
                    "semanticRole": "authoredLevelScriptRadioTrigger",
                    "radioId": radio_id,
                    "triggerRole": str(
                        binding.get("role")
                        or LEVELSCRIPT_RADIO_ACTION_ROLES.get(action_name)
                        or "play"
                    ),
                    "sourceField": str(binding.get("sourceField") or "_radioId"),
                    "radioIdentityKind": "RadioTableDefinitionId",
                    "wwiseEventStatus": "notApplicable",
                })
            radio_field = fields.get("radioId") or {}
            if (
                action_name in LEVELSCRIPT_RADIO_ACTION_ROLES
                and radio_field.get("bindingKind") == "dynamic"
            ):
                dynamic_radio_binding = {
                    **common,
                    "kind": "levelScriptDynamicRadioBinding",
                    "semanticRole": "authoredLevelScriptRadioTrigger",
                    "triggerRole": LEVELSCRIPT_RADIO_ACTION_ROLES[action_name],
                    "sourceField": str(radio_field.get("sourceField") or "_radioId"),
                    "binding": radio_field,
                    "resolutionStatus": "runtimeRadioIdParamUnresolved",
                    "radioIdentityKind": "RadioTableDefinitionId",
                    "wwiseEventStatus": "notApplicable",
                }
                getter_local_id = radio_field.get("idRef")
                getter_row = (
                    string_list_getters.get(getter_local_id)
                    if radio_field.get("paramSource") == -1
                    and isinstance(getter_local_id, int)
                    else None
                )
                getter = (
                    getter_row.get("getter")
                    if isinstance(getter_row, dict)
                    and isinstance(getter_row.get("getter"), dict)
                    else None
                )
                list_binding = (
                    getter.get("list")
                    if isinstance(getter, dict)
                    and isinstance(getter.get("list"), dict)
                    else None
                )
                if isinstance(list_binding, dict):
                    brief, brief_source_path = _load_levelscript_brief_property_sources(
                        export_root,
                        levelscript_id,
                        source_root,
                        levelscript_brief_cache,
                    )
                    resolution = resolve_levelscript_dynamic_property_string_list(
                        brief,
                        list_binding,
                    )
                    if resolution:
                        getter_record = getter_row.get("record") or {}
                        dynamic_radio_binding.update({
                            "resolutionStatus": (
                                "resolvedRadioCandidateSetRuntimeIndexUnobserved"
                            ),
                            "candidateRadioIds": resolution["values"],
                            "selectionStatus": resolution["selectionStatus"],
                            "getter": getter,
                            "getterRecordLocalId": getter_record.get("localId"),
                            "getterRecordUid": str(getter_record.get("uid") or ""),
                            "getterActionMapRole": str(
                                getter_row.get("actionMapRole") or ""
                            ),
                            "resolution": resolution,
                            "resolutionSourcePath": brief_source_path,
                            "triggerRequestEvidence": [
                                "exactLevelScriptRadioActionUnionAndFields",
                                "exactListGetValueStringGetterUnionAndFields",
                                "exactLevelScriptBriefDataStringListProperty",
                            ],
                            "triggerRuntimeActivationStatuses": [
                                "levelScriptActionExecutionNotObserved",
                                "runtimeListIndexSelectionUnobserved",
                            ],
                        })
                        resolved_dynamic_radio_bindings.append(
                            dynamic_radio_binding
                        )
                dynamic_radio_bindings.append(dynamic_radio_binding)
            control_role = LEVELSCRIPT_AUDIO_CONTROL_ROLES.get(action_name)
            if control_role:
                control_actions.append({
                    **common,
                    "kind": "levelScriptAudioControl",
                    "controlRole": control_role,
                })
                for field_name, field in fields.items():
                    if field.get("bindingKind") != "dynamic":
                        continue
                    dynamic_control_bindings.append({
                        **common,
                        "kind": "levelScriptDynamicControlBinding",
                        "controlRole": control_role,
                        "sourceField": str(field.get("sourceField") or f"_{field_name}"),
                        "binding": field,
                        "resolutionStatus": "runtimeParamValueUnresolved",
                    })
            for field_name, role in LEVELSCRIPT_AUDIO_EVENT_FIELDS.get(action_name, ()):
                field = fields.get(field_name) or {}
                if field.get("bindingKind") != "dynamic":
                    continue
                dynamic_binding = {
                    **common,
                    "kind": "levelScriptDynamicAudioBinding",
                    "triggerRole": role,
                    "sourceField": str(field.get("sourceField") or f"_{field_name}"),
                    "binding": field,
                    "resolutionStatus": "runtimeParamValueUnresolved",
                }
                if (
                    field.get("paramSource") == 200
                    and field.get("idRef") == -1
                    and isinstance(field.get("path"), str)
                    and field.get("path")
                ):
                    brief, brief_source_path = _load_levelscript_brief_property_sources(
                        export_root,
                        levelscript_id,
                        source_root,
                        levelscript_brief_cache,
                    )
                    resolution = resolve_levelscript_dynamic_property_string(
                        brief,
                        field,
                    )
                    if resolution:
                        resolved_event_name = str(resolution.get("value") or "").strip()
                        if resolved_event_name:
                            dynamic_binding.update({
                                "resolutionStatus": "resolvedLevelScriptBriefProperty",
                                "resolvedEventName": resolved_event_name,
                                "resolution": resolution,
                                "resolutionSourcePath": brief_source_path,
                            })
                            resolved_dynamic_event_bindings.append(dynamic_binding)
                            _append_context(contexts, seen, resolved_event_name, {
                                **common,
                                "kind": "levelScriptAudioActionDynamicProperty",
                                "semanticRole": (
                                    "authoredLevelScriptAudioActionPropertyEvent"
                                ),
                                "eventName": resolved_event_name,
                                "triggerRole": role,
                                "sourceField": dynamic_binding["sourceField"],
                                "dynamicBinding": field,
                                "resolutionStatus": (
                                    "resolvedLevelScriptBriefProperty"
                                ),
                                "resolution": resolution,
                                "resolutionSourcePath": brief_source_path,
                                "triggerRequestEvidence": [
                                    "exactLevelScriptAudioActionUnionAndFields",
                                    "exactLevelScriptParamSource200PropertyPath",
                                    "exactLevelScriptBriefDataStringProperty",
                                ],
                                "triggerRuntimeActivationStatuses": [
                                    "levelScriptActionExecutionNotObserved",
                                    "resolvedEventRuntimePlaybackUnobserved",
                                ],
                            })
                dynamic_event_bindings.append(dynamic_binding)

    event_context_count = sum(len(rows) for rows in contexts.values())
    direct_event_context_count = sum(
        context.get("kind") == "levelScriptAudioAction"
        for rows in contexts.values()
        for context in rows
    )
    cue_behavior_context_count = sum(
        context.get("kind") == "levelScriptAudioCueBehaviorEvent"
        for rows in contexts.values()
        for context in rows
    )
    direct_event_names = sum(
        any(context.get("kind") == "levelScriptAudioAction" for context in rows)
        for rows in contexts.values()
    )
    cue_definition_statuses = Counter(
        str(row.get("definitionStatus") or "unknown") for row in cue_invocations
    )
    radio_action_counts = {
        name: action_counts[name]
        for name in sorted(LEVELSCRIPT_RADIO_ACTION_NAMES)
        if action_counts[name]
    }
    radio_role_counts = Counter(
        str(row.get("triggerRole") or "unknown") for row in radio_invocations
    )
    return {
        "eventContexts": dict(contexts),
        "cueInvocations": cue_invocations,
        "dynamicEventBindings": dynamic_event_bindings,
        "resolvedDynamicEventBindings": resolved_dynamic_event_bindings,
        "radioInvocations": radio_invocations,
        "dynamicRadioBindings": dynamic_radio_bindings,
        "resolvedDynamicRadioBindings": resolved_dynamic_radio_bindings,
        "controlActions": control_actions,
        "dynamicControlBindings": dynamic_control_bindings,
        "stats": {
            "sourceFiles": len(overlay),
            "sourceFilesWithAudioActions": source_files_with_actions,
            "targetAudioActionRecords": target_records,
            "decodedAudioActionRecords": decoded_records,
            "decodeFailures": decode_failures,
            "skippedNonActionTargetRecords": non_action_target_records,
            "skippedNonActionTargetRoles": dict(sorted(non_action_target_roles.items())),
            "eventRequestContexts": event_context_count,
            "constantEventRequestContexts": direct_event_context_count,
            "constantEventNames": direct_event_names,
            "cueInvocations": len(cue_invocations),
            "cueBehaviorEventContexts": cue_behavior_context_count,
            "cueDefinitionStatusCounts": dict(sorted(cue_definition_statuses.items())),
            "dynamicEventBindings": len(dynamic_event_bindings),
            "resolvedDynamicEventBindings": len(resolved_dynamic_event_bindings),
            "radioActionRecords": sum(radio_action_counts.values()),
            "constantRadioBindings": len(radio_invocations),
            "dynamicRadioBindings": len(dynamic_radio_bindings),
            "resolvedDynamicRadioBindings": len(
                resolved_dynamic_radio_bindings
            ),
            "uniqueConstantRadioIds": len({
                str(row.get("radioId") or "")
                for row in radio_invocations
                if str(row.get("radioId") or "")
            }),
            "radioActionCounts": radio_action_counts,
            "radioRoleCounts": dict(sorted(radio_role_counts.items())),
            "controlActions": len(control_actions),
            "dynamicControlBindings": len(dynamic_control_bindings),
            "actionCounts": dict(sorted(action_counts.items())),
            "controlActionCounts": dict(sorted(Counter(
                str(row.get("action") or "") for row in control_actions
            ).items())),
        },
        "evidenceBoundary": (
            "Exact union/member-count fields prove authored LevelScript requests and routing. "
            "Constant Event parameters and cue names joined through the native AudioHashGenerator and exact "
            "AudioCue behavior expressions become Event contexts. Cue handler/condition evaluation, action "
            "execution, unresolved dynamic Param values, state/variable writes, playback handles, and "
            "placeholder-music ids are not observed. A resolved ParamSource=200 property still proves only "
            "the authored property-to-action string join, not action execution or Wwise playback. A "
            "resolved ListGetValueString radio binding proves its authored candidate set, while the "
            "runtime-selected list index remains unobserved."
        ),
    }


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


def normalize_levelsequence_audio_id(value: Any) -> str:
    """Return the authored sequence id only for the exact ``_Audio`` suffix."""

    text = str(value or "").strip()
    if not text.endswith("_Audio"):
        return ""
    base = text[:-len("_Audio")]
    return base if base.startswith("levelseq_") else ""


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
        try:
            from story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_record_semantic_key,
            )
        except ImportError:
            from scripts.story_builder.levelscript_binary import (
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


def _object_identity(record: dict[str, Any]) -> dict[str, Any]:
    obj = record.get("object") if isinstance(record.get("object"), dict) else {}
    return {
        "serializedFile": str(obj.get("serializedFile") or ""),
        "pathId": obj.get("pathId"),
        "source": str(obj.get("source") or ""),
        "sourceOffset": obj.get("sourceOffset"),
    }


def _object_identity_key(value: dict[str, Any] | None) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    serialized_file = str(value.get("serializedFile") or "")
    try:
        path_id = int(value.get("pathId"))
    except (TypeError, ValueError):
        return None
    return (serialized_file, path_id) if serialized_file else None


def _scalar_value(record: dict[str, Any], path: str) -> Any:
    for row in record.get("scalars") or []:
        if isinstance(row, (list, tuple)) and len(row) >= 3 and row[0] == path:
            return row[2]
    return None


def _resolved_pptr(record: dict[str, Any], path: str) -> dict[str, Any] | None:
    for row in record.get("pptrs") or []:
        if not isinstance(row, dict) or row.get("path") != path:
            continue
        target = row.get("target")
        if isinstance(target, dict):
            identity = {
                "serializedFile": str(target.get("serializedFile") or ""),
                "pathId": target.get("pathId"),
                "source": str(target.get("source") or ""),
                "sourceOffset": target.get("sourceOffset"),
                "type": str(target.get("type") or ""),
                "name": str(target.get("name") or ""),
            }
            if _object_identity_key(identity):
                return identity
    return None


def _object_index_path(
    export_root: Path,
    class_name: str,
    explicit: Path | None,
) -> Path:
    if explicit is not None:
        return Path(explicit)
    return (
        export_root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
        / "object_index" / "parts"
        / f"StreamingAssets_animestudio_json_by_type_{class_name}.jsonl"
    )


def collect_timeline_audio_ownership(
    export_root: Path,
    *,
    event_ids: Iterable[str] | None = None,
    cue_names: Iterable[str] | None = None,
    mono_path: Path | None = None,
    director_path: Path | None = None,
) -> dict[str, Any]:
    """Recover serialized Timeline audio ownership joins.

    AudioEventPlayable carries a Wwise Event name directly.  AudioCuePlayable
    carries a cue name instead; keeping that namespace separate is important:
    a cue is resolved by AudioCueSystem/AudioCueTable and is not itself a
    Wwise Event.  Both playable types share the same exact Track/Timeline and
    PlayableDirector PPtr chain.
    """

    wanted = {
        str(value or "").strip().lower()
        for value in (event_ids or [])
        if str(value or "").strip()
    }
    scan_all_cues = cue_names is None
    wanted_cues = {
        str(value or "").strip().casefold()
        for value in (cue_names or [])
        if str(value or "").strip()
    }
    mono_file = _object_index_path(export_root, "MonoBehaviour", mono_path)
    directors_file = _object_index_path(export_root, "PlayableDirector", director_path)
    playable_events: dict[tuple[str, int], str] = {}
    playable_cues: dict[tuple[str, int], dict[str, str]] = {}
    carriers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cue_carriers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats = Counter()

    # The object-index writer is not required to emit a referenced asset before
    # the Track that points at it.  Pre-index the small playable subset so an
    # AudioMusicPlayable after its Track is still an exact PPtr join.  This is
    # deliberately not a full object-index materialization.
    if mono_file.is_file():
        with mono_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(record, dict) or record.get("recordType") != "object":
                    continue
                name = str(record.get("name") or "")
                script_name = _scalar_value(record, "$.m_Name")
                is_audio_event_playable = (
                    "AudioEventPlayable" in name
                    or "AudioDlgEventPlayable" in name
                    or "AudioMusicPlayable" in name
                    or script_name in {
                        "AudioEventPlayable",
                        "AudioDlgEventPlayable",
                        "AudioMusicPlayable",
                    }
                )
                event_value = _scalar_value(record, "$._audioEventKey")
                identity = _object_identity(record)
                key = _object_identity_key(identity)
                event_id = str(event_value or "").strip().lower()
                if is_audio_event_playable and event_id and key and (
                    not wanted
                    or event_id in wanted
                    or "AudioMusicPlayable" in name
                    or script_name == "AudioMusicPlayable"
                ):
                    playable_events[key] = event_id
                    if "AudioMusicPlayable" in name or script_name == "AudioMusicPlayable":
                        stats["audioMusicPlayableRecords"] += 1

    if mono_file.is_file():
        with mono_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    stats["decodeFailures"] += 1
                    continue
                if not isinstance(record, dict) or record.get("recordType") != "object":
                    continue
                stats["monoObjects"] += 1
                name = str(record.get("name") or "")
                script_name = _scalar_value(record, "$.m_Name")
                event_value = _scalar_value(record, "$._audioEventKey")
                if event_value is not None and (
                    "AudioEventPlayable" in name
                    or "AudioDlgEventPlayable" in name
                    or "AudioMusicPlayable" in name
                    or script_name
                    in {"AudioEventPlayable", "AudioDlgEventPlayable"}
                    or script_name == "AudioMusicPlayable"
                ):
                    event_id = str(event_value or "").strip().lower()
                    identity = _object_identity(record)
                    key = _object_identity_key(identity)
                    is_music_playable = (
                        "AudioMusicPlayable" in name or script_name == "AudioMusicPlayable"
                    )
                    if event_id and key and (
                        not wanted or event_id in wanted or is_music_playable
                    ):
                        playable_events[key] = event_id
                        stats["audioEventPlayableRecords"] += 1
                cue_start = str(_scalar_value(record, "$._startCueName") or "").strip()
                cue_end = str(_scalar_value(record, "$._endCueName") or "").strip()
                if (cue_start or cue_end) and (
                    "AudioCuePlayable" in name
                    or _scalar_value(record, "$.m_Name") == "AudioCuePlayable"
                ):
                    cue_values = {
                        value.casefold() for value in (cue_start, cue_end) if value
                    }
                    identity = _object_identity(record)
                    key = _object_identity_key(identity)
                    if key and (not wanted_cues or cue_values & wanted_cues):
                        playable_cues[key] = {
                            "startCueName": cue_start,
                            "endCueName": cue_end,
                        }
                        stats["audioCuePlayableRecords"] += 1
                clip_displays = []
                for scalar in record.get("scalars") or []:
                    if not isinstance(scalar, (list, tuple)) or len(scalar) < 3:
                        continue
                    match = re.fullmatch(
                        r"\$\.m_Clips\[(\d+)\]\.m_DisplayName",
                        str(scalar[0]),
                    )
                    if not match:
                        continue
                    value = str(scalar[2] or "").strip().lower()
                    if value:
                        clip_displays.append((int(match.group(1)), value))
                for clip_index, display_name in clip_displays:
                    if (
                        wanted
                        and not scan_all_cues
                        and not wanted_cues
                        and display_name not in wanted
                        and display_name not in {
                            "audioeventplayable",
                            "audiodlgeventplayable",
                            "audiomusicplayable",
                        }
                    ):
                        continue
                    parent = _resolved_pptr(record, "$.m_Parent")
                    asset = _resolved_pptr(
                        record, f"$.m_Clips[{clip_index}].m_Asset"
                    )
                    track_identity = _object_identity(record)
                    track_key = _object_identity_key(track_identity)
                    parent_key = _object_identity_key(parent)
                    asset_key = _object_identity_key(asset)
                    if not track_key or not parent_key or not asset_key:
                        stats["timelineCarrierMissingIdentity"] += 1
                        continue
                    playable_event_id = playable_events.get(asset_key)
                    playable_cue = playable_cues.get(asset_key)
                    asset_name = str(asset.get("name") or asset.get("type") or "")
                    asset_is_audio_playable = (
                        "AudioEventPlayable" in asset_name
                        or "AudioDlgEventPlayable" in asset_name
                        or "AudioMusicPlayable" in asset_name
                    )
                    asset_is_audio_music = "AudioMusicPlayable" in asset_name
                    asset_is_audio_cue = "AudioCuePlayable" in asset_name
                    if (
                        wanted
                        and (playable_event_id or asset_is_audio_playable)
                        and display_name not in wanted
                        and playable_event_id not in wanted
                        and not asset_is_audio_music
                    ):
                        continue
                    if playable_event_id and playable_event_id != display_name:
                        if not asset_is_audio_music:
                            stats["timelineCarrierPlayableMismatch"] += 1
                            continue
                        stats["timelineCarrierMusicDisplayNameMismatchAccepted"] += 1
                    if not playable_event_id and not playable_cue and not asset_is_audio_playable and not asset_is_audio_cue:
                        stats["timelineCarrierPlayableTypeUnresolved"] += 1
                        continue
                    parent_name = str(parent.get("name") or "")
                    base_id = normalize_levelsequence_audio_id(parent_name)
                    playable_type = asset_name or "AudioEventPlayable"
                    if not base_id:
                        stats["timelineCarrierNonLevelSequenceParent"] += 1
                    occurrence = {
                        "eventId": playable_event_id or display_name,
                        "timelineClipDisplayName": display_name,
                        "timelineAssetName": parent_name,
                        "timelineAssetNameBase": base_id,
                        "timelineParentNameStatus": (
                            "exactLevelSequenceAudioSuffix"
                            if base_id else "nonLevelSequenceTimelineParent"
                        ),
                        "timelineAssetSerializedFile": parent.get("serializedFile"),
                        "timelineAssetPathId": parent.get("pathId"),
                        "timelineAssetSource": parent.get("source"),
                        "timelineAssetSourceOffset": parent.get("sourceOffset"),
                        "timelineTrackName": name,
                        "timelineClipIndex": clip_index,
                        "timelineTrackSerializedFile": track_identity.get("serializedFile"),
                        "timelineTrackPathId": track_identity.get("pathId"),
                        "timelineTrackSource": track_identity.get("source"),
                        "timelineTrackSourceOffset": track_identity.get("sourceOffset"),
                        "audioPlayableType": playable_type,
                        "audioPlayableRuntimeContractId": (
                            _timeline_audio_runtime_contract_id(playable_type)
                        ),
                        "audioPlayableKeyStatus": (
                            "exactAudioEventPlayableScalar"
                            if playable_event_id
                            else "trackDisplayNameOnlyScalar"
                        ),
                        "audioPlayableSerializedFile": asset.get("serializedFile"),
                        "audioPlayablePathId": asset.get("pathId"),
                        "evidence": (
                            "exactAudioEventPlayableScalarTrackParentAssetPPtrs"
                            if playable_event_id
                            else "exactTimelineTrackDisplayNameAudioPlayableParentAssetPPtrs"
                        ),
                    }
                    if playable_event_id or asset_is_audio_playable:
                        carriers[playable_event_id or display_name].append(occurrence)
                        stats["exactTimelineCarriers"] += 1
                        if asset_is_audio_music:
                            stats["exactTimelineMusicCarriers"] += 1
                    elif playable_cue or asset_is_audio_cue:
                        cue_values = playable_cue or {
                            "startCueName": display_name,
                            "endCueName": "",
                        }
                        if wanted_cues and not any(
                            str(cue_values.get(key) or "").strip().casefold() in wanted_cues
                            for key in ("startCueName", "endCueName")
                        ):
                            continue
                        for cue_role in ("startCueName", "endCueName"):
                            cue_name = str(cue_values.get(cue_role) or "").strip()
                            if not cue_name:
                                continue
                            cue_occurrence = dict(occurrence)
                            cue_occurrence.update({
                                "cueName": cue_name,
                                "cueRole": "start" if cue_role == "startCueName" else "end",
                                "audioPlayableType": asset_name or "AudioCuePlayable",
                                "audioPlayableKeyStatus": (
                                    "exactAudioCuePlayableScalars"
                                    if playable_cue else "trackDisplayNameOnlyAudioCuePlayable"
                                ),
                                "evidence": (
                                    "exactAudioCuePlayableScalarsTrackParentAssetPPtrs"
                                    if playable_cue else
                                    "exactTimelineTrackDisplayNameAudioCuePlayableParentAssetPPtrs"
                                ),
                            })
                            cue_carriers[cue_name.casefold()].append(cue_occurrence)
                            stats["exactTimelineCueCarriers"] += 1
    stats["timelineCarrierEvents"] = len(carriers)
    stats["timelineCarrierCues"] = len(cue_carriers)
    parent_keys = {
        _object_identity_key({
            "serializedFile": row.get("timelineAssetSerializedFile"),
            "pathId": row.get("timelineAssetPathId"),
        })
        for rows in list(carriers.values()) + list(cue_carriers.values())
        for row in rows
    }
    parent_keys.discard(None)
    director_rows: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    if directors_file.is_file() and parent_keys:
        with directors_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    stats["directorDecodeFailures"] += 1
                    continue
                if not isinstance(record, dict) or record.get("recordType") != "object":
                    continue
                stats["playableDirectorRecords"] += 1
                playable_asset = _resolved_pptr(record, "$.m_PlayableAsset")
                key = _object_identity_key(playable_asset)
                if key not in parent_keys:
                    continue
                identity = _object_identity(record)
                director_rows[key].append({
                    "playableDirectorName": str(record.get("name") or "PlayableDirector"),
                    "playableDirectorSerializedFile": identity.get("serializedFile"),
                    "playableDirectorPathId": identity.get("pathId"),
                    "playableDirectorSource": identity.get("source"),
                    "playableDirectorSourceOffset": identity.get("sourceOffset"),
                    "playableDirectorPlayableAssetName": playable_asset.get("name") or "",
                    "evidence": "exactPlayableDirectorPlayableAssetPPtr",
                })
                stats["exactPlayableDirectorLinks"] += 1
    for rows in list(carriers.values()) + list(cue_carriers.values()):
        for row in rows:
            parent_key = _object_identity_key({
                "serializedFile": row.get("timelineAssetSerializedFile"),
                "pathId": row.get("timelineAssetPathId"),
            })
            row["playableDirectors"] = list(director_rows.get(parent_key, []))
    stats["timelineParents"] = len(parent_keys)
    stats["timelineParentsWithDirector"] = sum(
        bool(director_rows.get(key)) for key in parent_keys
    )
    stats["timelineParentsWithoutDirector"] = len(parent_keys) - stats["timelineParentsWithDirector"]
    stats["timelineEventsWithDirector"] = sum(
        any(row.get("playableDirectors") for row in rows)
        for rows in carriers.values()
    )
    return {
        "occurrencesByEvent": dict(carriers),
        "occurrencesByCue": dict(cue_carriers),
        "stats": dict(stats),
        "evidenceBoundary": (
            "AudioEventPlayable scalar keys, Track m_Asset/m_Parent PPtrs, and PlayableDirector "
            "m_PlayableAsset PPtrs are exact serialized-object identity joins. They prove authored "
            "Timeline ownership and Director references, not Director activation, audio posting, or "
            "Wwise leaf selection. The caller may combine the complete StreamingAssets and "
            "Persistent object-index parts."
        ),
    }


def merge_timeline_audio_ownership(
    ownership_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Merge exact Timeline carrier results from multiple object-index sources.

    Story Timeline assets occur in both Unity source domains.  Their serialized
    CAB/path-ID identity is the deduplication key; source proximity or native
    registration order is never used to collapse occurrences.
    """

    occurrences_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    occurrences_by_cue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_events: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    seen_cues: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    stats = Counter()

    def occurrence_marker(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(row.get("timelineAssetSerializedFile") or ""),
            row.get("timelineAssetPathId"),
            str(row.get("timelineTrackSerializedFile") or ""),
            row.get("timelineTrackPathId"),
            row.get("timelineClipIndex"),
            str(row.get("audioPlayableSerializedFile") or ""),
            row.get("audioPlayablePathId"),
            str(row.get("cueName") or ""),
            str(row.get("cueRole") or ""),
        )

    for ownership in ownership_rows:
        if not isinstance(ownership, dict):
            continue
        for key, rows in (ownership.get("occurrencesByEvent") or {}).items():
            event_id = str(key or "").strip().lower()
            if not event_id:
                continue
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                marker = occurrence_marker(row)
                if marker in seen_events[event_id]:
                    continue
                seen_events[event_id].add(marker)
                occurrences_by_event[event_id].append(row)
        for key, rows in (ownership.get("occurrencesByCue") or {}).items():
            cue_id = str(key or "").strip().casefold()
            if not cue_id:
                continue
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                marker = occurrence_marker(row)
                if marker in seen_cues[cue_id]:
                    continue
                seen_cues[cue_id].add(marker)
                occurrences_by_cue[cue_id].append(row)
        for key, value in (ownership.get("stats") or {}).items():
            if isinstance(value, bool):
                stats[key] += int(value)
            elif isinstance(value, int):
                stats[key] += value

    stats["timelineCarrierEvents"] = len(occurrences_by_event)
    stats["timelineCarrierCues"] = len(occurrences_by_cue)
    parent_keys = {
        _object_identity_key({
            "serializedFile": row.get("timelineAssetSerializedFile"),
            "pathId": row.get("timelineAssetPathId"),
        })
        for rows in list(occurrences_by_event.values()) + list(occurrences_by_cue.values())
        for row in rows
    }
    parent_keys.discard(None)
    stats["timelineParents"] = len(parent_keys)
    parent_keys_with_director = {
        _object_identity_key({
            "serializedFile": row.get("timelineAssetSerializedFile"),
            "pathId": row.get("timelineAssetPathId"),
        })
        for rows in list(occurrences_by_event.values()) + list(occurrences_by_cue.values())
        for row in rows
        if row.get("playableDirectors")
    }
    parent_keys_with_director.discard(None)
    stats["timelineParentsWithDirector"] = sum(
        key in parent_keys_with_director for key in parent_keys
    )
    stats["timelineParentsWithoutDirector"] = (
        stats["timelineParents"] - stats["timelineParentsWithDirector"]
    )
    stats["timelineEventsWithDirector"] = sum(
        any(row.get("playableDirectors") for row in rows)
        for rows in occurrences_by_event.values()
    )
    return {
        "occurrencesByEvent": dict(occurrences_by_event),
        "occurrencesByCue": dict(occurrences_by_cue),
        "stats": dict(stats),
        "evidenceBoundary": (
            "Exact AudioEventPlayable scalar keys, Track m_Asset/m_Parent PPtrs, and "
            "PlayableDirector m_PlayableAsset PPtrs are joined across the complete current "
            "StreamingAssets and Persistent object indexes. They prove authored Timeline "
            "ownership and Director references, not Director activation, audio posting, Wwise "
            "branch selection, or selected media leaf."
        ),
    }


def _timeline_raw_mono_payloads(
    export_root: Path,
    identities: Iterable[tuple[Any, Any]],
) -> dict[tuple[str, int], tuple[dict[str, Any], Path] | None]:
    """Bulk-load only requested raw MonoBehaviour identities.

    A per-identity ``Path.glob`` is prohibitively expensive on the large
    Persistent directory.  Enumerate each source directory once and parse
    JSON only when its path-ID suffix is one of the requested identities.
    """

    wanted: set[tuple[str, int]] = set()
    suffixes: set[str] = set()
    for serialized_file, path_id in identities:
        serialized = str(serialized_file or "").strip()
        try:
            numeric_path_id = int(path_id)
        except (TypeError, ValueError):
            continue
        if not serialized:
            continue
        wanted.add((serialized, numeric_path_id))
        suffixes.add(f"{numeric_path_id & ((1 << 64) - 1):016X}")
    cache: dict[tuple[str, int], tuple[dict[str, Any], Path] | None] = {
        identity: None for identity in wanted
    }
    if not wanted:
        return cache
    for source in ("StreamingAssets", "Persistent"):
        raw_root = (
            export_root / "recovered" / "AnimeStudio-cli" / source
            / "json_by_type" / "MonoBehaviour"
        )
        if not raw_root.is_dir():
            continue
        try:
            entries = os.scandir(raw_root)
        except OSError:
            continue
        with entries:
            for entry in entries:
                if not entry.is_file() or not entry.name.lower().endswith(".json"):
                    continue
                stem = entry.name[:-5]
                if "_p" not in stem:
                    continue
                suffix = stem.rsplit("_p", 1)[-1].upper()
                if suffix not in suffixes:
                    continue
                try:
                    unsigned = int(suffix, 16)
                except ValueError:
                    continue
                numeric_path_id = (
                    unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)
                )
                path = Path(entry.path)
                payload = load_json(path, {})
                metadata = payload.get("$animestudio") if isinstance(payload, dict) else None
                if not isinstance(metadata, dict):
                    continue
                identity = (
                    str(metadata.get("sourceFile") or ""),
                    numeric_path_id,
                )
                if identity not in wanted:
                    continue
                try:
                    if int(metadata.get("pathId")) != numeric_path_id:
                        continue
                except (TypeError, ValueError):
                    continue
                cache[identity] = (payload, path)
    return cache


def enrich_timeline_audio_ownership_from_raw_json(
    export_root: Path,
    ownership: dict[str, Any],
) -> dict[str, Any]:
    """Attach exact Timeline clip timing and AudioPlayable controls.

    The compact object-index scalar policy keeps identifiers and PPtrs but not
    every TimelineClip field.  The raw MonoBehaviour JSON is therefore joined
    only for the already exact Track/Playable identities recovered above.
    """

    identities: set[tuple[Any, Any]] = set()
    for rows in list((ownership.get("occurrencesByEvent") or {}).values()) + list(
        (ownership.get("occurrencesByCue") or {}).values()
    ):
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            identities.add((
                row.get("timelineTrackSerializedFile"),
                row.get("timelineTrackPathId"),
            ))
            identities.add((
                row.get("audioPlayableSerializedFile"),
                row.get("audioPlayablePathId"),
            ))
    cache = _timeline_raw_mono_payloads(export_root, identities)
    stats = Counter(ownership.get("stats") or {})
    enriched_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    enriched_cues: dict[str, list[dict[str, Any]]] = defaultdict(list)
    clip_fields = (
        ("m_Start", "timelineClipStartSec"),
        ("m_Duration", "timelineClipDurationSec"),
        ("m_ClipIn", "timelineClipInSec"),
        ("m_TimeScale", "timelineClipTimeScale"),
        ("m_EaseInDuration", "timelineClipEaseInDurationSec"),
        ("m_EaseOutDuration", "timelineClipEaseOutDurationSec"),
        ("m_BlendInDuration", "timelineClipBlendInDurationSec"),
        ("m_BlendOutDuration", "timelineClipBlendOutDurationSec"),
        ("optionIndex", "timelineClipOptionIndex"),
    )
    playable_fields = (
        ("_isCue", "audioPlayableIsCue"),
        ("_stopEventAtClipEnd", "audioPlayableStopEventAtClipEnd"),
        ("_stopEventAtClipEndKey", "audioPlayableStopEventAtClipEndKey"),
        ("_fadeOutTime", "audioPlayableFadeOutMs"),
        ("_enableSeek", "audioPlayableEnableSeek"),
        ("_useBindingObj", "audioPlayableUseBindingObject"),
        ("_is2D", "audioPlayableIs2D"),
        ("musicActionType", "audioMusicActionType"),
        ("triggerOnSkip", "audioMusicTriggerOnSkip"),
    )

    def enrich(row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        track_identity = (
            str(row.get("timelineTrackSerializedFile") or ""),
            row.get("timelineTrackPathId"),
        )
        track_loaded = cache.get(track_identity)
        if track_loaded:
            track_payload, track_path = track_loaded
            clips = track_payload.get("m_Clips") if isinstance(track_payload, dict) else None
            try:
                clip_index = int(row.get("timelineClipIndex"))
            except (TypeError, ValueError):
                clip_index = -1
            clip = clips[clip_index] if isinstance(clips, list) and 0 <= clip_index < len(clips) else None
            if isinstance(clip, dict):
                for source_key, output_key in clip_fields:
                    value = clip.get(source_key)
                    if value is not None:
                        result[output_key] = value
                result["timelineClipTimingEvidence"] = "exactSerializedTimelineClip"
                result["timelineTrackRawJsonPath"] = normalize_posix(
                    track_path.relative_to(export_root)
                )
                if (
                    result.get("timelineClipStartSec") is not None
                    and result.get("timelineClipDurationSec") is not None
                ):
                    result["timelineClipEndSec"] = (
                        float(result["timelineClipStartSec"])
                        + float(result["timelineClipDurationSec"])
                    )
                stats["timelineRawClipTimings"] += 1
            else:
                stats["timelineRawClipPayloadMissing"] += 1
        else:
            stats["timelineRawTrackPayloadMissing"] += 1

        playable_identity = (
            str(row.get("audioPlayableSerializedFile") or ""),
            row.get("audioPlayablePathId"),
        )
        playable_loaded = cache.get(playable_identity)
        if playable_loaded:
            playable_payload, playable_path = playable_loaded
            for source_key, output_key in playable_fields:
                value = playable_payload.get(source_key) if isinstance(playable_payload, dict) else None
                if value is not None:
                    result[output_key] = value
            if isinstance(playable_payload, dict):
                action_type = playable_payload.get("musicActionType")
                if isinstance(action_type, int):
                    result["audioMusicActionTypeLabel"] = (
                        AUDIO_MUSIC_ACTION_TYPE_LABELS.get(action_type)
                        or f"unknown({action_type})"
                    )
                trigger_on_skip = playable_payload.get("triggerOnSkip")
                if isinstance(trigger_on_skip, int) and not isinstance(trigger_on_skip, bool):
                    result["audioMusicTriggerOnSkipLabel"] = (
                        AUDIO_MUSIC_TRIGGER_ON_SKIP_LABELS.get(trigger_on_skip)
                        or f"unknown({trigger_on_skip})"
                    )
            result["audioPlayableControlEvidence"] = "exactSerializedAudioPlayableFields"
            result["audioPlayableRawJsonPath"] = normalize_posix(
                playable_path.relative_to(export_root)
            )
            stats["timelineRawPlayableControls"] += 1
        else:
            stats["timelineRawPlayablePayloadMissing"] += 1
        return result

    for key, rows in (ownership.get("occurrencesByEvent") or {}).items():
        enriched_events[key] = [enrich(row) for row in rows if isinstance(row, dict)]
    for key, rows in (ownership.get("occurrencesByCue") or {}).items():
        enriched_cues[key] = [enrich(row) for row in rows if isinstance(row, dict)]
    return {
        **ownership,
        "occurrencesByEvent": dict(enriched_events),
        "occurrencesByCue": dict(enriched_cues),
        "stats": dict(stats),
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
                        "exactAudioEventPlayableScalar"
                        if occurrence.get("audioPlayableKeyStatus") == "exactAudioEventPlayableScalar"
                        else "exactTimelineTrackDisplayName"
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


def build_timeline_audio_cue_contexts(
    ownership: dict[str, Any],
    cue_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Join AudioCuePlayable carriers to cue definitions and behavior Events.

    The Timeline asset requests a cue, not a Wwise Event.  A behavior Event is
    emitted only when the native-compatible cue hash resolves to an
    AudioCueTable definition with an exact ``behaviourExpr`` type-3 value.
    Unknown cues remain invocation records so the authored trigger is visible
    without fabricating an Event or media relation.
    """

    occurrences_by_cue = ownership.get("occurrencesByCue") or {}
    definitions = cue_semantics.get("cueDefinitions") or {}
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    invocations: list[dict[str, Any]] = []
    stats = Counter()
    event_ids: set[str] = set()

    for cue_key, occurrences in sorted(occurrences_by_cue.items()):
        for occurrence in occurrences:
            if not isinstance(occurrence, dict):
                continue
            cue_name = str(occurrence.get("cueName") or "").strip()
            if not cue_name:
                continue
            cue_id = audio_hash_generator_compute(cue_name)
            cue_signed_id = cue_id if cue_id < 0x80000000 else cue_id - 0x100000000
            definition = definitions.get(cue_id)
            lookup = {
                "cueName": cue_name,
                "cueId": cue_id,
                "cueSignedId": cue_signed_id,
                "cueHex": f"0x{cue_id:08x}",
                "cueHashAlgorithm": "fnv1AsciiLowerUtf16CodeUnits",
                "cueHashEvidence": "nativeAudioHashGeneratorCompute",
                "definitionStatus": "resolved" if isinstance(definition, dict) else "missing",
            }
            if isinstance(definition, dict):
                lookup.update({
                    "handlerCount": int(definition.get("handlerCount") or 0),
                    "directHandlerCount": int(definition.get("directHandlerCount") or 0),
                    "levelHandlerCount": int(definition.get("levelHandlerCount") or 0),
                    "behaviorEventCount": len(definition.get("behaviorEvents") or []),
                    "expressionOperandCount": len(definition.get("expressionOperands") or []),
                })
            invocation = {
                "kind": "timelineAudioCueInvocation",
                "semanticRole": "authoredTimelineAudioCue",
                "confidence": "exact",
                "ownershipEvidenceLevel": "exactSerializedTimelineCarrier",
                "triggerEvidenceLevel": "exact",
                "triggerRole": str(occurrence.get("cueRole") or "start"),
                "runtimeActivationStatus": "playableDirectorRuntimeExecutionNotObserved",
                "triggerRuntimeActivationStatuses": [
                    "timelineCueInvocationExecutionNotObserved",
                    "cueConditionAndHandlerEvaluationRequired",
                    "audioEventRuntimePlaybackUnobserved",
                ],
                "triggerRequestEvidence": [
                    "exactAudioCuePlayableScalars",
                    "exactTimelineTrackPPtr",
                    "exactTimelineParentPPtr",
                ],
                "triggerEvidenceKinds": [
                    "AudioCuePlayable",
                    "TimelineTrack",
                    "PlayableDirector" if occurrence.get("playableDirectors") else "PlayableDirectorUnresolved",
                ],
                "evidence": occurrence.get("evidence") or "exactAudioCuePlayableScalarsTrackParentAssetPPtrs",
                "timelineOwnershipStatus": (
                    "exactTimelineDirectorOwner"
                    if occurrence.get("playableDirectors")
                    else "exactTimelineOwnerDirectorUnresolved"
                ),
                "playableDirectorCount": len(occurrence.get("playableDirectors") or []),
                **lookup,
                **{
                    key: occurrence.get(key)
                    for key in (
                        "cueRole", "timelineAssetName", "timelineAssetNameBase",
                        "timelineAssetSerializedFile", "timelineAssetPathId",
                        "timelineAssetSource", "timelineAssetSourceOffset",
                        "timelineTrackName", "timelineTrackPathId", "timelineClipIndex",
                        "timelineTrackSource", "timelineTrackSourceOffset",
                        "audioPlayableType", "audioPlayableKeyStatus",
                        "audioPlayableSerializedFile", "audioPlayablePathId",
                        "playableDirectors",
                    )
                },
            }
            invocations.append(invocation)
            stats["timelineCueInvocations"] += 1
            if isinstance(definition, dict):
                stats["timelineCueInvocationsResolved"] += 1
                for behavior in definition.get("behaviorEvents") or []:
                    if not isinstance(behavior, dict):
                        continue
                    event_id = str(behavior.get("eventId") or "").strip().lower()
                    if not event_id:
                        continue
                    context = {
                        **invocation,
                        "kind": "timelineAudioCueBehaviorEvent",
                        "semanticRole": "authoredTimelineAudioCueBehaviorEvent",
                        "eventName": event_id,
                        "handlerScope": behavior.get("handlerScope"),
                        "handlerIndex": behavior.get("handlerIndex"),
                        "levelId": behavior.get("levelId"),
                        "expressionSide": behavior.get("expressionSide"),
                        "expressionPath": behavior.get("expressionPath"),
                        "exprType": behavior.get("exprType"),
                        "evidence": "exactTimelineAudioCueToAudioCueBehaviorExpression",
                        "triggerRequestEvidence": [
                            "exactAudioCuePlayableScalars",
                            "nativeAudioHashGeneratorCompute",
                            "audioCueBehaviorExprType3",
                        ],
                    }
                    _append_context(contexts, seen, event_id, context)
                    event_ids.add(event_id)
                    stats["timelineCueBehaviorContexts"] += 1
            else:
                stats["timelineCueInvocationsMissing"] += 1

    stats["timelineCueBehaviorEvents"] = len(event_ids)
    return {
        "eventContexts": dict(contexts),
        "invocations": invocations,
        "stats": dict(stats),
        "evidenceBoundary": (
            "AudioCuePlayable start/end cue names and Timeline/Director PPtrs are exact authored "
            "trigger evidence. Cue hash resolution and behavior Event edges are exact table joins; "
            "Timeline activation, cue conditions/handlers, AudioCueSystem execution, Wwise branch "
            "selection, and media playback remain unobserved."
        ),
    }


def attach_levelscript_radio_contexts(
    media_rows: list[dict[str, Any]],
    export_root: Path,
    levelscript_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Join exact RadioTable line identities to direct AudioDialog media.

    ``radioId`` and each ordered ``audioOverride`` are narrative identities,
    not Wwise Event names.  A media association exists only when the override
    equals the stem of an exported direct ``audioDialogPath``.  Invocation
    detail is attached to the lazy media shard; the returned eager catalog is
    limited to aggregate counts and bounded unresolved/dynamic examples.
    """

    table_path = next((
        export_root / "structured" / source_root / "Table" / "RadioTable.json"
        for source_root in ("Persistent", "StreamingAssets")
        if (
            export_root / "structured" / source_root / "Table" / "RadioTable.json"
        ).is_file()
    ), None)
    payload = load_json(table_path, {}) if table_path else {}
    if not isinstance(payload, dict):
        payload = {}
    table_source = (
        normalize_posix(table_path.relative_to(export_root)) if table_path else ""
    )

    definitions: dict[str, dict[str, Any]] = {}
    lines_by_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_lines: list[dict[str, Any]] = []
    for radio_id, raw_definition in sorted(payload.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_definition, dict):
            continue
        radio_id = str(radio_id)
        definition = {
            "radioId": radio_id,
            "radioType": raw_definition.get("radioType"),
            "priority": raw_definition.get("priority"),
            "continueAfterDialog": raw_definition.get("continueAfterDialog"),
            "continueAfterRadio": raw_definition.get("continueAfterRadio"),
            "source": table_source,
            "lines": [],
        }
        for line_ordinal, raw_line in enumerate(
            raw_definition.get("radioSingleDataList") or []
        ):
            if not isinstance(raw_line, dict):
                continue
            audio_override = str(raw_line.get("audioOverride") or "").strip()
            override_stem = (
                PurePosixPath(audio_override.replace("\\", "/")).stem.casefold()
                if audio_override
                else ""
            )
            line = {
                "radioId": radio_id,
                "lineOrdinal": line_ordinal,
                "authoredIndex": raw_line.get("index"),
                "lineId": str(raw_line.get("id") or ""),
                "audioOverride": audio_override,
                "audioOverrideStem": override_stem,
                "actorNameId": str(raw_line.get("actorNameId") or ""),
                "is3D": raw_line.get("is3D"),
                "source": table_source,
                "audioOverrideIdentityKind": "AudioDialogPathStem",
                "wwiseEventStatus": "notApplicable",
            }
            line = {
                key: value
                for key, value in line.items()
                if value not in (None, "", [])
            }
            definition["lines"].append(line)
            all_lines.append(line)
            if override_stem:
                lines_by_stem[override_stem].append(line)
        definition["lineCount"] = len(definition["lines"])
        definitions[radio_id] = definition

    media_indices_by_stem: dict[str, list[int]] = defaultdict(list)
    for media_index, media in enumerate(media_rows):
        audio_dialog_path = str(media.get("audioDialogPath") or "").strip()
        if not audio_dialog_path:
            continue
        stem = PurePosixPath(audio_dialog_path.replace("\\", "/")).stem.casefold()
        if stem:
            media_indices_by_stem[stem].append(media_index)

    line_identities_by_media: dict[int, list[dict[str, Any]]] = defaultdict(list)
    contexts_by_media: dict[int, list[dict[str, Any]]] = defaultdict(list)
    decoded_line_count = 0
    decoded_media_indices: set[int] = set()
    for line in all_lines:
        media_indices = media_indices_by_stem.get(
            str(line.get("audioOverrideStem") or ""), []
        )
        if not media_indices:
            continue
        decoded_line_count += 1
        for media_index in media_indices:
            decoded_media_indices.add(media_index)
            line_identities_by_media[media_index].append(line)

    invocations = [
        row for row in levelscript_semantics.get("radioInvocations") or []
        if isinstance(row, dict) and str(row.get("radioId") or "")
    ]
    invocations_by_radio: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for invocation in invocations:
        invocations_by_radio[str(invocation["radioId"])].append(invocation)

    missing_definition_items: list[dict[str, Any]] = []
    resolved_invocation_count = 0
    referenced_lines: set[tuple[str, int, str]] = set()
    decoded_referenced_lines: set[tuple[str, int, str]] = set()
    invocation_line_associations = 0
    decoded_invocation_line_associations = 0
    for radio_id, radio_invocations in sorted(invocations_by_radio.items()):
        definition = definitions.get(radio_id)
        if definition is None:
            missing_definition_items.append({
                "radioId": radio_id,
                "invocationCount": len(radio_invocations),
                "actions": dict(sorted(Counter(
                    str(row.get("action") or "") for row in radio_invocations
                ).items())),
                "triggerRoles": sorted({
                    str(row.get("triggerRole") or "") for row in radio_invocations
                    if str(row.get("triggerRole") or "")
                }),
                "sampleLevelScriptIds": sorted({
                    str(row.get("levelScriptId") or "") for row in radio_invocations
                    if str(row.get("levelScriptId") or "")
                })[:3],
            })
            continue
        resolved_invocation_count += len(radio_invocations)
        definition_fields = {
            key: definition.get(key)
            for key in (
                "radioType", "priority", "continueAfterDialog",
                "continueAfterRadio", "lineCount", "source",
            )
            if definition.get(key) not in (None, "", [])
        }
        for line in definition.get("lines") or []:
            marker = (
                radio_id,
                int(line.get("lineOrdinal") or 0),
                str(line.get("audioOverride") or ""),
            )
            referenced_lines.add(marker)
            media_indices = media_indices_by_stem.get(
                str(line.get("audioOverrideStem") or ""), []
            )
            invocation_line_associations += len(radio_invocations)
            if media_indices:
                decoded_referenced_lines.add(marker)
                decoded_invocation_line_associations += len(radio_invocations)
            for media_index in media_indices:
                for invocation in radio_invocations:
                    contexts_by_media[media_index].append({
                        **invocation,
                        "radioDefinition": definition_fields,
                        "radioLine": line,
                        "audioDialogMatchEvidence": "exactAudioDialogPathStem",
                        "runtimeActivationStatus": (
                            "levelScriptActionExecutionNotObserved"
                        ),
                    })

    unresolved_line_items: list[dict[str, Any]] = []
    unresolved_referenced_line_count = 0
    unresolved_referenced_association_count = 0
    for line in all_lines:
        if media_indices_by_stem.get(str(line.get("audioOverrideStem") or "")):
            continue
        radio_id = str(line.get("radioId") or "")
        radio_invocations = invocations_by_radio.get(radio_id, [])
        invocation_count = len(radio_invocations)
        if invocation_count:
            unresolved_referenced_line_count += 1
            unresolved_referenced_association_count += invocation_count
        unresolved_line_items.append({
            **line,
            "triggerInvocationCount": invocation_count,
            "triggerActions": sorted({
                str(row.get("action") or "") for row in radio_invocations
                if str(row.get("action") or "")
            }),
            "triggerRoles": sorted({
                str(row.get("triggerRole") or "") for row in radio_invocations
                if str(row.get("triggerRole") or "")
            }),
            "resolutionStatus": "audioDialogMediaNotDecoded",
        })
    unresolved_line_items.sort(key=lambda row: (
        -int(row.get("triggerInvocationCount") or 0),
        str(row.get("radioId") or ""),
        int(row.get("lineOrdinal") or 0),
    ))

    total_context_count = 0
    stored_context_count = 0
    truncated_media_count = 0
    media_with_trigger_contexts = 0
    for media_index in sorted(decoded_media_indices):
        media = media_rows[media_index]
        line_identities = sorted(
            line_identities_by_media.get(media_index, []),
            key=lambda row: (
                str(row.get("radioId") or ""),
                int(row.get("lineOrdinal") or 0),
            ),
        )
        contexts = sorted(
            contexts_by_media.get(media_index, []),
            key=lambda row: (
                str(row.get("sourcePath") or ""),
                int(row.get("recordStart") or 0),
                str(row.get("radioId") or ""),
                int((row.get("radioLine") or {}).get("lineOrdinal") or 0),
            ),
        )
        stored_contexts = contexts[:RADIO_MEDIA_CONTEXT_LIMIT]
        total_context_count += len(contexts)
        stored_context_count += len(stored_contexts)
        if contexts:
            media_with_trigger_contexts += 1
        if len(stored_contexts) < len(contexts):
            truncated_media_count += 1

        search_terms = {
            str(value)
            for line in line_identities
            for value in (
                line.get("radioId"), line.get("lineId"),
                line.get("audioOverride"), line.get("actorNameId"),
            )
            if value not in (None, "", [])
        }
        for context in contexts:
            for value in (
                context.get("radioId"), context.get("action"),
                context.get("triggerRole"), context.get("levelScriptId"),
                context.get("sourcePath"), context.get("actionMapRole"),
            ):
                if value not in (None, "", []):
                    search_terms.add(str(value))
        sorted_search = sorted(search_terms)
        stored_search = sorted_search[:RADIO_MEDIA_SEARCH_LIMIT]
        media.update({
            "radioTableLineCount": len(line_identities),
            "radioTableLineIdentities": line_identities,
            "radioTriggerContextCount": len(contexts),
            "radioTriggerContextStoredCount": len(stored_contexts),
            "radioTriggerContextsTruncated": len(stored_contexts) < len(contexts),
            "radioTriggerActions": sorted({
                str(row.get("action") or "") for row in contexts
                if str(row.get("action") or "")
            }),
            "radioTriggerRoles": sorted({
                str(row.get("triggerRole") or "") for row in contexts
                if str(row.get("triggerRole") or "")
            }),
            "radioTriggerSearchTermCount": len(sorted_search),
            "radioTriggerSearchStoredCount": len(stored_search),
            "radioTriggerSearchTruncated": len(stored_search) < len(sorted_search),
            "radioTriggerSearch": stored_search,
        })
        if stored_contexts:
            media["radioTriggerContexts"] = stored_contexts

    dynamic_rows = [
        {
            key: row[key]
            for key in (
                "action", "triggerRole", "levelScriptId", "sourceRoot",
                "sourcePath", "recordStart", "recordUid", "recordLocalId",
                "actionMapRole", "unionTag", "serializedMemberCount",
                "sourceField", "binding", "resolutionStatus",
                "candidateRadioIds", "selectionStatus", "getter",
                "getterRecordLocalId", "getterRecordUid", "getterActionMapRole",
                "resolution", "resolutionSourcePath", "triggerRequestEvidence",
                "triggerRuntimeActivationStatuses",
                "radioIdentityKind", "wwiseEventStatus",
            )
            if row.get(key) not in (None, "", [])
        }
        for row in levelscript_semantics.get("dynamicRadioBindings") or []
        if isinstance(row, dict)
    ]

    def bounded(items: list[dict[str, Any]]) -> dict[str, Any]:
        stored = items[:RADIO_CATALOG_ITEM_LIMIT]
        return {
            "totalCount": len(items),
            "storedCount": len(stored),
            "truncated": len(stored) < len(items),
            "items": stored,
        }

    return {
        "schemaVersion": 1,
        "counts": {
            "radioTableDefinitions": len(definitions),
            "radioTableLines": len(all_lines),
            "radioTableUniqueAudioOverrides": len(lines_by_stem),
            "decodedDirectMedia": len(decoded_media_indices),
            "decodedRadioTableLines": decoded_line_count,
            "unresolvedRadioTableLines": len(all_lines) - decoded_line_count,
            "levelScriptRadioActionRecords": int(
                (levelscript_semantics.get("stats") or {}).get("radioActionRecords")
                or 0
            ),
            "constantRadioBindings": len(invocations),
            "dynamicRadioBindings": len(dynamic_rows),
            "resolvedDynamicRadioBindings": sum(
                bool(row.get("candidateRadioIds")) for row in dynamic_rows
            ),
            "uniqueConstantRadioIds": len(invocations_by_radio),
            "resolvedConstantRadioBindings": resolved_invocation_count,
            "unresolvedConstantRadioBindings": (
                len(invocations) - resolved_invocation_count
            ),
            "referencedRadioDefinitions": sum(
                radio_id in definitions for radio_id in invocations_by_radio
            ),
            "referencedRadioLines": len(referenced_lines),
            "decodedReferencedRadioLines": len(decoded_referenced_lines),
            "unresolvedReferencedRadioLines": unresolved_referenced_line_count,
            "invocationLineAssociations": invocation_line_associations,
            "decodedInvocationLineAssociations": (
                decoded_invocation_line_associations
            ),
            "unresolvedInvocationLineAssociations": (
                unresolved_referenced_association_count
            ),
            "mediaRowsWithRadioTableIdentity": len(decoded_media_indices),
            "mediaRowsWithRadioTriggerContexts": media_with_trigger_contexts,
            "radioTriggerContextAssociations": total_context_count,
            "radioTriggerContextAssociationsStored": stored_context_count,
            "mediaRowsWithTruncatedRadioTriggerContexts": truncated_media_count,
        },
        "unresolvedRadioIds": bounded(missing_definition_items),
        "unresolvedRadioLines": bounded(unresolved_line_items),
        "dynamicRadioBindings": bounded(dynamic_rows),
        "evidenceBoundary": (
            "A constant LevelScript radioId selects an exact RadioTable definition. "
            "Its radioSingleDataList order and audioOverride values are authored dialog "
            "identities; an override links to decoded media only by exact audioDialogPath "
            "stem. Neither radioId nor audioOverride is a Wwise Event, and action execution, "
            "line selection, playback, and dynamic radioId values remain unobserved."
            " A resolved dynamic candidate set still leaves its runtime list index and "
            "selected radioId unobserved."
        ),
    }


def _trigger_media_ref(media: dict[str, Any] | None, *, fallback_id: str = "") -> dict[str, Any]:
    """Return a small media reference for the trigger-context shard.

    The event and media shards remain authoritative for full Wwise evidence.
    Trigger contexts only carry the identity needed to navigate to that media,
    plus the small amount of duration/speaker information useful when reading
    a situation without opening another shard.
    """

    media = media if isinstance(media, dict) else {}
    ref: dict[str, Any] = {}
    for key in (
        "id", "mediaId", "src", "rel", "format", "duration",
        "audioDialogPath", "speakerChannel", "audioCategory", "audioScope",
        "sourceLanguage",
    ):
        value = media.get(key)
        if value not in (None, "", []):
            ref[key] = value
    if fallback_id and not ref.get("id"):
        ref["id"] = fallback_id
    return ref


def _compact_trigger_action(context: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "action", "triggerRole", "levelScriptId", "sourceRoot", "sourcePath",
        "recordIndex", "recordStart", "recordUid", "recordLocalId",
        "actionMapRole", "unionTag", "serializedMemberCount", "nativeMappingId",
        "payloadShape", "sourceField", "fields", "runtimeActivationStatus",
    )
    return {
        key: context[key]
        for key in keys
        if context.get(key) not in (None, "", [])
    }


DIALOG_LIFECYCLE_PATH_RE = re.compile(
    r"^(?P<dialogId>[^.]+)\."
    r"(?P<phase>preloadEvents|preEnterEvents|postEnterEvents|preExitEvents|postExitEvents)"
    r"\[(?P<index>\d+)\]$"
)
DIALOG_LIFECYCLE_PHASES = {
    "preloadEvents": {
        "triggerRole": "DialogPreloadAudioEvent",
        "runtimeMethod": "_StartDialogEventPreload",
        "runtimeMethodToken": "0x060099ec",
    },
    "preEnterEvents": {
        "triggerRole": "DialogPreEnterAudioEvent",
        "runtimeMethod": "_OnPreEnterDialog",
        "runtimeMethodToken": "0x060099e7",
    },
    "postEnterEvents": {
        "triggerRole": "DialogPostEnterAudioEvent",
        "runtimeMethod": "_OnPostEnterDialog",
        "runtimeMethodToken": "0x060099e8",
    },
    "preExitEvents": {
        "triggerRole": "DialogPreExitAudioEvent",
        "runtimeMethod": "_OnPreExitDialog",
        "runtimeMethodToken": "0x060099e9",
    },
    "postExitEvents": {
        "triggerRole": "DialogPostExitAudioEvent",
        "runtimeMethod": "_OnPostExitDialog",
        "runtimeMethodToken": "0x060099ea",
    },
}
DIALOG_LIFECYCLE_RUNTIME_CONSUMER = {
    "type": "Beyond.Gameplay.Audio.AudioGameplayStatusSystem",
    "image": "Gameplay.Beyond.dll",
    "typeToken": "0x02001a6f",
    "source": "reports/story/recovery/options/option_flow_runtime_metadata.json",
    "fields": [
        "m_currentDialogId",
        "m_dialogEventStatus",
        "m_pendingDialogAudioEventIds",
        "m_pinnedDialogAudioEventIds",
    ],
    "methods": {
        "schedule": {
            "name": "_ScheduleDialogAudioEvent",
            "token": "0x060099eb",
        },
        "preload": {
            "name": "_StartDialogEventPreload",
            "token": "0x060099ec",
        },
        "preloadCompleted": {
            "name": "_OnDialogEventPreloadCompleted",
            "token": "0x060099ed",
        },
        "triggerPending": {
            "name": "_TriggerAllPendingDialogAudioEvents",
            "token": "0x060099ee",
        },
    },
    "evidenceBoundary": "staticTypeAndMethodMetadataOnly",
}


def _timeline_audio_runtime_contract_id(playable_type: Any) -> str | None:
    """Return a stable static-contract id for a serialized playable type."""

    normalized = re.sub(r"(?:\(Clone\))+$", "", str(playable_type or "")).strip()
    contract = TIMELINE_AUDIO_RUNTIME_CONTRACTS.get(normalized)
    return str(contract.get("id")) if isinstance(contract, dict) else None


def _conversation_line_meanings(
    webui_root: Path,
    language: str,
    *,
    kinds: frozenset[str],
) -> dict[str, dict[str, Any]]:
    meanings: dict[str, dict[str, Any]] = {}
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return meanings
    for path in sorted(conv_root.glob("*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict) or str(payload.get("kind") or "") not in kinds:
            continue
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            line_id = str(line.get("id") or "").strip()
            if not line_id:
                continue
            meanings.setdefault(line_id, {
                key: line[key]
                for key in ("id", "actor", "aid", "text", "slot", "cid", "audio", "duration")
                if line.get(key) not in (None, "", [])
            })
    return meanings


def _build_radio_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    line_meanings: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        media_ref = _trigger_media_ref(media)
        for occurrence_index, raw_context in enumerate(
            media.get("radioTriggerContexts") or []
        ):
            if not isinstance(raw_context, dict):
                continue
            line = raw_context.get("radioLine")
            line = line if isinstance(line, dict) else {}
            radio_id = str(raw_context.get("radioId") or line.get("radioId") or "").strip()
            line_id = str(line.get("lineId") or "").strip()
            source_path = str(raw_context.get("sourcePath") or "").strip()
            record_uid = str(raw_context.get("recordUid") or "").strip()
            trigger_id = ":".join((
                "radio",
                source_path,
                record_uid or str(raw_context.get("recordStart") or occurrence_index),
                radio_id,
                line_id or str(line.get("lineOrdinal") or 0),
            ))
            meaning = line_meanings.get(line_id, {})
            definition = raw_context.get("radioDefinition")
            definition = definition if isinstance(definition, dict) else {}
            action = _compact_trigger_action(raw_context)
            if radio_id and "radioId" not in action:
                action["radioId"] = radio_id
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "radio",
                "triggerRole": str(
                    raw_context.get("triggerRole")
                    or raw_context.get("action")
                    or "play"
                ),
                "situation": {
                    key: value
                    for key, value in {
                        "levelScriptId": raw_context.get("levelScriptId"),
                        "radioId": radio_id,
                        "lineId": line_id,
                        "lineOrdinal": line.get("lineOrdinal"),
                    }.items()
                    if value not in (None, "", [])
                },
                "meaning": meaning,
                "action": action,
                "owner": {
                    "radioId": radio_id,
                    "radioDefinition": definition,
                    "radioLine": line,
                },
                "selection": {
                    "triggerRole": raw_context.get("triggerRole"),
                    "fields": raw_context.get("fields") or {},
                    "lineSelectionStatus": "runtimeLineSelectionUnobserved",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": "exactLevelScriptRadioAction",
                    "owner": "exactRadioTableLine",
                    "media": raw_context.get("audioDialogMatchEvidence")
                    or "audioDialogMediaUnresolved",
                    "runtimeExecution": raw_context.get("runtimeActivationStatus")
                    or "levelScriptActionExecutionNotObserved",
                },
                "runtimeActivationStatus": raw_context.get(
                    "runtimeActivationStatus"
                ) or "levelScriptActionExecutionNotObserved",
                "sourceRefs": [
                    value
                    for value in (
                        source_path,
                        str(line.get("source") or ""),
                        str(media.get("audioDialogPath") or ""),
                    )
                    if value
                ],
            })
    return contexts


def _build_envtalk_trigger_contexts(
    webui_root: Path,
    language: str,
    media_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    media_by_id = {
        str(row.get("id") or "").casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    used_trigger_ids: set[str] = set()
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return contexts
    for path in sorted(conv_root.glob("env_*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            continue
        env_id = str(payload.get("title") or payload.get("key") or "").strip()
        if not env_id:
            continue
        is_greeting = env_id.casefold().startswith("greetenvtalk_")
        if payload.get("kind") != "env" and not is_greeting:
            continue
        semantic_kind = "envTalkGreeting" if is_greeting else "envTalk"
        cooldown = payload.get("cooldown")
        payload_debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        payload_source = payload_debug.get("source") if isinstance(payload_debug.get("source"), dict) else {}
        for line_index, line in enumerate(payload.get("lines") or []):
            if not isinstance(line, dict):
                continue
            audio_id = str(line.get("audio") or "").strip()
            line_debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            debug = line_debug or payload_debug
            source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
            if not source:
                source = payload_source
            hints = debug.get("speakerHints") if isinstance(debug.get("speakerHints"), list) else []
            if not hints and isinstance(payload_debug.get("speakerHints"), list):
                hints = payload_debug["speakerHints"]
            proxy_rows: list[dict[str, Any]] = []
            for hint in hints:
                if not isinstance(hint, dict):
                    continue
                hint_source = hint.get("source") if isinstance(hint.get("source"), dict) else {}
                fields = hint_source.get("fields") if isinstance(hint_source.get("fields"), dict) else {}
                proxy_info = fields.get("proxyInfoData") if isinstance(fields.get("proxyInfoData"), dict) else {}
                if not proxy_info:
                    proxy_info = hint.get("proxyInfoData") if isinstance(hint.get("proxyInfoData"), dict) else {}
                proxy_id = str(hint.get("proxyId") or fields.get("proxyId") or "").strip()
                if not proxy_id:
                    continue
                proxy_row = {
                    key: value
                    for key, value in {
                        "proxyId": proxy_id,
                        "levelId": fields.get("levelId"),
                        "npcId": proxy_info.get("npcId"),
                        "npcNameId": proxy_info.get("npcNameId"),
                        "npcProxyType": proxy_info.get("npcProxyType"),
                    }.items()
                    if value not in (None, "", [])
                }
                if proxy_row not in proxy_rows:
                    proxy_rows.append(proxy_row)
            media = media_by_id.get(audio_id.casefold(), {})
            media_ref = _trigger_media_ref(media, fallback_id=audio_id)
            if not media_ref.get("src") and line.get("audioSrc"):
                media_ref["src"] = line.get("audioSrc")
            audio_meta = line.get("audioMeta") if isinstance(line.get("audioMeta"), dict) else {}
            for key in ("duration", "audioDialogPath", "speakerChannel", "audioCategory"):
                if media_ref.get(key) in (None, "") and audio_meta.get(key) not in (None, ""):
                    media_ref[key] = audio_meta[key]
            proxy_ids = sorted({str(row.get("proxyId")) for row in proxy_rows})
            level_ids = sorted({
                str(row.get("levelId"))
                for row in proxy_rows
                if str(row.get("levelId") or "")
            })
            slot_id = line.get("slot")
            line_id = str(line.get("id") or env_id).strip()
            slot_actor_id = str(line.get("aid") or "").strip()
            slot_actor_match_status = (
                "exactProxyIdMatch"
                if slot_actor_id and slot_actor_id.casefold() in {
                    str(value.get("proxyId") or "").casefold()
                    for value in proxy_rows
                }
                else (
                    "proxyHintDoesNotMatchLineActor"
                    if proxy_rows and slot_actor_id
                    else "lineActorOrProxyOwnerUnresolved"
                )
            )
            base_trigger_id = ":".join((
                "envTalk",
                env_id,
                str(line.get("cid") or line_index + 1),
                str(slot_id if slot_id is not None else "unknown"),
                audio_id or line_id,
            ))
            trigger_id = base_trigger_id
            if trigger_id in used_trigger_ids:
                trigger_id = f"{base_trigger_id}:line{line_index}"
                suffix = 2
                while trigger_id in used_trigger_ids:
                    trigger_id = f"{base_trigger_id}:line{line_index}:{suffix}"
                    suffix += 1
            used_trigger_ids.add(trigger_id)
            owner_status = "exactNpcProxyTableSpeakerHint" if proxy_rows else "envTalkOwnerUnresolved"
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": semantic_kind,
                "triggerRole": (
                    "NpcProxyEnvTalkGreeting"
                    if is_greeting and proxy_rows
                    else "EnvTalkGreetingOwnerUnresolved"
                    if is_greeting
                    else "NpcProxyEnvTalk"
                    if proxy_rows
                    else "EnvTalkOwnerUnresolved"
                ),
                "situation": {
                    "envTalkId": env_id,
                    "envTalkVariant": "greetEnvTalk" if is_greeting else "envTalk",
                    "mission": payload.get("mission"),
                    "levelIds": level_ids,
                    "proxyIds": proxy_ids,
                    "cooldown": cooldown,
                },
                "meaning": {
                    key: line[key]
                    for key in ("id", "actor", "aid", "text", "audio", "slot", "cid", "duration")
                    if line.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "EnvTalkGreetingRuntimeSelection" if is_greeting else "EnvTalkRuntimeSelection",
                    "runtimeActivationStatus": "envTalkRuntimeExecutionNotObserved",
                },
                "owner": {
                    "proxyRows": proxy_rows,
                    "slotActorId": line.get("aid"),
                    "slotActorMatchStatus": slot_actor_match_status,
                    "speakerChannel": media_ref.get("speakerChannel") or audio_meta.get("speakerChannel"),
                },
                "selection": {
                    "slotId": slot_id,
                    "lineIndex": line_index,
                    "slotSelectionStatus": "runtimeSlotSelectionUnobserved",
                    "triggerDistanceStatus": "authoredTriggerDistanceNotRecoveredInConversationRow",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": (
                        "exactEnvTalkTableGreeting"
                        if is_greeting
                        else str(source.get("envTalkId") or env_id)
                    ),
                    "owner": owner_status,
                    "media": "playable" if media_ref.get("src") else "audioDialogMediaUnresolved",
                    "runtimeExecution": "envTalkRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "envTalkRuntimeExecutionNotObserved",
                "sourceRefs": [
                    normalize_posix(path.relative_to(webui_root)),
                    str(
                        debug.get("table")
                        or (source.get("table") if isinstance(source, dict) else "")
                        or ""
                    ),
                    str(source.get("envTalkId") or env_id),
                ],
            })
    return contexts


def _build_remote_common_event_contexts(
    export_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Expose exact RemoteCommon auto-play Event requests in event rows.

    ``audioId`` is the authored SFX/Wwise Event request. ``voiceId`` is a
    separate dialogue identity and remains separate from the Event/media
    route. These low-level contexts prevent an authored RemoteCommon Event
    from being synthesized as a Timeline ownership gap.
    """

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    table_paths = [
        export_root / "structured" / source_root / "Table" / "RemoteCommonTable.json"
        for source_root in ("Persistent", "StreamingAssets")
    ]
    for table_path in table_paths:
        payload = load_json(table_path, {})
        if not isinstance(payload, dict):
            continue
        try:
            source_ref = normalize_posix(table_path.relative_to(export_root))
        except ValueError:
            source_ref = normalize_posix(table_path)
        for remote_id, row in sorted(payload.items(), key=lambda item: str(item[0])):
            if not isinstance(row, dict) or row.get("autoPlay") is not True:
                continue
            remote_id = str(remote_id or "").strip()
            if not remote_id:
                continue
            for line_index, line in enumerate(row.get("remoteCommSingleDataList") or []):
                if not isinstance(line, dict):
                    continue
                audio_id = str(line.get("audioId") or "").strip()
                if not audio_id:
                    continue
                single_id = str(line.get("singleId") or f"{remote_id}:{line_index + 1}").strip()
                _append_context(contexts, seen, audio_id, {
                    "kind": "remoteCommonAudio",
                    "semanticRole": "remoteCommonAutoPlayAudioEvent",
                    "confidence": "exact",
                    "ownershipEvidenceLevel": "exactRemoteCommonSingleDataListRow",
                    "triggerEvidenceLevel": "exact",
                    "triggerBindingStatus": "exactRemoteCommonAudioId",
                    "triggerRole": "RemoteCommonTableAutoPlay",
                    "remoteCommonId": remote_id,
                    "singleId": single_id,
                    "index": line.get("index", line_index + 1),
                    "middleId": line.get("middleId"),
                    "actorList": line.get("actorList") or [],
                    "voiceId": line.get("voiceId"),
                    "voiceLinkStatus": "separateRemoteCommonVoiceId",
                    "authoredEventId": audio_id,
                    "autoPlay": True,
                    "autoPlayTime": line.get("autoPlayTime"),
                    "startAudioEvent": row.get("startAudioEvent"),
                    "endAudioEvent": row.get("endAudioEvent"),
                    "source": source_ref,
                    "sourcePath": source_ref,
                    "evidence": "exactRemoteCommonTableAutoPlay",
                    "triggerRequestEvidence": [
                        "exactRemoteCommonTableAutoPlay",
                        "exactRemoteCommonAudioId",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "remoteCommonAutoPlayExecutionNotObserved",
                    ],
                    "triggerOwnershipMethods": [
                        "RemoteCommonTable.remoteCommSingleDataList",
                    ],
                    "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    "evidenceBoundary": (
                        "RemoteCommonTable autoPlay and the exact single-data audioId "
                        "prove an authored Event request. The row does not prove "
                        "RemoteCommon selection, execution, PostEvent, or an audible "
                        "Wwise media leaf; voiceId remains a separate dialogue identity."
                    ),
                })
    return dict(contexts)


def _build_remote_common_trigger_contexts(
    export_root: Path,
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact RemoteCommonTable auto-play Event requests.

    ``audioId`` is the SFX/Wwise Event used by the automatic remote-communication
    surface.  ``voiceId`` is a separate dialogue voice identity and is retained
    as such; it is never merged into the Event/media candidate.
    """

    event_by_id = {
        str(event.get("id") or "").casefold(): event
        for event in event_rows
        if isinstance(event, dict) and str(event.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    table_paths = [
        export_root / "structured" / source_root / "Table" / "RemoteCommonTable.json"
        for source_root in ("Persistent", "StreamingAssets")
    ]
    for table_path in table_paths:
        payload = load_json(table_path, {})
        if not isinstance(payload, dict):
            continue
        try:
            source_ref = normalize_posix(table_path.relative_to(export_root))
        except ValueError:
            source_ref = normalize_posix(table_path)
        for remote_id, row in sorted(payload.items(), key=lambda item: str(item[0])):
            if not isinstance(row, dict) or row.get("autoPlay") is not True:
                continue
            remote_id = str(remote_id or "").strip()
            if not remote_id:
                continue
            for line_index, line in enumerate(row.get("remoteCommSingleDataList") or []):
                if not isinstance(line, dict):
                    continue
                audio_id = str(line.get("audioId") or "").strip()
                if not audio_id:
                    continue
                single_id = str(line.get("singleId") or f"{remote_id}:{line_index + 1}").strip()
                identity = (remote_id.casefold(), single_id.casefold(), audio_id.casefold())
                if identity in seen:
                    continue
                seen.add(identity)
                event = event_by_id.get(audio_id.casefold(), {})
                media_refs = [
                    _trigger_media_ref(media, fallback_id=audio_id)
                    for media in event.get("media") or []
                    if isinstance(media, dict)
                ]
                media_refs = [media for media in media_refs if media]
                found_in_wwise = event.get("foundInWwise") is True
                if media_refs and any(media.get("src") for media in media_refs):
                    media_status = "directWwiseMediaCandidate"
                    media_evidence = "exactWwiseEventDirectSound"
                elif found_in_wwise:
                    media_status = "wwiseEventHasNoDecodedMedia"
                    media_evidence = "wwiseEventHasNoDecodedMediaLeaf"
                else:
                    media_status = "audioEventUnresolved"
                    media_evidence = "audioIdMissingFromCurrentWwiseIndex"
                event_hash = event.get("hash")
                if isinstance(event_hash, int):
                    event_hash &= 0xFFFFFFFF
                event_meaning = {
                    key: event.get(key)
                    for key in (
                        "category", "foundInWwise", "possibleMediaCount", "playRootCount",
                        "runtimeSelection", "mediaRelationTypes", "traversalStatus",
                    )
                    if event.get(key) not in (None, "", [])
                }
                if event_hash is not None:
                    event_meaning["eventHash"] = event_hash
                contexts.append({
                    "triggerId": ":".join(("remoteCommonAudio", remote_id, single_id, audio_id)),
                    "semanticKind": "remoteCommonAudio",
                    "triggerRole": "RemoteCommonTableAutoPlay",
                    "situation": {
                        "remoteCommonId": remote_id,
                        "singleId": single_id,
                        "index": line.get("index", line_index + 1),
                        "middleId": line.get("middleId"),
                        "autoPlay": True,
                        "autoPlayTime": line.get("autoPlayTime"),
                        "startAudioEvent": row.get("startAudioEvent"),
                        "endAudioEvent": row.get("endAudioEvent"),
                        "eventId": audio_id,
                        "eventHash": event_hash,
                    },
                    "meaning": {
                        "id": single_id,
                        "audio": audio_id,
                        "eventId": audio_id,
                        **event_meaning,
                    },
                    "action": {
                        "action": "RemoteCommonAutoPlay",
                        "triggerRole": "RemoteCommonTableAutoPlay",
                        "sourcePath": source_ref,
                        "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    },
                    "owner": {
                        "remoteCommonId": remote_id,
                        "singleId": single_id,
                        "middleId": line.get("middleId"),
                        "actorList": line.get("actorList") or [],
                        "voiceId": line.get("voiceId"),
                        "voiceLinkStatus": "separateRemoteCommonVoiceId",
                    },
                    "selection": {
                        "autoPlay": True,
                        "autoPlayTime": line.get("autoPlayTime"),
                        "audioSelectionStatus": "exactRemoteCommonAudioId",
                        "mediaSelectionStatus": media_status,
                        "runtimeSelectionStatus": "remoteCommonAutoPlaySelectionUnobserved",
                    },
                    "mediaRefs": media_refs,
                    "evidence": {
                        "definition": "exactRemoteCommonTableAutoPlay",
                        "owner": "exactRemoteCommonSingleDataListRow",
                        "media": media_evidence,
                        "runtimeExecution": "remoteCommonAutoPlayExecutionNotObserved",
                        "voice": "voiceId remains a separate dialogue identity",
                    },
                    "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    "sourceRefs": [
                        source_ref,
                        remote_id,
                        single_id,
                        audio_id,
                        str(line.get("voiceId") or ""),
                    ],
                })
    return contexts


def _build_dialog_timeline_trigger_contexts(
    webui_root: Path,
    language: str,
    media_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose authored DialogTrunk timeline voice placements.

    These rows are deliberately separate from Wwise Event/Timeline carrier
    rows.  A dialog line can have an exact serialized timeline schedule and a
    playable AudioDialog file without being a Wwise Event at all.
    """

    media_by_id = {
        str(row.get("id") or "").casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return contexts
    for path in sorted(conv_root.glob("dlg_*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict) or payload.get("kind") != "dlg":
            continue
        dialog_key = str(payload.get("key") or path.stem).strip()
        payload_debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        line_order = payload_debug.get("lineOrder") if isinstance(payload_debug.get("lineOrder"), dict) else {}
        timeline_sources = [
            source
            for source in line_order.get("sources") or []
            if isinstance(source, dict)
        ]
        source_refs = [
            str(value)
            for source in timeline_sources
            for value in (source.get("sourceKey"), source.get("file"))
            if value
        ]
        for line_index, line in enumerate(payload.get("lines") or []):
            if not isinstance(line, dict):
                continue
            line_debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing = line_debug.get("timelineTiming") if isinstance(line_debug.get("timelineTiming"), dict) else {}
            timeline_id = str(timing.get("timeline") or line.get("timeline") or "").strip()
            if not timeline_id:
                continue
            line_id = str(line.get("id") or f"{dialog_key}:{line_index}").strip()
            audio_id = str(line.get("audio") or "").strip()
            media = media_by_id.get(audio_id.casefold(), {})
            media_ref = _trigger_media_ref(media, fallback_id=audio_id)
            if not media_ref.get("src") and line.get("audioSrc"):
                media_ref["src"] = line.get("audioSrc")
            audio_meta = line.get("audioMeta") if isinstance(line.get("audioMeta"), dict) else {}
            for key in (
                "duration", "audioDialogPath", "speakerChannel", "audioCategory",
            ):
                if media_ref.get(key) in (None, "") and audio_meta.get(key) not in (None, ""):
                    media_ref[key] = audio_meta[key]
            line_source_refs = list(source_refs)
            line_source_refs.extend(
                value
                for value in (
                    normalize_posix(path.relative_to(webui_root)),
                    timeline_id,
                    str(line_debug.get("table") or ""),
                )
                if value
            )
            trigger_id = ":".join((
                "dialogTimeline",
                dialog_key,
                timeline_id,
                line_id,
            ))
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "dialogTimeline",
                "triggerRole": "DialogTimelineVoice",
                "situation": {
                    "dialogKey": dialog_key,
                    "timelineId": timeline_id,
                    "lineId": line_id,
                    "timelineStartSec": timing.get("start"),
                    "timelineDurationSec": timing.get("duration"),
                },
                "meaning": {
                    key: line[key]
                    for key in (
                        "id", "actor", "aid", "text", "audio", "slot", "cid", "duration",
                    )
                    if line.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "DialogTimelineVoice",
                    "timelineId": timeline_id,
                    "runtimeActivationStatus": "dialogTimelineRuntimeExecutionNotObserved",
                },
                "owner": {
                    "dialogKey": dialog_key,
                    "timelineId": timeline_id,
                    "speakerActorId": line.get("aid"),
                    "speakerChannel": media_ref.get("speakerChannel") or audio_meta.get("speakerChannel"),
                },
                "selection": {
                    "lineIndex": line_index,
                    "timelineStartSec": timing.get("start"),
                    "timelineDurationSec": timing.get("duration"),
                    "lineScheduleStatus": "exactDialogTimelineTiming",
                    "mediaSelectionStatus": "audioDialogIdentityJoined",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": "exactDialogTimelineTiming",
                    "owner": "exactDialogTimelineSource",
                    "media": "playable" if media_ref.get("src") else "audioDialogMediaUnresolved",
                    "runtimeExecution": "dialogTimelineRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "dialogTimelineRuntimeExecutionNotObserved",
                "sourceRefs": sorted(set(line_source_refs)),
            })
    return contexts


def _build_dialog_lifecycle_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact AudioDialogCustomEventTable lifecycle hooks.

    The table binds a dialog id and a phase array slot to a uint32 Wwise Event
    id.  The event/media shards remain authoritative for Wwise traversal; this
    catalog only adds the authored dialog-state situation and the static
    ``AudioGameplayStatusSystem`` method shape.  It deliberately does not
    claim that the dialog state transition or the Wwise event was executed.
    """

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        found_in_wwise = event.get("foundInWwise") is True
        if found_in_wwise and media_refs:
            media_selection_status = "wwiseEventMediaCandidates"
            media_evidence = "wwiseEventMediaCandidate"
        elif found_in_wwise:
            media_selection_status = "wwiseEventHasNoDecodedMedia"
            media_evidence = "wwiseEventHasNoDecodedMediaLeaf"
        else:
            media_selection_status = "authoredEventUnresolved"
            media_evidence = "authoredEventMissingFromCurrentWwiseIndex"
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if not isinstance(raw_context, dict):
                continue
            if raw_context.get("kind") != "tableEventHash":
                continue
            if raw_context.get("table") != "AudioDialogCustomEventTable":
                continue
            match = DIALOG_LIFECYCLE_PATH_RE.fullmatch(
                str(raw_context.get("path") or "")
            )
            if not match:
                continue
            phase = match.group("phase")
            phase_info = DIALOG_LIFECYCLE_PHASES[phase]
            dialog_id = match.group("dialogId")
            array_index = int(match.group("index"))
            event_hash = raw_context.get("eventHash")
            if not isinstance(event_hash, int):
                event_hash = event.get("hash")
            if isinstance(event_hash, int):
                event_hash &= 0xFFFFFFFF
            authored_value = raw_context.get("signedValue")
            event_key = event_id or (
                f"0x{event_hash:08x}" if isinstance(event_hash, int) else "unknown"
            )
            trigger_id = ":".join((
                "dialogLifecycle",
                dialog_id,
                phase,
                str(array_index),
                event_key,
            ))
            meaning = {
                key: event.get(key)
                for key in (
                    "id", "name", "hash", "category", "foundInWwise",
                    "possibleMediaCount", "playRootCount", "runtimeSelection",
                    "mediaRelationTypes", "traversalStatus", "unresolvedNodeCount",
                )
                if event.get(key) not in (None, "", [])
            }
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "dialogLifecycle",
                "triggerRole": phase_info["triggerRole"],
                "situation": {
                    "dialogId": dialog_id,
                    "lifecyclePhase": phase,
                    "arrayIndex": array_index,
                    "eventId": event_id,
                    "eventHash": event_hash,
                    "authoredSignedValue": authored_value,
                    "tablePath": raw_context.get("path"),
                },
                "meaning": meaning,
                "action": {
                    "action": "DialogLifecycleAudioEvent",
                    "lifecyclePhase": phase,
                    "runtimeMethod": phase_info["runtimeMethod"],
                    "runtimeMethodToken": phase_info["runtimeMethodToken"],
                    "runtimeActivationStatus": "dialogLifecycleRuntimeExecutionNotObserved",
                },
                "owner": {
                    "dialogId": dialog_id,
                    "sourceTable": "AudioDialogCustomEventTable",
                    "lifecycleField": phase,
                    "ownerStatus": "exactDialogIdAndLifecycleField",
                },
                "selection": {
                    "triggerBindingStatus": "exactAudioDialogCustomEventTable",
                    "mediaSelectionStatus": media_selection_status,
                    "runtimeDispatchStatus": "dialogLifecycleDispatchUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactAudioDialogCustomEventTable",
                    "owner": "exactAudioDialogCustomEventTableDialogIdAndPhase",
                    "media": media_evidence,
                    "runtimeExecution": "dialogLifecycleRuntimeExecutionNotObserved",
                    "requestEvidence": [
                        "exactAudioDialogCustomEventTableField",
                        "exactDialogLifecycleRuntimeMethodMetadata",
                    ],
                },
                "runtimeActivationStatus": "dialogLifecycleRuntimeExecutionNotObserved",
                "sourceRefs": [
                    value
                    for value in (
                        str(raw_context.get("source") or ""),
                        str(raw_context.get("path") or ""),
                        event_id,
                    )
                    if value
                ],
            })
    return contexts


def _build_timeline_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_rows = list(event_rows)
    contexts: list[dict[str, Any]] = []
    event_ids_with_serialized_carrier = {
        str(event.get("id") or "").strip()
        for event in event_rows
        if isinstance(event, dict)
        and str(event.get("id") or "").strip()
        and any(
            isinstance(context, dict)
            and context.get("kind") in {"levelSequenceAudio", "cutsceneTimeline"}
            and context.get("audioPlayableRuntimeContractId")
            for context in event.get("contexts") or []
        )
    }
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") not in {
                "levelSequenceAudio",
                "cutsceneTimeline",
            }:
                continue
            context_kind = str(context.get("kind") or "")
            asset = str(context.get("timelineAssetName") or "")
            serialized_file = str(context.get("timelineAssetSerializedFile") or "")
            path_id = context.get("timelineAssetPathId")
            playable_path_id = context.get("audioPlayablePathId")
            story_key = str(context.get("storyKey") or "")
            trigger_id = ":".join((
                "timeline",
                event_id,
                context_kind,
                serialized_file or "unknown",
                str(path_id if path_id is not None else occurrence_index),
                str(playable_path_id if playable_path_id is not None else "unknown"),
            ))
            owner = {
                key: context[key]
                for key in (
                    "timelineAssetName", "timelineAssetSerializedFile", "timelineAssetPathId",
                    "timelineAssetSource", "timelineAssetSourceOffset", "timelineTrackName",
                    "timelineClipIndex", "timelineClipDisplayName", "timelineClipStartSec",
                    "timelineClipDurationSec", "timelineClipEndSec", "timelineClipInSec",
                    "timelineClipTimeScale", "timelineClipEaseInDurationSec",
                    "timelineClipEaseOutDurationSec", "timelineClipBlendInDurationSec",
                    "timelineClipBlendOutDurationSec", "timelineClipOptionIndex",
                    "timelineClipTimingEvidence", "timelineTrackRawJsonPath",
                    "timelineTrackSerializedFile", "timelineTrackPathId",
                    "timelineTrackSource", "timelineTrackSourceOffset", "audioPlayableType",
                    "audioPlayableRuntimeContractId",
                    "audioPlayableSerializedFile", "audioPlayablePathId", "audioPlayableIsCue",
                    "audioPlayableStopEventAtClipEnd", "audioPlayableStopEventAtClipEndKey",
                    "audioPlayableFadeOutMs", "audioPlayableEnableSeek",
                    "audioPlayableUseBindingObject", "audioPlayableIs2D",
                    "audioMusicActionType", "audioMusicActionTypeLabel",
                    "audioMusicTriggerOnSkip", "audioMusicTriggerOnSkipLabel",
                    "audioPlayableControlEvidence", "audioPlayableRawJsonPath",
                    "playableDirectorCount",
                    "playableDirectorNames", "playableDirectorPathIds", "directorEvidence",
                    "storyKey", "evidence",
                )
                if context.get(key) not in (None, "", [])
            }
            if context_kind == "cutsceneTimeline" and not context.get(
                "audioPlayableRuntimeContractId"
            ):
                owner["runtimeCarrierStatus"] = (
                    "eventIdAlsoHasSerializedTimelineCarrier"
                    if event_id in event_ids_with_serialized_carrier
                    else "storyCutsceneAudioReferenceOnly"
                )
            source_refs = [
                str(value)
                for value in (
                    context.get("timelineAssetSource"),
                    context.get("timelineTrackSource"),
                )
                if value
            ]
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "timelineAudio",
                "triggerRole": context.get("triggerRole") or (
                    "CutsceneTimelineAudio"
                    if context_kind == "cutsceneTimeline"
                    else "TimelineAssetPlayback"
                ),
                "situation": {
                    "eventId": event_id,
                    "contextKind": context_kind,
                    "storyKey": story_key,
                    "timelineAssetName": asset,
                    "timelineClipDisplayName": context.get("timelineClipDisplayName"),
                    "timelineStartSec": context.get("timelineClipStartSec"),
                    "timelineDurationSec": context.get("timelineClipDurationSec"),
                    "timelineEndSec": context.get("timelineClipEndSec"),
                    "timelineParentNameStatus": context.get("timelineParentNameStatus"),
                    "levelSequenceId": context.get("levelSequenceId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "authoredTimelineKeyStatus": (
                        "matchedCurrentWwiseEvent"
                        if event.get("foundInWwise")
                        else "authoredTimelineKeyNotInCurrentWwiseIndex"
                    ),
                    "mediaRelationTypes": event.get("mediaRelationTypes") or [],
                },
                "action": {
                    key: context[key]
                    for key in (
                        "triggerRole", "levelSequenceId", "levelScriptActionCount",
                        "levelScriptIds", "levelScriptSourcePaths", "levelSequenceFieldOffsets",
                    )
                    if context.get(key) not in (None, "", [])
                },
                "owner": owner,
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "confidence": context.get("confidence"),
                    "contextKind": context_kind,
                    "runtimeSelection": event.get("runtimeSelection"),
                    "mediaSelectionStatus": (
                        "wwiseSelectionUnobserved"
                        if event.get("foundInWwise")
                        else "authoredTimelineMediaUnresolved"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerEvidenceLevel")
                    or context.get("evidence")
                    or "inferred",
                    "owner": context.get("ownershipEvidenceLevel")
                    or (
                        "authoredTimelineOrLevelSequence"
                        if context_kind == "cutsceneTimeline"
                        else "exactSerializedTimelineCarrier"
                    ),
                    "media": (
                        "wwiseEventMediaCandidate"
                        if event.get("foundInWwise")
                        else "authoredTimelineKeyNotInCurrentWwiseIndex"
                    ),
                    "runtimeExecution": context.get("runtimeActivationStatus")
                        or (
                        "cutsceneTimelineRuntimeExecutionNotObserved"
                        if context_kind == "cutsceneTimeline"
                        else "audioEventRuntimePlaybackUnobserved"
                    ),
                    "requestEvidence": [
                        value
                        for value in (
                            (
                                "exactAudioEventPlayableScalar"
                                if context.get("audioPlayableKeyStatus")
                                == "exactAudioEventPlayableScalar"
                                else "exactTimelineTrackDisplayName"
                            )
                            if context.get("audioPlayableKeyStatus")
                            or context.get("timelineTrackPathId") is not None
                            else (
                                "storyCutsceneAudioEventList"
                                if context_kind == "cutsceneTimeline"
                                else None
                            ),
                            (
                                "exactTimelineTrackPPtr"
                                if context.get("timelineTrackPathId") is not None
                                else None
                            ),
                            (
                                "exactTimelineParentPPtr"
                                if context.get("timelineAssetPathId") is not None
                                else None
                            ),
                            context.get("timelineClipTimingEvidence"),
                            context.get("audioPlayableControlEvidence"),
                        )
                        if value
                    ],
                },
                "runtimeActivationStatus": context.get(
                    "runtimeActivationStatus"
                ) or (
                    "cutsceneTimelineRuntimeExecutionNotObserved"
                    if context_kind == "cutsceneTimeline"
                    else "audioEventRuntimePlaybackUnobserved"
                ),
                "sourceRefs": source_refs,
            })
    return contexts


def _build_lua_post_event_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if not isinstance(raw_context, dict) or raw_context.get("kind") != "luaPostEvent":
                continue
            source = str(raw_context.get("source") or "")
            line = int(raw_context.get("line") or 0)
            contexts.append({
                "triggerId": f"luaPostEvent:{source}:{line}:{occurrence_index}:{event_id}",
                "semanticKind": "luaPostEvent",
                "triggerRole": "scriptedEventRequest",
                "situation": {
                    "eventId": event_id,
                    "eventHash": raw_context.get("eventHash"),
                    "luaSource": source,
                    "line": line,
                    "expression": raw_context.get("expression"),
                },
                "meaning": {
                    key: event.get(key)
                    for key in (
                        "id", "name", "hash", "category", "foundInWwise",
                        "possibleMediaCount", "runtimeSelection", "traversalStatus",
                    )
                    if event.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "AudioAdapter.PostEvent",
                    "runtimeActivationStatus": "luaBranchExecutionNotObserved",
                },
                "owner": {
                    "luaSource": source,
                    "ownerStatus": "exactLuaFileAndLine",
                },
                "selection": {
                    "triggerBindingStatus": "exactDecryptedLuaPostEventLiteral",
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates"
                        if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactDecryptedLuaPostEventLiteral",
                    "owner": "exactLuaFileAndLine",
                    "media": (
                        "wwiseEventMediaCandidate"
                        if media_refs
                        else "noDecodedMediaLeaf"
                    ),
                    "runtimeExecution": "luaBranchExecutionNotObserved",
                },
                "runtimeActivationStatus": "luaBranchExecutionNotObserved",
                "sourceRefs": [value for value in (source, f"line:{line}", event_id) if value],
            })
    return contexts


def build_trigger_context_catalog(
    event_rows: Iterable[dict[str, Any]],
    media_rows: Iterable[dict[str, Any]],
    webui_root: Path,
    language: str,
    export_root: Path | None = None,
) -> dict[str, Any]:
    """Build one navigable trigger -> situation -> media surface.

    This is intentionally a reference layer over the existing event/media
    shards. It does not merge authored ownership with runtime execution and it
    does not invent a trigger for a media file that has only a table identity.
    """

    event_rows = list(event_rows)
    media_rows = list(media_rows)
    line_meanings = _conversation_line_meanings(
        webui_root,
        language,
        kinds=frozenset({"radio"}),
    )
    grouped = {
        "radio": _build_radio_trigger_contexts(media_rows, line_meanings),
        "envTalk": _build_envtalk_trigger_contexts(webui_root, language, media_rows),
        "remoteCommonAudio": (
            _build_remote_common_trigger_contexts(export_root, event_rows)
            if export_root is not None
            else []
        ),
        "dialogTimeline": _build_dialog_timeline_trigger_contexts(
            webui_root,
            language,
            media_rows,
        ),
        "dialogLifecycle": _build_dialog_lifecycle_trigger_contexts(event_rows),
        "timelineAudio": _build_timeline_trigger_contexts(event_rows),
        "luaPostEvent": _build_lua_post_event_trigger_contexts(event_rows),
    }
    contexts = [row for rows in grouped.values() for row in rows]
    contexts.sort(key=lambda row: (str(row.get("semanticKind") or ""), str(row.get("triggerId") or "")))
    counts = Counter(str(row.get("semanticKind") or "unknown") for row in contexts)
    coverage = {
        "radio": {
            "source": "media.radioTriggerContexts",
            "conversationLineIds": len(line_meanings),
            "storedTriggerContextRows": len(grouped["radio"]),
            "unresolvedRowsRemainIn": "triggerCatalog.levelScriptRadio.unresolvedRadioLines",
        },
        "envTalk": {
            "source": "conv/env_*.json lines",
            "storedTriggerContextRows": len(grouped["envTalk"]),
            "greetingRows": sum(
                str(row.get("semanticKind") or "") == "envTalkGreeting"
                for row in grouped["envTalk"]
                if isinstance(row, dict)
            ),
        },
        "remoteCommonAudio": {
            "source": "RemoteCommonTable.remoteCommSingleDataList[*].audioId where autoPlay=true",
            "storedTriggerContextRows": len(grouped["remoteCommonAudio"]),
            "rowsWithPlayableMedia": sum(
                any(
                    isinstance(media_ref, dict) and media_ref.get("src")
                    for media_ref in row.get("mediaRefs") or []
                )
                for row in grouped["remoteCommonAudio"]
                if isinstance(row, dict)
            ),
            "voiceIdKeptSeparate": True,
        },
        "luaPostEvent": {
            "source": "decrypted VFS Lua AudioAdapter/AudioManager.PostEvent string literals",
            "storedTriggerContextRows": len(grouped["luaPostEvent"]),
            "runtimeExecutionObserved": 0,
        },
        "dialogTimeline": {
            "source": "conv/dlg_*.json line._debug.timelineTiming",
            "storedTriggerContextRows": len(grouped["dialogTimeline"]),
        },
        "dialogLifecycle": {
            "source": (
                "AudioDialogCustomEventTable dialogId + preloadEvents / "
                "preEnterEvents / postEnterEvents / preExitEvents / postExitEvents"
            ),
            "storedTriggerContextRows": len(grouped["dialogLifecycle"]),
            "rowsWithCurrentWwiseEvent": sum(
                bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
            "rowsWithNoDecodedMediaLeaf": sum(
                row.get("selection", {}).get("mediaSelectionStatus")
                == "wwiseEventHasNoDecodedMedia"
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
            "phaseCounts": dict(sorted(Counter(
                str((row.get("situation") or {}).get("lifecyclePhase") or "unknown")
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ).items())),
            "runtimeConsumer": DIALOG_LIFECYCLE_RUNTIME_CONSUMER,
        },
        "timelineAudio": {
            "source": (
                "event contexts kind levelSequenceAudio or cutsceneTimeline, including "
                "Persistent and StreamingAssets serialized Timeline carriers"
            ),
            "storedTriggerContextRows": len(grouped["timelineAudio"]),
            "rowsWithCurrentWwiseEvent": sum(
                bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "rowsWithAuthoredKeyMissingFromCurrentWwiseIndex": sum(
                not bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "rowsByRuntimeContract": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioPlayableRuntimeContractId") or "unknown")
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ).items())),
            "rowsByCarrierEvidence": dict(sorted(Counter(
                (
                    "serializedPlayableCarrier"
                    if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                    else (row.get("owner") or {}).get("runtimeCarrierStatus")
                    or "unresolved"
                )
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ).items())),
            "rowsByMusicActionType": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioMusicActionTypeLabel") or "unknown")
                for row in grouped["timelineAudio"]
                if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                == "timelineMusicEventKey.audioMusic"
            ).items())),
            "rowsByMusicSkipPolicy": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioMusicTriggerOnSkipLabel") or "unknown")
                for row in grouped["timelineAudio"]
                if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                == "timelineMusicEventKey.audioMusic"
            ).items())),
            "runtimeContracts": TIMELINE_AUDIO_RUNTIME_CONTRACTS,
        },
    }
    return {
        "schemaVersion": TRIGGER_CONTEXT_SCHEMA_VERSION,
        "language": language.upper(),
        "counts": {
            "total": len(contexts),
            "bySemanticKind": dict(sorted(counts.items())),
            "withPlayableMedia": sum(
                any(
                    isinstance(media_ref, dict) and media_ref.get("src")
                    for media_ref in row.get("mediaRefs") or []
                )
                for row in contexts
            ),
            "runtimeExecutionObserved": 0,
            "runtimeExecutionUnobserved": len(contexts),
            "timelineAudioRowsWithAuthoredKeyMissingFromCurrentWwiseIndex": sum(
                not bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "timelineAudioRowsWithStaticRuntimeContract": sum(
                bool((row.get("owner") or {}).get("audioPlayableRuntimeContractId"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "dialogLifecycleRowsWithNoDecodedMediaLeaf": sum(
                row.get("selection", {}).get("mediaSelectionStatus")
                == "wwiseEventHasNoDecodedMedia"
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
        },
        "coverage": coverage,
        "contexts": contexts,
        "evidenceBoundary": (
            "Each row joins an authored trigger/owner/selection surface to zero or more "
            "media references. Definition, media availability, and runtime execution "
            "are independent evidence states. The shard never claims that a LevelScript, "
            "NpcProxy, dialog lifecycle state transition, Timeline Director, Wwise branch, "
            "RemoteCommon auto-play row, or selected line/slot actually ran. "
            "AudioDialogCustomEventTable lifecycle rows identify a static request/scheduling "
            "hook; RemoteCommon voiceId remains separate from its audioId; neither proves "
            "PostEvent or an audible media leaf."
        ),
    }


def _first_recovered_mono_behaviour(export_root: Path, stem: str) -> Path | None:
    root = export_root / "recovered/AnimeStudio-cli"
    for source_root in ("Persistent", "StreamingAssets"):
        matches = sorted((root / source_root / "json_by_type/MonoBehaviour").glob(f"{stem}_p*.json"))
        if matches:
            return matches[0]
    return None


def collect_interactive_component_contexts(
    export_root: Path,
    *,
    decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Decode per-entity InteractiveAudioData state maps from MemoryPack.

    ``InteractiveData`` files are core-template definitions, while
    ``InteractiveTable`` maps those definitions to configured interactive
    identities.  The component body itself proves the request, but the file
    name is not by itself an entity owner.  When both table mirrors decode to
    the same exact mapping, add the template path and all configured consumer
    identities to each context.  A missing or ambiguous table mapping stays an
    explicit association gap rather than being guessed from the file stem.
    """

    if decoder is None:
        try:
            from build_data_index import parse_interactive_audio_component
        except ImportError:
            from scripts.build_data_index import parse_interactive_audio_component

        def decoder(_path: Path, data: bytes, _size: int) -> dict[str, Any]:
            components: list[dict[str, Any]] = []
            signature = bytes((0x5D, 0x02, 0, 0, 0, 0, 0x0D))
            cursor = 0
            while True:
                candidate = data.find(signature, cursor)
                if candidate < 0:
                    break
                cursor = candidate + 1
                try:
                    parsed, end = parse_interactive_audio_component(data, candidate + 2, 2)
                except (UnicodeDecodeError, struct.error, ValueError):
                    continue
                if end <= candidate + len(signature) or end > len(data):
                    continue
                components.append({
                    "index": len(components),
                    "sourceOffset": candidate,
                    **parsed,
                })
            return {"decoded": {"componentAudioComponents": components}}

    # InteractiveTable is an exact serialized ownership index.  Keep this
    # optional so focused callers/tests that only provide an InteractiveData
    # fixture retain their bounded component evidence without needing a table.
    template_ids_by_file_name: dict[str, list[str]] = defaultdict(list)
    template_paths_by_id: dict[str, str] = {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    table_source_paths: list[str] = []
    table_source_fingerprint = ""
    table: dict[str, Any] | None = None
    if table_decoder is None:
        try:
            from story_builder.interactive_binary import decode_interactive_table
        except ImportError:
            from scripts.story_builder.interactive_binary import decode_interactive_table
        table_decoder = decode_interactive_table
    table_versions: list[tuple[str, Path, bytes, str]] = []
    for source_root in ("Persistent", "StreamingAssets"):
        table_path = (
            export_root / "structured" / source_root
            / "Data/Json/Interactive/InteractiveTable.json"
        )
        if not table_path.is_file():
            continue
        try:
            table_data = table_path.read_bytes()
        except OSError:
            continue
        table_versions.append((
            source_root,
            table_path,
            table_data,
            hashlib.sha256(table_data).hexdigest(),
        ))
    if table_versions and len({row[3] for row in table_versions}) == 1:
        try:
            table = table_decoder(table_versions[0][2])
        except (UnicodeDecodeError, struct.error, ValueError):
            table = None
        if isinstance(table, dict):
            table_source_paths = [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _data, _digest in table_versions
            ]
            table_source_fingerprint = table_versions[0][3]
            for template_id, template_path in (table.get("coreTemplatePaths") or {}).items():
                normalized_template_path = normalize_posix(str(template_path or ""))
                pure_template_path = PurePosixPath(normalized_template_path)
                if (
                    pure_template_path.is_absolute()
                    or ".." in pure_template_path.parts
                    or not normalized_template_path.startswith(
                        "Data/Json/Interactive/InteractiveData/"
                    )
                ):
                    continue
                template_id = str(template_id)
                template_paths_by_id[template_id] = normalized_template_path
                file_name = pure_template_path.name
                if file_name:
                    template_ids_by_file_name[file_name].append(template_id)
            for consumer_id, template_id in (table.get("objectToTemplate") or {}).items():
                consumers_by_template[str(template_id)].append(str(consumer_id))
    paths_by_identity: dict[str, list[Path]] = defaultdict(list)
    for source_root in ("Persistent", "StreamingAssets"):
        root = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveData"
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            paths_by_identity[path.stem].append(path)

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for owner_id, paths in sorted(paths_by_identity.items()):
        paths_by_hash: dict[str, list[Path]] = defaultdict(list)
        data_by_hash: dict[str, bytes] = {}
        for path in paths:
            try:
                data = path.read_bytes()
            except OSError:
                continue
            digest = hashlib.sha256(data).hexdigest()
            paths_by_hash[digest].append(path)
            data_by_hash[digest] = data
        for digest, version_paths in sorted(paths_by_hash.items()):
            data = data_by_hash[digest]
            decoded = decoder(version_paths[0], data, len(data))
            body = decoded.get("decoded") if isinstance(decoded, dict) else None
            components = body.get("componentAudioComponents") if isinstance(body, dict) else None
            if not isinstance(components, list):
                continue
            source_paths = [normalize_posix(path.relative_to(export_root)) for path in version_paths]
            template_file_name = f"{owner_id}.json"
            template_ids = sorted(set(template_ids_by_file_name.get(template_file_name, [])))
            template_path = ""
            if len(template_ids) == 1:
                # The current table has one path per template id.  Keep the
                # path exact and do not collapse a future ambiguous match.
                template_path = template_paths_by_id.get(template_ids[0], "")
            consumer_ids = sorted({
                consumer
                for template_id in template_ids
                for consumer in consumers_by_template.get(template_id, [])
            })
            if len(template_ids) == 1:
                association_status = "exactInteractiveTableTemplatePath"
            elif len(template_ids) > 1:
                association_status = "ambiguousInteractiveTableTemplatePath"
            elif table_versions:
                association_status = "interactiveTableTemplatePathUnresolved"
            else:
                association_status = "interactiveTableIndexUnavailable"
            for component in components:
                if not isinstance(component, dict):
                    continue
                component_index = component.get("index")
                for state_index, row in enumerate(component.get("audioRows") or []):
                    if not isinstance(row, dict):
                        continue
                    for event_index, event_id in enumerate(row.get("events") or []):
                        event_name = str(event_id or "").strip()
                        if not event_name:
                            continue
                        _append_context(contexts, seen, event_name, {
                            "kind": "interactiveComponentTrigger",
                            "table": "InteractiveData",
                            "semanticRole": "entityInteractiveLifecycleEvent",
                            "ownerKind": "interactiveEntityConfig",
                            "ownerId": owner_id,
                            "interactiveTemplateIds": template_ids,
                            "interactiveTemplatePath": template_path,
                            "interactiveConsumerIds": consumer_ids,
                            "templateAssociationStatus": association_status,
                            "interactiveTableSourcePaths": table_source_paths,
                            "interactiveTableSha256": table_source_fingerprint,
                            "componentIndex": component_index,
                            "sourceOffset": component.get("sourceOffset"),
                            "triggerStateId": row.get("state"),
                            "triggerStateName": str(row.get("stateName") or ""),
                            "triggerRequestEvidence": ["decodedInteractiveAudioComponentStateMap"],
                            "triggerRuntimeActivationStatuses": ["runtimeInteractiveStateEntryRequired"],
                            "path": f"componentAudioComponents[{component_index}].audioRows[{state_index}].events[{event_index}]",
                            "sourcePaths": source_paths,
                            "sourceFingerprint": digest,
                            "evidence": "exactDecodedMemoryPackInteractiveAudioData",
                        })
                for custom_index, row in enumerate(component.get("customRows") or []):
                    if not isinstance(row, dict):
                        continue
                    event_name = str(row.get("event") or "").strip()
                    if not event_name:
                        continue
                    context = {
                        "kind": "interactiveComponentTrigger",
                        "table": "InteractiveData",
                        "semanticRole": "entityInteractiveCustomStateEvent",
                        "ownerKind": "interactiveEntityConfig",
                        "ownerId": owner_id,
                        "interactiveTemplateIds": template_ids,
                        "interactiveTemplatePath": template_path,
                        "interactiveConsumerIds": consumer_ids,
                        "templateAssociationStatus": association_status,
                        "interactiveTableSourcePaths": table_source_paths,
                        "interactiveTableSha256": table_source_fingerprint,
                        "componentIndex": component_index,
                        "sourceOffset": component.get("sourceOffset"),
                        "triggerCustomState": str(row.get("name") or ""),
                        "triggerRequestEvidence": ["decodedInteractiveAudioComponentCustomStateMap"],
                        "triggerRuntimeActivationStatuses": ["runtimeInteractiveCustomStateEntryRequired"],
                        "path": f"componentAudioComponents[{component_index}].customRows[{custom_index}].event",
                        "sourcePaths": source_paths,
                        "sourceFingerprint": digest,
                        "evidence": "exactDecodedMemoryPackInteractiveAudioData",
                    }
                    note = str(row.get("note") or "").strip()
                    if note:
                        context["description"] = note
                    _append_context(contexts, seen, event_name, context)
    return dict(contexts)


def collect_physics_audio_semantics(
    export_root: Path,
    *,
    component_decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact PhysicsAudio Event/RTPC contexts and consumer aliases.

    ``InteractiveTable`` is the ownership boundary: its core-template path
    identifies the one serialized definition, while ``interactiveDataDict``
    identifies every configured object id that consumes that definition.
    StreamingAssets/Persistent mirrors must agree byte-for-byte before either
    table or template data is accepted.
    """
    if component_decoder is None or table_decoder is None:
        try:
            from story_builder.interactive_binary import (
                decode_interactive_table,
                find_physics_audio_components,
            )
        except ImportError:
            from scripts.story_builder.interactive_binary import (
                decode_interactive_table,
                find_physics_audio_components,
            )
        component_decoder = component_decoder or find_physics_audio_components
        table_decoder = table_decoder or decode_interactive_table

    source_roots = ("StreamingAssets", "Persistent")
    table_paths = [
        export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
        for source_root in source_roots
    ]
    table_versions: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    table_data: dict[str, bytes] = {}
    failures: list[dict[str, Any]] = []
    for source_root, path in zip(source_roots, table_paths):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
            continue
        digest = hashlib.sha256(data).hexdigest()
        table_versions[digest].append((source_root, path))
        table_data[digest] = data

    empty_stats = {
        "status": "unavailable" if not table_versions else "failed",
        "interactiveTablePhysicalFiles": sum(len(rows) for rows in table_versions.values()),
        "interactiveTableContentVersions": len(table_versions),
        "templateDefinitionsScanned": 0,
        "templatePhysicalFiles": 0,
        "physicsAudioDefinitions": 0,
        "physicsAudioComponents": 0,
        "physicsAudioEventContexts": 0,
        "distinctPhysicsAudioEvents": 0,
        "physicsAudioRtpcControls": 0,
        "physicsAudioConsumerIdentities": 0,
        "physicsAudioAliasIdentities": 0,
        "failureSamples": failures[:16],
    }
    boundary = (
        "The exact tag-0x00BE/member-1, 21-key PhysicsAudio dynamic-property map and "
        "InteractiveTable ownership/alias rows prove authored movement, impact, rotation, "
        "and RTPC configuration. They do not prove component instantiation, physics state "
        "changes, RTPC updates, Event posting, or a selected Wwise playback branch."
    )
    if not table_versions:
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }
    if len(table_versions) != 1:
        empty_stats["status"] = "conflictingMirrors"
        empty_stats["failureSamples"] = [{
            "source": "InteractiveTable.json",
            "error": "StreamingAssets/Persistent content hashes differ",
            "sha256": sorted(table_versions),
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }

    table_sha256 = next(iter(table_versions))
    table_sources = table_versions[table_sha256]
    table_source_paths = [
        normalize_posix(path.relative_to(export_root)) for _root, path in table_sources
    ]
    try:
        table = table_decoder(table_data[table_sha256])
    except (UnicodeDecodeError, struct.error, ValueError) as exc:
        empty_stats["failureSamples"] = [{
            "source": table_source_paths[0], "error": str(exc), "sha256": table_sha256,
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }
    if not isinstance(table, dict):
        empty_stats["failureSamples"] = [{
            "source": table_source_paths[0], "error": "InteractiveTable decoder returned no object",
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }

    core_paths = table.get("coreTemplatePaths") or {}
    object_to_template = table.get("objectToTemplate") or {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    for consumer_id, template_id in object_to_template.items():
        consumers_by_template[str(template_id)].append(str(consumer_id))

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    rtpc_parameters: list[dict[str, Any]] = []
    definitions: list[dict[str, Any]] = []
    template_physical_files = 0
    template_definitions_scanned = 0
    component_count = 0
    consumer_ids: set[str] = set()
    alias_ids: set[str] = set()
    accepted_template_versions = 0

    for template_id, raw_template_path in sorted(core_paths.items()):
        template_path = normalize_posix(str(raw_template_path or ""))
        pure_path = PurePosixPath(template_path)
        if (
            pure_path.is_absolute()
            or ".." in pure_path.parts
            or not template_path.startswith("Data/Json/Interactive/InteractiveData/")
        ):
            continue
        existing: list[tuple[str, Path, bytes, str]] = []
        for source_root in source_roots:
            path = export_root / "structured" / source_root / Path(*pure_path.parts)
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                if len(failures) < 16:
                    failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
                continue
            existing.append((source_root, path, data, hashlib.sha256(data).hexdigest()))
        if not existing:
            continue
        template_definitions_scanned += 1
        template_physical_files += len(existing)
        version_hashes = {digest for _root, _path, _data, digest in existing}
        if len(version_hashes) != 1:
            relevant_components = False
            relevant_decode_error = ""
            for _source_root, _path, version_data, _digest in existing:
                try:
                    relevant_components = bool(component_decoder(version_data)) or relevant_components
                except (UnicodeDecodeError, struct.error, ValueError) as exc:
                    relevant_decode_error = str(exc)
            # Overlay differences in unrelated Interactive definitions do not
            # weaken this bounded PhysicsAudio audit.  A differing definition
            # is a blocker only when at least one version contains the exact
            # PhysicsAudio anchor or fails after reaching that anchor.
            if (relevant_components or relevant_decode_error) and len(failures) < 16:
                failures.append({
                    "source": template_path,
                    "error": (
                        "StreamingAssets/Persistent PhysicsAudio template content hashes differ"
                        + (f": {relevant_decode_error}" if relevant_decode_error else "")
                    ),
                    "sha256": sorted(version_hashes),
                })
            continue
        template_sha256 = existing[0][3]
        source_paths = [
            normalize_posix(path.relative_to(export_root)) for _root, path, _data, _digest in existing
        ]
        try:
            components = component_decoder(existing[0][2])
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            if len(failures) < 16:
                failures.append({
                    "source": source_paths[0], "error": str(exc), "sha256": template_sha256,
                })
            continue
        if not isinstance(components, list) or not components:
            continue
        accepted_template_versions += 1
        configured_consumers = sorted(set(consumers_by_template.get(str(template_id), [])))
        consumer_ids.update(configured_consumers)
        alias_ids.update(value for value in configured_consumers if value != str(template_id))
        for component_occurrence_index, component in enumerate(components):
            if not isinstance(component, dict):
                continue
            component_count += 1
            properties = [row for row in component.get("properties") or [] if isinstance(row, dict)]
            definition = {
                "kind": "physicsAudioDefinition",
                "definitionOwnerId": str(template_id),
                "templatePath": template_path,
                "consumerIds": configured_consumers,
                "consumerAliasIds": [value for value in configured_consumers if value != str(template_id)],
                "componentOccurrenceIndex": component_occurrence_index,
                "componentTag": component.get("unionTag"),
                "componentTagHex": str(component.get("unionTagHex") or ""),
                "serializedMemberCount": component.get("memberCount"),
                "propertyCount": component.get("propertyCount"),
                "sourceOffset": component.get("sourceOffset"),
                "propertyMapOffset": component.get("propertyMapOffset"),
                "endOffset": component.get("endOffset"),
                "sourcePaths": source_paths,
                "sourceRoots": [root for root, _path, _data, _digest in existing],
                "sourceSha256": template_sha256,
                "interactiveTableSourcePaths": table_source_paths,
                "interactiveTableSha256": table_sha256,
                "schemaMappingId": str(component.get("schemaMappingId") or ""),
                "runtimeMappingId": str(component.get("runtimeMappingId") or ""),
                "schemaStatus": str(component.get("schemaStatus") or ""),
                "properties": properties,
            }
            definitions.append(definition)
            common = {
                "ownerId": str(template_id),
                "definitionOwnerId": str(template_id),
                "ownerKind": "interactivePhysicsAudioDefinition",
                "consumerIds": configured_consumers,
                "consumerAliasIds": definition["consumerAliasIds"],
                "confidence": "direct",
                "table": "InteractiveTable",
                "templatePath": template_path,
                "componentOccurrenceIndex": component_occurrence_index,
                "componentTag": component.get("unionTag"),
                "componentTagHex": str(component.get("unionTagHex") or ""),
                "serializedMemberCount": component.get("memberCount"),
                "propertyCount": component.get("propertyCount"),
                "sourceOffset": component.get("sourceOffset"),
                "componentEndOffset": component.get("endOffset"),
                "sourcePaths": source_paths,
                "sourceRoots": definition["sourceRoots"],
                "sourceFingerprint": template_sha256,
                "sourceSha256": template_sha256,
                "interactiveTableSourcePaths": table_source_paths,
                "interactiveTableSha256": table_sha256,
                "schemaMappingId": definition["schemaMappingId"],
                "runtimeMappingId": definition["runtimeMappingId"],
                "schemaStatus": definition["schemaStatus"],
                "runtimeActivationStatus": "physicsAudioRuntimeExecutionNotObserved",
            }
            for row in properties:
                value = row.get("value")
                event_role = str(row.get("eventRole") or "")
                rtpc_role = str(row.get("rtpcRole") or "")
                row_common = {
                    **common,
                    "authoredProperty": str(row.get("authoredKey") or ""),
                    "runtimeField": str(row.get("runtimeField") or ""),
                    "propertySourceOffset": row.get("propertySourceOffset", row.get("sourceOffset")),
                    "propertyValueSourceOffset": row.get("valueSourceOffset"),
                    "valueType": row.get("valueType"),
                    "valueTypeName": str(row.get("valueTypeName") or ""),
                    "semanticPath": (
                        "PhysicsAudioComponentData.propertyList["
                        + str(row.get("authoredKey") or "")
                        + "]"
                    ),
                }
                if event_role and isinstance(value, str) and value.strip():
                    event_name = value.strip()
                    _append_context(contexts, seen, event_name, {
                        **row_common,
                        "kind": "physicsAudioComponentEvent",
                        "semanticRole": "authoredInteractivePhysicsAudioEvent",
                        "eventName": event_name,
                        "triggerRole": event_role,
                        "triggerRequestEvidence": [
                            "exactPhysicsAudioComponentDynamicProperty",
                            "exactInteractiveTableTemplateOwnership",
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "physicsAudioComponentInstantiationAndThresholdStateRequired"
                        ],
                    })
                if rtpc_role and isinstance(value, str) and value.strip():
                    rtpc_parameters.append({
                        **row_common,
                        "kind": "physicsAudioRtpcParameter",
                        "parameterName": value.strip(),
                        "controlRole": rtpc_role,
                        "semanticRole": "authoredInteractivePhysicsAudioRtpc",
                        "wwiseEventStatus": "notApplicable",
                        "evidence": "exactPhysicsAudioComponentDynamicProperty",
                    })

    event_context_count = sum(len(rows) for rows in contexts.values())
    stats = {
        "status": "complete" if not failures else "partial",
        "interactiveTablePhysicalFiles": sum(len(rows) for rows in table_versions.values()),
        "interactiveTableContentVersions": len(table_versions),
        "interactiveTableSourcePaths": table_source_paths,
        "interactiveTableSha256": table_sha256,
        "coreTemplateCount": int(table.get("coreTemplateCount") or len(core_paths)),
        "interactiveDataCount": int(table.get("interactiveDataCount") or len(object_to_template)),
        "templateDefinitionsScanned": template_definitions_scanned,
        "templatePhysicalFiles": template_physical_files,
        "physicsAudioTemplateVersions": accepted_template_versions,
        "physicsAudioDefinitions": len(definitions),
        "physicsAudioComponents": component_count,
        "physicsAudioEventContexts": event_context_count,
        "distinctPhysicsAudioEvents": len(contexts),
        "physicsAudioRtpcControls": len(rtpc_parameters),
        "physicsAudioConsumerIdentities": len(consumer_ids),
        "physicsAudioAliasIdentities": len(alias_ids),
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    return {
        "eventContexts": dict(contexts),
        "rtpcParameters": rtpc_parameters,
        "definitions": definitions,
        "stats": stats,
        "evidenceBoundary": boundary,
    }


def collect_model_view_state_audio_semantics(
    export_root: Path,
    *,
    controller_decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact ModelView state Event, position, RTPC, and spatial rows.

    The controller decoder must consume the complete MemoryPack object before
    any audio member is accepted. InteractiveData joins are exact serialized
    controller-id references, but their property slot is not yet decoded; they
    therefore remain authored template associations rather than runtime owners.
    """
    if controller_decoder is None or table_decoder is None:
        try:
            from story_builder.interactive_binary import (
                decode_interactive_table,
                decode_model_view_state_controller,
            )
        except ImportError:
            from scripts.story_builder.interactive_binary import (
                decode_interactive_table,
                decode_model_view_state_controller,
            )
        controller_decoder = controller_decoder or decode_model_view_state_controller
        table_decoder = table_decoder or decode_interactive_table

    source_roots = ("StreamingAssets", "Persistent")
    controller_rel = PurePosixPath(
        "Data/Json/Interactive/ModelViewStateControllerData"
    )
    failures: list[dict[str, Any]] = []
    physical_files = 0
    files_by_name: dict[str, list[tuple[str, Path, bytes, str]]] = defaultdict(list)
    for source_root in source_roots:
        directory = export_root / "structured" / source_root / Path(*controller_rel.parts)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                data = path.read_bytes()
            except OSError as exc:
                failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
                continue
            physical_files += 1
            files_by_name[path.name].append(
                (source_root, path, data, hashlib.sha256(data).hexdigest())
            )

    boundary = (
        "Exact complete ModelViewStateControllerData decoding proves authored state-bound "
        "Event/position requests and RTPC/spatial controls, including behavior time and the "
        "model/layer/state/behavior owner chain. InteractiveData matches prove only an exact "
        "serialized controller-id association because the containing property slot is unresolved. "
        "State entry, behavior execution, Event posting, RTPC/spatial application, and Wwise "
        "branch playback were not observed. CustomAudioId strings remain unresolved controls, "
        "not Wwise Events."
    )
    empty = {
        "status": "unavailable" if not files_by_name else "failed",
        "controllerPhysicalFiles": physical_files,
        "controllerLogicalFiles": len(files_by_name),
        "controllersDecoded": 0,
        "controllersWithAudio": 0,
        "audioBehaviorCount": 0,
        "eventBehaviorCount": 0,
        "positionEventBehaviorCount": 0,
        "rtpcBehaviorCount": 0,
        "spatialBehaviorCount": 0,
        "customAudioControlCount": 0,
        "controllersWithTemplateAssociations": 0,
        "templateAssociationCount": 0,
        "interactiveConsumerIdentityCount": 0,
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    if not files_by_name:
        return {
            "eventContexts": {}, "rtpcParameters": [], "spatialControls": [],
            "customAudioControls": [], "stats": empty, "evidenceBoundary": boundary,
        }

    decoded_controllers: list[dict[str, Any]] = []
    for file_name, versions in sorted(files_by_name.items()):
        decoded_versions: list[tuple[str, Path, str, dict[str, Any]]] = []
        for source_root, path, data, digest in versions:
            try:
                decoded = controller_decoder(data)
            except (UnicodeDecodeError, struct.error, ValueError) as exc:
                if len(failures) < 16:
                    failures.append({
                        "source": normalize_posix(path.relative_to(export_root)),
                        "error": str(exc),
                        "sha256": digest,
                    })
                continue
            if not isinstance(decoded, dict):
                if len(failures) < 16:
                    failures.append({
                        "source": normalize_posix(path.relative_to(export_root)),
                        "error": "ModelView decoder returned no object",
                    })
                continue
            decoded_versions.append((source_root, path, digest, decoded))
        if len(decoded_versions) != len(versions):
            continue

        def audio_projection(decoded: dict[str, Any]) -> str:
            rows = []
            for raw in decoded.get("audioBehaviors") or []:
                if not isinstance(raw, dict):
                    continue
                rows.append({
                    key: value for key, value in raw.items()
                    if key not in {"sourceOffset", "endOffset", "byteLength"}
                })
            return json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

        projections = {audio_projection(row[3]) for row in decoded_versions}
        if len(projections) != 1:
            if len(failures) < 16:
                failures.append({
                    "source": normalize_posix(controller_rel / file_name),
                    "error": "StreamingAssets/Persistent decoded audio projections differ",
                    "sha256": sorted(row[2] for row in decoded_versions),
                })
            continue
        preferred = next(
            (row for row in decoded_versions if row[0] == "Persistent"),
            decoded_versions[0],
        )
        decoded = preferred[3]
        decoded_controllers.append({
            "fileName": file_name,
            "controllerId": str(decoded.get("modelId") or Path(file_name).stem),
            "decoded": decoded,
            "sourcePaths": [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _digest, _decoded in decoded_versions
            ],
            "sourceRoots": [row[0] for row in decoded_versions],
            "sourceFingerprints": sorted(set(row[2] for row in decoded_versions)),
        })

    # Recover the bounded external association without pretending the still
    # unresolved InteractiveData property slot is a runtime activation edge.
    references_by_controller: dict[str, set[str]] = defaultdict(set)
    template_paths_by_id: dict[str, str] = {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    table_source_paths: list[str] = []
    table_sha256 = ""
    table_versions: list[tuple[str, Path, bytes, str]] = []
    for source_root in source_roots:
        table_path = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
        if not table_path.is_file():
            continue
        try:
            data = table_path.read_bytes()
        except OSError as exc:
            if len(failures) < 16:
                failures.append({"source": normalize_posix(table_path.relative_to(export_root)), "error": str(exc)})
            continue
        table_versions.append((source_root, table_path, data, hashlib.sha256(data).hexdigest()))
    if table_versions and len({row[3] for row in table_versions}) == 1:
        try:
            table = table_decoder(table_versions[0][2])
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            table = None
            if len(failures) < 16:
                failures.append({
                    "source": normalize_posix(table_versions[0][1].relative_to(export_root)),
                    "error": str(exc),
                })
        if isinstance(table, dict):
            table_source_paths = [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _data, _digest in table_versions
            ]
            table_sha256 = table_versions[0][3]
            template_paths_by_id = {
                str(key): normalize_posix(str(value or ""))
                for key, value in (table.get("coreTemplatePaths") or {}).items()
            }
            for consumer_id, template_id in (table.get("objectToTemplate") or {}).items():
                consumers_by_template[str(template_id)].append(str(consumer_id))
            anchors = {
                row["controllerId"]: struct.pack("<I", len(row["controllerId"].encode("utf-8")))
                + row["controllerId"].encode("utf-8")
                for row in decoded_controllers
                if row.get("controllerId")
            }
            for template_id, template_path in sorted(template_paths_by_id.items()):
                pure_path = PurePosixPath(template_path)
                if (
                    pure_path.is_absolute()
                    or ".." in pure_path.parts
                    or not template_path.startswith("Data/Json/Interactive/InteractiveData/")
                ):
                    continue
                candidates: list[bytes] = []
                for source_root in reversed(source_roots):
                    path = export_root / "structured" / source_root / Path(*pure_path.parts)
                    if path.is_file():
                        try:
                            candidates.append(path.read_bytes())
                        except OSError:
                            pass
                if not candidates:
                    continue
                # Associations must agree semantically across available mirrors.
                matches = [
                    {controller_id for controller_id, anchor in anchors.items() if data.find(anchor) >= 0}
                    for data in candidates
                ]
                if len({tuple(sorted(row)) for row in matches}) != 1:
                    if len(failures) < 16:
                        failures.append({
                            "source": template_path,
                            "error": "StreamingAssets/Persistent controller-id reference sets differ",
                        })
                    continue
                for controller_id in matches[0]:
                    references_by_controller[controller_id].add(template_id)
    elif table_versions:
        if len(failures) < 16:
            failures.append({
                "source": "Data/Json/Interactive/InteractiveTable.json",
                "error": "StreamingAssets/Persistent content hashes differ",
                "sha256": sorted(row[3] for row in table_versions),
            })

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    rtpc_parameters: list[dict[str, Any]] = []
    spatial_controls: list[dict[str, Any]] = []
    custom_controls: list[dict[str, Any]] = []
    tag_counts: Counter[int] = Counter()
    controllers_with_audio = 0
    associated_controllers: set[str] = set()
    associated_templates: set[str] = set()
    associated_consumers: set[str] = set()
    for controller in decoded_controllers:
        decoded = controller["decoded"]
        audio_rows = [row for row in decoded.get("audioBehaviors") or [] if isinstance(row, dict)]
        if audio_rows:
            controllers_with_audio += 1
        controller_id = str(controller.get("controllerId") or "")
        template_ids = sorted(references_by_controller.get(controller_id, set()))
        consumer_ids = sorted({
            consumer
            for template_id in template_ids
            for consumer in consumers_by_template.get(template_id, [])
        })
        if audio_rows and template_ids:
            associated_controllers.add(controller_id)
            associated_templates.update(template_ids)
            associated_consumers.update(consumer_ids)
        common = {
            "ownerId": controller_id,
            "controllerId": controller_id,
            "ownerKind": "modelViewStateController",
            "sourceFile": str(controller.get("fileName") or ""),
            "sourcePaths": controller.get("sourcePaths") or [],
            "sourceRoots": controller.get("sourceRoots") or [],
            "sourceFingerprints": controller.get("sourceFingerprints") or [],
            "schemaMappingId": str(decoded.get("schemaMappingId") or ""),
            "runtimeMappingId": str(decoded.get("runtimeMappingId") or ""),
            "schemaStatus": str(decoded.get("schemaStatus") or ""),
            "interactiveTemplateIds": template_ids,
            "interactiveTemplatePaths": [template_paths_by_id.get(value, "") for value in template_ids],
            "interactiveConsumerIds": consumer_ids,
            "interactiveTableSourcePaths": table_source_paths,
            "interactiveTableSha256": table_sha256,
            "templateAssociationStatus": (
                "exactSerializedControllerIdReferencePropertyUnresolved"
                if template_ids else "unlinked"
            ),
            "runtimeActivationStatus": "modelViewStateBehaviorExecutionNotObserved",
        }
        for row in audio_rows:
            tag = int(row.get("unionTag") or 0)
            tag_counts[tag] += 1
            row_common = {
                **common,
                "modelAnimatorIndex": row.get("modelAnimatorIndex"),
                "modelAnimatorName": str(row.get("modelAnimatorName") or ""),
                "layerIndex": row.get("layerIndex"),
                "layerFsmIndex": row.get("layerFsmIndex"),
                "layerName": str(row.get("layerName") or ""),
                "stateIndex": row.get("stateIndex"),
                "stateName": str(row.get("stateName") or ""),
                "stateType": row.get("stateType"),
                "behaviorIndex": row.get("behaviorIndex"),
                "behaviorTag": tag,
                "behaviorTagHex": str(row.get("unionTagHex") or f"0x{tag:04x}"),
                "serializedMemberCount": row.get("memberCount"),
                "behaviorType": row.get("behaviorType"),
                "behaviorKind": str(row.get("behaviorKind") or ""),
                "behaviorTime": row.get("time"),
                "timeFlowSwitch": row.get("timeFlowSwitch"),
                "canLoopActive": row.get("canLoopActive"),
                "needForceExecute": row.get("needForceExecute"),
                "normalizedTimeFlowBasedActive": row.get("normalizedTimeFlowBasedActive"),
                "sourceOffset": row.get("sourceOffset"),
                "behaviorEndOffset": row.get("endOffset"),
                "semanticPath": (
                    f"modelAnimatorDatas[{row.get('modelAnimatorIndex')}].layerFsmDatas"
                    f"[{row.get('layerIndex')}].stateDatas[{row.get('stateIndex')}]"
                    f".behaviors[{row.get('behaviorIndex')}]"
                ),
            }
            if tag in (1, 2):
                event_fields = {
                    **row_common,
                    "audioNodeName": str(row.get("audioNodeName") or ""),
                    "customAudioId": str(row.get("customAudioId") or ""),
                    "eAudioTriggerState": row.get("eAudioTriggerState"),
                    "isCustom": bool(row.get("isCustom")),
                    "isDirectlyPlay": bool(row.get("isDirectlyPlay")),
                    "normalAudioId": row.get("normalAudioId"),
                    "stopOnEnd": bool(row.get("stopOnEnd")),
                    "transitionTime": row.get("transitionTime"),
                }
                if row.get("isCustom"):
                    custom_controls.append({
                        **event_fields,
                        "kind": "modelViewStateCustomAudioControl",
                        "controlValue": str(row.get("customAudioId") or ""),
                        "semanticRole": "unresolvedModelViewCustomAudioId",
                        "wwiseEventStatus": "notPromotedToEvent",
                        "evidence": "exactDecodedModelViewStateCustomAudioBranch",
                    })
                    continue
                signed_id = row.get("normalAudioId")
                if not isinstance(signed_id, int) or isinstance(signed_id, bool) or signed_id == 0:
                    continue
                event_hash = signed_id & 0xFFFFFFFF
                _append_context(contexts, seen, event_hash_context_key(event_hash), {
                    **event_fields,
                    "kind": (
                        "modelViewStateAudioEvent" if tag == 1
                        else "modelViewStatePositionAudioEvent"
                    ),
                    "semanticRole": (
                        "authoredModelViewStateEventRequest" if tag == 1
                        else "authoredModelViewStatePositionedEventRequest"
                    ),
                    "signedValue": signed_id,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "confidence": "direct",
                    "evidence": "exactDecodedModelViewStateAudioBehavior",
                    "triggerRequestEvidence": [
                        "exactModelViewStateBehaviorUnion",
                        "exactModelLayerStateBehaviorOwnerChain",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "modelViewStateEntryAndBehaviorTimeRequired",
                        "modelViewStateBehaviorExecutionNotObserved",
                    ],
                })
            elif tag == 3:
                rtpc_parameters.append({
                    **row_common,
                    "kind": "modelViewStateRtpcParameter",
                    "parameterName": str(row.get("audioRTPCValue") or ""),
                    "audioNodeName": str(row.get("audioNodeName") or ""),
                    "setValue": row.get("audioRTPCSetValue"),
                    "rtpcBehaviourType": row.get("rtpcBehaviourType"),
                    "continuousTick": row.get("continuousTick"),
                    "dependBlackBoard": row.get("dependBlackBoard"),
                    "dependFloatKey": str(row.get("dependFloatKey") or ""),
                    "semanticRole": "authoredModelViewStateRtpcControl",
                    "wwiseEventStatus": "notApplicable",
                    "evidence": "exactDecodedModelViewStateRtpcBehavior",
                })
            elif tag == 4:
                spatial_controls.append({
                    **row_common,
                    "kind": "modelViewStateSpatialAudioControl",
                    "continuous": row.get("continuous"),
                    "dependBlackBoard": row.get("dependBlackBoard"),
                    "dependFloatKey": str(row.get("dependFloatKey") or ""),
                    "directSet": row.get("directSet"),
                    "targetClosePercentage": row.get("targetClosePercentage"),
                    "totalTime": row.get("totalTime"),
                    "semanticRole": "authoredModelViewStateSpatialControl",
                    "wwiseEventStatus": "notApplicable",
                    "evidence": "exactDecodedModelViewStateSpatialAudioBehavior",
                })

    event_context_count = sum(len(rows) for rows in contexts.values())
    stats = {
        "status": "complete" if not failures else "partial",
        "controllerPhysicalFiles": physical_files,
        "controllerLogicalFiles": len(files_by_name),
        "controllersDecoded": len(decoded_controllers),
        "controllersWithAudio": controllers_with_audio,
        "audioBehaviorCount": sum(tag_counts.values()),
        "eventBehaviorCount": tag_counts.get(1, 0),
        "positionEventBehaviorCount": tag_counts.get(2, 0),
        "rtpcBehaviorCount": tag_counts.get(3, 0),
        "spatialBehaviorCount": tag_counts.get(4, 0),
        "normalEventContextCount": event_context_count,
        "distinctNormalEventHashes": len(contexts),
        "customAudioControlCount": len(custom_controls),
        "controllersWithTemplateAssociations": len(associated_controllers),
        "templateAssociationCount": len(associated_templates),
        "interactiveConsumerIdentityCount": len(associated_consumers),
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    return {
        "eventContexts": dict(contexts),
        "rtpcParameters": rtpc_parameters,
        "spatialControls": spatial_controls,
        "customAudioControls": custom_controls,
        "stats": stats,
        "evidenceBoundary": boundary,
    }


def collect_authored_runtime_config_contexts(
    export_root: Path,
    runtime_model: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Recover exact interactive-state and global lifecycle Event requests."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for event_id, rows in collect_interactive_component_contexts(export_root).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    trigger_state_names: dict[int, str] = {}
    for system in (runtime_model or {}).get("systems") or []:
        if not isinstance(system, dict) or not str(system.get("type") or "").endswith("+EAudioTriggerState"):
            continue
        trigger_state_names = {
            int(value): str(name)
            for name, value in (system.get("enumValues") or {}).items()
            if isinstance(value, int)
        }
        break

    interactive_path = _first_recovered_mono_behaviour(export_root, "InteractiveAudioSetting")
    interactive = load_json(interactive_path, {}) if interactive_path else {}
    if isinstance(interactive, dict) and interactive_path is not None:
        source = normalize_posix(interactive_path.relative_to(export_root))
        for row_index, row in enumerate(interactive.get("subTemplateList") or []):
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("modelId") or "")
            sub_template_id = str(row.get("subTemplateId") or "")
            for state_index, state_row in enumerate(row.get("audioList") or []):
                if not isinstance(state_row, dict):
                    continue
                try:
                    trigger_state_id = int(state_row.get("state"))
                except (TypeError, ValueError):
                    continue
                for event_index, event_id in enumerate(state_row.get("audio") or []):
                    event_name = str(event_id or "").strip()
                    if not event_name:
                        continue
                    context = {
                        "kind": "interactiveAudioTrigger",
                        "table": "InteractiveAudioSetting",
                        "semanticRole": "interactiveLifecycleEvent",
                        "modelId": model_id,
                        "subTemplateId": sub_template_id,
                        "triggerStateId": trigger_state_id,
                        "triggerRequestEvidence": ["serializedInteractiveAudioStateMap"],
                        "triggerRuntimeActivationStatuses": ["runtimeInteractiveStateEntryRequired"],
                        "path": f"subTemplateList[{row_index}].audioList[{state_index}].audio[{event_index}]",
                        "source": source,
                        "evidence": "exactSerializedInteractiveAudioSetting",
                    }
                    if trigger_state_id in trigger_state_names:
                        context["triggerStateName"] = trigger_state_names[trigger_state_id]
                    _append_context(contexts, seen, event_name, context)
            for custom_index, custom_row in enumerate(row.get("customAudioList") or []):
                if not isinstance(custom_row, dict):
                    continue
                event_name = str(custom_row.get("audioEvent") or "").strip()
                if not event_name:
                    continue
                context = {
                    "kind": "interactiveAudioTrigger",
                    "table": "InteractiveAudioSetting",
                    "semanticRole": "interactiveCustomStateEvent",
                    "modelId": model_id,
                    "subTemplateId": sub_template_id,
                    "triggerCustomState": str(custom_row.get("audioState") or ""),
                    "triggerRequestEvidence": ["serializedInteractiveAudioCustomStateMap"],
                    "triggerRuntimeActivationStatuses": ["runtimeInteractiveCustomStateEntryRequired"],
                    "path": f"subTemplateList[{row_index}].customAudioList[{custom_index}].audioEvent",
                    "source": source,
                    "evidence": "exactSerializedInteractiveAudioSetting",
                }
                description = str(custom_row.get("desc") or "").strip()
                if description:
                    context["description"] = description
                _append_context(contexts, seen, event_name, context)

    global_path = _first_recovered_mono_behaviour(export_root, "AudioGlobalConfig")
    global_config = load_json(global_path, {}) if global_path else {}
    if isinstance(global_config, dict) and global_path is not None:
        source = normalize_posix(global_path.relative_to(export_root))

        def append_named(value: Any, path: str, semantic_role: str) -> None:
            event_name = str(value or "").strip()
            if not event_name:
                return
            _append_context(contexts, seen, event_name, {
                "kind": "audioGlobalConfigEvent",
                "table": "AudioGlobalConfig",
                "semanticRole": semantic_role,
                "path": path,
                "source": source,
                "evidence": "exactSerializedAudioGlobalConfig",
                "triggerRequestEvidence": ["serializedGlobalAudioPolicy"],
                "triggerRuntimeActivationStatuses": ["runtimeLifecycleConditionRequired"],
            })

        def append_hash(value: Any, path: str, semantic_role: str, **extra: Any) -> None:
            raw = value.get("_id") if isinstance(value, dict) else value
            if not isinstance(raw, int) or isinstance(raw, bool) or raw == 0:
                return
            event_hash = raw & 0xFFFFFFFF
            context = {
                "kind": "audioGlobalConfigEventHash",
                "table": "AudioGlobalConfig",
                "semanticRole": semantic_role,
                "path": path,
                "source": source,
                "signedValue": raw,
                "eventHash": event_hash,
                "evidence": "exactSerializedAudioId",
                "triggerRequestEvidence": ["serializedGlobalAudioPolicy"],
                "triggerRuntimeActivationStatuses": ["runtimeLifecycleConditionRequired"],
            }
            context.update({key: value for key, value in extra.items() if value not in (None, "", [])})
            _append_context(contexts, seen, event_hash_context_key(event_hash), context)

        for field, role in (
            ("loginMusicStartEvent", "loginMusicStartEvent"),
            ("metaMusicStartEvent", "metaMusicStartEvent"),
            ("gameplayMusicStartEvent", "gameplayMusicStartEvent"),
            ("rushWindEventName", "rushWindStartEvent"),
            ("rushWindStopEventName", "rushWindStopEvent"),
        ):
            append_named(global_config.get(field), field, role)
        for field, role in (
            ("initEvents", "audioEngineInitEvent"),
            ("preloadEvents", "audioPreloadEvent"),
            ("onLoginEvents", "loginLifecycleEvent"),
        ):
            for index, value in enumerate(global_config.get(field) or []):
                append_named(value, f"{field}[{index}]", role)
        for field, role in (
            ("globalEventLocal", "globalLocalEvent"),
            ("globalEventRemote", "globalRemoteEvent"),
            ("globalEventLeaveMainGame", "leaveMainGameEvent"),
            ("musicEventCutsceneForceEmpty", "cutsceneForceEmptyMusicEvent"),
            ("specialGameplayGenderSelectIn", "genderSelectEnterEvent"),
            ("specialGameplayGenderSelectOut", "genderSelectExitEvent"),
        ):
            append_hash(global_config.get(field), field, role)
        for field, role in (
            ("persistantPreparedEvents", "persistentPreparedEvent"),
            ("musicCommonEventList", "commonMusicEvent"),
        ):
            for index, value in enumerate(global_config.get(field) or []):
                append_hash(value, f"{field}[{index}]", role)
        for field, owner_kind in (
            ("charInitEvent", "character"),
            ("npcInitEvent", "npc"),
            ("enemyInitEvent", "enemy"),
        ):
            mapping = global_config.get(field) or {}
            keys = mapping.get("_keyData") or [] if isinstance(mapping, dict) else []
            values = mapping.get("_valueData") or [] if isinstance(mapping, dict) else []
            for index, (owner_id, value) in enumerate(zip(keys, values)):
                append_hash(
                    value,
                    f"{field}._valueData[{index}]",
                    "entityInitEvent",
                    ownerKind=owner_kind,
                    ownerId=str(owner_id or ""),
                )
        for field, direction in (("audioStatesIn", "enter"), ("audioStatesOut", "exit")):
            mapping = global_config.get(field) or {}
            masks = mapping.get("_keyData") or [] if isinstance(mapping, dict) else []
            values = mapping.get("_valueData") or [] if isinstance(mapping, dict) else []
            for state_index, (state_mask, value) in enumerate(zip(masks, values)):
                ids = value.get("_ids") or [] if isinstance(value, dict) else []
                for event_index, event_id in enumerate(ids):
                    append_hash(
                        event_id,
                        f"{field}._valueData[{state_index}]._ids[{event_index}]",
                        "audioStateTransitionEvent",
                        stateDirection=direction,
                        audioStateMask=state_mask,
                    )
    return dict(contexts)


def _iter_audio_cue_expression_nodes(value: Any, path: str) -> Iterable[tuple[dict[str, Any], str]]:
    if not isinstance(value, dict):
        return
    yield value, path
    for index, child in enumerate(value.get("children") or []):
        if isinstance(child, dict):
            yield from _iter_audio_cue_expression_nodes(child, f"{path}.children[{index}]")


def collect_audio_cue_semantics(export_root: Path) -> dict[str, Any]:
    """Split AudioCue Event requests from runtime expression operands."""

    table_path = next((
        export_root / "structured" / source_root / "Table" / "AudioCueTable.json"
        for source_root in ("Persistent", "StreamingAssets")
        if (export_root / "structured" / source_root / "Table" / "AudioCueTable.json").is_file()
    ), None)
    payload = load_json(table_path, {}) if table_path else {}
    source = normalize_posix(table_path.relative_to(export_root)) if table_path else ""
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    operands: list[dict[str, Any]] = []
    definitions: dict[int, dict[str, Any]] = {}

    for raw_cue_id, row in sorted((payload.items() if isinstance(payload, dict) else []), key=lambda item: str(item[0])):
        if not isinstance(row, dict):
            continue
        try:
            cue_signed_id = int(raw_cue_id)
        except (TypeError, ValueError):
            continue
        cue_id = cue_signed_id & 0xFFFFFFFF
        definition = {
            "cueSignedId": cue_signed_id,
            "cueId": cue_id,
            "cueHex": f"0x{cue_id:08x}",
            "source": source,
            "handlerCount": 0,
            "directHandlerCount": 0,
            "levelHandlerCount": 0,
            "behaviorEvents": [],
            "expressionOperands": [],
        }

        handlers: list[tuple[str, str, int, dict[str, Any]]] = []
        for handler_index, handler in enumerate(row.get("directHandlers") or []):
            if isinstance(handler, dict):
                handlers.append(("direct", "", handler_index, handler))
        level_map = row.get("levelHandlerMap") if isinstance(row.get("levelHandlerMap"), dict) else {}
        for level_id, wrapper in sorted(level_map.items(), key=lambda item: str(item[0])):
            level_handlers = wrapper.get("handlers") if isinstance(wrapper, dict) else wrapper
            if not isinstance(level_handlers, list):
                continue
            for handler_index, handler in enumerate(level_handlers):
                if isinstance(handler, dict):
                    handlers.append(("level", str(level_id), handler_index, handler))

        for handler_scope, level_id, handler_index, handler in handlers:
            definition["handlerCount"] += 1
            definition[f"{handler_scope}HandlerCount"] += 1
            handler_base = (
                f"{raw_cue_id}.directHandlers[{handler_index}]"
                if handler_scope == "direct"
                else f"{raw_cue_id}.levelHandlerMap[{level_id}].handlers[{handler_index}]"
            )
            for expression_side, root_name in (("behavior", "behaviourExpr"), ("condition", "conditionExpr")):
                for node, expression_path in _iter_audio_cue_expression_nodes(
                    handler.get(root_name),
                    f"{handler_base}.{root_name}",
                ):
                    try:
                        expr_type = int(node.get("exprType"))
                    except (TypeError, ValueError):
                        continue
                    string_value = str(node.get("stringValue") or "").strip()
                    common = {
                        "cueSignedId": cue_signed_id,
                        "cueId": cue_id,
                        "cueHex": f"0x{cue_id:08x}",
                        "handlerScope": handler_scope,
                        "handlerIndex": handler_index,
                        "expressionSide": expression_side,
                        "expressionPath": expression_path,
                        "exprType": expr_type,
                        "boolValue": bool(node.get("boolValue")),
                        "intValue": node.get("intValue"),
                        "floatValue": node.get("floatValue"),
                        "stringValue": string_value,
                        "source": source,
                    }
                    if level_id:
                        common["levelId"] = level_id
                    if expression_side == "behavior" and expr_type == 3 and string_value:
                        context = {
                            "kind": "audioCueBehaviorEvent",
                            "table": "AudioCueTable",
                            "semanticRole": "cueBehaviorEventRequest",
                            "evidence": "exactAudioCueBehaviorExpression",
                            "triggerRequestEvidence": ["audioCueBehaviorExprType3"],
                            "triggerRuntimeActivationStatuses": ["cueInvocationAndExpressionEvaluationRequired"],
                            **common,
                        }
                        _append_context(contexts, seen, string_value, context)
                        definition["behaviorEvents"].append({"eventId": string_value, **context})
                    elif expr_type == 8 and string_value:
                        operand = {
                            "kind": "audioCueExpressionOperand",
                            "semanticRole": "runtimeCueVariable",
                            "wwiseEventStatus": "notApplicable",
                            "evidence": "exactAudioCueExpressionOperand",
                            **common,
                        }
                        operands.append(operand)
                        definition["expressionOperands"].append(operand)
        definitions[cue_id] = definition

    return {
        "eventContexts": dict(contexts),
        "expressionOperands": operands,
        "cueDefinitions": definitions,
        "source": source,
    }


def collect_audio_global_control_semantics(
    export_root: Path,
    cue_semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recover Global cue references and RTPC parameters without making Event claims."""

    cue_semantics = cue_semantics or collect_audio_cue_semantics(export_root)
    cue_definitions = cue_semantics.get("cueDefinitions") or {}
    global_path = _first_recovered_mono_behaviour(export_root, "AudioGlobalConfig")
    global_config = load_json(global_path, {}) if global_path else {}
    source = normalize_posix(global_path.relative_to(export_root)) if global_path else ""
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    cue_refs: list[dict[str, Any]] = []
    rtpc_parameters: list[dict[str, Any]] = []
    if not isinstance(global_config, dict):
        global_config = {}

    for field, value in global_config.items():
        if not str(field).startswith("musicCue"):
            continue
        raw = value.get("_id") if isinstance(value, dict) else value
        if not isinstance(raw, int) or isinstance(raw, bool) or raw == 0:
            continue
        cue_id = raw & 0xFFFFFFFF
        definition = cue_definitions.get(cue_id)
        ref = {
            "kind": "audioGlobalMusicCueRef",
            "field": str(field),
            "cueSignedId": raw,
            "cueId": cue_id,
            "cueHex": f"0x{cue_id:08x}",
            "definitionStatus": "resolved" if definition else "missing",
            "source": source,
            "evidence": "exactSerializedAudioGlobalConfigCueId",
            "wwiseEventStatus": "notApplicable",
        }
        if definition:
            ref["handlerCount"] = definition.get("handlerCount", 0)
            ref["behaviorEventCount"] = len(definition.get("behaviorEvents") or [])
            ref["expressionOperandCount"] = len(definition.get("expressionOperands") or [])
            for behavior in definition.get("behaviorEvents") or []:
                event_name = str(behavior.get("eventId") or "").strip()
                if not event_name:
                    continue
                _append_context(contexts, seen, event_name, {
                    "kind": "audioGlobalMusicCueBehaviorEvent",
                    "table": "AudioGlobalConfig",
                    "semanticRole": "globalLifecycleMusicCueBehaviorEvent",
                    "globalMusicCueField": str(field),
                    "cueSignedId": raw,
                    "cueId": cue_id,
                    "cueHex": f"0x{cue_id:08x}",
                    "handlerScope": behavior.get("handlerScope"),
                    "levelId": behavior.get("levelId"),
                    "handlerIndex": behavior.get("handlerIndex"),
                    "expressionPath": behavior.get("expressionPath"),
                    "exprType": 3,
                    "source": source,
                    "evidence": "exactGlobalMusicCueToAudioCueBehaviorChain",
                    "triggerRequestEvidence": ["serializedGlobalMusicCueReference", "audioCueBehaviorExprType3"],
                    "triggerRuntimeActivationStatuses": ["globalLifecycleCueInvocationAndExpressionEvaluationRequired"],
                })
        cue_refs.append(ref)

    for field in (
        "rtpcGlobalVol", "rtpcMusicVol", "rtpcSfxVol", "rtpcVoiceVol",
        "rtpcControllerSpeakerVol", "rtpcVibrationVol",
        "listenerSpeedRtpcName", "listenerAccelerationRtpcName",
    ):
        parameter_name = str(global_config.get(field) or "").strip()
        if not parameter_name:
            continue
        rtpc_parameters.append({
            "kind": "rtpcParameter",
            "parameterName": parameter_name,
            "field": field,
            "source": source,
            "evidence": "exactSerializedAudioGlobalConfigParameter",
            "wwiseEventStatus": "notApplicable",
        })
    return {
        "eventContexts": dict(contexts),
        "audioGlobalMusicCueRefs": cue_refs,
        "rtpcParameters": rtpc_parameters,
    }


def collect_table_contexts(
    export_root: Path,
    runtime_model: dict[str, Any] | None = None,
    *,
    cue_semantics: dict[str, Any] | None = None,
    global_controls: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    prefix_re = re.compile(r"^(?:au_|bark_|radio_)", re.IGNORECASE)
    named_event_field_re = re.compile(
        r"(?:event(?:s|ids?)?$|musicEventSample$|^audio(?:collect|die|hit|pick|drag|drop)$)",
        re.IGNORECASE,
    )

    def visit(value: Any, path: str, table: str, source: str) -> None:
        if isinstance(value, str) and prefix_re.match(value.strip()):
            field_path = re.sub(r"\[\d+\]$", "", path)
            field_name = field_path.rsplit(".", 1)[-1]
            semantic_role = ""
            if named_event_field_re.search(field_name):
                semantic_role = "authoredEventName"
            # Voice IDs, audioOverride values, radio row IDs, and continuation
            # IDs are media/dialog identities rather than Wwise Events.  Do
            # not flatten them into this Event inventory.
            if semantic_role:
                _append_context(contexts, seen, value, {
                    "kind": "table",
                    "table": table,
                    "path": path,
                    "source": source,
                    "semanticRole": semantic_role,
                    "evidence": "exactTableField",
                })
        elif isinstance(value, int) and not isinstance(value, bool) and value:
            # List indices belong to the containing authored field.  Preserve
            # that field name so arrays such as levelInitEvent[] are recovered
            # as event ids without promoting adjacent music-state integers.
            field_path = re.sub(r"\[\d+\]$", "", path)
            field_name = field_path.rsplit(".", 1)[-1]
            if AUDIO_HASH_FIELD_RE.search(field_name):
                event_hash = value & 0xFFFFFFFF
                _append_context(contexts, seen, event_hash_context_key(event_hash), {
                    "kind": "tableEventHash",
                    "table": table,
                    "path": path,
                    "source": source,
                    "signedValue": value,
                    "eventHash": event_hash,
                    "evidence": "authoredUint32EventId",
                })
        elif isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, table, source)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", table, source)

    for table_name in AUDIO_TABLE_NAMES:
        if table_name == "AudioCueTable.json":
            continue
        path = next((
            export_root / "structured" / source_root / "Table" / table_name
            for source_root in ("Persistent", "StreamingAssets")
            if (export_root / "structured" / source_root / "Table" / table_name).is_file()
        ), None)
        if path is None:
            continue
        payload = load_json(path, None)
        if payload is not None:
            visit(payload, "", path.stem, normalize_posix(path.relative_to(export_root)))
    cue_semantics = cue_semantics or collect_audio_cue_semantics(export_root)
    global_controls = global_controls or collect_audio_global_control_semantics(export_root, cue_semantics)
    for event_id, rows in cue_semantics.get("eventContexts", {}).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    for event_id, rows in global_controls.get("eventContexts", {}).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    for event_id, rows in collect_authored_runtime_config_contexts(export_root, runtime_model).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    # RemoteCommon audioId is an authored Wwise Event request, unlike the
    # adjacent voiceId/audioOverride identities that the generic table walker
    # intentionally leaves out. Keep this route explicit so Event summaries
    # do not manufacture a Timeline-carrier gap for it.
    for event_id, rows in _build_remote_common_event_contexts(export_root).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    return dict(contexts)


def collect_table_audio_event_hashes(export_root: Path) -> set[int]:
    contexts = collect_table_contexts(export_root)
    hashes: set[int] = set()
    for key in contexts:
        if not key.startswith("#0x"):
            continue
        try:
            hashes.add(int(key[1:], 16) & 0xFFFFFFFF)
        except ValueError:
            continue
    return hashes


def collect_table_audio_event_names(export_root: Path) -> set[str]:
    """Return exact authored Event names from tables and recovered audio configs."""

    return {
        key
        for key, rows in collect_table_contexts(export_root).items()
        if key
        and not key.startswith("#0x")
        and rows
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


def exact_wwise_event_aliases(audio_index: dict[str, Any]) -> list[dict[str, Any]]:
    """Return cross-source aliases only when one hash has one exact name."""

    by_hash: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()
    for source_key in (
        "audioDialogWwiseEventAliases",
        "voiceTableWwiseEventAliases",
        "typedUiTableWwiseEventAliases",
        "snsVoiceWwiseEventAliases",
        "skillIdDictionaryWwiseEventAliases",
    ):
        for raw_row in audio_index.get(source_key) or []:
            if not isinstance(raw_row, dict):
                continue
            try:
                event_hash = int(raw_row.get("eventHash")) & 0xFFFFFFFF
            except (TypeError, ValueError):
                continue
            name = str(raw_row.get("name") or "").strip()
            if not name:
                continue
            previous = by_hash.get(event_hash)
            if previous is not None and str(previous.get("name") or "").casefold() != name.casefold():
                conflicts.add(event_hash)
                continue
            by_hash.setdefault(event_hash, raw_row)
    for event_hash in conflicts:
        by_hash.pop(event_hash, None)
    return sorted(
        by_hash.values(),
        key=lambda row: (str(row.get("name") or "").casefold(), int(row.get("eventHash") or 0)),
    )


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


def collect_responsive_voice_contexts(
    export_root: Path,
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Attach authored responsive-voice routes to exact Wwise Event aliases.

    Alias rows have already passed the three-way AudioDialog path hash,
    signed voice-id, and complete type-4 Wwise Event-id equality gate.  The
    response table proves possible trigger membership; native selection,
    cooldown, probability, tone replacement, and the actually heard response
    remain unresolved.
    """

    aliases = {
        int(row.get("eventHash")) & 0xFFFFFFFF: row
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict)
        and isinstance(row.get("eventHash"), int)
        and str(row.get("name") or "").strip()
    }
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    if not aliases:
        return {}

    for event_hash, alias in sorted(aliases.items()):
        event_id = str(alias["name"]).strip().lower()
        _append_context(contexts, seen, event_id, {
            "kind": "audioDialogVoiceDefinition",
            "voiceId": alias.get("voiceId"),
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "audioDialogPath": alias.get("name"),
            "codec": alias.get("codec"),
            "speakerChannel": alias.get("speakerChannel") or "",
            "voType": alias.get("voType"),
            "sources": alias.get("sources") or [],
            "evidence": alias.get("evidence") or "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
            "playbackPlacementStatus": "definitionOnly",
        })

    responsive_path = next((
        export_root / "structured" / source / "Table" / "ResponsiveDialog.json"
        for source in ("StreamingAssets", "Persistent")
        if (export_root / "structured" / source / "Table" / "ResponsiveDialog.json").is_file()
    ), None)
    if responsive_path is not None:
        payload = load_json(responsive_path, {})
        source = normalize_posix(responsive_path.relative_to(export_root))
        for sentence_type, sentence_row in (payload.items() if isinstance(payload, dict) else []):
            speakers = sentence_row.get("speakers") if isinstance(sentence_row, dict) else None
            if not isinstance(speakers, dict):
                continue
            for speaker_id, speaker_row in speakers.items():
                triggers = speaker_row.get("triggers") if isinstance(speaker_row, dict) else None
                if not isinstance(triggers, dict):
                    continue
                for trigger_key, trigger_row in triggers.items():
                    if not isinstance(trigger_row, dict):
                        continue
                    responses = trigger_row.get("response") or []
                    weights = trigger_row.get("weight") or []
                    if not isinstance(responses, list):
                        continue
                    if not isinstance(weights, list):
                        weights = []
                    for response_index, raw_voice_id in enumerate(responses):
                        if not isinstance(raw_voice_id, int):
                            continue
                        event_hash = raw_voice_id & 0xFFFFFFFF
                        alias = aliases.get(event_hash)
                        if alias is None:
                            continue
                        event_id = str(alias["name"]).strip().lower()
                        _append_context(contexts, seen, event_id, {
                            "kind": "responsiveDialogVoice",
                            "sentenceType": str(sentence_type),
                            "speakerId": str(speaker_id),
                            "triggerKey": str(trigger_key),
                            "triggerTypeId": trigger_row.get("triggerTypeId"),
                            "responseIndex": response_index,
                            "responseWeight": weights[response_index] if response_index < len(weights) else None,
                            "voiceId": raw_voice_id,
                            "eventHash": event_hash,
                            "audioDialogPath": alias.get("name"),
                            "source": source,
                            "evidence": "exactResponsiveDialogResponseVoiceId",
                            "runtimeRoute": "VoiceResponseProcessor._HandleSelection -> _QueueResponse -> VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice",
                            "runtimeSelectionStatus": "probabilityCooldownBandLimitToneAndLiveChoiceUnobserved",
                            "playbackPlacementStatus": "authoredPossibleTrigger",
                        })

    tone_path = next((
        export_root / "structured" / source / "Table" / "AudioVoTone.json"
        for source in ("StreamingAssets", "Persistent")
        if (export_root / "structured" / source / "Table" / "AudioVoTone.json").is_file()
    ), None)
    if tone_path is not None:
        payload = load_json(tone_path, {})
        source = normalize_posix(tone_path.relative_to(export_root))
        for raw_base_id, tone_row in (payload.items() if isinstance(payload, dict) else []):
            try:
                base_voice_id = int(raw_base_id)
            except (TypeError, ValueError):
                continue
            tone_list = tone_row.get("toneList") if isinstance(tone_row, dict) else None
            for variant_index, raw_voice_id in enumerate(tone_list or []):
                if not isinstance(raw_voice_id, int):
                    continue
                event_hash = raw_voice_id & 0xFFFFFFFF
                alias = aliases.get(event_hash)
                if alias is None:
                    continue
                event_id = str(alias["name"]).strip().lower()
                _append_context(contexts, seen, event_id, {
                    "kind": "voiceToneVariant",
                    "baseVoiceId": base_voice_id,
                    "variantVoiceId": raw_voice_id,
                    "variantIndex": variant_index,
                    "eventHash": event_hash,
                    "audioDialogPath": alias.get("name"),
                    "source": source,
                    "evidence": "exactAudioVoToneVariantVoiceId",
                    "runtimeRoute": "VoiceUtilsInternal.ApplyRandomVoiceTone -> TryReplaceVoiceIdWithTone",
                    "runtimeSelectionStatus": "liveVariantSelectionUnobserved",
                    "playbackPlacementStatus": "selectionTransformOnly",
                })
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


def managed_literal_contexts(
    metadata_path: Path | None,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    names = [
        name for name in collect_metadata_audio_literals(metadata_path)
        if not is_rtpc_parameter_name(name)
    ]
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for name in names:
        _append_context(contexts, seen, name, {
            "kind": "binaryManagedLiteral",
            "literal": name,
            "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
            "evidence": "exactManagedStringLiteral",
        })
    return dict(contexts), names


def _evidence_object_types(evidence: dict[str, Any]) -> dict[str, int]:
    raw = evidence.get("objectTypeCounts")
    if isinstance(raw, dict):
        return {str(key): int(value) for key, value in raw.items() if isinstance(value, int)}
    return {}


def wwise_event_playback_role(evidence_rows: list[dict[str, Any]]) -> str:
    """Classify typed root Actions without treating control Events as missing media."""
    playback_operations = {"play", "playEvent"}
    control_operations = {
        "stop", "pause", "resume", "break", "seek",
        "setState", "resetGameParameter",
    }
    operations: list[str] = []
    for evidence in evidence_rows:
        for action in evidence.get("actionEvidence") or []:
            if not isinstance(action, dict):
                continue
            operation = str(action.get("operation") or "")
            try:
                operation_type = int(action.get("actionType")) & 0xFF00
            except (TypeError, ValueError):
                operation_type = -1
            if operation_type == 0x1200:
                operation = "setState"
            elif operation_type == 0x1400:
                operation = "resetGameParameter"
            if operation:
                operations.append(operation)
    has_playback = any(value in playback_operations for value in operations) or any(
        int(evidence.get("rootPlayActionCount") or 0) > 0 for evidence in evidence_rows
    )
    has_control = any(value in control_operations for value in operations)
    if has_playback and has_control:
        return "mixedPlaybackAndControl"
    if has_playback:
        return "playback"
    if has_control and operations and all(value in control_operations for value in operations):
        return "controlOnly"
    return "unresolved"


def build_event_rows(
    audio_index: dict[str, Any],
    contexts: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidate_seen: dict[str, set[tuple[str, str]]] = defaultdict(set)
    hashes: dict[str, int] = {}
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("eventId") or entry.get("id") or "").strip().lower()
        if not key:
            continue
        try:
            hashes[key] = int(entry.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            pass
        compact = compact_media(entry)
        marker = (str(compact.get("mediaId") or compact.get("id") or ""), str(compact.get("src") or ""))
        if marker in candidate_seen[key]:
            continue
        candidate_seen[key].add(marker)
        candidates[key].append(compact)

    evidence_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bank_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for evidence in audio_index.get("eventEvidence") or []:
        if not isinstance(evidence, dict):
            continue
        key = str(evidence.get("eventId") or "").strip().lower()
        if not key:
            continue
        try:
            event_hash = int(evidence.get("eventHash")) & 0xFFFFFFFF
            hashes.setdefault(key, event_hash)
        except (TypeError, ValueError):
            event_hash = 0
        object_types = _evidence_object_types(evidence)
        selection_types = [
            HIRC_OBJECT_TYPE_LABELS.get(int(type_id), f"type{type_id}")
            for type_id in evidence.get("selectionObjectTypes") or []
            if isinstance(type_id, int)
        ]
        compact_evidence = {
            "bankId": evidence.get("bankId"),
            "bankVersion": evidence.get("bankVersion"),
            "bank": evidence.get("bank"),
            "edgeParser": evidence.get("edgeParser"),
            "traversalStatus": evidence.get("traversalStatus") or "unknown",
            "actionIds": evidence.get("actionIds") or [],
            "actionEvidence": evidence.get("actionEvidence") or [],
            "actionDispatchEvidence": evidence.get("actionDispatchEvidence") or {},
            "rootPlayActionCount": int(evidence.get("rootPlayActionCount") or 0),
            "rootStopActionCount": int(evidence.get("rootStopActionCount") or 0),
            "visitedObjectCount": len(evidence.get("visitedObjectIds") or []),
            "mediaIds": evidence.get("mediaIds") or [],
            "objectTypeCounts": object_types,
            "selectionContainerTypes": selection_types,
            "containerEvidence": compact_container_evidence(evidence.get("containerEvidence") or []),
            "musicNodeEvidence": evidence.get("musicNodeEvidence") or [],
            "sourceObjectSummary": evidence.get("sourceObjectSummary") or {},
            "nonMediaSourceEvidence": evidence.get("nonMediaSourceEvidence") or [],
            "unresolvedNodes": evidence.get("unresolvedNodes") or [],
            "source": evidence.get("source") or "wwiseHirc",
            "nestedReferenceConfidence": evidence.get("nestedReferenceConfidence") or "unknown",
        }
        evidence_by_event[key].append(compact_evidence)
        bank_name = str(evidence.get("bank") or "")
        try:
            bank_id = int(evidence.get("bankId") or 0)
        except (TypeError, ValueError):
            bank_id = 0
        bank_key = (bank_name, bank_id)
        bank = bank_rows.setdefault(bank_key, {
            "bank": bank_name,
            "bankId": bank_id,
            "eventIds": set(),
            "mediaIds": set(),
            "selectionEventIds": set(),
            "visitedObjectTypeOccurrences": Counter(),
        })
        bank["eventIds"].add(key)
        bank["mediaIds"].update(str(value) for value in evidence.get("mediaIds") or [])
        if selection_types:
            bank["selectionEventIds"].add(key)
        bank["visitedObjectTypeOccurrences"].update(object_types)

    # The authored-name index is intentionally incomplete: Wwise banks also
    # contain Event objects whose uint32 identity has no recovered string or
    # gameplay callsite yet. Keep those objects visible under a stable hash
    # key and use their typed HIRC traversal to recover media relations without
    # inventing a trigger name or ownership location.
    known_key_by_hash = {event_hash: key for key, event_hash in hashes.items()}
    authored_inventory_hashes = set(known_key_by_hash)
    for alias in exact_wwise_event_aliases(audio_index):
        if not isinstance(alias, dict):
            continue
        try:
            event_hash = int(alias.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        event_name = str(alias.get("name") or "").strip()
        if not event_name or event_hash in authored_inventory_hashes:
            continue
        key = event_name.lower()
        known_key_by_hash.setdefault(event_hash, key)
        hashes[key] = event_hash
    entry_by_media_id: dict[int, dict[str, Any]] = {}
    hotfix_entries_by_media_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in audio_index.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get("mediaId") or entry.get("id")
        try:
            media_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        entry_by_media_id.setdefault(media_id, entry)
        if (
            not entry.get("eventId")
            and str(entry.get("sourceBlock") or "") == "hotfix-audio"
        ):
            hotfix_entries_by_media_id[media_id].append(entry)
    for inventory in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(inventory, dict):
            continue
        try:
            event_hash = int(inventory.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        if event_hash in authored_inventory_hashes:
            continue
        key = known_key_by_hash.setdefault(event_hash, hashed_event_key(event_hash))
        hashes[key] = event_hash
        object_types = _evidence_object_types(inventory)
        selection_types = [
            HIRC_OBJECT_TYPE_LABELS.get(int(type_id), f"type{type_id}")
            for type_id in inventory.get("selectionObjectTypes") or []
            if isinstance(type_id, int)
        ]
        compact_evidence = {
            "bankId": inventory.get("bankId"),
            "bankVersion": inventory.get("bankVersion"),
            "bank": inventory.get("bank"),
            "edgeParser": "wwise150TypedCompactObjectInventory",
            "traversalStatus": inventory.get("traversalStatus") or "unknown",
            "actionIds": inventory.get("actionIds") or [],
            "actionEvidence": inventory.get("actionEvidence") or [],
            "actionDispatchEvidence": inventory.get("actionDispatchEvidence") or {},
            "rootPlayActionCount": int(inventory.get("rootPlayActionCount") or 0),
            "rootStopActionCount": int(inventory.get("rootStopActionCount") or 0),
            "visitedObjectCount": int(inventory.get("visitedObjectCount") or 0),
            "mediaIds": inventory.get("mediaIds") or [],
            "objectTypeCounts": object_types,
            "selectionContainerTypes": selection_types,
            "sourceObjectSummary": inventory.get("sourceObjectSummary") or {},
            "nonMediaSourceEvidence": inventory.get("nonMediaSourceEvidence") or [],
            "unresolvedNodes": inventory.get("unresolvedNodeSamples") or [],
            "unresolvedNodeCount": int(inventory.get("unresolvedNodeCount") or 0),
            "source": "wwiseHircObjectInventory",
            "nestedReferenceConfidence": (
                "typedExact"
                if inventory.get("traversalStatus") == "complete"
                else "typedPartial"
            ),
            "eventIdentityStatus": "wwiseObjectWithoutRecoveredTriggerName",
        }
        evidence_by_event[key].append(compact_evidence)
        root_action_ids = sorted({
            int(row.get("rootActionId"))
            for row in inventory.get("actionEvidence") or []
            if isinstance(row, dict) and isinstance(row.get("rootActionId"), int)
        })
        relation_types = [
            str(value)
            for value in inventory.get("mediaRelationTypes") or []
            if str(value)
        ]
        for media_id in inventory.get("mediaIds") or []:
            try:
                media_id = int(media_id)
            except (TypeError, ValueError):
                continue
            entry = entry_by_media_id.get(media_id)
            if not entry:
                continue
            compact = compact_media(entry)
            compact.update({
                "id": key,
                "eventId": key,
                "eventHash": event_hash,
                "mediaId": media_id,
                "bankId": inventory.get("bankId"),
                "bank": inventory.get("bank"),
                "source": "wwiseHircObjectInventory",
                "wwiseMediaEvidence": [{
                    "mediaId": media_id,
                    "rootActionIds": root_action_ids,
                    "relationTypes": relation_types,
                    "bankId": inventory.get("bankId"),
                    "bankPackage": PurePosixPath(str(inventory.get("bank") or "").replace("\\", "/")).name,
                }],
            })
            marker = (str(media_id), str(compact.get("src") or ""))
            if marker in candidate_seen[key]:
                continue
            candidate_seen[key].add(marker)
            candidates[key].append(compact)
        bank_name = str(inventory.get("bank") or "")
        bank_id = int(inventory.get("bankId") or 0)
        bank = bank_rows.setdefault((bank_name, bank_id), {
            "bank": bank_name,
            "bankId": bank_id,
            "eventIds": set(),
            "mediaIds": set(),
            "selectionEventIds": set(),
            "visitedObjectTypeOccurrences": Counter(),
        })
        bank["eventIds"].add(key)
        bank["mediaIds"].update(str(value) for value in inventory.get("mediaIds") or [])
        if selection_types:
            bank["selectionEventIds"].add(key)
        bank["visitedObjectTypeOccurrences"].update(object_types)

    display_names: dict[str, str] = {}
    for value in audio_index.get("eventNames") or []:
        display = str(value or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    for alias in exact_wwise_event_aliases(audio_index):
        if not isinstance(alias, dict):
            continue
        display = str(alias.get("name") or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        display = str(entry.get("eventId") or entry.get("id") or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    exact_alias_by_hash = {
        int(alias.get("eventHash")) & 0xFFFFFFFF: alias
        for alias in exact_wwise_event_aliases(audio_index)
        if isinstance(alias, dict) and isinstance(alias.get("eventHash"), int)
    }
    all_names = set(display_names)
    all_names.update(candidates)
    all_names.update(evidence_by_event)
    all_names.update(key for key in contexts if not key.startswith("#0x"))
    # Numeric contexts attach to whichever named or hash-only Event already
    # owns that uint32.  Emit a synthetic row only for an authored hash absent
    # from every available bank, rather than duplicating it as a #0x... row.
    known_hashes = set(hashes.values())
    for context_key in contexts:
        if not context_key.startswith("#0x"):
            continue
        try:
            event_hash = int(context_key[1:], 16) & 0xFFFFFFFF
        except ValueError:
            continue
        if event_hash in known_hashes:
            continue
        synthetic_key = hashed_event_key(event_hash)
        all_names.add(synthetic_key)
        hashes[synthetic_key] = event_hash
        known_hashes.add(event_hash)
    rows: list[dict[str, Any]] = []
    media_to_events: dict[str, list[str]] = defaultdict(list)
    bank_inventory = audio_index.get("hircSummary") or {}
    bank_package_count = int(bank_inventory.get("packageCount") or 0)
    bank_package_fingerprint = str(bank_inventory.get("packageFingerprint") or "")
    for key in sorted(all_names):
        event_candidates = list(candidates.get(key, []))
        candidate_sources = {
            str(candidate.get("src") or candidate.get("rel") or "")
            for candidate in event_candidates
        }
        # A HotfixAudio package replaces media by numeric Wwise media id. If
        # the replacement bytes differ from the base package, both decoded
        # occurrences must remain visible, but both inherit the exact Event
        # relation already proven for that media id. Do this only for typed
        # HotfixAudio provenance; generic cross-bank id collisions are not
        # merged.
        for base_candidate in list(event_candidates):
            try:
                media_id = int(base_candidate.get("mediaId") or base_candidate.get("id"))
            except (TypeError, ValueError):
                continue
            for replacement_entry in hotfix_entries_by_media_id.get(media_id, []):
                replacement = compact_media(replacement_entry)
                replacement_src = str(replacement.get("src") or replacement.get("rel") or "")
                if not replacement_src or replacement_src in candidate_sources:
                    continue
                replacement.update({
                    "id": key,
                    "eventId": key,
                    "eventHash": hashes.get(key),
                    "mediaId": media_id,
                    "hotfixMediaReplacement": True,
                    "mediaResolutionEvidence": "hotfixPackageMediaIdReplacesBaseMediaId",
                    "wwiseMediaEvidence": base_candidate.get("wwiseMediaEvidence") or [],
                })
                event_candidates.append(replacement)
                candidate_sources.add(replacement_src)
        event_candidates = sorted(
            event_candidates,
            key=lambda row: (int(row.get("mediaId") or 0), str(row.get("src") or "")),
        )
        content_counts = Counter(
            str(row.get("contentSha256") or "")
            for row in event_candidates
            if row.get("contentSha256")
        )
        for candidate in event_candidates:
            content_hash = str(candidate.get("contentSha256") or "")
            if content_hash and content_counts[content_hash] > 1:
                candidate["contentEquivalentCount"] = content_counts[content_hash]
        unique_content_keys = {
            str(row.get("contentSha256") or row.get("src") or row.get("mediaId") or "")
            for row in event_candidates
            if row.get("contentSha256") or row.get("src") or row.get("mediaId")
        }
        for candidate in event_candidates:
            marker = str(candidate.get("src") or candidate.get("rel") or candidate.get("mediaId") or "")
            if marker and key not in media_to_events[marker]:
                media_to_events[marker].append(key)
        event_contexts = list(contexts.get(key, []))
        event_hash = hashes.get(key)
        authored_event_hash = (
            event_hash
            if event_hash is not None
            else audio_hash_generator_compute(display_names.get(key, key))
        )
        if event_hash is not None:
            event_contexts.extend(contexts.get(event_hash_context_key(event_hash), []))
        evidence_rows = evidence_by_event.get(key, [])
        playback_role = wwise_event_playback_role(evidence_rows)
        identity_alias = exact_alias_by_hash.get(event_hash) if event_hash is not None else None
        character_animation_owner_ids = sorted({
            str(context.get("ownerId") or "")
            for context in event_contexts
            if context.get("kind") == "characterAnimation" and context.get("ownerId")
        })
        enemy_animation_owner_ids = sorted({
            str(context.get("ownerId") or "")
            for context in event_contexts
            if context.get("kind") == "enemyAnimation" and context.get("ownerId")
        })
        animation_functions = sorted({
            str(value)
            for context in event_contexts
            for value in context.get("animationFunctions") or []
            if str(value)
        })
        custom_footstep_variants = aggregate_custom_footstep_context_variants(event_contexts)
        animation_context_scope = (
            "sharedPlayableCharacters" if len(character_animation_owner_ids) > 1
            else "singlePlayableCharacter" if character_animation_owner_ids
            else "sharedEnemyTemplates" if len(enemy_animation_owner_ids) > 1
            else "singleEnemyTemplate" if enemy_animation_owner_ids
            else ""
        )
        selection_types = sorted({
            value
            for evidence in evidence_rows
            for value in evidence.get("selectionContainerTypes") or []
        })
        media_relation_types = sorted({
            str(relation)
            for candidate in event_candidates
            for media_evidence in candidate.get("wwiseMediaEvidence") or []
            for relation in media_evidence.get("relationTypes") or []
            if str(relation)
        })
        play_root_ids = sorted({
            int(root_action_id)
            for candidate in event_candidates
            for media_evidence in candidate.get("wwiseMediaEvidence") or []
            for root_action_id in media_evidence.get("rootActionIds") or []
            if isinstance(root_action_id, int)
        })
        traversal_status = (
            "partial" if any(row.get("traversalStatus") == "partial" for row in evidence_rows)
            else "complete" if evidence_rows else "unresolved"
        )
        branch_relations = [value for value in media_relation_types if value != "directSound"]
        if branch_relations or selection_types:
            runtime_selection = "runtimeBranchUnresolved"
        elif len(play_root_ids) > 1:
            runtime_selection = "multiplePlayRootsTimingUnresolved"
        elif len(event_candidates) == 1:
            runtime_selection = "singlePossibleMedia"
        elif event_candidates:
            runtime_selection = "multiplePossibleMediaUnresolved"
        else:
            runtime_selection = "unresolved"
        category = event_category(key)
        category_evidence = "namePrefix" if category != "unknown" else "unclassified"
        if category == "unknown" and (identity_alias or {}).get("dictionaryKind") == "skill_id":
            category = "sfx"
            category_evidence = "exactSkillIdDictionaryEventIdentity"
        if category == "unknown" and any(
            context.get("kind") == "projectileSoundField"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactProjectileSoundField"
        if category == "unknown" and any(
            context.get("kind") == "spawnerPreWarnAudio"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactSpawnerPreWarnAudioField"
        if category == "unknown" and any(
            context.get("kind") == "patrolSubActionPlayAudio"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactPatrolSubPlayAudioData"
        if category == "unknown" and any(
            context.get("kind") == "charInteractAudioEvent"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactCharInteractAudioEventField"
        if category == "unknown" and any(
            context.get("kind") == "physicsAudioComponentEvent"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactPhysicsAudioComponentEventField"
        if category == "unknown" and any(
            context.get("kind") in {
                "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent"
            }
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactModelViewStateAudioBehavior"
        if category == "unknown" and any(
            context.get("kind") in {
                "audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant",
                "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
                "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
                "responsiveVoiceEventTemplate", "voiceTableWwiseEvent", "snsVoiceMessageEvent",
            }
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "voice"
            category_evidence = (
                "exactTypedVoiceTableWwiseEventField"
                if any(
                    context.get("kind") in {
                        "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
                        "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
                        "responsiveVoiceEventTemplate", "voiceTableWwiseEvent", "snsVoiceMessageEvent",
                    }
                    for context in event_contexts
                    if isinstance(context, dict)
                )
                else "exactAudioDialogVoiceIdentity"
            )
        if key.startswith("hashed-event:0x"):
            event_identity_status = (
                "authoredHashMatchedWwiseObject"
                if event_contexts
                else "wwiseObjectWithoutRecoveredTriggerName"
            )
        else:
            event_identity_status = "recoveredAuthoredName"
        rows.append({
            "id": key,
            "name": display_names.get(key, key),
            "hash": event_hash,
            "category": category,
            "categoryEvidence": category_evidence,
            "foundInWwise": bool(evidence_rows),
            "audioLibraryResolutionStatus": (
                "resolvedWwiseEventObject"
                if evidence_rows
                else "eventHashAbsentFromScannedBankSet"
            ),
            "eventIdentityStatus": event_identity_status,
            "eventNameEvidence": (identity_alias or {}).get("evidence"),
            "eventNameSourceKind": (
                "skillIdDictionary"
                if (identity_alias or {}).get("dictionaryKind") == "skill_id"
                else None
            ),
            "identityOnlyPlaybackPlacementStatus": (identity_alias or {}).get("playbackPlacementStatus"),
            "identityNumericSkillIds": (identity_alias or {}).get("numericSkillIds") or [],
            "identityTableSources": (identity_alias or {}).get("tableSources") or [],
            "identitySkillDataSources": (identity_alias or {}).get("skillDataSources") or [],
            "playbackRole": playback_role,
            "authoredEventHash": authored_event_hash,
            "authoredEventHashHex": f"0x{authored_event_hash:08x}",
            "scannedBankPackageCount": bank_package_count,
            "scannedBankPackageFingerprint": bank_package_fingerprint,
            "possibleMediaCount": len(event_candidates),
            "uniqueDecodedContentCount": len(unique_content_keys),
            "contentEquivalentLeafCount": sum(max(0, count - 1) for count in content_counts.values()),
            "candidateCount": len(event_candidates),
            "playRootCount": len(play_root_ids) or max(
                (int(row.get("rootPlayActionCount") or 0) for row in evidence_rows),
                default=0,
            ),
            "playRootActionIds": play_root_ids,
            "runtimeSelection": runtime_selection,
            "mediaRelationTypes": media_relation_types,
            "selectionContainerTypes": selection_types,
            "traversalStatus": traversal_status,
            "unresolvedNodeCount": sum(len(row.get("unresolvedNodes") or []) for row in evidence_rows),
            "contextCount": len(event_contexts),
            "contextStoredCount": len(event_contexts),
            "contextsTruncated": False,
            "playableCharacterAnimationOwnerCount": len(character_animation_owner_ids),
            "enemyAnimationOwnerCount": len(enemy_animation_owner_ids),
            "animationContextScope": animation_context_scope,
            "animationFunctions": animation_functions,
            "customFootstepOccurrenceCount": sum(
                int(variant.get("occurrenceCount") or 0)
                for variant in custom_footstep_variants
            ),
            "customFootstepParameterVariants": custom_footstep_variants,
            "contexts": event_contexts,
            "evidence": evidence_rows,
            "media": event_candidates,
        })

    banks = []
    for bank in bank_rows.values():
        named_event_count = sum(
            not event_id.startswith("hashed-event:0x")
            for event_id in bank["eventIds"]
        )
        banks.append({
            "bank": bank["bank"],
            "bankId": bank["bankId"],
            "eventCount": len(bank["eventIds"]),
            "namedEventCount": named_event_count,
            "mediaCount": len(bank["mediaIds"]),
            "selectionEventCount": len(bank["selectionEventIds"]),
            "visitedObjectTypeOccurrences": dict(sorted(bank["visitedObjectTypeOccurrences"].items())),
        })
    banks.sort(key=lambda row: (str(row.get("bank") or ""), int(row.get("bankId") or 0)))
    return rows, media_to_events, banks


def build_media_rows(audio_index: dict[str, Any], media_to_events: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    definition_evidence_by_media_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for evidence in (audio_index.get("hircSummary") or {}).get("definitionOnlyDecodedSoundObjects") or []:
        if not isinstance(evidence, dict):
            continue
        try:
            media_id = int(evidence.get("mediaId"))
        except (TypeError, ValueError):
            continue
        definition_evidence_by_media_id[media_id].append(evidence)
    for entry in audio_index.get("entries") or []:
        if not isinstance(entry, dict) or entry.get("eventId"):
            continue
        compact = compact_media(entry)
        rel = str(compact.get("rel") or "")
        storage = str(compact.get("storageRoot") or "")
        marker = (storage, rel)
        if not rel or marker in seen:
            continue
        seen.add(marker)
        reverse_key = str(compact.get("src") or rel or compact.get("mediaId") or "")
        event_ids = media_to_events.get(reverse_key, [])
        compact["eventCount"] = len(event_ids)
        if event_ids:
            compact["eventIds"] = event_ids
        try:
            media_id = int(compact.get("mediaId") or compact.get("id"))
        except (TypeError, ValueError):
            media_id = 0
        definition_evidence = definition_evidence_by_media_id.get(media_id, [])
        if definition_evidence and not event_ids:
            compact["audioLibraryObjectStatus"] = "wwiseSoundDefinitionWithoutEventPath"
            compact["wwiseDefinitionEvidence"] = definition_evidence
        rows.append(compact)
    rows.sort(key=lambda row: (
        str(row.get("audioCategory") or "unknown"),
        str(row.get("id") or ""),
        str(row.get("rel") or ""),
    ))
    return rows


def annotate_media_playback_locations(
    media: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> Counter[str]:
    """Classify recovered placement without inventing a runtime playback edge."""

    event_has_context: dict[str, bool] = {}
    for event in events:
        context_rows = [
            row for row in event.get("contexts") or [] if isinstance(row, dict)
        ]
        has_context = any(
            str(row.get("playbackPlacementStatus") or "")
            not in {"definitionOnly", "selectionTransformOnly"}
            for row in context_rows
        )
        if not context_rows:
            has_context = bool(int(event.get("contextCount") or 0))
        for value in (event.get("id"), event.get("eventId"), event.get("name")):
            key = str(value or "").strip().casefold()
            if key:
                event_has_context[key] = event_has_context.get(key, False) or has_context

    counts: Counter[str] = Counter()
    for row in media:
        event_ids = [
            str(value or "").strip().casefold()
            for value in row.get("eventIds") or []
            if str(value or "").strip()
        ]
        if row.get("audioDialogKey") or row.get("audioDialogPath"):
            status = "directDialogMedia"
        elif any(event_has_context.get(event_id, False) for event_id in event_ids):
            status = "authoredEventContext"
        elif event_ids:
            status = "eventRelationOnly"
        else:
            status = "unknown"
        row["playbackLocationStatus"] = status
        counts[status] += 1
    return counts


def semantic_context_group(kind: Any) -> str:
    value = str(kind or "")
    if value in {"characterSkill", "enemySkill", "buffPlaySoundAction", "projectileSoundField"}:
        return "gameplay"
    if value == "cutsceneTimeline":
        return "cutscene"
    if value in {"characterAnimation", "enemyAnimation", "animationCallbackOwnerUnresolved"}:
        return "animation"
    if value in {"levelSequenceAudio", "timelineAudioCueBehaviorEvent"}:
        return "timeline"
    if value in {"levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent"}:
        return "scripted"
    if value in {
        "table", "tableEventHash", "dialogLifecycle", "interactiveAudioTrigger", "interactiveComponentTrigger",
        "audioGlobalConfigEvent", "audioGlobalConfigEventHash",
        "audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent",
        "spawnerPreWarnAudio", "patrolSubActionPlayAudio", "charInteractAudioEvent", "physicsAudioComponentEvent",
        "audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant",
        "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
        "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
        "responsiveVoiceEventTemplate", "voiceTableWwiseEvent",
        "uiAnimationOpenEvent", "activityPushPopupBgmEvent",
        "activityCenterBgmEvent", "uiVideoAudioEvent",
        "domainRegionSwitchEvent", "domainUpgradeAnimationEvent",
        "typedUiTableWwiseEvent", "snsVoiceMessageEvent",
        "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent",
        "remoteCommonAudio",
    }:
        return "authoredConfig"
    if value == "binaryManagedLiteral":
        return "managedRuntime"
    if value == "luaPostEvent":
        return "luaRuntime"
    return ""


def event_summary_row(row: dict[str, Any], detail_shard: str) -> dict[str, Any]:
    contexts = row.get("contexts") or []
    timeline_contexts = [
        context for context in contexts
        if isinstance(context, dict) and context.get("kind") == "levelSequenceAudio"
    ]
    timeline_asset_ids = {
        (
            str(context.get("timelineAssetSerializedFile") or ""),
            str(context.get("timelineAssetPathId") or ""),
        )
        for context in timeline_contexts
        if context.get("timelineAssetSerializedFile") or context.get("timelineAssetPathId")
    }
    director_count = sum(
        int(context.get("playableDirectorCount") or 0)
        for context in timeline_contexts
    )
    exact_timeline_count = sum(
        context.get("confidence") == "exact" for context in timeline_contexts
    )
    inferred_timeline_count = sum(
        context.get("confidence") == "inferred" for context in timeline_contexts
    )
    timeline_gap_count = sum(
        context.get("confidence") == "gap" for context in timeline_contexts
    )
    levelsequence_action_count = sum(
        int(context.get("levelScriptActionCount") or 0)
        for context in timeline_contexts
    )
    context_search: set[str] = set()
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for key in (
            "kind", "ownerId", "groupId", "storyKey", "table", "path",
            "semanticRole", "confidence", "skillId", "actionKind", "clip",
            "animationOwnershipScope", "possibleMediaScope", "triggerBindingStatus",
            "modelId", "subTemplateId", "triggerStateId", "triggerStateName",
            "triggerCustomState", "ownerKind", "stateDirection", "audioStateMask",
            "componentIndex", "sourceOffset", "sourceFingerprint",
            "projectileId", "projectileKey", "soundField", "triggerPhase",
            "runtimeActivationStatus", "sourceRoot", "sourcePathId", "sourceJsonPath",
            "signedValue", "eventHex", "sourceFile", "sourceVfsPath", "semanticPath",
            "sizzleSoundTriggerDistance", "ringProjectileSoundSmoothFactor",
            "cueName", "cueSignedId", "cueId", "cueHex", "cueHashEvidence",
            "definitionStatus", "handlerScope", "levelId",
            "handlerIndex", "expressionSide", "expressionPath", "exprType",
            "controllerId", "modelAnimatorIndex", "modelAnimatorName",
            "layerIndex", "layerFsmIndex", "layerName", "stateIndex", "stateName",
            "stateType", "behaviorIndex", "behaviorTag", "behaviorTagHex",
            "behaviorType", "behaviorKind", "behaviorTime", "timeFlowSwitch",
            "normalAudioId", "audioNodeName", "eAudioTriggerState",
            "templateAssociationStatus",
            "globalMusicCueField",
            "authoredEventId", "spawnerConfigId", "enemyLibraryIndex", "enemyId",
            "bornTemplateId", "enemyLevel", "spawnerEnemyKey", "preWarnTime",
            "preWarnEffectKey", "schemaMappingId", "schemaStatus",
            "remoteCommonId", "singleId", "middleId", "index", "autoPlay",
            "autoPlayTime", "voiceId", "voiceLinkStatus", "startAudioEvent",
            "endAudioEvent",
            "patrolId", "patrolIndex", "pointIndex", "patrolSubActionType",
            "subActionUnionTag", "subActionUnionTagHex", "nativeConsumer",
            "charInteractPerformId", "actionPhase", "actionIndex", "logicId",
            "delay", "duration", "devOnly", "useEvent", "attachedActorType",
            "charIndex", "endStop", "is2D", "runtimeOwnerStatus",
            "attachedActorResolutionStatus", "unionMappingId", "endOffset",
            "action", "levelScriptId", "sourcePath", "sourceSha256",
            "recordIndex", "recordStart", "recordUid", "recordLocalId",
            "actionMapRole", "unionTag", "serializedMemberCount",
            "nativeMappingId", "payloadShape", "eventName", "triggerRole",
            "sourceField", "definitionOwnerId", "templatePath", "componentTag",
            "componentTagHex", "componentEndOffset", "propertyCount",
            "componentOccurrenceIndex",
            "authoredProperty", "runtimeField", "propertySourceOffset",
            "propertyValueSourceOffset", "valueType", "valueTypeName",
            "runtimeMappingId", "interactiveTableSha256",
            "customFootstepOccurrenceCount",
            "levelSequenceId", "timelineAssetName", "timelineAssetNameBase",
            "timelineAssetSerializedFile", "timelineAssetPathId", "timelineTrackName",
            "timelineTrackPathId", "timelineClipIndex", "timelineClipDisplayName",
            "timelineClipStartSec", "timelineClipDurationSec", "timelineClipEndSec",
            "timelineClipTimingEvidence", "timelineTrackRawJsonPath", "audioPlayableType",
            "audioPlayableRuntimeContractId", "audioPlayablePathId",
            "audioPlayableKeyStatus", "audioPlayableIsCue",
            "audioPlayableStopEventAtClipEnd", "audioPlayableFadeOutMs",
            "audioPlayableEnableSeek", "audioPlayableUseBindingObject", "audioPlayableIs2D",
            "audioPlayableControlEvidence", "audioPlayableRawJsonPath",
            "playableDirectorName", "playableDirectorPathId",
            "ownershipEvidenceLevel", "triggerEvidenceLevel", "timelineOwnershipStatus",
            "levelScriptActionCount", "playableDirectorCount", "evidenceBoundary",
            "lifecyclePhase", "arrayIndex", "runtimeMethod", "runtimeMethodToken",
            "runtimeDispatchStatus", "mediaSelectionStatus", "ownerStatus",
        ):
            value = context.get(key)
            if value not in (None, "", []):
                context_search.add(str(value))
        for key in (
            "skillIds", "actionKinds", "animationClips", "animationFunctions",
            "animationClipContexts", "authoredEventIds", "triggerRequestEvidence",
            "triggerRuntimeActivationStatuses", "triggerRelationTypes",
            "triggerOwnershipMethods", "triggerEvidenceKinds", "triggerBuffIds",
            "triggerSourcePaths",
            "sourcePaths",
            "sourceRoots", "sourceFingerprints", "consumerIds", "consumerAliasIds",
            "interactiveTableSourcePaths",
            "interactiveTemplateIds", "interactiveTemplatePaths", "interactiveConsumerIds",
            "authoredSkillIds",
            "bornBuffIds", "preWarnEffectFixedRotation",
            "actorList",
            "playableDirectorNames", "playableDirectorPathIds",
            "levelScriptIds", "levelScriptSourcePaths",
            "levelSequenceFieldOffsets",
        ):
            context_search.update(str(value) for value in context.get(key) or [] if str(value))
        for variant in context.get("customFootstepParameterVariants") or []:
            if not isinstance(variant, dict):
                continue
            for value in variant.values():
                if isinstance(value, (str, int, float, bool)):
                    context_search.add(str(value))
        for action in context.get("triggerPlaySoundActions") or []:
            if not isinstance(action, dict):
                continue
            for value in action.values():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    context_search.add(str(value))
                elif isinstance(value, list):
                    context_search.update(str(item) for item in value if str(item))
        for field_name, field in (context.get("fields") or {}).items():
            context_search.add(str(field_name))
            if not isinstance(field, dict):
                continue
            for value in field.values():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    context_search.add(str(value))
    media = row.get("media") or []
    scopes = sorted({str(value.get("audioScope") or value.get("storageRoot") or "") for value in media if value.get("audioScope") or value.get("storageRoot")})
    banks = sorted({str(value.get("bankPackage") or "") for evidence in media for value in evidence.get("wwiseMediaEvidence") or [] if value.get("bankPackage")})
    source_kinds: set[str] = set()
    source_plugin_ids: set[str] = set()
    non_media_source_count = 0
    for evidence in row.get("evidence") or []:
        if not isinstance(evidence, dict):
            continue
        source_summary = evidence.get("sourceObjectSummary") or {}
        source_kinds.update(str(value) for value in (source_summary.get("sourceKindCounts") or {}))
        source_plugin_ids.update(str(value) for value in (source_summary.get("pluginCounts") or {}))
        for source in evidence.get("nonMediaSourceEvidence") or []:
            if not isinstance(source, dict):
                continue
            non_media_source_count += 1
            for key in (
                "pluginIdHex", "pluginName", "pluginTypeLabel", "streamTypeLabel",
                "sourceKind", "mediaLocationStatus",
            ):
                if source.get(key) not in (None, ""):
                    context_search.add(str(source[key]))
    keys = (
        "id", "name", "hash", "category", "categoryEvidence", "foundInWwise",
        "audioLibraryResolutionStatus", "eventIdentityStatus", "eventNameEvidence",
        "eventNameSourceKind", "identityOnlyPlaybackPlacementStatus",
        "identityNumericSkillIds", "identityTableSources", "identitySkillDataSources", "playbackRole",
        "authoredEventHash", "authoredEventHashHex",
        "scannedBankPackageCount", "scannedBankPackageFingerprint",
        "possibleMediaCount", "candidateCount", "uniqueDecodedContentCount",
        "contentEquivalentLeafCount", "playRootCount", "playRootActionIds",
        "runtimeSelection", "mediaRelationTypes", "selectionContainerTypes",
        "traversalStatus", "unresolvedNodeCount", "contextCount",
        "contextStoredCount", "contextsTruncated",
        "playableCharacterAnimationOwnerCount", "enemyAnimationOwnerCount",
        "animationContextScope", "animationFunctions", "customFootstepOccurrenceCount",
        "customFootstepParameterVariants",
        "timelineContextCount", "timelineAssetCount", "playableDirectorCount",
        "levelScriptPlayLevelSequenceActionCount", "timelineExactContextCount",
        "timelineInferredContextCount", "timelineOwnershipGapCount",
    )
    summary = {key: row[key] for key in keys if row.get(key) not in (None, "", [])}
    summary.update({
        "contextGroups": sorted({semantic_context_group(context.get("kind")) for context in contexts if isinstance(context, dict)} - {""}),
        "contextKinds": sorted({
            str(context.get("kind") or "")
            for context in contexts
            if isinstance(context, dict) and context.get("kind")
        }),
        "triggerBindingStatuses": sorted({
            str(context.get("triggerBindingStatus") or "")
            for context in contexts
            if isinstance(context, dict) and context.get("triggerBindingStatus")
        }),
        "contextSearch": sorted(context_search),
        "scope": scopes[0] if len(scopes) == 1 else "mixed" if scopes else "unknown",
        "source": "wwiseHirc" if row.get("foundInWwise") else "authoredContext",
        "bankPackages": banks,
        "detailShard": detail_shard,
    })
    if timeline_contexts:
        summary.update({
            "timelineContextCount": len(timeline_contexts),
            "timelineAssetCount": len(timeline_asset_ids),
            "playableDirectorCount": director_count,
            "levelScriptPlayLevelSequenceActionCount": levelsequence_action_count,
            "timelineExactContextCount": exact_timeline_count,
            "timelineInferredContextCount": inferred_timeline_count,
            "timelineOwnershipGapCount": timeline_gap_count,
        })
    if source_kinds:
        summary["sourceKinds"] = sorted(source_kinds)
    if source_plugin_ids:
        summary["sourcePluginIds"] = sorted(source_plugin_ids)
    if non_media_source_count:
        summary["nonMediaSourceCount"] = non_media_source_count
    canonical_play_sound_contexts = [
        context for context in contexts
        if isinstance(context, dict) and context.get("kind") == "buffPlaySoundAction"
    ]
    trigger_play_sound_action_count = sum(
        int(context.get("triggerPlaySoundActionCount") or 0)
        for context in (canonical_play_sound_contexts or contexts)
        if isinstance(context, dict)
    )
    if trigger_play_sound_action_count:
        summary["triggerPlaySoundActionCount"] = trigger_play_sound_action_count
    return summary


def build_audio_semantic_data(
    audio_index: dict[str, Any],
    *,
    language: str,
    export_root: Path,
    webui_root: Path,
    metadata_path: Path | None = None,
    cutscene_events: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    language = language.upper()
    runtime_model = build_runtime_model(metadata_path, export_root)
    literal_context_index, managed_literal_names = managed_literal_contexts(metadata_path)
    cue_semantics = collect_audio_cue_semantics(export_root)
    global_controls = collect_audio_global_control_semantics(export_root, cue_semantics)
    spawner_semantics = collect_spawner_pre_warn_semantics(export_root)
    patrol_semantics = collect_patrol_sub_action_audio_semantics(export_root)
    char_interact_semantics = collect_char_interact_audio_semantics(export_root)
    physics_audio_semantics = collect_physics_audio_semantics(export_root)
    model_view_semantics = collect_model_view_state_audio_semantics(export_root)
    managed_rtpc_parameters = [{
        "kind": "rtpcParameter",
        "parameterName": name,
        "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
        "evidence": "exactManagedStringLiteral",
        "wwiseEventStatus": "notApplicable",
    } for name in collect_metadata_audio_literals(metadata_path) if is_rtpc_parameter_name(name)]
    levelscript_semantics = collect_levelscript_audio_semantics(
        export_root,
        cue_semantics=cue_semantics,
    )
    responsive_voice_contexts = collect_responsive_voice_contexts(
        export_root,
        audio_index,
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
        levelscript_semantics.get("eventContexts") or {},
        collect_table_contexts(
            export_root,
            runtime_model,
            cue_semantics=cue_semantics,
            global_controls=global_controls,
        ),
        cutscene_contexts(cutscene_events),
        lua_audio_contexts(audio_index),
        literal_context_index,
        responsive_voice_contexts,
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
                candidate_hash_contexts[event_id].add(event_hash_context_key(event_hash))
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
    events, media_to_events, banks = build_event_rows(audio_index, contexts)
    media = build_media_rows(audio_index, media_to_events)
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
    )
    media_playback_location_counts = annotate_media_playback_locations(media, events)
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
    media_name = "media.json"
    event_details: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_summaries: list[dict[str, Any]] = []
    for row in events:
        bucket_value = int(row.get("hash") or int(hashlib.sha256(str(row.get("id") or "").encode("utf-8")).hexdigest()[:8], 16)) & 0x3F
        detail_shard = f"event_details/{bucket_value:02x}.json"
        event_details[detail_shard].append(row)
        event_summaries.append(event_summary_row(row, detail_shard))
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
    json_dump(out_root / media_name, {
        "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
        "language": language,
        "media": media,
    })
    trigger_context_name = "trigger_contexts.json"
    json_dump(out_root / trigger_context_name, trigger_context_catalog)

    payload = {
        "schemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
        "generated": audio_index.get("generated") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "debugOnly": False,
        "sourceIndex": f"export_full/structured/Audio/{language}/index.json",
        "sourceIndexFingerprint": {
            "generated": audio_index.get("generated"),
            "eventEvidenceSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
            "counts": audio_index.get("counts") or {},
        },
        "shards": {"events": events_name, "media": media_name},
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
            "eventRecords": len(events),
            "namedEvents": len(named_event_ids),
            "eventsFoundInWwise": linked_events,
            "wwiseEventObjectHashes": sum(
                row.get("foundInWwise") for row in events
            ),
            "wwiseEventObjectOccurrences": len(audio_index.get("wwiseEventInventory") or []),
            "wwiseEventObjectsWithoutRecoveredAuthoredTrigger": sum(
                row.get("eventIdentityStatus") == "wwiseObjectWithoutRecoveredTriggerName"
                for row in events
            ),
            "wwisePlaybackEvents": sum(row.get("playbackRole") == "playback" for row in events),
            "wwiseMixedPlaybackAndControlEvents": sum(
                row.get("playbackRole") == "mixedPlaybackAndControl" for row in events
            ),
            "wwiseControlOnlyEvents": sum(row.get("playbackRole") == "controlOnly" for row in events),
            "wwiseEventsWithUnresolvedActionRole": sum(
                row.get("playbackRole") == "unresolved" for row in events
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
            "snsVoiceMessageEvents": context_kind_event_counts.get("snsVoiceMessageEvent", 0),
            "voiceNarratingChannelEvents": context_kind_event_counts.get("voiceNarratingChannelEvent", 0),
            "voiceRadioChannelEvents": context_kind_event_counts.get("voiceRadioChannelEvent", 0),
            "audioDialogOverrideWwiseEvents": context_kind_event_counts.get("audioDialogOverrideWwiseEvent", 0),
            "responsiveVoiceEventTemplates": context_kind_event_counts.get("responsiveVoiceEventTemplate", 0),
            "uiAnimationOpenEvents": context_kind_event_counts.get("uiAnimationOpenEvent", 0),
            "activityPushPopupBgmEvents": context_kind_event_counts.get("activityPushPopupBgmEvent", 0),
            "activityCenterBgmEvents": context_kind_event_counts.get("activityCenterBgmEvent", 0),
            "uiVideoAudioEvents": context_kind_event_counts.get("uiVideoAudioEvent", 0),
            "domainRegionSwitchEvents": context_kind_event_counts.get("domainRegionSwitchEvent", 0),
            "domainUpgradeAnimationEvents": context_kind_event_counts.get("domainUpgradeAnimationEvent", 0),
            "responsiveDialogWwiseEvents": sum(
                any(context.get("kind") == "responsiveDialogVoice" for context in row.get("contexts") or [])
                for row in events
            ),
            "wwiseVoiceToneVariantEvents": sum(
                any(context.get("kind") == "voiceToneVariant" for context in row.get("contexts") or [])
                for row in events
            ),
            "authoredEventsUnresolvedToWwise": sum(
                not row.get("foundInWwise") for row in events
            ),
            "mediaPlaybackLocationUnknown": media_playback_location_counts.get("unknown", 0),
            "definitionOnlyDecodedMedia": sum(
                row.get("audioLibraryObjectStatus") == "wwiseSoundDefinitionWithoutEventPath"
                for row in media
            ),
            "mediaWithEventRelationOnly": media_playback_location_counts.get("eventRelationOnly", 0),
            "mediaWithAuthoredEventContext": media_playback_location_counts.get("authoredEventContext", 0),
            "directDialogMedia": media_playback_location_counts.get("directDialogMedia", 0),
            "eventPossibleMedia": sum(int(row.get("possibleMediaCount") or 0) for row in events),
            "eventMediaCandidates": sum(int(row.get("possibleMediaCount") or 0) for row in events),
            "banksWithIndexedEvents": len(banks),
            "banksWithNamedEvents": sum(
                int(bank.get("namedEventCount") or 0) > 0 for bank in banks
            ),
            "runtimeSelectionUnresolved": selection_events,
            "typedTraversalComplete": sum(row.get("traversalStatus") == "complete" for row in events),
            "typedTraversalPartial": sum(row.get("traversalStatus") == "partial" for row in events),
            "eventsWithMultiplePlayRoots": sum(int(row.get("playRootCount") or 0) > 1 for row in events),
            "wwiseCodecSourceReferences": wwise_source_reference_counts.get("codecMedia", 0),
            "wwiseExternalSourceReferences": wwise_source_reference_counts.get("externalSourceCodec", 0),
            "wwiseSynthesizedSourceReferences": wwise_source_reference_counts.get("synthesizedSource", 0),
            "wwiseEventsWithExternalSource": wwise_source_event_counts.get("externalSourceCodec", 0),
            "wwiseEventsWithSynthesizedSource": wwise_source_event_counts.get("synthesizedSource", 0),
            "wwiseSourcePluginIds": len(wwise_source_plugin_counts),
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
            "binaryManagedAudioLiterals": len(managed_literal_names),
            "binaryManagedLiteralWwiseEvents": managed_literal_hirc_matches,
            "luaPostEventNames": context_kind_event_counts.get("luaPostEvent", 0),
            "luaPostEventContexts": context_kind_counts.get("luaPostEvent", 0),
            "luaPostEventNamesFoundInWwise": sum(
                bool(row.get("foundInWwise"))
                and any(
                    isinstance(context, dict) and context.get("kind") == "luaPostEvent"
                    for context in row.get("contexts") or []
                )
                for row in events
            ),
            "authoredTableEventHashes": len(table_event_hashes),
            "authoredTableEventHashesFound": table_event_hash_matches,
            "runtimeSystems": len(runtime_systems),
            "interactiveAudioTriggerEvents": context_kind_event_counts.get("interactiveAudioTrigger", 0),
            "interactiveAudioTriggerContexts": context_kind_counts.get("interactiveAudioTrigger", 0),
            "interactiveComponentTriggerEvents": context_kind_event_counts.get("interactiveComponentTrigger", 0),
            "interactiveComponentTriggerContexts": context_kind_counts.get("interactiveComponentTrigger", 0),
            "audioGlobalConfigEvents": (
                context_kind_event_counts.get("audioGlobalConfigEvent", 0)
                + context_kind_event_counts.get("audioGlobalConfigEventHash", 0)
            ),
            "audioGlobalConfigContexts": (
                context_kind_counts.get("audioGlobalConfigEvent", 0)
                + context_kind_counts.get("audioGlobalConfigEventHash", 0)
            ),
            "projectileSoundEvents": context_kind_event_counts.get("projectileSoundField", 0),
            "projectileSoundContexts": context_kind_counts.get("projectileSoundField", 0),
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
            "physicsAudioConsumerIdentities": (
                (physics_audio_semantics.get("stats") or {}).get("physicsAudioConsumerIdentities") or 0
            ),
            "modelViewStateAudioEvents": (
                context_kind_event_counts.get("modelViewStateAudioEvent", 0)
                + context_kind_event_counts.get("modelViewStatePositionAudioEvent", 0)
            ),
            "modelViewStateAudioEventContexts": (
                context_kind_counts.get("modelViewStateAudioEvent", 0)
                + context_kind_counts.get("modelViewStatePositionAudioEvent", 0)
            ),
            "modelViewStateAudioEventsFoundInWwise": sum(
                bool(row.get("foundInWwise")) for row in model_view_event_rows
            ),
            "modelViewStateAudioEventsUnresolved": sum(
                not row.get("foundInWwise") for row in model_view_event_rows
            ),
            "modelViewStateRtpcControls": len(model_view_semantics.get("rtpcParameters") or []),
            "modelViewStateSpatialControls": len(model_view_semantics.get("spatialControls") or []),
            "modelViewStateCustomAudioControls": len(model_view_semantics.get("customAudioControls") or []),
            "levelScriptAudioActionEvents": context_kind_event_counts.get("levelScriptAudioAction", 0),
            "levelScriptAudioActionContexts": context_kind_counts.get("levelScriptAudioAction", 0),
            "levelScriptAudioCueInvocations": len(levelscript_semantics.get("cueInvocations") or []),
            "levelScriptAudioCueInvocationsResolved": (
                (levelscript_semantics.get("stats") or {}).get("cueDefinitionStatusCounts") or {}
            ).get("resolved", 0),
            "levelScriptAudioCueInvocationsMissing": (
                (levelscript_semantics.get("stats") or {}).get("cueDefinitionStatusCounts") or {}
            ).get("missing", 0),
            "levelScriptAudioCueBehaviorEvents": context_kind_event_counts.get("levelScriptAudioCueBehaviorEvent", 0),
            "levelScriptAudioCueBehaviorContexts": context_kind_counts.get("levelScriptAudioCueBehaviorEvent", 0),
            "levelScriptDynamicAudioBindings": len(levelscript_semantics.get("dynamicEventBindings") or []),
            "levelScriptResolvedDynamicAudioBindings": len(
                levelscript_semantics.get("resolvedDynamicEventBindings") or []
            ),
            "levelScriptRadioActions": (
                (radio_catalog.get("counts") or {}).get(
                    "levelScriptRadioActionRecords", 0
                )
            ),
            "levelScriptConstantRadioBindings": (
                (radio_catalog.get("counts") or {}).get("constantRadioBindings", 0)
            ),
            "levelScriptDynamicRadioBindings": (
                (radio_catalog.get("counts") or {}).get("dynamicRadioBindings", 0)
            ),
            "radioTableDefinitions": (
                (radio_catalog.get("counts") or {}).get("radioTableDefinitions", 0)
            ),
            "radioTableLines": (
                (radio_catalog.get("counts") or {}).get("radioTableLines", 0)
            ),
            "radioTableDecodedDirectMedia": (
                (radio_catalog.get("counts") or {}).get("decodedDirectMedia", 0)
            ),
            "levelScriptAudioControls": len(levelscript_semantics.get("controlActions") or []),
            "levelScriptDynamicControlBindings": len(levelscript_semantics.get("dynamicControlBindings") or []),
            "levelSequenceAudioEvents": context_kind_event_counts.get("levelSequenceAudio", 0),
            "levelSequenceAudioContexts": context_kind_counts.get("levelSequenceAudio", 0),
            "timelineAudioCueBehaviorEvents": context_kind_event_counts.get(
                "timelineAudioCueBehaviorEvent", 0
            ),
            "timelineAudioCueBehaviorContexts": context_kind_counts.get(
                "timelineAudioCueBehaviorEvent", 0
            ),
            "timelineAudioCueInvocations": (
                (timeline_cue_semantics.get("stats") or {}).get("timelineCueInvocations", 0)
            ),
            "timelineAudioCueInvocationsResolved": (
                (timeline_cue_semantics.get("stats") or {}).get("timelineCueInvocationsResolved", 0)
            ),
            "timelineAudioCueInvocationsMissing": (
                (timeline_cue_semantics.get("stats") or {}).get("timelineCueInvocationsMissing", 0)
            ),
            "levelSequenceExactContextEvents": sum(
                any(
                    isinstance(context, dict)
                    and context.get("kind") == "levelSequenceAudio"
                    and context.get("confidence") == "exact"
                    for context in row.get("contexts") or []
                )
                for row in events
            ),
            "levelSequenceInferredContextEvents": sum(
                any(
                    isinstance(context, dict)
                    and context.get("kind") == "levelSequenceAudio"
                    and context.get("confidence") == "inferred"
                    for context in row.get("contexts") or []
                )
                for row in events
            ),
            "levelSequenceOwnershipGapEvents": sum(
                any(
                    isinstance(context, dict)
                    and context.get("kind") == "levelSequenceAudio"
                    and context.get("confidence") == "gap"
                    for context in row.get("contexts") or []
                )
                for row in events
            ),
            "levelSequenceTimelineCarrierEvents": (
                (levelsequence_semantics.get("stats") or {}).get(
                    "eventsWithAnyTimelineCarrier", 0
                )
            ),
            "levelSequencePlayActionExactEvents": (
                (levelsequence_semantics.get("stats") or {}).get(
                    "eventsWithExactLevelSequenceAction", 0
                )
            ),
            "levelSequenceDirectorLinkContexts": (
                (levelsequence_semantics.get("stats") or {}).get(
                    "contextsWithPlayableDirector", 0
                )
            ),
            "levelSequenceDirectorLinkGapContexts": (
                (levelsequence_semantics.get("stats") or {}).get(
                    "contextsWithoutPlayableDirector", 0
                )
            ),
            "levelSequenceRuntimeActivationUnobservedEvents": context_kind_event_counts.get(
                "levelSequenceAudio", 0
            ),
            "levelEventAudioConditionDefinitions": len(LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS),
            "levelEventAudioConditionAuthoredOccurrences": sum(
                int(row.get("authoredOccurrenceCount") or 0)
                for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
            ),
            "authoredPlaySoundActionEvents": play_sound_action_events,
            "authoredPlaySoundActionContexts": play_sound_action_contexts,
            "authoredPlaySoundActionOccurrences": play_sound_action_occurrences,
            "exactSkillConfigTriggerEvents": trigger_status_event_counts.get("exactSkillConfig", 0),
            "inferredSkillConfigOwnerEvents": trigger_status_event_counts.get("inferredSkillConfigOwner", 0),
            "exactEnemyBornBuffTriggerEvents": trigger_status_event_counts.get("exactEnemyBornBuffConfig", 0),
            "exactSkillConfigTriggerContexts": trigger_status_context_counts.get("exactSkillConfig", 0),
            "inferredSkillConfigOwnerContexts": trigger_status_context_counts.get("inferredSkillConfigOwner", 0),
            "exactEnemyBornBuffTriggerContexts": trigger_status_context_counts.get("exactEnemyBornBuffConfig", 0),
            "runtimeTypesMissing": len(runtime_model.get("missingTypes") or []),
            "triggerContexts": int(
                (trigger_context_catalog.get("counts") or {}).get("total") or 0
            ),
            "triggerContextsWithPlayableMedia": int(
                (trigger_context_catalog.get("counts") or {}).get("withPlayableMedia") or 0
            ),
            "triggerContextsRuntimeExecutionUnobserved": int(
                (trigger_context_catalog.get("counts") or {}).get(
                    "runtimeExecutionUnobserved", 0
                )
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
        "hircSummary": audio_index.get("hircSummary") or {},
        "customFootstepModel": custom_footstep_model,
        "triggerCatalog": {
            "spawnerPreWarnAudio": spawner_semantics.get("stats") or {},
            "patrolSubActionPlayAudio": patrol_semantics.get("stats") or {},
            "charInteractAudio": char_interact_semantics.get("stats") or {},
            "physicsAudio": {
                **(physics_audio_semantics.get("stats") or {}),
                "definitions": physics_audio_semantics.get("definitions") or [],
            },
            "modelViewStateAudio": model_view_semantics.get("stats") or {},
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
            "schemaVersion": 1,
            "counts": {
                "audioCueDefinitions": len(cue_semantics.get("cueDefinitions") or {}),
                "audioCueBehaviorEventContexts": sum(
                    len(rows) for rows in (cue_semantics.get("eventContexts") or {}).values()
                ),
                "audioCueExpressionOperands": len(cue_semantics.get("expressionOperands") or []),
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
                "wwiseSelectorPackageValuesCensused": 234,
                "wwiseSelectorValuesWithMetadataStringMatch": 67,
                "wwiseSelectorValuesWithoutRecoveredString": 167,
            },
            "audioCueDefinitions": [
                {key: value for key, value in definition.items() if key not in {"behaviorEvents", "expressionOperands"}}
                | {
                    "behaviorEventCount": len(definition.get("behaviorEvents") or []),
                    "expressionOperandCount": len(definition.get("expressionOperands") or []),
                }
                for definition in (cue_semantics.get("cueDefinitions") or {}).values()
            ],
            "audioCueExpressionOperands": cue_semantics.get("expressionOperands") or [],
            "audioGlobalMusicCueRefs": global_controls.get("audioGlobalMusicCueRefs") or [],
            "rtpcParameters": (global_controls.get("rtpcParameters") or []) + managed_rtpc_parameters,
            "physicsAudioRtpcParameters": physics_audio_semantics.get("rtpcParameters") or [],
            "modelViewStateRtpcParameters": model_view_semantics.get("rtpcParameters") or [],
            "modelViewStateSpatialControls": model_view_semantics.get("spatialControls") or [],
            "modelViewStateCustomAudioControls": model_view_semantics.get("customAudioControls") or [],
            "levelScriptAudioCueInvocations": levelscript_semantics.get("cueInvocations") or [],
            "levelScriptDynamicAudioBindings": levelscript_semantics.get("dynamicEventBindings") or [],
            "levelScriptResolvedDynamicAudioBindings": (
                levelscript_semantics.get("resolvedDynamicEventBindings") or []
            ),
            "levelScriptAudioControls": levelscript_semantics.get("controlActions") or [],
            "levelScriptDynamicControlBindings": levelscript_semantics.get("dynamicControlBindings") or [],
            "timelineAudioCueInvocations": timeline_cue_semantics.get("invocations") or [],
            "levelEventAudioConditions": [
                dict(row) for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
            ],
            "wwiseSelectorGroups": [
                dict(row) for row in AUDIO_RUNTIME_SELECTOR_GROUPS
            ],
            "evidenceBoundary": "Cue behavior exprType=3 values, constant LevelScript Event parameters, LevelScript cue names joined by the native AudioHashGenerator to exact cue behavior expressions, non-empty PhysicsAudio Event properties, and normal ModelView Event/position hashes are authored requests. PhysicsAudio/ModelView RTPC names, ModelView spatial/custom-audio rows, cue/action execution, handler conditions, exprType=8 strings, dynamic Params, state/variable writes, playback handles, placeholder-music ids, unresolved cue hashes, and musicCue* values remain typed controls or unresolved runtime state. LevelEvent OnAudioStateChanged and OnMusicBeatEvent are current-build trigger-input definitions, not playback requests; exhaustive active-overlay scanning found zero authored occurrences. Two Wwise selector groups have exact native setter callsites; three more have high-confidence semantic correlation only. None reveal a live value, selected branch, or authored group name.",
        },
        "runtimeModel": runtime_model,
        "evidenceBoundary": {
            "decodedMedia": "A decoded FLAC/WAV/WEM is a source media object, not proof that it played.",
            "eventMedia": "Possible media leaves use typed Wwise v150 Event -> Action -> reciprocal Children -> Sound/MusicTrack AkBankSourceData edges. Ordinary Codec sources may join decoded media; External Source codec and synthesized Source-plugin records remain non-media playback sources. Play roots and random/sequence/switch/layer relations are preserved; runtime selection and source instantiation are not evaluated. Unsupported plugins, music nodes, and unparsed child structures fail closed.",
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
        },
    }
    json_dump(out_root / "index.json", payload)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--webui-root", type=Path, default=DEFAULT_WEBUI_ROOT)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--metadata", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.metadata is None:
        installed = args.game_root / DEFAULT_METADATA_REL
        cached = args.export_root / "recovered/il2cpp/global-metadata.dat"
        args.metadata = installed if installed.is_file() else (cached if cached.is_file() else None)
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
        cutscene_events=collect_webui_cutscene_events(args.webui_root.resolve(), language),
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
