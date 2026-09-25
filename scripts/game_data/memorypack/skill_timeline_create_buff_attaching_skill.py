"""Selected-build SkillData CreateBuffAttachingSkill 0x0093 framing.

The wrapper inherits CreateBuffAction's stored members. Its name does not
establish whether or when a buff is attached to a skill at runtime.
"""
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


LABEL = "skillTimelineCreateBuffAttachingSkill"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_create_buff_attaching_skill_native.json"
TAG = 0x0093
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffAttachingSkill_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.CreateBuffAttachingSkill+Data"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-create-buff-attaching-skill-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("typeName") != WRAPPER_NAME
        or contract.get("wrapper", {}).get("parentTypeName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffAction_DataForMemoryPack"
        or contract.get("sourceContract") != "buff_93_native.json"
        or contract.get("inheritedSourceContract") != "buff_92_native.json"
        or contract.get("inheritedFieldContract") != "skill_timeline_create_buff_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("serializedMemberCount") != 19
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xfe\x13"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    inherited = json.loads((CONTRACTS_DIR / contract["inheritedSourceContract"]).read_bytes())
    fields = json.loads((CONTRACTS_DIR / contract["inheritedFieldContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    read_order = source.get("anonymousReadOrder", {}).get("member19")
    if (
        source.get("schemaVersion") != 1
        or inherited.get("schemaVersion") != 1
        or read_order != inherited.get("anonymousReadOrder", {}).get("member19")
        or not isinstance(read_order, list)
        or len(read_order) != contract["serializedMemberCount"]
        or len(source.get("nestedContexts", [])) != 7
        or fields.get("wrapper", {}).get("typeDefinition")
        != contract["wrapper"]["parentTypeDefinition"]
        or fields.get("wrapper", {}).get("serializedMemberCount") != len(read_order)
        or len(fields.get("wrapper", {}).get("selectedReadOrder", [])) != len(read_order) - 4
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(read_order)
        or catalog.get("switches", {}).get("AbilityActionData", {}).get("entryCount")
        != len(catalog["families"]["AbilityActionData"])
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return source, inherited, fields, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the derived route and its reviewed 19-member source."""
    contract = _contract()
    source, inherited, fields, catalog = _dependencies()
    expected = contract["nativeInputs"]
    if (
        expected["GameAssembly.dll"] != catalog["nativeInputs"]["gameAssemblySha256"]
        or expected["global-metadata.dat"] != catalog["nativeInputs"]["metadataSha256"]
        or expected != fields["nativeInputs"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-inputs")
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
        int(catalog["switches"]["AbilityActionData"]["tableVa"], 16)
        != image.pe.image_base + contract["dispatcher"]["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeIndex", label=LABEL):
        raise ValueError(f"{LABEL}.native:unexpected-derived-setters")
    parent = image.metadata.types[contract["wrapper"]["parentTypeDefinition"]]
    if image.setter_methods(parent, parameter="typeIndex", label=LABEL) != [
        row[:3] for row in fields["wrapper"]["setterMethods"]
    ]:
        raise ValueError(f"{LABEL}.native:inherited-setters")
    image.check_instruction_windows([
        [contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]
    ], label=LABEL)
    source_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["sourceContract"],
    )
    inherited_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["inheritedSourceContract"],
    )
    if (
        source_audit["anonymousReadOrder"]["member19"]
        != inherited_audit["anonymousReadOrder"]["member19"]
        or source["methods"][1][1] != WRAPPER_NAME
        or source["methods"][1][2] != "Deserialize"
    ):
        raise ValueError(f"{LABEL}.native:source-profile")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": TAG, "sourceReadCount": len(source_audit["anonymousReadOrder"]["member19"]),
        "nestedContextCount": len(source["nestedContexts"]),
        "inheritedSetterCount": len(fields["wrapper"]["setterMethods"]),
    }


def decode_create_buff_attaching_skill_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume the selected derived action with the bounded BuffData grammar."""
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    Reader._action(reader, depth, tag, width)
