# Mission Flow Source Graph Query - 2026-07-06

## Scope

Added a `mission-flow` query to `tools/endfield_source_graph.py` for inspecting
static MissionRuntimeAsset structure from the source graph.

The original understanding report identified mission runtime data as strong
static quest-DAG evidence while still not proving observed player chronology or
runtime condition evaluation. This command makes that static evidence easier to
inspect from one seed.

## Query Behavior

Examples:

```bat
python tools\endfield_source_graph.py mission-flow a1m1 --limit 16
python tools\endfield_source_graph.py mission-flow a1m1_q#2 --kind quest_task --limit 16
python tools\endfield_source_graph.py mission-flow "a1m6d5:runtime PlayRadio 5a9a2a51" --kind mission_runtime_action --limit 12
python tools\endfield_source_graph.py mission-flow "a1m1_q#2 CombineCondition" --kind mission_runtime_condition --limit 12
```

The command accepts mission runtime assets, missions, quest tasks, runtime
actions, runtime conditions, levels, and story keys. It expands back to the
owning `mission_runtime_asset` where possible, then summarizes nearby graph
relations.

Returned groups include:

- `missionRuntimeAssets`
- `assets`
- `levelsAreas`
- `quests`
- `questDependencies`
- `conditions`
- `actions`
- `narrative`
- `rewards`
- `text`

Direct seed relations are ordered first, so focused action or condition lookups
surface the relevant action/condition edges before broader mission context.

## Evidence Model

The command is a compact view over existing graph edges such as:

- `mission_runtime_has_quest`
- `quest_task_depends_on_previous`
- `quest_has_runtime_condition`
- `mission_runtime_condition_type`
- `condition_reaches_level`
- `condition_checks_dialog_finish`
- `mission_runtime_has_action`
- `mission_runtime_action_next`
- `mission_runtime_action_plays_radio`
- `mission_runtime_action_references_narrative`
- `mission_runtime_rewards`
- `mission_runtime_name_text`

For `a1m1`, the current graph resolves `mission_runtime_asset:a1m1:runtime`,
links it to `map01_lv001`, `reward_mission_a1m1`, and two quest tasks. For
`a1m1_q#2`, it expands to the same runtime asset and exposes eleven runtime
condition links in the current validation sample.

## Interpretation

This is authored runtime-data evidence, not a simulation. It can show quest
dependency links, condition/action references, radio/story/dialog refs, level
links, rewards, and text ids, but it does not prove:

- observed player-visible chronology;
- live account mission state;
- condition evaluator truth values;
- action execution order beyond authored `_nextID` links;
- server-side unlock, reward, or activity state.

Use `mission-flow` when the question is "what does the original mission runtime
asset say this mission/quest/action/condition references?" Pair it with
`story`, `text-usage`, `audio-usage`, `item-usage`, and `map-usage` for deeper
cross-domain follow-up.

## Validation

Validated syntax and smoke queries:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py mission-flow --help
python tools\endfield_source_graph.py mission-flow a1m1 --limit 16
python tools\endfield_source_graph.py mission-flow a1m1_q#2 --kind quest_task --limit 16
python tools\endfield_source_graph.py mission-flow "a1m6d5:runtime PlayRadio 5a9a2a51" --kind mission_runtime_action --limit 12
python tools\endfield_source_graph.py mission-flow "a1m1_q#2 CombineCondition" --kind mission_runtime_condition --limit 12
```
