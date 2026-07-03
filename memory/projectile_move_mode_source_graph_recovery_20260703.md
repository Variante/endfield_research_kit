# Projectile MoveMode Source Graph Recovery - 2026-07-03

## Scope

The source graph now exposes decoded projectile `MoveModeData` records from
partial MonoBehaviour frontier JSONs. This follows the projectile curve decode
work by making the active `export_full/` payloads queryable instead of leaving
curve and movement semantics only in memory notes.

The graph is intentionally evidence-first. It records the currently exported
decoded suffix status, enum numeric values, blackboard-key use, and
AnimationCurve summaries, but it does not assign unverified enum member names
or simulate projectile runtime behavior.

## Graph Additions

New node kinds:

- `projectile_move_mode`
- `projectile_animation_curve`
- `projectile_enum_value`
- `projectile_move_mode_decode_status`
- `projectile_move_mode_decode_error`

New edges:

- `monobehaviour_frontier_entry_has_projectile_move_mode`
- `projectile_move_mode_has_curve`
- `projectile_move_mode_enum_value`
- `projectile_move_mode_decode_status`
- `projectile_move_mode_decode_error`
- `projectile_move_mode_uses_blackboard_key`

Each `projectile_move_mode` node stores compact evidence for the move-mode key,
source JSON path, prefix enum values (`traceType`, `moveType`, `parabolaDef`),
offsets, and structured suffix status. Each `projectile_animation_curve` node
stores keyframe count, first/last keyframe summaries, wrap modes, rotation
order, and non-finite sentinel count.

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_monobehaviour_frontier_report()`:

- `projectile_move_mode`: 331
- `projectile_animation_curve`: 954
- `projectile_enum_value`: 11
- `projectile_move_mode_decode_status`: 2
- `projectile_move_mode_decode_error`: 7

Focused edge counts:

- `monobehaviour_frontier_entry_has_projectile_move_mode`: 331
- `projectile_move_mode_has_curve`: 954
- `projectile_move_mode_enum_value`: 993
- `projectile_move_mode_decode_status`: 331
- `projectile_move_mode_decode_error`: 14
- `projectile_move_mode_uses_blackboard_key`: 8

Current active `export_full/` suffix status:

- decoded: 317
- failed: 14

Current active `export_full/` curve nodes:

- `speedCurve`: 320
- `angularSpeedCurve`: 317
- `speedScaleWithDistance`: 317

Query checks:

- `speedCurve --kind projectile_animation_curve` resolves to projectile
  move-mode curve nodes with `structuredSuffix.speedCurve` evidence.
- `Beyond.Gameplay.ProjectileMoveType:0 --kind projectile_enum_value`
  resolves move-mode enum-value edges without inventing member names.
- `invalid AnimationCurve keyframe count 26 --kind
  projectile_move_mode_decode_error` resolves the two current active-export
  suffix failures carrying that signature.
- Projectile blackboard keys resolve through
  `projectile_move_mode_uses_blackboard_key` for keys such as
  `EntityBB_speed`, `EntityBB_Speed`, `EntityBB_time`, and
  `EntityBB_TrackTIme`.

## Interpretation

This closes a graph visibility gap, not the remaining exporter decode gap. The
active `export_full/` still carries 14 projectile suffix failures because it has
not been refreshed with the later AnimeStudio curve non-finite handling
documented in `memory/projectile_movemode_curve_recovery_20260703.md`. The
source graph now makes that distinction explicit: current exported evidence is
queryable, and the remaining decode-error signatures are visible as their own
nodes.
