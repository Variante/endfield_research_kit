# MonoBehaviour Semantic Reverse Source-Graph Recovery - 2026-07-06

## Scope

This pass added target-to-entry reverse edges for decoded MonoBehaviour
frontier semantic references. The source graph already emitted forward links
from decoded MonoBehaviour frontier entries to recovered gameplay concepts; the
new edges make target-centric queries possible without custom SQL.

The change covers forward refs emitted by
`monobehaviour_frontier_semantic_refs()` for:

- skills
- model config ids
- AI config ids
- animation config ids
- blackboard keys
- gameplay effects
- buffs
- mode ids
- locators
- managed component classes

Audio refs already use their own forward/reverse helper from the preceding
sound-name recovery pass.

## Added Reverse Edges

- `skill_used_by_monobehaviour_frontier_entry`
- `model_used_by_monobehaviour_frontier_entry`
- `ai_config_used_by_monobehaviour_frontier_entry`
- `animation_config_used_by_monobehaviour_frontier_entry`
- `blackboard_key_used_by_monobehaviour_frontier_entry`
- `gameplay_effect_used_by_monobehaviour_frontier_entry`
- `buff_used_by_monobehaviour_frontier_entry`
- `mode_used_by_monobehaviour_frontier_entry`
- `locator_used_by_monobehaviour_frontier_entry`
- `component_class_used_by_monobehaviour_frontier_entry`

## Evidence Scan

A read-only sample scan over gameplay, managed-reference, ability, NPC, and
character decoded groups checked 3,240 recovered MonoBehaviour payloads.
Observed forward semantic refs in that sample:

| Category | Refs |
| --- | ---: |
| effect | 8,610 |
| skill | 1,815 |
| locator | 1,386 |
| component_class | 702 |
| mode | 485 |
| buff | 185 |
| model | 177 |
| animation_config | 154 |
| audio | 114 |
| ai_config | 100 |
| blackboard_key | 91 |

Representative examples:

| Category | Example value | Evidence path |
| --- | --- | --- |
| skill | `chr_0031_mifu_plunging_attack_start` | `$.references.RefIds[].data.skillDataBundle.allNormalAttackId[]` |
| model | `chr_0031_mifu_postmodel` | `$.references.RefIds[].data.modelId` |
| animation_config | `anim_cfg_chr_0031_mifu` path refs | `$.references.RefIds[].data.animConfigPath` |
| blackboard_key | `EntityBB_normalskill_1_moveto` | `$.references.RefIds[].data.entityBlackboard.entries[].key` |
| buff | `buff_common_dash` | `$.references.RefIds[].data.dashBuff.entries[].buffId` |
| mode | `extra_attack` | `$.references.RefIds[].data.modeConfig.modes[].modeId` |
| locator | `HeadBar` | `$.references.RefIds[].data.locatorNames[]` |
| component_class | `CharacterRootComponentData` | `$.references.RefIds[].data.entityTemplate.componentList[].type.class` |

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/monobehaviour_semantic_reverse_validate.sqlite`

Validation payload:

`export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour/data_chr_0031_mifu_pD4E3FD98F53C84FA.json`

Focused counts:

| Category | Forward | Reverse | Missing reverse |
| --- | ---: | ---: | ---: |
| skill | 19 | 19 | 0 |
| model | 1 | 1 | 0 |
| animation_config | 2 | 2 | 0 |
| blackboard_key | 1 | 1 | 0 |
| buff | 3 | 3 | 0 |
| mode | 2 | 2 | 0 |
| locator | 26 | 26 | 0 |
| component_class | 26 | 26 | 0 |

## Interpretation

These edges do not prove runtime usage order, conditional activation, or
formula execution. They make existing decoded MonoBehaviour references
queryable from the target side, which helps connect characters, enemies,
abilities, buffs, effects, and component classes back to their recovered
source payloads.
