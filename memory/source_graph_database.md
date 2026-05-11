# Source Graph Database

Date: 2026-05-11

`tools/endfield_source_graph.py` builds a local SQLite relationship graph across
the recovered WebUI data, selected structured tables, exported assets, character
recovery manifests, material links, and optional AnimeStudio asset maps.

The default output directory is:

```text
reports/source_graph/
```

This was moved out of `export_full/recovered/source_graph/` on 2026-05-11.
`export_full/` should remain the exported source-material tree; the SQLite graph
and derived JSON/Markdown reports are generated research reports, so they live
under `reports/`. Durable workflow notes stay here in `memory/`.

## Commands

Quick iteration build without the deep AnimeStudio asset-map pass:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps
```

Full graph build:

```bat
python tools\endfield_source_graph.py build
```

Search the graph:

```bat
python tools\endfield_source_graph.py query zhuangfy --limit 20
python tools\endfield_source_graph.py query dlg_c27m3_6 --limit 20
```

Useful build flags:

- `--skip-asset-maps`: skip the huge AnimeStudio asset-map pass.
- `--skip-reference-rows`: skip WebUI reference row expansion.
- `--skip-followups`: build only the graph and summary files.
- `--include-all-material-json`: scan all material JSON files instead of only
  actor material JSON files.

## Outputs

- `endfield_source_graph.sqlite`: SQLite graph database.
- `summary.json`: machine-readable graph counts and build metadata.
- `summary.md`: human-readable graph summary.
- `voice_audio_links.json`: story line to audio candidates.
- `character_recovery_candidates.json`: character, mesh, material, texture,
  shader, and animation recovery candidates.
- `option_branch_gaps.json`: recovered option groups and branch-following gaps.
- `map_level_index.json`: recovered map marks and level/table links.
- `semantic_update_summary.json`: source graph counts useful for later update
  classification.

The graph build also feeds standalone follow-up report tools. These write richer
reports under subdirectories of `reports/source_graph/`:

```bat
python tools\endfield_voice_audio_linker.py
python tools\endfield_character_recovery_planner.py
python tools\endfield_story_branch_resolver.py
python tools\endfield_map_level_indexer.py
python tools\endfield_semantic_update_classifier.py
```

Focused examples:

```bat
python tools\endfield_voice_audio_linker.py --story dlg_e1m5_4 --limit 10
python tools\endfield_voice_audio_linker.py inspect au_dlg_e1m5_4_018 --story dlg_e1m5_4 --limit 1
python tools\endfield_character_recovery_planner.py --character chr_0030_zhuangfy --limit 1
python tools\endfield_story_branch_resolver.py --story dlg_a1m10_1 --limit 1
python tools\endfield_map_level_indexer.py --level map01_fc001 --limit 8
```

Follow-up output directories:

- `voice_audio/`: story line to audio path reports, by-story and by-speaker
  groupings, missing path samples, and orphan audio definitions.
- `character_recovery/`: ranked character recovery reports with per-character
  mesh, material, texture, shader, animation, manifest, and Unity asset
  evidence.
- `story_branches/`: option group and branch route reports with per-story JSON
  and unresolved gap counts.
- `map_levels/`: map/level/mark indexes with linked table row evidence and
  related asset matches.
- `update_classification/`: semantic classification for WebUI update feed
  entries.

## Graph Shape

The SQLite database has these core tables:

- `nodes(id, kind, name, source, path, data)`
- `edges(src, dst, kind, source, evidence, data)`
- `aliases(alias, node_id, kind, source)`
- `files(path, kind, source, size, data)`
- `meta(key, value)`

Node kinds include story entries, lines, options, actors, i18n text, audio,
videos, assets, materials, meshes, shaders, animations, map marks, structured
table rows, reference rows, Unity asset containers, Unity assets, and Unity
PathIDs.

Edge kinds capture relationships such as story membership, line ordering,
actor names, localized text, option anchors, audio usage, narrative video links,
table ownership, exported files, character recovery manifest contents, asset-map
container ownership, and exported asset matches.

## Ingested Sources

- `webui/data/assets/index.json`
- `webui/data/assets/videos.json`
- `webui/data/lang/CN/index.json`
- `webui/data/lang/CN/conv/*.json`
- `webui/data/lang/CN/mission/*.json`
- `webui/data/lang/CN/reference/**`
- `export_full/recovered/story_source_links.json`
- actor material JSON under recovered AnimeStudio outputs
- Unity character recovery manifests under `unity_endfield_graph_shader_lab/`
- selected structured tables under `export_full/structured/StreamingAssets/Table/`
- AnimeStudio asset maps under `export_full/recovered/AnimeStudio-cli/`

The selected structured tables currently include:

- `AudioDialog`
- `AudioSequenceDialog`
- `CharacterTable`
- `DialogSummaryMapTable`
- `DialogSummaryTable`
- `InteractiveMissionDataTable`
- `LevelDescTable`
- `MapIdTable`
- `MapMarkInsTable`
- `MissionExtraInfoTable`
- `SceneAreaTable`
- `SpecialLevelToMapTable`

## Current Build Notes

The full 2026-05-11 build completed successfully and produced:

- `3,571,601` nodes
- `5,081,751` edges
- `3,001,773` aliases
- `179,574` file records
- SQLite size: about `5.05 GB`
- Full build time: about `9.7 minutes`

The 2026-05-11 quick build after option-risk and map/scene table ingestion,
with `--skip-asset-maps` and reference rows enabled, produced:

- `663,343` nodes
- `742,366` edges
- `298,527` aliases

Use the quick build for normal iteration. Use the full build when Unity asset
container, PathID, and exported asset relationship coverage matters.

## Current Follow-Up Reports

The 2026-05-11 follow-up pass completed successfully:

- Voice/audio report: `31,177` line/audio relationships across `6,171` stories
  and `1,028` speakers. `14,579` relationships have resolved audio paths;
  `16,598` still need path recovery.
- Character recovery planner: top `20` reports written from `1,778` candidates.
  Top recovered candidates include `zhuangfy`, `mifu`, `wulfa`, `tangtang`,
  `endminf`, `endminm`, `wolfgd`, and `laevat`.
- Story branch resolver: `1,272` option-bearing stories, `2,553` option groups,
  `3,957` options, and `3,428` unresolved gaps after ingesting WebUI
  `optionBranchRisk` evidence as graph edges. Status split: `555` resolved,
  `714` partial, `3` unresolved.
- Map/level indexer: `3` maps, `17` levels, `34` marks, `249` linked level
  table rows, `12` linked map-only table rows, and `0` table rows still lacking
  level linkage in the quick graph.
- Semantic update classifier: current WebUI update feed contains `0` entries,
  so the report is intentionally empty but keeps the bucket schema stable.

Verification command:

```bat
python -m py_compile tools\endfield_voice_audio_linker.py tools\endfield_character_recovery_planner.py tools\endfield_story_branch_resolver.py tools\endfield_map_level_indexer.py tools\endfield_semantic_update_classifier.py
```

## Missing And Improvement Backlog

Current known gaps from the 2026-05-11 reports:

- Audio path coverage is the biggest hole. The voice/audio report found
  `31,177` line/audio relationships, but `16,598` of them still do not resolve
  to a WEM path. Many missing examples are normal story IDs like
  `au_dlg_a1m10_1_001`, so the next step is better AudioDialog/hash/path
  matching rather than just more story extraction.
- Story branch recovery is useful but incomplete. The branch resolver now
  treats `optionBranchRisk` records with `candidateLineIds` or
  `commonContinuationLineId` as recoverable route evidence. Remaining gaps are
  `1,423` missing entries, `1,423` missing paths, `380` missing scene-graph
  edges, `110` missing anchors, `83` missing group anchors, `6` anchor
  mismatches, and `3` inconsistent option anchors. The likely next source is
  deeper AnimeStudio graph/Lua/task-flow recovery.
  The graph builder also ingests `timelineRouteBranches.branchLineIdsByOption`
  directly as `timeline_route_branch` `option_first_line` / `option_path_line`
  edges, so Runtime Jump recovered branches no longer collapse back to one
  generic candidate-line hint.
- Character recovery candidates need more manifests and shader certainty. In
  the top `20` reports, `17` candidates are missing shader evidence and `17`
  are missing character recovery manifests; `3` lack a CharacterTable identity
  and `1` lacks an actor identity. The ranking also still has alias noise, such
  as candidates that inherit display names from nearby meshes.
- Map/level recovery now resolves the previous `72` table-row level gaps by
  parsing level tokens embedded before suffixes such as `_env`, adding
  `base01_lv001`/`base01_lv002`/`base01_lv003`, and keeping map-only rows on
  the owning map instead of counting them as unresolved.
- Semantic update classification has not been exercised against a real changed
  feed yet. The current update feed has `0` entries, so the classifier emits a
  stable empty report but still needs validation against a real or synthetic
  update sample.
- The full graph is large: about `5.05 GB`, with a full build time around
  `9.7` minutes. A compact graph profile, incremental rebuild mode, or report
  manifest could make day-to-day iteration lighter.
- `tools/` and `reports/` are ignored by this checkout. That matches the local
  tool/generated-report setup, but promoted source-graph tools will need an
  explicit unignore or a tracked home if they should be versioned.

Good next improvements:

- Add a graph validation command that checks JSON validity, stale paths, missing
  report files, and expected node/edge counts after every rebuild.
- Add an audio resolver pass that links story `au_*` IDs to AudioDialog rows by
  normalized ID, Wwise event, and path-derived story tokens, then validates
  candidate WEM paths with the `fluffy-dumper-src` FNV-1a/PCK ID logic. The PCK
  data can validate exact candidates but does not recover original path strings
  by itself.
- Add branch gap reports grouped by mission and gap type so recovery can target
  the highest-impact scene graph families first.
- Add character planner outputs that generate Unity lab worklists directly,
  separating "ready to build" from "needs shader/material/manual identity fix".
- Add a lightweight WebUI Reports page or static index that links the generated
  source-graph summaries without loading the 5 GB SQLite database.
