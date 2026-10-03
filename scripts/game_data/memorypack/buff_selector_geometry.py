"""Native-proved HitBox/ShapeData values and their FindTarget parent joins."""
from __future__ import annotations
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vectors
from scripts.game_data.memorypack import buff_adding_cooldown as scalar

CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_geometry_native.json"
LABEL = "buffSelectorGeometry"
ROLES = ("findTargetAction", "hitBoxFinder", "shapeData", "inFightFinder")


def _contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_bytes())
    if (value.get("schema") != "endfield.buff-selector-geometry-native-contract.v1"
            or value.get("status") != "exact-current-build"
            or set(value.get("layouts", {})) != set(ROLES)):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def finder_tags() -> frozenset[int]:
    return frozenset(row["unionTag"] for row in _contract()["layouts"].values()
                     if row.get("family") == "SelectorFinder")


def action_tag() -> int:
    return _contract()["layouts"]["findTargetAction"]["unionTag"]


def _fail(check: str, expected: Any, actual: Any, role: str) -> None:
    def bounded(value):
        if isinstance(value, str): return value[:256]
        if isinstance(value, dict): return {str(k): bounded(v) for k, v in list(value.items())[:20]}
        if isinstance(value, (list, tuple)): return [bounded(v) for v in value[:20]]
        return value
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
                            expected=bounded(expected), actual=bounded(actual))
    error.diagnostic.update({"validator": LABEL, "role": role, "nativeInputs": _contract()["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _store_offset(image, row, role):
    image.check_instruction_windows([row], label=LABEL)
    raw = bytes.fromhex(row[1])
    instructions = image.mapper.decode_x64_subset(raw, image.pe.image_base + row[0], stop_offset=len(raw))
    match = re.fullmatch(r"mov \[r(?:ax|cx)\+0x([0-9a-f]+)\], \w+", instructions[0]["text"]) if len(instructions) == 1 else None
    if match is None: _fail("destination-instruction", "one selected object-field store", instructions, role)
    return int(match[1], 16)


def validate_current_native_contract(*, selector_native: dict[str, Any],
        vector_native: dict[str, Any], gameassembly: Path | None = None,
        metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); expected = c["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
                                         gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("native-inputs", expected["UnityPlayer.dll"], "UnityPlayer.dll missing or mismatched", "shared")
    for name, child in (("selector", selector_native), ("vector", vector_native)):
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("child-native-inputs", {"status": "validated", "nativeInputs": expected},
                  {k: child.get(k) for k in ("status", "nativeInputs")}, name)
    image = open_native_image(gate.gameassembly, gate.metadata)
    source = json.loads((CONTRACTS_DIR / c["sourceContract"]).read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=CONTRACTS_DIR / c["sourceContract"])
    switch = json.loads((CONTRACTS_DIR / c["switchContract"]).read_bytes())
    if switch["nativeInputs"] != expected: _fail("switch-native-inputs", expected, switch["nativeInputs"], "shared")
    routes, route_audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if route_audit.get("status") != "validated": _fail("action-dispatcher", "validated", route_audit.get("status"), "shared")
    wrappers = derive_from_image(image)
    for role, layout in c["layouts"].items():
        wrapper = wrappers.get(layout["wrapperTypeDefinition"])
        if (wrapper is None or wrapper.name != layout["wrapperName"] or wrapper.wrapped_type != layout["wrappedType"]
                or len(wrapper.inherited_members) != layout["inheritedMemberCount"]
                or len(wrapper.members) != layout["serializedMemberCount"]):
            _fail("wrapper", {k: layout[k] for k in ("wrapperName", "wrappedType", "serializedMemberCount")},
                  None if wrapper is None else wrapper.row(), role)
        if [f["readKind"] for f in layout["fields"]] != source["anonymousReadOrder"][layout["sourceReadOrder"]]:
            _fail("source-read-order", source["anonymousReadOrder"][layout["sourceReadOrder"]], layout["fields"], role)
        image.validate_method_row(layout["readerMethod"], label=LABEL)
        window = next(w for w in source["codeWindows"] if w["startRva"] == layout["readerMethod"][3])
        last_source = window["startRva"]
        for member, field in zip(wrapper.members, layout["fields"], strict=True):
            actual = {"name": member.name, "methodIndex": member.method_index,
                      "declaredType": member.declared_type, "kind": member.kind, "width": member.width}
            if actual != {k: field[k] for k in actual}: _fail("setter-member", {k: field[k] for k in actual}, actual, role)
            setter_rva = image.method_pointer_va(image.metadata.methods[member.method_index]) - image.pe.image_base
            if setter_rva != field["setterRva"]: _fail("setter-method", field["setterRva"], setter_rva, role)
            read_kind = field["readKind"]
            if ((read_kind == "byte" and (member.kind != "bool" or member.width != 1))
                    or (read_kind == "scalar32" and (member.width != 4 or member.kind not in ("enum", "scalar32", "float32")))):
                _fail("source-kind-width", read_kind, actual, role)
            anchor = field.get("setterCall") or field["sourceStore"]
            if not last_source < anchor[0] < window["endRva"]: _fail("source-field-order", [last_source, window["endRva"]], anchor[0], role)
            last_source = anchor[0]
            if "setterCall" in field:
                image.check_instruction_windows([anchor], label=LABEL);raw = bytes.fromhex(anchor[1])
                target = anchor[0] + 5 + struct.unpack_from("<i", raw, 1)[0] if len(raw) == 5 and raw[0] == 0xE8 else None
                if target != setter_rva: _fail("source-setter-call", setter_rva, target, role)
            else:
                store = field["setterStore"]
                if not setter_rva <= store[0] < setter_rva + 32: _fail("setter-store-owner", [setter_rva, setter_rva + 32], store[0], role)
                a = _store_offset(image, field["sourceStore"], role); b = _store_offset(image, store, role)
                if a != b: _fail("source-setter-destination", b, a, role)
        for join in layout["typedChildren"]:
            contexts = [r for r in source["nestedContexts"] if r["instructionRva"] == join["sourceContextRva"]]
            if len(contexts) != 1: _fail("typed-source-context", 1, len(contexts), role)
            context = contexts[0];args = image.instantiations.resolve(context["methodSpec"][2]).arguments
            actual = runtime_type_name(image.pe, image.metadata, args[0].type_pointer_va) if len(args) == 1 else None
            field = layout["fields"][join["memberIndex"]]
            if actual != join["typeName"] or field["declaredType"] != actual or field["name"] != join["fieldName"]:
                _fail("typed-parent-field", join, {"contextType": actual, "field": field}, role)
        if layout.get("family") == "SelectorFinder":
            image.validate_dispatcher({**switch["dispatcher"], **layout["dispatcher"]}, label=LABEL)
            branch = image.window_bytes(layout["dispatcher"]["routeWindow"]);offset = branch.find(b"\x48\x8b\x15")
            cell = layout["dispatcher"]["switchTargetRva"] + offset + 7 + struct.unpack_from("<i", branch, offset + 3)[0] if offset >= 0 else None
            if cell != layout["dispatcher"]["usageCellRva"]: _fail("dispatcher-type-load", layout["dispatcher"]["usageCellRva"], cell, role)
        elif layout.get("family") == "AbilityActionData":
            route = routes.get(layout["unionTag"])
            if (route is None or route.status != "resolved" or route.wrapper_name != layout["wrapperName"]
                    or list(route.member_order) != [f["name"] for f in layout["fields"]]):
                _fail("action-route", layout["wrapperName"], None if route is None else route.row(), role)
    return {"status": "validated", "nativeInputs": expected, "layouts": c["layouts"]}


def checked_layout(native: dict[str, Any], role: str) -> dict[str, Any]:
    c = _contract()
    if (native.get("status") != "validated" or native.get("nativeInputs") != c["nativeInputs"]
            or native.get("layouts", {}).get(role) != c["layouts"][role]):
        raise ValueError(f"{LABEL}.decode:native-layout-drift:{role}")
    return native["layouts"][role]


def _shape(reader, source, digest, context):
    layout = checked_layout(context["selectorGeometry"], "shapeData");begin = reader.pos;fields = []
    if reader.peek() == 255: reader.take(1, "null-shape")
    else:
        reader.header(layout["serializedMemberCount"])
        joins = {r["memberIndex"]: r for r in layout["typedChildren"]}
        for index, field in enumerate(layout["fields"]):
            start = reader.pos;kind = field["readKind"];value = {}
            if kind in ("byte", "scalar32"): value["rawHex"] = reader.take(1 if kind == "byte" else 4, field["name"]).hex().upper()
            elif kind == "scalar-payload":
                if joins[index]["typeName"] != scalar._contract()["rootContextType"]: raise ValueError(f"{LABEL}.decode:typed-scalar")
                reader.scalar_payload();value["child"] = scalar.decode_adding_cooldown(reader.data, start, reader.pos,
                    native_validation=context["effectVectors"]["scalarNative"])
                if value["child"].get("wholeValueExact") is not True: raise ValueError(f"{LABEL}.decode:scalar-incomplete")
            elif kind == "vector-payload":
                if joins[index]["typeName"] != vectors._contract()["vectorRuntimeTypeName"]: raise ValueError(f"{LABEL}.decode:typed-vector")
                reader.vector_payload();value["child"] = vectors.decode_blackboard_vector3_value(reader.data, source=source,
                    logical_sha256=digest, start=start, end=reader.pos, native_validation=context["effectVectors"])
            else: raise ValueError(f"{LABEL}.decode:unsupported-shape-kind={kind}")
            fields.append({"name": field["name"], "declaredType": field["declaredType"], "kind": kind,
                           "start": start, "end": reader.pos, **value})
    return {"start": begin, "end": reader.pos, "namedFields": fields, "wholeStoredSpanExact": True}


def decode_finder(data: bytes, *, source: str, digest: str, start: int, end: int,
                  context: dict[str, Any]) -> dict[str, Any]:
    native = context["selectorGeometry"]; c = _contract()
    if (hashlib.sha256(data).hexdigest().upper() != digest.upper() or not source
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)
            or any(context["effectVectors"].get("nativeInputs", {}).get(k) != v for k, v in c["nativeInputs"].items())):
        raise ValueError(f"{LABEL}.decode:source-or-child-inputs")
    roles = {layout["unionTag"]: role for role, layout in c["layouts"].items() if layout.get("family") == "SelectorFinder"}
    reader = Reader(data, source, end);reader.pos = start;tag = reader.nested_union_tag(tuple(roles), "geometry-finder");fields = []
    if tag is None:
        checked_layout(native, "hitBoxFinder");status = "exact-null-union"
    else:
        layout = checked_layout(native, roles[tag])
        if reader.peek() == 255: reader.take(1, "null-finder-wrapper");status = "exact-null-wrapper"
        else:
            reader.header(layout["serializedMemberCount"]);status = "named-finder-exact-span"
            for field in layout["fields"]:
                begin = reader.pos;kind = field["readKind"];value = {}
                if kind in ("byte", "scalar32"): value["rawHex"] = reader.take(1 if kind == "byte" else 4, field["name"]).hex().upper()
                elif kind == "counted-shape-profiles":
                    shape = checked_layout(native, "shapeData");joins = layout["typedChildren"]
                    if (len(joins) != 1 or joins[0]["fieldName"] != field["name"]
                            or joins[0]["typeName"] != "System.Collections.Generic.List`1<" + shape["wrappedType"] + ">"):
                        raise ValueError(f"{LABEL}.decode:typed-shape-list")
                    count = reader.count(1, reserve=4, nullable=True);value["count"] = count
                    value["elements"] = [_shape(reader, source, digest, context) for _ in range(max(0, count))]
                else: raise ValueError(f"{LABEL}.decode:unsupported-finder-kind={kind}")
                fields.append({"name": field["name"], "declaredType": field["declaredType"], "kind": kind,
                               "start": begin, "end": reader.pos, **value})
    if reader.pos != end: raise ValueError(f"{LABEL}.decode:finder-end")
    return {"source": source, "logicalSha256": digest.upper(), "start": start, "end": end, "tag": tag,
            "status": status, "namedFields": fields, "recursiveStoredSchemaExact": True}
