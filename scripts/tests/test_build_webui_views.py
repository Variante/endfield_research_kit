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


def graph(*argv: str) -> dict[str, build_webui_views.TaskSpec]:
    args = build_webui_views.parse_args(list(argv))
    return {task.name: task for task in build_webui_views.build_tasks(args)}


def spec(name: str, after: tuple[str, ...] = (), seconds: float = 0.0) -> build_webui_views.TaskSpec:
    """A task whose single command is a python sleep, for scheduler tests."""
    return build_webui_views.TaskSpec(
        name,
        (build_webui_views.CommandSpec(("python", "-c", f"pass  # {seconds}")),),
        after=after,
    )


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

    def test_default_plan_declares_every_producer_edge(self) -> None:
        tasks = graph()

        self.assertEqual(
            {name: task.after for name, task in tasks.items()},
            {
                "map_recovery": (),
                "gameplay": (),
                "projectiles": (),
                "characters": (),
                "gameplay_asset_refs": ("gameplay",),
                "map_streaming_instances": ("map_recovery",),
                "map_recovery_preview": ("map_streaming_instances",),
                "source_graph": ("gameplay",),
                "gameplay_asset_refs_after_graph": (
                    "source_graph",
                    "gameplay_asset_refs",
                ),
                "combat_relationships": ("source_graph",),
            },
        )
        self.assertNotIn("audio", tasks)
        self.assertNotIn("assets", tasks)
        phases = build_webui_views.build_phases(build_webui_views.parse_args([]))
        self.assertIn("--relevant-asset-maps", commands_for(phases, "source_graph")[0])
        for task_name in ("map_recovery", "characters", "gameplay", "projectiles"):
            self.assertEqual(commands_for(phases, task_name)[-1][1], "-m")

    def test_asset_plan_binds_asset_index_consumers_to_the_assets_task(self) -> None:
        tasks = graph("--with-assets", "--asset-mode", "debug", "--decode-audio")

        self.assertEqual(tasks["assets"].after, ())
        # build_character_data, the gameplay asset sidecar, the map preview and
        # the source graph all read webui/data/assets/index.json.
        for name in (
            "characters",
            "gameplay_asset_refs",
            "map_recovery_preview",
            "source_graph",
        ):
            self.assertIn("assets", tasks[name].after, name)
        # build_audio reads the gameplay index, projectiles.json and the
        # streaming-instance sidecars, but no asset index.
        self.assertEqual(
            tasks["audio"].after,
            ("gameplay", "projectiles", "map_streaming_instances"),
        )
        self.assertNotIn("assets", tasks["audio"].after)

    def test_audio_waits_for_the_streaming_sidecars_it_reads(self) -> None:
        # build_audio.py:14851 -> build_audio_semantics.py:13206 ->
        # scene_backgrounds.collect_scene_background_semantics globs
        # export_full/recovered/AnimeStudio-cli/*/map_streaming_instances.
        # Running audio beside the extractor that rewrites that directory
        # (as the old barrier phase did) reads a half-written catalog.
        from scripts.audio_semantics import scene_backgrounds

        source = inspect.getsource(scene_backgrounds._streaming_instance_paths)
        self.assertIn("map_streaming_instances", source)

        tasks = graph("--with-assets", "--decode-audio")
        self.assertIn("map_streaming_instances", tasks["audio"].after)
        depths = build_webui_views.dependency_depths(list(tasks.values()))
        self.assertGreater(depths["audio"], depths["map_streaming_instances"])

        phases = build_webui_views.build_phases(
            build_webui_views.parse_args(
                ["--with-assets", "--asset-mode", "debug", "--decode-audio"]
            )
        )
        asset_command = commands_for(phases, "assets")[0]
        self.assertNotIn("--skip-gameplay-refs", asset_command)
        self.assertEqual(asset_command[asset_command.index("--mode") + 1], "debug")
        self.assertNotIn("--skip-decode", commands_for(phases, "audio")[0])

    def test_audio_and_the_map_preview_never_gate_the_source_graph(self) -> None:
        # The 2026-09-07 barrier plan made the graph wait for the audio builder
        # and the map preview even though it reads neither.
        tasks = graph("--with-assets", "--decode-audio")
        depths = build_webui_views.dependency_depths(list(tasks.values()))

        for blocker in ("audio", "map_recovery_preview", "map_streaming_instances"):
            self.assertNotIn(blocker, tasks["source_graph"].after)
            self.assertNotIn(blocker, tasks["combat_relationships"].after)
            self.assertNotIn(blocker, tasks["gameplay_asset_refs_after_graph"].after)
        # The graph chain is shorter than the audio chain, so it cannot be the
        # thing that finishes last.
        self.assertLess(depths["source_graph"], depths["map_recovery_preview"])

    def test_gameplay_base_is_followed_by_recovery_audit_in_same_task(self) -> None:
        gameplay_task = graph()["gameplay"]
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
        tasks = graph()
        after_graph = tasks["gameplay_asset_refs_after_graph"]
        self.assertIn("source_graph", after_graph.after)
        # Both runs publish webui/data/assets/gameplay_refs.json, so the second
        # must follow the first instead of racing it.
        self.assertIn("gameplay_asset_refs", after_graph.after)

        for name in ("gameplay_asset_refs", "gameplay_asset_refs_after_graph"):
            task = tasks[name]
            self.assertEqual(len(task.commands), 1)
            command = task.commands[0].argv
            self.assertEqual(command[command.index("--stage") + 1], "asset-refs")

        gameplay_commands = [
            command.argv for command in tasks["gameplay"].commands
        ]
        self.assertEqual(
            [command[command.index("--stage") + 1] for command in gameplay_commands],
            ["base"],
        )
        self.assertEqual(gameplay_commands[0].count("--stage"), 2)

    def test_preview_follows_streaming_instances_without_rebuilding_map_data(self) -> None:
        tasks = graph()

        map_command = tasks["map_recovery"].commands[0].argv
        self.assertIn("scripts.build_map_recovery_data", map_command)
        self.assertNotIn("--preview-only", map_command)

        streaming = tasks["map_streaming_instances"]
        self.assertEqual(streaming.after, ("map_recovery",))
        self.assertIn("recover_map_streaming_instances.py", streaming.commands[0].argv[1])
        self.assertIn("--all-published-map-scenes", streaming.commands[0].argv)

        preview = tasks["map_recovery_preview"]
        self.assertEqual(preview.after, ("map_streaming_instances",))
        preview_command = preview.commands[0].argv
        self.assertIn("--preview-only", preview_command)
        self.assertEqual(preview_command[preview_command.index("--jobs") + 1], "4")

    def test_map_build_uses_worker_budget_with_and_without_assets(self) -> None:
        for argv in (["--jobs", "3"], ["--jobs", "3", "--with-assets"]):
            tasks = graph(*argv)
            for name in ("map_recovery", "map_streaming_instances", "map_recovery_preview"):
                command = tasks[name].commands[0].argv
                self.assertEqual(command[command.index("--jobs") + 1], "3", name)

    def test_full_graph_omits_relevant_scope_filters(self) -> None:
        graph_command = graph("--full-source-graph")["source_graph"].commands[0].argv

        self.assertNotIn("--relevant-asset-maps", graph_command)
        self.assertNotIn("--skip-reference-rows", graph_command)

    def test_graph_is_validated_at_plan_time(self) -> None:
        with self.assertRaises(ValueError):
            build_webui_views.validate_tasks([spec("a", ("missing",))])
        with self.assertRaises(ValueError):
            build_webui_views.validate_tasks([spec("a"), spec("a")])
        with self.assertRaises(ValueError):
            build_webui_views.validate_tasks([spec("a", ("b",)), spec("b", ("a",))])

    def test_phases_group_by_dependency_depth(self) -> None:
        phases = build_webui_views.build_phases(
            build_webui_views.parse_args(["--with-assets"])
        )
        names = {
            name: index
            for index, (_, tasks) in enumerate(phases)
            for task in tasks
            for name in (task.name,)
        }
        self.assertEqual([name for name, _ in phases][0], "depth0")
        self.assertEqual(names["assets"], 0)
        self.assertEqual(names["gameplay"], 0)
        self.assertEqual(names["map_recovery"], 0)
        self.assertLess(names["source_graph"], names["combat_relationships"])
        self.assertLess(names["map_streaming_instances"], names["map_recovery_preview"])

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
        tasks = graph()
        self.assertNotIn("mission_pipeline", tasks)
        self.assertIn(
            "--preview-only",
            tasks["map_recovery_preview"].commands[0].argv,
        )

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
        self.assertEqual(len(extraction_lines), 4)
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

    def test_export_wrapper_has_opt_in_freshness_bypass(self) -> None:
        source = (ROOT / "export.bat").read_text(encoding="utf-8")
        self.assertIn('if /I "%~1"=="--skip-freshness" goto :opt_skip_freshness', source)
        self.assertIn('set "SKIP_FRESHNESS=1"', source)
        self.assertIn("Freshness check skipped by --skip-freshness.", source)
        self.assertIn('if "%SKIP_FRESHNESS%"=="1" (', source)

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
                for task in build_webui_views.build_tasks(args)
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

    def test_dry_run_prints_every_task_with_its_dependencies(self) -> None:
        from io import StringIO

        buffer = StringIO()
        with mock.patch("sys.stdout", buffer):
            self.assertEqual(build_webui_views.main(["--dry-run", "--with-assets"]), 0)
        printed = buffer.getvalue()
        for name in graph("--with-assets"):
            self.assertIn(name, printed)
        self.assertIn("(after: map_streaming_instances", printed)
        self.assertIn("[depth0]", printed)


class WebuiViewSchedulerTests(unittest.TestCase):
    def run_graph(self, tasks, failures=(), jobs=4):
        """Run `run_graph` with run_task replaced by a deterministic stub."""
        order: list[str] = []
        failed = set(failures)

        def fake_run_task(task: build_webui_views.TaskSpec) -> dict:
            order.append(task.name)
            returncode = 3 if task.name in failed else 0
            return {
                "name": task.name,
                "returnCode": returncode,
                "seconds": 0.01,
                "commands": [],
            }

        with mock.patch.object(build_webui_views, "run_task", fake_run_task):
            returncode, runs = build_webui_views.run_graph(tasks, jobs)
        return returncode, {run.spec.name: run for run in runs}, order

    def test_dependencies_run_before_their_dependents(self) -> None:
        tasks = [
            spec("a"),
            spec("b", ("a",)),
            spec("c", ("b",)),
            spec("d"),
        ]
        returncode, runs, order = self.run_graph(tasks)
        self.assertEqual(returncode, 0)
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("b"), order.index("c"))
        self.assertEqual({run.status for run in runs.values()}, {"ok"})

    def test_a_failed_task_skips_its_dependents_and_fails_the_run(self) -> None:
        tasks = [
            spec("a"),
            spec("b", ("a",)),
            spec("c", ("b",)),
            spec("independent"),
        ]
        returncode, runs, order = self.run_graph(tasks, failures={"a"})
        self.assertEqual(returncode, 3)
        self.assertEqual(runs["a"].status, "failed")
        self.assertEqual(runs["b"].status, "skipped")
        self.assertEqual(runs["c"].status, "skipped")
        # A task that does not read the failed output still runs.
        self.assertEqual(runs["independent"].status, "ok")
        self.assertNotIn("b", order)
        self.assertNotIn("c", order)

    def test_job_budget_is_respected(self) -> None:
        import threading

        tasks = [spec(f"t{index}") for index in range(6)]
        peak = 0
        live = 0
        lock = threading.Lock()
        barrier = threading.Event()

        def fake_run_task(task: build_webui_views.TaskSpec) -> dict:
            nonlocal peak, live
            with lock:
                live += 1
                peak = max(peak, live)
            barrier.wait(0.05)
            with lock:
                live -= 1
            return {"name": task.name, "returnCode": 0, "seconds": 0.0, "commands": []}

        with mock.patch.object(build_webui_views, "run_task", fake_run_task):
            returncode, _ = build_webui_views.run_graph(tasks, 2)
        self.assertEqual(returncode, 0)
        self.assertLessEqual(peak, 2)

    def test_report_groups_tasks_by_depth_and_keeps_per_task_seconds(self) -> None:
        tasks = [spec("a"), spec("b", ("a",)), spec("c", ("b",))]
        _, runs, _ = self.run_graph(tasks)
        phases = build_webui_views.phase_payloads(
            [runs["a"], runs["b"], runs["c"]]
        )
        self.assertEqual([phase["name"] for phase in phases], ["depth0", "depth1", "depth2"])
        self.assertEqual(
            [[task["name"] for task in phase["tasks"]] for phase in phases],
            [["a"], ["b"], ["c"]],
        )
        for phase in phases:
            for task in phase["tasks"]:
                self.assertIn("seconds", task)
                self.assertIn("after", task)

    def test_skipped_tasks_are_reported_without_a_bogus_return_code(self) -> None:
        tasks = [spec("a"), spec("b", ("a",))]
        _, runs, _ = self.run_graph(tasks, failures={"a"})
        payload = build_webui_views.task_payload(runs["b"])
        self.assertEqual(payload["status"], "skipped")
        self.assertIsNone(payload["returnCode"])
        self.assertEqual(payload["after"], ["a"])


if __name__ == "__main__":
    unittest.main()
