"""Load and gate the reviewed TeleportParam native carrier contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

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


SCHEMA = "teleportParamNativeContract.v1"
AUDIT_SCHEMA = "nativeValueCarrierAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("teleport_param.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
EXPECTED_LAYOUT = {
    "source": "0x0",
    "uiType": "0x4",
    "options": "0x8",
    "resetMap": "0xc",
    "callbackHandle": "0x10",
    "missionId": "0x18",
    "levelScriptId": "0x20",
    "actionId": "0x28",
    "performId": "0x30",
}
EXPECTED_COUNTS = {
    "carrierFields": 9,
    "focusFields": 4,
    "containerPaths": 10,
    "signatureMethods": 15,
    "mappedSignaturePointers": 14,
    "focusFieldAccesses": 23,
    "directCallsites": 13,
    "directCarrierArguments": 10,
}
EXPECTED_INITIALIZER_STATES = {
    "forwarded_or_unresolved": 3,
    "unknown": 1,
    "zero": 6,
}
EXPECTED_FOCUS_ACCESS_COUNTS = {
    "missionId": {"readAccesses": 3, "writeAccesses": 2},
    "levelScriptId": {"readAccesses": 4, "writeAccesses": 2},
    "actionId": {"readAccesses": 4, "writeAccesses": 2},
    "performId": {"readAccesses": 4, "writeAccesses": 2},
}
EXPECTED_DIRECT_CALLER_CENSUS = {
    (
        "Beyond.Gameplay.Core.GameLevelLoader+LoadingPipeline."
        "Beyond.Gameplay.Core.ILoadingPipelineContext.get_teleportParam"
    ): 2,
    "Beyond.Gameplay.Core.GameLevelLoader.LoadAtPos": 1,
    "Beyond.Gameplay.Core.GameLevelLoader.LoadAtPosInCurrentMap": 2,
    "Beyond.Gameplay.Core.GameLevelLoader.OpenLevel": 1,
    "Beyond.Gameplay.Core.PerformerFactory._CreatePerformPerformer": 1,
    "Beyond.Gameplay.Core.SquadManager.ServerTeleportSquad": 1,
    "Beyond.Gameplay.TeleportProcessor.GetTeleportParamsFromPassThroughData": 2,
    "IFix.ILFixDynamicMethodWrapper.__Gen_Wrap_4652": 1,
    "IFix.ILFixDynamicMethodWrapper.__Gen_Wrap_8806": 1,
    "IFix.ILFixDynamicMethodWrapper.__Gen_Wrap_8811": 1,
}
EXPECTED_LOAD_FINISH_ACCESSES = [
    {
        "field": "levelScriptId",
        "kind": "read",
        "writeState": None,
        "pathKind": "nested_container",
        "root": "this",
        "expectedPath": ["0x20", "0x60"],
        "origin": "this+0x20+0x60",
        "method": (
            "Beyond.Gameplay.Core.GameLevelLoader+LoadingPipeline+"
            "LoadFinishStep.DoExecute"
        ),
        "token": "0x06011d23",
        "methodVa": "0x183dd8c60",
        "instructionVa": "0x183dd8e56",
        "instruction": "mov r14, [rsi+0x60]",
        "width": 8,
    },
    {
        "field": "actionId",
        "kind": "read",
        "writeState": None,
        "pathKind": "nested_container",
        "root": "this",
        "expectedPath": ["0x20", "0x68"],
        "origin": "this+0x20+0x68",
        "method": (
            "Beyond.Gameplay.Core.GameLevelLoader+LoadingPipeline+"
            "LoadFinishStep.DoExecute"
        ),
        "token": "0x06011d23",
        "methodVa": "0x183dd8c60",
        "instructionVa": "0x183dd8e63",
        "instruction": "mov rsi, [rsi+0x68]",
        "width": 8,
    },
]


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _failure_status(*, raw: bytes, native_status: str) -> str:
    if native_status != NATIVE_EVIDENCE_VALIDATED:
        return native_status
    return NATIVE_EVIDENCE_MISMATCHED if raw else NATIVE_EVIDENCE_MISSING


def _project_generic_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Reduce a fresh generic scan to the checked-in contract vocabulary."""
    carrier = audit.get("carrier") or {}
    summary = audit.get("summary") or {}
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
            "gameAssemblySha256": (audit.get("source") or {}).get(
                "gameAssemblySha256"
            ),
            "globalMetadataSha256": (audit.get("source") or {}).get(
                "globalMetadataSha256"
            ),
        },
        "carrier": {
            "type": carrier.get("type"),
            "nativeSize": carrier.get("nativeSize"),
            "layout": {
                str(row.get("name") or ""): str(row.get("offset") or "")
                for row in carrier.get("fields") or []
            },
        },
        "counts": {key: summary.get(key) for key in EXPECTED_COUNTS},
        "directCallerCensus": dict(sorted(target_counts.items())),
        "focusFieldSummary": audit.get("focusFieldSummary") or {},
        "loadFinishConsumerAccesses": [
            row for row in audit.get("fieldAccesses") or []
            if str(row.get("method") or "").endswith("LoadFinishStep.DoExecute")
        ],
    }


def reconcile_generic_audit(
    audit: dict[str, Any], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare a fresh generic scan against every retained production fact."""
    projected = _project_generic_audit(audit)
    expected = {
        "auditSchema": contract.get("auditSchema"),
        "auditValidation": "validated",
        "sources": {
            "gameAssemblySha256": (contract.get("sources") or {}).get(
                "gameAssemblySha256"
            ),
            "globalMetadataSha256": (contract.get("sources") or {}).get(
                "globalMetadataSha256"
            ),
        },
        "carrier": contract.get("carrier") or {},
        "counts": contract.get("counts") or {},
        "directCallerCensus": contract.get("directCallerCensus") or {},
        "focusFieldSummary": contract.get("focusFieldSummary") or {},
        "loadFinishConsumerAccesses": contract.get(
            "loadFinishConsumerAccesses"
        ) or [],
    }
    failures: list[dict[str, Any]] = []
    for gate in expected:
        if projected[gate] != expected[gate]:
            failures.append({
                "validator": "teleportParamNativeContractReconciliation",
                "gate": gate,
                "sourceFile": "generic native carrier audit",
                "expected": expected[gate],
                "actual": projected[gate],
            })
    return failures


def validate_teleport_param_contract(
    contract: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """Return deterministic failures for every production-consumed field."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "teleportParamNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    sources = contract.get("sources") or {}
    carrier = contract.get("carrier") or {}
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("audit_schema", AUDIT_SCHEMA, contract.get("auditSchema")),
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
        ("carrier_type", "Beyond.Gameplay.TeleportParam", carrier.get("type")),
        ("native_size", 0x38, carrier.get("nativeSize")),
        ("runtime_field_layout", EXPECTED_LAYOUT, carrier.get("layout")),
        ("counts", EXPECTED_COUNTS, contract.get("counts")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    focus = contract.get("focusFieldSummary") or {}
    for field_name, access_counts in EXPECTED_FOCUS_ACCESS_COUNTS.items():
        row = focus.get(field_name) or {}
        expected = {
            "offset": EXPECTED_LAYOUT[field_name],
            "width": 8,
            **access_counts,
            "zeroWriteAccesses": 1,
            "unknownWriteAccesses": 1,
            "directCallInitializerStates": EXPECTED_INITIALIZER_STATES,
        }
        if row != expected:
            reject(f"focus.{field_name}", expected, row)

    accesses = contract.get("loadFinishConsumerAccesses") or []
    if accesses != EXPECTED_LOAD_FINISH_ACCESSES:
        reject(
            "load_finish_consumer_accesses",
            EXPECTED_LOAD_FINISH_ACCESSES,
            accesses,
        )
    direct_callers = contract.get("directCallerCensus") or {}
    if direct_callers != EXPECTED_DIRECT_CALLER_CENSUS:
        reject(
            "direct_caller_census",
            EXPECTED_DIRECT_CALLER_CENSUS,
            direct_callers,
        )
    return failures


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
        "producerFinding": (
            "The generic installed-binary carrier scan finds one zero initializer "
            "and one value-copy write for each extended field. Six direct local "
            "carrier arguments leave missionId, levelScriptId, actionId, and "
            "performId exactly zero; three are forwarding/copy paths and the sole "
            "unknown local is a PerformerFactory consumer copy. No nonzero direct "
            "AOT originator is present."
        ),
        "consumerFinding": (
            "The inherited container-path scan proves that LoadFinishStep reads "
            "levelScriptId at 0x183dd8e56 and actionId at 0x183dd8e63. It does "
            "not read missionId. PerformerFactory separately consumes performId."
        ),
        "finding": (
            "The active client binary contains a typed teleport-finish correlation "
            "carrier but no audited direct AOT producer for its nonzero actionId. "
            "This creates no mission ownership, branch, or Story-order edge."
        ),
        "patchBoundary": (
            "The generic audit covers installed direct AOT calls and exact field "
            "accesses. The current Gameplay.Beyond IFix audit has no relevant "
            "TeleportProcessor, GameLevelLoader, LoadingPipeline, or PerformerFactory "
            "target; virtual/interface dispatch, reflection, XLua, and live server "
            "values remain outside the bounded result."
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
    """Load the contract only for the exact installed native build."""
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

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
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
        "type": "Beyond.Gameplay.TeleportParam",
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
    "DEFAULT_CONTRACT",
    "EXPECTED_COUNTS",
    "EXPECTED_DIRECT_CALLER_CENSUS",
    "EXPECTED_FOCUS_ACCESS_COUNTS",
    "EXPECTED_INITIALIZER_STATES",
    "EXPECTED_LAYOUT",
    "EXPECTED_LOAD_FINISH_ACCESSES",
    "GAMEASSEMBLY_SHA256",
    "METADATA_SHA256",
    "SCHEMA",
    "load_teleport_param_contract",
    "project_teleport_param_contract",
    "reconcile_generic_audit",
    "validate_teleport_param_contract",
]
