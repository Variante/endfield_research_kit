"""Source-bound Seraph SkillData cursor preflight and v3 receipt verification.

The existing target-set recorder can capture a single 9,756-byte target by
copied-byte SHA-256. This tool leaves the older single-target observer and
Wulfa receipt contracts intact. A valid receipt selects only this source's
executed terminal cursor; whole-file publication is a separate gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import skill_cursor_native_context as observer
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.memorypack import skill_cursor_receipt as cursor
from scripts.game_data.memorypack.corpus_gate import _fingerprint, verify_current_report_inputs
from scripts.game_data.memorypack.skill_timeline_dispel import validate_current_native_contract
from scripts.repo_paths import REPO_ROOT


TARGET_CONTRACT = CONTRACTS_DIR / "skill_cursor_capture_seraph_ultimate_target.json"
NATIVE_CONTRACT = CONTRACTS_DIR / "skill_cursor_observer_native.json"
DEFAULT_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_seraph_ultimate_context_latest.json"
DEFAULT_BINDING = REPO_ROOT / "reports/animestudio/skill_cursor_seraph_ultimate_binding.txt"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_seraph_ultimate_verification_latest.json"
WULFA_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_native_context_wulfa_ultimate_latest.json"
CONTRACT_SCHEMA = "endfield.skill-cursor-single-target-set.v1"
CONTEXT_SCHEMA = "endfield.skill-cursor-seraph-native-context.v1"
VERIFY_SCHEMA = "endfield.skill-cursor-seraph-verification.v1"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-seraph:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_bytes())
    _require(isinstance(value, dict), f"{path}:root-shape")
    return value


def _inside_repo(relative: str) -> Path:
    _require(isinstance(relative, str) and relative != "", "relative-path-shape")
    path = (REPO_ROOT / relative).resolve()
    _require(path.is_relative_to(REPO_ROOT) and path.is_file(),
             f"source-path-missing:{relative}")
    return path


def _evidence(target_contract_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    contract, _ = read_reviewed_contract(
        target_contract_path, schema=CONTRACT_SCHEMA,
        status="selected-current-logical-source", label="skill-cursor-seraph",
    )
    target = contract.get("target")
    scoped = contract.get("scopedEvidence")
    _require(isinstance(target, dict) and isinstance(scoped, dict), "target-shape")
    _require(contract.get("captureTransport") == "single-source-v3-target-set"
             and contract.get("captureMaxSourceBytes") == 131072,
             "transport-shape")
    basis_path = _inside_repo(scoped["basis"])
    source_path = _inside_repo(scoped["source"])
    control_path = _inside_repo(scoped["controlReport"])
    basis = _load(basis_path)
    path = target.get("virtualPath")
    _require(isinstance(path, str)
             and path.startswith("Data/Json/SkillData/")
             and path.endswith(".json")
             and basis.get("status") == "partial"
             and basis.get("publicationEligible") is False
             and basis.get("targetedVirtualPaths") == [path]
             and len(basis.get("files", [])) == 1
             and basis["files"][0].get("virtualPath") == path,
             "basis-target-scope")
    verify_current_report_inputs(basis, allow_partial=True)
    source = source_path.read_bytes()
    digest = hashlib.sha256(source).hexdigest().upper()
    row = basis["files"][0]
    _require((len(source), digest) == (target.get("length"), target.get("logicalSha256"))
             == (row.get("length"), row.get("logicalSha256"))
             and len(source) <= contract["captureMaxSourceBytes"],
             "current-source-identity")
    _require(row.get("timelineSharedSequenceStopReason")
             == "skillTimelineSharedSequence.timeline[17]:route=0x009F:not-contracted",
             "first-stop-drift")
    controls = _load(control_path)
    wulfa = _load(WULFA_CONTEXT)
    old_reference = wulfa.get("scopedTargetProvenance", {}).get("controlsReference")
    _require(controls.get("inputSetSha256") == basis.get("inputSetSha256")
             and controls.get("status") == "partial"
             and len(controls.get("files", [])) == 3
             and isinstance(old_reference, Mapping)
             and (old_reference.get("length"), old_reference.get("sha256"))
             == (_fingerprint(control_path)["length"], _fingerprint(control_path)["sha256"]),
             "prior-control-reference-drift")
    return contract, basis, basis_path, source_path


def _context(target_contract_path: Path = TARGET_CONTRACT) -> dict[str, Any]:
    target_contract_path = Path(target_contract_path).resolve()
    contract, basis, basis_path, source_path = _evidence(target_contract_path)
    target = contract["target"]
    observer_contract = _load(NATIVE_CONTRACT)
    expected = observer_contract.get("nativeInputs")
    _require(contract.get("nativeInputs") == expected, "native-contract-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    _require(gate.status == "validated", f"native-inputs:{gate.status}:{gate.detail}")
    image = NativeImage(gate.gameassembly, gate.metadata, label="skill-cursor-seraph")
    counts = observer.validate_native_observer(
        observer_contract, image, source=str(NATIVE_CONTRACT),
    )
    route = validate_current_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    _require(route.get("status") == "validated" and route.get("unionTag") == 0x9F,
             "dispel-native-drift")
    binding = f"{target['length']}:{target['logicalSha256']}".encode("ascii")
    return {
        "schema": CONTEXT_SCHEMA, "status": "native-only-unselected",
        "publicationEligible": False,
        "inputSetSha256": basis["inputSetSha256"],
        "target": target,
        "targetSources": [{"sourceLength": target["length"],
                           "sourceSha256": target["logicalSha256"]}],
        "targetSetBindingSha256": hashlib.sha256(binding).hexdigest().upper(),
        "bindingText": binding.decode("ascii"),
        "nativeInputs": {"gameAssemblySha256": gate.gameassembly_sha256.upper(),
                         "metadataSha256": gate.metadata_sha256.upper()},
        "nativeObserverValidation": {"status": "validated", **counts},
        "dispelNativeValidation": {
            key: route[key] for key in ("status", "unionTag", "sourceReadCount",
                                           "nestedContextCount", "codeWindowCount")
        },
        "provenance": {
            "targetContract": _fingerprint(target_contract_path),
            "observerContract": _fingerprint(NATIVE_CONTRACT),
            "basis": _fingerprint(basis_path),
            "source": _fingerprint(source_path),
            "priorControls": _fingerprint(_inside_repo(contract["scopedEvidence"]["controlReport"])),
            "priorControlContext": _fingerprint(WULFA_CONTEXT),
        },
        "evidenceBoundary": (
            "One exact current VFS source and selected native observer/DispelAction reader. "
            "The three controls are reused through their prior authenticated report reference. "
            "No Seraph terminal is selected until an executed cursor receipt is verified."
        ),
    }


def build_context(*, target_contract_path: Path = TARGET_CONTRACT,
                  context_path: Path = DEFAULT_CONTEXT,
                  binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    result = _context(target_contract_path)
    context_path = Path(context_path)
    binding_path = Path(binding_path)
    context_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.write_bytes(result["bindingText"].encode("ascii"))
    context_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    return result


def preflight(*, target_contract_path: Path = TARGET_CONTRACT,
              context_path: Path = DEFAULT_CONTEXT,
              binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    expected = _context(target_contract_path)
    actual = _load(context_path)
    _require(actual == expected, "context-replay-mismatch")
    binding = Path(binding_path).read_bytes()
    _require(binding == expected["bindingText"].encode("ascii")
             and hashlib.sha256(binding).hexdigest().upper()
             == expected["targetSetBindingSha256"],
             "binding-bytes-drift")
    return expected


def verify_receipt(receipt_path: Path, *, target_contract_path: Path = TARGET_CONTRACT,
                   context_path: Path = DEFAULT_CONTEXT,
                   binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    context = preflight(target_contract_path=target_contract_path,
                        context_path=context_path, binding_path=binding_path)
    receipt_path = Path(receipt_path)
    receipt, receipt_digest = cursor._load_json_with_sha256(
        receipt_path, label="Seraph capture receipt",
    )
    _require(receipt.get("schema") == "endfieldCapture.skillDataCursorCapture.v3"
             and receipt.get("targetSources") == context["targetSources"]
             and receipt.get("targetSetBindingSha256") == context["targetSetBindingSha256"]
             and "targetSourceSha256" not in receipt,
             "receipt-target-binding")
    adapted = dict(receipt)
    adapted["schema"] = cursor.SCHEMA
    input_set, game_hash, metadata_hash, _unsupported = cursor._require_capture_gates(adapted)
    _require(input_set == context["inputSetSha256"]
             and (game_hash, metadata_hash) ==
             (context["nativeInputs"]["gameAssemblySha256"],
              context["nativeInputs"]["metadataSha256"]),
             "receipt-current-inputs")
    target = context["target"]
    observations = receipt["observations"]
    _require(len(observations) == 1, "receipt-observation-count")
    source, digest = cursor._decode_source(observations[0], 0)
    _require((len(source), digest) == (target["length"], target["logicalSha256"]),
             "receipt-copied-source")
    from scripts.game_data.memorypack.skill_cursor_capture_target_set import _target_stats
    stats = _target_stats(receipt, context["targetSources"], {digest: 1})
    _require(len(stats) == 1 and stats[0]["observationsPublished"] == 1
             and stats[0]["duplicateConflicts"] == 0
             and stats[0]["unverifiedPairs"] == 0
             and receipt.get("pendingRecords") == 0
             and receipt.get("progressPublicationFailures") == 0,
             "receipt-local-transport")
    processed = 1 + stats[0]["duplicateIdentical"]
    _require(receipt.get("observationsProcessed") == processed
             and receipt.get("completedPairs") == processed
             and receipt.get("publishedRecords") == processed,
             "receipt-processed-counter-reconciliation")
    basis = _load(_inside_repo(_load(target_contract_path)["scopedEvidence"]["basis"]))
    row = cursor._verify_observation(
        observations[0], 0, basis["files"], input_set,
    )
    _require(row.get("boundaryClass") == "exact-closed"
             and row.get("parserCursor") == target["length"]
             and (row.get("logicalPath"), row.get("logicalSha256"),
                  row.get("hardLimit"))
             == (target["virtualPath"], target["logicalSha256"], target["length"]),
             "receipt-cursor-not-exact-closed")
    return {
        "schema": VERIFY_SCHEMA, "status": "exact-closed-one-source",
        "publicationEligible": False,
        "wholeSchemaExact": False,
        "inputSetSha256": input_set,
        "target": target,
        "row": row,
        "provenance": {"receipt": _fingerprint(receipt_path),
                       "context": _fingerprint(context_path),
                       "basis": context["provenance"]["basis"]},
        "evidenceBoundary": (
            "Executed 47-field and two ActionGroup-child cursor vector for the exact copied "
            "Seraph source. This selects the terminal and reaches EOF; the cursor report alone "
            "leaves the populated ActionGroup interior opaque and cannot publish whole schema."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", nargs="?", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--capture-binding-batch", action="store_true")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--target-contract", type=Path, default=TARGET_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            _require(args.receipt is None, "preflight-receipt-unexpected")
            result = preflight(target_contract_path=args.target_contract,
                               context_path=args.context, binding_path=args.binding)
            if args.capture_binding_batch:
                print("|".join((result["inputSetSha256"],
                                str(args.binding.resolve()),
                                result["targetSetBindingSha256"])))
            else:
                print(json.dumps({"status": "validated",
                                  "target": result["target"],
                                  "context": str(args.context)}, ensure_ascii=False))
            return 0
        if args.receipt is None:
            result = build_context(target_contract_path=args.target_contract,
                                   context_path=args.context, binding_path=args.binding)
            print(json.dumps({"status": result["status"],
                              "target": result["target"],
                              "context": str(args.context)}, ensure_ascii=False))
            return 0
        result = verify_receipt(args.receipt, target_contract_path=args.target_contract,
                                context_path=args.context, binding_path=args.binding)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"],
                          "candidate": result["row"].get("candidate"),
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError,
            cursor.ReceiptVerificationError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
