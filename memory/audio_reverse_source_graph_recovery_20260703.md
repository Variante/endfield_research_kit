# Audio Reverse Source Graph Recovery - 2026-07-03

## Context

Audio-centered graph queries had many forward references from story lines,
dialog support tables, decoded config rows, lipsync clips, and AudioDialog
metadata, but most audio nodes did not point back to their semantic consumers.
This made an audio-id lookup good for locating the audio node itself but weak
for answering which line, table semantic row, config entry, or actor channel
used it.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for the main audio
target relationships:

- `audio_used_by_line`
- `audio_used_by_dialog_text`
- `audio_used_by_skill_data`
- `audio_used_by_responsive_response`
- `audio_used_by_radio_line`
- `audio_used_by_env_talk`
- `audio_used_by_level_data`
- `audio_used_by_level_script`
- `audio_used_by_level_script_template`
- `audio_used_by_buff_data`
- `audio_used_by_spawner_enemy_prewarn`
- `audio_has_lipsync_clip`
- `audio_used_by_interactive_template`
- `audio_used_by_domain_ui`
- `audio_used_by_text_voice_id`
- `audio_used_by_factory_announcement`
- `audio_used_by_vo_tone`
- `audio_used_by_vo_tone_variant`
- `audio_used_by_sequence_dialog`
- `audio_used_by_remote_common_line_voice`
- `audio_used_by_remote_common_line`
- `audio_used_by_remote_common_line_music`
- `audio_used_by_activity_stamina_refund_bg_state`
- `actor_has_speaker_channel`

The generic `add_audio_target_edge()` helper now accepts an optional
`reverse_edge_kind`, and the AudioDialog reference helper similarly accepts an
optional reverse edge name for resolved AudioDialog-to-audio links.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary focused graph:

```bat
python tools\endfield_source_graph.py build --db tmp\audio_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The focused graph built successfully with 1,691,485 nodes and 3,718,934 edges.
Forward/reverse counts matched:

- `uses_audio`: 24,738 / `audio_used_by_line`: 24,738
- `dialog_text_uses_audio`: 17,329 / `audio_used_by_dialog_text`: 17,329
- `skill_data_references_audio`: 6,178 / `audio_used_by_skill_data`: 6,178
- `responsive_response_uses_audio`: 4,304 / `audio_used_by_responsive_response`: 4,304
- `radio_line_uses_audio`: 4,103 / `audio_used_by_radio_line`: 4,103
- `env_talk_uses_audio`: 2,537 / `audio_used_by_env_talk`: 2,537
- `level_script_references_audio`: 1,403 / `audio_used_by_level_script`: 1,403
- `spawner_enemy_prewarn_audio`: 864 / `audio_used_by_spawner_enemy_prewarn`: 864
- `lipsync_for_audio`: 64,920 / `audio_has_lipsync_clip`: 64,920
- `speaker_channel`: 25,245 / `actor_has_speaker_channel`: 25,245

All remaining checked pairs, including domain UI audio, AudioVoTone variants,
AudioSequenceDialog rows, remote common line voice/audio/music, and activity
stamina refund audio, also matched their forward counts.
