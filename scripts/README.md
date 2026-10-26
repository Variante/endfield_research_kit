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

`game_data/endminf_particle_matrix_native.py` is the selected-build loader for
the reviewed particle getter/matrix code families and raw-backed constants;
`game_data/endminf_particle_quad_native.py` extends that selected-build gate to
complete size/getter families and bounded quad stages. The Lab's offline
numeric consumer owns its report and does not publish WebUI
data through this package.

| Line | Path | Responsibility |
| --- | --- | --- |
| **1. Game data** | `game_data/extraction/` | installed client to `export_full/`: the export and changed-file exporters, `scope.py` (the structured-block and Unity-class vocabulary an export selects), the freshness guard with its per-output provenance, export benchmark, AnimeStudio object index, and `animestudio/` maintenance commands; never publishes page data |
| | `game_data/` | the exact framing readers, one per payload family (`irradiance_volume.py`, `extend_data_binary.py`, `bundle_manifest.py`, `ifix_patch.py`, `inverted_lz4.py`, `dynamic_streaming.py`, the serialized-gameplay `*_binary.py` readers, and the MemoryPack JsonData readers such as `levelconfig_binary.py`, `navmesh_binary.py`, `gpu_ui_binary.py`, with `string_pool.py` resolving the `Json/StringPool` indices pooled JsonData stores); the `*_corpus.py` current-corpus gates and `jsondata_schema_coverage.py`; the `*_native.py` loaders and validators for the reviewed native facts the Story, Mission Pipeline, Map and recovery tools consume, including `story_native_consumers_native.py` (Story's claim groups, cached in `reports/story/recovery/`) and `buff_ai_consumers_native.py` (assembly-owned AI caller/getter claims, explicit native hashes, writes `reports/game_data/`); `native_union_atlas.py` (re-validates every union contract); `dummydll_metadata.py`, `levelscript_union_layouts.py`, `levelscript_union_tags.py` (current `(tag, member count)` per type name, so codecs name a type instead of a tag literal) and `pure_getter_rows.py` (per-build PureGetter row fields for `--regenerate`); `dependency_snapshot.py`; `media_resolver.py` (game-media naming), `sprite_crops.py` (Sprite crop documents), `cabmap.py` (the CABMap container index and the `m_FileID` -> dependency-slot rule) and `wwise_sdk_symbols.py` (names shipped `AkSoundEngine.dll` functions from the installed Wwise SDK libraries) |
| | `game_data/codecs/` | all per-record LevelScript and LevelData byte decoding behind the `*_binary.py` readers, which keep only the file-level framing walk, the record dispatcher and the result assembly; `codecs/levelscript/modules.py` is the sequential `modules` dictionary codec, and `send_lua_event.py` the one nested value the derived declaration cannot describe |
| | `game_data/contracts/` | the reviewed contract JSON that every reader, loader and validator loads; `CONTRACTS_DIR` from the package is the only path anchor; git, not a pinned digest, owns each file's integrity |
| | `game_data/streaming/` | the block-15 Streaming lane: `framing.py`, `pairs.py`, the marker parsers, their `*_native.py` validators and `*_corpus.py` gates |
| | `game_data/terrain/` | the TRET container reader (`tret.py`), Map's `_H` texture-byte diagnostic (`height.py`), the native consumer and layer-path validators, and the corpus gate |
| | `game_data/il2cpp/` | `protocol.py` (metadata and PE primitives), `native_image.py` (the one opened installed build every contract validator checks against), `context.py` (generic-instantiation pointer tables), `method_resolver.py` (managed name to selected-build body), `call_graph.py` (a body's named calls, literals and field reads), `body_claims.py` (the claim kinds a claims contract states, evaluated on whichever build is installed), `instance_string_field_calls.py` (typed instance fields and guarded String call arguments), `ai_blackboard_selection.py` (closed Data/receiver flow, enum selection, null fallback and exact return leaves), `guarded_reference_getter.py` (complete false-guard/false-init typed reference return), `generic_lookup_forwarding.py` (registered generic arguments and conditional opaque-reference tail returns), `flag_guarded_reference_leaf.py` (authenticated raw byte-mask return/tail control and complete owned primary/cold conditional return), and the context audit split by section: `context_audit.py` (CLI and report), `context_audit_common.py` (build gate, audit pins and `consumer_window` through `contracts/il2cpp_context_audit_native.json`), `context_audit_memorypack.py`, `context_audit_skilldata.py`, `context_audit_vfs.py` |
| | `game_data/monobehaviour/` | the exported MonoBehaviour corpus: `census.py`, `monoscript_catalog.py`, `script_names.py`, `field_semantics.py` and `table_keys.py` |
| | `game_data/schemas/` | the reviewed named JSON schema readers for the textual JsonData families (`gameplay_config*.py`, `text_schema.py`, `mission_runtime_{main,meta}.py`, `npc_catalog.py`, `npc_prefab_info.py`, `map_config.py`, `ui_level_map_load_config.py`, `level_mount_point.py`, `gold_coin_config.py`), all validated by `named_schema.py` |
| | `game_data/memorypack/` | MemoryPack codecs and their corpus gates (`core.LabelledReader`, the BuffData and SkillData readers, gated through `il2cpp.native_image`); `buff_skill_lifetime_weakness_actions.py` owns recursive ChangeSkill, SaveBuffLifeTime and SetWeakness stored values, `buff_ai_marker_blackboard_actions.py` owns AI marker/blackboard stored values, and `buff_pick_target_action.py` owns the independent BlackboardInt child; `animation_curve.py` supplies explicit curve profiles and `source_bound_stored_tree.py` binds headered and headerless named records. The build-derived schema line includes `wrapper_members.py` (every `*ForMemoryPack` member order and type), `action_dispatcher.py` (the whole AbilityActionData dispatcher), `union_dispatch.py` (a union's tag table from its native formatter), `union_subtypes.py` (nested-union tags), `derived_schema.py` (recursive read plans), `derived_actions.py` (the flat-body subset), `derived_plans.py` (executes a plan; `--corpus` is its adoption gate), `derived_values.py` (named values checked against filenames, through the export StringPool) and `wrapper_body_audit.py` (`--family F`: each reached wrapper's native header count and member write order) |
| **2. WebUI** | `webui/export.py`, `webui/pages.py`, `webui/build_graph.py` | the `export.bat` entry point; the page registry, in which every build task declares what it reads from the export; the dependency-graph scheduler and timing report |
| | `webui/package.py` | packaging |
| | `webui/story/` | Story and Text page data plus shared Story evidence |
| | `webui/story_recovery/` | Story audits, OCR ordering, runtime traces, candidate generation, and `refresh_audio_hook_catalog.py` (re-pins the audio capture hook catalog to the installed build) |
| | `webui/mission_pipeline/` | standalone Mission Pipeline recovery (not a WebUI page); `runtime_contract_native.py` re-derives `RUNTIME_CONTRACT` by name on the installed build and labels each native chain row |
| | `webui/{gameplay,map,characters,audio,assets,data_inspector,updates}/` | page and catalog builders with their helper modules |
| | `webui/gameplay/items/` | Gameplay Items, buildings and recipes; `gameplay/gameplay_refs.py` and `gameplay/factory_models.py` own Gameplay-to-Assets joins, retaining the existing `data/assets/gameplay_refs.json` output |
| | `webui/audio/semantics/` | Audio's reusable evidence owners (see *Audio decode, indexing and semantics*), including `conversation_sidecar.py` (the per-conversation Story sidecars the Story page merges), `decoded_payload_event_names.py` and `runtime_capture_import.py` (validates one bounded saved audio session) |
| | `webui/recovery/` | the debug-only Recovery page: `build_recovery.py` plus `recovery_declarations.json` (reviewed enum names, family rules, per-type entries and evidence text); reads reports, asset maps, the VFS index and `memory/game_data/README.md`'s level table; `jsondata_stages.py` authenticates the optional current registry and checks exact path-partitioned L2 declarations before publication |
| | `webui/localization.py` | shared language-specific hotfixes for semantic page text and Updates comparisons; preserves raw tables |
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

AnimeStudio's tracked branch is `endfield` in `Variante/AnimeStudio`.
Setup checks out the parent repository's pinned submodule commit. To explicitly
advance that pin to the branch tip, run
`git submodule update --remote tools/AnimeStudio`, validate and rebuild the CLI,
then commit the updated `tools/AnimeStudio` gitlink in this repository.

## Export rules

Unity dependency loads use the selected layer's CABMap plus the other layer's
map as an absent-name fallback. Same-chunk dependency offsets are retained in
filtered exports, so Animator FBXs can include meshes from both installed
layers. Rebuild AnimeStudio after exporter source changes; existing FBXs need
re-extraction to acquire previously omitted geometry.
Model conversion also loads available built-in files from the selected player's
`Resources` directory; their hashes participate in model caching and freshness.

`export.bat` hands every argument to `python -m scripts.webui.export`. The one
source of truth for what a page needs is `scripts/webui/pages.py`: each build
task declares the export inputs it `reads` (must exist and be current) or
reads when present (`optional`), the same-page tasks it `needs`
(`check_pages_independent` refuses a cross-page edge), tasks it runs `after`
when both are in one build, inputs it `uses` but another page extracts, and
outputs it `serve`s at browse time (the Decoded page). A page run extracts the
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
| `audio` | Table, JsonData; MonoBehaviour, PlayableDirector, animator-controller JSON; AnimationClip; CN audio decode | Audio, and the Story voice-line sidecars (`lang/CN/audio/conv/`) |
| `data` | everything decodable except other pages' media: Table, JsonData, Lua, whole Terrain; every Unity JSON class; AnimationClip, Shader, Font, TextAsset | the Decoded page's decoded datasets; its file viewer serves the rest |
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
- `--webui-jobs N` bounds builders and Map's workers, `--asset-jobs N`
  AnimeStudio workers; `--full-source-graph` adds exhaustive PathID work.
  Options the wrapper does not own go to `export_full_from_game` and require
  `--from-game`. Keep wrapper files CRLF. Timings and a process-tree
  benchmark go to `reports/export/`.

### Exporter scope, provenance and stores

`python -m scripts.game_data.extraction.export_full_from_game` exports exactly
one `scope.ExtractionScope`; its docstring documents the presets, staging,
publication, scheduling and managed-reference diagnostics. Decoded blocks
publish into `game/`; `scope.RAW_BLOCKS` (Streaming, DynamicStreaming, IV,
ExtendData, IFixPatch, bundle manifest) publish byte-for-byte into
`<export root>/raw/`, shown only by the Decoded page. Bundles and audio packages
are never dumped. Provenance stamps live in `meta/extraction/provenance.json`;
`verify_export_freshness` checks `--require-structured`, `--require-unity`,
`--require-asset-map` and `--accept-reused` against them.

Unity object documents live in `game/Unity.sqlite` and the `PACKED_GAME_DIRS`
folders (`Json/LipSync`) in `game/GameFiles.sqlite`; converted media stays
under `game/Unity/<Type>/`, except Animator `.fbx`, which the Convert stage
packs into `Unity.sqlite` with its large FBX property blocks (meshes, skin)
stored once in a shared `chunks` table and rejoined byte-exact on read; each
FBX is normalized as it is packed (`fbx_normalize.py`: fixed SDK timestamps
and ids) so content-identical exports share one SHA256, and
`python -m scripts.game_data.unity_store normalize-fbx` upgrades rows packed
before that;
`serve.py` answers the path and static packages ship the rejoined file. Read them only through
`scripts/game_data/unity_store.py` and `scripts/game_data/game_file_store.py`;
nothing falls back to loose files. A Sprite is a crop document over its
Texture2D (`scripts/game_data/sprite_crops.py`, rendered by
`webui/sprite_worker.js`). The Decoded page browses the stores through
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
| Extraction | `game_data/extraction/export_full_from_game.py` | `export_full/`; page scopes come from `webui/pages.py` |
| Low-level delta and snapshot helpers | `game_data/extraction/export_changed_game_data.py`, `export_sync.py` | authenticated delta state and snapshot utilities; separate from the page export workflow |
| Export freshness | `game_data/extraction/verify_export_freshness.py` | validation result |
| Cooked collision readers | `python -m scripts.game_data.cooked_collision PAYLOAD --obj tmp/collision.obj`; `python -m scripts.game_data.cooked_convex PAYLOAD --obj tmp/hull.obj` | complete supported PhysX triangle/BV4 or convex/Gauss payload checks and local collision OBJ; triangle `--prefix-only` leaves its tail explicitly opaque |
| Selected cooked collision corpus | `python -m scripts.game_data.cooked_collision_corpus --selection FILTER --outer-summary AUDIT --outer-ledger LEDGER --expected-input-set-sha256 SHA` | fresh identity-filtered Mesh JSON/raw export under `tmp/`, exact payload joins and complete-reader census under `reports/assets/`; selection and current VFS audit define coverage |
| Collision observer preparation | `python -m scripts.game_data.collision_capture_prepare --game-root GAME --plan PLAN`; `tools\EndfieldCapture\Build.ps1 -Collision` | current selected native declarations under `reports/runtime_capture/collision-current/`; PLAN binds current stored Model frames through the narrow native source contract, without importing historical prefab/cooked-mesh joins; host/runtime binaries in `tools/EndfieldCapture/out/bin/`; no game launch or attachment |
| Lua VM observer preparation | `python -m scripts.game_data.lua_capture_prepare --game-dir GAME --output reports/runtime_capture/lua_vm/lua_vm_build.h --report reports/runtime_capture/lua-vm-preparation.json`; `tools\EndfieldCapture\Build.ps1 -LuaVm` | native-input-gated resolution of the `XLua.LuaDLL.Lua` wrapper thunks, the lua-protobuf `luaL_Reg` recovered from the opener's stack-slot stores, and the LuaSocket tcp metatable, emitted as a generated header plus preparation report; never emits unvalidated addresses. `tools\EndfieldCapture\Capture.ps1 -Preset network-blueprint` arms `--network --lua-vm`; no game launch |
| Collision capture and inspection | `tools\EndfieldCapture\Capture.ps1 -Preset collision`; `python -m scripts.game_data.collision_capture_inspect --session SESSION` | bounded queries, resource/CAB and ECS ownership, getter/cache and PGS/TGS contact evidence; v16 connects public-Scene execution and native phase/collide-step/narrowphase producers to the downstream task lifecycle; adds original destruction load/request/prepare/callback/submit stages, typed counts and manager returns alongside pinned-body rechecks; parent inspection owns admission and leaves missing step/lifetime fields explicit |
| Runtime ECS collision provenance | `python -m scripts.game_data.collision_runtime_ecs --session SESSION [--export-root EXPORT] [--output REPORT]` | reuses admitted capture bytes; strictly decodes owned definitions and separately projects schema-sized unbound prefixes with opaque tails/unknown length units; joins source callbacks or original Entity setters to versioned query identities; optional current AssetBundle PPtr joins supply input paths; shape geometry and solver contacts remain separate |
| Buff paired capture preparation | `python -m scripts.game_data.mission_trace_capture_prepare --profile buff --game-dir GAME --recipe scripts/game_data/contracts/buff_runtime_paired_capture.json --output reports/runtime_capture/buff-paired-trace-build.json --report reports/runtime_capture/buff-paired-trace-preparation.json`; `tools\EndfieldCapture\Capture.ps1 -Preset buff-paired` | selected native signatures, field paths and ordinary GP argument layouts; entry/return pairs plus declared entry-only initializers; captures retain exported BuffData context. Full procedure in `tools/EndfieldCapture/README.md` |
| Buff numeric capture preparation | Same preparer with `--recipe scripts/game_data/contracts/buff_runtime_values_capture.json --output reports/runtime_capture/buff-values-trace-build.json --report reports/runtime_capture/buff-values-trace-preparation.json`; `tools\EndfieldCapture\Capture.ps1 -Preset buff-values` | composes the paired recipe; selected GP inputs with typed Float/Double XMM0 returns, authenticated scalar-byref reads, initialization inputs and healing detail snapshots. Refuses ordinary XMM input arguments; see the numeric procedure in `tools/EndfieldCapture/README.md` |
| Buff paired capture analysis | `python -m scripts.game_data.buff_runtime_paired_inspect --session SESSION --output-dir REPORT_DIR` | reuses the maintained local-file trace reader; writes recorded call pairs, Boolean outcomes, raw numeric return bits with strict-JSON finite/nonfinite interpretation, sequential snapshot differences and incomplete coverage. No legacy receipt, runtime ownership or intermediate-write/effect admission |
| Buff numeric observations | `python -m scripts.game_data.buff_runtime_values_inspect --analysis-dir PAIRED_ANALYSIS_DIR --output REPORT [--gameassembly DLL --metadata DAT]` | reuses complete recorded pairs; groups expression fields, effect/query/write enclosures, Single-rounding checks and earlier initialization identity candidates. Resolution coverage keeps pack/outer healing and same-action/receiver HP notifications distinct; bundled intervals retain ordered creation/source-reset transfers with opaque source arguments, comparator/count-condition results, helper entry inputs, HealAction stages, reached merge submissions, Int32 modifier results, named patch decisions and codec snapshots without claiming full collections, helper lookup success or server acknowledgement. v4 also retains healing snapshot getter, interest, dispatch and action-queue intervals with gated copy-site labels. Both native paths enable the Float direct/entity join; Blackboard Double callers remain unmapped |
| Buff runtime compiled callsites | `python -m scripts.game_data.buff_runtime_callsite_inspect --analysis-dir PAIRED_ANALYSIS_DIR --gameassembly DLL --metadata DAT --output REPORT` | joins recorded sequence caller RVAs to selected-native IfElse condition/branch direct callsites and explicit outer invocation pairs; named entry zero coverage does not imply absent conditional execution. No loaded-image, source-node or effect admission |
| Buff healing settlement windows | `python -m scripts.game_data.buff_healing_settlement_native --gameassembly DLL --metadata DAT --output reports/runtime_capture/healing-settlement-audit.json` | authenticates normal healing formula, cancellation/clamp/readback, refreshed attribute-copy sites and event interest/context/dispatch windows; conditional compiled interpretation only, with empty results on build or proof drift. No live capture admission or generic delegate/server acknowledgement |
| Buff runtime source candidates | `python -m scripts.game_data.buff_runtime_source_candidates --analysis-dir PAIRED_ANALYSIS_DIR --family-validation FROZEN_FAMILY_RECEIPT --output-dir REPORT_DIR` | reuses a completed frozen Buff family receipt, its consumed native dispatch contracts and byte-matched captured exports; compares event, action type/index and stored fields under explicit paired enclosures. A unique match remains a candidate; no corpus rerun, root admission or runtime file/node-selection claim |
| Runtime query geometry identity | `python -m scripts.game_data.collision_runtime_geometry --session SESSION [--stored-receipt RECEIPT ...] [--game-root GAME] [--output REPORT]` | rechecks getter/cache/CAB identity and query/source records; repeated receipt flags combine independently authenticated selections; compares complete arrays and captured prefixes separately, native face remaps and source/current-pose face metrics while retaining hit-validity and sweep conditions; writes `collected/runtime-geometry-identity.json` |
| ECS shape simulation policy | `python -m scripts.game_data.collision_ecs_shape_policy_native --game-root GAME --output REPORT` | authenticates common shape-setup branches, typed original actor/body getters and shape flag interfaces; missing/mismatched native inputs withhold configuration facts; runtime mode, final flags, pair filtering and contacts remain separate |
| Saved collision configuration | `python -m scripts.game_data.collision_runtime_configuration --session SESSION --game-root GAME [--output REPORT]` | replays admitted typed body/shape/scene fields independently of versioned ECS ownership; the selected `collision_body_mode_native` gate authenticates original compiled kinematic-bit semantics; v2 output records worker/island populations and normalized scene-address comparisons under `collected/runtime-configuration.json`; body-to-step ownership, executed pair filters and positive contacts remain separate |
| Saved scene pair-filter rules | `python -m scripts.game_data.collision_runtime_filter --session SESSION --game-root GAME [--output REPORT]` | authenticates selected shader/helper families and ABI; v3 output replays v14 original pair/dispatcher/shader/helper returns, passive policies and typed owners; summarizes executed decisions, conditional flag comparisons and missing step ancestry separately from body-window coverage; old captures retain missing operands; solver contacts remain independent in `collected/runtime-filter.json` |
| Saved PGS solver response | `python -m scripts.game_data.collision_runtime_solver_response --session SESSION --game-root GAME [--output REPORT]` | authenticates original scalar solver families, dispatch tags and response operands; reads same-call post-solve accumulated normal values from `solverConstraint` windows; excludes copied body padding/neighbor changes and preserves uncaptured ranges as gaps; source, lifetime, step and newly generated impulse remain separate in `collected/runtime-solver-response.json` |
| Solver-side geometry recovery | `python -m scripts.game_data.collision_runtime_solver_geometry --session SESSION [--game-root GAME]` | authenticates selected primitive getters, recovers same-call capsule/box dimensions, joins exact versioned actor source candidates and separates primitive response from triangle preparation; missing mesh pointers and solve routes remain gaps in `collected/runtime-solver-geometry.json` |
| Runtime dynamics step candidates | `python -m scripts.game_data.collision_runtime_dispatch --session SESSION [--game-root GAME] [--output REPORT]` | rechecks original scene/update/island observations and typed enclosing core candidates; expanded captures separately join original scene generation, zero atomic decrement, typed task run and worker update/decision to the producing step; missing phases and reused addresses do not establish causality; writes `collected/runtime-dispatch-candidates.json` |
| Compiled pair/task route | `python -m scripts.game_data.collision_pair_step_native --gameassembly DLL --metadata DAT --unityplayer DLL --output REPORT` | authenticates complete public-Scene/phase/collide-step/narrowphase/broadphase/filter families, constructors, concrete vtables, original pair callees and producer hook declarations; protected entry dispatch and old archived pair-to-step generations remain unresolved; output stays under an ignored report root |
| Compiled PGS task route | `python -m scripts.game_data.collision_solver_task_native --gameassembly DLL --metadata DAT --unityplayer DLL --output REPORT` | authenticates context-owned task vtables, original update argument handoff, complete callbacks and base continuation release; capture preparation includes these declarations, while saved-session inspection admits original scheduling generations and preserves missing public-core/source joins |
| Compiled narrowphase producer | `python -m scripts.game_data.collision_narrowphase_task_native --gameassembly DLL --metadata DAT --unityplayer DLL --output REPORT` | authenticates the named embedded task, constructor/owner/name coordinates, virtual run and tail-call to dependency wiring; reuses the broadphase contract and leaves live enqueue/generation unresolved |
| Physics-body activation claims | `python -m scripts.game_data.collision_solver_body_native --gameassembly DLL --metadata DAT --expected-gameassembly-sha256 SHA --expected-metadata-sha256 SHA [--output REPORT]` | re-proves named original destructible/kickable activation, literal Boolean call arguments and force/wake calls; selected opened bytes and post-read freshness gate fail closed; does not assert a live awake body or solver pair |
| Runtime collision observation boundary | `python -m scripts.game_data.collision_runtime_evidence_boundary --session SESSION [--game-root GAME] [--output REPORT]` | audits getter/live-cache, auxiliary and typed scene/report evidence; selected dispatch contract identifies context/population fields, while `collision_capture_dispatch.py` rechecks original update/island decisions and scene/core provenance; checkpoint populations and a passed island gate never prove solver contacts |
| Saved collision cache decoding | `python -m scripts.game_data.collision_runtime_mesh --session SESSION --raw-mesh RAW --cooked PAYLOAD` | reuses unchanged admitted session bytes, validates the selected native cache layout and compares pointer-bound vertices/indices plus auxiliary remap/edge/slab bytes against one frozen source; report defaults to `SESSION/collected/runtime-mesh-comparison.json`; optional `--obj` writes a validated source-local collision surface under an ignored output root; separately timed samples do not prove shape attachment or contacts |
| Saved Collider shape attachment | `python -m scripts.game_data.collision_runtime_shape --session SESSION --raw-mesh RAW --cooked PAYLOAD` | recomputes the source-bound cache comparison and authenticates Collider/PxShape consumers, buffered geometry and flags; reports each same-call triangle-cache join, actor/flag observations and missing later shape windows to `SESSION/collected/runtime-shape-comparison.json`; partial coverage exits nonzero and never fills fields from another epoch; no contact claim |
| Saved actor scene/contact evidence | `python -m scripts.game_data.collision_runtime_actor --session SESSION --raw-mesh RAW --cooked PAYLOAD` | recomputes source-bound shape attachment, authenticates rigid-static registration/public scene and raw completed-core scene joins; writes same-call membership and contact-storage coverage to `SESSION/collected/runtime-actor-comparison.json`; partial coverage exits nonzero, missing headers stay unavailable, and empty lazy contact-header arrays never imply contact absence |
| Character movement/query native claims | `python -m scripts.game_data.collision_movement_native --gameassembly DLL --metadata DAT --expected-gameassembly-sha256 SHA --expected-metadata-sha256 SHA` | re-proves the complete named movement, query, layer-read and gameplay-filter claim set on explicitly selected binaries; success/failure receipts under `reports/runtime_capture/collision/`; no live query, IFix branch, hit or contact claim |
| Query/result observer ABI | `python -m scripts.game_data.collision_query_native --game-root GAME` | selected argument/result layouts, native writers and requested-name/resolver/cache/caller witnesses; reports under `reports/runtime_capture/collision/`; live registration additionally requires the observer caller/cache gate |
| Packed ECS collider definitions | `python -m scripts.game_data.ecs_collision --payload BYTES --mesh-count N --game-root GAME` | authenticates the selected decoder, actor userdata consumers and named factory ownership route, then projects one packed definition with exact EOF/count checks and ordered mesh slots; report under `reports/runtime_capture/collision/`; definitions and authored PPtrs do not identify a live query hit |
| Streaming collision definitions | `python -m scripts.game_data.streaming.collision_corpus --input-set-sha256 SHA --game-root GAME [--manifest MANIFEST]` | after `streaming.corpus`, authenticates the marker-17/ECS decoder bridge, ordered Mesh and fixed terrain resource keys, descriptor parameters and enum aliases; receipt plus gzip JSONL under `reports/animestudio/`; optional manifest full64 joins remain candidates |
| Streaming Mesh container candidates | `python -m scripts.game_data.streaming.collision_mesh_candidates --collision-receipt REPORT --scene-receipt REPORT --game-root GAME` | reuses an authenticated selected scene extraction, joins exact Bundle main-asset Mesh PPtrs and complete cooked buffers to stored manifest candidates; `##subasset` selection and live hit ownership stay unresolved; report under `reports/animestudio/` |
| Selected collider scene corpus | `python -m scripts.game_data.unity_scene_corpus --selection FILTER --outer-summary AUDIT --outer-ledger LEDGER --expected-input-set-sha256 SHA` | fresh scene/Mesh/AssetBundle JSON/raw exports, raw body/container-prefix checks, local or uniquely resolved external Mesh links and stored TRS chains; Mesh selectors require object coverage, AssetBundle selectors with PathID=0 select physical spans only; `--reuse-extraction REPORT` checks source and raw/JSON receipts; live placement remains unresolved |
| WebUI orchestration | `webui/export.py` (page registry `webui/pages.py`) | extraction, freshness, and every page's data |
| Story | `webui/story/build.py`, `refresh_evidence.py`, `source_links.py` | `webui/data/lang/<LANG>/`, `reports/story/` evidence, localized reference data |
| Gameplay | `webui/gameplay/build_gameplay.py` | Gameplay datasets; `--stage items` publishes items, buildings and recipe shards under `data/lang/<LANG>/gameplay/items/`; its `asset-refs` stage joins the last Gameplay and Assets publications and is the sole writer of `webui/data/assets/gameplay_refs.json` |
| Map | `webui/map/build_map_recovery_data.py` (its docstring documents the `export.bat map` sequence, `--with-preview`, `--preview-only`, `--jobs` and the render cache) | `reports/assets/map_recovery/`, `export_full/recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/`, `webui/data/map_recovery/` |
| Characters | `webui/characters/build_character_data.py` | character indexes, per-identity appearance sidecars, and versioned final-catalog snapshots |
| Text | `webui/story/build.py` (shared with Story) | localized reference tables under `webui/data/lang/<LANG>/reference/` |
| Audio | `webui/audio/build_audio.py` | decoded/relinked audio plus compact semantic evidence and shards |
| Assets | `webui/assets/build_assets.py` (`--mode default` for the served page; `--publish collision` for previews, `--publish collision-runtime` for runtime metadata) | asset indexes, the `relations.json` sidecar (Material/texture/model links; also read by the map preview and source graph), `table_owners.json`, compact `activity_media.json` (exact activity/instruction/reward images), media lookup and optional authenticated collision geometry/evidence |
| Decoded Data Inspector | `webui/data_inspector/build_data_inspector.py` | generic catalogs and lazy decoded-record shards |
| Updates | `webui/updates/build_updates.py` | `webui/data/updates/{latest,characters,story,map,gameplay}.json` |
| Recovery progress | `webui/recovery/build_recovery.py` | `webui/data/recovery/index.json` |
| Mission Pipeline recovery | `webui/mission_pipeline/build_mission_pipeline_data.py` | standalone recovery reports/data |
| Map01 RegionMap3D package | `webui/map/build_map_region3d.py` | a self-contained package plus its provenance sidecar |
| Packaging | `webui/package.py` | distributable static package |

For material shading fixes, `python -m scripts.webui.assets.build_assets
--publish material-appearance` refreshes existing Material appearance in
`relations.json` from the selected export's Unity store. It preserves texture
and model joins, the media index, and collision publications; new Material
links still require the normal broad index build.

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

Gameplay's `--stage battle-stages` publishes localized combat dungeon series,
explicit raid-mode pairs, enemy variants, artwork and fixed rewards to
`lang/<LANG>/gameplay/battle_stages.json`. `battle_activities.py` owns activity,
trial, completion-condition and season-destination navigation joins.
`battle_evidence.py` consumes Data's
last named LevelData/LevelScriptData/SpawnerConfig publication for conditional
host selection, stored spawn counts/timing and Buff references; it does not build
Data. Normal builds retain source freshness and selected-native gates. It is
included in normal Gameplay builds. For a preview over the last published
Text/Data/Assets/Gameplay publications without reading the export, run:

```bat
python -m scripts.webui.gameplay.build_gameplay --stage battle-stages --battle-stages-from-reference
```

This dedicated preview records missing tables and leaves unavailable raid modes
unclassified; it accepts no other stage or export/native path override. Data
snapshots validate publication framing and keep selected-native gates, and are
labelled as previews. Full builds accept `--game-root` for battle evidence;
an alternate export cannot silently use another installation's native evidence.

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
The Gameplay base stage also publishes Energy Alluvium term pools, area and
world-level rows, and reciprocal compatible-weapon links in its localized
index through `gameplay/gems.py`. These use exported Tables only.

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
not a production input. Story extraction omits Lua; Data and all-page extraction
include it. Refresh the index only from a complete plaintext-Lua extraction.
Task-hook declarations live in `game_data/contracts/mission_task_paths.json`.
Its loader re-proves named claims and typed storage on the selected binaries;
the protocol registry publishes the resulting current method identities and
explicit capture limits. The contract carries no old address catalog.

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

The Assets index uses `webui/assets/obj_geometry.py` to mark OBJ files without
a drawable triangle (`nd`); these remain inventoried for the off-by-default UI tag.

Assets index builds always detect byte-identical exported media and publish
preview deduplication metadata; no extra flag is needed. This applies to
`export.bat assets`, `export.bat assets --from-game`, all-page exports, and
`python -m scripts.webui.assets.build_assets --mode default --publish index`.
The WebUI groups confirmed copies within existing asset groups while retaining
all original files and source references. Other page-only runs leave the last
Assets publication untouched.

For FBX, `game_data/fbx_normalize.py` also supplies the `fc` content fingerprint:
the file's own document URLs/root label, non-bone Null instance labels,
placement/joint transforms, preferred angles, pose matrices and skin bind
matrices are excluded. Geometry, materials, mesh/bone names, skeleton
connections, skin indices/weights and animation still participate. The index
retains full-file hashes and every original file/resource path.
The same parse supplies `fv`, which keeps placement, pose and bind values
after ignoring the same labels. Assets uses it for separately selectable and
downloadable variants within each `fc` item; matrix compression alone is ignored.
The comparison runs only for broad Assets publications; focused and Story-media
publications skip it. `python -m scripts.webui.assets.build_assets --publish fbx-content`
refreshes only these keys in an existing broad index, checking
Animator provenance and published input hashes, without rebuilding other
Assets data. It rejects concurrent source/publication changes.

Model completeness tools are separate from a broad page rebuild:
`python -m scripts.game_data.fbx_inventory --export-root EXPORT --report REPORT`
inventories stored Animator geometry attachments (`--cache` reuses unchanged
rows). `animator_coverage` compares these with generic source renderer PPtrs;
the maintained `extraction/animestudio/animator_sources` sidecar reads those
complete selected source directories. `python -m
scripts.game_data.extraction.animestudio.repair_models --help` stages selected
repairs with CLI/resource/source receipts; `python -m
scripts.webui.assets.fbx_repair --help` backs up and publishes only validated
replacements into the existing broad index. `node
scripts/webui/assets/fbx_preview_audit.cjs --selection JSON --report REPORT`
checks selected hash-pinned files with the actual frontend mesh/skin/LOD code.
These tools report structural/static coverage, not runtime rendering parity.

Broad Assets builds optionally consume the current selected cooked-collision
receipt under `reports/assets/`; `--collision-corpus PATH` selects another.
They revalidate audited inputs and typed/raw joins, publish separate collision
OBJs under `webui/data/assets/collision/`, and record unavailable diagnostics
instead of retaining stale rows. `--publish collision` updates only that
projection in an existing broad index without rescanning render media or
rewriting the ownership/media sidecars. The raw corpus command above creates
the receipt; ordinary Assets extraction does not add Mesh JSON/raw jobs.

`--publish collision-runtime` refreshes runtime metadata on existing collision
previews. Select saved captures with repeated `--collision-runtime-session PATH`
and their authenticated sources with repeated
`--collision-runtime-stored-receipt PATH`. Successful selections are saved under
`reports/assets/collision_runtime_selection.json` (or
`--collision-runtime-selection PATH` under `reports/`) and revalidated on future
broad builds. `webui/assets/collision_runtime.py` projects the raw geometry audit
by exact identity and buffer hashes; failed admission/native/source gates clear
runtime claims and report the failed check, while retaining stored previews.

`--publish collision-authored` refreshes stored collider/prefab owners on
existing previews. Repeated `--collision-scene-receipt PATH` selects saved v4
scene-corpus extractions; no exporter or live capture runs. Successful paths
are saved under `reports/assets/collision_authored_selection.json` (or
`--collision-authored-selection PATH` under `reports/`) and revalidated on
future broad builds. The scene receipt API recomputes raw/typed pointer,
hierarchy and prefab-root joins; the Assets projection requires exact physical
Mesh identity, raw/cooked hashes and geometry dimensions. `game_data/unity_scene_meshes.py`
composes missing external targets with the admitted cooked-Mesh corpus, retaining
both selections and running complete target geometry checks. Failed gates clear
owner claims and report the failure, retaining previews and runtime metadata.

Add `--collision-model-receipt PATH` alongside the scene receipts to select an
existing Model source corpus. The authored selection v5 retains this path for
future replays. `dynamic_model_native.validate_receipt` authenticates the
selected source set and recomputes native-gated fields/manifest joins; the
Assets projection joins the active logical Bundle and declared prefab root,
and keeps Model axes separate from each collider's prefab-local matrix.
Missing/mismatched native or source inputs clear only Model metadata. Assets'
page registry declares the optional DynamicStreaming and bundle-manifest raw
inputs; no extraction or live capture runs during this metadata publication.

The same stage publishes selected stored MeshCollider assemblies through
`webui/assets/collision_prefabs.py`, under `webui/data/assets/collision_prefabs/`.
`cl.prefabs` and the `CollisionPrefab` source root supply preview/reset controls
and OBJ downloads. Per-collider stored Transform chains include the root TRS;
disabled definitions stay included. Coverage is selected MeshColliders and
separately admitted boxes, not other primitive/custom colliders or live placement. Assembly failures retain valid
owner/Model/runtime metadata and clear only assembly links.

`python -m scripts.game_data.unity_box_corpus --scene-receipt PATH` collects a
supplemental raw/typed BoxCollider scope from that scene's admitted physical
Bundles into `tmp/animestudio/collision_primitives/`, and publishes its receipt
under `reports/assets/collision_boxes_current.json`. This is a bounded static
extraction, not an `export_full/` refresh or live capture. Add
`--collision-box-receipt PATH` alongside scene receipts on the authored stage
to compose boxes with exact stored prefab assembly roots. The receipt is
revalidated on subsequent publications; `cl.prefabs` v2 distinguishes mesh/box
parts, stored center/full size and flags. Invalid BoxCollider admission leaves
mesh-only assemblies available.

`python -m scripts.game_data.unity_render_corpus --scene-receipt PATH` collects
the separately scoped MeshFilter/MeshRenderer supplement into
`tmp/animestudio/collision_renderers/` and writes
`reports/assets/collision_renderers_current.json`. The reviewed serialized
layout and independent EOF reader preserve material slot order and the trailing
vertex-stream pointer omitted by the typed constructor. Shared supplemental
source/producer gates authenticate both this lane and the BoxCollider lane.
Add `--collision-render-receipt PATH` alongside scene receipts on the authored
stage to publish `cl.renderers` v2 through exact physical prefab roots. The
selection retains paths for replay; unavailable/excluded resource references
stay explicit. Renderer failure clears only renderer claims, retaining the
other collision projections. Collection is bounded static extraction; ordinary
publication reads its receipt and never refreshes `export_full/` or runs a game.

`python -m scripts.game_data.unity_source_directory_corpus --scene-receipt PATH`
extracts complete selected serialized metadata, declared-class bodies and exact
owner-archive spans with an offline sidecar referencing the admitted CLI. It
writes ignored work files and `reports/assets/source_directories_current.json`;
independent directory/type-tree/Mesh readers validate framing and render buffers.
The CLI itself is not rebuilt. `python -m scripts.game_data.unity_render_resources --scene-receipt PATH
--render-receipt PATH --source-receipt PATH` recomputes resource and stored LOD
joins; `--collect-dependencies` and `--collect-material-resources` extend the
static source selection with located Mesh/material and shader/texture CABs.
Generated audits and selections stay under `reports/assets/`.

Select those admitted scopes on the authored publication with repeated
`--collision-render-resource-receipt PATH` alongside scene/render receipts.
`webui/assets/collision_render_assets.py` publishes neutral render Mesh and
stored-LOD assembly previews plus Material field documents through `StoredRender`.
Exact-source Texture2D top-mip previews use `game_data/unity_texture.py` for
complete mip framing and `unity_texture_decode.py` for the admitted AnimeStudio
codec sidecar; generated decode receipts stay under `reports/assets/` and work
files under `tmp/animestudio/texture_previews/`. Decoded channels are retained,
without gamma conversion, normal reconstruction or material application.
Failed resource admission clears only these derived links and retains admitted
component ownership. The stage neither refreshes the canonical export nor
executes a live game capture.

`python -m scripts.game_data.shader.corpus --scene-receipt PATH
--source-receipt PATH` admits selected Shader bodies, decodes segmented plain
LZ4/program directories, joins D3D code and parameter tables to stored passes
and keywords, and checks segment/code parity against the admitted CLI. Reports
stay under `reports/assets/`; unsupported platform records remain opaque.
`python -m scripts.webui.assets.shader_analysis --scene-receipt PATH
--source-receipt PATH` runs that gate and publishes an independent Shader-analysis
sidecar under `webui/data/assets/shader_analysis/`. Exact Shader identity/raw hash
and unchanged published Material artifact hashes gate its links. It does not
rewrite the existing asset index or renew its renderer admission; stored keyword
candidates do not select runtime shading.
Its v3 Material summaries retain explicit numeric values, Shader declarations
without numeric overrides, and conditional per-pass named parameter/resource
coverage with offset alternatives. The frontend uses existing immutable Mesh
and PNG artifacts for optional exact-slot texture-channel inspection; no new
canonical extraction or runtime capture is involved.
Add `--instructions` to publish checked VS/PS register and field reads through
the Windows system DXBC disassembler. `shader.instruction_corpus` runs that
reusable installed-format census alone, including bounded straight-line output
dependencies. `shader.capture_corpus --scene-receipt PATH --source-receipt PATH
--sessions-root PATH` joins freshly admitted stored programs to saved graphics
archive/draw metadata. `shader.capture_textures --draw-report PATH
--texture-receipt PATH` compares complete compressed GPU mip tails with frozen,
hash-checked stored preview inputs. Their reports stay in `reports/assets/`;
registration, draw-local operands, content equality and source Material ownership
remain separate. These commands do not launch the game or arm a capture.
`python -m scripts.webui.assets.mesh_uv --scene-receipt PATH --source-receipt PATH`
publishes admitted UV1 Mesh OBJ projections under `webui/data/assets/mesh_uv/`
and their receipt under `reports/assets/`. Fresh Mesh identity/raw hashes and
byte-for-byte reproduction of the original UV0 OBJ precede coordinate-only
projection; original Mesh artifact/body hashes and the stored-render publication
root gate frontend links, including changes confined to UV1.

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
The `semantics/record_media.py` projection publishes the optional
`lang/<LANG>/audio/record_media.json` for record-item Assets players, using
exact SpaceshipMusicTable event contexts and decoded Audio media candidates.

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
immutable in `webui/data/gameplay/projectiles.json`. Media evidence carries
`selectionNodePaths` (`[rootActionId, container…, leafObjectId]`) from the
typed HIRC traversal, and Gameplay sound events carry the `selectionTree`
that `semantics/gameplay_audio.py` rebuilds from them.

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
`wwise_effect_native` authenticates effect layouts and calls `wwise_effect_updates`
for reviewed anonymous numeric update routes; its gate returns those routes only
after the selected native triplet, dispatch tables, handlers and field joins pass.
Focused `wwise_mastering_updates`, `wwise_mastering_consumer`, `wwise_mastering_gain`,
`wwise_mastering_filter`, `wwise_mastering_dynamics`, `wwise_mastering_coefficients`,
`wwise_mastering_time`, `wwise_mastering_profiles`, `wwise_mastering_revisions`,
`wwise_mastering_legacy`, `wwise_mastering_trigonometry`, `wwise_mastering_startup`,
`wwise_mastering_shared`, `wwise_mastering_context`, `wwise_effect_small_fill`, `wwise_effect_scalar` and
`wwise_convolution_consumer` audits share that gate and their reviewed contracts.
`wwise_effect_integer_flow` supplies bounded symbolic loader proofs. These audits
authenticate update/source joins, conditional section/media consumers, mapped
channel gain arithmetic, descriptor admission, second-order IIR recurrence,
series routing, current band/peak controls, legacy header negotiation/control guards,
band-array/crossover routing and peak loop correspondence, crossover coefficient/packed-helper and time-helper arithmetic, static startup
initializer routing, local caller stride/descriptor joins, sparse-map pair index
boundaries, complete local buffer setup/reuse/failure routes, context sample
transitions/history capture, band/peak storage requests/failures and initial
history resets, bounded padding/cleanup writes, and partial
named math correspondence without publishing page data.
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

The short damage kernel recipe prepares with
`python -m scripts.game_data.mission_trace_capture_prepare --profile buff --recipe scripts/game_data/contracts/damage_runtime_kernel_capture.json --game-dir "PATH\Endfield Game" --output reports/runtime_capture/damage-kernel-build.json --report reports/runtime_capture/damage-kernel-preparation.json`.
It pairs formula/pack returns, scopes attribute getters to the two damage dump
callers, reads Boolean output pointees on return and records modifier/HP fields.
The local launcher uses `tools\EndfieldCapture\Capture.ps1 -Preset damage-kernel`;
the generic `mission_trace_inspect --local-files` command below decodes the
retained session. Entry bytes of output parameters are not formula outcomes.

| Owner / command | Output / boundary |
| --- | --- |
| `python -m scripts.game_data.mission_trace_capture_prepare --help` | offline signature/field/ABI proof, including generic/anonymous entries and closed layout witnesses; `--profile mission\|buff` selects scope; optional `--recipe` selects a reviewed contract; `mission_state_trace_capture.json` adds typed Param/EventData witnesses and GP-only paired state/AST calls, including separate lazy progress evaluation; `mission_daily_trace_capture.json` combines those with selected interactive/photo/SNS/script/action entries for the internal `Capture.ps1 -Preset mission-daily`; profiles under `reports/runtime_capture/` |
| `python -m scripts.game_data.mission_trace_source_archive --help` | retained mission context or `--profile buff` binary BuffData/available SkillData bytes and Buff tables; no current-native claim |
| `python -m scripts.game_data.mission_trace_inspect --session SESSION --output-dir reports/runtime_capture/INSPECTION --join-sources` | verifies saved identities, decodes typed fields and explicit synchronous invocation pairs; explicit `--local-files` analyzes current path/size inventories and selected source copies without legacy hash/replay admission; entry and return snapshots remain separate |
| `python -m scripts.webui.story_recovery.mission_capture_timeline --inspection-dir INSPECTION --output-dir reports/runtime_capture/TIMELINE` | rebinds a passing complete inspection to raw rows and receipts; explicit quest membership, restoration flags and configured predecessor corroboration stay separate from unowned playback; optional `--current-export-root` checks selected native inputs and observed mission-definition bytes; no Story ordering publication |
| `python -m scripts.game_data.buff_runtime_trace_inspect --inspection-dir INSPECTION --output-dir reports/runtime_capture/BUFF` | complete Buff sessions: raw-bound reset/reference, assignment, initialization and separate dispatch-triplet evidence; skill initializer and stored-data/NewAction reference matches with reuse/conflict diagnostics; optional paired `--corpus-summary`/`--corpus-ledger` joins stored-schema receipts; no action result, data-node selection or ownership promotion |
| `python -m scripts.game_data.mission_trace_diagnose --session SESSION --output-dir reports/runtime_capture/DIAGNOSTIC` | bounded failed-journal diagnostics by hook/field; reconciles per-hook attempted/recorded counts with queue losses and reports unexplained differences; diagnoses retained pair closure separately from producer completeness; preserves originals and never admits incomplete captures |
| `python -m scripts.game_data.mission_shared_native --gameassembly GA --metadata META` | `reports/runtime_capture/mission-shared-native.json`; lifecycle, objective-copy loops, default selectors, state predicates/quest lookup, combined AST/waiting gate, dialog, LevelScript and interactive-property claims; selected inputs gated before and after evaluation |
| `python -m scripts.game_data.mission_expression_native --gameassembly GA --metadata META` | `reports/runtime_capture/mission-expression-native-reviewed.json`; ASCII parser/resolver callers, checked Param source-selector leaves and concrete constructor/reader cells, typed state-event joins and default objective activation paths from `mission_expression_native.json`; native/byte/declaration/context gates, live construction and chronology remain conditional |
| `python -m scripts.webui.story_recovery.mission_mechanism_audit --mission-root export_full/game/Json/MissionRuntimeAsset --native-report RECEIPT.json --timeline-bundle BUNDLE.json` | `reports/runtime_capture/mission-mechanism-audit.json` and `.md`; named source census, reviewed selector inheritance, conditional named-state/Boolean source constraints and separately owned retained entries; receipts/source/native gates, no timeline-edge or page publication |
| `python -m scripts.webui.story_recovery.runtime_trace import --profile mission CAPTURE.jsonl` | saved Mission/Story event-schema validation and evidence bundle |
| `python -m scripts.webui.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl` | saved Audio event-schema validation and evidence bundle |
| `python -m scripts.webui.audio.semantics.effect_lifecycle_observer_profile --game-root "PATH\Endfield Game"` | `reports/audio/effect_lifecycle_capture_manifest.json`; unsampled effect-interface lifecycles, registration descendants and Room callback predicates, selected native gates, no launch. `wwise_effect_lifecycle_native` owns bank references, derived template address points, subscription targets and final destruction, borrowing the parameter owner. |
| `python -m scripts.webui.audio.semantics.effect_lifecycle_capture --game-root "PATH\Endfield Game" --session SESSION [--original-ak PRIVATE_DLL]` | `reports/audio/effect_lifecycle_capture_current.json`; frozen recipe/runtime and closed-pair checks, bank appends/releases, retained factory/load parameters, target membership, state entry/handle writes, clone/carrier/effect origins, exact setter payloads and final destruction. Nonlinear writes need the explicit identical private DLL; loss/unreadable selection withholds joins. Missing births and physical package occurrences remain explicit; accepted DSP captures are reused. |
| `python -m scripts.webui.story_recovery.prepare_audio_source_observer --game-root "PATH\Endfield Game"` | reconstructs the exact saved-profile recipe and validates selected native bodies, signatures and manifest ranges under `reports/audio/` |
| `python -m scripts.game_data.wwise_source_queue_native --gameassembly GA --metadata META --ak-sound-engine AK` | JSON audit on stdout; authored Action/Event registration, conditional intrusive-list order and target lookup, retained Event/queue pair, bank-source cookie and descriptor-selection rules; complete native/leaf/address-point bytes gated; no page publication or live Event/file binding |
| `python -m scripts.game_data.wwise_codec_factory_native --gameassembly GA --metadata META --ak-sound-engine AK [--include-voice-pipeline] [--include-voice-routing] [--include-sink-negotiation] [--include-authored-parameters] [--include-inheritance]` | JSON audit on stdout; source/plugin, codec, resident/node/numeric preparation, provider/RIFF and context sample interfaces; optional voice, routing and sink owners check owner/admission, frame assembly/release, route creation/bus mix/reset and format/service/capacity negotiation on the same image; authored parameters check whole Sound loading, collection, property-slot mapping and selected filter/gain consumers; inheritance checks hierarchy/registry/link, STMG/default/transition and object-component/listener selection consumers with existing owner dependencies; explicit native inputs gated; no decoding, engine-state changes, endpoint activation or page publication |
| `python -m scripts.webui.story_recovery.audit_audio_source_capture --game-root "PATH\Endfield Game" --manifest PROFILE.json --input CAPTURE.jsonl --output reports/audio/source_observer_capture_audit.json` | strict immutable-snapshot, sequence, pairing, field and clean-stop audit using the saved profile and adjacent diagnostics |
| `python -m scripts.webui.story_recovery.prepare_endfield_source_owner --game-root "PATH\Endfield Game"` | `reports/audio/endfield_source_owner_manifest.json` and offline preflight; selected source/queue/carrier gates |
| `python -m scripts.webui.story_recovery.prepare_audio_playback --game-root "PATH\Endfield Game" [--device \| --mixer \| --mixer-frame \| --sink-handoff \| --mixer-consumer \| --master-stage \| --bus-processing \| --mix-contributions \| --room-blend \| --room-input \| --room-history \| --room-wet \| --room-configuration]` | `reports/audio/playback_capture_manifest.json`; reviewed source/owner, component/listener, parameter and buffer phases. `--device` adds render-client results/copy bytes; `--mixer` adds stored owner identity, actual rows and output conversion; `--mixer-frame` adds paired bus mix/publication/reset with unsampled source/reset endpoints; `--sink-handoff` writes `sink_handoff_capture_manifest.json` and adds complete sink write/frame-end/submission observations in manually selected native windows. `--mixer-consumer` writes `mixer_consumer_capture_manifest.json` and adds original unfiltered consumer PCM/gain/matrix and initial/returned output through an eight-argument pair. `--master-stage` writes `master_stage_capture_manifest.json` and adds paired first master input/gain/mode/rounding and before/after PCM. `--bus-processing` writes `bus_processing_capture_manifest.json` and adds sampled whole output tasks with all selected descendants, scoped post-mix/effect transitions, floating frame-gain arguments, first effect Execute targets and original EQ/biquad operands. Selected native gates, no launch; launch instructions stay in the internal capture checkout. `--mix-contributions` writes `mix_contributions_capture_manifest.json` and adds original per-channel AVX constant/ramp additions plus independent multi-source consumer output reads. `--room-blend` writes `room_blend_capture_manifest.json` and adds the registered RoomVerb instance and three-buffer dry/wet blend through ten mixed arguments. `--room-input` writes `room_input_capture_manifest.json` with original input preparation, stereo folding, indexed source operands and wrapped circular copy/swap history plus delay/tone branch controls. `--room-history` adds complete tone-matrix operands and wrapped paired input/output diffusion history. `--room-wet` adds full early-tap projections, four-ring feedback and wet damping with Room-owned state snapshots. `--room-configuration` writes `room_configuration_capture_manifest.json` and adds the complete stored parameter projection and sample rate using the existing sites. |
| `python -m scripts.webui.audio.semantics.playback_capture SESSION --game-root "PATH\Endfield Game" [--device \| --mixer \| --mixer-frame \| --sink-handoff \| --mixer-consumer \| --master-stage \| --bus-processing \| --mix-contributions \| --room-blend \| --room-input \| --room-history \| --room-wet \| --room-configuration]` | Streaming saved phase review in `reports/audio/playback_capture_current.json` with a recipe beside each output; selected native gates, staged runtime/recipe, window/field/pair checks and Action/source/owner transport. `device_capture` owns COM/copy; `mixer_capture` owns conversion; `sink_pcm_witness` checks first-plane constant gain; `playback_lineage` checks/counts all current PCM with bounded identity examples; `mixer_frame_capture` owns publication/reset intervals and bus input/output. `mixer_pcm_witness` checks a supplied bounded constant matrix equation; `sink_handoff_capture` owns write/consume intervals for authenticated complete endpoint scopes. `--sink-handoff` checks explicit native window IDs/closure, complete sink endpoints, then links conversion and device copy only by checked invocation IDs and matching prefixes. `mixer_consumer_capture` owns same-call consumer inputs, address/argument/closure checks and bounded equations; `--mixer-consumer` retains source candidates under completed parent bus nesting and descriptor/sample identity. Accepted live comparisons remain bounded source/mixer/bus prefixes; `master_stage_observer_profile` owns borrowed master declarations and `master_gain_witness` checks the admitted constant first-plane equation under `--master-stage`. `bus_processing_capture` admits same-task mix/processing/master prefix transitions and links only the admitted master invocation to device; it separates frame-gain arithmetic, unity reset and remaining effect changes. `biquad_capture` admits original EQ service coefficient/history/PCM operands through the actual instance and collection handoff; the selected native first-block programs feed `biquad_pcm_witness` for bit-exact bounded SSE/AVX comparison. `wwise_biquad_arithmetic` owns portable integer rounding and fused arithmetic. Whole buffers, global bus generations and whole Event-to-device claims remain open. Selection totals bound closed-window entries; excess stays unattributed. Historical incorrect ID/array reads are excluded. `mix_contributions_capture` checks exact constant/ramp additions, original consumer output returns, ordered mixed prefixes and conditional source/Event/file candidates under `--mix-contributions`; it links only the already admitted task to device. `mix_bus_lineage` connects completed intermediate bus prefixes through observed writer/reset intervals; `room_blend_capture` checks actual registered RoomVerb nesting, separately rounded dry/wet sums and normal Room/effect returns under `--room-blend`. Its native contract and arithmetic live in `scripts/game_data/`; complete live history remains open. `room_input_capture` compares indexed stereo folds, circular old-history output/index progression and same-Room preparation/delay handoffs under `--room-input`; `wwise_room_input_native` and `wwise_room_input_arithmetic` own selected native declarations and portable prefix models. `room_history_capture` adds bounded tone/diffusion replay and ordered input preparation chains under `--room-history`, with selected bodies in `wwise_room_history_native`. `room_wet_capture` owns early/FDN/damping prefix comparison and return-time ownership under `--room-wet`; `wwise_room_wet_native` and `wwise_room_wet_arithmetic` own its selected bodies and portable models. `room_configuration_capture` owns matching parameter snapshots and derived-state comparisons under `--room-configuration`; `wwise_room_configuration_native` owns lifecycle/configuration and store extents, and `wwise_room_configuration_host` executes the selected original initialization on bounded owned buffers without engine initialization. `wwise_room_parameters_native` owns parameter clone/update/default/termination and generic template/registry/carrier joins; `wwise_room_parameters_host` executes isolated original parameter operations on owned storage. |
| `python -m scripts.webui.audio.semantics.playback_package_candidates [--game-root "PATH\Endfield Game"]` | `reports/audio/playback_package_candidates_current.json`; compares source-word candidates with current supplied-corpus headers; explicit selected root adds native-gated complete external-path hashing; no live occurrence selection or decoding |
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
The package option covers native encrypted-header/table admission, package-list
precedence and numeric key/language lookup alongside external-path hashing;
it authenticates those rules without decoding or publishing media.
`--include-standard-stream` independently checks numeric stream construction,
read completion and resident-memory provider handoff, reusing existing native
group and leaf owners. It authenticates the original read/decryption interfaces
without executing I/O or admitting game scheduling or a live playback generation.

`build_audio --package-catalog-only --package-input-set-sha256 SHA` refreshes the
static package inventory in an existing publication. The raw gate,
`game_data/wwise_package_corpus --expected-input-set-sha256 SHA`, authenticates
available PCKs against the VFS roster and logical-payload hashes, then writes
`reports/audio/package_corpus_current.json`. `game_data/wwise_package.py` owns
AKPK framing and shared media/header crypto; `semantics/package_catalog.py`
owns the page projection. Missing packages, duplicate keys and low-word
collisions remain explicit. Full semantic builds revalidate the existing roster.

`python -m scripts.game_data.wwise_bank_settings_corpus --package-receipt RECEIPT.json --expected-input-set-sha256 SHA --output reports/audio/bank_settings_corpus_current.json`
uses that authenticated available-package roster to sweep bank section headers
and exact v150 STMG framing. `wwise_bank_settings.py` owns the raw reader;
`wwise_bank_settings_corpus.py` owns source/build/roster gates and the generated
report. Neither selects runtime parameters nor publishes Audio page data.

`python -m scripts.game_data.wwise_effect_controls_corpus --package-receipt RECEIPT.json --expected-input-set-sha256 SHA --gameassembly GA --metadata META --ak-sound-engine AK --output reports/audio/effect_controls_corpus_current.json`
uses the same authenticated roster and an explicit selected native gate to
inventory complete common FX controls. `wwise_effect_controls.py` owns bounded
parameter/media/RTPC/state/default framing; `wwise_effect_controls_native.py`
authenticates the state loader and borrows existing FX loader/factory bodies.
The corpus gate owns source hashes and enclosing bank/HIRC coverage. FX IDs
retain their plug-in parameter domain; effective live states stay unresolved.
`wwise_builtin_parameters_native.py` authenticates the selected ray-array,
distance, built-in binding-list and scoped-value path on the caller's explicitly
gated opened image, borrowing the existing Init settings owner. It supplies no
live emitter/listener identities or current control values.

## Updates

Page export and Updates publication are separate commands. Keep a complete
previous export before refreshing the current export with `export.bat
--from-game`, then compare the saved pair.

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
levels, Gameplay source records for optional page badges and previous/current
field and linked-file comparisons, independently of asset flags and sample
limits. Linked-file previews reuse the feed's bounded maintained readers.
`gameplay_sources.py` owns typed entity joins; `gameplay_items.py` honors
catalog source-field selections and keeps related item labels terminal.
`catalog_sources.py` owns Combat stage sources and the Activities page's exact
guide/related-reward joins; both subpages use the shared badges and filters.
`build_page_updates(..., pages=(...))` permits focused sidecar maintenance
without recomputing unrelated page comparisons.
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
| `--expected-input-set-sha256 SHA` (`--input-set-sha256` in `streaming.*`) | the `inputSetSha256` of the current `vfs-audit` summary; the gate reauthenticates the outer VFS ledger and refuses a mismatch. It fingerprints the CLI apphost EXE; runtime DLL drift is checked separately. Re-run the audit after an exporter rebuild, even when this value stays the same; never edit a recorded value |
| `--game-root ".../Endfield_Data"` or `--gameassembly GA --metadata META` | the explicit selected native pair; a missing or different build yields no validated rows |
| `--export-root export_full/game/Json --ledger reports/animestudio/jsondata_current_files_latest.jsonl.gz --summary reports/animestudio/jsondata_current_latest.json` | joined source replay against the complete JsonData corpus receipt; pass the three together |
| `--input-root DUMP_ROOT` | a targeted `AnimeStudio.CLI dump` tree holding the named `Data/...` files, authenticated by VFS MD5 |
| `--buff-report`, `--action-report`, `--corpus-report` | the upstream gate report a receipt rejoins (`buffdata_current_latest.json`, `buff_action_receipts_current_latest.json`, ...) |
| `--limit`, `--max-files` | bounded diagnostics only; output belongs in `tmp/` or `scratch/` and never certifies a corpus |
| `--output`, `--out`, `--report`, `--output-json`/`--output-md` | report path; defaults live in the module |

`levelscript_source_receipts.py` binds source replays to the complete reader,
selected native inputs and matching StringPool receipts before and after reading.
Plain replays share its exact-span loop; domain and script-ID checks stay with
their validators. Unproved direct EntityPtr/LevelScriptPtr interpretations refuse.

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
| `dynamic_group_components_native` | nested DataGroup component layouts and explicit grid-local target spans over authenticated main files; explicit native pair, `--input-root`, `--expected-input-set-sha256`, optional `--output-json` | `dynamic_group_components_native_latest.json` |
| `dynamic_group_owner_join` | joins typed group children to template-checked authored RootComp candidates on the same raw bytes; explicit native pair, `--game-root`, `--export-root`, `--input-root`, `--expected-input-set-sha256`; alternate audits use `--outer-report`/`--ledger` | `dynamic_group_owner_join_latest.json` |
| `dynamic_erosion_consumers_native` | re-proves PosList/group index to Unity Vector3 arguments and unchanged CoreId return; required `--gameassembly`/`--metadata`, optional `--output-json`; native-only proof, with ordinary and explicit proxy ABI gates | `dynamic_erosion_consumers_native_latest.json`; no source corpus refresh or live insertion/activation claim |
| `dynamic_mission_condition_consumers_native` | re-proves selected MissionCondition State/IsSame comparison and the anonymous cache changed flag; required `--gameassembly`/`--metadata`, optional `--output-json`; source-owned getter/carrier and selected control-flow gates | `dynamic_mission_condition_consumers_native_latest.json`; provider/cache ownership and runtime truth remain separate |
| `dynamic_mission_ready_native` | re-proves names-based, image-qualified ready claims and the typed player/mission tail request; required `--gameassembly`/`--metadata`, optional `--output-json`; complete selected entry and return paths | `dynamic_mission_ready_native_latest.json`; false-patch/non-null path returns true, without establishing a stored or live readiness state |
| `dynamic_mission_key_source_native` | re-proves the source-owned GetStrKey returned Int32, bounded slot writer and matching query-key lane; required `--gameassembly`/`--metadata`, optional `--output-json`; concrete context, byte-flow and selected-input gates | `dynamic_mission_key_source_native_latest.json`; same-slot/storage conditions remain explicit, with allocation and live ownership unresolved |
| `dynamic_mission_string_providers_native` | re-proves the ordinary string-length branch, typed UInt64-to-Int32 lookup, signed counter and selected GetStrKey value-source paths; required `--gameassembly`/`--metadata`, optional `--output-json`; complete selected programs and source/native gates | `dynamic_mission_string_providers_native_latest.json`; hash computation, live dictionary contents, synchronization and global uniqueness remain unresolved |
| `dynamic_mission_state_cache_native` | re-proves the complete selected Mission/Quest callback requests, typed receivers, same key local and concrete dictionary setter context; required `--gameassembly`/`--metadata`, optional `--output-json`; primary/cold ownership and source/native gates | `dynamic_mission_state_cache_native_latest.json`; generic event fields, live cache contents and condition truth remain unresolved |
| `dynamic_mission_{string_enqueue,stored_state,state_symbols,state_set,pause_writes,completion_predicates}_native` | typed lookup/local-copy requests, returned MissionData enum-field/null bits, concrete Mission/Quest enum declarations, authored IsQuest/key-to-HashSet Add requests, selected typed pause-field byte writes and Boolean completion predicates; required `--gameassembly`/`--metadata`, optional `--output-json`; independent selected-native/source gates | `dynamic_mission_*_native_latest.json`; failed checks preserve publication; managed value layout, lookup implementation, actual set mutation, live state, network effects and source/cache classification remain separate |
| `dynamic_quest_{pause_requests,pause_dirty,display_list}_native` | named pause/listening requests, selected MissionData dirty-byte writes and normal returns, and the typed display-list return after RefreshIfDirty; required `--gameassembly`/`--metadata`, optional `--output-json`; independent selected-native/source gates | `dynamic_quest_*_native_latest.json`; failed checks preserve publication; opaque collection helpers, list mutation, full refresh semantics and live state remain separate |
| `dynamic_quest_state_message_writes_native` | selected message String/Int32 transfers into concrete QuestData fields and the caller-local old-state spill; required `--gameassembly`/`--metadata`, optional `--output-json`; typed constructor/field and native/source gates | `dynamic_quest_state_message_writes_native_latest.json`; sender state is Int32, with allocation success, dictionary ownership/mutation and live state separate |
| `dynamic_quest_state_value_source_native` | selected GetQuestState direct record-state return and returned-String/MissionData fallback mapping; required `--gameassembly`/`--metadata`, optional `--output-json`; complete selected programs, ordinary storage/enum ABIs and source/native gates | `dynamic_quest_state_value_source_native_latest.json`; failed checks preserve publication; opaque dictionary API, returned-String hierarchy, record identity/stability and live state remain separate |
| `dynamic_quest_parent_string_source_native` | selected String-return paths, actual ordinary IndexOf/Substring requests and preserved local result; required `--gameassembly`/`--metadata`, optional `--output-json`; qualified method/enum/storage ABI and source/native gates | `dynamic_quest_parent_string_source_native_latest.json`; failed checks preserve publication; delimiter, String algorithms, cache API, stable selection and mission hierarchy remain separate |
| `dynamic_quest_action_requests_native` | selected SucceedQuest request suffix and SafeRunQuestAction direct branches; required `--gameassembly`/`--metadata`, optional `--output-json`; same typed recipients, QuestAction declarations, owned instruction boundaries and native/source gates | `dynamic_quest_action_requests_native_latest.json`; failed checks preserve publication; queue mutation, complete SucceedQuest entry reachability and executed actions remain separate |
| `dynamic_quest_objective_boolean_native` | selected Objective completion byte-to-Boolean returns and compatible record/List context; required `--gameassembly`/`--metadata`, optional `--output-json`; qualified ordinary ABI, typed fields, context descriptors and source/native gates | `dynamic_quest_objective_boolean_native_latest.json`; failed checks preserve publication; indexed API identity, anonymous bound ownership, valid indices and live selection remain separate |
| `dynamic_level_{predicate_value_sources,state_writes}_native` | selected Level availability/started/id returns and Load/Start/Ready/Unload entry prefixes through concrete State stores; required `--gameassembly`/`--metadata`, optional `--output-json`; ordinary method/field/enum identities and direct JSON/native/source gates | `dynamic_level_*_native_latest.json`; failed checks preserve publication; writes are conditional observed prefix effects, with later calls, complete writer returns, concurrent state changes and lifecycle behavior unresolved |
| `dynamic_*_native` (main, data_index, system_routing, root_comp, resource_comp, sludge_surf_tile, stream_area, version, version_ban, active_version, aux_bridge, visibility_runtime) | selected-build layouts, accessors and call chains, rejoined to a targeted dump (`--input-root`) where they read stored records | `dynamic_*_native_latest.*`, `dynamic_visibility_runtime_claims_latest.json` |
| `dynamic_model_runtime_native` | reprove named stored-transform, prefab-load, runtime scene-matrix, parenting and child-collider enable routes; explicit `--gameassembly`/`--metadata` and expected hashes; failed gates/claims preserve the validated report | `dynamic_model_runtime_claims_latest.json`, separate `dynamic_model_runtime_claims_failure_latest.json` |
| `dynamic_model_native` | complete inline Model fields and manifest prefab-path joins; explicit native pair, `--input-root` raw DynamicStreaming folder, `--manifest`, `--outer-report`, `--ledger`, `--expected-input-set-sha256`; optional `--scene-receipt` requires declared prefab roots and active logical Bundle identity for collider joins | `dynamic_model_current_latest.json`; failed gates preserve it and write `.failed.json` |
| `dynamic_{visibility_area,visibility_state,streaming_config,main_path}_join`, `dynamic_version_id_domain`, `portal_center_join` | joins of validated native reports with the area corpus, MapConfig, exports and LevelData portals | `dynamic_*_latest.*`, `reports/game_data/portal_center_join_latest.json` |
| `bundle_manifest_{corpus,native}`, `bundle_cab_dependency_corpus`, `bundle_cab_exceptions`, `bundle_external_identity_corpus` | `manifest.hgmmap` from the bundle-manifest dump (`--manifest`); CAB dependencies against `export_full/meta/cab_map` | `bundle_*_latest.json` |
| `string_path_hash_{native,corpus}` | path-hash catalogs against VFS and manifest hashes (`--scope main` or `initial`, kept in separate reports) | `string_path_hash_*_latest.json` |
| `extend_data_*` (compress_corpus, graph_native, graph_owner_corpus, graph_ai_native/corpus, spawner_library_native/corpus) | ExtendData graphs, owners and spawner-library joins | `extend_data_*_latest.json` |
| `enemy_ai_runtime_native` (`--gameassembly --metadata --expected-*-sha256`) | enemy AI graph selection/scheduling and task-to-skill claims | `reports/game_data/enemy_ai/enemy_ai_runtime_claims.json` |
| `ifix_vm_{instruction,operands}_native`, `ifix_external_signatures_native` | IFix VM opcodes, operand joins and extern signatures over supplied patch dumps | `ifix_*_current.json` |
| `ifix_runtime_evidence --help` | Rebind saved entry inspections and selected IFix native receipts; audit alias/context observation requirements without admitting runtime claims | `reports/ifix/runtime_evidence_current.json`; no launch, attachment or observer changes |
| `streaming.corpus`, `streaming.marker{17,13,2}_corpus`, `streaming.marker15_gap_corpus` | block-15 root subgraphs and marker bodies (`marker15_gap` takes `--scene`) | `streaming_*_latest.*` |
| `streaming.descriptor_{name_corpus,names,component_index_gate,mask_corpus}` | Init slot-7 descriptor names and anonymous mask positions | `reports/chunk_data/` |
| `jsondata_corpus` | identity and routing of every JsonData file, with a per-file status consumers gate on; `--buff-report`/`--skill-report` select complete family receipts without overwriting a historical cursor basis; failed runs preserve prior publications and record bounded validator/predicate/source-hash diagnostics; unsafe output aliases fail before companion publication | `jsondata_current_latest.{json,md}`, `jsondata_current_files_latest.jsonl.gz`, companion `.validation.json` |
| `jsondata_schema_coverage` | named bytes per family and bucket, ranked by unnamed bytes (never read `bytesConsumed` as coverage) | `reports/game_data/jsondata_schema_coverage*.json` |
| `levelscript_corpus` | independently joins both complete LevelScript families to a full VFS audit and existing exports, with native and complete raw-package reader gates; `--outer-summary`/`--outer-ledger`, required `--expected-input-set-sha256`, optional `--export-root`/native pair/`--output`; no Buff/Skill receipt dependency | `reports/game_data/levelscript_current_latest.json`, companion `.validation.json`; separate from the complete JsonData registry and WebUI publication |
| `levelscript_first_stop_census` | reruns the selected owner on every authenticated `bounded_partial` source and ranks first refusals by whole files; JsonData mode uses `--summary`/`--ledger`, independent family mode uses `--family-receipt` plus required `--expected-family-receipt-sha256`; both require `--expected-input-set-sha256` and use `--export-root` pointing to `game/Json`; `--family LevelScriptTemplateData` selects templates | `reports/game_data/levelscript_partial_first_stops_current.json`, or `levelscript_template_partial_first_stops_current.json`; family mode checks live inputs before and after; failed runs preserve the last census and write the separate `.validation.json` diagnostic |
| `levelscript_receipt_compare` | compares two saved complete family receipts with `--before`/`--after` and required artifact SHA256s; identical audit input sets by default, or explicit `--allow-audit-run-change`; every source and selected-native identity, decoded EOF and no-regression gate still applies | v2 stdout comparison, optional `--output` under `reports/`; records both audit identities, rejects input aliases and other owners, preserves output on failure, and never claims current inputs or partial cursor progress |
| `damage_snapshot_consumer_native` | re-proves snapshot consumer, cache construction, request/store/getter/reset paths, selected named numerical rules and bounded control graphs; `--gameassembly`/`--metadata` select inputs, `--output` selects an ignored report path; every nonvalidated result preserves it | `reports/game_data/damage_snapshot_consumers_native.json`; separate `.diagnostics.json` for native/source refusals, pending claims and tooling failures |
| `damage_pack_scale_native` | authenticates conditional zone, modifier, formula, immunity/tag, shield, base-HP and part-transfer rules; `--gameassembly`/`--metadata` select inputs, `--output` selects an ignored report; optional `--export-root` plus `--game-root` projects the fresh stored zone config (`--zone-config` selects a document). Runtime selection and final output parity remain separate | `reports/game_data/damage_pack_scale_native.json` |
| `levelscript_pos_rot_native` | `--game-root`: authenticate selected current PosRot value, pooled Param, list capacity/store and typed adapter/provider transfers | CLI audit; runtime camera/provider selection and owner EOF remain separate |
| `levelscript_spline_ptr_native` | `--contract`, selected `--game-root` or explicit native pair: authenticates the current stored `Param<SplinePtr>`, four-byte ID/cursor, owned stores and pooled path | stdout audit only; parent movement and complete owner require separate validation |
| `levelscript_{gameplay_tag_param,water_volume_ptr_param}_native` | optional `--game-root`/`--contract`: authenticate actual four/eight-byte scalar sources, cursor updates, typed wrapper methods and selected allocation/store paths; shared proof primitives live in `memorypack.scalar_param_native` | stdout audit only; registered generic entries, actual caller targets, parent read order and complete owner are checked separately |
| `levelscript_environment_volume_ptr_param_native` | optional `--game-root`/`--contract` or explicit `--gameassembly`/`--metadata`: authenticate the independent raw UInt64 child and pooled path with the shared scalar proof | stdout audit only; EnvironmentEnable parent admission remains separate |
| `levelscript_bool_param_native` | optional `--game-root`/`--contract` or explicit native pair: authenticate the generated Boolean Param's typed byref ABI, owned allocation/stores, byte normalization and pooled path; ActionMap requires this gate | stdout audit only; parent/default selection and owner EOF remain separate |
| `levelscript_int_param_native` | same selected-input flags: authenticate the independent Int32 storage component through `memorypack.primitive_param` | stdout audit only; the Int32 evaluator, enclosing cursors and owner admission are separate |
| `levelscript_string_param_native` | same selected-input flags: authenticate String Param's two pooled reads, typed owned slots and reference barriers | stdout audit only; enclosing/default formatter selection and owner admission are separate |
| `levelscript_float_param_native` | same selected-input flags: authenticate Single Param's raw XMM transfer, typed owned store and pooled path | stdout audit only; default/provider selection and owner admission are separate |
| `levelscript_uint_param_native` | same selected-input flags: authenticate UInt32 Param's buffered object-header helper, typed setter calls, unwind-owned null branch and pooled path | stdout audit only; default/provider selection and owner admission are separate |
| `levelscript_ulong_param_native` | same selected-input flags: authenticate UInt64 Param's complete QWORD read/cursor program and owned typed-setter/null paths | stdout audit only; default/provider selection and owner admission are separate |
| `levelscript_vector3_param_native` | same selected-input flags: authenticate Vector3 Param's typed source, disjoint stack result and complete twelve-byte owned transfers | stdout audit only; parent/list/default selection and owner admission are separate |
| `levelscript_vector2_param_native` | same selected-input flags: authenticate Vector2 Param's typed context, packed XY return, SIMD restores and matching owned setter | stdout audit only; parent/list/default selection and owner admission are separate |
| `levelscript_param_output_native` | same selected-input flags and optional `--codec-kind`: authenticate closed output wrappers, raw Int32 target, pooled path, complete caller variants and owned null exits | stdout audit only; no serialized T value, live/default provider selection or owner admission |
| `levelscript_enum_param_native` | same selected-input flags: authenticate the reviewed closed enum Param catalog, signed Int32 backing, typed ReadUnmanaged context, complete caller/null program, owned setters and pooled path | stdout audit only; unknown enum components refuse, and parent/default selection and owner admission remain separate |
| `levelscript_byte_enum_param_native` | same selected-input flags: authenticate the reviewed unsigned-byte enum Param component, raw byte source, typed four-field caller/setters and pooled path | stdout audit only; byte values remain intact, and parent/default selection and owner admission remain separate |
| `levelscript_camera_target_param_native` | same selected-input flags: authenticate the initialized buffered target-enum Param, raw Int32/source/path reads, owned stores, factories/getter and bitmap marking branches | stdout audit only; cold initialization/refill, live provider selection and enclosing camera owner remain separate |
| `levelscript_area_rule_native` | internal library used by the protocol registry with an explicit selected NativeImage, actual/named targets and typed empty-exit witness; the scalar buffer, outer-branch and geometry relation tools live under `il2cpp/` | authenticated conditional original initialized rule only; finite Euler inputs, original icall caches and explicit override/storage/FP premises stay in the projection |
| `levelscript_script_ptr_param_native` | optional `--game-root`/`--contract` or explicit `--gameassembly`/`--metadata`: authenticate the current raw16 LevelScriptPtr Param source, owned stores, reference factories/getter, concrete registration and pooled tail | stdout audit only; stored ID/level/padding do not establish effective script resolution, live providers or enclosing owners |
| `levelscript_null_param_native` | same selected-input flags: authenticate reviewed one-byte null class-Param branches and reference getters | stdout audit only; positive values, generic provider selection and owner admission remain separate |
| `levelscript_long_param_native` | optional `--game-root`/`--contract` or explicit `--gameassembly`/`--metadata`: authenticate the buffered eight-byte source, signed Int64 ABI and four-field Param composition with a separately proved pooled path | stdout audit only; selected native pair and pooled source are rechecked outside the cache; parent routes and physical owner EOF require separate proofs |
| `levelscript_param_value_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: authenticate selected closed Int32 evaluator entries, actual caller targets, explicit byref constant copy and generated typed wrapper slots | stdout audit, optional report under `reports/`; source/native gates clear rows on failure and preserve publication; runtime receiver/provider choice and stored-codec integration remain conditional or unresolved |
| `levelscript_long_param_value_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: evaluate qualified named Int64 consumer claims, closed registered entries, selected full-width caller/constant transfers and generated setter view; declared types and named registration/wrapper logic live in `levelscript_param_types` and `levelscript_param_value_bridge` | stdout audit, optional report under `reports/`; changed claims are `pendingReview`, native/source refusals clear rows and preserve publication; runtime selection and stored cursor/evaluator integration remain separate |
| `levelscript_long_param_storage_consumer_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: join the independently validated stored Int64 wrapper to the named consumer through concrete holder/getter/setter identities, disjoint field intervals and the selected ready CONST path | stdout audit, optional report under `reports/`; one conditional constant bit-flow association with explicit wrapper/holder/storage identity requirements; actual pooled-string dependency and selected GA/MD/Unity inputs are checked before/after; runtime selection and enclosing owner admission remain unresolved |
| `levelscript_global_var_callback_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: validate the complete owned global-variable callback, its selected original normal paths, actual loaded generic contexts and signed Int64-to-Single comparison requests | stdout summary, optional report under `reports/`; the byref QWORD lane remains anonymous, shared enum implementation compatibility is conditional, and the result is an enum setter request; concrete comparison results, setter effects and live event order remain unresolved |
| `levelscript_bool_param_value_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: evaluate named Boolean evaluator claims, actual caller targets, complete selected byte transfer and generated typed setter view | stdout audit, optional report under `reports/`; copied storage bytes are not proved normalized to `0/1`; runtime selection, nonconstant providers and stored cursor integration remain unresolved |
| `levelscript_float_param_value_native` | required `--gameassembly`/`--metadata`, optional `--contract`/`--output`: evaluate named Single claims, actual caller targets, the complete owned warm/cold return join and unchanged four-byte constant transfer | stdout audit, optional report under `reports/`; selected returns preserve low Single bits without arithmetic or conversion; runtime selection, other providers and stored cursor integration remain unresolved |
| `gpu_ui_corpus`, `leveldata_bezier_knot_corpus`, `leveldata_spline_runtime_native`, `map_mark_relations` | GPUI named schemas; LevelData knot frames; spline consumer; GameplayConfig map-mark joins | `gpu_ui_current_latest.json`, `reports/story/recovery/`, `reports/game_data/` |
| `levelscript_fmv_video_native.validate(...)` (Python API) | Authenticate current bounded FMV source/name programs, typed declarations/contexts, owned native windows, literal-derived recipe and independent StringParam/copy gates; accepts `game_root`/`contract_path` or explicit native paths | Conditional source/name facts only; initialized iFix/default/cache/allocator/gender/suffix/VFS choices, owner EOF, coverage and playback remain separate |
| `levelscript_fmv_video_corpus --expected-input-set-sha256 SHA --expected-family-receipt-sha256 SHA` | Fresh current pooled owner-to-Video join; optional `--family-receipt`, `--source`, `--export-root`, `--game-root`, `--contract` | `reports/story/recovery/current_levelscript_fmv_video_join.json`; requires the current complete LevelScript family/pool receipt, retains per-source refusals and never clears unused-cutscene safety |
| `memorypack.skill_corpus`, `memorypack.skill_timeline_cursor`, `memorypack.skill_cursor_*`, `il2cpp.skill_cursor_*` | SkillData whole-file gate and the saved cursor-receipt verification chain | `skilldata_*_latest.*` |
| `lipsync_native`; `memorypack.lipsync_corpus --expected-input-set-sha256 SHA` | Re-prove the selected channel reader with `--regenerate --write`, then join available JsonData/JsonLip language identities and require strict EOF; wholly absent languages remain explicit exclusions | native stdout audit; `reports/animestudio/lipsync_current_latest.{json,md}` |
| `spawner_records_native [--regenerate --write]` | Validate the selected Spawner root read/setter order, typed contexts, pooled strings and Boolean leaves; declaration drift refuses regeneration | `reports/game_data/spawner_record_sources_native.json`; source facts do not establish runtime spawning or collection-provider selection |
| `serialization_roots_native [--regenerate --write]` | Validate world-root declarations/counts, preserved source arguments, risk/world-list joins, pooled LevelScript template path and LevelData scene ID | `reports/game_data/serialization_roots_native.json`; positive list/property children and whole-owner admission remain separate |
| `char_interact_perform_actor_native.validate_current_native_contract(...)` (Python API) | Validate the selected actor source contract, typed fields, source/store instructions and owned code/table windows; accepts explicit `gameassembly` and `metadata` paths | Returns actor facts only after before/after native gates; missing or mismatched inputs return no fields; enclosing-owner admission stays false |
| `leveldata_function_area_native [--regenerate --write]` | Validate the current base additions, factory-hide read/setter order, typed sources and enum storage | `reports/game_data/leveldata_function_area_native.json`; stored configuration does not establish runtime visibility |
| `leveldata_airwalls_native [--regenerate --write]` | Validate air-wall declarations/counts and pooled radio/effect/mission-ID sources, including the mission-ID setter transfer | `reports/game_data/leveldata_airwalls_native.json`; callback consumers and collector behavior remain separate |
| `levelscript_node_strings_native [--regenerate --write]` | Prove reviewed node UID prefixes, primitive sources and pooled-string setter transfers | `reports/game_data/levelscript_node_strings_native.json`; other fields and whole owners remain separate |
| `il2cpp.skill_cursor_target_set_context` | Current v2 target contract binds reviewed logical paths as observation-only filters using selected native declarations and MD5-verified VFS bytes; `--corpus-report` selects the outer audit summary for this scope. Historical v1 corpus/receipt replay remains separate | current context and binding under `reports/animestudio/`; no terminal or complete-corpus publication |
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
| `memorypack.{buff,buff_1b,lipsync}_corpus` | whole-family MemoryPack gates | `*_current_latest.{json,md}` |
| `npc_montage_native`, `memorypack.npc_montage`, `memorypack.npc_montage_corpus` | current native-gated sparse MontageNew; null/empty collections only; census `--export-root` selects StringPool pages and joins them to the authenticated VFS ledger | `npc_montage_current_latest.{json,md}`; positive lists remain unsupported |
| `memorypack.buff_*_receipt`, `memorypack.buff_*_child_corpus`, `buff_action_receipt_corpus`, `buff_create_action_root_corpus`, `buff_stacking_compact_corpus`, `buff_shared_nested_receipt_corpus` | per-route selected-native readers replayed on current source bytes; the Buff root admits only the compositions each docstring names | `buff_*_current_latest.json` |
| `memorypack.buff_damage_gradual_condition_receipt` | `--buff-report`, `--export-root`, `--source`, `--expected-input-set-sha256`, `--output`: join one selected gradual Buff source to current native and prior complete-report receipts, then verify the exact condition and whole-root EOF | caller's `--output` under `reports/` |
| `memorypack.buff_heal_check_tag_selected`, `memorypack.buff_heal_processor_zero` | `--input`, `--source`, `--audit-report`, `--buff-report`, `--output`: replay the selected positive heal modifier's native-audited condition and tag-zero processor; the root's `decode_selected_positive_heal_buff` composes them with its 30-field reader | caller's `--output` under `reports/` (selected diagnostics) |
| `memorypack.buff_selected_roots` | Shared source-bound positive-heal, BreakPassing event-map, attribute-plus-empty-condition/tag-ten and recursive sword damage root admission and canonical replay, consumed by `buff_corpus` and `jsondata_corpus`; the Buff gate's `--selected-native-audit` defaults to the existing current IL2CPP context audit without rerunning it | complete-family `selectedSourceRoots` cohorts and registry replay input pins; standalone selected diagnostics stay nonpublishable |
| `memorypack.buff_attribute_modifier`, `memorypack.buff_residual_census` | Shared native-gated AttributeModifierData reader; residual census authenticates the family/source receipt, excludes exact roots and ranks recorded shared-event refusals; `--replay-no-positive` replays ordinary roots, `--replay-shared-events` replays eligible event-map roots and ranks actual first child refusals | shared Buff root admission; `reports/game_data/buff_residual_census_latest.json`, never standalone family promotion |
| `memorypack.buff_event_maps`, `memorypack.buff_recursive_actions` and their control, ID/string, selector/geometry child owners | Distinct Ability/Buff event-map read orders and recursively named action/selector children under typed native joins; bounded list counts are independent of selected fixture names | shared root receipt through `buff_corpus` and canonical JsonData replay; unsupported nested unions refuse admission |
| `memorypack.buff_skill_stack_interrupt_actions`, `memorypack.buff_selector_distance_validator` | Named skill/ATB-gain/stack conditions, cooldown, mode switching, interrupts and Buff duration configuration; independent child extents and selected native joins gate composition | shared event-map and selector-list children through `buff_corpus`; stored operands do not establish live condition results or lifetime writes |
| `memorypack.buff_selector_validator_zero`, `memorypack.buff_selector_shared_children` | Current ExcludeOwner/MainCharacter/SkillCastId zero-member routes and mixed validator lists; typed parent extents and native inputs gate composition | `buff_corpus` recursive selector children; original component replay precedes whole-family/root admission, runtime predicates remain unresolved |
| `memorypack.buff_selector_validator_consumer`, `memorypack.buff_selector_validator_mutation_consumer`, `memorypack.buff_selector_validator_identity_consumer` | Named SkillCastId Data consumer claims, complete CFG/frame checks, conditional mutation arguments and cast-identity field/branch joins | `validate_current_native_contract(gameassembly=..., metadata=...)`; selected native inputs gate proof, while non-null action helper and patched sources, live branch outcomes, invocation and callee effects remain unresolved |
| `memorypack.buff_save_heal_value_action` | SaveHealValue common fields and two independently bounded nullable UTF-8 keys | Recursive action dispatcher; selected native source/setter/string gates and exact component spans precede complete-family/root admission |
| `memorypack.buff_channeling_action` | Channeling mixed inherited/direct/setter outputs, bounded sequence and target children, and raw Single interval bits | Recursive action dispatcher; independently gated child/source/route proofs and exact component spans precede complete-family/root admission |
| `memorypack.buff_vitals_actions`, `memorypack.buff_data_transfer_actions`, `memorypack.buff_probability_action`, `memorypack.buff_entity_count_action`, `memorypack.buff_notify_char_passive_ui_action`, `memorypack.buff_id_actions` | Original-span composition of vitals and entity-count conditions, skill-setting reads, battle signals, target Buff blackboards, stack storage, scalar calculations, attribute storage, probability, passive UI storage and cooldown actions; independently bounded targets, finders, providers and nullable lists | shared event-map children through `buff_corpus`; whole-root and canonical replay gates still apply |
| `memorypack.buff_cost_action`, `memorypack.buff_timed_marker_condition` | Named stored resource-cost and timed-marker parents with independent targets/providers; `named_native_records` authenticates explicit closed unmanaged source reads; `unmanaged_cursor_sources` checks the complete DWORD cursor-call profile and separate registered entry | shared event-map children through `buff_corpus`; stored operands do not establish live results; whole-root and canonical replay gates still apply |
| `memorypack.buff_super_armor_condition`, `memorypack.buff_debug_print_action` | Named armor comparison and debug-print storage; inline color requires an independent sixteen-byte source copy, cursor advance and runtime-field destination proof | shared event-map children through `buff_corpus`; comparison/log results remain unresolved |
| `memorypack.animation_curve`, `memorypack.buff_curve_actions` | Named AnimationCurve wrap words and seven Keyframe words proved by closed array type and independent source/cursor/destination programs; time-dilation, hurt-animation and hit-stop parents compose original-span children and explicit unmanaged tag reads | shared event-map children through `buff_corpus`; null/empty lists and curves remain distinct, evaluation and effects remain unresolved |
| `memorypack.buff_marker_mask_actions` | Named timed-marker creation and tag/object/physical-infliction/spell-infliction/target-equality conditions; independent Blackboard, target and query receipts, with explicit typed output-buffer transfer for the query | shared event-map children through `buff_corpus`; runtime copy extent is distinct from serialized grammar, marker lifetime and predicate results remain unresolved |
| `memorypack.buff_tag_sequence_actions`, `memorypack.buff_sequence`, `memorypack.buff_spawn_entity_action`, `memorypack.struct_output_sources` | AddTag and ForEach use independently typed tag elements and shared recursive sequences; SpawnAbilityEntity proves distinct raw12 source/registered entries and inline raw16 transfer before composing original-span children | shared event-map children through `buff_corpus`; null/list distinctions and receiver identity remain checked, tag attachment and entity execution remain unresolved |
| `memorypack.buff_camera_impulse_action`, `memorypack.value_wrapper_sources` | CameraImpulse independently joins impulse definitions, inline envelope fields, curves and targets; explicit inline raw12 cursor/copy and provider output32 transfers keep wire framing separate from runtime extent | shared event-map children through `buff_corpus`; curve evaluation, formatter selection and camera execution remain unresolved |
| `memorypack.buff_leaf_actions`, `memorypack.inherited_action_sources`, `memorypack.buff_spell_infliction_action` | Named leaves include MoveGait's max/min enums, TriggerSpellBurst's terminal DWORD, CheckDamageType's raw enum DWORD and independently sourced CheckSkillCastId/SkillAffix inherited operands with explicit buffered read/cursor/base-Data setter proof; the spell event composes TargetSettings and both enum operands | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, runtime condition evaluation, skill-affix effects, movement and spell/event execution remain unresolved |
| `memorypack.buff_target_mask_conditions` | CheckWeaponType and CheckEnemyRank keep their distinct target/mask order, independently join the TargetSettings wrapper's runtime instance, bind every reached nonnull child to ordered named receipts and reencode the complete action | recursive event-map and sequence children through `buff_corpus`; selected spans alone do not admit a root or establish target selection, mask interpretation or predicate results |
| `memorypack.buff_check_target_contains_action` | Named child/parent TargetSettings with separate typed source contexts and original recursive child spans | shared event-map child through `buff_corpus`; both nonnull settings require independent recursive target proof, while acquired targets and containment results remain unresolved |
| `memorypack.buff_merge_target_action` | Current seven-member MergeTarget layout, separately stored merge flag, proved UTF-8 key source and closed `List<TargetSettings>` with independently bounded recursive elements | shared event-map child through `buff_corpus`; historical tags/layouts are excluded, full-family and gained-root replay decide admission, and provider choice or merge/replacement execution remains unresolved |
| `memorypack.buff_move_to_source`, `memorypack.inherited_direct_action_sources` | Current MoveTo parent names, declared destinations and independent union route; explicit common-field direct stores, raw Vector3 transfer and LayerMask source profiles, with authenticated selected inputs and source closure | parent source evidence only; recursive Blackboard/curve/vector/target/SubSpeed/string spans, remaining owned operand flow, full action/root admission and movement effects remain separate obligations |
| `memorypack.buff_move_to_subspeed_source`, `memorypack.direct_data_sources` | Current SubSpeed generated order and conditional normal operand flow through each owned Data store, final wrapper dereference, buffered DWORD cursor and following reference-slot helper calls; explicit native and source closure gates | child source evidence only; typed MethodSpec does not identify a physical generic callee, post-store effects/provider/error behavior and full child/action/root admission remain unresolved |
| `memorypack.buff_move_to_setter_transfers`, `memorypack.selected_wrapper_setter_sources` | All selected MoveTo caller/getter/setter transfers, distinct primitive/unmanaged cursor sources, shared physical reference return and disabled post-store helper joins; run `python -m scripts.game_data.memorypack.buff_move_to_setter_transfers --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_setter_transfers_validation_latest.json` | conditional native evidence only; preserves the report on native-input drift; physical generic identity, enabled barriers, lifecycle/provider effects and recursive action/root admission remain open |
| `memorypack.buff_move_to_lifecycle`, `memorypack.buffered_wrapper_lifecycle_sources` | MoveTo/SubSpeed buffered headers, null/new/reused wrapper returns, typed construction transfers and warm/cold cached getter paths; run `python -m scripts.game_data.memorypack.buff_move_to_lifecycle --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_lifecycle_validation_latest.json` | conditional native evidence only; preserves the report on native-input drift; nested defaults and ready preparation use the following owner; allocator/factory effects, initialization slow paths, provider choice and recursive action/root admission remain open |
| `memorypack.buff_move_to_runtime_defaults`, `memorypack.runtime_constructor_sources` | Complete selected MoveTo/SubSpeed and nested constructor stores, closed Float32 Blackboard defaults, opaque curve factory arguments and ready `OnDeserialized` cache paths; run `python -m scripts.game_data.memorypack.buff_move_to_runtime_defaults --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_runtime_defaults_validation_latest.json` | conditional native evidence only; before/after selected native, Unity, dependency and source gates; preserves the report on native-input drift; allocator/engine effects, slow paths, final accumulated state, provider choice and recursive action/root admission remain open |
| `memorypack.buff_move_to_formatter_routes`, `memorypack.generated_formatter_routes` | Current generated wrapper initializer, first Register argument path, ready formatter constructor and full Deserialize caller restoration/tail into the existing MoveTo/SubSpeed readers; run `python -m scripts.game_data.memorypack.buff_move_to_formatter_routes --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_formatter_routes_validation_latest.json` | conditional native evidence only; selected native/Unity/dependency/source gates and report preservation on drift; remaining registrations, dictionary effects, runtime-original adapter/provider selection and recursive action/root admission remain open |
| `memorypack.buff_move_to_original_adapters`, `memorypack.original_adapter_sources` | Current eager original/wrapper adapter blocks, retained closed constructor contexts, adapter callback declarations, parent SubSpeed ReadValue type-key joins and complete repeated interface/getter forwarding; run `python -m scripts.game_data.memorypack.buff_move_to_original_adapters --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_original_adapters_validation_latest.json` | conditional static/native evidence only; selected native/Unity/dependency/source gates and report preservation on drift; actual initializer/provider/vtable selection, dictionary and allocation effects, accumulated state and recursive action/root admission remain open |
| `memorypack.buff_move_to_subspeed` | Complete null/member-five stored codec combining the current source order, full selected wrapper returns, default adapter route and named scalar/string/curve children; run `python -m scripts.game_data.memorypack.buff_move_to_subspeed --gameassembly <DLL> --metadata <DAT> --report reports/game_data/buff_move_to_subspeed_composition_validation_latest.json` | source-bound stored schema with bit-exact named reencoding; explicit native/Unity/source gates preserve the report on drift; compatible initialized contexts and default formatter binding remain conditions, while actual callback cursor/provider/state, other member variants and enclosing action/root admission remain open |
| `memorypack.buff_move_to`, `memorypack.stored_plan_values` | Complete source-bound MoveTo parent and bit-preserving named recursive values; `python -m scripts.game_data.memorypack.buff_move_to --gameassembly <DLL> --metadata <DAT> --children-cache <CACHE> --children-cache-receipt <RECEIPT> --report reports/game_data/buff_move_to_composition_validation_latest.json`; recursive action composition also validates it from fresh child returns | metadata value trees remain structural until joined to independently proved named child boundaries and wire values; full roots require the current `buff_corpus` gate and original-root replay; actual provider/cursor/state and runtime effects remain unresolved |
| `memorypack.buff_teleport_action`, `memorypack.source_bound_stored_tree` | Current Teleport parent with independent sequence/scalar/target proofs and exact named-tree coverage; consumed by `buff_recursive_actions` under `buff_corpus` | exact stored reencoding preserves raw bits and null/empty distinctions; the fresh full-family gate and original-root replay own complete roots; target selection and teleport effects remain unresolved |
| `il2cpp.vector3_squared_magnitude`, `il2cpp.single_squared_limit` | Complete static Vector3 Single square/sum leaf and exact field-load/product/COMISS/JA windows; callers authenticate the selected image and independently bind receiver, field and input buffer | named layout and byte programs remain conditional on valid buffers/call frames and normal floating completion; actual values, input ownership and effects remain separate |
| `il2cpp.vector3_distance_flow` | Complete navigation argument setup, subtraction-to-square buffer copies and saved 8+4-byte success output with explicit frame offsets and call targets | callers authenticate the selected image, declarations and complete arithmetic callees; navigation writes, failure paths and runtime effects remain separate |
| `il2cpp.vector3_zero_value`, `il2cpp.vector3_failure_flow`, `il2cpp.win64_rbp_frame` | Selected complete Vector3 zero getter, 8+4-byte failure output and matched entry/return frame programs | callers authenticate the selected image and join exact branch/callee targets; valid memory, saved-slot integrity and normal ABI calls remain conditions |
| `il2cpp.unwind_chains` | Declared AMD64 PE exception-table framing and complete chained-parent membership, including nested and noncontiguous ranges | selected-image callers own freshness gates; rejects missing/mismatched parents, cycles and frame-byte drift; unwind operation/handler semantics and managed execution remain separate |
| `il2cpp.nullable_vector3_programs`, `il2cpp.nullable_vector3_path_return` | Complete canonical Nullable<Vector3> interface programs and ordinary tagged path-return program, with exact count width, fields, branches, frame and buffer copies | selected-image callers bind exact closed MethodSpecs and named declarations; total closed size/private fields, adjustors, array header, cold paths, navigation writes and actual execution remain separate |
| `il2cpp.nullable_vector3_distance_path`, `il2cpp.vector3_array_element`, `il2cpp.vector3_distance_program` | Complete ordinary distance continuation, low-DWORD array bound/full-index copy and packed distance arithmetic, including direct threshold and tagged fallback returns | callers authenticate owned bytes, hot frame, typed fields and helper entries; count dispatch, stable path, full array header, opaque helper/IFix effects and actual execution remain separate |
| `il2cpp.null_safe_count_programs`, `il2cpp.lazy_reference_cache` | Complete null-zero/count-delegation call and tail-call programs, and reference-cache hit/miss with typed producer/slot joins | callers authenticate selected owned bytes and static declarations; matching arguments do not equate entry identities, and runtime context, actual count, producer/notification effects and external writes remain separate |
| `il2cpp.array_collection_count` | Complete split array Count and leaf Rank programs, shared QWORD length dereference, low-DWORD product and exact fragment transfers | callers authenticate owned ranges and named declarations; rank-one count-coordinate equality is conditional, while actual interface selection, dimension/error helpers and full array allocation remain separate |
| `il2cpp.contract_read_scope` | CPython audit observer for JSON contract pins frozen before fresh consumer imports; verifies actual reads, latches caught input errors and rechecks the consumed set at completion | unknown, writable, linked and changed inputs fail closed even when consumers catch their exceptions; probe required; native/Python/VFS gates remain independent; unopened files are not proved universally unused |
| `memorypack.buff_blackboard_double_key`, `memorypack.inline_utf8_sources` | Independently gated BlackboardDouble first-key framing and actual ReadUtf8 source; buffered length/cursor/bounds and null/empty/positive branches, strict original UTF-8 decoding and exact key reencoding | original key spans only; closed generic Data destination, replacement/refill behavior, evaluated lookups and complete child/action/root admission remain unresolved |
| `memorypack.buff_blackboard_double_data`, `memorypack.closed_scalar_wrapper_fields` | Closed BlackboardDouble VAR ownership and actual named setter cells joined to key, normalized Boolean and raw Float32 sources; original whole-child reencoding retains the wire selector byte | conditional coherent-reference normal field flow only; generic definition offsets are not instance layout, constructor/provider/consumer/error behavior and complete action/root admission remain unresolved |
| `memorypack.buff_blackboard_double_consumers`, `memorypack.closed_scalar_consumers` | Current concrete key getter, lower-lane Single-to-Double cast and guarded direct/keyed TryGetValueInternal programs through return; actual lookup overload/arguments and eight-byte output copy join independently proved scalar cells | conditional selected consumer flow only; live instance/field-state correspondence, CPU outcomes, lookup body/results, public GetValue/provider/error behavior and complete action/root admission remain unresolved |
| `memorypack.buff_blackboard_key_comparison`, `il2cpp.utf16_ascii_comparison` | Complete current managed 16-bit key-comparison CFG, ASCII A-Z folding, signed length/loop and both Boolean returns; exact lookup-owned callback and false Burst-getter edge | readable stable spans and normal completion only; callback input origins, Burst enabled path, whole lookup/results, actual execution and action/root admission remain unresolved |
| `memorypack.buff_blackboard_pair_list`, `memorypack.blackboard_pair_cells` | Current nongeneric DataPair cells, type-size/boxed-value correspondence, numeric/string/copy constructors with actual disabled-barrier volatile preservation, three numeric-predicate returns and registered closed List value-copy success path | conditional runtime value flow only; managed references and opaque padding are not a wire schema; enabled barrier/dispatch/failure effects, actual receivers, whole lookup/public GetValue/provider and action/root admission remain unresolved |
| `memorypack.buff_blackboard_number_lookup`, `memorypack.blackboard_number_lookup` | Complete selected managed _TryGetNumber CFG and arbitrary loop; joins proved pair/list and key comparison, original key/output aliases, rejection backedges and eight-byte found/zero returns | stable coherent inputs, normal dispatch guards and false Burst getter required; actual receiver/result, other dispatch/error effects, concrete consumer/public GetValue/provider composition and action/root admission remain unresolved |
| `memorypack.buff_blackboard_double_lookup`, `memorypack.closed_scalar_lookup` | Compose the current keyed TryGetValueInternal with the complete selected managed lookup: same actual callee/build, argument and output aliases, derived stack separation, restored caller state and preserved Boolean; original keyed fields join the first-numeric-match or false/zero relation | conditional stable fields/inputs, normal guards, false Burst getter and isolated returning frames; actual instance/list/found value, public GetValue/default/provider, other effects and whole action/root admission remain unresolved |
| `memorypack.buff_blackboard_double_default`, `memorypack.blackboard_double_default` | Complete selected GetValueOrDefaultInternal → GetDoubleOrDefault → TryGetDouble programs: inlined scalar direct/keyed flow, saved Double default, AL-based output/default choice, argument forwarding and full returns; null Board edge authenticates helper CALL/INT3 | false patch checks, normal guards/managed lookup, coherent fields and isolated returning frames; actual default/list/value, exception effects, public GetValue virtual/context/provider and full action/root admission remain unresolved |
| `memorypack.buff_blackboard_null_getvalue`, `memorypack.blackboard_null_getvalue` | Complete initialized null-Blackboard GetValue/direct/cast-fallback programs, static closed MethodSpec registration, concrete metadata slot, restored tail frames and public Double return; keyed selector logs then returns zero | explicit native/metadata paths and before/after native/Unity/dependency/source gates; initialized flags, false patch checks, actual class function equal to concrete cast and ordinary helper returns remain conditions; nonnull public paths, actual runtime/context/provider/effects and full roots remain unresolved |
| `memorypack.buff_blackboard_nonnull_getvalue`, `memorypack.blackboard_nonnull_getvalue` | Complete initialized nonnull public/matching-Try returns: direct conversion or managed keyed lookup, exact output/AL forwarding, home-space temporary and frame separation, found return or actual dump/logger arguments then zero; stored string/string logger context and physical object/object registration stay distinct | explicit native/metadata paths and before/after native/Unity/dependency/source gates; matching concrete Try function, normal guards, coherent fields/frames, ordinary logger with compatible context and completed SIMD remain conditions; unequal virtual selection, actual context/runtime/provider/effects and complete recursive roots remain unresolved |
| `memorypack.buff_animation_sequence_actions` | PlayAnimation composes independently decoded original UTF-8 strings, raw float bits and its own ending sequence; JumpTo composes its distinct condition sequence followed by the required Int32 destination frame; current named source/destination and dispatcher proofs gate both | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, animation, callback results and frame jumps remain unresolved |
| `memorypack.buff_direct_target_actions`, `memorypack.buff_custom_ability_event_condition` | Named head-bar/poise-break target actions and custom event storage; each new parent has independent source/destination and dispatcher joins, original target/BlackboardString children, null distinctions and required fields; the event's saved parameter key additionally has a current UTF-8 source proof | shared event-map children through `buff_corpus`; full-root and canonical replay gates apply, selected targets, recovery, event matching and parameter capture remain unresolved |
| `memorypack.buff_keyword_actions` | Independently named vulnerable, shelter, slow, speedup, weak, enhanced and infliction storage; separate KeywordEnhanceEdit elements and bounded raw-string lists; each parent retains its own required list suffix and original-span provider/target receipts | shared event-map children through `buff_corpus`; null/list distinctions remain explicit, edits and infliction effects remain unresolved |
| `memorypack.buff_check_consume_layer`, `memorypack.buff_pick_target_action` | CheckConsumeBuffLayer composes its named comparison enum, independently owned BlackboardInt and required final source-string key; `validate_integer_native_contract` checks the child separately without a PickTarget/TargetSettings gate | Shared event-map child; original child/parent spans and full-family/root gates apply, evaluated comparison, consumption, lookup and key writes remain unresolved |
| `memorypack.buff_bind_bounty_action` | Current BindBountyEnemy inherited prefix and independently bounded BlackboardString bountyKey, preserving raw child bytes and short/extended tag spans | Shared event-map child; full-family/root gates apply, key evaluation, bounty/enemy ownership and binding effects remain unresolved |
| `memorypack.buff_archery_chip_action` | Current eighteen-member TyphoeaArcheryChipDataAction, independently owned nullable string keys and raw save flags with required suffix reservations | Shared event-map child; full-family/root gates apply, key lookup and projectile/bounce/split/trajectory/affix effects remain unresolved |
| `memorypack.buff_launch_projectile_action` | Complete named projectile storage, four explicit inline Vector3 programs, independently named preset-point elements and shared AssignPair children | shared event-map children through `buff_corpus`; original spans and required tails gate composition, emission and trajectories remain unresolved |
| `memorypack.buff_ignite_text_action` | Complete named text action storage; independent direct/registered raw Vector2 reads, cursor helper, full return argument and typed getter/setter field transfer | shared event-map children through `buff_corpus`; original target spans and required final payload remain checked, displayed text and gameplay effects remain unresolved |
| `memorypack.buff_global_creation_action`, `memorypack.buff_switch_action` | GlobalBuffInput/GlobalBuffId with assignments and an explicit addressed string reference proof; Switch Option with independently typed recursive sequence and BlackboardDouble | shared event-map children through `buff_corpus`; original child ranges, null/list distinctions and bounded recursion remain checked, live creation, lifetime and branch effects remain unresolved |
| `memorypack.buff_finish_global_action`, `il2cpp.formatter_composition` | FinishGlobalBuff parent with independently owned Blackboard scalar and reviewed conditional original-value ID list; exact source-list registration, generic/interface identities, buffered count/null/conversion programs and required final flag | shared event-map child through `buff_corpus`; original action spans and complete root/canonical gates decide admission; live provider/IFix selection, evaluated IDs/count and finishing effects remain unresolved |
| `memorypack.buff_blow_off_action`, `memorypack.inherited_setter_output_sources` | BlowOffAction common/derived setter flows, six independent scalar children, recursive targets and direction | Original component receipts precede complete-family/root admission; evaluated movement and effects remain unresolved |
| `memorypack.buff_self_rotate_action`, `memorypack.getter_direct_action_sources` | SelfRotateAction common direct stores, cached getter flows and interleaved raw Single store; independent UTF8, direction and recursive target children | Exact original component/dispatcher receipts precede complete-family/root admission; rotation and runtime effects remain unresolved |
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
| `memorypack.buff_formatter_dispatch_fallback`, `il2cpp.{dispatch_fallback_control,integer_source_operands}` | Actual prepare-entry load/tail transfer and complete stored-byte guards; resolver receiver/context/UInt16 forwarding, first/alternate result returns and restored frames | library validation only; selected native/source gates fail closed; opaque child effects/search, runtime class/interface/MethodInfo, cache/callback and root admission remain open |
| `memorypack.buff_formatter_resolver_scan`, `il2cpp.{resolver_scan_control,integer_tag_dispatch}` | Actual resolver child and preparation bridge; complete owned code/table/padding partition, signed-byte and unsigned word/DWORD scan guards, bounded two-level table targets and both complete index leaves with preserved caller scan registers | library validation only; selected native/source gates fail closed; compatible stable storage and normal opaque conversion/relation returns remain conditions; live header/base identity/bounds, named runtime targets/effects, cache/callback and root admission remain open |
| `memorypack.buff_formatter_carrier_conversion`, `il2cpp.{carrier_conversion_control,integer_decrement}` | Actual carrier call/flag joined to complete owned tag/table/global-read control, cached return/null fallback, original/payload/recursive tail arguments and restored frames; checked global return cells joined to caller normalization loads | library validation only; selected native/source gates fail closed; stable compatible storage/values and normal child returns remain conditions; named type/class, initialization, recursion termination, child allocation/cache effects, opaque relation and callback/root admission remain open |
| `memorypack.buff_class_name_lookup`, `il2cpp.class_name_lookup_control` | Complete selected lookup/cache/resolver/constructor controls; zero key, namespace/name byte comparisons, valid record-to-index arithmetic, raw type copies and later copied-type address forwarding | library validation only; explicit native inputs gate before/after; stable storage and helper returns remain conditions; live named class/cache identity, later copy preservation, concrete enum sharing and root admission remain open |
| `memorypack.buff_copied_type_readonly`, `il2cpp.type_comparer_control` | Closed search/comparison family, complete code/table/padding partition and count-leaf entry; bounded stack-only writes, selected kind/flag/QWORD comparisons and a nonidentical zero-result witness | library validation only; explicit native gates before/after; finite normal calls and disjoint recursive stacks condition input-copy preservation; other constructor effects, termination, live identity/provider and root admission remain open |
| `memorypack.buff_enum_list_control`, `memorypack.enum_list_sources` | Independent Int32Enum registrations and selected buffered header, existing/null list, fresh-pointer-matched scalar bridge and spare-capacity DWORD insertion | library validation only; explicit native gates before/after; stable storage, available buffer/capacity and normal helper returns remain conditions; header count guard does not guarantee element bytes; concrete DamageType sharing/provider and parent/root admission remain open |
| `memorypack.buff_enum_underlying`, `il2cpp.enum_underlying_control`, `il2cpp.enum_underlying_instructions` | Complete enum projection, named enum/element/type API entries, flag-only memory TEST and record-pointer conversion | library validation only; selected native gates before/after; repeated class results remain fresh; on-disk DamageType stores an index; runtime initialization and live record-pointer identity remain open, along with concrete sharing/provider and parent/root admission |
| `memorypack.buff_type_data_initialization`, `il2cpp.type_data_initialization_control`, `il2cpp.type_data_initialization_instructions` | Complete registration publication, actual initialization calls, guarded type dispatch and signed-index QWORD fixups | library validation only; selected native gates before/after; index-to-record-pointer join is conditional on the loaded source and stable disjoint storage; other negative indices, repeat initialization, live class/sharing/provider and parent/root admission remain open |
| `memorypack.buff_class_enum_fields`, `il2cpp.class_enum_fields_control` | Complete constructor/type-helper control, metadata enum-bit writes, element/cast result stores and selected Int32 class-cell producer | library validation only; selected native gates before/after; preserves distinct record/allocation origins under normal ABI; no zero allocation, nonnull/named primitive class, alias stability, concrete sharing/provider or parent/root result is inferred |
| `memorypack.buff_name_cache_key_record`, `il2cpp.name_cache_key_record_control` | Complete construction/growth controls and selected same-node header/string/record copies | library validation only; selected native and source gates; actual migration/swap calls located; unused node padding, duplicate/history, growth preservation, probe termination, named class identity and parent/root admission remain separate |
| `memorypack.buff_name_cache_migration_swap`, `il2cpp.name_cache_migration_swap_control` | Complete migration child controls, closed config exchange/R11 preservation, metadata/node-pointer exchange and selected migration field copies | library validation only; selected native/source gates; arbitrary-bit symbolic replay under stable disjoint storage; full enumeration/free markers, predicates, duplicates, termination, named class identity and positive parent/root admission remain open |
| `memorypack.buff_name_cache_marker_iterator`, `il2cpp.name_cache_marker_iterator_control` | Free-descriptor node initialization, AL-only header/string predicate, complete iterator filters and actual argument/frame joins | library validation only; selected native/source gates; finite aligned range and stable CString/node/iterator conditions; next filters its input cursor and migration advances first; allocator success, complete migration/probes/history, named class and positive parent/root admission remain open |
| `memorypack.buff_name_cache_destination_migration`, `il2cpp.name_cache_destination_migration_control` | Complete migration/hash control, triangular probe permutation and conditional node-field multiset preservation | library validation only; native/source gates; nonzero power-of-two capacity, enough slots and stable disjoint valid post-allocation storage are explicit conditions; capacity may wrap to zero; live allocation/history, class identity and positive parent/root admission remain open |
| `memorypack.buff_name_cache_constructor`, `il2cpp.name_cache_constructor_control` | Complete constructor/base-child defaults, exact binary32 thresholds and conditional free-node initialization | library validation only; selected native/source gates; valid disjoint storage and normal completion; allocator validity and noninterference are explicit postconditions; future population capacity, duplicate history, named class and positive parent/root admission remain open |
| `memorypack.buff_name_cache_allocator`, `il2cpp.name_cache_allocator_control` | Allocator tail/wrapper and retry/error helper control, static HeapAlloc import and conditional null/success returns | library validation only; selected native/source gates; live heap/IAT identity and unknown getter/dispatcher/context effects remain open; normal wrapper completion does not guarantee allocation, retry termination or cache isolation |
| `memorypack.buff_name_cache_handler_getter`, `il2cpp.name_cache_handler_getter_control`, `il2cpp.pe_load_config` | Handler-word XOR/rotate return, SecurityCookie/CFG storage declaration joins and conditional file-default dispatch tails | library validation only; selected native/source gates; guard effects, same-epoch reads, live CFG selection/callback identity and cache isolation remain open; on-disk pointer declarations and default words do not prove runtime bindings |
| `memorypack.buff_name_cache_handler_guard`, `il2cpp.name_cache_handler_guard_control` | Signed-index shared storage and closed static Enter/LeaveCriticalSection tails | selected native/source gates; initialized objects, live bindings, mutex effects and complete writer protection remain open |
| `memorypack.buff_name_cache_handler_state`, `il2cpp.name_cache_handler_lifecycle_control`, `il2cpp.name_cache_handler_setter_control` | Conditional initialized-prefix rollback and handler replacement/previous-word return | library validation only; zero initial counter, valid objects and normal API completion are conditions; AL-only results, invocation/order and surviving global state remain separate |
| `memorypack.buff_name_cache_handler_direct_init`, `il2cpp.name_cache_handler_direct_init_control`, `il2cpp.native_call_references` | Whole saved-cookie caller and actual direct handler store; raw direct-call candidate scan | selected native/source gates; sibling effects, enclosing locks and startup invocation remain open; candidate scanning is not a complete call graph |
| `memorypack.buff_name_cache_handler_sibling_stores`, `il2cpp.name_cache_handler_sibling_stores_control` | All closed direct children, exact disjoint global stores and conditional caller return state | selected native/source gates; valid storage and absent concurrent writes are conditions; invocation/order, enclosing locks and complete writer coverage remain open |
| `memorypack.buff_refrain_obtain_usp` | Current USP parent fields with independent GameplayTagList/TargetSettings receipts, named-tree bindings and exact reencoding | `buff_recursive_actions` integrates it; selected native/source gates, complete-family and thirty-field/source-ID/EOF root admission remain distinct from actual USP effects |
| `memorypack.buff_camera_list_constructor` | Concrete camera list registrations and complete shared constructor control | Explicit selected native gates; positive list grammar, provider choice and camera effects remain unresolved |
| `memorypack.buff_shared_reference_list`, `il2cpp.reference_list_control` | Complete shared Object ListFormatter control/frame checks, DWORD count/QWORD reference projections and count/null/provider/callback-loop routing | Library validation only; selected native gates reject missing or changed builds, concrete collection grammar, negative-count helper parity, callback effects, termination and parent/root admission remain unresolved |
| `memorypack.buff_camera_base_constructor` | Inherited List<T> constructor/parent argument identity and folded registered RET0 entry | Explicit selected native gates; actual runtime slot population/cold target equality and positive camera lists remain unresolved |
| `memorypack.buff_camera_context_slot_publication` | Complete context initializer graph, declaration-to-slot strides and method-slot argument/return publication | Selected native/source gates; compatible range/allocation/helper conditions, live slot values and positive camera lists remain separate |
| `memorypack.buff_camera_method_spec_descriptor` | Complete MethodSpec descriptor index/control and inherited-constructor class/method argument join | Selected native/source gates; input bounds, fresh cache return and helper effects remain explicit conditions |
| `memorypack.buff_camera_descriptor_composition` | Complete descriptor composition graph, joined entry origins and three QWORD stores | Selected native/source gates; cache key equality, allocation and later pointee effects remain open |
| `memorypack.buff_camera_descriptor_cache_lookup` | Complete triple-key probe, zero-flag equality and caller key/output frame join | Selected native/source gates; delegated empty output, volatile helper effects and insertion remain open |
| `memorypack.buff_camera_descriptor_cache_helpers` | Closed comparator effects, complete iterator/empty-output control and conditional end stores | Selected native/source gates; physical leaf extent, coherent globals, insertion and runtime selection remain separate |
| `memorypack.buff_camera_descriptor_cache_insertion` | Complete insertion graph, new/existing entry writes and table/current/end/inserted output | Selected native/source gates; opaque growth effects, FP policy, pointee stability and runtime selection remain separate |
| `memorypack.buff_camera_descriptor_cache_rebuild` | Complete guarded halving request and selected bidirectional publication fields | Selected native/source gates; helper success, numeric FP policy, whole-object swap and atomic visibility remain unproved |
| `memorypack.buff_camera_descriptor_temporary_cleanup` | Complete temporary-pointer handoff, release thunk/body and exact declared import cells | Selected native/source gates; pointer/heap ownership, live IAT binding, error helpers and release success remain unproved |
| `memorypack.buff_formatter_relation_control`, `il2cpp.{relation_control,integer_effects}` | Complete owned relation code/table/padding partition, original branch/call boundaries, guarded indexed transfers, low-byte returns and enumerated physical memory updates; actual resolver/carrier calls joined | library validation only; selected native/source gates fail closed; static possible paths do not establish typed relation/lock/cache meaning, indirect callee values, child effects, recursion termination, live callbacks or list/root admission |
| `memorypack.buff_formatter_relation_import_control`, `il2cpp.{pe_imports,relation_import_control}` | Actual terminated PE descriptor/name/IAT ownership and Baselib declarations; complete selected caller acquire/release arguments, DWORD counter/retry control and finite CFG constant flow | library validation only; selected native/source gates fail closed; normal compatible returns are conditional, the post-child slot pointer is fresh, and loaded-library identity, imported/child effects, initialization, termination and callback/list/root admission remain open |
| `memorypack.buff_formatter_baselib`, `il2cpp.{pe_exports,baselib_semaphore_control}` | Actual caller names joined through selected Baselib export names/ordinals/EAT, named kernel imports and complete primary/chained Acquire/Release/ThreadId programs | library validation only; GameAssembly/metadata/UnityPlayer/explicit Baselib and source gates fail closed before/after proof; DWORD result, error tails and adjusted release retry are conditional; live API identity, initialization, observed effects, finite wait/retry, requested total and callback/list/root admission remain open |
| `memorypack.buff_formatter_context_setup`, `il2cpp.{context_setup_control,integer_byte_operations}` | Actual context caller joins, complete owned CFG/store inventories, first byte-count/array/flag program and finite incoming-address provenance through partial-register writes and saved home cells | library validation only; selected native/source gates fail closed; compatible stable/disjoint storage and normal Win64 calls remain conditions; second complete typed field flow, pointed-slot mutations, allocation/copy effects, runtime callback/cursor and list/root admission remain open |
| `memorypack.buff_formatter_context_allocation`, `il2cpp.{context_allocation_control,integer_context_memory}` | Actual context byte-count/stride call joined to complete owned reservation/refill/node control, explicit writes and restored clear-tail arguments; bounded size arithmetic for this caller | library validation only; selected native/source gates fail closed; compatible stable storage and normal ABI returns remain conditions; live allocator/protocol/capacity, child results/effects, pointed slots and callback/list/root admission remain open |
| `memorypack.buff_formatter_clear_tail`, `il2cpp.{byte_fill_control,fill_instructions,fill_geometry}` | Complete fill/REP control, guarded tables, scalar/SSE/AVX values, affine byte ranges for every loop count, normal returned cursor and actual context array-field join | library validation only; selected native/source gates fail closed; writable storage, CPU/DF/stack, nonwrapping endpoints and noninterference remain conditions; live allocator/capacity, actual execution, return visibility and callback/list/root admission remain open |
| `memorypack.buff_formatter_class_ancestry`, `il2cpp.class_ancestry_control` | Selected GameAssembly names/ordinals/EAT joined to closed class field getters and complete has-parent control; actual first-context call and parent/depth/array/ready-field joins | library validation only; selected native/source gates fail closed; coherent valid storage and normal ABI returns are conditional; live receiver/formatter identity, initialization/synchronization, slot contents, ancestry capacity and callback/list/root admission remain open |
| `memorypack.buff_formatter_incoming_address`, `il2cpp.{initializer_control,initializer_instructions}` | Actual context/helper join, complete owned CFG and explicit stores, vector/byte/locked forms, saved-home frame geometry and finite input-register origins | library validation only; selected native/source gates fail closed; normal ABI calls and compatible stable/disjoint storage remain conditions; known call register values do not prove callee reads, pointed-slot preservation, typed class semantics, initialization/capacity, termination or callback/list/root admission |
| `memorypack.buff_formatter_class_fields`, `il2cpp.{class_field_control,integer_byte_shifts}` | Actual named type-flags/blittable/has-references and field-iterator consumers, complete preparation bridge/recursive control, shared input-helper callee and named bit replacement | library validation only; selected native/source gates fail closed; fresh field/context reloads and unknown aliases/child writes retain their boundaries; live class/formatter identity, field construction/capacity, synchronization, termination and callback/list/root admission remain open |
| `memorypack.buff_formatter_field_construction`, `il2cpp.field_construction_control` | Named field record getters, complete generic preparation child and inline allocation/record stores; actual setup call, closed receiver wrapper and shared-clear value/return join | library validation only; selected native/source gates fail closed; receiver count coherence, trailing DWORD meaning, ordinary/auxiliary construction, child alias/slot effects, type substitution, capacity and runtime/root admission remain open |
| `memorypack.buff_formatter_field_setup`, `il2cpp.{field_setup_control,field_setup_instructions,scalar_conversions}` | Complete ordinary/auxiliary owned CFG, explicit stores and normal frames; actual sibling/allocator joins and selected count/home/reference/early-ready projections | library validation only; native/source drift fails closed; other typed effects, fresh count coherence, pointed-slot effects, capacity, conversion outcomes and runtime/root admission remain open |
| `memorypack.buff_formatter_class_creation`, `il2cpp.{class_creation_control,class_creation_instructions}` | Complete metadata-record creation candidate control/stores/normal frame; current named count words, source-address and allocation/count-copy/result-return projections | library validation requires explicit GameAssembly and metadata paths; three native/source gates fail closed; live table/class/cache/preparation identity, bounds, later count coherence, child/alias effects and capacity/runtime/root admission remain open |
| `memorypack.buff_formatter_generic_creation`, `il2cpp.{generic_creation_control,generic_creation_instructions}` | Complete generic creation code/table partition, guarded image-RVA targets, stores/frames and register origins across the possible graph; actual getter/allocator, fresh count copy, incoming receiver link, cache exchange/reload and return projections | library validation requires explicit GameAssembly and metadata paths; three native/source gates fail closed; cached/null paths bypass creation, exchange overwrites the saved pointer and fresh reload equality is open; live preparation/count coherence, child aliases, synchronization/capacity, recursion and runtime/root admission remain open |
| `memorypack.buff_formatter_receiver_resolution`, `il2cpp.{receiver_resolution_control,record_index_geometry}` | Closed nullable/pointer-index leaf programs, complete owned indexed-cache resolver control/stores/frames, all-selected-record reciprocal bound and actual metadata-constructor/result-store/return joins | library validation requires explicit GameAssembly and metadata paths; native/source and parent provenance gates fail closed; leaf unwind ownership is not inferred, and live header/base/class identity, cache/count-view equality, index bounds, aliases and synchronization/runtime/root admission remain open |
| `memorypack.buff_formatter_metadata_initialization`, `il2cpp.{metadata_initialization_control,metadata_initialization_instructions,metadata_cache_geometry}` | Complete owned initializer control/stores/frames, unsigned full-product boundaries, actual loader-result/header/base and allocator-result/resolver-cache joins, conditional current metadata section-size quotient | library validation requires explicit GameAssembly and metadata paths; parent/current metadata and before/after native/source gates fail closed; loaded-file identity, allocator target/outcome, capacity, global stability, child aliases and runtime/root admission remain open |
| `memorypack.buff_formatter_metadata_loader`, `il2cpp.metadata_loader_control` | Complete owned loader/path-helper control/stores/frames, exact literal descriptors and physical argument/result guards, close/error import declarations, closed mapping/default-allocator transfers | explicit GameAssembly/metadata validation and actual initializer/allocator-cell provenance fail closed; no transfer ownership inference; final path, child reserve/append/open/map effects, live bindings/file identity, allocation outcome/capacity and runtime/root admission remain open |
| `memorypack.buff_formatter_metadata_mapping`, `il2cpp.metadata_mapping_control` | Actual loader tail target's complete owned control/stores/frames, child argument and registration payload joins, mutable-slot subtraction/fresh-return source, release-counter/import declaration program | explicit GameAssembly/metadata paths and actual parent/native/source gates fail closed; original view-result equality, slot noninterference, pointer/file identity, live bindings, synchronization, retry termination and runtime/root admission remain open |
| `il2cpp.native_cell_references` | Overlapping selected RIP-relative QWORD MOV/LEA/immediate-store byte candidates in the supplied image's text section | library discovery only; no instruction ownership or complete writer enumeration; other widths, aliases and child writers remain open |
| `memorypack.buff_condition_context_adapter`, `il2cpp.{accumulator_immediate_instructions,context_adapter_control,class_selector_source,context_fallback_control}` | Complete adapter/fallback programs, anonymous metadata selector copy, five named Context fields/getters and stored IActionEnvironment get_context slot | library validation requires explicit GameAssembly/metadata; native/Unity/source drift fails closed; live class/interface/pair identity, child effects/termination, pair capacity and whole-condition/root admission remain open |
| `memorypack.buff_condition_context_dispatch`, `il2cpp.{class_dispatch_sources,context_dispatch_joins}` | Allocated self QWORD, named interface-offset count copy, static getter pairs within requested allocation geometry, and actual existing prepare/resolver/search program joins | explicit GameAssembly/metadata and native/Unity/source gates; fresh resolver class remains distinct from the outer saved class, external child effects/termination, runtime array/pair identity and actual allocator capacity remain open |
| `memorypack.buff_context_publication`, `il2cpp.context_publication_sources` | Complete second preparation field/argument program: both interface-array writers, ordinary/linked method pairs, guarded selector repair joined to the adapter read, special flag replacement and incoming-address handoffs | explicit native/metadata/Unity/source gates; stored tables and full parent CFGs are authenticated; lookup/inflation/special child identities/effects/termination, byref contents, recursion, live storage/capacity/visibility and condition execution remain open |
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
| `memorypack.buff_selector_point_finder` | Named PointFinder position/rotation offset fields, each with independent Vector3/scalar children; current selector route and original direct parent spans gate composition | selector children through `buff_corpus`; full family/root replay still gates root coverage, evaluated offsets and selected points remain unresolved |
| `memorypack.buff_continuous_find_target`, `memorypack.direct_float_sources` | Nineteen-member continuous target action, explicit inherited direct stores and terminal Single/getter/field transfer; direction, selector and source strings compose independently | recursive actions through `buff_corpus`; original component spans precede full family/root acceptance, interval evaluation and targeting effects remain unresolved |
| `memorypack.buff_check_distance_condition`, `memorypack.buff_selector_shape_finder`, `memorypack.buff_collider_shape` | CheckDistance composes two separate TargetSettings; ShapeFinder composes its distinct sixteen-member ColliderShapeData with three fully proved raw Vector3 transfers | shared event-map and selector children through `buff_corpus`; original spans and selected native proofs are required, evaluated distances, colliders and target results remain unresolved |
| `memorypack.buff_damage_processor_collection` | DamageUnit-owned signed nullable processor lists compose independently gated scalar, scale, text, attribute-modifier and calculation children | used by `buff_damage_action` through `buff_corpus`; conditional shared-reference list grammar, original child spans and complete following fields are required; evaluated arithmetic and mutations remain unresolved |
| `memorypack.buff_effect_action_data`, `memorypack.struct_output_sources` | Concrete eighteen-member EffectActionData source/destination proof includes an explicit buffered Int32 enum program, inherited typed owner, complete cursor accounting and full-width store | library validation through the reviewed concrete record contract; collection/provider dispatch, object header/null parity and complete original child composition remain separate gates |
| `buff_action_consumers_native`, `il2cpp.compiled_paths`, `il2cpp.owned_byte_returns` | Build-independent consumer/initialization claims, bounded original local branch paths, receiver-proved closed-data reads, byte argument/store/return flow and typed enum returns through checked guard/epilogue paths; `--gameassembly`, `--metadata`, `--output` select inputs and report; failed claims empty their group and native drift empties all groups | report under `reports/`, `scratch/` or `tmp/`; compiled paths do not prove branch feasibility, runtime selection or format-coverage admission |
| `buff_tick_interval_consumer_native` | Build-independent named TickInterval return-policy claims; `--gameassembly`, `--metadata`, `--output` select inputs and report; native drift and failed claims empty all rows | report under `reports/`, `scratch/` or `tmp/`; the conditional getter policy grants no scheduling, Data ownership, execution result or stored-root admission |
| `memorypack.buff_compare_float_blackboard_children`, `memorypack.buff_damage_check_entity_num_target_children` | Library composition of independently gated parent typed calls and bounded child readers on exact source spans; the selected sword's operands and null/empty target children remain diagnostic-only | caller-owned diagnostics under `reports/` or `tmp/`; no whole-condition or Buff root promotion |
| `memorypack.buff_damage_sword_condition_receipt` | Explicit `--gameassembly`, `--metadata`, `--audit-report`, raw `--source-file` and `--output`: compose independently gated actions, nested IfElse children and sequence envelopes on the reviewed selected source | diagnostic under `reports/`; exact stored condition only; its owning modifier/root composition supplies canonical admission, with no runtime result |
| `memorypack.buff_damage_sword_selected` | Explicit `--gameassembly`, `--metadata`, `--audit-report`, raw `--source-file`, authenticated `--outer-row` and `--output`: compose the recursive sword condition, processor and enum under typed parent joins; the sole root reader owns its thirty-field continuation | selected child diagnostic under `reports/`; canonical admission belongs to `buff_selected_roots` and the complete Buff gate |
| `memorypack.{derived_schema,derived_plans,derived_actions,derived_values,union_subtypes,action_dispatcher,wrapper_members}` | build-derived read plans, dispatch and wrapper member orders (`derived_plans --corpus` is the adoption gate) | `reports/game_data/memorypack_*.json` |
| `memorypack.buff_values`, `il2cpp.reviewed_program` | Gameplay's complete identifier-matched Buff values with an explicit export string pool and typed native enums; shared authentication of reviewed damage/Poise signatures, fields, code windows and linked witnesses | consumed by the Gameplay base and battle-stage builders; stored values and conditional arithmetic remain separate from runtime effects |
| `memorypack.{target_settings,effect_config,damage_unit}_corpus` | selected enum labels over exact SkillData/BuffData records | `reports/game_data/memorypack_*.json` |
| `memorypack.*_native` (multiply_attribute, atk_scale, definite_value, breaking_attack, damage_action_route, damage_action_poise_route, poise_result, buff_1b_action), `scripts.webui.gameplay.route_audit` | selected unpatched formula and route bodies; exact character damage-route partition | `reports/game_data/` |
| `il2cpp.context_audit`, `native_union_atlas` | generic-instantiation contexts; reviewed JsonData union contracts; Atlas accepts a repeated `--contract` for focused audits and an explicit `--gameassembly`/`--metadata` pair, and rechecks native/proof sources before publication | `il2cpp_context_current_latest.*`, `jsondata_union_atlas_current.json`; failed Atlas checks preserve publication and identify the contract and affected native row |
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
| Shared camera fields | `route_deserialize --contract scripts/game_data/contracts/levelscript_camera_look_at_fields_native.json` (parent fields), `curve_key_param` (pooled key), `camera_initial_param` (managed raw24), `camera_state_param` (null reference constant); child gates authenticate pooled bindings and selected native/Unity inputs |
| ActionBase actions | `add_buffs_to_target_selves`, `add_tracking_point`, `tracking_point`, `remove_tracking_point`, `archery_stage`, `typhoea_chip_id`, `audio_cue`, `block_auto_music_change_cancel`, `block_battle_music`, `bool_compare`, `building_pos_hint_show`, `building_pos_hint_hide`, `cutscene_teleport`, `enemy_patrol_start`, `entities_visibility`, `environment_enable`, `event_args_float`, `fac_build_effect`, `fac_change_building`, `fac_get_building_position`, `fac_guide_hint_enable`, `fac_set_interact_locked_state`, `fac_top_view_range`, `finish_buffs`, `finish_scene_effect`, `is_look_at_point_in_screen`, `list_add_value_entity_ptr`, `manually_stop_guide`, `mark_task_condition_failed`, `npc_effect`, `npc_stop_cur_montage`, `npc_proxy_effect`, `npc_proxy_patrol_stop`, `override_npc_dialog`, `play_voice_narrative`, `post_audio_status`, `stop_radio`, `require_settlement_show`, `settlement_followon`, `settlement_upgrade_show`, `reset_follow_camera`, `resume_spawner`, `scripted_char_teleport_to`, `scripted_char_patrol_start`, `stop_char_scripted_mode`, `send_lua_event1`, `set_enemy_ui_show_range`, `set_fac_mode`, `set_forbid_map_teleport`, `set_list_buff`, `show_chapter_completed_panel`, `show_chapter_panel_direct`, `show_finish_toast`, `show_start_toast`, `start_seq_loop`, `start_subgame_countdown`, `stop_subgame_countdown_by_handle`, `start_track_camera`, `exit_camera`, `switch_to_camera`, `track_camera`, `toggle_clear_screen_but_radio_v2`, `toggle_main_hud_ignore`, `set_squad_special_idle_enable`, `set_squad_enable_relax_idle`, `character_play_montage`, `set_decoration_animator_int`, `set_decoration_view_state`, `entity_move_to_with_speed`, `move_bamboo_last`, `set_bamboo_pos_index`, `start_fmv_and_teleport`, `start_narrative_black_screen_teleport`, `disable_hud_fade`, `start_cutscene_hide_scene_object`, `start_cutscene_control_scene_object`, `stop_effect_on_npc_proxy`, `set_main_char_hp_bar_active`, `destroy_ability_entity`, `teleport_gameplay_npc`, `apply_movement_setting_modifier`, `toggle_ui_dev_only`, `set_squad_icon_active`, `skip_entity_die_display`, `water_height` |
| ActionHeader events | `header` (snapshot enter/leave), `entity_hp_changed`, `entity_scanned`, `squad_fight_header`, `squad_all_die_header`, `mission_changed_header`, `leader_enter_trigger_volume`, `on_leader_enter_trigger_volume_list`, `on_spawner_entity_spawn`, `on_spawner_group_begin`, `on_spawner_group_complete`, `on_spawner_start`, `on_spawner_wave_begin`, `on_spawner_pause`, `on_spawner_entity_die`, `on_entity_die`, `on_encounter_intro_part_end`, `on_npc_dirty_block_cleaned`, `on_server_dialog_exit`, `on_level_reset`, `on_specific_entity_die`, `on_specific_entity_list_die`, `on_script_pre_start`, `on_client_global_var_changed`, `on_sub_game_start`, `on_npc_patrol_checkpoint_reach`, `on_physical_no_guard`, `on_physical_infliction`, `on_any_entity_die`, `on_any_enemy_poise_zero`, `on_any_enemy_poise_knot_break`, `on_aether_lock_endpoint_scanned`, `on_blight_miasma_weak_guide`, `on_cutscene_exit`, `on_bb_variable_changed`, `on_start_script_controlled_char_mode`, `on_encounter_activated`, `on_encounter_battle_part_begin`, `on_encounter_battle_part_end`, `on_entity_cast_skill`, `on_spell_abnormal_start`, `settlement_ready_performance`, `archery_advanced_headers`, `on_train_level_event`, `on_enemy_take_last_attack_damage`, `on_spell_infliction`, `on_map_var_changed` (OnMapVarChanged), `on_enemy_in_fight` (OnEnemyInFight) |
| PureGetter getters | `getter_int`, `getter_compare`, `getter_entity_ptr`, `getter_levelscript_ptr`, `getter_list_buff`, `get_cur_squad_all_dead`, `get_character_template_id`, `float_getter_int_to_float`, `float_getter_plus`, `get_interactive_property_int`, `get_mission_save_property_int`, `bool_getter_mult_or`, `npc_get_pack_anim_has_clean`, `get_script_task_objective_is_completed`, `is_endmin_gender`, `entity_to_string`, `get_mission_state`, `get_is_leader_in_trigger_volume`, `check_performance_ready`, `list_make_entity_ptr` |
| GameCondition (`taskMap`) | `taskmap_condition`, `taskmap_followon`, `taskmap_submit`, `taskmap_archery`, `check_game_inst_start_duration`, `check_fac_linking_mode`; `task_condition` is a loader |
| Claims and aggregates | `audio_cue_execute` (build-independent `SetAudioCueVar.Execute` body claims; `--game-root`, `--output`), `route_deserialize` (`--report`), `two_routes` (loader), `param_list` (current pooled graph native audit; shared sequence/template codec) |

Most take `--game-root` and the three source-replay flags. `entity_scanned`
and `track_camera` take no `--summary`. `header`, `getter_*`,
`get_mission_state`, `finish_scene_effect`, `npc_proxy_patrol_stop`,
`post_audio_status`, `set_fac_mode`, `start_seq_loop` and `water_height` take
no options: they print their native audit (some replay default paths) and
their `validate_*` function accepts explicit paths.

`track_camera` authenticates the current parent read/store component and
move-state declarations. It accepts an explicit `--gameassembly`/`--metadata`
pair; source replay remains refused until the current child composition is
proved. Its old owner spans are not reused.

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

`python -m scripts.game_data.audit_build_impact --check-code-windows` inventories
maintained scripts, native-input drift, pinless formatter-window byte drift and
result caches that reach native gates through explicit top-level calls/imports
under `reports/game_data/script_build_impact.{json,md}`. `--previous-report PATH`
reuses checks only when source/native hashes agree. Static dependency exposure
is advisory; matching pins do not certify a reader's semantics. Dynamic calls
and object methods need separate review. `--output` must stay under `reports/`,
`scratch/` or `tmp/`.

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
python -m scripts.game_data.callserver_callback_native --report reports/story/callserver_current_native.json
python -m scripts.game_data.cutscene_case_resolution_native [--game-root GAME_ROOT] [--export-root EXPORT_ROOT]
python -m scripts.game_data.buff_frontiers_regenerate --regenerate [--only frontier9] [--write]
python -m scripts.game_data.skill_custom_root_motion_regenerate --regenerate [--write]
python -m scripts.game_data.levelscript_family_regenerate --regenerate [--only CONTRACT_STEM] [--write] [--report reports/game_data/levelscript_regeneration.json]
python -m scripts.game_data.ifix_patch_native --regenerate PATCH [--write]
python -m scripts.webui.story_recovery.audit_native_carriers cinematic --write-contract
python -m scripts.webui.story_recovery.audit_native_carriers generic --carrier-type Beyond.Gameplay.TeleportParam --focus-field missionId --focus-field levelScriptId --focus-field actionId --focus-field performId --write-contract
python -m scripts.game_data.ifix_vm_operands_native --gameassembly GA --metadata META --input PATCH [--outer-summary OUTER --outer-ledger LEDGER --expected-input-set-sha256 SHA] --output reports/animestudio/ifix_vm_operands_current.json
```

The LevelScript family command re-derives task-condition declaration/dispatch
identity and attempts complete formatter and nested getter
read/setter-pair proofs; auxiliary claims, unsupported ranges, and unresolved helper identities remain unchanged, with
per-contract refusals in its report. Source cursor receipts are separately gated.
String target resolution also accepts the reviewed pooled-index reader only
when its native-input pins, named extension method and complete code windows
validate against `memorypack_pooled_string_reader_native.json`.
The pooled helper's Python API also accepts `wrapper`/`field` for its reviewed
inline sources; explicit selected native paths are required, and a passing
field component never admits its enclosing owner.
Reviewed type comparisons expand only fixed C# aliases. Anonymous `ReadValue`,
`ReadArray` and `ReadPackable` targets require the exact build, registered generic equivalent,
complete body/fragment windows and instruction proof in
`memorypack_reader_clones_native.json`; the typed context must name the same reader
and the reference-return, hidden-output16 or hidden-output40 ABI must match.
Saved argument roles and inlined stores use the maintained instruction readers;
unknown bytes, changed fields and unproved transfers still refuse publication.
Grouped single-Param routes also require a consistent switch and shared helpers.
Catalog routes authenticate inherited metadata and typed own fields; a whole-instance
read is distinguished from a declared field setter. Inner source receipts stay historical.
The impact audit also flags chained inequalities for identity review; its source-cache
version prevents older cached facts from hiding newly added checks.
`il2cpp/string_source_programs.py` uses the optional `string_source_instructions.py`
lane for buffered string/header/span/cursor and cache/constructor transfers.
`string_source_bindings.py` authenticates typed fields and the exact byte span
context/registered target plus internal decoder slots. The optional decoder-loop
extension supplies instruction facts; full edge/frame and String-return checks
remain separate from character semantics and runtime receiver identity.
`memorypack/utf8_source_contract.py` derives the current v2 source contract from
selected metadata, call targets, type cells and complete unwind windows. Its
owning helper validates the candidate before publication; parent source calls
remain independently gated. Valid stored strings use the standard Encoding API
boundary, without invalid-byte replacement or live execution claims.

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
