"""Bind AnimeStudio HIRC structural audits to the current authenticated VFS set."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTER = ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_LEDGER = ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
DEFAULT_CLI = ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
DEFAULT_OUTPUT = ROOT / "reports/animestudio/hirc_action_current_latest.json"
DEFAULT_TYPE02_OUTPUT = ROOT / "reports/animestudio/hirc_type02_prefix_current_latest.json"
DEFAULT_TYPE04_OUTPUT = ROOT / "reports/animestudio/hirc_type04_u32_vector_current_latest.json"
DEFAULT_TYPE02_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type02_body_current_latest.json"
DEFAULT_TEMP_AUDIT = ROOT / "tmp/audio/hirc_action_current/audio_audit.json"
INPUT_SET_RE = re.compile(r"^[0-9A-F]{64}$")
HIRC_OBJECT_ID_BYTES = 4
TYPE04_FRAME_FIELDS = (
    "exactEntryCount",
    "count",
    "exact",
    "unsupported",
    "failed",
    "ambiguous",
    "bodyBytes",
    "candidatePrefixBytes",
    "unsupportedCandidatePrefixBytes",
    "exactCursorBytes",
    "opaqueTailBytes",
    "failedBodyBytes",
    "candidateEntryCount",
)
# Families the shared node frame reads on every body, and the one it reads only on
# some. A lane that does not use the node frame supplies its own.
SHARED_NODE_FRAME_SELECTOR_FAMILIES = (
    "groupAFlag_",
    "groupBFlag_",
    "groupESelector_",
    "groupFSelector_",
)
SHARED_NODE_FRAME_CONDITIONAL_SELECTORS = ("groupEBranch_",)
SHARED_NODE_FRAME_RESIDUALS = (
    "group B element width: no body of any framed type carries a nonempty vector",
    "group E selector predicate: selector 0x01 disproves a bit-0 rule, but selector "
    "0x02 is still unobserved, so bit-1-only and both-bits-set tie",
    "group A slot split: one corpus object separates a shared mask byte plus six-byte "
    "slots from no mask byte plus seven-byte slots",
    "group E branch 2 is accepted on the strength of a single corpus object and has no "
    "fixture; branch 3 beside it is fenced as unsupported",
    "group F selector bits other than 0x08 gate no observed payload, and several "
    "selector values occur only a handful of times",
    "group A and group B flag bytes gate nothing in this frame",
    "the fixed six-byte group G block is consumed without internal structure",
    "group H state element width: every state in every shipped lane carries exactly "
    "one element, so the corpus these reports publish cannot distinguish the counted "
    "state from a fixed twelve-byte one. The only non-degenerate witness is numeric "
    "type 0x09, which is not a shipped lane, and a fixed twelve-byte state followed by "
    "a separately gated six-byte structure is not excluded",
    "the group I key is consumed by extent only; its value is unnamed, and the "
    "five-byte cap plus 32-bit range are inherited from the type 0x03 Action reader "
    "rather than proven here -- see the published groupIKeyWidth_* histogram for the "
    "widths this corpus actually witnesses",
)

TYPE02_BODY_FRAME_FIELDS = (
    "count",
    "exact",
    "unsupported",
    "failed",
    "ambiguous",
    "bodyBytes",
    "exactCursorBytes",
    "nonExactBodyBytes",
)
TYPE02_BODY_RANGE_FIELDS = ("minExactBodyBytes", "maxExactBodyBytes")
# 14-byte source prefix, two flag/count pairs, nine anonymous scalars, two empty
# bundles, two empty selectors, the fixed six-byte block, an empty directory and
# an empty entry count.
TYPE02_BODY_MINIMUM_FRAME_BYTES = 45
# The same node groups without a source prefix, plus an empty four-byte child count.
# The fixed head, the list-count byte and the two closing bytes. This is both the
# smallest body that can frame and the per-body constant in the closed-form total,
# because everything else in this layout is counted: the two uses are the same
# quantity by construction, not a coincidence to be split apart.
TYPE22_BODY_MINIMUM_FRAME_BYTES = 4
TYPE22_BODY_PROPERTY_BYTES = 5
# Numeric type 0x16 ends with the node frame's group I structure verbatim, so the
# group I residuals apply to it and the rest of the node frame's do not.
TYPE22_BODY_RESIDUALS = (
    "the counted key/value block is consumed by extent only: keys are one byte, "
    "values four, and neither is named or interpreted here",
    "one anonymous byte separates that block from the group I structure and gates "
    "nothing observed",
    "the group I key is consumed by extent only, and every key in this type is one "
    "byte wide, so this corpus does not widen the inherited five-byte cap either",
    "the twelve-byte group I points are consumed whole; no internal split is claimed",
)

TYPE14_BODY_MINIMUM_FRAME_BYTES = 24
TYPE14_BODY_FIXED_HEAD_BYTES = 21
TYPE14_BODY_OPTIONAL_BLOCK_BYTES = 20
TYPE14_BODY_ELEMENT_BYTES = 12
TYPE14_BODY_ENTRY_HEADER_BYTES = 3
# Numeric type 0x0E is framed on its own terms, so none of the node frame's open
# widths are statements about it. What stays open here is different and shorter.
TYPE14_BODY_RESIDUALS = (
    "the twenty-one byte fixed head and the twenty-byte optional block are consumed "
    "by extent only; no field inside either is separated or named",
    "the optional-block flag is a byte with exactly two observed values, so the "
    "branch is a two-way choice witnessed by the corpus rather than a decoded "
    "predicate, and the long branch rests on 164 of 24,145 bodies",
    "searching for a start offset that consumes a body exactly does not by itself "
    "determine the prefix: 6,218 bodies admit two such offsets. The flag byte is "
    "what removes that ambiguity, so this framing depends on the flag rule holding "
    "and not merely on the list parsing cleanly",
    "the twelve-byte element is consumed whole; its internal split is not "
    "established here, only the published trailing-word histogram",
    "the two closing bytes read as zero in every body, so a terminator and an "
    "always-empty counted list are indistinguishable in this corpus",
)

TYPE07_BODY_MINIMUM_FRAME_BYTES = 35
# Seven-bit continuation groups capped at five bytes. The cap and the 32-bit range
# are inherited from the type 0x03 Action reader, not proven by any framed corpus.
HIRC_VARIABLE_SIZE_MAX_BYTES = 5
# The 31-byte node frame with no source prefix, a fixed 24-byte block, an empty
# four-byte reference count and an empty two-byte record count.
TYPE05_BODY_MINIMUM_FRAME_BYTES = 61
# The node frame, a fixed ten-byte header and three empty four-byte counts.
TYPE06_BODY_MINIMUM_FRAME_BYTES = 53
DEFAULT_TYPE05_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type05_body_current_latest.json"
DEFAULT_REFERENCE_OUTPUT = ROOT / "reports/animestudio/hirc_reference_graph_current_latest.json"
DEFAULT_TYPE06_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type06_body_current_latest.json"
REFERENCE_CENSUS_FIELDS = (
    "references",
    "resolvedSameBank",
    "unresolvedInBank",
    "selfReferences",
    "targetsWithMultipleReferrers",
    "duplicateObjectIds",
    "referencesToDuplicateIds",
    "candidateWords",
    "candidateWordsMatchingAnObject",
    "referenceCycleOrFeedingNodes",
    "distinctDuplicateObjectIds",
)
# Depth is a maximum across banks, not a sum, so it is aggregated separately.
REFERENCE_DEPTH_FIELD = "maximumReferenceDepth"
DEFAULT_TYPE07_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type07_body_current_latest.json"
DEFAULT_TYPE14_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type14_body_current_latest.json"
DEFAULT_TYPE22_BODY_OUTPUT = ROOT / "reports/animestudio/hirc_type22_body_current_latest.json"
AUDIO_BLOCKS = frozenset(
    {
        "InitAudio",
        "Audio",
        "AuditAudio",
        "HotfixAudio",
        "AudioChinese",
        "AudioEnglish",
        "AudioJapanese",
        "AudioKorean",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _load_json_with_sha256(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON report root must be an object: {path}")
    return value, sha256_bytes(raw)


def _capture_cli_output_closure(cli_path: Path) -> dict[str, Any]:
    root = cli_path.resolve().parent
    if not root.is_dir():
        raise ValueError(f"AnimeStudio CLI output directory is missing: {root}")
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )
    files: list[dict[str, Any]] = []
    cli_relative = cli_path.resolve().relative_to(root).as_posix()
    for path in paths:
        relative = path.relative_to(root).as_posix()
        before = path.stat()
        digest = sha256_file(path)
        after = path.stat()
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise ValueError(f"AnimeStudio CLI output file changed while hashing: {path}")
        files.append({"path": relative, "length": after.st_size, "sha256": digest})
    if not any(row["path"].casefold() == cli_relative.casefold() for row in files):
        raise ValueError(f"AnimeStudio CLI apphost is absent from its output closure: {cli_path}")
    manifest_bytes = json.dumps(
        files,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "root": str(root),
        "manifestFormat": "relative-path-length-sha256-v1",
        "fileCount": len(files),
        "manifestSha256": sha256_bytes(manifest_bytes),
        "files": files,
    }


def load_current_outer(
    outer_path: Path,
    ledger_path: Path,
    expected_input_set_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = expected_input_set_sha256.upper()
    if INPUT_SET_RE.fullmatch(expected) is None:
        raise ValueError("expected inputSetSha256 must be 64 hexadecimal characters")
    if not outer_path.is_file():
        raise ValueError(f"outer VFS report is missing: {outer_path}")
    if not ledger_path.is_file():
        raise ValueError(f"outer VFS ledger is missing: {ledger_path}")

    outer = json.loads(outer_path.read_text(encoding="utf-8"))
    if outer.get("format") != "animestudio-vfs-boundary-audit" or outer.get("schemaVersion") != 1:
        raise ValueError(
            "outer VFS report schema mismatch: expected animestudio-vfs-boundary-audit/1"
        )
    if outer.get("inputSetSha256") != expected:
        raise ValueError(
            "outer VFS input-set mismatch: "
            f"expected={expected} actual={outer.get('inputSetSha256')}"
        )

    summary = outer.get("summary") or {}
    if (
        summary.get("fullAuditPassed") is not True
        or summary.get("allAvailableBoundaryVerified") is not True
        or int(summary.get("failureCount") or 0) != 0
    ):
        raise ValueError(
            "outer VFS audit did not pass: "
            f"fullAuditPassed={summary.get('fullAuditPassed')} "
            f"allAvailableBoundaryVerified={summary.get('allAvailableBoundaryVerified')} "
            f"failureCount={summary.get('failureCount')}"
        )

    expected_ledger_sha = str((outer.get("publication") or {}).get("ledgerSha256") or "").upper()
    actual_ledger_sha = sha256_file(ledger_path)
    if not expected_ledger_sha or actual_ledger_sha != expected_ledger_sha:
        raise ValueError(
            "outer ledger publication hash mismatch: "
            f"expected={expected_ledger_sha or '<missing>'} actual={actual_ledger_sha}"
        )

    fingerprints = outer.get("sourceFingerprints") or []
    if not fingerprints:
        raise ValueError("outer VFS report has no physical .blc source fingerprints")
    fingerprint_failures = []
    for row in fingerprints:
        source = Path(str(row.get("path") or ""))
        expected_sha = str(row.get("sha256") or "").upper()
        if not source.is_file():
            fingerprint_failures.append(
                {"path": str(source), "expectedSha256": expected_sha, "actual": "missing"}
            )
            continue
        actual_sha = sha256_file(source)
        if actual_sha != expected_sha:
            fingerprint_failures.append(
                {"path": str(source), "expectedSha256": expected_sha, "actualSha256": actual_sha}
            )
    if fingerprint_failures:
        first = fingerprint_failures[0]
        raise ValueError(
            "outer .blc source fingerprints changed after the boundary audit: "
            + json.dumps(first, sort_keys=True)
        )

    for field in ("primaryAssets", "fallbackAssets"):
        root = Path(str(outer.get(field) or ""))
        if not root.is_dir():
            raise ValueError(f"outer VFS {field} root is missing: {root}")
    return outer, {
        "ledgerSha256": actual_ledger_sha,
        "outerReportSha256": sha256_file(outer_path),
        "sourceFingerprintCount": len(fingerprints),
        "sourceFingerprintsMatched": len(fingerprints),
    }


def collect_current_audio_files(
    ledger_path: Path,
    input_set_sha256: str,
    expected_file_rows: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    input_set = input_set_sha256.upper()
    available: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    file_row_count = 0
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"outer ledger row {line_number} is invalid JSON: {exc}") from exc
            if row.get("recordType") != "file":
                continue
            file_row_count += 1
            if str(row.get("inputSetSha256") or "").upper() != input_set:
                raise ValueError(
                    "outer ledger row input-set mismatch: "
                    f"row={line_number} expected={input_set} actual={row.get('inputSetSha256')}"
                )
            block = row.get("blockName")
            path = row.get("virtualPath") or row.get("fileName")
            if block not in AUDIO_BLOCKS:
                continue
            boundary_status = str(row.get("boundaryStatus") or "")
            if boundary_status.startswith("excluded_"):
                excluded.append(
                    {
                        "block": block,
                        "path": path,
                        "status": boundary_status,
                        "chunkFile": row.get("chunkFile"),
                    }
                )
            if not isinstance(path, str) or not path.lower().endswith(".pck"):
                continue
            if row.get("boundaryStatus") == "boundary_verified":
                try:
                    actual_bytes = int(row["actualBytesRead"])
                    declared_bytes = int(row["length"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"audio VFS row has invalid byte counts: {block}:{path}") from exc
                if actual_bytes != declared_bytes:
                    raise ValueError(
                        "audio VFS row byte-count mismatch: "
                        f"{block}:{path} expected={declared_bytes} actual={actual_bytes}"
                    )
                if str(row.get("declaredFileDataMd5LittleEndianHex") or "").upper() != str(
                    row.get("recomputedFileDataMd5") or ""
                ).upper():
                    raise ValueError(f"audio VFS row FileDataMd5 mismatch: {block}:{path}")
                chunk_file = row.get("chunkFile")
                source_path = row.get("physicalChunkPath")
                file_data_md5 = str(row.get("recomputedFileDataMd5") or "").upper()
                if not isinstance(chunk_file, str) or not chunk_file:
                    raise ValueError(f"audio VFS row has no physical chunk identity: {block}:{path}")
                if not isinstance(source_path, str) or not source_path:
                    raise ValueError(f"audio VFS row has no physical source path: {block}:{path}")
                if re.fullmatch(r"[0-9A-F]{32}", file_data_md5) is None:
                    raise ValueError(f"audio VFS row has no verified FileDataMd5: {block}:{path}")
                available.append(
                    {
                        "block": block,
                        "path": path,
                        "declaredBytes": int(row["length"]),
                        "fileDataMd5": file_data_md5,
                        "chunk": chunk_file,
                        "source": source_path,
                    }
                )
    if file_row_count != expected_file_rows:
        raise ValueError(
            f"outer ledger file-row count mismatch: expected={expected_file_rows} actual={file_row_count}"
        )
    if not available:
        raise ValueError("outer ledger has no current available audio PCK files")
    return available, excluded, file_row_count


def _file_identity(row: dict[str, Any]) -> tuple[str, str, int, str, str, str]:
    return (
        str(row.get("block") or row.get("blockName") or ""),
        str(row.get("path") or row.get("virtualPath") or row.get("fileName") or ""),
        int(row.get("declaredBytes") or row.get("length") or 0),
        str(row.get("verifiedFileDataMd5") or row.get("fileDataMd5") or "").upper(),
        str(row.get("chunk") or row.get("chunkFile") or "").replace("\\", "/").casefold(),
        str(row.get("source") or row.get("physicalChunkPath") or "")
        .replace("\\", "/")
        .rstrip("/")
        .casefold(),
    )


def _outer_cli_fingerprint(outer: dict[str, Any], cli_path: Path, cli_sha256: str) -> dict[str, Any]:
    identity = str(cli_path.resolve()).replace("\\", "/").casefold()
    rows = [
        row
        for row in outer.get("buildFingerprints", [])
        if isinstance(row, dict)
        and isinstance(row.get("path"), str)
        and str(Path(row["path"]).resolve()).replace("\\", "/").casefold() == identity
    ]
    if len(rows) != 1:
        raise ValueError(
            "outer VFS buildFingerprints must contain one selected AnimeStudio CLI path: "
            f"path={cli_path} matchCount={len(rows)}"
        )
    try:
        expected_length = int(rows[0]["length"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"outer VFS AnimeStudio CLI fingerprint has an invalid length: {cli_path}") from exc
    expected_sha = str(rows[0].get("sha256") or "").upper()
    if re.fullmatch(r"[0-9A-F]{64}", expected_sha) is None:
        raise ValueError(f"outer VFS AnimeStudio CLI fingerprint has an invalid SHA-256: {cli_path}")
    current_length = cli_path.stat().st_size
    return {
        "path": str(cli_path),
        "outerAuditLength": expected_length,
        "outerAuditSha256": expected_sha,
        "currentLength": current_length,
        "currentSha256": cli_sha256,
        "matchesOuterAudit": current_length == expected_length and cli_sha256 == expected_sha,
    }


def _read_frame_metrics(frame: dict[str, Any], label: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for key in ("count", "exact", "unsupported", "failed", "ambiguous", "bodyBytes", "exactCursorBytes"):
        if key not in frame:
            raise ValueError(f"type 0x03 frame result has no {key}: {label}")
        try:
            value = int(frame[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"type 0x03 frame result has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x03 frame result has negative {key}: {label}")
        metrics[key] = value
    if metrics["exactCursorBytes"] > metrics["bodyBytes"]:
        raise ValueError(f"type 0x03 exact cursor bytes exceed body bytes: {label}")

    for key in ("operationCounts", "failureCategories"):
        counts = frame.get(key)
        if not isinstance(counts, dict):
            raise ValueError(f"type 0x03 frame result has invalid {key}: {label}")
        normalized: dict[str, int] = {}
        for name, raw_count in counts.items():
            try:
                count = int(raw_count)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"type 0x03 frame result has invalid {key} entry: {label}") from exc
            if count < 0:
                raise ValueError(f"type 0x03 frame result has negative {key} entry: {label}")
            if count:
                normalized[str(name)] = count
        metrics[key] = dict(sorted(normalized.items()))
    if metrics["count"] != sum(metrics[key] for key in ("exact", "unsupported", "failed", "ambiguous")):
        raise ValueError(f"type 0x03 outcome partition mismatch: {label}")
    return metrics


def _read_type02_prefix_metrics(
    frame: Any,
    type_stats: Any,
    expected_count: int,
    label: str,
) -> dict[str, Any]:
    if expected_count < 0:
        raise ValueError(f"negative type 0x02 object count: {label}")
    if frame is None and expected_count == 0:
        frame = {
            "count": 0,
            "prefixBytes": 0,
            "opaqueTailBytes": 0,
            "minOpaqueTailBytes": 0,
            "maxOpaqueTailBytes": 0,
            "pluginTypeCounts": {},
        }
    if not isinstance(frame, dict):
        raise ValueError(f"missing type 0x02 source-prefix result: {label}")
    if type_stats is None and expected_count == 0:
        type_stats = {"count": 0, "declaredLengthBytes": 0}
    if not isinstance(type_stats, dict):
        raise ValueError(f"missing type 0x02 object-length stats: {label}")

    metrics: dict[str, Any] = {}
    for key in ("count", "prefixBytes", "opaqueTailBytes", "minOpaqueTailBytes", "maxOpaqueTailBytes"):
        try:
            value = int(frame[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x02 source-prefix result has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x02 source-prefix result has negative {key}: {label}")
        metrics[key] = value
    if metrics["count"] != expected_count:
        raise ValueError(
            f"type 0x02 source-prefix count mismatch: {label} "
            f"objects={expected_count} framed={metrics['count']}"
        )
    try:
        stats_count = int(type_stats.get("count", 0))
        declared_length_bytes = int(type_stats.get("declaredLengthBytes", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"type 0x02 object-length stats are invalid: {label}") from exc
    if stats_count != expected_count:
        raise ValueError(
            f"type 0x02 object-stat count mismatch: {label} "
            f"objects={expected_count} stats={stats_count}"
        )
    object_id_bytes = HIRC_OBJECT_ID_BYTES * expected_count
    if declared_length_bytes < object_id_bytes:
        raise ValueError(
            f"type 0x02 declared object bytes are smaller than object ids: {label} "
            f"declared={declared_length_bytes} idBytes={object_id_bytes}"
        )
    metrics["bodyBytes"] = declared_length_bytes - object_id_bytes
    if metrics["prefixBytes"] + metrics["opaqueTailBytes"] != metrics["bodyBytes"]:
        raise ValueError(
            f"type 0x02 prefix-plus-tail body accounting mismatch: {label} "
            f"prefix={metrics['prefixBytes']} opaqueTail={metrics['opaqueTailBytes']} "
            f"body={metrics['bodyBytes']} declaredObjectBytes={declared_length_bytes}"
        )
    if expected_count == 0:
        if any(metrics[key] for key in ("prefixBytes", "opaqueTailBytes", "minOpaqueTailBytes", "maxOpaqueTailBytes")):
            raise ValueError(f"empty type 0x02 source-prefix result has nonzero bytes: {label}")
    else:
        if metrics["prefixBytes"] < 14 * expected_count:
            raise ValueError(
                f"type 0x02 source-prefix bytes fall below the 14-byte minimum: {label} "
                f"prefix={metrics['prefixBytes']} objects={expected_count}"
            )
        if metrics["minOpaqueTailBytes"] > metrics["maxOpaqueTailBytes"]:
            raise ValueError(f"type 0x02 opaque-tail minimum exceeds maximum: {label}")
        if not (
            metrics["minOpaqueTailBytes"] * expected_count
            <= metrics["opaqueTailBytes"]
            <= metrics["maxOpaqueTailBytes"] * expected_count
        ):
            raise ValueError(f"type 0x02 opaque-tail range does not bound its total: {label}")

    raw_plugin_counts = frame.get("pluginTypeCounts")
    if not isinstance(raw_plugin_counts, dict):
        raise ValueError(f"type 0x02 pluginTypeCounts is invalid: {label}")
    plugin_counts: dict[str, int] = {}
    for raw_plugin_type, raw_count in raw_plugin_counts.items():
        plugin_type = str(raw_plugin_type).lower()
        if re.fullmatch(r"0x[0-9a-f]+", plugin_type) is None:
            raise ValueError(f"type 0x02 plugin type is not numeric: {label} value={raw_plugin_type!r}")
        try:
            count = int(raw_count)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"type 0x02 plugin count is invalid: {label} type={plugin_type}") from exc
        if count < 0:
            raise ValueError(f"type 0x02 plugin count is negative: {label} type={plugin_type}")
        if count:
            plugin_counts[plugin_type] = count
    if sum(plugin_counts.values()) != expected_count:
        raise ValueError(
            f"type 0x02 plugin-type count mismatch: {label} "
            f"objects={expected_count} pluginCounts={sum(plugin_counts.values())}"
        )
    metrics["pluginTypeCounts"] = dict(sorted(plugin_counts.items()))
    raw_plugin_ids = frame.get("pluginIdCounts")
    if not isinstance(raw_plugin_ids, dict):
        raise ValueError(f"type 0x02 pluginIdCounts is invalid: {label}")
    plugin_ids = {str(name): int(count) for name, count in raw_plugin_ids.items()}
    if sum(plugin_ids.values()) != expected_count:
        raise ValueError(
            f"type 0x02 plugin-id count mismatch: {label} "
            f"objects={expected_count} pluginIdCounts={sum(plugin_ids.values())}"
        )
    metrics["pluginIdCounts"] = dict(sorted(plugin_ids.items()))
    return metrics


def _histogram_label_value(name: str, prefix: str, label: str) -> int:
    suffix = name[len(prefix):]
    if not suffix.isdigit():
        raise ValueError(
            f"histogram key is not a plain width: {label} key={name!r}"
        )
    return int(suffix)


def _read_hirc_body_metrics(
    frame: Any,
    type_stats: Any,
    expected_count: int,
    label: str,
    *,
    type_label: str,
    minimum_frame_bytes: int,
    element_widths: dict[str, int],
    unconditional_selectors: tuple[str, ...] = SHARED_NODE_FRAME_SELECTOR_FAMILIES,
    conditional_selectors: tuple[str, ...] = SHARED_NODE_FRAME_CONDITIONAL_SELECTORS,
    fixed_bytes_per_body: int | None = None,
    selector_families_matching_groups: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_count < 0:
        raise ValueError(f"negative {type_label} object count: {label}")
    if frame is None and expected_count == 0:
        frame = {key: 0 for key in TYPE02_BODY_FRAME_FIELDS + TYPE02_BODY_RANGE_FIELDS}
        frame.update(
            {
                "groupCounts": {},
                "selectorCounts": {},
                "failureCategories": {},
                "unsupportedCategories": {},
                "nonExactExamples": [],
            }
        )
    if not isinstance(frame, dict):
        raise ValueError(f"missing {type_label} body-frame result: {label}")
    if type_stats is None and expected_count == 0:
        type_stats = {"count": 0, "declaredLengthBytes": 0}
    if not isinstance(type_stats, dict):
        raise ValueError(f"missing {type_label} object-length stats: {label}")

    metrics: dict[str, Any] = {}
    for key in TYPE02_BODY_FRAME_FIELDS + TYPE02_BODY_RANGE_FIELDS:
        try:
            value = int(frame[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{type_label} body-frame result has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"{type_label} body-frame result has negative {key}: {label}")
        metrics[key] = value

    if metrics["count"] != expected_count:
        raise ValueError(
            f"{type_label} body-frame count mismatch: {label} "
            f"objects={expected_count} framed={metrics['count']}"
        )
    if metrics["count"] != sum(
        metrics[key] for key in ("exact", "unsupported", "failed", "ambiguous")
    ):
        raise ValueError(f"{type_label} body outcome partition mismatch: {label}")
    if metrics["ambiguous"] != 0:
        raise ValueError(f"unexpected ambiguous {type_label} body-frame result: {label}")
    if metrics["exactCursorBytes"] + metrics["nonExactBodyBytes"] != metrics["bodyBytes"]:
        raise ValueError(
            f"{type_label} exact/non-exact body accounting mismatch: {label} "
            f"exact={metrics['exactCursorBytes']} nonExact={metrics['nonExactBodyBytes']} "
            f"body={metrics['bodyBytes']}"
        )
    if metrics["exact"] == 0:
        if metrics["exactCursorBytes"] or any(
            metrics[key] for key in TYPE02_BODY_RANGE_FIELDS
        ):
            raise ValueError(f"{type_label} exact cursor bytes exist without exact bodies: {label}")
    else:
        # The smallest possible frame is a real per-object bound, unlike the mean.
        if metrics["minExactBodyBytes"] < minimum_frame_bytes:
            raise ValueError(
                f"{type_label} exact body falls below the minimum frame: {label} "
                f"min={metrics['minExactBodyBytes']} "
                f"required={minimum_frame_bytes}"
            )
        if metrics["minExactBodyBytes"] > metrics["maxExactBodyBytes"]:
            raise ValueError(f"{type_label} exact-length minimum exceeds maximum: {label}")
        if not (
            metrics["minExactBodyBytes"] * metrics["exact"]
            <= metrics["exactCursorBytes"]
            <= metrics["maxExactBodyBytes"] * metrics["exact"]
        ):
            raise ValueError(f"{type_label} exact-length range does not bound its total: {label}")
    if metrics["exact"] + metrics["unsupported"] + metrics["failed"] == 0 and metrics["bodyBytes"]:
        raise ValueError(f"{type_label} body bytes exist without framed bodies: {label}")

    try:
        stats_count = int(type_stats.get("count", 0))
        declared_length_bytes = int(type_stats.get("declaredLengthBytes", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{type_label} object-length stats are invalid: {label}") from exc
    if stats_count != expected_count:
        raise ValueError(
            f"{type_label} body object-stat count mismatch: {label} "
            f"objects={expected_count} stats={stats_count}"
        )
    object_id_bytes = HIRC_OBJECT_ID_BYTES * expected_count
    if declared_length_bytes < object_id_bytes:
        raise ValueError(
            f"{type_label} declared object bytes are smaller than object ids: {label} "
            f"declared={declared_length_bytes} idBytes={object_id_bytes}"
        )
    declared_body_bytes = declared_length_bytes - object_id_bytes
    if metrics["bodyBytes"] != declared_body_bytes:
        raise ValueError(
            f"{type_label} body bytes differ from declared HIRC object bodies: {label} "
            f"framed={metrics['bodyBytes']} declared={declared_body_bytes}"
        )

    for key, expected_category_count in (
        ("failureCategories", metrics["failed"]),
        ("unsupportedCategories", metrics["unsupported"]),
    ):
        raw_counts = frame.get(key)
        if not isinstance(raw_counts, dict):
            raise ValueError(f"{type_label} body-frame result has invalid {key}: {label}")
        normalized: dict[str, int] = {}
        for name, raw_count in raw_counts.items():
            try:
                count = int(raw_count)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{type_label} body-frame result has invalid {key} entry: {label}") from exc
            if count < 0:
                raise ValueError(f"{type_label} body-frame result has negative {key} entry: {label}")
            if count:
                normalized[str(name)] = count
        if sum(normalized.values()) != expected_category_count:
            raise ValueError(
                f"{type_label} body {key} do not match outcome counts: {label} "
                f"categories={sum(normalized.values())} outcomes={expected_category_count}"
            )
        metrics[key] = dict(sorted(normalized.items()))

    for key in ("groupCounts", "selectorCounts"):
        raw_counts = frame.get(key)
        if not isinstance(raw_counts, dict):
            raise ValueError(f"{type_label} body-frame result has invalid {key}: {label}")
        normalized = {}
        for name, raw_count in raw_counts.items():
            try:
                count = int(raw_count)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{type_label} body-frame result has invalid {key} entry: {label}") from exc
            if count < 0:
                raise ValueError(f"{type_label} body-frame result has negative {key} entry: {label}")
            normalized[str(name)] = count
        metrics[key] = dict(sorted(normalized.items()))
    # Every exactly framed body contributes exactly one observation to each
    # unconditional selector family; the group E branch family is conditional.
    for prefix in unconditional_selectors:
        selector_total = sum(
            count for name, count in metrics["selectorCounts"].items() if name.startswith(prefix)
        )
        if selector_total != metrics["exact"]:
            raise ValueError(
                f"{type_label} selector family {prefix} does not match exact bodies: {label} "
                f"selectors={selector_total} exact={metrics['exact']}"
            )
    # Some selector families are per-element, not per-body: one observation for each
    # counted thing. Those must reconcile against their own group counter, or a
    # miscounted run would leave the histogram silently disagreeing with it.
    for prefix, group_name in (selector_families_matching_groups or {}).items():
        observed = sum(
            count for name, count in metrics["selectorCounts"].items() if name.startswith(prefix)
        )
        expected = metrics["groupCounts"].get(group_name, 0)
        if observed != expected:
            raise ValueError(
                f"{type_label} selector family {prefix} does not match {group_name}: {label} "
                f"selectors={observed} {group_name}={expected}"
            )
    for prefix in conditional_selectors:
        branch_total = sum(
            count for name, count in metrics["selectorCounts"].items() if name.startswith(prefix)
        )
        if branch_total > metrics["exact"]:
            raise ValueError(
                f"{type_label} conditional selector family {prefix} exceeds exact bodies: {label} "
                f"selectors={branch_total} exact={metrics['exact']}"
            )

    # The anonymous inventories are the one place a reader-side regression could grow
    # unnoticed, so bound every counter that a variable-length read can inflate.
    groups = metrics["groupCounts"]
    entries = groups.get("groupIEntries", 0)
    key_bytes = groups.get("groupIKeyBytes", 0)
    if not entries <= key_bytes <= HIRC_VARIABLE_SIZE_MAX_BYTES * entries:
        raise ValueError(
            f"{type_label} group I key bytes are not bounded by their entry count: {label} "
            f"entries={entries} keyBytes={key_bytes} "
            f"maxPerEntry={HIRC_VARIABLE_SIZE_MAX_BYTES}"
        )
    over_widths = sum(
        count for name, count in metrics["selectorCounts"].items()
        if name.startswith("groupHStateWidth_over_")
    )
    if over_widths:
        raise ValueError(
            f"{type_label} group H state width histogram is bucketed, so its element "
            f"total cannot be reconciled: {label} bucketed={over_widths}"
        )
    state_width_total = sum(
        count for name, count in metrics["selectorCounts"].items()
        if name.startswith("groupHStateWidth_")
    )
    states = groups.get("groupHStates", 0)
    if state_width_total != states:
        raise ValueError(
            f"{type_label} group H state width histogram does not match its state count: "
            f"{label} widths={state_width_total} states={states}"
        )
    state_widths = {
        name: count
        for name, count in metrics["selectorCounts"].items()
        if name.startswith("groupHStateWidth_") and not name.startswith("groupHStateWidth_over_")
    }
    state_width_bytes = 0
    for name, count in state_widths.items():
        width = _histogram_label_value(name, "groupHStateWidth_", label)
        # A state is a four-byte key, a two-byte count and whole six-byte elements.
        if width < 6 or (width - 6) % 6:
            raise ValueError(
                f"{type_label} group H state width is not a key plus whole elements: "
                f"{label} width={width}"
            )
        state_width_bytes += width * count
    expected_state_bytes = 6 * states + 6 * groups.get("groupHStateElements", 0)
    if state_width_bytes != expected_state_bytes:
        raise ValueError(
            f"{type_label} group H state width histogram does not sum to its element "
            f"total: {label} histogram={state_width_bytes} expected={expected_state_bytes}"
        )
    width_total = sum(
        count for name, count in metrics["selectorCounts"].items()
        if name.startswith("groupIKeyWidth_")
    )
    if width_total != entries:
        raise ValueError(
            f"{type_label} group I key width histogram does not match its entry count: {label} "
            f"widths={width_total} entries={entries}"
        )
    width_bytes = 0
    for name, count in metrics["selectorCounts"].items():
        if not name.startswith("groupIKeyWidth_"):
            continue
        width = _histogram_label_value(name, "groupIKeyWidth_", label)
        if not 1 <= width <= HIRC_VARIABLE_SIZE_MAX_BYTES:
            raise ValueError(
                f"{type_label} group I key width is outside the reader's range: "
                f"{label} width={width} max={HIRC_VARIABLE_SIZE_MAX_BYTES}"
            )
        width_bytes += width * count
    if width_bytes != key_bytes:
        raise ValueError(
            f"{type_label} group I key width histogram does not sum to its byte total: {label} "
            f"histogram={width_bytes} keyBytes={key_bytes}"
        )
    # Every counted element must fit inside the bodies that were actually framed.
    element_bytes = sum(
        width * groups.get(name, 0) for name, width in element_widths.items()
    )
    unbounded = sorted(
        name
        for name, count in groups.items()
        if count and name.endswith("Entries") and name not in element_widths
    )
    if unbounded:
        raise ValueError(
            f"{type_label} counts anonymous elements with no declared byte width: "
            f"{label} counters={unbounded}"
        )
    if element_bytes > metrics["exactCursorBytes"]:
        raise ValueError(
            f"{type_label} anonymous element bytes exceed the framed bodies: {label} "
            f"elements={element_bytes} exactCursor={metrics['exactCursorBytes']}"
        )
    if fixed_bytes_per_body is not None:
        # A closed body: its framed bytes are the fixed part of every body plus the
        # declared width of everything counted. Equality, not containment.
        predicted = fixed_bytes_per_body * metrics["exact"] + element_bytes
        if predicted != metrics["exactCursorBytes"]:
            raise ValueError(
                f"{type_label} framed bytes do not equal their closed-form total: {label} "
                f"predicted={predicted} framed={metrics['exactCursorBytes']}"
            )

    examples = frame.get("nonExactExamples")
    if not isinstance(examples, list):
        raise ValueError(f"{type_label} body-frame result has invalid nonExactExamples: {label}")
    metrics["nonExactExamples"] = examples
    return metrics


def _read_type04_u32_vector_metrics(
    frame: Any,
    type_stats: Any,
    expected_count: int,
    label: str,
) -> dict[str, Any]:
    if expected_count < 0:
        raise ValueError(f"negative type 0x04 object count: {label}")
    if frame is None and expected_count == 0:
        frame = {
            "count": 0,
            "exact": 0,
            "unsupported": 0,
            "failed": 0,
            "ambiguous": 0,
            "bodyBytes": 0,
            "candidatePrefixBytes": 0,
            "unsupportedCandidatePrefixBytes": 0,
            "exactCursorBytes": 0,
            "opaqueTailBytes": 0,
            "failedBodyBytes": 0,
            "candidateEntryCount": 0,
            "failureCategories": {},
            "unsupportedCategories": {},
            "nonExactExamples": [],
        }
    if not isinstance(frame, dict):
        raise ValueError(f"missing type 0x04 candidate-vector result: {label}")
    if type_stats is None and expected_count == 0:
        type_stats = {"count": 0, "declaredLengthBytes": 0}
    if not isinstance(type_stats, dict):
        raise ValueError(f"missing type 0x04 object-length stats: {label}")

    metrics: dict[str, Any] = {}
    for key in TYPE04_FRAME_FIELDS:
        try:
            value = int(frame[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x04 candidate-vector result has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x04 candidate-vector result has negative {key}: {label}")
        metrics[key] = value

    if metrics["count"] != expected_count:
        raise ValueError(
            f"type 0x04 candidate-vector count mismatch: {label} "
            f"objects={expected_count} framed={metrics['count']}"
        )
    if metrics["count"] != sum(
        metrics[key] for key in ("exact", "unsupported", "failed", "ambiguous")
    ):
        raise ValueError(f"type 0x04 outcome partition mismatch: {label}")
    if metrics["ambiguous"] != 0:
        raise ValueError(f"unexpected ambiguous type 0x04 candidate-vector result: {label}")
    if metrics["exactCursorBytes"] < metrics["exact"]:
        raise ValueError(f"type 0x04 exact candidate bodies are shorter than their count bytes: {label}")
    if metrics["unsupported"] == 0:
        if metrics["unsupportedCandidatePrefixBytes"] or metrics["opaqueTailBytes"]:
            raise ValueError(f"type 0x04 unsupported bytes exist without unsupported bodies: {label}")
    elif (
        metrics["unsupportedCandidatePrefixBytes"] < metrics["unsupported"]
        or metrics["opaqueTailBytes"] < metrics["unsupported"]
    ):
        raise ValueError(f"type 0x04 unsupported bodies lack a count prefix or opaque tail: {label}")
    if metrics["failed"] == 0 and metrics["failedBodyBytes"] != 0:
        raise ValueError(f"type 0x04 failed-body bytes exist without failed bodies: {label}")
    if metrics["exactCursorBytes"] > metrics["candidatePrefixBytes"]:
        raise ValueError(f"type 0x04 exact cursor bytes exceed candidate prefix bytes: {label}")
    if (
        metrics["unsupportedCandidatePrefixBytes"] + metrics["exactCursorBytes"]
        != metrics["candidatePrefixBytes"]
    ):
        raise ValueError(f"type 0x04 exact and unsupported candidate-prefix bytes do not reconcile: {label}")
    if (
        metrics["candidatePrefixBytes"]
        + metrics["opaqueTailBytes"]
        + metrics["failedBodyBytes"]
        != metrics["bodyBytes"]
    ):
        raise ValueError(
            f"type 0x04 candidate-prefix/tail/failed body accounting mismatch: {label} "
            f"prefix={metrics['candidatePrefixBytes']} opaqueTail={metrics['opaqueTailBytes']} "
            f"failedBody={metrics['failedBodyBytes']} body={metrics['bodyBytes']}"
        )
    candidate_frame_count = metrics["exact"] + metrics["unsupported"]
    if metrics["candidatePrefixBytes"] != candidate_frame_count + 4 * metrics["candidateEntryCount"]:
        raise ValueError(
            f"type 0x04 candidate prefix does not match count-byte/u32-entry arithmetic: {label} "
            f"prefix={metrics['candidatePrefixBytes']} frames={candidate_frame_count} "
            f"entries={metrics['candidateEntryCount']}"
        )

    try:
        stats_count = int(type_stats.get("count", 0))
        declared_length_bytes = int(type_stats.get("declaredLengthBytes", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"type 0x04 object-length stats are invalid: {label}") from exc
    if stats_count != expected_count:
        raise ValueError(
            f"type 0x04 object-stat count mismatch: {label} objects={expected_count} stats={stats_count}"
        )
    object_id_bytes = HIRC_OBJECT_ID_BYTES * expected_count
    if declared_length_bytes < object_id_bytes:
        raise ValueError(
            f"type 0x04 declared object bytes are smaller than object ids: {label} "
            f"declared={declared_length_bytes} idBytes={object_id_bytes}"
        )
    declared_body_bytes = declared_length_bytes - object_id_bytes
    if metrics["bodyBytes"] != declared_body_bytes:
        raise ValueError(
            f"type 0x04 body bytes differ from declared HIRC object bodies: {label} "
            f"framed={metrics['bodyBytes']} declared={declared_body_bytes}"
        )

    categories: dict[str, dict[str, int]] = {}
    for key, expected_category_count in (
        ("failureCategories", metrics["failed"]),
        ("unsupportedCategories", metrics["unsupported"]),
    ):
        raw_counts = frame.get(key)
        if not isinstance(raw_counts, dict):
            raise ValueError(f"type 0x04 candidate-vector result has invalid {key}: {label}")
        normalized: dict[str, int] = {}
        for name, raw_count in raw_counts.items():
            try:
                count = int(raw_count)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"type 0x04 candidate-vector result has invalid {key} entry: {label}") from exc
            if count < 0:
                raise ValueError(f"type 0x04 candidate-vector result has negative {key} entry: {label}")
            if count:
                normalized[str(name)] = count
        if sum(normalized.values()) != expected_category_count:
            raise ValueError(
                f"type 0x04 {key} do not match outcome counts: {label} "
                f"categories={sum(normalized.values())} outcomes={expected_category_count}"
            )
        categories[key] = dict(sorted(normalized.items()))
    metrics.update(categories)
    examples = frame.get("nonExactExamples")
    if not isinstance(examples, list):
        raise ValueError(f"type 0x04 candidate-vector result has invalid nonExactExamples: {label}")
    metrics["nonExactExamples"] = examples
    return metrics


class _BodyLanePackage:
    """One package's view of a body lane, plus the per-bank totals it must match."""

    def __init__(self, lane: "_BodyLane", metrics: dict[str, Any]) -> None:
        self.lane = lane
        self.metrics = metrics
        self.bank_totals: Counter[str] = Counter()
        self.bank_groups: Counter[str] = Counter()
        self.bank_selectors: Counter[str] = Counter()
        self.bank_failures: Counter[str] = Counter()
        self.bank_unsupported: Counter[str] = Counter()
        self.bank_mins: list[int] = []
        self.bank_maxes: list[int] = []

    def add_bank(self, bank: dict[str, Any], bank_type_stats: Any, bank_name: str, version: Any) -> None:
        bank_count = int((bank_type_stats or {}).get("count") or 0)
        metrics = self.lane.read(bank, bank_type_stats, bank_count, bank_name)
        for key in TYPE02_BODY_FRAME_FIELDS:
            self.bank_totals[key] += metrics[key]
        self.bank_groups.update(metrics["groupCounts"])
        self.bank_selectors.update(metrics["selectorCounts"])
        self.bank_failures.update(metrics["failureCategories"])
        self.bank_unsupported.update(metrics["unsupportedCategories"])
        if metrics["exact"]:
            self.bank_mins.append(metrics["minExactBodyBytes"])
            self.bank_maxes.append(metrics["maxExactBodyBytes"])
        if bank_count:
            self.lane.banks_with_objects += 1
            self.lane.bank_versions[str(version) if version is not None else "unknown"] += 1

    def reconcile(self, package_label: str) -> None:
        label = self.lane.type_label
        for key in TYPE02_BODY_FRAME_FIELDS:
            if self.bank_totals[key] != self.metrics[key]:
                raise ValueError(
                    f"per-bank/package {label} body-frame total mismatch: "
                    f"{package_label} field={key} banks={self.bank_totals[key]} "
                    f"package={self.metrics[key]}"
                )
        if dict(sorted(self.bank_groups.items())) != self.metrics["groupCounts"]:
            raise ValueError(f"per-bank/package {label} group inventory mismatch: {package_label}")
        if dict(sorted(self.bank_selectors.items())) != self.metrics["selectorCounts"]:
            raise ValueError(f"per-bank/package {label} selector inventory mismatch: {package_label}")
        if dict(sorted(self.bank_failures.items())) != self.metrics["failureCategories"]:
            raise ValueError(f"per-bank/package {label} body failure categories mismatch: {package_label}")
        if dict(sorted(self.bank_unsupported.items())) != self.metrics["unsupportedCategories"]:
            raise ValueError(f"per-bank/package {label} body unsupported categories mismatch: {package_label}")
        bank_min = min(self.bank_mins) if self.bank_mins else 0
        bank_max = max(self.bank_maxes) if self.bank_maxes else 0
        if (
            bank_min != self.metrics["minExactBodyBytes"]
            or bank_max != self.metrics["maxExactBodyBytes"]
        ):
            raise ValueError(
                f"per-bank/package {label} exact-length range mismatch: {package_label} "
                f"banks={bank_min}..{bank_max} "
                f"package={self.metrics['minExactBodyBytes']}.."
                f"{self.metrics['maxExactBodyBytes']}"
            )


class _BodyLane:
    """Accumulates one numeric HIRC type's whole-body census across the corpus.

    Every lane shares the same node frame, so they must also share the same guards,
    the same reconciliation, and the same residual list.
    """

    def __init__(
        self,
        type_key: str,
        frame_key: str,
        minimum_frame_bytes: int,
        claim: str,
        layout: str,
        extra_non_claims: tuple[str, ...] = (),
        extra_residuals: tuple[str, ...] = (),
        extra_element_widths: dict[str, int] | None = None,
        base_residuals: tuple[str, ...] = SHARED_NODE_FRAME_RESIDUALS,
        base_element_widths: dict[str, int] | None = None,
        unconditional_selectors: tuple[str, ...] = SHARED_NODE_FRAME_SELECTOR_FAMILIES,
        conditional_selectors: tuple[str, ...] = SHARED_NODE_FRAME_CONDITIONAL_SELECTORS,
        fixed_bytes_per_body: int | None = None,
        selector_families_matching_groups: dict[str, str] | None = None,
        upstream_note: str = "",
        shared_note: str = "",
    ) -> None:
        self.type_key = type_key
        self.type_label = f"type {type_key}"
        self.frame_key = frame_key
        self.minimum_frame_bytes = minimum_frame_bytes
        self.claim = claim
        # The layout sentence is the one thing that tells a reader what the framer
        # actually consumes, so every lane must carry its own.
        self.layout = layout
        self.non_claims = SHARED_NODE_FRAME_NON_CLAIMS + extra_non_claims
        self.extra_residuals = extra_residuals
        # A lane that does not share the node frame must not inherit its residuals:
        # they are statements about groups this body never contains.
        self.base_residuals = base_residuals
        self.unconditional_selectors = unconditional_selectors
        self.conditional_selectors = conditional_selectors
        self.fixed_bytes_per_body = fixed_bytes_per_body
        self.selector_families_matching_groups = selector_families_matching_groups or {}
        self.closed_form_total = (
            None
            if fixed_bytes_per_body is None
            else (
                f"framed body bytes equal {fixed_bytes_per_body} bytes a body plus "
                + ", ".join(
                    f"{width} a `{name}`"
                    for name, width in sorted((base_element_widths or {}).items())
                )
                + "; this is an equality, so a miscounted element or entry breaks it"
            )
        )
        self.element_widths = dict(
            SHARED_NODE_FRAME_ELEMENT_WIDTHS if base_element_widths is None else base_element_widths
        )
        self.element_widths.update(extra_element_widths or {})
        self.upstream_note = upstream_note
        self.shared_note = shared_note
        self.totals: Counter[str] = Counter()
        self.groups: Counter[str] = Counter()
        self.selectors: Counter[str] = Counter()
        self.failures: Counter[str] = Counter()
        self.unsupported: Counter[str] = Counter()
        self.counts_by_block: Counter[str] = Counter()
        self.bank_versions: Counter[str] = Counter()
        self.packages_with_objects = 0
        self.banks_with_objects = 0
        self.min_exact: int | None = None
        self.max_exact = 0
        self.examples: list[dict[str, Any]] = []

    def read(self, container: dict[str, Any], type_stats: Any, expected_count: int, label: str):
        return _read_hirc_body_metrics(
            container.get(self.frame_key),
            type_stats,
            expected_count,
            label,
            type_label=self.type_label,
            minimum_frame_bytes=self.minimum_frame_bytes,
            element_widths=self.element_widths,
            unconditional_selectors=self.unconditional_selectors,
            conditional_selectors=self.conditional_selectors,
            fixed_bytes_per_body=self.fixed_bytes_per_body,
            selector_families_matching_groups=self.selector_families_matching_groups,
        )

    def add_package(
        self,
        package: dict[str, Any],
        type_stats: Any,
        expected_count: int,
        package_label: str,
        block: Any,
        path: Any,
    ) -> _BodyLanePackage:
        metrics = self.read(package, type_stats, expected_count, package_label)
        for key in TYPE02_BODY_FRAME_FIELDS:
            self.totals[key] += metrics[key]
        self.groups.update(metrics["groupCounts"])
        self.selectors.update(metrics["selectorCounts"])
        self.failures.update(metrics["failureCategories"])
        self.unsupported.update(metrics["unsupportedCategories"])
        if expected_count:
            self.packages_with_objects += 1
            self.counts_by_block[str(block)] += expected_count
        if metrics["exact"]:
            if self.min_exact is None or metrics["minExactBodyBytes"] < self.min_exact:
                self.min_exact = metrics["minExactBodyBytes"]
            self.max_exact = max(self.max_exact, metrics["maxExactBodyBytes"])
        for example in metrics["nonExactExamples"]:
            if len(self.examples) >= 32:
                break
            self.examples.append({"block": block, "package": path, **example})
        return _BodyLanePackage(self, metrics)

    def publish(self) -> dict[str, Any]:
        count = int(self.totals["count"])
        exact = int(self.totals["exact"])
        published = {
            "count": count,
            "exact": exact,
            "unsupported": int(self.totals["unsupported"]),
            "failed": int(self.totals["failed"]),
            "ambiguous": int(self.totals["ambiguous"]),
            "packagesWithObjects": self.packages_with_objects,
            "banksWithObjects": self.banks_with_objects,
            "bodyBytes": int(self.totals["bodyBytes"]),
            "exactCursorBytes": int(self.totals["exactCursorBytes"]),
            "nonExactBodyBytes": int(self.totals["nonExactBodyBytes"]),
            "minExactBodyBytes": self.min_exact or 0,
            "maxExactBodyBytes": self.max_exact,
            "minimumPossibleFrameBytes": self.minimum_frame_bytes,
            "frameClosure": (
                "no-objects" if count == 0
                else "all-bodies-exact" if exact == count
                else "incomplete"
            ),
            "closedFormTotal": self.closed_form_total,
        "bodyAccounting": (
                "framedBodyBytesEqualDeclaredHircObjectBodiesMinusObjectIds; "
                "every exact body ends at its declared body end"
            ),
            "anonymousGroupCounts": dict(sorted(self.groups.items())),
            "anonymousSelectorCounts": dict(sorted(self.selectors.items())),
            "failureCategories": dict(sorted(self.failures.items())),
            "unsupportedCategories": dict(sorted(self.unsupported.items())),
            "nonExactExamples": self.examples,
            "objectCountsByBlock": dict(sorted(self.counts_by_block.items())),
            "bankVersionCounts": dict(sorted(self.bank_versions.items())),
            "unresolvedWidths": list(self.base_residuals) + list(self.extra_residuals),
        }
        published["frameLayout"] = self.layout
        if self.shared_note:
            published["sharedNodeFrame"] = self.shared_note
        if self.upstream_note:
            published["upstreamAbortsNotCountedHere"] = self.upstream_note
        return published


# Byte weight of every anonymous element a lane counts, so the gate can bound the
# inventories a variable-length read could inflate. A lane adds its own terminal
# vectors; forgetting one leaves that counter unbounded, so keep them together
# with the lane declaration rather than in a single hand-maintained sum.
# Widths are per-element minimums, so the sum stays a lower bound on the bytes a
# lane must have consumed. Group B is deliberately absent: its element width is
# unresolved, and the framer holds any nonempty vector unsupported, so a nonempty
# group B can never reach an exact body's inventory.
SHARED_NODE_FRAME_ELEMENT_WIDTHS = {
    "groupAEntries": 6,
    "groupCEntries": 5,
    "groupDEntries": 9,
    "groupEVertices": 16,
    "groupEItems": 20,
    # A state is a four-byte key plus its own counted six-byte elements, so the
    # state itself is at least six bytes and each element adds six more.
    "groupHStates": 6,
    "groupHStateElements": 6,
    "groupIEntries": 14,
    "groupIPoints": 12,
}
SHARED_NODE_FRAME_NOTE = (
    "the nine anonymous groups are the same ones proven on type 0x02 bodies"
)
SHARED_NODE_FRAME_NON_CLAIMS = (
    "serialized field ownership or field names",
    "group, selector, key, or value meanings",
    "parent, child, bus, or effect object identity",
    "container membership, selection, or ordering behaviour",
    "runtime execution, event selection, or audibility",
)


NODE_FRAME_LAYOUT = (
    "the nine anonymous node groups: two flag/count slot vectors, two parallel "
    "one-byte-key/value bundles with four- and eight-byte values, a selector-directed "
    "vector pair, a selector-directed fixed block, a fixed six-byte block, a nested "
    "property/group/state directory, and a counted entry list whose entries carry one "
    "variable-size key and counted twelve-byte points"
)


def _build_body_lanes() -> dict[str, "_BodyLane"]:
    """One lane per numeric HIRC type whose body opens with the shared node frame."""
    return {
        "0x02": _BodyLane(
            "0x02",
            "hircType02BodyFrame",
            TYPE02_BODY_MINIMUM_FRAME_BYTES,
            claim=(
                "numeric HIRC type 0x02 object bodies are consumed by a bounded source "
                "prefix plus the shared anonymous node frame, reaching the declared body "
                "end when status is exact"
            ),
            layout=(
                "The reader consumes the bounded 14-byte source prefix, its optional "
                "length-prefixed plug-in parameter range, and then " + NODE_FRAME_LAYOUT + "."
            ),
            extra_non_claims=(
                "source, effect, bus, or parent object identity",
                "cross-object or cross-bank relationships",
                "physical media placement or source-plugin semantics",
            ),
            upstream_note=(
                "a malformed 14-byte source prefix or plugin parameter range throws in "
                "the preceding prefix census and aborts the whole package, so it is "
                "never counted as a failed body by this lane"
            ),
        ),
        "0x16": _BodyLane(
            "0x16",
            "hircType22BodyFrame",
            TYPE22_BODY_MINIMUM_FRAME_BYTES,
            "numeric type 0x16 bodies are consumed whole, from the first byte to the "
            "declared object-body end",
            layout=(
                "The reader consumes a byte-counted block of properties -- that many "
                "one-byte keys followed by that many four-byte values, as two parallel "
                "runs rather than interleaved pairs -- then one anonymous byte, then the "
                "node frame's group I structure verbatim. Group I is not re-derived here: "
                "it is the same structure the shipped reader already frames byte-exactly "
                "on numeric types 0x02, 0x05, 0x06 and 0x07, which is why this type closed "
                "with almost no new guessing."
            ),
            extra_non_claims=(
                "that a property key names anything, or that its value is a number of "
                "any particular kind",
                "that this type's group I entries mean the same thing as another type's",
            ),
            base_residuals=TYPE22_BODY_RESIDUALS,
            base_element_widths={
                "propertyEntries": TYPE22_BODY_PROPERTY_BYTES,
                "groupIEntries": 14,
                "groupIPoints": 12,
            },
            unconditional_selectors=(),
            conditional_selectors=(),
            # Both families are per-element: one observation per counted property and
            # per group I entry, so each must equal its own counter.
            selector_families_matching_groups={
                "propertyKey_": "propertyEntries",
                "groupIKeyWidth_": "groupIEntries",
            },
            shared_note=(
                "This lane shares only group I with the node frame, not the whole frame, "
                "so it carries the group I residuals and none of the others"
            ),
        ),
        "0x0E": _BodyLane(
            "0x0E",
            "hircType14BodyFrame",
            TYPE14_BODY_MINIMUM_FRAME_BYTES,
            "numeric type 0x0E bodies are consumed whole, from the first byte to the "
            "declared object-body end, without the shared node frame",
            layout=(
                "The reader consumes a fixed twenty-one byte head, then a twenty-byte "
                "optional block present only when the second byte of the body is 1, then "
                "a byte-counted list whose entries each carry one selector byte, a "
                "sixteen-bit element count, and that many twelve-byte elements, and "
                "finally two closing bytes that must read as zero. The branch is decided "
                "by a byte rather than by searching for an offset that happens to fit: "
                "that byte is 0 or 1 in every body and predicts the prefix length in "
                "every body, and any other value fails closed."
            ),
            extra_non_claims=(
                "that the twelve-byte elements are points, curves, or samples of anything",
                "that the optional block and the flag byte that selects it are related "
                "to each other in any way beyond the flag deciding whether it is present",
                "an ordering, interpolation, or evaluation rule over the elements",
            ),
            base_residuals=TYPE14_BODY_RESIDUALS,
            base_element_widths={
                "listElements": TYPE14_BODY_ELEMENT_BYTES,
                "optionalBlock": TYPE14_BODY_OPTIONAL_BLOCK_BYTES,
                # Each entry's own header: one selector byte and a sixteen-bit count.
                "listEntries": TYPE14_BODY_ENTRY_HEADER_BYTES,
            },
            # Fixed head, list count byte and the two closing bytes: 21 + 1 + 2.
            fixed_bytes_per_body=TYPE14_BODY_MINIMUM_FRAME_BYTES,
            # Both bytes are read on every body, so both must be observed once per
            # exactly framed body. The optional block itself is conditional.
            unconditional_selectors=("headByte_", "optionalBlockFlag_"),
            conditional_selectors=(),
            shared_note=(
                "This lane does not share the node frame with the other body lanes, so "
                "its residual list is its own"
            ),
        ),
        "0x07": _BodyLane(
            "0x07",
            "hircType07BodyFrame",
            TYPE07_BODY_MINIMUM_FRAME_BYTES,
            claim=(
                "numeric HIRC type 0x07 object bodies are consumed by the shared anonymous "
                "node frame followed by one counted four-byte reference vector, reaching "
                "the declared body end when status is exact"
            ),
            layout=(
                "The reader consumes " + NODE_FRAME_LAYOUT + ", and then one counted vector of "
                "four-byte anonymous references."
            ),
            extra_residuals=(
                "the terminal counted vector holds four-byte anonymous references with "
                "no proven target namespace",
            ),
            extra_element_widths={"childEntries": 4},
            upstream_note=(
                "type 0x07 has no preceding per-object census, so unlike type 0x02 every "
                "malformed body reaches this lane as a counted failure"
            ),
            shared_note=SHARED_NODE_FRAME_NOTE,
        ),
        "0x06": _BodyLane(
            "0x06",
            "hircType06BodyFrame",
            TYPE06_BODY_MINIMUM_FRAME_BYTES,
            claim=(
                "numeric HIRC type 0x06 object bodies are consumed by the shared anonymous "
                "node frame, a fixed ten-byte opaque header, one counted four-byte "
                "reference vector, one counted group list each carrying its own counted "
                "reference vector, and one counted fourteen-byte record vector, reaching "
                "the declared body end when status is exact"
            ),
            layout=(
                "The reader consumes " + NODE_FRAME_LAYOUT + ", a fixed ten-byte opaque "
                "header, one counted vector of four-byte anonymous references, one counted "
                "list of groups each holding a four-byte key and its own counted reference "
                "vector, and one counted vector of fourteen-byte records that each open "
                "with a reference."
            ),
            extra_residuals=(
                "the fixed ten-byte header carries two id-shaped words that match no object "
                "in their bank; they are consumed opaquely and never offered to the "
                "reference join",
                "each group's four-byte key likewise matches no bank object and stays opaque",
                "the ten bytes after each record's leading reference are consumed without "
                "internal structure",
            ),
            extra_element_widths={
                "childEntries": 4,
                "groupEntries": 8,
                "groupItemEntries": 4,
                "recordEntries": 14,
            },
            upstream_note=(
                "type 0x06 has no preceding per-object census, so every malformed body "
                "reaches this lane as a counted failure"
            ),
            shared_note=SHARED_NODE_FRAME_NOTE,
        ),
        "0x05": _BodyLane(
            "0x05",
            "hircType05BodyFrame",
            TYPE05_BODY_MINIMUM_FRAME_BYTES,
            claim=(
                "numeric HIRC type 0x05 object bodies are consumed by the shared anonymous "
                "node frame, a fixed 24-byte opaque block, one counted four-byte reference "
                "vector and one counted eight-byte record vector, reaching the declared "
                "body end when status is exact"
            ),
            layout=(
                "The reader consumes " + NODE_FRAME_LAYOUT + ", a fixed twenty-four-byte opaque "
                "block, one counted vector of four-byte anonymous references and one "
                "counted vector of eight-byte anonymous records."
            ),
            extra_residuals=(
                "the fixed 24-byte block after the node frame is consumed without internal "
                "structure",
                "the two terminal vectors are counted independently; the census publishes "
                "referenceRecordCountMismatch, the number of bodies whose two counts "
                "differ, so neither vector is a projection of the other. Their element "
                "contents and any relationship between them are unproven",
            ),
            extra_element_widths={"referenceEntries": 4, "recordEntries": 8},
            upstream_note=(
                "type 0x05 has no preceding per-object census, so every malformed body "
                "reaches this lane as a counted failure"
            ),
            shared_note=SHARED_NODE_FRAME_NOTE,
        ),
    }


def body_lane_corpus_is_closed(corpus: dict[str, Any]) -> bool:
    """Return whether a body lane consumed the whole current corpus.

    Anything else -- a failed body, an unsupported body, or a single unaccounted
    byte -- is a regression a person has to resolve, so the caller must refuse to
    publish a `complete` report or a zero exit code for it.
    """
    return (
        corpus.get("frameClosure") == "all-bodies-exact"
        and int(corpus.get("count") or 0) == int(corpus.get("exact") or 0)
        and int(corpus.get("unsupported") or 0) == 0
        and int(corpus.get("failed") or 0) == 0
        and int(corpus.get("ambiguous") or 0) == 0
        and int(corpus.get("nonExactBodyBytes") or 0) == 0
    )


def aggregate_current_hirc_actions(
    outer: dict[str, Any],
    expected_files: list[dict[str, Any]],
    excluded_files: list[dict[str, Any]],
    audio_audit: dict[str, Any],
) -> dict[str, Any]:
    primary = str(outer.get("primaryAssets") or "")
    fallback = str(outer.get("fallbackAssets") or "")
    if audio_audit.get("streamingAssets") != primary or audio_audit.get("fallbackAssets") != fallback:
        raise ValueError(
            "AKPK audit roots differ from the authenticated outer view: "
            f"expected={primary}|{fallback} actual={audio_audit.get('streamingAssets')}|{audio_audit.get('fallbackAssets')}"
        )

    audio_summary = audio_audit.get("summary") or {}
    rows = audio_audit.get("rows") or []
    verified_rows = [row for row in rows if row.get("status") == "verified"]
    observed_identities = Counter(_file_identity(row) for row in verified_rows)
    expected_identities = Counter(_file_identity(row) for row in expected_files)
    if observed_identities != expected_identities:
        missing = list((expected_identities - observed_identities).items())[:4]
        extra = list((observed_identities - expected_identities).items())[:4]
        raise ValueError(
            "AKPK verified package identities do not match current outer ledger: "
            f"missing={missing} extra={extra}"
        )
    expected_packages = len(expected_files)
    if (
        int(audio_summary.get("packages", -1)) != expected_packages
        or int(audio_summary.get("verified", -1)) != expected_packages
        or int(audio_summary.get("failures", -1)) != 0
        or int(audio_summary.get("missingBlocks", -1)) != 0
    ):
        raise ValueError(
            "AKPK current package gate failed: "
            f"expectedPackages={expected_packages} summary={json.dumps(audio_summary, sort_keys=True)}"
        )

    expected_excluded_statuses: dict[str, str] = {}
    expected_excluded_file_counts: Counter[str] = Counter()
    expected_excluded_chunks: dict[str, set[str]] = {}
    for row in excluded_files:
        block = str(row.get("block") or "")
        status = str(row.get("status") or "")
        if not block or not status.startswith("excluded_"):
            raise ValueError(f"outer ledger has an invalid conditional-exclusion row: {row}")
        previous_status = expected_excluded_statuses.setdefault(block, status)
        if previous_status != status:
            raise ValueError(
                f"outer ledger has contradictory exclusion statuses for {block}: "
                f"{previous_status} vs {status}"
            )
        expected_excluded_file_counts[block] += 1
        chunk_file = row.get("chunkFile")
        if not isinstance(chunk_file, str) or not chunk_file:
            raise ValueError(f"outer ledger has no excluded chunk identity for {block}")
        expected_excluded_chunks.setdefault(block, set()).add(chunk_file.casefold())

    excluded_rows = [
        row
        for row in rows
        if str(row.get("status") or "").startswith("excluded_")
    ]
    expected_excluded_pairs = Counter((block, status) for block, status in expected_excluded_statuses.items())
    observed_excluded_pairs = Counter(
        (str(row.get("block") or ""), str(row.get("status") or ""))
        for row in excluded_rows
    )
    if observed_excluded_pairs != expected_excluded_pairs:
        raise ValueError(
            "AKPK conditional-exclusion identity mismatch: "
            f"outer={sorted(expected_excluded_pairs.items())} "
            f"audit={sorted(observed_excluded_pairs.items())}"
        )
    if len(rows) != len(verified_rows) + len(excluded_rows):
        raise ValueError("AKPK audit contains a nonterminal or unclassified row")
    for row in excluded_rows:
        block = str(row.get("block") or "")
        actual_chunks = int(row.get("declaredChunks", -1))
        actual_files = int(row.get("declaredFiles", -1))
        if row.get("source") != "missing_both":
            raise ValueError(f"AKPK exclusion was not terminally missing from both roots: {block}")
        if (
            actual_chunks != len(expected_excluded_chunks.get(block, set()))
            or actual_files != expected_excluded_file_counts.get(block, 0)
        ):
            raise ValueError(
                "AKPK conditional-exclusion multiplicity mismatch: "
                f"block={block} expectedFiles={expected_excluded_file_counts.get(block, 0)} "
                f"actualFiles={actual_files} expectedChunks={len(expected_excluded_chunks.get(block, set()))} "
                f"actualChunks={actual_chunks}"
            )
    if int(audio_summary.get("excluded", -1)) != len(excluded_rows):
        raise ValueError(
            "AKPK conditional-exclusion summary mismatch: "
            f"rows={len(excluded_rows)} summary={audio_summary.get('excluded')}"
        )

    totals: Counter[str] = Counter()
    operation_counts: Counter[str] = Counter()
    non_exact_categories: Counter[str] = Counter()
    non_exact_examples: list[dict[str, Any]] = []
    bank_version_counts: Counter[str] = Counter()
    package_type03_counts: Counter[str] = Counter()
    type02_totals: Counter[str] = Counter()
    type02_plugin_counts: Counter[str] = Counter()
    type02_plugin_ids: Counter[str] = Counter()
    type02_package_counts_by_block: Counter[str] = Counter()
    type02_bank_version_counts: Counter[str] = Counter()
    type02_packages_with_objects = 0
    type02_banks_with_objects = 0
    type02_min_opaque_tail: int | None = None
    type02_max_opaque_tail = 0
    type04_totals: Counter[str] = Counter()
    type04_failure_categories: Counter[str] = Counter()
    type04_unsupported_categories: Counter[str] = Counter()
    type04_package_counts_by_block: Counter[str] = Counter()
    type04_bank_version_counts: Counter[str] = Counter()
    type04_packages_with_objects = 0
    type04_banks_with_objects = 0
    type04_non_exact_examples: list[dict[str, Any]] = []
    body_lanes = _build_body_lanes()
    type09_totals: Counter[str] = Counter()
    type09_failures: Counter[str] = Counter()
    type09_flags: Counter[str] = Counter()
    type17_totals: Counter[str] = Counter()
    type17_failures: Counter[str] = Counter()
    type17_reasons: Counter[str] = Counter()
    type17_by_type: Counter[str] = Counter()
    type08_totals: Counter[str] = Counter()
    type11_totals: Counter[str] = Counter()
    type11_plugins: Counter[str] = Counter()
    type11_streams: Counter[str] = Counter()
    type11_record_counts: Counter[str] = Counter()
    music_head_totals: Counter[str] = Counter()
    music_head_shapes: Counter[str] = Counter()
    music_head_by_type: Counter[str] = Counter()
    music_head_offsets: Counter[str] = Counter()
    music_head_discriminants: Counter[str] = Counter()
    reference_totals: Counter[str] = Counter()
    reference_edges: Counter[str] = Counter()
    reference_objects: Counter[str] = Counter()
    reference_targets: Counter[str] = Counter()
    reference_depth = 0
    for row in verified_rows:
        package = row.get("package") or {}
        type_counts = package.get("hircObjectTypeCounts") or {}
        package_label = f"{row.get('block')}:{row.get('path')}"
        expected_type02 = int(type_counts.get("0x02") or 0)
        package_type_stats = package.get("hircObjectTypeStats") or {}
        package_type02 = _read_type02_prefix_metrics(
            package.get("hircType02Prefix"),
            package_type_stats.get("0x02"),
            expected_type02,
            package_label,
        )
        package_type02_bank_totals: Counter[str] = Counter()
        package_type02_bank_plugins: Counter[str] = Counter()
        package_type02_bank_mins: list[int] = []
        package_type02_bank_maxes: list[int] = []
        for key in ("count", "prefixBytes", "opaqueTailBytes", "bodyBytes"):
            type02_totals[key] += package_type02[key]
            package_type02_bank_totals[key] = 0
        if expected_type02:
            type02_packages_with_objects += 1
            type02_package_counts_by_block[str(row.get("block"))] += expected_type02
            if type02_min_opaque_tail is None or package_type02["minOpaqueTailBytes"] < type02_min_opaque_tail:
                type02_min_opaque_tail = package_type02["minOpaqueTailBytes"]
            type02_max_opaque_tail = max(type02_max_opaque_tail, package_type02["maxOpaqueTailBytes"])
        for plugin_type, count in package_type02["pluginTypeCounts"].items():
            type02_plugin_counts[plugin_type] += count
        for plugin_id, count in package_type02["pluginIdCounts"].items():
            type02_plugin_ids[plugin_id] += count

        package_type09 = _read_type09_census(package.get("hircType09"), package_label)
        for key in TYPE09_SCALARS:
            type09_totals[key] += package_type09[key]
        type09_failures.update(package_type09["failureCounts"])
        type09_flags.update(package_type09["tailFlagCounts"])

        package_type17 = _read_type17_census(package.get("hircType17"), package_label)
        for key in TYPE17_SCALARS:
            type17_totals[key] += package_type17[key]
        type17_failures.update(package_type17["failureCounts"])
        type17_reasons.update(package_type17["fenceReasons"])
        type17_by_type.update(package_type17["bodiesByType"])

        package_type08 = _read_type08_head_census(
            package.get("hircType08Head"), package_label
        )
        for key in TYPE08_HEAD_SCALARS:
            type08_totals[key] += package_type08[key]

        package_type11 = _read_type11_source_census(
            package.get("hircType11Sources"), package_label
        )
        for key in TYPE11_SOURCE_SCALARS:
            type11_totals[key] += package_type11[key]
        type11_plugins.update(package_type11["pluginIdCounts"])
        type11_streams.update(package_type11["streamTypeCounts"])
        type11_record_counts.update(package_type11["recordCountCounts"])

        package_music_head = _read_music_head_census(
            package.get("hircMusicHeadReferences"), package_label
        )
        for key in MUSIC_HEAD_SCALARS:
            music_head_totals[key] += package_music_head[key]
        music_head_by_type.update(package_music_head["bodiesByType"])
        music_head_offsets.update(package_music_head["offsetCounts"])
        music_head_discriminants.update(package_music_head["discriminantCounts"])
        music_head_shapes.update(package_music_head["headShapeCounts"])

        package_reference = _read_reference_census(
            package.get("hircReferenceCensus"), package_label
        )
        for key in REFERENCE_CENSUS_FIELDS:
            reference_totals[key] += package_reference[key]
        reference_depth = max(reference_depth, package_reference[REFERENCE_DEPTH_FIELD])
        reference_edges.update(package_reference["edgeCounts"])
        reference_objects.update(package_reference["objectCountsByType"])
        reference_targets.update(package_reference["referenceTargetsByType"])
        bank_reference_totals: Counter[str] = Counter()
        bank_reference_edges: Counter[str] = Counter()
        bank_reference_depth = 0

        lane_packages = {
            key: lane.add_package(
                package,
                package_type_stats.get(key),
                int(type_counts.get(key) or 0),
                package_label,
                row.get("block"),
                row.get("path"),
            )
            for key, lane in body_lanes.items()
        }

        expected_type04 = int(type_counts.get("0x04") or 0)
        package_type04_stats = package_type_stats.get("0x04")
        package_type04 = _read_type04_u32_vector_metrics(
            package.get("hircType04U32VectorFrame"),
            package_type04_stats,
            expected_type04,
            package_label,
        )
        package_type04_bank_totals: Counter[str] = Counter()
        package_type04_bank_failures: Counter[str] = Counter()
        package_type04_bank_unsupported: Counter[str] = Counter()
        for key in TYPE04_FRAME_FIELDS:
            type04_totals[key] += package_type04[key]
        if expected_type04:
            type04_packages_with_objects += 1
            type04_package_counts_by_block[str(row.get("block"))] += expected_type04
        type04_failure_categories.update(package_type04["failureCategories"])
        type04_unsupported_categories.update(package_type04["unsupportedCategories"])
        for example in package_type04["nonExactExamples"]:
            if len(type04_non_exact_examples) >= 32:
                break
            type04_non_exact_examples.append(
                {
                    "block": row.get("block"),
                    "package": row.get("path"),
                    **example,
                }
            )

        expected_type03 = int(type_counts.get("0x03") or 0)
        frame = package.get("hircType03ActionFrame")
        if not isinstance(frame, dict):
            raise ValueError(f"missing type 0x03 cursor result: {package_label}")
        count = int(frame.get("count") or 0)
        exact = int(frame.get("exact") or 0)
        unsupported = int(frame.get("unsupported") or 0)
        failed = int(frame.get("failed") or 0)
        ambiguous = int(frame.get("ambiguous") or 0)
        if count != expected_type03 or count != exact + unsupported + failed + ambiguous:
            raise ValueError(
                "type 0x03 audit count mismatch: "
                f"{package_label} "
                f"objects={expected_type03} framed={count} "
                f"exact={exact} unsupported={unsupported} failed={failed} ambiguous={ambiguous}"
            )
        if ambiguous != 0:
            raise ValueError(
                f"unexpected ambiguous type 0x03 frame result: {package_label}"
            )
        package_metrics = _read_frame_metrics(frame, package_label)
        bank_metrics: Counter[str] = Counter()
        bank_operations: Counter[str] = Counter()
        bank_categories: Counter[str] = Counter()

        totals["count"] += count
        totals["exact"] += exact
        totals["unsupported"] += unsupported
        totals["failed"] += failed
        totals["ambiguous"] += ambiguous
        totals["bodyBytes"] += int(frame.get("bodyBytes") or 0)
        totals["exactCursorBytes"] += int(frame.get("exactCursorBytes") or 0)
        package_type03_counts[str(row.get("block"))] += count
        for operation, operation_count in (frame.get("operationCounts") or {}).items():
            operation_counts[str(operation)] += int(operation_count)
        for category, category_count in (frame.get("failureCategories") or {}).items():
            non_exact_categories[str(category)] += int(category_count)
        for example in frame.get("nonExactExamples") or []:
            if len(non_exact_examples) >= 32:
                break
            non_exact_examples.append(
                {
                    "block": row.get("block"),
                    "package": row.get("path"),
                    **example,
                }
            )
        for bank in package.get("bnkStructures") or []:
            version = bank.get("version")
            bank_version_counts[str(version) if version is not None else "unknown"] += 1
            bank_type_stats = bank.get("hircObjectTypeStats") or {}
            bank_type02_stats = bank_type_stats.get("0x02")
            bank_type02_count = int((bank_type02_stats or {}).get("count") or 0)
            bank_name = f"{package_label} bank={bank.get('bankId')}"
            bank_type02 = _read_type02_prefix_metrics(
                bank.get("hircType02Prefix"),
                bank_type02_stats,
                bank_type02_count,
                bank_name,
            )
            for key in ("count", "prefixBytes", "opaqueTailBytes", "bodyBytes"):
                package_type02_bank_totals[key] += bank_type02[key]
            package_type02_bank_plugins.update(bank_type02["pluginTypeCounts"])
            if bank_type02_count:
                type02_banks_with_objects += 1
                type02_bank_version_counts[str(version) if version is not None else "unknown"] += 1
                package_type02_bank_mins.append(bank_type02["minOpaqueTailBytes"])
                package_type02_bank_maxes.append(bank_type02["maxOpaqueTailBytes"])
            bank_reference = _read_reference_census(
                bank.get("hircReferenceCensus"), bank_name
            )
            for key in REFERENCE_CENSUS_FIELDS:
                bank_reference_totals[key] += bank_reference[key]
            bank_reference_depth = max(bank_reference_depth, bank_reference[REFERENCE_DEPTH_FIELD])
            bank_reference_edges.update(bank_reference["edgeCounts"])
            for key, lane_package in lane_packages.items():
                lane_package.add_bank(
                    bank, bank_type_stats.get(key), bank_name, version
                )
            bank_type04_stats = bank_type_stats.get("0x04")
            bank_type04_count = int((bank_type04_stats or {}).get("count") or 0)
            bank_type04 = _read_type04_u32_vector_metrics(
                bank.get("hircType04U32VectorFrame"),
                bank_type04_stats,
                bank_type04_count,
                bank_name,
            )
            for key in TYPE04_FRAME_FIELDS:
                package_type04_bank_totals[key] += bank_type04[key]
            package_type04_bank_failures.update(bank_type04["failureCategories"])
            package_type04_bank_unsupported.update(bank_type04["unsupportedCategories"])
            if bank_type04_count:
                type04_banks_with_objects += 1
                type04_bank_version_counts[str(version) if version is not None else "unknown"] += 1
            bank_type03_count = int(
                ((bank.get("hircObjectTypeStats") or {}).get("0x03") or {}).get("count") or 0
            )
            bank_frame = bank.get("hircType03ActionFrame")
            if not isinstance(bank_frame, dict):
                raise ValueError(f"missing per-bank type 0x03 cursor result: {bank_name}")
            current_bank_metrics = _read_frame_metrics(bank_frame, bank_name)
            if current_bank_metrics["count"] != bank_type03_count:
                raise ValueError(
                    f"per-bank type 0x03 frame count mismatch: {bank_name} "
                    f"objects={bank_type03_count} framed={current_bank_metrics['count']}"
                )
            if current_bank_metrics["count"] != sum(
                current_bank_metrics[key] for key in ("exact", "unsupported", "failed", "ambiguous")
            ):
                raise ValueError(f"per-bank type 0x03 outcome partition mismatch: {bank_name}")
            if current_bank_metrics["ambiguous"] != 0:
                raise ValueError(f"unexpected per-bank ambiguous type 0x03 result: {bank_name}")
            for key in ("count", "exact", "unsupported", "failed", "ambiguous", "bodyBytes", "exactCursorBytes"):
                bank_metrics[key] += current_bank_metrics[key]
            bank_operations.update(current_bank_metrics["operationCounts"])
            bank_categories.update(current_bank_metrics["failureCategories"])

        for key in ("count", "prefixBytes", "opaqueTailBytes", "bodyBytes"):
            if package_type02_bank_totals[key] != package_type02[key]:
                raise ValueError(
                    "per-bank/package type 0x02 source-prefix total mismatch: "
                    f"{package_label} field={key} banks={package_type02_bank_totals[key]} "
                    f"package={package_type02[key]}"
                )
        if dict(sorted(package_type02_bank_plugins.items())) != package_type02["pluginTypeCounts"]:
            raise ValueError(f"per-bank/package type 0x02 plugin-type counts mismatch: {package_label}")
        package_min_tail = min(package_type02_bank_mins) if package_type02_bank_mins else 0
        package_max_tail = max(package_type02_bank_maxes) if package_type02_bank_maxes else 0
        if (
            package_min_tail != package_type02["minOpaqueTailBytes"]
            or package_max_tail != package_type02["maxOpaqueTailBytes"]
        ):
            raise ValueError(
                f"per-bank/package type 0x02 opaque-tail range mismatch: {package_label} "
                f"banks={package_min_tail}..{package_max_tail} "
                f"package={package_type02['minOpaqueTailBytes']}..{package_type02['maxOpaqueTailBytes']}"
            )

        for key in REFERENCE_CENSUS_FIELDS:
            if bank_reference_totals[key] != package_reference[key]:
                raise ValueError(
                    "per-bank/package HIRC reference census mismatch: "
                    f"{package_label} field={key} banks={bank_reference_totals[key]} "
                    f"package={package_reference[key]}"
                )
        if dict(sorted(bank_reference_edges.items())) != package_reference["edgeCounts"]:
            raise ValueError(f"per-bank/package HIRC reference edges mismatch: {package_label}")
        if bank_reference_depth != package_reference[REFERENCE_DEPTH_FIELD]:
            raise ValueError(
                "per-bank/package HIRC reference depth mismatch: "
                f"{package_label} banks={bank_reference_depth} "
                f"package={package_reference[REFERENCE_DEPTH_FIELD]}"
            )

        for lane_package in lane_packages.values():
            lane_package.reconcile(package_label)

        for key in TYPE04_FRAME_FIELDS:
            if package_type04_bank_totals[key] != package_type04[key]:
                raise ValueError(
                    "per-bank/package type 0x04 candidate-vector total mismatch: "
                    f"{package_label} field={key} banks={package_type04_bank_totals[key]} "
                    f"package={package_type04[key]}"
                )
        if dict(sorted(package_type04_bank_failures.items())) != package_type04["failureCategories"]:
            raise ValueError(f"per-bank/package type 0x04 failure categories mismatch: {package_label}")
        if dict(sorted(package_type04_bank_unsupported.items())) != package_type04["unsupportedCategories"]:
            raise ValueError(f"per-bank/package type 0x04 unsupported categories mismatch: {package_label}")

        for key in ("count", "exact", "unsupported", "failed", "ambiguous", "bodyBytes", "exactCursorBytes"):
            if bank_metrics[key] != package_metrics[key]:
                raise ValueError(
                    "per-bank/package type 0x03 total mismatch: "
                    f"{row.get('block')}:{row.get('path')} field={key} "
                    f"banks={bank_metrics[key]} package={package_metrics[key]}"
                )
        if dict(sorted(bank_operations.items())) != package_metrics["operationCounts"]:
            raise ValueError(
                "per-bank/package type 0x03 operation count mismatch: "
                f"{row.get('block')}:{row.get('path')}"
            )
        if dict(sorted(bank_categories.items())) != package_metrics["failureCategories"]:
            raise ValueError(
                "per-bank/package type 0x03 category count mismatch: "
                f"{row.get('block')}:{row.get('path')}"
            )

    body_bytes = int(totals["bodyBytes"])
    exact_cursor_bytes = int(totals["exactCursorBytes"])
    if exact_cursor_bytes > body_bytes:
        raise ValueError(
            f"type 0x03 exact cursor bytes exceed body bytes: {exact_cursor_bytes}>{body_bytes}"
        )

    frame_closure = "exact" if totals["exact"] == totals["count"] else "incomplete"
    # The accounting equation uses the entries that can actually reach the census.
    # The type 0x04 lane tolerates unsupported bodies whose vectors are framed but
    # never resolved; that gap is published separately below and blocks closure, so
    # it is visible rather than silently shrinking the denominator. The type 0x05 and
    # 0x07 terms are exact-path-only like the census and cannot fire on their own;
    # their lanes' closure gates already refuse any body that is not exact.
    framed_vector_entries = (
        int(type04_totals["exactEntryCount"])
        + int(body_lanes["0x05"].groups.get("referenceEntries", 0))
        + int(body_lanes["0x07"].groups.get("childEntries", 0))
        + int(body_lanes["0x06"].groups.get("childEntries", 0))
    )
    if int(reference_totals["references"]) != framed_vector_entries:
        raise ValueError(
            "HIRC reference census does not cover every framed vector entry: "
            f"references={int(reference_totals['references'])} "
            f"framedEntries={framed_vector_entries}"
        )
    # Edges must also reconcile with their source lane, so a mislabelled source type
    # cannot hide inside a correct grand total.
    # Words framed inside type 0x06 that are deliberately not joined. They must be
    # accounted for exactly, so excluding them cannot quietly become cherry-picking.
    unjoined_candidate_words = (
        int(body_lanes["0x06"].groups.get("groupItemEntries", 0))
        + int(body_lanes["0x06"].groups.get("recordEntries", 0))
    )
    if int(reference_totals["candidateWords"]) != unjoined_candidate_words:
        raise ValueError(
            "HIRC candidate words do not cover every unjoined framed word: "
            f"candidateWords={int(reference_totals['candidateWords'])} "
            f"framedUnjoined={unjoined_candidate_words}"
        )
    entries_not_reaching_census = (
        int(type04_totals["candidateEntryCount"]) - int(type04_totals["exactEntryCount"])
    )
    if entries_not_reaching_census < 0:
        raise ValueError(
            "type 0x04 exact entries exceed its candidate entries: "
            f"exact={int(type04_totals['exactEntryCount'])} "
            f"candidate={int(type04_totals['candidateEntryCount'])}"
        )
    for source, expected_entries in (
        ("type04", int(type04_totals["exactEntryCount"])),
        ("type05", int(body_lanes["0x05"].groups.get("referenceEntries", 0))),
        ("type07", int(body_lanes["0x07"].groups.get("childEntries", 0))),
        ("type06", int(body_lanes["0x06"].groups.get("childEntries", 0))),
    ):
        edge_total = sum(
            count
            for edge, count in reference_edges.items()
            if edge.startswith(source + "_to_")
        )
        if edge_total != expected_entries:
            raise ValueError(
                "HIRC reference edges do not match their source lane: "
                f"source={source} edges={edge_total} laneEntries={expected_entries}"
            )
    type04_count = int(type04_totals["count"])
    type04_exact = int(type04_totals["exact"])
    type04_frame_closure = (
        "no-objects"
        if type04_count == 0
        else "all-candidate-vectors-exact"
        if type04_exact == type04_count
        else "incomplete"
    )
    return {
        "packageCount": expected_packages,
        "verifiedPackageCount": len(verified_rows),
        "excludedBlockCount": len(expected_excluded_statuses),
        "identityReconciliation": {
            "verifiedPackagesMatchedToOuterLedger": True,
            "excludedBlocksMatchedToOuterLedger": True,
            "perBankFramesMatchedToPackageFrames": True,
            "perBankType04FramesMatchedToPackageFrames": True,
        },
        "type03Objects": {
            "count": int(totals["count"]),
            "exact": int(totals["exact"]),
            "unsupported": int(totals["unsupported"]),
            "failed": int(totals["failed"]),
            "ambiguous": int(totals["ambiguous"]),
            "bodyBytes": body_bytes,
            "exactCursorBytes": exact_cursor_bytes,
            "nonExactBodyBytes": body_bytes - exact_cursor_bytes,
            "frameClosure": frame_closure,
            "operationCounts": dict(sorted(operation_counts.items())),
            "nonExactCategories": dict(sorted(non_exact_categories.items())),
            "nonExactExamples": non_exact_examples,
            "packageCountsByBlock": dict(sorted(package_type03_counts.items())),
            "bankVersionCounts": dict(sorted(bank_version_counts.items())),
        },
        "type02SourcePrefixes": {
            "count": int(type02_totals["count"]),
            "packagesWithObjects": type02_packages_with_objects,
            "banksWithObjects": type02_banks_with_objects,
            "prefixBytes": int(type02_totals["prefixBytes"]),
            "opaqueTailBytes": int(type02_totals["opaqueTailBytes"]),
            "bodyBytes": int(type02_totals["bodyBytes"]),
            "bodyAccounting": "prefixBytesPlusOpaqueTailBytesEqualsDeclaredHircObjectBodies",
            "minOpaqueTailBytes": type02_min_opaque_tail or 0,
            "maxOpaqueTailBytes": type02_max_opaque_tail,
            "pluginTypeCounts": dict(sorted(type02_plugin_counts.items())),
            "pluginIdCounts": dict(sorted(type02_plugin_ids.items())),
            "objectCountsByBlock": dict(sorted(type02_package_counts_by_block.items())),
            "bankVersionCounts": dict(sorted(type02_bank_version_counts.items())),
            "wholeBodyCursor": "not-claimed-opaque-tail-remains",
        },
        "referenceGraph": {
            **{key: int(reference_totals[key]) for key in REFERENCE_CENSUS_FIELDS},
            "framedVectorEntries": framed_vector_entries,
            "entriesNotReachingCensus": entries_not_reaching_census,
            REFERENCE_DEPTH_FIELD: reference_depth,
            "edgeCounts": dict(sorted(reference_edges.items())),
            "objectCountsByType": dict(sorted(reference_objects.items())),
            "referenceTargetsByType": dict(sorted(reference_targets.items())),
            "closure": (
                "every-reference-names-one-same-bank-object"
                if reference_graph_is_closed(
                    {
                        **{key: int(reference_totals[key]) for key in REFERENCE_CENSUS_FIELDS},
                    }
                )
                else "incomplete"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "reference direction, parenthood, containment or membership",
                "ordering, selection, mixing or playback behaviour",
                "any name for either endpoint of an edge",
                "that a cross-bank relation is impossible; its absence is a property "
                "of this corpus, not a proven rule",
            ],
        },
        "type02BodyFrames": body_lanes["0x02"].publish(),
        "type07BodyFrames": body_lanes["0x07"].publish(),
        "type05BodyFrames": body_lanes["0x05"].publish(),
        "type06BodyFrames": body_lanes["0x06"].publish(),
        "type14BodyFrames": body_lanes["0x0E"].publish(),
        "type22BodyFrames": body_lanes["0x16"].publish(),
        "type08HeadWords": {key: int(type08_totals[key]) for key in TYPE08_HEAD_SCALARS},
        "type09Bodies": {
            **{key: int(type09_totals[key]) for key in TYPE09_SCALARS},
            "failureCounts": dict(sorted(type09_failures.items())),
            "tailFlagCounts": dict(sorted(type09_flags.items())),
        },
        "type17Bodies": {
            **{key: int(type17_totals[key]) for key in TYPE17_SCALARS},
            "failureCounts": dict(sorted(type17_failures.items())),
            "fenceReasons": dict(sorted(type17_reasons.items())),
            "bodiesByType": dict(sorted(type17_by_type.items())),
        },
        "type11SourceRecords": {
            **{key: int(type11_totals[key]) for key in TYPE11_SOURCE_SCALARS},
            "pluginIdCounts": dict(sorted(type11_plugins.items())),
            "streamTypeCounts": dict(sorted(type11_streams.items())),
            "recordCountCounts": dict(sorted(type11_record_counts.items())),
        },
        "musicHeadReferences": {
            **{key: int(music_head_totals[key]) for key in MUSIC_HEAD_SCALARS},
            "bodiesByType": dict(sorted(music_head_by_type.items())),
            "headShapeCounts": dict(sorted(music_head_shapes.items())),
            "offsetCounts": dict(sorted(music_head_offsets.items())),
            "discriminantCounts": dict(sorted(music_head_discriminants.items())),
        },
        "type04U32VectorCandidates": {
            "count": type04_count,
            "exact": type04_exact,
            "unsupported": int(type04_totals["unsupported"]),
            "failed": int(type04_totals["failed"]),
            "ambiguous": int(type04_totals["ambiguous"]),
            "packagesWithObjects": type04_packages_with_objects,
            "banksWithObjects": type04_banks_with_objects,
            "bodyBytes": int(type04_totals["bodyBytes"]),
            "candidatePrefixBytes": int(type04_totals["candidatePrefixBytes"]),
            "unsupportedCandidatePrefixBytes": int(type04_totals["unsupportedCandidatePrefixBytes"]),
            "exactCursorBytes": int(type04_totals["exactCursorBytes"]),
            "opaqueTailBytes": int(type04_totals["opaqueTailBytes"]),
            "failedBodyBytes": int(type04_totals["failedBodyBytes"]),
            "candidateEntryCount": int(type04_totals["candidateEntryCount"]),
            "nonExactBodyBytes": int(type04_totals["bodyBytes"] - type04_totals["exactCursorBytes"]),
            "frameClosure": type04_frame_closure,
            "bodyAccounting": "candidatePrefixBytesPlusOpaqueTailBytesPlusFailedBodyBytesEqualsDeclaredHircObjectBodies",
            "failureCategories": dict(sorted(type04_failure_categories.items())),
            "unsupportedCategories": dict(sorted(type04_unsupported_categories.items())),
            "nonExactExamples": type04_non_exact_examples,
            "objectCountsByBlock": dict(sorted(type04_package_counts_by_block.items())),
            "bankVersionCounts": dict(sorted(type04_bank_version_counts.items())),
        },
        "audioAuditSummary": audio_summary,
    }


def _markdown(report: dict[str, Any]) -> str:
    actions = report["corpus"]["type03Objects"]
    operation_rows = "\n".join(
        f"| `{operation}` | {count:,} |"
        for operation, count in actions["operationCounts"].items()
    ) or "| _none_ | 0 |"
    categories = actions["nonExactCategories"]
    category_text = ", ".join(f"`{key}` {value:,}" for key, value in categories.items()) or "none"
    return "\n".join(
        [
            "# Wwise HIRC numeric type `0x03` body cursor audit",
            "",
            f"- Status: `{report['status']}`; frame closure: `{actions['frameClosure']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
            f"- Current AnimeStudio CLI matches the outer audit fingerprint: `{report['outer']['animeStudioCliFingerprint']['matchesOuterAudit']}`.",
            _tool_closure_markdown(report),
            f"- Verified AKPK packages: {report['corpus']['verifiedPackageCount']:,}/{report['corpus']['packageCount']:,}; excluded audio blocks: {report['corpus']['excludedBlockCount']:,}.",
            "- Outer-ledger package checksum/chunk/source identities, exclusion status/multiplicity, and per-bank/package frame totals reconciled.",
            f"- Type `0x03` objects: {actions['count']:,}; exact {actions['exact']:,}; unsupported {actions['unsupported']:,}; failed {actions['failed']:,}; ambiguous {actions['ambiguous']:,}.",
            f"- Body bytes: {actions['bodyBytes']:,}; exact cursor bytes: {actions['exactCursorBytes']:,}; non-exact body bytes: {actions['nonExactBodyBytes']:,}.",
            f"- Non-exact categories: {category_text}.",
            "",
            "## Numeric operation-code counts",
            "",
            "| Code | Objects |",
            "|---|---:|",
            operation_rows,
            "",
            "The parser reports byte framing only. Numeric operation codes remain unnamed; this audit does not establish field ownership, operation meaning, target resolution, runtime execution, event selection, or audibility.",
            "",
            f"Corpus gate SHA-256: `{report['corpusGate']['sha256']}`.",
            f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
            "",
        ]
    )


def _type02_markdown(report: dict[str, Any]) -> str:
    prefixes = report["corpus"]["type02SourcePrefixes"]
    cli_fingerprint = report["outer"]["animeStudioCliFingerprint"]
    plugin_rows = "\n".join(
        f"| `{plugin_type}` | {count:,} |"
        for plugin_type, count in prefixes["pluginTypeCounts"].items()
    ) or "| _none_ | 0 |"
    block_rows = "\n".join(
        f"| `{block}` | {count:,} |"
        for block, count in prefixes["objectCountsByBlock"].items()
    ) or "| _none_ | 0 |"
    return "\n".join(
        [
            "# Wwise HIRC numeric type `0x02` bounded source-prefix census",
            "",
            f"- Status: `{report['status']}`; whole-body cursor: `{prefixes['wholeBodyCursor']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
            f"- Current AnimeStudio CLI matches the outer audit fingerprint: `{cli_fingerprint['matchesOuterAudit']}` (outer `{cli_fingerprint['outerAuditSha256']}`, current `{cli_fingerprint['currentSha256']}`).",
            _tool_closure_markdown(report),
            f"- Verified AKPK packages: {report['corpus']['verifiedPackageCount']:,}/{report['corpus']['packageCount']:,}; excluded audio blocks: {report['corpus']['excludedBlockCount']:,}.",
            "- Outer-ledger package checksum/chunk/source identities, exclusions, and per-bank/package prefix totals reconciled.",
            f"- Type `0x02` objects: {prefixes['count']:,} across {prefixes['packagesWithObjects']:,} packages and {prefixes['banksWithObjects']:,} banks.",
            f"- Bounded source-prefix bytes: {prefixes['prefixBytes']:,}; opaque tail bytes: {prefixes['opaqueTailBytes']:,}; object body bytes: {prefixes['bodyBytes']:,}.",
            f"- Per-object opaque-tail sizes range from {prefixes['minOpaqueTailBytes']:,} to {prefixes['maxOpaqueTailBytes']:,} bytes; the tail remains unparsed.",
            "",
            "## Numeric plugin-type counts",
            "",
            "| Low-nibble type | Objects |",
            "|---|---:|",
            plugin_rows,
            "",
            "## Object counts by block",
            "",
            "| Audio block | Objects |",
            "|---|---:|",
            block_rows,
            "",
            "The parser bounds a 14-byte source prefix and, for numeric plugin type `0x02`, its length-prefixed parameter range. Remaining body bytes stay opaque. This is byte-boundary evidence only; it does not identify tail fields, physical media placement, runtime selection, or audibility.",
            "",
            f"Corpus gate SHA-256: `{report['corpusGate']['sha256']}`; AnimeStudio CLI SHA-256 `{report['audioAudit']['toolSha256']}`.",
            f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
            "",
        ]
    )


def _type04_markdown(report: dict[str, Any]) -> str:
    vectors = report["corpus"]["type04U32VectorCandidates"]
    cli_fingerprint = report["outer"]["animeStudioCliFingerprint"]
    block_rows = "\n".join(
        f"| `{block}` | {count:,} |"
        for block, count in vectors["objectCountsByBlock"].items()
    ) or "| _none_ | 0 |"
    failure_rows = "\n".join(
        f"| `{category}` | {count:,} |"
        for category, count in vectors["failureCategories"].items()
    ) or "| _none_ | 0 |"
    unsupported_rows = "\n".join(
        f"| `{category}` | {count:,} |"
        for category, count in vectors["unsupportedCategories"].items()
    ) or "| _none_ | 0 |"
    return "\n".join(
        [
            "# Wwise HIRC numeric type `0x04` candidate-vector frame census",
            "",
            f"- Status: `{report['status']}`; candidate-vector closure: `{vectors['frameClosure']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
            f"- Current AnimeStudio CLI matches the outer audit fingerprint: `{cli_fingerprint['matchesOuterAudit']}` (outer `{cli_fingerprint['outerAuditSha256']}`, current `{cli_fingerprint['currentSha256']}`).",
            _tool_closure_markdown(report),
            f"- Verified AKPK packages: {report['corpus']['verifiedPackageCount']:,}/{report['corpus']['packageCount']:,}; excluded audio blocks: {report['corpus']['excludedBlockCount']:,}.",
            "- Outer-ledger package checksum/chunk/source identities, exclusions, and per-bank/package type `0x04` metrics reconciled.",
            f"- Type `0x04` objects: {vectors['count']:,}; exact candidate frames {vectors['exact']:,}; unsupported {vectors['unsupported']:,}; failed {vectors['failed']:,}; ambiguous {vectors['ambiguous']:,}.",
            f"- Object bodies: {vectors['bodyBytes']:,} bytes; candidate prefix {vectors['candidatePrefixBytes']:,}; exact cursor {vectors['exactCursorBytes']:,}; opaque tail {vectors['opaqueTailBytes']:,}; failed bodies {vectors['failedBodyBytes']:,}.",
            f"- Fully available anonymous candidate entries: {vectors['candidateEntryCount']:,}; packages with objects: {vectors['packagesWithObjects']:,}; banks with objects: {vectors['banksWithObjects']:,}.",
            "- Body accounting: `candidatePrefixBytes + opaqueTailBytes + failedBodyBytes = declared HIRC type 0x04 body bytes`.",
            "",
            "## Failure categories",
            "",
            "| Category | Objects |",
            "|---|---:|",
            failure_rows,
            "",
            "## Unsupported categories",
            "",
            "| Category | Objects |",
            "|---|---:|",
            unsupported_rows,
            "",
            "## Object counts by audio block",
            "",
            "| Audio block | Objects |",
            "|---|---:|",
            block_rows,
            "",
            "The structural candidate is a one-byte count followed by that many 32-bit-width entries. Exact status means this candidate framing reaches the declared object-body end. Entry values remain unnamed; this census does not establish serialized field ownership, entry identity or meaning, Action relationships, runtime execution, event selection, or audibility.",
            "",
            f"Corpus gate SHA-256: `{report['corpusGate']['sha256']}`; AnimeStudio CLI SHA-256 `{report['audioAudit']['toolSha256']}`.",
            f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
            "",
        ]
    )


def _body_lane_markdown(report: dict[str, Any], corpus_key: str, type_key: str) -> str:
    bodies = report["corpus"][corpus_key]
    cli_fingerprint = report["outer"]["animeStudioCliFingerprint"]

    def rows(mapping):
        return "\n".join(f"| `{name}` | {count:,} |" for name, count in mapping.items()) or "| _none_ | 0 |"

    unresolved_rows = "\n".join(f"- {item}" for item in bodies["unresolvedWidths"]) or "- none"
    lines = [
        f"# Wwise HIRC numeric type `{type_key}` whole-body cursor audit",
        "",
        f"- Status: `{report['status']}`; body closure: `{bodies['frameClosure']}`.",
        f"- Current VFS input set: `{report['inputSetSha256']}`.",
        f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
        f"- Current AnimeStudio CLI matches the outer audit fingerprint: `{cli_fingerprint['matchesOuterAudit']}` (outer `{cli_fingerprint['outerAuditSha256']}`, current `{cli_fingerprint['currentSha256']}`).",
        _tool_closure_markdown(report),
        f"- Verified AKPK packages: {report['corpus']['verifiedPackageCount']:,}/{report['corpus']['packageCount']:,}; excluded audio blocks: {report['corpus']['excludedBlockCount']:,}.",
        f"- Outer-ledger package checksum/chunk/source identities, exclusions, and per-bank/package type `{type_key}` body metrics reconciled.",
        f"- Type `{type_key}` objects: {bodies['count']:,}; exact {bodies['exact']:,}; unsupported {bodies['unsupported']:,}; failed {bodies['failed']:,}; ambiguous {bodies['ambiguous']:,}.",
        f"- Object bodies: {bodies['bodyBytes']:,} bytes; exact cursor {bodies['exactCursorBytes']:,}; non-exact {bodies['nonExactBodyBytes']:,}.",
        f"- Exact body lengths range from {bodies['minExactBodyBytes']:,} to {bodies['maxExactBodyBytes']:,} bytes; the smallest possible frame is {bodies['minimumPossibleFrameBytes']}.",
        f"- Packages with objects: {bodies['packagesWithObjects']:,}; banks with objects: {bodies['banksWithObjects']:,}.",
    ]
    if bodies.get("sharedNodeFrame"):
        lines.append(f"- Shared frame: {bodies['sharedNodeFrame'].rstrip('.')}.")
    if bodies.get("closedFormTotal"):
        lines.append(f"- Closed-form check: {bodies['closedFormTotal']}.")
    lines += [
        "- The constraining check is that framed body bytes equal the declared HIRC object bytes minus object ids, and that every exact body ends at its declared body end. The `exactCursorBytes + nonExactBodyBytes = bodyBytes` identity is an internal consistency assert, not independent evidence: a short read is never labelled exact, so that identity cannot fail.",
        f"- Closure is enforced: any failed, unsupported, or ambiguous body makes this report `incomplete` and the gate exit nonzero. Current status: `{report['status']}`.",
        "",
        "## Anonymous group inventory",
        "",
        "| Group | Elements |",
        "|---|---:|",
        rows(bodies["anonymousGroupCounts"]),
        "",
        "## Anonymous selector inventory",
        "",
        "| Selector | Observations |",
        "|---|---:|",
        rows(bodies["anonymousSelectorCounts"]),
        "",
        "## Failure categories",
        "",
        "| Category | Objects |",
        "|---|---:|",
        rows(bodies["failureCategories"]),
        "",
        "## Unsupported categories",
        "",
        "| Category | Objects |",
        "|---|---:|",
        rows(bodies["unsupportedCategories"]),
        "",
        "## Object counts by audio block",
        "",
        "| Audio block | Objects |",
        "|---|---:|",
        rows(bodies["objectCountsByBlock"]),
        "",
        "## What this corpus does not resolve",
        "",
        unresolved_rows,
        "",
    ]
    if bodies.get("upstreamAbortsNotCountedHere"):
        lines += [
            "## Failures this lane cannot count",
            "",
            f"- {bodies['upstreamAbortsNotCountedHere']}",
            "",
        ]
    lines += [
        bodies["frameLayout"],
        "",
        "Exact status means the framing reaches the declared object-body end, and nothing more. Every key, value, selector bit and counted element stays anonymous. This census does not establish:",
        "",
        *(f"- {claim}" for claim in report["evidenceBoundary"]["nonClaims"]),
        "",
        f"Corpus gate SHA-256: `{report['corpusGate']['sha256']}`; AnimeStudio CLI SHA-256 `{report['audioAudit']['toolSha256']}`.",
        f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
        "",
    ]
    return "\n".join(lines)


def _read_reference_census(census: Any, label: str) -> dict[str, Any]:
    """Validate one package's or bank's anonymous reference join.

    Resolution is an identity fact: a reference either names exactly one object in
    the same bank or it does not. Nothing here claims what the relation means.
    """
    # A silent zero default is the wrong default in a gate: an absent census would
    # otherwise read as a clean bank with nothing to resolve.
    if not isinstance(census, dict):
        raise ValueError(f"missing HIRC reference census: {label}")
    metrics: dict[str, Any] = {}
    for key in REFERENCE_CENSUS_FIELDS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"HIRC reference census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"HIRC reference census has negative {key}: {label}")
        metrics[key] = value
    if metrics["references"] != metrics["resolvedSameBank"] + metrics["unresolvedInBank"]:
        raise ValueError(
            f"HIRC reference outcome partition mismatch: {label} "
            f"references={metrics['references']} resolved={metrics['resolvedSameBank']} "
            f"unresolved={metrics['unresolvedInBank']}"
        )
    if metrics["selfReferences"] > metrics["references"]:
        raise ValueError(f"HIRC self references exceed total references: {label}")
    if metrics["referencesToDuplicateIds"] > metrics["references"]:
        raise ValueError(f"HIRC duplicate-id references exceed total references: {label}")
    if metrics["candidateWordsMatchingAnObject"] > metrics["candidateWords"]:
        raise ValueError(
            f"HIRC candidate words matching an object exceed the candidate total: {label}"
        )
    if metrics["targetsWithMultipleReferrers"] > metrics["references"]:
        raise ValueError(f"HIRC multi-referrer targets exceed total references: {label}")
    if metrics["referenceCycleOrFeedingNodes"] > metrics["references"]:
        raise ValueError(f"HIRC reference cycle-or-feeding nodes exceed total references: {label}")
    try:
        depth = int(census[REFERENCE_DEPTH_FIELD])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"HIRC reference census has invalid {REFERENCE_DEPTH_FIELD}: {label}") from exc
    if depth < 0 or depth > metrics["references"]:
        raise ValueError(f"HIRC reference depth is outside its reference count: {label}")
    metrics[REFERENCE_DEPTH_FIELD] = depth
    if metrics["references"] and not depth:
        raise ValueError(f"HIRC references exist with no measured depth: {label}")

    raw_edges = census.get("edgeCounts")
    if not isinstance(raw_edges, dict):
        raise ValueError(f"HIRC reference census has invalid edgeCounts: {label}")
    edges: dict[str, int] = {}
    for name, raw_count in raw_edges.items():
        key = str(name)
        if re.fullmatch(r"type[0-9A-F]{2}_to_type[0-9A-F]{2}", key) is None:
            raise ValueError(f"HIRC reference edge is not a numeric type pair: {label} edge={key!r}")
        try:
            count = int(raw_count)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"HIRC reference edge count is invalid: {label} edge={key}") from exc
        if count < 0:
            raise ValueError(f"HIRC reference edge count is negative: {label} edge={key}")
        if count:
            edges[key] = count
    if sum(edges.values()) != metrics["resolvedSameBank"]:
        raise ValueError(
            f"HIRC reference edges do not account for every resolved reference: {label} "
            f"edges={sum(edges.values())} resolved={metrics['resolvedSameBank']}"
        )
    metrics["edgeCounts"] = dict(sorted(edges.items()))

    raw_objects = census.get("objectCountsByType")
    if not isinstance(raw_objects, dict):
        raise ValueError(f"HIRC reference census has invalid objectCountsByType: {label}")
    object_counts: dict[str, int] = {}
    for name, raw_count in raw_objects.items():
        key = str(name)
        if re.fullmatch(r"type[0-9A-F]{2}", key) is None:
            raise ValueError(f"HIRC object type key is not numeric: {label} key={key!r}")
        count = int(raw_count)
        if count < 0:
            raise ValueError(f"HIRC object type count is negative: {label} type={key}")
        object_counts[key] = count
    metrics["objectCountsByType"] = dict(sorted(object_counts.items()))

    # Both endpoints of every edge must be a type this corpus actually declares, and
    # no type may receive more references than it has objects: with at most one
    # referrer per target, edges into a type are distinct targets of that type.
    target_totals: Counter[str] = Counter()
    for edge, count in metrics["edgeCounts"].items():
        source, target = edge.split("_to_")
        for endpoint in (source, target):
            if endpoint not in object_counts:
                raise ValueError(
                    f"HIRC reference edge names a type the bank does not declare: "
                    f"{label} edge={edge} type={endpoint}"
                )
        target_totals[target] += count
    if metrics["targetsWithMultipleReferrers"] == 0:
        for target, total in target_totals.items():
            if total > object_counts[target]:
                raise ValueError(
                    f"HIRC references into a type exceed its object population: "
                    f"{label} type={target} references={total} objects={object_counts[target]}"
                )
    metrics["referenceTargetsByType"] = dict(sorted(target_totals.items()))
    return metrics


MUSIC_HEAD_SCALARS = (
    "bodies",
    "resolved",
    "unresolved",
    "zero",
    "unknownDiscriminant",
    "tooShort",
    # Bodies whose first byte is not 0. Their head is a different shape, so they are
    # outside the claim; the count is published rather than removed from the total.
    "unknownHeadShape",
)
# Byte 2 chooses where the word sits. Only these values are observed, and an
# unobserved one must be counted as unknown rather than assigned a branch.
MUSIC_HEAD_DISCRIMINANTS = {"byte2_00": 9, "byte2_01": 5, "byte2_02": 5}


def _read_music_head_census(census: Any, label: str) -> dict[str, Any]:
    """Validate one package's or bank's type 0x0A / 0x0D head-reference census."""
    if census is None:
        return {key: 0 for key in MUSIC_HEAD_SCALARS} | {
            "bodiesByType": {}, "offsetCounts": {}, "discriminantCounts": {}, "headShapeCounts": {}
        }
    if not isinstance(census, dict):
        raise ValueError(f"music head reference census is not an object: {label}")
    out: dict[str, Any] = {}
    for key in MUSIC_HEAD_SCALARS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"music head census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"music head census has negative {key}: {label}")
        out[key] = value
    for key in ("bodiesByType", "offsetCounts", "discriminantCounts", "headShapeCounts"):
        raw = census.get(key)
        if not isinstance(raw, dict):
            raise ValueError(f"music head census has invalid {key}: {label}")
        out[key] = {str(name): int(count) for name, count in raw.items()}
    # Every body must land in exactly one outcome, or a body has been double
    # counted or dropped somewhere in the reader.
    outcomes = (
        out["resolved"] + out["unresolved"] + out["zero"]
        + out["unknownDiscriminant"] + out["tooShort"] + out["unknownHeadShape"]
    )
    if outcomes != out["bodies"]:
        raise ValueError(
            f"music head outcomes do not partition the bodies: {label} "
            f"outcomes={outcomes} bodies={out['bodies']}"
        )
    if sum(out["bodiesByType"].values()) != out["bodies"]:
        raise ValueError(f"music head per-type counts disagree with the body total: {label}")
    for name in out["discriminantCounts"]:
        if name not in MUSIC_HEAD_DISCRIMINANTS:
            raise ValueError(f"music head census reports an unobserved discriminant: {label} {name}")
    # The offset histogram must follow from the discriminant histogram, not float free.
    expected: dict[str, int] = {}
    for name, count in out["discriminantCounts"].items():
        key = f"offset_{MUSIC_HEAD_DISCRIMINANTS[name]}"
        expected[key] = expected.get(key, 0) + count
    if out["offsetCounts"] and out["offsetCounts"] != expected:
        raise ValueError(
            f"music head offsets do not follow from the discriminant byte: {label} "
            f"offsets={out['offsetCounts']} expected={expected}"
        )
    return out


def music_head_references_are_closed(corpus: dict[str, Any]) -> bool:
    """Every type 0x0A and 0x0D body must name exactly one same-bank object.

    The claim is that the offset follows from a byte and the word always resolves.
    A single body that is zero, unresolved, short, or carries an unobserved
    discriminant falsifies that, so none of them may be tolerated.
    """
    bodies = int(corpus.get("bodies") or 0)
    # The claim covers bodies whose head shape is the established one. The rest are
    # published, not deleted, so the denominator stays visible.
    claimed = bodies - int(corpus.get("unknownHeadShape") or 0)
    return (
        claimed > 0
        and claimed == int(corpus.get("resolved") or 0)
        and int(corpus.get("unresolved") or 0) == 0
        and int(corpus.get("zero") or 0) == 0
        and int(corpus.get("unknownDiscriminant") or 0) == 0
        and int(corpus.get("tooShort") or 0) == 0
    )


TYPE09_SCALARS = (
    "bodies", "exact", "unestablishedSecondRun", "failed",
    "exactBytes", "bodyBytes", "runEntries",
)


def _read_type09_census(census: Any, label: str) -> dict[str, Any]:
    if census is None:
        return {key: 0 for key in TYPE09_SCALARS} | {"failureCounts": {}, "tailFlagCounts": {}}
    if not isinstance(census, dict):
        raise ValueError(f"type 0x09 census is not an object: {label}")
    out: dict[str, Any] = {}
    for key in TYPE09_SCALARS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x09 census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x09 census has negative {key}: {label}")
        out[key] = value
    for key in ("failureCounts", "tailFlagCounts"):
        raw = census.get(key)
        if not isinstance(raw, dict):
            raise ValueError(f"type 0x09 census has invalid {key}: {label}")
        out[key] = {str(k): int(v) for k, v in raw.items()}
    if out["exact"] + out["unestablishedSecondRun"] + out["failed"] != out["bodies"]:
        raise ValueError(
            f"type 0x09 outcomes do not partition the bodies: {label} "
            f"exact={out['exact']} open={out['unestablishedSecondRun']} "
            f"failed={out['failed']} bodies={out['bodies']}"
        )
    if sum(out["failureCounts"].values()) != out["failed"]:
        raise ValueError(f"type 0x09 failure categories do not sum to the failures: {label}")
    # One tail flag is read per exactly framed body and nowhere else.
    if sum(out["tailFlagCounts"].values()) != out["exact"]:
        raise ValueError(
            f"type 0x09 tail flags do not match the exact bodies: {label} "
            f"flags={sum(out['tailFlagCounts'].values())} exact={out['exact']}"
        )
    if out["exactBytes"] > out["bodyBytes"]:
        raise ValueError(f"type 0x09 exact bytes exceed the body bytes: {label}")
    return out


def type09_is_framed_except_the_second_run(corpus: dict[str, Any]) -> bool:
    """Every type 0x09 body is consumed exactly or fenced for its second run.

    The node frame opens all of them, so a failure here means the reader broke,
    not that the format is hard; failures are therefore not tolerated at all.
    """
    return (
        int(corpus.get("bodies") or 0) > 0
        and int(corpus.get("failed") or 0) == 0
        and int(corpus.get("exact") or 0) > 0
        and int(corpus.get("exact") or 0) + int(corpus.get("unestablishedSecondRun") or 0)
        == int(corpus.get("bodies") or 0)
    )


TYPE17_SCALARS = (
    "bodies", "exact", "fenced", "failed",
    "exactBytes", "bodyBytes", "runElements", "groupIEntries",
)


def _read_type17_census(census: Any, label: str) -> dict[str, Any]:
    if census is None:
        return {key: 0 for key in TYPE17_SCALARS} | {
            "failureCounts": {}, "fenceReasons": {}, "bodiesByType": {}
        }
    if not isinstance(census, dict):
        raise ValueError(f"type 0x11 census is not an object: {label}")
    out: dict[str, Any] = {}
    for key in TYPE17_SCALARS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x11 census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x11 census has negative {key}: {label}")
        out[key] = value
    for key in ("failureCounts", "fenceReasons", "bodiesByType"):
        raw = census.get(key)
        if not isinstance(raw, dict):
            raise ValueError(f"type 0x11 census has invalid {key}: {label}")
        out[key] = {str(k): int(v) for k, v in raw.items()}
    # Each fenced body carries exactly one stated reason, so a fence with no reason
    # would be indistinguishable from a body quietly dropped.
    if sum(out["fenceReasons"].values()) != out["fenced"]:
        raise ValueError(
            f"type 0x11 fence reasons do not sum to the fenced bodies: {label} "
            f"reasons={sum(out['fenceReasons'].values())} fenced={out['fenced']}"
        )
    if sum(out["bodiesByType"].values()) != out["bodies"]:
        raise ValueError(f"type 0x11 per-type counts disagree with the body total: {label}")
    if out["exact"] + out["fenced"] + out["failed"] != out["bodies"]:
        raise ValueError(
            f"type 0x11 outcomes do not partition the bodies: {label} "
            f"exact={out['exact']} fenced={out['fenced']} "
            f"failed={out['failed']} bodies={out['bodies']}"
        )
    if sum(out["failureCounts"].values()) != out["failed"]:
        raise ValueError(f"type 0x11 failure categories do not sum to the failures: {label}")
    if out["exactBytes"] > out["bodyBytes"]:
        raise ValueError(f"type 0x11 exact bytes exceed the body bytes: {label}")
    return out


def type17_is_framed_except_the_tied_block(corpus: dict[str, Any]) -> bool:
    """Every type 0x11 body is either consumed exactly or fenced for the tied width.

    A failure is not tolerated: the only body this reader is allowed to leave
    unframed is one whose optional-block width the corpus genuinely cannot
    determine, and that has to be a distinct outcome rather than a failure bucket.
    """
    return (
        int(corpus.get("bodies") or 0) > 0
        and int(corpus.get("failed") or 0) == 0
        and int(corpus.get("exact") or 0) > 0
        and int(corpus.get("exact") or 0) + int(corpus.get("fenced") or 0)
        == int(corpus.get("bodies") or 0)
    )


TYPE08_HEAD_SCALARS = ("bodies", "resolved", "null", "unresolved", "tooShort")


def _read_type08_head_census(census: Any, label: str) -> dict[str, int]:
    if census is None:
        return {key: 0 for key in TYPE08_HEAD_SCALARS}
    if not isinstance(census, dict):
        raise ValueError(f"type 0x08 head census is not an object: {label}")
    out: dict[str, int] = {}
    for key in TYPE08_HEAD_SCALARS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x08 head census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x08 head census has negative {key}: {label}")
        out[key] = value
    outcomes = out["resolved"] + out["null"] + out["unresolved"] + out["tooShort"]
    if outcomes != out["bodies"]:
        raise ValueError(
            f"type 0x08 head outcomes do not partition the bodies: {label} "
            f"outcomes={outcomes} bodies={out['bodies']}"
        )
    return out


def type08_head_words_are_null_or_resolve(corpus: dict[str, Any]) -> bool:
    """The leading word is null or names one same-bank object, never anything else.

    Null is a legitimate outcome for this type, so it is allowed; a non-null word
    that names nothing is not, because that is what the claim forbids.
    """
    return (
        int(corpus.get("bodies") or 0) > 0
        and int(corpus.get("unresolved") or 0) == 0
        and int(corpus.get("tooShort") or 0) == 0
        and int(corpus.get("resolved") or 0) > 0
        and int(corpus.get("resolved") or 0) + int(corpus.get("null") or 0)
        == int(corpus.get("bodies") or 0)
    )


TYPE11_SOURCE_SCALARS = ("bodies", "bodiesWithRecords", "records", "recordsOutOfRange", "tooShort")


def _read_type11_source_census(census: Any, label: str) -> dict[str, Any]:
    """Validate one package's or bank's type 0x0B source-record census."""
    if census is None:
        return {key: 0 for key in TYPE11_SOURCE_SCALARS} | {
            "pluginIdCounts": {}, "streamTypeCounts": {}, "recordCountCounts": {}
        }
    if not isinstance(census, dict):
        raise ValueError(f"type 0x0B source census is not an object: {label}")
    out: dict[str, Any] = {}
    for key in TYPE11_SOURCE_SCALARS:
        try:
            value = int(census[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"type 0x0B source census has invalid {key}: {label}") from exc
        if value < 0:
            raise ValueError(f"type 0x0B source census has negative {key}: {label}")
        out[key] = value
    for key in ("pluginIdCounts", "streamTypeCounts", "recordCountCounts"):
        raw = census.get(key)
        if not isinstance(raw, dict):
            raise ValueError(f"type 0x0B source census has invalid {key}: {label}")
        out[key] = {str(name): int(count) for name, count in raw.items()}
    for key in ("pluginIdCounts", "streamTypeCounts"):
        if sum(out[key].values()) != out["records"]:
            raise ValueError(
                f"type 0x0B {key} do not sum to the record total: {label} "
                f"histogram={sum(out[key].values())} records={out['records']}"
            )
    if out["bodiesWithRecords"] > out["bodies"]:
        raise ValueError(f"type 0x0B bodies with records exceed the body total: {label}")
    return out


def type11_sources_share_the_type02_plugin_space(
    corpus: dict[str, Any], type02_plugin_counts: dict[str, Any]
) -> bool:
    """Every type 0x0B source record must use a plug-in id type 0x02 also uses.

    The claim only has force because plug-in ids are sparse 32-bit values: a wrong
    record stride would put garbage in this field and it would leave the set at
    once. So a single record outside the set falsifies the stride, and the gate
    must refuse rather than report a rate.
    """
    if int(corpus.get("records") or 0) <= 0:
        return False
    if int(corpus.get("recordsOutOfRange") or 0) or int(corpus.get("tooShort") or 0):
        return False
    known = set(type02_plugin_counts)
    if not known:
        return False
    return all(name in known for name in (corpus.get("pluginIdCounts") or {}))


def reference_graph_is_closed(corpus: dict[str, Any]) -> bool:
    """Return whether every reference names exactly one unambiguous same-bank object.

    An unresolved reference, a self reference, a target with more than one referrer,
    or a reference into a duplicated id each break a different part of the claim, so
    any of them must stop the gate rather than lower a percentage.
    """
    return (
        int(corpus.get("references") or 0) > 0
        and int(corpus.get("unresolvedInBank") or 0) == 0
        and int(corpus.get("selfReferences") or 0) == 0
        and int(corpus.get("targetsWithMultipleReferrers") or 0) == 0
        and int(corpus.get("referencesToDuplicateIds") or 0) == 0
        and int(corpus.get("references") or 0) == int(corpus.get("resolvedSameBank") or 0)
        # A cycle would make the relation something other than a forest.
        and int(corpus.get("referenceCycleOrFeedingNodes") or 0) == 0
        # A framed vector entry that never reached the census is an unresolved
        # reference by another name.
        and int(corpus.get("entriesNotReachingCensus") or 0) == 0
    )


def _reference_graph_markdown(report: dict[str, Any]) -> str:
    graph = report["corpus"]["referenceGraph"]
    type09 = report["corpus"].get("type09Bodies") or {}
    type09_lines = []
    if type09.get("bodies"):
        type09_lines = [
            "",
            "## Numeric type `0x09`: the node frame does open it",
            "",
            f"- Bodies: {type09['bodies']:,}; consumed exactly to the declared body end: "
            f"{type09['exact']:,} ({type09['exactBytes']:,} of {type09['bodyBytes']:,} bytes).",
            f"- Fenced because a second counted run introduces records of an "
            f"unestablished shape: {type09['unestablishedSecondRun']:,}. Failures: "
            f"{type09['failed']:,}.",
            f"- Four-byte run entries: {type09['runEntries']:,}.",
            "",
            "The shared node frame opens **every** one of these bodies, which is worth "
            "stating plainly because this type was previously recorded here as resisting "
            "it. After the frame comes a counted run of four-byte entries and then a "
            "second count. Where that second count is zero, one more byte closes the "
            "body exactly.",
            "",
            "Where it is not zero it introduces records this reader cannot frame, so "
            "those bodies are fenced. Several fixed and variable record shapes were "
            "tried and none consumed them, so nothing is claimed about that run.",
        ]

    type17 = report["corpus"].get("type17Bodies") or {}
    type17_lines = []
    if type17.get("bodies"):
        type17_lines = [
            "",
            "## Numeric types `0x11` and `0x10`: one grammar, framed except where it is undetermined",
            "",
            f"- Bodies: {type17['bodies']:,}; consumed exactly to the declared body end: "
            f"{type17['exact']:,} ({type17['exactBytes']:,} of {type17['bodyBytes']:,} bytes).",
            f"- Fenced: {type17['fenced']:,}. Failures: {type17['failed']:,}.",
            "",
            "| Fence reason | Bodies |",
            "|---|---:|",
            *(f"| `{name}` | {count:,} |" for name, count in sorted(type17["fenceReasons"].items())),
            "",
            "| Numeric type | Bodies |",
            "|---|---:|",
            *(f"| `{name}` | {count:,} |" for name, count in sorted(type17["bodiesByType"].items())),
            f"- Group I entries: {type17['groupIEntries']:,}; six-byte run elements: "
            f"{type17['runElements']:,}.",
            "",
            "Numeric types `0x11` and `0x10` share one grammar: an eight-byte header "
            "whose second word sizes an opaque section, one byte, the node frame's group "
            "I structure, a sixteen-bit flag, and a counted run of six-byte elements. "
            "Group I is reused, not re-derived. Type `0x10` was not decoded separately -- "
            "its header matched, so the existing grammar was tried and it fit.",
            "",
            "Every fenced body states why. When the flag is set an extra block "
            "appears, and **two widths consume every flagged body exactly**: 21 and 27. "
            "They are the same bytes read two ways, with 27 swallowing the run's single "
            "element and reading a zero count. The flag is never greater than 1 anywhere "
            "in this corpus, so no body can separate the two readings, and the width is "
            "underdetermined rather than merely unknown. Those bodies are therefore not "
            "framed at all; picking either width would be a coin flip presented as a "
            "result. Separately, type `0x10` bodies whose third byte is 0x7F end in "
            "something group I does not describe at any offset tried, so they are fenced "
            "under their own reason rather than blamed on the shared grammar.",
        ]

    head08 = report["corpus"].get("type08HeadWords") or {}
    head08_lines = []
    if head08.get("bodies"):
        head08_lines = [
            "",
            "## Numeric type `0x08`: a leading word that is null or names one object",
            "",
            f"- Bodies: {head08['bodies']:,}; naming one same-bank object: {head08['resolved']:,}; "
            f"null: {head08['null']:,}.",
            f"- Naming something that is not in the bank: {head08['unresolved']:,}; too short: "
            f"{head08['tooShort']:,}.",
            "",
            "Type `0x08` is **not framed**. The claim here is only about its first four "
            "bytes: they are either all zero or the identity of exactly one object "
            "declared by the same bank, and never a non-null value that names nothing. "
            "Null is a real outcome for this type rather than a failure, so it is counted "
            "on its own instead of being folded into either side; what the gate forbids is "
            "the third case.",
        ]

    sources11 = report["corpus"].get("type11SourceRecords") or {}
    known_plugins = report["corpus"].get("type02PluginIdCounts") or {}
    source_lines = []
    if sources11.get("records"):
        source_lines = [
            "",
            "## Numeric type `0x0B`: a counted run of source records",
            "",
            f"- Bodies: {sources11['bodies']:,}; declaring at least one record: {sources11['bodiesWithRecords']:,}.",
            f"- Records: {sources11['records']:,}; out of range {sources11['recordsOutOfRange']:,}; too short {sources11['tooShort']:,}.",
            "",
            "| Plug-in id | Records in `0x0B` | Objects in `0x02` |",
            "|---|---:|---:|",
            *(
                f"| `{name}` | {count:,} | {known_plugins.get(name, 0):,} |"
                for name, count in sorted(sources11["pluginIdCounts"].items())
            ),
            "",
            "Numeric type `0x0B` opens with a byte, a 32-bit record count, and that many "
            "fourteen-byte records whose first word is a plug-in id. Every one of those ids "
            "is an id numeric type `0x02` also uses. That is the evidence for the record "
            "stride, and it carries weight because plug-in ids are sparse 32-bit values "
            "rather than small integers: a wrong stride would put arbitrary bytes in this "
            "field and they would leave the set immediately. Records after the first are "
            "what actually test the stride, and they are in the counts above.",
            "",
            "This is **not** a frame for type `0x0B`. Only the counted run is read; what "
            "follows it is untouched and unclaimed. The bytes after the run do continue "
            "with a second counted structure whose entries repeat one of these source ids, "
            "but 248 of those entries name something else, so it is not established and is "
            "deliberately absent from this report.",
        ]

    head = report["corpus"].get("musicHeadReferences") or {}
    head_lines = []
    if head:
        shape_rows = chr(10).join(
            f"| `{name}` | {count:,} |" for name, count in sorted(head["headShapeCounts"].items())
        ) or "| _none_ | 0 |"
        head_lines = [
            "",
            "## Numeric types `0x0A`, `0x0C` and `0x0D`: one named object per body",
            "",
            f"- Bodies: {head['bodies']:,}; naming exactly one same-bank object: {head['resolved']:,}.",
            f"- Unresolved {head['unresolved']:,}; zero {head['zero']:,}; unknown discriminant "
            f"{head['unknownDiscriminant']:,}; too short {head['tooShort']:,}.",
            f"- Bodies outside the claim because their first byte is not 0: {head['unknownHeadShape']:,}. "
            "They are excluded and counted here rather than removed from the total, so the "
            "denominator above stays the whole population.",
            "",
            "| Body byte 2 | Bodies | Word offset |",
            "|---|---:|---:|",
            *(
                f"| `{name}` | {count:,} | {9 if name.endswith('00') else 5} |"
                for name, count in sorted(head["discriminantCounts"].items())
            ),
            "",
            "",
            "| Body byte 0 | Bodies |",
            "|---|---:|",
            shape_rows,
            "",
            "These three types are **not framed**: a variable-length region inside them is "
            "still unisolated, so no layout is claimed here. What is claimed is narrower "
            "and is gated the same way as the vectors above: body byte 2 selects where a "
            "single 32-bit word sits, and that word names exactly one object declared by "
            "the same bank in every body whose first byte is 0. The offset is computed from the byte and never "
            "searched for, the offset histogram is required to follow from the byte "
            "histogram, and an unobserved byte value is counted as unknown rather than "
            "assigned a branch. Nothing here says what the relation means.",
        ]

    cli_fingerprint = report["outer"]["animeStudioCliFingerprint"]
    edge_rows = "\n".join(
        f"| `{edge}` | {count:,} |" for edge, count in graph["edgeCounts"].items()
    ) or "| _none_ | 0 |"
    return "\n".join(
        [
            "# Wwise HIRC anonymous reference-graph join",
            "",
            f"- Status: `{report['status']}`; join closure: `{graph['closure']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
            f"- Current AnimeStudio CLI matches the outer audit fingerprint: `{cli_fingerprint['matchesOuterAudit']}` (outer `{cli_fingerprint['outerAuditSha256']}`, current `{cli_fingerprint['currentSha256']}`).",
            _tool_closure_markdown(report),
            f"- Verified AKPK packages: {report['corpus']['verifiedPackageCount']:,}/{report['corpus']['packageCount']:,}; excluded audio blocks: {report['corpus']['excludedBlockCount']:,}.",
            f"- References framed: {graph['references']:,}; resolved in the same bank: {graph['resolvedSameBank']:,}; unresolved: {graph['unresolvedInBank']:,}.",
            f"- Self references: {graph['selfReferences']:,}; targets carrying more than one referrer: {graph['targetsWithMultipleReferrers']:,}.",
            f"- Nodes on or feeding a reference cycle: {graph['referenceCycleOrFeedingNodes']:,}; longest chain of references traversed: {graph['maximumReferenceDepth']:,} (counted in references, so a chain of {graph['maximumReferenceDepth']:,} links {graph['maximumReferenceDepth'] + 1:,} objects).",
            f"- Framed vector entries that never reached this census: {graph['entriesNotReachingCensus']:,}.",
            f"- Words framed beside a reference vector but deliberately not joined: {graph['candidateWords']:,}, of which {graph['candidateWordsMatchingAnObject']:,} do match an object in their bank. They are excluded because they do not all match, so they are not established as identities -- the shortfall is published here rather than dropped.",
            "- With no target carrying more than one referrer, the references into a numeric type are that many distinct objects of it, so the table below is directly comparable to the object population beside it.",
            f"- Object ids that repeat inside a bank: {graph['distinctDuplicateObjectIds']:,} distinct ids over {graph['duplicateObjectIds']:,} repeat occurrences.",
            f"- References into a duplicated id: {graph['referencesToDuplicateIds']:,}.",
            "",
            "## Numeric type-pair edges",
            "",
            "| Edge | References |",
            "|---|---:|",
            edge_rows,
            "",
            "## References into each numeric type, against that type's population",
            "",
            "| Type | Referenced | Objects |",
            "|---|---:|---:|",
            "\n".join(
                f"| `{name}` | {graph['referenceTargetsByType'].get(name, 0):,} | {count:,} |"
                for name, count in graph["objectCountsByType"].items()
            ) or "| _none_ | 0 | 0 |",
            "",
            *type09_lines,
            *type17_lines,
            *head08_lines,
            *source_lines,
            *head_lines,
            "",
            "Every reference is a four-byte value inside a counted vector that the body framers already consume exactly. This report joins those values to the object identities declared by the same bank and reports where each one lands.",
            "",
            "Resolution is an identity fact and nothing more. A resolved reference does not establish direction, parenthood, containment, membership, ordering, selection, playback, or any name for either endpoint; it establishes only that the value equals the identity of exactly one object declared in the same bank. The type pairs are numeric on both sides. No cross-bank or cross-package relation is claimed, and absence of one here is a property of this corpus, not a rule.",
            "",
            f"Corpus gate SHA-256: `{report['corpusGate']['sha256']}`; AnimeStudio CLI SHA-256 `{report['audioAudit']['toolSha256']}`.",
            f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
            "",
        ]
    )


def _tool_closure_markdown(report: dict[str, Any]) -> str:
    closure = report["audioAudit"]["toolClosure"]
    return (
        f"- Current AnimeStudio CLI output closure: {closure['fileCount']:,} files; "
        f"manifest SHA-256 **{closure['manifestSha256']}**."
    )


def run_current_corpus_audit(
    *,
    expected_input_set_sha256: str,
    outer_path: Path = DEFAULT_OUTER,
    ledger_path: Path = DEFAULT_LEDGER,
    cli_path: Path = DEFAULT_CLI,
    intermediate_path: Path = DEFAULT_TEMP_AUDIT,
    output_json: Path = DEFAULT_OUTPUT,
    output_markdown: Path | None = None,
    type02_output_json: Path = DEFAULT_TYPE02_OUTPUT,
    type02_output_markdown: Path | None = None,
    type04_output_json: Path = DEFAULT_TYPE04_OUTPUT,
    type04_output_markdown: Path | None = None,
    type02_body_output_json: Path = DEFAULT_TYPE02_BODY_OUTPUT,
    type02_body_output_markdown: Path | None = None,
    type07_body_output_json: Path = DEFAULT_TYPE07_BODY_OUTPUT,
    type07_body_output_markdown: Path | None = None,
    type05_body_output_json: Path = DEFAULT_TYPE05_BODY_OUTPUT,
    type05_body_output_markdown: Path | None = None,
    type06_body_output_json: Path = DEFAULT_TYPE06_BODY_OUTPUT,
    type06_body_output_markdown: Path | None = None,
    type14_body_output_json: Path = DEFAULT_TYPE14_BODY_OUTPUT,
    type14_body_output_markdown: Path | None = None,
    type22_body_output_json: Path = DEFAULT_TYPE22_BODY_OUTPUT,
    type22_body_output_markdown: Path | None = None,
    reference_output_json: Path = DEFAULT_REFERENCE_OUTPUT,
    reference_output_markdown: Path | None = None,
) -> dict[str, Any]:
    outer, source_auth = load_current_outer(outer_path, ledger_path, expected_input_set_sha256)
    input_set = str(outer["inputSetSha256"]).upper()
    expected_file_rows = int((outer.get("summary") or {}).get("ledgerFileCount") or 0)
    expected_files, excluded_files, file_row_count = collect_current_audio_files(
        ledger_path,
        input_set,
        expected_file_rows,
    )
    if not cli_path.is_file():
        raise ValueError(f"AnimeStudio CLI is missing: {cli_path}")
    corpus_gate_path = Path(__file__).resolve()
    corpus_gate_sha = sha256_file(corpus_gate_path)
    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown = output_markdown or output_json.with_suffix(".md")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type02_output_json.parent.mkdir(parents=True, exist_ok=True)
    type02_output_markdown = type02_output_markdown or type02_output_json.with_suffix(".md")
    type02_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type04_output_json.parent.mkdir(parents=True, exist_ok=True)
    type04_output_markdown = type04_output_markdown or type04_output_json.with_suffix(".md")
    type04_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type02_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type02_body_output_markdown = type02_body_output_markdown or type02_body_output_json.with_suffix(".md")
    type02_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type07_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type07_body_output_markdown = type07_body_output_markdown or type07_body_output_json.with_suffix(".md")
    type07_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type05_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type05_body_output_markdown = type05_body_output_markdown or type05_body_output_json.with_suffix(".md")
    type05_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type06_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type06_body_output_markdown = type06_body_output_markdown or type06_body_output_json.with_suffix(".md")
    type06_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type14_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type14_body_output_markdown = type14_body_output_markdown or type14_body_output_json.with_suffix(".md")
    type14_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    type22_body_output_json.parent.mkdir(parents=True, exist_ok=True)
    type22_body_output_markdown = type22_body_output_markdown or type22_body_output_json.with_suffix(".md")
    type22_body_output_markdown.parent.mkdir(parents=True, exist_ok=True)
    reference_output_json.parent.mkdir(parents=True, exist_ok=True)
    reference_output_markdown = reference_output_markdown or reference_output_json.with_suffix(".md")
    reference_output_markdown.parent.mkdir(parents=True, exist_ok=True)

    cli_sha_before = sha256_file(cli_path)
    tool_closure_before = _capture_cli_output_closure(cli_path)
    outer_cli_fingerprint = _outer_cli_fingerprint(outer, cli_path, cli_sha_before)
    command = [
        str(cli_path),
        "audio-audit",
        "--streaming-assets",
        str(outer["primaryAssets"]),
        "--fallback-assets",
        str(outer["fallbackAssets"]),
        "--hirc-only",
        "--output",
        str(intermediate_path),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(
            "AnimeStudio audio-audit failed: "
            f"exit={result.returncode} stderr={result.stderr[-1000:]}"
        )
    cli_sha_after = sha256_file(cli_path)
    if cli_sha_after != cli_sha_before:
        raise ValueError(
            f"AnimeStudio CLI changed during audio-audit: before={cli_sha_before} after={cli_sha_after}"
        )
    tool_closure_after = _capture_cli_output_closure(cli_path)
    if tool_closure_after["manifestSha256"] != tool_closure_before["manifestSha256"]:
        raise ValueError(
            "AnimeStudio CLI output closure changed during audio-audit: "
            f"before={tool_closure_before['manifestSha256']} after={tool_closure_after['manifestSha256']}"
        )
    gate_sha_after = sha256_file(corpus_gate_path)
    if gate_sha_after != corpus_gate_sha:
        raise ValueError(
            f"HIRC corpus gate changed during audio-audit: before={corpus_gate_sha} after={gate_sha_after}"
        )
    if not intermediate_path.is_file():
        raise ValueError(f"AnimeStudio audio-audit did not write its report: {intermediate_path}")
    audio_audit, intermediate_sha = _load_json_with_sha256(intermediate_path)
    corpus = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
    type02_prefix_corpus = corpus["type02SourcePrefixes"]
    type04_vector_corpus = corpus["type04U32VectorCandidates"]
    type02_body_corpus = corpus["type02BodyFrames"]
    type07_body_corpus = corpus["type07BodyFrames"]
    action_corpus = {
        key: value
        for key, value in corpus.items()
        if key not in {
            "type02SourcePrefixes",
            "type04U32VectorCandidates",
            "type02BodyFrames",
            "type07BodyFrames",
        }
    }

    report = {
        "format": "animestudio-wwise-hirc-type03-corpus-audit",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "inputSetSha256": input_set,
        "outer": {
            "reportPath": str(outer_path),
            "reportSha256": source_auth["outerReportSha256"],
            "ledgerPath": str(ledger_path),
            "ledgerSha256": source_auth["ledgerSha256"],
            "primaryAssets": outer["primaryAssets"],
            "fallbackAssets": outer["fallbackAssets"],
            "fullAuditPassed": (outer.get("summary") or {}).get("fullAuditPassed"),
            "boundaryVerifiedFileCount": (outer.get("summary") or {}).get("boundaryVerifiedCount"),
            "fileLedgerRows": file_row_count,
            "sourceFingerprintCount": source_auth["sourceFingerprintCount"],
            "sourceFingerprintsMatched": source_auth["sourceFingerprintsMatched"],
            "animeStudioCliFingerprint": outer_cli_fingerprint,
        },
        "audioAudit": {
            "tool": str(cli_path),
            "toolSha256": cli_sha_before,
            "toolClosure": tool_closure_before,
            "intermediatePath": str(intermediate_path),
            "sha256": intermediate_sha,
            "hircOnly": True,
            "fileDataMd5VerifiedByAnimeStudio": True,
        },
        "corpusGate": {"path": str(corpus_gate_path), "sha256": corpus_gate_sha},
        "corpus": action_corpus,
        "evidenceBoundary": {
            "layer": 3,
            "claim": "numeric HIRC type 0x03 object bodies are byte-framed with an exact cursor when status is exact",
            "semanticStatus": "structural-only",
            "nonClaims": [
                "operation-code names or meanings",
                "serialized field ownership or names",
                "Action target identity or cross-bank relationships",
                "runtime execution, event selection, or audibility",
            ],
        },
    }
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_markdown.write_text(_markdown(report), encoding="utf-8")

    type02_report = {
        "format": "animestudio-wwise-hirc-type02-prefix-corpus-audit",
        "schemaVersion": 1,
        "generatedUtc": report["generatedUtc"],
        "status": "complete",
        "inputSetSha256": input_set,
        "outer": report["outer"],
        "audioAudit": report["audioAudit"],
        "corpusGate": report["corpusGate"],
        "corpus": {
            "packageCount": corpus["packageCount"],
            "verifiedPackageCount": corpus["verifiedPackageCount"],
            "excludedBlockCount": corpus["excludedBlockCount"],
            "identityReconciliation": {
                "verifiedPackagesMatchedToOuterLedger": True,
                "excludedBlocksMatchedToOuterLedger": True,
                "perBankSourcePrefixTotalsMatchedToPackageTotals": True,
            },
            "type02SourcePrefixes": type02_prefix_corpus,
            "audioAuditSummary": corpus["audioAuditSummary"],
        },
        "evidenceBoundary": {
            "layer": 3,
            "claim": (
                "each current numeric HIRC type 0x02 object has a bounded source prefix "
                "and plugin-type-0x02 parameter range when present; remaining body bytes are opaque"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "opaque-tail field names or internal cursor",
                "physical media placement or source-plugin semantics",
                "runtime execution, event selection, or audibility",
            ],
        },
    }
    type02_output_json.write_text(
        json.dumps(type02_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    type02_output_markdown.write_text(_type02_markdown(type02_report), encoding="utf-8")

    type04_report = {
        "format": "animestudio-wwise-hirc-type04-u32-vector-candidate-corpus-audit",
        "schemaVersion": 1,
        "generatedUtc": report["generatedUtc"],
        "status": "complete",
        "inputSetSha256": input_set,
        "outer": report["outer"],
        "audioAudit": report["audioAudit"],
        "corpusGate": report["corpusGate"],
        "corpus": {
            "packageCount": corpus["packageCount"],
            "verifiedPackageCount": corpus["verifiedPackageCount"],
            "excludedBlockCount": corpus["excludedBlockCount"],
            "identityReconciliation": {
                "verifiedPackagesMatchedToOuterLedger": True,
                "excludedBlocksMatchedToOuterLedger": True,
                "perBankCandidateFramesMatchedToPackageTotals": True,
            },
            "type04U32VectorCandidates": type04_vector_corpus,
            "audioAuditSummary": corpus["audioAuditSummary"],
        },
        "evidenceBoundary": {
            "layer": 3,
            "claim": (
                "numeric HIRC type 0x04 bodies are classified against an anonymous "
                "one-byte-count plus 32-bit-width-entry candidate frame; exact rows reach body end"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "serialized field ownership or names",
                "entry identities or meanings",
                "Action relationships or cross-bank resolution",
                "runtime execution, event selection, or audibility",
            ],
        },
    }
    type04_output_json.write_text(
        json.dumps(type04_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    type04_output_markdown.write_text(_type04_markdown(type04_report), encoding="utf-8")

    def publish_body_lane(type_key, corpus_key, lane, output_json, output_markdown):
        """Write one body lane's report and refuse to call a non-closed corpus complete."""
        closed = body_lane_corpus_is_closed(corpus[corpus_key])
        lane_report = {
            "format": f"animestudio-wwise-hirc-type{type_key[2:]}-body-corpus-audit",
            "schemaVersion": 1,
            "generatedUtc": report["generatedUtc"],
            "status": "complete" if closed else "incomplete",
            "closureEnforced": True,
            "inputSetSha256": input_set,
            "outer": report["outer"],
            "audioAudit": report["audioAudit"],
            "corpusGate": report["corpusGate"],
            "corpus": {
                "packageCount": corpus["packageCount"],
                "verifiedPackageCount": corpus["verifiedPackageCount"],
                "excludedBlockCount": corpus["excludedBlockCount"],
                "identityReconciliation": {
                    "verifiedPackagesMatchedToOuterLedger": True,
                    "excludedBlocksMatchedToOuterLedger": True,
                    "perBankBodyFramesMatchedToPackageTotals": True,
                },
                corpus_key: corpus[corpus_key],
                "audioAuditSummary": corpus["audioAuditSummary"],
            },
            "evidenceBoundary": {
                "layer": 3,
                "claim": lane.claim,
                "semanticStatus": "structural-only",
                "nonClaims": list(lane.non_claims),
                "unresolved": corpus[corpus_key]["unresolvedWidths"],
            },
        }
        output_json.write_text(
            json.dumps(lane_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        output_markdown.write_text(
            _body_lane_markdown(lane_report, corpus_key, type_key), encoding="utf-8"
        )
        if closed:
            return None
        body = corpus[corpus_key]
        return (
            f"type {type_key} body corpus did not close exactly: "
            f"exact={body['exact']} count={body['count']} "
            f"unsupported={body['unsupported']} failed={body['failed']} "
            f"nonExactBodyBytes={body['nonExactBodyBytes']}; report={output_json}"
        )

    # Publish every lane before raising: aborting on the first non-closed lane would
    # leave the later lanes' reports on disk still claiming the previous run's status.
    lanes = _build_body_lanes()
    lane_outputs = (
        ("0x02", "type02BodyFrames", type02_body_output_json, type02_body_output_markdown),
        ("0x07", "type07BodyFrames", type07_body_output_json, type07_body_output_markdown),
        ("0x05", "type05BodyFrames", type05_body_output_json, type05_body_output_markdown),
        ("0x06", "type06BodyFrames", type06_body_output_json, type06_body_output_markdown),
        ("0x0E", "type14BodyFrames", type14_body_output_json, type14_body_output_markdown),
        ("0x16", "type22BodyFrames", type22_body_output_json, type22_body_output_markdown),
    )
    lane_failures = [
        failure
        for type_key, corpus_key, lane_json, lane_markdown in lane_outputs
        if (failure := publish_body_lane(
            type_key, corpus_key, lanes[type_key], lane_json, lane_markdown
        )) is not None
    ]
    reference_corpus = corpus["referenceGraph"]
    music_head_corpus = corpus["musicHeadReferences"]
    music_head_closed = music_head_references_are_closed(music_head_corpus)
    type11_corpus = corpus["type11SourceRecords"]
    type09_corpus = corpus["type09Bodies"]
    type09_closed = type09_is_framed_except_the_second_run(type09_corpus)
    type17_corpus = corpus["type17Bodies"]
    type17_closed = type17_is_framed_except_the_tied_block(type17_corpus)
    type08_corpus = corpus["type08HeadWords"]
    type08_closed = type08_head_words_are_null_or_resolve(type08_corpus)
    type11_closed = type11_sources_share_the_type02_plugin_space(
        type11_corpus, corpus["type02SourcePrefixes"]["pluginIdCounts"]
    )
    reference_closed = (
        reference_graph_is_closed(reference_corpus)
        and music_head_closed
        and type11_closed
        and type08_closed
        and type17_closed
        and type09_closed
    )
    reference_report = {
        "format": "animestudio-wwise-hirc-reference-graph-audit",
        "schemaVersion": 1,
        "generatedUtc": report["generatedUtc"],
        "status": "complete" if reference_closed else "incomplete",
        "closureEnforced": True,
        "inputSetSha256": input_set,
        "outer": report["outer"],
        "audioAudit": report["audioAudit"],
        "corpusGate": report["corpusGate"],
        "corpus": {
            "packageCount": corpus["packageCount"],
            "verifiedPackageCount": corpus["verifiedPackageCount"],
            "excludedBlockCount": corpus["excludedBlockCount"],
            "identityReconciliation": {
                "verifiedPackagesMatchedToOuterLedger": True,
                "excludedBlocksMatchedToOuterLedger": True,
                "perBankCensusRowsSumToPackageRow": True,
            },
            "referenceGraph": reference_corpus,
            "musicHeadReferences": music_head_corpus,
            "type11SourceRecords": type11_corpus,
            "type08HeadWords": type08_corpus,
            "type17Bodies": type17_corpus,
            "type09Bodies": type09_corpus,
            "type02PluginIdCounts": corpus["type02SourcePrefixes"]["pluginIdCounts"],
            "audioAuditSummary": corpus["audioAuditSummary"],
        },
        "evidenceBoundary": {
            "layer": 4,
            "claim": (
                "every four-byte value in the exactly framed anonymous reference vectors "
                "equals the identity of exactly one HIRC object declared by the same bank, "
                "and every numeric type 0x0A and 0x0D body names one same-bank object at "
                "an offset selected by its third byte"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": reference_corpus["nonClaims"],
        },
    }
    reference_output_json.write_text(
        json.dumps(reference_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    reference_output_markdown.write_text(
        _reference_graph_markdown(reference_report), encoding="utf-8"
    )
    if not type09_closed:
        lane_failures.append(
            "type 0x09 bodies are neither framed nor fenced: "
            f"bodies={type09_corpus['bodies']} exact={type09_corpus['exact']} "
            f"open={type09_corpus['unestablishedSecondRun']} failed={type09_corpus['failed']} "
            f"categories={sorted(type09_corpus['failureCounts'])}"
        )
    if not type17_closed:
        lane_failures.append(
            "type 0x11 bodies are neither framed nor fenced: "
            f"bodies={type17_corpus['bodies']} exact={type17_corpus['exact']} "
            f"fenced={type17_corpus['fenced']} failed={type17_corpus['failed']} "
            f"categories={sorted(type17_corpus['failureCounts'])}"
        )
    if not type08_closed:
        lane_failures.append(
            "type 0x08 head words are not null-or-resolved: "
            f"bodies={type08_corpus['bodies']} resolved={type08_corpus['resolved']} "
            f"null={type08_corpus['null']} unresolved={type08_corpus['unresolved']} "
            f"tooShort={type08_corpus['tooShort']}"
        )
    if not type11_closed:
        lane_failures.append(
            "type 0x0B source records do not share the type 0x02 plug-in space: "
            f"records={type11_corpus['records']} outOfRange={type11_corpus['recordsOutOfRange']} "
            f"tooShort={type11_corpus['tooShort']} plugins={sorted(type11_corpus['pluginIdCounts'])}"
        )
    if not music_head_closed:
        lane_failures.append(
            "type 0x0A/0x0D head references are not closed: "
            f"bodies={music_head_corpus['bodies']} resolved={music_head_corpus['resolved']} "
            f"unresolved={music_head_corpus['unresolved']} zero={music_head_corpus['zero']} "
            f"unknownDiscriminant={music_head_corpus['unknownDiscriminant']} "
            f"tooShort={music_head_corpus['tooShort']}"
        )
    if not reference_closed:
        lane_failures.append(
            "HIRC reference graph did not close: "
            f"references={reference_corpus['references']} "
            f"unresolved={reference_corpus['unresolvedInBank']} "
            f"self={reference_corpus['selfReferences']} "
            f"multiReferrer={reference_corpus['targetsWithMultipleReferrers']} "
            f"duplicateIdRefs={reference_corpus['referencesToDuplicateIds']}; "
            f"report={reference_output_json}"
        )
    if lane_failures:
        raise ValueError("; ".join(lane_failures))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--intermediate", type=Path, default=DEFAULT_TEMP_AUDIT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-markdown", type=Path, default=None)
    parser.add_argument("--type02-output-json", type=Path, default=DEFAULT_TYPE02_OUTPUT)
    parser.add_argument("--type02-output-markdown", type=Path, default=None)
    parser.add_argument("--type04-output-json", type=Path, default=DEFAULT_TYPE04_OUTPUT)
    parser.add_argument("--type04-output-markdown", type=Path, default=None)
    parser.add_argument("--type02-body-output-json", type=Path, default=DEFAULT_TYPE02_BODY_OUTPUT)
    parser.add_argument("--type02-body-output-markdown", type=Path, default=None)
    parser.add_argument("--type07-body-output-json", type=Path, default=DEFAULT_TYPE07_BODY_OUTPUT)
    parser.add_argument("--type14-body-output-json", type=Path, default=DEFAULT_TYPE14_BODY_OUTPUT)
    parser.add_argument("--type22-body-output-json", type=Path, default=DEFAULT_TYPE22_BODY_OUTPUT)
    parser.add_argument("--type22-body-output-markdown", type=Path, default=None)
    parser.add_argument("--type14-body-output-markdown", type=Path, default=None)
    parser.add_argument("--type07-body-output-markdown", type=Path, default=None)
    parser.add_argument("--type05-body-output-json", type=Path, default=DEFAULT_TYPE05_BODY_OUTPUT)
    parser.add_argument("--type05-body-output-markdown", type=Path, default=None)
    parser.add_argument("--type06-body-output-json", type=Path, default=DEFAULT_TYPE06_BODY_OUTPUT)
    parser.add_argument("--type06-body-output-markdown", type=Path, default=None)
    parser.add_argument("--reference-output-json", type=Path, default=DEFAULT_REFERENCE_OUTPUT)
    parser.add_argument("--reference-output-markdown", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = run_current_corpus_audit(
            expected_input_set_sha256=args.expected_input_set_sha256,
            outer_path=args.outer_report,
            ledger_path=args.outer_ledger,
            cli_path=args.animestudio_cli,
            intermediate_path=args.intermediate,
            output_json=args.output_json,
            output_markdown=args.output_markdown,
            type02_output_json=args.type02_output_json,
            type02_output_markdown=args.type02_output_markdown,
            type04_output_json=args.type04_output_json,
            type04_output_markdown=args.type04_output_markdown,
            type02_body_output_json=args.type02_body_output_json,
            type02_body_output_markdown=args.type02_body_output_markdown,
            type07_body_output_json=args.type07_body_output_json,
            type07_body_output_markdown=args.type07_body_output_markdown,
            type05_body_output_json=args.type05_body_output_json,
            type05_body_output_markdown=args.type05_body_output_markdown,
            type06_body_output_json=args.type06_body_output_json,
            type06_body_output_markdown=args.type06_body_output_markdown,
            type14_body_output_json=args.type14_body_output_json,
            type14_body_output_markdown=args.type14_body_output_markdown,
            type22_body_output_json=args.type22_body_output_json,
            type22_body_output_markdown=args.type22_body_output_markdown,
            reference_output_json=args.reference_output_json,
            reference_output_markdown=args.reference_output_markdown,
        )
        type02_report = json.loads(args.type02_output_json.read_text(encoding="utf-8"))
        type04_report = json.loads(args.type04_output_json.read_text(encoding="utf-8"))
        type02_body_report = json.loads(args.type02_body_output_json.read_text(encoding="utf-8"))
        type07_body_report = json.loads(args.type07_body_output_json.read_text(encoding="utf-8"))
        type05_body_report = json.loads(args.type05_body_output_json.read_text(encoding="utf-8"))
        reference_report = json.loads(args.reference_output_json.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"HIRC Action current-corpus audit failed: {exc}", file=sys.stderr)
        return 1

    actions = report["corpus"]["type03Objects"]
    print(
        "HIRC type 0x03 current corpus: "
        f"{actions['exact']:,}/{actions['count']:,} exact; "
        f"unsupported={actions['unsupported']:,} failed={actions['failed']:,} "
        f"ambiguous={actions['ambiguous']:,}; inputSetSha256={report['inputSetSha256']}"
    )
    prefixes = type02_report["corpus"]["type02SourcePrefixes"]
    print(
        "HIRC type 0x02 source-prefix current corpus: "
        f"{prefixes['count']:,} objects; prefix={prefixes['prefixBytes']:,} bytes; "
        f"opaqueTail={prefixes['opaqueTailBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x02 report: {args.type02_output_json}")
    vectors = type04_report["corpus"]["type04U32VectorCandidates"]
    print(
        "HIRC type 0x04 anonymous-vector current corpus: "
        f"{vectors['exact']:,}/{vectors['count']:,} exact; "
        f"unsupported={vectors['unsupported']:,} failed={vectors['failed']:,}; "
        f"opaqueTail={vectors['opaqueTailBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x04 report: {args.type04_output_json}")
    bodies = type02_body_report["corpus"]["type02BodyFrames"]
    print(
        "HIRC type 0x02 whole-body current corpus: "
        f"{bodies['exact']:,}/{bodies['count']:,} exact; "
        f"unsupported={bodies['unsupported']:,} failed={bodies['failed']:,}; "
        f"nonExactBody={bodies['nonExactBodyBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x02 body report: {args.type02_body_output_json}")
    bodies07 = type07_body_report["corpus"]["type07BodyFrames"]
    print(
        "HIRC type 0x07 whole-body current corpus: "
        f"{bodies07['exact']:,}/{bodies07['count']:,} exact; "
        f"unsupported={bodies07['unsupported']:,} failed={bodies07['failed']:,}; "
        f"nonExactBody={bodies07['nonExactBodyBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x07 body report: {args.type07_body_output_json}")
    type14_body_report = json.loads(args.type14_body_output_json.read_text(encoding="utf-8"))
    bodies14 = type14_body_report["corpus"]["type14BodyFrames"]
    print(
        "HIRC type 0x0E whole-body current corpus: "
        f"{bodies14['exact']:,}/{bodies14['count']:,} exact; "
        f"unsupported={bodies14['unsupported']:,} failed={bodies14['failed']:,}; "
        f"nonExactBody={bodies14['nonExactBodyBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x0E body report: {args.type14_body_output_json}")
    bodies05 = type05_body_report["corpus"]["type05BodyFrames"]
    print(
        "HIRC type 0x05 whole-body current corpus: "
        f"{bodies05['exact']:,}/{bodies05['count']:,} exact; "
        f"unsupported={bodies05['unsupported']:,} failed={bodies05['failed']:,}; "
        f"nonExactBody={bodies05['nonExactBodyBytes']:,} bytes; inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Type 0x05 body report: {args.type05_body_output_json}")
    graph = reference_report["corpus"]["referenceGraph"]
    print(
        "HIRC anonymous reference graph: "
        f"{graph['resolvedSameBank']:,}/{graph['references']:,} name one same-bank object; "
        f"unresolved={graph['unresolvedInBank']:,} self={graph['selfReferences']:,} "
        f"multiReferrer={graph['targetsWithMultipleReferrers']:,}; "
        f"inputSetSha256={report['inputSetSha256']}"
    )
    print(f"Reference graph report: {args.reference_output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
