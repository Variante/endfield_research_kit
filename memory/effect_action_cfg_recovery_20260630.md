# EffectActionCfg Recovery - 2026-06-30

## Scope

Focused recovery pass for `Beyond.Gameplay.EffectActionCfg` when serialized as
`AbilitySystemData.deadEffect`.

Validation output:

- `tmp/ability_system_effectcfg_named_after_20260630/`

Focused source chunks:

- `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk`
- `71FC2E71A9F249B382BF8DAED3BCEE65.chk`
- `FBAD673F662CF3EACDDB14A65999F7EF.chk`

## Implemented

AnimeStudio now decodes `deadEffect` as named
`Beyond.Gameplay.EffectActionCfg` fields instead of preserving one opaque
107-word raw block.

The observed Unity MonoBehaviour payload follows IL2CPP metadata field order
with one important omission:

```text
EffectActionCfg fields F00-F14
omit F15 centerOffset
EffectActionCfg fields F16-F75
```

This produces the observed 107 int32 words before the enclosing
`AbilitySystemData.effectScale` field.

`BlackboardDouble` remains partial by design: it is still emitted as a raw
3-word wrapper plus a float candidate, because the internal meaning of the
three words is not fully proven.

## Validation

Command shape:

```bat
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  <chunk> tmp\ability_system_effectcfg_named_after_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op All --map_type JSON ^
  --export_type JSON --types MonoBehaviour:Both --names "^data_chr_" ^
  --dummy_dlls tools\DummyDll
```

Results:

- CLI focused export completed with no Warning/Error log output.
- JSON files: 29 total, including `assets_map.json`.
- JSON parse errors: 0.
- `AbilitySystemData` rows: 28.
- `$diagnostic` markers: 0.
- `$unparsed` markers: 0.
- `deadEffect` named `EffectActionCfg` blocks: 28 / 28.
- old `deadEffect.rawWords` opaque blocks: 0 / 28.
- `deadEffect.serializedWordCount`: 107 in 28 / 28 rows.
- `remainingRawWords`: 0 words in 28 / 28 rows.

Observed stable values in the focused rows:

- `deadEffect.scale`: `(1.0, 1.0, 1.0)` in 28 / 28 rows.
- `deadEffect.effectName`, `limitKey`, and `weaponVfxKey`: empty in 28 / 28 rows.
- `deadEffect.effectPosData.count`: 0 in 28 / 28 rows.
- `deadEffect.weaponVfxIndex`: `-1` in 28 / 28 rows.
- enclosing `effectScale`: `1.0` in 28 / 28 rows.
- enclosing `healthType`: `Normal` / `0` in 28 / 28 rows.

Build verification:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Final rebuild result: 0 warnings, 0 errors.

## Evidence And Caveats

Alternative layout checks:

- all metadata fields included: fails, because `limitKey` becomes a bogus
  length and the top-level tail no longer aligns.
- omit only `centerOffset`: passes all 28 focused rows and aligns the enclosing
  `AbilitySystemData` tail.
- omit only `forceGuardEffect`: wrong length for the observed top-level tail.
- omit both `forceGuardEffect` and `centerOffset`: wrong length for the
  observed top-level tail.

`AbilitySystemData.overrideDeadEffect` remains metadata-known but not
payload-proven for these rows. The focused Unity payloads still start directly
with `deadEffect` after `skillCameraConfig`.

`EffectActionCfg.centerOffset` is metadata-known but omitted from the observed
Unity payload layout. MemoryPack setter evidence is not identical to the Unity
MonoBehaviour layout, so the exporter follows the validated Unity payload.

## Remaining Unknowns

- The internal three-word meaning of `Beyond.Blackboard.BlackboardDouble` still
  needs a separate pass.
- Broader non-default `EffectActionCfg` rows with non-empty strings or
  `effectPosData` entries should be used to stress-test the parser beyond the
  focused `data_chr_*` default-like rows.
