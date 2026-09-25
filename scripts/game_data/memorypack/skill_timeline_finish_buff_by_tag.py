"""Selected-build SkillData FinishBuffByTag action 0x00B5 storage framing.

The route and twelve-member source order reuse the reviewed Buff frontier
for the same AbilityActionData union. This consumes stored bytes only.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from scripts.game_data.buff_frontiers_native import load_rows
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineFinishBuffByTag"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_finish_buff_by_tag_native.json"
TAG = 0x00B5
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_FinishBuffByTag_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.FinishBuffByTag+Data"
READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32", "target-settings",
    "target-settings", "bool", "blackboard-double", "target-settings",
    "bool", "bool", "tag-query",
)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-finish-buff-by-tag-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("sourceContract") != "buff_frontier9.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or contract.get("unionTag") != TAG
        or contract.get("wrapperName") != WRAPPER_NAME
        or contract.get("wrappedType") != TYPE_NAME
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    rows = [row for row in source.get("actions", ()) if row.get("unionTag") == TAG]
    routes = catalog.get("families", {}).get("AbilityActionData", ())
    if (
        source.get("schema") != "endfield.buff-frontier9-native-contract.v1"
        or source.get("status") != "exact-current-build"
        or source.get("nativeInputs") != contract.get("nativeInputs")
        or len(rows) != 1
        or rows[0].get("wrapperName") != WRAPPER_NAME
        or rows[0].get("actualTypeName") != TYPE_NAME
        or rows[0].get("serializedMemberCount") != len(READ_KINDS)
        or tuple(rows[0].get("readOrder", ())) != READ_KINDS
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs", {}).get("gameAssemblySha256")
        != contract["nativeInputs"]["GameAssembly.dll"]
        or catalog.get("nativeInputs", {}).get("metadataSha256")
        != contract["nativeInputs"]["global-metadata.dat"]
        or len(routes) <= TAG
        or routes[TAG].get("tag") != TAG
        or routes[TAG].get("wrapperName") != WRAPPER_NAME
        or routes[TAG].get("wrappedType") != TYPE_NAME
        or routes[TAG].get("memberCount") != len(READ_KINDS)
        or catalog.get("switches", {}).get("AbilityActionData", {}).get("entryCount") != len(routes)
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return rows[0], catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the source frontier and selected SkillData union join."""
    source, _catalog = _dependencies()
    rows, audit = load_rows("frontier9")
    if audit.get("status") != "validated" or rows.get(TAG) != source:
        raise ValueError(f"{LABEL}.native:{audit.get('status')}:{audit.get('validationFailures')}")
    return {
        "status": "validated",
        "nativeInputs": _contract()["nativeInputs"],
        "unionTag": TAG,
        "sourceReadCount": len(READ_KINDS),
        "sourceFrontierValidatedRows": audit["validatedRows"],
    }


def decode_finish_buff_by_tag_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached finite action and bounded nested profiles."""
    del depth
    _contract()
    _dependencies()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    reader.take(1, "FinishBuffByTag.member0.byte")
    for index in range(1, 4):
        reader.take(4, f"FinishBuffByTag.member{index}.raw4")
    reader.target_profile()
    reader.target_profile()
    reader.take(1, "FinishBuffByTag.member6.byte")
    reader.scalar_payload()
    reader.target_profile()
    reader.take(1, "FinishBuffByTag.member9.byte")
    reader.take(1, "FinishBuffByTag.member10.byte")
    reader.query_profile()
