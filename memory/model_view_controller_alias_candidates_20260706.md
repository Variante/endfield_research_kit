# Model-View Controller Alias Candidates - 2026-07-06

## Change

`tools/endfield_source_graph.py` now emits model-view-controller alias evidence
inside `reports/source_graph/model_config_asset_binding_candidates.json`.

The existing `model-bindings` classification remains conservative:

- Direct `model_config_asset_entity` edges still drive
  `strong_exact_graph_edge` and `ambiguous_graph_edge`.
- Name-token matches still drive `candidate_name_match`.
- Controller-derived asset hints do not promote a row to a resolved renderable
  binding.

Instead, each record may now include `controllerAliasEntities`, derived from
model-view-state-controller clip/effect references that map cleanly to existing
`asset_entity` bases.

## Why

The `int_switch_union_v2` investigation showed that some unresolved model
config ids do not share an exported renderable stem, but their decoded
`ModelViewStateControllerData` references animation/effect names that do map to
exported model entities. The concrete example is:

- model config: `int_switch_union_v2`
- controller: `model_view_state_controller:int_switch_union_v2`
- controller refs:
  - `A_interactive_universalswitch+1_001_01_closeidle_01`
  - `A_interactive_universalswitch+1_001_01_open_01`
  - `A_interactive_universalswitch+1_001_01_openidle_01`
  - `A_interactive_universalswitch+1_001_01_close_01`
  - `P_interactive_universalswitch+1_001_01`
- exported entity candidate:
  `asset_entity:StreamingAssets/interactive_universalswitch_1_001_01`

This is strong alias evidence, but not enough by itself to assert that the
controller reference is the full renderable prefab binding. Surfacing it in the
report makes follow-up work repeatable without changing the binding status.

## Validation

The normal report path under `reports/source_graph/` was not rewritten during
this pass because the current file handle refused writes in the sandbox. To
validate the generator without mutating ignored report artifacts, the tool was
run with `GRAPH_DIR` redirected to:

```text
C:\Users\Xine\AppData\Local\Temp\source_graph_model_binding_validate
```

Validation command:

```bat
python -c "import os, sqlite3; from pathlib import Path; import tools.endfield_source_graph as g; g.GRAPH_DIR = Path(os.environ['MODEL_BINDING_VALIDATE_DIR']); conn=sqlite3.connect(g.DEFAULT_DB); conn.row_factory=sqlite3.Row; g.emit_model_config_asset_binding_candidates(conn); conn.close()"
```

The generated validation JSON reported:

- `controllerAliasCandidateRows=12`
- `int_switch_union_v2` still has
  `status=no_exported_renderable_candidate`.
- `int_switch_union_v2.controllerAliasEntities` contains aliases from the
  four `A_interactive_universalswitch+1_001_01_*` clip refs and the
  `P_interactive_universalswitch+1_001_01` effect ref to
  `asset_entity:StreamingAssets/interactive_universalswitch_1_001_01`.

## Next Checks

- On the next full source-graph refresh, confirm the committed generator writes
  the new field into the normal `reports/source_graph/` report artifacts.
- Add a narrow CLI view if repeated investigation needs filtering by
  `controllerAliasEntities`.
- For switch-family recovery, compare the alias evidence against prefab or
  AnimeStudio map data before promoting any controller alias to a direct
  renderable binding.
