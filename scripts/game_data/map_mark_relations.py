"""Audit exact stored joins around GameplayConfig/LevelMapMark.json.

This is a static-data audit. It does not infer runtime marker visibility or
assign a scene from a shared numeric group key or a registry id bucket. JsonData source identities are
checked against the current complete corpus receipt before the named schemas
and joins are read. The Table source has its own digest in the output.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.game_data.schemas.gameplay_config import decode_compact_gameplay_config_json
from scripts.game_data.schemas.gameplay_config_polymorphic import decode_polymorphic_gameplay_config
from scripts.repo_paths import REPO_ROOT


DEFAULT_GAME = REPO_ROOT / "export_full" / "game"
DEFAULT_CORPUS = REPO_ROOT / "reports" / "animestudio" / "jsondata_corpus_current_latest.json"
DEFAULT_FILES = REPO_ROOT / "reports" / "animestudio" / "jsondata_corpus_files_current_latest.jsonl.gz"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "game_data" / "map_mark_relations.json"
JSON_NAMES = (
    "LevelMapMark.json", "MapBriefInfoTable.json", "MapRegionTable.json",
    "LevelShortIdTable.json", "LevelBasicInfoTable.json", "WorldEntityRegistry.json",
)


class MapMarkRelationsError(ValueError):
    pass


def _read_json(path: Path) -> tuple[Any, bytes]:
    data = path.read_bytes()
    try:
        return json.loads(data.decode("utf-8")), data
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MapMarkRelationsError(f"{path}: invalid UTF-8 JSON: {exc}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _verified_json_rows(game: Path, corpus: Path, files: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    report, _ = _read_json(corpus)
    if (
        report.get("format") != "endfield-jsondata-current-corpus-v1"
        or report.get("status") != "complete"
        or Path(report.get("exportRoot", "")).resolve() != (game / "Json").resolve()
        or report.get("summary", {}).get("filesSelected") != report.get("summary", {}).get("filesJoined")
    ):
        raise MapMarkRelationsError("JsonData corpus receipt is incomplete or for another export root")
    wanted = {f"GameplayConfig/{name}" for name in JSON_NAMES}
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(files, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            relative = row.get("exportRelativePath")
            if relative not in wanted:
                continue
            if relative in rows:
                raise MapMarkRelationsError(f"duplicate corpus identity: {relative}")
            rows[relative] = row
    if set(rows) != wanted:
        raise MapMarkRelationsError(f"missing JsonData identities: {sorted(wanted - set(rows))}")
    return report["inputSetSha256"], rows


def audit(game: Path, corpus: Path, files: Path) -> dict[str, Any]:
    input_set, certified = _verified_json_rows(game, corpus, files)
    roots: dict[str, Any] = {}
    source: dict[str, dict[str, Any]] = {}
    for name in JSON_NAMES:
        relative = f"GameplayConfig/{name}"
        path = game / "Json" / "GameplayConfig" / name
        root, data = _read_json(path)
        receipt = certified[relative]
        if (
            receipt.get("status") != "schema_decoded"
            or receipt.get("length") != len(data)
            or receipt.get("logicalSha256") != _sha256(data)
        ):
            raise MapMarkRelationsError(f"{relative}: source differs from named-schema corpus receipt")
        if name == "LevelMapMark.json":
            decode_polymorphic_gameplay_config(data, source=relative)
        else:
            decode_compact_gameplay_config_json(data, source=relative)
        roots[name] = root
        source[name] = {"path": str(path), "length": len(data), "sha256": _sha256(data)}

    table_path = game / "Table" / "MapMarkTempTable.json"
    templates, table_data = _read_json(table_path)
    if not isinstance(templates, dict) or any(
        not isinstance(row, dict) or not isinstance(row.get("markInfoId"), str)
        for row in templates.values()
    ):
        raise MapMarkRelationsError("MapMarkTempTable: missing row/markInfoId structure")
    source["MapMarkTempTable.json"] = {
        "path": str(table_path), "length": len(table_data), "sha256": _sha256(table_data)
    }

    marks = roots["LevelMapMark.json"]
    brief = roots["MapBriefInfoTable.json"]["mapTable"]
    regions = roots["MapRegionTable.json"]
    short_ids = roots["LevelShortIdTable.json"]
    levels = roots["LevelBasicInfoTable.json"]
    world_entities = roots["WorldEntityRegistry.json"]["worldEntityBriefInfos"]
    scenes_by_logic_id: dict[str, set[str]] = defaultdict(set)
    for scene, entry in short_ids.items():
        for logic_id in entry["ids"]:
            scenes_by_logic_id[logic_id].add(scene)
    brief_groups: dict[str, list[str]] = defaultdict(list)
    for map_id, entry in brief.items():
        for group in entry["subLevelTable"]:
            brief_groups[group].append(map_id)

    templates_used: Counter[str] = Counter()
    visibility_types: Counter[str] = Counter()
    detector_count = detector_equal = 0
    marker_ids: set[str] = set()
    unmatched_templates: set[str] = set()
    group_rows: list[dict[str, Any]] = []
    scene_linked_marks: list[dict[str, Any]] = []
    registry_linked_marks: list[dict[str, Any]] = []
    short_id_matches = short_id_ambiguous = short_id_missing_level = 0
    short_id_missing_registry = short_id_position_mismatch = 0
    registry_id_matches = registry_position_matches = 0
    for group, group_marks in marks.items():
        group_scenes: Counter[str] = Counter()
        for row in group_marks:
            basic = row["basicData"]
            template = basic["templateId"]
            mark_id = basic["markInstId"]
            if mark_id in marker_ids:
                raise MapMarkRelationsError(f"duplicate markInstId: {mark_id}")
            marker_ids.add(mark_id)
            templates_used[template] += 1
            if template not in templates:
                unmatched_templates.add(template)
            visibility = row.get("visibilityData") or {}
            tag = visibility.get("$type", "<absent>")
            visibility_types[tag] += 1
            if tag == "Beyond.Gameplay.MapMarkVisibilityDataMapDetectorEntity, Gameplay.Beyond":
                detector_count += 1
                detector_equal += str(visibility["entityId"]) == mark_id
            registry_row = world_entities.get(mark_id)
            if registry_row is not None:
                registry_id_matches += 1
                if registry_row.get("position") == basic["pos"]:
                    registry_position_matches += 1
                    if template in templates and templates[template]["markInfoId"] == template:
                        registry_linked_marks.append({
                            "groupKey": group,
                            "markInstId": mark_id,
                            "templateId": template,
                            "position": basic["pos"],
                            "defaultVisible": basic["defaultVisible"],
                            "visibilityType": tag,
                        })
            scenes = scenes_by_logic_id.get(mark_id, set())
            if scenes:
                short_id_matches += 1
                if len(scenes) != 1:
                    short_id_ambiguous += 1
                else:
                    scene = next(iter(scenes))
                    if scene not in levels:
                        short_id_missing_level += 1
                    elif mark_id not in world_entities:
                        short_id_missing_registry += 1
                    elif world_entities[mark_id].get("position") != basic["pos"]:
                        short_id_position_mismatch += 1
                    elif template in templates and templates[template]["markInfoId"] == template:
                        group_scenes[scene] += 1
                        scene_linked_marks.append({
                            "groupKey": group,
                            "sceneName": scene,
                            "markInstId": mark_id,
                            "templateId": template,
                            "position": basic["pos"],
                            "defaultVisible": basic["defaultVisible"],
                            "visibilityType": tag,
                        })
        region_levels = sorted({row["levelId"] for row in regions.get(group, [])})
        group_rows.append({
            "groupKey": group,
            "markCount": len(group_marks),
            "mapBriefMapIds": sorted(brief_groups.get(group, [])),
            "mapRegionLevelIds": region_levels,
            "directSceneMarkCounts": dict(sorted(group_scenes.items())),
        })

    return {
        "schema": "endfield.map-mark-relations-audit.v3",
        "evidenceBoundary": {
            "exact": "Source bytes match named-schema JsonData corpus rows. An exact marker instance ID plus identical position joins authored map-mark data to an existing WorldEntityRegistry entity. A subset has a unique LevelShortIdTable sceneName for that same ID.",
            "unresolved": "Registry identity does not assign an authored scene: only the unique LevelShortIdTable subset does. Numeric group keys and registry id buckets cannot promote other marks to scenes; runtime visibility, discovery and server state are unobserved.",
        },
        "jsonDataInputSetSha256": input_set,
        "sources": source,
        "counts": {
            "groups": len(marks),
            "marks": len(marker_ids),
            "usedTemplates": len(templates_used),
            "templateTableRows": len(templates),
            "templateAliasRows": sum(key != row["markInfoId"] for key, row in templates.items()),
            "resolvedTemplateMarks": sum(count for key, count in templates_used.items() if key in templates),
            "usedTemplatesWithMatchingMarkInfoId": sum(
                key in templates and templates[key]["markInfoId"] == key for key in templates_used
            ),
            "unresolvedTemplates": sorted(unmatched_templates),
            "groupsInMapBrief": sum(bool(brief_groups.get(group)) for group in marks),
            "groupsInMapRegion": sum(bool(regions.get(group)) for group in marks),
            "groupsWithoutExternalKey": sum(
                not row["mapBriefMapIds"] and not row["mapRegionLevelIds"] for row in group_rows
            ),
            "marksWithoutExternalKey": sum(
                row["markCount"] for row in group_rows
                if not row["mapBriefMapIds"] and not row["mapRegionLevelIds"]
            ),
            "groupsWithMultipleMapBriefIds": sum(len(row["mapBriefMapIds"]) > 1 for row in group_rows),
            "groupsWithMultipleRegionLevels": sum(len(row["mapRegionLevelIds"]) > 1 for row in group_rows),
            "detectorEntityMarks": detector_count,
            "detectorEntityIdEqualsMarkInstId": detector_equal,
            "registryIdMatchedMarks": registry_id_matches,
            "registryPositionMatchedMarks": registry_position_matches,
            "registryPositionMismatchMarks": registry_id_matches - registry_position_matches,
            "registryLinkedMarks": len(registry_linked_marks),
            "withoutRegistryLinkMarks": len(marker_ids) - len(registry_linked_marks),
            "shortIdMatchedMarks": short_id_matches,
            "shortIdAmbiguousMarks": short_id_ambiguous,
            "shortIdMissingLevelMarks": short_id_missing_level,
            "shortIdMissingRegistryMarks": short_id_missing_registry,
            "shortIdPositionMismatchMarks": short_id_position_mismatch,
            "sceneLinkedMarks": len(scene_linked_marks),
            "sceneLinkedGroups": sum(bool(row["directSceneMarkCounts"]) for row in group_rows),
            "withoutDirectSceneMarks": len(marker_ids) - len(scene_linked_marks),
        },
        "visibilityTypes": dict(sorted(visibility_types.items())),
        "groups": group_rows,
        "registryLinkedMarks": sorted(registry_linked_marks, key=lambda row: row["markInstId"]),
        "sceneLinkedMarks": sorted(scene_linked_marks, key=lambda row: (row["sceneName"], row["markInstId"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--corpus-files", type=Path, default=DEFAULT_FILES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.game_root, args.corpus_report, args.corpus_files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
