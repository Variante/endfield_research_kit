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

2026-07-01 DialogIdTable registry graph progress: source graph ingestion now
promotes the exact `DialogIdTable` decoded-config entry plus the generated
`export_full/recovered/dialog_id_table_index.json` runtime registry. A fast CN
rebuild to `tmp/source_graph_dialog_registry.sqlite` verified 1,156,410 total
nodes, 2,057,921 edges, and 1,608,598 aliases. New coverage includes 1
`dialog_id_table_config` node, 2 `defines_dialog_id_table` source-file edges
split across Persistent and StreamingAssets, 4,918 `dialog_registry_scene`
nodes and aliases, 4,918 registry-to-story links, 3,589 registered line links,
3,589 line-to-story links, 4,131 registered option links, and 4,131
option-to-story links. Registry data confirms 1,156 scenes with line/trunk
registration, 1,299 scenes with option registrations, and 541 multi-trunk
registered scenes. These edges are runtime registration evidence from
DialogIdTable; they do not replace generated WebUI line order, option placement,
option branch, or timeline route evidence. Example exact queries:

```bat
python tools\endfield_source_graph.py query DialogIdTable --kind dialog_id_table_config
python tools\endfield_source_graph.py query dlg_e1m1_5 --kind dialog_registry_scene
python tools\endfield_source_graph.py query option_dlg_e1m1_5_1_001 --kind option
```

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
2026-07-01 decoded parameter blackboard bridge progress: source graph now runs a
post-decoded-config exact-name bridge from `buff_parameter` and
`skill_parameter` nodes to already-authored `gameplay_blackboard_key` nodes. A
fast CN temp graph build to `tmp/source_graph_parameter_blackboard.sqlite`
verified 214 `buff_parameter_matches_blackboard_key` edges, 357
`skill_parameter_matches_blackboard_key` edges, and 391 distinct blackboard keys
covered by at least one decoded parameter string. Example lookups such as
`atk_scale --kind gameplay_blackboard_key`, `atk_scale --kind buff_parameter`,
and `atb_gain --kind skill_parameter` now connect decoded BuffData/SkillData
string evidence to SkillPatch, potential, and Gameplay blackboard consumers.
This is exact string-key evidence only; it does not prove parameter typing,
formula evaluation, modifier order, or runtime action execution.

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

2026-07-01 LevelConfig/LevelData graph progress: source graph ingestion now
promotes bounded `LevelConfig` and `LevelData` evidence from the WebUI Data
index. A fast CN rebuild to `tmp/source_graph_leveldata.sqlite` verified
1,105,990 total nodes, 1,907,541 edges, and 1,540,158 aliases. New coverage
includes 149 `level_config` nodes collapsed across 290 decoded config files, 810
`level_data` nodes collapsed across 1,593 decoded data files, 68
`level_scene_config` nodes, 17 `level_asset_reference` nodes, 4,354
`level_task_marker` nodes, and 4,986 `level_data_param` nodes. Edge checks
verified 290 `level_config_data_defines_config` edges, 149
`level_config_defines_level` edges, 139 map-id edges, 149 default-scene-config
edges, 1,593 `level_data_file_defines_level_data` edges, 810
`level_has_level_data` edges, and bounded LevelData string-reference edges: 303
level-script refs, 360 story refs, 511 mission-like refs, 26 audio refs, 103
effect refs, 5 buff refs, 347 montage refs, 19 asset-path refs, 136 level refs,
4,635 task-marker refs, and 13,370 parameter-string refs. LevelData string refs
are unique per value per data file and capped by the 512-string scan window.
LevelConfig-to-LevelData path edges are intentionally absent because the raw
LevelConfig payload exposes the path count but not stable path strings in the
current scanner. This pass makes level config/data inventory, level ownership,
default scene config paths, script/story/mission/montage refs, and sampled task
markers queryable without claiming object placement, spawn behavior, or
LevelData control-flow semantics. Example exact queries:

```bat
python tools\endfield_source_graph.py query map01_lv006 --kind level_config
python tools\endfield_source_graph.py query map01_lv006_lv_data_sub_sm1l6m3 --kind level_data
python tools\endfield_source_graph.py query radio_sm1l6m3_1d5_finished --kind story
```

2026-07-01 NPC montage graph progress: source graph ingestion now promotes
`NPCMontageJson` definitions from the WebUI Data index onto the same
`level_script_montage` nodes used by LevelScript and LevelData references. A
fast CN rebuild to `tmp/source_graph_npc_montage.sqlite` verified 1,123,902
total nodes, 1,938,118 edges, and 1,571,706 aliases. New definition coverage
includes 6,800 `npc_montage_data_defines_montage` edges collapsed to 3,392
unique montage tags, 2 `npc_montage_category` nodes, 47 `npc_montage_body`
nodes, and 1,078 `npc_montage_action` nodes. The graph adds 3,392 category
edges, 3,392 body edges, and 3,392 action edges from montage tags, plus
`npc_montage_tag`, `npc_montage_path`, and source data-path aliases. This pass
uses the Data index's exact tail GameplayTag parse and does not decode montage
clip payloads, controller states, animation curves, or runtime playback rules.
Example exact query:

```bat
python tools\endfield_source_graph.py query Montage/NPC/Generic/rabbit01/escaped --kind level_script_montage
```

2026-07-01 AnimationConfig decoded-config progress: source graph ingestion now
promotes bounded `AnimationConfig` evidence from the WebUI Data index. A fast
CN rebuild to `tmp/source_graph_animation.sqlite` verified 1,125,538 total
nodes, 1,941,396 edges, and 1,573,659 aliases after the typed-path classifier
fix. New coverage includes 213 `animation_config_data_defines_config` edges
collapsed to 107 unique `animation_config` nodes, 584 `animation_state` nodes,
315 `facial_morph` nodes, 197 `actor_animation_ref` nodes, 3
`animation_cutscene_ref` nodes, and 1 generic `animation_path_ref` node. Edge
checks verified 1,886 state refs, 339 facial-morph refs, 34 montage refs joined
to `level_script_montage`, 364 actor-animation refs, 14 cutscene-like refs, and
1 sampled skeleton/bone path ref. This pass mirrors the guarded MemoryPack
string scan: member-count 12, up to 640 string hits, and 192 unique sampled
strings. It does not decode controller graphs, blend trees, clip bindings,
animation curves, actor skeletons, or runtime playback conditions. Example
exact queries:

```bat
python tools\endfield_source_graph.py query anim_cfg_abilityEntity_chr_0030_zhuangfy_ult --kind animation_config
python tools\endfield_source_graph.py query A_actor_zhuangfy_battle_skill_ult_03 --kind actor_animation_ref
```

2026-07-01 AtmosphericNpcData decoded-config progress: source graph ingestion
now promotes bounded `NpcAtmosphericDataTable` row evidence from the WebUI Data
index onto `environmental_npc` nodes. A fast CN rebuild to
`tmp/source_graph_atmospheric.sqlite` verified 1,135,357 total nodes,
1,989,414 edges, and 1,592,007 aliases. New row coverage includes 15,452
`atmospheric_npc_table_has_row` file-occurrence edges collapsed to 7,760 unique
`atmospheric_npc_row_key` aliases. Row reference checks verified 7,760
`atmospheric_npc_uses_template` edges, 7,760 `atmospheric_npc_in_level` edges,
7,577 `atmospheric_npc_uses_ai_config` edges to 19 `ai_config` nodes, 4,866
`atmospheric_npc_uses_montage` edges, 2,427
`atmospheric_npc_uses_facial_morph` edges, 994 `atmospheric_npc_in_cluster`
edges to 412 `atmospheric_npc_cluster` nodes, and 615
`atmospheric_npc_uses_env_talk` edges. This pass mirrors the Data index's
row-key boundary scan and capped per-row string scan; it does not decode the
full 109-member row payload, coordinates, placement volumes, schedules,
behavior trees, or playback timing. `envTalk_*` links are modeled as `env_talk`
references, not direct story-line proof unless resolved by other tables. Example
exact queries:

```bat
python tools\endfield_source_graph.py query npc_boy_efstaff_a_01_map01_lv001_data_sub_npc_v1d0_atmospheric_001 --kind environmental_npc
python tools\endfield_source_graph.py query aiconf_npc_normal --kind ai_config
python tools\endfield_source_graph.py query envTalk_map01_lv001_env_27 --kind env_talk
```

2026-07-01 CharInteractPerformCfgs decoded-config progress: source graph
ingestion now promotes high-confidence `CharInteractPerformCfgs` evidence from
the WebUI Data index. A fast CN rebuild to `tmp/source_graph_charinteract.sqlite`
verified 1,136,310 total nodes, 1,990,915 edges, and 1,593,441 aliases after
noisy state/param strings were left payload-only. New coverage includes 318
`char_interact_data_defines_perform_config` file edges collapsed to 159
`char_interact_perform_config` nodes. Typed reference checks verified 83 exact
active-tag edges and 54 scanned status-tag edges to 4 gameplay tags, 102 montage
edges to 82 montage targets, 33 character edges to 7 characters, 4 NPC-template
edges to 3 templates, 146 effect edges to 113 effect targets, 46 intra-family
perform-config refs to 38 targets, 52 asset-path refs to 26 paths, and 13 CCS
refs to 7 paths. This pass parses the strong MemoryPack prefix exactly
(member-count 26, `activeTags`, `allowInheritPerform`, and
`bodyTypeActDataDictCount`) and uses the existing capped body string scan for
prefixed refs. It does not decode the body action dictionaries, timing, IK,
interrupt rules, sub-perform entries, or runtime interaction state machine.
`stateOrParamStrings` are retained in node payloads but intentionally not
promoted to graph edges because they can duplicate actor/effect refs and contain
incidental body strings. Example exact queries:

```bat
python tools\endfield_source_graph.py query CharIntPerform_c28m3_Investigate --kind char_interact_perform_config
python tools\endfield_source_graph.py query CharIntPerform_Camille_RelaxLoop --kind char_interact_perform_config
python tools\endfield_source_graph.py query LD/CCS_LD_c28m3kanjiangjun --kind char_interact_ccs_reference
```

2026-07-01 InteractiveTemplateData exact component graph progress: source graph
ingestion now reuses the existing `decode_interactive_template_memorypack()`
parser from `scripts/build_data_index.py` instead of the truncated compact
`entry["t"]` preview for new interactive semantics. A fast CN rebuild to
`tmp/source_graph_interactive_exact.sqlite` verified 1,140,216 total nodes,
2,020,247 edges, and 1,593,937 aliases. Exact decoded coverage includes 542
`interactive_template_data` source nodes collapsed onto 271 template ids, 3,234
source-qualified `interactive_component` nodes, 79 `interactive_component_type`
nodes, 296 `interactive_property_key` nodes, 33 `interactive_logic_type` nodes,
3 trigger shapes, and 3 guide shapes. Edge checks verified 3,234
template-to-component edges, 3,234 component-to-type edges, 542 first-component
edges, 1,284 parsed-payload type edges, 306 stop-component type edges, 574
category-tag edges, 418 model edges, 488 raw-byte audio edges, 3,840 generic
property-key edges, 3,144 trigger-property edges, 242 perform-property edges,
156 logic-property edges, 448 hittable-property edges, 88 logic-type edges, 262
trigger-shape edges, and 50 guide-shape edges. This pass models exact decoded
component inventory and selected component bodies; it does not prove runtime
interaction control flow, component execution order, formula behavior, or the
meaning of numeric logic/shape enums. The separate collection pass below handles `Json_InteractiveData` collection ids; this component pass does not interpret collection counters.
Example exact queries:

```bat
python tools\endfield_source_graph.py query Core_InteractiveRootComponentData --kind interactive_component_type
python tools\endfield_source_graph.py query destroy_self --kind interactive_property_key
python tools\endfield_source_graph.py query 70 --kind interactive_logic_type
python tools\endfield_source_graph.py query Category/Interactive/Model --kind gameplay_tag
```

2026-07-01 InteractiveData collection graph progress: source graph ingestion
now includes `webui/data/game_data/groups/Json_InteractiveData.json` for the
plain UTF-8 `Json/InteractiveData/Collections.json` files. A fast CN rebuild to
`tmp/source_graph_interactive_collections.sqlite` verified 1,141,176 total
nodes, 2,023,030 edges, and 1,594,876 aliases. New collection coverage includes
935 unique `interactive_collection` nodes, 1,843 `defines_interactive_collection`
source-file edges split as 935 Persistent and 908 StreamingAssets rows, 935
`interactive_collection_in_level` links, 935 `interactive_collection_id`
aliases, and 214 unique linked level ids. The graph preserves `sceneId` and the
21-element `totalCnt` arrays as payload evidence on definition edges, but does
not assign gameplay meaning to those counters. Example exact queries:

```bat
python tools\endfield_source_graph.py query 100000000 --kind interactive_collection
python tools\endfield_source_graph.py query map01_lv002 --kind level
```

2026-07-01 ModelViewStateControllerData decoded-config progress: source graph
ingestion now promotes the bounded `ModelViewStateControllerData` decoder from
`Json_Interactive.json`. A fast CN rebuild to `tmp/source_graph_model_view.sqlite`
verified 1,145,058 total nodes, 2,032,639 edges, and 1,598,757 aliases. New
coverage includes 399 unique `model_view_state_controller` nodes, 798
`defines_model_view_state_controller` source-file edges split evenly across
Persistent and StreamingAssets, 399 model-id links to `model_config_model`, 582
`model_view_clip_ref` nodes, 750 `model_view_animator_name` nodes, 923 exact
clip-asset edges, 823 animator-body clip-ref edges, 619 exact effect-id edges,
872 animator-body effect-ref edges, and 3,385 animator-name edges. The
`model_view_state_controller_asset_entity` join currently verifies 0 edges,
matching the known lean asset-index gap for decoded config model ids. This pass
uses exact prefix fields and the verified model-id/preTick tail, plus the Data
index's capped animator-body string scan; it does not decode animator state
machines, transitions, clip timing, effect playback rules, or emissive/camera
hash semantics. Example exact queries:

```bat
python tools\endfield_source_graph.py query dyn_big_wheel_postmodel --kind model_view_state_controller
python tools\endfield_source_graph.py query A_imod_map02_sfwaterwheel+1_005_01_open_01 --kind model_view_clip_ref
python tools\endfield_source_graph.py query defaultlayer --kind model_view_animator_name
```

2026-07-01 NavMesh decoded-config graph progress: source graph ingestion now
includes `Json_NavMesh.json` and promotes exact raw MemoryPack rows for
`LunaArea` and `NavMeshStateContainer`. A fast CN rebuild to
`tmp/source_graph_navmesh.sqlite` verified 1,157,189 total nodes, 2,060,303
edges, and 1,609,373 aliases. New coverage includes 139 unique `navmesh_area`
nodes with 278 `defines_navmesh_area` source-file edges split evenly across
Persistent and StreamingAssets, 17 owner-qualified `navmesh_area_id` nodes, 6
`navmesh_state_container` nodes with 12 source definition edges, and 569
`navmesh_state_record` nodes with 1,138 source definition edges. State record
kinds split into 57 `bounds36`, 6 `groupedU64Lists`, 144 `idValueLists`, 314
`ints16`, and 48 `ints20` rows. Area owners are `base01_lv001`,
`indie_hdg004`, `map01`, and `map02`; state owners are `base01_lv001`,
`blackbox01_dg001`, `blackbox02_dg001`, `indie_dg006`, `map01`, and `map02`.
Bounds records add 57 owner-qualified area-id refs, and owner-to-level links
produce 3 inferred map edges for `base01`, `map01`, and `map02`. This pass
preserves decoded geometry/state evidence; it does not infer walkability,
pathfinding behavior, state row semantics, or grouped/id-list meanings. Example
exact queries:

```bat
python tools\endfield_source_graph.py query map02:row0000:area12 --kind navmesh_area
python tools\endfield_source_graph.py query map02:12 --kind navmesh_area_id
python tools\endfield_source_graph.py query blackbox01_dg001:f02:r0000 --kind navmesh_state_record
```

2026-07-01 BambooRaftTaskTable decoded-config graph progress: source graph
ingestion now promotes exact MemoryPack rows from
`Json/NonGeneratedConfigs/BambooRaftTaskTable.json`. A fast CN rebuild to
`tmp/source_graph_bamboo.sqlite` verified 1,157,214 total nodes, 2,060,373
edges, and 1,609,399 aliases. New coverage includes 7
`bamboo_raft_task_group` hash nodes, 14 `defines_bamboo_raft_task_group` edges
split evenly across Persistent and StreamingAssets, 13 `quest_task` nodes, 26
`defines_bamboo_raft_task_ref` source edges, 13 `bamboo_raft_group_has_task`
edges, 13 `quest_task_in_mission` prefix links, and 13 duplicate-id matches.
The task ids link to six mission prefixes: `e5m1`, `e6m1`, `e6m4`, `e8m2`,
`sm2l1m1`, and `sm2l1m3`. The row hash and `field0U32` values remain preserved
payload evidence only; this pass does not infer quest ordering, task execution,
or bamboo-raft gameplay mechanics. Example exact queries:

```bat
python tools\endfield_source_graph.py query 1510085735 --kind bamboo_raft_task_group
python tools\endfield_source_graph.py query e8m2_q#10 --kind quest_task
python tools\endfield_source_graph.py query e8m2 --kind mission
```

2026-07-01 GPUISystemConfig damage_text graph progress: source graph ingestion
now promotes exact MemoryPack row, animation, node-name, and filtered UI
resource evidence from `Json/GPUISystemConfig/damage_text.json`. A fast CN
rebuild to `tmp/source_graph_damage_text.sqlite` verified 1,157,317 total
nodes, 2,060,606 edges, and 1,609,499 aliases. New coverage includes 20
`damage_text_style` row nodes, 40 `defines_damage_text_style` source-file edges
split evenly across Persistent and StreamingAssets, 10 `damage_text_animation`
nodes, 58 `damage_text_node_name` nodes, and 8 `damage_text_ui_resource` nodes.
Edge checks verified 22 style-to-animation refs, 143 style-to-node-name refs,
and 23 style-to-`ui_*` resource refs. Numeric placeholders, localized sample
text, and non-`ui_*` resource strings remain payload evidence only; this pass
does not infer UI prefab hierarchy, animation timing semantics, or runtime
combat-text rendering rules. Example exact queries:

```bat
python tools\endfield_source_graph.py query damage_text:row000 --kind damage_text_style
python tools\endfield_source_graph.py query element_fusion_in --kind damage_text_animation
python tools\endfield_source_graph.py query ui_bat_physical_airborne --kind damage_text_ui_resource
```

2026-07-01 LipSync aggregate graph progress: source graph ingestion now includes
`Json_LipSync.json` as aggregate clip evidence only. A fast CN rebuild to
`tmp/source_graph_lipsync.sqlite` verified 1,481,831 total nodes, 2,579,643
edges, and 1,998,807 aliases. New coverage includes 129,732
`defines_lipsync_clip` source-file edges split as 64,920 Persistent and 64,812
StreamingAssets entries, collapsed to 64,920 `lipsync_clip` language/audio
nodes, 4 `lipsync_language` nodes, 64,920 `lipsync_clip_language` edges, 64,920
`lipsync_for_audio` edges, 64,920 `lipsync_clip_key` aliases, and 64,920
`lipsync_audio_id` aliases. Language splits are Chinese 16,248, English 16,224,
Japanese 16,223, and Korean 16,225 unique clips. Source entries sum to
43,043,103 curve records; unique clip nodes sum to 21,553,022 records after
Persistent/StreamingAssets collapse. This pass deliberately avoids per-record
curve nodes and does not infer phoneme/viseme semantics, curve timing, or audio
playability beyond exact audio-stem links. Example exact queries:

```bat
python tools\endfield_source_graph.py query Chinese:au_dlg_c13m1_1_001 --kind lipsync_clip
python tools\endfield_source_graph.py query Chinese --kind lipsync_language
python tools\endfield_source_graph.py query au_dlg_c13m1_1_001 --kind audio
```

2026-07-01 MissionRuntimeAsset graph progress: source graph ingestion now
promotes bounded mission runtime JSON semantics from `Json_MissionRuntimeAsset.json`.
A fast CN rebuild to `tmp/source_graph_mission_runtime.sqlite` verified
1,494,351 total nodes, 2,615,206 edges, and 2,013,397 aliases. New coverage
includes 884 `mission_runtime_asset` nodes, 1,756 source-file definition edges
split as Persistent 884 and StreamingAssets 872, 884 mission links, 813 level
links, 494 reward links, 331 mission-name text links, 324 mission-description
text links, 3,984 mission quest links, 3,984 mission-runtime quest-to-mission
links, 3,334 previous-quest dependency edges, 3,155 objective text links, 55
condition-type nodes with 3,964 quest condition edges, 7 tracking-type nodes
with 3,167 tracking edges, 2,755 tracking scene/level links, 1,134 mission-area
tracking links, 6 action-type nodes with 495 action edges, 345 action narrative
refs, and 579 quest narrative refs. Top condition types are
`GameConditionServerPlaceHolder`, `ReachDestination`, `CheckTalkOptionFinish`,
and `CombineCondition`; top tracking types are `MissionAreaTrackingInfo`,
`NpcProxyTrackingInfo`, `PosTrackingInfo`, and `EntityTrackingInfo`; action
refs are mostly `PlayRadio`. This pass models static mission asset/quest DAG
and authored tracking evidence; it does not prove observed runtime chronology,
condition evaluation, action execution, or exact player-visible mission order.
Example exact queries:

```bat
python tools\endfield_source_graph.py query e8m2:runtime --kind mission_runtime_asset
python tools\endfield_source_graph.py query e8m2_q#10 --kind quest_task
python tools\endfield_source_graph.py query ReachDestination --kind mission_runtime_condition_type
python tools\endfield_source_graph.py query MissionAreaTrackingInfo --kind mission_runtime_tracking_type
```
2026-07-01 MissionRuntimeAsset action-level graph progress: mission runtime
action-map entries now become `mission_runtime_action` nodes instead of only
asset-level action-type counts. A fast CN temp graph build to
`tmp/source_graph_mission_runtime_actions.sqlite` verified 495 collapsed
action nodes, 6 action-type nodes, 95 guide groups, 11 chapter-panel ids, 495
`mission_runtime_has_action` edges, 495 `mission_runtime_action_type` edges,
345 `mission_runtime_action_plays_radio` edges, 69 media-guide-group edges, 64
guide-group edges, 69 guide text edges, 17 chapter-panel edges, and 7 static
`_nextID` action links. Example queries now resolve direct evidence for
`radio_a1m9_2`, `guide_group_connector_intro`, and `chr_0013_aglina_e1` through
specific `actionList[...]` fields. This is static authored action-map evidence;
it does not simulate action execution, condition evaluation, or mission
chronology.

2026-07-01 MissionRuntimeAsset condition graph progress: mission runtime
objective conditions now get `mission_runtime_condition` nodes, typed links to
condition classes, and conservative target edges for high-signal payload fields.
A fast CN temp graph build to `tmp/source_graph_mission_conditions.sqlite`
verified 4,725 condition nodes, 79 condition-type nodes, 4,725
`quest_has_runtime_condition` edges, 4,725 `mission_runtime_condition_type`
edges, 761 nested `condition_has_sub_condition` edges, 263 condition-to-level
edges, 200 `condition_checks_level_script_property` edges, 200 property-key
edges, 63 script-kill level-script edges, 201 composite
`condition_checks_world_entity_script_slot` edges, 149 quest-state checks, 79
mission-state checks, 60 factory-tech checks, 231 item/money count checks, 707
ReachDestination level edges, 707 ReachDestination mission-area edges, and 449
TalkOptionFinish story refs. Example queries:

```bat
python tools\endfield_source_graph.py query c13m1:runtime:c13m1_q#1:objective:0:CheckLevelScriptPropertyBool:aacc615d --kind mission_runtime_condition
python tools\endfield_source_graph.py query 22800970011:30001 --kind world_entity_script_slot
python tools\endfield_source_graph.py query dlg_a1m10_1 --kind story
```

These edges expose authored runtime condition references, including nested
`subConditions`; they do not evaluate comparers, infer enum names, treat
`finishId = -1` as a concrete option, or prove observed mission chronology.
2026-07-01 ScriptTaskExtraInfoTable display-metadata graph progress: the
`GameplayConfigScriptTaskExtraInfoTable` handler now also ingests the larger
`Json/GameplayConfig/ScriptTaskExtraInfoTable.json` entries in `Json_GameplayConfig.json`,
not only the small wrapper group. A fast CN temp graph build to
`tmp/source_graph_script_task_extra.sqlite` verified 536 collapsed
`level_script_task_extra` rows, 536 `level_script_task_uid` nodes, 671
`level_script_task_objective` nodes, 1,052 source definition edges, 536 links to
levels, 536 links to `level_script` nodes, 638 objective text edges, 285 title
text edges, 7 single-description text edges, 2 progress-display-mode nodes, and
3 track-point-type nodes. Example queries now resolve
`map01_lv007:2800200002:0174178d`, `dungeon_train_train02_title`, and
`9900020001` to concrete task-display metadata. This is authored UI/tracking
text metadata; it does not prove objective formulas, mission areas, quest-task
identity, or runtime completion logic.

2026-07-01 AIConfig graph progress: source graph ingestion now promotes exact
enemy-template preload mappings from `Json_AIConfig.json`
`EnemyTemplateDataSummary.json`. A fast CN rebuild to
`tmp/source_graph_aiconfig.sqlite` verified 1,494,436 total nodes, 2,615,445
edges, and 2,013,635 aliases. New coverage includes 78 `enemy_data_asset`
nodes, 156 `ai_config_preloads_enemy_template` file-to-template edges split
as Persistent 78 and StreamingAssets 78, 78 deduplicated
`enemy_template_preloads_data_asset` edges, 78 `enemy_data_asset_path`
aliases, and 78 `enemy_data_asset_stem` aliases. The template-to-asset edge
deduplicates identical Persistent/StreamingAssets mappings into one relation.
This is preload-path evidence only; it does not prove AI behavior trees,
spawn behavior, renderable model binding, or asset presence in the lean asset
index. Example exact queries:

```bat
python tools\endfield_source_graph.py query eny_0007_mimicw --kind enemy_template
python tools\endfield_source_graph.py query data_eny_0007_mimicw --kind enemy_data_asset
```

2026-07-01 MapConfig graph progress: source graph ingestion now promotes
exact map config JSON from `Json_MapConfig.json`. A fast CN rebuild to
`tmp/source_graph_mapconfig.sqlite` verified 1,495,527 total nodes,
2,617,649 edges, and 2,015,082 aliases. New coverage includes 139
`map_config` nodes from 270 source-file definition edges split as
Persistent 139 and StreamingAssets 131, 139 config-to-map links, 48
`map_domain` nodes, 68 `map_streaming_asset` path nodes, 197 unique
numeric `map_config_has_level_id` edges with the original 31,992 grid-cell
level id counts preserved in config node data, 149 `levelStrIds` links, 99
`map_scene_state` nodes, 39 `map_variable` nodes with 78 definition edges,
4 condition-type nodes with 53 scene-condition type edges, 32 quest-task
condition refs, 5 mission condition refs, and 9 map-variable condition
refs. This pass models static authored map config metadata and condition
references; it does not prove map streaming behavior, scene-state
evaluation, grid placement semantics, or UI map rendering. Example exact
queries:

```bat
python tools\endfield_source_graph.py query base01_lv001 --kind map_config
python tools\endfield_source_graph.py query base01_lv001:default --kind map_scene_state
python tools\endfield_source_graph.py query dung02_bdg002:Nefarp_human --kind map_variable
```

2026-07-01 GameplayConfigScriptTaskExtraInfoTable graph progress: source
graph ingestion now promotes the small `LevelScriptTaskExtraInfoTable` JSON
from `Json_GameplayConfigScriptTaskExtraInfoTable.json`. A fast CN rebuild
to `tmp/source_graph_script_task_extra.sqlite` verified 1,495,542 total
nodes, 2,617,699 edges, and 2,015,102 aliases. New coverage includes 4
`level_script_task_extra` nodes, 8 source-file definition edges split as
Persistent 4 and StreamingAssets 4, 4 level links to `map01_lv007`, 1
title text link, and 4 objective text links covering `task_race_obj_1`,
`task_energy_point`, `task_energy_point_mini`, and
`world_challenge_energy_point_desc`. This pass indexes static task display
metadata and tracking text keys; it does not prove level-script execution,
objective progress logic, or runtime challenge state. Example exact queries:

```bat
python tools\endfield_source_graph.py query map01_lv007:2800200002:0174178d --kind level_script_task_extra
python tools\endfield_source_graph.py query task_energy_point --kind i18n_text
```

2026-07-01 LevelMountPoint graph progress: source graph ingestion now
promotes static mount-point leaves from `Json_LevelMountPoint.json`. A fast
CN rebuild to `tmp/source_graph_level_mount_point.sqlite` verified
1,495,652 total nodes, 2,618,076 edges, and 2,015,393 aliases. New coverage
includes 92 `level_mount_point` nodes, 184 source-file definition edges split
as Persistent 92 and StreamingAssets 92, 92 level links split as 46 each for
`base01_lv001` and `base01_lv003`, 7 `level_mount_type` nodes, and 92
type links. Type splits are WeaponWall 44, MedalWall 20, SpaceshipSummon
10, CabinPos 8, CabinTeleport 6, CharacterWall 2, and SpaceshipScreen 2.
Each mount point preserves its level-qualified tree path plus position and
rotation payloads. This pass indexes static authored mount transforms; it
does not prove runtime attachment rules, cabin interaction behavior, or
display/spawn usage. Example exact queries:

```bat
python tools\endfield_source_graph.py query base01_lv001:WeaponWall/Claymores/0 --kind level_mount_point
python tools\endfield_source_graph.py query WeaponWall --kind level_mount_type
```

2026-07-01 LevelGenForRuntime graph progress: source graph ingestion now
promotes static factory generation data from `Json_LevelGenForRuntime.json`.
A fast CN rebuild to `tmp/source_graph_level_gen.sqlite` verified
1,498,231 total nodes, 2,622,475 edges, and 2,018,261 aliases. New coverage
includes 70 `level_gen_parent_data` nodes, 267 `level_gen_doodad_group`
nodes from 534 Persistent/StreamingAssets definition edges, 1,967
`level_gen_doodad_logic` nodes, 267 center links, 1,700 outer links, 56
doodad map-mark links, 136 source-file factory-region definition edges
collapsed to 68 runtime region refs, 202 `factory_mine` nodes from 404
source-file definition edges, 202 region-to-mine links, 202 mine-to-doodad
logic links, 4 mine proto nodes, and 202 mine-to-item output links. Mine
outputs are `item_originium_ore` 84, `item_iron_ore` 73,
`item_quartz_sand` 23, and `item_copper_ore` 22. This pass indexes
static authored factory/doodad generation metadata and mine output refs; it
does not prove runtime resource refresh formulas, gathering logic, factory
simulation behavior, or map-mark visibility. Example exact queries:

```bat
python tools\endfield_source_graph.py query 200060035 --kind level_gen_doodad_group
python tools\endfield_source_graph.py query region_301:200060537 --kind factory_mine
python tools\endfield_source_graph.py query item_originium_ore --kind item
```

2026-07-01 UILevelMapLoadConfig graph progress: source graph ingestion
now promotes bounded UI map-load metadata from `Json_UILevelMapLoadConfig.json`.
A fast CN rebuild to `tmp/source_graph_ui_level_map.sqlite` verified
1,498,815 total nodes, 2,623,975 edges, and 2,019,120 aliases. New
coverage includes 17 `ui_level_map_config` nodes from 34 source-file
definition edges plus 34 load-list refs, 220 `ui_map_static_element` nodes
from 440 source-file definition edges, 7 static-element type nodes, 220
config-to-static-element edges, 54 target-level refs, 2 region-level refs,
157 static-element text refs, 58 `ui_map_tier_name` nodes from 116
source-file definition edges, and 58 tier text refs. Static-element type
splits are 2:157, 1:30, 7:24, 4:5, 3:2, 5:1, and 6:1. Chunk/grid/mist
and tier geometry arrays are preserved as config payload counts only; this
pass does not prove UI map rendering, fog/mist reveal behavior, chunk LOD
selection, or coordinate projection. Example exact queries:

```bat
python tools\endfield_source_graph.py query map01_lv001 --kind ui_level_map_config
python tools\endfield_source_graph.py query map01_lv001_se_1 --kind ui_map_static_element
python tools\endfield_source_graph.py query scene_map01_lv001_sub01_location_tips_10 --kind i18n_text
```

2026-07-01 GameplayConfig map/level lookup graph progress: source graph
ingestion now promotes four decoded text JSON lookup tables from
`Json_GameplayConfig.json`: `MapIdTable`, `LevelBasicInfoTable`,
`LevelShortIdTable`, and `MapBriefInfoTable`. A fast CN rebuild to
`tmp/source_graph_gameplay_map_level.sqlite` verified 1,499,464 total nodes,
2,627,034 edges, and 2,020,809 aliases. New coverage includes 270
`gameplay_config_map_id_table_defines_map` source-file edges split as
Persistent 139 and StreamingAssets 131; 149 `level_basic_info` nodes from
290 source-file definition edges split as Persistent 149 and StreamingAssets
141; 149 level links, 149 level-config path links, 149 domain links, 5 map-UI
links, 5 region-UI links, and 3 factory-area links; 21 short-id scene nodes,
86 `level_short_id` nodes, 42 source-file scene-definition edges, and 86
scene-to-short-id edges; plus 142 `map_brief_info` nodes, 211
`map_sublevel_brief` nodes, 276 source-file map-brief definition edges split
as Persistent 142 and StreamingAssets 134, 139 resolved map links, 211
sublevel-to-map links, and 1,009 sublevel enemy refs. Numeric map ids from
`MapBriefInfoTable` are joined to `map` nodes only when `MapIdTable` resolves
them; unresolved numeric rows stay as brief-info nodes. Sublevel ids are kept
as map-local subdata ids, not forced into level ids. `LevelMapMark`,
`MapRegionTable`, and `MinePointTeamTable` remain a separate placed-map pass;
their top-level numeric keys should not be treated as map ids. Example exact
queries:

```bat
python tools\endfield_source_graph.py query map01_lv001 --kind level_basic_info
python tools\endfield_source_graph.py query map01_lv001:2100000031 --kind level_short_id
python tools\endfield_source_graph.py query map01 --kind map_brief_info
python tools\endfield_source_graph.py query map01:200000000 --kind map_sublevel_brief
```

2026-07-01 GameplayConfig placed-map graph progress: source graph ingestion
now promotes decoded `LevelMapMark`, `MapRegionTable`, and
`MinePointTeamTable` text JSON from `Json_GameplayConfig.json`. A fast CN
rebuild to `tmp/source_graph_gameplay_map_placement.sqlite` verified 1,502,251
total nodes, 2,642,324 edges, and 2,026,314 aliases. New coverage includes
1,993 unique `map_mark` nodes from 3,915 source-file mark definitions split as
Persistent 1,958 and StreamingAssets 1,957; 268 `map_region` nodes from 536
source-file region definitions; and 46 `factory_mine_team` nodes from 92
source-file team definitions. Region evidence adds 268 level-region links, 98
tier-region links, 100 mist-hide links, and 11 group-region links. Mark
evidence adds 1,877 region-derived level links, 1,803 mist-region links, 884
tier-region links, 10 detail type nodes, 31 visibility type nodes, 109 item
refs, 42 reward refs, 79 teleport validation refs, 122 system-instance refs,
370 logic refs, 42 activity refs, 35 activity-stage refs, 6 settlement refs, 103
minigame refs, and 300 core-doodad logic refs from the detail and visibility
payloads. Mine-team evidence adds 46 mark links, 46 level links, and 150 doodad
logic refs. Geometry arrays stay as compact payload counts, and the top-level
numeric keys are preserved as placement/group keys, not treated as map ids. This
is static placed-map evidence; it does not prove live visibility, activation,
fog reveal, resource refresh, or runtime map rendering behavior. Example exact
queries:

```bat
python tools\endfield_source_graph.py query 200060037 --kind map_mark
python tools\endfield_source_graph.py query mark_p_minepoint_team200060037 --kind factory_mine_team
python tools\endfield_source_graph.py query map01_lv002_region_tier_001 --kind map_region
python tools\endfield_source_graph.py query TpForMap_ent_200001237 --kind teleport_point
```

2026-07-01 GameplayConfig text WorldEntityRegistry graph progress: source graph
ingestion now promotes decoded text `Json/GameplayConfig/WorldEntityRegistry.json`
from `Json_GameplayConfig.json`, separate from the compact MemoryPack
`Json_GameplayConfigWorldEntityRegistry.json` pass. A fast CN rebuild to
`tmp/source_graph_world_entity_text.sqlite` verified 1,538,463 total nodes,
2,729,132 edges, and 2,084,083 aliases. New coverage includes 2
`world_entity_text_registry` source roots, 15,083 collapsed
`world_entity_instance` nodes from 30,129 Persistent/StreamingAssets source
rows, 2,591 `world_entity_script_slot` nodes from 5,093 source slot rows, 77
`world_entity_config` nodes, 154 `world_entity_config_property` nodes, 1,646
`npc_proxy_brief` nodes, and 1,646 `world_entity_segment` nodes. The pass adds
15,083 instance-to-compact-world-entity links, 1,642 instance enemy links, 1,613
instance enemy-template links, 8,740 instance interactive-detail links, 269
fallback detail links, 2,591 script-slot-to-level-script links, 648 script-slot
enemy links, 1,840 script-slot interactive-detail links, 154 config-to-property
links, 77 config-to-instance links, 1,646 proxy-to-segment links, and 101 proxy
segment-to-instance links. Position, rotation, and config property arrays stay
as compact payloads; numeric prefixes are not interpreted as map or level ids.
This is static placement/registry evidence, not runtime spawn, visibility,
lifetime, or script execution proof. Example exact queries:

```bat
python tools\endfield_source_graph.py query 200001183 --kind world_entity_instance
python tools\endfield_source_graph.py query 200000033:30001 --kind world_entity_script_slot
python tools\endfield_source_graph.py query 200001237 --kind world_entity_config
python tools\endfield_source_graph.py query xiaona_map01_e1m7cage --kind npc_proxy_brief
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

2026-07-01 attribute consumer graph progress: source graph now links authored
attribute consumers to `AttributeMetaTable` and mapped stat-property keys. A
fast CN temp graph build to `tmp/source_graph_attribute_consumers.sqlite`
verified 83,636 `character_base_attribute_meta` edges, 29
`character_main_attribute_meta` edges, 29 `character_sub_attribute_meta` edges,
51 `potential_talent_modifies_attribute_meta` edges, 28
`ability_entity_sets_stat_property` edges, 86
`attribute_display_entry_uses_modifier_property` edges, and 40
`attribute_meta_has_stat_property` edges from the maintained `STAT_ATTR_KEYS`
mapping. Example queries now resolve `chr_0013_aglina`, `attr_39`, and
`chr_0005_chen_potential_2` to explicit stat metadata evidence. This indexes
authored attribute values and modifiers; it does not infer runtime formula
execution, modifier order, or display-modifier semantic identity.

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

2026-07-01 postmodel asset entity bridge progress: asset ingestion now also
groups exported model files whose normalized stem ends in `_postmodel` into
`asset_entity` nodes, preserving the existing LOD grouping path. Decoded model
references try exact normalized bases plus append-only `_postmodel` candidates,
then the existing delimiter-boundary entity-prefix match. A fast CN temp graph
build to `tmp/source_graph_asset_bridge.sqlite` verified 10,678
`asset_entity` nodes, including 213 new postmodel entity groups, and recovered
215 `model_config_asset_entity`, 82 `interactive_template_asset_entity`, and 86
`model_view_state_controller_asset_entity` edges. Smoke queries verified direct
links for `chr_0012_avywen_postmodel`, `int_collection_common`, and
`int_base01_autodoor_1`. This is exact exported model/postmodel evidence; it
intentionally does not remap names such as `abilityentity_*` to unrelated
`actor_*`, `monster_*`, or loose substring asset families.
2026-07-01 weapon renderable bridge progress: Gameplay weapon nodes now link
directly to renderable `asset_entity` nodes when the weapon `modelPath` stem
matches an entity base or entity-base prefix. A fast CN graph rebuild verified
132 `has_gameplay_asset_entity` edges across 71 weapon sources and 132
renderable entity targets; the only weapon without a renderable entity candidate
is `wpn_lance_0003` (`寻路者道标`). The query
`python tools\endfield_source_graph.py used-by wpn_sword_0019_01 --kind asset_entity`
now surfaces `weapon:wpn_sword_0019` before raw asset-detail rows.

2026-07-01 gameplay effect asset-name match progress: source graph builds a
final strict name-match bridge from `gameplay_effect` nodes to exported `asset`
nodes whose asset stem matches `<effectKey>_p[0-9A-F]{16}` after stripping the
exported PathID suffix. A fast CN graph build to
`tmp/source_graph_effect_assets.sqlite` verified 1,090,873 nodes, 1,880,527
edges, and 1,521,156 aliases, including 232
`effect_name_matches_export_base_asset` edges from 223 gameplay-effect nodes to
232 concrete asset nodes. The matched assets split into 225 `model` entries and
7 `json` entries. Direct full-stem effect-to-asset alias matches remain zero,
and loose prefix matches are intentionally excluded because they create
collisions such as `P_agtrinit_skill13` vs `P_agtrinit_skill132_*`. These edges
are filename/export-suffix evidence for browsing, not proof of runtime effect
dependency.

2026-07-01 visual token asset bridge progress: source graph now links typed
semantic nodes with top-level authored visual tokens to exported image assets by
strict suffix-normalized stem match. A fast CN temp graph build to
`tmp/source_graph_visual_tokens_semantic.sqlite` verified 32,422
`uses_icon_asset` edges and 340 `uses_visual_asset` edges across 8,008 semantic
source nodes, 1,507 distinct visual tokens, and 10,620 exported image assets.
The largest source kinds are item, gameplay skill level, NPC group, PRTS first
level, SNS chat, system jump, scene collectable, spaceship skill, map-mark type,
and activity banner nodes. Generic `table_row` nodes are intentionally excluded
so lookups prefer domain records. Example queries:

```bat
python tools\endfield_source_graph.py query achv_adv_tundra_box_1 --kind item
python tools\endfield_source_graph.py query beginner_gacha --kind activity_banner
python tools\endfield_source_graph.py used-by StreamingAssets/Sprite/new_journey_pC8860EAECF821AC9.png
```

These edges preserve the source field path, token, normalized base, asset stem,
and asset path. They are exact export-name evidence for browsing, not proof that
the runtime UI loader chooses a specific Sprite/Texture2D duplicate.

2026-07-01 FMV binding graph progress: source graph now ingests
`export_full/recovered/video_bindings.json` as first-class video/story evidence.
A fast CN graph build to `tmp/source_graph_video_bindings.sqlite` verified 29
`fmv_binding` nodes, 29 `fmv_clip` nodes, 29 `defines_fmv_binding` edges, 29
`fmv_binding_targets_story` edges, 29 `fmv_binding_in_mission` edges, 84
`fmv_binding_uses_video` edges, 29 `fmv_binding_timeline_clip` edges, 58
`fmv_binding_source_file` edges, 58 `fmv_binding_playable_pathid` edges, and
110 `unbound_video_candidate` edges. Example queries:

```bat
python tools\endfield_source_graph.py query cs_video_dlg_e10m1_1 --kind fmv_binding
python tools\endfield_source_graph.py query StreamingAssets-structured/Data/Video/PC/Narrative/Cutscene/cs_video_dlg_e10m1_1.mp4 --kind video
```

The binding pass preserves Timeline playable and MissionRuntime source-file
links, playable PathID values, mission hints, story fallback hints, and the
`sceneIsHint` caveat. The 110 unbound videos are diagnostic candidates only;
they are not promoted to story links.

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


2026-07-01 runtime option-route audit graph refs: `tools/endfield_source_graph.py` now ingests generated nearby Runtime Jump option-route audit reports matching `reports/runtime_jump_option_route_audit_CN*_nearby*.json`. A fast CN graph build to `tmp/source_graph_runtime_option_audit.sqlite` verified 4 `runtime_option_route_audit_group` nodes, 3 `runtime_option_route_conflict` nodes, 18 `runtime_audit_expected_first_line` edges, 10 `runtime_audit_runtime_first_line` edges, 10 `runtime_audit_directional_first_line` edges, 7 `has_runtime_route_conflict` edges, 3 `runtime_audit_has_conflict` edges, and 7 `runtime_audit_nearby_jump` edges. The ingester links audited story option groups to expected/runtime/directional first-line candidates, conflict records, candidate-owner options, and nearby runtime jump clips by `assetTrack` when available.

`reports/source_graph/option_branch_gaps.json` now appends audit-only scene entries when runtime audit evidence exists outside the inferred-anchor report. The validated rows surface `dlg_c28m3_10`, `dlg_c28m3_23`, `dlg_e6m1_10`, and `dlg_e6m4_14` with runtime audit group/conflict/jump counts plus all contributing audit report paths. These edges remain generated audit evidence from `runtime_jump_option_route_audit`, not automatic WebUI override promotions.


2026-07-01 settings semantics graph refs: `tools/endfield_source_graph.py` now ingests `SettingTabTable`, `QualitySubSettingTable`, `QualitySubSettingOptionTable`, `GamepadSettingItemTable`, and `GamepadImplicitSettingItemTable` as the `structured_settings` dataset. A fast CN graph build to `tmp/source_graph_settings_semantics.sqlite` verified 8 `setting_tab` nodes, 139 `setting_item` nodes, 27 `setting_quality_subsetting` nodes, 55 `setting_quality_option` nodes, 7 `setting_gamepad_item` nodes, 5 `setting_gamepad_implicit_item` nodes, 31 `setting_gamepad_option` nodes, 9 `setting_text_key` nodes, 116 `setting_function` nodes, 88 `input_action` nodes, 5 `input_scope` nodes, and 10 `input_key` nodes.

Validated settings edges include 100 `setting_tab_has_item`, 92 `setting_item_references_action`, 74 `setting_item_has_key_scope`, 27 `quality_subsetting_extends_setting_item`, 55 `setting_quality_option_text`, 40 `gamepad_setting_references_action`, 41 `gamepad_option_uses_input_key`, 6 `gamepad_setting_uses_input_key`, 14 `setting_item_mutex_setting`, 120 setting function-reference edges, and 255 setting-related i18n text edges across the specific setting text edge kinds. Query smoke tests passed for `gameSetting_video`, `battle_attack_start`, and `sub_anisoLevel_x16`. This covers a previously unmodeled Settings/I18n island without promoting platform, region, or channel filters into content categories.

2026-07-01 tag taxonomy graph refs: `tools/endfield_source_graph.py` now ingests `TagGroupDataTable` and `TagDataTable` as the `structured_tag_taxonomy` dataset, separate from activity, enemy, and gameplay tag systems. A fast CN graph build to `tmp/source_graph_tag_taxonomy.sqlite` verified 77 canonical `tag` nodes, 6 `tag_group` nodes, 77 `defines_tag`, 6 `defines_tag_group`, 77 `tag_belongs_to_group`, 77 `tag_name_text`, 6 `tag_group_name_text`, 6 `tag_group_desc_text`, and 69 `character_tag_resolves_to_tag` edges. The 8 `hideTag` rows are preserved as tag data instead of being excluded. Query smoke tests passed for `tag_disposition_active`, `tag_group_disposition`, and the overlapping character tag `tag_activity_universe`.


2026-07-01 character support i18n bridge refs: existing `CharacterTagDesTable` and `DungeonCharTutorialStepTable` graph nodes now link to their text records instead of only storing compact text in node data. A fast CN graph build to `tmp/source_graph_character_support_i18n.sqlite` verified 104 `character_tag_desc_text` edges, 336 `tutorial_step_desc_text` edges, 336 `tutorial_step_icon_desc_text` edges, and 776 `uses_i18n_text` edges from those two sources. Query smoke tests passed for `aglina_stage_1_step_01` and `chr_0004_pelica:tag_expert_oripow`.


2026-07-01 attribute display i18n bridge refs: existing attribute display/filter graph entries now link to their text records. A fast CN graph build to `tmp/source_graph_attribute_i18n.sqlite` verified 150 `attribute_display_entry_text` edges and matching `uses_i18n_text` edges: 109 from `AttributeShowConfigTable`, 20 from `CompositeAttributeShowConfigTable`, and 21 from `AttributeFilterTable`. Query smoke tests passed for `attribute:1:0` and `filter:equipExtraAttr:0`.

2026-07-01 UI label graph refs: `tools/endfield_source_graph.py` now ingests 16 compact UI label/config dictionaries as the `structured_ui_labels` dataset: battle-pass task labels, settlement tags, share channels, social sign tabs/signs, factory blueprint and ingredient tag labels, cash-shop pack tags, money gain/consume source labels, report reasons, system menu labels, tower-defense groups, bloc labels, and character battle tags. A fast CN graph build to `tmp/source_graph_ui_labels.sqlite` verified 243 `ui_label` nodes, 243 `defines_ui_label` edges, 297 specific UI-label text edges, 297 matching `uses_i18n_text` edges, 25 social sign tab edges, 20 factory blueprint tag-type edges, and 39 tag/character-tag reference edges. Query smoke tests passed for `BattlePassTaskLabelTable:bp_01_task_label_activity`, `SocialBuildingSignTable:1`, `FactoryBlueprintTagTable:101`, and `system_activity_center`.

2026-07-01 tag text bridge refs: existing activity and shop tag graph nodes now use specific label text edge kinds, and `EnemyTagTable` is ingested directly through combat semantics instead of relying only on generated gameplay output. A fast CN graph build to `tmp/source_graph_tag_text_bridges.sqlite` verified 23 `activity_tag_name_text` edges, 6 `shop_goods_tag_name_text` edges, 5 `enemy_tag_text` edges, and 5 `defines_enemy_tag` edges. Query smoke tests passed for `activity_tag_benefits`, `crafts`, and `tag_boss`.

2026-07-01 weapon semantics graph refs: `tools/endfield_source_graph.py` now ingests `WeaponBasicTable`, weapon upgrade/sum/breakthrough/talent templates, weapon potential-up items, and weapon EXP items as the `structured_weapon_semantics` dataset while reusing the existing `weapon` node kind. A fast CN graph build to `tmp/source_graph_weapon_semantics.sqlite` verified 71 `defines_weapon` edges, 71 `weapon_name_text`, 71 `weapon_desc_text`, 21 `weapon_upgrade_template` nodes, 21 `weapon_upgrade_sum_template` nodes, 20 `weapon_breakthrough_template` nodes, 2 `weapon_talent_template` nodes, 71 each of `weapon_uses_upgrade_template`, `weapon_uses_breakthrough_template`, and `weapon_uses_talent_template`, 137 `weapon_has_skill_entry`, 71 `weapon_has_potential_skill`, 200 `weapon_breakthrough_requires_item`, 16 `weapon_potential_requires_item`, and 3 `defines_weapon_exp_item` edges. All 208 weapon skill edges target `gameplay_skill` nodes. Smoke tests passed for `wpn_claym_0003`, `weapon_breakthrough_456star_D_1`, and `weapon_upgrade_curve_4star_1`.

2026-07-02 scene collectable text/interactive refs: existing `SceneCollectableItemTable` graph nodes now link nested `infoLabel` text ids, expose `imagePath` stems for the visual-token bridge, and post-link collectables to real `interactive_object` / `interactive_template` nodes after decoded configs are ingested. A fast CN graph build to `tmp/source_graph_scene_collectable_text.sqlite` verified 37 `scene_collectable` nodes, 32 `scene_collectable_info_text` edges plus matching `uses_i18n_text`, 74 collectable `asset_stem` aliases, 10 item `asset_stem` aliases from the table, 296 `uses_visual_asset` edges from collectables, and 19 each of `scene_collectable_uses_interactive_object` / `scene_collectable_uses_interactive_template`. Smoke tests passed for `indie_dg007:int_campfire_v2:0`, text id `-1191669540078518252`, and `interactive_object:int_collection_piece`.

2026-07-02 achievement text bridge refs: existing achievement graph nodes now expose specific text edge kinds instead of only generic `uses_i18n_text` links. A fast CN graph build to `tmp/source_graph_achievement_text.sqlite` verified 8 `achievement_category_name_text`, 8 `achievement_group_name_text`, 114 `achievement_name_text`, 156 `achievement_level_complete_text`, and 200 `achievement_condition_desc_text` edges; `achievement_desc_text` is currently 0 because the structured `desc` fields are id `0`. Smoke tests passed for `achv_adv_tundra_box`, `achv_adv_tundra_box:level:1`, and `achv_type_adventure`.

2026-07-02 item economy text refs: existing item economy graph nodes now expose role-specific item text edges and `ItemGatherTextTable` is part of `structured_item_economy`. A fast CN graph build to `tmp/source_graph_item_text.sqlite` verified 2,348 `item_name_text`, 2,296 `item_desc_text`, 2,174 `item_deco_desc_text`, 862 `item_no_obtain_hint_text`, 91 `item_type_name_text`, 10 `item_showing_type_name_text`, 42 `item_gather_desc_text`, 42 `defines_item_gather_text`, and 42 `item_gather_text_domain` edges. The item family produced 7,644 generic `uses_i18n_text` edges from `item`, `item_type`, `item_showing_type`, and `item_gather_text` nodes. Smoke tests passed for `achv_adv_tundra_box_1`, item type `1`, and `item_drop_agfly_1`.

2026-07-02 system tips/errors graph refs: `tools/endfield_source_graph.py` now ingests `ErrorCodeTable`, `LoadingTipsTable`, `HyperlinkTextTable`, common/dungeon/enemy/training death tips, and `BattlePassForecastTipTable` as `structured_system_tips`. A fast CN graph build to `tmp/source_graph_system_tips.sqlite` verified 614 `error_code`, 144 `loading_tip`, 105 `hyperlink_text`, 195 `death_tip`, 3 `battlepass_forecast_tip`, and 31 `wiki_entry` nodes; 599 `error_code_text`, 144 each of loading tip title/body text, 105 each of hyperlink name/desc text, 259 `death_tip_text`, 3 each of battle-pass forecast text1/text2, 32 `hyperlink_jumps_to_wiki`, 86 `death_tip_related_enemy`, 82 `death_tip_related_dungeon`, and 1,362 system-tip `uses_i18n_text` edges. Smoke tests passed for error code `-1`, `tips_adventure_1`, `adv.electricFence`, `DungeonDeathTips:dung01_actmonster01`, and `forecasttip_activity_common`.


2026-07-02 wiki/tutorial graph refs: `tools/endfield_source_graph.py` now ingests the structured wiki and tutorial tables as `structured_wiki`. A fast CN graph build to `tmp/source_graph_wiki_semantics.sqlite` verified 6 `wiki_category`, 56 `wiki_group`, 1,107 `wiki_entry`, 308 `wiki_tutorial`, 527 `wiki_tutorial_page`, 118 `wiki_limited_guide`, and 69 `wiki_craft_ref` nodes. Validated edge coverage includes 6 category-name text links, 56 category-to-group links, 1,105 domain-to-entry links, 1,105 defined wiki entries, 434 wiki entry description links, 1,105 group-to-entry links, 724 item refs, 73 enemy refs, 527 tutorial page title links, 527 tutorial page content links, 1,054 tutorial-to-page links, 455 page-to-entry refs, 118 limited-guide entry links, 114 craft jump refs, 2 default craft item refs, and 64 enemy drop item refs. Smoke tests passed for `wiki_type_building`, `wiki_eny_0007_mimicw`, `wiki_tut_adv_accelerate_mushroom_1`, `item_bottled_food_1`, and `eny_0007_mimicw`.

This turns wiki categories, encyclopedia entries, tutorial pages, limited guides, craft jumps, and wiki enemy-drop dictionaries into queryable semantic evidence instead of leaving them as mostly disconnected table rows or hyperlink-only wiki ids.

2026-07-02 gacha pool graph refs: `tools/endfield_source_graph.py` now ingests the character/weapon gacha pool family as `structured_gacha`, including character info, character pools, pool content, pool types, character and weapon presets, weapon pools, ticket-to-pool maps, entry recommendations, and weapon refresh offers. A fast CN graph build to `tmp/source_graph_gacha_semantics.sqlite` verified 26 `gacha_char_info`, 10 `gacha_char_pool`, 4 `gacha_char_pool_type`, 14 `gacha_weapon_pool`, 1 `gacha_weapon_pool_type`, 1 `gacha_recommendation`, 4 `gacha_recommendation_group`, 1 `gacha_recommendation_rule`, and 1 `gacha_refresh_rule` nodes. Validated edge coverage includes 210 character-pool membership edges, 532 weapon-pool membership edges, 9 featured character edges, 14 featured weapon edges, 13 character-ticket-to-pool edges, 1 weapon-ticket-to-pool edge, 23 initial/perfect character weapon links, 92 perfect equipment links, 64 weapon perfect-gem links, 9 pool cost item edges, 24 pool name text links across character/weapon pools, and 3 refresh-rule shop-goods edges. Smoke tests passed for `joint_1_2_2`, `weaponbox_constant_2`, `item_ticketgacha_joint_single_lt_1_2_2`, `beginnerPool`, and direct `chr_0007_ikut` gacha preset edges.

This models authored pool membership, tickets, display text, featured entries, presets, and refresh offers as queryable evidence. It does not simulate live gacha probability execution or server-side guarantee state.

2026-07-02 game mechanic graph refs: `tools/endfield_source_graph.py` now ingests `GameMechanicCategoryTable`, `GameMechanicGroupTable`, `GameMechanicTable`, `GameMechanicConditionTable`, `GameMechanicGroupByConditionTable`, and `WorldGameMechanicsDisplayInfoTable` as `structured_game_mechanics`. A fast CN graph build to `tmp/source_graph_game_mechanics.sqlite` verified 28 `game_mechanic_category`, 9 `game_mechanic_group`, 480 `game_mechanic`, 249 `game_mechanic_condition`, 8 `game_mechanic_condition_type`, 1 `game_mechanic_type`, and 5 `world_game_mechanic_display` nodes. Validated edge coverage includes 438 defined mechanics, 438 category links, 498 mechanic-condition links, 395 mechanic name text links, 332 mechanic description text links, 155 condition description links, 126 group membership links, 9 conditional child-mechanic links, 9 group first-pass rewards, 245 mechanic reward edges across normal/first-pass/extra/hunter reward fields, 296 string-parameter mechanic refs, 5 world display level links, 148 world display enemy-level edges, and 122 world display item-drop edges. Smoke tests passed for `world_energy_point01`, `activity_high_difficulty_condition_s1_01s`, and `dungeon_bossrush`, including direct grade/level payload checks on world-energy enemy edges.

This closes a gameplay-mode/instruction-table gap by making authored mechanic categories, groups, conditions, rewards, display enemies/items, and level placement queryable. Condition parameter refs remain static source-table evidence and are not proof of runtime evaluator behavior.

2026-07-02 dungeon/training catalog graph refs: `tools/endfield_source_graph.py` now ingests `DungeonTable`, `DungeonSeriesTable`, `DungeonTypeTable`, `DungeonCategory2ndTable`, `DungeonRaidTable`, `DungeonFactoryTable`, `SimulationTrainingLevelTable`, `SimulationTrainingCardTable`, `SimulationTrainingCardPoolTable`, `TrainingTypeInfoTable`, `AdventureLevelTable`, and `AdventureWorldLevelTable` as `structured_dungeon_training`. A fast CN graph build to `tmp/source_graph_dungeon_training.sqlite` verified 242 `dungeon`, 106 `dungeon_series`, 18 `dungeon_type`, 7 `dungeon_category2nd`, 4 `simulation_training_level`, 28 `simulation_training_card`, 7 `simulation_training_card_pool`, 4 `training_type`, 60 `adventure_level`, and 7 `adventure_world_level` nodes. Validated edge coverage includes 215 `defines_dungeon`, 198 dungeon-name text, 194 dungeon-description text, 215 dungeon type links, 370 series-to-dungeon links, 316 dungeon level/scene links, 274 dungeon enemy links with level payloads, 177 dungeon reward edges across normal/first-pass/custom/extra/hunter fields, 106 defined dungeon series, 56 series name links, 18 dungeon type rows, 30 raid-related level links, 46 factory dungeon rows, 34 factory dungeon dependency links, 4 simulation training levels, 28 training cards, 125 training pool card links, 4 training type labels, 60 adventure levels, 59 adventure level rewards, and 42 adventure world-level tip text links. Smoke tests passed for `dung01_actmonster01`, `dung01_group_activity01`, `test_pool_1`, and adventure world level `2`, plus a direct check of `dung01_actmonster01` enemy level payloads.

This bridges authored dungeon taxonomy, playable dungeon rows, simulation training card pools, and adventure/world-level progression into the graph. Numeric training/adventure fields are preserved as table evidence, not treated as runtime economy or balancing formulas.

2026-07-02 battle-pass progression graph refs: `tools/endfield_source_graph.py` now ingests `BattlePassSeasonTable`, task/task-group/condition tables, level and override level groups, tracks, reward previews, banners, label maps, and `WeekRaidBattlePassTable` as `structured_battlepass`. A fast CN graph build to `tmp/source_graph_battlepass.sqlite` verified 4 `battlepass_season`, 45 `battlepass_task_group`, 306 `battlepass_task`, 288 `battlepass_condition`, 6 `battlepass_level_group`, 162 `battlepass_level`, 3 `battlepass_track`, 3 `battlepass_track_type`, 8 `battlepass_reward_preview_group`, 44 `battlepass_reward_preview`, 4 `battlepass_banner`, 16 `battlepass_banner_entry`, and 20 `weekraid_battlepass_node` nodes. Validated edge coverage includes 8 season name/short-name text links, 4 season level-group links, 4 season override-level-group links, 8 season preview-group links, 4 season banner links, 4 weapon-box item links, 45 task-group label links, 306 task name links, 306 group-task links, 322 task-condition links, 167 task system-jump links, 162 level entries, 484 level reward edges across free/originium/pay tracks, 3 track name links, 44 preview entries/items, 16 banner entries, 46 label/sublabel links, and 20 week-raid node links each to game dungeon, reward, and reward item. Smoke tests passed for `bp_01`, `bp_01_task_activity_1`, `bp_lv_group_default:10`, and week-raid node `10`, including direct level-reward and week-raid edge checks.

This models authored battle-pass progression, task, reward, preview, and week-raid linkage. It does not model live server season state, purchase entitlement, or runtime progress counters.


2026-07-02 profile/social catalog graph refs: `tools/endfield_source_graph.py` now ingests player-profile and social catalog tables as `structured_profile_social`, covering `PictureTable`, `PictureItemTable`, `PictureTypeTable`, `PictureGenderTable`, `UserAvatarTable`, `BusinessCardTopicTable`, `MailSenderTable`, `MailTemplateTable`, and the friend-chat text/emotion tables. A fast CN graph build to `tmp/source_graph_profile_social.sqlite` verified 88 `profile_picture`, 1 `profile_picture_type`, 39 `user_avatar`, 20 `business_card_topic`, 57 `mail_sender`, 39 `mail_template`, 7 `friend_chat_emotion_tab`, 118 `friend_chat_emotion`, 5 `friend_chat_text_tab`, and 48 `friend_chat_text` nodes. Validated edge coverage includes 88 picture name/author/unlock/character links, 88 item-to-picture unlock links, 39 avatar unlock links, 20 business-card unlock links, 57 mail-sender name links, 39 mail-template title/content/sender links, 22 mail reward links, 118 emotion-to-tab links, 48 friend-chat message/tab text links, and 5 friend-chat tab labels. Smoke tests passed for `pic_1_chr_0004_pelica`, `user_avatar_activity_1`, `activity_reissue_test_mail`, `chat_text_blueprint_1`, and `chat_emojis_tab_1`.

This models authored profile-picture, avatar, business-card, mail-template, and friend-chat catalog semantics. It does not prove live account unlock state, mail delivery state, or server-side social behavior.


2026-07-02 character progression graph refs: `tools/endfield_source_graph.py` now ingests `CharLevelUpTable`, `CharBreakTable`, `CharBreakStageTable`, `CharBreakNodeTable`, and `CharGrowthTable` as `structured_character_progression`, bridging previously modeled characters to explicit level costs, break configs, break-stage caps, break nodes, default weapons, growth profession/type, main/sub attribute metadata, and per-character break-cost requirements. A fast CN graph build to `tmp/source_graph_character_progression.sqlite` verified 90 `defines_character_level_cost`, 5 `defines_character_break_config`, 5 `character_break_config_stage`, 13 `character_break_config_exp_item`, 5 `defines_character_break_stage`, 7 `defines_character_break_node`, 7 `character_break_node_stage`, 29 `defines_character_growth`, 29 each of growth type/profession/default-weapon/main-attribute/sub-attribute links, 203 `character_has_break_cost`, 203 each of break-cost name/description/node/stage links, and 464 `character_break_cost_requires_item` edges. Smoke tests passed for `chr_0004_pelica`, `chr_0004_pelica:charBreak20`, break config `1`, and node `charBreak20`.

This models authored character level and breakthrough progression costs as table evidence. It does not prove live account level state, dynamic balance formulas, or runtime progression execution.


2026-07-02 cash shop commerce graph refs: `tools/endfield_source_graph.py` now ingests `CashShopGoodsTable`, `CashShopTable`, `CashShopGroupTable`, `CashShopRechargeTable`, `CashShopRecommendTable`, `CashshopShopTabDataTable`, `GiftpackCashShopGoodsDataTable`, and `RechargeTable` as `structured_cash_shop`. A fast CN graph build to `tmp/source_graph_cash_shop.sqlite` verified 61 `defines_cash_goods`, 40 cash-goods name text links, 61 cash-goods shop links, 61 cash-goods reward links, 8 defined cash shops, 8 cash-shop name links, 61 shop-list goods links, 2 defined cash-shop groups, 8 group-to-shop links, 34 recharge bonus rows and reward links, 24 recommendations, 25 recommendation-to-goods links, 31 cash-shop tab rows, 26 gift-pack config rows, 16 gift-pack tag links, 6 gift-pack show-after links, and 6 recharge packs linked to recharge items. Smoke tests passed for `bp_pay_track`, shop `BP`, `shop_pay_gift_pack`, `recommend_newbie_special`, `newbie_giftpack_01`, `direct_recharge_198`, and `os_recharge_originium_198`.

This models authored paid-shop goods, display grouping, recommendations, gift-pack presentation config, recharge packs, and first-purchase/bonus reward rows. It does not prove live purchase availability, platform pricing enforcement, entitlement ownership, or server-side store rotation.


2026-07-02 item acquisition/grouping graph refs: `tools/endfield_source_graph.py` now ingests `ItemListByTypeTable`, `ItemListByShowingTypeTable`, `NoObtainWayCondTable`, `ObtainWayShowCondTable`, `UsableItemChestTable`, `LTItemTable`, and `LTItemTypeTable` as `structured_item_acquisition`. A fast CN graph build to `tmp/source_graph_item_acquisition.sqlite` verified 83 `defines_item_type_list`, 1,946 `item_type_lists_item`, 11 `defines_item_showing_type_list`, 1,946 `item_showing_type_lists_item`, 53 `item_obtain_condition`, 6 `item_obtain_condition_type`, 53 typed condition-type edges, 27 dungeon condition refs, 12 wiki condition refs, 13 factory-tech condition refs, 1 item condition ref, 32 obtain-way show-condition edges, 36 usable chest configs, 36 item-to-chest config edges, 5 random chest item edges, 154 chest reward edges, 28 limited-time item aliases, and 5 limited-time item-type preset edges. Smoke tests passed for item type `1`, showing type `0`, dungeon/wiki/tech obtain conditions, `item_obtain_case_bp_selfselect_skillsp_1_1`, `item_case_bp_random_1`, `ap_supply_lt_abs1`, and limited-time item type `63`.

This models authored item grouping, obtain-display gates, chest reward configs, and limited-time item aliases. It does not prove live inventory contents, server-side acquisition availability, or runtime chest selection behavior.

Known parser limits are acceptable for current use:

- lightweight IL2CPP metadata parsing can leave generic/array/byref type
  indexes unresolved in reports;
- full asset-map ingestion is expensive and should be skipped unless needed;
- legacy local `character_recovery/` report directories may exist, but the
  maintained graph emits the top-level recovery candidate JSON.
