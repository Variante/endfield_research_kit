# AbilitySystemData UIData Recovery - 2026-06-29

## Scope

Focused pass on the `Beyond.Gameplay.Core.AbilitySystemData` tail immediately
after `SkillDataBundle.defaultCmdMapping`. The previous combo-condition pass
left a repeated 26-word zero prefix before the first buff string hint. This pass
identifies and decodes that prefix as `AbilitySystemData.UIData`.

## Metadata Evidence

The focused IL2CPP metadata dump used:

```text
D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat
version: 29
sha256: cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df
```

`AbilitySystemData` field order after `skillDataBundle`:

```text
3 uiData: AbilitySystemData.UIData
4 dashBuff: List<BuffInput>
5 buffDuringPoiseExist: List<BuffInput>
6 buffDuringZeroPoise: List<BuffInput>
7 plungingAttackData: AbilitySystemData.PlungingAttackData
...
```

`AbilitySystemData.UIData` field order:

```text
showBigHeadBar: bool
useSpecificDamageTextParam: bool
damageTextRelated: AbilitySystemData.DamageTextData
overrideHeadBarDeltaTowardCamera: bool
headBarDeltaTowardCamera: float
headBar2DOffset: Vector2
useHeadBarGuideLine: bool
heightInRangeNoFollow: bool
heightRange: Vector2
heightFollowMountPoint: MountPoint
```

`AbilitySystemData.DamageTextData` field order:

```text
mainChrDmgTxtSpawnOffset: Vector2
mainChrDmgTxtMoveSpawnOffset: Vector2
mainChrDmgTxtMaxMoveNum: int
mainChrDmgTxtMoveSpawnWaitTime: float
guardDmgTxtSpawnOffset: Vector2
guardDmgTxtSpawnAreaSize: Vector2
immuneTxtSpawnOffset: Vector2
immuneTxtSpawnAreaSize: Vector2
immuneTxtCooldown: float
```

This exactly accounts for the repeated 26 serialized int32/float32 words that
previously preceded the first remaining string hint.

## Parser Change

`AnimeStudio.CLI/Exporter.cs` now attempts `TryReadAbilitySystemUIData` after a
successful `SkillDataBundle` decode. The helper uses a local reader and only
advances the main reader after the whole `UIData` layout is consumed, so unknown
future variants leave the tail preserved rather than misaligned.

Fields are emitted under:

```text
uiData.layout = Beyond.Gameplay.Core.AbilitySystemData.UIData
uiData.damageTextRelated
uiData.headBar2DOffset
uiData.heightRange
```

## Validation

Command pattern:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe <chunk> tmp\ability_system_uidata_after_20260629\<chunk> --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op All --map_type JSON --export_type JSON --types MonoBehaviour:Both --names '^data_chr_' --dummy_dlls tools\DummyDll
```

Focused chunks:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

Results:

```text
json_files: 31
parse_errors: 0
AbilitySystemData rows: 28
AbilitySystemData decoded: 28
AbilitySystemData diagnostics: 0
AbilitySystemData $unparsed: 0
all $diagnostic: 0
all $unparsed: 0
uiData rows: 28
```

Every focused row had `uiData` values equal to zero/false in this corpus. The
remaining raw tail shrank by exactly 26 words in all 28 rows.

The new tail start is the `dashBuff` list. Typical first fields are:

```text
dashBuff.count = 1
dashBuff[0].buffId = buff_common_dash
```

Outliers:

```text
data_chr_0016_laevat: dashBuff.count = 2, first buff = buff_chr_0016_laevat_ult_dash
data_chr_0019_karin: dashBuff.count = 2, includes buff_common_dash_immune
data_chr_0021_whiten: dashBuff.count = 2, includes buff_common_dash_immune
data_chr_0030_zhuangfy: first buff = buff_chr_0030_zhuangfy_dash
```

## Remaining Unknowns

The next section is `List<BuffInput>` for `dashBuff`,
`buffDuringPoiseExist`, and `buffDuringZeroPoise`. `BuffInput.buffId` and
`assignBlackboard` are clear, but `assignItems` contains
`Beyond.Blackboard.DataPair` records whose nested value serialization is not yet
fully proven from metadata alone. The next useful pass should focus on
`BuffInput.assignItems` raw layout before promoting a parser for the three buff
lists.
