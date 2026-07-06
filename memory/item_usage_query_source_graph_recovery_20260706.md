# Item Usage Query Source Graph Recovery - 2026-07-06

## Context

The source graph has broad item, reward, shop, acquisition, factory, crop,
equipment, gem, profile, activity, and battle-pass edges, but practical lookup
still required knowing many table-specific edge names. This made common
questions such as "where is this item granted?", "what reward does this shop
good sell?", or "which items are in this obtain bucket?" awkward.

## Change

`tools/endfield_source_graph.py` now has an `item-usage` query. It resolves
terms through item/economy seed kinds including:

- `item`, `reward`, `reward_drop`
- `item_obtain_way`, `item_obtain_condition`, `item_type`,
  `item_showing_type`, `item_valuable_tab`, `usable_item_chest`
- `shop_goods`, `shop`, `shop_group`, `cash_goods`, `cash_shop_goods`,
  `cash_shop`, `cash_shop_group`, `cash_shop_tab`
- `money_config`, `money_exchange`
- `equipment`, `equipment_formula`, `equipment_suit`, `gem_preset`,
  `gem_term`, `gem_tag`, `gem_term_pool`
- `factory_item`, `factory_recipe`, `factory_mine`, `factory_liquid`,
  `factory_miner`
- `planting_crop`, `soil_reward`, `fertilize_item`, `world_doodad`
- `activity`, `activity_stage`, `activity_task`, `activity_submit_item`,
  `activity_limited_formula`, `business_card_topic`, `profile_picture`,
  `user_avatar`, `mail_template`, `battlepass_season`,
  `battlepass_level`, `battlepass_reward_preview`

The query uses a bounded item/economy edge predicate instead of a frozen list of
hundreds of edge names. It includes edge names containing item, reward, shop,
cost, currency, money, obtain, unlock, gift, checkin, equip, gem, factory,
crop, soil, battlepass, and activity, plus visual icon edges. This makes the
lookup follow new item/economy edges without another query update.

For item and shop-good seeds, `item-usage` also performs a separate reward-link
pass, then expands one hop around those rewards. This avoids losing reward
context when common items have many icon, activity, or grouping edges before
reward rows in the general relation limit.

## Validation

Syntax and CLI checks:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py --help
```

Smoke checks against the current default graph:

```bat
python tools\endfield_source_graph.py item-usage item_gold --kind item --limit 8
python tools\endfield_source_graph.py item-usage reward_activity_checkin_agline_1 --kind reward --limit 8
python tools\endfield_source_graph.py item-usage item_muck_feces_1 --kind item --limit 8
python tools\endfield_source_graph.py item-usage domainshop_goods_map01_10001 --kind shop_goods --limit 8
python tools\endfield_source_graph.py item-usage item_obtain_explore --kind item_obtain_way --limit 5
```

Observed evidence:

- `item_gold` resolves as an `item`, reports `item_has_obtain_way`, and exposes
  reward links through `item_granted_by_reward` / `reward_grants_item` even at a
  small limit.
- `reward_activity_checkin_agline_1` resolves as a `reward`, links to check-in
  stage usage, and grants `item_gold` plus
  `ticketgacha_special_single_lt_1_0_3`.
- `item_muck_feces_1` resolves as an `item` and reports
  `item_has_fertilize_config`.
- `domainshop_goods_map01_10001` resolves as `shop_goods`, links to the shop,
  price item, reward, shop-channel unlock levels, and reward context showing
  the sold reward grants `item_bp_double_reward`.
- `item_obtain_explore` resolves as an obtain-way bucket with 265
  `item_has_obtain_way` / `obtain_way_has_item` relationships.

## Boundary

This is authored config and extracted-reference evidence only. It is not proof
of live inventory state, entitlement, shop rotation, reward claiming,
server-side availability, or runtime drop-roll outcomes. Currency is modeled as
ordinary `item` nodes in the graph. Probabilistic edges such as reward-drop,
random chest, or likely gem edges should be read as possible authored outcomes,
not guaranteed acquisition.
