#!/usr/bin/env python3
"""Decode ExtendData/FacBoneTRS.bin and bound its Story relevance.

The current file is read by ``Beyond.Gameplay.Factory.FacBoneTRSBinary``.
Its lookup path is:

``guid -> unit entry -> boneNameHash -> frame -> 64-byte matrix``

This offline audit validates every bucket, unit, bone, and matrix range and
checks the numeric payload for exact encoded forms of the unresolved Story
roots. It is not part of ``export.bat``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file,
)

DEFAULT_FACBONE_BIN = (
    ROOT
    / "tmp"
    / "story"
    / "facbone_trs"
    / "Data"
    / "ExtendData"
    / "Main"
    / "FacBone"
    / "FacBoneTRS.bin"
)
DEFAULT_VFS_INDEX = (
    ROOT / "tmp" / "story" / "extend_data_inventory" / "current.json"
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery" / "facbone_trs_story_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")
DEFAULT_TARGETS = (
    "cutscene_e11m2_liexi_xs_m_01_last_01",
    "cutscene_e11m2_liexi_xs_m_01_last_02",
    "cutscene_f1m9d3_1",
)

EXPECTED_FACBONE_SHA256 = (
    "d0882963c6a90c9f19ef41eb5f0983b83b925b075e7ea7d1f2ffc9ef2640c5a4"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_EXTEND_DATA_FILES = {
    "Data/ExtendData/Initial/InitStringPathHash.bin": {
        "blockType": "InitialExtendData",
        "length": 305_796,
        "dataMd5": "DE473419868A89EC8E8BD6F72083D2ED",
    },
    "Data/ExtendData/Main/CompressData.bin": {
        "blockType": "ExtendData",
        "length": 789_844,
        "dataMd5": "490BB497AA3517F781228FB81CFB0556",
    },
    "Data/ExtendData/Main/FacBone/FacBoneTRS.bin": {
        "blockType": "ExtendData",
        "length": 17_909_576,
        "dataMd5": "087D084B92C6FBACD786BE77AEE09087",
    },
    "Data/ExtendData/Main/StringPathHash.bin": {
        "blockType": "ExtendData",
        "length": 118_687_426,
        "dataMd5": "D2F5B204E803E9B0C1515FBCE442BC0C",
    },
}

UNIT_BUCKET_SIZE = 8
UNIT_ENTRY_SIZE = 16
BONE_ENTRY_SIZE = 16
MATRIX_SIZE = 64


class AuditError(RuntimeError):
    """Raised when an input cannot support a fail-closed conclusion."""


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()




def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def require_partition(
    ranges: Iterable[tuple[int, int, str]],
    start: int,
    end: int,
    label: str,
) -> None:
    cursor = start
    for range_start, range_end, owner in sorted(ranges):
        if range_start != cursor:
            raise AuditError(
                f"{label}: expected next range at {cursor}, got "
                f"{range_start} ({owner})"
            )
        if range_end <= range_start or range_end > end:
            raise AuditError(
                f"{label}: invalid range {range_start}:{range_end} ({owner})"
            )
        cursor = range_end
    if cursor != end:
        raise AuditError(f"{label}: ranges end at {cursor}, expected {end}")


def decode_facbone_trs(data: bytes) -> dict[str, Any]:
    if len(data) < 12:
        raise AuditError("FacBoneTRS.bin is too short")

    unit_table_bytes = struct.unpack_from("<I", data, 0)[0]
    unit_table_start = 4
    bone_table_start = unit_table_start + unit_table_bytes
    if unit_table_bytes < 4 or bone_table_start > len(data):
        raise AuditError("unit table length exceeds file bounds")

    bucket_count = struct.unpack_from("<I", data, unit_table_start)[0]
    if bucket_count <= 0:
        raise AuditError("unit table has no buckets")
    bucket_table_start = unit_table_start + 4
    bucket_table_end = bucket_table_start + bucket_count * UNIT_BUCKET_SIZE
    if bucket_table_end > bone_table_start:
        raise AuditError("unit bucket table exceeds its section")

    unit_ranges: list[tuple[int, int, str]] = []
    units: list[dict[str, int]] = []
    non_empty_buckets = 0
    for bucket_index in range(bucket_count):
        bucket_offset = bucket_table_start + bucket_index * UNIT_BUCKET_SIZE
        relative_offset, entry_count = struct.unpack_from(
            "<II", data, bucket_offset
        )
        if entry_count == 0:
            if relative_offset != 0:
                raise AuditError(
                    f"empty unit bucket {bucket_index} has offset "
                    f"{relative_offset}"
                )
            continue
        non_empty_buckets += 1
        entry_start = unit_table_start + relative_offset
        entry_end = entry_start + entry_count * UNIT_ENTRY_SIZE
        if entry_start < bucket_table_end or entry_end > bone_table_start:
            raise AuditError(
                f"unit bucket {bucket_index} points outside the unit table"
            )
        unit_ranges.append(
            (entry_start, entry_end, f"unit bucket {bucket_index}")
        )
        for entry_index in range(entry_count):
            offset = entry_start + entry_index * UNIT_ENTRY_SIZE
            hash_key, bone_count, bones_offset = struct.unpack_from(
                "<qII", data, offset
            )
            if hash_key < -(1 << 31) or hash_key >= (1 << 31):
                raise AuditError(
                    f"unit key {hash_key} is not a sign-extended int32 guid"
                )
            if abs(hash_key) % bucket_count != bucket_index:
                raise AuditError(
                    f"unit key {hash_key} is in bucket {bucket_index}, "
                    f"expected {abs(hash_key) % bucket_count}"
                )
            if bone_count <= 0:
                raise AuditError(f"unit key {hash_key} has no bones")
            units.append(
                {
                    "guid": hash_key,
                    "boneCount": bone_count,
                    "bonesOffset": bones_offset,
                    "bucket": bucket_index,
                }
            )

    require_partition(
        unit_ranges,
        bucket_table_end,
        bone_table_start,
        "unit entries",
    )
    if len({unit["guid"] for unit in units}) != len(units):
        raise AuditError("unit guid keys are not unique")

    bone_count = sum(unit["boneCount"] for unit in units)
    bone_table_end = bone_table_start + bone_count * BONE_ENTRY_SIZE
    if bone_table_end > len(data):
        raise AuditError("bone table exceeds file bounds")
    bone_ranges = [
        (
            unit["bonesOffset"],
            unit["bonesOffset"] + unit["boneCount"] * BONE_ENTRY_SIZE,
            f"unit {unit['guid']}",
        )
        for unit in units
    ]
    require_partition(
        bone_ranges,
        bone_table_start,
        bone_table_end,
        "unit bone ranges",
    )

    matrix_ranges: list[tuple[int, int, str]] = []
    frame_counts: list[int] = []
    duplicate_bone_hashes = 0
    matrix_count = 0
    for unit in units:
        seen_bone_hashes: set[int] = set()
        for bone_index in range(unit["boneCount"]):
            offset = unit["bonesOffset"] + bone_index * BONE_ENTRY_SIZE
            bone_hash, frame_count, matrix_offset = struct.unpack_from(
                "<QII", data, offset
            )
            if bone_hash in seen_bone_hashes:
                duplicate_bone_hashes += 1
            seen_bone_hashes.add(bone_hash)
            if frame_count <= 0:
                raise AuditError(
                    f"unit {unit['guid']} bone {bone_hash:#x} has no frames"
                )
            matrix_end = matrix_offset + frame_count * MATRIX_SIZE
            if matrix_offset < bone_table_end or matrix_end > len(data):
                raise AuditError(
                    f"unit {unit['guid']} bone {bone_hash:#x} matrix range "
                    "is outside the file"
                )
            matrix_ranges.append(
                (
                    matrix_offset,
                    matrix_end,
                    f"unit {unit['guid']} bone {bone_hash:#x}",
                )
            )
            frame_counts.append(frame_count)
            matrix_count += frame_count

    require_partition(
        matrix_ranges,
        bone_table_end,
        len(data),
        "matrix ranges",
    )

    non_finite_float_count = 0
    for matrix in struct.iter_unpack(
        "<16f", data[bone_table_end:]
    ):
        non_finite_float_count += sum(
            not math.isfinite(value) for value in matrix
        )
    if non_finite_float_count:
        raise AuditError(
            f"matrix payload has {non_finite_float_count} non-finite floats"
        )

    return {
        "fileBytes": len(data),
        "unitTableBytes": unit_table_bytes,
        "unitTableStart": unit_table_start,
        "bucketCount": bucket_count,
        "nonEmptyBucketCount": non_empty_buckets,
        "unitCount": len(units),
        "unitEntryBytes": UNIT_ENTRY_SIZE,
        "boneTableStart": bone_table_start,
        "boneTableEnd": bone_table_end,
        "boneCount": bone_count,
        "boneEntryBytes": BONE_ENTRY_SIZE,
        "matrixTableStart": bone_table_end,
        "matrixTableEnd": len(data),
        "matrixCount": matrix_count,
        "matrixBytes": MATRIX_SIZE,
        "frameCountMin": min(frame_counts),
        "frameCountMax": max(frame_counts),
        "duplicateBoneHashesWithinUnit": duplicate_bone_hashes,
        "nonFiniteFloatCount": non_finite_float_count,
        "unitGuidMin": min(unit["guid"] for unit in units),
        "unitGuidMax": max(unit["guid"] for unit in units),
    }


def find_exact_encoded_targets(
    data: bytes, targets: Iterable[str]
) -> list[dict[str, Any]]:
    hits = []
    for target in targets:
        for encoding, needle in (
            ("ascii", target.encode("ascii")),
            ("utf16le", target.encode("utf-16le")),
        ):
            offsets = []
            cursor = 0
            while True:
                offset = data.find(needle, cursor)
                if offset < 0:
                    break
                offsets.append(offset)
                cursor = offset + 1
            if offsets:
                hits.append(
                    {
                        "target": target,
                        "encoding": encoding,
                        "offsets": offsets,
                    }
                )
    return hits


def validate_extend_data_inventory(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AuditError(f"ExtendData VFS index does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid ExtendData VFS index: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise AuditError("unsupported ExtendData VFS index shape")

    summary = payload.get("summary") or {}
    if int(summary.get("missingBlockCount", -1)) != 0:
        raise AuditError("ExtendData VFS index has missing blocks")
    if int(summary.get("missingChunkCount", -1)) != 0:
        raise AuditError("ExtendData VFS index has missing chunks")

    actual: dict[str, dict[str, Any]] = {}
    for row in payload["files"]:
        if not isinstance(row, dict):
            raise AuditError("ExtendData VFS index has a non-object file row")
        name = str(row.get("fileName") or "")
        actual[name] = {
            "blockType": str(
                row.get("fileBlockType") or row.get("blockName") or ""
            ),
            "length": int(row.get("length") or 0),
            "dataMd5": str(row.get("fileDataMd5") or "").upper(),
        }
    if set(actual) != set(EXPECTED_EXTEND_DATA_FILES):
        missing = sorted(set(EXPECTED_EXTEND_DATA_FILES) - set(actual))
        extra = sorted(set(actual) - set(EXPECTED_EXTEND_DATA_FILES))
        raise AuditError(
            f"ExtendData inventory drifted; missing={missing}, extra={extra}"
        )
    for name, expected in EXPECTED_EXTEND_DATA_FILES.items():
        if actual[name] != expected:
            raise AuditError(
                f"ExtendData inventory row drifted for {name}: "
                f"{actual[name]!r}"
            )
    return {
        "index": rel_path(path),
        "version": sorted(
            {
                int(block.get("version"))
                for block in payload.get("blocks", [])
                if isinstance(block, dict) and block.get("version") is not None
            }
        ),
        "blockCount": int(summary.get("blockCount") or 0),
        "chunkCount": int(summary.get("chunkCount") or 0),
        "fileCount": len(actual),
        "files": [
            {"name": name, **actual[name]} for name in sorted(actual)
        ],
    }


def validate_native_inputs(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    if not gameassembly.is_file():
        raise AuditError(f"GameAssembly.dll does not exist: {gameassembly}")
    if not metadata.is_file():
        raise AuditError(f"global-metadata.dat does not exist: {metadata}")
    gameassembly_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata)
    if gameassembly_hash != EXPECTED_GAMEASSEMBLY_SHA256:
        raise AuditError(
            "GameAssembly.dll hash drifted; re-audit FacBoneTRSBinary methods"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise AuditError(
            "global-metadata.dat hash drifted; re-audit FacBoneTRSBinary methods"
        )
    return {
        "mappingId": "gameassembly-2026-07-29-facbone-trs-v1",
        "gameAssembly": str(gameassembly.resolve()),
        "gameAssemblySha256": gameassembly_hash,
        "metadata": str(metadata.resolve()),
        "metadataSha256": metadata_hash,
        "methods": [
            {
                "name": "Beyond.Gameplay.Factory.FacBoneTRSBinary.InitMain",
                "token": "0x060004c5",
                "methodIndex": 394317,
                "va": "0x18449b330",
                "finding": (
                    "memory-maps FacBoneTRS.bin, retains its base pointer, and "
                    "initializes the unit lookup table"
                ),
            },
            {
                "name": "Beyond.Gameplay.Factory.FacBoneTRSBinary._InitTable",
                "token": "0x060004c6",
                "methodIndex": 394318,
                "va": "0x18449bb30",
                "finding": (
                    "initializes the unit hash table from file base + 4"
                ),
            },
            {
                "name": (
                    "Beyond.Gameplay.Factory.FacBoneTRSBinary.TryGetBoneTRS"
                ),
                "token": "0x060004c7",
                "methodIndex": 394319,
                "va": "0x1869bf644",
                "finding": (
                    "looks up signed guid, scans 16-byte bone entries for a "
                    "64-bit bone hash, bounds-checks frame, and copies one "
                    "64-byte matrix"
                ),
            },
            {
                "name": "Beyond.Gameplay.Factory.STATICVATDATA.GetBoneTRS",
                "token": "0x060069bd",
                "methodIndex": 27068,
                "va": "0x1874e4ae0",
                "finding": (
                    "gets the entity's current VAT frame, hashes boneName with "
                    "StringHash64, and calls TryGetBoneTRS"
                ),
            },
        ],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if not args.facbone_trs.is_file():
        raise AuditError(f"FacBoneTRS.bin does not exist: {args.facbone_trs}")
    data = args.facbone_trs.read_bytes()
    file_hash = hashlib.sha256(data).hexdigest()
    if file_hash != EXPECTED_FACBONE_SHA256:
        raise AuditError("FacBoneTRS.bin hash drifted; re-audit its layout")
    decoded = decode_facbone_trs(data)
    target_hits = find_exact_encoded_targets(data, args.target)
    inventory = validate_extend_data_inventory(args.vfs_index)
    native = validate_native_inputs(args.gameassembly, args.metadata)
    return {
        "schemaVersion": 1,
        "source": {
            "file": rel_path(args.facbone_trs),
            "sha256": file_hash,
        },
        "scope": {
            "targets": list(args.target),
            "purpose": (
                "classify the final current ExtendData-family file and test "
                "whether it can co-carry unresolved Story selectors"
            ),
        },
        "layout": decoded,
        "extendDataInventory": inventory,
        "nativeEvidence": native,
        "exactEncodedTargetHits": target_hits,
        "conclusion": {
            "classification": "factory_animation_transform_only",
            "missionGraphAction": "none",
            "reason": (
                "The complete file is an exact guid -> bone hash -> frame -> "
                "64-byte matrix lookup. The native caller supplies an entity "
                "VAT frame and hashed bone name; the schema has no Story key, "
                "mission, quest, LevelScript, phase, or playback-owner field. "
                "No unresolved Story root occurs in ASCII or UTF-16LE form."
            ),
        },
        "boundary": (
            "This closes the hash-gated current FacBoneTRS.bin as a Story "
            "carrier. It does not classify runtime/server state, future "
            "ExtendData files, or arbitrary semantic meaning assigned to "
            "numeric guids outside this reader path."
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    layout = report["layout"]
    inventory = report["extendDataInventory"]
    conclusion = report["conclusion"]
    methods = report["nativeEvidence"]["methods"]
    lines = [
        "# FacBoneTRS Story audit",
        "",
        f"- classification: **{conclusion['classification']}**",
        f"- mission-graph action: **{conclusion['missionGraphAction']}**",
        f"- source: `{report['source']['file']}`",
        f"- SHA-256: `{report['source']['sha256']}`",
        f"- bytes: {layout['fileBytes']:,}",
        "",
        "## Current ExtendData inventory",
        "",
        f"- VFS index: `{inventory['index']}`",
        f"- blocks / chunks / files: {inventory['blockCount']:,} / "
        f"{inventory['chunkCount']:,} / {inventory['fileCount']:,}",
        "",
    ]
    for row in inventory["files"]:
        lines.append(
            f"- `{row['name']}`: {row['length']:,} bytes "
            f"(`{row['blockType']}`)"
        )
    lines.extend(
        [
        "",
        "## Validated layout",
        "",
        f"- unit hash table: {layout['bucketCount']:,} buckets / "
        f"{layout['unitCount']:,} guid entries / "
        f"{layout['unitTableBytes']:,} bytes",
        f"- bone table: {layout['boneCount']:,} records from "
        f"{layout['boneTableStart']:,} to {layout['boneTableEnd']:,}",
        f"- matrix table: {layout['matrixCount']:,} 64-byte matrices from "
        f"{layout['matrixTableStart']:,} to {layout['matrixTableEnd']:,}",
        f"- frame-count range per bone: {layout['frameCountMin']:,} to "
        f"{layout['frameCountMax']:,}",
        f"- non-finite matrix floats: {layout['nonFiniteFloatCount']:,}",
        f"- duplicate bone hashes within a unit: "
        f"{layout['duplicateBoneHashesWithinUnit']:,}",
        "",
        "Every unit, bone, and matrix range forms a gap-free, non-overlapping "
        "partition and the final matrix ends exactly at EOF.",
        "",
        "## Native reader",
        "",
        ]
    )
    for method in methods:
        lines.append(
            f"- `{method['name']}` (`{method['token']}`, "
            f"`{method['va']}`): {method['finding']}"
        )
    lines.extend(
        [
            "",
            "## Story relevance",
            "",
            f"- exact encoded target hits: "
            f"{len(report['exactEncodedTargetHits']):,}",
            "",
            conclusion["reason"],
            "",
            report["boundary"],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facbone-trs", type=Path, default=DEFAULT_FACBONE_BIN)
    parser.add_argument("--vfs-index", type=Path, default=DEFAULT_VFS_INDEX)
    parser.add_argument(
        "--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--target", action="append", default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    args.target = tuple(args.target or DEFAULT_TARGETS)
    return args


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args)
    except AuditError as exc:
        raise SystemExit(f"error: {exc}") from exc
    write_json(args.out, report)
    write_markdown(args.markdown, report)
    layout = report["layout"]
    print(
        "FacBoneTRS Story audit: "
        f"{layout['unitCount']} units, {layout['boneCount']} bones, "
        f"{layout['matrixCount']} matrices, "
        f"{len(report['exactEncodedTargetHits'])} target hits"
    )
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
