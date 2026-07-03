# Character Progression Reverse Source Graph Recovery - 2026-07-03

## Context

Character progression tables already exposed level cost rows and break-stage
EXP item lists, but the gold cost was only preserved as node data and EXP item
usage was forward-only from the break config. Item-centered progression queries
therefore missed authored character level and break EXP consumers.

## Change

`tools/endfield_source_graph.py` now emits explicit item edges for character
progression costs:

- `character_level_cost_requires_gold`
- `item_gold_cost_for_character_level_cost`
- `item_usable_for_character_break_exp`

The gold edges preserve the authored `gold` value as a count payload, and the
EXP item reverse edge preserves the original `availableExpItems[...]` evidence.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\character_progression_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,805,874 edges.
Forward/reverse counts matched:

- `character_level_cost_requires_gold`: 90 / `item_gold_cost_for_character_level_cost`: 90
- `character_break_config_exp_item`: 13 / `item_usable_for_character_break_exp`: 13
