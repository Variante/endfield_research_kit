"""Authenticate one current SkillData cursor target set before a live capture.

The existing single-target native context remains the provenance source for its
earlier receipt.  This context uses the same native observer validator and
unselected corpus gate, but binds every still-ambiguous logical source at once.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import skill_cursor_native_context as native
from scripts.game_data.memorypack import skill_cursor_receipt
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.skill-cursor-target-set-native-context.v1"
CONTRACT_SCHEMA = "endfield.skill-cursor-capture-target-set.v1"
TARGET_CONTRACT_PATH = CONTRACTS_DIR / "skill_cursor_capture_target_set.json"
DEFAULT_CORPUS = native.DEFAULT_CORPUS
DEFAULT_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_target_set_native_context_latest.json"
SKILL_PATH = re.compile(r"Data/Json/SkillData/[^/]+[.]json\Z")


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise native.NativeCursorContextError(
            "input-json-invalid", source=str(path), expected=f"valid {label} JSON object",
            actual=str(exc),
        ) from exc
    native._require(isinstance(value, dict), "input-json-shape-invalid", source=str(path),
                    expected=f"{label} object", actual=type(value).__name__)
    return value


def validate_target_set(corpus: Mapping[str, Any], contract: Mapping[str, Any],
                        *, source: str) -> list[dict[str, Any]]:
    """Require each reviewed source to match the immutable unselected basis."""
    native._require(
        contract.get("schema") == CONTRACT_SCHEMA
        and contract.get("status") == "selected-current-logical-source-set",
        "target-set-contract-invalid", source=source,
        expected={"schema": CONTRACT_SCHEMA,
                  "status": "selected-current-logical-source-set"},
        actual={key: contract.get(key) for key in ("schema", "status")},
    )
    identity = contract.get("sourceIdentitySetSha256")
    native._require(
        isinstance(identity, str) and native.HEX64.fullmatch(identity) is not None
        and identity == corpus.get("identitySetSha256"),
        "target-set-identity-mismatch", source=source,
        expected=corpus.get("identitySetSha256"), actual=identity,
    )
    limit = contract.get("captureMaxSourceBytes")
    native._require(type(limit) is int and limit == 131072,
                    "target-set-source-limit-invalid", source=source,
                    expected=131072, actual=limit)
    target_rows = contract.get("targets")
    native._require(isinstance(target_rows, list) and 0 < len(target_rows) <= 64,
                    "target-set-size-invalid", source=source,
                    expected="1..64 target objects", actual=native._bounded(target_rows))
    targets: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    for index, item in enumerate(target_rows):
        path = item.get("virtualPath") if isinstance(item, Mapping) else None
        length = item.get("length") if isinstance(item, Mapping) else None
        digest = item.get("logicalSha256") if isinstance(item, Mapping) else None
        role = item.get("role") if isinstance(item, Mapping) else None
        native._require(
            isinstance(path, str) and SKILL_PATH.fullmatch(path) is not None
            and type(length) is int and 0 < length <= limit
            and isinstance(digest, str) and native.HEX64.fullmatch(digest) is not None
            and digest == digest.upper() and role in ("unresolved", "positiveControl"),
            "target-set-row-invalid", source=f"{source}.targets[{index}]",
            expected="SkillData path, bounded byte length, uppercase SHA-256, reviewed role",
            actual=native._bounded(item),
        )
        native._require(path not in seen_paths and digest not in seen_hashes,
                        "target-set-duplicate-identity", source=f"{source}.targets[{index}]",
                        expected="unique path and copied-byte SHA-256",
                        actual={"virtualPath": path, "logicalSha256": digest})
        seen_paths.add(path)
        seen_hashes.add(digest)
        targets.append({"virtualPath": path, "length": length,
                        "logicalSha256": digest, "role": role})
    role_counts = {role: sum(item["role"] == role for item in targets)
                   for role in ("unresolved", "positiveControl")}
    native._require(role_counts["unresolved"] > 0 and role_counts["positiveControl"] == 1,
                    "target-set-role-count-invalid", source=source,
                    expected="at least one unresolved target and one positive control",
                    actual=role_counts)
    native._require(
        [row["virtualPath"] for row in targets]
        == sorted(row["virtualPath"] for row in targets),
        "target-set-order-invalid", source=source,
        expected="lexicographic virtualPath order",
        actual=[row["virtualPath"] for row in targets],
    )
    corpus_rows = corpus.get("files")
    native._require(isinstance(corpus_rows, list), "target-set-corpus-files-invalid",
                    source=source, expected="corpus files array",
                    actual=type(corpus_rows).__name__)
    by_path = {row.get("virtualPath"): row for row in corpus_rows
               if isinstance(row, Mapping) and isinstance(row.get("virtualPath"), str)}
    for target in targets:
        row = by_path.get(target["virtualPath"])
        actual = ({"length": row.get("length"),
                   "logicalSha256": row.get("logicalSha256"),
                   "boundaryClass": row.get("boundaryClass"),
                   "coverageStatus": row.get("coverageStatus"),
                   "blockName": row.get("blockName"),
                   "blockTypeValue": row.get("blockTypeValue")}
                  if isinstance(row, Mapping) else None)
        expected = {
            "length": target["length"],
            "logicalSha256": target["logicalSha256"],
            "boundaryClass": "ambiguous",
            "coverageStatus": "ambiguous-disjoint-independent-ranges",
            "blockName": "JsonData", "blockTypeValue": 19,
        }
        native._require(actual == expected, "target-set-current-row-mismatch",
                        source=target["virtualPath"], expected=expected, actual=actual)
    # The generic verifier joins copied source bytes by SHA-256, so every
    # target hash must select exactly one logical row in the full corpus.
    by_hash: dict[str, int] = {}
    for row in corpus_rows:
        digest = row.get("logicalSha256") if isinstance(row, Mapping) else None
        if isinstance(digest, str):
            by_hash[digest] = by_hash.get(digest, 0) + 1
    for target in targets:
        native._require(by_hash.get(target["logicalSha256"]) == 1,
                        "target-set-hash-join-ambiguous", source=target["virtualPath"],
                        expected=1, actual=by_hash.get(target["logicalSha256"], 0))
    return targets


def validate_selected_status_basis(
    contract: Mapping[str, Any], targets: list[Mapping[str, Any]],
    *, input_set: str, identity_set: str,
) -> dict[str, Any]:
    """Prove that unresolved roles cover every pre-capture ambiguous row."""
    recorded = contract.get("selectedStatusBasis")
    native._require(isinstance(recorded, Mapping),
                    "selected-status-reference-invalid", source="capture target-set contract",
                    expected="immutable report path, length, SHA-256", actual=native._bounded(recorded))
    relative = recorded.get("path")
    native._require(isinstance(relative, str), "selected-status-reference-invalid",
                    source="capture target-set contract", expected="relative reports path",
                    actual=relative)
    path = (REPO_ROOT / relative).resolve()
    report_dir = (REPO_ROOT / "reports/animestudio").resolve()
    native._require(path.is_relative_to(report_dir) and path != report_dir
                    and path.name.startswith("skilldata_target_set_selected_basis_")
                    and path.suffix == ".json",
                    "selected-status-path-invalid", source=str(path),
                    expected="immutable SkillData selected basis under reports/animestudio",
                    actual=relative)
    reference = native._file_reference(path)
    native._require((recorded.get("length"), recorded.get("sha256")) ==
                    (reference["length"], reference["sha256"]),
                    "selected-status-bytes-drift", source=str(path),
                    expected={"length": recorded.get("length"),
                              "sha256": recorded.get("sha256")},
                    actual={"length": reference["length"],
                            "sha256": reference["sha256"]})
    selected = _read_object(path, label="immutable selected SkillData status")
    native._require(
        selected.get("format") == "animestudio-skilldata-current-vfs-corpus"
        and selected.get("status") == "complete"
        and selected.get("publicationEligible") is True
        and selected.get("inputSetSha256") == input_set
        and selected.get("identitySetSha256") == identity_set,
        "selected-status-basis-mismatch", source=str(path),
        expected={"status": "complete", "inputSetSha256": input_set,
                  "identitySetSha256": identity_set},
        actual={key: selected.get(key) for key in
                ("status", "inputSetSha256", "identitySetSha256")},
    )
    try:
        native.verify_current_report_inputs(selected)
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        raise native.NativeCursorContextError(
            "selected-status-provenance-failed", source=str(path),
            expected="current selected report source/tool provenance",
            actual=getattr(exc, "diagnostic", str(exc)),
        ) from exc
    rows = selected.get("files")
    native._require(isinstance(rows, list), "selected-status-files-invalid",
                    source=str(path), expected="files array", actual=type(rows).__name__)
    unresolved = sorted(({
        "virtualPath": row.get("virtualPath"),
        "length": row.get("length"),
        "logicalSha256": row.get("logicalSha256"),
    } for row in rows if isinstance(row, Mapping)
        and row.get("boundaryClass") == "ambiguous"),
        key=lambda row: str(row["virtualPath"]))
    contracted = [{key: target[key] for key in ("virtualPath", "length", "logicalSha256")}
                  for target in targets if target["role"] == "unresolved"]
    native._require(unresolved == contracted, "selected-status-unresolved-set-mismatch",
                    source=str(path), expected=native._bounded(unresolved),
                    actual=native._bounded(contracted))
    control = next(target for target in targets if target["role"] == "positiveControl")
    matches = [row for row in rows if isinstance(row, Mapping)
               and row.get("virtualPath") == control["virtualPath"]]
    actual_control = ({"length": matches[0].get("length"),
                       "logicalSha256": matches[0].get("logicalSha256"),
                       "boundaryClass": matches[0].get("boundaryClass"),
                       "wholeSchemaExact": matches[0].get("wholeSchemaExact")}
                      if len(matches) == 1 else None)
    expected_control = {"length": control["length"],
                        "logicalSha256": control["logicalSha256"],
                        "boundaryClass": "exact-closed", "wholeSchemaExact": True}
    native._require(actual_control == expected_control,
                    "selected-status-control-mismatch", source=control["virtualPath"],
                    expected=expected_control, actual=actual_control)
    return reference


def target_set_binding_bytes(target_sources: list[Mapping[str, Any]]) -> bytes:
    return ";".join(f"{row['sourceLength']}:{row['sourceSha256']}"
                    for row in target_sources).encode("ascii")


def target_set_binding_sha256(target_sources: list[Mapping[str, Any]]) -> str:
    return hashlib.sha256(target_set_binding_bytes(target_sources)).hexdigest().upper()


def audit_native_only(corpus_path: Path = DEFAULT_CORPUS,
                      target_contract_path: Path = TARGET_CONTRACT_PATH) -> dict[str, Any]:
    """Recheck the current corpus, reviewed targets and selected native build."""
    corpus_path = Path(corpus_path).resolve()
    contract_path = native.CONTRACT_PATH.resolve()
    target_contract_path = Path(target_contract_path).resolve()
    corpus_reference = native._file_reference(corpus_path)
    contract_reference = native._file_reference(contract_path)
    target_contract_reference = native._file_reference(target_contract_path)
    auditor_reference = native._file_reference(Path(__file__))
    corpus = _read_object(corpus_path, label="SkillData corpus")
    contract = _read_object(contract_path, label="native observer contract")
    target_contract = _read_object(target_contract_path, label="capture target-set contract")
    input_set, file_count = native.validate_unselected_basis(corpus, source=str(corpus_path))
    targets = validate_target_set(corpus, target_contract, source=str(target_contract_path))
    identity_set = corpus["identitySetSha256"]
    try:
        native.verify_current_report_inputs(corpus)
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        raise native.NativeCursorContextError(
            "basis-provenance-failed", source=str(corpus_path),
            expected="current VFS/source/parser provenance",
            actual=getattr(exc, "diagnostic", str(exc)),
        ) from exc
    expected_native = contract.get("nativeInputs")
    native._require(
        isinstance(expected_native, Mapping)
        and all(isinstance(expected_native.get(name), str)
                and native.HEX64.fullmatch(expected_native[name]) is not None
                for name in ("GameAssembly.dll", "global-metadata.dat"))
        and target_contract.get("nativeInputs") == expected_native,
        "target-set-native-pins-mismatch", source=str(target_contract_path),
        expected=expected_native, actual=target_contract.get("nativeInputs"),
    )
    gate = native.check_installed_native_inputs(
        expected_native["GameAssembly.dll"], expected_native["global-metadata.dat"]
    )
    native._require(gate.status == "validated", "native-inputs-unavailable",
                    source=str(gate.gameassembly), expected="selected native build",
                    actual={"status": gate.status, "detail": gate.detail})
    try:
        image = native.NativeImage(gate.gameassembly, gate.metadata,
                                   label="skill-cursor-target-set-native-only")
        native_counts = native.validate_native_observer(contract, image,
                                                        source=str(contract_path))
    except native.NativeCursorContextError:
        raise
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise native.NativeCursorContextError(
            "native-observer-validation-failed", source=str(contract_path),
            expected="exact method, body and callsite validation", actual=str(exc),
        ) from exc
    # Each source report is around 1.5 GB in JSON.  Release the unselected
    # parse before opening the independent immutable selected-status snapshot.
    del corpus
    gc.collect()
    selected_reference = validate_selected_status_basis(
        target_contract, targets, input_set=input_set, identity_set=identity_set
    )
    observer = {
        "status": "exact-static-callsite-vector",
        "fieldCallsites": contract["fieldCallsites"],
        "inlineField": contract["inlineField"],
        "actionGroupChildCallsites": contract["actionGroupChildCallsites"],
        "sourceLengths": contract["receiptVerifierSourceLengths"],
        "boundary": "Native-only observer coordinates; source lengths are prior receipt compatibility values, not target-set coverage.",
    }
    target_sources = [
        {"sourceLength": row["length"], "sourceSha256": row["logicalSha256"]}
        for row in targets
    ]
    return {
        "schema": SCHEMA,
        "schemaVersion": 1,
        "status": "native-only-unselected",
        "inputSetSha256": input_set,
        "nativeInputs": {
            "gameassembly": str(gate.gameassembly.resolve()),
            "gameassemblySha256": gate.gameassembly_sha256.upper(),
            "metadata": str(gate.metadata.resolve()),
            "metadataSha256": gate.metadata_sha256.upper(),
        },
        "corpusReference": {**corpus_reference, "inputSetSha256": input_set,
                            "filesSelected": file_count, "terminalSelections": 0},
        "contractReference": contract_reference,
        "captureTargetSetContractReference": target_contract_reference,
        "selectedStatusReportReference": selected_reference,
        "captureTargetSet": targets,
        "unresolvedTargetCount": sum(item["role"] == "unresolved" for item in targets),
        "positiveControlCount": sum(item["role"] == "positiveControl" for item in targets),
        "targetSources": target_sources,
        "targetSetBindingSha256": target_set_binding_sha256(target_sources),
        "captureMaxSourceBytes": target_contract["captureMaxSourceBytes"],
        "auditorReference": auditor_reference,
        "nativeValidation": {"status": "validated", **native_counts},
        "selectedSkillDataReaderOrder": {
            "status": "native-only-unselected",
            "runtimeCursorObserver": observer,
        },
        "evidenceBoundary": (
            "The unselected SkillData corpus has current source and parser provenance; "
            "the immutable selected-status report proves that the reviewed unresolved "
            "source set is exactly the pre-capture ambiguous set. "
            "Selected native files, reader methods, body hashes and observer callsites "
            "are validated. No live source load or cursor is inferred."
        ),
    }


def preflight_native_only(corpus_path: Path = DEFAULT_CORPUS,
                          context_path: Path = DEFAULT_CONTEXT,
                          target_contract_path: Path = TARGET_CONTRACT_PATH) -> dict[str, Any]:
    expected = audit_native_only(corpus_path, target_contract_path)
    actual = _read_object(Path(context_path), label="target-set native context")
    difference = native._first_difference(expected, actual, str(context_path))
    native._require(difference is None, "context-replay-mismatch",
                    source=difference[0] if difference else str(context_path),
                    expected=difference[1] if difference else "current audited context",
                    actual=difference[2] if difference else "matching")
    try:
        input_set = skill_cursor_receipt.preflight_skilldata_corpus(
            corpus_report_path=Path(corpus_path),
            native_context_path=Path(context_path),
        )
    except skill_cursor_receipt.ReceiptVerificationError as exc:
        raise native.NativeCursorContextError(
            "receipt-preflight-failed", source=str(context_path),
            expected="matching current corpus and native observer vector", actual=str(exc),
        ) from exc
    native._require(input_set == expected["inputSetSha256"], "receipt-input-set-drift",
                    source=str(context_path), expected=expected["inputSetSha256"],
                    actual=input_set)
    return {"inputSetSha256": input_set,
            "targetSources": expected["targetSources"],
            "targetSetBindingSha256": expected["targetSetBindingSha256"],
            "captureMaxSourceBytes": expected["captureMaxSourceBytes"]}


def write_capture_binding(binding: Mapping[str, Any]) -> Path:
    """Write a content-addressed ASCII binding without replacing prior bytes."""
    data = target_set_binding_bytes(binding["targetSources"])
    digest = hashlib.sha256(data).hexdigest().upper()
    native._require(digest == binding.get("targetSetBindingSha256"),
                    "target-set-binding-drift", source="capture binding",
                    expected=binding.get("targetSetBindingSha256"), actual=digest)
    path = REPO_ROOT / "reports/animestudio" / (
        f"skilldata_cursor_target_set_binding_{digest[:16]}.txt"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        native._require(path.read_bytes() == data, "target-set-binding-file-drift",
                        source=str(path), expected=digest,
                        actual=hashlib.sha256(path.read_bytes()).hexdigest().upper())
    else:
        try:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
        except FileExistsError:
            native._require(path.read_bytes() == data, "target-set-binding-file-drift",
                            source=str(path), expected=digest,
                            actual=hashlib.sha256(path.read_bytes()).hexdigest().upper())
    return path.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--target-contract", type=Path, default=TARGET_CONTRACT_PATH)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--output", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--capture-binding", action="store_true",
                        help="with --preflight, print JSON input set and targetSources")
    parser.add_argument("--capture-binding-batch", action="store_true",
                        help="with --preflight, print inputSet|absolutePath|bindingSha256")
    args = parser.parse_args(argv)
    if args.capture_binding and args.capture_binding_batch:
        parser.error("choose one capture-binding output format")
    if (args.capture_binding or args.capture_binding_batch) and not args.preflight:
        parser.error("capture-binding output requires --preflight")
    try:
        if args.preflight:
            binding = preflight_native_only(args.corpus_report, args.native_context,
                                            args.target_contract)
            if args.capture_binding or args.capture_binding_batch:
                path = write_capture_binding(binding)
                if args.capture_binding_batch:
                    print("|".join((binding["inputSetSha256"], path.as_posix(),
                                    binding["targetSetBindingSha256"])))
                else:
                    print(json.dumps({
                        "inputSetSha256": binding["inputSetSha256"],
                        "bindingFilePath": path.as_posix(),
                        "bindingSha256": binding["targetSetBindingSha256"],
                        "targetCount": len(binding["targetSources"]),
                    }, separators=(",", ":")))
            else:
                print(binding["inputSetSha256"])
        else:
            context = audit_native_only(args.corpus_report, args.target_contract)
            native._atomic_json(args.output, context)
            print(json.dumps({"status": context["status"],
                              "targetCount": len(context["targetSources"]),
                              "inputSetSha256": context["inputSetSha256"],
                              "output": str(args.output)}))
    except native.NativeCursorContextError as exc:
        print(json.dumps({"status": "failed", "diagnostic": exc.diagnostic},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
