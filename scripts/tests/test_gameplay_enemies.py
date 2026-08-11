from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gameplay_builder.base_data import build_enemy_entries, enemy_stat_curve_payload


def attribute_row(level: int | None, hp: float, atk: float, defense: float) -> dict:
    attrs = []
    if level is not None:
        attrs.append({"attrType": 0, "attrValue": level})
    attrs.extend((
        {"attrType": 1, "attrValue": hp},
        {"attrType": 2, "attrValue": atk},
        {"attrType": 3, "attrValue": defense},
    ))
    return {"Attribute": {"attrs": attrs}}


class GameplayEnemyTests(unittest.TestCase):
    def test_enemy_stats_keep_only_exact_authored_points(self) -> None:
        payload = enemy_stat_curve_payload({
            "templateId": "attr_test",
            "levelDependentAttributes": [
                attribute_row(1, 100, 20, 30),
                attribute_row(None, 999, 999, 999),
                attribute_row(5, 220, 44, 60),
            ],
        }, {})

        self.assertEqual([1, 5], [row["level"] for row in payload["rows"]])
        self.assertEqual(2, payload["pointCount"])
        self.assertFalse(payload["interpolated"])
        self.assertNotIn("checkpoints", payload)

    def test_variants_share_exact_attribute_templates_without_wiki_duplicates(self) -> None:
        tables = {
            "EnemyTable.json": {
                "eny_test": {"templateId": "eny_test", "attrTemplateId": "attr_a", "modelId": "model_a"},
                "eny_test_hard": {"templateId": "eny_test", "attrTemplateId": "attr_b", "modelId": "model_b"},
            },
            "EnemyAttributeTemplateTable.json": {
                "attr_a": {"templateId": "attr_a", "levelDependentAttributes": [attribute_row(1, 100, 20, 30)]},
                "attr_b": {"templateId": "attr_b", "levelDependentAttributes": [attribute_row(1, 200, 40, 60)]},
            },
            "EnemyDisplayInfoTable.json": {},
            "EnemyTemplateDisplayInfoTable.json": {},
            "DisplayEnemyTypeTable.json": {},
            "EnemyAbilityDescTable.json": {},
            "EnemyTagTable.json": {},
            "WikiEnemyDropTable.json": {},
            "ItemTable.json": {},
            "AttributeMetaTable.json": {},
        }

        entry = build_enemy_entries(
            tables,
            {},
            {},
            {"wiki_eny_test": "Test", "wiki_eny_test_hard": "Duplicate variant page"},
        )[0]

        self.assertEqual(["wiki_eny_test"], entry["storyWikiKeys"])
        self.assertTrue(all("storyWikiKey" not in variant for variant in entry["variants"]))
        self.assertEqual({"attr_a", "attr_b"}, set(entry["attributeTemplates"]))
        self.assertEqual(200, entry["attributeTemplates"]["attr_b"]["stats"]["rows"][0]["attrs"][0]["value"])


if __name__ == "__main__":
    unittest.main()
