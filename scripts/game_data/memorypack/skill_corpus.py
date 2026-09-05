"""Current-input SkillData corpus gate.

The authoritative outer VFS
ledger supplies identity and encrypted physical boundaries.  AnimeStudio
``stream --verify-md5`` supplies the decrypted logical bytes; every stream row
must join one-for-one to the current ledger before the MemoryPack framer runs.

Family-agnostic provenance and drift gating lives in :mod:`corpus_gate`; this
module owns only the SkillData selection, framing, and report contract.
"""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    HEX64,
    MODULE_REPO_ROOT,
    CensusGateError,
    _atomic_write_json,
    _canonical_sha256,
    _chunk_fingerprints,
    _chunk_selection_snapshot,
    _discover_blc_paths,
    _expected_blc_paths,
    _fail,
    _fingerprint,
    _guard_output_path,
    _guard_partial_output,
    _parser_source_snapshots,
    _read_outer_and_ledger,
    _require_int,
    _sha256_file,
    _snapshot_pinned_files,
    _stream_tool_snapshot,
    family_rows,
    verify_current_report_inputs as _verify_current_report_inputs,
)
from scripts.game_data.memorypack.skill import frame_skill_common_prefix, frame_skill_memorypack


SKILL_PREFIX = "Data/Json/SkillData/"
SKILL_PATTERN = re.compile(r"^Data/Json/SkillData/[^/]+[.]json$")
SKILL_REPORT_FORMAT = "animestudio-skilldata-current-vfs-corpus"

verify_current_report_inputs = functools.partial(
    _verify_current_report_inputs,
    expected_format=SKILL_REPORT_FORMAT,
    label="SkillData",
)


def _skill_rows(file_rows, *, expected_input: str) -> list[dict[str, Any]]:
    return family_rows(
        file_rows,
        expected_input=expected_input,
        prefix=SKILL_PREFIX,
        pattern=SKILL_PATTERN,
        label="skill",
    )


def _stream_command(cli_path: Path, outer: Mapping[str, Any], selected_rows: list[Mapping[str, Any]], *, partial: bool) -> list[str]:
    command = [
        str(cli_path.resolve()),
        "stream",
        "--streaming-assets", str(outer["primaryAssets"]),
        "--fallback-assets", str(outer["fallbackAssets"]),
        "--block-type", "json-data",
        "--verify-md5",
    ]
    if partial:
        for row in selected_rows:
            command.extend(("--file-regex", "^" + re.escape(str(row["virtualPath"])).replace(r"/", "/") + "$"))
    else:
        command.extend(("--file-regex", r"^Data/Json/SkillData/[^/]+[.]json$"))
    return command


def _read_stream_rows(command: list[str]) -> tuple[list[dict[str, Any]], str]:
    # The selected corpus is about 24 MiB (roughly 33 MiB base64), so bounded
    # communicate() avoids the stdout/stderr pipe deadlock of sequential drains.
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail("stream-json-invalid", source="AnimeStudio stream stdout", offset=line_number, actual=str(exc))
        if not isinstance(row, dict):
            _fail("stream-row-not-object", source="AnimeStudio stream stdout", offset=line_number, actual=type(row).__name__)
        rows.append(row)
    if process.returncode != 0:
        _fail("stream-process-failed", source=command[0], expected=0, actual={"returnCode": process.returncode, "stderr": process.stderr[-4000:]})
    return rows, process.stderr


def _join_and_frame(
    ledger_rows: list[Mapping[str, Any]],
    stream_rows: list[Mapping[str, Any]],
    *,
    stderr: str,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    ledger_by_path = {str(row["virtualPath"]): row for row in ledger_rows}
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    for index, stream_row in enumerate(stream_rows):
        path = stream_row.get("fileName")
        if not isinstance(path, str) or path not in ledger_by_path:
            _fail("unexpected-stream-identity", source=f"stream[{index}].fileName", expected="selected ledger identity", actual=path)
        if path in seen:
            _fail("duplicate-stream-identity", source=f"stream[{index}]", actual=path)
        seen.add(path)
        ledger = ledger_by_path[path]
        if stream_row.get("blockType") != "JsonData" or stream_row.get("blockTypeValue") != 19:
            _fail("stream-block-mismatch", source=path, expected=["JsonData", 19], actual=[stream_row.get("blockType"), stream_row.get("blockTypeValue")])
        length = _require_int(stream_row.get("length"), source=f"stream:{path}.length", minimum=1)
        encoded = stream_row.get("dataBase64")
        if not isinstance(encoded, str):
            _fail("stream-base64-missing", source=path, actual=type(encoded).__name__)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            _fail("stream-base64-invalid", source=path, actual=str(exc))
        if length != len(data) or length != ledger["length"]:
            _fail("stream-length-mismatch", source=path, expected=ledger["length"], actual={"declared": length, "decoded": len(data)})
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != ledger["recomputedFileDataMd5"]:
            _fail("stream-ledger-md5-mismatch", source=path, expected=ledger["recomputedFileDataMd5"], actual=actual_md5)
        identity_result = {
            "virtualPath": path,
            "blockName": ledger["blockName"],
            "blockTypeValue": ledger["blockTypeValue"],
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
            common_prefix = frame_skill_common_prefix(data)
            framed = frame_skill_memorypack(data, source=path)
        except Exception as exc:
            coverage_counts["failed-framing"] += 1
            results.append({
                **identity_result,
                "coverageStatus": "failed-framing",
                "framingFailure": {
                    "code": "skill-framer-failed",
                    "source": path,
                    "offset": "0x0",
                    "expected": "valid maintained SkillData structural profile",
                    "actual": f"{type(exc).__name__}: {exc}",
                },
                "wholeSchemaExact": False,
            })
            continue
        status_counts[framed["status"]] += 1
        prefix_end = int(common_prefix["cursorOffset"], 0)
        candidate_coverage: list[dict[str, Any]] = []
        has_overlap = False
        for candidate_index, candidate in enumerate(framed["candidates"]):
            candidate_start = int(candidate["startOffset"], 0)
            overlap = candidate_start < prefix_end
            has_overlap = has_overlap or overlap
            candidate_coverage.append({
                "candidateIndex": candidate_index,
                "prefixCertifiedRange": {"start": 0, "end": prefix_end, "endExclusive": True},
                "terminalCertifiedRange": {"start": candidate_start, "end": len(data), "endExclusive": True},
                "rangesOverlap": overlap,
                "opaqueGap": None if overlap else {
                    "start": prefix_end,
                    "end": candidate_start,
                    "length": candidate_start - prefix_end,
                },
            })
        if has_overlap:
            coverage_status = "unsupported-overlapping-independent-ranges"
        elif framed["candidateCount"] == 0:
            coverage_status = "unsupported-no-terminal-candidate"
        elif framed["candidateCount"] > 1:
            coverage_status = "ambiguous-disjoint-independent-ranges"
        else:
            coverage_status = "unique-disjoint-independent-ranges"
        coverage_counts[coverage_status] += 1
        results.append({
            **identity_result,
            "commonPrefixFraming": common_prefix,
            "framing": framed,
            "coverageStatus": coverage_status,
            "candidateCoverage": candidate_coverage,
            "wholeSchemaExact": False,
        })
    missing = sorted(set(ledger_by_path) - seen)
    if missing:
        _fail("stream-missing-identities", source="AnimeStudio stream", expected=len(ledger_by_path), actual={"count": len(seen), "firstMissing": missing[:10]})
    matches = re.findall(r"(?m)^Streamed ([0-9]+) files\s*$", stderr)
    if len(matches) != 1 or int(matches[0]) != len(stream_rows):
        _fail("stream-terminal-count-mismatch", source="AnimeStudio stream stderr", expected=len(stream_rows), actual={"matches": matches, "stderrTail": stderr[-1000:]})
    return (
        sorted(results, key=lambda row: row["virtualPath"]),
        dict(sorted(status_counts.items())),
        dict(sorted(coverage_counts.items())),
    )


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    max_files: int | None = None,
    output_path: Path | None = None,
    output_md_path: Path | None = None,
) -> dict[str, Any]:
    if max_files is not None:
        _require_int(max_files, source="maxFiles", minimum=1)
    if output_path is not None and output_md_path is not None:
        _guard_output_path(output_path, [output_md_path])
    outer, _header, file_rows, provenance_start = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    all_skill_rows = _skill_rows(file_rows, expected_input=expected_input_set_sha256.upper())
    selected = all_skill_rows if max_files is None else all_skill_rows[:max_files]
    partial = max_files is not None
    chunk_selection_start = _chunk_selection_snapshot(selected, outer)
    selected_chunks_start = _chunk_fingerprints(selected)
    stream_tool_start = _stream_tool_snapshot(cli_path)
    cli_key = os.path.normcase(str(cli_path.resolve()))
    authenticated_build_paths = {
        os.path.normcase(str(Path(row["path"]).resolve()))
        for row in provenance_start["buildFingerprints"]
    }
    if cli_key not in authenticated_build_paths:
        _fail("stream-cli-not-in-outer-build-fingerprints", source=str(cli_path.resolve()),
              expected=sorted(authenticated_build_paths), actual=cli_key)
    parser_start = _parser_source_snapshots()
    gate_start = _fingerprint(Path(__file__))
    outputs = [path for path in (output_path, output_md_path) if path is not None]
    if outputs:
        protected = [outer_path, ledger_path, Path(__file__),
                     Path(outer["primaryAssets"]), Path(outer["fallbackAssets"])]
        # Outputs must not damage unselected format families either. Retain
        # all ledger chunk paths for collision checks without hashing them.
        chunk_paths = sorted({str(row.get("physicalChunkPath")) for row in file_rows
                              if row.get("physicalChunkPath")})
        vfs_roots = [(Path(outer[field]) / "VFS").resolve()
                     for field in ("primaryAssets", "fallbackAssets")]
        for raw_path in chunk_paths:
            chunk_path = Path(raw_path).resolve()
            if not any(chunk_path.is_relative_to(root) for root in vfs_roots):
                _fail("ledger-chunk-outside-input-roots", source=raw_path,
                      expected=[str(root) for root in vfs_roots], actual=str(chunk_path))
            protected.append(chunk_path)
        protected.extend(Path(row["path"]) for row in provenance_start["sourceFingerprints"])
        protected.extend(Path(row["path"]) for row in provenance_start["buildFingerprints"])
        protected.extend(Path(row["path"]) for row in stream_tool_start)
        protected.extend(Path(row["path"]) for row in selected_chunks_start)
        protected.extend(Path(row["path"]) for row in parser_start)
        for output in outputs:
            if partial:
                _guard_partial_output(output)
            _guard_output_path(output, protected + [path for path in outputs if path != output])
    command = _stream_command(cli_path, outer, selected, partial=partial)
    stream_rows, stderr = _read_stream_rows(command)
    rows, status_counts, coverage_counts = _join_and_frame(selected, stream_rows, stderr=stderr)

    _outer_end, _header_end, end_file_rows, provenance_end = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    end_skill_rows = _skill_rows(end_file_rows, expected_input=expected_input_set_sha256.upper())
    if [row["virtualPath"] for row in end_skill_rows] != [row["virtualPath"] for row in all_skill_rows]:
        _fail("skill-ledger-set-drift", source=str(ledger_path), expected=len(all_skill_rows), actual=len(end_skill_rows))
    stream_tool_end = _stream_tool_snapshot(cli_path)
    selected_chunks_end = _chunk_fingerprints(selected)
    chunk_selection_end = _chunk_selection_snapshot(selected, outer)
    parser_end = _parser_source_snapshots()
    gate_end = _fingerprint(Path(__file__))
    if provenance_start != provenance_end:
        _fail("outer-provenance-drift", source=str(outer_path), expected=provenance_start, actual=provenance_end)
    if stream_tool_start != stream_tool_end:
        _fail("stream-tool-drift", source=str(cli_path), expected=stream_tool_start, actual=stream_tool_end)
    if selected_chunks_start != selected_chunks_end:
        _fail("selected-chunk-drift", source="SkillData physical chunks", expected=selected_chunks_start, actual=selected_chunks_end)
    if chunk_selection_start != chunk_selection_end:
        _fail("chunk-overlay-selection-drift", source="SkillData chunk selection", expected=chunk_selection_start, actual=chunk_selection_end)
    if parser_start != parser_end or gate_start != gate_end:
        _fail("code-drift", source="SkillData census code", expected={"parser": parser_start, "corpusGate": gate_start}, actual={"parser": parser_end, "corpusGate": gate_end})
    for output in outputs:
        _guard_output_path(output, protected + [path for path in outputs if path != output])

    identity_rows = [
        {key: row[key] for key in (
            "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
            "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
            "chunkOverlayState", "physicalOffset", "encrypted",
        )}
        for row in rows
    ]
    unique_count = coverage_counts.get("unique-disjoint-independent-ranges", 0)
    ambiguous_count = coverage_counts.get("ambiguous-disjoint-independent-ranges", 0)
    failed_count = coverage_counts.get("failed-framing", 0)
    unsupported_count = len(rows) - unique_count - ambiguous_count - failed_count
    final_status = "failed" if failed_count else "partial" if partial else "complete"
    return {
        "format": SKILL_REPORT_FORMAT,
        "schemaVersion": 1,
        "status": final_status,
        "publicationEligible": not partial and failed_count == 0,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "provenance": {
            **provenance_start,
            "combinedOuterFingerprintCount": len(provenance_start["sourceFingerprints"]) + len(provenance_start["buildFingerprints"]),
            "streamToolFingerprints": stream_tool_start,
            "selectedChunkFingerprints": selected_chunks_start,
            "selectedChunkResolution": chunk_selection_start,
            "parser": parser_start,
            "corpusGate": gate_start,
        },
        "summary": {
            "ledgerSkillFiles": len(all_skill_rows),
            "filesSelected": len(selected),
            "filesSucceeded": len(rows) - failed_count,
            "filesFailed": failed_count,
            "filesUnique": unique_count,
            "filesAmbiguous": ambiguous_count,
            "filesUnsupported": unsupported_count,
            "logicalBytes": sum(row["length"] for row in rows),
            "physicalChunkCount": len({row["physicalChunkPath"] for row in rows}),
            "framingStatusCounts": status_counts,
            "coverageStatusCounts": coverage_counts,
        },
        "identitySetSha256": _canonical_sha256(identity_rows),
        "wholeSchemaExact": False,
        "evidenceBoundary": (
            "current outer-ledger identities plus AnimeStudio stream --verify-md5 decrypted bytes; "
            "the maintained framer proves only the 48-member envelope and anonymous EOF terminal "
            "candidate shapes, while prefix fields, candidate ownership, field order, and semantics remain unresolved"
        ),
        "files": rows,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SkillData current VFS corpus", "",
        f"Status: `{report['status']}`; inputSetSha256: `{report['inputSetSha256']}`.", "",
        f"Selected: {summary['filesSelected']}/{summary['ledgerSkillFiles']}; "
        f"successful: {summary['filesSucceeded']}; failed: {summary['filesFailed']}; "
        f"unsupported: {summary['filesUnsupported']}.",
        f"Unique supported candidates: {summary['filesUnique']}; "
        f"ambiguous: {summary['filesAmbiguous']}; logical bytes: {summary['logicalBytes']}.", "",
        report["evidenceBoundary"], "",
        "A candidate is not an independently proven formatter start. "
        "Whole-schema exactness and field semantics remain unresolved.", "",
        "Full identities, hashes, ranges and source gates are in the companion JSON.", "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_current_census(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            cli_path=args.animestudio_cli,
            expected_input_set_sha256=args.expected_input_set_sha256,
            max_files=args.max_files,
            output_path=args.output,
            output_md_path=args.output_md,
        )
        if args.output_md is not None:
            if args.max_files is not None:
                _guard_partial_output(args.output_md)
            protected = [args.output, args.outer_summary, args.outer_ledger]
            provenance = result["provenance"]
            for field in ("sourceFingerprints", "buildFingerprints", "streamToolFingerprints",
                          "selectedChunkFingerprints", "parser"):
                protected.extend(Path(row["path"]) for row in provenance[field])
            _guard_output_path(args.output_md, protected)
            args.output_md.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(dir=args.output_md.parent, suffix=".tmp")
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(render_markdown(result))
                os.replace(temporary, args.output_md)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        # JSON is the final publication marker after the optional Markdown.
        _atomic_write_json(args.output, result)
    except Exception as exc:
        diagnostic = exc.diagnostic if isinstance(exc, CensusGateError) else {
            "code": "unexpected-error", "source": "skilldata-current-census", "offset": None,
            "expected": None, "actual": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "files": result["summary"]["filesSucceeded"], "output": str(args.output)}, ensure_ascii=False))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
