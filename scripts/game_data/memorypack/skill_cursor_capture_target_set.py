"""Verify a bounded multi-source SkillData cursor session source by source.

The v3 runtime receipt can observe any reviewed source in one session.  A
source that never loads is reported missing; a conflicting source is isolated
to that source.  Diagnostic mode can inspect retained rows from an incomplete
transport, but its output is never publication eligible.  This verifier does
not publish a whole-schema corpus claim.

The target set (``contracts/skill_cursor_capture_target_set.json``, gated
for offline validation by ``python -m
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

Offline workflow. ``python -m
scripts.game_data.il2cpp.skill_cursor_target_set_context`` validates the native
and source binding. ``python -m
scripts.game_data.memorypack.skill_cursor_target_set_progress
<session>/skilldata-cursor/progress.json`` inspects provisional saved coverage;
this module verifies ``<session>/skilldata-cursor/receipt.json`` into
``reports/animestudio/skilldata_cursor_target_set_verification_latest.json``
(with ``--diagnose-incomplete``, into
``skilldata_cursor_target_set_diagnostic_latest.json``). The verification
is what ``memorypack.skill_corpus --capture-target-set-verification`` replays.
Raw sessions stay under ``scratch/reverse_engineering/endfield_capture/``.

Offline rebind.  After an exporter audit changes inputSetSha256 without a
game-build change, stream only the reviewed target paths with
``skill_corpus --target-set-contract`` into a partial report under ``tmp/``.
``--rebind-current-corpus --historical-verification`` rechecks the unchanged
raw receipt, historical target binding, current source bytes, native reader
and static field spans against that exact sparse scope.  Its report retains
the capture's original input set and can later be replayed by the full corpus
gate if a complete publication is separately authorized.  It never labels
the sparse report a full SkillData census.
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
REBIND_OUTPUT_SCHEMA = "endfield.skillDataCursorTargetSetRebind.v1"
DIAGNOSTIC_OUTPUT_SCHEMA = "endfield.skillDataCursorTargetSetDiagnostic.v1"
RECEIPT_SCHEMA = "endfieldCapture.skillDataCursorCapture.v3"
DEFAULT_CORPUS = context_audit.DEFAULT_CORPUS
DEFAULT_NATIVE_CONTEXT = context_audit.DEFAULT_CONTEXT
DEFAULT_TARGET_CONTRACT = context_audit.TARGET_CONTRACT_PATH
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_target_set_verification_latest.json"
DEFAULT_DIAGNOSTIC_OUTPUT = (
    REPO_ROOT / "reports/animestudio/skilldata_cursor_target_set_diagnostic_latest.json"
)
DEFAULT_REBIND_OUTPUT = (
    REPO_ROOT / "reports/animestudio/skilldata_cursor_target_set_rebind_latest.json"
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


def _pinned_historical_input(value: Any, *, label: str,
                             expected_path: Path | None = None) -> dict[str, Any]:
    """Authenticate saved evidence bytes without requiring old code to be live."""
    _require(isinstance(value, Mapping), f"historical {label}: missing file reference")
    raw_path = value.get("path")
    _require(isinstance(raw_path, str) and Path(raw_path).is_absolute(),
             f"historical {label}: expected absolute file path")
    path = Path(raw_path).resolve()
    if expected_path is not None:
        _require(path == expected_path.resolve(),
                 f"historical {label}: path differs from selected input")
    actual = context_audit.native._file_reference(path)
    _require((value.get("length"), value.get("sha256")) ==
             (actual["length"], actual["sha256"]),
             f"historical {label}: saved file bytes differ")
    return actual


def verify_capture_target_set_rebind(
    receipt: Mapping[str, Any], *, receipt_path: Path, receipt_sha256: str,
    historical_verification_path: Path, corpus_path: Path,
    target_contract_path: Path = DEFAULT_TARGET_CONTRACT,
) -> dict[str, Any]:
    """Recheck a saved complete v3 session on a newly streamed input set.

    The old input-set value remains attached to the capture.  Only the
    independently authenticated current corpus supplies the new value; every
    copied source and reader cursor is checked anew before an overlay may use
    this report.  Old code fingerprints are retained as historical provenance,
    rather than incorrectly treated as current code.
    """
    _require(receipt.get("schema") == RECEIPT_SCHEMA,
             "receipt.schema: expected v3 target-set capture")
    legacy_compatible = dict(receipt)
    legacy_compatible["schema"] = receipt_verifier.SCHEMA
    from_input, game_hash, metadata_hash, _unsupported = (
        receipt_verifier._require_capture_gates(legacy_compatible)
    )
    _require(receipt.get("pendingRecords") == 0
             and receipt.get("progressPublicationFailures") == 0,
             "receipt transport: pending records or progress publication failures")
    _require("targetSourceSha256" not in receipt,
             "receipt.targetSourceSha256: singleton binding is invalid in v3")
    _require((receipt.get("unsupported") == receipt.get("unsupportedSourceLength", 0)
              + receipt.get("unsupportedSourceIdentity", 0))
             and all(type(receipt.get(name)) is int and receipt[name] >= 0
                     for name in ("unsupportedSourceLength", "unsupportedSourceIdentity",
                                  "wrongCallsite")),
             "receipt unsupported and callsite counters are invalid")

    historical, historical_sha256 = receipt_verifier._load_json_with_sha256(
        historical_verification_path, label="historical target-set verification"
    )
    historical_provenance = historical.get("provenance")
    historical_summary = historical.get("summary")
    historical_targets = historical.get("targets")
    historical_rows = historical.get("rows")
    _require(historical.get("schema") == OUTPUT_SCHEMA
             and historical.get("status") == "validated"
             and historical.get("coverageStatus") == "complete"
             and historical.get("publicationEligible") is not False
             and historical.get("inputSetSha256") == from_input
             and historical.get("nativeInputs") == {
                 "gameAssemblySha256": game_hash, "metadataSha256": metadata_hash}
             and isinstance(historical_provenance, Mapping)
             and isinstance(historical_summary, Mapping)
             and historical_summary.get("globalFailureReasons") == []
             and isinstance(historical_targets, list)
             and isinstance(historical_rows, list),
             "historical target-set verification is not complete for this capture")
    receipt_reference = _pinned_historical_input(
        historical_provenance.get("receipt"), label="receipt",
        expected_path=receipt_path,
    )
    _require(receipt_reference["sha256"] == receipt_sha256.upper(),
             "receipt bytes changed since loading")
    old_corpus_reference = _pinned_historical_input(
        historical_provenance.get("corpusReport"), label="corpus report"
    )
    old_context_reference = _pinned_historical_input(
        historical_provenance.get("nativeContext"), label="native context"
    )
    target_contract_reference = _pinned_historical_input(
        historical_provenance.get("captureTargetSetContract"),
        label="target-set contract", expected_path=target_contract_path,
    )
    # These verifier files are expected to have changed.  Their old digests
    # are provenance only; the current implementation rechecks raw evidence.
    for name in ("verifier", "captureTargetSetVerifier"):
        recorded = historical_provenance.get(name)
        _require(isinstance(recorded, Mapping)
                 and isinstance(recorded.get("path"), str)
                 and type(recorded.get("length")) is int
                 and recorded["length"] > 0
                 and isinstance(recorded.get("sha256"), str)
                 and context_audit.native.HEX64.fullmatch(recorded["sha256"]) is not None,
                 f"historical {name}: invalid code provenance")

    contract = receipt_verifier._load_json(
        target_contract_path, label="target-set contract"
    )
    _require(historical_provenance.get("corpusReport", {}).get("identitySetSha256")
             == contract.get("sourceIdentitySetSha256"),
             "historical verification and reviewed target-set identity differ")
    old_context = receipt_verifier._load_json(
        Path(old_context_reference["path"]), label="historical native context"
    )
    selected_basis = contract.get("selectedStatusBasis")
    _require(isinstance(selected_basis, Mapping)
             and isinstance(selected_basis.get("path"), str),
             "target-set contract lacks its historical selected-status basis")
    selected_path = (REPO_ROOT / selected_basis["path"]).resolve()
    report_root = (REPO_ROOT / "reports/animestudio").resolve()
    _require(selected_path.is_relative_to(report_root)
             and selected_path.name.startswith("skilldata_target_set_selected_basis_")
             and selected_path.suffix == ".json",
             "historical selected-status basis path is invalid")
    selected_reference = _pinned_historical_input(
        {"path": str(selected_path), "length": selected_basis.get("length"),
         "sha256": selected_basis.get("sha256")},
        label="selected-status basis", expected_path=selected_path,
    )
    _require(old_context.get("schema") == context_audit.SCHEMA
             and old_context.get("inputSetSha256") == from_input
             and old_context.get("corpusReference", {}).get("sha256")
             == old_corpus_reference["sha256"]
             and old_context.get("selectedStatusReportReference") == selected_reference
             and old_context.get("captureTargetSetContractReference", {}).get("sha256")
             == target_contract_reference["sha256"],
             "historical native context no longer joins its pinned inputs")

    current_corpus, current_corpus_sha256 = receipt_verifier._load_json_with_sha256(
        corpus_path, label="current unselected SkillData corpus"
    )
    context_audit.native.verify_current_report_inputs(
        current_corpus, allow_partial=True
    )
    to_input = receipt_verifier._sha256_text(
        current_corpus.get("inputSetSha256"), source="currentCorpus.inputSetSha256"
    )
    _require(contract.get("schema") == context_audit.CONTRACT_SCHEMA
             and contract.get("status") == "selected-current-logical-source-set"
             and contract.get("captureMaxSourceBytes") == 131072
             and isinstance(contract.get("targets"), list),
             "reviewed target-set contract shape is invalid")
    targets = contract["targets"]
    target_paths = [row.get("virtualPath") if isinstance(row, Mapping) else None
                    for row in targets]
    current_rows = current_corpus.get("files")
    _require(current_corpus.get("status") == "partial"
             and current_corpus.get("publicationEligible") is False
             and isinstance(current_rows, list)
             and len(current_rows) == len(targets)
             and current_corpus.get("targetedVirtualPaths") == target_paths
             and target_paths == sorted(target_paths)
             and len(target_paths) == len(set(target_paths)),
             "current target basis is not the exact reviewed sparse scope")
    _require(current_corpus.get("provenance", {}).get("targetSelectionContract") ==
             target_contract_reference,
             "current sparse basis does not pin the reviewed target contract")
    for target, row in zip(targets, current_rows):
        _require(isinstance(target, Mapping) and isinstance(row, Mapping)
                 and target.get("role") in ("unresolved", "positiveControl")
                 and (row.get("virtualPath"), row.get("length"),
                      row.get("logicalSha256")) ==
                 (target.get("virtualPath"), target.get("length"),
                  target.get("logicalSha256"))
                 and row.get("inputSetSha256") == to_input
                 and row.get("blockName") == "JsonData"
                 and row.get("blockTypeValue") == 19
                 and row.get("boundaryClass") == "ambiguous"
                 and row.get("coverageStatus") == "ambiguous-disjoint-independent-ranges"
                 and row.get("wholeSchemaExact") is False
                 and row.get("terminalSelection") is None
                 and isinstance(row.get("framing"), Mapping)
                 and row["framing"].get("candidateCount") == 2,
                 f"current sparse target row differs from reviewed source: {target}")
    _require(to_input != from_input,
             "rebind requires a new input set; use strict same-input verification")
    target_sources = [
        {"sourceLength": row["length"], "sourceSha256": row["logicalSha256"]}
        for row in targets
    ]
    binding_sha256 = context_audit.target_set_binding_sha256(target_sources)
    _require(receipt.get("targetSources") == target_sources
             and receipt.get("targetSetBindingSha256") == binding_sha256
             and historical.get("targetSetBindingSha256") == binding_sha256
             and old_context.get("targetSources") == target_sources
             and old_context.get("captureTargetSet") == targets,
             "capture target binding differs from the reviewed source set")
    _require(contract.get("nativeInputs") ==
             {"GameAssembly.dll": game_hash, "global-metadata.dat": metadata_hash},
             "target-set native pins differ from the captured build")
    native_contract_path = context_audit.native.CONTRACT_PATH
    native_contract_reference = context_audit.native._file_reference(native_contract_path)
    historical_observer_reference = old_context.get("contractReference")
    _require(isinstance(historical_observer_reference, Mapping)
             and isinstance(historical_observer_reference.get("path"), str)
             and Path(historical_observer_reference["path"]).resolve()
             == native_contract_path.resolve()
             and type(historical_observer_reference.get("length")) is int
             and historical_observer_reference["length"] > 0
             and isinstance(historical_observer_reference.get("sha256"), str)
             and context_audit.native.HEX64.fullmatch(
                 historical_observer_reference["sha256"]) is not None,
             "historical native observer contract provenance is invalid")
    native_contract = receipt_verifier._load_json(
        native_contract_path, label="native observer contract"
    )
    historical_observer = old_context.get("selectedSkillDataReaderOrder", {})
    historical_observer = (historical_observer.get("runtimeCursorObserver")
                           if isinstance(historical_observer, Mapping) else None)
    _require(isinstance(historical_observer, Mapping)
             and historical_observer.get("status") == "exact-static-callsite-vector"
             and historical_observer.get("fieldCallsites")
             == native_contract.get("fieldCallsites")
             and historical_observer.get("inlineField")
             == native_contract.get("inlineField")
             and historical_observer.get("actionGroupChildCallsites")
             == native_contract.get("actionGroupChildCallsites")
             and historical_observer.get("sourceLengths")
             == native_contract.get("receiptVerifierSourceLengths")
             and native_contract.get("nativeInputs") == contract.get("nativeInputs")
             and old_context.get("nativeInputs", {}).get("gameassemblySha256")
             == game_hash
             and old_context.get("nativeInputs", {}).get("metadataSha256")
             == metadata_hash
             and old_context.get("nativeValidation", {}).get("status")
             == "validated",
             "native observer geometry or build differs from the captured context")
    build_fingerprints = current_corpus.get("provenance", {}).get("buildFingerprints")
    _require(isinstance(build_fingerprints, list),
             "current sparse basis lacks native build fingerprints")
    selected_native = {
        Path(str(row.get("path"))).name.casefold(): row
        for row in build_fingerprints if isinstance(row, Mapping)
    }
    game_row = selected_native.get("gameassembly.dll")
    metadata_row = selected_native.get("global-metadata.dat")
    _require(isinstance(game_row, Mapping) and isinstance(metadata_row, Mapping)
             and game_row.get("sha256") == game_hash
             and metadata_row.get("sha256") == metadata_hash,
             "current sparse basis native paths/hashes differ from receipt")
    native_gate = context_audit.native.check_installed_native_inputs(
        game_hash, metadata_hash,
        gameassembly=Path(game_row["path"]), metadata=Path(metadata_row["path"]),
    )
    _require(native_gate.status == "validated",
             f"selected native inputs {native_gate.status}: {native_gate.detail}")
    image = context_audit.native.NativeImage(
        native_gate.gameassembly, native_gate.metadata,
        label="skill-cursor-target-set-rebind",
    )
    native_counts = context_audit.native.validate_native_observer(
        native_contract, image, source=str(native_contract_path)
    )

    observations = receipt.get("observations")
    _require(isinstance(observations, list)
             and len(observations) == len(targets)
             and len(historical_targets) == len(targets)
             and len(historical_rows) == len(targets),
             "target-set capture does not contain one observation per reviewed target")
    if "observationCount" in receipt:
        _require(type(receipt["observationCount"]) is int
                 and receipt["observationCount"] == len(observations),
                 "receipt.observationCount differs from its observations")
    observed_counts: dict[str, int] = {}
    for index, observation in enumerate(observations):
        _require(isinstance(observation, Mapping),
                 f"receipt.observations[{index}]: expected object")
        source_bytes, digest = receipt_verifier._decode_source(observation, index)
        _require(len(source_bytes) <= contract["captureMaxSourceBytes"]
                 and {"sourceLength": len(source_bytes), "sourceSha256": digest}
                 in target_sources,
                 f"receipt.observations[{index}]: source outside target set")
        observed_counts[digest] = observed_counts.get(digest, 0) + 1
    stats = _target_stats(receipt, target_sources, observed_counts)
    _require(all(row["observationsPublished"] == 1
                 and row["duplicateConflicts"] == 0
                 and row["unverifiedPairs"] == 0 for row in stats),
             "target-set receipt has missing, conflicting, or unverified pairs")
    processed = sum(row["observationsPublished"] + row["duplicateIdentical"]
                    + row["duplicateConflicts"] for row in stats)
    _require(all(type(receipt.get(field)) is int and receipt[field] == processed
                 for field in ("observationsProcessed", "publishedRecords", "completedPairs")),
             "target-set receipt record totals do not reconcile")
    _require(historical_summary.get("observationCount") == len(targets)
             and historical_summary.get("unresolvedTargets") ==
             sum(row["role"] == "unresolved" for row in targets)
             and historical_summary.get("unresolvedExactClosed") ==
             historical_summary.get("unresolvedTargets")
             and historical_summary.get("positiveControls") == 1
             and historical_summary.get("positiveControlsExactClosed") == 1,
             "historical verification did not close the entire target set")

    by_path = {row["virtualPath"]: row for row in current_rows}
    from scripts.game_data.memorypack import skill_cursor_target_set_overlay as overlay
    verified_rows = [
        receipt_verifier._verify_observation(observation, index, current_rows, to_input)
        for index, observation in enumerate(observations)
    ]
    observed_indices = {row.get("logicalSha256"): index
                        for index, row in enumerate(verified_rows)}
    _require(len(observed_indices) == len(targets),
             "runtime observations do not identify every target uniquely")
    prior_targets = {row.get("virtualPath"): row for row in historical_targets
                     if isinstance(row, Mapping)}
    _require(len(prior_targets) == len(targets),
             "historical verification target identities are not unique")
    rebound_targets = []
    for target_index, target in enumerate(targets):
        path, digest, length = (target["virtualPath"], target["logicalSha256"],
                                target["length"])
        index = observed_indices.get(digest)
        _require(type(index) is int, f"{path}: no current runtime observation")
        observed = verified_rows[index]
        source_bytes, _source_hash = receipt_verifier._decode_source(observations[index], index)
        current_row = by_path[path]
        _require((observed.get("logicalPath"), observed.get("logicalSha256"),
                  observed.get("hardLimit"), observed.get("boundaryClass"),
                  observed.get("parserCursor")) ==
                 (path, digest, length, "exact-closed", length)
                 and current_row.get("logicalMd5") == hashlib.md5(source_bytes).hexdigest().upper(),
                 f"{path}: current copied bytes or executed cursor do not close")
        old_target = prior_targets.get(path)
        old_row = historical_rows[index]
        _require(isinstance(old_target, Mapping)
                 and old_target.get("role") == target["role"]
                 and old_target.get("status") == "observed-exact-closed"
                 and old_target.get("captureHealth") == "clean"
                 and old_target.get("observationCount") == 1
                 and old_target.get("observationIndices") == [index]
                 and old_target.get("duplicateConflicts") == 0
                 and old_target.get("unverifiedPairs") == 0
                 and old_target.get("sourceLength") == length
                 and old_target.get("logicalSha256") == digest
                 and old_target.get("selectedTerminal") == observed.get("candidate")
                 and old_target.get("runtimeFieldRanges") == observed.get("runtimeFieldRanges")
                 and old_target.get("actionGroupCheckpoints") ==
                 observed.get("actionGroupCheckpoints")
                 and isinstance(old_row, Mapping)
                 and (old_row.get("logicalPath"), old_row.get("logicalSha256"),
                      old_row.get("hardLimit")) == (path, digest, length),
                 f"{path}: current cursor disagrees with historical verified target")
        rebound = {
            "virtualPath": path, "sourceLength": length, "logicalSha256": digest,
            "role": target["role"], "status": "observed-exact-closed",
            "cursorEvidenceStatus": "exact-closed", "captureHealth": "clean",
            "observationIndices": [index], "observationCount": 1,
            "duplicateIdentical": stats[target_index]["duplicateIdentical"],
            "duplicateConflicts": 0, "unverifiedPairs": 0,
            "selectedTerminal": observed["candidate"],
            "runtimeFieldRanges": observed["runtimeFieldRanges"],
            "actionGroupCheckpoints": observed["actionGroupCheckpoints"],
            "parserCursor": observed["parserCursor"], "wholeSchemaExact": False,
            "nestedActionGroupInterior": "unresolved",
        }
        overlay._validate_join(current_row, rebound, observed)
        rebound_targets.append(rebound)

    return {
        "schema": REBIND_OUTPUT_SCHEMA,
        "status": "validated", "coverageStatus": "complete",
        "publicationEligible": True,
        "fromInputSetSha256": from_input, "inputSetSha256": to_input,
        "nativeInputs": {"gameAssemblySha256": game_hash,
                         "metadataSha256": metadata_hash},
        "targetSetBindingSha256": binding_sha256,
        "provenance": {
            "receipt": receipt_reference,
            "historicalVerification": receipt_verifier._file_provenance(
                historical_verification_path, historical_sha256),
            "historicalCorpus": old_corpus_reference,
            "historicalNativeContext": old_context_reference,
            "selectedStatusBasis": selected_reference,
            "corpusReport": {**receipt_verifier._file_provenance(
                corpus_path, current_corpus_sha256),
                "identitySetSha256": current_corpus["identitySetSha256"]},
            "targetContract": target_contract_reference,
            "historicalObserverContract": dict(historical_observer_reference),
            "observerContract": native_contract_reference,
            "cursorVerifier": context_audit.native._file_reference(
                Path(receipt_verifier.__file__)),
            "rebindVerifier": context_audit.native._file_reference(Path(__file__)),
            "targetSetOverlay": context_audit.native._file_reference(
                Path(overlay.__file__)),
        },
        "nativeValidation": {"status": "validated", **native_counts},
        "summary": {
            "unresolvedTargets": historical_summary["unresolvedTargets"],
            "unresolvedExactClosed": historical_summary["unresolvedTargets"],
            "positiveControls": 1, "positiveControlsExactClosed": 1,
            "observationCount": len(verified_rows), "globalFailureReasons": [],
        },
        "targets": rebound_targets, "rows": verified_rows,
        "evidenceBoundary": (
            "The old loss-free v3 capture retains its original input set. An exact "
            "27-source current VFS/stream target basis and the selected native observer "
            "reconfirm each copied logical source and all direct reader cursors through "
            "EOF. Current static ActionGroup and top-level field spans agree for each "
            "source; populated ActionGroup child interiors and gameplay branch execution "
            "remain unresolved."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--corpus-report", type=Path)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_NATIVE_CONTEXT)
    parser.add_argument("--target-contract", type=Path, default=DEFAULT_TARGET_CONTRACT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diagnose-incomplete", action="store_true",
                        help="verify retained rows in a failed v3 transport; always non-publishable")
    parser.add_argument("--rebind-current-corpus", action="store_true",
                        help="recheck a complete historical v3 receipt against its exact current sparse target scope")
    parser.add_argument("--historical-verification", type=Path,
                        help="complete original target-set verification, required for offline rebind")
    args = parser.parse_args(argv)
    if args.rebind_current_corpus:
        if args.diagnose_incomplete or args.historical_verification is None or args.corpus_report is None:
            parser.error("offline rebind requires --historical-verification and --corpus-report, without --diagnose-incomplete")
    elif args.historical_verification is not None:
        parser.error("--historical-verification requires --rebind-current-corpus")
    output = args.output or (DEFAULT_REBIND_OUTPUT if args.rebind_current_corpus
                             else DEFAULT_DIAGNOSTIC_OUTPUT if args.diagnose_incomplete
                             else DEFAULT_OUTPUT)
    protected = [args.receipt, args.target_contract]
    if args.corpus_report is not None:
        protected.append(args.corpus_report)
    if args.historical_verification is not None:
        protected.append(args.historical_verification)
    if output.resolve() in {path.resolve() for path in protected}:
        parser.error("--output must not replace a receipt or evidence input")
    try:
        receipt, digest = receipt_verifier._load_json_with_sha256(
            args.receipt, label="target-set capture receipt"
        )
        if args.rebind_current_corpus:
            result = verify_capture_target_set_rebind(
                receipt, receipt_path=args.receipt, receipt_sha256=digest,
                historical_verification_path=args.historical_verification,
                corpus_path=args.corpus_report,
                target_contract_path=args.target_contract,
            )
        else:
            result = verify_capture_target_set(
                receipt, receipt_path=args.receipt, receipt_sha256=digest,
                corpus_path=args.corpus_report or DEFAULT_CORPUS,
                native_context_path=args.native_context,
                target_contract_path=args.target_contract,
                diagnose_incomplete=args.diagnose_incomplete,
            )
    except (receipt_verifier.ReceiptVerificationError,
            context_audit.native.NativeCursorContextError,
            context_audit.native.CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": REBIND_OUTPUT_SCHEMA if args.rebind_current_corpus
                  else DIAGNOSTIC_OUTPUT_SCHEMA if args.diagnose_incomplete
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
