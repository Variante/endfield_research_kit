# Option Branch Gap Query Source Graph Recovery - 2026-07-06

## Scope

This pass improves story-recovery review ergonomics only. It does not change
Story WebUI output, promote inferred option routes, or update manual overrides.

## Change

`tools/endfield_source_graph.py` now exposes the generated
`reports/source_graph/option_branch_gaps.json` follow-up through a CLI shortcut:

```bat
python tools\endfield_source_graph.py option-gaps
python tools\endfield_source_graph.py option-gaps --conflicts
python tools\endfield_source_graph.py option-gaps --audit-only
python tools\endfield_source_graph.py option-gaps --recommendation nearbyRuntimeJumpIncompleteOptionCoverage
```

The follow-up emitter also writes
`reports/source_graph/option_branch_gaps.md`, summarizing inferred option-anchor
gaps together with runtime jump route-audit evidence.

## Validation

Regenerated the ignored option branch follow-up from the current source graph
DB and verified:

- total option-gap scenes: 5
- audit-only runtime-route scenes: 4
- runtime-conflict scenes: 3
- `nearbyRuntimeJumpContradictsInferredPath`: 3
- `nearbyRuntimeJumpIncompleteOptionCoverage`: 1

The CLI filters returned:

- `option-gaps --conflicts`: `dlg_c28m3_10`, `dlg_e6m1_10`, `dlg_e6m4_14`
- `option-gaps --recommendation nearbyRuntimeJumpIncompleteOptionCoverage`:
  `dlg_c28m3_23`

During validation, the generated markdown initially displayed the numeric scene
index `5` for `dlg_gm01m25_5` because the emitter preferred a numeric `scene`
field over the stable story key. The emitter now prefers `key` / `storyKey` and
only falls back to `scene` when it is already a string.

## Boundary

This is diagnostic source-graph evidence. The conflict scenes still require
manual review or stronger runtime binding before changing authoritative story
order or option override data.
