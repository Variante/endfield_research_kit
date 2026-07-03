# Character Height And Animation Handler Recovery - 2026-07-03

## Scope

This pass promotes two small MonoBehaviour managed-reference frontiers from
generic raw diagnostics into named fields:

- `Beyond.Gameplay.CharacterHeightData`
- selected `Beyond.Gameplay.View.Animation.FastAnimationEventHandler` subclasses

It does not attempt to resolve larger character, enemy, ability-entity, camera,
or weapon-exhibit payloads.

## CharacterHeightData

IL2CPP metadata names the payload fields:

- `isShadowFadeInCharInfo`
- `charInfoShadowFadeConfig`
- `isShadowFadeInFormation`
- `formationShadowFadeConfig`

`CharacterShadowFadeConfig` contains:

- `circleFadeDistance`
- `circleFadeSmoothness`

The observed payloads are 24 bytes:

```text
bool32 isShadowFadeInCharInfo
float32 charInfoShadowFadeConfig.circleFadeDistance
float32 charInfoShadowFadeConfig.circleFadeSmoothness
bool32 isShadowFadeInFormation
float32 formationShadowFadeConfig.circleFadeDistance
float32 formationShadowFadeConfig.circleFadeSmoothness
```

Current values across all four references:

- `isShadowFadeInCharInfo`: `true`
- `charInfoShadowFadeConfig`: `0.3`, `2.5`
- `isShadowFadeInFormation`: `false`
- `formationShadowFadeConfig`: `0.0`, `0.0`

The decoder requires exactly 24 bytes and uses bounded float reads.

## Animation Handler Classes

The existing `FastAnimationEventHandler` decoder reads the shared 4-byte
`_weightThreshold` base-field payload. This pass extends that decoder to these
observed subclasses:

- `BattleCustomEventHandler`
- `RendererVisibilityHandler`
- `SpawnEntityHandler`

IL2CPP metadata shows these classes as animation handlers with no additional
serialized instance fields relevant to the observed payloads. The shared base
field is therefore the only 4-byte payload content.

## Validation

Built AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

The build succeeded. It reported existing warnings in AnimeStudio core and YAML
utility projects, with `0` errors.

Generated a focused 13-entry filter from the refreshed MonoBehaviour index and
the StreamingAssets AnimeStudio asset map.

Focused export output:

```text
tmp\height_animation_handlers_after_20260703
```

Validation results:

- JSON files emitted by focused export: `413`
- `CharacterHeightData`: `4` refs decoded
- `SpawnEntityHandler`: `8` refs decoded
- `RendererVisibilityHandler`: `2` refs decoded
- `BattleCustomEventHandler`: `2` refs decoded
- validation assertion errors: `0`

Observed `_weightThreshold` values:

- `SpawnEntityHandler`: `0.5` across `8` refs
- `RendererVisibilityHandler`: `0.0` across `2` refs
- `BattleCustomEventHandler`: `0.0` across `2` refs

The touched classes no longer emit `$unparsed`, `$heuristic`,
`heuristicRawWordHints`, or top-level generic `rawWords` in the focused export.
