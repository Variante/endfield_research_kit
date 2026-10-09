# Scripts

This directory contains the maintained exporters and builders for the static
WebUI. Use the root wrappers for normal work; call Python entry points only for
focused development or validation.

This file is the command and module-ownership map. What the recovered evidence
*means* is not here: it belongs to the two memory axes --
[`memory/game_data/`](../memory/game_data/README.md) for how the original binary
is understood, and [`memory/webui/`](../memory/webui/README.md) for how that data
reaches a page. Every wrapper and entry point prints `--help`, and every
validator, gate and builder states in its module docstring what it checks,
what it writes and what it does not prove; this file does not repeat that.

## Layout

The tree follows the same split: two lines of work, each mirroring one memory
axis. A path appears under exactly one owner; each module's docstring states
the rest.

| Line | Path | Responsibility |
| --- | --- | --- |
| **1. Game data** | `game_data/extraction/` | installed client to `export_full/`: the export and changed-file exporters, `scope.py` (the structured-block and Unity-class vocabulary an export selects), the freshness guard with its per-output provenance, export benchmark, AnimeStudio object index, and `animestudio/` maintenance commands; never publishes page data |
| | `game_data/` | the exact framing readers, one per payload family (`irradiance_volume.py`, `extend_data_binary.py`, `bundle_manifest.py`, `ifix_patch.py`, `inverted_lz4.py`, `dynamic_streaming.py`, the serialized-gameplay `*_binary.py` readers, and the MemoryPack JsonData readers such as `levelconfig_binary.py`, `navmesh_binary.py`, `gpu_ui_binary.py`); the `*_corpus.py` current-corpus gates and `jsondata_schema_coverage.py`; the `*_native.py` loaders and validators for the reviewed native facts the Story, Mission Pipeline, Map and recovery tools consume, including `story_native_consumers_native.py` (Story's claim groups, cached in `reports/story/recovery/`); `native_union_atlas.py` (re-validates every union contract); `dummydll_metadata.py`, `levelscript_union_layouts.py`, `levelscript_union_tags.py` (current `(tag, member count)` per type name, so codecs name a type instead of a tag literal) and `pure_getter_rows.py` (per-build PureGetter row fields for `--regenerate`); `dependency_snapshot.py`; `media_resolver.py` (game-media naming), `sprite_crops.py` (Sprite crop documents), `cabmap.py` (the CABMap container index and the `m_FileID` -> dependency-slot rule) and `wwise_sdk_symbols.py` (names shipped `AkSoundEngine.dll` functions from the installed Wwise SDK libraries) |
| | `game_data/codecs/` | all per-record LevelScript and LevelData byte decoding behind the `*_binary.py` readers, which keep only the file-level framing walk, the record dispatcher and the result assembly; `codecs/levelscript/modules.py` is the sequential `modules` dictionary codec, and `send_lua_event.py` the one nested value the derived declaration cannot describe |
| | `game_data/contracts/` | the reviewed contract JSON that every reader, loader and validator loads; `CONTRACTS_DIR` from the package is the only path anchor; git, not a pinned digest, owns each file's integrity |
| | `game_data/streaming/` | the block-15 Streaming lane: `framing.py`, `pairs.py`, the marker parsers, their `*_native.py` validators and `*_corpus.py` gates |
| | `game_data/terrain/` | the TRET container reader (`tret.py`), Map's `_H` texture-byte diagnostic (`height.py`), the native consumer and layer-path validators, and the corpus gate |
| | `game_data/il2cpp/` | `protocol.py` (metadata and PE primitives), `native_image.py` (the one opened installed build every contract validator checks against), `context.py` (generic-instantiation pointer tables), `method_resolver.py` (managed name to selected-build body), `call_graph.py` (a body's named calls, literals and field reads), `body_claims.py` (the claim kinds a claims contract states, evaluated on whichever build is installed), and the context audit split by section: `context_audit.py` (CLI and report), `context_audit_common.py` (build gate, audit pins and `consumer_window` through `contracts/il2cpp_context_audit_native.json`), `context_audit_memorypack.py`, `context_audit_skilldata.py`, `context_audit_vfs.py` |
| | `game_data/monobehaviour/` | the exported MonoBehaviour corpus: `census.py`, `monoscript_catalog.py`, `script_names.py`, `field_semantics.py` and `table_keys.py` |
| | `game_data/schemas/` | the reviewed named JSON schema readers for the textual JsonData families (`gameplay_config*.py`, `text_schema.py`, `mission_runtime_{main,meta}.py`, `npc_catalog.py`, `npc_prefab_info.py`, `map_config.py`, `ui_level_map_load_config.py`, `level_mount_point.py`, `gold_coin_config.py`), all validated by `named_schema.py` |
| | `game_data/memorypack/` | MemoryPack codecs and their corpus gates (`core.LabelledReader`, the BuffData and SkillData readers, gated through `il2cpp.native_image`), plus the build-derived schema line: `wrapper_members.py` (every `*ForMemoryPack` member order and type), `action_dispatcher.py` (the whole AbilityActionData dispatcher), `union_dispatch.py` (a union's tag table from its native formatter), `union_subtypes.py` (nested-union tags), `derived_schema.py` (recursive read plans), `derived_actions.py` (the flat-body subset), `derived_plans.py` (executes a plan; `--corpus` is its adoption gate) and `derived_values.py` (named values checked against filenames) |
| **2. WebUI** | `webui/export.py`, `webui/pages.py`, `webui/build_graph.py` | the `export.bat` entry point; the page registry, in which every build task declares what it reads from the export; the dependency-graph scheduler and timing report |
| | `webui/package.py` | packaging |
| | `webui/story/` | Story and Text page data plus shared Story evidence |
| | `webui/story_recovery/` | Story audits, OCR ordering, runtime traces, candidate generation, and `refresh_audio_hook_catalog.py` (re-pins the audio capture hook catalog to the installed build) |
| | `webui/mission_pipeline/` | standalone Mission Pipeline recovery (not a WebUI page); `runtime_contract_native.py` re-derives `RUNTIME_CONTRACT` by name on the installed build and labels each native chain row |
| | `webui/{assets,audio,characters,gameplay,map,production,recovery,updates}/` | page and catalog builders with their helper modules |
| | `webui/audio/semantics/` | Audio's reusable evidence owners (see *Audio decode, indexing and semantics*), including `conversation_sidecar.py` (the per-conversation Story sidecars the Story page merges), `decoded_payload_event_names.py` and `runtime_capture_import.py` (validates one bounded saved audio session) |
| | `webui/recovery/` | the debug-only Recovery page: `build_recovery.py` plus `recovery_declarations.json` (reviewed enum names, family rules, per-type entries and evidence text); reads reports, asset maps, the VFS index and `memory/game_data/README.md`'s level table; `jsondata_stages.py` authenticates the optional current registry and checks exact path-partitioned L2 declarations before publication |
| | `webui/decoded_payloads.py` | export-relative path to the `game_data` reader that owns it, rendered as diffable text |
| **Shared** | `common.py`, `source_paths.py`, `repo_paths.py` | helpers used by both lines; `repo_paths.REPO_ROOT` is the only repo-root anchor |
| **Tests** | `tests/` | stdlib `unittest`, untracked, run by explicit module path |

Dependencies point one way: shared helpers import neither line, line 1
imports only shared helpers, and line 2 imports both. A page builder calls a
`game_data` reader or contract instead of re-decoding bytes, and a helper that
both lines need goes in `common.py` under its own name, not in a private copy.
The local `tests/test_scripts_layout_boundaries.py` checks the direction
statically and at import time. The one sanctioned crossing is data: focused
asset export reads the published `webui/data` media references to scope which
textures it extracts. Line 1 never writes under `webui/data/`; a production
builder never imports or executes a recovery/audit module.

Every entry point runs as a module from the repository root, e.g.
`python -m scripts.webui.audio.build_audio`, with absolute imports and no
depth-computed repo root; run directly as a file it exits with the
`python -m` command to use instead.

## Root workflows

| Goal | Command |
| --- | --- |
| First-time Story/Text setup | `.\setup.bat` |
| Rebuild every page from the current export | `.\export.bat` |
| Rebuild named pages | `.\export.bat map audio` |
| Extract what every page reads, then build | `.\export.bat --from-game` |
| Extract and build one page | `.\export.bat map --from-game` |
| Lean Story/Text extraction and build | `.\export.bat story --from-game` |
| Extract every structured block and Unity class | `.\export.bat debug --from-game` |
| Sync installed game data and build every page, including Updates | `.\export.bat --changed-only` |
| Story recovery loop | `python -m scripts.webui.story.build --languages CN --default-language CN` |
| Mission Pipeline recovery (standalone, not WebUI) | `python -m scripts.webui.mission_pipeline.build_mission_pipeline_data --refresh-source-story-gap-queue` |
| Compare exports for Updates | `.\build_updates.bat OLD NEW` |
| Regenerate the export workflow SVG from the page registry | `python -m scripts.webui.export_diagram` |
| Rebuild the Recovery progress page | `python -m scripts.webui.recovery.build_recovery` |
| Check Recovery JsonData L2 declarations | `python -m scripts.webui.recovery.jsondata_stages` |
| Serve or package | `python serve.py` / `python -m scripts.webui.package` |

The wrappers load `endfield_paths.bat`, then apply explicit path flags.
`setup.bat` initializes only the required `tools/AnimeStudio` submodule, runs
`export.bat story --from-game --animestudio-story-monobehaviour-names`, then
prints the page follow-ups (`--no-serve` skips starting `serve.py`).
`tools/Cpp2IL-Endfield` is optional.

## Export rules

`export.bat` hands every argument to `python -m scripts.webui.export`. The one
source of truth for what a page needs is `scripts/webui/pages.py`: each build
task declares the export inputs it `reads` (must exist and be current) or
reads when present (`optional`), the same-page tasks it `needs`
(`check_pages_independent` refuses a cross-page edge), tasks it runs `after`
when both are in one build, inputs it `uses` but another page extracts, and
outputs it `serve`s at browse time (the Data page). A page run extracts the
union of its tasks' inputs and served outputs; served outputs are not
freshness-checked. `--show-plan` prints pages, tasks, scope and freshness
requirements without running anything.

| Target | Extracted with `--from-game` | Built |
| --- | --- | --- |
| `story` (`text`) | text only: Table, JsonData; TextAsset, MonoBehaviour, PlayableDirector JSON. Narrative video is read when another run extracted it (`uses`), reported as reused otherwise | Story and Text |
| `story-media` | `story` plus video, Texture2D, Sprite | Story and Text, `story_media.json` (`build_assets --publish story-media`) |
| `map` | Table, JsonData, Terrain height grids; Material JSON; Texture2D, Mesh | Map; its render colours come from the published Assets index |
| `characters` | Table; optional JsonData, Texture2D, Mesh, Sprite, Animator | Characters, including direct story speaker discovery; media through the published Assets index |
| `assets` | Table, video; Material JSON; Texture2D, Mesh, Sprite, Animator | the Assets index (`build_assets --publish index`) |
| `gameplay` | Table, JsonData; MonoBehaviour, PlayableDirector, MonoScript, Material JSON | Gameplay, projectiles, source graph, combat; asset links from the published Assets index |
| `production` | Table; reuses existing Texture2D/Sprite icons without extracting them | Gameplay's item sources and uses, recipes, encyclopedia building groups and dimensions, configured shop rewards, and upgrade references |
| `audio` | Table, JsonData; MonoBehaviour, PlayableDirector, animator-controller JSON; AnimationClip; CN audio decode | Audio, and the Story voice-line sidecars (`lang/CN/audio/conv/`) |
| `data` | everything decodable except other pages' media: Table, JsonData, Lua, whole Terrain; every Unity JSON class; AnimationClip, Shader, Font, TextAsset | the Data page's decoded datasets; its file viewer serves the rest |
| none, `all` | the union of the above, which with Data is everything | every page except Updates |
| `debug` | every structured block and Unity class (`scope.EVERYTHING`) | every page except Updates |

Behaviour `--help` does not give you:

- Without `--from-game` the build checks that every input its tasks read came
  from the installed build; a missing optional input only degrades its
  builder, a present stale one fails the run. `--skip-freshness` bypasses the
  check for one run.
- A page builds only itself and reads other pages' output as last published.
  No builder writes another page's output, so any build order is safe: Audio
  publishes its Story links as `lang/CN/audio/conv/` sidecars.
- MonoBehaviour and PlayableDirector are always exported together, and every
  such run republishes the object index. `--animestudio-story-monobehaviour-names`
  is accepted only for `story` and stamps that export partial.
- `--changed-only` applies the focused structured VFS delta, refreshes the
  remaining structured inputs, Unity outputs, indexes and CN/shared audio,
  then builds every page and Updates. Missing authenticated delta evidence
  falls back to full extraction. Managed snapshots under
  `reports/export/sync/` keep the last successful sync as the comparison
  baseline; failures retain it, and unchanged runs retain the last feed.
- `--webui-jobs N` bounds builders and Map's workers, `--asset-jobs N`
  AnimeStudio workers; `--full-source-graph` adds exhaustive PathID work.
  Options the wrapper does not own go to `export_full_from_game` and require
  `--from-game` or `--changed-only`; the latter owns the complete extraction
  scope. Keep wrapper files CRLF. Timings and a process-tree
  benchmark go to `reports/export/`.

### Exporter scope, provenance and stores

`python -m scripts.game_data.extraction.export_full_from_game` exports exactly
one `scope.ExtractionScope`; its docstring documents the presets, staging,
publication, scheduling and managed-reference diagnostics. Decoded blocks
publish into `game/`; `scope.RAW_BLOCKS` (Streaming, DynamicStreaming, IV,
ExtendData, IFixPatch, bundle manifest) publish byte-for-byte into
`<export root>/raw/`, shown only by the Data page. Bundles and audio packages
are never dumped. Provenance stamps live in `meta/extraction/provenance.json`;
`verify_export_freshness` checks `--require-structured`, `--require-unity`,
`--require-asset-map` and `--accept-reused` against them.

Unity object documents live in `game/Unity.sqlite` and the `PACKED_GAME_DIRS`
folders (`Json/LipSync`) in `game/GameFiles.sqlite`; converted media stays
under `game/Unity/<Type>/`. Read them only through
`scripts/game_data/unity_store.py` and `scripts/game_data/game_file_store.py`;
nothing falls back to loose files. A Sprite is a crop document over its
Texture2D (`scripts/game_data/sprite_crops.py`, rendered by
`webui/sprite_worker.js`). The Data page browses the stores through
`serve.py`'s read-only `/api/stores` (`webui/data_inspector/store_browser.py`).

```bat
python -m scripts.game_data.extraction.pack_export_stores --export-root export_full_1d5d1 --dry-run
python -m scripts.game_data.unity_store sql "SELECT name, doc(data, '$.m_Name') FROM objects WHERE type='TextAsset' LIMIT 5"
python -m scripts.game_data.game_file_store ls Json/LipSync "Chinese/*"
python -m scripts.game_data.sprite_crops check
```

## Main builders

| Area | Entry point | Main output |
| --- | --- | --- |
| Extraction, local delta and rolling snapshots | `game_data/extraction/export_full_from_game.py`, `export_changed_game_data.py`, `export_sync.py` | `export_full/`; delta state and managed snapshots under `reports/export/sync/` |
| Export freshness | `game_data/extraction/verify_export_freshness.py` | validation result |
| WebUI orchestration | `webui/export.py` (page registry `webui/pages.py`) | extraction, freshness, and every page's data |
| Story | `webui/story/build.py`, `refresh_evidence.py`, `source_links.py` | `webui/data/lang/<LANG>/`, `reports/story/` evidence, localized reference data |
| Mission Pipeline recovery | `webui/mission_pipeline/build_mission_pipeline_data.py` | standalone recovery reports/data |
| Map | `webui/map/build_map_recovery_data.py` (its docstring documents the `export.bat map` sequence, `--with-preview`, `--preview-only`, `--jobs` and the render cache) | `reports/assets/map_recovery/`, `export_full/recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/`, `webui/data/map_recovery/` |
| Map01 RegionMap3D package | `webui/map/build_map_region3d.py` | a self-contained package plus its provenance sidecar |
| Characters | `webui/characters/build_character_data.py` | character indexes, per-identity appearance sidecars, and versioned final-catalog snapshots |
| Decoded Data Inspector | `webui/data_inspector/build_data_inspector.py` | generic catalogs and lazy decoded-record shards |
| Gameplay | `webui/gameplay/build_gameplay.py` | Gameplay datasets; its `asset-refs` stage is the sole writer of `webui/data/assets/gameplay_refs.json` |
| Gameplay production catalogs | `webui/production/build_production.py` | `webui/data/production/manifest.json` and localized catalogs/shards under `lang/<LANG>/production/` |
| Assets | `webui/assets/build_assets.py` (`--mode default` for the served page) | asset indexes, `table_owners.json` and media lookup |
| Audio | `webui/audio/build_audio.py` | decoded/relinked audio plus compact semantic evidence and shards |
| Updates | `webui/updates/build_updates.py` | `webui/data/updates/{latest,characters,story,map,gameplay}.json` |
| Recovery progress | `webui/recovery/build_recovery.py` | `webui/data/recovery/index.json` |
| Packaging | `webui/package.py` | distributable static package |

Map's normal builder also runs `webui/map/build_map_encounters.py`; its focused
command refreshes only the encounter sidecars from Data's last publication.
`webui/map/interactive_catalog.py` supplies Map's exact Interactive template
and localized facility-name joins, plus structural display categories, from
the existing exported tables; the normal Map data build publishes them.
Map and Gameplay share `webui/data_inspector/publication.py` to validate that
publication before projecting their own views. Story/Text guide projections
live in `webui/story/reference_activity_guides.py` beside the existing
structured-field renderer. `webui/story/kite_station_tasks.py` projects
observation-station task definitions into mission-linked Story cards, including
the lean profile; it uses the existing Table and mission-flow inputs.

Gameplay's `--stage skill-refs` refreshes its skill/action/reference sidecars
from the current Data publication, with `--export-root` and `--game-root`
selecting the source export and native proof when needed. Normal Gameplay
runs include this stage; missing or stale optional sources remain visible.

For the reviewed single Map02 water footprint and its saved selected live
receipt, refresh only its existing render manifest, then attach that manifest
to the one published map payload:

```bat
python -m scripts.webui.map.build_map_recovery_preview --authored-water-only --level map02_lv002 --map-water-capture-session scratch/map_water_capture/map02_water_01 --map-water-live-report-output reports/map_recovery/map02_water_live_capture.json
python -c "from scripts.webui.map.build_map_recovery_data import refresh_render_backgrounds; refresh_render_backgrounds({'map02_lv002'})"
```

The focused commands validate `map_water_getmesh_native`,
`map_water_surface_join`, and the saved capture against the selected installed
build and export inputs; they do not render model geometry or scan other levels.
Without `--map-water-capture-session`, an authored-only refresh publishes only
the static source join.

`game_data/map_water_live_capture.py` validates saved water receipts against
the selected build and authored source. A retained Transform-position receipt
additionally requires repeated selected post-Tick samples, a stable source
token, no recycle or loss, and a final sample close to stop. Its position is a
bounded observation; it does not establish renderer visibility or an atomic
stop-time value.

`webui/package.py` emits four archives -- main, `-media`, `-audio` and an
optional `-resources`; their ownership and publication order are a contract
in [`../memory/webui_recovery.md`](../memory/webui_recovery.md). One
comma-separated argument selects a subset in build/publication order; no
argument builds all four. Gameplay dataset semantics are in
[`../memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md);
Gameplay can validate a saved tag-registry observation when the serialized
registry is incomplete.

```bat
.\pack_webui.bat story,audio,media,resource
.\pack_webui.bat story --dry-run
python -m scripts.webui.characters.build_character_data --languages CN --default-language CN
python -m scripts.webui.data_inspector.build_data_inspector --dataset levelscript-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset levelscript-template-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset spawner-config --dataset atmospheric-npc --dataset map-config
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-action-receipts
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset dynamic-components
python -m scripts.game_data.attribute_formula_native
python -m scripts.webui.assets.build_assets --mode default
python -m scripts.webui.gameplay.build_gameplay --stage base --languages CN --default-language CN --runtime-tag-capture scratch\reverse_engineering\gameplay_tag_runtime\capture.jsonl
```

Characters reads raw speaker Tables and optional NPC proxy Json independently
of generated Story data. `characters/story_speakers.py` owns speaker discovery
and bounded evidence samples; names without speaker ids remain unresolved
candidates. Use `.\export.bat characters` for a checked Characters-only rebuild.

## Story recovery

Production parsing, validation, attachment, and generated schemas live in
`webui/story/`. Audit and candidate-generation tools live in
`webui/story_recovery/`; they may import stable builder primitives, but
production builders never import or execute them.

| Module | Owns |
| --- | --- |
| `webui/story/refresh_evidence.py`, `source_links.py`, `build.py` | Story evidence refresh, localized reference data, the Story page data |
| `webui/story/dialog_registry.py`, `video_bindings.py` | dialog id registration, Story-to-video bindings |
| `webui/story/timeline_recovery.py`, `timeline_action_evidence.py` | Timeline recovery and typed Timeline action evidence |
| `webui/story/mission_recovery.py`, `scene_order_gap_shared.py` | mission reconstruction, shared scene-order gap logic |
| `webui/story/lua_consumer_references.py` | the fingerprinted Lua consumer index Mission Pipeline reads |
| `webui/story/source_gap/` | the canonical source-only Story gap queue (refreshed in process by Mission Pipeline) |

Mission Pipeline is standalone; the WebUI export does not run it. It reads the
Lua consumer index and the installed-build-gated
`game_data/contracts/cinematic_queue.json`; the full native carrier report is
not a production input. Standard extraction omits Lua, so refresh the index
only from an explicit complete plaintext-Lua extraction. Task RVAs, message
IDs and field offsets have one source, `game_data/contracts/mission_task_paths.json`,
read by the protocol registry and validated by the mission hook manifest.

Work in small validated batches (AGENTS.md, *Mission Recovery Edit-Loop
Policy*); a direct Story build takes several minutes, so allow at least 15 for
multiple languages or forced Timeline recovery. Timeline-order and
localized-reference reuse belong to the direct Story builder only and never
follow `--from-game`. Validators fail closed with actionable diagnostics in
both structured output and the CLI summary. Manual Story order is user-managed
in `webui/overrides/story_order.json`; OCR writes proposals to
`webui/data/story_order_ocr.json` and never replaces it. Each command's stages
and profiles are in its docstring; mission and audio runtime traces share the
fail-closed, import-only `runtime_trace` CLI with separate event schemas and
evidence boundaries.

```bat
python -m scripts.webui.story.lua_consumer_references --markdown
python -m scripts.webui.story_recovery.build_option_override_coverage_audit --language CN
python -m scripts.webui.story_recovery.ocr_story_order sample --dry-run
python -m scripts.webui.story_recovery.ocr_story_order match
python -m scripts.webui.story_recovery.ocr_story_order publish
python -m scripts.webui.story_recovery.ocr_story_order compare
python -m scripts.webui.story_recovery.audit_story_objects --stage reverse
python -m scripts.webui.story_recovery.audit_native_carriers cinematic
python -m scripts.webui.story_recovery.audit_native_carriers radio-forbid
python -m scripts.webui.story_recovery.runtime_trace import --profile mission CAPTURE.jsonl
```

## Assets and audio

`export.bat assets --from-game` refreshes the Assets inputs and index;
`export.bat audio --from-game` refreshes Audio's Unity inputs and decodes CN
audio; without `--from-game` both rebuild from the current export and reuse
decoded audio.

### AnimeStudio scheduling and DummyDlls

The default AnimeStudio type-job mode is `auto`: map-filtered conversion stays
sharded, broad Story JSON runs in isolated sequential processes. Do not add a
JSON type to map filtering until broad and filtered exports are byte-diffed,
and do not shard JSON export without new measurements. The DummyDll generator
consumes a tag-and-commit-pinned `Variante/Cpp2IL-Endfield` release; missing
or stale DummyDlls warn and fall back to serialized schemas, and native
registration addresses are never reused across builds.

```bat
python -m scripts.game_data.extraction.animestudio.generate_dummydll --dry-run
python -m scripts.game_data.extraction.animestudio.generate_dummydll --replace
python -m scripts.game_data.extraction.export_full_from_game --skip-structured --sources Persistent --animestudio-scope story --animestudio-stages json_by_type --animestudio-managed-reference-diagnostics --animestudio-managed-reference-diagnostic-type "AbilitySystemData$"
```

### Audio decode, indexing and semantics

`build_audio.py` is the single Audio command: decode (FLAC-only, pinned
vgmstream from `setup.bat` or
`scripts\game_data\extraction\animestudio\setup_vgmstream.bat`), Wwise
bank/HIRC indexing, relinking, the Gameplay and Story conversation sidecars,
then the semantic page data through its internal publisher
`build_audio_semantics.py`. Native Audio claims take the selected pair from
`--game-root` and never fall back to a module-global game path. Use direct
runs for non-CN languages or audio-only maintenance.

```bat
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
python -m scripts.webui.audio.build_audio --semantics-only --language CN --runtime-trace-bundle reports\story\recovery\audio_runtime_trace.json
python -m scripts.webui.audio.semantics.hirc_action_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.webui.audio.semantics.hirc_named_reach --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.webui.audio.semantics.play_sound_action_corpus
python -m scripts.webui.audio.semantics.native_play_sound_string --gameassembly GA --metadata META
python -m scripts.webui.story_recovery.refresh_audio_hook_catalog
```

A successful complete decode removes previously decoded files absent from
the validated emitted set in the selected language and shared storage. Partial
block refreshes, `--skip-decode` and semantic-only runs do not prune that set.

The HIRC gates write `reports/animestudio/hirc_*_current_latest.{json,md}`,
one per structural lane; what each framing establishes is in
[`memory/game_data/audio_overview.md`](../memory/game_data/audio_overview.md).
`play_sound_action_corpus` and `native_play_sound_string` are focused audits
under `reports/audio/`, not page builds. Outputs:
`webui/data/lang/<LANG>/audio/{index,events,media,scene_backgrounds}.json`,
`audio/conv/`, `gameplay/{sound_effects,projectile_audio}.json`, and native
audits under `reports/story/recovery/audio/`; projectile behavior stays
immutable in `webui/data/gameplay/projectiles.json`.

Reusable evidence owners live under `webui/audio/semantics/`. Add logic to its
owner rather than to either entry point, and add no compatibility re-exports,
duplicate native catalogs, broad `ImportError` fallbacks, or a second scan:
`native_evidence` (installed-build gate), `wwise_enums` (the one
`wwise_sdk_enums` loader), `identifiers`, `managed_literals`,
`responsive_voice`, `voice_requests`, `model_view_projection`, `interactive_components`, `authored_components`,
`table_contexts` (with the AudioCue expression AST), `audio_cue_native`,
`rtpc_contract`, `rtpc_alignment`, `scene_backgrounds`, `media_ownership`,
`name_recovery`, `authored_payload_event_names` (`gameplay_audio` keeps
SkillData/BuffData), `decoded_payload_event_names`, `play_sound_actions`,
`entity_contexts`, `conversation_sidecar`, and `event_projection`/`event_summary`.
`conversation_sidecar` includes per-conversation linked-file search text in its
index; `event_summary` includes the event detail's file references in list rows.
Story search rows and Data catalogs use the same `webui/search.py` extractor.
`webui.story.level_bindings` owns the LevelScript dynamic string property
resolution audio lifecycle evidence reads. Ownership and native-hook
boundaries are in
[`memory/game_data/audio_naming_coverage.md`](../memory/game_data/audio_naming_coverage.md)
and [`memory/game_data/audio_native_hooks.md`](../memory/game_data/audio_native_hooks.md).

### Saved runtime evidence

Runtime evidence commands validate and replay saved sessions offline. Selected
native inputs, exact profile recipes, source identities, complete sessions and
loss-free receipts remain required; failed gates publish no claims. Entry-only
recordings cannot supply historical paired-trace return or nesting evidence.

| Owner / command | Output / boundary |
| --- | --- |
| `python -m scripts.game_data.mission_trace_capture_prepare --help` | offline signature/field/ABI proof, including registered generic entries, reviewed anonymous assignment entries and closed reference-layout witnesses; `--profile mission\|buff` selects recording scope; optional `--recipe` selects a reviewed contract under `contracts/`; profiles under `reports/runtime_capture/` |
| `python -m scripts.game_data.mission_trace_source_archive --help` | retained mission context or `--profile buff` binary BuffData/available SkillData bytes and Buff tables; no current-native claim |
| `python -m scripts.game_data.mission_trace_inspect --session SESSION --output-dir reports/runtime_capture/INSPECTION --join-sources` | verifies saved identities, decodes typed fields and distinguishes observed from unobserved hooks |
| `python -m scripts.game_data.buff_runtime_trace_inspect --inspection-dir INSPECTION --output-dir reports/runtime_capture/BUFF` | complete Buff sessions: raw-bound reset/reference, assignment, initialization and separate dispatch-triplet evidence; skill initializer and stored-data/NewAction reference matches with reuse/conflict diagnostics; optional paired `--corpus-summary`/`--corpus-ledger` joins stored-schema receipts; no action result, data-node selection or ownership promotion |
| `python -m scripts.game_data.mission_trace_diagnose --session SESSION --output-dir reports/runtime_capture/DIAGNOSTIC` | bounded failed-journal diagnostics by hook/field; preserves originals and never admits incomplete captures |
| `python -m scripts.game_data.mission_shared_native --gameassembly GA --metadata META` | `reports/runtime_capture/mission-shared-native.json`; Mission lifecycle, condition selection, dialog, LevelScript and interactive-property consumer claims gate selected inputs before and after evaluation |
| `python -m scripts.webui.story_recovery.runtime_trace import --profile mission CAPTURE.jsonl` | saved Mission/Story event-schema validation and evidence bundle |
| `python -m scripts.webui.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl` | saved Audio event-schema validation and evidence bundle |
| `python -m scripts.webui.story_recovery.prepare_audio_source_observer --game-root "PATH\Endfield Game"` | reconstructs the exact saved-profile recipe and validates selected native bodies, signatures and manifest ranges under `reports/audio/` |
| `python -m scripts.webui.story_recovery.audit_audio_source_capture --game-root "PATH\Endfield Game" --manifest PROFILE.json --input CAPTURE.jsonl --output reports/audio/source_observer_capture_audit.json` | strict immutable-snapshot, sequence, pairing, field and clean-stop audit using the saved profile and adjacent diagnostics |
| `python -m scripts.webui.story_recovery.prepare_endfield_source_owner --game-root "PATH\Endfield Game"` | `reports/audio/endfield_source_owner_manifest.json` and offline preflight; selected source/queue/carrier gates |
| `python -m scripts.webui.audio.semantics.source_owner_capture --session SESSION --game-root "PATH\Endfield Game"` | strict saved native-entry audit; staged recipe/runtime, closed windows and receipt gates |
| `python -m scripts.webui.story_recovery.archive_runtime_capture save --session-id ID --kind audio-source --input ROLE=PATH` (repeat `--input`; optional repeated `--note`) | ZIP with SHA256 inventory at `reports/audio/captures/ID.zip`; retain trace, diagnostics, session profile and preflight |
| `python -m scripts.webui.story_recovery.archive_runtime_capture verify reports/audio/captures/ID.zip` | verifies archived bytes against the inventory; preservation alone does not prove recording correctness |
| `python -m scripts.webui.story_recovery.audit_capture_crash_dump --input CLOSED.dmp --output reports/audio/crash_dump_audit.json` | bounded offline minidump framing, exception/context and module ranges; optional `--compare-dbghelp`; incomplete memory cannot establish cause |

`runtime_trace_audio_manifest` owns offline profile-shape and module-address
validation. `source_observer_profile` owns pure profile recipes; the optional
`--include-source-consumer`, `--include-source-bridge` and
`--include-owner-carrier` preparation flags reconstruct separately gated
historical recipes. Each saved trace keeps its own frozen manifest and
diagnostics. For larger recordings, explicitly raise the auditor's
`--max-input-bytes` and `--max-events`; all admitted rows still pass the same
checks. Pointer matches never establish lifetime, file, codec or audibility
ownership.

Publish a saved native-entry session through the single Audio command:
`python -m scripts.webui.audio.build_audio --semantics-only --game-root "PATH\Endfield Game\Endfield_Data" --native-entry-session SESSION`.
For an existing publication, `--native-entry-only` refreshes just that evidence
and writes `reports/audio/endfield_native_entry_refresh_latest.json`. It is
exclusive with `--semantics-only`, decode/HIRC options and runtime-trace import.
`--native-entry-package-index INDEX` adds bounded header/encoded-word candidate
comparisons; `--native-entry-decode-witness RECEIPT` also requires that index and
revalidates a prior offline PCM comparison. Neither establishes a live backing
filename or read-to-codec relation.

For paired source observations, import with repeated
`--source-observer-manifest TRACE=PROFILE` associations and explicit
`--game-root`. Every associated trace must also be a positional input and
receives a fresh strict audit. `--source-max-input-bytes` and
`--source-max-events` control the recorded budgets. Then use
`build_audio --semantics-only --runtime-trace-bundle BUNDLE` with selected native
inputs. `--runtime-source-only --runtime-trace-bundle BUNDLE --game-root GAME_DATA`
re-audits the published source/owner child, requiring matching bundle path and
SHA, and writes `reports/audio/runtime_source_refresh_latest.json`. Anonymous
native rows never gain Event/media ownership from these summaries.

`runtime_capture_import` owns saved-session admission; `managed_post_observations`
owns local managed argument/result pairs. `source_io_observations`,
`package_read_observations`, `package_read_witness` and `package_decode_witness`
own the independent retained-provider, transfer, encoded-word and decoded-PCM
children. Their identities and evidence limits are documented in
[`../memory/game_data/audio_native_hooks.md`](../memory/game_data/audio_native_hooks.md).

`python -m scripts.game_data.wwise_decoder_provider_native --gameassembly GA --metadata META --ak-sound-engine AK`
authenticates static decoder/owner/source reads. `--include-storage`,
`--include-dispatch`, `--include-package` and `--include-retention` add independently
gated groups while reusing opened images. `semantics/source_provider.py`
publishes the static result through `build_audio --semantics-only`.

`build_audio --package-catalog-only --package-input-set-sha256 SHA` refreshes the
static package inventory in an existing publication. The raw gate,
`game_data/wwise_package_corpus --expected-input-set-sha256 SHA`, authenticates
available PCKs against the VFS roster and logical-payload hashes, then writes
`reports/audio/package_corpus_current.json`. `game_data/wwise_package.py` owns
AKPK framing and shared media/header crypto; `semantics/package_catalog.py`
owns the page projection. Missing packages, duplicate keys and low-word
collisions remain explicit. Full semantic builds revalidate the existing roster.

## Updates

`export.bat --changed-only` synchronizes the installed client, then calls the
same Updates builder with an exact comparison against the last successful
sync. Its initial old export can come from `ENDFIELD_PREVIOUS_EXPORT_ROOT`
or `--previous-export-root`; later runs manage their own complete snapshots.

Updates compare two complete layout-v4 export folders. Pass `OLD NEW`, or
configure `ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` in
`endfield_paths.bat`; a named `OLD` refreshes the cached baseline under
`.game-data-tracker/`. `build_updates.py` calls the `webui/updates/scanner.py`
API in process; the scanner is not a second CLI.

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --text-only
.\build_updates.bat --prune-old --dry-run
python -m scripts.webui.updates.build_updates --refresh-previous-export-baseline
```

The default scan covers WebUI-facing exported text plus image, model, video
and decoded audio assets. `--text-only` omits all assets, `--no-audio` keeps
other assets, `--exact` hashes contents, and `--full-export-scan` (broad
audits only) expands both SQLite stores into per-document entries. Text is
classified by content and rendered through the reader `webui/decoded_payloads.py`
routes to; changing that routing requires refreshing the baseline. Relocation
matching, exclusions and `--sample-limit` are in `build_updates.py`; the
Characters sidecar rules are in `webui/updates/characters.py`;
`webui/updates/page_records.py` compares authored Story conversations, Map
levels, Gameplay and Production source records for optional page badges and previous/current
field and linked-file comparisons, independently of asset flags and sample
limits. Linked-file previews reuse the feed's bounded maintained readers.
Pruning is
destructive: preview with `--dry-run`; the guard rejects the current export
and repository root and never touches a Unity object store.

## Native evidence and source graph

Steps that read `GameAssembly.dll` or `global-metadata.dat` validate the exact
installed build first. Missing or mismatched inputs skip only that step and
leave its published report untouched; set `ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1`
when an audit must fail hard. The source graph is rebuilt after semantic views:

```bat
python tools\endfield_source_graph.py build
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Reviewed per-build native facts are tracked data in
`scripts/game_data/contracts/`, loaded by the `*_native.py` modules, which
check the installed build against `nativeInputs` and native code against
recorded hashes, never a contract's own bytes. Claims contracts
(`dialog_finish_native.json`, `story_native_consumers.json`, `*_claims.json`)
are re-proved by `il2cpp/body_claims.py` on whichever build is installed.
Generated artifacts made on one build (the reverse-PPtr audit,
`webui/story/dynamic_scene.json`, `contracts/audio_native.json` rows) are
current only while their native hashes match. Read the native-contract rules
in `AGENTS.md` before adding or regenerating a contract.

### Shared invocation pattern

Validators and corpus gates share one flag vocabulary; each module's
docstring (its `--help` text) names the flags it takes and its default report.

| Flag | Meaning |
| --- | --- |
| `--expected-input-set-sha256 SHA` (`--input-set-sha256` in `streaming.*`) | the `inputSetSha256` of the current `vfs-audit` summary; the gate reauthenticates the outer VFS ledger and refuses a mismatch. The value also fingerprints the AnimeStudio CLI binary, so rebuilding the exporter invalidates the audit and every gate below it: re-run the audit, never edit a recorded value |
| `--game-root ".../Endfield_Data"` or `--gameassembly GA --metadata META` | the explicit selected native pair; a missing or different build yields no validated rows |
| `--export-root export_full/game/Json --ledger reports/animestudio/jsondata_current_files_latest.jsonl.gz --summary reports/animestudio/jsondata_current_latest.json` | joined source replay against the complete JsonData corpus receipt; pass the three together |
| `--input-root DUMP_ROOT` | a targeted `AnimeStudio.CLI dump` tree holding the named `Data/...` files, authenticated by VFS MD5 |
| `--buff-report`, `--action-report`, `--corpus-report` | the upstream gate report a receipt rejoins (`buffdata_current_latest.json`, `buff_action_receipts_current_latest.json`, ...) |
| `--limit`, `--max-files` | bounded diagnostics only; output belongs in `tmp/` or `scratch/` and never certifies a corpus |
| `--output`, `--out`, `--report`, `--output-json`/`--output-md` | report path; defaults live in the module |

The chain starts with the bundle-free VFS audit, which returns non-zero for
any missing or unauthenticated declaration while still publishing its ledger:

```bat
set ASCLI=tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
%ASCLI% vfs-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --summary-json reports\animestudio\vfs_understanding_latest.json --ledger-jsonl-gz reports\animestudio\vfs_understanding_files_latest.jsonl.gz --report-md reports\animestudio\vfs_understanding_latest.md
%ASCLI% vfs-inner-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --block-type initial-bundle --block-type bundle --output reports\animestudio\vfs_inner_understanding_files_latest.jsonl.gz --summary-json reports\animestudio\vfs_inner_understanding_latest.json
%ASCLI% dump --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --output tmp\animestudio\bundle_manifest --block-type bundle-manifest --verify-md5
python -m scripts.game_data.memorypack.buff_corpus --expected-input-set-sha256 SHA
python -m scripts.game_data.memorypack.skill_corpus --expected-input-set-sha256 SHA
python -m scripts.game_data.jsondata_corpus --expected-input-set-sha256 SHA
```

When an audit uses a retained CLI copy, pass its recorded path with `--cli`
to the corpus gates that stream bytes; their default executable is a different
build input even when its apphost bytes match.

The CLI's object-index diagnostics (`inspect-object`, `audit-refs`,
`certify-index`, `replay`, `schema-diff`, `shader-recover`) take JSONL or
`.jsonl.gz` indexes; `certify-index` requires a complete terminal summary row
and `replay` takes one `{ "pathId": N, "source": "...", "type": "..." }`
request per line. Keep probes under `scratch/animestudio/`. **What each gate
proves and leaves open is in its docstring and in
[`memory/game_data/extraction_payload_boundaries.md`](../memory/game_data/extraction_payload_boundaries.md)**
-- do not restate a boundary here.

### Validator and gate families

Module names are relative to `scripts.game_data` unless shown in full; reports
are under `reports/animestudio/` unless another directory is shown.

| Family (modules) | What it checks | Report |
| --- | --- | --- |
| `terrain.corpus` | TRET tile groups, D/N layer pairing, GraphicsFormat and header shapes by path family | `terrain_tret_latest.{json,md}` |
| `terrain.{layer_paths,tile_slots,layer_slots,virtual_texture_managed,manager_bridge}_native`, `terrain.shader_sampling` | selected native path templates, tile and layer render-property slots, managed texture handoff, Terrain-manager bridge, authored shader sample | `reports/terrain/` |
| `irradiance_path_native`, `irradiance_volume_corpus` | IV V3 path construction, stream route and cursor; every current IV index and room against the VFS ledger, with the checked per-magic index-word additive relations | `reports/irradiance/` |
| `dynamic_stream_area_corpus`, `dynamic_aux_pair_corpus` | DynamicStreaming `FBStreamArea` and paired `fb_init`/`fb_streaming` framing over authenticated VFS bytes | `dynamic_*_latest.*` |
| `dynamic_scalar_components_native` | native field layouts and direct authored MissionCondition string-slot consumer, plus current main-file census; explicit `--gameassembly`/`--metadata`, `--input-root`, `--expected-input-set-sha256` | `dynamic_scalar_components_native_latest.{json,md}` |
| `dynamic_*_native` (main, data_index, system_routing, root_comp, resource_comp, sludge_surf_tile, stream_area, version, version_ban, active_version, aux_bridge, visibility_runtime) | selected-build layouts, accessors and call chains, rejoined to a targeted dump (`--input-root`) where they read stored records | `dynamic_*_native_latest.*`, `dynamic_visibility_runtime_claims_latest.json` |
| `dynamic_{visibility_area,visibility_state,streaming_config,main_path}_join`, `dynamic_version_id_domain`, `portal_center_join` | joins of validated native reports with the area corpus, MapConfig, exports and LevelData portals | `dynamic_*_latest.*`, `reports/game_data/portal_center_join_latest.json` |
| `bundle_manifest_{corpus,native}`, `bundle_cab_dependency_corpus`, `bundle_cab_exceptions`, `bundle_external_identity_corpus` | `manifest.hgmmap` from the bundle-manifest dump (`--manifest`); CAB dependencies against `export_full/meta/cab_map` | `bundle_*_latest.json` |
| `string_path_hash_{native,corpus}` | path-hash catalogs against VFS and manifest hashes (`--scope main` or `initial`, kept in separate reports) | `string_path_hash_*_latest.json` |
| `extend_data_*` (compress_corpus, graph_native, graph_owner_corpus, graph_ai_native/corpus, spawner_library_native/corpus) | ExtendData graphs, owners and spawner-library joins | `extend_data_*_latest.json` |
| `ifix_vm_{instruction,operands}_native`, `ifix_external_signatures_native` | IFix VM opcodes, operand joins and extern signatures over supplied patch dumps | `ifix_*_current.json` |
| `streaming.corpus`, `streaming.marker{17,13,2}_corpus`, `streaming.marker15_gap_corpus` | block-15 root subgraphs and marker bodies (`marker15_gap` takes `--scene`) | `streaming_*_latest.*` |
| `streaming.descriptor_{name_corpus,names,component_index_gate,mask_corpus}` | Init slot-7 descriptor names and anonymous mask positions | `reports/chunk_data/` |
| `jsondata_corpus` | identity and routing of every JsonData file, with a per-file status consumers gate on; `--buff-report`/`--skill-report` select complete family receipts without overwriting a historical cursor basis; failed runs preserve prior publications and record bounded validator/predicate/source-hash diagnostics; unsafe output aliases fail before companion publication | `jsondata_current_latest.{json,md}`, `jsondata_current_files_latest.jsonl.gz`, companion `.validation.json` |
| `jsondata_schema_coverage` | named bytes per family and bucket, ranked by unnamed bytes (never read `bytesConsumed` as coverage) | `reports/game_data/jsondata_schema_coverage*.json` |
| `levelscript_first_stop_census` | reruns the LevelScript sequential owner on every `bounded_partial` file of the JsonData receipt and ranks first refusals by whole files (`--expected-input-set-sha256`, plus `--summary`/`--ledger`/`--export-root`) | `reports/game_data/levelscript_partial_first_stops_current.json` |
| `levelscript_on_squad_member_usp_native` | `--game-root` or explicit `--gameassembly`/`--metadata`: authenticate parent typed reads and isolated child grammars; shared provider selection remains unresolved and the canonical owner refuses positive headers | CLI audit only; direct outer-wrapper null branch is supported |
| `levelscript_pos_rot_native` | `--game-root`: authenticate the isolated PosRot two-member field order against selected native inputs; the positive parent list/provider join remains unresolved and is refused by the LevelScript owner | CLI audit only; no positive-list admission |
| `gpu_ui_corpus`, `levelscript_fmv_video_corpus`, `leveldata_bezier_knot_corpus`, `leveldata_spline_runtime_native`, `map_mark_relations` | GPUI named schemas; LevelScript `moviePath` to Video; LevelData knot frames; spline consumer; GameplayConfig map-mark joins | `gpu_ui_current_latest.json`, `reports/story/recovery/`, `reports/game_data/` |
| `memorypack.skill_corpus`, `memorypack.skill_timeline_cursor`, `memorypack.skill_cursor_*`, `il2cpp.skill_cursor_*` | SkillData whole-file gate and the saved cursor-receipt verification chain | `skilldata_*_latest.*` |
| `memorypack.skill_corpus --source-corpus BASIS --expected-source-corpus-sha256 SHA` | Selection-only replay of a complete current all-unselected basis: authenticate every ledger identity and current parser/native/catalog/CLI/chunk receipt before and after, then apply the existing cursor/capture flags without another VFS stream; keep `--output` distinct from the basis | complete report with `provenance.selectionReplay`; helper owner: `memorypack.skill_corpus_replay` |
| `memorypack.skill_cursor_wulfa_scope`, `il2cpp.skill_cursor_native_context --scoped-wulfa`, `memorypack.skill_cursor_capture_target --scoped-wulfa` | Reuse the Wulfa one-source VFS row plus authenticated controls for offline source/native validation and saved-receipt checks | scoped native context and diagnostic receipt verification under `reports/animestudio/` |
| `memorypack.skill_cursor_wulfa_terminal` | Replay the verified Wulfa-only receipt and join its selected terminal cursor to exact static fields 0-42 and ActionGroup children; the reviewed selection contract is `skill_cursor_wulfa_terminal_selection.json` | `reports/animestudio/skilldata_cursor_wulfa_terminal_latest.json` (one-source diagnostic) |
| `memorypack.skill_cursor_seraph_capture` | Authenticate the Seraph ultimate source binding and controls, then verify the saved v3 target-set receipt; reports only the observed cursor | `reports/animestudio/skill_cursor_seraph_ultimate_context_latest.json`, `skilldata_cursor_seraph_ultimate_verification_latest.json` |
| `memorypack.skill_cursor_seraph_terminal` | Replay the verified Seraph-only receipt and join the selected terminal to the exact static `0x009F` action, ActionGroup and fields 0-42 | `reports/animestudio/skilldata_cursor_seraph_terminal_latest.json` (one-source diagnostic) |
| `memorypack.skill_cursor_scoped_group` | Validate a reviewed 1-32 source v3 binding (`--contract`), then require every copied source and cursor to close in a loss-free saved receipt. Contract v1 checks one selected VFS report; v2 combines authenticated one-source reports without re-streaming unchanged chunks | `reports/animestudio/skill_cursor_scoped_group_{context_latest.json,binding.txt}`, `skilldata_cursor_scoped_group_verification_latest.json` (cursor-only diagnostic) |
| `memorypack.skill_cursor_lizhiyan_pograni_join` | Replay the reviewed grouped receipt and current one-source report fingerprints; join selected native-gated ActionGroups and fields 0-42 to the observed terminal cursors in the Lizhiyan combo and Pograni ultimate sources | `reports/animestudio/skilldata_cursor_lizhiyan_pograni_join_latest.json` (two-source diagnostic; family publication remains separate) |
| `memorypack.skill_timeline_{check_ability_entity_cur_duration,set_ability_entity_duration,voice_interrupt,perfect_dodge_direction,change_specific_layer}`, `memorypack.skill_cursor_zhuangfy_*_join` | Five selected-native route readers and four saved source/cursor joins. The saved join reports remain historical diagnostics: their frozen VFS basis carries the parser fingerprint from before shared admission, so the strict current-source gate rejects a fresh join run until a reviewed rebind or current basis exists | saved `reports/animestudio/skilldata_cursor_zhuangfy_*_join_latest.json` (nonpublishable) |
| `memorypack.skill_timeline_shared_sequence` | Shared SkillData reader authenticates each admitted domain contract, including CheckSkillHasHit, SetIgnoreGlobalTimeScale and DispelAction; `memorypack.skill_corpus --target-virtual-path PATH` remains a bounded diagnostic under the current VFS audit | diagnostic output under `tmp/` or `scratch/`; complete-family gate remains the publication boundary |
| `memorypack.skill_timeline_set_ignore_global_time_scale` | Native-gated SetIgnoreGlobalTimeScale action reader; standalone `--source`, `--gameassembly`, `--metadata`, `--output` inspects the selected Pograni source; the shared reader consumes the same grammar after its own selected-build gate | shared route consumed by `memorypack.skill_corpus`; standalone output nonpublishable |
| `memorypack.skill_sparse_corpus_compose` | Compose authenticated prior controls with newly streamed unknown SkillData sources (`--controls`, `--unknowns`, `--old-parser-source`, `--family-verification`, repeated `--expected-unknown`); route rebind also takes `--old-shared-parser-source` and `--old-shared-contract`, proving exact route additions and the reviewed HurtAnim promotion did not affect controls | caller's diagnostic `--output` under `tmp/` or `scratch/` |
| `memorypack.skill_timeline_check_skill_has_hit` | Native-gated CheckSkillHasHit action decoder admitted through the shared reader; `--source`, `--corpus-report`, `--virtual-path`, `--output` retains the one-source diagnostic | shared route consumed by `memorypack.skill_corpus`; standalone output nonpublishable |
| `memorypack.skill_timeline_dice_float` | Isolated selected-native `DiceFloat` action decoder joined to one current SkillData source (`--source`, `--corpus-report`, `--virtual-path`, `--output`); does not publish a family result | caller's diagnostic `--output` under `tmp/` or `scratch/` |
| `memorypack.skill_timeline_move_to_slot` | Selected-native `0x00FA` MoveToSlot action reader and 17-member contract; the shared SkillData parser admits it only after the current native gate | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_log_action` | Selected-native `0x00E5` LogAction reader and ten-member contract, including two bounded string payloads; admitted through the shared native gate | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_hurt_anim` | Selected-native `0x00C8` HurtAnim reader and ten-member contract ending in TargetSettings; replaces the former derived-only composite route | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_save_buff_stack_num_by_tag` | Selected-native `0x0137` SaveBuffStackNumByTag reader and eight-member contract with TargetSettings, bounded key and GameplayTagQuery children | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_fracture` | Selected-native `0x00BE` FractureAction reader, reusing reviewed Buff frontier9 source order and nested contexts | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_show_combo_skill_ui` | Selected-native `0x015F` ShowComboSkillUI four-member reader, reusing reviewed Buff residual frontier and derived wrapper plan | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_try_teleport_squad` | Selected-native `0x018C` TryToTeleportSquadAction four-member reader and reviewed source-order contract; closes one action but leaves later Wulfa timeline framing to the shared parser | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_anim_event_receiver` | Selected-native `0x0012` AnimEventReceiver seven-member reader with a reviewed nested SequenceActionData; `--source`, `--corpus-report`, `--virtual-path` isolate a current first stop | diagnostic `--output` under `tmp/` or `scratch/`; shared parser route consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_continuous_anim_time_scale` | Selected-native `0x008B` ContinuousSetAnimTimeScale five-member reader with `BlackboardDouble` child; closes Wulfa's ActionGroup while terminal selection stays source specific | consumed by `memorypack.skill_corpus` |
| `memorypack.skill_timeline_dispel` | Native-gated DispelAction nine-member reader, reusing the reviewed Buff source order and nested contexts; admitted through the shared reader | consumed by `memorypack.skill_corpus` |
| `memorypack.{buff,buff_1b,npc_montage,lipsync}_corpus` | whole-family MemoryPack gates | `*_current_latest.{json,md}` |
| `memorypack.buff_*_receipt`, `memorypack.buff_*_child_corpus`, `buff_action_receipt_corpus`, `buff_create_action_root_corpus`, `buff_stacking_compact_corpus`, `buff_shared_nested_receipt_corpus` | per-route selected-native readers replayed on current source bytes; the Buff root admits only the compositions each docstring names | `buff_*_current_latest.json` |
| `memorypack.buff_damage_gradual_condition_receipt` | `--buff-report`, `--export-root`, `--source`, `--expected-input-set-sha256`, `--output`: join one selected gradual Buff source to current native and prior complete-report receipts, then verify the exact condition and whole-root EOF | caller's `--output` under `reports/` |
| `memorypack.buff_heal_check_tag_selected`, `memorypack.buff_heal_processor_zero` | `--input`, `--source`, `--audit-report`, `--buff-report`, `--output`: replay the selected positive heal modifier's native-audited condition and tag-zero processor; the root's `decode_selected_positive_heal_buff` composes them with its 30-field reader | caller's `--output` under `reports/` (selected diagnostics) |
| `memorypack.buff_selected_roots` | Shared source-bound positive-heal, BreakPassing event-map, attribute-plus-empty-condition/tag-ten and recursive sword damage root admission and canonical replay, consumed by `buff_corpus` and `jsondata_corpus`; the Buff gate's `--selected-native-audit` defaults to the existing current IL2CPP context audit without rerunning it | complete-family `selectedSourceRoots` cohorts and registry replay input pins; standalone selected diagnostics stay nonpublishable |
| `memorypack.buff_attribute_modifier`, `memorypack.buff_residual_census` | Shared native-gated AttributeModifierData reader; residual census authenticates the family/source receipt, excludes exact roots and ranks recorded shared-event refusals; `--replay-no-positive` replays ordinary roots, `--replay-shared-events` replays eligible event-map roots and ranks actual first child refusals | shared Buff root admission; `reports/game_data/buff_residual_census_latest.json`, never standalone family promotion |
| `memorypack.buff_event_maps`, `memorypack.buff_recursive_actions` and their control, ID/string, selector/geometry child owners | Distinct Ability/Buff event-map read orders and recursively named action/selector children under typed native joins; bounded list counts are independent of selected fixture names | shared root receipt through `buff_corpus` and canonical JsonData replay; unsupported nested unions refuse admission |
| `memorypack.buff_skill_stack_interrupt_actions`, `memorypack.buff_selector_distance_validator` | Named skill/ATB-gain/stack conditions, cooldown, mode switching, interrupts and Buff duration configuration; independent child extents and selected native joins gate composition | shared event-map and selector-list children through `buff_corpus`; stored operands do not establish live condition results or lifetime writes |
| `memorypack.buff_vitals_actions`, `memorypack.buff_data_transfer_actions`, `memorypack.buff_probability_action`, `memorypack.buff_entity_count_action`, `memorypack.buff_notify_char_passive_ui_action`, `memorypack.buff_id_actions` | Original-span composition of vitals and entity-count conditions, skill-setting reads, battle signals, target Buff blackboards, stack storage, scalar calculations, attribute storage, probability, passive UI storage and cooldown actions; independently bounded targets, finders, providers and nullable lists | shared event-map children through `buff_corpus`; whole-root and canonical replay gates still apply |
| `memorypack.buff_cost_action`, `memorypack.buff_timed_marker_condition` | Named stored resource-cost and timed-marker parents with independent targets/providers; `named_native_records` authenticates explicit closed unmanaged source reads and separately proves registered and optimized native entries when they differ | shared event-map children through `buff_corpus`; stored operands do not establish live results; whole-root and canonical replay gates still apply |
| `memorypack.buff_super_armor_condition`, `memorypack.buff_debug_print_action` | Named armor comparison and debug-print storage; inline color requires an independent sixteen-byte source copy, cursor advance and runtime-field destination proof | shared event-map children through `buff_corpus`; comparison/log results remain unresolved |
| `memorypack.animation_curve`, `memorypack.buff_curve_actions` | Named AnimationCurve wrap words and seven Keyframe words proved by closed array type and independent source/cursor/destination programs; time-dilation, hurt-animation and hit-stop parents compose original-span children and explicit unmanaged tag reads | shared event-map children through `buff_corpus`; null/empty lists and curves remain distinct, evaluation and effects remain unresolved |
| `memorypack.buff_marker_mask_actions` | Named timed-marker creation and tag/object/physical-infliction/spell-infliction/target-equality conditions; independent Blackboard, target and query receipts, with explicit typed output-buffer transfer for the query | shared event-map children through `buff_corpus`; runtime copy extent is distinct from serialized grammar, marker lifetime and predicate results remain unresolved |
| `memorypack.buff_tag_sequence_actions`, `memorypack.buff_sequence`, `memorypack.buff_spawn_entity_action`, `memorypack.struct_output_sources` | AddTag and ForEach use independently typed tag elements and shared recursive sequences; SpawnAbilityEntity proves distinct raw12 source/registered entries and inline raw16 transfer before composing original-span children | shared event-map children through `buff_corpus`; null/list distinctions and receiver identity remain checked, tag attachment and entity execution remain unresolved |
| `memorypack.buff_camera_impulse_action`, `memorypack.value_wrapper_sources` | CameraImpulse independently joins impulse definitions, inline envelope fields, curves and targets; explicit inline raw12 cursor/copy and provider output32 transfers keep wire framing separate from runtime extent | shared event-map children through `buff_corpus`; curve evaluation, formatter selection and camera execution remain unresolved |
| `memorypack.buff_leaf_actions`, `memorypack.buff_spell_infliction_action` | Independently named leaf actions include MoveGait's separate max/min enum operands; the spell event composes its own TargetSettings followed by both required enum operands; physical tags and null-wrapper states remain checked | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, movement, event dispatch and spell attachment remain unresolved |
| `memorypack.buff_animation_sequence_actions` | PlayAnimation composes independently decoded original UTF-8 strings, raw float bits and its own ending sequence; JumpTo composes its distinct condition sequence followed by the required Int32 destination frame; current named source/destination and dispatcher proofs gate both | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, animation, callback results and frame jumps remain unresolved |
| `memorypack.buff_direct_target_actions`, `memorypack.buff_custom_ability_event_condition` | Named head-bar/poise-break target actions and custom event storage; each new parent has independent source/destination and dispatcher joins, original target/BlackboardString children, null distinctions and required fields; the event's saved parameter key additionally has a current UTF-8 source proof | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, selected targets, recovery, event matching and parameter capture remain unresolved |
| `memorypack.buff_keyword_actions` | Independently named vulnerable, shelter, slow, speedup, weak, enhanced and infliction storage; separate KeywordEnhanceEdit elements and bounded raw-string lists; each parent retains its own required list suffix and original-span provider/target receipts | shared event-map children through `buff_corpus`; null/list distinctions remain explicit, edits and infliction effects remain unresolved |
| `memorypack.buff_launch_projectile_action` | Complete named projectile storage, four explicit inline Vector3 programs, independently named preset-point elements and shared AssignPair children | shared event-map children through `buff_corpus`; original spans and required tails gate composition, emission and trajectories remain unresolved |
| `memorypack.buff_ignite_text_action` | Complete named text action storage; independent direct/registered raw Vector2 reads, cursor helper, full return argument and typed getter/setter field transfer | shared event-map children through `buff_corpus`; original target spans and required final payload remain checked, displayed text and gameplay effects remain unresolved |
| `memorypack.buff_global_creation_action`, `memorypack.buff_switch_action` | GlobalBuffInput/GlobalBuffId with assignments and an explicit addressed string reference proof; Switch Option with independently typed recursive sequence and BlackboardDouble | shared event-map children through `buff_corpus`; original child ranges, null/list distinctions and bounded recursion remain checked, live creation, lifetime and branch effects remain unresolved |
| `memorypack.buff_finish_global_action`, `il2cpp.formatter_composition` | FinishGlobalBuff parent with independently owned Blackboard scalar and reviewed conditional original-value ID list; exact source-list registration, generic/interface identities, buffered count/null/conversion programs and required final flag | shared event-map child through `buff_corpus`; original action spans and complete root/canonical gates decide admission; live provider/IFix selection, evaluated IDs/count and finishing effects remain unresolved |
| `memorypack.buff_blow_off_character_action`, `memorypack.inherited_reference_sources` | BlowOffCharacter parent and its distinct four-member priority child; closed generic ancestry, metadata-owned VAR ordinal, actual inherited setter destinations and buffered primitive widths | shared event-map child through `buff_corpus`; original spans and root/canonical gates decide admission; getter cache/cast success, evaluated priority, target selection and blow-off effects remain conditional or unresolved |
| `memorypack.buff_cast_skill_action`, `memorypack.buff_animator_param_action` | CastSkill composes independent caster/target settings and a paired BlackboardString; SetAnimatorParam composes two independently nullable named AnimatorParamAction records | shared event-map children through `buff_corpus`; full original spans and root/canonical gates decide admission; skill execution, cost/interrupt decisions and animator effects remain unresolved |
| `memorypack.buff_selector_fixed_point_finder`, `memorypack.struct_output_sources` | FixedPointFinder proves separate inline raw12/raw16 source/cursor/complete-transfer programs, its selected finder route and independently owned Blackboard radius | shared recursive selector child through `buff_corpus`; raw geometry/flag bits and null states remain distinct; navigation sampling and selected targets remain unresolved |
| `memorypack.buff_selector_postprocessors`, `memorypack.buff_direction_target_children`, `memorypack.reference_output_sources`, `memorypack.setter_output_sources` | Nullable postprocessor lists and recursive Direction children with typed reference transfers, owned generated-setter outputs and strict original spans | shared target, FindTarget and hurt-animation composition through `buff_corpus`; CircularOrderSort/Projection/ExcludeTarget/NavMeshPathPositionProcessor/PriorityFilter/ShuffleTarget retain named operands; normal transfers remain conditional, runtime processing unresolved |
| `memorypack.buff_timeline_element_sources`, `memorypack.buffered_owned_sources` | Independently gated positive Timeline/ForceSync source wrappers: complete buffered primitive/inline cursor programs, ordered owned stores and original absolute element spans with separately gated Sequence/UTF-8 children | library diagnostics only; `positiveSourceFieldsExact` does not admit nullable runtime adapters, a positive list or a Buff root |
| `memorypack.buff_timeline_composition`, `il2cpp.formatter_registration` | Static concrete Timeline/ForceSync adapter registration, closed-context constructor thunks, wrapper interfaces/getters/formatter forwarding, and the Buff root's exact source-list registration | library validation only; actual provider selection, nullable conversion, positive list and root admission remain separate |
| `memorypack.buff_timeline_reference`, `memorypack.reference_nullable_sources`, `memorypack.reference_conversion_sources` | Class-owned reference ABI, complete buffered FF branch, and selected conditional non-null helper conversion: saved Reader/wrap slots, typed RGCTX/interface joins, concrete formatter/getter fallbacks and original output through return | library validation only; original nullable child composition, positive list/root admission and runtime provider/context selection remain separate |
| `memorypack.buff_timeline_instance`, `memorypack.reference_instance_sources` | Selected positive parent creation branch, owned provider/Activator contexts, same saved Reader and created-wrapper local through child dispatch, original typed conversion and complete zero/nonzero output returns | library validation only; class/metadata parity, full creation/cache/provider effects and original nullable child/cursor composition remain open; no positive list/root admission |
| `memorypack.buff_timeline_source_wrappers`, `memorypack.buffered_reference_wrappers` | Complete buffered source FF clear/cursor/return paths and concrete constructor original-type allocation-return stores into owned instance fields; separate complete disabled-barrier helper | library validation only; allocation and actual constructor invocation, active barrier/refill behavior and original nullable child/list/root composition remain separate |
| `memorypack.buff_timeline_read_value`, `memorypack.read_value_reference_sources` | Actual child helper's owned Reader/provider/formatter contexts, initialized local output and full return; first optimized dispatcher case with complete FF and positive wrapper creation/dispatch/clear/conversion paths; required Sequence concrete composition and physical formatter-provider typed return | library validation only; separately registered Object entry differs; provider effects and original child cursor composition remain open; no child grammar/list/root admission |
| `memorypack.buff_sequence_composition` | Concrete Sequence original/adapter/wrapper registration, same closed constructor thunk/shared entry, typed getter/interface/formatter/source forwarding and complete nested formatter/getter fallbacks | library validation only; initialization, provider selection, allocation/constructor effects and original child cursor/list/root composition remain separate |
| `memorypack.buff_formatter_provider`, `memorypack.formatter_provider_sources` | Actual physical formatter helper's same-MethodInfo key/expected-class transfer, selected candidate/result/class check and identical full-width return through the complete epilogue | library validation only; initialized cache and normal typed returns remain conditions; indirect global, cache-miss and allocation effects, runtime selection and child/list/root admission remain open |
| `memorypack.buff_timeline_source_returns` | Exact positive Timeline/ForceSync field programs continued through complete return, caller-stack/nonvolatile restoration and no further calls or object/Reader writes | library validation only; disabled final Timeline barrier and prior source conditions remain required; original nullable child cursor and list/root composition remain separate |
| `memorypack.buff_sequence_array_source`, `memorypack.array_reference_sources` | Owned inline ReadArray overload/element contexts and complete selected Sequence FF, null/empty array and single/repeated reference-element programs; same Reader, direct cursor equation, normalized flags and full return | library validation only; helper/child typed normal returns, compatible contexts and disabled barriers are conditions; Empty/allocation effects and child cursor/list/root composition remain open |
| `memorypack.buff_timeline_root_list`, `memorypack.packable_reference_sources`, `memorypack.new_list_reference_sources` | Root's owned ReadPackable context, actual same-Reader/output/return helper and local field store; complete null/new-list callers and owned capacity-constructor return paths joined to the existing loop | library validation only; fresh count/capacity, typed normal returns and compatible contexts remain conditions; allocation/global effects, original child cursor and full root composition remain open |
| `memorypack.buff_timeline_cursor_composition` | Selected nullable ReadValue/concrete forwarding/source-return joins, direct Timeline/Sequence/ForceSync cursor equations and a bounded audit of existing certified original storage spans | library diagnostics only; stable Reader aliases, callback native advances, string-helper/global effects and list/root admission remain separate; passing source receipts are reused |
| `memorypack.buff_action_union_header`, `memorypack.union_header_sources` | Owned original/base-wrapper eager binding, concrete union formatter registration and actual caller/helper join; complete buffered short, extended UInt16 and high-marker false returns | library diagnostics only; runtime callback/class selection and positive union/child composition remain open; reserved markers gain no canonical admission and no child/list/root is admitted |
| `memorypack.buff_action_array_callback_binding`, `il2cpp.formatter_callback_signatures` | Current sealed adapter declaration, reciprocal original generic parent and instance virtual void/byref ABI joined to the independently owned array Reader/receiver/indexed output transfer | library validation only; abstract base slot representation is structural; actual provider state, inflated vtable/MethodInfo selection, callback cursor and child/list/root admission remain open |
| `memorypack.buff_formatter_registration_state`, `il2cpp.formatter_registration_state` | Complete RegisterWrap/public Type lookup callers, exact closed dictionary setter/lookup usages and selected named lookup-hit output return joined to the original eager call and actual array result helper | library validation only; static address equality retains stable initialized storage conditions; dictionary mutation/retrieval, inlined result-helper control, cache/class/vtable state, callback cursor and list/root admission remain open |
| `memorypack.buff_formatter_dictionary_lookup`, `il2cpp.{dictionary_lookup_control,signed_division}` | Actual named lookup caller bytes and full owned grammar; sign-cleared dword division/remainder index, unsigned guard, original-word node comparison and conditional full hit/miss outputs through restored returns | library validation only; anonymous storage, finite stable chain, normal compatible helper returns and disabled hit barrier remain conditions; hash/equality helper meaning, setter/live state, active effects, callback cursor and list/root admission remain open |
| `memorypack.buff_formatter_comparer_dispatch`, `il2cpp.{comparer_dispatch_control,integer_widths}` | Actual lookup selectors and arguments joined to complete word/predicate dispatch; UInt16 scan, signed offset/selector arithmetic, paired function/context load, indirect forwarding and specialized returns | library validation only; stable compatible storage and normal opaque helper returns remain conditions; named runtime interface/slot/MethodInfo, actual target/hash/equality meaning, cache/callback state and root admission remain open |
| `memorypack.buff_formatter_dispatch_fallback`, `il2cpp.{dispatch_fallback_control,integer_source_operands}` | Actual prepare-entry load/tail transfer and complete stored-byte guards; resolver receiver/context/UInt16 forwarding, first/alternate result returns and restored frames | library validation only; selected native/source gates fail closed; opaque child effects/search, deeper code/table boundaries, runtime class/interface/MethodInfo, cache/callback and root admission remain open |
| `memorypack.buff_action_reference`, `memorypack.reference_instance_sources`, `memorypack.union_false_sources` | Explicit abstract-zero wrapper local through both complete adapter output returns; full union false/output/return path and actual jump to the independently proved disabled shared barrier | library diagnostics only; runtime attributes/context/provider selection, positive union/child cursors and active/global effects remain conditional or unresolved; no reserved-marker/child/list/root admission |
| `memorypack.buff_pick_target_union_route`, `memorypack.union_route_sources` | Current indexed PickTarget union selection, complete null-cast/new-child/output/return and closed context thunk to the proved shared ReadPackable body | library diagnostics only; concrete source/child cursors, reused-wrapper paths and actual array/provider selection remain open; no child/list/root admission and no old bundle ordinals are reused |
| `memorypack.buff_effect_line_center_action`, `memorypack.buff_effect_vector_child_receipt` | Derived EffectLineCenter source/setter and FF return proofs; bounded nineteen-member action with five typed targets and an independent EffectActionCfg value entry point | recursive children through `buff_corpus`; original spans, current native child joins and the complete corpus gate are required; positive terrain-effect arrays, enclosing positive lists and gameplay execution remain open |
| `buff_effect_line_center_consumer_native`, `il2cpp.{vector_arithmetic,conditional_moves,program_grammar}` | Selected closed Data slot and fieldless receiver; complete caller with conditional target substitution, aggregate center-minus-source forwarding, runtime centerOffset write and ordinary OnCreate reference-cache assignment | independent selected native validation; getter primary-return and caller IFix selections remain conditional; later cached-reference identity, parent execution consumption and observed effects remain open |
| `buff_effect_line_center_trail_native`, `il2cpp.sse_lanes` | Current EffectInstance configuration offset forwarding; static typed query/enumerator contexts and complete trail Start/exact-zero guards; complete register lane instructions preserve original boundaries | independent selected native validation; generic runtime/provider results, parent configuration join, point deformation, renderer submission and observed execution remain open |
| `buff_effect_line_center_points_native`, `il2cpp.vector3_value_leaves` | Complete trail offset caller, ordered Single arithmetic and signed counter widths; complete typed vector leaves, Transform aggregate wrappers, closed list contexts and twelve-byte setter writeback | independent selected native validation; compiled list slots do not use open generic offsets; initial population/aliasing, Unity coordinate semantics, parent configuration identity, renderer submission and observed execution remain open |
| `buff_effect_line_center_population_native`, `il2cpp.integer_registers` | Complete source-point transfer, constructor reference stores, physical append/growth programs and five-parameter Array.Copy forwarding; checked dword addition preserves original spans | independent selected native validation; whole no-resize copying has explicit source/storage/capacity conditions; resize old-value preservation, allocation/reference lifetime, renderer submission and actual execution remain open |
| `buff_effect_line_center_copy_arguments_native`, `il2cpp.integer_addressing` | Selected same-element Array.Copy argument/return chain, qword byte-address arithmetic and optional static-bitset update; checked REX.X addressing and arithmetic retain original spans | independent selected native validation; full bulk bytes are authenticated but variable-length/CPU/overlap copy effects, live stride and resize preservation remain open |
| `buff_effect_line_center_copy_rep_native`, `il2cpp.rep_string_moves` | Complete selected size/overlap/mode/option blocks join actual default-address REP MOVSB leaf, saved-register restoration and destination return to the existing argument proof | independent selected native validation; byte copying and old-point preservation retain DF, valid/stable memory, runtime stride/selection and bitset conditions; larger/vector/backward closure and general resize preservation require separate proofs |
| `il2cpp.memory_moves` | Exact selected GP/SSE/VEX memory transfer widths, independent register/base/index extensions, alignment and upper-register facts; complete original multi-prefix padding spans | library decoder only; selected branch/table bounds, byte coverage, overlap safety, valid memory/CPU support and complete copy effects require a separate consumer proof |
| `buff_effect_line_center_copy_small_native`, `il2cpp.byte_copy_programs` | Current small/snapshot/bounded vector table bounds and complete target/return joins; distinct symbolic source-byte identities prove every finite selected length, payload bounds and forward-safe overlap | independent selected native validation; ordinary growth fits both bounded mode branches, but live stride/providers, larger/non-temporal/backward paths, allocation/alias lifetime and general resize preservation remain open |
| `buff_effect_line_center_copy_loops_native`, `il2cpp.aligned_copy_loops` | Complete alignment, padding, temporal vector loops and unsigned count guards join actual shared tails; chunk byte identities, arbitrary-count induction and affine remainder proofs preserve original head/endpoint bytes | independent selected native validation; temporal branch, valid memory, forward-safe overlap and parent stride/return/frame/bitset conditions remain explicit; non-temporal/backward copying, allocation/alias lifetime and general resize preservation remain open |
| `buff_effect_line_center_copy_non_temporal_native`, `il2cpp.non_temporal_copy` | Actual non-temporal threshold entry, complete counter loop, raw tail table and all reachable original payloads through SFENCE/cleanup/RET; aligned store-value projections preserve byte coverage without projecting ordering | independent selected native validation; SFENCE orders preceding stores before following stores; return-time visibility, later load consumption, parent publication-store join, backward copying and general resize preservation remain open |
| `buff_effect_line_center_copy_publication_native`, `il2cpp.scalar_memory_moves` | Revalidate store/fence and population chains on one selected image; actual post-copy qword items publication, matched return frame and complete eight-plus-four-byte indexed getter transfer | independent selected native validation; old-point reads retain actual publication visibility/observation, stable compatible references, live stride and parent memory/frame/selection conditions; general resize preservation and observed effects remain open |
| `buff_effect_line_center_copy_backward_native`, `il2cpp.backward_copy_instructions`, `il2cpp.backward_copy_programs` | Actual overlap edge joins complete original backward program; alignment caches, descending arbitrary-count chunk induction, repeat/exit delayed-vector writes and all tail remainders preserve distinct source bytes | independent selected native validation; supported vector state, valid stable non-wrapping memory and parent return/frame/bitset conditions remain explicit; complete branch combination, live stride/reference/allocation joins and general resize preservation remain open |
| `buff_effect_line_center_copy_dispatch_native`, `il2cpp.copy_dispatch_domains` | Revalidate all original copy programs on one image; actual branch/fallthrough joins and exact disjoint integer partitions cover every unsigned count, mode, option bit and masked alignment residue | independent selected native validation; complete conditional store values retain supported CPU/memory and parent selections, DF only on REP, and non-temporal visibility conditions; live stride, publication/read observation, allocation/reference lifetime, general resize and runtime effects remain open |
| `memorypack.buff_timeline_list`, `memorypack.list_reference_sources`, `memorypack.list_context_helpers` | Selected buffered existing-reference-list count/cursor/child/append loop and owned contexts; actual called helper index reset/version increment and positive span-call arguments | library validation only; span/provider effects, child wire widths, source/root composition and positive list/root admission remain separate |
| `memorypack.buff_camera_control_state_action` | Named camera-control parent fields with independently typed AnimationCurve children and the shared nullable List<string> context/read target | shared event-map children through `buff_corpus`; byte-payload string interpretation remains conditional, and camera state, lifetime and action effects remain unresolved |
| `buff_blow_off_consumer_flow_native`, `il2cpp.call_result_discard` | independently gated selected Boolean-call discard before a local loop back edge | no WebUI publication; accepted blow-off effects and overall action result remain separate |
| `buff_cast_skill_consumer_flow_native`, `il2cpp.call_completion_return` | independently gated void-call completion, constant AL assignment and complete matching entry/return frame | no WebUI publication; the selected caller true value does not prove skill acceptance or effects |
| `memorypack.buff_weapon_visual_action` | Named CharWeaponVisibleAction and separate WeaponVFXOverrideConfig; raw flags/index and independently owned nullable string byte payloads retain their original spans | shared event-map children through `buff_corpus`; visibility/VFX receiver and rendering effects remain unresolved |
| `memorypack.buff_selector_random_point_finder`, `memorypack.buff_recover_poise_action` | Named RandomPointFinder with independent BlackboardVector2/scalar/Vector3 children, and RecoverPoiseAction with shared effect/calculation/target children; selected native routes and original spans gate composition | shared event-map and selector children through `buff_corpus`; whole-root and canonical replay gates apply, evaluated positions/recovery and effects remain unresolved |
| `memorypack.buff_check_distance_condition`, `memorypack.buff_selector_shape_finder`, `memorypack.buff_collider_shape` | CheckDistance composes two separate TargetSettings; ShapeFinder composes its distinct sixteen-member ColliderShapeData with three fully proved raw Vector3 transfers | shared event-map and selector children through `buff_corpus`; original spans and selected native proofs are required, evaluated distances, colliders and target results remain unresolved |
| `memorypack.buff_damage_processor_collection` | DamageUnit-owned signed nullable processor lists compose independently gated scalar, scale, text, attribute-modifier and calculation children | used by `buff_damage_action` through `buff_corpus`; conditional shared-reference list grammar, original child spans and complete following fields are required; evaluated arithmetic and mutations remain unresolved |
| `memorypack.buff_effect_action_data`, `memorypack.struct_output_sources` | Concrete eighteen-member EffectActionData source/destination proof includes an explicit buffered Int32 enum program, inherited typed owner, complete cursor accounting and full-width store | library validation through the reviewed concrete record contract; collection/provider dispatch, object header/null parity and complete original child composition remain separate gates |
| `buff_action_consumers_native`, `il2cpp.compiled_paths`, `il2cpp.owned_byte_returns` | Build-independent consumer/initialization claims, bounded original local branch paths, receiver-proved closed-data reads, byte argument/store/return flow and typed enum returns through checked guard/epilogue paths; `--gameassembly`, `--metadata`, `--output` select inputs and report; failed claims empty their group and native drift empties all groups | report under `reports/`, `scratch/` or `tmp/`; compiled paths do not prove branch feasibility, runtime selection or format-coverage admission |
| `buff_tick_interval_consumer_native` | Build-independent named TickInterval return-policy claims; `--gameassembly`, `--metadata`, `--output` select inputs and report; native drift and failed claims empty all rows | report under `reports/`, `scratch/` or `tmp/`; the conditional getter policy grants no scheduling, Data ownership, execution result or stored-root admission |
| `memorypack.buff_compare_float_blackboard_children`, `memorypack.buff_damage_check_entity_num_target_children` | Library composition of independently gated parent typed calls and bounded child readers on exact source spans; the selected sword's operands and null/empty target children remain diagnostic-only | caller-owned diagnostics under `reports/` or `tmp/`; no whole-condition or Buff root promotion |
| `memorypack.buff_damage_sword_condition_receipt` | Explicit `--gameassembly`, `--metadata`, `--audit-report`, raw `--source-file` and `--output`: compose independently gated actions, nested IfElse children and sequence envelopes on the reviewed selected source | diagnostic under `reports/`; exact stored condition only; its owning modifier/root composition supplies canonical admission, with no runtime result |
| `memorypack.buff_damage_sword_selected` | Explicit `--gameassembly`, `--metadata`, `--audit-report`, raw `--source-file`, authenticated `--outer-row` and `--output`: compose the recursive sword condition, processor and enum under typed parent joins; the sole root reader owns its thirty-field continuation | selected child diagnostic under `reports/`; canonical admission belongs to `buff_selected_roots` and the complete Buff gate |
| `memorypack.{derived_schema,derived_plans,derived_actions,derived_values,union_subtypes,action_dispatcher,wrapper_members}` | build-derived read plans, dispatch and wrapper member orders (`derived_plans --corpus` is the adoption gate) | `reports/game_data/memorypack_*.json` |
| `memorypack.{target_settings,effect_config,damage_unit}_corpus` | selected enum labels over exact SkillData/BuffData records | `reports/game_data/memorypack_*.json` |
| `memorypack.*_native` (multiply_attribute, atk_scale, definite_value, breaking_attack, damage_action_route, damage_action_poise_route, poise_result, buff_1b_action), `scripts.webui.gameplay.route_audit` | selected unpatched formula and route bodies; exact character damage-route partition | `reports/game_data/` |
| `il2cpp.context_audit`, `native_union_atlas` | generic-instantiation contexts; every reviewed JsonData union contract | `il2cpp_context_current_latest.*`, `jsondata_union_atlas_current.json` |
| `levelscript_*_native` | one LevelScript route each (below) | stdout or `reports/game_data/` |

### LevelScript validators

Each `levelscript_<route>_native` module authenticates one selected native
LevelScript route -- the generated union reader (including fragmented
readers), ordered reads and setters, typed parameter contexts, enum backings
and nested list element types -- then optionally replays current source
spans. It proves stored bytes only, never live dispatch or execution; the
sequential reader admits a route only while its check validates. Tags are
per-build and live in the contracts, so routes are named by type.

After one route changes, `python -m scripts.game_data.levelscript_targeted_replay --contract scripts/game_data/contracts/<route>_native.json --expected-files N --output reports/game_data/<route>_targeted_replay.json` reads only that contract's hash-checked source files and reports their next first stop. It also accepts a single GameCondition route with receipts nested under `route`. Its scoped projection does not replace a whole JsonData corpus gate.

| Kind | Modules (`levelscript_*_native`) |
| --- | --- |
| Shared camera fields | `camera_look_at` (camera layouts and the typed `CameraBlendCurveKey` reader; `--game-root`, stdout native audit) |
| ActionBase actions | `add_buffs_to_target_selves`, `add_tracking_point`, `tracking_point`, `remove_tracking_point`, `archery_stage`, `typhoea_chip_id`, `audio_cue`, `block_auto_music_change_cancel`, `block_battle_music`, `bool_compare`, `building_pos_hint_show`, `building_pos_hint_hide`, `cutscene_teleport`, `enemy_patrol_start`, `entities_visibility`, `environment_enable`, `event_args_float`, `fac_build_effect`, `fac_change_building`, `fac_get_building_position`, `fac_guide_hint_enable`, `fac_set_interact_locked_state`, `fac_top_view_range`, `finish_buffs`, `finish_scene_effect`, `is_look_at_point_in_screen`, `list_add_value_entity_ptr`, `manually_stop_guide`, `mark_task_condition_failed`, `npc_effect`, `npc_stop_cur_montage`, `npc_proxy_effect`, `npc_proxy_patrol_stop`, `override_npc_dialog`, `play_voice_narrative`, `post_audio_status`, `stop_radio`, `require_settlement_show`, `settlement_followon`, `settlement_upgrade_show`, `reset_follow_camera`, `resume_spawner`, `scripted_char_teleport_to`, `scripted_char_patrol_start`, `stop_char_scripted_mode`, `send_lua_event1`, `set_enemy_ui_show_range`, `set_fac_mode`, `set_forbid_map_teleport`, `set_list_buff`, `show_chapter_completed_panel`, `show_chapter_panel_direct`, `show_finish_toast`, `show_start_toast`, `start_seq_loop`, `start_subgame_countdown`, `stop_subgame_countdown_by_handle`, `start_track_camera`, `exit_camera`, `switch_to_camera`, `track_camera`, `toggle_clear_screen_but_radio_v2`, `toggle_main_hud_ignore`, `set_squad_special_idle_enable`, `set_squad_enable_relax_idle`, `character_play_montage`, `set_decoration_animator_int`, `set_decoration_view_state`, `entity_move_to_with_speed`, `move_bamboo_last`, `set_bamboo_pos_index`, `start_fmv_and_teleport`, `start_narrative_black_screen_teleport`, `disable_hud_fade`, `start_cutscene_hide_scene_object`, `start_cutscene_control_scene_object`, `stop_effect_on_npc_proxy`, `set_main_char_hp_bar_active`, `destroy_ability_entity`, `teleport_gameplay_npc`, `apply_movement_setting_modifier`, `toggle_ui_dev_only`, `set_squad_icon_active`, `skip_entity_die_display`, `water_height` |
| ActionHeader events | `header` (snapshot enter/leave), `entity_hp_changed`, `entity_scanned`, `squad_fight_header`, `squad_all_die_header`, `mission_changed_header`, `leader_enter_trigger_volume`, `on_leader_enter_trigger_volume_list`, `on_spawner_entity_spawn`, `on_spawner_group_begin`, `on_spawner_group_complete`, `on_spawner_start`, `on_spawner_wave_begin`, `on_spawner_pause`, `on_spawner_entity_die`, `on_entity_die`, `on_encounter_intro_part_end`, `on_npc_dirty_block_cleaned`, `on_server_dialog_exit`, `on_level_reset`, `on_specific_entity_die`, `on_specific_entity_list_die`, `on_script_pre_start`, `on_client_global_var_changed`, `on_sub_game_start`, `on_npc_patrol_checkpoint_reach`, `on_physical_no_guard`, `on_physical_infliction`, `on_any_entity_die`, `on_any_enemy_poise_zero`, `on_any_enemy_poise_knot_break`, `on_aether_lock_endpoint_scanned`, `on_blight_miasma_weak_guide`, `on_cutscene_exit`, `on_bb_variable_changed`, `on_start_script_controlled_char_mode`, `on_encounter_activated`, `on_encounter_battle_part_begin`, `on_encounter_battle_part_end`, `on_entity_cast_skill`, `on_spell_abnormal_start`, `settlement_ready_performance`, `archery_advanced_headers`, `on_train_level_event`, `on_enemy_take_last_attack_damage`, `on_spell_infliction`, `on_map_var_changed` (OnMapVarChanged), `on_enemy_in_fight` (OnEnemyInFight) |
| PureGetter getters | `getter_int`, `getter_compare`, `getter_entity_ptr`, `getter_levelscript_ptr`, `getter_list_buff`, `get_cur_squad_all_dead`, `get_character_template_id`, `float_getter_int_to_float`, `float_getter_plus`, `get_interactive_property_int`, `get_mission_save_property_int`, `bool_getter_mult_or`, `npc_get_pack_anim_has_clean`, `get_script_task_objective_is_completed`, `is_endmin_gender`, `entity_to_string`, `get_mission_state`, `get_is_leader_in_trigger_volume`, `check_performance_ready`, `list_make_entity_ptr` |
| GameCondition (`taskMap`) | `taskmap_condition`, `taskmap_followon`, `taskmap_submit`, `taskmap_archery`, `check_game_inst_start_duration`, `check_fac_linking_mode`, `encounter_opera_segments`; `task_condition` is a loader |
| Claims and aggregates | `audio_cue_execute` (build-independent `SetAudioCueVar.Execute` body claims; `--game-root`, `--output`), `route_deserialize` (`--report`), `two_routes` and `param_list` (loaders) |

Most take `--game-root` and the three source-replay flags. `entity_scanned`
and `track_camera` take no `--summary`. `header`, `getter_*`,
`get_mission_state`, `finish_scene_effect`, `npc_proxy_patrol_stop`,
`post_audio_status`, `set_fac_mode`, `start_seq_loop` and `water_height` take
no options: they print their native audit (some replay default paths) and
their `validate_*` function accepts explicit paths.

`levelscript_union_layouts` derives every union layout from `tools/DummyDll`
(through `dummydll_metadata`, the stdlib ECMA-335 reader), gates on
`tools\DummyDll\generation.json`, rechecks every reviewed row of
`codecs/levelscript/action_map_layouts.json`, and writes nothing on
disagreement (`--allow-build-drift` skips only the native gate). Derived rows
are `direct`, not the reviewed `exact`; keep the reviewed-tier coverage report
beside the declared-tier one:

```bat
python -m scripts.game_data.levelscript_union_layouts --report reports\game_data\levelscript_union_layouts.json
python -m scripts.game_data.jsondata_schema_coverage --report reports\game_data\jsondata_schema_coverage.json
python -m scripts.game_data.jsondata_schema_coverage --declarations reports\game_data\levelscript_union_layouts.json --report reports\game_data\jsondata_schema_coverage_declared.json
```

### Naming the exported MonoBehaviour corpus

The export does not carry MonoBehaviour class names: `m_Script` points into a
MonoScript CAB outside the export scope. Every `m_Script` resolves to one
container through the dependency-slot rule in `scripts/game_data/cabmap.py`
(also the most depended-on container in the CABMap). Take its chunk path and
offset from the CABMap at the time of use, because its chunk filename differs
per VFS root; `--filter_data` takes a JSON array of
`{"Source": "<chunk>", "Offset": N}`. The census and field sweep cover the
whole corpus, so give them a generous timeout.

```bat
python -m scripts.game_data.monobehaviour.census --report reports\assets\monobehaviour_script_census.json
python -m scripts.webui.assets.cabmap
%ASCLI% "<chunk from the CABMap>" tmp\game_data\monoscript --game ArknightsEndfield --filter_data tmp\game_data\monoscript\filter.json --types "MonoScript:Both" --export_type Dump
python -m scripts.game_data.monobehaviour.monoscript_catalog --dump-root tmp\game_data\monoscript\MonoScript --report reports\assets\monoscript_catalog.json
python -m scripts.game_data.monobehaviour.script_names reports\assets\monobehaviour_script_census.json --monoscript-dump tmp\game_data\monoscript\MonoScript --report reports\assets\monobehaviour_script_names.json
python -m scripts.game_data.monobehaviour.field_semantics --names-report reports\assets\monobehaviour_script_names.json --progress 100000 --report reports\assets\monobehaviour_field_semantics.json
python -m scripts.game_data.monobehaviour.table_keys --report reports\assets\monobehaviour_table_keys.json
```

`--top N` works `field_semantics` down by class size (`--limit N` is only a
probe). The modules own the grading rules; `memory/game_data/unity_assets.md`
owns why both naming routes exist.

### Migrating a contract that pins a superseded build

`il2cpp/method_resolver.py` re-resolves recorded managed identities on the
selected build without pinning anything. Contracts whose claims can be
re-proved carry a regenerator that re-derives rows by name, re-checks every
claim and refuses to write when one no longer holds. Census contracts
(`identity_carrier_boundaries.json`, `cross_system_consumers.json`) have none
and stay `mismatched` until reviewed again. `PATCH` is
`Gameplay.Beyond.patch.bytes` from a bounded `AnimeStudio.CLI dump -b i-fix-patch`
into `tmp/`.

```bat
python -m scripts.game_data.il2cpp.method_resolver --type "Ns.Type" --method "Method"
python -m scripts.game_data.il2cpp.method_resolver --from-contract path\to\contract.json --report reports\assets\character_recovery\<name>.json
python -m scripts.game_data.callserver_callback_native --regenerate [--write]
python -m scripts.game_data.cutscene_case_resolution_native --regenerate [--write]
python -m scripts.game_data.ifix_patch_native --regenerate PATCH [--write]
python -m scripts.webui.story_recovery.audit_native_carriers cinematic --write-contract
python -m scripts.webui.story_recovery.audit_native_carriers generic --carrier-type Beyond.Gameplay.TeleportParam --focus-field missionId --focus-field levelScriptId --focus-field actionId --focus-field performId --write-contract
python -m scripts.game_data.ifix_vm_operands_native --gameassembly GA --metadata META --input PATCH [--outer-summary OUTER --outer-ledger LEDGER --expected-input-set-sha256 SHA] --output reports/animestudio/ifix_vm_operands_current.json
```

## Output hygiene

- Generated reports go in topic directories under `reports/`, revisitable
  experiments in `scratch/<topic>/<task>/`, disposable intermediates in
  `tmp/<topic>/<run>/` (removed after validation). Reusable conclusions go to
  a `memory/` owner.
- Track a file only if it is reusable and general enough to explain the data:
  a corpus gate, native validator, audit tool or data-structure contract is
  tracked; the reports, ledgers and receipts they write are not. Keep
  declarations in a contract the module loads, not pinned inside a module.
- Tests live in `scripts/tests/` (untracked, kept in place) and run by explicit
  module path, e.g. `python -m unittest scripts.tests.test_build_assets`;
  `unittest discover` does not reach that directory.
