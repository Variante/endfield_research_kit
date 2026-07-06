# dlg_e6m1_10 Option Route Conflict Investigation - 2026-07-06

## Question

`dlg_e6m1_10` group 4 is one of the remaining runtime option-route conflicts
from the current story-control-flow hotlist. This pass checks whether it follows
the same late, targetless RuntimeJumpClip pattern as `dlg_c28m3_10`, or whether
it gives stronger evidence for the existing WebUI override.

## Graph Evidence

Command:

```bat
python tools\endfield_source_graph.py option-route-audit --story dlg_e6m1_10 --limit 20
```

The graph returns one conflict group:

- Scene: `dlg_e6m1_10`
- Group: `4`
- Recommendation: `nearbyRuntimeJumpContradictsInferredPath`
- Options:
  - `option_dlg_e6m1_10_4_001`, option index `3`
  - `option_dlg_e6m1_10_4_002`, option index `2`
- Candidate first lines:
  - `dlg_e6m1_10_016`
  - `dlg_e6m1_10_003`
- Common continuation:
  - `dlg_e6m1_10_004`

The audit conflict is:

| Option | Expected/inferred first line | Runtime first line | Runtime first-line candidate owner |
| --- | --- | --- | --- |
| `option_dlg_e6m1_10_4_002` | `dlg_e6m1_10_003` | `dlg_e6m1_10_016` | `option_dlg_e6m1_10_4_001` |

Relevant line timing:

| Line | Time | Speaker | Meaning |
| --- | ---: | --- | --- |
| `dlg_e6m1_10_011` | 19.417 | Zhuangfy | Pre-option anchor line. |
| `dlg_e6m1_10_016` | 30.100 | Pelica | Notices the erosion tide. |
| `dlg_e6m1_10_003` | 36.717 | Zhuangfy | Explains abnormal superfield activity and flooding. |
| `dlg_e6m1_10_004` | 46.333 | Zhuangfy | Common continuation about Xirang depletion. |

The source graph also shows a WebUI-only manual override for this group:

```json
{
  "responses": {
    "option_dlg_e6m1_10_4_001": ["dlg_e6m1_10_016"],
    "option_dlg_e6m1_10_4_002": ["dlg_e6m1_10_016"]
  },
  "notes": {
    "4": "Observation-system choices converge to Pelica noticing the erosion tide."
  }
}
```

This override is represented in the graph with `webui/option_override` edges
and `webuiOnly=true`.

## Raw Audit Records

Three audit reports contain the same group:

- `reports/runtime_jump_option_route_audit_CN_nearby.json`
- `reports/runtime_jump_option_route_audit_CN_nearby_promoted.json`
- `reports/runtime_jump_option_route_audit_CN_story_dlg_e6m1_10_dlg_e6m4_14_nearby.json`

The first two reports point at stale/missing timeline folder
`D51A2BD428D8BAE15AD67D4212A8603E`. The story-specific report points at the
current folder:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/2FA0A1186A99B33466EF687A717704F3/MonoBehaviour/
```

The runtime-audit asset path diagnostic added in the previous pass classifies
the stale `D51...` RuntimeJumpClip paths as `basename_resolved` and maps them to
the current `2FA0...` folder.

## Raw Timeline Evidence

Current option playable:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/2FA0A1186A99B33466EF687A717704F3/MonoBehaviour/DialogOptionPlayableAsset(Clone)(Clone)(Clone)_pB93650CB9CDAB3F8.json
```

Option entries:

```json
[
  {
    "_optionId": "option_dlg_e6m1_10_4_001",
    "optionIndex": 3,
    "changeFinishNum": 0,
    "targetFinishNum": 0,
    "trunkId": "",
    "dialogId": "",
    "logicId": 23753
  },
  {
    "_optionId": "option_dlg_e6m1_10_4_002",
    "optionIndex": 2,
    "changeFinishNum": 0,
    "targetFinishNum": 0,
    "trunkId": "",
    "dialogId": "",
    "logicId": 23754
  }
]
```

The option playable clip itself is on
`Dialog Trunk Track (1)_p08B6078E0812B3F8.json`:

- start `22.966667`
- duration `1.633333`
- end `24.6`
- asset PathID `-5100800692510346248`

Runtime jump tracks and clips:

- `Runtime Jump Track (2)_p81A0D500DBA7B3F8.json`
  - track option index: `3`
  - nearby clip start `26.216667`
  - duration `0.55`
  - end `26.766667`
  - clip option index `3`
  - asset `RuntimeJumpClip_pE84017749746B3F8.json`
  - payload:
    - `needChangeOptionAfterJump=1`
    - `optionIndexAfterJump=0`
    - `isReverseJump=0`
    - `isJumpFirst=0`
- `Runtime Jump Track (1)_p1802024CC9F6B3F8.json`
  - track option index: `2`
  - nearby clip start `26.766667`
  - duration `3.333333`
  - end `30.1`
  - clip option index `2`
  - asset `RuntimeJumpClip_p19FA7270061FB3F8.json`
  - payload:
    - `needChangeOptionAfterJump=1`
    - `optionIndexAfterJump=0`
    - `isReverseJump=0`
    - `isJumpFirst=0`
  - same track also has a later clip at `85.016667-91.016667`; that later clip
    is outside the group-4 nearby window.

Adjacent trunk timing:

```text
dlg_e6m1_10_011: 19.416667-22.2
option playable: 22.966667-24.6
optionIndex 3 jump: 26.216667-26.766667
optionIndex 2 jump: 26.766667-30.1
dlg_e6m1_10_016 starts: 30.1
dlg_e6m1_10_003 starts: 36.716667
dlg_e6m1_10_004 starts: 46.333333
```

## Interpretation

This conflict is not the same shape as `dlg_c28m3_10`.

In `dlg_c28m3_10`, the raw option tracks supported the inferred split paths and
the late RuntimeJumpClip was targetless. In `dlg_e6m1_10`, both nearby
RuntimeJumpClips explicitly set `needChangeOptionAfterJump=1`, but both reset
to `optionIndexAfterJump=0`. The audit interprets the option-index-2 jump that
ends exactly at `dlg_e6m1_10_016` as evidence that option 002 also reaches line
016, contradicting the inferred `003` first line.

The raw files still do not directly prove first response lines:

- both option entries have empty `trunkId` and `dialogId`;
- the RuntimeJumpClip payloads do not store target line ids;
- the route result is a timing inference from option indices, jump timing, and
  nearby trunk clip starts.

The existing WebUI override is therefore reasonable but should remain marked as
WebUI-only/manual: both choices converge to `dlg_e6m1_10_016`, matching the
runtime audit direction and the note that both observation-system choices lead
to Pelica noticing the erosion tide.

## Recovery Boundary

This pass does not justify promoting the route to hard runtime truth. It does
support keeping the current manual override and keeping the conflict warning
auditable:

- The override is aligned with runtime-jump timing evidence.
- The direct target fields are still missing.
- The jump semantics of `needChangeOptionAfterJump=1` with
  `optionIndexAfterJump=0` still need runtime-side interpretation.

## Next Checks

- Inspect `dlg_e6m4_14` group 2 to see whether it matches the `c28m3` pattern
  or the `e6m1` reset-to-default pattern.
- Teach `option-route-audit` output to collapse duplicate audit reports by
  `sceneKey/group/sourceReport` or expose a per-report list more compactly.
- Continue looking for the runtime writer/consumer of option active-clip and
  post-jump option-change fields before promoting inferred routes.
