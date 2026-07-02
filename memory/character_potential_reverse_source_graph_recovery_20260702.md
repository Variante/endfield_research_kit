# Character potential reverse source graph recovery - 2026-07-02

## Context

`CharacterPotentialTable` recovery already exposed character-to-potential,
potential-to-cost-item, potential-to-effect, and potential-to-unlock-item
relationships. Queries starting from a cost item, unlock item, or potential
effect still had to inspect incoming edges manually.

## Graph Change

`tools/endfield_source_graph.py` now emits target-centric reverse edges for
character potential table evidence:

- `potential_item_used_by_character`
- `item_cost_for_character_potential`
- `potential_effect_used_by_character_potential`
- `item_unlocks_character_potential_picture`
- `item_unlocks_character_potential_card_topic`

These edges preserve the same evidence labels and count/index metadata as the
forward edges. They represent declarative character-potential table
relationships, not runtime progression state.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\character_potential_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,144,085 edges, 2,277,554 aliases
- `character_uses_potential_item`: 29 edges
- `potential_item_used_by_character`: 29 edges
- `character_potential_cost_item`: 145 edges
- `item_cost_for_character_potential`: 145 edges
- `character_potential_effect`: 145 edges
- `potential_effect_used_by_character_potential`: 145 edges
- `character_potential_unlock_picture_item`: 91 edges
- `item_unlocks_character_potential_picture`: 91 edges
- `character_potential_unlock_card_topic_item`: 12 edges
- `item_unlocks_character_potential_card_topic`: 12 edges

Top potential cost item targets:

- `item_charpotentialup_chr_9000_endmin`: 15 potentials
- `item_charpotentialup_chr_0004_pelica`: 5 potentials
- `item_charpotentialup_chr_0005_chen`: 5 potentials
- `item_charpotentialup_chr_0006_wolfgd`: 5 potentials
- `item_charpotentialup_chr_0007_ikut`: 5 potentials

Top potential effect targets:

- `chr_9000_endmin_potential_1`: 3 potential rows
- `chr_9000_endmin_potential_2`: 3 potential rows
- `chr_9000_endmin_potential_3`: 3 potential rows
- `chr_9000_endmin_potential_4`: 3 potential rows
- `chr_9000_endmin_potential_5`: 3 potential rows
