"""Join authenticated RootComp area values to the same scene's FBStreamArea IDs.

The two source audits establish their selected native layouts independently.
This audit rechecks their contracts, installed native inputs, input-set identity,
report rows, and dumped payload hashes before comparing stored IDs. It does not
observe live area selection or controller execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_stream_area_native import audit_payload
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout, parse_dynamic_file
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


ROOT_CONTRACT = CONTRACTS_DIR / "dynamic_root_comp_native.json"
AREA_CONTRACT = CONTRACTS_DIR / "dynamic_stream_area_native.json"
DEFAULT_MAIN_REPORT = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.json"
DEFAULT_AREA_NATIVE_REPORT = REPO_ROOT / "reports/animestudio/dynamic_stream_area_native_latest.json"
DEFAULT_AREA_CORPUS_REPORT = REPO_ROOT / "reports/animestudio/dynamic_stream_area_current_latest.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_area_join_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_visibility_area_join_latest.md"
FORMAT = "endfield.dynamic-visibility-area-join.v1"


class DynamicVisibilityAreaJoinError(ValueError):
    """An input gate or current scene-local area ID relation differs."""


def _read_report(path: Path, expected_format: str, expected_status: str) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get("format") != expected_format or report.get("status") != expected_status:
        raise DynamicVisibilityAreaJoinError(f"{path}: format/status differs from {expected_format}/{expected_status}")
    return report, hashlib.sha256(raw).hexdigest().upper()


def _scene_key(path: str, *, area: bool) -> str | None:
    parts = path.replace("\\", "/").split("/")
    if len(parts) < 6 or parts[:4] != ["Data", "DynamicStreaming", "PC", "Scene"]:
        if not area and parts[:4] == ["Data", "DynamicStreaming", "PC", "Extra"] and parts[-1].startswith("fb_main_"):
            return None
        raise DynamicVisibilityAreaJoinError(f"unexpected DynamicStreaming source path: {path}")
    if any(part in ("", ".", "..") for part in parts):
        raise DynamicVisibilityAreaJoinError(f"invalid DynamicStreaming source path: {path}")
    if area and (len(parts) != 6 or parts[-1] != "FBStreamArea.bytes"):
        raise DynamicVisibilityAreaJoinError(f"unexpected FBStreamArea source path: {path}")
    if not area and (len(parts) != 6 or not parts[-1].startswith("fb_main_") or not parts[-1].endswith(".bytes")):
        raise DynamicVisibilityAreaJoinError(f"unexpected main source path: {path}")
    return parts[4].casefold()


def _check_shared_evidence(
    main: dict[str, Any], area_native: dict[str, Any], area_corpus: dict[str, Any],
    *, gameassembly: Path, metadata: Path, expected_input_set_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    root_contract, root_digest = read_reviewed_contract(
        ROOT_CONTRACT, schema="endfield.dynamic-root-comp-native-contract.v7",
        label="dynamic_root_comp", status="validated",
    )
    area_contract, area_digest = read_reviewed_contract(
        AREA_CONTRACT, schema="endfield.dynamic-stream-area-native-contract.v2",
        label="dynamic_stream_area", status="validated",
    )
    inputs = root_contract["nativeInputs"]
    if area_contract["nativeInputs"] != inputs:
        raise DynamicVisibilityAreaJoinError("root and area contracts select different native inputs")
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVisibilityAreaJoinError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"].upper():
        raise DynamicVisibilityAreaJoinError("installed_native_inputs:missing-or-mismatched:UnityPlayer.dll")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": inputs["unityPlayerSha256"].upper(),
    }
    if (main.get("nativeInputs") != receipt or area_native.get("nativeInputs") != receipt
            or main.get("rootCompContractSha256") != root_digest
            or area_native.get("contractSha256") != area_digest):
        raise DynamicVisibilityAreaJoinError("source native report input/contract provenance differs")
    predicate = area_contract["runtimePredicate"]
    predicate_method = predicate["method"]
    predicate_receipt = area_native.get("runtimePredicate")
    if predicate_receipt != {
        "status": "validated",
        "method": f"{predicate_method['type']}.{predicate_method['method']}",
        "bodySha256": predicate_method["bodySha256"].upper(),
        "toggleOffSha256": predicate["toggleOffWindow"]["sha256"].upper(),
        "reviewedMeaning": predicate["reviewedMeaning"],
    }:
        raise DynamicVisibilityAreaJoinError("source area predicate receipt differs")
    selected = expected_input_set_sha256.upper()
    if any(report.get("inputSetSha256", "").upper() != selected
           for report in (main, area_native, area_corpus)):
        raise DynamicVisibilityAreaJoinError("source reports select different VFS input sets")
    if (len(main["files"]) != main["corpus"]["files"]
            or len(area_native["files"]) != area_native["fileCount"]
            or len(area_corpus["corpus"]["files"]) != area_corpus["corpus"]["fileCount"]):
        raise DynamicVisibilityAreaJoinError("source report file cardinality differs")
    return root_contract["layout"], area_contract["layout"], receipt


def _area_ids(
    corpus_rows: list[dict[str, Any]], native_rows: list[dict[str, Any]],
    *, input_root: Path, layout: dict[str, Any],
) -> tuple[dict[str, set[int]], dict[str, int]]:
    by_path = {row["source"].casefold(): row for row in native_rows}
    if len(by_path) != len(native_rows) or {row["path"].casefold() for row in corpus_rows} != set(by_path):
        raise DynamicVisibilityAreaJoinError("area corpus and native report paths differ")
    areas: dict[str, set[int]] = {}
    counts: dict[str, int] = {}
    for row in corpus_rows:
        source = row["path"]
        key = _scene_key(source, area=True)
        if key in areas:
            raise DynamicVisibilityAreaJoinError(f"{source}: duplicate scene area file")
        data = _checked_dump_path(input_root, source).read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != row["sourceBytes"] or md5 != row["fileDataMd5"].upper():
            raise DynamicVisibilityAreaJoinError(f"{source}: area dump differs from authenticated corpus row")
        parsed = audit_payload(data, layout, source=source)
        if parsed["counts"] != by_path[source.casefold()]["counts"]:
            raise DynamicVisibilityAreaJoinError(f"{source}: area native summary differs from current decoded bytes")
        framed = parse_dynamic_file("stream_area", data)
        total = next(item for item in framed["Vectors"] if item["fieldIndex"] == 0)
        ids = {struct.unpack_from("<i", data, total["bodyOffset"] + index * 4)[0]
               for index in range(total["count"])}
        if len(ids) != total["count"]:
            raise DynamicVisibilityAreaJoinError(f"{source}: duplicate TotalAreas ID")
        areas[key] = ids
        counts[key] = len(ids)
    return areas, counts


def _main_area_values(data: bytes, source: str, layout: dict[str, Any]) -> tuple[list[tuple[int, int, int]], int]:
    """Return (grid ordinal, RootComp ordinal, value) using the reviewed layout."""
    groups: list[tuple[int, int, int]] = []
    group_count = 0
    grid_body, grid_count, _ = _bounded_vector(data, _root_layout(data), 3, 4)
    visible = layout["visibleDesc"]
    for ordinal in range(grid_count):
        slot = grid_body + ordinal * 4
        grid = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
        uid_at = _field_span(data, grid, 0, 4)
        if uid_at is None:
            raise DynamicVisibilityAreaJoinError(f"{source}: grid[{ordinal}] lacks UniqueId")
        uid = struct.unpack_from("<I", data, uid_at)[0]
        root_body, root_count, _ = _bounded_vector(data, grid, int(layout["rootCompFieldIndex"]), int(layout["rootCompWidth"]))
        primitive_body, primitive_count, _ = _bounded_vector(data, grid, int(visible["vectorFieldIndex"]), 4)
        group_count += root_count
        for group in range(root_count):
            at = (root_body + group * int(layout["rootCompWidth"])
                  + int(layout["rootCompVisibleDescOffset"]) + int(visible["visibleAreaGroupOffset"]))
            invalid, type_id, grid_id, start = struct.unpack_from("<B3xiIi", data, at)
            num, total = struct.unpack_from("<ii", data, at + int(layout["groupNumOffset"]))
            if (invalid not in (0, 1) or type_id != int(visible["dataTypeValue"])
                    or grid_id != uid or start < 0 or num < 0 or start + num > primitive_count
                    or total != primitive_count or bool(invalid) == bool(num)):
                raise DynamicVisibilityAreaJoinError(
                    f"{source}: grid[{ordinal}] UniqueId={uid} RootComp[{group}].VisibleAreaGroup "
                    f"span differs: invalid={invalid} type={type_id} grid={grid_id} "
                    f"index={start} num={num} total={total} primitiveCount={primitive_count}"
                )
            for position in range(start, start + num):
                value = struct.unpack_from("<i", data, primitive_body + position * 4)[0]
                groups.append((ordinal, group, value))
    return groups, group_count


def _join_observed(
    scene_ids: dict[str, set[int]], observations: list[tuple[str, str | None, list[tuple[int, int, int]]]],
) -> tuple[Counter[str], dict[str, Counter[int]]]:
    counts: Counter[str] = Counter()
    by_scene: dict[str, Counter[int]] = defaultdict(Counter)
    for source, scene, values in observations:
        if scene is None:
            counts["extraMainFiles"] += 1
            counts["extraAreaGroupValues"] += len(values)
            for grid, group, value in values:
                if value != 0:
                    raise DynamicVisibilityAreaJoinError(
                        f"{source}: Extra grid[{grid}] RootComp[{group}] area value={value} has no scene area file"
                    )
            continue
        ids = scene_ids.get(scene)
        if ids is None:
            raise DynamicVisibilityAreaJoinError(f"{source}: no FBStreamArea.TotalAreas for scene={scene}")
        counts["sceneMainFiles"] += 1
        for grid, group, value in values:
            if value not in ids:
                raise DynamicVisibilityAreaJoinError(
                    f"{source}: grid[{grid}] RootComp[{group}] area value={value} "
                    f"absent from scene={scene} FBStreamArea.TotalAreas"
                )
            counts["sceneAreaGroupValues"] += 1
            if value:
                counts["nonzeroSceneAreaGroupValues"] += 1
            by_scene[scene][value] += 1
    return counts, by_scene


def audit(
    *, gameassembly: Path, metadata: Path, main_report_path: Path, main_input_root: Path,
    area_native_report_path: Path, area_corpus_report_path: Path, area_input_root: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    main, main_sha = _read_report(main_report_path, "endfield.dynamic-root-comp-native-audit.v7", "validated")
    area_native, area_sha = _read_report(area_native_report_path, "endfield.dynamic-stream-area-native-audit.v2", "validated")
    area_corpus, corpus_sha = _read_report(area_corpus_report_path, "endfield.dynamic-stream-area-current.v2", "current_corpus_pass")
    root_layout, area_layout, receipt = _check_shared_evidence(
        main, area_native, area_corpus, gameassembly=gameassembly, metadata=metadata,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    ids_by_scene, id_counts = _area_ids(
        area_corpus["corpus"]["files"], area_native["files"],
        input_root=area_input_root, layout=area_layout,
    )
    observations = []
    values_total: Counter[int] = Counter()
    seen_paths: set[str] = set()
    groups_total = 0
    for row in main["files"]:
        source = row["path"]
        if source.casefold() in seen_paths:
            raise DynamicVisibilityAreaJoinError(f"duplicate main file: {source}")
        seen_paths.add(source.casefold())
        data = _checked_dump_path(main_input_root, source).read_bytes()
        if hashlib.md5(data).hexdigest().upper() != row["fileDataMd5"].upper():
            raise DynamicVisibilityAreaJoinError(f"{source}: main dump differs from authenticated native audit row")
        values, group_count = _main_area_values(data, source, root_layout)
        if group_count != row["groups"]:
            raise DynamicVisibilityAreaJoinError(f"{source}: RootComp group count differs from native audit")
        groups_total += group_count
        values_total.update(value for _grid, _group, value in values)
        observations.append((source, _scene_key(source, area=False), values))
    if groups_total != main["corpus"]["groups"]:
        raise DynamicVisibilityAreaJoinError("main RootComp group total differs from native audit")
    reported_values = Counter({int(row["value"]): row["count"] for row in main["visibleDesc"]["values"]["visibleArea"]})
    if values_total != reported_values:
        raise DynamicVisibilityAreaJoinError("visible area values differ from source native audit")
    counts, by_scene = _join_observed(ids_by_scene, observations)
    counts["areaFiles"] = len(ids_by_scene)
    counts["mainFiles"] = len(observations)
    counts["rootCompGroups"] = groups_total
    if counts["sceneMainFiles"] + counts["extraMainFiles"] != counts["mainFiles"]:
        raise DynamicVisibilityAreaJoinError("main scene/extra file partition differs")
    return {
        "format": FORMAT,
        "status": "validated",
        "inputSetSha256": expected_input_set_sha256.upper(),
        "nativeInputs": receipt,
        "sources": {
            "mainNativeReportSha256": main_sha,
            "areaNativeReportSha256": area_sha,
            "areaCorpusReportSha256": corpus_sha,
        },
        "counts": dict(counts),
        "scenes": [
            {
                "scene": key,
                "areaIdCount": id_counts[key],
                "groupValueCount": sum(by_scene[key].values()),
                "nonzeroValues": [
                    {"value": value, "count": count}
                    for value, count in sorted(by_scene[key].items()) if value
                ],
            }
            for key in sorted(ids_by_scene)
        ],
        "evidenceBoundary": {
            "exact": "Both native audit reports match their reviewed contracts and selected installed binaries, their current input-set identities agree, and all compared dump bytes match authenticated source rows.",
            "structuralOnly": "Every observed Scene main VisibleAreaGroup integer is a member of the same scene's FBStreamArea.TotalAreas ID set. Extra/SpaceshipCabins main files have no corresponding area file and are counted separately.",
            "unresolved": "The cross-file ID match does not observe live area selection or prove how the runtime uses these IDs.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    nonzero = [row for row in report["scenes"] if row["nonzeroValues"]]
    return "\n".join([
        "# DynamicStreaming visibility area ID join", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Scene main files: {counts['sceneMainFiles']:,}; all {counts['sceneAreaGroupValues']:,} area-group values occur in the same scene's FBStreamArea.TotalAreas.",
        f"- Extra main files without an area file: {counts['extraMainFiles']:,}; their area-group values: {counts['extraAreaGroupValues']:,} zero entries, kept outside the join.",
        f"- Scenes with nonzero area-group values: {', '.join(row['scene'] for row in nonzero) or 'none'}.",
        "- This is a stored ID relation, not a live area-selection receipt.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--main-report", type=Path, default=DEFAULT_MAIN_REPORT)
    parser.add_argument("--main-input-root", type=Path, required=True)
    parser.add_argument("--area-native-report", type=Path, default=DEFAULT_AREA_NATIVE_REPORT)
    parser.add_argument("--area-corpus-report", type=Path, default=DEFAULT_AREA_CORPUS_REPORT)
    parser.add_argument("--area-input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            main_report_path=args.main_report, main_input_root=args.main_input_root,
            area_native_report_path=args.area_native_report,
            area_corpus_report_path=args.area_corpus_report,
            area_input_root=args.area_input_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, struct.error) as exc:
        print(f"dynamic-visibility-area-join: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming visibility area join passed: "
        f"sceneFiles={report['counts']['sceneMainFiles']} "
        f"matchedValues={report['counts']['sceneAreaGroupValues']} "
        f"extraFiles={report['counts']['extraMainFiles']}"
    )
    print(f"JSON: {args.output}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
