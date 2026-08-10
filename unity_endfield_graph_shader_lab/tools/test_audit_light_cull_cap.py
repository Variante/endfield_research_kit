#!/usr/bin/env python3
"""Focused tests for the recovered retail punctual-light cap validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("audit_light_cull_cap.py")
SPEC = importlib.util.spec_from_file_location("audit_light_cull_cap", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class LightCullCapAuditTests(unittest.TestCase):
    def write_fixture(
        self,
        root: Path,
        *,
        desktop_cap: int = 256,
        common_cap: int | None = None,
    ) -> None:
        contents = {
            "SettingFiles": "\n".join(AUDIT.EXPECTED_SETTING_FILES) + "\n",
            "HGRenderPipelineSettings": "\n\n".join(
                (
                    "[IncludeSettings]"
                    if route == "Common"
                    else f"[IncludeSettings@{route}]"
                )
                + f"\nincludeSettings = {file_name}"
                for route, file_name in AUDIT.EXPECTED_INCLUDE_ROUTES.items()
            )
            + "\n",
            "CommonSettings": (
                "[Lighting@1000]\n"
                + (
                    f"PunctualLightMaxCount = {common_cap}\n"
                    if common_cap is not None
                    else "OtherValue = 1\n"
                )
            ),
            "DesktopSettings": (
                "[Lighting@1000]\n"
                f"PunctualLightMaxCount = {desktop_cap}\n"
            ),
            "CloudDesktopOverride": "[Streaming@1000]\nchunkLoadRadius = 128\n",
            "ConsoleSettings": "[Lighting@1000]\nPunctualLightMaxCount = 256\n",
            "MobileSettings": (
                "[ECS@5000]\nCullingViewScreenSizeMin = 0.0\n\n"
                "[ECS@3000]\nCullingViewScreenSizeMin = 0.0\n\n"
                "[ECS@1000]\nCullingViewScreenSizeMin = 0.0\n\n"
                "[Lighting@1000]\nPunctualLightMaxCount = 32\n"
            ),
            "CinematicSettings": "[Lighting@1000]\nOtherValue = 1\n",
        }
        for logical_name, (file_name, _, _) in AUDIT.TEXT_ASSETS.items():
            (root / file_name).write_text(
                contents[logical_name], encoding="utf-8"
            )

    def test_successful_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root)
            _, caps = AUDIT.validate_settings_payloads(
                root, verify_hashes=False
            )
            self.assertEqual(caps, AUDIT.EXPECTED_CAP_DEFINITIONS)

    def test_wrong_desktop_cap_reports_expected_and_actual(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root, desktop_cap=128)
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=cap_definitions;.*"
                r"DesktopSettings.*128",
            ):
                AUDIT.validate_settings_payloads(root, verify_hashes=False)

    def test_unexpected_common_override_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root, common_cap=64)
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=cap_definitions;.*"
                r"CommonSettings.*64",
            ):
                AUDIT.validate_settings_payloads(root, verify_hashes=False)

    def test_unexpected_desktop_screen_threshold_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root)
            desktop = root / AUDIT.TEXT_ASSETS["DesktopSettings"][0]
            desktop.write_text(
                desktop.read_text(encoding="utf-8")
                + "\n[ECS@1000]\nCullingViewScreenSizeMin = 0.01\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=screen_threshold_definitions;.*"
                r"DesktopSettings.*0\.01",
            ):
                AUDIT.validate_settings_payloads(root, verify_hashes=False)

    def test_native_handoff_and_capture_row_contract(self) -> None:
        result = AUDIT.validate_native_handoff(AUDIT.read_native_method_bodies())
        self.assertEqual(result["resultAbi"]["sizeBytes"], 16)
        self.assertEqual(
            result["resultAbi"]["fields"]["visibleLightCount"]["offset"], 8
        )
        self.assertEqual(result["managedCallSites"]["maxCount"], 256)
        self.assertEqual(result["captureRowContract"]["elementStrideBytes"], 148)
        self.assertEqual(
            result["captureRowContract"]["validatedConsumerOffsets"]["lightPriority"],
            "0x70",
        )

    def test_changed_visible_light_stride_fails_closed(self) -> None:
        bodies = AUDIT.read_native_method_bodies()
        changed = bytearray(bodies["setup_state"])
        changed[0x1E8] = 0x95
        bodies["setup_state"] = bytes(changed)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; check=setup_state_priority_and_stride; "
            r"source=.*GameAssembly.dll; expected=.*actual=",
        ):
            AUDIT.validate_native_handoff(bodies, verify_hashes=False)

    def test_hgtree_component_managed_id_is_80_not_67(self) -> None:
        result = AUDIT.validate_native_handoff(
            AUDIT.read_native_method_bodies()
        )["managedHGTreeComponent"]
        self.assertEqual(result["metadataMethodIndex"], 478429)
        self.assertEqual(result["metadataToken"], "0x06000279")
        self.assertEqual(result["componentId"], 80)
        self.assertEqual(
            result["archetypeMask"]["highQwordMask"],
            "0x0000000000010000",
        )
        self.assertFalse(result["component67Match"])

    def test_render_object_lod_info_component_managed_id_is_6_not_67(
        self,
    ) -> None:
        result = AUDIT.validate_native_handoff(
            AUDIT.read_native_method_bodies()
        )["managedRenderObjectLODInfoComponent"]
        self.assertEqual(result["metadataMethodIndex"], 478390)
        self.assertEqual(result["metadataToken"], "0x06000252")
        self.assertEqual(result["componentId"], 6)
        self.assertFalse(result["component67Match"])

    def test_changed_hgtree_component_id_fails_closed(self) -> None:
        bodies = AUDIT.read_native_method_bodies()
        changed = bytearray(bodies["hgtree_component_get_id"])
        changed[1] = 67
        bodies["hgtree_component_get_id"] = bytes(changed)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=hgtree_component_get_id_body; "
            r"source=.*GameAssembly.dll; expected=.*actual=",
        ):
            AUDIT.validate_native_handoff(bodies, verify_hashes=False)

    def test_streaming_component_conversion_contract(self) -> None:
        result = AUDIT.validate_streaming_component_conversion(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(result["internalCall"]["index"], 677)
        enum = result["streamingComponentType"]
        self.assertEqual(enum["slotCount"], 43)
        self.assertEqual(enum["hlodGroupBitIndex"], 11)
        self.assertEqual(enum["hgtreeBitIndex"], 41)
        self.assertEqual(enum["selectedFields"]["HGTree"]["value"], 1 << 41)
        self.assertEqual(
            result["conversionContract"]["slotStrideBytes"], 0x308
        )
        self.assertFalse(
            result["managedComponentDisambiguation"][
                "component67MatchesEither"
            ]
        )

    def test_changed_streaming_hgtree_enum_value_fails_closed(self) -> None:
        metadata = bytearray(AUDIT.GLOBAL_METADATA.read_bytes())
        values_offset = 36_439_024
        hgtree_data_index = 585_112
        metadata[values_offset + hgtree_data_index] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=streaming_component_HGTree_value; "
            r"source=.*global-metadata.dat; expected=.*actual=",
        ):
            AUDIT.validate_streaming_component_conversion(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER), bytes(metadata)
            )

    def test_changed_streaming_converter_registry_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18117B010 and size == 0x1A5:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_streaming_streaming_scene_manager_registry_constructor_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_streaming_component_conversion(image)

    def test_unity_native_candidate_producer(self) -> None:
        result = AUDIT.validate_unity_native_producer(AUDIT.PEImage(AUDIT.UNITY_PLAYER))
        self.assertEqual(result["internalCall"]["index"], 3320)
        self.assertEqual(result["candidateRecord"]["sizeBytes"], 12)
        self.assertIn("maxCount output cap", result["closedBehavior"])

    def test_changed_unity_native_cap_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181052830:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=unity_native_output_max_count_cap; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_native_producer(image)

    def test_unity_scheduled_cull_view_constructor(self) -> None:
        result = AUDIT.validate_unity_cull_view_constructor(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(result["internalCall"]["index"], 3304)
        self.assertEqual(
            result["managedInputContract"]["cameraCullingMask"]["viewRecordOffset"],
            "0x04",
        )
        self.assertFalse(
            result["managedInputContract"]["sceneCullingMask"]["constructorRead"]
        )
        self.assertEqual(result["viewRecord"]["planeCount"], 6)
        self.assertEqual(
            result["candidateGateOrder"][0],
            "candidate synchronous visibility/AABB-plane result bit 0",
        )

    def test_changed_scheduled_cull_view_body_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18104A7A0 and size == 0x1082:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_cull_view_scheduled_constructor_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_cull_view_constructor(image)

    def test_unity_scheduled_culling_boundary(self) -> None:
        result = AUDIT.validate_unity_scheduled_culling_boundary(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(result["internalCall"]["index"], 3315)
        self.assertFalse(
            result["perViewVisibilityPredicate"][
                "screenSizeMinimumSquaredAt0x18Read"
            ]
        )
        self.assertNotIn("rendererCandidateRecord", result)

    def test_unity_hgtree_renderer_boundary(self) -> None:
        result = AUDIT.validate_unity_hgtree_renderer_boundary(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(result["internalCall"]["index"], 564)
        self.assertEqual(result["internalCall"]["entryCount"], 729)
        self.assertEqual(
            result["internalCall"]["targetVirtualAddress"], "0x1801D9D10"
        )
        self.assertEqual(result["registrationInternalCall"]["index"], 567)
        self.assertEqual(
            result["registrationInternalCall"]["targetVirtualAddress"],
            "0x1801DA040",
        )
        self.assertEqual(
            [row["index"] for row in result["unregistrationInternalCalls"]],
            [568, 569],
        )
        self.assertEqual(
            result["runtimeTransform"]["ownerCleanup"][
                "recordHandleOffset"
            ],
            "0x02",
        )
        self.assertEqual(
            result["runtimeTransform"]["ownerCleanup"][
                "recordBatchKeyOffset"
            ],
            "0x04",
        )
        self.assertEqual(
            result["treeInstance"]["rendererElementType"], "HGTreeRenderer"
        )
        self.assertEqual(result["rendererRecord"]["sizeBytes"], 28)
        self.assertEqual(
            result["rendererRecord"]["fields"][-1],
            {
                "name": "lodScreenSizeMinSquared",
                "offset": "0x18",
                "sizeBytes": 4,
            },
        )
        self.assertTrue(
            result["separationFromScheduledCulling"][
                "separateEntryAndOwnershipProven"
            ]
        )
        self.assertFalse(
            result["runtimeJobs"][
                "serializedRecordStrideObservedInPinnedJobSlices"
            ]
        )
        self.assertEqual(
            result["runtimeTransform"]["outputLayout"]["capacityBuckets"],
            [1, 2, 4, 8, 16, 32],
        )
        self.assertEqual(
            result["runtimeTransform"]["outputLayout"][
                "lodArrayOffsetEquation"
            ],
            "4 + 24 * capacity",
        )
        self.assertEqual(
            result["lodSelection"]["selectionBoundary"],
            "lower bound exclusive; upper bound inclusive",
        )
        self.assertIn(
            "lodFloat2.y < distanceSquared <= lodFloat2.x",
            result["lodSelection"]["directDistanceEquation"],
        )
        self.assertEqual(
            result["lodSelection"]["dispatchPacket"]["lodBiasPacketOffset"],
            "0x3E",
        )
        self.assertEqual(
            result["lodSelection"]["payload"][
                "artTagLODStreamingOffsetOffset"
            ],
            "0x82C",
        )
        self.assertIn(
            "(1 + lodBias / 255)^2",
            result["lodSelection"]["lodBiasEncoding"][
                "viewLodBiasMultiplier"
            ],
        )
        self.assertIn(
            "clamp to [0, lodCount-1]",
            result["lodSelection"]["artTagLODStreamingOffset"][
                "selectionUse"
            ],
        )
        ecs_state = result["lodSelection"]["ecsStateRecord"]
        self.assertEqual(ecs_state["archetypeComponentBitIndex"], 67)
        self.assertEqual(
            ecs_state["indexedAccessorVirtualAddress"], "0x1811648A0"
        )
        self.assertEqual(ecs_state["strideBytes"], 24)
        self.assertEqual(ecs_state["sentinelLodIndex"], 8)
        self.assertEqual(
            [field["offset"] for field in ecs_state["fields"]],
            [
                "0x00",
                "0x01",
                "0x02",
                "0x03",
                "0x04",
                "0x05",
                "0x06",
                "0x08",
                "0x10",
            ],
        )
        self.assertIn(
            "clear record+0x04 and set record+0x05",
            ecs_state["availabilityWriter"]["complete"],
        )
        initial_completion = ecs_state["initialCompletionWriter"]
        self.assertEqual(
            initial_completion["normalTransition"]["availableMaskAt0x05"],
            1,
        )
        self.assertEqual(
            initial_completion["fallbackTransition"]["desiredLodAt0x01"],
            8,
        )
        self.assertIn(
            "does not write record+0x00",
            initial_completion["closedBoundary"],
        )
        direct_initializer = ecs_state["directAvailabilityInitializer"]
        self.assertEqual(
            direct_initializer["allLodsBranch"]["pendingMaskAt0x04"],
            0,
        )
        self.assertEqual(
            direct_initializer["terminalLodBranch"]["rangeEnd"],
            "cumulativeRange[lodIndex]",
        )
        component_mask = ecs_state["componentIdMaskRegistration"]
        self.assertEqual(component_mask["internalCallIndex"], 712)
        self.assertEqual(
            component_mask["component67Result"]["highQwordMask"],
            "0x0000000000000008",
        )
        self.assertEqual(
            component_mask["hgtreeComponent80Result"]["highQwordMask"],
            "0x0000000000010000",
        )
        self.assertIn(
            "is not HGTreeComponent",
            component_mask["boundary"],
        )
        descriptor_core = ecs_state["archetypeDescriptorRegistrationCore"]
        self.assertEqual(descriptor_core["virtualAddress"], "0x1801FAEC0")
        self.assertEqual(descriptor_core["descriptorStrideBytes"], 8)
        self.assertEqual(
            [field["offset"] for field in descriptor_core["descriptorFields"]],
            ["0x00", "0x02", "0x04"],
        )
        self.assertEqual(descriptor_core["firstComponentDataOffsetBytes"], 8)
        self.assertIn("runtime descriptor", descriptor_core["component67Implication"])
        type_identity = ecs_state["nativeScriptingTypeIdentity"]
        self.assertTrue(type_identity["proxyToNativeTypeNameClosed"])
        self.assertEqual(
            type_identity["strings"]["native_type_name"]["value"],
            "HGTreeComponent",
        )
        self.assertEqual(
            type_identity["strings"]["managed_namespace"]["value"],
            "UnityEngine.HyperGryph.ECS",
        )
        self.assertIn(
            "HGTreeComponent is id 80",
            type_identity["boundary"],
        )
        self.assertEqual(type_identity["managedGetId"]["componentId"], 80)
        self.assertTrue(ecs_state["managedHGTreeComponentIdMappingClosed"])
        self.assertEqual(ecs_state["managedHGTreeComponentId"], 80)
        self.assertFalse(ecs_state["component67MatchesHGTreeComponent"])
        self.assertFalse(ecs_state["component67NativeIdentityClosed"])
        self.assertEqual(
            result["lodControlInternalCalls"]["cullingSystem"][-1]["index"],
            3303,
        )
        self.assertEqual(
            result["lodControlInternalCalls"]["lodStreamingSystem"][-1][
                "index"
            ],
            280,
        )
        self.assertNotIn("virtual slot", " ".join(result["callChain"]))

    def test_changed_hgtree_renderer_binding_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801D9D10 and size == 0x82:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_create_renderer_list_binding_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_lod_control_body_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1800F9230 and size == 0x14C:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_art_tag_lod_bias_setter_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_ecs_entity_type_registration_core_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801FAEC0 and size == 0x425:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_ecs_entity_type_registration_core_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_runtime_transform_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810C5F30 and size == 0x6BC:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_serialized_to_runtime_transform_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_owner_cleanup_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810BCE00 and size == 0x48A:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_runtime_transform_owner_cleanup_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_lod_ecs_availability_writer_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810842E0 and size == 0x835:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_availability_writer_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_lod_ecs_initial_completion_writer_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181159010 and size == 0x398:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_initial_completion_writer_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_component_proxy_registration_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1807EEEE0 and size == 0x2A:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_component_proxy_registration_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_component_type_name_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_cstring = image.cstring

        def changed_cstring(virtual_address: int) -> str:
            if virtual_address == 0x181DA5338:
                return "ChangedHGTreeComponent"
            return original_cstring(virtual_address)

        with mock.patch.object(image, "cstring", changed_cstring):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_component_native_type_name; "
                r"source=.*UnityPlayer.dll; expected='HGTreeComponent'; "
                r"actual='ChangedHGTreeComponent'",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_ecs_component_mask_binding_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801E0D90 and size == 0x1A3:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_ecs_entity_type_component_mask_binding_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_direct_availability_initializer_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181157760 and size == 0x7F9:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_direct_availability_initializer_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_hgtree_icall_index_out_of_bounds_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        with mock.patch.object(AUDIT, "UNITY_HG_ICALL_COUNT", 564):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hg_icall_create_renderer_list_index_in_bounds; "
                r"source=.*UnityPlayer.dll; expected=True; actual=False",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_scheduled_cull_predicate_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x180FEAEF0 and size == 0x60:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_scheduled_cull_camera_type_0x80_sphere_predicate_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_scheduled_culling_boundary(image)


if __name__ == "__main__":
    unittest.main()
