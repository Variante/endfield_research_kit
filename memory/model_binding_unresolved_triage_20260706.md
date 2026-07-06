# Model Binding Unresolved Triage - 2026-07-06

## Scope

Improved `python tools/endfield_source_graph.py model-bindings` with filters for
world-use count, interactive-template-use count, and resolved sibling evidence.
This makes the asset semantics gap easier to work in small passes: the report
already classifies model config rows, and the CLI can now isolate the model rows
that matter most to placed world objects or interactive templates.

## Current Counts

Current `reports/source_graph/model_config_asset_binding_candidates.json`:

- Model config rows: 1,280
- Asset entity rows: 10,678
- Direct `model_config_asset_entity` edges: 215
- Candidate entity matches: 225

Status counts:

- `strong_exact_graph_edge`: 200
- `ambiguous_graph_edge`: 10
- `candidate_name_match`: 10
- `no_exported_renderable_candidate`: 161
- `runtime_only_or_unreferenced`: 899

## New Filters

Useful commands:

```bat
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate --min-world-uses 20
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate --min-interactive-uses 4
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate --with-siblings
```

The first command currently isolates five high-world-use unresolved rows:

| Model | World uses | Interactive template uses | Notes |
| --- | ---: | ---: | --- |
| `int_doodad_ore_cluster_iron` | 92 | 0 | Ore-cluster family; sibling `int_doodad_ore_cluster_metal_sp` has a strong exported binding. |
| `int_doodad_ore_cluster_originium` | 52 | 2 | Ore-cluster family; same resolved sibling family evidence. |
| `int_doodad_flower_1` | 31 | 0 | No exported renderable candidate found by current token rules. |
| `int_doodad_flower_2` | 23 | 0 | No exported renderable candidate found by current token rules. |
| `int_switch_union_v2` | 20 | 0 | No exported renderable candidate found by current token rules. |

The second command currently isolates fifteen template-heavy unresolved rows.
The highest repeated template users include placeholder/empty postmodels,
`int_fixable_robot`, `int_1x1Cube`, anchor/electric/laser obstacle templates,
and several travel/platform interactives.

The sibling filter currently returns eighteen unresolved rows with at least one
resolved sibling model. These are good candidates for family-level analysis
because the graph proves a nearby naming family has an exported renderable even
when the specific row does not.

## Interpretation

`no_exported_renderable_candidate` does not prove the model is missing from the
game. It means the current exported `asset_entity` index and conservative
model-name token matching did not find a renderable entity for a model config
row that is referenced by world entities or interactive templates.

Common explanations to test next:

- the row is a gameplay/collider/controller-only postmodel with no renderable
- the real exported asset uses a different naming stem than the config row
- the model is nested under a sibling/family prefab
- the asset exists only in an unmodeled bundle or under a non-renderable entity
- the current token matcher misses case, punctuation, or suffix normalization

## Next Step

Start with `int_doodad_ore_cluster_iron` and
`int_doodad_ore_cluster_originium`: they have the largest world placement counts
and a resolved sibling in the same ore-cluster family. Comparing those rows
against `int_doodad_ore_cluster_metal_sp` should show whether missing
renderables are true absences, alternate stems, or family-prefab reuse.
