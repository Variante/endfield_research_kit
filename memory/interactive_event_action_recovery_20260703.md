# InteractiveEvent action recovery - 2026-07-03

## Scope

Added narrow AnimeStudio managed-reference decoders for simple
`Beyond.Gameplay.InteractiveEvent` action payloads observed in the focused
`data_abilityentity_interact*` exports from VFS chunk
`68B3B9B8EB82E88FBFE6A313E6B18FB6.chk`.

The decoder intentionally handles only stable, self-contained action records:

- `AddTag`
- `RemoveAddedTag`
- `RemoveTag`
- `ClearAddedTag`
- `PlayAnimationAction`
- `StopAnimationAction`
- `PlaySoundAction`
- `CastSkill`
- `AttachSkill`
- `ExitThrowMode`

The broader structural records remain heuristic because their layouts still need
more evidence:

- `InteractiveEventComponentData`
- `EnterThrowMode`
- `AttachToInstigator`

## Validation

Build:

```powershell
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: succeeded with the existing 14 warnings and 0 errors.

Focused export:

```powershell
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe `
  "C:\Program Files\GRYPHLINE\Arknights Endfield\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" `
  tmp\interactive_event_actions_after_68b3 `
  --game ArknightsEndfield `
  --logger_flags Warning Error `
  --group_assets ByType `
  --map_op None `
  --export_type JSON `
  --types MonoBehaviour:Both `
  --dummy_dlls tools\DummyDll `
  --names "^data_abilityentity_interact"
```

Result: succeeded, exporting 9 focused MonoBehaviour JSON files.

Decoded action counts from managed-reference entries:

| Type | Count | Payload lengths | Partial | Unparsed | Heuristic |
| --- | ---: | --- | ---: | ---: | ---: |
| `AddTag` | 11 | 32x1, 56x9, 176x1 | 0 | 0 | 0 |
| `RemoveAddedTag` | 6 | 32x1, 56x4, 100x1 | 0 | 0 | 0 |
| `RemoveTag` | 5 | 192x5 | 0 | 0 | 0 |
| `ClearAddedTag` | 11 | 4x11 | 0 | 0 | 0 |
| `PlayAnimationAction` | 4 | 16x4 | 0 | 0 | 0 |
| `StopAnimationAction` | 6 | 16x6 | 0 | 0 | 0 |
| `PlaySoundAction` | 4 | 28x4 | 0 | 0 | 0 |
| `CastSkill` | 6 | 40x6 | 0 | 0 | 0 |
| `AttachSkill` | 1 | 60x1 | 0 | 0 | 0 |
| `ExitThrowMode` | 11 | 28x10, 32x1 | 0 | 0 | 0 |

Intentionally heuristic broad records in the same focused export:

| Type | Count | Payload lengths | Unparsed | Heuristic |
| --- | ---: | --- | ---: | ---: |
| `InteractiveEventComponentData` | 3 | 188x1, 212x1, 220x1 | 3 | 3 |
| `EnterThrowMode` | 6 | 712x1, 716x1, 732x2, 752x2 | 6 | 6 |
| `AttachToInstigator` | 6 | 88x6 | 6 | 6 |

## Layout evidence

Observed tag actions serialize:

1. operation mode word (`AddTag` = 1, `RemoveAddedTag` = 2, `RemoveTag` = 0)
2. tag count
3. repeated aligned ASCII tag strings
4. one hash word per tag

Observed string actions:

- `PlayAnimationAction` / `StopAnimationAction`: mode word plus aligned animation name.
- `PlaySoundAction`: aligned sound event string plus one zero word.
- `CastSkill`: two zero prefix words plus aligned skill id.
- `AttachSkill`: aligned `SkillData/...json` path plus one zero word.
- `ExitThrowMode`: aligned skill id string.

Examples recovered in the focused export include:

- tag: `GameplayState/Interacting/Bomb/PickUp`
- sound: `au_int_bomb_acquire`
- animation: `PickUp`
- skill: `common_character_bomb_add`
- skill path: `SkillData/Common/common_character_bomb_add_2.json`

## Follow-up

The next safe InteractiveEvent target is not another small string action; the
remaining value is in reconstructing the structural lists inside
`InteractiveEventComponentData` and then correlating those RID chains with
`EnterThrowMode`/`AttachToInstigator`. Keep those broad payloads heuristic until
their field boundaries are cross-checked against more chunks or IL2CPP metadata.
