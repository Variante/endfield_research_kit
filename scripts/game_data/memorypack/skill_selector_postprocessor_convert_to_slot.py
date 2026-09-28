"""Selected zero-member ConvertToSlot postprocessor nested in SkillData.

The selected ``SelectorPostProcessor`` switch dispatches physical tag ``0x03``
to ``Selector+ConvertToSlot+Data``.  Its generated wrapper has no setters and
its selected ``Deserialize`` reads one wrapper header with zero members; ``FF``
is a separate null-wrapper state, which ``decode_convert_to_slot_postprocessor``
keeps distinct.  The reviewed contract pins the switch target, registered
wrapper type, formatter and reader bodies, source header call, zero-member
branch and the installed native inputs (``exact`` for that stored shape).

The finite Skill reader applies this shape only at reached postprocessor
children.  A SkillData file is still exact only when the enclosing timeline,
fields through 42, the selected terminal and EOF all close; a file that
advances past this child to a later unsupported action tag keeps its earlier
prefix partial.  The static stored type does not establish runtime target
conversion.
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


LABEL = "skillSelectorPostprocessorConvertToSlot"
CONTRACT_PATH = CONTRACTS_DIR / "skill_selector_postprocessor_convert_to_slot_native.json"
TAG = 3
TYPE_NAME = "Beyond.Gameplay.Core.Selector+ConvertToSlot+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_ConvertToSlot_DataForMemoryPack"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-selector-postprocessor-convert-to-slot-native-contract.v1",
        status="exact-current-build", label=LABEL,
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
    rows = catalog.get("families", {}).get("SelectorPostProcessor", ())
    switch = catalog.get("switches", {}).get("SelectorPostProcessor", {})
    route = rows[TAG] if len(rows) > TAG else {}
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != 0
        or switch.get("entryCount") != len(rows)
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:catalog-shape")
    return catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected postprocessor switch and source byte reader."""
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
        int(catalog["switches"]["SelectorPostProcessor"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    selected = image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    branch = image.window_bytes(contract["dispatcher"]["routeWindow"])
    load = branch.find(b"\x48\x8b\x15")
    if load < 0 or branch[:6] != b"\x48\x8b\x0f\x48\x85\xc9":
        raise ValueError(f"{LABEL}.native:route-shape")
    usage_cell = (
        image.pe.image_base + contract["dispatcher"]["switchTargetRva"]
        + load + 7 + struct.unpack_from("<i", branch, load + 3)[0]
    )
    if usage_cell != selected["usageCell"]:
        raise ValueError(f"{LABEL}.native:route-usage-cell")
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    header = contract["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != []:
        raise ValueError(f"{LABEL}.native:unexpected-setter")
    source = contract["sourceHeaderRead"]
    start, end = (contract["codeWindows"][1][key] for key in ("startRva", "endRva"))
    rva = source["sourceCallsiteRva"]
    if not start <= rva < header["rva"] < end:
        raise ValueError(f"{LABEL}.native:header-order")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != source["sourceCallHex"]:
        raise ValueError(f"{LABEL}.native:header-call")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target != source["sourceTargetRva"]:
        raise ValueError(f"{LABEL}.native:header-target")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "serializedMemberCount": 0,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_convert_to_slot_postprocessor(reader: Reader) -> None:
    """Consume a reached tag-3 postprocessor, retaining a distinct FF state."""
    _contract()
    _catalog()
    if reader.peek() != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "nested-postprocessor-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-nested-postprocessor-wrapper")
    else:
        reader.header(0)
    reader.records.append({
        "start": start, "end": reader.pos,
        "kind": "anonymous-selector-postprocessor-profile",
    })
