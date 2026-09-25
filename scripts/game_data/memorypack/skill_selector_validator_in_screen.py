"""Selected-build finite SelectorValidator 0x0007 SkillData nested profile.

The native wrapper has zero serialized members. Its stored type identity does
not establish runtime in-screen evaluation or combat behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillSelectorValidatorInScreen"
CONTRACT_PATH = CONTRACTS_DIR / "skill_selector_validator_in_screen_native.json"
TAG = 0x0007
TYPE_NAME = "Beyond.Gameplay.Core.Selector+InScreenValidator+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_InScreenValidator_DataForMemoryPack"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-selector-validator-in-screen-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    route = contract.get("dispatcher", {})
    if (
        contract.get("serializedMemberCount") != 0
        or route.get("unionTag") != TAG
        or route.get("wrapperName") != WRAPPER_NAME
        or contract.get("setterMethods") != []
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x84\xff"
        or not isinstance(contract.get("sourceHeaderRead"), dict)
        or len(contract.get("methods", ())) != 2
        or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    contract = _contract()
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("SelectorValidator", [])[TAG]
    switch = catalog.get("switches", {}).get("SelectorValidator", {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != 0
        or switch.get("entryCount") != len(catalog["families"]["SelectorValidator"])
        or switch.get("base") != "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:catalog-shape")
    return catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected union route and zero-member source reader."""
    contract = _contract()
    catalog = _catalog()
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
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if (
        int(catalog["switches"]["SelectorValidator"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    header = contract["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != []:
        raise ValueError(f"{LABEL}.native:unexpected-setter")
    source = contract["sourceHeaderRead"]
    start, end = contract["codeWindows"][1]["startRva"], contract["codeWindows"][1]["endRva"]
    rva = source["sourceCallsiteRva"]
    if not start <= rva < header["rva"] < end:
        raise ValueError(f"{LABEL}.native:header-order")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != source["sourceCallHex"]:
        raise ValueError(f"{LABEL}.native:header-call")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target != source["sourceTargetRva"]:
        raise ValueError(f"{LABEL}.native:header-target")
    return {"status": "validated", "nativeInputs": expected,
            "methodIndices": methods, "serializedMemberCount": 0}


def decode_in_screen_validator(reader: Reader) -> None:
    """Consume a reached tag-7 nested validator, retaining FF as a distinct state."""
    _contract()
    _catalog()
    if reader.peek() != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "nested-validator-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-nested-validator-wrapper")
    else:
        reader.header(0)
    reader.records.append({"start": start, "end": reader.pos,
                           "kind": "anonymous-selector-validator-profile"})
