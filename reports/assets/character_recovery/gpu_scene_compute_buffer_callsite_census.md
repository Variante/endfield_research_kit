# GPU-scene compute-buffer callsite census

This report checks the GameAssembly compute-shader binding surface against the
GPU-scene/per-draw hypothesis. The result is a bounded negative: the only
direct `Internal_HGSetBuffer` callers belong to MagicaCloth physics, while the
GPU-scene setup wrapper has no static call edge to this managed binding API.

## Binary identity

- GameAssembly: `D:\Program Files\Endfield Game\GameAssembly.dll`
- SHA-256:
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`

## Wrapper surface

The installed GameAssembly wrapper table gives these relevant method bodies:

| Managed API | GameAssembly body |
| --- | --- |
| `ComputeShader.Internal_HGSetBuffer` | `0x18b3d75bc` |
| `ComputeShader.HGSetBuffer` | `0x18b3d75ac` |
| `ComputeShader.Internal_SetBuffer` | `0x18b3d761c` |
| `ComputeShader.Internal_SetGraphicsBuffer` | `0x18b3d767c` |
| `ComputeShader.Dispatch` | `0x18b3d74a8` |
| `ComputeShader.SetBuffer` (buffer overload) | `0x18b3d772c` |
| `CommandBuffer.Internal_SetComputeBufferParam` | `0x18b3e6d80` |
| `CommandBuffer.Internal_DispatchCompute` | `0x18b3e6868` |

The direct-call census covered the `.text` and `il2cpp` code sections and
resolved each callsite to its PData body where available.

## Positive but non-target callsite

`Internal_HGSetBuffer` has exactly two direct callsites:

```text
0x189f19be3
0x189f19c18
```

Both are inside
`MagicaCloth.PhysicsManagerMeshData::DispatchWriting[431943]`
(`0x189f198e4..0x189f19d4b`). The same body then calls
`ComputeShader.Dispatch` at `0x189f19d1d`; its arguments are sourced from the
MagicaCloth method state (`rsi+0x148`/`+0x150` and the physics buffer IDs), not
from `HGShadingStateSystem`, `GPUDrivenRendererV1/V2`, the factory manager, or
the persistent custom-per-draw resource resolver.

The `HGSetBuffer` wrapper itself (`0x18b3d75ac`) has no direct callsite in the
image. The raw `Internal_SetBuffer` and `Internal_SetGraphicsBuffer` wrappers
also have no direct callsite. This prevents treating the physics call as the
missing character upload merely because it contains a similarly named HG
binding API.

## GPU-scene boundary

`HGShadingStateSystem.SetupGpuSceneUploadCs` remains the GameAssembly wrapper at
`0x1839454d0`, resolving UnityPlayer `0x1801ee4c0`. Its native body uses the
relocated pointer-table/context slots and does not contain a literal call to
the managed compute-buffer wrappers, `_RTPerDrawParamsBuffer`,
`UploadPerDrawParams`, or kernel 7. The existing command-buffer census still
finds built-in render-pass callers for `Internal_SetComputeBufferParam` and
`Internal_DispatchCompute`, but no factory/per-draw/character body.

Therefore this API surface is now explicitly fail-closed for the character
route:

```text
factory 0x8c record / persistent per-draw resource
  -X-> managed HGSetBuffer / ComputeShader.Dispatch callsite
GPU-scene setup
  -> relocated native context/resource slots (edge unresolved)
```

The next useful target remains the runtime-indirect consumer that binds the
persistent resource records to GPU-scene resources; no managed
`ComputeBuffer` call should be inferred from the MagicaCloth physics path.
