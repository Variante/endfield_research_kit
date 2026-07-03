# MonoBehaviour CheckBuffIdInContextAdvanced Recovery - 2026-07-03

## Context

The post-diagnostics MonoBehaviour index still had two direct `$unparsed`
`Beyond.Gameplay.Core.Conditions.CheckBuffIdInContextAdvanced/Data` managed
references. Both occur in `data_chr_0033_camille` and are 92-byte payloads.

The old heuristic view exposed the tag string
`Skill/Character/Common/SpellInflict/FireInflict`, but the payload stayed
anonymous because no exact class decoder handled the advanced condition.

## Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now has an exact-length decoder
for the observed 92-byte `CheckBuffIdInContextAdvanced/Data` shape:

- inherited `AbilityActionData` prefix
- `checkType`
- empty `buffIdList`
- `GameplayTagQuery` with tag path and tag hash
- one final raw int32 tail word

The decoder keeps the object `$partial` because the final one-word advanced
tail is byte-bounded but not semantically named. It falls closed for other
lengths or variants.

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Final rebuild result: `0 Warning(s)`, `0 Error(s)`.

Focused export:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" tmp\mono_frontier_camille_checkbuff_adv_after2 --game ArknightsEndfield --logger_flags Warning Error --group_assets BySource --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "data_chr_0033_camille"
```

Focused output metrics:

| Metric | Result |
| --- | ---: |
| JSON files | 1 |
| `CheckBuffIdInContextAdvanced/Data` typed records | 2 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| `decodeError` records | 0 |

Both advanced records decode as `checkType = Tag`, `queryType = HasAny`, with
the tag `Skill/Character/Common/SpellInflict/FireInflict` and tag hash
`0xa315eb9b`. The final tail word is `0`.
