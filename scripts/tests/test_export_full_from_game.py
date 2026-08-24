from __future__ import annotations

import unittest
import tempfile
import gzip
import hashlib
import inspect
import json
from pathlib import Path
from unittest import mock

from scripts import export_full_from_game
from scripts.export_full_from_game import (
    ANIMESTUDIO_STORY_JSON_TYPES,
    CommandResult,
    animestudio_object_index_export_is_relevant,
    animestudio_object_index_dir,
    animestudio_object_index_is_enabled,
    animestudio_object_index_part_path,
    animestudio_object_index_plan_is_relevant,
    animestudio_stage_options_for_scope,
    build_animestudio_object_index_cli_provenance,
    build_animestudio_stage_signature,
    collect_source_sizes,
    expected_missing_output_log_indexes,
    invalidate_animestudio_object_index_commit_marker,
    load_animestudio_object_index_summary,
    merge_animestudio_object_index_for_source,
    record_matches_expected_missing_output_log,
    parse_world_scene_chunks,
    run_animestudio_stage,
    should_merge_animestudio_type_jobs,
    stable_hash,
    structured_freshness_source_sizes,
    structured_dump_steps_for_source,
    structured_dump_steps_with_world_scenes,
    world_scene_chunk_file_regex,
)


class StructuredFreshnessProvenanceTests(unittest.TestCase):
    def test_final_export_summary_uses_structured_freshness_provenance(self) -> None:
        source = inspect.getsource(export_full_from_game.main)
        calculation = "structured_source_sizes = structured_freshness_source_sizes("
        publication = '"source_sizes": structured_source_sizes'
        self.assertEqual(source.count(calculation), 1)
        self.assertLess(source.index(calculation), source.index(publication))

    def test_full_export_publishes_current_source_sizes(self) -> None:
        current = {"StreamingAssets": {"fingerprint": "current"}}
        self.assertIs(
            structured_freshness_source_sizes(
                skip_structured=False,
                selected_sources=("StreamingAssets",),
                current_source_sizes=current,
                previous_summary={},
            ),
            current,
        )

    def test_asset_only_export_preserves_structured_source_sizes(self) -> None:
        previous = {"StreamingAssets": {"fingerprint": "structured-old"}}
        result = structured_freshness_source_sizes(
            skip_structured=True,
            selected_sources=("StreamingAssets",),
            current_source_sizes={"StreamingAssets": {"fingerprint": "asset-current"}},
            previous_summary={"source_sizes": previous},
        )
        self.assertEqual(result, previous)

    def test_asset_only_export_without_prior_provenance_fails_closed(self) -> None:
        result = structured_freshness_source_sizes(
            skip_structured=True,
            selected_sources=("StreamingAssets", "Persistent"),
            current_source_sizes={},
            previous_summary={},
        )
        self.assertEqual(result, {"StreamingAssets": {}, "Persistent": {}})


def object_index_cli_provenance() -> dict:
    assemblies = [
        {"name": name, "bytes": index + 10, "sha256": str(index + 1) * 64}
        for index, name in enumerate(
            ("AnimeStudio.CLI.dll", "AnimeStudio.dll", "AnimeStudio.Utility.dll")
        )
    ]
    provenance = {
        "entrypoint": {
            "name": "AnimeStudio.CLI.exe",
            "bytes": 9,
            "sha256": "a" * 64,
        },
        "implementationAssemblies": assemblies,
    }
    provenance["fingerprint"] = stable_hash(provenance)
    return provenance


def object_index_source_fingerprint(fingerprint: str = "b" * 64) -> dict:
    return {"files": 3, "bytes": 40, "fingerprint": fingerprint}


def object_index_stage_signature(
    source: str = "StreamingAssets",
    *,
    cli: dict | None = None,
    source_fingerprint: dict | None = None,
) -> dict:
    payload = {
        "source": source,
        "part_schema_version": 1,
        "merge_contract": "endfield-animestudio-object-index-merge-v1",
        "identity": "serialized-file-source-offset-pathid-v1",
        "external_resolution": "unique-expected-cab-pathid-v1",
        "scalar_policy": "identifier-and-state-v1",
        "cli": cli or object_index_cli_provenance(),
        "source_fingerprint": source_fingerprint or object_index_source_fingerprint(),
        "commands": ["worker"],
        "items": [],
    }
    return {"sha256": stable_hash(payload), "payload": payload}


class ExpectedMissingOutputLogTests(unittest.TestCase):
    def test_shared_log_matcher_prefers_exact_source_then_fallback(self) -> None:
        exact, fallback = expected_missing_output_log_indexes(
            {
                "records": [
                    {
                        "reason": "expected",
                        "PathID": "0x10",
                        "SourceOffset": "32",
                        "SourceFile": "folder/source.ab",
                    },
                    {
                        "reason": "expected",
                        "PathID": 17,
                        "SourceOffset": 33,
                    },
                    {"reason": "unexpected", "PathID": 18, "SourceOffset": 34},
                ],
            },
            record_key="records",
            sample_key="samples",
            allowed_reasons=frozenset({"expected"}),
        )

        self.assertEqual(exact, {(16, 32, "source.ab")})
        self.assertEqual(fallback, {(17, 33)})
        self.assertTrue(record_matches_expected_missing_output_log(
            {"entry": {"PathID": 16, "Offset": 32, "Source": "SOURCE.AB"}},
            exact,
            fallback,
        ))
        self.assertTrue(record_matches_expected_missing_output_log(
            {"entry": {"PathID": 17, "Offset": 33}},
            exact,
            fallback,
        ))
        self.assertFalse(record_matches_expected_missing_output_log(
            {"entry": {"PathID": 16, "Offset": 32, "Source": "other.ab"}},
            exact,
            fallback,
        ))


class SourceFreshnessFingerprintTests(unittest.TestCase):
    def test_persistent_runtime_only_roots_do_not_stale_export(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            persistent = root / "Persistent"
            vfs_file = persistent / "VFS" / "ABCD" / "payload.chk"
            vfs_file.parent.mkdir(parents=True)
            vfs_file.write_bytes(b"source")
            for relative in (
                "HGDownload/download_sdk_config",
                "Logs/client.log",
                "Temp/session.tmp",
            ):
                path = persistent / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"runtime-only")

            summary = collect_source_sizes(root, ("Persistent",))["Persistent"]

            self.assertEqual(summary["files"], 1)
            self.assertEqual(summary["bytes"], len(b"source"))


class AnimeStudioStageOptionsTests(unittest.TestCase):
    def test_story_json_is_not_asset_map_filtered(self) -> None:
        options = animestudio_stage_options_for_scope("story")

        self.assertEqual(options["json_by_type"]["types"], ANIMESTUDIO_STORY_JSON_TYPES)
        self.assertFalse(options["json_by_type"]["asset_map_filter"])

    def test_combined_json_keeps_story_sources_outside_asset_map(self) -> None:
        options = animestudio_stage_options_for_scope("all", "default")

        for type_spec in ANIMESTUDIO_STORY_JSON_TYPES:
            self.assertIn(type_spec, options["json_by_type"]["types"])
        self.assertFalse(options["json_by_type"]["asset_map_filter"])

    def test_asset_only_json_can_use_asset_map(self) -> None:
        options = animestudio_stage_options_for_scope("assets", "default")

        self.assertTrue(options["json_by_type"]["asset_map_filter"])

    def test_auto_does_not_merge_broad_story_json(self) -> None:
        items = [{"item_name": name} for name in ("TextAsset", "MonoBehaviour", "PlayableDirector")]

        self.assertFalse(should_merge_animestudio_type_jobs("json_by_type", items, "auto"))
        self.assertTrue(
            should_merge_animestudio_type_jobs(
                "json_by_type",
                items,
                "auto",
                asset_map_filter=True,
            )
        )
        self.assertTrue(should_merge_animestudio_type_jobs("json_by_type", items, "merged"))


class JsonMapFilterTests(unittest.TestCase):
    """json_by_type may load through the asset map only for types the map
    enumerates completely; anything else must still see every bundle."""

    BASE = {"export_type": "JSON", "asset_map_filter": False, "json_map_filter_map": "a.map"}

    def applies(self, types, **overrides):
        options = dict(self.BASE)
        options.update(overrides)
        return export_full_from_game.animestudio_json_map_filter_applies(
            "json_by_type", options, tuple(types)
        )

    def test_fully_covered_types_are_filtered(self) -> None:
        for name in sorted(export_full_from_game.ANIMESTUDIO_JSON_MAP_FILTER_TYPES):
            self.assertTrue(self.applies([name]), name)

    def test_types_needing_other_bundles_stay_broad(self) -> None:
        # PlayableDirector has no map entries at all, so a filtered load emits
        # nothing. MonoBehaviour has full map coverage but resolves its class
        # name and external PPtrs out of bundles a filtered load never opens,
        # which silently renames 73% of its output and drops reference targets.
        for name in ("PlayableDirector", "MonoBehaviour", "Material"):
            self.assertNotIn(name, export_full_from_game.ANIMESTUDIO_JSON_MAP_FILTER_TYPES)
            self.assertFalse(self.applies([name]), name)

    def test_merged_job_with_any_uncovered_type_stays_broad(self) -> None:
        self.assertFalse(self.applies(["TextAsset", "PlayableDirector"]))
        self.assertFalse(self.applies(["TextAsset", "MonoBehaviour"]))

    def test_requires_a_map(self) -> None:
        self.assertFalse(self.applies(["TextAsset"], json_map_filter_map=None))

    def test_does_not_double_up_on_a_map_filtered_stage(self) -> None:
        self.assertFalse(self.applies(["TextAsset"], asset_map_filter=True))

    def test_other_stages_are_untouched(self) -> None:
        self.assertFalse(
            export_full_from_game.animestudio_json_map_filter_applies(
                "convert_by_type", dict(self.BASE), ("Material",)
            )
        )

    def test_signature_records_the_decision(self) -> None:
        covered = build_animestudio_stage_signature("json_by_type", dict(self.BASE), "TextAsset")
        broad = build_animestudio_stage_signature("json_by_type", dict(self.BASE), "PlayableDirector")
        self.assertTrue(covered["json_map_filter"])
        self.assertFalse(broad["json_map_filter"])
        self.assertNotEqual(covered, broad)


class JsonMapFilterWiringTests(unittest.TestCase):
    """The stage runner must hand map arguments to covered types only."""

    def _map_args_by_type(self, type_names) -> dict:
        plan = {
            "options": {
                "export_type": "JSON",
                "asset_map_filter": False,
                "json_map_filter_map": "endfield_streamingassets_assets.map",
            },
            "items": [{"item_name": n, "type_spec": n} for n in type_names],
            "run_items": list(type_names),
        }
        seen = {}

        def fake_run(tasks, jobs, call_pool=None):
            for task in tasks:
                kwargs = task["kwargs"]
                seen[task["item_name"]] = (
                    kwargs.get("map_op"), kwargs.get("map_name"))
                task["result"] = CommandResult(
                    name="t", argv=[], cwd=".", returncode=0,
                    duration_seconds=0.0, stdout_log="o", stderr_log="e")

        with mock.patch.object(
            export_full_from_game, "run_animestudio_call_tasks", side_effect=fake_run
        ), mock.patch.object(
            export_full_from_game, "clear_animestudio_stage_outputs"
        ), mock.patch.object(
            export_full_from_game, "write_animestudio_parallel_log_index",
            return_value=("out.log", "err.log"),
        ):
            export_full_from_game.run_animestudio_stage_plan(
                source="StreamingAssets", input_root=Path("in"), output_root=Path("out"),
                reports_dir=Path("reports"), animestudio_exe=Path("cli"),
                animestudio_dummy_dlls=None, stage="json_by_type", plan=plan,
                jobs=8, type_job_mode="auto",
            )
        return seen

    def test_only_covered_types_get_the_map(self) -> None:
        seen = self._map_args_by_type(
            ["TextAsset", "MonoBehaviour", "Material", "PlayableDirector"])
        self.assertEqual(seen["TextAsset"][0], "AssetMap,Load")
        self.assertTrue(seen["TextAsset"][1].endswith(".map"))
        # Every type that needs bundles outside its own must still load broadly.
        for broad in ("MonoBehaviour", "Material", "PlayableDirector"):
            self.assertIsNone(seen[broad][0], broad)
            self.assertIsNone(seen[broad][1], broad)


class BroadJsonBatchingTests(unittest.TestCase):
    """The broad json_by_type types cannot shard and cannot merge, so the only
    lever is how many of their multi-GiB loads are resident at once."""

    STAGE_KWARGS = dict(
        source="StreamingAssets",
        input_root=Path("in"),
        output_root=Path("out"),
        reports_dir=Path("reports"),
        animestudio_exe=Path("AnimeStudio.CLI"),
        animestudio_dummy_dlls=None,
        stage="json_by_type",
        jobs=8,
    )

    def _plan(self) -> dict:
        names = ("TextAsset", "MonoBehaviour", "PlayableDirector", "Material")
        return {
            "options": {"export_type": "JSON", "asset_map_filter": False},
            "items": [
                {"item_name": name, "type_spec": name} for name in names
            ],
            "run_items": list(names),
        }

    def _batches(self, broad_json_jobs: int) -> list[int]:
        """Record how many tasks each dispatch call submitted together."""
        seen: list[int] = []

        def fake_run(tasks, jobs, call_pool=None):
            seen.append(len(tasks))
            for task in tasks:
                task["result"] = CommandResult(
                    name=task["kwargs"].get("command_name") or "type",
                    argv=[],
                    cwd=".",
                    returncode=0,
                    duration_seconds=0.0,
                    stdout_log="out.log",
                    stderr_log="err.log",
                )

        with mock.patch.object(
            export_full_from_game, "run_animestudio_call_tasks", side_effect=fake_run
        ), mock.patch.object(
            export_full_from_game, "clear_animestudio_stage_outputs"
        ), mock.patch.object(
            export_full_from_game,
            "write_animestudio_parallel_log_index",
            return_value=("out.log", "err.log"),
        ):
            export_full_from_game.run_animestudio_stage_plan(
                plan=self._plan(),
                type_job_mode="auto",
                broad_json_jobs=broad_json_jobs,
                **self.STAGE_KWARGS,
            )
        return seen

    def test_default_keeps_one_broad_load_resident(self) -> None:
        self.assertEqual(self._batches(1), [1, 1, 1, 1])

    def test_batch_of_two_halves_the_broad_tail(self) -> None:
        self.assertEqual(self._batches(2), [2, 2])

    def test_batch_is_capped_by_the_task_count(self) -> None:
        self.assertEqual(self._batches(99), [4])

    def test_non_positive_batch_falls_back_to_sequential(self) -> None:
        self.assertEqual(self._batches(0), [1, 1, 1, 1])


class AnimeStudioObjectIndexTests(unittest.TestCase):
    def test_effective_gating_excludes_asset_only_and_skipped_runs(self) -> None:
        self.assertTrue(
            animestudio_object_index_is_enabled(True, "story", False)
        )
        self.assertTrue(
            animestudio_object_index_is_enabled(True, "all", False)
        )
        self.assertFalse(
            animestudio_object_index_is_enabled(True, "assets", False)
        )
        self.assertFalse(
            animestudio_object_index_is_enabled(True, "story", True)
        )

    def test_cli_provenance_hashes_managed_implementation_assemblies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entrypoint = root / "AnimeStudio.CLI.exe"
            entrypoint.write_bytes(b"apphost")
            for name, payload in (
                ("AnimeStudio.CLI.dll", b"cli"),
                ("AnimeStudio.dll", b"core"),
                ("AnimeStudio.Utility.dll", b"utility"),
            ):
                (root / name).write_bytes(payload)

            provenance = build_animestudio_object_index_cli_provenance(entrypoint)

            assemblies = {
                item["name"]: item
                for item in provenance["implementationAssemblies"]
            }
            self.assertEqual(
                assemblies["AnimeStudio.CLI.dll"]["sha256"],
                hashlib.sha256(b"cli").hexdigest(),
            )
            self.assertEqual(
                assemblies["AnimeStudio.dll"]["sha256"],
                hashlib.sha256(b"core").hexdigest(),
            )
            original_fingerprint = provenance["fingerprint"]
            (root / "AnimeStudio.dll").write_bytes(b"changed core")
            self.assertNotEqual(
                build_animestudio_object_index_cli_provenance(entrypoint)["fingerprint"],
                original_fingerprint,
            )

    def test_only_original_data_carrier_json_types_are_relevant(self) -> None:
        self.assertTrue(
            animestudio_object_index_export_is_relevant(
                "json_by_type", "JSON", ("MonoBehaviour:Both",)
            )
        )
        self.assertTrue(
            animestudio_object_index_export_is_relevant(
                "json_by_type", "JSON", ("PlayableDirector:Both",)
            )
        )
        self.assertFalse(
            animestudio_object_index_export_is_relevant(
                "json_by_type", "JSON", ("TextAsset:Both",)
            )
        )
        self.assertFalse(
            animestudio_object_index_export_is_relevant(
                "convert_by_type", "Convert", ("MonoBehaviour:Both",)
            )
        )

    def test_signature_records_the_exact_index_contract(self) -> None:
        options = {
            "export_type": "JSON",
            "object_index_enabled": True,
            "mono_behaviour_type_tree_priority": "SerializedFirst",
        }

        signature = build_animestudio_stage_signature(
            "json_by_type", options, "MonoBehaviour:Both"
        )

        self.assertTrue(signature["object_index"]["enabled"])
        self.assertEqual(signature["object_index"]["part_schema_version"], 1)
        self.assertNotIn(
            "object_index",
            build_animestudio_stage_signature(
                "json_by_type", options, "TextAsset:Both"
            ),
        )

    def test_plan_relevance_requires_a_selected_carrier(self) -> None:
        plan = {
            "json_by_type": {
                "selected_items": ["MonoBehaviour"],
                "items": [
                    {
                        "item_name": "MonoBehaviour",
                        "type_spec": "MonoBehaviour:Both",
                    },
                    {"item_name": "TextAsset", "type_spec": "TextAsset:Both"},
                ],
            }
        }

        self.assertTrue(animestudio_object_index_plan_is_relevant(plan))
        plan["json_by_type"]["selected_items"] = ["TextAsset"]
        self.assertFalse(animestudio_object_index_plan_is_relevant(plan))

    def test_published_summary_is_hash_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = animestudio_object_index_dir(root, "StreamingAssets")
            output_dir.mkdir(parents=True)
            outputs = {}
            for key, filename in (
                ("objects", "objects.jsonl.gz"),
                ("schemas", "schemas.jsonl.gz"),
            ):
                path = output_dir / filename
                with gzip.open(path, "wt", encoding="utf-8") as stream:
                    stream.write("{}\n")
                outputs[key] = {
                    "path": filename,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            (output_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "mergeContract": "endfield-animestudio-object-index-merge-v1",
                        "complete": True,
                        "stageSignature": object_index_stage_signature(),
                        "outputs": outputs,
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                load_animestudio_object_index_summary(
                    root,
                    "StreamingAssets",
                    expected_cli_provenance=object_index_cli_provenance(),
                    expected_source_fingerprint=object_index_source_fingerprint(),
                )["complete"]
            )
            (output_dir / "objects.jsonl.gz").write_bytes(b"tampered")
            invalid = load_animestudio_object_index_summary(
                root, "StreamingAssets"
            )
            self.assertFalse(invalid["complete"])
            self.assertIn("hash does not match", invalid["errors"][0])

    def test_published_summary_requires_signed_current_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = animestudio_object_index_dir(root, "StreamingAssets")
            output_dir.mkdir(parents=True)
            outputs = {}
            for key, filename in (
                ("objects", "objects.jsonl.gz"),
                ("schemas", "schemas.jsonl.gz"),
            ):
                path = output_dir / filename
                path.write_bytes(key.encode("ascii"))
                outputs[key] = {
                    "path": filename,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            summary_path = output_dir / "summary.json"
            summary = {
                "schemaVersion": 1,
                "mergeContract": "endfield-animestudio-object-index-merge-v1",
                "complete": True,
                "outputs": outputs,
            }
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            legacy = load_animestudio_object_index_summary(root, "StreamingAssets")
            self.assertFalse(legacy["complete"])
            self.assertIn("no stage signature", legacy["errors"][0])

            signature = object_index_stage_signature()
            signature["payload"]["source"] = "Persistent"
            summary["stageSignature"] = signature
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            bad_signature = load_animestudio_object_index_summary(
                root, "StreamingAssets"
            )
            self.assertFalse(bad_signature["complete"])
            self.assertIn("signature hash does not match", bad_signature["errors"][0])

            summary["stageSignature"] = object_index_stage_signature()
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            stale_source = load_animestudio_object_index_summary(
                root,
                "StreamingAssets",
                expected_source_fingerprint=object_index_source_fingerprint("c" * 64),
            )
            self.assertFalse(stale_source["complete"])
            self.assertIn("different source fingerprint", stale_source["errors"][0])

            current_cli = object_index_cli_provenance()
            current_cli["entrypoint"]["bytes"] += 1
            current_cli["fingerprint"] = stable_hash(
                {
                    key: value
                    for key, value in current_cli.items()
                    if key != "fingerprint"
                }
            )
            stale_cli = load_animestudio_object_index_summary(
                root,
                "StreamingAssets",
                expected_cli_provenance=current_cli,
            )
            self.assertFalse(stale_cli["complete"])
            self.assertIn("different CLI provenance", stale_cli["errors"][0])

    def test_commit_marker_invalidation_applies_before_any_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = animestudio_object_index_dir(root, "StreamingAssets")
            output_dir.mkdir(parents=True)
            for name in ("summary.json", "summary.json.tmp"):
                (output_dir / name).write_text("stale", encoding="utf-8")

            invalidate_animestudio_object_index_commit_marker(
                root, "StreamingAssets"
            )

            self.assertFalse((output_dir / "summary.json").exists())
            self.assertFalse((output_dir / "summary.json.tmp").exists())

    def test_part_collision_invalidates_the_commit_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = animestudio_object_index_dir(root, "StreamingAssets")
            output_dir.mkdir(parents=True)
            (output_dir / "summary.json").write_text("{}", encoding="utf-8")
            part = output_dir / "parts" / "collision.jsonl"
            results = [
                CommandResult(
                    name=name,
                    argv=[],
                    cwd=str(root),
                    returncode=0,
                    duration_seconds=0.0,
                    stdout_log="",
                    stderr_log="",
                    object_index_jsonl=str(part),
                )
                for name in ("worker_a", "worker_b")
            ]
            stage_plans = {
                "json_by_type": {
                    "command_results": results,
                    "items": [],
                }
            }

            summary, error = merge_animestudio_object_index_for_source(
                root,
                "StreamingAssets",
                stage_plans,
                {"name": "AnimeStudio.CLI.exe", "sha256": "test"},
                {"files": 1, "bytes": 2, "fingerprint": "source"},
            )

            self.assertIsNotNone(error)
            self.assertFalse(summary["complete"])
            self.assertFalse((output_dir / "summary.json").exists())

    def test_worker_gets_a_unique_clean_part_without_changing_other_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command_name = "StreamingAssets_animestudio_json_by_type_MonoBehaviour"
            part = animestudio_object_index_part_path(
                root, "StreamingAssets", command_name
            )
            part.parent.mkdir(parents=True)
            part.write_text("stale", encoding="utf-8")
            part.with_name(part.name + ".tmp").write_text("stale", encoding="utf-8")
            captured: list[list[str]] = []

            def fake_run(
                name: str,
                argv: list[str],
                cwd: Path,
                reports_dir: Path,
                stream_output: bool = False,
            ) -> CommandResult:
                self.assertFalse(part.exists())
                self.assertFalse(part.with_name(part.name + ".tmp").exists())
                captured.append(argv)
                reports_dir.mkdir(parents=True, exist_ok=True)
                stdout = reports_dir / f"{name}.stdout.log"
                stderr = reports_dir / f"{name}.stderr.log"
                stdout.write_text("", encoding="utf-8")
                stderr.write_text("", encoding="utf-8")
                return CommandResult(
                    name=name,
                    argv=argv,
                    cwd=str(cwd),
                    returncode=0,
                    duration_seconds=0.0,
                    stdout_log=str(stdout),
                    stderr_log=str(stderr),
                )

            with mock.patch.object(
                export_full_from_game, "run_logged_command", side_effect=fake_run
            ):
                indexed = run_animestudio_stage(
                    source="StreamingAssets",
                    input_root=root / "input",
                    output_root=root,
                    reports_dir=root / "reports",
                    animestudio_exe=root / "AnimeStudio.CLI.exe",
                    animestudio_dummy_dlls=None,
                    mono_behaviour_type_tree_priority="SerializedFirst",
                    stage="json_by_type",
                    export_type="JSON",
                    types=("MonoBehaviour:Both",),
                    command_name=command_name,
                    object_index_enabled=True,
                )
                unindexed = run_animestudio_stage(
                    source="StreamingAssets",
                    input_root=root / "input",
                    output_root=root,
                    reports_dir=root / "reports",
                    animestudio_exe=root / "AnimeStudio.CLI.exe",
                    animestudio_dummy_dlls=None,
                    mono_behaviour_type_tree_priority="SerializedFirst",
                    stage="json_by_type",
                    export_type="JSON",
                    types=("TextAsset:Both",),
                    command_name="StreamingAssets_animestudio_json_by_type_TextAsset",
                    object_index_enabled=True,
                )

            self.assertEqual(indexed.object_index_jsonl, str(part))
            self.assertIn("--object_index_jsonl", captured[0])
            self.assertIsNone(unindexed.object_index_jsonl)
            self.assertNotIn("--object_index_jsonl", captured[1])


class WorldSceneChunkExportTests(unittest.TestCase):
    def test_parses_and_deduplicates_chunk_specs(self) -> None:
        chunks = parse_world_scene_chunks(["map02:2:-13", "MAP02:2:-13"])

        self.assertEqual(chunks, (("map02", 2, -13),))

    def test_rejects_invalid_chunk_spec(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected MAP:X:Z"):
            parse_world_scene_chunks(["map02_lv006"])

    def test_scene_regex_matches_init_and_streaming_payloads(self) -> None:
        pattern = world_scene_chunk_file_regex("map02", 2, -13)

        self.assertRegex(
            "Data/Streaming/PC/map02/Streaming/InitChunkData_2_-13_0_0.bytes",
            pattern,
        )
        self.assertRegex(
            "Data/Streaming/PC/map02/Streaming/StreamingChunkData_2_-13_0_0.bytes",
            pattern,
        )
        self.assertNotRegex(
            "Data/Streaming/PC/map02/Streaming/StreamingChunkData_2_-12_0_0.bytes",
            pattern,
        )

    def test_world_scene_step_only_runs_for_streaming_assets(self) -> None:
        steps = structured_dump_steps_with_world_scenes("webui", (("map02", 2, -13),))

        streaming_steps = structured_dump_steps_for_source(steps, "StreamingAssets")
        persistent_steps = structured_dump_steps_for_source(steps, "Persistent")
        self.assertEqual([step["name"] for step in streaming_steps], ["required", "world_scene_chunks"])
        self.assertEqual([step["name"] for step in persistent_steps], ["required"])


class StoryMonoBehaviourNameFilterTests(unittest.TestCase):
    """--names shrinks only what is written, so it must never reach a job that
    also carries a type whose consumers do not glob by name."""

    BASE = {"export_type": "JSON", "story_monobehaviour_names": "Track|Trunk"}

    def applies(self, types, stage="json_by_type", **overrides):
        options = dict(self.BASE)
        options.update(overrides)
        return export_full_from_game.animestudio_story_name_filter_applies(
            stage, options, tuple(types)
        )

    def test_monobehaviour_only_job_is_filtered(self) -> None:
        self.assertTrue(self.applies(["MonoBehaviour"]))
        self.assertTrue(self.applies(["MonoBehaviour:Both"]))

    def test_merged_job_keeps_every_other_type_complete(self) -> None:
        # --names applies to the whole CLI call, so a merged job would filter
        # TextAsset by a MonoBehaviour vocabulary and silently lose Story text.
        self.assertFalse(self.applies(["TextAsset", "MonoBehaviour"]))
        self.assertFalse(self.applies(["TextAsset"]))
        self.assertFalse(self.applies(["PlayableDirector", "MonoBehaviour"]))

    def test_off_unless_requested_for_this_stage(self) -> None:
        self.assertFalse(self.applies(["MonoBehaviour"], story_monobehaviour_names=None))
        self.assertFalse(self.applies(["MonoBehaviour"], stage="maps"))
        self.assertFalse(self.applies([]))

    def test_default_vocabulary_covers_the_story_globs(self) -> None:
        # Keep representative names from every Story/video discovery family.
        import re

        pattern = re.compile(
            export_full_from_game.ANIMESTUDIO_STORY_MONOBEHAVIOUR_NAME_FILTER,
            re.IGNORECASE,
        )
        for asset_name in (
            "Animation Track",
            "activation track (2)",
            "Trunk",
            "LeftSubtitlePlayableAsset",
            "DialogCenterTextPlayableAsset(Clone)",
            "BeyondFMVPlayableAsset",
            "AudioMusicPlayable",
            "dlg_sm2l5m2_3_npc_chr_0004_pelica_0",
            "f_cutscene_e11m7_1",
            "fm_cutscene_e0m0_11111_actor",
            "cs_video_e6m3_2",
            "SFX",
        ):
            self.assertRegex(asset_name, pattern)

    def test_effective_names_are_part_of_the_stage_signature(self) -> None:
        options = dict(self.BASE)
        signature = export_full_from_game.build_animestudio_stage_signature(
            "json_by_type", options, "MonoBehaviour:Both"
        )
        self.assertEqual(signature["names"], "Track|Trunk")

        text_signature = export_full_from_game.build_animestudio_stage_signature(
            "json_by_type", options, "TextAsset:Both"
        )
        self.assertIsNone(text_signature["names"])


if __name__ == "__main__":
    unittest.main()
