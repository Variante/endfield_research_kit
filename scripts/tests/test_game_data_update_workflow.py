from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "game_data_update_workflow.py"
SPEC = importlib.util.spec_from_file_location("game_data_update_workflow", SCRIPT)
assert SPEC and SPEC.loader
workflow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = workflow
SPEC.loader.exec_module(workflow)


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.game_root = self.root / "Endfield_Data"
        self.export_root = self.root / "export_full"
        self.game_root.mkdir()
        self.export_root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def args(self, **overrides: object) -> argparse.Namespace:
        values: dict[str, object] = {
            "game_root": self.game_root,
            "export_root": self.export_root,
            "previous_export_root": self.root / "export_previous",
            "baseline": None,
            "animestudio": self.root / "AnimeStudio.CLI.exe",
            "operational_root": self.root / ".game-data-tracker" / "original-data",
            "plan": self.root / "reports" / "updates" / "plan.json",
            "skip_freshness_check": False,
            "asset_mode": "default",
            "animestudio_jobs": 2,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_public_asset_modes_map_to_internal_modes_and_wrapper_flags(self) -> None:
        self.assertEqual(
            workflow.ANIMESTUDIO_ASSET_MODES,
            {"focused": "focused", "default": "default", "debug": "debug"},
        )
        self.assertEqual(
            workflow.WEBUI_ASSET_FLAGS,
            {
                "focused": "--focused-assets",
                "default": "--default-assets",
                "debug": "--debug-assets",
            },
        )

    def test_initialize_publishes_one_source_baseline_without_overwrite(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str]) -> None:
            calls.append(command)
            if "snapshot" in command:
                output = Path(command[command.index("--output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"snapshot")
        with mock.patch.object(workflow, "ROOT", self.root), mock.patch.object(
            workflow, "_run", fake_run
        ):
            result = workflow.initialize_current_baseline(self.args())

        baseline = self.export_root / workflow.DEFAULT_BASELINE_REL
        self.assertEqual(baseline.read_bytes(), b"snapshot")
        self.assertNotIn("feed", result)
        self.assertEqual(len(calls), 3)
        self.assertEqual(
            sum(1 for command in calls if str(workflow.FRESHNESS_CHECK) in command),
            2,
        )
        with mock.patch.object(workflow, "ROOT", self.root), mock.patch.object(
            workflow, "_run", fake_run
        ):
            with self.assertRaises(workflow.WorkflowError):
                workflow.initialize_current_baseline(self.args())

    def test_unchanged_check_discards_candidate_and_touches_no_published_state(self) -> None:
        baseline = self.export_root / workflow.DEFAULT_BASELINE_REL
        baseline.parent.mkdir(parents=True)
        baseline.write_bytes(b"baseline")
        before = baseline.read_bytes()
        before_mtime = baseline.stat().st_mtime_ns

        def fake_run(command: list[str]) -> None:
            candidate = Path(command[command.index("--candidate") + 1])
            plan = Path(command[command.index("--plan") + 1])
            candidate.write_bytes(b"candidate")
            plan.write_text(
                json.dumps(
                    {
                        "logicalChanged": False,
                        "totals": {"added": 0, "modified": 0, "deleted": 0, "repacked": 0},
                    }
                ),
                encoding="utf-8",
            )

        args = self.args()
        args.plan.parent.mkdir(parents=True)
        args.plan.write_text("stale", encoding="utf-8")
        with mock.patch.object(workflow, "ROOT", self.root), mock.patch.object(
            workflow, "_run", fake_run
        ):
            result = workflow.check_current_version(args)

        self.assertFalse(result["logicalChanged"])
        self.assertEqual(baseline.read_bytes(), before)
        self.assertEqual(baseline.stat().st_mtime_ns, before_mtime)
        self.assertFalse(args.plan.exists())
        self.assertFalse((args.operational_root / "candidates").exists())

    def test_changed_check_publishes_plan_and_candidate_without_baseline_mutation(self) -> None:
        baseline = self.export_root / workflow.DEFAULT_BASELINE_REL
        baseline.parent.mkdir(parents=True)
        baseline.write_bytes(b"baseline")
        before = baseline.read_bytes()

        def fake_run(command: list[str]) -> None:
            candidate = Path(command[command.index("--candidate") + 1])
            plan = Path(command[command.index("--plan") + 1])
            candidate.write_bytes(b"candidate")
            plan.write_text(
                json.dumps(
                    {
                        "logicalChanged": True,
                        "candidate": {"snapshotId": "a" * 64},
                        "totals": {"added": 1, "modified": 0, "deleted": 0, "repacked": 0},
                    }
                ),
                encoding="utf-8",
            )

        args = self.args()
        with mock.patch.object(workflow, "ROOT", self.root), mock.patch.object(
            workflow, "_run", fake_run
        ):
            result = workflow.check_current_version(args)

        self.assertTrue(result["logicalChanged"])
        self.assertEqual(baseline.read_bytes(), before)
        published = json.loads(args.plan.read_text(encoding="utf-8"))
        self.assertEqual(published["candidate"]["snapshotId"], "a" * 64)
        self.assertEqual(published["candidate"]["path"], result["candidate"])
        self.assertEqual(Path(result["candidate"]).read_bytes(), b"candidate")

    def test_check_rejects_plan_alias_and_export_root_outputs(self) -> None:
        baseline = self.export_root / workflow.DEFAULT_BASELINE_REL
        baseline.parent.mkdir(parents=True)
        baseline.write_bytes(b"baseline")
        before = baseline.read_bytes()

        for plan in (baseline, self.export_root / "plan.json"):
            with self.subTest(plan=plan):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.check_current_version(self.args(plan=plan))
                self.assertEqual(baseline.read_bytes(), before)

        with self.assertRaises(workflow.WorkflowError):
            workflow.check_current_version(
                self.args(operational_root=self.export_root / "tracker-state")
            )

    def snapshot(
        self,
        path: Path,
        snapshot_id: str,
        *,
        data_md5: str,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(
                """
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE files (
                    source TEXT NOT NULL,
                    block TEXT NOT NULL,
                    logical_path TEXT NOT NULL,
                    data_md5 TEXT NOT NULL,
                    length INTEGER NOT NULL,
                    PRIMARY KEY (source, block, logical_path)
                );
                """
            )
            connection.execute(
                "INSERT INTO metadata VALUES ('snapshot_id', ?)", (snapshot_id,)
            )
            connection.execute(
                "INSERT INTO files VALUES (?, ?, ?, ?, ?)",
                (
                    "StreamingAssets",
                    "Table",
                    "Data/TableCfg/TestTable.bytes",
                    data_md5,
                    10,
                ),
            )
            connection.commit()

    def patch_fixture(self) -> tuple[argparse.Namespace, Path, Path]:
        baseline = self.export_root / workflow.DEFAULT_BASELINE_REL
        candidate = self.root / "candidate.sqlite3"
        self.snapshot(baseline, "a" * 64, data_md5="1" * 32)
        self.snapshot(candidate, "b" * 64, data_md5="2" * 32)
        (self.export_root / "old-marker.txt").write_text("old", encoding="utf-8")
        webui_data = self.root / "webui" / "data"
        webui_data.mkdir(parents=True)
        (webui_data / "old-feed.json").write_text("old", encoding="utf-8")
        args = self.args()
        args.plan.parent.mkdir(parents=True, exist_ok=True)
        args.plan.write_text(
            json.dumps(
                {
                    "baseline": {"snapshotId": "a" * 64},
                    "candidate": {"snapshotId": "b" * 64, "path": str(candidate)},
                    "logicalChanged": True,
                }
            ),
            encoding="utf-8",
        )
        return args, baseline, candidate

    def test_patch_scope_and_structured_output_mapping(self) -> None:
        rows = [
            {"source": "StreamingAssets", "block": "Table", "logicalPath": "x", "status": "modified"},
            {"source": "Persistent", "block": "AudioChinese", "logicalPath": "y", "status": "modified"},
            {"source": "Persistent", "block": "Bundle", "logicalPath": "z", "status": "modified"},
        ]
        self.assertEqual(
            workflow._structured_output_relative(
                "Table", "Data/TableCfg/CharacterConst.bytes"
            ).as_posix(),
            "Table/CharacterConst.json",
        )
        self.assertEqual(
            workflow._structured_output_relative("Video", "movies/a.usm").as_posix(),
            "movies/a.mp4",
        )
        scope = workflow._patch_scope(rows)
        self.assertTrue(scope["structured"])
        self.assertTrue(scope["audio"])
        self.assertTrue(scope["animestudio"])

    def test_structured_patch_exports_exact_changed_paths_and_removes_deletes(self) -> None:
        candidate = self.root / "candidate.sqlite3"
        self.snapshot(candidate, "b" * 64, data_md5="2" * 32)
        stage = self.root / "stage"
        deleted_output = (
            stage / "structured" / "StreamingAssets" / "Table" / "OldTable.json"
        )
        deleted_output.parent.mkdir(parents=True)
        deleted_output.write_text("old", encoding="utf-8")
        commands: list[list[str]] = []

        def fake_run(command: list[str]) -> None:
            commands.append(command)
            output = Path(command[command.index("--output") + 1])
            generated = output / "Table" / "TestTable.json"
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_text("new", encoding="utf-8")

        rows = [
            {
                "source": "StreamingAssets",
                "block": "Table",
                "logicalPath": "Data/TableCfg/TestTable.bytes",
                "status": "modified",
            },
            {
                "source": "StreamingAssets",
                "block": "Table",
                "logicalPath": "Data/TableCfg/OldTable.bytes",
                "status": "deleted",
            },
        ]
        with mock.patch.object(workflow, "_run", fake_run):
            result = workflow._apply_structured_patch(
                self.args(), stage, candidate, rows
            )

        self.assertEqual(result["commands"], 1)
        self.assertEqual(result["deletedOutputs"], 1)
        self.assertFalse(deleted_output.exists())
        self.assertTrue(
            (stage / "structured" / "StreamingAssets" / "Table" / "TestTable.json").is_file()
        )
        regex = commands[0][commands[0].index("--file-regex") + 1]
        self.assertRegex("Data/TableCfg/TestTable.bytes", regex)

    def test_occupied_archive_destination_gets_snapshot_suffix(self) -> None:
        preferred = self.root / "export_previous"
        preferred.mkdir()
        chosen = workflow._choose_archive_destination(preferred, "a" * 64)
        self.assertEqual(chosen.name, "export_previous_aaaaaaaaaaaa")
        self.assertTrue(preferred.is_dir())

    def test_interrupted_journal_blocks_apply_before_detection(self) -> None:
        args = self.args()
        journal = args.operational_root / "patch-transaction.json"
        journal.parent.mkdir(parents=True)
        journal.write_text("{}", encoding="utf-8")
        with mock.patch.object(workflow, "check_current_version") as check:
            with self.assertRaisesRegex(workflow.WorkflowError, "unfinished patch transaction"):
                workflow.build_patch_update(args)
        check.assert_not_called()

    def test_apply_no_change_touches_nothing(self) -> None:
        args = self.args()
        with mock.patch.object(
            workflow,
            "check_current_version",
            return_value={"logicalChanged": False, "totals": {}},
        ):
            result = workflow.build_patch_update(args)
        self.assertFalse(result["exportUpdated"])
        self.assertFalse(result["updatesPageBuilt"])

    def test_apply_rotates_only_after_staging_and_advances_baseline(self) -> None:
        args, baseline, candidate = self.patch_fixture()
        check_result = {
            "logicalChanged": True,
            "candidate": str(candidate),
            "totals": {"modified": 1},
        }
        patches = (
            mock.patch.object(workflow, "ROOT", self.root),
            mock.patch.object(workflow, "DEFAULT_EXPORT_ROOT", self.export_root),
            mock.patch.object(workflow, "check_current_version", return_value=check_result),
            mock.patch.object(workflow, "_apply_structured_patch", return_value={"changedFiles": 1}),
            mock.patch.object(workflow, "_refresh_patch_scopes"),
            mock.patch.object(workflow, "_validate_candidate_still_current"),
            mock.patch.object(workflow, "_run_webui_build"),
            mock.patch.object(workflow, "_run_updates_build"),
            mock.patch.object(workflow, "_run"),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            result = workflow.build_patch_update(args)

        self.assertTrue(result["exportUpdated"])
        self.assertEqual((args.previous_export_root / "old-marker.txt").read_text(), "old")
        self.assertEqual(workflow._snapshot_id_from_database(baseline), "b" * 64)
        self.assertEqual(
            workflow._snapshot_id_from_database(
                args.previous_export_root / workflow.DEFAULT_BASELINE_REL
            ),
            "a" * 64,
        )
        self.assertTrue(
            (self.root / "reports" / "updates" / "vfs-patch-build-latest.json").is_file()
        )

    def test_apply_failure_after_rotation_restores_export_and_webui(self) -> None:
        args, baseline, candidate = self.patch_fixture()
        summary_dir = self.root / "reports" / "export"
        summary_dir.mkdir(parents=True)
        summary_json = summary_dir / "export_full_summary.json"
        summary_md = summary_dir / "export_full_summary.md"
        summary_json.write_text("old summary", encoding="utf-8")
        check_result = {
            "logicalChanged": True,
            "candidate": str(candidate),
            "totals": {"modified": 1},
        }

        def fake_report_run(_command: list[str]) -> None:
            summary_json.write_text("new summary", encoding="utf-8")
            summary_md.write_text("new summary", encoding="utf-8")

        with mock.patch.object(workflow, "ROOT", self.root), mock.patch.object(
            workflow, "DEFAULT_EXPORT_ROOT", self.export_root
        ), mock.patch.object(
            workflow, "check_current_version", return_value=check_result
        ), mock.patch.object(
            workflow, "_apply_structured_patch", return_value={"changedFiles": 1}
        ), mock.patch.object(
            workflow, "_refresh_patch_scopes"
        ), mock.patch.object(
            workflow, "_validate_candidate_still_current"
        ), mock.patch.object(
            workflow, "_run_webui_build", side_effect=workflow.WorkflowError("builder failed")
        ), mock.patch.object(
            workflow, "_run_updates_build"
        ), mock.patch.object(
            workflow, "_run", fake_report_run
        ):
            with self.assertRaisesRegex(workflow.WorkflowError, "builder failed"):
                workflow.build_patch_update(args)

        self.assertEqual((self.export_root / "old-marker.txt").read_text(), "old")
        self.assertEqual(workflow._snapshot_id_from_database(baseline), "a" * 64)
        self.assertFalse(args.previous_export_root.exists())
        self.assertEqual(summary_json.read_text(encoding="utf-8"), "old summary")
        self.assertFalse(summary_md.exists())
        self.assertEqual(
            (self.root / "webui" / "data" / "old-feed.json").read_text(), "old"
        )
        self.assertFalse((args.operational_root / "patch-transaction.json").exists())


if __name__ == "__main__":
    unittest.main()
