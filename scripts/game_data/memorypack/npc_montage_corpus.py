"""Gate current NPC Montage VFS bytes through the maintained MemoryPack frame.

The outer VFS ledger authenticates file identity and encrypted boundaries.
AnimeStudio stream --verify-md5 supplies decrypted logical bytes; every selected
row must join one-for-one before the parser may certify physical EOF.
"""

from __future__ import annotations

import argparse
import base64
import binascii
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

from . import corpus_gate as vfs
from .npc_montage import (
    NPC_MONTAGE_RELATIVE_PREFIX,
    NpcMontageFramingError,
    frame_npc_montage,
)


NPC_MONTAGE_PATTERN = re.compile(
    r"^Data/Json/NPC/MontageJson/MontageNew/.+[.]json$"
)
NPC_MONTAGE_REPORT_FORMAT = "animestudio-npc-montage-current-vfs-corpus"
DEFAULT_JSON = (
    vfs.MODULE_REPO_ROOT / "reports/animestudio/npc_montage_current_latest.json"
)
DEFAULT_MD = (
    vfs.MODULE_REPO_ROOT / "reports/animestudio/npc_montage_current_latest.md"
)


def select_rows(
    file_rows: Iterable[Mapping[str, Any]], *, expected_input: str
) -> list[dict[str, Any]]:
    """Select every verified JsonData row in the exact MontageNew family."""
    return vfs.family_rows(
        file_rows,
        expected_input=expected_input,
        prefix=NPC_MONTAGE_RELATIVE_PREFIX,
        pattern=NPC_MONTAGE_PATTERN,
        label="npc-montage",
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
        NPC_MONTAGE_PATTERN.pattern,
        "--verify-md5",
    ]


def _iter_stream_rows(command: list[str]):
    """Yield AnimeStudio JSONL rows and retain bounded stderr on process errors."""
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


def _join_and_frame(
    ledger_rows: list[Mapping[str, Any]],
    stream_rows: Iterable[Mapping[str, Any]],
    *,
    expected_input: str,
) -> list[dict[str, Any]]:
    """Join the complete selected family and frame each authenticated file."""
    ledger_by_path = {str(row["virtualPath"]): row for row in ledger_rows}
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, stream_row in enumerate(stream_rows):
        path = stream_row.get("fileName")
        if not isinstance(path, str) or path not in ledger_by_path:
            vfs._fail(
                "unexpected-stream-identity",
                source=f"stream[{index}].fileName",
                expected="selected current NPC Montage identity",
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
        except (binascii.Error, ValueError) as exc:
            vfs._fail("stream-base64-invalid", source=path, actual=str(exc))
        if length != len(data) or length != ledger["length"]:
            vfs._fail(
                "stream-length-mismatch",
                source=path,
                expected=ledger["length"],
                actual={"declared": length, "decoded": len(data)},
            )
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != str(ledger["recomputedFileDataMd5"]).upper():
            vfs._fail(
                "stream-ledger-md5-mismatch",
                source=path,
                expected=ledger["recomputedFileDataMd5"],
                actual=actual_md5,
            )

        identity = {
            "inputSetSha256": expected_input.upper(),
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
            frame = frame_npc_montage(data)
        except NpcMontageFramingError as exc:
            results.append(
                {
                    **identity,
                    "status": "unsupported",
                    "boundaryClass": "unsupported",
                    "bytesConsumed": None,
                    "frameStatus": None,
                    "member3RecordCount": None,
                    "member3InnerRecordCount": None,
                    "member18RecordCount": None,
                    "bothCollectionsNonempty": None,
                    "diagnostic": {
                        "code": "npc-montage-frame-not-closed",
                        "category": "unsupported",
                        "source": path,
                        "inputSetSha256": expected_input.upper(),
                        "logicalSha256": identity["logicalSha256"],
                        "expected": "supported 3-member root and 24-member body through physical EOF",
                        "actual": str(exc),
                    },
                }
            )
            continue

        if frame.get("bytesConsumed") != length:
            vfs._fail(
                "parser-eof-mismatch",
                source=path,
                expected=length,
                actual=frame.get("bytesConsumed"),
            )
        member3_count = len(frame["member3Records"])
        member3_inner_count = sum(
            len(record["innerRecords"]) for record in frame["member3Records"]
        )
        member18_count = len(frame["member18Records"])
        results.append(
            {
                **identity,
                "status": "success",
                "boundaryClass": "exact-closed",
                "bytesConsumed": frame["bytesConsumed"],
                "frameStatus": frame["status"],
                "member3RecordCount": member3_count,
                "member3InnerRecordCount": member3_inner_count,
                "member18RecordCount": member18_count,
                "bothCollectionsNonempty": member3_count > 0 and member18_count > 0,
                "diagnostic": None,
            }
        )

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
    successful = [row for row in rows if row.get("status") == "success"]
    issues = sorted(
        (row["diagnostic"] for row in rows if row.get("diagnostic")),
        key=lambda row: (str(row.get("source", "")), str(row.get("code", ""))),
    )
    return {
        "filesSelected": len(rows),
        "filesJoined": len(rows),
        "filesExactClosed": statuses.get("success", 0),
        "filesUnsupported": statuses.get("unsupported", 0),
        "filesAmbiguous": statuses.get("ambiguous", 0),
        "filesFailed": statuses.get("failed", 0),
        "logicalBytes": sum(int(row["length"]) for row in rows),
        "physicalChunkCount": len({str(row["physicalChunkPath"]) for row in rows}),
        "frameStatusCounts": dict(sorted(
            Counter(str(row.get("frameStatus")) for row in successful).items()
        )),
        "member3Files": sum(int(row["member3RecordCount"]) > 0 for row in successful),
        "member3Records": sum(int(row["member3RecordCount"]) for row in successful),
        "member3InnerRecords": sum(
            int(row["member3InnerRecordCount"]) for row in successful
        ),
        "member18Files": sum(int(row["member18RecordCount"]) > 0 for row in successful),
        "member18Records": sum(int(row["member18RecordCount"]) for row in successful),
        "bothCollectionsNonemptyFiles": sum(
            bool(row["bothCollectionsNonempty"]) for row in successful
        ),
        "firstIssue": issues[0] if issues else None,
    }


def _input_paths_to_protect(
    *,
    outer_path: Path,
    ledger_path: Path,
    outer: Mapping[str, Any],
    file_rows: Iterable[Mapping[str, Any]],
    provenance: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> list[Path]:
    """Protect every input path, including chunks outside the selected family."""
    protected = [
        outer_path,
        ledger_path,
        Path(str(outer["primaryAssets"])),
        Path(str(outer["fallbackAssets"])),
    ]
    all_chunk_paths = {
        str(row["physicalChunkPath"])
        for row in file_rows
        if isinstance(row.get("physicalChunkPath"), str)
        and row["physicalChunkPath"]
    }
    protected.extend(Path(path) for path in sorted(all_chunk_paths))
    for group in (
        provenance["sourceFingerprints"],
        provenance["buildFingerprints"],
        snapshot["streamToolFingerprints"],
        snapshot["selectedChunkFingerprints"],
        snapshot["parser"],
    ):
        protected.extend(Path(row["path"]) for row in group)
    return protected


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> dict[str, Any]:
    """Authenticate, re-stream, and EOF-frame the complete current family."""
    if output_json is not None and output_md is not None:
        vfs._guard_output_path(output_json, [output_md])
    expected_input = expected_input_set_sha256.upper()
    outer, _header, file_rows, provenance_start = vfs._read_outer_and_ledger(
        outer_path,
        ledger_path,
        expected_input_set_sha256=expected_input,
    )
    selected = select_rows(file_rows, expected_input=expected_input)

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
    protected = _input_paths_to_protect(
        outer_path=outer_path,
        ledger_path=ledger_path,
        outer=outer,
        file_rows=file_rows,
        provenance=provenance_start,
        snapshot=snapshot_start,
    )
    for output in outputs:
        vfs._guard_output_path(
            output, protected + [path for path in outputs if path != output]
        )

    rows = _join_and_frame(
        selected,
        _iter_stream_rows(_stream_command(cli_path, outer)),
        expected_input=expected_input,
    )

    outer_end, _header_end, end_file_rows, provenance_end = vfs._read_outer_and_ledger(
        outer_path,
        ledger_path,
        expected_input_set_sha256=expected_input,
    )
    selected_end = select_rows(end_file_rows, expected_input=expected_input)
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
            source="NPC Montage corpus gate inputs",
            expected=vfs._canonical_sha256(snapshot_start),
            actual=vfs._canonical_sha256(snapshot_end),
        )
    for output in outputs:
        vfs._guard_output_path(
            output, protected + [path for path in outputs if path != output]
        )

    summary = _summary(rows)
    complete = (
        summary["filesExactClosed"] == summary["filesSelected"]
        and summary["filesUnsupported"] == 0
        and summary["filesAmbiguous"] == 0
        and summary["filesFailed"] == 0
    )
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
        "format": NPC_MONTAGE_REPORT_FORMAT,
        "schemaVersion": 1,
        "status": "complete" if complete else "incomplete",
        "publicationEligible": complete,
        "inputSetSha256": expected_input,
        "provenance": {
            **provenance_start,
            **snapshot_start,
            "streamArguments": [
                "stream",
                "--block-type json-data",
                f"--file-regex {NPC_MONTAGE_PATTERN.pattern}",
                "--verify-md5",
            ],
        },
        "summary": summary,
        "identitySetSha256": vfs._canonical_sha256(identity_rows),
        "wholeFamilyFrameExact": complete,
        "evidenceBoundary": (
            "Every selected NPC Montage identity is joined one-for-one from the "
            "authenticated outer VFS ledger to an AnimeStudio stream --verify-md5 "
            "row by path, length, and logical MD5. The maintained reader consumes "
            "the supported MemoryPack frame through physical EOF using explicit "
            "collection counts and nested member markers. Nested strings, scalar "
            "values, and fixed record bodies remain anonymous; this is not a claim "
            "about field meaning or runtime use."
        ),
        "files": rows,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# NPC Montage current VFS corpus",
        "",
        f"Status: `{report['status']}`; publication eligible: "
        f"`{report['publicationEligible']}`; inputSetSha256: "
        f"`{report['inputSetSha256']}`.",
        "",
        f"Joined `{summary['filesJoined']}` of `{summary['filesSelected']}` "
        f"files; exact-to-EOF: `{summary['filesExactClosed']}`; unsupported: "
        f"`{summary['filesUnsupported']}`; ambiguous: `{summary['filesAmbiguous']}`; "
        f"failed: `{summary['filesFailed']}`; logical bytes: `{summary['logicalBytes']}`.",
        "",
        f"Nonempty member 3 files/records/inner records: "
        f"`{summary['member3Files']}` / `{summary['member3Records']}` / "
        f"`{summary['member3InnerRecords']}`; nonempty member 18 files/records: "
        f"`{summary['member18Files']}` / `{summary['member18Records']}`; both "
        f"collections nonempty: `{summary['bothCollectionsNonemptyFiles']}`.",
        "",
        report["evidenceBoundary"],
        "",
        "Per-file current identities, hashes, exact frame status, and record counts "
        "are in the companion JSON.",
        "",
    ]
    first_issue = summary["firstIssue"]
    if first_issue is not None:
        lines.extend((
            "First unsupported/failed record:",
            "",
            "```json",
            json.dumps(first_issue, ensure_ascii=False, indent=2),
            "```",
            "",
        ))
    return "\n".join(lines)


def _atomic_write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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
            "source": "npc-montage-current-census",
            "offset": None,
            "expected": "current authenticated NPC Montage corpus",
            "actual": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1

    _atomic_write_markdown(args.output_md, render_markdown(report))
    vfs._atomic_write_json(args.output_json, report)
    print(json.dumps({
        "status": report["status"],
        "inputSetSha256": report["inputSetSha256"],
        "summary": report["summary"],
        "outputJson": str(args.output_json.resolve()),
        "outputMarkdown": str(args.output_md.resolve()),
    }, ensure_ascii=False))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
