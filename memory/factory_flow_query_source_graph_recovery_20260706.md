# Factory Flow Source Graph Query Recovery - 2026-07-06

## Context

The July 1 original-data understanding report still marks numerical systems
and runtime formulas as one of the weaker areas. Factory data is a clear
example: the graph already exposes authored tables for machines, recipes,
items, miners, fluids, logistics units, pipes, power, building items, tech, and
reverse indexes, but those relationships were spread across generic `query`
results and exact edge names.

The new query is a shortcut over existing graph evidence. It does not simulate
factory runtime behavior, throughput scheduling, power networks, liquid
transfer, or building state.

## Change

`tools/endfield_source_graph.py` now supports:

```bat
python tools\endfield_source_graph.py factory-flow TERM
```

The command prefers factory-specific seed kinds before generic graph fallback:

- `factory_miner`
- `factory_fluid_machine`
- `factory_machine`
- `factory_recipe`
- `factory_item`
- `item`
- `factory_liquid`
- `factory_building`
- `factory_logistic_unit`
- `factory_underground_pipe`
- `factory_tech`
- `factory_mine`
- `factory_region`

Specialized miner and fluid-machine rows are checked before the general
machine row, so ambiguous ids such as `miner_2` and `pump_1` expose authored
production or liquid evidence by default.

It returns edge counts, raw relation rows, and grouped `flowHints` for:

- `recipe`
- `mining`
- `fluid`
- `logistics`
- `power`
- `tech`
- `machine`
- `item`
- `other`

## Validation Examples

Machine and recipe view:

```bat
python tools\endfield_source_graph.py factory-flow furnance_1 --kind factory_machine --limit 8
```

This resolves the `factory_machine` node instead of the `StrIdNumTable`
dictionary entry that generic `query` prefers. Expected evidence includes
machine/building/renderer/audio/recipe capability relations when present.

Miner numeric view:

```bat
python tools\endfield_source_graph.py factory-flow miner_2 --kind factory_miner --limit 8
```

Expected evidence includes `factory_miner_consumes_item`,
`factory_miner_outputs_item`, and `factory_miner_machine_ref`. Edge data
preserves authored counts or rates when the graph row carries them.

Fluid machine view:

```bat
python tools\endfield_source_graph.py factory-flow pump_2 --kind factory_fluid_machine --limit 8
```

Expected evidence includes `factory_fluid_machine_accepts_liquid`,
`factory_fluid_machine_ref`, and related item/liquid rows when present.

## Follow-Up

This command is still a single-hop evidence query. A richer generated
`factory_flow_chains` report could walk from a building or machine through
recipes, recipe inputs/outputs, ingredient tags, supporting machines, miner
rates, fluid mappings, logistic units, pipes, and tech unlocks. That should
stay explicitly framed as authored config flow, not runtime simulation.
