from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "webui" / "src" / "features" / "audio" / "index.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for WebUI JavaScript tests")
class AudioSceneCatalogContractTests(unittest.TestCase):
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

    def test_view_model_filters_scene_mission_and_event_and_preserves_partial_status(self) -> None:
        source = AUDIO.read_text(encoding="utf-8")
        body = source.split("  function buildSceneCatalogViewModel", 1)[1].split(
            "\n  function sceneEventButton", 1
        )[0]
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const normalize = (value) => String(value ?? "").trim();
const normalizeLower = (value) => normalize(value).toLowerCase();
const asArray = (value) => Array.isArray(value) ? value : (value === undefined || value === null || value === "" ? [] : [value]);
function buildSceneCatalogViewModel{body}
const catalog = {{
  status: "validatedPartialPublishedObjectIndex",
  counts: {{catalogScenes: 2}},
  sourceDiagnostics: [{{source: "StreamingAssets", status: "missingPublishedObjectIndex", diagnostic: "missing"}}],
  scenes: [
    {{sceneId: "map01_lv001", audioLevel: {{events: [{{eventId: "au_music_tundra", role: "levelInitEvent"}}]}}, missionRefs: [{{missionId: "m1m6"}}]}},
    {{sceneId: "map02_lv008", audioLevel: {{events: [{{eventId: "hashed-event:0x1234"}}]}}, missionRefs: []}},
  ],
  sceneEmitters: [{{sceneOwnershipStatus: "prefabLocalNotSceneContained"}}],
}};
let view = buildSceneCatalogViewModel(catalog, "m1m6");
assert.equal(view.partial, true);
assert.deepEqual(view.scenes.map((row) => row.scene.sceneId), ["map01_lv001"]);
assert.equal(view.emitters.length, 1);
view = buildSceneCatalogViewModel(catalog, "0x1234");
assert.deepEqual(view.scenes.map((row) => row.scene.sceneId), ["map02_lv008"]);
view = buildSceneCatalogViewModel(catalog, "music tundra");
assert.deepEqual(view.scenes.map((row) => row.scene.sceneId), ["map01_lv001"]);
view = buildSceneCatalogViewModel({{
  status: "validatedPublishedObjectIndex",
  scenes: [
    {{sceneId: "empty", audioLevel: {{events: []}}, missionRefs: []}},
    {{sceneId: "useful", audioLevel: {{events: [{{eventId: "au_useful"}}]}}, missionRefs: []}},
  ],
}});
assert.equal(view.partial, false);
assert.equal(view.unavailable, false);
assert.deepEqual(view.scenes.map((row) => row.scene.sceneId), ["useful", "empty"]);
"""
        )

    def test_catalog_is_loaded_source_locally_and_event_links_reuse_existing_detail(self) -> None:
        source = AUDIO.read_text(encoding="utf-8")
        self.assertIn("audio/scene_backgrounds.json", source)
        self.assertIn("state.sceneCatalog = await loadSceneCatalog(nextLanguage, token);", source)
        self.assertIn("if (state.sceneCatalog) panel.appendChild(sceneCatalogSection(state.sceneCatalog));", source)
        self.assertIn('(state.datasets.events || []).find((candidate)', source)
        self.assertIn('row.sceneOwnershipStatus || "unresolved"', source)
        self.assertIn("no level ownership is claimed", source)
        self.assertNotIn("possibleMedia", source.split("  function sceneCatalogSection", 1)[1].split("\n  function hircInventorySection", 1)[0])


if __name__ == "__main__":
    unittest.main()
