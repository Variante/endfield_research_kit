from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "webui" / "src" / "features" / "story_triggers.js"
APP = ROOT / "webui" / "app.js"
APP_TREE = ROOT / "webui" / "app_tree.js"
MISSION_PIPELINE = ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for WebUI JavaScript tests")
class StoryTriggerWebUiTests(unittest.TestCase):
    def run_node(self, source: str) -> None:
        completed = subprocess.run(
            ["node", "-e", source],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"Node test failed:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}",
        )

    def test_exact_native_path_is_the_primary_playback_trigger(self) -> None:
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const triggers = require({str(MODULE)!r});
const manifest = {{
  dlg_test_1: {{
    routes: [
      {{
        storyKey: "dlg_test_1",
        causality: "condition",
        missionId: "test",
        steps: [{{kind: "story", id: "dlg_test_1"}}, {{kind: "quest", id: "test_q1"}}],
      }},
      {{
        storyKey: "dlg_test_1",
        causality: "context",
        missionId: "test",
        nativePaths: [{{
          eventName: "ScriptEvent_OnLeaderEnterTriggerVolume",
          eventSummary: "leader enters trigger slot 7",
          steps: [{{actionName: "StartDialogAction"}}],
        }}],
      }},
    ],
  }},
}};
const view = triggers.triggerView(manifest, "dlg_test_1");
assert.equal(view.category, "native_playback");
assert.equal(view.hasProvenPlayback, true);
assert.equal(view.routes[0].causality, "context");
assert.deepEqual(triggers.compactTrigger(view), {{
  category: "native_playback",
  event: "leader enters trigger slot 7",
  eventName: "ScriptEvent_OnLeaderEnterTriggerVolume",
  actions: ["StartDialogAction"],
  owner: "test",
  pathCount: 1,
}});
"""
        )

    def test_non_playback_relations_remain_explicitly_non_playback(self) -> None:
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const triggers = require({str(MODULE)!r});
const manifest = {{
  condition: {{routes: [{{storyKey: "condition", causality: "condition"}}]}},
  context: {{routes: [{{storyKey: "context", causality: "context"}}]}},
  unresolvedContext: {{routes: [{{storyKey: "unresolvedContext", causality: "context_owner_unresolved"}}]}},
  dependency: {{routes: [{{storyKey: "dependency", causality: "dependency"}}]}},
  definition: {{attachmentStatus: "definition_only_no_consumer", routes: []}},
  exhausted: {{
    attachmentStatus: "unlinked_no_trigger_route",
    offlineRecovery: {{graphEffect: "none", evidenceKind: "fixture_boundary"}},
    routes: [],
  }},
  mismatch: {{routes: [{{storyKey: "somewhere_else", causality: "playback"}}]}},
}};
for (const [key, category] of [
  ["condition", "condition"],
  ["context", "context"],
  ["unresolvedContext", "context_owner_unresolved"],
  ["dependency", "dependency"],
  ["definition", "definition_only"],
  ["exhausted", "offline_exhausted"],
  ["mismatch", "unknown"],
  ["missing", "unknown"],
]) {{
  const view = triggers.triggerView(manifest, key);
  assert.equal(view.category, category, key);
  assert.equal(view.hasProvenPlayback, false, key);
}}
"""
        )

    def test_trigger_manifest_and_surfaces_are_debug_only(self) -> None:
        app_source = APP.read_text(encoding="utf-8")
        app_tree_source = APP_TREE.read_text(encoding="utf-8")
        language_switch = app_source.split(
            "async function switchLanguage(",
            1,
        )[1].split("\nfunction ", 1)[0]

        self.assertNotIn("loadStoryTriggerManifest(", language_switch)
        self.assertNotIn(
            "ensureStoryTriggerManifestForDebug(",
            language_switch,
        )
        self.assertIn(
            "coverage.offlineRecoveryEvidence.storyTriggerManifestOverlay",
            app_source,
        )
        self.assertIn(
            "const triggerSummary = STATE.showDebug "
            "? storyTriggerCompactText(e.k) : null;",
            app_source,
        )
        self.assertIn(
            "if (!STATE.showDebug) {\n"
            "    slot.hidden = true;\n"
            "    return;\n"
            "  }",
            app_source,
        )
        self.assertIn(
            "if (next && typeof ensureStoryTriggerManifestForDebug",
            app_tree_source,
        )
        self.assertIn(
            "if (typeof rebuildTree === \"function\") "
            "rebuildTree({ resetScroll: false });",
            app_tree_source,
        )

    def test_mission_pipeline_surfaces_native_producer_and_attached_files(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("route.nativeCinematicProducerRoutes", source)
        self.assertIn('t("cinematicProducer")', source)
        self.assertIn("nativeCinematicProducerRouteAttachments", source)
        self.assertIn("route.sourceFiles", source)

    def test_mission_pipeline_surfaces_property_contract_as_non_ordering_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.authoredPropertyContract", source)
        self.assertIn('t("missionObservedProperty")', source)
        self.assertIn("consumer.propertyKeys", source)
        self.assertIn("They do not identify the writer, Story owner, or scene-file order.", source)

    def test_mission_pipeline_surfaces_exact_active_phase_receivers(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.activePhaseReceiverControl", source)
        self.assertIn('t("binaryActivePhaseReceiver")', source)
        self.assertIn("Setup → ActiveBegin → Active(", source)
        self.assertIn("not who selected public Active", source)

    def test_mission_pipeline_surfaces_exact_client_active_request_selector(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.clientActiveRequestControl", source)
        self.assertIn('t("binaryClientActiveRequest")', source)
        self.assertIn("clientActiveRequestControl.runtimePath", source)
        self.assertIn("who supplied Enabled", source)
        self.assertIn('t("binaryActiveVolume")', source)
        self.assertIn("clientActiveRequestControl.activeShapeList?.shapes", source)
        self.assertIn("validated_runtime_position_dependent", source)
        self.assertIn("shape.position", source)
        self.assertIn("shape.eulerAngles", source)
