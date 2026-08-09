#!/usr/bin/env python3
"""Focused tests for the gacha authored-light population audit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_gacha_light_population.py")
SPEC = importlib.util.spec_from_file_location("audit_gacha_light_population", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


GOOD_LUA = """
local lightPrefab = self.loader:LoadGameObject(string.format("Assets/Beyond/DynamicAssets/Gameplay/Prefabs/CharInfo/AdditionalLights/light_%s.prefab", charId))
lightObj.transform:DoActionOnChildren(function(childTrans)
    local isTarget = childTrans.name == "light_overview"
    childTrans.gameObject:SetActive(isTarget)
    if isTarget then
        uiModelMono:InitLightFollower(childTrans)
    end
end)
self.m_phase.m_roomObjItem.view.sceneLight6Rarity.gameObject:SetActive(rarity >= 6)
self.m_phase.m_roomObjItem.view.sceneLight5Rarity.gameObject:SetActive(rarity == 5)
self.m_phase.m_roomObjItem.view.sceneLight4Rarity.gameObject:SetActive(rarity <= 4)
"""


class GachaLightPopulationAuditTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
