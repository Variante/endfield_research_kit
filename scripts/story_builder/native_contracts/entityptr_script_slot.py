"""Validate the pinned EntityPtr current-script slot resolution contract."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

if __package__ == "scripts.story_builder.native_contracts":
    from ...common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
elif __package__ == "story_builder.native_contracts":
    from common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
else:  # pragma: no cover
    raise ImportError(f"unsupported package identity: {__package__!r}")

SCHEMA = "entityPtrScriptSlotNativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("entityptr_script_slot.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-07-11-entityptr-current-script-slot"
CONTRACT_SHA256 = "0860E7776282C3C9465168FC5811531BC17E32B1C158D9C8FA73E9E4FDE6747D"


@lru_cache(maxsize=1)
def load_entityptr_script_slot_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrScriptSlotNativeContract",
                         "gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "validationFailures": failures}
    actual_contract_hash = hashlib.sha256(raw).hexdigest().upper()
    if actual_contract_hash != CONTRACT_SHA256:
        reject("contract_sha256", CONTRACT_SHA256, actual_contract_hash)
    metadata = contract.get("metadata") or {}
    for gate, expected, actual in (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("native_mapping_id", NATIVE_MAPPING_ID, contract.get("nativeMappingId")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, metadata.get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256, metadata.get("metadataSha256")),
    ):
        if actual != expected:
            reject(gate, expected, actual)
    native = check_installed_native_inputs(GAMEASSEMBLY_SHA256, METADATA_SHA256)
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    gameassembly = getattr(native, "gameassembly", None)
    if gameassembly is None:
        gameassembly = getattr(native, "gameAssembly", None)
    try:
        image = Path(gameassembly).read_bytes() if gameassembly else b""
    except OSError as error:
        image = b""
        reject("read_gameassembly", True, str(error)[:400])
    methods: dict[str, dict[str, Any]] = {}
    for method in contract.get("methods") or []:
        method_id = method.get("id")
        if not isinstance(method_id, str) or not method_id or method_id in methods:
            reject("unique_method_id", "unique nonempty string", method_id)
            continue
        methods[method_id] = method
        offset, size = method.get("fileOffset"), method.get("bodySize")
        expected_hash = method.get("bodySha256")
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
            reject("method_byte_range", {"offset": "int", "size": ">0"}, method)
            continue
        body = image[offset:offset + size]
        actual_hash = hashlib.sha256(body).hexdigest().upper()
        if len(body) != size or actual_hash != str(expected_hash).upper():
            reject("method_body_sha256", {"methodId": method_id, "sha256": expected_hash},
                   {"methodId": method_id, "size": len(body), "sha256": actual_hash})
    for call in contract.get("directCalls") or []:
        method = methods.get(call.get("methodId")) or {}
        body_offset, call_offset = method.get("fileOffset"), call.get("offset")
        try:
            expected_target = int(str(call.get("targetVa")), 16)
            method_va = int(str(method.get("methodPointerVa")), 16)
        except (TypeError, ValueError):
            reject("direct_call_metadata", "hex VAs", call)
            continue
        if not isinstance(body_offset, int) or not isinstance(call_offset, int):
            reject("direct_call_metadata", "integer offsets", call)
            continue
        call_bytes = image[body_offset + call_offset:body_offset + call_offset + 5]
        actual_hex = call_bytes.hex().upper()
        if len(call_bytes) != 5 or call_bytes[:1] != b"\xE8":
            reject("direct_call_opcode", {"methodId": call.get("methodId"),
                   "offset": call_offset, "opcode": "E8"}, actual_hex)
            continue
        relative = int.from_bytes(call_bytes[1:], "little", signed=True)
        actual_target = method_va + call_offset + 5 + relative
        if actual_target != expected_target:
            reject("direct_call_target", {"target": call.get("target"),
                   "targetVa": f"0x{expected_target:x}"}, f"0x{actual_target:x}")
    for sequence in contract.get("criticalByteSequences") or []:
        method = methods.get(sequence.get("methodId")) or {}
        offset, relative = method.get("fileOffset"), sequence.get("offset")
        try:
            expected = bytes.fromhex(str(sequence.get("hex") or ""))
        except ValueError:
            expected = b""
        if not isinstance(offset, int) or not isinstance(relative, int) or not expected:
            reject("critical_flow_metadata", "valid method/offset/hex", sequence)
            continue
        actual = image[offset + relative:offset + relative + len(expected)]
        if actual != expected:
            reject("critical_flow_bytes", sequence,
                   {"methodId": sequence.get("methodId"), "offset": relative,
                    "hex": actual.hex().upper()})
    audit = {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
             "nativeMappingId": NATIVE_MAPPING_ID, "validationFailures": failures}
    return (contract if not failures else {}), audit


__all__ = ["load_entityptr_script_slot_contract", "NATIVE_MAPPING_ID"]
