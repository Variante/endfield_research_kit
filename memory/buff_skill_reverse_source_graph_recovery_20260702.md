# Buff and skill reverse source graph recovery - 2026-07-02

## Context

Decoded `BuffData` and `SkillData` already produce forward graph edges from a
config owner to referenced buffs and gameplay effects:

- `buff_data_references_buff`
- `buff_data_references_effect`
- `skill_data_references_buff`
- `skill_data_references_effect`

Those edges come from recovered string references in MemoryPack-like config
payloads, with byte-offset evidence. For investigation, the target side was
less convenient: querying a common buff or effect showed incoming references,
but there was no target-centric semantic edge naming the owner class.

## Graph Change

`tools/endfield_source_graph.py` now emits matching reverse edges:

- `buff_used_by_buff_data`
- `buff_used_by_skill_data`
- `gameplay_effect_used_by_buff_data`
- `gameplay_effect_used_by_skill_data`

These edges do not claim runtime formula execution. They preserve decoded
string-reference evidence from recovered config payloads and make high-fanout
buffs/effects easier to query from the target side.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\buff_skill_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,007 nodes, 3,141,270 edges, 2,277,552 aliases
- `buff_data_references_buff`: 1,862 edges
- `buff_used_by_buff_data`: 1,862 edges
- `skill_data_references_buff`: 3,000 edges
- `buff_used_by_skill_data`: 3,000 edges
- `buff_data_references_effect`: 1,404 edges
- `gameplay_effect_used_by_buff_data`: 1,404 edges
- `skill_data_references_effect`: 9,527 edges
- `gameplay_effect_used_by_skill_data`: 9,527 edges
- retained `buff`: 2,377 nodes
- retained `gameplay_skill`: 2,114 nodes
- retained `gameplay_effect`: 5,338 nodes

Top decoded skill-data buff targets include:

- `buff_eny_0090_wgabyss_interrupted_face_to_attacker`: 186 references
- `buff_chr_0017_yvonne_ultimate_skill_shield`: 93 references
- `buff_eny_0080_reaper_alreadyhit`: 66 references
- `buff_wpn_passive_spirit_01`: 63 references

Top decoded skill-data effect targets include:

- `P_common_enemy_atk_ready_01`: 454 references
- `P_skillalert_circle_01`: 180 references
- `P_palesent_03_skill01_hit`: 166 references
- `P_hsmino_skill_hit_01`: 67 references

Sidecar gameplay review identified a small next candidate: materialize
`FactoryBattleTable.attackRangeEffect` as `factory_battle_attack_range_effect`
edges to `gameplay_effect` nodes. Expected coverage is 16 rows and 2 distinct
effect ids. That should remain separate from this decoded BuffData/SkillData
reverse-reference commit.
