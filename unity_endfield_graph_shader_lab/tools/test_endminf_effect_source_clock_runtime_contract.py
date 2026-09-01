#!/usr/bin/env python3
"""Focused source-clock transport tests for Endminf entrance animations."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
PLAYBACK = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
    / "EndfieldOverviewPlayback.cs"
)
SPAWNER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldRecoveredCharEffectSpawner.cs"
)
CAPTURE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)
CONTRACT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "endminf_effect_nanguan_trigger_contract.json"
)
OVERVIEW_01 = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf"
    / "Effects/Overview/P_fxui_endminm003_overview_01.prefab"
)
ANIMATION = OVERVIEW_01.parent / "Animation"


class EndminfEffectSourceClockRuntimeContractTests(unittest.TestCase):
    def test_published_contract_requires_one_shot_raw_source_seed(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        playback = payload["conclusions"]["labPlayback"]
        self.assertTrue(playback["sourceTriggerOwnerExact"])
        self.assertTrue(playback["oneShotSeedExact"])
        self.assertIn("single captured length*normalizedTime seed",
                      playback["labStartPolicy"])
        self.assertIn("Do not graft clip 03", playback["rule"])
        self.assertIn("continuously resample", playback["rule"])

    def test_source_clock_fails_closed_before_exposing_elapsed_time(self) -> None:
        source = PLAYBACK.read_text(encoding="utf-8")
        method = source[
            source.index("internal bool TryGetAuthenticatedElapsed"):
            source.index("    }\n\n    [System.Serializable]", source.index(
                "internal bool TryGetAuthenticatedElapsed"))
        ]
        for required in (
            "!valid",
            "owner == null",
            "!owner.AnimatorContractActive",
            "owner.PlaybackGeneration != playbackGeneration",
            "SourceOverviewStartFullPathHash",
            "animator.runtimeAnimatorController == null",
            "float.IsNaN(elapsedSeconds)",
            "float.IsInfinity(elapsedSeconds)",
            "elapsedSeconds < 0f",
        ):
            self.assertIn(required, method)
        self.assertLess(method.index("return false;"),
                        method.index("elapsed = elapsedSeconds;"))

    def test_spawner_seeds_after_play_once_without_retiming_particles(self) -> None:
        source = SPAWNER.read_text(encoding="utf-8")
        start = source[
            source.index("private bool StartRecoveredLegacyAnimations"):
            source.index("private static void PlayRecoveredParticleSystems")
        ]
        self.assertIn("sourceClock.TryGetAuthenticatedElapsed", start)
        self.assertIn("sourceClock.valid && !sourceClockAuthenticated", start)
        self.assertIn("became invalid or stale", start)
        self.assertIn("sourceElapsed > 0f", start)
        self.assertLess(start.index("PlayRecoveredLegacyAnimation(animation)"),
                        start.index("TryApplyOneShotSourceAnimationSeed("))

        seed = start[
            start.index("private static bool TryApplyOneShotSourceAnimationSeed"):
        ]
        self.assertIn("state.time = sourceElapsed;", seed)
        self.assertEqual(seed.count("animation.Sample();"), 1)
        self.assertNotIn("Mathf.Clamp", seed)
        self.assertNotIn("Mathf.Repeat", seed)

        particles = source[
            source.index("private static void PlayRecoveredParticleSystems"):
            source.index("private IEnumerator FinishAfterDuration")
        ]
        self.assertNotIn("sourceClock", particles)
        self.assertNotIn("sourceElapsed", particles)

    def test_overview_01_admission_is_exact_and_precedes_playback(self) -> None:
        source = SPAWNER.read_text(encoding="utf-8")
        start = source[
            source.index("private bool StartRecoveredLegacyAnimations"):
            source.index("private static bool PlayRecoveredLegacyAnimation")
        ]
        selection = start[
            start.index("private static bool TrySelectRecoveredAutomaticAnimations"):
        ]
        self.assertLess(
            start.index("TrySelectRecoveredAutomaticAnimations("),
            start.index("sourceClock.TryGetAuthenticatedElapsed"),
        )
        self.assertLess(
            start.index("TrySelectRecoveredAutomaticAnimations("),
            start.index("PlayRecoveredLegacyAnimation(animation)"),
        )
        for required in (
            '"P_fxui_endminm003_overview_01__OverviewRuntime"',
            "automatic.Count != 2",
            'instance.transform.Find("effect_01")',
            'instance.transform.Find("effect_nanguan")',
            '"A_actor_endminf_ui_overview_02"',
            '"A_fx_endminf_ui_overview_04"',
            "animation.enabled",
            "animation.playAutomatically",
            "animation.clip.legacy",
            "selected = Array.Empty<Animation>();",
        ):
            self.assertIn(required, selection)
        self.assertIn("duplicate or unexpected", selection)

    def test_runtime_marker_canonicalizes_only_the_mutable_clone_root(self) -> None:
        source = SPAWNER.read_text(encoding="utf-8")
        validator = source[
            source.index("private static bool TryValidateEndminfV2Marker"):
            source.index("private static bool TryValidateParticleRendererState")
        ]
        self.assertIn(
            "HierarchyIncludingSourceRoot(\n"
            "                        row.generatedTransform,\n"
            "                        prefab.transform,\n"
            "                        marker.effectRoot)",
            validator,
        )
        self.assertIn(
            "names.Add(current == root ? sourceRootName : current.name);",
            validator,
        )
        for diagnostic in (
            "hierarchy identity/reference drifted at row ",
            "expected=",
            "actual=",
            "runtimeRoot=",
            "sourceRoot=",
        ):
            self.assertIn(diagnostic, validator)
        self.assertNotIn(
            "HierarchyIncludingRoot(row.generatedTransform, prefab.transform)",
            validator,
        )

    def test_overview_01_has_exactly_two_automatic_source_children(self) -> None:
        prefab = OVERVIEW_01.read_text(encoding="utf-8")
        blocks = re.findall(
            r"--- !u!111 .*?\nAnimation:\n(.*?)(?=\n--- !u!)",
            prefab,
            re.DOTALL,
        )
        automatic = [block for block in blocks if "m_PlayAutomatically: 1" in block]
        self.assertEqual(len(automatic), 2)

        expected = {
            "A_actor_endminf_ui_overview_02.anim",
            "A_fx_endminf_ui_overview_04.anim",
        }
        guid_to_name = {}
        for meta in ANIMATION.glob("*.anim.meta"):
            match = re.search(r"^guid: ([0-9a-f]+)$", meta.read_text(
                encoding="utf-8"), re.MULTILINE)
            self.assertIsNotNone(match)
            guid_to_name[match.group(1)] = meta.name.removesuffix(".meta")
        actual = set()
        for block in automatic:
            match = re.search(r"m_Animation: .*guid: ([0-9a-f]+)", block)
            self.assertIsNotNone(match)
            actual.add(guid_to_name[match.group(1)])
        self.assertEqual(actual, expected)

    def test_capture_reports_two_authenticated_overview_01_seeds(self) -> None:
        spawner = SPAWNER.read_text(encoding="utf-8")
        capture = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("TryGetSourceSeedTelemetry(", spawner)
        self.assertIn("sourceSeededAnimationCount++;", spawner)
        self.assertLess(
            spawner.index("sourceSeedTelemetry.Remove(request.prefabName);"),
            spawner.index("Binding binding = FindBinding(request.prefabName);"),
        )
        finish = spawner[
            spawner.index("public void FinishOverviewEffect"):
            spawner.index("private static void DestroyEffectInstance")
        ]
        self.assertLess(
            finish.index("sourceSeedTelemetry.Remove(prefabName);"),
            finish.index("activeEffects.TryGetValue"),
        )
        finish_all = spawner[
            spawner.index("private void FinishAllEffects"):
            spawner.index("private Binding FindBinding")
        ]
        self.assertIn("sourceSeedTelemetry.Clear();", finish_all)
        self.assertIn(
            '"P_fxui_endminm003_overview_01",',
            capture,
        )
        self.assertIn("overview01SourceSeededAnimationCount == 2", capture)
        self.assertIn("observedOverview01AuthenticatedSourceSeed", capture)
        self.assertIn(
            "overview_01 authenticated one-shot source seed on two automatic",
            capture,
        )


if __name__ == "__main__":
    unittest.main()
