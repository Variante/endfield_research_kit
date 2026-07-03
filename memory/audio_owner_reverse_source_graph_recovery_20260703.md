# Audio Owner Reverse Source-Graph Recovery - 2026-07-03

## Scope

Audio config tables already linked audio config nodes to owner rows when the
audio row key matched an existing gameplay owner node. This pass adds reverse
owner-to-audio edges so queries starting from buildings, machines, items, item
types, or levels can discover their authored audio config rows.

## Added Reverse Edges

- `factory_building_uses_audio_battle_building`
- `factory_machine_uses_audio_battle_building`
- `factory_building_uses_audio_factory`
- `factory_machine_uses_audio_factory`
- `item_uses_audio_item_drag_drop`
- `factory_item_uses_audio_item_drag_drop`
- `factory_machine_uses_audio_item_drag_drop`
- `item_type_uses_audio_item_type_drag_drop`
- `level_uses_audio_level`

## Validation

Focused temp graph:
`tmp/audio_owner_reverse_validate.sqlite`

The validation seeded only the owner node kinds needed by the audio tables, then
ran `ingest_audio_config_semantics()`.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `audio_battle_building_for_factory_building` | 17 | `factory_building_uses_audio_battle_building` | 17 |
| `audio_battle_building_for_factory_machine` | 17 | `factory_machine_uses_audio_battle_building` | 17 |
| `audio_factory_for_factory_building` | 73 | `factory_building_uses_audio_factory` | 73 |
| `audio_factory_for_factory_machine` | 73 | `factory_machine_uses_audio_factory` | 73 |
| `audio_item_drag_drop_for_item` | 571 | `item_uses_audio_item_drag_drop` | 571 |
| `audio_item_drag_drop_for_factory_item` | 571 | `factory_item_uses_audio_item_drag_drop` | 571 |
| `audio_item_drag_drop_for_factory_machine` | 571 | `factory_machine_uses_audio_item_drag_drop` | 571 |
| `audio_item_type_drag_drop_for_item_type` | 11 | `item_type_uses_audio_item_type_drag_drop` | 11 |
| `audio_level_for_level` | 103 | `level_uses_audio_level` | 103 |

`python -m py_compile tools\endfield_source_graph.py` passed.
