# AnimeStudio face-morph managed-reference payload recovery

Date: 2026-06-28

## Result

A focused MonoBehaviour pass decoded the high-volume face-morph managed-reference
families that were previously exported as heuristic payloads:

- `Beyond.Gameplay.Core.SkeletalMorphMappingData`
- `Beyond.Gameplay.Core.SkeletalMorphShaderPropMappingData`
- `Beyond.Gameplay.Core.SkMorphShaderParamFloat`
- `Beyond.Gameplay.Core.SkMorphShaderParamVector4`

These are not encrypted payloads. They are compact Unity serialized managed
reference records with fixed primitive fields, aligned strings, managed-reference
RID links, and bounded object lists.

## Implemented decoder

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now decodes the above classes
before falling back to heuristic string/RID scanning.

`SkeletalMorphMappingData` layout:

```text
int32 id
int32 nameHash
int32 tagHash
int32 partType
int32 bones.count
repeat bones.count:
  int32 nameHash
  int32 index
  float[3] position
  float[3] rotation
  float[3] scale
```

This matches the observed payload sizes:

```text
length = 20 + bones.count * 44
```

`SkMorphShaderParamFloat` layout:

```text
aligned string name
int32 channelIndex
float value
```

`SkMorphShaderParamVector4` layout:

```text
aligned string name
int32 channelIndex
float[4] value
```

`SkeletalMorphShaderPropMappingData` layout:

```text
int32 id
int32 nameHash
int32 tagHash
int32 partType
int32 paramSetIndex
int32 componentIndex
int64 shaderParamRid
```

`shaderParamRid` is resolved through the recovered managed-reference registry
when the target reference is available.

The byte layout is verified from raw sidecars. Some field labels such as
`position`, `rotation`, `scale`, `paramSetIndex`, and `componentIndex` remain
marked `$inferred` in JSON because the local Cpp2IL/DummyDll outputs did not
provide reliable field names for these private payload classes.

## Verification

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with 0 warnings and 0 errors after the final decoder
edit.

Targeted `data_facemorph_avatar_antal` verification:

```text
D:\fluffy-dump\tmp\mb_skeletal_after\MonoBehaviour\data_facemorph_avatar_antal_p40F48185244A5DFD.json
```

Result: 243/243 `SkeletalMorphMappingData` refs decoded, 0 heuristic/unparsed.
Observed payload lengths map cleanly to bone-list counts:

| Payload length | Bone count | Refs |
| ---: | ---: | ---: |
| 20 | 0 | 212 |
| 64 | 1 | 17 |
| 108 | 2 | 8 |
| 152 | 3 | 6 |

Broad StreamingAssets face-morph verification:

```text
D:\fluffy-dump\tmp\mb_skeletal_all_facemorph_streaming_after2\MonoBehaviour\
```

| Class | Refs | Decoded | Heuristic/unparsed |
| --- | ---: | ---: | ---: |
| `SkeletalMorphMappingData` | 15,044 | 15,044 | 0 |
| `SkeletalMorphShaderPropMappingData` | 53 | 53 | 0 |
| `SkMorphShaderParamFloat` | 49 | 49 | 0 |
| `SkMorphShaderParamVector4` | 1 | 1 | 0 |
| **Total** | **15,147** | **15,147** | **0** |

The StreamingAssets run emitted one unrelated map/load warning for unknown
`ClassIDType 1186182244` and still exited 0.

Persistent face-morph verification:

```text
D:\fluffy-dump\tmp\mb_skeletal_all_facemorph_persistent_after\MonoBehaviour\
```

| Class | Refs | Decoded | Heuristic/unparsed |
| --- | ---: | ---: | ---: |
| `SkeletalMorphMappingData` | 267 | 267 | 0 |
| `SkeletalMorphShaderPropMappingData` | 2 | 2 | 0 |
| `SkMorphShaderParamFloat` | 2 | 2 | 0 |
| **Total** | **271** | **271** | **0** |

Combined face-morph verification now covers 15,418 managed references with 0
heuristic/unparsed payloads in this family.

## Remaining MonoBehaviour gaps

The enemy/ability component payloads are still separate unresolved families. In
the same two-file probe, `data_eny_0077_agshield` still has 50 heuristic refs,
and some recovered headers such as `FootBar.HeadBar` indicate the current header
segmentation can still misidentify payload bytes as managed-reference type
headers for complex enemy data. That should be handled separately before adding
large enemy component decoders.