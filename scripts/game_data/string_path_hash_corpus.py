"""Gate both StringPathHash catalogs against current VFS and manifest keys.

The VFS audit supplies independently recomputed path hashes from the installed
metadata. The selected native contract proves the catalog hash branch, while
BundleManifest's native contract identifies AssetInfo pathHashHead. This gate
checks every catalog row by exact path plus stored hash, retaining repeated
catalog pairs. Main AssetInfo rows must equal the manifest multiset; initial
AssetInfo rows must be a multiset subset. Repeated VFS rows for one logical
path are reported without duplicating its path/hash witness.
Reading the compressed manifest requires the same optional Brotli package as
the maintained BundleManifest reader; no xxhash package is used.

The initial catalog also repeats its own ``Data/`` path/hash pair. Standard
XXH3 disagrees with some main-catalog rows only because the VFS
implementation branches at exactly 128 UTF-8 bytes; the gate replays 127-,
128- and 129-byte controls to keep that boundary visible. The catalog writer
and runtime lookup remain open.

What a passing run establishes: every distinct ``Data/`` path/hash pair in
either catalog equals the VFS ledger's recomputed filename hash for that exact
path (the ledger separates verified payloads from missing optional audio or
voice chunks whose metadata-only filename hashes still match), and the
remaining pairs join the manifest as above. The reader
(``extend_data_binary``) consumes the string pool through EOF: every counted
string is strict, terminated UTF-16LE, every bucket has a distinct record
position, and every stored path offset names a string start. Every stored
unsigned 64-bit hash locates its slot by modulo the catalog's count. The other
bucket word and a four-byte gap before the string pool stay anonymous. These
stored joins establish neither asset ownership nor runtime use, and a framed
catalog is not an exhaustive runtime namespace.

Recorded negatives: FNV, DJB2, SDBM, classic xxHash64, Murmur64A and
MurmurHash3 failed to replay the catalogs under their tested encodings and
seeds; the native method name ``XXHash64`` does not mean classic xxHash64, and
the 128-byte branch explains why the earlier xxHash64 and standard-XXH3 probes
missed rows. It is not evidence for a third stored hash.

``--scope`` is ``main`` or ``initial``; ``--source`` is that scope's dumped
catalog ``.bin`` and ``--manifest`` the dumped manifest. Pass the VFS audit
summary, ledger and ``inputSetSha256``. Run each scope separately, each with
its own ``--out`` path under ``reports/animestudio/``, so one scope's report
never overwrites the other's.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.string_path_hash_corpus")

import argparse
from collections import Counter
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.bundle_manifest import parse_decompressed_bundle_manifest
from scripts.game_data.bundle_manifest_native import audit_bundle_manifest_native
from scripts.game_data.extend_data_binary import parse_string_path_hash
from scripts.game_data.string_path_hash_native import audit_string_path_hash_native


SCHEMA = "endfield.string-path-hash-corpus-audit.v2"
CATALOG_NAMES = {
    "main": "Data/ExtendData/Main/StringPathHash.bin",
    "initial": "Data/ExtendData/Initial/InitStringPathHash.bin",
}
MANIFEST_NAME = "Data/Bundles/Windows/manifest.hgmmap"


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(f"string-path-hash-corpus:{label}")


def _catalog_pairs(raw: bytes) -> tuple[Counter[tuple[str, int]], Counter[tuple[str, int]], Counter[int], int]:
    parsed = parse_string_path_hash(raw)
    data_pairs: Counter[tuple[str, int]] = Counter()
    asset_pairs: Counter[tuple[str, int]] = Counter()
    data_lengths: Counter[int] = Counter()
    slot_matches = 0
    for slot in range(parsed.count):
        offset, size = struct.unpack_from("<II", raw, 8 + slot * 8)
        for bucket in range(size):
            _word, value, path_offset = struct.unpack_from("<IQI", raw, offset + bucket * 16)
            _require(value % parsed.count == slot, f"slot-hash-modulo:{slot}:{bucket}")
            slot_matches += 1
            start = parsed.str_data_offset + path_offset
            length = struct.unpack_from("<I", raw, start)[0]
            path = raw[start + 4:start + 4 + length].decode("utf-16-le", "strict")
            if path.lower().startswith("data/"):
                data_pairs[(path, value)] += 1
                data_lengths[len(path.encode("utf-8"))] += 1
            else:
                asset_pairs[(path.lower(), value)] += 1
    _require(slot_matches == parsed.count, "catalog-count")
    _require(parsed.consumed_bytes == len(raw), "catalog-exact-eof")
    return data_pairs, asset_pairs, data_lengths, slot_matches


def _manifest_pairs(raw: bytes) -> tuple[Counter[tuple[str, int]], dict[str, Any]]:
    try:
        import brotli
    except ImportError as error:
        raise ValueError("string-path-hash-corpus:manifest-brotli-package-missing") from error
    decoded = brotli.decompress(raw)
    parsed = parse_decompressed_bundle_manifest(decoded)
    table = parsed.tables[0]
    payload = memoryview(decoded)[parsed.variable_region.payload_offset:parsed.variable_region.footer_offset]
    value_start = table.offset + table.row_count * 8
    pairs: Counter[tuple[str, int]] = Counter()
    for row in range(table.row_count):
        path_hash, path_offset, _bundle_index, _asset_size, _padding = struct.unpack_from(
            "<Q4I", decoded, value_start + row * 24
        )
        _require(path_offset <= len(payload) - 4, f"manifest-path-offset:{row}")
        compressed_size = struct.unpack_from("<I", payload, path_offset)[0]
        _require(compressed_size <= len(payload) - path_offset - 4, f"manifest-path-size:{row}")
        path_bytes = brotli.decompress(payload[path_offset + 4:path_offset + 4 + compressed_size])
        _require(len(path_bytes) % 2 == 0, f"manifest-path-utf16-length:{row}")
        path = path_bytes.decode("utf-16-le", "strict")
        pairs[(path, path_hash)] += 1
    _require(sum(pairs.values()) == table.row_count, "manifest-asset-count")
    return pairs, {
        "compressedSha256": _digest(raw),
        "decompressedSha256": _digest(decoded),
        "assetValueCount": table.row_count,
        "distinctPathHashPairs": len(pairs),
    }


def _ledger_rows(
    ledger_path: Path, summary: dict[str, Any], data_paths: set[str], catalog_name: str,
) -> tuple[Counter[tuple[str, int]], dict[str, list[dict[str, Any]]], Counter[str], int]:
    expected_sha = summary["publication"]["ledgerSha256"].upper()
    _require(_digest(ledger_path.read_bytes()) == expected_sha, "vfs-ledger-sha256")
    input_set = summary["inputSetSha256"]
    data_pairs: Counter[tuple[str, int]] = Counter()
    data_statuses: Counter[str] = Counter()
    duplicate_data_rows = 0
    sources: dict[str, list[dict[str, Any]]] = {catalog_name: [], MANIFEST_NAME: []}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            _require(row.get("inputSetSha256") == input_set, "vfs-ledger-input-set")
            if row.get("recordType") != "file":
                continue
            name = row.get("fileName")
            if name not in data_paths and name not in sources:
                continue
            status = row.get("status")
            boundary = row.get("boundaryStatus")
            if status == "verified" and boundary == "boundary_verified":
                pass
            elif status in {"excluded_missing_audio", "excluded_missing_voice"} and boundary == status:
                _require(row.get("physicalChunkSource") == "missing", f"excluded-chunk:{name}")
            else:
                continue
            _require(row["fileNameHashDeclaredHex"] == row["fileNameHashRecomputedHex"],
                     f"vfs-filename-hash:{name}")
            if name in sources:
                if status == "verified":
                    sources[name].append(row)
            if name in data_paths:
                pair = (name, int(row["fileNameHashRecomputedHex"], 16))
                if pair in data_pairs:
                    duplicate_data_rows += 1
                data_pairs[pair] = 1
                data_statuses[status] += 1
    return data_pairs, sources, data_statuses, duplicate_data_rows


def _compare_pairs(left: Counter[tuple[str, int]], right: Counter[tuple[str, int]], label: str) -> None:
    missing = left - right
    extra = right - left
    if missing or extra:
        first = next(iter(missing or extra))
        raise ValueError(
            f"string-path-hash-corpus:{label}:missing={sum(missing.values())},"
            f"extra={sum(extra.values())},first={first!r}"
        )


def audit_string_path_hash_corpus(
    *, source: Path, manifest: Path, vfs_summary: Path, vfs_ledger: Path,
    expected_input_set_sha256: str, scope: str = "main",
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "mismatched", "detail": "",
        "catalogScope": scope,
        "expectedInputSetSha256": expected_input_set_sha256.upper(),
    }
    try:
        _require(scope in CATALOG_NAMES, "catalog-scope")
        catalog_name = CATALOG_NAMES[scope]
        summary = json.loads(vfs_summary.read_text(encoding="utf-8"))
        _require(summary["summary"]["fullAuditPassed"] is True, "vfs-summary-not-full-pass")
        input_set = summary["inputSetSha256"].upper()
        _require(input_set == expected_input_set_sha256.upper(), "input-set-sha256")
        native = audit_string_path_hash_native()
        _require(native["status"] == "validated", f"catalog-native:{native['status']}:{native['detail']}")
        manifest_native = audit_bundle_manifest_native()
        _require(manifest_native["status"] == "validated",
                 f"manifest-native:{manifest_native['status']}:{manifest_native['detail']}")

        source_raw = source.read_bytes()
        manifest_raw = manifest.read_bytes()
        data_pairs, asset_pairs, data_lengths, slot_matches = _catalog_pairs(source_raw)
        ledger_data, source_rows, data_statuses, duplicate_data_rows = _ledger_rows(
            vfs_ledger, summary, {path for path, _ in data_pairs}, catalog_name
        )
        for name, raw in ((catalog_name, source_raw), (MANIFEST_NAME, manifest_raw)):
            rows = source_rows[name]
            _require(len(rows) == 1, f"selected-vfs-source:{name}")
            row = rows[0]
            _require(row["length"] == len(raw), f"source-length:{name}")
            _require(row["recomputedFileDataMd5"].upper() == hashlib.md5(raw).hexdigest().upper(),
                     f"source-md5:{name}")
        data_distinct_pairs = Counter({pair: 1 for pair in data_pairs})
        if scope == "main":
            _require(sum(data_pairs.values()) == len(data_pairs), "main-data-catalog-duplicate")
        _compare_pairs(data_distinct_pairs, ledger_data, "data-vfs-path-hash")
        manifest_pairs, manifest_info = _manifest_pairs(manifest_raw)
        if scope == "main":
            _compare_pairs(asset_pairs, manifest_pairs, "asset-manifest-path-hash")
            for boundary_length in (127, 128, 129):
                _require(data_lengths[boundary_length] > 0, f"missing-length-control:{boundary_length}")
        else:
            missing_assets = asset_pairs - manifest_pairs
            if missing_assets:
                first = next(iter(missing_assets))
                raise ValueError(
                    f"string-path-hash-corpus:initial-asset-manifest:"
                    f"missing={sum(missing_assets.values())},first={first!r}"
                )
        repeated_data = [
            {"path": path, "storedHash": f"{value:016X}", "rows": count}
            for (path, value), count in data_pairs.items() if count > 1
        ]
        report.update(
            status="validated",
            inputSetSha256=input_set,
            nativeContractSha256=native["contractSha256"],
            manifestNativeContractSha256=manifest_native["contractSha256"],
            vfsLedgerSha256=summary["publication"]["ledgerSha256"].upper(),
            catalog={
                "logicalPath": catalog_name,
                "sourceSha256": _digest(source_raw), "sourceMd5": hashlib.md5(source_raw).hexdigest().upper(),
                "sourceBytes": len(source_raw), "rows": slot_matches,
                "dataRows": sum(data_pairs.values()), "assetRows": sum(asset_pairs.values()),
                "dataDistinctPathHashPairs": len(data_pairs),
                "assetDistinctPathHashPairs": len(asset_pairs),
                "slotHashModuloMatches": slot_matches,
            },
            joins={
                "dataRowsWithVfsFilenameHashWitness": sum(data_pairs.values()),
                "dataDistinctPairsWithVfsWitness": len(data_pairs),
                "repeatedDataPathHashPairs": repeated_data,
                "dataVfsRowStatuses": dict(data_statuses),
                "duplicateVfsRowsForDataPathHash": duplicate_data_rows,
                "assetJoinRelation": "equal" if scope == "main" else "multiset-subset",
                "assetRowsWithManifestPathHashHeadWitness": sum(asset_pairs.values()),
                "manifest": manifest_info,
                "dataUtf8LengthControls": {
                    str(length): {"rows": data_lengths[length], "vfsHashMatches": data_lengths[length]}
                    for length in (127, 128, 129)
                },
            },
            evidenceBoundary={
                "data": "every distinct catalog path/hash pair equals an independently recomputed VFS filename hash; repeated catalog pairs and duplicate VFS rows are separately reported; excluded missing audio/voice rows authenticate metadata but have no available payload",
                "assets": "main catalog equals native-gated BundleManifest AssetInfo by lowercased path/hash multiset; initial catalog is a multiset subset",
                "native": "selected-build static hash route; live writer execution and unseen paths unresolved",
            },
        )
    except (OSError, ValueError, KeyError, IndexError, struct.error, UnicodeError) as error:
        report["detail"] = str(error)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=tuple(CATALOG_NAMES), default="main")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--vfs-summary", type=Path, required=True)
    parser.add_argument("--vfs-ledger", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit_string_path_hash_corpus(
        source=args.source, manifest=args.manifest, vfs_summary=args.vfs_summary,
        vfs_ledger=args.vfs_ledger, expected_input_set_sha256=args.expected_input_set_sha256,
        scope=args.scope,
    )
    result = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
    print(result, end="")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
