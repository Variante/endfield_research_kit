"""Verify one exact-hash SkillData capture target without changing the older publication receipt.

The legacy receipt verifier is a pinned source of the current SkillData basis.
This diagnostic composes that verifier's native, corpus, cursor and teardown
checks, then replaces only its older two-length publication requirement with
the reviewed current capture target. It does not publish a SkillData selection.

The reviewed target contract (``contracts/skill_cursor_capture_target.json``)
binds one added SkillData logical path, length and current SHA-256 to the
unselected basis.  Another current file shares that length, so the recorder
copies the bounded source first and hashes the copied bytes, rejecting a
same-length source before it opens a cursor transaction; a failed hash
fails closed.  The copy cap, native manifest gate, quiescence checks and
source-hash join stay in force.  The accepted target receipt witnesses the
Purrche second-talent source: fields 0..42 match the static empty-ActionGroup
profile, the cursor selects the earlier one-member terminal and closes at EOF,
and :mod:`skill_cursor_target_overlay` promotes only that exact path and
SHA-256.  Other sources in the same session close their own cursors but are
not admitted, and a source with a populated ActionGroup keeps unresolved
interior ownership.  A second binding with the same schema
(``contracts/skill_cursor_capture_purrche_combo_target.json``, passed with
``--target-contract``) admits Purrche's smaller combo-skill source by exact
copied hash; its populated ActionGroup needs separate interior evidence, and
the second-talent witness cannot select its terminal by analogy.

Capture procedure: wait for ``runtime.ready``, exercise a plausible source
trigger, stop the capture with ``Numpad 9`` while the game is still open, and
retain the raw receipt before exiting; a session that ends by the game
exiting leaves no receipt, and runtime readiness alone never supplies a
cursor.  Authored links identify plausible triggers, not proof that the game
loads the source.

Before a new target, rebuild the all-unselected basis
(``reports/animestudio/skilldata_cursor_basis_latest.json``) and its
native-only context with ``python -m
scripts.game_data.il2cpp.skill_cursor_native_context``, and check the host
with ``tools/EndfieldCapture/StartCapture.bat skilldata-cursor targeted
--skilldata-next-target --preflight-only --no-pause``.  Verify the session's
``<session>/skilldata-cursor/receipt.json`` with ``--output
reports/animestudio/skilldata_cursor_target_verification_latest.json``; that
is what ``memorypack.skill_corpus --capture-target-verification`` replays.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import skill_cursor_receipt as receipt_verifier
from scripts.repo_paths import REPO_ROOT


OUTPUT_SCHEMA = "endfield.skillDataCursorTargetVerification.v1"
DEFAULT_CORPUS = REPO_ROOT / "reports/animestudio/skilldata_cursor_basis_latest.json"
DEFAULT_NATIVE_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_native_context_current_latest.json"
DEFAULT_TARGET_CONTRACT = CONTRACTS_DIR / "skill_cursor_capture_target.json"


def _target_binding(
    receipt: Mapping[str, Any],
    native_context: Mapping[str, Any],
    contract: Mapping[str, Any],
    contract_sha256: str,
) -> tuple[str, int, str]:
    error = receipt_verifier.ReceiptVerificationError
    if (contract.get("schema") != "endfield.skill-cursor-capture-target.v1"
            or contract.get("status") != "selected-current-logical-source"):
        raise error("capture target contract schema or status differs")
    target = contract.get("target")
    if not isinstance(target, Mapping):
        raise error("capture target contract lacks target")
    path = target.get("virtualPath")
    if not isinstance(path, str) or receipt_verifier._normalise_required_path(path) != path:
        raise error("capture target contract has invalid virtualPath")
    length = receipt_verifier._integer(target.get("length"), source="capture target length", minimum=1)
    digest = receipt_verifier._sha256_text(
        target.get("logicalSha256"), source="capture target logicalSha256"
    )
    if receipt.get("targetSourceSha256") != digest:
        raise error("receipt.targetSourceSha256 differs from capture target contract")
    if (native_context.get("status") != "native-only-unselected"
            or not isinstance(native_context.get("captureTarget"), Mapping)):
        raise error("native context is not the unselected capture-target context")
    actual = native_context["captureTarget"]
    if (actual.get("virtualPath"), actual.get("length"), actual.get("logicalSha256")) != (
        path, length, digest
    ):
        raise error("native context capture target differs from contract")
    reference = native_context.get("captureTargetContractReference")
    if not isinstance(reference, Mapping) or receipt_verifier._sha256_text(
        reference.get("sha256"), source="nativeContext.captureTargetContractReference.sha256"
    ) != contract_sha256:
        raise error("native context capture target contract bytes differ")
    return path, length, digest


def verify_capture_target(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
    receipt_sha256: str,
    corpus_path: Path = DEFAULT_CORPUS,
    native_context_path: Path = DEFAULT_NATIVE_CONTEXT,
    target_contract_path: Path = DEFAULT_TARGET_CONTRACT,
) -> dict[str, Any]:
    """Require a complete exact-target cursor while retaining all legacy gates."""
    contract, contract_sha256 = receipt_verifier._load_json_with_sha256(
        target_contract_path, label="capture target contract"
    )
    native_context = receipt_verifier._load_json(
        native_context_path, label="capture native context"
    )
    path, length, digest = _target_binding(
        receipt, native_context, contract, contract_sha256
    )
    result = receipt_verifier.verify_skilldata_cursor_capture(
        receipt,
        corpus_report_path=corpus_path,
        native_context_path=native_context_path,
        required_logical_paths=(path,),
        receipt_path=receipt_path,
        receipt_sha256=receipt_sha256,
    )
    summary = result["summary"]
    verified_lengths = summary["verifiedSourceLengths"]
    failures = [
        reason for reason in summary["failureReasons"]
        if reason.get("gate") != "required_source_lengths"
    ]
    if length not in verified_lengths:
        failures.append({
            "gate": "required_source_lengths", "missing": [length],
            "verified": verified_lengths,
        })
    exact_target_rows = [
        row for row in result["rows"]
        if row.get("boundaryClass") == "exact-closed"
        and row.get("logicalPath") == path
        and row.get("logicalSha256") == digest
        and row.get("hardLimit") == length
    ]
    if not exact_target_rows:
        failures.append({
            "gate": "capture_target_exact_row", "logicalPath": path,
            "expectedSha256": digest,
        })
    result["schema"] = OUTPUT_SCHEMA
    result["verificationMode"] = "capture-target"
    result["status"] = "complete" if not failures else "failed"
    result["captureTarget"] = {
        "logicalPath": path, "sourceLength": length, "logicalSha256": digest,
        "exactObservationCount": len(exact_target_rows),
    }
    result["terminalSelectionContract"]["requiredSourceLengths"] = [length]
    summary["failureReasons"] = failures
    summary["supplementalSourceLengths"] = [
        value for value in verified_lengths if value != length
    ]
    result["provenance"]["captureTargetContract"] = receipt_verifier._file_provenance(
        target_contract_path, contract_sha256
    )
    result["provenance"]["captureTargetVerifier"] = receipt_verifier._file_provenance(
        Path(__file__), hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_NATIVE_CONTEXT)
    parser.add_argument("--target-contract", type=Path, default=DEFAULT_TARGET_CONTRACT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt, receipt_sha256 = receipt_verifier._load_json_with_sha256(
            args.receipt, label="capture receipt"
        )
        result = verify_capture_target(
            receipt,
            receipt_path=args.receipt,
            receipt_sha256=receipt_sha256,
            corpus_path=args.corpus_report,
            native_context_path=args.native_context,
            target_contract_path=args.target_contract,
        )
    except receipt_verifier.ReceiptVerificationError as exc:
        result = {"schema": OUTPUT_SCHEMA, "status": "failed", "diagnostic": str(exc)}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(encoded)
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
