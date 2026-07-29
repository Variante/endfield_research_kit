# Cutscene Timeline event-surface audit

- Root playback aliases: **4**
- Object indexes: **2** files / **1,337,486** rows
- Candidate event/mission surfaces: **0**
- Finding: `no_authored_event_or_mission_surface_in_exact_played_timelines`

## Exact played Timeline assets

| Root | Played TimelineAsset | CAB objects | Typed script classes | Surface |
|---|---|---:|---|---|
| `cutscene_e11m2_liexi_xs_m_01_last_01` | `cutscene_e11m2_liexi_xs_m_01_last_02` | 11 | `UnityEngine.Timeline.ControlPlayableAsset` x5, `UnityEngine.Timeline.ControlTrack` x5, `UnityEngine.Timeline.TimelineAsset` x1 | `no_authored_event_or_mission_surface_in_exact_played_timeline` |
| `cutscene_e11m2_liexi_xs_m_01_last_02` | `cutscene_e11m2_liexi_xs_m_01_last_03` | 11 | `UnityEngine.Timeline.ControlPlayableAsset` x5, `UnityEngine.Timeline.ControlTrack` x5, `UnityEngine.Timeline.TimelineAsset` x1 | `no_authored_event_or_mission_surface_in_exact_played_timeline` |
| `cutscene_f1m9d3_1` | `cutscene_f1m9d4_1` | 11 | `UnityEngine.Timeline.ControlPlayableAsset` x5, `UnityEngine.Timeline.ControlTrack` x5, `UnityEngine.Timeline.TimelineAsset` x1 | `no_authored_event_or_mission_surface_in_exact_played_timeline` |
| `cutscene_gm02m4_3` | `cutscene_gm02m4_1` | 11 | `UnityEngine.Timeline.ControlPlayableAsset` x5, `UnityEngine.Timeline.ControlTrack` x5, `UnityEngine.Timeline.TimelineAsset` x1 | `no_authored_event_or_mission_surface_in_exact_played_timeline` |

## Evidence boundary

Exact reverse-PPtr root/director/playable binding plus exact source/CAB/offset/PathID object-index identity and fully decoded typed TimelineAsset.

The complete indexed CAB of the exact played TimelineAsset has no event/signal/marker/mission/quest/level/global-named typed track or scalar surface.

Absence of an emitted-event surface does not prove that the root is unused, definition-only, mission-owned, or ordered. External registries, server/runtime selectors, indirect native state, and future builds remain outside this audit.
