# Stat Usage Query Source Graph Recovery - 2026-07-06

## Scope

Recent P7 work made more authored stat evidence queryable: character stat
checkpoints, weapon ATK checkpoints, equipment curves, ability entity stats,
potential talent modifiers, attribute metadata, and enemy damage-taken scalar
links. This pass adds a CLI shortcut for asking where a stat or attribute is
used. It does not evaluate runtime formulas or modifier order.

## Change

`tools/endfield_source_graph.py` now supports:

```bat
python tools\endfield_source_graph.py stat-usage atk
python tools\endfield_source_graph.py stat-usage 2 --kind attribute_meta
python tools\endfield_source_graph.py stat-usage all_damage_taken_scalar
```

The query resolves `gameplay_stat_property`, `attribute_meta`, or
`composite_attribute` nodes, returns edge-kind counts, and includes bounded
relation samples with source/evidence/edge payloads.

## Validation

Against the current large graph DB, `stat-usage atk --limit 8` resolves
`gameplay_stat_property:atk` and reports:

- `ability_entity_sets_stat_property`: 14
- `attribute_meta_has_stat_property`: 1
- `scales_stat_property`: 20
- `stat_property_set_by_ability_entity`: 14
- `stat_property_used_by_character_checkpoint`: 2,632

`stat-usage 2 --kind attribute_meta --limit 8` resolves `attribute_meta:2` and
shows the attribute-to-stat mapping plus character, enemy, and equipment usage
counts.

Because `reports/source_graph/endfield_source_graph.sqlite` predates the latest
weapon and damage-scalar commits, a focused temp graph smoke build validated
the newest edge families:

- `stat-usage atk`: 1,890 `stat_property_used_by_weapon_upgrade_checkpoint`
  edges and 1,890 forward checkpoint-to-stat edges.
- `stat-usage all_damage_taken_scalar`: 5 enemy damage-taken level scalar links.
- `stat-usage physical_damage_taken_scalar`: 113 enemy attribute-template
  scalar links plus the attribute-meta mapping.

## Boundary

The shortcut is an evidence navigator. Counts and samples are authored table or
generated graph evidence only; they do not prove final runtime stats, formula
execution, live account state, or combat modifier order.
