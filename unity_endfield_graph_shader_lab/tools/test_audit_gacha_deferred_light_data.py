#!/usr/bin/env python3
"""Focused tests for the Gacha deferred LightData audit."""

from __future__ import annotations

import importlib.util
import copy
import json
import struct
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_gacha_deferred_light_data.py")
SPEC = importlib.util.spec_from_file_location("audit_gacha_deferred_light_data", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def call_body(offset: int, target: int) -> bytes:
    body = bytearray(AUDIT.PREPARE_CPU_DATA_SIZE)
    body[offset] = 0xE8
    displacement = target - (AUDIT.PREPARE_CPU_DATA_VA + offset + 5)
    struct.pack_into("<i", body, offset + 1, displacement)
    return bytes(body)


class GachaDeferredLightDataAuditTests(unittest.TestCase):
    def test_call_target_round_trip(self) -> None:
        offset = 0x08DB
        target = AUDIT.NATIVE_CALLS[offset][0]
        self.assertEqual(AUDIT.call_target(call_body(offset, target), offset), target)

    def test_wrong_call_target_reports_offset(self) -> None:
        offset = 0x08DB
        body = call_body(offset, 0x180000000)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_deferred_light_data; check=native_call_08db_target;.*"
            r"expected=",
        ):
            AUDIT.require(
                "native_call_08db_target",
                AUDIT.call_target(body, offset),
                AUDIT.NATIVE_CALLS[offset][0],
                "fixture",
            )

    def test_wrong_call_opcode_reports_source(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            r"check=native_call_08db_opcode; source=.*GameAssembly.dll;.*"
            r"expected=232; actual=0",
        ):
            AUDIT.call_target(bytes(AUDIT.PREPARE_CPU_DATA_SIZE), 0x08DB)

    def test_consumer_contract(self) -> None:
        text = AUDIT.SELECTED_FRAGMENT.read_text(encoding="utf-8")
        result = AUDIT.validate_consumer(text)
        self.assertEqual(result["strideVectors"], 8)
        self.assertIn("CharacterOnly", result["records"]["3"])

    def test_missing_consumer_lane_fails_closed(self) -> None:
        text = AUDIT.SELECTED_FRAGMENT.read_text(encoding="utf-8")
        with self.assertRaisesRegex(
            AssertionError,
            r"check=consumer_record3CharacterOnly;.*expected=True; actual=False",
        ):
            AUDIT.validate_consumer(
                text.replace("_LightDataBuffer_f_96[_773].z > 0.5f", "removed")
            )

    def test_native_record_writes(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
        result = AUDIT.validate_record_writes(body)
        self.assertEqual([row["record"] for row in result["spot"]], list(range(7)))
        self.assertEqual(result["common"][0]["record"], 7)

    def test_native_additional_data_layout(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_LIGHT_NPR_DATA_FILE_OFFSET)
            npr_body = stream.read(AUDIT.GET_LIGHT_NPR_DATA_SIZE)
            stream.seek(AUDIT.GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET)
            additional_body = stream.read(AUDIT.GET_LIGHT_ADDITIONAL_DATA_SIZE)
        result = AUDIT.validate_additional_data_native(npr_body, additional_body)
        layout = result["getLightAdditionalData"]["returnLayout"]
        self.assertEqual(layout["0x14"], "bool LightCharacterOnly plus padding")
        self.assertIn(
            "defaultAutoLimit",
            result["getLightNprData"]["selectedTypeZeroPacking"],
        )

    def test_changed_additional_layout_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_LIGHT_NPR_DATA_FILE_OFFSET)
            npr_body = stream.read(AUDIT.GET_LIGHT_NPR_DATA_SIZE)
            stream.seek(AUDIT.GET_LIGHT_ADDITIONAL_DATA_FILE_OFFSET)
            additional_body = bytearray(stream.read(AUDIT.GET_LIGHT_ADDITIONAL_DATA_SIZE))
        additional_body[0x28B + 4] = 0x85
        with self.assertRaisesRegex(
            AssertionError,
            r"check=get_light_additional_data_body_sha256;.*expected=.*actual=",
        ):
            AUDIT.validate_additional_data_native(npr_body, bytes(additional_body))

    def test_changed_record_address_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x0DF7 + 3] = 7
        with self.assertRaisesRegex(
            AssertionError,
            r"check=spot_record0_address;.*expected=b'.*\\x06'; actual=b'.*\\x07'",
        ):
            AUDIT.validate_record_writes(bytes(body))

    def test_selected_room_population(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(row["unityLightType"] == 0 for row in rows), 1)
        self.assertEqual(sum(row["linearLightLength"] > 0 for row in rows), 4)

    def test_selected_room_additional_components(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.attach_room_additional_data(
            AUDIT.room_light_rows(population, hierarchy)
        )
        self.assertEqual(len(rows), 11)
        self.assertTrue(all("additionalLightData" in row for row in rows))
        self.assertTrue(
            all(
                row["additionalLightData"]["nprDataNativePacked"]
                == [1.0, 1.0, 0.0, 0.0]
                for row in rows
            )
        )
        self.assertEqual(
            sorted(
                row["additionalLightData"]["volumetricScatteringIntensity"]
                for row in rows
            ),
            [0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 10.0, 10.0, 10.0, 10.0],
        )

    def test_changed_room_falloff_reports_component(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        game_objects = AUDIT.dump_index(AUDIT.ROOM_RAW_DUMP_ROOT / "GameObject")
        behaviours = AUDIT.dump_index(AUDIT.ROOM_RAW_DUMP_ROOT / "MonoBehaviour")
        light = AUDIT.load_json(AUDIT.REPO_ROOT / rows[0]["sourcePath"])
        game_object_id = int(light["m_GameObject"]["m_PathID"])
        component_id = int(
            game_objects[game_object_id][1]["m_Components"][2]["m_PathID"]
        )
        changed = copy.deepcopy(behaviours)
        changed[component_id][1]["m_falloffExponent"] = 2.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_falloff_exponent; source=.*MonoBehaviour.*; "
            r"expected=-1.0; actual=2.0",
        ):
            AUDIT.attach_room_additional_data(rows, game_objects, changed)

    def test_changed_room_order_reports_expected_and_actual(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        changed = copy.deepcopy(population)
        room_rows = [
            row
            for row in changed["exactKnownAuthoredSelectedAspectSurvivors"]["rows"]
            if row["source"] == "SceneLight6Rarity"
        ]
        room_rows[0]["name"] = "wrong room row"
        with self.assertRaisesRegex(
            AssertionError,
            r"check=selected_room_order;.*expected=.*Spot Light \(12\).*"
            r"actual=.*wrong room row",
        ):
            AUDIT.room_light_rows(changed, hierarchy)


if __name__ == "__main__":
    unittest.main()
