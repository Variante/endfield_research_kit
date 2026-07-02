# Item submission source graph recovery - 2026-07-02

## Scope

Added structured source-graph recovery for item submission, bottle/liquid item
forms, AP recovery items, valuable depot categories, collection entries, recycle
bins, and food-submit stage reward links:

- `SubmitItem.json`
- `FullBottleTable.json`
- `EmptyBottleTable.json`
- `FoodSubmitStageIdTable.json`
- `RecoverApItemTable.json`
- `ValuableDepot.json`
- `CollectionTable.json`
- `RecycleBinTable.json`
- `LevelId2RecycleBinsTable.json`

## Recovered semantics

- `SubmitItem` rows now define submit ids and link each requirement group to
  required item ids with count/type evidence from `paramData`.
- Full bottle rows now link the full bottle item to its empty container item and
  contained liquid item.
- Empty bottle rows now link container items to accepted liquid items and full
  bottle variants.
- Food-submit stage id rows now link activity submit stages to activity ids,
  activity-stage overlays, rewards, jump ids, and stage name text.
- AP recovery item rows now link item ids to AP recovery values.
- Valuable depot rows now link depot categories to allowed item types and depot
  icon/name metadata.
- Collection rows now link prefab entries to item/bandwidth items and merge
  targets.
- Recycle bin rows now link bins to domains, levels, level-map inference, level
  upgrade entries, rewards, and localized descriptions.
- Level-to-recycle-bin rows now link levels to their recycle bin ids.

## Validation

Commands run:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\item_submission_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The validation build completed with:

```text
Source graph: 1587917 nodes, 3012679 edges, 2158504 aliases
```

Targeted count checks:

```text
activity_submit_item          169 nodes
full_bottle_item               67 nodes
empty_bottle_item               7 nodes
ap_recovery_item               18 nodes
valuable_depot                  9 nodes
collection_entry               22 nodes
recycle_bin                    16 nodes
recycle_bin_level              64 nodes
activity_submit_food_stage     16 nodes

defines_submit_item           169 edges
submit_item_requires_item     308 edges
defines_full_bottle            67 edges
full_bottle_item_ref           67 edges
full_bottle_empty_container    67 edges
full_bottle_contains_liquid    67 edges
defines_empty_bottle            7 edges
empty_bottle_item_ref           7 edges
empty_bottle_accepts_liquid    67 edges
empty_bottle_full_variant      67 edges
defines_food_submit_stage_id   16 edges
food_submit_stage_activity     16 edges
food_submit_stage_id_overlay   16 edges
food_submit_stage_reward       14 edges
defines_ap_recovery_item       18 edges
item_has_ap_recovery           18 edges
defines_valuable_depot          9 edges
valuable_depot_allows_item_type 42 edges
defines_collection_entry       21 edges
collection_entry_item           4 edges
collection_entry_bandwidth_item 1 edge
collection_entry_merges_to     19 edges
defines_recycle_bin            16 edges
recycle_bin_domain             16 edges
recycle_bin_level              16 edges
recycle_bin_has_level          64 edges
recycle_bin_level_reward       64 edges
defines_level_recycle_bins      9 edges
level_has_recycle_bin          16 edges
```

