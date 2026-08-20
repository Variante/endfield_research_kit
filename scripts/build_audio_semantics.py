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
import os
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
    from scripts.audio_semantics import (
        authored_components,
        context_utils,
        event_projection,
        event_summary,
        external_source,
        identifiers,
        interactive_components,
        managed_literals,
        model_view_projection,
        native_evidence,
        purpose,
        responsive_voice,
        table_contexts,
        voice_requests,
    )
elif not __package__:
    from common import sha256_file as file_sha256
    from audio_semantics import (
        authored_components,
        context_utils,
        event_projection,
        event_summary,
        external_source,
        identifiers,
        interactive_components,
        managed_literals,
        model_view_projection,
        native_evidence,
        purpose,
        responsive_voice,
        table_contexts,
        voice_requests,
    )
else:  # pragma: no cover - this file has exactly two supported identities.
    raise ImportError("import as scripts.build_audio_semantics or run the script directly")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_METADATA_REL = Path("il2cpp_data/Metadata/global-metadata.dat")
METADATA_HELPER = ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
RUNTIME_CACHE_REL = Path("recovered/audio_semantics/runtime_metadata.json")

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
AUDIO_SEMANTIC_SCHEMA_VERSION = 112
TRIGGER_CONTEXT_SCHEMA_VERSION = 38

MONO_BEHAVIOUR_AUDIO_EVENT_FIELD_NAMES = frozenset({
    "_spawnAudioEvent", "_finishAudioEvent", "_onHitAudioEvent",
    "_onStartMoveAudioEvent", "_onStopMoveAudioEvent",
    "_onRotationGroundOneShotAudioEvent", "_onEnableLoopAudioEvent",
    "normalAudiId", "audioKey", "_audioKey", "soundEvent",
    "enterSoundName", "exitSoundName", "startHitEvent", "endShootSoundName",
    "shootIsHitSoundName", "shootNotHitSoundName", "aimableSoundEvent",
    "notAimableSoundEvent", "capacityCountLowEvent", "enterWaterSfx",
    "exitWaterSfx", "splashSfx",
})
MONO_BEHAVIOUR_AUDIO_EVENT_PREFILTERS = tuple(sorted(
    {f"{name}._id" for name in MONO_BEHAVIOUR_AUDIO_EVENT_FIELD_NAMES}
    | {"soundBase.soundSpawn", "soundBase.soundFinish", "PlayLineSound"}
))
MONO_BEHAVIOUR_AUDIO_CONTEXT_CACHE_SCHEMA_VERSION = 2
RUNTIME_MODEL_CACHE_SCHEMA_VERSION = 109
METADATA_EVENT_SYMBOL_SCHEMA_VERSION = 1
METADATA_EVENT_SYMBOL_RE = re.compile(r"^AU_[A-Z0-9_]+$")
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
    "DialogAudioEventPlayableAsset": {
        "id": "timelineAudioId.dialogAudioEvent",
        "type": "Beyond.Gameplay.Core.DialogAudioEventPlayableAsset",
        "behaviourType": "Beyond.Gameplay.Core.DialogAudioEventPlayableBehaviour",
        "assetToken": "0x020027eb",
        "behaviourToken": "0x0200282d",
        "requestMethods": [
            {"name": "CreatePlayable", "token": "0x0600f08d"},
            {"name": "ProcessFrame", "token": "0x0600f20e"},
        ],
        "stopMethods": [
            {"name": "OnClipDisable", "token": "0x0600f20d"},
            {"name": "_StopPlaying", "token": "0x0600f20f"},
        ],
        "serializedControls": ["audioEvent", "stopOnDisable"],
        "nativeEvidence": {
            "createPlayableVa": "0x186dcb008",
            "processFrameVa": "0x186dd6d98",
            "stopPlayingVa": "0x186dd7028",
            "processFrameAudioObjectResolver": "Beyond.Audio.AudioPlayableUtil.GetBindObjectAudioObjectId",
            "onClipDisableCallsStopPlaying": True,
        },
        "evidenceBoundary": "currentIl2CppMetadataAndMappedNativePlayableBodies; runtimeDirectorEvaluationUnobserved",
    },
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


def native_unmapped_playback_entry(
    role: str,
    type_name: str,
    method: str,
    virtual_address: str,
    relation: str,
    evidence: str,
) -> dict[str, Any]:
    """Describe a current-build native entry point with no managed owner.

    Some callers enter the bridge through compiler/native helpers that are not
    represented by an IL2CPP method pointer (and are not recovered by the
    generic-instantiation map).  Keep those helpers explicit without inventing
    a managed token or method index.
    """
    return {
        "role": role,
        "type": type_name,
        "method": method,
        "virtualAddress": virtual_address,
        "relation": relation,
        "evidence": evidence,
    }


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
        "alternateEntryPoints": (
            native_unmapped_playback_entry(
                "stringCallbackEntry",
                "Unmapped current-build native helper",
                "string event + callback helper (managed owner unresolved)",
                "0x183288d10",
                (
                    "Timeline and VoicePlayer callers pass eventName, audioObjectId, callbackType, "
                    "and callback. The helper calls Beyond.Audio.AudioHashGenerator.Compute at "
                    "0x18328dcd0, writes a zero cookie, then tail-jumps AudioAdapter._PostEvent "
                    "at 0x18328a690."
                ),
                "decodedCurrentGameAssemblyBody;notInCodegenOrGenericMethodPointerTables",
            ),
        ),
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
        "alternateEntryPoints": (
            native_unmapped_playback_entry(
                "voiceExternalPreparation",
                "Unmapped current-build native helper",
                "VoicePlayer external-source preparation helper (managed owner unresolved)",
                "0x183abef40",
                (
                    "VoicePlayer._PlayVoice supplies the resolver output from VoiceContext.voiceData.data "
                    "(+0x60), wwiseEvent (+0x20), audioObjectId (+0x18), handleId (+0x10), and codec "
                    "(+0x68), plus the Event/path context, and voice handle fields. The selected "
                    "RuntimeVoiceData.FromSparkBuffer path reads VoiceData.codec at serialized +0x14 "
                    "through the shared Int32 reader and copies it raw into that codec slot; no arithmetic "
                    "or enum conversion occurs before this call. Its current native ABI "
                    "is explicit: rcx=resolved externalSourceKey, rdx=wwiseEvent, r8=audioObject, and "
                    "r9d=handleId; stack +0x20 carries codec. The helper validates the Event/path objects, "
                    "writes fixed externalCookie 0x24db9834 and callback type 0x100001, then calls "
                    "Beyond.Audio.AudioAdapter.PostEventExternal at 0x183abf0a0 with the incoming "
                    "Event/object values, resolver output as externalSourceKey, fixed externalCookie "
                    "0x24db9834, callback type 0x100001, the context handle as callback cookie, and "
                    "the fifth stack argument as codec before entering _PostEventWithExternalSource. "
                    "The helper returns the managed PostEventExternal result; downstream static tracing "
                    "shows _PostEventWithExternalSource returns the internal playing id, while the native "
                    "PostEvent result and external-manager registration serial are retained separately."
                ),
                "decodedCurrentGameAssemblyBody;exactVoicePlayerArgumentRegisters;fixedExternalCookieLiteral;directCallToMappedPostEventExternal;managedReturnIsInternalPlayingId;nativePostResultAndManagerSerialSeparate",
            ),
            native_unmapped_playback_entry(
                "voiceExternalSourceKeyResolution",
                "Unmapped current-build native helper",
                "VoicePlayer external-source key/path resolver (managed owner unresolved)",
                "0x183abe750",
                (
                    "VoicePlayer._PlayVoice passes VoiceContext.voiceData.data (+0x60) and an out pointer. The helper "
                    "calls shared formatter target 0x182f25040, whose current body performs runtime/template UTF-16 "
                    "placeholder expansion, stores its returned managed string through the out pointer, and "
                    "tail-enters the write-barrier helper; the out value is then forwarded as "
                    "PostEventExternal.externalSourceKey. The VoicePlayer caller resolves the current "
                    "VoiceI18n metadata type and reads static +0x10 s_languagePrefix, then passes the exact "
                    "formatter arguments (format {0}/{1}/{2}, root Voice, language prefix, VoiceData.path). "
                    "The normal native key is therefore Voice/<language>/<VoiceData.path>. The body does not "
                    "itself read a file or post to Wwise; the same formatter is also called by "
                    "VoiceI18n.GetVoicePath/GetDebugVoicePath (0x186b02b1c/0x186b0296c) and VFS path helpers."
                ),
                "decodedCurrentGameAssemblyBody;voicePlayerVoiceI18nStaticLanguagePrefix;exactVoicePathFormatterArguments;sharedVoiceI18nAndVfsPathCallers;callerAndOutParameterEvidence;templateExpansionAndStringCopy;sharedFormatterTarget0x182f25040",
            ),
            native_unmapped_playback_entry(
                "nativeExternalDescriptor",
                "AkSoundEngine native export",
                "external PostEvent export CSharp_b533bd82e4996d0c1d5686812d0f2",
                "0x1800285d0",
                (
                    "GameAssembly resolves this obfuscated AkSoundEngine export for the external-source overload. "
                    "Its shared native body 0x1800c38b0 enters 0x1800c08d0 when cExternals is nonzero, copies each "
                    "0x20-byte source descriptor, duplicates szFile (descriptor +0) into a native source record "
                    "at record +0x10, and preserves codec/cookie "
                    "plus the optional in-memory pointer/size. The in-memory branch validates RIFF/WAVE/PLUG/MIDI "
                    "headers at 0x18011bf00. The copied allocation is carried through 0x1800c3990's event record "
                    "+0x14 and into the source-manager constructor 0x1800e1320, which retains the copied external-descriptor "
                    "allocation pointer at manager +0x38. No file-open call occurs in this descriptor path, and the later "
                    "source-state key -> exact sourceInfo +0x10 instance join remains unproven."
                ),
                "currentAkSoundEngineExportHash;nativeExternalDescriptorCopy;szFileDescriptorPlus0ToNativeRecordPlus10;descriptorAllocationRetainedAtManagerPlus38;inMemoryWaveValidator;noFileOpenCallsite;sourceStateKeyConstructionKnown;sourceStateKeyContextPlus268;sourceStateKeyInstanceJoinUnproven",
            ),
        ),
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
                "Builds AkExternalSourceInfo and keeps an external playing/object cleanup mapping. The body calls "
                "_GetInternalPlayingId at 0x18328a810 and stores that result in edi, then calls native "
                "AkSoundEngine.PostEvent at 0x183abed90 and stores that result separately in ebx. Telemetry "
                "receives both values, while the function returns edi; the managed UInt32 return is therefore "
                "not the native c3990 registration serial/manager key.",
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
                "externalSourceCookieBankJoinAudit",
                "Wwise External Source AkBankSourceData",
                "sourceId -> iExternalSrcCookie",
                None,
                "",
                "0x24db9834",
                "The current CN v150 HIRC corpus contains 1,712 exact Wwise External Source source records (plugin 0x00080001); every record has sourceId 618371124 = 0x24db9834, the same constant written by the current VoicePlayer external-source helper at 0x183abefd9 before PostEventExternal. This closes the serialized source-cookie to managed AkExternalSourceInfo cookie identity and therefore the callback-family selection boundary. It does not identify the per-request externalSourceKey path, a particular sourceInfo +0x10 instance, or a live callback/file/PCM observation.",
            ),
            native_playback_stage(
                "externalSourceHircPathSeparationAudit",
                "Wwise External Source HIRC path corpus",
                "external source records versus native sourceInfo HIRC owner",
                None,
                "",
                "0x18003a5b0",
                "The current CN event-detail corpus contains 1,712 exact externalSourceCodec records (plugin 0x00080001, sourceId 0x24db9834): 1,711 serialized paths are event -> action -> sound and one is event -> action -> ordinary HIRC type-5 Random/Sequence Container -> sound. None is owned by HIRC type-13 Music Random Sequence Container, the only native sourceInfo-table construction path found at dispatcher 0x18003a5b0. Therefore that type-13 sourceInfo table cannot be used as a static key mapping for this external-source corpus; the bank sourceId/cookie and native sourceInfo/source-state key remain separate evidence domains.",
            ),
            native_playback_stage(
                "nativeExternalCookieLiteralAbsenceAudit",
                "AkSoundEngine native external-source manager",
                "managed external cookie -> native registration input boundary",
                None,
                "",
                "0x180344988",
                "An exact byte scan of the selected AkSoundEngine.dll finds zero occurrences of the little-endian dword 0x24db9834. The image-initial dword at serial slot 0x180344988 is 0x002f9238 (raw RVA 0x344988), so an unmodified first lock-xadd would generate 0x002f9239, not the HIRC cookie; this is image-initialization evidence only, not a claim about runtime counter state. The native manager constructor therefore receives its callback cookie/context dynamically (entry +0x58), while its exact lookup/registration key is the separately generated serial at entry +0x4c. The serialized sourceId/cookie join is consequently established by managed GameAssembly plus current HIRC data, not by a baked AkSoundEngine literal; runtime argument capture is still required to prove which native input carries the managed cookie and whether any source-state key matches the registration serial.",
            ),
            native_playback_stage(
                "externalFile",
                "AkExternalSourceInfo",
                "set_szFile",
                444128,
                "0x0600015a",
                "0x183abe850",
                "Sets the external audio file path directly from the externalSourceKey argument carried by _PostEventWithExternalSource; the managed key/path and the AkExternalSourceInfo.szFile field therefore share one value before native descriptor copying. This statically closes the direct VoicePlayer key -> external-descriptor path identity. It does not by itself prove a later native source-state key equals the registration serial, a selected sourceInfo instance, an opened handle, or audibility.",
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
                "externalCallbackPackage",
                "AkCallbackManager+EventCallbackPackage",
                "Create",
                446969,
                "0x06000c73",
                "0x18328ca20",
                "Wraps the bridge external callback and the external-playing mapping object; a successful package supplies callback flags 1 to the Wwise post.",
            ),
            native_playback_stage(
                "wwise",
                "AkSoundEngine",
                "PostEvent external-source overload",
                446376,
                "0x06000a22",
                "0x183abed90",
                "Calls PostEvent(eventId, audioObjectId, flags=1, externalCallback, mappingCookie, cExternals=1, externalSourceArray) and crosses dedicated native slot 0x18f361150; ordinary Event posting uses 0x18f361158.",
            ),
            native_playback_stage(
                "nativeSourceManager",
                "AkSoundEngine native external-source manager",
                "external source object construction",
                None,
                "",
                "0x1800e1320",
                "The wrapper 0x1800e12e0 passes the external context pointer/count plus callback, cookie, and flags into the native constructor. The constructor allocates and hash-links a source object, storing its constructor input id at +0x4c, callback at +0x50, cookie at +0x58, flags at +0x60, descriptor/context pointers at +0x28/+0x38/+0x40/+0x48, and chain-next at +0x68. For the shared external descriptor path, nativeSourceDescriptorManagerRetentionAudit below proves that +0x38 is the copied external-descriptor allocation pointer, while +0x40/+0x48 retain its companion fields. Every current constructor callsite reaches +0x4c from the internally generated registration serial written at 0x1800c3990 record +0xc (global lock-xadd result +1, via the 0x1800c3990/related paths), not from a direct managed external-key copy. The maintained runtime probe resolves the exact hash-table entry by +0x4c after constructor return and at join/lookup entry, so shared entry pointers can prove one manager node without claiming a file or PCM join. The later source setup's exact-key join is covered by nativeSourceManagerJoinAudit below; this stage itself proves registration storage and callback metadata, not a live match or file open.",
            ),
            native_playback_stage(
                "nativeSourceDescriptorManagerRetentionAudit",
                "AkSoundEngine native external-source manager",
                "copied external descriptor -> manager entry retention",
                None,
                "",
                "0x1800c38b0",
                "The shared external PostEvent body 0x1800c38b0 calls descriptor copier 0x1800c08d0 when cExternals is nonzero. On success it stores the copied allocation pointer in its local carrier at [rsp+0x50], passes a pointer to that carrier as c3990 stack argument 6, and 0x1800c3990 copies 0x14 bytes from that carrier into registration record +0x14/+0x24. The wrapper 0x1800e12e0 then passes record +0x14 to constructor 0x1800e1320; the constructor loads [record+0x14] into manager entry +0x38, so this path proves manager +0x38 is the copied external-descriptor allocation pointer, with +0x40/+0x48 as its copied companion fields. The same constructor stores the callback at +0x50 and cookie/context at +0x58. This is descriptor ownership/retention, not proof that manager +0x38 is a UTF-16 string, a selected sourceInfo instance, an opened handle, or PCM.",
            ),
            native_playback_stage(
                "nativePostEventCookieFieldSeparationAudit",
                "AkSoundEngine native external-source manager",
                "PostEvent pCookie versus AkExternalSourceInfo external cookie",
                None,
                "",
                "0x1800285d0",
                "The external PostEvent export stub 0x1800285d0 preserves the callback bridge in r9 and copies caller stack arguments pCookie, cExternals, pExternalSources, and the playing-id output into native 0x1800c38b0. Native 0x1800c38b0 passes pCookie to 0x1800c3990 stack argument 5; c3990 forwards it as r9 into wrapper 0x1800e12e0, whose constructor stack argument 6 becomes manager entry +0x58. The external-source descriptor instead travels through 0x1800c08d0 and registration record +0x14 into manager +0x38, where its copied 0x20-byte payload retains AkExternalSourceInfo iExternalSrcCookie/szFile/codec. The separately generated registration serial remains manager +0x4c. Therefore manager +0x58 is the PostEvent callback-mapping cookie, not Wwise externalCookie 0x24db9834; these identities must not be equated.",
            ),
            native_playback_stage(
                "nativeSourceDescriptorManagerLifetimeAudit",
                "AkSoundEngine native external-source manager",
                "manager descriptor retention lifetime and release",
                None,
                "",
                "0x1800e1770",
                "Exact-key detach callers 0x1800e2a5e and 0x1800e2a8e enter teardown 0x1800e1770 after the source-state attachment array is empty. Teardown reads manager entry +0x38 only to pass the retained copied descriptor allocation to refcount release 0x1800c5f60, then clears/unlinks the entry; it does not dereference +0x38 as a path or feed the provider/codec. This bounds +0x38 as an ownership-retention field on the shared external path, not a direct sourceInfo/provider input.",
            ),
            native_playback_stage(
                "nativeSourceRegistrationSerialAudit",
                "AkSoundEngine native external-source manager",
                "constructor wrapper and registration-serial coverage",
                None,
                "",
                "0x1800e1320",
                "An exhaustive direct-call scan of the selected AkSoundEngine .text finds two wrapper families into constructor 0x1800e1320: 0x1800e12e0 -> 0x1800e1320 at 0x1800e130b, and 0x1800e1490 -> 0x1800e1320 at 0x1800e14d2. The first wrapper has direct registration callers 0x1800c3516, 0x1800c3b31, and 0x1800c3e7e; the second has 0x1800c41cc and 0x1800c4472. These callers allocate/prepare the native records and use the c3990/related lock-xadd registration-serial paths before the wrapper passes the record's +8 dword into constructor field +0x4c. This closes constructor-wrapper coverage for the selected binary, but it still does not prove that the later source-state key equals that serial.",
            ),
            native_playback_stage(
                "nativeSourceLookup",
                "AkSoundEngine native external-source manager",
                "external key lookup and callback dispatch",
                None,
                "",
                "0x1800e2820",
                "Uses the requested numeric key only for bucket selection (edx = key % manager bucket count), then walks the +0x68 chain and compares the exact key against object +0x4c; there is no additional hash transform in this body. It copies object +0x58/+0x28 plus the key and +0x24 into a resolver descriptor, then dispatches the stored +0x50 callback through 0x1800e19a0 with operation 0x10. Sibling lookup 0x1800e28d0 performs the analogous flag-0x20 operation. This is the exact native key-to-callback boundary, not a CreateFileW call.",
            ),
            native_playback_stage(
                "nativeSourceCallbackBranches",
                "AkSoundEngine native external-source manager",
                "flag-gated resolver callback descriptor branches",
                None,
                "",
                "0x1800e2820",
                "The exact-key lookup has two flag-gated callback branches. 0x1800e2820 accepts a source object only when object +0x60 bit 0x10 is set, writes a resolver descriptor at the caller output (+0 cookie/context = object +0x58, +8 context = object +0x28, +0x10 requested key, +0x14 object +0x24), and invokes 0x1800e19a0 with operation 0x10. Sibling 0x1800e28d0 requires object +0x60 bit 0x20, builds the stack descriptor (+0x20 cookie, +0x28 context, +0x30 requested key, +0x34 object +0x24), invokes the stored callback directly with operation 0x20, and stores its return in manager +0x48. Generic invoker 0x1800e19a0 prepares the callback lock/state; fixed bridge 0x180002da0 maps op 0x10 to 0x1800030cf's no-op path and op 0x20 to the queued callback record at 0x180003430. This closes descriptor/operation transport only; it does not identify the managed path, opened handle, or PCM consumer.",
            ),
            native_playback_stage(
                "nativeSourceExtendedCallbackBranches",
                "AkSoundEngine native external-source manager",
                "extended exact-key callback branches",
                None,
                "",
                "0x1800e25f0",
                "The same manager table has two additional exact-key branches. 0x1800e25f0 computes key % bucketCount, walks bucket +0x68, requires entry +0x60 bit 0x80, builds the callback descriptor from entry +0x58/+0x28/key/+0x24, invokes entry +0x50 with operation 0x80, stores the return at manager +0x48, and releases the temporary manager state; direct callsites are 0x1800347af, 0x1800356bf, and 0x18003578f. 0x1800e26f0 performs the same exact-key walk, requires bit 0x2000, copies the caller payload (0x20 bytes plus input +0x20), adds key/entry metadata and callback context, then invokes entry +0x50 with operation 0x2000; its direct caller 0x18004388b iterates range-matched slots at object +0x118. The fixed bridge 0x180002da0 maps op 0x80 to the common 0x30-byte queued record and op 0x2000 to the string-or-generic queued record builder at 0x180003169 -> 0x18000302b. These branches prove extended callback transport only; they do not select a UTF-16 path, open a handle, or deliver PCM.",
            ),
            native_playback_stage(
                "nativeResolverCallback",
                "AkSoundEngine native external-source resolver",
                "resolver callback operation dispatch",
                None,
                "",
                "0x1800e19a0",
                "Prepares callback state and invokes the stored resolver callback with the output descriptor and operation length supplied by the source-manager lookup. The non-null PostEvent callback is normalized by export stub 0x1800285d0 to fixed native bridge 0x180002da0 before it is stored at +0x50; this boundary still does not call CreateFileW, ReadFileEx, or the embedded codec reader.",
            ),
            native_playback_stage(
                "nativeSourceMediaLookup",
                "AkSoundEngine native source/media state",
                "external key -> source/media lookup",
                None,
                "",
                "0x18010df60",
                "Receives the source object and stream state, reads the requested numeric key from source-state +0, and calls 0x1800e2820 (or the fallback registry 0x1801398f0). In the voice/render path, 0x1801443e0 loads context +0x268 into a temporary dword at its local +0x10 and passes the address of that slot as stack argument 5 to 0x18018a5a0 (unless its flag branch clears the argument). The 0x18018a5a0 -> 0x1801898c0 path preserves that pointer in r8, and caller 0x180189a59 passes it as rcx to this lookup, so this callsite reads exactly context +0x268 as source-state key +0. The same lookup has separate mixer callers at 0x180189826, 0x180189e18, and 0x18018a2a8. A related voice/render path 0x180188ed0 -> 0x180188fae -> 0x1800e1ed0 uses the same key, requires source flags +0x60 bit 3, and invokes the stored callback with operation 0x8; fixed bridge 0x180002da0 routes that operation to 0x180002f31, which copies a 0x48-byte notification record and queues it through 0x180003430. That is source-state callback transport, not path opening or PCM delivery. The unrelated 0x1801443e0 local integer computed from temporary state/input +0x10 (initialized from build constant 0x200) and context +0x2a4 is not the key passed at 0x189a59. State-object initializer 0x1800d1f90 copies its +0x268 field from config +0x34. One concrete config-producing path at 0x180034e4f fills that +0x34 from an upstream record +0x14 before 0x1800365f0 calls the initializer; the other constructors 0x1800fc9e0 and 0x18018dba0 receive their config pointers through separate callers. The source-setup join is now closed separately: 0x1800350d7 passes the same source key into 0x1800e2cd0, whose bucket walk performs an exact numeric equality comparison directly against manager entry +0x4c (the 0x1800c3990 record +0xc serial); a successful runtime match and the later path/PCM handoff remain unobserved. no direct call-rel32 or field-dataflow edge proves the alternate mixer key slots' runtime matches. The manager lookup fills the output descriptor at the caller's stack +0x40 with object +0x58 (callback cookie/context), object +0x28 (source context), the requested key at +0x10, and object +0x24 at +0x14 before dispatching callback operation 0x10 through 0x1800e19a0. This statically joins source-state key -> callback descriptor metadata, but not the managed UTF-16 path or exact selected media; direct callers still contain no direct CreateFileW, ReadFileEx, or codec call. This is the precise static boundary before the unresolved virtual-I/O join.",
            ),
            native_playback_stage(
                "nativeSourceProviderPrep",
                "AkSoundEngine native source/provider preparation",
                "source metadata -> file/key or memory provider",
                None,
                "",
                "0x1801af7a0",
                "Consumes owner +0x18 source metadata at +0x288. Flags at sourceInfo +0xc select the in-memory branch (owner +0x338/+0x340) or the file/key branch; in the latter, flag bit 9 selects sourceInfo +0x10 as the descriptor path pointer, while sourceInfo +4, +0x1a and flag-derived fields populate the remaining local descriptor. The registered provider path reaches factory 0x1800b5e30, whose constructor 0x1800bb160 installs the primary provider vtable and the decoder-facing secondary interface at allocation +0x90; the returned secondary interface is stored at decoder +0x58 before default-device I/O queueing, and descriptor +0 is copied into provider-owned UTF-16 path storage. The separate 0x1800b9460 -> 0x1800b9530 table seen elsewhere is not this sourceInfo factory path. This closes descriptor/path/provider transport, but not source-state key +0 -> this source metadata instance.",
            ),
            native_playback_stage(
                "nativeSourceProviderDescriptorInputAudit",
                "AkSoundEngine native source/provider preparation",
                "sourceInfo path field -> provider descriptor input",
                None,
                "",
                "0x1801af7a0",
                "The exact source-preparation body loads owner +0x18 into r11 and sourceInfo from [r11 + 0x288]. In the file/key branch it initializes the local descriptor pointer from owner +0x338, then when sourceInfo flags select bit 9 it overwrites that pointer with [sourceInfo +0x10]; the remaining descriptor fields come from sourceInfo +4, +0x1a, and flag-derived locals. It passes the address of this local descriptor to the singleton provider vtable +0x28, which reaches 0x1800b5e30 and then 0x1800b9530; provider setup copies descriptor +0 into provider-owned UTF-16 storage. The call boundary carries no explicit manager entry, +0x38, or source-state key value, so this proves sourceInfo/provider input provenance while leaving identity with the copied external descriptor unresolved.",
            ),
            native_playback_stage(
                "nativeSourceKeyCallsites",
                "AkSoundEngine native source/media state",
                "source-state key pointer callsites",
                None,
                "",
                "0x18018a5a0",
                "The shared source-state preparation helper consumes stack argument 5 as a pointer to a numeric key slot, preserves it as r8 into 0x1801898c0, and the 0x180189a59 lookup path passes that pointer to 0x18010df60, which reads the dword at pointer +0. Voice/render caller 0x1801451ea copies [r12+0x268] into local [rbp+0x190] and passes its address; caller 0x180144c1f instead passes r12+0x18 when r12+8 bit 4 is set, otherwise null; mixer/alternate caller 0x18017da06 passes a local zero slot only under its context flag. Thus the exact voice key source is [r12+0x268], while other branches can supply a distinct state field or no key; none is statically proven equal to manager serial +0x4c.",
            ),
            native_playback_stage(
                "nativeSourceKeyWriteAudit",
                "AkSoundEngine native source/media state",
                "source-state +0x268 write audit",
                None,
                "",
                "0x1800d2055",
                "A complete direct-offset/overlap audit of the selected AkSoundEngine .text finds one source-state +0x268 writer: 0x1800d2055 copies config +0x34 into the source-state object. Exact-offset stores at 0x18008668c and 0x1800ac3bf copy larger structures, 0x1800ae238 bulk-clears an e38-sized container, and 0x18012d0fe initializes a separate 0x310-byte object; overlapping 16-byte zero stores at 0x18022ad9c, 0x18022b3f5, and 0x18022b83a begin at +0x264 inside separately allocated 0x320-byte auxiliary objects. All remaining +0x268 hits are stack locals or atomic refcount-like fields. The serial storage resolves to global 0x180344988; its only RIP-relative references are lock-xadd writers at 0x1800c3414, 0x1800c3af2, 0x1800c3e48, 0x1800c418e, and 0x1800c443d, with no direct RIP-relative read at the source-state constructors. No source-state setter copies the serial; the separate 0x1800350d7 -> 0x1800e2cd0 join now proves the key is compared against manager +0x4c, while successful runtime matching remains unobserved.",
            ),
            native_playback_stage(
                "nativeSourceKeyConfigCallsiteAudit",
                "AkSoundEngine native source/media state",
                "config +0x34 producer and source-state key callsite coverage",
                None,
                "",
                "0x180034db0",
                "A byte-level direct-call scan of the selected AkSoundEngine .text finds one direct callsite, 0x18003def1 -> 0x180034db0. The caller passes the callee's stack argument 6 from the record returned by 0x180040350; that accessor returns nested [object +0x10] -> [+0x68] +0x18. Because the returned record is parent B +0x18, callee 0x180034e4f reads parent B +0x2c into config +0x34. Sibling accessor 0x1800404f0 reads the same B +0x2c directly; callsites 0x18003e35b and 0x18003e486 pass that value into source vtable +0x138, proving field reuse in native source/state operations. Source-state construction 0x1800365f0 and initializer 0x1800d1f90 later copy config +0x34 into source-state +0x268. A separate child-source branch 0x180034640 -> 0x180037740 preserves one source record: constructor write 0x18003779e copies record +0x14 to child source +0x2c, and 0x180034733 passes that same record field to 0x1800e2cd0 as the exact-key lookup value. This proves local same-record value identity before the manager comparison, but parent B/source record is not statically aliased to the 0x1800c3990 external-registration record and its +0xc serial; registration provenance and runtime match remain unproven.",
            ),
            native_playback_stage(
                "nativeSourceStateMetadataProvenanceAudit",
                "AkSoundEngine native source/media state",
                "source-state +0x288 metadata provenance",
                None,
                "",
                "0x1800d1f90",
                "Initializer 0x1800d1f90 has a stable three-pointer ABI in the selected build: rcx is the destination source-state object, rdx is the source config, and r9 is the sourceInfo metadata pointer. It copies config +0x34 directly to source-state +0x268 and r9 directly to source-state +0x288; the same call also preserves sourceInfo-derived fields for later selection. The primary voice construction chain reaches it at return address 0x180036622: 0x180034db0 places its incoming r8 in stack argument +0x20, 0x1800365f0 reloads that value as initializer r9, and the sole direct caller 0x18003def1 supplies the original r8 from the record returned by 0x180046580. That selector walks its own +0xe0 table and returns the matched record's +8 pointer. Alternate callsite 0x1800fca27 (function 0x1800fc9e0, return address 0x1800fca2c) remaps its incoming r9 to initializer rdx/config and incoming r8 to initializer r9/sourceInfo; callsite 0x18018dbc5 (function 0x18018dba0, return address 0x18018dbca) forwards incoming rdx/r9 directly as config/sourceInfo. These are three distinct register-source families, not one proven external-source path. The external-source manager constructor 0x1800e1320 instead stores its own incoming r9 at manager entry +0x38, and no direct call or field-dataflow edge in the selected AkSoundEngine joins that allocation to the 0x180046580 record or source-state +0x288. The runtime manifest now samples initializer object/key/pointer fields and return addresses for bounded joins with provider and decoder owners; sourceInfo identity, runtime key matching, path selection, and PCM delivery remain unobserved.",
            ),
            native_playback_stage(
                "nativeSourceInfoInternalSelectionAudit",
                "AkSoundEngine native source/media state",
                "sourceInfo key/mode -> internal source selection registry",
                None,
                "",
                "0x1800d2ed0",
                "Source-state helper 0x1800d2ed0 dereferences source-state +0x288, then passes sourceInfo dword +0 and mode ((sourceInfo +0xc >> 2) & 0x1f) to 0x1800f5030 through global slot 0x180344a20. That selector walks its own table at +0x88 using bucket count +0x90 and compares entry +8 exactly against sourceInfo +0 before choosing an available candidate. The helper 0x1800f9780 then materializes a 0x20-byte local descriptor: +0 is the matched table entry, +8 is the type-2 candidate context (otherwise null), +0x10 is candidate +8, and +0x18 is candidate +0x10. The caller checks descriptor +0x10/+0x18 against source +0x328 +0x18, passes the candidate through 0x180143de0, then applies sourceInfo to source +0x328 through 0x180104720 before copying the descriptor into the source object. Slot 0x180344a20 is distinct from the external-source manager hash slot 0x1803449f8 and the key-to-decoder registry slot 0x1803449d0. This bounds sourceInfo +0 as an internal selection key that feeds provider/source setup; it is not statically shown to be the external manager serial +0x4c, and runtime values, path/handle choice, and PCM delivery remain unobserved.",
            ),
            native_playback_stage(
                "nativeSourceInfoDescriptorContinuityAudit",
                "AkSoundEngine native source/media state",
                "selector descriptor -> source-owner +0x338 continuity",
                None,
                "",
                "0x1800d2f99",
                "The sourceInfo consumer success branch receives selector output at local +0x30: helper 0x1800f9780 writes candidate +8 to local +0x40 and candidate +0x10 to local +0x48, then 0x180104720 applies sourceInfo metadata before the consumer copies the complete 0x20-byte descriptor from local +0x30 into source object +0x328. Therefore selector output +0x10 is copied exactly to source +0x338 and output +0x18 to source +0x340; the failure branch applies a zero descriptor. The runtime manifest samples selector output +0x10 and source +0x338 after the consumer, then repeats owner +0x18 -> +0x338 in provider preparation, exposing bounded pointer intersections without claiming a file, handle, or PCM join.",
            ),
            native_playback_stage(
                "nativeSourceInfoPathWriterAudit",
                "AkSoundEngine native source/media state",
                "sourceInfo +0x10 UTF-16 path writer and metadata-link provenance",
                None,
                "",
                "0x180104630",
                "The selected build has one direct caller of 0x180104630 at 0x1800e037e. Setter 0x180104630 copies the incoming UTF-16 pointer r8 into source record +0x10 after replacing the 16-byte identity block at +0 and sets the source mode at +0x18; its sibling 0x1801044f0 performs the same path role by measuring r9 with 0x18026b7f8, allocating UTF-16 storage, and copying the characters through 0x180263808 before storing the owned pointer at +0x10 and setting the owned-string flag. Caller 0x1800e037e walks the source-metadata records at r13 +0x20, matches the current source key [r12+4] against record +0, and takes either the direct-path branch (record +8 -> 0x1801044f0) or the alias branch when record +0x18 is nonzero and record +0x10 is present (record +0x10 -> r8 -> 0x180104630). This closes the native writer and UTF-16 storage provenance for sourceInfo +0x10; the separate sourceInfo consumer audit closes selector-descriptor copying into source +0x338/+0x340 and the exact copied-descriptor identity. No manager entry +0x38, managed external key, or source-state key appears in either writer boundary, and runtime values remain unobserved.",
            ),
            native_playback_stage(
                "nativeSourceInfoHircOwnerAudit",
                "Wwise HIRC Music Random Sequence Container",
                "HIRC type byte -> sourceInfo-table parser",
                None,
                "",
                "0x18003a5b0",
                "The selected AkSoundEngine bank-object dispatcher at 0x18003a5b0 reads the serialized HIRC type byte: 10 -> 0x180039e80, 11 -> 0x18003a190, 12 -> 0x180039b70, and 13 -> 0x1800397b0. The only direct calls into sourceInfo-table parser 0x180047120 are 0x180039a28 inside the type-13 parser and 0x180039b35 inside helper 0x180039af0, whose only callers are 0x1800398e7/0x180039a54 in that same type-13 path. The type-12 branch has no direct 0x180047120 call in the selected .text. This attributes the table-construction call path to the maintained HIRC Music Random Sequence Container family, and positively separates it from the direct AkBankSourceData external-source parser; the later source/provider consumers still require a separate runtime/source-state join.",
            ),
            native_playback_stage(
                "nativeSourceInfoSerializedParserAudit",
                "AkSoundEngine serialized sourceInfo-table parser",
                "serialized cursor -> sourceInfo map key/identity",
                None,
                "",
                "0x1800f5fc0",
                "The only direct callers of sourceInfo-table parser 0x180047120 are 0x180039a28 and 0x180039b35; the parser itself gates the owning object on virtual type value 6, then consumes an internal serialized cursor. Parser 0x1800f5fc0 writes output +4 from the first cursor dword, output +8 and +0xc from the second dword, output +0x10 from the third dword, and derives output +0x14 flags; the caller passes output +8 as the map key (edx), output +4 as the mode (r8d), and copies output +8..+0x17 as the 16-byte identity block into 0x180045fd0/0x180045f30 records. This closes sourceInfo-table key/identity provenance to the owning object's serialized payload, distinct from Wwise External Source sourceId/cookie 0x24db9834 and the native manager registration serial +0x4c. No manager table, managed externalSourceKey, or source-state key is read at this parser/map-insertion boundary, so the exact sourceInfo instance selected for external playback remains unresolved.",
            ),
            native_playback_stage(
                "nativeSourceManagerJoinAudit",
                "AkSoundEngine native external-source manager",
                "source key -> manager serial exact-compare join",
                None,
                "",
                "0x1800e2cd0",
                "The post-construction source setup at 0x1800350d7 passes edx = [r13 + 0x14], the same parent B +0x2c that feeds config +0x34 and source-state +0x268, into 0x1800e2cd0. That helper uses the manager table supplied in rcx (loaded from the native global handle slot at 0x1803449f8), computes key % bucketCount from manager +0x8, walks the bucket +0x68 chain, and compares entry +0x4c directly against edx with no hash transform. On a match it stores the source-state pointer and updates the manager entry's auxiliary state; the sibling setup callsite 0x180034762 follows the same helper. This closes the static source-key -> manager-entry +0x4c comparison path, while a successful runtime match, the manager instance's registration provenance at that invocation, and the later UTF-16 path/PCM handoff remain unobserved.",
            ),
            native_playback_stage(
                "nativeSourceManagerJoinCallsiteAudit",
                "AkSoundEngine native external-source manager",
                "exact direct-call census for source-key manager joins",
                None,
                "",
                "0x1800e2cd0",
                "An exhaustive direct-call scan of the selected AkSoundEngine .text finds four valid callsites to exact-key join helper 0x1800e2cd0: 0x180034762 and 0x1800350d7 in the primary source/voice construction paths, plus 0x1800d35a8 and 0x1800e06ea in broader manager state transitions. The first passes edx = [r14 + 0x14], r8 = rbx + 0x18 (or null), and r9 = r15; the second passes edx = [r13 + 0x14], r8 = [rsi], and r9 = r14; the latter two pass edx = [rdi + 0x250], r8 = [rdi - 0x18], r9 = [rdi + 8], or edx = [r13 + 0x34], r8 = r14, r9 = [r14 + 0x20], respectively. This expands join coverage beyond the primary source setup, but only the two 0x034xxx callsites carry the parent-B/source-state key explanation; the broader callers do not by themselves prove external-source media selection, path opening, or PCM delivery.",
            ),
            native_playback_stage(
                "nativeSourceManagerJoinPayloadBoundaryAudit",
                "AkSoundEngine native external-source manager",
                "exact-key join payload and attachment boundary",
                None,
                "",
                "0x1800e2cd0",
                "The exact 0x1800e2cd0 body proves that a key hit is an attachment operation, not path selection: after the +0x4c equality check it appends the supplied source-state pointer r8 to the manager entry dynamic array at +0x10, updates live count/capacity at +0x18/+0x1c, and, when absent, retains the auxiliary state pointer r9 at +0x30 while updating its reference/status fields. The join body does not read manager entry +0x38/+0x40, the constructor's descriptor-derived refcount/context companions, or the copied UTF-16 record at +0x10; those fields are consumed by separate callback/cleanup paths. Therefore the e2cd0 result closes source-state lifecycle registration only. The source-state key still needs a runtime-equal manager entry before the separate provider path can be joined to the managed UTF-16 path, file handle, or PCM consumer.",
            ),
            native_playback_stage(
                "nativeSourceRegistrationKeyIndependenceAudit",
                "AkSoundEngine native external-source manager",
                "registration serial versus source-state key provenance",
                None,
                "",
                "0x1800c3990",
                "The selected-binary registration families generate manager-entry keys internally: 0x1800c3af2 lock-xadds global serial slot 0x180344988, stores serial+1 in record +0xc, and passes record +4 to wrapper 0x1800e12e0; the sibling family at 0x1800c3414/0x1800c3516 and the 0x1800e1490 callers at 0x1800c3e48/0x1800c443d use the same lock-xadd pattern before constructor storage at manager entry +0x4c. The primary source joins instead load edx = [r14 + 0x14] at 0x180034762 or edx = [r13 + 0x14] at 0x1800350d7, i.e. parent-B/source-state data, and the complete +0x268 writer audit finds no store sourced from the serial global. Therefore the exact-key comparison is proven, but key equality remains a runtime value question rather than a statically copied serial; path/handle selection and PCM delivery remain unobserved.",
            ),
            native_playback_stage(
                "nativeSourceStateAttachmentLifecycle",
                "AkSoundEngine native external-source manager",
                "source-state attachment detach and cleanup",
                None,
                "",
                "0x1800e29d0",
                "The source-state pointer stored by 0x1800e2cd0 is retained in the matched manager entry's dynamic array at +0x10, with live count at +0x18 and capacity at +0x1c. Detach helper 0x1800e29d0 repeats the exact key bucket walk, scans that array for the supplied source-state pointer, removes it with a memmove and decrements +0x18, then calls 0x1800e1770; if no attached states remain, that path unlinks the entry, releases its +0x30 auxiliary state and +0x50 callback, and frees the record. Manager reset 0x1800e2e20 similarly clears every entry array (+0x10/+0x18/+0x1c) before releasing the hash table. These consumers only manage attachment lifetime; they do not read a path, issue file I/O, or feed the codec, so the e2cd0 hit remains a state-registration join rather than a media-selection edge.",
            ),
            native_playback_stage(
                "nativeSourceKeyDecoderRegistry",
                "AkSoundEngine source/provider decoder registry",
                "source-state key -> active decoder association",
                None,
                "",
                "0x18013f440",
                "After source/provider preparation, 0x1801b0160 reads decoder +0x18 owner and passes owner +0x268 as the key, the decoder pointer as r8, and a status record as r9 to registry helper 0x18013f440. The registry object is supplied through global slot 0x1803449d0, distinct from the source-manager hash slot 0x1803449f8 used by 0x1800e2cd0. Its +0x10 dynamic table uses 0x18-byte records keyed by dword +0, stores the decoder pointer at +8, and updates status fields at +0x10/+0x14; helper 0x18013f440 exact-searches the key, updates an existing decoder record or grows/inserts a new one. Direct callers include 0x1801afab5 (provider/decoder preparation) and codec-side refreshes 0x1801c4932, 0x1801c4978, 0x1801c56f0, and 0x1801c570d. Teardown caller 0x180189041 reaches 0x18013f290 to remove a key+decoder pair. This statically joins the source-state key to an active decoder lifetime, not to the UTF-16 path value, ReadFileEx request, or PCM buffer.",
            ),
            native_playback_stage(
                "nativeCallbackBridge",
                "AkSoundEngine native callback bridge",
                "external-source callback operation switch",
                None,
                "",
                "0x180002da0",
                "The PostEvent export stub 0x1800285d0 replaces a non-null managed callback with this fixed native bridge. Operation 0x10 takes the default no-op branch at 0x1800030cf; operation 0x20 packages the resolver descriptor (cookie/context/key/aux) into a 0x30-byte callback record and enqueues it through 0x180003430. Voice/render source path 0x180188ed0 -> 0x180188fae -> 0x1800e1ed0 invokes the same stored callback with operation 0x8; the bridge routes it to 0x180002f31, copies a 0x48-byte record, and queues it through 0x180003430. These branches establish callback transport, not file opening or PCM delivery.",
            ),
            native_playback_stage(
                "nativeCallbackPump",
                "AkCallbackManager",
                "PostCallbacks",
                446952,
                "0x06000c62",
                "0x18328b440",
                "Resolves CSharp_b1b6b5807eef294 to native export 0x18002ea80 -> 0x180002d10, detaches the global native callback list, then reads each record cookie/type/info through CSharp_e6dab33ded3a701 (0x18002e310), CSharp_bd21aa4a6b071193c (0x18002e320), and CSharp_c5c6cb50efed2 (0x18002e330). Each record enters _ProcessEventCallback 0x18328cd90 and the registered managed callback package delegate. For source-manager operation 0x20 this proves callback transport and managed dispatch, not file opening.",
            ),
            native_playback_stage(
                "callback",
                "Beyond.Audio.AudioAdapter",
                "_OnExternalSourceEventCallback",
                480009,
                "0x0600005e",
                "0x1843c7930",
                "Receives the callback package after native queue transport and managed callback dispatch; raw callback type 1 removes the external mapping and starts cleanup. It is not a direct file-open implementation.",
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
            "Event media. The native source-manager object, exact-key bucket lookup, and resolver callback dispatch are now also exact: "
            "object +0x4c is compared through the +0x68 hash chain, +0x50 is invoked with operation 0x10 (or 0x20 in the sibling path), "
            "and +0x58/+0x28 plus key metadata form the callback descriptor. The PostEvent export stub's fixed bridge is exact: operation "
            "0x10 is a native no-op, while operation 0x20 queues a descriptor record. AkCallbackManager.PostCallbacks at 0x18328b440 "
            "detaches that queue through 0x180002d10, decodes cookie/type/info with the three native getters, and dispatches through "
            "_ProcessEventCallback at 0x18328cd90 into the registered managed delegate. Wwise's separate default I/O device and ReadFileEx "
            "batch reader are exact in the stream-manager chain, but the external key/context is not statically joined to an opened file "
            "handle or read request. The callback-to-codec join, live returned playing id, and decoded external-file content remain unobserved."
        ),
    },
    "vfsPackageLoad": {
        "id": "vfsBasePathToWwisePackage",
        "label": "VFS base path -> selected PCK -> Wwise LoadFilePackage",
        "evidence": "exactCurrentGameAssemblyDirectCallsAndManagedPathBridge",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeCallChainNotLivePackageTrace",
        "stages": (
            native_playback_stage(
                "vfsBasePath",
                "Beyond.VFS.VirtualFileSystem",
                "GetAkSoundEngineVFSBasePath",
                295909,
                "0x06000d80",
                "0x184653ea0",
                "Returns the VFS-derived base path consumed by audio initialization.",
            ),
            native_playback_stage(
                "initBasePaths",
                "Beyond.Audio.AudioVFSLoader",
                "InitBasePaths",
                480253,
                "0x06000152",
                "0x1846536a0",
                "Obtains the VFS base path and initializes path-related loader state.",
            ),
            native_playback_stage(
                "pckDispatch",
                "Beyond.Audio.AudioVFSLoader",
                "_DoLoadPcksFromVfs",
                480258,
                "0x06000157",
                "0x183eb5100",
                "Iterates selected VFS PCK records and dispatches single-package loads.",
            ),
            native_playback_stage(
                "singlePck",
                "Beyond.Audio.AudioVFSLoader",
                "_DoLoadSinglePckFromVfs",
                480259,
                "0x06000158",
                "0x183eb5a20",
                "Resolves the VFS record/path and creates the package load record.",
            ),
            native_playback_stage(
                "wwisePackage",
                "AkSoundEngine",
                "LoadFilePackage",
                446704,
                "0x06000b6a",
                "0x183eb5cd0",
                "Converts the managed package path to a native string and crosses the Wwise package bridge.",
            ),
        ),
        "branches": (
            {
                "id": "initLanguageHotfix",
                "label": "Init/language/hotfix PCKs",
                "relation": (
                    "TryLoadInitPck (480249), TryLoadLanguagePck (480251), and "
                    "_DoLoadLanguageAndHotfixPck (480252) feed the same VFS package loop."
                ),
            },
            {
                "id": "extraPck",
                "label": "Extra PCK path",
                "relation": (
                    "LoadExtraPckFromPath (480262, 0x18635f304) calls AddBasePath "
                    "(446705, 0x184653e10) before LoadFilePackage."
                ),
            },
            {
                "id": "debugPck",
                "label": "Debug bank path",
                "relation": (
                    "AudioBankManager debug add/load helpers call SetBasePath "
                    "(446702, 0x1853d8d08) and then LoadFilePackage."
                ),
            },
        ),
        "boundary": (
            "The managed VFS-to-Wwise package path is exact, but these wrappers only pass a native path into Wwise. "
            "The native file read, bank parsing, and external-source callback-to-file-open path remain unobserved."
        ),
    },
    "streamManagerIoPump": {
        "id": "streamManagerIoPump",
        "label": "AkSoundEngine.PerformStreamMgrIO -> registered native I/O-device vtable",
        "evidence": "exactCurrentGameAssemblyToAkSoundEngineExportAndNativeVtableLoop",
        "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
        "runtimeObservationStatus": "staticNativeIoDeviceDispatchNotLive",
        "stages": (
            native_playback_stage(
                "managedBridge",
                "AkSoundEngine",
                "PerformStreamMgrIO",
                446743,
                "0x06000b91",
                "0x1853d36c8",
                "Lazily resolves the obfuscated native export hash e0f7cfc07dcaa207637ad91773d6 and jumps through the generated bridge.",
            ),
            native_playback_stage(
                "nativeExport",
                "AkSoundEngine native export",
                "CSharp_e0f7cfc07dcaa207637ad91773d6",
                446743,
                "0x06000b91",
                "0x180033d20",
                "The installed AkSoundEngine export stub jumps to native stream-manager dispatch at 0x180007900.",
            ),
            native_playback_stage(
                "nativePump",
                "AkSoundEngine native stream manager",
                "registered I/O-device pump",
                None,
                "",
                "0x1800b6b80",
                "Checks initialization, iterates the global registered stream-device pointer array, and invokes each device object's vtable slot +0x8 (implementation 0x1800bc1e0). Native Init export CSharp_d857bb8298429c59 (0x180006310) reaches setup 0x180023f90 -> 0x1800b5fc0, which allocates a 0x468-byte object, constructor 0x1800bb1b0 installs vtable 0x180292fc8, virtual +0x20 initializer 0x1800bc0b0 succeeds, and stores it in array 0x180344900/count 0x180344908; the pump itself dispatches the device and does not directly call a Windows file API.",
            ),
            native_playback_stage(
                "sourceManager",
                "AkSoundEngine stream source manager",
                "source metadata -> decoder provider",
                None,
                "",
                "0x1801af7a0",
                "Codec source preparation 0x1801b03b8 calls 0x1801af7a0, which selects the branch from owner metadata at +0x288 and obtains singleton 0x1803448f0. Its vtable +0x20 allocates a memory provider (vtable 0x180292ec0), while +0x28 allocates one 0x110-byte file/key provider object through 0x1800b5e30. Constructor 0x1800bb160 installs the primary vtable 0x1802932e8 at the base and a decoder-facing secondary point 0x180293260 at base +0x90; the source manager returns that secondary point at decoder +0x58. Both interfaces therefore belong to one provider allocation: the codec uses the secondary +0x78/+0x80 queue methods, while the registered-device pump uses the primary +0x20 method and request context. The in-memory branch copies owner +0x338/+0x340 into decoder +0x60/+0x68 and enters codec +0x120/+0x130; the provider branch is the codec's source abstraction, not the Windows file handle itself.",
            ),
            native_playback_stage(
                "sourceDescriptor",
                "AkSoundEngine file/key source descriptor",
                "descriptor UTF-16 path -> provider-owned storage",
                None,
                "",
                "0x1800b5e30",
                "The file/key branch of 0x1801af7a0 builds a local source descriptor from owner metadata +0x288/+0x10 when its flag branch selects an external path, then passes the UTF-16 path pointer into singleton vtable +0x28 at factory 0x1800b5e30. That factory allocates the provider through constructor 0x1800bb160, which installs primary vtable 0x1802932e8 at the allocation base and secondary decoder-facing vtable 0x180293260 at base +0x90; the returned secondary interface is written to decoder +0x58. The provider constructor copies descriptor +0 as provider-owned UTF-16 storage and preserves descriptor +0xc..+0x2b source metadata. The separate 0x1800b9460 -> 0x1800b9530 table is a different provider-callback/batch-wrapper path, not this sourceInfo factory. This is an exact descriptor-to-provider allocation join; it does not yet identify which external key/context supplied that descriptor.",
            ),
            native_playback_stage(
                "sourceProviderQueue",
                "AkSoundEngine external/file source provider",
                "provider GetBuffer -> registered device request",
                None,
                "",
                "0x1800b85c0",
                "The file/key provider's decoder-facing secondary vtable +0x78 enters 0x1800b85c0, consumes queued blocks through 0x1800b89b0, and when empty uses bound device +0x38 0x1800b8120; setup 0x1800b5d70 and 0x1800b7a40 bind the primary provider base into those queues. It releases consumed nodes through secondary +0x80 (0x1800b9a00), a release/advance-like operation. Source preparation 0x1801af960 passes that provider buffer/size into decoder address point 0x18029cde8 +0x130 (0x1801afc80), and stores the buffer at decoder +0x60, with refill/reset using decoder +0x120/+0x80. The pump's primary-provider request stores that same base object at request +0x48; completion 0x1800bf190 therefore receives the provider base that owns the codec-facing secondary point, recycles its request, and walks associated nodes through virtual +0x30. This closes fixed read completion to the provider allocation/queue, while the codec stream callback remains an indirect call.",
            ),
            native_playback_stage(
                "requestAssembly",
                "AkSoundEngine stream-manager request assembly",
                "provider chunk -> 0x18-byte default-I/O descriptor",
                None,
                "",
                "0x1800bc1e0",
                "The registered-device method 0x1800bc1e0 selects each source provider through 0x1800ba0e0, calls primary provider +0x20 at 0x1800bc369 with descriptor/candidate/flag output slots, and assembles 0x18-byte descriptors before dispatching 0x1800bc4a5. The primary provider base is the base of the dual-interface object constructed by 0x1800bb160; its +0x20 implementation is 0x1800bc660, which may create a chunk/request through 0x1800bb970 -> 0x1800bb8e0. The decoder-facing secondary point is base +0x90 at vtable 0x180293260, whose +0x20 = 0x1800b8820 is serializer-only and does not write the candidate context or flag. For the ordinary branch, the pump forms descriptor +0x10 as the address of candidate +0x8, where candidate is the request returned through bb970/bb8e0. The resulting carrier view is exact: carrier +0 = request +0x8, +8 = request +0x10, +0x10 = request +0x18 buffer/source, +0x18 = request +0x20 static callback 0x1800bf190, +0x20 = request +0x28 self, and +0x28 = request +0x30 ring helper. The request constructor retains the primary provider base at request +0x48, so the fixed completion callback's provider identity is the same allocation as the codec-facing secondary +0x90 point. The state-2 helper 0x1800b97e0 remains a separate default-I/O filter/deferred callback path; branch-dependent provenance remains for its carrier. Init 0x180001060 installs active address point 0x18028c020 at stream-manager +0x428; its +0x28/+0x30/+0x38 slots resolve to 0x180005430, 0x180024270 (ReadFileEx), and 0x1800243e0 (WriteFileEx). The provider-filter callback 0x1800b92c0 -> 0x1800b8b00 is a queue/state transition, not the codec callback. This closes ordinary provider -> carrier -> ReadFileEx -> fixed request callback transport and joins the fixed callback to the codec provider allocation; the indirect codec stream callback target for other descriptors remains open, while the selected decoder output's 0x1801c4650 -> 0x1801c7ec0 -> 0x1801c481a/0x1801c483c path closes the float-to-signed-PCM16 handoff.",
            ),
            native_playback_stage(
                "requestObject",
                "AkSoundEngine asynchronous request object",
                "free-list request -> caller-owned completion callback",
                None,
                "",
                "0x1800bb8e0",
                "Request constructor 0x1800bb8e0 takes an object from the stream-manager free list at +0x458 (decrementing +0x448), derives request +0x8 from the queue/chunk context at input +0x28 and caller offset, copies stack arguments into request +0x10/+0x14, stores caller-supplied r8 at request +0x18 as the buffer/source pointer, installs static callback 0x1800bf190 at +0x20, self at +0x28, clears +0x30, and retains the primary provider base at +0x48. The pump passes candidate +0x8 as the direct-read carrier, so ReadFileEx carrier +0x18 aliases request +0x20 and is exactly 0x1800bf190; carrier +0x10 aliases request +0x18, carrier +8 aliases request +0x10, and carrier +0x28 aliases request +0x30. Callers 0x1800bbad3 and 0x1800bca20 supply branch-specific source/offset inputs to this segment allocator; the first chunk record also exposes position/source-base/length fields to its indexer, while the second caller supplies [object +0xa0] + current offset. Because the primary base carries the decoder-facing secondary interface at base +0x90, completion 0x1800245b0 -> 0x1800bf190 is tied to the same provider allocation that supplies the codec queue, even though it does not directly call the codec's indirect stream callback.",
            ),
            native_playback_stage(
                "providerDispatchBoundary",
                "AkSoundEngine default-I/O provider dispatch",
                "provider descriptor -> virtual device dispatch -> ReadFileEx ABI",
                None,
                "",
                "0x180005430",
                "The alternate provider-batch wrapper 0x180005430 filters provider pointers through vtable +0x38 (0x180005870), then calls 0x180024200 (+0x58 on the primary address point). Its accepted 0x70-byte state record is allocated by 0x1800b9530, with callback 0x1800b92c0 at record +0x18 and owner at +0x20; this resolves to queue/state transition 0x1800b92c0 -> 0x1800b8b00, not the codec callback. The active address point 0x18028c020 exposes +0x28=0x180005430, +0x30=0x180024270 ReadFileEx, and +0x38=0x1800243e0 WriteFileEx. ReadFileEx consumes 0x18-byte descriptors; descriptor +0 is provider (+0x10 supplies HANDLE) and descriptor +0x10 is the ordinary carrier at request +0x8. For request base R, carrier +0=R+8, +8=R+0x10 byte count, +0x10=R+0x18 buffer/source, +0x18=R+0x20 fixed callback 0x1800bf190, +0x20=R+0x28 self, and +0x28=R+0x30 ring helper. Completion 0x1800245b0 loads this carrier from ring slot +0x18 and tail-jumps carrier +0x18; because request +0x48 is the primary base whose secondary +0x90 is the codec provider interface, this closes the active pump -> ReadFileEx -> fixed request cleanup/release path to the codec provider allocation. It still does not resolve the generic stream-object +0 callback for other codec descriptors or the selected decoder's optional callback target.",
            ),
            native_playback_stage(
                "nativeFileIo",
                "AkSoundEngine default Wwise file-I/O object",
                "open/path/queued batch-read interface",
                None,
                "",
                "0x180005030",
                "The `%u.bnk`/`%u.wem` interface table at 0x18028bfa0 points to path normalization 0x180005150, directory check 0x180005180, and open/size helper 0x180005030 (CreateFileW + GetFileSize). The composite object initialized at 0x180001060 retains active address point 0x18028c020 at stream-manager +0x428 (primary +0x60 also exposes 0x180024270); its +0x28/+0x30/+0x38 slots resolve to 0x180005430 (provider filter/state dispatch), 0x180024270 (ReadFileEx batch read), and 0x1800243e0 (WriteFileEx batch write). The pump method 0x1800bc1e0 selects the active address point; the ordinary provider +0x20 implementation is 0x1800bc660 with nested 0x1800bb970 -> 0x1800bb8e0 assembly, distinct from serializer 0x1800b8820. The batch reader consumes descriptor +0x10 as request +0x8; for request base R, carrier +0x10 is R+0x18 buffer/source, carrier +8 is R+0x10 byte count, carrier +0 is R+8 transfer scalar, carrier +0x18 is R+0x20 fixed callback 0x1800bf190, and carrier +0x28 is R+0x30 ring helper. Request +0x48 retains the primary provider base, whose secondary +0x90 is returned to the decoder, so the read completion and codec queue share one allocation. This closes the pump-to-ReadFileEx dispatch, active transport, and read-completion-to-provider-allocation callback; the selected decoder output's 0x1801c4650 -> 0x1801c7ec0 -> 0x1801c481a/0x1801c483c path also closes float-to-signed-PCM16 handoff. The generic stream-object +0 callback for other codec descriptors and the optional decoder callback remain unresolved.",
            ),
            native_playback_stage(
                "nativeFileOpenPathTransportAudit",
                "AkSoundEngine default Wwise file-I/O object",
                "provider request descriptor -> normalized path -> CreateFileW",
                None,
                "",
                "0x180024630",
                "The concrete open wrapper 0x180024630 receives the registered-device descriptor, obtains its provider-side path/context through the object's vtable, and calls 0x180004a20 with the descriptor and returned path pointer. 0x180004a20 validates the descriptor state, calls 0x180004b40, and then dispatches the default file-I/O vtable slot 0 at 0x18028bfa0 to 0x180005030, whose CreateFileW/GetFileSize pair stores the handle/size result. 0x180004b40 selects the incoming path pointer or the file-I/O object's base path, normalizes it through vtable slot +0x8 at 0x180005150, and feeds that normalized path into the open object. This closes the provider-request-to-native-open ABI, while no external key, source-state key, or manager +0x38 value appears in this open boundary.",
            ),
            native_playback_stage(
                "nativeFileOpenArgumentFlowAudit",
                "AkSoundEngine default Wwise file-I/O object",
                "open wrapper register/stack argument flow",
                None,
                "",
                "0x180024630",
                "Capstone decoding of the selected build's concrete open wrapper closes the ABI at register level: rcx is the registered-device/file-I/O object, rdx is the original descriptor/path argument, and r8 is the caller output slot. The wrapper clears the lookup key before calling object vtable +0x10, stores the returned provider context through the output slot, then calls 0x180004a20 with object +0x10, the original rdx, flag r8b=1, and that provider context in r9. 0x180004a20 forwards the descriptor/path state to 0x180004b40, whose normalized UTF-16 result reaches default file-I/O slot 0 at 0x180005030; that routine receives path, access mode, and async flag and writes the native handle/size result. No manager entry +0x38, external key, source-state key, or codec pointer occurs in these argument registers or local path-normalization frames, so this is an exact open ABI boundary rather than an identity join.",
            ),
            native_playback_stage(
                "nativeIoVtablePointerCensus",
                "AkSoundEngine native I/O vtable tables",
                "exact .rdata function-pointer census",
                None,
                "",
                "0x18028f2f8",
                "An exact pointer scan of the selected AkSoundEngine.dll (SHA-256 b33c3c71e44c305fb1c3903942308f2ab55a7854d68c719fe55e7de323e7dba2) finds the registered-device table at 0x18028f2f8 with slot 0 -> 0x180024630 and slot +0x38 -> 0x180024270; the default file-I/O table at 0x18028bfa0 has slots 0/1/2 -> 0x180005030/0x180005150/0x180005180; the active stream-manager table begins at 0x18028c000 with +0x28 -> 0x180005430, +0x30 -> 0x180024270, and +0x38 -> 0x1800243e0; the provider and pump tables at 0x180292c58 and 0x180292fd0 expose slot 0 -> 0x1800b9530 and slot 0 -> 0x1800bc1e0 respectively. This is a static pointer-table proof of the I/O dispatch topology only; it does not prove that a live external-source request selects these slots or that a returned handle reaches the decoder.",
            ),
            native_playback_stage(
                "readCompletion",
                "AkSoundEngine ReadFileEx completion",
                "queued read completion transform and callback",
                None,
                "",
                "0x1800245b0",
                "The ReadFileEx completion routine 0x1800245b0 (passed as the OS completion argument by the batch reader) resolves the carrier through the completed ring slot's +0x18 pointer. On success it calls 0x1800092d0 -> 0x180009020 with the carrier for an in-place post-read transform, then tail-jumps to carrier +0x18 with rcx=carrier and status 1/2. For the ordinary pump carrier=request+0x8, carrier +0x18 aliases request +0x20 and is the fixed callback 0x1800bf190. That callback reads provider base Q=[request +0x48], locks Q's device/queue state at +0x60, recycles the request, and walks associated nodes through virtual +0x30 release/advance calls. Since the decoder owns Q+0x90 through the secondary provider vtable, this closes ReadFileEx -> request cleanup/release -> the codec provider allocation/queue; it is not a PCM decoder and does not directly invoke the codec stream object's indirect callback at +0.",
            ),
            native_playback_stage(
                "codecReadBoundary",
                "AkSoundEngine embedded codec path",
                "stream callback -> Opus/packet parser",
                None,
                "",
                "0x1801c9fa0",
                "The generic codec stream reader at 0x1801c9fa0 keeps buffered bytes at stream-object +0x48 and inline stream state at +0x58, then calls the indirect function pointer at +0 with context +0x20, buffer, and length. Setup 0x1801ca710 copies the caller-provided 32-byte callback descriptor into the stream object before allocating its buffer. The exact `.rdata` descriptor literals reached by current calls are 0x1802b09d8 for Opus and 0x1802b1020 for the generic memory source. The selected Opus path 0x1801c5239 passes 0x1802b09d8; descriptor +0 is 0x1801c44d0, a memory-source copier that reads context +0x60 with available/offset fields at +0x68/+0x6c and calls source-provider vtable +0x80 only when releasing an exhausted buffer. A second native source path is also closed: 0x1801c4650 -> 0x1801ca9a0 -> 0x1801cfe80 constructs a 24-byte memory-stream context (source pointer, byte length, cursor) and four-function descriptor at its local +0x30; descriptor +0 = 0x1801cfd80 copies bytes and advances context +0x10, +0x8 = 0x1801cfe00 updates the cursor for seek modes, +0x10 = 0x18010ad90 returns the source pointer, and +0x18 = 0x1801cfd70 frees the stream wrapper. Thus both the selected Opus descriptor and this header-recognized generic memory descriptor have statically resolved stream callbacks; descriptors not reached by these current callers remain an evidence gap. The decoder-side provider handoff is exact: source prep 0x1801af960 gets provider +0x78 buffer/size, decoder address point 0x18029cde8 +0x130 resolves to 0x1801afc80, and that method stores the buffer at decoder +0x60; decoder +0x120 -> 0x1801aebf0 and reset 0x1801af740 release/advance through provider +0x80. The provider is the secondary +0x90 interface of the same base object retained by request +0x48, so the static file-read completion now joins the codec provider queue. Codec state path 0x1801c8d11 directly calls the stream reader; packet wrapper 0x1801c8b60 reaches 0x1801cc1b0 at 0x1801c8bda. Its callee-frame +0xf0 callback slot is populated by every direct 0x1801cc1f0 caller: 0x1801c6490 and 0x1801c6bf2 pass 0x1801c6f90, an integer-array transform, while wrapper 0x1801cc1e1 passes 0x1801cbff0, another integer-array transform. Those known callbacks are invoked at 0x1801cc4ce/0x1801cc532/0x1801cc57e, so this parser callback branch is not a PCM sink. The selected decoder output boundary is now statically closed: 0x1801c4650-0x1801c48cc calls generic decoder 0x1801c7ec0 at 0x1801c4770 with an output-pointer slot; after return it loads float samples through the returned pointer at 0x1801c481a, scales/clamps and converts with cvttss2si, then writes signed 16-bit samples to the caller PCM buffer at 0x1801c483c while advancing the byte count/pointer. This proves decoded float -> PCM16 handoff for this native decode path. The optional decoder callback context +0x2a08 is read only at 0x1801c8b64; no direct store to that field occurs in the current AkSoundEngine function table, so its initialization remains unresolved. The same path reaches exact OpusHead parser 0x1801cf560. The pump-to-ReadFileEx, read-completion-to-request-recycle, and completion-to-provider-allocation joins are statically closed. The direct VoicePlayer externalSourceKey -> AkExternalSourceInfo.szFile -> copied-descriptor path is statically closed; remaining gaps are source-state/sourceInfo instance selection, any unobserved codec descriptor, and live invocation.",
            ),
            native_playback_stage(
                "nativeOptionalDecoderCallbackAudit",
                "AkSoundEngine embedded codec decoder",
                "optional decoder callback slot initialization audit",
                None,
                "",
                "0x1801c8b64",
                "A direct and overlap-aware audit of the selected AkSoundEngine .text function table covers decoder context offsets +0x29f0..+0x2a10. It finds stores at +0x29f8 and +0x29fc, plus a qword store at +0x2a00 that ends at +0x2a07, but no direct or overlapping write reaches +0x2a08. The only current access to that slot is the read at 0x1801c8b64 before the optional callback invocation branch. Therefore callback initialization/ownership is unresolved rather than proven absent; no target is promoted from this negative audit.",
            ),
            native_playback_stage(
                "nativeCodecDescriptorCallsites",
                "AkSoundEngine embedded codec stream setup",
                "direct stream-descriptor callsite coverage",
                None,
                "",
                "0x1801ca710",
                "An exhaustive direct-call scan of the selected AkSoundEngine .text finds only two callsites to stream setup 0x1801ca710: 0x1801c7e3e and 0x1801caa1c. The first is reached by 0x1801c5255 -> 0x1801c7df0 and passes static descriptor 0x1802b09d8; the second is reached by 0x1801c46f9 -> 0x1801ca9a0 -> 0x1801cfe80 and passes the local four-entry generic memory descriptor (0x1801cfd80/0x1801cfe00/0x18010ad90/0x1801cfd70). No additional direct setup callsite or direct descriptor literal is present in the current executable; an address-taken indirect caller would remain outside this direct-call result.",
            ),
            native_playback_stage(
                "nativeCodecIndirectSetupReferenceAudit",
                "AkSoundEngine embedded codec stream setup",
                "address-taken stream setup reference audit",
                None,
                "",
                "0x1801ca710",
                "A raw selected-build executable scan finds no absolute pointer literal in writable/read-only sections and no RIP-relative memory operand resolving to stream setup 0x1801ca710 or the generic reader 0x1801c9fa0. Together with the exhaustive direct-call result, this excludes an in-image static address reference for another setup caller or descriptor table in the scanned sections. It cannot exclude a runtime-computed function pointer, a pointer supplied by an external module, or a descriptor assembled through an indirect call, so other codec callbacks remain an evidence gap rather than proven absent.",
            ),
            native_playback_stage(
                "nativeCodecReaderCallsiteAudit",
                "AkSoundEngine embedded codec stream reader",
                "generic stream reader direct-call census",
                None,
                "",
                "0x1801c9fa0",
                "An exhaustive direct-call scan of the selected AkSoundEngine .text finds ten valid callsites to generic reader 0x1801c9fa0: 0x1801c83fd in containing function 0x1801c8160, 0x1801c8d11 in 0x1801c8c60, 0x1801c96bf/0x1801c985a/0x1801c9909 in 0x1801c9670, 0x1801c9adb in 0x1801c9a00, 0x1801c9cca in 0x1801c9c80, 0x1801ca1eb in 0x1801ca110, and 0x1801cb8ee/0x1801cbd1b in 0x1801cb270. Each passes a stream object in rcx plus a caller-owned range/output descriptor; no other direct reader call exists in the selected .text. This expands read-consumer coverage beyond the two setup callsites, but does not by itself identify additional setup descriptors or prove the indirect callback target for any caller.",
            ),
            native_playback_stage(
                "nativeCodecDecoderCallsiteAudit",
                "AkSoundEngine embedded codec decoder",
                "generic decoder direct-call census",
                None,
                "",
                "0x1801c7ec0",
                "An exhaustive direct-call scan of the selected AkSoundEngine .text finds three valid calls to generic decoder 0x1801c7ec0: 0x1801c477b in function 0x1801c4729, plus 0x1801c49bc and 0x1801c4a3e in function 0x1801c499c. The 0x1801c477b call receives local output-pointer/count slots and its returned float samples flow to the signed PCM16 writes at 0x1801c481a/0x1801c483c; its native return address is 0x1801c4780. The 0x1801c49bc call is the initial decode attempt (return address 0x1801c49c1); 0x1801c4a3e retries after provider refill 0x1801af960 (return address 0x1801c4a43), and both return codes drive decoder state/consumption rather than independently proving a PCM sink. No other direct decoder call exists in the selected .text. The runtime manifest also hooks this exact entry with ABI (decoder, float-output slot, frame-count slot), samples decoder owner +0x268, provider +0x58, and native return address, and reports intersections with the key registry and provider-preparation hooks when a verified capture is available; those observations are still absent here.",
            ),
        ),
        "branches": (
            {
                "id": "uninitialized",
                "label": "Stream manager unavailable",
                "relation": "The native pump returns status 0x6d before walking devices when the stream manager has not been initialized.",
            },
        ),
        "boundary": (
            "This closes the Wwise package/media I/O boundary to a registered native I/O-device callback rather than the generic managed VFS low-I/O reader, and the selected native plugin now supplies direct CreateFileW/GetFileSize, queued ReadFileEx, read-completion transform, and embedded codec-parser evidence. "
            "The current binary identifies the registration site, 0x468-byte device object, active composite address point, source-provider queue binding, virtual pump, the composite default file-I/O object at device +0x428, the concrete CreateFileW helper, provider/state dispatch 0x180005430 -> 0x180024200 -> 0x1800b92c0, and the direct pump call to 0x180024270 ReadFileEx. It also identifies the ordinary candidate carrier as request +0x8, maps carrier +0x18 to fixed callback 0x1800bf190, and closes ReadFileEx -> request-recycle/release into the same dual-interface provider allocation: primary base at request +0x48, codec-facing secondary at base +0x90. The provider +0x20 call remains branch-sensitive: active implementation 0x1800bc660 may assemble a segment through 0x1800bb970 -> 0x1800bb8e0, while alternate 0x1800b8820 does not populate candidate context/flag slots. The selected decoder's 0x1801c4650 -> 0x1801c7ec0 -> 0x1801c481a/0x1801c483c path now proves float-sample to signed PCM16 writes. The direct VoicePlayer externalSourceKey -> AkExternalSourceInfo.szFile -> copied-descriptor path is statically closed, and selector output +0x10 is copied into source +0x338 before provider preparation. Remaining static gaps are the runtime source-state/sourceInfo instance/key match, generic other-codec stream callback targets, and live invocation; no direct GameAssembly caller was found by the current static call-rel32 scan.",
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
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["vfsPackageLoad"],),
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
        native_call_chains=(AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["vfsPackageLoad"],),
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
            "SetState", "SetSwitch", "SetRTPCValue", "PerformStreamMgrIO",
        ),
        native_call_chains=(
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["adapterPost"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["externalSource"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["vfsPackageLoad"],
            AUDIO_PLAYBACK_NATIVE_CALL_CHAINS["streamManagerIoPump"],
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


normalize_posix = context_utils.normalize_posix
_append_context = context_utils.append_context
load_json = context_utils.load_json


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
























def _metadata_module() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_audio_metadata_helper", METADATA_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load metadata helper: {METADATA_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def collect_metadata_event_symbol_aliases(
    metadata_path: Path | None,
    current_wwise_event_hashes: Iterable[int],
) -> dict[str, Any]:
    """Join exact ``AU_*`` IL2CPP field symbols to current Wwise Event IDs.

    These fields are shipped game-side constants, not observed calls.  The
    hash join therefore recovers an Event's symbol identity and conservative
    name-prefix category, while leaving its runtime caller/trigger unresolved.
    Hash collisions are excluded rather than choosing one field arbitrarily.
    """

    base: dict[str, Any] = {
        "schemaVersion": METADATA_EVENT_SYMBOL_SCHEMA_VERSION,
        "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:string-field",
        "evidence": "exactIl2CppMetadataFieldNameAudioHashAndCurrentWwiseEvent",
        "metadataSha256": None,
        "metadataSize": None,
        "metadataVersion": None,
        "status": "degraded",
        "candidateCount": 0,
        "matchCount": 0,
        "ambiguousHashCount": 0,
        "entries": [],
        "evidenceBoundary": (
            "An AU_* field name hashed with the current AudioHashGenerator and "
            "matching a scanned Wwise Event proves a static game-side symbol to "
            "uint32 Event identity join. It does not prove a runtime setter, "
            "caller, execution, selected Wwise branch, or audibility."
        ),
    }
    if metadata_path is None or not metadata_path.is_file():
        base["reason"] = "Installed IL2CPP metadata was unavailable."
        return base

    current_hashes = {
        int(value) & 0xFFFFFFFF
        for value in current_wwise_event_hashes
        if isinstance(value, int)
    }
    metadata_sha256 = file_sha256(metadata_path)
    base.update({
        "metadataSha256": metadata_sha256,
        "metadataSize": metadata_path.stat().st_size,
    })
    module = _metadata_module()
    md = module.Metadata(metadata_path)
    base["metadataVersion"] = int(md.version)
    by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for type_def in md.types:
        declaring_type = md.type_full_name(type_def)
        for field in md.fields_for(type_def):
            field_name = str(md.string(field.name_index) or "").strip()
            if not METADATA_EVENT_SYMBOL_RE.fullmatch(field_name):
                continue
            base["candidateCount"] += 1
            event_hash = identifiers.audio_hash_generator_compute(field_name)
            if event_hash not in current_hashes:
                continue
            by_hash[event_hash].append({
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "name": field_name,
                "metadataField": field_name,
                "metadataDeclaringType": declaring_type,
                "metadataFieldIndex": int(field.index),
                "metadataFieldToken": f"0x{int(field.token):08x}",
                "metadataSha256": metadata_sha256,
                "source": base["source"],
                "evidence": base["evidence"],
            })

    entries: list[dict[str, Any]] = []
    for event_hash, rows in by_hash.items():
        identities = {
            (str(row.get("name") or "").casefold(), str(row.get("metadataDeclaringType") or ""))
            for row in rows
        }
        if len(identities) != 1:
            continue
        entries.append(sorted(rows, key=lambda row: (
            str(row.get("name") or "").casefold(),
            str(row.get("metadataDeclaringType") or ""),
            int(row.get("metadataFieldIndex") or 0),
        ))[0])
    entries.sort(key=lambda row: (int(row.get("eventHash") or 0), str(row.get("name") or "")))
    base.update({
        "status": "complete",
        "matchCount": len(entries),
        "ambiguousHashCount": sum(
            len({
                (str(row.get("name") or "").casefold(), str(row.get("metadataDeclaringType") or ""))
                for row in rows
            }) > 1
            for rows in by_hash.values()
        ),
        "entries": entries,
    })
    return base


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


LEVELSCRIPT_AUDIO_EVENT_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "PlayAudiAtPosition": (("key", "play"),),
    "PlayAudio": (("key", "play"),),
    "PlayAudioAndWait": (("eventName", "play"),),
    "PlayAudioOnTarget": (("audioKey", "play"),),
    "PlayStandaloneMusic": (("startEvent", "standaloneStart"), ("stopEvent", "standaloneStop")),
    "PostAudioStatusEvent": (("statusEnterEvent", "statusEnter"), ("statusExitEvent", "statusExit")),
    "PostMusicEvent": (("musicEvent", "post"), ("musicEventOnRelease", "release")),
}




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

    if __package__ == "scripts":
        from scripts.story_builder.level_bindings import (
            parse_leveldata_levelscript_brief_dictionary,
        )
    else:
        from story_builder.level_bindings import (
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

    cue_semantics = cue_semantics or table_contexts.collect_audio_cue_semantics(export_root)
    cue_definitions = cue_semantics.get("cueDefinitions") or {}
    if __package__ == "scripts":
        from scripts.story_builder.level_bindings import (
            resolve_levelscript_dynamic_property_string,
            resolve_levelscript_dynamic_property_string_list,
        )
    else:
        from story_builder.level_bindings import (
            resolve_levelscript_dynamic_property_string,
            resolve_levelscript_dynamic_property_string_list,
        )

    if decode_file is None:
        if __package__ == "scripts":
            from scripts.story_builder.levelscript_binary import (
                decode_levelscript_record_payload,
                extract_levelscript_uid_records,
                levelscript_action_map_membership,
                levelscript_record_semantic_key,
            )
        else:
            from story_builder.levelscript_binary import (
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
    voice_invocations: list[dict[str, Any]] = []
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
            for binding in action.get("voiceBindings") or []:
                if not isinstance(binding, dict):
                    continue
                voice_id = str(binding.get("voiceId") or "").strip()
                if not voice_id:
                    continue
                voice_invocations.append({
                    **common,
                    "kind": "levelScriptVoiceTrigger",
                    "semanticRole": "authoredLevelScriptVoiceSelection",
                    "voiceId": voice_id,
                    "triggerRole": str(binding.get("role") or "voice"),
                    "sourceField": str(binding.get("sourceField") or "_voId"),
                    "voiceIdentityKind": str(
                        binding.get("identityKind") or "AudioDialogPathStem"
                    ),
                    "wwiseEventStatus": "notApplicable",
                })
            for binding in action.get("cueBindings") or []:
                if not isinstance(binding, dict) or not str(binding.get("cueName") or ""):
                    continue
                cue_name = str(binding["cueName"])
                cue_id = identifiers.audio_hash_generator_compute(cue_name)
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
        "voiceInvocations": voice_invocations,
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
            "constantVoiceBindings": len(voice_invocations),
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
            "PlayVoice/PlayVoiceNarrative _voId values are AudioDialog path-stem selections, "
            "not Wwise Events; an exact stem join proves the selected voice media identity. "
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
                    or "DialogAudioEventPlayableAsset" in name
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
                integer_event_value = _scalar_value(record, "$.audioEvent._id")
                if "DialogAudioEventPlayableAsset" in name and key:
                    try:
                        integer_event_hash = int(integer_event_value) & 0xFFFFFFFF
                    except (TypeError, ValueError):
                        integer_event_hash = 0
                    if integer_event_hash:
                        playable_events[key] = identifiers.hashed_event_key(integer_event_hash)
                        stats["dialogAudioEventPlayableRecords"] += 1
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
                integer_event_value = _scalar_value(record, "$.audioEvent._id")
                identity = _object_identity(record)
                key = _object_identity_key(identity)
                if "DialogAudioEventPlayableAsset" in name and key:
                    try:
                        integer_event_hash = int(integer_event_value) & 0xFFFFFFFF
                    except (TypeError, ValueError):
                        integer_event_hash = 0
                    if integer_event_hash:
                        playable_events[key] = identifiers.hashed_event_key(integer_event_hash)
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
                clip_indices = {index for index, _display in clip_displays}
                for pptr in record.get("pptrs") or []:
                    if not isinstance(pptr, dict):
                        continue
                    match = re.fullmatch(r"\$\.m_Clips\[(\d+)\]\.m_Asset", str(pptr.get("path") or ""))
                    if not match:
                        continue
                    clip_index = int(match.group(1))
                    if clip_index in clip_indices:
                        continue
                    target = pptr.get("target") if isinstance(pptr.get("target"), dict) else {}
                    if "DialogAudioEventPlayableAsset" not in str(target.get("name") or ""):
                        continue
                    clip_displays.append((clip_index, ""))
                    clip_indices.add(clip_index)
                    stats["dialogAudioClipsRecoveredFromExactAssetPPtr"] += 1
                for clip_index, display_name in clip_displays:
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
                        or "DialogAudioEventPlayableAsset" in asset_name
                    )
                    asset_is_dialog_audio_id = "DialogAudioEventPlayableAsset" in asset_name
                    asset_is_audio_music = "AudioMusicPlayable" in asset_name
                    asset_is_audio_cue = "AudioCuePlayable" in asset_name
                    if (
                        wanted
                        and (playable_event_id or asset_is_audio_playable)
                        and display_name not in wanted
                        and playable_event_id not in wanted
                        and not asset_is_audio_music
                        and not asset_is_dialog_audio_id
                    ):
                        continue
                    if playable_event_id and playable_event_id != display_name and not asset_is_dialog_audio_id:
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
                    authored_event_name = ""
                    if asset_is_dialog_audio_id and playable_event_id:
                        display_match = re.search(r"<([^<>]+)>", display_name)
                        candidate_name = str(display_match.group(1) if display_match else "").strip()
                        if candidate_name and identifiers.audio_hash_generator_compute(candidate_name) == int(
                            playable_event_id.rsplit("0x", 1)[1], 16
                        ):
                            authored_event_name = candidate_name
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
                            "exactDialogAudioEventPlayableAudioIdScalar"
                            if asset_is_dialog_audio_id and playable_event_id
                            else "exactAudioEventPlayableScalar"
                            if playable_event_id
                            else "trackDisplayNameOnlyScalar"
                        ),
                        "authoredEventName": authored_event_name or None,
                        "authoredEventNameEvidence": (
                            "exactTimelineDisplayNameHashEqualsSerializedAudioId"
                            if authored_event_name else None
                        ),
                        "audioPlayableSerializedFile": asset.get("serializedFile"),
                        "audioPlayablePathId": asset.get("pathId"),
                        "evidence": (
                            "exactDialogAudioEventPlayableAudioIdTrackParentAssetPPtrs"
                            if asset_is_dialog_audio_id and playable_event_id
                            else "exactAudioEventPlayableScalarTrackParentAssetPPtrs"
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
            "m_PlayableAsset PPtrs are exact serialized-object identity joins. Typed integer "
            "DialogAudioEventPlayableAsset AudioIds additionally require exact display-name hash "
            "agreement before recovering an authored Event name. "
            "They prove authored "
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


def _iter_mono_audio_object_index_rows(path: Path) -> Iterable[dict[str, Any]]:
    """Yield only object-index rows containing a maintained AudioId field.

    The current StreamingAssets MonoBehaviour index is several gigabytes.  Use
    ripgrep as a byte-level prefilter when available, while retaining a small
    stdlib fallback for tests and environments without rg.
    """

    if not path.is_file():
        return
    rg = shutil.which("rg")
    def matching_rows(patterns: Iterable[str]) -> Iterable[dict[str, Any]]:
        text_patterns = tuple(patterns)
        if rg:
            command = [rg, "--no-filename", "--no-line-number", "--fixed-strings"]
            for pattern in text_patterns:
                command.extend(("-e", pattern))
            command.append(str(path))
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            for line in process.stdout:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    yield row
            process.stdout.close()
            error = process.stderr.read() if process.stderr is not None else ""
            if process.stderr is not None:
                process.stderr.close()
            return_code = process.wait()
            if return_code not in (0, 1):
                raise RuntimeError(
                    f"rg MonoBehaviour AudioId prefilter failed for {path}: "
                    f"{error.strip() or f'exit {return_code}'}"
                )
            return
        byte_patterns = tuple(value.encode("utf-8") for value in text_patterns)
        with path.open("rb") as handle:
            for raw_line in handle:
                if not any(pattern in raw_line for pattern in byte_patterns):
                    continue
                try:
                    row = json.loads(raw_line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(row, dict):
                    yield row

    schema_ids: set[str] = set()
    seen_objects: set[tuple[str, int]] = set()
    for row in matching_rows(MONO_BEHAVIOUR_AUDIO_EVENT_PREFILTERS):
        if row.get("recordType") == "schema" and row.get("schemaId"):
            schema_ids.add(str(row["schemaId"]))
            continue
        if row.get("recordType") != "object":
            continue
        object_row = row.get("object") if isinstance(row.get("object"), dict) else {}
        identity = (str(object_row.get("serializedFile") or ""), int(object_row.get("pathId") or 0))
        if identity not in seen_objects:
            seen_objects.add(identity)
            yield row
    if not schema_ids:
        return
    schema_patterns = [f'\"schemaId\":\"{schema_id}\"' for schema_id in sorted(schema_ids)]
    for row in matching_rows(schema_patterns):
        if row.get("recordType") != "object":
            continue
        object_row = row.get("object") if isinstance(row.get("object"), dict) else {}
        identity = (str(object_row.get("serializedFile") or ""), int(object_row.get("pathId") or 0))
        if identity in seen_objects:
            continue
        seen_objects.add(identity)
        yield row


def _mono_audio_event_scalar(path: Any, value: Any) -> tuple[int, str] | None:
    """Return a typed uint32 Event and authored role for a scalar path."""

    scalar_path = str(path or "")
    role = ""
    if scalar_path.endswith((".soundBase.soundSpawn.value", ".soundBase.soundSpawn.hex")):
        role = "soundSpawn"
    elif scalar_path.endswith((".soundBase.soundFinish.value", ".soundBase.soundFinish.hex")):
        role = "soundFinish"
    elif scalar_path.endswith("._id"):
        candidate = scalar_path.rsplit(".", 2)[-2]
        if candidate in MONO_BEHAVIOUR_AUDIO_EVENT_FIELD_NAMES:
            role = candidate
    if not role:
        return None
    try:
        numeric = int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError):
        return None
    event_hash = numeric & 0xFFFFFFFF
    if event_hash == 0:
        return None
    return event_hash, role


def _mono_play_line_sound_event_scalars(
    scalar_values: dict[str, Any],
) -> Iterable[tuple[str, int, str, dict[str, Any]]]:
    """Recover the exact two AudioIds from a 24-byte PlayLineSound payload."""

    suffix = ".type.class"
    for class_path, class_name in scalar_values.items():
        if class_name != "PlayLineSound" or not class_path.endswith(suffix):
            continue
        prefix = class_path[:-len(suffix)]
        if (
            scalar_values.get(prefix + ".type.ns") != "Beyond.Gameplay"
            or scalar_values.get(prefix + ".type.asm") != "Gameplay.Beyond"
            or scalar_values.get(prefix + ".data.layout") != "Beyond.Gameplay.PlayLineSound"
        ):
            continue
        decoded_paths = {
            "soundSpawn": prefix + ".data.soundSpawn.hex",
            "soundFinish": prefix + ".data.soundFinish.hex",
        }
        if all(path in scalar_values for path in decoded_paths.values()):
            for role, scalar_path in decoded_paths.items():
                try:
                    event_hash = int(str(scalar_values[scalar_path]), 0) & 0xFFFFFFFF
                except (TypeError, ValueError):
                    continue
                if event_hash == 0:
                    continue
                yield scalar_path, event_hash, role, {
                    "managedReferenceClass": "PlayLineSound",
                    "managedReferenceNamespace": "Beyond.Gameplay",
                    "managedReferenceAssembly": "Gameplay.Beyond",
                    "managedReferenceLayout": "Beyond.Gameplay.PlayLineSound",
                    "managedReferencePayloadLength": 24,
                    "managedReferenceDecodeStatus": "strictStructuredDecoder",
                }
            continue
        word_paths = [prefix + f".data.rawWords[{index}].hex" for index in range(6)]
        if not all(path in scalar_values for path in word_paths):
            continue
        if prefix + ".data.rawWords[6].hex" in scalar_values:
            continue
        for word_index, role in ((0, "soundSpawn"), (1, "soundFinish")):
            scalar_path = word_paths[word_index]
            try:
                event_hash = int(str(scalar_values[scalar_path]), 0) & 0xFFFFFFFF
            except (TypeError, ValueError):
                continue
            if event_hash == 0:
                continue
            yield scalar_path, event_hash, role, {
                "managedReferenceClass": "PlayLineSound",
                "managedReferenceNamespace": "Beyond.Gameplay",
                "managedReferenceAssembly": "Gameplay.Beyond",
                "managedReferenceLayout": "Beyond.Gameplay.PlayLineSound",
                "managedReferencePayloadLength": 24,
                "managedReferenceDecodeStatus": "metadataValidatedLegacyRawWordFallback",
            }


def _iter_json_leaf_scalars(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$animestudio":
                continue
            yield from _iter_json_leaf_scalars(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_json_leaf_scalars(child, f"{path}[{index}]")
    elif isinstance(value, (str, int)) and not isinstance(value, bool):
        yield path, value


def _mono_audio_raw_json_paths(root: Path) -> Iterable[Path]:
    """Locate the bounded raw objects whose JSON contains maintained fields."""

    directories = [
        root / source / "json_by_type" / "MonoBehaviour"
        for source in ("StreamingAssets", "Persistent")
        if (root / source / "json_by_type" / "MonoBehaviour").is_dir()
    ]
    if not directories:
        return
    rg = shutil.which("rg")
    if rg:
        command = [rg, "--files-with-matches", "--fixed-strings", "--glob", "*.json"]
        for pattern in MONO_BEHAVIOUR_AUDIO_EVENT_PREFILTERS:
            command.extend(("-e", pattern.split("._id", 1)[0]))
        command.extend(str(path) for path in directories)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            candidate = Path(line.strip())
            if candidate.is_file():
                yield candidate
        process.stdout.close()
        error = process.stderr.read() if process.stderr is not None else ""
        if process.stderr is not None:
            process.stderr.close()
        return_code = process.wait()
        if return_code not in (0, 1):
            raise RuntimeError(
                f"rg raw MonoBehaviour AudioId prefilter failed: "
                f"{error.strip() or f'exit {return_code}'}"
            )
        return
    patterns = tuple(value.encode("utf-8") for value in MONO_BEHAVIOUR_AUDIO_EVENT_PREFILTERS)
    for directory in directories:
        for path in directory.glob("*.json"):
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if any(pattern in data for pattern in patterns):
                yield path


def collect_mono_behaviour_audio_id_contexts(
    export_root: Path,
    current_wwise_event_hashes: set[int],
) -> dict[str, Any]:
    """Recover exact serialized component AudioId fields for current Events.

    This closes a purpose gap for components, effects, state machines, and
    WaterDrone configs without claiming that their GameObjects instantiated or
    that the configured callback/state executed.
    """

    root = export_root / "recovered" / "AnimeStudio-cli"
    index_paths = [
        root / source / "object_index" / "parts"
        / f"{source}_animestudio_json_by_type_MonoBehaviour.jsonl"
        for source in ("StreamingAssets", "Persistent")
    ]
    source_fingerprint = [{
        "path": normalize_posix(path.relative_to(export_root)),
        "size": path.stat().st_size,
        "mtimeNs": path.stat().st_mtime_ns,
    } for path in index_paths if path.is_file()]
    source_fingerprint.extend({
        "path": normalize_posix(path.relative_to(export_root)),
        "kind": "directory",
        "mtimeNs": path.stat().st_mtime_ns,
    } for path in (
        root / source / "json_by_type" / "MonoBehaviour"
        for source in ("StreamingAssets", "Persistent")
    ) if path.is_dir())
    event_hash_fingerprint = hashlib.sha256(
        "\n".join(f"{value & 0xFFFFFFFF:08x}" for value in sorted(current_wwise_event_hashes)).encode("ascii")
    ).hexdigest()
    cache_path = export_root / "recovered" / "audio_semantics" / "mono_behaviour_audio_id_contexts.json"
    cached = load_json(cache_path, {})
    if (
        isinstance(cached, dict)
        and cached.get("cacheSchemaVersion") == MONO_BEHAVIOUR_AUDIO_CONTEXT_CACHE_SCHEMA_VERSION
        and cached.get("audioSemanticSchemaVersion") == AUDIO_SEMANTIC_SCHEMA_VERSION
        and cached.get("sourceFingerprint") == source_fingerprint
        and cached.get("eventHashFingerprint") == event_hash_fingerprint
        and isinstance(cached.get("result"), dict)
    ):
        result = dict(cached["result"])
        result["stats"] = {**(result.get("stats") or {}), "cacheStatus": "hit"}
        return result

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    source_paths: list[str] = []
    candidate_objects = 0
    accepted_occurrences = 0
    raw_candidate_files = 0
    raw_fallback_occurrences = 0
    role_counts: Counter[str] = Counter()
    occurrence_keys: set[tuple[str, str, int, str, int]] = set()
    raw_object_candidates: set[tuple[str, str, int]] = set()
    for source_root in ("StreamingAssets", "Persistent"):
        path = (
            root / source_root / "object_index" / "parts"
            / f"{source_root}_animestudio_json_by_type_MonoBehaviour.jsonl"
        )
        if not path.is_file():
            continue
        source_paths.append(normalize_posix(path.relative_to(export_root)))
        for row in _iter_mono_audio_object_index_rows(path):
            candidate_objects += 1
            scalars = [
                scalar for scalar in row.get("scalars") or []
                if isinstance(scalar, list) and len(scalar) >= 3
            ]
            object_row = row.get("object") if isinstance(row.get("object"), dict) else {}
            try:
                candidate_path_id = int(object_row.get("pathId") or 0)
            except (TypeError, ValueError):
                candidate_path_id = 0
            raw_object_candidates.add((
                source_root,
                str(row.get("name") or ""),
                candidate_path_id,
            ))
            scene = row.get("sceneContext") if isinstance(row.get("sceneContext"), dict) else {}
            script = row.get("script") if isinstance(row.get("script"), dict) else {}
            scalar_values = {
                str(scalar[0]): scalar[2]
                for scalar in scalars
                if isinstance(scalar[0], str)
            }
            for scalar_path, _scalar_type, scalar_value in scalars:
                parsed = _mono_audio_event_scalar(scalar_path, scalar_value)
                if parsed is None:
                    continue
                event_hash, authored_role = parsed
                if event_hash not in current_wwise_event_hashes:
                    continue
                normalized_scalar_path = str(scalar_path)
                if authored_role in {"soundSpawn", "soundFinish"}:
                    normalized_scalar_path = normalized_scalar_path.rsplit(".", 1)[0]
                occurrence_key = (
                    source_root,
                    str(object_row.get("serializedFile") or ""),
                    int(object_row.get("pathId") or 0),
                    normalized_scalar_path,
                    event_hash,
                )
                if occurrence_key in occurrence_keys:
                    continue
                occurrence_keys.add(occurrence_key)
                accepted_occurrences += 1
                role_counts[authored_role] += 1
                context: dict[str, Any] = {
                    "kind": "monoBehaviourAudioIdField",
                    "semanticRole": "authoredSerializedComponentAudioEvent",
                    "authoredFieldRole": authored_role,
                    "serializedFieldPath": scalar_path,
                    "signedValue": scalar_value if isinstance(scalar_value, int) else None,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "sourceRoot": source_root,
                    "objectIndexSource": normalize_posix(path.relative_to(export_root)),
                    "serializedFile": object_row.get("serializedFile"),
                    "sourceAssetFile": object_row.get("source"),
                    "sourceOffset": object_row.get("sourceOffset"),
                    "pathId": object_row.get("pathId"),
                    "componentName": row.get("name"),
                    "schemaId": row.get("schemaId"),
                    "typeTreeSource": row.get("typeTreeSource"),
                    "scriptPathId": script.get("pathId"),
                    "scriptFullName": script.get("fullName"),
                    "gameObjectName": scene.get("gameObjectName"),
                    "hierarchyPath": scene.get("hierarchyPath") or [],
                    "worldPosition": scene.get("worldPosition"),
                    "worldPositionStatus": scene.get("worldPositionStatus"),
                    "confidence": "direct",
                    "playbackPlacementStatus": "authoredComponentAudioField",
                    "triggerBindingStatus": "exactSerializedAudioIdField",
                    "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                    "evidence": "exactSerializedMonoBehaviourAudioIdFieldAndCurrentWwiseEvent",
                    "triggerRequestEvidence": [
                        "exactSerializedMonoBehaviourAudioIdField",
                        "exactCurrentWwiseEventHash",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "componentInstantiationNotObserved",
                        "componentStateOrCallbackExecutionNotObserved",
                    ],
                }
                if authored_role in {"soundSpawn", "soundFinish"}:
                    prefix = str(scalar_path).rsplit(".data.soundBase.", 1)[0]
                    context["managedReferenceClass"] = scalar_values.get(prefix + ".type.class")
                    context["managedReferenceNamespace"] = scalar_values.get(prefix + ".type.ns")
                    context["managedReferenceLayout"] = scalar_values.get(prefix + ".data.layout")
                elif authored_role == "normalAudiId":
                    config_prefix = str(scalar_path).rsplit(".normalAudiId._id", 1)[0]
                    state_prefix = config_prefix.split(".audioPlayConfigs[", 1)[0]
                    controls = {
                        "stateName": scalar_values.get(state_prefix + ".stateName"),
                        "animationEventName": scalar_values.get(config_prefix + ".animationEventName"),
                        "isEvent": scalar_values.get(config_prefix + ".isEvent"),
                        "isDirectlyPlay": scalar_values.get(config_prefix + ".isDirectlyPlay"),
                        "canLoopActive": scalar_values.get(config_prefix + ".canLoopActive"),
                        "eAudioTriggerState": scalar_values.get(config_prefix + ".eAudioTriggerState"),
                        "disableAudioOnState": scalar_values.get(state_prefix + ".disableAudio"),
                    }
                    context["serializedPlaybackControls"] = {
                        key: value for key, value in controls.items() if value not in (None, "")
                    }
                _append_context(
                    contexts,
                    seen,
                    identifiers.event_hash_context_key(event_hash),
                    {key: value for key, value in context.items() if value not in (None, "", [])},
                )
            for scalar_path, event_hash, authored_role, managed_details in (
                _mono_play_line_sound_event_scalars(scalar_values)
            ):
                if event_hash not in current_wwise_event_hashes:
                    continue
                occurrence_key = (
                    source_root,
                    str(object_row.get("serializedFile") or ""),
                    int(object_row.get("pathId") or 0),
                    scalar_path,
                    event_hash,
                )
                if occurrence_key in occurrence_keys:
                    continue
                occurrence_keys.add(occurrence_key)
                accepted_occurrences += 1
                role_counts[authored_role] += 1
                context = {
                    "kind": "monoBehaviourAudioIdField",
                    "semanticRole": "authoredSerializedComponentAudioEvent",
                    "authoredFieldRole": authored_role,
                    "serializedFieldPath": scalar_path,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "sourceRoot": source_root,
                    "objectIndexSource": normalize_posix(path.relative_to(export_root)),
                    "serializedFile": object_row.get("serializedFile"),
                    "sourceAssetFile": object_row.get("source"),
                    "sourceOffset": object_row.get("sourceOffset"),
                    "pathId": object_row.get("pathId"),
                    "componentName": row.get("name"),
                    "schemaId": row.get("schemaId"),
                    "typeTreeSource": row.get("typeTreeSource"),
                    "scriptPathId": script.get("pathId"),
                    "scriptFullName": script.get("fullName"),
                    "gameObjectName": scene.get("gameObjectName"),
                    "hierarchyPath": scene.get("hierarchyPath") or [],
                    "worldPosition": scene.get("worldPosition"),
                    "worldPositionStatus": scene.get("worldPositionStatus"),
                    "confidence": "direct",
                    "playbackPlacementStatus": "authoredComponentAudioField",
                    "triggerBindingStatus": "exactSerializedAudioIdField",
                    "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                    "evidence": "exactSerializedPlayLineSoundPayloadAndCurrentWwiseEvent",
                    "triggerRequestEvidence": [
                        "exactSerializedManagedReferenceType",
                        "exactPlayLineSound24ByteFieldLayout",
                        "exactCurrentWwiseEventHash",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "componentInstantiationNotObserved",
                        "managedReferenceExecutionNotObserved",
                    ],
                    **managed_details,
                }
                _append_context(
                    contexts,
                    seen,
                    identifiers.event_hash_context_key(event_hash),
                    {key: value for key, value in context.items() if value not in (None, "", [])},
                )
    raw_paths: set[Path] = set()
    for source_root, object_name, candidate_path_id in raw_object_candidates:
        if not object_name:
            continue
        raw_path = (
            root / source_root / "json_by_type" / "MonoBehaviour"
            / f"{object_name}_p{candidate_path_id & ((1 << 64) - 1):016X}.json"
        )
        if raw_path.is_file():
            raw_paths.add(raw_path)
    raw_paths.update(_mono_audio_raw_json_paths(root))
    for raw_path in sorted(raw_paths):
        raw_candidate_files += 1
        payload = load_json(raw_path, {})
        if not isinstance(payload, dict):
            continue
        metadata = payload.get("$animestudio")
        metadata = metadata if isinstance(metadata, dict) else {}
        try:
            source_root = raw_path.relative_to(root).parts[0]
        except (ValueError, IndexError):
            source_root = "unknown"
        serialized_file = str(metadata.get("sourceFile") or "")
        try:
            path_id = int(metadata.get("pathId") or 0)
        except (TypeError, ValueError):
            path_id = 0
        for scalar_path, scalar_value in _iter_json_leaf_scalars(payload):
            parsed = _mono_audio_event_scalar(scalar_path, scalar_value)
            if parsed is None:
                continue
            event_hash, authored_role = parsed
            if event_hash not in current_wwise_event_hashes:
                continue
            normalized_scalar_path = str(scalar_path)
            if authored_role in {"soundSpawn", "soundFinish"}:
                normalized_scalar_path = normalized_scalar_path.rsplit(".", 1)[0]
            occurrence_key = (
                source_root, serialized_file, path_id, normalized_scalar_path, event_hash,
            )
            if occurrence_key in occurrence_keys:
                continue
            occurrence_keys.add(occurrence_key)
            accepted_occurrences += 1
            raw_fallback_occurrences += 1
            role_counts[authored_role] += 1
            context = {
                "kind": "monoBehaviourAudioIdField",
                "semanticRole": "authoredSerializedComponentAudioEvent",
                "authoredFieldRole": authored_role,
                "serializedFieldPath": scalar_path,
                "signedValue": scalar_value if isinstance(scalar_value, int) else None,
                "eventHash": event_hash,
                "eventHex": f"0x{event_hash:08x}",
                "sourceRoot": source_root,
                "rawJsonSource": normalize_posix(raw_path.relative_to(export_root)),
                "serializedFile": serialized_file,
                "sourceOriginalPath": metadata.get("sourceOriginalPath"),
                "sourceOffset": metadata.get("sourceOffset"),
                "pathId": path_id,
                "componentName": metadata.get("name"),
                "typeTreeSource": metadata.get("typeTreeSource"),
                "rawDataSha256": metadata.get("rawDataSha256"),
                "confidence": "direct",
                "playbackPlacementStatus": "authoredComponentAudioField",
                "triggerBindingStatus": "exactSerializedAudioIdField",
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                "evidence": "exactSerializedMonoBehaviourAudioIdFieldAndCurrentWwiseEvent",
                "triggerRequestEvidence": [
                    "exactSerializedMonoBehaviourAudioIdField",
                    "exactCurrentWwiseEventHash",
                ],
                "triggerRuntimeActivationStatuses": [
                    "componentInstantiationNotObserved",
                    "componentStateOrCallbackExecutionNotObserved",
                ],
            }
            _append_context(
                contexts,
                seen,
                identifiers.event_hash_context_key(event_hash),
                {key: value for key, value in context.items() if value not in (None, "", [])},
            )
    boundary = (
        "Exact serialized MonoBehaviour AudioId field paths joined to current Wwise Event "
        "hashes prove authored component/config playback placement. SceneContext, when present, "
        "proves the serialized GameObject and transform hierarchy only. Component instantiation, "
        "state/callback execution, Event posting, Wwise acceptance, selected media, and audibility "
        "were not observed. The one raw-word exception is an exact typed PlayLineSound "
        "managed-reference payload whose six-field/24-byte layout is fixed by current IL2CPP "
        "metadata and complete payload consumption. RTPC fields, generic integers, PathIDs, "
        "untyped raw words, AudioVoTone selection rows, and ResponsiveDialog membership are excluded."
    )
    result = {
        "eventContexts": dict(contexts),
        "stats": {
            "status": "complete" if source_paths else "unavailable",
            "objectIndexSources": source_paths,
            "prefilteredObjectRows": candidate_objects,
            "prefilteredRawJsonFiles": raw_candidate_files,
            "eventContextOccurrences": accepted_occurrences,
            "rawJsonFallbackOccurrences": raw_fallback_occurrences,
            "distinctEventHashes": len(contexts),
            "fieldRoleCounts": dict(sorted(role_counts.items())),
            "runtimeExecutionObserved": 0,
            "cacheStatus": "refreshed",
            "evidenceBoundary": boundary,
        },
        "evidenceBoundary": boundary,
    }
    json_dump(cache_path, {
        "cacheSchemaVersion": MONO_BEHAVIOUR_AUDIO_CONTEXT_CACHE_SCHEMA_VERSION,
        "audioSemanticSchemaVersion": AUDIO_SEMANTIC_SCHEMA_VERSION,
        "sourceFingerprint": source_fingerprint,
        "eventHashFingerprint": event_hash_fingerprint,
        "result": result,
    })
    return result


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
        ("stopOnDisable", "audioPlayableStopOnDisable"),
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
                display_name = str(clip.get("m_DisplayName") or "").strip()
                if display_name:
                    result["timelineClipDisplayName"] = display_name
                if (
                    result.get("audioPlayableKeyStatus")
                    == "exactDialogAudioEventPlayableAudioIdScalar"
                ):
                    display_match = re.search(r"<([^<>]+)>", display_name)
                    candidate_name = str(display_match.group(1) if display_match else "").strip()
                    event_id = str(result.get("eventId") or "")
                    try:
                        event_hash = int(event_id.rsplit("0x", 1)[1], 16) & 0xFFFFFFFF
                    except (ValueError, IndexError):
                        event_hash = None
                    if (
                        candidate_name
                        and event_hash is not None
                        and identifiers.audio_hash_generator_compute(candidate_name) == event_hash
                    ):
                        result["authoredEventName"] = candidate_name
                        result["authoredEventNameEvidence"] = (
                            "exactTimelineDisplayNameHashEqualsSerializedAudioId"
                        )
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
            cue_id = identifiers.audio_hash_generator_compute(cue_name)
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
                    "audioPlayableKeyStatus", "authoredEventName",
                    "authoredEventNameEvidence",
                    "audioPlayableSerializedFile", "audioPlayablePathId", "audioPlayableIsCue",
                    "audioPlayableStopEventAtClipEnd", "audioPlayableStopEventAtClipEndKey",
                    "audioPlayableFadeOutMs", "audioPlayableEnableSeek",
                    "audioPlayableUseBindingObject", "audioPlayableIs2D",
                    "audioPlayableStopOnDisable",
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
                                "exactDialogAudioEventPlayableAudioIdScalar"
                                if context.get("audioPlayableKeyStatus")
                                == "exactDialogAudioEventPlayableAudioIdScalar"
                                else "exactAudioEventPlayableScalar"
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
                            context.get("authoredEventNameEvidence"),
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


def _build_levelscript_voice_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    invocations: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join PlayVoice* ``_voId`` values to AudioDialog media identities.

    The native actions route this field through the voice player.  It is an
    AudioDialog path-stem selection id, not a Wwise Event name, so keep this
    evidence out of the authored Event universe.
    """

    media_by_id = {
        str(row.get("id") or "").strip().casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    for invocation_index, invocation in enumerate(invocations):
        if not isinstance(invocation, dict):
            continue
        voice_id = str(invocation.get("voiceId") or "").strip()
        if not voice_id:
            continue
        media = media_by_id.get(voice_id.casefold(), {})
        media_ref = _trigger_media_ref(media, fallback_id=voice_id)
        story_line_count = int(media.get("storyLineBindingCount") or 0)
        contexts.append({
            "triggerId": (
                f"levelScriptVoice:{invocation.get('levelScriptId') or 'unknown'}:"
                f"{invocation.get('recordStart') or 0}:{invocation_index}:{voice_id}"
            ),
            "semanticKind": "levelScriptVoice",
            "triggerRole": str(invocation.get("triggerRole") or "voice"),
            "situation": {
                "voiceId": voice_id,
                "voiceIdentityKind": "AudioDialogPathStem",
                "levelScriptId": invocation.get("levelScriptId"),
            },
            "meaning": {
                "audioCategory": media.get("audioCategory"),
                "audioDialogPath": media.get("audioDialogPath"),
                "storyLineBindingCount": story_line_count,
                "purposeKnowledgeStatus": media.get("purposeKnowledgeStatus"),
            },
            "action": _compact_trigger_action(invocation),
            "owner": {
                "levelScriptId": invocation.get("levelScriptId"),
                "sourcePath": invocation.get("sourcePath"),
                "ownerStatus": "exactLevelScriptActionRecord",
            },
            "selection": {
                "voiceSelectionStatus": (
                    "exactAudioDialogPathStem" if media else "audioDialogPathStemMissing"
                ),
                "mediaSelectionStatus": (
                    "exactDecodedAudioDialogMedia" if media_ref.get("src")
                    else "decodedMediaMissing"
                ),
                "wwiseEventStatus": "notApplicable",
            },
            "mediaRefs": [media_ref] if media_ref else [],
            "evidence": {
                "definition": "exactLevelScriptPlayVoiceUnionAndVoIdField",
                "owner": "exactLevelScriptActionRecord",
                "media": (
                    "exactAudioDialogPathStem" if media else "audioDialogPathStemMissing"
                ),
                "runtimeExecution": "levelScriptActionExecutionNotObserved",
            },
            "runtimeActivationStatus": "levelScriptActionExecutionNotObserved",
            "sourceRefs": [
                value for value in (
                    invocation.get("sourcePath"),
                    invocation.get("levelScriptId"),
                    voice_id,
                    media.get("audioDialogPath") if media else "",
                ) if value
            ],
        })
    return contexts


def _build_gameplay_config_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose owner-unresolved SkillData/BuffData audio references.

    The exact MemoryPack string boundary and source object identify an authored
    gameplay-config request. They do not identify its still-undecoded member,
    runtime actor, activation condition, or live Event execution.
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
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(raw_context, dict)
                or raw_context.get("kind") != "gameplayConfigAudioReference"
            ):
                continue
            config_kind = str(raw_context.get("configKind") or "")
            config_id = str(raw_context.get("configId") or "")
            source_refs = [
                str(value)
                for value in raw_context.get("triggerSourcePaths") or []
                if str(value)
            ]
            contexts.append({
                "triggerId": (
                    f"gameplayConfigAudio:{config_kind}:{config_id}:"
                    f"{occurrence_index}:{event_id}"
                ),
                "semanticKind": "gameplayConfigAudioReference",
                "triggerRole": "authoredGameplayConfigAudioReference",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "configKind": config_kind,
                    "configId": config_id,
                },
                "meaning": {
                    key: event.get(key)
                    for key in (
                        "id", "name", "hash", "category", "foundInWwise",
                        "playbackRole", "possibleMediaCount",
                    )
                    if event.get(key) not in (None, "", [])
                },
                "action": {
                    "runtimeActivationStatus": "configRuntimeExecutionNotObserved",
                },
                "owner": {
                    "configKind": config_kind,
                    "configId": config_id,
                    "ownerStatus": "gameplayOwnerUnresolved",
                },
                "selection": {
                    "triggerBindingStatus": "exactMemoryPackLengthPrefixedAudioEventString",
                    "memberFieldStatus": "undecodedConfigMember",
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates"
                        if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactMemoryPackLengthPrefixedAudioEventString",
                    "owner": "exactGameplayConfigBinaryOwnerUnresolved",
                    "media": (
                        "wwiseEventMediaCandidate"
                        if media_refs
                        else "noDecodedMediaLeaf"
                    ),
                    "runtimeExecution": "configRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "configRuntimeExecutionNotObserved",
                "sourceRefs": source_refs,
            })
    return contexts


def _build_ability_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact SkillData response-trigger actions without inventing playback."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(context, dict)
                or context.get("kind") != "abilityVoiceTriggerAction"
            ):
                continue
            contexts.append({
                "triggerId": (
                    f"abilityVoiceTrigger:{context.get('configId')}:"
                    f"{context.get('actionOffsetHex')}:{event_id}"
                ),
                "semanticKind": "abilityVoiceTriggerAction",
                "triggerRole": "authoredAbilityVoiceResponseTrigger",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "ownerId": context.get("ownerId"),
                    "configId": context.get("configId"),
                    "triggerKey": context.get("triggerKey"),
                    "speakerType": context.get("speakerType"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "eventSelectionStatus": context.get("eventSelectionStatus"),
                },
                "action": {
                    "action": "VoiceTriggerAction",
                    "unionTag": context.get("actionUnionTag"),
                    "serializedMemberCount": context.get("serializedMemberCount"),
                    "canInterruptTimeMs": context.get("canInterruptTimeMs"),
                    "serverActionIndex": context.get("serverActionIndex"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "configKind": context.get("configKind"),
                    "configId": context.get("configId"),
                    "ownerId": context.get("ownerId"),
                    "sourcePath": context.get("sourcePath"),
                    "sourceSha256": context.get("sourceSha256"),
                    "actionOffset": context.get("actionOffset"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "eventSelectionStatus": context.get("eventSelectionStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": (
                        "responsiveRuntimeSelectionUnobserved"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactSkillDataAbilityActionRecord",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": context.get("sourcePaths") or [],
            })
    return contexts


def _build_responsive_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose authored ResponsiveDialog choices as possible trigger rows."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") not in {
                "responsiveDialogVoice", "responsiveDialogToneVariant",
            }:
                continue
            is_tone_variant = context.get("kind") == "responsiveDialogToneVariant"
            source_path = str(context.get("responsiveSource") or context.get("source") or "")
            tone_source_path = str(context.get("toneSource") or "")
            source_layer = (
                "Persistent" if "/Persistent/" in source_path
                else "StreamingAssets" if "/StreamingAssets/" in source_path
                else "unknown"
            )
            tone_source_layer = (
                "Persistent" if "/Persistent/" in tone_source_path
                else "StreamingAssets" if "/StreamingAssets/" in tone_source_path
                else "none"
            )
            contexts.append({
                "triggerId": (
                    f"responsiveVoice:{source_layer}:{tone_source_layer}:"
                    f"{context.get('sentenceType')}:"
                    f"{context.get('speakerId')}:{context.get('triggerKey')}:"
                    f"{context.get('responseIndex')}:"
                    f"{context.get('variantIndex') if is_tone_variant else 'base'}:{event_id}"
                ),
                "semanticKind": str(context.get("kind")),
                "triggerRole": (
                    "authoredResponsiveToneVariantCandidate"
                    if is_tone_variant else "authoredResponsiveVoiceCandidate"
                ),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "sentenceType": context.get("sentenceType"),
                    "speakerId": context.get("speakerId"),
                    "triggerKey": context.get("triggerKey"),
                    "triggerTypeId": context.get("triggerTypeId"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "responseWeight": context.get("responseWeight"),
                    "baseVoiceId": context.get("baseVoiceId"),
                    "variantVoiceId": context.get("variantVoiceId"),
                    "variantIndex": context.get("variantIndex"),
                },
                "action": {
                    "responseIndex": context.get("responseIndex"),
                    "voiceId": context.get("voiceId"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                    "aiBarkRequests": context.get("aiBarkRequests") or [],
                    "aiBarkRuntimeStatus": context.get("aiBarkRuntimeStatus"),
                    "enemyTriggerVoiceAction": context.get("enemyTriggerVoiceAction"),
                    "enemyTriggerVoiceActionStatus": context.get(
                        "enemyTriggerVoiceActionStatus"
                    ),
                },
                "owner": {
                    "table": "ResponsiveDialog",
                    "source": source_path,
                    "sourcePath": source_path,
                    "sourceLayer": source_layer,
                    "toneSource": tone_source_path,
                    "toneSourceLayer": tone_source_layer,
                    "speakerId": context.get("speakerId"),
                    "aiBarkSources": sorted({
                        str(source)
                        for request in context.get("aiBarkRequests") or []
                        if isinstance(request, dict)
                        for source in request.get("sources") or []
                        if str(source)
                    }),
                },
                "selection": {
                    "triggerBindingStatus": (
                        "exactResponsiveDialogResponseVoiceIdComposedWithExactAudioVoToneVariantVoiceId"
                        if is_tone_variant else "exactResponsiveDialogResponseVoiceId"
                    ),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "aiBark": (
                        "exactAIBarkRowTriggerKeyAndFingerprintLockedNativeDispatch"
                        if context.get("aiBarkRequests") else None
                    ),
                    "enemyTriggerVoiceAction": (
                        "exactCurrentBinaryVoiceTypeToTriggerKeyDictionaryAndResponseOnEntityCall"
                        if context.get("enemyTriggerVoiceAction") else None
                    ),
                    "owner": (
                        "exactResponsiveDialogSpeakerTriggerAndAudioVoToneVariantComposition"
                        if is_tone_variant
                        else "exactResponsiveDialogSpeakerTriggerResponseMembership"
                    ),
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": "liveResponseSelectionUnobserved",
                },
                "runtimeActivationStatus": "liveResponseSelectionUnobserved",
                "sourceRefs": [value for value in (source_path, tone_source_path) if value],
            })
    return contexts


def _build_native_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "nativeVoiceTriggerCallsite":
                continue
            contexts.append({
                "triggerId": f"nativeVoiceTrigger:{context.get('triggerKey')}:{event_id}",
                "semanticKind": "nativeVoiceTriggerCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "triggerKey": context.get("triggerKey"),
                    "targetBinding": context.get("targetBinding"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "runtimeRoute": context.get("runtimeRoute"),
                    "literalLoadVa": context.get("literalLoadVa"),
                    "playbackCall": context.get("playbackCall"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "methodIndex": context.get("methodIndex"),
                    "methodVa": context.get("methodVa"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactCurrentBuildNativeVoiceResponseCallsite",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": [
                    value for value in (
                        context.get("methodVa"), context.get("literalLoadVa"),
                        context.get("playbackInvocationVa"),
                    ) if value
                ],
            })
    return contexts


def _build_animation_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "animationVoiceTrigger":
                continue
            contexts.append({
                "triggerId": (
                    f"animationVoice:{context.get('sourceLayer')}:"
                    f"{context.get('clip')}:{context.get('eventIndex')}:{event_id}"
                ),
                "semanticKind": "animationVoiceTrigger",
                "triggerRole": "authoredAnimationVoiceResponseTrigger",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                    "triggerKey": context.get("triggerKey"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "intParameter": context.get("intParameter"),
                },
                "action": {
                    "function": context.get("function"),
                    "eventIndex": context.get("eventIndex"),
                    "time": context.get("time"),
                    "floatParameter": context.get("floatParameter"),
                    "intParameter": context.get("intParameter"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "playbackCall": context.get("playbackCall"),
                    "playbackCallVa": context.get("playbackCallVa"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                    "ownerCandidateIds": context.get("ownerCandidateIds") or [],
                    "animationOwnerCandidateCount": context.get("animationOwnerCandidateCount"),
                    "animationOwnershipScope": context.get("animationOwnershipScope"),
                    "identityToken": context.get("identityToken"),
                    "clip": context.get("clip"),
                    "sourcePath": context.get("clipSource"),
                    "sourceLayer": context.get("sourceLayer"),
                    "methodIndex": context.get("methodIndex"),
                    "methodVa": context.get("methodVa"),
                    "additionalMethodIndex": context.get("additionalMethodIndex"),
                    "additionalMethodVa": context.get("additionalMethodVa"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactAnimationClipAndAudioDialogOwnerIdentity",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": [
                    value for value in (
                        context.get("clipSource"), context.get("methodVa"),
                        context.get("playbackInvocationVa"),
                    ) if value
                ],
            })
    return contexts


def _build_interactive_property_audio_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact InteractiveData audio-key placements without runtime guesses."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(context, dict)
                or context.get("kind") not in {
                    "interactiveComponentPropertyAudio",
                    "interactivePropertyMapAudio",
                    "interactiveTemplateConfigAudio",
                    "interactiveTemplateActionAudio",
                    "interactiveEmbeddedActionAudio",
                }
            ):
                continue
            is_action = context.get("kind") in {
                "interactiveTemplateActionAudio",
                "interactiveEmbeddedActionAudio",
            }
            owner_id = str(context.get("ownerId") or "unknown")
            property_key = str(
                context.get("audioPropertyKey")
                or context.get("audioSourceField")
                or "unknown"
            )
            contexts.append({
                "triggerId": (
                    f"{'interactiveActionAudio' if is_action else 'interactivePropertyAudio'}:"
                    f"{owner_id}:{property_key}:"
                    f"{occurrence_index}:{event_id}"
                ),
                "semanticKind": str(context.get("kind")),
                "triggerRole": (
                    "authoredInteractiveActionAudioRequest"
                    if is_action
                    else "authoredInteractiveAudioProperty"
                ),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "contextKind": "InteractiveData",
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": owner_id,
                    "audioPropertyKey": property_key,
                    "audioAction": context.get("audioAction"),
                    "audioActionRole": context.get("audioActionRole"),
                    "actionLocalId": context.get("actionLocalId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "action": context.get("audioAction"),
                    "role": context.get("audioActionRole"),
                    "sourceField": context.get("audioSourceField"),
                    "actionMapRole": context.get("actionMapRole"),
                    "localId": context.get("actionLocalId"),
                    "uid": context.get("actionUid"),
                    "nextId": context.get("actionNextId"),
                    "unionTag": context.get("actionUnionTag"),
                    "stopOnRelease": context.get("stopOnRelease"),
                    "targetBindingKind": context.get("targetBindingKind"),
                    "targetParamSource": context.get("targetParamSource"),
                    "targetParameterKind": context.get("targetParameterKind"),
                    "runtimeActivationStatus": (
                        "runtimeActionActivationUnobserved"
                        if is_action
                        else "runtimePropertyConsumerUnresolved"
                    ),
                },
                "owner": {
                    "ownerId": owner_id,
                    "componentType": context.get("componentType"),
                    "componentTag": context.get("componentTag"),
                    "componentResolutionStatus": context.get("componentResolutionStatus"),
                    "interactiveTemplatePath": context.get("interactiveTemplatePath"),
                    "templateAssociationStatus": context.get("templateAssociationStatus"),
                    "propertyMapOffset": context.get("propertyMapOffset"),
                    "audioPropertyKey": property_key,
                    "sourceOffset": context.get("sourceOffset"),
                    "actionRecordOffset": context.get("actionRecordOffset"),
                    "actionPayloadOffset": context.get("actionPayloadOffset"),
                    "actionMapOffset": context.get("actionMapOffset"),
                },
                "selection": {
                    "triggerBindingStatus": str(context.get("evidence")),
                    "memberFieldStatus": (
                        "exactActionListAndTypedAudioActionEventField"
                        if is_action
                        else "exactDynamicPropertyKeyAndEventValue"
                    ),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": "runtimeEventPostingNotObserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": (
                        "exactInteractiveDataTemplateActionMapMembership"
                        if is_action
                        else "exactInteractiveDataTemplateAndComponentProperty"
                    ),
                    "media": "wwiseEventMediaCandidate" if media_refs else "noDecodedMediaLeaf",
                    "runtimeExecution": (
                        "runtimeActionActivationTargetResolutionAndEventPostingNotObserved"
                        if is_action
                        else "runtimePropertyConsumerAndEventPostingNotObserved"
                    ),
                },
                "runtimeActivationStatus": (
                    "runtimeActionActivationUnobserved"
                    if is_action
                    else "runtimePropertyConsumerUnresolved"
                ),
                "sourceRefs": [
                    value for value in context.get("sourcePaths") or []
                    if isinstance(value, str) and value
                ],
            })
    return contexts


def _build_mono_behaviour_audio_id_trigger_contexts(
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
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            )
            if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") != "monoBehaviourAudioIdField":
                continue
            serialized_file = str(context.get("serializedFile") or "unknown")
            path_id = context.get("pathId")
            field_path = str(context.get("serializedFieldPath") or "")
            trigger_id = ":".join((
                "mono-behaviour-audio-id",
                event_id,
                str(context.get("sourceRoot") or "unknown"),
                serialized_file,
                str(path_id if path_id is not None else occurrence_index),
                hashlib.sha1(field_path.encode("utf-8")).hexdigest()[:12],
            ))
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": context.get("authoredFieldRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "componentName": context.get("componentName"),
                    "gameObjectName": context.get("gameObjectName"),
                    "serializedFieldPath": field_path,
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "triggerRole": context.get("authoredFieldRole"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "sourceRoot", "serializedFile", "sourceAssetFile", "sourceOffset",
                        "pathId", "componentName", "scriptPathId", "scriptFullName",
                        "gameObjectName", "worldPositionStatus", "managedReferenceClass",
                        "managedReferenceNamespace", "managedReferenceAssembly",
                        "managedReferenceLayout", "managedReferencePayloadLength",
                        "managedReferenceDecodeStatus",
                    )
                    if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactSerializedAudioIdField",
                    "mediaSelectionStatus": "wwiseSelectionUnobserved",
                    "runtimeSelectionStatus": "componentStateOrCallbackExecutionNotObserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactSerializedMonoBehaviourAndSceneContext",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "monoBehaviourComponentExecutionNotObserved",
                    "requestEvidence": context.get("triggerRequestEvidence") or [],
                },
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                "sourceRefs": [
                    value for value in (
                        context.get("objectIndexSource"),
                        context.get("sourceAssetFile"),
                        field_path,
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts


def _build_audio_global_config_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact global lifecycle AudioId placements in the trigger catalog."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") != "audioGlobalConfigEventHash":
                continue
            field_path = str(context.get("path") or "")
            contexts.append({
                "triggerId": ":".join((
                    "audio-global-config",
                    event_id,
                    str(context.get("sourceRoot") or "unknown"),
                    str(context.get("pathId") or occurrence_index),
                    hashlib.sha1(field_path.encode("utf-8")).hexdigest()[:12],
                )),
                "semanticKind": "audioGlobalConfigEventHash",
                "triggerRole": context.get("semanticRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "serializedFieldPath": field_path,
                    "stateDirection": context.get("stateDirection"),
                    "audioStateMask": context.get("audioStateMask"),
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "triggerRole": context.get("semanticRole"),
                    "runtimeActivationStatus": "runtimeLifecycleConditionRequired",
                },
                "owner": {
                    key: context[key]
                    for key in ("sourceRoot", "serializedFile", "pathId", "table")
                    if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactSerializedGlobalAudioPolicyAudioId",
                    "mediaSelectionStatus": "wwiseSelectionUnobserved",
                    "runtimeSelectionStatus": "runtimeLifecycleConditionRequired",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactSerializedAudioGlobalConfigField",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeLifecycleConditionRequired",
                    "requestEvidence": context.get("triggerRequestEvidence") or [],
                },
                "runtimeActivationStatus": "runtimeLifecycleConditionRequired",
                "sourceRefs": [
                    value for value in (context.get("source"), field_path)
                    if isinstance(value, str) and value
                ],
            })
    return contexts


def _build_managed_literal_callsite_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose fingerprint-locked managed native playback callsites."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "binaryManagedLiteralCallsite":
                continue
            contexts.append({
                "triggerId": ":".join((
                    "managed-audio-callsite",
                    event_id,
                    str(context.get("methodIndex") or "unknown"),
                    str(context.get("playbackCallVa") or "unknown"),
                )),
                "semanticKind": "binaryManagedLiteralCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                    "triggerRole": context.get("triggerRole"),
                    "targetBinding": context.get("targetBinding"),
                    "branchCondition": context.get("branchCondition"),
                    "selectorType": context.get("selectorType"),
                    "selectorMethod": context.get("selectorMethod"),
                    "selectorMethodIndex": context.get("selectorMethodIndex"),
                    "selectorMethodVa": context.get("selectorMethodVa"),
                    "selectorCallVa": context.get("selectorCallVa"),
                    "selectorLoadVa": context.get("selectorLoadVa"),
                    "selectorField": context.get("selectorField"),
                    "selectorFieldOffset": context.get("selectorFieldOffset"),
                    "additionalConsumerMethod": context.get("additionalConsumerMethod"),
                    "additionalMethodVa": context.get("additionalMethodVa"),
                    "additionalSelectorLoadVa": context.get("additionalSelectorLoadVa"),
                    "additionalSelectorCallVa": context.get("additionalSelectorCallVa"),
                    "additionalPlaybackCallVa": context.get("additionalPlaybackCallVa"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "playbackCall": context.get("playbackCall"),
                    "playbackCallVa": context.get("playbackCallVa"),
                    "playbackParameter": context.get("playbackParameter"),
                    "literalArgumentRegister": context.get("literalArgumentRegister"),
                    "literalArgumentInstruction": context.get("literalArgumentInstruction"),
                    "playbackHashCall": context.get("playbackHashCall"),
                    "playbackHashCallVa": context.get("playbackHashCallVa"),
                    "playbackHashInvocationVa": context.get("playbackHashInvocationVa"),
                    "playbackSink": context.get("playbackSink"),
                    "playbackSinkVa": context.get("playbackSinkVa"),
                    "playbackSinkInvocationVa": context.get("playbackSinkInvocationVa"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "consumerType", "consumerMethod", "methodIndex", "methodVa",
                        "literalLoadVa", "metadataSha256", "gameAssemblySha256",
                    ) if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactCurrentBuildManagedNativePlaybackCallsite",
                    "mediaSelectionStatus": "wwiseEventMediaCandidates",
                    "runtimeSelectionStatus": "runtimeBranchExecutionUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactManagedMethodAndLiteralHandleXref",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeBranchExecutionUnobserved",
                },
                "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                "sourceRefs": [
                    value for value in (
                        context.get("source"), context.get("methodVa"),
                        context.get("selectorMethodVa"), context.get("selectorLoadVa"),
                        context.get("selectorCallVa"), context.get("additionalMethodVa"),
                        context.get("additionalSelectorLoadVa"), context.get("additionalSelectorCallVa"),
                        context.get("literalLoadVa"), context.get("playbackCallVa"),
                        context.get("additionalPlaybackCallVa"),
                        context.get("playbackInvocationVa"), context.get("playbackSinkInvocationVa"),
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts


def _build_native_custom_state_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact native custom-state calls joined to authored Events."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "nativeCustomStateCallsite":
                continue
            callsite = str(context.get("callsiteVa") or "unknown")
            contexts.append({
                "triggerId": ":".join((
                    "native-custom-state",
                    event_id,
                    str(context.get("methodIndex") or "unknown"),
                    callsite,
                )),
                "semanticKind": "nativeCustomStateCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                    "triggerRole": context.get("triggerRole"),
                    "customStateName": context.get("customStateName"),
                    "switchMethod": context.get("switchMethod"),
                    "switchMethodVa": context.get("switchMethodVa"),
                    "branchCondition": context.get("branchCondition"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "switchMethod": context.get("switchMethod"),
                    "switchMethodVa": context.get("switchMethodVa"),
                    "customStateName": context.get("customStateName"),
                    "staticArgumentVa": context.get("staticArgumentVa"),
                    "metadataUsageWord": context.get("metadataUsageWord"),
                    "metadataStringLiteralIndex": context.get("metadataStringLiteralIndex"),
                    "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "consumerType", "consumerMethod", "methodIndex", "methodVa",
                        "callsiteVa", "staticArgumentVa", "metadataSha256", "gameAssemblySha256",
                    ) if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactCurrentBuildNativeCustomStateCallsite",
                    "mediaSelectionStatus": "wwiseEventMediaCandidates",
                    "runtimeSelectionStatus": "runtimeBranchExecutionUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactNativeSwitchAudioCustomStateCallsiteAndAuthoredInteractiveConfig",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeBranchExecutionUnobserved",
                },
                "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                "sourceRefs": [
                    value for value in (
                        context.get("source"), context.get("methodVa"),
                        context.get("callsiteVa"), context.get("staticArgumentVa"),
                        context.get("switchMethodVa"),
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts


def build_trigger_context_catalog(
    event_rows: Iterable[dict[str, Any]],
    media_rows: Iterable[dict[str, Any]],
    webui_root: Path,
    language: str,
    export_root: Path | None = None,
    levelscript_semantics: dict[str, Any] | None = None,
    mono_behaviour_audio_id_contexts: dict[str, list[dict[str, Any]]] | None = None,
    model_view_semantics: dict[str, Any] | None = None,
    native_context: native_evidence.NativeAudioEvidence | None = None,
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
    mono_event_rows: list[dict[str, Any]] = []
    events_by_hash = {
        int(event["hash"]) & 0xFFFFFFFF: event
        for event in event_rows
        if isinstance(event, dict) and isinstance(event.get("hash"), int)
    }
    for context_key, rows in (mono_behaviour_audio_id_contexts or {}).items():
        match = re.fullmatch(r"#0x([0-9a-fA-F]{8})", str(context_key))
        if not match:
            continue
        event = events_by_hash.get(int(match.group(1), 16))
        if not isinstance(event, dict):
            continue
        mono_event_rows.append({**event, "contexts": list(rows or [])})
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
        "levelScriptVoice": _build_levelscript_voice_trigger_contexts(
            media_rows,
            (levelscript_semantics or {}).get("voiceInvocations") or [],
        ),
        "timelineAudio": _build_timeline_trigger_contexts(event_rows),
        "luaPostEvent": _build_lua_post_event_trigger_contexts(event_rows),
        "gameplayConfigAudio": _build_gameplay_config_trigger_contexts(event_rows),
        "abilityVoiceTrigger": _build_ability_voice_trigger_contexts(event_rows),
        "responsiveVoiceTrigger": _build_responsive_voice_trigger_contexts(event_rows),
        "nativeVoiceTrigger": _build_native_voice_trigger_contexts(event_rows),
        "animationVoiceTrigger": _build_animation_voice_trigger_contexts(event_rows),
        "interactivePropertyAudio": _build_interactive_property_audio_trigger_contexts(event_rows),
        "managedLiteralCallsite": _build_managed_literal_callsite_trigger_contexts(event_rows),
        "nativeCustomStateCallsite": _build_native_custom_state_trigger_contexts(event_rows),
        "monoBehaviourAudioId": _build_mono_behaviour_audio_id_trigger_contexts(
            mono_event_rows or event_rows
        ),
        "audioGlobalConfig": _build_audio_global_config_trigger_contexts(event_rows),
        "modelViewStateAudio": model_view_projection.project_model_view_state_audio_trigger_contexts(
            model_view_semantics,
            event_rows,
            native_context=native_context,
        ),
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
        "gameplayConfigAudio": {
            "source": "exact MemoryPack length-prefixed au_* strings in SkillData/BuffData",
            "storedTriggerContextRows": len(grouped["gameplayConfigAudio"]),
            "runtimeExecutionObserved": 0,
            "ownerStatus": "gameplayOwnerUnresolved",
        },
        "abilityVoiceTrigger": {
            "source": "exact SkillData AbilityActionData VoiceTriggerAction records",
            "storedTriggerContextRows": len(grouped["abilityVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "responsiveRuntimeSelectionUnobserved",
        },
        "nativeVoiceTrigger": {
            "source": "fingerprint-locked current metadata literal handles and GameAssembly voice response callsites",
            "storedTriggerContextRows": len(grouped["nativeVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "speakerCooldownProbabilityToneAndLiveChoiceUnobserved",
        },
        "responsiveVoiceTrigger": {
            "source": "merged StreamingAssets/Persistent ResponsiveDialog response arrays plus exact AudioVoTone compositions",
            "storedTriggerContextRows": len(grouped["responsiveVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "probabilityCooldownBandLimitToneAndLiveChoiceUnobserved",
        },
        "monoBehaviourAudioId": {
            "source": "AnimeStudio MonoBehaviour object-index exact AudioId scalar paths",
            "storedTriggerContextRows": len(grouped["monoBehaviourAudioId"]),
            "runtimeExecutionObserved": 0,
        },
        "audioGlobalConfig": {
            "source": "AudioGlobalConfig raw JSON or complete MonoBehaviour object index",
            "storedTriggerContextRows": len(grouped["audioGlobalConfig"]),
            "runtimeExecutionObserved": 0,
        },
        "modelViewStateAudio": {
            "source": "ModelViewStateControllerData tag-0x0001 normal Event plus tag-0x0002 positioned direct/control branches",
            "storedTriggerContextRows": len(grouped["modelViewStateAudio"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "wwiseEventAndPositionedBranchSelectionUnobserved",
            "ownerStatus": "modelViewStateControllerOwnerOnlyInteractiveAssociationNotOwner",
            "nativeRouteStatus": (
                "exactCurrentBuildPositionedAndNormalRoutes"
                if any(row.get("nativeRoute") for row in grouped["modelViewStateAudio"])
                else "nativeRouteUnavailable"
            ),
            "positionedDirectEventRows": sum(
                row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                for row in grouped["modelViewStateAudio"]
                if isinstance(row, dict)
            ),
            "positionedEndpointAuditStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("endpointAuditStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedPostAndForgetToAudioAdapterConnectionStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("postAndForgetToAudioAdapterConnectionStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unresolved",
            ),
            "positionedPostEventRuntimeStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("postEventRuntimeStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedAsyncBoundaryStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("asyncBoundaryStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedAudioHandleWriteStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("fieldContract", {}).get("audioHandleWrite", {}).get("status")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedControlRows": sum(
                str(row.get("semanticKind") or "").startswith("modelViewStatePositioned")
                and row.get("semanticKind") != "modelViewStatePositionAudioEvent"
                for row in grouped["modelViewStateAudio"]
                if isinstance(row, dict)
            ),
        },
        "managedLiteralCallsite": {
            "source": "fingerprint-locked current metadata literal handles and GameAssembly native callsites",
            "storedTriggerContextRows": len(grouped["managedLiteralCallsite"]),
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
        "levelScriptVoice": {
            "source": "LevelScript PlayVoice/PlayVoiceNarrative constant _voId",
            "storedTriggerContextRows": len(grouped["levelScriptVoice"]),
            "rowsWithExactAudioDialogMedia": sum(
                row.get("selection", {}).get("voiceSelectionStatus")
                == "exactAudioDialogPathStem"
                for row in grouped["levelScriptVoice"]
                if isinstance(row, dict)
            ),
            "wwiseEventStatus": "notApplicable",
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
            "PostEvent or an audible media leaf. ModelView normal Event rows keep the "
            "serialized definition, possible Wwise media leaves, unresolved runtime branch, "
            "and unobserved activation as separate evidence fields; InteractiveTable "
            "associations are not promoted to owners."
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
        callsite_contexts = MANAGED_AUDIO_CALLSITE_CONTEXTS
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








def _media_route_marker(media: dict[str, Any]) -> str:
    return str(
        media.get("src")
        or media.get("rel")
        or media.get("mediaId")
        or media.get("id")
        or ""
    )


def _media_post_process_routes(
    events: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Project exact Event output-bus paths onto their possible media leaves.

    The serialized Wwise graph proves that an Event branch reaches the listed
    output bus.  It does not prove which random/switch/sequence branch was
    selected at runtime, so this projection remains a possible-route summary.
    Bus definitions stay in the top-level HIRC catalog; media rows carry only
    stable IDs and resolution statuses to avoid duplicating plug-in payloads.
    The compact State/RTPC rows below are the exception: they preserve the
    authored control shape that explains a media leaf's processing without
    copying the full Event evidence graph.
    """

    by_marker: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        selection_status = str(event.get("runtimeSelection") or "unresolved")
        for candidate in event.get("media") or ():
            if not isinstance(candidate, dict):
                continue
            marker = _media_route_marker(candidate)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "routeKeys": set(),
                "busPaths": set(),
                "outputBusIds": set(),
                "effectBusIds": set(),
                "unresolvedBusIds": set(),
                "selectionStatuses": set(),
                "routeStatuses": set(),
                "evidenceKeys": set(),
                "parsedNodeCount": 0,
                "outputBusNodeCount": 0,
                "directEffects": {},
                "directEffectOccurrences": 0,
                "rtpcControls": {},
                "stateControls": {},
                "stateGroupIds": set(),
                "auxSends": {},
                "auxSendOccurrences": 0,
                "auxBusRoutes": {},
                "properties": {},
                "propertyOccurrences": 0,
                "rangedProperties": {},
                "rangedPropertyOccurrences": 0,
                "mediaRelationTypes": set(),
                "mediaSelectionPaths": set(),
                "mediaRootActionIds": set(),
            })
            target["selectionStatuses"].add(selection_status)
            # ``wwiseMediaEvidence`` is copied from the typed HIRC traversal
            # and retains the exact edge shape to this leaf.  Project only the
            # compact relation/path identity here; full container payloads
            # remain lazy Event-detail evidence.
            for media_evidence in candidate.get("wwiseMediaEvidence") or ():
                if not isinstance(media_evidence, dict):
                    continue
                target["mediaRelationTypes"].update(
                    str(value)
                    for value in media_evidence.get("relationTypes") or ()
                    if str(value)
                )
                for raw_path in media_evidence.get("selectionPaths") or ():
                    if not isinstance(raw_path, (list, tuple)):
                        continue
                    path = tuple(str(value) for value in raw_path if str(value))
                    if path:
                        target["mediaSelectionPaths"].add(path)
                for value in media_evidence.get("rootActionIds") or ():
                    try:
                        target["mediaRootActionIds"].add(int(value))
                    except (TypeError, ValueError):
                        continue
            for evidence in event.get("evidence") or ():
                if not isinstance(evidence, dict):
                    continue
                post_process = evidence.get("postProcessSummary") or {}
                if not isinstance(post_process, dict):
                    continue
                try:
                    bank_id = int(evidence.get("bankId") or 0)
                except (TypeError, ValueError):
                    bank_id = 0
                target["evidenceKeys"].add((event_id, bank_id))
                target["parsedNodeCount"] += int(
                    post_process.get("parsedNodeCount") or 0
                )
                for auxiliary_bus in post_process.get("auxiliaryBuses") or ():
                    if not isinstance(auxiliary_bus, dict):
                        continue
                    aux_bus_id = str(
                        auxiliary_bus.get("busIdHex")
                        or auxiliary_bus.get("busId")
                        or ""
                    ).lower()
                    if not aux_bus_id:
                        continue
                    route = {
                        "sendKind": auxiliary_bus.get("sendKind"),
                        "busIdHex": aux_bus_id,
                        "resolutionStatus": auxiliary_bus.get("resolutionStatus"),
                        "busPathIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get("busPathIdHexes") or ()
                            if str(value)
                        ][:16],
                        "busPathResolutionStatus": auxiliary_bus.get(
                            "busPathResolutionStatus"
                        ),
                        "effectBusIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get("effectBusIdHexes") or ()
                            if str(value)
                        ][:16],
                        "unresolvedBusProcessingIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get(
                                "unresolvedBusProcessingIdHexes"
                            ) or ()
                            if str(value)
                        ][:16],
                    }
                    route = {
                        key: value for key, value in route.items()
                        if value not in (None, "", [])
                    }
                    route_key = tuple(
                        (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                        for key, value in sorted(route.items())
                    )
                    target["auxBusRoutes"].setdefault(aux_bus_id, {})[
                        route_key
                    ] = route
                output_buses = list(post_process.get("outputBuses") or ())
                target["outputBusNodeCount"] += int(
                    post_process.get("outputBusNodeCount") or 0
                )
                for effect_node in post_process.get("effectNodes") or ():
                    if not isinstance(effect_node, dict):
                        continue
                    for slot in effect_node.get("effects") or ():
                        if not isinstance(slot, dict):
                            continue
                        effect_id = int(slot.get("effectId") or 0)
                        if not effect_id:
                            continue
                        target["directEffectOccurrences"] += 1
                        effect_id_hex = str(
                            slot.get("effectIdHex") or f"0x{effect_id:08x}"
                        ).lower()
                        effect_row = {
                            "effectIdHex": effect_id_hex,
                            "slotIndex": slot.get("slotIndex"),
                            "objectId": effect_node.get("objectId"),
                            "pluginName": slot.get("pluginName"),
                            "pluginClassIdHex": slot.get("pluginClassIdHex"),
                            "parameterSummary": slot.get("parameterSummary"),
                            "effectBypass": slot.get("effectBypass"),
                            "effectShareSet": slot.get("effectShareSet"),
                            "effectRendered": slot.get("effectRendered"),
                            "resolutionStatus": slot.get("resolutionStatus"),
                        }
                        effect_row = {
                            key: value for key, value in effect_row.items()
                            if value not in (None, "", [])
                        }
                        effect_key = tuple(
                            (key, str(value))
                            for key, value in sorted(effect_row.items())
                        )
                        target["directEffects"].setdefault(effect_key, effect_row)
                for property_node in post_process.get("propertyNodes") or ():
                    if not isinstance(property_node, dict):
                        continue
                    source_type = str(property_node.get("objectTypeLabel") or "")
                    for property_row in property_node.get("properties") or ():
                        if not isinstance(property_row, dict):
                            continue
                        target["propertyOccurrences"] += 1
                        property_key = tuple(
                            str(property_row.get(key) or "")
                            for key in (
                                "propertyIdHex", "propertyLabel", "rawHex",
                                "rawU32", "floatValue", "valueEncoding",
                            )
                        )
                        compact_property = target["properties"].setdefault(
                            property_key,
                            {
                                "propertyIdHex": property_row.get("propertyIdHex"),
                                "propertyLabel": property_row.get("propertyLabel"),
                                "rawHex": property_row.get("rawHex"),
                                "rawU32": property_row.get("rawU32"),
                                "floatValue": property_row.get("floatValue"),
                                "valueEncoding": property_row.get("valueEncoding"),
                                "sourceOccurrenceCount": 0,
                                "sourceObjectTypeLabels": set(),
                            },
                        )
                        compact_property["sourceOccurrenceCount"] += 1
                        if source_type:
                            compact_property["sourceObjectTypeLabels"].add(source_type)
                    for range_row in property_node.get("rangedProperties") or ():
                        if not isinstance(range_row, dict):
                            continue
                        target["rangedPropertyOccurrences"] += 1
                        range_key = tuple(
                            str(range_row.get(key) or "")
                            for key in (
                                "propertyIdHex", "propertyLabel", "minimumRawHex",
                                "maximumRawHex", "minimumFloat", "maximumFloat",
                                "valueEncoding",
                            )
                        )
                        compact_range = target["rangedProperties"].setdefault(
                            range_key,
                            {
                                "propertyIdHex": range_row.get("propertyIdHex"),
                                "propertyLabel": range_row.get("propertyLabel"),
                                "minimumRawHex": range_row.get("minimumRawHex"),
                                "minimumRawU32": range_row.get("minimumRawU32"),
                                "minimumFloat": range_row.get("minimumFloat"),
                                "maximumRawHex": range_row.get("maximumRawHex"),
                                "maximumRawU32": range_row.get("maximumRawU32"),
                                "maximumFloat": range_row.get("maximumFloat"),
                                "valueEncoding": range_row.get("valueEncoding"),
                                "sourceOccurrenceCount": 0,
                                "sourceObjectTypeLabels": set(),
                            },
                        )
                        compact_range["sourceOccurrenceCount"] += 1
                        if source_type:
                            compact_range["sourceObjectTypeLabels"].add(source_type)
                # StateChunk and InitialRTPC controls are exact serialized
                # authored values on the Event's processing nodes.  Keep a
                # bounded, deduplicated projection on each possible media
                # leaf; this is not a claim about live setters or branch
                # selection.
                for control_node in post_process.get("stateRtpcNodes") or ():
                    if not isinstance(control_node, dict):
                        continue
                    node_identity = {
                        "objectId": control_node.get("objectId"),
                        "objectType": control_node.get("objectType"),
                        "objectTypeLabel": control_node.get("objectTypeLabel"),
                    }
                    for raw_curve in control_node.get("rtpcCurves") or ():
                        if not isinstance(raw_curve, dict):
                            continue
                        points = [
                            {
                                key: point.get(key)
                                for key in (
                                    "pointIndex", "from", "to",
                                    "interpolation", "interpolationLabel",
                                )
                                if point.get(key) is not None
                            }
                            for point in (raw_curve.get("points") or ())
                            if isinstance(point, dict)
                        ]
                        point_limit = 8
                        curve_row = {
                            **node_identity,
                            "rtpcId": raw_curve.get("rtpcId"),
                            "rtpcIdHex": raw_curve.get("rtpcIdHex"),
                            "parameterId": raw_curve.get("parameterId"),
                            "parameterLabel": raw_curve.get("parameterLabel"),
                            "rtpcType": raw_curve.get("rtpcType"),
                            "rtpcTypeLabel": raw_curve.get("rtpcTypeLabel"),
                            "accum": raw_curve.get("accum"),
                            "accumLabel": raw_curve.get("accumLabel"),
                            "scaling": raw_curve.get("scaling"),
                            "scalingLabel": raw_curve.get("scalingLabel"),
                            "pointCount": raw_curve.get("pointCount")
                            if raw_curve.get("pointCount") is not None
                            else len(points),
                            "points": points[:point_limit],
                            "pointsTruncated": len(points) > point_limit,
                        }
                        curve_row = {
                            key: value for key, value in curve_row.items()
                            if value not in (None, "", [])
                        }
                        curve_key = tuple(
                            (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                            for key, value in sorted(curve_row.items())
                        )
                        target["rtpcControls"].setdefault(curve_key, curve_row)
                    for group in control_node.get("stateGroups") or ():
                        if not isinstance(group, dict):
                            continue
                        group_hex = str(
                            group.get("groupIdHex")
                            or (
                                f"0x{int(group.get('groupId')):08x}"
                                if group.get("groupId") is not None else ""
                            )
                        ).lower()
                        if group_hex:
                            target["stateGroupIds"].add(group_hex)
                        for state in group.get("states") or ():
                            if not isinstance(state, dict):
                                continue
                            for raw_value in state.get("values") or ():
                                if not isinstance(raw_value, dict):
                                    continue
                                state_row = {
                                    **node_identity,
                                    "groupId": group.get("groupId"),
                                    "groupIdHex": group_hex,
                                    "syncType": group.get("syncType"),
                                    "syncTypeLabel": group.get("syncTypeLabel"),
                                    "stateId": state.get("stateId"),
                                    "stateIdHex": state.get("stateIdHex"),
                                    "parameterId": raw_value.get("parameterId"),
                                    "parameterLabel": raw_value.get("parameterLabel"),
                                    "value": raw_value.get("value"),
                                }
                                state_row = {
                                    key: value for key, value in state_row.items()
                                    if value not in (None, "", [])
                                }
                                state_key = tuple(
                                    (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                                    for key, value in sorted(state_row.items())
                                )
                                target["stateControls"].setdefault(state_key, state_row)
                for aux_node in post_process.get("auxSendNodes") or ():
                    if not isinstance(aux_node, dict):
                        continue
                    for send in aux_node.get("userDefinedAuxSends") or ():
                        if not isinstance(send, dict):
                            continue
                        bus_id = str(
                            send.get("busIdHex") or send.get("busId") or ""
                        ).lower()
                        if not bus_id:
                            continue
                        target["auxSendOccurrences"] += 1
                        slot_index = send.get("slotIndex")
                        aux_key = (bus_id, str(slot_index or 0))
                        aux_row = target["auxSends"].setdefault(aux_key, {
                            "busIdHex": bus_id,
                            "slotIndex": slot_index,
                            "sourceObjectIds": set(),
                            "sourceObjectTypeLabels": set(),
                            "auxFlagsRawValues": set(),
                            "overrideUserDefinedAuxSends": set(),
                            "useGameDefinedAuxSends": set(),
                            "serializationStatuses": set(),
                            "gameDefinedAssignmentBoundaries": set(),
                            "rootActionIds": set(),
                        })
                        if aux_node.get("objectId") is not None:
                            aux_row["sourceObjectIds"].add(int(aux_node["objectId"]))
                        object_type_label = str(aux_node.get("objectTypeLabel") or "")
                        if object_type_label:
                            aux_row["sourceObjectTypeLabels"].add(object_type_label)
                        if aux_node.get("auxFlagsRaw") is not None:
                            aux_row["auxFlagsRawValues"].add(int(aux_node["auxFlagsRaw"]))
                        for field in (
                            "overrideUserDefinedAuxSends", "useGameDefinedAuxSends"
                        ):
                            if aux_node.get(field) is not None:
                                aux_row[field].add(bool(aux_node[field]))
                        status = str(send.get("serializationStatus") or "")
                        if status:
                            aux_row["serializationStatuses"].add(status)
                        boundary = str(
                            aux_node.get("gameDefinedAssignmentBoundary") or ""
                        )
                        if boundary:
                            aux_row["gameDefinedAssignmentBoundaries"].add(boundary)
                        aux_row["rootActionIds"].update(
                            int(value)
                            for value in aux_node.get("rootActionIds") or ()
                            if isinstance(value, int)
                        )
                if output_buses:
                    target["routeStatuses"].add("exactSerializedOutputBusPath")
                elif int(post_process.get("outputBusNodeCount") or 0) > 0:
                    target["routeStatuses"].add("outputBusNodeUnresolved")
                elif post_process.get("parserStatus"):
                    target["routeStatuses"].add("noExplicitOutputBusSerialized")
                for bus in output_buses:
                    if not isinstance(bus, dict):
                        continue
                    path = tuple(
                        str(value).lower()
                        for value in (
                            bus.get("busPathIdHexes")
                            or ([bus.get("busIdHex")] if bus.get("busIdHex") else [])
                        )
                        if str(value)
                    )
                    if not path:
                        continue
                    route_key = (event_id, bank_id, path)
                    target["routeKeys"].add(route_key)
                    target["busPaths"].add(path)
                    output_bus = str(bus.get("busIdHex") or "").lower()
                    if output_bus:
                        target["outputBusIds"].add(output_bus)
                    target["effectBusIds"].update(
                        str(value).lower()
                        for value in bus.get("effectBusIdHexes") or ()
                        if str(value)
                    )
                    target["unresolvedBusIds"].update(
                        str(value).lower()
                        for value in bus.get("unresolvedBusProcessingIdHexes") or ()
                        if str(value)
                    )

    output: dict[str, dict[str, Any]] = {}
    for marker, row in by_marker.items():
        paths = sorted(row["busPaths"])
        direct_effects = sorted(
            row["directEffects"].values(),
            key=lambda value: (
                str(value.get("pluginName") or ""),
                str(value.get("effectIdHex") or ""),
                int(value.get("objectId") or 0),
                int(value.get("slotIndex") or 0),
                str(value.get("parameterSummary") or ""),
            ),
        )
        rtpc_controls = sorted(
            row["rtpcControls"].values(),
            key=lambda value: (
                str(value.get("parameterLabel") or ""),
                str(value.get("rtpcIdHex") or ""),
                int(value.get("objectId") or 0),
                int(value.get("parameterId") or 0),
            ),
        )
        state_controls = sorted(
            row["stateControls"].values(),
            key=lambda value: (
                str(value.get("groupIdHex") or ""),
                str(value.get("stateIdHex") or ""),
                str(value.get("parameterLabel") or ""),
                int(value.get("objectId") or 0),
            ),
        )
        aux_sends = sorted(
            row["auxSends"].values(),
            key=lambda value: (
                str(value.get("busIdHex") or ""),
                int(value.get("slotIndex") or 0),
            ),
        )
        properties = sorted(
            row["properties"].values(),
            key=lambda value: (
                str(value.get("propertyLabel") or ""),
                str(value.get("propertyIdHex") or ""),
                str(value.get("rawHex") or ""),
            ),
        )
        ranged_properties = sorted(
            row["rangedProperties"].values(),
            key=lambda value: (
                str(value.get("propertyLabel") or ""),
                str(value.get("propertyIdHex") or ""),
                str(value.get("minimumRawHex") or ""),
                str(value.get("maximumRawHex") or ""),
            ),
        )
        compact_properties = []
        for property_row in properties:
            compact = {
                key: value for key, value in property_row.items()
                if key not in {"sourceObjectTypeLabels", "rawU32"}
            }
            # Float values are already losslessly represented by the decoded
            # scalar plus encoding tag; retain rawHex for ID/typed-union rows.
            if compact.get("valueEncoding") == "float":
                compact.pop("rawHex", None)
            compact_properties.append(compact)
        compact_ranges = [
            {
                key: value for key, value in range_row.items()
                if key not in {
                    "sourceObjectTypeLabels", "minimumRawU32", "maximumRawU32"
                }
            }
            for range_row in ranged_properties
        ]
        compact_aux_sends = []
        for aux in aux_sends:
            bus_routes = sorted(
                row["auxBusRoutes"].get(aux["busIdHex"], {}).values(),
                key=lambda value: (
                    str(value.get("busPathIdHexes") or []),
                    str(value.get("resolutionStatus") or ""),
                ),
            )
            compact_aux_sends.append({
                "busIdHex": aux["busIdHex"],
                "slotIndex": aux.get("slotIndex"),
                "sourceObjectCount": len(aux["sourceObjectIds"]),
                "sourceObjectIds": sorted(aux["sourceObjectIds"])[:8],
                "sourceObjectIdsTruncated": len(aux["sourceObjectIds"]) > 8,
                "sourceObjectTypeLabels": sorted(aux["sourceObjectTypeLabels"])[:8],
                "auxFlagsRawValues": sorted(aux["auxFlagsRawValues"]),
                "overrideUserDefinedAuxSends": sorted(
                    aux["overrideUserDefinedAuxSends"]
                ),
                "useGameDefinedAuxSends": sorted(aux["useGameDefinedAuxSends"]),
                "serializationStatuses": sorted(aux["serializationStatuses"]),
                "gameDefinedAssignmentBoundaries": sorted(
                    aux["gameDefinedAssignmentBoundaries"]
                ),
                "rootActionIds": sorted(aux["rootActionIds"])[:8],
                "rootActionIdsTruncated": len(aux["rootActionIds"]) > 8,
                "busRoutes": bus_routes[:4],
                "busRoutesTruncated": len(bus_routes) > 4,
            })
        media_relation_types = sorted(row["mediaRelationTypes"])
        media_selection_paths = sorted(row["mediaSelectionPaths"])
        media_root_action_ids = sorted(row["mediaRootActionIds"])
        output[marker] = {
            "postProcessRouteCount": len(row["routeKeys"]),
            "postProcessBusPathCount": len(paths),
            "postProcessBusPaths": [list(path) for path in paths[:32]],
            "postProcessBusPathsTruncated": len(paths) > 32,
            "postProcessOutputBusIds": sorted(row["outputBusIds"]),
            "postProcessEffectBusIds": sorted(row["effectBusIds"]),
            "postProcessUnresolvedBusProcessingIds": sorted(row["unresolvedBusIds"]),
            "postProcessSelectionStatuses": sorted(row["selectionStatuses"]),
            "postProcessRouteStatuses": sorted(row["routeStatuses"]),
            "postProcessEvidenceEventCount": len(row["evidenceKeys"]),
            "postProcessParsedNodeCount": row["parsedNodeCount"],
            "postProcessOutputBusNodeCount": row["outputBusNodeCount"],
            "postProcessDirectEffectCount": len(direct_effects),
            "postProcessDirectEffects": direct_effects[:32],
            "postProcessDirectEffectsTruncated": len(direct_effects) > 32,
            "postProcessDirectEffectOccurrences": row["directEffectOccurrences"],
            "postProcessDirectEffectEvidence": (
                "exactSerializedEventNodeEffectJoin"
                if direct_effects else None
            ),
            "postProcessRtpcControlCount": len(rtpc_controls),
            "postProcessRtpcControls": rtpc_controls[:32],
            "postProcessRtpcControlsTruncated": len(rtpc_controls) > 32,
            "postProcessStateGroupIds": sorted(row["stateGroupIds"]),
            "postProcessStateControlCount": len(state_controls),
            "postProcessStateControls": state_controls[:32],
            "postProcessStateControlsTruncated": len(state_controls) > 32,
            "postProcessControlEvidence": (
                "exactSerializedEventNodeStateRtpcJoin"
                if rtpc_controls or state_controls else None
            ),
            "postProcessAuxSendCount": len(aux_sends),
            "postProcessAuxSends": compact_aux_sends[:32],
            "postProcessAuxSendsTruncated": len(aux_sends) > 32,
            "postProcessAuxSendOccurrences": row["auxSendOccurrences"],
            "postProcessAuxSendEvidence": (
                "exactSerializedEventNodeUserDefinedAuxSendJoin"
                if aux_sends else None
            ),
            "postProcessPropertyCount": len(properties),
            "postProcessProperties": compact_properties[:32],
            "postProcessPropertiesTruncated": len(properties) > 32,
            "postProcessPropertyOccurrences": row["propertyOccurrences"],
            "postProcessRangeCount": len(ranged_properties),
            "postProcessRanges": compact_ranges[:32],
            "postProcessRangesTruncated": len(ranged_properties) > 32,
            "postProcessRangeOccurrences": row["rangedPropertyOccurrences"],
            "postProcessPropertyEvidence": (
                "exactSerializedEventNodePropertyJoin"
                if properties or ranged_properties else None
            ),
            "wwiseMediaRelationTypes": media_relation_types[:32],
            "wwiseMediaRelationTypesTruncated": len(media_relation_types) > 32,
            "wwiseMediaSelectionPathCount": len(media_selection_paths),
            "wwiseMediaSelectionPaths": [
                list(path) for path in media_selection_paths[:32]
            ],
            "wwiseMediaSelectionPathsTruncated": len(media_selection_paths) > 32,
            "wwiseMediaRootActionIds": media_root_action_ids[:32],
            "wwiseMediaRootActionIdsTruncated": len(media_root_action_ids) > 32,
            "wwiseMediaGraphEvidence": (
                "exactSerializedWwiseEventMediaJoin"
                if media_relation_types or media_selection_paths or media_root_action_ids
                else None
            ),
            "postProcessRouteEvidence": "exactSerializedEventOutputBusJoin",
        }
    return output


def annotate_media_post_process_effect_chains(
    media_rows: Iterable[dict[str, Any]],
    audio_index: dict[str, Any],
    *,
    limit: int = 64,
) -> dict[str, int]:
    """Attach a bounded authored direct-node + Bus effect chain to media.

    ``postProcessBusPaths`` are serialized from the leaf/output Bus toward its
    parent.  Direct node slots are emitted first because an Actor-Mixer/Blend
    node's own effects precede the output-bus route in the authored graph;
    Bus slots then follow each path in the serialized leaf-to-root order.
    This is a compact explanation of authored processing evidence, not a
    runtime DSP order claim: inherited platform values, live setters, branch
    selection, and audibility remain unobserved.
    """

    post_process = (audio_index.get("hircSummary") or {}).get(
        "postProcessSummary"
    ) or {}
    bus_definitions = {
        str(row.get("busIdHex") or row.get("busId") or "").lower(): row
        for row in post_process.get("busDefinitions") or ()
        if isinstance(row, dict)
        and str(row.get("busIdHex") or row.get("busId") or "")
    }

    attached = 0
    chain_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        chain: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        control_rows_by_bus: dict[str, dict[str, Any]] = {}
        duck_rows_by_bus: dict[str, dict[str, Any]] = {}

        # Direct node effects are already deduplicated and bounded on the
        # media row.  Retain node/slot identity so two authored effect nodes
        # with the same plug-in settings do not collapse together.
        direct_effects = sorted(
            (
                direct for direct in media.get("postProcessDirectEffects") or ()
                if isinstance(direct, dict)
            ),
            key=lambda direct: (
                int(direct.get("objectId") or 0),
                int(direct.get("slotIndex") or 0),
                str(direct.get("effectIdHex") or ""),
            ),
        )
        for direct in direct_effects:
            row = {
                "stage": "directNode",
                "objectId": direct.get("objectId"),
                "slotIndex": direct.get("slotIndex"),
                "effectIdHex": direct.get("effectIdHex"),
                "pluginName": direct.get("pluginName"),
                "pluginClassIdHex": direct.get("pluginClassIdHex"),
                "parameterSummary": direct.get("parameterSummary"),
                "effectBypass": direct.get("effectBypass"),
                "effectShareSet": direct.get("effectShareSet"),
                "effectRendered": direct.get("effectRendered"),
                "resolutionStatus": direct.get("resolutionStatus"),
            }
            row = {
                key: value for key, value in row.items()
                if value not in (None, "", [])
            }
            key = tuple(
                (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                for key, value in sorted(row.items())
            )
            if key not in seen:
                seen.add(key)
                chain.append(row)

        # The path list is already deterministic and serialized leaf-to-root;
        # preserve that order and the slot order inside each Bus definition.
        for path_index, raw_path in enumerate(media.get("postProcessBusPaths") or ()):
            if not isinstance(raw_path, (list, tuple)):
                continue
            for path_depth, raw_bus_id in enumerate(raw_path):
                bus_id = str(raw_bus_id or "").lower()
                if not bus_id:
                    continue
                definition = bus_definitions.get(bus_id)
                state_rtpc = (definition or {}).get("serializedStateAndRtpc") or {}
                if int((definition or {}).get("serializedDuckCount") or 0):
                    duck_row = duck_rows_by_bus.setdefault(bus_id, {
                        "busIdHex": bus_id,
                        "pathIndexes": set(),
                        "pathDepths": set(),
                        "duckCount": int((definition or {}).get("serializedDuckCount") or 0),
                        "maxDuckVolumeDb": (definition or {}).get("serializedMaxDuckVolumeDb"),
                        "ducks": list((definition or {}).get("serializedDucks") or ()),
                    })
                    duck_row["pathIndexes"].add(path_index)
                    duck_row["pathDepths"].add(path_depth)
                if (
                    int(state_rtpc.get("rtpcCurveCount") or 0)
                    or int(state_rtpc.get("stateGroupCount") or 0)
                ):
                    control_row = control_rows_by_bus.setdefault(bus_id, {
                        "busIdHex": bus_id,
                        "pathIndexes": set(),
                        "pathDepths": set(),
                        "rtpcCurveCount": int(state_rtpc.get("rtpcCurveCount") or 0),
                        "rtpcPointCount": int(state_rtpc.get("rtpcPointCount") or 0),
                        "rtpcControls": [],
                        "stateGroupCount": int(state_rtpc.get("stateGroupCount") or 0),
                        "stateCount": int(state_rtpc.get("stateCount") or 0),
                        "stateValueCount": int(state_rtpc.get("stateValueCount") or 0),
                        "stateControls": [],
                        "parserStatus": state_rtpc.get("parserStatus"),
                    })
                    control_row["pathIndexes"].add(path_index)
                    control_row["pathDepths"].add(path_depth)
                    if not control_row["rtpcControls"]:
                        for curve in state_rtpc.get("rtpcCurves") or ():
                            if not isinstance(curve, dict):
                                continue
                            points = [
                                {
                                    key: point.get(key)
                                    for key in (
                                        "pointIndex", "from", "to",
                                        "interpolation", "interpolationLabel",
                                    )
                                    if point.get(key) is not None
                                }
                                for point in (curve.get("points") or ())
                                if isinstance(point, dict)
                            ]
                            control_row["rtpcControls"].append({
                                key: value for key, value in {
                                    "rtpcIdHex": curve.get("rtpcIdHex"),
                                    "parameterId": curve.get("parameterId"),
                                    "parameterLabel": curve.get("parameterLabel"),
                                    "rtpcTypeLabel": curve.get("rtpcTypeLabel"),
                                    "accumLabel": curve.get("accumLabel"),
                                    "scalingLabel": curve.get("scalingLabel"),
                                    "pointCount": curve.get("pointCount")
                                    if curve.get("pointCount") is not None
                                    else len(points),
                                    "points": points[:8],
                                    "pointsTruncated": len(points) > 8,
                                }.items()
                                if value not in (None, "", [])
                            })
                    if not control_row["stateControls"]:
                        for group in state_rtpc.get("stateGroups") or ():
                            if not isinstance(group, dict):
                                continue
                            group_hex = str(
                                group.get("groupIdHex")
                                or group.get("groupId")
                                or ""
                            ).lower()
                            for state in group.get("states") or ():
                                if not isinstance(state, dict):
                                    continue
                                state_hex = str(
                                    state.get("stateIdHex")
                                    or state.get("stateId")
                                    or ""
                                ).lower()
                                for value in state.get("values") or ():
                                    if not isinstance(value, dict):
                                        continue
                                    control_row["stateControls"].append({
                                        key: item for key, item in {
                                            "groupIdHex": group_hex,
                                            "syncTypeLabel": group.get("syncTypeLabel"),
                                            "stateIdHex": state_hex,
                                            "parameterId": value.get("parameterId"),
                                            "parameterLabel": value.get("parameterLabel"),
                                            "value": value.get("value"),
                                        }.items()
                                        if item not in (None, "", [])
                                    })
                for slot in (definition or {}).get("effects") or ():
                    if not isinstance(slot, dict):
                        continue
                    # The top-level Bus catalog is the canonical payload for
                    # plug-in names, parameters, and flags.  Media rows keep
                    # only the stable slot/path reference to avoid copying a
                    # long authored parameter summary for every possible leaf.
                    row = {
                        "stage": "bus",
                        "busIdHex": bus_id,
                        "pathIndex": path_index,
                        "pathDepth": path_depth,
                        "slotIndex": slot.get("slotIndex"),
                        "effectIdHex": slot.get("effectIdHex"),
                    }
                    row = {
                        key: value for key, value in row.items()
                        if value not in (None, "", [])
                    }
                    key = tuple(
                        (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                        for key, value in sorted(row.items())
                    )
                    if key not in seen:
                        seen.add(key)
                        chain.append(row)

        if not chain:
            if not control_rows_by_bus and not duck_rows_by_bus:
                continue
        if chain:
            attached += 1
            chain_count += len(chain)
            media["postProcessEffectChainCount"] = len(chain)
            media["postProcessEffectChain"] = chain[:limit]
            media["postProcessEffectChainTruncated"] = len(chain) > limit
            media["postProcessEffectChainEvidence"] = (
                "exactSerializedEventNodeAndBusEffectJoin"
            )
        control_rows = []
        for row in control_rows_by_bus.values():
            rtpc_ids = sorted({
                str(curve.get("rtpcIdHex") or "").lower()
                for curve in row["rtpcControls"]
                if str(curve.get("rtpcIdHex") or "")
            })
            rtpc_parameter_labels = sorted({
                str(curve.get("parameterLabel") or "")
                for curve in row["rtpcControls"]
                if str(curve.get("parameterLabel") or "")
            })
            state_controls = [
                {
                    key: value for key, value in state.items()
                    if key in {
                        "groupIdHex", "stateIdHex", "parameterLabel", "value"
                    }
                }
                for state in row["stateControls"][:16]
            ]
            control_rows.append({
                "busIdHex": row["busIdHex"],
                "pathIndexes": sorted(row["pathIndexes"])[:32],
                "pathDepths": sorted(row["pathDepths"])[:32],
                "rtpcCurveCount": row["rtpcCurveCount"],
                "rtpcPointCount": row["rtpcPointCount"],
                "rtpcIds": rtpc_ids,
                "rtpcParameterLabels": rtpc_parameter_labels,
                "rtpcControlsTruncated": len(row["rtpcControls"]) > 8,
                "stateGroupCount": row["stateGroupCount"],
                "stateCount": row["stateCount"],
                "stateValueCount": row["stateValueCount"],
                "stateControls": state_controls,
                "stateControlsTruncated": len(row["stateControls"]) > 16,
            })
        control_rows.sort(key=lambda row: (
            row["pathIndexes"][0] if row["pathIndexes"] else 0,
            row["pathDepths"][0] if row["pathDepths"] else 0,
            row["busIdHex"],
        ))
        if control_rows:
            media["postProcessBusControlCount"] = len(control_rows)
            media["postProcessBusControls"] = control_rows[:32]
            media["postProcessBusControlsTruncated"] = len(control_rows) > 32
            media["postProcessBusControlEvidence"] = (
                "exactSerializedBusInitialRtpcAndStateJoin"
            )
        duck_rows = []
        for row in duck_rows_by_bus.values():
            ducks = []
            for duck in row["ducks"][:8]:
                if not isinstance(duck, dict):
                    continue
                ducks.append({
                    key: value for key, value in {
                        "duckIndex": duck.get("duckIndex"),
                        "targetBusIdHex": str(
                            duck.get("busIdHex") or duck.get("busId") or ""
                        ).lower(),
                        "duckVolumeDb": duck.get("duckVolumeDb"),
                        "fadeOutMs": duck.get("fadeOutMs"),
                        "fadeInMs": duck.get("fadeInMs"),
                        "fadeCurve": duck.get("fadeCurve"),
                        "targetPropertyIdHex": duck.get("targetPropertyIdHex"),
                        "targetPropertyLabel": duck.get("targetPropertyLabel"),
                    }.items()
                    if value not in (None, "", [])
                })
            duck_rows.append({
                "busIdHex": row["busIdHex"],
                "pathIndexes": sorted(row["pathIndexes"])[:32],
                "pathDepths": sorted(row["pathDepths"])[:32],
                "duckCount": row["duckCount"],
                "maxDuckVolumeDb": row["maxDuckVolumeDb"],
                "ducks": ducks,
                "ducksTruncated": len(row["ducks"]) > 8,
            })
        duck_rows.sort(key=lambda row: (
            row["pathIndexes"][0] if row["pathIndexes"] else 0,
            row["pathDepths"][0] if row["pathDepths"] else 0,
            row["busIdHex"],
        ))
        if duck_rows:
            media["postProcessBusDuckCount"] = len(duck_rows)
            media["postProcessBusDucks"] = duck_rows[:32]
            media["postProcessBusDucksTruncated"] = len(duck_rows) > 32
            media["postProcessBusDuckEvidence"] = (
                "exactSerializedBusDuckingJoin"
            )

    return {
        "mediaWithPostProcessEffectChain": attached,
        "mediaPostProcessEffectChainCount": chain_count,
    }


def annotate_media_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    trigger_context_catalog: dict[str, Any] | None,
    *,
    limit: int = 32,
) -> dict[str, int]:
    """Attach compact exact trigger-context summaries to media leaves.

    Trigger contexts already carry full situation/owner/evidence records in
    ``trigger_contexts.json``.  This pass only joins their serialized
    ``mediaRefs`` back to the media shard, so a reader can understand why a
    decoded leaf is present without loading the trigger catalog first.  It
    deliberately preserves the context's runtime-selection and activation
    boundaries; it does not turn an authored request into observed playback.
    """

    if not isinstance(trigger_context_catalog, dict):
        return {"mediaWithTriggerContextSummary": 0, "triggerContextMediaRefs": 0}
    by_marker: dict[str, dict[str, Any]] = {}
    for index, context in enumerate(trigger_context_catalog.get("contexts") or ()):
        if not isinstance(context, dict):
            continue
        trigger_id = str(context.get("triggerId") or f"context:{index}")
        semantic_kind = str(context.get("semanticKind") or "unknown")
        trigger_role = str(context.get("triggerRole") or "unknown")
        runtime_status = str(context.get("runtimeActivationStatus") or "")
        selection = context.get("selection") or {}
        selection_statuses = {
            str(selection.get(key) or "")
            for key in (
                "runtimeSelectionStatus", "eventSelectionStatus",
                "mediaSelectionStatus",
            )
            if str(selection.get(key) or "")
        }
        owner = context.get("owner") or {}
        owner_values = {
            str(owner.get(key) or "")
            for key in ("ownerId", "configId", "voiceId", "speakerActorId")
            if str(owner.get(key) or "")
        }
        situation = context.get("situation") or {}
        situation_values = {
            str(situation.get(key) or "")
            for key in (
                "eventId", "dialogId", "dialogKey", "lineId", "triggerKey",
                "remoteCommonId", "singleId", "levelScriptId",
            )
            if str(situation.get(key) or "")
        }
        for media_ref in context.get("mediaRefs") or ():
            if not isinstance(media_ref, dict):
                continue
            marker = _media_route_marker(media_ref)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "triggerIds": set(),
                "semanticKinds": set(),
                "triggerRoles": set(),
                "selectionStatuses": set(),
                "runtimeStatuses": set(),
                "ownerValues": set(),
                "situationValues": set(),
            })
            target["triggerIds"].add(trigger_id)
            target["semanticKinds"].add(semantic_kind)
            target["triggerRoles"].add(trigger_role)
            target["selectionStatuses"].update(selection_statuses)
            if runtime_status:
                target["runtimeStatuses"].add(runtime_status)
            target["ownerValues"].update(owner_values)
            target["situationValues"].update(situation_values)

    attached = 0
    ref_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        marker = _media_route_marker(media)
        target = by_marker.get(marker)
        if not target:
            continue
        attached += 1
        ref_count += len(target["triggerIds"])
        fields = {
            "triggerContextCount": len(target["triggerIds"]),
            "triggerSemanticKinds": sorted(target["semanticKinds"])[:limit],
            "triggerRoles": sorted(target["triggerRoles"])[:limit],
            "triggerSelectionStatuses": sorted(target["selectionStatuses"])[:limit],
            "triggerRuntimeActivationStatuses": sorted(target["runtimeStatuses"])[:limit],
            "triggerOwnerValues": sorted(target["ownerValues"])[:limit],
            "triggerSituationValues": sorted(target["situationValues"])[:limit],
            "triggerContextSummaryEvidence": "exactSerializedTriggerContextMediaJoin",
        }
        media.update(fields)
        media["triggerContextSummaryTruncated"] = any(
            len(target[key]) > limit
            for key in (
                "semanticKinds", "triggerRoles", "selectionStatuses",
                "runtimeStatuses", "ownerValues", "situationValues",
            )
        )
    return {
        "mediaWithTriggerContextSummary": attached,
        "triggerContextMediaRefs": ref_count,
    }


_MONO_BEHAVIOUR_SFX_FIELD_ROLES = frozenset({
    "soundSpawn",
    "_spawnAudioEvent",
    "_onHitAudioEvent",
    "startHitEvent",
    "normalAudiId",
    "soundFinish",
    "_onEnableLoopAudioEvent",
    "soundEvent",
    "_onRotationGroundOneShotAudioEvent",
    "_finishAudioEvent",
    "_onStartMoveAudioEvent",
    "notAimableSoundEvent",
    "aimableSoundEvent",
    "capacityCountLowEvent",
})


def annotate_media_trigger_semantic_categories(
    media_rows: Iterable[dict[str, Any]],
    trigger_context_catalog: dict[str, Any] | None,
) -> dict[str, int]:
    """Recover semantic categories from exact trigger-context ownership.

    The physical Wwise path can remain ``unknown`` even when an authored
    trigger context identifies the Event's category or an exact serialized
    MonoBehaviour field role.  This pass adds a separate semantic label only
    when the evidence is unambiguous.  It never rewrites ``audioCategory`` and
    never resolves a random/switch branch or runtime activation.
    """

    if not isinstance(trigger_context_catalog, dict):
        return {
            "mediaWithSemanticCategoryFromTriggerContext": 0,
            "mediaSemanticCategoryFromTriggerEventCategory": 0,
            "mediaSemanticCategoryFromMonoBehaviourSfxField": 0,
        }

    by_marker: dict[str, dict[str, Any]] = {}
    for index, context in enumerate(trigger_context_catalog.get("contexts") or ()):
        if not isinstance(context, dict):
            continue
        trigger_id = str(context.get("triggerId") or f"context:{index}")
        meaning = context.get("meaning") or {}
        category = str(meaning.get("category") or "").strip().lower()
        if category in {"", "unknown"}:
            category = ""
        semantic_kind = str(context.get("semanticKind") or "")
        trigger_role = str(context.get("triggerRole") or "")
        mono_sfx_role = (
            semantic_kind == "monoBehaviourAudioIdField"
            and trigger_role in _MONO_BEHAVIOUR_SFX_FIELD_ROLES
        )
        for media_ref in context.get("mediaRefs") or ():
            if not isinstance(media_ref, dict):
                continue
            marker = _media_route_marker(media_ref)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "triggerIds": set(),
                "categories": set(),
                "monoSfxRoles": set(),
            })
            target["triggerIds"].add(trigger_id)
            if category:
                target["categories"].add(category)
            if mono_sfx_role:
                target["monoSfxRoles"].add(trigger_role)

    attached = 0
    from_event_category = 0
    from_mono_sfx_field = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        marker = _media_route_marker(media)
        target = by_marker.get(marker)
        if not target:
            continue
        if str(media.get("audioCategory") or "unknown") != "unknown":
            continue
        if media.get("semanticCategory"):
            continue
        categories = sorted(target["categories"])
        semantic_category = ""
        evidence = ""
        if len(categories) == 1:
            semantic_category = categories[0]
            evidence = "exactSerializedTriggerContextEventCategory"
            from_event_category += 1
            media["semanticCategoryContextCategories"] = categories
        elif not categories and target["monoSfxRoles"]:
            semantic_category = "sfx"
            evidence = "exactSerializedMonoBehaviourAudioIdFieldRole"
            from_mono_sfx_field += 1
            media["semanticCategoryFieldRoles"] = sorted(target["monoSfxRoles"])
        if not semantic_category:
            continue
        media["semanticCategory"] = semantic_category
        media["semanticCategoryEvidence"] = evidence
        attached += 1

    return {
        "mediaWithSemanticCategoryFromTriggerContext": attached,
        "mediaSemanticCategoryFromTriggerEventCategory": from_event_category,
        "mediaSemanticCategoryFromMonoBehaviourSfxField": from_mono_sfx_field,
    }


def annotate_media_event_contexts(
    media_rows: Iterable[dict[str, Any]],
    event_rows: Iterable[dict[str, Any]],
    *,
    limit: int = 32,
) -> dict[str, int]:
    """Attach Event-level authored contexts to their possible media leaves.

    Unlike ``trigger_contexts.json`` mediaRefs, this join starts from the
    Event's complete candidate media set.  It therefore explains who/what
    authored the Event while explicitly retaining the runtime branch boundary:
    a context can apply to several random/switch/sequence leaves.
    """

    by_marker: dict[str, dict[str, Any]] = {}
    for event_index, event in enumerate(event_rows or ()):
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or event.get("eventId") or "").strip()
        if not event_id:
            continue
        contexts = [
            context for context in event.get("contexts") or ()
            if isinstance(context, dict)
        ]
        if not contexts:
            continue
        for candidate in event.get("media") or ():
            if not isinstance(candidate, dict):
                continue
            marker = _media_route_marker(candidate)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "contextKeys": set(),
                "eventIds": set(),
                "kinds": set(),
                "roles": set(),
                "ownerValues": set(),
                "situationValues": set(),
                "selectionStatuses": set(),
            })
            target["eventIds"].add(event_id)
            for context_index, context in enumerate(contexts):
                target["contextKeys"].add((event_id, event_index, context_index))
                kind = str(context.get("kind") or "unknown")
                target["kinds"].add(kind)
                role = str(context.get("triggerRole") or "").strip()
                if role:
                    target["roles"].add(role)
                for key in (
                    "ownerId", "configId", "voiceId", "speakerActorId",
                    "skillId", "enemyId", "characterId",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["ownerValues"].add(f"{key}={value}")
                for key in (
                    "dialogId", "dialogKey", "lineId", "triggerKey",
                    "remoteCommonId", "singleId", "levelScriptId",
                    "path", "table", "source",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["situationValues"].add(f"{key}={value}")
                for key in (
                    "runtimeSelectionStatus", "eventSelectionStatus",
                    "mediaSelectionStatus", "runtimeActivationStatus",
                    "triggerBindingStatus",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["selectionStatuses"].add(value)

    attached = 0
    context_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        target = by_marker.get(_media_route_marker(media))
        if not target:
            continue
        attached += 1
        context_count += len(target["contextKeys"])
        fields = {
            "eventContextCount": len(target["contextKeys"]),
            "eventContextEventIds": sorted(target["eventIds"])[:limit],
            "eventContextKinds": sorted(target["kinds"])[:limit],
            "eventContextRoles": sorted(target["roles"])[:limit],
            "eventContextOwnerValues": sorted(target["ownerValues"])[:limit],
            "eventContextSituationValues": sorted(target["situationValues"])[:limit],
            "eventContextSelectionStatuses": sorted(target["selectionStatuses"])[:limit],
            "eventContextSummaryEvidence": "exactSerializedEventContextToPossibleMediaJoin",
        }
        media.update(fields)
        media["eventContextSummaryTruncated"] = any(
            len(target[key]) > limit
            for key in (
                "eventIds", "kinds", "roles", "ownerValues",
                "situationValues", "selectionStatuses",
            )
        )
    return {
        "mediaWithEventContextSummary": attached,
        "mediaEventContextSummaryCount": context_count,
    }


def build_media_rows(
    audio_index: dict[str, Any],
    media_to_events: dict[str, list[str]],
    event_categories: dict[str, str] | None = None,
    event_rows: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    event_categories = event_categories or {}
    seen: set[tuple[str, str]] = set()
    event_rows = list(event_rows or ())
    post_process_routes = _media_post_process_routes(event_rows)
    definition_evidence_by_media_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    authored_event_ids_by_bank: dict[tuple[str, int], set[str]] = defaultdict(set)
    for inventory in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(inventory, dict):
            continue
        event_id = str(inventory.get("eventId") or "").strip()
        bank = str(inventory.get("bank") or "").strip()
        try:
            bank_id = int(inventory.get("bankId"))
        except (TypeError, ValueError):
            continue
        if event_id and bank and not event_id.lower().startswith("hashed-event:"):
            authored_event_ids_by_bank[(bank, bank_id)].add(event_id)
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
        compact = event_projection.compact_media(entry)
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
            related_categories = sorted({
                str(event_categories.get(event_id) or "unknown")
                for event_id in event_ids
            })
            compact["relatedEventCategories"] = related_categories
            unique_known_categories = sorted({
                value for value in related_categories if value not in {"", "unknown"}
            })
            if (
                str(compact.get("audioCategory") or "unknown") == "unknown"
                and len(unique_known_categories) == 1
            ):
                compact["semanticCategory"] = unique_known_categories[0]
                compact["semanticCategoryEvidence"] = (
                    "exactUniqueRelatedWwiseEventCategory"
                )
        route = post_process_routes.get(reverse_key)
        if route:
            compact.update(route)
        try:
            media_id = int(compact.get("mediaId") or compact.get("id"))
        except (TypeError, ValueError):
            media_id = 0
        definition_evidence = definition_evidence_by_media_id.get(media_id, [])
        if definition_evidence and not event_ids:
            compact["audioLibraryObjectStatus"] = "wwiseSoundDefinitionWithoutEventPath"
            compact["wwiseDefinitionEvidence"] = definition_evidence
            bank_event_ids = sorted({
                event_id
                for evidence in definition_evidence
                for event_id in authored_event_ids_by_bank.get((
                    str(evidence.get("bank") or ""),
                    int(evidence.get("bankId") or 0),
                ), set())
            })
            if bank_event_ids:
                compact["audioLibraryBankEventIds"] = bank_event_ids
                compact["purposeHintStatus"] = "authoredEventBankColocationOnly"
        rows.append(compact)
    annotate_media_event_contexts(rows, event_rows)
    annotate_media_post_process_effect_chains(rows, audio_index)
    rows.sort(key=lambda row: (
        str(row.get("audioCategory") or "unknown"),
        str(row.get("id") or ""),
        str(row.get("rel") or ""),
    ))
    return rows








def build_audio_semantic_data(
    audio_index: dict[str, Any],
    *,
    language: str,
    export_root: Path,
    webui_root: Path,
    metadata_path: Path | None = None,
    gameassembly_path: Path | None = None,
    cutscene_events: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    language = language.upper()
    native_context = native_evidence.validate_native_audio_evidence(
        metadata_path,
        gameassembly_path,
    )
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
    external_source_event_identity_audit = external_source.collect_event_identity_audit(
        audio_index,
        language=language,
        export_root=export_root,
    )
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
    cue_semantics = table_contexts.collect_audio_cue_semantics(export_root)
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
    managed_rtpc_parameters = [{
        "kind": "rtpcParameter",
        "parameterName": name,
        "source": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat:stringLiteral",
        "evidence": "exactManagedStringLiteral",
        "wwiseEventStatus": "notApplicable",
    } for name in identifiers.collect_metadata_audio_literals(metadata_path) if identifiers.is_rtpc_parameter_name(name)]
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
    media_name = "media.json"
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
        "metadataEventSymbolAliases": metadata_event_symbol_catalog,
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
            **media_trigger_context_counts,
            **media_trigger_semantic_category_counts,
            **media_post_process_counts,
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
            "wwiseEmptyEventDefinitions": sum(
                row.get("playbackRole") == "emptyEventDefinition" for row in events
            ),
            "eventsWithAuthoredSharedPlayTargetSet": shared_play_target_event_count,
            "eventsWithAuthoredSharedMediaLeafSet": shared_media_leaf_event_count,
            "eventsWithAuthoredSharedMediaLeafCategory": shared_media_leaf_category_event_count,
            "eventsWithAuthoredNamePatternCategory": authored_name_category_event_count,
            "mediaWithSemanticCategory": sum(
                bool(row.get("semanticCategory")) for row in media
            ),
            "mediaWithSemanticCategoryFromRelatedEvent": sum(
                row.get("semanticCategoryEvidence") == "exactUniqueRelatedWwiseEventCategory"
                for row in media
            ),
            "mediaSemanticCategoryCounts": dict(sorted(media_semantic_categories.items())),
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
            "aiBarkResponsiveWwiseEvents": sum(
                any(
                    context.get("kind") == "responsiveDialogVoice"
                    and bool(context.get("aiBarkRequests"))
                    for context in row.get("contexts") or []
                )
                for row in events
            ),
            "aiBarkResponsiveWwiseEventContexts": sum(
                context.get("kind") == "responsiveDialogVoice"
                and bool(context.get("aiBarkRequests"))
                for row in events
                for context in row.get("contexts") or []
                if isinstance(context, dict)
            ),
            "aiBarkIdsLinkedToResponsiveWwiseEvents": len({
                str(request.get("barkId") or "")
                for row in events
                for context in row.get("contexts") or []
                if isinstance(context, dict)
                and context.get("kind") == "responsiveDialogVoice"
                for request in context.get("aiBarkRequests") or []
                if isinstance(request, dict) and str(request.get("barkId") or "")
            }),
            "enemyTriggerVoiceActionResponsiveWwiseEvents": sum(
                any(
                    context.get("kind") == "responsiveDialogVoice"
                    and bool(context.get("enemyTriggerVoiceAction"))
                    for context in row.get("contexts") or []
                    if isinstance(context, dict)
                )
                for row in events
            ),
            "enemyTriggerVoiceActionResponsiveWwiseEventContexts": sum(
                context.get("kind") == "responsiveDialogVoice"
                and bool(context.get("enemyTriggerVoiceAction"))
                for row in events
                for context in row.get("contexts") or []
                if isinstance(context, dict)
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
            "recoveredOrphanExternalMediaIdentities": sum(
                row.get("externalMediaIdentityStatus") == "recoveredAuthoredPathHash"
                for row in media
            ),
            "mediaWithEventRelationOnly": media_playback_location_counts.get("eventRelationOnly", 0),
            "mediaWithAuthoredEventContext": media_playback_location_counts.get("authoredEventContext", 0),
            "directDialogMedia": media_playback_location_counts.get("directDialogMedia", 0),
            "mediaWithPostProcessRoutes": sum(
                int(row.get("postProcessRouteCount") or 0) > 0
                for row in media
            ),
            "mediaWithPostProcessUnresolvedBusPaths": sum(
                bool(row.get("postProcessUnresolvedBusProcessingIds"))
                for row in media
            ),
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
            "externalSourceEventIdentityEvents": external_source_event_identity_audit.get(
                "externalSourceEventCount", 0
            ),
            "externalSourceEventIdentityVoiceTableMatches": external_source_event_identity_audit.get(
                "externalEventsWithVoiceTableAlias", 0
            ),
            "externalSourceEventIdentityAudioDialogMatches": external_source_event_identity_audit.get(
                "externalEventsWithAudioDialogAlias", 0
            ),
            "externalSourceEventIdentityDecodedMediaMatches": external_source_event_identity_audit.get(
                "externalEventsWithDecodedMedia", 0
            ),
            "externalSourceEventIdentityZeroResolvedMedia": external_source_event_identity_audit.get(
                "externalEventsWithZeroResolvedMedia", 0
            ),
            "externalSourceOverridePathEvents": external_source_event_identity_audit.get(
                "externalEventsWithOverridePathCandidates", 0
            ),
            "externalSourceOverridePathUniqueEvents": external_source_event_identity_audit.get(
                "externalEventsWithUniqueOverridePath", 0
            ),
            "externalSourceOverridePathCandidates": external_source_event_identity_audit.get(
                "externalOverridePathCandidateCount", 0
            ),
            "externalSourceOverridePathDecodedCandidates": external_source_event_identity_audit.get(
                "externalOverridePathCandidatesWithDecodedMedia", 0
            ),
            "externalSourceChannelPathEvents": external_source_event_identity_audit.get(
                "externalEventsWithChannelPathCandidates", 0
            ),
            "externalSourceChannelPathUniqueCandidates": external_source_event_identity_audit.get(
                "externalChannelPathUniqueCandidateCount", 0
            ),
            "externalSourceChannelPathDecodedCandidates": external_source_event_identity_audit.get(
                "externalChannelPathUniqueCandidatesWithDecodedMedia", 0
            ),
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
            "metadataEventSymbolAliases": int(
                metadata_event_symbol_catalog.get("matchCount") or 0
            ),
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
            "interactiveComponentPropertyAudioEvents": context_kind_event_counts.get("interactiveComponentPropertyAudio", 0),
            "interactiveComponentPropertyAudioContexts": context_kind_counts.get("interactiveComponentPropertyAudio", 0),
            "interactivePropertyMapAudioEvents": context_kind_event_counts.get("interactivePropertyMapAudio", 0),
            "interactivePropertyMapAudioContexts": context_kind_counts.get("interactivePropertyMapAudio", 0),
            "interactiveTemplateConfigAudioEvents": context_kind_event_counts.get("interactiveTemplateConfigAudio", 0),
            "interactiveTemplateConfigAudioContexts": context_kind_counts.get("interactiveTemplateConfigAudio", 0),
            "interactiveTemplateActionAudioEvents": context_kind_event_counts.get("interactiveTemplateActionAudio", 0),
            "interactiveTemplateActionAudioContexts": context_kind_counts.get("interactiveTemplateActionAudio", 0),
            "interactiveEmbeddedActionAudioEvents": context_kind_event_counts.get("interactiveEmbeddedActionAudio", 0),
            "interactiveEmbeddedActionAudioContexts": context_kind_counts.get("interactiveEmbeddedActionAudio", 0),
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
            "modelViewStatePositionDirectEvents": context_kind_event_counts.get("modelViewStatePositionAudioEvent", 0),
            "modelViewStatePositionDirectEventContexts": context_kind_counts.get("modelViewStatePositionAudioEvent", 0),
            "modelViewStatePositionedCustomStateControls": context_kind_counts.get("modelViewStatePositionedCustomStateControl", 0),
            "modelViewStatePositionedEntityStateControls": context_kind_counts.get("modelViewStatePositionedEntityStateControl", 0),
            "modelViewStatePositionedControls": (
                context_kind_counts.get("modelViewStatePositionedCustomStateControl", 0)
                + context_kind_counts.get("modelViewStatePositionedEntityStateControl", 0)
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
            "modelViewStatePositionedControls": model_view_semantics.get("positionedControls") or [],
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
                dict(row) for row in wwise_selector_groups
            ],
            "wwiseActionControls": wwise_action_control_catalog,
            "wwiseInitialRtpcParameters": wwise_initial_rtpc_catalog,
            "evidenceBoundary": "Cue behavior exprType=3 values, constant LevelScript Event parameters, LevelScript cue names joined by the native AudioHashGenerator to exact cue behavior expressions, non-empty PhysicsAudio Event properties, and normal ModelView Event plus positioned direct-position hashes are authored requests. Positioned custom/entity state rows are typed controls only and never Event ownership. Metadata-named InitialRTPC rows are exact ID/hash joins that preserve authored curve targets and controlled properties; they do not observe live RTPC updates or audibility. PhysicsAudio/ModelView RTPC names, ModelView spatial/custom-audio rows, cue/action execution, handler conditions, exprType=8 strings, dynamic Params, state/variable writes, playback handles, placeholder-music ids, unresolved cue hashes, and musicCue* values remain typed controls or unresolved runtime state. LevelEvent OnAudioStateChanged and OnMusicBeatEvent are current-build trigger-input definitions, not playback requests; exhaustive active-overlay scanning found zero authored occurrences. Two non-music Wwise selector groups have exact native setter callsites; three more have high-confidence semantic correlation only, and ten music State groups have exact current-metadata/native-setter joins. None reveal a live value, selected branch, or authored group name.",
        },
        "runtimeModel": runtime_model,
        "externalSourceEventIdentityAudit": external_source_event_identity_audit,
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
            "externalSourceEventIdentity": external_source_event_identity_audit.get(
                "evidenceBoundary", ""
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
