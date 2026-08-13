from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.narrative_video_overrides import (
    NarrativeVideoOverrideValidationError,
    load_narrative_video_overrides,
    validate_narrative_video_override_application,
    validate_narrative_video_override_inputs,
)


class NarrativeVideoOverrideTests(unittest.TestCase):
    def write_overrides(self, root: Path, payload: object) -> Path:
        path = root / "narrative_videos.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def test_current_schema_validates_and_records_application(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_overrides(
                Path(temp_dir),
                {
                    "attachInline": {
                        "cutscene_target": {
                            "stems": ["videos/cs_video_target.mp4"],
                            "audioFrom": ["cutscene_audio"],
                            "note": "reviewed",
                        }
                    },
                    "suppressInline": {
                        "cutscene_false": {
                            "stems": ["cs_video_false"],
                        }
                    },
                },
            )
            overrides = load_narrative_video_overrides(path)
            inputs = validate_narrative_video_override_inputs(
                overrides,
                story_keys={
                    "cutscene_target",
                    "cutscene_audio",
                    "cutscene_false",
                },
                video_refs=[
                    {"baseStem": "cs_video_target"},
                    {"name": "cs_video_false.mp4"},
                ],
            )
            result = validate_narrative_video_override_application(
                overrides,
                applied_attach={
                    ("cutscene_target", "cs_video_target"),
                },
                applied_suppress={
                    ("cutscene_false", "cs_video_false"),
                },
                input_validation=inputs,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rules"], 2)
        self.assertEqual(result["appliedAttachPairs"], 1)
        self.assertEqual(len(result["sourceSha256"]), 64)

    def test_stale_inputs_fail_with_bounded_source_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_overrides(
                Path(temp_dir),
                {
                    "attachInline": {
                        "cutscene_removed": {
                            "stems": ["cs_video_removed"],
                            "audioFrom": ["cutscene_audio_removed"],
                        }
                    }
                },
            )
            overrides = load_narrative_video_overrides(path)
            with self.assertRaises(
                NarrativeVideoOverrideValidationError
            ) as raised:
                validate_narrative_video_override_inputs(
                    overrides,
                    story_keys={"cutscene_current"},
                    video_refs=[{"stem": "cs_video_current"}],
                )

        error = raised.exception
        self.assertEqual(error.stage, "inputs")
        self.assertEqual(
            [issue["code"] for issue in error.issues],
            [
                "stale_target_key",
                "stale_video_stem",
                "stale_audio_source_key",
            ],
        )
        report = error.report(language="CN")
        self.assertEqual(report["summary"]["validationErrors"], 3)
        self.assertEqual(len(report["overrideValidation"]["sourceSha256"]), 64)

    def test_invalid_schema_is_rejected_instead_of_silently_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_overrides(
                Path(temp_dir),
                {
                    "attachTo": {
                        "cutscene_target": {
                            "videoStem": "cs_video_target",
                        }
                    },
                    "suppressInline": [],
                },
            )
            with self.assertRaises(
                NarrativeVideoOverrideValidationError
            ) as raised:
                load_narrative_video_overrides(path)

        self.assertEqual(raised.exception.stage, "schema")
        self.assertEqual(
            [issue["code"] for issue in raised.exception.issues],
            ["unknown_root_fields", "invalid_bucket_type"],
        )

    def test_unapplied_current_rule_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_overrides(
                Path(temp_dir),
                {
                    "attachInline": {
                        "cutscene_target": {
                            "stems": ["cs_video_target"],
                        }
                    }
                },
            )
            overrides = load_narrative_video_overrides(path)
            inputs = validate_narrative_video_override_inputs(
                overrides,
                story_keys={"cutscene_target"},
                video_refs=[{"stem": "cs_video_target"}],
            )
            with self.assertRaises(
                NarrativeVideoOverrideValidationError
            ) as raised:
                validate_narrative_video_override_application(
                    overrides,
                    applied_attach=set(),
                    applied_suppress=set(),
                    input_validation=inputs,
                )

        self.assertEqual(raised.exception.stage, "application")
        self.assertEqual(
            raised.exception.issues[0],
            {
                "code": "override_not_applied",
                "bucket": "attachInline",
                "targetKey": "cutscene_target",
                "stem": "cs_video_target",
                "expected": "matching built video reference",
                "actual": "none",
            },
        )


if __name__ == "__main__":
    unittest.main()
