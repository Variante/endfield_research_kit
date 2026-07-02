# Guide Video Source Graph Recovery - 2026-07-02

## Scope

Recovered explicit source graph links from tutorial/guide data to indexed video
assets and guide-group ids:

- `WikiTutorialPageTable.video`
- `DungeonCharTutorialTable.tutorialStageData[].guideGroupId`
- `DungeonCharTrialTable.guideGroupId`

This turns guide and tutorial videos from searchable asset inventory into
navigable graph semantics.

## Recovered Semantics

`WikiTutorialPageTable` now resolves page `video` stems to indexed `video`
nodes and emits `wiki_tutorial_page_uses_video` edges with
`videoDeviceType` metadata. Guide videos are duplicated across export roots in
the current asset index, so the resolver prefers the matching
`StreamingAssets-structured` video node when a stem resolves to both
StreamingAssets and Persistent paths.

Character tutorial stages now emit `guide_group` nodes and
`tutorial_stage_uses_guide_group` edges instead of only adding `guide_group_id`
aliases to stage nodes.

Character trial rows now emit `trial_uses_guide_group` edges for non-empty
trial guide groups.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\guide_video_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1684421 nodes, 3113956 edges, 2272423 aliases
```

Focused semantic counts:

```text
NODE guide_group 174
NODE wiki_tutorial_page 527
NODE video 942
EDGE wiki_tutorial_page_uses_video 253
EDGE tutorial_stage_uses_guide_group 75
EDGE trial_uses_guide_group 1
```

The first validation pass produced `0` wiki video edges because every tested
guide video stem resolved to both StreamingAssets and Persistent video nodes.
After adding the StreamingAssets preference, all 253 non-empty wiki tutorial
video rows resolve to video nodes.
