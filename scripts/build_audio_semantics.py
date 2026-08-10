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
AUDIO_SEMANTIC_SCHEMA_VERSION = 20
RUNTIME_MODEL_CACHE_SCHEMA_VERSION = 12
RADIO_MEDIA_CONTEXT_LIMIT = 64
RADIO_MEDIA_SEARCH_LIMIT = 96
RADIO_CATALOG_ITEM_LIMIT = 64
MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)

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
                "callback",
                "Beyond.Audio.AudioAdapter",
                "_OnEventCallback",
                480008,
                "0x0600005d",
                "0x18328d3e0",
                "Forwards the original callback and cookie through an unresolved delegate thunk.",
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
        ),
        "boundary": (
            "The binary proves the cache/miss branch, Event-id bank load, one-Event PrepareEvent call, "
            "completion callback, Wwise Event post, playing-id mapping, and conditional cache deactivation. It does not prove which branch "
            "ran for a captured request, live switch/state/RTPC values, or the selected Wwise media leaf."
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
            "PostEvent", "StopByPlayingId", "PauseByPlayingId", "ResumeByPlayingId",
            "SetState", "SetSwitch", "SetRtpc", "SeekOnEvent", "RegisterGameObject",
            "UnregisterGameObject", "SetListener", "SetDefaultListener", "SetAudioLanguage",
            "_OnEventPreparedDoPostEvent", "_OnEventCallback", "_PostEvent",
            "_ExecuteActionOnPlayingId",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["playingIdAction"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["switchSelector"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["rtpcSelector"],
        ),
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
        ),
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
    )
    compact = {key: entry[key] for key in keys if entry.get(key) not in (None, "", [])}
    if compact.get("wwiseMediaEvidence"):
        compact["wwiseMediaEvidence"] = [
            {
                key: row[key]
                for key in (
                    "rootActionIds", "soundObjectCount", "relationTypes",
                    "musicTrackObjectCount", "selectionPaths", "bankId", "bankPackage",
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
    "ManualRestoreMusicState": "musicStateRestore",
    "ManualSetMusicState": "musicStateOverride",
    "PlayStandaloneMusic": "standaloneMusicLifecycle",
    "SetAudioCueVar": "cueVariableWrite",
    "StartPlaceholderMusic_DevOnly": "placeholderMusicStart",
    "StopAudio": "playingAudioStop",
    "StopPlaceholderMusic_DevOnly": "placeholderMusicStop",
    "StopVoice": "voiceStop",
    "SwitchAIBarkEnable": "aiBarkEnableSwitch",
    "SwitchAudioState": "entityAudioStateSwitch",
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
        )
    except ImportError:
        from scripts.story_builder.level_bindings import (
            resolve_levelscript_dynamic_property_string,
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
            (0x0306, 0x09), (0x0307, 0x0B),
            (0x034A, 0x14), (0x034B, 0x14), (0x034C, 0x0C),
            (0x034E, 0x0B), (0x034F, 0x10), (0x0352, 0x0C),
            (0x0363, 0x0D), (0x0364, 0x0D), (0x0367, 0x11),
            (0x036B, 0x13),
            (0x0371, 0x0B), (0x0373, 0x0C), (0x03D5, 0x0F),
            (0x04A7, 0x0E), (0x04AC, 0x0A), (0x04B4, 0x0B),
            (0x04B5, 0x09), (0x04B7, 0x0A), (0x04BA, 0x09),
            (0x04BC, 0x0B), (0x04CA, 0x09),
        }

        def decode_file(_path: Path, data: bytes) -> dict[str, Any]:
            records = extract_levelscript_uid_records(data)
            _action_map, memberships = levelscript_action_map_membership(data, records)
            rows: list[dict[str, Any]] = []
            target_count = 0
            for index, record in enumerate(records):
                if levelscript_record_semantic_key(record) not in target_keys:
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
            return {"targetCount": target_count, "rows": rows}

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
    control_actions: list[dict[str, Any]] = []
    dynamic_control_bindings: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    source_files_with_actions = 0
    target_records = 0
    decoded_records = 0
    decode_failures = 0
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
        target_records += int(decoded.get("targetCount") or len(rows)) if isinstance(decoded, dict) else len(rows)
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
                dynamic_radio_bindings.append({
                    **common,
                    "kind": "levelScriptDynamicRadioBinding",
                    "semanticRole": "authoredLevelScriptRadioTrigger",
                    "triggerRole": LEVELSCRIPT_RADIO_ACTION_ROLES[action_name],
                    "sourceField": str(radio_field.get("sourceField") or "_radioId"),
                    "binding": radio_field,
                    "resolutionStatus": "runtimeRadioIdParamUnresolved",
                    "radioIdentityKind": "RadioTableDefinitionId",
                    "wwiseEventStatus": "notApplicable",
                })
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
        "controlActions": control_actions,
        "dynamicControlBindings": dynamic_control_bindings,
        "stats": {
            "sourceFiles": len(overlay),
            "sourceFilesWithAudioActions": source_files_with_actions,
            "targetAudioActionRecords": target_records,
            "decodedAudioActionRecords": decoded_records,
            "decodeFailures": decode_failures,
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
            "the authored property-to-action string join, not action execution or Wwise playback."
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
) -> dict[str, list[dict[str, Any]]]:
    """Decode per-entity InteractiveAudioData state maps from MemoryPack."""

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

    display_names: dict[str, str] = {}
    for value in audio_index.get("eventNames") or []:
        display = str(value or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        display = str(entry.get("eventId") or entry.get("id") or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
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
    for key in sorted(all_names):
        event_candidates = sorted(
            candidates.get(key, []),
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
        if event_hash is not None:
            event_contexts.extend(contexts.get(event_hash_context_key(event_hash), []))
        evidence_rows = evidence_by_event.get(key, [])
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
        rows.append({
            "id": key,
            "name": display_names.get(key, key),
            "hash": event_hash,
            "category": category,
            "categoryEvidence": category_evidence,
            "foundInWwise": bool(evidence_rows),
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
        banks.append({
            "bank": bank["bank"],
            "bankId": bank["bankId"],
            "eventCount": len(bank["eventIds"]),
            "mediaCount": len(bank["mediaIds"]),
            "selectionEventCount": len(bank["selectionEventIds"]),
            "visitedObjectTypeOccurrences": dict(sorted(bank["visitedObjectTypeOccurrences"].items())),
        })
    banks.sort(key=lambda row: (str(row.get("bank") or ""), int(row.get("bankId") or 0)))
    return rows, media_to_events, banks


def build_media_rows(audio_index: dict[str, Any], media_to_events: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
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
        rows.append(compact)
    rows.sort(key=lambda row: (
        str(row.get("audioCategory") or "unknown"),
        str(row.get("id") or ""),
        str(row.get("rel") or ""),
    ))
    return rows


def semantic_context_group(kind: Any) -> str:
    value = str(kind or "")
    if value in {"characterSkill", "enemySkill", "buffPlaySoundAction", "projectileSoundField"}:
        return "gameplay"
    if value == "cutsceneTimeline":
        return "cutscene"
    if value in {"characterAnimation", "enemyAnimation", "animationCallbackOwnerUnresolved"}:
        return "animation"
    if value in {"levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent"}:
        return "scripted"
    if value in {
        "table", "tableEventHash", "interactiveAudioTrigger", "interactiveComponentTrigger",
        "audioGlobalConfigEvent", "audioGlobalConfigEventHash",
        "audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent",
        "spawnerPreWarnAudio", "patrolSubActionPlayAudio", "charInteractAudioEvent", "physicsAudioComponentEvent",
        "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent",
    }:
        return "authoredConfig"
    if value == "binaryManagedLiteral":
        return "managedRuntime"
    return ""


def event_summary_row(row: dict[str, Any], detail_shard: str) -> dict[str, Any]:
    contexts = row.get("contexts") or []
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
    keys = (
        "id", "name", "hash", "category", "categoryEvidence", "foundInWwise",
        "possibleMediaCount", "candidateCount", "uniqueDecodedContentCount",
        "contentEquivalentLeafCount", "playRootCount", "playRootActionIds",
        "runtimeSelection", "mediaRelationTypes", "selectionContainerTypes",
        "traversalStatus", "unresolvedNodeCount", "contextCount",
        "contextStoredCount", "contextsTruncated",
        "playableCharacterAnimationOwnerCount", "enemyAnimationOwnerCount",
        "animationContextScope", "animationFunctions", "customFootstepOccurrenceCount",
        "customFootstepParameterVariants",
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
    levelscript_semantics = collect_levelscript_audio_semantics(
        export_root,
        cue_semantics=cue_semantics,
    )
    managed_rtpc_parameters = [{
        "kind": "rtpcParameter",
        "parameterName": name,
        "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
        "evidence": "exactManagedStringLiteral",
        "wwiseEventStatus": "notApplicable",
    } for name in collect_metadata_audio_literals(metadata_path) if is_rtpc_parameter_name(name)]
    contexts = merge_contexts(
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
        literal_context_index,
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
        "eventDetailShardCount": len(event_details),
        "counts": {
            "decodedMedia": len(media),
            "eventRecords": len(events),
            "namedEvents": len(named_event_ids),
            "eventsFoundInWwise": linked_events,
            "eventPossibleMedia": sum(int(row.get("possibleMediaCount") or 0) for row in events),
            "eventMediaCandidates": sum(int(row.get("possibleMediaCount") or 0) for row in events),
            "banksWithNamedEvents": len(banks),
            "runtimeSelectionUnresolved": selection_events,
            "typedTraversalComplete": sum(row.get("traversalStatus") == "complete" for row in events),
            "typedTraversalPartial": sum(row.get("traversalStatus") == "partial" for row in events),
            "eventsWithMultiplePlayRoots": sum(int(row.get("playRootCount") or 0) > 1 for row in events),
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
            "levelScriptRadio": radio_catalog,
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
                "levelEventAudioConditionDefinitions": len(LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS),
                "levelEventAudioConditionAuthoredOccurrences": sum(
                    int(row.get("authoredOccurrenceCount") or 0)
                    for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
                ),
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
            "levelEventAudioConditions": [
                dict(row) for row in LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
            ],
            "evidenceBoundary": "Cue behavior exprType=3 values, constant LevelScript Event parameters, LevelScript cue names joined by the native AudioHashGenerator to exact cue behavior expressions, non-empty PhysicsAudio Event properties, and normal ModelView Event/position hashes are authored requests. PhysicsAudio/ModelView RTPC names, ModelView spatial/custom-audio rows, cue/action execution, handler conditions, exprType=8 strings, dynamic Params, state/variable writes, playback handles, placeholder-music ids, unresolved cue hashes, and musicCue* values remain typed controls or unresolved runtime state. LevelEvent OnAudioStateChanged and OnMusicBeatEvent are current-build trigger-input definitions, not playback requests; exhaustive active-overlay scanning found zero authored occurrences.",
        },
        "runtimeModel": runtime_model,
        "evidenceBoundary": {
            "decodedMedia": "A decoded FLAC/WAV/WEM is a source media object, not proof that it played.",
            "eventMedia": "Possible media leaves use typed Wwise v150 Event -> Action -> reciprocal Children -> Sound source edges. Play roots and random/sequence/switch/layer relations are preserved; runtime selection is not evaluated. Unsupported music nodes and unparsed child structures fail closed.",
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
        f" {payload['counts']['namedEvents']:,} events,"
        f" {payload['counts']['decodedMedia']:,} media,"
        f" {payload['counts']['runtimeSystems']:,} runtime systems"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
