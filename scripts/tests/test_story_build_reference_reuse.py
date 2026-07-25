from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.language_bundle import load_reused_reference_stats


class StoryBuildReferenceReuseTests(unittest.TestCase):
    def _write_fixture(
        self,
        root: Path,
        *,
        language: str = "CN",
        file_name: str = "streaming/Fixture.json",
    ) -> Path:
        reference_dir = root / "reference"
        payload_path = reference_dir / "streaming" / "Fixture.json"
        payload_path.parent.mkdir(parents=True)
        payload_path.write_text("{}", encoding="utf-8")
        (reference_dir / "index.json").write_text(
            json.dumps({
                "language": language,
                "tables": [{
                    "source": "streaming",
                    "table": "Fixture.json",
                    "file": file_name,
                }],
                "stats": {
                    "tables": 1,
                    "rows": 2,
                    "texts": 3,
                    "bytes": 4,
                },
            }),
            encoding="utf-8",
        )
        return reference_dir

    def test_validated_reference_bundle_can_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_dir = self._write_fixture(Path(temp_dir))
            stats = load_reused_reference_stats(reference_dir, "CN")

        self.assertEqual({
            "tables": 1,
            "rows": 2,
            "texts": 3,
            "bytes": 4,
        }, stats)

    def test_wrong_language_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_dir = self._write_fixture(Path(temp_dir), language="EN")
            with self.assertRaisesRegex(RuntimeError, "belongs to"):
                load_reused_reference_stats(reference_dir, "CN")

    def test_missing_indexed_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_dir = self._write_fixture(
                Path(temp_dir),
                file_name="streaming/Missing.json",
            )
            with self.assertRaisesRegex(RuntimeError, "indexed file is missing"):
                load_reused_reference_stats(reference_dir, "CN")

    def test_parent_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_dir = self._write_fixture(
                Path(temp_dir),
                file_name="../outside.json",
            )
            with self.assertRaisesRegex(RuntimeError, "unsafe file path"):
                load_reused_reference_stats(reference_dir, "CN")


if __name__ == "__main__":
    unittest.main()
