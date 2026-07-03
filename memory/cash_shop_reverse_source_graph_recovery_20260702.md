# Cash Shop Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for cash-shop goods, groups, recharge
bonus, recommendations, tabs, gift-pack configs, and recharge item grants.

New reverse edges:

- `reward -> cash_goods` as `reward_granted_by_cash_goods`
- `cash_goods -> cash_shop` as `cash_goods_listed_by_shop`
- `cash_shop -> cash_shop_group` as `cash_shop_in_group`
- `cash_recharge_bonus -> cash_goods` as `cash_recharge_bonus_for_goods`
- `reward -> cash_recharge_bonus` as `reward_used_by_cash_recharge_bonus`
- `cash_recommendation -> cash_recommendation` as
  `cash_recommendation_previous_choice`
- `cash_goods -> cash_recommendation` as `cash_goods_in_recommendation`
- `cash_shop -> cash_shop_tab` as `cash_shop_has_tab`
- `cash_shop_tag -> cash_shop_tab` as `cash_shop_tag_in_tab`
- `cash_giftpack_config -> cash_goods` as `cash_giftpack_config_for_goods`
- `cash_goods -> cash_giftpack_config` as `cash_goods_anchor_for_giftpack`
- `cash_goods -> cash_giftpack_config` as `cash_goods_show_after_giftpack`
- `cash_shop_tag -> cash_giftpack_config` as
  `cash_shop_tag_used_by_giftpack`
- `item -> recharge_pack` as `item_granted_by_recharge_pack`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\cash_shop_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,177,047` edges
- `2,277,554` aliases

Populated parity checks:

- `cash_goods_grants_reward`: `61`
- `reward_granted_by_cash_goods`: `61`
- `cash_shop_lists_goods`: `61`
- `cash_goods_listed_by_shop`: `61`
- `cash_shop_group_has_shop`: `8`
- `cash_shop_in_group`: `8`
- `cash_goods_has_recharge_bonus`: `34`
- `cash_recharge_bonus_for_goods`: `34`
- `cash_recharge_bonus_reward`: `34`
- `reward_used_by_cash_recharge_bonus`: `34`
- `cash_recommendation_next_choice`: `1`
- `cash_recommendation_previous_choice`: `1`
- `cash_recommendation_surfaces_goods`: `25`
- `cash_goods_in_recommendation`: `25`
- `cash_shop_tab_for_shop`: `31`
- `cash_shop_has_tab`: `31`
- `cash_goods_has_giftpack_config`: `26`
- `cash_giftpack_config_for_goods`: `26`
- `cash_giftpack_show_after_goods`: `6`
- `cash_goods_show_after_giftpack`: `6`
- `cash_giftpack_has_tag`: `16`
- `cash_shop_tag_used_by_giftpack`: `16`
- `recharge_pack_grants_item`: `6`
- `item_granted_by_recharge_pack`: `6`

Empty in this dataset:

- `cash_shop_tab_has_tag` / `cash_shop_tag_in_tab`
- `cash_giftpack_anchor_goods` / `cash_goods_anchor_for_giftpack`

Sample evidence:

- `reward:monthly_giftpack_material_01 -> cash_goods:monthly_giftpack_01`
  as `reward_granted_by_cash_goods`, source `CashShopGoodsTable`, evidence
  `rewardId`
- `cash_shop_tag:3 -> cash_giftpack_config:seasonal_crossover_lt_1_2_1`
  as `cash_shop_tag_used_by_giftpack`, source
  `GiftpackCashShopGoodsDataTable`, evidence `tagList[0]`
- `item:item_originium_recharge -> recharge_pack:direct_recharge_18`
  as `item_granted_by_recharge_pack`, source `RechargeTable`, evidence
  `itemid`

## Notes

Cash-shop catalog queries can now start from a reward, item, goods id, shop,
group, recommendation, tab, or gift-pack tag and traverse back to the authored
cash-shop declaration. This complements the normal shop reverse graph coverage.
