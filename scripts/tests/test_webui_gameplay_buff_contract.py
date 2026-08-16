from __future__ import annotations

import json
import shutil
import subprocess
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
        self.assertIn('renderEvidenceBadge("recoveryExact", "buffAttributeModifierBoundary")', source)
        self.assertIn('renderEvidenceBadge("recoveryExact", "buffAppliedTagBoundary")', source)
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

    def test_gameplay_evidence_uses_compact_status_and_collapsed_guidance(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")

        self.assertIn("function renderEvidenceBadge", source)
        self.assertIn('class="gameplay-guidance gameplay-buff-guidance"', source)
        self.assertIn('class="gameplay-guidance"', source)
        self.assertIn("recoveryExact:", labels)
        self.assertIn("recoveryPartial:", labels)
        self.assertIn("recoveryUnavailable:", labels)
        self.assertIn("recoveryStructured:", labels)
        self.assertIn("buffEvidenceHelp:", labels)
        self.assertIn("projectileCoverageHelp:", labels)

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
        self.assertIn('settings.status !== "exact"', source)
        self.assertIn("buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial)", source)
        self.assertIn("buffTargetSettingsSummary(decoded.calculationTarget)", source)
        self.assertIn("buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial)", source)

    def test_partial_action_coverage_does_not_use_html_presence_for_exact_boundary(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")
        self.assertIn("const buffActionSummaryByDecoded = new WeakMap()", source)
        self.assertIn("const coverage = { exact: 0, partial: 0, unresolved: 0, total: 0 }", source)
        self.assertIn("return { html: groups.join(\"\"), coverage }", source)
        self.assertIn('actionCoverage.partial === 0', source)
        self.assertIn('actionBoundaryKey =', source)
        self.assertIn('"buffAbilityEventActionPartialBoundary"', source)
        self.assertIn("buffAbilityEventActionPartialBoundary:", labels)

    def test_partial_action_fallback_if_else_and_candidate_wording_are_visible(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        labels = LABELS.read_text(encoding="utf-8")
        self.assertIn("if (rows.length === rowStart && !isExactIfElse)", source)
        self.assertIn("buffActionIfElsePartial", source)
        self.assertIn("buffActionConfiguredCandidate", source)
        self.assertIn("buffActionRecoveredBuffIds", source)
        self.assertIn('decoded.semanticStatus === "exact-obtain-atb-type-condition"', source)
        self.assertIn("buffActionCheckObtainAtbType:", labels)
        self.assertIn("buffActionConfiguredCandidate:", labels)
        self.assertIn("buffActionRecoveredBuffIds:", labels)

    def test_partial_action_debug_details_are_bounded_and_source_is_debug_only(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        technical = source.split("function renderBuffActionTechnical", 1)[1].split(
            "\n  function buffDecodedActions", 1
        )[0]
        self.assertIn("STATE.showDebug", technical)
        self.assertIn("buffActionDebugStats", technical)
        self.assertNotIn("rawHex", technical)
        self.assertIn('STATE.showDebug && record.source?.path', source)

    def test_runtime_gameplay_action_fixture_covers_status_branches_and_escaping(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required for the Gameplay render fixture")
        source_path = json.dumps(str(GAMEPLAY))
        script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({source_path}, "utf8");
const passthroughTexts = new Proxy({{}}, {{ get: (_, key) => String(key) }});
const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (ch) => ({{
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '\"': "&quot;", "'": "&#39;"
}}[ch]));
const WebUI = {{
  gameplayTexts: {{ zh: passthroughTexts, en: passthroughTexts }},
  $: () => null,
  applyTemplate: (value) => value,
  escapeHtml,
  fetchWithProgress: () => Promise.reject(new Error("fixture")),
  formatNumber: (value) => String(value),
  normalizeUiLocale: (value) => value || "zh",
  parseQuery: () => ({{}}),
  queryScore: () => 0,
  highlightRegex: () => null,
  storageGet: () => null,
  storageSet: () => {{}},
}};
const document = {{
  readyState: "loading",
  body: {{ classList: {{ contains: () => false }} }},
  addEventListener: () => {{}},
}};
const window = {{ WebUI }};
const context = {{ window, document, console, URL, location: {{ hash: "" }}, setTimeout, clearTimeout }};
const marker = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);';
const injected = source.replace(marker, `window.__gameplayTest = {{
  renderBuffAbilityEventActions,
  renderBuffCard,
  state: STATE,
}};\\n${{marker}}`);
vm.runInNewContext(injected, context);
const api = window.__gameplayTest;
const item = (decoded, status) => ({{
  tag: "<tag>", name: decoded.type || "<unknown>", memberCount: 3,
  offset: "0x1", bytes: 7, decodeStatus: status || decoded.decodeStatus,
  decoded,
}});
const exactObtain = () => ({{
  type: "Obtain<ATB>", decodeStatus: "exact",
  semanticStatus: "exact-obtain-atb-type-condition",
  checkObtainMethod: true, obtainMethodList: [0],
  checkObtainType: true, obtainTypeList: [3],
}});
const exactIfElse = item({{
  type: "Core_IfElseAction_IfElseActionData", decodeStatus: "exact",
  semanticStatus: "exact-if-else-action",
  conditionAction: {{ actionDataItems: [item(exactObtain())] }},
  failActions: {{ actionDataItems: [item(exactObtain())] }},
  succeedActions: {{ actionDataItems: [item(exactObtain())] }},
}});
const partialIfElse = item({{
  type: "Core_IfElseAction_IfElseActionData", decodeStatus: "partial",
  semanticStatus: "partial-nested-action-payloads-and-target-settings-opaque",
  conditionAction: {{ actionDataItems: [item(exactObtain())] }},
  failActions: {{ actionDataItems: [] }},
  succeedActions: {{ actionDataItems: [] }},
}});
const unknown = item({{ type: "Unknown<\\u003cAction\\u003e" }});
const partialFallback = item({{
  type: "Partial<Payload>", decodeStatus: "partial",
  semanticStatus: "partial-unregistered-action",
  rawSha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  rawHex: "deadbeef",
}});
const record = {{
  evidenceStatus: "exact", source: {{ path: "source<fixture>.json" }},
  lifeType: {{ name: "Infinity" }}, stacking: {{ stackingTypeName: "Unique", identifierTypeName: "Id" }},
  flags: {{}}, refs: [], bornBuffs: [], abilityEventActionCount: 1,
  abilityEventActions: [{{ abilityEvent: 1, actions: [{{ actionDataItems: [exactIfElse, partialIfElse, partialFallback, unknown] }}] }}],
}};
const exactRecord = {{
  evidenceStatus: "exact", source: {{ path: "exact<fixture>.json" }},
  lifeType: {{ name: "Infinity" }}, stacking: {{ stackingTypeName: "Unique", identifierTypeName: "Id" }},
  flags: {{}}, refs: [], bornBuffs: [], abilityEventActionCount: 1,
  abilityEventActions: [{{ abilityEvent: 1, actions: [{{ actionDataItems: [item(exactObtain())] }}] }}],
}};
const zeroRecord = {{
  evidenceStatus: "exact", source: {{ path: "zero<fixture>.json" }},
  lifeType: {{ name: "Infinity" }}, stacking: {{ stackingTypeName: "Unique", identifierTypeName: "Id" }},
  flags: {{}}, refs: [], bornBuffs: [], abilityEventActionCount: 0,
  abilityEventActions: [{{ abilityEvent: 1, actions: [] }}],
}};
const exactEmptyIfElse = item({{
  type: "Core_IfElseAction_IfElseActionData", decodeStatus: "exact",
  semanticStatus: "exact-if-else-action",
  conditionAction: {{ actionDataItems: [] }},
  failActions: {{ actionDataItems: [] }},
  succeedActions: {{ actionDataItems: [] }},
}});
api.state.showDebug = false;
const normalActions = api.renderBuffAbilityEventActions(record);
const emptyIfElseActions = api.renderBuffAbilityEventActions({{ abilityEventActions: [{{ abilityEvent: 1, actions: [{{ actionDataItems: [exactEmptyIfElse] }}] }}] }});
api.state.index = {{ buffs: {{ fixture: record, exact: exactRecord, zero: zeroRecord }} }};
const normalCardWithIndex = api.renderBuffCard("fixture", false);
const exactCard = api.renderBuffCard("exact", false);
const zeroCard = api.renderBuffCard("zero", false);
api.state.showDebug = true;
const debugActions = api.renderBuffAbilityEventActions(record);
const debugCard = api.renderBuffCard("fixture", false);
console.log(JSON.stringify({{
  normalCoverage: normalActions.coverage,
  normalHtml: normalActions.html,
  emptyIfElseHtml: emptyIfElseActions.html,
  normalCard: normalCardWithIndex,
  exactCard,
  zeroCard,
  debugHtml: debugActions.html,
  debugCard,
}}));
"""
        result = subprocess.run(
            [node, "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual({"exact": 5, "partial": 2, "unresolved": 1, "total": 8}, payload["normalCoverage"])
        self.assertEqual(1, payload["normalHtml"].count("buffActionUnresolvedPayload"))
        self.assertIn("buffActionIfElsePartial", payload["normalHtml"])
        self.assertIn("buffActionPartialMarker", payload["normalHtml"])
        self.assertIn("buffActionIfElseExact", payload["emptyIfElseHtml"])
        self.assertNotIn("buffActionUnresolvedPayload", payload["emptyIfElseHtml"])
        self.assertIn("&lt;", payload["normalHtml"])
        self.assertNotIn("source&lt;fixture&gt;", payload["normalCard"])
        self.assertIn("buffAbilityEventActionPartialBoundary", payload["normalCard"])
        self.assertIn("buffAbilityEventActionExactBoundary", payload["exactCard"])
        self.assertIn("buffAbilityEventActionBoundary", payload["zeroCard"])
        self.assertIn("source&lt;fixture&gt;.json", payload["debugCard"])
        self.assertIn("buffActionTechnical", payload["debugHtml"])
        self.assertIn("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", payload["debugHtml"])
        self.assertNotIn("deadbeef", payload["debugHtml"])

    def test_modify_dynamic_blackboard_surfaces_calculation_type_and_operation(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        self.assertIn('"exact-modify-dynamic-blackboard-action"', source)
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
