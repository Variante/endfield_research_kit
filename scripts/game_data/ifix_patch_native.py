"""Load the reviewed current-build Gameplay IFix patch contract.

The checked-in contract is the production boundary.  Recovery tooling may
refresh or reconcile it, but Story builders never read ignored recovery
reports or require the IFix payload to be extracted into ``export_full``.
"""
from __future__ import annotations

from scripts.game_data.contracts import CONTRACTS_DIR
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from scripts.common import (
    NATIVE_EVIDENCE_MISSING,
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
)
from scripts.game_data.ifix_patch import ordered_signature_parameters


SCHEMA = "ifixPatchNativeContract.v1"
AUDIT_SCHEMA = "ifixPatchNativeContractAudit.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "ifix_patch.json"
VIRTUAL_PATH = (
    "Persistent VFS/Data/IFixPatchOut/Windows/Gameplay.Beyond.patch.bytes"
)
CLASSIFICATION_KEYS = (
    "taskCompletionFixMatches",
    "taskCompletionReferenceMatches",
    "receiverOwnershipFixMatches",
    "receiverOwnershipReferenceMatches",
    "missionHudFixSignatures",
    "dialogCinematicFixSignatures",
)


from scripts.common import repo_path as _source_file



def validate_ifix_patch_contract(
    contract: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """Return deterministic failures for every production-consumed fact."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "ifixPatchNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    sources = contract.get("sources") if isinstance(contract.get("sources"), dict) else {}
    signatures = (
        contract.get("fixedMethodSignatures")
        if isinstance(contract.get("fixedMethodSignatures"), list)
        else []
    )
    classifications = (
        contract.get("classifications")
        if isinstance(contract.get("classifications"), dict)
        else {}
    )
    classification_counts = {
        key: len(value) if isinstance(value, list) else None
        for key, value in classifications.items()
    }
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("virtual_path", VIRTUAL_PATH, sources.get("virtualPath")),
        ("classification_keys", sorted(CLASSIFICATION_KEYS), sorted(classification_counts)),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    for key in ("patchSha256", "gameAssemblySha256", "globalMetadataSha256"):
        if not re.fullmatch(r"[0-9A-Fa-f]{64}", str(sources.get(key) or "")):
            reject(f"source_{key}", "64 hex characters", sources.get(key))
    if not isinstance(sources.get("patchBytes"), int) or sources["patchBytes"] <= 0:
        reject("patch_bytes", "positive integer", sources.get("patchBytes"))

    malformed = [
        index
        for index, signature in enumerate(signatures)
        if not isinstance(signature, str) or not signature
    ]
    if malformed:
        reject("fixed_signature_shape", {"nonemptyStrings": True}, malformed)
    if len(signatures) != len(set(signatures)):
        reject("fixed_signature_uniqueness", len(signatures), len(set(signatures)))
    fixed_set = set(signatures)
    for key in (
        "taskCompletionFixMatches",
        "receiverOwnershipFixMatches",
        "missionHudFixSignatures",
        "dialogCinematicFixSignatures",
    ):
        missing = [value for value in classifications.get(key) or [] if value not in fixed_set]
        if missing:
            reject(f"{key}_membership", {"subsetOfFixedMethods": True}, missing)
    return failures


# -- classification rules -------------------------------------------------------
#
# Name rules, applied to the fixed method signatures and to the methods the
# patched code references. They reproduce the reviewed classification of the
# previous patch exactly; a new patch is classified by the same rules.


def is_mission_hud(signature: str) -> bool:
    return "MissionHud" in signature


def is_dialog_cinematic(signature: str) -> bool:
    return "Cinematic" in signature or "Dialog" in signature


def is_task_completion(signature: str) -> bool:
    return "Task" in signature and any(word in signature for word in ("Complete", "Finish", "Succeed"))


def is_receiver_ownership(signature: str) -> bool:
    """LevelScript event-receiver ownership, not every component named receiver."""
    return "Receiver" in signature and any(
        word in signature for word in ("LevelScript", "EventParams", "SetReceiver")
    )


def _clr_type_name(qualified: str) -> str:
    """Drop the assembly qualification outside generic brackets."""
    depth = 0
    for index, char in enumerate(qualified):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == "," and depth == 0:
            return qualified[:index]
    return qualified


def _signature_text(record: dict[str, Any], type_names: list[str]) -> str:
    owner = type_names[record["declaringTypeIndex"]]
    method = record["name"]["value"]
    if record["genericTypeIndices"]:
        arguments = ", ".join(type_names[index] for index in record["genericTypeIndices"])
        method += f"<{arguments}>"
    parameters = ", ".join(
        type_names[parameter["typeIndex"]]
        if parameter["kind"] == "extern-type-index" else parameter["name"]
        for parameter in ordered_signature_parameters(record)
    )
    return f"{owner}::{method}({parameters})"


def regenerate(patch_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Rebuild the contract from the installed Gameplay patch and native build."""
    from scripts.game_data.ifix_patch import parse_ifix_patch

    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {}, [f"installed_native_inputs:{gate.status}:{gate.detail}"]
    data = Path(patch_path).read_bytes()
    parsed = parse_ifix_patch(data, source=str(patch_path))
    type_names = [_clr_type_name(row["value"]) for row in parsed["externTypes"]["records"]]
    signatures = [
        _signature_text(row["signature"], type_names)
        for row in parsed["fixRecords"]["records"]
    ]
    references = sorted({
        _signature_text(row, type_names) for row in parsed["externMethods"]["records"]
    })
    contract = {
        "schema": SCHEMA,
        "status": "validated",
        "sources": {
            "virtualPath": VIRTUAL_PATH,
            "patchBytes": len(data),
            "patchSha256": hashlib.sha256(data).hexdigest().upper(),
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "globalMetadataSha256": gate.metadata_sha256.upper(),
        },
        "fixedMethodSignatures": signatures,
        "classifications": {
            "taskCompletionFixMatches": [s for s in signatures if is_task_completion(s)],
            "taskCompletionReferenceMatches": [s for s in references if is_task_completion(s)],
            "receiverOwnershipFixMatches": [s for s in signatures if is_receiver_ownership(s)],
            "receiverOwnershipReferenceMatches": [s for s in references if is_receiver_ownership(s)],
            "missionHudFixSignatures": [s for s in signatures if is_mission_hud(s)],
            "dialogCinematicFixSignatures": [s for s in signatures if is_dialog_cinematic(s)],
        },
    }
    return contract, validate_ifix_patch_contract(contract, str(patch_path))


def project_ifix_patch_contract(
    contract: dict[str, Any], *, source_file: str, source_sha256: str
) -> dict[str, Any]:
    """Project the compact contract into the shared production audit shape."""
    sources = contract["sources"]
    signatures = list(contract["fixedMethodSignatures"])
    return {
        "schema": AUDIT_SCHEMA,
        "status": NATIVE_EVIDENCE_VALIDATED,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "source": {
            "label": sources["virtualPath"],
            "patchBytes": sources["patchBytes"],
            "patchSha256": str(sources["patchSha256"]).upper(),
            "gameAssemblySha256": str(sources["gameAssemblySha256"]).upper(),
            "metadataSha256": str(sources["globalMetadataSha256"]).upper(),
        },
        "fixedMethodSignatures": signatures,
        "classifications": contract["classifications"],
        "validationFailures": [],
    }


def load_ifix_patch_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Load IFix facts only when contract shape and installed native build match."""
    path = Path(contract_path)
    source_file = _source_file(path)
    raw = b""
    failures: list[dict[str, Any]] = []
    try:
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(contract, dict):
            raise ValueError(f"expected object, found {type(contract).__name__}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        contract = {}
        failures.append({
            "validator": "ifixPatchNativeContract",
            "gate": "read_valid_json",
            "sourceFile": source_file,
            "expected": {"readableJsonObject": True},
            "actual": str(error)[:400],
        })
    if contract:
        failures.extend(validate_ifix_patch_contract(contract, source_file))

    sources = contract.get("sources") or {}
    native = check_installed_native_inputs(
        str(sources.get("gameAssemblySha256") or ""),
        str(sources.get("globalMetadataSha256") or ""),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        failures.append({
            "validator": "ifixPatchNativeContract",
            "gate": "installed_native_inputs",
            "sourceFile": source_file,
            "expected": {"status": NATIVE_EVIDENCE_VALIDATED},
            "actual": {"status": native.status, "detail": native.detail},
        })
    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    if not failures:
        return project_ifix_patch_contract(
            contract,
            source_file=source_file,
            source_sha256=source_sha256,
        )
    status = (
        native.status
        if native.status != NATIVE_EVIDENCE_VALIDATED
        else NATIVE_EVIDENCE_MISSING
        if not raw
        else NATIVE_EVIDENCE_MISMATCHED
    )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "validationFailures": failures,
    }


def fixed_method_prefix_matches(
    audit: dict[str, Any], prefixes: Iterable[str]
) -> list[str]:
    """Return fixed signatures covered by any exact reviewed method prefix."""
    if audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        return []
    normalized = tuple(str(value) for value in prefixes if str(value))
    return [
        signature
        for signature in audit.get("fixedMethodSignatures") or []
        if any(str(signature).startswith(prefix) for prefix in normalized)
    ]


def project_current_ifix_evidence(
    audit: dict[str, Any], *, relevant_prefixes: Iterable[str]
) -> dict[str, Any]:
    """Project the shared audit into the existing Dialog control-flow shape."""
    if audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"IFix contract status is {audit.get('status')!r}")
    source = audit["source"]
    signatures = audit["fixedMethodSignatures"]
    return {
        "status": "audited",
        "sourceLabel": source["label"],
        "sha256": str(source["patchSha256"]).lower(),
        "reportFile": audit["sourceFile"],
        "fixedMethodCount": len(signatures),
        "relevantFixedMethods": fixed_method_prefix_matches(
            audit,
            relevant_prefixes,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load or regenerate the Gameplay IFix patch contract.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--regenerate", type=Path, metavar="PATCH",
        help="Gameplay.Beyond.patch.bytes from a bounded AnimeStudio i-fix-patch dump",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.regenerate is None:
        audit = load_ifix_patch_contract(args.contract)
        print(json.dumps({"status": audit["status"], "failures": audit.get("validationFailures")}, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract, failures = regenerate(args.regenerate)
    print(json.dumps({"failures": failures, "fixedMethods": len(contract.get("fixedMethodSignatures") or []),
                      "classifications": {k: len(v) for k, v in (contract.get("classifications") or {}).items()}},
                     indent=1))
    if failures:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(contract, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.ifix_patch_native")
    sys.exit(main())


__all__ = [
    "AUDIT_SCHEMA",
    "CLASSIFICATION_KEYS",
    "DEFAULT_CONTRACT",
    "SCHEMA",
    "regenerate",
    "fixed_method_prefix_matches",
    "load_ifix_patch_contract",
    "project_current_ifix_evidence",
    "project_ifix_patch_contract",
    "validate_ifix_patch_contract",
]
