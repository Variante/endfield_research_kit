"""Load, gate and regenerate the reviewed TeleportParam native carrier contract.

The contract comes from the generic native value-carrier scan
(``audit_native_carriers generic --carrier-type Beyond.Gameplay.TeleportParam``)
and proves two bounded facts about the teleport-finish correlation carrier:
no direct AOT caller passes a nonzero missionId, levelScriptId, actionId or
performId, and LoadFinishStep reads levelScriptId and actionId but not
missionId. It therefore adds no mission ownership, branch or Story-order edge.

The validator checks those invariants, not one build's counts, offsets or
instruction addresses; the scan regenerates all of those with
``--write-contract``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_MISSING,
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
)
from scripts.common import repo_path as _source_file
from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "teleportParamNativeContract.v2"
AUDIT_SCHEMA = "nativeValueCarrierAudit.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "teleport_param.json"
CARRIER_TYPE = "Beyond.Gameplay.TeleportParam"
FOCUS_FIELDS = ("missionId", "levelScriptId", "actionId", "performId")
#: Initializer states that carry no authored value into the carrier.
NON_ORIGINATING_STATES = frozenset({"zero", "forwarded_or_unresolved", "unknown"})
LOAD_FINISH_METHOD_SUFFIX = "LoadFinishStep.DoExecute"
COUNT_KEYS = (
    "carrierFields",
    "focusFields",
    "containerPaths",
    "signatureMethods",
    "mappedSignaturePointers",
    "focusFieldAccesses",
    "directCallsites",
    "directCarrierArguments",
)


def _failure_status(*, raw: bytes, native_status: str) -> str:
    if native_status != NATIVE_EVIDENCE_VALIDATED:
        return native_status
    return NATIVE_EVIDENCE_MISMATCHED if raw else NATIVE_EVIDENCE_MISSING


def _project_generic_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Reduce a fresh generic scan to the checked-in contract vocabulary."""
    carrier = audit.get("carrier") or {}
    summary = audit.get("summary") or {}
    source = audit.get("source") or {}
    target_counts: dict[str, int] = {}
    for call in audit.get("directCallsites") or []:
        targets = call.get("targets") or []
        if not targets:
            continue
        target = targets[0]
        key = f"{target.get('type', '')}.{target.get('method', '')}"
        target_counts[key] = target_counts.get(key, 0) + 1
    return {
        "auditSchema": audit.get("schema"),
        "auditValidation": (audit.get("validation") or {}).get("status"),
        "sources": {
            "gameAssembly": source.get("gameAssembly"),
            "gameAssemblySha256": str(source.get("gameAssemblySha256") or "").upper(),
            "globalMetadata": source.get("globalMetadata"),
            "globalMetadataSha256": str(source.get("globalMetadataSha256") or "").upper(),
        },
        "carrier": {
            "type": carrier.get("type"),
            "nativeSize": carrier.get("nativeSize"),
            "layout": {
                str(row.get("name") or ""): str(row.get("offset") or "")
                for row in carrier.get("fields") or []
            },
        },
        "counts": {key: summary.get(key) for key in COUNT_KEYS},
        "directCallerCensus": dict(sorted(target_counts.items())),
        "focusFieldSummary": audit.get("focusFieldSummary") or {},
        "loadFinishConsumerAccesses": [
            row for row in audit.get("fieldAccesses") or []
            if str(row.get("method") or "").endswith(LOAD_FINISH_METHOD_SUFFIX)
        ],
    }


def contract_from_generic_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Regenerate the checked-in contract from a fresh generic scan."""
    projected = _project_generic_audit(audit)
    projected.pop("auditValidation")
    return {"schema": SCHEMA, "status": "validated", **projected}


def reconcile_generic_audit(
    audit: dict[str, Any], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare a fresh generic scan against every retained production fact."""
    projected = _project_generic_audit(audit)
    failures: list[dict[str, Any]] = []
    if projected["auditValidation"] != "validated":
        failures.append({
            "validator": "teleportParamNativeContractReconciliation",
            "gate": "auditValidation",
            "sourceFile": "generic native carrier audit",
            "expected": "validated",
            "actual": projected["auditValidation"],
        })
    for gate in (
        "auditSchema", "sources", "carrier", "counts", "directCallerCensus",
        "focusFieldSummary", "loadFinishConsumerAccesses",
    ):
        expected = contract.get(gate)
        if gate == "sources":
            expected = {key: str(value).upper() if key.endswith("Sha256") else value
                        for key, value in (expected or {}).items()}
        if projected[gate] != expected:
            failures.append({
                "validator": "teleportParamNativeContractReconciliation",
                "gate": gate,
                "sourceFile": "generic native carrier audit",
                "expected": expected,
                "actual": projected[gate],
            })
    return failures


def validate_teleport_param_contract(
    contract: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """Return failures for every invariant a consumer relies on."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "teleportParamNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    carrier = contract.get("carrier") or {}
    layout = carrier.get("layout") or {}
    for gate, expected, actual in (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("audit_schema", AUDIT_SCHEMA, contract.get("auditSchema")),
        ("carrier_type", CARRIER_TYPE, carrier.get("type")),
        ("count_keys", sorted(COUNT_KEYS), sorted(contract.get("counts") or {})),
    ):
        if actual != expected:
            reject(gate, expected, actual)
    missing_fields = [name for name in FOCUS_FIELDS if name not in layout]
    if missing_fields:
        reject("focus_fields_in_layout", list(FOCUS_FIELDS), missing_fields)

    focus = contract.get("focusFieldSummary") or {}
    for field_name in FOCUS_FIELDS:
        states = set((focus.get(field_name) or {}).get("directCallInitializerStates") or {})
        originating = sorted(states - NON_ORIGINATING_STATES)
        if not states or originating:
            reject(
                f"focus.{field_name}.no_direct_originator",
                sorted(NON_ORIGINATING_STATES),
                sorted(states),
            )
        if (focus.get(field_name) or {}).get("offset") != layout.get(field_name):
            reject(f"focus.{field_name}.offset", layout.get(field_name), (focus.get(field_name) or {}).get("offset"))

    read_fields = {
        row.get("field") for row in contract.get("loadFinishConsumerAccesses") or []
        if row.get("kind") == "read"
    }
    if not {"levelScriptId", "actionId"} <= read_fields or "missionId" in read_fields:
        reject(
            "load_finish_consumer_reads",
            {"reads": ["actionId", "levelScriptId"], "notRead": "missionId"},
            sorted(read_fields),
        )
    return failures


def _producer_finding(contract: dict[str, Any]) -> str:
    focus = contract["focusFieldSummary"]
    states: dict[str, int] = {}
    for field_name in FOCUS_FIELDS:
        for state, count in (focus[field_name].get("directCallInitializerStates") or {}).items():
            states[state] = max(states.get(state, 0), count)
    parts = ", ".join(f"{count} {state.replace('_', ' ')}" for state, count in sorted(states.items()))
    return (
        "The generic installed-binary carrier scan finds no nonzero direct AOT originator "
        f"for missionId, levelScriptId, actionId or performId; direct carrier arguments are {parts}."
    )


def _consumer_finding(contract: dict[str, Any]) -> str:
    reads = [
        f"{row['field']} at {row.get('instructionVa')}"
        for row in contract["loadFinishConsumerAccesses"] if row.get("kind") == "read"
    ]
    return (
        f"The inherited container-path scan proves that LoadFinishStep reads {' and '.join(reads)}. "
        "It does not read missionId."
    )


def project_teleport_param_contract(
    contract: dict[str, Any], *, source_file: str, source_sha256: str
) -> dict[str, Any]:
    """Project the compact native facts into the existing pipeline shape."""
    sources = contract["sources"]
    carrier = contract["carrier"]
    counts = contract["counts"]
    return {
        "type": carrier["type"],
        "size": f"0x{carrier['nativeSize']:x}",
        "layout": carrier["layout"],
        "auditSchema": contract["auditSchema"],
        "auditReport": source_file,
        "contractSourceSha256": source_sha256,
        "metadataSignatureMethodCount": counts["signatureMethods"],
        "containerPathCount": counts["containerPaths"],
        "focusFieldAccessCount": counts["focusFieldAccesses"],
        "directCallerCensus": contract["directCallerCensus"],
        "focusFieldSummary": contract["focusFieldSummary"],
        "loadFinishConsumerAccesses": contract["loadFinishConsumerAccesses"],
        "producerFinding": _producer_finding(contract),
        "consumerFinding": _consumer_finding(contract),
        "finding": (
            "The active client binary contains a typed teleport-finish correlation "
            "carrier but no audited direct AOT producer for its nonzero actionId. "
            "This creates no mission ownership, branch, or Story-order edge."
        ),
        "patchBoundary": (
            "The generic audit covers installed direct AOT calls and exact field "
            "accesses. Virtual/interface dispatch, reflection, XLua, IFix "
            "substitution and live server values remain outside the bounded result."
        ),
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
        "validation": {"status": NATIVE_EVIDENCE_VALIDATED, "failures": []},
        "relatedOriginalFiles": [
            {
                "kind": "original_game_binary",
                "sourceFile": sources.get("gameAssembly"),
                "sha256": sources.get("gameAssemblySha256"),
                "relationship": "native_value_carrier_audit_authority",
            },
            {
                "kind": "original_game_metadata",
                "sourceFile": sources.get("globalMetadata"),
                "sha256": sources.get("globalMetadataSha256"),
                "relationship": "native_value_carrier_audit_authority",
            },
        ],
    }


def load_teleport_param_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Load the contract only for the build it records."""
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
            "validator": "teleportParamNativeContract",
            "gate": "read_valid_json",
            "sourceFile": source_file,
            "expected": {"readableJsonObject": True},
            "actual": str(error)[:400],
        })
    if contract:
        failures.extend(validate_teleport_param_contract(contract, source_file))

    sources = contract.get("sources") or {}
    native = check_installed_native_inputs(
        str(sources.get("gameAssemblySha256") or ""),
        str(sources.get("globalMetadataSha256") or ""),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        failures.append({
            "validator": "teleportParamNativeContract",
            "gate": "installed_native_inputs",
            "sourceFile": source_file,
            "expected": {"status": NATIVE_EVIDENCE_VALIDATED},
            "actual": {"status": native.status, "detail": native.detail},
        })
    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    if not failures:
        return project_teleport_param_contract(
            contract, source_file=source_file, source_sha256=source_sha256
        )
    return {
        "type": CARRIER_TYPE,
        "auditSchema": AUDIT_SCHEMA,
        "auditReport": source_file,
        "contractSourceSha256": source_sha256,
        "storyBindingsAdded": 0,
        "validation": {
            "status": _failure_status(raw=raw, native_status=native.status),
            "failures": failures,
        },
        "relatedOriginalFiles": [],
    }


__all__ = [
    "AUDIT_SCHEMA",
    "CARRIER_TYPE",
    "COUNT_KEYS",
    "DEFAULT_CONTRACT",
    "FOCUS_FIELDS",
    "SCHEMA",
    "contract_from_generic_audit",
    "load_teleport_param_contract",
    "reconcile_generic_audit",
    "validate_teleport_param_contract",
]
