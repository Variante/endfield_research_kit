# AbilitySystemData Post-Camera Tail Recovery - 2026-06-30

## Scope

Focused recovery pass for the tail of
`Beyond.Gameplay.Core.AbilitySystemData` after `skillCameraConfig`.

Validation output:

- `tmp/ability_system_post_camera_corrected_after_20260630/`

Focused source chunks:

- `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk`
- `71FC2E71A9F249B382BF8DAED3BCEE65.chk`
- `FBAD673F662CF3EACDDB14A65999F7EF.chk`

## Implemented

AnimeStudio now decodes the top-level post-camera fields observed in the Unity
payload:

```text
deadEffect: Beyond.Gameplay.EffectActionCfg
effectScale: float
isPlayHitFlash: bool
hitFlashAsset: string
healthType: Beyond.Gameplay.Core.HealthType
preloadAbilityEntities: SerializeFieldDictionary<string, int>
maxPotentialEffectBuffId: string
```

`deadEffect` is intentionally emitted as a partial `EffectActionCfg` block:

- fixed 107 raw int32 words in all focused `data_chr_*` rows;
- stable nonzero-word signature in all 28 rows;
- not yet internally decoded into the 76 fields known from IL2CPP metadata.

This is a real recovery step, not warning suppression: the exporter now names
and consumes the top-level tail fields while preserving the complex object that
is not fully understood yet.

Important caveat: IL2CPP metadata lists `overrideDeadEffect` before
`deadEffect`, but the focused Unity payloads align only when `deadEffect` starts
immediately after `skillCameraConfig`. The exporter does not emit
`overrideDeadEffect` for these rows until a validated payload variant proves it
is serialized.

## Validation

Command shape:

```bat
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  <chunk> tmp\ability_system_post_camera_corrected_after_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op All --map_type JSON ^
  --export_type JSON --types MonoBehaviour:Both --names "^data_chr_" ^
  --dummy_dlls tools\DummyDll
```

Results:

- JSON files: 29 total, including `assets_map.json`.
- `data_chr_*` MonoBehaviour files: 28.
- JSON parse errors: 0.
- `AbilitySystemData` rows: 28.
- each observed post-camera field decoded in 28 / 28 rows.
- `overrideDeadEffect` present in output: 0 / 28 rows.
- `remainingRawWords` distribution: 0 words in 28 / 28 rows.
- `$diagnostic` rows in focused `AbilitySystemData`: 0.
- `$unparsed` markers in focused `AbilitySystemData`: 0.

Observed values:

- `effectScale`: 1.0 in 28 / 28 rows.
- `isPlayHitFlash`: false in 28 / 28 rows.
- `hitFlashAsset`: empty string in 28 / 28 rows.
- `healthType`: `Normal` / `0` in 28 / 28 rows.
- `preloadAbilityEntities`: empty in 27 / 28 rows.
- `maxPotentialEffectBuffId`: empty in 16 / 28 rows, non-empty in 12 / 28 rows.

Non-empty `preloadAbilityEntities`:

| row | entries |
| --- | --- |
| `data_chr_0030_zhuangfy` | `abilityentity_chr_0030_zhuangfy_ult_mirror=1`, `abilityentity_chr_0030_zhuangfy_ult=1` |

Non-empty `maxPotentialEffectBuffId` rows:

- `data_chr_0009_azrila`: `buff_chr_0009_azrila_potential_5`
- `data_chr_0013_aglina`: `buff_chr_0013_aglina_potential_5`
- `data_chr_0015_lifeng`: `buff_chr_0015_lifeng_potential_5_vfx`
- `data_chr_0016_laevat`: `buff_chr_0016_laevat_potential_5_vfx`
- `data_chr_0017_yvonne`: `buff_chr_0017_yvonne_potential_5_effect`
- `data_chr_0025_ardelia`: `buff_chr_0025_ardelia_potential5_vfx`
- `data_chr_0026_lastrite`: `buff_chr_0026_lastrite_potential5_vfx`
- `data_chr_0027_tangtang`: `buff_chr_0027_tangtang_potential_5_effect`
- `data_chr_0028_wulfa`: `buff_chr_0028_wulfa_potential_5_effect`
- `data_chr_0029_pograni`: `buff_chr_0029_pograni_potential_5_effect`
- `data_chr_0030_zhuangfy`: `buff_chr_0030_zhuangfy_potential5_vfx`
- `data_chr_0031_mifu`: `buff_chr_0031_mifu_potential_5`

`deadEffect` nonzero word signature, relative to the start of the 107-word
`EffectActionCfg` block, is identical in all 28 rows:

```text
6=0x3f800000
7=0x3f800000
8=0x3f800000
9=1
12=1
15=1
35=1
41=0x40400000
58=1
61=1
64=1
84=1
87=1
90=1
93=1
97=-1
```

## Metadata Evidence

IL2CPP metadata lists the remaining `AbilitySystemData` tail as:

```text
overrideDeadEffect: bool
deadEffect: Beyond.Gameplay.EffectActionCfg
effectScale: float
isPlayHitFlash: bool
hitFlashAsset: string
healthType: Beyond.Gameplay.Core.HealthType
preloadAbilityEntities: Beyond.SerializeFieldDictionary<string, int>
maxPotentialEffectBuffId: string
```

The observed Unity payloads do not currently serialize `overrideDeadEffect` at
this boundary. Treat it as metadata-known but not payload-proven for these
focused rows.

`HealthType` values observed in metadata:

- `Normal = 0`
- `Independent = 2`

`EffectActionCfg` has 76 fields in metadata. The current pass does not claim to
decode those fields. A direct metadata-order parse becomes ambiguous in the
middle of the block, so the exporter preserves the fixed raw block under the
correct field name and layout.

## Remaining Unknowns

- `Beyond.Gameplay.EffectActionCfg` internal 76-field Unity serialized layout
  still needs a separate pass. The focused rows only show a stable default-like
  block, which is useful evidence but not enough to name every internal field
  safely.
- `overrideDeadEffect` exists in IL2CPP metadata but is not proven serialized in
  the focused Unity payloads.
- The full `MountPoint` enum remains only partially named in exporter helpers;
  this did not affect the focused post-camera tail because all relevant
  observed mount-like values inside the raw `deadEffect` block are preserved
  rather than interpreted.