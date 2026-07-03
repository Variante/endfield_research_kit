# Optional i18n Value Source Graph Recovery - 2026-07-03

## Context

The exported table coverage audit found that the only nonempty structured
tables still absent from the source graph were the multilingual
`I18nTextTable_*` files. The existing graph already creates canonical
`i18n_text:<id>` nodes and `uses_i18n_text` references from Story, gameplay,
Lua virtual-table evidence, and selected structured tables, but it did not
store per-language localized values.

Adding every language by default would materially increase graph size. The
current export has fourteen language files and would add roughly 1.6 million
`i18n_text_value` nodes plus matching table/value/id edges. This is useful for
localization investigation, but too large for the default source-graph build.

## Change

`tools/endfield_source_graph.py` now supports an opt-in i18n value ingest:

```bat
python tools\endfield_source_graph.py build --include-i18n-values
python tools\endfield_source_graph.py build --include-i18n-values --i18n-value-language EN --i18n-value-language JP
```

The ingest reads `export_full/structured/StreamingAssets/Table/I18nTextTable_*.json`
one file at a time and creates:

- `dataset:i18n_text_tables`
- `table:I18nTextTable_<LANG>` nodes with language and row counts
- `language:<LANG>` nodes
- `i18n_text_value:<LANG>:<textId>` nodes with localized text, length, blank,
  and trailing-tab flags
- `structured_i18n_table` file rows

Edges:

- `has_i18n_text_table`
- `i18n_text_table_language`
- `defines_i18n_text_value`
- `i18n_text_value_for_id`

The value nodes link back to canonical `i18n_text:<id>` nodes. They do not add
localized aliases, because localized strings are often long, repeated, or
unsuitable as stable query aliases.

## Validation

Syntax and diff checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A limited real EN/JP build was attempted:

```bat
python tools\endfield_source_graph.py build --db tmp\i18n_value_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups --include-i18n-values --i18n-value-language EN --i18n-value-language JP
```

It did not finish within a 15 minute timeout, and the still-running temp-build
process was stopped. This reinforces that multilingual value ingestion should
remain opt-in and should be used with language filters when possible.

A focused fixture validation directly exercised `ingest_i18n_text_values()`
with EN, JP, and CN test tables while filtering to EN and JP. Results:

| Kind | Count |
|---|---:|
| `i18n_text_value` nodes | 5 |
| `i18n_text` nodes | 4 |
| `language` nodes | 2 |
| `table` nodes | 2 |
| `dataset` nodes | 1 |
| `defines_i18n_text_value` edges | 5 |
| `i18n_text_value_for_id` edges | 5 |
| `has_i18n_text_table` edges | 2 |
| `i18n_text_table_language` edges | 2 |

Additional fixture checks:

- EN produced 3 value nodes and JP produced 2.
- CN produced 0 value nodes because it was filtered out.
- Text id `0` produced 0 value nodes.
- Blank string metadata set `isBlank: true`.
- A trailing tab string set `hasTrailingTab: true`.
- Two `structured_i18n_table` file rows were written, one each for EN and JP.

## Notes

The default graph build still skips localized value ingestion. Use
`--include-i18n-values` only when the investigation needs actual localized
strings, and prefer `--i18n-value-language` filters for targeted work.
