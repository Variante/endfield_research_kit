#!/usr/bin/env python3
"""Focused tests for the gacha authored-light population audit."""

from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_gacha_light_population.py")
SPEC = importlib.util.spec_from_file_location("audit_gacha_light_population", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


GOOD_LUA = """
local charObj = CSUtils.CreateObject(prefab, self.m_phase.m_roomObjItem.view.timelineRoot)
local lightPrefab = self.loader:LoadGameObject(string.format("Assets/Beyond/DynamicAssets/Gameplay/Prefabs/CharInfo/AdditionalLights/light_%s.prefab", charId))
local lightObj = CSUtils.CreateObject(lightPrefab, charObj.transform)
lightObj.transform:DoActionOnChildren(function(childTrans)
    local isTarget = childTrans.name == "light_overview"
    childTrans.gameObject:SetActive(isTarget)
    if isTarget then
        uiModelMono:InitLightFollower(childTrans)
    end
end)
charObj:SetLayerRecursive(UIConst.GACHA_LAYER)
self.m_phase.m_roomObjItem.view.sceneLight6Rarity.gameObject:SetActive(rarity >= 6)
self.m_phase.m_roomObjItem.view.sceneLight5Rarity.gameObject:SetActive(rarity == 5)
self.m_phase.m_roomObjItem.view.sceneLight4Rarity.gameObject:SetActive(rarity <= 4)
"""


def native_cull_fixtures() -> tuple[dict, dict, dict, list[dict]]:
    native = {
        "status": (
            "native candidate producer substantially source-closed; scheduled generic "
            "cull-view internals remain bounded open"
        )
    }
    view = {
        "nativeProof": {
            "fallbackMode": {
                "useFallbackLightCullingOnSourceClosedShippedRoute": False
            },
            "occlusion": {"addCullViewDimensions": [0, 0]},
        },
        "strongestExactOutput": {
            "authoredRoomMaximumContributionCount": 11,
            "excludedAuthoredRoomRows": ["Spot Light (20)"],
            "remainingAuthoredRoomOrderIsExactSubsequenceOf": AUDIT.ROOM_SURVIVOR_SUBSEQUENCE,
        },
        "noRuntimeLaunches": {
            "endfieldLaunched": False,
            "unityLaunched": False,
            "retailModuleLoaded": False,
            "processAttached": False,
        },
    }
    selected = {
        "strongestExactOutput": {
            "genericFlagMaskGateClosedForAll12": True,
            "guaranteedAbsent": ["Spot Light (20)"],
            "remainingStrictRelativeOrderIfAdmitted": AUDIT.ROOM_SURVIVOR_SUBSEQUENCE,
        },
        "noRuntimeLaunches": view["noRuntimeLaunches"],
    }
    return native, view, selected, [{"name": "Spot Light (20)"}]


class GachaLightPopulationAuditTests(unittest.TestCase):
    def test_operator_light_hash_ignores_unconsumed_roster_rows(self) -> None:
        payload = json.loads(AUDIT.OPERATOR_LIGHTS.read_text(encoding="utf-8"))
        payload.setdefault("actors", {}).setdefault("liino", {})[
            "test_only_marker"
        ] = "roster-addition"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator_lights.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(
                AUDIT.scoped_sha256(path, AUDIT.OPERATOR_LIGHT_SCOPE),
                AUDIT.EXPECTED_HASHES["operatorLights"],
            )

    def test_installed_resolution_gate(self) -> None:
        result = AUDIT.validate_installed_resolution(
            {
                "screenWidth": 3840,
                "screenHeight": 2160,
                "videoWidth": 3840,
                "videoHeight": 2160,
            },
            "fixture registry",
        )
        self.assertEqual(result["gameVideo"], {"width": 3840, "height": 2160})

    def test_installed_resolution_mismatch_reports_values(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=installed_resolution_values;.*"
            r"actual=.*1920",
        ):
            AUDIT.validate_installed_resolution(
                {
                    "screenWidth": 3840,
                    "screenHeight": 2160,
                    "videoWidth": 1920,
                    "videoHeight": 1080,
                },
                "fixture registry",
            )

    def test_selected_aspect_room_survivor_gate(self) -> None:
        AUDIT.validate_room_survivor_names(
            AUDIT.ROOM_SURVIVOR_SUBSEQUENCE,
            ["Spot Light (20)"],
            "fixture geometry",
        )

    def test_selected_aspect_room_survivor_mismatch_reports_names(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=selected_aspect_room_survivors;.*"
            r"actual=\['Spot Light \(12\)'\]",
        ):
            AUDIT.validate_room_survivor_names(
                ["Spot Light (12)"],
                ["Spot Light (20)"],
                "fixture geometry",
            )

    def test_successful_lua_gate(self) -> None:
        result = AUDIT.validate_lua_contract(GOOD_LUA, "fixture.lua")
        self.assertEqual(result["selectedChild"], "light_overview")
        self.assertTrue(result["initLightFollowerOnSelectedChild"])

    def test_wrong_selected_group_reports_expected_and_actual(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=lua_overviewSelector;.*"
            r"expected=True; actual=False",
        ):
            AUDIT.validate_lua_contract(
                GOOD_LUA.replace('"light_overview"', '"light_document"'),
                "wrong_group.lua",
            )

    def test_missing_follower_call_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=lua_followerInitialization;.*"
            r"expected=True; actual=False",
        ):
            AUDIT.validate_lua_contract(
                GOOD_LUA.replace("uiModelMono:InitLightFollower(childTrans)", ""),
                "missing_follower.lua",
            )

    def test_missing_recursive_layer_assignment_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=lua_recursiveGachaLayer;.*"
            r"expected=True; actual=False",
        ):
            AUDIT.validate_lua_contract(
                GOOD_LUA.replace("charObj:SetLayerRecursive(UIConst.GACHA_LAYER)", ""),
                "missing_layer.lua",
            )

    def test_aligned_layer_array_round_trip(self) -> None:
        payload = bytearray(struct.pack("<I", len(AUDIT.EXPECTED_LAYERS)))
        for value in AUDIT.EXPECTED_LAYERS:
            encoded = value.encode("utf-8")
            payload.extend(struct.pack("<I", len(encoded)))
            payload.extend(encoded)
            payload.extend(b"\0" * ((-len(payload)) & 3))
        self.assertEqual(
            AUDIT.parse_aligned_string_array(bytes(payload), 0),
            AUDIT.EXPECTED_LAYERS,
        )

    def test_character_survivor_gate(self) -> None:
        AUDIT.validate_character_survivor_names(
            AUDIT.CHARACTER_SURVIVORS,
            [],
            "fixture geometry",
        )

    def test_character_survivor_mismatch_reports_names(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=selected_aspect_character_survivors;.*"
            r"actual=\['FogLight_1 \(2\)'\]",
        ):
            AUDIT.validate_character_survivor_names(
                ["FogLight_1 (2)"],
                [],
                "fixture geometry",
            )

    def test_fixed_offset_follower_world_position(self) -> None:
        row = {
            "follower": {
                "followableNodeName": "BIP001",
                "followType": 0,
                "positionOffset": [0.5, 0.0, -1.0],
            },
            "serializedPosition": [0.0, 0.0, 0.0],
            "serializedForward": [0.0, 0.0, 1.0],
            "type": 2,
            "range": 1.0,
            "spotAngle": 30.0,
        }
        nodes = {
            "BIP001": ([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0])
        }
        result = AUDIT.evaluate_character_light(
            row,
            nodes,
            [("fixture", [1.0, 0.0, 0.0], 100.0)],
            [0.0, 0.0, 0.0],
        )
        self.assertEqual(result["worldPosition"], [1.5, 2.0, 2.0])
        self.assertEqual(
            result["positionEquation"],
            "target.worldPosition + positionOffset",
        )

    def test_parent_follower_world_position(self) -> None:
        row = {
            "follower": {
                "followableNodeName": "HEAD_LOCAL",
                "followType": 1,
                "localPosition": [0.5, 0.0, -1.0],
            },
            "serializedPosition": [0.0, 0.0, 0.0],
            "serializedForward": [0.0, 0.0, 1.0],
            "type": 2,
            "range": 1.0,
            "spotAngle": 30.0,
        }
        nodes = {
            "HEAD_LOCAL": ([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0])
        }
        result = AUDIT.evaluate_character_light(
            row,
            nodes,
            [("fixture", [1.0, 0.0, 0.0], 100.0)],
            [0.0, 0.0, 0.0],
        )
        self.assertEqual(result["worldPosition"], [1.5, 2.0, 2.0])
        self.assertEqual(
            result["positionEquation"],
            "target.worldPosition + target.worldRotation * localPosition",
        )

    def test_native_cull_boundary_success(self) -> None:
        result = AUDIT.validate_native_cull_boundary(*native_cull_fixtures())
        self.assertEqual(result["preCharacterEvaluationKnownAuthoredUpperBound"], 17)
        self.assertFalse(result["gachaOcclusionActive"])

    def test_native_cull_wrong_exclusion_reports_expected_and_actual(self) -> None:
        native, view, selected, room_rows = native_cull_fixtures()
        view["strongestExactOutput"]["excludedAuthoredRoomRows"] = []
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_light_population; check=room_exact_exclusion;.*"
            r"expected=\['Spot Light \(20\)'\]; actual=\[\]",
        ):
            AUDIT.validate_native_cull_boundary(native, view, selected, room_rows)


if __name__ == "__main__":
    unittest.main()
