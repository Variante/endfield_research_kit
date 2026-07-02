# Factory Interaction Lookup Source Graph Recovery - 2026-07-02

## Scope

Recovered graph semantics for compact factory, interaction, activity, loading,
gem, stamina, and EXP lookup tables that were still only represented as raw
structured rows.

Tables added to `FACTORY_INTERACTION_LOOKUP_TABLES`:

- `FactorySpecialPowerPoleTable.json`
- `MapRemindTable.json`
- `FactorySeedItemTable.json`
- `InteractiveMarkDataTable.json`
- `LimitedFormulaCraftIdReverseTable.json`
- `LimitedFormulaItemIdReverseTable.json`
- `OriginiumStaminaCost.json`
- `GemCustomizationBox.json`
- `FactoryQuickBarTypeTable.json`
- `LoadingTypeTagTable.json`
- `ActivityDungeonState.json`
- `ActivityDungeonFightingStageTable.json`
- `ActivityCleaningStageDataTable.json`
- `FactoryHubCraftTypeListTable.json`
- `LTItemTyp2ItemTypeTable.json`
- `ExpItemMap.json`
- `ExpItemDataMap.json`

## Recovered Semantics

- Special factory power-pole rows now become searchable
  `factory_special_power_pole` nodes with name, description, map-name, and
  position text refs.
- Map reminder rows now expose `map_reminder` and `map_reminder_tab` nodes,
  reminder description text, and icon asset aliases.
- Seed item rows now link seed items to item ids, interactive doodad ids, and
  growing/final model asset refs.
- Interactive mark lookup rows now link interactive ids to map-mark templates.
- Limited-formula reverse tables now link source item or craft ids back to the
  limited formula recipe id.
- Originium stamina purchase costs now expose direct
  `originium_stamina_cost` nodes.
- Gem customization boxes now link the box item, produced gem item, and locked
  term type slots.
- Factory quickbar types now expose localized labels, icon asset refs, and
  priority metadata.
- Loading type tags now expose background image refs.
- Activity dungeon state/fighting stage tables now link level ids, activity
  stages, quest ids, and display states.
- Activity cleaning stage rows now expose image asset refs.
- Factory hub craft type lists now group factory building ids by type-list id.
- LT item type conversions now link source and target item-type nodes.
- EXP item maps now link item ids to EXP gain/type metadata.

## Validation

Command:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_interaction_lookup_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1627151 nodes, 3054375 edges, 2233212 aliases
```

Target node counts:

```text
factory_special_power_pole 16
map_reminder 13
map_reminder_tab 2
factory_seed_item 13
interactive_mark_binding 10
limited_formula_reverse 17
originium_stamina_cost 10
gem_customization_box 12
gem_customization_term_type 3
factory_quickbar_type 9
loading_type_tag 8
activity_dungeon_state 8
activity_dungeon_show_state 3
activity_cleaning_stage 7
factory_hub_craft_type_list 6
item_type_conversion 5
exp_item_value 5
```

Notable target edge counts:

```text
factory_hub_craft_type_has_building 59
lookup_references_asset 79
uses_i18n_text 54
limited_formula_reverse_formula 17
limited_formula_reverse_source 17
gem_customization_locks_term_type 27
activity_stage_level 8
activity_stage_quest 8
interactive_mark_binding_mark_template 10
```
