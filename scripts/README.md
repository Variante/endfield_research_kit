# Scripts

This directory contains the maintained exporters and builders for the static
WebUI. Use the root wrappers for normal work; call Python entry points only for
focused development or validation.

This file is the command and module-ownership map. What the recovered evidence
*means* is not here: it belongs to the two memory axes --
[`memory/game_data/`](../memory/game_data/README.md) for how the original binary
is understood, and [`memory/webui/`](../memory/webui/README.md) for how that data
reaches a page.

## Layout

The tree follows the same split: two lines of work, each mirroring one memory
axis. A path appears under exactly one owner.

| Line | Path | Responsibility |
| --- | --- | --- |
| **1. Game data** | `game_data/extraction/` | installed client to `export_full/`: the export and changed-file exporters, freshness guard, export benchmark, AnimeStudio object index, and `animestudio/` maintenance commands; never publishes page data |
| | `game_data/` | exact framing readers (including `terrain_tret.py`, `terrain_height.py`, `dynamic_streaming.py`), `*_corpus.py` gates, `*_native.py` validators and their reviewed contracts, `il2cpp_protocol.py`, `il2cpp_context*.py` |
| | `game_data/memorypack/` | MemoryPack codecs and their corpus gates |
| **2. WebUI** | `webui/views.py`, `webui/package.py` | page-build orchestration, and packaging |
| | `webui/story/` | Story and Text page data plus shared Story evidence, including `native_contracts/` |
| | `webui/story_recovery/` | Story audits, OCR ordering, runtime traces, candidate generation |
| | `webui/mission_pipeline/` | standalone Mission Pipeline recovery (not a WebUI page) |
| | `webui/{assets,audio,characters,gameplay,map,updates}/` | one folder per page: its `build_*.py` entry point and helper modules |
| **Shared** | `common.py`, `source_paths.py`, `repo_paths.py` | helpers used by both lines; `repo_paths.REPO_ROOT` is the only repo-root anchor |
| **Tests** | `tests/` | stdlib `unittest`, untracked, run by explicit module path |

Three rules keep that split honest. Line 1 never writes under `webui/data/`.
A production builder must not import or execute a recovery/audit module. A
corpus gate or native validator is tracked because the sweep is reusable,
while everything it emits goes to `reports/`.

Every entry point runs as a module from the repository root, e.g.
`python -m scripts.webui.audio.build_audio`. Imports are absolute
(`from scripts.… import`), and nothing computes the repo root from its own
depth, so moving a file changes only the paths that name it. A documented entry
point run directly as a file exits with the `python -m` command to use instead.

## Root workflows

| Goal | Command |
| --- | --- |
| First-time Story/Text setup | `.\setup.bat` |
| Rebuild from the current export | `.\export.bat` |
| Refresh Story from the game | `.\export.bat --from-game` |
| Refresh Story and assets together | `.\export.bat --from-game --with-assets` |
| Refresh changed local game files and all WebUI views, excluding Updates | `.\export.bat --changed-only` |
| Story recovery loop | `python -m scripts.webui.story.build --languages CN --default-language CN` |
| Mission Pipeline recovery (standalone, not WebUI) | `python -m scripts.webui.mission_pipeline.build_mission_pipeline_data --refresh-source-story-gap-queue` |
| Rebuild post-Story views, assets, and CN audio | `.\export_assets.bat` |
| Refresh assets/audio and rebuild post-Story views | `.\export_assets.bat --from-game` |
| Compare exports for Updates | `.\build_updates.bat OLD NEW` |
| Serve or package | `python serve.py` / `python -m scripts.webui.package` |

The wrappers load `endfield_paths.bat`, then apply explicit path flags. Run any
wrapper with `--help` for its supported options.

The maintained Terrain structure gate is
`python -m scripts.game_data.terrain_corpus`; it consumes a completed VFS audit
summary/ledger plus that audit's exact `inputSetSha256`, revalidates the pinned
current native consumer contract, and writes
`reports/animestudio/terrain_tret_latest.{json,md}`. It is a focused recovery
command, not part of normal WebUI export.

The maintained DynamicStreaming `stream_area` gate is
`python -m scripts.game_data.dynamic_stream_area_corpus --expected-input-set-sha256 INPUT_SET_SHA256`.
It revalidates the authenticated outer VFS inputs, streams only current
`FBStreamArea.bytes` files, checks every payload against its ledger identity,
and writes `reports/animestudio/dynamic_stream_area_current_latest.{json,md}`.
It bounds the root fields and requires the greatest vector end to equal payload
EOF; gaps between offsets and record contents remain unassigned.

For the recovery path and evidence boundary of an individual WebUI page, use
[`memory/webui/README.md`](../memory/webui/README.md). This file remains the
command and module-ownership map.

`setup.bat` initializes only the required `tools/AnimeStudio` submodule.
`tools/Cpp2IL-Endfield`, `endfield_reconstruction_lab`, and
`tools/EndfieldCapture` are optional and are not needed for the normal WebUI
build. The DummyDll generator initializes Cpp2IL-Endfield on demand when
script-schema recovery needs it.

## Export rules

`export.bat` is the canonical Story, Text, Characters, Gameplay, and generated
WebUI rebuild. It reads the current `export_full/` by default and runs
`verify_export_freshness.py` before downstream builders. Use `--from-game` only
when the extraction must be refreshed from the installed client.

**Every wrapper prints its own option list**, so run `--help` for the flag
surface. Only the behaviour `--help` does not give you is recorded here:

- `--changed-only` implies `--from-game --with-assets`. It compares focused
  structured VFS logical files by decoded MD5, length, type, path and
  encryption identity, applies only the delta, then runs the *complete* normal
  WebUI build. It never touches Updates -- no baseline change, no entry. Its
  private snapshot under
  `export_full/recovered/AnimeStudio-cli/local_incremental/` advances only
  after every builder succeeds, so a late failure retries from the applied
  files rather than needing an older audit snapshot.
- `--story-only` and `--assets-only` are mutually exclusive.
  `--assets-only` implies `--with-assets` and skips Story evidence, Story and
  Text Tables; `export_assets.bat` is the thin wrapper that adds it.
- `--skip-freshness` bypasses the guard for one run. It does not refresh stale
  source data -- use it only when the existing export is known compatible.
- `--webui-jobs N` also supplies the Map data/streaming worker count. A run
  that rebuilds assets pins Map to one worker so it cannot contend with
  image/model conversion for disk and memory.
- `--full-source-graph` adds exhaustive Unity-object/PathID work; the default
  graph carries only rows consumed by WebUI edges.
- Asset scope runs narrowest to broadest: `--focused-assets` (WebUI-referenced
  `Texture2D` only), `--default-assets` (WebUI-facing image/model/material/
  animation output plus audio callback-ownership inputs), `--debug-assets`
  (broad conversion and JSON for investigation).
- The default asset scope includes AnimationClip conversion plus
  AnimatorController and AnimatorOverrideController JSON. Controller JSON stays
  on the broad dependency-loading path so cross-bundle PPtr targets are not
  silently withheld.

`setup.bat` runs `export.bat --from-game --story-only
--animestudio-story-monobehaviour-names` for its first-time Story build, then
prints the optional asset and semantic-view follow-ups; `--no-serve` finishes
without starting `serve.py`.

`ENDFIELD_EXPORT_ROOT` reaches extraction as `--output` and builders as
`--export-root`, so both halves of a run use one tree. Installed-game-only
flags fail with an explanation when `--from-game` is absent rather than being
dropped. Keep wrapper files CRLF: `cmd.exe` mis-resolves backward `goto` in
LF-only batch files.

Every export records build-step timings and a process-tree benchmark under
`reports/export/`. The Combat builder rejects stale graph inputs and publishes
a degraded reason instead of using them as direct evidence.

## Main builders

| Area | Entry point | Main output |
| --- | --- | --- |
| Extraction | `export_full_from_game.py` | `export_full/` |
| Local logical-file delta | `export_changed_game_data.py` | changed structured files and private snapshot |
| Export freshness | `verify_export_freshness.py` | validation result |
| WebUI orchestration | `webui/views.py` | semantic page data |
| Story evidence | `webui/story/refresh_evidence.py` | `reports/story/` evidence |
| Story links | `webui/story/source_links.py` | localized reference data |
| Story | `webui/story/build.py` | `webui/data/lang/<LANG>/` |
| Mission Pipeline recovery | `build_mission_pipeline_data.py` | standalone recovery reports/data |
| Map | `export.bat` runs map data, then `recover_map_streaming_instances.py --all-published-map-scenes`, then preview publication; a sidecar failure stops the phase instead of silently degrading to registry points. The recovery streams installed-game `InitChunkData` through AnimeStudio.CLI and joins the exported AssetMap/Mesh; colored output additionally needs Material JSON and Texture2D from the default asset scope. `build_map_recovery_data.py --with-preview` remains the direct data/preview path, while `--preview-only` reuses current map data and sidecars. `--jobs N` bounds both the per-level data workers and preview processes; maps sharing one exact Streaming scene remain together so their shared bounds and outputs cannot race. Preview rendering checkpoints each completed exact streaming, point, and inferred HLOD render under `reports/assets/map_recovery/render_cache/`; matching map, matrix, mesh, material, texture, renderer-index, bounds, density, and renderer-version inputs reuse the published PNG/sample set across runs. Missing outputs or changed inputs invalidate only that checkpoint, and the CLI reports cache hits/writes; pass `build_map_recovery_preview.py --no-render-cache` for a forced rerender. `--refresh-exact-fallbacks-only` cheaply refreshes registry/quest point fallbacks. | `reports/assets/map_recovery/terrain_height_index.json`, `export_full/recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/`, `reports/assets/map_recovery/`, `webui/data/map_recovery/` |
| Map01 RegionMap3D package | `build_map_region3d.py` | a self-contained package plus its provenance sidecar; separate from the WebUI map renderer and the authored 2D minimap |
| Lua consumer index | `webui/story/lua_consumer_references.py` | fingerprinted Mission Pipeline evidence |
| Characters | `build_character_data.py` | character indexes and versioned final-catalog snapshots |
| Gameplay | `build_gameplay.py` | Gameplay datasets |
| Assets | `build_assets.py` | asset indexes and media lookup |
| Audio | `build_audio.py` | decoded/relinked audio data |
| Audio semantics | `build_audio_semantics.py` | compact Audio page evidence and shards |
| Audio HIRC structural gates | `webui/audio/semantics/hirc_action_corpus.py` | Action cursors and type `0x02` source prefixes under `reports/animestudio/` |
| DynamicStreaming stream-area gate | `game_data/dynamic_stream_area_corpus.py` | `reports/animestudio/dynamic_stream_area_current_latest.{json,md}` |
| Updates | `build_updates.py` | `webui/data/updates/latest.json`, `webui/data/updates/characters.json` |
| Packaging | `webui/package.py` | distributable static package |

### Packaging

`webui/package.py` emits four archives -- main, `-media`, `-audio` and an optional
`-resources`. What each one owns and why they publish in that order is a
publication contract:
[`../memory/webui_recovery.md`](../memory/webui_recovery.md).

Select any subset with one comma-separated positional argument; the given order
is the build/publication order. With no argument all four are built:

```bat
.\pack_webui.bat story,audio,media,resource
.\pack_webui.bat resource
.\pack_webui.bat media,audio
.\pack_webui.bat story --dry-run
```

### Gameplay datasets

`build_gameplay.py` owns every Gameplay dataset. Behavior-focused stages live
in `webui/gameplay/`; its `asset-refs` stage calls the public
`webui.assets.gameplay_refs` API with the current Gameplay and Assets indexes
and is the sole writer of `webui/data/assets/gameplay_refs.json`.
What those datasets establish, and the registry/tag join rules they obey, are
in [`../memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md).

When the serialized registry is incomplete, capture the live current-build
registry before rebuilding the base stage. Start the capture first so it can
attach during client startup, then load the title/menu or a gameplay scene:

```bat
tools\frida-runtime\venv\Scripts\python.exe -m scripts.webui.gameplay.capture_runtime_tags --duration 600 --output scratch\reverse_engineering\gameplay_tag_runtime\capture.jsonl
python -m scripts.webui.gameplay.build_gameplay --stage base --languages CN --default-language CN --runtime-tag-capture scratch\reverse_engineering\gameplay_tag_runtime\capture.jsonl
```

The capture is read-only and refuses to attach unless the selected
`GameAssembly.dll` and `global-metadata.dat` match the pinned current-build
hashes. Runtime rows are merged only when that same native-input gate is
validated; otherwise the static export remains unchanged. Use `--check-only`
to verify the hook manifest without attaching.
`build_assets.py` writes only Assets-owned indexes and media lookup. The legacy
economy, world, presentation, and broad data index helpers are diagnostic only
and do not feed active pages.

### Focused commands

```bat
python -m scripts.game_data.extraction.verify_export_freshness
python -m scripts.webui.story.refresh_evidence
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
python -m scripts.webui.characters.build_character_data --languages CN --default-language CN
python -m scripts.webui.mission_pipeline.build_mission_pipeline_data
python -m scripts.webui.gameplay.build_gameplay
python -m scripts.webui.assets.build_assets
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
python -m scripts.webui.package
```

### Offline recovery probes

AnimeStudio offline recovery probes:

```bat
set ASCLI=tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
%ASCLI% vfs-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --summary-json reports\animestudio\vfs_understanding_latest.json --ledger-jsonl-gz reports\animestudio\vfs_understanding_files_latest.jsonl.gz --report-md reports\animestudio\vfs_understanding_latest.md
python -m scripts.game_data.streaming_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming_marker17_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming_marker13_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming_marker2_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.skill_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output reports/animestudio/skilldata_current_latest.json --output-md reports/animestudio/skilldata_current_latest.md
python -m scripts.game_data.memorypack.skill_cursor_receipt --preflight
python -m scripts.game_data.memorypack.skill_timeline_cursor --stream-jsonl CURRENT_SKILLDATA_STREAM_JSONL --native-context reports/animestudio/il2cpp_context_current_latest.json
python -m scripts.game_data.memorypack.npc_montage_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.buff_1b_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.lipsync_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
%ASCLI% shader-recover --input PATH_TO_SPIRV --output PATH_TO_HLSL
%ASCLI% inspect-object --index OBJECT_INDEX.jsonl --path-id PATH_ID --source SOURCE --type TYPE
%ASCLI% audit-refs --index OBJECT_INDEX.jsonl
%ASCLI% certify-index --index OBJECT_INDEX.jsonl
%ASCLI% replay --index OBJECT_INDEX.jsonl --requests RECOVERY_REQUESTS.jsonl
%ASCLI% schema-diff --left LEFT.json --right RIGHT.json
```

These are bundle-free, fail-closed diagnostics. `vfs-audit` streams each
selected physical chunk once and intentionally returns non-zero for any missing
or unauthenticated declaration while still publishing its terminal ledger.
Each gate reauthenticates the outer VFS ledger before it publishes, and writes
its result under `reports/animestudio/`:

| Gate | Publishes |
| --- | --- |
| `game_data.streaming_corpus` | `streaming_root_subgraphs_latest.{json,md}` |
| `game_data.streaming_marker17_corpus` | `streaming_marker17_bodies_latest.{json,md}` |
| `game_data.streaming_marker13_corpus` | `streaming_marker13_latest.{json,md}` + inventory `.jsonl.gz` |
| `game_data.streaming_marker2_corpus` | `streaming_marker2_latest.{json,md}` + inventory `.jsonl.gz` |
| `game_data.memorypack.skill_corpus` | `skilldata_current_latest.{json,md}` |
| `game_data.memorypack.skill_timeline_cursor` | `skilldata_timeline_cursor_latest.{json,md}` |
| `game_data.memorypack.npc_montage_corpus` | `npc_montage_current_latest.{json,md}` |
| `game_data.memorypack.buff_corpus` | `buffdata_current_latest.{json,md}` |
| `game_data.memorypack.buff_1b_corpus` | `buff_1b_current_latest.{json,md}` |
| `game_data.memorypack.lipsync_corpus` | `lipsync_current_latest.{json,md}` |
| `game_data.terrain_corpus` | `terrain_tret_latest.{json,md}` |
| `game_data.dynamic_stream_area_corpus` | `dynamic_stream_area_current_latest.{json,md}` |
| `game_data.il2cpp_context_audit` | `il2cpp_context_current_latest.*` (JSON on stdout) |

Partial `--max-files` probes are not complete-corpus evidence and their output
belongs in `tmp/` or `scratch/`. **What each gate proves, and what it explicitly
leaves unresolved, is in
[`memory/game_data/extraction_payload_boundaries.md`](../memory/game_data/extraction_payload_boundaries.md)**
-- do not restate a boundary here.

Object indexes may be JSONL or
`.jsonl.gz`; `certify-index` requires a complete terminal summary row, `replay`
uses one `{ "pathId": N, "source": "...", "type": "..." }` request per line,
and `schema-diff` compares shape rather than values. Keep probes and request
fixtures under `scratch/animestudio/`; promote stable results to the matching
`reports/` topic. See `memory/game_data/extraction_pipeline.md` for the Ruri retirement
gate and shader fixture requirements.

Direct Story builds take several minutes. Allow at least 15 minutes for the
shell command, especially for multiple languages or forced Timeline recovery.

## Story recovery

Production parsing, validation, attachment, and generated schemas live in
`webui/story/`. Audit and candidate-generation tools live in
`webui/story_recovery/`; they may import stable builder primitives, but production
builders must not import or execute recovery modules.

The reconstruction helpers WebUI builders depend on:

| Module | Owns |
| --- | --- |
| `webui/story/refresh_evidence.py` | Story evidence refresh |
| `webui/story/source_links.py` | localized reference data |
| `webui/story/build.py` | the Story page data itself |
| `webui/story/dialog_registry.py` | dialog id registration |
| `webui/story/video_bindings.py` | Story-to-video bindings |
| `webui/story/timeline_recovery.py` | Timeline recovery |
| `webui/story/timeline_action_evidence.py` | typed Timeline action evidence |
| `webui/story/mission_recovery.py` | mission reconstruction |
| `webui/story/lua_consumer_references.py` | the fingerprinted Lua consumer index |
| `webui/story/native_contracts/` | reviewed current-build native facts |
| `scene_order_gap_shared.py` | shared scene-order gap logic |

Mission Pipeline is a standalone recovery/reporting workflow; the WebUI export
does not run it. It reads the canonical shipped-Lua consumer index through
`webui.story.lua_consumer_references`; it does not consume a recovery-script
artifact. Cinematic-handle classification and typed action-producer joins come
from the reviewed, installed-build-gated
`webui/story/native_contracts/cinematic_queue.json`; the full native carrier
report is not a production input. Standard WebUI extraction intentionally
omits Lua, so refresh this tracked index only from an explicit complete
plaintext-Lua extraction. To refresh it and optionally render Markdown, run:

```bat
python -m scripts.webui.story.lua_consumer_references --markdown
```

To refresh and reconcile the optional full cinematic native audit against the
compact contract, run
`python -m scripts.webui.story_recovery.audit_native_carriers cinematic`. Use
`--skip-contract-reconciliation` only while reviewing a new installed build
before intentionally updating the versioned contract.

`webui/story/source_gap/` owns the canonical source-only Story gap queue.
Mission Pipeline refreshes it through the in-process builder API; it is not a
recovery-script subprocess.

Work in small validated batches:

1. Use focused unit tests and parser probes while generated Story inputs are current.
2. After at least three independent changes, or at the end of a coherent
   30–60 minute batch, run the direct Mission Pipeline Python sequence.
3. Rebuild earlier only for changed installed inputs, stale generated data, or
   a cross-cutting schema change that focused tests cannot validate.

Reuse Timeline order and localized references only through the direct Story
builder when their inputs are unchanged. These options are not accepted by
`export.bat` and must not be used with `--from-game`.

Validators fail closed. A failure must name the validator, gate, affected
mission or Story key, source path, bounded expected/actual values, and relevant
hashes in both structured output and the CLI summary.

Review manual option coverage, stale targets, and current generated response
candidate conflicts with the single maintained option audit:

```bat
python -m scripts.webui.story_recovery.build_option_override_coverage_audit --language CN
```

Manual Story order is user-managed in `webui/overrides/story_order.json`.
OCR writes proposals to `webui/data/story_order_ocr.json`; exports never replace
the active override.

Gameplay-video OCR uses one command surface. `sample` extracts OCR evidence,
`match` builds an OCR-only order proposal, `publish` refreshes the compact
WebUI reference, and `compare` reports differences without editing the active
override:

```bat
python -m scripts.webui.story_recovery.ocr_story_order sample --dry-run
python -m scripts.webui.story_recovery.ocr_story_order match
python -m scripts.webui.story_recovery.ocr_story_order publish
python -m scripts.webui.story_recovery.ocr_story_order compare
```

AnimeStudio Story-object recovery uses one staged audit. `reverse` publishes
the fail-closed playback-alias evidence consumed by builders; `carrier` and
`hierarchy` remain optional candidate diagnostics, and `all` runs the three in
dependency order:

```bat
python -m scripts.webui.story_recovery.audit_story_objects --stage reverse
```

Native value-carrier work also uses one profile command. `generic` is the
importable type/field-driven scanner, `cinematic` retains the structural queue
contract and its existing report paths, and `radio-forbid` validates the small
versioned negative boundary recorded for the pinned build:

```bat
python -m scripts.webui.story_recovery.audit_native_carriers generic --carrier-type TYPE --focus-field FIELD
python -m scripts.webui.story_recovery.audit_native_carriers cinematic
python -m scripts.webui.story_recovery.audit_native_carriers radio-forbid
```

Reusable implementations and the radio boundary live under
`webui/story_recovery/native_carriers/`; tests live under `scripts/tests/` rather
than beside recovery tools.

Mission and audio runtime traces share one fail-closed CLI while retaining
separate hook manifests, Frida agents, schemas, and evidence boundaries:

```bat
tools\frida-runtime\venv\Scripts\python.exe -m scripts.webui.story_recovery.runtime_trace capture --profile mission
tools\frida-runtime\venv\Scripts\python.exe -m scripts.webui.story_recovery.runtime_trace capture --profile audio
python -m scripts.webui.story_recovery.runtime_trace import --profile mission CAPTURE.jsonl
python -m scripts.webui.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl
```

To publish a verified imported capture onto the Audio Event/media detail rows,
rerun the semantic publisher with its JSON bundle:

```bat
python -m scripts.webui.audio.build_audio_semantics --language CN --runtime-trace-bundle reports\story\recovery\audio_runtime_trace.json
```

The projection requires the bundle's current schema, matching language, and
verified GameAssembly path/size/SHA-256 facts. It records observed managed
request boundaries and exact Event-to-media relations, but never promotes a
capture to selected Wwise branch, decoded leaf, or audibility evidence.

The reviewed LevelScript task paths are builder-owned in
`webui/story/native_contracts/mission_task_paths.json`. The protocol registry
reads that contract directly; the mission runtime hook manifest references and
validates the same contract before rendering its Frida agent, so task RVAs,
message IDs, and field offsets have one mutable source of truth.

## Assets and audio

### Wrapper selection

Prefer `export.bat --from-game --with-assets` when Story and assets both need a
fresh extraction; it folds the asset export into one AnimeStudio run. When
generated Story is already current, `export_assets.bat --from-game` refreshes
assets/audio and rebuilds map recovery, Characters, Gameplay/projectiles, the
curated source graph, and combat relationships; plain `export_assets.bat`
rebuilds the same post-Story views while reusing existing decoded assets and
audio. Mission Pipeline is not one of those builders -- run its direct Python
command separately.

`export_assets.bat` is a thin wrapper around `export.bat --assets-only`, so it
shares one option parser, runs `verify_export_freshness.py`, and writes a
benchmark under `reports/export/benchmarks/` with an `export_assets_` label.
Asset-only installed-game extraction leaves structured Story/Table outputs
untouched and preserves their previous source fingerprints, recording its own
asset scan separately, so it cannot make stale Story data pass the freshness
guard after a client update.

### AnimeStudio scheduling, DummyDlls, and managed-reference diagnostics

The default AnimeStudio type-job mode is `auto`: map-filtered conversion stays
sharded, while broad Story JSON runs in isolated sequential processes. Do not
add a JSON type to map filtering until broad and filtered exports are
byte-diffed, and do not shard JSON export without new measurements; current
results show disk contention rather than a speedup.

Optional DummyDll regeneration is build-specific:

```bat
python -m scripts.game_data.extraction.animestudio.generate_dummydll --dry-run
python -m scripts.game_data.extraction.animestudio.generate_dummydll --replace
```

The generator consumes a tag-and-commit-pinned release from
`Variante/Cpp2IL-Endfield`; Cpp2IL compatibility changes are released there
before the local pin moves, and it does not apply an in-repo source patch.
Missing or stale DummyDlls warn and fall back to serialized schemas. Never
reuse native registration addresses across game builds.

Managed-reference schema work can opt into a separate fail-closed JSONL sidecar
without changing normal JSON or object-index output:

```bat
python -m scripts.game_data.extraction.export_full_from_game --skip-structured --sources Persistent --animestudio-scope story --animestudio-stages json_by_type --animestudio-managed-reference-diagnostics
python -m scripts.game_data.extraction.export_full_from_game --skip-structured --sources Persistent --animestudio-scope story --animestudio-stages json_by_type --animestudio-managed-reference-diagnostics --animestudio-managed-reference-diagnostic-type "AbilitySystemData$"
python -m scripts.game_data.extraction.export_full_from_game --skip-structured --sources Persistent --animestudio-scope story --animestudio-stages json_by_type --animestudio-managed-reference-diagnostics --animestudio-managed-reference-diagnostic-type "AbilitySystemForEnemyPartData$" --animestudio-managed-reference-diagnostics-include-exact-matches
```

Each MonoBehaviour worker writes a unique atomic part under
`export_full/recovered/AnimeStudio-cli/<source>/managed_reference_diagnostics/parts/`.
Only partial managed references are included by default; repeat
`--animestudio-managed-reference-diagnostic-type` to constrain capture by
`assembly::namespace.class` regex, and
`--animestudio-managed-reference-diagnostics-include-exact-matches` requires at
least one explicit type filter before it adds exact matches for those
identities. The option set is rejected outside Story/all MonoBehaviour JSON
scope. Rows carry exact object/RID/type identity, payload offset/length,
SHA-256, bounded full base64 payload, focused-decoder failure cursors, and the
serialized file's matching script/type hashes plus bounded full TypeTree node
list when it has one, tying field order to the asset's serialized schema rather
than runtime metadata alone. Payloads up to the explicit 1 MiB per-record cap
include full base64 bytes; larger rows keep their exact range/hash with
`truncated=true` and omit base64. A final file is published only after a
successful worker and ends with a complete terminal summary; absent, temporary,
truncated, errored, or incomplete parts are not evidence.

### Audio decode and Wwise indexing

`build_audio.py` owns decode, Wwise bank/HIRC indexing, relinking, and the
Gameplay sidecars. It writes shared SFX/music once under
`export_full/structured/Audio/shared/` and language voice under
`export_full/structured/Audio/<LANG>/`.

```bat
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
```

AnimeStudio streams decoded PCM into lossless FLAC without intermediate WAV
files or `ffmpeg`; decode and WebUI output are FLAC-only, so existing WAV/WEM
files stay readable on an index-only maintenance run but are no longer produced
or converted. WEM decoding uses the pinned 64-bit vgmstream CLI, installed by
`setup.bat` under `tools/vgmstream/` or directly by
`scripts\game_data\extraction\animestudio\setup_vgmstream.bat`. `--skip-decode --refresh-hirc` gives
a fresh HIRC bank pass while decoded audio is already current; plain
`--skip-decode` reuses the existing event-media/HIRC cache. Use direct
`build_audio.py` runs for non-CN languages or audio-only maintenance.

Projectile behavior and authored event hashes stay immutable in
`webui/data/gameplay/projectiles.json`; Audio publishes playable HIRC candidates
separately in `webui/data/lang/<LANG>/gameplay/projectile_audio.json`.

### HIRC structural corpus gates

Both gates are current-corpus bound: pass the exact `inputSetSha256` from
`reports/animestudio/vfs_understanding_latest.json` as the required
`--expected-input-set-sha256` argument.

```bat
python -m scripts.webui.audio.semantics.hirc_action_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.webui.audio.semantics.hirc_named_reach --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
```

`hirc_action_corpus` binds verified package MD5/chunk/physical-source identities
and per-bank cursor totals to the authenticated outer ledger, hashes a sorted
path/length/SHA-256 manifest of the CLI output directory before and after the
audit, and hashes the exact intermediate JSON bytes it parses. It publishes:

```text
reports/animestudio/hirc_action_current_latest.{json,md}
reports/animestudio/hirc_type02_prefix_current_latest.{json,md}
reports/animestudio/hirc_type04_u32_vector_current_latest.{json,md}
reports/animestudio/hirc_type02_body_current_latest.{json,md}
reports/animestudio/hirc_type05_body_current_latest.{json,md}
reports/animestudio/hirc_type07_body_current_latest.{json,md}
reports/animestudio/hirc_reference_graph_current_latest.{json,md}
```

The body lanes share one framer, census, metrics reader, renderer, and
publisher. Every lane enforces its own closure -- a failed, unsupported, or
ambiguous body publishes `incomplete` and exits nonzero -- and every lane
publishes the same shared-framer residual list. Adding a numeric type means one
more lane and one more framer, not another copy of the census.

`hirc_named_reach` is the naming lane: it hashes the exact audio-like
`stringLiteral` rows from the selected `global-metadata.dat`, joins them to HIRC
object identities, walks reference vectors to the source ids a named object
reaches, and runs a second broad pass scored against a computed coincidence
rate. It refuses to publish when a gated match lands on an unexpected type,
when a count and its id list describe different walks, or when nothing clears
the bar. What each lane's framing does and does not establish is a durable
conclusion in
[`memory/game_data/audio_overview.md`](../memory/game_data/audio_overview.md)
and the HIRC files beside it; do not restate a framing claim here.

### Audio semantics: orchestration and domain ownership

`build_audio_semantics.py` is the thin orchestration/publishing surface for the
Audio evidence page; page data changes only after a formal semantic rebuild
(normally `export.bat`, or the targeted run below).

```bat
python -m scripts.webui.audio.build_audio_semantics --language CN
```

Maintained domain code lives under `webui/audio/semantics/`: `native_evidence.py`
(installed-build gate), `identifiers.py` (Wwise hashes and managed string
identities), `managed_literals.py` (managed literal and MonoBehaviour
audio-field contexts), `responsive_voice.py` and `voice_requests.py` (their
respective consumer evidence), `external_source.py` (static External Source
voice-route/path joins), `model_view_projection.py` (authored ModelView
normal/positioned branch projection), `interactive_components.py` and
`authored_components.py` (serialized component recovery), `table_contexts.py`
(authored table/config scanning plus the bounded AudioCue expression AST),
`audio_cue_native.py` (the AudioCue enum/operator native contract gate),
`rtpc_contract.py` (the canonical `AU_RTPC_*` name mapping), `rtpc_alignment.py`
(`controlCatalog.staticRtpcAlignment`, `authoredStatic` evidence only),
`scene_backgrounds.py` (scene-background catalog and table/NPC identity
overlays), `media_ownership.py` (coarse decoded-media ownership and the Gameplay
sound projection), `name_recovery.py` (grammar-derived Event name recovery), and
`event_projection.py`/`event_summary.py` (WebUI row projection).

`build_audio.py` imports shared primitives from these owners instead of treating
the semantics entry point as a utility module, and
`webui.story.level_bindings` owns the LevelScript dynamic string property
resolution that audio lifecycle evidence reads. Add logic to its domain owner
rather than growing either entry point; do not add compatibility re-exports,
duplicate native catalogs, broad `ImportError` import fallbacks, or a second
scan when one collected context index can supply both names and hashes.

Lazy Event-detail payloads carry their own schema versions and are omitted from
compact Event summaries: `selectorBranches` (`selectorBranchSchemaVersion=1`),
`levelScriptAudioLifecycle` (version 1), and full AudioCue ASTs
(`audioCueExpressionSchemaVersion=1`). The semantic payload is schema 117.
Role/layout coverage is emitted in generated Audio stats and Event summaries
rather than fixed in this document. Generated and reported outputs:

```text
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/lang/<LANG>/audio/scene_backgrounds.json
webui/data/lang/<LANG>/gameplay/sound_effects.json
reports/story/recovery/audio/external_source_override_path_audit.*
reports/story/recovery/audio/external_source_channel_path_audit.*
reports/story/recovery/audio/native_io_vtable_pointer_census.*
reports/story/recovery/audio/native_registration_serial_audit.*
```

`scene_backgrounds.py` consumes validated AnimeStudio AssetMap object roots in
one bounded streaming pass, and `recover_map_streaming_instances.py` supplies
the validated `InitChunkData` sidecar it joins against; the promotion rules for
scene, prefab, character, enemy, and NPC ownership live in
[`memory/game_data/audio_naming_coverage.md`](../memory/game_data/audio_naming_coverage.md).
Native Audio claims always receive both the selected `global-metadata.dat` and
the matching `GameAssembly.dll` through `--game-root`; missing or mismatched
binaries retain authored evidence but omit build-locked callsites, mappings, and
runtime addresses, and module-global default game paths must not be restored.
The reviewed native facts belong in their contracts and generated reports, and
their durable interpretation in
[`memory/game_data/audio_native_hooks.md`](../memory/game_data/audio_native_hooks.md).

### Optional read-only runtime observation

Both audio observers are optional, read-only, and part of no export, Updates, or
packaging flow. Validate the single manifest and payload contract before any
authorized staging:

```bat
python -m scripts.webui.story_recovery.runtime_trace_audio_native_capture --check-only --native-library PATH\AudioCapture.dll
tools\frida-runtime\venv\Scripts\python.exe -m scripts.webui.story_recovery.runtime_trace capture --profile audio --check-only
tools\frida-runtime\venv\Scripts\python.exe -m scripts.webui.story_recovery.runtime_trace capture --profile audio
python -m scripts.webui.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl
```

The experimental native fallback under `tools/audio-runtime-capture/` verifies
the selected process, `GameAssembly.dll`, and `AkSoundEngine.dll`, then can
install the manifest-derived `audio_chain_v1` read-only profile, which records
the managed external-source request, the Wwise source-media lookup, and the
default I/O open; the descriptor-post boundary stays disabled until its ABI is
recovered. Its launcher copies the verified x64 DLL into a private package
directory, writes the adjacent `audio_capture.session.json`, makes at most one
ordinary LoadLibrary injection attempt when explicitly requested, and requires
an importer-compatible, fully hash-matched `session_start` handshake before
reporting the session armed. A denial, incomplete module gate, hook attachment
failure, or unsupported profile stops without retry or fallback.

The Frida audio hook manifest verifies `AkSoundEngine.dll` and reads the
builder-owned native contracts rather than pinning its own copy of a task RVA,
message ID, or field offset; `runtime_trace_audio_import.py` publishes the
observed relations, and what a capture does and does not prove is recorded in
[`memory/game_data/audio_native_hooks.md`](../memory/game_data/audio_native_hooks.md).
An optional guided native observer can supply bounded graphics/audio evidence
alongside the independently valid staged 3DMigoto workflow -- its host recording
is a BMP sequence plus WAV, not MP4 -- and the audio-only launchers above remain
focused diagnostics rather than that combined workflow. Keep raw sessions under
the relevant scratch recovery topic and retain the provider and completeness
summary with any published evidence.

## Updates

Updates compare two complete export folders. Pass `OLD NEW`, or configure
`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` in
`endfield_paths.bat`. A named `OLD` refreshes the cached baseline.
`build_updates.py` calls the reusable `webui/updates/scanner.py` API in
process; the scanner is an internal component rather than a second CLI.

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --text-only
.\build_updates.bat OLD NEW --no-audio
.\build_updates.bat OLD NEW --exact
python -m scripts.webui.updates.build_updates --refresh-previous-export-baseline
```

The default scan covers WebUI-facing exported text plus image, model, video,
and decoded audio assets. `--text-only` omits all assets, `--no-audio` keeps
other assets, `--exact` hashes contents, and `--full-export-scan` is for broad
audits only.
AnimeStudio `object_index`/`field_index` directories (including their
`parts`) and exporter index-only JSONL, compressed, and temporary files are
excluded from every Updates comparison and previous-export prune; ordinary
WebUI JSON, media, and decoded audio remain in scope.

Every Characters build also saves its final generated catalog under
`export_full/recovered/WebUI/characters/<LANG>.json`. Every Updates comparison
writes `webui/data/updates/characters.json` by comparing those version-owned
catalog snapshots. The comparison therefore covers the same Table, Story actor,
and exported-asset identities and evidence that formed each Characters page,
not only `CharacterTable`. Only languages present on both sides participate.
It reports `added`, `modified`, and `deleted` independently of asset flags,
including under `--text-only`. Missing, invalid, empty, or legacy exports
without snapshots publish an unavailable empty sidecar instead of treating the
current roster as entirely new. The sidecar does not alter recovery or grouping.

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

Reviewed per-build native facts are stored as data, not prose:
`scripts/game_data/*_native.json` for raw-format consumers and MemoryPack
formatter windows, and `scripts/game_data/native_contracts/` for Story
builders. These JSON files **are tracked**: what they record is a data
structure, and the per-build anchors beside each field are its provenance. The
digest of a named consumer contract is pinned as `CONTRACT_SHA256` in its
`*_native.py` module and re-checked at load, so editing the JSON without
updating that pin fails closed. The pin covers exact bytes, so
`.gitattributes` marks `scripts/**/*.json -text` and their line endings must
never be converted. See the native-contract rules in `AGENTS.md` before adding
or regenerating one, and never carry an RVA, registration index, or code-window
hash over from a previous installed build.

## Output hygiene

- Generated reports belong in topic directories under `reports/`.
- Reusable conclusions belong to a `memory/` owner: `memory/game_data/` for
  what the binary means, `memory/webui/` for how it reaches a page.
- Revisitable experiments belong in `scratch/<topic>/<task>/`.
- Disposable intermediates belong in `tmp/<topic>/<run>/` and should be
  removed after validation.
- Track a file only if it is reusable and general enough to explain the data. A
  corpus gate, native validator, or audit tool is tracked, and so is a contract
  that documents a data structure; the reports, ledgers, and receipts those
  tools write are not.
- Keep declarations in a contract the module loads, not as a large block of
  pinned hashes and addresses inside a tracked module.
- Tests for maintained scripts belong in `scripts/tests/` and run by explicit
  module path, for example
  `python -m unittest scripts.tests.test_build_assets`. `unittest discover`
  does not reach that directory. The suite is untracked and stays in place; do
  not re-track it or move it.
