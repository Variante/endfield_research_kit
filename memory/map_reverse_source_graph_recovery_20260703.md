# Map Reverse Source Graph Recovery - 2026-07-03

## Context

Decoded map config, map brief, region, mark, and selected structured table
ingests already connected levels, maps, regions, sublevels, and mark templates
in the forward direction. Map-centered and region-centered queries still needed
extra hops or manual SQL because several reverse relationships were missing.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for map and map-mark
relationships:

- `map_has_config`
- `map_has_level`
- `map_has_brief_info`
- `map_sublevel_in_brief_info`
- `map_has_sublevel_brief`
- `map_region_in_level`
- `map_region_tier_used_by_region`
- `map_region_hides_region`
- `map_region_groups_region`
- `map_mark_template_used_by_mark`
- `map_mark_in_level`
- `map_mark_category_has_type`
- `map_mark_type_has_template`

The shared `add_level_map_edge()` helper now emits `map_has_level`, so reverse
map-level evidence is preserved across decoded config and structured table
call sites.

## Validation

Syntax check:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temporary graph:

```bat
tmp\map_reverse_validation_20260703.sqlite
```

Focused ingest methods:

- `ingest_decoded_config_semantics`
- `ingest_selected_structured_tables`

Counts:

- `map_config_defines_map`: 139 / `map_has_config`: 139
- `level_belongs_to_map`: 794 / `map_has_level`: 794
- `map_brief_info_for_map`: 139 / `map_has_brief_info`: 139
- `map_brief_info_has_sublevel`: 211 / `map_sublevel_in_brief_info`: 211
- `map_sublevel_brief_in_map`: 211 / `map_has_sublevel_brief`: 211
- `level_has_map_region`: 268 / `map_region_in_level`: 268
- `map_region_has_tier_region`: 98 / `map_region_tier_used_by_region`: 98
- `map_region_hidden_by_mist_region`: 100 / `map_region_hides_region`: 100
- `map_region_group_region`: 11 / `map_region_groups_region`: 11
- `map_mark_uses_template`: 1,959 / `map_mark_template_used_by_mark`: 1,959
- `level_has_map_mark`: 1,843 / `map_mark_in_level`: 1,843

The selected structured rows in this focused graph did not resolve
`map_mark_type_has_category` or `map_mark_template_has_type`; both reverse
pairs matched at zero.
