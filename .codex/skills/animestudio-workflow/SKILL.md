---
name: animestudio-workflow
description: Use when working on the local tools/AnimeStudio exporter for Endfield, including compiling AnimeStudio.CLI, calling it directly or through export.bat and export_assets.bat, using integrated VFS dump/audio/index commands, debugging MonoBehaviour and Export error logs, inspecting code structure, and reducing per-worker memory use.
---

# Animestudio Workflow

## When To Use

Use this skill for AnimeStudio or Anime Studio tasks in this repo: building the CLI, changing `tools/AnimeStudio`, running installed-game Unity asset exports, running integrated VFS structured/audio/index commands, explaining CLI arguments, investigating object parser failures, or tuning `--asset-jobs`.

If the task is about the whole WebUI export flow, also use `endfield-webui-workflow`. For implementation details, read `references/animestudio.md` before changing code or diagnosing logs.

## Quick Commands

Initialize and build the local submodule:

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
```

Fast rebuild after the first restore:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Expected executable:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

## DummyDll Regeneration

When a task needs script-derived MonoBehaviour schemas, or the installed game
changed since `tools\DummyDll\generation.json`, first run:

```bat
python scripts\animestudio\generate_dummydll.py --dry-run
```

If the unique registration checks pass and regeneration is actually needed:

```bat
python scripts\animestudio\generate_dummydll.py --replace
```

The generator owns CodeRegistration/MetadataRegistration discovery, the tested
Cpp2IL `2022.0.7` patch/build, staged validation, atomic publication, backup,
and provenance manifest. Never reuse addresses from memory or a prior build.
Treat Cpp2IL skip counts as coverage gaps, verify that the target full type name
exists in the generated assembly, and keep AnimeStudio serialized-first unless
a focused comparison proves script-first is better. Read the DummyDll section
in `references/animestudio.md` before diagnosing or changing this path.

## Wrapper Usage

Use the parent wrappers for normal Endfield exports:

```bat
.\export.bat --from-game
.\export_assets.bat --from-game
.\build_updates_by_patch.bat
```

Both pass AnimeStudio options through to `scripts\export_full_from_game.py`. Keep `--asset-jobs` conservative unless the machine has enough free RAM:

```bat
.\export.bat --from-game --asset-jobs 2
.\export_assets.bat --from-game --asset-jobs 2
```

The default is now `8`; AnimeStudio subprocess tasks for each source share
that worker pool, and asset shards are queued round-robin by type. Lower
`--asset-jobs` when peak memory is too high.
`export.bat --from-game` also uses AnimeStudio as the default structured
data dumper. `export_assets.bat --from-game` uses AnimeStudio for the
lightweight `vfs-index` snapshot and CN audio decode before relinking.
Asset conversion uses more shards than workers by default: `--animestudio-shards 16`
with `--animestudio-jobs 8`; the shared pool consumes those shards alongside
other AnimeStudio type requests. Adjust `--animestudio-shards` separately to tune
per-process asset slice size. Non-sharded JSON type jobs use
`--animestudio-type-job-mode auto` by default, merging map-filtered JSON while
running broad Story JSON types sequentially in isolated processes; pass
`parallel` only when comparing concurrent per-type jobs.
`export_assets.bat --from-game` now defaults to the standard WebUI-facing
image/model asset export plus `Material` JSON. Asset modes, from narrowest to
broadest, are `--focused-assets`, `--default-assets`, and `--debug-assets`.
Audio export defaults to direct lossless FLAC through AnimeStudio's in-process
encoder. It does not create intermediate WAV files or require `ffmpeg`; use
`--format wav` or `--format wem` only for explicit compatibility output.

## Integrated VFS Commands

AnimeStudio.CLI now owns the Endfield VFS paths used by the WebUI wrappers:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe audio --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe stream --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe list --help
```

`dump`, `audio`, `stream`, and `vfs-index` must expose `--fallback-assets`. Use direct
subcommand calls for parity probes or targeted extraction; use the parent
wrappers for normal WebUI exports.

`vfs-index --jsonl` writes streaming header/block/chunk/file/summary records for
the original-data snapshot tracker without materializing the large duplicated
JSON index shape. The default remains the existing JSON document format.

## Direct CLI Shape

Use direct CLI calls only for targeted debugging:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe input_path output_path --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType
```

Common direct options:

```bat
--map_op Both --map_type JSON
--export_type JSON --types MonoBehaviour:Both
--export_type Convert --types Texture2D:Both
--dummy_dlls path\to\DummyDll  (optional)
--filter_data export_full\recovered\AnimeStudio-cli\timeline_targets.json
```

## Diagnostics

After wrapper runs, start with:

```text
reports\export\export_full_summary.md
reports\export\runs\<timestamp>\StreamingAssets\*.stdout.log
reports\export\runs\<timestamp>\StreamingAssets\*.stderr.log
reports\export\runs\<timestamp>\Persistent\*.stdout.log
reports\export\runs\<timestamp>\Persistent\*.stderr.log
export_full\recovered\AnimeStudio-cli\animestudio_type_manifest.json
```

Use the `reports_run_root` recorded in the latest JSON summary to locate the
matching timestamped logs. Do not write exporter logs or summaries directly at
the `reports/` root.

The exporter keeps five timestamped run directories under
`reports/export/runs/` by default. Override this with
`--report-runs-to-keep N`; use `0` only when intentionally disabling pruning.
The separate `benchmark_export.py` wrapper keeps ten runs per label under
`reports/export/benchmarks/` and writes its latest summary under
`reports/export/`.

Put revisitable exporter probes under `scratch/animestudio/<task>/` and
disposable decode/export intermediates under `tmp/animestudio/<task-or-run>/`.
Put IL2CPP or native-code-only probes under
`scratch/reverse_engineering/<task>/` or
`tmp/reverse_engineering/<task-or-run>/`. Do not write loose files or run
directories at the root of `scratch/` or `tmp/`; remove completed temporary
runs after validation.

`Export ... error` means one asset conversion failed inside a stage; other assets in that process may still export. A nonzero AnimeStudio subprocess now fails the wrapper. A MonoBehaviour `metadata-only JSON` warning means the tool preserved object metadata and raw hashes after schema decode failed, instead of dropping the object entirely.

For code structure, memory guards, CLI API, and log interpretation, read `references/animestudio.md`.
