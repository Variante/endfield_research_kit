# Progression Usage Source Graph Query - 2026-07-06

## Scope

Added `progression-usage` to `tools/endfield_source_graph.py` for compact
lookup of authored character, weapon, equipment, gem, stat, attribute, and item
cost progression evidence.

The original understanding report identifies numerical systems as partially
decoded but still weak on runtime formula proof. This query does not evaluate
combat formulas. It makes the already-recovered static table relationships
easier to inspect from one seed.

`progression-flow` remains accepted as an alias, but `progression-usage` is the
preferred name because the command reports graph evidence rather than runtime
calculation flow.

## Query Behavior

Examples:

```bat
python tools\endfield_source_graph.py progression-usage chr_0017_yvonne --kind character --limit 18
python tools\endfield_source_graph.py progression-usage chr_0017_yvonne:potential:1 --kind character_potential --limit 12
python tools\endfield_source_graph.py progression-usage weapon_upgrade_curve_4star_1 --kind weapon_upgrade_template --limit 12
python tools\endfield_source_graph.py progression-usage weapon_breakthrough_456star_A_1 --kind weapon_breakthrough_template --limit 12
python tools\endfield_source_graph.py progression-usage item_equip_t0_parts_tundra01_body_01 --kind equipment --limit 12
python tools\endfield_source_graph.py progression-usage gem_claym_0003_442 --kind gem_preset --limit 12
python tools\endfield_source_graph.py progression-usage item_char_skill_level_1_6 --kind item --limit 12
python tools\endfield_source_graph.py progression-usage attr_1 --kind attribute_meta --limit 12
```

The command resolves progression-oriented seed kinds first, expands one hop to
nearby progression nodes, and groups relations into:

- `characterLevels`
- `breakthrough`
- `potentialTalent`
- `skills`
- `weapons`
- `equipmentFormulas`
- `equipment`
- `gems`
- `statsAttributes`
- `costs`
- `gameplay`

Character seed output is ordered so high-level checkpoint, breakthrough, and
potential/cost evidence appears before the very large base-attribute fanout.

## Evidence Model

High-value edge families include:

- character level and checkpoint edges such as
  `has_character_level_checkpoint`, `has_character_stat_checkpoint`,
  `stat_checkpoint_has_property`, and `level_checkpoint_gold_cost`;
- breakthrough and potential edges such as `character_has_break_cost`,
  `character_break_cost_requires_item`, `has_character_potential`, and
  `character_potential_cost_item`;
- weapon progression edges such as `weapon_uses_upgrade_template`,
  `weapon_uses_breakthrough_template`, and `weapon_breakthrough_requires_item`;
- equipment and formula edges such as `equipment_crafted_by_formula`,
  `equipment_formula_outputs_equipment`, `equipment_formula_cost_item`, and
  `equipment_runtime_attribute`;
- gem edges such as `gem_preset_has_term`, `gem_enhance_rule_cost_item`, and
  `gem_dismantle_rule_output_item`;
- attribute/stat edges such as `attribute_meta_has_stat_property`,
  `attribute_meta_used_by_character_base`, and
  `attribute_meta_used_by_equipment`;
- item-cost reverse edges such as `requires_item`, `item_required_by_gameplay`,
  and item-specific reverse cost links.

Smoke checks showed:

- `chr_0017_yvonne` surfaces character level checkpoints and break costs before
  raw base attributes.
- `item_char_skill_level_1_6` surfaces required-by gameplay cost edges.
- `attr_1` surfaces potential-talent and equipment attribute consumers.
- `item_equip_t0_parts_tundra01_body_01` surfaces equipment formula and
  attribute evidence.
- `gem_claym_0003_442` surfaces preset term/item/domain links.
- `weapon_breakthrough_456star_A_1` surfaces weapon breakthrough item
  requirements.

## Interpretation

Treat output as authored static evidence from recovered tables and generated
gameplay summaries. Numeric payloads such as levels, costs, stat values, gold
counts, and item counts are table/config evidence.

Do not treat this as proof of:

- final in-game stat totals;
- runtime combat formula evaluation;
- modifier ordering;
- live account inventory or unlock state;
- random drop or enhancement outcomes;
- server-side progression state.

Use `progression-usage` with `item-usage`, `stat-usage`, `formula-usage`,
`text-usage`, and `actor-usage` for cross-domain follow-up.

## Validation

Validated syntax and smoke lookups:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py progression-usage --help
python tools\endfield_source_graph.py progression-usage chr_0017_yvonne --kind character --limit 18
python tools\endfield_source_graph.py progression-usage chr_0017_yvonne:potential:1 --kind character_potential --limit 12
python tools\endfield_source_graph.py progression-usage weapon_upgrade_curve_4star_1 --kind weapon_upgrade_template --limit 12
python tools\endfield_source_graph.py progression-usage weapon_breakthrough_456star_A_1 --kind weapon_breakthrough_template --limit 12
python tools\endfield_source_graph.py progression-usage item_equip_t0_parts_tundra01_body_01 --kind equipment --limit 12
python tools\endfield_source_graph.py progression-usage gem_claym_0003_442 --kind gem_preset --limit 12
python tools\endfield_source_graph.py progression-usage item_char_skill_level_1_6 --kind item --limit 12
python tools\endfield_source_graph.py progression-usage attr_1 --kind attribute_meta --limit 12
python tools\endfield_source_graph.py progression-flow weapon_breakthrough_456star_A_1 --kind weapon_breakthrough_template --limit 12
```
