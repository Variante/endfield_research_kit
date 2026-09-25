"""Authenticate SludgeComp.SurfTileIDs and audit current primitive-int ownership.

The selected getter identifies an inline DataGroup. The corpus audit tests its
stored span alongside RootComp and resource visibility spans, without assigning
runtime behavior to the selected tile IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_resource_comp_native import (
    _checked_span,
    _group,
    validate_native_layout as validate_resource_layout,
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
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_sludge_surf_tile_native.json"
SCHEMA = "endfield.dynamic-sludge-surf-tile-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_sludge_surf_tile_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_sludge_surf_tile_native_latest.md"


class DynamicSludgeSurfTileError(ValueError):
    """The selected getter, authenticated corpus, or stored spans differ."""


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[int, str], dict[str, Any]
]:
    """Authenticate the SurfTileIDs getter and its shared record/vector types."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_sludge_surf_tile", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicSludgeSurfTileError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"]:
        raise DynamicSludgeSurfTileError("installed_native_inputs:mismatched:UnityPlayer.dll missing or hash differs")
    resource, root, main, enum_by_id, resource_provenance, _ = validate_resource_layout(gameassembly, metadata)
    if resource_provenance["nativeInputs"] != inputs:
        raise DynamicSludgeSurfTileError("SurfTileIDs and resource contracts select different native inputs")
    layout = contract["layout"]
    vectors = {row["name"]: row for row in main["vectors"]}
    if (layout["gridType"] != main["gridType"] or layout["recordVector"] not in vectors
            or layout["targetVector"] not in vectors or layout["groupType"] != root["groupType"]
            or int(layout["groupWidth"]) != int(root["groupWidth"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs shared native types differ")
    record = vectors[layout["recordVector"]]
    target = vectors[layout["targetVector"]]
    name_to_id = {name: number for number, name in enum_by_id.items()}
    if (record["elementType"] != layout["recordType"]
            or int(record["fieldIndex"]) != int(layout["recordFieldIndex"])
            or int(record["elementWidth"]) != int(layout["recordWidth"])
            or target["elementType"] != "System.Int32"
            or layout["targetDataType"] not in name_to_id
            or int(root["visibleDesc"]["dataTypeValue"]) != name_to_id[layout["targetDataType"]]
            or int(target["fieldIndex"]) != int(root["visibleDesc"]["vectorFieldIndex"])
            or int(layout["groupOffset"]) < 0
            or int(layout["groupOffset"]) + int(layout["groupWidth"]) > int(layout["recordWidth"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs record or primitive-vector binding differs")
    getter = contract["getter"]
    if (getter["type"] != layout["recordType"] or getter["method"] != "get_" + layout["groupField"]
            or getter["parameters"] or getter["returnType"] != layout["groupType"]):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter declaration differs")
    image = open_native_image(gameassembly, metadata)
    image.validate_method_row(
        [int(getter["index"]), getter["type"], getter["method"], int(getter["rva"])],
        label="dynamic_sludge_surf_tile",
    )
    method = image.metadata.methods[int(getter["index"])]
    actual_parameters = [image.metadata.metadata_type_name(row.type_index)
                         for row in image.metadata.parameters_for(method)]
    if (actual_parameters != getter["parameters"]
            or image.metadata.metadata_type_name(method.return_type) != getter["returnType"]):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter signature differs")
    length = int(getter["windowLength"])
    if not 0 < length <= 4096:
        raise DynamicSludgeSurfTileError("SurfTileIDs getter window length invalid")
    body = image.pe.bytes_at_va(image.pe.image_base + int(getter["rva"]), length)
    if hashlib.sha256(body).hexdigest().upper() != getter["windowSha256"]:
        raise DynamicSludgeSurfTileError("SurfTileIDs getter code window differs")
    instruction = bytes.fromhex(getter["offsetInstructionHex"])
    if (int(getter["offsetInstructionRva"]) < int(getter["rva"])
            or int(getter["offsetInstructionRva"]) + len(instruction) > int(getter["rva"]) + length
            or image.pe.bytes_at_va(image.pe.image_base + int(getter["offsetInstructionRva"]),
                                    len(instruction)) != instruction
            or instruction[:2] != b"\x81\xc2"
            or struct.unpack_from("<I", instruction, 2)[0] != int(layout["groupOffset"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter DataGroup offset differs")
    provenance = {
        "contractSha256": digest,
        "resourceContractSha256": resource_provenance["contractSha256"],
        "rootContractSha256": resource_provenance["rootContractSha256"],
        "nativeInputs": inputs,
    }
    return layout, resource, root, main, enum_by_id, provenance


def _checked_ownership(spans: list[tuple[int, int, str]], count: int, label: str) -> tuple[int, int]:
    """Return visible and SurfTileIDs counts, rejecting any double ownership."""
    cursor = 0
    visible = surf = 0
    for start, end, owner in sorted(spans):
        if not 0 <= start < end <= count:
            raise DynamicSludgeSurfTileError(f"{label}: invalid {owner} PrimitiveIntList span {start}:{end}/{count}")
        if start < cursor:
            raise DynamicSludgeSurfTileError(f"{label}: {owner} PrimitiveIntList span overlaps at {start}:{end}")
        cursor = end
        if owner == "SurfTileIDs":
            surf += end - start
        else:
            visible += end - start
    return visible, surf


def audit_current_main(
    layout: dict[str, Any], resource: dict[str, Any], root_layout: dict[str, Any],
    main_layout: dict[str, Any], enum_by_id: dict[int, str], *,
    outer_path: Path, ledger_path: Path, cli_path: Path, input_root: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Check all main files and partition each grid's primitive-int vector."""
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in main_layout["vectors"]}
    vectors = {row["name"]: row for row in main_layout["vectors"]}
    primitive_field = int(vectors[layout["targetVector"]]["fieldIndex"])
    resource_field = int(resource["resourceGroup"]["gridVectorFieldIndex"])
    root_field = int(root_layout["rootCompFieldIndex"])
    sludge_field = int(layout["recordFieldIndex"])
    root_visible_offset = int(root_layout["rootCompVisibleDescOffset"])
    resource_visible_offset = next(int(row["offset"]) for row in resource["resourceGroup"]["fields"]
                                   if row["name"] == "VisibleDesc")
    visible_offsets = (int(root_layout["visibleDesc"]["visibleStateGroupOffset"]),
                       int(root_layout["visibleDesc"]["visibleAreaGroupOffset"]))
    primitive_type = {name: number for number, name in enum_by_id.items()}[layout["targetDataType"]]
    totals: Counter[str] = Counter()
    surf_samples: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen_paths:
            raise DynamicSludgeSurfTileError(f"duplicate current main path: {path}")
        seen_paths.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        if (len(data) != source["declaredBytes"]
                or hashlib.md5(data).hexdigest().upper() != source["fileDataMd5"]):
            raise DynamicSludgeSurfTileError(f"{path}: dump length/MD5 differs from authenticated VFS row")
        parse_dynamic_file("main", data, main_vector_widths=widths)
        root = _root_layout(data)
        grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
        totals.update(files=1, grids=grid_count)
        for ordinal in range(grid_count):
            slot = grid_body + ordinal * 4
            table = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
            uid_address = _field_span(data, table, 0, 4)
            if uid_address is None:
                raise DynamicSludgeSurfTileError(f"{path}: grid[{ordinal}] lacks UniqueId")
            uid = struct.unpack_from("<I", data, uid_address)[0]
            primitive_body, primitive_count, _ = _bounded_vector(data, table, primitive_field, 4)
            totals["primitiveInts"] += primitive_count
            spans: list[tuple[int, int, str]] = []
            for field, width, desc_offset, owner in (
                (root_field, int(root_layout["rootCompWidth"]), root_visible_offset, "RootComp visibility"),
                (resource_field, int(resource["resourceGroup"]["width"]),
                 resource_visible_offset, "ResourceGroup visibility"),
            ):
                body, count, _ = _bounded_vector(data, table, field, width)
                for index in range(count):
                    for group_offset in visible_offsets:
                        group = _group(data, body + index * width + desc_offset + group_offset)
                        span = _checked_span(
                            group, label=f"{path}: grid[{ordinal}] {owner}[{index}]",
                            expected_type=primitive_type, expected_grid=uid, target_count=primitive_count,
                        )
                        if span is not None:
                            spans.append((*span, owner))
            sludge_body, sludge_count, _ = _bounded_vector(data, table, sludge_field, int(layout["recordWidth"]))
            totals["sludgeRecords"] += sludge_count
            for index in range(sludge_count):
                group = _group(data, sludge_body + index * int(layout["recordWidth"]) + int(layout["groupOffset"]))
                span = _checked_span(
                    group, label=f"{path}: grid[{ordinal}] SludgeComp[{index}].SurfTileIDs",
                    expected_type=primitive_type, expected_grid=uid, target_count=primitive_count,
                )
                if span is None:
                    totals["invalidSurfTileGroups"] += 1
                    continue
                spans.append((*span, "SurfTileIDs"))
                totals["validSurfTileGroups"] += 1
                for position in range(span[0], span[1]):
                    value = struct.unpack_from("<i", data, primitive_body + position * 4)[0]
                    totals["nonzeroSurfTileIds"] += value != 0
                    if len(surf_samples) < 12:
                        surf_samples.append({"source": path, "gridUniqueId": uid,
                                             "index": position, "value": value})
            visible, surf = _checked_ownership(spans, primitive_count, f"{path}: grid[{ordinal}] UniqueId={uid}")
            totals["visiblePrimitiveInts"] += visible
            totals["surfTileIds"] += surf
            totals["unownedPrimitiveInts"] += primitive_count - visible - surf
            totals["gridsWithSurfTileIds"] += surf > 0
    return {
        "format": "endfield.dynamic-sludge-surf-tile-native-audit.v1",
        "status": "validated",
        "primitiveOwnershipComplete": totals["unownedPrimitiveInts"] == 0,
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {"reportSha256": provenance["outerReportSha256"],
                  "ledgerSha256": provenance["ledgerSha256"],
                  "ledgerFileRowCount": provenance["ledgerFileRowCount"]},
        "corpus": dict(totals),
        "surfTileIdSamples": surf_samples,
        "evidenceBoundary": {
            "direct": "The selected native getter returns SludgeComp.SurfTileIDs as an inline DataGroup at its checked offset.",
            "structuralOnly": "Current authenticated main files have disjoint RootComp visibility, ResourceGroup visibility and SurfTileIDs spans into each grid's PrimitiveIntList. The corpus counts show whether these spans tile each vector.",
            "unresolved": "The runtime consumer and behavior of SurfTileIDs, and activation of any stored grid, remain open.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    c = report["corpus"]
    return "\n".join([
        "# DynamicStreaming Sludge SurfTileIDs audit", "",
        f"- Status: {report['status']}; authenticated main files: {c['files']:,}; grids: {c['grids']:,}.",
        f"- Selected SurfTileIDs getter offset: {report['layout']['groupOffset']} bytes in SludgeComp.",
        f"- SludgeComp records: {c['sludgeRecords']:,}; valid SurfTileIDs groups: {c['validSurfTileGroups']:,}; invalid groups: {c.get('invalidSurfTileGroups', 0):,}.",
        f"- PrimitiveIntList entries: {c['primitiveInts']:,}; visible-group entries: {c['visiblePrimitiveInts']:,}; SurfTileIDs entries: {c['surfTileIds']:,}; still unowned: {c['unownedPrimitiveInts']:,}.",
        f"- Stored primitive ownership complete: {str(report['primitiveOwnershipComplete']).lower()}.",
        "- These are stored DataGroup spans. Runtime tile use and grid activation remain open.", "",
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
        layout, resource, root, main_layout, enum_by_id, native = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_main(
            layout, resource, root, main_layout, enum_by_id,
            outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-sludge-surf-tile-native-audit: {error}", file=sys.stderr)
        return 1
    report.update(native)
    report["layout"] = {"groupField": layout["groupField"], "groupOffset": layout["groupOffset"],
                        "recordVector": layout["recordVector"], "targetVector": layout["targetVector"]}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"DynamicStreaming SurfTileIDs audit passed: files={report['corpus']['files']} "
          f"SurfTileIDs={report['corpus']['surfTileIds']} "
          f"unowned={report['corpus']['unownedPrimitiveInts']}")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
