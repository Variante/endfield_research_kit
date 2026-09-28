"""Selected native source for reached finite LevelScript union routes.

The reviewed contract records complete generated reader fragments, selected
dispatch branches and ordered reads. It proves stored framing only; execution
and getter/entity behavior require separate runtime evidence.

Routes, each after its inherited fields (seven NodeBase fields for a
PureGetter, eight for an ActionBase):

* `BoolGetterOr` adds two `Param<bool>` operands.
* `EntityHide` adds an allow-missing `Param<bool>` and a `Param<EntityPtr>`.
* `DeadZoneDoRepatriate` adds a ninth member, `damageRatioPerFall` as
  `Param<float>`, with its `System.Single` generic context checked. Its
  reviewed layout row also carries a source-hash cursor record, and this
  validator checks that the row's fields and cursor evidence still agree
  with the selected route. The float is a stored setting, not evidence that
  repatriation ran or damage was applied.
* `OpenSnapshot` adds its camera rotation, focus and two boolean controls.

The same rows live in `codecs/levelscript/action_map_layouts.json`; a
focused replay that consumes one of these records advances a cursor only,
and the JsonData corpus EOF gate alone promotes an enclosing owner.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "levelscriptTwoRoutes"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_two_routes_native.json"
LAYOUT_PATH = Path(__file__).parent / "codecs" / "levelscript" / "action_map_layouts.json"
CODEC_FAMILIES = {"GetterBase": "PureGetter", "ActionBase": "ActionBase"}
PARAM_ELEMENT_TYPES = {
    "Param<bool>": "System.Boolean",
    "Param<EntityPtr>": "Beyond.Gameplay.Core.EntityPtr",
    "Param<float>": "System.Single",
    "Param<Vector2>": "UnityEngine.Vector2",
}


@lru_cache(maxsize=1)
def _reviewed() -> tuple[dict[str, Any], dict[str, Any]]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.levelscript-two-routes-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    layouts = json.loads(LAYOUT_PATH.read_bytes()).get("layouts", [])
    routes = contract.get("routes")
    if (
        contract.get("catalogContract") != "levelscript_union_tags.json"
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(routes, list) or not routes
        or len({(r.get("codecFamily"), r.get("tag")) for r in routes}) != len(routes)
    ):
        raise ValueError(f"{LABEL}.contract:route-set")
    for route in routes:
        key = route.get("codecFamily"), route.get("tag")
        family_name = CODEC_FAMILIES.get(key[0])
        family = catalog.get("families", {}).get(family_name)
        catalog_route = family[key[1]] if isinstance(family, list) and key[1] < len(family) else None
        fields = route.get("fields")
        reads = route.get("orderedSourceReads")
        windows = route.get("codeWindows")
        contexts = route.get("nestedContexts")
        setters = route.get("setterMethods")
        setter_calls = route.get("setterCallsites")
        matching_layouts = [row for row in layouts if
                            (row.get("family"), row.get("tag")) == key]
        layout = matching_layouts[0] if len(matching_layouts) == 1 else None
        cursor = layout.get("cursorEvidence") if layout else None
        if not isinstance(fields, list) or not all(
            isinstance(field, list) and len(field) == 2 and isinstance(field[0], str)
            and isinstance(field[1], str) for field in fields
        ):
            raise ValueError(f"{LABEL}.contract:field-list={key}")
        param_members = [index for index, (_name, kind) in enumerate(fields) if kind.startswith("Param<")]
        if any(fields[index][1] not in PARAM_ELEMENT_TYPES for index in param_members):
            raise ValueError(f"{LABEL}.contract:unsupported-param-kind={key}")
        if any(kind not in ("bool", "int32", "string", *PARAM_ELEMENT_TYPES) for _name, kind in fields):
            raise ValueError(f"{LABEL}.contract:unsupported-field-kind={key}")
        if (
            route.get("nativeFamily") != family_name
            or route.get("serializedMemberCount") != len(fields)
            or not 0 < len(fields) < 256
            or not isinstance(catalog_route, dict)
            or catalog_route.get("tag") != key[1]
            or catalog_route.get("wrappedType") != route.get("typeName")
            or catalog_route.get("wrapperName") != route.get("wrapperName")
            or catalog_route.get("memberCount") != len(fields)
            or not isinstance(route.get("memberCountInstruction", {}).get("hex"), str)
            or len(route["memberCountInstruction"]["hex"]) not in (8, 10)
            or bytes.fromhex(route["memberCountInstruction"]["hex"])[-1] != len(fields)
            or not isinstance(reads, list) or len(reads) != len(fields)
            or [r.get("memberIndex") for r in reads] != list(range(len(reads)))
            or [list((r.get("fieldName"), r.get("readKind"))) for r in reads] != fields
            or not isinstance(windows, list) or len(windows) < 2
            or not isinstance(route.get("methods"), list) or len(route["methods"]) != 2
            or [r[2] for r in route["methods"]] != ["Deserialize", "Deserialize"]
            or route["methods"][0][1] != route["wrapperName"]
            or not route["methods"][1][1].startswith(route["wrapperName"] + "+")
            or not isinstance(setters, list) or len(setters) != len(param_members)
            or [row[1] for row in setters]
            != [f"set____{fields[index][0]}__" for index in param_members]
            or not isinstance(setter_calls, list) or len(setter_calls) != len(param_members)
            or [r.get("memberIndex") for r in setter_calls]
            != param_members
            or not isinstance(contexts, list) or len(contexts) != len(param_members)
            or [r.get("memberIndex") for r in contexts]
            != param_members
            or [r.get("elementTypeName") for r in contexts]
            != [PARAM_ELEMENT_TYPES[fields[index][1]] for index in param_members]
            or layout is None
            or layout.get("wrapperName") != route.get("wrapperName")
            or layout.get("memberCount") != len(fields)
            or layout.get("fields") != fields
            or not isinstance(cursor, dict)
            or not isinstance(cursor.get("source"), str)
            or not isinstance(cursor.get("sourceSha256"), str)
            or len(cursor["sourceSha256"]) != 64
            or not isinstance(cursor.get("unionOffset"), int)
        ):
            raise ValueError(f"{LABEL}.contract:source-shape={key}")
    return contract, catalog


def reviewed_route(family: str, tag: int) -> dict[str, Any]:
    """Return one reviewed field plan; native validation remains a separate gate."""
    contract, _catalog = _reviewed()
    matches = [r for r in contract["routes"] if (r["codecFamily"], r["tag"]) == (family, tag)]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.contract:missing-route={family}:{tag:#x}")
    return matches[0]


def _validate_dispatch(image: Any, route: dict[str, Any], catalog: dict[str, Any]) -> None:
    dispatcher = route["dispatcher"]
    family = route["nativeFamily"]
    switch = catalog["switches"][family]
    table_rva = dispatcher["switchTableRva"]
    count = dispatcher["switchEntryCount"]
    if (
        int(switch["tableVa"], 16) != image.pe.image_base + table_rva
        or switch["entryCount"] != count
        or count != len(catalog["families"][family])
    ):
        raise ValueError(f"{LABEL}.native:switch-shape={family}")
    table = image.pe.bytes_at_va(image.pe.image_base + table_rva, count * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["switchTableSha256"]:
        raise ValueError(f"{LABEL}.native:switch-hash={family}")
    target_rva = struct.unpack_from("<I", table, route["tag"] * 4)[0]
    entry = image.pe.bytes_at_va(image.pe.image_base + target_rva, 5)
    if (
        target_rva != dispatcher["switchTargetRva"]
        or entry[0] != 0xE9
        or entry.hex().upper() != dispatcher["switchEntryHex"]
        or target_rva + 5 + struct.unpack_from("<i", entry, 1)[0] != dispatcher["branchRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-entry={family}:{route['tag']:#x}")
    branch = dispatcher["branchWindow"]
    if branch["startRva"] != dispatcher["branchRva"]:
        raise ValueError(f"{LABEL}.native:branch-start={family}")
    image.check_windows([branch], label=LABEL)
    load_rva = dispatcher["typeLoadRva"]
    if not branch["startRva"] <= load_rva < branch["endRva"] - 7:
        raise ValueError(f"{LABEL}.native:type-load-range={family}")
    load = image.pe.bytes_at_va(image.pe.image_base + load_rva, 7)
    if load[:3] != b"\x48\x8B\x15" or load.hex().upper() != dispatcher["typeLoadHex"]:
        raise ValueError(f"{LABEL}.native:type-load={family}")
    cell = image.pe.image_base + load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    if cell - image.pe.image_base != dispatcher["usageCellRva"] or usage.hex().upper() != dispatcher["usageRawHex"]:
        raise ValueError(f"{LABEL}.native:usage-cell={family}")
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
    )
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if (
        index != dispatcher["registeredTypeIndex"]
        or definition != dispatcher["wrapperTypeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-type={family}")


def _validate_context(image: Any, context: dict[str, Any], expected_type: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:child-method-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1 or list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:child-method-spec-record")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:child-param-type")
    carrier_ptr = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_ptr, 32)
    base_ptr = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_ptr, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"])
        != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:child-param-carrier")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:child-param-instantiation")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    if (
        element.hex().upper() != context["elementRawHex"]
        or element[10] != context["elementTypeKind"]
        or context["elementTypeName"] != expected_type
    ):
        raise ValueError(f"{LABEL}.native:child-param-element")
    primitive_kinds = {"System.Boolean": 2, "System.Int32": 8, "System.Single": 12}
    if expected_type in primitive_kinds:
        if (element[10] != primitive_kinds[expected_type]
                or context["elementTypeDefinition"] is not None):
            raise ValueError(f"{LABEL}.native:child-primitive={expected_type}")
    else:
        definition = struct.unpack_from("<Q", element)[0]
        if (
            element[10] != 0x11
            or definition != context["elementTypeDefinition"]
            or image.type_name(definition) != expected_type
        ):
            raise ValueError(f"{LABEL}.native:child-value-type")


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected routes and complete source read sequences."""
    contract, catalog = _reviewed()
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    extents = image.mapper.pdata_function_extents(image.pe)
    fragments = BodyIndex(image).chained_fragments
    results = []
    for route in contract["routes"]:
        _validate_dispatch(image, route, catalog)
        methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
        image.check_windows(route["codeWindows"], label=LABEL)
        image.check_instruction_windows([
            [route["memberCountInstruction"]["rva"], route["memberCountInstruction"]["hex"]]
        ], label=LABEL)
        source_ptr = image.method_pointer_va(image.metadata.methods[methods[0]])
        formatter_ptr = image.method_pointer_va(image.metadata.methods[methods[1]])
        source_windows = route["codeWindows"][:-1]
        formatter_window = route["codeWindows"][-1]
        if (
            source_windows[0]["startRva"] != source_ptr - image.pe.image_base
            or source_windows[0]["endRva"] != extents.get(source_ptr, 0) - image.pe.image_base
            or formatter_window["startRva"] != formatter_ptr - image.pe.image_base
            or formatter_window["endRva"] != extents.get(formatter_ptr, 0) - image.pe.image_base
            or [(r["startRva"], r["endRva"]) for r in source_windows[1:]]
            != [(s - image.pe.image_base, s + n - image.pe.image_base) for s, n in fragments.get(source_ptr, ())]
        ):
            raise ValueError(f"{LABEL}.native:method-extents={route['nativeFamily']}:{route['tag']:#x}")
        owner = image.metadata.types[route["dispatcher"]["wrapperTypeDefinition"]]
        if image.setter_methods(owner, parameter="typeName", label=LABEL) != route["setterMethods"]:
            raise ValueError(f"{LABEL}.native:setter-order={route['nativeFamily']}:{route['tag']:#x}")
        ranges = [(r["startRva"], r["endRva"]) for r in source_windows]
        header_rva = route["memberCountInstruction"]["rva"]
        if not any(start <= header_rva < end for start, end in ranges):
            raise ValueError(f"{LABEL}.native:header-range")
        previous = header_rva
        for read in route["orderedSourceReads"]:
            rva = read["sourceCallsiteRva"]
            if rva <= previous or not any(start <= rva < end for start, end in ranges):
                raise ValueError(f"{LABEL}.native:source-order={rva:#x}")
            previous = rva
            raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
            if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
                raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
            if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != read["sourceTargetRva"]:
                raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
        read_targets = route["orderedSourceReads"]
        for kind in ("bool", "int32", "string"):
            targets = {r["sourceTargetRva"] for r in read_targets if r["readKind"] == kind}
            if len(targets) != 1:
                raise ValueError(f"{LABEL}.native:primitive-helper={kind}")
        param_targets = {r["sourceTargetRva"] for r in read_targets
                         if r["readKind"].startswith("Param<")}
        if len(param_targets) != 1:
            raise ValueError(f"{LABEL}.native:param-helper")
        for setter, call, context, expected_type in zip(
            route["setterMethods"], route["setterCallsites"],
            route["nestedContexts"],
            (PARAM_ELEMENT_TYPES[route["fields"][r["memberIndex"]][1]] for r in route["nestedContexts"]),
            strict=True,
        ):
            member = call["memberIndex"]
            source_rva = read_targets[member]["sourceCallsiteRva"]
            next_rva = read_targets[member + 1]["sourceCallsiteRva"] if member + 1 < len(read_targets) else max(end for _, end in ranges)
            call_rva = call["callsiteRva"]
            if (
                context["memberIndex"] != member
                or not read_targets[member - 1]["sourceCallsiteRva"] < context["instructionRva"] < source_rva < call_rva < next_rva
                or not any(start <= call_rva < end for start, end in ranges)
            ):
                raise ValueError(f"{LABEL}.native:child-order={member}")
            raw = image.pe.bytes_at_va(image.pe.image_base + call_rva, 5)
            target = call_rva + 5 + struct.unpack_from("<i", raw, 1)[0]
            if (
                raw[0] != 0xE8 or raw.hex().upper() != call["callHex"]
                or target != call["targetRva"]
                or image.method_pointer_va(image.metadata.methods[setter[0]])
                != image.pe.image_base + target
            ):
                raise ValueError(f"{LABEL}.native:setter-call={member}")
            _validate_context(image, context, expected_type)
        results.append({
            "family": route["codecFamily"], "tag": route["tag"],
            "sourceReadCount": len(read_targets),
            "sourceFragmentCount": len(fragments.get(source_ptr, ())),
        })
    return {"status": "validated", "nativeInputs": expected, "routes": results}
