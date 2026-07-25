from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "track_game_data_updates.py"
SPEC = importlib.util.spec_from_file_location("track_game_data_updates", SCRIPT)
assert SPEC and SPEC.loader
tracker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tracker
SPEC.loader.exec_module(tracker)


def md5(character: str) -> str:
    return character * 32


def records(version: int, files: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = [
        {
            "recordType": "header",
            "format": "animestudio-vfs-index",
            "encoding": "jsonl",
            "schemaVersion": 1,
        },
        {
            "recordType": "block",
            "name": "table",
            "version": version,
            "codeVersion": 4,
            "hashDirectory": "table-hash",
        },
    ]
    chunks: dict[str, list[dict[str, object]]] = {}
    for item in files:
        chunks.setdefault(str(item["chunk"]), []).append(item)
    for chunk_name, chunk_files in chunks.items():
        chunk_md5 = str(chunk_files[0]["chunk_md5"])
        result.append(
            {
                "recordType": "chunk",
                "blockType": "table",
                "fileName": chunk_name,
                "contentMd5": chunk_md5,
                "length": 100,
                "source": "primary",
            }
        )
        for item in chunk_files:
            result.append(
                {
                    "recordType": "file",
                    "blockType": "table",
                    "name": item["path"],
                    "dataMd5": item["md5"],
                    "length": item["length"],
                }
            )
    result.append({"recordType": "summary", "fileCount": len(files)})
    return result


class TrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_jsonl(self, name: str, payload: list[dict[str, object]]) -> Path:
        path = self.root / name
        path.write_text(
            "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in payload),
            encoding="utf-8",
        )
        return path

    def build(
        self,
        destination: Path,
        streaming: list[dict[str, object]],
        persistent: list[dict[str, object]],
        *,
        replace: bool = False,
    ) -> dict[str, object]:
        return tracker.build_snapshot(
            destination,
            self.write_jsonl(destination.stem + "-streaming.jsonl", streaming),
            self.write_jsonl(destination.stem + "-persistent.jsonl", persistent),
            replace=replace,
        )

    def test_baseline_snapshot_is_deterministic_and_refuses_overwrite(self) -> None:
        source = records(
            10,
            [
                {"path": r"Table\Items.json", "md5": md5("a"), "length": 8, "chunk": "c1", "chunk_md5": md5("1")},
            ],
        )
        empty = records(20, [])
        first = self.build(self.root / "baseline.sqlite", source, empty)
        second = self.build(self.root / "other.sqlite", source, empty)
        self.assertEqual(first["snapshotId"], second["snapshotId"])
        with closing(sqlite3.connect(self.root / "baseline.sqlite")) as connection:
            row = connection.execute("SELECT logical_path FROM files").fetchone()
        self.assertEqual(row[0], "Table/Items.json")
        with self.assertRaises(tracker.TrackerError):
            self.build(self.root / "baseline.sqlite", source, empty)

    def test_logical_path_validation_rejects_unsafe_and_aliasing_names(self) -> None:
        self.assertEqual(
            tracker.normalize_logical_path(r"Table\Items.json"), "Table/Items.json"
        )
        invalid = (
            "bad\0name",
            "/rooted/path",
            r"\rooted\path",
            r"C:\drive\path",
            "./alias",
            "folder/../alias",
            "folder/./alias",
            "folder//alias",
            "folder/",
            "e\u0301/decomposed",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(tracker.TrackerError):
                tracker.normalize_logical_path(value)

    def test_diff_reports_logical_changes_and_repack_with_linkage(self) -> None:
        old = records(
            100,
            [
                {"path": "same", "md5": md5("a"), "length": 1, "chunk": "old", "chunk_md5": md5("1")},
                {"path": "modify", "md5": md5("b"), "length": 2, "chunk": "old", "chunk_md5": md5("1")},
                {"path": "delete", "md5": md5("c"), "length": 3, "chunk": "old", "chunk_md5": md5("1")},
            ],
        )
        new = records(
            101,
            [
                {"path": "same", "md5": md5("a"), "length": 1, "chunk": "new", "chunk_md5": md5("2")},
                {"path": "modify", "md5": md5("d"), "length": 4, "chunk": "new", "chunk_md5": md5("2")},
                {"path": "add", "md5": md5("e"), "length": 5, "chunk": "new", "chunk_md5": md5("2")},
            ],
        )
        empty = records(200, [])
        baseline = self.root / "baseline.sqlite"
        candidate = self.root / "candidate.sqlite"
        self.build(baseline, old, empty)
        before = baseline.read_bytes()
        before_mtime = baseline.stat().st_mtime_ns
        self.build(candidate, new, empty)
        plan = tracker.compare_snapshots(baseline, candidate, sample_limit=2)
        self.assertEqual(
            plan["totals"], {"added": 1, "modified": 1, "deleted": 1, "repacked": 1}
        )
        self.assertTrue(plan["logicalChanged"])
        self.assertEqual(len(plan["samples"]), 2)
        modified = next(item for item in plan["entries"] if item["status"] == "modified")
        self.assertEqual(modified["oldRevision"], {"version": 100, "codeVersion": 4})
        self.assertEqual(modified["newRevision"], {"version": 101, "codeVersion": 4})
        self.assertEqual(modified["oldChunk"]["name"], "old")
        self.assertEqual(modified["newChunk"]["contentMd5"], md5("2"))
        self.assertEqual(baseline.read_bytes(), before)
        self.assertEqual(baseline.stat().st_mtime_ns, before_mtime)

    def test_entry_limit_keeps_exact_totals_samples_and_truncation_by_status(self) -> None:
        old = records(
            1,
            [
                {"path": "delete", "md5": md5("a"), "length": 1, "chunk": "old", "chunk_md5": md5("1")},
                {"path": "modify", "md5": md5("b"), "length": 2, "chunk": "old", "chunk_md5": md5("1")},
                {"path": "repack", "md5": md5("c"), "length": 3, "chunk": "old", "chunk_md5": md5("1")},
            ],
        )
        new = records(
            2,
            [
                {"path": "add", "md5": md5("d"), "length": 4, "chunk": "new", "chunk_md5": md5("2")},
                {"path": "modify", "md5": md5("e"), "length": 5, "chunk": "new", "chunk_md5": md5("2")},
                {"path": "repack", "md5": md5("c"), "length": 3, "chunk": "new", "chunk_md5": md5("2")},
            ],
        )
        empty = records(3, [])
        baseline = self.root / "baseline.sqlite"
        candidate = self.root / "candidate.sqlite"
        self.build(baseline, old, empty)
        self.build(candidate, new, empty)
        plan = tracker.compare_snapshots(
            baseline, candidate, entry_limit=2, sample_limit=3
        )
        self.assertEqual(
            plan["totals"], {"added": 1, "modified": 1, "deleted": 1, "repacked": 1}
        )
        self.assertEqual(len(plan["entries"]), 2)
        self.assertEqual(len(plan["samples"]), 3)
        self.assertEqual(plan["entriesTruncated"], 2)
        self.assertEqual(
            plan["truncatedCounts"],
            {"added": 0, "modified": 1, "deleted": 0, "repacked": 1},
        )

    def test_repack_only_has_same_snapshot_id_and_needs_no_promotion(self) -> None:
        original = records(
            10,
            [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")}],
        )
        repacked = records(
            11,
            [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "b", "chunk_md5": md5("2")}],
        )
        empty = records(20, [])
        baseline = self.root / "baseline.sqlite"
        candidate = self.root / "candidate.sqlite"
        old_result = self.build(baseline, original, empty)
        new_result = self.build(candidate, repacked, empty)
        plan = tracker.compare_snapshots(baseline, candidate)
        self.assertEqual(old_result["snapshotId"], new_result["snapshotId"])
        self.assertFalse(plan["logicalChanged"])
        self.assertFalse(plan["promotionRequired"])
        self.assertEqual(plan["totals"]["repacked"], 1)

    def test_unchanged_check_does_not_touch_baseline(self) -> None:
        current = records(
            10,
            [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")}],
        )
        empty = records(20, [])
        baseline = self.root / "baseline.sqlite"
        candidate = self.root / "candidate.sqlite"
        self.build(baseline, current, empty)
        before = baseline.read_bytes()
        before_mtime = baseline.stat().st_mtime_ns
        self.build(candidate, current, empty)
        plan = tracker.compare_snapshots(baseline, candidate)
        self.assertFalse(plan["logicalChanged"])
        self.assertEqual(
            plan["totals"], {"added": 0, "modified": 0, "deleted": 0, "repacked": 0}
        )
        self.assertEqual(baseline.read_bytes(), before)
        self.assertEqual(baseline.stat().st_mtime_ns, before_mtime)

    def test_csharp_flat_file_fields_use_containing_block_name(self) -> None:
        streaming = [
            {
                "recordType": "header",
                "format": "animestudio-vfs-index",
                "encoding": "jsonl",
                "schemaVersion": 1,
            },
            {
                "recordType": "block",
                "name": "bundle",
                "version": 7,
                "codeVersion": 4,
            },
            {
                "recordType": "file",
                "blockName": "bundle",
                "fileBlockType": "initial-bundle",
                "fileName": r"Bundles\characters.ab",
                "fileDataMd5": md5("a"),
                "length": 42,
                "chunkFile": "chunk.bin",
                "chunkContentMd5": md5("1"),
                "chunkSource": "fallback",
                "fileNameHash": "123",
            },
            {"recordType": "summary", "fileCount": 1, "missingChunkCount": 0},
        ]
        destination = self.root / "snapshot.sqlite"
        self.build(destination, streaming, records(8, []))
        with closing(sqlite3.connect(destination)) as connection:
            row = connection.execute(
                "SELECT block, logical_path, chunk_source FROM files WHERE source='StreamingAssets'"
            ).fetchone()
        self.assertEqual(row, ("bundle", "Bundles/characters.ab", "fallback"))

    def test_rejects_truncated_scan_missing_chunk_and_duplicate(self) -> None:
        valid_empty = records(1, [])
        truncated = [
            {
                "recordType": "header",
                "format": "animestudio-vfs-index",
                "encoding": "jsonl",
                "schemaVersion": 1,
            },
            {"recordType": "block", "name": "table", "version": 1, "codeVersion": 4},
        ]
        with self.assertRaisesRegex(tracker.TrackerError, "terminal summary"):
            self.build(self.root / "truncated.sqlite", truncated, valid_empty)

        missing_chunk = [
            {
                "recordType": "header",
                "format": "animestudio-vfs-index",
                "encoding": "jsonl",
                "schemaVersion": 1,
            },
            {"recordType": "block", "name": "table", "version": 1, "codeVersion": 4},
            {
                "recordType": "chunk",
                "blockType": "table",
                "fileName": "missing",
                "contentMd5": md5("1"),
                "exists": False,
            },
            {"recordType": "summary", "fileCount": 0, "missingChunkCount": 1},
        ]
        with self.assertRaisesRegex(tracker.TrackerError, "missing chunk"):
            self.build(self.root / "missing.sqlite", missing_chunk, valid_empty)

        duplicate = records(
            1,
            [
                {"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")},
                {"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")},
            ],
        )
        with self.assertRaisesRegex(tracker.TrackerError, "duplicate logical file"):
            self.build(self.root / "duplicate.sqlite", duplicate, valid_empty)

    def test_compare_rejects_a_previously_present_block_becoming_missing(self) -> None:
        present = records(
            10,
            [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")}],
        )
        missing = [
            {
                "recordType": "header",
                "format": "animestudio-vfs-index",
                "encoding": "jsonl",
                "schemaVersion": 1,
            },
            {"recordType": "missingBlock", "name": "table", "hashDirectory": "table-hash"},
            {
                "recordType": "summary",
                "fileCount": 0,
                "missingBlockCount": 1,
                "missingChunkCount": 0,
            },
        ]
        empty = records(20, [])
        baseline = self.root / "baseline.sqlite"
        candidate = self.root / "candidate.sqlite"
        self.build(baseline, present, empty)
        self.build(candidate, missing, empty)
        with self.assertRaisesRegex(tracker.TrackerError, "potentially incomplete"):
            tracker.compare_snapshots(baseline, candidate)

    def test_cli_baseline_current_and_check_leave_baseline_immutable(self) -> None:
        old_streaming = self.write_jsonl(
            "old-streaming.jsonl",
            records(1, [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")}]),
        )
        new_streaming = self.write_jsonl(
            "new-streaming.jsonl",
            records(2, [{"path": "x", "md5": md5("b"), "length": 1, "chunk": "a", "chunk_md5": md5("2")}]),
        )
        persistent = self.write_jsonl("persistent.jsonl", records(3, []))
        baseline = self.root / "state" / "baseline.sqlite"
        candidate = self.root / "work" / "candidate.sqlite"
        plan_path = self.root / "plans" / "plan.json"
        self.assertEqual(
            tracker.main(
                [
                    "baseline-current", "--baseline", str(baseline),
                    "--streaming-jsonl", str(old_streaming), "--persistent-jsonl", str(persistent),
                ]
            ),
            0,
        )
        before = baseline.read_bytes()
        self.assertEqual(
            tracker.main(
                [
                    "check", "--baseline", str(baseline), "--candidate", str(candidate),
                    "--plan", str(plan_path), "--streaming-jsonl", str(new_streaming),
                    "--persistent-jsonl", str(persistent), "--entry-limit", "0",
                ]
            ),
            0,
        )
        self.assertEqual(baseline.read_bytes(), before)
        written_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertTrue(written_plan["logicalChanged"])
        self.assertEqual(written_plan["entries"], [])
        self.assertEqual(written_plan["entriesTruncated"], 1)
        with closing(sqlite3.connect(baseline)) as connection:
            value = connection.execute("SELECT data_md5 FROM files").fetchone()[0]
        self.assertEqual(value, md5("a"))

    def test_cli_check_rejects_all_output_path_aliases_before_mutation(self) -> None:
        current = records(
            1,
            [{"path": "x", "md5": md5("a"), "length": 1, "chunk": "a", "chunk_md5": md5("1")}],
        )
        streaming = self.write_jsonl("alias-streaming.jsonl", current)
        persistent = self.write_jsonl("alias-persistent.jsonl", records(2, []))
        baseline = self.root / "baseline.sqlite"
        self.build(baseline, current, records(2, []))
        before = baseline.read_bytes()

        cases = (
            (baseline, self.root / "plan.json"),
            (self.root / "candidate.sqlite", baseline),
            (self.root / "shared-output", self.root / "shared-output"),
        )
        for candidate, plan in cases:
            with self.subTest(candidate=candidate, plan=plan):
                self.assertEqual(
                    tracker.main(
                        [
                            "check",
                            "--baseline",
                            str(baseline),
                            "--candidate",
                            str(candidate),
                            "--plan",
                            str(plan),
                            "--streaming-jsonl",
                            str(streaming),
                            "--persistent-jsonl",
                            str(persistent),
                        ]
                    ),
                    2,
                )
                self.assertEqual(baseline.read_bytes(), before)

    def test_live_scan_uses_bidirectional_vfs_fallbacks(self) -> None:
        game_root = self.root / "Endfield_Data"
        for source in tracker.SOURCES:
            catalog = game_root / source / "VFS" / "table" / "table.blc"
            catalog.parent.mkdir(parents=True)
            catalog.write_bytes(b"catalog")
        executable = self.root / "AnimeStudio.CLI.exe"
        executable.write_bytes(b"")
        commands: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> object:
            commands.append(command)
            if len(commands) == 1:
                return subprocess.CompletedProcess(command, 0, stdout="--jsonl", stderr="")
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(tracker.subprocess, "run", side_effect=fake_run):
            tracker._invoke_animestudio(executable, game_root, self.root / "scan")

        streaming_command, persistent_command = commands[1:]
        self.assertEqual(
            streaming_command[streaming_command.index("--fallback-assets") + 1],
            str(game_root / "Persistent"),
        )
        self.assertEqual(
            persistent_command[persistent_command.index("--fallback-assets") + 1],
            str(game_root / "StreamingAssets"),
        )
        for command in (streaming_command, persistent_command):
            tracked_blocks = [
                command[index + 1]
                for index, value in enumerate(command)
                if value == "--block-type"
            ]
            self.assertEqual(tracked_blocks, list(tracker.WEBUI_TRACKED_VFS_BLOCKS))
            self.assertIn("AudioChinese", tracked_blocks)
            self.assertNotIn("AudioEnglish", tracked_blocks)
            self.assertNotIn("AuditAudio", tracked_blocks)

    def test_live_scan_rejects_vfs_metadata_mutation(self) -> None:
        game_root = self.root / "Endfield_Data"
        for source in tracker.SOURCES:
            catalog = game_root / source / "VFS" / "table" / "table.blc"
            catalog.parent.mkdir(parents=True)
            catalog.write_bytes(b"before")
        executable = self.root / "AnimeStudio.CLI.exe"
        executable.write_bytes(b"")
        call_count = 0

        def fake_run(command: list[str], **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return subprocess.CompletedProcess(command, 0, stdout="--jsonl", stderr="")
            if call_count == 3:
                catalog = game_root / "Persistent" / "VFS" / "table" / "table.blc"
                catalog.write_bytes(b"after")
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(tracker.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(tracker.TrackerError, "changed during the scan"):
                tracker._invoke_animestudio(executable, game_root, self.root / "scan")


if __name__ == "__main__":
    unittest.main()
