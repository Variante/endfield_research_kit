# Wiki Reverse Source Graph Recovery - 2026-07-03

## Scope

The structured Wiki and tutorial tables already exposed forward relationships
from categories, groups, domains, entries, tutorial pages, guide rows, craft
refs, items, and enemy drop rows. This pass adds reverse source-graph edges so
item-, enemy-, entry-, page-, and group-centered queries can answer what Wiki
content references them without manual SQL.

This is authored table evidence only. It does not prove runtime guide unlock
state, player tutorial progress, item ownership, enemy encounter availability,
or live Wiki visibility.

## Source Tables

- `WikiCategoryTable.json`
- `WikiGroupTable.json`
- `WikiEntryTable.json`
- `WikiEntryDataTable.json`
- `WikiTutorialPageTable.json`
- `WikiTutorialPageByEntryTable.json`
- `WikiLimitedGuideTable.json`
- `WikiCraftJumpTable.json`
- `WikiDefaultCraftTable.json`
- `WikiEnemyDropTable.json`

## Graph Change

New reverse edge kinds:

- `wiki_group_in_category`
- `wiki_entry_in_domain`
- `wiki_entry_in_group`
- `item_referenced_by_wiki_entry`
- `enemy_referenced_by_wiki_entry`
- `wiki_tutorial_page_in_tutorial`
- `wiki_entry_referenced_by_tutorial_page`
- `wiki_entry_used_by_limited_guide`
- `wiki_craft_item_blueprint_used_by_item`
- `wiki_craft_item_blackbox_used_by_item`
- `item_has_wiki_default_craft_source`
- `item_dropped_by_wiki_enemy`

These mirror existing forward relationships such as
`wiki_group_has_entry`, `wiki_entry_refers_item`,
`wiki_tutorial_page_refs_entry`, and `wiki_enemy_drops_item`.

## Validation

Focused temporary graph:

```bat
tmp\wiki_reverse_validation.sqlite
```

Focused ingest:

- `ingest_wiki_semantics()`

Node counts:

- `wiki_category`: 6
- `wiki_group`: 56
- `wiki_entry`: 1,107
- `wiki_tutorial`: 308
- `wiki_tutorial_page`: 527
- `wiki_limited_guide`: 118
- `wiki_craft_ref`: 69
- `item`: 726
- `enemy`: 78
- `gameplay_domain`: 56

Forward/reverse counts:

- `wiki_category_has_group`: 56 / `wiki_group_in_category`: 56
- `domain_has_wiki_entry`: 1,105 / `wiki_entry_in_domain`: 1,105
- `wiki_group_has_entry`: 1,105 / `wiki_entry_in_group`: 1,105
- `wiki_entry_refers_item`: 724 / `item_referenced_by_wiki_entry`: 724
- `wiki_entry_refers_enemy`: 73 / `enemy_referenced_by_wiki_entry`: 73
- `wiki_tutorial_has_page`: 1,054 / `wiki_tutorial_page_in_tutorial`: 1,054
- `wiki_tutorial_page_refs_entry`: 455 /
  `wiki_entry_referenced_by_tutorial_page`: 455
- `wiki_limited_guide_entry`: 118 / `wiki_entry_used_by_limited_guide`: 118
- `wiki_craft_item_blueprint`: 54 /
  `wiki_craft_item_blueprint_used_by_item`: 54
- `wiki_craft_item_blackbox`: 60 /
  `wiki_craft_item_blackbox_used_by_item`: 60
- `wiki_default_craft_item`: 2 / `item_has_wiki_default_craft_source`: 2
- `wiki_enemy_drops_item`: 64 / `item_dropped_by_wiki_enemy`: 64

Smoke queries:

```bat
python tools\endfield_source_graph.py query item_copper_ore --kind item --db tmp\wiki_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query eny_0007_mimicw --kind enemy --db tmp\wiki_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query wiki_tut_fac_miner4_1 --kind wiki_tutorial_page --db tmp\wiki_reverse_validation.sqlite --limit 16
```

The item query now shows the Wiki entry that references `item_copper_ore`.
The enemy query shows both the Wiki entry and Wiki drop-item relationship for
`eny_0007_mimicw`. The tutorial-page query shows reverse entry references for
`wiki_item_port_miner_4` and `wiki_item_copper_ore`, plus the tutorial
membership reverse edge.
