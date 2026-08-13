from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


from scripts.updates_builder.scanner import ScanConfig, scan_export_changes


class ExportChangeScannerTests(unittest.TestCase):
    def test_scanner_returns_and_writes_the_same_focused_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_root = root / "export"
            tracked = export_root / "structured" / "Table" / "Items.json"
            ignored = export_root / "unrelated.json"
            tracked.parent.mkdir(parents=True)
            tracked.write_text('{"value": 1}\n', encoding="utf-8")
            ignored.write_text('{"ignored": true}\n', encoding="utf-8")

            config = ScanConfig(
                root=export_root,
                state_dir=root / "state",
                summary_json=root / "reports" / "summary.json",
                summary_md=root / "reports" / "summary.md",
                include_relative_paths=("structured/Table",),
                workers=1,
                hash_batch_size=1,
            )
            initial = scan_export_changes(config)
            self.assertEqual(initial.payload["changes"]["added"], 1)
            self.assertEqual(initial.payload["scanned_files"], 1)

            tracked.write_text('{"value": 200}\n', encoding="utf-8")
            changed = scan_export_changes(config)

            self.assertEqual(changed.payload["changes"]["modified"], 1)
            self.assertEqual(changed.payload["changes"]["added"], 0)
            self.assertEqual(
                json.loads(config.summary_json.read_text(encoding="utf-8")),
                changed.payload,
            )
            self.assertTrue(config.summary_md.is_file())

    def test_missing_export_root_fails_with_its_resolved_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing"
            config = ScanConfig(
                root=missing,
                state_dir=root / "state",
                summary_json=root / "summary.json",
                summary_md=root / "summary.md",
            )

            with self.assertRaisesRegex(FileNotFoundError, str(missing.resolve()).replace("\\", "\\\\")):
                scan_export_changes(config)


if __name__ == "__main__":
    unittest.main()
