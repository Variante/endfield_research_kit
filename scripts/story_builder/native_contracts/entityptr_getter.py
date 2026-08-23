"""Validate pinned EntityPtr getter semantics and formatter boundaries."""
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

SCHEMA = "entityPtrGetterNativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("entityptr_getter.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-07-11-entityptr-getter-semantics"
CONTRACT_SHA256 = "41D2EF61CB94E3B4C43FA6D01D5B3BF63EF552E56D56C793DF71981675712E14"
_KINDS = {(49, 9): "runtime_event_args_key", (309, 7): "runtime_zero_field_entity_unresolved",
          (383, 8): "constant_param_alias", (729, 8): "runtime_levelscript_property",
          (825, 9): "runtime_list_index_duplicate_unresolved", (995, 8): "constant_proxy_id_lookup"}

@lru_cache(maxsize=1)
def load_entityptr_getter_contract(contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrGetterNativeContract", "gate": gate,
                         "expected": expected, "actual": actual})
    try:
        raw = Path(contract_path).read_bytes(); contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400]); return {}, {"status": "validation_failed", "validationFailures": failures}
    actual_hash = hashlib.sha256(raw).hexdigest().upper()
    if actual_hash != CONTRACT_SHA256: reject("contract_sha256", CONTRACT_SHA256, actual_hash)
    metadata = contract.get("metadata") or {}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")), ("status", "validated", contract.get("status")),
        ("native_mapping_id", NATIVE_MAPPING_ID, contract.get("nativeMappingId")), ("gameassembly_sha256", GAMEASSEMBLY_SHA256, metadata.get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256, metadata.get("metadataSha256"))):
        if actual != expected: reject(gate, expected, actual)
    native = check_installed_native_inputs(GAMEASSEMBLY_SHA256, METADATA_SHA256)
    if native.status != NATIVE_EVIDENCE_VALIDATED: reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED, {"status": native.status, "detail": native.detail})
    gameassembly = getattr(native, "gameassembly", None) or getattr(native, "gameAssembly", None)
    try: image = Path(gameassembly).read_bytes() if gameassembly else b""
    except OSError as error: image = b""; reject("read_gameassembly", True, str(error)[:400])
    out = {}
    for getter in contract.get("getters") or []:
        key = (getter.get("unionTag"), getter.get("serializedMemberCount"))
        if key not in _KINDS or key in out: reject("unique_known_shape", sorted(_KINDS), key); continue
        if getter.get("resolutionKind") != _KINDS[key]: reject("resolution_kind", _KINDS[key], getter.get("resolutionKind"))
        methods = [getter.get("getResult") or {}]
        formatter = getter.get("formatter") or {}
        if formatter:
            methods.extend([{"fileOffset": formatter.get("deserializeFileOffset"), "bodySize": formatter.get("deserializeBodySize"), "bodySha256": formatter.get("deserializeBodySha256")},
                            {"fileOffset": formatter.get("setterFileOffset"), "bodySize": formatter.get("setterBodySize"), "bodySha256": formatter.get("setterBodySha256")}])
        for method in methods:
            if not method: continue
            offset, size, expected = method.get("fileOffset"), method.get("bodySize"), str(method.get("bodySha256") or "").upper()
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0: reject("method_byte_range", {"offset": "int", "size": ">0"}, method); continue
            body = image[offset:offset + size]; actual = hashlib.sha256(body).hexdigest().upper()
            if len(body) != size or actual != expected: reject("method_body_sha256", {"shape": key, "sha256": expected}, {"size": len(body), "sha256": actual})
        out[key] = getter
    if set(out) != set(_KINDS): reject("complete_shape_set", sorted(_KINDS), sorted(out))
    if failures: out = {}
    return out, {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed", "nativeMappingId": NATIVE_MAPPING_ID, "validationFailures": failures}

__all__ = ["load_entityptr_getter_contract", "NATIVE_MAPPING_ID"]
