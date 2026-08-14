# Burst shared-data producer contract

This report records the first positive factory-record producer recovered from
the installed Burst AOT library. It is a CPU-side producer only; it is not the
missing GPU upload or `UploadPerDrawParams` kernel-7 path.

## Binary boundary

- Input: `D:\Program Files\Endfield Game\Endfield_Data\Plugins\x86_64\lib_burst_generated.dll`
- SHA-256: `ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99`
- PE image base: `0x180000000`
- Burst `.pdata`: 6,298 `[start RVA, end RVA, metadata RVA]` ranges.
- The Burst resolver at `0x18001d1c0` binds the following external slots:
  `SetEntitySharedDataPartial` string VA `0x1803bb896` to slot
  `0x1803c4440`, `GetEntityDirtyFlags` to `0x1803c43f0`, and
  `SetEntityDirtyFlags` to `0x1803c4420`.

## Positive producer

The range `0x1801d0140..0x1801d045c` is a per-entity loop. It calls the
inner range `0x1801cf3c0..0x1801d013c`, which directly invokes the resolved
shared-data and dirty-flag slots. The inner body has these constant partial
writes (the managed ABI is `sharedDataIndex, data, offset, size`):

| call | offset | size |
| --- | ---: | ---: |
| `0x1801cf890` | `0x50` | `0x20` |
| `0x1801cf91a` | `0x1c` | `4` |
| `0x1801cf975` | `0x18` | `4` |
| `0x1801cfa38` | `0x60` | `0x10` |
| `0x1801cfe38` | `0x14` | `4` |

Each partial write is followed by a dirty-flag read/write. The outer loop
walks the job input count at `[rdi+0x80]` and the per-entity input arrays at
`[rdi+0x60]`/`[rdi+0x68]`; it is therefore a real Burst factory-record update
route, not a generic constant-buffer candidate.

## Native storage contract

`HGFactoryRenderManager.SetEntitySharedDataPartial` is mapped in GameAssembly
at `0x183d689c0`, then reaches UnityPlayer endpoint `0x1801eb9a0` and the
partial-copy core `0x1810d91f0`. The core computes
`manager+0x38 + sharedDataIndex*0x8c + offset` and copies `size` bytes from the
caller data. This confirms that the Burst producer writes the native `0x8c`
shared-data records that later ECS/render maintenance consumes.

## Boundary and next gap

The Burst image has no strings for `ComputeBuffer`, `ComputeShader`,
`CommandBuffer`, `GpuScene`, `UploadPerDraw`, `_UploadBuffer`, `GPUDriven`, or
`Dispatch`; the recovered calls are CPU record maintenance only. Their
offset/size set also does not produce an 84-byte prefix or identify channel 2
/resource `+0xd0`. Keep the record-to-`_UploadBuffer` pack and kernel-7
consumer fail-closed. Reproduce the scan with the disposable probes under
`scratch/reverse_engineering/gpu_scene_upload_next/`.
