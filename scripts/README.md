# Scripts

This directory contains the maintained exporters and builders for the static
WebUI. Use the root wrappers for normal work; call Python entry points only for
focused development or validation.

## Root workflows

| Goal | Command |
| --- | --- |
| First-time Story/Text setup | `.\setup_first_time.bat` |
| Rebuild from the current export | `.\export.bat` |
| Refresh Story from the game | `.\export.bat --from-game` |
| Refresh Story and assets together | `.\export.bat --from-game --with-assets` |
| Story/Mission recovery loop | `.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference` |
| Mission Pipeline JSON only | `.\export.bat --mission-pipeline-data-only` |
| Reindex assets and CN audio | `.\export_assets.bat` |
| Refresh assets and CN audio | `.\export_assets.bat --from-game` |
| Compare exports for Updates | `.\build_updates.bat OLD NEW` |
| Serve or package | `python serve.py` / `python scripts\pack_webui.py` |

The wrappers load `endfield_paths.bat`, then apply explicit path flags. Run any
wrapper with `--help` for its supported options.

## Export rules

`export.bat` is the canonical Story, Text, Characters, Gameplay, and generated
WebUI rebuild. It reads the current `export_full/` by default and runs
`verify_export_freshness.py` before downstream builders. Use `--from-game` only
when the extraction must be refreshed from the installed client.

Useful shared flags:

- `--with-assets` adds asset indexes and CN audio relinking.
- `--focused-assets`, `--default-assets`, and `--debug-assets` select asset
  scope from narrowest to broadest.
- `--asset-jobs N` caps AnimeStudio workers; `--webui-jobs N` caps independent
  post-Story builders.
- `--game-root PATH` overrides the configured client for one run.
- `--story-only`, `--mission-pipeline-only`, and
  `--mission-pipeline-data-only` stop after their named scope.
- `--full-source-graph` adds exhaustive Unity-object/PathID graph work. The
  default graph contains only source rows consumed by WebUI edges.

Installed-game-only flags fail with an explanation when `--from-game` is
absent. Keep wrapper files CRLF; LF-only batch files can break backward `goto`
argument loops under `cmd.exe`.

Every export records build-step timings and a process-tree benchmark under
`reports/export/`. The Combat builder rejects stale graph inputs and publishes
a degraded reason instead of using them as direct evidence.

## Main builders

| Area | Entry point | Main output |
| --- | --- | --- |
| Extraction | `export_full_from_game.py` | `export_full/` |
| Export freshness | `verify_export_freshness.py` | validation result |
| WebUI orchestration | `build_webui_views.py` | semantic page data |
| Story evidence | `story_builder/refresh_evidence.py` | `reports/story/` evidence |
| Story links | `story_builder/source_links.py` | localized reference data |
| Story | `story_builder/build.py` | `webui/data/lang/<LANG>/` |
| Mission Pipeline | `build_mission_pipeline_data.py` | `webui/data/mission_pipeline/` |
| Characters | `build_character_data.py` | character indexes |
| Gameplay | `build_gameplay.py` | Gameplay datasets |
| Assets | `build_assets.py` | asset indexes and media lookup |
| Audio | `build_audio.py` | decoded/relinked audio data |
| Updates | `build_updates.py` | `webui/data/updates/latest.json` |
| Packaging | `pack_webui.py` | distributable static package |

`build_gameplay.py` owns every Gameplay dataset; focused stages live in
`gameplay_builder/`. The legacy economy, world, presentation, and broad data
index helpers are diagnostic only and do not feed active pages.

Typical focused commands:

```bat
python scripts\verify_export_freshness.py
python scripts\story_builder\refresh_evidence.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay.py
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\pack_webui.py
```

Direct Story builds take several minutes. Allow at least 15 minutes for the
shell command, especially for multiple languages or forced Timeline recovery.

## Story recovery

Production parsing, validation, attachment, and generated schemas live in
`story_builder/`. Audit and candidate-generation tools live in
`story_recovery/`; they may import stable builder primitives, but production
builders must not import or execute recovery modules.

Work in small validated batches:

1. Use focused unit tests, parser probes, or
   `--mission-pipeline-data-only` while generated Story inputs are current.
2. After at least three independent changes, or at the end of a coherent
   30–60 minute batch, run the canonical `--mission-pipeline-only` rebuild.
3. Rebuild earlier only for changed installed inputs, stale generated data, or
   a cross-cutting schema change that focused tests cannot validate.

Reuse Timeline order and localized references only when their inputs are
unchanged. `--reuse-reference` is incompatible with `--from-game`.

Validators fail closed. A failure must name the validator, gate, affected
mission or Story key, source path, bounded expected/actual values, and relevant
hashes in both structured output and the CLI summary.

Manual Story order is user-managed in `webui/overrides/story_order.json`.
OCR writes proposals to `webui/data/story_order_ocr.json`; exports never replace
the active override.

## Assets and audio

Prefer `export.bat --from-game --with-assets` when both Story and assets need a
fresh extraction. Use `export_assets.bat --from-game` when Story is already
current, or plain `export_assets.bat` to rebuild indexes and relink existing
decoded assets.

`build_audio.py` writes shared SFX/music once under
`export_full/structured/Audio/shared/` and language voice under
`export_full/structured/Audio/<LANG>/`. AnimeStudio streams decoded PCM into
lossless FLAC by default without intermediate WAV files or `ffmpeg`; use
`--format wav` or `--format wem` only when needed.

The default AnimeStudio type-job mode is `auto`: map-filtered conversion stays
sharded, while broad Story JSON runs in isolated sequential processes. Do not
add a JSON type to map filtering until broad and filtered exports are
byte-diffed. Do not shard JSON export without new measurements; current results
show disk contention rather than a speedup.

Optional DummyDll regeneration is build-specific:

```bat
python scripts\animestudio\generate_dummydll.py --dry-run
python scripts\animestudio\generate_dummydll.py --replace
```

Missing or stale DummyDlls warn and fall back to serialized schemas. Never
reuse native registration addresses across game builds.

## Updates

Updates compare two complete export folders. Pass `OLD NEW`, or configure
`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` in
`endfield_paths.bat`. A named `OLD` refreshes the cached baseline.

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --text-only
.\build_updates.bat OLD NEW --no-audio
.\build_updates.bat OLD NEW --exact
python scripts\build_updates.py --refresh-previous-export-baseline
```

The default scan covers WebUI-facing exported text plus image, model, video,
and decoded audio assets. `--text-only` omits all assets, `--no-audio` keeps
other assets, `--exact` hashes contents, and `--full-export-scan` is for broad
audits only.

Pruning is destructive. Preview byte-identical files in the previous export
with `.\build_updates.bat --prune-old --dry-run`; run without `--dry-run` only
when intentionally cleaning that saved previous export. The guard rejects the
current export and repository root.

## Native evidence and source graph

Steps that read `GameAssembly.dll` or `global-metadata.dat` validate the exact
installed build first. Missing or mismatched inputs skip only that step and
leave its published report untouched. Set
`ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` when an audit must fail hard.

The source graph is rebuilt after semantic views:

```bat
python tools\endfield_source_graph.py build
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

## Output hygiene

- Generated reports belong in topic directories under `reports/`.
- Reusable conclusions belong in the six topic files under `memory/`.
- Revisitable experiments belong in `scratch/<topic>/<task>/`.
- Disposable intermediates belong in `tmp/<topic>/<run>/` and should be
  removed after validation.
- New maintained scripts must support the WebUI or the Unity character lab;
  otherwise keep them in `scratch/` or `tmp/`.
