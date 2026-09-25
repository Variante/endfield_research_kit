"""Audit current DynamicStreaming main grids with selected-build vector widths.

The generic reader bounds grid vectors with a one-byte minimum. This module
uses reviewed generated FlatBuffer accessors and vector builders to close the
element extents, then rejoins each dumped file to the current VFS ledger.
It does not decode nested struct fields or claim live grid activation.
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
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    MAIN_NAME_RE,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import parse_dynamic_file
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_main_vector_native.json"
SCHEMA = "endfield.dynamic-main-vector-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_main_vector_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_main_vector_native_latest.md"


class DynamicMainNativeError(ValueError):
    """The native contract, current corpus, or selected vector framing differs."""


def _builder_vector_shape(raw: bytes, *, name: str) -> tuple[int, int]:
    """Read the selected generated StartVector call's size and alignment."""
    prefix = b"\x48\x83\x64\x24\x20\x00"  # clear the outgoing stack argument
    start = raw.find(prefix)
    if start < 0 or raw.find(prefix, start + 1) >= 0:
        raise DynamicMainNativeError(f"{name}: generated vector builder prefix differs")
    code = raw[start + len(prefix):]
    if code.startswith(b"\xBA") and code[5:15] == b"\x44\x8B\xCA\x44\x8B\xC7\x48\x8B\xCB\xE8":
        width = struct.unpack_from("<I", code, 1)[0]
        return width, width
    if code.startswith(b"\x41\xB9") and code[6:9] == b"\x44\x8B\xC7":
        alignment = struct.unpack_from("<I", code, 2)[0]
        if code[9:12] == b"\x48\x8B\xCB" and code[12:15] == b"\x41\x8D\x51" and code[16:17] == b"\xE8":
            return alignment + struct.unpack_from("<b", code, 15)[0], alignment
        # Larger widths load EDX before moving the builder pointer into RCX.
        if code[9:10] == b"\xBA" and code[14:18] == b"\x48\x8B\xCB\xE8":
            return struct.unpack_from("<I", code, 10)[0], alignment
    raise DynamicMainNativeError(f"{name}: unreviewed generated vector builder shape")


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[dict[str, Any], str, dict[str, str]]:
    """Authenticate the selected generated accessors and vector builders."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_main", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicMainNativeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicMainNativeError(f"installed_native_inputs:missing:{unity}")
    unity_sha = sha256_file(unity).upper()
    if unity_sha != inputs["unityPlayerSha256"].upper():
        raise DynamicMainNativeError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")

    image = open_native_image(Path(gameassembly), Path(metadata))
    methods: dict[int, dict[str, Any]] = {}
    method_bytes: dict[int, bytes] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicMainNativeError(f"duplicate method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_main")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        return_type = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or return_type != row["returnType"]:
            raise DynamicMainNativeError(f"method signature differs: {row['type']}.{row['method']}")
        raw = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), int(row["bodyExtent"]))
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"].upper():
            raise DynamicMainNativeError(f"method code window differs: {row['type']}.{row['method']}")
        methods[index] = row
        method_bytes[index] = raw

    layout = contract["layout"]
    vectors = layout["vectors"]
    if len(vectors) != 59 or {row["fieldIndex"] for row in vectors} != set(range(1, 60)):
        raise DynamicMainNativeError("SingleGrid vector fields must cover 1..59 exactly")
    used: set[int] = set()
    for row in vectors:
        name = row["name"]
        element_type = row["elementType"]
        width = int(row["elementWidth"])
        alignment = int(row["elementAlignment"])
        if width <= 0 or alignment <= 0 or alignment & (alignment - 1) or width % alignment:
            raise DynamicMainNativeError(f"invalid element width/alignment for {name}")
        if int(row["vtableSlot"]) != 4 + 2 * int(row["fieldIndex"]):
            raise DynamicMainNativeError(f"invalid vector vtable slot for {name}")
        getter = methods[row["accessorMethodIndex"]]
        builder = methods[row["startVectorMethodIndex"]]
        if (getter["type"], getter["method"], getter["parameters"], getter["returnType"]) != (
            layout["gridType"], name, ["System.Int32"], element_type
        ):
            raise DynamicMainNativeError(f"indexed accessor binding differs: {name}")
        if (builder["type"], builder["method"], builder["parameters"], builder["returnType"]) != (
            layout["gridType"], "Start" + name + "Vector",
            ["Google.FlatBuffers.FlatBufferBuilder", "System.Int32"], "System.Void"
        ):
            raise DynamicMainNativeError(f"vector builder binding differs: {name}")
        if element_type == "System.Int32":
            kind = "scalar32"
        else:
            matches = [t for t in image.metadata.types if image.metadata.type_full_name(t) == element_type]
            if len(matches) != 1:
                raise DynamicMainNativeError(f"element type differs: {name}: {element_type}")
            element = matches[0]
            pointer = [
                method for method in image.metadata.methods[
                    element.method_start:element.method_start + element.method_count
                ] if image.metadata.string(method.name_index) == "GetPointer"
            ]
            if len(pointer) != 1:
                raise DynamicMainNativeError(f"element pointer accessor differs: {name}")
            kind = image.metadata.metadata_type_name(pointer[0].return_type).rsplit(".", 1)[-1].lower()
        if kind != row["elementKind"]:
            raise DynamicMainNativeError(f"element kind differs: {name}: expected={row['elementKind']} actual={kind}")
        builder_width, builder_alignment = _builder_vector_shape(method_bytes[builder["index"]], name=name)
        if (builder_width, builder_alignment) != (width, alignment):
            raise DynamicMainNativeError(
                f"{name}: builder size/alignment differs: expected={width}/{alignment} "
                f"actual={builder_width}/{builder_alignment}"
            )
        slot_witness = b"\xBA" + struct.pack("<I", int(row["vtableSlot"]))
        if method_bytes[getter["index"]][:64].count(slot_witness) != 1:
            raise DynamicMainNativeError(f"{name}: indexed accessor vtable-slot witness differs")
        used.update((getter["index"], builder["index"]))
    for owner, entries, required in (
        (layout["rootType"], layout["rootAccessors"], set(range(5))),
        (layout["gridType"], layout["gridScalars"], {0, 60}),
    ):
        if {entry["fieldIndex"] for entry in entries} != required:
            raise DynamicMainNativeError(f"scalar/root accessor fields differ: {owner}")
        for entry in entries:
            method = methods[entry["methodIndex"]]
            if method["type"] != owner:
                raise DynamicMainNativeError(f"scalar/root accessor owner differs: {owner}")
            used.add(method["index"])
    if used != set(methods):
        raise DynamicMainNativeError("unused method in reviewed native contract")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": unity_sha,
    }
    return layout, digest, receipt


def _checked_dump_path(input_root: Path, virtual_path: str) -> Path:
    parts = virtual_path.replace("\\", "/").split("/")
    if not parts or any(part in ("", ".", "..") or ":" in part for part in parts):
        raise DynamicMainNativeError(f"invalid current VFS virtual path: {virtual_path!r}")
    return Path(input_root, *parts)


def audit_current_main(
    layout: dict[str, Any], *, outer_path: Path, ledger_path: Path,
    cli_path: Path, input_root: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in layout["vectors"]}
    field_totals: dict[int, Counter[str]] = {index: Counter() for index in widths}
    file_rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    mask_nonempty_matches: Counter[str] = Counter()
    mask_present_matches: Counter[str] = Counter()
    mask_checked = 0
    seen: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen:
            raise DynamicMainNativeError(f"duplicate current main path: {path}")
        seen.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["declaredBytes"] or actual_md5 != source["fileDataMd5"]:
            raise DynamicMainNativeError(
                f"{path}: dumped bytes differ from authenticated VFS row "
                f"length={len(data)}/{source['declaredBytes']} md5={actual_md5}/{source['fileDataMd5']}"
            )
        try:
            parsed = parse_dynamic_file("main", data, main_vector_widths=widths)
        except (ValueError, OverflowError) as exc:
            raise DynamicMainNativeError(f"{path}: selected vector framing failed: {exc}") from exc
        frame = parsed["ProvidedWidthGridVectorFraming"]
        mask = frame["dataMaskCandidate"]
        mask_checked += mask["checkedGrids"]
        mask_nonempty_matches.update(mask["nonemptyMatchCounts"])
        mask_present_matches.update(mask["presentMatchCounts"])
        for row in frame["fieldCounts"]:
            field_totals[row["fieldIndex"]].update({
                "vectorCount": row["vectorCount"],
                "nonemptyVectorCount": row["nonemptyVectorCount"],
                "elementCount": row["elementCount"],
            })
        totals.update({
            "files": 1,
            "bytes": len(data),
            "grids": parsed["GridsLength"],
            "strings": parsed["TotalStrLength"],
            "vectors": frame["countWordAndBodySpanCount"],
            "nonemptyVectors": frame["nonemptyVectorCount"],
            "vectorBodyBytes": frame["bodyBytes"],
        })
        file_rows.append({
            "path": path,
            "sourceBytes": len(data),
            "fileDataMd5": actual_md5,
            "grids": parsed["GridsLength"],
            "totalStrings": parsed["TotalStrLength"],
            "vectorCountWordAndBodySpans": frame["countWordAndBodySpanCount"],
            "nonemptyVectors": frame["nonemptyVectorCount"],
            "vectorBodyBytes": frame["bodyBytes"],
            "status": frame["status"],
        })
    if len(file_rows) != len(current_files):
        raise DynamicMainNativeError("main file census differs from current VFS ledger")
    field_rows = [
        {
            **row,
            **field_totals[row["fieldIndex"]],
        }
        for row in layout["vectors"]
    ]
    all_mask_matches = list(mask_nonempty_matches.values()) + list(mask_present_matches.values())
    mask_status = (
        "rejected" if mask_checked == totals["grids"] and mask_checked > 0
        and all(count < mask_checked for count in all_mask_matches)
        else "inconclusive"
    )
    return {
        "format": "endfield.dynamic-main-vector-native-audit.v1",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {
            "reportSha256": provenance["outerReportSha256"],
            "ledgerSha256": provenance["ledgerSha256"],
            "ledgerFileRowCount": provenance["ledgerFileRowCount"],
            "sourceFingerprintCount": len(provenance["sourceFingerprints"]),
            "gameBuildFingerprintCount": len(provenance["gameBuildFingerprints"]),
        },
        "corpus": dict(totals),
        "oldFourByteAssumption": {
            "undercountedNonemptyVectors": sum(row["nonemptyVectorCount"] for row in field_rows if row["elementWidth"] > 4),
            "overcountedNonemptyVectors": sum(row["nonemptyVectorCount"] for row in field_rows if row["elementWidth"] < 4),
        },
        "dataMaskPresenceCandidate": {
            "status": mask_status,
            "checkedGrids": mask_checked,
            "candidate": "sum(1 << (fieldIndex - base)) over nonempty or present vector fields at or after base",
            "nonemptyMatchCounts": dict(mask_nonempty_matches),
            "presentMatchCounts": dict(mask_present_matches),
        },
        "fields": field_rows,
        "files": file_rows,
        "evidenceBoundary": "Selected-build generated builders and indexers close each grid vector body. This does not close all FlatBuffer object/string ranges or decode nested struct fields, DataMask, or live grid behavior.",
    }


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    fields = report["fields"]
    rows = "\n".join(
        f"| {row['fieldIndex']} | `{row['name']}` | {row['elementWidth']} | {row['elementAlignment']} | "
        f"{row['nonemptyVectorCount']} | {row['elementCount']} |"
        for row in fields
    )
    return "\n".join([
        "# DynamicStreaming main vector audit", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Authenticated main files: {corpus['files']:,}; grids: {corpus['grids']:,}; vector spans: {corpus['vectors']:,}; nonempty: {corpus['nonemptyVectors']:,}.",
        f"- Bounded vector body bytes: {corpus['vectorBodyBytes']:,}; the selected spans do not overlap.",
        f"- Old four-byte assumption undercounted {report['oldFourByteAssumption']['undercountedNonemptyVectors']:,} nonempty vectors and overcounted {report['oldFourByteAssumption']['overcountedNonemptyVectors']:,} byte vectors.",
        f"- Simple DataMask vector-presence candidate: `{report['dataMaskPresenceCandidate']['status']}` across {report['dataMaskPresenceCandidate']['checkedGrids']:,} grids.",
        "- Nested struct fields, table targets, DataMask, and whole-file closure remain separate.",
        "", "## Selected-build vector fields", "",
        "| Field | Accessor | Width | Alignment | Nonempty vectors | Elements |",
        "|---:|---|---:|---:|---:|---:|", rows, "",
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
        layout, contract_sha, native = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_main(
            layout, outer_path=args.outer_report, ledger_path=args.ledger,
            cli_path=args.cli, input_root=args.input_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-main-native-audit: {error}", file=sys.stderr)
        return 1
    report["contractSha256"] = contract_sha
    report["nativeInputs"] = native
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming main native audit passed: "
        f"files={report['corpus']['files']} grids={report['corpus']['grids']} "
        f"nonemptyVectors={report['corpus']['nonemptyVectors']}"
    )
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
