"""Load the reviewed current-build cinematic queue contract.

The compact checked-in contract contains only facts consumed by Story builders.
The optional recovery profile can regenerate the full native audit and reconcile
its production projection against this contract.
"""
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


SCHEMA = "cinematicQueueNativeContract.v1"
AUDIT_SCHEMA = "cinematicQueueNativeContractAudit.v1"
RECOVERY_AUDIT_SCHEMA = "cinematicQueueRuntimeAudit.v2"
DEFAULT_CONTRACT = Path(__file__).with_name("cinematic_queue.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
QUEUE_BASE_TYPE = "Beyond.Gameplay.Core.CinematicQueueItemDataBase"
QUEUE_HANDLE_TYPE = (
    "Beyond.Gameplay.Core.CinematicQueueManager+CinematicQueueItemHandle"
)
EXPECTED_DISPATCHERS = [
    "DoPlayCutsceneByHandle",
    "DoPlayDialogByHandle",
    "DoPlayForceSNSByHandle",
    "PlayCGByHandle",
    "ShowNarrativeBlackScreenByHandle",
    "ShowUIReadingPopPanelByHandle",
    "StartRemoteCommByHandle",
]
EXPECTED_COUNTS = {
    "payloadTypes": 7,
    "nativeDispatchers": 7,
    "enqueueEdges": 10,
    "nativeProducers": 10,
    "typedActionProducerRoutes": 16,
    "typedActionProducerTypes": 16,
}
ACTION_ROUTE_FIELDS = (
    "actionType",
    "actionFullType",
    "actionMethod",
    "actionToken",
    "actionVa",
    "producerType",
    "producerMethod",
    "producerToken",
    "producerVa",
)
ACTION_ROUTES_SHA256 = (
    "E758914A5A6FEEE667AC0DF76C8091B11AA1061DFEAD0FA853EA77476087778A"
)
BOUNDARY = (
    "The exact installed binary proves one polymorphic cinematic-handle "
    "dispatcher family and typed serialized-action producer routes. These "
    "facts do not identify mission ownership or establish Story order."
)


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


def validate_cinematic_queue_contract(
    contract: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """Return deterministic failures for every production-consumed fact."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "cinematicQueueNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    sources = contract.get("sources") or {}
    conclusion = contract.get("conclusion") or {}
    routes = contract.get("actionProducerRoutes") or []
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
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
        ("queue_base_type", QUEUE_BASE_TYPE, contract.get("queueBaseType")),
        ("queue_handle_type", QUEUE_HANDLE_TYPE, contract.get("queueHandleType")),
        ("dispatcher_methods", EXPECTED_DISPATCHERS, contract.get("dispatcherMethods")),
        ("counts", EXPECTED_COUNTS, contract.get("counts")),
        (
            "action_producer_routes_sha256",
            ACTION_ROUTES_SHA256,
            _canonical_sha256(routes),
        ),
        (
            "lua_runtime_dispatchers",
            True,
            conclusion.get("luaCallsAreRuntimeDispatchers"),
        ),
        ("static_mission_ownership", False, conclusion.get("staticMissionOwnership")),
        ("static_story_order", False, conclusion.get("staticStoryOrder")),
        ("boundary", BOUNDARY, contract.get("boundary")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    malformed_routes = [
        index
        for index, row in enumerate(routes)
        if not isinstance(row, dict)
        or any(row.get(field) in (None, "") for field in ACTION_ROUTE_FIELDS)
    ]
    if malformed_routes:
        reject("action_producer_route_fields", {"completeRoutes": 16}, malformed_routes)
    return failures


def project_cinematic_queue_contract(
    contract: dict[str, Any], *, source_file: str, source_sha256: str
) -> dict[str, Any]:
    """Project compact facts into the Lua/Mission Pipeline evidence shape."""
    sources = contract["sources"]
    counts = contract["counts"]
    return {
        "schema": AUDIT_SCHEMA,
        "status": NATIVE_EVIDENCE_VALIDATED,
        "report": source_file,
        "sha256": source_sha256.lower(),
        "gameAssemblySha256": str(sources["gameAssemblySha256"]).lower(),
        "metadataSha256": str(sources["globalMetadataSha256"]).lower(),
        "handleType": contract["queueHandleType"],
        "queueBaseType": contract["queueBaseType"],
        "dispatcherMethods": contract["dispatcherMethods"],
        "payloadTypeCount": counts["payloadTypes"],
        "nativeProducerCount": counts["nativeProducers"],
        "typedActionProducerRouteCount": counts["typedActionProducerRoutes"],
        "typedActionProducerTypeCount": counts["typedActionProducerTypes"],
        "actionProducerRoutes": contract["actionProducerRoutes"],
        "enqueueEdgeCount": counts["enqueueEdges"],
        "validationFailures": [],
    }


def load_cinematic_queue_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Load the cinematic facts only for their exact installed native build."""
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
            "validator": "cinematicQueueNativeContract",
            "gate": "read_valid_json",
            "sourceFile": source_file,
            "expected": {"readableJsonObject": True},
            "actual": str(error)[:400],
        })
    if contract:
        failures.extend(validate_cinematic_queue_contract(contract, source_file))

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        failures.append({
            "validator": "cinematicQueueNativeContract",
            "gate": "installed_native_inputs",
            "sourceFile": source_file,
            "expected": {"status": NATIVE_EVIDENCE_VALIDATED},
            "actual": {"status": native.status, "detail": native.detail},
        })
    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    if not failures:
        return project_cinematic_queue_contract(
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
        "report": source_file,
        "sha256": source_sha256.lower(),
        "validationFailures": failures,
    }


def project_runtime_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Extract exactly the stable production facts from a full recovery audit."""
    source = audit.get("source") or {}
    summary = audit.get("summary") or {}
    runtime = audit.get("contract") or {}
    conclusion = audit.get("conclusion") or {}
    routes = [
        {field: row.get(field) for field in ACTION_ROUTE_FIELDS}
        for row in runtime.get("actionProducerRoutes") or []
        if isinstance(row, dict)
    ]
    return {
        "schema": SCHEMA,
        "status": "validated",
        "sources": {
            "gameAssembly": "GameAssembly.dll",
            "gameAssemblySha256": str(source.get("gameAssemblySha256") or "").upper(),
            "globalMetadata": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
            "globalMetadataSha256": str(source.get("metadataSha256") or "").upper(),
        },
        "queueBaseType": (runtime.get("queueBase") or {}).get("type"),
        "queueHandleType": (runtime.get("queueHandle") or {}).get("type"),
        "dispatcherMethods": runtime.get("nativeDispatcherMethods") or [],
        "counts": {
            "payloadTypes": summary.get("payloadTypeCount"),
            "nativeDispatchers": summary.get("nativeDispatcherCount"),
            "enqueueEdges": summary.get("enqueueEdgeCount"),
            "nativeProducers": summary.get("nativeProducerCount"),
            "typedActionProducerRoutes": summary.get("typedActionProducerRouteCount"),
            "typedActionProducerTypes": summary.get("typedActionProducerTypeCount"),
        },
        "actionProducerRoutes": routes,
        "conclusion": {
            "luaCallsAreRuntimeDispatchers": conclusion.get("luaCallsAreRuntimeDispatchers"),
            "staticMissionOwnership": conclusion.get("staticMissionOwnership"),
            "staticStoryOrder": conclusion.get("staticStoryOrder"),
        },
        "boundary": BOUNDARY,
    }


def reconcile_runtime_audit(
    audit: dict[str, Any], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare a fresh full audit against every retained production fact."""
    projected = project_runtime_audit(audit)
    failures: list[dict[str, Any]] = []
    if audit.get("schemaVersion") != RECOVERY_AUDIT_SCHEMA:
        failures.append({
            "validator": "cinematicQueueNativeContractReconciliation",
            "gate": "recovery_audit_schema",
            "sourceFile": "cinematic native carrier audit",
            "expected": RECOVERY_AUDIT_SCHEMA,
            "actual": audit.get("schemaVersion"),
        })
    for gate in (
        "schema",
        "status",
        "sources",
        "queueBaseType",
        "queueHandleType",
        "dispatcherMethods",
        "counts",
        "actionProducerRoutes",
        "conclusion",
        "boundary",
    ):
        if projected.get(gate) != contract.get(gate):
            failures.append({
                "validator": "cinematicQueueNativeContractReconciliation",
                "gate": gate,
                "sourceFile": "cinematic native carrier audit",
                "expected": contract.get(gate),
                "actual": projected.get(gate),
            })
    return failures


__all__ = [
    "ACTION_ROUTE_FIELDS",
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "EXPECTED_COUNTS",
    "EXPECTED_DISPATCHERS",
    "GAMEASSEMBLY_SHA256",
    "METADATA_SHA256",
    "RECOVERY_AUDIT_SCHEMA",
    "SCHEMA",
    "load_cinematic_queue_contract",
    "project_cinematic_queue_contract",
    "project_runtime_audit",
    "reconcile_runtime_audit",
    "validate_cinematic_queue_contract",
]
