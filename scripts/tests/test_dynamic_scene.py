from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.story_builder import dynamic_scene


class DynamicSceneContextTests(unittest.TestCase):
    def test_current_artifact_is_fully_validated(self) -> None:
        audit = dynamic_scene.validate_dynamic_scene_context()

        self.assertEqual(audit["status"], "validated")
        self.assertEqual(audit["validationFailures"], [])
        context = audit["dynamicSceneContext"]
        self.assertEqual(context["counts"], dynamic_scene.EXPECTED_COUNTS)
        self.assertFalse(context["directBridgeFound"])
        self.assertFalse(context["missionActivationBridgeFound"])
        self.assertEqual(context["missionGraphAction"], "none")

    def test_positive_ownership_claim_fails_closed_with_diagnostic(self) -> None:
        artifact = json.loads(dynamic_scene.DEFAULT_ARTIFACT.read_text("utf-8"))
        artifact["context"]["rows"][0]["storyBinding"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dynamic_scene.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            audit = dynamic_scene.validate_dynamic_scene_context(path)

        self.assertEqual(audit["status"], "mismatched")
        self.assertIsNone(audit["dynamicSceneContext"])
        failure = next(
            row for row in audit["validationFailures"]
            if row["gate"] == "row_0_storyBinding"
        )
        self.assertEqual(failure["validator"], "dynamicSceneStoryContext")
        self.assertFalse(failure["expected"])
        self.assertTrue(failure["actual"])

    def test_levelscript_source_hash_drift_fails_closed(self) -> None:
        artifact = json.loads(dynamic_scene.DEFAULT_ARTIFACT.read_text("utf-8"))
        artifact["sources"]["levelScriptFiles"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dynamic_scene.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            audit = dynamic_scene.validate_dynamic_scene_context(path)

        self.assertEqual(audit["status"], "mismatched")
        self.assertIsNone(audit["dynamicSceneContext"])
        failure = next(
            row for row in audit["validationFailures"]
            if row["gate"] == "levelscript_source_0_sha256"
        )
        self.assertEqual(failure["expected"], "0" * 64)
        self.assertRegex(failure["actual"], r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
