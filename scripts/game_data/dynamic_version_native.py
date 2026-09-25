"""Authenticate and exact-frame current DynamicStreaming fb_version files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import parse_dynamic_file
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_version_native.json"
SCHEMA = "endfield.dynamic-version-native-contract.v1"
VERSION_NAME_RE = re.compile(r"(?:^|/)fb_version\.bytes$", re.IGNORECASE)
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_version_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_version_native_latest.md"


class DynamicVersionNativeError(ValueError):
    """The selected version schema, native build, or current corpus differs."""


def _vtable_slot(raw: bytes) -> int:
    if len(raw) != 5 or raw[0] != 0xBA:
        raise DynamicVersionNativeError("selected version vtable-slot instruction differs")
    return struct.unpack_from("<I", raw, 1)[0]


def _check_layout_operands(checks: dict[str, bytes], layout: dict[str, Any]) -> None:
    """Relate checked native operands to the reviewed field layout."""
    expected_roles = {
        "entriesSlot", "entriesStride", "lengthSlot", "majorSlot", "minorSlot",
        "vectorAlignment", "vectorWidth", "idOffset", "versionOffset",
        "entryBuilderWidth", "rootFieldCount",
    }
    if set(checks) != expected_roles:
        raise DynamicVersionNativeError("selected version instruction roles differ")
    for role, field in (("entriesSlot", "entriesFieldIndex"), ("lengthSlot", "entriesFieldIndex"),
                        ("majorSlot", "majorFieldIndex"), ("minorSlot", "minorFieldIndex")):
        if _vtable_slot(checks[role]) != 4 + 2 * int(layout[field]):
            raise DynamicVersionNativeError(f"{role}: selected vtable slot differs")
    stride = checks["entriesStride"]
    if stride[:2] != b"\xc1\xe6" or len(stride) != 3 or 1 << stride[2] != int(layout["entryWidth"]):
        raise DynamicVersionNativeError("Entries indexed stride differs")
    alignment = checks["vectorAlignment"]
    width = checks["vectorWidth"]
    if (len(alignment) != 6 or alignment[:2] != b"\x41\xb9"
            or len(width) != 4 or width[:3] != b"\x41\x8d\x51"
            or struct.unpack_from("<I", alignment, 2)[0] != int(layout["entryAlignment"])
            or struct.unpack_from("<I", alignment, 2)[0] + width[3] != int(layout["entryWidth"])):
        raise DynamicVersionNativeError("Entries vector builder width/alignment differs")
    builder = checks["entryBuilderWidth"]
    if (len(builder) != 8 or builder[:3] != b"\x41\x8d\x51"
            or builder[4:7] != b"\x45\x8d\x41"
            or builder[3] != int(layout["entryAlignment"])
            or builder[7] != int(layout["entryWidth"])):
        raise DynamicVersionNativeError("VersionEntry builder width/alignment differs")
    if checks["idOffset"] != b"\x8b\xd3" or int(layout["entryIdOffset"]) != 0:
        raise DynamicVersionNativeError("VersionEntry.Id selected offset differs")
    version = checks["versionOffset"]
    if len(version) != 3 or version[:2] != b"\x8d\x53" or version[2] != int(layout["entryVersionOffset"]):
        raise DynamicVersionNativeError("VersionEntry.Version selected offset differs")
    root_fields = checks["rootFieldCount"]
    if (len(root_fields) != 7 or root_fields[:6] != b"\x48\x8b\xcf\x41\x8d\x50"
            or root_fields[6] != int(layout["rootFieldCount"])):
        raise DynamicVersionNativeError("VersionData builder field count differs")
    if (int(layout["entryVersionOffset"]) + 4 + int(layout["entryPaddingWidth"])
            != int(layout["entryWidth"])):
        raise DynamicVersionNativeError("VersionEntry declared tail differs")


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Authenticate selected generated version accessors and their operands."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_version", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVersionNativeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"]:
        raise DynamicVersionNativeError("installed_native_inputs:mismatched:UnityPlayer.dll missing or hash differs")
    image = open_native_image(gameassembly, metadata)
    windows: list[tuple[int, int]] = []
    methods: dict[int, dict[str, Any]] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicVersionNativeError(f"duplicate selected version method {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])],
                                  label="dynamic_version")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(item.type_index)
                      for item in image.metadata.parameters_for(method)]
        if (parameters != row["parameters"]
                or image.metadata.metadata_type_name(method.return_type) != row["returnType"]):
            raise DynamicVersionNativeError(f"selected version method signature differs: {index}")
        start, length = int(row["rva"]), int(row["windowLength"])
        if not 0 < length <= 4096:
            raise DynamicVersionNativeError(f"selected version method window length invalid: {index}")
        body = image.pe.bytes_at_va(image.pe.image_base + start, length)
        if hashlib.sha256(body).hexdigest().upper() != row["windowSha256"]:
            raise DynamicVersionNativeError(f"selected version method code differs: {index}")
        windows.append((start, start + length))
        methods[index] = row
    expected_methods = {
        "Entries", "get_EntriesLength", "get_Major", "get_Minor", "StartEntriesVector",
        "get_Id", "get_Version", "CreateFBDynamicSceneVersionEntry",
        "CreateFBDynamicSceneVersionData",
    }
    if {row["method"] for row in methods.values()} != expected_methods:
        raise DynamicVersionNativeError("selected version method set differs")
    layout = contract["layout"]
    for name in ("Entries", "get_EntriesLength", "get_Major", "get_Minor",
                 "StartEntriesVector", "CreateFBDynamicSceneVersionData"):
        if next(row for row in methods.values() if row["method"] == name)["type"] != layout["rootType"]:
            raise DynamicVersionNativeError(f"{name}: root method owner differs")
    for name in ("get_Id", "get_Version", "CreateFBDynamicSceneVersionEntry"):
        if next(row for row in methods.values() if row["method"] == name)["type"] != layout["entryType"]:
            raise DynamicVersionNativeError(f"{name}: entry method owner differs")
    for row in contract["fragments"]:
        owner = methods[int(row["methodIndex"])]
        start, length = int(row["startRva"]), int(row["length"])
        if owner["method"] not in ("get_Major", "get_Minor") or start != int(owner["rva"]) + int(owner["windowLength"]):
            raise DynamicVersionNativeError("selected version scalar fragment is not contiguous with getter")
        body = image.pe.bytes_at_va(image.pe.image_base + start, length)
        if hashlib.sha256(body).hexdigest().upper() != row["sha256"]:
            raise DynamicVersionNativeError(f"selected version scalar fragment differs: {owner['method']}")
        windows.append((start, start + length))
    if {int(row["methodIndex"]) for row in contract["fragments"]} != {
        int(row["index"]) for row in methods.values() if row["method"] in ("get_Major", "get_Minor")
    }:
        raise DynamicVersionNativeError("selected version scalar fragment set differs")
    checks: dict[str, bytes] = {}
    for row in contract["instructionChecks"]:
        role, rva = row["role"], int(row["rva"])
        if role in checks:
            raise DynamicVersionNativeError(f"duplicate selected version instruction role: {role}")
        raw = bytes.fromhex(row["hex"])
        if not raw or not any(start <= rva and rva + len(raw) <= end for start, end in windows):
            raise DynamicVersionNativeError(f"selected version instruction lies outside checked code: {role}")
        if image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw:
            raise DynamicVersionNativeError(f"selected version instruction differs: {role}")
        checks[role] = raw
    _check_layout_operands(checks, layout)
    return layout, {"contractSha256": digest, "nativeInputs": inputs}


def audit_current_versions(
    layout: dict[str, Any], *, outer_path: Path, ledger_path: Path, cli_path: Path,
    input_root: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Rejoin every current version dump and decode the selected fields."""
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=VERSION_NAME_RE, selection_label="fb_version.bytes",
    )
    totals: Counter[str] = Counter()
    major_minor: Counter[tuple[int, int]] = Counter()
    entry_versions: Counter[int] = Counter()
    populated: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen_paths:
            raise DynamicVersionNativeError(f"duplicate current version path: {path}")
        seen_paths.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        if (len(data) != source["declaredBytes"]
                or hashlib.md5(data).hexdigest().upper() != source["fileDataMd5"]):
            raise DynamicVersionNativeError(f"{path}: dump length/MD5 differs from authenticated VFS row")
        parsed = parse_dynamic_file("version", data, version_entry_width=int(layout["entryWidth"]))
        root = parsed["root"]
        if (root["fieldCount"] != int(layout["rootFieldCount"])
                or tuple(root["presentFields"]) != (int(layout["entriesFieldIndex"]),
                                                     int(layout["majorFieldIndex"]),
                                                     int(layout["minorFieldIndex"]))):
            raise DynamicVersionNativeError(f"{path}: selected VersionData root shape differs")
        major, minor = (struct.unpack("<i", struct.pack("<I", value))[0]
                        for value in parsed["ScalarFieldValues"])
        major_minor[(major, minor)] += 1
        vector = parsed["VectorField0"]
        count, body = int(vector["count"]), int(vector["bodyOffset"])
        totals["emptyEntryVectors" if count == 0 else "populatedEntryVectors"] += 1
        ids: set[int] = set()
        samples: list[dict[str, int]] = []
        for index in range(count):
            start = body + index * int(layout["entryWidth"])
            entry_id = struct.unpack_from("<Q", data, start + int(layout["entryIdOffset"]))[0]
            version = struct.unpack_from("<i", data, start + int(layout["entryVersionOffset"]))[0]
            padding_start = start + int(layout["entryVersionOffset"]) + 4
            totals["nonzeroEntryPadding"] += any(data[padding_start:padding_start + int(layout["entryPaddingWidth"])])
            totals["duplicateIdsWithinFile"] += entry_id in ids
            ids.add(entry_id)
            entry_versions[version] += 1
            if len(samples) < 8:
                samples.append({"id": entry_id, "version": version})
        totals.update(files=1, bytes=len(data), entries=count)
        if count:
            populated.append({"source": path, "entries": count, "major": major,
                              "minor": minor, "sample": samples})
    return {
        "format": "endfield.dynamic-version-native-audit.v1",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {"reportSha256": provenance["outerReportSha256"],
                  "ledgerSha256": provenance["ledgerSha256"],
                  "ledgerFileRowCount": provenance["ledgerFileRowCount"]},
        "corpus": {**dict(totals), "nullEntryVectors": 0,
                   "emptyEntryVectors": totals["emptyEntryVectors"],
                   "populatedEntryVectors": totals["populatedEntryVectors"],
                   "nonzeroEntryPadding": totals["nonzeroEntryPadding"],
                   "duplicateIdsWithinFile": totals["duplicateIdsWithinFile"]},
        "majorMinor": [{"major": major, "minor": minor, "files": count}
                       for (major, minor), count in sorted(major_minor.items())],
        "entryVersions": [{"version": version, "entries": count}
                          for version, count in sorted(entry_versions.items())],
        "populatedFiles": populated,
        "evidenceBoundary": {
            "exact": "Selected native accessors establish the named fields and entry width. Current dump size and MD5 rejoin the authenticated VFS ledger; the entries vector count word starts immediately after the root and its 16-byte body closes at EOF.",
            "unresolved": "The Id's domain, version-ban decision, live file selection, and whether any entry affects a running scene remain open.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    c = report["corpus"]
    return "\n".join([
        "# DynamicStreaming fb_version native audit", "",
        f"- Status: {report['status']}; authenticated version files: {c['files']:,}; entries: {c['entries']:,}.",
        f"- Entry vectors: {c['populatedEntryVectors']:,} populated, {c['emptyEntryVectors']:,} empty, {c['nullEntryVectors']:,} null; entry padding with nonzero bytes: {c['nonzeroEntryPadding']:,}.",
        "- Selected root fields are Entries, Major and Minor; each entry carries UInt64 Id and Int32 Version in a 16-byte struct.",
        "- The vector body closes at EOF in every current file. Runtime version-ban decisions remain open.", "",
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
        layout, native = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_versions(
            layout, outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-version-native-audit: {error}", file=sys.stderr)
        return 1
    report.update(native)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"DynamicStreaming version audit passed: files={report['corpus']['files']} entries={report['corpus']['entries']}")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
