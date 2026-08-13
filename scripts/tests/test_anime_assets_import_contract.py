from __future__ import annotations

import ast
from pathlib import Path
import unittest

from scripts.story_builder import anime_assets


SOURCE = Path(anime_assets.__file__)
CONTEXT_DEPENDENCIES = {
    "ANIME_RESOURCE_DIRS",
    "EXPORT_ROOT",
    "GAMEPLAY_CONFIG_DIR",
    "LEVELDATA_DIR",
    "NARRATIVE_VIDEO_EXTENSIONS",
    "NPC_PROXY_TABLE_PATH",
    "PERSISTENT_ASSETS_DIR",
    "STREAMING_ASSETS_DIR",
    "VIDEO_BINDINGS_PATH",
    "_CUTSCENE_REF_FIELDS",
    "_DIALOG_REF_FIELDS",
    "_RADIO_REF_FIELDS",
    "_REMOTECOMM_REF_FIELDS",
}


class AnimeAssetsImportContractTests(unittest.TestCase):
    def test_context_imports_are_explicit_and_bounded(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "context"
        ]

        self.assertEqual(len(imports), 1)
        self.assertNotIn("*", {alias.name for alias in imports[0].names})
        self.assertEqual(
            {alias.name for alias in imports[0].names},
            CONTEXT_DEPENDENCIES,
        )

    def test_module_owned_cache_slots_are_initialized(self) -> None:
        for name in (
            "_CUTSCENE_ASSET_CACHE",
            "_CUTSCENE_SUBTITLE_TRACK_CACHE",
            "_LEVELDATA_QUEST_STORY_REF_CACHE",
            "_MISSION_AREA_CACHE",
            "_NARRATIVE_VIDEO_CACHE",
            "_NPC_PROXY_TABLE_CACHE",
            "_VIDEO_BINDINGS_CACHE",
            "_VIDEO_DEFINITIONS_CACHE",
        ):
            with self.subTest(name=name):
                self.assertIn(name, vars(anime_assets))


if __name__ == "__main__":
    unittest.main()
