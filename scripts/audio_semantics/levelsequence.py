"""LevelSequence audio: play actions and the contexts they produce.

Reads authored LevelSequence detail and the active LevelScript overlay. A decoded
play action is authored evidence; sequence evaluation is unobserved."""

from __future__ import annotations

import hashlib
import struct
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .context_utils import append_context as _append_context
from .context_utils import normalize_posix as normalize_posix

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
        if __package__ == "scripts.audio_semantics":
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
