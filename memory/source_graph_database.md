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
audio, videos, Gameplay weapons/equipment/characters/skills/talents/items and
progression records, assets, materials, meshes, shaders, animations, map
marks, structured table rows, reference rows, Unity asset containers, Unity
assets, and Unity PathIDs.

Edge kinds capture story membership, line ordering, actor names, localized
text, option anchors, audio use, narrative video links, Gameplay source-row,
skill, talent, progression, default-weapon, and required-item relationships,
table ownership, exported files, character recovery manifest contents, asset-map
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
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 322
Gameplay entries, 409 skills, 556 talent nodes, 958 progression nodes, 53 item
nodes, and edges for source rows, default weapons, skill/talent membership,
progression records, and required item costs. Example exact queries:

```bat
python tools\endfield_source_graph.py query chr_0017_yvonne --kind character
python tools\endfield_source_graph.py query wpn_pistol_0001 --kind weapon
```

The same build now links Gameplay entries to exported asset nodes by exact
Gameplay ID, icon ID, or model-path stem containment in asset paths. The fast
CN verification build produced 3,652 `has_gameplay_asset` edges: 1,675 from
weapons, 1,097 from characters, and 880 from equipment. Evidence values record
the source field (`id`, `iconId`, or `modelPath`) so later audits can separate
broad ID matches from icon/model-path matches.

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

Known parser limits are acceptable for current use:

- lightweight IL2CPP metadata parsing can leave generic/array/byref type
  indexes unresolved in reports;
- full asset-map ingestion is expensive and should be skipped unless needed;
- legacy local `character_recovery/` report directories may exist, but the
  maintained graph emits the top-level recovery candidate JSON.
