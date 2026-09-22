"""Validate the reviewed EntityPtr current-script slot resolution, per build.

The reviewed reading: an ``EntityPtr`` that names a slot resolves through the
current LevelScript (``GetSlotParentScriptId`` reads ``ActionContext.current``
then ``LevelScriptRuntime.scriptId``), and ``EntityManager`` keeps the slot /
logic-id pair in two dictionaries that ``OnScriptEntityDataAdd`` and
``OnScriptEntityDataRemove`` maintain and ``TryGetScriptEntityLogicIdBySlotId``
reads. That reading is authored as names: which callees each method reaches in
order, and which dictionary field each dictionary call loads.

``--regenerate`` re-proves every claim on the installed build -- methods by
name through ``il2cpp.method_resolver``, callees through ``il2cpp.call_graph``,
fields through the metadata registration's runtime offsets -- and records the
body extents and hashes as data. A claim that no longer holds refuses the
write. The loader then checks only the installed build and the recorded
bodies.

Run as: python -m scripts.game_data.entityptr_script_slot_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "entityPtrScriptSlotNativeContract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "entityptr_script_slot.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "entityptr-current-script-slot.v2"
#: How far before a dictionary call its field load may sit.
FIELD_LOAD_WINDOW = 0x40


@lru_cache(maxsize=1)
def load_entityptr_script_slot_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrScriptSlotNativeContract",
                         "gate": gate, "expected": expected, "actual": actual})

    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "nativeMappingId": NATIVE_MAPPING_ID,
                    "validationFailures": failures}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    if not failures:
        try:
            image = Path(native.gameassembly).read_bytes()
        except OSError as error:
            image = b""
            reject("read_gameassembly", True, str(error)[:400])
        for method in contract.get("methods") or []:
            offset, size = method.get("fileOffset"), method.get("bodySize")
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
                reject("method_byte_range", {"offset": "int", "size": ">0"}, method)
                continue
            digest = hashlib.sha256(image[offset:offset + size]).hexdigest().upper()
            if digest != str(method.get("bodySha256") or "").upper():
                reject("method_body_sha256", {"methodId": method.get("id"), "sha256": method.get("bodySha256")},
                       {"sha256": digest})
    if not (contract.get("callClaims") and contract.get("fieldClaims")):
        reject("reviewed_claims", "nonempty callClaims and fieldClaims", None)
    audit = {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
             "nativeMappingId": NATIVE_MAPPING_ID, "validationFailures": failures}
    return (contract if not failures else {}), audit


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-prove every authored claim and re-record the bodies they live in."""
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.call_graph import CallGraph, first_missing_in_order
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import NativeImage

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="entityptrScriptSlot")
    graph = CallGraph(image)
    resolver, _receipt = open_resolver()
    metadata = image.metadata
    type_index = {metadata.type_full_name(t): i for i, t in enumerate(metadata.types)}
    refused: list[str] = []
    methods, calls_by_id = [], {}
    for method in contract.get("methods") or []:
        resolved = resolver.resolve(MethodSpec(type_name=method["type"], method_name=method["name"]))
        matches = resolved.get("matches") or []
        if resolved.get("status") != "exact" or len(matches) != 1:
            refused.append(f"{method['type']}.{method['name']}: {resolved.get('status')}")
            continue
        match = matches[0]
        va, size = int(match["methodPointerVa"], 16), match["bodyExtent"]
        calls_by_id[method["id"]] = (va, size, graph.direct_calls(va, size))
        methods.append({"id": method["id"], "type": method["type"], "name": method["name"],
                        "va": match["methodPointerVa"], "fileOffset": int(match["fileOffset"], 16),
                        "bodySize": size, "bodySha256": match["bodySha256"].upper()})
    for claim in contract.get("callClaims") or []:
        _va, _size, calls = calls_by_id.get(claim["methodId"], (0, 0, []))
        missing = first_missing_in_order(calls, claim["calls"])
        if missing:
            refused.append(f"{claim['methodId']}: no ordered call to {missing}")
    for claim in contract.get("fieldClaims") or []:
        va, _size, calls = calls_by_id.get(claim["methodId"], (0, 0, []))
        owner = type_index.get(claim["fieldType"])
        offsets = protocol.runtime_type_field_offsets(metadata, image.pe, image.registration, owner) \
            if owner is not None else {}
        field_offset = offsets.get(claim["field"])
        if field_offset is None:
            refused.append(f"{claim['fieldType']}.{claim['field']}: no such field now")
            continue
        matched = graph.field_loads_before(va, calls, claim["callee"], field_offset, FIELD_LOAD_WINDOW)
        if matched < claim.get("occurrences", 1):
            refused.append(f"{claim['methodId']}: {claim['callee']} on {claim['field']} "
                           f"found {matched}, expected {claim.get('occurrences', 1)}")
    regenerated = {
        **{key: value for key, value in contract.items() if key not in ("methods", "nativeInputs", "metadata")},
        "schema": SCHEMA, "status": "validated", "nativeMappingId": NATIVE_MAPPING_ID,
        "nativeInputs": {"gameAssemblySha256": native.gameassembly_sha256.upper(),
                         "metadataSha256": native.metadata_sha256.upper()},
        "methods": methods,
    }
    return regenerated, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _contract, audit = load_entityptr_script_slot_contract(args.contract)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    regenerated, refused = regenerate(json.loads(args.contract.read_bytes().decode("utf-8-sig")))
    print(json.dumps({"refused": refused, "methods": len(regenerated["methods"])}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["load_entityptr_script_slot_contract", "regenerate", "NATIVE_MAPPING_ID"]
