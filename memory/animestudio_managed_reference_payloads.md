# AnimeStudio Managed-Reference Payloads

Generated 2026-06-28 while investigating positive
`ManagedReferencesRegistry` payloads that were previously recovered only as
heuristic string/RID hints.

## Scope

This pass only touched MonoBehaviour managed-reference payload handling in
`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`.

The targeted recurring sample is the `CharacterDisplayConfig` MonoBehaviour
from:

```text
D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk
PathID 1075246499258409311
```

The object has 31 positive managed-reference entries of type:

```text
Beyond.Gameplay.CharacterDisplayData, Gameplay.Beyond
```

## Metadata Findings

`tools/DummyDll/Gameplay.Beyond.dll` was not reliable for this work. Mono.Cecil
could read the assembly, but the type table was garbled-looking, many names
were truncated, and fields were reported as zero. Raw byte string search also
did not find `CharacterDisplayData` in the DummyDll.

The installed IL2CPP metadata at:

```text
D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat
```

did contain useful authoritative field names. The local
`tools/endfield-il2cpp/catalog_option_flow_metadata.py` parser confirmed:

- `Beyond.Gameplay.CharacterDisplayData` fields:
  `decoItemConfig`, `potentialEffectConfig`, `weaponConfig`, `height`,
  `cameraConfig`, `charInfoCameraGroup`, `charInfoLightGroup`,
  `talentPanelRotate`, `talentPanelScale`, `overviewImgOffset`,
  `overrideSpIdleConfig`, `charRelaxSpIdleConfig`,
  `charRelaxReactConfig`, and `charId`.
- Nested field names for `DecoItemDisplayData`, `PotentialEffectData`,
  `WeaponDisplayConfig`, `WeaponData`, `StaticWeaponData`,
  `WeaponEffectData`, `CameraConfig`, `CharRelaxSpIdleConfig`, and
  `CharRelaxReactConfig`.
- `height` maps to the enum `Beyond.Gameplay.CharacterHeight`, not the larger
  table row type `CharacterHeightData`.

The lightweight metadata parser still cannot resolve all generic IL2CPP field
type indexes by itself. The final byte layout was therefore proven by combining
the metadata field order with raw sidecar bytes from a targeted export.

## Parsed Layout

The implemented `CharacterDisplayData` decoder consumes every byte in a payload
and rejects the layout if any count, string, bool, float, or final offset is
invalid.

Decoded fields:

- `decoItemConfig.decoItemData[]`: `prefabPath`, `mountPoint`
- `potentialEffectConfig.potentialEffects[]`: `name`, `mountPoint`,
  `followScale`, `followRotation`, `offset`
- `weaponConfig.weaponData[]`: `weaponIndex`, `vfxKey`, `weaponScale`,
  idle/fight flags and mount points, `overrideController`, `weaponPath`
- `weaponConfig.staticWeaponData[]`: `weaponIndex`, `vfxKey`, `weaponScale`,
  static `weaponPath`, idle/fight flags and mount points,
  `overrideController`, `nodeUIIdle`
- `weaponConfig.weaponAppearEffectName[]`
- `weaponConfig.weaponDisappearEffectName[]`
- `weaponConfig.weaponAppearEffectDuration`
- `weaponConfig.weaponDisappearEffectDuration`
- `weaponConfig.weaponChangeEffects[]`
- `height`: enum value plus name
- `cameraConfig.charFormationOverride`
- `charInfoCameraGroup`
- `charInfoLightGroup`
- `talentPanelRotate`
- `talentPanelScale`
- `overviewImgOffset`
- `overrideSpIdleConfig`
- `charRelaxSpIdleConfig`
- `charRelaxReactConfig`
- `charId`

The 31-entry target set covered these weapon layout variants:

| weaponData | staticWeaponData | appear strings | change effects | Entries |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 3 | 1 | 18 |
| 2 | 0 | 3 | 2 | 4 |
| 4 | 1 | 3 | 1 | 1 |
| 1 | 1 | 3 | 1 | 3 |
| 3 | 1 | 3 | 3 | 1 |
| 1 | 0 | 1 | 0 | 1 |
| 0 | 0 | 1 | 0 | 1 |
| 4 | 0 | 3 | 4 | 1 |
| 3 | 0 | 3 | 3 | 1 |

## Verification

Compile verification used a separate output directory because another active
AnimeStudio process was locking the normal release output:

```bat
.\tools\AnimeStudio\.dotnet\dotnet.exe build ^
  .\tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj ^
  -c Release -f net9.0-windows --no-restore ^
  -p:OutDir=D:\fluffy-dump\tools\AnimeStudio\AnimeStudio.CLI\bin\codex-mb-verify\
```

Result: build succeeded with 0 errors. Existing TODO warnings from
`AnimeStudio.Utility` remain.

Targeted CharacterDisplayConfig export:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\codex-mb-verify\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" ^
  tmp\animestudio_mb_characterdisplay_decoded ^
  --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType ^
  --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll ^
  --filter_data tmp\animestudio_monobehaviour_character_filter.json
```

Result:

- exit code 0
- `managedReferencesRegistryRecovered: true`
- `references.RefIds`: 31 entries
- decoded `Beyond.Gameplay.CharacterDisplayData`: 31
- heuristic/unparsed `CharacterDisplayData`: 0

Existing negative-RID sentinel dialog sample was also rerun through the same
verification build and still exported `rid = -2` as the null sentinel payload.

## Remaining Limits

- This is a real parser for the recurring `CharacterDisplayData` family, not a
  generic deserializer for every positive managed-reference type.
- The local DummyDlls are not currently sufficient as a field source for this
  class family. Broader generic deserialization would need better IL2CPP type
  index resolution, likely by joining `global-metadata.dat` with
  GameAssembly/metadata-registration type tables.
- A full MonoBehaviour `json_by_type` refresh has not been run in this pass.
