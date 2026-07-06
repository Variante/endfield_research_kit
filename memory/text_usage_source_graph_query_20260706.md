# Text Usage Source Graph Query - 2026-07-06

## Scope

Added a compact `text-usage` query to `tools/endfield_source_graph.py` for
following stable text keys, raw i18n ids, and domain rows back to their
semantic consumers.

This fills the lookup gap between low-level `query` output and the existing
domain-specific usage commands. The graph already contained `i18n_text`,
`text_table_key`, dialog, UI, item/economy, mission, help/tutorial, factory,
tag, and reference-file edges; the new command groups those edges into a
single text-first view.

## Query Behavior

Examples:

```bat
python tools\endfield_source_graph.py text-usage ActivityGuide_Go --limit 8
python tools\endfield_source_graph.py text-usage -3364611944259307077 --kind i18n_text --limit 8
python tools\endfield_source_graph.py text-usage 3657856467240665913 --kind i18n_text --limit 8
```

The command resolves text-first by default, with `i18n_text` and
`text_table_key` before generic graph lookup so numeric i18n ids do not get
lost behind unrelated numeric asset/config names.

For non-i18n seeds such as `text_table_key:ActivityGuide_Go`, output includes:

- direct text relations such as `defines_text_table_key`;
- canonical `i18nTextIds`, for example `i18n_text:1641306292803804709`;
- `i18nConsumers`, so a text key can be followed through its linked i18n id.

For raw i18n seeds, output focuses on consumer categories. For example
`-3364611944259307077` resolves to shop/giftpack usage via
`cash_shop_name_text`, `giftpack_cash_shop_label_text`, and
`giftpack_cash_shop_show_name_text`. `3657856467240665913` resolves to
factory blueprint name usage through `factory_system_blueprint_name_text`.

## Interpretation

The strongest semantic proof is a domain-specific edge such as
`mission_runtime_name_text`, `item_desc_text`, `factory_system_blueprint_name_text`,
or `ui_label_name_text`.

Broad reference-file edges such as `i18n_reference_file_references_text` are
useful for locating files, but they are static scan evidence and should not be
treated as runtime UI occurrence proof.

The default graph may include localized display values for some `i18n_text`
nodes when source tables have them, but raw i18n ids remain the stable join key.
Graphs built without `--include-i18n-values` should still be interpreted as
id/reference recovery, not complete localization recovery.

## Validation

Validated the tool syntax and smoke lookups:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py text-usage ActivityGuide_Go --limit 8
python tools\endfield_source_graph.py text-usage -3364611944259307077 --kind i18n_text --limit 8
python tools\endfield_source_graph.py text-usage 3657856467240665913 --kind i18n_text --limit 8
```

Observed categories included `textTableKeys`, `i18nReferenceFiles`,
`itemsEconomy`, `i18nItemsEconomy`, `factory`, and `i18nFactory`.
