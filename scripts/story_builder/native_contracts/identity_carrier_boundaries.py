"""Load the reviewed negative boundaries for managed identity carriers."""
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


SCHEMA = "identityCarrierNegativeBoundaries.v1"
AUDIT_SCHEMA = "identityCarrierNegativeBoundariesAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("identity_carrier_boundaries.json")
DEFAULT_IFIX_AUDIT = (
    Path(__file__).resolve().parents[3]
    / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
IFIX_PATCH_SHA256 = (
    "737134081E06371F13C073988547E887037FCCF2F57E1052BE35DD255D27BC21"
)
BOUNDARY_IDS = (
    "mission_option_alternate_actions",
    "mission_property_script_pointer",
    "implicit_current_mission_context",
    "direct_managed_identity_carriers",
    "nested_managed_identity_carriers",
)


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> tuple[dict[str, Any], bytes, str | None]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, b"", str(error)[:400]
    if not isinstance(payload, dict):
        return {}, raw, f"expected object, found {type(payload).__name__}"
    return payload, raw, None


def load_identity_carrier_boundaries_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    ifix_audit_path: Path = DEFAULT_IFIX_AUDIT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Expose the negative conclusions only when their build gates match."""

    path = Path(contract_path)
    source_file = _source_file(path)
    failures: list[dict[str, Any]] = []

    def reject(
        gate: str,
        expected: Any,
        actual: Any,
        source: str = source_file,
    ) -> None:
        failures.append({
            "validator": "identityCarrierNegativeBoundaries",
            "gate": gate,
            "sourceFile": source,
            "expected": expected,
            "actual": actual,
        })

    contract, raw, error = _read_json(path)
    if error:
        reject("read_valid_contract", {"readableJsonObject": True}, error)
    sources = (
        contract.get("sources")
        if isinstance(contract.get("sources"), dict)
        else {}
    )
    boundaries = (
        contract.get("boundaries")
        if isinstance(contract.get("boundaries"), list)
        else []
    )
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        (
            "gameassembly_sha256",
            GAMEASSEMBLY_SHA256,
            sources.get("gameAssemblySha256"),
        ),
        (
            "metadata_sha256",
            METADATA_SHA256,
            sources.get("globalMetadataSha256"),
        ),
        (
            "ifix_patch_sha256",
            IFIX_PATCH_SHA256,
            sources.get("ifixPatchSha256"),
        ),
        (
            "boundary_ids",
            list(BOUNDARY_IDS),
            [row.get("id") for row in boundaries if isinstance(row, dict)],
        ),
        (
            "story_bindings_added",
            [0] * len(BOUNDARY_IDS),
            [
                row.get("storyBindingsAdded")
                for row in boundaries
                if isinstance(row, dict)
            ],
        ),
        (
            "mission_order_edges_added",
            [0] * len(BOUNDARY_IDS),
            [
                row.get("missionOrderEdgesAdded")
                for row in boundaries
                if isinstance(row, dict)
            ],
        ),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    ifix_path = Path(ifix_audit_path)
    ifix, _ifix_raw, ifix_error = _read_json(ifix_path)
    if ifix_error:
        reject(
            "read_valid_ifix_audit",
            {"readableJsonObject": True},
            ifix_error,
            _source_file(ifix_path),
        )
    else:
        ifix_sha = str((ifix.get("source") or {}).get("patchSha256") or "").upper()
        if ifix_sha != IFIX_PATCH_SHA256:
            reject(
                "ifix_source_hash",
                IFIX_PATCH_SHA256,
                ifix_sha or "<missing>",
                _source_file(ifix_path),
            )

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_native_inputs",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {"status": native.status, "detail": native.detail},
        )

    status = NATIVE_EVIDENCE_VALIDATED
    if failures:
        status = (
            native.status
            if native.status != NATIVE_EVIDENCE_VALIDATED
            else NATIVE_EVIDENCE_MISSING
            if error or ifix_error
            else NATIVE_EVIDENCE_MISMATCHED
        )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": hashlib.sha256(raw).hexdigest().upper() if raw else "",
        "boundaries": boundaries if not failures else [],
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }


__all__ = [
    "AUDIT_SCHEMA",
    "BOUNDARY_IDS",
    "DEFAULT_CONTRACT",
    "DEFAULT_IFIX_AUDIT",
    "GAMEASSEMBLY_SHA256",
    "IFIX_PATCH_SHA256",
    "METADATA_SHA256",
    "SCHEMA",
    "load_identity_carrier_boundaries_contract",
]
