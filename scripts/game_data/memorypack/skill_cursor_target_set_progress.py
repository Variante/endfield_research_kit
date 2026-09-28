"""Show provisional logical-source coverage during a v3 SkillData capture.

This reads the runtime's atomic progress snapshot and maps hashes to reviewed
logical paths.  Only the final quiescent receipt can verify source cursors.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp import skill_cursor_target_set_context as context_audit
from scripts.game_data.memorypack import skill_cursor_receipt as receipt_verifier


PROGRESS_SCHEMA = "endfieldCapture.skillDataCursorProgress.v1"
LOSS_KEYS = (
    "lostObservations", "invalidReaderState", "unreadableReaderState",
    "sourceIdentityHashFailure", "unreadableSource", "truncatedSource",
    "cursorTransitionErrors", "unmatchedCalls",
)
OVERFLOW_KEYS = ("slotOverflow", "retainedRecordOverflow", "drainFailures")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _counters(value: Any, keys: tuple[str, ...], *, label: str) -> dict[str, int]:
    _require(isinstance(value, Mapping), f"{label}: expected object")
    result = {}
    for key in keys:
        count = value.get(key)
        _require(type(count) is int and count >= 0,
                 f"{label}.{key}: expected nonnegative integer")
        result[key] = count
    return result


def summarize_progress(
    progress: Mapping[str, Any], *,
    native_context: Mapping[str, Any],
    target_contract: Mapping[str, Any],
    contract_sha256: str,
) -> dict[str, Any]:
    _require(progress.get("schema") == PROGRESS_SCHEMA,
             "progress.schema: unsupported schema")
    _require(native_context.get("schema") == context_audit.SCHEMA
             and native_context.get("status") == "native-only-unselected",
             "native context: expected target-set preflight report")
    _require(target_contract.get("schema") == context_audit.CONTRACT_SCHEMA
             and target_contract.get("status") == "selected-current-logical-source-set",
             "target contract: unsupported target set")
    reference = native_context.get("captureTargetSetContractReference")
    _require(isinstance(reference, Mapping)
             and reference.get("sha256") == contract_sha256,
             "native context: target contract bytes differ")
    targets = target_contract.get("targets")
    _require(isinstance(targets, list)
             and native_context.get("captureTargetSet") == targets,
             "native context: target rows differ from contract")
    sources = [
        {"sourceLength": target["length"],
         "sourceSha256": target["logicalSha256"]}
        for target in targets
    ]
    _require(native_context.get("targetSources") == sources
             and progress.get("targetSources") == sources,
             "progress.targetSources: differs from reviewed target set")
    _require(progress.get("inputSetSha256") == native_context.get("inputSetSha256"),
             "progress.inputSetSha256: differs from native context")
    stats = progress.get("targetStats")
    _require(isinstance(stats, list) and len(stats) == len(sources),
             "progress.targetStats: expected one ordered row per source")
    processed = progress.get("observationsProcessed")
    _require(type(processed) is int and processed >= 0,
             "progress.observationsProcessed: expected nonnegative integer")
    losses = _counters(progress.get("primaryLosses"), LOSS_KEYS, label="primaryLosses")
    overflow = _counters(progress.get("primaryOverflow"), OVERFLOW_KEYS,
                         label="primaryOverflow")
    rows = []
    for index, (target, source, stat) in enumerate(zip(targets, sources, stats)):
        _require(isinstance(stat, Mapping)
                 and (stat.get("sourceLength"), stat.get("sourceSha256")) ==
                 (source["sourceLength"], source["sourceSha256"]),
                 f"progress.targetStats[{index}]: source identity/order differs")
        counters = _counters(stat, ("observationsPublished", "duplicateIdentical",
                                    "duplicateConflicts", "unverifiedPairs"),
                             label=f"progress.targetStats[{index}]")
        _require(counters["observationsPublished"] <= 1,
                 f"progress.targetStats[{index}]: recorder retains at most one observation")
        rows.append({
            "virtualPath": target["virtualPath"],
            "name": Path(target["virtualPath"]).name,
            "role": target["role"],
            "observed": counters["observationsPublished"] == 1,
            "conflicted": counters["duplicateConflicts"] > 0,
            "unverified": counters["unverifiedPairs"] > 0,
            **counters,
        })
    expected_processed = sum(
        row["observationsPublished"] + row["duplicateIdentical"]
        + row["duplicateConflicts"] for row in rows
    )
    _require(processed == expected_processed,
             "progress.observationsProcessed: differs from completed target pairs")
    unresolved = [row for row in rows if row["role"] == "unresolved"]
    controls = [row for row in rows if row["role"] == "positiveControl"]
    return {
        "status": "provisional",
        "inputSetSha256": progress["inputSetSha256"],
        "observationsProcessed": processed,
        "unresolvedTotal": len(unresolved),
        "unresolvedObserved": sum(row["observed"] for row in unresolved),
        "observedNames": [row["name"] for row in unresolved if row["observed"]],
        "missingNames": [row["name"] for row in unresolved
                         if not row["observed"] and not row["unverified"]],
        "unverifiedNames": [row["name"] for row in rows if row["unverified"]],
        "conflictedNames": [row["name"] for row in rows if row["conflicted"]],
        "positiveControl": controls[0]["name"] if controls else None,
        "positiveControlObserved": controls[0]["observed"] if controls else None,
        "primaryLosses": losses,
        "primaryOverflow": overflow,
        "primaryCountersClean": not any(losses.values()) and not any(overflow.values()),
        "boundary": "Live progress is provisional; only the finalized receipt authenticates reader cursors and teardown.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("progress", type=Path)
    parser.add_argument("--native-context", type=Path,
                        default=context_audit.DEFAULT_CONTEXT)
    parser.add_argument("--target-contract", type=Path,
                        default=context_audit.TARGET_CONTRACT_PATH)
    args = parser.parse_args(argv)
    try:
        progress = json.loads(args.progress.read_text(encoding="utf-8"))
        native_context = json.loads(args.native_context.read_text(encoding="utf-8"))
        contract, contract_sha256 = receipt_verifier._load_json_with_sha256(
            args.target_contract, label="target-set contract"
        )
        summary = summarize_progress(
            progress, native_context=native_context,
            target_contract=contract, contract_sha256=contract_sha256,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError,
            receipt_verifier.ReceiptVerificationError) as exc:
        print(f"progress unavailable: {exc}", file=sys.stderr)
        return 1
    print(f"provisional: {summary['unresolvedObserved']}/{summary['unresolvedTotal']} unresolved sources observed")
    print("observed: " + (", ".join(summary["observedNames"]) or "none"))
    print("missing: " + (", ".join(summary["missingNames"]) or "none"))
    print("unverified: " + (", ".join(summary["unverifiedNames"]) or "none"))
    print("conflicts: " + (", ".join(summary["conflictedNames"]) or "none"))
    control = summary["positiveControl"]
    print(f"positive control: {control or 'none'}"
          f" ({'observed' if summary['positiveControlObserved'] else 'missing'})")
    print("primary counters: " + ("zero" if summary["primaryCountersClean"] else "nonzero"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
