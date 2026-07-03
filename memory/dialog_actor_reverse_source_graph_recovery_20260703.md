# Dialog Actor Reverse Source Graph Recovery - 2026-07-03

## Context

Dialog registry and WebUI story ingests already linked registry scenes to
stories, registry scenes to lines/options, lines/options back to stories, and
story lines to speakers. Dialog support tables also resolved many speaker-like
fields to actor or character nodes. Starting from a story, line, option, actor,
or character was still less direct because several useful reverse edges were
missing.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for dialog registry,
story actor, and dialog-support actor/character relationships:

- `story_has_dialog_registry_scene`
- `line_in_dialog_registry_scene`
- `story_has_dialog_registry_line`
- `option_in_dialog_registry_scene`
- `story_has_dialog_registry_option`
- `actor_mentioned_by_story`
- `actor_speaks_line`
- `actor_speaks_audio_sequence_dialog`
- `character_speaks_audio_sequence_dialog`
- `actor_speaks_dialog_text`
- `character_speaks_dialog_text`
- `actor_owns_sns_chat`
- `character_owns_sns_chat`
- `actor_used_by_sns_option`
- `character_used_by_sns_option`
- `actor_speaks_sns_content`
- `character_speaks_sns_content`
- `actor_speaks_radio_line`
- `character_speaks_radio_line`
- `actor_used_by_remote_common_line_middle`
- `character_used_by_remote_common_line_middle`
- `actor_speaks_remote_common_line`
- `character_speaks_remote_common_line`

These edges preserve the same source, evidence, and payload data as the forward
relationships, including registry trunk/group keys and recovered ordering
indexes. The shared actor/character resolver now accepts explicit reverse edge
names for call sites that can safely describe the inverse relationship.

## Validation

Syntax check:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Temporary focused graph:

```bat
python tools\endfield_source_graph.py build --db tmp\actor_dialog_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,798,317 edges.

Counts:

- `dialog_registry_targets_story`: 4,918 / `story_has_dialog_registry_scene`: 4,918
- `dialog_registry_has_line`: 3,589 / `line_in_dialog_registry_scene`: 3,589
- `dialog_registry_line_for_story`: 3,589 / `story_has_dialog_registry_line`: 3,589
- `dialog_registry_has_option`: 4,131 / `option_in_dialog_registry_scene`: 4,131
- `dialog_registry_option_for_story`: 4,131 / `story_has_dialog_registry_option`: 4,131
- `mentions_actor`: 7,972 / `actor_mentioned_by_story`: 7,972
- `spoken_by`: 24,206 / `actor_speaks_line`: 24,206
- `audio_sequence_dialog_speaker_actor`: 80 / `actor_speaks_audio_sequence_dialog`: 80
- `audio_sequence_dialog_speaker_character`: 80 / `character_speaks_audio_sequence_dialog`: 80
- `dialog_text_actor`: 15,337 / `actor_speaks_dialog_text`: 15,337
- `sns_chat_owner_actor`: 4 / `actor_owns_sns_chat`: 4
- `sns_option_uses_actor`: 9 / `actor_used_by_sns_option`: 9
- `sns_content_speaker_actor`: 5,237 / `actor_speaks_sns_content`: 5,237
- `radio_line_actor`: 3,760 / `actor_speaks_radio_line`: 3,760
- `remote_common_line_middle_actor`: 284 / `actor_used_by_remote_common_line_middle`: 284
- `remote_common_line_middle_character`: 188 / `character_used_by_remote_common_line_middle`: 188
- `remote_common_line_actor`: 934 / `actor_speaks_remote_common_line`: 934
- `remote_common_line_character`: 934 / `character_speaks_remote_common_line`: 934

Character fallback pairs that did not resolve in this focused build, such as
`dialog_text_character` and `radio_line_character`, also matched at zero.
