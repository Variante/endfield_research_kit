from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.story_builder.mission_assets import (
    mission_runtime_source_summary,
    select_complete_mission_runtime_root,
)


class MissionAssetsTests(unittest.TestCase):
    def test_complete_persistent_corpus_wins(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            streaming.mkdir()
            persistent.mkdir()
            for name in ("m1.json", "m1_meta.json"):
                (streaming / name).write_text("{}", encoding="utf-8")
                (persistent / name).write_text("{}", encoding="utf-8")
            self.assertEqual(
                select_complete_mission_runtime_root(
                    streaming,
                    persistent,
                ),
                persistent,
            )

    def test_partial_persistent_corpus_falls_back(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            streaming.mkdir()
            persistent.mkdir()
            for name in ("m1.json", "m2.json"):
                (streaming / name).write_text("{}", encoding="utf-8")
            (persistent / "m1.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                select_complete_mission_runtime_root(
                    streaming,
                    persistent,
                ),
                streaming,
            )

    def test_missing_base_corpus_cannot_validate_override(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            persistent.mkdir()
            (persistent / "m1.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                select_complete_mission_runtime_root(
                    streaming,
                    persistent,
                ),
                streaming,
            )

    def test_summary_labels_complete_override(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            streaming.mkdir()
            persistent.mkdir()
            (streaming / "m1.json").write_text("{}", encoding="utf-8")
            (persistent / "m1.json").write_text("{}", encoding="utf-8")
            summary = mission_runtime_source_summary(
                streaming,
                persistent,
            )
            self.assertEqual(
                summary["selection"],
                "complete_persistent_override",
            )
            self.assertEqual(summary["persistentMissingBaseFiles"], [])


if __name__ == "__main__":
    unittest.main()
