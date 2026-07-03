# Runtime Metadata Focus Source Graph Recovery - 2026-07-03

## Summary

Promoted the focused portions of `reports/buff_runtime_metadata.json` into the
source graph.

Despite the filename, the current report is a broad IL2CPP metadata catalog for
dialog/option/playable/timeline runtime types. The graph now ingests the
high-value filtered pieces only:

- focus types
- their fields, methods, parameters, and referenced return/parameter/field types
- unresolved type-index usage groups

It intentionally does not ingest all 4,952 `matchedTypes` or 3,849
`memberOnlyTypes`, keeping the graph useful without turning the broad report
into a full metadata mirror.

## Node And Edge Shapes

New node kinds:

- `il2cpp_metadata_report`
- `il2cpp_type`
- `il2cpp_field`
- `il2cpp_method`
- `il2cpp_parameter`
- `il2cpp_image`
- `il2cpp_unresolved_type_index`
- `il2cpp_unresolved_type_usage`

New edge kinds include:

- `il2cpp_metadata_report_focus_type`
- `il2cpp_type_in_image`
- `il2cpp_type_has_field`
- `il2cpp_field_uses_type`
- `il2cpp_type_has_method`
- `il2cpp_method_returns_type`
- `il2cpp_method_has_parameter`
- `il2cpp_parameter_uses_type`
- `il2cpp_metadata_report_unresolved_type_index`
- `il2cpp_unresolved_type_has_usage`
- `il2cpp_type_has_unresolved_usage`

The builder runs this after the timeline option-flow audit so related story and
option runtime evidence sits close together in the source graph.

## Validation

Static checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest called only
`ingest_runtime_metadata_focus_report()` against the current metadata report.

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `il2cpp_metadata_report` nodes | 1 |
| `il2cpp_type` nodes | 350 |
| `il2cpp_field` nodes | 274 |
| `il2cpp_method` nodes | 718 |
| `il2cpp_parameter` nodes | 806 |
| `il2cpp_image` nodes | 2 |
| `il2cpp_unresolved_type_index` nodes | 211 |
| `il2cpp_unresolved_type_usage` nodes | 473 |
| `file` nodes | 1 |
| `il2cpp_metadata_report_focus_type` edges | 12 |
| `il2cpp_type_in_image` edges | 12 |
| `il2cpp_type_has_field` edges | 274 |
| `il2cpp_field_uses_type` edges | 274 |
| `il2cpp_type_has_method` edges | 718 |
| `il2cpp_method_returns_type` edges | 718 |
| `il2cpp_method_has_parameter` edges | 806 |
| `il2cpp_parameter_uses_type` edges | 806 |
| `il2cpp_metadata_report_unresolved_type_index` edges | 211 |
| `il2cpp_unresolved_type_has_usage` edges | 473 |
| `il2cpp_type_has_unresolved_usage` edges | 473 |
| `il2cpp_metadata_report` file rows | 1 |

Source report summary:

- matched types: 4,952
- focus types: 12
- member-only types: 3,849
- body target methods: 0
- unresolved type indexes: 211

## Notes

This closes a graph gap between data-table semantics and runtime code metadata.
Queries can now start from dialog/option runtime classes such as
`Beyond.Gameplay.Core.DialogTimelineManager` and inspect their fields, methods,
parameter types, return types, and unresolved metadata type-index usage.
