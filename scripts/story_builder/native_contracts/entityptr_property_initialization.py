"""Validate pinned, diagnostic-only EntityPtr brief-property initialization facts."""
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

SCHEMA = "entityPtrPropertyInitializationNativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("entityptr_property_initialization.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-08-22-entityptr-property-initialization"
CONTRACT_SHA256 = "E7709921BA38DD73D1D50E5AE8063D723224362E4FA932CB720CCD94E99D2D0F"

_EXPECTED_METHODS = {
    "level_script_runtime_init": ("0x0601218d", "0x183179e50"),
    "level_script_runtime_setup": ("0x0601218e", "0x182fdc3a0"),
    "reset_action_graph_param_blackboard": ("0x06012197", "0x184254c10"),
    "param_blackboard_load_value": ("0x06003523", "0x182fd3850"),
}


def _parse_va(value: Any) -> int:
    return int(str(value), 16)


@lru_cache(maxsize=1)
def load_entityptr_property_initialization_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrPropertyInitializationNativeContract",
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
    expected_scalars = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated_initial_entityptr_value_nonfinal", contract.get("status")),
        ("native_mapping_id", NATIVE_MAPPING_ID, contract.get("nativeMappingId")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, metadata.get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256, metadata.get("metadataSha256")),
    )
    for gate, expected, actual in expected_scalars:
        if actual != expected:
            reject(gate, expected, actual)
    expected_enum = {"declaringType": "Beyond.GEnums.ParamRealType",
                     "declaringTypeToken": "0x020009d3", "fieldName": "EntityPtr",
                     "fieldToken": "0x0400249b", "value": 13}
    if contract.get("paramRealType") != expected_enum:
        reject("param_real_type_entityptr_identity", expected_enum, contract.get("paramRealType"))
    expected_brief = {"declaringType": "Beyond.Gameplay.LevelScriptBriefData",
                      "declaringTypeToken": "0x020003d0",
                      "propertiesFieldToken": "0x04001914",
                      "refWorldEntityIdListFieldToken": "0x04001913", "paramSource": 200}
    if contract.get("briefProperties") != expected_brief:
        reject("source200_brief_property_identity", expected_brief, contract.get("briefProperties"))
    boundary = contract.get("lifecycleBoundary") or {}
    expected_boundary = {"classification": "validated_initial_entityptr_value_nonfinal",
                         "mutableAfterBind": True, "diagnosticOnly": True,
                         "allowTargetPromotion": False}
    for key, expected in expected_boundary.items():
        if boundary.get(key) != expected:
            reject(f"lifecycle_boundary_{key}", expected, boundary.get(key))

    native = check_installed_native_inputs(GAMEASSEMBLY_SHA256, METADATA_SHA256)
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    gameassembly = getattr(native, "gameassembly", None) or getattr(native, "gameAssembly", None)
    try:
        image = Path(gameassembly).read_bytes() if gameassembly else b""
    except OSError as error:
        image = b""
        reject("read_gameassembly", True, str(error)[:400])

    methods: dict[str, dict[str, Any]] = {}
    for method in contract.get("methods") or []:
        method_id = method.get("id")
        if method_id not in _EXPECTED_METHODS or method_id in methods:
            reject("unique_known_method", sorted(_EXPECTED_METHODS), method_id)
            continue
        expected_identity = _EXPECTED_METHODS[method_id]
        actual_identity = (method.get("token"), method.get("virtualAddress"))
        if actual_identity != expected_identity:
            reject("method_identity", {"id": method_id, "identity": expected_identity}, actual_identity)
        offset, size = method.get("fileOffset"), method.get("bodySize")
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
            reject("method_byte_range", {"offset": "int", "size": ">0"}, method)
            continue
        body = image[offset:offset + size]
        actual_hash = hashlib.sha256(body).hexdigest().upper()
        expected_hash = str(method.get("bodySha256") or "").upper()
        if len(body) != size or actual_hash != expected_hash:
            reject("method_body_sha256", {"id": method_id, "sha256": expected_hash},
                   {"size": len(body), "sha256": actual_hash})
        methods[method_id] = method
    if set(methods) != set(_EXPECTED_METHODS):
        reject("complete_method_set", sorted(_EXPECTED_METHODS), sorted(methods))

    seen_calls: set[tuple[str, int]] = set()
    for call in contract.get("criticalCalls") or []:
        caller, call_offset = call.get("caller"), call.get("callOffset")
        key = (caller, call_offset)
        if caller not in methods or not isinstance(call_offset, int) or key in seen_calls:
            reject("unique_valid_critical_call", True, key)
            continue
        seen_calls.add(key)
        method = methods[caller]
        pos = method["fileOffset"] + call_offset
        actual_bytes = image[pos:pos + 5]
        expected_bytes = bytes.fromhex(str(call.get("callBytes") or ""))
        if len(actual_bytes) != 5 or actual_bytes[:1] != b"\xe8" or actual_bytes != expected_bytes:
            reject("direct_call_bytes", {"caller": caller, "offset": call_offset,
                   "bytes": expected_bytes.hex().upper()}, actual_bytes.hex().upper())
            continue
        relative = int.from_bytes(actual_bytes[1:5], "little", signed=True)
        actual_target = _parse_va(method["virtualAddress"]) + call_offset + 5 + relative
        expected_target = _parse_va(call.get("targetVa"))
        if actual_target != expected_target:
            reject("direct_call_target", {"caller": caller, "offset": call_offset,
                   "target": hex(expected_target)}, hex(actual_target))
    expected_calls = {("level_script_runtime_init", offset) for offset in (157, 171, 181, 206)}
    expected_calls |= {("level_script_runtime_setup", 757),
                       ("level_script_runtime_setup", 789),
                       ("reset_action_graph_param_blackboard", 135)}
    if seen_calls != expected_calls:
        reject("complete_critical_call_set", sorted(expected_calls), sorted(seen_calls))
    ordering = contract.get("ordering") or {}
    if not (ordering.get("setupResetCallOffset") == 757
            and ordering.get("setupActionContextBindCallOffset") == 789
            and 757 < 789
            and ordering.get("requiredRelation") == "reset_and_load_before_action_context_bind"):
        reject("reset_load_before_bind_order", "757 < 789", ordering)

    if failures:
        contract = {}
    return contract, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "classification": "validated_initial_entityptr_value_nonfinal",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "allowTargetPromotion": False,
        "validationFailures": failures,
    }


__all__ = ["load_entityptr_property_initialization_contract", "NATIVE_MAPPING_ID"]
