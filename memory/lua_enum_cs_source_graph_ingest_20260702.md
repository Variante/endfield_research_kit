# Lua enum and CS source graph ingest - 2026-07-02

## Context

`reports/mission_order/lua_consumer_reference_audit.json` now contributes more
than table-consumer evidence to `tools/endfield_source_graph.py`.

The source graph ingests each Lua module's `topEnums` and `topCsBeyond` audit
summaries as queryable references:

- `lua_enum_reference` nodes linked by `lua_module_references_enum`
- `lua_cs_reference` nodes linked by `lua_module_references_cs_api`

This preserves semantic Lua dependencies such as mission state enums, SNS chat
types, activity states, and `CS.Beyond.*` runtime constants without requiring
future investigations to re-open the raw audit JSON.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\lua_enum_cs_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,686,850 nodes, 3,119,049 edges, 2,275,243 aliases
- `lua_module`: 724 nodes
- `lua_enum_reference`: 237 nodes
- `lua_cs_reference`: 251 nodes
- `lua_module_references_table`: 2,018 edges
- `lua_module_references_enum`: 372 edges
- `lua_module_references_cs_api`: 323 edges

Top enum edge targets include `ActivityConditionalStageState.*`,
`SNSChatType.Group`, `FacBuildingState.Normal`, and `MarkType`.
Top CS edge targets include `CS.Beyond.Gameplay.MissionSystem.*`,
`CS.Beyond.UI.UIConst.AnimationState.In`, and logging/friend constants.
