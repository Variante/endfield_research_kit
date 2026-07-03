# Mission Runtime Reverse Links Source Graph Recovery - 2026-07-03

## Scope

The source graph now adds target-side reverse evidence for mission runtime
actions, action maps, and dialog-finish conditions. This improves target-first
questions such as "which runtime action plays this radio?" or "which condition
waits for this dialog?" without changing mission runtime parsing or claiming
full execution-order simulation.

## Graph Additions

New reverse edges:

- `radio_used_by_mission_runtime_action`
- `sns_dialog_used_by_mission_runtime_action`
- `remote_common_used_by_mission_runtime_action`
- `story_used_by_mission_runtime_action`
- `radio_used_by_mission_runtime_action_map`
- `story_used_by_mission_runtime_action_map`
- `story_used_by_mission_runtime_condition`
- `i18n_text_used_by_mission_runtime_action`
- `chapter_panel_used_by_mission_runtime_action`
- `mission_runtime_action_previous`

The shared narrative helper now names reverse edges by owner kind:

- `mission_runtime_action` owners use `*_used_by_mission_runtime_action`.
- `mission_runtime_asset` `actionMapRaw` references use
  `*_used_by_mission_runtime_action_map`.
- `mission_runtime_condition` references use
  `*_used_by_mission_runtime_condition`.

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_decoded_config_semantics()`:

- `mission_runtime_action_references_narrative`: 349
- `mission_runtime_action_map_references_narrative`: 345
- `mission_runtime_action_plays_radio`: 345
- `mission_runtime_action_text`: 69
- `mission_runtime_action_shows_chapter_panel`: 17
- `mission_runtime_action_next`: 7

New reverse-edge counts:

- `radio_used_by_mission_runtime_action`: 694
- `radio_used_by_mission_runtime_action_map`: 345
- `story_used_by_mission_runtime_condition`: 449
- `i18n_text_used_by_mission_runtime_action`: 69
- `chapter_panel_used_by_mission_runtime_action`: 17
- `mission_runtime_action_previous`: 7

The action-radio reverse count is larger than
`mission_runtime_action_plays_radio` because the same radio ids are also found
by the generic action string scan as
`mission_runtime_action_references_narrative`. Both edges keep separate
evidence paths, such as `_radioId` and `storyRef[0]`.

Query checks:

- `radio --kind radio` now shows `radio_used_by_mission_runtime_action`
  neighbors pointing back to `PlayRadio` actions.
- `main_e2 --kind mission_runtime_chapter_panel` shows
  `chapter_panel_used_by_mission_runtime_action` pointing back to the
  `ShowChapterCompletedPanel` action in `e1m10`.
- `mission_runtime_action_previous` mirrors all 7 `_nextID` action-chain edges.
- `story_used_by_mission_runtime_condition` links dialog ids such as
  `dlg_a1m10_1` to `CheckTalkOptionFinish` condition nodes.

## Interpretation

This is a graph explainability improvement for mission chronology and runtime
control-flow evidence. It does not prove live execution order beyond authored
references, but it makes the existing authored action, action-map, and
condition references navigable from their narrative/text/chapter targets.
