"""Join one exactly framed BundleManifest to a full authenticated VFS ledger.

The joined row words are reported as structural relations, not managed field
names or a runtime lookup receipt. Run ``vfs-audit`` for the selected install
first, then ``AnimeStudio.CLI dump --block-type bundle-manifest --verify-md5``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.bundle_manifest import (
    BinaryFormatError,
    parse_decompressed_bundle_manifest,
)


MANIFEST_PATH = "Data/Bundles/Windows/manifest.hgmmap"
BUNDLE_PREFIX = "Data/Bundles/Windows/"
BUNDLE_BLOCKS = {"Bundle", "InitBundle"}


class BundleManifestCorpusError(ValueError):
    """An authenticated input or complete-corpus relation failed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest().upper()


def _record(payload: memoryview, offset: int) -> tuple[str, bytes, int]:
    """Return one parser-validated anonymous record without naming its lists."""

    start = offset
    if start < 0 or start + 4 > len(payload):
        raise BundleManifestCorpusError(f"record at {start} lacks a UTF-16 length")
    byte_count = struct.unpack_from("<I", payload, offset)[0]
    if byte_count % 2 or offset + 4 + byte_count + 2 > len(payload):
        raise BundleManifestCorpusError(f"record at {start} has invalid UTF-16 range")
    offset += 4
    name = bytes(payload[offset : offset + byte_count]).decode("utf-16-le", "strict")
    offset += byte_count + 2
    for component in range(3):
        if offset + 4 > len(payload):
            raise BundleManifestCorpusError(
                f"record at {start} lacks list {component + 1} count"
            )
        count = struct.unpack_from("<I", payload, offset)[0]
        length = 4 + count * 4 + 2
        if length > len(payload) - offset:
            raise BundleManifestCorpusError(
                f"record at {start} list {component + 1} exceeds payload"
            )
        offset += length
    return name, bytes(payload[start:offset]), offset


def _load_ledger(
    summary_path: Path,
    ledger_path: Path,
    expected_input_set_sha256: str,
) -> tuple[str, dict[str, tuple[str, str]], dict[str, Any], set[str]]:
    outer = json.loads(summary_path.read_text(encoding="utf-8"))
    input_set = str(outer.get("inputSetSha256", "")).upper()
    if input_set != expected_input_set_sha256.upper():
        raise BundleManifestCorpusError(
            f"vfs-audit inputSetSha256 {input_set or '<missing>'} != expected "
            f"{expected_input_set_sha256.upper()}"
        )
    if not outer.get("summary", {}).get("fullAuditPassed"):
        raise BundleManifestCorpusError("vfs-audit did not pass its full-catalog gate")
    expected_ledger_hash = str(outer.get("publication", {}).get("ledgerSha256", "")).upper()
    actual_ledger_hash = _sha256_file(ledger_path)
    if not expected_ledger_hash or actual_ledger_hash != expected_ledger_hash:
        raise BundleManifestCorpusError(
            f"ledger SHA256 {actual_ledger_hash} != summary publication "
            f"{expected_ledger_hash or '<missing>'}"
        )

    bundles: dict[str, tuple[str, str]] = {}
    manifest_rows: list[dict[str, Any]] = []
    all_filename_hashes: set[str] = set()
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get("recordType") != "file":
                continue
            if row.get("inputSetSha256", "").upper() != input_set:
                raise BundleManifestCorpusError(
                    f"ledger line {line_number} inputSetSha256 differs from summary"
                )
            if row.get("boundaryStatus") != "boundary_verified":
                continue
            file_hash = str(row.get("fileNameHashRecomputedHex", "")).upper()
            if file_hash:
                all_filename_hashes.add(file_hash)
            name = row.get("fileName")
            if name == MANIFEST_PATH and row.get("blockName") == "BundleManifest":
                manifest_rows.append(row)
            if row.get("blockName") not in BUNDLE_BLOCKS:
                continue
            if not isinstance(name, str) or not name.startswith(BUNDLE_PREFIX):
                raise BundleManifestCorpusError(
                    f"ledger line {line_number} bundle has unexpected path {name!r}"
                )
            short_name = name[len(BUNDLE_PREFIX) :]
            if short_name in bundles:
                raise BundleManifestCorpusError(
                    f"duplicate active bundle path {short_name!r} at ledger line {line_number}"
                )
            declared = str(row.get("fileNameHashDeclaredHex", "")).upper()
            recomputed = str(row.get("fileNameHashRecomputedHex", "")).upper()
            if not declared or declared != recomputed:
                raise BundleManifestCorpusError(
                    f"ledger line {line_number} bundle filename hash did not verify"
                )
            bundles[short_name] = (row["blockName"], recomputed)
    if len(manifest_rows) != 1:
        raise BundleManifestCorpusError(
            f"expected one active {MANIFEST_PATH} ledger row, found {len(manifest_rows)}"
        )
    return input_set, bundles, manifest_rows[0], all_filename_hashes


def inspect(
    manifest_path: Path,
    summary_path: Path,
    ledger_path: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Authenticate source bytes and check every indexed manifest row."""

    input_set, bundles, manifest_ledger, all_filename_hashes = _load_ledger(
        summary_path, ledger_path, expected_input_set_sha256
    )
    compressed = manifest_path.read_bytes()
    actual_md5 = hashlib.md5(compressed).hexdigest().upper()
    expected_md5 = str(manifest_ledger.get("recomputedFileDataMd5", "")).upper()
    expected_length = manifest_ledger.get("length")
    if len(compressed) != expected_length or actual_md5 != expected_md5:
        raise BundleManifestCorpusError(
            f"manifest dump length/MD5 {len(compressed)}/{actual_md5} != "
            f"VFS ledger {expected_length}/{expected_md5} ({MANIFEST_PATH})"
        )
    try:
        import brotli
    except ImportError as exc:
        raise BundleManifestCorpusError("Python brotli is required for .hgmmap") from exc
    try:
        decoded = brotli.decompress(compressed)
    except Exception as exc:
        raise BundleManifestCorpusError(f"manifest Brotli stream: {exc}") from exc
    parsed = parse_decompressed_bundle_manifest(decoded, source=MANIFEST_PATH)
    table = parsed.tables[2]
    if table.row_count != len(bundles):
        raise BundleManifestCorpusError(
            f"48-byte manifest rows {table.row_count} != verified bundle files {len(bundles)}"
        )
    region = parsed.variable_region
    payload = memoryview(decoded)[region.payload_offset : region.footer_offset]

    sequential_records: Counter[bytes] = Counter()
    cursor = 0
    for index in range(table.row_count):
        _, raw, cursor = _record(payload, cursor)
        if cursor > region.sequential_region_length:
            raise BundleManifestCorpusError(
                f"sequential record {index} crosses region end {region.sequential_region_length}"
            )
        sequential_records[raw] += 1
    if cursor != region.sequential_region_length:
        raise BundleManifestCorpusError(
            f"sequential records end at {cursor}, expected {region.sequential_region_length}"
        )

    seen_names: set[str] = set()
    duplicate_hash_pairs = 0
    alternate_hash_vfs_matches = 0
    previous_name = ""
    for index in range(table.row_count):
        row = struct.unpack_from("<12I", decoded, table.offset + index * table.row_size)
        name, raw, end = _record(payload, row[1])
        expected_end = (
            struct.unpack_from("<I", decoded, table.offset + (index + 1) * table.row_size + 4)[0]
            if index + 1 < table.row_count
            else region.opaque_suffix_offset
        )
        if end != expected_end:
            raise BundleManifestCorpusError(
                f"indexed row {index} record end {end} != next boundary {expected_end}"
            )
        if name in seen_names:
            raise BundleManifestCorpusError(f"duplicate indexed manifest name {name!r}")
        seen_names.add(name)
        if index and name <= previous_name:
            raise BundleManifestCorpusError(
                f"indexed names not strictly ascending at row {index}: "
                f"{previous_name!r} then {name!r}"
            )
        previous_name = name
        ledger_row = bundles.get(name)
        if ledger_row is None:
            raise BundleManifestCorpusError(
                f"indexed row {index} {name!r} has no verified Bundle/InitBundle path"
            )
        block_name, expected_hash = ledger_row
        stored_hash = f"{row[7]:08X}{row[6]:08X}"
        if stored_hash != expected_hash:
            raise BundleManifestCorpusError(
                f"indexed row {index} {name!r} word[6:8] {stored_hash} != "
                f"VFS filename hash {expected_hash}"
            )
        expected_flag = 1 if block_name == "InitBundle" else 0
        if row[10] != expected_flag:
            raise BundleManifestCorpusError(
                f"indexed row {index} {name!r} word[10] {row[10]} != "
                f"{block_name} discriminator {expected_flag}"
            )
        if sequential_records[raw] <= 0:
            raise BundleManifestCorpusError(
                f"indexed row {index} {name!r} has no matching sequential record"
            )
        sequential_records[raw] -= 1
        if not sequential_records[raw]:
            del sequential_records[raw]
        alternate_hash = f"{row[9]:08X}{row[8]:08X}"
        duplicate_hash_pairs += alternate_hash == stored_hash
        alternate_hash_vfs_matches += (
            alternate_hash != stored_hash and alternate_hash in all_filename_hashes
        )
    if sequential_records or seen_names != bundles.keys():
        missing = sorted(bundles.keys() - seen_names)
        raise BundleManifestCorpusError(
            f"manifest/VFS sets differ: {len(sequential_records)} unmatched records; "
            f"first missing bundle {missing[:1]!r}"
        )

    return {
        "format": "endfield-bundle-manifest-corpus-v1",
        "status": "validated",
        "inputSetSha256": input_set,
        "source": str(manifest_path),
        "sourceLength": len(compressed),
        "sourceMd5": actual_md5,
        "decompressedLength": len(decoded),
        "decompressedSha256": hashlib.sha256(decoded).hexdigest().upper(),
        "framing": "exact-eof-anonymous",
        "bundleCount": len(bundles),
        "table48Rows": table.row_count,
        "indexedNamesLexicallySorted": True,
        "indexedNamesUnique": True,
        "indexedNamesEqualVerifiedBundlePaths": True,
        "sequentialAndIndexedRawRecordMultisetsEqual": True,
        "filenameHashWordPair67Matches": table.row_count,
        "blockDiscriminatorWord10Matches": table.row_count,
        "wordPair67EqualsWordPair89": duplicate_hash_pairs,
        "differentWordPair89MatchesAnyVfsFilenameHash": alternate_hash_vfs_matches,
        "opaqueTerminalBytes": region.opaque_suffix_length,
        "evidenceBoundary": "structuralOnly",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--outer-summary", type=Path, required=True)
    parser.add_argument("--outer-ledger", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = inspect(
            args.manifest,
            args.outer_summary,
            args.outer_ledger,
            args.expected_input_set_sha256,
        )
    except (BundleManifestCorpusError, BinaryFormatError, OSError, ValueError) as exc:
        report = {
            "format": "endfield-bundle-manifest-corpus-v1",
            "status": "failed",
            "inputSetSha256": args.expected_input_set_sha256.upper(),
            "source": str(args.manifest),
            "firstFailure": str(exc),
        }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"BundleManifest corpus: {report['status']}")
    if report["status"] != "validated":
        print(f"  {report['firstFailure']}")
        return 1
    print(
        f"  {report['bundleCount']} names, filename hashes, and block discriminators "
        "match the full VFS ledger"
    )
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.bundle_manifest_corpus")
    raise SystemExit(main())
