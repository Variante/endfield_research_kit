import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import build_nested_managed_identity_carrier_census as census


def field(name, *, dependencies=(), classes=()):
    return {
        "name": name,
        "runtimeType": dependencies[0] if dependencies else "System.String",
        "dependencies": list(dependencies),
        "classes": list(classes),
    }


class NestedManagedIdentityCarrierCensusTests(unittest.TestCase):
    def test_shortest_path_reaches_fixed_point_and_terminates_on_cycle(self):
        fields = {
            "Root": [field("child", dependencies=("Middle",))],
            "Middle": [
                field("back", dependencies=("Root",)),
                field("child", dependencies=("Leaf",)),
            ],
            "Leaf": [field("questId", classes=("mission_or_quest",))],
        }

        rows, direct, traversed_depth = census.shortest_identity_evidence(
            fields, "Root", "mission_or_quest"
        )

        self.assertFalse(direct)
        self.assertEqual(rows[0]["depth"], 2)
        self.assertEqual(traversed_depth, 2)
        self.assertEqual(
            rows[0]["path"],
            "Root.child -> Middle.child -> Leaf.questId",
        )

    def test_shortest_path_prefers_deterministic_minimum(self):
        fields = {
            "Root": [
                field("z", dependencies=("Zed",)),
                field("a", dependencies=("Alpha",)),
            ],
            "Alpha": [field("dialogId", classes=("story",))],
            "Zed": [field("radioId", classes=("story",))],
        }

        rows, _, _ = census.shortest_identity_evidence(fields, "Root", "story")

        self.assertEqual(rows[0]["path"], "Root.a -> Alpha.dialogId")

    def test_entity_hub_boundary_is_path_family_based(self):
        paths = {
            "mission_or_quest": (
                "Root.entity -> Beyond.Gameplay.Core.Entity.<interactive>k__BackingField "
                "-> Lock.questId"
            ),
            "level_script": "Root.scriptId",
            "story": (
                "Root.entity -> Beyond.Gameplay.Core.Entity.<npcInteractCom>k__BackingField "
                "-> Npc.dialogId"
            ),
        }

        self.assertTrue(
            census.crosses_runtime_entity_hub(paths, {"level_script"})
        )
        self.assertFalse(
            census.crosses_runtime_entity_hub(paths, {"mission_or_quest"})
        )

    def test_mixed_runtime_hubs_are_classified_without_root_type_rules(self):
        paths = {
            "mission_or_quest": "Root.missionId",
            "level_script": (
                "Root.data -> Beyond.Gameplay.MissionRuntimeAsset.propertyDic "
                "-> ScriptPtr.scriptId"
            ),
            "story": (
                "Root.entity -> Beyond.Gameplay.Core.Entity.<npcInteractCom>k__BackingField "
                "-> Npc.dialogId"
            ),
        }

        self.assertEqual(
            census.runtime_identity_hub_families(
                paths, {"mission_or_quest"}
            ),
            {
                "mission_runtime_property_or_action_graph",
                "runtime_entity_component_graph",
            },
        )

    def test_serialized_instance_audit_reports_success_and_exact_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "summary.json").write_text(
                json.dumps({
                    "complete": True,
                    "counts": {"objects": 2},
                    "inputParts": [{
                        "counts": {"objectsWithTruncatedScalars": 1},
                    }],
                    "outputs": {"objects": {"sha256": "fixture-sha"}},
                    "stageSignature": {
                        "payload": {
                            "source_fingerprint": {"fingerprint": "fixture-source"},
                        },
                    },
                }),
                encoding="utf-8",
            )
            rows = [{
                "script": {"fullName": "Fixture.Unrelated"},
                "scalars": [],
            }, {
                "script": {},
                "scalars": [[
                    "$.layout",
                    "s",
                    "Beyond.Gameplay.Core.Entity",
                ]],
            }]
            with gzip.open(root / "objects.jsonl.gz", "wt", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row) + "\n")

            audit = census.audit_serialized_entity_instances((root,))

        self.assertEqual(audit["exactInstances"], 1)
        self.assertEqual(
            audit["exactInstanceCounts"]["Beyond.Gameplay.Core.Entity"],
            1,
        )
        self.assertEqual(audit["objectsWithTruncatedScalars"], 1)
        self.assertEqual(audit["sources"][0]["objectsSha256"], "fixture-sha")

    def test_serialized_instance_audit_rejects_incomplete_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "summary.json").write_text(
                json.dumps({"complete": False}),
                encoding="utf-8",
            )
            with gzip.open(root / "objects.jsonl.gz", "wt", encoding="utf-8"):
                pass

            with self.assertRaisesRegex(RuntimeError, "not complete"):
                census.audit_serialized_entity_instances((root,))


if __name__ == "__main__":
    unittest.main()
