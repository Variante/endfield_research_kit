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
.\scripts\animestudio\setup_vgmstream.bat
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
- Local changed-file refresh with every normal WebUI builder: `export.bat --changed-only`.
- Assets and CN audio only: `export_assets.bat --from-game`.
- Updates publication from two complete exports: `build_updates.bat OLD NEW`.

Use direct CLI calls only for targeted parity probes, extraction, or debugging.
Inspect subcommand help rather than duplicating its full option surface:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe audio --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe stream --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-audit --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-profile --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-inner-audit --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe audio-audit --help
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe list --help
```

`dump`, `audio`, `stream`, and `vfs-index` must expose `--fallback-assets`.
`dump`, `stream`, and `vfs-index` support repeated `--block-type` and
`--file-regex` filters. Audio defaults to direct lossless FLAC; request WAV or
WEM only for explicit compatibility needs.

For VFS-format or payload-semantic recovery, start with the "VFS recovery
evidence index" in `references/animestudio.md`. It maps every active block
family to its maintained reader, negative fixtures, corpus reports, and the
remaining evidence boundary. Read the outer-boundary report before an inner
format report: a valid offset/hash proves the bytes being studied, not their
internal schema or runtime meaning.

After any installed-game change, rerun `vfs-audit` first and treat its
`inputSetSha256` as the provenance gate for every inner census. Do not transfer
a prior type-level "current corpus" result merely because file counts stayed
constant; rejoin identities/hashes or rerun the relevant sweep.

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

Use DummyDlls only when script-derived MonoBehaviour schemas matter. Before
schema-dependent work, and after an installed-game, generator, or pinned
Cpp2IL-Endfield release change, check the repo-local set first:

```bat
python -m scripts.animestudio.generate_dummydll --status-only
python -m scripts.animestudio.generate_dummydll --dry-run
```

If status is missing, stale, invalid, or degraded and script schemas are in
scope, refresh it proactively: require the dry run's unique registration and
source-provenance checks, then run `--replace` and re-run `--status-only`. Never reuse
registration addresses from an earlier build. The generator must block any
type-population failure, a required-image skip, catastrophic size regression,
or any mismatch in the full metadata-to-DummyDll `(assembly, token, FullName)`
identity join by default; do not use its coverage-regression override during
routine refreshes.
The identity gate requires a built AnimeStudio CLI. Missing or unusable
DummyDlls must warn and fall back cleanly; normal exports must continue.

Keep serialized-first TypeTree priority by default. Treat historical or
experimental Cpp2IL type skips as coverage gaps, verify the required full type
name exists in the generated assembly, and use script-first only for a focused
comparison. Method generic parameters must be declared in metadata order before
constraints, return types, or parameters are imported; return-first lazy MVAR
creation can silently reorder multi-generic signatures.

Cpp2IL Endfield compatibility is owned by
`https://github.com/Variante/Cpp2IL-Endfield`, branch
`endfield/2022.0.7`. Make source changes there, build them, publish a new
immutable `endfield-2022.0.7-vN` tag, and update both the tag and commit pin in
`generate_dummydll.py`. The generator may advance an existing checkout only
when its tracked files are clean and its origin matches that repository; a
dirty or foreign checkout must fail closed. Do not restore the retired in-repo
patch workflow.

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
