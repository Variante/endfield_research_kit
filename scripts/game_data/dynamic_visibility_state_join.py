"""Join authenticated RootComp visibility state indices to scene MapConfig.

The RootComp audit establishes the selected native layout and current main
payloads. The export freshness guard checks that the selected Persistent
export still describes the installed client. This audit compares stored IDs;
it does not evaluate scene-state conditions or observe runtime activation.
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
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout
from scripts.game_data.extraction.verify_export_freshness import build_report
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_root_comp_native.json"
DEFAULT_MAIN_REPORT = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.json"
DEFAULT_EXPORT_SUMMARY = REPO_ROOT / "reports/export/export_full_summary.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_state_join_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_visibility_state_join_latest.md"
FORMAT = "endfield.dynamic-visibility-state-join.v1"
CONTRACT_SCHEMA = "endfield.dynamic-root-comp-native-contract.v7"
REPORT_FORMAT = "endfield.dynamic-root-comp-native-audit.v7"


class DynamicVisibilityStateJoinError(ValueError):
    """An input gate or current same-scene state-index relation differs."""


def _scene_key(source: str) -> str | None:
    parts = source.replace("\\", "/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise DynamicVisibilityStateJoinError(f"invalid DynamicStreaming source path: {source}")
    if (len(parts) < 6 or parts[:3] != ["Data", "DynamicStreaming", "PC"]
            or not parts[-1].startswith("fb_main_") or not parts[-1].endswith(".bytes")):
        raise DynamicVisibilityStateJoinError(f"unexpected main source path: {source}")
    if parts[3] == "Scene" and len(parts) == 6:
        return parts[4].casefold()
    if parts[3] == "Extra" and len(parts) >= 7:
        return None
    raise DynamicVisibilityStateJoinError(f"unexpected main source path: {source}")


def _selected_inputs(
    main: dict[str, Any], *, gameassembly: Path, metadata: Path,
    expected_input_set_sha256: str,
) -> tuple[dict[str, Any], dict[str, str], str]:
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=CONTRACT_SCHEMA, label="dynamic_root_comp", status="validated",
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVisibilityStateJoinError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"].upper():
        raise DynamicVisibilityStateJoinError("installed_native_inputs:missing-or-mismatched:UnityPlayer.dll")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": inputs["unityPlayerSha256"].upper(),
    }
    selected = expected_input_set_sha256.upper()
    if (main.get("format") != REPORT_FORMAT or main.get("status") != "validated"
            or main.get("nativeInputs") != receipt
            or main.get("rootCompContractSha256") != digest
            or main.get("inputSetSha256", "").upper() != selected
            or len(main.get("files", [])) != main.get("corpus", {}).get("files")):
        raise DynamicVisibilityStateJoinError("main native report format/input/contract provenance differs")
    return contract["layout"], receipt, digest


def _fresh_persistent_export(
    *, game_root: Path, export_root: Path, export_summary_path: Path,
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, Any], str]:
    if (gameassembly.resolve() != (game_root.parent / "GameAssembly.dll").resolve()
            or metadata.resolve() != (game_root / "il2cpp_data/Metadata/global-metadata.dat").resolve()):
        raise DynamicVisibilityStateJoinError("native binaries and Persistent export select different game roots")
    raw = export_summary_path.read_bytes()
    summary = json.loads(raw)
    if Path(summary.get("output_root", "")).resolve() != export_root.resolve():
        raise DynamicVisibilityStateJoinError("export summary output_root differs from selected export root")
    if Path(summary.get("game_root", "")).resolve() != game_root.resolve():
        raise DynamicVisibilityStateJoinError("export summary game_root differs from selected installed game")
    freshness = build_report(
        game_root=game_root, output_root=export_root,
        summary_path=export_summary_path, sources=("Persistent",),
    )
    if not freshness.get("fresh"):
        stale = [row["source"] for row in freshness.get("sources", []) if not row["fresh"]]
        missing = [row["kind"] for row in freshness.get("missingOutputs", [])]
        raise DynamicVisibilityStateJoinError(
            f"Persistent export freshness differs: staleSources={stale} missingOutputs={missing} "
            f"error={freshness.get('error', '')}"
        )
    layout = json.loads((export_root / "layout.json").read_text(encoding="utf-8"))
    if layout.get("schema") != "endfield.export-layout.v2" or layout.get("state") != "complete":
        raise DynamicVisibilityStateJoinError("selected export layout is not complete v2")
    return freshness, hashlib.sha256(raw).hexdigest().upper()


def _main_state_values(
    data: bytes, source: str, layout: dict[str, Any],
) -> tuple[list[tuple[int, int, int]], int, int, int]:
    """Return (grid, RootComp, value) plus group and auxiliary-vector counts."""
    values: list[tuple[int, int, int]] = []
    group_count = 0
    auxiliary = [0, 0]
    grid_body, grid_count, _ = _bounded_vector(data, _root_layout(data), 3, 4)
    visible = layout["visibleDesc"]
    for grid_ordinal in range(grid_count):
        slot = grid_body + 4 * grid_ordinal
        grid = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
        uid_at = _field_span(data, grid, 0, 4)
        if uid_at is None:
            raise DynamicVisibilityStateJoinError(f"{source}: grid[{grid_ordinal}] lacks UniqueId")
        uid = struct.unpack_from("<I", data, uid_at)[0]
        for field in (1, 2):
            _body, count, _end = _bounded_vector(data, grid, field, 4)
            auxiliary[field - 1] += count
        root_body, root_count, _ = _bounded_vector(
            data, grid, int(layout["rootCompFieldIndex"]), int(layout["rootCompWidth"]),
        )
        primitive_body, primitive_count, _ = _bounded_vector(
            data, grid, int(visible["vectorFieldIndex"]), 4,
        )
        group_count += root_count
        for group in range(root_count):
            at = (root_body + group * int(layout["rootCompWidth"])
                  + int(layout["rootCompVisibleDescOffset"])
                  + int(visible["visibleStateGroupOffset"]))
            invalid, type_id, grid_id, start = struct.unpack_from("<B3xiIi", data, at)
            num, total = struct.unpack_from("<ii", data, at + int(layout["groupNumOffset"]))
            if (invalid not in (0, 1) or type_id != int(visible["dataTypeValue"])
                    or grid_id != uid or start < 0 or num < 0 or start + num > primitive_count
                    or total != primitive_count or bool(invalid) == bool(num)):
                raise DynamicVisibilityStateJoinError(
                    f"{source}: grid[{grid_ordinal}] UniqueId={uid} RootComp[{group}].VisibleStateGroup "
                    f"span differs: invalid={invalid} type={type_id} grid={grid_id} "
                    f"index={start} num={num} total={total} primitiveCount={primitive_count}"
                )
            for position in range(start, start + num):
                value = struct.unpack_from("<i", data, primitive_body + 4 * position)[0]
                values.append((grid_ordinal, group, value))
    return values, group_count, auxiliary[0], auxiliary[1]


def _scene_state_names(config: dict[str, Any], scene: str, source: Path) -> dict[int, str]:
    if not isinstance(config, dict):
        raise DynamicVisibilityStateJoinError(f"{source}: MapConfig is not an object")
    map_id = config.get("mapIdStr")
    if not isinstance(map_id, str) or map_id.casefold() != scene:
        raise DynamicVisibilityStateJoinError(f"{source}: mapIdStr differs from scene={scene}")
    raw = config.get("sceneStates", {})
    if not isinstance(raw, dict):
        raise DynamicVisibilityStateJoinError(f"{source}: sceneStates is not an object")
    names: dict[int, str] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not name or type(value) is not int or value < 0 or value in names:
            raise DynamicVisibilityStateJoinError(f"{source}: invalid or duplicate sceneStates entry {name!r}={value!r}")
        names[value] = name
    return names


def _join_observed(
    state_names: dict[str, dict[int, str]],
    observations: list[tuple[str, str | None, list[tuple[int, int, int]]]],
) -> tuple[Counter[str], dict[str, Counter[int]]]:
    counts: Counter[str] = Counter()
    by_scene: dict[str, Counter[int]] = defaultdict(Counter)
    for source, scene, values in observations:
        if scene is None:
            counts["extraMainFiles"] += 1
            counts["extraStateGroupValues"] += len(values)
            continue
        counts["sceneMainFiles"] += 1
        if not values:
            continue
        names = state_names.get(scene)
        if names is None:
            raise DynamicVisibilityStateJoinError(f"{source}: no MapConfig sceneStates for scene={scene}")
        for grid, group, value in values:
            if value not in names:
                raise DynamicVisibilityStateJoinError(
                    f"{source}: grid[{grid}] RootComp[{group}] state value={value} "
                    f"absent from scene={scene} MapConfig.sceneStates"
                )
            counts["sceneStateGroupValues"] += 1
            by_scene[scene][value] += 1
    return counts, by_scene


def audit(
    *, gameassembly: Path, metadata: Path, game_root: Path,
    main_report_path: Path, main_input_root: Path, export_root: Path,
    export_summary_path: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    raw_main = main_report_path.read_bytes()
    main = json.loads(raw_main)
    layout, receipt, _digest = _selected_inputs(
        main, gameassembly=gameassembly, metadata=metadata,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    freshness, summary_sha = _fresh_persistent_export(
        game_root=game_root, export_root=export_root, export_summary_path=export_summary_path,
        gameassembly=gameassembly, metadata=metadata,
    )
    observations: list[tuple[str, str | None, list[tuple[int, int, int]]]] = []
    scene_keys: set[str] = set()
    seen_paths: set[str] = set()
    values_total: Counter[int] = Counter()
    groups_total = 0
    auxiliary_total = [0, 0]
    for row in main["files"]:
        source = row["path"]
        if source.casefold() in seen_paths:
            raise DynamicVisibilityStateJoinError(f"duplicate main file: {source}")
        seen_paths.add(source.casefold())
        data = _checked_dump_path(main_input_root, source).read_bytes()
        if hashlib.md5(data).hexdigest().upper() != row["fileDataMd5"].upper():
            raise DynamicVisibilityStateJoinError(f"{source}: main dump differs from authenticated native audit row")
        values, group_count, state_vector_count, area_vector_count = _main_state_values(data, source, layout)
        if group_count != row["groups"]:
            raise DynamicVisibilityStateJoinError(f"{source}: RootComp group count differs from native audit")
        groups_total += group_count
        auxiliary_total[0] += state_vector_count
        auxiliary_total[1] += area_vector_count
        values_total.update(value for _grid, _group, value in values)
        scene = _scene_key(source)
        if scene is not None and values:
            scene_keys.add(scene)
        observations.append((source, scene, values))
    if groups_total != main["corpus"]["groups"]:
        raise DynamicVisibilityStateJoinError("main RootComp group total differs from native audit")
    reported_values = Counter({int(row["value"]): row["count"]
                               for row in main["visibleDesc"]["values"]["visibleState"]})
    if values_total != reported_values:
        raise DynamicVisibilityStateJoinError("visible state values differ from source native audit")
    config_dir = export_root / "game/Json/MapConfig"
    state_names: dict[str, dict[int, str]] = {}
    config_receipts: dict[str, str] = {}
    for scene in sorted(scene_keys):
        path = config_dir / f"{scene}.json"
        raw = path.read_bytes()
        state_names[scene] = _scene_state_names(json.loads(raw), scene, path)
        config_receipts[scene] = hashlib.sha256(raw).hexdigest().upper()
    counts, by_scene = _join_observed(state_names, observations)
    counts["mainFiles"] = len(observations)
    counts["sceneConfigs"] = len(state_names)
    counts["rootCompGroups"] = groups_total
    counts["sceneVisibleStateInts"] = auxiliary_total[0]
    counts["sceneVisibleAreaInts"] = auxiliary_total[1]
    if counts["sceneMainFiles"] + counts["extraMainFiles"] != counts["mainFiles"]:
        raise DynamicVisibilityStateJoinError("main scene/extra file partition differs")
    return {
        "format": FORMAT,
        "status": "validated",
        "inputSetSha256": expected_input_set_sha256.upper(),
        "nativeInputs": receipt,
        "sources": {
            "mainNativeReportSha256": hashlib.sha256(raw_main).hexdigest().upper(),
            "exportSummarySha256": summary_sha,
            "persistentFingerprint": next(row["current"]["fingerprint"] for row in freshness["sources"]
                                          if row["source"] == "Persistent"),
        },
        "counts": dict(counts),
        "scenes": [
            {
                "scene": scene,
                "mapConfigSha256": config_receipts[scene],
                "configuredStates": len(state_names[scene]),
                "groupValueCount": sum(by_scene[scene].values()),
                "matchedStates": [
                    {"index": index, "name": state_names[scene][index], "count": count}
                    for index, count in sorted(by_scene[scene].items())
                ],
            }
            for scene in sorted(scene_keys)
        ],
        "evidenceBoundary": {
            "exact": "The selected native report matches its reviewed contract, installed binaries, VFS input set, and every compared main dump; the selected Persistent export passes the current-source freshness gate.",
            "structuralOnly": "Every observed Scene main VisibleStateGroup integer is a key in that scene's MapConfig.sceneStates reverse map. Zero is a named state index in the matched configs, not an assumed sentinel.",
            "unresolved": "The stored match does not evaluate MapConfig.sceneStateConditions, observe active state selection, or prove a live scene-specific runtime path.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    matched = [row for row in report["scenes"] if row["matchedStates"]]
    return "\n".join([
        "# DynamicStreaming visibility state index join", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Scene main files: {counts['sceneMainFiles']:,}; all {counts['sceneStateGroupValues']:,} state-group values occur in the same scene's MapConfig.sceneStates.",
        f"- Scenes with authored state-group values: {', '.join(row['scene'] for row in matched) or 'none'}.",
        f"- Auxiliary grid vectors: SceneVisibleStateInts={counts['sceneVisibleStateInts']:,}, SceneVisibleAreaInts={counts['sceneVisibleAreaInts']:,} entries.",
        "- This is a stored index relation, not a live state-selection receipt.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--main-report", type=Path, default=DEFAULT_MAIN_REPORT)
    parser.add_argument("--main-input-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--export-summary", type=Path, default=DEFAULT_EXPORT_SUMMARY)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata, game_root=args.game_root,
            main_report_path=args.main_report, main_input_root=args.main_input_root,
            export_root=args.export_root, export_summary_path=args.export_summary,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, struct.error) as exc:
        print(f"dynamic-visibility-state-join: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming visibility state join passed: "
        f"sceneFiles={report['counts']['sceneMainFiles']} "
        f"matchedValues={report['counts']['sceneStateGroupValues']} "
        f"sceneConfigs={report['counts']['sceneConfigs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
