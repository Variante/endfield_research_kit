from __future__ import annotations

import unittest

from scripts import build_assets, build_webui_views


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
                ["combat_relationships"],
            ],
        )
        self.assertIn("--relevant-asset-maps", commands_for(phases, "source_graph")[0])
        self.assertNotIn("audio", [name for phase in task_names(phases) for name in phase])

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
        self.assertIn("--skip-gameplay-refs", asset_command)
        self.assertEqual(asset_command[asset_command.index("--mode") + 1], "default")
        self.assertNotIn("--skip-decode", commands_for(phases, "audio")[0])

    def test_mission_only_plan_has_no_unrelated_views(self) -> None:
        args = build_webui_views.parse_args(["--mission-pipeline-only"])
        phases = build_webui_views.build_phases(args)

        self.assertEqual(task_names(phases), [["mission_pipeline"]])

    def test_full_graph_omits_relevant_scope_filters(self) -> None:
        args = build_webui_views.parse_args(["--full-source-graph"])
        graph_command = commands_for(build_webui_views.build_phases(args), "source_graph")[0]

        self.assertNotIn("--relevant-asset-maps", graph_command)
        self.assertNotIn("--skip-reference-rows", graph_command)

    def test_asset_builder_can_defer_joined_gameplay_sidecar(self) -> None:
        args = build_assets.parse_args(["--skip-gameplay-refs"])

        self.assertTrue(args.skip_gameplay_refs)


if __name__ == "__main__":
    unittest.main()
