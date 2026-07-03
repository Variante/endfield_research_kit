# Attribute Meta Reverse Source Graph Recovery - 2026-07-03

## Context

Attribute metadata is a high-fan-in numerical system. The source graph already
linked characters, equipment, and enemy templates to `attribute_meta` nodes, but
attribute-centered queries could not directly enumerate which gameplay entities
used a given attribute type.

## Finding

`tools/endfield_source_graph.py` now emits reverse edges for the main attribute
fan-in paths:

- `attribute_meta_used_by_equipment`
- `attribute_meta_used_by_enemy`
- `attribute_meta_used_by_character_main`
- `attribute_meta_used_by_character_sub`
- `attribute_meta_used_by_character_base`

The equipment and enemy reverse edges include the original forward edge kind in
payload data as `edgeKind`, preserving whether the source was display/runtime
equipment data or a particular enemy attribute-template family.

During validation, a malformed direct `add_node()` call in
`ingest_reference_tables()` was also corrected so the method can be exercised
directly when checking reference-table semantics.

## Validation

Focused temporary graph builds:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DBs:

- `tmp/attribute_meta_reverse.sqlite`
- `tmp/character_attribute_reverse.sqlite`

Equipment/enemy counts:

- `equipment_display_base_attribute`: 220 / reverse 220
- `equipment_display_attribute`: 618 / reverse 618
- `equipment_runtime_attribute`: 915 / reverse 915
- `enemy_attribute_modifier_meta`: 67 / reverse 67
- `enemy_attribute_template_independent_attr`: 1,695 / reverse 1,695
- `enemy_attribute_template_level_attr`: 36,800 / reverse 36,800

Character counts:

- `character_main_attribute_meta`: 29 / reverse 29
- `character_sub_attribute_meta`: 29 / reverse 29
- `character_base_attribute_meta`: 83,636 / reverse 83,636

Sample reverse edges showed `attribute_meta:0` pointing back to
`enemy_attribute_template:eny_0007_mimicw` level-dependent rows and to
`character:chr_0002_endminm` base-attribute rows with the original level,
break-stage, and value payloads.
