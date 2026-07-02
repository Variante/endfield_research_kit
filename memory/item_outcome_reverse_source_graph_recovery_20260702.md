# Item Outcome Reverse Source Graph Recovery - 2026-07-02

## Slice

Added reverse source-graph coverage for `ItemTable.outcomeItemIds`.

- Existing forward edge: `item -> item` as `item_outcomes_item`
- New reverse edge: outcome item -> source item as `item_outcome_of_item`
- Source table: `ItemTable`
- Evidence: matching `outcomeItemIds[index]`

## Validation

Quick graph build:

```bat
python tools\endfield_source_graph.py build --db tmp\item_outcome_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,688,009` nodes
- `3,146,549` edges
- `2,277,554` aliases

Parity checks:

- `item_outcomes_item`: `288`
- `item_outcome_of_item`: `288`

Top source items by reverse fan-out:

- `item_crystal_shell`: `3`
- `item_drop_enemycommon_1`: `3`
- `item_fbottle_glass_acid`: `3`
- `item_fbottle_glass_copper`: `3`
- `item_fbottle_glass_copper_enr`: `3`
- `item_fbottle_glass_grass_1`: `3`
- `item_fbottle_glass_grass_2`: `3`
- `item_fbottle_glass_sewage`: `3`
- `item_fbottle_glass_water`: `3`
- `item_fbottle_glass_xiranite`: `3`

## Notes

This closes the direct reverse lookup gap for result items. A graph query on an
item yielded by a drop/container/bottle-style source can now traverse back to
the item record that declares the outcome without manually scanning inbound
`item_outcomes_item` edges.
