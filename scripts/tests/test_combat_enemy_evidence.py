from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gameplay_builder.combat_relationships import PayloadBuilder


class CombatEnemyEvidenceTests(unittest.TestCase):
    def test_enemy_links_retain_variant_source_coordinates_and_semantics(self) -> None:
        gameplay = {"entries": [{
            "id": "eny_test",
            "kind": "enemy",
            "title": "Test enemy",
            "displaySource": {"table": "EnemyTemplateDisplayInfoTable.json", "id": "eny_test"},
            "abilities": [{"id": "ability_test", "name": "Test ability"}],
            "attributeTemplates": {
                "attr_test": {
                    "source": {"table": "EnemyAttributeTemplateTable.json", "id": "attr_test"},
                    "stats": {"pointCount": 3, "interpolated": False},
                },
            },
            "variants": [{
                "id": "eny_test_hard",
                "name": "Hard",
                "templateId": "eny_test",
                "attrTemplateId": "attr_test",
                "modelId": "model_test",
                "aiTemplateId": "ai_test",
                "bornBuffs": ["buff_test"],
                "source": {"table": "EnemyTable.json", "id": "eny_test_hard"},
            }],
        }]}
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload = PayloadBuilder(
                "CN",
                gameplay,
                temp / "missing.sqlite",
                "fixture graph disabled",
                temp / "missing-animestudio",
                0,
                0,
            ).payload()

        nodes = {node["id"]: node for node in payload["nodes"]}
        edges = {(edge["source"], edge["target"], edge["type"]): edge for edge in payload["edges"]}

        variant = nodes["enemy_variant:eny_test_hard"]
        self.assertEqual("exact authored EnemyTable row", variant["semanticStatus"])
        self.assertEqual(
            "eny_test_hard.attrTemplateId",
            edges[("enemy_variant:eny_test_hard", "enemy_attr_template:attr_test", "uses_attribute_template")]["evidence"]["path"],
        )
        self.assertEqual(
            "eny_test_hard.bornBuffs[0]",
            edges[("enemy_variant:eny_test_hard", "buff:buff_test", "starts_with_buff")]["evidence"]["path"],
        )
        self.assertEqual(3, nodes["enemy_attr_template:attr_test"]["raw"]["statPointCount"])


if __name__ == "__main__":
    unittest.main()
