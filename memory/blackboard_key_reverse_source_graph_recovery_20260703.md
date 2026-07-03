# Blackboard Key Reverse Source Graph Recovery - 2026-07-03

## Context

Blackboard keys are one of the main numerical glue layers for skills, buffs,
potential effects, item use effects, spawner born-buffs, and ether global
effects. The graph already linked gameplay owners to blackboard keys, but
blackboard-key-centered queries could not reliably enumerate which gameplay
rows used or modified a given key.

## Finding

`tools/endfield_source_graph.py` now emits reverse blackboard-key edges:

- `blackboard_key_used_by_gameplay`
- `blackboard_key_used_by_character_potential`
- `blackboard_key_modified_by_potential_talent`
- `blackboard_key_matches_buff_parameter`
- `blackboard_key_matches_skill_parameter`

The generic `blackboard_key_used_by_gameplay` edge is emitted by the shared
`add_blackboard_edges()` helper and keeps the original forward edge kind in
payload data as `edgeKind`. This covers skill levels, use-item effects,
potential-talent attached buffs, spawner born-buff blackboards, and ether submit
global effects without replacing their more specific forward edge names.

## Validation

Focused temporary graph builds:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DBs:

- `tmp/blackboard_combat_reverse.sqlite`
- `tmp/blackboard_gameplay_reverse.sqlite`
- `tmp/blackboard_decoded_reverse.sqlite`
- `tmp/blackboard_world_energy_reverse.sqlite`

Validated forward/reverse counts:

- `skill_level_uses_blackboard_key`: 14,838 / reverse 14,838
- `use_effect_uses_blackboard_key`: 202 / reverse 202
- `potential_talent_uses_blackboard_key`: 104 / reverse 104
- `potential_talent_modifies_blackboard_key`: 331 / reverse 331
- `character_potential_uses_blackboard_key`: 794 / reverse 794
- `spawner_buff_uses_blackboard_key`: 677 / reverse 677
- `ether_submit_global_effect_blackboard`: 21 / reverse 21
- `buff_parameter_matches_blackboard_key`: 22 / reverse 22 in the focused decoded-config build
- `skill_parameter_matches_blackboard_key`: 14 / reverse 14 in the focused decoded-config build

Sample reverse edges showed keys such as `atb`, `atb_return`, and `Duration`
pointing back to potential-talent effects with preserved skill ids and numeric
values, and ether keys such as `attack`, `cure`, and `defend` pointing back to
`global_effect:wulingbuff*` rows with the original value payloads.
