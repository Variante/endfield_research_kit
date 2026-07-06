# Voice Audio Links Source Graph Report Recovery - 2026-07-06

## Summary

Refined `emit_voice_audio_links()` in `tools/endfield_source_graph.py` so the
generated source-graph follow-up report separates WebUI story-line audio ids
from graph relations that already resolve to path-backed `AudioDialog` audio
nodes.

This is a source-graph report improvement only. It does not relink Story audio,
change WebUI output, decode new Wwise media, or promote inferred audio
matches.

## Problem

The older `reports/source_graph/voice_audio_links.json` reported:

- `linked`: 0
- `unresolved`: 24,738

That was technically true for `line -> uses_audio` WebUI Story edges, because
those audio nodes are story ids such as `au_dlg_a1m10_1_001` with no WEM path
on the graph node. It was misleading as a source-graph audio overview because
the same graph also contains many path-backed `AudioDialog` audio nodes and
non-Story audio usage relations.

## Current Report Behavior

The refreshed report now writes:

- `voice_audio_links.json`
- `voice_audio_links.md`

The JSON report includes:

- `summary.storyLineAudioRefs`
- `summary.storyLineLinked`
- `summary.storyLineUnresolved`
- `summary.pathBackedUsageLinks`
- `summary.pathBackedUniqueAudio`
- `summary.storyAudioIdsAlsoPathBacked`
- path-backed usage counts by edge kind and owner kind
- sampled path-backed links
- sampled unresolved Story line audio ids

## Validation

Validated by refreshing the ignored generated reports from the current SQLite
source graph.

Observed summary:

```json
{
  "storyLineAudioRefs": 24738,
  "storyLineLinked": 0,
  "storyLineUnresolved": 24738,
  "pathBackedUsageLinks": 18123,
  "pathBackedUniqueAudio": 10820,
  "storyAudioIdsAlsoPathBacked": 0
}
```

Top path-backed usage edge counts:

```text
actor_has_speaker_channel: 10820
responsive_response_uses_audio: 4304
has_profile_voice: 2210
audio_vo_tone_has_variant_audio: 291
remote_common_line_uses_voice: 265
audio_vo_tone_for_audio: 115
audio_sequence_dialog_uses_audio: 100
audio_factory_announcement_uses_voice: 13
level_script_references_audio: 3
text_voice_id_uses_audio: 2
```

The key semantic boundary is now explicit: the graph has substantial
path-backed narrative/audio-config evidence, but the WebUI Story line audio ids
in `uses_audio` still do not resolve to those path-backed `AudioDialog` nodes
by id.

`python -m py_compile tools\endfield_source_graph.py` passes.
