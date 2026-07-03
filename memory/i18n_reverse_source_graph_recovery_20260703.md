# I18n Reverse Source Graph Recovery - 2026-07-03

## Context

The source graph had broad forward text-consumer links through
`uses_i18n_text` and `text_table_key_i18n_text`, but i18n-centered queries could
not directly enumerate most consuming gameplay, UI, economy, or metadata nodes.

## Change

`tools/endfield_source_graph.py` now emits:

- `i18n_text_used_by` for generic `uses_i18n_text` consumers.
- `i18n_text_used_by_text_table_key` for structured text-table key rows.

The generic reverse edge records the more specific text edge kind in payload
data as `edgeKind` when the forward edge came from a domain-specific text helper
such as `item_desc_text`, `tutorial_step_icon_desc_text`, or
`game_mechanic_desc_text`.

## Validation

Syntax:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Targeted temporary DB:

```bat
tmp/i18n_reverse_structured_subset.sqlite
```

The temporary DB ran the structured-table semantic ingesters that exercise the
shared i18n helpers and direct generic i18n-use sites, while skipping the
heavier asset/story/decoded-config passes.

Counts:

- `uses_i18n_text`: 27,490 / reverse 27,490
- `text_table_key_i18n_text`: 18,250 / reverse 18,250

Sample reverse rows showed text ids pointing back to item descriptions, kite
station tasks, wiki tutorial pages, game mechanics, character tutorial steps,
map mark templates, submit items, and item gather text nodes with original
specific edge-kind payloads.
