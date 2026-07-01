# Source Graph Database

`tools/endfield_source_graph.py` builds a local SQLite relationship graph from
recovered WebUI story and Gameplay data, selected structured tables, exported
assets, character recovery manifests, material links, and optional AnimeStudio
asset maps.

Generated graph files live under `reports/source_graph/`. They are research
outputs, not exported source material, so they should not be written under
`export_full/`.

## Commands

Quick iteration build:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps
```

Full build with AnimeStudio asset maps:

```bat
python tools\endfield_source_graph.py build
```

Useful queries:

```bat
python tools\endfield_source_graph.py query dlg_c17m1_5 --limit 20
python tools\endfield_source_graph.py story dlg_c17m1_5 --limit-lines 8
python tools\endfield_source_graph.py issues --code inferredOptionResponse --limit 20
python tools\endfield_source_graph.py used-by pid:6C45653831AB1627 --limit 10
python tools\endfield_source_graph.py used-by pathid:4135669062202981187 --kind unity_pathid --limit 10
```

Useful flags:

- `--skip-gameplay`: skip WebUI Gameplay entry/skill/talent/progression ingestion.
- `--skip-asset-maps`: skip the expensive AnimeStudio asset-map pass.
- `--skip-reference-rows`: skip WebUI reference row expansion.
- `--skip-followups`: build only the graph and summary files.
- `--include-all-material-json`: scan all material JSON files instead of only
  actor material JSON files.

## Outputs

Core files:

- `endfield_source_graph.sqlite`
- `summary.json`
- `summary.md`
- `voice_audio_links.json`
- `character_recovery_candidates.json`
- `option_branch_gaps.json`
- `map_level_index.json`
- `semantic_update_summary.json`

The old standalone follow-up tools have been retired into
`tools/endfield_source_graph.py`; the graph builder writes those follow-up
indexes directly unless `--skip-followups` is passed.

## Graph Shape

Core SQLite tables:

- `nodes(id, kind, name, source, path, data)`
- `edges(src, dst, kind, source, evidence, data)`
- `aliases(alias, node_id, kind, source)`
- `files(path, kind, source, size, data)`
- `meta(key, value)`

Node kinds include story entries, lines, options, actors, localized text,
audio, videos, Gameplay weapons/equipment/characters/skills/talents/items,
equipment formulas/packs/suits/domains/unlock keys/stat properties/property
curves, progression records, assets, materials, meshes, shaders, animations,
map marks, structured table rows, reference rows, Unity asset containers,
Unity assets, and Unity PathIDs.

Edge kinds capture story membership, line ordering, actor names, localized
text, option anchors, audio use, narrative video links, Gameplay source-row,
skill, talent, progression, default-weapon, equipment domain/suit/formula/stat
property, formula-pack/unlock/output, and required-item relationships, table
ownership, exported files, character recovery manifest contents, asset-map
container ownership, and exported asset matches.

## Ingested Sources

High-value inputs:

- `webui/data/assets/index.json`
- `webui/data/assets/videos.json`
- `webui/data/lang/CN/index.json`
- `webui/data/lang/CN/conv/*.json`
- `webui/data/lang/CN/mission/*.json`
- `webui/data/lang/CN/reference/**`
- `webui/data/lang/CN/gameplay/index.json`
- `export_full/recovered/story_source_links.json`
- `export_full/recovered/AnimeStudio-cli/timeline_line_orders.json`
- actor material JSON under recovered AnimeStudio outputs
- Unity character recovery manifests under `unity_endfield_graph_shader_lab/`
- selected structured tables under `export_full/structured/StreamingAssets/Table/`
- optional AnimeStudio asset maps under `export_full/recovered/AnimeStudio-cli/`

Selected structured tables currently include audio, character, dialog summary,
interactive mission, level/map, mission extra info, scene area, and special
level-to-map tables.

## Current Notes

2026-07-01 Gameplay ingestion adds exact-queryable `weapon`, `equipment`,
`character`, `gameplay_skill_group`, `gameplay_skill`,
`gameplay_talent_group`, `gameplay_talent`, `gameplay_progression`, and `item`
nodes from `webui/data/lang/<LANG>/gameplay/index.json`. A fast CN build with
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 72 weapon
nodes, 220 equipment nodes, 30 character nodes, 409 skills, 526 talent nodes,
950 progression nodes, 66 item nodes, and edges for source rows, default
weapons, skill/talent membership, progression records, and required item costs.
The generated WebUI payload deliberately exposes 320 visible Gameplay entries:
72 weapons, 220 equipment records, and 28 visible character records. The two
hidden `chr_0002_endminm` / `chr_0003_endminf` Endministrator rows remain as
`CharacterTable` graph nodes and are folded into `chr_9000_endmin` story wiki
aliases for WebUI navigation. Example exact queries:

```bat
python tools\endfield_source_graph.py query chr_0017_yvonne --kind character
python tools\endfield_source_graph.py query wpn_pistol_0001 --kind weapon
```

The same build now links Gameplay entries to exported asset nodes by exact
Gameplay ID, icon ID, or model-path stem containment in asset paths. The fast
CN verification build produced 5,877 `has_gameplay_asset` edges: 2,078 from
weapons, 2,039 from characters, and 1,760 from equipment. Evidence values record
the source field (`id`, `iconId`, or `modelPath`) so later audits can separate
broad ID matches from icon/model-path matches.

2026-07-01 equipment semantic ingestion promotes equipment formula, domain,
suit, unlock, and stat-property details from compact Gameplay payload blobs to
queryable graph nodes. A fast CN build with
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 220
`equipment_formula` nodes, 27 formula packs, 22 suits, 2 gameplay domains, 22
unlock keys, 838 equipment property curves, and 24 stat-property nodes. It also
verified 220 `crafted_by_formula`, 220 `formula_outputs_equipment`, 220
`belongs_to_formula_pack`, 129 `unlocked_by`, 220 `uses_gameplay_domain`, 182
`has_equipment_suit`, 838 `has_equipment_property_curve`, and 838
`scales_stat_property` edges. Example exact queries:

```bat
python tools\endfield_source_graph.py query item_formu_t4_suit_atk02_hand_01 --kind equipment_formula
python tools\endfield_source_graph.py query domain_2 --kind gameplay_domain
python tools\endfield_source_graph.py query agi --kind gameplay_stat_property
```

2026-07-01 progression cost traversal now follows `itemBundle`, `items`,
formula materials, and positive `goldCost` fields in Gameplay payloads. A fast
CN build verified 3,820 `requires_item` edges total: 1,268 from progression
nodes, 1,008 from skill groups, 1,104 from talent nodes, 440 from equipment
formula nodes, and 736 total edges to `item_gold`. Numeric item counts at or
below 0 are filtered, so the rebuilt graph has no zero-count required-item
edges.

2026-07-01 asset relation ingestion now preserves `pid:<hex>` and
`pathid:<signed>` aliases for WebUI asset-index entries with exported PathIDs
and ingests asset-index material/texture relation blocks. After rebuilding the
full asset index, a fast CN graph build with
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 291,078
`asset_pid` aliases, 291,078 `asset_pathid` aliases, 229,557 `uses_texture`
edges, 8,450 `uses_material` edges, 190,457 `referenced_by_material` edges,
and 37,702 `referenced_by_model` edges. The current full asset index has 84,103
relation records and resolves blank-name Material texture slots by `m_PathID`.
The `used-by` command is the focused CLI for those edges: it resolves asset
paths and `pid:<hex>` aliases to WebUI asset nodes by default, and can use
`--kind unity_pathid` for lower-level Material JSON `uses_texture_pathid`
queries.

2026-07-01 renderable asset entity ingestion groups exported LOD model rows into
`asset_entity` nodes keyed by source plus normalized model base. A fast CN graph
rebuild verified 10,465 `asset_entity` nodes, 30,482 `entity_has_lod_model`
edges, 1,962 `entity_uses_material` edges, and 8,581 `entity_uses_texture`
edges. Entity aliases resolve bare bases such as `actor_aglina_body_01`; texture
`used-by` queries now surface renderable entities such as
`anm_com_machine+1_001_01` in addition to raw material/model rows.

Use the quick build for normal story/option/map investigation. Use the full
build only when Unity asset container, PathID, or exported asset relationship
coverage matters.

Timeline recovery is first-class graph input. The graph records raw Timeline
line clip order, option clip anchors, Runtime Jump routes, skipped lines,
continuation options, runtime jump clip nodes, and links to extracted source
JSON. This makes the `story` and `issues` commands the best starting point
before changing WebUI story recovery rules.

The graph also ingests WebUI recovery warnings. For example,
`issues --code inferredOptionResponse` separates cases with only Timeline clip
placement from cases with stronger route/skip evidence.

2026-07-01 option override ingestion adds WebUI-only `option_override` nodes
from `webui/overrides/options.json` without treating them as game-source proof.
A fast CN graph build verified 43 `option_override` nodes and 587
`webui/option_override` edges: 43 `has_option_override`, 43
`defines_option_override`, 43 `overrides_option_group`, 74 `overrides_option`,
19 `anchored_after_line`, 19 `manual_position_after`, 8
`manual_position_pre`, 74 each of `option_first_line`, `option_path_story`, and
`option_enters_story`, plus 116 `option_path_line` edges. Query examples:

```bat
python tools\endfield_source_graph.py query manual-option:dlg_c28m3_23:1 --kind option_override --limit 20
python tools\endfield_source_graph.py query webui/overrides/options.json --kind file --limit 5
```

Known parser limits are acceptable for current use:

- lightweight IL2CPP metadata parsing can leave generic/array/byref type
  indexes unresolved in reports;
- full asset-map ingestion is expensive and should be skipped unless needed;
- legacy local `character_recovery/` report directories may exist, but the
  maintained graph emits the top-level recovery candidate JSON.
