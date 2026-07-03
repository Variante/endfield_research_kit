# Weapon Template Reverse Source Graph Recovery - 2026-07-03

## Context

`WeaponBasicTable` links each weapon to its upgrade, breakthrough, and talent
templates:

- `levelTemplateId`
- `breakthroughTemplateId`
- `talentTemplateId`

The source graph already emitted forward edges from weapons to those template
nodes. Template-centered queries could show template definitions and costs, but
they did not directly show which weapons used a given template.

The current export has 71 `WeaponBasicTable` weapon rows. Each row references
one upgrade template, one breakthrough template, and one talent template.

## Implementation

`tools/endfield_source_graph.py` now adds reverse edges for the existing
template references:

- `weapon_upgrade_template_used_by_weapon`
- `weapon_breakthrough_template_used_by_weapon`
- `weapon_talent_template_used_by_weapon`

The implementation is localized to `add_weapon_basic_edges` and preserves the
source field name as edge data.

## Validation

Focused validation graph:

```text
weapon_uses_upgrade_template 71 weapon_upgrade_template_used_by_weapon 71
weapon_uses_breakthrough_template 71 weapon_breakthrough_template_used_by_weapon 71
weapon_uses_talent_template 71 weapon_talent_template_used_by_weapon 71
```

Sample reverse evidence:

```text
weapon_upgrade_template:weapon_upgrade_curve_4star_1
  weapon_upgrade_template_used_by_weapon -> weapon:wpn_claym_0003 (levelTemplateId)

weapon_breakthrough_template:weapon_breakthrough_456star_D_1
  weapon_breakthrough_template_used_by_weapon -> weapon:wpn_claym_0003 (breakthroughTemplateId)

weapon_talent_template:wpn_potential_456star
  weapon_talent_template_used_by_weapon -> weapon:wpn_claym_0003 (talentTemplateId)
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query weapon_upgrade_curve_4star_1 --kind weapon_upgrade_template --db tmp\weapon_template_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query weapon_breakthrough_456star_D_1 --kind weapon_breakthrough_template --db tmp\weapon_template_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query wpn_potential_456star --kind weapon_talent_template --db tmp\weapon_template_reverse_validation.sqlite --limit 12
```

The upgrade and talent template queries surfaced the new reverse weapon links
directly. The breakthrough template query also validated the template node, but
its first results are crowded by item-cost edges, so the focused SQL sample is
the clearest proof of the new reverse breakthrough links.
