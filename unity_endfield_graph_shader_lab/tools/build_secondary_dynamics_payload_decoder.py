#!/usr/bin/env python3
"""Decode the safe, read-only portion of the secondary-dynamics payload.

The input is the reviewed static ``secondary_dynamics_solver_inputs.json``
contract.  This module never constructs a Unity object, calls a solver, writes
Transform state, or changes any input object.  It only validates the pinned
source contract and projects two unambiguous payloads:

* ``selectionData``'s explicit JSON positions/attributes; and
* every PPtr in ``uniquePreBuildData.proxyMesh.transformData.transformArray``.

The serialized proxy-mesh byte arrays deliberately remain raw unless their
record contains an explicit ``count`` and ``stride`` and the field is one of
the small, reviewed layouts below.  The current contract has no stride fields
for those arrays, so its generated report keeps them raw and marks their
semantics unresolved.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
CONTRACT_SCHEMA = "endfield.charinfo.secondary-dynamics-solver-inputs.v1"
REPORT_SCHEMA = "endfield.charinfo.secondary-dynamics-payload-decoder.v1"
INPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    / "secondary_dynamics_solver_inputs.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    / "secondary_dynamics_payload_decode.json"
)

# These values are intentionally duplicated as a small gate.  A decoder must
# never treat a newly substituted installed build as the pinned source used by
# the reviewed static-input contract.
EXPECTED_INPUT_SHA256 = "35ecd376533773035fce3afadd8935ee5f0f2466168d8a5f8016c158c64f6d97"
EXPECTED_SOURCE_BUILD = {
    "game_assembly": {
        "size": 280436712,
        "sha256": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
        "path_at_recovery": "D:/Program Files/Endfield Game/GameAssembly.dll",
    },
    "global_metadata": {
        "size": 62925560,
        "sha256": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
        "path_at_recovery": "D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
    },
    "code_registration": "0x18b9217d0",
    "asset_map": {
        "size": 759252292,
        "sha256": "148415835f911fc94a634925c50c2d8b9a1cd4f5f141412f956cbb143805b6f3",
        "repo_path": "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json",
    },
    "vfs_chunks": {
        "4A65D5C2457B9C4DBE29646A23A14004.chk": {
            "size": 1194696472,
            "sha256": "60472ad1584689c0e43fee9fa332e7abd75a18cc83fd91a6873d75f26ec3ce90",
            "path_at_recovery": "D:/Program Files/Endfield Game/Endfield_Data/StreamingAssets/VFS/7064D8E2/4A65D5C2457B9C4DBE29646A23A14004.chk",
        },
        "62EB15DCD74A3348E244B9B068AB9694.chk": {
            "size": 1040864172,
            "sha256": "db94219ee4f522a824c32ec979c2dc5bfd7b1013b4e45c18b77fb3ae4809694e",
            "path_at_recovery": "D:/Program Files/Endfield Game/Endfield_Data/StreamingAssets/VFS/7064D8E2/62EB15DCD74A3348E244B9B068AB9694.chk",
        },
        "98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk": {
            "size": 1152031554,
            "sha256": "dac3bee8b778dff1342d03bcc29d465fada2af0f0ae7c61111f99e2758a266e7",
            "path_at_recovery": "D:/Program Files/Endfield Game/Endfield_Data/StreamingAssets/VFS/7064D8E2/98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk",
        },
    },
}


class PayloadDecodeError(ValueError):
    """Raised when a source payload fails a fail-closed decoder gate."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PayloadDecodeError(f"{label}: expected number")
    result = float(value)
    if not math.isfinite(result):
        raise PayloadDecodeError(f"{label}: non-finite float")
    return result


def _repo_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PayloadDecodeError(f"{label}: expected a repo-relative path")
    path = (REPO_ROOT / value).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise PayloadDecodeError(f"{label}: path escapes repository") from exc
    return path


def _validate_file_record(record: dict[str, Any], label: str, *, strict: bool = True) -> Path:
    path = _repo_path(record.get("repo_path"), label)
    if not path.is_file():
        raise PayloadDecodeError(f"{label}: missing source file {record['repo_path']}")
    if not _is_int(record.get("size")) or int(record["size"]) < 0:
        raise PayloadDecodeError(f"{label}: source size drift")
    expected = record.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise PayloadDecodeError(f"{label}: invalid source hash")
    if strict and (int(record["size"]) != path.stat().st_size or file_sha256(path) != expected):
        raise PayloadDecodeError(f"{label}: source hash drift")
    return path


def validate_input(payload: dict[str, Any], *, input_path: Path | None = None) -> None:
    """Validate schema, pinned build evidence, and referenced source hashes."""

    if not isinstance(payload, dict):
        raise PayloadDecodeError("input: expected object")
    if payload.get("schema") != CONTRACT_SCHEMA:
        raise PayloadDecodeError(f"input: unexpected schema {payload.get('schema')!r}")
    if payload.get("status") != "static_inputs_recovered_solver_unimplemented":
        raise PayloadDecodeError("input: solver/input status is not the reviewed static contract")
    if payload.get("source_build") != EXPECTED_SOURCE_BUILD:
        raise PayloadDecodeError("input: pinned source_build hash/size contract drift")
    if input_path is not None:
        if not input_path.is_file():
            raise PayloadDecodeError(f"input: missing {input_path}")
        if file_sha256(input_path) != EXPECTED_INPUT_SHA256:
            raise PayloadDecodeError("input: source JSON hash drift")

    actors = payload.get("actors")
    if not isinstance(actors, dict) or not actors:
        raise PayloadDecodeError("input: actors must be a non-empty object")
    for actor_name, actor in actors.items():
        if not isinstance(actor, dict):
            raise PayloadDecodeError(f"{actor_name}: actor must be an object")
        source = actor.get("source")
        if not isinstance(source, dict):
            raise PayloadDecodeError(f"{actor_name}: missing source records")
        for key in ("owner_contract", "target_filter", "hierarchy_name_map"):
            record = source.get(key)
            if not isinstance(record, dict):
                raise PayloadDecodeError(f"{actor_name}: missing {key} source record")
            # Keep the recorded hash as a hard source identity in the input
            # contract, but report current generated-file drift below.  Some
            # ignored Unity manifests are regenerated with a different line
            # ending while their semantic hierarchy remains unchanged.
            _validate_file_record(record, f"{actor_name}.{key}", strict=False)
        if not isinstance(source.get("export_root"), str):
            raise PayloadDecodeError(f"{actor_name}: missing export_root")


def _hierarchy_map(actor: dict[str, Any], actor_name: str) -> dict[int, str]:
    path = _validate_file_record(
        actor["source"]["hierarchy_name_map"],
        f"{actor_name}.hierarchy_name_map",
        strict=False,
    )
    manifest = load_json(path)
    rows = manifest.get("transforms")
    if not isinstance(rows, list):
        raise PayloadDecodeError(f"{actor_name}: hierarchy map has no transforms")
    result: dict[int, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not _is_int(row.get("path_id")):
            raise PayloadDecodeError(f"{actor_name}: invalid hierarchy transform row {index}")
        path_value = row.get("path")
        if not isinstance(path_value, str) or not path_value:
            raise PayloadDecodeError(f"{actor_name}: empty hierarchy path at row {index}")
        path_id = int(row["path_id"])
        if path_id in result:
            raise PayloadDecodeError(f"{actor_name}: duplicate hierarchy PathID {path_id}")
        result[path_id] = path_value
    return result


def _source_hash_checks(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe recorded-vs-current hashes without promoting drift."""

    checks: dict[str, Any] = {}
    for actor_name, actor in payload["actors"].items():
        actor_checks: dict[str, Any] = {}
        for key in ("owner_contract", "target_filter", "hierarchy_name_map"):
            record = actor["source"][key]
            path = _repo_path(record["repo_path"], f"{actor_name}.{key}")
            actual_size = path.stat().st_size
            actual_hash = file_sha256(path)
            actor_checks[key] = {
                "repo_path": record["repo_path"],
                "recorded_size": int(record["size"]),
                "actual_size": actual_size,
                "recorded_sha256": record["sha256"],
                "actual_sha256": actual_hash,
                "matches": int(record["size"]) == actual_size and record["sha256"] == actual_hash,
            }
        checks[actor_name] = actor_checks
    return checks


def _pptr(value: Any, label: str, hierarchy: dict[int, str], index: int) -> dict[str, Any]:
    if not isinstance(value, dict) or not _is_int(value.get("m_FileID")) or not _is_int(value.get("m_PathID")):
        raise PayloadDecodeError(f"{label}[{index}]: invalid Transform PPtr")
    file_id = int(value["m_FileID"])
    path_id = int(value["m_PathID"])
    if file_id != 0:
        raise PayloadDecodeError(f"{label}[{index}]: external Transform PPtr file ID {file_id}")
    if path_id == 0:
        return {
            "index": index,
            "m_FileID": file_id,
            "m_PathID": path_id,
            "hierarchy_path": None,
            "status": "null",
            "pptr_valid": True,
        }
    path = hierarchy.get(path_id)
    if path is None:
        raise PayloadDecodeError(f"{label}[{index}]: unresolved Transform PPtr {path_id}")
    return {
        "index": index,
        "m_FileID": file_id,
        "m_PathID": path_id,
        "hierarchy_path": path,
        "status": "resolved",
        "pptr_valid": True,
    }


def _selection(selection: Any, label: str) -> dict[str, Any]:
    if not isinstance(selection, dict):
        raise PayloadDecodeError(f"{label}: expected object")
    positions = selection.get("positions")
    attributes = selection.get("attributes")
    if not isinstance(positions, list) or not isinstance(attributes, list):
        raise PayloadDecodeError(f"{label}: positions/attributes must be arrays")
    if len(positions) != len(attributes):
        raise PayloadDecodeError(f"{label}: positions/attributes count mismatch")
    decoded_positions = []
    for index, value in enumerate(positions):
        if not isinstance(value, dict):
            raise PayloadDecodeError(f"{label}.positions[{index}]: expected vector3")
        decoded_positions.append({
            axis: _finite(value.get(axis), f"{label}.positions[{index}].{axis}")
            for axis in ("x", "y", "z")
        })
    decoded_attributes = []
    for index, value in enumerate(attributes):
        if not isinstance(value, dict) or not _is_int(value.get("Value")):
            raise PayloadDecodeError(f"{label}.attributes[{index}]: expected integer Value")
        decoded_attributes.append({"Value": int(value["Value"])})
    max_connection = _finite(selection.get("maxConnectionDistance"), f"{label}.maxConnectionDistance")
    if max_connection < 0.0:
        raise PayloadDecodeError(f"{label}.maxConnectionDistance: negative value")
    user_edit = selection.get("userEdit")
    if not _is_int(user_edit):
        raise PayloadDecodeError(f"{label}.userEdit: expected integer")
    return {
        "count": len(decoded_positions),
        "positions": decoded_positions,
        "attributes": decoded_attributes,
        "max_connection_distance": max_connection,
        "user_edit": int(user_edit),
        "checks": {
            "count_match": True,
            "positions_finite": True,
            "attributes_valid": True,
        },
    }


# A layout is only eligible when the source record itself supplies ``stride``.
# These declarations prevent a future caller from silently treating an
# arbitrary byte blob as a familiar Unity value merely because of its field
# name.  No current source array supplies that field.
TYPED_LAYOUTS: dict[str, tuple[str, int, str]] = {
    "referenceIndices": ("int32", 4, "<i"),
    "attributes": ("uint8", 1, "<B"),
    "localPositions": ("float3", 12, "<3f"),
    "localNormals": ("float3", 12, "<3f"),
    "localTangents": ("float3", 12, "<3f"),
    "uv": ("float2", 8, "<2f"),
    "triangles": ("int32", 4, "<i"),
    "lines": ("int32", 4, "<i"),
    "skinBoneTransformIndices": ("int32", 4, "<i"),
    "skinBoneBindPoses": ("float16", 64, "<16f"),
    "transformData.flagArray": ("uint8", 1, "<B"),
    "transformData.initLocalPositionArray": ("float3", 12, "<3f"),
    "transformData.initLocalRotationArray": ("float4", 16, "<4f"),
}


def _raw_array(value: dict[str, Any], label: str) -> dict[str, Any]:
    raw = value.get("arrayBytes")
    if not isinstance(raw, list) or any(not _is_int(item) or not 0 <= item <= 255 for item in raw):
        raise PayloadDecodeError(f"{label}: invalid arrayBytes")
    count = value.get("count")
    length = value.get("length")
    if count is not None and (not _is_int(count) or count < 0):
        raise PayloadDecodeError(f"{label}: invalid count")
    if length is not None and (not _is_int(length) or length < 0):
        raise PayloadDecodeError(f"{label}: invalid length")
    if _is_int(count) and _is_int(length) and count > length:
        raise PayloadDecodeError(f"{label}: count exceeds length")
    raw_bytes = bytes(raw)
    return {
        "status": "raw_preserved",
        "semantic": "semantic_unresolved",
        "raw_preserved": True,
        "semantic_unresolved": True,
        "count": int(count) if _is_int(count) else None,
        "length": int(length) if _is_int(length) else None,
        "byte_length": len(raw_bytes),
        "array_bytes_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "array_bytes": list(raw),
    }


def _typed_array(value: dict[str, Any], label: str, layout: tuple[str, int, str]) -> dict[str, Any]:
    element_type, expected_stride, fmt = layout
    if not _is_int(value.get("count")) or not _is_int(value.get("stride")):
        return _raw_array(value, label)
    count = int(value["count"])
    stride = int(value["stride"])
    if count < 0 or stride != expected_stride:
        raise PayloadDecodeError(f"{label}: explicit count/stride mismatch")
    length_value = value.get("length", count)
    if not _is_int(length_value) or int(length_value) < count:
        raise PayloadDecodeError(f"{label}: invalid count/length")
    length = int(length_value)
    raw = value.get("arrayBytes")
    if not isinstance(raw, list) or any(not _is_int(item) or not 0 <= item <= 255 for item in raw):
        raise PayloadDecodeError(f"{label}: invalid arrayBytes")
    if len(raw) != length * stride:
        raise PayloadDecodeError(f"{label}: byte length does not match count/stride")
    raw_bytes = bytes(raw)
    values = []
    for index in range(count):
        decoded = struct.unpack_from(fmt, raw_bytes, index * stride)
        if element_type == "int32":
            integer = int(decoded[0])
            if integer < 0:
                raise PayloadDecodeError(f"{label}[{index}]: negative index {integer}")
            values.append(integer)
        elif element_type == "uint8":
            values.append(int(decoded[0]))
        else:
            numbers = [_finite(item, f"{label}[{index}]") for item in decoded]
            values.append(numbers)
    return {
        "status": "typed_decoded",
        "semantic": element_type,
        "raw_preserved": False,
        "semantic_unresolved": False,
        "count": count,
        "length": length,
        "stride_bytes": stride,
        "byte_length": len(raw_bytes),
        "values": values,
        "checks": {
            "count_length": True,
            "byte_length": True,
            "index_values_nonnegative": element_type == "int32",
            "finite": element_type.startswith("float"),
        },
    }


def _proxy_arrays(proxy: dict[str, Any], label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in proxy.items():
        path = f"{label}.{name}"
        if name == "transformData" and isinstance(value, dict):
            nested: dict[str, Any] = {}
            for nested_name, nested_value in value.items():
                nested_path = f"{path}.{nested_name}"
                if isinstance(nested_value, dict) and "arrayBytes" in nested_value:
                    layout = TYPED_LAYOUTS.get(f"transformData.{nested_name}")
                    nested[nested_name] = (
                        _typed_array(nested_value, nested_path, layout)
                        if layout is not None
                        else _raw_array(nested_value, nested_path)
                    )
                else:
                    nested[nested_name] = {
                        "status": "raw_preserved",
                        "semantic": "semantic_unresolved",
                        "raw_preserved": True,
                        "semantic_unresolved": True,
                        "value": _copy(nested_value),
                    }
            result[name] = nested
        elif isinstance(value, dict) and "arrayBytes" in value:
            layout = TYPED_LAYOUTS.get(name)
            result[name] = _typed_array(value, path, layout) if layout is not None else _raw_array(value, path)
        elif isinstance(value, list):
            result[name] = {
                "status": "raw_preserved",
                "semantic": "semantic_unresolved",
                "raw_preserved": True,
                "semantic_unresolved": True,
                "value": _copy(value),
            }
    return result


def decode_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a decoded report without mutating ``payload``."""

    validate_input(payload)
    actors: dict[str, Any] = {}
    source_hash_checks = _source_hash_checks(payload)
    source_hashes_match = all(
        check["matches"]
        for actor_checks in source_hash_checks.values()
        for check in actor_checks.values()
    )
    for actor_name, actor in payload["actors"].items():
        hierarchy = _hierarchy_map(actor, actor_name)
        cloths = []
        for cloth_index, cloth in enumerate(actor.get("cloths", [])):
            label = f"{actor_name}.cloths[{cloth_index}]"
            serialized2 = cloth.get("serialized_data2")
            if not isinstance(serialized2, dict):
                raise PayloadDecodeError(f"{label}: missing serialized_data2")
            selection = _selection(serialized2.get("selectionData"), f"{label}.selectionData")
            prebuild = serialized2.get("preBuildData")
            if not isinstance(prebuild, dict):
                raise PayloadDecodeError(f"{label}: missing preBuildData")
            unique = prebuild.get("uniquePreBuildData")
            if not isinstance(unique, dict):
                raise PayloadDecodeError(f"{label}: missing uniquePreBuildData")
            proxy = unique.get("proxyMesh")
            if not isinstance(proxy, dict):
                raise PayloadDecodeError(f"{label}: missing unique proxyMesh")
            transform_data = proxy.get("transformData")
            if not isinstance(transform_data, dict) or not isinstance(transform_data.get("transformArray"), list):
                raise PayloadDecodeError(f"{label}: missing transformArray")
            transform_array = [
                _pptr(value, f"{label}.transformArray", hierarchy, index)
                for index, value in enumerate(transform_data["transformArray"])
            ]

            source_proxy = prebuild.get("preBuildData", {}).get("proxyMesh")
            if not isinstance(source_proxy, dict):
                raise PayloadDecodeError(f"{label}: missing source proxyMesh")
            cloths.append({
                "path_id": int(cloth["path_id"]),
                "game_object_path": cloth.get("game_object_path"),
                "selection_data": selection,
                "transform_array": {
                    "count": len(transform_array),
                    "entries": transform_array,
                    "checks": {
                        "count_match": True,
                        "all_pptrs_valid": True,
                        "all_indices_in_order": all(
                            entry["index"] == index
                            for index, entry in enumerate(transform_array)
                        ),
                        "all_non_null_mapped": all(entry["status"] != "unresolved" for entry in transform_array),
                    },
                },
                "proxy_mesh_arrays": _proxy_arrays(source_proxy, f"{label}.proxyMesh"),
            })
        actors[actor_name] = {
            "character_id": actor.get("character_id"),
            "display_name": actor.get("display_name"),
            "cloths": cloths,
        }
    return {
        "schema": REPORT_SCHEMA,
        "status": (
            "decoded_read_only_payload"
            if source_hashes_match
            else "decoded_read_only_payload_source_hash_mismatch"
        ),
        "source": {
            "input_schema": CONTRACT_SCHEMA,
            "input_path": INPUT.relative_to(REPO_ROOT).as_posix(),
            "input_sha256": EXPECTED_INPUT_SHA256,
            "source_build": _copy(payload["source_build"]),
            "hash_checks": source_hash_checks,
            "hashes_match": source_hashes_match,
        },
        "actors": actors,
        "implementation_boundary": {
            "read_only": True,
            "solver_instantiated": False,
            "transforms_modified": False,
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "source_hashes_match": source_hashes_match,
            "limitation": "Decoded static payload only; no solver, Unity object, Transform writeback, or verified claim.",
        },
    }


def build_report() -> dict[str, Any]:
    payload = load_json(INPUT)
    validate_input(payload, input_path=INPUT)
    report = decode_payload(payload)
    report["source"]["input_size"] = INPUT.stat().st_size
    return report


def main() -> int:
    report = build_report()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(json.dumps({actor: len(value["cloths"]) for actor, value in report["actors"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
