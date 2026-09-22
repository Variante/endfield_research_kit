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
| | `game_data/` | the exact framing readers, one per payload family (`irradiance_volume.py`, `extend_data_binary.py`, `bundle_manifest.py`, `ifix_patch.py`, `inverted_lz4.py`, `dynamic_streaming.py`, the serialized-gameplay `*_binary.py` readers, and the MemoryPack JsonData readers such as `levelconfig_binary.py`, `navmesh_binary.py`, `gpu_ui_binary.py`); the `*_corpus.py` current-corpus gates (`jsondata_corpus.py`, `gpu_ui_corpus.py`, `dynamic_stream_area_corpus.py`) and `jsondata_schema_coverage.py`; the `*_native.py` loaders and validators for the reviewed native facts the Story, Mission Pipeline, Map and recovery tools consume; `native_union_atlas.py`, which re-validates every union contract; `dummydll_metadata.py`, `levelscript_union_layouts.py` and `dependency_snapshot.py`; `media_resolver.py` (game-media naming) and `cabmap.py` (the CABMap container index and the `m_FileID` -> dependency-slot rule) |
| | `game_data/codecs/` | all per-record LevelScript and LevelData byte decoding behind the `*_binary.py` readers, which keep only the file-level framing walk, the record dispatcher and the result assembly; includes `send_lua_event.py` for the one nested value the derived declaration cannot describe |
| | `game_data/contracts/` | the reviewed contract JSON that every reader, loader and validator loads; `CONTRACTS_DIR` from the package is the only path anchor; git, not a pinned digest, owns each file's integrity |
| | `game_data/streaming/` | the block-15 Streaming lane: `framing.py`, `pairs.py`, the marker parsers, their `*_native.py` validators and `*_corpus.py` gates |
| | `game_data/terrain/` | the TRET container reader (`tret.py`), the height grids map recovery reads (`height.py`), the native consumer validator and the corpus gate |
| | `game_data/il2cpp/` | `protocol.py` (metadata and PE primitives), `native_image.py` (the one opened installed build every contract validator checks against, with the shared method-identity, dispatcher-route, code-window and setter-order checks), `context.py` (generic-instantiation pointer tables), `method_resolver.py` (managed name to selected-build body), and the context audit split by the section it owns: `context_audit.py` (CLI, registration and method-spec sweeps, report assembly), `context_audit_common.py` (build gate through `contracts/il2cpp_context_audit_native.json`, hashing and sweep helpers), `context_audit_memorypack.py` (MemoryPack reader and BuffData consumer checks), `context_audit_skilldata.py` (SkillData branch witness, replay and static alignment), `context_audit_vfs.py` (stream, VFS and UnityPlayer consumer checks) |
| | `game_data/monobehaviour/` | the exported MonoBehaviour corpus: `census.py`, `monoscript_catalog.py`, `script_names.py`, `field_semantics.py` (what each named class's fields hold) and `table_keys.py` (which string fields carry exported Table keys) |
| | `game_data/schemas/` | the reviewed named JSON schema readers for the textual JsonData families (`gameplay_config.py`, `gameplay_config_polymorphic.py`, `text_schema.py`, `mission_runtime_main.py`, `mission_runtime_meta.py`, `npc_catalog.py`, `npc_prefab_info.py`, `map_config.py`, `ui_level_map_load_config.py`, `level_mount_point.py`, `gold_coin_config.py`), all validated by `named_schema.py` and keeping only their contract pin, path predicate, relations and result shape |
| | `game_data/wwise_sdk_symbols.py` | names functions in the shipped `AkSoundEngine.dll` by matching each `.pdata` function body against the named COMDAT sections of every installed Wwise SDK library, recording which one named it and dropping a symbol two archives define differently; a match needs an equal extent, 80% byte agreement and a clear margin over the runner-up, so an ambiguous or weak candidate leaves the function unnamed |
| | `game_data/memorypack/derived_schema.py` | recursive read-plan resolution over the derived wrapper, union, enum and wrapped-type tables; models the counted-map framing a reviewed reader proves and refuses every other formatter-backed type rather than reading its member list |
| | `game_data/memorypack/union_subtypes.py` | tag assignment for the nested unions the dispatcher walk cannot reach, inferred from the wrapper hierarchy and gated on the walked union reproducing exactly |
| | `game_data/memorypack/derived_actions.py` | the narrow flat-body case of the same idea: adds only the routes whose members are all fixed-width or strings, with no plan registry. `derived_plans` is the superset |
| | `webui/story_recovery/refresh_audio_hook_catalog.py` | re-pins the audio hook catalog the capture host reads to the installed build: managed RVAs re-resolved by name, native RVAs kept only when still a `.pdata` function start. The host writes the activation manifest itself, and each native row is named from the Wwise SDK on every re-pin, an annotation cleared rather than carried when the match is lost |
| | `webui/audio/semantics/runtime_capture_import.py` | validates one bounded EndfieldCapture audio session against the provider's own completeness counters, decodes its callback payloads with the writer's own `AudioEventPayload` layout, and reports the Events posted and files opened without joining them |
| | `webui/audio/semantics/decoded_payload_event_names.py` | Wwise Event names taken from the decoded member that holds them rather than from a spelling grammar; standalone, not yet wired into `build_audio` |
| | `game_data/memorypack/derived_values.py` | decodes a plan into named values rather than only framing it, and checks each decoded record's own identifier against its filename |
| | `game_data/memorypack/derived_plans.py` | opt-in reader that executes a `derived_schema` read plan with the frozen reader's own primitives, so a nested record, list, counted map or union is consumed rather than only described; `--corpus` is its adoption gate against exported BuffData |
| | `game_data/memorypack/action_dispatcher.py` | the whole AbilityActionData union dispatcher of the selected build, walked generically from the switch table the reviewed contracts pin; names the wrapper behind every tag, including the ones no contract covers |
| | `game_data/memorypack/wrapper_members.py` | the selected build's generated wrapper member order and member types for every `*ForMemoryPack` type, derived in one metadata pass; the bulk source the per-tag contracts record one wrapper at a time |
| | `game_data/memorypack/union_dispatch.py` | reads a union's tag assignment from its native `<Base>ForMemoryPackFormatter.Deserialize` jump table, found by name and instruction shape; accepts a table only when every entry resolves one-for-one onto the family's derived wrappers, and refuses unions compiled without one |
| | `game_data/pure_getter_rows.py` | re-derives the per-build fields of reviewed PureGetter contract rows -- tag, member count and ordinals, `GetResult` body -- for the `*_getter_native.py` loaders' `--regenerate` |
| | `game_data/levelscript_union_tags.py` | the current build's ActionBase / PureGetter / ActionHeader `(tag, member count)` for every type name, regenerated from the native formatter switches into `contracts/levelscript_union_tags.json`; LevelScript codecs and Story name a type (`union_tags.action("IfElseAction")`) instead of writing a tag literal that the next client update renumbers |
| | `game_data/il2cpp/call_graph.py` | names a body's direct calls (ordinary and generic method pointers), the string literals it loads and the fields it reads before a call, so a native contract can state "A calls B, then C" by name and re-prove it on each build |
| | `game_data/memorypack/` | MemoryPack codecs and their corpus gates, including the current-build BuffData additions (`buff_icon_config.py`, `buff_residual_actions.py`, `buff_named_schema.py`) and the SkillData first-timeline lane (`skill_timeline_*.py`), which share `core.LabelledReader` and gate through `il2cpp.native_image` |
| **2. WebUI** | `webui/views.py`, `webui/package.py` | page-build orchestration, and packaging |
| | `webui/story/` | Story and Text page data plus shared Story evidence |
| | `webui/story_recovery/` | Story audits, OCR ordering, runtime traces, candidate generation |
| | `webui/mission_pipeline/` | standalone Mission Pipeline recovery (not a WebUI page) |
| | `webui/{assets,audio,characters,gameplay,map,recovery,updates}/` | one folder per page: its `build_*.py` entry point and helper modules |
| | `webui/recovery/` | the Recovery-progress page: `build_recovery.py` plus its tracked `recovery_declarations.json`. It derives from generated reports and the `memory/game_data/README.md` lane index only, never from installed bytes, and fails closed on a missing report, a schema-token mismatch, or a VFS block type with no declared lane |
| | `webui/decoded_payloads.py` | export-relative path to the `game_data` reader that owns it, rendered as diffable text; the routing shared by consumers that need a serialized `.json` payload as text rather than as a page record |
| **Shared** | `common.py`, `source_paths.py`, `repo_paths.py` | helpers used by both lines; `repo_paths.REPO_ROOT` is the only repo-root anchor |
| **Tests** | `tests/` | stdlib `unittest`, untracked, run by explicit module path |

Dependencies point one way: shared helpers import neither line, line 1
imports only shared helpers, and line 2 imports both. Reuse is the point of
that direction. A page builder calls a `game_data` reader or contract instead
of re-decoding bytes, and a helper that both lines need goes in `common.py`
under its own name, not in a private copy. The local
`tests/test_scripts_layout_boundaries.py` checks the direction statically and
at import time. The one sanctioned
crossing is data, not code: focused asset export reads the published
`webui/data` media references to scope which textures it extracts.

Three more rules keep the split honest. Line 1 never writes under
`webui/data/`. A production builder must not import or execute a
recovery/audit module. A corpus gate or native validator is tracked because
the sweep is reusable, while everything it emits goes to `reports/`.

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
| Rebuild the Recovery progress page | `python -m scripts.webui.recovery.build_recovery` |
| Serve or package | `python serve.py` / `python -m scripts.webui.package` |

The wrappers load `endfield_paths.bat`, then apply explicit path flags. Run any
wrapper with `--help` for its supported options.

The maintained Terrain structure gate is
`python -m scripts.game_data.terrain.corpus`; it consumes a completed VFS audit
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

`game_data/dependency_snapshot.py` is the maintained development-only input
closure for scoped parser caches and diagnostics. Call
`dependency_snapshot(roots)` with importable module names; it hashes the
repo-local Python import closure, unambiguous literal JSON resources,
transitive relative `.json`/`.py` paths declared by contract `dependencies`
arrays, and statically resolvable Python helpers passed to
`spec_from_file_location`. Ambiguous basenames, conflicting literal helper
assignments, missing declared files, and paths escaping the selected root fail
closed. Runtime-computed paths and imports that cannot be resolved statically
remain outside this snapshot, so canonical publication continues to use the
complete family sweep and its broad authenticated start/end drift gate.

For the recovery path and evidence boundary of an individual WebUI page, use
[`memory/webui/README.md`](../memory/webui/README.md). This file remains the
command and module-ownership map.

`setup.bat` initializes only the required `tools/AnimeStudio` submodule.
`tools/Cpp2IL-Endfield` and `tools/EndfieldCapture` are optional and are not needed for the normal WebUI
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
  `<export root>/meta/extraction/incremental/` advances only
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
- Structured scope is a **separate axis** with three levels, each containing
  the one below: `--structured-dump-mode focused` (default: Table, JsonData,
  video, Lua), `default` (plus the Terrain height grids), `full` (plus Terrain
  whole, Streaming, DynamicStreaming, IV, ExtendData, IFixPatch, bundle
  manifest; about 6.4 GB more). No structured level carries raw bundles or
  audio packages.
- `--for story|map|pages|everything` sets both axes from one intent, because
  almost nobody picks them independently. It fills only what the caller left
  alone, so an explicit `--structured-dump-mode` or `--*-assets` still wins in
  either order. `--show-scope` prints the resolved scopes and exits, which is
  how to check a preset before paying for the run.

  | `--for` | structured | assets |
  | --- | --- | --- |
  | `story` | `focused` | none |
  | `map` | `default` | none |
  | `pages` | `default` | `default` |
  | `everything` | `full` | `debug` |

  A page-to-input mapping could not be a single ladder: Map needs Terrain and
  Streaming but no bundles, Assets needs bundles but no Terrain, and Story
  needs neither. These four presets are the intents that actually occur, not a
  derivation from a page list -- a page-to-input table would have to be kept in
  lockstep with every builder's inputs.
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
| Decoded Data Inspector | `data_inspector/build_data_inspector.py` | generic catalogs and lazy decoded-record shards |
| Gameplay | `build_gameplay.py` | Gameplay datasets |
| Assets | `build_assets.py` | asset indexes and media lookup |
| Audio | `build_audio.py` | decoded/relinked audio data |
| Audio semantics | `build_audio_semantics.py` | compact Audio page evidence and shards |
| Audio HIRC structural gates | `webui/audio/semantics/hirc_action_corpus.py` | Action cursors and type `0x02` source prefixes under `reports/animestudio/` |
| DynamicStreaming stream-area gate | `game_data/dynamic_stream_area_corpus.py` | `reports/animestudio/dynamic_stream_area_current_latest.{json,md}` |
| Updates | `build_updates.py` | `webui/data/updates/latest.json`, `webui/data/updates/characters.json` |
| Recovery progress | `webui/recovery/build_recovery.py` | `webui/data/recovery/index.json` |
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
`build_assets.py` also writes `webui/data/assets/table_owners.json` from
`webui/assets/table_asset_owners.py`: exact table-row ownership for indexed
assets, always derived from the complete scan even when the published index is
the focused Story/Wiki projection. Maintained Text Tables renderers live in
`webui/story/reference_structured_fields.py` and are published by
`webui/story/build.py` as each reference row's `fields`.

`build_assets.py` writes only Assets-owned indexes and media lookup. Its `--mode` defaults to `focused`, the Story/Wiki media projection; the served Assets page is built with `--mode default`, and the wrapper passes it. A direct run without `--mode default` replaces the full index with the focused projection. The legacy
economy, world, presentation, and broad data index helpers are diagnostic only
and do not feed active pages.

### Focused commands

```bat
python -m scripts.game_data.extraction.verify_export_freshness
python -m scripts.webui.story.refresh_evidence
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
python -m scripts.webui.characters.build_character_data --languages CN --default-language CN
python -m scripts.webui.data_inspector.build_data_inspector
python -m scripts.webui.mission_pipeline.build_mission_pipeline_data
python -m scripts.webui.gameplay.build_gameplay
python -m scripts.webui.assets.build_assets --mode default
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
python -m scripts.webui.package
```

### Offline recovery probes

AnimeStudio offline recovery probes:

```bat
set ASCLI=tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
%ASCLI% vfs-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --summary-json reports\animestudio\vfs_understanding_latest.json --ledger-jsonl-gz reports\animestudio\vfs_understanding_files_latest.jsonl.gz --report-md reports\animestudio\vfs_understanding_latest.md
python -m scripts.game_data.memorypack.buff_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output-json reports/animestudio/buffdata_current_latest.json --output-md reports/animestudio/buffdata_current_latest.md
python -m scripts.game_data.memorypack.skill_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --cursor-verification reports/animestudio/skilldata_cursor_verification_latest.json --output reports/animestudio/skilldata_current_latest.json --output-md reports/animestudio/skilldata_current_latest.md
python -m scripts.game_data.jsondata_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.gpu_ui_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming.corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming.marker17_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming.marker13_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.streaming.marker2_corpus --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.skill_cursor_receipt --preflight
python -m scripts.game_data.memorypack.skill_timeline_cursor --stream-jsonl CURRENT_SKILLDATA_STREAM_JSONL --native-context reports/animestudio/il2cpp_context_current_latest.json
python -m scripts.game_data.memorypack.npc_montage_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.buff_1b_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.lipsync_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.wrapper_members
python -m scripts.game_data.memorypack.wrapper_members --wrapper Beyond_Gameplay_Core_CreateBuffAction_DataForMemoryPack
python -m scripts.game_data.memorypack.action_dispatcher
python -m scripts.game_data.memorypack.action_dispatcher --tag 0x92
python -m scripts.game_data.memorypack.derived_actions
python -m scripts.game_data.memorypack.derived_actions --list-routes
python -m scripts.game_data.memorypack.union_subtypes
python -m scripts.game_data.memorypack.union_subtypes --union Selector_Finder_DataForMemoryPack
python -m scripts.game_data.memorypack.derived_schema
python -m scripts.game_data.memorypack.derived_plans
python -m scripts.game_data.memorypack.derived_plans --corpus
python -m scripts.game_data.memorypack.derived_values
python -m scripts.webui.audio.semantics.decoded_payload_event_names
python -m scripts.game_data.wwise_sdk_symbols
python -m scripts.game_data.wwise_sdk_symbols --find CAkSrcMedia
python -m scripts.webui.story_recovery.refresh_audio_hook_catalog
python -m scripts.webui.audio.semantics.runtime_capture_import
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
| `game_data.streaming.corpus` | `streaming_root_subgraphs_latest.{json,md}` |
| `game_data.streaming.marker17_corpus` | `streaming_marker17_bodies_latest.{json,md}` |
| `game_data.streaming.marker13_corpus` | `streaming_marker13_latest.{json,md}` + inventory `.jsonl.gz` |
| `game_data.streaming.marker2_corpus` | `streaming_marker2_latest.{json,md}` + inventory `.jsonl.gz` |
| `game_data.jsondata_corpus` | `jsondata_current_latest.{json,md}` + per-file `.jsonl.gz` |
| `game_data.gpu_ui_corpus` | `gpu_ui_current_latest.json`; authenticated GPUI named schemas, including native-gated DamageText |
| `game_data.memorypack.skill_corpus` | `skilldata_current_latest.{json,md}` |
| `game_data.memorypack.skill_timeline_cursor` | `skilldata_timeline_cursor_latest.{json,md}` |
| `game_data.memorypack.npc_montage_corpus` | `npc_montage_current_latest.{json,md}` |
| `game_data.memorypack.buff_corpus` | `buffdata_current_latest.{json,md}` |
| `game_data.memorypack.buff_1b_corpus` | `buff_1b_current_latest.{json,md}` |
| `game_data.memorypack.lipsync_corpus` | `lipsync_current_latest.{json,md}` |
| `game_data.memorypack.derived_schema` | `reports/game_data/memorypack_derived_schema.json`; a recursive read plan per action tag over nested records, lists, arrays and nested unions, with each route's evidence tier and the named type blocking the rest |
| `game_data.memorypack.union_subtypes` | `reports/game_data/memorypack_union_subtypes.json`; every union base's subtypes and predicted tag assignment, gated on reproducing the walked root union and corroborated against the reviewed nested rows plus the frozen reader's own per-tag member counts for six nested unions it never walks |
| `game_data.memorypack.derived_actions` | `reports/game_data/memorypack_derived_actions.json`; the union tags whose whole body this reader can consume, and the cross-check of that framing against the frozen reader |
| `game_data.memorypack.derived_values` | `reports/game_data/memorypack_derived_values.json`; how many records of each exported family decode into named values, how many carry an identifier matching their filename, how many cross-record references resolve to records that exist, and one decoded sample per family |
| `game_data.memorypack.derived_plans` | `reports/game_data/memorypack_derived_plans.json`; each plan's framing cross-checked against the frozen reader tag by tag. `--corpus` prints instead: how many exported BuffData files each reader closes, whether every file the frozen reader already closed still ends at the same cursor, how many routes and nested-union placements the run actually walked, and and how many files of each of the four whole-record families the plan consumes exactly to EOF, against how many land short and how often a refused body's position was reached |
| `game_data.memorypack.action_dispatcher` | `reports/game_data/memorypack_action_dispatcher.json`; every AbilityActionData union tag's route, registered type, generated wrapper, named member order and member widths, with each reviewed tag re-derived and compared |
| `game_data.memorypack.wrapper_members` | `reports/game_data/memorypack_wrapper_members.json`; every generated `*ForMemoryPack` wrapper's serialized member order, member types, fixed member widths (including each enum's real underlying width), and the wrapped type each wrapper frames, derived from the selected build, plus its agreement with the reviewed contracts |
| `game_data.terrain.corpus` | `terrain_tret_latest.{json,md}` |
| `game_data.dynamic_stream_area_corpus` | `dynamic_stream_area_current_latest.{json,md}` |
| `game_data.il2cpp.context_audit` | `il2cpp_context_current_latest.*` (JSON on stdout) |
| `game_data.native_union_atlas` | `jsondata_union_atlas_current.json`; one-context authenticated index of reviewed JsonData union contracts, with each row's generated member order named from `memorypack.wrapper_members` |

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
| `scene_order_gap_shared.py` | shared scene-order gap logic |

Mission Pipeline is a standalone recovery/reporting workflow; the WebUI export
does not run it. It reads the canonical shipped-Lua consumer index through
`webui.story.lua_consumer_references`; it does not consume a recovery-script
artifact. Cinematic-handle classification and typed action-producer joins come
from the reviewed, installed-build-gated
`game_data/contracts/cinematic_queue.json`; the full native carrier
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

The reviewed LevelScript task paths live in
`game_data/contracts/mission_task_paths.json`. The protocol registry
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
`<export root>/meta/<Layer>/managed_reference_diagnostics/`.
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
`<export root>/game/Audio/shared/` and language voice under
`<export root>/game/Audio/<LANG>/`.

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
`scripts.webui.gameplay.projectiles` reads only `data_projectile_*` objects
whose template and component references are exact managed-reference TypeTree
decodes; every other candidate is skipped and counted by reason
(`counts.skipped`, `skippedFiles`), and `--require-exact` turns a non-exact
skip into a non-zero exit. Sound fields carry the signed int32 plus the
uint32 hex that Audio joins on.

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
reports/animestudio/hirc_type09_body_current_latest.{json,md}
reports/animestudio/hirc_type0a_body_current_latest.{json,md}
reports/animestudio/hirc_type0b_body_current_latest.{json,md}
reports/animestudio/hirc_type0c_body_current_latest.{json,md}
reports/animestudio/hirc_type0d_body_current_latest.{json,md}
reports/animestudio/hirc_type10_body_current_latest.{json,md}
reports/animestudio/hirc_type11_body_current_latest.{json,md}
reports/animestudio/hirc_type13_body_current_latest.{json,md}
reports/animestudio/hirc_type14mod_body_current_latest.{json,md}
reports/animestudio/hirc_type15_body_current_latest.{json,md}
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
(installed-build gate), `wwise_enums.py` (the one loader for the pinned
`wwise_sdk_enums` contract; label tables read it instead of copying it, and a
digest or schema mismatch fails closed), `identifiers.py` (Wwise hashes and managed string
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
sound projection), `name_recovery.py` (grammar-derived Event name recovery),
`authored_payload_event_names.py` (shipped MemoryPack length-prefixed Event-name
literals in the `LevelScriptData`/`LevelScriptTemplateData`/`SpawnerConfig`/
`Interactive`/`LevelData` payload roots; `gameplay_audio.py` keeps `SkillData`
and `BuffData`), and `event_projection.py`/`event_summary.py` (WebUI row
projection).

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
contracts through the `game_data/*_native.py` loaders rather than pinning its own copy of a task RVA,
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

A `.json` name does not mean the bytes are text. The scanner decides by
content: UTF-8 text diffs as itself, a serialized payload is rendered through
the `scripts.game_data` reader `webui/decoded_payloads.py` routes for it, and a
payload with no reader or one over the diff size limit gets no text. Each file
records which form it stored, so a bounded reader's diff is published as
partial and a changed file with no diff says why. Changing that routing changes
the cached text: refresh the previous-export baseline afterwards.

The default scan covers WebUI-facing exported text plus image, model, video,
and decoded audio assets. `--text-only` omits all assets, `--no-audio` keeps
other assets, `--exact` hashes contents, and `--full-export-scan` is for broad
audits only. The published feed keeps every matching changed entry by default;
`--sample-limit N` is an opt-in diagnostic cap, while `0` remains unlimited.
Only an individual oversized text diff preview is bounded; that does not omit
the update entry itself.

Asset identity normally follows the exported relative path. For unmatched
add/delete pairs, the builder also recognizes one-to-one Unity exports whose
stable name differs only by the generated `_p<PathID>` suffix, and decoded
audio whose bytes match exactly. A second FLAC-only lane compares the decoded
PCM identity from STREAMINFO, so metadata or encoder changes can still be
recognized without an external decoder. Exact-byte hashing is limited to
equal-size unmatched candidates, while STREAMINFO supplies exact duration and
format. A shared filename is preferred; duplicate-content buckets may then pair
one-to-one inside the same unchanged parent folder, otherwise each byte or PCM
identity must be unique. Recognized relocations publish as no update when their
effective content is unchanged. A stable Unity identity whose bytes also
changed publishes as `modified` with both paths and its match basis. Multiple
candidates inside one folder remain separate `added` and `deleted` entries
rather than being guessed.

The same reconciliation pass filters obsolete numeric AudioDialog copies when
the numeric filename is the exact 64-bit external-source hash of one current
authored dialog path, that dialog basename resolves to one canonical voice
asset, the bytes match, and the canonical asset survives on both sides. These
are redundant export copies rather than game deletions. A repeated basename,
hash ambiguity, missing canonical peer, or content mismatch keeps the original
add/delete entry visible.
AnimeStudio `object_index`/`field_index` directories (including their
`parts`) and exporter index-only JSONL, compressed, and temporary files are
excluded from every Updates comparison and previous-export prune; ordinary
WebUI JSON, media, and decoded audio remain in scope.

Every Characters build also saves its final generated catalog under
`webui/data/_build/characters/<LANG>.json` (the page's own snapshot). Every
Updates comparison writes `webui/data/updates/characters.json` from two
catalogs that Updates builds itself, one per export, with the current builder
and cached in `.game-data-tracker/`: each from that export's own tables and
converted media, without the Story actor registry that exists only for the
built export. Builder changes and Story-only inputs therefore never appear as
game updates; the comparison covers Table and exported-asset identities, not
only `CharacterTable`. Only languages present on both sides participate.
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
`scripts/game_data/contracts/*_native.json` for raw-format consumers and MemoryPack
formatter windows, and the native facts Story, Mission Pipeline, Map and the
recovery tools consume through the `scripts/game_data/*_native.py` loaders. These JSON files **are tracked**: what they record is a data
structure, and the per-build anchors beside each field are its provenance.
No module pins a contract's own bytes; a loader checks the installed build
against the contract's `nativeInputs` and the native code against its recorded
window or body hashes. See the native-contract rules in `AGENTS.md` before
adding or regenerating one, and never carry an RVA, registration index, or
code-window hash over from a previous installed build.

### Measuring JsonData schema coverage

```bat
python -m scripts.game_data.jsondata_schema_coverage ^
  --report reports\game_data\jsondata_schema_coverage.json
```

Reports named bytes per family and bucket, ranked by unnamed bytes, for the
binary families whose framings declare their opaque ranges. It answers "how
much of each file is understood", which is a different question from
`jsondata_corpus`: that gate proves identity and routing and reports a per-file
status, and a consumer must still gate on the status. Never read
`bytesConsumed` as coverage -- see
[`memory/game_data/extraction_payload_boundaries.md`](../memory/game_data/extraction_payload_boundaries.md)
for why, and for the recovery order the measurement sets.

### Deriving the LevelScript union layout table

```bat
python -m scripts.game_data.levelscript_union_layouts ^
  --report reports\game_data\levelscript_union_layouts.json
```

Derives every `ActionBase`/`GetterBase`/`ActionHeader` union layout for the
selected build from `tools/DummyDll`, instead of recovering one row at a time
from the native dispatcher. Tag is the case-insensitive alphabetical rank of
the wrapper type name without its `ForMemoryPack` suffix; members are the base
chain's setters, root first, typed by each setter's parameter.

It seeds four union families -- ActionBase, GetterBase, ActionHeader and
GameCondition -- plus the `LevelScriptData` and `LevelScriptTemplateData`
roots, then closes the declarations and derives a family for every union base
it discovers, repeating to a fixed point. Each struct carries `containsReferences`, which decides whether it
is framed as an object or written raw, and a `rawLayout` giving its memory
offsets when that is established. Each enum carries the underlying width read
from its own `value__` field.

It gates on the installed native inputs recorded in
`tools\DummyDll\generation.json`, then recomputes all 277 rows of
`codecs/levelscript/action_map_layouts.json`, checks the derived declarations
against that contract's `primitiveEvidence`, and writes nothing if anything
disagrees. `--allow-build-drift` skips only the native gate, for inspecting a
DummyDll set that is not the selected build. Derived rows carry the `direct`
evidence boundary, not the reviewed table's `exact`; see
[`memory/game_data/extraction_payload_boundaries.md`](../memory/game_data/extraction_payload_boundaries.md).

`action_map.decode_action_serialized_map` consumes the report through its
optional `declarations` argument, built with
`action_map.Declarations.from_report`. Passing nothing keeps the reviewed-only
behaviour every production consumer publishes at; passing it admits the derived
tier, and the caller owns recording that its result is `direct`.
`levelscript_binary.frame_levelscript_declared_root` is the whole-file framing
built on it -- it refuses any file whose cursor does not close at physical EOF
-- with `frame_levelscript_declared_action_map` as the partial fallback. The
coverage sweep measures with both:

```bat
python -m scripts.game_data.jsondata_schema_coverage ^
  --declarations reports\game_data\levelscript_union_layouts.json ^
  --report reports\game_data\jsondata_schema_coverage_declared.json
```

The report records which tier it was measured at as `evidenceTier`. Keep the
reviewed-tier report beside it rather than replacing it; the pair is what makes
the derived tier's contribution visible.

`scripts/game_data/dummydll_metadata.py` is the stdlib ECMA-335 reader beneath
it: PE to metadata root, the table row sizes, TypeDef base chains, setter
declaration order, and signature decoding. It has no entry point of its own and
carries no build-locked constant -- it reads whatever DummyDll set it is given,
so a caller that makes a schema claim from it must run the native gate itself.

The corpus gates run in a chain and each needs the current
`inputSetSha256` from the VFS audit:

```bat
%ASCLI% vfs-audit ...
python -m scripts.game_data.memorypack.buff_corpus --expected-input-set-sha256 ...
python -m scripts.game_data.memorypack.skill_corpus --expected-input-set-sha256 ...
python -m scripts.game_data.jsondata_corpus --expected-input-set-sha256 ...
```

That hash covers the AnimeStudio CLI binary, so rebuilding the exporter
invalidates the audit, every gate below it, and the tracked contracts that pin
it. Re-run the audit for a current value; do not edit a recorded one.

### Naming the exported MonoBehaviour corpus

MonoBehaviour is the largest exported Unity type, and the export does not carry
its class names: `m_Script` points into a MonoScript CAB outside the export
scope. Three commands turn that anonymous corpus into a named catalog.

```bat
python -m scripts.game_data.monobehaviour.census ^
  --report reports\assets\monobehaviour_script_census.json
python -m scripts.webui.assets.cabmap
python -m scripts.game_data.monobehaviour.monoscript_catalog ^
  --dump-root tmp\game_data\monoscript\MonoScript ^
  --report reports\assets\monoscript_catalog.json
python -m scripts.game_data.monobehaviour.script_names ^
  reports\assets\monobehaviour_script_census.json ^
  --monoscript-dump tmp\game_data\monoscript\MonoScript ^
  --report reports\assets\monobehaviour_script_names.json
```

The census sweeps every exported object, so give it a generous timeout. The
MonoScript dump itself is an AnimeStudio run into `tmp/`, filtered to the CAB
the corpus references. That CAB no longer has to be hunted for: every
`m_Script` in the corpus resolves to `CAB-5f527d7b7706baccdad9f794cf46420c`
through the dependency-slot rule in `scripts/game_data/cabmap.py`, and the
CABMap independently shows it as the most depended-on container in both maps.
Take its chunk path and offset from the CABMap at the time of use rather than
recording them, because it sits in a block that ships a different chunk
filename in each VFS root:

```bat
%ASCLI% "<chunk from the CABMap>" tmp\game_data\monoscript ^
  --game ArknightsEndfield --filter_data tmp\game_data\monoscript\filter.json ^
  --types "MonoScript:Both" --export_type Dump
```

`--filter_data` takes a JSON array of `{"Source": "<chunk>", "Offset": N}`.
The namer runs the structural IL2CPP match as an independent check on the
script PPtr and reports their agreement; `memory/game_data/unity_assets.md`
owns why both routes exist and where each one stops.

### What a named MonoBehaviour class owns

A class name is an identity for the script, not evidence about its fields. The
fourth command measures that, per field path rather than per class, over the
whole corpus:

```bat
python -m scripts.game_data.monobehaviour.field_semantics ^
  --names-report reports\assets\monobehaviour_script_names.json ^
  --progress 100000 ^
  --report reports\assets\monobehaviour_field_semantics.json
```

It is a second full sweep of the corpus, so give it the same generous timeout
as the census. Each field row carries its declared TypeTree type beside what
the corpus actually holds there. A reference row also carries the container its
sampled targets resolve to, through the CABMap rule in
`scripts/game_data/cabmap.py`, and the tier that resolution stands at: `exact`
where an exported target confirmed the predicted CAB, `container_only` where
the container is named but nothing exported sits there to check it,
`contradicted` where the prediction and the target disagree, and `unresolved`
where the CABMap could not answer. The export's `meta/cab_map` is read from the
same export root; without it the reference rows stay `unresolved` rather than
falling back to a global PathID match.

A reference that lands on another MonoBehaviour also names the target's class,
so a row reads `ControlTrack.m_Parent -> TimelineAsset` rather than
`-> MonoBehaviour`.

`--top N` reports only the N largest classes, which is how to work the corpus
down by object count; `--limit N` is a bounded probe, not a census.

A fifth command asks which of those string fields hold **exported Table keys**.
It reads the field-semantics report rather than the corpus, so it is seconds
rather than a sweep:

```bat
python -m scripts.game_data.monobehaviour.table_keys ^
  --report reports\assets\monobehaviour_table_keys.json
```

It refuses purely numeric values. Only 0.5% of the 178,582 numeric table keys
belong to a single table -- `"1"` is a key in 94 of them -- while 90.5% of the
90,988 named keys belong to exactly one, so pooling the two would turn a
bounded candidate list into thousands of invented references. `--min-objects N`
works the corpus down by class size.

Read the statuses as a ladder. `key_of` and `key_of_several` mean every checked
value belongs. `mostly_key_of` means one table holds at least 75% of them, so
the field is that key with exceptions and the exceptions are the interesting
part; the row lists them. `partial` means no table comes close, which makes the
field an unrelated name space that collided rather than a key field, and its
unmatched values are not reported as unresolved ids.

### Migrating a contract that pins a superseded build

`scripts/game_data/il2cpp/method_resolver.py` re-resolves recorded managed
method identities against the selected build. It pins nothing: it derives
`Il2CppCodeRegistration` from the selected `GameAssembly.dll` against the
complete image-name set of the selected `global-metadata.dat`, so it runs
unchanged after a client update.

```bat
python -m scripts.game_data.il2cpp.method_resolver --type "Ns.Type" --method "Method"
python -m scripts.game_data.il2cpp.method_resolver ^
  --from-contract path\to\contract.json ^
  --report reports\assets\character_recovery\<name>.json
```

`--from-contract` harvests every nested `{"type": ..., "method": ...}` object,
so it reads a contract's shape rather than one schema's key path, and may be
repeated. Each resolution records the route that reached it: `name`,
`lambda` (closure ordinals renumber), `undecoratedName` (a recorded
`Execute(int)` display form), and a `burstDirectCall` type route (Burst wrapper
tokens renumber). `memory/game_data_recovery.md` owns why each drift class
exists. The report is evidence that the identity still exists at a new address,
not that the old contract's body conclusions still hold.

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
