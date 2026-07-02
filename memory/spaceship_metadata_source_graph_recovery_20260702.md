# Spaceship Metadata Source Graph Recovery - 2026-07-02

## Scope

Extended spaceship source-graph semantics for the remaining nonempty
spaceship/base-building metadata tables that were not covered by the existing
spaceship pass:

- `SpaceshipAreaUnlockNeedCenterLvTable`
- `SpaceshipBacklogConfigDataTable`
- `SpaceshipConst`
- `SpaceshipSubCharGiftTable`

`SpaceshipDomainMoneyExchangeRateDataTable` was already covered by the economy
metadata pass as domain coupon exchange-rate semantics.

## Recovered Semantics

- Construction areas now expose required command-center levels through
  `spaceship_construction_area` nodes and `spaceship_area_requires_center_level`
  edges.
- Backlog types now expose sort order, color, icon asset aliases, title text,
  and subtitle text.
- Spaceship constants now expose scalar/list constants and promote recognizable
  references to items, rewards, room types, scene names, and spaceship game
  modes.
- Sub-character gift rows now connect characters to per-slot gift-talk nodes and
  gift dialog story ids.

## Validation

Built a temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\spaceship_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- `1,628,296` nodes
- `3,057,180` edges
- `2,234,845` aliases

Targeted counts:

- `spaceship_construction_area`: 2 nodes
- `spaceship_backlog_type`: 2 nodes
- `spaceship_const`: 67 nodes
- `spaceship_char_gift_talk`: 78 nodes
- `spaceship_scene`: 2 nodes
- `spaceship_game_mode`: 2 nodes

Representative edge counts:

- `spaceship_area_requires_center_level`: 2
- `spaceship_backlog_title_text`: 2
- `spaceship_backlog_subtitle_text`: 2
- `spaceship_const_item_ref`: 2
- `spaceship_const_reward_ref`: 1
- `spaceship_const_room_ref`: 3
- `spaceship_const_scene_ref`: 2
- `spaceship_const_game_mode_ref`: 2
- `defines_spaceship_sub_character_gifts`: 26
- `spaceship_character_has_gift_talk`: 78
- `spaceship_gift_talk_dialog`: 78

Example recovered link:

- `chr_0004_pelica` gift slots now link to
  `story:dlg_npc_0004_pelica_spaceshipgift`.
