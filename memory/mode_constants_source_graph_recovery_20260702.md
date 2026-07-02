# Mode constants source graph recovery - 2026-07-02

## Scope

Added structured source-graph recovery for mode constants and small mapping
tables that bind systems, UI labels, factory wrappers, character behaviors, and
activity-stage metadata:

- `SpaceshipConst.json`
- `FactoryConst.json`
- `CinematicConst.json`
- `SimulationTrainingConst.json`
- `DungeonConst.json`
- `ActivityConst.json`
- `FacBlueprintConst.json`
- `BattlePassConst.json`
- `CashShopConst.json`
- `InteractiveFacWrapperTable.json`
- `PsTrophyTable.json`
- `FactoryNodeTypeToBuildingType.json`
- `FactoryBuildingTypeToNodeType.json`
- `ActivityHighDifficultySpecialStageTable.json`
- `CharGatherBehaviourTable.json`
- `SpaceshipSubCharGiftTable.json`
- `LevelGradeTable.json`
- `DistributionInfoTable.json`
- `FactorySmartAlertTable.json`
- `FactoryBattleTable.json`

## Recovered semantics

- Constants are now queryable as `mode_const` nodes and link obvious item,
  reward, activity, map, and level references.
- Factory interactive wrappers now link wrapper ids to interactive template ids.
- PS trophy rows now expose object ids and trophy numeric aliases.
- Factory node/building-type mapping tables now preserve both directions as
  `factory_building_type_map` nodes.
- High-difficulty special-stage rows now link activity-stage ids and background
  asset stems.
- Character gather behavior rows now link characters to crop/doodad env emoji
  states and cooldowns.
- Spaceship character gift rows now link characters to gift entries and story
  dialog ids.
- Level grade rows now expose grade configs and per-grade bandwidth/prosperity
  limits.
- Distribution info rows now link area names and system jump ids.
- Factory smart alerts now expose localized alert text variants.
- Factory battle rows now link battle configs to gameplay skills, text, and
  range-effect asset stems. `FactoryBattleTable` has 18 definition rows but 17
  unique config nodes because two rows share the same `id`.

## Validation

Commands run:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\mode_constants_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The validation build completed with:

```text
Source graph: 1626304 nodes, 3052645 edges, 2232098 aliases
```

Targeted count checks:

```text
mode_const                         250 nodes
interactive_fac_wrapper             46 nodes
ps_trophy                           41 nodes
factory_building_type_map           65 nodes
activity_high_difficulty_special_stage 32 nodes
character_gather_behavior           28 nodes
env_emoji                            5 nodes
spaceship_character_gift            26 nodes
spaceship_character_gift_entry      78 nodes
level_grade_config                  26 nodes
level_grade_entry                  164 nodes
distribution_info                   24 nodes
factory_smart_alert                 21 nodes
factory_battle_config               17 nodes

defines_mode_const                 250 edges
mode_const_refs_item                17 edges
mode_const_refs_reward               4 edges
mode_const_refs_activity             5 edges
mode_const_refs_map_or_level         2 edges
defines_interactive_fac_wrapper     46 edges
interactive_fac_wrapper_template    46 edges
defines_ps_trophy                   41 edges
defines_factory_building_type_map   65 edges
factory_building_type_map_source    65 edges
factory_building_type_map_target    65 edges
defines_high_difficulty_special_stage 32 edges
high_difficulty_special_stage_activity_stage 32 edges
defines_character_gather_behavior   28 edges
character_has_gather_behavior       28 edges
character_gather_behavior_env_emoji 112 edges
defines_spaceship_character_gift    26 edges
spaceship_character_gift_has_entry  78 edges
spaceship_character_gift_dialog     78 edges
defines_level_grade_config          26 edges
level_grade_config_has_grade       197 edges
defines_distribution_info           24 edges
distribution_area_name_text         24 edges
distribution_info_jump              21 edges
defines_factory_smart_alert         21 edges
defines_factory_battle_config       18 edges
factory_battle_common_skill         17 edges
factory_battle_overload_skill       16 edges
factory_battle_normal_desc_text     16 edges
factory_battle_overload_desc_text   16 edges
```

