"""Load the reviewed current-build cross-system consumer contract.

The contract is a checked-in native profile, not a generated recovery report.
Mission Pipeline reads it directly and exposes no native conclusion when the
profile or the installed IL2CPP inputs drift.
"""
from __future__ import annotations

from scripts.game_data.contracts import CONTRACTS_DIR
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_MISSING,
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
)


SCHEMA = "nativeCrossSystemConsumerCensus.v4"
AUDIT_SCHEMA = "crossSystemConsumersNativeContractAudit.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "cross_system_consumers.json"
#: Counts that are review conclusions: each must stay zero. Every other count
#: is census data, checked for consistency with the rows it summarises.
ZERO_CONCLUSIONS = {
    "summary": (
        "missionLevelScriptCallers", "tripleOrGreaterFamilyCallers", "unreviewedCallers",
        "storyBindingsAdded", "missionOrderEdgesAdded",
    ),
    "directConsumerClosure": ("levelScriptMethods", "storyMethods", "unreviewedIndirectSites"),
    "missionRuntimeSurface": ("crossFamilyMethodSignatures", "trackingMissionFieldWrites", "unreviewedCallers"),
    "managedCallableSurface": ("crossIdentityCallableFields", "missionLevelScriptBindings", "unreviewedBindingCallers"),
}
PENDING_FIELD_NAME = "m_pendingRefreshCompSet"

from scripts.common import repo_path as _source_file


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

    summary = contract.get("summary") or {}
    closure = contract.get("directConsumerClosure") or {}
    deferred = contract.get("deferredRefreshClosure") or {}
    mission_runtime = contract.get("missionRuntimeSurface") or {}
    callable_surface = contract.get("managedCallableSurface") or {}
    validation = contract.get("validation") or {}
    rows = [row for row in contract.get("rows") or [] if isinstance(row, dict)]
    row_classes = dict(Counter(str(row.get("classification") or "") for row in rows))
    exact_gates = (
        ("schema", SCHEMA, contract.get("schemaVersion")),
        ("validation_status", "passed", validation.get("status")),
        ("validation_failures", [], validation.get("failures")),
        ("cross_system_callers", len(rows), summary.get("crossSystemCallers")),
        ("row_classification_counts", summary.get("classificationCounts"), row_classes),
        ("deferred_pending_field", PENDING_FIELD_NAME, (deferred.get("pendingField") or {}).get("name")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    sections = {
        "summary": summary,
        "directConsumerClosure": closure.get("counts") or {},
        "missionRuntimeSurface": mission_runtime.get("counts") or {},
        "managedCallableSurface": callable_surface.get("counts") or {},
    }
    for section, keys in ZERO_CONCLUSIONS.items():
        for key in keys:
            if sections[section].get(key) != 0:
                reject(f"{section}.{key}", 0, sections[section].get(key))
    if not isinstance(deferred.get("counts"), dict) or not deferred["counts"]:
        reject("deferred_counts", "recorded", deferred.get("counts"))
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

    source = contract.get("source") or {}
    native = check_installed_native_inputs(
        str(source.get("gameAssemblySha256") or ""),
        str(source.get("globalMetadataSha256") or ""),
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
    "PENDING_FIELD_NAME",
    "SCHEMA",
    "ZERO_CONCLUSIONS",
    "load_cross_system_consumers_contract",
    "project_cross_system_consumers",
    "validate_cross_system_consumers",
]
