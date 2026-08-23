"""Load the build-locked action entity-field formatter contract."""
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
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


SCHEMA = "actionEntityFieldNativeContract.v2"
DEFAULT_CONTRACT = Path(__file__).with_name("action_entity_fields.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-07-11-action-entity-formatter-fields"
CONTRACT_SHA256 = "01FD8D207122F062D212DFB4048712689B5BC6618088D023FFEF55733B65EE42"
_ALLOWED_PROOF_KINDS = {None, "closed_generic_companion_setter_call"}
_CLOSED_GENERIC_COMPANION_PROOF = {
    "key": (694, 11),
    "actionFormatterTypeToken": "0x020018b4",
    "genericDefinitionTypeToken": "0x020015a8",
    "genericDefinitionFieldToken": "0x040062a3",
    "closedGenericCompanionTypeToken": "0x020018b7",
    "deserializeToken": "0x0600941e",
    "deserializeVa": 0x18A2FC9E0,
    "deserializeFileOffset": 170897376,
    "setterToken": "0x06009425",
    "setterVa": 0x18A307B9C,
    "callSites": (
        (857, 0x18A2FCD39, "E85EAE0000"),
        (1205, 0x18A2FCE95, "E802AD0000"),
    ),
}


@lru_cache(maxsize=1)
def load_action_entity_field_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "actionEntityFieldNativeContract", "gate": gate,
                         "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "validationFailures": failures}
    source_sha256 = hashlib.sha256(raw).hexdigest().upper()
    if source_sha256 != CONTRACT_SHA256:
        reject("contract_sha256", CONTRACT_SHA256, source_sha256)
    for gate, expected, actual in (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256,
         (contract.get("metadata") or {}).get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256,
         (contract.get("metadata") or {}).get("metadataSha256")),
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
    for action in contract.get("actions") or []:
        if not isinstance(action, dict):
            reject("action_object", "object", type(action).__name__)
            continue
        key = (action.get("unionTag"), action.get("serializedMemberCount"))
        if not all(isinstance(value, int) for value in key) or key in out:
            reject("unique_action_key", "unique integer pair", key)
            continue
        methods = [action.get("deserialize") or {}]
        methods.extend(action.get("entityFields") or [])
        for method in methods:
            offset = method.get("fileOffset", method.get("setterFileOffset"))
            size = method.get("bodySize", method.get("setterBodySize"))
            expected_hash = method.get("bodySha256", method.get("setterBodySha256"))
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
                reject("method_byte_range", {"offset": "int", "size": ">0"}, method)
                continue
            actual_hash = hashlib.sha256(image[offset:offset + size]).hexdigest().upper()
            if len(image[offset:offset + size]) != size or actual_hash != expected_hash:
                reject("method_body_sha256", expected_hash, actual_hash)
        fields = action.get("entityFields") or []
        proof_kind = action.get("proofKind")
        if proof_kind not in _ALLOWED_PROOF_KINDS:
            reject("proof_kind", sorted(
                value for value in _ALLOWED_PROOF_KINDS if value is not None
            ) + [None], proof_kind)
        if proof_kind == "closed_generic_companion_setter_call":
            proof = _CLOSED_GENERIC_COMPANION_PROOF
            field = fields[0] if len(fields) == 1 else {}
            expected_metadata = {
                "key": proof["key"],
                "actionFormatterTypeToken": proof["actionFormatterTypeToken"],
                "genericDefinitionTypeToken": proof["genericDefinitionTypeToken"],
                "genericDefinitionFieldToken": proof["genericDefinitionFieldToken"],
                "closedGenericCompanionTypeToken": proof[
                    "closedGenericCompanionTypeToken"
                ],
                "deserializeToken": proof["deserializeToken"],
                "deserializeVa": f"0x{proof['deserializeVa']:x}",
                "deserializeFileOffset": proof["deserializeFileOffset"],
                "fieldName": "_value",
                "fieldOrdinal": 10,
                "fieldOffset": "0xe0",
                "setterToken": proof["setterToken"],
                "setterVa": f"0x{proof['setterVa']:x}",
                "callOffsets": [site[0] for site in proof["callSites"]],
                "callVas": [f"0x{site[1]:x}" for site in proof["callSites"]],
                "callTargetVa": f"0x{proof['setterVa']:x}",
            }
            actual_metadata = {
                "key": key,
                "actionFormatterTypeToken": action.get("actionFormatterTypeToken"),
                "genericDefinitionTypeToken": action.get("genericDefinitionTypeToken"),
                "genericDefinitionFieldToken": action.get("genericDefinitionFieldToken"),
                "closedGenericCompanionTypeToken": action.get(
                    "closedGenericCompanionTypeToken"
                ),
                "deserializeToken": (action.get("deserialize") or {}).get(
                    "methodToken"
                ),
                "deserializeVa": (action.get("deserialize") or {}).get(
                    "methodPointerVa"
                ),
                "deserializeFileOffset": (action.get("deserialize") or {}).get(
                    "fileOffset"
                ),
                "fieldName": field.get("fieldName"),
                "fieldOrdinal": field.get("memberOrdinalZeroBased"),
                "fieldOffset": field.get("fieldOffset"),
                "setterToken": field.get("setterToken"),
                "setterVa": field.get("setterPointerVa"),
                "callOffsets": field.get("deserializeDirectCallOffsets"),
                "callVas": field.get("deserializeDirectCallVas"),
                "callTargetVa": field.get("deserializeDirectCallTargetVa"),
            }
            if actual_metadata != expected_metadata:
                reject("closed_generic_companion_metadata", expected_metadata,
                       actual_metadata)
            for call_offset, call_va, expected_hex in proof["callSites"]:
                file_offset = proof["deserializeFileOffset"] + call_offset
                call_bytes = image[file_offset:file_offset + 5]
                actual_hex = call_bytes.hex().upper()
                if len(call_bytes) != 5 or actual_hex != expected_hex:
                    reject("closed_generic_companion_call_bytes", {
                        "fileOffset": file_offset,
                        "hex": expected_hex,
                    }, {
                        "fileOffset": file_offset,
                        "hex": actual_hex,
                    })
                    continue
                relative = int.from_bytes(call_bytes[1:5], "little", signed=True)
                actual_target = call_va + 5 + relative
                if actual_target != proof["setterVa"]:
                    reject("closed_generic_companion_call_target", {
                        "callVa": f"0x{call_va:x}",
                        "targetVa": f"0x{proof['setterVa']:x}",
                    }, {
                        "callVa": f"0x{call_va:x}",
                        "targetVa": f"0x{actual_target:x}",
                    })
        non_entity_value = action.get("nonEntityContract", False)
        if not isinstance(non_entity_value, bool):
            reject("non_entity_contract", "bool", type(non_entity_value).__name__)
        non_entity_contract = non_entity_value is True
        value_layout = action.get("serializedValueLayout") or {}
        expected_layout = {
            "managedType": "Beyond.Gameplay.Actions.Param<Beyond.Gameplay.Core.EntityPtr>",
            "parameterTypeIndex": 85044,
            "fieldTypeIndex": 85046,
            "genericTypeDefinitionToken": "0x02001930",
            "genericArgumentTypeDefinitionToken": "0x02002f3a",
            "outerMemberCount": 4,
            "valueMemberCount": 3,
            "valueFields": ["logicId", "slotId", "useSlotId"],
        }
        if non_entity_contract:
            if action.get("entityFields") != []:
                reject("non_entity_fields", [], action.get("entityFields"))
            if "serializedValueLayout" in action:
                reject("non_entity_serialized_layout", "absent", value_layout)
        else:
            if value_layout != expected_layout:
                reject("serialized_entity_ptr_layout", expected_layout, value_layout)
            ordinals = [field.get("constantPointerOrdinal") for field in fields]
            if ordinals != list(range(len(fields))):
                reject("constant_pointer_ordinals", list(range(len(fields))), ordinals)
        out[key] = action
    if failures:
        out = {}
    return out, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "validationFailures": failures,
    }


__all__ = ["load_action_entity_field_contract", "NATIVE_MAPPING_ID"]
