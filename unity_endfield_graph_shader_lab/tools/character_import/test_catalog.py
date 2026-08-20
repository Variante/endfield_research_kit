from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.catalog import build_import_plan, unity_catalog_from_plan  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def entry(name: str, asset_type: str, container: str, path_id: int) -> dict:
    return {
        "Name": name,
        "Container": container,
        "Source": str(Path(tempfile.gettempdir()) / f"source_{path_id}.chk"),
        "PathID": path_id,
        "Type": asset_type,
        "Hash": f"hash{path_id}",
        "Offset": abs(path_id) * 10,
    }


def actor_ui_container(token: str, name: str) -> str:
    return f"assets/beyond/arts/entity/actor/{token}/animations/ui/{name}.fbx"


def fx_ui_prefab_container(name: str) -> str:
    return f"assets/beyond/dynamicassets/gameplay/effects/prefabs/{name}.prefab"


class CatalogTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, list[Path]]:
        table_path = root / "CharacterTable.json"
        write_json(
            table_path,
            {
                "chr_9000_endmin": {
                    "charId": "chr_9000_endmin",
                    "engName": "Endministrator",
                    "sortOrder": 1,
                    "rarity": 6,
                },
                "chr_0002_endminm": {
                    "charId": "chr_0002_endminm",
                    "engName": "Endministrator",
                    "sortOrder": 2,
                    "rarity": 6,
                },
                "chr_0003_endminf": {
                    "charId": "chr_0003_endminf",
                    "engName": "Endministrator",
                    "sortOrder": 3,
                    "rarity": 6,
                },
            },
        )
        streaming = root / "StreamingAssets" / "maps" / "assets.json"
        persistent = root / "Persistent" / "maps" / "assets.json"
        write_json(
            streaming,
            {
                "GameType": "ArknightsEndfield",
                "AssetEntries": [
                    entry(
                        "chr_0002_endminm_postmodel",
                        "Animator",
                        "assets/beyond/dynamicassets/gameplay/actors/postmodels/npc/chr_0002_endminm_postmodel.prefab",
                        10,
                    ),
                    entry(
                        "chr_0002_endminm_postmodel",
                        "Animator",
                        "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0002_endminm_postmodel.prefab",
                        11,
                    ),
                    entry(
                        "chr_0003_endminf_postmodel",
                        "Animator",
                        "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0003_endminf_postmodel.prefab",
                        12,
                    ),
                    entry(
                        "chr_0002_endminm_deco_1",
                        "Animator",
                        "assets/beyond/dynamicassets/gameplay/prefabs/uimodels/decoitems/"
                        "chr_0002_endminm_deco_1.prefab",
                        13,
                    ),
                    entry("A_actor_endminm_ui_overview_start", "AnimationClip", actor_ui_container("endminm", "start"), 20),
                    entry("A_actor_endminm_ui_overview_loop", "AnimationClip", actor_ui_container("endminm", "loop"), 21),
                    entry("A_actor_endminm_uiteam_idle_01", "AnimationClip", actor_ui_container("endminm", "team"), 22),
                    entry("A_actor_endminm_gacha", "AnimationClip", actor_ui_container("endminm", "gacha"), 23),
                    entry("A_actor_endminm_gacha_cam", "AnimationClip", actor_ui_container("endminm", "gacha"), 24),
                    entry("A_actor_endminm_battle_attack", "AnimationClip", "animations/battle/a.fbx", 25),
                    entry(
                        "A_actor_endminm_ui_overview_fx_01",
                        "AnimationClip",
                        "assets/beyond/arts/effects/commonassets/arts/sk_model/sk_fx_endminm_ui.fbx",
                        32,
                    ),
                    entry("A_item_widget_endminm_01_ui_overview_start", "AnimationClip", "widgets/ui.fbx", 26),
                    entry(
                        "A_item_widget_apple_01_ui_disappear_01",
                        "AnimationClip",
                        "assets/beyond/dynamicassets/gameplay/prefabs/uimodels/decoitems/"
                        "chr_0002_endminm_deco_1_controller.controller",
                        27,
                    ),
                    entry(
                        "A_item_widget_apple_01_ui_overview_start_01",
                        "AnimationClip",
                        "assets/beyond/arts/entity/item/widget/item_widget_apple/animations/ui/apple.fbx",
                        28,
                    ),
                    entry(
                        "A_item_widget_apple_01_ui_overview_loop_01",
                        "AnimationClip",
                        "assets/beyond/arts/entity/item/widget/item_widget_apple/animations/ui/apple.fbx",
                        29,
                    ),
                    entry(
                        "A_item_widget_unowned_01_ui_overview_loop_01",
                        "AnimationClip",
                        "assets/beyond/arts/entity/item/widget/shared/animations/ui/unowned.fbx",
                        33,
                    ),
                    entry("A_actor_endminf_ui_overview_start_01", "AnimationClip", actor_ui_container("endminf", "start"), 30),
                    entry("A_actor_endminf_ui_overview_start_loop", "AnimationClip", actor_ui_container("endminf", "loop"), 31),
                    entry(
                        "P_fxui_endminm003_overview_01",
                        "Animator",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_01"),
                        40,
                    ),
                    entry(
                        "P_fxui_endminm003_overview_02",
                        "Animator",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_02"),
                        41,
                    ),
                    entry(
                        "P_fxui_endminm003_overview_06",
                        "Animator",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_06"),
                        42,
                    ),
                    # A same-container child Animator must not be promoted to
                    # a root candidate without hierarchy evidence.
                    entry(
                        "effect_01",
                        "Animator",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_01"),
                        47,
                    ),
                    entry(
                        "A_fx_endminf_ui_overview_01",
                        "AnimationClip",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_06"),
                        43,
                    ),
                    entry(
                        "A_fx_endminf_ui_overview_02",
                        "AnimationClip",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_01"),
                        44,
                    ),
                    entry(
                        "A_fx_endminf_ui_overview_03",
                        "AnimationClip",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_02"),
                        45,
                    ),
                    entry(
                        "A_fx_endminf_ui_overview_04",
                        "AnimationClip",
                        fx_ui_prefab_container("p_fxui_endminm003_overview_01"),
                        46,
                    ),
                ],
            },
        )
        write_json(persistent, {"GameType": "ArknightsEndfield", "AssetEntries": []})
        return table_path, [streaming, persistent]

    def test_roster_is_joined_to_playable_postmodel_and_selector_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps = self.make_fixture(root)
            plan = build_import_plan(table, maps, work_root=root / "work")

            self.assertEqual(plan["table_row_count"], 3)
            self.assertEqual(plan["roster_count"], 2)
            self.assertEqual(plan["excluded_table_rows"][0]["character_id"], "chr_9000_endmin")
            male = plan["characters"][0]
            female = plan["characters"][1]
            self.assertIn("/postmodels/characters/", male["postmodel"]["Container"])
            self.assertNotEqual(male["display_name"], female["display_name"])
            self.assertEqual(male["ui_animation"]["selected_names"], [
                "A_actor_endminm_ui_overview_start",
                "A_actor_endminm_ui_overview_loop",
            ])
            self.assertEqual(male["ui_animation"]["external_camera_count"], 1)
            self.assertEqual(male["ui_animation"]["external_ui_effect_count"], 1)
            self.assertEqual(
                male["ui_animation"]["external_ui_effect_entries"][0]["Name"],
                "A_actor_endminm_ui_overview_fx_01",
            )
            self.assertEqual(female["ui_animation"]["external_ui_effect_count"], 4)
            self.assertEqual(
                [item["Name"] for item in female["ui_animation"]["external_ui_effect_entries"]],
                [
                    "A_fx_endminf_ui_overview_01",
                    "A_fx_endminf_ui_overview_02",
                    "A_fx_endminf_ui_overview_03",
                    "A_fx_endminf_ui_overview_04",
                ],
            )
            self.assertEqual(female["ui_animation"]["external_ui_effect_prefab_count"], 3)
            self.assertEqual(
                [item["Name"] for item in female["ui_animation"]["external_ui_effect_prefab_entries"]],
                [
                    "P_fxui_endminm003_overview_01",
                    "P_fxui_endminm003_overview_02",
                    "P_fxui_endminm003_overview_06",
                ],
            )
            for item in female["ui_animation"]["external_ui_effect_prefab_entries"]:
                self.assertEqual(
                    item["_ownership_evidence"],
                    "same_container_as_explicit_actor_keyed_fx_clip",
                )
                self.assertIn("no hierarchy", item["_evidence_boundary"])
            unity_catalog = unity_catalog_from_plan(plan)
            female_catalog = next(
                item for item in unity_catalog["characters"] if item["actor_token"] == "endminf"
            )
            self.assertEqual(female_catalog["deferred_external_ui_effect_prefab_count"], 3)
            self.assertEqual(
                [item["Name"] for item in female_catalog["deferred_external_ui_effect_prefabs"]],
                [
                    "P_fxui_endminm003_overview_01",
                    "P_fxui_endminm003_overview_02",
                    "P_fxui_endminm003_overview_06",
                ],
            )
            self.assertEqual(male["ui_animation"]["companion_widget_count"], 4)
            self.assertEqual(
                male["ui_animation"]["selected_companion_widget_names"],
                [
                    "A_item_widget_apple_01_ui_overview_loop_01",
                    "A_item_widget_apple_01_ui_overview_start_01",
                    "A_item_widget_endminm_01_ui_overview_start",
                ],
            )
            self.assertNotIn(
                "A_item_widget_unowned_01_ui_overview_loop_01",
                male["ui_animation"]["selected_companion_widget_names"],
            )
            self.assertEqual(
                male["ui_item_widgets"]["controller_owned_clip_families"],
                [
                    {
                        "family": "a_item_widget_apple_01",
                        "owner_prefabs": ["chr_0002_endminm_deco_1"],
                    }
                ],
            )
            self.assertNotIn("battle_attack", " ".join(male["ui_animation"]["selected_names"]).lower())

    def test_scopes_expand_only_inside_ui_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps = self.make_fixture(root)
            team_plan = build_import_plan(
                table,
                maps,
                clip_scope="overview-team",
                selected_actor_tokens={"endminm"},
                work_root=root / "work",
            )
            male = next(item for item in team_plan["characters"] if item["actor_token"] == "endminm")
            self.assertIn("A_actor_endminm_uiteam_idle_01", male["ui_animation"]["selected_names"])
            self.assertFalse(next(item for item in team_plan["characters"] if item["actor_token"] == "endminf")["import_enabled"])

            all_ui = build_import_plan(
                table,
                maps,
                clip_scope="all-ui",
                work_root=root / "work",
            )
            male = next(item for item in all_ui["characters"] if item["actor_token"] == "endminm")
            names = male["ui_animation"]["selected_names"]
            self.assertIn("A_actor_endminm_gacha", names)
            self.assertNotIn("A_actor_endminm_gacha_cam", names)
            self.assertNotIn("A_actor_endminm_battle_attack", names)
            self.assertNotIn("A_actor_endminm_ui_overview_fx_01", names)
            self.assertIn(
                "A_item_widget_apple_01_ui_disappear_01",
                male["ui_animation"]["selected_companion_widget_names"],
            )

    def test_fx_clips_remain_evidence_when_same_container_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps = self.make_fixture(root)
            streaming = json.loads(maps[0].read_text(encoding="utf-8"))
            streaming["AssetEntries"] = [
                item
                for item in streaming["AssetEntries"]
                if not (
                    item.get("Type") == "Animator"
                    and str(item.get("Name") or "").casefold().startswith("p_fxui_")
                )
            ]
            write_json(maps[0], streaming)

            plan = build_import_plan(table, maps, work_root=root / "work")
            female = next(
                item for item in plan["characters"] if item["actor_token"] == "endminf"
            )
            self.assertEqual(female["ui_animation"]["external_ui_effect_count"], 4)
            self.assertEqual(female["ui_animation"]["external_ui_effect_prefab_count"], 0)
            self.assertEqual(
                female["ui_animation"]["external_ui_effect_entries"][0]["_ownership_evidence"],
                "explicit_actor_keyed_fx_clip_in_external_ui_effect_prefab_container",
            )

    def test_exact_private_controller_pptr_admits_generic_clip_and_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps = self.make_fixture(root)
            streaming = json.loads(maps[0].read_text(encoding="utf-8"))
            streaming["AssetEntries"].append(
                entry(
                    "A_wpn_misc_9999_ui_overview_start_01",
                    "AnimationClip",
                    "assets/beyond/arts/entity/item/weapon/animations/ui/shared.fbx",
                    34,
                )
            )
            write_json(maps[0], streaming)

            controller_root = root / "StreamingAssets" / "json_by_type" / "AnimatorController"
            write_json(
                controller_root / "private_controller.json",
                {
                    "$animestudio": {
                        "container": (
                            "assets/beyond/dynamicassets/gameplay/prefabs/uimodels/"
                            "decoitems/chr_0002_endminm_deco_1.prefab"
                        )
                    },
                    "m_Name": "chr_0002_endminm_deco_1_controller",
                    "m_AnimationClips": [{"m_PathID": 34}],
                },
            )

            plan = build_import_plan(
                table,
                maps,
                work_root=root / "work",
                controller_roots=[controller_root],
            )
            male = next(item for item in plan["characters"] if item["actor_token"] == "endminm")
            self.assertIn(
                "A_wpn_misc_9999_ui_overview_start_01",
                male["ui_animation"]["selected_companion_widget_names"],
            )
            self.assertIn(
                {
                    "name": "a_wpn_misc_9999_ui_overview_start_01",
                    "owner_prefabs": ["chr_0002_endminm_deco_1"],
                    "evidence": "exact_private_deco_animator_controller_pptr",
                },
                male["ui_item_widgets"]["controller_owned_clips"],
            )
            selected = next(
                item
                for item in male["ui_animation"]["selected_companion_widget_entries"]
                if item["Name"] == "A_wpn_misc_9999_ui_overview_start_01"
            )
            self.assertEqual(selected["_owner_prefabs"], ["chr_0002_endminm_deco_1"])

    def test_scoped_run_does_not_shrink_shared_unity_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps = self.make_fixture(root)
            plan = build_import_plan(
                table,
                maps,
                selected_actor_tokens={"endminm"},
                work_root=root / "work",
            )

            catalog = unity_catalog_from_plan(plan)

            self.assertEqual(catalog["import_character_count"], catalog["roster_count"])
            self.assertEqual(catalog["selected_run_character_count"], 1)
            self.assertTrue(all(row["import_enabled"] for row in catalog["characters"]))
            self.assertEqual(
                sum(bool(row["selected_this_run"]) for row in catalog["characters"]),
                1,
            )


if __name__ == "__main__":
    unittest.main()
