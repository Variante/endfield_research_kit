# Runtime Option Route Conflict Audit - 2026-07-06

## Scope

Added `python tools/endfield_source_graph.py option-route-audit` as a compact
drilldown for the runtime jump option-route audit evidence already stored in the
source graph. This addresses the smallest current story-control-flow gap from
the original understanding report: audit-backed option-route contradictions.

The command is intentionally diagnostic. It does not promote routes, change
WebUI overrides, or claim live runtime playback.

## Current Hotlist

`python tools/endfield_source_graph.py option-gaps --audit-only --limit 10`
returns four audit-only scenes:

- `dlg_c28m3_10`: one runtime route conflict.
- `dlg_c28m3_23`: incomplete runtime jump coverage, no conflict.
- `dlg_e6m1_10`: one runtime route conflict.
- `dlg_e6m4_14`: one runtime route conflict.

The three runtime audit conflicts are:

| Scene | Group | Option | Expected first line | Runtime first line | Runtime line owner |
| --- | ---: | --- | --- | --- | --- |
| `dlg_c28m3_10` | 1 | `option_dlg_c28m3_10_1_001` | `dlg_c28m3_10_023` | `dlg_c28m3_10_025` | `option_dlg_c28m3_10_1_002` |
| `dlg_e6m1_10` | 4 | `option_dlg_e6m1_10_4_002` | `dlg_e6m1_10_003` | `dlg_e6m1_10_016` | `option_dlg_e6m1_10_4_001` |
| `dlg_e6m4_14` | 2 | `option_dlg_e6m4_14_2_002` | `dlg_e6m4_14_021` | `dlg_e6m4_14_020` | `option_dlg_e6m4_14_2_001` |

For all three conflict rows, the recommendation is
`nearbyRuntimeJumpContradictsInferredPath`.

## Interpretation

The contradiction pattern is consistent: the inferred option response expects
one option to enter a particular first response line, but nearby Runtime Jump
evidence points at the first line currently assigned to another option. That
means the inferred branch mapping is suspect; it does not automatically prove
the runtime mapping is complete, because the nearby jump must still be
interpreted together with option index and post-jump option-change fields.

`dlg_c28m3_23` is different. It has
`nearbyRuntimeJumpIncompleteOptionCoverage`: the audit found insufficient
runtime jump coverage to prove all option paths, but it did not find a direct
expected-vs-runtime first-line contradiction.

## Useful Commands

```bat
python tools\endfield_source_graph.py option-route-audit --conflicts --limit 10
python tools\endfield_source_graph.py option-route-audit --story dlg_c28m3_10
python tools\endfield_source_graph.py option-route-audit --story dlg_e6m1_10
python tools\endfield_source_graph.py option-route-audit --story dlg_e6m4_14
python tools\endfield_source_graph.py option-route-audit --story dlg_c28m3_23
```

The command returns each audit group with:

- compact option refs
- candidate line ids and common continuation line
- conflict rows with expected/runtime first-line line refs
- expected, runtime, and directional first-line mappings
- nearby Runtime Jump clip refs and edge data
- source report paths

## Caveats

`expectedFirstLine` may reflect current inference or manual override state; it
is not independent runtime truth. `runtimeFirstLine` is recovered static
timeline evidence, not observed live playback. Nearby Runtime Jump edges remain
diagnostic until option-index mapping and post-jump option-change behavior are
fully proven.

## Next Step

The next story recovery pass should inspect the three conflict groups manually
against their `DialogOptionPlayableAsset` and `RuntimeJumpClip` tracks, then
decide whether any WebUI-only override should be adjusted or whether the audit
should remain as a warning until stronger runtime evidence is available.
