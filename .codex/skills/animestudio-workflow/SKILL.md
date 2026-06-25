---
name: animestudio-workflow
description: Use when working on the local tools/AnimeStudio exporter for Endfield, including compiling AnimeStudio.CLI, calling it directly or through export.bat and export_assets.bat, debugging MonoBehaviour and Export error logs, inspecting code structure, and reducing per-worker memory use.
---

# Animestudio Workflow

## When To Use

Use this skill for AnimeStudio or Anime Studio tasks in this repo: building the CLI, changing `tools/AnimeStudio`, running installed-game Unity asset exports, explaining CLI arguments, investigating object parser failures, or tuning `--animestudio-jobs`.

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

## Wrapper Usage

Use the parent wrappers for normal Endfield exports:

```bat
.\export.bat --export-from-game
.\export_assets.bat --export-from-game
```

Both pass AnimeStudio options through to `scripts\export_full_from_game.py`. Keep `--animestudio-jobs` conservative unless the machine has enough free RAM:

```bat
.\export.bat --export-from-game --animestudio-jobs 2
.\export_assets.bat --export-from-game --animestudio-jobs 2
```

The default is `1` for lower peak memory. On the current 64 GiB workstation, `2` was the best measured setting; avoid `3` unless there is substantially more free RAM.

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
--dummy_dlls path\to\DummyDll
--filter_data export_full\recovered\AnimeStudio-cli\timeline_targets.json
```

## Diagnostics

After wrapper runs, start with:

```text
reports\export_full_summary.md
reports\StreamingAssets\*.stdout.log
reports\StreamingAssets\*.stderr.log
reports\Persistent\*.stdout.log
reports\Persistent\*.stderr.log
export_full\recovered\AnimeStudio-cli\animestudio_type_manifest.json
```

`Export ... error` means one asset conversion failed inside a stage; other assets in that process may still export. A nonzero AnimeStudio subprocess now fails the wrapper. A MonoBehaviour `metadata-only JSON` warning means the tool preserved object metadata and raw hashes after schema decode failed, instead of dropping the object entirely.

For code structure, memory guards, CLI API, and log interpretation, read `references/animestudio.md`.
