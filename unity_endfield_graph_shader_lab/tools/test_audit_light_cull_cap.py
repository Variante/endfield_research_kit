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
    def write_ifix_fixture(
        self,
        path: Path,
        *,
        target_count: int = 1,
        target_type: str = "Beyond.Gameplay.Test",
    ) -> None:
        targets = [
            {
                "type": target_type,
                "method": "Tick",
                "parameters": [],
                "implementation_index": 0,
            }
            for _ in range(target_count)
        ]
        state = {
            "schema": "endfield.charinfo.installed-ifix-patch-state.v1",
            "source_build": {
                "game_assembly": {
                    "sha256": AUDIT.EXPECTED_HASHES["game_assembly"]
                }
            },
            "vfs_state": {
                "persistent_overlay": {
                    "file": {"sha256": "a" * 64}
                }
            },
            "patch_format": {"target_count": target_count, "terminal_int32": 0},
            "targets": targets,
            "refresh": {
                "tool": "refresh_installed_ifix_patch_state.py",
                "source_patch_sha256": "a" * 64,
            },
        }
        path.write_text(json.dumps(state), encoding="utf-8")

    def test_ifix_state_accepts_current_self_consistent_target_count(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "ifix.json"
            self.write_ifix_fixture(path, target_count=2)
            report_hash, state = AUDIT.validate_ifix_state(path)
            self.assertEqual(len(report_hash), 64)
            self.assertEqual(state["patch_format"]["target_count"], 2)

    def test_ifix_state_count_mismatch_reports_expected_and_actual(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "ifix.json"
            self.write_ifix_fixture(path, target_count=2)
            state = json.loads(path.read_text(encoding="utf-8"))
            state["patch_format"]["target_count"] = 1
            path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=ifix_target_count_matches_targets; source=.*"
                r"expected=2; actual=1",
            ):
                AUDIT.validate_ifix_state(path)

    def test_ifix_state_rejects_hgrp_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "ifix.json"
            self.write_ifix_fixture(
                path,
                target_type="HG.Rendering.Runtime.LightClusteringPassConstructor",
            )
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=ifix_hgrp_targets; source=.*",
            ):
                AUDIT.validate_ifix_state(path)

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

    def test_scene_culling_mask_is_ifix_payload_producer(self) -> None:
        result = AUDIT.validate_scene_culling_mask_source()
        self.assertEqual(result["ifixTargetId"], 793)
        self.assertFalse(result["ordinaryManagedCameraComputation"])
        self.assertIn("IFix/future-patch", result["nativeValueBoundary"])

    def test_changed_scene_culling_mask_ifix_target_fails_closed(self) -> None:
        source_text = AUDIT.HG_UTILS_SOURCE.read_text(encoding="utf-8")
        changed = source_text.replace(
            "GetPatch(793, 0LL)", "GetPatch(794, 0LL)", 1
        )
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=scene_culling_mask_ifix_target; source=.*HGUtils.cs; "
            r"expected=1; actual=0",
        ):
            AUDIT.validate_scene_culling_mask_source(
                source_text=changed, verify_source_hash=False
            )

    def test_light_clustering_preserves_sorted_original_row_indices(self) -> None:
        result = AUDIT.validate_light_clustering_consumer()
        self.assertEqual(result["sourceProjection"]["maxRows"], 256)
        self.assertEqual(result["sourceProjection"]["rowStrideBytes"], 148)
        self.assertTrue(result["survivorIndexTransport"]["postSortCopy"])
        self.assertEqual(
            result["survivorIndexTransport"]["elementType"], "Int32"
        )
        self.assertIn(
            "PreparePunctualLightShadowCasters",
            result["survivorIndexTransport"]["consumer"],
        )

    def test_changed_light_clustering_index_consumer_fails_closed(self) -> None:
        source_text = AUDIT.LIGHT_CLUSTER_SOURCE.read_text(encoding="utf-8")
        changed = source_text.replace(
            "PreparePunctualLightShadowCasters",
            "PreparePunctualLightShadowCastersChanged",
            1,
        )
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=light_cluster_shadow_index_consumer; "
            r"source=.*LightClusteringPassConstructor.cs; expected=True; actual=False",
        ):
            AUDIT.validate_light_clustering_consumer(
                source_text=changed, verify_source_hash=False
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

    def test_complete_managed_ecs_get_id_surface_excludes_67(self) -> None:
        result = AUDIT.validate_managed_ecs_get_id_census(
            AUDIT.GLOBAL_METADATA.read_bytes(),
            AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
        )
        self.assertEqual(result["declaredGetIdCount"], 30)
        self.assertEqual(result["concreteGetIdCount"], 29)
        self.assertNotIn(67, result["exposedComponentIds"])
        self.assertFalse(result["component67Present"])
        by_type = {row["type"].rsplit(".", 1)[-1]: row for row in result["rows"]}
        self.assertEqual(by_type["HGTreeComponent"]["componentId"], 80)
        self.assertEqual(
            by_type["RenderObjectLODInfoComponent"]["componentId"], 6
        )
        self.assertIsNone(by_type["IComponentECS"]["componentId"])

    def test_managed_ecs_get_id_metadata_drift_fails_closed(self) -> None:
        metadata = bytearray(AUDIT.GLOBAL_METADATA.read_bytes())
        sections = {
            name: struct.unpack_from("<Ii", metadata, 8 + index * 8)
            for index, name in enumerate(AUDIT.IL2CPP_METADATA_SECTION_NAMES)
        }
        method_offset, _ = sections["methods"]
        hgtree_method_index = AUDIT.MANAGED_ECS_GET_ID_ROWS[
            "HGTreeComponent"
        ][2]
        token_offset = method_offset + hgtree_method_index * 32 + 20
        struct.pack_into("<I", metadata, token_offset, 0x0600FFFF)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=managed_ecs_get_id_HGTreeComponent_method_token; "
            r"source=.*global-metadata.dat; expected=.*actual=",
        ):
            AUDIT.validate_managed_ecs_get_id_census(
                bytes(metadata), AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
            )

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
        registry = result["component67Owners"]["nativeCallbackRegistry"]
        self.assertEqual(registry["installerCallCount"], 105)
        self.assertEqual(
            [row["installerCallCount"] for row in registry["constructors"]],
            [52, 53],
        )
        self.assertEqual(
            [
                row["name"]
                for row in registry["component67Owners"][0][
                    "activeTransitions"
                ]
            ],
            [
                "UnloadedToLoading",
                "LoadingToLoaded",
                "UnloadingToUnloaded",
                "LoadingToUnloaded",
            ],
        )
        self.assertFalse(
            registry["component67OwnerRegistriesReplacedByManagedScript"]
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

    def test_native_ecs_callback_registry_contract(self) -> None:
        transitions = AUDIT.validate_streaming_byte_enum_fields(
            AUDIT.GLOBAL_METADATA.read_bytes(),
            AUDIT.GLOBAL_METADATA,
            "streaming_entity_transition",
            AUDIT.STREAMING_ENTITY_TRANSITION_FIELDS,
        )
        result = AUDIT.validate_native_ecs_callback_registry(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER),
            AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
            transitions,
        )
        self.assertEqual(result["registryLayout"]["sizeBytes"], 0x288)
        self.assertEqual(result["registryLayout"]["callbackSlotCount"], 10)
        self.assertEqual(
            result["managedScriptOverrides"],
            [
                {"entityType": 1, "entityTypeName": "Water"},
                {"entityType": 13, "entityTypeName": "WaterDecal"},
            ],
        )

    def test_native_ecs_callback_target_drift_fails_closed(self) -> None:
        transitions = AUDIT.validate_streaming_byte_enum_fields(
            AUDIT.GLOBAL_METADATA.read_bytes(),
            AUDIT.GLOBAL_METADATA,
            "streaming_entity_transition",
            AUDIT.STREAMING_ENTITY_TRANSITION_FIELDS,
        )
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18116B9F3 and size == 7:
                data[3] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=native_ecs_system_type0_slot1_callback; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_native_ecs_callback_registry(
                    image,
                    AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
                    transitions,
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
        self.assertEqual(result["candidateCoreBody"][0]["sizeBytes"], 0x4E1)
        self.assertEqual(
            result["resultLifetimeWrapper"]["emptyViewHandle"]["input"],
            -1,
        )
        self.assertIn(
            "copies converted pointer/count to the hidden sret result",
            result["resultLifetimeWrapper"]["nonEmptyFlow"],
        )
        self.assertEqual(
            result["visibleLightProducer"]["allocationSizeEquation"],
            "inputCount * 0x94",
        )
        self.assertEqual(result["visibleLightProducer"]["rowStrideBytes"], 148)
        self.assertIn(
            "row+0x68 <- source+0x18, or source+0x138 for source type 3/4",
            result["visibleLightProducer"]["writtenRawFieldMappings"],
        )
        self.assertIn(
            "row+0x84 <- constant zero (converter r12d is zero throughout the loop)",
            result["visibleLightProducer"]["writtenRawFieldMappings"],
        )
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

    def test_changed_unity_native_candidate_core_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181051A40 and size == 0x4E1:
                data[0x200] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_culling_candidate_core_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_native_producer(image)

    def test_changed_visible_light_producer_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x180543CE0 and size == 0x1B0:
                data[0x80] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_visible_light_producer_candidate_vector_to_visible_light_rows_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_native_producer(image)

    def test_changed_unity_native_result_wrapper_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181050FC0 and size == 0x133:
                data[0x50] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_culling_wrapper_result_lifetime_wrapper_sha256; "
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
        self.assertNotIn(
            "a separate consumer, if any, for the forwarded sceneCullingMask slot",
            result["evidenceBoundary"]["open"],
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

    def test_unity_cull_view_consumer_surface(self) -> None:
        result = AUDIT.validate_unity_cull_view_consumer_surface(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(
            [row["index"] for row in result["internalCallSurface"]["entries"]],
            [3304, 3306, 3307, 3313, 3314, 3315, 3316, 3317],
        )
        census = result["consumerCensus"]
        self.assertFalse(census["consumerFound"])
        self.assertFalse(census["postDispatchPacketCopy"])
        self.assertEqual(
            census["scheduledViewLoopReadOffsets"],
            ["0x20", "0x28", "0x2C", "0x54"],
        )
        self.assertIn("manager+0x58", census["childViewSeparation"])
        self.assertIn("manager+0x158", census["uniqueIdRegistry"])
        self.assertNotIn(
            "any separate consumer of the forwarded sceneCullingMask slot",
            result["evidenceBoundary"]["open"],
        )

    def test_changed_cull_view_consumer_loop_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181053A10 and size == 0x267:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_cull_view_consumer_scheduled_view_loop_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_cull_view_consumer_surface(image)

    def test_unity_hgtree_renderer_boundary(self) -> None:
        result = AUDIT.validate_unity_hgtree_renderer_boundary(
            AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        )
        self.assertEqual(result["internalCall"]["index"], 564)
        self.assertEqual(result["internalCall"]["entryCount"], 729)
        self.assertEqual(
            result["internalCall"]["targetVirtualAddress"], "0x1801D9D10"
        )
        renderer_variants = result["rendererListVariants"]
        self.assertEqual(
            [row["index"] for row in renderer_variants["entries"]],
            [564, 565, 566],
        )
        self.assertTrue(
            renderer_variants["allHGTreeVariantsReachSharedScheduler"]
        )
        self.assertEqual(
            [
                row["schedulerCallVirtualAddress"]
                for row in renderer_variants["entries"]
            ],
            ["0x18107F258", "0x18108012E", "0x1810806E4"],
        )
        factory_copy = result["factoryBatchedEntityCopyInternalCalls"]
        self.assertEqual(
            [row["index"] for row in factory_copy["entries"]],
            [198, 215],
        )
        self.assertEqual(
            factory_copy["copyCoreCallSites"],
            {
                "0x1810CE510": ["0x1801EB71A"],
                "0x1810CEBC0": ["0x1801ECCB5"],
            },
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
        resource_mapping = runtime_layout["hgmeshRendererDataResourceMapping"]
        self.assertTrue(resource_mapping["producerClosed"])
        self.assertEqual(
            [row["name"] for row in resource_mapping["serializedFields"]],
            ["m_Materials", "m_Meshes", "m_ShadowProxyMeshes"],
        )
        self.assertEqual(
            [
                row["recordWriteOffset"]
                for row in resource_mapping["serializedFields"]
            ],
            ["0x04", "0x08", "0x0C"],
        )
        self.assertEqual(
            resource_mapping["excludedField"],
            {
                "name": "m_ColliderMeshes",
                "nativeOffset": "0xD8",
                "rendererBlobWriteObserved": False,
            },
        )
        self.assertTrue(
            runtime_tail["materialMapWordAt0x04"]["resourceSourceClosed"]
        )
        self.assertTrue(runtime_tail["mutableRenderFlagsAt0x08"]["roleClosed"])
        self.assertEqual(
            runtime_tail["mutableRenderFlagsAt0x08"]["hgmeshResourceSource"],
            "m_Meshes GeometryHandle",
        )
        self.assertEqual(
            runtime_tail["mutableRenderFlagsAt0x08"]["writtenValue"],
            "0x00100000",
        )
        self.assertEqual(
            runtime_tail["mutableRenderFlagsAt0x08"]["particleModes"],
            [2, 3, 4, 5],
        )
        mesh_filter = runtime_tail["shadowProxyGeometryHandleAt0x0C"]
        self.assertTrue(mesh_filter["consumerRoleClosed"])
        self.assertTrue(mesh_filter["producerClosed"])
        self.assertTrue(mesh_filter["assetClassClosed"])
        self.assertTrue(mesh_filter["assetHandleContractClosed"])
        self.assertTrue(mesh_filter["engineIdentityClosed"])
        self.assertTrue(mesh_filter["handleEncodingClosed"])
        self.assertEqual(
            mesh_filter["assetType"],
            "UnityEngine.HyperGryph.AssetType.Mesh",
        )
        self.assertEqual(mesh_filter["assetTypeValue"], 2)
        self.assertEqual(mesh_filter["resourceField"], "m_ShadowProxyMeshes")
        self.assertEqual(mesh_filter["engineType"], "UInt32 GeometryHandle")
        self.assertEqual(mesh_filter["handleIndexMask"], "0x00FFFFFF")
        self.assertEqual(mesh_filter["handleGenerationBits"], "24..31")
        self.assertEqual(
            mesh_filter["directResourceWriterVirtualAddress"],
            "0x18108906A",
        )
        self.assertEqual(
            [row["assetTypeImmediate"] for row in mesh_filter["acquisitionPaths"]],
            [2, 2],
        )
        self.assertEqual(
            [row["ownerHandleOffset"] for row in mesh_filter["acquisitionPaths"]],
            ["0x18", "0x18"],
        )
        self.assertEqual(
            mesh_filter["writerPaths"][0]["writeVirtualAddress"],
            "0x181157AD1",
        )
        self.assertEqual(
            mesh_filter["mappingKey"], "Unity asset instance ID"
        )
        geometry_system = result["geometrySystemInternalCalls"]
        self.assertEqual(
            geometry_system["getGeometryHandle"]["index"], 300
        )
        self.assertIn(
            "HGGeometrySystem::GetGeometryHandle",
            geometry_system["getGeometryHandle"]["name"],
        )
        self.assertEqual(geometry_system["getMesh"]["index"], 301)
        self.assertEqual(
            geometry_system["handleEncoding"]["equation"],
            "GeometryHandle = ((slotGeneration + 1) & 0xFF) << 24 | slotIndex",
        )
        render_flags_abi = result["rendererListVariants"][
            "renderFlagsFilterAbi"
        ]
        self.assertEqual(
            render_flags_abi["descriptorRenderFlagsMaskOffset"], "0x40"
        )
        self.assertEqual(
            render_flags_abi["callbackRenderFlagsMaskOffset"], "0x3C"
        )
        self.assertEqual(render_flags_abi["callbackDescriptorBiasBytes"], 4)
        managed_callers = renderer_variants["managedCallers"]
        self.assertEqual(managed_callers["directCallerCount"], 7)
        self.assertEqual(
            managed_callers["directionalCascadeMasksAndValues"],
            ["0x02180100", "0x02280100", "0x02480100", "0x02880100"],
        )
        deferred_route = next(
            row
            for row in managed_callers["callerRoutes"]
            if row["owner"] == "HGRenderPathDeferred.OnPreRendering"
        )
        self.assertEqual(deferred_route["renderFlagsMask"], "0x00000500 (Opaque|ShadowOnly)")
        self.assertEqual(deferred_route["renderFlagsValue"], "0x00000100 (Opaque)")
        caller_contract = renderer_variants["managedCallerContract"]
        self.assertEqual(
            caller_contract["cascadeRenderFlags"]["values"],
            ["0x00100000", "0x00200000", "0x00400000", "0x00800000"],
        )
        self.assertEqual(
            [
                row["name"]
                for row in caller_contract["punctualFlagHelper"]["parameters"][-2:]
            ],
            ["renderFlags", "renderFlagsMask"],
        )
        renderer_list_method = result["rendererListVariants"][
            "managedContract"
        ]["method"]
        self.assertEqual(renderer_list_method["methodIndex"], 478192)
        self.assertEqual(
            [row["name"] for row in renderer_list_method["parameters"][:4]],
            [
                "viewHandle",
                "renderFlagsMask",
                "renderFlagsValue",
                "lightModeMask",
            ],
        )
        resource_load = result["resourceLoadInternalCall"]
        self.assertEqual(resource_load["index"], 437)
        self.assertIn("LoadAsync_Injected", resource_load["name"])
        self.assertEqual(
            resource_load["targetVirtualAddress"], "0x1801F2AB0"
        )
        asset_literals = {
            row["name"]: row["value"]
            for row in resource_load["managedContract"]["assetType"]["literals"]
        }
        self.assertEqual(asset_literals["Material"], 1)
        self.assertEqual(asset_literals["Mesh"], 2)
        load_parameters = resource_load["managedContract"][
            "loadAsyncInjected"
        ]["parameters"]
        self.assertEqual(load_parameters[1]["name"], "type")
        self.assertEqual(load_parameters[1]["metadataTypeIndex"], 122373)
        resource_handles = result["resourceHandleInternalCalls"]
        self.assertEqual(resource_handles["getAsset"]["index"], 440)
        self.assertIn("GetAsset_Injected", resource_handles["getAsset"]["name"])
        self.assertEqual(resource_handles["updateAssetHandle"]["index"], 441)
        self.assertEqual(
            resource_handles["updateAssetHandle"]["assetInstanceIdSlotOffset"],
            "0x18",
        )
        self.assertTrue(runtime_tail["rendererPropertyFlagsAt0x10"]["roleClosed"])
        self.assertFalse(
            runtime_tail["rendererPropertyFlagsAt0x10"][
                "resourceInitializerSeedObserved"
            ]
        )
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
        self.assertTrue(enabled_modes["downstreamConsumerClosed"])
        self.assertEqual(downstream["gpuDrivenRequestMaskJobOffset"], "0x54")
        gpu_consumer = downstream["gpuDrivenRendererConsumer"]
        self.assertTrue(gpu_consumer["closed"])
        self.assertEqual(gpu_consumer["generations"], ["V1", "V2"])
        self.assertEqual(gpu_consumer["variants"], ["default", "pre_z"])
        self.assertEqual(gpu_consumer["recordOffset"], "0x14")
        self.assertEqual(
            gpu_consumer["representativeReadSites"],
            [
                "0x1810E8E73",
                "0x1810EA245",
                "0x1810F5F7F",
                "0x1810F7356",
            ],
        )
        gpu_routes = result["gpuDrivenRendererList"]
        self.assertTrue(gpu_routes["enabledLightModesReadObserved"])
        self.assertEqual(gpu_routes["descriptorSizeBytes"], 0xA0)
        self.assertEqual(gpu_routes["requestLightModeMaskOffset"], "0x54")
        self.assertEqual(
            [(row["generation"], row["variant"]) for row in gpu_routes["entries"]],
            [
                ("V1", "default"),
                ("V1", "pre_z"),
                ("V2", "default"),
                ("V2", "pre_z"),
            ],
        )
        self.assertEqual(len(gpu_routes["verifiedBodies"]), 20)
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
            ["0x181129E0D", "0x18112A790", "0x18113781A"],
        )
        self.assertEqual(pointer_boundary["allDirectLookupCallCount"], 53)
        self.assertEqual(pointer_boundary["exactFamilyLookupCallCount"], 44)
        self.assertEqual(pointer_boundary["exactFamilyEntryCfgCount"], 41)
        self.assertEqual(pointer_boundary["nonFamilyLookupCallCount"], 9)
        self.assertEqual(
            pointer_boundary["directConsumerRecordReads"][1][
                "recordOffsets"
            ],
            ["0x00", "0x04", "0x08", "0x10"],
        )
        self.assertEqual(
            pointer_boundary["recordBaseZeroInitializationCallSites"],
            ["0x18042A497", "0x18042AEAD", "0x180BCBAEC"],
        )
        hot_cold = pointer_boundary["hotColdCfgTraversal"]
        self.assertEqual(hot_cold["enabledLightModesReadSites"], [])
        self.assertEqual(
            hot_cold["recordBaseNonStackMemoryStoreSites"], []
        )
        self.assertEqual(hot_cold["recordBaseReturnSites"], [])
        self.assertTrue(hot_cold["memoryOperandWidthOverlapChecked"])
        stack_boundary = pointer_boundary["stackPointerBoundary"]
        self.assertEqual(stack_boundary["blobHeaderStoreCount"], 4)
        self.assertEqual(stack_boundary["recordBaseStoreCount"], 3)
        self.assertEqual(stack_boundary["addressTakenSites"], [])
        self.assertEqual(len(stack_boundary["stores"]), 7)
        self.assertEqual(
            pointer_boundary["fullBlobCopy"]["byteCountEquation"],
            "4 + 32 * (familyMask >> 8)",
        )
        self.assertIn(
            "copied verbatim",
            pointer_boundary["fullBlobCopy"][
                "enabledLightModesBehavior"
            ],
        )
        self.assertEqual(
            [
                row["internalCallIndex"]
                for row in pointer_boundary["fullBlobCopy"][
                    "factoryCreateBatchedEntityRoutes"
                ]
            ],
            [198, 215],
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
        companion = ecs_state["resourceCompanion"]
        self.assertEqual(companion["candidateComponentIds"], list(range(68, 75)))
        self.assertEqual(companion["serializedComponentIds"], list(range(68, 74)))
        self.assertEqual(
            [row["rowCapacity"] for row in companion["serializedCapacityClasses"]],
            [1, 2, 4, 8, 16, 32],
        )
        self.assertEqual(companion["recordLayout"]["rowStrideBytes"], 40)
        unload = ecs_state["unloadStateMachine"]
        self.assertEqual(
            unload["unloadingToUnloaded"]["selectedLodMask"],
            "pendingMask | availableMask",
        )
        self.assertIn(
            "clearing pending and available masks together",
            unload["unloadingToUnloaded"]["component67Effect"],
        )
        self.assertEqual(
            unload["loadingToUnloaded"]["selectedLodMask"],
            "pendingMask only",
        )
        self.assertIn(
            "preserve available mask",
            unload["loadingToUnloaded"]["component67Effect"],
        )
        controls = ecs_state["lodStreamingControl"]
        self.assertEqual(
            [row["index"] for row in controls["internalCalls"]],
            list(range(273, 292)),
        )
        self.assertEqual(
            controls["internalCalls"][-1]["name"],
            "UnityEngine.HyperGryph.HGLODStreamingSystem::get_pendingEntityCount",
        )
        self.assertEqual(
            controls["stateFields"]["enableLODStreaming"],
            "0x38",
        )
        self.assertEqual(
            controls["stateFields"]["enableLODStreamingKeepLastLODResource"],
            "0x39",
        )
        managed_types = result["lodControlInternalCalls"][
            "managedFieldContract"
        ]["managedValueTypes"]
        self.assertEqual(
            managed_types[0]["fields"][2]["name"],
            "c1",
        )
        self.assertEqual(
            managed_types[0]["fields"][2]["unboxedOffset"],
            "0x18",
        )
        self.assertEqual(
            managed_types[1]["fields"][0]["name"],
            "lodCenter",
        )
        self.assertEqual(
            managed_types[1]["fields"][0]["unboxedOffset"],
            "0x0",
        )
        load = ecs_state["loadRequestStateMachine"]
        self.assertEqual(
            [row["assetType"] for row in load["resourceTriplet"]],
            [1, 2, 2],
        )
        self.assertEqual(load["requestDescriptor"]["strideBytes"], 24)
        self.assertEqual(
            load["mergedRenderCollider"]["streamingEnabled"]["pendingMask"],
            "1 << (lodCount - 1)",
        )
        self.assertEqual(
            load["mergedRenderCollider"]["streamingDisabled"]["pendingMask"],
            "(1 << lodCount) - 1",
        )
        self.assertIn(
            "distanceSquared >=",
            load["render"]["streamingEnabled"]["requestCondition"],
        )
        self.assertIn(
            "component 75",
            load["render"]["streamingEnabled"]["hlodLevel"],
        )
        batch = load["requestBatchLifecycle"]
        self.assertEqual(batch["transitionTaskVirtualAddress"], "0x181172DD0")
        self.assertEqual(batch["taskBatchPointerOffset"], "0x18")
        self.assertEqual(
            batch["descriptorInputs"]["deferredUniqueSet"]["offset"],
            "callback context+0x50",
        )
        self.assertEqual(
            batch["descriptorInputs"]["directDescriptorVector"]["offset"],
            "callback context+0x58",
        )
        self.assertEqual(
            batch["descriptorInputs"]["combinedCount"],
            "deferredUniqueSet.count + directDescriptorVector.count",
        )
        poller = batch["poller"]
        self.assertEqual(poller["virtualAddress"], "0x181172750")
        self.assertEqual(poller["directCallSites"], ["0x181173268"])
        self.assertEqual(
            [row["value"] for row in poller["states"]],
            [0, 1, 2],
        )
        self.assertIn("load failure", poller["states"][2]["meaning"])
        self.assertEqual(
            batch["transitionTaskDirectCallSites"],
            [
                "0x181173854",
                "0x181180A25",
                "0x181180EB4",
                "0x181181095",
            ],
        )
        caller_surface = batch["directCallerSurface"]
        self.assertEqual(
            caller_surface["gridLoadStateDriver"]["virtualAddress"],
            "0x1811733F0",
        )
        self.assertEqual(
            caller_surface["streamingBatchUpdate"]["callSites"],
            ["0x181180A25", "0x181180EB4", "0x181181095"],
        )
        entrypoints = batch["updateEntrypoints"]
        managed_tick = entrypoints["managedTick"]
        self.assertEqual(managed_tick["internalCall"]["index"], 614)
        self.assertEqual(
            managed_tick["streamingBatchUpdateCallSite"],
            "0x18117486A",
        )
        self.assertEqual(
            managed_tick["allDirectBatchUpdateCallSites"],
            ["0x181174727", "0x18117486A"],
        )
        managed_tick_resource = entrypoints["managedTickResource"]
        self.assertEqual(managed_tick_resource["internalCall"]["index"], 615)
        self.assertEqual(
            managed_tick_resource["directRequestLifecycleCallSites"],
            [],
        )
        native_update = entrypoints["registeredNativeGridUpdate"]
        self.assertEqual(
            native_update["callbackSlotVirtualAddress"],
            "0x1821A87F8",
        )
        self.assertEqual(
            [row["targetVirtualAddress"] for row in native_update["chain"]],
            [
                "0x181172C70",
                "0x18117FE00",
                "0x181173950",
                "0x1811733F0",
                "0x181172DD0",
            ],
        )
        self.assertIn("remain unproved", native_update["boundary"])
        managed_chain = AUDIT.validate_streaming_gameplay_managed_update_chain(
            AUDIT.GLOBAL_METADATA.read_bytes(),
            AUDIT.PEImage(AUDIT.GAME_ASSEMBLY),
        )
        self.assertEqual(
            [row["method"] for row in managed_chain["chain"]],
            [
                "Beyond.Gameplay.View.GameSceneManager.Tick",
                "Beyond.Gameplay.View.BaseGameScene.Update",
                (
                    "Beyond.Gameplay.Core.DynamicScene."
                    "DynamicStreamingScene.Update"
                ),
                (
                    "Beyond.Gameplay.Core.DynamicScene."
                    "DynamicStreamingScene.TickSystem"
                ),
                (
                    "Beyond.Gameplay.Core.DynamicScene."
                    "DynamicSceneEcsSystem.Tick"
                ),
            ],
        )
        self.assertEqual(
            managed_chain["chain"][3]["resourceTickCallSite"],
            "0x1830AD7B3",
        )
        self.assertEqual(
            managed_chain["chain"][4]["batchLimitEquation"],
            "system+0x54 == 2 ? 0x800 : 0x100",
        )
        self.assertEqual(
            managed_chain["dynamicStreamingSceneFields"]["m_systems"][
                "boxedOffset"
            ],
            "0x170",
        )
        self.assertEqual(
            managed_chain["dynamicStreamingSceneFields"]["m_validSystems"][
                "boxedOffset"
            ],
            "0x180",
        )
        self.assertIn("virtual caller", managed_chain["boundary"])
        failure = batch["failureEvidence"]
        self.assertEqual(
            failure["diagnostics"]["load"]["value"],
            "Streaming load asset %lld failed",
        )
        self.assertIn("state 2 removes", failure["stateEquation"])
        handoff = batch["readyHandoff"]
        self.assertEqual(handoff["transition"]["value"], 3)
        self.assertEqual(
            [row["destination"] for row in handoff["projections"]],
            [
                "callback context+0x60",
                "callback context+0x68",
                "callback context+0x70",
            ],
        )
        self.assertEqual(
            [row["virtualAddress"] for row in handoff["callbacks"]],
            ["0x181159010", "0x181157760"],
        )
        self.assertNotIn("request-submission continuation", load["closedBoundary"])
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
            291,
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

    def test_changed_hgtree_managed_asm_caller_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x189D18418 and size == 0x121A:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=hgtree_renderer_list_callers_asm_render_sha256; "
                r"source=.*GameAssembly.dll; expected=.*actual=",
            ):
                AUDIT.validate_hgtree_renderer_list_game_assembly(image)

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

    def test_changed_runtime_record_grouping_consumer_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18112A790 and size == 0x67E:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_runtime_record_blob_consumer_component_grouping_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_child_renderer_list_core_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18107FCF0 and size == 0x491:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_create_renderer_list_child_core_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_gpu_driven_v2_record_consumer_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810F58F0 and size == 0xA20:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_gpu_driven_renderer_v2_record_consumer_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_runtime_record_full_blob_copy_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810CE280 and size == 0x143:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_runtime_record_full_blob_copy_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_runtime_blob_stack_spill_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1810CF36D and size == 0x1FD:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_runtime_record_blob_header_stack_spill_a_sha256; "
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

    def test_changed_hgmesh_runtime_record_initializer_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181088D80 and size == 0x35E:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_hgmesh_renderer_data_runtime_record_"
                r"initializer_sha256; source=.*UnityPlayer.dll; "
                r"expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_geometry_handle_builder_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18108B1C0 and size == 0x396:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_hg_geometry_slot_populate_and_handle_"
                r"build_sha256; source=.*UnityPlayer.dll; "
                r"expected=.*actual=",
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

    def test_changed_hgtree_renderer_list_metadata_fails_closed(self) -> None:
        metadata = bytearray(AUDIT.GLOBAL_METADATA.read_bytes())
        sections = {
            section_name: struct.unpack_from(
                "<Ii", metadata, 8 + section_index * 8
            )
            for section_index, section_name in enumerate(
                AUDIT.IL2CPP_METADATA_SECTION_NAMES
            )
        }
        method_offset, _method_size = sections["methods"]
        position = (
            method_offset
            + AUDIT.HG_TREE_CREATE_RENDERER_LIST_INJECTED_METHOD_INDEX * 32
            + 8
        )
        struct.pack_into("<i", metadata, position, 168242)
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=hgtree_renderer_list_method_return_type; "
            r"source=.*global-metadata.dat; expected=168243; actual=168242",
        ):
            AUDIT.validate_hgtree_renderer_list_metadata(bytes(metadata))

    def test_changed_hg_asset_type_mesh_value_fails_closed(self) -> None:
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
        mesh_field = AUDIT.HG_ASSET_TYPE_FIELDS["Mesh"][0]
        mesh_data_index = None
        for position in range(
            defaults_offset, defaults_offset + defaults_size, 12
        ):
            field_index, _type_index, data_index = struct.unpack_from(
                "<iii", metadata, position
            )
            if field_index == mesh_field:
                mesh_data_index = data_index
                break
        self.assertIsNotNone(mesh_data_index)
        metadata[values_offset + mesh_data_index] ^= 2
        with self.assertRaisesRegex(
            AssertionError,
            r"validator=light_cull_cap; "
            r"check=hg_resource_asset_type_Mesh_value; "
            r"source=.*global-metadata.dat; expected=2; actual=3",
        ):
            AUDIT.validate_hg_resource_asset_type_metadata(bytes(metadata))

    def test_changed_hg_resource_acquire_core_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x180FBFC60 and size == 0x224:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_resource_slot_acquire_sha256; "
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

    def test_changed_hgtree_lod_ecs_resource_request_poller_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181172750 and size == 0x361:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_resource_request_poller_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_lod_ecs_transition_task_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181172DD0 and size == 0x614:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_transition_task_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_hgtree_lod_ecs_grid_load_state_driver_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1811733F0 and size == 0x4E9:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_grid_load_state_driver_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_streaming_gameplay_tick_binding_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801DDF20 and size == 0x08:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_streaming_gameplay_tick_binding_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_native_update_callback_slot_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x180FC23E4 and size == 14:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_native_update_callback_slot_init; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_managed_streaming_tick_system_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1830AD740 and size == 0x948:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=streaming_managed_update_"
                r"dynamic_streaming_scene_tick_system_sha256; "
                r"source=.*GameAssembly.dll; expected=.*actual=",
            ):
                AUDIT.validate_streaming_gameplay_managed_update_chain(
                    AUDIT.GLOBAL_METADATA.read_bytes(), image
                )

    def test_changed_managed_streaming_tick_resolver_string_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
        original_cstring = image.cstring

        def changed_cstring(virtual_address: int) -> str:
            if virtual_address == 0x18B8CE930:
                return "Changed Tick resolver"
            return original_cstring(virtual_address)

        with mock.patch.object(image, "cstring", changed_cstring):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=streaming_managed_update_tick_resolver_string; "
                r"source=.*GameAssembly.dll; expected=.*actual=",
            ):
                AUDIT.validate_streaming_gameplay_managed_update_chain(
                    AUDIT.GLOBAL_METADATA.read_bytes(), image
                )

    def test_changed_hgtree_resource_load_failure_string_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_cstring = image.cstring

        def changed_cstring(virtual_address: int) -> str:
            if virtual_address == 0x181D25868:
                return "Changed resource failure"
            return original_cstring(virtual_address)

        with mock.patch.object(image, "cstring", changed_cstring):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_resource_lifecycle_load_failure; "
                r"source=.*UnityPlayer.dll; "
                r"expected='Streaming load asset %lld failed'; "
                r"actual='Changed resource failure'",
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

    def test_changed_hg_resource_update_handle_binding_fails_closed(
        self,
    ) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801F2C10 and size == 0x97:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_hg_resource_update_handle_binding_sha256; "
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

    def test_changed_component67_companion_mask_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x181E22FC0 and size == 16:
                data[8] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_component67_companion_component_mask; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_component67_unload_callback_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18115BC90 and size == 0x1EA:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_ecs_component_67_type9_"
                r"unload_to_unloaded_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_lod_streaming_enable_binding_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x1801EDCE0 and size == 0x19:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_lod_streaming_get_enable_sha256; "
                r"source=.*UnityPlayer.dll; expected=.*actual=",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_changed_lod_cross_fade_field_offset_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.GAME_ASSEMBLY)
        original_read = image.read

        def changed_read(virtual_address: int, size: int) -> bytes:
            data = bytearray(original_read(virtual_address, size))
            if virtual_address == 0x18B9F1B60 and size == 4:
                data[0] ^= 1
            return bytes(data)

        with mock.patch.object(image, "read", changed_read):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=lod_streaming_lod_cross_fade_config_c1_boxed_offset; "
                r"source=.*GameAssembly.dll; expected=40; actual=41",
            ):
                AUDIT.validate_lod_streaming_metadata(
                    AUDIT.GLOBAL_METADATA.read_bytes(), image
                )

    def test_component67_accessor_call_site_drift_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)

        def changed_sites(_image: object, target: int) -> list[int]:
            if target == AUDIT.UNITY_RENDERER_BLOB_LOOKUP_VA:
                return AUDIT.UNITY_RENDERER_BLOB_LOOKUP_CALL_SITES
            if target == AUDIT.UNITY_RENDERER_LIST_SCHEDULER_VA:
                return AUDIT.UNITY_RENDERER_LIST_SCHEDULER_CALL_SITES
            if target in AUDIT.UNITY_FACTORY_BATCHED_ENTITY_COPY_CALL_SITES:
                return AUDIT.UNITY_FACTORY_BATCHED_ENTITY_COPY_CALL_SITES[
                    target
                ]
            return []

        with mock.patch.object(
            AUDIT, "find_relative_call_sites", side_effect=changed_sites
        ):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_component67_archetype_accessor_call_sites; "
                r"source=.*UnityPlayer.dll; expected=.*actual=\[\]",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_renderer_blob_lookup_call_site_drift_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)
        with mock.patch.object(AUDIT, "find_relative_call_sites", return_value=[]):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_blob_lookup_call_sites; "
                r"source=.*UnityPlayer.dll; expected=.*actual=\[\]",
            ):
                AUDIT.validate_unity_hgtree_renderer_boundary(image)

    def test_renderer_list_scheduler_call_site_drift_fails_closed(self) -> None:
        image = AUDIT.PEImage(AUDIT.UNITY_PLAYER)

        def changed_sites(_image: object, target: int) -> list[int]:
            if target == AUDIT.UNITY_RENDERER_BLOB_LOOKUP_VA:
                return AUDIT.UNITY_RENDERER_BLOB_LOOKUP_CALL_SITES
            if target == AUDIT.UNITY_RENDERER_LIST_SCHEDULER_VA:
                return []
            return AUDIT.find_relative_call_sites(image, target)

        with mock.patch.object(
            AUDIT, "find_relative_call_sites", side_effect=changed_sites
        ):
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; "
                r"check=unity_hgtree_renderer_list_scheduler_call_sites; "
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
