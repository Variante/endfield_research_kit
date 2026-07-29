from __future__ import annotations

import base64
import json
from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_recovery.build_dynamic_scene_mission_control_audit import (
    _data_index,
    _scene_name,
    decode_chunks,
    render_markdown,
)


class DynamicSceneMissionControlAuditTests(unittest.TestCase):
    def test_data_index_decodes_typed_identity(self) -> None:
        payload = struct.pack("<B3x i I i", 0, 15, 262915, 34)
        self.assertEqual(
            _data_index(payload, 0),
            {
                "isInvalid": False,
                "type": 15,
                "typeName": "IdComp",
                "gridId": 262915,
                "index": 34,
            },
        )

    def test_scene_name_uses_dynamic_streaming_path(self) -> None:
        self.assertEqual(
            _scene_name(
                "Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0003_0003.bytes"
            ),
            "map01",
        )
        self.assertEqual(_scene_name("Data/other.bytes"), "")

    def test_stream_length_mismatch_is_reported(self) -> None:
        row = {
            "fileName": "Data/DynamicStreaming/PC/Scene/map01/fb_main.bytes",
            "length": 5,
            "dataBase64": base64.b64encode(b"\x00\x00\x00\x00").decode("ascii"),
        }
        chunks, errors = decode_chunks([json.dumps(row)])
        self.assertEqual(chunks, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("payload length", errors[0]["error"])

    def test_empty_markdown_uses_clean_placeholder_and_boundary(self) -> None:
        report = {
            "counts": {
                "filesDecoded": 0,
                "gridsDecoded": 0,
                "missionControlledRoots": 0,
                "levelScriptIdentityRoots": 0,
                "storyIdentityRoots": 0,
                "storyOccurrences": 0,
                "decodeErrors": 0,
                "duplicateSceneGridIds": 0,
            },
            "storyIdentityCandidates": [],
            "nativeIdentityBoundary": {
                "classification": "exact_cross_reference_not_runtime_owner",
                "missionGraphAction": "none",
                "directBridgeFound": False,
            },
        }
        markdown = render_markdown(report)
        self.assertIn("| — | — | — | — | — |", markdown)
        self.assertIn("Mission graph action: `none`", markdown)


if __name__ == "__main__":
    unittest.main()
