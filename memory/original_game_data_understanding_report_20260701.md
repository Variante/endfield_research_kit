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
Tables display, texture extraction, audio linkage, and broad asset discovery.
The WebUI-facing data is coherent enough to browse most story, table, audio,
video, and asset references from extracted game data.

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
| Audio | High for story linkage, moderate for full semantics | Event/media links and line usage are strong; non-story semantic classification can improve. |
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
- `uses_audio`: 24,936.
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

Partial but useful current examples include:

- `BuffData`: top-level schema, id verification, stacking settings for large
  subsets, selected prefix/tail values, and visible tags/parameters/references.
- `SkillData`: top-level schema, strict id rows, switch config, skill tags,
  target/buff settings, and UI range hints for common branches.
- `LevelScriptData`: all 3,658 files validate through a compact action-map
  helper, exposing script ids, action-map shape, UID records, list counts, and
  source hints while leaving full action payload semantics bounded.
- `Interactive/InteractiveData`: 25-member template roots and many component
  bodies parse far enough to expose names, component families, property maps,
  audio rows, guide geometry, trigger observers, hittable data, and interactive
  state properties.
- `AnimationConfig`, `AtmosphericNpcData`, `CharInteractPerformCfgs`,
  `LevelConfig`, `LevelData`, `LevelScriptTemplateData`, NPC montage rows,
  `SpawnerConfig`, and other families have verified top-level ids/counts and
  meaningful previews.

The remaining risk is nested semantics. A decoded field name or count proves
structure; it does not automatically prove gameplay meaning, formula behavior,
or runtime control flow.

### WebUI Story and Text Corpus

Understanding is strong at the corpus/display level.

The CN WebUI output contains thousands of conversation files, hundreds of
mission data files, over one hundred thousand reference rows, actor metadata,
audio links, source links, and narrative video references. The generated
source graph links lines, stories, options, missions, actors, audio, videos,
and selected table rows.

The current system is good at answering questions such as:

- Which dialog lines exist?
- Which actor is attached to a line?
- Which audio file or event is used by a line?
- Which mission or story key references a dialog scene?
- Which option groups exist?
- Which source file appears to back a story key?
- Which table rows and text IDs are visible to the WebUI?

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

- Audio nodes: 35,151.
- `audio_path` edges: 25,245.
- `defines_audio` edges: 25,245.
- `speaker_channel` edges: 25,245.
- `uses_audio` edges: 24,936.

The WebUI build also post-processes generated conversation JSON with playable
`audioSrc` links. This makes the story audio experience usable and gives a
solid evidence base for line-to-audio investigation.

Remaining audio improvements are mostly about semantic classification,
coverage validation outside story voice, and deeper Wwise/runtime behavior, not
basic line playback.

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
the generated Gameplay payload, a pre-Gameplay item/economy table pass, a
pre-Gameplay combat semantics pass, and selected structured factory tables as
evidence graph nodes and relationships. A fast CN verification build with
`--skip-asset-maps --skip-reference-rows --skip-followups` produced 72 weapon
nodes, 220 equipment nodes, 30 character nodes, 290 enemy nodes, 78 enemy
template nodes, 98 enemy attribute-template nodes, 134 enemy ability nodes, 217
buff nodes, 497 skill nodes, 4,807 skill level nodes, 33 skill tag nodes, 405
gameplay blackboard key nodes, 80 use-item effect nodes, 9 general ability
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
`chr_0002_endminm_attack1`, `item_proc_bomb_1`, `atk_scale`, and
`component_activity_xiranite_cmpt_1` now resolve to semantic nodes with source
table rows and neighbors. This improves cross-domain lookup; it still does not
prove formulas beyond generated source-table evidence.

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
9 general abilities, 14 ability entity stat nodes, 19 global effects, 54 global
effect params, 251 potential talent effects, 57 talent buff edges, 30 talent
attach-skill edges, 331 talent skill-blackboard modifier edges, 30 talent
skill-param modifier edges, and 51 talent stat modifier edges. This recovers
static combat parameter evidence; runtime skill execution order, buff stacking,
and formula evaluation remain future work.

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
source graph is large and useful, CN story display is mostly reconstructed, and
several binary/MonoBehaviour payload families now have real schema recovery
rather than only raw dumps.

The next level is semantic proof. The highest-value improvements are to finish
the small remaining story gap hotlist, prove more option routes with runtime
evidence, align mission ordering with observed gameplay or runtime writer-side
evidence, map numeric tables to runtime formulas, rebuild current MonoBehaviour
gap inventories, certify AB cleanliness per source file, and turn broad asset
indexes into entity-level catalogs.
