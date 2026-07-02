# Reward And Shop Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph traversal for reward grants, reward drop tables, and
normal shop catalog relationships.

New reverse edges:

- item -> reward as `item_granted_by_reward`
- item -> reward as `item_may_be_granted_by_reward`
- reward drop -> reward as `reward_drop_for_reward`
- item -> reward drop as `item_may_drop_from_reward_drop`
- shop -> shop group as `shop_in_shop_group`
- shop goods -> shop as `shop_goods_in_shop`
- item/currency -> shop goods as `item_prices_shop_goods`
- reward -> shop goods as `reward_sold_by_shop_goods`
- shop goods tag -> shop goods as `shop_goods_tag_has_goods`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\reward_shop_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,009` nodes
- `3,176,738` edges
- `2,277,554` aliases

Parity checks:

- `reward_grants_item`: `16,865`
- `item_granted_by_reward`: `16,865`
- `reward_may_grant_item`: `2,344`
- `item_may_be_granted_by_reward`: `2,344`
- `reward_has_drop_table`: `1,252`
- `reward_drop_for_reward`: `1,252`
- `reward_drop_may_drop_item`: `3,319`
- `item_may_drop_from_reward_drop`: `3,319`
- `shop_group_has_shop`: `28`
- `shop_in_shop_group`: `28`
- `shop_has_goods`: `687`
- `shop_goods_in_shop`: `687`
- `shop_goods_priced_in_item`: `687`
- `item_prices_shop_goods`: `687`
- `shop_goods_grants_reward`: `673`
- `reward_sold_by_shop_goods`: `673`
- `shop_goods_tagged`: `214`
- `shop_goods_tag_has_goods`: `214`

## Notes

This improves economy/numerical recovery by letting graph queries start from an
item, reward, shop, or tag and traverse back to the authored reward/drop/shop
declaration that uses it. The normal shop graph is now closer to the existing
cash-shop bidirectional coverage.
