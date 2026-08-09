#!/usr/bin/env python3
"""Build compact debug-only WebUI data for Endfield audio semantics.

The normal audio index under ``export_full/structured/Audio/<LANG>`` is the
lossless recovery surface and can be tens of megabytes.  This builder keeps
that file authoritative, then publishes a compact overview plus lazy event and
media shards for the debug Audio page.  Installed IL2CPP metadata is optional:
when present, selected runtime-system types and members are validated against
the current binary metadata instead of being asserted from a stale snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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
AUDIO_SEMANTIC_SCHEMA_VERSION = 3
RUNTIME_MODEL_CACHE_SCHEMA_VERSION = 3


def runtime_spec(
    type_name: str,
    layer: str,
    meaning: str,
    *,
    fields: Iterable[str] = (),
    methods: Iterable[str] = (),
    enum_values: bool = False,
) -> dict[str, Any]:
    return {
        "type": type_name,
        "layer": layer,
        "meaning": meaning,
        "fields": tuple(fields),
        "methods": tuple(methods),
        "enumValues": enum_values,
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
        "Owns Wwise bank handles and asynchronous load/unload lifetime.",
        fields=("s_loadedBankHandles",),
        methods=("LoadMainPCK", "LoadBankAsync", "UnloadBank", "UnloadAllBanks", "IsBankLoaded"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioAssetHelper",
        "banks",
        "Prepares, pins, caches, and garbage-collects event-owned audio resources.",
        fields=("s_memoryBudget", "s_pendingLoadRequests", "s_solidLoadedEvents"),
        methods=("LoadEventAsync", "PinEvent", "UnpinEvent", "UnloadEvent", "ReleaseAllCachedEventsSync"),
    ),
    runtime_spec(
        "Beyond.Audio.AudioAdapter",
        "wwise_bridge",
        "Low-level bridge for Wwise events, states, switches, RTPCs, objects, listeners, and seek/stop operations.",
        methods=(
            "PostEvent", "StopByPlayingId", "PauseByPlayingId", "ResumeByPlayingId",
            "SetState", "SetSwitch", "SetRtpc", "SeekOnEvent", "RegisterGameObject",
            "UnregisterGameObject", "SetListener", "SetDefaultListener", "SetAudioLanguage",
        ),
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
            "REMOTE_COMM_MUSIC_STATE_GROUP_ID",
        ),
        methods=(
            "PostMusicEvent", "StartLoginMusic", "PauseMusic", "ResumeMusic", "StopMusic",
            "SwitchToDialogMusic", "PlayStandaloneMusic", "ManualSetMusicState",
            "ManualSetBattleMusicState", "ManualSetBattleMusicIntensityState",
        ),
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
    ),
    runtime_spec(
        "Beyond.Gameplay.Audio.AudioStateSystem+EAudioState",
        "game_state",
        "High-level audio state flags for combat, dialog, cutscenes, remote communication, factory, and loading.",
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
                    "selectionPaths", "bankId", "bankPackage",
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
    return [
        {key: value for key, value in row.items() if value not in (None, "", [])}
        for row in summary.values()
    ]


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
            "They prove shipped runtime structure, not live call order, the active game state, "
            "or which Wwise branch a player heard."
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
                    "authoredEventIds": list(event.get("authoredEventIds") or [])[:8],
                }
                _append_context(contexts, seen, event.get("id"), context)
    return dict(contexts)


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


def collect_table_contexts(
    export_root: Path,
    runtime_model: dict[str, Any] | None = None,
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
            elif table == "AudioCueTable" and field_name == "stringValue":
                semantic_role = "cueExpressionValue"
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
        and any(
            isinstance(row, dict) and row.get("semanticRole") != "cueExpressionValue"
            for row in rows
        )
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
    names = collect_metadata_audio_literals(metadata_path)
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
            "rootPlayActionCount": int(evidence.get("rootPlayActionCount") or 0),
            "rootStopActionCount": int(evidence.get("rootStopActionCount") or 0),
            "visitedObjectCount": len(evidence.get("visitedObjectIds") or []),
            "mediaIds": evidence.get("mediaIds") or [],
            "objectTypeCounts": object_types,
            "selectionContainerTypes": selection_types,
            "containerEvidence": compact_container_evidence(evidence.get("containerEvidence") or []),
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
        rows.append({
            "id": key,
            "name": display_names.get(key, key),
            "hash": event_hash,
            "category": event_category(key),
            "categoryEvidence": "namePrefix" if event_category(key) != "unknown" else "unclassified",
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
    if value in {"characterSkill", "enemySkill", "buffPlaySoundAction"}:
        return "gameplay"
    if value == "cutsceneTimeline":
        return "cutscene"
    if value in {"characterAnimation", "enemyAnimation"}:
        return "animation"
    if value in {
        "table", "tableEventHash", "interactiveAudioTrigger", "interactiveComponentTrigger",
        "audioGlobalConfigEvent", "audioGlobalConfigEventHash",
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
        ):
            context_search.update(str(value) for value in context.get(key) or [] if str(value))
        for action in context.get("triggerPlaySoundActions") or []:
            if not isinstance(action, dict):
                continue
            for value in action.values():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    context_search.add(str(value))
                elif isinstance(value, list):
                    context_search.update(str(item) for item in value if str(item))
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
        "animationContextScope", "animationFunctions",
    )
    summary = {key: row[key] for key in keys if row.get(key) not in (None, "", [])}
    summary.update({
        "contextGroups": sorted({semantic_context_group(context.get("kind")) for context in contexts if isinstance(context, dict)} - {""}),
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
    contexts = merge_contexts(
        collect_gameplay_contexts(webui_root, language),
        collect_table_contexts(export_root, runtime_model),
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
        "debugOnly": True,
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
        "runtimeModel": runtime_model,
        "evidenceBoundary": {
            "decodedMedia": "A decoded FLAC/WAV/WEM is a source media object, not proof that it played.",
            "eventMedia": "Possible media leaves use typed Wwise v150 Event -> Action -> reciprocal Children -> Sound source edges. Play roots and random/sequence/switch/layer relations are preserved; runtime selection is not evaluated. Unsupported music nodes and unparsed child structures fail closed.",
            "authoredContext": "Table, Timeline, SkillData, and BuffData references prove authored consumers, not a live playback trace.",
            "animationOwnership": "An AnimationClip callback proves that the owned clip requests the Event. If the same Event is used by multiple playable characters, its complete Wwise leaf graph is a shared selector surface and is not character-specific media ownership.",
            "authoredEventHash": "Signed table integers are normalized to uint32 only in event-designated fields; row and field prove semantic ownership even when no string name is known.",
            "runtimeMetadata": "IL2CPP names prove shipped system structure, not live call order or active state.",
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
