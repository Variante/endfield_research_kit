# AnimeStudio Export Recovery Progress - 2026-06-28

This is the first integrated progress checkpoint after splitting recovery work
by failure class.

## Completed Tracks

### Shader

- Owner: shader worker.
- File changed: `tools/AnimeStudio/AnimeStudio.Utility/ShaderConverter.cs`.
- Previous failure: shader bytecode decode exceptions surfaced as `Export Shader`
  errors and dropped the `.shader` output.
- Current behavior: recoverable shader bytecode blob failures export parsed
  shader metadata plus explicit bytecode-unavailable comments.
- Verification:
  - targeted `Mobile/Particles/Additive` repro now exports 1 `.shader` with a
    classified `Unit` signature warning.
  - targeted `Hidden/RayTracingReflection` repro exports 1 `.shader` with a
    classified `_RTR` signature warning.
  - targeted Persistent `HGRP/UI/Grid` repro exports 1 `.shader` with a
    classified `_Glo` signature warning.

Remaining unknown: the newer Endfield/Unity shader bytecode payload is still
not decompiled. We now preserve metadata and classify the blob instead of
pretending the bytecode is understood.

### AnimationClip

- Owner: AnimationClip worker.
- File changed:
  `tools/AnimeStudio/AnimeStudio.Utility/YAML/CustomCurveResolver.cs`.
- Previous failure: unknown custom curve binding attributes threw exceptions
  and dropped whole `.anim` files.
- Current behavior: unknown custom bindings export as stable placeholder field
  names such as `unknown_Light_44543834` and
  `unknown_CustomType39_1865675821`.
- Verification:
  - four-row targeted repro now exports 4 `.anim` files with no warning/error
    output.
  - StreamingAssets shard 04 replay requested 15,643 clips and produced 15,643.
  - Persistent shard 01 replay requested 7,922 clips and produced 7,922.

Remaining unknown: placeholder names preserve data but do not identify the
original Unity or Endfield property names.

## Shared Diagnostics

- File changed: `tools/AnimeStudio/AnimeStudio.CLI/Studio.cs`.
- Top-level export catch logs now include PathID, source file, original source
  path, and container. This is intended to make the next full report map export
  warnings/errors back to source AB/VFS evidence.

## Verification

The combined current AnimeStudio source, including still-uncommitted parallel
worker changes, compiled successfully to a temporary output directory:

```bat
.\tools\AnimeStudio\.dotnet\dotnet.exe build .\tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows --no-restore -p:OutDir=D:\fluffy-dump\tmp\animestudio_build_check\
```

Result: build succeeded with the existing TODO/compiler warnings only and 0
errors.

The normal release output was temporarily locked by active worker repro runs, so
the temp output build was used for this checkpoint.

## Active Tracks

- MonoBehaviour worker: still investigating partial managed-reference/type-tree
  recovery and source-context warnings.
- Missing-output/status worker: still investigating Texture2D/Sprite accounting
  and per-AB status reporting.

Files from active tracks are intentionally left unstaged until their workers
return final verification.
## Follow-up: Real Parser/Selection Fixes

### Shader Blob Layout

A second shader pass replaced the temporary metadata-only fallback for Endfield
shader subprogram blobs with a real outer-layout parser:

- Endfield subprogram records start with marker `0x0C11FFE2`.
- D3D11 native records use raw program type `33` and contain DXBC snippets.
- Vulkan native records use raw program type `25` and contain SMOL-V-like
  snippets.
- Non-native records are parameter/resource records and are skipped by bounded
  record length instead of being misread as old Unity string fields.

Verification:

```text
D:\fluffy-dump\tmp\animestudio_shader_full_audit_20260628_013658\summary.json
```

Results from replaying all existing Shader shards:

| Source | Shards | Outputs | Warning lines | Error lines | Nonzero exits |
| --- | ---: | ---: | ---: | ---: | ---: |
| StreamingAssets | 7 | 227 | 0 | 0 | 0 |
| Persistent | 2 | 218 | 0 | 0 | 0 |

A targeted repro for the previous remaining `HGRP/WaterForwardRendering` error
also exits 0 and writes a shader containing 28 DXBC snippet markers and 28
SMOL-V snippet markers, with no `bytecode unavailable` fallback.

Remaining shader gap: DXBC containers are extracted, but HLSL decompilation
needs the native decompiler dependency; Vulkan snippets are identified as
SMOL-V-like but the current SMOL-V decoder still fails on Endfield samples.

### SMOL-V Shader Decoder

The Vulkan/SMOL-V half of the shader gap is now resolved for the existing
shader shard set. `tools/AnimeStudio/AnimeStudio.Utility/Smolv/` was updated to
match upstream SMOL-V encoding version 1 behavior: mask the SMOL-V encoding byte
out of the SPIR-V version word, add opcodes 331-366, use version-specific opcode
table bounds, port compact `MemberDecorate` decoding, and bound reads by the
advertised snippet size.

Verification:

```text
D:\fluffy-dump\tmp\animestudio_shader_smolv_full_audit_20260628_020333\summary.json
```

Results from replaying all existing Shader shards after the SMOL-V decoder
patch:

| Metric | Count |
| --- | ---: |
| Shader shards | 9 |
| Shader outputs | 443 |
| SMOL-V snippets | 59,686 |
| DXBC snippets | 56,878 |
| SMOL-V disassembly errors | 0 |
| bad dictionary key errors | 0 |
| nonzero exits | 0 |

Remaining shader gap: DXBC containers are extracted, but HLSL decompilation
still needs a reliable native/out-of-process decompiler path.
### Texture2D Filter Data Identity

The Texture2D decoder was not the cause of the parseable missing-output rows.
The valid rows were loaded by source offset but dropped by the final name regex
because the asset-map display name differed from `Texture2D.m_Name`.

`tools/AnimeStudio/AnimeStudio.CLI/Studio.cs` now keeps assets whose
`filter_data` source, offset, PathID, and type match, even when the `--names`
regex does not match the actual Unity object name.

Verification used a representative BC7 row:

```text
map Name: 74618664eecd07dc
actual Texture2D.m_Name: facskill_hub_mine_spd_20
PathID: -598241958808313765
output: tmp/texture2d_filter_identity_repro/after2/Texture2D/facskill_hub_mine_spd_20_pF7B29E1BAB7F205B.png
```

The command exited 0 with no warning/error output and produced a 1,839-byte PNG.
### MonoBehaviour Face-Morph Managed References

A MonoBehaviour pass decoded the high-volume face-morph managed-reference
families: `SkeletalMorphMappingData`, `SkeletalMorphShaderPropMappingData`,
`SkMorphShaderParamFloat`, and `SkMorphShaderParamVector4`.

Verification outputs:

```text
D:\fluffy-dump\tmp\mb_skeletal_all_facemorph_streaming_after2\MonoBehaviour\
D:\fluffy-dump\tmp\mb_skeletal_all_facemorph_persistent_after\MonoBehaviour\
```

Results:

| Source | Files | Managed refs | Decoded | Heuristic/unparsed |
| --- | ---: | ---: | ---: | ---: |
| StreamingAssets | 62 | 15,147 | 15,147 | 0 |
| Persistent | 1 | 271 | 271 | 0 |

The same probe confirms the enemy component family remains separate: the
`data_eny_0077_agshield` sample still has 50 heuristic refs and apparent false
managed-reference headers such as `FootBar.HeadBar`.

### MonoBehaviour Enemy Managed-Reference Segmentation

The enemy component family had a boundary-recovery bug before any payload
decoder could be trusted. The old scanner accepted loose `rid + class/ns/asm`
triples and could mistake socket, bone, lock-point, and skill-name arrays for
managed-reference headers.

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now runs a strong-header chain
pass before the loose fallback. Strong headers are positive non-null RIDs that
either resolve through loaded DummyDll metadata or look like runtime
namespace/assembly pairs such as `Beyond.Gameplay.Core` / `Gameplay.Beyond`.

Verification:

| Sample | Refs | Non-Gameplay refs | Result |
| --- | ---: | ---: | --- |
| `data_eny_0077_agshield` | 50 | 0 | bogus `FootBar.HeadBar` and skill-name islands gone |
| `data_eny_0115_nefarcore` | 19 | 0 | bogus `HP`/`FootBar`/`VBHit` headers gone |
| `data_facemorph_avatar_antal` regression | 243 | 0 | 243 decoded, 0 heuristic/unparsed |

Remaining enemy gap: the true `Gameplay.Beyond` component records are now
segmented correctly, but their payload schemas are still `$unparsed` /
`$heuristic`.

### MonoBehaviour Enemy Component Payload Decoders

After the segmentation fix, a second pass decoded the small and bounded enemy
component payloads in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`.

Verification:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed |
| --- | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 38 | 23 | 12 |
| `data_eny_0115_nefarcore` | 19 | 17 | 7 | 2 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 |

Newly decoded families include `ModelComponentData`, `EnemyAIComponentData`,
`EnemyControllerData`, `ControlledStateComponentData`, obstacle capsule/box
records, zero-length no-op components, and inferred fixed/raw layouts for
`EnemyRootComponentData`, movement, RVO, mesh adjust, pivot, part-root, and
part-animator records.

Remaining enemy gap: `EnemyTemplateData`, `AbilitySystemData`,
`AbilitySystemForEnemyPartData`, `EnemyPartsControllerComponentData`, and
`NavMeshObstacleComponentData` still need real nested schema recovery.

### MonoBehaviour Enemy Wrapper Payload Decoders

A follow-up pass decoded `EnemyPartsControllerComponentData` and
`NavMeshObstacleComponentData` as bounded wrapper records with typed RID links.

Verification:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed |
| --- | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 40 | 25 | 10 |
| `data_eny_0115_nefarcore` | 19 | 17 | 7 | 2 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 |

Remaining enemy gap: `EnemyTemplateData`, `AbilitySystemData`, and
`AbilitySystemForEnemyPartData` still need real nested schema recovery.
