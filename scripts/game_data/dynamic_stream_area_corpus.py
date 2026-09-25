"""Authenticate and exact-frame the current DynamicStreaming FBStreamArea corpus."""

from __future__ import annotations

import argparse
import base64
import binascii
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

from scripts.game_data.dynamic_streaming import (
    OBSERVED_ROOT_SHAPES,
    OBSERVED_STREAM_AREA_INLINE_WIDTHS,
    OBSERVED_STREAM_AREA_VECTOR_WIDTHS,
    parse_dynamic_file,
)


from scripts.repo_paths import REPO_ROOT
from scripts.common import sha256_file_upper as sha256_file

ROOT = REPO_ROOT
DEFAULT_OUTER = ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_LEDGER = ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
DEFAULT_CLI = ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
DEFAULT_JSON = ROOT / "reports/animestudio/dynamic_stream_area_current_latest.json"
DEFAULT_MARKDOWN = ROOT / "reports/animestudio/dynamic_stream_area_current_latest.md"
INPUT_SET_RE = re.compile(r"^[0-9A-F]{64}$")
MD5_RE = re.compile(r"^[0-9A-F]{32}$")
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
STREAM_AREA_NAME_RE = re.compile(r"(?:^|/)FBStreamArea\.bytes$", re.IGNORECASE)
MAIN_NAME_RE = re.compile(r"(?:^|/)fb_main_[^/]+\.bytes$", re.IGNORECASE)
STREAM_AREA_FILE_REGEX = r"(?:^|/)FBStreamArea\.bytes$"



def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _resolved_identity(raw_path: str) -> str:
    return str(Path(raw_path).resolve()).replace("\\", "/").casefold()


def _verify_fingerprints(rows: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"outer VFS {label} fingerprint list is missing or empty")
    checked: list[dict[str, Any]] = []
    identities: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"outer VFS {label}[{index}] is not an object")
        raw_path = row.get("path")
        expected_sha = str(row.get("sha256") or "").upper()
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError(f"outer VFS {label}[{index}] has no source path")
        if SHA256_RE.fullmatch(expected_sha) is None:
            raise ValueError(f"outer VFS {label}[{index}] has an invalid SHA-256: {raw_path}")
        path = Path(raw_path)
        identity = _resolved_identity(raw_path)
        if identity in identities:
            raise ValueError(f"outer VFS {label} contains a duplicate source path: {raw_path}")
        identities.add(identity)
        if not path.is_file():
            raise ValueError(f"outer VFS {label} source is missing: {raw_path}")
        actual_length = path.stat().st_size
        try:
            expected_length = int(row["length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"outer VFS {label} source has an invalid length: {raw_path}") from exc
        if actual_length != expected_length:
            raise ValueError(
                f"outer VFS {label} source length mismatch: {raw_path} "
                f"expected={expected_length} actual={actual_length}"
            )
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            raise ValueError(
                f"outer VFS {label} source SHA-256 mismatch: {raw_path} "
                f"expected={expected_sha} actual={actual_sha}"
            )
        checked.append({"path": raw_path, "length": actual_length, "sha256": actual_sha})
    return checked


def _verify_build_fingerprints(rows: Any, cli_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify the pinned game build; report CLI drift for per-file revalidation."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("outer VFS buildFingerprints list is missing or empty")
    cli_identity = _resolved_identity(str(cli_path))
    checked_game_builds: list[dict[str, Any]] = []
    stream_cli: dict[str, Any] | None = None
    identities: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"outer VFS buildFingerprints[{index}] is not an object")
        raw_path = row.get("path")
        expected_sha = str(row.get("sha256") or "").upper()
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError(f"outer VFS buildFingerprints[{index}] has no source path")
        if SHA256_RE.fullmatch(expected_sha) is None:
            raise ValueError(f"outer VFS buildFingerprints[{index}] has an invalid SHA-256: {raw_path}")
        identity = _resolved_identity(raw_path)
        if identity in identities:
            raise ValueError(f"outer VFS buildFingerprints contains a duplicate source path: {raw_path}")
        identities.add(identity)
        path = Path(raw_path)
        if not path.is_file():
            raise ValueError(f"outer VFS buildFingerprints source is missing: {raw_path}")
        actual_length = path.stat().st_size
        try:
            expected_length = int(row["length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"outer VFS buildFingerprint has an invalid length: {raw_path}") from exc
        actual_sha = sha256_file(path)
        if identity == cli_identity:
            stream_cli = {
                "path": raw_path,
                "outerAuditLength": expected_length,
                "outerAuditSha256": expected_sha,
                "currentLength": actual_length,
                "currentSha256": actual_sha,
                "matchesOuterAudit": actual_length == expected_length and actual_sha == expected_sha,
            }
            continue
        if actual_length != expected_length:
            raise ValueError(
                f"outer VFS game build source length mismatch: {raw_path} "
                f"expected={expected_length} actual={actual_length}"
            )
        if actual_sha != expected_sha:
            raise ValueError(
                f"outer VFS game build source SHA-256 mismatch: {raw_path} "
                f"expected={expected_sha} actual={actual_sha}"
            )
        checked_game_builds.append({"path": raw_path, "length": actual_length, "sha256": actual_sha})
    if stream_cli is None:
        raise ValueError(
            "outer VFS buildFingerprints does not include the selected AnimeStudio CLI: "
            f"{cli_path}"
        )
    return checked_game_builds, stream_cli


def _is_dynamic_file_row(row: dict[str, Any], file_name_re: re.Pattern[str]) -> bool:
    block = str(row.get("blockName") or "").casefold()
    path = row.get("virtualPath") or row.get("fileName")
    return (
        block == "dynamicstreaming"
        and isinstance(path, str)
        and file_name_re.search(path.replace("\\", "/")) is not None
    )


def _dynamic_streaming_block_type_value(outer: dict[str, Any]) -> int:
    rows = [
        row
        for row in outer.get("blocks", [])
        if isinstance(row, dict) and str(row.get("blockName") or "").casefold() == "dynamicstreaming"
    ]
    if len(rows) != 1:
        raise ValueError(
            "outer VFS report must contain one DynamicStreaming block row: "
            f"actualCount={len(rows)}"
        )
    try:
        value = int(rows[0]["blockTypeValue"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("outer VFS DynamicStreaming block has an invalid blockTypeValue") from exc
    if value < 0:
        raise ValueError(f"outer VFS DynamicStreaming block has a negative blockTypeValue: {value}")
    return value


def _collect_current_dynamic_files(
    ledger_path: Path,
    expected_input_set_sha256: str,
    expected_file_row_count: int,
    file_name_re: re.Pattern[str],
    selection_label: str,
) -> tuple[list[dict[str, Any]], int]:
    expected_input_set = expected_input_set_sha256.upper()
    files: list[dict[str, Any]] = []
    file_row_count = 0
    seen_paths: set[str] = set()
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"outer VFS ledger row {line_number} is invalid JSON: {exc}") from exc
            if not isinstance(row, dict) or row.get("recordType") != "file":
                continue
            file_row_count += 1
            row_input_set = str(row.get("inputSetSha256") or "").upper()
            if row_input_set != expected_input_set:
                raise ValueError(
                    "outer VFS ledger row input-set mismatch: "
                    f"row={line_number} expected={expected_input_set} actual={row_input_set or '<missing>'}"
                )
            if not _is_dynamic_file_row(row, file_name_re):
                continue
            path = row.get("virtualPath") or row.get("fileName")
            assert isinstance(path, str)
            path_identity = path.replace("\\", "/").casefold()
            if path_identity in seen_paths:
                raise ValueError(f"outer VFS ledger has duplicate {selection_label} path: {path}")
            seen_paths.add(path_identity)
            status = str(row.get("boundaryStatus") or "")
            if status != "boundary_verified":
                raise ValueError(
                    f"outer VFS ledger candidate is not boundary_verified: {path} status={status or '<missing>'}"
                )
            try:
                actual_bytes = int(row["actualBytesRead"])
                declared_bytes = int(row["length"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"outer VFS ledger candidate has invalid byte counts: {path}") from exc
            if actual_bytes != declared_bytes:
                raise ValueError(
                    f"outer VFS ledger candidate byte-count mismatch: {path} "
                    f"declared={declared_bytes} actual={actual_bytes}"
                )
            declared_md5 = str(row.get("declaredFileDataMd5LittleEndianHex") or "").upper()
            recomputed_md5 = str(row.get("recomputedFileDataMd5") or "").upper()
            if MD5_RE.fullmatch(declared_md5) is None or declared_md5 != recomputed_md5:
                raise ValueError(
                    f"outer VFS ledger candidate FileDataMd5 mismatch: {path} "
                    f"declared={declared_md5 or '<missing>'} recomputed={recomputed_md5 or '<missing>'}"
                )
            chunk = row.get("chunkFile")
            source = row.get("physicalChunkPath")
            if not isinstance(chunk, str) or not chunk or not isinstance(source, str) or not source:
                raise ValueError(f"outer VFS ledger candidate lacks physical source identity: {path}")
            files.append(
                {
                    "block": "DynamicStreaming",
                    "path": path,
                    "declaredBytes": declared_bytes,
                    "fileDataMd5": recomputed_md5,
                    "chunk": chunk,
                    "source": source,
                }
            )
    if file_row_count != expected_file_row_count:
        raise ValueError(
            "outer VFS ledger file-row count mismatch: "
            f"expected={expected_file_row_count} actual={file_row_count}"
        )
    if not files:
        raise ValueError(f"outer VFS ledger has no current DynamicStreaming {selection_label} files")
    return files, file_row_count


def load_current_inputs(
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    *,
    file_name_re: re.Pattern[str] = STREAM_AREA_NAME_RE,
    selection_label: str = "FBStreamArea.bytes",
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    expected = expected_input_set_sha256.upper()
    if INPUT_SET_RE.fullmatch(expected) is None:
        raise ValueError("expected inputSetSha256 must be 64 hexadecimal characters")
    if not outer_path.is_file():
        raise ValueError(f"outer VFS report is missing: {outer_path}")
    if not ledger_path.is_file():
        raise ValueError(f"outer VFS ledger is missing: {ledger_path}")
    try:
        outer = json.loads(outer_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read outer VFS report {outer_path}: {exc}") from exc
    if not isinstance(outer, dict):
        raise ValueError("outer VFS report root must be an object")
    if outer.get("format") != "animestudio-vfs-boundary-audit" or outer.get("schemaVersion") != 1:
        raise ValueError("outer VFS report schema mismatch: expected animestudio-vfs-boundary-audit/1")
    actual_input_set = str(outer.get("inputSetSha256") or "").upper()
    if actual_input_set != expected:
        raise ValueError(
            f"outer VFS input-set mismatch: expected={expected} actual={actual_input_set or '<missing>'}"
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
    if summary.get("terminalCountsReconciled") is not True or summary.get("availableCountsReconciled") is not True:
        raise ValueError("outer VFS terminal and available counts are not reconciled")
    publication = outer.get("publication") or {}
    expected_ledger_sha = str(publication.get("ledgerSha256") or "").upper()
    actual_ledger_sha = sha256_file(ledger_path)
    if SHA256_RE.fullmatch(expected_ledger_sha) is None or actual_ledger_sha != expected_ledger_sha:
        raise ValueError(
            "outer VFS ledger publication hash mismatch: "
            f"expected={expected_ledger_sha or '<missing>'} actual={actual_ledger_sha}"
        )
    source_fingerprints = _verify_fingerprints(outer.get("sourceFingerprints"), "sourceFingerprints")
    game_build_fingerprints, stream_cli_fingerprint = _verify_build_fingerprints(
        outer.get("buildFingerprints"), cli_path
    )
    primary = outer.get("primaryAssets")
    fallback = outer.get("fallbackAssets")
    if not isinstance(primary, str) or not Path(primary).is_dir():
        raise ValueError(f"outer VFS primary asset root is missing: {primary}")
    if not isinstance(fallback, str) or not Path(fallback).is_dir():
        raise ValueError(f"outer VFS fallback asset root is missing: {fallback}")
    try:
        expected_file_rows = int(summary["ledgerFileCount"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("outer VFS report has an invalid ledgerFileCount") from exc
    files, ledger_file_rows = _collect_current_dynamic_files(
        ledger_path, expected, expected_file_rows, file_name_re, selection_label
    )
    return outer, files, {
        "outerReportSha256": sha256_file(outer_path),
        "ledgerSha256": actual_ledger_sha,
        "ledgerFileRowCount": ledger_file_rows,
        "sourceFingerprints": source_fingerprints,
        "gameBuildFingerprints": game_build_fingerprints,
        "streamCliFingerprint": stream_cli_fingerprint,
    }


def validate_stream_output(
    expected_files: list[dict[str, Any]],
    stdout: bytes,
    expected_block_type_value: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_by_path: dict[str, dict[str, Any]] = {}
    for row in expected_files:
        path = str(row.get("path") or "")
        identity = path.replace("\\", "/").casefold()
        if not identity or identity in expected_by_path:
            raise ValueError(f"current ledger has a missing or duplicate stream-area path: {path!r}")
        expected_by_path[identity] = row
    try:
        output_text = stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"AnimeStudio stream stdout is not UTF-8: {exc}") from exc
    lines = [line for line in output_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("AnimeStudio stream returned no JSONL file rows")
    parsed_files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    vector_element_counts: Counter[tuple[int, int]] = Counter()
    vector_file_counts: Counter[tuple[int, int]] = Counter()
    payload_bytes = 0
    for line_number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"AnimeStudio stream stdout line {line_number} is not JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"AnimeStudio stream stdout line {line_number} is not an object")
        if row.get("blockType") != "DynamicStreaming":
            raise ValueError(
                f"AnimeStudio stream returned the wrong block on line {line_number}: "
                f"expected=DynamicStreaming actual={row.get('blockType')}"
            )
        if type(row.get("blockTypeValue")) is not int or row["blockTypeValue"] != expected_block_type_value:
            raise ValueError(
                f"AnimeStudio stream returned the wrong DynamicStreaming block value on line {line_number}: "
                f"expected={expected_block_type_value} actual={row.get('blockTypeValue')}"
            )
        path = row.get("fileName")
        if not isinstance(path, str) or STREAM_AREA_NAME_RE.search(path.replace("\\", "/")) is None:
            raise ValueError(f"AnimeStudio stream returned a non-FBStreamArea path on line {line_number}")
        identity = path.replace("\\", "/").casefold()
        if identity in seen_paths:
            raise ValueError(f"AnimeStudio stream returned a duplicate path: {path}")
        seen_paths.add(identity)
        expected = expected_by_path.get(identity)
        if expected is None:
            raise ValueError(f"AnimeStudio stream returned a file absent from the current ledger: {path}")
        try:
            declared_length = int(row["length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"AnimeStudio stream row has an invalid length: {path}") from exc
        encoded = row.get("dataBase64")
        if not isinstance(encoded, str):
            raise ValueError(f"AnimeStudio stream row has no base64 payload: {path}")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"AnimeStudio stream row has invalid base64 payload: {path}: {exc}") from exc
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        expected_length = int(expected["declaredBytes"])
        expected_md5 = str(expected["fileDataMd5"]).upper()
        if declared_length != expected_length or len(data) != expected_length:
            raise ValueError(
                f"AnimeStudio stream length mismatch: {path} expected={expected_length} "
                f"row={declared_length} payload={len(data)}"
            )
        if actual_md5 != expected_md5:
            raise ValueError(
                f"AnimeStudio stream FileDataMd5 mismatch: {path} "
                f"expected={expected_md5} actual={actual_md5}"
            )
        try:
            framed = parse_dynamic_file("stream_area", data)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"maintained stream_area parser rejected {path}: {exc}") from exc
        decoded_length = int(framed.get("decodedBytes") or -1)
        root = framed.get("root") or {}
        vectors = framed.get("Vectors")
        inline_fields = framed.get("InlineFields")
        tail = framed.get("ContiguousVectorTail")
        if (
            decoded_length != len(data)
            or not isinstance(vectors, list)
            or not isinstance(inline_fields, list)
            or len(vectors) != len(OBSERVED_STREAM_AREA_VECTOR_WIDTHS)
            or len(inline_fields) != len(OBSERVED_STREAM_AREA_INLINE_WIDTHS)
            or int(root.get("fieldCount") or -1) != OBSERVED_ROOT_SHAPES["stream_area"][0]
        ):
            raise ValueError(
                f"maintained stream_area parser returned an incomplete frame: {path} "
                f"sourceBytes={len(data)} decodedBytes={decoded_length} "
                f"rootFieldCount={root.get('fieldCount')} "
                f"vectorCount={len(vectors) if isinstance(vectors, list) else '<invalid>'} "
                f"inlineFieldCount={len(inline_fields) if isinstance(inline_fields, list) else '<invalid>'}"
            )
        expected_tail = {
            "startOffset": int(root["tableOffset"]) + int(root["objectSize"]),
            "endOffset": len(data),
            "status": "exact",
        }
        if tail != expected_tail:
            raise ValueError(
                f"maintained stream_area parser tail mismatch: {path} "
                f"expected={expected_tail} actual={tail}"
            )
        vector_widths = {
            int(vector.get("fieldIndex", -1)): int(vector.get("elementWidth", -1))
            for vector in vectors
        }
        inline_widths = {
            int(field.get("fieldIndex", -1)): int(field.get("width", -1))
            for field in inline_fields
        }
        if vector_widths != OBSERVED_STREAM_AREA_VECTOR_WIDTHS or inline_widths != OBSERVED_STREAM_AREA_INLINE_WIDTHS:
            raise ValueError(
                f"maintained stream_area parser returned unexpected root extents: {path} "
                f"vectors={vector_widths} inline={inline_widths}"
            )
        final_vector_end = max(int(vector.get("endOffset", -1)) for vector in vectors)
        if final_vector_end != decoded_length:
            raise ValueError(
                f"maintained stream_area parser EOF mismatch: {path} "
                f"finalVectorEnd={final_vector_end} payloadEof={decoded_length}"
            )
        for vector in vectors:
            try:
                field_index = int(vector["fieldIndex"])
                element_width = int(vector["elementWidth"])
                count = int(vector["count"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"maintained stream_area parser returned an invalid vector: {path}") from exc
            if field_index < 0 or element_width <= 0 or count < 0:
                raise ValueError(f"maintained stream_area parser returned negative vector metrics: {path}")
            vector_element_counts[(field_index, element_width)] += count
            vector_file_counts[(field_index, element_width)] += 1
        payload_bytes += len(data)
        parsed_files.append(
            {
                "path": path,
                "sourceBytes": len(data),
                "fileDataMd5": actual_md5,
                "chunk": expected["chunk"],
                "source": expected["source"],
                "rootFieldCount": int(root.get("fieldCount") or 0),
                "rootObjectSize": int(root.get("objectSize") or 0),
                "finalVectorEndOffset": final_vector_end,
                "finalVectorReachesPayloadEof": True,
                "contiguousVectorTail": tail,
                "vectors": vectors,
            }
        )
    missing = sorted(set(expected_by_path) - seen_paths)
    if missing:
        names = [expected_by_path[item]["path"] for item in missing[:8]]
        raise ValueError(
            f"AnimeStudio stream omitted current ledger files: missingCount={len(missing)} examples={names}"
        )
    if len(parsed_files) != len(expected_files):
        raise ValueError(
            f"AnimeStudio stream row-count mismatch: ledger={len(expected_files)} parsed={len(parsed_files)}"
        )
    summary = {
        "fileCount": len(parsed_files),
        "sourceBytes": payload_bytes,
        "decodedBytes": payload_bytes,
        "finalVectorReachesPayloadEofCount": len(parsed_files),
        "contiguousVectorTailCount": len(parsed_files),
        "vectorFieldCounts": [
            {
                "fieldIndex": field_index,
                "elementWidth": element_width,
                "fileCount": vector_file_counts[(field_index, element_width)],
                "elementCount": vector_element_counts[(field_index, element_width)],
            }
            for field_index, element_width in sorted(vector_element_counts)
        ],
        "sourceByteLengthCounts": dict(sorted(Counter(str(row["sourceBytes"]) for row in parsed_files).items())),
    }
    return parsed_files, summary


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    vector_rows = "\n".join(
        f"| {row['fieldIndex']} | {row['elementWidth']} | {row['fileCount']:,} | {row['elementCount']:,} |"
        for row in corpus["vectorFieldCounts"]
    ) or "| _none_ | _none_ | 0 | 0 |"
    return "\n".join(
        [
            "# DynamicStreaming `FBStreamArea.bytes` contiguous-vector gate",
            "",
            f"- Status: `{report['status']}`.",
            f"- Current VFS input set: `{report['inputSetSha256']}`.",
            f"- Authenticated outer ledger: `{report['outer']['ledgerSha256']}`.",
            f"- Verified source fingerprints: {report['outer']['sourceFingerprintCount']:,}; non-CLI game build fingerprints: {report['outer']['gameBuildFingerprintsMatched']:,}/{report['outer']['buildFingerprintCount'] - 1:,}.",
            f"- Streamed and FileDataMd5-matched files: {corpus['fileCount']:,}/{corpus['fileCount']:,}.",
            f"- Maintained parser contiguous-tail and EOF checks: {corpus['contiguousVectorTailCount']:,}/{corpus['fileCount']:,}; payload bytes: {corpus['sourceBytes']:,}.",
            "- The six count words and vector bodies tile the range from the root object end through payload EOF. Record contents remain unnamed here.",
            f"- Current stream CLI matches the outer audit fingerprint: `{report['outer']['outerAuditCliMatchesCurrent']}` (outer `{report['outer']['outerAuditCliSha256']}`, current `{report['stream']['cliSha256']}`).",
            "",
            "## Current vector-width census",
            "",
            "| Root field index | Element width (bytes) | Files | Elements |",
            "|---:|---:|---:|---:|",
            vector_rows,
            "",
            "The gate establishes authenticated VFS identity, selected-build table/vector bounds, and exact contiguous tail coverage. It does not assign gameplay or runtime meaning to record contents.",
            "",
            f"AnimeStudio CLI SHA-256: `{report['stream']['cliSha256']}`; maintained parser SHA-256: `{report['parser']['sha256']}`; gate SHA-256: `{report['gate']['sha256']}`.",
            "",
        ]
    )


def run_current_gate(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    outer, expected_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256
    )
    if not cli_path.is_file():
        raise ValueError(f"AnimeStudio CLI is missing: {cli_path}")
    cli_sha = str(provenance["streamCliFingerprint"]["currentSha256"])
    parser_path = ROOT / "scripts/game_data/dynamic_streaming.py"
    parser_sha = sha256_file(parser_path)
    gate_path = Path(__file__).resolve()
    gate_sha = sha256_file(gate_path)
    command = [
        str(cli_path),
        "stream",
        "--streaming-assets",
        str(outer["primaryAssets"]),
        "--fallback-assets",
        str(outer["fallbackAssets"]),
        "--block-type",
        "dynamic-streaming",
        "--file-regex",
        STREAM_AREA_FILE_REGEX,
        "--verify-md5",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, timeout=900, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("AnimeStudio stream timed out after 900 seconds") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise ValueError(
            f"AnimeStudio stream failed with exit code {completed.returncode}: {stderr.strip()}"
        )
    block_type_value = _dynamic_streaming_block_type_value(outer)
    parsed_files, corpus = validate_stream_output(expected_files, completed.stdout, block_type_value)
    actual_parser_sha = sha256_file(parser_path)
    if actual_parser_sha != parser_sha:
        raise ValueError(
            "maintained DynamicStreaming parser changed during the gate: "
            f"before={parser_sha} after={actual_parser_sha}"
        )
    actual_cli_sha = sha256_file(cli_path)
    if actual_cli_sha != cli_sha:
        raise ValueError(
            f"AnimeStudio stream CLI changed during the gate: before={cli_sha} after={actual_cli_sha}"
        )
    actual_gate_sha = sha256_file(gate_path)
    if actual_gate_sha != gate_sha:
        raise ValueError(
            f"DynamicStreaming corpus gate changed during the run: before={gate_sha} after={actual_gate_sha}"
        )
    return {
        "format": "endfield.dynamic-stream-area-current.v2",
        "schemaVersion": 2,
        "generatedUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "current_corpus_pass",
        "inputSetSha256": str(outer["inputSetSha256"]).upper(),
        "outer": {
            "reportPath": str(outer_path),
            "reportSha256": provenance["outerReportSha256"],
            "ledgerPath": str(ledger_path),
            "ledgerSha256": provenance["ledgerSha256"],
            "ledgerFileRowCount": provenance["ledgerFileRowCount"],
            "candidateLedgerFileCount": len(expected_files),
            "sourceFingerprintCount": len(provenance["sourceFingerprints"]),
            "buildFingerprintCount": len(provenance["gameBuildFingerprints"]) + 1,
            "sourceFingerprintsMatched": len(provenance["sourceFingerprints"]),
            "gameBuildFingerprintsMatched": len(provenance["gameBuildFingerprints"]),
            "outerAuditCliSha256": provenance["streamCliFingerprint"]["outerAuditSha256"],
            "outerAuditCliMatchesCurrent": provenance["streamCliFingerprint"]["matchesOuterAudit"],
        },
        "stream": {
            "cliPath": str(cli_path),
            "cliSha256": cli_sha,
            "stdoutSha256": sha256_bytes(completed.stdout),
            "stderrSummary": completed.stderr.decode("utf-8", errors="replace").strip()[-1000:],
            "blockType": "DynamicStreaming",
            "blockTypeValue": block_type_value,
            "fileRegex": STREAM_AREA_FILE_REGEX,
            "verifyMd5": True,
        },
        "parser": {
            "path": str(parser_path),
            "sha256": parser_sha,
            "entrypoint": "scripts.game_data.dynamic_streaming.parse_dynamic_file('stream_area', bytes)",
        },
        "gate": {"path": str(gate_path), "sha256": gate_sha},
        "corpus": {
            **corpus,
            "files": parsed_files,
        },
        "evidenceBoundary": (
            "All selected FBStreamArea VFS identities match the authenticated outer ledger and "
            "physical source fingerprints; non-CLI game build fingerprints also match. The "
            "stream CLI fingerprint is recorded separately because the executable can change "
            "after the outer audit; AnimeStudio verifies each current chunk and every returned "
            "payload is independently matched to its ledger FileDataMd5. The maintained "
            "generated-accessor framing parser bounds six vectors and one 24-byte inline root "
            "field and requires their count words and bodies to tile the tail from the "
            "root object end through payload EOF. Record contents remain unnamed here; "
            "this does not establish gameplay or runtime semantics."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Authenticate and exact-frame current DynamicStreaming FBStreamArea VFS files."
    )
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        report = run_current_gate(
            outer_path=args.outer_report,
            ledger_path=args.ledger,
            cli_path=args.cli,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"DynamicStreaming stream_area current corpus gate failed: {exc}", file=sys.stderr)
        return 2
    corpus = report["corpus"]
    print(
        "DynamicStreaming stream_area current corpus gate passed: "
        f"files={corpus['fileCount']} contiguousTail={corpus['contiguousVectorTailCount']} "
        f"inputSetSha256={report['inputSetSha256']}"
    )
    print(f"JSON: {args.json_output}")
    print(f"Markdown: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
