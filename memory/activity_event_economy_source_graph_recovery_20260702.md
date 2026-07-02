# Activity Event Economy Source Graph Recovery - 2026-07-02

## Scope

Extended `tools/endfield_source_graph.py` activity catalog ingestion for the
small event-economy tables that were still only visible as raw table rows:

- `ActivityLimitedFormulaTable`
- `ActivityLimitedFormulaSettlementTable`
- `ActivityRankInfoTable`
- `ActivityShopAdditionalTable`
- `ActivitySubmitTextTable`
- `ActivityHighDifficultyTable`
- `ActivityStaminaRefundBgStateTable`

## Recovered Semantics

- Limited formula events now resolve to a semantic `activity_limited_formula`
  node linked to the base activity, shop group, money item, end stage, per-stage
  completion/incompletion jumps and i18n text, shop-lock rows, required
  time-limited factory recipes, and time-limited items.
- Formula settlement data now links the limited formula to settlement nodes and
  settlement trade items, preserving trade money counts on the edge data.
- Activity rank info now resolves leaderboard metadata and NPC rank rows, with
  NPC head icons as asset aliases, name text edges, and business-card topic
  refs.
- Activity shop additions now link shop group metadata to activity ids,
  activity currency items, banner assets, and close-countdown text.
- Submit text rows now expose the activity submit lock text/toast i18n tags as
  queryable nodes.
- High-difficulty activity config rows now expose background-node asset aliases.
- Stamina-refund background-state rows now expose background state names and
  `audioOnOpen` references.

## Validation

Built a temporary graph with:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_event_economy_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `activity_limited_formula`: 1 node
- `activity_limited_formula_stage`: 4 nodes
- `activity_limited_formula_shop_lock`: 2 nodes
- `activity_rank_info`: 3 nodes
- `activity_rank_npc`: 17 nodes
- `activity_shop_additional`: 1 node
- `activity_submit_text`: 2 nodes
- `activity_high_difficulty_config`: 4 nodes
- `activity_stamina_refund_bg_state`: 2 nodes

Representative edge counts:

- `activity_limited_formula_recipe`: 9
- `activity_limited_formula_item`: 8
- `activity_limited_formula_settlement_trade_item`: 4
- `activity_rank_npc_topic`: 17
- `activity_shop_additional_money_item`: 1
- `activity_submit_food_locked_text`: 2
- `activity_stamina_refund_bg_state_open_audio`: 2

The temporary build reported `1,627,997` nodes, `3,056,428` edges, and
`2,234,571` aliases.
