"""Diagnose new SkillData rows using separately authenticated cursor controls.

Both inputs are exact scoped current-VFS reports. A prior control report can
survive a later edit to the downstream target-set rebind verifier only when
its exact old source bytes are supplied and an AST comparison proves that no
other code changed. The joined rows exist only in memory; output is a bounded
diagnostic for the new rows, never a complete-family publication.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack import skill_corpus
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_partial_output


SCHEMA = "endfield.skillDataSparseCursorComposition.v1"
DOWNSTREAM_SOURCE = "skill_cursor_capture_target_set.py"
DOWNSTREAM_FUNCTION = "verify_capture_target_set_rebind"
SHARED_SOURCE = "skill_timeline_shared_sequence.py"
DICE_SOURCE = "skill_timeline_dice_float.py"
SHARED_CONTRACT = "skill_timeline_shared_sequence_native.json"
DICE_CONTRACT = "skill_timeline_dice_float_native.json"
SLOT_SOURCE = "skill_timeline_move_to_slot.py"
SLOT_CONTRACT = "skill_timeline_move_to_slot_native.json"
LOG_SOURCE = "skill_timeline_log_action.py"
LOG_CONTRACT = "skill_timeline_log_action_native.json"
HURT_SOURCE = "skill_timeline_hurt_anim.py"
HURT_CONTRACT = "skill_timeline_hurt_anim_native.json"
SAVE_BUFF_SOURCE = "skill_timeline_save_buff_stack_num_by_tag.py"
SAVE_BUFF_CONTRACT = "skill_timeline_save_buff_stack_num_by_tag_native.json"
FRACTURE_SOURCE = "skill_timeline_fracture.py"
SHOW_COMBO_UI_SOURCE = "skill_timeline_show_combo_skill_ui.py"
SHOW_COMBO_UI_CONTRACT = "buff_residual_frontier.json"
TELEPORT_SQUAD_SOURCE = "skill_timeline_try_teleport_squad.py"
TELEPORT_SQUAD_CONTRACT = "skill_timeline_try_teleport_squad_native.json"
ANIM_EVENT_SOURCE = "skill_timeline_anim_event_receiver.py"
ANIM_EVENT_CONTRACT = "skill_timeline_anim_event_receiver_native.json"
ANIM_SCALE_SOURCE = "skill_timeline_continuous_anim_time_scale.py"
ANIM_SCALE_CONTRACT = "skill_timeline_continuous_anim_time_scale_native.json"
EXPECTED_SHARED_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_dice_float import (
    decode_shared_action as decode_dice_float_action,
    validate_current_native_contract as validate_dice_float_native_contract,
)
""",
    """        if tag == 0x009C:
            decode_dice_float_action(self, depth, tag, width)
            return
""",
    """    dice_route = next((row for row in routes if row.get("tag") == "0x009C"), None)
    dice_source = dependency_values.get("skill_timeline_dice_float_native.json", {})
    if (
        not isinstance(dice_route, dict)
        or dice_route.get("typeName") != "Beyond.Gameplay.Core.DiceFloat+Data"
        or dice_route.get("memberCount") != 7
        or dice_route.get("sourceContract") != {
            "path": "skill_timeline_dice_float_native.json",
            "schema": "endfield.skill-timeline-dice-float-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or dice_source.get("schema") != "endfield.skill-timeline-dice-float-native-contract.v1"
        or dice_source.get("status") != "exact-current-build"
        or dice_source.get("dispatcher", {}).get("unionTag") != 0x009C
        or dice_source.get("dispatcher", {}).get("wrapperName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_DiceFloat_DataForMemoryPack"
        or len(dice_source.get("orderedSourceReads", ())) != 7
    ):
        raise ValueError("skillTimelineSharedSequence.contract:dice-float-source-drift")
""",
    """    dice_float_validation = validate_dice_float_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "diceFloatNativeValidation": dice_float_validation,
""",
)
EXPECTED_SLOT_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_move_to_slot import (
    decode_shared_action as decode_move_to_slot_action,
    validate_current_native_contract as validate_move_to_slot_native_contract,
)
""",
    """        if tag == 0x00FA:
            decode_move_to_slot_action(self, depth, tag, width)
            return
""",
    """    slot_route = next((row for row in routes if row.get("tag") == "0x00FA"), None)
    slot_source = dependency_values.get("skill_timeline_move_to_slot_native.json", {})
    if (
        not isinstance(slot_route, dict)
        or slot_route.get("typeName") != "Beyond.Gameplay.Core.MoveToSlotAction+Data"
        or slot_route.get("memberCount") != 17
        or slot_route.get("sourceContract") != {
            "path": "skill_timeline_move_to_slot_native.json",
            "schema": "endfield.skill-timeline-move-to-slot-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or slot_source.get("schema") != "endfield.skill-timeline-move-to-slot-native-contract.v1"
        or slot_source.get("status") != "exact-current-build"
        or slot_source.get("dispatcher", {}).get("unionTag") != 0x00FA
        or slot_source.get("serializedMemberCount") != 17
        or len(slot_source.get("orderedSourceReads", ())) != 17
    ):
        raise ValueError("skillTimelineSharedSequence.contract:move-to-slot-source-drift")
""",
    """    move_to_slot_validation = validate_move_to_slot_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "moveToSlotNativeValidation": move_to_slot_validation,
""",
)
EXPECTED_LOG_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_log_action import (
    decode_shared_action as decode_log_action,
    validate_current_native_contract as validate_log_action_native_contract,
)
""",
    """        if tag == 0x00E5:
            decode_log_action(self, depth, tag, width)
            return
""",
    """    log_route = next((row for row in routes if row.get("tag") == "0x00E5"), None)
    log_source = dependency_values.get("skill_timeline_log_action_native.json", {})
    if (
        not isinstance(log_route, dict)
        or log_route.get("typeName") != "Beyond.Gameplay.Core.LogAction+Data"
        or log_route.get("memberCount") != 10
        or log_route.get("sourceContract") != {
            "path": "skill_timeline_log_action_native.json",
            "schema": "endfield.skill-timeline-log-action-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or log_source.get("schema") != "endfield.skill-timeline-log-action-native-contract.v1"
        or log_source.get("status") != "exact-current-build"
        or log_source.get("dispatcher", {}).get("unionTag") != 0x00E5
        or log_source.get("serializedMemberCount") != 10
        or len(log_source.get("orderedSourceReads", ())) != 10
    ):
        raise ValueError("skillTimelineSharedSequence.contract:log-action-source-drift")
""",
    """    log_action_validation = validate_log_action_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "logActionNativeValidation": log_action_validation,
""",
)
EXPECTED_HURT_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_hurt_anim import (
    decode_shared_action as decode_hurt_anim_action,
    validate_current_native_contract as validate_hurt_anim_native_contract,
)
""",
    """        if tag == 0x00C8:
            decode_hurt_anim_action(self, depth, tag, width)
            return
""",
    """    hurt_route = next((row for row in routes if row.get("tag") == "0x00C8"), None)
    hurt_source = dependency_values.get("skill_timeline_hurt_anim_native.json", {})
    if (
        not isinstance(hurt_route, dict)
        or hurt_route.get("typeName") != "Beyond.Gameplay.Core.HurtAnimAction+Data"
        or hurt_route.get("memberCount") != 10
        or hurt_route.get("sourceContract") != {
            "path": "skill_timeline_hurt_anim_native.json",
            "schema": "endfield.skill-timeline-hurt-anim-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or hurt_source.get("schema") != "endfield.skill-timeline-hurt-anim-native-contract.v1"
        or hurt_source.get("status") != "exact-current-build"
        or hurt_source.get("dispatcher", {}).get("unionTag") != 0x00C8
        or hurt_source.get("serializedMemberCount") != 10
        or len(hurt_source.get("orderedSourceReads", ())) != 10
    ):
        raise ValueError("skillTimelineSharedSequence.contract:hurt-anim-source-drift")
""",
    """    hurt_anim_validation = validate_hurt_anim_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "hurtAnimNativeValidation": hurt_anim_validation,
""",
)
EXPECTED_SAVE_BUFF_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_save_buff_stack_num_by_tag import (
    decode_shared_action as decode_save_buff_stack_num_by_tag_action,
    validate_current_native_contract as validate_save_buff_stack_num_by_tag_native_contract,
)
""",
    """        if tag == 0x0137:
            decode_save_buff_stack_num_by_tag_action(self, depth, tag, width)
            return
""",
    """    save_buff_route = next((row for row in routes if row.get("tag") == "0x0137"), None)
    save_buff_source = dependency_values.get("skill_timeline_save_buff_stack_num_by_tag_native.json", {})
    if (
        not isinstance(save_buff_route, dict)
        or save_buff_route.get("typeName") != "Beyond.Gameplay.Core.SaveBuffStackNumByTag+Data"
        or save_buff_route.get("memberCount") != 8
        or save_buff_route.get("sourceContract") != {
            "path": "skill_timeline_save_buff_stack_num_by_tag_native.json",
            "schema": "endfield.skill-timeline-save-buff-stack-num-by-tag-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or save_buff_source.get("schema") != "endfield.skill-timeline-save-buff-stack-num-by-tag-native-contract.v1"
        or save_buff_source.get("status") != "exact-current-build"
        or save_buff_source.get("dispatcher", {}).get("unionTag") != 0x0137
        or save_buff_source.get("serializedMemberCount") != 8
        or len(save_buff_source.get("orderedSourceReads", ())) != 8
    ):
        raise ValueError("skillTimelineSharedSequence.contract:save-buff-stack-num-by-tag-source-drift")
""",
    """    save_buff_stack_num_by_tag_validation = validate_save_buff_stack_num_by_tag_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "saveBuffStackNumByTagNativeValidation": save_buff_stack_num_by_tag_validation,
""",
)
EXPECTED_FRACTURE_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_fracture import (
    decode_shared_action as decode_fracture_action,
    validate_current_native_contract as validate_fracture_native_contract,
)
""",
    """        if tag == 0x00BE:
            decode_fracture_action(self, depth, tag, width)
            return
""",
    """    fracture_route = next((row for row in routes if row.get("tag") == "0x00BE"), None)
    fracture_source = next(
        (row for row in frontier.get("actions", ()) if row.get("unionTag") == 0x00BE), None
    )
    if (
        not isinstance(fracture_route, dict)
        or fracture_route.get("typeName") != "Beyond.Gameplay.Core.FractureAction+Data"
        or fracture_route.get("memberCount") != 15
        or fracture_route.get("sourceContract") != {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=190].readOrder",
        }
        or not isinstance(fracture_source, dict)
        or fracture_source.get("actualTypeName") != fracture_route["typeName"]
        or fracture_source.get("serializedMemberCount") != 15
        or tuple(fracture_source.get("readOrder", ())) != (
            "byte", "scalar32", "scalar32", "scalar32", "target-settings",
            "blackboard-double", "blackboard-double", "enum32", "direction-settings",
            "blackboard-double", "bool", "bool", "target-settings",
            "blackboard-double", "float32",
        )
    ):
        raise ValueError("skillTimelineSharedSequence.contract:fracture-source-drift")
""",
    """    fracture_validation = validate_fracture_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "fractureNativeValidation": fracture_validation,
""",
)
EXPECTED_SHOW_COMBO_UI_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_show_combo_skill_ui import (
    decode_shared_action as decode_show_combo_skill_ui_action,
    validate_current_native_contract as validate_show_combo_skill_ui_native_contract,
)
""",
    """        if tag == 0x015F:
            decode_show_combo_skill_ui_action(self, depth, tag, width)
            return
""",
    """    combo_ui_route = next((row for row in routes if row.get("tag") == "0x015F"), None)
    residual_frontier = dependency_values.get("buff_residual_frontier.json", {})
    combo_ui_source = next(
        (row for row in residual_frontier.get("actions", ()) if row.get("unionTag") == 0x015F),
        None,
    )
    if (
        not isinstance(combo_ui_route, dict)
        or combo_ui_route.get("typeName") != "Beyond.Gameplay.Core.ShowComboSkillUI+Data"
        or combo_ui_route.get("memberCount") != 4
        or combo_ui_route.get("sourceContract") != {
            "path": "buff_residual_frontier.json",
            "schema": "endfield.buff-residual-frontier-native-contract.v1",
            "orderedReadRef": "actions[unionTag=351].readOrder",
        }
        or residual_frontier.get("schema") != "endfield.buff-residual-frontier-native-contract.v1"
        or residual_frontier.get("status") != "exact-current-build"
        or not isinstance(combo_ui_source, dict)
        or combo_ui_source.get("wrapperName")
        != "Beyond.MemoryPack.Beyond_Gameplay_Core_ShowComboSkillUI_DataForMemoryPack"
        or combo_ui_source.get("serializedMemberCount") != 4
        or tuple(combo_ui_source.get("readOrder", ()))
        != ("byte", "scalar32", "scalar32", "scalar32")
    ):
        raise ValueError("skillTimelineSharedSequence.contract:show-combo-skill-ui-source-drift")
""",
    """    show_combo_skill_ui_validation = validate_show_combo_skill_ui_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "showComboSkillUINativeValidation": show_combo_skill_ui_validation,
""",
)
EXPECTED_TELEPORT_SQUAD_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_try_teleport_squad import (
    decode_shared_action as decode_try_teleport_squad_action,
    validate_current_native_contract as validate_try_teleport_squad_native_contract,
)
""",
    """        if tag == 0x018C:
            decode_try_teleport_squad_action(self, depth, tag, width)
            return
""",
    """    teleport_squad_route = next((row for row in routes if row.get("tag") == "0x018C"), None)
    teleport_squad_source = dependency_values.get("skill_timeline_try_teleport_squad_native.json", {})
    if (
        not isinstance(teleport_squad_route, dict)
        or teleport_squad_route.get("typeName")
        != "Beyond.Gameplay.Core.TryToTeleportSquadAction+Data"
        or teleport_squad_route.get("memberCount") != 4
        or teleport_squad_route.get("sourceContract") != {
            "path": "skill_timeline_try_teleport_squad_native.json",
            "schema": "endfield.skill-timeline-try-teleport-squad-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or teleport_squad_source.get("schema")
        != "endfield.skill-timeline-try-teleport-squad-native-contract.v1"
        or teleport_squad_source.get("status") != "exact-current-build"
        or teleport_squad_source.get("dispatcher", {}).get("unionTag") != 0x018C
        or teleport_squad_source.get("serializedMemberCount") != 4
        or len(teleport_squad_source.get("orderedSourceReads", ())) != 4
    ):
        raise ValueError("skillTimelineSharedSequence.contract:try-teleport-squad-source-drift")
""",
    """    try_teleport_squad_validation = validate_try_teleport_squad_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "tryTeleportSquadNativeValidation": try_teleport_squad_validation,
""",
)
EXPECTED_ANIM_EVENT_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_anim_event_receiver import (
    decode_shared_action as decode_anim_event_receiver_action,
    validate_current_native_contract as validate_anim_event_receiver_native_contract,
)
""",
    """        if tag == 0x0012:
            decode_anim_event_receiver_action(self, depth, tag, width)
            return
""",
    """    anim_event_route = next((row for row in routes if row.get("tag") == "0x0012"), None)
    anim_event_source = dependency_values.get("skill_timeline_anim_event_receiver_native.json", {})
    if (
        not isinstance(anim_event_route, dict)
        or anim_event_route.get("typeName") != "Beyond.Gameplay.Core.AnimEventReceiver+Data"
        or anim_event_route.get("memberCount") != 7
        or anim_event_route.get("sourceContract") != {
            "path": "skill_timeline_anim_event_receiver_native.json",
            "schema": "endfield.skill-timeline-anim-event-receiver-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or anim_event_source.get("schema")
        != "endfield.skill-timeline-anim-event-receiver-native-contract.v1"
        or anim_event_source.get("status") != "exact-current-build"
        or anim_event_source.get("dispatcher", {}).get("unionTag") != 0x0012
        or anim_event_source.get("serializedMemberCount") != 7
        or len(anim_event_source.get("orderedSourceReads", ())) != 7
    ):
        raise ValueError("skillTimelineSharedSequence.contract:anim-event-receiver-source-drift")
""",
    """    anim_event_receiver_validation = validate_anim_event_receiver_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "animEventReceiverNativeValidation": anim_event_receiver_validation,
""",
)
EXPECTED_ANIM_SCALE_ADDITIONS = (
    """from scripts.game_data.memorypack.skill_timeline_continuous_anim_time_scale import (
    decode_shared_action as decode_continuous_anim_time_scale_action,
    validate_current_native_contract as validate_continuous_anim_time_scale_native_contract,
)
""",
    """        if tag == 0x008B:
            decode_continuous_anim_time_scale_action(self, depth, tag, width)
            return
""",
    """    anim_scale_route = next((row for row in routes if row.get("tag") == "0x008B"), None)
    anim_scale_source = dependency_values.get(
        "skill_timeline_continuous_anim_time_scale_native.json", {}
    )
    if (
        not isinstance(anim_scale_route, dict)
        or anim_scale_route.get("typeName")
        != "Beyond.Gameplay.Core.ContinuousSetAnimTimeScale+Data"
        or anim_scale_route.get("memberCount") != 5
        or anim_scale_route.get("sourceContract") != {
            "path": "skill_timeline_continuous_anim_time_scale_native.json",
            "schema": "endfield.skill-timeline-continuous-anim-time-scale-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        }
        or anim_scale_source.get("schema")
        != "endfield.skill-timeline-continuous-anim-time-scale-native-contract.v1"
        or anim_scale_source.get("status") != "exact-current-build"
        or anim_scale_source.get("dispatcher", {}).get("unionTag") != 0x008B
        or anim_scale_source.get("serializedMemberCount") != 5
        or len(anim_scale_source.get("orderedSourceReads", ())) != 5
    ):
        raise ValueError("skillTimelineSharedSequence.contract:continuous-anim-time-scale-source-drift")
""",
    """    continuous_anim_time_scale_validation = validate_continuous_anim_time_scale_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
""",
    """        "continuousAnimTimeScaleNativeValidation": continuous_anim_time_scale_validation,
""",
)
SCOPE_PROVENANCE = frozenset({
    "selectedChunkFingerprints", "selectedChunkResolution", "parser",
    "cursorVerification",
})
IDENTITY_KEYS = (
    "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
    "physicalChunkPath", "physicalChunkSource", "metadataProvenance",
    "overlayState", "chunkOverlayState", "physicalOffset", "encrypted",
)


class SparseCompositionError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SparseCompositionError(message)


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    _require(isinstance(data, dict), f"{path}: expected JSON object")
    return data


def _source_fingerprint(data: bytes) -> tuple[int, str]:
    return len(data), hashlib.sha256(data).hexdigest().upper()


def _ast_without_downstream_body(data: bytes) -> str:
    tree = ast.parse(data.decode("utf-8"))
    matches = [node for node in tree.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == DOWNSTREAM_FUNCTION]
    _require(len(matches) == 1, f"expected one {DOWNSTREAM_FUNCTION} function")
    matches[0].body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def prove_downstream_only_drift(
    old_source: bytes, current_source: bytes,
    old_reference: Mapping[str, Any], current_reference: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate both versions and compare every AST node outside one body."""
    _require(
        _source_fingerprint(old_source)
        == (old_reference.get("length"), old_reference.get("sha256")),
        "historical parser source bytes differ from the control report",
    )
    _require(
        _source_fingerprint(current_source)
        == (current_reference.get("length"), current_reference.get("sha256")),
        "current parser source bytes differ from the unknown report",
    )
    _require(
        _ast_without_downstream_body(old_source)
        == _ast_without_downstream_body(current_source),
        "parser AST changed outside the downstream target-set rebind function",
    )
    return {
        "status": "downstream-only-source-drift",
        "sourcePath": current_reference["path"],
        "historicalLength": old_reference["length"],
        "historicalSha256": old_reference["sha256"],
        "currentLength": current_reference["length"],
        "currentSha256": current_reference["sha256"],
        "excludedFunctionBody": DOWNSTREAM_FUNCTION,
    }


def prove_dice_route_only_drift(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate an exact additive route edit and its reviewed JSON row."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_SHARED_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser route addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    _require(stripped.encode("utf-8") == old_source,
             "shared parser changed beyond the DiceFloat route addition")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict)
             and old_value.get("schema") == current_value.get("schema"),
             "shared contract schema differs")
    routes = current_value.get("allowedReachedRoutes")
    dependencies = current_value.get("dependencies")
    _require(isinstance(routes, list) and isinstance(dependencies, list),
             "shared contract routes or dependencies missing")
    added = [row for row in routes if row.get("tag") == "0x009C"]
    _require(added == [{
        "tag": "0x009C", "typeName": "Beyond.Gameplay.Core.DiceFloat+Data",
        "memberCount": 7, "sourceContract": {
            "path": DICE_CONTRACT,
            "schema": "endfield.skill-timeline-dice-float-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        },
    }], "shared contract DiceFloat route differs")
    _require(dependencies.count({"path": DICE_CONTRACT}) == 1,
             "shared contract DiceFloat dependency differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row not in added]
    current_value["dependencies"] = [row for row in dependencies
                                     if row != {"path": DICE_CONTRACT}]
    _require(current_value == old_value,
             "shared contract changed beyond one DiceFloat route and dependency")
    return {
        "status": "dice-route-only-source-and-contract-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTag": "0x009C",
    }


def prove_three_route_only_drift(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the exact DiceFloat, MoveToSlot and LogAction additions only."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in (*EXPECTED_SHARED_ADDITIONS,
                     *EXPECTED_SLOT_ADDITIONS, *EXPECTED_LOG_ADDITIONS):
        _require(stripped.count(addition) == 1,
                 "shared parser multi-route addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    _require(stripped.encode("utf-8") == old_source,
             "shared parser changed beyond the three exact route additions")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict)
             and old_value.get("schema") == current_value.get("schema"),
             "shared contract schema differs")
    routes = current_value.get("allowedReachedRoutes")
    dependencies = current_value.get("dependencies")
    _require(isinstance(routes, list) and isinstance(dependencies, list),
             "shared contract routes or dependencies missing")
    expected_rows = (
        ("0x009C", "Beyond.Gameplay.Core.DiceFloat+Data", 7,
         DICE_CONTRACT, "endfield.skill-timeline-dice-float-native-contract.v1"),
        ("0x00FA", "Beyond.Gameplay.Core.MoveToSlotAction+Data", 17,
         SLOT_CONTRACT, "endfield.skill-timeline-move-to-slot-native-contract.v1"),
        ("0x00E5", "Beyond.Gameplay.Core.LogAction+Data", 10,
         LOG_CONTRACT, "endfield.skill-timeline-log-action-native-contract.v1"),
    )
    added = []
    for tag, type_name, count, path, schema in expected_rows:
        row = {
            "tag": tag, "typeName": type_name, "memberCount": count,
            "sourceContract": {"path": path, "schema": schema,
                               "orderedReadRef": "orderedSourceReads"},
        }
        _require([x for x in routes if x.get("tag") == tag] == [row],
                 f"shared contract {tag} route differs")
        _require(dependencies.count({"path": path}) == 1,
                 f"shared contract {tag} dependency differs")
        added.append(row)
    current_value["allowedReachedRoutes"] = [row for row in routes if row not in added]
    current_value["dependencies"] = [
        row for row in dependencies
        if row not in ({"path": DICE_CONTRACT}, {"path": SLOT_CONTRACT},
                       {"path": LOG_CONTRACT})
    ]
    _require(current_value == old_value,
             "shared contract changed beyond three routes and dependencies")
    return {
        "status": "three-route-only-source-and-contract-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [row[0] for row in expected_rows],
    }


def prove_four_route_with_hurt_promotion(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove three additions plus exact derived-to-reviewed HurtAnim promotion."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_HURT_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser HurtAnim promotion differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    old_hurt = {"tag": "0x00C8",
                "typeName": "Beyond.Gameplay.Core.HurtAnimAction+Data",
                "memberCount": 10, "evidence": "derivedPlanCorpusVerified"}
    new_hurt = {"tag": "0x00C8",
                "typeName": "Beyond.Gameplay.Core.HurtAnimAction+Data",
                "memberCount": 10,
                "sourceContract": {
                    "path": HURT_CONTRACT,
                    "schema": "endfield.skill-timeline-hurt-anim-native-contract.v1",
                    "orderedReadRef": "orderedSourceReads",
                }}
    old_routes = old_value.get("allowedReachedRoutes", [])
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(old_routes, list) and isinstance(routes, list)
             and isinstance(deps, list)
             and [row for row in old_routes if row.get("tag") == "0x00C8"] == [old_hurt]
             and [row for row in routes if row.get("tag") == "0x00C8"] == [new_hurt]
             and deps.count({"path": HURT_CONTRACT}) == 1,
             "shared contract HurtAnim promotion differs")
    current_value["allowedReachedRoutes"] = [
        old_hurt if row == new_hurt else row for row in routes
    ]
    current_value["dependencies"] = [
        row for row in deps if row != {"path": HURT_CONTRACT}
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_three_route_only_drift(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "four-route-with-hurt-promotion-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x00C8"],
    }


def prove_five_route_with_save_buff_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior four edits plus exact additive 0x0137 route."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_SAVE_BUFF_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser SaveBuffStackNumByTag addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    save_route = {
        "tag": "0x0137", "typeName": "Beyond.Gameplay.Core.SaveBuffStackNumByTag+Data",
        "memberCount": 8,
        "sourceContract": {
            "path": SAVE_BUFF_CONTRACT,
            "schema": "endfield.skill-timeline-save-buff-stack-num-by-tag-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(routes, list) and isinstance(deps, list)
             and [row for row in routes if row.get("tag") == "0x0137"] == [save_route]
             and deps.count({"path": SAVE_BUFF_CONTRACT}) == 1,
             "shared contract SaveBuffStackNumByTag addition differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row != save_route]
    current_value["dependencies"] = [row for row in deps
                                      if row != {"path": SAVE_BUFF_CONTRACT}]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_four_route_with_hurt_promotion(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "five-route-with-save-buff-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x0137"],
    }


def prove_six_route_with_fracture_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior five edits plus one route reusing Buff frontier9."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_FRACTURE_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser FractureAction addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    fracture_route = {
        "tag": "0x00BE", "typeName": "Beyond.Gameplay.Core.FractureAction+Data",
        "memberCount": 15,
        "sourceContract": {
            "path": "buff_frontier9.json",
            "schema": "endfield.buff-frontier9-native-contract.v1",
            "orderedReadRef": "actions[unionTag=190].readOrder",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    _require(isinstance(routes, list)
             and [row for row in routes if row.get("tag") == "0x00BE"] == [fracture_route],
             "shared contract FractureAction addition differs")
    current_value["allowedReachedRoutes"] = [
        row for row in routes if row != fracture_route
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_five_route_with_save_buff_addition(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "six-route-with-fracture-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x00BE"],
    }


def prove_seven_route_with_show_combo_ui_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior six edits plus selected residual frontier route 0x015F."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_SHOW_COMBO_UI_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser ShowComboSkillUI addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    route = {
        "tag": "0x015F", "typeName": "Beyond.Gameplay.Core.ShowComboSkillUI+Data",
        "memberCount": 4,
        "sourceContract": {
            "path": SHOW_COMBO_UI_CONTRACT,
            "schema": "endfield.buff-residual-frontier-native-contract.v1",
            "orderedReadRef": "actions[unionTag=351].readOrder",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(routes, list) and isinstance(deps, list)
             and [row for row in routes if row.get("tag") == "0x015F"] == [route]
             and deps.count({"path": SHOW_COMBO_UI_CONTRACT}) == 1,
             "shared contract ShowComboSkillUI addition differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row != route]
    current_value["dependencies"] = [
        row for row in deps if row != {"path": SHOW_COMBO_UI_CONTRACT}
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_six_route_with_fracture_addition(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "seven-route-with-show-combo-ui-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x015F"],
    }


def prove_eight_route_with_teleport_squad_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior seven edits plus exact selected 0x018C admission."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_TELEPORT_SQUAD_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser TryToTeleportSquad addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    route = {
        "tag": "0x018C", "typeName": "Beyond.Gameplay.Core.TryToTeleportSquadAction+Data",
        "memberCount": 4,
        "sourceContract": {
            "path": TELEPORT_SQUAD_CONTRACT,
            "schema": "endfield.skill-timeline-try-teleport-squad-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(routes, list) and isinstance(deps, list)
             and [row for row in routes if row.get("tag") == "0x018C"] == [route]
             and deps.count({"path": TELEPORT_SQUAD_CONTRACT}) == 1,
             "shared contract TryToTeleportSquad addition differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row != route]
    current_value["dependencies"] = [
        row for row in deps if row != {"path": TELEPORT_SQUAD_CONTRACT}
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_seven_route_with_show_combo_ui_addition(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "eight-route-with-teleport-squad-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x018C"],
    }


def prove_nine_route_with_anim_event_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior eight edits plus exact selected 0x0012 admission."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_ANIM_EVENT_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser AnimEventReceiver addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    route = {
        "tag": "0x0012", "typeName": "Beyond.Gameplay.Core.AnimEventReceiver+Data",
        "memberCount": 7,
        "sourceContract": {
            "path": ANIM_EVENT_CONTRACT,
            "schema": "endfield.skill-timeline-anim-event-receiver-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(routes, list) and isinstance(deps, list)
             and [row for row in routes if row.get("tag") == "0x0012"] == [route]
             and deps.count({"path": ANIM_EVENT_CONTRACT}) == 1,
             "shared contract AnimEventReceiver addition differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row != route]
    current_value["dependencies"] = [
        row for row in deps if row != {"path": ANIM_EVENT_CONTRACT}
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_eight_route_with_teleport_squad_addition(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "nine-route-with-anim-event-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x0012"],
    }


def prove_ten_route_with_anim_scale_addition(
    old_source: bytes, current_source: bytes,
    old_source_ref: Mapping[str, Any], current_source_ref: Mapping[str, Any],
    old_contract: bytes, current_contract: bytes,
    old_contract_ref: Mapping[str, Any], current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the prior nine edits plus exact selected 0x008B admission."""
    for label, raw, ref in (
        ("old parser", old_source, old_source_ref),
        ("current parser", current_source, current_source_ref),
        ("old contract", old_contract, old_contract_ref),
        ("current contract", current_contract, current_contract_ref),
    ):
        _require(_source_fingerprint(raw) == (ref.get("length"), ref.get("sha256")),
                 f"{label} bytes differ from the authenticated report")
    stripped = current_source.decode("utf-8")
    for addition in EXPECTED_ANIM_SCALE_ADDITIONS:
        _require(stripped.count(addition) == 1,
                 "shared parser ContinuousAnimTimeScale addition differs from reviewed source")
        stripped = stripped.replace(addition, "", 1)
    interim_source = stripped.encode("utf-8")
    old_value, current_value = json.loads(old_contract), json.loads(current_contract)
    _require(isinstance(old_value, dict) and isinstance(current_value, dict),
             "shared contract shape differs")
    route = {
        "tag": "0x008B", "typeName": "Beyond.Gameplay.Core.ContinuousSetAnimTimeScale+Data",
        "memberCount": 5,
        "sourceContract": {
            "path": ANIM_SCALE_CONTRACT,
            "schema": "endfield.skill-timeline-continuous-anim-time-scale-native-contract.v1",
            "orderedReadRef": "orderedSourceReads",
        },
    }
    routes = current_value.get("allowedReachedRoutes", [])
    deps = current_value.get("dependencies", [])
    _require(isinstance(routes, list) and isinstance(deps, list)
             and [row for row in routes if row.get("tag") == "0x008B"] == [route]
             and deps.count({"path": ANIM_SCALE_CONTRACT}) == 1,
             "shared contract ContinuousAnimTimeScale addition differs")
    current_value["allowedReachedRoutes"] = [row for row in routes if row != route]
    current_value["dependencies"] = [
        row for row in deps if row != {"path": ANIM_SCALE_CONTRACT}
    ]
    interim_contract = json.dumps(current_value, separators=(",", ":")).encode()
    interim_source_ref = {"length": len(interim_source),
                          "sha256": _source_fingerprint(interim_source)[1]}
    interim_contract_ref = {"length": len(interim_contract),
                            "sha256": _source_fingerprint(interim_contract)[1]}
    base = prove_nine_route_with_anim_event_addition(
        old_source, interim_source, old_source_ref, interim_source_ref,
        old_contract, interim_contract, old_contract_ref, interim_contract_ref,
    )
    return {
        "status": "ten-route-with-anim-scale-addition-only-drift",
        "oldParserSha256": old_source_ref["sha256"],
        "currentParserSha256": current_source_ref["sha256"],
        "oldContractSha256": old_contract_ref["sha256"],
        "currentContractSha256": current_contract_ref["sha256"],
        "routeTags": [*base["routeTags"], "0x008B"],
    }


def _parser_map(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    parser = report.get("provenance", {}).get("parser")
    _require(isinstance(parser, list) and all(isinstance(x, Mapping) for x in parser),
             "parser fingerprints missing")
    result = {str(row.get("path")): row for row in parser}
    _require(len(result) == len(parser), "duplicate parser source fingerprint")
    return result


def _fingerprint_map(report: Mapping[str, Any], role: str) -> dict[str, Mapping[str, Any]]:
    rows = report.get("provenance", {}).get(role)
    _require(isinstance(rows, list) and all(isinstance(row, Mapping) for row in rows),
             f"{role} fingerprints missing")
    result = {str(row.get("path")): row for row in rows}
    _require(len(result) == len(rows), f"duplicate {role} fingerprint")
    return result


def _unique_named(rows: Mapping[str, Mapping[str, Any]], name: str) -> tuple[str, Mapping[str, Any]]:
    matches = [(path, row) for path, row in rows.items() if Path(path).name == name]
    _require(len(matches) == 1, f"expected exactly one {name} fingerprint")
    return matches[0]


def _controls_unreached_routes(rows: list[dict[str, Any]], added_tags: set[int]) -> None:
    """The added action cannot affect a closed control that never reaches it."""
    for row in rows:
        _require(row.get("wholeSchemaExact") is True,
                 "saved family control is not whole-schema exact")
        empty = row.get("emptyActionGroupProfile") or {}
        timeline = row.get("timelineSharedSequenceProfile") or {}
        if empty.get("status") == "verified-exact-through-field-42":
            _require(not timeline, "empty family control has a timeline profile")
            continue
        _require(timeline.get("wholeActionGroupDataExact") is True
                 and timeline.get("wholeTimelineListExact") is True
                 and timeline.get("laterStopReason") is None
                 and timeline.get("timelineActionsCount") == 1,
                 "family control's action list is not completely observed")
        actions = timeline.get("firstTimelineAction", {}).get("actionData")
        _require(isinstance(actions, list) and actions
                 and all(action.get("tag") not in added_tags for action in actions),
                 "family control reaches a newly added action route")


def _controls_unreached_dice(rows: list[dict[str, Any]]) -> None:
    _controls_unreached_routes(rows, {0x009C})


def _scope_rows(report: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    _require(report.get("status") == "partial"
             and report.get("publicationEligible") is False,
             f"{label}: expected nonpublishable partial corpus")
    paths, rows = report.get("targetedVirtualPaths"), report.get("files")
    _require(isinstance(paths, list) and isinstance(rows, list)
             and paths == sorted(set(paths))
             and [row.get("virtualPath") for row in rows] == paths,
             f"{label}: rows differ from exact targeted scope")
    _require(all(row.get("inputSetSha256") == report.get("inputSetSha256")
                 for row in rows), f"{label}: row input set differs")
    return rows


def compose(
    control_path: Path, unknown_path: Path, old_parser_source_path: Path,
    verification_path: Path, expected_unknown_paths: list[str],
    *, old_shared_parser_source_path: Path | None = None,
    old_shared_contract_path: Path | None = None,
) -> dict[str, Any]:
    """Recheck two partial reports and replay the family receipt on their union."""
    control_path = control_path.resolve()
    unknown_path = unknown_path.resolve()
    verification_path = verification_path.resolve()
    route_mode = old_shared_parser_source_path is not None or old_shared_contract_path is not None
    _require(not route_mode or (old_shared_parser_source_path is not None
                                and old_shared_contract_path is not None),
             "route-addition rebind requires both old shared source and contract")
    _require(len({control_path, unknown_path, verification_path}) == 3,
             "evidence files must be distinct")
    control = _load(control_path)
    unknown = _load(unknown_path)
    verification = _load(verification_path)
    control_rows = _scope_rows(control, "controls")
    unknown_rows = _scope_rows(unknown, "unknowns")
    _require(expected_unknown_paths == sorted(set(expected_unknown_paths))
             and expected_unknown_paths == unknown["targetedVirtualPaths"],
             "unknown report is not the exact requested scope")
    expected_controls = sorted(row.get("logicalPath")
                               for row in verification.get("rows", [])
                               if isinstance(row, Mapping))
    _require(expected_controls and control["targetedVirtualPaths"] == expected_controls,
             "control report does not contain every captured observation")
    _require(not set(expected_controls) & set(expected_unknown_paths),
             "control and unknown scopes overlap")
    _require(control.get("inputSetSha256") == unknown.get("inputSetSha256"),
             "control and unknown VFS input sets differ")
    left, right = control.get("provenance"), unknown.get("provenance")
    _require(isinstance(left, Mapping) and isinstance(right, Mapping)
             and set(left) == set(right), "provenance shape differs")
    variable_provenance = set(SCOPE_PROVENANCE)
    if route_mode:
        variable_provenance.update(("timelinePlayAnimationContracts",
                                    "timelineSharedSequenceNativeValidation"))
    for key in left:
        if key not in variable_provenance:
            _require(left[key] == right[key], f"shared {key} provenance differs")
    _require(left.get("cursorVerification", {}).get("path") == verification_path.as_posix()
             and left.get("cursorVerification", {}).get("sha256")
             == _fingerprint(verification_path)["sha256"]
             and right.get("cursorVerification") is None
             and left.get("captureTargetSetVerification") is None
             and right.get("captureTargetSetVerification") is None,
             "family verification or downstream target-set scope differs")
    old_map, new_map = _parser_map(control), _parser_map(unknown)
    downstream_path, old_ref = _unique_named(old_map, DOWNSTREAM_SOURCE)
    _require(downstream_path in new_map, "downstream verifier path differs")
    new_ref = new_map[downstream_path]
    _require(Path(downstream_path).resolve() == Path(new_ref["path"]).resolve(),
             "downstream verifier path differs")
    downstream_proof = prove_downstream_only_drift(
        old_parser_source_path.read_bytes(), Path(new_ref["path"]).read_bytes(),
        old_ref, new_ref,
    )
    route_proof = None
    if route_mode:
        new_only = set(new_map) - set(old_map)
        new_names = {Path(path).name for path in new_only}
        valid_module_sets = (
            {DICE_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE, HURT_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE, HURT_SOURCE, SAVE_BUFF_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE, HURT_SOURCE, SAVE_BUFF_SOURCE,
             FRACTURE_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE, HURT_SOURCE, SAVE_BUFF_SOURCE,
             FRACTURE_SOURCE, SHOW_COMBO_UI_SOURCE},
            {DICE_SOURCE, SLOT_SOURCE, LOG_SOURCE, HURT_SOURCE, SAVE_BUFF_SOURCE,
             FRACTURE_SOURCE, SHOW_COMBO_UI_SOURCE, TELEPORT_SQUAD_SOURCE},
        )
        route_modules = new_names
        _require(len(new_only) == len(route_modules)
                 and route_modules in valid_module_sets
                 and not (set(old_map) - set(new_map)),
                 "parser closure changed beyond the reviewed additive route modules")
        changed = {Path(path).name for path in old_map
                   if old_map[path] != new_map[path]}
        _require(changed == {DOWNSTREAM_SOURCE, SHARED_SOURCE},
                 "parser closure changed beyond the two attested sources")
        shared_path, old_shared_ref = _unique_named(old_map, SHARED_SOURCE)
        _require(shared_path in new_map, "shared parser path differs")
        old_contract_map = _fingerprint_map(control, "timelinePlayAnimationContracts")
        new_contract_map = _fingerprint_map(unknown, "timelinePlayAnimationContracts")
        new_contract_only = set(new_contract_map) - set(old_contract_map)
        expected_contracts = {DICE_CONTRACT}
        if len(route_modules) >= 3:
            expected_contracts.update({SLOT_CONTRACT, LOG_CONTRACT})
        if len(route_modules) >= 4:
            expected_contracts.add(HURT_CONTRACT)
        if len(route_modules) >= 5:
            expected_contracts.add(SAVE_BUFF_CONTRACT)
        if len(route_modules) >= 7:
            expected_contracts.add(SHOW_COMBO_UI_CONTRACT)
        if len(route_modules) == 8:
            expected_contracts.add(TELEPORT_SQUAD_CONTRACT)
        _require(len(new_contract_only) == len(expected_contracts)
                 and {Path(path).name for path in new_contract_only} == expected_contracts
                 and not (set(old_contract_map) - set(new_contract_map)),
                 "contract closure changed beyond the reviewed additive route contracts")
        contract_changes = {Path(path).name for path in old_contract_map
                            if old_contract_map[path] != new_contract_map[path]}
        _require(contract_changes == {SHARED_CONTRACT},
                 "contract closure changed beyond the shared route contract")
        shared_contract_path, old_contract_ref = _unique_named(
            old_contract_map, SHARED_CONTRACT,
        )
        _require(shared_contract_path in new_contract_map,
                 "shared contract path differs")
        proof = ({1: prove_dice_route_only_drift,
                  3: prove_three_route_only_drift,
                  4: prove_four_route_with_hurt_promotion,
                  5: prove_five_route_with_save_buff_addition,
                  6: prove_six_route_with_fracture_addition,
                  7: prove_seven_route_with_show_combo_ui_addition,
                  8: prove_eight_route_with_teleport_squad_addition}[len(route_modules)])
        route_proof = proof(
            old_shared_parser_source_path.read_bytes(),
            Path(shared_path).read_bytes(),
            old_shared_ref, new_map[shared_path],
            old_shared_contract_path.read_bytes(),
            Path(shared_contract_path).read_bytes(),
            old_contract_ref, new_contract_map[shared_contract_path],
        )
        native_keys = {"diceFloatNativeValidation": 0x009C}
        if len(route_modules) >= 3:
            native_keys.update({"moveToSlotNativeValidation": 0x00FA,
                                "logActionNativeValidation": 0x00E5})
        if len(route_modules) >= 4:
            native_keys["hurtAnimNativeValidation"] = 0x00C8
        if len(route_modules) >= 5:
            native_keys["saveBuffStackNumByTagNativeValidation"] = 0x0137
        if len(route_modules) >= 6:
            native_keys["fractureNativeValidation"] = 0x00BE
        if len(route_modules) >= 7:
            native_keys["showComboSkillUINativeValidation"] = 0x015F
        if len(route_modules) == 8:
            native_keys["tryTeleportSquadNativeValidation"] = 0x018C
        _controls_unreached_routes(control_rows, set(native_keys.values()))
        old_native = copy.deepcopy(left["timelineSharedSequenceNativeValidation"])
        new_native = copy.deepcopy(right["timelineSharedSequenceNativeValidation"])
        _require(all(new_native.pop(key, {}).get("status") == "validated"
                     for key in native_keys)
                 and new_native.pop("dependencyCount")
                 == old_native.pop("dependencyCount") + len(native_keys)
                 - (1 if len(route_modules) >= 6 else 0)
                 and new_native.pop("contractSha256") == route_proof["currentContractSha256"]
                 and old_native.pop("contractSha256") == route_proof["oldContractSha256"]
                 and new_native == old_native,
                 "composite native validation changed beyond the reviewed additive routes")
    else:
        _require(set(old_map) == set(new_map), "parser closure paths differ")
        changes = [path for path in old_map if old_map[path] != new_map[path]]
        _require(changes == [downstream_path],
                 "parser closure changed beyond the downstream verifier")
    # Both reports must pass the live source, tool, native and selected-chunk
    # gate. The old control parser row is updated only after the exact AST
    # proof; all other provenance remains byte-for-byte as published.
    skill_corpus.verify_current_report_inputs(unknown, allow_partial=True)
    control_current = copy.deepcopy(control)
    control_current["provenance"]["parser"] = copy.deepcopy(right["parser"])
    if route_mode:
        control_current["provenance"]["timelinePlayAnimationContracts"] = copy.deepcopy(
            right["timelinePlayAnimationContracts"])
        control_current["provenance"]["timelineSharedSequenceNativeValidation"] = copy.deepcopy(
            right["timelineSharedSequenceNativeValidation"])
    skill_corpus.verify_current_report_inputs(control_current, allow_partial=True)
    rows = [*copy.deepcopy(control_rows), *copy.deepcopy(unknown_rows)]
    rows.sort(key=lambda row: row["virtualPath"])
    # The control report has already applied the family terminal. Restore
    # only the pre-selection status of its two empty ActionGroup profiles so
    # the existing verifier can compare their unchanged named field ranges
    # with the copied runtime cursor again. No bytes or cursors are inferred.
    required = set(verification.get("summary", {}).get("requiredLogicalPaths", []))
    _require(required and required <= set(expected_controls),
             "family verification lacks required control samples")
    for row in rows:
        if row["virtualPath"] not in required:
            continue
        profile = row.get("emptyActionGroupProfile")
        _require(isinstance(profile, dict)
                 and profile.get("status") == "verified-exact-through-field-42"
                 and row.get("wholeSchemaExact") is True,
                 "control sample is not a previously verified empty profile")
        profile["status"] = "exact-through-field-42"
    identity = skill_corpus._canonical_sha256([
        {key: row[key] for key in IDENTITY_KEYS} for row in rows
    ])
    family_replay = skill_corpus._apply_verified_terminal_selection(
        rows, verification_path=verification_path,
        expected_input_set_sha256=unknown["inputSetSha256"],
        identity_set_sha256=identity,
        build_fingerprints=right["buildFingerprints"],
        blc_paths=right["blcPaths"],
        allow_verified_subset_rebind=True,
        allow_historical_verifier_rebind=True,
    )
    unknown_set = set(expected_unknown_paths)
    outcomes = [
        {
            "virtualPath": row["virtualPath"],
            "length": row["length"],
            "logicalSha256": row["logicalSha256"],
            "boundaryClass": row["boundaryClass"],
            "coverageStatus": row["coverageStatus"],
            "wholeSchemaExact": row["wholeSchemaExact"],
            "timelineSharedSequenceStopReason":
                row.get("timelineSharedSequenceStopReason"),
        }
        for row in rows if row["virtualPath"] in unknown_set
    ]
    _require(len(outcomes) == len(expected_unknown_paths),
             "unknown outcome count differs")
    return {
        "schema": SCHEMA, "status": "diagnostic-only",
        "publicationEligible": False,
        "inputSetSha256": unknown["inputSetSha256"],
        "provenance": {
            "controls": _fingerprint(control_path),
            "unknowns": _fingerprint(unknown_path),
            "familyVerification": _fingerprint(verification_path),
            "oldParserCopy": _fingerprint(old_parser_source_path),
            "downstreamOnlyDrift": downstream_proof,
            "routeAdditionDrift": route_proof,
            "familyReplay": family_replay,
        },
        "summary": {
            "newUnknownFilesChecked": len(outcomes),
            "reusedCapturedControls": len(control_rows),
            "wholeSchemaExact": sum(row["wholeSchemaExact"] is True
                                    for row in outcomes),
        },
        "outcomes": outcomes,
        "evidenceBoundary": (
            "Only the requested unknown rows were newly streamed. Previously "
            "authenticated control rows were reused after live source/tool/native "
            "gates and exact parser drift proofs. The "
            "saved family cursor selects the terminal only for unchanged "
            "logical bytes. This scoped diagnostic is not a complete SkillData "
            "census or an observed gameplay branch."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--unknowns", type=Path, required=True)
    parser.add_argument("--old-parser-source", type=Path, required=True)
    parser.add_argument("--old-shared-parser-source", type=Path)
    parser.add_argument("--old-shared-contract", type=Path)
    parser.add_argument("--family-verification", type=Path, required=True)
    parser.add_argument("--expected-unknown", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    _guard_partial_output(args.output)
    _require(args.output.resolve() not in {
        args.controls.resolve(), args.unknowns.resolve(),
        args.old_parser_source.resolve(), args.family_verification.resolve(),
        *(path.resolve() for path in (
            args.old_shared_parser_source, args.old_shared_contract) if path is not None),
    }, "output overlaps evidence input")
    try:
        result = compose(args.controls, args.unknowns, args.old_parser_source,
                         args.family_verification, args.expected_unknown,
                         old_shared_parser_source_path=args.old_shared_parser_source,
                         old_shared_contract_path=args.old_shared_contract)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"SkillData sparse composition failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"],
                      "summary": result["summary"],
                      "outcomes": result["outcomes"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
