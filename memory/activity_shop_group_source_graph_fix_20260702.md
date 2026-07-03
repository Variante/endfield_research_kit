# Activity Shop Group Source Graph Fix - 2026-07-02

## Slice

Corrected activity catalog shop-group references so `shopGroupId` values point
to `shop_group` nodes instead of generic `shop` nodes.

Changed target constructors for:

- `ActivityLimitedFormulaTable.shopGroupId`
- `ActivityLimitedFormulaTable.activityShopLockList` keys
- `ActivityShopAdditionalTable.shopGroupId`

Affected edge kinds:

- `activity_limited_formula_shop_group`
- `activity_limited_formula_lock_shop`
- `activity_shop_additional_shop_group`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_shop_group_fix_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,010` nodes
- `3,176,738` edges
- `2,277,554` aliases

Destination node-kind query:

- `activity_limited_formula_shop_group`: `shop_group` = `1`
- `activity_limited_formula_lock_shop`: `shop_group` = `2`
- `activity_shop_additional_shop_group`: `shop_group` = `1`

No checked activity shop-group edge now targets `shop`.

## Notes

The referenced ids, such as `shop_activity_limited_formula_1`, are authored in
`ShopGroupTable`, not `ShopTable`. This fix keeps activity limited formula and
activity shop-additional traversal aligned with normal shop-group semantics.
