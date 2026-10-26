"""Exact SetNpcAtmosphericClusterVisible ActionBase cursor and native proof.

This establishes stored fields at a caller supplied cursor. Serialized
visibility values do not establish a runtime NPC state change.

The action adds a `clusterId` string parameter and a `visible` boolean
parameter after the inherited action fields
(`levelscript_npc_atmospheric_cluster_native.json`).
"""

from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.codecs.levelscript import params
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR, memorypack_union_header


LABEL = "npcAtmosphericCluster"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_npc_atmospheric_cluster_native.json"


class NpcAtmosphericClusterCodecError(ValueError):
    """The selected member sequence is absent or incomplete."""


@lru_cache(maxsize=1)
def _contract(path=None) -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH if path is None else path,
        schema="endfield.levelscript-npc-atmospheric-cluster-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    route = value.get("route") or {}
    fields = route.get("fields")
    members = route.get("orderedMembers")
    contexts = route.get("nestedContexts")
    if (
        value.get("catalogContract") != "levelscript_union_tags.json"
        or route.get("family") != "ActionBase"
        or type(route.get("tag")) is not int or not 0 <= route["tag"] < 0x10000
        or route.get("name") != "SetNpcAtmosphericClusterVisible"
        or route.get("serializedMemberCount") != 10
        or not isinstance(fields, list) or len(fields) != 10
        or any(not isinstance(row, list) or len(row) != 2 or row[1] not in ("bool", "int32", "string", "Param<string>", "Param<bool>") for row in fields)
        or not isinstance(members, list)
        or [(row.get("fieldName"), row.get("wireKind")) for row in members] != [tuple(row) for row in fields]
        or [row.get("memberIndex") for row in members] != list(range(10))
        or not isinstance(contexts, list)
        or [(row.get("memberIndex"), row.get("elementTypeName")) for row in contexts]
        != [(8, "System.String"), (9, "System.Boolean")]
    ):
        raise NpcAtmosphericClusterCodecError(f"{LABEL}.contract:source-shape")
    return value


def decode_npc_atmospheric_cluster(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Consume exactly one non-null node using the reviewed route header."""
    route = _contract()["route"]
    start = offset
    prefix = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(prefix)] != prefix:
        raise NpcAtmosphericClusterCodecError(f"{LABEL}.union:expected={prefix.hex().upper()},offset={offset}")
    offset += len(prefix)
    values: dict[str, Any] = {}
    for name, kind in route["fields"]:
        if kind == "bool":
            if offset >= len(data) or data[offset] not in (0, 1):
                raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:invalid-bool,offset={offset}")
            values[name] = bool(data[offset])
            offset += 1
        elif kind == "int32":
            if offset + 4 > len(data):
                raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:truncated-int32,offset={offset}")
            values[name] = struct.unpack_from("<i", data, offset)[0]
            offset += 4
        elif kind == "string":
            if offset + 4 > len(data):
                raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:truncated-string-length,offset={offset}")
            size = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if size == -1:
                values[name] = None
            elif size < 0 or size > 1_000_000 or offset + size > len(data):
                raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:invalid-string-length={size},offset={offset - 4}")
            else:
                try:
                    values[name] = data[offset:offset + size].decode("utf-8")
                except UnicodeDecodeError as error:
                    raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:invalid-utf8,offset={offset}") from error
                offset += size
        else:
            if offset < len(data) and data[offset] == 0xFF:
                values[name] = None
                offset += 1
                continue
            decoder = params.decode_string_param if kind == "Param<string>" else params.decode_bool_param
            decoded = decoder(data, offset)
            if decoded is None:
                raise NpcAtmosphericClusterCodecError(f"{LABEL}.{name}:invalid-{kind},offset={offset}")
            values[name], offset = decoded
    return {
        "sourceOffset": start, "endOffset": offset,
        "unionTag": route["tag"], "memberCount": route["serializedMemberCount"],
        "wrapperName": route["wrapperName"], "fields": values,
    }, offset


def _direct_call(image: Any, row: dict[str, Any]) -> int:
    rva = row["rva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != row["hex"].upper():
        raise ValueError(f"{LABEL}.native:callsite={rva:#x}")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target != row["targetRva"]:
        raise ValueError(f"{LABEL}.native:call-target={rva:#x}")
    return target


def _validate_param_context(image: Any, context: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-method-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1 or list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:param-method-spec-record")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != context["typeKind"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-carrier-type")
    carrier_ptr = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_ptr, 32)
    base_ptr = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_ptr, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if carrier != context["classCarrier"] or image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1":
        raise ValueError(f"{LABEL}.native:param-carrier")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    expected_kind = {"System.String": 14, "System.Boolean": 2}[context["elementTypeName"]]
    if (
        element.hex().upper() != context["elementRawHex"]
        or element[10] != context["elementTypeKind"]
        or element[10] != expected_kind
    ):
        raise ValueError(f"{LABEL}.native:param-element")


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate selected dispatch and complete ten-member source order."""
    contract = _contract()
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(inputs["GameAssembly.dll"], inputs["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file() or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != inputs["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    return _validate_native(image, contract)


def _validate_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    route = contract["route"]
    inputs = contract["nativeInputs"]
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or inputs["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or inputs["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
        or catalog["families"]["ActionBase"][route["tag"]] != {
            "name": route["name"], "wrapperName": route["wrapperName"],
            "tag": route["tag"], "memberCount": route["serializedMemberCount"],
            "wrappedType": route["typeName"],
        }
    ):
        raise ValueError(f"{LABEL}.native:catalog-join")
    pe, metadata = image.pe, image.metadata
    base = pe.image_base
    dispatch = route["dispatcher"]
    switch = catalog["switches"]["ActionBase"]
    if (
        int(switch["tableVa"], 16) != base + dispatch["switchTableRva"]
        or switch["entryCount"] != dispatch["switchEntryCount"]
        or switch["entryCount"] != len(catalog["families"]["ActionBase"])
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = pe.bytes_at_va(base + dispatch["switchTableRva"], dispatch["switchEntryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatch["switchTableSha256"]:
        raise ValueError(f"{LABEL}.native:switch-hash")
    target = struct.unpack_from("<I", table, route["tag"] * 4)[0]
    jump = pe.bytes_at_va(base + target, 5)
    if (
        target != dispatch["switchTargetRva"] or jump[0] != 0xE9
        or jump.hex().upper() != dispatch["switchEntryHex"]
        or target + 5 + struct.unpack_from("<i", jump, 1)[0] != dispatch["branchRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-route")
    branch = dispatch["branchWindow"]
    if branch["startRva"] != dispatch["branchRva"]:
        raise ValueError(f"{LABEL}.native:branch-range")
    image.check_windows([branch], label=LABEL)
    load_rva = dispatch["typeLoadRva"]
    load = pe.bytes_at_va(base + load_rva, 7)
    if (
        not branch["startRva"] <= load_rva <= branch["endRva"] - 7
        or load[:3] != b"\x48\x8b\x15" or load.hex().upper() != dispatch["typeLoadHex"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-load")
    cell_rva = load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = pe.bytes_at_va(base + cell_rva, 8)
    if cell_rva != dispatch["usageCellRva"] or usage.hex().upper() != dispatch["usageRawHex"]:
        raise ValueError(f"{LABEL}.native:usage-cell")
    type_index = unresolved_usage_index(usage, image.registration["typesCount"], tag=1, source=LABEL, offset=base+cell_rva)
    type_pointer = pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
    definition = struct.unpack_from("<Q", pe.bytes_at_va(type_pointer, 16))[0]
    if (
        type_index != dispatch["registeredTypeIndex"]
        or definition != dispatch["wrapperTypeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-identity")
    for parent in route["wrapperInheritance"] + route["managedInheritance"]:
        image.check_wrapper_inheritance(parent, label=LABEL)
    managed = metadata.types[route["managedInheritance"][0]["typeDefinition"]]
    managed_fields = [[metadata.string(field.name_index), metadata.metadata_type_name(field.type_index)] for field in metadata.fields_for(managed)]
    if managed_fields != route["ownManagedFields"]:
        raise ValueError(f"{LABEL}.native:own-managed-fields")
    if image.setter_methods(metadata.types[definition], parameter="typeName", label=LABEL) != route["ownWrapperSetters"]:
        raise ValueError(f"{LABEL}.native:own-wrapper-setters")
    for owner in route["inheritedSetterOwners"]:
        if image.type_name(owner["typeDefinition"]) != owner["typeName"] or image.setter_methods(
            metadata.types[owner["typeDefinition"]], parameter="typeName", label=LABEL
        ) != owner["setters"]:
            raise ValueError(f"{LABEL}.native:inherited-setters")
    methods = route["methods"]
    for row in methods:
        image.validate_method_row(row, label=LABEL)
    source_ptr = image.method_pointer_va(metadata.methods[methods[0][0]])
    formatter_ptr = image.method_pointer_va(metadata.methods[methods[1][0]])
    windows = route["codeWindows"]
    if len(windows) != 2:
        raise ValueError(f"{LABEL}.native:code-windows")
    image.check_windows(windows, label=LABEL)
    extents = image.mapper.pdata_function_extents(pe)
    if (
        windows[0]["startRva"] != source_ptr - base
        or windows[0]["endRva"] != extents.get(source_ptr, 0) - base
        or BodyIndex(image).chained_fragments.get(source_ptr, ())
        or windows[1]["startRva"] != formatter_ptr - base
        or windows[1]["endRva"] != extents.get(formatter_ptr, 0) - base
    ):
        raise ValueError(f"{LABEL}.native:method-extents")
    header = route["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label=LABEL)
    if header["hex"].upper() != (b"\x80\x7c\x24\x38" + bytes((route["serializedMemberCount"],))).hex().upper():
        raise ValueError(f"{LABEL}.native:member-count")
    if not windows[0]["startRva"] <= header["rva"] <= windows[0]["endRva"] - len(bytes.fromhex(header["hex"])):
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = header["rva"]
    targets: dict[str, set[int]] = {}
    contexts = {row["memberIndex"]: row for row in route["nestedContexts"]}
    for member in route["orderedMembers"]:
        read, setter = member["sourceRead"], member["setterCall"]
        if (
            read["rva"] <= previous or setter["rva"] <= read["rva"]
            or not (windows[0]["startRva"] <= read["rva"] and read["rva"] + 5 <= setter["rva"]
                    and setter["rva"] + 5 <= windows[0]["endRva"])
        ):
            raise ValueError(f"{LABEL}.native:member-order={member['memberIndex']}")
        previous = setter["rva"]
        targets.setdefault(member["wireKind"], set()).add(_direct_call(image, read))
        setter_target = _direct_call(image, setter)
        method_row = member["setterMethod"]
        image.validate_method_row(method_row, label=LABEL)
        if method_row[2].removeprefix("set_").strip("_") != member["fieldName"]:
            raise ValueError(f"{LABEL}.native:setter-field={member['memberIndex']}")
        if image.method_pointer_va(metadata.methods[method_row[0]]) != base + setter_target:
            raise ValueError(f"{LABEL}.native:setter-target={member['memberIndex']}")
        context = contexts.get(member["memberIndex"])
        if member["wireKind"].startswith("Param<"):
            if context is None or not (
                route["orderedMembers"][member["memberIndex"] - 1]["setterCall"]["rva"] + 5 <= context["instructionRva"]
                and context["instructionRva"] + 7 <= read["rva"]):
                raise ValueError(f"{LABEL}.native:param-source-order={member['memberIndex']}")
            _validate_param_context(image, context)
        elif context is not None:
            raise ValueError(f"{LABEL}.native:unexpected-param-context={member['memberIndex']}")
    if (
        any(len(values) != 1 for values in targets.values())
        or targets["Param<string>"] != targets["Param<bool>"]
        or len(set.union(*targets.values())) != len(targets) - 1
    ):
        raise ValueError(f"{LABEL}.native:primitive-read-helpers")
    return {"status": "validated", "family": route["family"], "tag": route["tag"],
            "serializedMemberCount": len(route["orderedMembers"]), "nestedParamContexts": len(contexts)}
