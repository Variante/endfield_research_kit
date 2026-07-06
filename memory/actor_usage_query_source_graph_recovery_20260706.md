# Actor Usage Query Source Graph Recovery - 2026-07-06

## Context

Actor and character evidence was spread across WebUI story indexes, dialog
lines, AudioDialog speaker channels, structured SNS/radio/remote tables,
character progression tables, gameplay rows, and exported asset-entity names.
Starting from an actor id such as `endminf` usually surfaced many raw audio
rows first, while the related character id `chr_0003_endminf` and model
entities such as `actor_endminf_body_01` required separate lookups.

## Change

`tools/endfield_source_graph.py` now has an `actor-usage` query. It resolves
terms through actor/character-adjacent seed kinds including:

- `actor`
- `character`
- `actor_image`
- `asset_entity`
- `model_config_model`
- `model_prefab`
- `model_radius`
- `world_entity`
- `npc_voice_profile`
- `text_voice_id`
- `audio_voice_extra`
- `profile_picture`
- `user_avatar`
- `business_card_topic`
- `spaceship_character_gift`
- `gameplay_skill`
- `gameplay_talent`
- `weapon`
- `character_trial`

The query reports direct graph evidence for actor and character relationships,
including story mentions, spoken lines, AudioDialog speaker channels,
structured dialog/SNS/radio/remote speaker rows, character progression and
potential edges, gameplay skill/talent/weapon edges, profile/social references,
and exported asset-entity model/material/texture edges.

It also derives a short actor token from ids such as `endminf`,
`chr_0003_endminf`, `actor_endminf_body_01`, and
`abilityentity_chr_0030_zhuangfy_...`. That token is used to surface candidate
actor/character nodes and candidate exported asset entities. Candidate matches
are returned separately from direct graph edges.

## Validation

Syntax and CLI checks:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py --help
```

Smoke checks against the current default graph:

```bat
python tools\endfield_source_graph.py actor-usage endminf --kind actor --limit 8
python tools\endfield_source_graph.py actor-usage zhuangfy --kind actor --limit 8
python tools\endfield_source_graph.py actor-usage chr_0003_endminf --kind character --limit 8
python tools\endfield_source_graph.py actor-usage actor_endminf_body_01 --kind asset_entity --limit 6
python tools\endfield_source_graph.py actor-usage chr_0004_pelica --kind character --limit 8
python tools\endfield_source_graph.py actor-usage chr_0004_pelica --kind actor --limit 8
python tools\endfield_source_graph.py actor-usage abilityentity_chr_0004_pelica_ultimate_skill_postmodel --kind model_config_model --limit 8
python tools\endfield_source_graph.py actor-usage pic_1_chr_0004_pelica --kind profile_picture --limit 8
```

Observed evidence:

- `endminf` resolves as `actor:endminf`, with 427
  `actor_has_speaker_channel` edges and 268 `actor_mentioned_by_story` edges in
  the current graph. Candidate expansion finds `actor:chr_0003_endminf`,
  `character:chr_0003_endminf`, and exported asset entities such as
  `actor_endminf_body_01`.
- `zhuangfy` resolves as `actor:zhuangfy`, with 776 speaker-channel edges.
  Candidate expansion finds `actor:chr_0030_zhuangfy`,
  `character:chr_0030_zhuangfy`, the Unity lab `actor_zhuangfy` node, and
  exported asset entities such as `actor_zhuangfy_body_01`.
- `chr_0003_endminf` resolves as `character:chr_0003_endminf` and shows
  character progression evidence including default weapon, potential, and
  growth/attribute edges, plus candidate exported actor model entities.
- `actor_endminf_body_01` resolves as an `asset_entity`, reports
  `entity_has_lod_model`, and derives token `endminf` for character candidate
  expansion.
- `chr_0004_pelica --kind character` reports progression and profile/voice
  evidence such as `character_growth_default_weapon`,
  `character_has_actor_image`, `has_character_potential`, and
  `has_profile_voice`, plus candidate exported actor model entities.
- `chr_0004_pelica --kind actor` separately resolves the story/audio actor
  node and shows `actor_has_speaker_channel`, demonstrating that actor and
  character nodes are intentionally distinct in the current graph.
- `abilityentity_chr_0004_pelica_ultimate_skill_postmodel` resolves as a
  `model_config_model`, showing `model_config_has_model`,
  `model_config_has_radius`, and `model_config_uses_prefab` while still
  deriving `pelica` candidate actor/character context.
- `pic_1_chr_0004_pelica` resolves as a `profile_picture`, linking to
  `character:chr_0004_pelica` through `picture_for_character` and to its unlock
  item through `profile_picture_unlock_item` /
  `item_unlocks_profile_picture`.

## Boundary

Direct edges in `relations` are graph evidence. `characterCandidates`,
`assetEntityCandidates`, and `candidateRelations` are token-based joins and
must be treated as candidate evidence unless another direct edge proves the
relationship. Actor ids, playable character ids, speaker-channel ids, SNS actor
ids, and exported model entity names are not globally one-to-one. This query is
not proof of runtime party roster state, runtime voice-selection rules,
animation playback, or final renderer behavior. Actor nodes currently have
weaker alias coverage than character/model/profile nodes in the default SQLite
graph, so ambiguous names should use `--kind` when possible. Current SQLite
edge names are authoritative until the graph is rebuilt; newer memory notes can
mention reverse edges not present in a stale graph.
