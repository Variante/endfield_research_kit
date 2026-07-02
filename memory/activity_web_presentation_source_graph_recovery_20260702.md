# Activity Web Presentation Source Graph Recovery - 2026-07-02

## Scope

Recovered first-class source graph coverage for the compact activity
web/presentation tables left outside the activity semantic groups:

- `AdventureActivityDataTable`
- `ActivityWebTable`
- `ActivityGlobalEffectTable`
- `ActivityArknightsBirthMultiStageTable`

These tables are not core activity progression rules. They connect activity UI
cards, web-entry jumps, global-effect wrappers, and Arknights-birth web stages
to the broader activity, item, reward, effect, and jump graph.

## Recovered Semantics

`AdventureActivityDataTable` now emits `adventure_activity_entry` nodes with
name text, reward item refs, and asset aliases for background, decoration, and
title images.

`ActivityWebTable` now emits `activity_web_entry` nodes and links them to
`system_jump` targets through `activity_web_entry_jump`.

`ActivityGlobalEffectTable` now emits `activity_global_effect_group` nodes and
links each configured effect id to `global_effect` nodes.

`ActivityArknightsBirthMultiStageTable` now emits `activity_web_stage` nodes
with panel metadata, stage links, web jump refs, and reward refs.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\activity_web_presentation_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1628820 nodes, 3058104 edges, 2235461 aliases
```

Focused semantic counts:

```text
NODE adventure_activity_entry 3
NODE activity_web_entry 3
NODE activity_global_effect_group 3
NODE activity_web_stage 2
EDGE defines_adventure_activity_entry 3
EDGE adventure_activity_name_text 3
EDGE adventure_activity_reward_item 4
EDGE defines_activity_web_entry 3
EDGE activity_web_entry_jump 3
EDGE defines_activity_global_effect_group 3
EDGE activity_global_effect_group_effect 3
EDGE defines_activity_web_stage 2
EDGE activity_web_stage_jump 2
EDGE activity_web_stage_reward 2
```
