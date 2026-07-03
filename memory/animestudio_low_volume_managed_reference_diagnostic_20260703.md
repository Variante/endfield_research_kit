# AnimeStudio Low-Volume Managed Reference Diagnostic Decode - 2026-07-03

## Context

After the camera-config diagnostic decode, the current MonoBehaviour residual
set still had nine non-camera `unparsed` rows in
`tmp/decoded_index_mono_current_20260703`:

- `CharacterHeightData`
- `WeaponExhibitData`
- `CheckRpgEquipCount`
- `LineFollower`
- `PlayLineSound`
- `Cube`
- `Prism`

All were recovered managed-reference entries. The generic serialized TypeTree
reader failed inside `ReferencedObjectData`, but the recovery layer had already
identified the managed-reference type headers and payload bounds.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now has a final known-class
diagnostic fallback after all semantic managed-reference decoders. It emits:

- `$partial` typed raw-word diagnostics for small word-aligned gameplay payloads:
  - `Beyond.Gameplay.CharacterHeightData`
  - `Beyond.Gameplay.WeaponExhibitData`
  - `Beyond.Gameplay.LineFollower`
  - `Beyond.Gameplay.PlayLineSound`
  - `Beyond.Gameplay.Core.CheckRpgEquipCount`
- typed empty decoded data for zero-byte ProBuilder shape payloads:
  - `UnityEngine.ProBuilder.Shapes.Cube`
  - `UnityEngine.ProBuilder.Shapes.Prism`

The fallback does not run until all semantic decoders decline the payload. It
does not claim field names; it preserves type identity, payload bounds, and
word-level int32/float32/ascii diagnostics.

## Validation

Rebuilt the CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Targeted probes:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\low_volume_mono_probe_chunk68_after_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^(CharacterHeightConfig|WeaponExhibitConfig|team_effect_rpg_check_equip_cnt_dmg_up|MonoBehaviour#1656866|MonoBehaviour#1781336|MonoBehaviour#1781324|MonoBehaviour#1781328)$"

.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\low_volume_mono_probe_chunk71_filter_after_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --filter_data tmp\linefollower_filter_20260703.json

.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\low_volume_mono_probe_probuilder_after_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --filter_data tmp\probuilder_shape_filter_20260703.json
```

Combined probe result:

- 15 JSON files emitted.
- 23 low-volume gameplay payloads emitted as `$partial` with `rawWords`.
- 4 ProBuilder shape payloads emitted as typed zero-length decoded data.
- 0 `$heuristic` markers.
- 0 `$unparsed` markers.
- No `Export ... error` or `Partially decoded MonoBehaviour` lines in targeted
  probes.

Together with the camera diagnostic decode, the next full MonoBehaviour refresh
should move the current 16 `unparsed` rows to typed partial/decoded evidence.
