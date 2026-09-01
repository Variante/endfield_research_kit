#!/usr/bin/env python3
"""Focused offline tests for Endminf effect_nanguan trigger recovery."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_effect_nanguan_trigger_contract",
    HERE / "build_endminf_effect_nanguan_trigger_contract.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat"
)


class EndminfEffectNanguanTriggerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gameassembly = Path(os.environ.get("ENDFIELD_GAMEASSEMBLY", DEFAULT_GAMEASSEMBLY))
        cls.metadata = Path(os.environ.get("ENDFIELD_GLOBAL_METADATA", DEFAULT_METADATA))
        if not cls.gameassembly.is_file() or not cls.metadata.is_file():
            raise unittest.SkipTest("pinned Endfield native inputs are unavailable")

    def test_published_contract_matches_exact_sources_and_native_build(self) -> None:
        payload = MOD.build(self.gameassembly, self.metadata)
        published = json.loads(MOD.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload, published)
        self.assertEqual(payload["schema"], "endfield.endminf-effect-nanguan-trigger.v5")
        own_animator = payload["conclusions"]["effectInstanceDelayAndOwnAnimatorEnable"]
        self.assertTrue(own_animator["sourceClosed"])
        self.assertEqual(own_animator["relativeAnchor"], "EffectInstance.Start")
        self.assertNotIn("A_fx_endminf_ui_overview_04", own_animator["provenChain"])
        relationship = payload["conclusions"]["effectInstanceAnimatorToChildAnimatorRelationship"]
        self.assertFalse(relationship["sourceClosed"])
        self.assertEqual(relationship["status"], "unresolved")
        child = payload["conclusions"]["lodOwnedChildAnimatorDefinitionAndPlayCodePath"]
        self.assertTrue(child["definitionSourceClosed"])
        self.assertTrue(child["nativeCodePathSourceClosed"])
        self.assertTrue(child["runtimeInvocationForThisLodRowSourceClosed"])
        self.assertTrue(child["clipStartRelativeToEffectInstanceStartSourceClosed"])
        self.assertIn("activation latch", child["sourceClosedScope"])
        outer = payload["conclusions"]["overviewStateToEffectInstanceStart"]
        self.assertTrue(outer["serializedOwnerSourceClosed"])
        self.assertTrue(outer["pinnedUnpatchedNativeRouteSourceClosed"])
        self.assertTrue(outer["recordedIfixSnapshotNonreplacement"])
        self.assertFalse(outer["currentRuntimeRouteSourceClosed"])
        self.assertEqual(outer["status"], "conditional_pinned_unpatched_route_only")
        self.assertEqual(payload["evidence"]["effectSetting"]["delaySeconds"], 0.0)
        self.assertEqual(
            payload["evidence"]["lodOwnedChildAnimator"]["clipName"],
            "A_fx_endminf_ui_overview_04",
        )
        self.assertFalse(
            payload["evidence"]["lodOwnedChildAnimator"]
            ["relationshipToEffectInstanceRuntimeAnimatorProven"]
        )
        self.assertTrue(payload["evidence"]["overviewRootAnimator"]["controllerIsNull"])
        self.assertEqual(payload["evidence"]["overviewRootAnimator"]["controllerPathId"], 0)
        original_rows = payload["evidence"]["originalAssetMap"]["exactRows"]
        owner_row = next(row for row in original_rows if row["Name"] == "effect_nanguan")
        self.assertEqual(owner_row, MOD.ASSET_MAP_EXPECTED_ROWS["effect_nanguan"])
        self.assertEqual(
            payload["evidence"]["originalAssetMap"]["exactNameRowCounts"]
            ["effect_nanguan"],
            3,
        )
        self.assertEqual(
            payload["rejectedComposite"]["originalAssetMapExactNameRowCount"], 0
        )
        lod = payload["conclusions"]["effectSettingLodGameObjectActivation"]
        self.assertFalse(lod["sourceClosed"])
        self.assertEqual(
            lod["status"],
            "animator_play_closed_gameobject_display_unresolved",
        )
        lab_playback = payload["conclusions"]["labPlayback"]
        self.assertTrue(lab_playback["sourceTriggerOwnerExact"])
        self.assertTrue(lab_playback["oneShotSeedExact"])
        self.assertFalse(lab_playback["retailOwnerExact"])
        self.assertFalse(lab_playback["retailEffectInstanceTransportExact"])
        self.assertFalse(lab_playback["retailTimingExact"])
        source_join = payload["evidence"]["overviewSourceJoin"]
        self.assertEqual(
            source_join["state"],
            {
                "path": "Base Layer.Overview.FromOveview",
                "fullPathId": 1560421867,
                "pathCrc32": "0x5d0225eb",
                "layerIndex": 0,
            },
        )
        self.assertEqual(
            [row["effectName"] for row in
             source_join["stateMachineBehaviour"]["orderedEffects"]],
            list(MOD.SOURCE_OVERVIEW_EFFECTS),
        )
        self.assertEqual(
            source_join["overview01PostHierarchy"]["postLocalPosition"],
            [0.0, 1.266, 0.0],
        )
        self.assertTrue(
            source_join["recordedInstalledIfixSnapshot"]
            ["sourceBuildMatchesPinnedNative"]
        )
        self.assertFalse(
            source_join["recordedInstalledIfixSnapshot"]
            ["runtimeOrRemotePatchStateProven"]
        )
        identities = payload["evidence"]["native"]["methodIdentities"]
        self.assertIn(
            ("UnityEngine.Animator", "Play", "0x06000212"),
            {(row["type"], row["method"], row["token"]) for row in identities},
        )
        self.assertIn(
            ("Beyond.Gameplay.EffectInstance", "get_isValid", "0x06005a7f",
             "System.Boolean"),
            {(row["type"], row["method"], row["token"], row["returnType"])
             for row in identities},
        )
        mapping = payload["evidence"]["native"]["methodPointerMapping"]
        self.assertEqual(
            mapping["status"],
            "validated_from_current_metadata_and_codegen_module_tables",
        )
        self.assertIn(
            ("UnityEngine.Animator.Play(System.Int32)", "0x1834fcd00"),
            {(row["method"], row["methodPointerVa"]) for row in mapping["methods"]},
        )
        control = payload["evidence"]["native"]["controlFlow"]
        self.assertEqual(
            [row["name"] for row in control],
            [row["name"] for row in MOD.NATIVE_CONTROL_FLOW],
        )
        self.assertEqual(
            payload["evidence"]["native"]["negativeEdges"][0]
            ["directRelativeCallOffsets"],
            [],
        )
        self.assertEqual(
            payload["evidence"]["native"]["internalCoreEdges"][0],
            {
                "caller": "Beyond.Gameplay.EffectInstance.Start",
                "target": "Beyond.Gameplay.EffectInstance.SetActiveCore",
                "directRelativeCallOffsets": ["0x95", "0x4fa"],
                "meaning": (
                    "+0x95 is the false-to-true Start activation path; +0x4fa is the "
                    "separate delayed false path. Their bounded source bytes keep the two "
                    "boolean arguments distinct."
                ),
            },
        )
        start_activation = next(
            row for row in control
            if row["name"] == "start_set_active_true_internal_core"
        )
        self.assertEqual(
            start_activation["target"],
            "Beyond.Gameplay.EffectInstance.SetActiveCore",
        )
        self.assertEqual(start_activation["callIndex"], 29)
        self.assertIn("active=true", start_activation["semantic"])
        gates = payload["evidence"]["native"]["ifixWrapperGates"]
        self.assertEqual(
            {(row["method"], row["gateId"]) for row in gates},
            {(method, f"0x{gate_id:x}")
             for method, _, gate_id, _ in MOD.NATIVE_IFIX_WRAPPER_GATES},
        )
        self.assertEqual(
            payload["evidence"]["native"]["syncEffectTimeDirectCallers"],
            [{
                "fileOffset": "0x6b84937",
                "callVirtualAddress": "0x186b86337",
                "section": "il2cpp",
            }],
        )
        self.assertEqual(
            [row["name"] for row in payload["evidence"]["native"]
             ["syncEffectTimeDirectCallerExecutableSectionsScanned"]],
            [".text", "il2cpp", ".tvm0"],
        )
        validity_gate = next(
            row for row in control
            if row["name"] == "sync_effect_time_valid_positive_elapsed_gate"
        )
        self.assertEqual(
            validity_gate["target"],
            "Beyond.Gameplay.EffectInstance.get_isValid",
        )
        self.assertNotIn("inactive", validity_gate["semantic"])
        self.assertIn(
            "Gameplay.Beyond managed route method",
            outer["nonclaim"],
        )

    def test_fromoverview_behaviour_range_mutation_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.ACTOR_CONTROLLER:
                value = copy.deepcopy(value)
                ranges = value["m_StateMachineBehaviourVectorDescription"][
                    "m_StateMachineBehaviourRanges"
                ]
                row = next(item for item in ranges
                           if item["Key"]["m_StateID"] == MOD.SOURCE_OVERVIEW_STATE_HASH)
                row["Value"]["m_StartIndex"] = 2
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "Behaviour range drifted"):
                MOD.build(self.gameassembly, self.metadata)

    def test_overview_effect_order_mutation_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.OVERVIEW_PLAY_EFFECT_BEHAVIOUR:
                value = copy.deepcopy(value)
                value["_effects"][0], value["_effects"][1] = (
                    value["_effects"][1], value["_effects"][0]
                )
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "payload/order drifted"):
                MOD.build(self.gameassembly, self.metadata)

    def test_overview_post_hierarchy_mutation_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.OVERVIEW_01_POST_TRANSFORM:
                value = copy.deepcopy(value)
                value["m_Father"]["m_PathID"] = 0
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "local hierarchy/anchor drifted"):
                MOD.build(self.gameassembly, self.metadata)

    def test_recorded_ifix_route_target_mutation_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.INSTALLED_IFIX_PATCH_STATE:
                value = copy.deepcopy(value)
                value["targets"].append({
                    "type": "Beyond.Gameplay.AnimatorBehaviourPlayEffect",
                    "method": "_SyncEffectTime",
                    "parameters": [],
                    "implementation_index": 999,
                })
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "replaces source-clock route"):
                MOD.build(self.gameassembly, self.metadata)

    def test_recorded_ifix_set_active_route_mutation_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.INSTALLED_IFIX_PATCH_STATE:
                value = copy.deepcopy(value)
                value["targets"].append({
                    "type": "Beyond.Gameplay.EffectInstance",
                    "method": "SetActive",
                    "parameters": ["System.Boolean"],
                    "implementation_index": 999,
                })
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "replaces source-clock route"):
                MOD.build(self.gameassembly, self.metadata)

    def test_nonzero_serialized_delay_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.EFFECT_SETTING:
                value = copy.deepcopy(value)
                value["effectLogicCfg"]["delay"] = 1.0
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "zero/non-random delay"):
                MOD.build(self.gameassembly, self.metadata)

    def test_controller_clip_substitution_fails_closed(self) -> None:
        original = MOD.load_json

        def changed(path: Path) -> dict:
            value = original(path)
            if Path(path) == MOD.CONTROLLER:
                value = copy.deepcopy(value)
                value["m_AnimationClips"][0]["m_PathID"] = 8378992340436559080
            return value

        with mock.patch.object(MOD, "load_json", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "controller clip pointer"):
                MOD.build(self.gameassembly, self.metadata)

    def test_assetmap_owner_marker_substitution_fails_closed(self) -> None:
        original = MOD.load_json_list

        def changed(path: Path) -> list[dict]:
            value = original(path)
            if Path(path) == MOD.ASSET_MAP_FILTER:
                value = copy.deepcopy(value)
                row = next(
                    item for item in value
                    if item.get("Name") == "A_fx_endminf_ui_overview_04"
                )
                row["Container"] = row["Container"].replace("overview_01", "overview_02")
            return value

        with mock.patch.object(MOD, "load_json_list", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "exact filtered original AssetMap row"):
                MOD.build(self.gameassembly, self.metadata)

    def test_full_assetmap_child_animator_owner_row_substitution_fails_closed(self) -> None:
        rows = {
            name: [copy.deepcopy(row)]
            for name, row in MOD.ASSET_MAP_EXPECTED_ROWS.items()
        }
        rows["effect_nanguan"][0]["Container"] = (
            "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
            "p_fxui_endminm003_overview_02.prefab"
        )
        with self.assertRaisesRegex(ValueError, "Animator owner row drifted"):
            MOD.validate_exact_asset_map_rows(rows)

    def test_native_build_hash_gate_rejects_other_input(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            wrong = Path(folder) / "GameAssembly.dll"
            wrong.write_bytes(b"not the pinned build")
            with self.assertRaisesRegex(ValueError, "pinned Endfield build"):
                MOD.validate_native(wrong, self.metadata)

    def test_tracked_importer_binds_source_clip_without_composite_or_delay(self) -> None:
        lab = MOD.LAB
        importer = (
            lab
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfEffectAnimationImporter.cs"
        ).read_text(encoding="utf-8")
        spawner = (
            lab
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredCharEffectSpawner.cs"
        ).read_text(encoding="utf-8")

        self.assertIn('EffectNanguanClipName = "A_fx_endminf_ui_overview_04"', importer)
        self.assertNotIn("A_fx_endminf_ui_overview_03_04", importer)
        self.assertNotIn("AddRockVisibilityCurves", importer)
        self.assertNotIn("CopyClip", importer)
        self.assertIn("rockBindings.Length == 28", importer)
        self.assertNotIn("EndminfCompositeRockClipDelaySeconds", spawner)
        self.assertNotIn("PlayEndminfCompositeRockClipAfterDelay", spawner)
        self.assertNotIn("2.7666667", spawner)


if __name__ == "__main__":
    unittest.main()
