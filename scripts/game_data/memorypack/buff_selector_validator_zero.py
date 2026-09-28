"""Selected zero-member validator children in Buff SelectorData lists."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffSelectorValidatorZero"
SCHEMA = "endfield.buff-selector-validator-zero-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_validator_zero_native.json"
FAMILY = "SelectorValidator"
TYPE_NAMES = {
    5: "Beyond.Gameplay.Core.Selector+ExcludeOwnerValidator+Data",
    9: "Beyond.Gameplay.Core.Selector+MainCharacterValidator+Data",
}
WRAPPER_NAMES = {
    5: "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_ExcludeOwnerValidator_DataForMemoryPack",
    9: "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_MainCharacterValidator_DataForMemoryPack",
}


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-selector-validator-zero-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if (contract.get("switchContract") != "skill_selector_validator_in_screen_native.json"
            or contract.get("catalogContract") != "levelscript_union_tags.json"
            or not isinstance(contract.get("sharedHeaderWindow"), dict)
            or not isinstance(contract.get("routes"), list)
            or {row.get("unionTag") for row in contract["routes"]} != set(TYPE_NAMES)):
        raise ValueError(f"{LABEL}.contract:shape")
    for row in contract["routes"]:
        tag = row["unionTag"]
        if (row.get("wrappedType") != TYPE_NAMES[tag]
                or row.get("serializedMemberCount") != 0
                or row.get("dispatcher", {}).get("unionTag") != tag
                or row["dispatcher"].get("wrapperName") != WRAPPER_NAMES[tag]
                or row.get("setterMethods") != []
                or len(row.get("methods", ())) != 2
                or [method[2] for method in row["methods"]] != ["Deserialize", "Deserialize"]
                or len(row.get("codeWindows", ())) != 2):
            raise ValueError(f"{LABEL}.contract:route-shape:{tag}")
        order = row.get("readOrder", {})
        if tag == 5:
            if (set(order) != {"headerCall", "zeroMemberTest"}
                    or bytes.fromhex(order["zeroMemberTest"][1]) != b"\x40\x84\xff"
                    or order["headerCall"][2] != contract["sharedHeaderWindow"]["startRva"]):
                raise ValueError(f"{LABEL}.contract:header-route")
        else:
            forms = {
                "sourceByteRead": b"\x0f\xb6\x30",
                "sourceAdvance": b"\x48\xff\x43\x50",
                "nullMarkerCompare": b"\x40\x80\xfe\xff",
                "zeroMemberTest": b"\x40\x84\xf6",
            }
            if set(order) != set(forms) or any(
                bytes.fromhex(order[role][1]) != shape
                for role, shape in forms.items()
            ):
                raise ValueError(f"{LABEL}.contract:inline-route")
        starts = [value[0] for value in order.values()]
        reader = row["codeWindows"][1]
        if starts != sorted(starts) or not all(
            reader["startRva"] <= start < reader["endRva"] for start in starts
        ):
            raise ValueError(f"{LABEL}.contract:reader-order:{tag}")
    return contract


def validate_current_native_contract(*, selector_native: dict[str, Any]) -> dict[str, Any]:
    """Reprove two selected switch routes and their zero-member readers."""
    if selector_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:selector-not-validated")
    contract = _contract()
    base, _digest = read_reviewed_contract(
        CONTRACTS_DIR / contract["switchContract"],
        schema="endfield.skill-selector-validator-in-screen-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    expected = contract["nativeInputs"]
    if expected != base["nativeInputs"] or expected != selector_native["nativeInputs"]:
        raise ValueError(f"{LABEL}.native:selected-inputs")
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    validator_rows = catalog.get("families", {}).get(FAMILY, ())
    switch = catalog.get("switches", {}).get(FAMILY, {})
    if (catalog.get("schema") != "endfield.levelscript-union-tags.v1"
            or catalog.get("nativeInputs", {}).get("gameAssemblySha256") != expected["GameAssembly.dll"]
            or catalog.get("nativeInputs", {}).get("metadataSha256") != expected["global-metadata.dat"]
            or len(validator_rows) != base["dispatcher"]["switchEntryCount"]
            or switch.get("base") != "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack"):
        raise ValueError(f"{LABEL}.native:catalog")
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
    image.check_windows([contract["sharedHeaderWindow"]], label=LABEL)
    registry = selector_native["_registry"]
    selector_plan = registry.plans[selector_native["selectorDefinition"]]
    validators = [row for row in selector_plan if row.name == "validatorData" and row.kind == "list"]
    if (len(validators) != 1 or validators[0].element is None
            or validators[0].element.kind != "union"):
        raise ValueError(f"{LABEL}.native:parent-validator-list")
    selected = {}
    for row in contract["routes"]:
        tag = row["unionTag"]
        catalog_row = validator_rows[tag]
        if (catalog_row.get("tag") != tag or catalog_row.get("memberCount") != 0
                or catalog_row.get("wrapperName") != WRAPPER_NAMES[tag]
                or catalog_row.get("wrappedType") != TYPE_NAMES[tag]):
            raise ValueError(f"{LABEL}.native:catalog-route:{tag}")
        dispatcher = {**base["dispatcher"], **row["dispatcher"]}
        route = image.validate_dispatcher(dispatcher, label=LABEL)
        branch = image.window_bytes(row["dispatcher"]["routeWindow"])
        type_load = branch.find(b"\x48\x8b\x15")
        if type_load < 0 or branch[:6] not in (
            b"\x48\x8b\x0f\x48\x85\xc9", b"\x48\x8b\x0e\x48\x85\xc9",
        ):
            raise ValueError(f"{LABEL}.native:route-type-load:{tag}")
        cell = (image.pe.image_base + row["dispatcher"]["switchTargetRva"]
                + type_load + 7 + struct.unpack_from("<i", branch, type_load + 3)[0])
        if cell != route["usageCell"]:
            raise ValueError(f"{LABEL}.native:route-type-cell:{tag}")
        methods = [image.validate_method_row(method, label=LABEL)
                   for method in row["methods"]]
        image.check_windows(row["codeWindows"], label=LABEL)
        image.check_instruction_windows(row["readOrder"].values(), label=LABEL)
        if tag == 5:
            rva, raw_hex, target = row["readOrder"]["headerCall"]
            raw = bytes.fromhex(raw_hex)
            if (len(raw) != 5 or raw[0] != 0xE8
                    or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target):
                raise ValueError(f"{LABEL}.native:header-call:{tag}")
        definition = row["dispatcher"]["wrapperTypeDefinition"]
        owner = image.metadata.types[definition]
        if (image.setter_methods(owner, parameter="typeName", label=LABEL) != []
                or registry.union_tag_maps.get(validators[0].element.ref, {}).get(tag) != definition
                or registry.plans.get(definition) != ()
                or registry.wrapped_names.get(definition) != TYPE_NAMES[tag]):
            raise ValueError(f"{LABEL}.native:wrapper-plan:{tag}")
        selected[tag] = {"wrappedType": TYPE_NAMES[tag], "wrapperName": WRAPPER_NAMES[tag],
                         "methodIndices": methods, "serializedMemberCount": 0}
    return {"status": "validated", "nativeInputs": expected,
            "selectedTags": selected, "evidenceBoundary": contract["evidenceBoundary"]}


def decode_zero_validator_list(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse a fixed one-entry validator list and its selected empty body."""
    if native_validation.get("status") != "validated":
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
    tag = reader.peek()
    if tag not in TYPE_NAMES or tag not in native_validation.get("selectedTags", {}):
        raise ValueError(f"{LABEL}:unsupported-tag={tag}")
    reader.take(1, "validator-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-validator-wrapper")
        status = "exact-null-wrapper"
    else:
        reader.header(0)
        status = "named-zero-member-validator-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:validator-list-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": "named-selected-validator-list-exact-span",
            "source": source, "logicalSha256": actual_sha,
            "start": start, "end": end, "count": count,
            "selectedElement": {"start": element_start, "end": reader.pos,
                                "unionTag": tag, "wrappedType": TYPE_NAMES[tag],
                                "status": status, "serializedMemberCount": 0},
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
            "runtimePredicateKnown": False, "wholeBuffDataExact": False}
