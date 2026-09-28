"""Verify a bounded multi-source SkillData cursor session source by source.

The v3 runtime receipt can observe any reviewed source in one session.  A
source that never loads is reported missing; a conflicting source is isolated
to that source.  Diagnostic mode can inspect retained rows from an incomplete
transport, but its output is never publication eligible.  This verifier does
not publish a whole-schema corpus claim.

The target set (``contracts/skill_cursor_capture_target_set.json``, gated
before launch by ``python -m
scripts.game_data.il2cpp.skill_cursor_target_set_context``) binds every
current terminal-ambiguous SkillData logical source plus the
already closed Purrche second-talent source as a positive control.  The
recorder admits each source by copied-byte hash, retains one full cursor
vector per identity, and counts identical repeats, conflicting repeats and
locally incomplete pairs separately; its atomic live progress
(:mod:`skill_cursor_target_set_progress`) is provisional.  Publication needs
a quiescent, loss-free receipt.  The strict mode replays the current native
and corpus gates, exact copied source bytes, field cursors, child checkpoints
and terminal EOF for each source independently.  A source never loaded during
play stays missing rather than borrowing another source's selection.

One earlier session lost callbacks during a bounded recorder-lock wait, and
its positive control ended with an incomplete pair; the strict verifier
rejected the globally incomplete receipt, and its diagnostic output stays
nonpublishable even though every retained row selected the one-member
terminal.  V3 callbacks wait on an SRW lock while worker drains stay
nonblocking.  The following session produced a complete, loss-free receipt:
every requested target and the positive control verified, each reading the
earlier one-member terminal, so that set needs no further capture.  A
top-level cursor never names a populated ActionGroup interior.

Workflow.  ``python -m scripts.game_data.il2cpp.skill_cursor_target_set_context
--preflight --capture-binding-batch`` prints the host binding;
``tools/EndfieldCapture/StartCapture.bat skilldata-cursor targeted
--skilldata-all-targets --no-pause`` (first with ``--preflight-only``) runs
the session; ``python -m
scripts.game_data.memorypack.skill_cursor_target_set_progress
<session>/skilldata-cursor/progress.json`` shows provisional coverage; this
module then verifies ``<session>/skilldata-cursor/receipt.json`` into
``reports/animestudio/skilldata_cursor_target_set_verification_latest.json``
(with ``--diagnose-incomplete``, into
``skilldata_cursor_target_set_diagnostic_latest.json``).  The verification
is what ``memorypack.skill_corpus --capture-target-set-verification`` replays.
Raw sessions stay under ``scratch/reverse_engineering/endfield_capture/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp import skill_cursor_target_set_context as context_audit
from scripts.game_data.memorypack import skill_cursor_receipt as receipt_verifier
from scripts.repo_paths import REPO_ROOT


OUTPUT_SCHEMA = "endfield.skillDataCursorTargetSetVerification.v1"
DIAGNOSTIC_OUTPUT_SCHEMA = "endfield.skillDataCursorTargetSetDiagnostic.v1"
RECEIPT_SCHEMA = "endfieldCapture.skillDataCursorCapture.v3"
DEFAULT_CORPUS = context_audit.DEFAULT_CORPUS
DEFAULT_NATIVE_CONTEXT = context_audit.DEFAULT_CONTEXT
DEFAULT_TARGET_CONTRACT = context_audit.TARGET_CONTRACT_PATH
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_target_set_verification_latest.json"
DEFAULT_DIAGNOSTIC_OUTPUT = (
    REPO_ROOT / "reports/animestudio/skilldata_cursor_target_set_diagnostic_latest.json"
)

LOSS_COUNTERS = (
    "lostObservations", "sourceIdentityHashFailure", "invalidReaderState",
    "unreadableReaderState", "unreadableSource", "truncatedSource",
    "cursorTransitionErrors", "unmatchedCalls", "incompletePairs",
)
OVERFLOW_COUNTERS = ("slotOverflow", "retainedRecordOverflow", "drainFailures")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise receipt_verifier.ReceiptVerificationError(message)


def _target_stats(receipt: Mapping[str, Any], target_sources: list[dict[str, Any]],
                  observed_counts: dict[str, int]) -> list[dict[str, Any]]:
    stats = receipt.get("targetStats")
    _require(isinstance(stats, list) and len(stats) == len(target_sources),
             "receipt.targetStats: expected one ordered entry per target source")
    result = []
    for index, (source, raw) in enumerate(zip(target_sources, stats)):
        _require(isinstance(raw, Mapping),
                 f"receipt.targetStats[{index}]: expected an object")
        _require((raw.get("sourceLength"), raw.get("sourceSha256")) ==
                 (source["sourceLength"], source["sourceSha256"]),
                 f"receipt.targetStats[{index}]: target identity/order differs")
        counters = {}
        for field in ("observationsPublished", "duplicateIdentical",
                      "duplicateConflicts", "unverifiedPairs"):
            value = raw.get(field)
            _require(type(value) is int and value >= 0,
                     f"receipt.targetStats[{index}].{field}: expected nonnegative integer")
            counters[field] = value
        digest = source["sourceSha256"]
        _require(counters["observationsPublished"] == observed_counts.get(digest, 0),
                 f"receipt.targetStats[{index}].observationsPublished: differs from rows")
        _require(counters["observationsPublished"] <= 1,
                 f"receipt.targetStats[{index}].observationsPublished: recorder retains at most one row")
        _require(counters["observationsPublished"] > 0 or
                 (counters["duplicateIdentical"] == 0 and
                  counters["duplicateConflicts"] == 0),
                 f"receipt.targetStats[{index}]: duplicate count without an observation")
        result.append({**source, **counters})
    return result


def _observation_signature(row: Mapping[str, Any]) -> str:
    """Compare complete repeated cursor vectors, excluding report-only labels."""
    return json.dumps({
        "fieldCursors": row.get("fieldCursors"),
        "actionGroupCheckpoints": row.get("actionGroupCheckpoints"),
        "runtimeFieldRanges": row.get("runtimeFieldRanges"),
        "candidate": row.get("candidate"),
        "parserCursor": row.get("parserCursor"),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _diagnostic_transport(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Describe the original failed transport without changing its receipt."""
    _require(receipt.get("captureComplete") is False,
             "diagnostic mode requires receipt.captureComplete=false")
    for field in ("hooksInstalled", "quiescentCleanup"):
        _require(receipt.get(field) is True,
                 f"receipt.{field}: required even for source-bound diagnostics")
    counters: dict[str, dict[str, int]] = {}
    reasons: list[dict[str, Any]] = [{"gate": "captureComplete", "actual": False}]
    for section, expected in (("losses", LOSS_COUNTERS),
                              ("overflow", OVERFLOW_COUNTERS)):
        raw = receipt.get(section)
        _require(isinstance(raw, Mapping) and set(raw) == set(expected),
                 f"receipt.{section}: expected the complete v3 counter set")
        section_counters = {}
        for name in expected:
            value = raw[name]
            _require(type(value) is int and value >= 0,
                     f"receipt.{section}.{name}: expected nonnegative integer")
            section_counters[name] = value
            if value:
                reasons.append({"gate": f"{section}.{name}", "actual": value})
        counters[section] = section_counters
    for field in ("unsupported", "unsupportedSourceLength",
                  "unsupportedSourceIdentity", "wrongCallsite",
                  "progressPublicationFailures"):
        value = receipt.get(field)
        _require(type(value) is int and value >= 0,
                 f"receipt.{field}: expected nonnegative integer")
    _require(receipt["unsupported"] == receipt["unsupportedSourceLength"]
             + receipt["unsupportedSourceIdentity"],
             "receipt.unsupported: does not reconcile with source counters")
    if receipt["progressPublicationFailures"]:
        reasons.append({"gate": "progressPublicationFailures",
                        "actual": receipt["progressPublicationFailures"]})
    pending = receipt.get("pendingRecords")
    _require(type(pending) is int and pending >= 0,
             "receipt.pendingRecords: expected nonnegative integer")
    if pending:
        reasons.append({"gate": "pendingRecords", "actual": pending})
    return {**counters, "failureReasons": reasons}


def _diagnose_source_rows(
    receipt: Mapping[str, Any], *, corpus_path: Path, native_context_path: Path,
    receipt_path: Path, receipt_sha256: str,
) -> dict[str, Any]:
    """Authenticate current inputs, then verify retained rows without transport promotion."""
    input_set = receipt_verifier._sha256_text(
        receipt.get("inputSetSha256"), source="receipt.inputSetSha256"
    )
    native = receipt.get("nativeInputs")
    _require(isinstance(native, Mapping), "receipt.nativeInputs: expected object")
    game_hash = receipt_verifier._sha256_text(
        native.get("gameAssemblySha256"),
        source="receipt.nativeInputs.gameAssemblySha256",
    )
    metadata_hash = receipt_verifier._sha256_text(
        native.get("metadataSha256"), source="receipt.nativeInputs.metadataSha256",
    )
    corpus, corpus_sha256 = receipt_verifier._load_json_with_sha256(
        corpus_path, label="SkillData corpus report"
    )
    native_context, native_context_sha256 = receipt_verifier._load_json_with_sha256(
        native_context_path, label="IL2CPP context report"
    )
    corpus_rows = receipt_verifier._validate_report_gates(
        input_set, game_hash, metadata_hash, corpus, native_context, corpus_sha256
    )
    rows = [
        receipt_verifier._verify_observation(observation, index, corpus_rows, input_set)
        for index, observation in enumerate(receipt["observations"])
    ]
    return {
        "inputSetSha256": input_set,
        "nativeInputs": {"gameAssemblySha256": game_hash,
                         "metadataSha256": metadata_hash},
        "provenance": {
            "receipt": receipt_verifier._file_provenance(receipt_path, receipt_sha256),
            "corpusReport": {
                **receipt_verifier._file_provenance(corpus_path, corpus_sha256),
                "identitySetSha256": corpus.get("identitySetSha256"),
            },
            "nativeContext": receipt_verifier._file_provenance(
                native_context_path, native_context_sha256
            ),
            "verifier": receipt_verifier._file_provenance(
                Path(receipt_verifier.__file__), hashlib.sha256(
                    Path(receipt_verifier.__file__).read_bytes()
                ).hexdigest().upper(),
            ),
        },
        "summary": {"failureReasons": []},
        "rows": rows,
    }


def verify_capture_target_set(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
    receipt_sha256: str,
    corpus_path: Path = DEFAULT_CORPUS,
    native_context_path: Path = DEFAULT_NATIVE_CONTEXT,
    target_contract_path: Path = DEFAULT_TARGET_CONTRACT,
    diagnose_incomplete: bool = False,
) -> dict[str, Any]:
    """Verify strictly, or diagnose retained rows without publishing transport loss."""
    _require(receipt.get("schema") == RECEIPT_SCHEMA,
             "receipt.schema: expected v3 target-set capture")
    _require("targetSourceSha256" not in receipt,
             "receipt.targetSourceSha256: singleton binding is invalid in v3")
    binding = context_audit.preflight_native_only(
        corpus_path, native_context_path, target_contract_path
    )
    target_sources = binding["targetSources"]
    _require(receipt.get("targetSources") == target_sources,
             "receipt.targetSources: differs from the preflighted target set")
    _require(receipt.get("targetSetBindingSha256") ==
             binding["targetSetBindingSha256"],
             "receipt.targetSetBindingSha256: differs from canonical target binding")
    transport = _diagnostic_transport(receipt) if diagnose_incomplete else None
    contract, contract_sha256 = receipt_verifier._load_json_with_sha256(
        target_contract_path, label="capture target-set contract"
    )
    native_context = receipt_verifier._load_json(
        native_context_path, label="capture target-set native context"
    )
    _require(native_context.get("schema") == context_audit.SCHEMA
             and native_context.get("captureTargetSet") == contract.get("targets")
             and native_context.get("targetSources") == target_sources
             and native_context.get("targetSetBindingSha256") ==
             binding["targetSetBindingSha256"],
             "native context target set differs from reviewed contract")
    reference = native_context.get("captureTargetSetContractReference")
    _require(isinstance(reference, Mapping)
             and receipt_verifier._sha256_text(
                 reference.get("sha256"),
                 source="nativeContext.captureTargetSetContractReference.sha256"
             ) == contract_sha256,
             "native context target-set contract bytes differ")
    source_by_pair = {
        (source["sourceLength"], source["sourceSha256"]): source
        for source in target_sources
    }
    observations = receipt.get("observations")
    _require(isinstance(observations, list), "receipt.observations: expected array")
    if "observationCount" in receipt:
        _require(type(receipt["observationCount"]) is int
                 and receipt["observationCount"] == len(observations),
                 "receipt.observationCount: differs from observations array")
    observed_indices: dict[str, list[int]] = {}
    for index, observation in enumerate(observations):
        _require(isinstance(observation, Mapping),
                 f"receipt.observations[{index}]: expected object")
        data, digest = receipt_verifier._decode_source(observation, index)
        _require(len(data) <= binding["captureMaxSourceBytes"],
                 f"receipt.observations[{index}]: source exceeds recorder bound")
        _require((len(data), digest) in source_by_pair,
                 f"receipt.observations[{index}]: copied source is outside target set")
        observed_indices.setdefault(digest, []).append(index)
    stats = _target_stats(receipt, target_sources,
                          {digest: len(indices) for digest, indices in observed_indices.items()})
    processed = receipt.get("observationsProcessed")
    expected_processed = sum(
        stat["observationsPublished"] + stat["duplicateIdentical"]
        + stat["duplicateConflicts"] for stat in stats
    )
    _require(type(processed) is int and processed == expected_processed,
             "receipt.observationsProcessed: differs from completed target pairs")
    for field in ("publishedRecords", "completedPairs"):
        _require(type(receipt.get(field)) is int and receipt[field] == processed,
                 f"receipt.{field}: differs from completed target pairs")
    pending = receipt.get("pendingRecords")
    _require(type(pending) is int and 0 <= pending <= sum(
        stat["unverifiedPairs"] for stat in stats
    ), "receipt.pendingRecords: exceeds attributable unverified pairs")
    if diagnose_incomplete:
        # The original receipt remains failed and unchanged.  Only the copied
        # sources are analyzed after independent current-corpus/native gates.
        cursor = _diagnose_source_rows(
            receipt, corpus_path=corpus_path,
            native_context_path=native_context_path,
            receipt_path=receipt_path, receipt_sha256=receipt_sha256,
        )
    else:
        # Reuse the unchanged v2 cursor verifier for global teardown/native/
        # corpus gates and each copied source's 47+2 reader cursor validation.
        # Only the schema discriminator is adapted in memory; the raw file
        # hash is still attached to the verification provenance.
        legacy_compatible = dict(receipt)
        legacy_compatible["schema"] = receipt_verifier.SCHEMA
        cursor = receipt_verifier.verify_skilldata_cursor_capture(
            legacy_compatible,
            corpus_report_path=corpus_path,
            native_context_path=native_context_path,
            required_logical_paths=(),
            receipt_path=receipt_path,
            receipt_sha256=receipt_sha256,
        )
    ignored = {"all_rows_exact_closed", "required_source_lengths"}
    unexpected = [reason for reason in cursor["summary"]["failureReasons"]
                  if reason.get("gate") not in ignored]
    _require(not unexpected,
             f"cursor verification has unexpected global failures: {unexpected!r}")
    rows = cursor["rows"]
    targets = native_context["captureTargetSet"]
    per_target: list[dict[str, Any]] = []
    for target, stat in zip(targets, stats):
        digest = target["logicalSha256"]
        indices = observed_indices.get(digest, [])
        target_rows = [rows[index] for index in indices]
        for index, row in zip(indices, target_rows):
            _require((row.get("logicalPath"), row.get("logicalSha256"),
                      row.get("hardLimit")) ==
                     (target["virtualPath"], digest, target["length"]),
                     f"cursor row {index}: current logical source join differs from contract")
        exact = [row for row in target_rows
                 if row.get("boundaryClass") == "exact-closed"]
        signatures = {_observation_signature(row) for row in exact}
        if stat["duplicateConflicts"] or len(signatures) > 1:
            status = "conflict"
        elif len(exact) != len(target_rows):
            status = "observed-unverified"
        elif not indices:
            status = "observed-unverified" if stat["unverifiedPairs"] else "missing"
        elif stat["unverifiedPairs"]:
            status = "observed-exact-closed-with-unverified-pairs"
        else:
            status = "observed-exact-closed"
        exact_witness = status in (
            "observed-exact-closed", "observed-exact-closed-with-unverified-pairs"
        )
        representative = exact[0] if exact_witness else None
        capture_health = (
            "duplicate-conflict" if status == "conflict" else
            "local-unverified-pairs" if stat["unverifiedPairs"] else
            "unverified-observation" if status == "observed-unverified" else "clean"
        )
        per_target.append({
            "virtualPath": target["virtualPath"],
            "sourceLength": target["length"],
            "logicalSha256": digest,
            "role": target["role"],
            "status": status,
            "cursorEvidenceStatus": "exact-closed" if exact_witness else "not-established",
            "captureHealth": capture_health,
            "observationIndices": indices,
            "observationCount": len(indices),
            "duplicateIdentical": stat["duplicateIdentical"],
            "duplicateConflicts": stat["duplicateConflicts"],
            "unverifiedPairs": stat["unverifiedPairs"],
            "observationClasses": [row.get("boundaryClass") for row in target_rows],
            "diagnostics": [row.get("diagnostic") for row in target_rows
                            if row.get("diagnostic") is not None],
            "selectedTerminal": representative.get("candidate") if representative else None,
            "runtimeFieldRanges": representative.get("runtimeFieldRanges") if representative else None,
            "actionGroupCheckpoints": representative.get("actionGroupCheckpoints") if representative else None,
            "parserCursor": representative.get("parserCursor") if representative else None,
            "wholeSchemaExact": False,
            "nestedActionGroupInterior": "unresolved" if target["role"] == "unresolved"
                                         else "prior-profile-not-reproven",
            "evidenceBoundary": (
                "Exact copied-byte source identity and same-reader field/child cursors select "
                "the terminal candidate and close the top-level reader at EOF only when status "
                "is observed-exact-closed or observed-exact-closed-with-unverified-pairs. "
                "The latter preserves the exact witness but is not clean promotion coverage. "
                "Nonempty ActionGroup nested member semantics are not established by these cursors."
            ),
        })
    unresolved = [row for row in per_target if row["role"] == "unresolved"]
    controls = [row for row in per_target if row["role"] == "positiveControl"]
    missing = [row["virtualPath"] for row in unresolved if row["status"] == "missing"]
    exact_count = sum(row["status"] == "observed-exact-closed" for row in unresolved)
    exact_witness_count = sum(row["cursorEvidenceStatus"] == "exact-closed"
                              for row in unresolved)
    coverage = ("incomplete" if diagnose_incomplete else
                "complete" if exact_count == len(unresolved) else "partial")
    result = {
        "schema": DIAGNOSTIC_OUTPUT_SCHEMA if diagnose_incomplete else OUTPUT_SCHEMA,
        "status": "incomplete" if diagnose_incomplete else "validated",
        "coverageStatus": coverage,
        "inputSetSha256": cursor["inputSetSha256"],
        "nativeInputs": cursor["nativeInputs"],
        "targetSetBindingSha256": binding["targetSetBindingSha256"],
        "provenance": {
            **cursor["provenance"],
            "captureTargetSetContract": receipt_verifier._file_provenance(
                target_contract_path, contract_sha256),
            "captureTargetSetVerifier": receipt_verifier._file_provenance(
                Path(__file__), hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()),
        },
        "summary": {
            "unresolvedTargets": len(unresolved),
            "unresolvedExactClosed": exact_count,
            "unresolvedExactWitnesses": exact_witness_count,
            "unresolvedExactWitnessesWithUnverifiedPairs":
                exact_witness_count - exact_count,
            "unresolvedMissing": len(missing),
            "unresolvedConflicted": sum(row["status"] == "conflict" for row in unresolved),
            "unresolvedObservedUnverified": sum(row["status"] == "observed-unverified" for row in unresolved),
            "missingTargets": missing,
            "positiveControls": len(controls),
            "positiveControlsExactClosed": sum(row["status"] == "observed-exact-closed"
                                               for row in controls),
            "missingPositiveControls": [row["virtualPath"] for row in controls
                                        if row["status"] == "missing"],
            "observationCount": len(observations),
            "observationsProcessed": processed,
            "globalFailureReasons": unexpected,
        },
        "targets": per_target,
        "rows": rows,
        "evidenceBoundary": (
            ("The original capture is globally incomplete and cannot be published. "
             "Diagnostic analysis authenticates current native and source inputs and the "
             "exact reviewed target set. " if diagnose_incomplete else
             "Global validation authenticates complete loss-free capture, current native and "
             "source inputs, and the exact reviewed target set. Optional sources may be missing. ")
            +
            "Each observed source is verified independently; conflicting or unclosed sources "
            "cannot establish terminal selection. No nonempty ActionGroup whole-schema claim "
            "is published by this report."
        ),
    }
    if diagnose_incomplete:
        result["publicationEligible"] = False
        result["diagnosticOnly"] = True
        result["transport"] = transport
        result["summary"]["transportFailureReasons"] = transport["failureReasons"]
        result["summary"]["positiveControlsObservedUnverified"] = sum(
            row["status"] == "observed-unverified" for row in controls
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_NATIVE_CONTEXT)
    parser.add_argument("--target-contract", type=Path, default=DEFAULT_TARGET_CONTRACT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diagnose-incomplete", action="store_true",
                        help="verify retained rows in a failed v3 transport; always non-publishable")
    args = parser.parse_args(argv)
    output = args.output or (DEFAULT_DIAGNOSTIC_OUTPUT if args.diagnose_incomplete
                             else DEFAULT_OUTPUT)
    try:
        receipt, digest = receipt_verifier._load_json_with_sha256(
            args.receipt, label="target-set capture receipt"
        )
        result = verify_capture_target_set(
            receipt, receipt_path=args.receipt, receipt_sha256=digest,
            corpus_path=args.corpus_report, native_context_path=args.native_context,
            target_contract_path=args.target_contract,
            diagnose_incomplete=args.diagnose_incomplete,
        )
    except (receipt_verifier.ReceiptVerificationError,
            context_audit.native.NativeCursorContextError) as exc:
        result = {"schema": DIAGNOSTIC_OUTPUT_SCHEMA if args.diagnose_incomplete
                  else OUTPUT_SCHEMA, "status": "failed", "diagnostic": str(exc)}
        if args.diagnose_incomplete:
            result["publicationEligible"] = False
            result["diagnosticOnly"] = True
    context_audit.native._atomic_json(output, result)
    print(json.dumps({"status": result["status"],
                      "coverageStatus": result.get("coverageStatus"),
                      "summary": result.get("summary"),
                      "diagnostic": result.get("diagnostic"),
                      "output": str(output)}, ensure_ascii=False))
    return 0 if result.get("status") == "validated" else (2 if result.get("status") == "incomplete" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
