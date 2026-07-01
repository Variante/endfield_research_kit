# Model Config To Renderable Asset Binding Audit - 2026-07-01

## Scope

This note audits the current gap between exact decoded `ModelTable` config rows
and exported renderable `asset_entity` groups in the source graph. It uses the
fast CN temp graph from the latest semantic pass:

```bat
tmp\source_graph_subgame.sqlite
```

The goal is not to infer missing bindings, but to document what current evidence
proves and where the next asset-semantics work should focus.

## Current Evidence

Read-only coverage query:

```bat
python - <<PY
import json, sqlite3
from pathlib import PurePosixPath
c = sqlite3.connect('tmp/source_graph_subgame.sqlite')
models = []
for node_id, name, data in c.execute("SELECT id,name,data FROM nodes WHERE kind='model_config_model'"):
    payload = json.loads(data or '{}')
    prefab = payload.get('prefabPath') or ''
    models.append((node_id, name.lower(), PurePosixPath(prefab).stem.lower(), prefab))
entities = []
for node_id, name, data in c.execute("SELECT id,name,data FROM nodes WHERE kind='asset_entity'"):
    payload = json.loads(data or '{}')
    base = (payload.get('modelBase') or name or '').lower()
    entities.append((node_id, base, payload))
entity_bases = {base for _, base, _ in entities if base}
print('model_config_model', len(models))
print('asset_entity', len(entity_bases))
print('exact modelId->entity', sum(1 for _, m, _, _ in models if m in entity_bases))
print('exact prefabStem->entity', sum(1 for _, _, s, _ in models if s in entity_bases))
print('prefix modelId->entity', sum(1 for _, m, _, _ in models if any(e.startswith(m) for e in entity_bases)))
print('prefix prefabStem->entity', sum(1 for _, _, s, _ in models if s and any(e.startswith(s) for e in entity_bases)))
PY
```

Observed counts:

- `model_config_model`: 1,201
- `asset_entity`: 10,424
- exact `modelId` to `asset_entity`: 0
- exact prefab stem to `asset_entity`: 0
- prefix `modelId` to `asset_entity`: 0
- prefix prefab stem to `asset_entity`: 0
- `model_config_asset_entity`: 0
- `interactive_template_asset_entity`: 0
- `has_gameplay_asset_entity`: 132, currently from other gameplay asset paths
- distinct model rows with `world_entity_uses_model`: 22
- distinct model rows with `interactive_template_uses_model`: 187

## Examples

Highly used decoded model rows currently have no renderable entity edge:

| Model id | World entity uses | Interactive template uses | Prefab path |
| --- | ---: | ---: | --- |
| `int_doodad_ore_cluster_iron` | 92 | 0 | `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_iron_postmodel.prefab` |
| `int_doodad_ore_cluster_originium` | 52 | 2 | `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_ore_cluster_originium_postmodel.prefab` |
| `int_doodad_flower_1` | 31 | 0 | `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_doodad_flower_1_postmodel.prefab` |
| `int_switch_union_v2` | 20 | 0 | `Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_switch_union_v2_postmodel.prefab` |

Renderable asset groups are present, but many are named by exported mesh/entity
bases rather than decoded config `modelId` or prefab stem. For example:

```bat
python tools\endfield_source_graph.py used-by actor_endminf_body_01 --db tmp\source_graph_subgame.sqlite --kind asset_entity --limit 8
```

returns grouped LOD model assets for `actor_endminf_body_01`, but `usedBy` is
empty. This proves the renderable grouping exists while the semantic owner link
is still missing.

The decoded config side is also queryable:

```bat
python tools\endfield_source_graph.py query int_movingplat --db tmp\source_graph_subgame.sqlite --kind model_config_model --limit 10
```

This returns `model_config_model` rows and prefab-path aliases such as
`Assets/Beyond/DynamicAssets/Gameplay/Interactives/PostModels/int_movingplat_10mx10m_postmodel.prefab`,
but no `model_config_asset_entity` edge.

## Interpretation

Current evidence supports these conclusions:

- The source graph can now identify which decoded model rows are used by world
  entities, interactive templates, radii, and related decoded config records.
- The asset index can group many exported renderable LOD meshes into
  `asset_entity` nodes.
- There is not yet a verified naming bridge from decoded `ModelTable` ids or
  prefab stems to exported renderable groups for these interactive/postmodel
  objects.
- Naive exact and prefix string matching is insufficient. The missing bridge
  likely requires prefab/component evidence, asset-map evidence, or a recovered
  Unity object/container relation rather than filename matching alone.

## Recommended Next Step

Build a focused model-binding audit that classifies each `model_config_model`
row by:

- `modelId` and prefab stem
- radius row presence
- interactive template consumers
- world entity consumers
- candidate exported models/materials/textures from asset-map or container
  evidence
- status: exact, candidate, ambiguous, no exported renderable, or likely
  runtime-only/postmodel

Do not add source-graph `model_config_asset_entity` edges until the bridge has
stronger evidence than exact or prefix filename similarity.
