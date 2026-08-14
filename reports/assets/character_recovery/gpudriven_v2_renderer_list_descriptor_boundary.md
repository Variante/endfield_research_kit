# GPUDriven V2 renderer-list descriptor boundary

This note records a literal `0x100`-byte native record that initially looked
like the missing factory per-draw staging buffer. The installed internal-call
table identifies it as the GPUDriven V2 renderer-list path instead.

## Binary identity

- `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`

## Managed/native registration

UnityPlayer's internal-call table maps:

| registered call | wrapper | native body |
| --- | --- | --- |
| `GPUDrivenRendererV2::CreateRendererList` | `0x1801e9680` | `0x1810fd1b0` |
| `GPUDrivenRendererV2::CreateRendererListWithPreZ` | `0x1801e9770` | `0x1810fd7d0` |

Both wrappers first call `0x1810fe120`, the V2 runtime-resource selector
(selector `1` in the shared `context+0xe8` table), then forward the managed
renderer-list arguments to the native body. This is a renderer-list creation
surface, not a factory shared-data setter.

## `0x100` record construction

`0x1810fd1b0` obtains a runtime descriptor from the V2 object's resource array
(`object+0x50`, indexed by the caller's renderer-list index) and checks its
descriptor payload at `+0x20`. When the command-stream path is active it calls
the context vtable slot `+0xea0`; the installed normal backend resolves that
slot to `0x1809324e0`, which emits command opcode `0x273b`.

The helper `0x18041ed50`, called by the native body, fills an approximately
`0x100`-byte CPU record. It copies runtime descriptor lanes `+0x5c..+0x9c`
into output lanes `+0xc0..+0xf0`, adds renderer/camera data, and returns the
record to the V2 renderer-list path. The fallback branch appends the resulting
record to the V2-owned dynamic arrays. `0x1810fd7d0` performs the analogous
pre-Z path and also reaches the same `+0xea0` command-stream slot.

## Recovery boundary

The checked bodies contain no load of the factory manager's
`manager+0x38 + index*0x8c` record, no dirty-byte test from that record, no
`_UploadBuffer`/84-byte pack, and no `GpuSceneDirtyUpdateCS.UploadPerDrawParams`
kernel-7 selection. The literal `0x100` record therefore belongs to a
GPUDriven V2 renderer-list descriptor/command path and must not be aliased to
the factory callback's `0x100`-stride scratch or to the unresolved channel-2
per-draw upload resource.

```text
GPUDrivenRendererV2::CreateRendererList
  -> 0x1810fe120 (V2 runtime resource selector)
  -> 0x1810fd1b0 / 0x18041ed50 (CPU renderer-list record)
  -> context vtable +0xea0 -> opcode 0x273b (normal backend)

[factory manager +0x38/index*0x8c -> this 0x100 record: not found]
```

