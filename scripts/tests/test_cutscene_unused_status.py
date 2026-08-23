from __future__ import annotations

import unittest
from pathlib import Path

from scripts.story_builder.cutscene_semantics import (
    apply_cutscene_playback_use_postpass,
    classify_cutscene_playback_use,
    validated_lua_cutscene_playback_keys,
)


class CutsceneUnusedStatusTests(unittest.TestCase):
    def test_case_insensitive_lua_playback_suppresses_unused(self) -> None:
        keys, failures = validated_lua_cutscene_playback_keys({
            "schemaVersion": "luaConsumerReferenceAudit.v5",
            "readErrors": [],
            "gameActionAudit": {"authoredStoryPlaybackCalls": [{
                "playbackKind": "cutscene",
                "resolvedLiteral": "Cutscene_e0m0_1",
                "canonicalStoryKey": "cutscene_e0m0_1",
                "registryStatus": "case_mismatch_registry_match",
            }]},
        })
        self.assertEqual([], failures)
        self.assertEqual(["cutscene_e0m0_1"], keys)
        result = classify_cutscene_playback_use(
            "cutscene_e0m0_1", definition_keys=["cutscene_e0m0_1"],
            playback_story_keys=keys, scan_status="validated_complete",
        )
        self.assertEqual("playback_observed", result["status"])
        self.assertFalse(result["automaticUnused"])

    def test_requires_complete_scan_and_case_insensitive_playback(self) -> None:
        unused = classify_cutscene_playback_use(
            "cutscene_fixture", definition_keys=["cutscene_fixture"],
            playback_story_keys=[], scan_status="validated_complete",
        )
        referenced = classify_cutscene_playback_use(
            "cutscene_fixture", definition_keys=["cutscene_fixture"],
            playback_story_keys=["Cutscene_Fixture"], scan_status="validated_complete",
        )
        degraded = classify_cutscene_playback_use(
            "cutscene_fixture", definition_keys=["cutscene_fixture"],
            playback_story_keys=[], scan_status="degraded",
            validation_failures=[{"gate": "fixture"}],
        )
        self.assertTrue(unused["automaticUnused"])
        self.assertEqual("playback_observed", referenced["status"])
        self.assertFalse(referenced["automaticUnused"])
        self.assertEqual("unresolved_playback_scan", degraded["status"])
        self.assertFalse(degraded["automaticUnused"])

    def test_rejects_case_colliding_definitions(self) -> None:
        result = classify_cutscene_playback_use(
            "cutscene_fixture",
            definition_keys=["cutscene_fixture", "Cutscene_Fixture"],
            playback_story_keys=[], scan_status="validated_complete",
        )
        self.assertEqual("unresolved_definition_identity", result["status"])
        self.assertFalse(result["automaticUnused"])

    def test_postpass_updates_payload_and_compact_index_without_promoting_unresolved(self) -> None:
        payloads = {
            "used": {"kind": "cutscene", "cutscene": {}},
            "unused": {"kind": "cutscene", "cutscene": {}},
        }
        entries = [{"k": "used", "d": "cutscene"}, {"k": "unused", "d": "cutscene"}]
        summary = apply_cutscene_playback_use_postpass(
            payloads, entries, playback_story_keys=["USED"],
            scan_status="validated_complete",
        )
        self.assertEqual(1, summary["automaticUnused"])
        self.assertFalse(payloads["used"]["automaticUnused"])
        self.assertTrue(payloads["unused"]["automaticUnused"])
        self.assertTrue(entries[1]["automaticUnused"])

        degraded_payloads = {"unused": {"kind": "cutscene", "cutscene": {}}}
        apply_cutscene_playback_use_postpass(
            degraded_payloads, [{"k": "unused"}], playback_story_keys=[],
            scan_status="degraded", validation_failures=[{"gate": "fixture"}],
        )
        self.assertFalse(degraded_payloads["unused"]["automaticUnused"])

    def test_story_ui_keeps_automatic_badge_separate_from_manual_override(self) -> None:
        root = Path(__file__).resolve().parents[2]
        app = (root / "webui" / "app.js").read_text(encoding="utf-8")
        labels = (root / "webui" / "app_labels.js").read_text(encoding="utf-8")
        self.assertIn('e.automaticUnused === true', app)
        self.assertIn('story-automatic-unused-badge', app)
        self.assertIn('story-order-unused-badge', app)
        self.assertIn('storyAutomaticUnusedBadge: "\\u672a\\u4f7f\\u7528"', labels)


if __name__ == "__main__":
    unittest.main()
