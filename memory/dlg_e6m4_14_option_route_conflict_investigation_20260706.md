# dlg_e6m4_14 Option Route Conflict Investigation - 2026-07-06

## Question

`dlg_e6m4_14` group 2 is the third runtime option-route conflict from the
current story-control-flow hotlist. This pass checks whether the conflict
matches the late, targetless `dlg_c28m3_10` pattern, the
`needChangeOptionAfterJump` convergence pattern from `dlg_e6m1_10`, or a
separate shape.

## Graph Evidence

The runtime-jump audit reports one group:

- Scene: `dlg_e6m4_14`
- Group: `2`
- Recommendation: `nearbyRuntimeJumpContradictsInferredPath`
- Options:
  - `option_dlg_e6m4_14_2_001`, option index `1`
  - `option_dlg_e6m4_14_2_002`, option index `2`
- Candidate first lines:
  - `dlg_e6m4_14_020`
  - `dlg_e6m4_14_021`
- Common continuation:
  - `dlg_e6m4_14_022`

The content-based inferred route is:

| Option | Expected/inferred first line | Merge |
| --- | --- | --- |
| `option_dlg_e6m4_14_2_001` | `dlg_e6m4_14_020` | `dlg_e6m4_14_022` |
| `option_dlg_e6m4_14_2_002` | `dlg_e6m4_14_021` | `dlg_e6m4_14_022` |

The runtime-jump audit conflict is:

| Option | Expected/inferred first line | Runtime first line | Runtime first-line candidate owner |
| --- | --- | --- | --- |
| `option_dlg_e6m4_14_2_002` | `dlg_e6m4_14_021` | `dlg_e6m4_14_020` | `option_dlg_e6m4_14_2_001` |

Relevant recovered line data:

| Line | Time | Speaker | Meaning |
| --- | ---: | --- | --- |
| `dlg_e6m4_14_020` | 67.617 | Tangtang | Asks whether Endfield would help if the village is in trouble. |
| `dlg_e6m4_14_021` | 74.933 | Chen Qianyu | Asks whether Qingbo Village is already in trouble. |
| `dlg_e6m4_14_022` | 77.667 | Tangtang | Says the village is fine and the concern is everyone's future. |

The current WebUI-only override maps both options in group 2 to
`dlg_e6m4_14_020`:

```json
{
  "option_dlg_e6m4_14_2_001": ["dlg_e6m4_14_020"],
  "option_dlg_e6m4_14_2_002": ["dlg_e6m4_14_020"]
}
```

The note text for that override still describes the choices as a split, so the
documentation text is less precise than the actual override targets.

## Raw Audit Records

The conflict appears in:

- `reports/runtime_jump_option_route_audit_CN_nearby.json`
- `reports/runtime_jump_option_route_audit_CN_nearby_promoted.json`
- `reports/runtime_jump_option_route_audit_CN_story_dlg_e6m1_10_dlg_e6m4_14_nearby.json`

The general nearby reports point at a stale or alternate timeline folder:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/048B4163B7ADCBCB40EB3B754F26C8F9/MonoBehaviour/
```

Those exact files are absent in the current checkout. The story-specific
nearby report points at the current recovered folder:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/B0480FD62435984EB094C470D9CDC6A4/MonoBehaviour/
```

This is the same stale-path class seen in earlier conflict work. The current
source-graph ingestion can annotate future runtime-audit jump edges with
`assetTrackPathStatus`, but the checked-in source graph database may need a
rebuild before those path diagnostics appear in normal queries.

## Raw Timeline Evidence

Current option playable evidence links both choices to one option playable
asset:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/B0480FD62435984EB094C470D9CDC6A4/MonoBehaviour/DialogOptionPlayableAsset(Clone)(Clone)(Clone)_pB86C1A6EBD576088.json
```

Source-graph option-flow evidence assigns:

| Option | Option index | Logic id | Candidate line |
| --- | ---: | ---: | --- |
| `option_dlg_e6m4_14_2_001` | `1` | `88` | `dlg_e6m4_14_020` |
| `option_dlg_e6m4_14_2_002` | `2` | `44` | `dlg_e6m4_14_021` |

The option texts are:

- `option_dlg_e6m4_14_2_001`: "You are my chief."
- `option_dlg_e6m4_14_2_002`: "I have never chosen anyone else."

The relevant runtime jump tracks and clips are:

- `Runtime Jump Track_p9D3462F104736088.json`
  - track `OptionIndex=2`
  - clip option index `2`
  - start `65.25`
  - duration `2.11666666666666`
  - end `67.367`
  - asset `RuntimeJumpClip_p3152FD496CC06088.json`
  - payload:
    - `needChangeOptionAfterJump=0`
    - `optionIndexAfterJump=0`
    - `isReverseJump=0`
    - `isJumpFirst=0`
- `Runtime Jump Track (1)_p594C3B5C48FD6088.json`
  - track `OptionIndex=0`
  - clip option index `0`
  - start `65.75`
  - duration `1.61666666666666`
  - end `67.367`
  - asset `RuntimeJumpClip_p76D4057514F76088.json`
  - payload:
    - `needChangeOptionAfterJump=0`
    - `optionIndexAfterJump=0`
    - `isReverseJump=0`
    - `isJumpFirst=0`

Both clips end just before `dlg_e6m4_14_020` starts at `67.617`. The
option-index-2 jump is why the audit infers that option 002 reaches line 020
instead of the content-inferred line 021.

The raw `RuntimeJumpClip` payloads do not contain line ids, trunk ids, dialog
ids, or direct jump targets. The branch result is inferred from option index,
jump timing, and nearby trunk-line timing.

After rebuilding the quick source graph, runtime-audit jump edges expose the
new asset-path diagnostic fields:

- stale general-report path
  `.../048B4163B7ADCBCB40EB3B754F26C8F9/.../RuntimeJumpClip_p3152FD496CC06088.json`
  has `assetTrackPathStatus=basename_resolved`;
- story-specific path
  `.../B0480FD62435984EB094C470D9CDC6A4/.../RuntimeJumpClip_p3152FD496CC06088.json`
  has `assetTrackPathStatus=exists`.

## Interpretation

This case is not identical to either previously checked conflict:

- Like `dlg_c28m3_10`, the jump payload is targetless and
  `needChangeOptionAfterJump=0`, so the runtime evidence is weak for remapping
  without a proven runtime rule.
- Unlike `dlg_e6m1_10`, the jump clips do not set
  `needChangeOptionAfterJump=1`; there is no explicit post-jump reset-to-zero
  signal.

The best current classification is:

```text
nearbyRuntimeJumpContradictsInferredPath / doNotPromoteWithoutRuntimeRule
```

The existing WebUI override follows the runtime-audit direction, but this
evidence should remain a manual/WebUI-only decision rather than promoted
authored truth because:

- option entries do not name explicit response trunk/dialog ids;
- runtime jump clips do not name target line ids;
- both jump clips have `needChangeOptionAfterJump=0`;
- at least two audit reports still carry stale timeline folder paths.

The manual override note should eventually be tightened so it no longer says
the group "splits" when the actual override targets converge both choices to
`dlg_e6m4_14_020`.

## Recovery Boundary

This pass supports keeping the current manual override and keeping the conflict
auditable. It does not prove a general rule that option-index-gated
RuntimeJumpClips should always override line-content branch inference.

## Next Checks

- Rebuild the source graph after the runtime-audit asset path diagnostic change
  so normal graph queries expose `assetTrackPathStatus`.
- Update the `dlg_e6m4_14` group-2 override note to describe convergence rather
  than a split, if WebUI override docs are being cleaned up.
- Continue looking for runtime code that consumes `OptionIndex`,
  `needChangeOptionAfterJump`, and `optionIndexAfterJump`; that remains the
  missing proof for promoting timing-derived option routes.
