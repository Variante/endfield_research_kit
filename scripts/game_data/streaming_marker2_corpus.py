"""Full authenticated block-15 corpus gate for marker2 read windows.

This module reuses only the provenance/I/O helpers already
exercised by the marker13 corpus gate.  Marker2 directory, parser and native
evidence remain separate maintained dependencies.
"""
from __future__ import annotations

import argparse
import collections
import copy
import gzip
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from scripts.game_data import streaming as fmt
from scripts.game_data import streaming_corpus as root_corpus
from scripts.game_data import streaming_marker13_corpus as shared
from scripts.game_data.streaming_marker2_native import (
    PROFILE as NATIVE_PROFILE,
    validate_marker2_native_contract,
)
from scripts.game_data.streaming_marker2 import parse_marker2_gaps
from scripts.game_data.streaming_pairs import bind_current_pair, index_ordered_pairs


SCHEMA = "endfield.streaming-marker2-corpus.v1"
ROOT_SCHEMA = "endfield.streaming-root-subgraphs-corpus.v15"
# Candidate location is tmp/animestudio/<task>. The promoted maintained file
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.corpus_common import is_bounded_diagnostic_output as _is_bounded_diagnostic_output

# must change this to REPO_ROOT.
MODULE_REPO_ROOT = REPO_ROOT
FRAMED_STATUS = "framed"
UNSUPPORTED_STATUSES = frozenset((
    "unsupported-context", "unsupported-cluster", "unsupported-occupancy",
))
AMBIGUOUS_STATUSES = frozenset(("ambiguous-key", "ambiguous-target"))


def source_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "rootParserSha256": repo_root / "scripts/game_data/streaming.py",
        "orderedPairValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_pairs.py",
        "invertedLz4DecoderSha256": repo_root / "scripts/game_data/inverted_lz4.py",
        "commonNativeGateSha256": repo_root / "scripts/common.py",
        "rootCorpusGateSha256": repo_root / "scripts/game_data/contracts/streaming_corpus.py",
        "rootNativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_native.py",
        "rootNativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_field2_native.json",
        "marker17ParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker17.py",
        "marker17NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.py",
        "marker17NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.json",
        # The shared helper module imports these at module initialization even
        # though this gate never calls their domain functions.
        "sharedMarker13ParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker13.py",
        "sharedMarker13NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker13_native.py",
        "sharedMarker13NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker13_native.json",
        "marker2DirectorySha256": repo_root / "scripts/game_data/contracts/streaming_marker2_directory.py",
        "marker2ParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker2.py",
        "marker2NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker2_native.py",
        "marker2NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker2_native.json",
        # Imported generic snapshot/ledger/output-isolation helpers are an
        # explicit transitive source dependency, never an implicit copy.
        "sharedCorpusHelpersSha256": repo_root / "scripts/game_data/contracts/streaming_marker13_corpus.py",
        "marker2CorpusGateSha256": Path(__file__).resolve(),
    }


def snapshot_blc_manifest_set(outer: dict[str, Any], failures: list[dict[str, Any]],
                              stage: str) -> dict[str, Any]:
    """Reconcile the authenticated BLC manifest path set with the live roots."""
    expected_paths = []
    for index, row in enumerate(outer.get("sourceFingerprints") or []):
        raw = row.get("path") if isinstance(row, dict) else None
        if not isinstance(raw, str) or not raw:
            failures.append(shared.failure(
                f"sourceFingerprint[{index}]", stage, "nonempty BLC path", raw
            ))
            continue
        expected_paths.append(shared._resolved_identity(Path(raw)))
    roots = []
    actual_paths = []
    for field in ("primaryAssets", "fallbackAssets"):
        raw = outer.get(field)
        if not isinstance(raw, str) or not raw:
            failures.append(shared.failure("outer-summary", stage, "nonempty assets root", raw,
                                           field=field))
            continue
        vfs = Path(raw) / "VFS"
        roots.append(vfs.as_posix())
        try:
            actual_paths.extend(
                shared._resolved_identity(path) for path in vfs.rglob("*.blc") if path.is_file()
            )
        except OSError as exc:
            failures.append(shared.failure(
                vfs.as_posix(), stage, "readable VFS BLC directory",
                f"{type(exc).__name__}: {exc}", field=field,
            ))
    expected_set, actual_set = set(expected_paths), set(actual_paths)
    if len(expected_paths) != len(expected_set):
        failures.append(shared.failure(
            "outer-summary", stage, "unique sourceFingerprint BLC paths",
            len(expected_paths)-len(expected_set), field="duplicatePaths",
        ))
    if len(actual_paths) != len(actual_set):
        failures.append(shared.failure(
            "installed-vfs", stage, "unique resolved live BLC paths",
            len(actual_paths)-len(actual_set), field="duplicatePaths",
        ))
    missing = sorted(expected_set-actual_set)
    added = sorted(actual_set-expected_set)
    if missing or added:
        failures.append(shared.failure(
            "installed-vfs", stage,
            {"missing": [], "added": [], "expectedCount": len(expected_set)},
            {"missing": missing[:25], "added": added[:25], "actualCount": len(actual_set)},
            field="blcManifestPathSet",
        ))
    return {
        "roots": roots, "count": len(actual_set),
        "pathSetSha256": shared.sha256_bytes("\n".join(sorted(actual_set)).encode("utf-8")),
        "paths": sorted(actual_set),
    }


def validate_native(native: dict[str, Any], contract_sha: str,
                    failures: list[dict[str, Any]]) -> bool:
    shared.require(failures, "marker2-native", "native-gate", "status",
                   native.get("status"), "validated")
    shared.require(failures, "marker2-native", "native-gate", "validationFailures",
                   native.get("validationFailures") or [], [])
    shared.require(failures, "marker2-native", "native-gate", "contractSha256",
                   str(native.get("contractSha256", "")).upper(), contract_sha)
    shared.require(failures, "marker2-native", "native-gate", "profile",
                   native.get("profile"), NATIVE_PROFILE)
    return not failures


def _range(value: Any, field: str, decoded_length: int) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected mapping, actual {type(value).__name__}")
    start, end = value.get("start"), value.get("end")
    if type(start) is not int or type(end) is not int:
        raise ValueError(f"{field}: expected integer start/end, actual {start!r}:{end!r}")
    if start < 0 or end <= start or end > decoded_length:
        raise ValueError(
            f"{field}: expected 0 <= start < end <= {decoded_length}, actual {start}:{end}"
        )
    length = value.get("length")
    if type(length) is not int or length != end - start:
        raise ValueError(
            f"{field}.length: expected integer {end-start}, actual {length!r}"
        )
    return start, end


def range_coverage(decoded_length: int, certified_ranges: list[Any],
                   projections: list[dict[str, Any]]) -> dict[str, Any]:
    certified: list[tuple[int, int, str]] = []
    for index, item in enumerate(certified_ranges):
        if isinstance(item, dict):
            start, end, kind = item.get("start"), item.get("end"), item.get("kind")
        else:
            try:
                start, end, kind = item
            except (TypeError, ValueError) as exc:
                raise ValueError(f"certified range {index}: expected triple") from exc
        if type(start) is not int or type(end) is not int or not isinstance(kind, str) or not kind:
            raise ValueError(
                f"certified range {index}: expected integer bounds/nonempty kind, "
                f"actual {start!r}:{end!r}:{kind!r}"
            )
        certified.append((start, end, kind))
    if certified != sorted(set(certified)):
        raise ValueError("certified ranges: expected sorted duplicate-free triples")
    for index, (start, end, _kind) in enumerate(certified):
        if start < 0 or end <= start or end > decoded_length:
            raise ValueError(
                f"certified range {index}: expected 0 <= start < end <= {decoded_length}, "
                f"actual {start}:{end}"
            )
    for left, right in zip(certified, certified[1:]):
        if right[0] < left[1]:
            raise ValueError(f"certified ranges overlap: {left!r} / {right!r}")

    read_windows: list[tuple[int, int]] = []
    physical_gaps: list[tuple[int, int]] = []
    residuals: list[tuple[int, int]] = []
    for index, row in enumerate(projections):
        if row.get("status") != FRAMED_STATUS:
            continue
        read_windows.append(_range(
            row.get("nativeReadWindowRange"),
            f"marker2 row {index}.nativeReadWindowRange", decoded_length,
        ))
        physical_gaps.append(_range(
            row.get("physicalGapRange"),
            f"marker2 row {index}.physicalGapRange", decoded_length,
        ))
        residual = row.get("residualOpaqueRange")
        if residual is not None:
            residuals.append(_range(
                residual, f"marker2 row {index}.residualOpaqueRange", decoded_length,
            ))

    def reject_self_overlap(label: str, values: list[tuple[int, int]]) -> None:
        ordered = sorted(values)
        for left, right in zip(ordered, ordered[1:]):
            if right[0] < left[1]:
                raise ValueError(f"{label}: expected pairwise disjoint ranges, actual {left}/{right}")

    def reject_cross_overlap(label: str, left_values: list[tuple[int, int]],
                             right_values: list[tuple[int, int]]) -> None:
        left, right = sorted(left_values), sorted(right_values)
        i = j = 0
        while i < len(left) and j < len(right):
            a, b = left[i], right[j]
            if a[0] < b[1] and b[0] < a[1]:
                raise ValueError(
                    f"{label}: expected category-disjoint ranges, actual {a}/{b}"
                )
            if a[1] <= b[0]:
                i += 1
            else:
                j += 1

    certified_pairs = [(start, end) for start, end, _kind in certified]
    reject_self_overlap("marker2 physical gaps", physical_gaps)
    reject_self_overlap("marker2 native read windows", read_windows)
    # Keep categories distinct until after intersection checks. In particular,
    # exact equality must not disappear through set() deduplication.
    reject_cross_overlap("certified/marker2 physical gaps", certified_pairs, physical_gaps)
    reject_cross_overlap("certified/marker2 native read windows", certified_pairs, read_windows)

    intervals = sorted(set(
        certified_pairs + list(read_windows)
    ))
    union: list[list[int]] = []
    for start, end in intervals:
        if union and start < union[-1][1]:
            raise ValueError(
                f"owned/certified coverage overlap: {union[-1]!r} / {(start,end)!r}"
            )
        if union and start == union[-1][1]:
            union[-1][1] = end
        else:
            union.append([start, end])
    opaque = []
    cursor = 0
    for start, end in union:
        if cursor < start:
            opaque.append({"start": cursor, "end": start, "length": start-cursor})
        cursor = end
    if cursor < decoded_length:
        opaque.append({"start": cursor, "end": decoded_length,
                       "length": decoded_length-cursor})
    for residual in residuals:
        if not any(item["start"] <= residual[0] and residual[1] <= item["end"]
                   for item in opaque):
            raise ValueError(
                "marker2 residual opaque range: expected contained in final opaque complement, "
                f"actual {residual} / {opaque!r}"
            )
    return {
        "decodedCertifiedRanges": [
            {"start": start, "end": end, "kind": kind} for start, end, kind in certified
        ],
        "selectedNativeReadWindowRanges": [
            {"start": start, "end": end, "length": end-start}
            for start, end in read_windows
        ],
        "selectedPhysicalGapRanges": [
            {"start": start, "end": end, "length": end-start}
            for start, end in physical_gaps
        ],
        "selectedResidualOpaqueRanges": [
            {"start": start, "end": end, "length": end-start}
            for start, end in residuals
        ],
        "ownedOrCertifiedUnion": [
            {"start": start, "end": end, "length": end-start} for start, end in union
        ],
        "opaqueComplement": opaque,
        "certifiedReferenceBytes": sum(end-start for start, end, _kind in certified),
        "nativeReadWindowReferenceBytes": sum(end-start for start, end in read_windows),
        "uniqueNativeReadWindowBytes": sum(end-start for start, end in set(read_windows)),
        "physicalGapReferenceBytes": sum(end-start for start, end in physical_gaps),
        "residualOpaqueReferenceBytes": sum(end-start for start, end in residuals),
        "unionBytes": sum(end-start for start, end in union),
        "opaqueBytes": sum(item["length"] for item in opaque),
    }


def validate_projection(result: dict[str, Any], *, family: str,
                        expected_references: int, decoded_length: int,
                        certified_ranges: list[Any]) -> tuple[collections.Counter, dict[str, Any]]:
    if not isinstance(result, dict):
        raise ValueError(f"marker2 result: expected mapping, actual {type(result).__name__}")
    if result.get("family") != family:
        raise ValueError(
            f"marker2 family: expected {family!r}, actual {result.get('family')!r}"
        )
    expected_profile = {**copy.deepcopy(NATIVE_PROFILE), "physicalGapLengths": [4, 6]}
    if result.get("profile") != expected_profile:
        raise ValueError(
            f"marker2 profile: expected {expected_profile!r}, actual {result.get('profile')!r}"
        )
    directory = result.get("directory")
    if not isinstance(directory, dict):
        raise ValueError("marker2 directory: expected mapping")
    directory_rows = directory.get("rows")
    rows = result.get("rows")
    if not isinstance(directory_rows, list) or not isinstance(rows, list):
        raise ValueError("marker2 rows: expected directory and projection lists")
    if type(expected_references) is not int or expected_references < 0:
        raise ValueError(
            f"root marker2 count: expected nonnegative integer, actual {expected_references!r}"
        )
    directory_count = (directory.get("counts") or {}).get("marker2References")
    if type(directory_count) is not int or directory_count < 0:
        raise ValueError(
            f"marker2 directory count: expected nonnegative integer, actual {directory_count!r}"
        )
    if directory_count != expected_references or len(directory_rows) != expected_references:
        raise ValueError(
            "marker2 directory count: expected root parser "
            f"{expected_references}, actual directory {directory_count}/{len(directory_rows)}"
        )
    if len(rows) != expected_references:
        raise ValueError(
            f"marker2 projection count: expected {expected_references}, actual {len(rows)}"
        )
    missing = object()
    for index, (directory_row, projection_row) in enumerate(zip(directory_rows, rows)):
        if not isinstance(directory_row, dict) or not isinstance(projection_row, dict):
            raise ValueError(f"marker2 row {index}: expected directory/projection mappings")
        differences = {
            field: {"directory": value, "projection": projection_row.get(field, missing)}
            for field, value in directory_row.items()
            if projection_row.get(field, missing) != value
        }
        if differences:
            printable = {
                field: {
                    "directory": value["directory"],
                    "projection": "<missing>" if value["projection"] is missing else value["projection"],
                }
                for field, value in differences.items()
            }
            raise ValueError(
                f"marker2 row {index}: projection must preserve complete directory identity, "
                f"actual differences {printable!r}"
            )
    counts: collections.Counter = collections.Counter(references=len(rows))
    status_counts: collections.Counter = collections.Counter()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"marker2 row {index}: expected mapping")
        status = row.get("status")
        status_counts[status] += 1
        if status == FRAMED_STATUS:
            counts["framed"] += 1
            read_start, read_end = _range(
                row.get("nativeReadWindowRange"),
                f"marker2 row {index}.nativeReadWindowRange", decoded_length,
            )
            gap_start, gap_end = _range(
                row.get("physicalGapRange"),
                f"marker2 row {index}.physicalGapRange", decoded_length,
            )
            gap_length = gap_end-gap_start
            target_start = row.get("targetStart")
            if type(target_start) is not int:
                raise ValueError(
                    f"marker2 row {index}.targetStart: expected integer, actual {target_start!r}"
                )
            if (read_end-read_start != 4 or gap_length not in (4, 6)
                    or read_start != gap_start or read_start != target_start):
                raise ValueError(
                    f"marker2 row {index}: expected target-started read4 within physical gap4/6, "
                    f"actual target {target_start}, read {read_start}:{read_end}, gap {gap_start}:{gap_end}"
                )
            selected_identity = {
                "family": row.get("family"), "rootMarker": row.get("rootMarker"),
                "rawSelector": row.get("rowSelectorU32"), "packedKey": row.get("key"),
                "marker": row.get("marker"), "readWidth": read_end-read_start,
            }
            expected_identity = {
                "family": NATIVE_PROFILE["family"],
                "rootMarker": NATIVE_PROFILE["rootMarker"],
                "rawSelector": NATIVE_PROFILE["rawSelector"],
                "packedKey": NATIVE_PROFILE["packedKey"],
                "marker": NATIVE_PROFILE["marker"],
                "readWidth": NATIVE_PROFILE["readWidth"],
            }
            if selected_identity != expected_identity:
                raise ValueError(
                    f"marker2 row {index}: expected native selected identity {expected_identity!r}, "
                    f"actual {selected_identity!r}"
                )
            residual = row.get("residualOpaqueRange")
            if gap_length == 4:
                if residual is not None:
                    raise ValueError(
                        f"marker2 row {index}.residualOpaqueRange: expected None for gap4, actual {residual!r}"
                    )
            else:
                residual_start, residual_end = _range(
                    residual, f"marker2 row {index}.residualOpaqueRange", decoded_length,
                )
                if (residual_start, residual_end) != (read_end, gap_end):
                    raise ValueError(
                        f"marker2 row {index}.residualOpaqueRange: expected {read_end}:{gap_end}, "
                        f"actual {residual_start}:{residual_end}"
                    )
        elif status in UNSUPPORTED_STATUSES:
            counts["unsupported"] += 1
            counts[status] += 1
        elif status in AMBIGUOUS_STATUSES:
            counts["ambiguous"] += 1
            counts[status] += 1
        else:
            raise ValueError(f"marker2 row {index}: unsupported parser status {status!r}")
        if status != FRAMED_STATUS:
            leaked = {
                field: row.get(field) for field in (
                    "nativeReadWindowRange", "physicalGapRange", "residualOpaqueRange",
                    "anonymousU32", "pairRow",
                ) if row.get(field) is not None
            }
            if leaked:
                raise ValueError(
                    f"marker2 row {index}: nonframed row must not expose ranges, actual {leaked!r}"
                )
        if type(row.get("targetOwnedBytes")) is not int or row.get("targetOwnedBytes") != 0:
            raise ValueError(
                f"marker2 row {index}.targetOwnedBytes: expected 0, actual {row.get('targetOwnedBytes')!r}"
            )
    summary = result.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("marker2 summary: expected mapping")
    for field, expected in (
        ("references", counts["references"]),
        ("framed", counts["framed"]),
        ("unsupported", counts["unsupported"]),
        ("ambiguous", counts["ambiguous"]),
        ("targetOwnedBytes", 0),
    ):
        if type(summary.get(field)) is not int or summary.get(field) != expected:
            raise ValueError(
                f"marker2 summary.{field}: expected integer {expected}, actual {summary.get(field)!r}"
            )
    expected_status = (
        "ambiguous" if counts["ambiguous"] else
        "partial" if counts["unsupported"] else
        "exact-anonymous-physical-gaps"
    )
    if result.get("status") != expected_status:
        raise ValueError(
            f"marker2 status: expected {expected_status!r}, actual {result.get('status')!r}"
        )
    if result.get("statusCounts") != dict(status_counts):
        raise ValueError(
            f"marker2 statusCounts: expected {dict(status_counts)!r}, "
            f"actual {result.get('statusCounts')!r}"
        )
    if type(result.get("targetOwnedBytes")) is not int or result.get("targetOwnedBytes") != 0:
        raise ValueError(
            f"marker2 targetOwnedBytes: expected 0, actual {result.get('targetOwnedBytes')!r}"
        )
    coverage = range_coverage(decoded_length, certified_ranges, rows)
    for field, expected in (
        ("nativeReadWindowBytes", coverage["nativeReadWindowReferenceBytes"]),
        ("physicalGapBytes", coverage["physicalGapReferenceBytes"]),
        ("opaqueBytes", coverage["residualOpaqueReferenceBytes"]),
    ):
        if type(summary.get(field)) is not int or summary.get(field) != expected:
            raise ValueError(
                f"marker2 summary.{field}: expected integer {expected}, actual {summary.get(field)!r}"
            )
    if coverage["unionBytes"] + coverage["opaqueBytes"] != decoded_length:
        raise ValueError(
            f"decoded range partition: expected {decoded_length}, actual "
            f"{coverage['unionBytes']+coverage['opaqueBytes']}"
        )
    return counts, coverage


class InventorySink:
    def __init__(self, path: Path | None, *, input_set: str,
                 source_hashes: dict[str, str]):
        self.path = Path(path) if path is not None else None
        self.rows: list[dict[str, Any]] = []
        self.file_rows = 0
        self.content_hash = hashlib.sha256()
        self.temp_path: Path | None = None
        self.raw = self.gz = self.text = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            self.temp_path = Path(name)
            self.raw = os.fdopen(fd, "wb")
            self.gz = gzip.GzipFile(
                filename="", fileobj=self.raw, mode="wb", mtime=0, compresslevel=6
            )
            self.text = io.TextIOWrapper(self.gz, encoding="utf-8", newline="\n")
        self.write({
            "recordType": "inventory_header", "schema": SCHEMA,
            "inputSetSha256": input_set, "sourceHashes": source_hashes,
            "publicationStatus": "staged-until-terminal-summary-gate",
        })

    def write(self, row: dict[str, Any]) -> None:
        line = (
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        self.content_hash.update(line)
        if row.get("recordType") == "file":
            self.file_rows += 1
        if self.text is not None:
            self.text.write(line.decode("utf-8"))
        else:
            self.rows.append(row)

    def finish(self, *, keep: bool) -> dict[str, Any] | None:
        if self.text is not None:
            self.text.flush()
            self.text.detach()
            self.gz.close()
            self.raw.close()
        if not keep:
            if self.temp_path is not None:
                self.temp_path.unlink(missing_ok=True)
            self.rows.clear()
            return None
        result = {
            "path": self.path.as_posix() if self.path else None,
            "fileRowCount": self.file_rows,
            "contentSha256": self.content_hash.hexdigest().upper(),
        }
        if self.temp_path is not None and self.path is not None:
            result["gzipSha256"] = shared.sha256_file(self.temp_path)
            os.replace(self.temp_path, self.path)
        return result


def sweep(*, repo_root: Path, root_report_path: Path, outer_summary_path: Path,
          ledger_path: Path, expected_input_set_sha256: str,
          game_root: Path | None = None, max_files: int | None = None,
          inventory_path: Path | None = None,
          progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    supplied_repo_root = Path(repo_root).resolve()
    module_repo_root = MODULE_REPO_ROOT.resolve()
    if supplied_repo_root != module_repo_root:
        failures.append(shared.failure(
            "arguments", "source-root-gate", module_repo_root.as_posix(),
            supplied_repo_root.as_posix(), field="repoRoot",
        ))
    # Never hash another checkout after importing code from this one.
    repo_root = module_repo_root
    expected_input = expected_input_set_sha256.upper()
    if len(expected_input) != 64 or any(c not in "0123456789ABCDEF" for c in expected_input):
        failures.append(shared.failure(
            "arguments", "input-gate", "64 uppercase hexadecimal characters", expected_input
        ))
    if max_files is not None and (type(max_files) is not int or max_files <= 0):
        failures.append(shared.failure(
            "arguments", "selection", "positive integer max_files or None", max_files
        ))
    if (max_files is not None and inventory_path is not None
            and not _is_bounded_diagnostic_output(Path(inventory_path), module_repo_root)):
        failures.append(shared.failure(
            str(inventory_path), "selection",
            "partial inventory path under current repo tmp/ or scratch/",
            Path(inventory_path).resolve().as_posix(), field="inventoryPath",
        ))
    paths = source_paths(Path(repo_root))
    source_start = shared.snapshot_sources(paths, failures, "source-start")
    input_paths = {
        "rootReportSha256": root_report_path,
        "outerSummarySha256": outer_summary_path,
        "outerLedgerSha256": ledger_path,
    }
    input_start = shared.snapshot_sources(input_paths, failures, "input-start")
    report = shared.read_json(root_report_path, failures, "root-report-read")
    outer = shared.read_json(outer_summary_path, failures, "outer-summary-read")
    fingerprints_start = shared.snapshot_fingerprints(outer, failures, "fingerprints-start")
    blc_manifest_start = snapshot_blc_manifest_set(outer, failures, "blc-manifest-start")
    header, ledger_rows = shared.read_ledger(ledger_path, failures)
    shared.validate_root_report(
        report, outer, header, ledger_rows, expected_input,
        input_start.get("outerLedgerSha256", ""), source_start, failures,
    )
    if game_root is None and outer.get("primaryAssets"):
        game_root = Path(str(outer["primaryAssets"])).parent
    if game_root is None:
        failures.append(shared.failure(
            "arguments", "native-gate",
            "explicit game_root or authenticated outer primaryAssets", None,
        ))
        native_inputs_start = {}
        native = {"status": "validation_failed", "profile": None, "validationFailures": []}
    else:
        game_root = Path(game_root)
        native_inputs_start = shared.snapshot_native_inputs(
            game_root, failures, "native-inputs-start"
        )
        native = validate_marker2_native_contract(game_root=game_root)
    native_ok = validate_native(
        native, source_start.get("marker2NativeContractSha256", ""), failures
    )

    pair_index = {}
    if not failures:
        try:
            pair_index = index_ordered_pairs(report)
            shared.require(
                failures, "root-report", "pair-index", "dataFileCount", len(pair_index),
                sum(root_corpus._family(row["virtualPath"]) != "info" for row in ledger_rows),
            )
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(shared.failure(
                "root-report", "pair-index", "complete source-bound ordered pairs", str(exc)
            ))

    paths_seen = collections.Counter(str(row.get("virtualPath", "")) for row in ledger_rows)
    for path, count in paths_seen.items():
        if not path or count != 1:
            failures.append(shared.failure(
                path or "outer-ledger", "ledger-identity", "unique nonempty virtualPath", count
            ))
    selected = ledger_rows[:max_files] if max_files is not None else ledger_rows
    partial = max_files is not None
    try:
        shared.validate_output_isolation(
            outputs={"outputInventory": inventory_path},
            protected=shared.protected_input_paths(
                repo_root=repo_root, root_report_path=root_report_path,
                outer_summary_path=outer_summary_path, ledger_path=ledger_path,
                outer=outer, game_root=game_root, source_paths=paths,
                ledger_rows=ledger_rows,
            ),
        )
    except ValueError as exc:
        failures.append(shared.failure(
            str(inventory_path), "output-path-isolation", "output disjoint from inputs", str(exc)
        ))
    sink = InventorySink(
        None if failures else inventory_path,
        input_set=expected_input, source_hashes=source_start,
    )
    counters = collections.Counter(filesSelected=len(selected), filesTotal=len(ledger_rows))
    identity_rows: list[str] = []
    if not failures:
        chunks: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for row in selected:
            chunks[str(row.get("physicalChunkPath", ""))].append(row)
        for chunk_name, chunk_rows in chunks.items():
            chunk_path = Path(chunk_name)
            try:
                stream = chunk_path.open("rb")
                chunk_size = chunk_path.stat().st_size
            except OSError as exc:
                counters["filesFailed"] += len(chunk_rows)
                for row in chunk_rows:
                    failures.append(shared.failure(
                        str(row.get("virtualPath")), "chunk-open", "readable physical chunk",
                        f"{type(exc).__name__}: {exc}",
                    ))
                continue
            with stream:
                for row in chunk_rows:
                    virtual_path = str(row.get("virtualPath", ""))
                    try:
                        offset, length = row.get("offset"), row.get("length")
                        checks = {
                            "status": "verified", "boundaryStatus": "boundary_verified",
                            "inputSetSha256": expected_input, "encrypted": False,
                            "actualBytesRead": length,
                        }
                        for field, expected in checks.items():
                            actual = (
                                str(row.get(field, "")).upper()
                                if field == "inputSetSha256" else row.get(field)
                            )
                            if actual != expected:
                                raise ValueError(
                                    f"ledger {field}: expected {expected!r}, actual {actual!r}"
                                )
                        if type(offset) is not int or offset < 0 or type(length) is not int or length < 0:
                            raise ValueError(
                                "physical range: expected nonnegative integer offset/length, "
                                f"actual {offset!r}/{length!r}"
                            )
                        if offset > chunk_size or length > chunk_size-offset:
                            raise ValueError(
                                f"physical range: expected 0 <= {offset} <= {offset}+{length} <= {chunk_size}"
                            )
                        family = root_corpus._family(virtual_path)
                        stream.seek(offset)
                        packed = stream.read(length)
                        if len(packed) != length:
                            raise ValueError(
                                f"packed read length: expected {length}, actual {len(packed)}"
                            )
                        packed_md5 = hashlib.md5(
                            packed, usedforsecurity=False
                        ).hexdigest().upper()
                        if packed_md5 != str(row.get("recomputedFileDataMd5", "")).upper():
                            raise ValueError(
                                f"packed MD5: expected {row.get('recomputedFileDataMd5')}, actual {packed_md5}"
                            )
                        packed_sha = shared.sha256_bytes(packed)
                        parsed = fmt.parse_streaming_file(
                            family, packed,
                            allow_raw=virtual_path in root_corpus.RAW_DATA_EXCEPTIONS,
                            native_layout_validated=native_ok,
                            include_certified_ranges=True,
                        )
                        clear = (
                            fmt._decode_compressed(packed)
                            if parsed.get("encoding") == "inverted_lz4" else packed
                        )
                        if len(clear) != parsed.get("decodedBytes"):
                            raise ValueError(
                                f"decoded length: expected parser {parsed.get('decodedBytes')}, actual {len(clear)}"
                            )
                        decoded_sha = shared.sha256_bytes(clear)
                        pair_context = None
                        if family in {"init", "streaming"}:
                            pair_context = bind_current_pair(
                                pair_index=pair_index,
                                identity={**row, "packedSha256": packed_sha},
                                decoded=clear, parsed=parsed,
                                root_report_sha256=input_start["rootReportSha256"],
                            )
                            marker_counts = (
                                (parsed.get("anonymousParallelSubgraph") or {})
                                .get("nestedElementMarkerCounts") or {}
                            )
                            expected_references = marker_counts.get(2, 0)
                            projection = parse_marker2_gaps(
                                clear, source=virtual_path, family=family, parsed=parsed,
                                certified_ranges=parsed.get("decodedCertifiedRanges"),
                                native_layout_validated=native_ok,
                                pair_context=pair_context,
                            )
                            counts, coverage = validate_projection(
                                projection, family=family,
                                expected_references=expected_references,
                                decoded_length=len(clear),
                                certified_ranges=parsed.get("decodedCertifiedRanges") or [],
                            )
                        elif family == "info":
                            info_status = (parsed.get("anonymousInner") or {}).get("status")
                            if info_status != "exact_anonymous":
                                raise ValueError(
                                    "Info whole-file status: expected exact_anonymous, "
                                    f"actual {info_status!r}"
                                )
                            expected_references = 0
                            projection = {
                                "status": "unsupported-context-only", "directory": {
                                    "status": "not-applicable-info", "rows": [],
                                    "counts": {"marker2References": 0},
                                },
                                "rows": [], "summary": {
                                    "references": 0, "framed": 0, "unsupported": 0,
                                    "ambiguous": 0, "physicalGapBytes": 0,
                                    "nativeReadWindowBytes": 0, "opaqueBytes": 0,
                                    "targetOwnedBytes": 0,
                                }, "targetOwnedBytes": 0,
                            }
                            counts = collections.Counter()
                            coverage = range_coverage(
                                len(clear), [(0, len(clear), "info-exact-anonymous-graph")], []
                            )
                        else:
                            raise ValueError(f"family: expected info/init/streaming, actual {family!r}")

                        counters["filesSucceeded"] += 1
                        counters[f"family:{family}"] += 1
                        counters["packedBytes"] += len(packed)
                        counters["decodedBytes"] += len(clear)
                        counters["marker2References"] += expected_references
                        counters["filesWithFramedReferences"] += int(counts["framed"] > 0)
                        for projected_row in projection["rows"]:
                            if projected_row["status"] == FRAMED_STATUS:
                                gap_length = projected_row["physicalGapRange"]["length"]
                                counters[f"physicalGapLength:{gap_length}"] += 1
                        for name in (
                            "framed", "unsupported", "ambiguous", "unsupported-context",
                            "unsupported-cluster", "unsupported-occupancy",
                            "ambiguous-key", "ambiguous-target",
                        ):
                            counters[name] += counts[name]
                        counters["physicalGapReferenceBytes"] += coverage["physicalGapReferenceBytes"]
                        counters["nativeReadWindowReferenceBytes"] += coverage["nativeReadWindowReferenceBytes"]
                        counters["uniqueNativeReadWindowBytes"] += coverage["uniqueNativeReadWindowBytes"]
                        counters["residualOpaqueReferenceBytes"] += coverage["residualOpaqueReferenceBytes"]
                        counters["opaqueBytes"] += coverage["opaqueBytes"]
                        identity_rows.append("\0".join((
                            virtual_path, str(row.get("physicalChunkSource")),
                            str(row.get("chunkFile")), str(offset), str(length),
                            packed_md5, packed_sha,
                        )))
                        sink.write({
                            "recordType": "file", "virtualPath": virtual_path,
                            "family": family, "physicalChunkPath": chunk_path.as_posix(),
                            "physicalChunkSource": row.get("physicalChunkSource"),
                            "metadataProvenance": row.get("metadataProvenance"),
                            "overlayState": row.get("overlayState"),
                            "offset": offset, "length": length,
                            "packedMd5": packed_md5, "packedSha256": packed_sha,
                            "decodedLength": len(clear), "decodedSha256": decoded_sha,
                            "wholeLogicalFileStatus": (
                                "exact-anonymous-eof" if family == "info"
                                else "partial-with-explicit-opaque-complement"
                            ),
                            "rangeCoverage": coverage, "marker2": projection,
                            "orderedPairContext": pair_context,
                        })
                    except (OSError, ValueError, TypeError, KeyError, struct.error) as exc:
                        counters["filesFailed"] += 1
                        failures.append(shared.failure(
                            virtual_path, "file-validation",
                            "authenticated parse and marker2 projection",
                            f"{type(exc).__name__}: {exc}", offset=row.get("offset"),
                        ))
                        if progress is not None and counters["filesFailed"] == 1:
                            progress({"firstFailure": failures[-1]})
                    done = counters["filesSucceeded"] + counters["filesFailed"]
                    if progress is not None and (done % 5000 == 0 or done == len(selected)):
                        progress({"parsed": done, "total": len(selected),
                                  "failed": counters["filesFailed"]})

    if not partial and not failures:
        identity_sha = shared.sha256_bytes("\n".join(sorted(identity_rows)).encode("utf-8"))
        shared.require(
            failures, "root-v15", "terminal-reconciliation", "logicalIdentitySetSha256",
            identity_sha, ((report.get("layer1") or {}).get("logicalIdentitySetSha256")),
        )
        expected_references = (
            ((report.get("layer3") or {}).get("nestedElementFraming") or {})
            .get("nestedElementMarkerCounts", {}).get("2", 0)
        )
        shared.require(
            failures, "root-v15", "terminal-reconciliation", "marker2ReferenceCount",
            counters["marker2References"], expected_references,
        )
    shared.require(
        failures, "terminal", "terminal-reconciliation", "files",
        counters["filesSucceeded"] + counters["filesFailed"], len(selected),
    )
    shared.require(
        failures, "terminal", "terminal-reconciliation", "referencePartition",
        counters["framed"] + counters["unsupported"] + counters["ambiguous"],
        counters["marker2References"],
    )
    shared.require(
        failures, "terminal", "terminal-reconciliation", "targetOwnedBytes", 0, 0
    )

    source_end = shared.snapshot_sources(paths, failures, "source-end")
    input_end = shared.snapshot_sources(input_paths, failures, "input-end")
    fingerprints_end = shared.snapshot_fingerprints(outer, failures, "fingerprints-end")
    blc_manifest_end = snapshot_blc_manifest_set(outer, failures, "blc-manifest-end")
    native_inputs_end = shared.snapshot_native_inputs(game_root, failures, "native-inputs-end")
    shared.require(failures, "source-set", "source-end", "sourceHashes", source_end, source_start)
    shared.require(failures, "input-set", "input-end", "inputHashes", input_end, input_start)
    shared.require(
        failures, "fingerprints", "input-end", "outerFingerprints",
        fingerprints_end, fingerprints_start,
    )
    shared.require(
        failures, "installed-vfs", "input-end", "blcManifestPathSet",
        blc_manifest_end, blc_manifest_start,
    )
    shared.require(
        failures, "native-inputs", "input-end", "nativeInputHashes",
        native_inputs_end, native_inputs_start,
    )

    success = not failures
    status = "partial" if success and partial else "complete" if success else "failed"
    if success:
        sink.write({
            "recordType": "inventory_terminal", "schema": SCHEMA,
            "status": status, "publicationEligible": not partial,
            "inputSetSha256": expected_input, "sourceHashes": source_end,
            "counts": {
                "filesSelected": len(selected),
                "filesSucceeded": counters["filesSucceeded"],
                "filesFailed": counters["filesFailed"],
                "marker2References": counters["marker2References"],
                "framedReferences": counters["framed"],
                "unsupportedReferences": counters["unsupported"],
                "ambiguousReferences": counters["ambiguous"],
                "nativeReadWindowReferenceBytes": counters["nativeReadWindowReferenceBytes"],
                "uniqueNativeReadWindowBytes": counters["uniqueNativeReadWindowBytes"],
            },
        })
    inventory = sink.finish(keep=success)
    return {
        "schema": SCHEMA, "status": status, "failed": not success,
        "publicationEligible": success and not partial,
        "inputSetSha256": expected_input,
        "provenance": {
            "start": {"sourceHashes": source_start, "inputHashes": input_start,
                      "outerFingerprints": fingerprints_start,
                      "blcManifestPathSet": blc_manifest_start,
                      "nativeInputs": native_inputs_start},
            "end": {"sourceHashes": source_end, "inputHashes": input_end,
                    "outerFingerprints": fingerprints_end,
                    "blcManifestPathSet": blc_manifest_end,
                    "nativeInputs": native_inputs_end},
            "outerFingerprintCount": len(fingerprints_start),
            "outerFingerprintSetSha256": shared.sha256_bytes(json.dumps(
                fingerprints_start, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")),
            "nativeValidation": native,
        },
        "selection": {
            "mode": "partial" if partial else "full",
            "profile": dict(NATIVE_PROFILE),
            "unknownContextDisposition": (
                "unsupported opaque; authenticated and directory-counted; targetOwnedBytes=0"
            ),
        },
        "summary": {
            "filesTotal": len(ledger_rows), "filesSelected": len(selected),
            "filesSucceeded": counters["filesSucceeded"],
            "filesFailed": counters["filesFailed"],
            "packedBytes": counters["packedBytes"],
            "decodedBytes": counters["decodedBytes"],
            "marker2References": counters["marker2References"],
            "framedReferences": counters["framed"],
            "filesWithFramedReferences": counters["filesWithFramedReferences"],
            "selectedPhysicalGapLengthCounts": {
                str(length): counters[f"physicalGapLength:{length}"] for length in (4, 6)
            },
            "unsupportedReferences": counters["unsupported"],
            "ambiguousReferences": counters["ambiguous"],
            "unsupportedByReason": {
                name: counters[name] for name in sorted(UNSUPPORTED_STATUSES)
            },
            "ambiguousByReason": {
                name: counters[name] for name in sorted(AMBIGUOUS_STATUSES)
            },
            "physicalGapReferenceBytes": counters["physicalGapReferenceBytes"],
            "nativeReadWindowReferenceBytes": counters["nativeReadWindowReferenceBytes"],
            "uniqueNativeReadWindowBytes": counters["uniqueNativeReadWindowBytes"],
            "residualOpaqueReferenceBytes": counters["residualOpaqueReferenceBytes"],
            "opaqueBytes": counters["opaqueBytes"],
            "targetOwnedBytes": 0,
            "failed": len(failures), "unsupported": counters["unsupported"],
        },
        "layer3": {
            "status": "exact-anonymous-marker2-read-window-directory" if success else "unvalidated",
            "evidenceLevel": "structural-only", "inventory": inventory,
            "targetOwnedBytes": 0, "serializedSizeStatus": "unknown",
            "nativeFinalCursorStatus": "unknown", "semanticsStatus": "unresolved",
        },
        "evidenceBoundary": {
            "exact": (
                "Every marker2 reference is re-derived from authenticated root bytes and classified; "
                "only exclusive native-profile gaps of the maintained finite shapes are framed."
            ),
            "structuralOnly": (
                "Native supplies only a conditional four-byte read window. Physical gap and "
                "read-window bytes are reported separately; no target bytes are owned."
            ),
            "unsupported": (
                "Other contexts, multi-target clusters and incomplete unknown-marker occupancy "
                "remain explicit unsupported rows, not silent successes."
            ),
            "unresolved": (
                "Serialized extent/sizeof, native EOF/final cursor, runtime receipt, field names and semantics."
            ),
        },
        "failures": failures, "failureCount": len(failures),
        **({"_inventoryRows": sink.rows if success else []} if inventory_path is None else {}),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join([
        "# Streaming marker2 corpus gate", "",
        f"- Status: `{report['status']}`; publication eligible: `{str(report['publicationEligible']).lower()}`.",
        f"- Input set: `{report['inputSetSha256']}`.",
        f"- Files: {summary['filesSucceeded']:,} succeeded / {summary['filesFailed']:,} failed / {summary['filesSelected']:,} selected.",
        f"- Marker2: {summary['framedReferences']:,} framed; {summary['unsupportedReferences']:,} unsupported; {summary['ambiguousReferences']:,} ambiguous; {summary['marker2References']:,} total.",
        f"- Physical-gap reference bytes: {summary['physicalGapReferenceBytes']:,}; native read-window reference bytes: {summary['nativeReadWindowReferenceBytes']:,}; unique read-window bytes: {summary['uniqueNativeReadWindowBytes']:,}; target-owned bytes: 0.", "",
        "Certified neighbours bound the selected physical gaps; only the conditional four-byte native read window is projected. Serialized record extent, native EOF, runtime receipt and semantics remain unresolved.", "",
    ])



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=MODULE_REPO_ROOT)
    parser.add_argument("--root-report", type=Path)
    parser.add_argument("--outer-summary", type=Path)
    parser.add_argument("--outer-ledger", type=Path)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--input-set-sha256", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--output-inventory", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    if root != MODULE_REPO_ROOT.resolve():
        parser.error(
            "--repo-root must identify the checkout containing the executing gate: "
            f"expected {MODULE_REPO_ROOT.resolve()!s}, actual {root!s}"
        )
    if args.max_files is not None:
        outputs = (args.output_json, args.output_md, args.output_inventory)
        if any(value is None for value in outputs):
            parser.error("--max-files requires explicit JSON, Markdown and inventory outputs")
        if any(not _is_bounded_diagnostic_output(Path(value), root) for value in outputs):
            parser.error("--max-files outputs must stay under repo tmp/ or scratch/")
    output_json = args.output_json or root / "reports/animestudio/streaming_marker2_latest.json"
    output_md = args.output_md or root / "reports/animestudio/streaming_marker2_latest.md"
    output_inventory = args.output_inventory or root / "reports/animestudio/streaming_marker2_inventory_latest.jsonl.gz"
    root_report = args.root_report or root / "reports/animestudio/streaming_root_subgraphs_latest.json"
    outer_summary = args.outer_summary or root / "reports/animestudio/vfs_understanding_latest.json"
    outer_ledger = args.outer_ledger or root / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
    preflight_failures: list[dict[str, Any]] = []
    outer = shared.read_json(outer_summary, preflight_failures, "output-preflight")
    _header, ledger_rows = shared.read_ledger(outer_ledger, preflight_failures)
    if preflight_failures:
        parser.error(json.dumps(preflight_failures[0], ensure_ascii=False))
    try:
        shared.validate_output_isolation(
            outputs={"outputJson": output_json, "outputMarkdown": output_md,
                     "outputInventory": output_inventory},
            protected=shared.protected_input_paths(
                repo_root=root, root_report_path=root_report,
                outer_summary_path=outer_summary, ledger_path=outer_ledger,
                outer=outer, game_root=args.game_root,
                source_paths=source_paths(root), ledger_rows=ledger_rows,
            ),
        )
    except ValueError as exc:
        parser.error(str(exc))
    result = sweep(
        repo_root=root, root_report_path=root_report,
        outer_summary_path=outer_summary, ledger_path=outer_ledger,
        expected_input_set_sha256=args.input_set_sha256,
        game_root=args.game_root, max_files=args.max_files,
        inventory_path=output_inventory,
        progress=lambda row: print(json.dumps(row), flush=True),
    )
    serializable = {key: value for key, value in result.items() if not key.startswith("_")}
    root_corpus._atomic_write_text(output_md, render_markdown(serializable))
    root_corpus._atomic_write_text(
        output_json, json.dumps(serializable, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps({
        "status": result["status"],
        "publicationEligible": result["publicationEligible"],
        **result["summary"],
    }, indent=2))
    if result["failed"] and result["failures"]:
        print("firstFailure=" + json.dumps(result["failures"][0], ensure_ascii=False), file=sys.stderr)
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
