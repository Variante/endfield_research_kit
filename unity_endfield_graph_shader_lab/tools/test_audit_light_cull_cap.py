#!/usr/bin/env python3
"""Focused tests for the recovered retail punctual-light cap validator."""

from __future__ import annotations

import importlib.util
import json
import struct
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
    def test_movss_displacement_counter_covers_rex_prefixes(self) -> None:
        body = bytes.fromhex("f30f104018 f3410f104018 f30f10c0")
        self.assertEqual(AUDIT.count_legacy_movss_disp_loads(body, 0x18), 2)

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

    def test_managed_streaming_binding_set_excludes_hgtree(self) -> None:
        result = AUDIT.validate_native_handoff(
            AUDIT.read_native_method_bodies()
        )["managedStreamingComponentBindings"]
        self.assertEqual(result["directCallCount"], 9)
        self.assertEqual(
            [row["bitIndex"] for row in result["bindings"]],
            [25, 14, 19, 12, 32, 33, 29, 15, 40],
        )
        self.assertFalse(result["hgtreeManagedBindingPresent"])

    def test_changed_managed_streaming_binding_fails_closed(self) -> None:
        bodies = AUDIT.read_native_method_bodies()
        changed = bytearray(bodies["streaming_scene_manager_ctor"])
        changed[0x2BF6] = 0x02
        bodies["streaming_scene_manager_ctor"] = bytes(changed)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=managed_streaming_HGVolumetricCloud_component_type; "
            r"source=.*GameAssembly.dll; expected=.*actual=",
        ):
            AUDIT.validate_native_handoff(bodies, verify_hashes=False)

    def test_hgmesh_renderer_data_inventory_excludes_component67(self) -> None:
        result = AUDIT.validate_hgmesh_renderer_data_inventory(
            verify_source_hash=False
        )
        self.assertEqual(result["corpus"]["objectCount"], 117)
        self.assertEqual(result["corpus"]["entityDescriptorCount"], 1449)
        self.assertEqual(result["component67"]["descriptorCount"], 0)
        self.assertFalse(result["component67"]["present"])

    def test_hgmesh_renderer_data_component67_drift_fails_closed(self) -> None:
        inventory = json.loads(
            AUDIT.HGMESH_RENDERER_DATA_INVENTORY.read_text(encoding="utf-8")
        )
        inventory["corpus"]["componentIdCounts"]["67"] = 1
        inventory["component67"]["descriptorCount"] = 1
        inventory["component67"]["present"] = True
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=hgmesh_renderer_data_component_counts; "
            r"source=.*hgmesh_renderer_data_component_inventory.json; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_hgmesh_renderer_data_inventory(
                inventory, verify_source_hash=False
            )

    def test_hgtree_native_serialized_type_census(self) -> None:
        result = AUDIT.validate_hgtree_native_serialized_type_census(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        rows = {
            row["name"]: row["classId"]
            for row in result["nativeDescriptorRows"]
        }
        self.assertEqual(rows["HGTree"], 0x2C9CB981)
        self.assertEqual(rows["HGTreeData"], 0x59383C91)
        self.assertEqual(rows["HGMeshRendererData"], 0x50F4EE0C)
        self.assertEqual(result["controlledFullScan"]["mapEntryCount"], 117)
        self.assertEqual(result["hgtreeTopLevelObjectCount"], 0)
        self.assertEqual(result["hgtreeDataTopLevelObjectCount"], 0)

    def test_changed_hgtree_native_class_id_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1821252F8 and size == 8:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=hgtree_native_serialized_type_HGTree_descriptor_raw; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_hgtree_native_serialized_type_census(image)

    def test_hgtree_top_level_object_count_drift_fails_closed(self) -> None:
        census = json.loads(
            AUDIT.HGTREE_NATIVE_SERIALIZED_TYPE_CENSUS.read_text(
                encoding="utf-8"
            )
        )
        census["controlledFullScan"]["typeCounts"]["HGTree"] = 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=hgtree_native_serialized_census_map_type_counts; "
            r"source=.*hgtree_native_serialized_type_census.json; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_hgtree_native_serialized_type_census(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER), census
            )

    def test_streaming_scene_v2_payload_census(self) -> None:
        result = AUDIT.validate_streaming_scene_v2_payload_census(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER),
            AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
        )
        self.assertEqual(result["serializedMapConfigs"]["configCount"], 83)
        self.assertEqual(result["streamingPayloads"]["fileCount"], 51012)
        self.assertEqual(
            result["nativeEntityDispatch"]["tags"][1],
            {"tag": 2, "name": "NativeECS"},
        )
        self.assertEqual(
            result["component67Owners"]["entityTypes"][1]["name"],
            "MergedRenderCollider",
        )
        self.assertEqual(
            result["component67InitialData"]["runtimeProducer"][
                "archetypeInitialDataCopy"
            ],
            "0x1801F95E0",
        )
        self.assertTrue(
            result["component67InitialData"]["fullScan"][
                "component67OwnerSetExactPerMapScope"
            ]
        )
        self.assertEqual(
            result["component67InitialData"]["fullScan"][
                "distinctComponent67EntityCountByMapScope"
            ],
            1230041,
        )
        self.assertEqual(
            result["component67InitialData"]["initialState"][
                "reservedWordAt0x06"
            ],
            0,
        )
        self.assertEqual(
            result["component67InitialData"]["initialState"][
                "reservedWordEntityCount"
            ],
            1305818,
        )
        self.assertEqual(
            result["streamingPayloads"]["ecsEntityTypes"][7]["entityCount"],
            2576964,
        )
        self.assertEqual(
            result["streamingPayloads"]["hgtreeBit41ComponentCount"], 0
        )
        self.assertEqual(
            result["dynamicStreaming"]["initAndStreaming"][
                "componentEntryCount"
            ],
            0,
        )
        self.assertEqual(
            result["dynamicStreaming"]["fbMain"]["treeRootCompCount"],
            2828,
        )

    def test_streaming_scene_v2_hgtree_count_drift_fails_closed(self) -> None:
        census = json.loads(
            AUDIT.STREAMING_SCENE_V2_PAYLOAD_CENSUS.read_text(
                encoding="utf-8"
            )
        )
        census["streamingPayloads"]["hgtreeBit41ComponentCount"] = 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=streaming_scene_v2_census_payload_hgtree_bit41_count; "
            r"source=.*streaming_scene_v2_payload_census.json; "
            r"expected=0; actual=1",
        ):
            AUDIT.validate_streaming_scene_v2_payload_census(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER),
                AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
                census,
            )

    def test_streaming_scene_v2_merged_render_count_drift_fails_closed(self) -> None:
        census = json.loads(
            AUDIT.STREAMING_SCENE_V2_PAYLOAD_CENSUS.read_text(
                encoding="utf-8"
            )
        )
        census["streamingPayloads"]["ecsEntityTypes"][7]["entityCount"] += 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=streaming_scene_v2_census_payload_ecs_entity_types; "
            r"source=.*streaming_scene_v2_payload_census.json; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_streaming_scene_v2_payload_census(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER),
                AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
                census,
            )

    def test_component67_initial_data_count_drift_fails_closed(self) -> None:
        census = json.loads(
            AUDIT.STREAMING_SCENE_V2_PAYLOAD_CENSUS.read_text(
                encoding="utf-8"
            )
        )
        census["component67InitialData"]["fullScan"][
            "distinctComponent67EntityCountByMapScope"
        ] += 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=streaming_scene_v2_census_component67_initial_data; "
            r"source=.*streaming_scene_v2_payload_census.json; "
            r"expected=.*actual=",
        ):
            AUDIT.validate_streaming_scene_v2_payload_census(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER),
                AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
                census,
            )

    def test_changed_native_ecs_initial_data_copy_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801F95E0 and size == 0x41A:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=streaming_scene_v2_native_ecs_archetype_initial-data_copy_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_streaming_scene_v2_payload_census(
                    image, AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
                )

    def test_changed_merged_render_registration_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18116B6AB and size == 0x2F6:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=streaming_scene_v2_mergedrendercollider_type-9_callback_registration_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_streaming_scene_v2_payload_census(
                    image, AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
                )

    def test_changed_merged_render_enum_value_fails_closed(self) -> None:
        metadata = bytearray(AUDIT.GLOBAL_METADATA.read_bytes())
        values_offset = 36_439_024
        merged_render_data_index = 585_181
        metadata[values_offset + merged_render_data_index] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=streaming_ecs_entity_type_MergedRenderCollider_value; "
            r"source=.*global-metadata.dat; expected=9; actual=8",
        ):
            AUDIT.validate_streaming_scene_v2_payload_census(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER),
                AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
                metadata=bytes(metadata),
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
        self.assertEqual(
            result["screenSizeMinimumSquaredDataflow"][
                "scheduledBatchCoreDirectMovssDisplacement0x18Loads"
            ],
            0,
        )
        self.assertIn(
            "state+0x180",
            result["screenSizeMinimumSquaredDataflow"][
                "independentParentLODBiasSquaredFlow"
            ][0],
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
        runtime_layout = result["runtimeTransform"]["outputLayout"]
        self.assertEqual(
            [row["offset"] for row in runtime_layout["runtimeRecordInitialFields"]],
            ["0x00", "0x02", "0x04", "0x08", "0x0C", "0x10", "0x14"],
        )
        runtime_tail = runtime_layout["runtimeRecordFieldLifecycle"]
        self.assertTrue(runtime_tail["mutableRenderFlagsAt0x08"]["roleClosed"])
        self.assertEqual(
            runtime_tail["mutableRenderFlagsAt0x08"]["writtenValue"],
            "0x00100000",
        )
        self.assertEqual(
            runtime_tail["mutableRenderFlagsAt0x08"]["particleModes"],
            [2, 3, 4, 5],
        )
        self.assertTrue(
            runtime_tail["thirdResolvedResourceAt0x0C"][
                "consumerRoleClosed"
            ]
        )
        self.assertTrue(
            runtime_tail["thirdResolvedResourceAt0x0C"]["producerClosed"]
        )
        self.assertEqual(
            runtime_tail["thirdResolvedResourceAt0x0C"]["writerPaths"][0][
                "writeVirtualAddress"
            ],
            "0x181157AD1",
        )
        self.assertTrue(runtime_tail["rendererPropertyFlagsAt0x10"]["roleClosed"])
        self.assertEqual(
            runtime_tail["rendererPropertyFlagsAt0x10"]["preserveMask"],
            "0xFC07FBFD",
        )
        self.assertTrue(
            runtime_tail["enabledLightModesAt0x14"]["roleClosed"]
        )
        self.assertEqual(
            runtime_tail["enabledLightModesAt0x14"]["internalCallIndex"],
            204,
        )
        self.assertIn(
            "SetEntityEnabledLightModes_Injected",
            runtime_tail["enabledLightModesAt0x14"]["internalCallName"],
        )
        self.assertEqual(result["enabledLightModesInternalCall"]["index"], 204)
        self.assertEqual(
            result["enabledLightModesInternalCall"]["writerCoreVirtualAddress"],
            "0x1810D9110",
        )
        enabled_modes = runtime_tail["enabledLightModesAt0x14"]
        self.assertTrue(enabled_modes["passBitMeaningsClosed"])
        self.assertTrue(enabled_modes["nativeInitializationProducerClosed"])
        self.assertEqual(enabled_modes["rendererObjectFieldOffset"], "0x250")
        self.assertEqual(enabled_modes["rendererObjectDefault"], "0xFFFFFFFF")
        self.assertEqual(len(enabled_modes["nativeInitializationPaths"]), 3)
        self.assertEqual(
            enabled_modes["nativeInitializationPaths"][0][
                "writeVirtualAddress"
            ],
            "0x18042AACC",
        )
        self.assertIn(
            "constructorInput[+0x20] = renderer[+0x250]",
            enabled_modes["nativeInitializationPaths"][2]["equation"],
        )
        downstream = enabled_modes["downstreamSearchBoundary"]
        self.assertEqual(downstream["requestMaskJobOffset"], "0x44")
        self.assertEqual(downstream["testedRendererEntryOffset"], "0x1C")
        self.assertTrue(downstream["projectionHypothesisRetracted"])
        self.assertTrue(downstream["distinctMaskRoleClosed"])
        entry_mask = downstream["rendererEntryMask"]
        self.assertEqual(entry_mask["meaning"], "shader-supported light modes")
        self.assertEqual(entry_mask["entryStrideBytes"], 96)
        self.assertEqual(
            entry_mask["builderVirtualAddresses"],
            ["0x18109BE90", "0x18109C9D0"],
        )
        self.assertEqual(len(entry_mask["passNames"]), 31)
        self.assertEqual(entry_mask["passNames"][0], "GBuffer")
        self.assertEqual(entry_mask["passNames"][-1], "GPUParticleSimulate")
        pointer_boundary = downstream["runtimeRecordPointerBoundary"]
        self.assertEqual(
            pointer_boundary["consumerFunctions"],
            ["0x181129E0D", "0x18113781A"],
        )
        self.assertEqual(
            pointer_boundary["recordBaseEscapeCallSites"],
            ["0x18112A25A", "0x181137B81", "0x181137C84"],
        )
        self.assertEqual(
            pointer_boundary["escapeTargetRecordReads"], ["0x00"]
        )
        self.assertFalse(pointer_boundary["enabledLightModesReadObserved"])
        callback_false_positive = pointer_boundary["callbackAFalsePositive"]
        self.assertTrue(
            callback_false_positive["rejectedAsRuntimeRecord"]
        )
        self.assertEqual(
            [
                row["archetypeBit"]
                for row in callback_false_positive["componentColumnAccessors"]
            ],
            [127, 126],
        )
        self.assertEqual(enabled_modes["maskType"], "System.UInt32")
        self.assertEqual(enabled_modes["shaderLightModeLiteralCount"], 32)
        self.assertEqual(
            enabled_modes["shaderLightModeCombinedMask"], "0x7FFFFFFF"
        )
        managed_contract = result["enabledLightModesInternalCall"][
            "managedContract"
        ]
        literals = {
            row["name"]: row["value"]
            for row in managed_contract["shaderLightMode"]["literals"]
        }
        self.assertEqual(literals["GBuffer"], "0x00000001")
        self.assertEqual(literals["ShadowCaster"], "0x00000400")
        self.assertEqual(literals["DepthOnly"], "0x00000800")
        self.assertEqual(literals["GPUParticleSimulate"], "0x40000000")
        set_enabled_parameters = managed_contract["methods"][
            "setEntityEnabledLightModes"
        ]["parameters"]
        self.assertEqual(
            set_enabled_parameters[-1]["name"],
            "lightModeMask",
        )
        game_assembly_contract = result["enabledLightModesInternalCall"][
            "gameAssemblyContract"
        ]
        self.assertEqual(
            game_assembly_contract["perDrawApplyCall"]["targetVirtualAddress"],
            "0x18B3F9118",
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
        self.assertIn("reserved/alignment", ecs_state["fields"][6]["meaning"])
        accessor_closure = ecs_state["directAccessorClosure"]
        self.assertEqual(accessor_closure["directCallCount"], 25)
        self.assertEqual(accessor_closure["logicalCallerCount"], 21)
        self.assertEqual(
            accessor_closure["offlineControlFlowDataflow"][
                "fieldOffsetsModuloStride"
            ],
            [0, 1, 2, 3, 4, 5, 8, 15, 16],
        )
        self.assertEqual(
            accessor_closure["offlineControlFlowDataflow"][
                "reservedWordWriteCount"
            ],
            0,
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

    def test_changed_renderer_entry_pass_mask_builder_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18109BE90 and size == 0xB33:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_entry_pass_mask_builder_a_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_runtime_record_classifier_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181131FC0 and size == 0xDD:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_runtime_record_batch_flag_classifier_sha256; "
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

    def test_changed_renderer_runtime_property_flag_sync_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x180432CD0 and size == 0x1ED:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_runtime_property_flag_sync_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_set_enabled_light_modes_core_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810D9110 and size == 0x5F:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_factory_set_enabled_light_modes_core_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_renderer_enabled_light_modes_default_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18042BF10 and size == 0x1A9:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_base_constructor_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_shader_light_mode_bit_fails_closed(self) -> None:
        metadata = bytearray(AUDIT.GLOBAL_METADATA.read_bytes())
        sections = {}
        for section_index, section_name in enumerate(
            AUDIT.IL2CPP_METADATA_SECTION_NAMES
        ):
            sections[section_name] = struct.unpack_from(
                "<Ii", metadata, 8 + section_index * 8
            )
        defaults_offset, defaults_size = sections["fieldDefaultValues"]
        values_offset, _values_size = sections[
            "fieldAndParameterDefaultValueData"
        ]
        shadow_caster_field = AUDIT.HG_SHADER_LIGHT_MODE_FIELDS[
            "ShadowCaster"
        ][0]
        shadow_caster_data_index = None
        for position in range(
            defaults_offset, defaults_offset + defaults_size, 12
        ):
            field_index, _type_index, data_index = struct.unpack_from(
                "<iii", metadata, position
            )
            if field_index == shadow_caster_field:
                shadow_caster_data_index = data_index
                break
        self.assertIsNotNone(shadow_caster_data_index)
        metadata[values_offset + shadow_caster_data_index] ^= 1
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=enabled_light_modes_shader_light_mode_ShadowCaster_value; "
            r"source=.*global-metadata.dat; expected=1024; actual=1280",
        ):
            AUDIT.validate_unity_hgtree_renderer_boundary(
                AUDIT.PEImage(AUDIT.UNITY_PLAYER), metadata=bytes(metadata)
            )

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

    def test_changed_component67_direct_caller_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181000F10 and size == 0xC70:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_component67_direct_caller_181000F10_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_component67_accessor_call_site_drift_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        with mock.patch.object(AUDIT, "find_relative_call_sites", return_value=[]):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_component67_archetype_accessor_call_sites; "
                r"source=.*UnityPlayer.dll; expected=.*actual=\[\]",
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

    def test_changed_scheduled_cull_parallel_thunk_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181045F80 and size == 0xDE:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_scheduled_cull_parallel_batch_thunk_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_scheduled_culling_boundary(image)


if __name__ == "__main__":
    unittest.main()
