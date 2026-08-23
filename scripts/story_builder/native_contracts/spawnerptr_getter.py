"""Validate and decode the pinned ``SpawnerPtrGetter`` formatter shape."""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

if __package__ == "scripts.story_builder.native_contracts":
    from ...common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
elif __package__ == "story_builder.native_contracts":
    from common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
else:  # pragma: no cover
    raise ImportError(f"unsupported package identity: {__package__!r}")

SCHEMA = "spawnerPtrGetterNativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("spawnerptr_getter.json")
GAMEASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
NATIVE_MAPPING_ID = "gameassembly-2026-08-23-spawnerptr-getter"
CONTRACT_SHA256 = "C81EDDFDBEFE92FB192546EE7A058F677780E83B313872DA2F2FBE671E5B0DA0"


@lru_cache(maxsize=1)
def load_spawnerptr_getter_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "spawnerPtrGetterNativeContract", "gate": gate,
                         "expected": expected, "actual": actual})

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
    getter = contract.get("getter") or {}
    boundary = getter.get("recordBoundary") or {}
    expected_shape = (420, 8, "_value", 7, -4, 4, 8, 12)
    actual_shape = (
        getter.get("unionTag"), getter.get("serializedMemberCount"),
        getter.get("fieldName"), getter.get("fieldOrdinal"),
        boundary.get("payloadStartAdjustment"), boundary.get("paramMarker"),
        boundary.get("constantByteLength"), boundary.get("tailByteLength"),
    )
    if actual_shape != expected_shape:
        reject("formatter_and_boundary_shape", expected_shape, actual_shape)
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
    for name in ("setter", "deserialize", "getResult"):
        method = getter.get(name) or {}
        offset, size = method.get("fileOffset"), method.get("bodySize")
        expected_hash = str(method.get("bodySha256") or "").upper()
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
            reject(f"{name}_byte_range", {"offset": "int", "size": ">0"}, method)
            continue
        body = image[offset:offset + size]
        actual_hash = hashlib.sha256(body).hexdigest().upper()
        if len(body) != size or actual_hash != expected_hash:
            reject(f"{name}_body_sha256", expected_hash,
                   {"size": len(body), "sha256": actual_hash})
    if failures:
        getter = {}
    return getter, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "validationFailures": failures,
    }


def decode_spawnerptr_getter_member(
    data: bytes,
    *,
    payload_start: int,
    record_end: int,
) -> dict[str, Any]:
    """Decode exactly one Param<SpawnerPtr>, including the scanner overlap."""
    getter, audit = load_spawnerptr_getter_contract()
    if audit.get("status") != NATIVE_EVIDENCE_VALIDATED or not getter:
        return {}
    start = payload_start - 4
    if start < 0 or record_end <= start or record_end > len(data):
        return {}
    payload = data[start:record_end]
    if len(payload) < 21 or payload[0] != 4:
        return {}
    spawner_id = struct.unpack_from("<Q", payload, 1)[0]
    id_ref, source, path_size = struct.unpack_from("<iii", payload, 9)
    cursor = 21
    if id_ref < -1 or source < -1:
        return {}
    if path_size == -1:
        path = None
    elif 0 < path_size <= 256 and cursor + path_size == len(payload):
        try:
            path = payload[cursor:cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += path_size
    else:
        return {}
    if cursor != len(payload):
        return {}
    binding_kind = (
        "constant" if spawner_id > 0 and id_ref == -1 and source == 0 and path is None
        else "source200_property" if spawner_id == 0 and id_ref == -1 and source == 200 and path
        else "runtime_unresolved"
    )
    return {
        "spawnerId": spawner_id,
        "idRef": id_ref,
        "paramSource": source,
        "path": path,
        "bindingKind": binding_kind,
        "memberStart": start,
        "memberEnd": record_end,
        "recordPayloadStartAdjustment": -4,
        "payloadShape": "spawnerptr-getter-param-exact-eof",
        "nativeMappingId": NATIVE_MAPPING_ID,
    }


__all__ = ["decode_spawnerptr_getter_member", "load_spawnerptr_getter_contract", "NATIVE_MAPPING_ID"]
