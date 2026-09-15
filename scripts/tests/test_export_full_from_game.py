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
    animestudio_managed_reference_diagnostics_export_is_relevant,
    animestudio_managed_reference_diagnostics_part_path,
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
    refresh_animestudio_plan_output_counts,
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


class AnimeStudioOutputCountTests(unittest.TestCase):
    def test_counts_all_selected_types_and_separates_marker_only_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            stage_root = (
                output_root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "convert_by_type"
            )
            animation_dir = stage_root / "AnimationClip"
            animator_dir = stage_root / "Animator"
            empty_dir = stage_root / "Texture2D"
            animation_dir.mkdir(parents=True)
            animator_dir.mkdir()
            empty_dir.mkdir()
            (animation_dir / "walk.anim").write_bytes(b"anim")
            (animation_dir / "run.anim").write_bytes(b"anim")
            (animation_dir / "nested").mkdir()
            (animation_dir / "nested" / "diagnostic.json").write_text("{}")
            (animator_dir / "empty.fbx.empty.json").write_text("{}")

            plan = {
                "items": [
                    {"type_spec": "AnimationClip:Both"},
                    {"type_spec": "Animator:Both"},
                    {"type_spec": "Texture2D:Both"},
                ]
            }
            refresh_animestudio_plan_output_counts(
                output_root, "StreamingAssets", "convert_by_type", plan
            )

            self.assertEqual(
                plan["item_file_counts"],
                {"AnimationClip": 2, "Animator": 1, "Texture2D": 0},
            )
            self.assertEqual(
                plan["item_marker_file_counts"],
                {"AnimationClip": 0, "Animator": 1, "Texture2D": 0},
            )

    def test_duplicate_type_specs_are_counted_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            type_dir = (
                output_root / "recovered" / "AnimeStudio-cli" / "Persistent"
                / "json_by_type" / "TextAsset"
            )
            type_dir.mkdir(parents=True)
            (type_dir / "a.json").write_text("{}")
            plan = {"items": [{"type_spec": "TextAsset:Both"}, {"type_spec": "TextAsset:Parse"}]}

            refresh_animestudio_plan_output_counts(
                output_root, "Persistent", "json_by_type", plan
            )

            self.assertEqual(plan["item_file_counts"], {"TextAsset": 1})


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

    def test_default_assets_publish_audio_animation_evidence(self) -> None:
        options = animestudio_stage_options_for_scope("assets", "default")

        self.assertIn("AnimationClip:Both", options["convert_by_type"]["types"])
        self.assertIn("AnimatorController:Both", options["json_by_type"]["types"])
        self.assertIn("AnimatorOverrideController:Both", options["json_by_type"]["types"])

    def test_audio_controller_json_requires_broad_dependency_loading(self) -> None:
        for type_name in ("AnimatorController:Both", "AnimatorOverrideController:Both"):
            self.assertFalse(export_full_from_game.animestudio_map_filter_is_safe((type_name,)))

        self.assertTrue(export_full_from_game.animestudio_map_filter_is_safe(("AnimationClip:Both",)))

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

    def test_managed_reference_diagnostics_are_atomic_and_monobehaviour_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command_name = "Persistent_animestudio_json_by_type_MonoBehaviour"
            part = animestudio_managed_reference_diagnostics_part_path(
                root, "Persistent", command_name
            )
            part.parent.mkdir(parents=True)
            part.write_text("stale", encoding="utf-8")
            part.with_name(part.name + ".tmp").write_text("stale", encoding="utf-8")
            captured: list[list[str]] = []

            def fake_run(name, argv, cwd, reports_dir, stream_output=False):
                self.assertFalse(part.exists())
                self.assertFalse(part.with_name(part.name + ".tmp").exists())
                captured.append(argv)
                return CommandResult(name, argv, str(cwd), 0, 0.0, "", "")

            with mock.patch.object(export_full_from_game, "run_logged_command", side_effect=fake_run):
                result = run_animestudio_stage(
                    source="Persistent",
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
                    managed_reference_diagnostics_enabled=True,
                    managed_reference_diagnostic_types=("AbilitySystemData$", "ProjectileComponentData$"),
                    managed_reference_diagnostics_include_exact_matches=True,
                )

            self.assertEqual(result.managed_reference_diagnostics_jsonl, str(part))
            self.assertIn("--managed_reference_diagnostics_jsonl", captured[0])
            self.assertIn("--managed_reference_diagnostics_include_exact_matches", captured[0])
            type_flag = captured[0].index("--managed_reference_diagnostic_types")
            self.assertEqual(
                captured[0][type_flag + 1 : type_flag + 3],
                ["AbilitySystemData$", "ProjectileComponentData$"],
            )
            self.assertTrue(
                animestudio_managed_reference_diagnostics_export_is_relevant(
                    "json_by_type", "JSON", ("MonoBehaviour:Both",)
                )
            )
            self.assertFalse(
                animestudio_managed_reference_diagnostics_export_is_relevant(
                    "json_by_type", "JSON", ("TextAsset:Both",)
                )
            )


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
        steps = structured_dump_steps_with_world_scenes("focused", (("map02", 2, -13),))

        streaming_steps = structured_dump_steps_for_source(steps, "StreamingAssets")
        persistent_steps = structured_dump_steps_for_source(steps, "Persistent")
        self.assertEqual([step["name"] for step in streaming_steps], ["required", "world_scene_chunks"])
        self.assertEqual([step["name"] for step in persistent_steps], ["required"])

    def test_default_structured_dump_adds_filtered_terrain_height_step(self) -> None:
        focused = structured_dump_steps_with_world_scenes("focused", ())
        default = structured_dump_steps_with_world_scenes("default", ())

        self.assertEqual(default[0], focused[0])
        self.assertEqual([step["name"] for step in default], ["required", "terrain_height"])
        self.assertEqual(default[1]["block_types"], ("terrain",))
        self.assertEqual(default[1]["sources"], ("StreamingAssets",))
        self.assertRegex("Data/Terrain/PC/map02/Terrain_6_16_32_H.bytes", default[1]["file_regexes"][0])
        self.assertNotRegex("Data/Terrain/PC/map02/Terrain_6_16_32_C.bytes", default[1]["file_regexes"][0])

    def test_rejects_unknown_structured_dump_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported structured dump mode"):
            structured_dump_steps_with_world_scenes("unknown", ())


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


def asset_cache_plan(**overrides) -> dict:
    plan = {
        "stage": "convert_by_type",
        "options": {"export_type": "Convert", "asset_cache_enabled": True},
        "cli_signature": {"fingerprint": "cli-1"},
        "dummy_dll_signature": {"dll_count": 2, "bytes": 10, "fingerprint": "dll-1"},
        "source_fingerprint": {"files": 3, "bytes": 30, "fingerprint": "src-1"},
    }
    plan.update(overrides)
    return plan


def asset_cache_item() -> dict:
    return {
        "type_spec": "Mesh:Both",
        "item_name": "Mesh",
        "stage_signature": export_full_from_game.build_animestudio_stage_signature(
            "convert_by_type", {"export_type": "Convert"}, "Mesh:Both"
        ),
    }


def asset_map_entry(**overrides) -> dict:
    entry = {
        "Name": "prop_rock",
        "Container": "assets/prop_rock.prefab",
        "Source": "level0.ab",
        "PathID": 1234,
        "Type": "Mesh",
        "Hash": "aaaaaaaaaaaaaaaa",
        "Offset": 0,
    }
    entry.update(overrides)
    return entry


class AnimeStudioAssetCacheKeyTests(unittest.TestCase):
    def key(self, *, entry=None, plan=None) -> str:
        return export_full_from_game.asset_entry_cache_key(
            entry if entry is not None else asset_map_entry(),
            asset_cache_item(),
            plan if plan is not None else asset_cache_plan(),
        )

    def test_identical_inputs_produce_one_stable_key(self) -> None:
        self.assertEqual(self.key(), self.key())

    def test_changed_object_hash_changes_the_key(self) -> None:
        # The asset map carries AnimeStudio's XXH64 of the raw object bytes, so
        # an object the game patched cannot be served from the cache.
        self.assertNotEqual(
            self.key(),
            self.key(entry=asset_map_entry(Hash="bbbbbbbbbbbbbbbb")),
        )

    def test_changed_cli_dummy_dlls_or_source_change_the_key(self) -> None:
        baseline = self.key()
        for field, value in (
            ("cli_signature", {"fingerprint": "cli-2"}),
            ("dummy_dll_signature", {"dll_count": 3, "bytes": 11, "fingerprint": "dll-2"}),
            ("source_fingerprint", {"files": 4, "bytes": 31, "fingerprint": "src-2"}),
        ):
            with self.subTest(field=field):
                self.assertNotEqual(
                    baseline,
                    self.key(plan=asset_cache_plan(**{field: value})),
                )

    def test_changed_export_options_change_the_key(self) -> None:
        item = asset_cache_item()
        other = asset_cache_item()
        other["stage_signature"] = dict(other["stage_signature"], logger_flags=["Debug"])
        plan = asset_cache_plan()
        self.assertNotEqual(
            export_full_from_game.asset_entry_cache_key(asset_map_entry(), item, plan),
            export_full_from_game.asset_entry_cache_key(asset_map_entry(), other, plan),
        )

    def test_missing_evidence_refuses_to_produce_a_key(self) -> None:
        for field in export_full_from_game.ASSET_CACHE_REQUIRED_PLAN_SIGNATURES:
            with self.subTest(field=field):
                plan = asset_cache_plan(**{field: None})
                self.assertEqual(
                    export_full_from_game.asset_cache_plan_evidence_gap(plan),
                    field,
                )
                with self.assertRaises(ValueError):
                    self.key(plan=plan)

    def test_complete_evidence_reports_no_gap(self) -> None:
        self.assertIsNone(
            export_full_from_game.asset_cache_plan_evidence_gap(asset_cache_plan())
        )


class AnimeStudioAssetCacheValidityTests(unittest.TestCase):
    def cache_with(self, output_path: Path, **overrides) -> dict:
        stat = output_path.stat()
        entry = {
            "cache_key": "key-1",
            "output_path": str(output_path),
            "missing_output": False,
            "output_size": stat.st_size,
            "output_mtime_ns": stat.st_mtime_ns,
        }
        entry.update(overrides)
        return {"schema_version": 1, "entries": {"manifest-1": entry}}

    def test_matching_key_and_output_is_a_hit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prop_rock_p1234.obj"
            output.write_text("v 0 0 0\n", encoding="utf-8")
            self.assertTrue(
                export_full_from_game.asset_cache_entry_is_valid(
                    self.cache_with(output), "manifest-1", "key-1", output
                )
            )

    def test_changed_key_deleted_output_or_edited_output_is_a_miss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prop_rock_p1234.obj"
            output.write_text("v 0 0 0\n", encoding="utf-8")
            cache = self.cache_with(output)

            # A different cache key (new Hash, new CLI, new options, ...).
            self.assertFalse(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-1", "key-2", output
                )
            )
            # An unknown object.
            self.assertFalse(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-2", "key-1", output
                )
            )
            # An output edited or truncated outside the exporter.
            output.write_text("v 1 1 1\nv 2 2 2\n", encoding="utf-8")
            self.assertFalse(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-1", "key-1", output
                )
            )
            # An output that was deleted.
            output.unlink()
            self.assertFalse(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-1", "key-1", output
                )
            )

    def test_recorded_missing_output_stays_valid_only_while_still_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "clip_p9.anim"
            output.write_text("x", encoding="utf-8")
            cache = self.cache_with(output, missing_output=True)
            self.assertFalse(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-1", "key-1", output
                )
            )
            output.unlink()
            self.assertTrue(
                export_full_from_game.asset_cache_entry_is_valid(
                    cache, "manifest-1", "key-1", output
                )
            )

    def test_cache_written_for_another_schema_is_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "animestudio_asset_cache.json"
            path.write_text(
                json.dumps({"schema_version": 0, "entries": {"manifest-1": {}}}),
                encoding="utf-8",
            )
            cache = export_full_from_game.load_animestudio_asset_cache(path)
            self.assertEqual(cache["entries"], {})
            self.assertEqual(
                cache["schema_version"],
                export_full_from_game.ANIMESTUDIO_ASSET_CACHE_SCHEMA_VERSION,
            )

    def test_current_schema_cache_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "animestudio_asset_cache.json"
            export_full_from_game.save_animestudio_asset_cache(
                path, {"entries": {"manifest-1": {"cache_key": "key-1"}}}
            )
            cache = export_full_from_game.load_animestudio_asset_cache(path)
            self.assertEqual(cache["entries"]["manifest-1"]["cache_key"], "key-1")


class AnimeStudioAssetCacheEnablementTests(unittest.TestCase):
    def test_cache_is_on_by_default_and_opt_out_turns_it_off(self) -> None:
        source = inspect.getsource(export_full_from_game.main)
        self.assertIn(
            "animestudio_asset_cache_enabled = not (\n"
            "        args.skip_animestudio or args.animestudio_no_asset_cache\n"
            "    )",
            source,
        )
        self.assertIn(
            'options["asset_cache_enabled"] = animestudio_asset_cache_enabled',
            source,
        )
        # The run summary must report the live decision, not a hard-coded line.
        self.assertNotIn("cache_removed", source)
        self.assertNotIn("removed (every run re-exports)", source)

    def test_plan_records_the_three_cache_key_signatures(self) -> None:
        plan = export_full_from_game.plan_animestudio_stage(
            source="StreamingAssets",
            output_root=Path("export_full"),
            stage="convert_by_type",
            options={
                "export_type": "Convert",
                "asset_cache_enabled": True,
                "types": ("Mesh:Both",),
            },
            cli_signature={"fingerprint": "cli-1"},
            dummy_dll_signature={"fingerprint": "dll-1"},
            source_fingerprint={"fingerprint": "src-1"},
        )
        self.assertEqual(plan["cache_state"], "per_asset")
        self.assertIsNone(export_full_from_game.asset_cache_plan_evidence_gap(plan))

    def test_plan_without_the_cache_stays_uncached(self) -> None:
        plan = export_full_from_game.plan_animestudio_stage(
            source="StreamingAssets",
            output_root=Path("export_full"),
            stage="convert_by_type",
            options={
                "export_type": "Convert",
                "asset_cache_enabled": False,
                "types": ("Mesh:Both",),
            },
        )
        self.assertEqual(plan["cache_state"], "no_cache")
        self.assertEqual(plan["cached_items"], [])
        self.assertEqual(plan["run_items"], ["Mesh"])

    def test_opt_out_flag_is_parseable_and_defaults_to_false(self) -> None:
        with mock.patch(
            "sys.argv",
            ["export_full_from_game.py"],
        ):
            args = export_full_from_game.parse_args()
        self.assertFalse(args.animestudio_no_asset_cache)
        with mock.patch(
            "sys.argv",
            ["export_full_from_game.py", "--animestudio-no-asset-cache"],
        ):
            args = export_full_from_game.parse_args()
        self.assertTrue(args.animestudio_no_asset_cache)


class AnimeStudioAssetCachePruningTests(unittest.TestCase):
    def test_outputs_of_vanished_objects_are_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            type_dir = export_full_from_game.animestudio_stage_dir(
                output_root, "StreamingAssets", "convert_by_type"
            ) / "Mesh"
            type_dir.mkdir(parents=True)
            kept = export_full_from_game.predict_animestudio_convert_output_path(
                output_root, "StreamingAssets", "convert_by_type", asset_map_entry()
            )
            kept.write_text("v 0 0 0\n", encoding="utf-8")
            vanished = type_dir / "deleted_prop_p999.obj"
            vanished.write_text("v 1 1 1\n", encoding="utf-8")

            removed = export_full_from_game.prune_unmatched_animestudio_asset_outputs(
                output_root=output_root,
                source="StreamingAssets",
                stage="convert_by_type",
                entries=[asset_map_entry()],
                type_name="Mesh",
            )
            self.assertEqual(removed, 1)
            self.assertTrue(kept.is_file())
            self.assertFalse(vanished.exists())

    def test_pending_outputs_are_removed_before_re_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            stale = export_full_from_game.predict_animestudio_convert_output_path(
                output_root, "StreamingAssets", "convert_by_type", asset_map_entry()
            )
            stale.parent.mkdir(parents=True)
            stale.write_text("v 0 0 0\n", encoding="utf-8")

            removed = export_full_from_game.remove_animestudio_asset_outputs(
                output_root=output_root,
                source="StreamingAssets",
                stage="convert_by_type",
                entries=[asset_map_entry()],
            )
            self.assertEqual(removed, 1)
            self.assertFalse(stale.exists())


class AnimeStudioAssetShardCacheDecisionTests(unittest.TestCase):
    """End-to-end reuse decision over a fixture asset map."""

    ENTRIES = (
        asset_map_entry(Name="rock", PathID=1, Hash="1111111111111111"),
        asset_map_entry(Name="tree", PathID=2, Hash="2222222222222222"),
        asset_map_entry(Name="wall", PathID=3, Hash="3333333333333333"),
    )

    def build(self, output_root: Path, entries, *, cache=None, plan_overrides=None):
        map_path = output_root / "maps" / "endfield_streamingassets_assets.json"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps({"AssetEntries": list(entries)}), encoding="utf-8")
        options = {
            "export_type": "Convert",
            "asset_cache_enabled": True,
            "asset_map_filter": True,
            "map_name": str(map_path),
            "asset_shards": 2,
            "types": ("Mesh:Both",),
        }
        plan = asset_cache_plan(options=options)
        plan.update(plan_overrides or {})
        item = asset_cache_item()
        item["stage_signature"] = export_full_from_game.build_animestudio_stage_signature(
            "convert_by_type", options, "Mesh:Both"
        )
        return export_full_from_game.prepare_animestudio_asset_shards(
            source="StreamingAssets",
            output_root=output_root,
            stage="convert_by_type",
            plan=plan,
            runnable_items=[item],
            jobs=2,
            asset_cache=cache,
        ), plan, item

    def seed_cache(self, output_root: Path, plan, item, entries):
        """Write the outputs and cache rows a previous run would have left."""
        cache = export_full_from_game.default_animestudio_asset_cache()
        for entry in entries:
            output = export_full_from_game.predict_animestudio_convert_output_path(
                output_root, "StreamingAssets", "convert_by_type", entry
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(f"v {entry['PathID']} 0 0\n", encoding="utf-8")
        export_full_from_game.update_asset_cache_entries(
            cache=cache,
            entries=list(entries),
            item=item,
            plan=plan,
            output_root=output_root,
            source="StreamingAssets",
            stage="convert_by_type",
        )
        return cache

    def test_unchanged_assets_are_reused_and_changed_ones_re_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            _, plan, item = self.build(output_root, self.ENTRIES)
            cache = self.seed_cache(output_root, plan, item, self.ENTRIES)

            # Same game, same CLI, same options: nothing to do.
            work, _, _ = self.build(output_root, self.ENTRIES, cache=cache)
            self.assertEqual(len(work["cached_entries"]), 3)
            self.assertEqual(work["pending_entries"], [])
            self.assertEqual(work["shards"], [])

            # One object's raw bytes changed and one object is new.
            patched = (
                self.ENTRIES[0],
                asset_map_entry(Name="tree", PathID=2, Hash="ffffffffffffffff"),
                self.ENTRIES[2],
                asset_map_entry(Name="fence", PathID=4, Hash="4444444444444444"),
            )
            work, _, _ = self.build(output_root, patched, cache=cache)
            self.assertEqual(
                sorted(entry["Name"] for entry in work["cached_entries"]),
                ["rock", "wall"],
            )
            self.assertEqual(
                sorted(entry["Name"] for entry in work["pending_entries"]),
                ["fence", "tree"],
            )

    def test_a_new_cli_build_invalidates_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            _, plan, item = self.build(output_root, self.ENTRIES)
            cache = self.seed_cache(output_root, plan, item, self.ENTRIES)

            work, _, _ = self.build(
                output_root,
                self.ENTRIES,
                cache=cache,
                plan_overrides={"cli_signature": {"fingerprint": "cli-rebuilt"}},
            )
            self.assertEqual(work["cached_entries"], [])
            self.assertEqual(len(work["pending_entries"]), 3)

    def test_a_patched_game_invalidates_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            _, plan, item = self.build(output_root, self.ENTRIES)
            cache = self.seed_cache(output_root, plan, item, self.ENTRIES)

            # Streamed payloads (.resS) are not covered by the per-object Hash,
            # so the source VFS fingerprint has to invalidate the cache too.
            work, _, _ = self.build(
                output_root,
                self.ENTRIES,
                cache=cache,
                plan_overrides={
                    "source_fingerprint": {"files": 9, "bytes": 99, "fingerprint": "src-2"}
                },
            )
            self.assertEqual(work["cached_entries"], [])
            self.assertEqual(len(work["pending_entries"]), 3)

    def test_disabled_cache_marks_every_entry_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            _, plan, item = self.build(output_root, self.ENTRIES)
            cache = self.seed_cache(output_root, plan, item, self.ENTRIES)

            map_path = output_root / "maps" / "endfield_streamingassets_assets.json"
            options = dict(plan["options"], asset_cache_enabled=False, map_name=str(map_path))
            disabled_plan = asset_cache_plan(options=options)
            work = export_full_from_game.prepare_animestudio_asset_shards(
                source="StreamingAssets",
                output_root=output_root,
                stage="convert_by_type",
                plan=disabled_plan,
                runnable_items=[item],
                jobs=2,
                asset_cache=cache,
            )
            self.assertFalse(work["cache_enabled"])
            self.assertEqual(work["cached_entries"], [])
            self.assertEqual(len(work["pending_entries"]), 3)

    def test_enabled_cache_without_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            with self.assertRaises(ValueError):
                self.build(
                    output_root,
                    self.ENTRIES,
                    plan_overrides={"cli_signature": None},
                )


if __name__ == "__main__":
    unittest.main()
