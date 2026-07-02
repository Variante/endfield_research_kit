# Settings metadata source graph recovery - 2026-07-02

## Scope

Extended the existing settings source-graph pass to cover settings ids,
constants, UI text/style metadata, instruction books, item icon composites, and
temporary map-mark templates:

- `SettingIdTable.json`
- `SettingIdToStr.json`
- `SettingIdToNum.json`
- `StrIdNumTable.json`
- `NumIdStrTable.json`
- `GlobalConst.json`
- `JsonConst.json`
- `GameSystemConfigTable.json`
- `RichTextStyleTable.json`
- `InstructionBook.json`
- `ItemIconCompositeTable.json`
- `MapMarkTypeTempTable.json`

## Recovered semantics

- Setting ids now link to setting groups plus bidirectional string/numeric id
  lookup rows.
- String/numeric id dictionaries now preserve all entries in both directions.
- Global constants and JSON constants are queryable, with obvious references to
  items, rewards, activities, systems, map marks, maps, or levels linked as
  semantic edges. `JsonConst` string payloads are parsed before reference
  extraction when they contain valid JSON.
- Game system configs now link system ids to icons, red-dot names, unlock types,
  localized names, and descriptions.
- Rich text style ids are queryable with pre/post formatting definitions.
- Instruction book ids now link title/content i18n text and activity-like ids.
- Item icon composite configs now expose mark/background icon asset stems.
- Temporary map mark groups now link to map-mark templates, active/inactive icon
  asset stems, names, and descriptions.

## Validation

Commands run:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\settings_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The validation build completed with:

```text
Source graph: 1624691 nodes, 3050424 edges, 2230477 aliases
```

Targeted count checks:

```text
setting_item                  141 nodes
setting_group                   8 nodes
setting_id_map                116 nodes
id_dictionary                 110 nodes
id_dictionary_entry         34898 nodes
global_const                   80 nodes
json_const                     23 nodes
game_system_config             18 nodes
rich_text_style                87 nodes
instruction_book               79 nodes
item_icon_composite            60 nodes
map_mark_temp_group            54 nodes
map_mark_template             156 nodes

defines_setting_id            100 edges
setting_id_in_group           100 edges
defines_setting_num_to_str     58 edges
setting_num_maps_to_setting    58 edges
defines_setting_str_to_num     58 edges
setting_maps_to_num            58 edges
defines_str_id_num_dictionary  55 edges
defines_num_id_str_dictionary  55 edges
dictionary_str_to_num_entry 17449 edges
dictionary_num_to_str_entry 17449 edges
defines_global_const           80 edges
global_const_refs_item         21 edges
global_const_refs_reward        2 edges
global_const_refs_map_mark      1 edge
defines_json_const             23 edges
json_const_refs_item            6 edges
json_const_refs_activity        1 edge
defines_game_system_config     18 edges
game_system_name_text          18 edges
game_system_desc_text          11 edges
defines_rich_text_style        87 edges
defines_instruction_book       79 edges
instruction_book_title_text    79 edges
instruction_book_content_text  79 edges
instruction_book_activity_ref  79 edges
defines_item_icon_composite    60 edges
defines_map_mark_temp_group    54 edges
map_mark_temp_group_has_template 153 edges
map_mark_template_name_text   151 edges
map_mark_template_desc_text   113 edges
```

