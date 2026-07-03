# Ability Entity Animation Component Recovery - 2026-07-03

## Context

The post-diagnostics MonoBehaviour index still had 27 unparsed
`Beyond.Gameplay.View.AbilityEntityAnimationComponentData` managed references
inside `data_abilityentity_*` rows. The heuristic view showed these payloads
were almost entirely aligned animation config paths, with two 4-byte rows that
contained only a zero string length.

## Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now decodes
`AbilityEntityAnimationComponentData` as a single aligned UTF-8
`animationConfigPath` string.

The decoder validates non-empty paths with:

- prefix: `Data/Json/AnimationConfig/`
- suffix: `.json`

Empty-string rows are accepted and emitted with
`animationConfigPathPresent = false`.

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Targeted exports:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\abilityentity_animation_after_68b3 --game ArknightsEndfield --logger_flags Warning Error --group_assets BySource --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\abilityentity_animation_after_71fc --game ArknightsEndfield --logger_flags Warning Error --group_assets BySource --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\abilityentity_animation_after_fbad --game ArknightsEndfield --logger_flags Warning Error --group_assets BySource --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_chr_0030_zhuangfy_ult"
```

Focused output metrics:

| Chunk | Decoded animation components |
| --- | ---: |
| `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` | 23 |
| `71FC2E71A9F249B382BF8DAED3BCEE65.chk` | 2 |
| `FBAD673F662CF3EACDDB14A65999F7EF.chk` | 2 |

Total observed family coverage:

| Metric | Result |
| --- | ---: |
| `AbilityEntityAnimationComponentData` records | 27 |
| Decoded records | 27 |
| Empty-path records | 2 |
| Animation-specific `$unparsed` records | 0 |
| Animation-specific `$heuristic` records | 0 |
| Animation-specific `decodeError` records | 0 |

Observed payload lengths: `4`, `60`, `76`, `80`, `84`, `88`, and `92` bytes.
