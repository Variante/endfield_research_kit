# MonoBehaviour Frontier Semantic Reference Source Graph Recovery - 2026-07-03

## Scope

The source graph now extracts conservative semantic references from residual
partial MonoBehaviour frontier JSON payloads. During
`ingest_monobehaviour_frontier_report()`, each frontier entry's decoded JSON
under `export_full/` is scanned for field-path evidence and linked to existing
graph concepts where possible.

This adds queryable gameplay meaning to the partial `ProjectileTemplateData`,
`AbilityEntityTemplateData`, `EnemyTemplateData`, and `CharacterTemplateData`
frontier entries without claiming full runtime schema recovery.

## Graph Additions

New or newly populated links from `monobehaviour_frontier_entry`:

- `monobehaviour_frontier_entry_uses_skill`
- `monobehaviour_frontier_entry_uses_model`
- `monobehaviour_frontier_entry_uses_ai_config`
- `monobehaviour_frontier_entry_uses_animation_config`
- `monobehaviour_frontier_entry_uses_gameplay_effect`
- `monobehaviour_frontier_entry_uses_buff`
- `monobehaviour_frontier_entry_uses_blackboard_key`
- `monobehaviour_frontier_entry_uses_mode`
- `monobehaviour_frontier_entry_uses_locator`
- `monobehaviour_frontier_entry_has_component_class`
- `monobehaviour_frontier_entry_model_asset_entity`

Node kinds populated from this slice include:

- `gameplay_skill`
- `model_config_model`
- `ai_config`
- `animation_config`
- `gameplay_effect`
- `buff`
- `gameplay_blackboard_key`
- `monobehaviour_mode_id`
- `monobehaviour_locator`
- `monobehaviour_managed_class`

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_monobehaviour_frontier_report()`:

- `monobehaviour_frontier_entry_uses_skill`: 4,235
- `monobehaviour_frontier_entry_uses_model`: 567
- `monobehaviour_frontier_entry_uses_ai_config`: 156
- `monobehaviour_frontier_entry_uses_animation_config`: 373
- `monobehaviour_frontier_entry_uses_gameplay_effect`: 77
- `monobehaviour_frontier_entry_uses_buff`: 213
- `monobehaviour_frontier_entry_uses_blackboard_key`: 107
- `monobehaviour_frontier_entry_uses_mode`: 1,570
- `monobehaviour_frontier_entry_uses_locator`: 2,383
- `monobehaviour_frontier_entry_has_component_class`: 1,710
- `monobehaviour_frontier_entry_model_asset_entity`: 0 in the focused graph
  because asset maps were disabled.

Focused node counts:

- `gameplay_skill`: 1,575
- `model_config_model`: 225
- `ai_config`: 66
- `animation_config`: 84
- `gameplay_effect`: 24
- `buff`: 22
- `gameplay_blackboard_key`: 63
- `monobehaviour_mode_id`: 55
- `monobehaviour_locator`: 379
- `monobehaviour_managed_class`: 101

Query checks:

- `common_enemy_passive_patrol --kind gameplay_skill` resolves through
  `modeConfig.modes[].extraPassiveSkillId[]` and
  `skillDataBundle.allPassiveSkillId[]`.
- `HeadBar --kind monobehaviour_locator` resolves through
  `locatorNames[]`.
- `eny_0007_mimicw_postmodel --kind model_config_model` resolves through
  `postModelKey` and `modelId`.
- `aiconf_eny_0007_mimicw --kind ai_config` resolves through `aiCfgPath`.
- `P_fxbat_enemy_hit_flash_01_asset --kind gameplay_effect` resolves through
  `hitFlashAsset`.
- `buff_chr_0031_mifu_potential_5 --kind buff` resolves through
  `maxPotentialEffectBuffId`.

## Interpretation

The strongest semantic hub remains `AbilitySystemData`, especially its
`skillDataBundle`, `modeConfig`, effects, blackboard, and locator/model
adjacent fields. The extraction is intentionally field-name based and keeps the
JSON path as evidence on every edge. It is useful for graph navigation and
recovery targeting, but it is not proof that the partially decoded tail is now
fully typed or behaviorally simulated.
