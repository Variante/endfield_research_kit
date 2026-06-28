# AnimeStudio Warning Recovery Checkpoint - 2026-06-28

This checkpoint summarizes the current warning/error recovery state after the
2026-06-28 targeted fixes. The broad full-export logs under
`reports/20260627_215637/` predate the latest parser changes, so their counts
are useful for prioritization but not as current pass/fail truth.

## Stale Full-Export Census

The 2026-06-27 full run reported these major classes:

| Rank | Export stage | Reported issue count | Current interpretation |
| ---: | --- | ---: | --- |
| 1 | `json_by_type / MonoBehaviour` | 13,434 warnings | Largest remaining recovery surface. Recent targeted fixes cleared face morph and representative enemy payloads, but the full MonoBehaviour tree has not been refreshed. |
| 2 | `convert_by_type / Shader` | 454 errors | Stale. All existing Shader shards were later replayed cleanly after the SMOL-V/custom shader blob fixes. Remaining shader gap is semantic decompilation of extracted bytecode, not extraction. |
| 3 | `convert_by_type / Sprite` | 26,520 missing outputs | Likely stale or wrapper-dependency related. Targeted fix added Texture2D/SpriteAtlas parse dependencies, but broad Sprite refresh is still needed. |
| 4 | `convert_by_type / AnimationClip` | 50 errors | Now covered by targeted and shard replays for known failing signatures. |
| 5 | `convert_by_type / Texture2D` | 100 missing outputs | Partly classified: zero-size `Font Texture` placeholders are real empty payloads; the rest appear to be stale filter/name identity mismatches pending broader verification. |
| 6 | maps / Animator | 2 warnings | Unknown `ClassIDType 1186182244`; low priority until downstream use is known. |

## New Verification

`StreamingAssets` `AnimationClip` shard 13, one of the remaining old-error
shards, was replayed directly against installed game data:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\verify_anim_shard13_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\AnimationClip\shard_13_of_16_names.txt" --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\AnimationClip\shard_13_of_16_filter_data.json" --types AnimationClip:Both
```

Result:

- Exit code: 0.
- Warning/error output: none.
- Output directory: `tmp/verify_anim_shard13_current/AnimationClip/`.
- Output file count: 22,768.

Together with the earlier targeted AnimationClip repros and shard 04 /
Persistent shard 01 replays, the known AnimationClip export-error signatures
are now understood as stale in the old full report.

## ManagedReferences Null Registry Classification

The top stale `MonoBehaviour#N` family was sampled with the login prefab bundle:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk" "D:\fluffy-dump\tmp\mb_anonymous_loginroot_bundle_null_registry_fix" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls "D:\fluffy-dump\tools\DummyDll"
```

Before the classifier fix, the current exporter wrote 3,835 MonoBehaviour JSON
files for that bundle, with 140 `UIButton` files carrying
`serializedTypeTreeError` and `$heuristic` only because the final
`ManagedReferencesRegistry` encoded one null RID at EOF:

```text
version=2, count=1, rid=-2, empty class/ns/asm, dataLength=0
```

After the fix:

- The same bundle still writes 3,835 MonoBehaviour JSON files.
- The 140 `UIButton` files have no problem markers.
- Their `references` registry is marked `$decoded`, with
  `managedReferencesRegistryFullyDecoded: true`.
- The original TypeTree EOF is not preserved as an export error when the
  recovered registry contains only decoded data.

Regression samples keep real unknowns visible:

- `data_facemorph_avatar_antal`: `managedReferencesRegistryFullyDecoded: true`,
  no serialized TypeTree error.
- `data_eny_0077_agshield`: `managedReferencesRegistryFullyDecoded: false`,
  keeps the serialized TypeTree error and 2 semantic `$partial` payloads.
- `data_eny_0115_nefarcore`: `managedReferencesRegistryFullyDecoded: false`,
  keeps the serialized TypeTree error and 1 semantic `$partial` payload.

This removes a large false-positive bucket without hiding real incomplete
managed-reference payloads.

## Current Highest-Value Work

1. Refresh or sample `MonoBehaviour` managed-reference recovery by family. The
   stale report is dominated by anonymous prefab/script objects and dialog
   playable assets, while recent targeted work has focused on face morph and
   enemy data.
2. Verify Sprite/Texture2D output coverage after the wrapper dependency fixes.
   The old missing-output counts were large but emitted no export errors, so the
   next useful result is a status manifest that distinguishes dependency gaps,
   empty payload placeholders, and true conversion failures.
3. Add per-source/per-type status manifests before claiming all AB files are
   fully understood. The current logs do not map every warning-free output back
   to a clean source AB certification.
