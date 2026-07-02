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

## Follow-up: Condition Reverse Edges

Added reverse source-graph coverage for item obtain-condition evidence.

- `item_obtain_check_used_by_condition`: check target back to condition
- `item_obtain_type_has_condition`: condition type back to condition
- `item_obtain_condition_shows_obtain_way`: condition back to obtain way

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_acquisition_condition_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

SQLite validation:

- `item_obtain_check_used_by_condition`: `53`
- `item_obtain_type_has_condition`: `53`
- `item_obtain_condition_shows_obtain_way`: `32`
- forward check refs still resolve as `27` dungeon refs, `12` wiki refs, `13` factory-tech refs, and `1` item ref
- `item_obtain_condition_has_type`: `53`
- `item_obtain_way_show_condition`: `32`

Sample evidence:

- `dungeon:dung01_bossrush01_01 -> item_obtain_condition:condition_dung01_bossrush01_01` as `item_obtain_check_used_by_condition`, source `NoObtainWayCondTable`, evidence `checkId`
- `item_obtain_condition_type:5909 -> item_obtain_condition:condition_item_obtain_noway_item_bbflower` as `item_obtain_type_has_condition`, source `NoObtainWayCondTable`, evidence `conditionType`
- `item_obtain_condition:condition_dung01_bossrush01_01 -> item_obtain_way:item_obtain_dungeon_bossrush_01_04` as `item_obtain_condition_shows_obtain_way`, source `ObtainWayShowCondTable`, evidence `rowValue`

This closes the inbound query gap for item acquisition visibility rules: a graph query from a dungeon/wiki/factory-tech/item check target can now enumerate the obtain conditions that reference it, then follow those conditions to the obtain ways they hide or show.
