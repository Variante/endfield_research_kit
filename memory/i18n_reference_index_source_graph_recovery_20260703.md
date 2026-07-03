# I18n Reference Index Source Graph Recovery - 2026-07-03

## Summary

Promoted `reports/i18n_reference_index_CN.json` into the source graph.

The report scans exported JSON files for localized text IDs and records which
files are already handled by Story build paths versus still outside direct
Story handling. The graph now exposes file-level i18n usage across broad
gameplay/UI/system data, not just Story/Text Tables.

This is reference evidence only. It does not add new WebUI pages or assert that
every referenced ID is user-facing.

## Node And Edge Shapes

New node kinds:

- `i18n_reference_file`
- `i18n_reference_field`
- `i18n_reference_scan_mode`
- `i18n_reference_build_story_mode`

New edge kinds include:

- `i18n_reference_index_has_file`
- `file_has_i18n_reference_summary`
- `i18n_reference_file_top_field`
- `i18n_reference_file_scan_mode`
- `i18n_reference_file_build_story_mode`
- `i18n_reference_file_references_text`
- `i18n_text_used_by_reference_file`
- `i18n_reference_index_top_text`
- `i18n_top_text_used_by_file`
- `i18n_reference_index_build_story_direct_table`

The builder runs this pass after text-reference semantics and before optional
i18n text-value ingestion, so it can attach broad text-reference evidence while
still allowing value-table ingestion to enrich the same `i18n_text` nodes.

## Validation

Static checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest called only `ingest_i18n_reference_index()`
against the current CN report.

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `i18n_reference_file` nodes | 538 |
| `i18n_reference_field` nodes | 1 |
| `i18n_reference_scan_mode` nodes | 1 |
| `i18n_reference_build_story_mode` nodes | 2 |
| `i18n_text` nodes | 108,679 |
| `table` nodes | 52 |
| `file` nodes | 481 |
| `dataset` nodes | 1 |
| `i18n_reference_index_has_file` edges | 480 |
| `file_has_i18n_reference_summary` edges | 480 |
| `i18n_reference_file_top_field` edges | 480 |
| `i18n_reference_file_scan_mode` edges | 480 |
| `i18n_reference_file_build_story_mode` edges | 480 |
| `i18n_reference_file_references_text` edges | 220,119 |
| `i18n_text_used_by_reference_file` edges | 220,119 |
| `i18n_reference_index_top_text` edges | 80 |
| `i18n_top_text_used_by_file` edges | 381 |
| `i18n_reference_index_build_story_direct_table` edges | 52 |
| `i18n_reference_index` file rows | 1 |

Handled split from `i18n_reference_file` node data:

| `handledByBuildStory` | Files |
| --- | ---: |
| `true` | 80 |
| `false` | 400 |
| unset top-id-only file nodes | 58 |

The source report summary records 480 files with references, 108,679 referenced
IDs, 109,992 recovered IDs, and 1,151 unrecovered referenced IDs.

## Notes

This closes a graph coverage gap for localized text references outside the
Story-focused builders. Queries can now start from a text ID and find exported
JSON files that reference it, or start from a non-story table file and inspect
which i18n IDs it carries.
