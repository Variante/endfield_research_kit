# Model Config Asset Binding Status - 2026-07-06

## Scope

This pass updated the current P6 status after the source graph gained
`model_config_asset_entity` evidence and a generated binding report.

The original 2026-07-01 audit recorded a 0-match baseline between decoded
`model_config_model` rows and renderable `asset_entity` groups. The current
generated report shows that baseline is now stale, but the hardest P6 target is
still open.

## Current Counts

Generated report:
`reports/source_graph/model_config_asset_binding_candidates.json`

| Metric | Count |
| --- | ---: |
| decoded `model_config_model` rows | 1,280 |
| `asset_entity` rows | 10,678 |
| direct `model_config_asset_entity` edges | 215 |
| candidate entity matches | 225 |
| strong exact graph-edge rows | 200 |
| ambiguous graph-edge rows | 10 |
| name-only candidate rows | 10 |
| referenced rows with no exported renderable candidate | 161 |
| runtime-only or unreferenced rows | 899 |

The new source-graph shortcut is:

```bat
python tools\endfield_source_graph.py model-bindings --status strong_exact_graph_edge --limit 5
python tools\endfield_source_graph.py model-bindings --status candidate_name_match --limit 5
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate --term ore_cluster --limit 5
```

## Remaining Gap

The original P6 success target included the `int_doodad_ore_cluster_*` family.
Those rows remain unresolved in the current generated report:

| Model id | World uses | Interactive uses | Radius | Status |
| --- | ---: | ---: | --- | --- |
| `int_doodad_ore_cluster_iron` | 92 | 0 | true | `no_exported_renderable_candidate` |
| `int_doodad_ore_cluster_originium` | 52 | 2 | true | `no_exported_renderable_candidate` |

This means the graph now has nonzero model-config to asset-entity edges, but
the ore-cluster bridge still needs prefab/component or asset-map evidence. Do
not promote additional speculative edges from name similarity alone.
