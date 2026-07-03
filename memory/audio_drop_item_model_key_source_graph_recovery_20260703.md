# Audio Drop Item Model-Key Source-Graph Recovery - 2026-07-03

## Scope

`ItemTable.modelKey` often names an `AudioDrop` config that controls item
pickup/drop SFX. The item graph already stored `modelKey` as a `model_key`
alias, and `AudioDrop` already emitted audio-drop config nodes and Wwise event
edges, but there was no semantic bridge between the item and the audio-drop
config.

This pass links `AudioDrop` rows back to `item` nodes that use the same
`model_key` alias.

## Added Semantics

- `item_uses_audio_drop_config`
- `audio_drop_config_used_by_item`

The edge evidence is `modelKey`.

## Validation

Focused temp graph:
`tmp/audio_drop_item_validate.sqlite`

The validation used `ingest_item_economy()` followed by
`ingest_audio_config_semantics()`, because `ItemTable.modelKey` aliases are
created by the item economy ingest.

Counts:

| Edge kind | Count |
| --- | ---: |
| `item_uses_audio_drop_config` | 1,145 |
| `audio_drop_config_used_by_item` | 1,145 |

The links cover 42 distinct `audio_drop` configs.

CLI smoke checks:

- `python tools\endfield_source_graph.py query item_ap_feed_in --kind item --db tmp\audio_drop_item_validate.sqlite --limit 20`
  showed `item_uses_audio_drop_config -> audio_drop:int_collection_item_1`.
- `python tools\endfield_source_graph.py query int_drop_gem --kind audio_drop --db tmp\audio_drop_item_validate.sqlite --limit 20`
  showed gem items through `audio_drop_config_used_by_item`, including
  `gem_sword_0003_42`.

`python -m py_compile tools\endfield_source_graph.py` passed.
