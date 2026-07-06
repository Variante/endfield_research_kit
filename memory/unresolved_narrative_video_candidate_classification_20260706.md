# Unresolved Narrative Video Candidate Classification - 2026-07-06

## Scope

This pass classified the three unresolved narrative-video candidates that have
generated story targets:

- `cs_video_dlg_e1m2_1` -> existing generated story `dlg_e1m2_1`
- `cs_video_e1m3_3` -> existing generated story `dlg_e1m3_3`
- `cs_video_e6m1_1` -> existing generated story `dlg_e6m1_1`

The source evidence is filename/key-candidate matching from the narrative video
override audit and source graph. None of the three has timeline-playable
evidence in the current report.

## Current Classification

All three are emitted as standalone `video_*` conversation bundles:

| Stem | Standalone key | Standalone refs | Candidate story | Candidate story video refs |
| --- | --- | ---: | --- | ---: |
| `cs_video_dlg_e1m2_1` | `video_cs_video_dlg_e1m2_1` | 2 | `dlg_e1m2_1` | 0 |
| `cs_video_e1m3_3` | `video_cs_video_e1m3_3` | 2 | `dlg_e1m3_3` | 0 |
| `cs_video_e6m1_1` | `video_cs_video_e6m1_1` | 4 | `dlg_e6m1_1` | 0 |

Each standalone bundle reports
`standaloneVideoNoAuthoritativeStoryBinding` in
`_debug.narrativeVideos.source.reason`.

## Tooling Update

`reports/source_graph/unresolved_narrative_video_candidates.json` and `.md`
now include:

- `standaloneVideoKey`
- `recommendation`

Recommendation values:

- `manual_attach_candidate_needs_timeline_or_playback_check` for
  `hasGeneratedStoryTarget` candidates.
- `keep_standalone_until_generated_target_exists` for no-target candidates.

## Interpretation

The three generated-target candidates are plausible manual attach candidates,
but this pass does not promote them into `webui/overrides/narrative_videos.json`.
Attaching would move them from standalone rows into dialog/cutscene display
without timeline or observed-playback proof. Keep them standalone until a
timeline playable, source-link, OCR/playback, or other runtime-order signal
proves placement.
