# Character Growth Progression Source Graph Recovery - 2026-07-03

## Context

`CharGrowthTable` already connected character identity, type, profession,
default weapon, main/sub attributes, and break costs. Its authored combat
progression fields were still mostly opaque:

- `skillGroupMap`
- `skillLevelUp`
- `talentNodeMap`

Those fields describe character skill groups, concrete gameplay skill ids,
skill upgrade costs, talent unlock nodes, passive talent effects, talent
attribute modifiers, and required items.

## Implementation

`tools/endfield_source_graph.py` now models these `CharGrowthTable` structures
inside the existing character progression ingestion branch.

New node kinds:

- `character_skill_group`
- `character_skill_level_cost`
- `character_talent_node`

Key edges added:

- `character_has_skill_group`
- `skill_group_has_skill`
- `skill_used_by_character_skill_group`
- `character_skill_group_name_text`
- `character_skill_group_desc_text`
- `character_has_skill_level_cost`
- `character_skill_level_cost_for_group`
- `skill_group_has_level_cost`
- `character_skill_level_cost_requires_gold`
- `character_skill_level_cost_requires_item`
- `character_talent_node_requires_item`
- `character_talent_node_uses_effect`
- `potential_talent_effect_used_by_character_talent_node`
- `character_talent_node_modifies_attribute_meta`
- `attribute_meta_modified_by_character_talent_node`
- `character_talent_node_name_text`
- `character_talent_node_desc_text`

The patch reuses existing graph helpers for gameplay skill references, item
references, i18n text links, potential talent effect nodes, and attribute-meta
nodes.

## Validation

Focused validation graph:

```text
nodes character_skill_group 116
nodes character_skill_level_cost 1276
nodes character_talent_node 537
edges character_has_skill_group 116
edges skill_group_has_skill 306
edges skill_used_by_character_skill_group 306
edges character_has_skill_level_cost 1276
edges skill_group_has_level_cost 1276
edges character_skill_level_cost_requires_item 3248
edges character_talent_node_requires_item 1128
edges character_talent_node_uses_effect 114
edges potential_talent_effect_used_by_character_talent_node 114
edges character_talent_node_modifies_attribute_meta 116
edges attribute_meta_modified_by_character_talent_node 116
```

Sample evidence:

```text
character_skill_group:chr_0002_endminm_ComboSkill
  skill_group_has_skill -> gameplay_skill:chr_0002_endminm_combo_skill

character_skill_level_cost:chr_0002_endminm:chr_0002_endminm_NormalSkill:2
  character_skill_level_cost_requires_gold -> item:item_gold
  character_skill_level_cost_requires_item -> item:item_char_skill_level_1_6
  character_skill_level_cost_requires_item -> item:item_plant_crylplant_1_1

character_talent_node:chr_0002_endminm:chr_0002_endminm_1
  character_talent_node_modifies_attribute_meta -> attribute_meta:40

character_talent_node:chr_0002_endminm:chr_0002_endminm_passive_skill_0_1
  character_talent_node_uses_effect -> potential_talent_effect:chr_0002_endminm_talent_1_1
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query chr_0002_endminm_combo_skill --kind gameplay_skill --db tmp\char_growth_progression_validation.sqlite --limit 12
python tools\endfield_source_graph.py query item_char_skill_level_1_6 --kind item --db tmp\char_growth_progression_validation.sqlite --limit 12
python tools\endfield_source_graph.py query chr_0002_endminm_talent_1_1 --kind potential_talent_effect --db tmp\char_growth_progression_validation.sqlite --limit 20
python tools\endfield_source_graph.py query 40 --kind attribute_meta --db tmp\char_growth_progression_validation.sqlite --limit 12
```

The queries expose the expected skill-group ownership, upgrade-material usage,
talent-effect reverse links, and attribute-modifier reverse links.
