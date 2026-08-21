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
SCENE_CONTAINMENT_DIAGNOSTIC_LIMIT = 4
SCENE_CONTAINMENT_TYPES = frozenset({"SceneAsset", "Level", "LevelAsset"})
PREFAB_CONTAINMENT_TYPES = frozenset({"Prefab", "PrefabAsset"})
UNRESOLVED_CONTAINER_TYPES = frozenset({"SceneAssetContainer", "AssetContainer"})
STREAMING_INSTANCE_CONTRACT_VERSION = 1
STREAMING_INSTANCE_DIAGNOSTIC_LIMIT = 8
SceneIdentityKey = tuple[Any, ...]


class SceneBackgroundError(RuntimeError):
    """Raised when the published object-index evidence cannot be trusted."""


def _streaming_instance_paths(export_root: Path) -> list[Path]:
    """Return generated InitChunkData sidecars without treating names as IDs."""
    root = export_root / "recovered" / "AnimeStudio-cli"
    paths: list[Path] = []
    for source in ("StreamingAssets", "Persistent"):
        sidecar_root = root / source / "map_streaming_instances"
        if sidecar_root.is_dir():
            paths.extend(sorted(path for path in sidecar_root.glob("*.json") if path.is_file()))
    return paths


def _prefab_identity_key(value: Any) -> SceneIdentityKey | None:
    """Accept only an explicit prefab Source+PathID identity from a sidecar."""
    if not isinstance(value, dict) or value.get("status") != "exact":
        return None
    source = value.get("source", value.get("Source"))
    path_id = value.get("pathId", value.get("PathID"))
    if not isinstance(source, str) or not source:
        return None
    if isinstance(path_id, bool) or not isinstance(path_id, int):
        return None
    tokens = _source_tokens(source)
    if len(tokens) != 1:
        return None
    return ("assetMap", tokens[0], path_id)


def _load_streaming_instance_identity_catalog(export_root: Path) -> dict[str, Any]:
    """Load exact prefab->level instance facts, or publish bounded gaps.

    The currently validated InitChunkData sidecars contain entity IDs, names,
    transforms, and raw ECS component columns, but no known prefab AssetMap
    Source+PathID/hash field in the observed schema.  This loader
    deliberately does not derive one from entity names, Mesh joins, positions,
    or chunk filenames.  A future exporter may add an exact ``prefabIdentity``
    object to each instance; only that object can enter ``entries``.
    """
    paths = _streaming_instance_paths(export_root)
    diagnostics: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    total_instances = 0
    exact_instances = 0
    malformed_instances = 0
    unavailable_contracts = 0
    collection_invalid = False

    def report(status: str, reason: str, **extra: Any) -> None:
        if len(diagnostics) < STREAMING_INSTANCE_DIAGNOSTIC_LIMIT:
            diagnostics.append({"status": status, "reason": reason, **extra})

    for path in paths:
        relative = str(path.relative_to(export_root)).replace("\\", "/")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            collection_invalid = True
            report("streamingInstanceSidecarUnreadable", "invalidSidecar", path=relative, error=str(exc))
            continue
        if not isinstance(payload, dict):
            collection_invalid = True
            report("streamingInstanceSidecarMalformed", "rootNotObject", path=relative)
            continue
        level_id = payload.get("levelId")
        if not isinstance(level_id, str) or not level_id:
            collection_invalid = True
            report("streamingInstanceSidecarMalformed", "missingLevelId", path=relative)
            continue
        schema_version = payload.get("schemaVersion")
        contract = payload.get("prefabIdentityContract")
        source_row = {
            "path": relative,
            "levelId": level_id,
            "schemaVersion": schema_version,
            "prefabIdentityContractStatus": (
                contract.get("status") if isinstance(contract, dict) else None
            ),
        }
        sources.append(source_row)
        instances = payload.get("instances")
        if not isinstance(instances, list):
            collection_invalid = True
            report("streamingInstanceSidecarMalformed", "instancesNotAList", path=relative, levelId=level_id)
            continue
        identity_contract_valid = schema_version == 2 and isinstance(contract, dict) and contract.get("status") == "exact"
        if not identity_contract_valid:
            collection_invalid = True
            report(
                "prefabIdentityUnavailable",
                "sidecarLacksPrefabIdentityContract",
                path=relative,
                levelId=level_id,
                schemaVersion=schema_version,
            )
            unavailable_contracts += 1
        elif contract.get("status") != "exact":
            unavailable_contracts += 1
        total_instances += len(instances)
        for ordinal, instance in enumerate(instances):
            if not isinstance(instance, dict):
                collection_invalid = True
                malformed_instances += 1
                report(
                    "streamingInstanceSidecarMalformed",
                    "instanceNotAnObject",
                    path=relative,
                    levelId=level_id,
                    ordinal=ordinal,
                )
                continue
            # A row cannot override a sidecar-level contract failure. This
            # prevents stale/hand-authored exact rows from bypassing the
            # versioned exporter gate.
            if not identity_contract_valid:
                continue
            identity = instance.get("prefabIdentity")
            if not isinstance(identity, dict) or identity.get("status") != "exact":
                collection_invalid = True
                report(
                    "prefabIdentityMalformed",
                    "instanceLacksExactPrefabIdentity",
                    path=relative,
                    levelId=level_id,
                    ordinal=ordinal,
                )
                continue
            key = _prefab_identity_key(identity)
            if key is None:
                collection_invalid = True
                malformed_instances += 1
                report(
                    "prefabIdentityMalformed",
                    "exactIdentityMissingSourcePathId",
                    path=relative,
                    levelId=level_id,
                    ordinal=ordinal,
                )
                continue
            exact_instances += 1
            entries.append({
                "levelId": level_id,
                "entityId": instance.get("entityId"),
                "sourceFile": instance.get("sourceFile"),
                "groupIndex": instance.get("groupIndex"),
                "entityIndex": instance.get("entityIndex"),
                "prefabIdentity": {
                    "source": identity.get("source", identity.get("Source")),
                    "pathId": identity.get("pathId", identity.get("PathID")),
                },
                "identityKey": list(key),
                "evidence": identity.get("evidence") or "exact prefab identity exported by InitChunkData recovery",
            })

    candidate_exact_instances = exact_instances
    if collection_invalid:
        entries = []
        exact_instances = 0
    if exact_instances:
        status = "exactPrefabIdentityEntries"
    elif paths and (diagnostics or unavailable_contracts):
        status = "unavailablePrefabIdentity"
    elif paths:
        status = "unavailableNoPrefabIdentityEntries"
    else:
        status = "unavailableNoStreamingInstanceSidecars"
    return {
        "schemaVersion": STREAMING_INSTANCE_CONTRACT_VERSION,
        "status": status,
        "sources": sources,
        "counts": {
            "sidecars": len(sources),
            "instances": total_instances,
            "exactPrefabIdentityInstances": exact_instances,
            "candidateExactPrefabIdentityInstances": candidate_exact_instances,
            "malformedInstances": malformed_instances,
            "exactPrefabIdentityLevels": len({row["levelId"] for row in entries}),
        },
        "entries": entries,
        "diagnostics": diagnostics,
        "evidenceBoundary": (
            "Only an explicit prefab Source+PathID identity can join a prefab to a placed "
            "level instance. Entity names, positions, matrices, Mesh objects, and chunk "
            "filenames are not identity evidence; the currently validated sidecars expose "
            "no known field for that identity. A future exporter or separately proven "
            "StreamingChunkData relation may add exact evidence."
        ),
    }


def _normalise_asset_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("\\", "/").strip()
    if not normalized or "/" not in normalized:
        return None
    return normalized.casefold()


def _enrich_streaming_instance_asset_paths(
    export_root: Path,
    catalog: dict[str, Any],
    *,
    asset_map_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve exact prefab identities to unique full AssetMap container paths.

    This is the only path-based bridge allowed for the future instance join:
    both sides must first be exact Source+PathID identities, then resolve to
    one complete AssetMap ``Container`` path.  Basename, entity-name, Mesh,
    transform, and similarity joins never enter this function.
    """
    entries = [entry for entry in catalog.get("entries") or () if isinstance(entry, dict)]
    if not entries:
        return catalog
    identities = [
        entry.get("prefabIdentity")
        for entry in entries
        if _prefab_identity_key(entry.get("prefabIdentity")) is not None
    ]
    provided = _asset_map_containment_provider(
        export_root, identities, collected_index=asset_map_index,
    )
    # Keep raw AssetMap rows here.  The general containment normalizer
    # intentionally deduplicates equal candidates for scene-emitter display;
    # prefab identity recovery must see duplicate rows and fail closed.
    _normalized_for_diagnostics, diagnostics = _normalise_scene_containment_index(provided)
    raw_by_identity: dict[SceneIdentityKey, list[dict[str, Any]]] = defaultdict(list)
    for candidate in provided.get("entries") or ():
        if not isinstance(candidate, dict):
            continue
        for candidate_key in _containment_lookup_keys(candidate):
            raw_by_identity[candidate_key].append(candidate)
    duplicate_identity_row_count = 0
    duplicate_diagnostics: list[dict[str, Any]] = []
    duplicate_keys_seen: set[SceneIdentityKey] = set()
    catalog["assetMapResolution"] = {
        "status": "validated" if not diagnostics else "diagnostics",
        "scanEvidence": _bound_rows(provided.get("scanEvidence") or []),
        "diagnostics": _bound_rows(diagnostics),
        "duplicateIdentityRowCount": 0,
    }
    for entry in entries:
        key = _prefab_identity_key(entry.get("prefabIdentity"))
        if key is None:
            continue
        candidates = raw_by_identity.get(key, [])
        all_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
        prefab_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
        families: set[str] = set()
        for candidate in candidates:
            path = _normalise_asset_path(candidate.get("sourceAssetPath"))
            if not path:
                continue
            all_by_path[path].append(candidate)
            containment_type = candidate.get("containmentType")
            if (
                containment_type in PREFAB_CONTAINMENT_TYPES
                or path.endswith(".prefab")
            ):
                family = "prefab"
                prefab_by_path[path].append(candidate)
            elif (
                containment_type in SCENE_CONTAINMENT_TYPES | UNRESOLVED_CONTAINER_TYPES
                or path.endswith(".unity")
            ):
                family = "scene"
            else:
                family = "other"
            families.add(family)
        duplicate_count = sum(max(0, len(rows) - 1) for rows in all_by_path.values())
        if duplicate_count and key not in duplicate_keys_seen:
            duplicate_keys_seen.add(key)
            duplicate_identity_row_count += duplicate_count
            duplicate_diagnostics.append({
                "status": "duplicateAssetMapIdentity",
                "reason": "multipleAssetMapRowsForSameSourcePathId",
                "identityKey": list(key),
                "duplicateRowCount": duplicate_count,
                "sourceAssetPaths": sorted(all_by_path),
            })
        if "prefab" in families and len(families) > 1:
            entry["prefabAssetPathStatus"] = "conflictingAssetMapContainerFamilies"
            entry["prefabAssetPathDiagnostics"] = [{
                "status": "conflicting",
                "reason": "prefabAndNonPrefabAssetMapContainerFamilies",
                "containerFamilies": sorted(families),
                "candidates": _bound_rows([
                    row for rows in all_by_path.values() for row in rows
                ]),
            }]
        elif duplicate_count:
            entry["prefabAssetPathStatus"] = "duplicateAssetMapIdentityRows"
            entry["prefabAssetPathDiagnostics"] = _bound_rows(duplicate_diagnostics)
        elif families == {"prefab"} and len(prefab_by_path) == 1:
            candidate = next(iter(prefab_by_path.values()))[0]
            entry["prefabSourceAssetPath"] = candidate["sourceAssetPath"]
            entry["prefabAssetPathStatus"] = "exactUniqueAssetMapContainer"
            entry["prefabAssetPathEvidence"] = {
                "relation": "exactPrefabSourcePathIdToUniqueAssetMapContainer",
                "containmentType": candidate.get("containmentType"),
                "sourceAssetPath": candidate.get("sourceAssetPath"),
            }
        elif families == {"prefab"} and len(prefab_by_path) > 1:
            entry["prefabAssetPathStatus"] = "ambiguousAssetMapContainers"
            entry["prefabAssetPathDiagnostics"] = [{
                "status": "ambiguous",
                "reason": "multipleCompleteAssetMapContainerPaths",
                "candidates": _bound_rows([
                    row for rows in prefab_by_path.values() for row in rows
                ]),
            }]
        elif families:
            entry["prefabAssetPathStatus"] = "nonPrefabAssetMapContainer"
            entry["prefabAssetPathDiagnostics"] = [{
                "status": "unavailable",
                "reason": "noPrefabContainerFamilyForIdentity",
                "containerFamilies": sorted(families),
            }]
        else:
            entry["prefabAssetPathStatus"] = "missingAssetMapContainer"
    catalog["assetMapResolution"]["duplicateIdentityRowCount"] = duplicate_identity_row_count
    if duplicate_diagnostics:
        catalog["assetMapResolution"]["diagnostics"] = _bound_rows([
            *catalog["assetMapResolution"]["diagnostics"],
            *duplicate_diagnostics,
        ])
        catalog["assetMapResolution"]["status"] = "diagnostics"
    return catalog


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("object")
    if not isinstance(value, dict):
        return {}
    return {
        key: value.get(key)
        for key in ("serializedFile", "source", "sourceOffset", "pathId")
        if value.get(key) is not None
    }


def _identity_key(value: Any) -> SceneIdentityKey | None:
    """Return a complete serialized-object identity, without normalizing names."""
    if not isinstance(value, dict):
        return None
    serialized_file = value.get("serializedFile")
    source = value.get("source")
    source_offset = value.get("sourceOffset")
    path_id = value.get("pathId")
    if (
        not isinstance(serialized_file, str) or not serialized_file
        or not isinstance(source, str) or not source
        or isinstance(source_offset, bool) or not isinstance(source_offset, int)
        or isinstance(path_id, bool) or not isinstance(path_id, int)
    ):
        return None
    return serialized_file, source, source_offset, path_id


def _identity_projection(value: Any) -> dict[str, Any]:
    key = _identity_key(value)
    if key is None:
        return {}
    return {
        "serializedFile": key[0],
        "source": key[1],
        "sourceOffset": key[2],
        "pathId": key[3],
    }


def _source_tokens(value: Any) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    normalized = value.replace("\\", "/").lower()
    absolute_markers = ("/streamingassets/vfs/", "/persistent/vfs/")
    suffix = ""
    for marker in absolute_markers:
        if marker in normalized:
            suffix = normalized.split(marker, 1)[1]
            break
    if not suffix:
        if normalized.startswith("vfs/"):
            suffix = normalized[len("vfs/"):]
        else:
            return []
    # Keep the complete VFS-relative identity. In particular, do not add a
    # basename alias: two roots may legitimately contain the same hash name.
    if not suffix or suffix.startswith("/") or "/" not in suffix:
        return []
    return [suffix]


def _asset_map_keys(value: Any) -> list[SceneIdentityKey]:
    """Return explicit AssetMap Source+PathID aliases, never name/path guesses."""
    if not isinstance(value, dict):
        return []
    source = value.get("source")
    path_id = value.get("pathId")
    if not isinstance(source, str) or not source:
        source = value.get("Source")
    if isinstance(path_id, bool) or not isinstance(path_id, int):
        path_id = value.get("PathID")
    if (
        not isinstance(source, str) or not source
        or isinstance(path_id, bool) or not isinstance(path_id, int)
    ):
        return []
    return [("assetMap", token, path_id) for token in _source_tokens(source)]


def _containment_lookup_keys(value: Any) -> list[SceneIdentityKey]:
    keys: list[SceneIdentityKey] = []
    identity_key = _identity_key(value)
    if identity_key is not None:
        keys.append(("object", *identity_key))
    keys.extend(_asset_map_keys(value))
    return keys


def _asset_map_identity_projection(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source = value.get("Source", value.get("source"))
    path_id = value.get("PathID", value.get("pathId"))
    if not isinstance(source, str) or not source:
        return None
    if isinstance(path_id, bool) or not isinstance(path_id, int):
        return None
    return {"source": source, "pathId": path_id}


def _bound_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if isinstance(row, dict)][
        :SCENE_CONTAINMENT_DIAGNOSTIC_LIMIT
    ]


def _normalise_scene_containment_index(
    raw_index: Any,
) -> tuple[dict[SceneIdentityKey, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Normalize an explicit same-pass identity -> SceneAsset/Level catalog.

    The index is intentionally identity-only.  Names, hierarchy paths, prefab
    names, and positions are not accepted as join keys.  The maintained
    exporter may provide a list or ``{"entries": [...]}``; both forms retain
    the exact identity in the published evidence.
    """
    if isinstance(raw_index, dict):
        entries = raw_index.get("entries")
        if entries is None:
            entries = raw_index.get("sceneContainments")
        external_diagnostics = raw_index.get("diagnostics") or []
    else:
        entries = raw_index
        external_diagnostics = []
    if not isinstance(entries, (list, tuple)):
        return {}, _bound_rows([
            {"status": "malformed", "reason": "entriesNotAList"},
            *external_diagnostics,
        ])

    by_identity: dict[SceneIdentityKey, list[dict[str, Any]]] = defaultdict(list)
    diagnostics: list[dict[str, Any]] = []
    for ordinal, entry in enumerate(entries):
        if not isinstance(entry, dict):
            diagnostics.append({
                "status": "malformed",
                "ordinal": ordinal,
                "reason": "entryNotAnObject",
            })
            continue
        identity_value = (
            entry.get("identity")
            or entry.get("objectIdentity")
            or entry.get("object")
            or entry.get("ownerIdentity")
        )
        if identity_value is None and (
            entry.get("Source") is not None or entry.get("source") is not None
        ):
            identity_value = {
                "Source": entry.get("Source", entry.get("source")),
                "PathID": entry.get("PathID", entry.get("pathId")),
            }
        lookup_keys = _containment_lookup_keys(identity_value)
        containment_type = (
            entry.get("containmentType")
            or entry.get("containerType")
            or entry.get("type")
        )
        scene_id = entry.get("sceneId")
        source_name = entry.get("sourceName")
        source_path = entry.get("sourcePath")
        if not lookup_keys:
            diagnostics.append({
                "status": "malformed",
                "ordinal": ordinal,
                "reason": "incompleteIdentity",
            })
            continue
        source_asset_path = entry.get("sourceAssetPath") or entry.get("assetPath")
        if containment_type in PREFAB_CONTAINMENT_TYPES | UNRESOLVED_CONTAINER_TYPES:
            if not isinstance(source_asset_path, str) or not source_asset_path:
                diagnostics.append({
                    "status": "malformed",
                    "ordinal": ordinal,
                    "identity": _identity_projection(identity_value),
                    "reason": "prefabMissingSourceAssetPath",
                })
                continue
            candidate = {
                "identity": _identity_projection(identity_value),
                "containmentType": containment_type,
                "sourceAssetPath": source_asset_path,
            }
            asset_identity = _asset_map_identity_projection(identity_value)
            if asset_identity:
                candidate["assetMapIdentity"] = asset_identity
            for key in lookup_keys:
                if not any(existing == candidate for existing in by_identity[key]):
                    by_identity[key].append(candidate)
            continue
        if (
            not isinstance(scene_id, str) or not scene_id
            or not isinstance(source_name, str) or not source_name
            or not isinstance(source_path, str) or not source_path
            or not isinstance(containment_type, str)
            or containment_type not in SCENE_CONTAINMENT_TYPES
        ):
            diagnostics.append({
                "status": "malformed",
                "ordinal": ordinal,
                "identity": _identity_projection(identity_value),
                "reason": "incompleteSceneAssetLevelFields",
            })
            continue
        candidate = {
            "identity": _identity_projection(identity_value),
            "sceneId": scene_id,
            "sourceName": source_name,
            "sourcePath": source_path,
            "containmentType": containment_type,
        }
        asset_identity = _asset_map_identity_projection(identity_value)
        if asset_identity:
            candidate["assetMapIdentity"] = asset_identity
        for key in lookup_keys:
            if not any(existing == candidate for existing in by_identity[key]):
                by_identity[key].append(candidate)
    return dict(by_identity), _bound_rows([*diagnostics, *external_diagnostics])


def _resolve_scene_emitter_containment(
    owner_identity: dict[str, Any],
    placement: dict[str, Any] | None,
    containment_index: dict[SceneIdentityKey, list[dict[str, Any]]],
    *,
    index_diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve only explicit object identities to a unique SceneAsset/Level."""
    identities: list[dict[str, Any]] = []
    for value in (
        owner_identity,
        placement.get("gameObject") if isinstance(placement, dict) else None,
        placement.get("transform") if isinstance(placement, dict) else None,
    ):
        keys = _containment_lookup_keys(value)
        if not keys or any(set(keys) & set(_containment_lookup_keys(item)) for item in identities):
            continue
        projected = _identity_projection(value)
        identities.append(projected or {
            "source": value.get("Source", value.get("source")),
            "pathId": value.get("PathID", value.get("pathId")),
        })

    matches: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for identity in identities:
        candidates: list[dict[str, Any]] = []
        for key in _containment_lookup_keys(identity):
            for candidate in containment_index.get(key, ()):
                if candidate not in candidates:
                    candidates.append(candidate)
        if len(candidates) > 1:
            conflicts.append({
                "identity": identity,
                "candidates": _bound_rows(candidates),
            })
        matches.extend(candidates)
    if conflicts:
        return {
            "status": "conflictingSceneAssetLevelContainment",
            "diagnostics": _bound_rows(conflicts),
            **({"indexDiagnostics": index_diagnostics} if index_diagnostics else {}),
        }
    prefab_matches = [
        candidate for candidate in matches
        if candidate.get("containmentType") in PREFAB_CONTAINMENT_TYPES
    ]
    scene_matches = [
        candidate for candidate in matches
        if candidate.get("containmentType") in SCENE_CONTAINMENT_TYPES
    ]
    unresolved_matches = [
        candidate for candidate in matches
        if candidate.get("containmentType") in UNRESOLVED_CONTAINER_TYPES
    ]
    if prefab_matches and not scene_matches:
        return {
            "status": "prefabLocalNotSceneContained",
            "diagnostics": _bound_rows([{
                "status": "prefabLocal",
                "reason": "explicitAssetMapPrefabContainer",
                "candidates": prefab_matches,
            }]),
        }
    if prefab_matches and scene_matches:
        return {
            "status": "ambiguousSceneAssetLevelContainment",
            "diagnostics": _bound_rows([{
                "status": "ambiguous",
                "reason": "sceneAndPrefabContainersForSameIdentity",
                "candidates": matches,
            }]),
        }
    if unresolved_matches and (scene_matches or prefab_matches):
        return {
            "status": "ambiguousSceneAssetLevelContainment",
            "diagnostics": _bound_rows([{
                "status": "ambiguous",
                "reason": "mixedContainmentFamiliesForSameIdentity",
                "candidates": matches,
            }]),
        }
    if unresolved_matches and not scene_matches and not prefab_matches:
        status = (
            "sceneAssetContainerWithoutAuthoritativeSceneId"
            if any(
                candidate.get("containmentType") == "SceneAssetContainer"
                for candidate in unresolved_matches
            )
            else "assetContainerNotSceneContained"
        )
        return {
            "status": status,
            "diagnostics": _bound_rows([{
                "status": "unresolvedContainer",
                "reason": "assetMapContainerLacksAuthoritativeSceneId",
                "candidates": unresolved_matches,
            }]),
        }
    # Only the scene/level family may enter the scene candidate tuple below.
    # Other explicit container families have already failed closed above.
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for candidate in scene_matches:
        signature = tuple(
            candidate[field]
            for field in ("sceneId", "sourceName", "sourcePath", "containmentType")
        )
        unique.setdefault(signature, candidate)
    if not unique:
        diagnostics: list[dict[str, Any]] = [{
            "status": "missing",
            "reason": "noExactIdentityJoin",
            "identityCandidates": identities[:SCENE_CONTAINMENT_DIAGNOSTIC_LIMIT],
        }]
        if index_diagnostics:
            diagnostics.extend(index_diagnostics)
        return {
            "status": "missingSceneAssetLevelContainment",
            "diagnostics": _bound_rows(diagnostics),
        }
    if len(unique) > 1:
        return {
            "status": "ambiguousSceneAssetLevelContainment",
            "diagnostics": _bound_rows([{
                "status": "ambiguous",
                "reason": "multipleExactIdentityCandidates",
                "candidates": list(unique.values()),
            }]),
        }
    candidate = next(iter(unique.values()))
    return {
        "status": "exactSceneAssetLevelContainment",
        "sceneId": candidate["sceneId"],
        "sourceName": candidate["sourceName"],
        "sourcePath": candidate["sourcePath"],
        "sceneContainmentEvidence": {
            "kind": "exactSceneAssetLevelContainment",
            "relation": "explicitObjectIdentityToSceneAssetLevel",
            "identity": candidate["identity"],
            "containmentType": candidate["containmentType"],
        },
    }


class _AssetMapJsonStream:
    """Small incremental JSON reader used for the broad AssetMap array."""

    def __init__(self, handle: Any, chunk_size: int = 1024 * 1024) -> None:
        self.handle = handle
        self.chunk_size = chunk_size
        self.buffer = ""
        self.position = 0
        self.eof = False
        self.decoder = json.JSONDecoder()

    def _compact(self) -> None:
        if self.position >= self.chunk_size:
            self.buffer = self.buffer[self.position:]
            self.position = 0

    def _read(self) -> None:
        if self.eof:
            return
        chunk = self.handle.read(self.chunk_size)
        if chunk:
            self.buffer += chunk
        else:
            self.eof = True

    def skip_ws(self) -> None:
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer) or self.eof:
                return
            self._read()

    def peek(self) -> str | None:
        self.skip_ws()
        if self.position >= len(self.buffer):
            return None
        return self.buffer[self.position]

    def consume(self, expected: str) -> bool:
        if self.peek() != expected:
            return False
        self.position += len(expected)
        self._compact()
        return True

    def raw_value(self) -> Any:
        self.skip_ws()
        while True:
            if self.position >= len(self.buffer):
                raise ValueError(f"unexpected end of JSON at {self.position}")
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
            except json.JSONDecodeError as exc:
                if self.eof:
                    raise ValueError(
                        f"invalid JSON value at {self.position}"
                    ) from exc
                if exc.pos < len(self.buffer) - 4096:
                    raise ValueError(
                        f"invalid JSON value at {self.position + exc.pos}"
                    ) from exc
                self._read()
                continue
            self.position = end
            self._compact()
            return value


def _iter_asset_map_array(
    stream: _AssetMapJsonStream,
) -> Iterable[dict[str, Any]]:
    if not stream.consume("["):
        raise ValueError("expected JSON array")
    if stream.peek() == "]":
        stream.consume("]")
        return
    while True:
        value = stream.raw_value()
        if not isinstance(value, dict):
            raise ValueError("array entry is not an object")
        yield value
        if stream.consume(","):
            continue
        if stream.consume("]"):
            return
        raise ValueError("expected comma or array end")


def _iter_asset_map_entries(
    path: Path,
    diagnostics: list[dict[str, Any]] | None = None,
    *,
    allow_bare_array: bool = True,
) -> Iterable[dict[str, Any]]:
    """Stream AssetEntries from the real object root without full loading."""
    diagnostics = diagnostics if diagnostics is not None else []

    def report(status: str, reason: str, **extra: Any) -> None:
        if len(diagnostics) >= SCENE_CONTAINMENT_DIAGNOSTIC_LIMIT:
            return
        diagnostics.append({
            "status": status,
            "path": str(path),
            "reason": reason,
            **extra,
        })

    if not path.is_file():
        report("assetMapUnavailable", "fileMissing")
        return

    try:
        with path.open("r", encoding="utf-8") as handle:
            stream = _AssetMapJsonStream(handle)
            root = stream.peek()
            if root == "[":
                if not allow_bare_array:
                    report("assetMapMalformed", "rootIsNotObject")
                    return
                yield from _iter_asset_map_array(stream)
            elif root == "{":
                stream.consume("{")
                found_entries = False
                if stream.peek() == "}":
                    stream.consume("}")
                else:
                    while True:
                        key = stream.raw_value()
                        if not isinstance(key, str) or not stream.consume(":"):
                            raise ValueError("invalid object member")
                        if key == "AssetEntries":
                            if found_entries:
                                report("assetMapMalformed", "duplicateAssetEntries")
                                return
                            found_entries = True
                            yield from _iter_asset_map_array(stream)
                        else:
                            # GameType and other small metadata fields are
                            # decoded and discarded; AssetEntries is streamed.
                            stream.raw_value()
                        if stream.consume(","):
                            continue
                        if stream.consume("}"):
                            break
                        raise ValueError("expected comma or object end")
                if not found_entries:
                    report("assetMapMalformed", "missingAssetEntries")
                    return
            else:
                report("assetMapMalformed", "rootIsNotObject")
                return
            if stream.peek() is not None:
                report("assetMapMalformed", "trailingDataAfterRoot")
    except UnicodeDecodeError as exc:
        report("assetMapUnreadable", "invalidUtf8", offset=exc.start)
    except OSError as exc:
        report("assetMapUnreadable", "ioError", error=str(exc))
    except ValueError as exc:
        report("assetMapMalformed", str(exc))


def _asset_map_paths(export_root: Path) -> list[Path]:
    root = export_root / "recovered" / "AnimeStudio-cli"
    paths: list[Path] = []
    for source in ("StreamingAssets", "Persistent"):
        maps_root = root / source / "maps"
        if not maps_root.is_dir():
            continue
        paths.extend(sorted(path for path in maps_root.glob("*_assets.json") if path.is_file()))
    return paths


def _collect_asset_map_containment_index(
    export_root: Path,
    wanted: set[SceneIdentityKey] | None = None,
) -> dict[str, Any]:
    """Collect the AssetMap identity/container index once for all consumers.

    AssetMap ``Source`` + ``PathID`` is used only as an explicit identity. A
    prefab container is retained as prefab-local evidence; a ``.unity``
    container is retained as an unresolved SceneAsset candidate until a
    structured authoritative scene id is available.
    """
    entries: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    scan_evidence: list[dict[str, Any]] = []
    paths = _asset_map_paths(export_root)
    if not paths:
        return {
            "entries": [],
            "diagnostics": [{
                "status": "assetMapUnavailable",
                "reason": "noAssetMapFile",
            }],
        }
    failed = False
    for path in paths:
        rows_seen = 0
        local_entries: list[dict[str, Any]] = []
        local_diagnostics: list[dict[str, Any]] = []
        for row in _iter_asset_map_entries(
            path,
            local_diagnostics,
            allow_bare_array=False,
        ):
            rows_seen += 1
            path_id = row.get("PathID")
            source = row.get("Source")
            if isinstance(path_id, bool) or not isinstance(path_id, int):
                continue
            if not isinstance(source, str) or not source:
                continue
            if wanted is not None and not wanted.intersection(
                _asset_map_keys({"Source": source, "PathID": path_id})
            ):
                continue
            container = str(row.get("Container") or "").replace("\\", "/")
            if not container:
                continue
            lower = container.lower()
            if lower.endswith(".prefab"):
                containment_type = "Prefab"
            elif lower.endswith(".unity"):
                containment_type = "SceneAssetContainer"
            else:
                containment_type = "AssetContainer"
            local_entries.append({
                "Source": source,
                "PathID": path_id,
                "containmentType": containment_type,
                "sourceAssetPath": container,
            })
        if local_diagnostics:
            failed = True
            diagnostics.extend(local_diagnostics)
            diagnostics.append({
                "status": "assetMapRejected",
                "path": str(path.relative_to(export_root)).replace("\\", "/"),
                "reason": "malformedOrUnreadableAssetMap",
                "rowsScanned": rows_seen,
            })
        else:
            entries.extend(local_entries)
            scan_evidence.append({
                "status": "assetMapScanned",
                "path": str(path.relative_to(export_root)).replace("\\", "/"),
                "rowsScanned": rows_seen,
            })
    if failed:
        return {
            "entries": [],
            "diagnostics": _bound_rows(diagnostics),
            "scanEvidence": scan_evidence,
        }
    return {
        "entries": entries,
        "diagnostics": diagnostics,
        "scanEvidence": scan_evidence,
    }


def _asset_map_containment_provider(
    export_root: Path,
    emitter_identities: list[dict[str, Any]],
    *,
    collected_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Filter one collected AssetMap index by exact requested identities."""
    wanted: set[SceneIdentityKey] = {
        key
        for identity in emitter_identities
        for key in _containment_lookup_keys(identity)
    }
    if not wanted:
        return {"entries": [], "diagnostics": []}
    collected = collected_index or _collect_asset_map_containment_index(export_root, wanted)
    entries = [
        entry for entry in collected.get("entries") or ()
        if wanted.intersection(_containment_lookup_keys(entry))
    ]
    return {
        "entries": entries,
        "diagnostics": _bound_rows(collected.get("diagnostics") or []),
        "scanEvidence": _bound_rows(collected.get("scanEvidence") or []),
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
                    kind="sceneGlobalAudioEvent",
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
    kind: str | None = None,
    scene_containment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context_kind = kind or (
        "sceneGlobalAudioEvent" if scene_id else "sceneEmitterAudioEvent"
    )
    context: dict[str, Any] = {
        "kind": context_kind,
        "semanticRole": role,
        "source": source,
        "owner": owner,
        "eventHash": event_hash,
        "eventHex": f"0x{event_hash:08x}",
        "confidence": "direct",
        "evidence": (
            "exactAudioMapDataSceneIndex"
            if context_kind == "sceneGlobalAudioEvent"
            else "exactObjectIndexSceneComponentScalar"
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
    if scene_containment:
        status = scene_containment.get("status")
        if status:
            context["sceneContainmentStatus"] = status
        if status == "exactSceneAssetLevelContainment":
            for key in ("sceneId", "sourceName", "sourcePath"):
                if scene_containment.get(key):
                    context[key] = scene_containment[key]
            if scene_containment.get("sceneContainmentEvidence"):
                context["sceneContainmentEvidence"] = scene_containment[
                    "sceneContainmentEvidence"
                ]
        elif scene_containment.get("diagnostics"):
            context["sceneContainmentDiagnostics"] = _bound_rows(
                scene_containment["diagnostics"]
            )
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
                        kind="sceneGlobalAudioEvent",
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
    scene_containment_index: dict[SceneIdentityKey, list[dict[str, Any]]] | None = None,
    scene_containment_index_diagnostics: list[dict[str, Any]] | None = None,
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
    containment = None
    if scene_containment_index is not None:
        containment = _resolve_scene_emitter_containment(
            owner,
            placement,
            scene_containment_index,
            index_diagnostics=scene_containment_index_diagnostics,
        )
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
                kind="sceneEmitterAudioEvent",
                scene_containment=containment,
            ),
        )
    emitter = {
        "source": source,
        "componentType": full_name,
        "name": str(row.get("name") or ""),
        "identity": owner,
        "placement": placement,
        "sceneOwnershipStatus": "objectIndexSceneContextWithoutSceneAssetJoin",
        "eventRequests": requests,
    }
    if containment is not None:
        emitter["sceneOwnershipStatus"] = containment["status"]
        if containment.get("diagnostics"):
            emitter["sceneContainmentDiagnostics"] = _bound_rows(
                containment["diagnostics"]
            )
        if containment.get("sceneContainmentEvidence"):
            emitter["sceneContainmentEvidence"] = containment[
                "sceneContainmentEvidence"
            ]
        if containment.get("status") == "exactSceneAssetLevelContainment":
            for key in ("sceneId", "sourceName", "sourcePath"):
                emitter[key] = containment[key]
    return emitter


def _streaming_instance_emitter_projection(
    owner: dict[str, Any],
    catalog: dict[str, Any],
    emitter_asset_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Join an emitter only through exact, independently proven identity evidence.

    A placed streaming instance normally identifies its prefab asset, while an
    object-index emitter identifies a component object.  Those are different
    identities.  The safe routes are an explicit component identity, or exact
    Source+PathID identities on both sides that resolve to one unique
    normalized complete prefab sourceAssetPath. Names, basenames, meshes, transforms, and
    similarity never qualify.
    """
    status = str(catalog.get("status") or "unavailable")
    diagnostics = _bound_rows(catalog.get("diagnostics") or [])
    entries = [entry for entry in catalog.get("entries") or () if isinstance(entry, dict)]
    owner_keys = set(_containment_lookup_keys(owner))
    matches: list[dict[str, Any]] = []
    for entry in entries:
        component_identity = entry.get("componentIdentity") or entry.get("emitterIdentity")
        if not isinstance(component_identity, dict):
            continue
        if owner_keys.intersection(_containment_lookup_keys(component_identity)):
            matches.append(entry)
    emitter_paths = {
        normalized
        for value in emitter_asset_paths or ()
        for normalized in [_normalise_asset_path(value)]
        if normalized
    }
    path_matches = [
        entry for entry in entries
        if entry.get("prefabAssetPathStatus") == "exactUniqueAssetMapContainer"
        and _normalise_asset_path(entry.get("prefabSourceAssetPath")) in emitter_paths
    ]
    if path_matches:
        matches = path_matches
    if not entries:
        return {
            "status": status,
            "diagnostics": diagnostics,
        }
    if not matches:
        return {
            "status": "unresolvedPrefabEntriesLackEmitterIdentityJoin",
            "diagnostics": _bound_rows([
                *diagnostics,
                {
                    "status": "identityJoinUnavailable",
                    "reason": "prefabAssetIdentityIsNotEmitterComponentIdentity",
                },
            ]),
        }
    levels = sorted({str(entry.get("levelId")) for entry in matches if entry.get("levelId")})
    if len(levels) != 1:
        return {
            "status": "ambiguousPrefabInstanceToLevel",
            "levelIds": levels,
            "diagnostics": _bound_rows([{
                "status": "ambiguous",
                "reason": "multipleExplicitStreamingLevelsForEmitterIdentity",
                "levelIds": levels,
            }]),
        }
    return {
        "status": "exactPrefabInstanceToLevel",
        "levelId": levels[0],
        "entries": matches[:STREAMING_INSTANCE_DIAGNOSTIC_LIMIT],
    }


def build_scene_background_catalog(
    rows_by_source: dict[str, Iterable[dict[str, Any]]],
    audio_index: dict[str, Any],
    *,
    source_evidence: list[dict[str, Any]] | None = None,
    scene_containment_index: Any = None,
    scene_containment_provider: Any = None,
    streaming_instance_catalog: dict[str, Any] | None = None,
    asset_map_export_root: Path | None = None,
) -> dict[str, Any]:
    """Build the catalog from already validated, single-pass object streams."""
    wwise_by_hash = _wwise_lookup(audio_index)
    media_by_id = _media_lookup(audio_index)
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    context_seen: dict[str, set[str]] = defaultdict(set)
    audio_maps: list[dict[str, Any]] = []
    emitters: list[dict[str, Any]] = []
    scanned_counts: Counter[str] = Counter()
    normalized_containment: dict[SceneIdentityKey, list[dict[str, Any]]] | None = None
    containment_index_diagnostics: list[dict[str, Any]] = []
    containment_source_status = "notSupplied"
    containment_scan_evidence: list[dict[str, Any]] = []
    streaming_instance_catalog = streaming_instance_catalog or {
        "schemaVersion": STREAMING_INSTANCE_CONTRACT_VERSION,
        "status": "notSupplied",
        "counts": {},
        "sources": [],
        "entries": [],
        "diagnostics": [],
    }
    if scene_containment_index is not None:
        containment_source_status = "suppliedIdentityCatalog"
        if isinstance(scene_containment_index, dict):
            containment_scan_evidence = _bound_rows(
                scene_containment_index.get("scanEvidence") or []
            )
        normalized_containment, containment_index_diagnostics = (
            _normalise_scene_containment_index(scene_containment_index)
        )

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
                    normalized_containment,
                    containment_index_diagnostics,
                )
                if emitter:
                    emitters.append(emitter)

    if scene_containment_provider is not None and scene_containment_index is None:
        containment_source_status = "assetMapIdentityCatalog"
        prefab_identities = [
            entry.get("prefabIdentity")
            for entry in streaming_instance_catalog.get("entries") or ()
            if isinstance(entry, dict)
            and _prefab_identity_key(entry.get("prefabIdentity")) is not None
        ]
        provided_index = scene_containment_provider([
            *[
                row.get("identity") for row in emitters
                if isinstance(row.get("identity"), dict)
            ],
            *prefab_identities,
        ])
        if isinstance(provided_index, dict):
            containment_scan_evidence = _bound_rows(
                provided_index.get("scanEvidence") or []
            )
        normalized_containment, containment_index_diagnostics = (
            _normalise_scene_containment_index(provided_index)
        )
        for emitter in emitters:
            containment = _resolve_scene_emitter_containment(
                emitter.get("identity") or {},
                emitter.get("placement"),
                normalized_containment,
                index_diagnostics=containment_index_diagnostics,
            )
            emitter["sceneOwnershipStatus"] = containment["status"]
            if containment.get("diagnostics"):
                emitter["sceneContainmentDiagnostics"] = _bound_rows(
                    containment["diagnostics"]
                )
            if containment.get("sceneContainmentEvidence"):
                emitter["sceneContainmentEvidence"] = containment[
                    "sceneContainmentEvidence"
                ]
            if containment.get("status") == "exactSceneAssetLevelContainment":
                for key in ("sceneId", "sourceName", "sourcePath"):
                    emitter[key] = containment[key]
            owner = emitter.get("identity")
            if not isinstance(owner, dict):
                continue
            for request in emitter.get("eventRequests") or ():
                context_key = identifiers.event_hash_context_key(
                    request["eventHash"]
                )
                for context in contexts.get(context_key, ()):
                    if (
                        context.get("kind") == "sceneEmitterAudioEvent"
                        and context.get("owner") == owner
                    ):
                        context["sceneContainmentStatus"] = containment["status"]
                        if containment.get("status") == "exactSceneAssetLevelContainment":
                            for key in ("sceneId", "sourceName", "sourcePath"):
                                context[key] = containment[key]
                            context["sceneContainmentEvidence"] = containment[
                                "sceneContainmentEvidence"
                            ]
                        elif containment.get("diagnostics"):
                            context["sceneContainmentDiagnostics"] = _bound_rows(
                                containment["diagnostics"]
                            )

        if streaming_instance_catalog.get("entries") and isinstance(provided_index, dict):
            streaming_instance_catalog = _enrich_streaming_instance_asset_paths(
                asset_map_export_root or Path(),
                streaming_instance_catalog,
                asset_map_index=provided_index,
            )

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
    for emitter in emitters:
        emitter_asset_paths: list[str] = []
        for value in (
            emitter.get("sourceAssetPath"),
            (emitter.get("sceneContainmentEvidence") or {}).get("sourceAssetPath")
            if isinstance(emitter.get("sceneContainmentEvidence"), dict) else None,
        ):
            if isinstance(value, str):
                emitter_asset_paths.append(value)
        for diagnostic in emitter.get("sceneContainmentDiagnostics") or ():
            if not isinstance(diagnostic, dict):
                continue
            for candidate in diagnostic.get("candidates") or ():
                if isinstance(candidate, dict) and isinstance(candidate.get("sourceAssetPath"), str):
                    emitter_asset_paths.append(candidate["sourceAssetPath"])
        projection = _streaming_instance_emitter_projection(
            emitter.get("identity") or {}, streaming_instance_catalog,
            emitter_asset_paths,
        )
        emitter["streamingPrefabInstanceStatus"] = projection["status"]
        if projection.get("levelId"):
            emitter["streamingPrefabInstanceLevelId"] = projection["levelId"]
        if projection.get("entries"):
            emitter["streamingPrefabInstanceEvidence"] = projection["entries"]
        if projection.get("diagnostics"):
            emitter["streamingPrefabInstanceDiagnostics"] = projection["diagnostics"]
        owner = emitter.get("identity")
        for rows in contexts.values():
            for context in rows:
                if (
                    not isinstance(context, dict)
                    or context.get("kind") != "sceneEmitterAudioEvent"
                    or context.get("owner") != owner
                ):
                    continue
                context["streamingPrefabInstanceStatus"] = projection["status"]
                if projection.get("levelId"):
                    context["streamingPrefabInstanceLevelId"] = projection["levelId"]
                if projection.get("entries"):
                    context["streamingPrefabInstanceEvidence"] = projection["entries"]
                if projection.get("diagnostics"):
                    context["streamingPrefabInstanceDiagnostics"] = projection["diagnostics"]
    boundary = (
        "AudioMapData scene names, state counts, lifecycle Events, room-tone Event, and "
        "aux-bus ids are exact serialized definitions. Scene component requests and exact "
        "transform-hierarchy positions are authored placements; prefab-local ownership is "
        "not promoted to a level join. An explicit unique SceneAsset/Level identity "
        "catalog is required for containment promotion; missing, ambiguous, and "
        "conflicting joins remain unresolved. Streaming InitChunkData prefab-to-level joins "
        "require an explicit numeric prefab Source+PathID identity. An emitter may join via "
        "explicit component identity, or via exact identities on both sides resolving to one "
        "unique normalized complete prefab sourceAssetPath; entity names, Meshes, positions, "
        "and chunk filenames are not accepted as either join key. Wwise leaves are possible media only. Runtime scene "
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
            "sceneEmittersWithExactContainment": sum(
                row.get("sceneOwnershipStatus") == "exactSceneAssetLevelContainment"
                for row in emitters
            ),
            "sceneEmittersWithMissingContainment": sum(
                row.get("sceneOwnershipStatus") == "missingSceneAssetLevelContainment"
                for row in emitters
            ),
            "sceneEmittersWithAmbiguousContainment": sum(
                row.get("sceneOwnershipStatus") == "ambiguousSceneAssetLevelContainment"
                for row in emitters
            ),
            "sceneEmittersWithConflictingContainment": sum(
                row.get("sceneOwnershipStatus") == "conflictingSceneAssetLevelContainment"
                for row in emitters
            ),
            "sceneEmittersPrefabLocal": sum(
                row.get("sceneOwnershipStatus") == "prefabLocalNotSceneContained"
                for row in emitters
            ),
            "sceneEmittersWithExactStreamingPrefabInstance": sum(
                row.get("streamingPrefabInstanceStatus") == "exactPrefabInstanceToLevel"
                for row in emitters
            ),
            "uniquePossibleMedia": len(possible_media_ids),
            "streamingInstanceSidecars": int(
                (streaming_instance_catalog.get("counts") or {}).get("sidecars", 0)
            ),
            "streamingInstanceRows": int(
                (streaming_instance_catalog.get("counts") or {}).get("instances", 0)
            ),
            "streamingPrefabIdentityRows": int(
                (streaming_instance_catalog.get("counts") or {}).get(
                    "exactPrefabIdentityInstances", 0
                )
            ),
        },
        "scenes": scenes,
        "unresolvedSceneDefinitions": unresolved_scene_rows,
        "audioMaps": audio_maps,
        "sceneEmitters": emitters,
        "eventContexts": dict(contexts),
        "sceneContainmentIndex": {
            "status": containment_source_status,
            "diagnostics": containment_index_diagnostics,
            "scanEvidence": containment_scan_evidence,
        },
        "streamingInstanceCatalog": streaming_instance_catalog,
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
    scene_containment_index: Any = None,
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

    streaming_instance_catalog = _load_streaming_instance_identity_catalog(export_root)
    result = build_scene_background_catalog(
        rows_by_source,
        audio_index,
        source_evidence=evidence,
        scene_containment_index=scene_containment_index,
        scene_containment_provider=(
            lambda identities: _asset_map_containment_provider(export_root, identities)
            if scene_containment_index is None else None
        ),
        streaming_instance_catalog=streaming_instance_catalog,
        asset_map_export_root=export_root,
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
        "is not promoted to a level join. Streaming InitChunkData entries are published "
        "only when they carry explicit numeric prefab Source+PathID identity. An emitter "
        "can attach through explicit component identity, or when both exact identities "
        "resolve to one unique normalized complete prefab sourceAssetPath; otherwise it remains "
        "unresolved. "
        "Only an explicit unique SceneAsset/Level identity "
        "catalog can promote containment; missing, ambiguous, and conflicting joins remain "
        "unresolved. Wwise leaves are possible media only. Runtime "
        "scene activation, live State/RTPC values, listener position, branch selection, "
        "playback, and audibility remain unobserved."
    )
    return result
