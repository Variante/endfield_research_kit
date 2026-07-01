# Source Graph Database

`tools/endfield_source_graph.py` builds a local SQLite relationship graph from
recovered WebUI story and Gameplay data, selected structured tables, exported
assets, character recovery manifests, material links, and optional AnimeStudio
asset maps.

Generated graph files live under `reports/source_graph/`. They are research
outputs, not exported source material, so they should not be written under
`export_full/`.

## Commands

Quick iteration build:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps
```

Full build with AnimeStudio asset maps:

```bat
python tools\endfield_source_graph.py build
```

Useful queries:

```bat
python tools\endfield_source_graph.py query dlg_c17m1_5 --limit 20
python tools\endfield_source_graph.py story dlg_c17m1_5 --limit-lines 8
python tools\endfield_source_graph.py issues --code inferredOptionResponse --limit 20
python tools\endfield_source_graph.py used-by pid:6C45653831AB1627 --limit 10
python tools\endfield_source_graph.py used-by pathid:4135669062202981187 --kind unity_pathid --limit 10
```

Useful flags:

- `--skip-gameplay`: skip WebUI Gameplay entry/skill/talent/progression ingestion.
- `--skip-asset-maps`: skip the expensive AnimeStudio asset-map pass.
- `--skip-reference-rows`: skip WebUI reference row expansion.
- `--skip-followups`: build only the graph and summary files.
- `--include-all-material-json`: scan all material JSON files instead of only
  actor material JSON files.

## Outputs

Core files:

- `endfield_source_graph.sqlite`
- `summary.json`
- `summary.md`
- `voice_audio_links.json`
- `character_recovery_candidates.json`
- `option_branch_gaps.json`
- `map_level_index.json`
- `semantic_update_summary.json`

The old standalone follow-up tools have been retired into
`tools/endfield_source_graph.py`; the graph builder writes those follow-up
indexes directly unless `--skip-followups` is passed.

## Graph Shape

Core SQLite tables:

- `nodes(id, kind, name, source, path, data)`
- `edges(src, dst, kind, source, evidence, data)`
- `aliases(alias, node_id, kind, source)`
- `files(path, kind, source, size, data)`
- `meta(key, value)`

Node kinds include story entries, lines, options, actors, localized text,
audio, videos, Gameplay weapons/equipment/characters/skills/talents/items,
equipment formulas/packs/suits/domains/unlock keys/stat properties/property
curves, progression records, assets, materials, meshes, shaders, animations,
map marks, structured table rows, reference rows, Unity asset containers,
Unity assets, and Unity PathIDs.

Edge kinds capture story membership, line ordering, actor names, localized
text, option anchors, audio use, narrative video links, Gameplay source-row,
skill, talent, progression, default-weapon, equipment domain/suit/formula/stat
property, formula-pack/unlock/output, and required-item relationships, table
ownership, exported files, character recovery manifest contents, asset-map
container ownership, and exported asset matches.

## Ingested Sources

High-value inputs:

- `webui/data/assets/index.json`
- `webui/data/assets/videos.json`
- `webui/data/lang/CN/index.json`
- `webui/data/lang/CN/conv/*.json`
- `webui/data/lang/CN/mission/*.json`
- `webui/data/lang/CN/reference/**`
- `webui/data/lang/CN/gameplay/index.json`
- `export_full/recovered/story_source_links.json`
- `export_full/recovered/AnimeStudio-cli/timeline_line_orders.json`
- actor material JSON under recovered AnimeStudio outputs
- Unity character recovery manifests under `unity_endfield_graph_shader_lab/`
- selected structured tables under `export_full/structured/StreamingAssets/Table/`
- optional AnimeStudio asset maps under `export_full/recovered/AnimeStudio-cli/`

The pre-Gameplay item/economy pass currently includes item, item type, item
showing type, reward, reward-drop, shop group, shop, shop goods, and shop goods
tag tables. The early world semantics pass includes map, level, loading,
scene-area, map-mark, track-map, collectable, factory-region, settlement POI,
and shop-channel POI tables. The pre-Gameplay combat semantics pass includes
buff, skill patch, use-item, general ability, ability entity attribute, global
effect, and potential talent effect tables. Selected structured tables also
include audio, character, dialog summary, interactive mission, mission extra
info, special level-to-map, and factory tables.

## Current Notes

2026-07-01 Gameplay, item/economy, combat semantics, world/map, and selected
structured-table ingestion adds exact-queryable `weapon`, `equipment`,
`character`, `character_break_stage`, `character_level_checkpoint`,
`character_stat_checkpoint`, `character_breakthrough`, `character_potential`,
`character_tag`, `character_tag_desc`, `character_profession`, `character_type`,
`character_team`, `character_preset`, `weapon_skill_recommendation`, `dungeon`,
`character_tutorial`, `character_tutorial_stage`, `character_tutorial_step`,
`character_trial`, `character_guide`, `training_recommendation`,
`attribute_meta`, `attribute_display_config`, `attribute_display_entry`,
`composite_attribute`, `attribute_filter`, `interactive_attribute`,
`enemy`, `enemy_template`, `enemy_attribute_template`,
`enemy_display_type`, `enemy_ability`, `enemy_attribute_modifier`, `buff`,
`map`, `level`, `level_loading`, `scene_area`, `map_mark`,
`map_mark_template`, `map_mark_type`, `map_mark_category`, `track_map_point`,
`track_map_link`, `scene_collectable`, `factory_region`, `settlement_poi`,
`shop_channel_poi`, `gameplay_skill_group`, `gameplay_skill`,
`gameplay_skill_level`, `skill_tag`, `gameplay_blackboard_key`,
`use_item_effect`, `general_ability`, `ability_entity`, `global_effect`,
`global_effect_param`, `potential_talent_effect`, `gameplay_talent_group`,
`gameplay_talent`, `gameplay_progression`, `item`, `item_type`,
`item_showing_type`, `item_obtain_way`, `reward`, `reward_drop`, `shop_group`,
`shop`, `shop_goods`, `shop_goods_tag`, `factory_recipe`, `factory_item`,
`factory_machine`, `factory_craft_group`, `factory_craft_showing_type`,
`spaceship_npc_proxy`, `spaceship_skill`, `spaceship_room_type`,
`spaceship_room_attr`, `spaceship_room_level`, `spaceship_empty_room`,
`spaceship_formula`, `spaceship_clue`, `env_talk`, `i18n_text`, `system_jump`,
`activity`, `activity_tag`, `activity_condition`, `activity_task`,
`activity_stage`, `activity_milestone`, `activity_banner`, `activity_push`,
`achievement_category`, `achievement_group`, `achievement`,
`achievement_level`, `achievement_condition`, `achievement_statistic`, and
`factory_tech` nodes. A fast CN build with `--skip-asset-maps
--skip-reference-rows
--skip-followups` verified 72 weapon nodes, 220 equipment nodes, 30 character
nodes, 290 enemy nodes, 78 enemy template nodes, 98 enemy attribute-template
nodes, 5 enemy display-type nodes, 134 enemy ability nodes, 70 enemy modifier
nodes, 217 buff nodes, 6 map nodes, 208 level nodes, 147 level loading nodes, 74
scene areas, 34 map marks, 155 map mark templates, 39 map mark types, 5 map mark
categories, 32 track-map points, 64 track-map links, 37 scene collectables, 69
factory regions, 5 settlement POIs, 5 shop-channel POIs, 497 skills, 4,807 skill
level nodes, 33 skill tag nodes, 405 gameplay blackboard key nodes, 80 use-item
effect nodes, 9 general ability nodes, 14 ability entity nodes, 19 global effect
nodes, 54 global effect param nodes, 251 potential talent effect nodes, 526
talent nodes, 1,240 progression nodes, 2,425 item nodes, 93 item type nodes, 11
item showing-type nodes, 232 item obtain-way nodes, 5,722 reward nodes, 1,252
reward-drop nodes, 19 shop groups, 28 shops, 687 shop goods, 6 shop goods tags,
392 factory recipes, 485 factory item descriptors, 38 factory machines, 20
factory craft groups, and 22 factory craft showing types. The generated WebUI
payload deliberately exposes 610 visible Gameplay entries: 72 weapons, 220
equipment records, 28 visible character records, and 290 enemies. The two hidden
`chr_0002_endminm` / `chr_0003_endminf` Endministrator rows remain as
`CharacterTable` graph nodes and are folded into `chr_9000_endmin` story wiki
aliases for WebUI navigation. Example exact queries:

```bat
python tools\endfield_source_graph.py query chr_0017_yvonne --kind character
python tools\endfield_source_graph.py query chr_0017_yvonne:stat:90:4 --kind character_stat_checkpoint
python tools\endfield_source_graph.py query chr_0017_yvonne:potential:1 --kind character_potential
python tools\endfield_source_graph.py query chr_0017_yvonne:breakthrough:charBreak20 --kind character_breakthrough
python tools\endfield_source_graph.py query aglina_indie --kind character_preset
python tools\endfield_source_graph.py query dung_aglina_chartrain01 --kind character_tutorial
python tools\endfield_source_graph.py query attr_1 --kind attribute_meta
python tools\endfield_source_graph.py query wpn_pistol_0001 --kind weapon
python tools\endfield_source_graph.py query eny_0018_lbtough --kind enemy
python tools\endfield_source_graph.py query item_gold --kind item
python tools\endfield_source_graph.py query reward_payshop_wpn_claym_0003 --kind reward
python tools\endfield_source_graph.py query domainshop_goods_map01_10001 --kind shop_goods
python tools\endfield_source_graph.py query chr_0002_endminm_attack1 --kind gameplay_skill
python tools\endfield_source_graph.py query item_proc_bomb_1 --kind use_item_effect
python tools\endfield_source_graph.py query atk_scale --kind gameplay_blackboard_key
python tools\endfield_source_graph.py query map01 --kind map
python tools\endfield_source_graph.py query mark_arrow --kind map_mark_template
python tools\endfield_source_graph.py query component_activity_xiranite_cmpt_1 --kind factory_recipe
python tools\endfield_source_graph.py query aglina_base01_lv001 --kind spaceship_npc_proxy
python tools\endfield_source_graph.py query spaceship_skill_chr_0004_pelica_1_1 --kind spaceship_skill
python tools\endfield_source_graph.py query growcabin_plant_crylplant_1_1 --kind spaceship_formula
python tools\endfield_source_graph.py query envEmoji_common_adaptationwork --kind env_talk
python tools\endfield_source_graph.py query activity_weekly_task_1 --kind activity
python tools\endfield_source_graph.py query week10_task1 --kind activity_task
python tools\endfield_source_graph.py query achv_adv_tundra_box --kind achievement
python tools\endfield_source_graph.py query jump_activity_conditional_multistage_1 --kind system_jump
```

2026-07-01 character progression graph progress: generated Gameplay character
payloads now promote break-stage ranges, level EXP/gold checkpoints, visible
character stat checkpoints, breakthroughs, and potential levels into first-class
source graph nodes. A fast rebuild on the current CN payload verified 140
`character_break_stage` nodes, 196 `character_level_checkpoint` nodes, 2,632
`character_stat_checkpoint` nodes, 112 `character_breakthrough` nodes, and 140
`character_potential` nodes. Edge checks verified 140 `has_character_break_stage`,
364 `break_stage_allows_exp_item`, 196 `has_character_level_checkpoint`, 140
`level_checkpoint_gold_cost`, 2,632 `has_character_stat_checkpoint`, 18,424
`stat_checkpoint_has_property`, 112 `has_character_breakthrough`, 112
`unlocks_character_break_stage`, 28 `uses_character_potential_item`, 140
`has_character_potential`, 140 `uses_potential_talent_effect`, 794
`character_potential_uses_blackboard_key`, 101 `character_potential_unlocks_item`,
and 28 `uses_default_weapon` edges. The current CN Gameplay payload used for
this check reports 515 visible entries: 72 weapons, 220 equipment records, 28
characters, 78 visible enemy entries, and 117 usable items, while preserving 290
`enemyVariants` as generated payload evidence. This makes authored character
progression values queryable without simulating runtime formulas.

2026-07-01 character support and attribute dictionary graph progress: source
graph ingestion now promotes character tags/descriptions, professions, element
types, presets, teams, weapon recommendations, weapon-skill recommendations,
tutorials, trials, training thresholds, and shared attribute display metadata. A
fast CN rebuild verified 75 `character_tag` nodes, 108 `character_tag_desc`
nodes, 6 professions, 5 character types, 635 presets, 185 teams, 12 unique
weapon-skill recommendation nodes, 29 dungeons, 22 tutorials, 97 tutorial
stages, 336 tutorial steps, 7 trials, 6 character guide rows, 80 training
recommendation rows, 94 attribute meta rows, 55 attribute display configs, 127
attribute display entries, 9 composite attribute nodes, 1 attribute filter, and
51 interactive attribute rows. Edge checks verified 274 `has_character_tag`,
635 `preset_uses_character`, 635 `preset_uses_weapon`, 2,340
`preset_uses_equipment`, 832 `team_includes_preset`, 8
`team_requires_character`, 115 `character_recommends_weapon`, 174
`character_recommends_weapon_skill`, 97 `tutorial_has_stage`, 336
`tutorial_stage_has_step`, 22 `character_training_dungeon`, 86
`attribute_show_includes_modifier`, 25 `composite_attribute_includes`, 21
`attribute_filter_includes`, and 204 `interactive_attribute_sets_property`
edges. That scouted slice has since landed in the Spaceship/base graph pass
below.

2026-07-01 Spaceship/base graph progress: source graph ingestion now promotes
Spaceship NPC proxies, behavior EnvTalk refs, base skills, room types, room
attrs, room levels, empty rooms, growth/manufacture formulas, clue rows, EnvTalk
rows, audio refs, item refs, and local I18n text references. A fast CN rebuild
verified 52 `spaceship_npc_proxy` nodes, 140 `spaceship_skill` nodes, 8
`spaceship_room_type` nodes, 18 room attrs, 15 room levels, 6 empty rooms, 38
formulas, 7 clues, 1,704 EnvTalk nodes, and 516 I18n text ref nodes. Edge
checks verified 52 `spaceship_proxy_for_character`, 234
`spaceship_behavior_uses_env_talk`, 108 `character_has_spaceship_skill`, 140
`spaceship_skill_applies_to_room_type`, 25 `spaceship_room_level_for_type`, 31
room-level item costs, 23 room-level formula unlocks, 30 formula consumed-item
edges, 38 produced-item edges, 15 material-to-seed and 15 seed-to-material
reverse map edges, 2,537 `env_talk_uses_audio`, and 1,046 `uses_i18n_text`
edges. The scouted Activity/Achievement plus SystemJump slice has since landed
below.

2026-07-01 Activity/Achievement/SystemJump graph progress: source graph
ingestion now promotes `SystemJumpTable`, root activities, activity tags,
activity conditions, weekly and multistage tasks, activity stages, milestones,
banners, push bubbles, achievement categories/groups, achievements, achievement
levels, achievement conditions, and achievement statistic rows. The corrected
fast CN rebuild verified 814,908 total graph nodes and 1,254,229 edges, including
600 `defines_system_jump` edges, 64 authored `defines_activity` edges, 23
activity tags, 300 activity conditions, 276 activity tasks, 150 activity stage
nodes, 5 milestones, 18 banners, 34 push bubbles, 8 achievement categories, 12
achievement groups, 114 achievements, 156 achievement levels, 200 achievement
conditions, and 3 achievement statistic rows. Edge checks verified 63
`activity_has_tag`, 42 `activity_jumps_to`, 40 `activity_rewards`, 276
`activity_has_task`, 43 `task_jumps_to`, 16 task reward edges, 350
`activity_has_stage`, 332 `stage_rewards`, 121 `stage_jumps_to`, 50
`stage_uses_mission`, 41 stage unlock-condition edges, 139 stage completion
condition edges, 18 `banner_jumps_to`, 34 `activity_has_push`, 12
`achievement_category_has_group`, 114 `achievement_group_has_achievement`, 156
`achievement_has_level`, 200 `achievement_level_has_condition`, 3
`achievement_statistic_tracks`, 66 `system_jump_targets_activity`, 16
`system_jump_targets_factory_tech`, 50 `system_jump_targets_manual_craft_unlock`,
4 map jump targets, 24 dungeon jump targets, 22 domain jump targets, and 44 shop
group jump targets. Averroes scout identified factory tech-tree/unlock bridge as
the next compact graph slice: 71 tech nodes, 72 machine-to-tech links, 59
blueprint links, 89 building item links, 168 manual-craft unlock links, and 45
manual-craft upgrade rows expected from local tables.

2026-07-01 world/map graph progress: an early world semantics pass now ingests
`MapIdTable`, `LevelDescTable`, `LevelLoadingTable`, `SpecialLevelToMapTable`,
`SceneAreaTable`, `MapMarkInsTable`, `MapMarkTempTable`, `MapMarkTypeTable`,
`MapMarkCategoryTable`, `TrackMapPointTable`, `TrackMapLinkTable`,
`SceneCollectableItemTable`, `FactoryLevelRegionTable`,
`SettlementLevelPOIMapTable`, and `ShopChannelLevelPOIMapTable`. The fast CN
rebuild verified 3 `defines_map` edges, 6 map nodes including inferred map
prefixes, 188 `defines_level` edges, 147 `level_has_loading` edges, 122
`level_belongs_to_map` edges, 74 `level_has_scene_area` edges, 34
`level_has_map_mark` edges, 34 `map_mark_uses_template` edges, 173
`defines_map_mark_template` edges collapsed to 155 unique template nodes, 27
`map_mark_type_has_category` edges, 32 track-map point nodes, 64 track-map link
nodes, 37 scene collectables, 37 `level_has_collectable_item` edges, 69
`level_has_factory_region` edges, 5 `level_has_settlement_poi` edges, and 5
`level_has_shop_channel_poi` edges. General ability `banMap` values now link to
`map` nodes through `general_ability_banned_in_map`, not to level nodes.

2026-07-01 combat/buff/ability graph progress: a pre-Gameplay combat semantics
pass now ingests `BuffTable`, `SkillPatchTable`, `UseItemTable`,
`GeneralAbilityTable`, `AbilityEntityAttrTable`, `GlobalEffectTable`, and
`PotentialTalentEffectTable`. The fast CN rebuild verified 80 `defines_buff`
edges, 479 `defines_skill_patch` edges, 4,807 `defines_skill_patch_level` edges,
4,807 `has_skill_patch_level` edges, 1,053 `skill_level_has_tag` edges, 14,838
`skill_level_uses_blackboard_key` edges, 80 `defines_use_item_effect` edges, 80
`item_has_use_effect` edges, 83 `use_effect_applies_buff` edges, 1
`use_effect_runs_skill` edge, 202 `use_effect_uses_blackboard_key` edges, 9
`defines_general_ability` edges, 2 `general_ability_uses_item` edges, 9
`general_ability_unlock_system` edges, 2 `general_ability_banned_in_map` edges,
14 `defines_ability_entity_attr` edges, 19 `defines_global_effect` edges,
54 `global_effect_has_param` edges, 251 `defines_potential_talent_effect` edges,
57 `potential_talent_attaches_buff` edges, 30 `potential_talent_attaches_skill`
edges, 331 `potential_talent_modifies_skill_blackboard` edges, 331
`potential_talent_modifies_blackboard_key` edges, 30
`potential_talent_modifies_skill_param` edges, 51
`potential_talent_modifies_stat_property` edges, and 104
`potential_talent_uses_blackboard_key` edges. Blackboard numeric values are
stored as edge data for lookup; this pass indexes authored static parameters and
does not execute skill, buff, or talent formulas.

2026-07-01 item/economy graph progress: a pre-Gameplay pass now ingests
`ItemTable`, `ItemTypeTable`, `ItemShowingTypeTable`, `RewardTable`,
`RewardDropTable`, `ShopGroupTable`, `ShopTable`, `ShopGoodsTable`, and
`ShopGoodsTagTable`. The fast CN rebuild verified 2,376 `defines_item` edges,
2,376 `item_has_type` edges, 2,376 `item_has_showing_type` edges, 2,035
`item_has_obtain_way` edges, 288 `item_outcomes_item` edges, 5,722
`defines_reward` edges, 16,865 `reward_grants_item` edges, 2,344
`reward_may_grant_item` edges, 1,252 `defines_reward_drop` edges, 3,319
`reward_drop_may_drop_item` edges, 19 `defines_shop_group` edges, 28
`shop_group_has_shop` edges, 28 `defines_shop` edges, 687 `shop_has_goods`
edges, 687 `defines_shop_goods` edges, 687 `shop_goods_priced_in_item` edges,
673 `shop_goods_grants_reward` edges, 6 `defines_shop_goods_tag` edges, and 214
`shop_goods_tagged` edges. Item nodes are created before Gameplay ingestion so
full `ItemTable` rows own authored item ids, while reward/drop references add
unresolved gem item ids as item nodes when no `ItemTable` row exists.

2026-07-01 enemy semantic ingestion promotes authored `EnemyTable`,
`EnemyAttributeTemplateTable`, enemy display, ability, drop, and born-buff data
into Gameplay payload entries and graph edges. The CN payload verifies 290 enemy
entries, 9,800 distinct enemy stat-template rows, 29,000 per-enemy stat row
references, 406 ability references, and 194 born-buff references. The graph
verified 290 `uses_enemy_attribute_template`, 290 `uses_enemy_template`, 406
`has_enemy_ability`, 194 `starts_with_buff`, and 266 `drops_item` edges. Enemy
stats are HP/ATK/DEF checkpoints from authored level-dependent attributes;
combat scalars, resilience fields, independent attributes, and attr modifiers
are exposed as source-table facts, not as a recovered runtime formula.
2026-07-01 factory recipe graph progress: selected structured-table ingestion
now includes `FactoryManualCraftTable`, `FactoryMachineCraftTable`,
`FactoryHubCraftTable`, `FactoryItemTable`, `FactoryMachineCrafterTable`, and
`FactoryCraftShowingTypeTable`. A fast graph rebuild verified 392
`factory_recipe` nodes, 615 `factory_consumes_item` edges, 468
`factory_produces_item` edges, 76 `unlocked_by_factory_formula_item` edges, 257
`crafted_by_machine` edges, 76 `factory_recipe_domain` edges, 135
`has_factory_showing_type` edges, 316 `belongs_to_factory_craft_group` edges,
485 `factory_item` descriptor nodes, 38 `factory_machine` nodes, and 22
`factory_craft_showing_type` nodes. This makes manual, machine, and hub factory
recipes queryable by recipe ID, item ID, machine ID, domain, and showing type;
it does not yet simulate factory timing, power, logistics, or unlock rules.

The same build now links Gameplay entries and Gameplay cost/drop item nodes to
exported asset nodes by exact Gameplay ID, icon ID, model-path stem, or item-id
containment in asset paths. The fast CN verification build produced 6,716
`has_gameplay_asset` edges: 2,078 from weapons, 2,039 from characters, 1,760
from equipment, and 839 from Gameplay item nodes. The item links cover 96 item
nodes, split into 836 image edges and 3 `item_gold` drop-model edges;
`item_charpotentialup_chr_9000_endmin` still has no exported asset-path match.
Evidence values record the source field (`id`, `iconId`, `modelPath`, or
`itemId`) so later audits can separate broad ID matches from
icon/model-path/item matches.

2026-07-01 equipment semantic ingestion promotes equipment formula, domain,
suit, unlock, and stat-property details from compact Gameplay payload blobs to
queryable graph nodes. A fast CN build with
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 220
`equipment_formula` nodes, 27 formula packs, 22 suits, 2 gameplay domains, 22
unlock keys, 838 equipment property curves, and 24 stat-property nodes. It also
verified 220 `crafted_by_formula`, 220 `formula_outputs_equipment`, 220
`belongs_to_formula_pack`, 129 `unlocked_by`, 220 `uses_gameplay_domain`, 182
`has_equipment_suit`, 838 `has_equipment_property_curve`, and 838
`scales_stat_property` edges. Example exact queries:

```bat
python tools\endfield_source_graph.py query item_formu_t4_suit_atk02_hand_01 --kind equipment_formula
python tools\endfield_source_graph.py query domain_2 --kind gameplay_domain
python tools\endfield_source_graph.py query agi --kind gameplay_stat_property
```

2026-07-01 progression cost traversal now follows `itemBundle`, `items`,
formula materials, and positive `goldCost` fields in Gameplay payloads. A fast
CN build verified 3,820 `requires_item` edges total: 1,268 from progression
nodes, 1,008 from skill groups, 1,104 from talent nodes, 440 from equipment
formula nodes, and 736 total edges to `item_gold`. Numeric item counts at or
below 0 are filtered, so the rebuilt graph has no zero-count required-item
edges.

2026-07-01 asset relation ingestion now preserves `pid:<hex>` and
`pathid:<signed>` aliases for WebUI asset-index entries with exported PathIDs
and ingests asset-index material/texture relation blocks. After rebuilding the
full asset index, a fast CN graph build with
`--skip-asset-maps --skip-reference-rows --skip-followups` verified 291,078
`asset_pid` aliases, 291,078 `asset_pathid` aliases, 229,557 `uses_texture`
edges, 8,450 `uses_material` edges, 190,457 `referenced_by_material` edges,
and 37,702 `referenced_by_model` edges. The current full asset index has 84,103
relation records and resolves blank-name Material texture slots by `m_PathID`.
The `used-by` command is the focused CLI for those edges: it resolves asset
paths and `pid:<hex>` aliases to WebUI asset nodes by default, and can use
`--kind unity_pathid` for lower-level Material JSON `uses_texture_pathid`
queries.

2026-07-01 renderable asset entity ingestion groups exported LOD model rows into
`asset_entity` nodes keyed by source plus normalized model base. A fast CN graph
rebuild verified 10,465 `asset_entity` nodes, 30,482 `entity_has_lod_model`
edges, 1,962 `entity_uses_material` edges, and 8,581 `entity_uses_texture`
edges. Entity aliases resolve bare bases such as `actor_aglina_body_01`; texture
`used-by` queries now surface renderable entities such as
`anm_com_machine+1_001_01` in addition to raw material/model rows.

2026-07-01 weapon renderable bridge progress: Gameplay weapon nodes now link
directly to renderable `asset_entity` nodes when the weapon `modelPath` stem
matches an entity base or entity-base prefix. A fast CN graph rebuild verified
132 `has_gameplay_asset_entity` edges across 71 weapon sources and 132
renderable entity targets; the only weapon without a renderable entity candidate
is `wpn_lance_0003` (`寻路者道标`). The query
`python tools\endfield_source_graph.py used-by wpn_sword_0019_01 --kind asset_entity`
now surfaces `weapon:wpn_sword_0019` before raw asset-detail rows.

Use the quick build for normal story/option/map investigation. Use the full
build only when Unity asset container, PathID, or exported asset relationship
coverage matters.

Timeline recovery is first-class graph input. The graph records raw Timeline
line clip order, option clip anchors, Runtime Jump routes, skipped lines,
continuation options, runtime jump clip nodes, and links to extracted source
JSON. This makes the `story` and `issues` commands the best starting point
before changing WebUI story recovery rules.

The graph also ingests WebUI recovery warnings. For example,
`issues --code inferredOptionResponse` separates cases with only Timeline clip
placement from cases with stronger route/skip evidence.

2026-07-01 option override ingestion adds WebUI-only `option_override` nodes
from `webui/overrides/options.json` without treating them as game-source proof.
A fast CN graph build verified 43 `option_override` nodes and 587
`webui/option_override` edges: 43 `has_option_override`, 43
`defines_option_override`, 43 `overrides_option_group`, 74 `overrides_option`,
19 `anchored_after_line`, 19 `manual_position_after`, 8
`manual_position_pre`, 74 each of `option_first_line`, `option_path_story`, and
`option_enters_story`, plus 116 `option_path_line` edges. Query examples:

```bat
python tools\endfield_source_graph.py query manual-option:dlg_c28m3_23:1 --kind option_override --limit 20
python tools\endfield_source_graph.py query webui/overrides/options.json --kind file --limit 5
```

2026-07-01 option branch conflict audit adds
`scripts/story_recovery/build_option_override_branch_conflict_audit.py`, which
writes generated JSON/Markdown to `reports/source_graph/`. The current graph
audit verifies 74 manual response options: 26 manual first lines match inferred
edges, 24 conflict with inferred first-line edges, and 24 are manual-only. The
runtime-jump join finds 3 manual-supported rows overall and highlights
`dlg_e6m1_10` plus `dlg_e6m4_14` as high-signal conflicts where nearby Runtime
Jump evidence supports the manual first line over the old inferred edge. The
audit now also joins Timeline option-flow writer evidence: 20 option-flow groups
join, all 5 required IL2CPP writer/gate fact kinds are present, and 21 of 24
manual-vs-inferred conflicts have strict option rows while candidate runtime
`+0x18` fields remain all zero (`strictOptionRowsButAllZeroCandidateRuntimeField`).
Those rows should stay diagnostic/manual-display fixes unless a stronger active
runtime clip binding appears.

2026-07-01 story query precedence annotations: `tools/endfield_source_graph.py
story` now labels branch refs from `webui/option_override` as
`manual_authoritative` / `webuiOnly`, `option_branch_risk` refs as
`diagnostic_inference`, `timeline_route_branch` refs as
`runtime_route_evidence`, and `timeline_line_orders` refs as
`runtime_timeline_evidence`. For `option_first_line`, the story output also tags
manual/inferred match or conflict states and includes the opposing manual or
inferred first-line IDs. This makes mixed manual, inferred, and runtime-derived
story output safer to interpret without changing the underlying evidence graph.

Known parser limits are acceptable for current use:

- lightweight IL2CPP metadata parsing can leave generic/array/byref type
  indexes unresolved in reports;
- full asset-map ingestion is expensive and should be skipped unless needed;
- legacy local `character_recovery/` report directories may exist, but the
  maintained graph emits the top-level recovery candidate JSON.
