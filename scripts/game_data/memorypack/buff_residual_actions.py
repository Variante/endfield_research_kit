"""Current-build BuffData action additions kept outside frozen SkillData readers.

``_ResidualReader`` extends the anonymous ``buff_actions.Reader`` with union
routes that the selected Buff action dispatcher authenticates in
``buff_residual_actions_native.json`` and the frontier contracts loaded by
``scripts.game_data.buff_frontiers_native``. Tag meanings are local to the
Buff dispatcher; none is borrowed from SkillData or LevelScript, because a
numeric match across union families is not a layout (the same number can
select a different wrapper and member count elsewhere).

Routes in ``buff_residual_actions_native.json`` (every wrapper reads the
inherited action prefix first: byte, scalar32, scalar32, scalar32):

- ``ReturnFalseAction``: fieldless; four-member base body.
- ``ModifyPartsDamageRatio`` and ``ModifyPartsPoiseRatio``:
  seven members; one bounded ``BlackboardDouble`` profile, one bounded
  ``GameplayTagQuery`` and a terminal byte. The two wrappers reverse the
  order of the nested profiles, in accord with their generated setters and
  selected readers.
- ``MoveTickAction``: seven members; bounded ``TargetSettings``,
  ``SequenceActionData`` and ``BlackboardDouble`` in generated setter order,
  with fail-closed recursion for unknown child actions.
- ``PassiveJumpAction.Data``: sixteen members.
- ``CheckPartTagMatch``: target then tag query.
- ``ChangeMoveGaitMultiplier``: nine members, three of them
  ``SerializeFieldDictionary<GroundedMoveGait, float>``. A non-null
  dictionary has a one-member object header, a signed count and fixed
  enum/float pairs (``gait_multiplier_map``); it is not framed like a bare
  ``Dictionary``.
- ``CheckMoveSpeed``: seven members; a direct compare scalar,
  ``BlackboardDouble`` and ``TargetSettings``.
- ``IgnoreModelIntervalCheck``: four-member base body.

The frontier contracts add the base-only, six-member, residual-twelve and
final nineteen routes described in ``buff_frontiers_native``. The
``frontier9_counts`` table in ``_action`` carries the member counts of the
final frontier. Tags are keyed by wrapper name; a tag of 255 is read only with extended width
(``FA FF 00``); a one-byte ``FF`` stays the null-union sentinel, and a null
wrapper (``FF`` after the tag) is a separate state.

Both direction-angle actions read ``clampToXZ`` at serialized member 4,
before their first direction/compare enum. The selected native reader calls
the same one-byte primitive as ``isEnable`` (byte load, cursor increment,
nonzero normalization); declaration order is not serialized order.

``root_continuation`` retries the frozen members 1-5 reader with these
routes only when the base reader stopped. ``frame_buff_named_middle`` retries
the named middle only when the ``damageModifier`` list reaches a tag declared
by one of the reviewed contracts (every contract must match the selected
input set); it then splices the recovered list back in front of the base
middle reader and requires that reader to reach the ``id`` marker. This is
how the ``ReturnFalseAction`` and ``CheckTwoDirectionAngle`` condition
routes inside damage-modifier condition sequences rejoin the middle.
``_close_icon_config`` then replaces the older named-opaque ``iconConfig``
range with the exact ``buff_icon_config`` cursor.

Evidence tier: the routes are ``exact`` stored member counts and read order
for the pinned build and ``direct`` cursor advance in the reached files. The
results stay ``structuralOnly`` (``wholeSchemaExact`` is always false here):
they do not prove runtime action behavior, enum or scalar meaning, live
provider choice, or whole-BuffData ownership. Unsupported nested bodies stay
opaque even inside a closed outer frame.
"""
from __future__ import annotations

import copy
import struct
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR

from scripts.game_data.memorypack.buff import frame_buff_named_middle as _base_named_middle
from scripts.game_data.memorypack.buff import _ability_action_tag as _A
from scripts.game_data.levelscript_union_tags import short_name
from scripts.game_data.memorypack.buff_icon_config import decode_icon_config
from scripts.game_data.memorypack.buff_enable_move_collider import decode_enable_move_collider_action
from scripts.game_data.memorypack.buff_actions import (
    FrameError,
    Reader as _BaseReader,
    Unsupported,
    root_continuation as _base_root_continuation,
)
from scripts.game_data import buff_frontiers_native as buff_frontiers


CONTRACT_PATH = CONTRACTS_DIR / "buff_residual_actions_native.json"
LABEL = "buffResidualActions"


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-residual-action-native-contract.v1", label=LABEL
    )
    return value


def _residual_routes_gate() -> dict[str, str]:
    """Whether the residual and frontier tags describe the selected build.

    ``_ResidualReader`` dispatches on the union tags those contracts record,
    and union tags are ordinals that shift between builds. Off the pinned
    build the routes are withheld, so a shifted tag is never read with
    another wrapper's member count and field order.
    """
    contracts = [(CONTRACT_PATH.name, _contract())]
    contracts += [(spec.file, buff_frontiers.reviewed_contract(name)) for name, spec in buff_frontiers.FRONTIERS.items()]
    for name, contract in contracts:
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["GameAssembly.dll"], inputs["global-metadata.dat"])
        if gate.status != NATIVE_EVIDENCE_VALIDATED:
            return {"status": gate.status, "contract": name, "detail": gate.detail}
    return {"status": NATIVE_EVIDENCE_VALIDATED, "contract": "", "detail": ""}


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the supplemental rows against the installed exact build."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    validated = []
    for action in contract["actions"]:
        image.validate_dispatcher(action, label=LABEL)
        for row in action["methods"]:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(action["codeWindows"], label=LABEL)
        for context in action.get("nestedContextUsage", []):
            image.nested_usage_cell(context, label=LABEL)
        validated.append(action["unionTag"])
    return {"status": "validated", "unionTags": validated, "nativeInputs": contract["nativeInputs"]}


class _ResidualReader(_BaseReader):
    """Add reviewed exact-build and selected native BuffData union routes."""

    def gait_multiplier_map(self) -> None:
        """Read SerializeFieldDictionary<GroundedMoveGait, float>."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-gait-multiplier-map")
        else:
            self.header(1)
            for _ in range(self.count(8)):
                self.take(4, "anonymous-grounded-move-gait")
                self.take(4, "anonymous-float32")
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-gait-multiplier-map",
        })

    def string_list(self, *, reserve: int = 0) -> None:
        """Read a nullable direct List<string> with bounded element payloads."""
        start = self.pos
        count = self.count(4, reserve=reserve, nullable=True)
        for _ in range(max(0, count)):
            self.byte_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-string-list",
        })

    def attribute_override_list(self) -> None:
        """Read List<OverrideRawAttributeAction.AttributeOverrideEntry>."""
        start = self.pos
        for _ in range(max(0, self.count(1, nullable=True))):
            if self.peek() == 0xFF:
                self.take(1, "null-attribute-override")
            else:
                self.header(2)
                self.take(4, "anonymous-enum32")
                self.scalar_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-attribute-override-list",
        })

    def buff_id_list(self, *, reserve: int = 0) -> None:
        """Read List<BuffId>, retaining the nested one-member wrapper."""
        start = self.pos
        for _ in range(max(0, self.count(1, reserve=reserve, nullable=True))):
            if self.peek() == 0xFF:
                self.take(1, "null-buff-id")
            else:
                self.header(1)
                self.byte_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-buff-id-list",
        })

    def teleport_fix_distance_profile(self) -> None:
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-teleport-fix-distance")
        else:
            self.header(3)
            self.scalar_payload()
            self.take(1, "anonymous-byte")
            self.take(1, "anonymous-byte")
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-teleport-fix-distance"})

    def teleport_ranged_profile(self) -> None:
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-teleport-ranged")
        else:
            self.header(1)
            self.scalar_payload()
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-teleport-ranged"})

    def create_buff_input_profile(self) -> None:
        """Read the five-member CreateBuffActionInput derived wrapper."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-create-buff-input")
        else:
            self.header(5)
            self.take(1, "anonymous-byte")
            for _ in range(max(0, self.count(1, reserve=5, nullable=True))):
                self.assignment_profile()
            self.byte_payload()
            self.byte_payload()
            self.take(1, "anonymous-byte")
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-create-buff-input"})

    def smart_target_select_profile(self) -> None:
        """Read the four-member SmartTargetSelectSetting value wrapper."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-smart-target-select")
        else:
            self.header(4)
            self.finder_profile()
            self.buff_id_list(reserve=5)
            self.take(4, "anonymous-enum32")
            self.query_profile()
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-smart-target-select"})

    def blow_off_fields(self) -> None:
        """Read the ten serialized fields inherited by BlowOff-derived actions."""
        self.target_profile()
        self.scalar_payload()
        self.scalar_payload()
        self.take(4, "anonymous-enum32")
        self.direction_profile()
        self.scalar_payload()
        self.take(1, "anonymous-byte")
        self.take(1, "anonymous-byte")
        self.target_profile()
        self.scalar_payload()

    def _action(self, depth: int, tag: int, width: int) -> None:
        if tag == _A("Core_EnableMoveColliderAction_Data"):
            decode_enable_move_collider_action(self, tag, width)
            return
        frontier9_counts = {
            _A("Core_BlowOffEnemyAction_Data"): 14, _A("Core_Conditions_CheckTwoDirectionAngle_Data"): 13, _A("Core_CrushAction_Data"): 17, _A("Core_FinishBuffByTag_Data"): 12, _A("Core_FootStepChangeAction_FootStepChangeData"): 9,
            _A("Core_FractureAction_Data"): 15, _A("Core_HurtAnimAction_Data"): 10, _A("Core_ImmuneTextAction_Data"): 9, _A("Core_KnockDownAction_Data"): 13, _A("Core_LogAction_LogActionData"): 10,
            _A("Core_MarkInheritSkillCastIdOnNormalAttack_Data"): 4, _A("Core_OverrideCameraFollowAction_OverrideCameraFollowActionData"): 12, _A("Core_OverrideRawAttributeAction_Data"): 6, _A("Core_PreventBuffConsumeAction_Data"): 7, _A("Core_SaveTwoDirectionAngle_Data"): 12,
            _A("Core_SealAction_Data"): 11, _A("Core_TeleportPosSelectAction_Data"): 9, _A("Core_TemporaryUnlockAction_Data"): 8, _A("Core_TyphoeaArcheryTargetSelect_Data"): 11,
        }
        if tag in frontier9_counts:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(frontier9_counts[tag])
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            if tag == _A("Core_BlowOffEnemyAction_Data"):
                self.blow_off_fields()
            elif tag == _A("Core_Conditions_CheckTwoDirectionAngle_Data"):
                self.take(1, "clampToXZ")
                self.take(4, "anonymous-enum32")
                self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile()
                self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile(); self.scalar_payload()
            elif tag in (_A("Core_CrushAction_Data"), _A("Core_FractureAction_Data")):
                self.blow_off_fields()
                if tag == _A("Core_CrushAction_Data"):
                    self.scalar_payload()
                    self.take(1, "anonymous-byte")
                self.take(4, "anonymous-float32")
            elif tag == _A("Core_FinishBuffByTag_Data"):
                self.target_profile(); self.target_profile(); self.take(1, "anonymous-byte")
                self.scalar_payload(); self.target_profile(); self.take(1, "anonymous-byte")
                self.take(1, "anonymous-byte"); self.query_profile()
            elif tag == _A("Core_FootStepChangeAction_FootStepChangeData"):
                for _ in range(3):
                    self.take(1, "anonymous-byte")
                self.byte_payload(); self.target_profile()
            elif tag == _A("Core_HurtAnimAction_Data"):
                self.take(4, "anonymous-float32"); self.take(4, "anonymous-enum32")
                self.take(4, "anonymous-float32"); self.take(4, "anonymous-float32")
                self.take(4, "anonymous-int32"); self.target_profile()
            elif tag == _A("Core_ImmuneTextAction_Data"):
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-enum32")
                self.take(8, "anonymous-vector2"); self.target_profile(); self.byte_payload()
            elif tag == _A("Core_KnockDownAction_Data"):
                self.take(4, "anonymous-enum32"); self.scalar_payload(); self.direction_profile()
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-float32")
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile()
            elif tag == _A("Core_LogAction_LogActionData"):
                self.take(1, "anonymous-byte"); self.byte_payload(); self.take(1, "anonymous-byte")
                self.take(1, "anonymous-byte"); self.byte_payload(); self.take(1, "anonymous-byte")
            elif tag == _A("Core_MarkInheritSkillCastIdOnNormalAttack_Data"):
                pass
            elif tag == _A("Core_OverrideCameraFollowAction_OverrideCameraFollowActionData"):
                self.take(4, "anonymous-enum32"); self.scalar_payload()
                self.take(4, "anonymous-enum32")
                for _ in range(3):
                    self.scalar_payload()
                self.target_profile(); self.target_profile()
            elif tag == _A("Core_OverrideRawAttributeAction_Data"):
                self.attribute_override_list(); self.target_profile()
            elif tag == _A("Core_PreventBuffConsumeAction_Data"):
                self.buff_id_list(reserve=5); self.take(4, "anonymous-enum32"); self.query_profile()
            elif tag == _A("Core_SaveTwoDirectionAngle_Data"):
                self.take(1, "clampToXZ")
                self.take(4, "anonymous-enum32"); self.target_profile(); self.target_profile()
                self.take(4, "anonymous-enum32"); self.target_profile(); self.target_profile()
                self.byte_payload()
            elif tag == _A("Core_SealAction_Data"):
                self.target_profile(); self.byte_payload(); self.curve_profile(); self.scalar_payload()
                self.take(1, "anonymous-byte"); self.target_profile(); self.take(1, "anonymous-byte")
            elif tag == _A("Core_TeleportPosSelectAction_Data"):
                self.byte_payload(); self.teleport_fix_distance_profile(); self.teleport_ranged_profile()
                self.target_profile(); self.take(4, "anonymous-enum32")
            elif tag == _A("Core_TemporaryUnlockAction_Data"):
                self.take(1, "anonymous-byte"); self.take(1, "anonymous-byte")
                self.take(4, "anonymous-float32"); self.target_profile()
            elif tag == _A("Core_TyphoeaArcheryTargetSelect_Data"):
                self.take(1, "anonymous-byte"); self.scalar_payload(); self.scalar_payload()
                self.create_buff_input_profile(); self.scalar_payload()
                self.smart_target_select_profile(); self.scalar_payload()
            return
        if (tag == 0xFF and width == 1) or tag not in (
            _A("Core_BreakPassingSmallSceneObject_Data"), _A("Core_ChangeMoveGaitMultiplier_Data"), _A("Core_ChangePushBackDistanceFactor_Data"), _A("Core_CheckMoveSpeed_Data"), _A("Core_Conditions_CheckPartTagMatch_Data"), _A("Core_DisableRootMotionAction_Data"), _A("Core_IgnoreModelIntervalCheck_Data"), _A("Core_IntRollingStoneRepatriateAction_IntRollingStoneRepatriateActionData"),
            _A("Core_LockMainCharacterToggleAction_Data"), _A("Core_ModifyPartsDamageRatio_Data"), _A("Core_ModifyPartsPoiseRatio_Data"), _A("Core_MoveTickAction_Data"), _A("Core_OnPhysicalNoGuardStart_Data"), _A("Core_PassiveJumpAction_Data"), _A("Core_PausePoiseRecover_Data"), _A("Core_ReplaceAnimationShake_Data"),
            _A("Core_ReturnFalseAction_Data"), _A("Core_ShowComboSkillUI_Data"), _A("Core_TyphoeaArcheryBrainToggleRegisterAction_Data"), _A("Core_ObtainUspInNormalSkill_Data"), _A("Core_OverrideJumpAction_Data"), _A("Core_OverrideStateAnimationWithMontageAction_OverrideStateAnimationActionData"), _A("Core_SetAllowedDamageDecoMask_Data"), _A("Core_ShowTyphoeaHudHint_Data"),
            _A("Core_StoreAtbValue_Data"), _A("Core_StoreCurSkillExecuteFrame_Data"), _A("Core_UpdateGlobalContextTarget_Data"), _A("Core_AddDynamicNavmeshObstacle_Data"), _A("Core_AttackClickListenerAction_Data"), _A("Core_BombClearAction_BombClearActionData"), _A("Core_ChangeSkillType_Data"), _A("Core_ComboAction_Data"),
            _A("Core_Conditions_CheckDungeonCategory_Data"), _A("Core_ExtendBuffAction_Data"), _A("Core_GetPatrolTeleportPos_Data"), _A("Core_JumpToAction_Data"), _A("Core_OverrideMultiDashLimit_Data"), _A("Core_PatrolTeleportToCachePos_Data"), _A("Core_PickTargetAction_Data"),
        ):
            return super()._action(depth, tag, width)
        self.take(width, "union-tag")
        if self.peek() == 0xFF:
            self.take(1, "null-wrapper")
            return
        self.header(
            4 if tag in (_A("Core_BombClearAction_BombClearActionData"), _A("Core_PatrolTeleportToCachePos_Data"), _A("Core_BreakPassingSmallSceneObject_Data"), _A("Core_DisableRootMotionAction_Data"), _A("Core_IgnoreModelIntervalCheck_Data"), _A("Core_OnPhysicalNoGuardStart_Data"), _A("Core_ReturnFalseAction_Data"), _A("Core_ShowComboSkillUI_Data"))
            else 9 if tag == _A("Core_ChangeMoveGaitMultiplier_Data")
            else 16 if tag == _A("Core_PassiveJumpAction_Data")
            else 6 if tag == _A("Core_Conditions_CheckPartTagMatch_Data")
            else 6 if tag in (_A("Core_AddDynamicNavmeshObstacle_Data"), _A("Core_AttackClickListenerAction_Data"), _A("Core_ExtendBuffAction_Data"), _A("Core_GetPatrolTeleportPos_Data"), _A("Core_JumpToAction_Data"), _A("Core_OverrideMultiDashLimit_Data"),
                                  _A("Core_ObtainUspInNormalSkill_Data"), _A("Core_OverrideJumpAction_Data"), _A("Core_OverrideStateAnimationWithMontageAction_OverrideStateAnimationActionData"), _A("Core_SetAllowedDamageDecoMask_Data"), _A("Core_ShowTyphoeaHudHint_Data"), _A("Core_StoreAtbValue_Data"), _A("Core_StoreCurSkillExecuteFrame_Data"), _A("Core_UpdateGlobalContextTarget_Data"))
            else 5 if tag in (_A("Core_ChangePushBackDistanceFactor_Data"), _A("Core_IntRollingStoneRepatriateAction_IntRollingStoneRepatriateActionData"), _A("Core_LockMainCharacterToggleAction_Data"), _A("Core_PausePoiseRecover_Data"), _A("Core_ReplaceAnimationShake_Data"), _A("Core_TyphoeaArcheryBrainToggleRegisterAction_Data"))
            else 7
        )
        self.take(1, "anonymous-nonzero-byte")
        for _ in range(3):
            self.take(4, "anonymous-scalar32")
        if tag in (_A("Core_BombClearAction_BombClearActionData"), _A("Core_PatrolTeleportToCachePos_Data")):
            pass
        elif tag == _A("Core_AddDynamicNavmeshObstacle_Data"):
            self.string_list(reserve=1)
            self.target_profile()
        elif tag == _A("Core_AttackClickListenerAction_Data"):
            self.sequence(depth)
            self.take(1, "anonymous-byte")
        elif tag == _A("Core_ChangeSkillType_Data"):
            self.paired_payload()
            self.take(4, "anonymous-enum32")
            self.target_profile()
        elif tag == _A("Core_ComboAction_Data"):
            self.scalar_payload()
            self.scalar_payload()
            self.target_profile()
        elif tag == _A("Core_Conditions_CheckDungeonCategory_Data"):
            self.string_list(reserve=2)
            self.take(1, "anonymous-byte")
            self.take(1, "anonymous-byte")
        elif tag == _A("Core_ExtendBuffAction_Data"):
            self.target_profile()
            self.finder_profile()
        elif tag == _A("Core_GetPatrolTeleportPos_Data"):
            self.byte_payload()
            self.take(4, "anonymous-float32")
        elif tag == _A("Core_JumpToAction_Data"):
            self.sequence(depth)
            self.take(4, "anonymous-int32")
        elif tag == _A("Core_OverrideMultiDashLimit_Data"):
            self.scalar_payload()
            self.target_profile()
        elif tag == _A("Core_PickTargetAction_Data"):
            self.byte_payload()
            self.scalar_payload()
            self.target_profile()
        elif tag == _A("Core_ChangeMoveGaitMultiplier_Data"):
            self.gait_multiplier_map()
            self.take(4, "anonymous-float32")
            self.take(1, "anonymous-byte")
            self.gait_multiplier_map()
            self.gait_multiplier_map()
        elif tag == _A("Core_ChangePushBackDistanceFactor_Data"):
            self.scalar_payload()
        elif tag == _A("Core_CheckMoveSpeed_Data"):
            self.take(4, "anonymous-scalar32")
            self.scalar_payload()
            self.target_profile()
        elif tag == _A("Core_Conditions_CheckPartTagMatch_Data"):
            self.target_profile()
            self.query_profile()
        elif tag in (_A("Core_IntRollingStoneRepatriateAction_IntRollingStoneRepatriateActionData"), _A("Core_PausePoiseRecover_Data")):
            self.target_profile()
        elif tag in (_A("Core_LockMainCharacterToggleAction_Data"), _A("Core_TyphoeaArcheryBrainToggleRegisterAction_Data")):
            self.take(1, "anonymous-byte")
        elif tag == _A("Core_ModifyPartsDamageRatio_Data"):
            self.scalar_payload()
            self.query_profile()
            self.take(1, "anonymous-byte")
        elif tag == _A("Core_ModifyPartsPoiseRatio_Data"):
            self.query_profile()
            self.scalar_payload()
            self.take(1, "anonymous-byte")
        elif tag == _A("Core_MoveTickAction_Data"):
            self.target_profile()
            self.sequence(depth)
            self.scalar_payload()
        elif tag == _A("Core_PassiveJumpAction_Data"):
            for _ in range(7):
                self.scalar_payload()
            self.target_profile()
            for _ in range(3):
                self.take(1, "anonymous-nonzero-byte")
            self.scalar_payload()
        elif tag == _A("Core_ReplaceAnimationShake_Data"):
            self.byte_payload()
        elif tag == _A("Core_ObtainUspInNormalSkill_Data"):
            self.scalar_payload()
            self.target_profile()
        elif tag == _A("Core_OverrideJumpAction_Data"):
            self.buff_input_profile()
            self.take(4, "anonymous-enum32")
        elif tag == _A("Core_OverrideStateAnimationWithMontageAction_OverrideStateAnimationActionData"):
            self.byte_payload()
            self.take(4, "anonymous-int32")
        elif tag == _A("Core_SetAllowedDamageDecoMask_Data"):
            self.take(8, "anonymous-int64")
            self.target_profile()
        elif tag == _A("Core_ShowTyphoeaHudHint_Data"):
            self.byte_payload()
            self.byte_payload()
        elif tag == _A("Core_StoreAtbValue_Data"):
            self.take(4, "anonymous-enum32")
            self.byte_payload()
        elif tag == _A("Core_StoreCurSkillExecuteFrame_Data"):
            self.byte_payload()
            self.target_profile()
        elif tag == _A("Core_UpdateGlobalContextTarget_Data"):
            self.target_profile()
            self.byte_payload()


def root_continuation(
    data: bytes,
    *,
    source: str,
    start: int,
    limit: int | None = None,
) -> dict[str, Any]:
    """Retry the frozen root continuation with authenticated residual actions."""
    base = _base_root_continuation(data, source=source, start=start, limit=limit)
    if base.get("status") != "unsupported":
        return base
    gate = _residual_routes_gate()
    if gate["status"] != NATIVE_EVIDENCE_VALIDATED:
        return {**base, "nativeResidualGate": gate}

    reader = _ResidualReader(data, source, limit)
    if type(start) is not int or not 1 <= start <= reader.limit:
        raise FrameError(source, 0, "first-collection endpoint within read limit", start, "start-bounds")
    reader.pos = start
    status = "supported-prefix"
    diagnostic = None
    named_fields = []
    try:
        for index, name, read_field in (
            (1, "addingCooldown", reader.scalar_payload),
            (2, "applyTags", reader.raw_dword_array),
            (3, "attributeModifier", reader.modifier_collection_profile),
            (4, "blackboard", reader.data_pair_collection_profile),
            (5, "buffEventAction", reader.buff_action_map_collection_profile),
        ):
            field_start = reader.pos
            read_field()
            named_fields.append({
                "index": index,
                "name": name,
                "start": field_start,
                "end": reader.pos,
                "boundaryClass": "exact-cursor",
            })
    except Unsupported as exc:
        status, diagnostic = "unsupported", exc.diagnostic
    except FrameError as exc:
        status, diagnostic = "failed", exc.diagnostic
    cursor = start
    for span in reader.ranges:
        if span["start"] != cursor or not cursor < span["end"] <= reader.limit:
            raise FrameError(source, cursor, "contiguous bounded scalar ranges", span, "internal-range")
        cursor = span["end"]
    if cursor != reader.pos:
        raise FrameError(source, cursor, reader.pos, cursor, "internal-range")
    return {
        "status": status,
        "diagnostic": diagnostic,
        "startOffset": start,
        "consumedEnd": reader.pos,
        "readLimit": reader.limit,
        "ranges": reader.ranges,
        "completedRecords": reader.records,
        "namedFields": named_fields,
        "fieldOrderSource": "current generated BuffDataForMemoryPack setter order",
        "opaqueRemainderRange": [reader.pos, len(data)],
        "wholeSchemaExact": False,
        "evidenceLevel": "structural-only",
        "nativeResidualActionTags": [
            _A("Core_BreakPassingSmallSceneObject_Data"), _A("Core_ChangeMoveGaitMultiplier_Data"), _A("Core_ChangePushBackDistanceFactor_Data"), _A("Core_CheckMoveSpeed_Data"), _A("Core_Conditions_CheckPartTagMatch_Data"), _A("Core_DisableRootMotionAction_Data"), _A("Core_IgnoreModelIntervalCheck_Data"), _A("Core_IntRollingStoneRepatriateAction_IntRollingStoneRepatriateActionData"),
            _A("Core_LockMainCharacterToggleAction_Data"), _A("Core_ModifyPartsDamageRatio_Data"), _A("Core_ModifyPartsPoiseRatio_Data"), _A("Core_MoveTickAction_Data"), _A("Core_OnPhysicalNoGuardStart_Data"), _A("Core_PassiveJumpAction_Data"), _A("Core_PausePoiseRecover_Data"), _A("Core_ReplaceAnimationShake_Data"),
            _A("Core_ReturnFalseAction_Data"), _A("Core_ShowComboSkillUI_Data"), _A("Core_TyphoeaArcheryBrainToggleRegisterAction_Data"), _A("Core_ObtainUspInNormalSkill_Data"), _A("Core_OverrideJumpAction_Data"), _A("Core_OverrideStateAnimationWithMontageAction_OverrideStateAnimationActionData"), _A("Core_SetAllowedDamageDecoMask_Data"), _A("Core_ShowTyphoeaHudHint_Data"),
            _A("Core_StoreAtbValue_Data"), _A("Core_StoreCurSkillExecuteFrame_Data"), _A("Core_UpdateGlobalContextTarget_Data"), _A("Core_AddDynamicNavmeshObstacle_Data"), _A("Core_AttackClickListenerAction_Data"), _A("Core_BombClearAction_BombClearActionData"), _A("Core_ChangeSkillType_Data"), _A("Core_ComboAction_Data"),
            _A("Core_Conditions_CheckDungeonCategory_Data"), _A("Core_ExtendBuffAction_Data"), _A("Core_GetPatrolTeleportPos_Data"), _A("Core_JumpToAction_Data"), _A("Core_OverrideMultiDashLimit_Data"), _A("Core_PatrolTeleportToCachePos_Data"), _A("Core_PickTargetAction_Data"),
            _A("Core_BlowOffEnemyAction_Data"), _A("Core_Conditions_CheckTwoDirectionAngle_Data"), _A("Core_CrushAction_Data"), _A("Core_FinishBuffByTag_Data"), _A("Core_FootStepChangeAction_FootStepChangeData"), _A("Core_FractureAction_Data"), _A("Core_HurtAnimAction_Data"), _A("Core_ImmuneTextAction_Data"),
            _A("Core_KnockDownAction_Data"), _A("Core_LogAction_LogActionData"), _A("Core_MarkInheritSkillCastIdOnNormalAttack_Data"), _A("Core_OverrideCameraFollowAction_OverrideCameraFollowActionData"), _A("Core_OverrideRawAttributeAction_Data"), _A("Core_PreventBuffConsumeAction_Data"), _A("Core_SaveTwoDirectionAngle_Data"), _A("Core_SealAction_Data"),
            _A("Core_TeleportPosSelectAction_Data"), _A("Core_TemporaryUnlockAction_Data"), _A("Core_TyphoeaArcheryTargetSelect_Data"),
        ],
        "nativeResidualContract": CONTRACT_PATH.name,
        "nativeFrontierContracts": {name: spec.file for name, spec in buff_frontiers.FRONTIERS.items()},
        "boundary": (
            "Selected root members 2-6 after the independently supported first collection. "
            "Supplemental action routes require the exact input-set contract; later bytes remain opaque."
        ),
    }


def _shift_offsets(value: Any, *, pivot: int, delta: int, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _shift_offsets(v, pivot=pivot, delta=delta, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [_shift_offsets(v, pivot=pivot, delta=delta, key=key) for v in value]
    offset_keys = {"start", "end", "startOffset", "endOffset", "hardLimit", "consumedEnd", "readLimit"}
    if key in offset_keys and isinstance(value, int) and value >= pivot:
        return value + delta
    if key == "offset" and isinstance(value, str) and value.startswith("0x"):
        number = int(value, 16)
        return hex(number + delta) if number >= pivot else value
    return value


def frame_buff_named_middle(
    data: bytes,
    start: int,
    id_marker_offset: int,
) -> dict[str, Any]:
    """Close a middle containing an authenticated residual condition action."""
    base = _base_named_middle(data, start, id_marker_offset)
    if base.get("status") == "named-through-iconConfig":
        return _close_icon_config(
            base,
            data=data,
            id_marker_offset=id_marker_offset,
        )
    if _residual_routes_gate()["status"] != NATIVE_EVIDENCE_VALIDATED:
        return base
    contracts = (
        (_contract(), CONTRACT_PATH.name),
        *((buff_frontiers.reviewed_contract(name), spec.file) for name, spec in buff_frontiers.FRONTIERS.items()),
    )
    # Contract rows name their wrappers; the recorded ``unionTag`` ordinal is
    # build-locked, so the current tag is resolved by name (a placeholder on
    # an unvalidated build, which never matches a scanned tag).
    authenticated_tags = {
        _A(short_name(action["wrapperName"]))
        for contract, _ in contracts
        for action in contract.get("actions", [])
    }

    reader = _ResidualReader(data, "BuffData.damageModifier", id_marker_offset)
    reader.pos = start
    try:
        count = reader.damage_modifier_collection_profile()
    except (ValueError, IndexError, struct.error):
        return base
    reached_residual_tags = sorted({
        row["tag"]
        for row in reader.records
        if row.get("kind") == "union" and row.get("tag") in authenticated_tags
    })
    if not reached_residual_tags:
        return base
    damage_end = reader.pos

    replacement = struct.pack("<i", 0)
    synthetic = data[:start] + replacement + data[damage_end:]
    synthetic_id = id_marker_offset - (damage_end - start) + len(replacement)
    framed = _base_named_middle(synthetic, start, synthetic_id)
    if framed.get("status") != "named-through-iconConfig" or framed.get("consumedEnd") != synthetic_id:
        return base

    delta = damage_end - start - len(replacement)
    recovered = _shift_offsets(copy.deepcopy(framed), pivot=start + len(replacement), delta=delta)
    fields = recovered.get("namedFields", [])
    if not fields or fields[0].get("name") != "damageModifier":
        return base
    fields[0].update({"start": start, "end": damage_end, "count": count, "isNull": count == -1})
    recovered.update({
        "consumedEnd": id_marker_offset,
        "hardLimit": id_marker_offset,
        "nativeResidualActionTags": reached_residual_tags,
        "nativeResidualContract": CONTRACT_PATH.name,
        "nativeResidualContracts": [name for _, name in contracts],
    })
    return _close_icon_config(
        recovered,
        data=data,
        id_marker_offset=id_marker_offset,
    )


def _close_icon_config(
    framed: dict[str, Any],
    *,
    data: bytes,
    id_marker_offset: int,
) -> dict[str, Any]:
    """Replace the old named opaque icon range with its exact nested cursor."""
    fields = framed.get("namedFields")
    if not isinstance(fields, list) or not fields or fields[-1].get("name") != "iconConfig":
        raise ValueError("buffIconConfig.integration:missing-field-14")
    icon_field = fields[-1]
    decoded = decode_icon_config(
        data,
        icon_field["start"],
        id_marker_offset,
    )
    icon_field.update({
        "end": decoded["consumedEnd"],
        "boundaryClass": "exact-cursor",
        "memberCount": decoded["memberCount"],
        "isNull": decoded["isNull"],
        "decoded": decoded,
    })
    framed["opaqueNestedRanges"] = []
    framed["iconConfigStatus"] = "exact"
    framed["iconConfigContract"] = "buff_icon_config_native.json"
    framed["boundary"] = (
        "Fields 6-14 advance exact cursors under the current generated wrapper order; "
        "the exact iconConfig cursor ends at the independently accepted id marker."
    )
    return framed
