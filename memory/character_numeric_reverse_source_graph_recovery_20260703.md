# Character Numeric Reverse Source Graph Recovery - 2026-07-03

## Finding

Character progression data already exposed authored numeric facts in the source
graph:

- character level checkpoints and their gold costs;
- character stat checkpoints and property values;
- structured `CharGrowthTable` break/equipment break required-item costs.

The forward evidence was good, but reverse traversal from a cost item or stat
property was incomplete for downstream graph consumers. This made it harder to
ask "where is this item/stat used in character progression?" without manually
scanning incoming edge families.

## Graph Change

`tools/endfield_source_graph.py` now emits reverse edges for conservative
authored character-progression facts:

- `item_gold_cost_for_level_checkpoint`
  from `item:item_gold` to `character_level_checkpoint`;
- `stat_property_used_by_character_checkpoint`
  from `gameplay_stat_property` to `character_stat_checkpoint`;
- `item_required_by_character_break_cost_requires_item`
  from `item` to `character_break_cost`.

These are reverse indexes over existing static authored values. They do not
evaluate runtime formulas, scaling curves, modifier ordering, or combat
behavior.

## Validation

Cheap checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused graph ingest:

```bat
python -c "... SourceGraphBuilder(db_path='tmp/character_numeric_reverse.sqlite').ingest_assets(); ingest_gameplay(); ingest_character_progression_semantics() ..."
```

Counts:

- `item_gold_cost_for_level_checkpoint`: `168`
- `stat_property_used_by_character_checkpoint`: `18,424`
- `item_required_by_character_break_cost_requires_item`: `464`

Sample SQL evidence:

- `item:item_gold -> character_level_checkpoint:chr_0004_pelica:level:20`
  with `{"count":250}`;
- `gameplay_stat_property:atk -> character_stat_checkpoint:chr_0004_pelica:stat:0:1:0`
  with `{"key":"atk","type":2,"value":30.0}`;
- `item:item_char_break_stage_1_2 -> character_break_cost:chr_0002_endminm:charBreak20`
  with `{"count":8,"index":0}`.

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query item_gold --kind item --db tmp\character_numeric_reverse.sqlite --limit 18
python tools\endfield_source_graph.py query atk --kind gameplay_stat_property --db tmp\character_numeric_reverse.sqlite --limit 18
python tools\endfield_source_graph.py query item_char_break_stage_1_2 --kind item --db tmp\character_numeric_reverse.sqlite --limit 18
```

The item queries show the existing forward cost evidence; the new reverse edges
are also present for exact traversal and downstream reports.

## Follow-Up

The next numerical-data step should stay evidence-preserving: expose more
reverse indexes for authored costs/stat consumers where the source table names
the relationship directly. Do not infer formula execution or derived runtime
values until the evaluator and modifier order are recovered.
