#!/usr/bin/env python3
"""Decode ExtendData/CompressData.bin and audit it for Story carriers.

The current file is a global pool used by ``Beyond.DataCompressManager``.
Each record stores a Brotli-compressed payload and its original byte length.
Serialized NodeCanvas BehaviourTree assets select records through
``_serializedGraphStringIndex`` when ``_enableGraphStringCompress`` is true.

This offline audit validates the complete container, decompresses every logical
record, joins pool indexes back to exact typed BehaviourTree assets, and
searches the logical JSON for Story/mission/quest/LevelScript identities.  It
is not part of ``export.bat``.

The audit requires the Python ``brotli`` module.  Normal repository builders
remain stdlib-only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    import brotli
except ImportError:  # pragma: no cover - exercised only in missing dependency envs
    brotli = None


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file,
)

DEFAULT_COMPRESS_BIN = (
    ROOT
    / "tmp"
    / "story"
    / "root_selector_compress_data"
    / "Data"
    / "ExtendData"
    / "Main"
    / "CompressData.bin"
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
DEFAULT_MONO_DIRS = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "MonoBehaviour",
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "json_by_type"
    / "MonoBehaviour",
)
DEFAULT_GAP_QUEUE = (
    ROOT / "reports" / "mission_order" / "source_story_gap_queue_CN.json"
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery" / "compress_data_story_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")

EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
BEHAVIOUR_TREE_TYPE = "NodeCanvas.BehaviourTrees.BehaviourTree"
PATH_ID_SUFFIX_RE = re.compile(r"_p([0-9A-Fa-f]{16})\.json$")
STORY_TOKEN_RE = re.compile(
    r"(?i)(?:cutscene|dlg|radio|black|sns|remotecomm|text|env)_[a-z0-9_#]+"
)
OWNER_TERM_RE = re.compile(r"(?i)\b(?:mission|quest|levelscript|story)\b")


class AuditError(RuntimeError):
    """Raised when an input cannot support a fail-closed conclusion."""


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )




def object_identity(value: Any) -> tuple[str, str, int, int]:
    if not isinstance(value, dict):
        raise AuditError("object identity is not a JSON object")
    try:
        return (
            str(value["serializedFile"]),
            str(value["source"]).replace("\\", "/"),
            int(value["sourceOffset"]),
            int(value["pathId"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError(f"incomplete object identity: {value!r}") from exc


def iter_jsonl(path: Path) -> Iterable[dict]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise AuditError(f"{path}:{line_number}: row is not an object")
            yield row


def walk_values(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_values(child, f"{path}[{index}]")
    else:
        yield path, value


def decode_compress_data(data: bytes) -> dict:
    if brotli is None:
        raise AuditError(
            "Python module 'brotli' is required for CompressData.bin decoding"
        )
    if len(data) < 8:
        raise AuditError("CompressData.bin is too short")
    count = struct.unpack_from("<I", data, 0)[0]
    if count <= 0:
        raise AuditError("CompressData.bin has no records")
    header_size = 4 + count * 4
    if header_size > len(data):
        raise AuditError("CompressData.bin offset table exceeds file size")
    offsets = list(struct.unpack_from(f"<{count}I", data, 4))
    if offsets[0] != header_size:
        raise AuditError(
            f"first record offset {offsets[0]} does not equal header {header_size}"
        )
    if offsets != sorted(set(offsets)):
        raise AuditError("record offsets are not strictly increasing")
    if offsets[-1] >= len(data):
        raise AuditError("last record offset is outside the file")

    records: list[dict] = []
    class_counts: Counter[str] = Counter()
    namespace_counts: Counter[str] = Counter()
    story_hits: list[dict] = []
    total_decompressed = 0

    for index, start in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < count else len(data)
        record = data[start:end]
        if len(record) < 8:
            raise AuditError(f"record {index}: shorter than 8-byte header")
        compressed_length, original_length = struct.unpack_from("<II", record, 0)
        payload = record[8:]
        if compressed_length != len(payload):
            raise AuditError(
                f"record {index}: compressed length {compressed_length} "
                f"does not equal payload {len(payload)}"
            )
        try:
            decoded = brotli.decompress(payload)
        except brotli.error as exc:
            raise AuditError(f"record {index}: Brotli decode failed: {exc}") from exc
        if len(decoded) != original_length:
            raise AuditError(
                f"record {index}: original length {original_length} "
                f"does not equal decoded {len(decoded)}"
            )
        if original_length % 2:
            raise AuditError(f"record {index}: UTF-16 payload has odd byte length")
        try:
            text = decoded.decode("utf-16le")
        except UnicodeDecodeError as exc:
            raise AuditError(f"record {index}: invalid UTF-16LE: {exc}") from exc
        try:
            logical = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AuditError(f"record {index}: invalid logical JSON: {exc}") from exc
        if not isinstance(logical, dict):
            raise AuditError(f"record {index}: logical JSON is not an object")
        if logical.get("type") != BEHAVIOUR_TREE_TYPE:
            raise AuditError(
                f"record {index}: unexpected logical type {logical.get('type')!r}"
            )

        record_hits = []
        record_classes = Counter()
        for value_path, value in walk_values(logical):
            if isinstance(value, str):
                if value_path.endswith(".$type") or value_path == "$.type":
                    record_classes[value] += 1
                    class_counts[value] += 1
                    namespace = (
                        "Beyond.Gameplay.AI"
                        if value.startswith("Beyond.Gameplay.AI.")
                        else value.rsplit(".", 1)[0] if "." in value else value
                    )
                    namespace_counts[namespace] += 1
                tokens = sorted(set(STORY_TOKEN_RE.findall(value)))
                owner_terms = sorted(
                    {match.group(0).lower() for match in OWNER_TERM_RE.finditer(value)}
                )
                if tokens or owner_terms:
                    record_hits.append(
                        {
                            "path": value_path,
                            "value": value,
                            "storyTokens": tokens,
                            "ownerTerms": owner_terms,
                        }
                    )
        if record_hits:
            story_hits.append({"recordIndex": index, "matches": record_hits})
        total_decompressed += len(decoded)
        records.append(
            {
                "index": index,
                "offset": start,
                "recordLength": len(record),
                "compressedLength": compressed_length,
                "originalLength": original_length,
                "decodedSha256": hashlib.sha256(decoded).hexdigest(),
                "nodeCount": len(logical.get("nodes") or []),
                "connectionCount": len(logical.get("connections") or []),
                "classCounts": dict(sorted(record_classes.items())),
                "storyHitCount": len(record_hits),
            }
        )

    return {
        "count": count,
        "headerSize": header_size,
        "totalCompressedPayloadBytes": sum(
            row["compressedLength"] for row in records
        ),
        "totalDecompressedBytes": total_decompressed,
        "records": records,
        "classCounts": dict(class_counts.most_common()),
        "namespaceCounts": dict(namespace_counts.most_common()),
        "storyHits": story_hits,
    }


def load_gap_targets(path: Path) -> set[str]:
    payload = read_json(path)
    missions = payload.get("missions") if isinstance(payload, dict) else None
    if not isinstance(missions, list):
        raise AuditError(f"{path}: missing missions list")
    targets: set[str] = set()
    for mission in missions:
        if not isinstance(mission, dict):
            continue
        for value in mission.get("actionableCoreIsolatedSceneKeys") or []:
            if isinstance(value, str) and value:
                targets.add(value)
    if not targets:
        raise AuditError(f"{path}: no actionable Story targets")
    return targets


def scan_behaviour_tree_objects(paths: tuple[Path, ...]) -> dict:
    objects: list[dict] = []
    lines_read = 0
    for path in paths:
        if not path.is_file():
            raise AuditError(f"object index does not exist: {path}")
        for row in iter_jsonl(path):
            lines_read += 1
            script = row.get("script") if isinstance(row.get("script"), dict) else {}
            if script.get("fullName") != BEHAVIOUR_TREE_TYPE:
                continue
            identity = object_identity(row.get("object"))
            if row.get("decodeStatus") != "decoded":
                raise AuditError(f"BehaviourTree object is not decoded: {identity!r}")
            objects.append(
                {
                    "identity": identity,
                    "name": str(row.get("name") or ""),
                    "indexPath": rel_path(path),
                }
            )
    if not objects:
        raise AuditError("object indexes contain no typed BehaviourTree objects")
    return {"linesRead": lines_read, "objects": objects}


def source_tail(value: str) -> str:
    normalized = str(value or "").replace("\\", "/")
    marker = "/VFS/"
    index = normalized.lower().find(marker.lower())
    return normalized[index + 1 :] if index >= 0 else normalized


def serialized_identity(payload: dict) -> tuple[str, str, int, int]:
    meta = payload.get("$animestudio")
    if not isinstance(meta, dict):
        raise AuditError("AnimeStudio JSON has no $animestudio metadata")
    try:
        return (
            str(meta["sourceFile"]),
            source_tail(str(meta["sourceOriginalPath"])),
            int(meta["sourceOffset"]),
            int(meta["pathId"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError("AnimeStudio JSON has incomplete object identity") from exc


def path_id_suffix(path_id: int) -> str:
    return f"_p{path_id & ((1 << 64) - 1):016X}.json".lower()


def find_serialized_json(
    objects: list[dict],
    mono_dirs: tuple[Path, ...],
) -> dict[tuple[str, str, int, int], Path]:
    suffixes: dict[str, set[tuple[str, str, int, int]]] = defaultdict(set)
    for row in objects:
        identity = row["identity"]
        suffixes[path_id_suffix(identity[3])].add(identity)

    candidate_paths: dict[str, list[Path]] = defaultdict(list)
    for directory in mono_dirs:
        if not directory.is_dir():
            raise AuditError(f"MonoBehaviour JSON directory does not exist: {directory}")
        with os.scandir(directory) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue
                match = PATH_ID_SUFFIX_RE.search(entry.name)
                if not match:
                    continue
                suffix = f"_p{match.group(1)}.json".lower()
                if suffix in suffixes:
                    candidate_paths[suffix].append(Path(entry.path))

    resolved: dict[tuple[str, str, int, int], Path] = {}
    for suffix, identities in suffixes.items():
        for path in candidate_paths.get(suffix, []):
            payload = read_json(path)
            identity = serialized_identity(payload)
            if identity in identities:
                if identity in resolved:
                    raise AuditError(f"duplicate AnimeStudio JSON for {identity!r}")
                resolved[identity] = path
    missing = sorted(
        row["identity"] for row in objects if row["identity"] not in resolved
    )
    if missing:
        raise AuditError(
            f"{len(missing)} typed BehaviourTree objects lack exact JSON; "
            f"first={missing[0]!r}"
        )
    return resolved


def join_serialized_consumers(
    pool_count: int,
    object_scan: dict,
    mono_dirs: tuple[Path, ...],
    gap_targets: set[str],
) -> dict:
    resolved = find_serialized_json(object_scan["objects"], mono_dirs)
    compressed: list[dict] = []
    inline: list[dict] = []
    index_consumers: dict[int, list[dict]] = defaultdict(list)
    exact_gap_hits: list[dict] = []

    for row in object_scan["objects"]:
        identity = row["identity"]
        path = resolved[identity]
        payload = read_json(path)
        enabled = payload.get("_enableGraphStringCompress")
        index = payload.get("_serializedGraphStringIndex")
        inline_json = payload.get("_serializedGraph")
        if enabled not in (0, 1) or not isinstance(index, int):
            raise AuditError(f"{path}: invalid compression selector fields")
        if not isinstance(inline_json, str):
            raise AuditError(f"{path}: _serializedGraph is not a string")
        entry = {
            "name": row["name"],
            "object": {
                "serializedFile": identity[0],
                "source": identity[1],
                "sourceOffset": identity[2],
                "pathId": identity[3],
            },
            "json": rel_path(path),
            "compressed": bool(enabled),
            "serializedGraphStringIndex": index,
            "inlineJsonLength": len(inline_json),
        }
        gap_name_hits = sorted(
            target for target in gap_targets if target == row["name"]
        )
        if gap_name_hits:
            exact_gap_hits.append({**entry, "matchedGapKeys": gap_name_hits})
        if enabled:
            if index < 0 or index >= pool_count:
                raise AuditError(f"{path}: compressed index {index} is out of range")
            if inline_json:
                raise AuditError(f"{path}: compressed graph also has inline JSON")
            compressed.append(entry)
            index_consumers[index].append(entry)
        else:
            inline.append(entry)

    missing_indexes = sorted(set(range(pool_count)) - set(index_consumers))
    shared_indexes = {
        str(index): rows
        for index, rows in sorted(index_consumers.items())
        if len(rows) > 1
    }
    return {
        "typedBehaviourTreeObjects": len(object_scan["objects"]),
        "objectIndexRowsScanned": object_scan["linesRead"],
        "compressedObjectCount": len(compressed),
        "inlineObjectCount": len(inline),
        "consumedPoolIndexCount": len(index_consumers),
        "missingPoolIndexes": missing_indexes,
        "sharedPoolIndexConsumers": shared_indexes,
        "exactActionableGapNameHits": exact_gap_hits,
        "compressedObjects": sorted(
            compressed, key=lambda row: row["serializedGraphStringIndex"]
        ),
    }


def validate_native_inputs(gameassembly: Path, metadata: Path) -> dict:
    if not gameassembly.is_file():
        raise AuditError(f"GameAssembly.dll does not exist: {gameassembly}")
    if not metadata.is_file():
        raise AuditError(f"global-metadata.dat does not exist: {metadata}")
    gameassembly_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata)
    if gameassembly_hash != EXPECTED_GAMEASSEMBLY_SHA256:
        raise AuditError(
            "GameAssembly.dll hash drifted; re-audit DataCompressManager methods"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise AuditError(
            "global-metadata.dat hash drifted; re-audit DataCompressManager methods"
        )
    return {
        "mappingId": "gameassembly-2026-07-28-data-compress-manager-v1",
        "gameAssembly": str(gameassembly.resolve()),
        "gameAssemblySha256": gameassembly_hash,
        "metadata": str(metadata.resolve()),
        "metadataSha256": metadata_hash,
        "methods": [
            {
                "name": "Beyond.DataCompressManager.Init",
                "token": "0x06000c49",
                "methodIndex": 295598,
                "va": "0x184966170",
                "finding": "loads and initializes the shipped compressed-data pool",
            },
            {
                "name": "Beyond.DataCompressManager._GetSpanByIndex",
                "token": "0x06000c54",
                "methodIndex": 295609,
                "va": "0x183115640",
                "finding": (
                    "bounds-checks the index, reads an absolute offset, then reads "
                    "compressedLength/originalLength and returns payload at +8"
                ),
            },
            {
                "name": "Beyond.DataCompressManager.GetCompressBinary",
                "token": "0x06000c4f",
                "methodIndex": 295604,
                "va": "0x186893790",
                "finding": "resolves the indexed span and calls BrotliDecoder.Decompress",
            },
            {
                "name": "Beyond.DataCompressManager.Compress",
                "token": "0x06000c58",
                "methodIndex": 295613,
                "va": "0x186893468",
                "finding": "calls BrotliEncoder.Compress for runtime-added records",
            },
        ],
    }


def build_report(
    compress_path: Path,
    object_indexes: tuple[Path, ...],
    mono_dirs: tuple[Path, ...],
    gap_queue: Path,
    gameassembly: Path,
    metadata: Path,
) -> dict:
    native = validate_native_inputs(gameassembly, metadata)
    raw = compress_path.read_bytes()
    pool = decode_compress_data(raw)
    targets = load_gap_targets(gap_queue)
    object_scan = scan_behaviour_tree_objects(object_indexes)
    consumers = join_serialized_consumers(
        pool["count"], object_scan, mono_dirs, targets
    )
    logical_story_hit_count = sum(
        len(row["matches"]) for row in pool["storyHits"]
    )
    join_complete = (
        not consumers["missingPoolIndexes"]
        and consumers["consumedPoolIndexCount"] == pool["count"]
        and consumers["compressedObjectCount"] >= pool["count"]
    )
    finding = (
        "complete_ai_behaviour_tree_pool_no_story_or_owner_carrier"
        if logical_story_hit_count == 0
        and not consumers["exactActionableGapNameHits"]
        and join_complete
        else "candidate_story_or_incomplete_consumer_surface_requires_review"
    )
    return {
        "_schema": "endfield-compress-data-story-audit-v1",
        "inputs": {
            "compressData": rel_path(compress_path),
            "compressDataSize": len(raw),
            "compressDataSha256": hashlib.sha256(raw).hexdigest(),
            "objectIndexes": [
                {"path": rel_path(path), "sha256": sha256_file(path)}
                for path in object_indexes
            ],
            "monoBehaviourJsonDirs": [rel_path(path) for path in mono_dirs],
            "gapQueue": rel_path(gap_queue),
            "gapQueueSha256": sha256_file(gap_queue),
            "actionableGapKeyCount": len(targets),
            "brotliModuleVersion": getattr(brotli, "__version__", "unknown"),
        },
        "nativeEvidence": native,
        "layout": {
            "header": "recordCount:uint32 + absoluteOffsets:uint32[recordCount]",
            "record": (
                "compressedLength:uint32 + originalLength:uint32 + "
                "brotliPayload[compressedLength]"
            ),
            "logicalEncoding": "UTF-16LE JSON",
        },
        "summary": {
            "recordCount": pool["count"],
            "headerSize": pool["headerSize"],
            "totalCompressedPayloadBytes": pool["totalCompressedPayloadBytes"],
            "totalDecompressedBytes": pool["totalDecompressedBytes"],
            "logicalType": BEHAVIOUR_TREE_TYPE,
            "logicalStoryOrOwnerHitCount": logical_story_hit_count,
            "typedBehaviourTreeObjects": consumers["typedBehaviourTreeObjects"],
            "compressedBehaviourTreeObjects": consumers["compressedObjectCount"],
            "inlineBehaviourTreeObjects": consumers["inlineObjectCount"],
            "consumedPoolIndexCount": consumers["consumedPoolIndexCount"],
            "missingPoolIndexCount": len(consumers["missingPoolIndexes"]),
            "sharedPoolIndexCount": len(
                consumers["sharedPoolIndexConsumers"]
            ),
            "exactActionableGapNameHitCount": len(
                consumers["exactActionableGapNameHits"]
            ),
            "finding": finding,
        },
        "namespaceCounts": pool["namespaceCounts"],
        "classCounts": pool["classCounts"],
        "records": pool["records"],
        "logicalStoryHits": pool["storyHits"],
        "consumerJoin": consumers,
        "evidencePolicy": {
            "accepted": (
                "Complete offset/length validation, successful Brotli decode, "
                "exact original-length match, UTF-16LE JSON parse, typed logical "
                "BehaviourTree identity, and exact serialized-object join through "
                "_enableGraphStringCompress/_serializedGraphStringIndex."
            ),
            "finding": (
                "CompressData.bin is the compressed JSON pool for AI NodeCanvas "
                "BehaviourTree assets. It is not a Story selector or mission-owner "
                "registry on the reviewed build."
            ),
            "notProved": (
                "This does not classify other ExtendData files, future builds, "
                "runtime-added compressed records, server state, or indirect "
                "selectors outside this exact current pool."
            ),
        },
    }


def markdown(report: dict) -> str:
    summary = report["summary"]
    top_namespaces = list(report["namespaceCounts"].items())[:10]
    lines = [
        "# CompressData Story audit",
        "",
        f"- Container records: **{summary['recordCount']:,}**",
        f"- Decompressed logical bytes: **{summary['totalDecompressedBytes']:,}**",
        f"- Logical type: `{summary['logicalType']}`",
        (
            "- Typed serialized BehaviourTrees: "
            f"**{summary['typedBehaviourTreeObjects']:,}** "
            f"({summary['compressedBehaviourTreeObjects']:,} compressed / "
            f"{summary['inlineBehaviourTreeObjects']:,} inline)"
        ),
        (
            "- Pool index join: "
            f"**{summary['consumedPoolIndexCount']:,}/{summary['recordCount']:,}**, "
            f"{summary['missingPoolIndexCount']} missing, "
            f"{summary['sharedPoolIndexCount']} shared by multiple assets"
        ),
        (
            "- Logical Story/owner hits: "
            f"**{summary['logicalStoryOrOwnerHitCount']:,}**"
        ),
        (
            "- Exact actionable gap-name hits on carrier assets: "
            f"**{summary['exactActionableGapNameHitCount']:,}**"
        ),
        f"- Finding: `{summary['finding']}`",
        "",
        "## Validated layout",
        "",
        f"- Header: `{report['layout']['header']}`",
        f"- Record: `{report['layout']['record']}`",
        f"- Logical encoding: `{report['layout']['logicalEncoding']}`",
        "",
        "## Logical class namespaces",
        "",
        "| Namespace | Occurrences |",
        "|---|---:|",
    ]
    for name, count in top_namespaces:
        lines.append(f"| `{name}` | {count:,} |")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            report["evidencePolicy"]["accepted"],
            "",
            report["evidencePolicy"]["finding"],
            "",
            report["evidencePolicy"]["notProved"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compress-data", type=Path, default=DEFAULT_COMPRESS_BIN)
    parser.add_argument("--object-index", type=Path, action="append")
    parser.add_argument("--mono-dir", type=Path, action="append")
    parser.add_argument("--gap-queue", type=Path, default=DEFAULT_GAP_QUEUE)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.compress_data.resolve(),
        tuple(
            path.resolve()
            for path in (args.object_index or list(DEFAULT_OBJECT_INDEXES))
        ),
        tuple(path.resolve() for path in (args.mono_dir or list(DEFAULT_MONO_DIRS))),
        args.gap_queue.resolve(),
        args.gameassembly.resolve(),
        args.metadata.resolve(),
    )
    write_json(args.out.resolve(), report)
    markdown_path = args.markdown.resolve()
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown(report), encoding="utf-8")
    print(
        "[compress-data-story] "
        f"{report['summary']['recordCount']} records / "
        f"{report['summary']['logicalStoryOrOwnerHitCount']} logical Story hits / "
        f"{report['summary']['finding']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
