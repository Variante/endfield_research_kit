# Activity Formula Factory Reverse Source Graph Recovery - 2026-07-03

## Context

Several focused table ingests already emitted forward edges from activity or
factory configs to item, recipe, and effect targets. Reverse lookups from the
target side were missing, so graph queries could show that a formula used an
item but not directly answer which formulas, shops, or factory battle configs
used a selected target.

## Change

`tools/endfield_source_graph.py` now adds reverse edges for:

- `factory_battle_attack_range_effect` ->
  `gameplay_effect_used_by_factory_battle_attack_range`
- `activity_limited_formula_money_item` ->
  `item_used_as_activity_limited_formula_money`
- `activity_limited_formula_recipe` ->
  `factory_recipe_used_by_activity_limited_formula`
- `activity_limited_formula_item` ->
  `item_used_by_activity_limited_formula`
- `activity_limited_formula_settlement_trade_item` ->
  `item_traded_by_activity_limited_formula_settlement`
- `activity_shop_additional_money_item` ->
  `item_used_as_activity_shop_additional_money`

The reverse edges preserve the same source, evidence, and small data payloads
as their corresponding forward edges.

## Validation

Built a temporary lightweight graph:

```bat
python tools\endfield_source_graph.py build --db tmp\source_graph_reverse_edges_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Static check:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Forward/reverse parity in the temporary graph:

| Forward edge | Reverse edge | Count | Missing reverse | Extra reverse |
| --- | --- | ---: | ---: | ---: |
| `factory_battle_attack_range_effect` | `gameplay_effect_used_by_factory_battle_attack_range` | 16 | 0 | 0 |
| `activity_limited_formula_money_item` | `item_used_as_activity_limited_formula_money` | 1 | 0 | 0 |
| `activity_limited_formula_recipe` | `factory_recipe_used_by_activity_limited_formula` | 9 | 0 | 0 |
| `activity_limited_formula_item` | `item_used_by_activity_limited_formula` | 8 | 0 | 0 |
| `activity_limited_formula_settlement_trade_item` | `item_traded_by_activity_limited_formula_settlement` | 4 | 0 | 0 |
| `activity_shop_additional_money_item` | `item_used_as_activity_shop_additional_money` | 1 | 0 | 0 |
