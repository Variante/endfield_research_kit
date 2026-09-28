"""Selected native gate for the reached LevelScript event-header wrappers.

The contract proves stored header bytes only. Runtime event registration and
dispatch require separate evidence. A failed or different installed build
leaves the reviewed header routes unavailable to the LevelScript reader.

Routes: `LevelEvent_OnSnapShotEnter` and `LevelEvent_OnSnapShotLeave`. Both
store the same 14-member shape and add no own wrapper fields: the selected
`ActionHeader` switch resolves each registered wrapper directly, and each
complete native `Deserialize` body reads the inherited `NodeBase` and
event-header members in order, ending with `validate` as `Param<bool>`. The
checked generic context and inherited setter identify that last member
independently of the source bytes. The shared ActionMap reader admits these
rows only while this gate confirms the switch, full method windows, ordered
helper calls and current build. Snapshot entry or exit bytes do not prove
that the event ran; owners that continue to later unions stay partial.

The command takes no options and prints the selected native audit, exiting
nonzero unless it validates; it has no source-replay mode.

Run as: python -m scripts.game_data.levelscript_header_native
"""

from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.levelscript_two_routes_native import _validate_context


LABEL = "levelscriptHeaderNative"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_header_native.json"
LAYOUT_PATH = Path(__file__).parent / "codecs" / "levelscript" / "action_map_layouts.json"
SCHEMA = "endfield.levelscript-header-native-contract.v1"


def _read_contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    routes = contract.get("routes")
    if (
        not isinstance(routes, list) or not routes
        or len({route.get("tag") for route in routes}) != len(routes)
        or any(route.get("nativeFamily") != "ActionHeader" for route in routes)
        or contract.get("evidenceBoundary") != "exact"
    ):
        raise ValueError(f"{LABEL}.contract:route-set")
    layout_contract = json.loads(LAYOUT_PATH.read_bytes())
    if layout_contract.get("schema") != "endfield.action-map-layouts.v3":
        raise ValueError(f"{LABEL}.contract:layout-schema")
    layouts = layout_contract.get("layouts", [])
    for route in routes:
        tag = route["tag"]
        fields = route.get("fields")
        reads = route.get("orderedSourceReads")
        if (
            route.get("codecFamily") != "ActionHeader"
            or route.get("serializedMemberCount") != 14
            or not isinstance(fields, list) or len(fields) != 14
            or not all(isinstance(item, list) and len(item) == 2 for item in fields)
            or [kind for _name, kind in fields] != [
                "bool", "int32", "bool", "string", "int32", "bool", "bool",
                "int32", "int32", "bool", "int32", "int32", "int32", "Param<bool>",
            ]
            or not isinstance(reads, list) or len(reads) != 14
            or [read.get("memberIndex") for read in reads] != list(range(14))
            or [[read.get("fieldName"), read.get("readKind")] for read in reads] != fields
            or set(route.get("readerHelpers", {})) != {kind for _name, kind in fields}
            or route.get("dispatcher", {}).get("dispatchKind") != "direct-branch"
            or len(route.get("methods", [])) != 2
            or route.get("memberCountInstruction", {}).get("hex", "").upper()[-2:] != "0E"
            or len(route.get("codeWindows", [])) < 2
            or route.get("inheritedValidateSetter", {}).get("memberIndex") != 13
            or len(route.get("nestedContexts", [])) != 1
            or route["nestedContexts"][0].get("elementTypeName") != "System.Boolean"
        ):
            raise ValueError(f"{LABEL}.contract:route-shape=ActionHeader:{tag:#x}")
        matching = [row for row in layouts if row.get("family") == "ActionHeader" and row.get("tag") == tag]
        if (
            len(matching) != 1
            or matching[0].get("fields") != fields
            or matching[0].get("wrapperName") != route.get("wrapperName")
            or matching[0].get("memberCount") != 14
            or matching[0].get("nativeGate") != "levelscript_header_native"
        ):
            raise ValueError(f"{LABEL}.contract:layout-join=ActionHeader:{tag:#x}")
        identity = matching[0].get("nativeIdentity") or {}
        dispatcher = route["dispatcher"]
        branch_hex = identity.get("branchCodeHex", "")
        if (
            identity.get("registeredTypeIndex") != dispatcher["registeredTypeIndex"]
            or identity.get("typeDefinition") != dispatcher["wrapperTypeDefinition"]
            or identity.get("usageRawHex") != dispatcher["usageRawHex"]
            or len(branch_hex) != 208
            or hashlib.sha256(bytes.fromhex(branch_hex)).hexdigest().upper()
            != dispatcher["branchWindow"]["sha256"]
        ):
            raise ValueError(f"{LABEL}.contract:layout-native-identity=ActionHeader:{tag:#x}")
        cursor = matching[0].get("cursorEvidence")
        if (
            not isinstance(cursor, dict)
            or not isinstance(cursor.get("source"), str) or not cursor["source"]
            or not isinstance(cursor.get("sourceSha256"), str) or len(cursor["sourceSha256"]) != 64
            or not isinstance(cursor.get("spanSha256"), str) or len(cursor["spanSha256"]) != 64
            or not isinstance(cursor.get("unionOffset"), int)
            or not isinstance(cursor.get("endOffset"), int)
            or cursor["endOffset"] <= cursor["unionOffset"]
        ):
            raise ValueError(f"{LABEL}.contract:cursor-anchor=ActionHeader:{tag:#x}")
    return contract


def _validate_route(image: Any, route: dict[str, Any], switch: dict[str, Any], wrappers: dict[int, Any], fragments: dict[int, Any], extents: dict[int, int]) -> dict[str, Any]:
    tag = route["tag"]
    branch = route["dispatcher"]
    base = image.pe.image_base
    if switch["entryCount"] != branch["switchEntryCount"] or int(switch["tableVa"], 16) != base + branch["switchTableRva"]:
        raise ValueError(f"{LABEL}.native:switch-shape=ActionHeader:{tag:#x}")
    table = image.pe.bytes_at_va(base + branch["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != branch["switchTableSha256"]:
        raise ValueError(f"{LABEL}.native:switch-hash=ActionHeader:{tag:#x}")
    target_rva = struct.unpack_from("<I", table, tag * 4)[0]
    entry = switch["entries"][tag]
    if (
        target_rva != branch["switchTargetRva"] == branch["branchRva"]
        or int(entry["targetVa"], 16) != base + target_rva
        or int(entry["bodyVa"], 16) != base + target_rva
        or entry["wrapperName"] != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:direct-branch=ActionHeader:{tag:#x}")
    image.check_windows([branch["branchWindow"]], label=LABEL)
    load_rva = branch["typeLoadRva"]
    raw = image.pe.bytes_at_va(base + load_rva, 7)
    if raw[:3] != b"\x48\x8b\x15" or raw.hex().upper() != branch["typeLoadHex"]:
        raise ValueError(f"{LABEL}.native:type-load=ActionHeader:{tag:#x}")
    cell_va = base + load_rva + 7 + struct.unpack_from("<i", raw, 3)[0]
    usage = image.pe.bytes_at_va(cell_va, 8)
    index = unresolved_usage_index(usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell_va)
    pointer_va = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer_va, 16))[0]
    if (
        cell_va - base != branch["usageCellRva"]
        or usage.hex().upper() != branch["usageRawHex"]
        or index != branch["registeredTypeIndex"] == entry["registeredTypeIndex"]
        or definition != branch["wrapperTypeDefinition"] == entry["typeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:registered-wrapper=ActionHeader:{tag:#x}")
    wrapper = wrappers[definition]
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or wrapper.own_members
        or len(wrapper.members) != 14
        or [member.name.lstrip("_") for member in wrapper.members] != [row[0] for row in route["fields"]]
    ):
        raise ValueError(f"{LABEL}.native:inherited-fields=ActionHeader:{tag:#x}")
    methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
    image.check_windows(route["codeWindows"], label=LABEL)
    image.check_instruction_windows([[route["memberCountInstruction"]["rva"], route["memberCountInstruction"]["hex"]]], label=LABEL)
    source_ptr = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter_ptr = image.method_pointer_va(image.metadata.methods[methods[1]])
    windows = route["codeWindows"]
    if (
        route["methods"][0][1] != wrapper.name
        or not route["methods"][1][1].startswith(wrapper.name + "+")
        or windows[0]["startRva"] != source_ptr - base
        or windows[0]["endRva"] != extents[source_ptr] - base
        or windows[-1]["startRva"] != formatter_ptr - base
        or windows[-1]["endRva"] != extents[formatter_ptr] - base
        or [(item["startRva"], item["endRva"]) for item in windows[1:-1]]
        != [(va-base, va+length-base) for va, length in fragments.get(source_ptr, ())]
    ):
        raise ValueError(f"{LABEL}.native:method-windows=ActionHeader:{tag:#x}")
    read_rows = route["orderedSourceReads"]
    previous = route["memberCountInstruction"]["rva"]
    for read in read_rows:
        site = read["sourceCallsiteRva"]
        code = image.pe.bytes_at_va(base + site, 5)
        target = site + 5 + struct.unpack_from("<i", code, 1)[0]
        if (
            site <= previous or not windows[0]["startRva"] <= site < windows[0]["endRva"]
            or code[0] != 0xE8 or code.hex().upper() != read["sourceCallHex"]
            or target != read["sourceTargetRva"]
            or target != route["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read=ActionHeader:{tag:#x}:{read['memberIndex']}")
        previous = site
    setter = route["inheritedValidateSetter"]
    inherited = wrapper.members[13]
    method = image.metadata.methods[inherited.method_index]
    callsite = setter["callsiteRva"]
    call = image.pe.bytes_at_va(base + callsite, 5)
    target = callsite + 5 + struct.unpack_from("<i", call, 1)[0]
    if (
        inherited.method_index != setter["methodIndex"]
        or inherited.declaring_wrapper != setter["declaringWrapper"]
        or image.type_name(method.declaring_type) != inherited.declaring_wrapper
        or image.metadata.string(method.name_index) != setter["setterName"] == "set____validate__"
        or not read_rows[-1]["sourceCallsiteRva"] < callsite < windows[0]["endRva"]
        or call[0] != 0xE8 or call.hex().upper() != setter["callHex"]
        or target != setter["targetRva"]
        or image.method_pointer_va(method) != base + target
    ):
        raise ValueError(f"{LABEL}.native:inherited-setter=ActionHeader:{tag:#x}")
    context = route["nestedContexts"][0]
    if context.get("memberIndex") != 13 or not read_rows[12]["sourceCallsiteRva"] < context["instructionRva"] < read_rows[13]["sourceCallsiteRva"]:
        raise ValueError(f"{LABEL}.native:validate-context-order=ActionHeader:{tag:#x}")
    _validate_context(image, context, "System.Boolean")
    return {"family": "ActionHeader", "tag": tag, "wrapperName": wrapper.name,
            "sourceReadCount": len(read_rows), "sourceFragmentCount": len(fragments.get(source_ptr, ()))}


@lru_cache(maxsize=1)
def load_current_header_native() -> tuple[dict[int, dict[str, Any]] | None, dict[str, Any]]:
    """Return selected rows only after full installed-native validation."""
    try:
        contract = _read_contract()
        expected = contract["nativeInputs"]
        gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
        if gate.status != "validated":
            return None, {"status": gate.status, "validator": LABEL, "failedCheck": "installed-native-inputs", "detail": gate.detail}
        unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unityplayer.is_file() or sha256_file(unityplayer).upper() != expected["UnityPlayer.dll"].upper():
            return None, {"status": "mismatched", "validator": LABEL, "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll is missing or has a different SHA256"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        wrappers = derive_from_image(image)
        switch = read_union_switch(image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers)
        extents = image.mapper.pdata_function_extents(image.pe)
        fragments = BodyIndex(image).chained_fragments
        validated = [_validate_route(image, route, switch, wrappers, fragments, extents) for route in contract["routes"]]
        routes = {route["tag"]: route for route in contract["routes"]}
        return routes, {"status": "validated", "validator": LABEL, "routes": validated,
                        "nativeInputs": expected}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        return None, {"status": "validation_failed", "validator": LABEL,
                      "failedCheck": "selected-route-contract-or-native", "detail": str(exc)}


def main() -> int:
    _routes, audit = load_current_header_native()
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
