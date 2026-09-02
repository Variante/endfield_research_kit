---
name: animestudio-workflow
description: Build, run, debug, and modify the local Endfield AnimeStudio exporter under tools/AnimeStudio. Use for AnimeStudio.CLI compilation, wrapper integration, VFS dump/audio/stream/index commands, MonoBehaviour or export errors, DummyDll schema recovery, targeted asset conversion, and worker-memory tuning.
---

# AnimeStudio Workflow

Work from the repository root. For WebUI delivery, use the relevant
specialized WebUI skill. Read `references/animestudio.md` before
changing exporter code, diagnosing nontrivial logs, or working with DummyDlls;
it contains CLI details, code structure, and focused verification patterns.

## Build

Initialize and build the tracked submodule:

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
```

After the first restore, prefer:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

The expected executable is
`tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.

## Choose the Entry Point

Use repository wrappers for production workflows:

- Story refresh: `export.bat --from-game`.
- Story and assets together: `export.bat --from-game --with-assets`.
- Assets and CN audio only: `export_assets.bat --from-game`.
- Installed-data patch workflow: `build_updates_by_patch.bat`.

Use direct CLI calls only for targeted parity probes, extraction, or debugging.
Inspect subcommand help rather than duplicating its full option surface:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe audio --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe stream --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe list --help
```

`dump`, `audio`, `stream`, and `vfs-index` must expose `--fallback-assets`.
`dump`, `stream`, and `vfs-index` support repeated `--block-type` and
`--file-regex` filters. Audio defaults to direct lossless FLAC; request WAV or
WEM only for explicit compatibility needs.

## Scope and Concurrency

Use `--focused-assets`, `--default-assets`, or `--debug-assets` from narrowest
to broadest. Keep `--asset-jobs N` conservative relative to available RAM.
Adjust worker count before changing shard count or exporter architecture.

Preserve the measured scheduling model: map-filtered conversion may shard,
while broad Story JSON types run sequentially in isolated processes. Do not add
JSON sharding or concurrent broad JSON loads without byte-for-byte comparison
and performance evidence. Add a type to map filtering only after broad and
filtered exports match byte-for-byte; equal object counts are insufficient.

## DummyDll Recovery

Use DummyDlls only when script-derived MonoBehaviour schemas matter. After an
installed-game update, or when provenance is stale, run:

```bat
python -m scripts.animestudio.generate_dummydll --dry-run
```

Run `--replace` only after unique registration and staged validation pass.
Never reuse registration addresses from an earlier build. Missing or stale
DummyDlls must warn and fall back cleanly; normal exports must continue.

Keep serialized-first TypeTree priority by default. Treat Cpp2IL skip counts as
coverage gaps, verify the required full type name exists in the generated
assembly, and use script-first only for a focused comparison.

## Diagnose and Change Safely

Start wrapper diagnosis with:

- `reports/export/export_full_summary.md` and its JSON companion.
- The `reports_run_root` recorded in the latest summary.
- Per-source stdout/stderr logs under `reports/export/runs/<timestamp>/`.
- `export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json`.

An `Export <Type>:<Name> error` is a per-asset failure; the process may have
continued. A nonzero subprocess return code fails the wrapper. A
`metadata-only JSON` warning means identity and raw hashes were preserved after
schema decoding failed.

For count-driven parser allocations, use the maintained count guards described
in the reference. Keep failures local to malformed objects when possible. Make
narrow changes, rebuild the CLI, and rerun the smallest affected source,
stage, and type before attempting a broad export.

Keep exporter reports under `reports/export/`, revisitable probes under
`scratch/animestudio/<task>/`, and disposable work under
`tmp/animestudio/<task-or-run>/`. Put native-only probes under the matching
`reverse_engineering` topic. Remove completed temporary runs.
