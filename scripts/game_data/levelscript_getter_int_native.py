"""Fail-closed native receipt for the reached LevelScript GetterInt union.

This proves stored bytes and their selected reader. It does not infer when the
getter executes or what gameplay state supplies its value.
"""

from __future__ import annotations

import hashlib
import gzip
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_two_routes_native import _validate_context
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


LABEL = "levelscriptGetterIntNative"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_getter_int_native.json"
SCHEMA = "endfield.levelscript-getter-int-native-contract.v1"


def _contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_bytes())
    route = contract.get("route") or {}
    if (
        contract.get("schema") != SCHEMA
        or contract.get("status") != "exact-current-build"
        or contract.get("evidenceBoundary") != "exact"
        or route.get("nativeFamily") != "PureGetter"
        or route.get("codecFamily") != "GetterBase"
        or not isinstance(route.get("tag"), int) or not 0xFA <= route["tag"] <= 0xFFFF
        or not isinstance(route.get("serializedMemberCount"), int)
        or not isinstance(route.get("fields"), list)
        or len(route["fields"]) != route["serializedMemberCount"]
        or [read.get("memberIndex") for read in route.get("orderedSourceReads", [])]
        != list(range(route["serializedMemberCount"]))
        or [[read.get("fieldName"), read.get("readKind")] for read in route["orderedSourceReads"]] != route["fields"]
        or len(route.get("sourceWindows", [])) < 2
        or len(route.get("methods", [])) != 2
        or route.get("nestedContext", {}).get("memberIndex") != route["serializedMemberCount"] - 1
        or route.get("inheritedValueSetter", {}).get("memberIndex") != route["serializedMemberCount"] - 1
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _rva_call(image: Any, row: dict[str, Any]) -> None:
    site = row["callsiteRva"]
    code = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    target = site + 5 + struct.unpack_from("<i", code, 1)[0]
    if code[0] != 0xE8 or code.hex().upper() != row["callHex"] or target != row["targetRva"]:
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")


def _validate_native(image: Any, route: dict[str, Any]) -> dict[str, Any]:
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_PureGetterForMemoryPack", wrappers=wrappers,
    )
    branch = route["dispatcher"]
    table = image.pe.bytes_at_va(base + branch["switchTableRva"], branch["switchEntryCount"] * 4)
    target_rva = struct.unpack_from("<I", table, route["tag"] * 4)[0]
    entry = switch["entries"][route["tag"]]
    if (
        int(switch["tableVa"], 16) != base + branch["switchTableRva"]
        or switch["entryCount"] != branch["switchEntryCount"]
        or hashlib.sha256(table).hexdigest().upper() != branch["switchTableSha256"]
        or target_rva != branch["switchTargetRva"] == int(entry["targetVa"], 16) - base
        or branch["bodyRva"] != int(entry["bodyVa"], 16) - base
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != branch["wrapperTypeDefinition"]
        or entry["registeredTypeIndex"] != branch["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:selected-dispatcher")
    image.check_windows([branch["branchWindow"]], label=LABEL)
    load_rva = branch["typeLoadRva"]
    instruction = image.pe.bytes_at_va(base + load_rva, 7)
    cell = base + load_rva + 7 + struct.unpack_from("<i", instruction, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
    )
    type_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(type_pointer, 16))[0]
    if (
        instruction[:3] != b"\x48\x8b\x15"
        or instruction.hex().upper() != branch["typeLoadHex"]
        or cell - base != branch["usageCellRva"]
        or usage.hex().upper() != branch["usageRawHex"]
        or index != branch["registeredTypeIndex"]
        or definition != branch["wrapperTypeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    parent = wrappers.get(wrapper.parent_type_definition)
    normalized_kinds = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.Param`1<int>": "Param<int>",
    }
    actual_fields = [
        [member.name.lstrip("_"), normalized_kinds.get(member.declared_type)]
        for member in wrapper.members
    ]
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or wrapper.own_members
        or parent is None or parent.name != route["parentWrapperName"]
        or len(parent.own_members) != 1
        or len(wrapper.members) != route["serializedMemberCount"]
        or actual_fields != route["fields"]
        or normalized_kinds.get(parent.own_members[0].declared_type) != route["fields"][-1][1]
    ):
        raise ValueError(f"{LABEL}.native:inherited-wrapper-members")
    methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
    if route["methods"][0][1] != wrapper.name or not route["methods"][1][1].startswith(wrapper.name + "+"):
        raise ValueError(f"{LABEL}.native:method-owners")
    source_ptr = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter_ptr = image.method_pointer_va(image.metadata.methods[methods[1]])
    extents = image.mapper.pdata_function_extents(image.pe)
    fragments = BodyIndex(image).chained_fragments.get(source_ptr, ())
    expected_windows = [
        (source_ptr - base, extents[source_ptr] - base),
        *((va - base, va + length - base) for va, length in fragments),
    ]
    windows = route["sourceWindows"]
    if (
        [(win["startRva"], win["endRva"]) for win in windows] != expected_windows
        or route["formatterWindow"]["startRva"] != formatter_ptr - base
        or route["formatterWindow"]["endRva"] != extents[formatter_ptr] - base
    ):
        raise ValueError(f"{LABEL}.native:complete-body-windows")
    image.check_windows([*windows, route["formatterWindow"]], label=LABEL)
    tail = route["formatterTailJump"]
    tail_code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
    tail_target = tail["instructionRva"] + 5 + struct.unpack_from("<i", tail_code, 1)[0]
    if (
        tail_code[0] != 0xE9
        or tail_code.hex().upper() != tail["instructionHex"]
        or tail_target != tail["targetRva"] == source_ptr - base
        or not route["formatterWindow"]["startRva"] <= tail["instructionRva"] < route["formatterWindow"]["endRva"]
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = route["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if count["hex"].upper() != f"4080FE{route['serializedMemberCount']:02X}":
        raise ValueError(f"{LABEL}.native:member-count-check")
    previous = count["rva"]
    for read in route["orderedSourceReads"]:
        site = read["callsiteRva"]
        if (
            site <= previous
            or not any(win["startRva"] <= site < win["endRva"] for win in windows)
            or read["targetRva"] != route["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read={read['memberIndex']}")
        _rva_call(image, read)
        previous = site
    setter = route["inheritedValueSetter"]
    own = parent.own_members[0]
    method = image.metadata.methods[own.method_index]
    if (
        own.method_index != setter["methodIndex"]
        or own.declaring_wrapper != setter["declaringWrapper"]
        or image.metadata.string(method.name_index) != setter["setterName"]
        or setter["setterName"] != f"set____{route['fields'][-1][0]}__"
        or image.method_pointer_va(method) != base + setter["targetRva"]
        or setter["callsiteRva"] <= previous
        or not any(win["startRva"] <= setter["callsiteRva"] < win["endRva"] for win in windows)
    ):
        raise ValueError(f"{LABEL}.native:inherited-value-setter")
    _rva_call(image, setter)
    context = route["nestedContext"]
    if not route["orderedSourceReads"][-2]["callsiteRva"] < context["instructionRva"] < route["orderedSourceReads"][-1]["callsiteRva"]:
        raise ValueError(f"{LABEL}.native:param-context-order")
    _validate_context(image, context, "System.Int32")
    return {"family": "GetterBase", "tag": route["tag"], "wrapperName": wrapper.name,
            "sourceReadCount": len(route["orderedSourceReads"]), "sourceFragmentCount": len(fragments)}


def validate_source_receipt(
    *, export_root: Path | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Replay the selected source hash and exact wide-tag span when requested."""
    contract = _contract()
    receipt = contract["sourceReceipt"]
    root = Path(export_root) if export_root is not None else Path("export_full/game/Json")
    try:
        data = (root / receipt["path"]).read_bytes()
        start, end = receipt["unionOffset"], receipt["unionEndOffset"]
        tag_prefix = b"\xfa" + contract["route"]["tag"].to_bytes(2, "little")
        member_count = contract["route"]["serializedMemberCount"]
        if (
            len(data) != receipt["sourceLength"]
            or hashlib.sha256(data).hexdigest().upper() != receipt["sourceSha256"]
            or not 0 <= start < end <= len(data)
            or data[start:start+4] != tag_prefix + bytes((member_count,))
            or hashlib.sha256(data[start:end]).hexdigest().upper() != receipt["unionSpanSha256"]
        ):
            raise ValueError("source length, hash, tag, or span differs")
        if ledger_path is not None:
            with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
                rows = [row for line in stream if receipt["path"] in line
                        if (row := json.loads(line)).get("exportRelativePath") == receipt["path"]]
            if len(rows) != 1 or rows[0].get("logicalSha256") != receipt["sourceSha256"]:
                raise ValueError("current JsonData ledger source hash differs")
    except (OSError, TypeError, KeyError, ValueError) as exc:
        return {"status": "validation_failed", "failedCheck": "selected-source-receipt",
                "sourcePath": receipt.get("path"), "detail": str(exc)}
    return {"status": "validated", "sourcePath": receipt["path"],
            "unionOffset": start, "unionEndOffset": end}


@lru_cache(maxsize=1)
def load_current_getter_int_native() -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return the selected route only after all installed native checks pass."""
    try:
        contract = _contract()
        expected = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
        )
        if gate.status != "validated":
            return None, {"status": gate.status, "validator": LABEL,
                          "failedCheck": "installed-native-inputs", "detail": gate.detail}
        unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unityplayer.is_file() or sha256_file(unityplayer).upper() != expected["UnityPlayer.dll"].upper():
            return None, {"status": "mismatched", "validator": LABEL,
                          "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll is missing or has a different SHA256"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        validated = _validate_native(image, contract["route"])
        return contract["route"], {"status": "validated", "validator": LABEL,
                                   "route": validated, "nativeInputs": expected}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        return None, {"status": "validation_failed", "validator": LABEL,
                      "failedCheck": "selected-route-contract-or-native", "detail": str(exc)}


def main() -> int:
    route, audit = load_current_getter_int_native()
    if route is not None:
        audit["sourceReceipt"] = validate_source_receipt(
            ledger_path=Path("reports/animestudio/jsondata_current_files_latest.jsonl.gz"),
        )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" and audit.get("sourceReceipt", {}).get("status") == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
