# Story Runtime Extraction Audit

This note summarizes the current runtime-side evidence for story recovery.
The useful sources are offline IL2CPP metadata, structured game tables,
mission/runtime JSON, Lua/UI scripts, and recovered AnimeStudio/Unity asset
maps. `global-metadata.dat` is a runtime vocabulary and drift source; it is not
the authored story payload.

## Current Payload Sources

High-signal structured tables under
`export_full/structured/StreamingAssets/Table/` include:

- `DialogTextTable.json`
- `DialogOptionTable.json`
- `DialogSummaryTable.json`
- `DialogSummaryMapTable.json`
- `RadioTable.json`
- `SNSDialogTable.json`
- `SNSDialogOptionTable.json`
- `EnvTalkTable.json`
- `ResponsiveDialog.json`
- `ReadingPopUpTable.json`
- `PrtsDocument.json`
- `PrtsNote.json`
- `PrtsRecord.json`

Mission and level-script JSON contain direct references to dialog, radio, SNS,
cutscene, remote comm, and related story IDs. Recovered AnimeStudio Timeline
and DialogTree JSON provides stronger line and option placement where present.

## IL2CPP Metadata Status

Main command:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
```

Current useful facts:

- Installed metadata path:
  `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`.
- Metadata version observed: `29`.
- Dialog, trunk, timeline, tree, option, cutscene, mission, scene, radio, SNS,
  env talk, LevelScript, interact, reading, PRTS, and remote comm vocabularies
  are cataloged.
- Strict specialized document/memo/letter loader canary remains `0`, supporting
  the conclusion that document-style dialog content uses the normal dialog
  stack rather than a separate loader.
- `DialogTimelineOptionData` still has exactly three serialized fields:
  `optionIndex`, `changeFinishNum`, and `targetFinishNum`.
- `DialogTreeOptionNode` exposes option display and next-index methods.
  `DialogTreeExOptionNode` has no serialized fields.

Known parser limits:

- Some generic, array, byref, pointer, and type-instance entries stay as
  `<type-index:N>` in output. This is a lightweight parser limitation, not a
  current recovery regression.
- The parser hard-fails on unsupported metadata versions instead of silently
  reading garbage.

## Option Response Status

Runtime Jump route recovery explains some option replies that used to be
inferred from adjacent Timeline lines. The graph and WebUI now distinguish raw
Timeline option clip evidence from actual route/skip evidence.

Current rule:

- Promote option response branches only when authored source evidence binds
  option indices to response lines.
- Do not promote groups that have only monotonic nearby candidate clips,
  default `optionIndex=0`, blank `trunkId`/`dialogId`, or logic-id hooks with no
  resolved target table.

Useful audits:

```bat
python tools\endfield_source_graph.py issues --code inferredOptionResponse --limit 20
python scripts\story_recovery\build_option_playable_semantics_audit.py --language CN --only-interesting
python scripts\story_recovery\build_option_runtime_field_analysis.py
python scripts\story_recovery\build_option_response_audio_evidence.py --language CN
```

Current runtime field conclusions:

- `+0x98` is the selected option index read by
  `DialogTimelineManager._SelectIndexInTimeline` and passed into
  `DialogChooseOption`.
- `+0x18` is the active clip gate checked before `SetDialogOption`; options
  with `[rax+0x18] == 0` are filtered out.
- Identifying the writer of `+0x18` is the next decoder target that would
  unblock the remaining inferred option-response groups.

## AnimeStudio Parser Notes

Native class parsing is intentionally narrow:

- `GameObject` reads components, layer, and name, then stops.
- `MonoBehaviour` reads script reference and name; game-specific fields arrive
  through TypeTree-backed output.
- `RectTransform` fields such as anchors, pivot, and size delta are available
  in Dump/TypeTree output, not native JSON class parsing.
- Extending native `GameObject` parsing past `m_Name` is risky because
  Endfield inserts an extra `UInt8 m_ArtTag` byte in the standard Unity layout.

Use TypeTree-backed Dump/JSON parsing for new game-specific loader work.

## Cutscene And FMV Evidence

`scripts/story_builder/anime_assets.py` decodes cutscene TextAsset payloads and
joins subtitle tracks through `$animestudio.pathId`. Current data has enough
patched dedup variants that unsuffixed canonical files without annotations do
not cause coverage loss.

`BeyondFMVPlayableAsset.fmvId` provides authored FMV clip timing. Current
Timeline track audit found roughly 20 distinct `cs_video_*` story keys with
clip start/duration evidence. This is suitable for a future weak FMV/cutscene
order edge in the WebUI builder.

## EnvEmoji Prefabs

`scripts/recover_envemoji_prefabs.py` merges AnimeStudio Dump and JSON exports
to recover `envEmoji_common_*` prefab layer geometry, active state, colors, and
enter animation curves.

Important current fix:

- Active state is keyed by GameObject PathID rather than `m_Name`, so duplicate
  child names inside emoji bundles no longer risk collisions.
- Regenerated output was byte-identical for the current dump, meaning the bug
  was latent in existing data.

Run:

```bat
python scripts\recover_envemoji_prefabs.py
```

## Rejected Or Diagnostic-Only Sources

- `AudioDialogCustomEventTable.json` is not a scene-ordering source. Its event
  IDs did not match other table strings, LevelScript payload bytes,
  AnimeStudio JSON, or common hashes of metadata-exposed `au_*` names. Treat it
  as a per-dialog audio profile/tag only.
- `AudioDialog` plus Timeline monotonicity is necessary but not sufficient for
  option-response promotion because it does not bind a specific response line
  to a specific option index.
- LevelScript property-flow bridges are real ordering sources, but not
  promotable until setter opcodes are decoded.

## Follow-Up Queue

1. Decode the writer of `DialogOptionPlayableAsset` active clip gate `+0x18`.
2. Identify LevelScript setter opcode/kind records for property-flow bridges.
3. Check whether `DialogOptionTable.options[*].actorId` can map per-option NPC
   response speakers for multi-speaker inferred groups.
4. Add weak FMV/cutscene order evidence from `BeyondFMVPlayableAsset.fmvId`
   clip timing.
