"""Selected-build SkillData ObtainUspInNormalSkill 0x00FF storage framing.

FA FF 00 is the three-byte union tag for this action, not the one-byte FF
null sentinel. The existing Buff frontier-seven native contract authenticates
its finite six-member reader and two child profile types.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineObtainUspNormal"
TAG = 0x00FF
SOURCE_CONTRACT = "buff_frontier7.json"
SOURCE_SCHEMA = "endfield.buff-frontier7-native-contract.v1"
CATALOG_CONTRACT = "levelscript_union_tags.json"
TYPE_NAME = "Beyond.Gameplay.Core.ObtainUspInNormalSkill+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ObtainUspInNormalSkill_DataForMemoryPack"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32",
    "blackboard-double", "target-settings",
)


@lru_cache(maxsize=1)
def _route() -> dict[str, Any]:
    source = buff_frontiers_native.reviewed_contract("frontier7")
    matches = [row for row in source["actions"] if row.get("unionTag") == TAG]
    catalog = json.loads((CONTRACTS_DIR / CATALOG_CONTRACT).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("status") != "exact-current-build"
        or len(matches) != 1
        or matches[0].get("actualTypeName") != TYPE_NAME
        or matches[0].get("wrapperName") != WRAPPER_NAME
        or matches[0].get("serializedMemberCount") != len(READ_ORDER)
        or tuple(matches[0].get("readOrder", ())) != READ_ORDER
        or [row[2] for row in matches[0].get("setterMethods", ()) if row[2] != "set___instance"]
        != ["set___coefficient__", "set___source__"]
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or source["nativeInputs"]["GameAssembly.dll"]
        != catalog["nativeInputs"]["gameAssemblySha256"]
        or source["nativeInputs"]["global-metadata.dat"]
        != catalog["nativeInputs"]["metadataSha256"]
        or route.get("tag") != TAG
        or route.get("wrappedType") != TYPE_NAME
        or route.get("wrapperName") != WRAPPER_NAME
        or route.get("memberCount") != len(READ_ORDER)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
        or switch.get("base")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return matches[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the existing frontier-seven route on the installed binaries."""
    route = _route()
    rows, audit = buff_frontiers_native.load_rows("frontier7")
    if audit.get("status") != "validated" or rows.get(TAG) != route:
        raise ValueError(f"{LABEL}.native:{audit.get('status')}:{audit.get('validationFailures')}")
    return {
        "status": "validated", "sourceContract": SOURCE_CONTRACT,
        "sourceSchema": SOURCE_SCHEMA, "unionTag": TAG,
        "nativeInputs": buff_frontiers_native.reviewed_contract("frontier7")["nativeInputs"],
    }


def decode_obtain_usp_normal_action(
    reader: Reader, depth: int, tag: int, width: int,
) -> None:
    """Consume the finite action while keeping child values as stored spans."""
    del depth
    _route()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "extended-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "ObtainUspInNormalSkill.bool-byte")
    for _ in range(3):
        reader.take(4, "ObtainUspInNormalSkill.scalar32")
    reader.scalar_payload()
    reader.target_profile()
