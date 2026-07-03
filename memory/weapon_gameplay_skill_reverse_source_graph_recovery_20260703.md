# Weapon Gameplay Skill Reverse Source Graph Recovery - 2026-07-03

## Context

`WeaponBasicTable` lists gameplay skill ids on each weapon through
`weaponSkillList`, with one of those entries usually matching
`weaponPotentialSkill`. The source graph already emitted:

- `weapon_has_skill_entry`
- `weapon_has_potential_skill`

Those forward links made weapon-centered queries useful, but
gameplay-skill-centered queries did not have explicit reverse links back to the
weapons using each skill.

The current export has:

- 71 weapon rows
- 208 `weaponSkillList` references
- 137 non-potential weapon skill entries
- 71 weapon potential skill entries
- 111 unique gameplay skill ids across the weapon skill lists

## Implementation

`tools/endfield_source_graph.py` now adds reverse edges while ingesting
`WeaponBasicTable`:

- `gameplay_skill_used_by_weapon`
- `gameplay_skill_used_as_weapon_potential`

The edge data preserves the original `weaponSkillList` index.

## Validation

Focused validation graph:

```text
weapon_has_skill_entry 137 gameplay_skill_used_by_weapon 137
weapon_has_potential_skill 71 gameplay_skill_used_as_weapon_potential 71
```

Sample reverse evidence:

```text
gameplay_skill:sk_wpn_claym_0003
  gameplay_skill_used_as_weapon_potential -> weapon:wpn_claym_0003 (weaponSkillList[2])

gameplay_skill:wpn_sp_attr_atk_high
  gameplay_skill_used_by_weapon -> weapon:wpn_claym_0004 (weaponSkillList[1])
  gameplay_skill_used_by_weapon -> weapon:wpn_claym_0013 (weaponSkillList[1])
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query sk_wpn_claym_0003 --kind gameplay_skill --db tmp\weapon_skill_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query wpn_sp_attr_atk_high --kind gameplay_skill --db tmp\weapon_skill_reverse_validation.sqlite --limit 12
```

Both queries showed the new reverse edges from gameplay skill nodes back to
weapons, alongside the existing forward weapon-to-skill edges.
