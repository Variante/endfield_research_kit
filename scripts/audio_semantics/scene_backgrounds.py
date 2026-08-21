"""Recover authored scene ambience definitions from the published object index.

This domain deliberately keeps three different facts separate:

* ``AudioMapData`` assigns lifecycle Events, outdoor room tone, and an aux bus
  to an exact serialized scene-name index;
* scene-bound audio components author positioned Event requests, but do not by
  themselves prove which level owns an asset or that the component was active;
* the Wwise index supplies possible media leaves, not a runtime-selected leaf.

The merged AnimeStudio object-index ``summary.json`` is the commit marker.  A
missing, incomplete, or hash-invalid summary fails closed before any rows are
published.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import identifiers
from .context_utils import append_context


if __package__ == "scripts.audio_semantics":
    from scripts.export_full_from_game import (
        animestudio_object_index_dir,
        load_animestudio_object_index_summary,
    )
elif __package__ == "audio_semantics":
    from export_full_from_game import (
        animestudio_object_index_dir,
        load_animestudio_object_index_summary,
    )
else:  # pragma: no cover - only the two maintained package identities work.
    raise ImportError(
        "import as scripts.audio_semantics.scene_backgrounds or "
        "audio_semantics.scene_backgrounds"
    )


SCHEMA_VERSION = 1
AUDIO_MAP_DATA_TYPE = "Beyond.Gameplay.Audio.AudioMapData"
SCENE_EMITTER_TYPES = frozenset({
    "Beyond.Gameplay.Audio.AudioEffectSoundMono",
    "Beyond.Gameplay.Audio.AudioParticleEffectSoundMono",
    "Beyond.Gameplay.Audio.AudioSceneObject",
    "Beyond.Gameplay.EffectSetting",
})
SCENE_NAME_RE = re.compile(r"^\$\.levelGlobalEvents\._sceneNames\[(\d+)\]$")
SCENE_STATE_COUNT_RE = re.compile(
    r"^\$\.levelGlobalEvents\._sceneStateCount\[(\d+)\]$"
)
STATE_RE = re.compile(r"^\$\.levelGlobalEvents\._states\[(\d+)\](.*)$")
GLOBAL_FIELD_RE = re.compile(
    r"^\$\.levelGlobalEvents\._events\[(\d+)\]\.(.+)$"
)
INDEXED_EVENT_RE = re.compile(r"^(levelInitEvents|levelExitEvents)\[(\d+)\]$")
EVENT_HASH_FIELD_RE = re.compile(
    r"(?:audio|sound|event).*?(?:\._id|event)$", re.IGNORECASE
)
AMBIENCE_NAME_MARKERS = (
    "au_amb_", "ambient", "ambience", "roomtone", "room_tone",
)


class SceneBackgroundError(RuntimeError):
    """Raised when the published object-index evidence cannot be trusted."""


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("object")
    if not isinstance(value, dict):
        return {}
    return {
        key: value.get(key)
        for key in ("serializedFile", "source", "sourceOffset", "pathId")
        if value.get(key) is not None
    }


def _scalars(row: dict[str, Any]) -> Iterable[tuple[str, str, Any]]:
    for scalar in row.get("scalars") or ():
        if not isinstance(scalar, list) or len(scalar) != 3:
            continue
        path, kind, value = scalar
        if isinstance(path, str) and isinstance(kind, str):
            yield path, kind, value


def _event_hash(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value == 0:
        return None
    return value & 0xFFFFFFFF


def _media_lookup(audio_index: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in audio_index.get("entries") or ():
        if not isinstance(row, dict):
            continue
        try:
            media_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        result[media_id] = row
    return result


def _wwise_lookup(audio_index: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in audio_index.get("wwiseEventInventory") or ():
        if not isinstance(row, dict) or not isinstance(row.get("eventHash"), int):
            continue
        result[int(row["eventHash"]) & 0xFFFFFFFF] = row
    return result


def _project_media(row: dict[str, Any]) -> dict[str, Any]:
    projected = {
        key: row.get(key)
        for key in ("id", "src", "duration", "bytes", "category", "codec")
        if row.get(key) is not None
    }
    try:
        projected["id"] = int(row.get("id"))
    except (TypeError, ValueError):
        pass
    return projected


def _join_event(
    event_hash: int,
    wwise_by_hash: dict[int, dict[str, Any]],
    media_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    wwise = wwise_by_hash.get(event_hash)
    if not wwise:
        return {
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "eventId": None,
            "eventIdentityStatus": "notFoundInWwise",
            "traversalStatus": None,
            "possibleMedia": [],
        }
    media_ids: list[int] = []
    for value in wwise.get("mediaIds") or ():
        try:
            media_id = int(value)
        except (TypeError, ValueError):
            continue
        if media_id not in media_ids:
            media_ids.append(media_id)
    return {
        "eventHash": event_hash,
        "eventHashHex": f"0x{event_hash:08x}",
        "eventId": wwise.get("eventId") or f"hashed-event:0x{event_hash:08x}",
        "eventIdentityStatus": (
            wwise.get("eventIdentityStatus")
            or "wwiseObjectWithoutRecoveredTriggerName"
        ),
        "traversalStatus": wwise.get("traversalStatus"),
        "mediaRelationTypes": list(wwise.get("mediaRelationTypes") or ()),
        "possibleMedia": [
            _project_media(media_by_id[media_id])
            if media_id in media_by_id
            else {"id": media_id, "status": "decodedMediaNotIndexed"}
            for media_id in media_ids
        ],
    }


def _merge_context_maps(
    target: dict[str, list[dict[str, Any]]],
    additions: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for source in (target, additions):
        for event_id, rows in source.items():
            for row in rows:
                if isinstance(row, dict):
                    append_context(merged, seen, event_id, row)
    return dict(merged)


def _mirrored_json(
    export_root: Path,
    relative_path: Path,
) -> tuple[Any, list[dict[str, Any]]]:
    versions: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    data_by_hash: dict[str, bytes] = {}
    for source in ("Persistent", "StreamingAssets"):
        path = export_root / "structured" / source / relative_path
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise SceneBackgroundError(f"cannot read {path}: {exc}") from exc
        digest = hashlib.sha256(data).hexdigest()
        versions[digest].append((source, path))
        data_by_hash[digest] = data
    if not versions:
        return None, []
    if len(versions) != 1:
        details = ", ".join(
            f"{digest}:{'/'.join(source for source, _path in rows)}"
            for digest, rows in sorted(versions.items())
        )
        raise SceneBackgroundError(
            f"conflicting mirrored {relative_path.as_posix()}: {details}"
        )
    digest = next(iter(versions))
    try:
        payload = json.loads(data_by_hash[digest])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SceneBackgroundError(
            f"invalid mirrored JSON {relative_path.as_posix()}: {exc}"
        ) from exc
    evidence = [{
        "source": source,
        "path": str(path.relative_to(export_root)).replace("\\", "/"),
        "sha256": digest,
    } for source, path in versions[digest]]
    return payload, evidence


def _collect_audio_level_semantics(
    export_root: Path,
    wwise_by_hash: dict[int, dict[str, Any]],
    media_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    payload, evidence = _mirrored_json(export_root, Path("Table/AudioLevel.json"))
    if payload is None:
        return {
            "status": "unavailable",
            "sources": [],
            "levels": [],
            "eventContexts": {},
            "error": "Table/AudioLevel.json is missing from both structured roots",
        }
    if not isinstance(payload, dict):
        raise SceneBackgroundError("Table/AudioLevel.json root is not an object")
    source_path = evidence[0]["path"]
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    levels: list[dict[str, Any]] = []
    for level_id, raw in sorted(payload.items()):
        if not isinstance(level_id, str) or not isinstance(raw, dict):
            continue
        events: list[dict[str, Any]] = []
        for ordinal, value in enumerate(raw.get("levelInitEvent") or ()):
            value_hash = _event_hash(value)
            if value_hash is None:
                continue
            events.append({
                "role": "levelInitEvent",
                "ordinal": ordinal,
                "signedValue": value,
                **_join_event(value_hash, wwise_by_hash, media_by_id),
            })
        battle_hash = _event_hash(raw.get("battleMusicTriggerEvent"))
        if battle_hash is not None:
            events.append({
                "role": "battleMusicTriggerEvent",
                "ordinal": None,
                "signedValue": raw.get("battleMusicTriggerEvent"),
                **_join_event(battle_hash, wwise_by_hash, media_by_id),
            })
        for event in events:
            append_context(
                contexts,
                seen,
                identifiers.event_hash_context_key(event["eventHash"]),
                _event_context(
                    source=source_path,
                    owner={"table": "AudioLevel", "levelId": level_id},
                    role=str(event["role"]),
                    event_hash=int(event["eventHash"]),
                    scene_id=level_id,
                ),
            )
        levels.append({
            "sceneId": level_id,
            "customMusicModeBaseState": raw.get("customMusicModeBaseState"),
            "events": events,
        })
    return {
        "status": "exactMirroredTable" if len(evidence) > 1 else "exactTable",
        "sources": evidence,
        "levels": levels,
        "eventContexts": dict(contexts),
    }


def _collect_mission_scene_refs(export_root: Path) -> dict[str, Any]:
    roots = [
        export_root / "structured" / source / "Data/Json/MissionRuntimeAsset"
        for source in ("Persistent", "StreamingAssets")
    ]
    refs: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    physical_files = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.glob("*_meta.json"):
            physical_files += 1
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            mission_id = str(payload.get("missionId") or "").strip()
            accept_mode = payload.get("acceptMode")
            scene_id = (
                str(accept_mode.get("levelId") or "").strip()
                if isinstance(accept_mode, dict) else ""
            )
            if not mission_id or not scene_id:
                continue
            evidence_path = str(path.relative_to(export_root)).replace("\\", "/")
            current = refs.get(mission_id)
            if current and current["sceneId"] != scene_id:
                conflicts.append({
                    "missionId": mission_id,
                    "firstSceneId": current["sceneId"],
                    "conflictingSceneId": scene_id,
                    "source": evidence_path,
                })
                continue
            if current:
                current["sources"].append(evidence_path)
            else:
                refs[mission_id] = {
                    "missionId": mission_id,
                    "sceneId": scene_id,
                    "mappingStatus": "exactMissionAcceptModeLevelId",
                    "sources": [evidence_path],
                }
    return {
        "status": "conflicting" if conflicts else ("exact" if refs else "unavailable"),
        "physicalFilesScanned": physical_files,
        "refs": [refs[key] for key in sorted(refs)],
        "conflicts": conflicts,
    }


def _event_context(
    *,
    source: str,
    owner: dict[str, Any],
    role: str,
    event_hash: int,
    scene_id: str | None = None,
    authored_name: str | None = None,
    placement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "kind": "sceneGlobalAudioEvent" if scene_id else "sceneEmitterAudioEvent",
        "semanticRole": role,
        "source": source,
        "owner": owner,
        "eventHash": event_hash,
        "eventHex": f"0x{event_hash:08x}",
        "confidence": "direct",
        "evidence": (
            "exactAudioMapDataSceneIndex"
            if scene_id else "exactObjectIndexSceneComponentScalar"
        ),
        "triggerRuntimeActivationStatuses": [
            "authoredDefinitionOnly",
            "runtimeActivationNotObserved",
            "wwiseBranchSelectionNotObserved",
        ],
    }
    if scene_id:
        context["sceneId"] = scene_id
    if authored_name:
        context["authoredEventName"] = authored_name
    if placement:
        context["placement"] = placement
    return context


def _scene_position(scene_context: Any) -> dict[str, Any] | None:
    if not isinstance(scene_context, dict):
        return None
    hierarchy = scene_context.get("hierarchyPath")
    result: dict[str, Any] = {
        "gameObjectName": scene_context.get("gameObjectName"),
        "hierarchyPath": list(hierarchy) if isinstance(hierarchy, list) else [],
        "worldPositionStatus": scene_context.get("worldPositionStatus"),
    }
    for key in ("gameObject", "transform"):
        value = scene_context.get(key)
        if isinstance(value, dict):
            result[key] = {
                identity_key: value.get(identity_key)
                for identity_key in (
                    "serializedFile", "source", "sourceOffset", "pathId"
                )
                if value.get(identity_key) is not None
            }
    if scene_context.get("worldPositionStatus") == "exact_transform_hierarchy":
        position = scene_context.get("worldPosition")
        if isinstance(position, dict):
            result["worldPosition"] = {
                key: position.get(key) for key in ("x", "y", "z")
                if isinstance(position.get(key), (int, float))
                and not isinstance(position.get(key), bool)
            }
    return result


def _parse_audio_map(
    row: dict[str, Any],
    source: str,
    wwise_by_hash: dict[int, dict[str, Any]],
    media_by_id: dict[int, dict[str, Any]],
    contexts: dict[str, list[dict[str, Any]]],
    context_seen: dict[str, set[str]],
) -> dict[str, Any]:
    scene_names: dict[int, str] = {}
    state_counts: dict[int, int] = {}
    state_scalars: dict[int, list[dict[str, Any]]] = defaultdict(list)
    event_fields: dict[int, list[dict[str, Any]]] = defaultdict(list)
    parameter_fields: dict[int, list[dict[str, Any]]] = defaultdict(list)
    asset_wide_fields: dict[str, list[dict[str, Any]]] = defaultdict(list)
    shape_group_fields: list[dict[str, Any]] = []

    for path, kind, value in _scalars(row):
        match = SCENE_NAME_RE.fullmatch(path)
        if match and isinstance(value, str) and value:
            scene_names[int(match.group(1))] = value
            continue
        match = SCENE_STATE_COUNT_RE.fullmatch(path)
        if match and isinstance(value, int) and not isinstance(value, bool):
            state_counts[int(match.group(1))] = value
            continue
        match = STATE_RE.fullmatch(path)
        if match:
            state_scalars[int(match.group(1))].append({
                "path": match.group(2) or "$", "kind": kind, "value": value,
            })
            continue
        match = GLOBAL_FIELD_RE.fullmatch(path)
        if match:
            event_index = int(match.group(1))
            field = match.group(2)
            indexed = INDEXED_EVENT_RE.fullmatch(field)
            role = indexed.group(1) if indexed else field
            ordinal = int(indexed.group(2)) if indexed else None
            if role in {"levelInitEvents", "levelExitEvents", "outdoorRoomToneEvent"}:
                value_hash = _event_hash(value)
                if value_hash is not None:
                    event_fields[event_index].append({
                        "role": role, "ordinal": ordinal, "eventHash": value_hash,
                    })
                continue
            if role == "outdoorRoomAuxBusId":
                value_hash = _event_hash(value)
                if value_hash is not None:
                    parameter_fields[event_index].append({
                        "role": "outdoorRoomAuxBus", "auxBusId": value_hash,
                        "auxBusIdHex": f"0x{value_hash:08x}",
                    })
                continue
            parameter_fields[event_index].append({
                "path": field, "kind": kind, "value": value,
            })
            continue
        if path.startswith("$.shapeIdToTriggerGroupIdx"):
            shape_group_fields.append({"path": path, "kind": kind, "value": value})
            continue
        for prefix, role in (
            ("$.triggerFunctions", "triggerFunction"),
            ("$.volumetricEmitterFunctions", "volumetricEmitterFunction"),
        ):
            if not path.startswith(prefix):
                continue
            value_hash = _event_hash(value)
            if value_hash is not None and EVENT_HASH_FIELD_RE.search(path):
                asset_wide_fields[role].append({
                    "path": path,
                    **_join_event(value_hash, wwise_by_hash, media_by_id),
                })
            elif isinstance(value, str) and value.lower().startswith("au_"):
                value_hash = identifiers.audio_hash_generator_compute(value)
                asset_wide_fields[role].append({
                    "path": path, "authoredEventName": value,
                    **_join_event(value_hash, wwise_by_hash, media_by_id),
                })
            break

    state_cursor = 0
    owner = _identity(row)
    scene_rows: list[dict[str, Any]] = []
    all_indices = sorted(set(scene_names) | set(state_counts) | set(event_fields) | set(parameter_fields))
    for event_index in all_indices:
        scene_id = scene_names.get(event_index)
        count = max(int(state_counts.get(event_index) or 0), 0)
        states = [
            {"stateIndex": index, "scalars": state_scalars.get(index, [])}
            for index in range(state_cursor, state_cursor + count)
        ]
        state_cursor += count
        events: list[dict[str, Any]] = []
        for event in event_fields.get(event_index, []):
            joined = {
                "role": event["role"], "ordinal": event["ordinal"],
                **_join_event(event["eventHash"], wwise_by_hash, media_by_id),
            }
            events.append(joined)
            if scene_id:
                append_context(
                    contexts,
                    context_seen,
                    identifiers.event_hash_context_key(event["eventHash"]),
                    _event_context(
                        source=source, owner=owner, role=event["role"],
                        event_hash=event["eventHash"], scene_id=scene_id,
                    ),
                )
        scene_rows.append({
            "eventIndex": event_index,
            "sceneId": scene_id,
            "sceneMappingStatus": (
                "exactSerializedSceneNameIndex"
                if scene_id else "unresolvedEventIndexWithoutSceneName"
            ),
            "sceneStateCount": state_counts.get(event_index),
            "states": states,
            "events": events,
            "roomToneParameters": parameter_fields.get(event_index, []),
        })

    return {
        "source": source,
        "audioMapData": str(row.get("name") or ""),
        "identity": owner,
        "scenes": scene_rows,
        "assetWideEvents": {
            key: rows for key, rows in sorted(asset_wide_fields.items()) if rows
        },
        "shapeToTriggerGroupScalars": shape_group_fields,
    }


def _parse_emitter(
    row: dict[str, Any],
    source: str,
    wwise_by_hash: dict[int, dict[str, Any]],
    media_by_id: dict[int, dict[str, Any]],
    contexts: dict[str, list[dict[str, Any]]],
    context_seen: dict[str, set[str]],
) -> dict[str, Any] | None:
    script = row.get("script") if isinstance(row.get("script"), dict) else {}
    full_name = str(script.get("fullName") or "")
    requests: list[dict[str, Any]] = []
    seen_requests: set[tuple[int, str]] = set()
    for path, _kind, value in _scalars(row):
        authored_name: str | None = None
        value_hash: int | None = None
        if isinstance(value, str) and value.lower().startswith("au_"):
            authored_name = value
            value_hash = identifiers.audio_hash_generator_compute(value)
        elif EVENT_HASH_FIELD_RE.search(path):
            value_hash = _event_hash(value)
        if value_hash is None:
            continue
        key = (value_hash, path)
        if key in seen_requests:
            continue
        seen_requests.add(key)
        role = "authoredSceneEmitterEvent"
        if authored_name and any(marker in authored_name.lower() for marker in AMBIENCE_NAME_MARKERS):
            role = "authoredAmbientEmitterCandidate"
        requests.append({
            "path": path,
            "semanticRole": role,
            **({"authoredEventName": authored_name} if authored_name else {}),
            **_join_event(value_hash, wwise_by_hash, media_by_id),
        })

    if not requests:
        return None
    owner = _identity(row)
    placement = _scene_position(row.get("sceneContext"))
    for request in requests:
        append_context(
            contexts,
            context_seen,
            identifiers.event_hash_context_key(request["eventHash"]),
            _event_context(
                source=source,
                owner=owner,
                role=request["semanticRole"],
                event_hash=request["eventHash"],
                authored_name=request.get("authoredEventName"),
                placement=placement,
            ),
        )
    return {
        "source": source,
        "componentType": full_name,
        "name": str(row.get("name") or ""),
        "identity": owner,
        "placement": placement,
        "sceneOwnershipStatus": "objectIndexSceneContextWithoutSceneAssetJoin",
        "eventRequests": requests,
    }


def build_scene_background_catalog(
    rows_by_source: dict[str, Iterable[dict[str, Any]]],
    audio_index: dict[str, Any],
    *,
    source_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the catalog from already validated, single-pass object streams."""
    wwise_by_hash = _wwise_lookup(audio_index)
    media_by_id = _media_lookup(audio_index)
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    context_seen: dict[str, set[str]] = defaultdict(set)
    audio_maps: list[dict[str, Any]] = []
    emitters: list[dict[str, Any]] = []
    scanned_counts: Counter[str] = Counter()

    for source, rows in rows_by_source.items():
        for row in rows:
            if not isinstance(row, dict) or row.get("recordType") != "object":
                continue
            scanned_counts[source] += 1
            script = row.get("script") if isinstance(row.get("script"), dict) else {}
            full_name = str(script.get("fullName") or "")
            if full_name == AUDIO_MAP_DATA_TYPE:
                audio_maps.append(_parse_audio_map(
                    row, source, wwise_by_hash, media_by_id, contexts, context_seen,
                ))
            elif full_name in SCENE_EMITTER_TYPES:
                emitter = _parse_emitter(
                    row, source, wwise_by_hash, media_by_id, contexts, context_seen,
                )
                if emitter:
                    emitters.append(emitter)

    scene_definitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_scene_rows: list[dict[str, Any]] = []
    for audio_map in audio_maps:
        for scene in audio_map["scenes"]:
            definition = {
                "source": audio_map["source"],
                "audioMapData": audio_map["audioMapData"],
                "identity": audio_map["identity"],
                **scene,
            }
            if scene.get("sceneId"):
                scene_definitions[str(scene["sceneId"])].append(definition)
            else:
                unresolved_scene_rows.append(definition)
    scenes = [
        {"sceneId": scene_id, "definitions": scene_definitions[scene_id]}
        for scene_id in sorted(scene_definitions)
    ]
    event_occurrences = [
        event
        for scene in scenes
        for definition in scene["definitions"]
        for event in definition.get("events") or ()
    ]
    emitter_requests = [
        request for emitter in emitters for request in emitter["eventRequests"]
    ]
    possible_media_ids = {
        int(media["id"])
        for event in event_occurrences + emitter_requests
        for media in event.get("possibleMedia") or ()
        if isinstance(media, dict) and isinstance(media.get("id"), int)
    }
    boundary = (
        "AudioMapData scene names, state counts, lifecycle Events, room-tone Event, and "
        "aux-bus ids are exact serialized definitions. Scene component requests and exact "
        "transform-hierarchy positions are authored placements; prefab-local ownership is "
        "not promoted to a level join. Wwise leaves are possible media only. Runtime scene "
        "activation, live State/RTPC values, listener position, branch selection, playback, "
        "and audibility remain unobserved."
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "validatedPublishedObjectIndex",
        "sources": source_evidence or [],
        "counts": {
            "objectRowsScannedBySource": dict(sorted(scanned_counts.items())),
            "audioMapDataAssets": len(audio_maps),
            "exactNamedScenes": len(scenes),
            "sceneDefinitions": sum(len(row["definitions"]) for row in scenes),
            "unresolvedSceneDefinitions": len(unresolved_scene_rows),
            "sceneGlobalEventOccurrences": len(event_occurrences),
            "sceneGlobalEventsFoundInWwise": sum(
                row.get("eventIdentityStatus") != "notFoundInWwise"
                for row in event_occurrences
            ),
            "sceneGlobalEventsWithPossibleMedia": sum(
                bool(row.get("possibleMedia")) for row in event_occurrences
            ),
            "sceneEmitterComponents": len(emitters),
            "sceneEmitterEventRequests": len(emitter_requests),
            "ambientEmitterCandidateRequests": sum(
                row.get("semanticRole") == "authoredAmbientEmitterCandidate"
                for row in emitter_requests
            ),
            "uniquePossibleMedia": len(possible_media_ids),
        },
        "scenes": scenes,
        "unresolvedSceneDefinitions": unresolved_scene_rows,
        "audioMaps": audio_maps,
        "sceneEmitters": emitters,
        "eventContexts": dict(contexts),
        "evidenceBoundary": boundary,
    }


def _iter_gzip_rows(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise SceneBackgroundError(
                        f"{path}:{line_number}: object-index row is not an object"
                    )
                yield row
    except (OSError, EOFError, json.JSONDecodeError) as exc:
        raise SceneBackgroundError(f"cannot read published object index {path}: {exc}") from exc


def collect_scene_background_semantics(
    export_root: Path,
    audio_index: dict[str, Any],
    *,
    sources: tuple[str, ...] = ("StreamingAssets", "Persistent"),
) -> dict[str, Any]:
    """Load validated merged indexes, scan each once, and build the catalog."""
    rows_by_source: dict[str, Iterable[dict[str, Any]]] = {}
    evidence: list[dict[str, Any]] = []
    expected_counts: dict[str, int] = {}
    for source in sources:
        summary = load_animestudio_object_index_summary(export_root, source)
        if summary is None:
            raise SceneBackgroundError(
                f"{source}: no published object index; run an installed-game Story/all "
                "export with --animestudio-object-index"
            )
        if summary.get("complete") is not True:
            errors = "; ".join(str(value) for value in summary.get("errors") or ())
            raise SceneBackgroundError(
                f"{source}: published object index is invalid: {errors or 'unknown error'}"
            )
        output = (summary.get("outputs") or {}).get("objects") or {}
        relative_name = str(output.get("path") or "")
        if not relative_name or Path(relative_name).name != relative_name:
            raise SceneBackgroundError(f"{source}: merged objects output path is invalid")
        index_dir = animestudio_object_index_dir(export_root, source)
        rows_by_source[source] = _iter_gzip_rows(index_dir / relative_name)
        expected_counts[source] = int((summary.get("counts") or {}).get("objects") or 0)
        evidence.append({
            "source": source,
            "summary": str((index_dir / "summary.json").relative_to(export_root)).replace("\\", "/"),
            "objects": str((index_dir / relative_name).relative_to(export_root)).replace("\\", "/"),
            "objectsSha256": output.get("sha256"),
            "expectedObjectRows": expected_counts[source],
            "stageSignatureSha256": (summary.get("stageSignature") or {}).get("sha256"),
        })

    result = build_scene_background_catalog(
        rows_by_source, audio_index, source_evidence=evidence,
    )
    actual_counts = (result.get("counts") or {}).get("objectRowsScannedBySource") or {}
    for source, expected in expected_counts.items():
        actual = int(actual_counts.get(source) or 0)
        if actual != expected:
            raise SceneBackgroundError(
                f"{source}: merged object count mismatch: {actual} parsed, {expected} published"
            )

    wwise_by_hash = _wwise_lookup(audio_index)
    media_by_id = _media_lookup(audio_index)
    audio_level = _collect_audio_level_semantics(
        export_root, wwise_by_hash, media_by_id,
    )
    mission_scene_refs = _collect_mission_scene_refs(export_root)
    result["audioLevel"] = {
        key: value for key, value in audio_level.items() if key != "eventContexts"
    }
    result["missionSceneRefs"] = mission_scene_refs
    result["eventContexts"] = _merge_context_maps(
        result.get("eventContexts") or {},
        audio_level.get("eventContexts") or {},
    )

    scenes_by_id = {
        str(row.get("sceneId") or ""): row
        for row in result.get("scenes") or ()
        if isinstance(row, dict) and row.get("sceneId")
    }
    for level in audio_level.get("levels") or ():
        if not isinstance(level, dict) or not level.get("sceneId"):
            continue
        scene_id = str(level["sceneId"])
        scene = scenes_by_id.setdefault(scene_id, {
            "sceneId": scene_id,
            "definitions": [],
        })
        scene["audioLevel"] = level
    for ref in mission_scene_refs.get("refs") or ():
        if not isinstance(ref, dict) or not ref.get("sceneId"):
            continue
        scene_id = str(ref["sceneId"])
        scene = scenes_by_id.setdefault(scene_id, {
            "sceneId": scene_id,
            "definitions": [],
        })
        scene.setdefault("missionRefs", []).append(ref)
    result["scenes"] = [scenes_by_id[key] for key in sorted(scenes_by_id)]

    audio_level_events = [
        event
        for level in audio_level.get("levels") or ()
        if isinstance(level, dict)
        for event in level.get("events") or ()
        if isinstance(event, dict)
    ]
    audio_map_events = [
        event
        for scene in result["scenes"]
        for definition in scene.get("definitions") or ()
        for event in definition.get("events") or ()
        if isinstance(event, dict)
    ]
    emitter_events = [
        event
        for emitter in result.get("sceneEmitters") or ()
        for event in emitter.get("eventRequests") or ()
        if isinstance(event, dict)
    ]
    all_events = audio_map_events + audio_level_events
    scene_global_media_ids = {
        int(media["id"])
        for event in all_events
        for media in event.get("possibleMedia") or ()
        if isinstance(media, dict) and isinstance(media.get("id"), int)
    }
    scene_emitter_media_ids = {
        int(media["id"])
        for event in emitter_events
        for media in event.get("possibleMedia") or ()
        if isinstance(media, dict) and isinstance(media.get("id"), int)
    }
    possible_media_ids = {
        int(media["id"])
        for event in all_events + emitter_events
        for media in event.get("possibleMedia") or ()
        if isinstance(media, dict) and isinstance(media.get("id"), int)
    }
    counts = result["counts"]
    counts.update({
        "catalogScenes": len(result["scenes"]),
        "audioLevelRows": len(audio_level.get("levels") or ()),
        "audioLevelEventOccurrences": len(audio_level_events),
        "missionSceneRefs": len(mission_scene_refs.get("refs") or ()),
        "missionSceneRefConflicts": len(mission_scene_refs.get("conflicts") or ()),
        "sceneGlobalEventOccurrences": len(all_events),
        "sceneGlobalEventsFoundInWwise": sum(
            row.get("eventIdentityStatus") != "notFoundInWwise"
            for row in all_events
        ),
        "sceneGlobalEventsWithPossibleMedia": sum(
            bool(row.get("possibleMedia")) for row in all_events
        ),
        "sceneGlobalUniquePossibleMedia": len(scene_global_media_ids),
        "sceneEmitterEventsFoundInWwise": sum(
            row.get("eventIdentityStatus") != "notFoundInWwise"
            for row in emitter_events
        ),
        "sceneEmitterEventsWithPossibleMedia": sum(
            bool(row.get("possibleMedia")) for row in emitter_events
        ),
        "sceneEmitterUniquePossibleMedia": len(scene_emitter_media_ids),
        "uniquePossibleMedia": len(possible_media_ids),
    })
    result["evidenceBoundary"] = (
        "AudioMapData scene names, state counts, lifecycle Events, room-tone Event, "
        "and aux-bus ids are exact serialized definitions. AudioLevel adds exact "
        "level-init and battle-music trigger Events; MissionRuntimeAsset acceptMode.levelId "
        "adds an exact mission-to-scene reference. Scene component requests and exact "
        "transform-hierarchy positions are authored placements, but prefab-local ownership "
        "is not promoted to a level join. Wwise leaves are possible media only. Runtime "
        "scene activation, live State/RTPC values, listener position, branch selection, "
        "playback, and audibility remain unobserved."
    )
    return result
