# Project C Scene Order Stage 4

Date: 2026-06-26

This note records the current Project C coarse-order pass from exported game
data. The scratch analyzer is:

```text
scratch/il2cpp_gameplay_sim/stage4_coarse_order/recover_coarse_order.py
```

Generated scratch outputs:

```text
scratch/il2cpp_gameplay_sim/stage4_coarse_order/coarse_order_report.json
scratch/il2cpp_gameplay_sim/stage4_coarse_order/coarse_order_report.md
```

## Inputs

- Observed calibration: `memory/e0m0_observed_order_calibration.json`
- Active override: `webui/overrides/story_order.json`
- LevelScript decode inputs: `indie_dg002`, `indie_dg004`
- Focused structured JSON probe roots: `MissionRuntimeAsset`, `LevelData`,
  `SpawnerConfig`

## Scores

| candidate | scored | inversions | rate |
| --- | ---: | ---: | ---: |
| active override full order | 45 | 1 / 990 | 0.10% |
| all first LevelScript story refs | 40 | 145 / 780 | 18.59% |
| q11 actionList first refs | 11 | 31 / 55 | 56.36% |
| q11 header signal refs | 5 | 1 / 10 | 10.00% |
| q11 getter debounce refs | 5 | 1 / 10 | 10.00% |
| q11 header/getter union refs | 5 | 1 / 10 | 10.00% |

## Findings

The raw LevelScript action-list order is real client data, but it is not a
runtime chronology signal for the q11 boss cluster. The action-list-first q11
sequence starts with `cutscene_e0m0_4 -> cutscene_e0m0_5`, then only later
reaches `cutscene_e0m0_3`, which contradicts the observed boss-cluster order
and produces 31 inversions over 55 scored pairs.

The header/getter debounce family is a weaker but useful recovery signal. It
recovers `radio_e0m0_13`, `radio_e0m0_14`, `radio_e0m0_15`,
`radio_e0m0_16_1`, `radio_e0m0_17`, `radio_e0m0_20`,
`radio_e0m0_16_2`, and `radio_e0m0_16_3` from `8700050001`. This proves
membership and debounce/signal grouping, including the WebUI-only
`radio_e0m0_16_1/2/3` rows, but it still should not be promoted as full
chronology. Its only scored q11 inversion is `radio_e0m0_15` before
`radio_e0m0_17`.

`radio_e0m0_22` and `radio_e0m0_23` remain action-only q11 nodes in the
decoded client data. They are present in `8700050001`, but not in the
header/getter debounce family.

`video_cs_video_e0m0_3` remains source-backed as a media mirror adjacent to
`cutscene_e0m0_3`; the adjacency comes from the AnimeStudio FMV binding, not
from LevelScript action ordering.

`radio_e0m0_21` is still absent from this LevelScript pass and from source
graph evidence beyond the generated WebUI story row. The active override has
`radio_e0m0_21` before `cutscene_e0m0_tombstonecollapseCam`, while the
observed calibration has the tombstone collapse cutscene first. Game data
currently supports the tombstone collapse cutscene through LevelScript, but
does not yet expose the `radio_e0m0_21` trigger.

The focused BattlerStage lead did not produce exported structured-data hits in
the probed roots. Token counts for `BattlerStage`, `stageIndex`,
`PlayCutscene`, `PlayFmv`, and `checkpointPropertyKey` were all zero.

## Limitation Summary

Project C can recover three useful classes of scene-order evidence from the
client export:

1. **Membership**: a story key belongs to a mission/script/quest cluster.
   Example: q11 radios and cutscenes are clearly tied to `8700050001`.
2. **Adjacency inside one asset**: a media row belongs beside a story row.
   Example: `video_cs_video_e0m0_3` is adjacent to `cutscene_e0m0_3` because
   the AnimeStudio timeline binds the FMV to that cutscene.
3. **Local signal/debounce structure**: a play-once property or header/getter
   family exists around a radio/cutscene key. Example:
   `radio_e0m0_16_1/2/3` are recoverable as q11 signal-only rows.

Project C cannot currently recover the full runtime chronology for clusters
whose playback is selected by state outside the decoded static graph. The q11
boss cluster is the clearest example: the same script owns multiple concrete
play actions, but the action-list order, byte order, numeric suffix order,
header/getter order, and asset metadata disagree with the observed runtime
interleave. The static data proves "these rows are part of this boss phase";
it does not prove "this exact row fires before that exact row" once gameplay or
server event state controls the branch.

The missing evidence is likely one of:

- runtime/server event callbacks that set phase state;
- hash-keyed references not yet decoded into story keys;
- IL2CPP gameplay control flow that calls the play action directly or writes
  the state consumed by LevelScript headers;
- live runtime traces from a controlled replay.

Until one of those evidence types is recovered, any q11 total order beyond the
current manual/observed calibration should be labeled partial or observed, not
source-backed. The safe automated builder target is coarse grouping plus
explicit uncertainty, not a forced total ordering.

## All Main Story Comparison

Generated comparison:

```text
reports/mission_order/main_story_order_vs_override_CN.json
reports/mission_order/main_story_order_vs_override_CN.md
```

Scope: all `e*` main-story missions present in CN WebUI data or in
`webui/overrides/story_order.json` (`58` missions).

The scratch generator is:

```text
scratch/main_story_order_compare/recover_main_story_order_compare.py
```

The recovered static order covers the override rows well but does not match
the override as a strict total sequence:

- override rows: `1910`
- recovered rows: `1917`
- shared rows: `1910`
- missing override rows: `0`
- recovered-only rows: `7`
- strict pair inversions: `13761 / 43244` (`31.82%`)
- exact strict matches: `3 / 58` missions

The coarse phase comparison is more useful. It ignores pairs inside the same
recovered quest bucket and only scores pairs where both rows have a recovered
quest/phase bucket:

- comparable coarse pairs: `9834`
- coarse inversions: `1610` (`16.37%`)
- same-bucket pairs: `2110`
- unknown-bucket pairs: `31300`

Interpretation: current static data can usually assemble a complete candidate
row set and often recover broad phase buckets, but it cannot recover the final
main-story row order at override quality. Many rows either fall into the same
phase bucket or have no recovered quest bucket at all, and static source edges
still over-promote control-flow/file-order signals that gameplay can interleave
differently at runtime. The active override remains the correct Story sort
source; the recovered order is best used as a coverage/evidence audit and a
queue for finding missing runtime/server-event evidence.

## Guidance

Do not promote q11 action-list order into the story-order builder. It is useful
membership evidence and a clue to active script structure, but not chronology.

Use the q11 header/getter order only as signal/debounce evidence unless a later
runtime or branch decode connects those gates to concrete playback order.

The next useful Project C lead is not another broad static LevelScript ordering
rule. It likely requires runtime/server-event decoding, hash-key decoding, or
IL2CPP control-flow work around gameplay callbacks that set q11 phase state and
fire `radio_e0m0_21`.
