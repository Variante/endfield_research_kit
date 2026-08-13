from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.story_builder import level_bindings


class LevelBindingSceneRefTests(unittest.TestCase):
    def test_resolves_direct_alias_and_canonical_cutscene_candidates(self) -> None:
        entries = {
            "dlg_direct": {},
            "dlg_alias": {},
            "cutscene_canonical": {},
        }
        with (
            patch.object(
                level_bindings,
                "_scene_ref_alias_candidates",
                side_effect=lambda value: ["dlg_alias"] if value == "missing" else [],
            ),
            patch.object(
                level_bindings,
                "_canonical_cutscene_key",
                side_effect=lambda value: (
                    "cutscene_canonical" if value == "raw_cutscene" else ""
                ),
            ),
        ):
            self.assertEqual(
                level_bindings._resolve_entry_scene_ref(
                    "dlg_direct",
                    entries_by_key=entries,
                ),
                "dlg_direct",
            )
            self.assertEqual(
                level_bindings._resolve_entry_scene_ref(
                    "missing",
                    entries_by_key=entries,
                ),
                "dlg_alias",
            )
            self.assertEqual(
                level_bindings._resolve_entry_scene_ref(
                    "raw_cutscene",
                    entries_by_key=entries,
                ),
                "cutscene_canonical",
            )


if __name__ == "__main__":
    unittest.main()
