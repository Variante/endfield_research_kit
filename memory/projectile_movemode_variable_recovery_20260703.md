# Projectile MoveModeData Variable Boundary Recovery - 2026-07-03

## Scope

`ProjectileComponentData` already decoded the projectile tail with a fixed
124-word `MoveModeData` value assumption. The frontier audit showed
`MoveModeData/StructuredSuffix` still had a small failure set, and focused
projectile JSON proved those failures were not corrupt data: some projectile
move modes contain longer `AnimationCurve` payloads, so the fixed boundary cut
through curve keyframes and shifted the following tail.

## Change

`AnimeStudio.CLI/Exporter.cs` now tries a guarded metadata-ordered
variable-length `MoveModeData` reader before falling back to the older fixed
124-word diagnostic reader.

The new path decodes:

- enum/blackboard prefix through `parabolaDef`
- `speed`, `speedCurve`, `useSpeedScaleWithDistance`,
  `speedScaleWithDistance`
- movement booleans, angular/travel/gravity fields, and both Bezier points

The dictionary accepts the variable boundary only when the following
`ProjectileComponentData` tail still validates through the existing
`showAlertEffect + alertEffect + sound tail` suffix guard.

## Metadata Notes

IL2CPP metadata lists `m_parabolaSpeedInfo`, `m_bezierSpeedInfo`, and
`m_speedCurveInfo` in `MoveModeData`, all with unresolved type index `157142`.
A sidecar metadata/sample audit found that `157142` behaves like an unresolved
string type across many fields, but current projectile samples serialize
`speed` directly after `parabolaDef`; no sampled bytes supported consuming
those three fields as serialized strings.

The exporter therefore emits those fields as omitted metadata fields with type
label `inferred string / unresolved typeIndex 157142`.

## Validation

- `.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore` passed.
- `git -C tools\AnimeStudio diff --check -- AnimeStudio.CLI\Exporter.cs`
  passed.
- Focused StreamingAssets export using
  `tmp\projectile_curve_filter_20260703.json`:
  - 300 projectile JSON files
  - 300 move-mode dictionaries used `metadataVariableLength`
  - 306 `MoveModeData` values decoded
  - observed value word counts: 124, 126, 128, 131, 133, 138, 142, 144,
    145, 146, 149, 150, 152, and 292
  - no `$unparsed`, `$heuristic`, or old `MoveModeData/StructuredSuffix`
    fallback markers
- Focused Persistent export using
  `tmp\projectile_component_all_20260630\source_01.filter_data.json`:
  - 10 projectile JSON files
  - 10 move-mode dictionaries used `metadataVariableLength`
  - 25 `MoveModeData` values decoded
  - no `$unparsed`, `$heuristic`, or old structured suffix markers

## Remaining Partial Surface

`MoveModeData` is still marked partial because blackboard wrapper internals and
enum value names remain diagnostic, and the three metadata-listed speed-info
fields are omitted from observed payloads rather than semantically explained.
The enclosing `ProjectileComponentData` effect-list prefix remains raw until
its collection shape is independently validated.
