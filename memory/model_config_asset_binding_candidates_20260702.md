# Model Config Asset Binding Candidate Report - 2026-07-02

## Scope

Added a source-graph follow-up report for decoded `model_config_model` rows and
exported `asset_entity` renderable groups.

The report is generated under `reports/source_graph/` as:

- `model_config_asset_binding_candidates.json`
- `model_config_asset_binding_candidates.md`

This intentionally does not promote new speculative graph edges. It classifies
current evidence from existing graph nodes and the conservative
`model_config_asset_entity` matcher.

## Recovered Understanding

The previous audit showed the important gap:

- decoded gameplay model rows were queryable;
- exported renderable entity groups were queryable;
- but the bridge between gameplay model ids and renderable groups was unclear.

The report now makes that gap measurable per model row and separates strong
matches from discovery-grade matches:

- `strong_exact_graph_edge`: one direct graph edge whose token normalizes
  exactly to the exported asset-entity base.
- `ambiguous_graph_edge`: existing graph edge exists, but it is multi-edge,
  prefix-expanded, or otherwise not a single exact token/base match.
- `candidate_name_match`: conservative candidate entity match without direct
  edge.
- `no_exported_renderable_candidate`: world/interactive gameplay references
  exist, but no renderable entity candidate was found.
- `runtime_only_or_unreferenced`: no current world/interactive consumer and no
  renderable candidate.

It also records candidate bases, prefab stems, radius presence, world entity use
count, interactive template use count, direct binding edges, and candidate
entity metadata.

## Validation

Built a temporary graph with follow-up reports enabled:

```bat
python tools\endfield_source_graph.py build --db tmp\model_binding_strength_source_graph.sqlite --skip-asset-maps --skip-reference-rows
```

Result:

- `1,628,129` nodes
- `3,056,720` edges
- `2,234,682` aliases
- wrote follow-up indexes under `reports/source_graph/`

Generated report summary:

- Model config rows: 1,201
- Asset entities: 10,678
- Direct `model_config_asset_entity` edges: 215
- Strong exact graph-edge rows: 200
- Ambiguous graph-edge rows: 10
- Candidate entity matches: 215
- `strong_exact_graph_edge`: 200
- `ambiguous_graph_edge`: 10
- `no_exported_renderable_candidate`: 161
- `runtime_only_or_unreferenced`: 830

Read-only edge-strength checking also found 203 exact-token-base edges and 12
prefix-expanded edges among the 215 direct edges. Multi-edge or prefix examples
include `int_collection_coin`, `chr_0031_mifu_postmodel`, and
`int_trigger_dnarrative_paper`.

The report preserves the main unresolved examples from the earlier audit as
top referenced unbound models:

- `int_doodad_ore_cluster_iron`: 92 world uses, no exported renderable
  candidate.
- `int_doodad_ore_cluster_originium`: 52 world uses and 2 interactive uses, no
  exported renderable candidate.
- `int_doodad_flower_1`: 31 world uses, no exported renderable candidate.
- `int_switch_union_v2`: 20 world uses, no exported renderable candidate.

## Follow-Up

The next useful asset recovery step is to find stronger evidence for the 161
referenced unbound models. Filename matching is still insufficient. Stronger
evidence likely needs prefab/component, Unity container/path, or asset-map
relations before adding new graph edges.
