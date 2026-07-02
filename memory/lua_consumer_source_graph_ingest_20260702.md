# Lua Consumer Source Graph Ingest - 2026-07-02

## Scope

Promoted the generated Lua consumer reference audit into the source graph.

Input:

- `reports/mission_order/lua_consumer_reference_audit.json`

The audit scans extracted VFS Lua from Persistent and StreamingAssets, finds
`Tables.*` consumers, matches them to exported table JSON files, and records
focus tags for story/UI areas such as SNS, RemoteComm, dialog, map marks, and
mission UI.

## Graph Model

The graph now emits:

- `lua_module` nodes keyed by unique Lua module path.
- `lua_audit_has_module` edges from the audit dataset to each module.
- `lua_module_references_table` edges from Lua modules to matched exported
  `table` nodes.
- edge data with use count, focus tags, export roots, and matched table paths.
- `lua_table_reference` aliases on table nodes for the Lua-side `Tables.*`
  spelling.

Unmatched Lua table names remain in the generated audit report rather than
being promoted to table edges.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\lua_consumer_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1685738 nodes, 3116626 edges, 2274221 aliases
```

Focused counts:

```text
NODE lua_module 652
EDGE lua_audit_has_module 652
EDGE lua_module_references_table 2018
LUA_MODULES_FROM_AUDIT 652
FOCUSED_LUA_TABLE_EDGES 634
```

The audit currently reports `2027` module-to-table candidates. Of those, `2018`
match exported table files and are ingested as graph edges; `9` are unmatched
and remain report-only evidence.
