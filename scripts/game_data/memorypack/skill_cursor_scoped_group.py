"""Prepare and verify an exact, newly selected SkillData v3 cursor target group.

The reviewed contract names only unresolved logical sources. The tool binds
their current VFS and local copied bytes to the selected native observer and
the existing v3 target-set transport. Every requested target must appear in a
loss-free receipt. This establishes top-level executed cursors only; nested
ActionGroup and route-specific whole-schema claims need separate validators.

Contract v1 is a reviewed JSON under ``scripts/game_data/contracts`` with
``status=selected-current-logical-sources``, selected observer ``nativeInputs``,
``captureTransport=v3-target-set``, ``captureMaxSourceBytes=131072``,
``scopedEvidence.basis`` and sorted ``targets``. Each target has
``virtualPath``, ``length``, ``logicalSha256`` and its exact local ``source``.

Contract v2 accepts one previously checked single-source report per target.
It does not re-stream or rehash their unchanged VFS chunks during capture
preparation. The runtime receipt must copy and close every reviewed source;
the result remains source-scoped and nonpublishable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
from scripts.game_data.memorypack.skill_cursor_capture_target_set import (
    LOSS_COUNTERS,
    OVERFLOW_COUNTERS,
    _target_stats,
)
from scripts.repo_paths import REPO_ROOT


CONTRACT_SCHEMA = "endfield.skill-cursor-scoped-group.v1"
CONTRACT_SCHEMA_V2 = "endfield.skill-cursor-scoped-group.v2"
CONTEXT_SCHEMA = "endfield.skill-cursor-scoped-group-context.v1"
CONTEXT_SCHEMA_V2 = "endfield.skill-cursor-scoped-group-context.v2"
VERIFY_SCHEMA = "endfield.skill-cursor-scoped-group-verification.v1"
VERIFY_SCHEMA_V2 = "endfield.skill-cursor-scoped-group-verification.v2"
NATIVE_CONTRACT = CONTRACTS_DIR / "skill_cursor_observer_native.json"
DEFAULT_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_scoped_group_context_latest.json"
DEFAULT_BINDING = REPO_ROOT / "reports/animestudio/skill_cursor_scoped_group_binding.txt"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_scoped_group_verification_latest.json"
MAX_TARGETS = 32
MAX_SOURCE_BYTES = 131072
MAX_BINDING_BYTES = 4095
HEX64 = re.compile(r"[0-9A-F]{64}\Z")
SKILL_PATH = re.compile(r"Data/Json/SkillData/[^/]+[.]json\Z")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-scoped-group:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_bytes())
    _require(isinstance(value, dict), f"{path}:root-shape")
    return value


def _inside_repo(relative: str) -> Path:
    _require(isinstance(relative, str) and relative != "" and not Path(relative).is_absolute(),
             "relative-path-shape")
    path = (REPO_ROOT / relative).resolve()
    _require(path.is_relative_to(REPO_ROOT) and path.is_file(),
             f"repo-file-missing:{relative}")
    return path


def _selected_evidence(contract_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path, list[Path]]:
    contract_path = Path(contract_path).resolve()
    _require(contract_path.parent == CONTRACTS_DIR.resolve()
             and contract_path.suffix == ".json",
             "contract-outside-reviewed-directory")
    contract, _ = read_reviewed_contract(
        contract_path, schema=CONTRACT_SCHEMA,
        status="selected-current-logical-sources", label="skill-cursor-scoped-group",
    )
    native = contract.get("nativeInputs")
    scope = contract.get("scopedEvidence")
    targets = contract.get("targets")
    _require(isinstance(native, Mapping) and isinstance(scope, Mapping)
             and isinstance(targets, list) and 1 <= len(targets) <= MAX_TARGETS
             and contract.get("captureTransport") == "v3-target-set"
             and contract.get("captureMaxSourceBytes") == MAX_SOURCE_BYTES,
             "contract-shape-or-cap")
    basis_path = _inside_repo(scope.get("basis"))
    basis = _load(basis_path)
    paths: list[str] = []
    digests: set[str] = set()
    source_paths: list[Path] = []
    for index, target in enumerate(targets):
        _require(isinstance(target, Mapping), f"target[{index}]:shape")
        virtual = target.get("virtualPath")
        length = target.get("length")
        digest = target.get("logicalSha256")
        local = target.get("source")
        _require(isinstance(virtual, str) and SKILL_PATH.fullmatch(virtual) is not None
                 and type(length) is int and 0 < length <= MAX_SOURCE_BYTES
                 and isinstance(digest, str) and HEX64.fullmatch(digest) is not None
                 and isinstance(local, str)
                 and local == "export_full/game/Json/SkillData/" + virtual.rsplit("/", 1)[1],
                 f"target[{index}]:identity-shape")
        _require(digest not in digests, f"target[{index}]:duplicate-source-sha256")
        digests.add(digest)
        paths.append(virtual)
        source_path = _inside_repo(local)
        source = source_path.read_bytes()
        _require((len(source), hashlib.sha256(source).hexdigest().upper())
                 == (length, digest), f"target[{index}]:local-source-drift")
        source_paths.append(source_path)
    _require(paths == sorted(set(paths)), "target-path-order-or-duplicate")
    _require(basis.get("status") == "partial"
             and basis.get("publicationEligible") is False
             and basis.get("targetedVirtualPaths") == paths,
             "basis-target-scope")
    rows = basis.get("files")
    _require(isinstance(rows, list) and len(rows) == len(targets)
             and [row.get("virtualPath") if isinstance(row, Mapping) else None
                  for row in rows] == paths,
             "basis-file-scope")
    verify_current_report_inputs(basis, allow_partial=True)
    for index, (target, row) in enumerate(zip(targets, rows)):
        _require((row.get("length"), row.get("logicalSha256"))
                 == (target["length"], target["logicalSha256"])
                 and row.get("wholeSchemaExact") is False
                 and row.get("blockName") == "JsonData"
                 and row.get("blockTypeValue") == 19,
                 f"basis-target[{index}]:source-or-unresolved-drift")
    binding = ";".join(f"{target['length']}:{target['logicalSha256']}"
                       for target in targets).encode("ascii")
    _require(0 < len(binding) <= MAX_BINDING_BYTES, "binding-length-cap")
    return contract, basis, basis_path, source_paths


def _selected_saved_evidence(contract_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path], list[Path]]:
    """Bind distinct saved one-source reports without checking unchanged chunks again."""
    contract_path = Path(contract_path).resolve()
    _require(contract_path.parent == CONTRACTS_DIR.resolve()
             and contract_path.suffix == ".json", "contract-outside-reviewed-directory")
    contract, _ = read_reviewed_contract(
        contract_path, schema=CONTRACT_SCHEMA_V2,
        status="selected-saved-logical-sources", label="skill-cursor-scoped-group",
    )
    native = contract.get("nativeInputs")
    scope = contract.get("scopedEvidence")
    targets = contract.get("targets")
    _require(isinstance(native, Mapping) and isinstance(scope, Mapping)
             and isinstance(targets, list) and 1 <= len(targets) <= MAX_TARGETS
             and contract.get("captureTransport") == "v3-target-set"
             and contract.get("captureMaxSourceBytes") == MAX_SOURCE_BYTES,
             "contract-shape-or-cap")
    basis_names = scope.get("bases")
    _require(isinstance(basis_names, list) and len(basis_names) == len(targets)
             and all(isinstance(name, str) for name in basis_names)
             and len(set(basis_names)) == len(basis_names), "basis-count-or-duplicate")
    paths: list[str] = []
    digests: set[str] = set()
    source_paths: list[Path] = []
    basis_paths: list[Path] = []
    bases: list[dict[str, Any]] = []
    input_set: str | None = None
    for index, (target, basis_name) in enumerate(zip(targets, basis_names)):
        _require(isinstance(target, Mapping), f"target[{index}]:shape")
        virtual, length = target.get("virtualPath"), target.get("length")
        digest, local = target.get("logicalSha256"), target.get("source")
        _require(isinstance(virtual, str) and SKILL_PATH.fullmatch(virtual) is not None
                 and type(length) is int and 0 < length <= MAX_SOURCE_BYTES
                 and isinstance(digest, str) and HEX64.fullmatch(digest) is not None
                 and isinstance(local, str)
                 and local == "export_full/game/Json/SkillData/" + virtual.rsplit("/", 1)[1],
                 f"target[{index}]:identity-shape")
        _require(digest not in digests, f"target[{index}]:duplicate-source-sha256")
        paths.append(virtual)
        digests.add(digest)
        source_path = _inside_repo(local)
        source = source_path.read_bytes()
        _require((len(source), hashlib.sha256(source).hexdigest().upper()) == (length, digest),
                 f"target[{index}]:local-source-drift")
        source_paths.append(source_path)
        basis_path = _inside_repo(basis_name)
        basis = _load(basis_path)
        current_input = basis.get("inputSetSha256")
        _require(isinstance(current_input, str) and HEX64.fullmatch(current_input) is not None
                 and (input_set is None or input_set == current_input),
                 f"basis[{index}]:input-set-drift")
        input_set = current_input
        rows = basis.get("files")
        _require(basis.get("format") == "animestudio-skilldata-current-vfs-corpus"
                 and basis.get("schemaVersion") == 1
                 and basis.get("status") == "partial"
                 and basis.get("publicationEligible") is False
                 and basis.get("targetedVirtualPaths") == [virtual]
                 and isinstance(basis.get("provenance"), Mapping)
                 and isinstance(rows, list) and len(rows) == 1
                 and isinstance(rows[0], Mapping), f"basis[{index}]:scope")
        row = rows[0]
        _require((row.get("virtualPath"), row.get("length"), row.get("logicalSha256"),
                  row.get("wholeSchemaExact"), row.get("blockName"), row.get("blockTypeValue"))
                 == (virtual, length, digest, False, "JsonData", 19),
                 f"basis[{index}]:source-or-unresolved-drift")
        bases.append(basis)
        basis_paths.append(basis_path)
    _require(paths == sorted(set(paths)), "target-path-order-or-duplicate")
    return contract, bases, basis_paths, source_paths


def _validated_observer(contract: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    observer_contract = _load(NATIVE_CONTRACT)
    expected = observer_contract.get("nativeInputs")
    _require(contract.get("nativeInputs") == expected, "observer-native-input-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    _require(gate.status == "validated", f"native-inputs:{gate.status}:{gate.detail}")
    image = NativeImage(gate.gameassembly, gate.metadata, label="skill-cursor-scoped-group")
    counts = observer.validate_native_observer(
        observer_contract, image, source=str(NATIVE_CONTRACT),
    )
    return gate, counts


def _context(contract_path: Path) -> dict[str, Any]:
    contract_path = Path(contract_path).resolve()
    if contract_path.is_file() and _load(contract_path).get("schema") == CONTRACT_SCHEMA_V2:
        contract, bases, basis_paths, source_paths = _selected_saved_evidence(contract_path)
        gate, observer_counts = _validated_observer(contract)
        targets = contract["targets"]
        target_sources = [{"sourceLength": target["length"],
                           "sourceSha256": target["logicalSha256"]}
                          for target in targets]
        binding = ";".join(f"{row['sourceLength']}:{row['sourceSha256']}"
                           for row in target_sources).encode("ascii")
        return {
            "schema": CONTEXT_SCHEMA_V2, "status": "native-only-unselected",
            "publicationEligible": False,
            "inputSetSha256": bases[0]["inputSetSha256"],
            "targets": targets, "targetSources": target_sources,
            "targetSetBindingSha256": hashlib.sha256(binding).hexdigest().upper(),
            "bindingText": binding.decode("ascii"),
            "captureMaxSourceBytes": MAX_SOURCE_BYTES,
            "nativeInputs": {"gameAssemblySha256": gate.gameassembly_sha256.upper(),
                             "metadataSha256": gate.metadata_sha256.upper()},
            "nativeObserverValidation": {"status": "validated", **observer_counts},
            "provenance": {"contract": _fingerprint(contract_path),
                           "observerContract": _fingerprint(NATIVE_CONTRACT),
                           "bases": [_fingerprint(path) for path in basis_paths],
                           "sources": [_fingerprint(path) for path in source_paths]},
            "evidenceBoundary": (
                "Saved single-source VFS reports and copied bytes bind the selected "
                "native cursor observer. Preparation does not recheck unchanged "
                "physical chunks. The runtime receipt must prove each source byte "
                "identity and EOF cursor; current family publication remains separate."
            ),
        }
    contract, basis, basis_path, source_paths = _selected_evidence(contract_path)
    gate, observer_counts = _validated_observer(contract)
    targets = contract["targets"]
    target_sources = [{"sourceLength": target["length"],
                       "sourceSha256": target["logicalSha256"]}
                      for target in targets]
    binding = ";".join(f"{row['sourceLength']}:{row['sourceSha256']}"
                       for row in target_sources).encode("ascii")
    return {
        "schema": CONTEXT_SCHEMA, "status": "native-only-unselected",
        "publicationEligible": False,
        "inputSetSha256": basis["inputSetSha256"],
        "targets": targets,
        "targetSources": target_sources,
        "targetSetBindingSha256": hashlib.sha256(binding).hexdigest().upper(),
        "bindingText": binding.decode("ascii"),
        "captureMaxSourceBytes": MAX_SOURCE_BYTES,
        "nativeInputs": {"gameAssemblySha256": gate.gameassembly_sha256.upper(),
                         "metadataSha256": gate.metadata_sha256.upper()},
        "nativeObserverValidation": {"status": "validated", **observer_counts},
        "provenance": {
            "contract": _fingerprint(contract_path),
            "observerContract": _fingerprint(NATIVE_CONTRACT),
            "basis": _fingerprint(basis_path),
            "sources": [_fingerprint(path) for path in source_paths],
        },
        "evidenceBoundary": (
            "Exact scoped VFS and local copied-source identities plus selected native "
            "SkillData cursor observer. No previous controls are restreamed or bound; "
            "no route-specific ActionGroup or whole-schema claim is made."
        ),
    }


def build_context(*, contract_path: Path, context_path: Path = DEFAULT_CONTEXT,
                  binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    result = _context(contract_path)
    context_path = Path(context_path)
    binding_path = Path(binding_path)
    context_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.write_bytes(result["bindingText"].encode("ascii"))
    context_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    return result


def preflight(*, contract_path: Path, context_path: Path = DEFAULT_CONTEXT,
              binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    expected = _context(contract_path)
    actual = _load(context_path)
    _require(actual == expected, "context-replay-mismatch")
    binding = Path(binding_path).read_bytes()
    _require(binding == expected["bindingText"].encode("ascii")
             and hashlib.sha256(binding).hexdigest().upper()
             == expected["targetSetBindingSha256"],
             "binding-bytes-drift")
    return expected


def verify_receipt(receipt_path: Path, *, contract_path: Path,
                   context_path: Path = DEFAULT_CONTEXT,
                   binding_path: Path = DEFAULT_BINDING) -> dict[str, Any]:
    context = preflight(contract_path=contract_path,
                        context_path=context_path, binding_path=binding_path)
    receipt_path = Path(receipt_path)
    receipt, _receipt_sha256 = cursor._load_json_with_sha256(
        receipt_path, label="scoped-group capture receipt",
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
             and (game_hash, metadata_hash)
             == (context["nativeInputs"]["gameAssemblySha256"],
                 context["nativeInputs"]["metadataSha256"]),
             "receipt-current-inputs")
    for section, expected_names in (("losses", LOSS_COUNTERS),
                                    ("overflow", OVERFLOW_COUNTERS)):
        counters = receipt.get(section)
        _require(isinstance(counters, Mapping)
                 and set(counters) == set(expected_names)
                 and all(type(counters[name]) is int and counters[name] == 0
                         for name in expected_names),
                 f"receipt-{section}-shape-or-loss")
    for name in ("unsupportedSourceLength", "unsupportedSourceIdentity", "wrongCallsite"):
        _require(type(receipt.get(name)) is int and receipt[name] >= 0,
                 f"receipt-{name}-shape")
    _require(receipt["unsupported"] == receipt["unsupportedSourceLength"]
             + receipt["unsupportedSourceIdentity"],
             "receipt-unsupported-counter-reconciliation")
    target_sources = context["targetSources"]
    by_pair = {(row["sourceLength"], row["sourceSha256"]): target
               for row, target in zip(target_sources, context["targets"])}
    observations = receipt.get("observations")
    _require(isinstance(observations, list) and len(observations) == len(target_sources),
             "receipt-target-coverage")
    if "observationCount" in receipt:
        _require(type(receipt["observationCount"]) is int
                 and receipt["observationCount"] == len(observations),
                 "receipt-observation-count")
    observed: set[tuple[int, str]] = set()
    for index, observation in enumerate(observations):
        _require(isinstance(observation, Mapping), f"receipt-observation[{index}]-shape")
        copied, digest = cursor._decode_source(observation, index)
        pair = (len(copied), digest)
        _require(pair in by_pair and pair not in observed,
                 f"receipt-observation[{index}]-outside-or-duplicate-target")
        observed.add(pair)
    _require(observed == set(by_pair), "receipt-target-coverage")
    stats = _target_stats(receipt, target_sources,
                          {digest: 1 for _length, digest in observed})
    _require(all(row["observationsPublished"] == 1
                 and row["duplicateConflicts"] == 0
                 and row["unverifiedPairs"] == 0 for row in stats),
             "receipt-target-loss-or-conflict")
    processed = sum(1 + row["duplicateIdentical"] for row in stats)
    _require(all(type(receipt.get(name)) is int and receipt[name] == processed
                 for name in ("observationsProcessed", "publishedRecords", "completedPairs"))
             and all(type(receipt.get(name)) is int and receipt[name] == 0
                     for name in ("pendingRecords", "progressPublicationFailures")),
             "receipt-transport-counter-reconciliation")
    if context.get("schema") == CONTEXT_SCHEMA_V2:
        basis_rows = [
            row
            for name in _load(contract_path)["scopedEvidence"]["bases"]
            for row in _load(_inside_repo(name))["files"]
        ]
        basis_provenance = {"bases": context["provenance"]["bases"]}
    else:
        basis = _load(_inside_repo(_load(contract_path)["scopedEvidence"]["basis"]))
        basis_rows = basis["files"]
        basis_provenance = {"basis": context["provenance"]["basis"]}
    rows = []
    for index, observation in enumerate(observations):
        row = cursor._verify_observation(
            observation, index, basis_rows, input_set,
        )
        pair = (row.get("hardLimit"), row.get("logicalSha256"))
        _require(pair in by_pair, f"receipt-cursor[{index}]-source-join")
        target = by_pair[pair]
        _require(row.get("boundaryClass") == "exact-closed"
                 and row.get("parserCursor") == target["length"]
                 and row.get("logicalPath") == target["virtualPath"],
                 f"receipt-cursor[{index}]-not-exact-closed")
        rows.append(row)
    _require(len(rows) == len(target_sources), "receipt-row-count")
    return {
        "schema": (VERIFY_SCHEMA_V2 if context.get("schema") == CONTEXT_SCHEMA_V2
                   else VERIFY_SCHEMA),
        "status": "exact-closed-scoped-group",
        "publicationEligible": False, "wholeSchemaExact": False,
        "inputSetSha256": input_set,
        "nativeInputs": context["nativeInputs"],
        "targetSetBindingSha256": context["targetSetBindingSha256"],
        "targets": context["targets"], "rows": rows,
        "summary": {"targetCount": len(target_sources),
                    "exactClosed": len(rows), "missing": 0,
                    "failureReasons": []},
        "provenance": {"receipt": _fingerprint(receipt_path),
                       "context": _fingerprint(context_path),
                       **basis_provenance},
        "evidenceBoundary": (
            "Every reviewed source has an exact copied-byte identity and executed "
            "47-field/two-child cursor vector through EOF in one loss-free v3 session. "
            "Populated ActionGroup interiors, route semantics and whole-schema closure "
            "remain independent source-specific questions."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", nargs="?", type=Path)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--capture-binding-batch", action="store_true")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            _require(args.receipt is None, "preflight-receipt-unexpected")
            result = preflight(contract_path=args.contract,
                               context_path=args.context, binding_path=args.binding)
            if args.capture_binding_batch:
                print("|".join((result["inputSetSha256"],
                                str(args.binding.resolve()),
                                result["targetSetBindingSha256"])))
            else:
                print(json.dumps({"status": "validated",
                                  "targetCount": len(result["targets"]),
                                  "context": str(args.context)}, ensure_ascii=False))
            return 0
        if args.receipt is None:
            result = build_context(contract_path=args.contract,
                                   context_path=args.context, binding_path=args.binding)
            print(json.dumps({"status": result["status"],
                              "targetCount": len(result["targets"]),
                              "context": str(args.context)}, ensure_ascii=False))
            return 0
        result = verify_receipt(args.receipt, contract_path=args.contract,
                                context_path=args.context, binding_path=args.binding)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"],
                          "targetCount": result["summary"]["targetCount"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError,
            cursor.ReceiptVerificationError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
