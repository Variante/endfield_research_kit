"""Authenticate one stored CheckIsInFacLinkingMode task-map condition.

The contract selects one GameCondition reader and its source cursor. It proves
the serialized fields and LinkType IDs, not runtime facility-link evaluation.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-check-fac-linking-mode-native.v1"
LABEL = "levelscriptCheckFacLinkingModeNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_check_fac_linking_mode_native.json"
_FIELDS = [
    ["scopeMask", "enum32"], ["uniqueId", "string"],
    ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
    ["isInFacLinkingMode", "Param<bool>"],
    ["targetFacLinkingModeType", "Param<LinkType>"],
]
_NATIVE_TYPES = {
    "Beyond.GEnums.ScopeName": "enum32", "string": "string", "bool": "bool",
    "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.GameMech.LinkWireBrain+LinkType>": "Param<LinkType>",
}
_ELEMENTS = {4: ("bool", 2),
             5: ("Beyond.Gameplay.Core.GameMech.LinkWireBrain+LinkType", 17)}


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route") or {}
    fields = route.get("fields") or []
    reads = route.get("orderedReads") or []
    contexts = route.get("paramContexts") or []
    enum = data.get("enumAlias") or {}
    if (
        data.get("schema") != SCHEMA or data.get("status") != "exact-current-build"
        or set(data.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or route.get("family") != "GameCondition" or route.get("tag") != 0xC1
        or route.get("typeName") != "Beyond.Gameplay.Conditions.CheckIsInFacLinkingMode"
        or route.get("serializedMemberCount") != 6 or route.get("inheritedMemberCount") != 4
        or fields != _FIELDS
        or [[name, _NATIVE_TYPES.get(kind)] for name, kind in route.get("nativeDeclaredTypes") or []]
        != fields
        or [row.get("memberIndex") for row in reads] != list(range(6))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or [row.get("memberIndex") for row in contexts] != [4, 5]
        or [(row.get("elementTypeName"), row.get("elementTypeKind")) for row in contexts]
        != [_ELEMENTS[4], _ELEMENTS[5]]
        or len(route.get("methods") or []) != 2 or len(route.get("codeWindows") or []) != 2
        or len(route.get("sourceReceipts") or []) != 1
        or any(len(row) != 5 for row in route["sourceReceipts"])
        or enum.get("typeName") != _ELEMENTS[5][0] or enum.get("underlyingType") != "int"
        or enum.get("width") != 4
        or [(row.get("id"), row.get("name")) for row in enum.get("members") or []]
        != [(0, "None"), (1, "PowerPole"), (2, "Udpipe")]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return data


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], expected: tuple[str, int]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:context-index={context['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16) + spec_index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    if (
        list(spec) != context["methodSpec"]
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
    ):
        raise ValueError(f"{LABEL}.native:context-reader={context['memberIndex']}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:context-arity={context['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:context-argument={context['memberIndex']}")
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(pointer, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:context-param={context['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    row = child.as_dict()
    row["arguments"] = list(row["arguments"])
    if len(child.arguments) != 1 or row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:context-instantiation={context['memberIndex']}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    definition = struct.unpack_from("<Q", element)[0] if expected[1] == 17 else None
    if (
        element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != expected[1]
        or context["elementTypeName"] != expected[0]
        or context["elementTypeDefinition"] != definition
        or protocol.runtime_type_name(image.pe, image.metadata, child.arguments[0].type_pointer_va)
        != expected[0]
        or (definition is not None and image.type_name(definition) != expected[0])
    ):
        raise ValueError(f"{LABEL}.native:context-element={context['memberIndex']}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route, dispatcher = contract["route"], contract["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_GameConditionForMemoryPack", wrappers=wrappers)
    if (
        switch["entryCount"] != dispatcher["entryCount"]
        or int(switch["tableVa"], 16) != base + dispatcher["tableRva"]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher")
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:dispatcher-table")
    entry = switch["entries"][route["tag"]]
    wrapper = wrappers[route["typeDefinition"]]
    if (
        struct.unpack_from("<I", table, route["tag"] * 4)[0] != route["switchTargetRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or int(entry["targetVa"], 16) != base + route["switchTargetRva"]
        or int(entry["bodyVa"], 16) != base + route["bodyRva"]
        or int(entry["usageCellVa"], 16) != base + route["usageCellRva"]
        or image.pe.bytes_at_va(base + route["usageCellRva"], 8).hex().upper()
        != route["usageRawHex"].upper()
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != 4
        or [[m.name.lstrip("_"), m.declared_type] for m in wrapper.members]
        != route["nativeDeclaredTypes"]
        or [[m.name.lstrip("_"), _NATIVE_TYPES.get(m.declared_type)] for m in wrapper.members]
        != route["fields"]
        or wrapper.members[0].underlying_kind != "scalar32"
    ):
        raise ValueError(f"{LABEL}.native:selected-wrapper")
    enum = contract["enumAlias"]
    owner = next((row for row in image.metadata.types
                  if image.metadata.type_full_name(row) == enum["typeName"]), None)
    if owner is None:
        raise ValueError(f"{LABEL}.native:enum-owner")
    backing = [row for row in image.metadata.fields_for(owner)
               if image.metadata.string(row.name_index) == "value__"]
    if len(backing) != 1:
        raise ValueError(f"{LABEL}.native:enum-backing-field")
    index = backing[0].type_index
    if not 0 <= index < image.registration["typesCount"]:
        raise ValueError(f"{LABEL}.native:enum-backing-index")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    if (
        protocol.runtime_type_name(image.pe, image.metadata, pointer) != enum["underlyingType"]
        or protocol.native_enum_members(image.metadata, protocol.field_defaults(image.metadata),
                                        image.pe, image.registration, enum["typeName"])
        != enum["members"]
    ):
        raise ValueError(f"{LABEL}.native:enum-members")
    methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
    body = BodyIndex(image)
    windows = route["codeWindows"]
    expected_windows = []
    for method_index in methods:
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if body.chained_fragments.get(pointer):
            raise ValueError(f"{LABEL}.native:unexpected-reader-fragment")
        expected_windows.append((pointer-base, body.extents[pointer]-base))
    if [(row["startRva"], row["endRva"]) for row in windows] != expected_windows:
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    image.check_windows(windows, label=LABEL)
    tail = route["formatterTailJump"]
    if (
        tail["targetRva"] != windows[0]["startRva"]
        or not windows[1]["startRva"] <= tail["instructionRva"] < windows[1]["endRva"]
        or _call_target_jump(image, tail["instructionRva"], tail["instructionHex"])
        != windows[0]["startRva"]
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = route["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if bytes.fromhex(count["hex"]) != b"\x80\x7c\x24\x38\x06":
        raise ValueError(f"{LABEL}.native:member-count")
    previous = count["rva"]
    reads = route["orderedReads"]
    for read in reads:
        member = wrapper.members[read["memberIndex"]]
        method = image.metadata.methods[member.method_index]
        if (
            not previous < read["readCallRva"] < read["setterCallRva"] < windows[0]["endRva"]
            or _call_target(image, read["readCallRva"], read["readCallHex"])
            != read["readTargetRva"]
            or _call_target(image, read["setterCallRva"], read["setterCallHex"])
            != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(method.name_index) != read["setterName"]
            or image.method_pointer_va(method) != base + read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={read['memberIndex']}")
        previous = read["setterCallRva"]
    for context in route["paramContexts"]:
        index = context["memberIndex"]
        if not reads[index-1]["setterCallRva"] < context["instructionRva"] < reads[index]["readCallRva"]:
            raise ValueError(f"{LABEL}.native:context-order={index}")
        _validate_context(image, context, _ELEMENTS[index])


def _call_target_jump(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE9 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:jump={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger_path: Path,
                      summary_path: Path) -> int:
    summary = json.loads(summary_path.read_bytes())
    output = summary.get("provenance", {}).get("outputFiles", {})
    if (
        summary.get("status") != "complete" or output.get("length") != ledger_path.stat().st_size
        or output.get("sha256", "").upper() != sha256_file(ledger_path).upper()
    ):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    route = contract["route"]
    path, digest, start, end, span_digest = route["sourceReceipts"][0]
    ledger_row = None
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData" and row.get("exportRelativePath") == path:
                ledger_row = row
                break
    data = (export_root / path).read_bytes()
    actual = hashlib.sha256(data).hexdigest().upper()
    if actual != digest.upper() or (ledger_row or {}).get("logicalSha256", "").upper() != actual or (ledger_row or {}).get("length") != len(data):
        raise ValueError(f"{LABEL}.source:source-or-ledger-hash={path}:expected={digest}:actual={actual}")
    if not 0 <= start < end <= len(data) or data[start:start+2] != bytes((route["tag"],6)):
        raise ValueError(f"{LABEL}.source:union-prefix={path}@{start}")
    if hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper():
        raise ValueError(f"{LABEL}.source:span-hash={path}@{start}")
    from scripts.game_data.codecs.levelscript.taskmap_fac_linking_condition import (
        decode_fac_linking_mode_condition,
    )
    decoded = decode_fac_linking_mode_condition(data, start, len(data), route, contract["enumAlias"])
    if decoded is None or decoded[1] != end:
        raise ValueError(f"{LABEL}.source:cursor={path}@{start}:expected={end}")
    return 1


@lru_cache(maxsize=4)
def validate_check_fac_linking_mode_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on build drift and optionally authenticate one source span."""
    try:
        contract = _contract(Path(contract_path))
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent/"GameAssembly.dll" if root else None,
            metadata=root/"il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        if gate.status != "validated":
            return {"status": gate.status, "validator": LABEL,
                    "failedGate": "installed_native_inputs", "detail": gate.detail}
        unity = gate.gameassembly.parent/"UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "validator": LABEL,
                    "failedGate": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll missing or different"}
        _validate_native(open_native_image(gate.gameassembly, gate.metadata), contract)
        count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            count = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "validator": LABEL, "evidenceBoundary": "exact",
                "route": contract["route"], "enumAlias": contract["enumAlias"],
                "sourceReceiptCount": count}
    except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
        detail = str(error)
        return {"status": "validation_failed", "validator": LABEL,
                "failedGate": detail.split(":",1)[0], "detail": detail[:500]}


@lru_cache(maxsize=1)
def validated_check_fac_linking_mode_route() -> tuple[dict[str, Any], dict[str, Any]] | None:
    audit = validate_check_fac_linking_mode_native_contract()
    if audit["status"] != "validated":
        return None
    return audit["route"], audit["enumAlias"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    audit = validate_check_fac_linking_mode_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps({key:value for key,value in audit.items() if key not in {"route","enumAlias"}},indent=2))
    return 0 if audit["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
