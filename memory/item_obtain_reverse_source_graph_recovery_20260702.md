# Item Obtain Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph coverage for item obtain-way relationships.

- Forward edge already present: `item -> item_obtain_way` as `item_has_obtain_way`
- New reverse edge: `item_obtain_way -> item` as `obtain_way_has_item`
- Source table: `ItemTable`
- Evidence: matching `obtainWayIds[index]`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_obtain_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,009` nodes
- `3,146,123` edges
- `2,277,554` aliases

Edge parity query:

- `item_has_obtain_way`: `2,035`
- `obtain_way_has_item`: `2,035`

Top reverse obtain-way buckets:

- `item_obtain_explore`: `265`
- `item_obtain_equip`: `220`
- `item_obtain_monster_common`: `184`
- `item_obtain_energy_point_2`: `175`
- `item_obtain_levelup`: `92`
- `item_obtain_potential_level`: `88`
- `item_obtain_techtree`: `86`
- `item_obtain_payshop_weapon`: `59`
- `item_obtain_char_potential`: `55`
- `item_obtain_domain_shop_levelup`: `43`

## Notes

This makes obtain-way queries symmetric with the existing item-facing lookup,
so a graph query for a source such as `item_obtain_explore` can enumerate all
items surfaced through that acquisition bucket without scanning inbound edges.
