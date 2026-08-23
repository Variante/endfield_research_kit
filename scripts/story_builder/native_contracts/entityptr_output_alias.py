"""Validate pinned EntityPtr producer-output alias and non-alias facts."""
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

SCHEMA = "entityPtrOutputAliasNativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("entityptr_output_alias.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-07-11-entityptr-producer-output-alias"
CONTRACT_SHA256 = "F3B7E7D72EA7030EEF7E02D27983C32CE4FE2576405F0B037BA5E4FB1E2B3E3B"

_EXPECTED_SHAPES = {
    (18, 19): ("entityPtr", "_targetEntity", "aliases_filter_when_guard_matches"),
    (160, 16): ("_entity", "_filterEntity", "aliases_filter_when_guard_matches"),
    (189, 20): ("_entityOutput", "_spawnerEntity", "validated_non_alias"),
    (913, 12): ("_entity", None, "validated_non_alias"),
}


@lru_cache(maxsize=1)
def load_entityptr_output_alias_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrOutputAliasNativeContract",
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

    out: dict[tuple[int, int], dict[str, Any]] = {}
    for producer in contract.get("producers") or []:
        key = (producer.get("unionTag"), producer.get("serializedMemberCount"))
        if key not in _EXPECTED_SHAPES or key in out:
            reject("unique_known_shape", sorted(_EXPECTED_SHAPES), key)
            continue
        output_name, filter_name, alias_status = _EXPECTED_SHAPES[key]
        actual_shape = (
            (producer.get("outputField") or {}).get("fieldName"),
            (producer.get("filterField") or {}).get("fieldName"),
            producer.get("aliasStatus"),
        )
        if actual_shape != (output_name, filter_name, alias_status):
            reject("shape_semantics", (output_name, filter_name, alias_status), actual_shape)
        if key == (18, 19):
            guard = producer.get("guard") or {}
            expected_guard = {
                "fieldName": "_triggerTarget",
                "memberOrdinalZeroBased": 17,
                "fieldOffset": "0x80",
                "enumTypeToken": "0x02001923",
                "requiredName": "SPECIFY_ENTITY",
                "requiredValue": 1,
                "serializedBytesBetweenFilterAndOutput":
                    "04FFFFFFFFFFFFFFFF00000000FFFFFFFFFF01000000",
            }
            if guard != expected_guard:
                reject("specify_entity_guard", expected_guard, guard)
        if key == (913, 12):
            expected_runtime_list_flow = {
                "producerRole": "action",
                "actionName": "Beyond.Gameplay.Actions.RepeatEntityPtrListAction",
                "actionTypeToken": "0x0200174a",
                "runtimeInputField": {
                    "fieldName": "_entityList",
                    "fieldTypeIndex": 84876,
                    "fieldToken": "0x0400673a",
                },
            }
            actual_runtime_list_flow = {
                key: producer.get(key) for key in expected_runtime_list_flow
            }
            if actual_runtime_list_flow != expected_runtime_list_flow:
                reject("runtime_list_element_flow", expected_runtime_list_flow,
                       actual_runtime_list_flow)
            expected_output = {
                "fieldName": "_entity",
                "memberOrdinalZeroBased": 9,
                "fieldType": (
                    "Beyond.Gameplay.Actions.ParamOutput<"
                    "Beyond.Gameplay.Core.EntityPtr>"
                ),
                "fieldTypeIndex": 84695,
                "fieldOffset": "0xd8",
            }
            if producer.get("outputField") != expected_output:
                reject("runtime_list_output_field", expected_output,
                       producer.get("outputField"))
            expected_method_tokens = {
                "deserialize": "0x0600b211",
                "output_setter": "0x0600b209",
                "execute": "0x06008ad4",
                "try_get_valid_entity": "0x06008ad5",
            }
            actual_method_tokens = {
                method.get("id"): method.get("token")
                for method in producer.get("methods") or []
            }
            if actual_method_tokens != expected_method_tokens:
                reject("runtime_list_method_flow", expected_method_tokens,
                       actual_method_tokens)
        for method in producer.get("methods") or []:
            offset, size = method.get("fileOffset"), method.get("bodySize")
            expected_hash = str(method.get("bodySha256") or "").upper()
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
                reject("method_byte_range", {"offset": "int", "size": ">0"}, method)
                continue
            body = image[offset:offset + size]
            actual_hash = hashlib.sha256(body).hexdigest().upper()
            if len(body) != size or actual_hash != expected_hash:
                reject("method_body_sha256", {"shape": key, "method": method.get("id"),
                       "sha256": expected_hash}, {"size": len(body), "sha256": actual_hash})
        out[key] = producer
    if set(out) != set(_EXPECTED_SHAPES):
        reject("complete_shape_set", sorted(_EXPECTED_SHAPES), sorted(out))
    if failures:
        out = {}
    return out, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "validationFailures": failures,
    }


__all__ = ["load_entityptr_output_alias_contract", "NATIVE_MAPPING_ID"]
