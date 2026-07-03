# Audio cue condition-key source graph recovery - 2026-07-03

## Context

`AudioCueTable.json` contains authored audio cue handlers with separate
`conditionExpr` and `behaviourExpr` trees. The source graph previously
recursively extracted every `stringValue` from both expressions as
`audio_cue_handler_uses_event`, which made condition trigger keys such as
`au_trigger_music_hongshan_002_raft_start` look like Wwise event usage.

This blurred the difference between "when this trigger key is active" and
"play this audio behavior event."

## Implementation

Updated `tools/endfield_source_graph.py` near the existing AudioCue helpers:

- `behaviourExpr` strings still produce `audio_cue_handler_uses_event`.
- `conditionExpr` strings now produce first-class
  `audio_cue_condition_key` nodes.
- Added forward and reverse edges:
  - `audio_cue_handler_condition_key`
  - `audio_cue_condition_key_used_by_handler`
- Edge data preserves `exprType`, `exprPath`, and the parent handler evidence.

No new ingest pass was needed; `AudioCueTable.json` is already handled by the
narrative audio semantic ingest.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/audio_cue_condition_validation.sqlite` with:

- `ingest_npc_voice_bark_semantics()`
- `ingest_narrative_audio_semantics()`

Observed focused counts:

- `audio_cue` nodes: 175
- `audio_cue_handler` nodes: 264
- `audio_cue_condition_key` nodes: 12
- `audio_cue_handler_condition_key` edges: 20
- `audio_cue_condition_key_used_by_handler` edges: 20
- all condition-key edges had `exprType == 8`
- `audio_cue_handler_uses_event` edges: 202 after excluding condition
  strings from event usage

Smoke queries confirmed:

- `au_trigger_music_hongshan_002_raft_start` resolves to
  `-1005274765:direct:1` through `audio_cue_condition_key_used_by_handler`.
- `-1005274765:direct:1` now separately links to condition key
  `au_trigger_music_hongshan_002_raft_start` and behavior event
  `au_music_hongshan_002_raft_A`.
- `base_mode_level_is_highest` resolves to the two authored direct handlers
  that use that condition key.
