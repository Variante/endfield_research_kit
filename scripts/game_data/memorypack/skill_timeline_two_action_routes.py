"""Selected SkillData readers for CheckAttackRangeType and DisableMoveCollider.

The six stored members have independent selected native routes.  The raw
enum words and nested TargetSettings framing do not establish runtime attack
range or collider behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineTwoActionRoutes"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_two_action_routes_native.json"
READ_LAYOUTS = {
    0x0054: ("bool-byte", "enum32", "scalar32", "scalar32", "enum32", "target-profile"),
    0x009D: ("bool-byte", "enum32", "scalar32", "scalar32", "bool-byte", "enum32"),
}
FIELD_NAMES = {
    0x0054: ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
             "attackRangeType", "checkTarget"),
    0x009D: ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
             "includeChildren", "mountPoint"),
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-two-action-routes-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    routes = contract.get("routes")
    if (
        not isinstance(routes, list)
        or {route.get("tag") for route in routes if isinstance(route, dict)}
        != {f"0x{tag:04X}" for tag in READ_LAYOUTS}
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("primitiveReadContract")
        != "skill_timeline_check_hit_collider_options_native.json"
        or contract.get("targetProfileContract") != "buff_ec_native.json"
    ):
        raise ValueError(f"{LABEL}.contract:routes")
    for route in routes:
        tag = int(route["tag"], 16)
        reads = route.get("orderedSourceReads")
        setters = route.get("setterMethods")
        setter_calls = route.get("setterCallsites")
        if (
            route.get("dispatcher", {}).get("unionTag") != tag
            or route.get("serializedMemberCount") != 6
            or not isinstance(reads, list)
            or [row.get("memberIndex") for row in reads] != list(range(6))
            or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES[tag]
            or tuple(row.get("readKind") for row in reads) != READ_LAYOUTS[tag]
            or not isinstance(setters, list) or len(setters) != 2
            or not isinstance(setter_calls, list)
            or [row.get("memberIndex") for row in setter_calls] != [4, 5]
            or [row.get("methodIndex") for row in setter_calls]
            != [row[0] for row in setters]
            or route.get("memberCountInstruction", {}).get("hex") != "807C243806"
            or (tag == 0x0054 and route.get("targetContext", {}).get("memberIndex") != 5)
            or (tag == 0x009D and route.get("targetContext") is not None)
        ):
            raise ValueError(f"{LABEL}.contract:source-shape:{tag:#x}")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = _contract()
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    target = json.loads((CONTRACTS_DIR / contract["targetProfileContract"]).read_bytes())
    actions = catalog.get("families", {}).get("AbilityActionData")
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(actions, list)
        or switch.get("entryCount") != len(actions)
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
        or primitive.get("schema")
        != "endfield.skill-timeline-check-hit-collider-options-native-contract.v1"
        or primitive.get("status") != "exact-current-build"
        or target.get("schemaVersion") != 1
        or len(target.get("anonymousReadOrder", {}).get("member13", ())) != 13
        or target["anonymousReadOrder"]["member13"][0] != "member8"
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
        or expected != primitive["nativeInputs"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-inputs")
    primitive_reads = primitive["orderedSourceReads"]
    for route in contract["routes"]:
        tag = int(route["tag"], 16)
        action = actions[tag]
        dispatch = route["dispatcher"]
        reads = route["orderedSourceReads"]
        if (
            action.get("tag") != tag
            or action.get("wrappedType") != route["typeName"]
            or action.get("wrapperName") != dispatch["wrapperName"]
            or action.get("memberCount") != route["serializedMemberCount"]
            or dispatch["switchTableRva"] != primitive["dispatcher"]["switchTableRva"]
            or [row["sourceTargetRva"] for row in reads[:4]]
            != [row["sourceTargetRva"] for row in primitive_reads[:4]]
        ):
            raise ValueError(f"{LABEL}.contract:route-dependency:{tag:#x}")
        for index in (4, 5):
            kind = READ_LAYOUTS[tag][index]
            if kind == "target-profile":
                if (
                    route["targetContext"]["typeName"]
                    != route["setterMethods"][index - 4][2]
                ):
                    raise ValueError(f"{LABEL}.contract:target-type:{tag:#x}")
            else:
                primitive_index = 0 if kind == "bool-byte" else 4
                if reads[index]["sourceTargetRva"] != primitive_reads[primitive_index]["sourceTargetRva"]:
                    raise ValueError(f"{LABEL}.contract:primitive-width:{tag:#x}:{index}")
    return catalog, primitive, target


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove selected routes, source call order, widths and nested type."""
    contract = _contract()
    _catalog, primitive, _target = _dependencies()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if (
        int(_catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + primitive["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(primitive["dispatcher"], label=LABEL)
    image.check_windows(primitive["codeWindows"], label=LABEL)
    target_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["targetProfileContract"],
    )
    if len(target_audit["anonymousReadOrder"]["member13"]) != 13:
        raise ValueError(f"{LABEL}.native:target-profile")
    summaries = []
    for route in contract["routes"]:
        tag = int(route["tag"], 16)
        image.validate_dispatcher(route["dispatcher"], label=LABEL)
        methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
        image.check_windows(route["codeWindows"], label=LABEL)
        count_instruction = route["memberCountInstruction"]
        image.check_instruction_windows(
            [[count_instruction["rva"], count_instruction["hex"]]], label=LABEL
        )
        owner = image.metadata.types[route["dispatcher"]["wrapperTypeDefinition"]]
        if image.setter_methods(owner, parameter="typeName", label=LABEL) != route["setterMethods"]:
            raise ValueError(f"{LABEL}.native:setter-order:{tag:#x}")
        start = route["codeWindows"][1]["startRva"]
        end = route["codeWindows"][1]["endRva"]
        previous = -1
        for read in route["orderedSourceReads"]:
            rva = read["sourceCallsiteRva"]
            if not start <= rva < end or rva <= previous:
                raise ValueError(f"{LABEL}.native:source-order:{tag:#x}")
            previous = rva
            raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
            if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
                raise ValueError(f"{LABEL}.native:source-call:{tag:#x}:{rva:#x}")
            if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
                raise ValueError(f"{LABEL}.native:source-target:{tag:#x}:{rva:#x}")
        for setter in route["setterCallsites"]:
            rva = setter["callsiteRva"]
            method = image.metadata.methods[setter["methodIndex"]]
            raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
            if (
                raw[0] != 0xE8
                or raw.hex().upper() != setter["callHex"]
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != setter["targetRva"]
                or image.method_pointer_va(method) != image.pe.image_base + setter["targetRva"]
            ):
                raise ValueError(f"{LABEL}.native:setter-call:{tag:#x}:{rva:#x}")
        if context := route.get("targetContext"):
            cell, usage = image.nested_usage_cell(context, label=LABEL)
            index = method_spec_usage_index(
                usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
            )
            if index != context["methodSpecIndex"]:
                raise ValueError(f"{LABEL}.native:target-method-spec-index")
            address = int(image.registration["methodSpecs"], 16) + index * 12
            spec = method_spec_record(
                image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                image.registration["genericInstsCount"], source=LABEL, offset=address,
            )
            instance = image.instantiations.resolve(spec[2])
            if (
                list(spec) != context["methodSpec"]
                or len(instance.arguments) != 1
                or instance.arguments[0].raw_type_record_hex.upper() != context["argumentRawHex"]
                or struct.unpack_from("<Q", bytes.fromhex(context["argumentRawHex"]))[0]
                != context["typeDefinition"]
                or image.type_name(context["typeDefinition"]) != context["typeName"]
            ):
                raise ValueError(f"{LABEL}.native:target-context")
        summaries.append({"tag": route["tag"], "methodIndices": methods, "sourceReadCount": 6})
    return {"status": "validated", "nativeInputs": expected, "routes": summaries}


def decode_two_action_route(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one selected action with bounded nullable TargetSettings."""
    del depth
    _contract()
    _dependencies()
    if tag not in READ_LAYOUTS or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(6)
    for field, kind in zip(FIELD_NAMES[tag], READ_LAYOUTS[tag]):
        if kind == "target-profile":
            reader.target_profile()
        elif kind == "bool-byte":
            reader.take(1, f"{field}.byte")
        else:
            reader.take(4, f"{field}.raw4")
