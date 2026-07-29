#!/usr/bin/env python3
"""Decode the current BundleManifest and bound its Story relevance.

The effective Persistent ``manifest.hgmmap`` is a Brotli stream containing
typed asset and bundle routing tables used by
``Beyond.ManifestBinary.ManifestDataBinary``. This standalone audit validates
the complete framing and table partitions and checks unresolved Story roots in
both compressed and decompressed bytes. It is not part of ``export.bat``.

The audit requires the Python ``brotli`` module. Normal repository builders
remain stdlib-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Iterable

try:
    import brotli
except ImportError:  # pragma: no cover
    brotli = None


ROOT = Path(__file__).resolve().parents[2]
PROBE_ROOT = ROOT / "tmp" / "story" / "bundle_manifest_probe"
DEFAULT_STREAMING_INDEX = PROBE_ROOT / "streaming.json"
DEFAULT_PERSISTENT_INDEX = PROBE_ROOT / "persistent.json"
DEFAULT_MANIFEST = (
    PROBE_ROOT
    / "persistent_dump"
    / "Data"
    / "Bundles"
    / "Windows"
    / "manifest.hgmmap"
)
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data"
    r"\il2cpp_data\Metadata\global-metadata.dat"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery" / "bundle_manifest_story_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")
DEFAULT_TARGETS = (
    "cutscene_e11m2_liexi_xs_m_01_last_01",
    "cutscene_e11m2_liexi_xs_m_01_last_02",
    "cutscene_f1m9d3_1",
)

EXPECTED_MANIFEST_SHA256 = (
    "24c0cbba2e1c1bbadcc096e6dd019ab5d7308a03cac41e64b221603e33692ae2"
)
EXPECTED_DECOMPRESSED_SHA256 = (
    "c6a22af9de87f21e9da4dcac93a39dad487e745245c4e9ded80d77a1cd3f72ec"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_INDEXES = {
    "streaming": {
        "version": 22_097_503,
        "length": 46_497_641,
        "dataMd5": "54F69A4C1B71C7DD3E5BA8026A758EF3",
    },
    "persistent": {
        "version": 22_764_515,
        "length": 46_476_082,
        "dataMd5": "D9F9F439835543890E98F90094D51A3F",
    },
}

HEAD1 = 0xFF11FF11
HEAD2 = 0xF1F2F3F4
ASSET_RECORD_SIZE = 24
BUNDLE_RECORD_SIZE = 48


class AuditError(RuntimeError):
    """Raised when an input cannot support a fail-closed conclusion."""


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_u32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise AuditError(f"{label}: missing uint32 at {offset}")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def read_utf16(data: bytes, offset: int, label: str) -> tuple[str, int]:
    length, offset = read_u32(data, offset, f"{label} length")
    end = offset + length * 2
    if end > len(data):
        raise AuditError(f"{label}: UTF-16 data exceeds bounds")
    try:
        value = data[offset:end].decode("utf-16le")
    except UnicodeDecodeError as exc:
        raise AuditError(f"{label}: invalid UTF-16LE: {exc}") from exc
    return value, end


def require_partition(
    ranges: Iterable[tuple[int, int, str]], start: int, end: int, label: str
) -> None:
    cursor = start
    for range_start, range_end, owner in sorted(ranges):
        if range_start != cursor:
            raise AuditError(
                f"{label}: expected {cursor}, got {range_start} ({owner})"
            )
        if range_end <= range_start or range_end > end:
            raise AuditError(
                f"{label}: invalid {range_start}:{range_end} ({owner})"
            )
        cursor = range_end
    if cursor != end:
        raise AuditError(f"{label}: ranges end at {cursor}, expected {end}")


def validate_hash_table(
    blob: bytes, record_size: int, label: str
) -> dict[str, int]:
    bucket_count, cursor = read_u32(blob, 0, f"{label} bucket count")
    if bucket_count <= 0:
        raise AuditError(f"{label}: no buckets")
    bucket_end = cursor + bucket_count * 8
    if bucket_end > len(blob):
        raise AuditError(f"{label}: bucket table exceeds blob")
    ranges = []
    entry_count = 0
    non_empty = 0
    for index in range(bucket_count):
        relative_offset, count = struct.unpack_from("<II", blob, cursor + index * 8)
        if count == 0:
            if relative_offset != 0:
                raise AuditError(f"{label}: empty bucket {index} has an offset")
            continue
        non_empty += 1
        start = relative_offset
        end = start + count * record_size
        if start < bucket_end or end > len(blob):
            raise AuditError(f"{label}: bucket {index} is outside the blob")
        ranges.append((start, end, f"bucket {index}"))
        entry_count += count
    require_partition(ranges, bucket_end, len(blob), f"{label} records")
    return {
        "bytes": len(blob),
        "bucketCount": bucket_count,
        "nonEmptyBucketCount": non_empty,
        "entryCount": entry_count,
        "recordBytes": record_size,
        "bucketTableBytes": bucket_count * 8,
    }


def decode_manifest(compressed: bytes) -> dict[str, Any]:
    if brotli is None:
        raise AuditError("Python module 'brotli' is required")
    try:
        data = brotli.decompress(compressed)
    except brotli.error as exc:
        raise AuditError(f"manifest Brotli decode failed: {exc}") from exc

    head1, cursor = read_u32(data, 0, "HEAD1")
    if head1 != HEAD1:
        raise AuditError(f"HEAD1 is {head1:#x}, expected {HEAD1:#x}")
    manifest_hash, cursor = read_utf16(data, cursor, "manifest hash")
    head2, cursor = read_u32(data, cursor, "HEAD2")
    if head2 != HEAD2:
        raise AuditError(f"HEAD2 is {head2:#x}, expected {HEAD2:#x}")
    hash_version, cursor = read_utf16(data, cursor, "hash version")
    perforce_cl, cursor = read_utf16(data, cursor, "perforce CL")

    blobs = []
    for name in ("assetInfoDictionary", "bundleInfoDictionary", "bundles"):
        length, cursor = read_u32(data, cursor, f"{name} length")
        end = cursor + length
        if end > len(data):
            raise AuditError(f"{name}: blob exceeds decompressed data")
        blobs.append((name, cursor, end, data[cursor:end]))
        cursor = end

    data_length, cursor = read_u32(data, cursor, "data pool length")
    data_end = cursor + data_length
    if data_end + 4 != len(data):
        raise AuditError(
            f"data pool ends at {data_end}, expected trailing length at "
            f"{len(data) - 4}"
        )
    trailing_length = struct.unpack_from("<I", data, data_end)[0]
    if trailing_length != data_length:
        raise AuditError(
            f"data pool trailing length {trailing_length} != {data_length}"
        )

    asset_table = validate_hash_table(
        blobs[0][3], ASSET_RECORD_SIZE, "asset dictionary"
    )
    bundle_table = validate_hash_table(
        blobs[1][3], BUNDLE_RECORD_SIZE, "bundle dictionary"
    )
    bundle_blob = blobs[2][3]
    bundle_count, _ = read_u32(bundle_blob, 0, "bundle array count")
    expected_bundle_bytes = 4 + bundle_count * BUNDLE_RECORD_SIZE
    if expected_bundle_bytes != len(bundle_blob):
        raise AuditError(
            f"bundle array is {len(bundle_blob)} bytes, expected "
            f"{expected_bundle_bytes}"
        )
    if bundle_table["entryCount"] != bundle_count:
        raise AuditError("bundle dictionary and array counts differ")

    return {
        "compressedBytes": len(compressed),
        "decompressedBytes": len(data),
        "decompressedSha256": hashlib.sha256(data).hexdigest(),
        "header": {
            "head1": f"0x{head1:08x}",
            "manifestHash": manifest_hash,
            "head2": f"0x{head2:08x}",
            "hashVersion": hash_version,
            "perforceCL": perforce_cl,
        },
        "assetDictionary": asset_table,
        "bundleDictionary": bundle_table,
        "bundleArray": {
            "bytes": len(bundle_blob),
            "entryCount": bundle_count,
            "recordBytes": BUNDLE_RECORD_SIZE,
        },
        "dataPool": {
            "bytes": data_length,
            "start": cursor,
            "end": data_end,
            "trailingLength": trailing_length,
        },
        "_decompressed": data,
    }


def validate_index(path: Path, expected: dict[str, Any], label: str) -> dict:
    if not path.is_file():
        raise AuditError(f"{label} VFS index does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"{label} VFS index is invalid JSON: {exc}") from exc
    files = payload.get("files")
    blocks = payload.get("blocks")
    summary = payload.get("summary") or {}
    if not isinstance(files, list) or len(files) != 1:
        raise AuditError(f"{label} VFS index does not contain one file")
    if not isinstance(blocks, list) or len(blocks) != 1:
        raise AuditError(f"{label} VFS index does not contain one block")
    if int(summary.get("missingBlockCount", -1)) != 0:
        raise AuditError(f"{label} VFS index has a missing block")
    if int(summary.get("missingChunkCount", -1)) != 0:
        raise AuditError(f"{label} VFS index has a missing chunk")
    row = files[0]
    actual = {
        "version": int(blocks[0].get("version") or 0),
        "length": int(row.get("length") or 0),
        "dataMd5": str(row.get("fileDataMd5") or "").upper(),
    }
    if actual != expected:
        raise AuditError(f"{label} BundleManifest index drifted: {actual!r}")
    return {
        "index": rel_path(path),
        "file": str(row.get("fileName") or ""),
        **actual,
    }


def find_exact_encoded_targets(
    sources: dict[str, bytes], targets: Iterable[str]
) -> list[dict[str, Any]]:
    hits = []
    for source, data in sources.items():
        for target in targets:
            for encoding, needle in (
                ("ascii", target.encode("ascii")),
                ("utf16le", target.encode("utf-16le")),
            ):
                offset = data.find(needle)
                if offset >= 0:
                    hits.append(
                        {
                            "source": source,
                            "target": target,
                            "encoding": encoding,
                            "firstOffset": offset,
                        }
                    )
    return hits


def validate_native_inputs(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    if not gameassembly.is_file() or not metadata.is_file():
        raise AuditError("current GameAssembly.dll/global-metadata.dat is missing")
    gameassembly_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata)
    if gameassembly_hash != EXPECTED_GAMEASSEMBLY_SHA256:
        raise AuditError("GameAssembly.dll drifted; re-audit manifest readers")
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise AuditError("global-metadata.dat drifted; re-audit manifest readers")
    return {
        "mappingId": "gameassembly-2026-07-29-bundle-manifest-v1",
        "gameAssemblySha256": gameassembly_hash,
        "metadataSha256": metadata_hash,
        "assetInfoFields": [
            "pathHashHead",
            "path",
            "bundleIndex",
            "assetSize",
        ],
        "bundleFields": [
            "bundleIndex",
            "name",
            "dependencies",
            "directReverseDependencies",
            "directDependencies",
            "bundleFlags",
            "hashName",
            "hashVersion",
            "category",
        ],
        "methods": [
            {
                "name": "Beyond.ManifestBinary.ManifestDataBinary.InitBinary",
                "token": "0x06000eb1",
                "methodIndex": 296214,
                "va": "0x18311e2e0",
            },
            {
                "name": "Beyond.ManifestBinary.ManifestDataBinary.TryGetValue(path)",
                "token": "0x06000ec2",
                "methodIndex": 296231,
                "va": "0x1868b1e50",
            },
            {
                "name": "Beyond.ManifestBinary.ManifestDataBinary.TryGetValue(hash)",
                "token": "0x06000ec3",
                "methodIndex": 296232,
                "va": "0x1868b1da0",
            },
            {
                "name": "Beyond.ManifestBinary.ManifestDataBinary._TryGetValue",
                "token": "0x06000ec4",
                "methodIndex": 296233,
                "va": "0x182fced80",
            },
        ],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    streaming = validate_index(
        args.streaming_index, EXPECTED_INDEXES["streaming"], "StreamingAssets"
    )
    persistent = validate_index(
        args.persistent_index, EXPECTED_INDEXES["persistent"], "Persistent"
    )
    if persistent["version"] <= streaming["version"]:
        raise AuditError("Persistent BundleManifest is not newer than StreamingAssets")
    if not args.manifest.is_file():
        raise AuditError(f"manifest does not exist: {args.manifest}")
    compressed = args.manifest.read_bytes()
    manifest_hash = hashlib.sha256(compressed).hexdigest()
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        raise AuditError("effective manifest.hgmmap hash drifted")
    decoded = decode_manifest(compressed)
    decompressed = decoded.pop("_decompressed")
    if decoded["decompressedSha256"] != EXPECTED_DECOMPRESSED_SHA256:
        raise AuditError("decompressed manifest hash drifted")
    target_hits = find_exact_encoded_targets(
        {"compressed": compressed, "decompressed": decompressed},
        args.target,
    )
    native = validate_native_inputs(args.gameassembly, args.metadata)
    return {
        "schemaVersion": 1,
        "source": {
            "streaming": streaming,
            "persistent": persistent,
            "effective": "persistent",
            "manifest": rel_path(args.manifest),
            "manifestSha256": manifest_hash,
        },
        "scope": {"targets": list(args.target)},
        "layout": decoded,
        "nativeEvidence": native,
        "exactEncodedTargetHits": target_hits,
        "conclusion": {
            "classification": "resource_routing_only",
            "missionGraphAction": "none",
            "reason": (
                "The complete effective manifest is a validated asset-path to "
                "bundle routing index plus bundle dependency metadata. Its "
                "typed records expose no mission, quest, LevelScript, phase, "
                "playback selector, or owner field. None of the unresolved "
                "Story roots occurs in compressed or decompressed ASCII/UTF-16LE."
            ),
        },
        "boundary": (
            "Bundle membership and dependency co-location are resource-loader "
            "relations, not authored Story ownership or chronology. Future "
            "builds, runtime/server selection, and consumers outside this "
            "hash-gated manifest reader remain separate evidence surfaces."
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    layout = report["layout"]
    source = report["source"]
    conclusion = report["conclusion"]
    lines = [
        "# BundleManifest Story audit",
        "",
        f"- classification: **{conclusion['classification']}**",
        f"- mission-graph action: **{conclusion['missionGraphAction']}**",
        f"- effective source: **{source['effective']}**",
        f"- StreamingAssets version: {source['streaming']['version']:,}",
        f"- Persistent version: {source['persistent']['version']:,}",
        f"- compressed / decompressed bytes: "
        f"{layout['compressedBytes']:,} / {layout['decompressedBytes']:,}",
        "",
        "## Validated content",
        "",
        f"- manifest hash: `{layout['header']['manifestHash']}`",
        f"- hash version: `{layout['header']['hashVersion']}`",
        f"- assets: {layout['assetDictionary']['entryCount']:,} in "
        f"{layout['assetDictionary']['bucketCount']:,} buckets",
        f"- bundles: {layout['bundleArray']['entryCount']:,} in both the "
        "dictionary and array",
        f"- data pool: {layout['dataPool']['bytes']:,} bytes with matching "
        "prefix/suffix lengths",
        f"- exact encoded target hits: "
        f"{len(report['exactEncodedTargetHits']):,}",
        "",
        "## Typed reader boundary",
        "",
        "AssetInfo fields: `" + "`, `".join(
            report["nativeEvidence"]["assetInfoFields"]
        ) + "`.",
        "",
        "Bundle fields: `" + "`, `".join(
            report["nativeEvidence"]["bundleFields"]
        ) + "`.",
        "",
        conclusion["reason"],
        "",
        report["boundary"],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--streaming-index", type=Path, default=DEFAULT_STREAMING_INDEX
    )
    parser.add_argument(
        "--persistent-index", type=Path, default=DEFAULT_PERSISTENT_INDEX
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
        "BundleManifest Story audit: "
        f"{layout['assetDictionary']['entryCount']} assets, "
        f"{layout['bundleArray']['entryCount']} bundles, "
        f"{len(report['exactEncodedTargetHits'])} target hits"
    )
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
