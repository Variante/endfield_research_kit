# Formula Usage Source Graph Query Recovery - 2026-07-06

## Context

The source graph already ingests several authored formula and recipe families,
including equipment formulas, factory recipes, spaceship formulas, activity
limited formulas, and reverse formula indexes. Those edges were useful through
generic `query`, but formula investigations had to know the exact node kind and
edge names first.

This is a numerical/gameplay semantics gap rather than an extraction gap: the
project has the authored config rows, but needs faster evidence lookup for
what a formula defines, consumes, produces, belongs to, unlocks, or is used by.

## Change

`tools/endfield_source_graph.py` now has:

```bat
python tools\endfield_source_graph.py formula-usage TERM
```

The command resolves common formula node families before falling back to the
generic query:

- `equipment_formula`
- `factory_recipe`
- `spaceship_formula`
- `activity_limited_formula`
- `activity_limited_formula_stage`
- `limited_formula_reverse`
- `equipment_formula_pack`

It returns edge counts plus relation rows for current graph edges whose names
contain `formula` or `recipe`, preserving source table, field evidence, and
edge data. The boundary is intentionally explicit: this is authored config
formula evidence, not runtime crafting, factory logistics, or economy
simulation.

## Validation Examples

Equipment formula lookup:

```bat
python tools\endfield_source_graph.py formula-usage item_formu_t0_parts_tundra01_body_01 --limit 8
```

Expected evidence includes the `equipment_formula` seed, `defines_equipment_formula`,
`equipment_formula_outputs_equipment`, `equipment_formula_cost_*`, pack, and
unlock-key edges when the row has those fields.

Factory recipe lookup:

```bat
python tools\endfield_source_graph.py formula-usage battle_cannon_1 --kind factory_recipe --limit 8
```

Expected evidence includes the `factory_recipe` seed and current recipe edges
such as domain, craft group, input items, output items, and machine/crafting
relations when present in the graph.

Activity limited formula lookup:

```bat
python tools\endfield_source_graph.py formula-usage activity_limited_formula_1 --kind activity_limited_formula --limit 8
```

Expected evidence includes the activity-limited formula seed, stage relations,
recipe links, money/item relations, shop lock links, and settlement/trade item
relations.

## Follow-Up

Noether's read-only parallel review recommended a broader `factory-flow`
command/report that would join recipes, machine capability, ingredient tags,
miner produce rates, pipe throughput, liquids, bottle mappings, and utility
profiles. That remains the better next step for factory numeric flow. This
commit deliberately keeps the smaller formula query independent so it can be
validated and reused before adding factory-specific chain logic.
