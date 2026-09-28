"""Selected one-member OwnerSpawnedEntityFinder child inside Buff selectors.

``SelectorFinder`` tag 13 selects ``OwnerSpawnedEntityFinder``. Its
generated setter names the sole ``spawnedObjectType`` member as
``ObjectType``; the native reader checks a one-member header, takes four
source bytes and passes the result to that setter. Every reached tag-13 span
ends after exactly the tag, the header and one raw signed 32-bit member, at
the parent finder field's fixed boundary. The enum value is not interpreted
and no runtime finder behavior is claimed.
"""
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


LABEL = "buffSelectorFinderOwnerSpawned"
SCHEMA = "endfield.buff-selector-finder-owner-spawned-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_finder_owner_spawned_native.json"
TAG = 13
FAMILY = "SelectorFinder"
TYPE_NAME = "Beyond.Gameplay.Core.Selector+OwnerSpawnedEntityFinder+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_OwnerSpawnedEntityFinder_DataForMemoryPack"
MEMBER_NAME = "spawnedObjectType"
MEMBER_TYPE = "Beyond.Gameplay.Core.ObjectType"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-selector-finder-owner-spawned-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    dispatcher = contract.get("dispatcher", {})
    if (contract.get("switchContract") != "skill_selector_finder_typhoea_native.json"
            or contract.get("catalogContract") != "levelscript_union_tags.json"
            or contract.get("serializedMemberCount") != 1
            or dispatcher.get("unionTag") != TAG
            or dispatcher.get("wrapperName") != WRAPPER_NAME
            or len(contract.get("methods", ())) != 3
            or [row[2] for row in contract["methods"]]
            != ["Deserialize", "Deserialize", "set___spawnedObjectType__"]
            or contract.get("setterMethods")
            != [[contract["methods"][2][0], "set___spawnedObjectType__", MEMBER_TYPE]]
            or len(contract.get("codeWindows", ())) != 5):
        raise ValueError(f"{LABEL}.contract:shape")
    order = contract.get("readOrder", {})
    if set(order) != {"headerCall", "memberCountCompare", "valueCall",
                      "setterCall", "setterStore"}:
        raise ValueError(f"{LABEL}.contract:read-order-roles")
    roles = ("headerCall", "memberCountCompare", "valueCall", "setterCall")
    positions = [order[role][0] for role in roles]
    window = contract["codeWindows"][1]
    if not (window["startRva"] <= positions[0] < positions[1] < positions[2]
            < positions[3] < window["endRva"]):
        raise ValueError(f"{LABEL}.contract:read-order")
    if (bytes.fromhex(order["memberCountCompare"][1]) != b"\x40\x80\xff\x01"
            or bytes.fromhex(order["setterStore"][1]) != b"\x89\x58\x10"
            or not (contract["codeWindows"][2]["startRva"]
                    <= order["setterStore"][0]
                    < contract["codeWindows"][2]["endRva"])):
        raise ValueError(f"{LABEL}.contract:member-count-or-store-shape")
    helper_targets = (order["headerCall"][2], order["valueCall"][2])
    if helper_targets != (contract["codeWindows"][3]["startRva"],
                          contract["codeWindows"][4]["startRva"]):
        raise ValueError(f"{LABEL}.contract:helper-windows")
    if order["setterCall"][2] != contract["methods"][2][3]:
        raise ValueError(f"{LABEL}.contract:setter-target")
    return contract


def validate_current_native_contract(*, selector_native: dict[str, Any]) -> dict[str, Any]:
    """Reprove the selected subtype, one-member read order, and setter store."""
    if selector_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:selector-not-validated")
    contract = _contract()
    base, _digest = read_reviewed_contract(
        CONTRACTS_DIR / contract["switchContract"],
        schema="endfield.skill-selector-finder-typhoea-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    expected = contract["nativeInputs"]
    if expected != base["nativeInputs"] or expected != selector_native["nativeInputs"]:
        raise ValueError(f"{LABEL}.native:selected-inputs")
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    finder_rows = catalog.get("families", {}).get(FAMILY, ())
    switch = catalog.get("switches", {}).get(FAMILY, {})
    if (catalog.get("schema") != "endfield.levelscript-union-tags.v1"
            or catalog.get("nativeInputs", {}).get("gameAssemblySha256") != expected["GameAssembly.dll"]
            or catalog.get("nativeInputs", {}).get("metadataSha256") != expected["global-metadata.dat"]
            or len(finder_rows) != base["dispatcher"]["switchEntryCount"]
            or finder_rows[TAG].get("tag") != TAG
            or finder_rows[TAG].get("memberCount") != 1
            or finder_rows[TAG].get("wrapperName") != WRAPPER_NAME
            or finder_rows[TAG].get("wrappedType") != TYPE_NAME
            or switch.get("base") != "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Finder_DataForMemoryPack"):
        raise ValueError(f"{LABEL}.native:catalog-route")
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
    dispatcher = {**base["dispatcher"], **contract["dispatcher"]}
    route = image.validate_dispatcher(dispatcher, label=LABEL)
    branch = image.window_bytes(contract["dispatcher"]["routeWindow"])
    type_load = branch.find(b"\x48\x8b\x15")
    # The jump-table interval also includes a later shared rejoin load. The
    # first load belongs to this branch before its terminal jump.
    if type_load < 0 or not branch.startswith(b"\x48\x8b\x0e\x48\x85\xc9"):
        raise ValueError(f"{LABEL}.native:route-type-load")
    cell = (image.pe.image_base + contract["dispatcher"]["switchTargetRva"]
            + type_load + 7 + struct.unpack_from("<i", branch, type_load + 3)[0])
    if cell != route["usageCell"]:
        raise ValueError(f"{LABEL}.native:route-type-cell")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    order = contract["readOrder"]
    image.check_instruction_windows(order.values(), label=LABEL)
    for role in ("headerCall", "valueCall", "setterCall"):
        rva, raw_hex, target = order[role]
        raw = bytes.fromhex(raw_hex)
        if len(raw) != 5 or raw[0] != 0xE8:
            raise ValueError(f"{LABEL}.native:{role}-shape")
        actual_target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if actual_target != target:
            raise ValueError(f"{LABEL}.native:{role}-target")
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-plan")
    registry = selector_native["_registry"]
    selector_plan = registry.plans[selector_native["selectorDefinition"]]
    finders = [row for row in selector_plan if row.name == "finderData" and row.kind == "union"]
    definition = contract["dispatcher"]["wrapperTypeDefinition"]
    plan = registry.plans.get(definition)
    if (len(finders) != 1
            or registry.union_tag_maps.get(finders[0].ref, {}).get(TAG) != definition
            or not isinstance(plan, tuple) or len(plan) != 1
            or plan[0].name != MEMBER_NAME or plan[0].kind != "fixed"
            or plan[0].width != 4 or plan[0].scalar != "scalar32"
            or registry.wrapped_names.get(definition) != TYPE_NAME):
        raise ValueError(f"{LABEL}.native:parent-finder-plan")
    return {"status": "validated", "nativeInputs": expected, "unionTag": TAG,
            "wrapperName": WRAPPER_NAME, "wrappedType": TYPE_NAME,
            "serializedMemberCount": 1, "memberName": MEMBER_NAME,
            "memberType": MEMBER_TYPE, "methodIndices": methods,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_owner_spawned_finder_span(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Consume only a bounded tag-13 finder and name its raw enum member."""
    if native_validation.get("status") != "validated" or native_validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}:native-not-validated")
    actual_sha = hashlib.sha256(data).hexdigest().upper()
    if actual_sha != logical_sha256.upper():
        raise ValueError(f"{LABEL}:logical-source-hash")
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:source-range")
    reader = Reader(data, source, end)
    reader.pos = start
    if reader.peek() != TAG:
        raise ValueError(f"{LABEL}:unsupported-tag")
    reader.take(1, "selector-finder-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-finder-wrapper")
        status = "exact-null-wrapper"
        member = None
    else:
        reader.header(1)
        member_start = reader.pos
        raw = reader.take(4, MEMBER_NAME)
        member = {"fieldName": MEMBER_NAME, "declaredType": MEMBER_TYPE,
                  "start": member_start, "end": reader.pos,
                  "rawHex": raw.hex().upper(),
                  "storedInt32": struct.unpack("<i", raw)[0]}
        status = "named-one-member-finder-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:finder-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": status, "source": source,
            "logicalSha256": actual_sha, "start": start, "end": end,
            "unionTag": TAG, "wrappedType": TYPE_NAME,
            "namedMember": member, "wholeStoredSpanExact": True,
            "recursiveNamedSchemaExact": True, "runtimeTargetSelectionKnown": False,
            "wholeBuffDataExact": False}
