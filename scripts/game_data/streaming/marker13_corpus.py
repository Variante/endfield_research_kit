"""Full authenticated block-15 corpus gate for marker13 gap/read projections."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from scripts.game_data.streaming import framing as fmt
from scripts.game_data.streaming import corpus as root_corpus
from scripts.game_data.streaming.marker13 import PROFILE as GAP_PROFILE
from scripts.game_data.streaming.marker13 import parse_marker13_gaps
from scripts.game_data.streaming.marker13_native import (
    EXPECTED_ABSENT_WITNESS, validate_marker13_native_contract,
)
from scripts.game_data.streaming.pairs import index_ordered_pairs, bind_current_pair
from scripts.common import sha256_file_upper as sha256_file
from scripts.game_data.corpus_common import is_bounded_diagnostic_output as _is_bounded_diagnostic_output


SCHEMA = "endfield.streaming-marker13-corpus.v2"
ROOT_SCHEMA = "endfield.streaming-root-subgraphs-corpus.v15"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()



def failure(source: str, stage: str, expected: Any, actual: Any,
            *, offset: int | None = None, field: str | None = None) -> dict[str, Any]:
    row = {"source": source, "stage": stage, "expected": expected, "actual": actual}
    if offset is not None:
        row["offset"] = offset
    if field is not None:
        row["field"] = field
    return row


def require(failures: list[dict[str, Any]], source: str, stage: str,
            field: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        failures.append(failure(source, stage, expected, actual, field=field))


def source_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "rootParserSha256": repo_root / "scripts/game_data/streaming/framing.py",
        "orderedPairValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_pairs.py",
        "invertedLz4DecoderSha256": repo_root / "scripts/game_data/inverted_lz4.py",
        "commonNativeGateSha256": repo_root / "scripts/common.py",
        "rootCorpusGateSha256": repo_root / "scripts/game_data/contracts/streaming_corpus.py",
        "rootNativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_native.py",
        "rootNativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_field2_native.json",
        "marker17ParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker17.py",
        "marker17NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.py",
        "marker17NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.json",
        "marker13GapParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker13.py",
        "marker13NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker13_native.py",
        "marker13NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker13_native.json",
        "marker13CorpusGateSha256": Path(__file__).resolve(),
    }


def snapshot_sources(paths: dict[str, Path], failures: list[dict[str, Any]], stage: str) -> dict[str, str]:
    result = {}
    for name, path in paths.items():
        try:
            result[name] = sha256_file(path)
        except OSError as exc:
            failures.append(failure(path.as_posix(), stage, "readable source",
                                    f"{type(exc).__name__}: {exc}", field=name))
    return result


def fingerprint_rows(outer: dict[str, Any]) -> list[dict[str, Any]]:
    return list(outer.get("sourceFingerprints") or []) + list(outer.get("buildFingerprints") or [])


def snapshot_fingerprints(outer: dict[str, Any], failures: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = fingerprint_rows(outer)
    if not rows:
        failures.append(failure("outer-summary", stage, "nonempty fingerprint inventory", 0))
        return []
    result = []
    seen = set()
    for index, row in enumerate(rows):
        source = f"outer-fingerprint[{index}]"
        raw_path = row.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(failure(source, stage, "nonempty path", raw_path))
            continue
        path = Path(raw_path)
        canonical = str(path.resolve()).casefold()
        if canonical in seen:
            failures.append(failure(source, stage, "unique resolved path", canonical))
            continue
        seen.add(canonical)
        try:
            length, digest = path.stat().st_size, sha256_file(path)
        except OSError as exc:
            failures.append(failure(path.as_posix(), stage, "readable fingerprint input",
                                    f"{type(exc).__name__}: {exc}"))
            continue
        require(failures, path.as_posix(), stage, "length", length, row.get("length"))
        require(failures, path.as_posix(), stage, "sha256", digest, str(row.get("sha256", "")).upper())
        result.append({"path": path.as_posix(), "length": length, "sha256": digest})
    return result


def snapshot_native_inputs(game_root: Path | None, failures: list[dict[str, Any]],
                           stage: str) -> dict[str, dict[str, Any]]:
    if game_root is None:
        return {}
    paths = {
        "GameAssembly.dll": Path(game_root).parent / "GameAssembly.dll",
        "global-metadata.dat": Path(game_root) / "il2cpp_data/Metadata/global-metadata.dat",
        "UnityPlayer.dll": Path(game_root).parent / "UnityPlayer.dll",
    }
    result = {}
    for name, path in paths.items():
        try:
            result[name] = {
                "path": path.as_posix(), "length": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        except OSError as exc:
            failures.append(failure(path.as_posix(), stage, "readable native input",
                                    f"{type(exc).__name__}: {exc}", field=name))
    return result


def range_coverage(decoded_length: int, certified_ranges: list[Any],
                   gap_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return exact union/complement accounting without assigning opaque bytes."""
    certified = []
    for item in certified_ranges:
        if isinstance(item, dict):
            start, end, kind = item.get("start"), item.get("end"), item.get("kind")
        else:
            start, end, kind = item
        if type(start) is not int or type(end) is not int:
            raise ValueError(
                f"certified range {len(certified)}: expected integer start/end, actual {start!r}:{end!r}"
            )
        if not isinstance(kind, str) or not kind:
            raise ValueError(
                f"certified range {len(certified)}: expected nonempty kind, actual {kind!r}"
            )
        certified.append({"start": start, "end": end, "kind": kind})
    supplied_triples = [
        (item["start"], item["end"], item["kind"]) for item in certified
    ]
    certified_triples = sorted(set(supplied_triples))
    if supplied_triples != certified_triples:
        raise ValueError(
            "certified range coverage: expected sorted duplicate-free triples, "
            f"actual {supplied_triples[:3]!r}"
        )
    for previous, current in zip(certified_triples, certified_triples[1:]):
        if current[0] < previous[1]:
            raise ValueError(
                f"certified range coverage: expected no non-identical overlap, actual {previous} and {current}"
            )
    certified = [
        {"start": start, "end": end, "kind": kind}
        for start, end, kind in certified_triples
    ]
    gaps = []
    for row in gap_rows:
        if row.get("status") == "exact-anonymous-physical-gap":
            physical = row["nativeReadWindowRange"]
            gaps.append({"start": physical["start"], "end": physical["end"],
                         "kind": "marker13-native-read-window16"})
    unique_gaps = sorted({(item["start"], item["end"]) for item in gaps})
    intervals = sorted(set(
        [(item["start"], item["end"]) for item in certified] + list(unique_gaps)
    ))
    union: list[list[int]] = []
    for start, end in intervals:
        if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > decoded_length:
            raise ValueError(
                f"range coverage: expected 0 <= start < end <= {decoded_length}, actual {start!r}:{end!r}"
            )
        if union and start < union[-1][1]:
            raise ValueError(
                f"range coverage: expected nonoverlap, actual {union[-1][0]}:{union[-1][1]} and {start}:{end}"
            )
        if union and start == union[-1][1]:
            union[-1][1] = end
        else:
            union.append([start, end])
    opaque = []
    cursor = 0
    for start, end in union:
        if cursor < start:
            opaque.append({"start": cursor, "end": start, "length": start - cursor})
        cursor = end
    if cursor < decoded_length:
        opaque.append({"start": cursor, "end": decoded_length,
                       "length": decoded_length - cursor})
    return {
        "decodedCertifiedRanges": certified,
        "selectedReadWindowRanges": gaps,
        "ownedOrCertifiedUnion": [
            {"start": start, "end": end, "length": end - start} for start, end in union
        ],
        "opaqueComplement": opaque,
        "certifiedReferenceBytes": sum(item["end"] - item["start"] for item in certified),
        "readWindowReferenceBytes": sum(item["end"] - item["start"] for item in gaps),
        "uniqueReadWindowBytes": sum(end - start for start, end in unique_gaps),
        "unionBytes": sum(end - start for start, end in union),
        "opaqueBytes": sum(item["length"] for item in opaque),
    }


def read_json(path: Path, failures: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("top-level JSON is not an object")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(failure(path.as_posix(), stage, "readable JSON object",
                                f"{type(exc).__name__}: {exc}"))
        return {}


def read_ledger(path: Path, failures: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    headers, rows = [], []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    failures.append(failure(path.as_posix(), "ledger-read", "valid JSON line",
                                            exc.msg, offset=line_number))
                    continue
                if not isinstance(row, dict):
                    failures.append(failure(path.as_posix(), "ledger-read", "JSON object", type(row).__name__, offset=line_number))
                elif row.get("recordType") == "audit_header":
                    headers.append(row)
                elif row.get("recordType") == "file" and row.get("blockTypeValue") == 15:
                    rows.append(row)
    except (OSError, UnicodeError, EOFError) as exc:
        failures.append(failure(path.as_posix(), "ledger-read", "readable gzip JSONL",
                                f"{type(exc).__name__}: {exc}"))
    require(failures, path.as_posix(), "ledger-read", "auditHeaderCount", len(headers), 1)
    if not rows:
        failures.append(failure(path.as_posix(), "ledger-read", "at least one block-15 row", 0))
    return (headers[0] if len(headers) == 1 else None), rows


def validate_root_report(report: dict[str, Any], outer: dict[str, Any], header: dict[str, Any] | None,
                         rows: list[dict[str, Any]], expected_input: str, ledger_sha: str,
                         sources: dict[str, str], failures: list[dict[str, Any]]) -> None:
    require(failures, "root-v15", "root-gate", "schema", report.get("schema"), ROOT_SCHEMA)
    require(failures, "root-v15", "root-gate", "status", report.get("status"), "complete")
    require(failures, "root-v15", "root-gate", "failed", report.get("failed"), False)
    require(failures, "root-v15", "root-gate", "inputSetSha256",
            str(report.get("inputSetSha256", "")).upper(), expected_input)
    summary = report.get("summary") or {}
    for field, expected in (("streamingFiles", len(rows)), ("parsed", len(rows)),
                            ("failed", 0), ("unsupported", 0), ("gateFailures", 0)):
        require(failures, "root-v15", "root-gate", f"summary.{field}", summary.get(field), expected)
    require(failures, "root-v15", "root-gate", "failures", report.get("failures"), [])
    provenance = report.get("provenance") or {}
    require(failures, "root-v15", "root-gate", "provenance.inputSetSha256",
            str(provenance.get("inputSetSha256", "")).upper(), expected_input)
    for field, source_name in {
        "parserSha256": "rootParserSha256", "corpusGateSha256": "rootCorpusGateSha256",
        "nativeValidatorSha256": "rootNativeValidatorSha256",
        "nativeContractSha256": "rootNativeContractSha256",
    }.items():
        require(failures, "root-v15", "root-source-gate", field,
                str(provenance.get(field, "")).upper(), sources.get(source_name))
    require(failures, "outer-summary", "outer-gate", "inputSetSha256",
            str(outer.get("inputSetSha256", "")).upper(), expected_input)
    require(failures, "outer-summary", "outer-gate", "summary.fullAuditPassed",
            (outer.get("summary") or {}).get("fullAuditPassed"), True)
    require(failures, "outer-summary", "outer-gate", "publication.ledgerSha256",
            str((outer.get("publication") or {}).get("ledgerSha256", "")).upper(), ledger_sha)
    require(failures, "root-v15", "outer-join", "outerLedgerSha256",
            str(provenance.get("outerLedgerSha256", "")).upper(), ledger_sha)
    for field in ("primaryAssets", "fallbackAssets"):
        require(failures, "root-v15", "outer-join", field, provenance.get(field), outer.get(field))
    if header is not None:
        require(failures, "outer-ledger", "outer-gate", "schemaVersion", header.get("schemaVersion"), 1)
        require(failures, "outer-ledger", "outer-gate", "inputSetSha256",
                str(header.get("inputSetSha256", "")).upper(), expected_input)
        for field in ("primaryAssets", "fallbackAssets"):
            require(failures, "outer-ledger", "outer-gate", field, header.get(field), outer.get(field))


def validate_native(native: dict[str, Any], contract_sha: str,
                    failures: list[dict[str, Any]]) -> bool:
    require(failures, "marker13-native", "native-gate", "status", native.get("status"), "validated")
    require(failures, "marker13-native", "native-gate", "validationFailures",
            native.get("validationFailures") or [], [])
    require(failures, "marker13-native", "native-gate", "contractSha256",
            str(native.get("contractSha256", "")).upper(), contract_sha)
    profile = native.get("profile") or {}
    expected = {
        "family": "streaming", "rootMarker": 2, "rawSelector": 9,
        "key": [255, 0, 0], "packedKey": 0xFF000000, "marker": 13,
        "readWidth": 16, "dwordOffsets": [0, 4, 8, 12],
        "allocatedSizeStatus": "not-proven-by-native",
        "markerBinding": "external authenticated same-element corpus join; native reader does not inspect marker13",
        "extentStatus": "read-window-only; record extent and EOF unresolved",
        "evidenceLevel": "structural-only",
    }
    require(failures, "marker13-native", "native-gate", "profile", profile, expected)
    require(failures, "marker13-native", "native-gate", "parserProfile",
            {"family": GAP_PROFILE["family"], "rootMarker": GAP_PROFILE["rootMarker"],
             "rawSelector": GAP_PROFILE["rowSelectorU32"], "packedKey": GAP_PROFILE["key"],
             "marker": GAP_PROFILE["marker"], "readWidth": GAP_PROFILE["readWidth"]},
            {"family": expected["family"], "rootMarker": expected["rootMarker"],
             "rawSelector": expected["rawSelector"], "packedKey": expected["packedKey"],
             "marker": expected["marker"], "readWidth": expected["readWidth"]})
    return not failures


def unsupported_rows(rows: list[dict[str, Any]], family: str) -> dict[str, Any]:
    projected = []
    for row in rows:
        projected.append({
            **row,
            "status": "unsupported-context", "reason": f"family {family!r} is not selected family 'streaming'",
            "family": family, "partitionedBytes": 0,
        })
    return {"status": "unsupported-context-only", "evidenceLevel": "structural-only",
            "rows": projected, "counts": {"exact": 0, "ambiguous": 0,
                                           "unsupportedContext": len(projected)},
            "partitionedBytes": 0, "targetOwnedBytes": 0,
            "serializedSizeStatus": "unknown", "nativeFinalCursorStatus": "unknown",
            "semanticsStatus": "unresolved"}


def _resolved_identity(path: Path) -> str:
    try:
        return str(Path(path).resolve(strict=False)).casefold()
    except OSError as exc:
        raise ValueError(
            f"output-path-isolation: cannot resolve {path!s}: {type(exc).__name__}: {exc}"
        ) from exc


def _same_path(left: Path, right: Path) -> bool:
    if _resolved_identity(left) == _resolved_identity(right):
        return True
    # resolve catches existing symlinks. samefile additionally catches hard
    # links and platform aliases when both endpoints already exist.
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError as exc:
        raise ValueError(
            "output-path-isolation: cannot compare existing paths "
            f"{left!s} and {right!s}: {type(exc).__name__}: {exc}"
        ) from exc


def protected_input_paths(
    *, repo_root: Path, root_report_path: Path, outer_summary_path: Path,
    ledger_path: Path, outer: Mapping[str, Any], game_root: Path | None,
    source_paths: Mapping[str, Path], ledger_rows: list[Mapping[str, Any]] | None = None,
) -> dict[str, Path]:
    """Collect every file an output must not replace during/after validation."""
    protected = {
        "rootReport": Path(root_report_path),
        "outerSummary": Path(outer_summary_path),
        "outerLedger": Path(ledger_path),
    }
    protected.update({f"source:{name}": Path(path) for name, path in source_paths.items()})
    chunk_identities: dict[str, Path] = {}
    raw_chunks = {
        row["physicalChunkPath"] for row in (ledger_rows or [])
        if isinstance(row, Mapping) and isinstance(row.get("physicalChunkPath"), str)
        and row["physicalChunkPath"]
    }
    for raw in sorted(raw_chunks):
        path = Path(raw)
        canonical = _resolved_identity(path)
        chunk_identities.setdefault(canonical, path)
    for index, path in enumerate(chunk_identities.values()):
        protected[f"physicalChunk[{index}]"] = path
    rows = list(outer.get("sourceFingerprints") or []) + list(outer.get("buildFingerprints") or [])
    for index, row in enumerate(rows):
        raw = row.get("path") if isinstance(row, dict) else None
        if isinstance(raw, str) and raw:
            protected[f"outerFingerprint[{index}]"] = Path(raw)
    selected_root = game_root
    if selected_root is None and outer.get("primaryAssets"):
        selected_root = Path(str(outer["primaryAssets"])).parent
    if selected_root is not None:
        selected_root = Path(selected_root)
        protected.update({
            "native:GameAssembly.dll": selected_root.parent / "GameAssembly.dll",
            "native:global-metadata.dat": (
                selected_root / "il2cpp_data/Metadata/global-metadata.dat"
            ),
            "native:UnityPlayer.dll": selected_root.parent / "UnityPlayer.dll",
        })
    return protected


def validate_output_isolation(
    *, outputs: Mapping[str, Path | None], protected: Mapping[str, Path]
) -> None:
    """Reject output-output and output-input identity before any temp is made."""
    concrete = [(name, Path(path)) for name, path in outputs.items() if path is not None]
    for index, (left_name, left) in enumerate(concrete):
        for right_name, right in concrete[index + 1:]:
            if _same_path(left, right):
                raise ValueError(
                    "output-path-isolation: expected distinct outputs, actual "
                    f"{left_name}={left!s} conflicts with {right_name}={right!s}"
                )
        for protected_name, protected_path in protected.items():
            protected_path = Path(protected_path)
            if _same_path(left, protected_path):
                raise ValueError(
                    "output-path-isolation: expected output disjoint from authenticated inputs, "
                    f"actual {left_name}={left!s} conflicts with "
                    f"{protected_name}={protected_path!s}"
                )


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
            fd, name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
            self.temp_path = Path(name)
            self.raw = os.fdopen(fd, "wb")
            self.gz = gzip.GzipFile(filename="", fileobj=self.raw, mode="wb", mtime=0, compresslevel=6)
            self.text = io.TextIOWrapper(self.gz, encoding="utf-8", newline="\n")
        self.write({"recordType": "inventory_header", "schema": SCHEMA,
                    "inputSetSha256": input_set,
                    "sourceHashes": source_hashes,
                    "publicationStatus": "staged-until-terminal-summary-gate"})

    def write(self, row: dict[str, Any]) -> None:
        line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
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
        result = {"path": self.path.as_posix() if self.path else None,
                  "fileRowCount": self.file_rows,
                  "contentSha256": self.content_hash.hexdigest().upper()}
        if self.temp_path is not None and self.path is not None:
            result["gzipSha256"] = sha256_file(self.temp_path)
            os.replace(self.temp_path, self.path)
        return result


def sweep(*, repo_root: Path, root_report_path: Path, outer_summary_path: Path,
          ledger_path: Path, expected_input_set_sha256: str, game_root: Path | None = None,
          max_files: int | None = None, inventory_path: Path | None = None,
          progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    expected_input = expected_input_set_sha256.upper()
    if len(expected_input) != 64 or any(c not in "0123456789ABCDEF" for c in expected_input):
        failures.append(failure("arguments", "input-gate", "64 uppercase hexadecimal characters", expected_input))
    if max_files is not None and (type(max_files) is not int or max_files <= 0):
        failures.append(failure("arguments", "selection", "positive integer max_files or None", max_files))
    paths = source_paths(Path(repo_root))
    source_start = snapshot_sources(paths, failures, "source-start")
    input_paths = {"rootReportSha256": root_report_path, "outerSummarySha256": outer_summary_path,
                   "outerLedgerSha256": ledger_path}
    input_start = snapshot_sources(input_paths, failures, "input-start")
    report = read_json(root_report_path, failures, "root-report-read")
    outer = read_json(outer_summary_path, failures, "outer-summary-read")
    fingerprints_start = snapshot_fingerprints(outer, failures, "fingerprints-start")
    header, ledger_rows = read_ledger(ledger_path, failures)
    validate_root_report(report, outer, header, ledger_rows, expected_input,
                         input_start.get("outerLedgerSha256", ""), source_start, failures)
    if game_root is None and outer.get("primaryAssets"):
        game_root = Path(str(outer["primaryAssets"])).parent
    if game_root is None:
        failures.append(failure("arguments", "native-gate", "explicit game_root or authenticated outer primaryAssets", None))
        native = {"status": "validation_failed", "profile": None, "validationFailures": []}
    else:
        game_root = Path(game_root)
        native_inputs_start = snapshot_native_inputs(game_root, failures, "native-inputs-start")
        native = validate_marker13_native_contract(game_root=game_root)
    if game_root is None:
        native_inputs_start = {}
    native_ok = validate_native(native, source_start.get("marker13NativeContractSha256", ""), failures)
    require(failures, "native", "absent-selector-gate", "absentSelectorContextWitness",
            native.get("absentSelectorContextWitness"), EXPECTED_ABSENT_WITNESS)
    pair_index = {}
    if not failures:
        try:
            pair_index = index_ordered_pairs(report)
            require(failures, "root-report", "pair-index", "dataFileCount", len(pair_index),
                    sum(root_corpus._family(row["virtualPath"]) != "info" for row in ledger_rows))
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(failure("root-report", "pair-index", "complete source-bound ordered pairs", str(exc)))

    paths_seen = collections.Counter(str(row.get("virtualPath", "")) for row in ledger_rows)
    for path, count in paths_seen.items():
        if not path or count != 1:
            failures.append(failure(path or "outer-ledger", "ledger-identity", "unique nonempty virtualPath", count))
    selected = ledger_rows[:max_files] if max_files is not None else ledger_rows
    partial = max_files is not None
    try:
        validate_output_isolation(
            outputs={"outputInventory": inventory_path},
            protected=protected_input_paths(
                repo_root=repo_root, root_report_path=root_report_path,
                outer_summary_path=outer_summary_path, ledger_path=ledger_path,
                outer=outer, game_root=game_root, source_paths=paths,
                ledger_rows=ledger_rows,
            ),
        )
    except ValueError as exc:
        failures.append(failure(str(inventory_path), "output-path-isolation",
                                "output disjoint from inputs", str(exc)))
    sink = InventorySink(None if failures else inventory_path, input_set=expected_input,
                         source_hashes=source_start)
    counters = collections.Counter(filesSelected=len(selected), filesTotal=len(ledger_rows))
    identity_rows = []

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
                    failures.append(failure(str(row.get("virtualPath")), "chunk-open", "readable physical chunk",
                                            f"{type(exc).__name__}: {exc}"))
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
                            actual = str(row.get(field, "")).upper() if field == "inputSetSha256" else row.get(field)
                            if actual != expected:
                                raise ValueError(f"ledger {field}: expected {expected!r}, actual {actual!r}")
                        if type(offset) is not int or offset < 0 or type(length) is not int or length < 0:
                            raise ValueError(f"physical range: expected nonnegative integer offset/length, actual {offset!r}/{length!r}")
                        if offset > chunk_size or length > chunk_size - offset:
                            raise ValueError(f"physical range: expected 0 <= {offset} <= {offset}+{length} <= {chunk_size}")
                        family = root_corpus._family(virtual_path)
                        stream.seek(offset)
                        packed = stream.read(length)
                        if len(packed) != length:
                            raise ValueError(f"packed read length: expected {length}, actual {len(packed)}")
                        packed_md5 = hashlib.md5(packed, usedforsecurity=False).hexdigest().upper()
                        if packed_md5 != str(row.get("recomputedFileDataMd5", "")).upper():
                            raise ValueError(f"packed MD5: expected {row.get('recomputedFileDataMd5')}, actual {packed_md5}")
                        packed_sha = sha256_bytes(packed)
                        parsed = fmt.parse_streaming_file(
                            family, packed, allow_raw=virtual_path in root_corpus.RAW_DATA_EXCEPTIONS,
                            native_layout_validated=native_ok, include_certified_ranges=True)
                        clear = (fmt._decode_compressed(packed)
                                 if parsed.get("encoding") == "inverted_lz4" else packed)
                        if len(clear) != parsed.get("decodedBytes"):
                            raise ValueError(f"decoded length: expected parser {parsed.get('decodedBytes')}, actual {len(clear)}")
                        decoded_sha = sha256_bytes(clear)
                        pair_context = None
                        if family in {"init", "streaming"}:
                            pair_context = bind_current_pair(
                                pair_index=pair_index, identity={**row, "packedSha256": packed_sha},
                                decoded=clear, parsed=parsed,
                                root_report_sha256=input_start["rootReportSha256"],
                            )
                        parallel = parsed.get("anonymousParallelSubgraph") or {}
                        directory = parallel.get("marker13KeyDirectory") or {}
                        if family in {"init", "streaming"}:
                            if directory.get("status") != "exact-structural-reference-directory":
                                raise ValueError(f"marker13 directory status: expected exact-structural-reference-directory, actual {directory.get('status')!r}")
                            directory_rows = directory.get("rows")
                            if not isinstance(directory_rows, list):
                                raise ValueError(f"marker13 directory rows: expected list, actual {type(directory_rows).__name__}")
                            expected_references = parallel.get("nestedElementMarkerCounts", {}).get(13, 0)
                            if len(directory_rows) != expected_references:
                                raise ValueError(
                                    f"marker13 directory count: expected {expected_references}, actual {len(directory_rows)}"
                                )
                        else:
                            directory_rows = []
                        certified_ranges = parsed.get("decodedCertifiedRanges") or []
                        if family == "info":
                            info_status = (parsed.get("anonymousInner") or {}).get("status")
                            if info_status != "exact_anonymous":
                                raise ValueError(
                                    f"Info whole-file status: expected exact_anonymous, actual {info_status!r}"
                                )
                            certified_ranges = [(0, len(clear), "info-exact-anonymous-graph")]
                        if family == "streaming":
                            gap = parse_marker13_gaps(
                                clear, source=virtual_path, family=family, rows=directory_rows,
                                certified_ranges=certified_ranges,
                                native_layout_validated=native_ok, pair_context=pair_context,
                                absent_selector_native_witness=native["absentSelectorContextWitness"])
                        else:
                            gap = unsupported_rows(directory_rows, family)
                        counts = gap["counts"]
                        if counts["ambiguous"]:
                            raise ValueError(f"selected marker13 key ambiguity: expected 0, actual {counts['ambiguous']}")
                        if gap["partitionedBytes"] != counts["exact"] * 16:
                            raise ValueError(f"marker13 partitioned bytes: expected {counts['exact']*16}, actual {gap['partitionedBytes']}")
                        coverage = range_coverage(
                            len(clear), certified_ranges, gap["rows"])
                        if coverage["readWindowReferenceBytes"] != gap["partitionedBytes"]:
                            raise ValueError(
                                "marker13 range/reference bytes: expected "
                                f"{gap['partitionedBytes']}, actual {coverage['readWindowReferenceBytes']}"
                            )
                        if coverage["unionBytes"] + coverage["opaqueBytes"] != len(clear):
                            raise ValueError(
                                f"decoded range partition: expected {len(clear)}, actual "
                                f"{coverage['unionBytes'] + coverage['opaqueBytes']}"
                            )
                        if family == "info" and coverage["opaqueBytes"]:
                            raise ValueError(
                                "Info whole-file range coverage: expected zero opaque bytes, "
                                f"actual {coverage['opaqueBytes']}"
                            )
                        counters["filesSucceeded"] += 1
                        counters[f"family:{family}"] += 1
                        counters["packedBytes"] += len(packed)
                        counters["decodedBytes"] += len(clear)
                        counters["marker13References"] += sum(counts.values())
                        counters["exact"] += counts["exact"]
                        counters["ambiguous"] += counts["ambiguous"]
                        counters["unsupported"] += counts["unsupportedContext"]
                        counters["partitionedBytes"] += gap["partitionedBytes"]
                        counters["uniqueReadWindowBytes"] += coverage["uniqueReadWindowBytes"]
                        counters["opaqueBytes"] += coverage["opaqueBytes"]
                        for projection in gap["rows"]:
                            if projection["status"] == "exact-anonymous-physical-gap":
                                gap_length = projection["physicalGapRange"]["length"]
                                counters[f"physicalGapLength:{gap_length}"] += 1
                                context_name = "absent" if projection["rowSelectorU32"] is None else "explicit9"
                                counters[f"selectedContext:{context_name}"] += 1
                                residual = projection["residualOpaqueRange"]
                                counters["residualOpaqueReferenceBytes"] += residual["length"] if residual else 0
                        identity_rows.append("\0".join((virtual_path, str(row.get("physicalChunkSource")),
                                                       str(row.get("chunkFile")), str(offset), str(length),
                                                       packed_md5, packed_sha)))
                        sink.write({
                            "recordType": "file", "virtualPath": virtual_path, "family": family,
                            "physicalChunkPath": chunk_path.as_posix(),
                            "physicalChunkSource": row.get("physicalChunkSource"),
                            "metadataProvenance": row.get("metadataProvenance"),
                            "overlayState": row.get("overlayState"), "offset": offset, "length": length,
                            "packedMd5": packed_md5, "packedSha256": packed_sha,
                            "decodedLength": len(clear), "decodedSha256": decoded_sha,
                            "wholeLogicalFileStatus": (
                                "exact-anonymous-eof" if family == "info" else
                                "partial-with-explicit-opaque-complement"
                            ),
                            "rangeCoverage": coverage, "marker13": gap,
                            "orderedPairContext": pair_context,
                        })
                    except (OSError, ValueError, TypeError, KeyError, struct.error) as exc:
                        counters["filesFailed"] += 1
                        failures.append(failure(virtual_path, "file-validation",
                                                "authenticated parse and marker13 projection",
                                                f"{type(exc).__name__}: {exc}", offset=row.get("offset")))
                        if progress is not None and counters["filesFailed"] == 1:
                            progress({"firstFailure": failures[-1]})
                    done = counters["filesSucceeded"] + counters["filesFailed"]
                    if progress is not None and (done % 5000 == 0 or done == len(selected)):
                        progress({"parsed": done, "total": len(selected), "failed": counters["filesFailed"]})

    if not partial and not failures:
        identity_sha = sha256_bytes("\n".join(sorted(identity_rows)).encode("utf-8"))
        require(failures, "root-v15", "terminal-reconciliation", "logicalIdentitySetSha256",
                identity_sha, ((report.get("layer1") or {}).get("logicalIdentitySetSha256")))
        expected_references = ((report.get("layer3") or {}).get("nestedElementFraming") or {}).get(
            "nestedElementMarkerCounts", {}).get("13", 0)
        require(failures, "root-v15", "terminal-reconciliation", "marker13ReferenceCount",
                counters["marker13References"], expected_references)
    require(failures, "terminal", "terminal-reconciliation", "files",
            counters["filesSucceeded"] + counters["filesFailed"], len(selected))

    source_end = snapshot_sources(paths, failures, "source-end")
    input_end = snapshot_sources(input_paths, failures, "input-end")
    fingerprints_end = snapshot_fingerprints(outer, failures, "fingerprints-end")
    native_inputs_end = snapshot_native_inputs(game_root, failures, "native-inputs-end")
    require(failures, "source-set", "source-end", "sourceHashes", source_end, source_start)
    require(failures, "input-set", "input-end", "inputHashes", input_end, input_start)
    require(failures, "fingerprints", "input-end", "outerFingerprints", fingerprints_end, fingerprints_start)
    require(failures, "native-inputs", "input-end", "nativeInputHashes",
            native_inputs_end, native_inputs_start)

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
                "exactGapReferences": counters["exact"],
                "ambiguousReferences": counters["ambiguous"],
                "unsupportedOpaqueReferences": counters["unsupported"],
                "readWindowReferenceBytes": counters["partitionedBytes"],
                "uniqueReadWindowBytes": counters["uniqueReadWindowBytes"],
                "opaqueBytes": counters["opaqueBytes"],
            },
        })
    inventory = sink.finish(keep=success)
    result = {
        "schema": SCHEMA, "status": status, "failed": not success,
        "publicationEligible": success and not partial, "inputSetSha256": expected_input,
        "provenance": {
            "start": {"sourceHashes": source_start, "inputHashes": input_start,
                      "outerFingerprints": fingerprints_start,
                      "nativeInputs": native_inputs_start},
            "end": {"sourceHashes": source_end, "inputHashes": input_end,
                    "outerFingerprints": fingerprints_end,
                    "nativeInputs": native_inputs_end},
            "outerFingerprintCount": len(fingerprints_start),
            "outerFingerprintSetSha256": sha256_bytes(json.dumps(
                fingerprints_start, sort_keys=True, separators=(",", ":")).encode("utf-8")),
            "nativeValidation": native,
        },
        "selection": {"mode": "partial" if partial else "full",
                      "profile": dict(GAP_PROFILE),
                      "absentSelectorProfile": native.get("absentSelectorContextWitness"),
                      "unknownContextDisposition": "unsupported-opaque; physically authenticated and parsed; owns no gap bytes"},
        "summary": {
            "filesTotal": len(ledger_rows), "filesSelected": len(selected),
            "filesSucceeded": counters["filesSucceeded"], "filesFailed": counters["filesFailed"],
            "packedBytes": counters["packedBytes"], "decodedBytes": counters["decodedBytes"],
            "marker13References": counters["marker13References"],
            "exactGapReferences": counters["exact"], "ambiguousReferences": counters["ambiguous"],
            "unsupportedOpaqueReferences": counters["unsupported"],
            "readWindowReferenceBytes": counters["partitionedBytes"],
            "uniqueReadWindowBytes": counters["uniqueReadWindowBytes"],
            "opaqueBytes": counters["opaqueBytes"],
            "selectedPhysicalGapLengthCounts": {
                str(length): counters[f"physicalGapLength:{length}"]
                for length in GAP_PROFILE["physicalGapLengths"]
            },
            "residualOpaqueReferenceBytes": counters["residualOpaqueReferenceBytes"],
            "selectedContextCounts": {name: counters[f"selectedContext:{name}"]
                                      for name in ("explicit9", "absent")},
            "failed": len(failures), "unsupported": counters["unsupported"],
        },
        "layer3": {
            "status": "exact-anonymous-marker13-read-window-directory" if success else "unvalidated",
            "evidenceLevel": "structural-only", "inventory": inventory,
            "targetOwnedBytes": 0, "serializedSizeStatus": "unknown",
            "nativeFinalCursorStatus": "unknown", "semanticsStatus": "unresolved",
        },
        "evidenceBoundary": {
            "exact": "Selected physical gaps are bracketed by certified ranges and restricted to 16 or 18 bytes; only the first 16 bytes project four anonymous u32 lanes.",
            "structuralOnly": "Native proves only a conditional 16-byte read window. Any two-byte residual stays in the opaque complement, without padding or record-ownership claims.",
            "absence": "Actual row/vtable field2 absence and source-bound ordered Init/Streaming pairing are rechecked. Raw selector remains null; native accessor default0 is a separate conditional slot5 witness. Existing-key history, overrides and execution remain unresolved.",
            "unresolved": "Serialized record extent, sizeof, native EOF/final cursor, runtime receipt, field names and game semantics.",
        },
        "failures": failures, "failureCount": len(failures),
    }
    if inventory_path is None:
        result["_inventoryRows"] = sink.rows if success else []
    return result


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join([
        "# Streaming marker13 corpus gate", "",
        f"- Status: `{report['status']}`; publication eligible: `{str(report['publicationEligible']).lower()}`.",
        f"- Input set: `{report['inputSetSha256']}`.",
        f"- Files: {summary['filesSucceeded']:,} succeeded / {summary['filesFailed']:,} failed / {summary['filesSelected']:,} selected.",
        f"- Marker13: {summary['exactGapReferences']:,} exact gaps; {summary['ambiguousReferences']:,} ambiguous; {summary['unsupportedOpaqueReferences']:,} unsupported opaque.",
        f"- Read-window reference bytes: {summary['readWindowReferenceBytes']:,}; unique read-window bytes: {summary['uniqueReadWindowBytes']:,}; opaque complement bytes: {summary['opaqueBytes']:,}; failures: {report['failureCount']:,}.",
        f"- Selected physical gap lengths: {summary['selectedPhysicalGapLengthCounts']}; residual opaque reference bytes: {summary['residualOpaqueReferenceBytes']}.", "",
        "Certified adjacency bounds 16- or 18-byte physical gaps; native supplies only a conditional 16-byte read window. Any residual stays opaque. Serialized extent, native EOF, runtime receipt and semantics remain unresolved.", "",
    ])



from scripts.repo_paths import REPO_ROOT

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
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
    if args.max_files is not None:
        outputs = (args.output_json, args.output_md, args.output_inventory)
        if any(value is None for value in outputs):
            parser.error("--max-files requires explicit JSON, Markdown and inventory outputs")
        if any(not _is_bounded_diagnostic_output(Path(value), root) for value in outputs):
            parser.error("--max-files outputs must stay under repo tmp/ or scratch/ and cannot replace reports")
    output_json = args.output_json or root / "reports/animestudio/streaming_marker13_latest.json"
    output_md = args.output_md or root / "reports/animestudio/streaming_marker13_latest.md"
    output_inventory = args.output_inventory or root / "reports/animestudio/streaming_marker13_inventory_latest.jsonl.gz"
    root_report = args.root_report or root / "reports/animestudio/streaming_root_subgraphs_latest.json"
    outer_summary = args.outer_summary or root / "reports/animestudio/vfs_understanding_latest.json"
    outer_ledger = args.outer_ledger or root / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
    preflight_failures = []
    outer = read_json(outer_summary, preflight_failures, "output-preflight")
    _header, ledger_rows = read_ledger(outer_ledger, preflight_failures)
    if preflight_failures:
        parser.error(json.dumps(preflight_failures[0], ensure_ascii=False))
    try:
        validate_output_isolation(
            outputs={"outputJson": output_json, "outputMarkdown": output_md,
                     "outputInventory": output_inventory},
            protected=protected_input_paths(
                repo_root=root, root_report_path=root_report, outer_summary_path=outer_summary,
                ledger_path=outer_ledger, outer=outer, game_root=args.game_root,
                source_paths=source_paths(root), ledger_rows=ledger_rows,
            ),
        )
    except ValueError as exc:
        parser.error(str(exc))
    result = sweep(
        repo_root=root,
        root_report_path=root_report,
        outer_summary_path=outer_summary,
        ledger_path=outer_ledger,
        expected_input_set_sha256=args.input_set_sha256, game_root=args.game_root,
        max_files=args.max_files, inventory_path=output_inventory,
        progress=lambda row: print(json.dumps(row), flush=True),
    )
    serializable = {key: value for key, value in result.items() if not key.startswith("_")}
    root_corpus._atomic_write_text(output_md, render_markdown(serializable))
    # JSON is the terminal summary/commit marker; publish it after inventory and Markdown.
    root_corpus._atomic_write_text(output_json, json.dumps(serializable, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "publicationEligible": result["publicationEligible"],
                      **result["summary"]}, indent=2))
    if result["failed"] and result["failures"]:
        print("firstFailure=" + json.dumps(result["failures"][0], ensure_ascii=False),
              file=sys.stderr)
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
