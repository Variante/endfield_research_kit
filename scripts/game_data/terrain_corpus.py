"""Fail-closed current-corpus gate for authenticated Terrain TRET payloads."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.terrain_native import (
    DEFAULT_CONTRACT as DEFAULT_NATIVE_CONTRACT,
    validate_terrain_native_contract,
)
from scripts.terrain_tret import parse_tret_record


SCHEMA = "endfield.terrain-tret-corpus.v1"
FAILURE_SAMPLE_LIMIT = 25


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
    headers: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
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
            elif row.get("recordType") == "file" and row.get("blockTypeValue") == 22:
                rows.append(row)
    if len(headers) != 1:
        raise ValueError(
            f"{path}: expected exactly one audit_header, actual {len(headers)}"
        )
    if not rows:
        raise ValueError(f"{path}: expected at least one Terrain file row, actual 0")
    return headers[0], rows


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
            {
                "scope": scope,
                "field": field,
                "expected": expected,
                "actual": actual,
            }
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


def _failure(path: str, stage: str, message: str, **details: Any) -> dict[str, Any]:
    return {"virtualPath": path, "stage": stage, "message": message, **details}


def sweep(
    *,
    outer_summary_path: Path,
    outer_ledger_path: Path,
    expected_input_set_sha256: str,
    native_contract_path: Path = DEFAULT_NATIVE_CONTRACT,
    game_root: Path | None = None,
    native_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Authenticate and parse every current Terrain row from one outer audit."""

    expected_input_set_sha256 = expected_input_set_sha256.upper()
    if (
        len(expected_input_set_sha256) != 64
        or any(character not in "0123456789ABCDEF" for character in expected_input_set_sha256)
    ):
        return {
            "schema": SCHEMA,
            "status": "failed",
            "failed": True,
            "inputSetSha256": expected_input_set_sha256,
            "summary": {
                "terrainFiles": 0,
                "parsedExact": 0,
                "failed": 1,
                "unsupported": 0,
                "gateFailures": 1,
            },
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
        provenance_failures, provenance = _validate_provenance(
            summary, header, outer_ledger_path, expected_input_set_sha256
        )
        provenance["parserSha256"] = _sha256_file(
            Path(__file__).resolve().parents[1] / "terrain_tret.py"
        )
        provenance["corpusGateSha256"] = _sha256_file(Path(__file__).resolve())
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "failed",
            "failed": True,
            "inputSetSha256": expected_input_set_sha256.upper(),
            "summary": {
                "terrainFiles": 0,
                "parsedExact": 0,
                "failed": 1,
                "unsupported": 0,
                "gateFailures": 1,
            },
            "failures": [
                {"stage": "provenance", "message": f"{type(exc).__name__}: {exc}"}
            ],
        }

    if native_evidence is None:
        native_evidence = validate_terrain_native_contract(
            contract_path=native_contract_path,
            game_root=game_root,
        )
    if native_evidence.get("status") != "validated":
        return {
            "schema": SCHEMA,
            "status": "failed",
            "failed": True,
            "inputSetSha256": expected_input_set_sha256,
            "provenance": provenance,
            "nativeEvidence": native_evidence,
            "summary": {
                "terrainFiles": len(rows),
                "parsedExact": 0,
                "failed": len(rows),
                "unsupported": 0,
                "gateFailures": 1,
            },
            "failures": [
                {
                    "stage": "native-contract",
                    "message": "current Terrain native consumer contract did not validate",
                    "expected": "validated",
                    "actual": native_evidence.get("status"),
                    "details": native_evidence.get("validationFailures") or [],
                }
            ],
        }

    failures = list(provenance_failures)
    duplicate_paths = [
        path
        for path, count in collections.Counter(
            str(row.get("virtualPath", "")) for row in rows
        ).items()
        if count != 1
    ]
    for path in duplicate_paths[:FAILURE_SAMPLE_LIMIT]:
        failures.append(
            _failure(path, "ledger", "duplicate Terrain virtualPath", expected=1)
        )

    by_chunk: dict[Path, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_chunk[Path(str(row.get("physicalChunkPath", "")))].append(row)

    storage_modes: collections.Counter[str] = collections.Counter()
    sources: collections.Counter[str] = collections.Counter()
    metadata_sources: collections.Counter[str] = collections.Counter()
    overlay_states: collections.Counter[str] = collections.Counter()
    layout_counts: collections.Counter[str] = collections.Counter()
    shape_counts: collections.Counter[str] = collections.Counter()
    packed_bytes = 0
    decoded_bytes = 0
    exact_ranges = 0
    anonymous_records = 0
    anonymous_record_bytes = 0
    parsed_exact = 0
    unsupported_count = 0
    frontier_files = 0
    frontier_ranges = 0
    frontier_bytes = 0
    identity_rows: list[str] = []

    for chunk_path, chunk_rows in sorted(by_chunk.items(), key=lambda item: str(item[0])):
        try:
            stream = chunk_path.open("rb")
        except OSError as exc:
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
                row_failures: list[str] = []
                if row.get("status") != "verified":
                    row_failures.append(
                        f"status expected 'verified', actual {row.get('status')!r}"
                    )
                if row.get("boundaryStatus") != "boundary_verified":
                    row_failures.append(
                        "boundaryStatus expected 'boundary_verified', "
                        f"actual {row.get('boundaryStatus')!r}"
                    )
                if str(row.get("inputSetSha256", "")).upper() != expected_input_set_sha256.upper():
                    row_failures.append("row inputSetSha256 does not match requested input set")
                if row.get("encrypted") is not False:
                    row_failures.append(
                        f"encrypted expected false, actual {row.get('encrypted')!r}"
                    )
                if row.get("actualBytesRead") != length:
                    row_failures.append(
                        "actualBytesRead expected to equal declared length: "
                        f"expected {length}, actual {row.get('actualBytesRead')!r}"
                    )
                if offset < 0 or length < 0:
                    row_failures.append(
                        f"physical interval expected non-negative, actual offset={offset}, length={length}"
                    )
                if row_failures:
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "ledger",
                                "; ".join(row_failures),
                                offset=offset,
                            )
                        )
                    continue
                try:
                    stream.seek(offset)
                    raw = stream.read(length)
                except OSError as exc:
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "physical-read",
                                str(exc),
                                offset=offset,
                                expected=length,
                            )
                        )
                    continue
                if len(raw) != length:
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
                raw_sha256 = hashlib.sha256(raw).hexdigest().upper()
                try:
                    parsed = parse_tret_record(raw, source=virtual_path)
                except Exception as exc:
                    if "unsupported TRET anonymous layout words" in str(exc):
                        unsupported_count += 1
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
                if parsed.anonymous_tiling_status != "exact_anonymous_record_tiling":
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "parse",
                                "Terrain row did not reach exact anonymous tiling",
                                expected="exact_anonymous_record_tiling",
                                actual=parsed.anonymous_tiling_status,
                            )
                        )
                    continue
                ranges = parsed.anonymous_record_ranges
                if not ranges or ranges[0].start_offset != 20:
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "range",
                                "first anonymous range does not begin after fixed header",
                                expected=20,
                                actual=ranges[0].start_offset if ranges else None,
                            )
                        )
                    continue
                range_error = next(
                    (
                        (previous.end_offset, current.start_offset)
                        for previous, current in zip(ranges, ranges[1:])
                        if previous.end_offset != current.start_offset
                    ),
                    None,
                )
                if range_error is not None or ranges[-1].end_offset != parsed.decoded_length:
                    if len(failures) < FAILURE_SAMPLE_LIMIT:
                        failures.append(
                            _failure(
                                virtual_path,
                                "range",
                                "anonymous ranges do not contiguously consume decoded EOF",
                                expected=parsed.decoded_length,
                                actual=ranges[-1].end_offset,
                                discontinuity=range_error,
                            )
                        )
                    continue

                words = parsed.body_u16le_offsets_8_18
                shape = ",".join(str(value) for value in words)
                raw_layout_word = words[3]
                byte_count = sum(item.end_offset - item.start_offset for item in ranges)
                parsed_exact += 1
                packed_bytes += len(raw)
                decoded_bytes += parsed.decoded_length
                exact_ranges += len(ranges)
                anonymous_records += sum(item.record_count for item in ranges)
                anonymous_record_bytes += byte_count
                storage_modes[parsed.storage_mode] += 1
                sources[str(row.get("physicalChunkSource"))] += 1
                metadata_sources[str(row.get("metadataProvenance"))] += 1
                overlay_states[str(row.get("overlayState"))] += 1
                layout_counts[str(raw_layout_word)] += 1
                shape_counts[shape] += 1
                if raw_layout_word in {108, 109}:
                    frontier_files += 1
                    frontier_ranges += len(ranges)
                    frontier_bytes += byte_count
                identity_rows.append(
                    "\0".join(
                        (
                            virtual_path,
                            str(row.get("physicalChunkSource")),
                            str(row.get("chunkFile")),
                            str(offset),
                            str(length),
                            actual_md5,
                            raw_sha256,
                        )
                    )
                )

    failed_count = len(rows) - parsed_exact - unsupported_count
    failed = bool(failures or failed_count or unsupported_count or duplicate_paths)
    report = {
        "schema": SCHEMA,
        "status": "failed" if failed else "complete",
        "failed": failed,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "provenance": provenance,
        "nativeEvidence": native_evidence,
        "summary": {
            "terrainFiles": len(rows),
            "parsedExact": parsed_exact,
            "failed": failed_count,
            "unsupported": unsupported_count,
            "gateFailures": len(failures),
            "packedBytes": packed_bytes,
            "decodedBytes": decoded_bytes,
            "exactRanges": exact_ranges,
            "anonymousRecords": anonymous_records,
            "anonymousRecordBytes": anonymous_record_bytes,
            "physicalChunks": len(by_chunk),
        },
        "layer1": {
            "physicalSourceCounts": dict(sorted(sources.items())),
            "metadataProvenanceCounts": dict(sorted(metadata_sources.items())),
            "overlayStateCounts": dict(sorted(overlay_states.items())),
            "logicalIdentitySetSha256": hashlib.sha256(
                "\n".join(sorted(identity_rows)).encode("utf-8")
            ).hexdigest().upper(),
        },
        "layer2And3": {
            "storageModeCounts": dict(sorted(storage_modes.items())),
            "rawLayoutWordCounts": dict(sorted(layout_counts.items(), key=lambda item: int(item[0]))),
            "headerShapeCounts": dict(sorted(shape_counts.items())),
            "frontier108And109": {
                "files": frontier_files,
                "ranges": frontier_ranges,
                "bytes": frontier_bytes,
                "status": "exact_anonymous_record_tiling",
            },
        },
        "evidenceBoundary": {
            "structure": (
                "Every successful row is one authenticated outer-ledger logical file; "
                "its exact TRET envelope, fixed header, and contiguous anonymous ranges "
                "consume decoded offset zero through EOF."
            ),
            "semantics": (
                "The native consumer directly establishes decoded +14 as GraphicsFormat, "
                "+16 as the checked payload length, and +20 as the copy source. Range "
                "contents, D/N path-marker meaning, texture-array ownership, and runtime "
                "render selection remain inferred or unresolved."
            ),
            "levels": (native_evidence.get("evidenceBoundary") or {}),
            "ambiguityHandling": (
                "No candidate layout search is used by the maintained parser. Only "
                "selected-build header tuples backed by the validated native footprint "
                "contract are accepted; every other tuple fails closed."
            ),
        },
        "failures": failures[:FAILURE_SAMPLE_LIMIT],
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    frontier = (report.get("layer2And3") or {}).get("frontier108And109") or {}
    provenance = report.get("provenance") or {}
    native = report.get("nativeEvidence") or {}
    lines = [
        "# Terrain TRET current-corpus gate",
        "",
        f"- Status: **{report.get('status', 'failed')}**",
        f"- Input set SHA-256: `{report.get('inputSetSha256', '')}`",
        f"- Outer ledger SHA-256: `{provenance.get('outerLedgerSha256', '')}`",
        f"- Native contract: **{native.get('status', 'unavailable')}** (`{native.get('nativeMappingId', '')}`)",
        f"- Terrain files: **{summary.get('terrainFiles', 0):,}**",
        f"- Exact parses: **{summary.get('parsedExact', 0):,}**",
        f"- Failures: **{summary.get('failed', 0):,}**",
        f"- Unsupported: **{summary.get('unsupported', 0):,}**",
        f"- Gate failures: **{summary.get('gateFailures', 0):,}**",
        f"- Packed / decoded bytes: **{summary.get('packedBytes', 0):,} / {summary.get('decodedBytes', 0):,}**",
        f"- Exact anonymous ranges: **{summary.get('exactRanges', 0):,}**",
        "",
        "## Raw layout words 108 and 109",
        "",
        f"- Files: **{frontier.get('files', 0):,}**",
        f"- Exact ranges: **{frontier.get('ranges', 0):,}**",
        f"- Bytes covered: **{frontier.get('bytes', 0):,}**",
        f"- Status: `{frontier.get('status', 'unavailable')}`",
        "",
        "## Evidence boundary",
        "",
        str((report.get("evidenceBoundary") or {}).get("structure", "")),
        "",
        str((report.get("evidenceBoundary") or {}).get("semantics", "")),
        "",
        str((report.get("evidenceBoundary") or {}).get("ambiguityHandling", "")),
    ]
    levels = (report.get("evidenceBoundary") or {}).get("levels") or {}
    for level in ("exact", "direct", "structuralOnly", "inferred", "unresolved"):
        if levels.get(level):
            lines.append(f"- **{level}:** {levels[level]}")
    failures = report.get("failures") or []
    if failures:
        lines.extend(("", "## Failure samples", ""))
        for failure in failures:
            lines.append(f"- `{json.dumps(failure, ensure_ascii=False, sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, required=True)
    parser.add_argument("--outer-ledger", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--native-contract", type=Path, default=DEFAULT_NATIVE_CONTRACT)
    parser.add_argument(
        "--game-root",
        type=Path,
        help="Installed Endfield_Data root; defaults to the maintained native-input resolver.",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = sweep(
        outer_summary_path=args.outer_summary,
        outer_ledger_path=args.outer_ledger,
        expected_input_set_sha256=args.expected_input_set_sha256,
        native_contract_path=args.native_contract,
        game_root=args.game_root,
    )
    _atomic_write_text(
        args.output_json,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write_text(args.output_md, render_markdown(report))
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "inputSetSha256": report.get("inputSetSha256"),
                **(report.get("summary") or {}),
                "outputJson": args.output_json.as_posix(),
                "outputMarkdown": args.output_md.as_posix(),
            },
            ensure_ascii=False,
        )
    )
    return 1 if report.get("failed", True) else 0


if __name__ == "__main__":
    raise SystemExit(main())
