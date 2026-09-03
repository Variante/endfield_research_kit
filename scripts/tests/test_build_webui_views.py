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
                    "map_recovery",
                    "characters",
                    "gameplay",
                    "projectiles",
                ],
                ["gameplay_asset_refs", "map_recovery"],
                ["source_graph"],
                ["gameplay_asset_refs_after_graph", "combat_relationships"],
            ],
        )
        self.assertIn("--relevant-asset-maps", commands_for(phases, "source_graph")[0])
        self.assertNotIn("audio", [name for phase in task_names(phases) for name in phase])
        for task_name in ("map_recovery", "characters", "gameplay", "projectiles"):
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
            command.argv[index + 1]
            for command in gameplay_task.commands
            for index, argument in enumerate(command.argv)
            if argument == "--stage"
        ]
        self.assertEqual(["base", "audit"], stages)
        for command in gameplay_task.commands:
            self.assertIn("--languages", command.argv)
            self.assertIn("--default-language", command.argv)

    def test_gameplay_asset_refs_refresh_after_graph_without_rebuilding_base(self) -> None:
        args = build_webui_views.parse_args([])
        phases = build_webui_views.build_phases(args)
        phase_names = [name for name, _ in phases]
        graph_index = phase_names.index("source_graph")
        refs_phase_index = next(
            index
            for index, (_, tasks) in enumerate(phases)
            if any(task.name == "gameplay_asset_refs" for task in tasks)
        )
        self.assertLess(refs_phase_index, graph_index)

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
            ["base"],
        )
        self.assertEqual(gameplay_commands[0].count("--stage"), 2)

    def test_asset_plan_joins_character_and_refs_after_fresh_asset_index(self) -> None:
        args = build_webui_views.parse_args(
            ["--with-assets", "--asset-mode", "debug", "--decode-audio"]
        )
        phases = build_webui_views.build_phases(args)

        self.assertEqual(task_names(phases)[0][:3], ["map_recovery", "assets", "gameplay"])
        self.assertNotIn("characters", task_names(phases)[0])
        self.assertEqual(
            task_names(phases)[1],
            ["characters", "gameplay_asset_refs", "map_recovery", "audio"],
        )
        asset_command = commands_for(phases, "assets")[0]
        self.assertNotIn("--skip-gameplay-refs", asset_command)
        self.assertEqual(asset_command[asset_command.index("--mode") + 1], "debug")
        self.assertNotIn("--skip-decode", commands_for(phases, "audio")[0])

    def test_full_plan_refreshes_preview_without_rebuilding_map_data(self) -> None:
        phases = build_webui_views.build_phases(build_webui_views.parse_args([]))
        map_commands = [
            command
            for command in commands_for(phases, "map_recovery")
            if "scripts.build_map_recovery_data" in command
        ]
        self.assertEqual(len(map_commands), 2)
        self.assertNotIn("--preview-only", map_commands[0])
        self.assertIn("--preview-only", map_commands[1])
        joined_map_task = next(
            task for name, tasks in phases if name == "joined_sidecars"
            for task in tasks if task.name == "map_recovery"
        )
        self.assertIn("recover_map_streaming_instances.py", joined_map_task.commands[0].argv[1])
        self.assertIn("--all-published-map-scenes", joined_map_task.commands[0].argv)
        self.assertIn("--preview-only", joined_map_task.commands[1].argv)

    def test_normal_map_build_uses_worker_budget_but_asset_build_stays_serial(self) -> None:
        normal = commands_for(
            build_webui_views.build_phases(build_webui_views.parse_args(["--jobs", "3"])),
            "map_recovery",
        )
        self.assertEqual(normal[0][normal[0].index("--jobs") + 1], "3")
        self.assertEqual(normal[1][normal[1].index("--jobs") + 1], "3")

        with_assets = commands_for(
            build_webui_views.build_phases(
                build_webui_views.parse_args(["--jobs", "3", "--with-assets"])
            ),
            "map_recovery",
        )
        self.assertEqual(with_assets[0][with_assets[0].index("--jobs") + 1], "1")
        self.assertEqual(with_assets[1][with_assets[1].index("--jobs") + 1], "1")

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
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertIn(
            "scripts\\build_webui_views.py %WEBUI_VIEW_ARGS% %GAME_ROOT_ARG% %EXPORT_ROOT_ARG%",
            source,
        )
        self.assertIn('set "WEBUI_VIEW_ARGS=--jobs "', source)
        self.assertIn("--with-assets", source)
        self.assertIn("--decode-audio", source)
        self.assertNotIn("scripts\\build_assets.py --mode", source)
        self.assertNotIn("scripts\\build_gameplay.py --stage asset-refs", source)
        self.assertNotIn("scripts\\build_audio.py --skip-decode", source)

    def test_asset_wrapper_delegates_to_the_single_export_entry_point(self) -> None:
        source = (ROOT / "export_assets.bat").read_text(encoding="utf-8")
        self.assertIn('call "%~dp0export.bat" --assets-only %*', source)
        # The wrapper must not carry its own copy of the option parser, the
        # freshness check, or the builder invocation; those drifted before.
        for duplicated in (
            ":parse_args",
            ":validate_asset_mode",
            "verify_export_freshness",
            "build_webui_views.py",
            "export_full_from_game.py",
        ):
            self.assertNotIn(duplicated, source)

    def test_export_wrapper_announces_long_running_stages_and_uses_crlf(self) -> None:
        messages = (
            "Resolved export options",
            "Checking export_full freshness",
            "Refreshing Story recovery evidence",
            "Building CN Story conversations",
            "Building Characters, Gameplay, map recovery",
            "source graph, and combat relationships",
            "Export pipeline complete",
        )
        for name in ("export.bat", "export_assets.bat"):
            raw = (ROOT / name).read_bytes()
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), name)
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertIn("[export.bat %time%] === %~1 ===", source)
        for message in messages:
            self.assertIn(message, source)

    def test_export_wrapper_owns_no_second_copy_of_the_mission_stage(self) -> None:
        # Mission Pipeline is maintained as a direct Python workflow and is
        # intentionally absent from the WebUI export plan.
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertNotIn(
            "mission_pipeline",
            [name for phase in task_names(build_webui_views.build_phases(build_webui_views.parse_args([]))) for name in phase],
        )
        self.assertTrue(any(
            "--preview-only" in command
            for command in commands_for(
                build_webui_views.build_phases(build_webui_views.parse_args([])),
                "map_recovery",
            )
        ))

    def test_export_wrapper_preflights_the_arguments_it_will_actually_run(self) -> None:
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        preflight = (
            "python .\\scripts\\build_webui_views.py %WEBUI_VIEW_ARGS%"
            " %GAME_ROOT_ARG% %EXPORT_ROOT_ARG% --dry-run >nul"
        )
        self.assertIn(preflight, source)
        # The dry run has to follow the assembly of the args it validates.
        self.assertLess(
            source.index('set "WEBUI_VIEW_ARGS=--jobs "'),
            source.index(preflight),
        )
        self.assertNotIn("--mission-pipeline-only", source)
        self.assertNotIn("--mission-pipeline-data-only", source)
        self.assertNotIn("if \"%POST_STORY_VIEWS%\"==\"0\" goto :preflight_done", source)

    def test_export_wrapper_forwards_configured_output_to_extraction(self) -> None:
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertIn(
            'set "EXTRACTION_OUTPUT_ARG=--output "%ENDFIELD_EXPORT_ROOT%""',
            source,
        )
        extraction_lines = [
            line
            for line in source.splitlines()
            if line.startswith("python .\\scripts\\export_full_from_game.py")
        ]
        self.assertEqual(len(extraction_lines), 3)
        for line in extraction_lines:
            self.assertIn("%EXTRACTION_OUTPUT_ARG%", line)

    def test_export_wrapper_rejects_object_index_when_story_is_reused(self) -> None:
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertIn(
            'if "%STORY_BUILD%"=="0" if "%ANIMESTUDIO_OBJECT_INDEX%"=="1" goto :object_index_without_story',
            source,
        )

    def test_export_wrapper_checks_freshness_once_for_every_scope(self) -> None:
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertEqual(source.count("verify_export_freshness.py"), 1)
        self.assertIn(
            "python .\\scripts\\verify_export_freshness.py %GAME_ROOT_ARG%",
            source,
        )

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
