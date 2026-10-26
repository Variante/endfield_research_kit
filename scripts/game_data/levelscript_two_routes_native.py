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
from scripts.game_data.il2cpp.protocol import canonical_type_name, RUNTIME_PRIMITIVE_TYPE_NAMES
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
    _check_shape(contract, catalog, layouts)
    return contract, catalog


def _check_shape(contract: dict[str, Any], catalog: dict[str, Any], layouts: list[dict[str, Any]]) -> None:
    """Reviewed route-plan shape; shared by the loader and the regenerator."""
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
                            (row.get("family"), row.get("wrapperName"))
                            == (key[0], route.get("wrapperName"))]
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
    if not branch["startRva"] <= load_rva <= branch["endRva"] - 7:
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


def validate_current_native_contract(
    contract: dict[str, Any] | None = None, catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Authenticate the selected routes and complete source read sequences."""
    if contract is None or catalog is None:
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


# --- Regeneration against the selected build -------------------------------

class RouteRefused(ValueError):
    """A reviewed route claim that cannot be re-proved on the selected build."""


def _sha256_upper(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _window(image: Any, start: int, end: int, boundary: str) -> dict[str, Any]:
    base = image.pe.image_base
    return {"startRva": start - base, "endRva": end - base,
            "sha256": _sha256_upper(image.pe.bytes_at_va(start, end - start)), "boundary": boundary}


def _deserialize_method(image: Any, type_name: str, *, nested_of: str | None = None) -> list[Any]:
    md = image.metadata
    rows = []
    for definition in range(len(md.types)):
        name = image.type_name(definition)
        if (name != type_name) if nested_of is None else not name.startswith(nested_of + "+"):
            continue
        owner = md.types[definition]
        for index in range(owner.method_start, owner.method_start + owner.method_count):
            if md.string(md.methods[index].name_index) == "Deserialize":
                rows.append([index, name, "Deserialize",
                             image.method_pointer_va(md.methods[index]) - image.pe.image_base])
    if len(rows) != 1:
        raise RouteRefused(f"deserialize-method={nested_of or type_name}:found={len(rows)}")
    return rows[0]


def _call_target(row: dict[str, Any]) -> int | None:
    text = row["text"]
    return int(text.split()[1], 16) if text.startswith("call 0x") else None


def check_reviewed_fields(wrapper: str, reviewed: list[list[str]], installed: list[list[str]]) -> None:
    """Refuse unless the installed member list equals the reviewed one.

    A non-append change names the first differing member; an append-only
    change is still refused, because new members need a reviewed kind and
    semantic claim before the contract may carry them.
    """
    if installed[:len(reviewed)] != reviewed:
        first = next((i for i, (a, b) in enumerate(zip(installed, reviewed)) if a != b),
                     min(len(installed), len(reviewed)))
        raise RouteRefused(
            f"field-order={wrapper}:member={first}"
            f":reviewed={reviewed[first] if first < len(reviewed) else None}"
            f":installed={installed[first] if first < len(installed) else None}")
    if installed != reviewed:
        raise RouteRefused(f"appended-fields={wrapper}:{installed[len(reviewed):]}:review-required")


def _regenerate_route(image: Any, route: dict[str, Any], catalog: dict[str, Any],
                      layouts: list[dict[str, Any]], switch: dict[str, Any]) -> dict[str, Any]:
    """Re-derive one route; reviewed identity and field order must still hold."""
    base = image.pe.image_base
    family, wrapper = route["nativeFamily"], route["wrapperName"]
    entries = [e for e in switch["entries"] if e.get("wrapperName") == wrapper]
    if len(entries) != 1:
        raise RouteRefused(f"switch-entry={wrapper}:found={len(entries)}")
    entry = entries[0]
    tag = entry["tag"]
    catalog_row = catalog["families"][family][tag]
    if (catalog_row.get("wrapperName"), catalog_row.get("wrappedType")) != (wrapper, route["typeName"]):
        raise RouteRefused(f"catalog-identity={family}:{tag}:{catalog_row.get('wrapperName')}")
    layout = [r for r in layouts if (r.get("family"), r.get("wrapperName")) == (route["codecFamily"], wrapper)]
    if len(layout) != 1:
        raise RouteRefused(f"layout-row={wrapper}:found={len(layout)}")
    fields = layout[0]["fields"]
    check_reviewed_fields(wrapper, route["fields"], fields)
    if catalog_row.get("memberCount") != len(fields):
        raise RouteRefused(f"member-count={wrapper}:catalog={catalog_row.get('memberCount')}:fields={len(fields)}")

    table_va = int(switch["tableVa"], 16)
    count = switch["entryCount"]
    target = int(entry["targetVa"], 16)
    body = int(entry["bodyVa"], 16)
    head = image.pe.bytes_at_va(target, 5)
    old = route["dispatcher"]
    branch_len = old["branchWindow"]["endRva"] - old["branchWindow"]["startRva"]
    load_offset = old["typeLoadRva"] - old["branchRva"]
    load = image.pe.bytes_at_va(body + load_offset, 7)
    cell = (body + load_offset + 7 + struct.unpack_from("<i", load, 3)[0]
            if load[:3] == b"\x48\x8B\x15" else None)
    if head[0] != 0xE9 or cell != int(entry["usageCellVa"], 16):
        raise RouteRefused(f"branch-shape={wrapper}:type-load-offset={load_offset:#x}")
    dispatcher = {
        "switchTableRva": table_va - base, "switchEntryCount": count,
        "switchTableSha256": _sha256_upper(image.pe.bytes_at_va(table_va, count * 4)),
        "switchTargetRva": target - base, "switchEntryHex": head.hex().upper(),
        "branchRva": body - base,
        "branchWindow": _window(image, body, body + branch_len, old["branchWindow"]["boundary"]),
        "typeLoadRva": body + load_offset - base, "typeLoadHex": load.hex().upper(),
        "usageCellRva": cell - base, "usageRawHex": image.pe.bytes_at_va(cell, 8).hex().upper(),
        "registeredTypeIndex": entry["registeredTypeIndex"], "wrapperTypeDefinition": entry["typeDefinition"],
    }
    methods = [_deserialize_method(image, wrapper), _deserialize_method(image, wrapper, nested_of=wrapper)]
    extents = image.mapper.pdata_function_extents(image.pe)
    fragments = BodyIndex(image).chained_fragments
    source, formatter = base + methods[0][3], base + methods[1][3]
    pieces = [(source, extents[source])] + [(s, s + n) for s, n in fragments.get(source, ())]
    windows = [_window(image, s, end, "complete selected source reader hot body" if i == 0
                       else "chained selected source reader fragment") for i, (s, end) in enumerate(pieces)]
    windows.append(_window(image, formatter, extents[formatter], route["codeWindows"][-1]["boundary"]))
    rows: list[dict[str, Any]] = []
    for s, end in sorted(pieces):
        rows.extend(image.mapper.decode_x64_subset(image.pe.bytes_at_va(s, end - s), s, stop_offset=end - s))
    for row in rows:
        row["vaInt"] = int(row["va"], 16)
        row["raw"] = bytes.fromhex(row["bytes"].replace(" ", ""))
    headers = [r for r in rows if r["text"].startswith("cmp ") and r["text"].endswith(f", {len(fields):#x}")
               and r["raw"][-1] == len(fields)]
    if len(headers) != 1 or len(headers[0]["raw"]) not in (4, 5):
        raise RouteRefused(f"member-count-instruction={wrapper}:found={len(headers)}")
    header = headers[0]
    owner = image.metadata.types[entry["typeDefinition"]]
    setters = image.setter_methods(owner, parameter="typeName", label=LABEL)
    setter_targets = {image.method_pointer_va(image.metadata.methods[r[0]]) for r in setters}
    reads: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    pending_load = None
    for i, row in enumerate(rows):
        if row["vaInt"] <= header["vaInt"]:
            continue
        if row["text"].startswith("mov rdx, [rip") and row["raw"][:3] == b"\x48\x8B\x15":
            pending_load = row
        callee = _call_target(row)
        if callee is None:
            continue
        if callee in setter_targets:
            calls.append({"memberIndex": len(reads) - 1, "callsiteRva": row["vaInt"] - base,
                          "callHex": row["raw"].hex().upper(), "targetRva": callee - base})
            continue
        back = [r["text"] for r in rows[max(0, i - 3):i]]
        if "mov rcx, rdi" in back and len(reads) < len(fields):
            member = len(reads)
            name, kind = fields[member]
            reads.append({"memberIndex": member, "fieldName": name, "readKind": kind,
                          "sourceCallsiteRva": row["vaInt"] - base, "sourceCallHex": row["raw"].hex().upper(),
                          "sourceTargetRva": callee - base})
            if kind.startswith("Param<"):
                if pending_load is None:
                    raise RouteRefused(f"param-context-load={wrapper}:member={member}")
                contexts.append(_derive_context(image, member, pending_load, PARAM_ELEMENT_TYPES[kind]))
            pending_load = None
    if len(reads) != len(fields):
        raise RouteRefused(f"source-reads={wrapper}:found={len(reads)}:fields={len(fields)}")
    regenerated = dict(route)
    regenerated.update({
        "tag": tag, "serializedMemberCount": len(fields), "fields": fields, "dispatcher": dispatcher,
        "methods": methods, "codeWindows": windows,
        "memberCountInstruction": {"rva": header["vaInt"] - base, "hex": header["raw"].hex().upper()},
        "setterMethods": setters, "setterCallsites": calls, "orderedSourceReads": reads,
        "nestedContexts": contexts,
    })
    return regenerated


def _derive_context(image: Any, member: int, load: dict[str, Any], expected_type: str,
                    *, expected_base: str = 'Beyond.Gameplay.Actions.Param`1') -> dict[str, Any]:
    base = image.pe.image_base
    va = load["vaInt"]
    cell = va + 7 + struct.unpack_from("<i", load["raw"], 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                              image.registration["genericInstsCount"], source=LABEL, offset=address)
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise RouteRefused(f"context-arity=member={member}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    carrier_ptr = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_ptr, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
                                   type_count=len(image.metadata.types), source=LABEL)
    if image.type_name(carrier['baseDefinitionIndex']) != expected_base:
        raise RouteRefused(f'context-carrier=member={member}:expected={expected_base}:installed={image.type_name(carrier["baseDefinitionIndex"])}')
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    if len(child.arguments) != 1:
        raise RouteRefused(f'context-element-arity=member={member}:expected=1:actual={len(child.arguments)}')
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    named_definition = struct.unpack_from("<Q", element)[0] if element[10] in (0x11,0x12) else None
    definition = named_definition if element[10] == 0x11 else None
    name = image.type_name(named_definition) if named_definition is not None else canonical_type_name(
        RUNTIME_PRIMITIVE_TYPE_NAMES.get(element[10],''))
    if element[10] == 0x15:
        from scripts.game_data.il2cpp.protocol import runtime_type_name
        name = runtime_type_name(image.pe,image.metadata,child.arguments[0].type_pointer_va)
    if name is None or canonical_type_name(name) != canonical_type_name(expected_type):
        raise RouteRefused(f"context-element=member={member}:expected={expected_type}:installed={name}")
    return {
        "memberIndex": member, "instructionRva": va - base, "instructionHex": load["raw"].hex().upper(),
        "cellRva": cell - base, "usageRawHex": usage.hex().upper(), "methodSpecIndex": index,
        "methodSpec": list(spec), "argumentRawHex": raw.hex().upper(), "typeKind": raw[10],
        "classCarrier": carrier, "classInstantiation": child_row, "elementRawHex": element.hex().upper(),
        "elementTypeKind": element[10], "elementTypeDefinition": definition, "elementTypeName": expected_type,
    }


def open_selected_build() -> tuple[Any, dict[str, str]]:
    """The installed image plus its native input hashes, or a refusal."""
    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED or gate.gameassembly is None:
        raise RouteRefused(f"native-inputs:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file():
        raise RouteRefused("native-inputs:UnityPlayer.dll:missing")
    inputs = {"GameAssembly.dll": _sha256_upper(gate.gameassembly.read_bytes()),
              "global-metadata.dat": _sha256_upper(gate.metadata.read_bytes()),
              "UnityPlayer.dll": _sha256_upper(unityplayer.read_bytes())}
    return open_native_image(gate.gameassembly, gate.metadata), inputs


def _read_switch(image: Any, family: str, cache: dict[str, Any]) -> dict[str, Any]:
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    if family not in cache:
        if "_wrappers" not in cache:
            cache["_wrappers"] = derive_from_image(image)
        cache[family] = read_union_switch(
            image, f"Beyond_Gameplay_Actions_{family}ForMemoryPack", wrappers=cache["_wrappers"])
    return cache[family]


def regenerate(contract: dict[str, Any], *, opener: Any = open_selected_build,
               route_builder: Any = _regenerate_route, switch_reader: Any = _read_switch,
               validator: Any = None) -> tuple[dict[str, Any], list[str]]:
    """Rebuild every route for the selected build, or name each refused claim.

    Nothing is regenerated partially: one refused route refuses the contract,
    because the loader requires every reviewed route to validate.
    """
    validator = validator or validate_current_native_contract
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    layouts = json.loads(LAYOUT_PATH.read_bytes()).get("layouts", [])
    try:
        image, inputs = opener()
    except RouteRefused as exc:
        return contract, [str(exc)]
    if (inputs["GameAssembly.dll"], inputs["global-metadata.dat"]) != (
            catalog["nativeInputs"]["gameAssemblySha256"].upper(),
            catalog["nativeInputs"]["metadataSha256"].upper()):
        return contract, ["catalog-inputs:levelscript_union_tags.json is not regenerated for the selected build"]
    cache: dict[str, Any] = {}
    refused, routes = [], []
    for route in contract["routes"]:
        try:
            switch = switch_reader(image, route["nativeFamily"], cache)
            routes.append(route_builder(image, route, catalog, layouts, switch))
        except (RouteRefused, KeyError, IndexError) as exc:
            refused.append(f"{route['codecFamily']}:{route['wrapperName']}:{type(exc).__name__}:{exc}")
    if refused:
        return contract, refused
    regenerated = dict(contract)
    regenerated["nativeInputs"] = inputs
    regenerated["routes"] = routes
    try:
        _check_shape(regenerated, catalog, layouts)
        validator(regenerated, catalog)
    except ValueError as exc:
        return contract, [f"post-validation:{exc}"]
    return regenerated, []


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        print(json.dumps(validate_current_native_contract(), indent=1))
        return 0
    contract = json.loads(CONTRACT_PATH.read_bytes().decode("utf-8-sig"))
    regenerated, refused = regenerate(contract)
    print(json.dumps({"refused": refused,
                      "routes": [[r["codecFamily"], r["tag"]] for r in regenerated["routes"]],
                      "written": bool(args.write and not refused)}, indent=1))
    if refused:
        return 1
    if args.write:
        text = json.dumps(regenerated, indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n"
        CONTRACT_PATH.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
