# Effect Usage Source Graph Query - 2026-07-06

## Scope

Added `effect-usage` to `tools/endfield_source_graph.py` for compact lookup of
authored gameplay-effect references, global/use-item/potential effects, and
strict exported asset name matches.

The original understanding report calls effect dependencies a partial area:
BuffData, SkillData, LevelScriptData, LevelData, ModelViewStateController, and
MonoBehaviour frontier entries expose many effect keys, and a small slice has
strict suffix-normalized exported asset matches. The query makes those links
inspectable without claiming runtime effect execution semantics.

## Query Behavior

Examples:

```bat
python tools\endfield_source_graph.py effect-usage P_agtrinit_skill01 --kind gameplay_effect --limit 14
python tools\endfield_source_graph.py effect-usage P_agtrinit_skill01_p5FD796A96DC49C4B.fbx --kind asset --limit 14
python tools\endfield_source_graph.py effect-usage chr_0004_pelica_potential_1 --kind potential_talent_effect --limit 12
python tools\endfield_source_graph.py effect-usage wulingbuff1 --kind global_effect --limit 12
python tools\endfield_source_graph.py effect-usage item_bottled_flower1spc_1 --kind use_item_effect --limit 12
```

The command can start from:

- `gameplay_effect`
- `global_effect`
- `potential_talent_effect`
- `use_item_effect`
- `domain_level_effect`
- `fertilize_effect`
- matched exported `asset` rows
- authored consumers such as buffs, skills, level scripts, model-view
  controllers, char-interact configs, and spawner entries

Returned groups include:

- `assets`
- `skills`
- `buffs`
- `levelScripts`
- `spawners`
- `modelView`
- `monobehaviour`
- `characterPotential`
- `useItems`
- `globalEffects`
- `worldDomain`

## Evidence Model

High-value edges include:

- `skill_data_references_effect`
- `gameplay_effect_used_by_skill_data`
- `buff_data_references_effect`
- `gameplay_effect_used_by_buff_data`
- `level_script_references_effect`
- `level_data_references_effect`
- `spawner_enemy_prewarn_effect`
- `model_view_state_controller_references_effect`
- `model_view_state_controller_animator_references_effect`
- `char_interact_references_effect`
- `monobehaviour_frontier_entry_uses_gameplay_effect`
- `effect_name_matches_export_base_asset`
- `asset_matched_by_gameplay_effect`
- `uses_potential_talent_effect`
- `use_effect_applies_buff`
- `global_effect_has_param`

Smoke checks showed:

- `P_agtrinit_skill01` exposes skill-data consumers and a strict exported FBX
  asset match.
- The matched exported asset
  `P_agtrinit_skill01_p5FD796A96DC49C4B.fbx` resolves back to the gameplay
  effect and its skill-data consumers.
- `chr_0004_pelica_potential_1` exposes potential/character and skill
  blackboard effect evidence.
- `wulingbuff1` exposes global-effect and ether-submit usage evidence.
- `item_bottled_flower1spc_1` exposes use-item buff and blackboard evidence.

## Interpretation

Treat output as authored static references plus strict export-filename evidence.
The exported asset match is useful for finding adjacent renderable/effect files,
but it is not proof that the runtime effect system binds that asset in every
context.

Do not treat this as proof of:

- runtime effect action execution;
- target selection, timing, or projectile behavior;
- particle/VFX renderer fidelity;
- complete prefab/component dependency recovery;
- buff stack or skill-targeting semantics;
- broad fuzzy effect-to-asset matches.

Use `effect-usage` with `material-usage`, `entity-assets`, `progression-usage`,
`audio-usage`, and `map-usage` for deeper cross-domain follow-up.

## Validation

Validated syntax and smoke lookups:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py effect-usage --help
python tools\endfield_source_graph.py effect-usage P_agtrinit_skill01 --kind gameplay_effect --limit 14
python tools\endfield_source_graph.py effect-usage P_agtrinit_skill01_p5FD796A96DC49C4B.fbx --kind asset --limit 14
python tools\endfield_source_graph.py effect-usage chr_0004_pelica_potential_1 --kind potential_talent_effect --limit 12
python tools\endfield_source_graph.py effect-usage wulingbuff1 --kind global_effect --limit 12
python tools\endfield_source_graph.py effect-usage item_bottled_flower1spc_1 --kind use_item_effect --limit 12
```
