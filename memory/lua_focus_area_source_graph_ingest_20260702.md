# Lua focus area source graph ingest - 2026-07-02

## Context

`reports/mission_order/lua_consumer_reference_audit.json` classifies Lua
consumer modules into high-value runtime/UI focus areas. These categories are
now queryable in `tools/endfield_source_graph.py` as `lua_focus_area` nodes
linked from `lua_module` nodes by `lua_module_in_focus_area`.

This makes the original Lua consumer layer easier to ask about directly:

- which modules are related to mission/runtime task display
- which modules are map marker consumers
- which modules bridge SNS, remote communication, or dialog tables

The graph still treats these as evidence categories from static Lua references,
not as proof of runtime execution order.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\lua_focus_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,686,855 nodes, 3,119,360 edges, 2,275,248 aliases
- `lua_focus_area`: 5 nodes
- `has_lua_focus_area`: 5 edges
- `lua_module_in_focus_area`: 306 edges
- retained `lua_module`: 724 nodes
- retained `lua_module_references_enum`: 372 edges
- retained `lua_module_references_cs_api`: 323 edges

Focus-area module coverage:

| Focus area | Modules | Hit count |
| --- | ---: | ---: |
| mission | 95 | 902 |
| mapmark | 86 | 1,127 |
| sns | 57 | 355 |
| remotecomm | 36 | 600 |
| dialog | 32 | 164 |

Sidecar investigations on this round identified two promising next slices:

- asset/model semantics: use `model_config_asset_binding_candidates.json` to
  improve the `model_config_model` to renderable/prefab bridge for 161
  referenced-but-unbound model rows
- numerical/gameplay semantics: continue using Lua consumer evidence to tie
  gameplay table usage to runtime/UI modules without claiming formula execution
