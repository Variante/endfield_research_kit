# FMV Video Reverse Source Graph Recovery - 2026-07-03

## Context

FMV binding data and WebUI narrative video data already linked stories,
missions, FMV bindings, timeline clips, and video files in the forward
direction. Starting from a video, story, mission, or FMV clip still did not
directly show the binding/story context that used it.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for FMV and narrative
video relationships:

- `story_has_fmv_binding`
- `mission_has_fmv_binding`
- `video_used_by_fmv_binding`
- `fmv_clip_used_by_binding`
- `video_used_by_story_narrative`

The reverse edges preserve the same source, evidence, and payload data as the
existing forward edges.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\fmv_video_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,818,804 edges.
Forward/reverse counts matched:

- `fmv_binding_targets_story`: 29 / `story_has_fmv_binding`: 29
- `fmv_binding_in_mission`: 29 / `mission_has_fmv_binding`: 29
- `fmv_binding_uses_video`: 84 / `video_used_by_fmv_binding`: 84
- `fmv_binding_timeline_clip`: 29 / `fmv_clip_used_by_binding`: 29
- `has_narrative_video`: 320 / `video_used_by_story_narrative`: 320
