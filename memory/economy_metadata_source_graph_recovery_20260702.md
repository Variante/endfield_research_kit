# Economy Metadata Source Graph Recovery - 2026-07-02

## Scope

Added source-graph semantics for small economy and settlement metadata tables
that were still only visible as raw rows:

- `SettlementTagTable`
- `SettlementConst`
- `ShopGroupDomainTable`
- `ShopManualRefreshTable`
- `ShopMonthlyPassRewardTable`
- `SpaceshipDomainMoneyExchangeRateDataTable`
- `WaterDroneLiquidTable`
- `MoneyConsumeTable`
- `MoneyGainTable`

## Recovered Semantics

- Settlement tags now link to their settlement ids, boost character tags, name
  text, description text, and numeric profit-rate fields.
- Settlement constants now expose mission and item references where the scalar
  value is an id.
- Domain shop groups now link to gameplay domains, background asset aliases, and
  channel partner nodes.
- Manual shop refreshes now expose per-step cost curves. The current export has
  four `shop_spaceship_credit` steps costing `item_spaceship_credit` x80, x120,
  x160, and x200.
- Monthly pass rewards now link `payshop_giftpack_monthlycard` to its goods node
  and item reward/count rows.
- Spaceship domain exchange rates now link coupon items to their numeric rates.
- Water drone liquid rows now link liquid items to their rate.
- Money gain and consume source-type rows now expose their i18n names.

## Validation

Built a temporary quick graph:

```bat
python tools\endfield_source_graph.py build --db tmp\economy_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `settlement_tag`: 15 nodes
- `settlement_const`: 5 nodes
- `domain_shop_channel_partner`: 5 nodes
- `shop_manual_refresh_step`: 4 nodes
- `shop_monthly_pass_reward`: 1 node
- `domain_money_exchange_rate`: 2 nodes
- `water_drone_liquid`: 3 nodes
- `money_consume_source`: 12 nodes
- `money_gain_source`: 15 nodes

Representative edge counts:

- `settlement_tag_for_settlement`: 15
- `settlement_tag_enhances_character_tag`: 16
- `domain_shop_group_for_domain`: 2
- `domain_shop_group_has_channel_partner`: 5
- `shop_group_has_manual_refresh_step`: 4
- `manual_refresh_costs_item`: 4
- `monthly_pass_reward_item`: 3
- `domain_money_exchange_rate_item`: 2
- `water_drone_liquid_item`: 3
- `money_consume_source_name_text`: 12
- `money_gain_source_name_text`: 15

The temporary build reported `1,628,129` nodes, `3,056,720` edges, and
`2,234,682` aliases.

## Follow-Up

The asset-focused explorer identified a separate high-value graph gap:
decoded gameplay model ids (`model_config_model`, world entity, and
interactive-template model consumers) are not yet bridged to exported
`asset_entity` renderable groups. That should be handled conservatively as a
candidate/proven binding report before promoting graph edges.
