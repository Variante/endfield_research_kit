# Factory Spaceship Item Reverse Source Graph Recovery - 2026-07-03

## Context

Spaceship formulas and factory utility tables already linked formulas, miners,
fuels, batteries, and liquids to item nodes in the forward direction. Starting
from an item node still did not directly show which formula consumed/produced
it or which factory utility definition used it.

## Change

`tools/endfield_source_graph.py` now emits reverse item edges for:

- `item_consumed_by_spaceship_formula`
- `item_produced_by_spaceship_formula`
- `item_output_by_factory_miner`
- `item_consumed_by_factory_miner`
- `item_defines_factory_fuel`
- `item_defines_factory_battery`
- `item_defines_factory_liquid`
- `item_empty_bottle_for_liquid`
- `item_full_bottle_for_liquid`

The reverse edges preserve the same source, evidence, and count/payload data as
their forward relationships.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph:

```bat
tmp\factory_spaceship_item_reverse_validation_20260703.sqlite
```

Focused ingest methods:

- `ingest_spaceship_semantics`
- `ingest_factory_utility_semantics`

Counts:

- `spaceship_formula_consumes_item`: 30 / `item_consumed_by_spaceship_formula`: 30
- `spaceship_formula_produces_item`: 38 / `item_produced_by_spaceship_formula`: 38
- `factory_miner_outputs_item`: 10 / `item_output_by_factory_miner`: 10
- `factory_miner_consumes_item`: 4 / `item_consumed_by_factory_miner`: 4
- `factory_fuel_item`: 6 / `item_defines_factory_fuel`: 6
- `factory_battery_item`: 5 / `item_defines_factory_battery`: 5
- `factory_liquid_item_ref`: 27 / `item_defines_factory_liquid`: 27
- `liquid_empty_bottle_item`: 67 / `item_empty_bottle_for_liquid`: 67
- `liquid_full_bottle_item`: 67 / `item_full_bottle_for_liquid`: 67
