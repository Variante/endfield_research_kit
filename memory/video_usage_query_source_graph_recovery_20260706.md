# Video Usage Query Source Graph Recovery - 2026-07-06

## Context

The source graph already held FMV binding, WebUI narrative-video, narrative
video override/audit, and FMV playable PathID evidence, but lookup required
knowing several separate edge families. This made it awkward to start from a
story key, FMV id, video file/stem, unresolved narrative-video stem, or playable
PathID and see the same evidence chain.

## Change

`tools/endfield_source_graph.py` now has a `video-usage` query. It resolves
terms through these seed kinds by default:

- `fmv_binding`
- `video`
- `story`
- `mission`
- `fmv_clip`
- `unity_pathid`
- `unity_asset`
- `asset`
- `narrative_video_stem`
- `narrative_video_override_rule`
- `narrative_video_unresolved_candidate`

The query reports direct FMV/story/mission/video/clip/source-file/PathID edges,
WebUI narrative-video edges, narrative-video override and unresolved-candidate
audit edges, and second-hop FMV playable owner/asset evidence from PathID seeds.

High-signal edge families include:

- FMV binding context: `fmv_binding_targets_story`,
  `story_has_fmv_binding`, `fmv_binding_in_mission`,
  `mission_has_fmv_binding`.
- Video file use: `fmv_binding_uses_video`, `video_used_by_fmv_binding`,
  `has_narrative_video`, `video_used_by_story_narrative`.
- Timeline/source proof: `fmv_binding_timeline_clip`,
  `fmv_clip_used_by_binding`, `fmv_binding_source_file`,
  `fmv_binding_playable_pathid`.
- AssetMap bridge where present: `fmv_playable_pathid_resolves_unity_asset`,
  `unity_asset_used_by_fmv_playable_pathid`,
  `fmv_playable_pathid_exports_asset`,
  `asset_export_used_by_fmv_playable_pathid`.
- Audit and stem evidence: `narrative_video_override_uses_stem`,
  `narrative_video_stem_resolves_video`,
  `narrative_video_filename_candidate_file`,
  `narrative_video_unresolved_candidate_uses_stem`,
  `narrative_video_unresolved_rel_video`.

## Validation

Syntax and CLI checks:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py --help
```

Smoke checks against the current default graph:

```bat
python tools\endfield_source_graph.py video-usage cs_video_dlg_e10m1_1 --kind fmv_binding --limit 6
python tools\endfield_source_graph.py video-usage dlg_e10m1_1 --kind story --limit 6
python tools\endfield_source_graph.py video-usage StreamingAssets-structured/Data/Video/PC/Narrative/Cutscene/cs_video_dlg_e10m1_1.mp4 --kind video --limit 6
python tools\endfield_source_graph.py video-usage pathid:-7643592810396086263 --kind unity_pathid --limit 6
python tools\endfield_source_graph.py video-usage cs_video_dlg_e1m2_1 --kind narrative_video_stem --limit 6
```

Observed evidence:

- `cs_video_dlg_e10m1_1` resolves as an FMV binding, links to story
  `dlg_e10m1_1`, mission `e10m1`, two video refs, a timeline clip, source file,
  and playable PathID `-7643592810396086263`.
- `dlg_e10m1_1` reports both WebUI narrative-video attachments and the reverse
  FMV binding edge.
- The exact StreamingAssets video path reports FMV binding and story narrative
  users.
- `pathid:-7643592810396086263` reports both the binding and clip owners through
  `fmv_binding_playable_pathid`.
- `cs_video_dlg_e1m2_1` resolves as a narrative-video stem and returns the
  unresolved candidate audit context.

## Boundary

This is binding/reference evidence, not a runtime playback simulator.
`fmv_binding_targets_story` can come from `fallbackSceneHint`, so it proves a
recovered binding association rather than exact playback placement in every
case. Narrative-video audit rows are filename/stem/key-candidate evidence, not
Timeline proof. FMV playable Unity-asset links require a graph build that
includes matching source-root AssetMap rows; quick or stale graphs may show only
the direct PathID owner evidence.
