"""Join a complete v3 SkillData target-set capture to current static profiles.

The runtime receipt chooses the terminal and authenticates the direct field
cursors.  Whole-record framing is promoted only where the independently
native-validated ActionGroup reader and top-level continuation reach those
same cursors.  This says nothing about gameplay branch selection.

The overlay composes each reviewed live field vector with that source's
native-gated whole-ActionGroup static profile and exact fields through 42.
Applied by the full authenticated SkillData sweep, it promotes every formerly
ambiguous target-set source to a whole stored-schema exact row, leaving no
terminal-ambiguous row in that input set; the singleton positive control
stays under its separate verifier.  Unsupported action children in other
files remain partial.

Example of the boundary: Purrche's base combo ability-range source was read
even on a Potential-3+ save.  Its exact-source replay closes the authored
timeline and fields through 42, and the live cursor selects the earlier
terminal directly after field 42.  Authored ``IfElseAction`` bytes in the
parent projectile-hit skill place that source in the fail branch of
``potential_3 >= 1`` (``buff_if_else_action_receipt``,
``buff_compare_float_action_receipt``), yet deserializing it does not show
that gameplay took the fail branch, since preloading remains possible, and the
outer provider and cache-selection path is not source-bound by the receipt.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack import skill_cursor_receipt
from scripts.game_data.memorypack.corpus_gate import _fail, _fingerprint
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS


VERIFIED_CAPTURE_TARGET_SET_EXACT = "verified-whole-schema-exact-capture-target-set"
_PROVENANCE_INPUTS = (
    "receipt", "corpusReport", "nativeContext", "verifier",
    "captureTargetSetContract", "captureTargetSetVerifier",
)


def _recorded_input(value: Any, *, label: str,
                    expected_path: Path | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("skill-target-set-input-provenance-missing", source=label,
              expected="path, length, SHA-256", actual=type(value).__name__)
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        _fail("skill-target-set-input-path-invalid", source=label,
              expected="absolute path", actual=raw_path)
    path = Path(raw_path)
    if not path.is_absolute() or (expected_path is not None and path.resolve() != expected_path.resolve()):
        _fail("skill-target-set-input-path-mismatch", source=label,
              expected=str(expected_path.resolve()) if expected_path is not None else "absolute path",
              actual=raw_path)
    actual = _fingerprint(path)
    recorded = {key: value.get(key) for key in ("path", "length", "sha256")}
    if recorded != actual:
        _fail("skill-target-set-input-drift", source=label,
              expected=recorded, actual=actual)
    return actual


def _field_range(value: Any, *, index: int, name: str, source: str) -> tuple[int, int]:
    if not isinstance(value, Mapping) or value.get("fieldIndex") != index or value.get("fieldName") != name:
        _fail("skill-target-set-field-identity-drift", source=source,
              expected={"fieldIndex": index, "fieldName": name}, actual=value)
    start, end = value.get("start"), value.get("end")
    if type(start) is not int or type(end) is not int or end <= start:
        _fail("skill-target-set-field-range-invalid", source=source,
              expected="positive integer range", actual={"start": start, "end": end})
    return start, end


def _offset(value: Any, *, source: str) -> int:
    if not isinstance(value, str):
        _fail("skill-target-set-candidate-offset-invalid", source=source,
              expected="integer string", actual=value)
    try:
        return int(value, 0)
    except ValueError:
        _fail("skill-target-set-candidate-offset-invalid", source=source,
              expected="integer string", actual=value)


def _static_fields(row: Mapping[str, Any], runtime_field_zero_end: int,
                   terminal_start: int, *, source: str) -> tuple[list[Mapping[str, Any]], str]:
    """Return exact fields 0..42 only when field 0 has a complete reader."""
    profile = row.get("emptyActionGroupProfile")
    if isinstance(profile, Mapping) and profile.get("status") in (
        "exact-through-field-42", "verified-exact-through-field-42"
    ):
        fields = profile.get("namedFields")
        if (runtime_field_zero_end != 10 or profile.get("parserCursor") != terminal_start
                or not isinstance(fields, list) or len(fields) != 43):
            _fail("skill-target-set-empty-profile-drift", source=source,
                  expected="empty ActionGroup and exact fields 0..42 to terminal",
                  actual={"fieldZeroEnd": runtime_field_zero_end,
                          "profileCursor": profile.get("parserCursor"),
                          "fieldCount": len(fields) if isinstance(fields, list) else None})
        return fields, "emptyActionGroupProfile"

    for key, expected_status in (
        ("timelineSharedSequenceProfile", "exact-first-timeline-shared-sequence-record"),
        ("passiveSharedSequenceProfile", "exact-passive-shared-sequence-list"),
    ):
        profile = row.get(key)
        if not isinstance(profile, Mapping) or profile.get("wholeActionGroupDataExact") is not True:
            continue
        continuation = profile.get("topLevelContinuation")
        fields = continuation.get("namedFields") if isinstance(continuation, Mapping) else None
        if (profile.get("status") != expected_status
                or profile.get("parserCursor") != runtime_field_zero_end
                or not isinstance(continuation, Mapping)
                or continuation.get("status") != "exact-through-field-42"
                or continuation.get("parserCursor") != terminal_start
                or not isinstance(fields, list) or len(fields) != 43):
            _fail("skill-target-set-static-profile-drift", source=source,
                  expected="exact ActionGroup and exact fields 0..42 to terminal",
                  actual={"profile": key, "status": profile.get("status"),
                          "fieldZeroEnd": runtime_field_zero_end,
                          "profileCursor": profile.get("parserCursor"),
                          "continuationStatus": continuation.get("status")
                          if isinstance(continuation, Mapping) else None,
                          "continuationCursor": continuation.get("parserCursor")
                          if isinstance(continuation, Mapping) else None})
        spans = profile.get("namedRanges")
        if not isinstance(spans, list) or not spans:
            _fail("skill-target-set-action-spans-missing", source=source,
                  expected="contiguous named ActionGroup ranges", actual=spans)
        cursor = 0
        for index, span in enumerate(spans):
            start = span.get("start") if isinstance(span, Mapping) else None
            end = span.get("end") if isinstance(span, Mapping) else None
            if (not isinstance(span, Mapping) or type(start) is not int or type(end) is not int
                    or start != cursor or end <= start or end > runtime_field_zero_end
                    or not isinstance(span.get("name"), str)):
                _fail("skill-target-set-action-span-drift", source=source, offset=index,
                      expected={"start": cursor, "endAtMost": runtime_field_zero_end}, actual=span)
            cursor = end
        if cursor != runtime_field_zero_end:
            _fail("skill-target-set-action-cursor-drift", source=source,
                  expected=runtime_field_zero_end, actual=cursor)
        return fields, key
    _fail("skill-target-set-static-profile-missing", source=source,
          expected="exact empty ActionGroup or full timeline/passive ActionGroup reader",
          actual={key: row.get(key, {}).get("status")
                  for key in ("emptyActionGroupProfile", "timelineSharedSequenceProfile",
                              "passiveSharedSequenceProfile")
                  if isinstance(row.get(key), Mapping)})


def _validate_join(row: dict[str, Any], target: Mapping[str, Any],
                   observation: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], str]:
    source = str(target["virtualPath"])
    names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    runtime = observation.get("runtimeFieldRanges")
    if not isinstance(runtime, list) or len(runtime) != len(names):
        _fail("skill-target-set-runtime-fields-missing", source=source,
              expected=len(names), actual=len(runtime) if isinstance(runtime, list) else None)
    cursor = 1
    for index, name in enumerate(names):
        start, end = _field_range(runtime[index], index=index, name=name,
                                  source=f"{source}:runtime field {index}")
        if start != cursor:
            _fail("skill-target-set-runtime-cursor-gap", source=source,
                  offset=index, expected=cursor, actual=start)
        cursor = end
    terminal_start = runtime[43]["start"]
    hard_limit = row["length"]
    if (cursor != hard_limit or observation.get("boundaryClass") != "exact-closed"
            or observation.get("hardLimit") != hard_limit
            or observation.get("parserCursor") != hard_limit):
        _fail("skill-target-set-runtime-not-closed", source=source,
              expected={"boundaryClass": "exact-closed", "end": hard_limit},
              actual={"boundaryClass": observation.get("boundaryClass"),
                      "hardLimit": observation.get("hardLimit"),
                      "parserCursor": observation.get("parserCursor"), "fieldEnd": cursor})
    static, key = _static_fields(row, runtime[0]["end"], terminal_start, source=source)
    for index, field in enumerate(static):
        start, end = _field_range(field, index=index, name=names[index],
                                  source=f"{source}:static field {index}")
        if (start, end) != (runtime[index]["start"], runtime[index]["end"]):
            _fail("skill-target-set-static-runtime-drift", source=source, offset=index,
                  expected={"start": runtime[index]["start"], "end": runtime[index]["end"]},
                  actual={"start": start, "end": end})
    selected_terminal = target.get("selectedTerminal")
    expected_terminal = {"start": terminal_start, "end": hard_limit,
                         "encoding": "one-member-wrapper", "framerCandidateCount": 2}
    if selected_terminal != expected_terminal or observation.get("candidate") != expected_terminal:
        _fail("skill-target-set-terminal-witness-drift", source=source,
              expected=expected_terminal,
              actual={"target": selected_terminal, "observation": observation.get("candidate")})
    checkpoints = target.get("actionGroupCheckpoints")
    if checkpoints != observation.get("actionGroupCheckpoints"):
        _fail("skill-target-set-action-checkpoints-drift", source=source,
              expected=observation.get("actionGroupCheckpoints"), actual=checkpoints)
    if not isinstance(checkpoints, list) or len(checkpoints) != 2:
        _fail("skill-target-set-action-checkpoints-missing", source=source,
              expected="two ordered child-list cursors", actual=checkpoints)
    # The strict receipt verifier already authenticates the two checkpoints.
    # Here the second child must also join the static full field-0 reader.
    if checkpoints[-1].get("cursorAfter") != runtime[0]["end"]:
        _fail("skill-target-set-action-checkpoint-cursor-drift", source=source,
              expected=runtime[0]["end"], actual=checkpoints[-1])

    framing = row.get("framing")
    candidates = framing.get("candidates") if isinstance(framing, Mapping) else None
    alternatives = observation.get("candidateAlternatives")
    coverage = row.get("candidateCoverage")
    if (not isinstance(candidates, list) or len(candidates) != 2
            or not isinstance(alternatives, list) or len(alternatives) != 2
            or not isinstance(coverage, list) or len(coverage) != 2):
        _fail("skill-target-set-candidate-pair-missing", source=source,
              expected="two static and runtime candidates", actual={
                  "static": len(candidates) if isinstance(candidates, list) else None,
                  "runtime": len(alternatives) if isinstance(alternatives, list) else None})
    expected_kinds = [item[3] for item in skill_cursor_receipt.TERMINAL_FIELD_CONTRACT]
    for index, (candidate, alternative, encoding, start) in enumerate((
        (candidates[0], alternatives[0], "one-member-wrapper", terminal_start),
        (candidates[1], alternatives[1], "counted", terminal_start + 1),
    )):
        if not isinstance(candidate, Mapping) or not isinstance(alternative, Mapping):
            _fail("skill-target-set-candidate-invalid", source=source,
                  expected="candidate objects", actual=index)
        members = candidate.get("members")
        actual = (candidate.get("encoding"), _offset(candidate.get("startOffset"), source=source),
                  _offset(candidate.get("endOffset"), source=source), alternative.get("encoding"),
                  alternative.get("start"), alternative.get("end"), alternative.get("selected"),
                  [member.get("kind") for member in members]
                  if isinstance(members, list) and all(isinstance(member, Mapping) for member in members)
                  else None)
        expected = (encoding, start, hard_limit, encoding, start, hard_limit,
                    index == 0, expected_kinds)
        if actual != expected:
            _fail("skill-target-set-candidate-drift", source=source,
                  expected=expected, actual=actual)
        if index == 0:
            for field_index, member in enumerate(members, 43):
                span = member.get("range")
                if (not isinstance(span, Mapping) or
                        (span.get("start"), span.get("end")) !=
                        (runtime[field_index]["start"], runtime[field_index]["end"])):
                    _fail("skill-target-set-terminal-range-drift", source=source,
                          offset=field_index, expected=runtime[field_index], actual=span)
    return static, key


def _promote(row: dict[str, Any], target: Mapping[str, Any],
             static: list[Mapping[str, Any]], profile_key: str) -> None:
    runtime = target["runtimeFieldRanges"]
    names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    terminal_start, hard_limit = runtime[43]["start"], row["length"]
    selected, rejected = row["framing"]["candidates"]
    selected.update(selected=True, boundaryClass="selected-terminal",
                    semanticFieldNamesStatus="named-by-authenticated-reader-alignment")
    rejected.update(selected=False, boundaryClass="rejected-alternative")
    for index, item in enumerate(row["candidateCoverage"]):
        item["selected"] = index == 0
    row["byteRanges"] = [
        {"start": 0, "end": 1, "kind": "SkillData.member-count"},
        *[{**field, "evidence": "native-static-profile-matched-exact-runtime-target-set"}
          for field in static],
        *[{"fieldIndex": index, "fieldName": names[index],
           "start": runtime[index]["start"], "end": runtime[index]["end"],
           "kind": selected["members"][index - 43]["kind"],
           "evidence": "exact-runtime-target-set-terminal"}
          for index in range(43, 48)],
    ]
    row["opaqueByteRanges"] = []
    row["parserCursor"] = hard_limit
    row["boundaryContext"]["parserCursor"] = hard_limit
    row["boundaryClass"] = "exact-closed"
    row["coverageStatus"] = VERIFIED_CAPTURE_TARGET_SET_EXACT
    row["wholeSchemaExact"] = True
    row["framing"]["wholeSchemaExact"] = True
    row["terminalSelection"] = {
        "status": "verified-native-reader-alignment", "candidateIndex": 0,
        "encoding": "one-member-wrapper", "start": terminal_start, "end": hard_limit,
        "fieldStartIndex": 43, "fieldEndIndex": 47,
        "namedFields": [item[1] for item in skill_cursor_receipt.TERMINAL_FIELD_CONTRACT],
        "wholeSchemaExact": True,
        "evidenceBoundary": "Exact stored-byte framing for this logical source: the native-gated static ActionGroup and top-level fields match the executed reader through EOF.",
    }
    profile = row[profile_key]
    if profile_key == "emptyActionGroupProfile":
        row[profile_key] = {**profile, "status": "verified-exact-through-field-42"}
    else:
        row[profile_key] = {
            **profile,
            "topLevelContinuation": {**profile["topLevelContinuation"],
                                     "status": "verified-exact-through-field-42"},
        }


def apply_verified_capture_target_set(
    rows: list[dict[str, Any]], *, verification_path: Path,
    expected_input_set_sha256: str, identity_set_sha256: str,
    build_fingerprints: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Strictly replay the v3 set and promote only exact current row joins."""
    # The native-context verifier imports this corpus module. Defer it until
    # the corpus has finished importing, then replay it without substitutes.
    from scripts.game_data.memorypack import skill_cursor_capture_target_set
    from scripts.game_data.memorypack.skill_cursor_target_overlay import VERIFIED_CAPTURE_TARGET_EXACT

    verification_fingerprint = _fingerprint(verification_path)
    try:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("skill-target-set-verification-unreadable", source=str(verification_path),
              expected="valid JSON object", actual=str(exc))
    summary = verification.get("summary") if isinstance(verification, Mapping) else None
    targets = verification.get("targets") if isinstance(verification, Mapping) else None
    if (not isinstance(verification, Mapping)
            or verification.get("schema") != skill_cursor_capture_target_set.OUTPUT_SCHEMA
            or verification.get("status") != "validated"
            or verification.get("coverageStatus") != "complete"
            or verification.get("publicationEligible") is False
            or not isinstance(summary, Mapping)
            or summary.get("globalFailureReasons") != []
            or not isinstance(targets, list) or not targets):
        _fail("skill-target-set-verification-incomplete", source=str(verification_path),
              expected="strict validated complete v3 verification",
              actual={"schema": verification.get("schema"),
                      "status": verification.get("status"),
                      "coverageStatus": verification.get("coverageStatus")}
              if isinstance(verification, Mapping) else type(verification).__name__)
    if verification.get("inputSetSha256") != expected_input_set_sha256.upper():
        _fail("skill-target-set-input-set-drift", source=str(verification_path),
              expected=expected_input_set_sha256.upper(), actual=verification.get("inputSetSha256"))
    provenance = verification.get("provenance")
    if not isinstance(provenance, Mapping):
        _fail("skill-target-set-provenance-missing", source=str(verification_path),
              expected=list(_PROVENANCE_INPUTS), actual=type(provenance).__name__)
    expected_paths = {
        "verifier": Path(skill_cursor_receipt.__file__),
        "captureTargetSetContract": skill_cursor_capture_target_set.DEFAULT_TARGET_CONTRACT,
        "captureTargetSetVerifier": Path(skill_cursor_capture_target_set.__file__),
    }
    inputs = {name: _recorded_input(provenance.get(name), label=name,
                                    expected_path=expected_paths.get(name))
              for name in _PROVENANCE_INPUTS}
    if provenance["corpusReport"].get("identitySetSha256") != identity_set_sha256:
        _fail("skill-target-set-corpus-identity-drift", source=str(verification_path),
              expected=identity_set_sha256,
              actual=provenance["corpusReport"].get("identitySetSha256"))
    installed: dict[str, str] = {}
    for item in build_fingerprints:
        if not isinstance(item, Mapping):
            _fail("skill-target-set-native-fingerprint-invalid", source=str(verification_path),
                  expected="fingerprint object", actual=type(item).__name__)
        name = Path(str(item.get("path"))).name.casefold()
        digest = str(item.get("sha256", "")).upper()
        if name in installed and installed[name] != digest:
            _fail("skill-target-set-native-fingerprint-conflict", source=str(verification_path),
                  expected=installed[name], actual=digest)
        installed[name] = digest
    native = {"gameAssemblySha256": installed.get("gameassembly.dll"),
              "metadataSha256": installed.get("global-metadata.dat")}
    if None in native.values() or verification.get("nativeInputs") != native:
        _fail("skill-target-set-native-input-drift", source=str(verification_path),
              expected=native, actual=verification.get("nativeInputs"))
    receipt_path = Path(inputs["receipt"]["path"])
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (not isinstance(receipt, Mapping) or receipt.get("captureComplete") is not True
                or receipt.get("pendingRecords") != 0
                or receipt.get("progressPublicationFailures") != 0):
            _fail("skill-target-set-capture-transport-incomplete", source=str(receipt_path),
                  expected={"captureComplete": True, "pendingRecords": 0,
                            "progressPublicationFailures": 0},
                  actual={key: receipt.get(key) for key in
                          ("captureComplete", "pendingRecords", "progressPublicationFailures")}
                  if isinstance(receipt, Mapping) else type(receipt).__name__)
        replayed = skill_cursor_capture_target_set.verify_capture_target_set(
            receipt, receipt_path=receipt_path,
            receipt_sha256=inputs["receipt"]["sha256"],
            corpus_path=Path(inputs["corpusReport"]["path"]),
            native_context_path=Path(inputs["nativeContext"]["path"]),
            target_contract_path=Path(inputs["captureTargetSetContract"]["path"]),
            diagnose_incomplete=False,
        )
    except (OSError, UnicodeError, json.JSONDecodeError,
            skill_cursor_receipt.ReceiptVerificationError,
            skill_cursor_capture_target_set.context_audit.native.NativeCursorContextError) as exc:
        _fail("skill-target-set-verification-replay-error", source=str(verification_path),
              expected="exact strict verifier replay", actual=str(exc))
    if replayed != verification:
        _fail("skill-target-set-verification-replay-mismatch", source=str(verification_path),
              expected="exact strict verifier replay", actual="report differs")
    verified_rows = verification.get("rows")
    if not isinstance(verified_rows, list):
        _fail("skill-target-set-observations-invalid", source=str(verification_path),
              expected="observation list", actual=type(verified_rows).__name__)
    if (summary.get("observationCount") != len(targets)
            or len(verified_rows) != len(targets)
            or summary.get("unresolvedExactClosed") != summary.get("unresolvedTargets")
            or summary.get("positiveControlsExactClosed") != summary.get("positiveControls")):
        _fail("skill-target-set-target-coverage-drift", source=str(verification_path),
              expected="one exact clean observation per target", actual=summary)
    by_path = {row.get("virtualPath"): row for row in rows}
    if len(by_path) != len(rows):
        _fail("skill-target-set-current-row-duplicates", source=str(verification_path),
              expected="unique logical paths", actual=len(rows) - len(by_path))
    seen: set[str] = set()
    seen_observations: set[int] = set()
    roles = {"unresolved": 0, "positiveControl": 0}
    plans: list[tuple[dict[str, Any], Mapping[str, Any], list[Mapping[str, Any]], str]] = []
    retained_control = 0
    for target in targets:
        if not isinstance(target, Mapping):
            _fail("skill-target-set-target-invalid", source=str(verification_path),
                  expected="target object", actual=type(target).__name__)
        path, length, digest = (target.get("virtualPath"), target.get("sourceLength"),
                                target.get("logicalSha256"))
        if (not isinstance(path, str) or path in seen or type(length) is not int
                or not isinstance(digest, str) or path not in by_path):
            _fail("skill-target-set-target-join-invalid", source=str(verification_path),
                  expected="unique current logical path", actual={"path": path, "length": length})
        seen.add(path)
        role = target.get("role")
        if role not in roles:
            _fail("skill-target-set-role-invalid", source=path,
                  expected=list(roles), actual=role)
        roles[role] += 1
        row = by_path[path]
        if row.get("length") != length or row.get("logicalSha256") != digest:
            _fail("skill-target-set-current-source-drift", source=path,
                  expected={"length": length, "logicalSha256": digest},
                  actual={"length": row.get("length"),
                          "logicalSha256": row.get("logicalSha256")})
        indices = target.get("observationIndices")
        if (target.get("status") != "observed-exact-closed"
                or target.get("cursorEvidenceStatus") != "exact-closed"
                or target.get("captureHealth") != "clean"
                or target.get("observationCount") != 1
                or target.get("duplicateConflicts") != 0
                or target.get("unverifiedPairs") != 0
                or not isinstance(indices, list) or len(indices) != 1
                or type(indices[0]) is not int or not 0 <= indices[0] < len(verified_rows)
                or indices[0] in seen_observations):
            _fail("skill-target-set-target-not-clean", source=path,
                  expected="one clean exact observation", actual=target)
        seen_observations.add(indices[0])
        observation = verified_rows[indices[0]]
        if (not isinstance(observation, Mapping)
                or (observation.get("logicalPath"), observation.get("logicalSha256"),
                    observation.get("hardLimit")) != (path, digest, length)
                or target.get("runtimeFieldRanges") != observation.get("runtimeFieldRanges")):
            _fail("skill-target-set-observation-join-drift", source=path,
                  expected={"path": path, "length": length, "digest": digest},
                  actual=observation if not isinstance(observation, Mapping) else
                  {key: observation.get(key) for key in ("logicalPath", "logicalSha256", "hardLimit")})
        static, key = _validate_join(row, target, observation)
        if target.get("role") == "positiveControl":
            if (row.get("coverageStatus") != VERIFIED_CAPTURE_TARGET_EXACT
                    or row.get("boundaryClass") != "exact-closed"
                    or row.get("wholeSchemaExact") is not True
                    or row.get("terminalSelection", {}).get("start") != target["selectedTerminal"]["start"]
                    or row.get("terminalSelection", {}).get("end") != length):
                _fail("skill-target-set-existing-exact-conflict", source=path,
                      expected="matching prior singleton positive control", actual=row.get("terminalSelection"))
            retained_control += 1
            continue
        if (row.get("boundaryClass") != "ambiguous"
                or row.get("coverageStatus") != "ambiguous-disjoint-independent-ranges"
                or row.get("wholeSchemaExact") is not False
                or not isinstance(row.get("boundaryContext"), dict)):
            _fail("skill-target-set-current-row-status-drift", source=path,
                  expected="unpromoted ambiguous row", actual={
                      key: row.get(key) for key in ("boundaryClass", "coverageStatus", "wholeSchemaExact")})
        plans.append((row, target, static, key))
    if (len(seen_observations) != len(verified_rows)
            or roles["unresolved"] != summary.get("unresolvedTargets")
            or roles["positiveControl"] != summary.get("positiveControls")
            or retained_control != roles["positiveControl"]
            or len(plans) != roles["unresolved"]):
        _fail("skill-target-set-role-accounting-drift", source=str(verification_path),
              expected={"observations": len(verified_rows),
                        "unresolved": summary.get("unresolvedTargets"),
                        "positiveControls": summary.get("positiveControls")},
              actual={"observations": len(seen_observations), **roles,
                      "retainedPositiveControls": retained_control,
                      "promotions": len(plans)})
    for row, target, static, key in plans:
        _promote(row, target, static, key)
    return {**verification_fingerprint,
            "inputs": [inputs[name] for name in _PROVENANCE_INPUTS],
            "targets": len(targets), "promoted": len(plans),
            "retainedPositiveControls": retained_control}
