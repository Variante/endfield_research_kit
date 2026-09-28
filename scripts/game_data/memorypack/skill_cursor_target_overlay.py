"""Apply one replayed SkillData cursor capture to its exact logical source.

The capture-target verifier authenticates the executed cursor.  This module
joins that cursor to the maintained static field-0..42 profile for the one
hash-pinned source, without changing the older corpus-wide receipt rule.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack import skill_cursor_capture_target, skill_cursor_receipt
from scripts.game_data.memorypack.corpus_gate import _fail, _fingerprint
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS


VERIFIED_CAPTURE_TARGET_EXACT = "verified-whole-schema-exact-capture-target"
_PROVENANCE_INPUTS = (
    "receipt", "corpusReport", "nativeContext", "verifier",
    "captureTargetContract", "captureTargetVerifier",
)


def _recorded_input(value: Any, *, label: str, expected_path: Path | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("skill-capture-input-provenance-missing", source=label,
              expected="path, length, SHA-256", actual=type(value).__name__)
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        _fail("skill-capture-input-path-invalid", source=label, expected="absolute path", actual=raw_path)
    path = Path(raw_path)
    if not path.is_absolute() or (expected_path is not None and path.resolve() != expected_path.resolve()):
        _fail("skill-capture-input-path-mismatch", source=label,
              expected=str(expected_path.resolve()) if expected_path is not None else "absolute path",
              actual=raw_path)
    actual = _fingerprint(path)
    recorded = {key: value.get(key) for key in ("path", "length", "sha256")}
    if recorded != actual:
        _fail("skill-capture-input-drift", source=label, expected=recorded, actual=actual)
    return actual


def _field_range(value: Any, *, index: int, name: str, source: str) -> tuple[int, int]:
    if not isinstance(value, Mapping) or value.get("fieldIndex") != index or value.get("fieldName") != name:
        _fail("skill-capture-field-identity-drift", source=source,
              expected={"fieldIndex": index, "fieldName": name},
              actual={key: value.get(key) for key in ("fieldIndex", "fieldName")}
              if isinstance(value, Mapping) else type(value).__name__)
    start, end = value.get("start"), value.get("end")
    if type(start) is not int or type(end) is not int or end <= start:
        _fail("skill-capture-field-range-invalid", source=source,
              expected="positive integer range", actual={"start": start, "end": end})
    return start, end


def _offset(value: Any, *, source: str) -> int:
    if not isinstance(value, str):
        _fail("skill-capture-candidate-offset-invalid", source=source, expected="integer string", actual=value)
    try:
        return int(value, 0)
    except ValueError:
        _fail("skill-capture-candidate-offset-invalid", source=source, expected="integer string", actual=value)


def _target_selection(row: dict[str, Any], observation: Mapping[str, Any], *, source: str) -> None:
    names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    runtime = observation.get("runtimeFieldRanges")
    profile = row.get("emptyActionGroupProfile")
    static = profile.get("namedFields") if isinstance(profile, Mapping) else None
    if (not isinstance(runtime, list) or len(runtime) != len(names)
            or not isinstance(static, list) or len(static) != 43
            or profile.get("status") != "exact-through-field-42"):
        _fail("skill-capture-field-profile-missing", source=source,
              expected="48 runtime ranges and exact static fields 0..42",
              actual={"runtimeCount": len(runtime) if isinstance(runtime, list) else None,
                      "staticCount": len(static) if isinstance(static, list) else None,
                      "profileStatus": profile.get("status") if isinstance(profile, Mapping) else None})
    cursor = 1
    for index, name in enumerate(names):
        start, end = _field_range(runtime[index], index=index, name=name,
                                  source=f"{source}:runtime field {index}")
        if start != cursor:
            _fail("skill-capture-runtime-cursor-gap", source=source, offset=index,
                  expected=cursor, actual=start)
        cursor = end
        if index <= 42:
            static_range = _field_range(static[index], index=index, name=name,
                                        source=f"{source}:static field {index}")
            if static_range != (start, end):
                _fail("skill-capture-static-runtime-drift", source=source, offset=index,
                      expected={"start": start, "end": end},
                      actual={"start": static_range[0], "end": static_range[1]})
    hard_limit = row["length"]
    if cursor != hard_limit or profile.get("parserCursor") != runtime[42]["end"]:
        _fail("skill-capture-profile-closure-drift", source=source,
              expected={"runtimeEnd": hard_limit, "staticEnd": runtime[42]["end"]},
              actual={"runtimeEnd": cursor, "staticEnd": profile.get("parserCursor")})
    if (observation.get("boundaryClass") != "exact-closed"
            or observation.get("hardLimit") != hard_limit):
        _fail("skill-capture-observation-not-closed", source=source,
              expected={"boundaryClass": "exact-closed", "hardLimit": hard_limit},
              actual={"boundaryClass": observation.get("boundaryClass"),
                      "hardLimit": observation.get("hardLimit")})

    framing = row.get("framing")
    candidates = framing.get("candidates") if isinstance(framing, Mapping) else None
    alternatives = observation.get("candidateAlternatives")
    coverage = row.get("candidateCoverage")
    context = row.get("boundaryContext")
    if (not isinstance(candidates, list) or len(candidates) != 2
            or not isinstance(alternatives, list) or len(alternatives) != 2
            or not isinstance(coverage, list) or len(coverage) != 2
            or not all(isinstance(item, dict) for item in coverage)
            or not isinstance(context, dict)):
        _fail("skill-capture-terminal-candidate-count", source=source,
              expected="two corpus candidates, two runtime alternatives, and mutable row context",
              actual={"corpus": len(candidates) if isinstance(candidates, list) else None,
                      "runtime": len(alternatives) if isinstance(alternatives, list) else None,
                      "coverage": len(coverage) if isinstance(coverage, list) else None})
    terminal_start = runtime[43]["start"]
    expected_kinds = [item[3] for item in skill_cursor_receipt.TERMINAL_FIELD_CONTRACT]
    for index, (candidate, alternative, encoding, start) in enumerate((
        (candidates[0], alternatives[0], "one-member-wrapper", terminal_start),
        (candidates[1], alternatives[1], "counted", terminal_start + 1),
    )):
        if not isinstance(candidate, Mapping) or not isinstance(alternative, Mapping):
            _fail("skill-capture-terminal-candidate-invalid", source=source,
                  expected="candidate objects", actual=index)
        members = candidate.get("members")
        actual = {
            "corpusEncoding": candidate.get("encoding"),
            "corpusStart": _offset(candidate.get("startOffset"), source=source),
            "corpusEnd": _offset(candidate.get("endOffset"), source=source),
            "runtimeEncoding": alternative.get("encoding"),
            "runtimeStart": alternative.get("start"),
            "runtimeEnd": alternative.get("end"),
            "runtimeSelected": alternative.get("selected"),
            "memberKinds": [member.get("kind") for member in members]
                if isinstance(members, list) and all(isinstance(member, Mapping) for member in members)
                else None,
        }
        expected = {
            "corpusEncoding": encoding, "corpusStart": start, "corpusEnd": hard_limit,
            "runtimeEncoding": encoding, "runtimeStart": start, "runtimeEnd": hard_limit,
            "runtimeSelected": index == 0, "memberKinds": expected_kinds,
        }
        if actual != expected:
            _fail("skill-capture-terminal-selection-drift", source=source,
                  expected=expected, actual=actual)
        if index == 0:
            for field_index, member in enumerate(members, 43):
                span = member.get("range")
                observed = runtime[field_index]
                if (not isinstance(span, Mapping)
                        or (span.get("start"), span.get("end")) !=
                        (observed["start"], observed["end"])):
                    _fail("skill-capture-terminal-member-range-drift", source=source,
                          offset=field_index,
                          expected={"start": observed["start"], "end": observed["end"]},
                          actual=span)

    # No row changes precede the final field and candidate checks.
    selected, rejected = candidates
    selected["selected"] = True
    selected["boundaryClass"] = "selected-terminal"
    selected["semanticFieldNamesStatus"] = "named-by-authenticated-reader-alignment"
    rejected["selected"] = False
    rejected["boundaryClass"] = "rejected-alternative"
    for index, item in enumerate(coverage):
        item["selected"] = index == 0
    row["byteRanges"] = [
        {"start": 0, "end": 1, "kind": "SkillData.member-count"},
        *[{**field, "evidence": "static-profile-matched-exact-runtime-target"} for field in static],
        *[{
            "fieldIndex": field_index,
            "fieldName": names[field_index],
            "start": runtime[field_index]["start"],
            "end": runtime[field_index]["end"],
            "kind": selected["members"][field_index - 43]["kind"],
            "evidence": "exact-runtime-target-terminal",
        } for field_index in range(43, 48)],
    ]
    row["opaqueByteRanges"] = []
    row["parserCursor"] = hard_limit
    context["parserCursor"] = hard_limit
    row["boundaryClass"] = "exact-closed"
    row["coverageStatus"] = VERIFIED_CAPTURE_TARGET_EXACT
    row["wholeSchemaExact"] = True
    framing["wholeSchemaExact"] = True
    row["terminalSelection"] = {
        "status": "verified-native-reader-alignment",
        "candidateIndex": 0, "encoding": "one-member-wrapper",
        "start": terminal_start, "end": hard_limit,
        "fieldStartIndex": 43, "fieldEndIndex": 47,
        "namedFields": [item[1] for item in skill_cursor_receipt.TERMINAL_FIELD_CONTRACT],
        "wholeSchemaExact": True,
        "evidenceBoundary": "Exact only for this path and logical SHA-256: static fields 0..42 match the executed cursor, and the selected terminal reaches EOF.",
    }
    row["emptyActionGroupProfile"] = {
        **profile, "status": "verified-exact-through-field-42",
        "evidenceBoundary": "Current static profile matches the executed cursor on this exact logical source.",
    }


def apply_verified_capture_target(
    rows: list[dict[str, Any]],
    *,
    verification_path: Path,
    expected_input_set_sha256: str,
    identity_set_sha256: str,
    build_fingerprints: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Replay the capture and promote only its reviewed source identity."""
    verification_fingerprint = _fingerprint(verification_path)
    try:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("skill-capture-verification-unreadable", source=str(verification_path),
              expected="valid JSON object", actual=str(exc))
    summary = verification.get("summary") if isinstance(verification, Mapping) else None
    if not isinstance(verification, Mapping) or (
        verification.get("schema") != skill_cursor_capture_target.OUTPUT_SCHEMA
        or verification.get("status") != "complete"
        or verification.get("verificationMode") != "capture-target"
        or not isinstance(summary, Mapping)
        or summary.get("failureReasons") != []
    ):
        _fail("skill-capture-verification-incomplete", source=str(verification_path),
              expected="complete capture-target verification without failed gates",
              actual={"schema": verification.get("schema"), "status": verification.get("status")}
              if isinstance(verification, Mapping) else type(verification).__name__)
    if verification.get("inputSetSha256") != expected_input_set_sha256.upper():
        _fail("skill-capture-input-set-drift", source=str(verification_path),
              expected=expected_input_set_sha256.upper(), actual=verification.get("inputSetSha256"))
    provenance = verification.get("provenance")
    if not isinstance(provenance, Mapping):
        _fail("skill-capture-provenance-missing", source=str(verification_path),
              expected=list(_PROVENANCE_INPUTS), actual=type(provenance).__name__)
    expected_paths = {
        "verifier": Path(skill_cursor_receipt.__file__),
        "captureTargetContract": skill_cursor_capture_target.DEFAULT_TARGET_CONTRACT,
        "captureTargetVerifier": Path(skill_cursor_capture_target.__file__),
    }
    inputs = {
        name: _recorded_input(provenance.get(name), label=name, expected_path=expected_paths.get(name))
        for name in _PROVENANCE_INPUTS
    }
    source_identity = provenance["corpusReport"].get("identitySetSha256")
    if source_identity != identity_set_sha256:
        _fail("skill-capture-corpus-identity-drift", source=str(verification_path),
              expected=identity_set_sha256, actual=source_identity)
    installed: dict[str, str] = {}
    for item in build_fingerprints:
        if not isinstance(item, Mapping):
            _fail("skill-capture-native-fingerprint-invalid", source=str(verification_path),
                  expected="fingerprint object", actual=type(item).__name__)
        name = Path(str(item.get("path"))).name.casefold()
        digest = str(item.get("sha256", "")).upper()
        if name in installed and installed[name] != digest:
            _fail("skill-capture-native-fingerprint-conflict", source=str(verification_path),
                  expected=installed[name], actual=digest)
        installed[name] = digest
    native = {
        "gameAssemblySha256": installed.get("gameassembly.dll"),
        "metadataSha256": installed.get("global-metadata.dat"),
    }
    if None in native.values() or verification.get("nativeInputs") != native:
        _fail("skill-capture-native-input-drift", source=str(verification_path),
              expected=native, actual=verification.get("nativeInputs"))
    receipt_path = Path(inputs["receipt"]["path"])
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, Mapping):
            _fail("skill-capture-receipt-invalid", source=str(receipt_path),
                  expected="JSON object", actual=type(receipt).__name__)
        replayed = skill_cursor_capture_target.verify_capture_target(
            receipt,
            receipt_path=receipt_path,
            receipt_sha256=inputs["receipt"]["sha256"],
            corpus_path=Path(inputs["corpusReport"]["path"]),
            native_context_path=Path(inputs["nativeContext"]["path"]),
            target_contract_path=Path(inputs["captureTargetContract"]["path"]),
        )
    except (OSError, UnicodeError, json.JSONDecodeError,
            skill_cursor_receipt.ReceiptVerificationError) as exc:
        _fail("skill-capture-verification-replay-error", source=str(verification_path),
              expected="exact verifier replay", actual=str(exc))
    if replayed != verification:
        _fail("skill-capture-verification-replay-mismatch", source=str(verification_path),
              expected="exact verifier replay", actual="report differs")
    target = verification.get("captureTarget")
    if not isinstance(target, Mapping):
        _fail("skill-capture-target-missing", source=str(verification_path),
              expected="one exact target", actual=type(target).__name__)
    path, length, digest = (target.get("logicalPath"), target.get("sourceLength"),
                            target.get("logicalSha256"))
    matching = [row for row in rows if row.get("virtualPath") == path]
    verified_rows = verification.get("rows")
    if not isinstance(verified_rows, list):
        _fail("skill-capture-observations-invalid", source=str(verification_path),
              expected="observation list", actual=type(verified_rows).__name__)
    observations = [item for item in verified_rows
                    if isinstance(item, Mapping) and item.get("logicalPath") == path
                    and item.get("logicalSha256") == digest and item.get("hardLimit") == length]
    if (len(matching) != 1 or len(observations) != 1
            or target.get("exactObservationCount") != 1
            or not isinstance(path, str) or type(length) is not int or not isinstance(digest, str)):
        _fail("skill-capture-target-selection-invalid", source=str(verification_path),
              expected="one row and one exact observation",
              actual={"corpusRows": len(matching), "observations": len(observations),
                      "recordedObservationCount": target.get("exactObservationCount")})
    row = matching[0]
    if (row.get("length") != length or row.get("logicalSha256") != digest
            or row.get("boundaryClass") != "ambiguous"
            or row.get("coverageStatus") != "ambiguous-disjoint-independent-ranges"):
        _fail("skill-capture-target-corpus-drift", source=path,
              expected={"length": length, "logicalSha256": digest,
                        "boundaryClass": "ambiguous"},
              actual={key: row.get(key) for key in
                      ("length", "logicalSha256", "boundaryClass", "coverageStatus")})
    _target_selection(row, observations[0], source=path)
    return {
        **verification_fingerprint,
        "inputs": [inputs[name] for name in _PROVENANCE_INPUTS],
        "target": {"virtualPath": path, "length": length, "logicalSha256": digest},
    }
