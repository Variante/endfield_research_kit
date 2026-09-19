"""Gate the current VFS LipSync corpus through the maintained MemoryPack reader.

The full family is substantially larger than the other JsonData audits, so
AnimeStudio's JSONL stream is consumed one row at a time. Logical bytes must
join the current VFS ledger by path, length and MD5 before the strict reader
may classify an entry as exact-to-EOF.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts.game_data.memorypack import corpus_gate as vfs
from scripts.game_data.memorypack.lipsync import (
    LIPSYNC_FIELD_NAMES,
    LipSyncDecodeError,
    decode_lipsync_memorypack,
)


LIPSYNC_PREFIX = "Data/Json/LipSync/"
LIPSYNC_PATTERN = re.compile(r"^Data/Json/LipSync/.+[.]json$")
LIPSYNC_REPORT_FORMAT = "animestudio-lipsync-current-vfs-corpus"
DEFAULT_JSON = vfs.MODULE_REPO_ROOT / "reports/animestudio/lipsync_current_latest.json"
DEFAULT_MD = vfs.MODULE_REPO_ROOT / "reports/animestudio/lipsync_current_latest.md"


def select_rows(file_rows: Iterable[Mapping[str, Any]], *, expected_input: str) -> list[dict[str, Any]]:
    """Select every current, verified JsonData row in the LipSync family."""
    return vfs.family_rows(
        file_rows,
        expected_input=expected_input,
        prefix=LIPSYNC_PREFIX,
        pattern=LIPSYNC_PATTERN,
        label="lipsync",
    )


def _stream_command(cli_path: Path, outer: Mapping[str, Any]) -> list[str]:
    return [
        str(cli_path.resolve()),
        "stream",
        "--streaming-assets",
        str(outer["primaryAssets"]),
        "--fallback-assets",
        str(outer["fallbackAssets"]),
        "--block-type",
        "json-data",
        "--file-regex",
        r"^Data/Json/LipSync/.+[.]json$",
        "--verify-md5",
    ]


def _iter_stream_rows(command: list[str]):
    """Yield AnimeStudio JSONL rows without buffering this 700 MiB family."""
    with tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            encoding="utf-8",
            errors="strict",
            bufsize=1,
        )
        assert process.stdout is not None
        try:
            for line_number, line in enumerate(process.stdout, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    vfs._fail(
                        "stream-json-invalid",
                        source="AnimeStudio stream stdout",
                        offset=line_number,
                        actual=str(exc),
                    )
                if not isinstance(row, dict):
                    vfs._fail(
                        "stream-row-not-object",
                        source="AnimeStudio stream stdout",
                        offset=line_number,
                        actual=type(row).__name__,
                    )
                yield row
            return_code = process.wait()
            if return_code != 0:
                stderr_file.seek(max(0, stderr_file.tell() - 4000))
                stderr_tail = stderr_file.read().decode("utf-8", errors="replace")
                vfs._fail(
                    "stream-process-failed",
                    source=command[0],
                    expected=0,
                    actual={"returnCode": return_code, "stderr": stderr_tail},
                )
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()


def _join_and_decode(
    ledger_rows: list[Mapping[str, Any]],
    stream_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Join every current row and record exact parser results or failures."""
    ledger_by_path = {str(row["virtualPath"]): row for row in ledger_rows}
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, stream_row in enumerate(stream_rows):
        path = stream_row.get("fileName")
        if not isinstance(path, str) or path not in ledger_by_path:
            vfs._fail(
                "unexpected-stream-identity",
                source=f"stream[{index}].fileName",
                expected="selected current LipSync identity",
                actual=path,
            )
        if path in seen:
            vfs._fail("duplicate-stream-identity", source=f"stream[{index}]", actual=path)
        seen.add(path)
        ledger = ledger_by_path[path]
        if stream_row.get("blockType") != "JsonData" or stream_row.get("blockTypeValue") != 19:
            vfs._fail(
                "stream-block-mismatch",
                source=path,
                expected=["JsonData", 19],
                actual=[stream_row.get("blockType"), stream_row.get("blockTypeValue")],
            )
        length = vfs._require_int(stream_row.get("length"), source=f"{path}.length", minimum=1)
        encoded = stream_row.get("dataBase64")
        if not isinstance(encoded, str):
            vfs._fail("stream-base64-missing", source=path, actual=type(encoded).__name__)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            vfs._fail("stream-base64-invalid", source=path, actual=str(exc))
        if length != len(data) or length != ledger["length"]:
            vfs._fail(
                "stream-length-mismatch",
                source=path,
                expected=ledger["length"],
                actual={"declared": length, "decoded": len(data)},
            )
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != ledger["recomputedFileDataMd5"]:
            vfs._fail(
                "stream-ledger-md5-mismatch",
                source=path,
                expected=ledger["recomputedFileDataMd5"],
                actual=actual_md5,
            )

        identity = {
            "inputSetSha256": str(ledger["inputSetSha256"]).upper(),
            "virtualPath": path,
            "length": length,
            "logicalMd5": actual_md5,
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
            "physicalChunkPath": ledger["physicalChunkPath"],
            "physicalChunkSource": ledger["physicalChunkSource"],
            "metadataProvenance": ledger["metadataProvenance"],
            "overlayState": ledger["overlayState"],
            "chunkOverlayState": ledger["chunkOverlayState"],
            "physicalOffset": ledger["offset"],
            "encrypted": ledger["encrypted"],
        }
        try:
            channels = decode_lipsync_memorypack(data)
        except LipSyncDecodeError as exc:
            results.append({
                **identity,
                "status": "failed",
                "bytesConsumed": None,
                "channelCount": None,
                "nonNullChannels": None,
                "rowCountsByChannel": None,
                "diagnostic": {
                    "code": "lipsync-framing-failed",
                    "source": path,
                    "offset": None,
                    "expected": "current 15-member, six-float MemoryPack frame through EOF",
                    "actual": str(exc),
                },
            })
            continue

        if tuple(channels) != LIPSYNC_FIELD_NAMES:
            vfs._fail(
                "lipsync-channel-order-mismatch",
                source=path,
                expected=list(LIPSYNC_FIELD_NAMES),
                actual=list(channels),
            )
        row_counts = {
            name: (None if channels[name] is None else len(channels[name]))
            for name in LIPSYNC_FIELD_NAMES
        }
        results.append({
            **identity,
            "status": "exact-closed",
            "bytesConsumed": length,
            "channelCount": len(channels),
            "nonNullChannels": sum(value is not None for value in channels.values()),
            "rowCountsByChannel": row_counts,
            "diagnostic": None,
        })

    missing = sorted(set(ledger_by_path) - seen)
    if missing:
        vfs._fail(
            "stream-missing-current-identities",
            source="AnimeStudio stream stdout",
            expected=len(ledger_by_path),
            actual={"joined": len(seen), "firstMissing": missing[0]},
        )
    if len(seen) != len(ledger_by_path):
        vfs._fail(
            "stream-current-count-mismatch",
            source="AnimeStudio stream stdout",
            expected=len(ledger_by_path),
            actual=len(seen),
        )
    return sorted(results, key=lambda row: row["virtualPath"])


def _summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status", "failed")) for row in rows)
    successful = [row for row in rows if row.get("status") == "exact-closed"]
    row_counts = Counter()
    non_null_files = Counter()
    null_files = Counter()
    empty_files = Counter()
    for row in successful:
        for name, count in row["rowCountsByChannel"].items():
            if count is None:
                null_files[name] += 1
            else:
                non_null_files[name] += 1
                row_counts[name] += count
                if count == 0:
                    empty_files[name] += 1
    failures = sorted(
        (row["diagnostic"] for row in rows if row.get("diagnostic")),
        key=lambda row: (str(row.get("source", "")), str(row.get("code", ""))),
    )
    return {
        "filesSelected": len(rows),
        "filesJoined": len(rows),
        "filesExactClosed": statuses.get("exact-closed", 0),
        "filesFailed": statuses.get("failed", 0),
        "logicalBytes": sum(int(row["length"]) for row in rows),
        "physicalChunkCount": len({str(row["physicalChunkPath"]) for row in rows}),
        "frameStatusCounts": dict(sorted(statuses.items())),
        "nonNullFilesByChannel": dict(sorted(non_null_files.items())),
        "nullFilesByChannel": dict(sorted(null_files.items())),
        "emptyFilesByChannel": dict(sorted(empty_files.items())),
        "keyframeRowsByChannel": dict(sorted(row_counts.items())),
        "firstFailure": failures[0] if failures else None,
    }


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> dict[str, Any]:
    """Authenticate and decode the complete current LipSync VFS family."""
    if output_json is not None and output_md is not None:
        vfs._guard_output_path(output_json, [output_md])
    outer, _header, file_rows, provenance_start = vfs._read_outer_and_ledger(
        outer_path,
        ledger_path,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    selected = select_rows(file_rows, expected_input=expected_input_set_sha256.upper())

    def snapshot() -> dict[str, Any]:
        return {
            "selectedChunkFingerprints": vfs._chunk_fingerprints(selected),
            "selectedChunkResolution": vfs._chunk_selection_snapshot(selected, outer),
            "streamToolFingerprints": vfs._stream_tool_snapshot(cli_path),
            "parser": vfs._parser_source_snapshots(),
            "corpusGate": vfs._fingerprint(Path(__file__)),
        }

    snapshot_start = snapshot()
    cli_key = os.path.normcase(str(cli_path.resolve()))
    authenticated_build_paths = {
        os.path.normcase(str(Path(row["path"]).resolve()))
        for row in provenance_start["buildFingerprints"]
    }
    if cli_key not in authenticated_build_paths:
        vfs._fail(
            "stream-cli-not-in-outer-build-fingerprints",
            source=str(cli_path.resolve()),
            expected=sorted(authenticated_build_paths),
            actual=cli_key,
        )

    outputs = [path for path in (output_json, output_md) if path is not None]
    protected = [
        outer_path,
        ledger_path,
        Path(outer["primaryAssets"]),
        Path(outer["fallbackAssets"]),
    ]
    protected.extend(Path(row["physicalChunkPath"]) for row in selected)
    for group in (
        provenance_start["sourceFingerprints"],
        provenance_start["buildFingerprints"],
        snapshot_start["streamToolFingerprints"],
        snapshot_start["selectedChunkFingerprints"],
        snapshot_start["parser"],
    ):
        protected.extend(Path(row["path"]) for row in group)
    for output in outputs:
        vfs._guard_output_path(output, protected + [path for path in outputs if path != output])

    command = _stream_command(cli_path, outer)
    rows = _join_and_decode(selected, _iter_stream_rows(command))

    outer_end, _header_end, end_file_rows, provenance_end = vfs._read_outer_and_ledger(
        outer_path,
        ledger_path,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    selected_end = select_rows(end_file_rows, expected_input=expected_input_set_sha256.upper())
    snapshot_end = snapshot()
    if provenance_start != provenance_end:
        vfs._fail(
            "outer-provenance-drift",
            source=str(outer_path),
            expected=vfs._canonical_sha256(provenance_start),
            actual=vfs._canonical_sha256(provenance_end),
        )
    if outer != outer_end or selected != selected_end:
        vfs._fail(
            "current-ledger-drift",
            source=str(ledger_path),
            expected=vfs._canonical_sha256(selected),
            actual=vfs._canonical_sha256(selected_end),
        )
    if snapshot_start != snapshot_end:
        vfs._fail(
            "current-input-drift",
            source="LipSync corpus gate inputs",
            expected=vfs._canonical_sha256(snapshot_start),
            actual=vfs._canonical_sha256(snapshot_end),
        )
    for output in outputs:
        vfs._guard_output_path(output, protected + [path for path in outputs if path != output])

    summary = _summary(rows)
    failed = summary["filesFailed"] != 0
    identity_rows = [
        {key: row[key] for key in (
            "virtualPath",
            "length",
            "logicalMd5",
            "logicalSha256",
            "physicalChunkPath",
            "physicalChunkSource",
            "metadataProvenance",
            "overlayState",
            "chunkOverlayState",
            "physicalOffset",
            "encrypted",
        )}
        for row in rows
    ]
    return {
        "format": LIPSYNC_REPORT_FORMAT,
        "schemaVersion": 1,
        "status": "failed" if failed else "complete",
        "publicationEligible": not failed,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "provenance": {
            **provenance_start,
            **snapshot_start,
            "streamArguments": [
                "stream",
                "--block-type json-data",
                "--file-regex ^Data/Json/LipSync/.+[.]json$",
                "--verify-md5",
            ],
        },
        "summary": summary,
        "identitySetSha256": vfs._canonical_sha256(identity_rows),
        "wholeFileFrameExact": not failed,
        "evidenceBoundary": (
            "Every current LipSync identity is joined from the authenticated VFS ledger to one "
            "AnimeStudio stream --verify-md5 row by path, length and logical MD5. The maintained "
            "reader consumes the 15-member MemoryPack object through physical EOF and accepts only "
            "count-framed rows of six finite float32 values. Native Keyframe argument order names "
            "those six values; this report does not infer voice-audio availability."
        ),
        "files": rows,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# LipSync current VFS corpus",
        "",
        f"Status: `{report['status']}`; publication eligible: `{report['publicationEligible']}`; "
        f"inputSetSha256: `{report['inputSetSha256']}`.",
        "",
        f"Joined `{summary['filesJoined']}` files; exact-to-EOF: "
        f"`{summary['filesExactClosed']}`; failed: `{summary['filesFailed']}`; "
        f"logical bytes: `{summary['logicalBytes']}`.",
        "",
        report["evidenceBoundary"],
        "",
        "Per-file identities, hashes, and channel row counts are in the companion JSON.",
        "",
    ]
    if summary["firstFailure"] is not None:
        lines.extend(("First failure:", "", "```json", json.dumps(summary["firstFailure"], ensure_ascii=False, indent=2), "```", ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=vfs.DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=vfs.DEFAULT_LEDGER)
    parser.add_argument("--animestudio-cli", type=Path, default=vfs.DEFAULT_CLI)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    try:
        report = build_current_census(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            cli_path=args.animestudio_cli,
            expected_input_set_sha256=args.expected_input_set_sha256,
            output_json=args.output_json,
            output_md=args.output_md,
        )
    except vfs.CensusGateError as exc:
        print(json.dumps({"status": "failed", "diagnostic": exc.diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        diagnostic = {
            "code": "unexpected-error",
            "source": "lipsync-current-census",
            "offset": None,
            "expected": "current authenticated LipSync corpus",
            "actual": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=args.output_md.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_markdown(report))
        os.replace(temporary, args.output_md)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    vfs._atomic_write_json(args.output_json, report)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "output": str(args.output_json)}))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
