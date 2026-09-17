"""Timeline audio ownership and cue contexts.

Joins Timeline records to the audio they own, including a raw-JSON enrichment pass
and the playable cue contexts. Ownership here is serialized; director evaluation
remains unobserved."""

from __future__ import annotations

import json
import os
import re
from . import identifiers
from . import build_contracts
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .context_utils import append_context as _append_context
from .context_utils import load_json as load_json
from .context_utils import normalize_posix as normalize_posix

AUDIO_MUSIC_ACTION_TYPE_LABELS = {
    0: "DIALOG_MUSIC",
    1: "NORMAL_MUSIC",
    2: "CUSTOM_MUSIC",
}

AUDIO_MUSIC_TRIGGER_ON_SKIP_LABELS = {
    0: "notTriggeredOnSkip",
    1: "triggeredOnSkip",
}

TIMELINE_AUDIO_RUNTIME_CONTRACTS = build_contracts.TIMELINE_AUDIO_RUNTIME_CONTRACTS

def normalize_levelsequence_audio_id(value: Any) -> str:
    """Return the authored sequence id only for the exact ``_Audio`` suffix."""

    text = str(value or "").strip()
    if not text.endswith("_Audio"):
        return ""
    base = text[:-len("_Audio")]
    return base if base.startswith("levelseq_") else ""

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

def _timeline_audio_runtime_contract_id(playable_type: Any) -> str | None:
    """Return a stable static-contract id for a serialized playable type."""

    normalized = re.sub(r"(?:\(Clone\))+$", "", str(playable_type or "")).strip()
    contract = TIMELINE_AUDIO_RUNTIME_CONTRACTS.get(normalized)
    return str(contract.get("id")) if isinstance(contract, dict) else None
