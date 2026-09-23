"""Validate and decode the reviewed ``SpawnerPtrGetter`` for the selected build.

The getter's meaning is authored and reviewed: ``GetResult`` returns
``ParamExtensions.GetValue<SpawnerPtr>(this._value)``, so a constant ``_value``
is the getter's value. Everything a client update moves is data in the
contract -- the union tag and member count from the PureGetter formatter
switch, the member ordinal, and the ``GetResult`` body location and hash --
re-derived by ``--regenerate``, which also re-checks that ``Param<SpawnerPtr>``
still serializes as the four members the decoder reads. A body that changed
since its review refuses to regenerate.

Run as: python -m scripts.game_data.spawnerptr_getter_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "spawnerPtrGetterNativeContract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "spawnerptr_getter.json"
#: Stable identifier cited in evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "spawnerptr-getter.v2"
GETTER_NAME = "Beyond.Gameplay.Actions.SpawnerPtrGetter"
PARAM_WRAPPER_TYPE = "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.SpawnerPtr>"
#: The four members ``decode_spawnerptr_getter_member`` reads, in wire order.
PARAM_LAYOUT = [("constValue", "object"), ("idRef", "scalar32"), ("paramSource", "scalar32"), ("path", "string")]
#: Codec facts of the shared record scanner, not of the build.
RECORD_BOUNDARY = {"payloadStartAdjustment": -4, "paramMarker": 4, "constantByteLength": 8, "tailByteLength": 12}


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
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    getter = contract.get("getter") or {}
    fields = [(field.get("name"), field.get("ordinal")) for field in getter.get("fields") or []]
    shape = (getter.get("getterName"), getter.get("resolutionKind"), fields, getter.get("recordBoundary"))
    expected_shape = (GETTER_NAME, "constant_param_alias", [("_value", 7)], RECORD_BOUNDARY)
    if shape != expected_shape:
        reject("getter_shape", expected_shape, shape)
    if not all(isinstance(getter.get(key), int) for key in ("unionTag", "serializedMemberCount")):
        reject("union_shape", "integer unionTag and serializedMemberCount",
               [getter.get("unionTag"), getter.get("serializedMemberCount")])
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    body = getter.get("getResult") or {}
    review = getter.get("review") or {}
    if not body or str(review.get("bodySha256", "")).upper() != str(body.get("bodySha256", "")).upper():
        reject("reviewed_body", "review matches getResult",
               {"review": review.get("bodySha256"), "getResult": body.get("bodySha256")})
    gameassembly = getattr(native, "gameassembly", None)
    if gameassembly and not failures:
        try:
            image = Path(gameassembly).read_bytes()
        except OSError as error:
            image = b""
            reject("read_gameassembly", True, str(error)[:400])
        offset, size = body.get("fileOffset"), body.get("bodySize")
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
            reject("getResult_byte_range", {"offset": "int", "size": ">0"}, body)
        elif image:
            region = image[offset:offset + size]
            digest = hashlib.sha256(region).hexdigest().upper()
            if len(region) != size or digest != str(body.get("bodySha256") or "").upper():
                reject("getResult_body_sha256", body.get("bodySha256"), {"size": len(region), "sha256": digest})
    if failures:
        getter = {}
    return getter, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "validationFailures": failures,
    }


def spawnerptr_getter_shape() -> tuple[int, int] | None:
    """The validated ``(unionTag, serializedMemberCount)``, or None."""
    getter, audit = load_spawnerptr_getter_contract()
    if audit.get("status") != NATIVE_EVIDENCE_VALIDATED or not getter:
        return None
    return getter["unionTag"], getter["serializedMemberCount"]


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-derive the per-build fields and the Param<SpawnerPtr> wire layout."""
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.pure_getter_rows import derive_getter_rows

    authored = contract.get("getter") or {}
    derived = derive_getter_rows([GETTER_NAME], with_get_result=[GETTER_NAME])
    refused = list(derived["refused"])
    native = check_installed_native_inputs()
    wrappers = derive_from_image(NativeImage(native.gameassembly, native.metadata, label="spawnerPtrGetter"))
    param = next((w for w in wrappers.values() if w.wrapped_type == PARAM_WRAPPER_TYPE), None)
    layout = [(member.name, member.kind) for member in param.members] if param else None
    if layout != PARAM_LAYOUT:
        refused.append(f"{PARAM_WRAPPER_TYPE}: wire layout {layout} differs from the decoder's {PARAM_LAYOUT}")
    fresh = derived["rows"].get(GETTER_NAME)
    if fresh is None:
        return contract, refused
    getter = {"getterName": GETTER_NAME, "resolutionKind": "constant_param_alias", **fresh,
              "recordBoundary": RECORD_BOUNDARY, "paramLayout": [list(item) for item in PARAM_LAYOUT]}
    if authored.get("review"):
        getter["review"] = authored["review"]
    if getter.get("getResult", {}).get("bodySha256") != str(getter.get("review", {}).get("bodySha256", "")).upper():
        refused.append(f"{GETTER_NAME}: GetResult body changed since review; re-review before writing")
    regenerated = {
        **{key: value for key, value in contract.items() if key not in ("getter", "nativeInputs", "union", "metadata")},
        "schema": SCHEMA, "status": "validated", "nativeMappingId": NATIVE_MAPPING_ID,
        "nativeInputs": derived["nativeInputs"], "union": derived["union"], "getter": getter,
    }
    return regenerated, refused


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true", help="write the regenerated contract")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _getter, audit = load_spawnerptr_getter_contract(args.contract)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract = json.loads(args.contract.read_bytes().decode("utf-8-sig"))
    regenerated, refused = regenerate(contract)
    encoded = (json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    print(json.dumps({"refused": refused, "sha256": hashlib.sha256(encoded).hexdigest().upper()}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["decode_spawnerptr_getter_member", "load_spawnerptr_getter_contract",
           "spawnerptr_getter_shape", "regenerate", "NATIVE_MAPPING_ID"]
