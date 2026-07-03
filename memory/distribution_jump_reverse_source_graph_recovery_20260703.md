# Distribution jump reverse source graph recovery - 2026-07-03

## Context

`DistributionInfoTable.json` defines authored distribution entries for map and
world-energy destinations. The source graph already emitted forward
`distribution_info_jump` edges from each `distribution_info` node to its
`system_jump`, but a query starting at `jump_map*` or `jump_world_energy*`
could not discover the distribution entry that used it.

## Implementation

Updated the shared `add_system_jump_edge()` reverse map in
`tools/endfield_source_graph.py`:

- `distribution_info_jump` now emits
  `system_jump_used_by_distribution_info`.

No new node kinds or ingest passes were needed.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/distribution_jump_reverse_validation.sqlite` with only
`ingest_mode_constant_semantics()`.

Observed counts:

- `distribution_info_jump`: 21
- `system_jump_used_by_distribution_info`: 21

Smoke query:

- `jump_map02_lv002` now returns
  `system_jump_used_by_distribution_info -> distribution_map02_lv002`.
