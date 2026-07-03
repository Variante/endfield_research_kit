# Responsive Trigger Policy Source Graph Recovery - 2026-07-03

## Scope

`ResponsiveTriggers.json` defines authored runtime policy fields for responsive
dialog and bark trigger types. The graph already linked trigger types to event
templates and base trigger types; this pass adds explicit numeric policy nodes
for cooldown, voice-limit, interrupt, invalid-state, and band-limit fields.

This improves queries from "what response/audio exists?" toward "what authored
runtime policy governs this response trigger?" It does not recover enum names,
runtime scheduler code, state-machine behavior, or live trigger availability.

## Source Table

- `export_full/structured/StreamingAssets/Table/ResponsiveTriggers.json`

The current table has 3 trigger groups and 165 trigger types.

## Graph Change

New node kinds:

- `responsive_cd_type`
- `responsive_vo_limit_type`
- `responsive_interrupt_type`
- `responsive_invalid_state_mask`
- `responsive_band_limit_count`

New forward and reverse edge kinds:

- `responsive_trigger_type_has_cd_type`
- `responsive_cd_type_used_by_trigger_type`
- `responsive_trigger_type_has_vo_limit_type`
- `responsive_vo_limit_type_used_by_trigger_type`
- `responsive_trigger_type_has_interrupt_type`
- `responsive_interrupt_type_used_by_trigger_type`
- `responsive_trigger_type_has_invalid_state_mask`
- `responsive_invalid_state_mask_used_by_trigger_type`
- `responsive_trigger_type_has_band_limit_count`
- `responsive_band_limit_count_used_by_trigger_type`

Each policy edge preserves scalar runtime-policy fields in its payload:

- `cdTime`
- `chatCd`
- `delay`
- `priority`
- `probability`
- `samePriorityInterrupt`
- the specific policy field value for the edge

## Validation

Focused temporary graph:

```bat
tmp\responsive_policy_validation.sqlite
```

Focused ingest:

- `ingest_npc_voice_bark_semantics()`

Node counts:

- `responsive_dialog_group`: 7
- `responsive_trigger_type`: 165
- `responsive_cd_type`: 3
- `responsive_vo_limit_type`: 5
- `responsive_interrupt_type`: 3
- `responsive_invalid_state_mask`: 7
- `responsive_band_limit_count`: 4
- `responsive_event_template`: 63

Policy value sets:

- `responsive_cd_type`: `0`, `1`, `3`
- `responsive_vo_limit_type`: `1`, `2`, `3`, `4`, `5`
- `responsive_interrupt_type`: `1`, `2`, `4`
- `responsive_invalid_state_mask`: `0`, `8`, `9`, `10`, `11`, `12`, `14`
- `responsive_band_limit_count`: `-1`, `1`, `2`, `3`

Forward/reverse counts:

- `responsive_trigger_type_has_cd_type`: 165 /
  `responsive_cd_type_used_by_trigger_type`: 165
- `responsive_trigger_type_has_vo_limit_type`: 165 /
  `responsive_vo_limit_type_used_by_trigger_type`: 165
- `responsive_trigger_type_has_interrupt_type`: 165 /
  `responsive_interrupt_type_used_by_trigger_type`: 165
- `responsive_trigger_type_has_invalid_state_mask`: 165 /
  `responsive_invalid_state_mask_used_by_trigger_type`: 165
- `responsive_trigger_type_has_band_limit_count`: 165 /
  `responsive_band_limit_count_used_by_trigger_type`: 165

Existing responsive edges in the focused graph:

- `responsive_trigger_type_uses_event_template`: 165
- `responsive_trigger_type_extends`: 5

Smoke queries:

```bat
python tools\endfield_source_graph.py query responsive_cd_type:3 --db tmp\responsive_policy_validation.sqlite --limit 12
python tools\endfield_source_graph.py query responsive_invalid_state_mask:8 --db tmp\responsive_policy_validation.sqlite --limit 12
python tools\endfield_source_graph.py query 43 --kind responsive_trigger_type --db tmp\responsive_policy_validation.sqlite --limit 12
```

The trigger-type `43` query shows incoming policy edges for band limit `2`,
cooldown type `3`, interrupt type `2`, invalid-state mask `8`, and its
responsive dialog trigger usage.
