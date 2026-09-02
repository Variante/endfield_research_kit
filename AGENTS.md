Agent notes for this repo. User-facing usage belongs in `README.md`.

## Active Scope

Keep root-level docs and workflow guidance focused on:

- the static WebUI in `webui/`

Keep the active documentation hierarchy concise:

- `README.md` is the short user-facing entry point. Preserve its screenshot
  gallery, Chinese links, acknowledgements, quick start, common commands, and
  headline Story/character progress.
- `scripts/README.md` is a compact maintained command/script map, not an
  exhaustive implementation narrative.
- `webui/README.md` documents only frontend scope, data layout, and behavior
  contracts.
- each `memory/*.md` topic records current status, stable evidence boundaries,
  essential commands, and the highest-value remaining gaps.

Fold durable observations, conclusions, and recovery status into the existing
topic documents under `memory/`. Do not recreate one-file-per-investigation or
dated status snapshots. Generated inventories belong in `reports/`, and
disposable evidence belongs in `scratch/` or `tmp/`.

### Audio recovery documentation boundary

Keep Audio documentation split by audience and do not repeat the same
build-specific catalog across files:

- `scripts/README.md` owns maintained Audio commands, module ownership, and
  builder/output contracts.
- `webui/README.md` owns only Audio page behavior, generated-data layout, and
  frontend evidence/filter contracts.
- `memory/game_data_recovery.md` owns durable Wwise, serialized-data, and
  native-consumer conclusions plus the highest-value recovery gaps.
- `memory/webui_recovery.md` owns the current user-visible Audio recovery
  state and UI-facing evidence boundary.
- Per-build addresses, method tokens, hashes, mapping tables, and full
  inventories belong in versioned code contracts or generated reports, not in
  `AGENTS.md`, active READMEs, or memory prose. Changing counts belong in
  reports; disposable before/after evidence belongs in `tmp/audio/<task>/`.

Audio code follows the same ownership boundary. `build_audio.py` owns decode,
Wwise indexing, relinking, and Gameplay sidecars;
`build_audio_semantics.py` owns orchestration and publication only; reusable
semantic domains live under `scripts/audio_semantics/`. Add logic to its
domain owner instead of growing either entry point or importing the entry
point as a helper library. Native claims must use the explicit selected
`global-metadata.dat` plus `GameAssembly.dll` gate, fail closed on
missing/mismatched inputs, and never fall back to a module-global game root.
Do not add compatibility re-exports, duplicate native catalogs, broad
`ImportError` import fallbacks, or a second scan when one collected context
index can supply both names and hashes.

## Commands

```bat
.\setup.bat
.\export.bat
.\export.bat --with-assets
.\export.bat --from-game
python -m scripts.build_mission_pipeline_data --refresh-source-story-gap-queue
.\build_updates.bat
.\build_updates.bat OLD NEW
.\export_assets.bat
python serve.py
python serve.py 9000
```

Export and rebuild commands are generally long-running. Give them an
appropriately long timeout and wait patiently for completion; do not poll or
check their results frequently while they are still running.

Before starting a WebUI server, check whether the default
`http://127.0.0.1:8765/` server is already running. Reuse the existing default
server instead of starting another `serve.py` process on `8765` or a custom
port, unless the user explicitly asks for a second server.

Root wrapper scripts load `endfield_paths.bat` before parsing arguments. That
file sets the repeated local defaults for `ENDFIELD_GAME_ROOT`,
`ENDFIELD_PREVIOUS_EXPORT_ROOT`, and `ENDFIELD_EXPORT_ROOT`; explicit path
flags still override it for one-off commands.

The wrappers share one flag vocabulary: `--from-game` reads installed game
data, `--focused-assets`/`--default-assets`/`--debug-assets` set asset scope,
`--asset-jobs N` caps AnimeStudio workers, `--webui-jobs N` caps post-Story
builders, `--game-root PATH` overrides the installed client, and `--help`
prints a plain-language option list on every wrapper. Options that only apply while reading
installed game data are rejected with an explanatory message when
`--from-game` is absent, instead of being silently dropped. Batch wrappers are
CRLF: cmd.exe mis-resolves backward `goto` in LF-only batch files, which
breaks their argument loops.

`setup.bat` is the user-facing all-in-one first-time setup path. It
initializes `tools/AnimeStudio`, builds the AnimeStudio CLI, verifies the
integrated AnimeStudio VFS/audio commands, runs `export.bat --from-game
--story-only --animestudio-story-monobehaviour-names`,
prints optional `export_assets.bat --from-game` and plain `export.bat` follow-up
commands for the remaining semantic views, explains that Updates requires two
complete exports, then starts or reuses the default WebUI server.
Pass `--no-serve` when setup should finish without starting `serve.py`.
The `endfield_reconstruction_lab` and `tools/EndfieldCapture` submodules are
optional and are not initialized by this quick-start path.

`export.bat` is the canonical Story/Text Tables and curated semantic-view WebUI rebuild from an existing
`export_full/`. It verifies that `export_full/` matches the current installed
`Endfield_Data` fingerprints before the long WebUI builders run, then builds CN
Story/Text Tables data by default. It does not export from installed game data by
default. Pass `--from-game` only when the user explicitly asks to refresh
`export_full/` and run the story export tools. Pass `--with-assets` to also
rebuild asset indexes and relink/decode CN audio after generated conversations
are rebuilt. Combining `--from-game --with-assets` runs one AnimeStudio
Story+asset export instead of separate Story and asset exporter invocations.
After Story is current, independent semantic builders run in dependency-safe
parallel phases; use `--webui-jobs N` to cap concurrency. Per-step timings are
written to `reports/export/webui_build_steps_latest.md/json`. After all
semantic-view builders and any requested asset/audio work, `export.bat`
rebuilds `reports/source_graph/endfield_source_graph.sqlite` with only the exact
original AssetMap source/PathID rows consumed by WebUI material, shader,
texture, and FMV edges, then builds the Combat view. Pass
`--full-source-graph` only when exhaustive Unity-object/PathID investigation and
generated graph follow-up reports are required. For a focused Mission Pipeline
edit loop, call the direct Python builders listed in the project Mission
Pipeline skill; the wrapper no longer owns a Mission Pipeline-only scope. The
data-only sequence omits source-story gap refresh and map preview rendering.
The Combat builder refuses graph edges when the database predates
its Gameplay/manifest/asset/AbilityEntity/CharacterTemplate inputs and records a
visible degraded-mode reason instead of treating stale edges as direct.
`export.bat` does not refresh `webui/overrides/story_order.json`; active Story
order is user-managed there, while OCR recovery writes proposed order references
under `webui/data/story_order_ocr.json`. Every `export.bat` run writes a
wall-time and process-tree RAM benchmark under `reports/export/benchmarks/` and updates
`reports/export/export_benchmark_latest.md/json`.
Use `build_updates.bat` to compare two complete exports. It reads the
previous/current export roots from `endfield_paths.bat` by default, tracks
WebUI-facing exported text JSON plus exported image/model/video assets and
decoded audio, and accepts a leading `OLD NEW` folder pair (or the long
`--previous-export-root`/`--export-root` flags) for one-off comparisons. A named
`OLD` implies `--refresh-previous-export-baseline`. Pass `--no-audio` to omit
decoded audio while keeping other asset entries. Pass `--text-only` only for a
text-only update feed, and `--exact` to hash asset contents instead of
comparing sizes. The wrapper forwards any other option to
`scripts/build_updates.py`.
Use `export_assets.bat` (a thin wrapper around `export.bat --assets-only`, so
it shares one option parser, freshness check, and benchmark report) when
generated Story is already current to rebuild
Mission Pipeline, map recovery, Characters, Gameplay/projectiles, WebUI Assets
indexes, compact Story media, CN audio links, the curated source graph, and
combat relationships. Pass `--from-game` only when the user explicitly asks
to run the default AnimeStudio image/model decode, `Material` JSON, and CN
audio decode from installed game data first. Prefer
`export.bat --from-game --with-assets` when Story and assets both need an
installed-game refresh. Asset modes, from narrowest to broadest, are
`--focused-assets`, `--default-assets`, and `--debug-assets`.
Asset-only extraction preserves the previous structured Story/Table source
fingerprints and records its current asset scan separately; it must never make
untouched structured data appear fresh after a client update. The configured
export root is passed as `--output` to extraction and `--export-root` to
downstream builders. Reject `--animestudio-object-index` in scopes that skip
Story evidence, because those scopes cannot refresh its Story consumer report.
Use direct `scripts/build_audio.py` runs for non-CN languages or audio-only
maintenance. The audio builder writes shared SFX/music once under
`export_full/structured/Audio/shared/` and language voice under
`export_full/structured/Audio/<LANG>/`, parses Wwise bank event-to-media links,
and post-processes generated conversation JSON with playable `audioSrc` links.
AnimeStudio pipes decoded Wwise PCM directly into its in-process FLAC encoder
and writes lossless FLAC without creating intermediate WAV files or requiring
`ffmpeg`. The maintained WebUI audio workflow is FLAC-only; existing WAV/WEM
files may still be indexed during a `--skip-decode` maintenance run.
It also writes the compact
per-language Gameplay skill/enemy SFX sidecar from exact SkillData/BuffData
references and Wwise event traversal. The default exporter mode is
`--animestudio-type-job-mode auto`: it merges map-filtered JSON, runs broad Story
JSON types sequentially in isolated processes, and keeps map-filtered asset
conversion sharded; use `parallel` only when comparing concurrent per-type jobs.
`TextAsset` loads through the generated asset map instead of every bundle:
byte-identical output, 508s -> 27s (475,588 bundle containers parsed -> 16,218).
Every other json type still loads broadly. Map filtering is only sound for a
type that resolves nothing outside its own bundle, because the filtered load
never opens the skipped bundles -- matching object counts prove nothing.
`MonoBehaviour` has complete map coverage and was still rejected: filtering
renamed 128,181 of 174,133 files to `MonoBehaviour#100001_p...` because the
defining MonoScript sits in a skipped bundle, and turned 2,709 resolved PPtr
targets into `external_target_unavailable`. `PlayableDirector` has zero map
entries and would emit nothing. Add to `ANIMESTUDIO_JSON_MAP_FILTER_TYPES`
only after exporting a type both ways and diffing the bytes;
`--no-animestudio-json-map-filter` forces the broad path. Sharding those loads was separately measured and rejected: on identical object sets, `Convert` Texture2D scales
4.03x across 8 shards while `JSON` Material runs 0.92-0.95x, i.e. no better
than one process. Convert is CPU-bound decode (~37 ms/object); JSON export is
~3.55 ms/object and bound on single-disk small-file creation, so extra
processes only contend. Keep `convert_by_type` sharding; do not add JSON
sharding. `--animestudio-broad-json-jobs N` bounds concurrent broad loads and
defaults to 1; values above 1 are not supported by any measurement.

For repeated Mission Pipeline recovery builds with unchanged Timeline and
Table inputs, use the direct Python sequences in
`.codex/skills/endfield-mission-pipeline-build/SKILL.md`. Story reference reuse
belongs to the direct Story builder and must not be used after an installed-game
refresh.

### Mission Recovery Edit-Loop Policy

Do not run a canonical Story/Mission Pipeline rebuild after every individual
recovery edit. Work in small validated batches:

- accumulate at least three independently validated recovery changes before
  running the direct Mission Pipeline Python sequence, or run it at the end of
  a coherent 30-60 minute recovery batch;
- during the batch, use focused unit tests and direct parser/builder probes;
- focused commits may be made after targeted validation; run the canonical
  rebuild once at the batch boundary before publishing generated WebUI data,
  documenting final counts, or declaring the batch complete;
- run an earlier canonical rebuild only when one cross-cutting parser/schema
  change cannot be validated safely with focused tests, installed-game inputs
  changed, generated Story/evidence is known stale, or the user explicitly
  requests it.

Treat generic validator failures as tooling gaps instead of repeatedly running
the expensive pipeline. Validators used by Story recovery must fail closed and
report actionable diagnostics:

- identify the validator, failed gate/check, affected mission or Story key, and
  source path;
- include bounded expected-versus-actual values and relevant source hashes;
- report at least the first failure deterministically, and preferably all
  independent bounded failures;
- expose the diagnostic in both structured report data and the CLI summary;
- add tests for the successful gate and for representative failure
  diagnostics whenever validator behavior changes.

Improve a validator's diagnostics before another full rebuild when its current
result is only a generic status such as `validation_failed`.

Steps that read the installed IL2CPP binaries gate on
`common.check_installed_native_inputs`, which resolves `GameAssembly.dll` and
`global-metadata.dat` from `ENDFIELD_GAME_ROOT`, then `endfield_paths.bat`,
then the export summary's `game_root`. Recorded native facts (method virtual
addresses, body hashes, field offsets) describe one specific client build, so
the gate reports `missing`, `mismatched`, or `validated`:

- an absent or different build skips only that step, with a one-line reason on
  stderr, and leaves its published report untouched; the rest of the pipeline
  is build-independent and still builds;
- a skipped step never emits unvalidated classifications, and each report's own
  source hashes still decide whether its recorded rows describe current data,
  so consumers stay fail-closed;
- set `ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` to restore hard failure when
  auditing the pinned build.

Useful direct commands:

```bat
python scripts\build_updates.py
python scripts\build_updates.py --text-only
python scripts\build_updates.py --no-audio
python scripts\build_updates.py --refresh-previous-export-baseline
python scripts\verify_export_freshness.py
python -m scripts.story_builder.refresh_evidence
python -m scripts.story_builder.source_links
python -m scripts.story_builder.build --languages CN --default-language CN
python -m scripts.story_builder.build --languages CN EN JP --default-language CN
python -m scripts.animestudio.generate_dummydll --dry-run
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay.py
python scripts\build_gameplay.py --stage projectiles
python -m scripts.story_recovery.build_option_override_coverage_audit --language CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\download_bilibili_video.py --dry-run
python scripts\pack_webui.py
```

`scripts/story_builder/build.py` currently takes about 3 minutes for the
default CN lean build on this checkout. Multi-language builds or forced
timeline recovery can take longer; when Codex runs this command directly, use a
longer shell timeout, such as 10-15 minutes (`timeout_ms` of at least
`900000`).

Unity character recovery lab:

```bat
cd endfield_reconstruction_lab
.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
```

The Python tooling is intended to stay stdlib-only unless a task explicitly
requires otherwise.

## WebUI Technical Notes

Keep detailed browser/export mechanics here, in project skills, or in code
comments. Keep `scripts/README.md` as a compact maintained workflow map and the
root `README.md` short and user-facing.

Browser behavior:

- Story/Text Tables inline media treats `sns_emoji_*` as regular inline emoji
  with no popup/modal preview.
- Non-emoji SNS media such as `sns_image_*` and `sns_sticker_*` render at
  normal image proportions with bounded hover/modal previews.
- Story recovery issue and method filters stay visible in every mode.
  Source/debug blocks, mission timeline evidence, cutscene debug panels, and
  manual order-edit controls are behind `Show debug info`.
- The Story reset button returns filters to Story sort while preserving
  expanded mission groups.
- Normal semantic navigation exposes Gameplay and Characters. Mission Pipeline
  is experimental and hidden unless the top-right `Show debug info` switch is
  enabled; disabling debug while it is active must normalize to a visible page
  and URL. The standalone Combat & Projectiles page is retired. Keep useful
  projectile behavior and playable sound links in Gameplay character skills;
  expose recovered character-skill and enemy SFX there as compact collapsed
  players with inferred ownership labeled;
  keep raw identity, source, matching, and unresolved ownership debug-only.
- Mission Pipeline Story cards show evidence-typed trigger chains. Preserve an
  explicit ownership gap for unlinked native playback, keep definition-only
  rows distinct, and never infer mission order from native registration or code
  address order.

Export freshness:

- `export.bat` runs `scripts/verify_export_freshness.py` before rebuilding
  from an existing `export_full/`.
- Run `python scripts\verify_export_freshness.py` directly when checking the
  guard, and pass `--game-root "...\Endfield_Data"` for non-default installs.
- If freshness reports stale source roots, rerun
  `.\export.bat --from-game` before Story or asset builders read
  `export_full/`.

Setup and export internals:

- The expected AnimeStudio CLI path is
  `tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.
- The AnimeStudio CLI provides the WebUI VFS commands `dump`, `audio`, `stream`,
  `vfs-index`, and `list`; `dump`, `audio`, `stream`, and `vfs-index` help should include
  `--fallback-assets <FALLBACK_ASSETS>`. `dump`, `stream`, and `vfs-index` accept repeated
  `--block-type` flags plus repeated `--file-regex` filters; `stream` exposes the
  same targeted VFS filtering for JSONL byte streaming.
- Installed-game Story exports use `--structured-dump-mode webui` by default:
  they dump only WebUI-consumed VFS blocks (`table`, `json-data`, and video)
  and skip raw asset bundles, audio PCK/media files, world-streaming bytes,
  irradiance volumes, extend-data bins, patch bytes, and Lua. `build_audio.py`
  streams Wwise bank metadata directly from VFS when relinking audio events.
  `--structured-dump-mode full` keeps the same production skip rules; use
  `--structured-dump-mode debug` only for broad VFS diagnostics.
- `export_assets.bat --from-game` (that is, `export.bat --assets-only
  --from-game`) passes `--skip-structured`, writes a
  lightweight VFS metadata index, runs WebUI-facing image/model/Material
  export, and decodes CN audio before relinking.
- `export.bat --from-game --with-assets` keeps the structured Story
  refresh and folds the asset export into the same AnimeStudio run.
- `tools\DummyDll` is the preferred repo-local IL2CPP DummyDll root when
  optional script-schema recovery is wanted. Wrapper flags or
  `ANIMESTUDIO_DUMMY_DLLS` can supply it, but missing or stale DummyDll paths
  must warn and continue without failing normal exports.
- `scripts\animestudio\generate_dummydll.py` is the maintained regeneration
  path. Run `--dry-run` first after a game update, then `--replace` only when
  script-derived schema recovery is needed. It discovers build-specific
  registrations, applies the maintained Cpp2IL patch, validates a staged
  complete DLL image set, retains the previous set, and writes
  `tools\DummyDll\generation.json`. Never reuse registration addresses from a
  previous installed build.
- `--animestudio-mono-behaviour-type-tree-priority script-first` is for
  targeted MonoBehaviour schema experiments; the default is `serialized-first`.
  Script-first must fall back cleanly when no usable DummyDlls are available.
- After installed-game refreshes, check `reports/export/export_full_summary.md` for
  stage return codes and AnimeStudio export errors.

Browser data inputs and outputs:

- Active inputs include `export_full/structured/StreamingAssets/Table/*.json`,
  recovered AnimeStudio text/metadata under `export_full/recovered/`,
  exported image/model/material outputs under
  `export_full/recovered/AnimeStudio-cli/<source>/`, and generated data under
  `webui/data/`.
- Generated browser outputs include `webui/data/manifest.json`,
  `webui/data/lang/<code>/index.json`, `conv/*.json`, `mission/*.json`,
  `reference/**`, `webui/data/mission_pipeline/index.json`,
  `webui/data/mission_pipeline/missions/*.json`, `webui/data/gameplay/projectiles.json`,
  `webui/data/lang/<code>/gameplay/projectile_audio.json`,
  `webui/data/lang/<code>/gameplay/sound_effects.json`,
  `webui/data/lang/<code>/characters/index.json`,
  `webui/data/lang/<code>/gameplay/combat_relationships.json`,
  `webui/data/assets/index.json`, `webui/data/assets/gameplay_refs.json`, and
  `webui/data/updates/latest.json`.
- The current `export.bat` skips raw VFS output and source inventory because
  the browser does not need them.

Tool pointers:

- `tools/AnimeStudio/` is the tracked AnimeStudio fork submodule used by
  installed-game Story and asset export paths. During audio or visual recovery,
  agents may patch this fork and its wrapper integration when doing so improves
  extraction quality, evidence coverage, or reproducibility. Keep changes
  narrowly scoped, validate them with the AnimeStudio workflow, and preserve
  existing fail-closed source/build gates.
- `tools/endfield_source_graph.py` builds/query local SQLite evidence across
  generated WebUI story/text-table data, selected tables, audio, videos,
  assets, material links, and optional AnimeStudio asset maps.
- `tools/endfield-il2cpp/` contains offline IL2CPP metadata diagnostics. It is
  not part of normal export, Updates, packaging, or serving flows.
- `tools/Endfield-map-extractor/` is an optional ignored research checkout,
  not a maintained WebUI dependency. Its BundleScanner/SceneProbe pipeline is
  a useful reference for recovering scene hierarchy, transforms, and the
  renderer-to-mesh/material/texture closure, but the current public workflow is
  specialized to Map01/Map02 and does not establish an `indie_dg002` or e0m0
  render. Review its PolyForm Noncommercial license before reusing code. Its
  game-root convention also names the directory containing `Endfield.exe`, not
  this repository's usual `Endfield_Data` value.
- Optional local vendor/tool caches may live under ignored `tools/`; keep their
  generated outputs local.

Script notes:

- `scripts/README.md` lists the maintained script map and workflow contracts.
- New one-off exploration scripts should start in `scratch/` or `tmp/`.
- Durable conclusions belong in the matching consolidated `memory/` topic;
  reusable helpers should move into maintained workflow code only with
  matching docs and intentional tracking.

## Memory Maintenance Rule

`memory/` is intentionally flat and limited to the topic files indexed by
`memory/README.md`. Treat those files as living sources of truth:

- update the current conclusion, evidence boundary, commands, and recovery
  queue in the owning topic;
- keep the topic concise; replace superseded conclusions instead of appending
  investigation chronology, native-address catalogs, hash inventories, or
  per-session proof logs;
- keep changing counts, exhaustive inventories, and generated audits in
  `reports/`, with only headline progress and durable interpretation in memory;
- keep disposable probes and intermediate output in `scratch/` or `tmp/`;
- add a new memory file only for a genuinely new durable topic, and update
  `memory/README.md`, this guidance list, and relevant active docs together.

The owning topics are WebUI, Story recovery, game-data recovery, semantic asset
recovery, AnimeStudio exporter recovery, and character render/animation
recovery. Cross-topic improvement plans should be split into the recovery
queues of those owning files rather than maintained as a second status source.

## Current Guidance Locations

The former exploration archive has been consolidated. Do not recreate duplicate
README-shaped or dated snapshots; update the current source of truth instead:

- user-facing active workflow: `README.md`
- agent-facing repo rules: `AGENTS.md`
- script/workflow contract: `scripts/README.md`
- WebUI frontend scope: `webui/README.md`
- memory topic index and writing rules: `memory/README.md`
- concise WebUI recovery status: `memory/webui_recovery.md`
- Story reconstruction conclusions: `memory/game_story_recovery.md`
- game-data formats, semantics, and source graph: `memory/game_data_recovery.md`
- semantic asset/entity recovery: `memory/asset_recovery.md`
- AnimeStudio exporter recovery: `memory/animestudio_recovery.md`
- character render/animation recovery: `memory/character_render_and_animation_recovery.md`

## Project Local Skills

Project-only Codex skills live under `.codex/skills/`. When a task matches one
of these workflows, open the matching `SKILL.md` before acting:

- `.codex/skills/endfield-webui-frontend/`: frontend behavior, routing, labels,
  styles, and page contracts.
- `.codex/skills/endfield-webui-serve-package/`: serving, smoke tests, and
  static packaging.
- `.codex/skills/endfield-story-recovery-build/`: Story/Text Tables and Story
  evidence builders.
- `.codex/skills/endfield-mission-pipeline-build/`: Mission Pipeline and map
  recovery Python builders.
- `.codex/skills/endfield-assets-audio-build/`: asset indexes, audio links, and
  gameplay sound sidecars.
- `.codex/skills/endfield-updates-build/`: Updates comparison feed.
- `.codex/skills/endfield-source-graph/`: source graph build/query and
  graph-backed follow-up reports.
- `.codex/skills/endfield-option-overrides/`: editing and validating
  WebUI-only manual option recovery overrides in
  `webui/overrides/options.json`.
- `.codex/skills/animestudio-workflow/`: building, running, patching, and
  debugging the local `tools/AnimeStudio` exporter and its WebUI wrappers.
- `.codex/skills/map-interactive-legend/`: regenerating and reviewing the
  offline map `detailId` legend under `reports/map_recovery/`.

`tools/EndfieldCapture/README.md` is the local usage guide for the optional
native observer. No WebUI, export, or recovery workflow requires
EndfieldCapture. When an investigation chooses to use it, the local environment
needs Windows x64, Visual Studio 2022 C++ build tools, CMake 3.23+, and an exact
installed Endfield build selected by `ENDFIELD_GAME_ROOT` or
`ENDFIELD_GAME_EXE`. Build and test it from the submodule with:

```bat
cmake -S tools\EndfieldCapture -B tools\EndfieldCapture\build-local -G "Visual Studio 17 2022" -A x64 -DBUILD_TESTING=ON
cmake --build tools\EndfieldCapture\build-local --config Release --parallel
ctest --test-dir tools\EndfieldCapture\build-local -C Release --output-on-failure
```

Use `tools\EndfieldCapture\StartCapture.bat` only with Endfield closed and
follow its exact-build, prelaunch, one-attachment, bounded-session, and
collection gates. It is observation-only: do not use it for shader/resource
overrides, draw suppression, input hooks, or game modification. Treat missing
modules, hash mismatches, hook errors, lost events, and incomplete provider
summaries as failed evidence. Keep raw sessions under
`scratch/reverse_engineering/endfield_capture/` and publish only compact,
validated findings under the owning report or memory topic.
During audio or visual recovery, agents may patch EndfieldCapture itself to
improve observation coverage, event fidelity, diagnostics, or collection
reproducibility, provided it remains observation-only and the exact-build,
bounded-session, failure-reporting, build, and test gates above remain intact.

The current checkout does not ship separate `endfield-story-recovery` or
`endfield-character-recovery-lab` skill folders. For those workflows, use the
active docs (`README.md`, `scripts/README.md`, `webui/README.md`, and
`endfield_reconstruction_lab/README.md`) plus the existing source-graph
skill when graph evidence is relevant.

The retired exploration snapshots were collapsed because they mixed active
workflow guidance with stale conclusions and repeated generated-report status.
Keep generated reports in `reports/`, concise durable conclusions in the six
owning memory topics, and disposable experiments in `scratch/` or `tmp/`.

## Update Tracking Rule

The WebUI Updates tab must report only exported game-data changes between a
saved previous export and the current export. By default it tracks the
exported JSON roots that feed Story/Text Tables display plus exported
image/model/video assets plus decoded audio. Use `--full-export-scan` only for
a broad audit of all files under the two export roots.

`build_updates.bat` reads the saved previous export and current export roots
from `endfield_paths.bat`
(`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT`). The underlying
`scripts/build_updates.py` defaults to comparing:

```text
export_1d2
export_full
```

when no wrapper config or explicit flags are supplied. The direct
two-extraction command that also generates the WebUI page is:

```bat
.\build_updates.bat OLD NEW
```

`OLD` is the saved extracted version and `NEW` is the current extracted
version; the pair must be the first arguments, and the wrapper adds
`--refresh-previous-export-baseline` for them. The long
`--previous-export-root PATH`/`--export-root PATH` flags remain available and
may override one side only. With no folder arguments, the wrapper uses its
configured defaults. Both complete export folders are required;
there is no first-time or installed-VFS tracking mode.
Scanner cache and feed history live under `.game-data-tracker/`; the cached
baseline is built from the previous export folder, then the current export root
is scanned against it using the same focused roots. Do not point this
comparison at `webui/`, `reports/`, `memory/`, or `scratch/`. WebUI edits and
generated output outside the export roots must not appear as game-data updates.

The builder scans exported assets in the same two export folders by default to
add image/model/video/audio asset-level entries to the Updates page. Asset
modifications use fast size fingerprints by default; pass `--exact` only when
same-size binary modifications must be detected. Use `--no-audio` when decoded
audio entries should be omitted while image/model/video entries remain
enabled. Use `--text-only` only when all asset entries should be omitted.
Use `--dry-run-prune-previous-export-untracked` to preview previous-export
files that exist byte-identically at the same relative paths in the current
export, and `--prune-previous-export-untracked` only when intentionally
deleting those old duplicate copies from the previous export folder. This
pruning must never target `export_full/` or the repo root. Through the wrapper
these are `build_updates.bat --prune-old --dry-run` and
`build_updates.bat --prune-old`.

Use `--refresh-previous-export-baseline` after replacing the saved previous
export folder so the cached scanner baseline is rebuilt.

## Repo Rules

- Prefer the layout rooted at `serve.py`, `export.bat`, `webui/`,
  `scripts/`, and `endfield_reconstruction_lab/`.
- Keep `README.md` focused on active WebUI usage and headline recovery
  progress. Preserve its screenshots, Chinese links, and acknowledgements.
- Keep active READMEs and memory topics concise. Put exhaustive implementation
  mechanics in code comments or focused generated reports, not long narrative
  appendices.
- Fold durable observations and conclusions into the matching consolidated
  `memory/` topic; do not add per-session or dated status files.
- Keep `reports/` for durable generated reports only, not agent conclusions or
  narrative writeups.
- Keep routine reports grouped by topic: exporter summaries, run logs, and
  benchmarks under `reports/export/`; Story build summaries under
  `reports/story/build/`; manual Story recovery evidence under
  `reports/story/recovery/`; update summaries under `reports/updates/`; and
  asset diagnostics under `reports/assets/`. Do not add loose report files at
  the `reports/` root.
- Keep the roots of `scratch/` and `tmp/` free of loose files and one-off run
  directories. Write experiments as `scratch/<topic>/<task>/` and disposable
  intermediates as `tmp/<topic>/<task-or-run>/`. Prefer the active topic names
  `webui`, `story`, `assets`, `animestudio`, `source_graph`,
  `character_recovery`, `game_data`, `updates`, `ocr`, and
  `reverse_engineering`; use `tests`, `tools`, or `misc` only when needed.
- Use `scratch/` for attempts, tool prototypes, and generated previews that may
  be revisited. Promote reusable helpers to maintained code or delete stale
  experiments.
- Use `tmp/` for disposable results and intermediates. Remove completed run
  directories after validation, and never cite `tmp/` as durable evidence.
- For self-contained `ue5_*` or `unity_*` projects, prefer that project's own
  scratch/temp area instead of the repo-root work directories.
- Put durable shared helper code under the maintained script/tool surface.
  `tools/` is ignored by default except for already tracked helper scripts, so
  new promoted tools need intentional tracking and documentation.
- Local vendor/tool caches may live under ignored `tools/`. `tools/Ruri.ShaderDecompiler`
  is historical migration evidence only; do not pull it, build it, or add new
  AnimeStudio dependencies on it. Preserve it locally until the AnimeStudio
  shader-recovery fixtures and downstream verifiers certify the replacement.
- Keep `ue5_*` and `unity_*` directories self-contained. Code, assets, generated
  files, and helpers related to those projects should live inside the matching
  project folder.
- Preserve narrow, surgical changes when adjusting exporters or builders.
- Do not promote an ad-hoc script into `scripts/` unless it supports WebUI or
  `endfield_reconstruction_lab`.

## Active Script Groups

WebUI:

- `scripts/export_full_from_game.py`
- `scripts/build_webui_views.py`
- `scripts/story_builder/dialog_registry.py`
- `scripts/story_builder/video_bindings.py`
- `scripts/verify_export_freshness.py`
- `scripts/story_builder/refresh_evidence.py`
- `scripts/build_updates.py`
- `scripts/story_builder/source_links.py`
- `scripts/story_builder/build.py`
- `scripts/story_builder/timeline_action_evidence.py`
- `scripts/story_builder/lua_consumer_references.py` (canonical fingerprinted
  Lua consumer index read directly by Mission Pipeline; refresh requires an
  explicit plaintext-Lua extraction)
- `scripts/build_character_data.py`
- `scripts/build_gameplay.py` (every Gameplay page dataset; stage modules in
  `scripts/gameplay_builder/`; its `asset-refs` stage directly calls the public
  `asset_builder.gameplay_refs` API and solely owns `gameplay_refs.json`)
- `scripts/build_mission_pipeline_data.py`
- `scripts/build_assets.py`
- maintained stdlib-only MemoryPack codecs live under
  `scripts/game_data/memorypack/`. The retired Data, Factory, World, and
  Presentation page builders remain removed; do not restore those pages or
  their generated outputs.
- `scripts/build_audio.py`
- `scripts/build_audio_semantics.py` is the Audio page orchestrator/publisher;
  reusable Audio evidence owners live under `scripts/audio_semantics/`
- `scripts/pack_webui.py`
- supporting files in `scripts/` and `scripts/asset_builder/`

Story reconstruction helpers used by WebUI builders:

- `scripts/story_builder/native_contracts/` (reviewed current-build native
  facts consumed by builders; recovery hooks must reference or validate these
  contracts rather than duplicate them)
- `scripts/story_builder/timeline_recovery.py`
- `scripts/story_builder/timeline_action_evidence.py`
- `scripts/story_builder/mission_recovery.py`
- `scripts/scene_order_gap_shared.py`

Story recovery audit/refresh tools, not run by `export.bat`:

- `scripts/story_recovery/`
- native carrier audits use the single
  `scripts/story_recovery/audit_native_carriers.py` profile CLI; reusable
  scanner/profile code and versioned negative boundaries live in
  `scripts/story_recovery/native_carriers/`
- `scripts/download_bilibili_video.py` is an optional gameplay-video intake
  helper for the OCR/audio story-order workflow. It requires `requests`,
  `ffmpeg`, and browser-exported Bilibili cookies, writes complete `.mp4` files
  under `videos/`, and is not part of the stdlib-only export path.

Unity character recovery lab:

- project-local scripts under `endfield_reconstruction_lab/`

The old archived-script bucket has been retired. Do not recreate it; put
disposable scripts in `scratch/` or `tmp/`, and promote only maintained
workflow code.
