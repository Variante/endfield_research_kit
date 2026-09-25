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
| | `game_data/terrain/` | the TRET container reader (`tret.py`), Map's `_H` texture-byte diagnostic (`height.py`), the native consumer and layer-path validators, and the corpus gate |
| | `game_data/il2cpp/` | `protocol.py` (metadata and PE primitives), `native_image.py` (the one opened installed build every contract validator checks against, with the shared method-identity, dispatcher-route, code-window and setter-order checks), `context.py` (generic-instantiation pointer tables), `method_resolver.py` (managed name to selected-build body), and the context audit split by the section it owns: `context_audit.py` (CLI, registration and method-spec sweeps, report assembly), `context_audit_common.py` (build gate through `contracts/il2cpp_context_audit_native.json`, hashing and sweep helpers), `context_audit_memorypack.py` (MemoryPack reader and BuffData consumer checks), `context_audit_skilldata.py` (SkillData branch witness, replay and static alignment), `context_audit_vfs.py` (stream, VFS and UnityPlayer consumer checks) |
| | `game_data/monobehaviour/` | the exported MonoBehaviour corpus: `census.py`, `monoscript_catalog.py`, `script_names.py`, `field_semantics.py` (what each named class's fields hold) and `table_keys.py` (which string fields carry exported Table keys) |
| | `game_data/schemas/` | the reviewed named JSON schema readers for the textual JsonData families (`gameplay_config.py`, `gameplay_config_polymorphic.py`, `text_schema.py`, `mission_runtime_main.py`, `mission_runtime_meta.py`, `npc_catalog.py`, `npc_prefab_info.py`, `map_config.py`, `ui_level_map_load_config.py`, `level_mount_point.py`, `gold_coin_config.py`), all validated by `named_schema.py` and keeping only their contract pin, path predicate, relations and result shape |
| | `game_data/wwise_sdk_symbols.py` | names functions in the shipped `AkSoundEngine.dll` by matching each `.pdata` function body against the named COMDAT sections of every installed Wwise SDK library, recording which one named it and dropping a symbol two archives define differently; a match needs an equal extent, 80% byte agreement and a clear margin over the runner-up, so an ambiguous or weak candidate leaves the function unnamed |
| | `game_data/memorypack/derived_schema.py` | recursive read-plan resolution over the derived wrapper, union, enum and wrapped-type tables; models the counted-map framing a reviewed reader proves and refuses every other formatter-backed type rather than reading its member list |
| | `game_data/memorypack/union_subtypes.py` | tag assignment for the nested unions the dispatcher walk cannot reach, inferred from the wrapper hierarchy and gated on the walked union reproducing exactly |
| | `game_data/memorypack/derived_actions.py` | the narrow flat-body case of the same idea: adds only the routes whose members are all fixed-width or strings, with no plan registry. `derived_plans` is the superset |
| | `webui/story_recovery/refresh_audio_hook_catalog.py` | re-pins the audio hook catalog the capture host reads to the installed build: managed RVAs re-resolved by name, native RVAs kept only when still a `.pdata` function start. The host writes the activation manifest itself, and each native row is named from the Wwise SDK on every re-pin, an annotation cleared rather than carried when the match is lost |
| | `webui/audio/semantics/runtime_capture_import.py` | validates one bounded EndfieldCapture audio session against the provider's own completeness counters, decodes its callback payloads with the writer's own `AudioEventPayload` layout, and reports the Events posted and files opened without joining them |
| | `webui/audio/semantics/decoded_payload_event_names.py` | Wwise Event-name candidates from exact decoded payload members, gated by selected native inputs and promoted by the source Audio index's HIRC inventory; also feeds `build_audio` |
| | `game_data/memorypack/derived_values.py` | decodes a plan into named values rather than only framing it, and checks each decoded record's own identifier against its filename |
| | `game_data/memorypack/derived_plans.py` | opt-in reader that executes a `derived_schema` read plan with the frozen reader's own primitives, so a nested record, list, counted map or union is consumed rather than only described; `--corpus` is its adoption gate against exported BuffData |
| | `game_data/memorypack/action_dispatcher.py` | the whole AbilityActionData union dispatcher of the selected build, walked from the reviewed catalog's matching wrapper/table pins; names the wrapper behind every tag, including the ones no contract covers |
| | `game_data/memorypack/wrapper_members.py` | the selected build's generated wrapper member order and member types for every `*ForMemoryPack` type, derived in one metadata pass; the bulk source the per-tag contracts record one wrapper at a time |
| | `game_data/memorypack/union_dispatch.py` | reads a union's tag assignment from its native `<Base>ForMemoryPackFormatter.Deserialize` jump table, found by name and instruction shape; accepts a table only when every entry resolves one-for-one onto the family's derived wrappers, and refuses unions compiled without one |
| | `game_data/pure_getter_rows.py` | re-derives the per-build fields of reviewed PureGetter contract rows -- tag, member count and ordinals, `GetResult` body -- for the `*_getter_native.py` loaders' `--regenerate` |
| | `game_data/levelscript_union_tags.py` | the current build's ActionBase / PureGetter / ActionHeader `(tag, member count)` for every type name, regenerated from the native formatter switches into `contracts/levelscript_union_tags.json`; LevelScript codecs and Story name a type (`union_tags.action("IfElseAction")`) instead of writing a tag literal that the next client update renumbers |
| | `game_data/il2cpp/call_graph.py` | names a body's direct calls (ordinary and generic method pointers), the string literals it loads and the fields it reads before a call, so a native contract can state "A calls B, then C" by name and re-prove it on each build |
| | `game_data/il2cpp/body_claims.py` | name-addressed method bodies of the selected build (`BodyIndex`: short-name resolution, `.pdata` fragments, one level of unnamed helpers, iFix patch ids) and the claim kinds a reviewed contract states about them -- `calls`, `notCallsPrefix`, `comparesResult`, `readsField`, `storesConstant`, `returnsConstant`, `matches` -- evaluated on whichever build is installed |
| | `game_data/story_native_consumers_native.py` | proves the Story builders' native claim groups and resolves their `cited` methods from `contracts/story_native_consumers.json`, caching the evaluation in `reports/story/recovery/story_native_consumers.json` keyed by the installed build and the contract bytes; a failed or `pendingReview` group publishes nothing |
| | `game_data/memorypack/` | MemoryPack codecs and their corpus gates, including the current-build BuffData additions (`buff_icon_config.py`, `buff_residual_actions.py`, `buff_named_schema.py`) and the SkillData timeline lane (`skill_timeline_*.py`), which share `core.LabelledReader` and gate through `il2cpp.native_image` |
| **2. WebUI** | `webui/views.py`, `webui/package.py` | page-build orchestration, and packaging |
| | `webui/story/` | Story and Text page data plus shared Story evidence |
| | `webui/story_recovery/` | Story audits, OCR ordering, runtime traces, candidate generation |
| | `webui/mission_pipeline/` | standalone Mission Pipeline recovery (not a WebUI page) |
| | `webui/mission_pipeline/runtime_contract_native.py` | re-derives `RUNTIME_CONTRACT`'s addresses, tokens, iFix patch ids and ParamBlackboard key slot by name on the installed build and labels each native chain row `verified`, `verified_with_bypassed_hops`, `partially_resolved` or `link_failed` |
| | `webui/{assets,audio,characters,gameplay,map,recovery,updates}/` | one folder per page: its `build_*.py` entry point and helper modules |
| | `webui/recovery/` | the debug-only Recovery page: `build_recovery.py` aggregates the VFS logical-file profile by concrete block and declared path family, and counts Unity objects per type from the export's asset maps; `recovery_declarations.json` owns the reviewed enum names, family rules, per-type entries, and four-stage evidence text. It reads the profile report, the export's `meta/` asset maps and VFS index, and the level table in `memory/game_data/README.md`, never installed bytes, and fails closed on unknown block ids, malformed rows, or ambiguous family rules |
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
command, not part of normal WebUI export. Its current-corpus receipt checks
complete H/N/T/A/S/C tile groups, paired D/N layer indices with C as an
optional subset, and GraphicsFormat/header-shape distributions by path family.

`python -m scripts.game_data.terrain.layer_paths_native --game-root ".../Endfield_Data"`
checks the selected native build and nine path-template loads in one
`UnityPlayer.dll` routine, including its entry, path continuation and
epilogue. It validates the grouped `LAYER_C/D/N` 32-byte
record and the separate packed-tile `Terrain_H/N/T/A/S/C` 56-byte record,
including each formatter/helper forwarding, the tile formatter's
root/high/low/middle argument order, and collection append.
It writes `reports/terrain/layer_paths_native.json` and withholds the result
if any input or checked instruction differs. The separate `LAYER_C/D/N`
render-property route is checked by `layer_slots_native.py` below.

`python -m scripts.game_data.terrain.tile_slots_native --game-root ".../Endfield_Data"`
checks the selected tile queue, ready callback, six result handles, guarded
copies, and the render-property ID binding. Its receipt is
`reports/terrain/tile_slots_native.json`. The exact suffix-to-property route is
H/Heightmap, N/Normalmap, T/TintColor, A/Albedo, S/SplatCtrl, and C/CliffIndex;
the native gate checks the A/S temporary-slot swap. This names render-property
literals, not encoded channels, runtime selection, or final GPU sampling.

`python -m scripts.game_data.terrain.layer_slots_native --game-root ".../Endfield_Data"`
checks the selected `LAYER_D/N/C` queue, callback, handle forwarding, distinct
owner-local destinations, guarded copy helper, and same-handle render-property
binding. Its receipt is `reports/terrain/layer_slots_native.json` and proves
D/`_Splats`, N/`_Normals`, and C/`_ConeMaps` (C is conditional). Managed field
names, encoded channels, shader sampling, and live selection remain open.

`python -m scripts.game_data.terrain.virtual_texture_managed_native --game-root ".../Endfield_Data"`
checks the separate managed `HGTerrainRenderer` to `VirtualTextureRenderer`
`TerrainResource` handoff and the child constructor's eight
`runtimeResources.textures` field copies, including field names, runtime
types/offsets, and selected instruction bytes. It also checks the direct
converter-to-terrain-manager setup route and four named converter property IDs,
`TryConvertAssetFrom<T>` MethodSpecs, and local output slots forwarded as
typed Phase 1 arguments. Its receipt is
`reports/terrain/virtual_texture_managed_native.json`. It does not join those
fields to the installed `LAYER_*` or six-file tile paths.

`python -m scripts.game_data.irradiance_path_native` validates the selected
IrradianceVolume V3 scene/Gacha `/v3/index.bytes` suffix construction,
the selected proxy property's conversion into a scene path,
managed-to-native path handoff, path-keyed stream lookup, the selected request's
type-zero queue drain and exact-count read success gate, queued status
completion, resource-name keyed handle cache, conditional default Windows-file
provider method set and virtual provider boundary,
ready buffer-pointer transfer, and downstream native cursor. It also checks a
conditional `regionIv_%s_%u.bytes` format, supplied-root directory plus
formatted-basename path assembly and shared lookup/stream route for room
files, plus the selected ready-buffer room-header parser and conditional
8- or 16-byte grid-record copy. It also checks the copied-record allocation
descriptor's callback handoff, command binding and grid-cell-count-sized
virtual dispatch request. The ignored
receipt is `reports/irradiance/v3_path_native.json`. The cursor checks both V3
index magics and uses 36-byte scene versus 32-byte Gacha records. The complete
selected parser body has no final EOF comparison; its byte and u32 readers have
no local length check. The selected read gate bounds successful I/O, separate
from the parser's missing final EOF comparison. The default provider's open and
read slots reach `CreateFileW`, `SetFilePointerEx`, and `ReadFile` if no
registered provider matches the request. The runtime-selected provider,
exact VFS file identity, backend normalization, supplied directory roots, and
the serialized property value remain unresolved. Room record fields, actual
GPU execution, and texture format also remain unresolved.

The maintained DynamicStreaming `stream_area` gate is
`python -m scripts.game_data.dynamic_stream_area_corpus --expected-input-set-sha256 INPUT_SET_SHA256`.
It revalidates the authenticated outer VFS inputs, streams only current
`FBStreamArea.bytes` files, checks every payload against its ledger identity,
and writes `reports/animestudio/dynamic_stream_area_current_latest.{json,md}`.
It bounds the root fields and requires all six vector count words and bodies
to tile the tail from the root object through payload EOF. The first three
vectors have four-byte elements; a `Get*Bytes` accessor does not make them
byte vectors.

`python -m scripts.game_data.dynamic_stream_area_native --gameassembly PATH
--metadata PATH --corpus-report reports/animestudio/dynamic_stream_area_current_latest.json
--input-root DUMP_ROOT --expected-input-set-sha256 INPUT_SET_SHA256
--output reports/animestudio/dynamic_stream_area_native_latest.json` checks the
reviewed selected-build accessors, reads the matching `AnimeStudio.CLI dump`
tree, and audits area/visibility and trigger/point ownership. It also checks
the selected `CheckInArea` body and parity-branch window that establish its
X/Z, height, and even-odd polygon tests. `DUMP_ROOT`
contains the `Data/DynamicStreaming/.../FBStreamArea.bytes` paths. The output
is a local report; it does not establish live activation.

`python -m scripts.game_data.dynamic_main_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` validates the selected-build
`SingleGrid` vector builders and indexed accessors, authenticates the current
VFS ledger and matching `AnimeStudio.CLI dump` tree, and writes
`reports/animestudio/dynamic_main_vector_native_latest.{json,md}`. `DUMP_ROOT`
contains `Data/DynamicStreaming/.../fb_main_*.bytes` from a targeted dump.
The generic main reader uses a one-byte lower bound; this native audit proves
field-specific vector extents and nonoverlap, without claiming whole-file
closure or nested record meaning.

`python -m scripts.game_data.dynamic_data_index_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` checks the selected-build
`DataIndex` record layout and enum values, then audits every current main
grid's stored `Grid`/`Type`/`Index` references against its named vectors. It
writes `reports/animestudio/dynamic_data_index_native_latest.{json,md}` and
keeps count-only rival mappings visible. It does not prove runtime dereference.

`python -m scripts.game_data.dynamic_system_routing_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` authenticates the selected
`GetSystemByDataType` jump-table route and its independently registered switch,
then rejoins the current DataIndex corpus. It writes
`reports/animestudio/dynamic_system_routing_native_latest.{json,md}` with
named system routes; stored records do not establish live lookup or activation.

`python -m scripts.game_data.dynamic_root_comp_native --gameassembly PATH
--metadata PATH --game-root GAME_DATA_ROOT --export-root EXPORT_ROOT
--input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` validates the selected RootComp
and DataGroup layout, the grid lifecycle to `_ParseLoad` to `RegisterEntity`
call chain, and the typed `DynamicSceneTemplates` load into the entity map.
It checks the fresh exported MonoBehaviour against its asset map and manifest,
then proves every current grid's RootComp groups tile its DataIndex vector and
match their template `comps` lists in order. It also checks that the selected
`IdComp` detour reads `UniqueId` and rejoins the common type route. It writes
`reports/animestudio/dynamic_root_comp_native_latest.{json,md}`.
The same audit checks RootComp's `State`, `NeedLazyDestroy`, and both nested
visible groups; their `PrimitiveInt` spans address the grid's
`PrimitiveIntList` without overlap, with unassigned integers reported locally.
It also validates the typed entity visibility controllers and their native
`Register` path from each group to the `PrimitiveIntList` vector reader.
The static consumer and authored match do not establish that a grid loaded or
a component ran.

`python -m scripts.game_data.dynamic_resource_comp_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` authenticates current main grids
and the selected ResourceComp/ResourceGroup record layout. It checks each
scene-scoped Grid ID and resource group against the Model, Effect, and Ecs
vectors, including same-scene cross-file targets, and reports exact span
coverage of the PrimitiveIntList alongside RootComp visibility. The generated
receipt is `reports/animestudio/dynamic_resource_comp_native_latest.{json,md}`;
stored references do not establish live resource activation.

`python -m scripts.game_data.dynamic_sludge_surf_tile_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` authenticates the selected
`SludgeComp.SurfTileIDs` inline group and checks its disjoint span with the
RootComp and ResourceGroup visibility groups in each current main grid. Its
ignored receipt is `reports/animestudio/dynamic_sludge_surf_tile_native_latest.{json,md}`;
the stored tile IDs do not establish runtime use.

`python -m scripts.game_data.dynamic_version_native --gameassembly PATH
--metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` authenticates the selected
`fb_version` root as an `Entries` vector with `Major` and `Minor`, checks its
16-byte `Id`/`Version` entries against the current VFS ledger and dump, and
writes `reports/animestudio/dynamic_version_native_latest.{json,md}`. The
runtime version decision remains unresolved.

`python -m scripts.game_data.dynamic_version_id_domain --gameassembly PATH
--metadata PATH --expected-input-set-sha256 INPUT_SET_SHA256
--control-scene map01` checks the selected native version and IdComp layouts,
streams the relevant files through AnimeStudio, and rejoins them to the
current VFS ledger. Its ignored receipt is
`reports/animestudio/dynamic_version_id_domain_latest.{json,md}`. It checks
same-scene version-ID containment in indexed `IdComp.UniqueId`, a separate
grid-ID negative check, and an explicit control scene. It does not classify a
live version-ban decision.

`python -m scripts.game_data.dynamic_version_ban_native --gameassembly PATH
--metadata PATH` checks the selected `LoadFromBasePath` candidate selection
and `IsEntityVersionBanned`/`IsBanned` HashSet query path, including IFix
override branches. It gates on the installed native inputs and the reviewed
version-entry layout, then writes the ignored
`reports/animestudio/dynamic_version_ban_native_latest.json`. It makes no
live patch-state, phase, or ban-outcome claim.

`python -m scripts.game_data.dynamic_active_version_native --gameassembly PATH
--metadata PATH` checks the selected network login response through the
typed yield, shared object reference, protocol-message branch-version setter,
player getter, parser regex and capture-to-output path, default active fields,
and guarded stores into the version ban set. It writes
`reports/animestudio/dynamic_active_version_native_latest.json`; the live
response bytes/value and selected phase remain unobserved.

`python -m scripts.game_data.dynamic_aux_pair_corpus --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` authenticates all paired
`fb_init`/`fb_streaming` dumps against the current VFS ledger and checks their
anonymous root framing, same-index table shapes, bounded byte/count
equalities, grouped-ID partition of root field three, exact descriptor
stride times ID count blob lengths, and descriptor 21's 63-byte stored-name
projection. It writes `reports/animestudio/dynamic_aux_pair_latest.{json,md}`;
other descriptor meanings and live file selection remain open.

`python -m scripts.game_data.dynamic_aux_bridge_native --gameassembly PATH
--metadata PATH` checks the selected managed calls from the DynamicStreaming
ECS load transition through both auxiliary path getters to the UnityPlayer
runtime-chunk allocator. It validates the internal-call registration and the
native helper's separate storage of the two paths. It also checks the indexed
native resource requests, ready-buffer root resolution, consumer reads of
first-root field seven and second-root field six, and the paired ID,
descriptor, and blob handoff to a descriptor-major copy builder, then writes
`reports/animestudio/dynamic_aux_bridge_native_latest.json`. Field meanings,
the selected provider, concrete VFS file identity, and live selection remain
open.

`python -m scripts.game_data.dynamic_visibility_area_join --gameassembly PATH
--metadata PATH --main-input-root MAIN_DUMP_ROOT
--area-input-root AREA_DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` joins the two validated native
reports and the current area corpus report, rechecks their selected inputs,
predicate receipt, and dump hashes, and proves each `Scene/` main file's
visible-area integers occur
in the matching `FBStreamArea.TotalAreas`. Unpaired `Extra/` main files remain
explicit. It writes `reports/animestudio/dynamic_visibility_area_join_latest.{json,md}`.

`python -m scripts.game_data.dynamic_visibility_state_join --gameassembly PATH
--metadata PATH --game-root GAME_DATA_ROOT --main-input-root MAIN_DUMP_ROOT
--export-root EXPORT_ROOT --expected-input-set-sha256 INPUT_SET_SHA256`
rechecks the RootComp native report, main dump hashes, and Persistent export
freshness, then joins each authored scene visible-state integer to the same
scene's `MapConfig.sceneStates` index. It reports the independent auxiliary
grid-vector counts and leaves runtime state selection open. It writes
`reports/animestudio/dynamic_visibility_state_join_latest.{json,md}`.

`python -m scripts.game_data.dynamic_visibility_runtime_native
--gameassembly PATH --metadata PATH --expected-gameassembly-sha256 SHA256
--expected-metadata-sha256 SHA256` evaluates the reviewed, build independent
field and call claims in `contracts/dynamic_visibility_runtime_claims.json`.
It checks MapConfig JSON path literals, table lookup and both scene-loading
handoffs, the `MapConfig` scene-state calculation, the named
`SetSceneState` route, and the index-list handoff to DynamicStreaming.
It also checks the streaming-config asset load and scene-name handoff, main,
init, streaming and version file path builders, typed FlatBuffer chunk reads,
condition evaluator and listener calls, selected enum defaults, and state and
area active-set routes through the entity and resource systems.
It also checks the `FBStreamArea.bytes` VFS read, area-dealer root and trigger
tree setup, `RootVisible` active-set seeding, initial area flush, and later
trigger queries through `CheckInArea` and area-change handoff to the streaming
engine and DynamicStreaming. Portal claims check the LevelData component
override handoff, the placed-interactive lookup and node spawn arguments into
the allocator, the dependency-group and AOI-state pipeline branches, the
grid callers of the checked anonymous AOI setter, typed
`tp_position` assignment, component-data enum keys and field reads, the
shared dynamic-property setup, and load handoff.
A successful run writes
`reports/animestudio/dynamic_visibility_runtime_claims_latest.json`; failed
claims write a separate pending-review report and leave the validated report
untouched. The checks do not observe live controller execution or condition
results.

`python -m scripts.game_data.dynamic_streaming_config_join --gameassembly PATH
--metadata PATH --game-root GAME_DATA_ROOT --export-root EXPORT_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` rechecks both native reports and
freshness of the StreamingAssets and Persistent exports. It joins all
catalogued scene streaming assets to exported MonoBehaviours and original
object-index rows by container, source and PathID, verifies their resolved
`StreamingMapConfig` MonoScript, and marks current MapConfig references.
It compares `mapSceneName` with authenticated DynamicStreaming main-file
directories and ordinary Streaming VFS paths (default ledger under
`reports/animestudio/`, override with `--vfs-ledger`). It writes
`reports/animestudio/dynamic_streaming_config_join_latest.json`, retaining
unreferenced assets and scene names present on only one side. The joined
paths are authored evidence; the tool does not claim a live asset load.

`python -m scripts.game_data.dynamic_main_path_join --gameassembly PATH
--metadata PATH --main-input-root MAIN_DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` rechecks the selected native
`GetPath` claims and RootComp report, authenticates each main dump by its VFS
MD5, and proves the `fb_main` filename encodes the root `UniqueId` in every
current file. It writes `reports/animestudio/dynamic_main_path_join_latest.json`.
The relation does not identify a live grid request.

`python -m scripts.game_data.portal_center_join --gameassembly PATH
--metadata PATH --game-root GAME_DATA_ROOT --export-root EXPORT_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256` rechecks selected native claims,
union tags, the interactive component enum, the VFS audit, and export
freshness. It joins exact portal templates to exact LevelData interactives,
keeping template defaults, placed source positions, and destination overrides
separate. It also retains each placed dependency-group ID and authored
force-load flag. It writes
`reports/game_data/portal_center_join_latest.json`. The
selected native claims trace the LevelData override into a component
blackboard and the conditional AOI-to-spawn route into the placed-data
allocator; live execution and the actual selected center remain open.

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

### Unity object store (layout v3)

The exporter publishes every exported Unity object document (`.json` and the
`.anim` clips, about 1.7 M files) into one SQLite file,
`<export root>/game/Unity.sqlite`, instead of loose files; converted media
(PNG, OBJ, FBX) stays under `game/Unity/<Type>/` because the browser opens it
by path. `scripts/game_data/unity_store.py` owns the format and the only
reader: builders call `UnityObjectStore.for_export(root)` and query by type
plus a file-name glob, by object name, or by PathID. Rows keep the exported
file name and exact bytes, so `game/Unity/<Type>/<name>` stays the provenance
reference, and `serve.py` still answers those URLs from the store. Nothing
falls back to loose files: a v2 root, or a v3 root with no store, fails closed.

A layout-v2 root (a saved previous export, for example) is converted in
place. The pack re-hashes every row before it deletes a loose file, resumes
after an interruption, and `--unpack` restores the v2 tree. A file the disk
cannot read stops the pack before anything is deleted, with every such file
listed in the work dir; `--accept-unreadable` is the explicit decision to
record them as lost (moved to a quarantine, listed in the store's
`unreadableAtPack` meta row) and finish:

```bat
python -m scripts.game_data.extraction.pack_unity_store --export-root export_full_1d5d1 --dry-run
python -m scripts.game_data.extraction.pack_unity_store --export-root export_full_1d5d1
```

For ad-hoc study, the store CLI lists, prints, extracts and runs SQL, with
`inflate(data)` (the document text) and `doc(data, '$.path')` registered:

```bat
python -m scripts.game_data.unity_store stats
python -m scripts.game_data.unity_store ls MonoBehaviour "data_chr_*"
python -m scripts.game_data.unity_store sql "SELECT name, doc(data, '$.m_Name') FROM objects WHERE type='TextAsset' LIMIT 5"
python -m scripts.game_data.unity_store extract MonoBehaviour "DynamicScene*" --out tmp\study\dyn
```

The `objects` table carries `type, name, object_name, path_id, source_file`
(the CAB) and `script_path_id` columns, all indexed; any other SQLite client
can read it, and only the document body needs `zlib` to inflate.

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
| DynamicStreaming main vector audit | `game_data/dynamic_main_native.py` | `reports/animestudio/dynamic_main_vector_native_latest.{json,md}` |
| DynamicStreaming DataIndex native audit | `game_data/dynamic_data_index_native.py` | `reports/animestudio/dynamic_data_index_native_latest.{json,md}` |
| DynamicStreaming system route audit | `game_data/dynamic_system_routing_native.py` | `reports/animestudio/dynamic_system_routing_native_latest.{json,md}` |
| DynamicStreaming RootComp group audit | `game_data/dynamic_root_comp_native.py` | `reports/animestudio/dynamic_root_comp_native_latest.{json,md}` |
| DynamicStreaming Sludge SurfTileIDs audit | `game_data/dynamic_sludge_surf_tile_native.py` | `reports/animestudio/dynamic_sludge_surf_tile_native_latest.{json,md}` |
| DynamicStreaming version root audit | `game_data/dynamic_version_native.py` | `reports/animestudio/dynamic_version_native_latest.{json,md}` |
| DynamicStreaming active-version source audit | `game_data/dynamic_active_version_native.py` | `reports/animestudio/dynamic_active_version_native_latest.json` |
| DynamicStreaming auxiliary pair corpus | `game_data/dynamic_aux_pair_corpus.py` | `reports/animestudio/dynamic_aux_pair_latest.{json,md}` |
| DynamicStreaming auxiliary native bridge | `game_data/dynamic_aux_bridge_native.py` | `reports/animestudio/dynamic_aux_bridge_native_latest.json` |
| DynamicStreaming area native audit | `game_data/dynamic_stream_area_native.py` | `reports/animestudio/dynamic_stream_area_native_latest.json` |
| DynamicStreaming scene-local area join | `game_data/dynamic_visibility_area_join.py` | `reports/animestudio/dynamic_visibility_area_join_latest.{json,md}` |
| DynamicStreaming scene-local state join | `game_data/dynamic_visibility_state_join.py` | `reports/animestudio/dynamic_visibility_state_join_latest.{json,md}` |
| DynamicStreaming visibility runtime claims | `game_data/dynamic_visibility_runtime_native.py` | `reports/animestudio/dynamic_visibility_runtime_claims_latest.json` |
| DynamicStreaming config asset and scene join | `game_data/dynamic_streaming_config_join.py` | `reports/animestudio/dynamic_streaming_config_join_latest.json` |
| DynamicStreaming main path and root ID join | `game_data/dynamic_main_path_join.py` | `reports/animestudio/dynamic_main_path_join_latest.json` |
| Portal template and instance center join | `game_data/portal_center_join.py` | `reports/game_data/portal_center_join_latest.json` |
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
in `webui/gameplay/`; `loadout_data.py` publishes the character loadout inputs
(`attributeCalculation`, `attributeRows`, equipment `attributeModifiers`,
`skillAttributeModifiers`) and publishes the formula only when
`game_data/attribute_formula_native.py` validates it on the installed build
(`python -m scripts.game_data.attribute_formula_native` checks it directly); its `asset-refs` stage calls the public
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
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-action-receipts
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
python -m scripts.game_data.memorypack.buff_stacking_compact_corpus --corpus-report reports/animestudio/buffdata_current_latest.json --export-root export_full/game/Json/BuffData --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output reports/animestudio/buff_stacking_compact_current_latest.json
python -m scripts.game_data.memorypack.buff_timeline_empty_receipt --compact-report reports/animestudio/buff_stacking_compact_current_latest.json --buff-report reports/animestudio/buffdata_current_latest.json --export-root export_full/game/Json/BuffData --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output reports/animestudio/buff_timeline_empty_current_latest.json
python -m scripts.game_data.memorypack.buff_damage_modifier_receipt --buff-report reports/animestudio/buffdata_current_latest.json --export-root export_full/game/Json/BuffData --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output reports/animestudio/buff_damage_modifier_child_receipt_latest.json
python -m scripts.game_data.memorypack.buff_action_receipt_corpus --buff-report reports/animestudio/buffdata_current_latest.json --export-root export_full --game-root ".../Endfield_Data" --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256
python -m scripts.game_data.memorypack.skill_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --cursor-verification COMPLETE_CURSOR_VERIFICATION_JSON --output reports/animestudio/skilldata_current_latest.json --output-md reports/animestudio/skilldata_current_latest.md
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
python -m scripts.game_data.leveldata_bezier_knot_corpus --game-root ".../Endfield_Data"
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

For the SkillData gate, choose a complete cursor verification whose receipt,
source corpus, native context, and verifier still match its recorded hashes.
If the VFS audit changes only because AnimeStudio.CLI was rebuilt, add
`--allow-exporter-rebind`; the gate then proves the selected logical bytes,
physical identities, game build, and asset roots are unchanged before
accepting that older receipt. A replaced `latest` report is not sufficient
provenance merely because it has the expected name.
The Skill gate also fingerprints every JSON dependency declared by the shared
timeline route contract before and after streaming, so a route update during
the run fails the report rather than publishing mixed evidence.

The LevelData knot gate validates the selected native formatter window and
struct offsets, then requires every exported LevelData file to close its named
43-field frame and every knot to occupy the proved stride. It writes
`reports/game_data/leveldata_bezier_knot_corpus.json`; run the export freshness
guard above first when claiming the export matches the installed client.
`python -m scripts.game_data.leveldata_spline_runtime_native` separately
validates the selected native spline-table and movement-transform consumer
contract. Its `validated` status describes reviewed normal branches; iFix patch
selection and actual movement remain unobserved.

For the complete current Init slot-7 name-prefix gate, run
`python -m scripts.game_data.streaming.descriptor_name_corpus
--expected-input-set-sha256 CURRENT_VFS_AUDIT_INPUT_SET_SHA256`. It rereads
every Init logical file from the VFS ledger's physical chunk, checks MD5 and
input-set provenance, and writes
`reports/chunk_data/descriptor_name_corpus_latest.json`. A `--limit` run is a
diagnostic and cannot certify the corpus. Descriptor 21's 64-byte slot is
compared with the paired root name's first 63 bytes, retaining full-name and
row-major controls separately.

For a bounded selected-file reproduction, run
`python -m scripts.game_data.streaming.descriptor_names --input-jsonl VERIFIED_INIT_STREAM_JSONL
--expected-report reports/chunk_data/slot4_pair_probe_latest.json
--output reports/chunk_data/descriptor_name_join_latest.json`. The input is a
targeted AnimeStudio `stream --verify-md5 --block-type streaming` JSONL. The
auditor checks complete Init framing, both byte layouts, source hashes and the
same-file root ID/name prefixes. The selected Streaming native contract separately
validates the direct descriptor and wrapped-byte consumer; neither check names
the other descriptor IDs as components.

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
| `game_data.memorypack.skill_corpus` | `skilldata_current_latest.{json,md}`; positive passive and shared timeline first refusals appear per file, in bounded summaries, and in the CLI result |
| `game_data.memorypack.skill_timeline_cursor` | `skilldata_timeline_cursor_latest.{json,md}` |
| `game_data.memorypack.npc_montage_corpus` | `npc_montage_current_latest.{json,md}` |
| `game_data.memorypack.buff_corpus` | `buffdata_current_latest.{json,md}` |
| `game_data.memorypack.buff_stacking_compact_corpus` | `buff_stacking_compact_current_latest.json`; selected-native child and raw GameplayTag array ownership rejoined to each complete Buff report identity and exported logical SHA/length; positive nested bodies and whole-BuffData schema stay open |
| `game_data.memorypack.buff_timeline_empty_receipt` | `buff_timeline_empty_current_latest.json`; selected-native timeline list source/store plus per-file null/empty count and exact following-tail joins; positive timeline bodies and whole-BuffData schema stay open |
| `game_data.memorypack.buff_damage_modifier_receipt` | `buff_damage_modifier_child_receipt_latest.json`; selected native and logical-byte hash gate for named child spans in the positive `damageModifier` first-blocker subset; nested processors/actions and whole-BuffData schema remain unresolved |
| `game_data.memorypack.buff_action_receipt_corpus` | `buff_action_receipts_current_latest.{json,md}`; a separate source-hash and selected-native gate for named `0x0092` and `0x00B4` action wrappers, retaining nested and whole-BuffData gaps |
| `game_data.memorypack.buff_1b_corpus` | `buff_1b_current_latest.{json,md}` |
| `game_data.memorypack.buff_1b_action_native --gameassembly GA --metadata META` | `reports/game_data/buff_1b_action_native.json`; selected tag `0x1B` reader-to-field setter order and guarded `BlowOffAction.ExecuteInternal` direct call to `ControlledStateComponent.ApplyBlowOff`. Requires the explicit selected native pair; no live execution or final motion claim. |
| `game_data.memorypack.lipsync_corpus` | `lipsync_current_latest.{json,md}` |
| `game_data.memorypack.derived_schema` | `reports/game_data/memorypack_derived_schema.json`; a recursive read plan per action tag over nested records, lists, arrays and nested unions, with each route's evidence tier and the named type blocking the rest |
| `game_data.memorypack.union_subtypes` | `reports/game_data/memorypack_union_subtypes.json`; every union base's subtypes and predicted tag assignment, gated on reproducing the walked root union and corroborated against the reviewed nested rows plus the frozen reader's own per-tag member counts for six nested unions it never walks |
| `game_data.memorypack.derived_actions` | `reports/game_data/memorypack_derived_actions.json`; the union tags whose whole body this reader can consume, and the cross-check of that framing against the frozen reader |
| `game_data.memorypack.derived_values` | `reports/game_data/memorypack_derived_values.json`; how many records of each exported family decode into named values, how many carry an identifier matching their filename, how many cross-record references resolve to records that exist, and one decoded sample per family |
| `game_data.memorypack.derived_plans` | `reports/game_data/memorypack_derived_plans.json`; each plan's framing cross-checked against the frozen reader tag by tag. `--corpus` prints instead: how many exported BuffData files each reader closes, whether every file the frozen reader already closed still ends at the same cursor, how many routes and nested-union placements the run actually walked, and and how many files of each of the four whole-record families the plan consumes exactly to EOF, against how many land short and how often a refused body's position was reached |
| `game_data.memorypack.action_dispatcher` | `reports/game_data/memorypack_action_dispatcher.json`; every AbilityActionData union tag's route, registered type, generated wrapper, named member order and member widths, with each reviewed tag re-derived and compared |
| `game_data.memorypack.wrapper_members` | `reports/game_data/memorypack_wrapper_members.json`; every generated `*ForMemoryPack` wrapper's serialized member order, member types, fixed member widths (including each enum's real underlying width), and the wrapped type each wrapper frames, derived from the selected build, plus its agreement with the reviewed contracts |
| `game_data.memorypack.target_settings_corpus --gameassembly GA --metadata META [--export-root EXPORT]` | `reports/game_data/memorypack_target_settings.json`; exact SkillData/BuffData `TargetSettings` instances found by derived-plan references, selected enum labels, target-source co-occurrences, and bounded exceptions. Stored authored values only; missing or changed native inputs and incomplete records fail closed. |
| `game_data.memorypack.effect_config_corpus --gameassembly GA --metadata META [--export-root EXPORT]` | `reports/game_data/memorypack_effect_config_enums.json`; exact SkillData/BuffData `EffectActionCfg` instances and selected enum labels across 15 fields. Stored authored values only; missing or changed native inputs and incomplete records fail closed. |
| `game_data.memorypack.damage_unit_corpus --gameassembly GA --metadata META [--export-root EXPORT]` | `reports/game_data/memorypack_damage_unit_enums.json`; exact SkillData/BuffData `DamageUnit` instances, four selected enum fields, attack/poise calculation subtype identities, and four selected calculation enum fields. Missing or changed native inputs and incomplete records fail closed. |
| `game_data.memorypack.multiply_attribute_native --gameassembly GA --metadata META` | `reports/game_data/multiply_attribute_calculation_native.json`; selected unpatched `MultiplyAttributeCalculation.Evaluate` field, call, branch and code-window proof for `GetAttribute × multiplier + addition`. The installed native pair must match; no live execution or final-damage claim. |
| `game_data.memorypack.atk_scale_native --gameassembly GA --metadata META` | `reports/game_data/atk_scale_calculation_native.json`; selected unpatched `AtkScaleCalculation.Evaluate` proof for attacker ATK (override element 2 or getter) times resolved `atkScale`. A present short override array fails; no live execution or final-damage claim. |
| `game_data.memorypack.definite_value_native --gameassembly GA --metadata META` | `reports/game_data/definite_value_calculation_native.json`; selected unpatched `DefiniteValueCalculation.Evaluate` proof for resolved `value`, optionally multiplied by resolved `valueScale` when `applyScale` is true. A patched path bypasses this formula. |
| `game_data.memorypack.breaking_attack_native --gameassembly GA --metadata META` | `reports/game_data/breaking_attack_calculation_native.json`; selected unpatched `BreakingAttackCalculation.Evaluate` proof for attacker ATK, defender break-damage scalar, and resolved scale/multiplier with the native Single/Double order. A patched path bypasses this formula. |
| `game_data.memorypack.damage_action_route_native --gameassembly GA --metadata META` | `reports/game_data/damage_action_normal_route_native.json`; selected normal-entity `DamageAction` snapshot/simple/calculation branch proof, the simple attack-array-times-resolved-scale expression, and `CalculationBase.GetAttribute` override-array fallback. Requires the explicit selected native pair; no live action or final-damage claim. |
| `game_data.memorypack.damage_action_poise_route_native --gameassembly GA --metadata META` | `reports/game_data/damage_action_poise_route_native.json`; selected `_ProcessDamage` join from indexed DamageUnit's nonnull stored `poiseCalculation` through before-calculation Poise modifier and calculation dispatch to intermediate `PoisePackData.calcResult.value`. Requires the explicit selected native pair; no applied or displayed Poise claim. |
| `game_data.memorypack.poise_result_native --gameassembly GA --metadata META` | `reports/game_data/poise_result_native.json`; selected post-calculation Poise modifier path, closed metadata vtable candidate set for virtual `ApplyModifier`, and conditional base Poise controller/writeback path. The God override returns `Failed` on its unpatched branch; live target, patch state and applied amount remain unknown. |
| `scripts.webui.gameplay.route_audit [--index webui/data/lang/CN/gameplay/index.json]` | `reports/game_data/character_damage_routes.json`; exact character SkillData partition by authored snapshot/simple attack flags and stored Poise calculation subtype/scale, requiring validated generated DamageUnit and both native caller routes plus DefiniteValue evaluator evidence. Run after the CN Gameplay base build. |
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
`python -m scripts.webui.story_recovery.audit_native_carriers cinematic`. After
a client update, `--write-contract` regenerates the contract from that audit
when it validates; `--skip-contract-reconciliation` only writes the audit.

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
Typed effect parameters require the selected `GameAssembly.dll`, metadata,
and `AkSoundEngine.dll` to pass the reviewed
`game_data/contracts/wwise_effect_parameters_native.json` gate, including its
12 stock `SetParamsBlock` windows. A mismatched build leaves raw class IDs,
parameter lengths and hashes visible while withholding native-derived values;
the proprietary Convolution Reverb and Mastering Suite rows remain opaque.

Projectile behavior and authored event hashes stay immutable in
`webui/data/gameplay/projectiles.json`; Audio publishes playable HIRC candidates
separately in `webui/data/lang/<LANG>/gameplay/projectile_audio.json`.
`scripts.webui.gameplay.projectiles` reads only `data_projectile_*` objects
whose template and component references are exact managed-reference TypeTree
decodes; every other candidate is skipped and counted by reason
(`counts.skipped`, `skippedFiles`), and `--require-exact` turns a non-exact
skip into a non-zero exit. Sound fields carry the signed int32 plus the
uint32 hex that Audio joins on. The direct builder also checks every exported
`EffectActionCfg` value against the selected native enum fields and publishes
optional `effectConfigEnums` with explicit evidence. The raw authored values
remain available when that native join cannot validate; these labels do not
establish runtime effect behavior.

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
python -m scripts.webui.audio.semantics.play_sound_action_corpus
python -m scripts.webui.audio.semantics.native_play_sound_string --gameassembly GA --metadata META
```

`play_sound_action_corpus` is a focused exact-decoding audit, not a page build.
It writes `reports/audio/play_sound_action_corpus.json` with SkillData/BuffData
PlaySound paths, enclosing timeline, Buff/Ability event context, selected native
enum labels, raw literals, and a comparison to the narrower local action reader.
It requires the selected
`GameAssembly.dll` and `global-metadata.dat`, refuses incomplete whole-record
decodes, and does not promote a sound string into a Wwise Event.
`decoded_payload_event_names.py` collects those same exact SkillData/BuffData
action rows during its one-pass native-gated source decode; `build_audio.py`
publishes their Gameplay sound catalog and owner links after HIRC identity is
known. `play_sound_actions.py` owns the shared action walker and selected
Buff/Ability event-enum labels. `entity_contexts.py` projects HIRC-matched
SkillData/BuffData actions into Audio Event detail contexts.
`native_play_sound_string` is a selected-build, fail-closed audit of the
unpatched PlaySound object and position routes from the serialized sound
string through `AudioHashGenerator.Compute(string)`. It writes
`reports/audio/play_sound_string_native.json`; optional `--event-literal`
and `--audio-source-index` compare the raw and hypothetically trimmed hashes
with one scanned HIRC inventory. iFix replacement and live posting remain open.

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
and `BuffData`), `decoded_payload_event_names.py` (native-gated exact-member
Event candidates), `play_sound_actions.py` (exact action walker and selected
event-enum labels), `play_sound_action_corpus.py` (whole-record action audit),
`native_play_sound_string.py` (selected default-branch string-to-hash proof),
and `event_projection.py`/`event_summary.py` (WebUI row
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
audits only. A broad scan expands `game/Unity.sqlite` into one entry per stored
document at its `game/Unity/<Type>/<name>` path, fingerprinted by the row's
SHA256, so both export roots must be layout v3. The published feed keeps every matching changed entry by default;
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
current export and repository root, and the prune never touches a Unity object
store.

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

### Auditing static map-mark joins

```bat
python -m scripts.game_data.map_mark_relations
```

Writes `reports/game_data/map_mark_relations.json`. It checks six
GameplayConfig JsonData sources against the complete JsonData corpus receipt,
reruns their named schemas, joins stored marker templates to `MapMarkTempTable`,
then records individual markers whose exact instance ID and decoded position
match `WorldEntityRegistry`. A smaller subset also has a unique
`LevelShortIdTable` scene. Group-key matches to MapBrief and MapRegion remain
separate from scene ownership and runtime visibility.

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

Contracts whose claims can be re-proved on a new build carry their own
regenerator. Each re-derives rows by managed name, re-checks every claim in the
installed binary, and refuses to write when one no longer holds:

```bat
python -m scripts.game_data.callserver_callback_native --regenerate [--write]
python -m scripts.game_data.cutscene_case_resolution_native --regenerate [--write]
python -m scripts.game_data.ifix_patch_native --regenerate PATCH [--write]
python -m scripts.webui.story_recovery.audit_native_carriers cinematic --write-contract
python -m scripts.webui.story_recovery.audit_native_carriers generic ^
  --carrier-type Beyond.Gameplay.TeleportParam --focus-field missionId ^
  --focus-field levelScriptId --focus-field actionId --focus-field performId --write-contract
```

`PATCH` is `Gameplay.Beyond.patch.bytes` from a bounded
`AnimeStudio.CLI dump -b i-fix-patch` into `tmp/`. Review contracts that record
a census conclusion rather than a re-provable claim
(`identity_carrier_boundaries.json`, `cross_system_consumers.json`) have no
regenerator; on a new build they stay `mismatched` until reviewed again.

The IFix VM opcode command derives the selected build's `Instruction` layout
and `Code` enum from the explicit native pair; it names opcodes inside the
patch reader's exact method spans and retains raw operands. Pass fresh,
MD5-verified patch dumps as inputs; the command does not select live VFS files.

```bat
python -m scripts.game_data.ifix_vm_instruction_native --gameassembly GA --metadata META ^
  --input PATCH [--input PATCH2] --output reports/animestudio/ifix_vm_opcodes_current.json
python -m scripts.game_data.ifix_vm_operands_native --gameassembly GA --metadata META ^
  --input PATCH [--input PATCH2] --output reports/animestudio/ifix_vm_operands_current.json
python -m scripts.game_data.ifix_external_signatures_native --gameassembly GA --metadata META ^
  --input PATCH [--input PATCH2] --output reports/animestudio/ifix_external_signatures_current.json
```

The operand command additionally checks the reviewed selected-build
`ifix_vm_operands_native.json` loader and interpreter bodies. It joins the
low-half indices for `Call`, `Callvirt`, `CallExtern`, and `Newobj` to declared
file rows, and resolves signed relative targets for `Br`, `Brtrue`, and
`Brfalse`. It also joins `Ldstr` and nonnegative `Ldfld`, `Ldsfld`, `Stfld`,
and `Stsfld` operands to declared string and field rows. The signed upper
half of `Call` and `Callvirt` is the recursive `argsCount`. For `CallExtern`,
the signed upper half rewinds that many 12-byte evaluation-stack slots to the
external argument base. `Newobj` uses that same signed upper-half rewind
when the resolved constructor's declaring-type base differs from
`System.MulticastDelegate`; the delegate path is separate. The negative
field-operand path and execution remain open.
It also decodes `StackSpace` local and evaluation-stack counts, validates
local-slot indices for `Ldloc`, `Ldloca`, and `Stloc`, names `Ldarg` slots
without assuming a runtime argument count, records their coverage under
authored recursive call edges, and records whether `Ret` selects a stack
value. It validates the loader's six `ReadInt32` calls and field stores for
each 24-byte exception record, then reports handler type, catch-type id,
instruction boundary indices, and their bounds against the VM method.
It reports `Leave` as an absolute pending instruction target (with zero
kept as a sentinel) and `Endfinally -1` as a conditional resume from that
pending target. These are authored control-flow edges, not an execution trace.
The audit also validates `CallExtern`'s encoded MethodDef delegate
target and the conditional reflected-result path through
`ReflectionMethodInvoker.Invoke` and `Call.PushObjectAsResult`.
The external-signature command restores generic parameters to their file
positions, substitutes constructed owner and method arguments, and requires a
unique full parameter match in the selected native metadata. It reports each
definition's return type and static flag; reflection selection remains
unobserved. Its explicit native pair must match the reviewed IFix contract.

Other reviewed native meanings are claims about named method bodies, checked
live on the installed build rather than pinned by body hash:
`contracts/dialog_finish_native.json` (the DialogTree finish audit) and
`contracts/story_native_consumers.json` (Story consumer groups: NPC proxy
selection, trunk playback, If/Branch next-index, Branch.Execute order,
CutsceneRoot playback, module save-key prefix, protocol event paths, plus a
`cited` map of methods rows only name). A claim that fails, or a group marked
`pendingReview` because its code moved, publishes nothing. Generated artifacts
made on one build -- the reverse-PPtr audit, `webui/story/dynamic_scene.json`
-- are current only when their recorded native hashes equal the installed
build's. The Audio native catalog still pins its reviewed build in
`contracts/audio_native.json`: its rows carry that build's indexes and
addresses and are withheld on any other build until re-derived.

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
