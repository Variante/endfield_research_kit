# Guide Group Reverse Source Graph Recovery - 2026-07-03

## Context

Guide groups appeared across mission runtime actions, mission completion
conditions, wiki-limited guides, factory dungeon reward prompts, character
tutorial stages, and character trials. Existing graph edges mostly pointed from
the consumer toward the `guide_group`, so starting from a guide group id still
required manual SQL to explain where it was used.

## Change

`tools/endfield_source_graph.py` now emits reverse guide-group usage edges for
the explicit guide-group fields already decoded by current inputs:

- `guide_group_used_by_mission_runtime_media_action`
- `guide_group_used_by_mission_runtime_action`
- `guide_group_checked_by_condition`
- `guide_group_used_by_wiki_limited_guide`
- `guide_group_used_by_factory_dungeon_after_reward`
- `guide_group_used_by_tutorial_stage`
- `guide_group_used_by_trial`

The pass also adds `wiki_limited_guide_uses_guide_group`, linking
`wiki_limited_guide` nodes to the shared `guide_group` node keyed by
`guideGroupId`. Mission runtime `CheckGuideGroupComplete` conditions now link
to their `_guideGroupId` targets with `condition_checks_guide_group_complete`,
preserving `_completeType` in edge data.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\guide_group_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,589 nodes and 3,821,224 edges.
Forward/reverse counts matched:

- `mission_runtime_action_media_guide_group`: 69 / `guide_group_used_by_mission_runtime_media_action`: 69
- `mission_runtime_action_guide_group`: 64 / `guide_group_used_by_mission_runtime_action`: 64
- `condition_checks_guide_group_complete`: 31 / `guide_group_checked_by_condition`: 31
- `wiki_limited_guide_uses_guide_group`: 118 / `guide_group_used_by_wiki_limited_guide`: 118
- `factory_dungeon_after_reward_guide`: 3 / `guide_group_used_by_factory_dungeon_after_reward`: 3
- `tutorial_stage_uses_guide_group`: 75 / `guide_group_used_by_tutorial_stage`: 75
- `trial_uses_guide_group`: 1 / `guide_group_used_by_trial`: 1

The graph contains 278 `guide_group` nodes. There are 62
`CheckGuideGroupComplete` type edges because Persistent and StreamingAssets
runtime entries both contribute source observations, but they collapse to 31
distinct condition nodes and 31 distinct `condition_checks_guide_group_complete`
edges.
