from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GAMEPLAY = ROOT / "webui" / "src" / "features" / "gameplay" / "index.js"
LABELS = ROOT / "webui" / "src" / "features" / "gameplay" / "labels.js"


class GameplayBuffFrontendContractTests(unittest.TestCase):
    def test_skill_cooldown_is_positive_only_and_level_scoped(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        body = source.split("  function collectGroupLevelChips", 1)[1].split(
            "\n  function renderActiveSkillLevelPane", 1
        )[0]

        self.assertIn("const cooldown = Number(level.coolDown);", body)
        self.assertIn("Number.isFinite(cooldown) && cooldown > 0", body)
        self.assertIn('text("cooldown")', body)

    def test_enemy_buffs_render_semantics_with_visible_evidence_boundary(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("function renderBuffCards", source)
        self.assertIn("STATE.index?.buffs", source)
        self.assertIn('text("buffEvidenceBoundary")', source)
        self.assertIn('text("enemyModifierBoundary")', source)
        self.assertIn("buffEvidenceBoundary:", labels)
        self.assertIn("enemyModifierBoundary:", labels)

    def test_buff_exact_attribute_modifiers_and_tag_boundaries_are_visible(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("function buffAttributeModifierPairs", source)
        self.assertIn("function renderGameplayTagDetails", source)
        self.assertIn("record.applyTags", source)
        self.assertIn("tagDetails", source)
        self.assertIn("record.attributeModifier", source)
        self.assertIn('text("buffAttributeModifierBoundary")', source)
        self.assertIn('text("buffAppliedTagBoundary")', source)
        self.assertIn('text("gameplayTagContext")', source)
        self.assertIn('text("gameplayTagUnresolvedReason")', source)
        self.assertIn("item.unresolvedReason", source)
        self.assertIn('text("buffAbilityEventChain")', source)
        self.assertIn('"buffAbilityEventActionBoundary"', source)
        self.assertIn("buffAttributeModifierBoundary:", labels)
        self.assertIn("buffAppliedTagBoundary:", labels)
        self.assertIn("gameplayTagContext:", labels)
        self.assertIn("gameplayTagUnresolvedReason:", labels)
        self.assertIn("buffAbilityEventActionBoundary:", labels)

    def test_exact_buff_skill_cooldown_actions_are_rendered(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("function renderBuffAbilityEventActions", source)
        self.assertIn('decoded.semanticStatus === "exact-skill-cooldown-operation"', source)
        self.assertIn('text("buffActionReduceCooldown")', source)
        self.assertIn('"buffAbilityEventActionExactBoundary"', source)
        self.assertIn("buffActionReduceCooldown:", labels)
        self.assertIn("buffAbilityEventActionExactBoundary:", labels)
        self.assertIn("buffAbilityEventChain:", labels)

    def test_if_else_actions_keep_branch_context_in_visible_labels(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("buffActionBranchCondition", source)
        self.assertIn("buffActionBranchFail", source)
        self.assertIn("buffActionBranchSucceed", source)
        self.assertIn("buffActionBranchByDecoded", source)
        self.assertIn("activeBranch = buffActionBranchByDecoded.get(decoded) || \"\"", source)
        self.assertIn("rowsWithBranchContext", source)
        for label in (
            "buffActionBranchCondition:",
            "buffActionBranchFail:",
            "buffActionBranchSucceed:",
        ):
            self.assertIn(label, labels)

    def test_unknown_skill_cooldown_operation_does_not_default_to_reduce(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn('decoded.functionTypeName === "Set"', source)
        self.assertIn('decoded.functionTypeName === "Reduce"', source)
        self.assertIn('text("buffActionUnknownCooldown")', source)
        self.assertIn("decoded.functionTypeName ?? decoded.functionType", source)
        self.assertIn("buffActionUnknownCooldown:", labels)

    def test_action_boundary_text_does_not_claim_event_enum_validation(self) -> None:
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("Action-union tags, member counts, and byte boundaries", labels)
        self.assertNotIn("Event enums and action unions are checked", labels)

    def test_exact_buff_shield_and_super_armor_actions_are_rendered(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        for semantic_status in (
            "exact-super-armor-condition",
            "exact-create-timed-marker-action",
            "partial-create-buff-input-tail-and-target-settings-opaque",
            "exact-finish-buff-action",
        ):
            self.assertIn(semantic_status, source)
        for label in (
            "buffActionCheckSuperArmor:",
            "buffActionCreateTimedMarker:",
            "buffActionCreateBuff:",
            "buffActionFinishBuff:",
        ):
            self.assertIn(label, labels)

    def test_exact_buff_conditions_and_nested_branches_are_rendered(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("function buffDecodedActions", source)
        for branch_key in (
            "decoded.conditionAction",
            "decoded.failActions",
            "decoded.succeedActions",
        ):
            self.assertIn(branch_key, source)
        for semantic_status in (
            "exact-buff-stack-condition",
            "exact-hp-condition",
            "exact-damage-type-condition",
            "exact-global-cooldown-condition",
            "exact-add-global-cooldown-action",
            "exact-obtain-cost-action",
            "exact-cast-skill-action",
        ):
            self.assertIn(semantic_status, source)
        for label in (
            "buffActionCheckBuffStack:",
            "buffActionCheckHp:",
            "buffActionCheckDamageType:",
            "buffActionAddGlobalCooldown:",
            "buffActionObtainCost:",
            "buffActionCastSkill:",
        ):
            self.assertIn(label, labels)

    def test_partial_actions_surface_exact_target_settings_fields(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        self.assertIn("function buffTargetSettingsSummary", source)
        self.assertIn("buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial)", source)
        self.assertIn("buffTargetSettingsSummary(decoded.calculationTargetEnvelopePartial)", source)
        self.assertIn("buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial)", source)

    def test_modify_dynamic_blackboard_surfaces_calculation_type_and_operation(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        self.assertIn("decoded.calculateTypeName || formatValue(decoded.calculateType)", source)
        self.assertIn("[decoded.key, calculationType, operation, target]", source)

    def test_convert_to_target_context_surfaces_native_operation_names(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")
        self.assertIn("partial-convert-from-target-settings-envelope-opaque", source)
        self.assertIn("decoded.operationTypeName || formatValue(decoded.operationType)", source)
        self.assertIn("decoded.translateOperationName || formatValue(decoded.translateOperation)", source)
        self.assertIn("buffActionConvertTargetContext", source)
        self.assertIn("buffActionConvertTargetContext:", labels)

    def test_compare_float_actions_are_visible(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")
        self.assertIn('decoded.semanticStatus === "exact-compare-float-action"', source)
        self.assertIn("decoded.compareName || buffCompareLabel(decoded.compare)", source)
        self.assertIn("buffActionCompareBlackboard", source)
        self.assertIn("buffActionCompareBlackboard:", labels)

    def test_simple_blackboard_calculation_uses_decoded_operation_name(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        self.assertIn("decoded.operationName || formatValue(decoded.operation)", source)
        self.assertIn("blackboardValue(decoded.value1)} ${operation} ${blackboardValue(decoded.value2)", source)

    def test_spell_infliction_surfaces_element_name(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")
        self.assertIn('decoded.semanticStatus === "partial-source-target-settings-envelopes-opaque"', source)
        self.assertIn("decoded.inflictionTypeName || formatValue(decoded.inflictionType)", source)
        self.assertIn("buffActionSpellInfliction:", labels)


if __name__ == "__main__":
    unittest.main()
