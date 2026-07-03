# Gameplay Required Item Reverse Source Graph Recovery - 2026-07-03

## Context

The compact WebUI gameplay ingest already recovered generic item requirements
from character skill groups, breakthroughs, potentials, equipment formulas,
skills, talents, and nested progression payloads. These relationships were
only easy to traverse from the owning gameplay node to the required item through
`requires_item`.

## Finding

`tools/endfield_source_graph.py` now emits a mirrored
`item_required_by_gameplay` edge for every generic WebUI gameplay
`requires_item` edge, including synthetic `item_gold` costs. The reverse edge
keeps the same evidence path and count payload, so an item query can enumerate
which gameplay formulas, checkpoints, skills, talents, potentials, or
breakthroughs consume it.

This is intentionally limited to the shared compact WebUI gameplay helper:

- `add_gameplay_gold_edge`
- `add_gameplay_item_edges`

More specialized table-specific cost edges still keep their existing specific
edge kinds unless they need separate reverse lookup work later.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary DB: `tmp/gameplay_required_item_reverse.sqlite`

Counts from `SourceGraphBuilder(include_gameplay=True, include_asset_maps=False,
include_reference_rows=False, emit_followups=False)`:

- `requires_item`: 4,324
- `item_required_by_gameplay`: 4,324
- reverse `item_gold` requirements: 848

Sample reverse edges showed `item:item_char_break_stage_1_2` pointing back to
multiple `character_breakthrough:*:charBreak20` and `charBreak40` owners with
the original `characterBreakthrough.requiredItem` evidence and counts.
