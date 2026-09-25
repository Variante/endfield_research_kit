"""Audit authored DynamicStreaming DataIndex references against current main grids.

The selected native builder and getters establish the inline record layout.
The separate main-vector contract establishes the target vector extents. This
audit checks stored references only; it does not claim runtime activation.
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
from scripts.game_data.dynamic_main_native import (
    _checked_dump_path,
    validate_native_layout as validate_main_layout,
)
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
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_data_index_native.json"
SCHEMA = "endfield.dynamic-data-index-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_data_index_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_data_index_native_latest.md"
FIELD_FORMATS = {"System.Boolean": "<B", "System.Int32": "<i", "System.UInt32": "<I"}


class DynamicDataIndexError(ValueError):
    """The selected build, main corpus, or authored index relation differs."""


def _unique_pattern(raw: bytes, pattern: bytes, label: str) -> int:
    position = raw.find(pattern)
    if position < 0 or raw.find(pattern, position + 1) >= 0:
        raise DynamicDataIndexError(f"{label}: native instruction pattern differs")
    return position


def _builder_layout(raw: bytes) -> tuple[int, int, dict[str, int]]:
    """Decode the generated reverse-order struct writes, including padding."""
    start = _unique_pattern(raw, b"\x41\x8d\x51", "DataIndex.StartStruct alignment")
    size = _unique_pattern(raw, b"\x45\x8d\x41", "DataIndex.StartStruct size")
    index = _unique_pattern(raw, b"\x8b\x54\x24\x70", "DataIndex.Index write")
    grid = _unique_pattern(raw, b"\x8b\xd7", "DataIndex.Grid write")
    type_ = _unique_pattern(raw, b"\x8b\xd6", "DataIndex.Type write")
    pad = _unique_pattern(raw, b"\x41\x8d\x50", "DataIndex padding")
    invalid = _unique_pattern(raw, b"\x40\x8a\xd5", "DataIndex.IsInvalid write")
    if not start < size < index < grid < type_ < pad < invalid:
        raise DynamicDataIndexError("DataIndex builder write order differs")
    alignment, width, padding = raw[start + 3], raw[size + 3], raw[pad + 3]
    end = width
    offsets: dict[str, int] = {}
    for name, span in (("Index", 4), ("Grid", 4), ("Type", 4), ("padding", padding), ("IsInvalid", 1)):
        end -= span
        offsets[name] = end
    if end != 0 or width <= 0 or alignment <= 0 or width % alignment:
        raise DynamicDataIndexError("DataIndex builder width/alignment/padding differs")
    return width, alignment, offsets


def _getter_offset(raw: bytes, name: str) -> int:
    pattern = b"\x8d\x53" if name == "Grid" else b"\x8d\x7e"
    position = _unique_pattern(raw, pattern, f"DataIndex.get_{name} offset")
    if position + len(pattern) >= len(raw):
        raise DynamicDataIndexError(f"DataIndex.get_{name} offset is truncated")
    return raw[position + len(pattern)]


def validate_native_layout(
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[int, str], str, str, dict[str, str]]:
    """Authenticate both reviewed layouts and the live selected-build enum."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_data_index", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicDataIndexError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicDataIndexError(f"installed_native_inputs:missing:{unity}")
    unity_sha = sha256_file(unity).upper()
    if unity_sha != inputs["unityPlayerSha256"].upper():
        raise DynamicDataIndexError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")
    main_layout, main_digest, main_native = validate_main_layout(gameassembly, metadata)
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": unity_sha,
    }
    if receipt != main_native:
        raise DynamicDataIndexError("main vector and DataIndex native contracts select different builds")

    image = open_native_image(Path(gameassembly), Path(metadata))
    methods: dict[int, dict[str, Any]] = {}
    method_bytes: dict[int, bytes] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicDataIndexError(f"duplicate DataIndex method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_data_index")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        return_type = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or return_type != row["returnType"]:
            raise DynamicDataIndexError(f"method signature differs: {row['type']}.{row['method']}")
        raw = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), int(row["bodyExtent"]))
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"].upper():
            raise DynamicDataIndexError(f"method code window differs: {row['type']}.{row['method']}")
        methods[index] = row
        method_bytes[index] = raw

    layout = contract["layout"]
    field_rows = layout["fields"]
    fields = {row["name"]: row for row in field_rows}
    if set(fields) != {"IsInvalid", "Type", "Grid", "Index"} or len(field_rows) != len(fields):
        raise DynamicDataIndexError("DataIndex record fields differ")
    if {name: row["type"] for name, row in fields.items()} != {
        "IsInvalid": "System.Boolean", "Type": "System.Int32",
        "Grid": "System.UInt32", "Index": "System.Int32",
    }:
        raise DynamicDataIndexError("DataIndex record field types differ")
    builder = methods[int(layout["builderMethodIndex"])]
    if (builder["type"], builder["method"], builder["parameters"]) != (
        layout["recordType"], "CreateFBDynamicSceneDataIndex",
        ["Google.FlatBuffers.FlatBufferBuilder", "System.Boolean", "System.Int32", "System.UInt32", "System.Int32"],
    ):
        raise DynamicDataIndexError("DataIndex builder binding differs")
    width, alignment, offsets = _builder_layout(method_bytes[builder["index"]])
    if width != int(layout["recordWidth"]) or alignment != int(layout["recordAlignment"]):
        raise DynamicDataIndexError("DataIndex record size/alignment differs from builder")
    used = {builder["index"]}
    for name, field in fields.items():
        if int(field["offset"]) != offsets[name]:
            raise DynamicDataIndexError(f"DataIndex.{name} offset differs from builder")
        if name == "IsInvalid":
            continue
        method = methods[int(field["getterMethodIndex"])]
        if (method["type"], method["method"], method["parameters"], method["returnType"]) != (
            layout["recordType"], "get_" + name, [], field["type"],
        ):
            raise DynamicDataIndexError(f"DataIndex.{name} getter binding differs")
        if _getter_offset(method_bytes[method["index"]], name) != int(field["offset"]):
            raise DynamicDataIndexError(f"DataIndex.{name} getter offset differs")
        used.add(method["index"])
    if used != set(methods):
        raise DynamicDataIndexError("unused method in DataIndex native contract")
    if layout["gridType"] != main_layout["gridType"]:
        raise DynamicDataIndexError("DataIndex and main grid type differ")
    vector = next((v for v in main_layout["vectors"] if v["fieldIndex"] == layout["dataIndexFieldIndex"]), None)
    if vector is None or vector["name"] != "DataIndex" or vector["elementType"] != layout["recordType"] or vector["elementWidth"] != width:
        raise DynamicDataIndexError("main grid DataIndex vector binding differs")
    enum_rows = native_enum_members(
        image.metadata, field_defaults(image.metadata), image.pe, image.registration,
        layout["enumType"],
    )
    enum_by_id = {int(row["id"]): row["name"] for row in enum_rows}
    if len(enum_by_id) != len(enum_rows) or len(set(enum_by_id.values())) != len(enum_rows):
        raise DynamicDataIndexError("EDynamicSceneData enum has duplicate IDs or names")
    if enum_by_id.get(1) != vector["name"]:
        raise DynamicDataIndexError("EDynamicSceneData.DataIndex value differs")
    return layout, main_layout, enum_by_id, digest, main_digest, receipt


def _payload_grids(
    data: bytes, *, widths: dict[int, int], layout: dict[str, Any],
    enum_by_id: dict[int, str], name_to_field: dict[str, int], source: str,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Decode checked grid-local references from a framed main payload."""
    parse_dynamic_file("main", data, main_vector_widths=widths)
    root = _root_layout(data)
    grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
    fields = {row["name"]: row for row in layout["fields"]}
    stats: Counter[str] = Counter()
    grids: list[dict[str, Any]] = []
    for ordinal in range(grid_count):
        slot = grid_body + ordinal * 4
        grid_table = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
        uid_address = _field_span(data, grid_table, 0, 4)
        if uid_address is None:
            raise DynamicDataIndexError(f"{source}: grid[{ordinal}] has no UniqueId")
        unique_id = struct.unpack_from("<I", data, uid_address)[0]
        vector_counts: dict[int, int] = {}
        data_index_body = 0
        for field, width in widths.items():
            body, count, _ = _bounded_vector(data, grid_table, field, width)
            vector_counts[field] = count
            if field == int(layout["dataIndexFieldIndex"]):
                data_index_body = body
        indexes: dict[int, list[int]] = defaultdict(list)
        for record in range(vector_counts[int(layout["dataIndexFieldIndex"])]):
            start = data_index_body + record * int(layout["recordWidth"])
            values = {
                name: struct.unpack_from(FIELD_FORMATS[field["type"]], data, start + int(field["offset"]))[0]
                for name, field in fields.items()
            }
            if values["IsInvalid"] not in (0, 1):
                raise DynamicDataIndexError(f"{source}: grid[{ordinal}] DataIndex[{record}] has invalid Boolean")
            if values["IsInvalid"]:
                stats["invalidRecords"] += 1
                continue
            if data[start + 1:start + 4] != b"\x00\x00\x00":
                stats["nonzeroPaddingRecords"] += 1
            if values["Grid"] != unique_id:
                raise DynamicDataIndexError(
                    f"{source}: grid[{ordinal}] DataIndex[{record}] Grid={values['Grid']} "
                    f"does not equal containing UniqueId={unique_id}"
                )
            type_id = values["Type"]
            name = enum_by_id.get(type_id)
            field_index = name_to_field.get(name or "")
            if field_index is None:
                raise DynamicDataIndexError(
                    f"{source}: grid[{ordinal}] DataIndex[{record}] Type={type_id} "
                    f"has no same-named grid vector (enum={name})"
                )
            index = values["Index"]
            if index < 0 or index >= vector_counts[field_index]:
                raise DynamicDataIndexError(
                    f"{source}: grid[{ordinal}] DataIndex[{record}] Type={type_id} "
                    f"Index={index} outside {name} count={vector_counts[field_index]}"
                )
            indexes[type_id].append(index)
            stats["validRecords"] += 1
        grids.append({
            "source": source, "ordinal": ordinal, "uniqueId": unique_id,
            "vectorCounts": vector_counts, "indexes": dict(indexes),
        })
        stats["grids"] += 1
    return grids, stats


def _first_partition_failure(
    grids: list[dict[str, Any]], type_id: int, field_index: int,
) -> dict[str, Any] | None:
    for grid in grids:
        indexes = sorted(grid["indexes"].get(type_id, []))
        count = grid["vectorCounts"][field_index]
        if indexes != list(range(count)):
            return {
                "source": grid["source"], "ordinal": grid["ordinal"],
                "uniqueId": grid["uniqueId"], "indexesSample": indexes[:12],
                "indexCount": len(indexes), "vectorCount": count,
            }
    return None


def audit_current_main(
    layout: dict[str, Any], main_layout: dict[str, Any], enum_by_id: dict[int, str], *,
    outer_path: Path, ledger_path: Path, cli_path: Path, input_root: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in main_layout["vectors"]}
    name_to_field = {row["name"]: int(row["fieldIndex"]) for row in main_layout["vectors"]}
    if len(name_to_field) != len(widths):
        raise DynamicDataIndexError("duplicate SingleGrid vector name")
    grids: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    file_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen:
            raise DynamicDataIndexError(f"duplicate current main path: {path}")
        seen.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["declaredBytes"] or md5 != source["fileDataMd5"]:
            raise DynamicDataIndexError(
                f"{path}: dumped bytes differ from authenticated VFS row "
                f"length={len(data)}/{source['declaredBytes']} md5={md5}/{source['fileDataMd5']}"
            )
        try:
            file_grids, stats = _payload_grids(
                data, widths=widths, layout=layout, enum_by_id=enum_by_id,
                name_to_field=name_to_field, source=path,
            )
        except (ValueError, OverflowError) as exc:
            raise DynamicDataIndexError(f"{path}: DataIndex framing/reference failed: {exc}") from exc
        grids.extend(file_grids)
        totals.update(stats)
        totals.update({"files": 1, "bytes": len(data)})
        file_rows.append({"path": path, "fileDataMd5": md5, "grids": len(file_grids), "records": stats["validRecords"] + stats["invalidRecords"]})
    type_ids = sorted({type_id for grid in grids for type_id in grid["indexes"]})
    type_rows: list[dict[str, Any]] = []
    for type_id in type_ids:
        name = enum_by_id[type_id]
        field_index = name_to_field[name]
        failure = _first_partition_failure(grids, type_id, field_index)
        if failure is not None:
            raise DynamicDataIndexError(
                f"{failure['source']}: grid[{failure['ordinal']}] UniqueId={failure['uniqueId']} "
                f"Type={type_id} {name}: Index values do not partition same-named vector "
                f"indexes={failure['indexesSample']} ({failure['indexCount']} total) "
                f"vectorCount={failure['vectorCount']}"
            )
        rivals = [
            {"fieldIndex": other, "name": other_name}
            for other_name, other in sorted(name_to_field.items(), key=lambda item: item[1])
            if other != field_index and _first_partition_failure(grids, type_id, other) is None
        ]
        type_rows.append({
            "type": type_id, "enumName": name, "vectorFieldIndex": field_index,
            "recordCount": sum(len(grid["indexes"].get(type_id, [])) for grid in grids),
            "populatedGrids": sum(bool(grid["indexes"].get(type_id)) for grid in grids),
            "corpusOnlyRivals": rivals,
        })
    return {
        "format": "endfield.dynamic-data-index-native-audit.v1",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {
            "reportSha256": provenance["outerReportSha256"],
            "ledgerSha256": provenance["ledgerSha256"],
            "ledgerFileRowCount": provenance["ledgerFileRowCount"],
        },
        "corpus": dict(totals),
        "types": type_rows,
        "files": file_rows,
        "evidenceBoundary": "Selected native builder/getters and EDynamicSceneData enum name the inline record; all current non-invalid records address a same-named vector element in their containing SingleGrid, and those indexes partition each observed vector per grid. This is a stored reference, not evidence of runtime dereference or activation.",
    }


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    rows = "\n".join(
        f"| {row['type']} | `{row['enumName']}` | {row['vectorFieldIndex']} | "
        f"{row['recordCount']:,} | {row['populatedGrids']:,} | "
        f"{', '.join(r['name'] for r in row['corpusOnlyRivals']) or '-'} |"
        for row in report["types"]
    )
    return "\n".join([
        "# DynamicStreaming DataIndex reference audit", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Authenticated main files: {corpus['files']:,}; grids: {corpus['grids']:,}; valid records: {corpus['validRecords']:,}.",
        f"- Invalid records: {corpus.get('invalidRecords', 0):,}; nonzero record padding: {corpus.get('nonzeroPaddingRecords', 0):,}.",
        "- Every observed Type indexes a same-named vector in the containing grid and partitions that vector exactly.",
        "- Corpus-only rivals show why counts alone cannot identify some vector fields; the selected enum supplies the name.",
        "- This audit does not observe live dereference or activation.",
        "", "## Observed Type values", "",
        "| Type | Enum name | Vector field | Records | Populated grids | Corpus-only rivals |",
        "|---:|---|---:|---:|---:|---|", rows, "",
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
    args = parser.parse_args(argv)
    try:
        layout, main_layout, enum_by_id, digest, main_digest, receipt = validate_native_layout(
            args.gameassembly, args.metadata,
        )
        report = audit_current_main(
            layout, main_layout, enum_by_id, outer_path=args.outer_report,
            ledger_path=args.ledger, cli_path=args.cli, input_root=args.input_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-data-index-native-audit: {error}", file=sys.stderr)
        return 1
    report["contractSha256"] = digest
    report["mainVectorContractSha256"] = main_digest
    report["nativeInputs"] = receipt
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming DataIndex native audit passed: "
        f"files={report['corpus']['files']} grids={report['corpus']['grids']} "
        f"records={report['corpus']['validRecords']} types={len(report['types'])}"
    )
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
