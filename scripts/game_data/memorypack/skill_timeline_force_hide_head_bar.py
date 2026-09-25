"""Selected-build SkillData ForceHideHeadBarAction 0x00B9 storage framing."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineForceHideHeadBar"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_force_hide_head_bar_native.json"
TAG = 0x00B9
TYPE_NAME = "Beyond.Gameplay.Core.ForceHideHeadBarAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ForceHideHeadBarAction_DataForMemoryPack"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "finishByAction", "target",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "bool-byte", "TargetSettings",
)
SOURCE_READ_ORDER = ("byte", "scalar32", "scalar32", "scalar32", "byte", "target")
TARGET_READ_ORDER = (
    "member8", "byte-payload", "byte", "scalar32", "byte", "byte-payload",
    "member3", "scalar32", "scalar32", "scalar32", "byte-payload",
    "byte-payload", "scalar32",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-force-hide-head-bar-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract["dispatcher"].get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or contract.get("sourceContract") != "buff_b9_native.json"
        or contract.get("targetProfileContract") != "buff_ec_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contract.get("setterMethods"), list)
        or [row[1:] for row in contract["setterMethods"]] != [
            ["set___finishByAction__", "System.Boolean"],
            ["set___target__", "Beyond.Gameplay.Core.TargetSettings"],
        ]
        or any(len(row) != 3 or type(row[0]) is not int for row in contract["setterMethods"])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    target = json.loads((CONTRACTS_DIR / contract["targetProfileContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member6", ())) != SOURCE_READ_ORDER
        or source.get("methods", [None, None])[1][1] != WRAPPER_NAME
        or tuple(row.get("typeName") for row in source.get("nestedContexts", ()))
        != (
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Gameplay.Core.TargetSettings",
        )
        or target.get("schemaVersion") != 1
        or tuple(target.get("anonymousReadOrder", {}).get("member13", ()))
        != TARGET_READ_ORDER
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the Skill union route separately from the reused Buff reader."""
    contract = _contract()
    expected = contract["nativeInputs"]
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
    ):
        raise ValueError(f"{LABEL}.native:catalog-inputs")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
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
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    sources = {}
    for key in ("sourceContract", "targetProfileContract"):
        name = contract[key]
        audit = buff_action_read_order(
            image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly),
            contract_path=CONTRACTS_DIR / name,
        )
        sources[name] = audit["anonymousReadOrder"]
    if tuple(sources[contract["sourceContract"]].get("member6", ())) != SOURCE_READ_ORDER:
        raise ValueError(f"{LABEL}.native:source-order")
    if (
        tuple(sources[contract["targetProfileContract"]].get("member13", ()))
        != TARGET_READ_ORDER
    ):
        raise ValueError(f"{LABEL}.native:target-profile")
    return {
        "status": "validated", "nativeInputs": expected,
        "sourceReadCount": len(READ_KINDS), "sourceContracts": list(sources),
    }


def decode_force_hide_head_bar_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume only the contracted stored fields and finite TargetSettings child."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(FIELD_NAMES))
    reader.take(1, "ForceHideHeadBar.isEnable.byte")
    for field in FIELD_NAMES[1:4]:
        reader.take(4, f"ForceHideHeadBar.{field}.raw4")
    reader.take(1, "ForceHideHeadBar.finishByAction.byte")
    reader.target_profile()
