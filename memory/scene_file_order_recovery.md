# Scene File Order Recovery

This note records the current evidence rules for ordering story, dialog,
radio, cutscene, and mission files from original game data. Existing WebUI
order is not evidence by itself.

## Evidence Stack

Strong evidence:

1. `MissionRuntimeAsset` quest DAG edges, especially
   `questDic[*].prevQuestIdList` plus quest-local story refs such as
   `_dialogId`, `snsDialogId`, `_cutsceneId`, `_remoteCommId`, and `_radioId`.
2. DialogTree edges decoded from `dlg_*` TextAssets:
   `connections[*]._sourceNode.$ref -> connections[*]._targetNode.$ref`.
3. Timeline clip order for cinematic dialog from
   `timeline_line_orders.json` and source Timeline `MonoBehaviour` JSON.
4. Typed UID/control-flow or trigger/action relations decoded from
   LevelScript data.

Weak evidence:

- LevelScript byte-offset order inside one file.
- filename/script-id proximity.
- radio continuation or audio metadata without a quest/control-flow bridge.
- table membership, summaries, or registry presence without a chronological
  edge.

Not evidence:

- generated WebUI rank/order;
- filesystem or VFS chunk order;
- filename suffix order except as a display fallback;
- branch flattening when the quest DAG does not prove a merge or predecessor.

## Current Coverage

Recent scans found:

- `418` mission runtime assets.
- `3,736` quest nodes.
- `185` missions with story file references.
- `548` total quest-local story refs across dialog, SNS, cutscene, remote
  comm, and radio fields.
- `4,223` decoded DialogTree graphs.
- `290` recovered dialog Timeline assets covering `273` dialog keys.
- `66` option route records in the Timeline catalog.

Timeline order proves suffix order is only a fallback. For example,
`dlg_c28m3_23` has authored clip times for `_001`, `_003`, `_004`, `_005`,
and `_007`, skipping numeric suffixes.

## Current Audit Conclusions

`e0m0` is partially confirmed. The first four-entry quest sequence and the
`cutscene_e0m0_6 -> cutscene_e0m0_7 -> cutscene_e0m0_8` UID chain are strong.
Most long radio/cutscene clusters remain weak LevelScript file-offset order,
and several exported files still have no mission-order clue.

`e10m4`, `c16m4`, `c6m1`, `e1m1`, and `c28m3` remain the highest-priority
unknown-heavy missions. After fixing short-id false positives in LevelData byte
scans, recent audit status was:

| mission | strong | weak | unknown | LevelData adjacent pairs |
| --- | ---: | ---: | ---: | ---: |
| `e10m4` | 29 | 8 | 44 | 2 |
| `c16m4` | 22 | 5 | 31 | 0 |
| `c6m1` | 13 | 3 | 42 | 0 |
| `e1m1` | 17 | 12 | 19 | 0 |
| `c28m3` | 12 | 16 | 31 | 0 |

Remaining `levelscriptChain` entries are placement/ownership anchors from
script/control nodes to story keys or terminals. Do not promote them as
inter-story chronology unless a decoded trigger owner, quest edge, UID chain,
or typed setter/action relation proves the relation.

## Useful Reports

Generate a mission evidence audit:

```bat
python scripts\story_recovery\build_mission_order_evidence_audit.py --language CN --mission e0m0
```

Current report families:

- `reports/mission_order/<mission>_evidence_audit.{json,md}`
- `reports/mission_order/levelscript_property_flow_CN.{json,md}`
- `reports/mission_order/audio_dialog_custom_events_CN.{json,md}`
- `reports/playable_director/timeline_track_clips.{json,md}`

## Candidate Recovery Queue

1. Decode LevelScript setter opcodes for property-flow bridges. The current
   audit found `60` confirmed bridges between `MissionRuntimeAsset`
   `CheckLevelScriptProperty*` conditions and owning LevelScript files, but
   they are not promotable until the setter record type is identified.
2. Trace `DialogOptionPlayableAsset` runtime field `+0x18`, the active clip
   gate checked before `SetDialogOption`, to unblock source-backed option
   response mapping.
3. Map per-option NPC response speakers for the multi-speaker inferred option
   response groups, likely via `DialogOptionTable.options[*].actorId`.
4. Connect `BeyondFMVPlayableAsset.fmvId` Timeline clip evidence to the WebUI
   builder as weak FMV/cutscene ordering evidence.
5. Keep rejecting `AudioDialogCustomEventTable` as a scene-ordering source. It
   is useful only as a per-dialog audio profile/tag.

## Rules For Future Promotions

- Promote to strong only from quest DAGs, authored scene transitions,
  UID/control-flow chains, or decoded typed trigger/action relations.
- Keep weak edges visibly separate from strong edges.
- Preserve unknown entries rather than inventing total order.
- Put generated audits under `reports/`, disposable prototypes under
  `scratch/` or `tmp/`, and durable conclusions in this file.
