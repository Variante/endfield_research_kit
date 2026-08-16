from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.gameplay_builder.base_data import (
    build_enemy_entries,
    collect_gameplay_buff_ids,
    enrich_buff_gameplay_tag_details,
    enrich_buff_native_action_names,
    enrich_buff_native_modifier_names,
    enemy_modifier_payload,
    enemy_stat_curve_payload,
    load_gameplay_tag_registry,
    load_native_gameplay_semantics,
    _load_runtime_gameplay_tag_names,
)


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
    def test_native_semantics_unexpected_parse_error_degrades_build(self) -> None:
        gate = SimpleNamespace(
            status="validated",
            detail="fixture",
            validated=True,
            metadata=Path("fixture-global-metadata.dat"),
        )
        helper_path = SimpleNamespace(is_file=lambda: True)
        with (
            patch("scripts.gameplay_builder.base_data.check_installed_native_inputs", return_value=gate),
            patch("scripts.gameplay_builder.base_data.NATIVE_METADATA_HELPER", helper_path),
            patch("scripts.gameplay_builder.base_data.il2cpp.load_metadata_helper", side_effect=KeyError("fixture-layout")),
        ):
            result = load_native_gameplay_semantics()

        self.assertEqual("parse-error", result["evidence"]["status"])
        self.assertIn("KeyError", result["evidence"]["detail"])

    def test_runtime_gameplay_tag_capture_is_hash_gated_and_keeps_exact_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            rows = [
                {
                    "kind": "session_start",
                    "gameBuild": "fixture",
                    "gameAssemblySha256": "a" * 64,
                    "metadataSha256": "b" * 64,
                },
                {"kind": "tag_mapping", "tagIdHex": "0xdeadbeef", "tagName": "Runtime/Test"},
                {"kind": "tag_mapping", "tagIdHex": "0xdeadbeef", "tagName": "Runtime/Test"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with patch(
                "scripts.gameplay_builder.base_data.check_installed_native_inputs",
                return_value=SimpleNamespace(status="validated", detail=""),
            ):
                names, sources, evidence = _load_runtime_gameplay_tag_names(path)
        self.assertEqual({"0xdeadbeef": ["Runtime/Test"]}, names)
        self.assertEqual("runtime-gameplay-tag-capture", sources[0]["kind"])
        self.assertEqual(1, evidence["mappingCount"])

    def test_predefined_gameplay_tag_names_are_exact_and_unknown_ids_stay_unresolved(self) -> None:
        if not Path("export_full").is_dir():
            self.skipTest("current export_full is required for the tag registry fixture")
        registry = load_gameplay_tag_registry(Path("export_full"))
        expected_status = (
            "exact-config-and-predefined"
            if registry["counts"].get("configTagNames")
            else "exact-predefined-partial"
        )
        self.assertEqual(expected_status, registry["status"])
        self.assertEqual("DamageImmuneByLevel", registry["tags"]["0x9a4868a1"]["name"])
        if registry["counts"].get("configTagNames"):
            self.assertEqual(2577, registry["configEvidence"]["serializedPathCount"])
            self.assertGreaterEqual(registry["configEvidence"]["matchedObjectCount"], 1)
            self.assertIn(
                "Skill/Character/chr_0004_pelica/PelicaTalent0",
                registry["tags"]["0x3f7bdd88"]["names"],
            )
            self.assertIn("Immune", registry["tags"]["0xa5e71f60"]["names"])

        record = {"applyTags": {"count": 2, "tagIds": ["0x9a4868a1", "0xdeadbeef"]}}
        enrich_buff_gameplay_tag_details(record, registry)
        details = record["applyTags"]["tagDetails"]
        self.assertEqual("exact-predefined", details[0]["evidenceStatus"])
        self.assertEqual("DamageImmuneByLevel", details[0]["name"])
        self.assertEqual("unresolved", details[1]["evidenceStatus"])
        self.assertEqual("0xdeadbeef", details[1]["id"])
        self.assertEqual("not-in-current-serialized-gameplay-tag-config", details[1]["unresolvedReason"])

    def test_buff_event_and_cooldown_names_require_gated_native_tables(self) -> None:
        record = {
            "abilityEventActions": [{
                "abilityEvent": 31,
                "actions": [{
                    "actionDataItems": [{
                        "decoded": {
                            "semanticStatus": "exact-skill-cooldown-operation",
                            "functionType": 0,
                            "skillTypeMask": 0,
                        },
                    }],
                }],
            }],
        }

        enrich_buff_native_action_names(record, {})
        event_map = record["abilityEventActions"][0]
        cooldown = event_map["actions"][0]["actionDataItems"][0]["decoded"]
        self.assertIsNone(event_map["abilityEventName"])
        self.assertIsNone(cooldown["functionTypeName"])

        enrich_buff_native_action_names(record, {
            "abilityEvents": {"31": "OnSkillEnd"},
            "skillCooldownFunctionTypes": {"0": "Reduce"},
            "skillTypeMasks": {"0": "None"},
        })
        self.assertEqual("OnSkillEnd", event_map["abilityEventName"])
        self.assertEqual("Reduce", cooldown["functionTypeName"])
        self.assertEqual("None", cooldown["skillTypeMaskName"])

    def test_buff_modifier_names_require_gated_native_tables(self) -> None:
        unresolved = {
            "attributeModifier": {
                "attributeModifiers": [{
                    "attributeType": 13,
                    "formulaItem": 4,
                    "modifyAttributeType": 0,
                }],
            },
        }
        enrich_buff_native_modifier_names(unresolved, {})
        modifier = unresolved["attributeModifier"]["attributeModifiers"][0]
        self.assertIsNone(modifier["attributeTypeName"])

        enrich_buff_native_modifier_names(unresolved, {
            "attributeTypes": {"13": "MoveSpeedScalar"},
            "modifierTypes": {"4": "FinalMultiplier"},
            "modifyAttributeTypes": {"0": "Specific"},
        })
        self.assertEqual("MoveSpeedScalar", modifier["attributeTypeName"])
        self.assertEqual("FinalMultiplier", modifier["formulaItemName"])
        self.assertEqual("Specific", modifier["modifyAttributeTypeName"])

    def test_gameplay_buff_ids_ignore_blackboard_keys_that_only_look_like_ids(self) -> None:
        payload = {
            "bornBuffs": ["buff_enemy_born"],
            "blackboard": [{"key": "buff_duration", "value": 5}],
            "effectRefs": [{"type": "buff", "id": "buff_talent"}],
            "actions": [{"buffId": "buff_item_use"}],
        }

        self.assertEqual(
            ["buff_enemy_born", "buff_item_use", "buff_talent"],
            collect_gameplay_buff_ids(payload),
        )

    def test_enemy_modifier_uses_only_gated_native_enum_names(self) -> None:
        source = [{
            "attrType": 1,
            "attrValue": -0.5,
            "modifierType": 1,
            "modifyAttributeType": 0,
        }]

        unresolved = enemy_modifier_payload(source, {})[0]
        resolved = enemy_modifier_payload(source, {}, {
            "modifierTypes": {"1": "Multiplier"},
            "modifyAttributeTypes": {"0": "Specific"},
        })[0]

        self.assertIsNone(unresolved["modifierTypeName"])
        self.assertEqual("Multiplier", resolved["modifierTypeName"])
        self.assertEqual("Specific", resolved["modifyAttributeTypeName"])

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

    def test_variant_born_buffs_are_row_exact_and_top_level_is_only_union(self) -> None:
        tables = {
            "EnemyTable.json": {
                "eny_test": {
                    "templateId": "eny_test",
                    "attrTemplateId": "attr_a",
                    "bornBuffs": ["buff_base"],
                },
                "eny_test_hard": {
                    "templateId": "eny_test",
                    "attrTemplateId": "attr_b",
                    "bornBuffs": ["buff_hard"],
                },
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

        entry = build_enemy_entries(tables, {}, {}, {})[0]
        variants = {row["id"]: row for row in entry["variants"]}
        self.assertEqual(["buff_base"], variants["eny_test"]["bornBuffs"])
        self.assertEqual(["buff_hard"], variants["eny_test_hard"]["bornBuffs"])
        self.assertEqual(["buff_base", "buff_hard"], entry["bornBuffs"])


if __name__ == "__main__":
    unittest.main()
