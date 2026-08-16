from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.gameplay_builder.combat_relationships import PayloadBuilder, SCHEMA_VERSION

class CombatEnemyEvidenceTests(unittest.TestCase):
    def test_projectile_name_classification_keeps_exact_graph_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload = PayloadBuilder(
                "CN",
                {},
                temp / "missing.sqlite",
                "fixture graph disabled",
                temp / "missing-animestudio",
                0,
                0,
            )
            payload.graph_node = lambda node_id: {
                "id": node_id,
                "kind": "gameplay_effect",
                "label": "projectile_unit_fx",
                "_graphData": {},
            }

            payload.merge_graph_node("gameplay_effect:projectile_unit_fx")

            node = payload.nodes["gameplay_effect:projectile_unit_fx"]
            self.assertEqual("gameplay_effect", node["kind"])
            self.assertNotEqual("projectile_effect", node["kind"])
            self.assertEqual(
                {
                    "confidence": "inferred",
                    "basis": "identifier contains projectile, bullet, or missile",
                    "graphKind": "gameplay_effect",
                },
                node["classification"],
            )

    def test_projectile_identifier_edge_stays_inferred(self) -> None:
        class FixtureGraph:
            def execute(self, _query: str):
                return [("gameplay_effect:projectile_unit_fx", "projectile_unit_fx")]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload = PayloadBuilder(
                "CN",
                {},
                temp / "missing.sqlite",
                "fixture graph disabled",
                temp / "missing-animestudio",
                0,
                0,
            )
            payload.graph = FixtureGraph()
            payload.roots = ["character:char_test_unit"]
            payload.add_node("character:char_test_unit", "character", "Test unit")
            payload.graph_node = lambda node_id: {
                "id": node_id,
                "kind": "gameplay_effect",
                "label": "projectile_unit_fx",
                "_graphData": {},
            }

            payload.add_inferred_projectile_effects()

            node = payload.nodes["gameplay_effect:projectile_unit_fx"]
            self.assertEqual("gameplay_effect", node["kind"])
            edge = next(iter(payload.edges.values()))
            self.assertEqual("identifier_matches_projectile_effect", edge["type"])
            self.assertEqual("inferred", edge["confidence"])

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

        description = nodes["ability_description:ability_test"]
        self.assertEqual("ability_description", description["kind"])
        self.assertIn("executable SkillData not proven", description["semanticStatus"])
        self.assertEqual("ability_test", description["raw"]["descriptionId"])
        self.assertEqual("gameplay_skill:ability_test", description["raw"]["legacySkillNodeId"])
        description_edge = edges[("enemy:eny_test", "ability_description:ability_test", "has_ability_description")]
        self.assertEqual("direct", description_edge["confidence"])
        self.assertIn("does not prove an executable SkillData", description_edge["note"])
        self.assertNotIn("gameplay_skill:ability_test", nodes)

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

    def test_graph_edge_contract_accepts_only_expected_skill_edges(self) -> None:
        gameplay = {"entries": [{
            "id": "chr_test",
            "kind": "character",
            "title": "Test character",
            "skillGroups": [{"id": "group_test", "actionSkillIds": ["skill_test"]}],
        }]}
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            graph_path = temp / "graph.sqlite"
            connection = sqlite3.connect(graph_path)
            connection.executescript(
                """
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY, kind TEXT, name TEXT, source TEXT,
                    path TEXT, data TEXT
                );
                CREATE TABLE edges (
                    src TEXT, dst TEXT, kind TEXT, source TEXT,
                    evidence TEXT, data TEXT
                );
                """
            )
            nodes = [
                ("gameplay_skill:skill_test", "gameplay_skill", "skill_test"),
                ("gameplay_skill:other_skill", "gameplay_skill", "other_skill"),
                ("buff:buff_test", "buff", "buff_test"),
                ("buff:unknown_test", "buff", "unknown_test"),
                ("buff:buff_child", "buff", "buff_child"),
                ("actor:unrelated", "actor", "unrelated"),
            ]
            connection.executemany(
                "INSERT INTO nodes(id,kind,name,source,path,data) VALUES(?,?,?,?,?,?)",
                [(node_id, kind, name, "fixture", "fixture", "{}") for node_id, kind, name in nodes],
            )
            connection.executemany(
                "INSERT INTO edges(src,dst,kind,source,evidence,data) VALUES(?,?,?,?,?,?)",
                [
                    (
                        "actor:unrelated", "gameplay_skill:skill_test",
                        "actor_speaks_line", "fixture", "unrelated.edge", "{}",
                    ),
                    (
                        "gameplay_skill:skill_test", "gameplay_skill:skill_test",
                        "skill_data_defines_skill", "fixture", "known.ignored", "{}",
                    ),
                    (
                        "gameplay_skill:skill_test", "buff:buff_test",
                        "skill_data_references_buff", "fixture", "skill.buff", "{}",
                    ),
                    (
                        "gameplay_skill:skill_test", "buff:unknown_test",
                        "skill_data_unknown_runtime_relation", "fixture", "skill.unknown", "{}",
                    ),
                    (
                        "gameplay_skill:other_skill", "buff:buff_test",
                        "skill_data_references_effect", "fixture", "other.effect", "{}",
                    ),
                    (
                        "gameplay_skill:other_skill", "buff:unknown_test",
                        "skill_data_unrelated_unknown", "fixture", "other.unknown", "{}",
                    ),
                    (
                        "buff:buff_test", "buff:buff_child",
                        "buff_data_references_buff", "fixture", "buff.child", "{}",
                    ),
                    (
                        "buff:buff_test", "buff:unknown_test",
                        "buff_data_unknown_runtime_relation", "fixture", "buff.unknown", "{}",
                    ),
                ],
            )
            connection.commit()
            connection.close()

            payload = PayloadBuilder(
                "CN",
                gameplay,
                graph_path,
                "",
                temp / "missing-animestudio",
                0,
                0,
            ).payload()

        edges = {(edge["source"], edge["target"], edge["type"]): edge for edge in payload["edges"]}
        self.assertIn(
            ("gameplay_skill:skill_test", "buff:buff_test", "skill_data_references_buff"),
            edges,
        )
        self.assertEqual(
            "inferred",
            edges[("gameplay_skill:skill_test", "buff:buff_test", "skill_data_references_buff")]["confidence"],
        )
        self.assertNotIn(
            ("gameplay_skill:skill_test", "buff:unknown_test", "skill_data_unknown_runtime_relation"),
            edges,
        )
        self.assertEqual("partial", payload["graphEdgeContract"]["status"])
        self.assertEqual("reachable_skill_buff_config_edges", payload["graphEdgeContract"]["scope"])
        expected = payload["graphEdgeContract"]["expectedKinds"]
        self.assertEqual(1, expected["skill_data_references_buff"]["observed"])
        self.assertEqual(1, expected["skill_data_references_buff"]["accepted"])
        self.assertEqual("accepted", expected["skill_data_references_buff"]["status"])
        self.assertEqual("missing", expected["skill_data_references_effect"]["status"])
        self.assertEqual(1, expected["buff_data_references_buff"]["observed"])
        self.assertEqual(1, expected["buff_data_references_buff"]["accepted"])
        self.assertEqual(1, payload["graphEdgeContract"]["unexpectedKinds"]["skill_data_unknown_runtime_relation"])
        self.assertEqual(1, payload["graphEdgeContract"]["unexpectedKinds"]["buff_data_unknown_runtime_relation"])
        self.assertNotIn("skill_data_unrelated_unknown", payload["graphEdgeContract"]["unexpectedKinds"])
        self.assertEqual(2, payload["graphEdgeContract"]["unexpectedEdgeCount"])
        self.assertNotIn("actor_speaks_line", payload["graphEdgeContract"]["unexpectedKinds"])
        self.assertNotIn("skill_data_defines_skill", payload["graphEdgeContract"]["unexpectedKinds"])
        self.assertEqual(7, SCHEMA_VERSION)

    def test_missing_graph_reports_unavailable_edge_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload = PayloadBuilder(
                "CN",
                {"entries": []},
                temp / "missing.sqlite",
                "",
                temp / "missing-animestudio",
                0,
                0,
            ).payload()

        self.assertFalse(payload["graph"]["available"])
        self.assertEqual("unavailable", payload["graphEdgeContract"]["status"])
        self.assertEqual({}, payload["graphEdgeContract"]["unexpectedKinds"])


if __name__ == "__main__":
    unittest.main()
