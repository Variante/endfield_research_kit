# Weapon Skill Recommendation Reverse Source Graph Recovery - 2026-07-03

## Context

`CharWpnSkillRecommendTable` links each character to recommended weapon skill
ids through `weaponSkillIds`. The source graph already emitted forward
`character_recommends_weapon_skill` edges, but the recommendation nodes did not
have reverse edges back to the characters that recommend them.

The current export has:

- 29 character recommendation rows
- 174 weapon skill recommendation references
- 12 unique recommendation ids

## Implementation

`tools/endfield_source_graph.py` now adds a reverse
`weapon_skill_recommended_by_character` edge for each existing
`character_recommends_weapon_skill` edge. The edge preserves the source list
index as edge data.

## Validation

Focused validation graph:

```text
character_recommends_weapon_skill 174
weapon_skill_recommended_by_character 174
defines_character_weapon_skill_recommendations 29
nodes weapon_skill_recommendation 12
```

Sample reverse evidence for `wpn_attr_agi_low`:

```text
weapon_skill_recommendation:wpn_attr_agi_low
  weapon_skill_recommended_by_character -> character:chr_0002_endminm (weaponSkillIds[0])
  weapon_skill_recommended_by_character -> character:chr_0003_endminf (weaponSkillIds[0])
  weapon_skill_recommended_by_character -> character:chr_0006_wolfgd (weaponSkillIds[3])
```

CLI smoke query:

```bat
python tools\endfield_source_graph.py query wpn_attr_agi_low --kind weapon_skill_recommendation --db tmp\weapon_skill_recommend_validation.sqlite --limit 16
```

The query showed both the existing forward recommendation edges and the new
reverse edges from the recommendation node to characters.
