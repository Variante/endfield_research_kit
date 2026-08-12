from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class CharacterIdentityOverrideTests(unittest.TestCase):
    def test_chenpast_is_not_manually_merged_into_chen(self) -> None:
        override_path = REPO_ROOT / "webui" / "overrides" / "character_merges.json"
        payload = json.loads(override_path.read_text(encoding="utf-8"))
        merges = payload.get("merges", {})
        self.assertNotEqual("chen", merges.get("chenpast"))

    def test_chen_and_chenpast_have_distinct_model_evidence(self) -> None:
        index_path = (
            REPO_ROOT / "webui" / "data" / "lang" / "CN" / "characters" / "index.json"
        )
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        rows = {row.get("id"): row for row in payload.get("records", [])}
        chen = rows["chen"]
        chenpast = rows["chenpast"]

        self.assertEqual("character", chen.get("kind"))
        self.assertEqual("asset_npc", chenpast.get("kind"))
        self.assertNotIn("chenpast", chen.get("aliases", []))

        def model_paths(row: dict) -> set[str]:
            return {
                path
                for evidence in row.get("evidence", [])
                if evidence.get("assetKind") == "model"
                for path in evidence.get("paths", [])
            }

        chen_paths = model_paths(chen)
        chenpast_paths = model_paths(chenpast)
        self.assertTrue(chen_paths)
        self.assertTrue(chenpast_paths)
        self.assertTrue(all("P_actor_chen_" in path for path in chen_paths))
        self.assertTrue(all("chenpast" in path for path in chenpast_paths))
        self.assertTrue(chen_paths.isdisjoint(chenpast_paths))

    def test_liino_is_present_as_a_playable_character(self) -> None:
        index_path = (
            REPO_ROOT / "webui" / "data" / "lang" / "CN" / "characters" / "index.json"
        )
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        rows = {row.get("id"): row for row in payload.get("records", [])}
        liino = rows["liino"]
        self.assertEqual("character", liino.get("kind"))
        self.assertIn("chr_0035_liino", liino.get("aliases", []))
        self.assertTrue(any(
            evidence.get("type") == "playable_character_row"
            for evidence in liino.get("evidence", [])
        ))
        self.assertTrue(any(
            evidence.get("assetKind") == "model" and evidence.get("count", 0) > 0
            for evidence in liino.get("evidence", [])
        ))


if __name__ == "__main__":
    unittest.main()
