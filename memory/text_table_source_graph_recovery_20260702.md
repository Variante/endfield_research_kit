# TextTable Source Graph Recovery - 2026-07-02

## Scope

Recovered explicit source graph coverage for `TextTable.json`, the last
non-I18n structured table file that was still outside named semantic ingestion
after the recent compact table recovery passes.

`TextTable` contains text-key rows such as `ATTRIBUTE_HINT_BUFF_FORMAT`,
`ActivityGuide_Go`, and `CS_COLLECTION_TOAST_BAG_FULL`. Each row maps a stable
text key to an i18n id payload. In this export, inline `text` values are empty,
so the semantic value is the key-to-i18n-id reference rather than localized
string content.

## Graph Model

The graph now emits:

- `text_table_key` nodes keyed by the original `TextTable` row key.
- `defines_text_table_key` edges from `table_row` to `text_table_key`.
- `text_table_key_i18n_text` edges from each text key to the existing
  `i18n_text` node when the row has a nonzero i18n id.
- aliases of kind `text_table_key` for direct query lookup.

This keeps `TextTable` separate from `setting_text_key`, which is specific to
settings/gamepad hint keys, while still reusing the existing `i18n_text` graph
nodes.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\text_table_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1684345 nodes, 3113627 edges, 2272347 aliases
```

Focused semantic counts:

```text
NODE text_table_key 18636
NODE i18n_text 99563
EDGE defines_text_table_key 18636
EDGE text_table_key_i18n_text 18250
TEXTTABLE_ROWS 18636
```

The missing `text_table_key_i18n_text` edges are rows with empty, zero, or
otherwise non-linkable i18n ids, matching existing `i18n_text` behavior.

The normalized non-I18n structured table census now reports:

```text
UNCOVERED_NONEMPTY_NO_I18N 0
```
