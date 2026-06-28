# AnimeStudio DummyDll Recovery

Date: 2026-06-24

## Scope

This note records the current state of AnimeStudio DummyDll-backed
MonoBehaviour decoding work. It is an investigation memory note, not
user-facing workflow documentation.

## Generated DummyDll Root

- Canonical root for wrapper use: `D:\fluffy-dump\tools\DummyDll`
- Current contents: 165 `.dll` files, about 43.21 MiB total, last written
  2026-06-24 17:11.
- The files appear mirrored from `D:\fluffy-dump\tools\Cpp2IL-endfield-patched-dlls4`.
- Important present assemblies include `Assembly-CSharp.dll`,
  `Gameplay.Beyond.dll`, `UnityEngine.dll`, `UnityEngine.CoreModule.dll`,
  `Unity.Timeline.dll`, `AK.Wwise.Unity.API.dll`, and other Endfield/Unity
  assemblies.
- The generated set is usable enough for AnimeStudio's `AssemblyLoader` to load
  all 165 local assemblies. Focused dependency-aware tests can now resolve
  external `m_Script` PPtrs to `MonoScript` identity. The remaining blocker for
  the tested dialog timeline objects is that the concrete script type
  `Beyond.Gameplay.DialogSlateTimelineData` is not present in the current
  Cpp2IL DummyDll set, so script-derived TypeTree generation reports
  `typeDefinitionNotFound`.

## Current AnimeStudio Patch Summary

Current local AnimeStudio and wrapper changes support targeted DummyDll tests:

- `scripts/export_full_from_game.py`
  - Adds `--animestudio-dummy-dlls PATH`.
  - Falls back to `ANIMESTUDIO_DUMMY_DLLS`, then known local roots including
    `tools\DummyDll` and `tools\dummy_dlls`.
  - Records a DummyDll signature in export summaries/manifests.
  - Adds `--animestudio-mono-behaviour-type-tree-priority` with
    `serialized-first` and `script-first`, translated to AnimeStudio CLI
    values `SerializedFirst` and `ScriptFirst`.
  - Passes `--dummy_dlls` to AnimeStudio when configured.
  - Passes `--mono_behaviour_type_tree_priority` only for MonoBehaviour
    `json_by_type` runs.

- `tools\AnimeStudio\AnimeStudio.CLI`
  - Adds `MonoBehaviourTypeTreePriority` (`SerializedFirst`, `ScriptFirst`) and
    CLI option `--mono_behaviour_type_tree_priority`.
  - Loads DummyDll assemblies through `AssemblyLoader` and logs load counts.
  - Forces `MonoScript` parsing when DummyDlls or `ScriptFirst` are requested.
  - Fixes direct CLI `--map_op CABMap,Load` semantics so `Load` loads an
    existing CAB map for dependency resolution, while plain `CABMap` builds one.
  - Lets filtered block loads include CAB dependency offsets from a loaded map
    while still skipping unrelated files.
  - Lets `ScriptFirst` try a script-derived TypeTree before the serialized
    TypeTree, while `SerializedFirst` can still retry script-derived TypeTrees
    after serialized decode failure.
  - Emits partial MonoBehaviour JSON when serialized TypeTree decoding fails
    after useful fields were already read.
  - If full TypeTree decoding fails and serialized partial output did not
    identify the body type, a usable script-derived TypeTree can now seed
    partial output as `typeTreeSource: scriptDerivedPartial`. This is a narrow
    fallback path; it does not override successful serialized TypeTree output.
  - Recovers managed-reference registry headers (`rid`, class, namespace,
    assembly, raw payload offset, raw payload length) when generic TypeTree
    decoding desynchronizes at `ReferencedObjectData`.
  - Embeds `$animestudio` diagnostics in MonoBehaviour JSON, including:
    `monoBehaviourTypeTreePriority`, `scriptDerivedTypeTreeAttempted`,
    `scriptDerivedTypeTreeStatus`, `scriptDerivedScriptIdentitySource`,
    `scriptDerivedMonoScriptResolved`,
    `scriptDerivedTypeDefinitionResolved`,
    `scriptDerivedTypeTreeNodeCount`, `scriptDerivedTypeTreeUsable`, and any
    script-derived decode/type-tree errors.

- `tools\AnimeStudio\AnimeStudio.Utility`
  - `AssemblyLoader` tracks load file/success/failure counts and module count.
  - `MonoBehaviourConverter.ConvertToTypeTreeWithDiagnostics` reports whether
    script identity came from `MonoScript`, `serializedType`, or nowhere.
  - Diagnostic statuses include `monoScriptUnresolved`, `dummyDllsNotLoaded`,
    `typeDefinitionNotFound`, `typeTreeConversionFailed`, and `resolved`.

## Baseline Export Context

The latest broad story export evidence before DummyDll testing is
`reports\20260623_182105\export_full_summary.md`.

- DummyDlls were not configured in that run.
- Story `json_by_type` completed with AnimeStudio subprocess return code `0`.
- Metadata-only MonoBehaviour fallbacks remained:
  - `StreamingAssets`: 2,433
  - `Persistent`: 238
- Samples included `MonoBehaviour#22257`, `data_eny_0077_agshield`,
  `data_facemorph_avatar_antal`, `CharacterDisplayConfig`,
  `data_eny_0115_nefarcore`, and `data_eny_0086_rpsword`.
- Failure mode was mostly impossible string lengths or negative string lengths
  during serialized TypeTree decode. These are bounded fallbacks, not wrapper
  failures.

## Targeted Test Results

Scratch output root:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test
```

Filter data:

- `StreamingAssets_filter_data.json`: 40 selected MonoBehaviour targets.
- `Persistent_filter_data.json`: 40 selected MonoBehaviour targets.
- StreamingAssets filter data includes targets from
  `D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk`.

Observed output folders:

| Folder | MonoBehaviour JSON files |
| --- | ---: |
| `streaming_no_dummy` | 508,699 |
| `single_71fc_no_dummy` | 65,804 |
| `single_71fc_with_dummy` | 65,804 |
| `single_71fc_patched_serialized_first` | 65,804 |
| `single_71fc_patched_script_first` | 65,804 |
| `single_71fc_patched_script_first_v2` | 65,804 |

Takeaways:

- Simply adding `--dummy_dlls tools\DummyDll` did not increase the `71FC...`
  MonoBehaviour output count versus no DummyDll.
- Patched `SerializedFirst` and `ScriptFirst` also produced the same file
  count in the `71FC...` target.
- Many timeline-like objects already decode through the serialized TypeTree.
  For example, `01_pF13B75CC02F5BDF6.json` has
  `typeTreeSource: serializedType` and 126 TypeTree nodes in the no-DummyDll,
  serialized-first, and script-first outputs.
- `ScriptFirst` did run the new diagnostic path, but spot checks show it fell
  back to serialized TypeTrees because the script-derived TypeTree was not
  usable.

## New Diagnostic Finding

The most important new signal is `monoScriptUnresolved`.

Example from
`tools\animestudio-dummydll-gain-test\single_71fc_patched_script_first_v2\MonoBehaviour\ActivationPlayableAsset(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)(Clone)_p71F6D07CBCFE879A.json`:

```json
"scriptFileId": 1,
"scriptPathId": 8570797628226573982,
"monoBehaviourTypeTreePriority": "ScriptFirst",
"scriptDerivedTypeTreeAttempted": true,
"scriptDerivedTypeTreeStatus": "monoScriptUnresolved",
"scriptDerivedScriptIdentitySource": "",
"scriptDerivedMonoScriptResolved": false,
"scriptDerivedTypeDefinitionResolved": false,
"scriptDerivedTypeTreeNodeCount": 12,
"scriptDerivedTypeTreeUsable": false
```

Interpretation:

- The MonoBehaviour has an `m_Script` pointer (`fileId=1`, nonzero `pathId`),
  but AnimeStudio cannot currently resolve that PPtr to a `MonoScript`.
- The serialized type also did not provide enough script identity for this
  object, otherwise `scriptDerivedScriptIdentitySource` would be
  `serializedType`.
- Because no script full name and assembly name are available, DummyDll type
  lookup is never reached. The current blocker is not obviously "DummyDll lacks
  type"; it is "AnimeStudio cannot resolve MonoScript identity for these
  MonoBehaviour objects."
- The base MonoBehaviour TypeTree has 12 nodes, so
  `scriptDerivedTypeTreeUsable: false` means no script fields were added.

## Focused Dependency-Aware Result

Follow-up targeted two-object tests used:

- Target file:
  `D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk`
- Target offsets:
  - `dlg_npc_0005_1_timeline`: `65289186`, CAB
    `CAB-b731a32d82e7752f0b6cadc44b47a998`
  - `dlg_chen_1_timeline`: `65463629`, CAB
    `CAB-37add11c1729dfad2222ebc35cb8abbc`
- Shared external script CAB:
  `CAB-5f527d7b7706baccdad9f794cf46420c`
- Current installed-game location for that dependency:
  `VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk`, offset `9841589`

The dependency-aware script-first run:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\target_timelines_minimap_current_script_first_refs" --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --mono_behaviour_type_tree_priority ScriptFirst --filter_data "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\target_timelines_filter_data.json" --map_op "CABMap,Load" --map_name endfield_target_timeline_deps_current
```

Important output:

- DummyDll load: `165/165` assemblies, `0` failed.
- Exactly two MonoBehaviour JSON files exported.
- Both objects now resolve `m_Script`:
  - `scriptClassName`: `DialogSlateTimelineData`
  - `scriptFullName`: `Beyond.Gameplay.DialogSlateTimelineData`
  - `scriptAssemblyName`: `Gameplay.Beyond.dll`
  - `scriptDerivedMonoScriptResolved`: `true`
- Script-derived TypeTree status is still `typeDefinitionNotFound` because that
  concrete type is not present as a usable Mono.Cecil `TypeDefinition` in
  `tools\DummyDll\Gameplay.Beyond.dll`.
- Serialized TypeTree decoding still fails at `ManagedReferencesRegistry`, but
  the patched exporter keeps partial content and recovered reference headers:
  - no-DummyDll partial output after decoded main-flow links and named action
    strings: about 55-59 KiB per file.
  - DummyDll + dependency output after decoded main-flow links and named action
    strings: about 56-60 KiB per file.
  - prior metadata-only output: about 5 KiB per file
  - recovered `actionsData` includes `slate_chen_1`, duration `56.699997`,
    and eight `mainFlowDatas` `rid` references.
  - recovered `$animestudio.recoveredManagedReferences.RefIds` has `66` entries
    per object, mapping each `rid` to managed types such as
    `Beyond.Gameplay.DialogMainFlowData`,
    `Beyond.Gameplay.DialogMFTrunkActionData`,
    `Beyond.Gameplay.DialogCamActData`,
    `Beyond.Gameplay.DialogAnimActData`, and
    `Beyond.Gameplay.DialogEmotionActData`, plus raw payload offset/length and
    validated inferred payload data when a narrow decoder matches.
  - `Beyond.Gameplay.DialogMainFlowData` payloads now decode when they exactly
    match `int64 leadRid`, `int32 linkedRidCount`,
    `int64[linkedRidCount] linkedRids`; the decoder requires
    `12 + linkedRidCount * 8 == dataLength` and every referenced `rid` to exist
    in the recovered table. The exported layout is
    `DialogMainFlowDataRidArray` with `leadRid` and `linkedRids`.
  - Common string-bearing dialog action payloads now partial-decode into named
    inferred fields when their expected offsets validate:
    - `DialogMFTrunkActionDataLineId`: `lineId` at relative offset `32`,
      currently `dlg_chen_1_001` through `dlg_chen_1_008`.
    - `DialogAnimActDataAnimationPath`: `animationPath` at relative offset
      `68`, including paths such as `Montage/NPC/chen/talk_006` and
      `Montage/NPC/endminf/talk_003`.
    - `DialogEmotionActDataFacialMorphPath`: `facialMorphPath` at relative
      offset `44`, including `FacialMorph/Emotion/smile01` and
      `FacialMorph/Emotion/sad01`.
    - `DialogEmotionPoseActDataControlNames`: `poseControlNames`, including
      controls such as `brow_happy_a_R_ctrl`.
    - `DialogTeleportEntityActionDataTransformLike`: inferred `entityIndex`,
      `positionLike`, and `rotationLike` fields for length-60 payloads with
      action code `107`, fixed zero fields, and bounded finite float triples.
    - `DialogSetDisableClickActionDataEmptyTail` and
      `DialogMFTransitionActionDataEmptyTail`: fixed length-28 action payloads
      where the first 12 bytes validate as the shared timing/action prefix and
      the remaining bytes are zero-filled.
    - `DialogMuteAutoBlinkActDataFlagLike` and
      `DialogShowOrHideSingleActorActionDataActorIndexLike`: small fixed
      payloads where raw-sidecar inspection validated a bounded flag-like or
      actor-index-like field plus fixed zero regions.
  - Dialog action payloads now include a conservative
    `inferredActionTimingPrefix` when the first 12 bytes validate as
    `float32 value0Seconds`, `float32 value1Seconds`, and `int32 actionCode`.
    These names are intentionally generic because current evidence does not
    prove more specific semantics such as start time or duration.
  - decoded `DialogMainFlowData` recovers the internal graph from each
    main-flow entry to its child action entries. In the focused samples, both
    no-DummyDll and DummyDll + dependency runs decode 8 main-flow records per
    file, with 8 `leadRid` values and 50 `linkedRids` values. The first
    main-flow entry links to action types such as `DialogMFTrunkActionData`,
    `DialogSetDisableClickActionData`, `DialogCamActData`,
    `DialogAnimActData`, and `DialogEmotionActData`.
  - latest measured coverage:
    - no DummyDll: `dlg_chen_1_timeline` has 66 refs, 8 decoded main-flow
      entries / 50 linked rids, 58 action timing prefixes, 8 line ids,
      10 animation paths, 10 facial morph paths, 2 inferred teleport
      transform-like payloads, and 11 pose control names;
      `dlg_npc_0005_1_timeline` has 66 refs, 8 decoded main-flow entries /
      50 linked rids, 58 action timing prefixes, 8 line ids, 0 animation paths,
      10 facial morph paths, 2 inferred teleport transform-like payloads, and
      11 pose control names.
    - DummyDll + dependency: same payload decode coverage, plus resolved script
      identity.

The measured gain is therefore layered:

1. Partial TypeTree recovery improves decoded content even without DummyDlls.
2. Narrow action decoders name line ids, animation paths, facial morph paths,
   pose control names, inferred teleport transform-like fields, empty-tail
   actions, and two small fixed action payloads from otherwise mostly unparsed
   payload bodies.
3. The narrow `DialogMainFlowData` decoder recovers the graph from decoded
   main-flow entries to runtime action entries.
4. The shared `inferredActionTimingPrefix` exposes the repeatable first-12-byte
   prefix for dialog action payloads without overclaiming class-specific scalar
   semantics.
5. DummyDlls plus CAB dependency loading add resolved script identity and prove
   whether script-derived TypeTree generation is possible for the object.

## Wider 11-Timeline Validation

A later pass rebuilt a current full StreamingAssets CAB map from the installed
game root instead of trusting the stale scratch/probe maps:

```bat
cd /d D:\fluffy-dump\tools\animestudio-dummydll-gain-test
.\..\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\cabmap_full_streaming_output" --game ArknightsEndfield --logger_flags Info Warning Error --map_op CABMap --map_name endfield_streamingassets_full_current
```

The resulting map is:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\Maps\endfield_streamingassets_full_current.bin
```

It was built from 794 input files, produced 258,423 CAB entries, and is about
42.1 MiB. The full build took about 4.3 minutes on the current machine.

Using that map, `dialog_timelines_11_filter_data.json` was generated for 11
known `dlg_*_timeline` MonoBehaviours:

- `dlg_chen_1_timeline`
- `dlg_npc_0005_1_timeline`
- `dlg_e1m1_1_timeline`
- `dlg_e2m2_1_timeline`
- `dlg_e2m2_3d5_timeline`
- `dlg_e2m4_11_timeline`
- `dlg_e2m4_7_timeline`
- `dlg_e2m5_2_timeline`
- `dlg_e2m5_4_timeline`
- `dlg_e3m1_1_timeline`
- `dlg_sm1l1m7_1_timeline`

Broad script-first output with DummyDlls and the full dependency map lives at:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_prefix
```

A clean no-DummyDll control with exact `--names` filtering lives at:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_prefix_exact
```

Important workflow lesson: the script-first dependency-map run exported 68,263
MonoBehaviour JSON files because dependency offsets from the loaded CAB map
expanded the loaded asset set. For future broad validations, pass both
`--filter_data` and an exact `--names` regex when the goal is a fixed target
set.

After broadening only validated string-action layouts and adding an inferred
Teleport payload decoder, final exact verification output lives at:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_final_v2
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_final_v2
```

Measured decoded payload coverage is identical between the no-DummyDll control
and the DummyDll + dependency-map run. Across the 11 target timelines:

| Metric | Count |
| --- | ---: |
| recovered managed references | 613 |
| decoded `DialogMainFlowData` entries | 85 |
| decoded action timing prefixes | 528 |
| decoded main-flow linked action rids | 443 |
| decoded line ids | 77 |
| decoded animation paths | 62 |
| decoded facial morph paths | 35 |
| decoded pose control-name payloads | 2 |
| individual pose control names inside those payloads | 22 |
| decoded `DialogTeleportEntityActionData` transform-like payloads | 83 |
| remaining heuristic string hints | 3 |
| remaining unparsed managed-reference payloads | 269 |

Per-target coverage:

| Timeline | Refs | Main flow | Linked rids | Prefixes | Lines | Anim paths | Morph paths | Teleports | Pose payloads | Unparsed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dlg_chen_1_timeline` | 66 | 8 | 50 | 58 | 8 | 10 | 10 | 2 | 1 | 27 |
| `dlg_npc_0005_1_timeline` | 66 | 8 | 50 | 58 | 8 | 0 | 10 | 2 | 1 | 37 |
| `dlg_e1m1_1_timeline` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `dlg_e2m2_1_timeline` | 197 | 16 | 165 | 181 | 15 | 24 | 15 | 23 | 0 | 104 |
| `dlg_e2m2_3d5_timeline` | 70 | 12 | 46 | 58 | 10 | 18 | 0 | 11 | 0 | 19 |
| `dlg_e2m4_11_timeline` | 17 | 2 | 13 | 15 | 1 | 0 | 0 | 9 | 0 | 5 |
| `dlg_e2m4_7_timeline` | 45 | 9 | 27 | 36 | 6 | 3 | 0 | 8 | 0 | 19 |
| `dlg_e2m5_2_timeline` | 28 | 5 | 18 | 23 | 4 | 1 | 0 | 10 | 0 | 8 |
| `dlg_e2m5_4_timeline` | 53 | 12 | 29 | 41 | 12 | 4 | 0 | 6 | 0 | 19 |
| `dlg_e3m1_1_timeline` | 64 | 12 | 40 | 52 | 12 | 2 | 0 | 11 | 0 | 27 |
| `dlg_sm1l1m7_1_timeline` | 7 | 1 | 5 | 6 | 1 | 0 | 0 | 1 | 0 | 4 |

For all 11 DummyDll script-first target outputs, `m_Script` resolved to
`Beyond.Gameplay.DialogSlateTimelineData`, but
`scriptDerivedTypeTreeStatus` remained `typeDefinitionNotFound`. The current
DummyDll set therefore helps prove script identity for these objects, but it
does not improve the decoded dialog payload fields beyond the partial
serialized-TypeTree and managed-reference payload recovery patch.

A follow-up probe after adding the `scriptDerivedPartial` fallback wrote:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_scriptpartial_probe
```

The decoded payload coverage stayed identical to `final_v2`:

```text
recovered refs: 613
decoded main-flow entries: 85
decoded main-flow linked rids: 443
decoded action timing prefixes: 528
decoded line ids: 77
decoded animation paths: 62
decoded facial morph paths: 35
decoded pose payloads: 2
decoded pose control names: 22
decoded teleport transform-like payloads: 83
remaining unparsed payloads: 269
```

All 11 outputs reported `scriptDerivedTypeTreeStatus:
typeDefinitionNotFound`, `scriptDerivedMonoScriptResolved: true`, and
`typeTreeSource: serializedType`. That is the desired behavior for this
target family: the new script-derived partial fallback is available for future
objects with usable DummyDll schema, but it did not degrade or replace the
better serialized partial recovery for dialog timelines.

A later small-action pass wrote:

```text
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_emptytail_v3
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_raw_probe
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_smallfixed_v4
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_smallfixed_v4
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_motionfx_v5b
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_motionfx_v5b
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_morefx_v7
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_morefx_v7
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_no_dummy_decoded_camact_v8
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_script_first_decoded_camact_v8
```

`emptytail_v3` promoted 32 fixed length-28 payloads:

- 24 `DialogSetDisableClickActionDataEmptyTail`
- 8 `DialogMFTransitionActionDataEmptyTail`

Raw-sidecar inspection in `raw_probe` then confirmed two more small fixed
layouts:

- 4 `DialogMuteAutoBlinkActDataFlagLike` payloads, length `44`, action code
  `304`, zero-filled regions at relative `12..31` and `36..43`, and a bounded
  flag-like int at relative `32`.
- 3 `DialogShowOrHideSingleActorActionDataActorIndexLike` payloads, length
  `36`, action code `301`, zero-filled regions at relative `12..27` and `32`,
  and a bounded actor-index-like int at relative `28`.

The following motion/camera-effect scalar pass promoted three more narrowly
validated payload families:

- 17 `DialogMoveToActDataTransformLike` payloads, length `128`, action code
  `105`, fixed zero regions, a bounded target-index-like int, finite
  position/rotation-like float triples, and fixed trailing constants.
- 14 `DialogCamDOFActionDataScalarBlock` payloads, length `96`, action code
  `115`, fixed zero/constant regions, and seven finite scalar parameters.
  These all come from `dlg_e2m2_1_timeline`, so the exported field names stay
  generic.
- 5 `DialogMaskActionDataParameterBlock` payloads, length `96`, action code
  `116`, fixed zero/constant regions, two bounded int slots, and a blend-like
  float in `[0, 1]`.

`motionfx_v5b` no-DummyDll and DummyDll script-first exact outputs have
identical decoded payload coverage across the 11 target timelines:

| Metric | Count |
| --- | ---: |
| recovered managed references | 613 |
| decoded `DialogMainFlowData` entries | 85 |
| decoded main-flow linked action rids | 443 |
| decoded action timing prefixes | 528 |
| decoded line ids | 77 |
| decoded animation paths | 62 |
| decoded facial morph paths | 35 |
| decoded pose control-name payloads | 2 |
| individual pose control names inside those payloads | 22 |
| decoded `DialogTeleportEntityActionData` transform-like payloads | 83 |
| decoded empty-tail action payloads | 32 |
| decoded small fixed action payloads | 7 |
| decoded `DialogMoveToActData` transform-like payloads | 17 |
| decoded `DialogCamDOFActionData` scalar-block payloads | 14 |
| decoded `DialogMaskActionData` parameter-block payloads | 5 |
| remaining heuristic string hints | 3 |
| remaining unparsed managed-reference payloads | 194 |

All 11 DummyDll script-first `motionfx_v5b` outputs still report
`typeDefinitionNotFound`, `scriptDerivedMonoScriptResolved: true`, and
`typeTreeSource: serializedType`, so these added fields are serialized partial
payload gains rather than DummyDll schema gains.

The remaining `motionfx_v5b` unparsed groups are:

| Count | Class / length / action code |
| ---: | --- |
| 109 | `DialogCamActData`, 476, 51 |
| 61 | `DialogLookAtActData`, 144, 52 |
| 10 | `DialogAnimActData`, 240, 54 |
| 4 | `DialogCamPPActionData`, 232, 118 |
| 3 | `DialogCamActData`, 560, 51 |
| 2 | `DialogTurnToActData`, 96, 53 |
| 1 | `DialogEmotionActData`, 220, 122 |
| 1 | `DialogSummaryActData`, 52, 127 |
| 1 | `DialogCamActData`, 588, 51 |
| 1 | `DialogMorphAnimActData`, 132, 306 |
| 1 | `DialogCamActData`, 644, 51 |

A subagent review plus raw-sidecar checks then promoted five more strict
layouts:

- 1 `DialogSummaryActDataSummaryId` payload, length `52`, action code `127`,
  zero fixed region, and a `summary_` string at relative offset `28`.
- 1 `DialogMorphAnimActDataPaths` payload, length `132`, action code `306`,
  fixed zero/constant regions, a `FacialMorph/MorphAnim/` path at relative
  offset `40`, and a second morph-state string at relative offset `88`.
- 61 `DialogLookAtActDataScalarBlock` payloads, length `144`, action code
  `52`, across 7 timelines. Exported fields stay generic:
  `selectorFieldsLike`, `vectorALike`, `vectorBLike`, and
  `parameterValuesLike`.
- 2 `DialogTurnToActDataAngleBlock` payloads, length `96`, action code `53`,
  across 2 timelines. The sample count is small, but the class/length/action,
  zero-region, marker, and angle gates are tight.
- 4 `DialogCamPPActionDataScalarBlock` payloads, length `232`, action code
  `118`, across 2 timelines, with repeated `2,2,4` marker groups and fixed
  post-process constants.

Latest `morefx_v7` no-DummyDll and DummyDll script-first exact outputs have
identical decoded payload coverage across the 11 target timelines:

| Metric | Count |
| --- | ---: |
| recovered managed references | 613 |
| decoded `DialogMainFlowData` entries | 85 |
| decoded main-flow linked action rids | 443 |
| decoded action timing prefixes | 528 |
| decoded line ids | 77 |
| decoded animation paths | 62 |
| decoded facial morph paths | 35 |
| decoded pose control-name payloads | 2 |
| individual pose control names inside those payloads | 22 |
| decoded `DialogTeleportEntityActionData` transform-like payloads | 83 |
| decoded empty-tail action payloads | 32 |
| decoded small fixed action payloads | 7 |
| decoded `DialogMoveToActData` transform-like payloads | 17 |
| decoded `DialogCamDOFActionData` scalar-block payloads | 14 |
| decoded `DialogMaskActionData` parameter-block payloads | 5 |
| decoded `DialogSummaryActData` summary ids | 1 |
| decoded `DialogMorphAnimActData` path payloads | 1 |
| decoded `DialogLookAtActData` scalar blocks | 61 |
| decoded `DialogTurnToActData` angle blocks | 2 |
| decoded `DialogCamPPActionData` scalar blocks | 4 |
| remaining heuristic string hints | 0 |
| remaining unparsed managed-reference payloads | 125 |

All 11 DummyDll script-first `morefx_v7` outputs still report
`typeDefinitionNotFound`, `scriptDerivedMonoScriptResolved: true`, and
`typeTreeSource: serializedType`, so these added fields are still serialized
partial payload gains rather than DummyDll schema gains.

The remaining `morefx_v7` unparsed groups are:

| Count | Class / length / action code |
| ---: | --- |
| 109 | `DialogCamActData`, 476, 51 |
| 10 | `DialogAnimActData`, 240, 54 |
| 3 | `DialogCamActData`, 560, 51 |
| 1 | `DialogEmotionActData`, 220, 122 |
| 1 | `DialogCamActData`, 588, 51 |
| 1 | `DialogCamActData`, 644, 51 |

A final CamAct-focused subagent review promoted only the common 476-byte
camera-action family and explicitly held the longer variants:

- 109 `DialogCamActDataScalarBlock` payloads, length `476`, action code `51`,
  across 10 timelines. Exported fields stay generic: `selectorFieldsLike` and
  `parameterValuesLike`.
- The 560/588/644-byte `DialogCamActData` variants also use action code `51`,
  but they are not clean `476 + tail` extensions; marker blocks shift and
  additional float blocks appear. The 560-byte group has only 3 samples, while
  the 588/644-byte groups are singletons, so they remain held.

Latest `camact_v8` no-DummyDll and DummyDll script-first exact outputs have
identical decoded payload coverage across the 11 target timelines:

| Metric | Count |
| --- | ---: |
| recovered managed references | 613 |
| decoded `DialogMainFlowData` entries | 85 |
| decoded main-flow linked action rids | 443 |
| decoded action timing prefixes | 528 |
| decoded line ids | 77 |
| decoded animation paths | 62 |
| decoded facial morph paths | 35 |
| decoded pose control-name payloads | 2 |
| individual pose control names inside those payloads | 22 |
| decoded `DialogTeleportEntityActionData` transform-like payloads | 83 |
| decoded empty-tail action payloads | 32 |
| decoded small fixed action payloads | 7 |
| decoded `DialogMoveToActData` transform-like payloads | 17 |
| decoded `DialogCamDOFActionData` scalar-block payloads | 14 |
| decoded `DialogMaskActionData` parameter-block payloads | 5 |
| decoded `DialogSummaryActData` summary ids | 1 |
| decoded `DialogMorphAnimActData` path payloads | 1 |
| decoded `DialogLookAtActData` scalar blocks | 61 |
| decoded `DialogTurnToActData` angle blocks | 2 |
| decoded `DialogCamPPActionData` scalar blocks | 4 |
| decoded `DialogCamActData` scalar blocks | 109 |
| remaining heuristic string hints | 0 |
| remaining unparsed managed-reference payloads | 16 |

All 11 DummyDll script-first `camact_v8` outputs still report
`typeDefinitionNotFound`, `scriptDerivedMonoScriptResolved: true`, and
`typeTreeSource: serializedType`, so the latest fields are still serialized
partial payload gains rather than DummyDll schema gains.

The remaining `camact_v8` unparsed groups are:

| Count | Class / length / action code | Current recommendation |
| ---: | --- | --- |
| 10 | `DialogAnimActData`, 240, 54 | Hold: all from `dlg_npc_0005_1_timeline`; aligned string scan found no non-empty strings, and the longer `animationPath` offset does not apply. |
| 3 | `DialogCamActData`, 560, 51 | Hold: small sample and not a clean extension of the 476-byte CamAct layout. |
| 1 | `DialogEmotionActData`, 220, 122 | Hold: singleton; aligned string scan found no non-empty strings. |
| 1 | `DialogCamActData`, 588, 51 | Hold: singleton longer CamAct variant. |
| 1 | `DialogCamActData`, 644, 51 | Hold: singleton longer CamAct variant. |

## Candidate Follow-Up From Subagent Review

A read-only explorer checked current exported JSON for other MonoBehaviours
where DummyDll-backed script-derived TypeTrees might matter. Promising names
were:

- `BB_eny_0081_ruanyi` and `BB_eny_0077_agshield`, both resolving through
  `m_Script` to `Beyond.Gameplay.AI.Config.EnemyAIBlackboard`.
- `BB_npc_coilbst_base`, resolving to
  `Beyond.Gameplay.AI.Config.NpcAIBlackboard`.
- `data_facemorph_avatar_mifu`, resolving to
  `Beyond.Gameplay.Core.SkeletalMorphAvatarDataSO`.
- weaker: `data_eny_0081_ruanyi` and `data_eny_0077_agshield`, resolving to
  `Beyond.Gameplay.TemplateDataConfig` rather than the expected enemy config
  type.

A Mono.Cecil check against the current local
`tools\DummyDll\Gameplay.Beyond.dll` found:

| Type | Present | Declared fields |
| --- | ---: | ---: |
| `Beyond.Gameplay.AI.Config.EnemyAIBlackboard` | no | n/a |
| `Beyond.Gameplay.AI.Config.NpcAIBlackboard` | yes | 0 |
| `Beyond.Gameplay.Core.SkeletalMorphAvatarDataSO` | no | n/a |
| `Beyond.Gameplay.TemplateDataConfig` | no | n/a |
| `Beyond.Gameplay.DialogSlateTimelineData` | no | n/a |

`NpcAIBlackboard` also has no resolved base type in the stub. A focused
`BB_npc_coilbst_base` probe used:

```text
D:\fluffy-dump\tmp\animestudio_npc_blackboard_filter.json
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\npc_blackboard_no_dummy_probe
D:\fluffy-dump\tools\animestudio-dummydll-gain-test\npc_blackboard_script_first_probe
```

Both runs partially decoded the same serialized fields:

```text
m_GameObject, m_Enabled, m_Script, m_Name, baseCfg, desc, parent, canvasBB,
mode, graph, behavior
```

The no-DummyDll control wrote a 9,199-byte JSON file with
`typeTreeSource: serializedType`. The DummyDll script-first run wrote a
9,812-byte JSON file with `typeTreeSource: serializedType`,
`scriptDerivedTypeTreeStatus: resolved`, `scriptDerivedMonoScriptResolved:
true`, `scriptDerivedTypeDefinitionResolved: true`, and
`scriptDerivedTypeTreeNodeCount: 12`. Because the script-derived tree contains
only the base MonoBehaviour nodes, the useful body-field recovery still comes
from the serialized partial decode, not from DummyDll schema.

The immediate conclusion is that the current DummyDll set can prove script
identity and type lookup for some blackboard assets, but it still lacks useful
field metadata for the best available candidates. Improving the DummyDll
generation path remains the highest-leverage route for true script-derived body
schema gains.

## Review Hardening Follow-Up

Subagent review flagged the main safety risks in the heuristic
ManagedReferencesRegistry recovery before it should be trusted outside the
focused two-object test:

- duplicate recovered `rid` values could have hidden a false header candidate;
- next-header detection could have latched onto payload bytes that only looked
  like a managed-reference header;
- expected `rid` collection was initially too broad and could fail recovery on
  unrelated fields named `rid`;
- CLR/Cecil type-name validation was too narrow for nested, generic, or array
  type forms;
- heuristic string hints needed explicit caps and naming so they did not look
  like authoritative typed payload decoding.

The current local patch mitigates those points by rejecting duplicate recovered
`rid`s, preferring expected-rid-aware next headers, checking that candidate
segmentation can parse the remaining headers, collecting expected managed
reference rids only from one-key `{ "rid": ... }` wrapper dictionaries,
loosening managed type-name validation for common CLR/Cecil forms, emitting
payload strings and generic `rid` links as `heuristicStringHints` and
`heuristicRidLinks` with per-reference and per-object limits, and only decoding
`DialogMainFlowData`, validated string-bearing dialog actions,
`DialogTeleportEntityActionData` transform-like payloads, small fixed/empty-tail
payloads, motion/camera/post-process scalar blocks, distinctive string payloads,
or the shared dialog action timing prefix when the inferred layout validates.
Later review also hardened exhausted TypeTree reads so they throw instead of
fabricating a zero, broadened heuristic string decoding from printable ASCII to
strict UTF-8 with control-character rejection, and made DummyDll type lookup
fall back across loaded modules only when the requested full type name is
unique. Header segmentation is still heuristic and greedy, so broad-run results
should keep that caveat.

## Next Hypotheses

1. Test more MonoBehaviours whose resolved `MonoScript` types are present in
   the DummyDll set. Those are the best candidates for actual script-derived
   TypeTree body decoding.
2. For dialog timeline objects, inspect the remaining non-string action
   payloads for stable scalar layouts before promoting class-specific fields.
   the remaining unknowns are now only `DialogAnimActData` length `240`,
   longer `DialogCamActData` variants, and one short `DialogEmotionActData`.
   `DialogAnimActData` length `240` has no aligned non-empty strings in the
   current sample, so do not broaden the longer animation-path decoder into it.
   Only promote fields that validate across multiple independent samples or
   against type/source evidence.
3. Revisit the DummyDll generation path: the current Cpp2IL output includes
   many `Gameplay.Beyond.dll` types but not
   `Beyond.Gameplay.DialogSlateTimelineData` or the tested dialog managed
   reference classes as usable Mono.Cecil `TypeDefinition`s. A different
   dumper/version or improved metadata recovery may emit those types.
4. Keep script-first as an experiment flag rather than the default. The default
   `SerializedFirst` remains safer because embedded serialized TypeTrees often
   contain more useful Endfield-specific field layout than incomplete DummyDll
   stubs.

## Scalar Payload Inspection

After adding the `DialogMainFlowData` and string-action decoders, the remaining
dialog action payloads were inspected for scalar layouts across the 11-target
filter. A shared first-12-byte prefix was promoted as
`inferredActionTimingPrefix` with generic fields `value0Seconds`,
`value1Seconds`, and `actionCode`; in the final 11-target samples it appears on
528 dialog action payloads.

Promoted after review:

- `DialogTeleportEntityActionData`: 83 payloads across 10 timelines, always
  length `60`, action code `107`, fixed zero fields at relative offsets
  `12`, `16`, `20`, `24`, and `56`, a small non-negative integer at `28`, and
  bounded finite float triples at `32..40` and `44..52`. Exported as inferred
  `entityIndex`, `positionLike`, and `rotationLike`.
- `DialogSetDisableClickActionData` and `DialogMFTransitionActionData`: 32
  fixed length-28 payloads total where the first 12 bytes validate as timing
  prefix plus action code (`124` or `308`) and the remaining 16 bytes are zero.
  Exported as empty-tail inferred payloads.
- `DialogMuteAutoBlinkActData`: 4 length-44 payloads with action code `304`,
  fixed zero regions, and a bounded int at relative offset `32`. Exported as
  inferred `muteFlagLike`.
- `DialogShowOrHideSingleActorActionData`: 3 length-36 payloads with action
  code `301`, fixed zero regions, and a bounded int at relative offset `28`.
  Exported as inferred `actorIndexLike`.
- `DialogMoveToActData`: 17 payloads across 4 timelines, length `128`, action
  code `105`, fixed zero/constant regions, a bounded int at relative offset
  `28`, and finite float triples at `76..84` and `88..96`. Exported as
  inferred `targetIndexLike`, `positionLike`, and `rotationLike`.
- `DialogCamDOFActionData`: 14 payloads from `dlg_e2m2_1_timeline`, length
  `96`, action code `115`, fixed zero/constant regions, and finite scalar
  values at `68..92`. Exported as generic `parameterValuesLike`; keep the
  single-timeline caveat when broadening this family.
- `DialogMaskActionData`: 5 payloads across 3 timelines, length `96`, action
  code `116`, fixed zero/constant regions, bounded ints at `28` and `32`, and
  a `[0, 1]` float at `40`. Exported as inferred `modeLike`, `targetLike`, and
  `blendValueLike`.
- `DialogSummaryActData`: 1 payload, length `52`, action code `127`, with a
  `summary_` string at relative offset `28`. Exported as inferred `summaryId`.
- `DialogMorphAnimActData`: 1 payload, length `132`, action code `306`, with a
  `FacialMorph/MorphAnim/` path at relative offset `40` and a morph-state
  string at relative offset `88`. Exported as inferred `morphAnimPath` and
  `morphStateName`.
- `DialogLookAtActData`: 61 payloads across 7 timelines, length `144`, action
  code `52`, fixed zero/marker regions, bounded selector-like ints, and finite
  scalar/vector-like float slots. Exported as generic `selectorFieldsLike`,
  `vectorALike`, `vectorBLike`, and `parameterValuesLike`.
- `DialogTurnToActData`: 2 payloads across 2 timelines, length `96`, action
  code `53`, fixed zero/marker regions, bounded selector-like ints, and a
  bounded `angleLike` float.
- `DialogCamPPActionData`: 4 payloads across 2 timelines, length `232`, action
  code `118`, repeated camera post-process marker groups, fixed constants, and
  finite scalar parameters. Exported as generic `parameterValuesLike`.
- `DialogCamActData`: 109 payloads across 10 timelines, length `476`, action
  code `51`, fixed zero/marker regions, bounded selector-like ints, and finite
  scalar float slots. Exported as generic `selectorFieldsLike` and
  `parameterValuesLike`.

Kept as future work:

- `DialogCamActData`: 5 remaining payloads across 3 timelines, but only in
  longer lengths (`560`, `588`, `644`) that are not clean extensions of the
  promoted 476-byte layout.
- `DialogAnimActData` length `240`: 10 payloads with action code `54`, but the
  validated `animationPath` offset used for longer `DialogAnimActData` payloads
  does not contain a string here.
- `DialogEmotionActData` length `220`: single payload with action code `122`;
  no non-empty strings in the current sample.

## Commands To Try Next

Rebuild after any AnimeStudio source changes:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Run the current exact 11-timeline script-first test against the full StreamingAssets
CAB map:

```bat
cd /d D:\fluffy-dump\tools\animestudio-dummydll-gain-test
.\..\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\next_dialog_timelines_11_script_first" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --mono_behaviour_type_tree_priority ScriptFirst --filter_data "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_filter_data.json" --names "^dlg_(chen_1|npc_0005_1|e1m1_1|e2m2_1|e2m2_3d5|e2m4_11|e2m4_7|e2m5_2|e2m5_4|e3m1_1|sm1l1m7_1)_timeline$" --map_op "CABMap,Load" --map_name endfield_streamingassets_full_current
```

Rebuild the current full StreamingAssets CAB map before trusting old map
entries:

```bat
cd /d D:\fluffy-dump\tools\animestudio-dummydll-gain-test
.\..\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\cabmap_full_streaming_output" --game ArknightsEndfield --logger_flags Info Warning Error --map_op CABMap --map_name endfield_streamingassets_full_current
```

The current direct CLI map convention reads and writes `Maps\*.bin` relative to
the process working directory, so run map build/load probes from the same
scratch directory.

Useful follow-up diagnostics:

- Compare no-DummyDll and DummyDll+dependency outputs for the same filter. The
  partial `actionsData` and `$animestudio.recoveredManagedReferences.RefIds`
  recovery should appear in both; script identity fields should appear only
  when the external `MonoScript` resolves.
- Search `tools\DummyDll\*.dll` with Mono.Cecil for resolved
  `scriptFullName` values before expecting script-derived body decoding.
- Use the recovered managed-reference `dataOffset`/`dataLength` spans to inspect
  still-unparsed action classes such as `DialogCamActData` before adding any
  more inferred decoders.

Wrapper-level broad refresh only after focused tests show the target class
family benefits:

```bat
.\export.bat --export-from-game --animestudio-jobs 1 --animestudio-dummy-dlls "D:\fluffy-dump\tools\DummyDll" --animestudio-mono-behaviour-type-tree-priority script-first --animestudio-refresh-types StreamingAssets:json_by_type:MonoBehaviour
```

Keep this broad command last: it is expensive, and script-first is still most
valuable for classes that exist in the current DummyDll set.

## 2026-06-28 Short DialogAnimActData Scalar Recovery

A fresh current 11-dialog-timeline probe after the subtitle/camera checkpoint
still had 16 unparsed managed-reference action payloads and no warning/error
sidecars:

| Class | Length | Count | Action code | Status before this pass |
| --- | ---: | ---: | ---: | --- |
| `DialogAnimActData` | 240 | 10 | 54 | `$heuristic` / `$unparsed` |
| `DialogCamActData` | 560 | 3 | 51 | `$heuristic` / `$unparsed` |
| `DialogCamActData` | 588 | 1 | 51 | `$heuristic` / `$unparsed` |
| `DialogCamActData` | 644 | 1 | 51 | `$heuristic` / `$unparsed` |
| `DialogEmotionActData` | 220 | 1 | 122 | `$heuristic` / `$unparsed` |

The 10 short `DialogAnimActData` records all came from
`dlg_npc_0005_1_timeline`, but they have a stable 240-byte scalar layout. They
share the normal first-12-byte dialog action timing prefix, action code `54`, no
aligned non-empty strings, fixed zero/constant regions, selector-like integers
at relative offsets `28` and `236`, an opaque variable int at `72`, and bounded
finite scalar slots including relative `112`. Because local `tools/DummyDll`
still does not contain a usable `Beyond.Gameplay.DialogAnimActData` schema, the
exporter records this as `DialogAnimActDataShortScalarBlock` with
`$partialDecoded` and `$inferred` rather than claiming a full script layout.

Verification command:

```bat
cd /d D:\fluffy-dump\tools\animestudio-dummydll-gain-test
.\..\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\dialog_timelines_11_shortanim_20260628" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --mono_behaviour_type_tree_priority ScriptFirst --filter_data "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_filter_data.json" --names "^dlg_(chen_1|npc_0005_1|e1m1_1|e2m2_1|e2m2_3d5|e2m4_11|e2m4_7|e2m5_2|e2m5_4|e3m1_1|sm1l1m7_1)_timeline$" --map_op "CABMap,Load" --map_name endfield_streamingassets_full_current
```

Result: exit code 0, 11 JSON files, no `.warning.txt` or `.error.txt` sidecars.
Marker counts moved from `$partialDecoded=512`, `$heuristic=21`, `$unparsed=16`
to `$partialDecoded=522`, `$heuristic=10`, `$unparsed=6`. The 10 new decoded
records are exactly `DialogAnimActDataShortScalarBlock` length `240`; the
remaining current unparsed action payloads are the longer `DialogCamActData`
variants (`560`, `588`, `644`) and one length-`220` `DialogEmotionActData`.

## 2026-06-28 Long DialogCamActData Scalar Recovery

A follow-up pass targeted the largest remaining current dialog camera family from
`tmp\dialog_timelines_11_shortanim_20260628`: three `DialogCamActData` payloads
with length `560` and action code `51`. The local DummyDll set still does not
provide a usable `Beyond.Gameplay.DialogCamActData` field schema, and the
single length-`588` and length-`644` variants did not have enough independent
samples, so only the length-`560` family was promoted.

The promoted payloads came from:

| File | Rid | Length |
| --- | ---: | ---: |
| `dlg_e2m2_1_timeline_pDE364550918DFC78.json` | `4297684264117342074` | 560 |
| `dlg_e2m2_1_timeline_pDE364550918DFC78.json` | `4297684264117342162` | 560 |
| `dlg_e2m2_3d5_timeline_pF1CAF5E8DE51D46E.json` | `1047` | 560 |

The layout is recorded as `DialogCamActDataLongScalarBlock` with
`$partialDecoded` and `$inferred`. Guards validate the first-12-byte dialog
action timing prefix, action code `51`, repeated Unity serialized marker groups
such as `2,2,4`, fixed `-1.0f` and `0.5f` sentinel slots, zero-filled blocks,
and finite camera/scalar float slots. It intentionally does not parse or rename
fields beyond generic selector/scalar groups.

Verification command:

```bat
cd /d D:\fluffy-dump\tools\animestudio-dummydll-gain-test
.\..\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\dialog_timelines_11_longcam_20260628" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --mono_behaviour_type_tree_priority ScriptFirst --filter_data "D:\fluffy-dump\tools\animestudio-dummydll-gain-test\dialog_timelines_11_filter_data.json" --names "^dlg_(chen_1|npc_0005_1|e1m1_1|e2m2_1|e2m2_3d5|e2m4_11|e2m4_7|e2m5_2|e2m5_4|e3m1_1|sm1l1m7_1)_timeline$" --map_op "CABMap,Load" --map_name endfield_streamingassets_full_current
```

Result: exit code 0, 11 JSON files, no `.warning.txt` or `.error.txt` sidecars.
Marker counts moved from the prior short-animation checkpoint
`$partialDecoded=522`, `$heuristic=10`, `$unparsed=6` to
`$partialDecoded=525`, `$heuristic=6`, `$unparsed=3`. The three new decoded
records are exactly `DialogCamActDataLongScalarBlock` length `560`. The remaining
current dialog unparsed action payloads are the singleton length-`588` and
length-`644` `DialogCamActData` variants plus one singleton length-`220`
`DialogEmotionActData`.

## 2026-06-28 Dialog Singleton Sample Search

A read-only subagent search looked for additional independent samples for the remaining odd dialog action payload lengths. It found no new unique objects beyond the existing 11-dialog temporary probes.

Evidence summary:

- The current `export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json` contains exactly 11 strict `dlg_*_timeline` MonoBehaviour rows, matching `tools/animestudio-dummydll-gain-test/dialog_timelines_11_filter_data.json`.
- `DialogCamActData` length `588`: one unique object, `dlg_e2m4_7_timeline`, PathID `-2965055753730031689`, rid `1024`, ref offset `6432`, length `588`, source offset `1130676656` in `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk`.
- `DialogCamActData` length `644`: one unique object, `dlg_e2m2_1_timeline`, PathID `-2434682336205472648`, rid `4297684264117342187`, ref offset `36600`, length `644`, source offset `1557302705` in the same chk.
- `DialogEmotionActData` length `220`: one unique object, `dlg_e2m5_2_timeline`, PathID `2544947724258404700`, rid `1011`, ref offset `2892`, length `220`, source offset `1132350533` in the same chk.

Conclusion: keep `DialogCamActData` lengths `588`/`644` and `DialogEmotionActData` length `220` as singleton evidence only. They are not safe to promote to decoded layouts without broader dialog/timeline candidates or additional independent samples.
