# Remote Factory Template Recovery - 2026-07-03

## Scope

Recovered a narrow managed-reference layout in AnimeStudio for the three
remote factory mine item MonoBehaviours:

- `data_mine_item_iron_ore`
- `data_mine_item_originium_ore`
- `data_mine_item_quartz_sand`

## Evidence

All three unresolved `Beyond.Gameplay.RemoteFactoryEntityTemplateData` payloads
are 64 bytes. The observed word layout is:

- eight zero int32 words
- one float32 word exactly `1.0` (`0x3f800000`)
- int32 component count `3`
- three managed-reference RIDs targeting, in order:
  - `Beyond.Gameplay.Core.RemoteFactoryRootComponentData`
  - `Beyond.Gameplay.Core.RemoteFactoryMineComponentData`
  - `Beyond.Gameplay.View.ModelComponentData`

`Beyond.Gameplay.Core.RemoteFactoryRootComponentData` is 32 bytes in these
objects and contains eight zero int32 words. No nonzero field bytes are present.

`Beyond.Gameplay.Core.RemoteFactoryMineComponentData` was already covered by the
known empty core-component decoder.

The installed IL2CPP metadata does not expose useful instance fields for the
entity or root component types, so the entity decoder is intentionally marked
`$partial` and `$inferred`.

The decoder gates that float word on the exact observed `0x3f800000` bit
pattern; mismatches fall back to the existing heuristic output path.

## Validation

Built AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded, 14 existing warnings, 0 errors.

Generated `tmp/remote_factory_filter_20260703.json` from the StreamingAssets
AnimeStudio AssetMap and ran a focused export:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  "tmp\remote_factory_after_20260703" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op None ^
  --export_type JSON ^
  --types MonoBehaviour:Both ^
  --filter_data tmp\remote_factory_filter_20260703.json
```

Focused export result:

- 3 `RemoteFactoryEntityTemplateData` refs decoded as partial structural data
- 3 `RemoteFactoryRootComponentData` refs decoded as reserved zero words
- 3 existing empty `RemoteFactoryMineComponentData` refs still decode
- 3 existing `ModelComponentData` refs still decode
- 0 `$unparsed`/`$heuristic` markers remain on RemoteFactory refs

The top-level files still preserve the original `serializedTypeTreeError`
diagnostic from the failed TypeTree path, which is expected; the recovered
managed-reference data is decoded under `references.RefIds[*].data`.
