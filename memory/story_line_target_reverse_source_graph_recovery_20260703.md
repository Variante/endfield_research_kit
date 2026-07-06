# Story Line Target Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added explicit reverse lookup edges in the shared story and line
target helpers used by dialog support, narrative audio, and audio config table
ingests.

The reverse maps are keyed by existing forward edge kind. They only mirror exact
joins to generated `story` or `line` nodes that already exist in the WebUI
story graph. They do not infer route order, option branching, audio playback
rules, or story chronology.

## Added Story Edges

- `story_targeted_by_dialog_summary_map`
- `story_used_as_domain_depot_initial_dialog`
- `story_used_as_domain_depot_repeat_dialog`
- `story_targeted_by_sns_dialog`
- `story_targeted_by_radio`
- `story_targeted_by_remote_common`
- `story_targeted_by_audio_dialog_custom_event`

## Added Line Edges

- `line_has_text_voice_id_mapping`
- `line_has_dialog_text`
- `line_used_by_radio_row`
- `line_used_by_remote_common_row`
- `line_has_audio_voice_extra`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/story_line_reverse_validate.sqlite`

The validation seeded `ingest_webui_story()`,
`ingest_audio_config_semantics()`, `ingest_dialog_support_semantics()`, and
`ingest_narrative_audio_semantics()`.

| Edge | Count |
| --- | ---: |
| `dialog_summary_map_targets_story` | 890 |
| `story_targeted_by_dialog_summary_map` | 890 |
| `domain_depot_initial_dialog` | 15 |
| `story_used_as_domain_depot_initial_dialog` | 15 |
| `domain_depot_repeat_dialog` | 15 |
| `story_used_as_domain_depot_repeat_dialog` | 15 |
| `sns_dialog_targets_story` | 434 |
| `story_targeted_by_sns_dialog` | 434 |
| `radio_targets_story` | 2,375 |
| `story_targeted_by_radio` | 2,375 |
| `remote_common_targets_story` | 30 |
| `story_targeted_by_remote_common` | 30 |
| `audio_dialog_custom_event_targets_story` | 46 |
| `story_targeted_by_audio_dialog_custom_event` | 46 |
| `text_voice_id_line_node` | 180 |
| `line_has_text_voice_id_mapping` | 180 |
| `dialog_text_line_node` | 17,528 |
| `line_has_dialog_text` | 17,528 |
| `radio_line_node` | 4,103 |
| `line_used_by_radio_row` | 4,103 |
| `remote_common_line_node` | 284 |
| `line_used_by_remote_common_row` | 284 |
| `audio_voice_extra_line_node` | 928 |
| `line_has_audio_voice_extra` | 928 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `story` | 9,521 |
| `line` | 39,203 |
| `dialog_text` | 17,528 |
| `dialog_summary_map` | 931 |
| `domain_depot_deliver_target_dialog` | 15 |
| `sns_dialog` | 288 |
| `radio` | 2,375 |
| `remote_common` | 30 |
| `audio_dialog_custom_event` | 47 |
| `audio_voice_extra` | 25,245 |
