# AnimeStudio Enemy Managed-Reference Segmentation

Generated 2026-06-28 while investigating enemy/ability MonoBehaviour
managed-reference payloads that produced bogus type names such as
`FootBar.HeadBar`.

## Finding

The suspicious enemy entries are not real IL2CPP classes. They are false
managed-reference headers produced by the old recovery scan.

The previous scanner accepted any 4-byte-aligned sequence shaped like:

```text
rid:int64
class:aligned string
namespace:aligned string
assembly:aligned string
```

That is too loose for Endfield enemy payloads because root/ability components
contain dense arrays of socket, bone, lock-point, and skill names. Sliding the
candidate offset by four bytes through those arrays can create many plausible
but false triples.

Example from `data_eny_0077_agshield`:

```text
false headerStart=716 dataOffset=764
rid=154618822831
type=FootBar.HeadBar
asm=LockPoint
```

The bytes at that location are inside the previous
`EnemyRootComponentData` payload. Nearby 4-byte shifts produce more equally
plausible false triples from the same name array.

The true next header is:

```text
headerStart=1380 dataOffset=1456
rid=5628437864111670018
type=Beyond.Gameplay.View.ModelComponentData
asm=Gameplay.Beyond
```

The same pattern appeared in `data_eny_0115_nefarcore`; examples such as
`HP.FootBar` and `HeadStatus.FootBar` were payload strings, not runtime types.

## Parser Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now uses a strong-header pass
before the older loose fallback. A strong managed-reference header must be a
positive, non-null RID and either:

- resolve through loaded DummyDll metadata, or
- look like a runtime namespace/assembly pair with dotted namespace and dotted
  assembly names, such as `Beyond.Gameplay.Core` / `Gameplay.Beyond`.

The strong pass must prove the remaining header chain using only strong
candidates. If that fails, AnimeStudio falls back to the old permissive scan so
non-Endfield or weakly named edge cases are still preserved.

## Verification

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with the existing 14 warnings and 0 errors.

Targeted StreamingAssets sample:

```text
D:\fluffy-dump\tmp\mb_enemy_segmentation_after\MonoBehaviour\data_eny_0077_agshield_p9FCDDD0503D62AC0.json
```

Result:

- `references.count`: 50
- recovered refs: 50
- non-`Gameplay.Beyond` refs: 0
- final real records `rid ...0051` through `...0065` are no longer hidden
  inside the last ability payload
- payloads remain `$unparsed`/`$heuristic` because the component schemas are not
  decoded yet

Targeted Persistent sample:

```text
D:\fluffy-dump\tmp\mb_enemy_segmentation_after_nefarcore\MonoBehaviour\data_eny_0115_nefarcore_p*.json
```

Result:

- `references.count`: 19
- recovered refs: 19
- non-`Gameplay.Beyond` refs: 0
- bogus `HP`/`FootBar`/`VBHit` headers are gone

Regression check:

```text
D:\fluffy-dump\tmp\mb_segmentation_facemorph_regression\MonoBehaviour\data_facemorph_avatar_antal_p40F48185244A5DFD.json
```

Result:

- refs: 243
- decoded: 243
- heuristic/unparsed: 0

## Remaining Work

This is a boundary recovery fix, not an enemy component payload decoder.
`EnemyTemplateData`, `EnemyRootComponentData`, `AbilitySystemData`,
`AbilitySystemForEnemyPartData`, and related small component records are now
segmented correctly but still need schema-specific parsers before the enemy
family can be considered fully understood.
