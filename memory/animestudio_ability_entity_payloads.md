# AnimeStudio Ability-Entity Payload Recovery

This note tracks current `data_abilityentity_*` MonoBehaviour managed-reference
recovery. It is separate from enemy component notes because the ability-entity
payloads share some `Beyond.Gameplay.Core` classes but have different template,
root, controller, and movement tails.

## 2026-06-28 Initial Current Repro

Targeted current-CLI repros before the ability-entity partial decoder pass:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" "D:\fluffy-dump\tmp\mb_abilityentity_streaming_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^(data_abilityentity_interact_mud_carpet|data_abilityentity_eny_0045_agtrinit_skill111)$"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" "D:\fluffy-dump\tmp\mb_abilityentity_persistent_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^data_abilityentity_chr_0033_camille_normal_skill$"
```

Both commands exited 0 with no warning/error log output. JSON markers showed the
schema gap:

| Sample | Refs | Decoded | Heuristic/unparsed | Partial | Main unknown records |
| --- | ---: | ---: | ---: | ---: | --- |
| `data_abilityentity_eny_0045_agtrinit_skill111` | 5 | 2 | 3 | 1 | `AbilityEntityTemplateData`, `AbilityEntityRootComponentData`, `AbilityEntityControllerData` |
| `data_abilityentity_interact_mud_carpet` | 5 | 2 | 3 | 1 | `AbilityEntityTemplateData`, `AbilityEntityRootComponentData`, `AbilityEntityControllerData` |
| `data_abilityentity_chr_0033_camille_normal_skill` | 8 | 2 | 6 | 1 | ability-entity template/root/controller, movement, plus two empty-type header islands |

`AbilitySystemData` and `RotatorComponentData` were already handled by the prior
enemy/common decoder work. The remaining ability-entity gaps are not CLI process
failures; they are managed-reference schema coverage gaps.

## Partial Decoder Pass

The 2026-06-28 partial decoder pass added conservative decoders for:

- `Beyond.Gameplay.AbilityEntityTemplateData`
- `Beyond.Gameplay.Core.AbilityEntityRootComponentData`
- `Beyond.Gameplay.Core.AbilityEntityControllerData`
- non-48-byte `Beyond.Gameplay.Core.CharacterMovementComponentData`

These decoders intentionally mark uncertain payloads as `$partial`. They expose
known metadata field order, aligned string hints, and all raw 32-bit words. They
avoid `$heuristic`/`$unparsed` for records where we know the class and preserve
the bytes, but they do not claim field-accurate deserialization for BB
field-meta blocks, surrounding/follow configs, skill data, model/nav/physical
sections, interactive action tails, movement lists, or nested controller blocks.

Final verification:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" "D:\fluffy-dump\tmp\mb_abilityentity_streaming_final" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^(data_abilityentity_interact_mud_carpet|data_abilityentity_eny_0045_agtrinit_skill111)$"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" "D:\fluffy-dump\tmp\mb_abilityentity_persistent_final" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^data_abilityentity_chr_0033_camille_normal_skill$"
```

Build result: 0 warnings, 0 errors. Both targeted exports exited 0 with no
warning/error output.

Final JSON marker counts:

| Sample | Refs | Decoded | Heuristic/unparsed | Partial | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `data_abilityentity_eny_0045_agtrinit_skill111` | 5 | 5 | 0 | 3 | template/root/AbilitySystem remain partial; zero-length controller fully decoded |
| `data_abilityentity_interact_mud_carpet` | 5 | 5 | 0 | 3 | same shape as `agtrinit_skill111` |
| `data_abilityentity_chr_0033_camille_normal_skill` | 8 | 6 | 2 | 5 | template/root/AbilitySystem/movement/controller partial; two empty-type records remain heuristic/unparsed |

The two remaining Persistent heuristic records have empty type names and negative
RIDs with non-zero data lengths. They are likely managed-reference segmentation
false positives, not known ability-entity classes. They should be handled by
hardening null-sentinel/header-chain validation rather than by adding an
ability-entity class decoder.

## Remaining Work

- Decode `AbilityEntityTemplateData` field-meta sections accurately instead of
  preserving them as raw words.
- Decode `AbilityEntityRootComponentData` BB field-meta/string blocks.
- Decode `AbilityEntityControllerData` nested movement/rotation blocks in the
  Persistent Camille sample.
- Harden managed-reference header parsing so empty-type negative-RID islands
  with non-zero payloads are not accepted as real records unless a future sample
  proves such records are valid.
