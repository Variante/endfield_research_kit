# Quest Tree Source Connections

Quest Tree nodes are `MissionRuntimeAsset.questDic` quest ids, not story files.
The durable join chain is:

```text
webui/data/lang/CN/mission/<mission>.json
  timelineRecovery.questTree.*[].questId
    -> timelineRecovery.quests[] by questId
    -> timelineRecovery.quests[].storyRefs[]
       or timelineRecovery.questSpatialTrack[].resources[]
    -> timelineRecovery.scenePlacement[<storyKey>]
    -> webui/data/lang/CN/conv/<storyKey>.json
    -> exported source/debug files under export_full/
```

The strongest quest-to-file evidence is the quest's original
`MissionRuntimeAsset/<mission>.json` source field. `scenePlacement` then keeps
secondary placement/order evidence such as `sourceBackedSceneEdges`,
`incomingEdges`, `outgoingEdges`, `sourceFiles`, and `levelIds`.

## Example: Cutscene

`e7m4_q#13` in `webui/data/lang/CN/mission/e7m4.json` is a Quest Tree node with
`attachedChunkIds: ["c2"]`.

Direct source:

```text
export_full/structured/StreamingAssets/Data/Json/MissionRuntimeAsset/e7m4.json
  questDic.e7m4_q#13.objectiveList[0].condition._cutsceneId.constValue
  = cutscene_e7m4_1
```

Generated joins:

- `timelineRecovery.quests[].storyRefs[]` contains
  `{kind: "cutscene", sceneKey: "cutscene_e7m4_1"}`.
- `questSpatialTrack[]` for `e7m4_q#13` lists resources
  `cutscene_e7m4_1` and `objectiveStoryRef: cutscene_e7m4_1`.
- `scenePlacement.cutscene_e7m4_1.questIds` includes `e7m4_q#13`.
- `webui/data/lang/CN/conv/cutscene_e7m4_1.json.sourceLinks[]` repeats the
  original `MissionRuntimeAsset` source path.

Actual recovered cutscene files live in
`webui/data/lang/CN/conv/cutscene_e7m4_1.json.cutscene.variants[]`, for example:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/TextAsset/f_cutscene_e7m4_1.json
export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/MonoBehaviour/f_cutscene_e7m4_1_Audio.json
export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/MonoBehaviour/f_cutscene_e7m4_1_Others_AU_EN.json
```

Subtitle/text evidence for individual lines is in `lines[*]._debug`, joining:

```text
TextTable[cutscene_e7m4_1_01].id
  -> I18nTextTable_CN[-4626715066193321455]
  -> AnimeStudio Subtitle Track MonoBehaviour file
```

For this cutscene, the conv payload also exposes cutscene-level runtime/audio
metadata:

```text
cutscene.paths[]: Assets/Beyond/DynamicAssets/Gameplay/Cutscene/f_cutscene_e7m4_1/Prefab/f_cutscene_e7m4_1
cutscene.audioEvents[]: au_sfx_cs_e7m4_1, au_vo_cs_e7m4_1_f, au_vo_cs_e7m4_1_m
```

## Example: Radio

`a1m6d5_q#11` in `webui/data/lang/CN/mission/a1m6d5.json` is attached to
`radio_a1m6d5_1` and chunk `c4`.

Direct source:

```text
export_full/structured/StreamingAssets/Data/Json/MissionRuntimeAsset/a1m6d5.json
  $.actionMapRaw.dataMap.actionList[0]._radioId.constValue
  = radio_a1m6d5_1
```

Generated joins:

- `questSpatialTrack[]` for `a1m6d5_q#11` lists resource
  `{kind: "radio", key: "radio_a1m6d5_1"}`.
- `scenePlacement.radio_a1m6d5_1.questIds` includes `a1m6d5_q#11`.
- `webui/data/lang/CN/conv/radio_a1m6d5_1.json.sourceLinks[]` repeats the
  original `MissionRuntimeAsset` source path.

Actual radio text/audio-id rows are in
`webui/data/lang/CN/conv/radio_a1m6d5_1.json.lines[]`:

```text
lines[0].id = radio_a1m6d5_1_001
lines[0].audio = au_radio_a1m6d5_1_001
lines[0]._debug.table = RadioTable.radioSingleDataList
lines[0]._debug.fields.text:
  RadioTable.radioSingleDataList[radio_a1m6d5_1_001].radioText
  -> I18nTextTable_CN[-7129651965124096651]
```

The audio ids used by radio lines are authored in `RadioTable` as
`audioOverride`. They are not always present in `AudioDialog.json`, so the
reliable local link is currently from `RadioTable` line rows to the audio id,
then to the packed Wwise/PCK audio payloads rather than to a decoded `.wem`
file path.

## Useful Queries

The source graph confirms direct mission-runtime references:

```bat
python tools\endfield_source_graph.py query cutscene_e7m4_1 --kind story
python tools\endfield_source_graph.py query radio_a1m6d5_1 --kind story
```

For one-off inspection, load the generated mission and conv payloads:

```bat
python -c "import json; m=json.load(open('webui/data/lang/CN/mission/e7m4.json', encoding='utf-8')); print(m['timelineRecovery']['scenePlacement']['cutscene_e7m4_1'])"
python -c "import json; c=json.load(open('webui/data/lang/CN/conv/radio_a1m6d5_1.json', encoding='utf-8')); print(c['lines'][0]['_debug'])"
```

## Narrative Videos

Narrative MP4 binding is separate from Quest Tree ownership. Once a quest node
resolves to a story key, check that story's conv payload for
`narrativeVideos[]`.

Example: `webui/data/lang/CN/conv/dlg_e0m2_5.json` carries
`m_cs_video_dlg_e0m2_5.mp4` with:

```text
rel = StreamingAssets-structured/Data/Video/PC/Narrative/Cutscene/m_cs_video_dlg_e0m2_5.mp4
binding.sourceKinds = ["timelinePlayable"]
binding.evidence[0].asset =
  export_full/recovered/AnimeStudio-cli/timeline_extract/048B4163B7ADCBCB40EB3B754F26C8F9/MonoBehaviour/BeyondFMVPlayableAsset(Clone).json
binding.evidence[0].container =
  assets/beyond/dynamicassets/gameplay/dialog/timeline/dlgtl_e0m2_5_sub_1/playable/dlgtl_e0m2_5_sub_1_actor.playable
```

So the video join is:

```text
questId -> storyKey -> conv/<storyKey>.json.narrativeVideos[]
  -> Data/Video/PC/Narrative/.../*.mp4
  -> BeyondFMVPlayableAsset timeline evidence
```
