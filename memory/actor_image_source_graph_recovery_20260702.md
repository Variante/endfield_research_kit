# Actor Image Source Graph Recovery - 2026-07-02

A focused source-graph pass now ingests `ActorImageTable.json` from
`export_full/structured/StreamingAssets/Table/`.

This closes a character-visual asset gap from the original game data
understanding follow-up work. Character rows now have first-class `actor_image`
nodes and field-specific visual-token links for authored character image slots:

- `avatarPath`
- `bustPath`
- `illustrationPath`
- `missionPanelChrAvatarPath`

Validation build:

```bat
python tools\endfield_source_graph.py build --db tmp\actor_image_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- Nodes: 1,583,875
- Edges: 2,959,566
- Aliases: 2,149,994

New visual-layer counts in the validation DB:

- `actor_image`: 28
- `visual_token`: 37

New direct edge counts:

- `defines_actor_image`: 28
- `character_has_actor_image`: 28
- `character_has_avatar_image`: 28
- `character_has_bust_image`: 28
- `character_has_mission_panel_image`: 8

The pass also adds `asset_stem` aliases for each non-empty visual token on the
`actor_image` node. That lets the existing visual-token/exported-asset matching
step resolve authored character image fields to exported assets without adding a
separate asset parser.
