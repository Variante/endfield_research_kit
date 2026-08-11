from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.all_characters import (  # noqa: E402
    all_character_catalog_from_plan,
    build_all_character_plan,
)


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


def character_container(character_id: str, group: str = "characters") -> str:
    return (
        "assets/beyond/dynamicassets/gameplay/actors/postmodels/"
        f"{group}/{character_id}_postmodel.prefab"
    )


def actor_animation_container(token: str, clip: str) -> str:
    return f"assets/beyond/arts/entity/actor/{token}/animations/common/{clip}.fbx"


class AllCharacterCatalogTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, list[Path], dict[str, Path]]:
        table = root / "CharacterTable.json"
        write_json(
            table,
            {
                "chr_0002_endminm": {
                    "charId": "chr_0002_endminm",
                    "engName": "Endministrator",
                    "sortOrder": 2,
                    "rarity": 6,
                },
                "chr_0035_liino": {
                    "charId": "chr_0035_liino",
                    "engName": "Liino",
                    "sortOrder": 35,
                    "rarity": 6,
                }
            },
        )
        streaming = root / "StreamingAssets" / "maps" / "assets.json"
        persistent = root / "Persistent" / "maps" / "assets.json"
        entries = [
            entry(
                "chr_0002_endminm_postmodel",
                "Animator",
                character_container("chr_0002_endminm"),
                1,
            ),
            entry(
                "A_actor_endminm_ui_overview_start",
                "AnimationClip",
                actor_animation_container("endminm", "overview"),
                2,
            ),
            entry(
                "A_actor_endminm_ui_overview_loop",
                "AnimationClip",
                actor_animation_container("endminm", "overview"),
                3,
            ),
            entry(
                "A_actor_liino_ui_overview_start_01",
                "AnimationClip",
                actor_animation_container("liino", "ui_overview_start_01"),
                4,
            ),
            entry(
                "A_actor_liino_ui_overview_loop_01",
                "AnimationClip",
                actor_animation_container("liino", "ui_overview_loop_01"),
                5,
            ),
        ]
        for index, token in enumerate(("liino", "jsspsi", "chenpast"), start=35):
            character_id = f"chr_{index:04d}_{token}"
            entries.append(
                entry(
                    f"{character_id}_postmodel",
                    "Animator",
                    character_container(character_id),
                    index * 10,
                )
            )
        entries.extend(
            [
                entry(
                    "A_actor_liino_t_pose",
                    "AnimationClip",
                    actor_animation_container("liino", "t_pose"),
                    401,
                ),
                entry(
                    "A_actor_jsspsi_t_pose",
                    "AnimationClip",
                    actor_animation_container("jsspsi", "t_pose"),
                    402,
                ),
                entry(
                    "chr_0035_liino_postmodel",
                    "Animator",
                    character_container("chr_0035_liino", "npc"),
                    403,
                ),
                entry(
                    "chr_0030_zhuangfy_ult_postmodel",
                    "Animator",
                    character_container("chr_0030_zhuangfy_ult"),
                    404,
                ),
                entry(
                    "eny_0001_test_postmodel",
                    "Animator",
                    (
                        "assets/beyond/dynamicassets/gameplay/actors/postmodels/"
                        "enemies/eny_0001_test_postmodel.prefab"
                    ),
                    405,
                ),
            ]
        )
        write_json(streaming, {"GameType": "ArknightsEndfield", "AssetEntries": entries})
        write_json(persistent, {"GameType": "ArknightsEndfield", "AssetEntries": []})
        npc_info = root / "NpcInfoTable.json"
        npc_groups = root / "NpcTemplateGroupTable.json"
        text_table = root / "TextTable.json"
        i18n_en = root / "I18nTextTable_EN.json"
        prefab_root = root / "PrefabInfo"
        write_json(
            npc_info,
            {
                "liino": {"npcId": "liino", "templateId": "npc_chr_0035_liino"},
                "si": {
                    "npcId": "si",
                    "templateId": "npc_chr_0036_jsspsi",
                    "voActor": "jsspsi",
                    "wwiseId": "jsspsi",
                },
                "chenpast": {
                    "npcId": "chenpast",
                    "templateId": "npc_spl_chenpast_01",
                },
            },
        )
        write_json(
            npc_groups,
            {
                "liino": {"templateId": "npc_chr_0035_liino", "name": "npcName_liino"},
                "si": {"templateId": "npc_chr_0036_jsspsi", "name": "npcName_si"},
                "chenpast": {"templateId": "npc_spl_chenpast_01", "name": ""},
            },
        )
        write_json(
            text_table,
            {
                "npcName_liino": {"id": 101},
                "npcName_si": {"id": -102},
            },
        )
        write_json(i18n_en, {"101": "Liino", "-102": "Si"})
        for template_id, face in (
            ("npc_chr_0035_liino", "liino"),
            ("npc_chr_0036_jsspsi", "jsspsi"),
            ("npc_spl_chenpast_01", "chen"),
        ):
            write_json(
                prefab_root / f"{template_id}.json",
                {
                    "id": template_id,
                    "facialMorphAvatarName": f"FacialMorph/Avatar/Girl/{face}",
                    "earMorphAvatarName": "",
                    "disableBlink": False,
                },
            )
        return table, [streaming, persistent], {
            "npc_info_table": npc_info,
            "npc_template_group_table": npc_groups,
            "text_table": text_table,
            "i18n_en_table": i18n_en,
            "npc_prefab_info_root": prefab_root,
        }

    def test_superset_uses_canonical_character_roots_and_excludes_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps, sources = self.make_fixture(root)
            plan = build_all_character_plan(
                table,
                maps,
                work_root=root / "work",
                controller_roots=(),
                **sources,
            )

            self.assertEqual(plan["roster_count"], 4)
            self.assertEqual(plan["playable_roster_count"], 2)
            self.assertEqual(plan["nonplayable_character_count"], 2)
            self.assertEqual(plan["import_character_count"], 2)
            self.assertEqual(
                [row["actor_token"] for row in plan["characters"]],
                ["endminm", "liino", "jsspsi", "chenpast"],
            )
            liino = next(row for row in plan["characters"] if row["actor_token"] == "liino")
            self.assertIn("/postmodels/characters/", liino["postmodel"]["Container"])
            self.assertEqual(
                liino["ui_animation"]["selected_names"],
                [
                    "A_actor_liino_ui_overview_start_01",
                    "A_actor_liino_ui_overview_loop_01",
                ],
            )
            self.assertEqual(liino["actor_class"], "playable")
            jsspsi = next(
                row for row in plan["characters"] if row["actor_token"] == "jsspsi"
            )
            self.assertEqual(jsspsi["display_name"], "Si (Jsspsi)")
            chenpast = next(
                row for row in plan["characters"] if row["actor_token"] == "chenpast"
            )
            self.assertEqual(chenpast["ui_animation"]["animation_profile"], "static_postmodel")
            self.assertEqual(chenpast["ui_animation"]["selected_names"], [])
            self.assertIn("chr_0030_zhuangfy_ult_postmodel", plan["excluded_character_variants"])

    def test_catalog_keeps_playable_paths_and_marks_source_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps, sources = self.make_fixture(root)
            plan = build_all_character_plan(
                table,
                maps,
                selected_actor_tokens={"liino"},
                work_root=root / "work",
                controller_roots=(),
                **sources,
            )
            catalog = all_character_catalog_from_plan(plan)

            self.assertEqual(catalog["roster_count"], 4)
            self.assertEqual(catalog["selected_run_character_count"], 1)
            self.assertTrue(all(row["import_enabled"] for row in catalog["characters"]))
            playable = next(
                row for row in catalog["characters"] if row["actor_token"] == "endminm"
            )
            self.assertIn("/Playable/", playable["manifest_asset_path"])
            liino = next(row for row in catalog["characters"] if row["actor_token"] == "liino")
            self.assertIn("/Playable/", liino["manifest_asset_path"])
            self.assertEqual(liino["actor_class"], "playable")
            self.assertTrue(liino["capabilities"]["source_preview_animation"])

    def test_unknown_or_variant_tokens_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table, maps, sources = self.make_fixture(root)
            with self.assertRaisesRegex(ValueError, "unknown canonical character"):
                build_all_character_plan(
                    table,
                    maps,
                    selected_actor_tokens={"zhuangfy_ult"},
                    work_root=root / "work",
                    controller_roots=(),
                    **sources,
                )


if __name__ == "__main__":
    unittest.main()
