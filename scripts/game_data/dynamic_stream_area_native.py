"""Validate FBStreamArea accessors, area predicate, and authored index spans.

The framing gate authenticates current VFS payloads first. This separate audit
names their fields only after the reviewed native code windows match the
explicit installed build. It does not observe live area activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_streaming import parse_dynamic_file
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract


CONTRACT = CONTRACTS_DIR / "dynamic_stream_area_native.json"
SCHEMA = "endfield.dynamic-stream-area-native-contract.v2"
CORPUS_FORMAT = "endfield.dynamic-stream-area-current.v2"
PRIMITIVES = {"System.Int32": ("<i", 4), "System.Single": ("<f", 4)}


class StreamAreaNativeError(ValueError):
    """The selected build, corpus, or authored index relation failed a gate."""


def _check_toggle_branch(body: bytes, method_pointer: int, branch_offset: int, toggle_pointer: int) -> None:
    """Require the selected JNE to target the separately checked parity window."""
    if branch_offset < 0 or branch_offset + 6 > len(body) or body[branch_offset:branch_offset + 2] != b"\x0f\x85":
        raise StreamAreaNativeError("stream_area_predicate toggle-off conditional branch differs")
    displacement = struct.unpack_from("<i", body, branch_offset + 2)[0]
    if method_pointer + branch_offset + 6 + displacement != toggle_pointer:
        raise StreamAreaNativeError("stream_area_predicate toggle-off branch target differs")


def _record_width(type_name: str, records: dict[str, dict[str, Any]]) -> int:
    if type_name in PRIMITIVES:
        return PRIMITIVES[type_name][1]
    if type_name not in records:
        raise StreamAreaNativeError(f"unknown record type {type_name}")
    return int(records[type_name]["width"])


def validate_native_layout(
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, Any], str, dict[str, str], dict[str, Any]]:
    """Return the pinned layout and predicate only when native witnesses match."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="stream_area", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise StreamAreaNativeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise StreamAreaNativeError(f"installed_native_inputs:missing:{unity}")
    unity_sha = sha256_file(unity).upper()
    if unity_sha != inputs["unityPlayerSha256"].upper():
        raise StreamAreaNativeError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")

    image = open_native_image(Path(gameassembly), Path(metadata))
    def validate_method_window(row: dict[str, Any], *, label: str) -> bytes:
        index = int(row["index"])
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label=label)
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        return_type = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or return_type != row["returnType"]:
            raise StreamAreaNativeError(f"{label} signature differs: {row['type']}.{row['method']}")
        extent = int(row["bodyExtent"])
        if not 0 < extent <= 65536:
            raise StreamAreaNativeError(f"{label} body extent invalid: {extent}")
        raw = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), extent)
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"].upper():
            raise StreamAreaNativeError(f"{label} body differs: {row['type']}.{row['method']}")
        return raw

    methods: dict[int, dict[str, Any]] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise StreamAreaNativeError(f"duplicate accessor method index {index}")
        validate_method_window(row, label="stream_area_accessor")
        methods[index] = row

    predicate = contract["runtimePredicate"]
    predicate_method = predicate["method"]
    body = validate_method_window(predicate_method, label="stream_area_predicate")
    toggle = predicate["toggleOffWindow"]
    toggle_extent = int(toggle["bodyExtent"])
    if not 0 < toggle_extent <= 64:
        raise StreamAreaNativeError(f"stream_area_predicate toggle window extent invalid: {toggle_extent}")
    toggle_pointer = image.pe.image_base + int(toggle["rva"])
    toggle_raw = image.pe.bytes_at_va(toggle_pointer, toggle_extent)
    if hashlib.sha256(toggle_raw).hexdigest().upper() != toggle["sha256"].upper():
        raise StreamAreaNativeError("stream_area_predicate toggle-off window differs")
    branch_offset = int(toggle["branchOffset"])
    _check_toggle_branch(body, image.pe.image_base + int(predicate_method["rva"]), branch_offset, toggle_pointer)

    layout = contract["layout"]
    records = {record["type"]: record for record in layout["records"]}
    if len(records) != len(layout["records"]):
        raise StreamAreaNativeError("duplicate record type")
    root_type = layout["rootType"]
    expected_methods: set[int] = set()

    def accessor(index: int, type_name: str, name: str, result_type: str, parameters: list[str]) -> None:
        row = methods.get(index)
        if row is None or (row["type"], row["method"], row["returnType"], row["parameters"]) != (
            type_name, name, result_type, parameters
        ):
            raise StreamAreaNativeError(f"accessor binding differs: {type_name}.{name}")
        expected_methods.add(index)

    for record in records.values():
        end = 0
        for field in record["fields"]:
            width = _record_width(field["type"], records)
            if int(field["offset"]) != end:
                raise StreamAreaNativeError(f"record field does not tile: {record['type']}.{field['name']}")
            end += width
            accessor(field["accessorMethodIndex"], record["type"], "get_" + field["name"], field["type"], [])
        if end != int(record["width"]):
            raise StreamAreaNativeError(f"record width differs: {record['type']}")
    vectors = layout["vectors"]
    if len({v["fieldIndex"] for v in vectors}) != len(vectors):
        raise StreamAreaNativeError("duplicate root vector field")
    for vector in vectors:
        if int(vector["elementWidth"]) != _record_width(vector["elementType"], records):
            raise StreamAreaNativeError(f"vector width differs: {vector['name']}")
        accessor(vector["accessorMethodIndex"], root_type, vector["name"], vector["elementType"], ["System.Int32"])
    inline = layout["inline"]
    if int(inline["width"]) != _record_width(inline["type"], records):
        raise StreamAreaNativeError("inline bounds width differs")
    accessor(inline["accessorMethodIndex"], root_type, "get_" + inline["name"], inline["type"], [])
    if expected_methods != set(methods):
        raise StreamAreaNativeError("unused accessor method in contract")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": unity_sha,
    }
    predicate_receipt = {
        "status": "validated",
        "method": f"{predicate_method['type']}.{predicate_method['method']}",
        "bodySha256": predicate_method["bodySha256"].upper(),
        "toggleOffSha256": toggle["sha256"].upper(),
        "reviewedMeaning": predicate["reviewedMeaning"],
    }
    return layout, digest, receipt, predicate_receipt


def _decode(data: bytes, offset: int, type_name: str, records: dict[str, dict[str, Any]]) -> Any:
    if type_name in PRIMITIVES:
        return struct.unpack_from(PRIMITIVES[type_name][0], data, offset)[0]
    return {
        field["name"]: _decode(data, offset + int(field["offset"]), field["type"], records)
        for field in records[type_name]["fields"]
    }


def _bounds_ordered(bounds: dict[str, Any]) -> bool:
    return (
        bounds["MinCoord"]["X"] <= bounds["MaxCoord"]["X"]
        and bounds["MinCoord"]["Y"] <= bounds["MaxCoord"]["Y"]
        and bounds["MinHeight"] <= bounds["MaxHeight"]
    )


def _contains(bounds: dict[str, Any], point: dict[str, Any]) -> bool:
    return (
        bounds["MinCoord"]["X"] <= point["X"] <= bounds["MaxCoord"]["X"]
        and bounds["MinCoord"]["Y"] <= point["Y"] <= bounds["MaxCoord"]["Y"]
    )


def _partition(spans: list[tuple[int, int]], size: int, *, source: str, name: str) -> None:
    covered = [False] * size
    for start, count in spans:
        if start < 0 or count < 0 or start + count > size:
            raise StreamAreaNativeError(f"{source}: {name} range {start}:{start + count} outside 0:{size}")
        for index in range(start, start + count):
            if covered[index]:
                raise StreamAreaNativeError(f"{source}: {name} overlaps at {index}")
            covered[index] = True
    if not all(covered):
        raise StreamAreaNativeError(f"{source}: {name} leaves {covered.count(False)} unowned entries")


def audit_payload(data: bytes, layout: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Decode named fields and verify only relations observed in authored data."""
    framed = parse_dynamic_file("stream_area", data)
    vectors = {v["fieldIndex"]: v for v in framed["Vectors"]}
    records = {record["type"]: record for record in layout["records"]}
    if set(vectors) != {v["fieldIndex"] for v in layout["vectors"]}:
        raise StreamAreaNativeError(f"{source}: root vector fields differ")
    values: dict[str, list[Any]] = {}
    for vector in layout["vectors"]:
        row = vectors[vector["fieldIndex"]]
        width = int(vector["elementWidth"])
        if row["elementWidth"] != width:
            raise StreamAreaNativeError(f"{source}: {vector['name']} element width differs")
        values[vector["name"]] = [
            _decode(data, row["bodyOffset"] + index * width, vector["elementType"], records)
            for index in range(row["count"])
        ]
    inline = layout["inline"]
    bounds_rows = {row["fieldIndex"]: row for row in framed["InlineFields"]}
    if set(bounds_rows) != {inline["fieldIndex"]} or bounds_rows[inline["fieldIndex"]]["width"] != inline["width"]:
        raise StreamAreaNativeError(f"{source}: inline bounds field differs")
    root_bounds = _decode(data, bounds_rows[inline["fieldIndex"]]["offset"], inline["type"], records)
    total = values["TotalAreas"]
    areas = values["Areas"]
    triggers = values["Triggers"]
    points = values["Points"]
    visible = values["AreaVisibleGroups"]
    area_ids = [row["AreaId"] for row in areas]
    if not total or total[0] != 0 or len(set(total)) != len(total) or set(total) != {0, *area_ids}:
        raise StreamAreaNativeError(f"{source}: TotalAreas and Areas ids differ")
    if len(set(area_ids)) != len(area_ids):
        raise StreamAreaNativeError(f"{source}: duplicate AreaId")
    if not set(values["RootVisible"]) <= set(total) or not set(visible) <= set(total):
        raise StreamAreaNativeError(f"{source}: visibility id absent from TotalAreas")
    _partition([(row["VisibleStart"], row["VisibleNum"]) for row in areas], len(visible), source=source, name="AreaVisibleGroups")
    _partition([(row["AreaPointStart"], row["AreaPointNum"]) for row in triggers], len(points), source=source, name="Points")
    for index, area in enumerate(areas):
        group = visible[area["VisibleStart"]:area["VisibleStart"] + area["VisibleNum"]]
        if not group or group[0] != 0 or group.count(0) != 1:
            raise StreamAreaNativeError(f"{source}: area {index} visibility slice lacks one leading zero")
    for index, trigger in enumerate(triggers):
        if trigger["AreaId"] not in area_ids:
            raise StreamAreaNativeError(f"{source}: trigger {index} AreaId absent from Areas")
        bounds = trigger["Bounds"]
        if not _bounds_ordered(bounds):
            raise StreamAreaNativeError(f"{source}: trigger {index} bounds inverted")
        point_indices = range(trigger["AreaPointStart"], trigger["AreaPointStart"] + trigger["AreaPointNum"])
        for point_index in point_indices:
            if not _contains(bounds, points[point_index]):
                raise StreamAreaNativeError(f"{source}: trigger {index} excludes point {point_index}")
        if not point_indices:
            raise StreamAreaNativeError(f"{source}: trigger {index} has no points for bounds check")
        x_values = [points[point_index]["X"] for point_index in point_indices]
        y_values = [points[point_index]["Y"] for point_index in point_indices]
        if (bounds["MinCoord"]["X"], bounds["MinCoord"]["Y"], bounds["MaxCoord"]["X"], bounds["MaxCoord"]["Y"]) != (
            min(x_values), min(y_values), max(x_values), max(y_values)
        ):
            raise StreamAreaNativeError(f"{source}: trigger {index} XY bounds are not tight around its points")
    if areas and not _bounds_ordered(root_bounds):
        raise StreamAreaNativeError(f"{source}: populated root bounds inverted")
    if areas:
        for index, trigger in enumerate(triggers):
            b = trigger["Bounds"]
            if not (_contains(root_bounds, b["MinCoord"]) and _contains(root_bounds, b["MaxCoord"]) and root_bounds["MinHeight"] <= b["MinHeight"] <= b["MaxHeight"] <= root_bounds["MaxHeight"]):
                raise StreamAreaNativeError(f"{source}: root bounds exclude trigger {index}")
    rotated_control: dict[str, Any] = {"status": "not_applicable"}
    if len(triggers) > 1:
        rotated_contained = sum(
            _contains(triggers[(index + 1) % len(triggers)]["Bounds"], points[point_index])
            for index, trigger in enumerate(triggers)
            for point_index in range(trigger["AreaPointStart"], trigger["AreaPointStart"] + trigger["AreaPointNum"])
        )
        rotated_control = {
            "status": "measured",
            "rotation": 1,
            "containedPoints": rotated_contained,
            "pointCount": len(points),
        }
    return {
        "source": source,
        "counts": {name: len(rows) for name, rows in values.items()},
        "rootBoundsOrdered": _bounds_ordered(root_bounds),
        "rootVisibleOutsideAreaGroupsCount": len(set(values["RootVisible"]) - set(visible) - {0}),
        "areaVisibilityPartition": "exact",
        "areaVisibilityZeroPrefixCount": len(areas),
        "triggerPointPartition": "exact",
        "triggerPointXYContainment": "exact",
        "tightTriggerXYBoundsCount": len(triggers),
        "rotatedTriggerBoundsControl": rotated_control,
        "rootTriggerContainment": "exact" if areas else "empty_root_sentinel_not_spatial",
    }


def audit_corpus(corpus_path: Path, input_root: Path, layout: dict[str, Any], expected_input_set_sha256: str) -> dict[str, Any]:
    corpus = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    if corpus.get("format") != CORPUS_FORMAT or corpus.get("status") != "current_corpus_pass":
        raise StreamAreaNativeError("stream_area corpus report is not a passing current v2 gate")
    actual_input_set = str(corpus.get("inputSetSha256", "")).upper()
    if actual_input_set != expected_input_set_sha256.upper():
        raise StreamAreaNativeError(f"stream_area input set differs: expected={expected_input_set_sha256} actual={actual_input_set}")
    rows = corpus["corpus"]["files"]
    if len(rows) != corpus["corpus"]["fileCount"]:
        raise StreamAreaNativeError("stream_area corpus report file count differs")
    files = []
    seen: set[str] = set()
    for row in rows:
        source = row["path"]
        parts = source.replace("\\", "/").split("/")
        if not parts or any(part in ("", ".", "..") or ":" in part for part in parts):
            raise StreamAreaNativeError(f"invalid corpus path {source!r}")
        if source.casefold() in seen:
            raise StreamAreaNativeError(f"duplicate corpus path {source}")
        seen.add(source.casefold())
        data = Path(input_root, *parts).read_bytes()
        if len(data) != row["sourceBytes"] or hashlib.md5(data).hexdigest().upper() != row["fileDataMd5"].upper():
            raise StreamAreaNativeError(f"{source}: dumped bytes differ from authenticated corpus row")
        files.append(audit_payload(data, layout, source=source))
    return {
        "format": "endfield.dynamic-stream-area-native-audit.v2",
        "status": "validated",
        "inputSetSha256": actual_input_set,
        "fileCount": len(files),
        "populatedFileCount": sum(bool(row["counts"]["Areas"]) for row in files),
        "indexPartitionFileCount": len(files),
        "files": files,
        "evidenceBoundary": "Selected-build generated accessors name serialized fields, and the selected unpatched CheckInArea code windows establish X/Z plus height bounds and even-odd trigger polygon tests. Index partitions and point containment are authored-data checks, not live activation evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--corpus-report", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        layout, contract_sha, native, predicate = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_corpus(args.corpus_report, args.input_root, layout, args.expected_input_set_sha256)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, struct.error) as error:
        print(f"stream-area-native-audit: {error}", file=sys.stderr)
        return 1
    report["contractSha256"] = contract_sha
    report["nativeInputs"] = native
    report["runtimePredicate"] = predicate
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stream-area native audit passed: files={report['fileCount']} populated={report['populatedFileCount']}")
    print(f"JSON: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
