# Interactive Mark Binding Reverse Source-Graph Recovery - 2026-07-03

## Scope

`InteractiveMarkDataTable` binds system interactive ids to map mark template ids.
The graph already had forward edges from each `interactive_mark_binding` to its
`system_interactive` and `map_mark_template` targets. This pass adds reverse
lookup edges for those same table rows.

## Added Edges

- `system_interactive_has_mark_binding`
- `map_mark_template_has_interactive_binding`

## Validation

Focused temp graph:
`tmp/interactive_mark_binding_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()` only.

| Edge | Count |
| --- | ---: |
| `interactive_mark_binding_interactive` | 10 |
| `system_interactive_has_mark_binding` | 10 |
| `interactive_mark_binding_mark_template` | 10 |
| `map_mark_template_has_interactive_binding` | 10 |

Node counts in the focused graph:

| Node kind | Count |
| --- | ---: |
| `interactive_mark_binding` | 10 |
| `system_interactive` | 23 |
| `map_mark_template` | 7 |

`python -m py_compile tools\endfield_source_graph.py` passed.
