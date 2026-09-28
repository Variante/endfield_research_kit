"""Selected TagValidator query child inside Buff SelectorData lists."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffSelectorValidatorTagQuery"
SCHEMA = "endfield.buff-selector-validator-tag-query-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_validator_tag_query_native.json"
TAG = 11
TYPE_NAME = "Beyond.Gameplay.Core.Selector+TagValidator+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_TagValidator_DataForMemoryPack"
QUERY_TYPE = "Beyond.Gameplay.Core.GameplayTagQuery"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-selector-validator-tag-query-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if (contract.get("switchContract") != "skill_selector_validator_in_screen_native.json"
            or contract.get("catalogContract") != "levelscript_union_tags.json"
            or contract.get("queryReaderContract") != "buff_14e_native.json"
            or contract.get("queryProfileContract") != "buff_b4_native.json"
            or contract.get("headerHelperContract") != "buff_selector_validator_zero_native.json"
            or contract.get("serializedMemberCount") != 1
            or contract.get("dispatcher", {}).get("unionTag") != TAG
            or contract["dispatcher"].get("wrapperName") != WRAPPER_NAME
            or len(contract.get("methods", ())) != 3
            or [row[2] for row in contract["methods"]]
            != ["Deserialize", "Deserialize", "set___query__"]
            or contract.get("setterMethods")
            != [[contract["methods"][2][0], "set___query__", QUERY_TYPE]]
            or len(contract.get("codeWindows", ())) != 3):
        raise ValueError(f"{LABEL}.contract:shape")
    order = contract.get("readOrder", {})
    if set(order) != {"headerCall", "memberCountCompare", "queryContext",
                      "queryBridgeCall", "directQueryStore", "setterQueryStore"}:
        raise ValueError(f"{LABEL}.contract:read-order-roles")
    positions = [order[name][0] if name != "queryContext" else order[name]["instructionRva"]
                 for name in ("headerCall", "memberCountCompare", "queryContext",
                              "queryBridgeCall", "directQueryStore")]
    reader = contract["codeWindows"][1]
    if not (reader["startRva"] <= positions[0] < positions[1] < positions[2]
            < positions[3] < positions[4] < reader["endRva"]):
        raise ValueError(f"{LABEL}.contract:read-order")
    setter_window = contract["codeWindows"][2]
    if (bytes.fromhex(order["memberCountCompare"][1]) != b"\x40\x80\xff\x01"
            or bytes.fromhex(order["directQueryStore"][1]) != b"\x0f\x11\x40\x10"
            or order["directQueryStore"][1] != order["setterQueryStore"][1]
            or not setter_window["startRva"] <= order["setterQueryStore"][0] < setter_window["endRva"]):
        raise ValueError(f"{LABEL}.contract:count-or-store-shape")
    return contract


def _dependencies(contract: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    base, _digest = read_reviewed_contract(
        CONTRACTS_DIR / contract["switchContract"],
        schema="endfield.skill-selector-validator-in-screen-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    query = json.loads((CONTRACTS_DIR / contract["queryReaderContract"]).read_bytes())
    profile = json.loads((CONTRACTS_DIR / contract["queryProfileContract"]).read_bytes())
    header = json.loads((CONTRACTS_DIR / contract["headerHelperContract"]).read_bytes())
    if (query.get("schemaVersion") != 1
            or profile.get("schemaVersion") != 1
            or header.get("schema") != "endfield.buff-selector-validator-zero-native-contract.v1"
            or tuple(profile.get("anonymousReadOrder", {}).get("query-profile", ()))
            != ("scalar32", "counted-scalar32")
            or tuple(query.get("anonymousReadOrder", {}).get("queryReader", ()))
            != ("header2", "scalar32", "nullable count", "count times four-byte array")):
        raise ValueError(f"{LABEL}.contract:query-dependencies")
    return base, catalog, query, profile, header


def validate_current_native_contract(*, selector_native: dict[str, Any]) -> dict[str, Any]:
    """Reprove tag 11's typed query bridge and direct destination store."""
    if selector_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:selector-not-validated")
    contract = _contract()
    base, catalog, query, profile, header = _dependencies(contract)
    expected = contract["nativeInputs"]
    if (expected != base["nativeInputs"] or expected != header["nativeInputs"]
            or expected != selector_native["nativeInputs"]):
        raise ValueError(f"{LABEL}.native:selected-inputs")
    validator_rows = catalog.get("families", {}).get("SelectorValidator", ())
    switch = catalog.get("switches", {}).get("SelectorValidator", {})
    if (catalog.get("schema") != "endfield.levelscript-union-tags.v1"
            or catalog.get("nativeInputs", {}).get("gameAssemblySha256") != expected["GameAssembly.dll"]
            or catalog.get("nativeInputs", {}).get("metadataSha256") != expected["global-metadata.dat"]
            or len(validator_rows) != base["dispatcher"]["switchEntryCount"]
            or validator_rows[TAG].get("tag") != TAG
            or validator_rows[TAG].get("memberCount") != 1
            or validator_rows[TAG].get("wrapperName") != WRAPPER_NAME
            or validator_rows[TAG].get("wrappedType") != TYPE_NAME
            or switch.get("base") != "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack"):
        raise ValueError(f"{LABEL}.native:catalog-route")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if (int(switch["tableVa"], 16)
            != image.pe.image_base + base["dispatcher"]["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:switch-table")
    dispatcher = {**base["dispatcher"], **contract["dispatcher"]}
    route = image.validate_dispatcher(dispatcher, label=LABEL)
    branch = image.window_bytes(contract["dispatcher"]["routeWindow"])
    type_load = branch.find(b"\x48\x8b\x15")
    if type_load < 0 or not branch.startswith(b"\x48\x8b\x0f\x48\x85\xc9"):
        raise ValueError(f"{LABEL}.native:route-type-load")
    cell = (image.pe.image_base + contract["dispatcher"]["switchTargetRva"]
            + type_load + 7 + struct.unpack_from("<i", branch, type_load + 3)[0])
    if cell != route["usageCell"]:
        raise ValueError(f"{LABEL}.native:route-type-cell")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-plan")
    order = contract["readOrder"]
    image.check_instruction_windows(
        [order["headerCall"], order["memberCountCompare"], order["queryBridgeCall"],
         order["directQueryStore"], order["setterQueryStore"]], label=LABEL,
    )
    for role in ("headerCall", "queryBridgeCall"):
        rva, raw_hex, target = order[role]
        raw = bytes.fromhex(raw_hex)
        if (len(raw) != 5 or raw[0] != 0xE8
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target):
            raise ValueError(f"{LABEL}.native:{role}-target")
    if order["headerCall"][2] != header["sharedHeaderWindow"]["startRva"]:
        raise ValueError(f"{LABEL}.native:header-helper-target")
    image.check_windows([header["sharedHeaderWindow"]], label=LABEL)
    bridge = [window for window in query["codeWindows"]
              if window["startRva"] == order["queryBridgeCall"][2]]
    reader = [window for window in query["codeWindows"]
              if window["startRva"] == query["methodGroups"][0]["methods"][0][3]]
    array = [window for window in query["codeWindows"]
             if "query array helper" in window["boundary"]]
    if len(bridge) != 1 or len(reader) != 1 or len(array) != 1:
        raise ValueError(f"{LABEL}.native:query-reader-windows")
    image.check_windows([*bridge, *reader, *array], label=LABEL)
    image.validate_method_row(query["methodGroups"][0]["methods"][0], label=LABEL)
    context = order["queryContext"]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(gate.gameassembly), offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:query-method-spec-index")
    raw_spec = image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + spec_index * 12, 12,
    )
    if list(struct.unpack("<iii", raw_spec)) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:query-method-spec")
    arguments = image.instantiations.resolve(context["methodSpec"][2]).arguments
    if (len(arguments) != 1
            or arguments[0].raw_type_record_hex.upper() != context["argumentRawHex"].upper()
            or image.type_name(context["typeDefinition"]) != context["typeName"]):
        raise ValueError(f"{LABEL}.native:query-type")
    query_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["queryProfileContract"],
    )
    if tuple(query_audit["anonymousReadOrder"].get("query-profile", ())) != (
        "scalar32", "counted-scalar32",
    ):
        raise ValueError(f"{LABEL}.native:query-profile")
    registry = selector_native["_registry"]
    selector_plan = registry.plans[selector_native["selectorDefinition"]]
    validators = [row for row in selector_plan if row.name == "validatorData" and row.kind == "list"]
    definition = contract["dispatcher"]["wrapperTypeDefinition"]
    plan = registry.plans.get(definition)
    if (len(validators) != 1 or validators[0].element is None
            or validators[0].element.kind != "union"
            or registry.union_tag_maps.get(validators[0].element.ref, {}).get(TAG) != definition
            or not isinstance(plan, tuple) or len(plan) != 1
            or plan[0].name != "query" or plan[0].kind != "object"
            or registry.wrapped_names.get(plan[0].ref) != QUERY_TYPE
            or registry.wrapped_names.get(definition) != TYPE_NAME):
        raise ValueError(f"{LABEL}.native:parent-validator-plan")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": TAG, "wrappedType": TYPE_NAME,
            "directMemberName": "query", "directMemberType": QUERY_TYPE,
            "queryProfileReadOrder": query_audit["anonymousReadOrder"]["query-profile"],
            "methodIndices": methods, "evidenceBoundary": contract["evidenceBoundary"]}


def decode_tag_query_validator_list(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse a fixed one-entry tag-validator list and bounded query child."""
    if native_validation.get("status") != "validated" or native_validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}:native-not-validated")
    actual_sha = hashlib.sha256(data).hexdigest().upper()
    if actual_sha != logical_sha256.upper():
        raise ValueError(f"{LABEL}:logical-source-hash")
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:source-range")
    reader = Reader(data, source, end)
    reader.pos = start
    count = reader.count(1)
    if count != 1:
        raise ValueError(f"{LABEL}:unsupported-list-count={count}")
    element_start = reader.pos
    if reader.peek() != TAG:
        raise ValueError(f"{LABEL}:unsupported-tag")
    reader.take(1, "validator-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-validator-wrapper")
        query = None
        status = "exact-null-wrapper"
    else:
        reader.header(1)
        query_start = reader.pos
        query_null = reader.peek() == 0xFF
        reader.query_profile()
        query = {"fieldName": "query", "declaredType": QUERY_TYPE,
                 "start": query_start, "end": reader.pos,
                 "status": "exact-null" if query_null else "framed-query-profile",
                 "nestedBodyStructural": True}
        status = "named-query-member-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:validator-list-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": "named-tag-validator-list-exact-span",
            "source": source, "logicalSha256": actual_sha,
            "start": start, "end": end, "count": count,
            "selectedElement": {"start": element_start, "end": reader.pos,
                                "unionTag": TAG, "wrappedType": TYPE_NAME,
                                "status": status, "namedMember": query},
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": False,
            "runtimePredicateKnown": False, "wholeBuffDataExact": False}
