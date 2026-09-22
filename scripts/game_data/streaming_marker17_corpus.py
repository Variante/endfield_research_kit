"""Fail-closed corpus gate for native-selected marker17 anonymous bodies.

This gate consumes the authenticated v15 marker17 directory.  It does
not rerun the larger Streaming parser, but it rereads and authenticates every
directory reference, including profile-excluded opaque references.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.repo_paths import REPO_ROOT

DEFAULT_REPO_ROOT = REPO_ROOT

from scripts.game_data import streaming as fmt
from scripts.game_data import streaming_corpus as corpus
from scripts.game_data.streaming_marker17 import TAG5_RECORD_WIDTHS, FIXED_BODY_PROFILES, TAG5_BODY_KEYS, parse_marker17_body
from scripts.game_data.streaming_marker17_native import validate_marker17_native_contract
from scripts.common import sha256_file_upper as sha256_file

SCHEMA = "endfield.streaming-marker17-bodies-corpus.v2"
V15_SCHEMA = "endfield.streaming-root-subgraphs-corpus.v15"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()



def _failure(source: str, stage: str, expected: Any, actual: Any,
             *, offset: int | None = None, field: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": source, "stage": stage, "expected": expected, "actual": actual,
    }
    if offset is not None:
        result["offset"] = offset
    if field is not None:
        result["field"] = field
    return result


def _require(failures: list[dict[str, Any]], source: str, stage: str,
             field: str, actual: Any, expected: Any, *, offset: int | None = None) -> bool:
    if actual == expected:
        return True
    failures.append(_failure(source, stage, expected, actual, offset=offset, field=field))
    return False


def _source_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "v15ParserSha256": repo_root / "scripts/game_data/streaming.py",
        "v15CorpusGateSha256": repo_root / "scripts/game_data/contracts/streaming_corpus.py",
        "v15NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_native.py",
        "v15NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_field2_native.json",
        "marker17ParserSha256": repo_root / "scripts/game_data/contracts/streaming_marker17.py",
        "marker17NativeValidatorSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.py",
        "marker17NativeContractSha256": repo_root / "scripts/game_data/contracts/streaming_marker17_native.json",
        "marker17CorpusGateSha256": Path(__file__).resolve(),
    }


def _snapshot_sources(paths: dict[str, Path], failures: list[dict[str, Any]], stage: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, path in paths.items():
        try:
            result[name] = sha256_file(path)
        except OSError as exc:
            failures.append(_failure(path.as_posix(), stage, "readable source", f"{type(exc).__name__}: {exc}", field=name))
    return result


def _fingerprint_rows(outer: dict[str, Any]) -> list[dict[str, Any]]:
    return list(outer.get("sourceFingerprints") or []) + list(outer.get("buildFingerprints") or [])


def _snapshot_outer_fingerprints(outer: dict[str, Any], failures: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    rows = _fingerprint_rows(outer)
    if not rows:
        failures.append(_failure("outer-summary", stage, "nonempty fingerprint inventory", 0,
                                 field="sourceFingerprints+buildFingerprints"))
        return []
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        source = f"outer-fingerprint[{index}]"
        raw_path = row.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(_failure(source, stage, "nonempty path", raw_path, field="path"))
            continue
        path = Path(raw_path)
        canonical = str(path.resolve()).casefold()
        if canonical in seen:
            failures.append(_failure(source, stage, "unique resolved path", str(path.resolve()), field="path"))
            continue
        seen.add(canonical)
        try:
            length = path.stat().st_size
            digest = sha256_file(path)
        except OSError as exc:
            failures.append(_failure(path.as_posix(), stage, "readable fingerprint source", f"{type(exc).__name__}: {exc}"))
            continue
        _require(failures, path.as_posix(), stage, "length", length, row.get("length"))
        _require(failures, path.as_posix(), stage, "sha256", digest, str(row.get("sha256", "")).upper())
        result.append({"path": path.as_posix(), "length": length, "sha256": digest})
    return result


def _read_json(path: Path, failures: list[dict[str, Any]], stage: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("top-level JSON is not an object")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(_failure(path.as_posix(), stage, "readable JSON object", f"{type(exc).__name__}: {exc}"))
        return None


def _read_ledger(path: Path, failures: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    headers: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    failures.append(_failure(path.as_posix(), "ledger-read", "valid JSON line", exc.msg, offset=line_number))
                    continue
                if row.get("recordType") == "audit_header":
                    headers.append(row)
                elif row.get("recordType") == "file" and row.get("blockTypeValue") == 15:
                    rows.append(row)
    except (OSError, UnicodeError, EOFError) as exc:
        failures.append(_failure(path.as_posix(), "ledger-read", "readable gzip JSONL", f"{type(exc).__name__}: {exc}"))
    _require(failures, path.as_posix(), "ledger-read", "auditHeaderCount", len(headers), 1)
    if not rows:
        failures.append(_failure(path.as_posix(), "ledger-read", "at least one block-15 file row", len(rows)))
    return (headers[0] if len(headers) == 1 else None), rows


def _pack_native_key(words: Any) -> int:
    if not isinstance(words, list) or len(words) != 3 or any(type(word) is not int or not 0 <= word <= 0xFFFFFFFF for word in words):
        raise ValueError(f"expected three uint32 key words, actual {words!r}")
    # Selected contract words are packed using the exact native expression.
    packed = (((words[0] << 8) | words[1]) << 16) | words[2]
    if packed > 0xFFFFFFFF:
        raise ValueError(f"packed selected key exceeds uint32: {packed}")
    return packed


def _validate_native_profile(native: dict[str, Any], failures: list[dict[str, Any]],
                             contract_sha: str) -> dict[int, int]:
    source = "streaming-marker17-native"
    _require(failures, source, "native-gate", "status", native.get("status"), "validated")
    _require(failures, source, "native-gate", "validationFailures", native.get("validationFailures") or [], [])
    _require(failures, source, "native-gate", "contractSha256",
             str(native.get("contractSha256", "")).upper(), contract_sha)
    profile = native.get("profile") or {}
    expected = {
        "tag": 5, "tagByteOffset": 28, "headerSize": 64,
        "countByteOffsets": [40, 44, 48, 52, 56, 60],
        "recordWidths": list(TAG5_RECORD_WIDTHS), "fields": "opaque",
        "evidenceLevel": "structural-only",
    }
    for field, value in expected.items():
        _require(failures, source, "native-profile", field, profile.get(field), value)
    selected: dict[int, int] = {}
    for index, row in enumerate(profile.get("selectedSlot3Keys") or []):
        try:
            selector = row["selector"]
            if type(selector) is not int or not 0 <= selector <= 0xFFFFFFFF:
                raise ValueError(f"selector is not uint32: {selector!r}")
            packed = _pack_native_key(row["key"])
            if selector in selected or packed in selected.values():
                raise ValueError(f"duplicate selector or key: {selector}/{packed:08X}")
            selected[selector] = packed
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(_failure(f"{source}.selectedSlot3Keys[{index}]", "native-profile",
                                     "unique selector and three uint32 words", str(exc)))
    expected_selected = dict(TAG5_BODY_KEYS)
    expected_selected.update({selector: key for selector, key in FIXED_BODY_PROFILES})
    _require(failures, source, "native-profile", "selectedIdentityUnion",
             sorted(selected.items()), sorted(expected_selected.items()))
    actual_fixed = []
    for index, row in enumerate(profile.get("fixedBodyProfiles") or []):
        try:
            selector, tag, length = row['selector'], row['tag'], row['bodyLength']
            key = _pack_native_key(row['key'])
            if any(type(v) is not int for v in (selector, tag, length)) or length < 32:
                raise ValueError('expected integer selector/tag and length >= 32')
            _require(failures, source, 'native-profile', 'conditionalReadCoverage',
                     row.get('conditionalReadCoverage'), [[0, 30], [32, length]])
            _require(failures, source, 'native-profile', 'opaqueUnreadRanges',
                     row.get('opaqueUnreadRanges'), [[30, 32]])
            actual_fixed.append((selector, key, tag, length))
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(_failure(f'{source}.fixedBodyProfiles[{index}]', 'native-profile',
                                     'bounded fixed profile joined to parser', str(exc)))
    _require(failures, source, 'native-profile', 'fixedBodyProfiles', sorted(actual_fixed),
             sorted((s, k, t, n) for (s, k), (t, n) in FIXED_BODY_PROFILES.items()))
    return selected


def _classify(file_row: dict[str, Any], row: dict[str, Any], selected: dict[int, int],
              failures: list[dict[str, Any]]) -> str:
    source = str(file_row.get("virtualPath", ""))
    key = row.get("key")
    if type(key) is not int or not 0 <= key <= 0xFFFFFFFF:
        failures.append(_failure(source, "directory-profile", "uint32 key", key,
                                 offset=row.get("keyOffset"), field="key"))
        return "invalid"
    expected_hex = f"{key:08X}"
    if row.get("keyHex") != expected_hex:
        failures.append(_failure(source, "directory-profile", expected_hex, row.get("keyHex"),
                                 offset=row.get("keyOffset"), field="keyHex"))
        return "invalid"
    selectors = [selector for selector, packed in selected.items() if packed == key]
    if not selectors:
        return "unsupported"
    expected_contexts = [
        ("streaming", 2, selector, selector & 0xFF, "unique", 17, 1)
        for selector in selectors
    ]
    actual = (file_row.get("family"), row.get("rootMarker"), row.get("rowSelectorU32"),
              row.get("rowSelectorLowByte"), row.get("keyStatus"), row.get("marker"), row.get("keyOccurrenceCountInTable"))
    if actual not in expected_contexts:
        failures.append(_failure(source, "directory-profile", expected_contexts, actual,
                                 offset=row.get("keyOffset"), field="selectedKeyContext"))
        return "invalid"
    return "supported"


def _validate_v15(report: dict[str, Any], expected_input: str, source_hashes: dict[str, str],
                  selected: dict[int, int], failures: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], collections.Counter]:
    source = "v15-report"
    _require(failures, source, "report-contract", "schema", report.get("schema"), V15_SCHEMA)
    _require(failures, source, "report-contract", "status", report.get("status"), "complete")
    _require(failures, source, "report-contract", "failed", report.get("failed"), False)
    _require(failures, source, "report-contract", "inputSetSha256", str(report.get("inputSetSha256", "")).upper(), expected_input)
    provenance = report.get("provenance") or {}
    _require(failures, source, "report-contract", "provenance.inputSetSha256",
             str(provenance.get("inputSetSha256", "")).upper(), expected_input)
    provenance_names = {
        "parserSha256": "v15ParserSha256", "corpusGateSha256": "v15CorpusGateSha256",
        "nativeValidatorSha256": "v15NativeValidatorSha256",
        "nativeContractSha256": "v15NativeContractSha256",
    }
    for report_name, source_name in provenance_names.items():
        _require(failures, source, "report-provenance", report_name,
                 str(provenance.get(report_name, "")).upper(), source_hashes.get(source_name))
    summary = report.get("summary") or {}
    _require(failures, source, "report-contract", "summary.failed", summary.get("failed"), 0)
    _require(failures, source, "report-contract", "summary.unsupported", summary.get("unsupported"), 0)
    _require(failures, source, "report-contract", "summary.gateFailures", summary.get("gateFailures"), 0)
    _require(failures, source, "report-contract", "summary.parsed", summary.get("parsed"), summary.get("streamingFiles"))
    _require(failures, source, "report-contract", "failures", report.get("failures"), [])

    layer3 = report.get("layer3") or {}
    directory = layer3.get("marker17KeyDirectory") or {}
    for field, expected in (("status", "exact-structural-directory"), ("evidenceLevel", "structural-only"),
                            ("bodyStatus", "opaque"), ("runtimeSelectionStatus", "unresolved"),
                            ("targetOwnedBytes", 0)):
        _require(failures, "marker17-directory", "directory-contract", field, directory.get(field), expected)
    files = directory.get("files") or []
    if not isinstance(files, list):
        failures.append(_failure("marker17-directory", "directory-contract", "list files", type(files).__name__))
        files = []
    counts = collections.Counter(files=len(files))
    seen_files: set[str] = set()
    for file_row in files:
        virtual_path = file_row.get("virtualPath")
        if not isinstance(virtual_path, str) or not virtual_path or virtual_path in seen_files:
            failures.append(_failure("marker17-directory", "directory-contract", "unique nonempty virtualPath", virtual_path))
        seen_files.add(str(virtual_path))
        seen_rows: set[tuple[Any, Any]] = set()
        for row in file_row.get("rows") or []:
            identity = (row.get("outerRowIndex"), row.get("elementIndex"))
            if identity in seen_rows:
                failures.append(_failure(str(virtual_path), "directory-contract", "unique row identity", identity))
            seen_rows.add(identity)
            byte_count = row.get("byteCount")
            if type(byte_count) is not int or byte_count < 0:
                failures.append(_failure(str(virtual_path), "directory-contract", "nonnegative byteCount", byte_count,
                                         offset=row.get("targetSlotOffset")))
                byte_count = 0
            counts["references"] += 1
            counts["bytes"] += byte_count
            kind = _classify(file_row, row, selected, failures)
            counts[kind] += 1
            counts[f"{kind}Bytes"] += byte_count
    for field, expected in (("referenceCount", counts["references"]), ("countedBytes", counts["bytes"]),
                            ("filesWithReferences", counts["files"]),
                            ("ambiguousReferenceCount", sum(
                                row.get("keyStatus") == "ambiguous" for f in files for row in (f.get("rows") or [])))):
        _require(failures, "marker17-directory", "directory-reconcile", field, directory.get(field), expected)

    framing = layer3.get("nestedElementFraming") or {}
    marker_counts = framing.get("nestedElementMarkerCounts") or {}
    framed_counts = framing.get("nestedElementFramedCounts") or {}
    byte_counts = framing.get("nestedElementByteCounts") or {}
    _require(failures, "nested-element-framing", "directory-reconcile", "marker17Count", marker_counts.get("17"), counts["references"])
    _require(failures, "nested-element-framing", "directory-reconcile", "framed17Count", framed_counts.get("17"), counts["references"])
    _require(failures, "nested-element-framing", "directory-reconcile", "marker17Bytes", byte_counts.get("17"), counts["bytes"])
    try:
        expected_opaque = sum(int(value) for value in marker_counts.values()) - int(framed_counts.get("17", 0))
    except (TypeError, ValueError):
        expected_opaque = None
    _require(failures, "nested-element-framing", "directory-reconcile", "opaqueElementCount",
             framing.get("opaqueElementCount"), expected_opaque)
    _require(failures, "nested-element-framing", "directory-contract", "marker17Representation",
             framing.get("marker17Representation"), "two-wrappers-to-opaque-counted-bytes")
    _require(failures, "nested-element-framing", "directory-contract", "markerMeaning",
             framing.get("markerMeaning"), "unresolved-not-a-proven-union-registry")
    return files, counts


def _validate_outer(outer: dict[str, Any], header: dict[str, Any] | None, expected_input: str,
                    ledger_sha: str, report: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    source = "outer-summary"
    _require(failures, source, "outer-contract", "inputSetSha256", str(outer.get("inputSetSha256", "")).upper(), expected_input)
    _require(failures, source, "outer-contract", "summary.fullAuditPassed", (outer.get("summary") or {}).get("fullAuditPassed"), True)
    _require(failures, source, "outer-contract", "publication.ledgerSha256",
             str((outer.get("publication") or {}).get("ledgerSha256", "")).upper(), ledger_sha)
    provenance = report.get("provenance") or {}
    _require(failures, "v15-report", "outer-join", "outerLedgerSha256",
             str(provenance.get("outerLedgerSha256", "")).upper(), ledger_sha)
    for field in ("primaryAssets", "fallbackAssets"):
        _require(failures, "v15-report", "outer-join", field, provenance.get(field), outer.get(field))
    if header is not None:
        _require(failures, "outer-ledger", "ledger-contract", "inputSetSha256",
                 str(header.get("inputSetSha256", "")).upper(), expected_input)
        for field in ("primaryAssets", "fallbackAssets"):
            _require(failures, "outer-ledger", "ledger-contract", field, header.get(field), outer.get(field))


def _join_ledger(files: list[dict[str, Any]], ledger_rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for row in ledger_rows:
        path = row.get("virtualPath")
        if not isinstance(path, str) or not path or path in by_path:
            failures.append(_failure("outer-ledger", "ledger-join", "unique nonempty virtualPath", path))
            continue
        by_path[path] = row
    joined: dict[str, dict[str, Any]] = {}
    identity_fields = ("physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState", "offset", "length")
    for file_row in files:
        path = str(file_row.get("virtualPath", ""))
        ledger = by_path.get(path)
        if ledger is None:
            failures.append(_failure(path, "ledger-join", "exact block-15 ledger row", "missing"))
            continue
        for field in identity_fields:
            report_value, ledger_value = file_row.get(field), ledger.get(field)
            if field == "physicalChunkPath" and isinstance(report_value, str) and isinstance(ledger_value, str):
                report_value = str(Path(report_value).resolve()).casefold()
                ledger_value = str(Path(ledger_value).resolve()).casefold()
            _require(failures, path, "ledger-join", field, report_value, ledger_value)
        _require(failures, path, "ledger-join", "status", ledger.get("status"), "verified")
        _require(failures, path, "ledger-join", "boundaryStatus", ledger.get("boundaryStatus"), "boundary_verified")
        _require(failures, path, "ledger-join", "encrypted", ledger.get("encrypted"), False)
        _require(failures, path, "ledger-join", "actualBytesRead", ledger.get("actualBytesRead"), ledger.get("length"))
        joined[path] = ledger
    return joined


def _validate_row(clear: bytes, file_row: dict[str, Any], row: dict[str, Any], kind: str) -> tuple[dict[str, Any] | None, int]:
    source = str(file_row["virtualPath"])
    slot = row.get("targetSlotOffset")
    marker = row.get("marker")
    if type(slot) is not int or slot < 0:
        raise ValueError(f"{source} decoded offset {slot}: expected nonnegative targetSlotOffset, actual {slot}")
    if type(marker) is not int or marker != 17:
        raise ValueError(f"{source} decoded offset {row.get('markerOffset')}: expected directory marker 17, actual {marker}")
    key_offset = row.get("keyOffset")
    if type(key_offset) is not int or key_offset < 0 or key_offset > len(clear) - 4:
        raise ValueError(f"{source} decoded offset {key_offset}: expected bounded uint32 key range within EOF {len(clear)}, actual {key_offset}")
    actual_key = struct.unpack_from("<I", clear, key_offset)[0]
    if actual_key != row.get("key"):
        raise ValueError(f"{source} decoded offset {key_offset}: expected directory key {row.get('key')}, actual {actual_key}")
    marker_offset = row.get("markerOffset")
    if type(marker_offset) is not int or marker_offset < 0 or marker_offset >= len(clear):
        raise ValueError(f"{source} decoded offset {marker_offset}: expected bounded marker byte within EOF {len(clear)}, actual {marker_offset}")
    actual_marker = clear[marker_offset]
    if actual_marker != marker:
        raise ValueError(f"{source} decoded offset {marker_offset}: expected directory marker {marker}, actual {actual_marker}")
    replay, count = fmt._nested_reference_ranges(clear, slot, marker, f"marker17 row {row.get('outerRowIndex')}/{row.get('elementIndex')}")
    expected_ranges = [{"start": start, "end": end, "kind": range_kind} for start, end, range_kind, _ in replay]
    if row.get("wrapperAndByteRanges") != expected_ranges:
        raise ValueError(f"{source} decoded offset {slot}: expected wrapperAndByteRanges {row.get('wrapperAndByteRanges')!r}, actual {expected_ranges!r}")
    if count != row.get("byteCount"):
        raise ValueError(f"{source} decoded offset {expected_ranges[-1]['start']}: expected byteCount {row.get('byteCount')}, actual {count}")
    if kind != "supported":
        return None, count
    prefix = expected_ranges[-1]["start"]
    body_start, body_end = prefix + 4, expected_ranges[-1]["end"]
    body = clear[body_start:body_end]
    parsed = parse_marker17_body(body, source=source, base_offset=body_start, native_layout_validated=True,
                                 selector=row['rowSelectorU32'], key=row['key'])
    return {
        "family": file_row.get("family"), "rootMarker": row.get("rootMarker"),
        "selector": row.get("rowSelectorU32"), "rowSelectorLowByte": row.get("rowSelectorLowByte"),
        "key": row.get("key"), "keyHex": row.get("keyHex"), "keyOffset": row.get("keyOffset"),
        "outerRowIndex": row.get("outerRowIndex"), "outerRowOffset": row.get("outerRowOffset"),
        "elementIndex": row.get("elementIndex"), "marker": marker, "markerOffset": row.get("markerOffset"),
        "targetSlotOffset": slot, "byteCount": count, "wrapperAndByteRanges": expected_ranges,
        "bodySha256": sha256_bytes(body), "parsed": parsed,
    }, count


def _finalize(*, expected_input: str, failures: list[dict[str, Any]], partial: bool,
              provenance: dict[str, Any], directory_counts: collections.Counter,
              counters: collections.Counter, selected_count: int, files: list[dict[str, Any]],
              target_keys: dict[int, int], native: dict[str, Any]) -> dict[str, Any]:
    success = not failures
    status = "partial" if success and partial else "complete" if success else "failed"
    published = files if success else []
    profile_counts = collections.Counter()
    profile_bytes = collections.Counter()
    for file_row in published:
        for row in file_row['rows']:
            identity = (row['selector'], row['key'])
            profile_counts[identity] += 1
            profile_bytes[identity] += row['byteCount']
    return {
        "schema": SCHEMA, "status": status, "failed": not success,
        "publicationEligible": success and not partial, "inputSetSha256": expected_input,
        "provenance": provenance,
        "selection": {
            "mode": "partial" if partial else "full", "selectedFileCount": selected_count,
            "profiles": [{"family": "streaming", "rootMarker": 2, "selector": selector,
                          "key": key, "keyHex": f"{key:08X}", "keyStatus": "unique",
                          "tag": FIXED_BODY_PROFILES.get((selector, key), (5, None))[0],
                          "fixedBodyLength": FIXED_BODY_PROFILES.get((selector, key), (5, None))[1],
                          "layoutKind": "fixed-profile" if (selector, key) in FIXED_BODY_PROFILES else "tag5-counted-arrays",
                          "referenceCount": profile_counts[(selector, key)],
                          "countedBytes": profile_bytes[(selector, key)], "evidenceLevel": "structural-only"}
                         for selector, key in sorted(target_keys.items())],
            "profileExcludedDisposition": "opaque; physically revalidated; not a supported-profile format failure",
        },
        "corpusDirectory": dict(sorted(directory_counts.items())),
        "summary": {
            "filesSelected": selected_count, "filesSucceeded": counters["filesSucceeded"],
            "filesFailed": counters["filesFailed"], "referencesValidated": counters["references"],
            "bytesValidated": counters["bytes"], "supportedReferences": counters["supported"],
            "supportedBytes": counters["supportedBytes"], "unsupportedOpaqueReferences": counters["unsupported"],
            "unsupportedOpaqueBytes": counters["unsupportedBytes"],
            "failed": len(failures), "unsupported": counters["unsupported"],
        },
        "layer3": {"marker17BodyDirectory": {
            "status": "exact-anonymous-supported-bodies" if success else "unvalidated",
            "evidenceLevel": "structural-only", "files": published,
            "referenceCount": sum(len(file_row["rows"]) for file_row in published),
            "countedBytes": sum(row["byteCount"] for file_row in published for row in file_row["rows"]),
            "targetOwnedBytes": 0, "recordFieldMeaning": "unresolved",
            "runtimeSelectionStatus": "unresolved",
        }},
        "nativeValidation": native, "failures": failures,
        "evidenceBoundary": {
            "exact": "Authenticated logical ranges, the v15 two-wrapper byte ranges, selected header/tag/count domains, anonymous strides, and parser EOF are checked.",
            "structuralOnly": "Record bytes and anonymous gaps remain opaque.",
            "unresolved": "Native final cursor, concrete runtime receipt, field names, object population and game semantics remain unresolved.",
        },
    }


def sweep(*, repo_root: Path, report_path: Path, outer_summary_path: Path, ledger_path: Path,
          expected_input_set_sha256: str, game_root: Path | None = None,
          max_files: int | None = None) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    expected_input = expected_input_set_sha256.upper()
    if len(expected_input) != 64 or any(c not in "0123456789ABCDEF" for c in expected_input):
        failures.append(_failure("arguments", "input-gate", "64 hexadecimal characters", expected_input,
                                 field="expected_input_set_sha256"))
    if max_files is not None and max_files <= 0:
        failures.append(_failure("arguments", "selection", "positive max_files or None", max_files, field="max_files"))
    source_paths = _source_paths(Path(repo_root))
    source_start = _snapshot_sources(source_paths, failures, "source-start")
    report_sha_start = sha256_file(report_path) if report_path.is_file() else ""
    outer_sha_start = sha256_file(outer_summary_path) if outer_summary_path.is_file() else ""
    ledger_sha_start = sha256_file(ledger_path) if ledger_path.is_file() else ""
    report = _read_json(report_path, failures, "report-read") or {}
    outer = _read_json(outer_summary_path, failures, "outer-read") or {}
    fingerprints_start = _snapshot_outer_fingerprints(outer, failures, "outer-fingerprint-start")
    header, ledger_rows = _read_ledger(ledger_path, failures)
    if game_root is None and outer.get("primaryAssets"):
        game_root = Path(str(outer["primaryAssets"])).parent
    if game_root is None:
        failures.append(_failure("arguments", "native-gate", "explicit game_root or outer.primaryAssets", None))
        native: dict[str, Any] = {"status": "validation_failed", "validationFailures": []}
    else:
        native = validate_marker17_native_contract(game_root=Path(game_root))
    target_keys = _validate_native_profile(native, failures, source_start.get("marker17NativeContractSha256", ""))
    directory_files, directory_counts = _validate_v15(report, expected_input, source_start, target_keys, failures)
    _validate_outer(outer, header, expected_input, ledger_sha_start, report, failures)
    joined = _join_ledger(directory_files, ledger_rows, failures)
    selected = directory_files[:max_files] if max_files is not None else directory_files
    partial = max_files is not None
    counters: collections.Counter = collections.Counter()
    output_files: list[dict[str, Any]] = []

    # Preliminary provenance or schema failures prohibit touching body bytes.
    if not failures:
        by_chunk: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for file_row in selected:
            by_chunk[str(file_row.get("physicalChunkPath", ""))].append(file_row)
        for chunk_name, chunk_files in by_chunk.items():
            chunk_path = Path(chunk_name)
            try:
                stream = chunk_path.open("rb")
            except OSError as exc:
                counters["filesFailed"] += len(chunk_files)
                for file_row in chunk_files:
                    failures.append(_failure(str(file_row.get("virtualPath")), "chunk-open",
                                             "readable physical chunk", f"{type(exc).__name__}: {exc}"))
                continue
            with stream:
                for file_row in chunk_files:
                    virtual_path = str(file_row["virtualPath"])
                    ledger = joined[virtual_path]
                    try:
                        offset, length = file_row.get("offset"), file_row.get("length")
                        if type(offset) is not int or offset < 0:
                            raise ValueError(f"offset: expected nonnegative integer, actual {offset!r}")
                        if type(length) is not int or length < 0:
                            raise ValueError(f"length: expected nonnegative integer, actual {length!r}")
                        chunk_size = chunk_path.stat().st_size
                        if offset > chunk_size or length > chunk_size - offset:
                            raise ValueError(f"range: expected 0 <= {offset} <= {offset}+{length} <= {chunk_size}, actual out of bounds")
                        stream.seek(offset)
                        packed = stream.read(length)
                        if len(packed) != length:
                            raise ValueError(f"read length: expected {length}, actual {len(packed)}")
                        packed_sha = sha256_bytes(packed)
                        if packed_sha != str(file_row.get("packedSha256", "")).upper():
                            raise ValueError(f"packed SHA-256: expected {file_row.get('packedSha256')}, actual {packed_sha}")
                        packed_md5 = hashlib.md5(packed, usedforsecurity=False).hexdigest().upper()
                        if packed_md5 != str(ledger.get("recomputedFileDataMd5", "")).upper():
                            raise ValueError(f"ledger MD5: expected {ledger.get('recomputedFileDataMd5')}, actual {packed_md5}")
                        clear = fmt._decode_compressed(packed)
                        staged_rows: list[dict[str, Any]] = []
                        local = collections.Counter()
                        for row in file_row.get("rows") or []:
                            kind = _classify(file_row, row, target_keys, failures)
                            if kind == "invalid":
                                raise ValueError(f"directory row at key offset {row.get('keyOffset')} is outside validated profile")
                            parsed, count = _validate_row(clear, file_row, row, kind)
                            local["references"] += 1
                            local["bytes"] += count
                            local[kind] += 1
                            local[f"{kind}Bytes"] += count
                            if parsed is not None:
                                staged_rows.append(parsed)
                        counters.update(local)
                        output_files.append({
                            "virtualPath": virtual_path, "physicalChunkPath": chunk_path.as_posix(),
                            "physicalChunkSource": file_row.get("physicalChunkSource"),
                            "metadataProvenance": file_row.get("metadataProvenance"),
                            "overlayState": file_row.get("overlayState"), "offset": offset, "length": length,
                            "packedSha256": packed_sha, "ledgerMd5": packed_md5,
                            "decodedLength": len(clear), "decodedSha256": sha256_bytes(clear), "rows": staged_rows,
                        })
                        counters["filesSucceeded"] += 1
                    except (OSError, ValueError, struct.error) as exc:
                        counters["filesFailed"] += 1
                        failures.append(_failure(virtual_path, "file-validation", "authenticated directory and selected marker17 body",
                                                 f"{type(exc).__name__}: {exc}", offset=file_row.get("offset")))

    expected_selected = collections.Counter(files=len(selected))
    for file_row in selected:
        for row in file_row.get("rows") or []:
            byte_count = row.get("byteCount")
            if type(byte_count) is int and byte_count >= 0:
                expected_selected["bytes"] += byte_count
            expected_selected["references"] += 1
            kind = _classify(file_row, row, target_keys, failures)
            expected_selected[kind] += 1
            if type(byte_count) is int and byte_count >= 0:
                expected_selected[f"{kind}Bytes"] += byte_count
    for field, actual, expected in (
        ("files", counters["filesSucceeded"] + counters["filesFailed"], expected_selected["files"]),
        ("references", counters["references"], expected_selected["references"]),
        ("bytes", counters["bytes"], expected_selected["bytes"]),
        ("supported", counters["supported"], expected_selected["supported"]),
        ("unsupported", counters["unsupported"], expected_selected["unsupported"]),
        ("supportedBytes", counters["supportedBytes"], expected_selected["supportedBytes"]),
        ("unsupportedBytes", counters["unsupportedBytes"], expected_selected["unsupportedBytes"]),
    ):
        _require(failures, "terminal-reconciliation", "terminal-reconciliation", field, actual, expected)

    source_end = _snapshot_sources(source_paths, failures, "source-end")
    fingerprints_end = _snapshot_outer_fingerprints(outer, failures, "outer-fingerprint-end")
    end_hashes = {
        "v15ReportSha256": sha256_file(report_path) if report_path.is_file() else "",
        "outerSummarySha256": sha256_file(outer_summary_path) if outer_summary_path.is_file() else "",
        "outerLedgerSha256": sha256_file(ledger_path) if ledger_path.is_file() else "",
    }
    start_hashes = {"v15ReportSha256": report_sha_start, "outerSummarySha256": outer_sha_start,
                    "outerLedgerSha256": ledger_sha_start}
    _require(failures, "source-set", "source-end", "sourceHashes", source_end, source_start)
    _require(failures, "source-set", "source-end", "reportHashes", end_hashes, start_hashes)
    _require(failures, "source-set", "source-end", "outerFingerprints", fingerprints_end, fingerprints_start)
    provenance = {
        "start": {**start_hashes, "sourceHashes": source_start, "outerFingerprints": fingerprints_start},
        "end": {**end_hashes, "sourceHashes": source_end, "outerFingerprints": fingerprints_end},
        "outerFingerprintCount": len(fingerprints_start),
        "outerFingerprintSetSha256": sha256_bytes(json.dumps(fingerprints_start, sort_keys=True, separators=(",", ":")).encode()),
    }
    return _finalize(expected_input=expected_input, failures=failures, partial=partial,
                     provenance=provenance, directory_counts=directory_counts, counters=counters,
                     selected_count=len(selected), files=output_files, target_keys=target_keys, native=native)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join([
        "# Streaming marker17 body corpus gate", "",
        f"- Status: `{report['status']}`; publication eligible: `{str(report['publicationEligible']).lower()}`.",
        f"- Input set: `{report['inputSetSha256']}`.",
        f"- Files: {summary['filesSucceeded']:,} succeeded / {summary['filesFailed']:,} failed / {summary['filesSelected']:,} selected.",
        f"- Directory: {summary['referencesValidated']:,} references / {summary['bytesValidated']:,} bytes physically revalidated.",
        f"- Supported bodies: {summary['supportedReferences']:,} references / {summary['supportedBytes']:,} bytes; unsupported opaque: {summary['unsupportedOpaqueReferences']:,}.",
        f"- Failures: {summary['failed']:,}; unsupported: {summary['unsupported']:,}.", "",
        "Bodies are structurally framed only. Native final-cursor behavior, runtime receipt, field meaning, object population, and game semantics remain unresolved.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--outer-summary", type=Path)
    parser.add_argument("--outer-ledger", type=Path)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--input-set-sha256", dest="expected_input_set_sha256", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()
    if args.max_files is not None and (args.output_json is None or args.output_md is None):
        parser.error("--max-files requires explicit --output-json and --output-md; partial runs cannot overwrite latest reports")
    root = args.repo_root.resolve()
    result = sweep(
        repo_root=root,
        report_path=args.report or root / "reports/animestudio/streaming_root_subgraphs_latest.json",
        outer_summary_path=args.outer_summary or root / "reports/animestudio/vfs_understanding_latest.json",
        ledger_path=args.outer_ledger or root / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz",
        expected_input_set_sha256=args.expected_input_set_sha256,
        game_root=args.game_root, max_files=args.max_files,
    )
    output_json = args.output_json or root / "reports/animestudio/streaming_marker17_bodies_latest.json"
    output_md = args.output_md or root / "reports/animestudio/streaming_marker17_bodies_latest.md"
    corpus._atomic_write_text(output_json, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    corpus._atomic_write_text(output_md, render_markdown(result))
    print(json.dumps({"status": result["status"], "publicationEligible": result["publicationEligible"], **result["summary"]}, indent=2))
    if result["failures"]:
        print(json.dumps(result["failures"][0], ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
