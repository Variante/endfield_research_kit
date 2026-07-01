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
map marks, SNS/radio/remote communication rows, audio cue handlers,
voice-extra rows, structured table rows, reference rows, Unity asset containers,
Unity assets, and Unity PathIDs.

Edge kinds capture story membership, line ordering, actor names, localized
text, option anchors, audio use, narrative video links, raw SNS content/option
links, radio/remote line-to-audio bridges, audio cue event references,
AudioVoiceExtra-to-AudioDialog links, Gameplay source-row, skill, talent,
progression, default-weapon, equipment domain/suit/formula/stat property,
formula-pack/unlock/output, and required-item relationships, table ownership,
exported files, character recovery manifest contents, asset-map container
ownership, and exported asset matches.

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
- selected structured tables under `export_full/structured/StreamingAssets/Table/`,
  including gameplay, world, activity, PRTS, NPC/voice/bark, SNS, radio,
  remote-common, audio cue, and voice-extra tables
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
`achievement_level`, `achievement_condition`, `achievement_statistic`,
`factory_tech_group`, `factory_tech_category`, `factory_tech_layer`,
`factory_tech`, `factory_tech_condition`, `factory_building`,
`factory_building_type`, `factory_renderer_template`,
`factory_blueprint_machine_icon`, `manual_craft_unlock`, `prts_page`,
`prts_category`, `prts_first_level`, `prts_entry`, `rich_content`,
`rich_content_line`, `reading_popup`, `reading_popup_icon`, `prts_reading`,
`prts_reading_entry`, `prts_investigation`, `prts_investigation_group`,
`prts_note`, `npc`, `npc_group`, `npc_template`, `npc_voice_profile`,
`environmental_npc`, `npc_camp_tag`, `npc_career_tag`,
`audio_dialog_channel`, `wwise_event`, `responsive_dialog_group`,
`responsive_speaker`, `responsive_trigger`, `responsive_trigger_key`,
`responsive_trigger_type`, `responsive_event_template`, `responsive_response`,
`bark_group`, `bark_variant`, `bark_text`, and `bark_table_const` nodes. A fast CN
build with `--skip-asset-maps
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
python tools\endfield_source_graph.py query tech_jinlong_1_battle_cannon_2 --kind factory_tech
python tools\endfield_source_graph.py query air_dancer_1 --kind factory_building
python tools\endfield_source_graph.py query hdwk_item_drop_agfly_1_1 --kind manual_craft_unlock
python tools\endfield_source_graph.py query nar_002_settlement --kind prts_entry
python tools\endfield_source_graph.py query text_002_settelment --kind rich_content
python tools\endfield_source_graph.py query rp_radio_c16m4_50 --kind reading_popup
python tools\endfield_source_graph.py query research_001 --kind prts_investigation
python tools\endfield_source_graph.py query chaosheng --kind npc
python tools\endfield_source_graph.py query CommonKid --kind npc_voice_profile
python tools\endfield_source_graph.py query action_dash_start --kind responsive_trigger_key
python tools\endfield_source_graph.py query -1006722661 --kind bark_text
python tools\endfield_source_graph.py query sns_a1m1_1 --kind sns_dialog
python tools\endfield_source_graph.py query option_sns_a1m1_1_1_001 --kind sns_option
python tools\endfield_source_graph.py query radio_a1m6d1_1 --kind radio
python tools\endfield_source_graph.py query remotecomm_c13m2_1 --kind remote_common
python tools\endfield_source_graph.py query -1000413093 --kind audio_voice_extra
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
`achievement_statistic_tracks`, 66 `system_jump_targets_activity`, 13
`system_jump_targets_factory_tech`, 1 `system_jump_targets_factory_tech_group`,
50 `system_jump_targets_manual_craft_unlock`, 4 map jump targets, 24 dungeon
jump targets, 22 domain jump targets, and 44 shop group jump targets. The
scouted factory tech-tree/unlock bridge has since landed below.

2026-07-01 Factory tech-tree/unlock graph progress: source graph ingestion now
promotes `FacSTT*` tech groups/categories/layers/nodes/conditions,
machine-to-tech links, blueprint-to-machine item links, factory buildings,
building types, renderer templates, blueprint machine icons, manual-craft
formula unlocks, and manual-craft upgrade rows. The corrected fast CN rebuild
verified 816,942 total graph nodes and 1,259,077 edges, including 2
`factory_tech_group` nodes, 11 categories, 6 layers, 71 authored tech nodes, 5
tech conditions, 94 factory buildings, 31 referenced building types, 113
renderer templates, 61 blueprint machine icon nodes, 168 manual-craft unlock
nodes, and 194 factory machine nodes. Edge checks verified 55
`factory_tech_requires_tech`, 128 `factory_tech_unlocks_item`, 52 tech action
item refs, 20 tech action machine refs, 3 tech action domain refs, 6
condition-to-level refs, 72 `machine_unlocked_by_tech`, 59
`blueprint_item_builds_item`, 89 `building_item_defines_building`, 94
`factory_building_has_type`, 82 `factory_building_has_map_mark_template`, 93
default renderer template refs, 97 building renderer template refs, 113
`renderer_template_for_machine`, 168 `manual_craft_material_unlocks_formula_item`,
45 manual-craft upgrade item edges, 13 system jumps to exact factory techs, and
1 system jump to a factory tech group. The scouted PRTS Archive / Reading /
RichContent bridge has since landed below.

2026-07-01 PRTS Archive/Reading/RichContent graph progress: source graph
ingestion now promotes PRTS page/category/first-level/archive entries,
RichContent roots and content lines, Reading popup rows/icons, PRTS reading
roots/entries, investigations/groups/notes, and SystemJump PRTS detail targets.
The corrected fast CN rebuild verified 829,057 total graph nodes and 1,279,042
edges, including 3 `prts_page` nodes, 6 categories, 375 first-level nodes, 422
PRTS entry nodes, 586 RichContent roots, 2,991 RichContent line nodes, 576
reading popups, 14 referenced popup icon nodes with 6 authored icon-map
definitions, 21 PRTS reading roots, 36 PRTS reading entries, 13 investigation
nodes, 29 investigation groups, and 29 notes. Edge checks verified 414 canonical
first-level-to-entry edges, 414 `defines_prts_entry` edges from `PrtsAllItem`,
327 record, 64 document, and 23 multimedia subtype definitions, 105 PRTS
entry-to-story targets, 391 entry-to-RichContent targets, 2,991 rich-content
line edges, 2,986 RichContent root i18n refs, 2,986 line i18n refs, 247
reading popup-to-story targets, 548 reading popup-to-RichContent targets, 576 popup icon-use edges, 36 PRTS reading
entries, 2 reading-entry story targets, 28 reading-entry RichContent targets, 12
authored investigations, 12 investigation-category rows, 47 direct investigation
entry refs, 58 investigation-to-group refs, 94 group-to-entry refs, 58
group-to-note refs, 25 system jumps to PRTS entries, and 5 system jumps to PRTS
investigations. Investigation grouping counts intentionally preserve duplicate
evidence from both `PrtsInvestigate.categoryDataList` and
`PrtsInvestigateCategory.list`; direct `PrtsCategory` to `PrtsPage` edges are
only emitted for exact key matches, so inferred page buckets remain out of graph
scope. The scouted NPC / Ambient Voice / Responsive Bark bridge has since
landed below.

2026-07-01 NPC/Ambient Voice/Responsive Bark graph progress: source graph
ingestion now promotes `NpcTable`, `NpcGroupTable`, `NpcTemplateGroupTable`,
`NpcInfoTable`, `AtmosphereNpcTable`, `GameplayAndEnvironmentalNpc`,
`AudioDialogChannel*`, `ResponsiveDialog`, `ResponsiveTriggers`, `AIBark`,
`AIBarkText`, and `AIBarkTableConst` into queryable semantic nodes. The corrected
fast CN rebuild verified 855,321 total graph nodes and 1,361,843 edges,
including 359 NPC nodes, 939 NPC groups, 543 unique NPC templates from 676
source rows, 1,239 voice profiles, 43 environmental NPC rows, 5 camp tags, 27
career tags, 676 audio dialog channel nodes including 33 mapping aliases, 1,142
Wwise event nodes, 7 responsive dialog/trigger groups, 72 responsive speakers,
9,521 responsive trigger nodes, 283 trigger keys, 165 global trigger types, 63
event templates, 4,325 responsive response nodes, 25 bark groups, 26 bark
variants, 928 bark text rows, and 11 bark constants. Edge checks verified 359
`npc_in_group`, 342 `npc_uses_template`, 341 `npc_group_uses_template`, 33
`npc_uses_env_talk`, 39 environmental NPC data-key group matches, 10
environmental template matches, 689 `npc_info_uses_template`, 541 Wwise-channel
and 635 voActor-channel voice profile links, 706 direct actor matches, 599
narrating and 599 radio Wwise channel events, 33 channel aliases, 642 channel to
actor matches, 9,521 responsive speaker-trigger/type/key edges, 13,919
trigger-response occurrence edges, 4,304 unique response-to-AudioDialog/audio
links, 868 response-to-bark-text links, 928 bark text-to-line links, and 30 bark
variant trigger-key links. Exact asset/dataKey joins remain intentionally zero
for this slice because current `asset_entity_id` aliases do not match NPC
template/dataKey IDs; the SNS, radio, remote-common, cue, and voice-extra
narrative/audio bridge has since landed below.

2026-07-01 narrative/audio communication graph progress: source graph ingestion
now promotes `SNSChatTable`, `SNSDialogTopicTable`, `SNSDialogOptionTable`,
`SNSDialogTable`, `SNSConst`, `RadioTable`, `RemoteCommonTable`,
`AudioCueTable`, `AudioVoiceExtraData`, `EmotionVoiceConfig`,
`AudioDialogCustomEventTable`, and `AudioDialogConfigs` into queryable semantic
nodes. A fast CN rebuild using the skip-asset-maps, skip-reference-rows, and
skip-followups path verified 939,999 total nodes and 1,532,614 edges, with 0
orphan edges from the new sources. New node counts include 122 `sns_chat`, 108
`sns_topic`, 1,284 `sns_option`, 288 `sns_dialog`, 5,684 `sns_content`, 2,375
`radio`, 4,103 `radio_line`, 30 `remote_common`, 284 `remote_common_line`, 175
`audio_cue`, 264 `audio_cue_handler`, 25,245 `audio_voice_extra`, 41
`emotion_voice_config`, 28 `voice_interjection`, 47 `audio_dialog_custom_event`,
and 4 `audio_dialog_config` nodes. Edge checks verified 288 raw SNS dialogs to
story nodes, 5,684 SNS content edges, 1,284 SNS content-to-option edges, 4,103
radio line-to-story-line and line-to-audio bridges, 284 remote line-to-story-line
bridges, 284 remote voice links, 221 cue handler event references, 25,245
voice-extra links to `AudioDialog` rows and audio nodes, and 928 voice-extra
links to existing story line nodes. SNS content IDs remain raw table content and
do not map directly to generated `line` nodes; radio lines, remote lines, and
matching `AudioVoiceExtraData` keys do map to generated line nodes where the
WebUI story corpus has them.

2026-07-01 audio config/support graph progress: source graph ingestion now
promotes `TextVoIdTable`, `AudioVoTone`, `AudioSpeakerTypeWeights`,
`AudioBattleBuildings`, `AudioCollection`, `AudioDrop`, `AudioFactory`,
`AudioFactoryAnnouncement`, `AudioItemDragAndDrop`, `AudioItemTypeDragAndDrop`,
and `AudioLevel`. The existing `AudioSequenceDialog` structured-table handler
was corrected so each sequence row becomes a distinct `audio_sequence_dialog`
node instead of collapsing under one `audio_sequence:sequence` node. A fast CN
rebuild verified 942,880 total nodes and 1,538,834 edges, with 0 orphan edges
from these audio support/config sources. New node counts include 180
`text_voice_id`, 115 `audio_vo_tone`, 3 `audio_speaker_type_weight`, 2
`audio_sequence_dialog_set`, 38 `audio_sequence_dialog`, 17
`audio_battle_building`, 31 `audio_collection`, 72 `audio_drop`, 73
`audio_factory`, 13 `audio_factory_announcement`, 571 `audio_item_drag_drop`,
11 `audio_item_type_drag_drop`, and 103 `audio_level` nodes; the old
`audio_sequence` kind is now 0. Edge checks verified 180 TextVoId line links,
153 TextVoId audio links, 291 voice tone variant audio links, 100 sequence dialog
links to `AudioDialog` rows/audio/line nodes, 38 sequence-response links, 80
sequence speaker-actor links, 80 sequence speaker-character links, 17
battle-building audio links to factory buildings and machines, 60
factory-building SFX event refs, 240 factory SFX event refs, 571 item drag/drop
links to item nodes, 457 item drag/drop links to factory items, 9 item-type
drag/drop links, 146 item drag/drop event refs, 99 level audio profile links,
and 105 level audio event refs. Values in SFX/config fields are modeled as
`wwise_event` nodes unless they
are explicit voice/audio IDs. The broad `DialogTextTable`/`DialogOptionTable`
support bridge has since landed below with exact joins only.

2026-07-01 dialog support graph progress: source graph ingestion now promotes
`DialogTextTable`, `DialogOptionTable`, `DialogSummaryTable`,
`DialogSummaryMapTable`, and `DomainDepotDeliverTargetDialogTable` into raw
support nodes that link back to generated Story/WebUI evidence only by exact ID.
A fast CN rebuild verified 1,026,124 total nodes and 1,698,548 edges, with 0
orphan edges from these dialog support sources. New node counts include 17,528
`dialog_text`, 4,343 `dialog_option`, 997 `dialog_summary`, 931
`dialog_summary_map`, and 15 `domain_depot_deliver_target_dialog` nodes. Edge
checks verified 17,528 dialog-text links to generated `line` nodes, 17,528
dialog-text story links via generated WebUI line ownership, 17,329 non-sentinel
dialog-text audio links, 15,337 dialog-text actor links, 4,219 dialog-option
links to generated option nodes, 931 summary-map links to summary nodes and raw
summary rows, 908 summary-map links to generated story nodes, and 15 initial
plus 15 repeat domain-depot dialog links to story nodes. The graph no longer
emits the `audio:0` sentinel as an audio node or edge target. These nodes are
supporting source-table evidence; they do not replace generated line order,
option branch, or option route recovery.

2026-07-01 decoded Data/Json config graph progress: source graph ingestion now
promotes exact WebUI Data-index MemoryPack decodes for `ModelTable`,
`ModelRadiusTable`, `InteractiveTable`, `InteractiveTemplateData`, and
`GameplayConfigWorldEntityRegistry`. After moving the pass behind Gameplay,
NPC, and audio config ingestion, a fast CN rebuild to a temporary DB verified
1,032,445 total nodes, 1,715,815 edges, and 1,437,796 aliases. New coverage
includes 552 `decoded_config_file` nodes, 5 decoded config families, 4
`model_config` roots, 1,201 unique `model_config_model` rows, 1,125
`model_radius` rows, 2 `interactive_table_config` roots, 271
`interactive_template` nodes, 922 `interactive_object` nodes, 542
`interactive_template_data` nodes, 2 `world_entity_registry` roots, 893
`world_entity` rows, and 228 remaining neutral `world_entity_detail` nodes. Edge
checks verified 4,397 `model_config_has_model` edges, 1,125
`model_config_has_radius` edges, 2,250 `model_radius_config_has_model` edges,
542 core-template path edges, 1,834 interactive object table edges, 917
interactive object-to-template edges, 418 interactive template-to-model edges,
26 interactive template audio edges, 1,786 world entity registry row edges, 66
world entity-to-enemy edges, 66 world entity-to-enemy-template edges, 3 world
entity-to-NPC edges, 594 world entity-to-interactive detail edges, 267 world
entity-to-model edges, 267 world entity-to-model-radius edges, 214 world
entity-to-audio-collection edges, 65 world entity-to-audio-dialog-channel edges,
and 228 world entity-to-neutral detail edges. Lean asset-index entity joins for
these model IDs remain 0, so the new model nodes are decoded config evidence,
not proof of exported model reconstruction. Example exact queries:

```bat
python tools\endfield_source_graph.py query abilityentity_0007_mimicw_death_postmodel --kind model_config_model
python tools\endfield_source_graph.py query abilityentity_0007_mimicw_death_postmodel --kind model_radius
python tools\endfield_source_graph.py query gantry_terminal1 --kind interactive_object
python tools\endfield_source_graph.py query int_001_comm_terminal --kind interactive_template_data
python tools\endfield_source_graph.py query 2800000160 --kind world_entity
```

2026-07-01 teleport validation decoded-config progress: source graph ingestion
now promotes exact `TeleportValidationDataTable` MemoryPack decodes from the
WebUI Data index. A fast CN rebuild to `tmp/source_graph_teleport.sqlite`
verified 1,032,692 total nodes, 1,716,403 edges, and 1,438,054 aliases. New
coverage includes 8 `teleport_validation_config` nodes, 222 unique
`teleport_point` nodes collapsed across Persistent and StreamingAssets duplicate
rows, 444 `teleport_validation_has_point` edges, 106 `teleport_point_in_level`
edges, and teleport links covering 17 distinct level ids. Each teleport point
preserves the exact id, validation float, 16-bit flag word, position, rotation,
nullable `mapId`, and four integer tail fields; `mapId` values are treated as
level ids and linked through the existing level/map graph. Example exact query:

```bat
python tools\endfield_source_graph.py query TpForMap_ent_10100020314 --kind teleport_point
```

2026-07-01 mission-area decoded-config progress: source graph ingestion now
promotes exact `GameplayConfigMissionAreaTable` rows from the WebUI Data index.
A fast CN rebuild to `tmp/source_graph_mission_area.sqlite` verified 1,032,774
total nodes, 1,716,593 edges, and 1,438,131 aliases. New coverage includes 2
`mission_area_config` nodes, 73 unique `mission_area` nodes collapsed across
Persistent and StreamingAssets duplicate rows, 146 `mission_area_config_has_area`
edges, and 37 `mission_area_for_mission` edges to 9 existing mission nodes when
the area key prefix exactly matches a known mission id. Each area node preserves
the exact key, type id, flag, two recovered vector triples, size values, and
bounded tail-length metadata; keys without an existing mission prefix remain
standalone area evidence instead of inferred mission links. Example exact query:

```bat
python tools\endfield_source_graph.py query c13m2_001 --kind mission_area
```

2026-07-01 subgame instance decoded-config progress: source graph ingestion now
promotes exact `SubGameInstanceDataTable` rows from the WebUI Data index. A fast
CN rebuild to `tmp/source_graph_subgame.sqlite` verified 1,032,791 total nodes,
1,716,624 edges, and 1,438,147 aliases. New coverage includes 2
`subgame_instance_config` nodes, 4 unique `subgame_instance` nodes collapsed
across Persistent and StreamingAssets duplicate rows, 1 `subgame_group` node, 8
`subgame_config_has_instance` edges, 4 `subgame_instance_default_group` edges,
and 12 explicit text edges split across failure, quit-button, and success text
ids. Each subgame instance preserves its source id, short hash, prefix bytes,
default group, three UI text ids, and marker bytes. Example exact query:

```bat
python tools\endfield_source_graph.py query world_energy_point04 --kind subgame_instance
```

2026-07-01 spawner decoded-config progress: source graph ingestion now promotes
bounded `SpawnerConfig` MemoryPack decodes from the WebUI Data index. A fast CN
rebuild to `tmp/source_graph_spawner.sqlite` verified 1,036,207 total nodes,
1,725,406 edges, and 1,442,058 aliases. New coverage includes 436 unique
`spawner_config` nodes collapsed across 849 Persistent/StreamingAssets config
files, 1,057 `spawner_enemy_entry` nodes, and 22 `gameplay_effect` key nodes.
Edge checks verified 849 `defines_spawner_config` edges, 1,057 config-to-enemy
row edges, 1,057 enemy-id edges to 178 distinct enemy keys, 1,599 born-buff
edges to 61 distinct buff keys, 677 blackboard-key edges to 23 distinct keys,
864 prewarn-audio edges to 16 distinct audio-event keys, and 980 prewarn-effect
edges to 22 distinct effect keys. Each enemy row preserves its row index,
enemy id, level, force-to-battle flag, wave/key string, override AI config,
patrol gait, born buffs with blackboard values, prewarn audio key, prewarn
effect key, fixed rotation, and prewarn time. The parser intentionally stops at
the enemy-library payload instead of claiming full-file consumption, and effect
or audio keys are reference evidence rather than exported asset proof. Example
exact queries:

```bat
python tools\endfield_source_graph.py query sc_base01_dg001_9900010011 --kind spawner_config
python tools\endfield_source_graph.py query eny_0018_lbtough_train --kind enemy
python tools\endfield_source_graph.py query buff_common_undeadable --kind buff
```

2026-07-01 BuffData decoded-config progress: source graph ingestion now promotes
bounded `BuffData` MemoryPack evidence from the WebUI Data index. A fast CN
rebuild to `tmp/source_graph_buff.sqlite` verified 1,050,017 total nodes,
1,757,974 edges, and 1,462,945 aliases. New coverage includes 4,616
`buff_data_defines_buff` edges from decoded config files to 2,325 unique buff
ids, plus 268 `gameplay_tag` nodes, 1,254 `buff_parameter` nodes, and 106
`buff_icon` nodes. Edge checks verified 1,862 BuffData string references to 779
distinct buff ids, 1,416 tag-string edges to 268 distinct gameplay tags, 13,373
parameter-string edges to 1,254 distinct parameter names, 1,404 effect-key edges
to 703 distinct BuffData effect keys, 273 audio-event edges to 145 distinct
audio keys, and 391 icon edges to 106 distinct icon ids. All 4,616 entries pass
the 29-member BuffData guard and carry generated `parsed-through-exact-tail`
post-id status; graph data preserves id-marker offsets, compact post-id sample
values, string scan counts, and per-edge byte offsets. These edges are bounded
length-prefixed string evidence, not proof of typed blackboard fields, timeline
action execution, formula evaluation, or exported effect/icon asset binding.
Example exact queries:

```bat
python tools\endfield_source_graph.py query buff_common_undeadable --kind buff
python tools\endfield_source_graph.py query Skill/Character/Common/Affixes --kind gameplay_tag
python tools\endfield_source_graph.py query icon_battle_affix_slow --kind buff_icon
```

2026-07-01 SkillData decoded-config progress: source graph ingestion now promotes
bounded `SkillData` MemoryPack evidence from the WebUI Data index. A fast CN
rebuild to `tmp/source_graph_skill.sqlite` verified 1,070,527 total nodes,
1,841,215 edges, and 1,487,149 aliases. New coverage includes 4,191
`skill_data_defines_skill` edges from decoded config files to 2,108 unique skill
ids, plus 3,323 `skill_parameter` nodes and 43 `skill_icon` nodes. Edge checks
verified 3,000 SkillData string references to 833 distinct buff ids, 1,786
tag-string edges to 311 distinct gameplay tags, 49,988 parameter-string edges
to 3,323 distinct parameter names, 9,527 effect-key edges to 3,900 distinct
effect keys, 6,178 audio-event edges to 3,156 distinct audio keys, and 188 icon
edges to 43 distinct icon ids. All 4,191 entries pass the 45-member SkillData
guard; 4,179 carry `parsed-through-smartTargetTagQuery`, 12 carry
`parsed-through-smartTargetPayload`, and all 4,191 switch-tail probes carry
`parsed-through-exact-tail`. These edges are bounded length-prefixed string and
post-tail sample evidence, not proof of target selection, action execution,
skill formula behavior, or exported effect/icon asset binding. Example exact
queries:

```bat
python tools\endfield_source_graph.py query abilityentity_0110_rytoken_boom_abilityrange --kind gameplay_skill
python tools\endfield_source_graph.py query P_actor_ikut_attack_01_start --kind gameplay_effect
python tools\endfield_source_graph.py query icon_round_chr_0007_ikut --kind skill_icon
```

2026-07-01 LevelScript inventory/reference graph progress: source graph
ingestion now promotes bounded `LevelScriptData` and `LevelScriptTemplateData`
inventory plus high-signal string-reference evidence from the WebUI Data index.
A fast CN rebuild to `tmp/source_graph_levelscript_refs.sqlite` verified
1,090,873 total nodes, 1,880,295 edges, and 1,521,156 aliases. Inventory
coverage includes 3,756 `level_script` nodes collapsed across 7,414 decoded
script files, 35 `level_script_template` nodes collapsed across 70 template
files, 20 template groups, 3 start-type nodes, and 120 `level_script_montage`
nodes. Edge checks verified 7,414 `level_script_data_defines_script` edges,
3,756 `level_has_level_script` edges across 148 level folders, 3,756
`level_script_has_start_type` edges, 70 template definition edges, and 35
template-group edges. Metadata totals preserved on script nodes include 84,326
action-map records, 129,065 UID records, 84,326 action-list entries, 17,410
getter-list entries, 21,917 header-list entries, 42,202 root action entries, and
42,124 linked action entries. Template metadata preserves 1,751 action-map
records. High-signal reference checks verified 4,416 script-to-story edges to
3,135 distinct story keys, 722 script-to-mission-like edges to 393 distinct ids,
1,403 script-to-audio edges to 683 distinct audio keys, 941 script-to-effect
edges to 148 distinct effect keys, 873 script-to-buff edges to 157 distinct buff
ids, 374 script-to-template edges to 27 distinct templates, and 228
script-to-montage edges to 115 distinct montage ids. Template reference checks
add 45 story, 10 audio, 16 effect, 5 buff, and 31 montage edges. This pass makes
script ids, level ownership, template ids, start types, action-map/list counts,
and high-signal story/audio/effect/buff/template/montage references queryable;
it intentionally skips generic key strings and does not emit per-action nodes,
action-body control-flow edges, target semantics, or formula behavior. Example
exact queries:

```bat
python tools\endfield_source_graph.py query 9900010001 --kind level_script
python tools\endfield_source_graph.py query black_c27m1_1_001 --kind story
python tools\endfield_source_graph.py query LST_EnergyPoint_Small_Graph --kind level_script_template
python tools\endfield_source_graph.py query Montage/NPC/Generic/rabbit01/escaped --kind level_script_montage
```

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
