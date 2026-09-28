"""Native-gated zero-member selector children reached by SkillData.

Each route has a selected switch entry and a complete pinned wrapper reader.
The wire profile is structural; it does not assert live target behavior.

The routes are ``GuardAITargetFinder``, ``HittableObjectValidator`` and
``ConvertToPosition``, each a distinct zero-member wrapper.  Their contracts
pin the selected dispatch, wrapper identity, empty setter set, source-header
read and the complete zero-member native body.  The reader distinguishes a
null ``FF`` wrapper from a present zero-member header and still requires the
enclosing cursors to close.  The bytes do not show which target was found,
validated or converted during play.
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


ROUTES = {
    ("SelectorFinder", 6): (
        "skill_selector_finder_guard_ai_target_native.json",
        "endfield.skill-selector-finder-guard-ai-target-native-contract.v1",
        "Beyond.Gameplay.Core.Selector+GuardAITargetFinder+Data",
        "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_GuardAITargetFinder_DataForMemoryPack",
        "finder",
    ),
    ("SelectorValidator", 6): (
        "skill_selector_validator_hittable_object_native.json",
        "endfield.skill-selector-validator-hittable-object-native-contract.v1",
        "Beyond.Gameplay.Core.Selector+HittableObjectValidator+Data",
        "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_HittableObjectValidator_DataForMemoryPack",
        "validator",
    ),
    ("SelectorPostProcessor", 2): (
        "skill_selector_postprocessor_convert_to_position_native.json",
        "endfield.skill-selector-postprocessor-convert-to-position-native-contract.v1",
        "Beyond.Gameplay.Core.Selector+ConvertToPosition+Data",
        "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_ConvertToPosition_DataForMemoryPack",
        "postprocessor",
    ),
}


@lru_cache(maxsize=3)
def _reviewed_route(family: str, tag: int) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        filename, schema, wrapped_type, wrapper_name, _kind = ROUTES[(family, tag)]
    except KeyError as exc:
        raise ValueError(f"skillSelectorZeroMember.route:unsupported:{family}:{tag:#x}") from exc
    contract, _digest = read_reviewed_contract(
        CONTRACTS_DIR / filename, schema=schema, status="exact-current-build",
        label="skillSelectorZeroMember",
    )
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    rows = catalog.get("families", {}).get(family)
    switch = catalog.get("switches", {}).get(family, {})
    route = rows[tag] if isinstance(rows, list) and tag < len(rows) else None
    dispatcher = contract.get("dispatcher", {})
    if (
        contract.get("serializedMemberCount") != 0
        or contract.get("setterMethods") != []
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("memberCountInstruction", {}).get("hex") != "4084FF"
        or not isinstance(contract.get("sourceHeaderRead"), dict)
        or len(contract.get("methods", ())) != 2
        or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
        or len(contract.get("codeWindows", ())) != 2
        or dispatcher.get("unionTag") != tag
        or dispatcher.get("wrapperName") != wrapper_name
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(rows, list)
        or route is None
        or route.get("tag") != tag
        or route.get("memberCount") != 0
        or route.get("wrappedType") != wrapped_type
        or route.get("wrapperName") != wrapper_name
        or switch.get("entryCount") != len(rows)
        or int(switch.get("tableVa", "0"), 16) == 0
    ):
        raise ValueError(f"skillSelectorZeroMember.contract:source-shape:{family}:{tag:#x}")
    return contract, catalog


@lru_cache(maxsize=3)
def validate_current_native_contract(family: str, tag: int) -> dict[str, Any]:
    """Check the selected branch, wrapper and complete zero-member source body."""
    contract, catalog = _reviewed_route(family, tag)
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"skillSelectorZeroMember.native:catalog-inputs:{family}:{tag:#x}")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"skillSelectorZeroMember.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError("skillSelectorZeroMember.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    dispatcher = contract["dispatcher"]
    if int(catalog["switches"][family]["tableVa"], 16) != image.pe.image_base + dispatcher["switchTableRva"]:
        raise ValueError(f"skillSelectorZeroMember.native:switch-table:{family}:{tag:#x}")
    selected = image.validate_dispatcher(dispatcher, label="skillSelectorZeroMember")
    branch = image.window_bytes(dispatcher["routeWindow"])
    if branch[:3] not in (b"\x48\x8B\x0E", b"\x48\x8B\x0F") or branch[3:6] != b"\x48\x85\xC9" or branch[8:11] != b"\x48\x8B\x15":
        raise ValueError(f"skillSelectorZeroMember.native:route-shape:{family}:{tag:#x}")
    usage_cell = (
        image.pe.image_base + dispatcher["switchTargetRva"] + 15
        + struct.unpack_from("<i", branch, 11)[0]
    )
    if usage_cell != selected["usageCell"]:
        raise ValueError(f"skillSelectorZeroMember.native:route-usage-cell:{family}:{tag:#x}")
    methods = [image.validate_method_row(row, label="skillSelectorZeroMember") for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label="skillSelectorZeroMember")
    header = contract["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label="skillSelectorZeroMember")
    owner = image.metadata.types[dispatcher["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label="skillSelectorZeroMember") != []:
        raise ValueError(f"skillSelectorZeroMember.native:unexpected-setter:{family}:{tag:#x}")
    source = contract["sourceHeaderRead"]
    reader_window = contract["codeWindows"][1]
    rva = source["sourceCallsiteRva"]
    if not reader_window["startRva"] <= rva < header["rva"] < reader_window["endRva"]:
        raise ValueError(f"skillSelectorZeroMember.native:header-order:{family}:{tag:#x}")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != source["sourceCallHex"]:
        raise ValueError(f"skillSelectorZeroMember.native:header-call:{family}:{tag:#x}")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target != source["sourceTargetRva"]:
        raise ValueError(f"skillSelectorZeroMember.native:header-target:{family}:{tag:#x}")
    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "family": family, "tag": tag,
        "serializedMemberCount": 0, "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_zero_member_selector(reader: Reader, family: str, tag: int) -> None:
    """Consume the selected union tag and its distinct null/zero-member wrapper."""
    validate_current_native_contract(family, tag)
    _kind = ROUTES[(family, tag)][4]
    if reader.peek() != tag:
        raise ValueError(f"skillSelectorZeroMember.unionTag:unsupported:{family}:{tag:#x}")
    start = reader.pos
    reader.take(1, f"nested-{_kind}-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, f"null-nested-{_kind}-wrapper")
    else:
        reader.header(0)
    reader.records.append({
        "start": start, "end": reader.pos,
        "kind": f"anonymous-selector-{_kind}-profile",
    })
