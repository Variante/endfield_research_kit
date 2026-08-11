#!/usr/bin/env python3
"""Focused tests for strict Gacha LightCullResult capture intake."""

from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_gacha_light_cull_capture_contract.py")
SPEC = importlib.util.spec_from_file_location("build_gacha_light_cull_capture_contract", SCRIPT)
assert SPEC and SPEC.loader
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def raw_row(
    *,
    light_type: int,
    position: tuple[float, float, float],
    priority: int,
    forward: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> bytes:
    row = bytearray(CONTRACT.DECODER.ROW_STRIDE_BYTES)
    struct.pack_into("<I", row, 0x00, light_type)
    struct.pack_into("<4f", row, 0x04, 1.0, 1.0, 1.0, 1.0)
    matrix = [0.0] * 16
    matrix[8:11] = forward
    matrix[11] = 0.0
    matrix[15] = 1.0
    struct.pack_into("<16f", row, 0x24, *matrix)
    struct.pack_into("<f", row, 0x64, 1.0)
    struct.pack_into("<f", row, 0x68, 10.0)
    struct.pack_into("<f", row, 0x6C, 45.0)
    struct.pack_into("<i", row, 0x70, priority)
    struct.pack_into("<3f", row, 0x74, *position)
    struct.pack_into("<I", row, 0x84, 0)
    return bytes(row)


def capture(rows: list[bytes]) -> dict:
    return {
        "schema": CONTRACT.DECODER.SCHEMA,
        "gameBuild": CONTRACT.DECODER.GAME_BUILD,
        "binaryPins": {
            "unityPlayerSha256": CONTRACT.DECODER.UNITY_PLAYER_SHA256,
            "gameAssemblySha256": CONTRACT.DECODER.GAME_ASSEMBLY_SHA256,
        },
        "callSite": "normal",
        "result": {
            "visibleLightsPtr": "0x12345000",
            "visibleLightCount": len(rows),
            "rawRowsHex": b"".join(rows).hex(),
        },
    }


class GachaLightCullCaptureContractTests(unittest.TestCase):
    def test_matches_one_authored_room_row_without_guessing_b31(self) -> None:
        source_row = CONTRACT._room_records(
            json.loads(CONTRACT.TRANSPORT.read_text(encoding="utf-8"))
        )[0]
        candidate = source_row["candidate"]
        row = raw_row(
            light_type=source_row["staticRecordTerms"]["unityLightType"],
            position=tuple(candidate["worldPosition"]["values"]),
            priority=source_row["priority"],
            forward=tuple(candidate["worldForward"]["values"]),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps(capture([row])), encoding="utf-8")
            result = CONTRACT.build_contract(
                path, (0.0, 0.0, 0.0), require_selected_room=False
            )
        self.assertEqual(result["roomIdentity"]["matchedCount"], 1)
        self.assertEqual(
            result["roomIdentity"]["matches"][0]["sourceName"],
            "Spot Light (12)",
        )
        self.assertFalse(result["targetFrame"]["b31Ready"])

    def test_selected_room_scope_fails_when_capture_is_incomplete(self) -> None:
        row = raw_row(light_type=0, position=(0.0, 0.0, 0.0), priority=0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps(capture([row])), encoding="utf-8")
            with self.assertRaisesRegex(
                CONTRACT.CaptureContractError,
                r"check=selected_room_capture_rows;.*missing=",
            ):
                CONTRACT.build_contract(path, (0.0, 0.0, 0.0))

    def test_setup_state_sort_is_priority_then_distance(self) -> None:
        rows = [
            {"lightType": 2, "priority": 0, "worldPosition": [2.0, 0.0, 0.0]},
            {"lightType": 0, "priority": 1, "worldPosition": [9.0, 0.0, 0.0]},
            {"lightType": 0, "priority": 0, "worldPosition": [1.0, 0.0, 0.0]},
        ]
        result = CONTRACT.sort_setup_state_rows(rows, (0.0, 0.0, 0.0))
        self.assertEqual(
            [item["captureRowIndex"] for item in result], [1, 2, 0]
        )

    def test_setup_state_tie_fails_closed(self) -> None:
        rows = [
            {"lightType": 0, "priority": 0, "worldPosition": [1.0, 0.0, 0.0]},
            {"lightType": 2, "priority": 0, "worldPosition": [-1.0, 0.0, 0.0]},
        ]
        with self.assertRaisesRegex(CONTRACT.CaptureContractError, "setupstate_tie"):
            CONTRACT.sort_setup_state_rows(rows, (0.0, 0.0, 0.0))

    def test_unsupported_capture_type_fails_closed(self) -> None:
        rows = [{"lightType": 1, "priority": 0, "worldPosition": [0.0, 0.0, 0.0]}]
        with self.assertRaisesRegex(CONTRACT.CaptureContractError, "setupstate_light_type"):
            CONTRACT.sort_setup_state_rows(rows, (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
