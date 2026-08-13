from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder.source_gap import api
from scripts.story_builder.source_gap.report import GapReportPaths


class SourceGapApiTests(unittest.TestCase):
    def test_builds_and_publishes_in_process(self) -> None:
        report = {"_schema": "sourceStoryGapQueue.v132", "language": "CN"}
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            paths = GapReportPaths(
                json=output_root / "source_story_gap_queue_CN.json",
                markdown=output_root / "source_story_gap_queue_CN.md",
            )
            with (
                patch.object(
                    api.core,
                    "build_partial_order_report",
                    return_value={"missions": []},
                ),
                patch.object(
                    api,
                    "build_levelscript_action_story_occurrences",
                    return_value={},
                ),
                patch.object(
                    api,
                    "build_levelscript_native_story_playback_index",
                    return_value={},
                ),
                patch.object(
                    api.core,
                    "project_authored_story_content_keys",
                    return_value=({}, {"status": "active"}),
                ),
                patch.object(
                    api.core,
                    "load_story_trigger_manifest_evidence",
                    return_value=({}, {"status": "active"}),
                ),
                patch.object(
                    api.core,
                    "build_offline_exhaustion_index",
                    return_value=({}, {"status": "active"}),
                ),
                patch.object(
                    api.core,
                    "build_quest_attachment_diagnostic_index",
                    return_value=({}, {"status": "active"}),
                ),
                patch.object(
                    api.core,
                    "build_general_quest_attachment_boundary_index",
                    return_value=({}, {"validationFailures": []}),
                ),
                patch.object(api.core, "build_gap_report", return_value=report),
                patch.object(api, "publish_gap_report", return_value=paths) as publish,
            ):
                result = api.build_source_gap_queue(
                    "cn",
                    reports_dir=output_root,
                    table_root=output_root / "Table",
                )

        self.assertIs(result.report, report)
        self.assertEqual(result.paths, paths)
        publish.assert_called_once_with(report, output_root, "CN")


if __name__ == "__main__":
    unittest.main()
