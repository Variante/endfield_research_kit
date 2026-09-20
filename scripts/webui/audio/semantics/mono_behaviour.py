"""MonoBehaviour audio-id contexts and the runtime model.

Scans published MonoBehaviour objects for audio-id carriers and projects the
runtime-system model. A carrier is a serialized field, not a playback claim."""

from __future__ import annotations
from scripts.source_paths import INSTALLED_LAYERS, ExportLayout

import hashlib
import importlib
import json
import re
import shutil
import struct
import subprocess
import sys
from scripts.webui.audio.semantics import identifiers
from scripts.webui.audio.semantics import managed_literals
from scripts.webui.audio.semantics import scene_backgrounds
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from scripts.webui.audio.semantics.build_contracts import AUDIO_MUSIC_NATIVE_STATE_GROUPS as AUDIO_MUSIC_NATIVE_STATE_GROUPS
from scripts.webui.audio.semantics.build_contracts import CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256 as CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256
from scripts.webui.audio.semantics.build_contracts import MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 as MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256
from scripts.webui.audio.semantics.context_utils import AUDIO_SEMANTIC_SCHEMA_VERSION as AUDIO_SEMANTIC_SCHEMA_VERSION
from scripts.webui.audio.semantics.context_utils import append_context as _append_context
from scripts.webui.audio.semantics.context_utils import json_dump as json_dump
from scripts.webui.audio.semantics.context_utils import load_json as load_json
from scripts.webui.audio.semantics.context_utils import normalize_posix as normalize_posix

from scripts.game_data.extraction.animestudio_index_io import (
    ObjectIndexUnavailable,
    iter_effective_layer_objects,
    load_published_schema_fields,
    published_object_index_path,
)
from scripts.common import sha256_file as file_sha256


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

from scripts.repo_paths import REPO_ROOT
from scripts.common import WEBUI_BUILD_DIR

ROOT = REPO_ROOT

METADATA_HELPER = ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"

RUNTIME_CACHE_PATH = WEBUI_BUILD_DIR / "audio" / "semantics" / "runtime_metadata.json"

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
    | {
        "soundBase.soundSpawn", "soundBase.soundFinish", "PlayLineSound",
        "triggerFunctions", "levelGlobalEvents",
    }
))

MONO_BEHAVIOUR_AUDIO_CONTEXT_CACHE_SCHEMA_VERSION = 4

RUNTIME_MODEL_CACHE_SCHEMA_VERSION = 109

METADATA_EVENT_SYMBOL_SCHEMA_VERSION = 1

METADATA_EVENT_SYMBOL_RE = re.compile(r"^AU_[A-Z0-9_]+$")

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
    cache_path = RUNTIME_CACHE_PATH
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

    directories = [path for path in (root / "MonoBehaviour",) if path.is_dir()]
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

    layout = ExportLayout(export_root)
    root = layout.unity_dir
    index_paths = [layout.object_index_dir(source) / "objects.jsonl.gz" for source in INSTALLED_LAYERS]
    # The cache lives in webui/data/_build, shared by every export root, so
    # the root itself is part of the key.
    source_fingerprint: list[dict[str, Any]] = [{"exportRoot": normalize_posix(export_root.resolve())}]
    source_fingerprint.extend({
        "path": normalize_posix(path.relative_to(export_root)),
        "size": path.stat().st_size,
        "mtimeNs": path.stat().st_mtime_ns,
    } for path in index_paths if path.is_file())
    source_fingerprint.extend({
        "path": normalize_posix(path.relative_to(export_root)),
        "kind": "directory",
        "mtimeNs": path.stat().st_mtime_ns,
    } for path in (root / "MonoBehaviour",) if path.is_dir())
    event_hash_fingerprint = hashlib.sha256(
        "\n".join(f"{value & 0xFFFFFFFF:08x}" for value in sorted(current_wwise_event_hashes)).encode("ascii")
    ).hexdigest()
    cache_path = WEBUI_BUILD_DIR / "audio" / "semantics" / "mono_behaviour_audio_id_contexts.json"
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
    raw_field_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    layout_counts: Counter[str] = Counter()
    event_role_counts: dict[str, Counter[str]] = defaultdict(Counter)
    occurrence_keys: set[tuple[str, str, int, str, int]] = set()
    raw_object_candidates: set[tuple[str, str, int]] = set()
    complete_index_sources = 0
    incomplete_index_sources = 0
    index_fields_contract: dict[str, bool] = {}
    for source_root in INSTALLED_LAYERS:
        merged_path = layout.object_index_dir(source_root) / "objects.jsonl.gz"
        try:
            published_object_index_path(export_root, source_root)
            schema_fields = load_published_schema_fields(export_root, source_root)
            rows = iter_effective_layer_objects(export_root, source_root)
            index_source_path = merged_path
            source_paths.append(normalize_posix(merged_path.relative_to(export_root)))
        except ObjectIndexUnavailable:
            continue
        for row in rows:
            candidate_objects += 1
            # AudioMap fields are accepted only against the complete typed schema.
            row["_audioSchemaFields"] = schema_fields.get(str(row.get("schemaId") or ""), frozenset())
            fields = [
                field for field in row.get("fields") or []
                if isinstance(field, list) and len(field) >= 3
            ]
            # New indexes carry the complete bounded field projection. Older
            # indexes only have the identity-oriented scalar projection and
            # must remain eligible for the legacy raw-JSON fallback.
            has_fields_contract = (
                isinstance(row.get("fields"), list)
                and row.get("fieldsStatus") == "decoded"
                and not bool(row.get("fieldsTruncated"))
            )
            index_fields_contract[source_root] = (
                index_fields_contract.get(source_root, True) and has_fields_contract
            )
            if fields:
                scalars = fields
            else:
                scalars = [
                    scalar for scalar in row.get("scalars") or []
                    if isinstance(scalar, list) and len(scalar) >= 3
                ]
            object_row = row.get("object") if isinstance(row.get("object"), dict) else {}
            try:
                candidate_path_id = int(object_row.get("pathId") or 0)
            except (TypeError, ValueError):
                candidate_path_id = 0
            # A row whose own field projection is complete (``fields`` decoded
            # and untruncated) already carries every serialized leaf the raw
            # JSON would yield, so re-reading its file cannot add an
            # occurrence.  Only rows that fail that per-row contract stay
            # eligible for the raw-JSON read; the source-level gate below still
            # decides whether the content prefilter is also required.
            if not has_fields_contract:
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
            audio_map_schema_fields = row.get("_audioSchemaFields")
            if not isinstance(audio_map_schema_fields, frozenset):
                audio_map_schema_fields = frozenset()
            for scalar_path, _scalar_type, scalar_value in scalars:
                parsed = (
                    _mono_audio_event_scalar(scalar_path, scalar_value)
                    or scene_backgrounds.audio_map_event_scalar(
                        scalar_path, scalar_value, audio_map_schema_fields,
                    )
                )
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
                raw_field_counts[authored_role] += 1
                context: dict[str, Any] = {
                    "kind": "monoBehaviourAudioIdField",
                    "semanticRole": "authoredSerializedComponentAudioEvent",
                    "authoredFieldRole": authored_role,
                    "serializedFieldPath": scalar_path,
                    "signedValue": scalar_value if isinstance(scalar_value, int) else None,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "sourceRoot": source_root,
                    "objectIndexSource": normalize_posix(index_source_path.relative_to(export_root)),
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
                context.update(managed_literals.project_mono_behaviour_audio_field(
                    scalar_path,
                    field_name=authored_role,
                    component_layout=context.get("managedReferenceLayout"),
                    component_type=script.get("fullName") or row.get("name"),
                ))
                if authored_role.startswith("audioMap"):
                    context.update({
                        "authoredFieldRole": authored_role,
                        "authoredFieldRoleEvidence": "exactSerializedAudioMapDataSchemaField",
                        "componentLayout": "Beyond.Gameplay.Audio.AudioMapData",
                        "componentLayoutStatus": "exactSerializedSchema",
                        "serializedFieldPathStatus": "exact",
                        "evidence": "exactSerializedAudioMapDataEventFieldAndCurrentWwiseEvent",
                        "triggerRequestEvidence": [
                            "exactCompleteSerializedAudioMapDataSchema",
                            "exactTypedAudioMapDataEventField",
                            "exactCurrentWwiseEventHash",
                        ],
                    })
                context["authoredFieldNameRaw"] = authored_role
                role_counts[str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
                layout_counts[str(context.get("componentLayout") or "unknown")] += 1
                event_role_counts[f"0x{event_hash:08x}"][str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
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
                raw_field_counts[authored_role] += 1
                context = {
                    "kind": "monoBehaviourAudioIdField",
                    "semanticRole": "authoredSerializedComponentAudioEvent",
                    "authoredFieldRole": authored_role,
                    "serializedFieldPath": scalar_path,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "sourceRoot": source_root,
                    "objectIndexSource": normalize_posix(index_source_path.relative_to(export_root)),
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
                context.update(managed_literals.project_mono_behaviour_audio_field(
                    scalar_path,
                    field_name=authored_role,
                    component_layout=managed_details.get("managedReferenceLayout"),
                    component_type=script.get("fullName") or row.get("name"),
                ))
                context["authoredFieldNameRaw"] = authored_role
                role_counts[str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
                layout_counts[str(context.get("componentLayout") or "unknown")] += 1
                event_role_counts[f"0x{event_hash:08x}"][str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
                _append_context(
                    contexts,
                    seen,
                    identifiers.event_hash_context_key(event_hash),
                    {key: value for key, value in context.items() if value not in (None, "", [])},
                )
    # A complete merged index contains the same scalar evidence without the
    # expensive raw-directory content scan.  Raw JSON remains an explicit
    # fallback for old exports or indexes whose scalar set was truncated.
    for source_root in INSTALLED_LAYERS:
        try:
            summary_path = layout.object_index_dir(source_root) / "summary.json"
            summary = load_json(summary_path, {})
            counts = summary.get("counts") if isinstance(summary, dict) else {}
            if (
                summary.get("complete") is True
                and index_fields_contract.get(source_root, False)
                and not int(counts.get("objectsWithTruncatedScalars") or 0)
                and not int(counts.get("objectsWithTruncatedFields") or 0)
            ):
                complete_index_sources += 1
            else:
                incomplete_index_sources += 1
        except (OSError, TypeError, ValueError):
            incomplete_index_sources += 1

    raw_paths: set[Path] = set()
    raw_fallback_reason = "not-needed-complete-object-index"
    for source_root, object_name, candidate_path_id in raw_object_candidates:
        if not object_name:
            continue
        raw_path = (
            root / "MonoBehaviour"
            / f"{object_name}_p{candidate_path_id & ((1 << 64) - 1):016X}.json"
        )
        if raw_path.is_file():
            raw_paths.add(raw_path)
    if incomplete_index_sources or not complete_index_sources:
        raw_paths.update(_mono_audio_raw_json_paths(root))
        raw_fallback_reason = (
            "published object index missing/incomplete; retained legacy JSON prefilter"
        )
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
            raw_field_counts[authored_role] += 1
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
            context.update(managed_literals.project_mono_behaviour_audio_field(
                scalar_path,
                field_name=authored_role,
                component_type=metadata.get("scriptFullName") or metadata.get("name"),
            ))
            context["authoredFieldNameRaw"] = authored_role
            role_counts[str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
            layout_counts[str(context.get("componentLayout") or "unknown")] += 1
            event_role_counts[f"0x{event_hash:08x}"][str(context.get("authoredFieldRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)] += 1
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
        "metadata and complete payload consumption. AudioMapData trigger, level lifecycle, and "
        "outdoor room-tone values are accepted only with the complete exact serialized schema. "
        "RTPC fields, generic integers, PathIDs, "
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
            "rawFieldNameCounts": dict(sorted(raw_field_counts.items())),
            "componentLayoutCounts": dict(sorted(layout_counts.items())),
            "eventFieldRoleCounts": {
                event_hex: dict(sorted(counts.items()))
                for event_hex, counts in sorted(event_role_counts.items())
            },
            "runtimeExecutionObserved": 0,
            "cacheStatus": "refreshed",
            "rawJsonFallbackReason": raw_fallback_reason,
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






