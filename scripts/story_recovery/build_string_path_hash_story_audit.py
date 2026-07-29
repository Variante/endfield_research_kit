#!/usr/bin/env python3
"""Audit StringPathHash resource paths for unresolved Story-root consumers.

The shipped ``StringPathHash.bin`` file is a reverse diagnostic lookup from an
opaque 64-bit ``Beyond.Resource.StringPathHash`` value to its original resource
path.  It proves that a resource path is registered, but it is not itself a
playback selector or an ownership table.

This fail-closed audit validates the binary layout, recovers every resource
path/hash containing the selected Story roots, and searches exported structured
data plus AnimeStudio object indexes for exact consumers of those hashes.  It is
an offline recovery audit and is not part of ``export.bat``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HASH_BIN = (
    ROOT
    / "tmp"
    / "story"
    / "root_selector_string_path_hash"
    / "Data"
    / "ExtendData"
    / "Main"
    / "StringPathHash.bin"
)
DEFAULT_INITIAL_HASH_BIN = (
    ROOT
    / "tmp"
    / "story"
    / "root_selector_string_path_hash"
    / "Data"
    / "ExtendData"
    / "Initial"
    / "InitStringPathHash.bin"
)
DEFAULT_STRUCTURED_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets"
DEFAULT_NATIVE_BINARIES = (
    Path(r"D:\Program Files\Endfield Game\GameAssembly.dll"),
)
DEFAULT_OBJECT_INDEXES = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "object_index"
    / "objects.jsonl.gz",
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "object_index"
    / "objects.jsonl.gz",
)
DEFAULT_EXTRA_BINARIES = (
    ROOT
    / "tmp"
    / "story"
    / "root_selector_compress_data"
    / "Data"
    / "ExtendData"
    / "Main"
    / "CompressData.bin",
)
DEFAULT_TARGETS = (
    "cutscene_e11m2_liexi_xs_m_01_last_01",
    "cutscene_e11m2_liexi_xs_m_01_last_02",
    "cutscene_f1m9d3_1",
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "string_path_hash_story_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")
UINT64_MASK = (1 << 64) - 1


@dataclass(frozen=True)
class HashPath:
    entry_index: int
    hash_signed: int
    string_pool_offset: int
    path: str

    @property
    def hash_unsigned(self) -> int:
        return self.hash_signed & UINT64_MASK

    @property
    def hash_hex(self) -> str:
        return f"0x{self.hash_unsigned:016x}"


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_string_path_hash(path: Path) -> tuple[dict[str, Any], list[HashPath]]:
    data = path.read_bytes()
    if len(data) < 8:
        raise ValueError(f"{path}: file is shorter than the 8-byte header")

    string_pool_offset, entry_count = struct.unpack_from("<II", data, 0)
    bucket_offset = 8
    entry_offset = bucket_offset + entry_count * 8
    expected_pool_offset = entry_offset + entry_count * 16
    if string_pool_offset != expected_pool_offset:
        raise ValueError(
            f"{path}: pool offset {string_pool_offset} does not equal "
            f"8 + {entry_count}*8 + {entry_count}*16 ({expected_pool_offset})"
        )
    if string_pool_offset > len(data):
        raise ValueError(f"{path}: string pool begins after end of file")

    pool: dict[int, str] = {}
    position = string_pool_offset
    while position < len(data):
        relative = position - string_pool_offset
        if position + 4 > len(data):
            raise ValueError(f"{path}: truncated string length at pool offset {relative}")
        byte_length = struct.unpack_from("<I", data, position)[0]
        end = position + 4 + byte_length
        if byte_length % 2:
            raise ValueError(f"{path}: odd UTF-16 byte length at pool offset {relative}")
        if end + 2 > len(data):
            raise ValueError(f"{path}: truncated string at pool offset {relative}")
        if data[end : end + 2] != b"\0\0":
            raise ValueError(f"{path}: missing UTF-16 terminator at pool offset {relative}")
        try:
            text = data[position + 4 : end].decode("utf-16le")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"{path}: invalid UTF-16 at pool offset {relative}"
            ) from exc
        pool[relative] = text
        position = end + 2

    if position != len(data):
        raise ValueError(f"{path}: string pool did not end at EOF")
    if len(pool) != entry_count:
        raise ValueError(
            f"{path}: {len(pool)} string records do not match "
            f"{entry_count} hash entries"
        )

    rows: list[HashPath] = []
    seen_offsets: set[int] = set()
    for index in range(entry_count):
        hash_signed, string_offset = struct.unpack_from(
            "<qQ", data, entry_offset + index * 16
        )
        if string_offset not in pool:
            raise ValueError(
                f"{path}: entry {index} references invalid pool offset {string_offset}"
            )
        if string_offset in seen_offsets:
            raise ValueError(
                f"{path}: duplicate string-pool reference {string_offset}"
            )
        seen_offsets.add(string_offset)
        rows.append(
            HashPath(
                entry_index=index,
                hash_signed=hash_signed,
                string_pool_offset=string_offset,
                path=pool[string_offset],
            )
        )
    if seen_offsets != set(pool):
        raise ValueError(f"{path}: hash entries do not cover the string pool exactly")

    return (
        {
            "file": display_path(path),
            "size": len(data),
            "sha256": sha256(path),
            "entryCount": entry_count,
            "stringPoolOffset": string_pool_offset,
            "bucketTableOffset": bucket_offset,
            "bucketTableBytes": entry_count * 8,
            "entryTableOffset": entry_offset,
            "entryTableBytes": entry_count * 16,
            "entryLayout": ["hash:int64", "stringPoolOffset:uint64"],
            "stringRecordLayout": (
                "byteLength:uint32 + UTF-16LE bytes + null:uint16"
            ),
            "validated": True,
        },
        rows,
    )


def selected_hash_paths(
    rows: Iterable[HashPath],
    targets: Iterable[str],
) -> list[dict[str, Any]]:
    target_values = tuple(targets)
    selected: list[dict[str, Any]] = []
    for row in rows:
        matches = [target for target in target_values if target in row.path]
        for target in matches:
            selected.append(
                {
                    "target": target,
                    "path": row.path,
                    "hashSigned": row.hash_signed,
                    "hashUnsigned": row.hash_unsigned,
                    "hashHex": row.hash_hex,
                    "entryIndex": row.entry_index,
                    "stringPoolOffset": row.string_pool_offset,
                }
            )
    return selected


def binary_patterns(
    selected: Iterable[dict[str, Any]],
) -> dict[bytes, list[tuple[dict[str, Any], str]]]:
    rows_by_pattern: dict[bytes, list[tuple[dict[str, Any], str]]] = {}
    for row in selected:
        value = int(row["hashUnsigned"])
        for byte_order in ("little", "big"):
            pattern = value.to_bytes(8, byte_order)
            rows_by_pattern.setdefault(pattern, []).append((row, byte_order))
    return rows_by_pattern


def scan_binary_paths(
    paths: Iterable[Path],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    rows_by_pattern = binary_patterns(selected)
    files_read = 0
    bytes_read = 0
    hits: list[dict[str, Any]] = []
    source_sample: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        files_read += 1
        bytes_read += len(data)
        source = display_path(path)
        if len(source_sample) < 32:
            source_sample.append(source)
        # CPython's fixed-byte search is materially faster than a large binary
        # alternation over the multi-gigabyte structured corpus.
        for pattern, pattern_rows in rows_by_pattern.items():
            start = 0
            while True:
                offset = data.find(pattern, start)
                if offset < 0:
                    break
                for row, byte_order in pattern_rows:
                    hits.append(
                        {
                            "sourceFile": source,
                            "byteOffset": offset,
                            "byteOrder": byte_order,
                            "target": row["target"],
                            "path": row["path"],
                            "hashHex": row["hashHex"],
                        }
                    )
                start = offset + 1
    return {
        "filesRead": files_read,
        "bytesRead": bytes_read,
        "sourceSample": source_sample,
        "sourceSampleTruncated": files_read > len(source_sample),
        "hitCount": len(hits),
        "hits": hits,
    }


def iter_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def text_patterns(
    selected: Iterable[dict[str, Any]],
) -> dict[bytes, list[dict[str, Any]]]:
    rows_by_pattern: dict[bytes, list[dict[str, Any]]] = {}
    for row in selected:
        for value in (
            str(row["hashSigned"]),
            str(row["hashUnsigned"]),
            str(row["hashHex"]),
        ):
            rows_by_pattern.setdefault(value.encode("ascii"), []).append(row)
    return rows_by_pattern


def scan_object_indexes(
    paths: Iterable[Path],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    rows_by_pattern = text_patterns(selected)
    files_read = 0
    lines_read = 0
    hits: list[dict[str, Any]] = []
    sources: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        files_read += 1
        source = display_path(path)
        sources.append(source)
        opener = gzip.open if path.suffix.lower() == ".gz" else open
        with opener(path, "rb") as stream:
            for line_number, line in enumerate(stream, start=1):
                lines_read += 1
                matches: dict[str, dict[str, Any]] = {}
                for pattern, pattern_rows in rows_by_pattern.items():
                    if pattern not in line:
                        continue
                    for row in pattern_rows:
                        matches[str(row["hashHex"])] = row
                if not matches:
                    continue
                try:
                    payload = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = {}
                for row in matches.values():
                    hits.append(
                        {
                            "sourceFile": source,
                            "lineNumber": line_number,
                            "target": row["target"],
                            "path": row["path"],
                            "hashHex": row["hashHex"],
                            "object": {
                                key: payload.get(key)
                                for key in (
                                    "source",
                                    "type",
                                    "name",
                                    "pathId",
                                    "containerPath",
                                )
                                if isinstance(payload, dict) and key in payload
                            },
                        }
                    )
    return {
        "filesRead": files_read,
        "linesRead": lines_read,
        "sources": sources,
        "hitCount": len(hits),
        "hits": hits,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    table, all_rows = parse_string_path_hash(args.string_path_hash)
    initial_table, initial_rows = parse_string_path_hash(
        args.initial_string_path_hash
    )
    selected = [
        {**row, "registry": "main"}
        for row in selected_hash_paths(all_rows, args.target)
    ]
    selected.extend(
        {**row, "registry": "initial"}
        for row in selected_hash_paths(initial_rows, args.target)
    )
    missing_targets = [
        target
        for target in args.target
        if not any(row["target"] == target for row in selected)
    ]
    if missing_targets:
        raise ValueError(
            "selected Story roots have no registered resource paths: "
            + ", ".join(missing_targets)
        )

    print(
        f"validated {table['entryCount']:,} main + "
        f"{initial_table['entryCount']:,} initial StringPathHash entries; "
        f"selected {len(selected)} target paths",
        flush=True,
    )
    phase = time.perf_counter()
    structured = scan_binary_paths(iter_files(args.structured_root), selected)
    print(
        f"structured scan: {structured['filesRead']:,} files / "
        f"{structured['bytesRead']:,} bytes / {structured['hitCount']} hits "
        f"in {time.perf_counter() - phase:.1f}s",
        flush=True,
    )
    phase = time.perf_counter()
    object_indexes = scan_object_indexes(args.object_index, selected)
    print(
        f"object-index scan: {object_indexes['linesRead']:,} rows / "
        f"{object_indexes['hitCount']} hits in "
        f"{time.perf_counter() - phase:.1f}s",
        flush=True,
    )
    phase = time.perf_counter()
    extra_binaries = scan_binary_paths(args.extra_binary, selected)
    print(
        f"adjacent-binary scan: {extra_binaries['filesRead']:,} files / "
        f"{extra_binaries['hitCount']} hits in "
        f"{time.perf_counter() - phase:.1f}s",
        flush=True,
    )
    phase = time.perf_counter()
    native_binaries = scan_binary_paths(args.native_binary, selected)
    print(
        f"native-binary scan: {native_binaries['filesRead']:,} files / "
        f"{native_binaries['bytesRead']:,} bytes / "
        f"{native_binaries['hitCount']} hits in "
        f"{time.perf_counter() - phase:.1f}s; "
        f"total {time.perf_counter() - started:.1f}s",
        flush=True,
    )
    total_hits = (
        structured["hitCount"]
        + object_indexes["hitCount"]
        + extra_binaries["hitCount"]
        + native_binaries["hitCount"]
    )
    return {
        "schemaVersion": 3,
        "scope": {
            "targets": list(args.target),
            "purpose": (
                "Recover exact StringPathHash resource identities and test whether "
                "offline exported sources serialize those hashes as Story-root "
                "playback consumers."
            ),
        },
        "stringPathHashTable": table,
        "stringPathHashTables": {
            "main": table,
            "initial": initial_table,
        },
        "targetHashPaths": selected,
        "counts": {
            "targets": len(args.target),
            "targetResourcePaths": len(selected),
            "mainTargetResourcePaths": sum(
                row["registry"] == "main" for row in selected
            ),
            "initialTargetResourcePaths": sum(
                row["registry"] == "initial" for row in selected
            ),
            "structuredFilesScanned": structured["filesRead"],
            "structuredBytesScanned": structured["bytesRead"],
            "objectIndexFilesScanned": object_indexes["filesRead"],
            "objectIndexLinesScanned": object_indexes["linesRead"],
            "extraBinaryFilesScanned": extra_binaries["filesRead"],
            "extraBinaryBytesScanned": extra_binaries["bytesRead"],
            "nativeBinaryFilesScanned": native_binaries["filesRead"],
            "nativeBinaryBytesScanned": native_binaries["bytesRead"],
            "exactConsumerHits": total_hits,
        },
        "consumerCensus": {
            "structuredBinary": structured,
            "objectIndexText": object_indexes,
            "extraBinary": extra_binaries,
            "nativeBinary": native_binaries,
        },
        "nativeSemantics": {
            "valueType": "Beyond.Resource.StringPathHash",
            "serializedIdentity": "System.Int64",
            "lookupOwner": "Beyond.Resource.StringPathHashBinary",
            "lookupMethods": [
                "StringPathHashBinary._GetMappingStrByHash",
                "StringPathHashBinary.GetMappingStrByHash",
            ],
            "direction": "hash_to_original_resource_path",
        },
        "conclusion": {
            "classification": (
                "resource_availability_only"
                if total_hits == 0
                else "exact_hash_consumers_require_review"
            ),
            "missionGraphAction": "none" if total_hits == 0 else "manual_review",
            "ownerRecovered": False,
            "reason": (
                "The validated binary is a hash-to-resource-path diagnostic "
                "dictionary. The selected paths are registered, but no exact "
                "64-bit hash consumer occurs in the scanned structured data, "
                "AnimeStudio object indexes, supplied adjacent binaries, or "
                "current native binaries."
                if total_hits == 0
                else "At least one exact hash occurrence requires typed review."
            ),
        },
        "boundary": (
            "Registration in StringPathHash.bin proves that a resource can be "
            "resolved by its opaque hash. It does not identify who requests that "
            "resource, when it plays, or which mission/quest owns it. A dynamically "
            "computed hash, a runtime-only/server selector, or an unscanned encoded "
            "source remains outside this exact-consumer census."
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    counts = report["counts"]
    conclusion = report["conclusion"]
    tables = report.get(
        "stringPathHashTables",
        {"main": report["stringPathHashTable"]},
    )
    lines = [
        "# StringPathHash Story audit",
        "",
        f"- classification: **{conclusion['classification']}**",
        f"- mission-graph action: **{conclusion['missionGraphAction']}**",
        f"- selected Story roots: {counts['targets']}",
        f"- registered resource paths: {counts['targetResourcePaths']}",
        f"- exact consumer hits: {counts['exactConsumerHits']}",
        "",
        "## Validated format",
        "",
    ]
    for name, table in tables.items():
        lines.extend(
            [
                f"### `{name}` registry",
                "",
                f"- source: `{table['file']}`",
                f"- SHA-256: `{table['sha256']}`",
                f"- entries / strings: {table['entryCount']:,}",
                f"- bucket table: {table['bucketTableBytes']:,} bytes",
                f"- entry table: {table['entryTableBytes']:,} bytes as "
                "`hash:int64 + stringPoolOffset:uint64`",
                "- string pool: "
                "`byteLength:uint32 + UTF-16LE bytes + null:uint16`",
                "",
            ]
        )
    lines.extend(
        [
            "Native metadata identifies `StringPathHash` as an eight-byte hash "
            "value and `StringPathHashBinary` as the owner of the main/init "
            "mapping dictionaries. Its public lookup direction is hash to "
            "original path.",
            "",
            "## Selected roots",
            "",
        ]
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in report["targetHashPaths"]:
        grouped.setdefault(row["target"], []).append(row)
    for target, rows in grouped.items():
        lines.append(f"### `{target}`")
        lines.append("")
        for row in rows:
            lines.append(
                f"- `{row.get('registry', 'main')}` "
                f"`{row['hashHex']}` -> `{row['path']}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Exact-consumer census",
            "",
            f"- structured export: {counts['structuredFilesScanned']:,} files / "
            f"{counts['structuredBytesScanned']:,} bytes; "
            f"{report['consumerCensus']['structuredBinary']['hitCount']} hits",
            f"- AnimeStudio object indexes: {counts['objectIndexLinesScanned']:,} "
            f"rows; {report['consumerCensus']['objectIndexText']['hitCount']} hits",
            f"- adjacent supplied binaries: {counts['extraBinaryFilesScanned']:,} "
            f"files / {counts['extraBinaryBytesScanned']:,} bytes; "
            f"{report['consumerCensus']['extraBinary']['hitCount']} hits",
            f"- current native binaries: "
            f"{counts['nativeBinaryFilesScanned']:,} files / "
            f"{counts['nativeBinaryBytesScanned']:,} bytes; "
            f"{report['consumerCensus']['nativeBinary']['hitCount']} hits",
            "",
            "Both little- and big-endian 64-bit byte forms were searched in binary "
            "sources; signed, unsigned, and hexadecimal text forms were searched "
            "in the object indexes.",
            "",
            "## Conclusion",
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
    parser.add_argument(
        "--string-path-hash",
        type=Path,
        default=DEFAULT_HASH_BIN,
        help=(
            "Targeted VFS dump of Data/ExtendData/Main/StringPathHash.bin. "
            "The normal WebUI export intentionally skips this block."
        ),
    )
    parser.add_argument(
        "--structured-root",
        type=Path,
        default=DEFAULT_STRUCTURED_ROOT,
    )
    parser.add_argument(
        "--initial-string-path-hash",
        type=Path,
        default=DEFAULT_INITIAL_HASH_BIN,
        help=(
            "Targeted VFS dump of "
            "Data/ExtendData/Initial/InitStringPathHash.bin."
        ),
    )
    parser.add_argument(
        "--object-index",
        type=Path,
        action="append",
        default=None,
        help="AnimeStudio object JSONL/JSONL.GZ index; may be repeated.",
    )
    parser.add_argument(
        "--extra-binary",
        type=Path,
        action="append",
        default=None,
        help="Adjacent decoded binary to search; may be repeated.",
    )
    parser.add_argument(
        "--native-binary",
        type=Path,
        action="append",
        default=None,
        help="Current native binary to search; may be repeated.",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        help="Story-root substring to recover and scan; may be repeated.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    args.object_index = (
        tuple(args.object_index) if args.object_index else DEFAULT_OBJECT_INDEXES
    )
    args.extra_binary = (
        tuple(args.extra_binary) if args.extra_binary else DEFAULT_EXTRA_BINARIES
    )
    args.native_binary = (
        tuple(args.native_binary)
        if args.native_binary
        else DEFAULT_NATIVE_BINARIES
    )
    args.target = tuple(args.target) if args.target else DEFAULT_TARGETS
    return args


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.markdown, report)
    print(
        "StringPathHash Story audit: "
        f"{report['counts']['targetResourcePaths']} paths, "
        f"{report['counts']['exactConsumerHits']} exact consumer hits"
    )
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
