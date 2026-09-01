#!/usr/bin/env python3
"""Focused tests for the exact Endminf overview-02 source post curves."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_overview_02_source_post_curves",
    HERE / "build_endminf_overview_02_source_post_curves.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EXPECTED_PAYLOAD_SHA256 = (
    "044017968e8d7cfe1f291274f29700a9d7bffc2bc18e333fa262d961b5385ace"
)


class EndminfOverview02SourcePostCurveTests(unittest.TestCase):
    def test_published_payload_matches_hash_gated_source_build(self) -> None:
        payload = MODULE.build()
        self.assertEqual(payload, json.loads(MODULE.OUTPUT.read_text(encoding="utf-8")))
        self.assertEqual(
            hashlib.sha256(MODULE.encode(payload)).hexdigest(),
            EXPECTED_PAYLOAD_SHA256,
        )
        self.assertEqual(
            [row["role"] for row in payload["curves"]],
            ["chromaticIntensity", "radialIntensity", "radialPower"],
        )
        self.assertEqual([len(row["keys"]) for row in payload["curves"]], [5, 5, 1])
        self.assertEqual(
            payload["curves"][0]["keys"][0],
            {
                "time": 0.0,
                "a": 54.86399841308594,
                "b": -13.7160005569458,
                "c": 0.0,
                "d": 0.12700000405311584,
            },
        )
        self.assertEqual(
            payload["curves"][1]["keys"][2],
            {
                "time": 4.400000095367432,
                "a": -5886.0166015625,
                "b": 294.300537109375,
                "c": 0.0,
                "d": 0.0,
            },
        )
        self.assertEqual(payload["curves"][2]["keys"][0]["d"], 1.0)

    def test_source_file_mutation_fails_closed_at_hash_gate(self) -> None:
        source = json.loads(MODULE.SOURCE_CLIP.read_text(encoding="utf-8"))
        source["m_Name"] = "mutated"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "clip.json"
            changed.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(MODULE, "SOURCE_CLIP", changed):
                with self.assertRaisesRegex(ValueError, "clip hash drifted"):
                    MODULE.build()

    def test_published_check_canonicalizes_windows_line_endings(self) -> None:
        payload = MODULE.encode(MODULE.build())
        crlf_payload = payload.replace(b"\n", b"\r\n")
        self.assertEqual(MODULE.canonicalize_newlines(crlf_payload), payload)

    def test_binding_mutation_fails_closed_after_identity_gate(self) -> None:
        source = json.loads(MODULE.SOURCE_CLIP.read_text(encoding="utf-8"))
        bindings = source["m_ClipBindingConstant"]["genericBindings"]
        bindings[0] = copy.deepcopy(bindings[0])
        bindings[0]["attribute"] = MODULE.EXPECTED_POWER_ATTRIBUTE
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "clip.json"
            changed.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(MODULE, "SOURCE_CLIP", changed), mock.patch.object(
                MODULE,
                "sha256",
                return_value=MODULE.EXPECTED_CLIP_SHA256,
            ):
                with self.assertRaisesRegex(ValueError, "binding 0 script/member"):
                    MODULE.build()

    def test_native_audit_mutation_fails_closed(self) -> None:
        audit = json.loads(MODULE.NATIVE_AUDIT.read_text(encoding="utf-8"))
        apply_method = next(
            row
            for row in audit["scriptTypes"][0]["methods"]
            if row["method"] == "Apply"
        )
        apply_method["bodySha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "audit.json"
            changed.write_text(json.dumps(audit), encoding="utf-8")
            with mock.patch.object(MODULE, "NATIVE_AUDIT", changed):
                with self.assertRaisesRegex(ValueError, "audit content hash drifted"):
                    MODULE.build()

    def test_runtime_uses_exact_cubic_payload_without_fitted_curve(self) -> None:
        runtime = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredEndminfSourcePostCurves.cs"
        ).read_text(encoding="utf-8")
        clock = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldEndminfVisualCompatibilityClock.cs"
        ).read_text(encoding="utf-8")
        pipeline = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        for token in (
            EXPECTED_PAYLOAD_SHA256,
            "Resources.Load<TextAsset>(ResourceName)",
            'Replace("\\r\\n", "\\n")',
            "sha.ComputeHash(Encoding.UTF8.GetBytes(normalizedPayload))",
            "return ((key.a * delta + key.b) * delta + key.c) * delta + key.d;",
        ):
            self.assertIn(token, runtime)
        self.assertIn("EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(", clock)
        for token in (
            '"ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST"',
            "public static bool SourcePostSeedAuthenticated =>",
            "TryGetAuthenticatedSourcePostElapsed(out _)",
            "if (!SourcePostRequested)",
            "ClearSourcePost();",
            "sourcePostRoot != null",
            "sourcePostSeedSeconds = sourceElapsed;",
            "sourcePostBindTime = Time.timeAsDouble;",
            "double delta = Time.timeAsDouble - sourcePostBindTime;",
            "elapsed = sourcePostSeedSeconds + (float)delta;",
            "boundSourcePostGeneration == sourcePostGeneration",
            "IsSourceOwnerLive(overview02SourceOwner,",
            "overview02SourcePlaybackGeneration",
            "owner.AnimatorContractActive",
            "animator.runtimeAnimatorController != null",
            "public static bool RetailEffectTickDomainExact => false;",
            '"P_fxui_endminm003_overview_01__OverviewRuntime"',
            '"P_fxui_endminm003_overview_02__OverviewRuntime"',
            "MarkOverview02CompatibilityStart(Transform effectRoot)",
        ):
            self.assertIn(token, clock)
        evaluator = clock[
            clock.index("public static bool TryEvaluateRecoveredPost("):
            clock.index("private static bool TryGetAuthenticatedSourcePostElapsed(")
        ]
        self.assertIn("!TryGetAuthenticatedSourcePostElapsed(out float elapsed)", evaluator)
        self.assertNotIn("TryGetElapsed(", evaluator)
        for token in (
            "EvaluateSourceCurve(",
            "initialPeak * 0.45f",
            "4.3166667f",
            "4.35f",
            "4.5166667f",
        ):
            self.assertNotIn(token, clock)
        self.assertIn("endminfPost.radialIntensity,", pipeline)
        self.assertIn("endminfPost.chromaticIntensity,", pipeline)
        self.assertNotIn("EndminfCompatibilityUberIntensityScale", pipeline)

    def test_source_effect_owner_and_state_elapsed_route_are_exact(self) -> None:
        playback = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldOverviewPlayback.cs"
        ).read_text(encoding="utf-8")
        spawner = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredCharEffectSpawner.cs"
        ).read_text(encoding="utf-8")
        clock = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldEndminfVisualCompatibilityClock.cs"
        ).read_text(encoding="utf-8")
        elapsed_method = playback[
            playback.index("public bool TryGetAutomaticOverviewStartSeconds("):
            playback.index("private bool waitingForExit;")
        ]
        self.assertIn("seconds = current.length * current.normalizedTime;", elapsed_method)
        self.assertIn("SourceOverviewStartFullPathHash", elapsed_method)
        self.assertIn("current.fullPathHash != SourceOverviewStartFullPathHash", elapsed_method)
        self.assertNotIn("Mathf.Clamp01(current.normalizedTime)", elapsed_method)

        restart = playback[
            playback.index("private bool TryRestartRecoveredAnimator()"):
            playback.index("private void OnAnimatorMove()")
        ]
        self.assertLess(restart.index('animator.SetTrigger("EnableSwitch")'),
                        restart.index("PublishEntranceEffects(new"))
        self.assertIn("animator.Update(0f);", restart)
        self.assertIn("TryGetAutomaticOverviewStartSeconds(out float sourceElapsed)", restart)
        for token in (
            "new EndfieldOverviewEffectSourceClock",
            "owner = this",
            "playbackGeneration = playbackGeneration",
            "stateFullPathHash = SourceOverviewStartFullPathHash",
            "elapsedSeconds = sourceElapsed",
            "valid = true",
        ):
            self.assertIn(token, restart)

        self.assertIn('"P_fxui_endminm003_overview_01"', spawner)
        self.assertIn("BindOverview02SourceClock(", spawner)
        create = spawner[
            spawner.index("private void CreateEffect("):
            spawner.index("private bool StartRecoveredLegacyAnimations(")
        ]
        self.assertLess(create.index("instance.SetActive(true);"),
                        create.index("StartRecoveredLegacyAnimations("))
        self.assertLess(create.index("StartRecoveredLegacyAnimations("),
                        create.index("PlayRecoveredParticleSystems(systems);"))
        self.assertLess(create.index("PlayRecoveredParticleSystems(systems);"),
                        create.index("BindOverview02SourceClock("))
        self.assertIn("MarkOverview02CompatibilityStart(instance.transform);", create)
        self.assertIn("source_post_effect_startup_failed", create)
        self.assertIn("source_post_clock_bind_rejected", create)
        for forbidden in (
            "EndminfSmoke20PresentationAdvanceSeconds",
            "IsEndminfSmoke20(",
            "system.Simulate(",
        ):
            self.assertNotIn(forbidden, spawner)

        elapsed = clock[
            clock.index("private static bool TryGetAuthenticatedSourcePostElapsed("):
            clock.index("public static bool TryEvaluateOpeningStrip(")
        ]
        self.assertNotIn("TryGetAutomaticOverviewStartSeconds", elapsed)
        self.assertIn("IsSourceOwnerLive(overview02SourceOwner", elapsed)

    def test_v4_trigger_contract_bounds_one_shot_source_clock(self) -> None:
        contract_path = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
            / "endminf_effect_nanguan_trigger_contract.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["schema"],
            "endfield.endminf-effect-nanguan-trigger.v4",
        )
        join = contract["evidence"]["overviewSourceJoin"]
        self.assertEqual(
            join["state"],
            {
                "path": "Base Layer.Overview.FromOveview",
                "fullPathId": 1560421867,
                "pathCrc32": "0x5d0225eb",
                "layerIndex": 0,
            },
        )
        behaviour = join["stateMachineBehaviour"]
        self.assertEqual(
            (
                behaviour["pathId"],
                behaviour["rangeStart"],
                behaviour["rangeCount"],
                behaviour["behaviourIndex"],
            ),
            (-5549677297504648584, 3, 1, 3),
        )
        self.assertEqual(
            [row["effectName"] for row in behaviour["orderedEffects"]],
            [
                "P_fxui_endminm003_overview_01",
                "P_fxui_endminm003_overview_02",
                "P_fxui_endminm003_overview_03",
                "P_fxui_endminm003_overview_04",
            ],
        )
        self.assertEqual(
            join["overview01PostHierarchy"],
            {
                "rootTransformPathId": 8425642429156191353,
                "postTransformPathId": 8592508268722613369,
                "postGameObject": "post (1)",
                "postLocalPosition": [0.0, 1.266, 0.0],
                "postLocalRotation": [0.0, 0.0, 0.0, 1.0],
                "postLocalScale": [1.0, 1.0, 1.0],
            },
        )
        ifix = join["recordedInstalledIfixSnapshot"]
        self.assertTrue(ifix["sourceBuildMatchesPinnedNative"])
        self.assertEqual(ifix["relevantRouteTargetsPresent"], [])
        self.assertFalse(ifix["runtimeOrRemotePatchStateProven"])
        route = contract["conclusions"]["overviewStateToEffectInstanceStart"]
        self.assertTrue(route["serializedOwnerSourceClosed"])
        self.assertTrue(route["pinnedUnpatchedNativeRouteSourceClosed"])
        self.assertTrue(route["recordedIfixSnapshotNonreplacement"])
        self.assertFalse(route["currentRuntimeRouteSourceClosed"])
        self.assertEqual(
            route["status"], "conditional_pinned_unpatched_route_only")
        control_flow_names = {
            row["name"] for row in contract["evidence"]["native"]["controlFlow"]
        }
        self.assertTrue({
            "overview_state_enter_load_immediately",
            "overview_state_enter_sync_same_effect_instance",
            "sync_effect_time_valid_positive_elapsed_gate",
            "sync_effect_time_elapsed_product",
            "sync_child_animator_update_zero",
            "sync_child_animator_update_elapsed",
            "sync_effect_instance_manual_time",
            "load_immediately_to_load_finish",
            "load_finish_to_start",
        }.issubset(control_flow_names))
        self.assertEqual(
            len(contract["evidence"]["native"]["syncEffectTimeDirectCallers"]),
            1,
        )
        self.assertEqual(
            [row["name"] for row in contract["evidence"]["native"]
             ["syncEffectTimeDirectCallerExecutableSectionsScanned"]],
            [".text", "il2cpp", ".tvm0"],
        )
        lab = contract["conclusions"]["labPlayback"]
        self.assertTrue(lab["sourceTriggerOwnerExact"])
        self.assertTrue(lab["oneShotSeedExact"])
        self.assertFalse(lab["retailOwnerExact"])
        self.assertFalse(lab["retailEffectInstanceTransportExact"])
        self.assertFalse(lab["retailTimingExact"])
        self.assertIn("without re-polling the body Animator", lab["labStartPolicy"])

        source_curves = json.loads(MODULE.OUTPUT.read_text(encoding="utf-8"))
        boundary = source_curves["runtimeBoundary"]
        for token in (
            "conditional pinned unpatched route",
            "recorded installed local IFix snapshot excludes those route targets",
            "retail EffectInstance tick domain",
            "SceneColor chronology",
            "retail-equivalent Unity presentation path remain outside this payload",
        ):
            self.assertIn(token, boundary)

    def test_selector_default_preserves_explicit_zero_and_generation_is_transactional(
            self) -> None:
        capture = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        selector_default = re.search(
            r"if \(string\.IsNullOrWhiteSpace\(Environment\.GetEnvironmentVariable\(\s*"
            r"EndfieldEndminfVisualCompatibilityClock\.SourcePostEnvironmentVariable\)\)\)\s*"
            r"\{\s*Environment\.SetEnvironmentVariable\(\s*"
            r"EndfieldEndminfVisualCompatibilityClock\.SourcePostEnvironmentVariable,\s*"
            r'"1"\);\s*\}',
            capture,
            re.DOTALL,
        )
        self.assertIsNotNone(selector_default)

        playback = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldOverviewPlayback.cs"
        ).read_text(encoding="utf-8")
        spawner = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredCharEffectSpawner.cs"
        ).read_text(encoding="utf-8")
        clock = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldEndminfVisualCompatibilityClock.cs"
        ).read_text(encoding="utf-8")
        for token in (
            "public struct EndfieldOverviewEffectSourceClock",
            "internal int playbackGeneration;",
            "EndfieldOverviewEffectSourceClock sourceClock);",
            "playbackGeneration = playbackGeneration",
        ):
            self.assertIn(token, playback)
        for token in (
            "EndfieldOverviewEffectSourceClock sourceClock)",
            "SpawnAfterDelay(binding, request, mount, sourceClock)",
            "CreateEffect(binding, request, mount, sourceClock)",
            "BindOverview02SourceClock(",
        ):
            self.assertIn(token, spawner)
        self.assertIn("IsSourceOwnerLive(sourceClock.owner,", clock)
        self.assertIn("owner.PlaybackGeneration == playbackGeneration", clock)

        capture = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfViewerPlayModeCapture.cs"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "EndfieldEndminfVisualCompatibilityClock.TryGetElapsed(\n"
            "                out float endminfPostSeconds);",
            capture,
        )
        for token in (
            "bool endminfPostEvaluated =",
            "? endminfPostState.elapsed",
            "endminfPostEvaluated = endminfPostEvaluated",
            "value.endminfPostEvaluated && Mathf.Abs(",
            "authenticated Endminf overview_01 source-post clock",
        ):
            self.assertIn(token, capture)


if __name__ == "__main__":
    unittest.main()
