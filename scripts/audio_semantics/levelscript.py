"""LevelScript audio semantics: controls, cue invocations, and radio contexts.

Reads authored LevelScript output and its lifecycle sources. A decoded control or
binding is authored evidence; it does not establish that the action ran."""

from __future__ import annotations

import hashlib
import re
from . import identifiers
from . import table_contexts
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .context_utils import append_context as _append_context
from .context_utils import load_json as load_json
from .context_utils import normalize_posix as normalize_posix
from . import media_rows

RADIO_MEDIA_CONTEXT_LIMIT = 64

RADIO_MEDIA_SEARCH_LIMIT = 96

RADIO_CATALOG_ITEM_LIMIT = 64

LEVELSCRIPT_AUDIO_EVENT_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "PlayAudiAtPosition": (("key", "play"),),
    "PlayAudio": (("key", "play"),),
    "PlayAudioAndWait": (("eventName", "play"),),
    "PlayAudioOnTarget": (("audioKey", "play"),),
    "PlayStandaloneMusic": (("startEvent", "standaloneStart"), ("stopEvent", "standaloneStop")),
    "PostAudioStatusEvent": (("statusEnterEvent", "statusEnter"), ("statusExitEvent", "statusExit")),
    "PostMusicEvent": (("musicEvent", "post"), ("musicEventOnRelease", "release")),
    # PostAudioCue.name is a cue identity rather than a Wwise Event.  It is
    # still an authored string parameter and may be sourced from the exact
    # LevelScriptBriefData property path, so keep it in the same narrow
    # ParamSource=200 resolution surface as the existing Event fields.
    "PostAudioCue": (("name", "cue"),),
    "PostAudioCueOnRelease": (("name", "cueOnRelease"),),
}

_LEVELSCRIPT_OUTPUT_PATH_RE = re.compile(r"^\$\d+@_[A-Za-z][A-Za-z0-9]*$")

_LEVELSCRIPT_AUDIO_LIFECYCLE_FIELDS = {
    ("PlayAudio", "audioPlayingId"): ("audioPlayingId", "producer"),
    ("PlayVoice", "voiceHandle"): ("voiceHandle", "producer"),
    ("PlayVoiceNarrative", "voiceHandle"): ("voiceHandle", "producer"),
    ("BlockAutoMusicChange", "blockHandle"): ("blockHandle", "producer"),
    ("PostAudioCue", "cueHandlerId"): ("cueHandlerId", "producer"),
    ("PostAudioCueOnRelease", "cueHandlerId"): ("cueHandlerId", "producer"),
    ("StopAudio", "audioId"): ("audioPlayingId", "consumer"),
    ("StopVoice", "voiceHandle"): ("voiceHandle", "consumer"),
    ("BlockAutoMusicChangeCancel", "blockHandle"): ("blockHandle", "consumer"),
}

def _levelscript_parameter_source(field: Any) -> str:
    """Classify a serialized audio Param without resolving runtime values."""
    if not isinstance(field, dict):
        return "runtime"
    param_source = field.get("paramSource")
    # ParamSource is authoritative.  In particular, a malformed/custom row
    # must not promote a ParamSource=100 or unknown source merely because a
    # decoder labelled it ``output``.
    if type(param_source) is not int:
        return "runtime"
    if param_source == 100:
        return "runtime"
    if param_source == 200:
        return "property"
    if param_source != 0:
        return "runtime"
    if field.get("bindingKind") == "output":
        return "output"
    if (
        field.get("bindingKind") == "constant"
        or (
            field.get("idRef") == -1
            and field.get("path") is None
        )
    ):
        return "constant"
    # ParamSource=100 is a runtime lookup.  It is intentionally never
    # promoted to a playing-id or other handle merely because its path looks
    # like an output reference.
    return "runtime"

def _levelscript_parameter_status(field: Any) -> str:
    source = _levelscript_parameter_source(field)
    if source == "constant":
        return "authored_constant"
    if source == "output":
        return "serialized_output_path"
    if source == "property":
        return "property_value_unresolved"
    return "runtime_value_unresolved"

def _decorate_levelscript_audio_field(field: Any) -> dict[str, Any]:
    """Add a stable source classification while retaining authored fields."""
    if not isinstance(field, dict):
        return {}
    source = _levelscript_parameter_source(field)
    return {
        **field,
        "sourceKind": source,
        "parameterSourceKind": source,
        "parameterStatus": _levelscript_parameter_status(field),
    }

def _levelscript_action_ordinal(action_map_role: Any) -> int | None:
    match = re.match(r"^actionList#(\d+)(?:\s|$)", str(action_map_role or ""))
    if match is None:
        return None
    try:
        ordinal = int(match.group(1)) - 1
    except (TypeError, ValueError):
        return None
    return ordinal if ordinal >= 0 else None

def _levelscript_topology_action_facts(
    topology: Any,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Project exact topology facts onto one physical action record.

    A topology row is authoritative only when the complete action map passed
    validation.  Physical duplicates that are not the active final indexed
    slot remain visible as shadowed evidence but cannot participate in a
    lifecycle join.
    """
    if not isinstance(topology, dict) or not str(topology.get("status") or "").startswith("exact_"):
        return {
            "topologyStatus": "unavailable_fail_closed",
            "topologyEvidence": False,
            "storyOrderEvidence": False,
        }
    record_start = record.get("start")
    record_local_id = record.get("localId")
    actions = [row for row in topology.get("actions") or [] if isinstance(row, dict)]
    active = next(
        (
            row for row in actions
            if isinstance(record_start, int)
            and row.get("recordStart", row.get("recordOffset")) == record_start
        ),
        None,
    )
    active_for_local = next(
        (
            row for row in actions
            if isinstance(record_local_id, int)
            and row.get("recordLocalId", row.get("localId")) == record_local_id
        ),
        None,
    )
    if active is None:
        shadowed = bool(active_for_local is not None and active_for_local.get("recordStart") != record_start)
        return {
            "topologyStatus": "shadowed_physical_record" if shadowed else "not_active_action_slot",
            "topologyEvidence": True,
            "storyOrderEvidence": False,
            "runtimeSlotStatus": "shadowed" if shadowed else "unresolved",
            "runtimeShadowedRecordOffsets": (
                topology.get("runtimeShadowedActionRecordOffsets")
                if shadowed else None
            ),
        }

    local_id = active.get("recordLocalId", active.get("localId"))
    static_next: list[dict[str, Any]] = []
    for edge in topology.get("edges") or []:
        if not isinstance(edge, dict) or edge.get("sourceKind") != "action":
            continue
        if edge.get("sourceLocalId") != local_id:
            continue
        target_local_id = edge.get("targetActionLocalId")
        target = next(
            (
                row for row in actions
                if row.get("recordLocalId", row.get("localId")) == target_local_id
            ),
            None,
        )
        static_next.append({
            "relation": edge.get("relation"),
            "targetActionLocalId": target_local_id,
            "targetStatus": "active" if target is not None else "missing",
        })
    for terminal in topology.get("runtimeTerminalTargets") or []:
        if not isinstance(terminal, dict) or terminal.get("sourceKind") != "action":
            continue
        if terminal.get("sourceLocalId") != local_id:
            continue
        static_next.append({
            "relation": terminal.get("relation"),
            "targetActionLocalId": terminal.get("targetActionLocalId"),
            "targetStatus": "missing_runtime_action_slot",
        })
    static_next = [
        row for row in static_next
        if row.get("targetActionLocalId") is not None
    ]
    return {
        "topologyStatus": "active_final_serialized_slot",
        "topologyEvidence": True,
        "storyOrderEvidence": False,
        "runtimeSlotStatus": "active-final-serialized-slot",
        "serializedActionOrdinal": active.get("serializedActionOrdinal"),
        "recordStart": active.get("recordStart", active.get("recordOffset")),
        "recordLocalId": active.get("recordLocalId", active.get("localId")),
        "actionMapRole": active.get("actionMapRole"),
        "staticNext": static_next,
        "staticNextStatus": "resolved" if static_next else "none",
        "runtimeShadowedRecordOffsets": active.get("runtimeShadowedRecordOffsets"),
        "runtimeDuplicateSignatureStatus": active.get("runtimeDuplicateSignatureStatus"),
    }

def _levelscript_lifecycle_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in (
            "action", "levelScriptId", "sourceRoot", "sourcePath", "serializedActionOrdinal",
            "recordStart", "recordLocalId", "actionMapRole", "runtimeSlotStatus",
        )
        if row.get(key) not in (None, "", [])
    }

_LEVELSCRIPT_LIFECYCLE_SOURCE_ROOTS = frozenset({
    "StreamingAssets",
    "Persistent",
})

def _levelscript_lifecycle_source_identity(
    row: dict[str, Any],
) -> tuple[str, str] | None:
    """Return one canonical source-root/path pair, or fail closed."""
    source_root = row.get("sourceRoot")
    source_path = row.get("sourcePath")
    level_script_id = row.get("levelScriptId")
    if (
        type(source_root) is not str
        or source_root not in _LEVELSCRIPT_LIFECYCLE_SOURCE_ROOTS
        or type(source_path) is not str
        or not source_path
        or "\\" in source_path
        or type(level_script_id) is not str
        or not level_script_id
        or "\\" in level_script_id
        or source_path.startswith("/")
        or level_script_id.startswith("/")
    ):
        return None
    normalized = PurePosixPath(source_path).as_posix()
    source_parts = PurePosixPath(source_path).parts
    normalized_level_script_id = PurePosixPath(level_script_id).as_posix()
    level_parts = PurePosixPath(level_script_id).parts
    expected_prefix = (
        f"structured/{source_root}/Data/Json/LevelScriptData/"
    )
    expected_path = f"{expected_prefix}{normalized_level_script_id}.json"
    if (
        normalized != source_path
        or normalized_level_script_id != level_script_id
        or any(part in {"", ".", ".."} for part in source_parts)
        or any(part in {"", ".", ".."} for part in level_parts)
        or level_script_id.endswith(".json")
        or source_path != expected_path
    ):
        return None
    return source_root, normalized

def _build_levelscript_audio_lifecycle(
    action_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Join only exact serialized output paths within one LevelScript.

    This is a static authored-output relation.  It deliberately does not
    resolve ParamSource=100 values and never calls a path an observed runtime
    playing id.
    """
    producers: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    producer_blockers: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    consumers: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for row in action_rows:
        if not isinstance(row, dict):
            continue
        action = str(row.get("action") or "")
        level_script_id = str(row.get("levelScriptId") or "")
        fields = row.get("fields") or {}
        if not isinstance(fields, dict):
            continue
        source_identity = _levelscript_lifecycle_source_identity(row)
        for field_name, field in fields.items():
            relation = _LEVELSCRIPT_AUDIO_LIFECYCLE_FIELDS.get((action, str(field_name)))
            if relation is None:
                continue
            lifecycle_kind, role = relation
            field = field if isinstance(field, dict) else {}
            source_kind = _levelscript_parameter_source(field)
            path = field.get("path")
            path_valid = isinstance(path, str) and bool(_LEVELSCRIPT_OUTPUT_PATH_RE.fullmatch(path))
            base = {
                "lifecycleKind": lifecycle_kind,
                "role": role,
                "fieldName": str(field_name),
                "sourceField": field.get("sourceField"),
                "parameterSource": field.get("paramSource"),
                "sourceKind": source_kind,
                "pathEvidence": "exactSerializedOutputPath" if path_valid else "malformedSerializedOutputPath",
                "serializedOutputPath": path if path_valid else None,
                "action": action,
                "levelScriptId": level_script_id,
                "sourceRoot": row.get("sourceRoot"),
                "sourcePath": row.get("sourcePath"),
                "actionIdentity": _levelscript_lifecycle_identity(row),
            }
            if source_identity is None:
                base["role"] = "unresolved"
                base["joinStatus"] = "unresolved_missing_or_invalid_source_identity"
                details.append(base)
                counts[base["joinStatus"]] += 1
                continue
            source_root, source_path = source_identity
            key_path = path if isinstance(path, str) and path else None
            key = (
                (level_script_id, source_root, source_path, lifecycle_kind, key_path)
                if key_path is not None else None
            )
            if role == "producer":
                blocker_status = "active"
                if not path_valid:
                    blocker_status = "malformed_serialized_output_path"
                elif source_kind != "output":
                    blocker_status = "invalid_parameter_source"
                elif row.get("runtimeSlotStatus") != "active-final-serialized-slot":
                    blocker_status = "inactive_or_unvalidated_slot"
                if key is not None:
                    base["producerBlockerStatus"] = blocker_status
                    producer_blockers[key].append(base)
                if not path_valid:
                    base["role"] = "unresolved"
                    base["joinStatus"] = "unresolved_malformed_serialized_output_path"
                    details.append(base)
                    counts[base["joinStatus"]] += 1
                    continue
                # Only an explicit ParamOutput with ParamSource=0 can create
                # a handle.  ParamSource=100/property/unknown rows remain
                # runtime/property evidence and cannot become producers.
                if source_kind != "output":
                    base["role"] = "unresolved"
                    base["joinStatus"] = "unresolved_invalid_producer_parameter_source"
                    details.append(base)
                    counts[base["joinStatus"]] += 1
                    continue
                # Shadowed physical records and topology-unavailable rows are
                # not active producers.  The latter are retained as an
                # explicit unresolved source rather than guessed active.
                if row.get("runtimeSlotStatus") == "active-final-serialized-slot":
                    producers[key].append(base)
                else:
                    base["joinStatus"] = "unresolved_inactive_or_unvalidated_producer"
                    details.append(base)
                    counts[base["joinStatus"]] += 1
            else:
                if not path_valid:
                    base["role"] = "unresolved"
                    base["joinStatus"] = "unresolved_malformed_serialized_output_path"
                    details.append(base)
                    counts[base["joinStatus"]] += 1
                    continue
                # A consumer must be an explicitly serialized ParamSource=0
                # dynamic path. ParamSource=100 and unknown sources remain
                # runtime-unresolved and cannot become a handle consumer.
                if (
                    source_kind != "runtime"
                    or type(field.get("paramSource")) is not int
                    or field.get("paramSource") != 0
                    or field.get("bindingKind") != "dynamic"
                ):
                    base["role"] = "unresolved"
                    base["joinStatus"] = "unresolved_invalid_consumer_parameter_source"
                    details.append(base)
                    counts[base["joinStatus"]] += 1
                    continue
                consumers.append(base)

    for consumer in consumers:
        key = (
            str(consumer.get("levelScriptId") or ""),
            str(consumer.get("sourceRoot") or ""),
            str(consumer.get("sourcePath") or ""),
            str(consumer.get("lifecycleKind") or ""),
            str(consumer.get("serializedOutputPath") or ""),
        )
        candidates = producers.get(key) or []
        blockers = producer_blockers.get(key) or []
        blocker_statuses = {
            str(row.get("producerBlockerStatus") or "")
            for row in blockers
        }
        if (
            len(candidates) == 1
            and len(blockers) == 1
            and blocker_statuses == {"active"}
        ):
            producer = candidates[0]
            joined = {
                **consumer,
                "joinStatus": "exact_unique_active_producer",
                "producer": producer,
                "consumer": {
                    key: consumer.get(key)
                    for key in (
                        "action", "levelScriptId", "actionIdentity", "fieldName",
                    )
                    if consumer.get(key) not in (None, "", [])
                },
            }
            details.append(joined)
            details.append({
                **producer,
                "joinStatus": "exact_unique_active_producer",
                "consumer": {
                    key: consumer.get(key)
                    for key in (
                        "action", "levelScriptId", "actionIdentity", "fieldName",
                    )
                    if consumer.get(key) not in (None, "", [])
                },
            })
            counts["exact_unique_active_producer"] += 1
            continue
        status = (
            "unresolved_ambiguous_or_shadowed_producer"
            if len(blockers) > 1
            else "unresolved_invalid_or_inactive_producer"
            if blockers and blocker_statuses != {"active"}
            else "unresolved_ambiguous_active_producer"
            if len(candidates) > 1
            else "unresolved_no_unique_active_producer"
        )
        details.append({
            **consumer,
            "joinStatus": status,
            "producerCandidateCount": len(candidates),
        })
        counts[status] += 1

    # Producers are always retained, including PostAudioCue's output-only
    # cueHandlerId.  This makes the producer-only boundary visible without
    # implying a consumer or current runtime state.
    joined_keys = {
        (
            str(row.get("levelScriptId") or ""),
            str(row.get("sourceRoot") or ""),
            str(row.get("sourcePath") or ""),
            str(row.get("lifecycleKind") or ""),
            str(row.get("serializedOutputPath") or ""),
        )
        for row in details
        if row.get("joinStatus") == "exact_unique_active_producer"
    }
    for key, rows in producers.items():
        for producer in rows:
            if key in joined_keys:
                continue
            producer_only = {
                **producer,
                "joinStatus": "producer_only",
            }
            details.append(producer_only)
            counts["producer_only"] += 1

    # Attach a compact static summary to each action occurrence.  Full path
    # and identity detail remains on the lazy event detail context.
    by_identity: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for detail in details:
        identity = detail.get("actionIdentity") or {}
        key = (
            str(identity.get("levelScriptId") or ""),
            int(identity.get("recordStart") or -1),
            str(identity.get("action") or ""),
        )
        by_identity[key].append(detail)
    for row in action_rows:
        key = (
            str(row.get("levelScriptId") or ""),
            int(row.get("recordStart") or -1),
            str(row.get("action") or ""),
        )
        row_details = by_identity.get(key) or []
        if row_details:
            row["levelScriptAudioLifecycle"] = row_details
    summary = {
        "schemaVersion": 1,
        "counts": dict(sorted(counts.items())),
        "total": len(details),
        "exactJoinCount": counts.get("exact_unique_active_producer", 0),
        "producerOnlyCount": counts.get("producer_only", 0),
        "unresolvedCount": sum(
            count for status, count in counts.items() if status.startswith("unresolved_")
        ),
        "storyOrderEvidence": False,
        "evidenceBoundary": (
            "Only same-LevelScript exact serialized output paths are joined to a "
            "unique active producer. ParamSource=100 remains runtime-unresolved; "
            "this catalog does not claim execution, current state, or a native "
            "playback route."
        ),
    }
    details.sort(key=lambda row: (
        str(row.get("levelScriptId") or ""),
        int((row.get("actionIdentity") or {}).get("recordStart") or 0),
        str(row.get("role") or ""),
        str(row.get("lifecycleKind") or ""),
    ))
    return details, summary

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

    cue_semantics = cue_semantics or table_contexts.collect_audio_cue_semantics(export_root)
    cue_definitions = cue_semantics.get("cueDefinitions") or {}
    from scripts.story_builder.level_bindings import (
        resolve_levelscript_dynamic_property_string,
        resolve_levelscript_dynamic_property_string_list,
    )

    if decode_file is None:
        from scripts.story_builder.levelscript_binary import (
            decode_levelscript_record_payload,
            extract_levelscript_uid_records,
            levelscript_action_map_membership,
            levelscript_record_semantic_key,
        )
        from scripts.story_builder.level_bindings import (
            decode_levelscript_native_action_topology,
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
            topology, topology_diagnostic = decode_levelscript_native_action_topology(data)
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
                "topology": topology,
                "topologyDiagnostic": topology_diagnostic,
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
    lifecycle_action_rows: list[dict[str, Any]] = []
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
                for key, value in _decorate_levelscript_audio_field(field).items()
                if key in {
                    "sourceField", "present", "bindingKind", "value", "idRef",
                    "paramSource", "path", "logicId", "slotId", "useSlotId",
                    "sourceKind", "parameterSourceKind", "parameterStatus",
                    "resolutionStatus", "resolvedValue", "resolvedEventName",
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
        topology = decoded.get("topology") if isinstance(decoded, dict) else None
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
            action_map_role = str(row.get("actionMapRole") or "")
            topology_facts = _levelscript_topology_action_facts(topology, record)
            # A custom focused decoder may provide only the maintained
            # actionList membership.  Its ordinal still comes from the
            # serialized membership label, never from the filtered audio row
            # index.  Native control-flow facts remain unavailable unless the
            # complete topology validator succeeded.
            if topology_facts.get("serializedActionOrdinal") is None:
                fallback_ordinal = _levelscript_action_ordinal(action_map_role)
                if fallback_ordinal is not None and (
                    topology_facts.get("topologyEvidence") is not True
                    or topology_facts.get("topologyStatus") in {
                        "shadowed_physical_record",
                        "not_active_action_slot",
                    }
                ):
                    topology_facts["serializedActionOrdinal"] = fallback_ordinal
                    topology_facts["ordinalEvidence"] = "actionListMembershipOnly"
            common = {
                "confidence": "direct",
                "semanticRole": "authoredLevelScriptAudioAction",
                "action": action_name,
                "levelScriptId": levelscript_id,
                "sourceRoot": source_root,
                "sourcePath": source_path,
                "sourceSha256": source_sha256,
                **topology_facts,
                "recordStart": int(record.get("start") or 0),
                "recordUid": str(record.get("uid") or ""),
                "recordLocalId": record.get("localId"),
                "actionMapRole": action_map_role,
                "unionTag": record.get("unionTag"),
                "serializedMemberCount": record.get("serializedMemberCount"),
                "nativeMappingId": str(action.get("nativeMappingId") or ""),
                "payloadShape": str(action.get("payloadShape") or ""),
                "fields": fields,
                "runtimeActivationStatus": "levelScriptActionExecutionNotObserved",
            }
            lifecycle_action_rows.append({
                **common,
                "fields": fields,
            })
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
                    "sourceKind": _levelscript_parameter_source(radio_field),
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
                        "sourceKind": _levelscript_parameter_source(field),
                        "resolutionStatus": (
                            "propertyValueUnresolved"
                            if _levelscript_parameter_source(field) == "property"
                            else "runtimeParamValueUnresolved"
                        ),
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
                    "sourceKind": _levelscript_parameter_source(field),
                    "resolutionStatus": (
                        "propertyValueUnresolved"
                        if _levelscript_parameter_source(field) == "property"
                        else "runtimeParamValueUnresolved"
                    ),
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
                            fields[field_name] = {
                                **field,
                                "resolutionStatus": "resolvedLevelScriptBriefProperty",
                                "parameterStatus": "property_value_resolved",
                                "resolvedValue": resolved_event_name,
                            }
                            dynamic_binding.update({
                                "resolutionStatus": "resolvedLevelScriptBriefProperty",
                                "sourceKind": "property",
                                "binding": fields[field_name],
                                "resolvedEventName": resolved_event_name,
                                "resolvedValue": resolved_event_name,
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

    lifecycle_details, lifecycle_summary = _build_levelscript_audio_lifecycle(
        lifecycle_action_rows
    )
    lifecycle_by_action: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for action_row in lifecycle_action_rows:
        key = (
            str(action_row.get("levelScriptId") or ""),
            int(action_row.get("recordStart") or -1),
            str(action_row.get("action") or ""),
        )
        for detail in action_row.get("levelScriptAudioLifecycle") or []:
            lifecycle_by_action[key].append(detail)

    def attach_lifecycle(row: Any) -> None:
        if not isinstance(row, dict):
            return
        key = (
            str(row.get("levelScriptId") or ""),
            int(row.get("recordStart") or -1),
            str(row.get("action") or ""),
        )
        details = lifecycle_by_action.get(key) or []
        if details:
            row["levelScriptAudioLifecycle"] = details

    for rows_by_event in contexts.values():
        for context in rows_by_event:
            attach_lifecycle(context)
    for collection in (
        cue_invocations, dynamic_event_bindings, resolved_dynamic_event_bindings,
        radio_invocations, voice_invocations, dynamic_radio_bindings,
        resolved_dynamic_radio_bindings, control_actions, dynamic_control_bindings,
    ):
        for row in collection:
            attach_lifecycle(row)

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
        # Full lifecycle rows are consumed only by lazy event details.  The
        # compact catalog receives lifecycle_summary below.
        "levelScriptAudioLifecycle": {
            "summary": lifecycle_summary,
            "details": lifecycle_details,
        },
        "lifecycleBindings": lifecycle_details,
        "lifecycleSummary": lifecycle_summary,
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
            "levelScriptAudioLifecycle": lifecycle_summary,
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
            "runtime-selected list index remains unobserved. LevelScript lifecycle rows join only "
            "same-script exact serialized output paths to unique active producers; authored fades, "
            "release flags, constants, and output-only cue handles remain serialized controls, not "
            "current state or execution evidence."
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
