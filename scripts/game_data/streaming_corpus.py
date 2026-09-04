"""Fail-closed current-corpus gate for authenticated block-15 Streaming files."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scripts.game_data.streaming import parse_streaming_file


SCHEMA = "endfield.streaming-root-subgraphs-corpus.v2"
FAILURE_SAMPLE_LIMIT = 25
RAW_DATA_EXCEPTIONS = {
    "Data/Streaming/PC/DevOnly/test_tifeng_range/Streaming/InitChunkData_Global_0_0.bytes",
    "Data/Streaming/PC/DevOnly/test_tifeng_range/Streaming/StreamingChunkData_Global_0_0.bytes",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _read_ledger(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headers = []
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: malformed ledger JSON: {exc.msg}"
                ) from exc
            if row.get("recordType") == "audit_header":
                headers.append(row)
            elif row.get("recordType") == "file" and row.get("blockTypeValue") == 15:
                rows.append(row)
    if len(headers) != 1:
        raise ValueError(
            f"{path}: expected exactly one audit_header, actual {len(headers)}"
        )
    if not rows:
        raise ValueError(f"{path}: expected at least one block-15 file row, actual 0")
    return headers[0], rows


def _family(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if name.startswith("InitChunkData_"):
        return "init"
    if name.startswith("StreamingChunkData_"):
        return "streaming"
    if name == "StreamingChunkInfo.bytes":
        return "info"
    raise ValueError(f"unsupported block-15 path family: {path}")


def _failure(path: str, stage: str, message: str, **details: Any) -> dict[str, Any]:
    return {"virtualPath": path, "stage": stage, "message": message, **details}


def _require_equal(
    failures: list[dict[str, Any]],
    *,
    scope: str,
    field: str,
    actual: Any,
    expected: Any,
) -> None:
    if actual != expected:
        failures.append(
            {"scope": scope, "field": field, "expected": expected, "actual": actual}
        )


def _validate_provenance(
    summary: dict[str, Any],
    header: dict[str, Any],
    ledger_path: Path,
    expected_input_set_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    expected = expected_input_set_sha256.upper()
    ledger_sha256 = _sha256_file(ledger_path)
    _require_equal(
        failures,
        scope="outer-summary",
        field="inputSetSha256",
        actual=str(summary.get("inputSetSha256", "")).upper(),
        expected=expected,
    )
    _require_equal(
        failures,
        scope="outer-summary",
        field="summary.fullAuditPassed",
        actual=(summary.get("summary") or {}).get("fullAuditPassed"),
        expected=True,
    )
    _require_equal(
        failures,
        scope="outer-summary",
        field="publication.ledgerSha256",
        actual=str((summary.get("publication") or {}).get("ledgerSha256", "")).upper(),
        expected=ledger_sha256,
    )
    _require_equal(
        failures,
        scope="outer-ledger-header",
        field="schemaVersion",
        actual=header.get("schemaVersion"),
        expected=1,
    )
    _require_equal(
        failures,
        scope="outer-ledger-header",
        field="inputSetSha256",
        actual=str(header.get("inputSetSha256", "")).upper(),
        expected=expected,
    )
    for field in ("primaryAssets", "fallbackAssets"):
        _require_equal(
            failures,
            scope="outer-ledger-header",
            field=field,
            actual=header.get(field),
            expected=summary.get(field),
        )
    return failures, {
        "inputSetSha256": expected,
        "outerSummary": str(summary.get("format", "")),
        "outerLedger": ledger_path.as_posix(),
        "outerLedgerSha256": ledger_sha256,
        "primaryAssets": header.get("primaryAssets"),
        "fallbackAssets": header.get("fallbackAssets"),
    }


def sweep(
    *,
    outer_summary_path: Path,
    outer_ledger_path: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Authenticate and parse every current block-15 row from one VFS audit."""

    expected_input_set_sha256 = expected_input_set_sha256.upper()
    empty_summary = {
        "streamingFiles": 0,
        "parsed": 0,
        "exactInfo": 0,
        "partialData": 0,
        "failed": 1,
        "unsupported": 0,
        "gateFailures": 1,
    }
    if (
        len(expected_input_set_sha256) != 64
        or any(character not in "0123456789ABCDEF" for character in expected_input_set_sha256)
    ):
        return {
            "schema": SCHEMA,
            "status": "failed",
            "failed": True,
            "inputSetSha256": expected_input_set_sha256,
            "summary": empty_summary,
            "failures": [
                {
                    "stage": "provenance",
                    "message": "expected inputSetSha256 must be exactly 64 hexadecimal characters",
                    "actual": expected_input_set_sha256,
                }
            ],
        }
    try:
        summary = json.loads(outer_summary_path.read_text(encoding="utf-8"))
        header, rows = _read_ledger(outer_ledger_path)
        failures, provenance = _validate_provenance(
            summary, header, outer_ledger_path, expected_input_set_sha256
        )
        module_root = Path(__file__).resolve().parent
        parser_path = module_root / "streaming.py"
        gate_path = Path(__file__).resolve()
        provenance["parserSha256"] = _sha256_file(parser_path)
        provenance["corpusGateSha256"] = _sha256_file(gate_path)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "failed",
            "failed": True,
            "inputSetSha256": expected_input_set_sha256,
            "summary": empty_summary,
            "failures": [
                {"stage": "provenance", "message": f"{type(exc).__name__}: {exc}"}
            ],
        }

    duplicate_paths = [
        path
        for path, count in collections.Counter(
            str(row.get("virtualPath", "")) for row in rows
        ).items()
        if count != 1
    ]
    for path in duplicate_paths[:FAILURE_SAMPLE_LIMIT]:
        failures.append(
            _failure(path, "ledger", "duplicate block-15 virtualPath", expected=1)
        )

    chunks: dict[Path, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        chunks[Path(str(row.get("physicalChunkPath", "")))].append(row)

    families: collections.Counter[str] = collections.Counter()
    encodings: collections.Counter[str] = collections.Counter()
    sources: collections.Counter[str] = collections.Counter()
    metadata_sources: collections.Counter[str] = collections.Counter()
    overlay_states: collections.Counter[str] = collections.Counter()
    field4_values: collections.Counter[str] = collections.Counter()
    field5_shapes: collections.Counter[str] = collections.Counter()
    field2_layouts: collections.Counter[str] = collections.Counter()
    field2_family_files: collections.Counter[str] = collections.Counter()
    packed_bytes = decoded_bytes = parsed_count = exact_info = partial_data = 0
    info_rows = parallel_rows = field5_references = field5_bytes = 0
    group_count = group_values = descriptors = blob_bytes = 0
    parallel_owned_bytes = parallel_ranges = parallel_reused = 0
    group_owned_bytes = group_ranges = group_reused_vtables = 0
    field2_rows = field2_owned_bytes = field2_ranges = field2_reused = 0
    field2_init_eof_files = 0
    row_failure_count = unsupported_count = 0
    identity_rows = []

    for chunk_path, chunk_rows in sorted(chunks.items(), key=lambda item: str(item[0])):
        try:
            stream = chunk_path.open("rb")
        except OSError as exc:
            row_failure_count += len(chunk_rows)
            for row in chunk_rows:
                if len(failures) < FAILURE_SAMPLE_LIMIT:
                    failures.append(
                        _failure(
                            str(row.get("virtualPath", "")),
                            "physical-read",
                            f"cannot open chunk {chunk_path}: {exc}",
                        )
                    )
            continue
        with stream:
            for row in sorted(chunk_rows, key=lambda item: int(item.get("offset", -1))):
                virtual_path = str(row.get("virtualPath", ""))
                offset = int(row.get("offset", -1))
                length = int(row.get("length", -1))
                row_errors = []
                if row.get("status") != "verified":
                    row_errors.append(f"status expected 'verified', actual {row.get('status')!r}")
                if row.get("boundaryStatus") != "boundary_verified":
                    row_errors.append(
                        "boundaryStatus expected 'boundary_verified', "
                        f"actual {row.get('boundaryStatus')!r}"
                    )
                if str(row.get("inputSetSha256", "")).upper() != expected_input_set_sha256:
                    row_errors.append("row inputSetSha256 does not match requested input set")
                if row.get("encrypted") is not False:
                    row_errors.append(f"encrypted expected false, actual {row.get('encrypted')!r}")
                if row.get("actualBytesRead") != length:
                    row_errors.append(
                        f"actualBytesRead expected {length}, actual {row.get('actualBytesRead')!r}"
                    )
                if offset < 0 or length < 0:
                    row_errors.append(f"negative physical interval offset={offset}, length={length}")
                if row_errors:
                    row_failure_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(virtual_path, "ledger", "; ".join(row_errors), offset=offset)
                        )
                    continue
                try:
                    family = _family(virtual_path)
                except ValueError as exc:
                    unsupported_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(_failure(virtual_path, "family", str(exc), offset=offset))
                    continue
                try:
                    stream.seek(offset)
                    raw = stream.read(length)
                except OSError as exc:
                    row_failure_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(virtual_path, "physical-read", str(exc), offset=offset)
                        )
                    continue
                if len(raw) != length:
                    row_failure_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "physical-read",
                                "short logical-file read",
                                offset=offset,
                                expected=length,
                                actual=len(raw),
                            )
                        )
                    continue
                actual_md5 = hashlib.md5(raw, usedforsecurity=False).hexdigest().upper()
                expected_md5 = str(row.get("recomputedFileDataMd5", "")).upper()
                if actual_md5 != expected_md5:
                    row_failure_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "physical-hash",
                                "logical-file MD5 mismatch",
                                offset=offset,
                                expected=expected_md5,
                                actual=actual_md5,
                            )
                        )
                    continue
                try:
                    parsed = parse_streaming_file(
                        family, raw, allow_raw=virtual_path in RAW_DATA_EXCEPTIONS
                    )
                except Exception as exc:
                    row_failure_count += 1
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "parse",
                                f"{type(exc).__name__}: {exc}",
                                offset=offset,
                            )
                        )
                    continue

                if family == "info":
                    inner = parsed.get("anonymousInner") or {}
                    if inner.get("status") != "exact_anonymous":
                        row_failure_count += 1
                        if len(failures) < FAILURE_SAMPLE_LIMIT:
                            failures.append(
                                _failure(
                                    virtual_path,
                                    "parse",
                                    "Info inner graph did not reach exact anonymous status",
                                    expected="exact_anonymous",
                                    actual=inner.get("status"),
                                )
                            )
                        continue
                    exact_info += 1
                    info_rows += int(inner.get("rowCount", 0))
                else:
                    parallel = parsed.get("anonymousParallelSubgraph") or {}
                    groups = parsed.get("anonymousGroupSubgraph") or {}
                    field2 = parsed.get("anonymousField2DirectSubgraph") or {}
                    if (
                        parallel.get("status") != "exact_anonymous_subgraph"
                        or groups.get("status") != "exact_anonymous_subgraph"
                        or field2.get("status")
                        != "exact_anonymous_direct_subgraph"
                    ):
                        row_failure_count += 1
                        if len(failures) < FAILURE_SAMPLE_LIMIT:
                            failures.append(
                                _failure(
                                    virtual_path,
                                    "parse",
                                    "data subgraphs did not reach exact anonymous status",
                                    expected="exact_anonymous_subgraph",
                                    actual={
                                        "parallel": parallel.get("status"),
                                        "groups": groups.get("status"),
                                        "field2": field2.get("status"),
                                    },
                                )
                            )
                        continue
                    partial_data += 1
                    field2_family_files[family] += 1
                    field2_rows += int(field2.get("rowCount", 0))
                    field2_owned_bytes += int(field2.get("ownedBytes", 0))
                    field2_ranges += int(field2.get("rangeCount", 0))
                    field2_reused += int(field2.get("reusedReferences", 0))
                    if family == "init" and field2.get("vectorEndsAtEof") is True:
                        field2_init_eof_files += 1
                    for layout in field2.get("rowLayouts") or []:
                        key = json.dumps(
                            [
                                layout.get("fieldCount"),
                                layout.get("objectSize"),
                                layout.get("presentFields"),
                                layout.get("fieldOffsets"),
                            ],
                            separators=(",", ":"),
                        )
                        field2_layouts[key] += int(layout.get("count", 0))
                    parallel_rows += int(parallel.get("parallelCount", 0))
                    parallel_owned_bytes += int(parallel.get("ownedBytes", 0))
                    parallel_ranges += int(parallel.get("rangeCount", 0))
                    parallel_reused += int(parallel.get("reusedReferences", 0))
                    field5_references += int(parallel.get("field5Field0ReferenceCount", 0))
                    field5_bytes += int(parallel.get("field5Field0ReferencedBytes", 0))
                    for value, count in (parallel.get("field4ByteValueCounts") or {}).items():
                        field4_values[str(value)] += int(count)
                    for shape in parallel.get("field5RowShapes") or []:
                        key = json.dumps(
                            [
                                shape.get("fieldCount"),
                                shape.get("objectSize"),
                                shape.get("presentFields"),
                            ],
                            separators=(",", ":"),
                        )
                        field5_shapes[key] += int(shape.get("count", 0))
                    group_count += int(groups.get("pairedGroupCount", 0))
                    group_values += int(groups.get("valueCount", 0))
                    descriptors += int(groups.get("descriptorCount", 0))
                    blob_bytes += int(groups.get("blobBytes", 0))
                    group_owned_bytes += int(groups.get("ownedBytes", 0))
                    group_ranges += int(groups.get("rangeCount", 0))
                    group_reused_vtables += int(
                        groups.get("reusedVtableReferences", 0)
                    )

                parsed_count += 1
                packed_bytes += len(raw)
                decoded_bytes += int(parsed.get("decodedBytes", 0))
                families[family] += 1
                encodings[str(parsed.get("encoding"))] += 1
                sources[str(row.get("physicalChunkSource"))] += 1
                metadata_sources[str(row.get("metadataProvenance"))] += 1
                overlay_states[str(row.get("overlayState"))] += 1
                identity_rows.append(
                    "\0".join(
                        (
                            virtual_path,
                            str(row.get("physicalChunkSource")),
                            str(row.get("chunkFile")),
                            str(offset),
                            str(length),
                            actual_md5,
                            hashlib.sha256(raw).hexdigest().upper(),
                        )
                    )
                )

    parser_sha256_at_end = _sha256_file(parser_path)
    gate_sha256_at_end = _sha256_file(gate_path)
    for label, expected_sha256, actual_sha256 in (
        ("parserSha256", provenance["parserSha256"], parser_sha256_at_end),
        ("corpusGateSha256", provenance["corpusGateSha256"], gate_sha256_at_end),
    ):
        if actual_sha256 != expected_sha256:
            failures.append(
                {
                    "scope": "current-corpus-run",
                    "stage": "provenance",
                    "field": label,
                    "message": "code changed while the corpus gate was running",
                    "expected": expected_sha256,
                    "actual": actual_sha256,
                }
            )

    failed = bool(
        failures
        or row_failure_count
        or unsupported_count
        or duplicate_paths
        or parsed_count != len(rows)
    )
    return {
        "schema": SCHEMA,
        "status": "failed" if failed else "complete",
        "failed": failed,
        "inputSetSha256": expected_input_set_sha256,
        "provenance": provenance,
        "summary": {
            "streamingFiles": len(rows),
            "parsed": parsed_count,
            "exactInfo": exact_info,
            "partialData": partial_data,
            "failed": row_failure_count,
            "unsupported": unsupported_count,
            "gateFailures": sum(
                1 for failure in failures if "virtualPath" not in failure
            ),
            "packedBytes": packed_bytes,
            "decodedBytes": decoded_bytes,
            "physicalChunks": len(chunks),
        },
        "layer1": {
            "physicalSourceCounts": dict(sorted(sources.items())),
            "metadataProvenanceCounts": dict(sorted(metadata_sources.items())),
            "overlayStateCounts": dict(sorted(overlay_states.items())),
            "logicalIdentitySetSha256": hashlib.sha256(
                "\n".join(sorted(identity_rows)).encode("utf-8")
            ).hexdigest().upper(),
        },
        "layer2": {
            "familyCounts": dict(sorted(families.items())),
            "encodingCounts": dict(sorted(encodings.items())),
            "rawDataExceptions": sorted(RAW_DATA_EXCEPTIONS),
        },
        "layer3": {
            "infoStatus": "exact_anonymous_eof" if not failed else "unvalidated",
            "infoRowCount": info_rows,
            "dataWholeFileStatus": "partial",
            "field2DirectSubgraphStatus": (
                "exact_anonymous_direct_subgraph" if not failed else "unvalidated"
            ),
            "field2VectorElementWidth": 4,
            "field2FamilyFileCounts": dict(sorted(field2_family_files.items())),
            "field2InitEmptyVectorAtEofFiles": field2_init_eof_files,
            "field2DirectRowCount": field2_rows,
            "field2DirectRowLayoutCounts": dict(sorted(field2_layouts.items())),
            "field2OwnedBytesPerFileSum": field2_owned_bytes,
            "field2RangeCountPerFileSum": field2_ranges,
            "field2ReusedReferenceCount": field2_reused,
            "field2RowFieldsStatus": "opaque",
            "parallelSubgraphStatus": (
                "exact_anonymous_subgraph" if not failed else "unvalidated"
            ),
            "parallelFieldWidths": {"3": 4, "4": 1, "5": 4},
            "parallelRowCount": parallel_rows,
            "parallelOwnedBytesPerFileSum": parallel_owned_bytes,
            "parallelRangeCountPerFileSum": parallel_ranges,
            "parallelReusedReferenceCount": parallel_reused,
            "field4ByteValueCounts": dict(sorted(field4_values.items())),
            "field5RowShapeCounts": dict(sorted(field5_shapes.items())),
            "field5Field0ReferenceCount": field5_references,
            "field5Field0ReferencedBytes": field5_bytes,
            "field5Field0Representation": "ambiguous",
            "field5Field0RepresentationCandidates": [
                "flatbuffer-string",
                "byte-vector-with-following-zero",
            ],
            "pairedGroupSubgraphStatus": (
                "exact_anonymous_subgraph" if not failed else "unvalidated"
            ),
            "pairedGroupCount": group_count,
            "pairedGroupValueCount": group_values,
            "descriptorCount": descriptors,
            "blobBytes": blob_bytes,
            "pairedGroupOwnedBytesPerFileSum": group_owned_bytes,
            "pairedGroupRangeCountPerFileSum": group_ranges,
            "pairedGroupReusedVtableReferenceCount": group_reused_vtables,
            "rangeAccountingNote": "Per-subgraph sums are not a whole-file union and must not be subtracted from decoded bytes to derive the opaque remainder.",
            "opaque": "field-2 row fields and child targets, field-5 row children other than field 0, and all bytes outside certified subgraphs",
        },
        "evidenceBoundary": {
            "exact": "Logical-file identities, envelopes, roots, Info EOF graphs, and the three indexed anonymous data subgraphs are checked byte-for-byte.",
            "structuralOnly": "Field indices, widths, record shapes, counts, ranges, and equal-count relations are serialized structure only.",
            "ambiguous": "Field-5 row field 0 has two retained representation candidates with the same proven length-prefixed byte range.",
            "unresolved": "Field-2 row fields/targets, field names, values, child payloads, cross-file ownership, runtime use, and game semantics are not claimed.",
        },
        "failures": failures[:FAILURE_SAMPLE_LIMIT],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    layer3 = report.get("layer3") or {}
    lines = [
        "# Streaming root-subgraph corpus gate",
        "",
        f"- Status: **{report.get('status')}**",
        f"- inputSetSha256: `{report.get('inputSetSha256')}`",
        f"- Files: {summary.get('parsed', 0)}/{summary.get('streamingFiles', 0)} parsed; "
        f"{summary.get('failed', 0)} failed; {summary.get('unsupported', 0)} unsupported",
        f"- Exact Info EOF: {summary.get('exactInfo', 0)}; partial data files: {summary.get('partialData', 0)}",
        f"- Bytes: {summary.get('packedBytes', 0):,} packed; {summary.get('decodedBytes', 0):,} decoded",
        "",
        "## Proven structure",
        "",
        f"- Root field 2 uses width-4 table offsets; direct rows: {layer3.get('field2DirectRowCount', 0):,}; Init empty vectors at EOF: {layer3.get('field2InitEmptyVectorAtEofFiles', 0):,}.",
        f"- Field-2 direct subgraph per-file range sums: {layer3.get('field2RangeCountPerFileSum', 0):,} ranges; {layer3.get('field2OwnedBytesPerFileSum', 0):,} owned bytes (not a whole-file union).",
        f"- Root fields 3/4/5 widths: `{layer3.get('parallelFieldWidths')}`; equal rows: {layer3.get('parallelRowCount', 0):,}.",
        f"- Parallel subgraph per-file range sums: {layer3.get('parallelRangeCountPerFileSum', 0):,} ranges; {layer3.get('parallelOwnedBytesPerFileSum', 0):,} owned bytes (not a whole-file union).",
        f"- Field-5 row field-0 references: {layer3.get('field5Field0ReferenceCount', 0):,}; referenced bytes: {layer3.get('field5Field0ReferencedBytes', 0):,}.",
        f"- Paired field-6/7 groups: {layer3.get('pairedGroupCount', 0):,}; values: {layer3.get('pairedGroupValueCount', 0):,}; descriptors: {layer3.get('descriptorCount', 0):,}; blob bytes: {layer3.get('blobBytes', 0):,}.",
        f"- Paired-group per-file range sums: {layer3.get('pairedGroupRangeCountPerFileSum', 0):,} ranges; {layer3.get('pairedGroupOwnedBytesPerFileSum', 0):,} owned bytes (not a whole-file union).",
        "",
        "## Evidence boundary",
        "",
        "The fields remain anonymous and structural-only. Field-2 row fields and child targets remain opaque. Field-5 row field 0 remains ambiguous between a FlatBuffer string and a byte vector followed by zero. All other field-5 children, cross-file ownership, runtime use, and game semantics remain unresolved.",
    ]
    failures = report.get("failures") or []
    if failures:
        lines.extend(["", "## Failure samples", ""])
        for failure in failures:
            lines.append(f"- `{failure.get('virtualPath', failure.get('scope', 'gate'))}`: {failure.get('message', failure)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outer-summary",
        type=Path,
        default=Path("reports/animestudio/vfs_understanding_latest.json"),
    )
    parser.add_argument(
        "--outer-ledger",
        type=Path,
        default=Path("reports/animestudio/vfs_understanding_files_latest.jsonl.gz"),
    )
    parser.add_argument("--input-set-sha256", required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/animestudio/streaming_root_subgraphs_latest.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("reports/animestudio/streaming_root_subgraphs_latest.md"),
    )
    args = parser.parse_args()
    report = sweep(
        outer_summary_path=args.outer_summary,
        outer_ledger_path=args.outer_ledger,
        expected_input_set_sha256=args.input_set_sha256,
    )
    _atomic_write_text(args.output_json, json.dumps(report, indent=2) + "\n")
    _atomic_write_text(args.output_md, render_markdown(report))
    summary = report.get("summary") or {}
    print(
        "Streaming corpus gate: "
        f"status={report.get('status')} parsed={summary.get('parsed', 0)}/"
        f"{summary.get('streamingFiles', 0)} failed={summary.get('failed', 0)} "
        f"unsupported={summary.get('unsupported', 0)}"
    )
    if report.get("failures"):
        print(json.dumps(report["failures"][0], ensure_ascii=False))
    return 1 if report.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
