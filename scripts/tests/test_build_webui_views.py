from __future__ import annotations

import ast
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_assets, build_gameplay, build_webui_views

ROOT = Path(__file__).resolve().parents[2]


def task_names(phases: list[tuple[str, list[build_webui_views.TaskSpec]]]) -> list[list[str]]:
    return [[task.name for task in tasks] for _, tasks in phases]


def commands_for(
    phases: list[tuple[str, list[build_webui_views.TaskSpec]]],
    task_name: str,
) -> list[tuple[str, ...]]:
    return [
        command.argv
        for _, tasks in phases
        for task in tasks
        if task.name == task_name
        for command in task.commands
    ]


class WebuiViewPlanTests(unittest.TestCase):
    def test_gameplay_base_builder_uses_scripts_package_identity(self) -> None:
        from scripts import common
        from scripts.gameplay_builder import base_data

        self.assertIs(base_data.write_json, common.write_json)
        tree = ast.parse(inspect.getsource(base_data))
        self.assertFalse(
            any(
                isinstance(node, ast.Attribute)
                and node.attr == "path"
                and isinstance(node.value, ast.Name)
                and node.value.id == "sys"
                for node in ast.walk(tree)
            )
        )

    def test_default_plan_keeps_graph_after_every_producer(self) -> None:
        args = build_webui_views.parse_args([])
        phases = build_webui_views.build_phases(args)

        self.assertEqual(
            task_names(phases),
            [
                [
                    "mission_pipeline",
                    "characters",
                    "gameplay",
                    "projectiles",
                ],
                ["gameplay_asset_refs"],
                ["source_graph"],
                ["gameplay_asset_refs_after_graph", "combat_relationships"],
            ],
        )
        self.assertIn("--relevant-asset-maps", commands_for(phases, "source_graph")[0])
        self.assertNotIn("audio", [name for phase in task_names(phases) for name in phase])
        for task_name in ("mission_pipeline", "characters", "gameplay", "projectiles"):
            self.assertEqual(commands_for(phases, task_name)[-1][1], "-m")

    def test_gameplay_base_is_followed_by_recovery_audit_in_same_task(self) -> None:
        args = build_webui_views.parse_args([])
        gameplay_task = next(
            task
            for _, tasks in build_webui_views.build_phases(args)
            for task in tasks
            if task.name == "gameplay"
        )
        stages = [
            command.argv[command.argv.index("--stage") + 1]
            for command in gameplay_task.commands
        ]
        self.assertEqual(["base", "audit"], stages)
        for command in gameplay_task.commands:
            self.assertIn("--languages", command.argv)
            self.assertIn("--default-language", command.argv)

    def test_graph_refreshes_gameplay_asset_refs_without_rebuilding_base(self) -> None:
        args = build_webui_views.parse_args([])
        phases = build_webui_views.build_phases(args)
        phase_names = [name for name, _ in phases]
        graph_index = phase_names.index("source_graph")
        consumer_index = phase_names.index("graph_consumers")
        self.assertLess(graph_index, consumer_index)

        asset_ref_tasks = [
            task
            for _, tasks in phases
            for task in tasks
            if task.name.startswith("gameplay_asset_refs")
        ]
        self.assertEqual(
            [task.name for task in asset_ref_tasks],
            ["gameplay_asset_refs", "gameplay_asset_refs_after_graph"],
        )
        for task in asset_ref_tasks:
            self.assertEqual(len(task.commands), 1)
            command = task.commands[0].argv
            self.assertEqual(command[command.index("--stage") + 1], "asset-refs")

        gameplay_commands = commands_for(phases, "gameplay")
        self.assertEqual(
            [command[command.index("--stage") + 1] for command in gameplay_commands],
            ["base", "audit"],
        )

    def test_asset_plan_joins_character_and_refs_after_fresh_asset_index(self) -> None:
        args = build_webui_views.parse_args(
            ["--with-assets", "--asset-mode", "debug", "--decode-audio"]
        )
        phases = build_webui_views.build_phases(args)

        self.assertEqual(task_names(phases)[0][:3], ["mission_pipeline", "assets", "gameplay"])
        self.assertNotIn("characters", task_names(phases)[0])
        self.assertEqual(
            task_names(phases)[1],
            ["characters", "gameplay_asset_refs", "audio"],
        )
        asset_command = commands_for(phases, "assets")[0]
        self.assertNotIn("--skip-gameplay-refs", asset_command)
        self.assertEqual(asset_command[asset_command.index("--mode") + 1], "debug")
        self.assertNotIn("--skip-decode", commands_for(phases, "audio")[0])

    def test_mission_only_plan_has_no_unrelated_views(self) -> None:
        args = build_webui_views.parse_args(["--mission-pipeline-only"])
        phases = build_webui_views.build_phases(args)

        self.assertEqual(task_names(phases), [["mission_pipeline"]])
        protocol_command = commands_for(phases, "mission_pipeline")[0]
        self.assertEqual(
            protocol_command[1:3],
            ("-m", "scripts.story_builder.protocol_registry"),
        )

    def test_full_graph_omits_relevant_scope_filters(self) -> None:
        args = build_webui_views.parse_args(["--full-source-graph"])
        graph_command = commands_for(build_webui_views.build_phases(args), "source_graph")[0]

        self.assertNotIn("--relevant-asset-maps", graph_command)
        self.assertNotIn("--skip-reference-rows", graph_command)

    def test_asset_builder_rejects_retired_gameplay_sidecar_option(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            build_assets.parse_args(["--skip-gameplay-refs"])

    def test_gameplay_stage_owns_asset_refs_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            gameplay_path = data_root / "lang/CN/gameplay/index.json"
            asset_index_path = data_root / "assets/index.json"
            output_path = data_root / "assets/gameplay_refs.json"
            gameplay_path.parent.mkdir(parents=True)
            asset_index_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
            asset_index_path.write_text(json.dumps({"entries": []}), encoding="utf-8")

            self.assertEqual(
                build_gameplay.build_asset_refs_stage("cn", data_root=data_root),
                0,
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["counts"]["entries"], 0)
            self.assertEqual(payload["sourcePath"], str(asset_index_path).replace("\\", "/"))

    def test_asset_export_runs_gameplay_owner_after_asset_index(self) -> None:
        source = (ROOT / "export_assets.bat").read_text(encoding="utf-8")

        asset_index = source.index("scripts\\build_assets.py")
        gameplay_refs = source.index(
            "scripts\\build_gameplay.py --stage asset-refs --default-language CN"
        )
        audio = source.index("scripts\\build_audio.py", gameplay_refs)
        self.assertLess(asset_index, gameplay_refs)
        self.assertLess(gameplay_refs, audio)

    def test_custom_roots_are_forwarded_to_every_subprocess_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = build_webui_views.parse_args(
                [
                    "--export-root",
                    str(root / "export"),
                    "--game-root",
                    str(root / "game"),
                ]
            )
            commands = [
                command
                for _, tasks in build_webui_views.build_phases(args)
                for task in tasks
                for command in task.commands
            ]

            self.assertTrue(commands)
            for command in commands:
                environment = dict(command.environment)
                self.assertEqual(
                    environment["ENDFIELD_EXPORT_ROOT"],
                    str((root / "export").resolve()),
                )
                self.assertEqual(
                    environment["ENDFIELD_GAME_ROOT"],
                    str((root / "game").resolve()),
                )


if __name__ == "__main__":
    unittest.main()
