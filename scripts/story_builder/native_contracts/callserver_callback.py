"""Load and gate the reviewed CallServer callback native contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
except ImportError:  # pragma: no cover - package import identity
    from scripts.common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )


SCHEMA = "callServerCallbackNativeContract.v1"
AUDIT_SCHEMA = "callServerCallbackNativeContractAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("callserver_callback.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_callserver_callback_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Return the contract only when its file and installed build both match."""

    path = Path(contract_path)
    source_file = _source_file(path)
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "callServerCallbackNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    try:
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", {"readableJsonObject": True}, str(error)[:400])
        return {
            "schema": AUDIT_SCHEMA,
            "status": (
                NATIVE_EVIDENCE_MISSING
                if isinstance(error, OSError)
                else NATIVE_EVIDENCE_MISMATCHED
            ),
            "sourceFile": source_file,
            "sourceSha256": "",
            "nativeContract": {},
            "validationFailures": failures,
            "usesOcrOrManualOrder": False,
        }

    source_sha256 = hashlib.sha256(raw).hexdigest().upper()
    if not isinstance(contract, dict):
        reject("contract_object", {"type": "object"}, {
            "type": type(contract).__name__,
        })
        contract = {}
    sources = (
        contract.get("sources")
        if isinstance(contract.get("sources"), dict)
        else {}
    )
    call_server = (
        contract.get("callServer")
        if isinstance(contract.get("callServer"), dict)
        else {}
    )
    action_base = (
        contract.get("actionBase")
        if isinstance(contract.get("actionBase"), dict)
        else {}
    )
    validation = (
        contract.get("validation")
        if isinstance(contract.get("validation"), dict)
        else {}
    )
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        (
            "gameassembly_sha256",
            GAMEASSEMBLY_SHA256,
            sources.get("gameAssemblySha256"),
        ),
        ("metadata_sha256", METADATA_SHA256, sources.get("globalMetadataSha256")),
        ("execute_method_token", "0x06008f04", call_server.get("executeMethodToken")),
        ("execute_method_va", "0x1845f6000", call_server.get("executeMethodVa")),
        ("output_field_token", "0x040069fe", call_server.get("outputFieldToken")),
        ("output_field_offset", "this+0xd8", call_server.get("outputFieldOffset")),
        (
            "set_wait_method_token",
            "0x06007e87",
            action_base.get("setWaitMethodToken"),
        ),
        ("set_wait_method_va", "0x1875f1180", action_base.get("setWaitMethodVa")),
        (
            "wait_header_uid_list_offset",
            "this+0x80",
            action_base.get("waitHeaderUidListOffset"),
        ),
        ("byte_gate_count", 4, len(validation.get("byteGates") or [])),
        ("native_validation_failures", [], validation.get("validationFailures")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

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
            else NATIVE_EVIDENCE_MISMATCHED
        )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "nativeContract": contract if not failures else {},
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }
