"""Selected native proof and exact wire cursor for ResetSummonTeamAI.

The reader establishes one serialized ActionBase node at a caller supplied
cursor. It does not infer execution or summon AI effects from the bytes.

`ResetSummonTeamAI` has only the eight inherited action fields; the
contract (`levelscript_reset_summon_team_ai_native.json`) names it through
`levelscript_union_tags.json` and checks that member sequence.
"""

from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR, memorypack_union_header


LABEL = "resetSummonTeamAI"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_reset_summon_team_ai_native.json"


class ResetSummonTeamAICodecError(ValueError):
    """The selected member sequence is absent or incomplete."""


@lru_cache(maxsize=1)
def _contract(path=None) -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH if path is None else path,
        schema="endfield.levelscript-reset-summon-team-ai-native-contract.v1",
        status="exact-current-build",
        label=LABEL,
    )
    route = value.get("route") or {}
    members = route.get("orderedMembers")
    fields = route.get("fields")
    if (
        value.get("catalogContract") != "levelscript_union_tags.json"
        or route.get("family") != "ActionBase"
        or type(route.get("tag")) is not int or not 0 <= route["tag"] < 0x10000
        or route.get("name") != "ResetSummonTeamAI"
        or route.get("serializedMemberCount") != 8
        or not isinstance(fields, list)
        or len(fields) != 8
        or any(not isinstance(row, list) or len(row) != 2 or row[1] not in ("bool", "int32", "string") for row in fields)
        or not isinstance(members, list)
        or [(row.get("fieldName"), row.get("wireKind")) for row in members] != [tuple(row) for row in fields]
        or [row.get("memberIndex") for row in members] != list(range(8))
    ):
        raise ResetSummonTeamAICodecError(f"{LABEL}.contract:source-shape")
    return value


def decode_reset_summon_team_ai(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Consume exactly one non-null node using the reviewed route header."""
    route = _contract()["route"]
    start = offset
    prefix = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(prefix)] != prefix:
        raise ResetSummonTeamAICodecError(f"{LABEL}.union:expected={prefix.hex().upper()},offset={offset}")
    offset += len(prefix)
    values: dict[str, Any] = {}
    for name, kind in route["fields"]:
        if kind == "bool":
            if offset >= len(data) or data[offset] not in (0, 1):
                raise ResetSummonTeamAICodecError(f"{LABEL}.{name}:invalid-bool,offset={offset}")
            values[name] = bool(data[offset])
            offset += 1
        elif kind == "int32":
            if offset + 4 > len(data):
                raise ResetSummonTeamAICodecError(f"{LABEL}.{name}:truncated-int32,offset={offset}")
            values[name] = struct.unpack_from("<i", data, offset)[0]
            offset += 4
        else:
            if offset + 4 > len(data):
                raise ResetSummonTeamAICodecError(f"{LABEL}.{name}:truncated-string-length,offset={offset}")
            size = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if size == -1:
                values[name] = None
            elif size < 0 or size > 1_000_000 or offset + size > len(data):
                raise ResetSummonTeamAICodecError(f"{LABEL}.{name}:invalid-string-length={size},offset={offset - 4}")
            else:
                try:
                    values[name] = data[offset:offset + size].decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ResetSummonTeamAICodecError(f"{LABEL}.{name}:invalid-utf8,offset={offset}") from error
                offset += size
    return {
        "sourceOffset": start,
        "endOffset": offset,
        "unionTag": route["tag"],
        "memberCount": route["serializedMemberCount"],
        "wrapperName": route["wrapperName"],
        "fields": values,
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


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate dispatch, inheritance and all eight source reads."""
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
    if image.setter_methods(metadata.types[definition], parameter="typeName", label=LABEL) != route["ownWrapperSetters"]:
        raise ValueError(f"{LABEL}.native:own-wrapper-setters")
    managed_definition = route["managedInheritance"][0]["typeDefinition"]
    if metadata.types[managed_definition].field_count != len(route["ownManagedFields"]):
        raise ValueError(f"{LABEL}.native:own-managed-fields")
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
    if len(windows) < 2:
        raise ValueError(f"{LABEL}.native:source-windows")
    image.check_windows(windows, label=LABEL)
    extents = image.mapper.pdata_function_extents(pe)
    fragments = BodyIndex(image).chained_fragments.get(source_ptr, ())
    if (
        windows[0]["startRva"] != source_ptr - base
        or windows[0]["endRva"] != extents.get(source_ptr, 0) - base
        or [(w["startRva"], w["endRva"]) for w in windows[1:-1]]
        != [(start - base, start + size - base) for start, size in fragments]
        or windows[-1]["startRva"] != formatter_ptr - base
        or windows[-1]["endRva"] != extents.get(formatter_ptr, 0) - base
    ):
        raise ValueError(f"{LABEL}.native:method-extents")
    header = route["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label=LABEL)
    if header["hex"].upper() != (b"\x40\x80\xfe" + bytes((route["serializedMemberCount"],))).hex().upper():
        raise ValueError(f"{LABEL}.native:member-count")
    ranges = [(w["startRva"], w["endRva"]) for w in windows[:-1]]
    if not any(start <= header["rva"] and header["rva"] + len(bytes.fromhex(header["hex"])) <= end for start, end in ranges):
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = header["rva"]
    targets: dict[str, set[int]] = {}
    for member in route["orderedMembers"]:
        read = member["sourceRead"]
        setter = member["setterCall"]
        if (
            read["rva"] <= previous or setter["rva"] <= read["rva"]
            or not any(start <= read["rva"] and read["rva"] + 5 <= setter["rva"] and setter["rva"] + 5 <= end for start, end in ranges)
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
    if any(len(values) != 1 for values in targets.values()) or len(set.union(*targets.values())) != len(targets):
        raise ValueError(f"{LABEL}.native:primitive-read-helpers")
    return {"status": "validated", "family": route["family"], "tag": route["tag"],
            "serializedMemberCount": len(route["orderedMembers"]), "sourceFragmentCount": len(fragments)}
