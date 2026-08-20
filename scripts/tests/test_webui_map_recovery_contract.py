import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WebuiMapRecoveryContractTests(unittest.TestCase):
    def test_authored_quest_endpoints_use_original_surface_without_relation_webs(self):
        source = (ROOT / "webui/src/features/map_recovery/index.js").read_text(encoding="utf-8")
        style = (ROOT / "webui/src/features/map_recovery/style.css").read_text(encoding="utf-8")

        self.assertIn('endpointRoles.set(keyOf(ordered[0]), "start")', source)
        self.assertIn('endpointRoles.set(keyOf(ordered.at(-1))', source)
        self.assertNotIn("inferredEdges", source)
        self.assertNotIn("mr-edge", source)
        self.assertNotIn("data-map-relations", source)
        self.assertIn("--mr-sunken: #ffffff", style)
        self.assertIn("background: var(--mr-sunken)", style)
        self.assertNotIn(".mr-map.is-point-cloud", style)
        self.assertIn(".mr-quest.is-mission-start", style)
        self.assertIn(".mr-quest.is-mission-end", style)
        self.assertIn('t("streamingSource")', source)
        self.assertIn("node.streamingInstance.mesh?.name", source)
        self.assertIn("state.kinds = new Set();", source)


if __name__ == "__main__":
    unittest.main()
