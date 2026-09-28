"""Selected CharacterTeamFinder child inside authenticated Buff selectors.

This is the reached SelectorFinder tag-2 branch only. Its generated wrapper
serializes zero members; other finder tags keep their structural boundary.
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


LABEL = "buffSelectorFinderCharacterTeam"
SCHEMA = "endfield.buff-selector-finder-character-team-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_finder_character_team_native.json"
TAG = 2
FAMILY = "SelectorFinder"
TYPE_NAME = "Beyond.Gameplay.Core.Selector+CharacterTeamFinder+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_CharacterTeamFinder_DataForMemoryPack"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-selector-finder-character-team-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if (contract.get("switchContract") != "skill_selector_finder_typhoea_native.json"
            or contract.get("catalogContract") != "levelscript_union_tags.json"
            or contract.get("serializedMemberCount") != 0
            or contract.get("dispatcher", {}).get("unionTag") != TAG
            or contract["dispatcher"].get("wrapperName") != WRAPPER_NAME
            or contract.get("setterMethods") != []
            or len(contract.get("methods", ())) != 2
            or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
            or len(contract.get("codeWindows", ())) != 2):
        raise ValueError(f"{LABEL}.contract:shape")
    instructions = contract.get("readerInstructions", {})
    if set(instructions) != {
        "sourceByteRead", "sourceAdvance", "nullMarkerCompare",
        "zeroMemberTest", "normalReturn",
    }:
        raise ValueError(f"{LABEL}.contract:instruction-roles")
    # These are instruction forms, not build addresses. The code windows and
    # method pointers bind the forms to the selected installed client.
    shapes = {
        "sourceByteRead": b"\x0f\xb6\x30",  # movzx esi, byte ptr [rax]
        "sourceAdvance": b"\x48\xff\x43\x50",  # inc qword ptr [rbx+0x50]
        "nullMarkerCompare": b"\x40\x80\xfe\xff",  # cmp sil, FF
        "zeroMemberTest": b"\x40\x84\xf6",  # test sil, sil
        "normalReturn": b"\xc3",
    }
    if any(bytes.fromhex(instructions[role][1]) != shape
           for role, shape in shapes.items()):
        raise ValueError(f"{LABEL}.contract:reader-shape")
    positions = [instructions[role][0] for role in shapes]
    window = contract["codeWindows"][1]
    if not (window["startRva"] <= positions[0] < positions[1] < positions[2]
            < positions[3] < positions[4] < window["endRva"]):
        raise ValueError(f"{LABEL}.contract:reader-order")
    return contract


def validate_current_native_contract(*, selector_native: dict[str, Any]) -> dict[str, Any]:
    """Check the native tag route, zero-member reader, and selected parent plan."""
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
            or finder_rows[TAG].get("memberCount") != 0
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
    if type_load < 0 or branch.find(b"\x48\x8b\x15", type_load + 1) >= 0:
        raise ValueError(f"{LABEL}.native:route-type-load")
    cell = (image.pe.image_base + contract["dispatcher"]["switchTargetRva"]
            + type_load + 7 + struct.unpack_from("<i", branch, type_load + 3)[0])
    if cell != route["usageCell"]:
        raise ValueError(f"{LABEL}.native:route-type-cell")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(contract["readerInstructions"].values(), label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != []:
        raise ValueError(f"{LABEL}.native:unexpected-setter")
    registry = selector_native["_registry"]
    selector_plan = registry.plans[selector_native["selectorDefinition"]]
    finders = [row for row in selector_plan if row.name == "finderData" and row.kind == "union"]
    if (len(finders) != 1
            or registry.union_tag_maps.get(finders[0].ref, {}).get(TAG)
            != contract["dispatcher"]["wrapperTypeDefinition"]
            or registry.plans.get(contract["dispatcher"]["wrapperTypeDefinition"]) != ()
            or registry.wrapped_names.get(contract["dispatcher"]["wrapperTypeDefinition"])
            != TYPE_NAME):
        raise ValueError(f"{LABEL}.native:parent-finder-plan")
    return {"status": "validated", "nativeInputs": expected, "unionTag": TAG,
            "wrapperName": WRAPPER_NAME, "wrappedType": TYPE_NAME,
            "serializedMemberCount": 0, "methodIndices": methods,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_character_team_finder_span(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Consume only a bounded tag-2 finder; any other tag or body refuses."""
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
    else:
        reader.header(0)
        status = "named-zero-member-finder-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:finder-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": status, "source": source,
            "logicalSha256": actual_sha, "start": start, "end": end,
            "unionTag": TAG, "wrappedType": TYPE_NAME,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
            "runtimeTargetSelectionKnown": False, "wholeBuffDataExact": False}
