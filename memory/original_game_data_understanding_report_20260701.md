# Original Game Data Understanding Report

Generated: 2026-07-01

This report summarizes how well the current checkout understands the original
Endfield game data, based on generated reports and WebUI data artifacts. It is
an interpretation of generated evidence, so it lives in `memory/` rather than
`reports/`.

Primary evidence reviewed:

- `reports/export_full_summary.md`
- `reports/source_graph/summary.md`
- `reports/game-data-change-summary.md`
- `reports/export_benchmark_latest.md`
- `reports/mission_timeline_recovery_CN.md`
- `reports/scene_order_gap_report_CN.md`
- `reports/narrative_videos_CN.md`
- `reports/story_source_links_CN.md`
- `reports/line_order_recovery_report_CN.md`
- `reports/runtime_jump_option_route_audit_CN.md`
- `reports/option_response_audio_evidence_CN.md`
- `reports/option_override_coverage_CN.md`
- `reports/i18n_reference_index_CN.md`
- `reports/build_story_unselected_i18n_jsons_CN_structured.md`
- `reports/option_flow_runtime_metadata.md`
- `reports/buff_runtime_metadata.md`
- `reports/texture2d_raw_hash_collision_audit.md`
- `reports/texture2d_raw_hash_collision_isolated_verify.md`
- `reports/video_bindings.md`
- `reports/gameplay_video_ocr/story_order_ocr_matches.md`
- `reports/mission_order/main_story_order_vs_override_CN.md`
- `webui/data/manifest.json`
- `webui/data/assets/index.json`

Additional durable memory reviewed:

- `memory/README.md`
- `memory/webui_recovery.md`
- `memory/game_data_formats.md`
- `memory/binary_json_cracking.md`
- `memory/source_graph_database.md`
- `memory/story_runtime_extraction_audit.md`
- `memory/scene_file_order_recovery.md`
- `memory/scene_order_static_frontier.md`
- `memory/mission_file_order_from_original_data.md`
- `memory/e0m0_file_order_from_binary_scripts.md`
- `memory/project_c_scene_order_stage4.md`
- `memory/quest_tree_source_connections.md`
- `memory/animestudio_ab_understanding_report.md`
- `memory/animestudio_decode_gaps.md`
- `memory/animestudio_export_recovery_progress_2026-06-28.md`
- `memory/animestudio_missing_output_and_ab_status.md`
- `memory/animestudio_warning_error_status_20260630.md`
- `memory/texture2d_output_collision_status_20260630.md`
- `memory/ability_system_*.md`
- `memory/advanced_buff_stack_recovery_20260629.md`
- `memory/create_buff_action_recovery_20260629.md`
- `memory/effect_action_cfg_recovery_20260630.md`
- `memory/monobehaviour_*_20260630.md`
- `memory/animestudio_ability_entity_payloads.md`
- `memory/character_unity_export_workflow.md`

## Executive Assessment

The project has strong coverage of raw extraction, indexing, CN Story/Text
Tables display, texture extraction, audio linkage, broad asset discovery, and
queryable SNS/radio/remote communication table bridges. The WebUI-facing data
is coherent enough to browse most story, table, audio, video, and asset
references from extracted game data.

After reading the memory notes, the main assessment changes in two ways:

- The project understands several binary game-data formats better than the
  generated report list alone implied. Many `.json` files are actually
  MemoryPack-like binary config blobs, and a number of important families now
  have exact or bounded partial decoders in the WebUI Data index and
  AnimeStudio exporter.
- The remaining gap is still semantic certainty, not file access. Exact runtime
  ordering, branch routing, formula execution, full game-wide
  character/animation reconstruction, original shader assignment, and gameplay
  control-flow interpretation still require runtime or engine-level evidence.

Current confidence by area:

| Area | Confidence | Summary |
| --- | --- | --- |
| VFS/container inventory | High | Current source roots are indexed with no missing VFS chunks in the latest summary. |
| WebUI Story/Text Tables corpus | High | CN conversations, missions, actors, references, and source links are broadly surfaced. |
| Story line order | High for most scenes, partial for known edge cases | Latest gap report is down to 35 flagged CN scenes. |
| Option branch routing | Moderate for runtime proof, high for current WebUI override coverage | Most options are represented. Current option warning units are all manually covered for display, but some response and route targets still require independent runtime proof. |
| Mission/global story chronology | Moderate to low | Static recovery provides useful structure, but observed gameplay order still diverges in many main-story missions. |
| Text/reference tables | High for extraction, moderate for meaning | Tables and IDs are mostly accessible; gameplay semantics and formulas are not fully decoded. |
| Binary config formats | Moderate to high by family | Many MemoryPack-like families have exact or bounded decoders; nested bodies and FlatBuffer schemas remain partial. |
| Numerical systems | Moderate for recovered schemas, low for formulas | Many fields and values are decoded; exact runtime formulas and evaluators remain partial. |
| Audio | High for story linkage, moderate for full semantics | Event/media links, line usage, raw SNS/radio/remote bridges, and voice-extra table joins are strong; deeper Wwise/runtime behavior remains partial. |
| Video | Moderate | Narrative and FMV links are partially bound; some references and standalone files remain unresolved. |
| Texture assets | High | Texture2D extraction and collision handling are verified by dedicated audits. |
| Models/materials | Moderate | Broad asset indexes and PathID-resolved material/texture relations exist, but semantic entity-level reconstruction is incomplete. |
| Asset bundles | High at VFS layer, partial at per-AB clean-certification layer | Bundle entries are indexed without missing chunks, but older logs cannot certify every AB warning-free. |
| MonoBehaviour/gameplay payloads | Moderate and improving | Large classes of managed-reference payloads are decoded or bounded; remaining incomplete files are concentrated in known schema gaps. |
| Characters/animation | Deep for selected actors, partial game-wide | Wulfa/Zhuangfy/Mifu recovery is substantial; general game-wide animation reconstruction is not solved. |
| Shaders | Moderate for payload extraction, partial for renderer fidelity | DXBC/SMOL-V snippets are extracted and SMOL-V decoding improved; original shader assignment and HLSL decompilation remain incomplete. |
| Update/change tracking | High | The Updates pipeline compares export roots and produces focused game-data changes. |

## Evidence Snapshot

### Current Export Health

The latest export summary points at the installed game root
`D:\Program Files\Endfield Game\Endfield_Data` and current export root
`D:\fluffy-dump\export_full`.

Important extraction signals:

- StreamingAssets source inventory: 794 files, 56.925 GiB.
- Persistent source inventory: 139 files, 1.823 GiB.
- StreamingAssets VFS index: 258,422 files, 32 chunks, 0 missing chunks.
- Persistent VFS index: 261,685 files, 33 chunks, 0 missing chunks.
- Latest asset-mode export reports 0 failed decode entries.
- Latest asset-mode export reports 0 manifest-only missing references.
- StreamingAssets Texture2D matched outputs: 126,496, with 0 missing outputs.
- Persistent Texture2D matched outputs: 5,960, with 0 missing outputs.

This means the current problem is mostly interpretation and reconstruction, not
basic access to packed files.

### Source Graph Scale

The source graph is large enough to support cross-domain investigation:

- Nodes: 756,400.
- Edges: 1,064,312.
- Aliases: 1,184,043.
- Files: 334,269.

Selected node counts:

- Assets: 292,020.
- Audio: 35,151.
- Lines: 39,216.
- Stories: 9,570.
- Options: 4,376.
- Option groups: 2,854.
- Missions: 655.
- Actors: 1,629.
- Videos: 942.
- Table rows: 29,162.

Selected edge counts:

- `indexes_asset`: 292,020.
- `has_line`: 40,863.
- `uses_audio`: 24,738.
- `has_story`: 9,472.
- `has_option`: 5,299.
- `option_enters_story`: 3,039.
- `option_first_line`: 3,037.
- `option_path_line`: 7,168.
- `has_narrative_video`: 320.
- `source_references_story`: 933.
- `has_story_source_link`: 861.
- `uses_texture`: 229,557.
- `uses_material`: 8,450.
- `referenced_by_material`: 190,457.
- `referenced_by_model`: 37,702.

The graph is useful as an evidence index. It should not be mistaken for full
runtime simulation.

### WebUI Corpus Scale

The WebUI manifest currently reports, for CN:

- Conversations: 9,472.
- Actors: 1,315.
- Conversation JSON bytes: 79,942,667.
- Mission data files: 632.
- Mission data bytes: 55,252,484.
- Reference tables: 486.
- Reference rows: 121,150.
- Scene order gap count: 35.
- Narrative video keys: 43.
- Narrative video refs: 150.

The WebUI-facing corpus is therefore broad and usable for story/table browsing.
### Binary Config And Data Format Snapshot

Memory notes show that `StreamingAssets/Data/Json` is not mostly plain JSON.
The current decoded Data scope has:

- Files under `Json/` across StreamingAssets and Persistent: 163,822.
- Parseable text JSON files: 6,070.
- Binary `.json` payloads: 157,752.
- Decoded config bytes: about 1,338.4 MiB.
- Lazy-loaded Data groups: 30.
- Source split: 81,735 StreamingAssets files and 82,087 Persistent files.

The dominant binary families are MemoryPack-like payloads where the first byte
usually matches a top-level member count. Important families include LipSync,
LevelScriptData, NPC montage rows, BuffData, SkillData, LevelData,
AnimationConfig, LevelConfig, InteractiveData, ModelTable, WorldEntityRegistry,
ModelRadiusTable, SpawnerConfig, and several gameplay config tables.

Current understanding is family-specific:

- Some files now parse exactly, including DialogIdTable, ModelTable,
  ModelRadiusTable, InteractiveTable, WorldEntityRegistry, several NavMesh
  containers, selected mission-area and teleport tables, and other small config
  roots.
- Some large gameplay families are partially decoded with verified top-level
  schemas and bounded previews, including BuffData, SkillData, LevelScriptData,
  InteractiveData, AnimationConfig, NPC montage rows, and SpawnerConfig.
- Some nested bodies intentionally remain opaque until byte-level boundaries and
  runtime field meanings are proven.

Non-JSON data also has a clearer census:

- `.bytes`: 38,824, with 38,561 validating as FlatBuffer-like streaming roots.
- `.ab`: 258,422 encoded asset-bundle payloads in the inspected Data root.
- `.mp4`: 464 media files.
- `.pck`: 16 Wwise package files.
- `.bin`: 3 ExtendData binary indexes.
- `.hgmmap`: 1 bundle manifest payload.

### MonoBehaviour And Runtime Payload Snapshot

Memory notes add a current MonoBehaviour inventory under recovered AnimeStudio
JSON:

- MonoBehaviour JSON files: 1,064,294.
- JSON parse errors: 0.
- Top-level metadata-only/raw-data-only fallbacks: 0.
- Files with incomplete markers: 3,644.
- Files with `serializedTypeTreeError`: 3,644.
- Files with `partialTypeTreeDecode`: 1,707.
- Files with heuristic managed-reference recovery: 1,937.

Several focused families have moved from generic raw or heuristic output to
named, byte-bounded structures:

- Character `AbilitySystemData` focused rows now decode parent payloads through
  skill bundles, command mappings, combo conditions, UI data, buff lists,
  entity blackboard, skill camera config, post-camera fields, preload ability
  entities, and potential buff IDs for the validated sample set.
- `EffectActionCfg` in focused `AbilitySystemData.deadEffect` rows is now named
  through the observed 107-word Unity layout, with `centerOffset` omitted in
  that payload shape.
- `TargetSettings` exposes metadata-backed selector/finder/validator RID slots
  while preserving post-selector uncertainty.
- `ProjectileComponentData` focused slices decode prefixes, move-mode
  dictionaries, BezierPoint records, alert-effect sections, and end suffixes;
  effect lists and sound structs remain partial.
- Audio and guide managed-reference payloads that appeared stale in older
  decoded indexes often recover cleanly with the current exporter.

This means runtime-payload understanding is no longer just field-name metadata.
For important focused samples it includes byte-consumed parent records and
named substructures. It is still not a full game-wide proof of every variant.

### Asset-Bundle Certainty Snapshot

The VFS-level bundle picture is strong. Memory notes count 518,131 indexed
`Bundle` AB entries across StreamingAssets and Persistent, with 0 missing
chunks in that VFS layer.

The conservative caveat is per-AB cleanliness. Older AnimeStudio logs were good
for stage-level and object-level counts but did not consistently map every
warning or conversion issue back to a source AB path, offset, and PathID. That
means the project can say the bundle entries are present and indexed, but it
cannot yet issue a complete per-AB certificate of "loaded and decoded without
warnings" for every bundle.

## What We Understand Well

### Raw Game Data Containers

Understanding is strong.

The latest VFS indexes report no missing chunks in either StreamingAssets or
Persistent data. The export summary also shows no failed decode entries and no
manifest-only missing references for the latest asset-mode run. This suggests
the project can reliably enumerate and read the relevant installed game data
needed by the WebUI pipeline.

The current export paths intentionally avoid dumping every raw VFS byte because
the WebUI does not need that. This is a workflow choice, not evidence that the
files cannot be reached.
### Data Format And MemoryPack Families

Understanding is moderate to high, depending on family.

The memory notes substantially improve the interpretation of `Data/Json`.
Many files with `.json` names are binary MemoryPack-like payloads, not failed
text JSON. The project has moved from simple file identification to real schema
recovery for many families.

Strong or exact current examples include:

- `GameplayConfig/DialogIdTable.json`: exact five-member root, 2,258
  `DialogBriefInfo` rows, dialog/option registries, and reverse mappings.
- `GameplayConfig/ModelTable.json` and `NonGeneratedConfigs/ModelTable.json`:
  exact model/layout dictionaries with model ids, prefab paths, scale floats,
  layout keys, and interactive extra data.
- `GameplayConfig/ModelRadiusTable.json`: 1,125 exact model-radius rows.
- `GameplayConfigWorldEntityRegistry.json`: 893 brief entity rows plus config
  property rows.
- `Interactive/InteractiveTable.json`: 271 core-template paths and 917 template
  references, with all referenced template targets verified.
- Several NavMesh, teleport, mission-area, matrix, bamboo-raft, damage-text,
  and small gameplay config roots that consume exactly.

2026-07-01 decoded config graph progress: the source graph now promotes these
exact WebUI Data-index decodes into queryable evidence nodes. The fast CN graph
contains 1,201 unique `model_config_model` rows, 1,125 `model_radius` rows, 271
interactive templates, 923 interactive objects, 542 interactive template-data
nodes, and 893 world entities from the exact MemoryPack families above. This
makes questions such as "which radius row belongs to this model id?", "which
interactive object aliases this template?", and "which world entity uses this
interactive detail or enemy?" answerable from SQLite. The corrected graph now
links `detailId` matches to 66 Gameplay enemy nodes, 66 enemy templates, 3 NPCs,
594 interactive objects, 267 model rows, 267 model-radius rows, 214 audio
collections, and 65 audio dialog channels. A follow-up exact
`TeleportValidationDataTable` graph pass adds 8 validation config nodes, 222
unique teleport points, 444 config-to-point edges, and 106 point-to-level links
across 17 level ids, preserving position, rotation, nullable `mapId`, flag word,
and integer tails. The exact mission-area pass adds 2 mission-area config nodes,
73 unique area rows, 146 config-to-area edges, and 37 prefix-backed links to 9
existing mission nodes. The exact subgame-instance pass adds 2 config nodes, 4
unique subgame instances, 1 default group, 8 config-to-instance edges, 4 group
edges, and 12 failure/quit/success text edges. The bounded `SpawnerConfig` pass
adds 436 unique spawner configs, 1,057 enemy rows, 178 distinct enemy keys, 61
born-buff keys, 23 blackboard keys, 16 prewarn audio-event keys, and 22 prewarn
effect keys while preserving enemy levels, force flags, wave keys, override AI,
born-buff blackboard values, fixed rotations, and prewarn timings. The bounded
`BuffData` pass adds 4,616 file-to-buff definition edges collapsed to 2,325
unique buff ids, 268 gameplay tag strings, 1,254 parameter strings, 779 linked
buff ids, 703 effect keys, 145 audio keys, and 106 icon ids from guarded
length-prefixed string evidence. The bounded `SkillData` pass adds 4,191
file-to-skill definition edges collapsed to 2,108 unique skill ids, 833 linked
buff ids, 311 gameplay tag strings, 3,323 parameter strings, 3,900 effect keys,
3,156 audio keys, and 43 icon ids from the same guarded string evidence plus
post-tail status samples. The LevelScript inventory/reference pass adds 7,414
file-to-script definition edges collapsed to 3,756 unique level scripts, 148
level-folder links, 35 level-script templates, 20 template groups, 3 start types,
120 montage refs, and high-signal string edges for 3,135 story keys, 393
mission-like ids, 683 audio keys, 148 effect keys, 157 buff ids, and 27 template
refs while preserving action-map/list-count totals. The LevelConfig/LevelData
pass adds 290 LevelConfig file edges collapsed to 149 level configs, 1,593
LevelData file edges collapsed to 810 level-data nodes, 149 config-to-level
links, 139 config map-id links, 149 default-scene-config links, 810
level-to-LevelData links, plus bounded LevelData string edges for 303 level
scripts, 360 story keys, 511 mission-like ids, 26 audio keys, 103 effect keys, 5
buff ids, 347 montage ids, 19 asset paths, 4,635 task markers, and 13,370
parameter strings. The NPCMontageJson pass adds 6,800 file-to-montage definition
edges collapsed to 3,392 unique montage tags, plus 2 montage categories, 47
bodies, 1,078 actions, and category/body/action edges for each defined montage
tag. The `AnimationConfig` pass adds 213 file-to-config definition edges
collapsed to 107 config nodes, 584 states, 315 facial morph paths, 197 actor
animation refs, 3 cutscene-like refs, 34 montage refs joined to existing
montage nodes, and 1 generic skeleton/bone path ref from guarded MemoryPack
string evidence; controller graphs, blend trees, clip bindings, animation
curves, and runtime playback conditions remain outside this pass. The
`AtmosphericNpcData` pass adds 15,452 file-row occurrence edges collapsed to
7,760 atmospheric NPC row aliases on `environmental_npc` nodes, with 7,760
template links, 7,760 level links, 7,577 AI-config links, 4,866 montage links,
2,427 facial-morph links, 994 cluster links, and 615 envTalk links from the
same bounded row-string evidence. The `CharInteractPerformCfgs` pass adds 318
file-to-config definition edges collapsed to 159 perform configs, with 83 exact
active-tag edges, 54 status-tag refs, 102 montage refs, 37 actor/template refs,
146 effect refs, 46 intra-family perform refs, 52 asset-path refs, and 13 CCS
refs from a strong parsed prefix plus bounded body string evidence. The
`DialogIdTable` registry pass adds exact runtime registration evidence for
4,918 scenes, 3,589 line ids, and 4,131 option ids. The
`InteractiveTemplateData` pass adds 3,234 source-qualified component nodes, 79
component-type nodes, 296 property-key nodes, 33 logic-type nodes, 574 category
tag edges, 418 model edges, 488 raw-byte audio edges, and exact component links
for first/payload/stop components, trigger/guide shapes, and selected property
maps. The InteractiveData collection pass adds 935 collection ids, 1,843
Persistent/StreamingAssets source-file definition edges, and 935 collection-to-level
links across 214 level ids while leaving the 21-element `totalCnt` arrays
uninterpreted. The `ModelViewStateControllerData` pass adds 399 model-view
controller nodes, 798 source-file definition edges, 582 clip-ref nodes, 750
animator-name nodes, 923 exact clip edges, 823 animator-body clip refs, 619
exact effect-id edges, and 872 animator-body effect refs; the config-model to
asset-entity join remains 0 for this family. The `Json_NavMesh` pass adds exact
MemoryPack graph evidence for 139 LunaArea polygon rows, 17 owner-qualified
area ids, 6 NavMeshStateContainer owners, 569 state rows, and 57 bounds-to-area
id refs across Persistent/StreamingAssets copies. The `BambooRaftTaskTable` pass
adds exact graph evidence for 7 task-group hashes, 13 quest task ids, 26
source-file task refs, and 13 mission-prefix links. The `damage_text` pass adds
20 UI combat-text style rows, 10 animation refs, 58 UI node names, and 8
filtered `ui_*` resources. The `LipSync` pass adds 64,920 aggregate
language/audio clip nodes from 129,732 source entries and links every clip to an
audio stem. The `MissionRuntimeAsset` pass adds 884 mission runtime/meta assets,
3,984 quest-task links, 3,334 previous-quest dependencies, 3,155 objective text
links, condition/tracking/action type nodes, and exact mission-area and
narrative refs. The `AIConfig/EnemyTemplateDataSummary` pass adds 78
enemy data asset path nodes from 156 Persistent/StreamingAssets source
mappings, 156 file-to-template preload edges, and 78 deduplicated
template-to-asset preload edges. The `MapConfig` pass adds 139 map-config
nodes, 197 unique numeric level-id edges with 31,992 grid-cell counts kept
as payload data, 149 string level links, 99 scene states, 39 map variables,
and exact quest/mission/map-variable condition refs. The
`GameplayConfigScriptTaskExtraInfoTable` pass adds 4 level-script task
extra nodes, one level link set, and 5 task title/objective text refs. The
`LevelMountPoint` pass adds 92 level-qualified mount leaves, 7 mount types,
and exact position/rotation payloads for `base01_lv001` and `base01_lv003`.
The `LevelGenForRuntime` pass adds 267 doodad groups, 1,967 doodad logic
ids, 68 runtime factory regions, 202 mine nodes, and exact mine output item
refs. The `UILevelMapLoadConfig` pass adds 17 UI map configs, 220 static map
elements, 58 tier names, target-level refs, and UI text refs. The
`GameplayConfig` map/level lookup pass adds 149 level-basic-info rows, 21
short-id scenes, 86 short-id rows, 142 map-brief rows, 211 map-local sublevel
rows, and 1,009 sublevel enemy refs from the decoded text JSON tables. The
placed-map pass adds 1,993 map-mark nodes, 268 map regions, 46 mine-team nodes,
and high-confidence mark-to-level, mark-to-region, teleport, reward, item,
activity, minigame, and doodad logic refs. The text `WorldEntityRegistry` pass
adds 15,083 placed world-entity instances, 2,591 script slots, 77 config nodes,
154 config properties, 1,646 NPC proxy briefs, and exact detail/script joins to
existing entity and level-script nodes.
These decoded-config passes still do not prove runtime formula usage,
full SpawnerConfig tail semantics,
BuffData timeline action execution, SkillData target/action execution,
LevelScript action-body control flow, LevelData object placement or control
flow, montage clip playback semantics, full exported model/icon reconstruction,
or runtime proof for effect asset dependencies. A strict suffix-normalized
gameplay-effect-to-asset name-match now exists for a small slice, but the lean
asset-index entity join for config model IDs is still empty.

Partial but useful current examples include:

- `BuffData`: queryable buff definitions plus bounded string-reference edges for
  visible tags, parameters, linked buffs, audio, effects, and icons; top-level
  schema, id verification, and selected prefix/tail values remain evidence, not
  runtime formula proof.
- `SkillData`: queryable skill definitions plus bounded string-reference edges
  for visible tags, parameters, linked buffs, audio, effects, and icons; strict
  id rows, switch-tail status, target/buff settings, and UI range hints remain
  evidence, not runtime action or targeting proof.
- `LevelScriptData`: queryable script/template inventory across 7,414 files and
  3,756 unique script ids, including level ownership, start types, action-map
  counts, UID counts, list-count summaries, and high-signal story/audio/effect/
  buff/template/montage references; generic keys, per-action bodies, and control
  flow remain bounded future work.
- `LevelConfig`/`LevelData`: queryable level config/data inventory across 290
  config files and 1,593 data files, including config-to-level/map/default-scene
  links, level-to-data ownership, and bounded string references for scripts,
  story keys, missions, audio, effects, buffs, montages, task markers, params,
  and asset paths; object placement and control-flow semantics remain future
  work.
- `NPCMontageJson`: queryable montage-tag definitions across 6,800 files and
  3,392 unique tags, including category, body, and action metadata joined onto
  the same montage nodes referenced by LevelScript and LevelData; animation clip
  payloads and playback rules remain future work.
- `AnimationConfig`: queryable config definitions across 213 files and 107
  unique configs, with bounded string-scan references to state names, facial
  morph paths, montage paths, actor animation refs, cutscene-like ids, and one
  skeleton/bone path; controller graphs, blend trees, clip bindings, animation
  curves, and runtime playback conditions remain future work.
- `AtmosphericNpcData`: queryable atmospheric/environmental NPC row inventory
  across 276 decoded tables, including row-to-template, level, AI config,
  montage, facial morph, cluster, and envTalk references; full row payloads,
  coordinates, placement volumes, behavior trees, schedules, and playback timing
  remain future work.
- `CharInteractPerformCfgs`: queryable common-interaction perform configs across
  318 decoded files and 159 unique perform ids, including active/status tags,
  montage refs, character/NPC-template refs, effects, inherited perform configs,
  asset paths, and CCS paths; action dictionaries, timing, IK/follow rules,
  interrupt behavior, and runtime interaction state machines remain future work.
- `Interactive/InteractiveData`: queryable template/component inventory across
  542 decoded source files and 271 template ids, including exact component
  nodes, component-type links, category tags, model ids, raw-byte audio refs,
  property keys, logic types, trigger shapes, guide shapes, trigger observers,
  common perform data, hittable data, and selected property maps; the separate
  Collections JSON now contributes 935 collection ids and level links across 214
  level ids, while component execution/control flow, numeric enum meaning, and
  `totalCnt` counter semantics remain future work.
- `ModelViewStateControllerData`: queryable model-view controller inventory
  across 798 decoded source files and 399 model ids, including model links,
  exact clip/effect refs, bounded animator-body clip/effect refs, animator-name
  refs, and `preTickAnimator` payload evidence; animator state machines,
  transitions, timing, camera/emissive hash meaning, and asset-entity joins
  remain future work.
- `Json/NavMesh`: queryable LunaArea polygon rows and NavMeshStateContainer
  rows for six owners, with owner-qualified area-id links and level/map owner
  links; numeric bounds/list evidence is preserved without inferring navigation
  behavior or walkability.
- `BambooRaftTaskTable`: queryable bamboo-raft task-group hashes and 13 exact
  quest task ids, with mission-prefix links such as `e8m2_q#10` to `e8m2`;
  hash meaning, quest order, and task execution remain future work.
- `GPUISystemConfig/damage_text`: queryable UI combat-text style rows,
  animation refs, UI node names, and filtered `ui_*` resource refs; numeric
  placeholders, text samples, prefab hierarchy, and runtime rendering behavior
  remain future work.
- `LipSync`: queryable aggregate language/audio clip nodes across Chinese,
  English, Japanese, and Korean, linked back to audio stems; per-record curve
  nodes, phoneme/viseme meaning, and timing semantics remain intentionally out
  of scope.
- `MissionRuntimeAsset`: queryable mission runtime/meta assets, quest task DAG
  edges, previous-quest dependencies, objective text refs, condition/tracking
  type refs, level/reward links, and narrative refs; this is static authored
  mission evidence, not observed runtime chronology or condition evaluation.
- `AIConfig/EnemyTemplateDataSummary`: queryable enemy-template preload
  mappings for 78 template ids to exact `EnemyData/*.asset` paths, with
  Persistent/StreamingAssets source-file evidence; these are preload path
  refs, not full AI behavior, behavior-tree, or renderable model bindings.
- `MapConfig`: queryable map config nodes for 139 map ids, including
  domain names, streaming map asset paths, unique numeric/string level links,
  scene states, map variables, and quest/mission/map-variable condition
  refs; grid placement, streaming behavior, state evaluation, and UI map
  rendering remain future work.
- `GameplayConfigScriptTaskExtraInfoTable`: queryable task-extra display
  metadata for four `map01_lv007` level-script tasks, including task title
  and objective text refs; runtime challenge execution and progress logic
  remain future work.
- `LevelMountPoint`: queryable static mount leaves for `base01_lv001` and
  `base01_lv003`, with mount type, tree path, position, and rotation
  payloads; runtime attachment rules, cabin interaction behavior, and
  display/spawn usage remain future work.
- `LevelGenForRuntime`: queryable static factory generation data, including
  parent data ids, doodad groups, center/outer doodad logic ids, runtime
  factory regions, mines, mine proto ids, mine output items, and map-mark
  refs; resource refresh formulas, gathering logic, factory simulation, and
  map-mark visibility remain future work.
- `UILevelMapLoadConfig`: queryable UI map config nodes, static map
  elements, static-element types, tier names, target-level refs, and text
  refs; chunk/grid/mist geometry, LOD selection, coordinate projection, and
  actual UI rendering remain future work.
- `LevelScriptTemplateData` and other partially previewed families have verified
  top-level ids/counts and meaningful previews.

The remaining risk is nested semantics. A decoded field name or count proves
structure; it does not automatically prove gameplay meaning, formula behavior,
or runtime control flow.

### WebUI Story and Text Corpus

Understanding is strong at the corpus/display level.

The CN WebUI output contains thousands of conversation files, hundreds of
mission data files, over one hundred thousand reference rows, actor metadata,
audio links, source links, and narrative video references. The generated
source graph links lines, stories, options, missions, actors, audio, videos,
selected table rows, and exact DialogText/DialogOption/Summary support-table
evidence.

The current system is good at answering questions such as:

- Which dialog lines exist?
- Which actor is attached to a line?
- Which audio file or event is used by a line?
- Which mission or story key references a dialog scene?
- Which option groups exist?
- Which source file appears to back a story key?
- Which table rows and text IDs are visible to the WebUI?
- Which raw DialogText/DialogOption/Summary rows support a generated line,
  option, or story?

2026-07-01 source graph dialog-support progress: a fast CN rebuild verified
1,026,124 graph nodes and 1,698,548 edges after adding exact support-table
semantics for DialogText, DialogOption, DialogSummary, DialogSummaryMap, and
DomainDepotDeliverTargetDialog. The pass adds 17,528 `dialog_text`, 4,343
`dialog_option`, 997 `dialog_summary`, 931 `dialog_summary_map`, and 15
`domain_depot_deliver_target_dialog` nodes, with 0 orphan edges from those
sources. It links all 17,528 dialog text rows to generated line nodes and
generated WebUI story ownership, 17,329 to non-sentinel audio, 15,337 to
actors, 4,219 dialog options to generated option nodes, 908 summary maps to
story nodes, and all 30 domain-depot initial/repeat dialog refs to story nodes.
The graph no longer emits the `audio:0` sentinel as an audio node or edge
target.

2026-07-01 source graph DialogIdTable registry progress: a fast CN rebuild to
`tmp/source_graph_dialog_registry.sqlite` verified runtime registry evidence
from exact `DialogIdTable` decoding and the generated dialog registry JSON. The
pass adds 1 `dialog_id_table_config` node, 2 decoded source-file definition
edges, 4,918 `dialog_registry_scene` nodes, 4,918 registry-to-story links, 3,589
registered line links, 4,131 registered option links, and matching line/option
to-story edges. This proves runtime registration structure for scenes, trunks,
lines, and options; it does not supersede generated WebUI line order,
scene-graph option placement, or timeline route evidence.

2026-07-01 source graph NavMesh progress: a fast CN rebuild to
`tmp/source_graph_navmesh.sqlite` verified exact decoded NavMesh evidence from
`Json_NavMesh.json`. The pass adds 139 `navmesh_area` polygon rows, 17
owner-qualified `navmesh_area_id` nodes, 6 `navmesh_state_container` owners,
569 `navmesh_state_record` rows, 278 area source-file definition edges, 1,138
state-record source-file definition edges, and 57 bounds-to-area-id refs. This
proves decoded geometry/state inventory by NavMesh owner; it does not infer
walkability, pathfinding behavior, or numeric state/list semantics.

2026-07-01 source graph BambooRaftTaskTable progress: a fast CN rebuild to
`tmp/source_graph_bamboo.sqlite` verified exact decoded task references from
`Json/NonGeneratedConfigs/BambooRaftTaskTable.json`. The pass adds 7
`bamboo_raft_task_group` hash nodes, 13 `quest_task` nodes, 14 group source-file
definition edges, 26 task-ref source-file definition edges, 13 group-to-task
edges, and 13 mission-prefix links across `e5m1`, `e6m1`, `e6m4`, `e8m2`,
`sm2l1m1`, and `sm2l1m3`. It preserves hash/field payload evidence without
inferring quest order or bamboo-raft gameplay mechanics.

2026-07-01 source graph GPUISystemConfig damage_text progress: a fast CN
rebuild to `tmp/source_graph_damage_text.sqlite` verified exact UI combat-text
row evidence from `Json/GPUISystemConfig/damage_text.json`. The pass adds 20
`damage_text_style` row nodes, 10 `damage_text_animation` nodes, 58
`damage_text_node_name` nodes, 8 filtered `damage_text_ui_resource` nodes, 40
row source-file definition edges, 22 animation refs, 143 node-name refs, and 23
`ui_*` resource refs. Numeric placeholders and non-`ui_*` strings remain
payload-only evidence; the graph does not infer UI prefab hierarchy or runtime
rendering behavior.

2026-07-01 source graph LipSync aggregate progress: a fast CN rebuild to
`tmp/source_graph_lipsync.sqlite` verified aggregate clip evidence from the
large `Json_LipSync.json` group. The pass adds 129,732 source-file definition
edges collapsed to 64,920 `lipsync_clip` language/audio nodes, 4 language nodes,
64,920 language edges, and 64,920 audio-stem links. Language splits are Chinese
16,248, English 16,224, Japanese 16,223, and Korean 16,225 unique clips. Source
entries sum to 43,043,103 curve records and unique clip nodes sum to 21,553,022
records after source collapse; per-record curve nodes and phoneme/viseme timing
semantics remain intentionally out of scope.

2026-07-01 source graph MissionRuntimeAsset progress: a fast CN rebuild to
`tmp/source_graph_mission_runtime.sqlite` verified static mission runtime JSON
semantics from `Json_MissionRuntimeAsset.json`. The pass adds 884
`mission_runtime_asset` nodes, 1,756 source-file definition edges, 884
asset-to-mission links, 813 level links, 494 reward links, 331 mission-name text
links, 324 mission-description text links, 3,984 mission quest links, 3,334
previous-quest dependencies, 3,155 objective text links, 55 condition-type
nodes, 7 tracking-type nodes, 6 action-type nodes, 1,134 mission-area tracking
links, 345 action narrative refs, and 579 quest narrative refs. It is strong
static quest DAG and authored tracking evidence; it does not prove observed
runtime chronology, condition evaluation, action execution, or exact
player-visible mission order.

2026-07-01 source graph AIConfig progress: a fast CN rebuild to
`tmp/source_graph_aiconfig.sqlite` verified exact enemy-template preload
mappings from `Json_AIConfig.json` `EnemyTemplateDataSummary.json`. The pass
adds 78 `enemy_data_asset` nodes, 156 file-to-template preload edges split as
Persistent 78 and StreamingAssets 78, 78 deduplicated template-to-asset
preload edges, and 78 path plus 78 stem aliases. This is static preload-path
evidence only; it does not prove AI behavior trees, spawn behavior, renderable
model binding, or asset presence in the lean asset index.

2026-07-01 source graph MapConfig progress: a fast CN rebuild to
`tmp/source_graph_mapconfig.sqlite` verified exact map config JSON from
`Json_MapConfig.json`. The pass adds 139 `map_config` nodes, 270
source-file definition edges, 139 config-to-map links, 48 domain nodes, 68
streaming map asset path nodes, 197 unique numeric level-id edges, 149
string level links, 99 scene-state nodes, 39 map variables, 4 condition
types, 32 quest condition refs, 5 mission refs, and 9 map-variable refs.
The original 31,992 `levelIds` grid entries are preserved as counts on
config node payloads rather than emitted as per-cell edges. This is static
authored map metadata, not proof of streaming behavior, condition evaluation,
grid placement semantics, or UI map rendering.

2026-07-01 source graph script-task extra progress: a fast CN rebuild to
`tmp/source_graph_script_task_extra.sqlite` verified the small
`GameplayConfigScriptTaskExtraInfoTable` pass. It adds 4
`level_script_task_extra` nodes, 8 source-file definition edges, 4 level
links to `map01_lv007`, 1 task-title text link, and 4 objective text links.
This is static display/tracking metadata, not proof of level-script
execution, objective progress logic, or runtime challenge state.

2026-07-01 source graph LevelMountPoint progress: a fast CN rebuild to
`tmp/source_graph_level_mount_point.sqlite` verified exact static mount
leaves from `Json_LevelMountPoint.json`. It adds 92 `level_mount_point`
nodes, 184 source-file definition edges, 92 level links split across
`base01_lv001` and `base01_lv003`, 7 mount-type nodes, and 92 type links.
Each mount point keeps its level-qualified tree path plus position and
rotation payloads. This is static authored transform data, not proof of
runtime attachment rules, cabin interaction behavior, or display/spawn usage.

2026-07-01 source graph LevelGenForRuntime progress: a fast CN rebuild to
`tmp/source_graph_level_gen.sqlite` verified exact static factory
generation data from `Json_LevelGenForRuntime.json`. It adds 70 parent data
nodes, 267 doodad groups, 1,967 doodad logic ids, 68 runtime factory
regions, 202 mines, 4 mine proto ids, 202 mine output item links, 267 center
links, 1,700 outer links, and 56 doodad map-mark links. This is static
authored generation metadata, not proof of resource refresh formulas,
gathering logic, factory simulation behavior, or map-mark visibility.

2026-07-01 source graph UILevelMapLoadConfig progress: a fast CN rebuild
to `tmp/source_graph_ui_level_map.sqlite` verified bounded UI map-load
metadata from `Json_UILevelMapLoadConfig.json`. It adds 17
`ui_level_map_config` nodes, 220 static map elements, 7 static-element
types, 54 target-level refs, 2 region-level refs, 157 static-element text
refs, 58 tier-name nodes, and 58 tier text refs. Chunk/grid/mist and tier
geometry arrays are payload counts only; this is static UI map metadata,
not proof of UI map rendering, fog/mist reveal behavior, chunk LOD
selection, or coordinate projection.

2026-07-01 source graph GameplayConfig map/level lookup progress: a fast CN
rebuild to `tmp/source_graph_gameplay_map_level.sqlite` verified four decoded
text JSON lookup tables from `Json_GameplayConfig.json`. The pass adds 270
source-file map-id definition edges, 149 `level_basic_info` nodes with level,
level-config, domain, map-UI, region-UI, and factory-area links, 21 short-id
scene nodes plus 86 `level_short_id` nodes, and 142 `map_brief_info` nodes
with 211 map-local sublevel nodes and 1,009 enemy refs. Numeric
`MapBriefInfoTable` map ids only join to `map` nodes through `MapIdTable`, and
sublevel ids are preserved as map-local subdata ids rather than inferred level
ids. Placed map marks, map regions, and mine teams remain a separate pass.

2026-07-01 source graph GameplayConfig placed-map progress: a fast CN rebuild
to `tmp/source_graph_gameplay_map_placement.sqlite` verified decoded
`LevelMapMark`, `MapRegionTable`, and `MinePointTeamTable` text JSON. The pass
adds 1,993 unique map-mark nodes from 3,915 source rows, 268 map-region nodes,
46 factory mine-team nodes, 1,877 region-derived level-to-mark links, 1,803
mist-region links, 884 tier-region links, 79 teleport refs, 42 reward refs, 109
item refs, 103 minigame refs, 300 mark core-doodad refs, and 150 mine-team
doodad refs. Geometry remains payload-level, and the top-level numeric keys are
not treated as map ids. This is static placed-map evidence, not proof of live
visibility, activation, fog reveal, resource refresh, or runtime map rendering.

2026-07-01 source graph text WorldEntityRegistry progress: a fast CN rebuild to
`tmp/source_graph_world_entity_text.sqlite` verified decoded text
`Json/GameplayConfig/WorldEntityRegistry.json`. The pass adds 15,083 collapsed
world-entity instance nodes from 30,129 source rows, 2,591 script-slot nodes,
77 config nodes, 154 config-property nodes, 1,646 NPC proxy briefs, and 1,646
segment nodes. It links instances and script slots to existing enemy,
enemy-template, interactive-detail, model, model-radius, audio, and level-script
nodes where exact detail or script ids already resolve. Position, rotation, and
config values remain payload-level, and numeric prefixes are not treated as
level or map ids. This is static registry evidence, not proof of runtime spawn,
visibility, lifetime, or script execution.

Useful support-table checks include:

```bat
python tools\endfield_source_graph.py query dlg_a1m10_1_001 --kind dialog_text
python tools\endfield_source_graph.py query dlg_spaceship_creditshop_trade --kind dialog_option
python tools\endfield_source_graph.py query summary_a1m2_1_001 --kind dialog_summary
python tools\endfield_source_graph.py query dlg_a1m2_1 --kind dialog_summary_map
python tools\endfield_source_graph.py query ahe_map02_v1d2d0_depot --kind domain_depot_deliver_target_dialog
```

### Line Order Inside Dialog Scenes

Understanding is strong for most scenes.

The latest scene-order gap report flags only 35 CN `dlg_*` scenes:

- Missing line-order block: 0.
- Partial authored line order: 6.
- Fallback line order: 0.
- Inferred option placement: 15.
- Inferred option response: 14.

This is much better than earlier audits. An older line-order recovery report
targeted 2,418 scene files and found explicit line order for 2,343 scenes
while leaving 0 multi-line scenes unresolved. That older report should not be
treated as the current gap source, but it supports the conclusion that basic
line ordering is largely solved.

The residual raw recovery problem is concentrated in option placement and response
inference, not broad line ordering failure. The option override coverage audit
validates all 40 generated option warning units as manually covered for WebUI
display, with 0 invalid override references. This does not prove runtime branch
semantics by itself.

### Texture Extraction

Understanding is strong.

Texture2D extraction is supported by dedicated collision reports:

- Texture2D raw-hash collision audit groups: 9.
- Collision entries: 362.
- Missing outputs: 0.
- Export errors: 0.
- Isolated verification checked all 362 collision entries.
- Expected PNG SHA-256 matches: 362.
- Mismatches: 0.
- Missing verified outputs: 0.

The latest export summary also reports:

- StreamingAssets Texture2D matched outputs: 126,496 / 126,496.
- Persistent Texture2D matched outputs: 5,960 / 5,960.

For WebUI purposes, texture extraction and collision disambiguation look
reliable.
Memory notes further tighten this conclusion. The remaining Texture2D
collision family is now understood as repeated source identities that decode to
byte-identical PNG output for the same exported asset identity. Refreshed status
manifests report dirty Texture2D source groups as 0 for both StreamingAssets and
Persistent, while preserving same-asset reference evidence in the status JSON.

### Asset Discovery and Indexing

Understanding is strong at file/index level.

The WebUI asset index reports:

- Total asset entries: 292,020.
- Images: 158,259.
- Models: 64,987.
- Videos: 942.
- JSON: 67,832.
- Relation records: 84,103.
- Material JSON records with texture links: 48,470.
- Resolved texture links: 190,457.

This is enough to search and browse a broad slice of exported game assets. The
source graph also indexes 292,020 asset nodes, which matches the active full
asset index scale. The limitation is semantic mapping. Many assets are known as
exported files, path IDs, type buckets, or recovered paths. Fewer are known as fully explained
game concepts such as "this exact model is used by this mission prop in this
runtime scene with this material variant and this animation state".

### Audio Linkage

Understanding is strong for story-facing audio.

The source graph includes:

- Audio nodes: 35,320.
- `audio_path` edges: 25,245.
- `defines_audio` edges: 25,245.
- `speaker_channel` edges: 25,245.
- `uses_audio` edges: 24,738.
- `radio_line_uses_audio` edges: 4,103.
- `remote_common_line_uses_voice` edges: 284.
- `audio_voice_extra_for_audio` edges: 25,245.
- `audio_cue_handler_uses_event` edges: 221.
- `text_voice_id_uses_audio` edges: 153.
- `audio_vo_tone_has_variant_audio` edges: 291.
- `audio_sequence_dialog_uses_audio` edges: 100.
- `audio_factory_uses_event` edges: 240.
- `audio_item_drag_drop_uses_event` edges: 146.
- `audio_level_uses_event` edges: 105.

The WebUI build also post-processes generated conversation JSON with playable
`audioSrc` links. This makes the story audio experience usable and gives a
solid evidence base for line-to-audio investigation.

2026-07-01 source graph narrative/audio progress: a fast CN rebuild verified
939,999 graph nodes and 1,532,614 edges after adding semantic ingestion for SNS,
radio, remote-common, audio cue, emotion voice, audio dialog custom event, and
AudioVoiceExtraData tables. The new slice adds 122 `sns_chat`, 108 `sns_topic`,
1,284 `sns_option`, 288 `sns_dialog`, 5,684 `sns_content`, 2,375 `radio`, 4,103
`radio_line`, 30 `remote_common`, 284 `remote_common_line`, 175 `audio_cue`, 264
`audio_cue_handler`, and 25,245 `audio_voice_extra` nodes, with 0 orphan edges
from those sources. SNS content is preserved as raw table content rather than
forced into generated story line IDs; radio lines, remote lines, and matching
voice-extra keys link to generated `line` nodes where the WebUI story corpus has
them. Useful checks include:

```bat
python tools\endfield_source_graph.py query sns_a1m1_1 --kind sns_dialog
python tools\endfield_source_graph.py query option_sns_a1m1_1_1_001 --kind sns_option
python tools\endfield_source_graph.py query radio_a1m6d1_1 --kind radio
python tools\endfield_source_graph.py query remotecomm_c13m2_1 --kind remote_common
python tools\endfield_source_graph.py query -1000413093 --kind audio_voice_extra
```

2026-07-01 source graph audio-config progress: a follow-up fast CN rebuild
verified 942,880 graph nodes and 1,538,834 edges after adding support/config
semantics for TextVoId, voice tone groups, speaker weights, battle/factory/item
SFX tables, factory announcements, and level audio settings. The pass adds 180
`text_voice_id`, 115 `audio_vo_tone`, 38 corrected `audio_sequence_dialog`, 571
`audio_item_drag_drop`, 73 `audio_factory`, and 103 `audio_level` nodes, among
others, with 0 orphan edges from those sources. `AudioSequenceDialog` now links
38 sequence records to responsive responses and 100 sequence entries to
`AudioDialog` rows, audio nodes, and generated line nodes where present instead of collapsing under a single `audio_sequence:sequence`
node. Useful checks include:

```bat
python tools\endfield_source_graph.py query black_a1m6d2_3_001 --kind text_voice_id
python tools\endfield_source_graph.py query -1008092446 --kind audio_vo_tone
python tools\endfield_source_graph.py query audio_sequence_dialog:1:-1043173561
python tools\endfield_source_graph.py query air_dancer_1 --kind audio_factory
python tools\endfield_source_graph.py query base01_lv001 --kind audio_level
```

Remaining audio improvements are now mostly about deeper Wwise/runtime behavior,
tone/voice intent classification, and coverage validation outside story voice,
not basic line playback, raw communication-table bridging, or basic
support/config table linkage.

### Updates and Change Tracking

Understanding is strong for exported-data deltas.

The latest game-data change summary reports:

- Files scanned: 7,499.
- Added: 8.
- Modified: 139.
- Deleted: 0.
- Metadata-only updates: 7,352.

The update scan is focused on export roots, not repo files. It tracks the
exported JSON roots that feed Story/Text Tables plus exported image/model/video
assets and decoded audio. This is the correct model for the WebUI Updates tab:
game-data changes only, not local report or WebUI implementation churn.

## What We Understand Partially

### Option Branching and Response Routes

Understanding is moderate.

The WebUI represents option groups and option paths, and the source graph has
thousands of option-related edges. However, some option branches are still
inferred rather than proven by direct runtime evidence.

Relevant current reports:

- Latest scene-order gap report: 15 inferred option placement scenes and 14
  inferred option response scenes.
- Option override coverage audit: 40 option warning units audited, all 40
  manually covered by `webui/overrides/options.json`, with 0 invalid override
  references.
- Runtime jump option route audit: 20 inferred option groups audited.
- Nearby Runtime Jump Track clips: 3.
- Complete forward optionIndex coverage: 1.
- Runtime Jump path evidence: 2.
- Contradictions with current inferred first line: 2.
- No remaining inferred group passes strict automatic promotion.

Audio evidence supports many inferred response groups:

- Live inferred option response groups: 20.
- Monotonic by Timeline start: 19.
- Monotonic by AudioDialog key: 15.
- All candidates after anchor on timeline: 19.
- Candidate speaker consistent: 13.
- Candidates share anchor timeline asset: 20.

2026-07-01 WebUI progress: ResponsiveDialog/AIBark fallback conversations now
preserve matching `AudioDialog.path` evidence on generated line payloads as
`audioPaths` and singleton `audioPath`. The audio relinker accepts those scalar
or list-valued fields, including under `_debug.source`, so recovered bark lines
can resolve to decoded audio without needing a separate explicit `audio` id.
A CN rebuild found 959 responsive lines with `audioPaths`, all 959 linked to
`audioSrc`, with no multi-path rows in the current export.

That is useful supporting evidence, but it is not the same as full branch proof.
The current representation is practical and mostly coherent, but not fully
authoritative for every branch.

Memory notes explain the current promotion rule more precisely: timeline/audio
monotonicity is supporting evidence only. Option responses should be promoted
only when authored source evidence binds option indices to response lines. The
next runtime target is the writer of the `DialogOptionPlayableAsset` active
clip gate at `+0x18`; without that, several option-response groups remain
inferred rather than proven.

2026-07-01 source graph progress: `webui/overrides/options.json` is now ingested
as explicitly WebUI-only `option_override` evidence. The fast CN build verified
43 override nodes and 587 `webui/option_override` edges, including manual
response `option_first_line` / `option_path_line` edges that keep their
`webuiOnly` marker in edge data. This improves auditability of display fixes,
but it still does not upgrade manual overrides into original game-source proof.

2026-07-01 option-branch audit progress:
`scripts/story_recovery/build_option_override_branch_conflict_audit.py` now
writes generated reports under `reports/source_graph/` that classify every
manual response option as matching inferred first-line evidence, conflicting
with it, or manual-only. The current audit verifies 74 manual response options:
26 match inference, 24 conflict with inferred first lines, and 24 are
manual-only. Runtime-jump evidence is still sparse, but the join highlights
`dlg_e6m1_10` and `dlg_e6m4_14` as high-signal conflicts where nearby Runtime
Jump evidence supports the manual first line over the old inferred edge. The
`story` source graph query now carries the same distinction inline by tagging
manual override branch refs as `manual_authoritative`, `option_branch_risk` refs
as `diagnostic_inference`, and timeline-derived refs as runtime evidence;
conflicting `option_first_line` refs name the opposing manual or inferred
first-line IDs.

### Mission Timeline and Global Story Order

Understanding is moderate at structural level and weaker at exact runtime
order level.

The mission timeline recovery report uses source-backed evidence only and
avoids filename/numeric suffix fallback chronology. It reports:

- Missions: 436.
- Quests: 3,897.
- Branch points: 122.
- Missions with dialog timeline evidence: 24.
- Source-backed scene edges: 191.
- Source-backed scene sequences: 76.
- Source-backed story-call contexts: 1,011 across 153 missions.
- Source-backed hash terminals: 893 across 141 missions.
- Scene placement entries: 4,561.
- Missing dialog timeline evidence: 405.

This is enough to establish many local relationships, but not enough to
guarantee exact user-visible order across all mission and gameplay states.

The OCR workflow helps by comparing against observed gameplay:

- OCR reports used: 71.
- Corpus lines: 49,717.
- Accepted OCR segment matches: 64,009.
- OCR proposal missions: 66.
- OCR proposal keys: 1,506.
- Score distribution is heavily concentrated in the 0.95-1.00 band.

However, the main-story order comparison still shows large divergence between
rough static recovery and OCR/manual override:

- Main-story missions compared: 58.
- Shared rows: 1,910.
- Strict inversions: 13,761 / 43,244 pairs, or 31.82%.
- Coarse inversions: 1,610 / 9,834 comparable pairs, or 16.37%.
- Highly divergent missions: 54.

This means static evidence can build a useful mission graph, but exact observed
gameplay order still needs manual/OCR/runtime evidence for many clusters.
Memory notes make the static boundary explicit. The strongest mission-local
ordering source is the `MissionRuntimeAsset` quest DAG joined to story refs,
NPC proxies, cutscenes, SNS, radio, remote comm, and LevelScript gates.
Filename suffixes, VFS order, generated WebUI order, and raw file order are not
chronology evidence by themselves.

The e0m0 and Project C notes show the ceiling for static recovery. Spatial
rules, trigger-volume proximity, content-suffix proximity, LevelScript header
chains, and source-backed script clusters can reduce mismatch and prove
membership, but they cannot recover full runtime chronology for boss/phase
clusters where gameplay or server event state chooses playback order. The q11
boss cluster is the clearest example: the same script owns many play actions,
but action-list order, byte order, numeric suffix order, header/getter order,
and observed runtime interleave disagree. Without runtime writer-side evidence,
manual/OCR-observed order must remain a separate evidence class.

### Narrative Video and FMV Binding

Understanding is moderate.

The narrative video report says:

- Video files scanned: 170.
- Attached WebUI keys: 43.
- Attached video refs: 150.
- Timeline-backed evidence rows: 56.
- Standalone video files: 59.
- Standalone video refs: 170.
- Manual inline attach refs: 16.
- Suppressed inline refs: 2.
- Unresolved video refs: 18.

The FMV binding report is narrower and focuses on authoritative `cs_video` and
FMV links:

- FMV IDs total: 29.
- Timeline-resolved scene links: 28.
- Video files scanned: 170.
- Bound files in that FMV scope: 60.
- Unbound files in that FMV scope: 110.

Together, these reports show good but incomplete video understanding. Many
important narrative links are attached, but standalone videos and unresolved
refs need more classification.

### Text Tables and I18n Coverage

Understanding is high for extraction and partial for completeness/meaning.

The CN i18n reference reports show:

- Source IDs across both i18n tables: 111,298.
- IDs surfaced by `build_story` output: 109,992.
- Leftover CN IDs after subtraction: 1,306.
- Leftovers found in JSON: 1,151.
- Leftovers not found in JSON: 155.
- JSON files containing leftovers: 76.

The biggest leftover clusters are not primarily core story dialog. They are
mostly UI, tutorial, attribute, tag, setting, task, and system-style tables,
including:

- `DungeonCharTutorialStepTable`.
- `CharacterTagDesTable`.
- `AttributeShowConfigTable`.
- `SettingTabTable`.
- `TagDataTable`.
- `BattlePassTaskLabelTable`.
- `QualitySubSettingOptionTable`.
- `SettlementTagTable`.
- `QualitySubSettingTable`.
- `ActivityTagTable`.
- `AttributeFilterTable`.

This suggests the story/text pipeline captures nearly all high-value CN text,
while some UI/system table text remains outside the current WebUI selection
plan.

### Numerical Values and Gameplay Tables

Understanding is moderate for recovered schemas and low to moderate for exact
runtime formulas.

The earlier report understated the format side. The extracted JSON tables and
WebUI reference rows expose many raw numerical values, and the memory notes show
that many binary MemoryPack-like config families are now partially or exactly
parsed. Examples include SkillData, BuffData, LevelData, LevelScriptData,
ModelTable, ModelRadiusTable, WorldEntityRegistry, MissionAreaTable,
TeleportValidationDataTable, InteractiveData, SpawnerConfig, and selected
non-generated gameplay configs.

The runtime metadata reports expose a large amount of IL2CPP structure:

- Type definitions: 61,338.
- Methods: 469,596.
- Fields: 283,933.
- Matched option-flow-related types in one report: 4,631.
- Focus option-flow types: 12.
- Likely option-flow method-body targets: 30.

The broader metadata and memory notes also recover concrete gameplay payload
schemas. Focused examples include:

2026-07-01 WebUI progress: `scripts/build_gameplay_data.py` now promotes a
compact, inspectable subset of progression semantics into the Gameplay tab. It
samples weapon upgrade curves with cumulative costs, weapon base-ATK stat rows
annotated by breakthrough stage, weapon breakthrough materials and skill bounds,
weapon talent bound templates, character level EXP checkpoints, global character
break-stage caps, playable-capped character stat checkpoints from
`CharacterTable.attributes`, per-character breakthrough materials, and potential
unlock effects/items. The builder preserves raw stat metadata separately: the
current CN export has 2,632 visible character stat rows and 2,884 raw rows, with
raw character curves extending to level 99 while the playable level curve caps at
90. This improves practical access to numerical progression data, but it still
stops short of full formula/runtime simulation.

2026-07-01 WebUI equipment-stat progress: Equipment entries now expose
localized part/domain/formula/suit context plus per-property stat curves derived
from `EquipTable` display attributes and enhancement arrays. The current CN
Gameplay payload verifies 220 equipment entries, 838 nested equipment property
curves, 40 composite-attribute curves, and 28 emitted stat keys. The builder now
filters placeholder `attrType == 0` rows, preserves the base modifier as its own
property curve, and labels composite attributes such as all-skill damage,
fire/natural damage, and cold/pulse damage. These curves make equipment
progression inspectable in the WebUI, while formula evaluation and exact runtime
combat math remain outside the static payload.

2026-07-01 WebUI enemy-table progress: the Gameplay builder now emits 290 enemy
entries from merged `EnemyTable`, `EnemyAttributeTemplateTable`, display,
ability, tag, and drop tables. The CN payload verifies 610 visible Gameplay
entries total: 72 weapons, 220 equipment records, 28 visible character records,
and 290 enemies. Enemy stat recovery contributes 9,800 distinct authored
stat-template rows and 29,000 per-enemy stat references, with HP/ATK/DEF
checkpoints exposed in the WebUI. It also exposes 406 ability references, 194
born-buff references, drops, combat scalars, resilience fields, independent
attributes, and raw attr modifiers. This is authored table semantics, not a full
runtime combat formula or modifier-order reconstruction.

2026-07-01 source graph progress: `tools/endfield_source_graph.py` now ingests
the generated Gameplay payload, a pre-Gameplay item/economy table pass, an early
world/map table pass, a pre-Gameplay combat semantics pass, selected structured
factory tables, Spaceship/base tables, Activity/Achievement/SystemJump tables,
and factory tech-tree/unlock, PRTS Archive, Reading, RichContent, NPC, ambient
voice, and responsive bark tables as evidence graph nodes and relationships. A fast CN verification build with `--skip-asset-maps --skip-reference-rows
--skip-followups` produced 72 weapon nodes, 220 equipment nodes, 30 character
nodes, 290 enemy nodes, 78 enemy template nodes, 98 enemy attribute-template
nodes, 134 enemy ability nodes, 217 buff nodes, 6 map nodes, 208 level nodes,
147 level loading nodes, 74 scene area nodes, 34 map marks, 155 map mark
templates, 39 map mark types, 5 map mark categories, 32 track-map points, 64
track-map links, 37 scene collectables, 69 factory regions, 5 settlement POIs, 5
shop-channel POIs, 497 skill nodes, 4,807 skill level nodes, 33 skill tag nodes,
405 gameplay blackboard key nodes, 80 use-item effect nodes, 9 general ability
nodes, 14 ability entity nodes, 19 global effect nodes, 54 global effect param
nodes, 251 potential talent effect nodes, 526 talent nodes, 1,240 progression
nodes, 2,425 item nodes, 93 item type nodes, 11 item showing-type nodes, 232
item obtain-way nodes, 5,722 reward nodes, 1,252 reward-drop nodes, 19 shop
groups, 28 shops, 687 shop goods, 6 shop goods tags, 392 factory recipe nodes,
485 factory item descriptor nodes, 38 factory machine nodes, 20 factory craft
group nodes, 22 factory showing-type nodes, 3,820 required-item edges, 290
`uses_enemy_attribute_template` edges, 406 `has_enemy_ability` edges, 194
`starts_with_buff` edges, 266 `drops_item` edges, and 6,716
`has_gameplay_asset` edges including 839 item-to-asset edges. The two hidden
Endministrator rows remain as `CharacterTable` graph nodes but are no longer
separate visible Gameplay entries. Exact queries such as `chr_0017_yvonne`,
`wpn_pistol_0001`, `eny_0018_lbtough`, `item_gold`,
`reward_payshop_wpn_claym_0003`, `domainshop_goods_map01_10001`,
`chr_0002_endminm_attack1`, `item_proc_bomb_1`, `atk_scale`, `map01`,
`mark_arrow`, `chr_0017_yvonne:stat:90:4`, `chr_0017_yvonne:potential:1`,
`chr_0017_yvonne:breakthrough:charBreak20`, `aglina_indie`,
`dung_aglina_chartrain01`, `attr_1`,
`component_activity_xiranite_cmpt_1`, `aglina_base01_lv001`,
`spaceship_skill_chr_0004_pelica_1_1`,
`growcabin_plant_crylplant_1_1`, `envEmoji_common_adaptationwork`,
`activity_weekly_task_1`, `week10_task1`, `achv_adv_tundra_box`,
`jump_activity_conditional_multistage_1`, `tech_jinlong_1_battle_cannon_2`,
`air_dancer_1`, `hdwk_item_drop_agfly_1_1`, `nar_002_settlement`,
`text_002_settelment`, `rp_radio_c16m4_50`, `research_001`, `chaosheng`,
`CommonKid`, `action_dash_start`, and `-1006722661` now resolve to semantic
nodes with source table rows and neighbors. This improves
cross-domain lookup; it still does not prove formulas beyond generated
source-table evidence.

2026-07-01 source graph character-progression progress: generated Gameplay
character payloads now expose break-stage ranges, level EXP/gold checkpoints,
visible stat checkpoints, breakthrough unlocks, potential levels, potential
blackboard parameters, potential unlock items, and default weapons as first-class
queryable graph facts. A fast rebuild on the current CN payload verified 140
character break-stage nodes, 196 level-checkpoint nodes, 2,632 stat-checkpoint
nodes, 18,424 stat-property value edges, 112 breakthrough nodes, 140 potential
nodes, 794 potential blackboard edges, 101 potential unlock-item edges, and 28
default-weapon edges. The current generated CN Gameplay payload used for this
check reports 515 visible entries: 72 weapons, 220 equipment records, 28
characters, 78 visible enemy entries, and 117 usable items, while retaining 290
enemy variants as generated payload evidence. This improves exact lookup for
character numerical progression; runtime formula evaluation and modifier order
remain future work.

2026-07-01 source graph character-support and attribute-dictionary progress:
character tags, tag descriptions, professions, element types, presets, teams,
weapon recommendations, weapon-skill recommendations, tutorials, trials,
training thresholds, and shared attribute display metadata are now queryable. A
fast rebuild verified 635 character presets, 2,340 preset-equipment edges, 832
team preset-list edges, 274 character-tag edges, 108 tag-description nodes, 115
recommended-weapon edges, 174 recommended weapon-skill edges, 22 tutorial
dungeons, 97 tutorial stages, 336 tutorial-step refs, 7 trial rows, 80 training
recommendation rows, 94 attribute meta rows, 86 attribute show entries, 25
composite-attribute member edges, 21 attribute-filter entries, and 51
interactive attribute rows. That scouted slice has since landed in the
Spaceship/base graph pass below.

2026-07-01 source graph Spaceship/base progress: Spaceship NPC proxies, behavior
EnvTalk refs, base skills, room types, room attrs, room levels, empty rooms,
growth/manufacture formulas, clue rows, EnvTalk rows, audio refs, item refs, and
local I18n text references are now queryable. A fast CN rebuild verified 52
spaceship NPC proxy nodes, 140 spaceship skill nodes, 8 room type nodes, 18 room
attrs, 15 room levels, 6 empty rooms, 38 formulas, 7 clues, 1,704 EnvTalk nodes,
516 I18n text ref nodes, 52 proxy-to-character edges, 234 behavior EnvTalk
edges, 108 character skill refs, 140 skill-to-room-type refs, 31 room-level item
costs, 23 formula unlocks, 68 formula item edges, 2,537 EnvTalk audio refs, and
1,046 I18n text-use edges. The scouted Activity/Achievement plus SystemJump
slice has since landed below.

2026-07-01 source graph Activity/Achievement/SystemJump progress: root
activities, activity tags, activity conditions, weekly and multistage tasks,
activity stages, milestones, banners, push bubbles, achievement
categories/groups, achievements, achievement levels, achievement conditions,
achievement statistic rows, and authored system jumps are now queryable. The
corrected fast CN rebuild verified 600 authored system-jump definitions, 64
authored activity definitions, 23 activity tags, 300 activity conditions, 276
activity tasks, 150 activity stages, 5 milestones, 18 banners, 34 push bubbles,
8 achievement categories, 12 groups, 114 achievements, 156 achievement levels,
200 achievement conditions, 3 achievement statistic rows, 63 activity-tag edges,
276 activity-task edges, 350 activity-stage edges, 332 stage reward edges, 156
achievement-level edges, 200 level-condition edges, 66 jump-to-activity edges,
13 jump-to-factory-tech edges, 1 jump-to-factory-tech-group edge, and 50
jump-to-manual-craft-unlock edges. The scouted factory tech-tree/unlock bridge
has since landed below.

2026-07-01 source graph factory tech-tree/unlock progress: `FacSTT*` tech
groups/categories/layers/nodes/conditions, machine-to-tech links,
blueprint-to-machine item links, factory buildings, building types, renderer
templates, blueprint machine icons, manual-craft formula unlocks, and
manual-craft upgrade rows are now queryable. The corrected fast CN rebuild
verified 2 tech groups, 11 categories, 6 layers, 71 authored tech nodes, 5 tech
conditions, 94 factory buildings, 31 referenced building types, 113 renderer
templates, 61 blueprint machine icon nodes, 168 manual-craft unlock nodes, 55
tech prerequisite edges, 128 tech unlock-item edges, 75 tech action refs, 72
machine-to-tech links, 59 blueprint item links, 89 building item links, 82
building map-mark refs, 97 building renderer-template refs, 168 manual-craft
formula unlock links, 45 manual-craft upgrade links, 13 system jumps to exact
factory techs, and 1 system jump to a factory tech group. The scouted PRTS
Archive / Reading / RichContent bridge has since landed below.

2026-07-01 source graph PRTS Archive/Reading/RichContent progress: PRTS
page/category/first-level/archive entries, RichContent roots and content lines,
Reading popup rows/icons, PRTS reading roots/entries, investigations/groups/notes,
and SystemJump PRTS detail targets are now queryable. The corrected fast CN
rebuild verified 422 PRTS entry nodes, 586 RichContent roots, 2,991 RichContent
line nodes, 576 reading popups, 14 referenced popup icon nodes with 6 authored
icon-map definitions, 21 PRTS reading roots, 36 PRTS reading entries, 13
investigation nodes, 29 investigation groups, 29 notes, 414 canonical
first-level-to-entry edges, 105 PRTS entry-to-story targets, 391
entry-to-RichContent targets, 247 popup-to-story targets, 548 popup-to-RichContent
targets, 2 reading-entry story targets, 28 reading-entry RichContent targets, 47
direct investigation entry refs, 58 investigation-to-group refs, 94
group-to-entry refs, 58 group-to-note refs, 25 system jumps to PRTS entries,
and 5 system
jumps to PRTS investigations. Investigation grouping intentionally keeps the two
source evidence paths from `PrtsInvestigate.categoryDataList` and
`PrtsInvestigateCategory.list`; inferred PRTS page buckets remain out of scope
until backed by a table or UI binding. The scouted NPC / Ambient Voice /
Responsive Bark bridge has since landed below.

2026-07-01 source graph NPC/Ambient Voice/Responsive Bark progress: NPC rows,
NPC groups, NPC templates, voice profiles, environmental NPCs, atmosphere
camp/career tags, audio dialog channels, responsive trigger groups, responsive
speakers/triggers/responses, AIBark rules, AIBark text, and bark constants are
now queryable. The corrected fast CN rebuild verified 359 NPC nodes, 939 NPC
groups, 543 unique NPC templates from 676 source rows, 1,239 voice profiles, 43
environmental NPC rows, 676 audio dialog channel nodes including 33 channel
aliases, 1,142 Wwise event nodes, 72 responsive speakers, 9,521 responsive
triggers, 165 global responsive trigger types, 4,325 responsive responses, 928
bark text rows, 359 NPC-to-group links, 33 NPC-to-EnvTalk links, 689 voice
profile-to-template links, 541 Wwise-channel and 635 voActor-channel voice
profile links, 642 channel-to-actor matches, 13,919 trigger-response occurrence
edges, 4,304 unique response-to-AudioDialog/audio links, 868 response-to-bark-
text links, and 928 bark text-to-line links. NPC template/dataKey asset joins
remain intentionally absent because current exact asset entity aliases do not
match those IDs; SNS, radio, remote-common, cue, and full voice-extra tables
remain a broader narrative/audio pass.

2026-07-01 source graph item/economy progress: item, reward, reward-drop, and
shop table semantics are now queryable before Gameplay ingestion. A fast source
graph rebuild verified 2,376 authored item rows, 2,035 obtain-way edges, 288
item outcome edges, 5,722 reward nodes, 16,865 guaranteed reward item edges,
2,344 probabilistic reward item edges, 1,252 reward-drop nodes, 3,319 reward-drop
item edges, 19 shop groups, 28 shops, 687 shop goods, 687 shop currency-price
edges, 673 shop reward edges, and 214 shop goods tag edges. This recovers static
economy relationships; runtime pricing conditions, refresh rules, random shop
selection, and reward probability formulas remain future work.

2026-07-01 source graph combat-semantics progress: buff configs, skill patch
levels, use-item actions, general abilities, ability-entity stats, global
effects, and potential talent effects are now queryable from authored tables. A
fast source graph rebuild verified 479 skill patch rows, 4,807 skill level
nodes, 14,838 skill-level blackboard value edges, 80 use-item effect nodes, 83
use-item-to-buff edges, 1 use-item-to-skill edge, 202 use-item blackboard edges,
9 general abilities, 2 general-ability map-ban edges, 14 ability entity stat
nodes, 19 global effects, 54 global effect params, 251 potential talent effects,
57 talent buff edges, 30 talent attach-skill edges, 331 talent skill-blackboard
modifier edges, 30 talent skill-param modifier edges, and 51 talent stat
modifier edges. A later BuffData decoded-config graph pass verified 4,616
BuffData files, 2,325 unique buff ids, 1,416 gameplay-tag string edges, 13,373
parameter-string edges, 1,862 linked-buff string edges, 1,404 effect-key edges,
273 audio-event edges, and 391 icon edges. A later SkillData decoded-config graph
pass verified 4,191 SkillData files, 2,108 unique skill ids, 1,786 gameplay-tag
string edges, 49,988 parameter-string edges, 3,000 linked-buff string edges,
9,527 effect-key edges, 6,178 audio-event edges, and 188 icon edges. This
recovers static combat parameter and reference evidence; runtime skill execution
order, skill targeting, buff stacking, BuffData timeline action behavior, and
formula evaluation remain future work.

2026-07-01 source graph world/map progress: map, level, loading, scene-area,
map-mark, track-map, scene collectable, factory-region, settlement POI, and shop
channel POI table semantics are now queryable. A fast source graph rebuild
verified 3 authored map rows plus 6 total map nodes including inferred map
prefixes, 188 level rows, 147 level loading rows, 122 level-to-map edges, 74
scene areas, 34 map marks, 155 unique map mark templates from 173 template rows,
32 track-map points, 64 track-map links, 37 scene collectables, 37 collectable
item edges, 69 factory region edges, 5 settlement POI edges, and 5 shop-channel
POI edges. This turns static map tables into a navigable world graph; runtime
streaming, object placement, and quest-dependent visibility remain future work.

2026-07-01 source graph factory progress: manual, machine, and hub factory
recipes are now queryable from selected structured tables. The fast graph
rebuild verified 392 `factory_recipe` nodes, 615 ingredient edges, 468 output
edges, 76 formula-item unlock edges, 257 machine edges, 76 domain edges, 135
showing-type edges, and 316 craft-group edges. Factory item descriptors add 485
`factory_item` nodes and domain visibility/transfer edges. This recovers static
factory recipe and item relationships; power, logistics, timing, and unlock
runtime rules remain future work.

2026-07-01 source graph equipment-semantic progress: equipment formula,
domain, suit, unlock, and stat-property details are now queryable instead of
only compacted into progression blobs. A fast CN source graph rebuild verified
220 `equipment_formula` nodes, 27 formula packs, 22 suits, 2 gameplay domains,
22 unlock keys, 838 equipment property curves, 24 stat-property nodes, 220
`crafted_by_formula` edges, 220 formula output edges, 220 domain edges, 182 suit
edges, and 838 property-curve-to-stat edges. Formula queries now show output
equipment, source `EquipFormulaTable` rows, formula packs, unlock keys, and
material costs. This improves static equipment semantics, but it still does not
simulate runtime crafting or combat formulas.

2026-07-01 source graph progression-cost progress: Gameplay item-cost
traversal now follows `itemBundle`, `items`, equipment formula materials, and
positive `goldCost` fields. A fast CN source graph rebuild verified 3,820
`requires_item` edges total: 1,268 from progression nodes, 1,008 from skill
groups, 1,104 from talent nodes, 440 from equipment formula nodes, and 736 total
edges to `item_gold`. The builder filters numeric item counts at or below 0, so
zero-cost placeholder rows no longer become required-item evidence.

2026-07-01 WebUI semantic-link progress: Gameplay entries now link to Story
wiki pages only when the current Story index contains the matching `wiki_*`
entry, and Story wiki pages link back to the relevant Gameplay entry through
`?gameplay=...#gameplay`. The current CN payload verifies 321 resolved links:
72 weapons, 220 equipment records, and 29 character-story links across 28
visible character entries. `chr_9000_endmin` now carries both
`wiki_chr_0002_endminm` and `wiki_chr_0003_endminf`, so the hidden male/female
Endministrator wiki records resolve through the single visible Gameplay entry.

- `AbilitySystemData` field order and many serialized fields for 28 character
  rows, including skill bundles, command mappings, combo conditions, UI data,
  buff lists, blackboard entries, camera config, hit/effect settings, health
  type, preload ability entities, and potential buff IDs.
- `SkillDataBundle` default command mappings and 36 combo-skill condition
  entries in the focused corpus, with 94 managed-reference action links.
- `BuffInput` rows and dash-buff assignments, including common dash and
  character-specific dash buff IDs.
- `EffectActionCfg` default-like dead-effect rows named through the observed
  107-word layout.
- `ProjectileComponentData` prefixes, move-mode dictionaries, selected movement
  and BezierPoint structures, and alert-effect/tail sections in focused
  projectile samples.
- `CreateBuffAction` and `CheckBuffStackNumAdvanced` payloads promoted from raw
  unparsed output to named partial records.

So the project can often answer:

- What values exist in a config row?
- Which field or payload family appears to contain them?
- Which runtime metadata type names and field order support the interpretation?
- Which focused binary payloads consume exactly or leave bounded partial tails?

What remains weaker:

- Which numeric columns feed which exact runtime methods in broad game-wide
  coverage.
- Formula/evaluator behavior for combat, buffs, skills, economy, factory,
  progression, targeting, projectile movement, and effect systems.
- Runtime override order, defaulting, clamping, scaling, branching, and feature
  gates.
- Whether a value is authored, derived, display-only, deprecated, or used only
  by a specific runtime variant.
- Non-focused variants of the partially decoded payloads.

The short version: value extraction and schema recovery are now fairly strong
for several important families; formula semantics are still the frontier.

### MonoBehaviour And Gameplay Payload Schemas

Understanding is moderate and improving.

The current recovered MonoBehaviour corpus is large: 1,064,294 JSON files with
0 JSON parse errors and 0 top-level metadata-only/raw-data-only fallbacks in the
memory inventory. Only 3,644 files carry incomplete markers, split between
partial TypeTree decode and heuristic managed-reference recovery.

Important focused wins:

- `AbilitySystemData` parent records in the focused character slice are now
  byte-consumed, with nested partials called out separately instead of leaving
  unread parent bytes.
- `TargetSettings` exposes finder/validator/post-processor RID evidence while
  preserving unresolved post-selector fields.
- `ProjectileComponentData` no longer fails as a whole record in the focused
  slices; remaining work is semantic depth inside effects, sounds, and some
  nested movement metadata.
- Audio managed-reference payloads such as `PlaySound`, `PlaySingleSound`, and
  `PlaySoundByParticleCount` decode in focused probes, and the decoded sound
  names are candidates for a later audio-index pass.
- Guide managed-reference warning buckets appear partly stale under the current
  exporter, with focused revalidation decoding 939 files and 8,857 refs.
- Ability-entity template/root/controller payloads now have conservative
  partial decoders that avoid generic heuristic output for known classes.

Remaining limitations:

- Some broad decoded-index buckets are stale and should be rebuilt before using
  them as current failure counts.
- Managed-reference failure diagnostics need to be attached to any future
  no-recovery cases so the remaining 1,707-style partials split into actionable
  buckets.
- Several nested game-specific structures are deliberately partial:
  `TargetSettings` post-selector fields, `SelectorData`, non-default
  `EffectActionCfg`, projectile effect lists, projectile sound structs,
  ability-entity field-meta blocks, and some `MoveModeData` internals.

### Models, Materials, and Scene Placement

Understanding is moderate.

The asset index has 64,987 model entries, 67,832 JSON entries, and 84,103
relation records. The source graph includes material, mesh, texture, shader,
and asset-index material/texture relationships.
This supports browsing and targeted lookup.

2026-07-01 source graph asset progress: Gameplay entries and Gameplay cost/drop
item nodes now get conservative asset neighbors when an exact gameplay ID, icon
ID, model-path stem, or item ID appears inside an exported asset path. The fast
CN source graph build verifies 6,716 `has_gameplay_asset` edges: 2,078 weapon
edges, 2,039 character edges, 1,760 equipment edges, and 839 Gameplay item edges
across 96 item nodes. The item links split into 836 image edges and 3
`item_gold` drop-model edges; `item_charpotentialup_chr_9000_endmin` remains
unmatched. This maps common weapon meshes/materials, character UI/portrait
textures, equipment icon textures, item icons, and drop models to semantic
Gameplay nodes without using fuzzy localized-name matching.

2026-07-01 asset relation progress: the full asset index now resolves Material
`m_Texture.m_PathID` references when Unity texture names are blank, so the
current index no longer has an empty relation surface. The rebuilt index has
84,103 relation records, including 56,789 entries with `textures`, 8,319 with
`materials`, 27,314 with `referencedByMaterials`, and 5,657 with
`referencedByModels`. A fast source graph rebuild verified 291,078 `asset_pid`
aliases, 291,078 `asset_pathid` aliases, 229,557 `uses_texture` edges, 8,450
`uses_material` edges, 190,457 `referenced_by_material` edges, and 37,702
`referenced_by_model` edges. Asset queries can now follow many material and
texture "used by" chains without scanning all Material JSON during graph use.

2026-07-01 renderable asset entity progress: source graph asset ingestion now
groups exported LOD model files into `asset_entity` nodes keyed by source plus
normalized model base. A fast graph rebuild verified 10,465 `asset_entity`
nodes, 30,482 `entity_has_lod_model` edges, 1,962 `entity_uses_material` edges,
and 8,581 `entity_uses_texture` edges. Queries such as
`python tools\endfield_source_graph.py used-by actor_aglina_body_01 --kind asset_entity`
resolve semantic renderable groups, and texture `used-by` queries now return
entity-level consumers before the raw material/model details.

2026-07-01 weapon-to-renderable progress: weapon Gameplay nodes now link to
renderable `asset_entity` groups through exact `modelPath` stem matches. A fast
graph rebuild verified 132 `has_gameplay_asset_entity` edges across 71 weapon
sources and 132 renderable entity targets; `wpn_lance_0003` (`寻路者道标`) is the
only weapon without a renderable entity candidate. The relationship makes
queries like `used-by wpn_sword_0019_01 --kind asset_entity` surface the
semantic weapon before lower-level material/model rows.

2026-07-01 gameplay-effect asset-name progress: source graph now adds strict
suffix-normalized name-match edges from `gameplay_effect` keys to exported
`asset` rows whose stem equals `<effectKey>_p[0-9A-F]{16}`. A fast CN temp graph
build verified 232 `effect_name_matches_export_base_asset` edges from 223
effects to 232 concrete asset rows, split across 225 model assets and 7 JSON
assets. Direct exact effect-to-asset alias matches remain zero, and broader
prefix matches were rejected because they create false collisions. This improves
lookup for effect-adjacent exported assets but remains export-filename evidence,
not runtime dependency proof.

2026-07-01 model config asset-binding audit:
`memory/model_config_asset_binding_audit_20260701.md` verifies that decoded
`ModelTable` rows still do not bind to renderable `asset_entity` groups through
exact or prefix `modelId`/prefab-stem matching. The current fast graph has 1,201
`model_config_model` rows and 10,424 renderable asset entities, but 0 exact or
prefix config-to-renderable matches, 0 `model_config_asset_entity` edges, and 0
`interactive_template_asset_entity` edges. Several highly used interactive
postmodels, such as `int_doodad_ore_cluster_iron`, have world/entity consumers
and prefab paths but no exported renderable owner link yet. The likely next
step is prefab/component or asset-map evidence, not looser filename matching.

The deeper semantic model is still incomplete:

- Exported LOD model files are now grouped into renderable `asset_entity` nodes,
  but many entities are still not mapped to gameplay records or runtime prefab
  placement.
- Material and texture dependency chains are now normalized for many
  PathID-resolved Material JSON links, but runtime material variants, shader
  behavior, and scene-specific swaps are not fully classified.
- Scene/level placement is partially represented, but not complete enough for
  a full in-game object map.
- Asset variants, LODs, effects, and runtime swaps require more classification.

For WebUI search and inspection this is already useful. For full reconstruction
of world state or entity behavior it is not yet complete.

### Asset Bundles And AnimeStudio Completeness

Understanding is high at the VFS layer and partial at the exact per-AB
clean-certification layer.

The memory AB report counted 518,131 indexed `Bundle` AB entries with no
missing chunks. That means the bundle population is reachable and well indexed.
AnimeStudio asset maps also enumerate over 1.5 million Unity objects across
Bundle and InitialBundle sources.

The conservative limitation is that older logs were not sufficient to certify
which exact source ABs were warning-free. Stage-level logs can say that shader,
Texture2D, AnimationClip, Sprite, or MonoBehaviour issues occurred, but older
entries often lacked the source AB path, bundle offset, PathID, and type needed
for an exact clean/dirty manifest.

Recent memory notes show strong progress in narrowing old issues:

- Texture2D missing/collision status is now clean for the current focused
  status manifests.
- Shader shard replay moved from dropped outputs to parsed shader metadata and
  extracted DXBC/SMOL-V snippets.
- AnimationClip unknown custom bindings now export with stable placeholder
  names instead of dropping entire clips in targeted checks.
- Managed-reference warning buckets are partly stale under the current exporter.

The next correctness upgrade is a per-source-file status manifest that records
source VFS block, AB name/offset/length/hash, object counts, warning counts,
conversion outputs, and partial MonoBehaviour counts per AB.

### Characters and Animation

Understanding is deep for selected targets and partial game-wide.

Older character recovery reports show strong targeted progress:

- Zhuangfy recovery has a verified Unity viewer scene with 9 LOD0 non-VFX
  skinned renderers, 22 materials, 383 clips, a 16-layer main controller, and
  IK/Grounder targets.
- Wulfa recovery reports 517 skeleton transforms, 460 scene transforms, 14
  active skinned meshes, 415 imported playable transform clips, 11 UI prop
  clips, 703 source clips, 780 transform auxiliary sample files, and 48
  recovered layered states.
- Shared viewer work also includes Mifu.

The broad game-wide picture is less complete. Older reports mention very large
counts, such as 109,670 AnimationClip entries and 52,929 Animator entries, but
normal conversion recovers only a small subset without specialized ACL,
binding, mask, avatar, controller, IK, morph, and constraint handling.

The practical conclusion: selected actor recovery is sophisticated, but this is
not yet a solved general character pipeline for the whole game.
The maintained Unity character workflow clarifies the current boundary. The
viewer is a recovery lab fed by AnimeStudio exports, actor-specific scratch
extraction, manifest generators, and Unity rebuild scripts. It imports LOD0
non-VFX body renderers, recovered mesh data, texture/material links, ACL-sampled
transform clips, selected static props, and controller evidence for Wulfa,
Zhuangfy, and Mifu.

Current generated materials use Unity `Standard` by default. Original Endfield
shader names and path IDs are preserved as metadata, but original game shaders
are not assigned by default. Animation playback uses legacy Unity `Animation`
clips generated from sampled transform curves; full controller scripts, IK
solvers, pose drivers, facial morph layers, and runtime state machines remain
partial.

### Shaders

Understanding is moderate for payload extraction and partial for game-faithful
rendering.

The generated reports captured older shader limitations, but memory notes show
later recovery progress:

- Endfield shader subprogram records start with marker `0x0C11FFE2`.
- D3D11 native records use raw program type `33` and contain DXBC snippets.
- Vulkan native records use raw program type `25` and contain SMOL-V-like
  snippets.
- Shader shard replay after parser fixes produced 443 shader outputs with 0
  warning lines, 0 error lines, and 0 nonzero exits in that replay set.
- Later SMOL-V decoder updates handled the existing shard set with 59,686
  SMOL-V snippets, 56,878 DXBC snippets, 0 SMOL-V disassembly errors, and 0 bad
  dictionary key errors.

Remaining shader gaps:

- DXBC containers are extracted, but reliable HLSL decompilation still needs a
  native or out-of-process decompiler path.
- Converted/dumped shaders are not automatically compatible with the Unity
  character viewer.
- Original material shader assignment is intentionally disabled in the viewer;
  generated actor materials use Unity `Standard` unless a dedicated shader
  recovery task changes material property names, render queues, blend modes,
  and texture color-space assumptions together.
- Full resource binding normalization and renderer-fidelity checks remain
  separate from payload extraction.
## Further Improvements

### 1. Finish the Remaining Story Gap Hotlist

The latest current story gap report is small enough to treat as a focused
quality project:

- 35 flagged scenes.
- 6 partial authored line-order scenes.
- 15 inferred option placement scenes.
- 14 inferred option response scenes.

Recommended work:

- Make a reviewed hotlist from `reports/scene_order_gap_report_CN.md`.
- For each inferred option group, capture source graph context, timeline asset
  evidence, audio ordering, and nearby runtime jump clips.
- Promote only cases with direct evidence; otherwise add explicit manual
  overrides with tags that preserve uncertainty.
- Keep `webui/overrides/story_order.json` user-managed, and write proposed
  order references to generated data only when the workflow already expects
  that.

Success metric:

- Reduce current scene-order gap count from 35 toward 0 without adding
  untagged guesses.

### 2. Improve Option Branch Proof

Current option routing is usable but not fully proven.

Recommended work:

- Extend runtime jump analysis around the 20 inferred option groups.
- Link `DialogTimelineManager.SelectIndex`, `SetDialogOption`, runtime jump
  tracks, and active clip windows to concrete story keys.
- Use audio monotonicity only as supporting evidence, not as final proof.
- Add a report that separates "proven route", "contradicted inference",
  "likely but unproven", and "manual override".

Success metric:

- Fewer inferred option responses.
- No contradictions between inferred first lines and nearby Runtime Jump Track
  evidence.

2026-07-01 story option-proof progress: manual option overrides are now
graph-indexed, conflict-audited, and joined to Timeline option-flow writer/gate
evidence. The conflict audit still verifies 74 manual response options: 26 match
inference, 24 conflict, and 24 are manual-only. It now joins 20 Timeline
option-flow groups, confirms all 5 required IL2CPP writer/gate fact kinds are
present, and classifies 21 of 24 manual-vs-inferred conflicts as strict option
rows whose candidate runtime `+0x18` fields are all zero. Nearby Runtime Jump
proof still supports the manual first line for the high-signal `dlg_e6m1_10` and
`dlg_e6m4_14` conflicts. The next proof step is no longer finding the `+0x18`
writer; it is binding authored Timeline option rows to active runtime clips
strongly enough to promote edges without relying on display-only overrides.

### 3. Move Global Story Order from Static Recovery Toward Observed Runtime

Static mission recovery still diverges heavily from OCR/manual main-story
order. This is expected for gameplay/server-event-controlled clusters, but it
limits confidence in exact chronology.

Recommended work:

- Use OCR proposals as calibration evidence for missions with good match
  density.
- Investigate the highly divergent missions first.
- Add hash-terminal and action-event proof where available.
- Distinguish local scene ordering from global mission ordering in WebUI debug
  views and reports.
- Treat "source-backed local edge" and "observed gameplay order" as separate
  evidence classes.

Success metric:

- Lower strict and coarse inversion rates in
  `reports/mission_order/main_story_order_vs_override_CN.md`.
- More missions classified as exact or near-exact rather than highly divergent.

### 4. Expand Table Semantics Beyond Display

The WebUI is good at showing tables; the next step is explaining systems.

Recommended work:

- Pick a small set of high-value systems first: character growth, skills,
  buffs, enemy attributes, items, factory, and progression.
- For each system, document:
  - Source table files.
  - Primary key structure.
  - Important numeric columns.
  - Referenced i18n IDs.
  - Runtime config classes.
  - Getter/evaluator methods that consume the rows.
- Build source graph edges from table columns to runtime metadata symbols where
  evidence is strong.
- Separate authored constants from derived, display-only, and unused fields.

Success metric:

- Ability to answer not only "where is this number?" but "what runtime path
  uses this number, and what formula does it enter?"

### 4b. Promote Binary Config Decoders Carefully

The Data index already identifies many MemoryPack-like families and exactly
parses several important roots. The next improvement is to promote parsers only
where byte boundaries and metadata agree.

Recommended work:

- Keep exact decoders for roots that consume fully.
- For partial decoders, expose field names, counts, strings, RID links, and raw
  tails without inventing nested semantics.
- Build reusable MemoryPack helpers for strings, primitive arrays, maps, nested
  object headers, and nullable collections.
- Add FlatBuffer schema recovery for streaming `.bytes` only after the current
  detector groups are stable.
- Keep irradiance volumes, encoded ABs, Wwise PCKs, and bundle manifests outside
  the WebUI Data tab unless a schema-specific view is intentionally designed.

Success metric:

- More binary config families move from "identified" to "exactly consumed" or
  "bounded partial with named fields", with no silent guessing.

2026-07-01 progress: exact `ModelTable`, `ModelRadiusTable`,
`InteractiveTable`, `InteractiveTemplateData`,
`GameplayConfigWorldEntityRegistry`, teleport, mission-area, and subgame decodes
are now first-class source graph nodes and edges, backed by the current WebUI
Data index plus bounded row parsers for the verified MemoryPack shapes.
`SpawnerConfig` now contributes bounded enemy-library graph evidence without
claiming full-file tail semantics.

### 4c. Rebuild And Rank Current MonoBehaviour Gaps

Several older warning buckets are stale after recent exporter fixes.

Recommended work:

- Rebuild the decoded MonoBehaviour index with the current AnimeStudio exporter.
- Emit managed-reference recovery failure reasons for every no-recovery case.
- Rank remaining incomplete files by class family, source, count, and user value.
- Continue focused decoders for `EffectActionCfg`, `TargetSettings`,
  `SelectorData`, projectile effect/sound tails, ability-entity field-meta
  sections, and non-default ability/buff variants.

Success metric:

- The 3,644 incomplete-marker inventory splits into current actionable buckets,
  not stale historical warnings.

### 5. Reduce Remaining I18n/Text Coverage Gaps

The unselected CN i18n leftovers are small relative to the full corpus, but
still useful for UI and system completeness.

Recommended work:

- Review the 76 JSON files containing leftover CN IDs.
- Add WebUI reference handling for high-value leftover tables, especially
  tutorials, attributes, settings, tags, and system jump/link text.
- Keep story build scope lean; do not force every UI/system table into Story.
- Add a report that classifies leftovers by user-facing value and WebUI tab.

Success metric:

- Fewer leftover CN IDs, with remaining leftovers explicitly classified as
  out-of-scope, deprecated, or not user-facing.

### 6. Build a Semantic Asset Catalog

The asset index is broad. The next improvement is meaning.

Recommended work:

- Add entity-level grouping for models, materials, textures, videos, and JSON
  metadata.
- Resolve dependencies from model to material to texture to shader where
  possible.
- Map assets to actors, missions, levels, UI screens, items, and props.
- Detect duplicate or variant assets and explain why they differ.
- Add stable preview thumbnails and representative images for grouped assets.

Success metric:

- Search results can answer "what is this used by?" and "what files make up
  this game object?", not just "which files match this name?"

### 6b. Add Per-AB Clean/Dirty Certification

Current VFS indexing proves bundle entries are present. It does not yet prove
that each individual AB was processed warning-free.

Recommended work:

- Emit per-AB status manifests during AnimeStudio map/convert/json stages.
- Include source VFS block, AB path, offset, length, data hash, PathID, object
  type, warning count, error count, output count, and partial decode counts.
- Distinguish unsupported-but-expected object types from true parser/exporter
  failures.
- Backfill report-only status manifests from existing maps where possible.

Success metric:

- A future report can count clean ABs, partially decoded ABs, conversion-error
  ABs, and indexed-but-not-loaded ABs exactly.

### 7. Generalize Character and Animation Recovery

Targeted recovery is strong, but broad actor recovery remains hard.

Recommended work:

- Promote proven Wulfa/Zhuangfy/Mifu logic into repeatable actor recovery
  stages where appropriate.
- Build manifest-driven actor selection and validation.
- Decode ACL transform buffers more broadly.
- Improve binding from clips to skeleton paths, avatars, masks, and controller
  states.
- Preserve additive/helper/IK uncertainty instead of forcing overconfident
  playback.

Success metric:

- A repeatable character recovery report for many actors with clear pass/fail
  checks, not only hand-targeted successes.

### 8. Continue Shader Binding Recovery

Shader payload extraction is useful but not enough for faithful rendering.

Recommended work:

- Focus on resource binding normalization.
- Decode packed texture/sampler/UAV bindings.
- Improve Vulkan descriptor-space interpretation.
- Track parse failures by shader family and platform.
- Link materials to recovered shader resources in a queryable way.

Success metric:

- More materials can be rendered or inspected with correct texture slots,
  samplers, and shader variants.

### 9. Resolve Video Stragglers

Narrative and FMV video coverage is useful but incomplete.

Recommended work:

- Investigate the 18 unresolved narrative video refs.
- Classify the 110 unbound files from the FMV-scope report.
- Separate full-motion narrative, UI/tutorial, background, logo, placeholder,
  and unused videos.
- Add stronger source graph links from timeline clips and MissionRuntime data
  to concrete video paths.

Success metric:

- Unresolved narrative refs approach 0.
- Standalone and unbound videos are classified rather than merely listed.

### 10. Keep Report Freshness Clear

Some older reports remain useful as historical notes, but they can contradict
current generated summaries if read without dates.

Recommended work:

- Add generated timestamps and source export fingerprints to every report that
  does not already have them.
- Prefer current `export_full_summary`, `source_graph/summary`, WebUI
  manifest, and latest gap reports for headline metrics.
- Move durable interpretations to `memory/`, as this report does.
- Avoid using older May character/shader reports as current global counts
  unless they are clearly labeled as historical or scoped.

Success metric:

- A reader can tell which numbers are current pipeline health metrics and which
  are historical recovery snapshots.

### 11. Improve Performance and Resource Use

The latest benchmark for a debug asset export shows:

- Wall time: about 1 hour 35 minutes.
- Peak process-tree RAM: 39.90 GiB working set.
- Largest single process: 11.48 GiB working set.

This is acceptable for heavy diagnostics, but too expensive for routine
iteration.

Recommended work:

- Keep lean WebUI paths as the default.
- Cache asset and source graph work aggressively.
- Use targeted asset/type filters for investigations.
- Track memory by stage and shard so regressions are visible.

Success metric:

- Routine WebUI refreshes remain fast, while heavy full/debug exports are
  clearly opt-in and benchmarked.

## Caveats

- Some reports are historical snapshots. Current headline metrics should come
  from the latest export summary, source graph summary, WebUI manifest, and
  current gap reports.- Some memory notes are focused validations, not global claims. A focused
  28-character-row AbilitySystemData pass or 300-projectile pass proves that
  slice, not every possible game payload variant.
- Some older memory notes intentionally preserve stale baselines so future work
  can see what changed. Prefer the newest status note when two memory files
  discuss the same warning family.
- Generated reports prove extracted evidence, not necessarily live runtime
  behavior.
- PowerShell console output can display CN text as mojibake depending on code
  page; use JSON/HTML data files or a UTF-8-aware viewer for text inspection.
- The filename `buff_runtime_metadata.md` currently appears to contain broad
  runtime metadata under a dialog-option-style title. Treat it as runtime
  schema evidence, not as a complete buff formula report.

## Bottom Line

The project understands the original game data well enough to provide a broad
static WebUI over story, text tables, audio, videos, assets, and many recovered
config structures. Extraction health is strong, texture output is verified, the
source graph is large and useful, CN story display is mostly reconstructed, raw
SNS/radio/remote/audio and DialogText/DialogOption support bridges are
queryable, and several
binary/MonoBehaviour payload families now have real schema recovery rather than
only raw dumps.

The next level is semantic proof. The highest-value improvements are to finish
the small remaining story gap hotlist, prove more option routes with runtime
evidence, align mission ordering with observed gameplay or runtime writer-side
evidence, map numeric tables to runtime formulas, rebuild current MonoBehaviour
gap inventories, certify AB cleanliness per source file, and turn broad asset
indexes into entity-level catalogs.
