"""Join authored MapConfig streaming paths to Unity objects and scene roots.

This is a stored-data join. Reviewed native claims separately establish the
conditional load and DynamicStreaming initialization route on the selected
installed build; neither source observes a live selected scene.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import mmap
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_visibility_state_join import _scene_key, _selected_inputs
from scripts.game_data.extraction.verify_export_freshness import build_report
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.schemas.map_config import decode_map_config
from scripts.repo_paths import REPO_ROOT


DEFAULT_MAIN_REPORT = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.json"
DEFAULT_RUNTIME_REPORT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_latest.json"
DEFAULT_EXPORT_SUMMARY = REPO_ROOT / "reports/export/export_full_summary.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_streaming_config_join_latest.json"
RUNTIME_CONTRACT = CONTRACTS_DIR / "dynamic_visibility_runtime_claims.json"
DEFAULT_VFS_LEDGER = REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
FORMAT = "endfield.dynamic-streaming-config-join.v2"
OBJECT_FIELDS = (
    "m_GameObject", "m_Enabled", "m_Script", "m_Name", "mapName",
    "exportScenePathRoot", "streamingDataPathRoot", "isDev", "mapSceneName",
    "useLowMemoryHLODLoadParameter",
)
REQUIRED_NATIVE_METHODS = (
    "BaseGameScene.get_sceneConfigPath", "BaseGameScene.GetCurPlatformPath",
    "GameScene._ExtractSceneConfig", "BaseGameScene.get_mapSceneName",
    "BaseGameScene.CreateDynamicStreamingScene", "DynamicStreamingScene.InitScene",
    "DynamicSceneFbDataLoader.Init", "DynamicSceneFbDataLoader.GetPath",
    "DynamicSceneFbDataLoader.GetGridData", "DynamicSceneFbDataLoader.GetFbData",
    "DynamicSceneFbDataLoaderBase.GetFbData",
    "DynamicSceneFbDataLoaderBase.TryLoadResource",
    "DynamicSceneFbDataLoader.AddChunkRef",
    "DynamicDataLoader.SetBasePath", "DynamicSceneVersionBanSet.LoadFromBasePath",
)


class DynamicStreamingConfigJoinError(ValueError):
    """Selected evidence or a stored identity relation differs."""


def _selected_runtime_report(report: dict[str, Any], receipt: dict[str, str]) -> str:
    contract, digest = read_reviewed_contract(
        RUNTIME_CONTRACT, schema="endfield.dynamic-visibility-runtime-claims.v16",
        label="dynamic_visibility_runtime", status="validated",
    )
    expected = {key: receipt[key] for key in ("gameAssemblySha256", "metadataSha256")}
    symbols = {row.get("symbol") for row in report.get("methods", [])}
    if (report.get("format") != "endfield.dynamic-visibility-runtime-claims-audit.v3"
            or report.get("status") != "validated" or report.get("failures")
            or report.get("contractSha256") != digest
            or report.get("nativeInputs") != expected
            or symbols != set(contract["methods"])
            or len(report["methods"]) != len(contract["methods"])
            or not set(REQUIRED_NATIVE_METHODS) <= symbols):
        raise DynamicStreamingConfigJoinError("runtime claims report format/input/contract provenance differs")
    return digest


def _fresh_export(
    *, game_root: Path, export_root: Path, export_summary: Path,
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, Any], str]:
    if (gameassembly.resolve() != (game_root.parent / "GameAssembly.dll").resolve()
            or metadata.resolve() != (game_root / "il2cpp_data/Metadata/global-metadata.dat").resolve()):
        raise DynamicStreamingConfigJoinError("native inputs and export select different game roots")
    raw = export_summary.read_bytes()
    summary = json.loads(raw)
    if (Path(summary.get("game_root", "")).resolve() != game_root.resolve()
            or Path(summary.get("output_root", "")).resolve() != export_root.resolve()):
        raise DynamicStreamingConfigJoinError("export summary selects different game/output roots")
    freshness = build_report(
        game_root=game_root, output_root=export_root, summary_path=export_summary,
        sources=("StreamingAssets", "Persistent"),
    )
    if not freshness.get("fresh"):
        stale = [row["source"] for row in freshness.get("sources", []) if not row["fresh"]]
        raise DynamicStreamingConfigJoinError(
            f"export freshness differs: staleSources={stale} "
            f"missingOutputs={freshness.get('missingOutputs', [])} error={freshness.get('error', '')}"
        )
    layout = json.loads((export_root / "layout.json").read_text(encoding="utf-8"))
    if layout.get("schema") != "endfield.export-layout.v2" or layout.get("state") != "complete":
        raise DynamicStreamingConfigJoinError("selected export layout is not complete v2")
    return freshness, hashlib.sha256(raw).hexdigest().upper()


def _configs(config_dir: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    by_path: dict[str, list[str]] = defaultdict(list)
    hashes: dict[str, str] = {}
    for path in sorted(config_dir.glob("*.json")):
        raw = path.read_bytes()
        decode_map_config(raw, source=str(path))
        data = json.loads(raw)
        if data["mapIdStr"].casefold() != path.stem.casefold():
            raise DynamicStreamingConfigJoinError(f"{path}: mapIdStr differs from filename")
        logical = data["streamingMapConfigPath"]
        parts = PurePosixPath(logical).parts
        if (len(parts) != 2 or any(part in ("", ".", "..") for part in parts)
                or PurePosixPath(logical).suffix.casefold() != ".asset"
                or "\\" in logical):
            raise DynamicStreamingConfigJoinError(f"{path}: invalid relative streaming asset path {logical!r}")
        by_path[logical.casefold()].append(path.stem)
        hashes[path.stem] = hashlib.sha256(raw).hexdigest().upper()
    if not by_path:
        raise DynamicStreamingConfigJoinError(f"{config_dir}: no MapConfig files")
    return dict(by_path), hashes


def _asset_entries(asset_map: Path, expected: set[str]) -> dict[str, dict[str, Any]]:
    """Read scene StreamingMapConfig candidates from a large asset map."""
    prefix = b'"Container": "assets/beyond/dynamicassets/scenes/'
    entries: dict[str, dict[str, Any]] = {}
    with asset_map.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as view:
        cursor = 0
        while (at := view.find(prefix, cursor)) >= 0:
            end_value = view.find(b'"', at + len(b'"Container": "'))
            if end_value < 0:
                raise DynamicStreamingConfigJoinError(f"{asset_map}: unterminated container")
            container = view[at + len(b'"Container": "'):end_value].decode("utf-8").casefold()
            cursor = end_value + 1
            remainder = container.removeprefix("assets/beyond/dynamicassets/scenes/pc/")
            if len(remainder.split("/")) != 2 or not remainder.endswith("_streaming.asset"):
                continue
            start = view.rfind(b"\n    {", 0, at)
            end = view.find(b"\n    }", at)
            if start < 0 or end < 0:
                raise DynamicStreamingConfigJoinError(f"{asset_map}: unbounded row for {container}")
            row = json.loads(view[start + 5:end + 6])
            if container in entries:
                raise DynamicStreamingConfigJoinError(f"{asset_map}: duplicate container {container}")
            entries[container] = row
    missing = sorted(expected - entries.keys())
    if missing:
        raise DynamicStreamingConfigJoinError(f"{asset_map}: missing containers {missing[:8]}")
    return entries


def _objects_by_stem(object_dir: Path, stems: set[str]) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = defaultdict(list)
    for path in object_dir.iterdir():
        if path.suffix != ".json" or "_p" not in path.stem:
            continue
        stem = path.stem.rsplit("_p", 1)[0].casefold()
        if stem in stems:
            found[stem].append(path)
    return found


def _asset_source_key(source: str) -> str:
    parts = Path(source).parts
    try:
        start = next(index for index, part in enumerate(parts) if part.casefold() == "vfs")
    except StopIteration as exc:
        raise DynamicStreamingConfigJoinError(f"asset source is not a VFS path: {source}") from exc
    return "/".join(parts[start:]).casefold()


def _indexed_scripts(
    object_index: Path, assets: dict[str, dict[str, Any]],
) -> tuple[dict[tuple[str, int], dict[str, Any]], set[tuple[str, int]]]:
    """Select matching objects and census the class without materializing JSONL."""
    wanted = {
        (_asset_source_key(row["Source"]), row["PathID"])
        for row in assets.values()
    }
    wanted_ids = {path_id for _source, path_id in wanted}
    found: dict[tuple[str, int], dict[str, Any]] = {}
    all_class_keys: set[tuple[str, int]] = set()
    marker = b'"object":{'
    id_marker = b'"pathId":'
    class_marker = b'"fullName":"Beyond.Gameplay.Streaming.StreamingMapConfig"'
    with gzip.open(object_index, "rb") as source:
        for line in source:
            at = line.find(marker)
            if at < 0:
                continue
            object_end = line.find(b"}", at + len(marker))
            id_at = line.find(id_marker, at + len(marker), object_end)
            if object_end < 0 or id_at < 0:
                raise DynamicStreamingConfigJoinError(f"{object_index}: malformed object index row")
            start = id_at + len(id_marker)
            end = line.find(b",", start, object_end)
            if end < 0:
                end = object_end
            path_id = int(line[start:end])
            is_class = class_marker in line
            if path_id not in wanted_ids and not is_class:
                continue
            row = json.loads(line)
            obj = row.get("object") or {}
            key = (str(obj.get("source", "")).casefold(), path_id)
            if is_class:
                if key in all_class_keys:
                    raise DynamicStreamingConfigJoinError(f"{object_index}: duplicate class object {key}")
                all_class_keys.add(key)
            if key not in wanted:
                continue
            if key in found:
                raise DynamicStreamingConfigJoinError(f"{object_index}: duplicate object {key}")
            found[key] = row
    missing = sorted(wanted - found.keys())
    if missing:
        raise DynamicStreamingConfigJoinError(f"{object_index}: missing objects {missing[:8]}")
    return found, all_class_keys


def _object_index_summary(summary_path: Path, object_index: Path, digest: str) -> str:
    raw = summary_path.read_bytes()
    summary = json.loads(raw)
    output = (summary.get("outputs") or {}).get("objects") or {}
    if (summary.get("complete") is not True or summary.get("errors") != []
            or summary.get("schemaVersion") != 1
            or not isinstance((summary.get("counts") or {}).get("objects"), int)
            or summary["counts"]["objects"] <= 0
            or output.get("path") != object_index.name
            or output.get("bytes") != object_index.stat().st_size
            or str(output.get("sha256", "")).upper() != digest.upper()):
        raise DynamicStreamingConfigJoinError(f"{summary_path}: object index completion/output digest differs")
    return hashlib.sha256(raw).hexdigest().upper()


def _vfs_streaming_scenes(
    ledger: Path, expected_input_set_sha256: str,
) -> Counter[str]:
    """Count authenticated ordinary Streaming files by authored scene folder."""
    counts: Counter[str] = Counter()
    with gzip.open(ledger, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if (header.get("recordType") != "audit_header"
                or header.get("inputSetSha256", "").upper() != expected_input_set_sha256.upper()):
            raise DynamicStreamingConfigJoinError(f"{ledger}: VFS ledger input-set/header differs")
        for line in source:
            row = json.loads(line)
            if row.get("recordType") != "file":
                continue
            path = str(row.get("virtualPath") or "").split("/")
            if path[:3] != ["Data", "Streaming", "PC"] or len(path) < 5:
                continue
            if (row.get("inputSetSha256", "").upper() != expected_input_set_sha256.upper()
                    or row.get("status") != "verified"):
                raise DynamicStreamingConfigJoinError(f"{ledger}: nonverified Streaming row {row.get('virtualPath')}")
            counts[path[3].casefold()] += 1
    return counts


def _check_object(
    logical: str, row: dict[str, Any], candidate_paths: list[Path],
) -> tuple[dict[str, Any], Path]:
    matches: list[tuple[dict[str, Any], Path]] = []
    for path in candidate_paths:
        obj = json.loads(path.read_text(encoding="utf-8"))
        meta = obj.get("$animestudio", {})
        if (meta.get("pathId") == row.get("PathID")
                and str(meta.get("sourceOriginalPath", "")).casefold() == str(row.get("Source", "")).casefold()):
            matches.append((obj, path))
    if len(matches) != 1:
        raise DynamicStreamingConfigJoinError(
            f"{logical}: expected one exported object by Source+PathID, found {len(matches)}"
        )
    obj, path = matches[0]
    scene, filename = logical.split("/", 1)
    stem = filename.removesuffix(".asset")
    fields = tuple(key for key in obj if key != "$animestudio")
    if (row.get("Type") != "MonoBehaviour" or row.get("Name") != stem
            or obj.get("m_Name", "").casefold() != stem
            or fields != OBJECT_FIELDS
            or obj.get("mapName", "").casefold() != stem.removesuffix("_streaming")
            or obj.get("mapSceneName", "").casefold() != scene
            or obj.get("exportScenePathRoot", "").casefold()
            != f"Assets/Beyond/DynamicAssets/Scenes/PC/{scene}".casefold()
            or obj.get("streamingDataPathRoot", "").casefold()
            != f"Data/Streaming/PC/{scene}".casefold()):
        raise DynamicStreamingConfigJoinError(f"{logical}: exported StreamingMapConfig shape/path differs")
    return obj, path


def audit(
    *, gameassembly: Path, metadata: Path, game_root: Path,
    export_root: Path, export_summary: Path, main_report: Path,
    runtime_report: Path, vfs_ledger: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    main_raw = main_report.read_bytes()
    main = json.loads(main_raw)
    _layout, receipt, _digest = _selected_inputs(
        main, gameassembly=gameassembly, metadata=metadata,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    runtime_raw = runtime_report.read_bytes()
    _selected_runtime_report(json.loads(runtime_raw), receipt)
    freshness, summary_sha = _fresh_export(
        game_root=game_root, export_root=export_root, export_summary=export_summary,
        gameassembly=gameassembly, metadata=metadata,
    )
    by_path, config_hashes = _configs(export_root / "game/Json/MapConfig")
    prefix = "assets/beyond/dynamicassets/scenes/pc/"
    expected = {prefix + logical for logical in by_path}
    asset_map = export_root / "meta/StreamingAssets/asset_map/endfield_streamingassets_assets.json"
    assets = _asset_entries(asset_map, expected)
    object_index = export_root / "meta/StreamingAssets/object_index/objects.jsonl.gz"
    object_index_sha = sha256_file(object_index).upper()
    object_index_summary_sha = _object_index_summary(
        object_index.parent / "summary.json", object_index, object_index_sha,
    )
    indexed, all_class_keys = _indexed_scripts(object_index, assets)
    streaming_file_counts = _vfs_streaming_scenes(vfs_ledger, expected_input_set_sha256)
    stems = {PurePosixPath(container).stem for container in assets}
    objects = _objects_by_stem(export_root / "game/Unity/MonoBehaviour", stems)
    scene_main_counts: Counter[str] = Counter()
    for file in main["files"]:
        scene = _scene_key(file["path"])
        if scene is not None:
            scene_main_counts[scene] += 1
    rows = []
    scene_names = set()
    referenced_scenes = set()
    for container, asset in sorted(assets.items()):
        logical = container.removeprefix(prefix)
        map_ids = by_path.get(logical, [])
        obj, path = _check_object(logical, asset, objects.get(PurePosixPath(logical).stem, []))
        indexed_row = indexed[(_asset_source_key(asset["Source"]), asset["PathID"])]
        script = indexed_row.get("script") or {}
        if (indexed_row.get("type") != "MonoBehaviour"
                or indexed_row.get("decodeStatus") != "decoded"
                or indexed_row.get("name", "").casefold() != obj["m_Name"].casefold()
                or script.get("fullName") != "Beyond.Gameplay.Streaming.StreamingMapConfig"
                or script.get("assembly") != "Gameplay.Beyond.dll"):
            raise DynamicStreamingConfigJoinError(f"{logical}: indexed MonoScript class differs")
        scene = obj["mapSceneName"].casefold()
        scene_names.add(scene)
        if map_ids:
            referenced_scenes.add(scene)
        rows.append({
            "streamingMapConfigPath": logical,
            "mapConfigs": sorted(map_ids),
            "referencedByMapConfig": bool(map_ids),
            "assetContainer": asset["Container"],
            "assetSource": asset["Source"],
            "assetPathId": asset["PathID"],
            "exportedObject": str(path.relative_to(export_root)).replace("\\", "/"),
            "exportedObjectSha256": sha256_file(path).upper(),
            "monoScriptClass": script["fullName"],
            "mapSceneName": obj["mapSceneName"],
            "exportScenePathRoot": obj["exportScenePathRoot"],
            "streamingDataPathRoot": obj["streamingDataPathRoot"],
            "dynamicMainFileCount": scene_main_counts[scene],
            "streamingVfsFileCount": streaming_file_counts[scene],
        })
    uncatalogued = sorted(all_class_keys - indexed.keys())
    return {
        "format": FORMAT,
        "status": "validated",
        "inputSetSha256": expected_input_set_sha256.upper(),
        "nativeInputs": receipt,
        "sources": {
            "mainReportSha256": hashlib.sha256(main_raw).hexdigest().upper(),
            "runtimeReportSha256": hashlib.sha256(runtime_raw).hexdigest().upper(),
            "exportSummarySha256": summary_sha,
            "assetMapSha256": sha256_file(asset_map).upper(),
            "objectIndexSha256": object_index_sha,
            "objectIndexSummarySha256": object_index_summary_sha,
            "vfsLedgerSha256": sha256_file(vfs_ledger).upper(),
            "mapConfigSha256": config_hashes,
            "exportFreshness": freshness,
        },
        "counts": {
            "mapConfigs": sum(map(len, by_path.values())),
            "streamingAssets": len(rows),
            "referencedStreamingAssets": len(by_path),
            "unreferencedStreamingAssets": len(rows) - len(by_path),
            "indexedStreamingMapConfigObjects": len(all_class_keys),
            "assetScenes": len(scene_names),
            "referencedAssetScenes": len(referenced_scenes),
            "mainScenes": len(scene_main_counts),
            "assetsWithMainFiles": sum(bool(row["dynamicMainFileCount"]) for row in rows),
        },
        "sceneWithoutMain": sorted(scene_names - scene_main_counts.keys()),
        "mainWithoutReferencedAsset": sorted(scene_main_counts.keys() - referenced_scenes),
        "mainWithoutStreamingAsset": sorted(scene_main_counts.keys() - scene_names),
        "assetWithoutStreamingFiles": sorted(scene_names - streaming_file_counts.keys()),
        "streamingFilesWithoutAsset": sorted(streaming_file_counts.keys() - scene_names),
        "uncataloguedStreamingMapConfigObjects": [
            {"source": source, "pathId": path_id} for source, path_id in uncatalogued
        ],
        "assets": rows,
        "evidenceBoundary": {
            "direct": "Selected native claims check the MapConfig asset-path read, typed scene-config field, map-scene-name read, DynamicStreaming base-path and file templates, typed FlatBuffer low-IO read, and chunk-version checks.",
            "structuralOnly": "Fresh exported MapConfigs join to catalogued MonoBehaviours by container, source, and PathID. The original object index resolves their MonoScript class; mapSceneName joins to authenticated DynamicStreaming main-file directories and ordinary Streaming VFS files. Unreferenced assets are retained.",
            "unresolved": "The selected live map, successful asset loads, scenes absent from either file family, and runtime grid activation are not observed.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--export-summary", type=Path, default=DEFAULT_EXPORT_SUMMARY)
    parser.add_argument("--main-report", type=Path, default=DEFAULT_MAIN_REPORT)
    parser.add_argument("--runtime-report", type=Path, default=DEFAULT_RUNTIME_REPORT)
    parser.add_argument("--vfs-ledger", type=Path, default=DEFAULT_VFS_LEDGER)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            game_root=args.game_root, export_root=args.export_root,
            export_summary=args.export_summary, main_report=args.main_report,
            runtime_report=args.runtime_report,
            vfs_ledger=args.vfs_ledger,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-streaming-config-join: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = report["counts"]
    print(f"DynamicStreaming config join passed: MapConfigs={counts['mapConfigs']} "
          f"assets={counts['streamingAssets']} referenced={counts['referencedStreamingAssets']} "
          f"assetScenes={counts['assetScenes']} "
          f"mainScenes={counts['mainScenes']}")
    print(f"Scene gaps: assetWithoutMain={len(report['sceneWithoutMain'])} "
          f"mainWithoutReferencedAsset={len(report['mainWithoutReferencedAsset'])} "
          f"mainWithoutAsset={len(report['mainWithoutStreamingAsset'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
