#!/usr/bin/env python3
"""Verify the hash-pinned installed IFix payload and its exact target table."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
REPORT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/installed_ifix_patch_state.json"
)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def repo_path(value: str) -> Path:
    path = REPO_ROOT / Path(value.replace("/", str(Path('/'))))
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(record: dict, label: str) -> Path:
    key = "repo_path" if "repo_path" in record else "extracted_repo_path"
    path = repo_path(record[key])
    if not path.is_file():
        fail(f"missing {label}: {path}")
    expected_size = record.get("size")
    if expected_size is not None and path.stat().st_size != expected_size:
        fail(f"{label} size changed: {path.stat().st_size} != {expected_size}")
    actual_hash = sha256(path)
    if actual_hash.lower() != record["sha256"].lower():
        fail(f"{label} SHA-256 changed: {actual_hash}")
    return path


def check_installed_file(record: dict, label: str) -> None:
    path = Path(record["path_at_recovery"])
    if not path.is_file():
        fail(f"missing installed {label}: {path}")
    if path.stat().st_size != record["size"]:
        fail(f"installed {label} size changed")
    actual_hash = sha256(path)
    if actual_hash.lower() != record["sha256"].lower():
        fail(f"installed {label} SHA-256 changed: {actual_hash}")


def same_installed_path(value: object, expected: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return str(Path(value).resolve()).casefold() == str(Path(expected).resolve()).casefold()


def check_loader_build_provenance(
    report: dict,
    metadata_catalog: dict,
    native_map: dict,
) -> None:
    source_build = report.get("source_build") or {}
    game_assembly = source_build.get("game_assembly") or {}
    metadata = source_build.get("global_metadata") or {}
    catalog_source = metadata_catalog.get("metadata") or {}
    map_source = native_map.get("metadata") or {}
    if not (
        same_installed_path(catalog_source.get("path"), metadata.get("path_at_recovery", "")) and
        str(catalog_source.get("sha256") or "").lower() ==
            str(metadata.get("sha256") or "").lower()
    ):
        fail("loader metadata catalog native-build provenance is stale or mismatched")
    if not (
        same_installed_path(map_source.get("metadataPath"), metadata.get("path_at_recovery", "")) and
        str(map_source.get("metadataSha256") or "").lower() ==
            str(metadata.get("sha256") or "").lower() and
        same_installed_path(map_source.get("gameAssembly"),
                            game_assembly.get("path_at_recovery", "")) and
        str(map_source.get("gameAssemblySha256") or "").lower() ==
            str(game_assembly.get("sha256") or "").lower()
    ):
        fail("loader native map native-build provenance is stale or mismatched")


def read_i32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        fail(f"truncated int32 at 0x{offset:x}")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_string(data: bytes, offset: int) -> tuple[str, int]:
    length = 0
    shift = 0
    for _ in range(5):
        if offset >= len(data):
            fail("truncated 7-bit string length")
        value = data[offset]
        offset += 1
        length |= (value & 0x7F) << shift
        if not value & 0x80:
            end = offset + length
            if end > len(data):
                fail("truncated string payload")
            return data[offset:end].decode("utf-8"), end
        shift += 7
    fail("invalid 7-bit string length")
    raise AssertionError


def short_type(value: str) -> str:
    # Generic assembly-qualified names contain commas inside [[...]]. The report
    # intentionally records the stable leading type identity used for this audit.
    return value.split(",", 1)[0]


def parse_patch(data: bytes, layout: dict) -> tuple[list[dict], dict]:
    bridge_offset = int(layout["bridge_string_offset"], 16)
    bridge, offset = read_string(data, bridge_offset)
    type_count, offset = read_i32(data, offset)
    types = []
    for _ in range(type_count):
        value, offset = read_string(data, offset)
        types.append(value)
    observed_type_end = offset

    offset = int(layout["target_table_offset"], 16)
    target_count, offset = read_i32(data, offset)
    targets = []
    for _ in range(target_count):
        if offset >= len(data):
            fail("truncated target flags")
        flags = data[offset]
        offset += 1
        type_index, offset = read_i32(data, offset)
        method, offset = read_string(data, offset)
        parameter_count, offset = read_i32(data, offset)
        parameter_indexes = []
        for _ in range(parameter_count):
            parameter_index, offset = read_i32(data, offset)
            parameter_indexes.append(parameter_index)
        implementation_index, offset = read_i32(data, offset)
        try:
            declaring_type = types[type_index]
            parameters = [types[index] for index in parameter_indexes]
        except IndexError:
            fail("target references a type-table index outside the table")
        if flags != 0:
            fail(f"unexpected nonzero target flags: {flags}")
        targets.append(
            {
                "type": short_type(declaring_type),
                "method": method,
                "parameters": [short_type(value) for value in parameters],
                "implementation_index": implementation_index,
            }
        )
    observed_target_end = offset
    terminal, offset = read_i32(data, offset)
    return targets, {
        "bridge": bridge,
        "type_count": type_count,
        "type_table_end": observed_type_end,
        "target_count": target_count,
        "target_table_end": observed_target_end,
        "terminal": terminal,
        "file_end": offset,
    }


def check_vfs_index(path: Path, expected: dict, label: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload["summary"]
    for key, source in (("fileCount", "file_count"), ("chunkCount", "chunk_count"), ("byteCount", "byte_count")):
        if summary[key] != expected[source]:
            fail(f"{label} {key} changed: {summary[key]} != {expected[source]}")
    blocks = payload.get("blocks") or []
    if len(blocks) != 1:
        fail(f"{label} expected one indexed IFixPatchOut block, got {len(blocks)}")
    block = blocks[0]
    if block["version"] != expected["block_version"] or block["codeVersion"] != expected["code_version"]:
        fail(f"{label} block/code version changed")


def check_refresh_metadata(report: dict, patch_record: dict) -> None:
    refresh = report.get("refresh") or {}
    if not isinstance(refresh.get("tool"), str):
        fail("IFix report refresh metadata missing tool identity")
    expected = patch_record.get("sha256")
    actual = refresh.get("source_patch_sha256")
    if actual != expected:
        fail(
            "IFix report refresh patch SHA mismatch: "
            f"expected={expected!r} actual={actual!r}"
        )


def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    check_installed_file(report["source_build"]["game_assembly"], "GameAssembly")
    check_installed_file(report["source_build"]["global_metadata"], "global metadata")
    vfs = report["vfs_state"]
    check_installed_file(vfs["persistent_overlay"]["chunk"], "IFix VFS chunk")
    check_installed_file(vfs["persistent_overlay"]["block_catalog"], "IFix block catalog")
    for name, record in vfs["launcher_manifests"].items():
        if isinstance(record, dict):
            check_installed_file(record, f"launcher manifest {name}")
    base_index = check_file(vfs["base_streaming_assets"]["index"], "base IFix VFS index")
    persistent_index = check_file(vfs["persistent_overlay"]["index"], "Persistent IFix VFS index")
    patch_path = check_file(vfs["persistent_overlay"]["file"], "decrypted Gameplay patch")
    check_refresh_metadata(report, vfs["persistent_overlay"]["file"])
    metadata_catalog_path = check_file(
        report["loader_recovery"]["metadata_catalog"], "loader metadata catalog"
    )
    native_map_path = check_file(
        report["loader_recovery"]["native_map"], "loader native map"
    )
    metadata_catalog = json.loads(metadata_catalog_path.read_text(encoding="utf-8"))
    native_map = json.loads(native_map_path.read_text(encoding="utf-8"))
    check_loader_build_provenance(report, metadata_catalog, native_map)
    check_vfs_index(base_index, vfs["base_streaming_assets"], "base")
    check_vfs_index(persistent_index, vfs["persistent_overlay"], "Persistent")

    expected = report["patch_format"]
    observed_targets, observed = parse_patch(patch_path.read_bytes(), expected)
    for key in ("bridge", "type_count", "target_count"):
        if observed[key] != expected[key]:
            fail(f"patch {key} changed: {observed[key]!r} != {expected[key]!r}")
    for key in ("type_table_end", "target_table_end", "file_end"):
        if observed[key] != int(expected[key], 16):
            fail(f"patch {key} changed: 0x{observed[key]:x} != {expected[key]}")
    if observed["terminal"] != expected["terminal_int32"]:
        fail("patch terminal int32 changed")
    if observed_targets != report["targets"]:
        fail("parsed patch target table no longer matches the refreshed report records")

    protected_prefixes = (
        "Beyond.Gameplay.Actions.CharInfoSwitchChar",
        "Beyond.Gameplay.View.CharUIModelMono",
        "HG.Rendering.Runtime.HGRenderPipeline",
        "HG.Rendering.Runtime.DeferredLightingPass",
        "HG.Rendering.Runtime.HGRendererListUtils",
        "HG.Rendering.Runtime.HGGraphicsFeatureSwitch",
    )
    protected_methods = {
        "PrepareRenderPipelineSettings",
        "get_settingParameters",
        "set_settingParameters",
    }
    for target in observed_targets:
        if target["type"].startswith(protected_prefixes) or target[
            "method"
        ] in protected_methods:
            fail(f"Character Info/render protected target unexpectedly patched: {target}")

    if native_map["summary"]["mappedTargetCount"] != report["loader_recovery"]["native_map"]["mapped_targets"]:
        fail("loader mapped-target count changed")
    edge_set = {
        (edge["caller"]["methodIndex"], callee["methodIndex"])
        for edge in native_map["directCallEdges"]
        for callee in edge["callees"]
    }
    required_edges = {(482175, 482190), (482190, 485545), (482190, 485546), (482162, 482163), (485545, 485543), (485545, 485544)}
    missing_edges = required_edges - edge_set
    if missing_edges:
        fail(f"loader native edges missing: {sorted(missing_edges)}")

    print(
        f"PASS: installed Persistent IFix patch is hash-pinned, parses as {len(observed_targets)} exact "
        "Gameplay.Beyond targets, "
        "and does not replace the audited Character Info/render/animation/settings methods"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
