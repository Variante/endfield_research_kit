#!/usr/bin/env python3
"""Source-contract tests for extending the viewer beyond CharacterTable.

These tests intentionally do not exercise the not-yet-generalized importer.
They pin the installed-game boundary that the generalized catalog must use:
canonical ``postmodels/characters`` roots, rather than every actor postmodel.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = LAB_ROOT.parent
TOOLS_ROOT = LAB_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from endfield_asset_map_filter import iter_asset_entries  # noqa: E402
from character_import.catalog import DEFAULT_CHARACTER_TABLE  # noqa: E402


ASSET_MAP = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
CHARACTER_TABLE = DEFAULT_CHARACTER_TABLE
NPC_INFO_TABLE = (
    REPO_ROOT
    / "export_full/structured/StreamingAssets/Table/NpcInfoTable.json"
)
NPC_TEMPLATE_GROUP_TABLE = (
    REPO_ROOT
    / "export_full/structured/StreamingAssets/Table/NpcTemplateGroupTable.json"
)
TEXT_TABLE = REPO_ROOT / "export_full/structured/StreamingAssets/Table/TextTable.json"
I18N_EN = (
    REPO_ROOT
    / "export_full/structured/StreamingAssets/Table/I18nTextTable_EN.json"
)
GENERATED_CHARACTERS = (
    LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/Characters"
)
CHEN_MESH_ROOT = GENERATED_CHARACTERS / "Playable/Chen/Meshes"
CHEN_PREFAB = GENERATED_CHARACTERS / "Playable/Chen/Prefabs/Chen.prefab"
CHENPAST_MESH_ROOT = GENERATED_CHARACTERS / "NonPlayable/Chenpast/Meshes"
CHENPAST_PREFAB = (
    GENERATED_CHARACTERS / "NonPlayable/Chenpast/Prefabs/Chenpast.prefab"
)

CANONICAL_POSTMODEL_RE = re.compile(
    r"^assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/"
    r"(?P<character_id>chr_\d{4}_[a-z0-9]+)_postmodel\.prefab$",
    re.IGNORECASE,
)


def canonical_character_postmodels() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for entry in iter_asset_entries(ASSET_MAP):
        if str(entry.get("Type") or "") != "Animator":
            continue
        container = str(entry.get("Container") or "").replace("\\", "/")
        match = CANONICAL_POSTMODEL_RE.fullmatch(container)
        if match is None:
            continue
        character_id = match.group("character_id").casefold()
        if str(entry.get("Name") or "").casefold() != character_id + "_postmodel":
            continue
        if character_id in result:
            raise AssertionError(f"duplicate canonical character postmodel: {character_id}")
        result[character_id] = entry
    return result


class AllCharacterSourceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.postmodels = canonical_character_postmodels()

    def test_non_table_character_models_are_not_lost(self) -> None:
        table = json.loads(CHARACTER_TABLE.read_text(encoding="utf-8"))
        table_ids = {
            str(row.get("charId") or key).casefold()
            for key, row in table.items()
            if isinstance(row, dict)
        }
        additions = set(self.postmodels) - table_ids
        self.assertIn("chr_0035_liino", table_ids)
        self.assertNotIn("chr_0035_liino", additions)
        self.assertTrue({"chr_0036_jsspsi", "chr_0037_chenpast"} <= additions)

    def test_scope_excludes_other_postmodel_families_and_variants(self) -> None:
        self.assertNotIn("chr_0030_zhuangfy_ult", self.postmodels)
        for character_id, entry in self.postmodels.items():
            container = str(entry["Container"]).replace("\\", "/")
            self.assertEqual(
                container.casefold(),
                "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/"
                + character_id
                + "_postmodel.prefab",
            )
            self.assertEqual(
                str(entry["Name"]).casefold(), character_id + "_postmodel"
            )

    def test_named_additions_have_exact_original_animator_identities(self) -> None:
        self.assertEqual(
            int(self.postmodels["chr_0035_liino"]["PathID"]),
            -5949722553604816173,
        )
        self.assertEqual(
            int(self.postmodels["chr_0036_jsspsi"]["PathID"]),
            8881938948943589676,
        )
        self.assertEqual(
            int(self.postmodels["chr_0037_chenpast"]["PathID"]),
            -1377940589218415556,
        )

    def test_chen_and_chenpast_keep_distinct_original_model_identities(self) -> None:
        chen = self.postmodels["chr_0005_chen"]
        chenpast = self.postmodels["chr_0037_chenpast"]

        # Chenpast may reuse Chen's facial-morph/CPU-animation basis, but the
        # rendered post-model must remain a separate source-authored identity.
        self.assertNotEqual(
            str(chen["Container"]).casefold(), str(chenpast["Container"]).casefold()
        )
        self.assertNotEqual(int(chen["PathID"]), int(chenpast["PathID"]))
        self.assertNotEqual(
            str(chen["Source"]).casefold(), str(chenpast["Source"]).casefold()
        )

    def test_generated_chen_prefabs_keep_mesh_guid_sets_disjoint(self) -> None:
        """The generated gallery must not silently alias the two model kits."""

        def mesh_guids(root: Path) -> dict[str, Path]:
            result: dict[str, Path] = {}
            for meta in root.glob("*.asset.meta"):
                match = re.search(
                    r"^guid: ([0-9a-f]{32})$",
                    meta.read_text(encoding="utf-8"),
                    re.MULTILINE,
                )
                self.assertIsNotNone(match, meta)
                result[match.group(1)] = meta
            return result

        chen = mesh_guids(CHEN_MESH_ROOT)
        chenpast = mesh_guids(CHENPAST_MESH_ROOT)
        self.assertEqual(len(chen), 10)
        self.assertEqual(len(chenpast), 10)
        self.assertTrue(set(chen).isdisjoint(chenpast))

        chen_prefab = CHEN_PREFAB.read_text(encoding="utf-8")
        chenpast_prefab = CHENPAST_PREFAB.read_text(encoding="utf-8")
        chen_refs = set(re.findall(r"guid: ([0-9a-f]{32})", chen_prefab))
        chenpast_refs = set(re.findall(r"guid: ([0-9a-f]{32})", chenpast_prefab))
        self.assertTrue(set(chen).issubset(chen_refs))
        self.assertTrue(set(chenpast).issubset(chenpast_refs))
        self.assertTrue(set(chen).isdisjoint(chenpast_refs))
        self.assertTrue(set(chenpast).isdisjoint(chen_refs))
        self.assertEqual(chen_prefab.count("S_actor_chen_"), 10)
        self.assertEqual(chenpast_prefab.count("S_npc_major_chenpast_"), 10)

        # The distinction is not only naming/identity metadata: the two
        # source-authored body meshes carry different triangle index buffers.
        chen_body = (
            CHEN_MESH_ROOT / "S_actor_chen_body_01_lod0.asset"
        ).read_text(encoding="utf-8")
        chenpast_body = (
            CHENPAST_MESH_ROOT / "S_npc_major_chenpast_body_01_lod0.asset"
        ).read_text(encoding="utf-8")
        chen_index = re.search(r"^  m_IndexBuffer: (.+)$", chen_body, re.MULTILINE)
        chenpast_index = re.search(
            r"^  m_IndexBuffer: (.+)$", chenpast_body, re.MULTILINE
        )
        self.assertIsNotNone(chen_index)
        self.assertIsNotNone(chenpast_index)
        self.assertNotEqual(chen_index.group(1), chenpast_index.group(1))

    def test_npc_source_joins_cover_non_table_display_and_prefab_identity(self) -> None:
        info = json.loads(NPC_INFO_TABLE.read_text(encoding="utf-8"))
        groups = json.loads(NPC_TEMPLATE_GROUP_TABLE.read_text(encoding="utf-8"))
        text = json.loads(TEXT_TABLE.read_text(encoding="utf-8"))
        english = json.loads(I18N_EN.read_text(encoding="utf-8"))

        self.assertEqual(info["liino"]["templateId"], "npc_chr_0035_liino")
        self.assertEqual(info["si"]["templateId"], "npc_chr_0036_jsspsi")
        self.assertEqual(info["chenpast"]["templateId"], "npc_spl_chenpast_01")
        self.assertEqual(groups["liino"]["name"], "npcName_liino")
        self.assertEqual(groups["si"]["name"], "npcName_si")
        self.assertEqual(groups["chenpast"]["name"], "")

        liino_id = str(text["npcName_liino"]["id"])
        si_id = str(text["npcName_si"]["id"])
        self.assertEqual(english[liino_id], "Liino")
        self.assertEqual(english[si_id], "Si")


if __name__ == "__main__":
    unittest.main()
