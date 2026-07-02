# Display Micro-Metadata Source Graph Recovery - 2026-07-02

## Scope

Recovered first-class graph coverage for compact display, sharing, storage, and
localization-support tables that were still outside semantic ingestion:

- `ItemStorage`
- `CashShopRecommendTextTable`
- `ShareTable`
- `I18nHotFix`
- `BattleBossOverrideIconTable`

## Recovered Semantics

`ItemStorage` now emits `item_storage_rule` nodes and links each storage bucket
to existing `item_type` nodes through `item_storage_allows_type`.

`CashShopRecommendTextTable` now emits `cash_shop_recommend_text` nodes with
i18n text edges.

`ShareTable` now emits one `share_channel_config` node per row and links each
config to share-channel UI labels. Validation caught that all rows have the same
`envLang` value, so row key is included in the node key to avoid collapsing
distinct configurations.

`I18nHotFix` now emits `i18n_hotfix` and `i18n_hotfix_entry` nodes with text
edges for platform-specific localization override payloads.

`BattleBossOverrideIconTable` now emits `battle_boss_override_icon` nodes and
asset aliases for override icon ids.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\display_micro_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1628784 nodes, 3058046 edges, 2235412 aliases
```

Focused semantic counts:

```text
NODE item_storage_rule 4
NODE cash_shop_recommend_text 4
NODE share_channel_config 3
NODE i18n_hotfix 3
NODE i18n_hotfix_entry 3
NODE battle_boss_override_icon 2
EDGE defines_item_storage_rule 4
EDGE item_storage_allows_type 93
EDGE defines_cash_shop_recommend_text 4
EDGE cash_shop_recommend_text 4
EDGE defines_share_channel_config 3
EDGE share_config_allows_channel 34
EDGE defines_i18n_hotfix 3
EDGE i18n_hotfix_has_entry 3
EDGE i18n_hotfix_text 3
EDGE defines_battle_boss_override_icon 2
```
