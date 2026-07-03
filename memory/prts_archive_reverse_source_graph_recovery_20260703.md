# PRTS Archive Reverse Source Graph Recovery - 2026-07-03

## Scope

The PRTS archive and reading tables already exposed authored forward
relationships between archive pages, categories, first-level collections,
entries, rich content, reading popups, reading entries, investigations, notes,
domains, stories, and rewards. This pass adds reverse source-graph edges so
entry-, content-, domain-, item-, note-, and group-centered queries can explain
which archive structures use them.

This is authored archive table evidence only. It does not prove runtime unlock
state, player collection progress, archive visibility, or reading-popup trigger
conditions.

## Source Tables

- `PrtsPage.json`
- `PrtsCategory.json`
- `PrtsFirstLv.json`
- `PrtsAllItem.json`
- `PrtsRecord.json`
- `PrtsDocument.json`
- `PrtsMultimedia.json`
- `RichContentTable.json`
- `ReadingPopUpIconTable.json`
- `ReadingPopUpTable.json`
- `PrtsReading.json`
- `PrtsInvestigate.json`
- `PrtsInvestigateCategory.json`
- `PrtsNote.json`

## Graph Change

New reverse edge kinds include:

- `rich_content_line_in_content`
- `prts_category_in_page`
- `prts_first_level_in_category`
- `prts_entry_in_first_level`
- `reading_popup_icon_used_by_popup`
- `prts_entry_referenced_by_reading_entry`
- `prts_investigation_group_in_investigation`
- `prts_entry_in_investigation_group`
- `prts_note_in_investigation_group`
- `domain_has_prts_investigation`
- `prts_entry_unlocked_by_investigation`
- `prts_entry_in_investigation`
- `item_rewarded_by_prts_investigation`

PRTS content-target helpers also now add reverse `*_source` edges for archive
owners that target existing story or rich-content nodes.

## Validation

Focused temporary graph:

```bat
tmp\prts_reverse_validation.sqlite
```

Focused ingest:

- `ingest_webui_story()`
- `ingest_prts_archive_semantics()`

Selected node counts:

- `prts_page`: 3
- `prts_category`: 6
- `prts_first_level`: 375
- `prts_entry`: 417
- `rich_content`: 586
- `rich_content_line`: 2,991
- `reading_popup`: 576
- `reading_popup_icon`: 14
- `prts_reading`: 21
- `prts_reading_entry`: 36
- `prts_investigation`: 12
- `prts_investigation_group`: 29
- `prts_note`: 29

Forward/reverse counts:

- `rich_content_has_line`: 2,991 / `rich_content_line_in_content`: 2,991
- `prts_page_has_category`: 1 / `prts_category_in_page`: 1
- `prts_category_has_first_level`: 375 / `prts_first_level_in_category`: 375
- `prts_first_level_has_entry`: 1,242 / `prts_entry_in_first_level`: 1,242
- `reading_popup_uses_icon`: 576 / `reading_popup_icon_used_by_popup`: 576
- `prts_reading_entry_refs_prts_entry`: 3 /
  `prts_entry_referenced_by_reading_entry`: 3
- `prts_investigation_has_group`: 58 /
  `prts_investigation_group_in_investigation`: 58
- `prts_investigation_group_has_entry`: 94 /
  `prts_entry_in_investigation_group`: 94
- `prts_investigation_group_has_note`: 58 /
  `prts_note_in_investigation_group`: 58
- `prts_investigation_uses_domain`: 12 / `domain_has_prts_investigation`: 12
- `prts_investigation_unlocks_entry`: 12 /
  `prts_entry_unlocked_by_investigation`: 12
- `prts_investigation_has_entry`: 47 / `prts_entry_in_investigation`: 47
- `prts_investigation_rewards_item`: 12 /
  `item_rewarded_by_prts_investigation`: 12
- `prts_entry_targets_story`: 105 / `prts_entry_targets_story_source`: 105
- `prts_entry_targets_rich_content`: 391 /
  `prts_entry_targets_rich_content_source`: 391
- `reading_popup_targets_story`: 247 /
  `reading_popup_targets_story_source`: 247
- `reading_popup_targets_rich_content`: 548 /
  `reading_popup_targets_rich_content_source`: 548
- `prts_reading_entry_targets_story`: 2 /
  `prts_reading_entry_targets_story_source`: 2
- `prts_reading_entry_targets_rich_content`: 28 /
  `prts_reading_entry_targets_rich_content_source`: 28

Smoke queries:

```bat
python tools\endfield_source_graph.py query nar_002_settlement --kind prts_entry --db tmp\prts_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query text_002_settelment --kind rich_content --db tmp\prts_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query domain_1 --kind gameplay_domain --db tmp\prts_reverse_validation.sqlite --limit 16
python tools\endfield_source_graph.py query item_diamond --kind item --db tmp\prts_reverse_validation.sqlite --limit 16
```

The smoke queries show archive entry membership, rich-content source entries,
domain-to-investigation links, and item-to-investigation reward links from the
new reverse direction.
