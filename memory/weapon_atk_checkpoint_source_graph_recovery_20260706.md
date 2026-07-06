# Weapon ATK Checkpoint Source Graph Recovery - 2026-07-06

## Scope

P7 asks for a formula-recovery pilot across character growth, weapon ATK, and
one damage path. The graph already exposed weapons, upgrade templates, and
template summary payloads, but `WeaponUpgradeTemplateTable.list[]` rows were
not queryable as per-level stat evidence.

## Change

`tools/endfield_source_graph.py` now emits
`weapon_upgrade_level_checkpoint` nodes from weapon upgrade template rows.
Each checkpoint records the authored level, `baseAtk`, level-up EXP/gold, and
cumulative EXP/gold fields when present.

New edge kinds:

- `weapon_upgrade_template_has_level_checkpoint`
- `weapon_upgrade_level_checkpoint_for_template`
- `weapon_upgrade_checkpoint_has_stat_property`
- `stat_property_used_by_weapon_upgrade_checkpoint`

The ATK edges point at the existing `gameplay_stat_property:atk` node. This
makes queries around weapon ATK curves use normal graph traversal instead of
requiring manual inspection of template node payloads.

## Validation

Validated with a skip-heavy temp source graph build:

```bat
python tools\endfield_source_graph.py build --db D:\fluffy-dump\tmp\weapon_atk_checkpoint_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Counts from `tmp/weapon_atk_checkpoint_graph.sqlite`:

- `weapon_upgrade_level_checkpoint`: 3,780 nodes
- `weapon_upgrade_template_has_level_checkpoint`: 3,780 edges
- `weapon_upgrade_level_checkpoint_for_template`: 3,780 edges
- `weapon_upgrade_checkpoint_has_stat_property`: 1,890 edges
- `stat_property_used_by_weapon_upgrade_checkpoint`: 1,890 edges

The 3,780 checkpoint nodes include both normal upgrade template rows and
cumulative upgrade-sum rows. The 1,890 ATK stat-property edges come from the
normal `WeaponUpgradeTemplateTable` rows that carry `baseAtk`; the sum rows
carry cumulative EXP/gold but no authored `baseAtk`.

Sample verified edge payload:

```json
{
  "level": 1,
  "statKey": "atk",
  "templateKind": "weapon_upgrade_template",
  "value": 27
}
```

## Boundary

This is authored table evidence only. It improves the weapon ATK pilot slice,
but does not prove the IL2CPP getter/evaluator path, modifier order, live
inventory state, or runtime combat formula execution.
