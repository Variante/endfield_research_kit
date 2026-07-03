# Specialized Item Cost Reverse Source Graph Recovery - 2026-07-03

## Context

After generic compact gameplay item requirements gained reverse graph edges,
several structured table-specific item economics still only traversed from the
consumer node to the required or cost item. These edges cover systems that do
not flow through the compact WebUI gameplay helper.

## Finding

`tools/endfield_source_graph.py` now emits explicit item-to-consumer reverse
edges for selected specialized item costs and requirements:

- `item_required_by_ether_submit`
- `item_cost_for_gem_enhance_rule`
- `item_cost_for_gacha_singlePull_pull`
- `item_cost_for_gacha_tenPull_pull`
- `item_required_by_weapon_potential`
- `item_required_by_weapon_breakthrough`
- `item_cost_for_shop_channel_level`
- `item_required_by_spaceship_room_level`
- `item_used_by_factory_tech_group`
- `item_required_by_factory_tech_layer`
- `item_required_by_manual_craft_unlock`
- `item_cost_for_factory_panel_store_good`

The reverse edges mirror the original evidence paths and count/cost payloads,
so item-centered graph queries can now explain where a currency, material, or
unlock item is consumed across gacha, weapon, shop, spaceship, factory tech,
manual crafting, gem enhancement, and ether-submit tables.

## Validation

Validation used a temporary source graph at
`tmp/specialized_item_reverse.sqlite` and ran only the relevant structured
semantic ingests:

- `ingest_world_energy_semantics`
- `ingest_equipment_gem_semantics`
- `ingest_gacha_semantics`
- `ingest_weapon_semantics`
- `ingest_display_metadata_semantics`
- `ingest_spaceship_semantics`
- `ingest_factory_tech_semantics`
- `ingest_factory_logistics_semantics`

Forward/reverse counts matched:

- `ether_submit_requires_item` / `item_required_by_ether_submit`: 33
- `gem_enhance_rule_cost_item` / `item_cost_for_gem_enhance_rule`: 12
- `gacha_singlePull_pull_cost_item` / `item_cost_for_gacha_singlePull_pull`: 7
- `gacha_tenPull_pull_cost_item` / `item_cost_for_gacha_tenPull_pull`: 2
- `weapon_potential_requires_item` / `item_required_by_weapon_potential`: 16
- `weapon_breakthrough_requires_item` / `item_required_by_weapon_breakthrough`: 200
- `shop_channel_level_cost_item` / `item_cost_for_shop_channel_level`: 19
- `spaceship_room_level_requires_item` / `item_required_by_spaceship_room_level`: 31
- `factory_tech_group_uses_point_item` / `item_used_by_factory_tech_group`: 2
- `factory_tech_layer_requires_item` / `item_required_by_factory_tech_layer`: 6
- `manual_craft_unlock_requires_item` / `item_required_by_manual_craft_unlock`: 168
- `factory_panel_store_good_cost_item` / `item_cost_for_factory_panel_store_good`: 42

Sample reverse edges showed `item:item_domain_jinlong_coupon` pointing to
multiple `factory_panel_store_good:*` owners with the original `currencyType`
evidence and `cost` values.
