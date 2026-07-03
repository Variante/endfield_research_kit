# LineFollower Structural Recovery - 2026-07-03

## Scope

This pass improves AnimeStudio managed-reference recovery for
`Beyond.Gameplay.LineFollower` payloads. The previous exporter preserved these
48 payloads as generic low-volume int32/float32 word diagnostics. The new
decoder keeps the payloads partial, but promotes the stable row structure into
named fields.

This is structural recovery only. The nested `line` field remains unresolved in
IL2CPP metadata and is preserved as raw words.

## Evidence

IL2CPP metadata shows:

- `Beyond.Gameplay.LineFollower.data`
- nested `LineFollowerData` fields:
  - `line` with unresolved type index `143013`
  - `useConfigSourceMountPoint`
  - `source`
  - `useConfigTargetMountPoint`
  - `target`
  - `positionNum`

The 48 observed payloads all follow:

```text
int32 data.count
data.count * 32-byte LineFollowerData rows
```

The nested `line` field occupies three int32 words in all current samples.

## Implementation

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now routes
`Gameplay.Beyond/Beyond.Gameplay/LineFollower` through a dedicated decoder before
the generic low-volume diagnostic fallback.

Each row emits:

- `line.rawWords` with three preserved int32 words
- `useConfigSourceMountPoint`
- `source`
- `useConfigTargetMountPoint`
- `target`
- `positionNum`

The output remains:

- `$decoded: true`
- `$partial: true`
- `$inferred: true`

## Validation

Built AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Generated a focused 48-entry filter from
`tmp\decoded_index_mono_refreshed_20260703\groups\MonoBehaviour_StreamingAssets_managed-reference_class_LineFollower_41ac20ba54.json`
and the StreamingAssets AnimeStudio asset map.

Focused export output:

```text
tmp\linefollower_structural_after_20260703
```

Coverage:

- `48 / 48` LineFollower managed references exported
- `0` validation errors
- no LineFollower output retained the old top-level generic `rawWords`
- row counts by payload:
  - `1` row: `9`
  - `2` rows: `6`
  - `3` rows: `30`
  - `4` rows: `3`
- payload lengths:
  - `36`: `9`
  - `68`: `6`
  - `100`: `30`
  - `132`: `3`

Observed `positionNum` values across rows:

- `2`: `110`
- `5`: `1`
- `10`: `12`

The decoder is intentionally conservative. If future payloads do not match the
count and row-size invariant, it declines and lets the existing diagnostic
fallback preserve the raw payload.
