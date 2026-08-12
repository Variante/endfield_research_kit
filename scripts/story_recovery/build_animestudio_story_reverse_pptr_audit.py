#!/usr/bin/env python3
"""Audit exact reverse PPtrs into actionable Story carrier objects.

The audit scans the current provenance-valid AnimeStudio object indexes twice:
first to identify exact actionable Story-value objects, then to find resolved
PPtrs into those objects. Cross-serialized-file PlayableDirector bindings are
followed through their exact GameObject ancestry and complete Transform
hierarchy. Results are containment/playback-composition evidence only; they do
not create mission ownership or chronology.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file as shared_sha256_file,
)

import build_animestudio_story_carrier_audit as carrier  # noqa: E402
import build_animestudio_story_gameobject_audit as gameobjects  # noqa: E402

SCHEMA = "animestudioStoryReversePPtrAudit.v4"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full"
DEFAULT_GAP_QUEUE = (
    ROOT / "reports" / "mission_order" / "source_story_gap_queue_CN.json"
)
DEFAULT_STORY_INDEX = ROOT / "webui" / "data" / "lang" / "CN" / "index.json"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
DEFAULT_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
EXPECTED_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-28-cutscene-root-director-playback-v1"
)
SOURCES = ("StreamingAssets", "Persistent")


class AuditError(RuntimeError):
    """Raised when exact provenance or relation identity cannot be trusted."""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return shared_sha256_file(path).upper()


def object_key(source: str, row: dict[str, Any]) -> tuple[str, str, int]:
    identity = row.get("object") or {}
    return (
        source,
        str(identity.get("serializedFile") or ""),
        int(identity.get("pathId") or 0),
    )


def pointer_target_key(
    source: str,
    pointer: dict[str, Any],
) -> tuple[str, str, int]:
    target = pointer.get("target") or {}
    return (
        source,
        str(target.get("serializedFile") or ""),
        int(target.get("pathId") or 0),
    )


def pointer_resolves_to_object(
    pointer: dict[str, Any],
    identity: dict[str, Any],
) -> bool:
    target = pointer.get("target") or {}
    return (
        str(pointer.get("status") or "").startswith("resolved")
        and str(target.get("serializedFile") or "")
        == str(identity.get("serializedFile") or "")
        and int(target.get("pathId") or 0)
        == int(identity.get("pathId") or 0)
    )


def resolved_game_object_ids(row: dict[str, Any]) -> list[int]:
    return sorted({
        int(pointer["pathId"])
        for pointer in row.get("pptrs") or []
        if isinstance(pointer, dict)
        and pointer.get("path") == "$.m_GameObject"
        and isinstance(pointer.get("pathId"), int)
        and pointer["pathId"]
        and str(pointer.get("status") or "").startswith("resolved")
    })


def cutscene_root_story_identity(
    component_story_keys: set[str],
    *,
    root_game_object_name: str,
    component_game_object_path_id: int,
    root_game_object_path_id: int,
    all_story_keys: set[str],
) -> tuple[set[str], str]:
    """Resolve a cutscene root's authored Story identity without guessing.

    ``_timelineName`` is normally the Story key.  Some original prefabs use a
    runtime ``levelseq_*`` name there, while the root GameObject retains the
    exact registered Story key.  The GameObject fallback is accepted only for
    the component on the hierarchy root and only when no scalar Story key was
    recovered, so it cannot overwrite a real cross-key playback alias.
    """
    if component_story_keys:
        return component_story_keys, "cutscene_root_timeline_name"
    if (
        component_game_object_path_id == root_game_object_path_id
        and root_game_object_name in all_story_keys
    ):
        return {root_game_object_name}, "root_game_object_name_fallback"
    return set(), "unresolved"


def story_index_keys(path: Path) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read Story index {path}: {exc}") from exc
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise AuditError(f"{path}: entries is not a list")
    return {
        str(row.get("k"))
        for row in entries
        if isinstance(row, dict) and row.get("k")
    }


def collect_targets(
    rows: Iterable[dict[str, Any]],
    target_missions: dict[str, set[str]],
    source: str,
) -> tuple[dict[tuple[str, str, int], dict[str, Any]], int]:
    targets: dict[tuple[str, str, int], dict[str, Any]] = {}
    parsed = 0
    for row in rows:
        if row.get("recordType") != "object":
            continue
        parsed += 1
        matches = sorted({
            story_key
            for field in carrier.scalar_rows(row)
            if (
                story_key := carrier.canonical_target_story_key(
                    field["value"],
                    target_missions,
                )
            )
        })
        if not matches:
            continue
        key = object_key(source, row)
        if not key[1] or not key[2]:
            raise AuditError(f"{source}: exact target has invalid identity")
        previous = targets.get(key)
        current = {
            "source": source,
            "storyKeys": matches,
            "expectedGapMissions": sorted({
                mission
                for story_key in matches
                for mission in target_missions[story_key]
            }),
            "type": carrier.object_type_identity(row),
            "object": row.get("object") or {},
        }
        if previous is not None and previous != current:
            raise AuditError(f"ambiguous exact target identity {key}")
        targets[key] = current
    return targets, parsed


def collect_reverse_relations(
    rows: Iterable[dict[str, Any]],
    targets: dict[tuple[str, str, int], dict[str, Any]],
    source: str,
) -> tuple[list[dict[str, Any]], int]:
    relations = []
    parsed = 0
    for row in rows:
        if row.get("recordType") != "object":
            continue
        parsed += 1
        referrer_key = object_key(source, row)
        for pointer in row.get("pptrs") or []:
            if (
                not isinstance(pointer, dict)
                or not str(pointer.get("status") or "").startswith("resolved")
            ):
                continue
            target_key = pointer_target_key(source, pointer)
            target = targets.get(target_key)
            if target is None or target_key == referrer_key:
                continue
            scalars = carrier.scalar_rows(row)
            relations.append({
                "targetStoryKeys": target["storyKeys"],
                "targetExpectedGapMissions":
                    target["expectedGapMissions"],
                "targetSource": target["source"],
                "targetType": target["type"],
                "targetObject": target["object"],
                "pointerPath": pointer.get("path"),
                "pointerStatus": pointer.get("status"),
                "scope": (
                    "same_serialized_file_composition"
                    if referrer_key[1] == target_key[1]
                    else "cross_serialized_file_reference"
                ),
                "referrerSource": source,
                "referrerType": carrier.object_type_identity(row),
                "referrerObject": row.get("object") or {},
                "referrerGameObjectPathIds":
                    resolved_game_object_ids(row),
                "ownerFields": [
                    field for field in scalars
                    if field["fieldClass"] == "owner_identifier"
                    and carrier.meaningful_identifier_value(field["value"])
                ],
                "runtimeFields": [
                    field for field in scalars
                    if field["fieldClass"] == "runtime_identifier"
                    and carrier.meaningful_identifier_value(field["value"])
                ],
            })
    return relations, parsed


def ancestor_chain(
    objects: dict[int, dict[str, Any]],
    start_path_id: int,
) -> list[int]:
    transform_to_game_object = {
        int(row["transformComponentPathId"]): path_id
        for path_id, row in objects.items()
        if int(row.get("transformComponentPathId") or 0)
    }
    chain = [start_path_id]
    seen = {start_path_id}
    current = start_path_id
    while True:
        parent_transform = int(
            objects[current].get("parentTransformPathId") or 0
        )
        if not parent_transform:
            return chain
        parent = transform_to_game_object.get(parent_transform)
        if parent is None:
            raise AuditError(
                f"GameObject {current}: unresolved parent Transform "
                f"{parent_transform}"
            )
        if parent in seen:
            raise AuditError(f"GameObject hierarchy cycle at {parent}")
        seen.add(parent)
        chain.append(parent)
        current = parent


def cross_file_director_roots(
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    roots = []
    for relation in relations:
        if relation["scope"] != "cross_serialized_file_reference":
            continue
        type_row = relation["referrerType"]
        if (
            relation["pointerPath"] != "$.m_PlayableAsset"
            or type_row.get("objectType") != "PlayableDirector"
            or len(relation["referrerGameObjectPathIds"]) != 1
        ):
            continue
        roots.append({
            "storyKeys": relation["targetStoryKeys"],
            "expectedGapMissions":
                relation["targetExpectedGapMissions"],
            "source": relation["referrerSource"],
            "object": relation["referrerObject"],
            "type": relation["referrerType"],
            "gameObjectPathIds":
                relation["referrerGameObjectPathIds"],
            "targetObject": relation["targetObject"],
            "pointerPath": relation["pointerPath"],
        })
    roots.sort(key=lambda row: (
        row["storyKeys"],
        row["source"],
        row["object"]["serializedFile"],
        row["object"]["pathId"],
    ))
    return roots


def analyze_director_hosts(
    roots: list[dict[str, Any]],
    *,
    output_root: Path,
    game_root: Path,
    cli: Path,
    work_parent: Path,
    all_story_keys: set[str],
) -> list[dict[str, Any]]:
    if not roots:
        return []
    logical = gameobjects.map_logical_bundles(output_root, roots)
    work_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="animestudio_story_reverse_pptr_",
        dir=work_parent,
    ) as temp_name:
        exported = gameobjects.extract_game_objects(
            cli, game_root, logical, Path(temp_name)
        )
        objects_by_source = {
            source: gameobjects.game_object_components(path)
            for source, path in exported.items()
        }
        wanted: dict[str, set[tuple[str, int]]] = defaultdict(set)
        analyzed = []
        for root in roots:
            source = root["source"]
            serialized_file = root["object"]["serializedFile"]
            start = int(root["gameObjectPathIds"][0])
            objects = objects_by_source[source]
            ancestors = ancestor_chain(objects, start)
            top = ancestors[-1]
            descendants, unresolved = gameobjects.descendant_game_objects(
                objects, top
            )
            hierarchy_ids = [top] + [
                int(row["pathId"]) for row in descendants
            ]
            for game_object_path_id in hierarchy_ids:
                for component_path_id in (
                    objects[game_object_path_id]["componentPathIds"]
                ):
                    wanted[source].add(
                        (serialized_file, component_path_id)
                    )
            analyzed.append({
                **root,
                "directorGameObjectPathId": start,
                "ancestorChain": ancestors,
                "rootGameObjectPathId": top,
                "rootGameObjectName": objects[top]["name"],
                "hierarchyGameObjectPathIds": hierarchy_ids,
                "unresolvedChildTransformPathIds": unresolved,
            })
        component_rows = gameobjects.collect_component_rows(
            output_root, wanted
        )
        for row in analyzed:
            source = row["source"]
            serialized_file = row["object"]["serializedFile"]
            objects = objects_by_source[source]
            typed_components = []
            host_story_keys = set()
            root_director_bindings = []
            for game_object_path_id in row["hierarchyGameObjectPathIds"]:
                game_object = objects[game_object_path_id]
                for component_path_id in game_object["componentPathIds"]:
                    if component_path_id == (
                        game_object["transformComponentPathId"]
                    ):
                        continue
                    component = component_rows.get((
                        source, serialized_file, component_path_id
                    ))
                    if component is None:
                        continue
                    compact = gameobjects.compact_component(component)
                    type_name = str(
                        compact["type"].get("scriptFullName") or ""
                    )
                    if type_name == (
                        "Beyond.Gameplay.View.CutsceneRootComponent"
                    ):
                        component_story_keys = set()
                        for field in carrier.scalar_rows(component):
                            if (
                                field["path"] == "$._timelineName"
                                and isinstance(field["value"], str)
                                and field["value"] in all_story_keys
                            ):
                                host_story_keys.add(field["value"])
                                component_story_keys.add(field["value"])
                        component_story_keys, identity_source = (
                            cutscene_root_story_identity(
                                component_story_keys,
                                root_game_object_name=row[
                                    "rootGameObjectName"
                                ],
                                component_game_object_path_id=
                                    game_object_path_id,
                                root_game_object_path_id=row[
                                    "rootGameObjectPathId"
                                ],
                                all_story_keys=all_story_keys,
                            )
                        )
                        host_story_keys.update(component_story_keys)
                        director_pointers = [
                            pointer
                            for pointer in component.get("pptrs") or []
                            if (
                                isinstance(pointer, dict)
                                and pointer.get("path") == "$._director"
                                and pointer_resolves_to_object(
                                    pointer,
                                    row["object"],
                                )
                            )
                        ]
                        for host_story_key in sorted(component_story_keys):
                            for pointer in director_pointers:
                                root_director_bindings.append({
                                    "hostStoryKey": host_story_key,
                                    "cutsceneRootGameObjectPathId":
                                        game_object_path_id,
                                    "cutsceneRootComponentPathId":
                                        int(
                                            (
                                                component.get("object")
                                                or {}
                                            ).get("pathId")
                                            or 0
                                        ),
                                    "pointerPath": pointer["path"],
                                    "pointerStatus":
                                        pointer.get("status"),
                                    "storyIdentitySource": identity_source,
                                    "directorObject": row["object"],
                                })
                    typed_components.append({
                        "gameObjectPathId": game_object_path_id,
                        "gameObjectName": game_object["name"],
                        **compact,
                    })
            row["typedComponents"] = typed_components
            row["candidateComponents"] = [
                component for component in typed_components
                if component["ownerFields"] or component["runtimeFields"]
            ]
            row["hostStoryKeys"] = sorted(host_story_keys)
            row["rootDirectorBindings"] = root_director_bindings
            row["crossStoryContainments"] = [
                {
                    "hostStoryKey": host,
                    "embeddedStoryKey": target,
                    "relation": "cutscene_root_embedded_timeline_asset",
                    "edgeStatus":
                        "exact_containment_no_chronology_or_mission_owner",
                }
                for host in sorted(host_story_keys)
                for target in row["storyKeys"]
                if host != target
            ]
            row["crossStoryPlaybackAliases"] = [
                {
                    "rootStoryKey": binding["hostStoryKey"],
                    "playableAssetStoryKey": target,
                    "relation":
                        "cutscene_root_director_playable_asset",
                    "edgeStatus":
                        "exact_root_playback_alias_no_chronology_or_"
                        "mission_owner",
                    "cutsceneRootGameObjectPathId":
                        binding["cutsceneRootGameObjectPathId"],
                    "cutsceneRootComponentPathId":
                        binding["cutsceneRootComponentPathId"],
                    "directorObject": binding["directorObject"],
                }
                for binding in root_director_bindings
                for target in row["storyKeys"]
                if binding["hostStoryKey"] != target
            ]
    return analyzed


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# AnimeStudio Story Reverse-PPtr Audit",
        "",
        f"- Core-isolated Story keys: `{report['targetStoryKeys']}`",
        f"- Exact target objects: `{summary['targetObjects']}`",
        f"- Object rows scanned per pass: `{summary['objectsPerPass']}`",
        f"- Exact reverse PPtr relations: `{summary['relations']}`",
        "- Same-serialized-file composition relations: "
        f"`{summary['sameFileRelations']}`",
        "- Cross-serialized-file relations: "
        f"`{summary['crossFileRelations']}`",
        "- Cross-file PlayableDirector hosts: "
        f"`{summary['crossFileDirectorHosts']}`",
        f"- Host hierarchy GameObjects: `{summary['hostGameObjects']}`",
        f"- Host typed components: `{summary['hostTypedComponents']}`",
        "- Typed owner/runtime candidates: "
        f"`{summary['candidateRelations'] + summary['hostCandidateComponents']}`",
        "- Cross-Story containment relations: "
        f"`{summary['crossStoryContainments']}`",
        "- Exact root-director playback aliases: "
        f"`{summary['crossStoryPlaybackAliases']}`",
        "",
        "Reverse PPtrs establish serialized composition, not mission ownership "
        "or chronology.",
        "",
        "## Exact root-director playback aliases",
        "",
    ]
    aliases = [
        relation
        for row in report["directorHosts"]
        for relation in row["crossStoryPlaybackAliases"]
    ]
    if not aliases:
        lines.append("_No exact cross-Story root-director alias._")
    else:
        lines.extend([
            "| root Story key | director TimelineAsset | status |",
            "| --- | --- | --- |",
        ])
        for row in aliases:
            lines.append(
                f"| `{row['rootStoryKey']}` | "
                f"`{row['playableAssetStoryKey']}` | "
                f"`{row['edgeStatus']}` |"
            )
    lines.extend([
        "",
        "## Cross-Story containment",
        "",
    ])
    containments = [
        relation
        for row in report["directorHosts"]
        for relation in row["crossStoryContainments"]
    ]
    if not containments:
        lines.append("_No cross-Story containment._")
    else:
        lines.extend([
            "| host cutscene | embedded TimelineAsset | status |",
            "| --- | --- | --- |",
        ])
        for row in containments:
            lines.append(
                f"| `{row['hostStoryKey']}` | "
                f"`{row['embeddedStoryKey']}` | "
                f"`{row['edgeStatus']}` |"
            )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "- Accepted: current complete object-index provenance, exact target "
        "identity, resolved PPtr target, exact PlayableDirector GameObject, "
        "mutually consistent Transform ancestry/descendants, and exact "
        "CutsceneRoot `_timelineName`. Playback aliases additionally require "
        "that exact CutsceneRoot's resolved `_director` PPtr to land on the "
        "same PlayableDirector.",
        "- Rejected: names without object identity, unresolved PPtrs, "
        "neighboring objects, bundle order/proximity, and filename order.",
        "- No relation here creates mission/quest ownership or relative Story "
        "order. Cross-Story rows are containment/playback composition only.",
        f"- Native mapping: `{report['nativeEvidence']['mappingId']}`; "
        "the current root/handle path resolves the root's `_director`, then "
        "`TimelineHandle.Play` calls `PlayableDirector.Play`, `Resume`, or "
        "`Evaluate` as appropriate.",
        "",
    ])
    return "\n".join(lines)


def build_report(
    *,
    output_root: Path,
    gap_queue: Path,
    story_index: Path,
    game_root: Path,
    cli: Path,
    work_parent: Path,
    gameassembly: Path,
    metadata: Path,
) -> dict[str, Any]:
    if not gameassembly.is_file():
        raise AuditError(f"GameAssembly not found: {gameassembly}")
    if not metadata.is_file():
        raise AuditError(f"IL2CPP metadata not found: {metadata}")
    gameassembly_sha256 = sha256(gameassembly)
    metadata_sha256 = sha256(metadata)
    if gameassembly_sha256 != EXPECTED_GAMEASSEMBLY_SHA256:
        raise AuditError(
            "GameAssembly hash changed; revalidate the CutsceneRoot/"
            "TimelineHandle playback mapping before publishing aliases"
        )
    if metadata_sha256 != EXPECTED_METADATA_SHA256:
        raise AuditError(
            "global-metadata.dat hash changed; revalidate the CutsceneRoot/"
            "TimelineHandle playback mapping before publishing aliases"
        )
    target_missions = carrier.load_gap_targets(gap_queue)
    all_story_keys = story_index_keys(story_index)
    targets: dict[tuple[str, str, int], dict[str, Any]] = {}
    source_indexes = []
    expected_total = 0
    for source in SOURCES:
        summary = carrier.load_animestudio_object_index_summary(
            output_root, source
        )
        if summary is None or summary.get("complete") is not True:
            raise AuditError(f"{source}: object index is incomplete")
        index_dir = carrier.animestudio_object_index_dir(output_root, source)
        object_path = index_dir / summary["outputs"]["objects"]["path"]
        expected = int((summary.get("counts") or {}).get("objects") or 0)
        found, parsed = collect_targets(
            carrier.iter_gzip_jsonl(object_path),
            target_missions,
            source,
        )
        if parsed != expected:
            raise AuditError(
                f"{source}: parsed {parsed} objects, expected {expected}"
            )
        for key, row in found.items():
            previous = targets.get(key)
            if previous is not None and previous != row:
                raise AuditError(f"cross-source target identity collision {key}")
            targets[key] = row
        expected_total += expected
        source_indexes.append({
            "source": source,
            "summary": str(index_dir / "summary.json"),
            "objects": str(object_path),
            "objectsCount": expected,
            "stageSignatureSha256": (
                (summary.get("stageSignature") or {}).get("sha256")
            ),
            "sourceFingerprint": (
                (
                    (summary.get("stageSignature") or {}).get("payload")
                    or {}
                ).get("source_fingerprint")
            ),
        })

    relations = []
    for source_row in source_indexes:
        source = source_row["source"]
        found, parsed = collect_reverse_relations(
            carrier.iter_gzip_jsonl(Path(source_row["objects"])),
            targets,
            source,
        )
        expected = int(source_row["objectsCount"])
        if parsed != expected:
            raise AuditError(
                f"{source}: reverse pass parsed {parsed}, expected {expected}"
            )
        relations.extend(found)
    relations.sort(key=lambda row: (
        row["targetStoryKeys"],
        row["scope"],
        str(row["referrerType"].get("scriptFullName") or ""),
        str(row["referrerObject"].get("serializedFile") or ""),
        int(row["referrerObject"].get("pathId") or 0),
    ))
    director_roots = cross_file_director_roots(relations)
    director_hosts = analyze_director_hosts(
        director_roots,
        output_root=output_root,
        game_root=game_root,
        cli=cli,
        work_parent=work_parent,
        all_story_keys=all_story_keys,
    )
    scope_counts = Counter(row["scope"] for row in relations)
    return {
        "_schema": SCHEMA,
        "gapQueue": str(gap_queue),
        "storyIndex": str(story_index),
        "targetStoryKeys": len(target_missions),
        "sources": source_indexes,
        "summary": {
            "targetObjects": len(targets),
            "objectsPerPass": expected_total,
            "relations": len(relations),
            "sameFileRelations":
                scope_counts["same_serialized_file_composition"],
            "crossFileRelations":
                scope_counts["cross_serialized_file_reference"],
            "candidateRelations": sum(
                bool(row["ownerFields"] or row["runtimeFields"])
                for row in relations
            ),
            "crossFileDirectorHosts": len(director_hosts),
            "hostGameObjects": sum(
                len(row["hierarchyGameObjectPathIds"])
                for row in director_hosts
            ),
            "hostTypedComponents": sum(
                len(row["typedComponents"]) for row in director_hosts
            ),
            "hostCandidateComponents": sum(
                len(row["candidateComponents"]) for row in director_hosts
            ),
            "crossStoryContainments": sum(
                len(row["crossStoryContainments"])
                for row in director_hosts
            ),
            "crossStoryPlaybackAliases": sum(
                len(row["crossStoryPlaybackAliases"])
                for row in director_hosts
            ),
        },
        "directorHosts": director_hosts,
        "relations": relations,
        "nativeEvidence": {
            "mappingId": NATIVE_MAPPING_ID,
            "gameAssembly": str(gameassembly),
            "gameAssemblySha256": gameassembly_sha256,
            "metadata": str(metadata),
            "metadataSha256": metadata_sha256,
            "methods": [
                {
                    "type":
                        "Beyond.Gameplay.View.CutsceneRootComponent",
                    "method": "get_topDirector",
                    "token": "0x0600cb29",
                    "va": "0x1839efb40",
                    "evidence": "returns _director at this+0x20",
                },
                {
                    "type": (
                        "Beyond.Gameplay.Core."
                        "CinematicTimelineManagerBase+TimelineHandle"
                    ),
                    "method": "get_director",
                    "token": "0x0600edfb",
                    "va": "0x18366d620",
                    "evidence": (
                        "reads root at this+0x10 and tail-jumps to "
                        "CutsceneRootComponent.get_topDirector"
                    ),
                },
                {
                    "type": (
                        "Beyond.Gameplay.Core."
                        "CinematicTimelineManagerBase+TimelineHandle"
                    ),
                    "method": "Play",
                    "token": "0x0600ee15",
                    "va": "0x186db66a8",
                    "evidence": (
                        "gets the root director and calls "
                        "PlayableDirector.Play/Resume/Evaluate"
                    ),
                },
                {
                    "type": (
                        "Beyond.Gameplay.Core."
                        "MainStreamTimelineManagerBase"
                    ),
                    "method": "_PlayMainTimelineStep3",
                    "token": "0x0600ef70",
                    "va": "0x186dc1cdc",
                    "evidence": (
                        "instantiates the Timeline root then calls "
                        "PlayMainTimelineSync"
                    ),
                },
                {
                    "type": (
                        "Beyond.Gameplay.Core."
                        "MainStreamTimelineManagerBase"
                    ),
                    "method": "PlayMainTimelineSync",
                    "token": "0x0600ef75",
                    "va": "0x186dbf934",
                    "evidence": "calls TimelineHandle.Play",
                },
            ],
        },
        "evidencePolicy": {
            "relation": "serialized composition only",
            "ownership": False,
            "chronology": False,
            "rootDirectorPlaybackAlias": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--gap-queue", type=Path, default=DEFAULT_GAP_QUEUE)
    parser.add_argument("--story-index", type=Path, default=DEFAULT_STORY_INDEX)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument(
        "--gameassembly",
        type=Path,
        help=(
            "GameAssembly.dll used to validate native playback semantics; "
            "defaults to the parent of --game-root"
        ),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help=(
            "global-metadata.dat paired with GameAssembly; defaults under "
            "--game-root/il2cpp_data/Metadata"
        ),
    )
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument(
        "--work-parent", type=Path, default=ROOT / "tmp" / "story"
    )
    parser.add_argument(
        "--report-root", type=Path, default=DEFAULT_REPORT_ROOT
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    game_root = args.game_root.resolve()
    gameassembly = (
        args.gameassembly.resolve()
        if args.gameassembly
        else game_root.parent / "GameAssembly.dll"
    )
    metadata = (
        args.metadata.resolve()
        if args.metadata
        else game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    )
    try:
        report = build_report(
            output_root=args.output_root.resolve(),
            gap_queue=args.gap_queue.resolve(),
            story_index=args.story_index.resolve(),
            game_root=game_root,
            cli=args.animestudio_cli.resolve(),
            work_parent=args.work_parent.resolve(),
            gameassembly=gameassembly,
            metadata=metadata,
        )
    except (AuditError, carrier.AuditError, gameobjects.AuditError) as exc:
        raise SystemExit(
            f"AnimeStudio Story reverse-PPtr audit failed: {exc}"
        ) from exc
    json_path = (
        args.report_root / "animestudio_story_reverse_pptr_audit.json"
    )
    markdown_path = (
        args.report_root / "animestudio_story_reverse_pptr_audit.md"
    )
    write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        "AnimeStudio Story reverse-PPtr audit: "
        f"{markdown_path.relative_to(ROOT)}"
    )
    print(
        "AnimeStudio Story reverse-PPtr data: "
        f"{json_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
