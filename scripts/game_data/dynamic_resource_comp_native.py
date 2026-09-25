"""Audit scene-scoped ResourceComp references in authenticated fb_main grids.

Generated FlatBuffer getters establish the two nested record layouts. The
selected main and RootComp contracts supply grid vectors, DataGroup and
VisibleDesc. This audits stored references, not live resource activation.
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
from scripts.game_data.dynamic_root_comp_native import validate_native_layout as validate_root_layout
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    MAIN_NAME_RE,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import (
    _bounded_vector,
    _field_span,
    _root_layout,
    _table_layout,
    parse_dynamic_file,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_resource_comp_native.json"
SCHEMA = "endfield.dynamic-resource-comp-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_resource_comp_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_resource_comp_native_latest.md"
GROUP_FORMAT = "<B3x i I i i i"


class DynamicResourceCompError(ValueError):
    """The selected build, source corpus, or resource reference differs."""


def _unique_byte_after(raw: bytes, prefix: bytes, label: str) -> int:
    position = raw.find(prefix)
    if position < 0 or raw.find(prefix, position + 1) >= 0 or position + len(prefix) >= len(raw):
        raise DynamicResourceCompError(f"{label}: selected instruction differs")
    return raw[position + len(prefix)]


def _group_getter_offset(raw: bytes, label: str) -> int:
    base = raw.find(b"\x8b\x17")  # mov edx,[rdi]: inline struct base
    if base < 0 or raw.find(b"\x8b\x17", base + 1) >= 0:
        raise DynamicResourceCompError(f"{label}: group base read differs")
    positions = [i for i in range(base + 2, len(raw) - 2) if raw[i:i + 2] == b"\x83\xc2"]
    if len(positions) > 1:
        raise DynamicResourceCompError(f"{label}: group offset is ambiguous")
    return raw[positions[0] + 2] if positions else 0


def _record_fields(record: dict[str, Any], methods: dict[int, dict[str, Any]],
                   raw: dict[int, bytes], group_type: str, group_width: int,
                   visible_type: str, visible_width: int) -> dict[str, int]:
    fields = record["fields"]
    names = [f["name"] for f in fields]
    if len(names) != len(set(names)):
        raise DynamicResourceCompError(f"{record['type']}: duplicate getter field")
    offsets: dict[str, int] = {}
    spans: list[tuple[int, int, str]] = []
    for field in fields:
        name = field["name"]
        index = int(field["getterMethodIndex"])
        row = methods[index]
        if row["type"] != record["type"] or row["method"] != "get_" + name or row["parameters"]:
            raise DynamicResourceCompError(f"{record['type']}.{name}: getter identity differs")
        if row["returnType"] == group_type or row["returnType"] == visible_type:
            actual = _group_getter_offset(raw[index], row["method"])
        elif row["returnType"] in ("System.Int32", "System.UInt32"):
            actual = _unique_byte_after(raw[index], b"\x8d\x53", row["method"])
        else:
            raise DynamicResourceCompError(f"{record['type']}.{name}: getter result type differs")
        if actual != int(field["offset"]):
            raise DynamicResourceCompError(f"{record['type']}.{name}: getter offset {actual} differs")
        offsets[name] = actual
        width = group_width if row["returnType"] == group_type else visible_width if row["returnType"] == visible_type else 4
        spans.append((actual, actual + width, name))
    builder = methods[int(record["builderMethodIndex"])]
    if builder["type"] != record["type"] or builder["method"] != "Create" + record["type"].rsplit(".", 1)[-1]:
        raise DynamicResourceCompError(f"{record['type']}: builder identity differs")
    alignment = _unique_byte_after(raw[int(builder["index"])], b"\x45\x8d\x69", builder["method"] + " alignment")
    width = _unique_byte_after(raw[int(builder["index"])], b"\x45\x8d\x41", builder["method"] + " width")
    if alignment != int(record["alignment"]) or width != int(record["width"]):
        raise DynamicResourceCompError(f"{record['type']}: builder width/alignment differs")
    cursor = 0
    for start, end, name in sorted(spans):
        if start != cursor:
            raise DynamicResourceCompError(f"{record['type']}.{name}: field layout breaks at {cursor}:{start}")
        cursor = end
    if cursor != width:
        raise DynamicResourceCompError(f"{record['type']}: fields cover {cursor}/{width} bytes")
    return offsets


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[int, str], dict[str, str], dict[str, str]]:
    """Return only selected layouts authenticated against explicit native files."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_resource_comp", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicResourceCompError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicResourceCompError(f"installed_native_inputs:missing:{unity}")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": sha256_file(unity).upper(),
    }
    if receipt != inputs:
        raise DynamicResourceCompError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")
    root, _, main, enum_by_id, _, root_digests, root_receipt = validate_root_layout(gameassembly, metadata)
    if receipt != root_receipt:
        raise DynamicResourceCompError("resource and RootComp native contracts select different builds")
    layout = contract["layout"]
    if (layout["gridType"] != main["gridType"] or layout["dataGroupType"] != root["groupType"]
            or int(layout["dataGroupWidth"]) != int(root["groupWidth"])
            or layout["visibleDescType"] != root["visibleDesc"]["type"]
            or int(layout["visibleDescWidth"]) != int(root["visibleDesc"]["width"])):
        raise DynamicResourceCompError("shared native layouts differ")
    vectors = {row["name"]: row for row in main["vectors"]}
    for key, vector_name in (("resourceGroup", "ResourceGroupWithStateDesc"), ("resourceComp", "ResourceComp")):
        record = layout[key]
        vector = vectors[vector_name]
        if (record["type"] != vector["elementType"] or int(record["width"]) != int(vector["elementWidth"])
                or int(record["gridVectorFieldIndex"]) != int(vector["fieldIndex"])):
            raise DynamicResourceCompError(f"{key}: grid vector binding differs")

    image = open_native_image(gameassembly, metadata)
    methods: dict[int, dict[str, Any]] = {}
    raw: dict[int, bytes] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicResourceCompError(f"duplicate selected method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_resource_comp")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        result = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or result != row["returnType"]:
            raise DynamicResourceCompError(f"selected method signature differs: {row['type']}.{row['method']}")
        length = int(row["windowLength"])
        if not 0 < length <= 4096:
            raise DynamicResourceCompError(f"selected method window length invalid: {index}")
        body = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), length)
        if hashlib.sha256(body).hexdigest().upper() != row["windowSha256"].upper():
            raise DynamicResourceCompError(f"selected method window differs: {row['type']}.{row['method']}")
        methods[index], raw[index] = row, body
    resource_fields = _record_fields(
        layout["resourceComp"], methods, raw, layout["dataGroupType"], int(layout["dataGroupWidth"]),
        layout["visibleDescType"], int(layout["visibleDescWidth"]),
    )
    group_fields = _record_fields(
        layout["resourceGroup"], methods, raw, layout["dataGroupType"], int(layout["dataGroupWidth"]),
        layout["visibleDescType"], int(layout["visibleDescWidth"]),
    )
    if set(methods) != {int(f["getterMethodIndex"]) for record in (layout["resourceComp"], layout["resourceGroup"]) for f in record["fields"]} | {int(layout[k]["builderMethodIndex"]) for k in ("resourceComp", "resourceGroup")}:
        raise DynamicResourceCompError("unused selected resource method")
    expected_results = {
        "resourceComp": {"Res": layout["dataGroupType"], "Mount": layout["dataGroupType"],
                         "MountViewModel": layout["dataGroupType"], "NavState": "System.Int32",
                         "NavData": layout["dataGroupType"], "LodInfo": layout["dataGroupType"]},
        "resourceGroup": {"Group": layout["dataGroupType"], "SceneState": "System.UInt32",
                          "LogicState": "System.UInt32", "LevelNum": "System.Int32",
                          "FactoryIndex": "System.Int32", "VisibleDesc": layout["visibleDescType"]},
    }
    for key, expected in expected_results.items():
        fields = layout[key]["fields"]
        if set(expected) != {f["name"] for f in fields}:
            raise DynamicResourceCompError(f"{key}: selected field names differ")
        for field in fields:
            if methods[int(field["getterMethodIndex"])]["returnType"] != expected[field["name"]]:
                raise DynamicResourceCompError(f"{key}.{field['name']}: selected result type differs")
    name_to_id = {name: number for number, name in enum_by_id.items()}
    if len(name_to_id) != len(enum_by_id):
        raise DynamicResourceCompError("selected data enum has duplicate names")
    links = layout["resourceCompLinks"]
    if {row["field"] for row in links} != set(resource_fields) - {"NavState"}:
        raise DynamicResourceCompError("resource component group links differ")
    for row in links:
        if row["dataType"] not in name_to_id or row["vector"] not in vectors:
            raise DynamicResourceCompError(f"resource link {row['field']} has unknown selected type/vector")
    if (len(layout["resourcePayloadTypes"]) != len(set(layout["resourcePayloadTypes"]))
            or not layout["resourcePayloadTypes"]
            or any(name not in name_to_id or name not in vectors for name in layout["resourcePayloadTypes"])
            or layout["visibleDataType"] not in name_to_id
            or layout["visibleVector"] not in vectors):
        raise DynamicResourceCompError("resource payload or visibility selector differs")
    provenance = {"contractSha256": digest, "rootContractSha256": root_digests["rootCompContractSha256"], "nativeInputs": receipt}
    return layout, root, main, enum_by_id, provenance, {"resourceComp": resource_fields, "resourceGroup": group_fields}


def _group(data: bytes, offset: int) -> dict[str, int]:
    invalid, type_id, grid, index, num, total = struct.unpack_from(GROUP_FORMAT, data, offset)
    return {"invalid": invalid, "type": type_id, "grid": grid, "index": index, "num": num, "total": total}


def _checked_span(group: dict[str, int], *, label: str, expected_type: int,
                  expected_grid: int, target_count: int) -> tuple[int, int] | None:
    if group["type"] != expected_type or group["invalid"] not in (0, 1):
        raise DynamicResourceCompError(f"{label}: DataGroup type/invalid differs: {group}")
    if group["invalid"]:
        if group["num"] != 0:
            raise DynamicResourceCompError(f"{label}: invalid DataGroup has Num={group['num']}")
        return None
    if (group["grid"] != expected_grid or group["total"] != target_count
            or group["index"] < 0 or group["num"] <= 0
            or group["index"] + group["num"] > target_count):
        raise DynamicResourceCompError(
            f"{label}: DataGroup span differs: {group}; expected Grid={expected_grid} TotalInGrid={target_count}"
        )
    return group["index"], group["index"] + group["num"]


def _partition(spans: list[tuple[int, int]], count: int, label: str) -> None:
    cursor = 0
    for start, end in sorted(spans):
        if start != cursor:
            raise DynamicResourceCompError(f"{label}: span partition breaks at {cursor}; next={start}:{end} targetCount={count}")
        cursor = end
    if cursor != count:
        raise DynamicResourceCompError(f"{label}: span partition covers {cursor}/{count}")


def audit_current_main(layout: dict[str, Any], root_layout: dict[str, Any], main_layout: dict[str, Any],
                       enum_by_id: dict[int, str], *, outer_path: Path, ledger_path: Path,
                       cli_path: Path, input_root: Path, expected_input_set_sha256: str) -> dict[str, Any]:
    """Rejoin every current main dump, then resolve resource groups scene locally."""
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    vectors = {row["name"]: row for row in main_layout["vectors"]}
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in main_layout["vectors"]}
    name_to_id = {name: number for number, name in enum_by_id.items()}
    links = {row["field"]: row for row in layout["resourceCompLinks"]}
    resource_field = int(layout["resourceComp"]["gridVectorFieldIndex"])
    group_field = int(layout["resourceGroup"]["gridVectorFieldIndex"])
    primitive_field = int(vectors[layout["visibleVector"]]["fieldIndex"])
    root_field = int(root_layout["rootCompFieldIndex"])
    comp_offsets = {f["name"]: int(f["offset"]) for f in layout["resourceComp"]["fields"]}
    group_offsets = {f["name"]: int(f["offset"]) for f in layout["resourceGroup"]["fields"]}
    visible_state_offset = int(root_layout["visibleDesc"]["visibleStateGroupOffset"])
    visible_area_offset = int(root_layout["visibleDesc"]["visibleAreaGroupOffset"])
    root_visible_offset = int(root_layout["rootCompVisibleDescOffset"])
    visible_type = name_to_id[layout["visibleDataType"]]
    payload_types = {name_to_id[name]: name for name in layout["resourcePayloadTypes"]}
    scene_grids: dict[tuple[str, int], dict[str, Any]] = {}
    target_groups: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    scalar_values: dict[str, Counter[int]] = defaultdict(Counter)
    unowned_samples: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen_paths:
            raise DynamicResourceCompError(f"duplicate current main path: {path}")
        seen_paths.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["declaredBytes"] or md5 != source["fileDataMd5"]:
            raise DynamicResourceCompError(f"{path}: dumped length/MD5 differs from authenticated VFS row")
        parse_dynamic_file("main", data, main_vector_widths=widths)
        root = _root_layout(data)
        grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
        scene = path.rsplit("/fb_main_", 1)[0]
        if scene == path:
            raise DynamicResourceCompError(f"{path}: main filename has no scene prefix")
        totals.update(files=1, bytes=len(data), grids=grid_count)
        for ordinal in range(grid_count):
            slot = grid_body + ordinal * 4
            table = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
            uid_address = _field_span(data, table, 0, 4)
            if uid_address is None:
                raise DynamicResourceCompError(f"{path}: grid[{ordinal}] lacks UniqueId")
            uid = struct.unpack_from("<I", data, uid_address)[0]
            key = (scene, uid)
            if key in scene_grids:
                raise DynamicResourceCompError(f"{path}: duplicate scene-local grid UniqueId={uid}")
            vector_spans = {field: _bounded_vector(data, table, field, width) for field, width in widths.items()}
            vector_counts = {field: span[1] for field, span in vector_spans.items()}
            scene_grids[key] = {"source": path, "ordinal": ordinal, "counts": vector_counts}
            comp_body, comp_count, _ = vector_spans[resource_field]
            group_body, group_count, _ = vector_spans[group_field]
            primitive_count = vector_counts[primitive_field]
            totals.update(resourceComps=comp_count, resourceGroups=group_count, primitiveInts=primitive_count)
            link_spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
            visible_spans: list[tuple[int, int]] = []
            for index in range(comp_count):
                start = comp_body + index * int(layout["resourceComp"]["width"])
                scalar_values["NavState"][struct.unpack_from("<i", data, start + comp_offsets["NavState"])[0]] += 1
                for name, link in links.items():
                    vector = vectors[link["vector"]]
                    target_field = int(vector["fieldIndex"])
                    group = _group(data, start + comp_offsets[name])
                    span = _checked_span(
                        group, label=f"{path}: grid[{ordinal}] ResourceComp[{index}].{name}",
                        expected_type=name_to_id[link["dataType"]], expected_grid=uid,
                        target_count=vector_counts[target_field],
                    )
                    if span is not None:
                        link_spans[name].append(span)
                        group_counts[name + "Groups"] += 1
                        group_counts[name + "Elements"] += span[1] - span[0]
            for name, link in links.items():
                _partition(
                    link_spans[name], vector_counts[int(vectors[link["vector"]]["fieldIndex"])],
                    f"{path}: grid[{ordinal}] ResourceComp.{name} -> {link['vector']}",
                )
            for index in range(group_count):
                start = group_body + index * int(layout["resourceGroup"]["width"])
                for name, fmt in (("SceneState", "<I"), ("LogicState", "<I"), ("LevelNum", "<i"), ("FactoryIndex", "<i")):
                    scalar_values[name][struct.unpack_from(fmt, data, start + group_offsets[name])[0]] += 1
                group = _group(data, start + group_offsets["Group"])
                if group["invalid"] not in (0, 1) or group["type"] not in payload_types:
                    raise DynamicResourceCompError(f"{path}: grid[{ordinal}] ResourceGroup[{index}].Group type/invalid differs: {group}")
                if group["invalid"]:
                    if group["num"] != 0:
                        raise DynamicResourceCompError(f"{path}: invalid ResourceGroup[{index}].Group has Num={group['num']}")
                    totals["invalidPayloadGroups"] += 1
                else:
                    target_groups.append({"source": path, "ordinal": ordinal, "scene": scene, "uid": uid,
                                          "index": index, "group": group})
                    group_counts[payload_types[group["type"]] + "Groups"] += 1
                    group_counts[payload_types[group["type"]] + "Elements"] += group["num"]
                for name, shift in (("VisibleState", visible_state_offset), ("VisibleArea", visible_area_offset)):
                    visible = _group(data, start + group_offsets["VisibleDesc"] + shift)
                    span = _checked_span(
                        visible, label=f"{path}: grid[{ordinal}] ResourceGroup[{index}].{name}",
                        expected_type=visible_type, expected_grid=uid, target_count=primitive_count,
                    )
                    if span is not None:
                        visible_spans.append(span)
                        group_counts["Resource" + name + "Elements"] += span[1] - span[0]
            root_body, root_count, _ = vector_spans[root_field]
            for index in range(root_count):
                start = root_body + index * int(root_layout["rootCompWidth"])
                for name, shift in (("VisibleState", visible_state_offset), ("VisibleArea", visible_area_offset)):
                    visible = _group(data, start + root_visible_offset + shift)
                    span = _checked_span(
                        visible, label=f"{path}: grid[{ordinal}] RootComp[{index}].{name}",
                        expected_type=visible_type, expected_grid=uid, target_count=primitive_count,
                    )
                    if span is not None:
                        visible_spans.append(span)
                        group_counts["Root" + name + "Elements"] += span[1] - span[0]
            previous_end = 0
            for start, end in sorted(visible_spans):
                if start < previous_end:
                    raise DynamicResourceCompError(f"{path}: grid[{ordinal}] resource/RootComp PrimitiveIntList spans overlap at {start}")
                previous_end = end
            covered = {position for start, end in visible_spans for position in range(start, end)}
            totals["visibleOwnedPrimitiveInts"] += len(covered)
            totals["visibleUnownedPrimitiveInts"] += primitive_count - len(covered)
            primitive_body = vector_spans[primitive_field][0]
            for position in range(primitive_count):
                if position in covered:
                    continue
                value = struct.unpack_from("<i", data, primitive_body + position * 4)[0]
                totals["nonzeroUnownedPrimitiveInts"] += value != 0
                if len(unowned_samples) < 12:
                    unowned_samples.append({"source": path, "gridUniqueId": uid, "index": position, "value": value})

    payload_spans: dict[tuple[str, int, int], list[tuple[int, int]]] = defaultdict(list)
    for item in target_groups:
        group = item["group"]
        target_key = (item["scene"], group["grid"])
        target = scene_grids.get(target_key)
        if target is None:
            raise DynamicResourceCompError(f"{item['source']}: ResourceGroup[{item['index']}] target grid {target_key} is missing")
        vector = vectors[payload_types[group["type"]]]
        target_count = target["counts"][int(vector["fieldIndex"])]
        span = _checked_span(
            group, label=f"{item['source']}: ResourceGroup[{item['index']}].Group",
            expected_type=group["type"], expected_grid=group["grid"], target_count=target_count,
        )
        if span is None:
            raise DynamicResourceCompError(f"{item['source']}: valid ResourceGroup[{item['index']}].Group lost its span")
        payload_spans[(item["scene"], group["grid"], group["type"])].append(span)
        totals["payloadTargetsSameFile" if target["source"] == item["source"] else "payloadTargetsOtherFile"] += 1
    for (scene, uid), grid in scene_grids.items():
        for type_id, name in payload_types.items():
            vector = vectors[name]
            _partition(
                payload_spans[(scene, uid, type_id)], grid["counts"][int(vector["fieldIndex"])],
                f"{grid['source']}: grid UniqueId={uid} ResourceGroup.Group -> {name}",
            )
    return {
        "format": "endfield.dynamic-resource-comp-native-audit.v1",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {"reportSha256": provenance["outerReportSha256"], "ledgerSha256": provenance["ledgerSha256"],
                  "ledgerFileRowCount": provenance["ledgerFileRowCount"]},
        "corpus": dict(totals),
        "groups": dict(group_counts),
        "scalarValues": {name: [{"value": value, "count": count} for value, count in counter.most_common()]
                         for name, counter in scalar_values.items()},
        "unownedPrimitiveSamples": unowned_samples,
        "evidenceBoundary": {
            "exact": "Selected generated getter offsets and builder widths, current VFS file identity, and bounded main vectors.",
            "structuralOnly": "Scene-local ResourceComp groups partition their named vectors. ResourceGroup.Group spans partition Model, Effect and Ecs vectors across main files of one scene. ResourceGroup and RootComp visible groups address disjoint PrimitiveIntList spans, leaving some entries unowned.",
            "unresolved": "Live grid loading, resource activation, state-filter evaluation and ownership of remaining primitive integers.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    return "\n".join([
        "# DynamicStreaming resource component audit", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Authenticated main files: {corpus['files']:,}; grids: {corpus['grids']:,}; ResourceComp records: {corpus['resourceComps']:,}; resource descriptors: {corpus['resourceGroups']:,}.",
        "- All five ResourceComp group fields partition their named same-grid vectors.",
        f"- Resource payload groups: {corpus['payloadTargetsSameFile']:,} target a grid in the same file; {corpus['payloadTargetsOtherFile']:,} target a different file of the same scene. Their Model, Effect and Ecs spans partition those target vectors exactly.",
        f"- Resource and RootComp visible groups address {corpus['visibleOwnedPrimitiveInts']:,}/{corpus['primitiveInts']:,} PrimitiveIntList entries without overlap; {corpus['visibleUnownedPrimitiveInts']:,} remain unowned by these groups, including {corpus['nonzeroUnownedPrimitiveInts']:,} nonzero values.",
        "- The report describes stored references, not live resource activation.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--stdout-json", action="store_true", help="print the report without writing files")
    args = parser.parse_args(argv)
    try:
        layout, root, main_layout, enum_by_id, native, _ = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_main(
            layout, root, main_layout, enum_by_id,
            outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-resource-comp-native-audit: {error}", file=sys.stderr)
        return 1
    report.update(native)
    if args.stdout_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.output_md.write_text(_markdown(report), encoding="utf-8")
        print(f"DynamicStreaming resource audit passed: files={report['corpus']['files']} grids={report['corpus']['grids']} ResourceComp={report['corpus']['resourceComps']}")
        print(f"JSON: {args.output_json}")
        print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
