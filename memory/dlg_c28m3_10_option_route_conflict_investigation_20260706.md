# dlg_c28m3_10 Option Route Conflict Investigation - 2026-07-06

## Question

`dlg_c28m3_10` group 1 is one of the three runtime option-route conflicts in
the current story recovery hotlist. This pass checks whether the conflict is
strong enough to adjust WebUI branch mapping, or whether it should remain a
diagnostic warning until runtime option-index behavior is better proven.

## Graph Evidence

Command:

```bat
python tools\endfield_source_graph.py option-route-audit --story dlg_c28m3_10 --limit 20
```

The command returns one audit group:

- Scene: `dlg_c28m3_10`
- Group: `1`
- Recommendation: `nearbyRuntimeJumpContradictsInferredPath`
- Options:
  - `option_dlg_c28m3_10_1_001`: `我更想当公爵。`
  - `option_dlg_c28m3_10_1_002`: `我想当国王！`
- Candidate first lines:
  - `dlg_c28m3_10_023`
  - `dlg_c28m3_10_025`
- Common continuation:
  - `dlg_c28m3_10_021`
- Conflict count:
  - `runtimePathConflictCount=1`
  - `directionalFirstLineConflictCount=1`

The current diagnostic/inferred branch mapping is:

| Option | Inferred first line | Inferred path | Merge |
| --- | --- | --- | --- |
| `option_dlg_c28m3_10_1_001` | `dlg_c28m3_10_023` | `023`, `024` | `021` |
| `option_dlg_c28m3_10_1_002` | `dlg_c28m3_10_025` | `025`, `026` | `021` |

The runtime-jump audit contradicts the first row:

| Option | Expected/inferred first line | Runtime first line | Runtime first-line candidate owner |
| --- | --- | --- | --- |
| `option_dlg_c28m3_10_1_001` | `dlg_c28m3_10_023` | `dlg_c28m3_10_025` | `option_dlg_c28m3_10_1_002` |

Relevant line text and timing:

| Line | Time | Speaker | Text |
| --- | ---: | --- | --- |
| `dlg_c28m3_10_020` | 141.817 | 洛茜 | `哼哼，多谢国王的恩典。` |
| `dlg_c28m3_10_025` | 150.150 | “积木国王” | `我、我、我的任期还没结束呢！` |
| `dlg_c28m3_10_023` | 150.767 | 洛茜 | `那要看国王愿不愿意把宝物交给我们了。` |
| `dlg_c28m3_10_024` | 154.617 | “积木国王” | `咳咳，如果大家都同意的话……` |
| `dlg_c28m3_10_026` | 157.267 | 洛茜 | `不行，大家都要排队，不过……管理员可以排在我前面。` |
| `dlg_c28m3_10_021` | 164.967 | “积木国王” | `我宣布，今天就是积木王国新的纪念日，大家一起去玩吧！` |

## Raw Timeline Evidence

The option playable asset is:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/79C9C13CFD1A1A38E3C8279B47406BCD/MonoBehaviour/DialogOptionPlayableAsset(Clone)(Clone)_pD1464DEE6300CFA8.json
```

It contains both group-1 options:

```json
[
  {
    "_optionId": "option_dlg_c28m3_10_1_001",
    "optionIndex": 1,
    "changeFinishNum": 0,
    "targetFinishNum": -1,
    "trunkId": "",
    "dialogId": "",
    "logicId": 32635
  },
  {
    "_optionId": "option_dlg_c28m3_10_1_002",
    "optionIndex": 2,
    "changeFinishNum": 0,
    "targetFinishNum": -1,
    "trunkId": "",
    "dialogId": "",
    "logicId": 32636
  }
]
```

This proves the display options and option indices, but it does not directly
target response trunk/dialog ids.

Raw option response tracks provide stronger ownership evidence for the current
inferred paths:

- `Option 1_p08EC3B0B1879CFA8.json`
  - `optionIndex=1`
  - clips at `150.7667-154.4833` and `154.6167-159.1667`
  - via `timeline_line_orders.json`, these map to `dlg_c28m3_10_023` and
    `dlg_c28m3_10_024`
- `Option 2_pDC13CBE97717CFA8.json`
  - `optionIndex=2`
  - clips at `150.1500-154.4833` and `157.2667-164.9667`
  - via `timeline_line_orders.json`, these map to `dlg_c28m3_10_025` and
    `dlg_c28m3_10_026`

The raw option track files contain PathIDs and timing, not line ids directly.
The line-id mapping comes from the recovered timeline line-order join.

The runtime jump audit record points to `RuntimeJumpClip_p96B55F633837CFA8`.
The path embedded in the audit edge uses:

```text
.../timeline_extract/EC06385C4A4367757C11409D45CD903E/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json
```

That exact path does not exist in the current checkout. Resolving by basename
finds the file under the main `dlg_c28m3_10` timeline folder:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/79C9C13CFD1A1A38E3C8279B47406BCD/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json
```

The recovered `RuntimeJumpClip` payload contains:

```json
{
  "isReverseJump": 0,
  "needChangeOptionAfterJump": 0,
  "optionIndexAfterJump": 0,
  "crossFadeDurationAfterJump": 0.0,
  "isJumpFirst": 0
}
```

The owning runtime jump track is:

```text
Runtime Jump Track 1_p4ABBB16F4A57CFA8.json
```

It has a single relevant clip:

```text
start=162.76666666666668
duration=2.1999999999999886
optionIndex=1
assetPathId=-7587053117486149720
displayName=--------->
```

The runtime jump begins after both candidate branch bodies and ends at the
common continuation start (`164.967`). That shape is consistent with a branch
skip/merge helper, but it does not by itself prove the branch entry line.

## Interpretation

This conflict is real as an audit contradiction:

- The DialogOptionPlayableAsset maps option 001 to `optionIndex=1` and option
  002 to `optionIndex=2`.
- Raw option response tracks support the current inferred branch paths: option
  index 1 owns `023/024`, and option index 2 owns `025/026`.
- The nearby RuntimeJumpClip is gated by `optionIndex=1`, but its audit-derived
  runtime first line is `025`, which is currently owned by option 002's inferred
  path.

However, this is not yet strong enough to change WebUI branch mapping:

- The option playable has empty `trunkId` and `dialogId`, so there is no direct
  authored response target.
- The RuntimeJumpClip occurs at `162.767`, near the branch merge, not at the
  branch entry point.
- The clip has `needChangeOptionAfterJump=0` and `optionIndexAfterJump=0`, so
  it does not provide a post-jump remap target.
- The raw RuntimeJumpClip JSON does not encode a target line id; the claim that
  option 001 maps to `dlg_c28m3_10_025` is an audit inference from timing, not a
  direct target stored on the clip.
- The audit edge path for the RuntimeJumpClip is stale or rebased relative to
  the current recovered file layout; the asset is recoverable by basename, but
  path identity should be treated carefully.

The safest current conclusion is to keep
`nearbyRuntimeJumpContradictsInferredPath` as a warning and not promote an
override.

## Tooling Implications

- `option-route-audit` already surfaces the important contradiction and caveats.
- A future audit pass should record whether referenced `assetTrack` paths exist
  in the current checkout, and optionally attach a basename-resolved current
  path when the report path is stale.
- A stronger promotion rule needs either direct branch target fields or a
  proven runtime interpretation of how late branch-skip RuntimeJumpClips map
  `optionIndex` to first response lines.

## Next Checks

- Inspect the other two conflict groups, `dlg_e6m1_10` group 4 and
  `dlg_e6m4_14` group 2, for the same "late merge jump" pattern.
- Search for the writer of the active clip gate field (`+0x18`) noted in
  `memory/story_runtime_extraction_audit.md`; that remains the runtime-side key
  to proving which option clips are active.
- Consider enhancing the source graph audit ingestion to include a
  `runtime_audit_asset_path_exists` diagnostic on RuntimeJumpClip refs.
