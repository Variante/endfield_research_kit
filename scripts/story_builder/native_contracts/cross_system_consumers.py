"""Load the reviewed current-build cross-system consumer contract.

The contract is a checked-in native profile, not a generated recovery report.
Mission Pipeline reads it directly and exposes no native conclusion when the
profile or the installed IL2CPP inputs drift.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
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


SCHEMA = "nativeCrossSystemConsumerCensus.v4"
AUDIT_SCHEMA = "crossSystemConsumersNativeContractAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("cross_system_consumers.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
EXPECTED_CLASS_COUNTS = {
    "mission_state_controls_dynamic_component_availability": 4,
    "shared_trigger_geometry_adapter": 3,
    "global_level_load_synchronization": 1,
    "story_dynamic_scene_visual_context": 8,
    "mission_or_dialog_alternate_action_consumer": 1,
}
EXPECTED_DIRECT_CLOSURE = {
    "seedMethods": 4,
    "reachableMethods": 23,
    "directEdges": 30,
    "maximumDepth": 2,
    "levelScriptMethods": 0,
    "storyMethods": 0,
    "reviewedIndirectSites": 1,
    "unreviewedIndirectSites": 0,
}
EXPECTED_DEFERRED_COUNTS = {
    "enqueueWriters": 2,
    "scheduledReaders": 1,
    "fieldWriterReferences": 1,
    "fieldReaderReferences": 3,
    "refreshEntityStatusTargets": 1,
    "conditionUpdateTargets": 1,
}
EXPECTED_PENDING_FIELD = {
    "name": "m_pendingRefreshCompSet",
    "token": "0x0400e5f9",
    "offset": "0x48",
}
EXPECTED_MISSION_RUNTIME_COUNTS = {
    "missionIdentityTypes": 174,
    "familyTargetPointers": 4322,
    "crossSystemCallers": 2,
    "missionRuntimeLevelScriptCallers": 1,
    "missionRuntimeStoryCallers": 1,
    "crossFamilyMethodSignatures": 0,
    "trackingMissionFieldWrites": 0,
    "trackingSceneFieldWrites": 3,
    "unreviewedCallers": 0,
}
EXPECTED_CALLABLE_COUNTS = {
    "callableFields": 13,
    "missionRuntimeCallableFields": 9,
    "levelScriptCallableFields": 4,
    "crossIdentityCallableFields": 0,
    "callableEntryMethods": 5,
    "callableEntryTargetPointers": 5,
    "directBindingCalls": 5,
    "missionLevelScriptBindings": 0,
    "unreviewedBindingCallers": 0,
}


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_cross_system_consumers(
    contract: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    """Return bounded, deterministic failures for a contract payload."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "crossSystemConsumersNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    source = contract.get("source") or {}
    summary = contract.get("summary") or {}
    closure = contract.get("directConsumerClosure") or {}
    deferred = contract.get("deferredRefreshClosure") or {}
    mission_runtime = contract.get("missionRuntimeSurface") or {}
    callable_surface = contract.get("managedCallableSurface") or {}
    validation = contract.get("validation") or {}
    exact_gates = (
        ("schema", SCHEMA, contract.get("schemaVersion")),
        ("validation_status", "passed", validation.get("status")),
        ("validation_failures", [], validation.get("failures")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, str(source.get("gameAssemblySha256") or "").upper()),
        ("metadata_sha256", METADATA_SHA256, str(source.get("globalMetadataSha256") or "").upper()),
        ("cross_system_callers", 17, summary.get("crossSystemCallers")),
        ("mission_levelscript_callers", 0, summary.get("missionLevelScriptCallers")),
        ("triple_family_callers", 0, summary.get("tripleOrGreaterFamilyCallers")),
        ("unreviewed_callers", 0, summary.get("unreviewedCallers")),
        ("story_bindings_added", 0, summary.get("storyBindingsAdded")),
        ("mission_order_edges_added", 0, summary.get("missionOrderEdgesAdded")),
        ("classification_counts", EXPECTED_CLASS_COUNTS, summary.get("classificationCounts")),
        ("row_classification_counts", EXPECTED_CLASS_COUNTS, dict(Counter(
            str(row.get("classification") or "")
            for row in contract.get("rows") or []
            if isinstance(row, dict)
        ))),
        ("direct_closure_counts", EXPECTED_DIRECT_CLOSURE, closure.get("counts")),
        ("deferred_pending_field", EXPECTED_PENDING_FIELD, deferred.get("pendingField")),
        ("deferred_counts", EXPECTED_DEFERRED_COUNTS, deferred.get("counts")),
        ("mission_runtime_counts", EXPECTED_MISSION_RUNTIME_COUNTS, mission_runtime.get("counts")),
        ("managed_callable_counts", EXPECTED_CALLABLE_COUNTS, callable_surface.get("counts")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    return failures


def project_cross_system_consumers(
    contract: dict[str, Any], *, source_file: str, source_sha256: str
) -> dict[str, Any]:
    """Project the reviewed rows into the stable Mission Pipeline contract."""
    source = contract["source"]
    method = contract["method"]
    summary = contract["summary"]
    closure = contract["directConsumerClosure"]
    closure_counts = closure["counts"]
    deferred = contract["deferredRefreshClosure"]
    mission_runtime = contract["missionRuntimeSurface"]
    callable_surface = contract["managedCallableSurface"]
    classifications = summary["classificationCounts"]
    return {
        "schema": AUDIT_SCHEMA,
        "status": NATIVE_EVIDENCE_VALIDATED,
        "source": source_file,
        "sourceSha256": source_sha256,
        "method": " ".join(filter(None, [
            str(method.get("selection") or ""),
            str(closure.get("method") or ""),
        ])),
        "counts": {
            "mappedMethodPointers": method.get("mappedMethodPointers", 0),
            "familyTargetPointers": method.get("familyTargetPointers", 0),
            "crossSystemCallers": summary.get("crossSystemCallers", 0),
            "missionStateDynamicSceneCallers": classifications.get(
                "mission_state_controls_dynamic_component_availability", 0
            ),
            "missionLevelScriptCallers": summary.get("missionLevelScriptCallers", 0),
            "tripleOrGreaterFamilyCallers": summary.get("tripleOrGreaterFamilyCallers", 0),
            "dynamicSceneStoryCallers": classifications.get(
                "story_dynamic_scene_visual_context", 0
            ),
            "unreviewedCallers": summary.get("unreviewedCallers", 0),
            "closureReachableMethods": closure_counts.get("reachableMethods", 0),
            "closureDirectEdges": closure_counts.get("directEdges", 0),
            "closureLevelScriptMethods": closure_counts.get("levelScriptMethods", 0),
            "closureStoryMethods": closure_counts.get("storyMethods", 0),
            "unreviewedIndirectSites": closure_counts.get("unreviewedIndirectSites", 0),
        },
        "classifications": classifications,
        "rows": contract["rows"],
        "deferredRefreshClosure": deferred,
        "missionRuntimeSurface": mission_runtime,
        "managedCallableSurface": callable_surface,
        "finding": contract.get("finding"),
        "boundary": contract.get("boundary"),
        "relatedOriginalFiles": [{
            "sourceFile": source.get("gameAssembly"),
            "sha256": source.get("gameAssemblySha256"),
            "role": "native consumer and deferred refresh implementation",
        }, {
            "sourceFile": source.get("globalMetadata"),
            "sha256": source.get("globalMetadataSha256"),
            "role": "managed identities and runtime field layout",
        }],
        "classification": deferred.get(
            "classification", "binary_cross_system_consumers_reviewed"
        ),
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "hash_locked_direct_and_deferred_native_closure",
        "validationFailures": [],
    }


def load_cross_system_consumers_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Load the contract only for its exact installed native build."""
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
            "validator": "crossSystemConsumersNativeContract",
            "gate": "read_valid_json",
            "sourceFile": source_file,
            "expected": {"readableJsonObject": True},
            "actual": str(error)[:400],
        })
    if contract:
        failures.extend(validate_cross_system_consumers(contract, source_file))

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        failures.append({
            "validator": "crossSystemConsumersNativeContract",
            "gate": "installed_native_inputs",
            "sourceFile": source_file,
            "expected": {"status": NATIVE_EVIDENCE_VALIDATED},
            "actual": {"status": native.status, "detail": native.detail},
        })
    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    if not failures:
        return project_cross_system_consumers(
            contract, source_file=source_file, source_sha256=source_sha256
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
        "source": source_file,
        "sourceSha256": source_sha256,
        "finding": "",
        "validationFailures": failures,
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
    }


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "EXPECTED_CALLABLE_COUNTS",
    "EXPECTED_CLASS_COUNTS",
    "EXPECTED_DEFERRED_COUNTS",
    "EXPECTED_DIRECT_CLOSURE",
    "EXPECTED_MISSION_RUNTIME_COUNTS",
    "EXPECTED_PENDING_FIELD",
    "GAMEASSEMBLY_SHA256",
    "METADATA_SHA256",
    "SCHEMA",
    "load_cross_system_consumers_contract",
    "project_cross_system_consumers",
    "validate_cross_system_consumers",
]
