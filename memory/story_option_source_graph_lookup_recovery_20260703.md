# Story Option Source Graph Lookup Recovery - 2026-07-03

## Finding

Runtime Jump option-route audit evidence was already present in the source
graph, including conflict nodes and expected/runtime first-line edges. The
problem was lookup ergonomics: querying an exact option id such as
`option_dlg_e6m1_10_4_002` seeded on the structured `dialog_option` table node
instead of the generated WebUI `option` node.

That made the useful route evidence easy to miss unless the query was manually
constrained with `--kind option`.

## Graph Change

`tools/endfield_source_graph.py` now adds aliases to generated WebUI story
option nodes during `ingest_webui_story()`:

- `option_id`: exact option id, for example `option_dlg_e6m1_10_4_002`;
- `option_text`: display text, for text-based lookup.

The dialog table node remains separate. This only changes source-graph lookup
resolution; it does not alter Story recovery or promote any runtime-route
mapping.

## Validation

Cheap checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Focused graph ingest:

```bat
python -c "... SourceGraphBuilder(db_path='tmp/option_alias_runtime_audit.sqlite').ingest_webui_story(); ingest_runtime_option_route_audits() ..."
```

Validation SQL:

- alias for `option_dlg_e6m1_10_4_002` now resolves to
  `option:option_dlg_e6m1_10_4_002`;
- `option:option_dlg_e6m1_10_4_002` has `has_runtime_route_conflict` edges from
  the Runtime Jump audit reports.

Query validation:

```bat
python tools\endfield_source_graph.py query option_dlg_e6m1_10_4_002 --db tmp\option_alias_runtime_audit.sqlite --limit 24
```

The seed node is now `option:option_dlg_e6m1_10_4_002`. The first-node neighbors
show:

- `has_runtime_route_conflict`;
- inferred `option_first_line` / `option_path_line` to
  `dlg_e6m1_10_003`;
- runtime audit `runtime_audit_runtime_first_line` and
  `runtime_audit_directional_first_line` to `dlg_e6m1_10_016`;
- nearby Runtime Jump clip evidence.

## Follow-Up

This improves graph evidence discovery for the known contradictory runtime-route
cases. It does not make the Runtime Jump evidence promotable; the current audit
still says the unresolved groups do not pass the strict automatic route rule.
