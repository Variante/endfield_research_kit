#!/usr/bin/env python3
"""Focused tests for the Gacha deferred LightData audit."""

from __future__ import annotations

import importlib.util
import copy
import json
import struct
import unittest
from pathlib import Path
from unittest import mock


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

    def test_native_record0_discriminator_formula(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
        result = AUDIT.validate_record0_discriminator_native(body)
        self.assertEqual(result["formula"], "float(lightKind + 2 * shadowOnly)")
        self.assertEqual(result["encodedValues"]["Spot"]["normal"], 0.0)
        self.assertEqual(
            result["encodedValues"]["PointOrLinearExtension"]["normal"], 1.0
        )

    def test_native_obb_flags_projection(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
        result = AUDIT.validate_obb_flags_native(body)
        self.assertEqual(
            result["formula"],
            "uint(enableOBBCullingBox) | (uint(enableOverrideShadowLight) << 1)",
        )
        self.assertEqual(
            result["selectedAuthoredRoomValue"]["record5WBits"], "0x3F800000"
        )
        self.assertTrue(result["nativeProjectionClosed"])

    def test_changed_obb_flags_projection_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x0A88] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=obb_flags_projection_sequence; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_obb_flags_native(bytes(body))

    def test_native_point_shadow_face_pack_contract(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
        result = AUDIT.validate_point_shadow_face_pack_native(body)
        self.assertEqual(result["faceOrder"], list(range(6)))
        self.assertEqual(
            [row["face"] for row in result["cacheIndexLookups"]], list(range(6))
        )
        self.assertEqual(result["unavailableSentinelByte"], 255)
        self.assertEqual(
            result["packing"]["record2W"],
            "(face0 << 24) | (face1 << 16) | (face2 << 8) | face3",
        )
        self.assertTrue(result["packing"]["nativeFallbackAndPackClosed"])

    def test_changed_point_shadow_face_lookup_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x117D + 1] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=point_shadow_face_2_cache_index_target; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_point_shadow_face_pack_native(bytes(body))

    def test_changed_point_shadow_face_pack_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x1280] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=point_shadow_face_pack_sequence; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_point_shadow_face_pack_native(bytes(body))

    def test_native_point_shadow_cache_index_resolver_contract(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PUNCTUAL_SHADOW_CACHE_INDEX_FILE_OFFSET)
            body = stream.read(AUDIT.PUNCTUAL_SHADOW_CACHE_INDEX_SIZE)
        result = AUDIT.validate_point_shadow_cache_index_native(body)
        self.assertEqual(result["dynamicMatchResult"], "dynamicOrdinal + 40 (0x28)")
        self.assertEqual(result["staticMatchResult"], "PunctualLightCachedShadowDesc.shadowCacheSlotIndex (+0x0C)")
        self.assertEqual(result["unmatchedResult"], -1)
        self.assertTrue(result["resolverOutcomeClosed"])

    def test_native_shadow_caster_property_masks(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_FILE_OFFSET)
            is_dynamic = stream.read(AUDIT.HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_SIZE)
            stream.seek(AUDIT.HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_FILE_OFFSET)
            cast_static = stream.read(AUDIT.HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_SIZE)
            stream.seek(AUDIT.HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_FILE_OFFSET)
            cast_dynamic = stream.read(AUDIT.HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_SIZE)
        result = AUDIT.validate_shadow_caster_property_getters(
            is_dynamic, cast_static, cast_dynamic
        )
        self.assertEqual(result["fields"]["isDynamicShadowCaster"]["mask"], "0x01")
        self.assertEqual(result["fields"]["castStaticObjects"]["mask"], "0x02")
        self.assertEqual(result["fields"]["castDynamicObjects"]["mask"], "0x04")
        self.assertTrue(result["propertyMasksClosed"])
        self.assertTrue(result["runtimeCacheValuesStillOpen"])

    def test_changed_shadow_caster_property_mask_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_FILE_OFFSET)
            cast_dynamic = bytearray(
                stream.read(AUDIT.HG_SHARED_LIGHT_CAST_DYNAMIC_OBJECTS_SIZE)
            )
            stream.seek(AUDIT.HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_FILE_OFFSET)
            is_dynamic = stream.read(AUDIT.HG_SHARED_LIGHT_IS_DYNAMIC_SHADOW_CASTER_SIZE)
            stream.seek(AUDIT.HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_FILE_OFFSET)
            cast_static = stream.read(AUDIT.HG_SHARED_LIGHT_CAST_STATIC_OBJECTS_SIZE)
        cast_dynamic[0x0C] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=castDynamicObjects_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_shadow_caster_property_getters(
                is_dynamic, cast_static, bytes(cast_dynamic)
            )

    def test_native_shadow_render_type_patch_gate(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_SHADOW_RENDER_TYPE_FILE_OFFSET)
            body = stream.read(AUDIT.GET_SHADOW_RENDER_TYPE_SIZE)
        result = AUDIT.validate_shadow_render_type_native(body)
        self.assertEqual(result["patchMethodId"], "0x886")
        self.assertTrue(result["nativeDefaultStaticResultClosed"])
        self.assertEqual(
            result["nativeDefault"]["staticRequest"]["castStaticObjects"], True
        )
        self.assertEqual(
            result["nativeDefault"]["staticRequest"]["castDynamicObjects"], False
        )
        self.assertTrue(result["runtimePatchedPath"]["runtimeWrapperTableEntryStillOpen"])
        self.assertEqual(
            result["runtimePatchedPath"]["wrapper"],
            f"0x{AUDIT.ILFIX_DYNAMIC_METHOD_WRAPPER_874_VA:X}",
        )

    def test_changed_shadow_render_type_branch_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_SHADOW_RENDER_TYPE_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.GET_SHADOW_RENDER_TYPE_SIZE))
        body[0x3D] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=shadow_render_type_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_shadow_render_type_native(bytes(body))

    def test_native_renderer_config_shadow_flag_projection(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_RENDERER_CONFIG_FILE_OFFSET)
            body = stream.read(AUDIT.GET_RENDERER_CONFIG_SIZE)
        result = AUDIT.validate_renderer_config_native(body)
        self.assertEqual(result["patchMethodId"], "0x887")
        self.assertEqual(result["nativeDefault"]["baseFlags"], "0x4800")
        self.assertEqual(
            result["nativeDefault"]["formula"],
            "0x4800 | (castStaticObjects ? 0x1000 : 0) | (castDynamicObjects ? 0x2000 : 0)",
        )
        self.assertTrue(result["nativeDefaultFlagsClosed"])
        self.assertEqual(
            result["runtimePatchedPath"]["wrapper"],
            f"0x{AUDIT.ILFIX_DYNAMIC_METHOD_WRAPPER_875_VA:X}",
        )

    def test_changed_renderer_config_formula_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_RENDERER_CONFIG_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.GET_RENDERER_CONFIG_SIZE))
        body[0x62] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=renderer_config_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_renderer_config_native(bytes(body))

    def test_native_ecs_render_flags_projection(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_ECS_RENDER_FLAGS_FILE_OFFSET)
            body = stream.read(AUDIT.GET_ECS_RENDER_FLAGS_SIZE)
        result = AUDIT.validate_ecs_render_flags_native(body)
        self.assertEqual(result["patchMethodId"], "0x888")
        self.assertEqual(
            result["nativeDefault"]["baseValues"],
            {
                "objectFlags": "0x08000002",
                "objectFlagsMask": "0x08000002",
                "renderFlags": "0x02080000",
                "renderFlagsMask": "0x02080000",
            },
        )
        self.assertEqual(
            result["nativeDefault"]["exclusiveCasterProjection"]["condition"],
            "castStaticObjects XOR castDynamicObjects",
        )
        self.assertEqual(result["nativeDefault"]["hdCharacterShadow"]["bit"], 28)
        self.assertTrue(result["nativeDefaultFlagsClosed"])
        self.assertEqual(
            result["runtimePatchedPath"]["wrapper"],
            f"0x{AUDIT.ILFIX_DYNAMIC_METHOD_WRAPPER_876_VA:X}",
        )

    def test_changed_ecs_render_flags_default_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_ECS_RENDER_FLAGS_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.GET_ECS_RENDER_FLAGS_SIZE))
        body[0x51] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=ecs_render_flags_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_ecs_render_flags_native(bytes(body))

    def test_native_ifix_wrapper_table_lookup_contract(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_FILE_OFFSET)
            is_patched = stream.read(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_SIZE)
            stream.seek(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_COLD_FILE_OFFSET)
            is_patched_cold = stream.read(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE)
            stream.seek(AUDIT.WRAPPERS_MANAGER_GET_PATCH_FILE_OFFSET)
            get_patch = stream.read(AUDIT.WRAPPERS_MANAGER_GET_PATCH_SIZE)
        result = AUDIT.validate_ifix_wrapper_table_native(
            is_patched, is_patched_cold, get_patch
        )
        self.assertEqual(result["managerGlobalSlot"], "0x18E28EC48")
        self.assertEqual(
            result["tableLayout"]["entryArray"], "+0x20 + 8 * methodId"
        )
        self.assertTrue(result["lookupContractClosed"])
        self.assertTrue(result["runtimeMembershipStillOpen"])
        self.assertTrue(result["runtimeWrapperPointersStillOpen"])

    def test_changed_ifix_wrapper_table_body_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.WRAPPERS_MANAGER_GET_PATCH_FILE_OFFSET)
            get_patch = bytearray(stream.read(AUDIT.WRAPPERS_MANAGER_GET_PATCH_SIZE))
            stream.seek(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_FILE_OFFSET)
            is_patched = stream.read(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_SIZE)
            stream.seek(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_COLD_FILE_OFFSET)
            is_patched_cold = stream.read(AUDIT.WRAPPERS_MANAGER_IS_PATCHED_COLD_SIZE)
        get_patch[0x48] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=wrappers_manager_get_patch_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_ifix_wrapper_table_native(
                is_patched, is_patched_cold, bytes(get_patch)
            )

    def test_changed_point_shadow_cache_index_unmatched_return_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PUNCTUAL_SHADOW_CACHE_INDEX_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PUNCTUAL_SHADOW_CACHE_INDEX_SIZE))
        body[0xC7] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=point_shadow_cache_index_body_sha256; source=.*GameAssembly.dll; ",
        ):
            AUDIT.validate_point_shadow_cache_index_native(bytes(body))

    def test_native_point_record_transform_contract(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
        result = AUDIT.validate_point_record_transform_native(body)
        self.assertEqual(
            [row["method"] for row in result["calls"]],
            [
                "VisibleLightExtensionMethods.GetForward",
                "HGUtils.PackNormalOctRectEncode",
                "VisibleLightExtensionMethods.GetPosition",
            ],
        )
        self.assertEqual(result["record1XYZ"]["nativeSpace"], "world-space")
        self.assertIn("cameraPosition", result["record1XYZ"]["deferredConsumerSpace"])
        self.assertEqual(result["record2XY"]["encoding"], "octahedral rectangle")

    def test_changed_point_record_transform_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x0798 + 1] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=point_record_transform_PackNormalOctRectEncode_target; "
            r"source=.*GameAssembly.dll; expected=.*actual=",
        ):
            AUDIT.validate_point_record_transform_native(bytes(body))

    def test_visible_light_transform_helper_bodies(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_FORWARD_FILE_OFFSET)
            forward = stream.read(AUDIT.VISIBLE_LIGHT_GET_FORWARD_SIZE)
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_POSITION_FILE_OFFSET)
            position = stream.read(AUDIT.VISIBLE_LIGHT_GET_POSITION_SIZE)
            stream.seek(AUDIT.HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_FILE_OFFSET)
            pack = stream.read(AUDIT.HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE)
            stream.seek(AUDIT.PACK_NORMAL_ONE_CONSTANT_FILE_OFFSET)
            one_constant = stream.read(4)
            stream.seek(AUDIT.PACK_NORMAL_HALF_CONSTANT_FILE_OFFSET)
            half_constant = stream.read(4)
        result = AUDIT.validate_visible_light_transform_helpers(
            forward, position, pack, one_constant, half_constant
        )
        self.assertEqual(result["getForward"]["matrixColumn"], 2)
        self.assertEqual(result["getPosition"]["matrixColumn"], 3)
        self.assertEqual(result["getForward"]["ifixMethodId"], "0x77A")
        self.assertEqual(result["getPosition"]["ifixMethodId"], "0x77D")
        self.assertEqual(result["packNormalOctRectEncode"]["input"], "float3 direction")

    def test_changed_visible_light_transform_helper_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_FORWARD_FILE_OFFSET)
            forward = bytearray(stream.read(AUDIT.VISIBLE_LIGHT_GET_FORWARD_SIZE))
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_POSITION_FILE_OFFSET)
            position = stream.read(AUDIT.VISIBLE_LIGHT_GET_POSITION_SIZE)
            stream.seek(AUDIT.HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_FILE_OFFSET)
            pack = stream.read(AUDIT.HG_UTILS_PACK_NORMAL_OCT_RECT_ENCODE_SIZE)
            stream.seek(AUDIT.PACK_NORMAL_ONE_CONSTANT_FILE_OFFSET)
            one_constant = stream.read(4)
            stream.seek(AUDIT.PACK_NORMAL_HALF_CONSTANT_FILE_OFFSET)
            half_constant = stream.read(4)
        forward[0x4D] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=visible_light_get_forward_body_sha256; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_visible_light_transform_helpers(
                bytes(forward), position, pack, one_constant, half_constant
            )

    def test_authored_room_transform_candidates(self) -> None:
        cull_view = json.loads(AUDIT.GACHA_CULL_VIEW_AUDIT.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rotatehouse = json.loads(AUDIT.ROTATEHOUSE.read_text(encoding="utf-8"))
        result = AUDIT.validate_authored_room_transform_candidates(
            cull_view, hierarchy, rotatehouse
        )
        self.assertEqual(result["count"], 12)
        self.assertEqual(
            [row["name"] for row in result["rows"]],
            [
                "Spot Light (12)",
                "Spot Light (19)",
                "Linear Light (12)",
                "Linear Light (13)",
                "Linear Light (14)",
                "Spot Light (17)",
                "Linear Light (15)",
                "Spot Light (18)",
                "Spot Light (9)",
                "Spot Light (20)",
                "Spot Light (11)",
                "Spot Light (10)",
            ],
        )
        self.assertEqual(
            result["rows"][0]["worldPosition"]["bits"],
            ["0xC0033333", "0x40CDFBE7", "0xC0975C26"],
        )
        self.assertEqual(len(result["rows"][0]["worldForward"]["values"]), 3)
        self.assertEqual(
            result["rows"][0]["record2XYCandidate"]["bits"],
            ["0xB3800000", "0xBF7FFFFE"],
        )
        self.assertTrue(result["record2XYCandidateClosed"])
        self.assertEqual(result["targetFrameValues"], "capture-only; these are authored static candidates, not a retail LightCullResult capture")

    def test_changed_authored_room_transform_fails_closed(self) -> None:
        cull_view = json.loads(AUDIT.GACHA_CULL_VIEW_AUDIT.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rotatehouse = json.loads(AUDIT.ROTATEHOUSE.read_text(encoding="utf-8"))
        next(
            row
            for row in hierarchy["lights"]
            if row["name"] == "Spot Light (12)"
            and row["rarityGroup"] == "SceneLight6Rarity"
        )["localPosition"]["X"] += 1.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=Spot Light \(12\)_authored_world_position_bits; source=.*audit.json; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_authored_room_transform_candidates(
                cull_view, hierarchy, rotatehouse
            )

    def test_changed_record0_discriminator_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
        body[0x1352 + 3] = 4
        with self.assertRaisesRegex(
            AssertionError,
            r"check=record0_point_discriminator_sequence; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_record0_discriminator_native(bytes(body))

    def test_native_static_record_terms(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = stream.read(AUDIT.PREPARE_CPU_DATA_SIZE)
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_RANGE_FILE_OFFSET)
            range_getter = stream.read(AUDIT.VISIBLE_LIGHT_GET_RANGE_SIZE)
            stream.seek(AUDIT.SCALAR_COS_FILE_OFFSET)
            scalar_cos = stream.read(AUDIT.SCALAR_COS_SIZE)
            stream.seek(AUDIT.GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET)
            one = stream.read(4)
            stream.seek(AUDIT.SPOT_ANGLE_DIVISOR_FILE_OFFSET)
            angle_divisor = stream.read(4)
            stream.seek(AUDIT.SPOT_ANGLE_PI_FILE_OFFSET)
            angle_pi = stream.read(4)
        result = AUDIT.validate_static_record_terms_native(
            body, range_getter, scalar_cos, one, angle_divisor, angle_pi
        )
        self.assertEqual(result["visibleLightRange"]["fieldOffset"], "0x68")
        self.assertEqual(
            result["visibleLightRange"]["record1WFormula"],
            "1.0f / VisibleLight.range",
        )
        self.assertEqual(
            result["spotRecord2"]["selectedGoldenBits"]["outerCos"],
            "0x3EAF1D40",
        )

    def test_changed_static_record_sequence_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PREPARE_CPU_DATA_FILE_OFFSET)
            body = bytearray(stream.read(AUDIT.PREPARE_CPU_DATA_SIZE))
            stream.seek(AUDIT.VISIBLE_LIGHT_GET_RANGE_FILE_OFFSET)
            range_getter = stream.read(AUDIT.VISIBLE_LIGHT_GET_RANGE_SIZE)
            stream.seek(AUDIT.SCALAR_COS_FILE_OFFSET)
            scalar_cos = stream.read(AUDIT.SCALAR_COS_SIZE)
            stream.seek(AUDIT.GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET)
            one = stream.read(4)
            stream.seek(AUDIT.SPOT_ANGLE_DIVISOR_FILE_OFFSET)
            angle_divisor = stream.read(4)
            stream.seek(AUDIT.SPOT_ANGLE_PI_FILE_OFFSET)
            angle_pi = stream.read(4)
        body[0xCFD] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=spot_inner_angle_scale_sequence; source=.*GameAssembly.dll; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_static_record_terms_native(
                bytes(body), range_getter, scalar_cos, one, angle_divisor, angle_pi
            )

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

    def test_original_global_lighting_settings(self) -> None:
        result = AUDIT.validate_global_lighting_settings(
            AUDIT.GLOBAL_GAME_MANAGERS.read_bytes()
        )
        self.assertEqual(result["playerSettings"]["activeColorSpace"], "Linear")
        self.assertTrue(result["graphicsSettings"]["lightsUseLinearIntensity"])
        self.assertTrue(result["graphicsSettings"]["lightsUseColorTemperature"])

    def test_unityplayer_light_color_and_flicker_producers(self) -> None:
        result = AUDIT.validate_unity_light_color_native(AUDIT.UNITY_PLAYER.read_bytes())
        self.assertEqual(
            result["finalColor"]["selectedRowsFormula"],
            "UnityPlayer Color.linear(serialized color) * intensity",
        )
        self.assertEqual(result["flickerScale"]["disabledAnimationResult"], 1.0)
        self.assertEqual(len(result["internalCallTable"]["resolvedEntries"]), 3)

    def test_unityplayer_matrix4x4_inverse_native(self) -> None:
        result = AUDIT.validate_matrix4x4_inverse_native(
            AUDIT.UNITY_PLAYER.read_bytes()
        )
        self.assertEqual(result["icallIndex"], 2471)
        self.assertEqual(result["nativeBodySizeBytes"], 0x2C4)
        self.assertEqual(
            result["nativeBodySha256"],
            "71e600ecd556110747f8fb572abb1ab41343b3f0b3154b7bd5187696922fd20d",
        )
        self.assertEqual(result["signMaskBits"], "0x80000000")

    def test_changed_matrix4x4_inverse_body_fails_closed(self) -> None:
        data = bytearray(AUDIT.UNITY_PLAYER.read_bytes())
        data[AUDIT.MATRIX4X4_INVERSE_NATIVE_FILE_OFFSET] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=matrix4x4_inverse_native_body_sha256;.*expected=.*actual=",
        ):
            AUDIT.validate_matrix4x4_inverse_native(bytes(data))

    def test_native_matrix4x4_inverse_replays_signed_zero(self) -> None:
        inverse, success, determinant = (
            AUDIT.unity_matrix4x4_inverse_affine_candidate(
                [
                    [2.0, 0.0, 0.0, 1.0],
                    [0.0, 3.0, 0.0, 2.0],
                    [0.0, 0.0, 4.0, 3.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
        )
        self.assertTrue(success)
        self.assertEqual(AUDIT.float32_bits(determinant), 0x41C00000)
        self.assertEqual(AUDIT.float32_bits(inverse[0][1]), 0x80000000)
        self.assertEqual(AUDIT.float32_bits(inverse[1][0]), 0x80000000)
        self.assertEqual(AUDIT.float32_bits(inverse[1][2]), 0x80000000)
        self.assertEqual(AUDIT.float32_bits(inverse[2][1]), 0x80000000)

    def test_native_matrix4x4_inverse_singular_path_returns_zero(self) -> None:
        inverse, success, _ = AUDIT.unity_matrix4x4_inverse_affine_candidate(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        self.assertFalse(success)
        self.assertEqual(inverse, [[0.0] * 4 for _ in range(4)])

    def test_unityplayer_matrix4x4_trs_native(self) -> None:
        result = AUDIT.validate_matrix4x4_trs_native(AUDIT.UNITY_PLAYER.read_bytes())
        self.assertEqual(result["icallIndex"], 2470)
        self.assertEqual(result["nativeBodySizeBytes"], 0xC6)
        self.assertEqual(
            result["nativeBodySha256"],
            "ed2c20824bf8944a67566c874df429a53f6ca1c25f51f0eaf39259a16105b980",
        )
        self.assertEqual(result["quaternionToMatrixHelperBodySizeBytes"], 0x142)

    def test_changed_matrix4x4_trs_body_fails_closed(self) -> None:
        data = bytearray(AUDIT.UNITY_PLAYER.read_bytes())
        data[AUDIT.MATRIX4X4_TRS_NATIVE_FILE_OFFSET] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=matrix4x4_trs_native_body_sha256;.*expected=.*actual=",
        ):
            AUDIT.validate_matrix4x4_trs_native(bytes(data))

    def test_native_matrix4x4_trs_replays_quaternion_helper_and_column_scale(self) -> None:
        quaternion = [0.0, 0.5, 0.0, 0.8660254]
        rotation = AUDIT.unity_quaternion_to_matrix_candidate(quaternion)
        self.assertEqual(
            [AUDIT.float32_bits(rotation[row][column]) for row, column in ((0, 0), (0, 2), (2, 0), (2, 2))],
            [0x3F000000, 0x3F5DB3D7, 0xBF5DB3D7, 0x3F000000],
        )
        trs = AUDIT.unity_matrix4x4_trs_candidate(
            quaternion,
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
        )
        self.assertEqual(
            [AUDIT.float32_bits(trs[0][column]) for column in range(4)],
            [0x3F800000, 0x00000000, 0x405DB3D7, 0x3F800000],
        )
        self.assertEqual(
            [AUDIT.float32_bits(trs[2][column]) for column in range(4)],
            [0xBFDDB3D7, 0x00000000, 0x40000000, 0x40400000],
        )

    def test_unityplayer_quaternion_euler_boundary(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_FILE_OFFSET)
            managed = stream.read(AUDIT.QUATERNION_EULER_MANAGED_SIZE)
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_FILE_OFFSET)
            lazy_init = stream.read(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_SIZE)
            stream.seek(AUDIT.QUATERNION_EULER_RESOLVER_STRING_FILE_OFFSET)
            resolver_string = stream.read(len(AUDIT.QUATERNION_EULER_RESOLVER_STRING))
            stream.seek(AUDIT.QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET)
            scale_helper = stream.read(AUDIT.QUATERNION_EULER_SCALE_HELPER_SIZE)
            stream.seek(AUDIT.DEGREES_TO_RADIANS_FILE_OFFSET)
            degrees_to_radians = stream.read(4)
        result = AUDIT.validate_quaternion_euler_native(
            managed,
            lazy_init,
            resolver_string,
            scale_helper,
            degrees_to_radians,
            AUDIT.UNITY_PLAYER.read_bytes(),
        )
        self.assertEqual(result["icallIndex"], 2489)
        self.assertEqual(result["degreesToRadiansBits"], "0x3C8EFA35")
        self.assertEqual(result["halfAngleConstantBits"], "0x3F000000")
        self.assertEqual(result["managedSlotVirtualAddress"], "0x18F36FAC8")
        self.assertEqual(result["icallResolverVirtualAddress"], "0x180059FC0")
        self.assertEqual(result["resolverString"], AUDIT.QUATERNION_EULER_RESOLVER_STRING)
        self.assertEqual(result["nativeOrderParameter"], 4)
        self.assertEqual(result["nativeOrderCaseOffset"], "0x425")
        self.assertEqual(len(result["nativeOrderJumpTable"]), 6)
        self.assertEqual(len(result["mathCalls"]), 6)

    def test_changed_quaternion_euler_managed_body_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_FILE_OFFSET)
            managed = bytearray(stream.read(AUDIT.QUATERNION_EULER_MANAGED_SIZE))
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_FILE_OFFSET)
            lazy_init = stream.read(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_SIZE)
            stream.seek(AUDIT.QUATERNION_EULER_RESOLVER_STRING_FILE_OFFSET)
            resolver_string = stream.read(len(AUDIT.QUATERNION_EULER_RESOLVER_STRING))
            stream.seek(AUDIT.QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET)
            scale_helper = stream.read(AUDIT.QUATERNION_EULER_SCALE_HELPER_SIZE)
            stream.seek(AUDIT.DEGREES_TO_RADIANS_FILE_OFFSET)
            degrees_to_radians = stream.read(4)
        managed[0] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=quaternion_euler_managed_body_sha256;.*expected=.*actual=",
        ):
            AUDIT.validate_quaternion_euler_native(
                bytes(managed),
                lazy_init,
                resolver_string,
                scale_helper,
                degrees_to_radians,
                AUDIT.UNITY_PLAYER.read_bytes(),
            )

    def test_changed_quaternion_euler_lazy_resolver_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_FILE_OFFSET)
            managed = stream.read(AUDIT.QUATERNION_EULER_MANAGED_SIZE)
            stream.seek(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_FILE_OFFSET)
            lazy_init = bytearray(
                stream.read(AUDIT.QUATERNION_EULER_MANAGED_LAZY_INIT_SIZE)
            )
            stream.seek(AUDIT.QUATERNION_EULER_RESOLVER_STRING_FILE_OFFSET)
            resolver_string = stream.read(len(AUDIT.QUATERNION_EULER_RESOLVER_STRING))
            stream.seek(AUDIT.QUATERNION_EULER_SCALE_HELPER_FILE_OFFSET)
            scale_helper = stream.read(AUDIT.QUATERNION_EULER_SCALE_HELPER_SIZE)
            stream.seek(AUDIT.DEGREES_TO_RADIANS_FILE_OFFSET)
            degrees_to_radians = stream.read(4)
        lazy_init[0] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"check=quaternion_euler_lazy_init_body_sha256;.*expected=.*actual=",
        ):
            AUDIT.validate_quaternion_euler_native(
                managed,
                bytes(lazy_init),
                resolver_string,
                scale_helper,
                degrees_to_radians,
                AUDIT.UNITY_PLAYER.read_bytes(),
            )

    def test_quaternion_euler_degrees_to_radians_float32_candidate(self) -> None:
        radians = AUDIT.unity_quaternion_euler_degrees_to_radians_candidate(
            [0.0, 90.0, -45.0]
        )
        self.assertEqual(
            [AUDIT.float32_bits(value) for value in radians],
            [0x00000000, 0x3FC90FDB, 0xBF490FDB],
        )

    def test_mapped_unityplayer_quaternion_euler_wrapper_candidate(self) -> None:
        with AUDIT.UnityPlayerQuaternionEulerExecutor() as executor:
            quaternion = executor(
                [0.0, AUDIT.float32_from_bits(0x3F490FDB), 0.0]
            )
        self.assertEqual(
            [AUDIT.float32_bits(value) for value in quaternion],
            [0x00000000, 0x3EC3EF16, 0x00000000, 0x3F6C835E],
        )

    def test_native_disabled_distance_falloff_is_one(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.GET_LIGHT_FALLOFF_FILE_OFFSET)
            body = stream.read(AUDIT.GET_LIGHT_FALLOFF_SIZE)
            stream.seek(AUDIT.GET_LIGHT_FALLOFF_DEFAULT_FILE_OFFSET)
            default = stream.read(4)
        result = AUDIT.validate_light_falloff_native(body, default)
        self.assertEqual(result["selectedRowsResult"], 1.0)

    def test_installed_half_conversion_and_pair_layout(self) -> None:
        self.assertEqual(AUDIT.f32_to_f16_bits(0.0), 0x0000)
        self.assertEqual(AUDIT.f32_to_f16_bits(-0.0), 0x8000)
        self.assertEqual(AUDIT.f32_to_f16_bits(1.0), 0x3C00)
        self.assertEqual(AUDIT.f32_to_f16_bits(-2.0), 0xC000)
        self.assertEqual(
            AUDIT.pack_two_half_words(1.0, -2.0),
            0xC0003C00,
        )

    def test_native_obb_half_pack_layout(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PACK_TWO_HALF_FILE_OFFSET)
            pack_body = stream.read(AUDIT.PACK_TWO_HALF_SIZE)
            stream.seek(AUDIT.F32_TO_F16_FILE_OFFSET)
            helper_body = stream.read(AUDIT.F32_TO_F16_BODY_SIZE)
            stream.seek(AUDIT.F32_TO_F16_MAGIC_FILE_OFFSET)
            magic = stream.read(4)
            stream.seek(AUDIT.F32_TO_F16_SCALE_FILE_OFFSET)
            scale = stream.read(4)
            stream.seek(AUDIT.DEGREES_TO_RADIANS_FILE_OFFSET)
            degrees_to_radians = stream.read(4)
        result = AUDIT.validate_obb_pack_native(
            pack_body, helper_body, magic, scale, degrees_to_radians
        )
        self.assertEqual(
            result["packTwoHalfValuesAsFloat"]["methodIndex"],
            288325,
        )
        self.assertEqual(
            result["prepareCpuDataPackOrder"][3],
            "inverse row1 zw -> record6.x",
        )

    def test_changed_half_helper_fails_closed(self) -> None:
        with AUDIT.GAME_ASSEMBLY.open("rb") as stream:
            stream.seek(AUDIT.PACK_TWO_HALF_FILE_OFFSET)
            pack_body = stream.read(AUDIT.PACK_TWO_HALF_SIZE)
            stream.seek(AUDIT.F32_TO_F16_FILE_OFFSET)
            helper_body = bytearray(stream.read(AUDIT.F32_TO_F16_BODY_SIZE))
            stream.seek(AUDIT.F32_TO_F16_MAGIC_FILE_OFFSET)
            magic = stream.read(4)
            stream.seek(AUDIT.F32_TO_F16_SCALE_FILE_OFFSET)
            scale = stream.read(4)
            stream.seek(AUDIT.DEGREES_TO_RADIANS_FILE_OFFSET)
            degrees_to_radians = stream.read(4)
        helper_body[0x42] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=gacha_deferred_light_data; check=f32_to_f16_body_sha256;.*"
            r"expected=.*actual=",
        ):
            AUDIT.validate_obb_pack_native(
                pack_body,
                bytes(helper_body),
                magic,
                scale,
                degrees_to_radians,
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
        self.assertEqual({row["shadowCasterProperties"] for row in rows}, {6})
        self.assertEqual({row["pointShadowCasterFaces"] for row in rows}, {-1})
        self.assertEqual({row["lightShadowCasterMode"] for row in rows}, {0})

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

    def test_selected_room_obb_half_payloads(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        recovered = [AUDIT.recover_obb_pack(row) for row in rows]
        self.assertEqual(
            recovered[0]["nativeInverseCandidateWordHex"],
            [
                "0x800030E8",
                "0xAF310000",
                "0x3E788000",
                "0x49348000",
                "0x80000000",
                "0xAA842DD7",
            ],
        )
        self.assertEqual(
            recovered[2]["signedZeroNormalizedCandidateWordHex"][4],
            "0x00001A03",
        )
        self.assertEqual(recovered[0]["oneFloat32UlpSensitiveHalfLanes"], [0])
        self.assertTrue(
            all(not row["oneFloat32UlpSensitiveHalfLanes"] for row in recovered[1:])
        )
        self.assertTrue(
            all(row["maximumAuthoredCornerBoundaryError"] < 0.003 for row in recovered)
        )

    def test_selected_room_record0_rgb_payloads(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        recovered = [AUDIT.recover_record0_color(row) for row in rows]
        self.assertEqual(
            recovered[0]["record0RgbBits"],
            ["0x42C80000", "0x427432C1", "0x41ACB03D"],
        )
        self.assertEqual(
            recovered[9]["record0RgbBits"],
            ["0x41F00000", "0x414DC57F", "0x3F7E3E9C"],
        )
        self.assertTrue(all(row["falloff"] == 1.0 for row in recovered))
        self.assertTrue(all(row["flickerScale"] == 1.0 for row in recovered))

    def test_selected_room_record0_discriminator_payloads(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        recovered = [AUDIT.recover_record0_discriminator(row) for row in rows]
        self.assertEqual(recovered[0]["record0WBits"], "0x00000000")
        self.assertTrue(
            all(row["record0WBits"] == "0x3F800000" for row in recovered[1:])
        )
        shadow_spot = copy.deepcopy(rows[0])
        shadow_spot["shadowOnly"] = True
        self.assertEqual(
            AUDIT.recover_record0_discriminator(shadow_spot)["record0W"], 2.0
        )

    def test_selected_room_record1_inverse_range_payloads(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        recovered = [AUDIT.recover_record1_inverse_range(row) for row in rows]
        self.assertEqual(
            [row["record1WBits"] for row in recovered],
            [
                "0x3DCCCCCD",
                "0x3E115050",
                "0x3DCCCCCD",
                "0x3DCCCCCD",
                "0x3D924925",
                "0x3E4CCCCD",
                "0x3D924925",
                "0x3E4CCCCD",
                "0x3E13CEC6",
                "0x3D4CCCCD",
                "0x3D888889",
            ],
        )

    def test_selected_room_record2_static_payloads(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        recovered = [AUDIT.recover_record2_static_terms(row) for row in rows]
        self.assertEqual(recovered[0]["record2ZBits"], "0x3EAF1D40")
        self.assertEqual(recovered[0]["record2WBits"], "0x402F4D02")
        self.assertEqual(
            sum(row["record2ZBits"] == "0x41900000" for row in recovered), 4
        )
        self.assertEqual(
            sum(row["record2ZBits"] == "0xBF800000" for row in recovered), 6
        )
        self.assertEqual(sum(row["record2WClosed"] for row in recovered), 1)

    def test_unknown_record1_range_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        row = copy.deepcopy(AUDIT.room_light_rows(population, hierarchy)[0])
        row["range"] = 3.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_record1_range_known; source=.*Light.*; "
            r"expected=True; actual=False",
        ):
            AUDIT.recover_record1_inverse_range(row)

    def test_changed_record2_input_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        rows = AUDIT.room_light_rows(population, hierarchy)
        changed_spot = copy.deepcopy(rows[0])
        changed_spot["outerSpotAngleDegrees"] = 139.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_record2_spot_angles; source=.*Light.*; expected=.*actual=",
        ):
            AUDIT.recover_record2_static_terms(changed_spot)
        changed_point = copy.deepcopy(rows[1])
        changed_point["linearLightLength"] = 2.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_record2_point_length; source=.*Light.*; "
            r"expected=True; actual=False",
        ):
            AUDIT.recover_record2_static_terms(changed_point)

    def test_unknown_record0_light_type_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        row = copy.deepcopy(AUDIT.room_light_rows(population, hierarchy)[0])
        row["unityLightType"] = 7
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_record0_supported_light_type; source=.*Light.*; "
            r"expected=True; actual=False",
        ):
            AUDIT.recover_record0_discriminator(row)

    def test_unknown_record0_color_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        row = copy.deepcopy(AUDIT.room_light_rows(population, hierarchy)[0])
        row["color"][1] = 0.5
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_record0_authored_color_known; source=.*Light.*; "
            r"expected=True; actual=False",
        ):
            AUDIT.recover_record0_color(row)

    def test_enabled_room_animation_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        first = next(
            row
            for row in hierarchy["lights"]
            if row["rarityGroup"] == "SceneLight6Rarity"
            and row["name"] == AUDIT.EXPECTED_ROOM_ORDER[0]
        )
        path_id = int(first["lightPathId"])
        path_hex = f"{path_id & ((1 << 64) - 1):016X}"
        target = next(AUDIT.ROOM_LIGHT_ROOT.glob(f"*p{path_hex}.json"))
        changed = json.loads(target.read_text(encoding="utf-8"))
        changed["m_LightAnimationSetting"]["enableLightAnimation"] = True
        original_read_text = Path.read_text

        def changed_read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path == target:
                return json.dumps(changed)
            return original_read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", changed_read_text):
            with self.assertRaisesRegex(
                AssertionError,
                rf"check=room_{path_id}_light_animation_enabled; source=.*Light.*; "
                r"expected=False; actual=True",
            ):
                AUDIT.room_light_rows(population, hierarchy)

    def test_non_y_obb_orientation_fails_closed(self) -> None:
        population = json.loads(AUDIT.GACHA_POPULATION.read_text(encoding="utf-8"))
        hierarchy = json.loads(AUDIT.ROOM_HIERARCHY.read_text(encoding="utf-8"))
        row = copy.deepcopy(AUDIT.room_light_rows(population, hierarchy)[0])
        row["cullingBoxOrientationZxyDegrees"]["x"] = 1.0
        with self.assertRaisesRegex(
            AssertionError,
            r"check=room_.*_obb_orientation_x_zero; source=.*Light.*; "
            r"expected=True; actual=False",
        ):
            AUDIT.recover_obb_pack(row)

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
