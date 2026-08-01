from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from story_builder import dialog_tree  # noqa: E402


class DialogTreeRootPayloadAliasTests(unittest.TestCase):
    def setUp(self) -> None:
        dialog_tree._DIALOG_TREE_ROOT_PAYLOAD_ALIAS_CACHE.clear()

    def test_byte_identical_foreign_scene_payload_is_admitted(self) -> None:
        payload = b'{"nodes":[],"connections":[]}'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                "dlg_alias": root / "dlg_alias_p1.json",
                "dlg_story": root / "dlg_story_p2.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps({
                    "m_Name": key,
                    "m_Script": base64.b64encode(payload).decode("ascii"),
                }), encoding="utf-8")
            with (
                patch.object(
                    dialog_tree,
                    "_load_dialog_tree_source",
                    return_value={"lineIds": ["dlg_story_001"]},
                ),
                patch.object(
                    dialog_tree,
                    "_find_anime_tree_path",
                    side_effect=lambda name: paths[Path(name).stem],
                ),
            ):
                alias = dialog_tree.load_exact_dialog_tree_root_payload_alias(
                    "dlg_alias"
                )

        self.assertEqual("dlg_story", alias["storyKey"])
        self.assertTrue(alias["payloadIdentity"])
        self.assertFalse(alias["activationEvidence"])
        self.assertFalse(alias["branchSelectionEvidence"])
        self.assertEqual(len(payload), alias["decodedScriptLength"])

    def test_different_payload_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                "dlg_alias": root / "dlg_alias_p1.json",
                "dlg_story": root / "dlg_story_p2.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps({
                    "m_Name": key,
                    "m_Script": base64.b64encode(key.encode()).decode("ascii"),
                }), encoding="utf-8")
            with (
                patch.object(
                    dialog_tree,
                    "_load_dialog_tree_source",
                    return_value={"lineIds": ["dlg_story_001"]},
                ),
                patch.object(
                    dialog_tree,
                    "_find_anime_tree_path",
                    side_effect=lambda name: paths[Path(name).stem],
                ),
            ):
                alias = dialog_tree.load_exact_dialog_tree_root_payload_alias(
                    "dlg_alias"
                )

        self.assertIsNone(alias)


if __name__ == "__main__":
    unittest.main()
