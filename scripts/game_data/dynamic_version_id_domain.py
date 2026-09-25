"""Join authenticated fb_version IDs to same-scene indexed IdComp.UniqueId rows."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.game_data.dynamic_data_index_native import _payload_grids as data_index_payload_grids
from scripts.game_data.dynamic_root_comp_native import validate_native_layout as validate_root_layout
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI, DEFAULT_LEDGER, DEFAULT_OUTER, load_current_inputs,
)
from scripts.game_data.dynamic_streaming import (
    _bounded_vector, _field_span, _root_layout, _table_layout, parse_dynamic_file,
)
from scripts.game_data.dynamic_version_native import (
    VERSION_NAME_RE, validate_native_layout as validate_version_layout,
)
from scripts.repo_paths import REPO_ROOT


DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_version_id_domain_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_version_id_domain_latest.md"
VERSION_RE = re.compile(r"^Data/DynamicStreaming/PC/Scene/([^/]+)/fb_version\.bytes$", re.I)


def _stream_selected(rows: list[dict[str, Any]], *, cli: Path, primary: Path,
                     fallback: Path, regex: str) -> dict[str, bytes]:
    command = [str(cli), "stream", "--streaming-assets", str(primary),
               "--fallback-assets", str(fallback), "--block-type", "dynamic-streaming",
               "--file-regex", regex, "--verify-md5"]
    run = subprocess.run(command, capture_output=True, text=True, check=False)
    if run.returncode:
        raise ValueError(f"AnimeStudio stream failed code={run.returncode}: {run.stderr[-500:]}")
    streamed: dict[str, bytes] = {}
    for line in run.stdout.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        path = record["fileName"]
        if path in streamed or record.get("blockType") != "DynamicStreaming":
            raise ValueError(f"AnimeStudio stream duplicate/type mismatch: {path}")
        streamed[path] = base64.b64decode(record["dataBase64"], validate=True)
    expected = {row["path"]: row for row in rows}
    if set(streamed) != set(expected):
        raise ValueError(f"AnimeStudio stream selection differs: expected={len(expected)} actual={len(streamed)}")
    for path, data in streamed.items():
        row = expected[path]
        digest = hashlib.md5(data).hexdigest().upper()
        if len(data) != row["declaredBytes"] or digest != row["fileDataMd5"]:
            raise ValueError(f"{path}: streamed length/MD5 differs from authenticated VFS row")
    return streamed


def _version_ids(data: bytes, layout: dict[str, Any], *, source: str) -> list[int]:
    parsed = parse_dynamic_file("version", data, version_entry_width=int(layout["entryWidth"]))
    root = parsed["root"]
    if (root["fieldCount"] != int(layout["rootFieldCount"])
            or tuple(root["presentFields"]) != (int(layout["entriesFieldIndex"]),
                                                 int(layout["majorFieldIndex"]),
                                                 int(layout["minorFieldIndex"]))):
        raise ValueError(f"{source}: selected version root shape differs")
    vector = parsed["VectorField0"]
    body, count = int(vector["bodyOffset"]), int(vector["count"])
    width, id_offset = int(layout["entryWidth"]), int(layout["entryIdOffset"])
    return [struct.unpack_from("<Q", data, body + index * width + id_offset)[0]
            for index in range(count)]


def _main_identities(data: bytes, *, source: str, root_layout: dict[str, Any],
                     index_layout: dict[str, Any], main_layout: dict[str, Any],
                     enum_by_id: dict[int, str]) -> tuple[list[int], set[int], int]:
    vectors = {row["name"]: row for row in main_layout["vectors"]}
    widths = {int(row["fieldIndex"]): int(row["elementWidth"])
              for row in main_layout["vectors"]}
    names = {name: int(row["fieldIndex"]) for name, row in vectors.items()}
    id_path = root_layout["idCompPath"]
    id_type = int(id_path["dataTypeValue"])
    field = int(id_path["vectorFieldIndex"])
    if (enum_by_id.get(id_type) != "IdComp" or names.get("IdComp") != field
            or widths.get(field) != 8):
        raise ValueError("selected IdComp enum/vector/width disagree")
    indexed, _ = data_index_payload_grids(
        data, widths=widths, layout=index_layout, enum_by_id=enum_by_id,
        name_to_field=names, source=source,
    )
    root = _root_layout(data)
    grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
    if grid_count != len(indexed):
        raise ValueError(f"{source}: indexed grid count differs")
    ids: list[int] = []
    grid_ids: set[int] = set()
    for ordinal, row in enumerate(indexed):
        slot = grid_body + ordinal * 4
        grid = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
        uid_address = _field_span(data, grid, 0, 4)
        if uid_address is None:
            raise ValueError(f"{source}: grid[{ordinal}] lacks UniqueId")
        uid = struct.unpack_from("<I", data, uid_address)[0]
        if uid != row["uniqueId"]:
            raise ValueError(f"{source}: grid[{ordinal}] UniqueId differs within parser")
        grid_ids.add(uid)
        body, count, _ = _bounded_vector(data, grid, field, 8)
        indexes = sorted(row["indexes"].get(id_type, []))
        if indexes != list(range(count)):
            raise ValueError(f"{source}: grid[{ordinal}] IdComp DataIndex partition differs")
        ids.extend(struct.unpack_from("<Q", data, body + index * 8)[0]
                   for index in indexes)
    return ids, grid_ids, grid_count


def compare_scene_ids(version_ids: list[int], id_comp_ids: list[int],
                      grid_ids: set[int], *, scene: str) -> dict[str, Any]:
    """Keep full containment separate from an exhaustive-entity claim."""
    version_set, id_comp_set = set(version_ids), set(id_comp_ids)
    missing = sorted(version_set - id_comp_set)
    extras = sorted(id_comp_set - version_set)
    return {
        "scene": scene,
        "versionEntries": len(version_ids), "distinctVersionIds": len(version_set),
        "idCompRecords": len(id_comp_ids), "distinctIdCompIds": len(id_comp_set),
        "matchingVersionIds": len(version_set & id_comp_set),
        "versionIdsWithoutIdComp": missing,
        "idCompIdsWithoutVersion": len(extras), "idCompOnlySample": extras[:8],
        "gridUniqueIds": len(grid_ids), "versionGridIdOverlap": len(version_set & grid_ids),
    }


def audit_current_domain(*, gameassembly: Path, metadata: Path,
                         expected_input_set_sha256: str, control_scene: str,
                         outer_path: Path = DEFAULT_OUTER,
                         ledger_path: Path = DEFAULT_LEDGER,
                         cli_path: Path = DEFAULT_CLI) -> dict[str, Any]:
    version_layout, version_native = validate_version_layout(gameassembly, metadata)
    root_layout, index_layout, main_layout, enum_by_id, _entity_enum, root_digests, root_native = (
        validate_root_layout(gameassembly, metadata)
    )
    if version_native["nativeInputs"] != root_native:
        raise ValueError("version and RootComp native contracts select different builds")
    version_outer, version_rows, version_provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=VERSION_NAME_RE, selection_label="fb_version.bytes",
    )
    primary = Path(version_outer["primaryAssets"])
    fallback = Path(version_outer["fallbackAssets"])
    version_files = _stream_selected(
        version_rows, cli=cli_path, primary=primary, fallback=fallback,
        regex=r"(?:^|/)fb_version\.bytes$",
    )
    populated: dict[str, list[int]] = {}
    non_scene_version_files = 0
    for row in version_rows:
        ids = _version_ids(version_files[row["path"]], version_layout, source=row["path"])
        match = VERSION_RE.fullmatch(row["path"])
        if match is None:
            non_scene_version_files += 1
            if ids:
                raise ValueError(f"{row['path']}: populated version path has no Scene key")
            continue
        scene = match.group(1)
        if ids:
            if scene in populated:
                raise ValueError(f"duplicate populated version scene: {scene}")
            populated[scene] = ids
    if not populated:
        raise ValueError("no populated version scene in authenticated corpus")
    if not re.fullmatch(r"[A-Za-z0-9_]+", control_scene):
        raise ValueError("control scene must be a simple scene name")
    if control_scene in populated:
        raise ValueError("control scene is also a populated version scene")
    scenes = sorted(set(populated) | {control_scene})
    scene_regex = "|".join(re.escape(scene) for scene in scenes)
    main_pattern = (r"^Data/DynamicStreaming/PC/Scene/(?:" + scene_regex
                    + r")/fb_main_[^/]+\.bytes$")
    main_outer, main_rows, main_provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=re.compile(main_pattern, re.I), selection_label="selected scene fb_main",
    )
    if main_outer["inputSetSha256"] != version_outer["inputSetSha256"]:
        raise ValueError("main/version VFS audit input sets differ")
    main_files = _stream_selected(
        main_rows, cli=cli_path, primary=primary, fallback=fallback,
        regex=main_pattern,
    )
    ids_by_scene: dict[str, list[int]] = defaultdict(list)
    grids_by_scene: dict[str, set[int]] = defaultdict(set)
    counts: Counter[str] = Counter()
    for row in main_rows:
        scene = row["path"].split("/")[-2]
        ids, grids, grid_count = _main_identities(
            main_files[row["path"]], source=row["path"],
            root_layout=root_layout, index_layout=index_layout,
            main_layout=main_layout, enum_by_id=enum_by_id,
        )
        ids_by_scene[scene].extend(ids)
        grids_by_scene[scene].update(grids)
        counts[scene] += 1
        if len(grids) > grid_count:
            raise ValueError(f"{row['path']}: unique grid count exceeds records")
    result = []
    for scene, version_ids in sorted(populated.items()):
        if not counts[scene]:
            raise ValueError(f"{scene}: populated version file has no authenticated main file")
        item = compare_scene_ids(version_ids, ids_by_scene[scene], grids_by_scene[scene], scene=scene)
        item["mainFiles"] = counts[scene]
        result.append(item)
    if not counts[control_scene]:
        raise ValueError(f"{control_scene}: control scene has no authenticated main file")
    control_ids = set(ids_by_scene[control_scene])
    control = {"scene": control_scene, "mainFiles": counts[control_scene],
               "idCompRecords": len(ids_by_scene[control_scene]),
               "distinctIdCompIds": len(control_ids),
               "overlapWithVersionIds": {
                   scene: len(set(ids) & control_ids) for scene, ids in sorted(populated.items())}}
    for item in result:
        if item["versionIdsWithoutIdComp"]:
            raise ValueError(
                f"{item['scene']}: fb_version Entry.Id={item['versionIdsWithoutIdComp'][0]} "
                "lacks same-scene indexed fb_main IdComp.UniqueId"
            )
    return {
        "format": "endfield.dynamic-version-id-domain-audit.v1",
        "status": "validated", "inputSetSha256": version_outer["inputSetSha256"],
        "nativeInputs": root_native,
        "contractSha256": {"version": version_native["contractSha256"], **root_digests},
        "sourceReports": {"versionOuterReportSha256": version_provenance["outerReportSha256"],
                          "versionLedgerSha256": version_provenance["ledgerSha256"],
                          "mainOuterReportSha256": main_provenance["outerReportSha256"],
                          "mainLedgerSha256": main_provenance["ledgerSha256"]},
        "versionFiles": len(version_rows), "nonSceneVersionFiles": non_scene_version_files,
        "populatedScenes": result, "control": control,
        "evidenceBoundary": {
            "exact": "Selected native contracts name the version entry Id and main-grid IdComp.UniqueId fields. Every streamed payload is checked against current VFS path, length and FileDataMd5; DataIndex indexes partition each IdComp vector in the selected scenes.",
            "direct": "Every populated version Id is present as an indexed IdComp.UniqueId in the same scene's authenticated main files. Extra IdComp values show that the version file is a subset, not a complete entity inventory.",
            "unresolved": "The runtime version-ban dictionary decision, live file/grid activation, and whether any stored entry affects play are not established by this stored-data join.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    if report["status"] != "validated":
        return f"# DynamicStreaming version Id domain\n\n- Status: {report['status']}; reason: {report['reason']}.\n"
    lines = ["# DynamicStreaming version Id domain", "",
             f"- Status: validated; authenticated version files: {report['versionFiles']} "
             f"({report['nonSceneVersionFiles']} empty non-scene roots).",
             "- Version IDs are a same-scene subset of indexed IdComp.UniqueId values; no live decision is claimed.",
             "", "| Scene | Version IDs | Matched IdComp IDs | IdComp-only IDs | Grid-ID overlap |",
             "|---|---:|---:|---:|---:|"]
    for row in report["populatedScenes"]:
        lines.append(f"| {row['scene']} | {row['distinctVersionIds']} | {row['matchingVersionIds']} | "
                     f"{row['idCompIdsWithoutVersion']} | {row['versionGridIdOverlap']} |")
    control = report["control"]
    overlaps = ", ".join(f"{scene}={count}" for scene, count in control["overlapWithVersionIds"].items())
    lines += ["", f"- Control scene `{control['scene']}`: {control['distinctIdCompIds']} distinct IdComp IDs; "
              f"version-ID overlap: {overlaps}.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--control-scene", default="map01")
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    for output in (args.output_json, args.output_md):
        if (REPO_ROOT / "reports").resolve() not in output.resolve().parents:
            parser.error("outputs must be under reports/")
    try:
        report = audit_current_domain(
            gameassembly=args.gameassembly, metadata=args.metadata,
            expected_input_set_sha256=args.expected_input_set_sha256,
            control_scene=args.control_scene, outer_path=args.outer_report,
            ledger_path=args.ledger, cli_path=args.cli,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError,
            subprocess.SubprocessError, json.JSONDecodeError) as error:
        report = {"format": "endfield.dynamic-version-id-domain-audit.v1",
                  "status": "validation_failed", "reason": str(error), "populatedScenes": []}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"DynamicStreaming version Id domain: {report['status']}; "
          f"populated scenes={len(report['populatedScenes'])}")
    if report["status"] != "validated":
        print(report["reason"], file=sys.stderr)
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
