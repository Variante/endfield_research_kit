# Factory Tech Manual Craft Reverse Source Graph Recovery - 2026-07-03

## Context

Factory tech and manual-craft tables already exposed authored progression
requirements and unlock outputs in the forward direction. Starting from a tech
node, item, or formula item still required manual SQL to answer which factory
tech depended on it, which tech unlocked it, or which manual-craft unlock/upgrade
targeted it.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for factory tech and
manual-craft progression relationships:

- `factory_tech_required_by_tech`
- `item_unlocked_by_factory_tech`
- `formula_item_granted_by_manual_craft_unlock`
- `formula_item_unlocked_by_manual_craft_material`
- `item_targeted_by_manual_craft_upgrade`

The reverse edges preserve the same source, evidence, and count payloads as the
existing forward edges.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_tech_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,805,681 edges.
Forward/reverse counts matched:

- `factory_tech_requires_tech`: 55 / `factory_tech_required_by_tech`: 55
- `factory_tech_unlocks_item`: 128 / `item_unlocked_by_factory_tech`: 128
- `manual_craft_unlock_grants_formula_item`: 168 / `formula_item_granted_by_manual_craft_unlock`: 168
- `manual_craft_material_unlocks_formula_item`: 168 / `formula_item_unlocked_by_manual_craft_material`: 168
- `manual_craft_upgrade_item_targets_item`: 45 / `item_targeted_by_manual_craft_upgrade`: 45
