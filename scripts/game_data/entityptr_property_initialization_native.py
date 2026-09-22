"""Validate the reviewed LevelScript EntityPtr property initialization, per build.

The reviewed reading: ``LevelScriptRuntime.Init`` builds an empty
``ParamBlackboard``, installs it as the runtime's properties and loads the
authored ``LevelScriptBriefData`` values into it; ``Setup`` resets and reloads
that blackboard before it binds the action context. An EntityPtr property is
stored as ``ParamRealType.EntityPtr`` under ParamSource 200. So a brief
property is the value an action graph *starts* with -- runtime setters, server
sync and graph resets can replace it later, which is why the classification
stays non-final and never promotes a target.

That reading is authored as names: ordered callees per method, the enum
member's value, and the brief-data fields it reads. ``--regenerate`` re-proves
each claim on the installed build through ``il2cpp.method_resolver``,
``il2cpp.call_graph`` and the metadata, and records the method bodies as data;
a claim that no longer holds refuses the write.

Run as: python -m scripts.game_data.entityptr_property_initialization_native --regenerate [--write]
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

SCHEMA = "entityPtrPropertyInitializationNativeContract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "entityptr_property_initialization.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "entityptr-property-initialization.v2"
CLASSIFICATION = "validated_initial_entityptr_value_nonfinal"


@lru_cache(maxsize=1)
def load_entityptr_property_initialization_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrPropertyInitializationNativeContract",
                         "gate": gate, "expected": expected, "actual": actual})

    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        contract = {}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", CLASSIFICATION, contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    boundary = contract.get("lifecycleBoundary") or {}
    for key, expected in (("classification", CLASSIFICATION), ("mutableAfterBind", True),
                          ("diagnosticOnly", True), ("allowTargetPromotion", False)):
        if boundary.get(key) != expected:
            reject(f"lifecycle_boundary_{key}", expected, boundary.get(key))
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
    if not contract.get("callClaims"):
        reject("reviewed_claims", "nonempty callClaims", None)
    if failures:
        contract = {}
    return contract, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "classification": CLASSIFICATION,
        "nativeMappingId": NATIVE_MAPPING_ID,
        "allowTargetPromotion": False,
        "validationFailures": failures,
    }


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-prove every authored claim and re-record the bodies they live in."""
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.call_graph import CallGraph, first_missing_in_order
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import NativeImage

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="entityptrPropertyInitialization")
    graph = CallGraph(image)
    resolver, _receipt = open_resolver()
    metadata = image.metadata
    refused: list[str] = []
    methods, calls_by_id = [], {}
    for method in contract.get("methods") or []:
        resolved = resolver.resolve(MethodSpec(type_name=method["declaringType"], method_name=method["name"]))
        matches = resolved.get("matches") or []
        if resolved.get("status") != "exact" or len(matches) != 1:
            refused.append(f"{method['declaringType']}.{method['name']}: {resolved.get('status')}")
            continue
        match = matches[0]
        va, size = int(match["methodPointerVa"], 16), match["bodyExtent"]
        calls_by_id[method["id"]] = graph.direct_calls(va, size)
        methods.append({"id": method["id"], "declaringType": method["declaringType"], "name": method["name"],
                        "va": match["methodPointerVa"], "fileOffset": int(match["fileOffset"], 16),
                        "bodySize": size, "bodySha256": match["bodySha256"].upper()})
    for claim in contract.get("callClaims") or []:
        missing = first_missing_in_order(calls_by_id.get(claim["methodId"], []), claim["calls"])
        if missing:
            refused.append(f"{claim['methodId']}: no ordered call to {missing}")
    enum = contract.get("paramRealType") or {}
    members = {row["name"]: row["id"] for row in protocol.enum_members(
        metadata, protocol.field_defaults(metadata), enum.get("declaringType", ""))}
    if members.get(enum.get("fieldName")) != enum.get("value"):
        refused.append(f"{enum.get('declaringType')}.{enum.get('fieldName')} is "
                       f"{members.get(enum.get('fieldName'))}, not {enum.get('value')}")
    brief = contract.get("briefProperties") or {}
    brief_type = next((t for t in metadata.types if metadata.type_full_name(t) == brief.get("declaringType")), None)
    fields = {metadata.string(f.name_index) for f in metadata.fields_for(brief_type)} if brief_type else set()
    for name in brief.get("fields") or []:
        if name not in fields:
            refused.append(f"{brief.get('declaringType')}.{name}: no such field now")
    regenerated = {
        **{key: value for key, value in contract.items() if key not in ("methods", "nativeInputs", "metadata")},
        "schema": SCHEMA, "status": CLASSIFICATION, "nativeMappingId": NATIVE_MAPPING_ID,
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
        _contract, audit = load_entityptr_property_initialization_contract(args.contract)
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


__all__ = ["load_entityptr_property_initialization_contract", "regenerate", "NATIVE_MAPPING_ID"]
