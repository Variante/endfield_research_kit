"""Load the reviewed current-build Gameplay IFix patch contract.

The checked-in contract is the production boundary.  Recovery tooling may
refresh or reconcile it, but Story builders never read ignored recovery
reports or require the IFix payload to be extracted into ``export_full``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

if __package__ == "scripts.story_builder.native_contracts":
    from ...common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
elif __package__ == "story_builder.native_contracts":
    from common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


SCHEMA = "ifixPatchNativeContract.v1"
AUDIT_SCHEMA = "ifixPatchNativeContractAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("ifix_patch.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
PATCH_SHA256 = (
    "737134081E06371F13C073988547E887037FCCF2F57E1052BE35DD255D27BC21"
)
PATCH_BYTES = 82021
FIXED_METHOD_COUNT = 30
FIXED_SIGNATURES_SHA256 = (
    "8FD675E32CD89D3F78171A78FAE42BCB557554B98C70074600C491C2FA4C6ECE"
)
VIRTUAL_PATH = (
    "Persistent VFS/Data/IFixPatchOut/Windows/Gameplay.Beyond.patch.bytes"
)
EXPECTED_CLASSIFICATION_COUNTS = {
    "taskCompletionFixMatches": 0,
    "taskCompletionReferenceMatches": 0,
    "receiverOwnershipFixMatches": 0,
    "receiverOwnershipReferenceMatches": 0,
    "missionHudFixSignatures": 2,
    "dialogCinematicFixSignatures": 7,
}
EXPECTED_CLASSIFICATION_SHA256 = {
    "missionHudFixSignatures": (
        "5C4C0B2C45C2C0A598C0DA6FAA1BC8F067237D54519392813437054E3B1AACB6"
    ),
    "dialogCinematicFixSignatures": (
        "B0E87644A44E53B781425A6A37FBF0A6CA22B53FC9F810A48CEE8944FA25EEC4"
    ),
}


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


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
        ("patch_bytes", PATCH_BYTES, sources.get("patchBytes")),
        (
            "patch_sha256",
            PATCH_SHA256,
            str(sources.get("patchSha256") or "").upper(),
        ),
        (
            "gameassembly_sha256",
            GAMEASSEMBLY_SHA256,
            str(sources.get("gameAssemblySha256") or "").upper(),
        ),
        (
            "metadata_sha256",
            METADATA_SHA256,
            str(sources.get("globalMetadataSha256") or "").upper(),
        ),
        ("fixed_method_count", FIXED_METHOD_COUNT, len(signatures)),
        (
            "fixed_signatures_declared_sha256",
            FIXED_SIGNATURES_SHA256,
            str(contract.get("fixedMethodSignaturesSha256") or "").upper(),
        ),
        (
            "fixed_signatures_sha256",
            FIXED_SIGNATURES_SHA256,
            _canonical_sha256(signatures),
        ),
        (
            "classification_counts",
            EXPECTED_CLASSIFICATION_COUNTS,
            classification_counts,
        ),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    for key, expected in EXPECTED_CLASSIFICATION_SHA256.items():
        actual = _canonical_sha256(classifications.get(key) or [])
        if actual != expected:
            reject(f"{key}_sha256", expected, actual)

    malformed = [
        index
        for index, signature in enumerate(signatures)
        if not isinstance(signature, str) or not signature
    ]
    if malformed:
        reject("fixed_signature_shape", {"nonemptyStrings": True}, malformed)
    if len(signatures) != len(set(signatures)):
        reject("fixed_signature_uniqueness", FIXED_METHOD_COUNT, len(set(signatures)))
    fixed_set = set(signatures)
    for key in ("missionHudFixSignatures", "dialogCinematicFixSignatures"):
        values = classifications.get(key) or []
        missing = [value for value in values if value not in fixed_set]
        if missing:
            reject(f"{key}_membership", {"subsetOfFixedMethods": True}, missing)
    for key in (
        "taskCompletionFixMatches",
        "taskCompletionReferenceMatches",
        "receiverOwnershipFixMatches",
        "receiverOwnershipReferenceMatches",
    ):
        if classifications.get(key) != []:
            reject(key, [], classifications.get(key))
    return failures


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

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
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


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "FIXED_METHOD_COUNT",
    "FIXED_SIGNATURES_SHA256",
    "GAMEASSEMBLY_SHA256",
    "METADATA_SHA256",
    "PATCH_BYTES",
    "PATCH_SHA256",
    "SCHEMA",
    "fixed_method_prefix_matches",
    "load_ifix_patch_contract",
    "project_current_ifix_evidence",
    "project_ifix_patch_contract",
    "validate_ifix_patch_contract",
]
