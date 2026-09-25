"""SkillData admission for the reviewed CheckSquadInFight 0x0052 reader.

The existing BuffData reader has a selected five-member source contract. This
module authenticates the current union route and reuses that finite framing.
"""
from __future__ import annotations

import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineCheckSquadInFight"
TAG = 0x0052
SOURCE_CONTRACT = "buff_52_native.json"
CATALOG_CONTRACT = "levelscript_union_tags.json"
TYPE_NAME = "Beyond.Gameplay.Core.Condition.CheckSquadInFight+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Condition_CheckSquadInFight_DataForMemoryPack"
READ_ORDER = ("byte", "scalar32", "scalar32", "scalar32", "byte")
PRIORITY_TYPE = "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"


@lru_cache(maxsize=1)
def _source() -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads((CONTRACTS_DIR / SOURCE_CONTRACT).read_text(encoding="utf-8"))
    catalog = json.loads((CONTRACTS_DIR / CATALOG_CONTRACT).read_text(encoding="utf-8"))
    actions = catalog.get("families", {}).get("AbilityActionData")
    selected = actions[TAG] if isinstance(actions, list) and len(actions) > TAG else None
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    contexts = source.get("nestedContexts", ())
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member5", ())) != READ_ORDER
        or len(contexts) != 1
        or contexts[0].get("typeName") != PRIORITY_TYPE
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(selected, dict)
        or selected.get("tag") != TAG
        or selected.get("memberCount") != len(READ_ORDER)
        or selected.get("wrappedType") != TYPE_NAME
        or selected.get("wrapperName") != WRAPPER_NAME
        or switch.get("entryCount") != len(actions)
        or switch.get("base") != "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove selected dispatch identity and the existing source contract."""
    _source_contract, catalog = _source()
    expected = catalog["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    switch = catalog["switches"]["AbilityActionData"]
    table_va = int(switch["tableVa"], 16)
    if table_va < image.pe.image_base:
        raise ValueError(f"{LABEL}.native:switch-address")
    table = image.pe.bytes_at_va(table_va, switch["entryCount"] * 4)
    target_rva = struct.unpack_from("<I", table, TAG * 4)[0]
    route_va = image.pe.image_base + target_rva
    instruction = image.pe.bytes_at_va(route_va, 7)
    if instruction[:3] != b"\x48\x8b\x15":
        raise ValueError(f"{LABEL}.native:route-instruction")
    cell_va = route_va + 7 + struct.unpack_from("<i", instruction, 3)[0]
    usage = image.pe.bytes_at_va(cell_va, 8)
    type_index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1,
        source=LABEL, offset=cell_va,
    )
    type_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(type_pointer, 16))[0]
    if image.type_name(definition) != WRAPPER_NAME:
        raise ValueError(f"{LABEL}.native:wrapper-route")
    audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / SOURCE_CONTRACT,
    )
    if audit["anonymousReadOrder"].get("member5") != list(READ_ORDER):
        raise ValueError(f"{LABEL}.native:source-read-order")
    return {
        "status": "validated", "nativeInputs": expected,
        "sourceContract": SOURCE_CONTRACT, "catalogContract": CATALOG_CONTRACT,
        "unionTag": TAG, "routeTargetRva": target_rva,
        "sourceReadCount": len(READ_ORDER), "nestedContextCount": 1,
    }


def decode_check_squad_in_fight_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Use the existing finite five-member action reader at a reached tag."""
    _source()
    if tag != TAG or width not in (1, 3):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    Reader._action(reader, depth, tag, width)
