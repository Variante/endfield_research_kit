"""Bind the AnimeStudio HIRC Action-body cursor audit to the current VFS set."""

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
DEFAULT_TEMP_AUDIT = ROOT / "tmp/audio/hirc_action_current/audio_audit.json"
INPUT_SET_RE = re.compile(r"^[0-9A-F]{64}$")
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
    for row in verified_rows:
        package = row.get("package") or {}
        type_counts = package.get("hircObjectTypeCounts") or {}
        expected_type03 = int(type_counts.get("0x03") or 0)
        frame = package.get("hircType03ActionFrame")
        if not isinstance(frame, dict):
            raise ValueError(f"missing type 0x03 cursor result: {row.get('block')}:{row.get('path')}")
        count = int(frame.get("count") or 0)
        exact = int(frame.get("exact") or 0)
        unsupported = int(frame.get("unsupported") or 0)
        failed = int(frame.get("failed") or 0)
        ambiguous = int(frame.get("ambiguous") or 0)
        if count != expected_type03 or count != exact + unsupported + failed + ambiguous:
            raise ValueError(
                "type 0x03 audit count mismatch: "
                f"{row.get('block')}:{row.get('path')} "
                f"objects={expected_type03} framed={count} "
                f"exact={exact} unsupported={unsupported} failed={failed} ambiguous={ambiguous}"
            )
        if ambiguous != 0:
            raise ValueError(
                f"unexpected ambiguous type 0x03 frame result: {row.get('block')}:{row.get('path')}"
            )
        package_metrics = _read_frame_metrics(frame, f"{row.get('block')}:{row.get('path')}")
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
            bank_type03_count = int(
                ((bank.get("hircObjectTypeStats") or {}).get("0x03") or {}).get("count") or 0
            )
            bank_frame = bank.get("hircType03ActionFrame")
            bank_name = f"{row.get('block')}:{row.get('path')} bank={bank.get('bankId')}"
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
    return {
        "packageCount": expected_packages,
        "verifiedPackageCount": len(verified_rows),
        "excludedBlockCount": len(expected_excluded_statuses),
        "identityReconciliation": {
            "verifiedPackagesMatchedToOuterLedger": True,
            "excludedBlocksMatchedToOuterLedger": True,
            "perBankFramesMatchedToPackageFrames": True,
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
            f"Raw AnimeStudio package audit: `{report['audioAudit']['intermediatePath']}` (SHA-256 `{report['audioAudit']['sha256']}`).",
            "",
        ]
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
    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown = output_markdown or output_json.with_suffix(".md")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)

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
    if not intermediate_path.is_file():
        raise ValueError(f"AnimeStudio audio-audit did not write its report: {intermediate_path}")
    audio_audit = json.loads(intermediate_path.read_text(encoding="utf-8"))
    corpus = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)

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
        },
        "audioAudit": {
            "tool": str(cli_path),
            "intermediatePath": str(intermediate_path),
            "sha256": sha256_file(intermediate_path),
            "hircOnly": True,
            "fileDataMd5VerifiedByAnimeStudio": True,
        },
        "corpus": corpus,
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
        )
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
