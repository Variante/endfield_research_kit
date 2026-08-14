# Factory record to `0x100` staging contract

This report records the first positive native consumer after the Burst
factory-record producer. The callback does copy five lanes at `+0xb0..+0xf0`
with a `+0x100` loop stride, but the destination is a callback-local stack
scratch array, not a persistent render/GPU staging allocation. The shader
`_UploadBuffer` and GPU descriptor upload therefore remain open.

## Binary boundary

- Input: `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- Main body: `0x1810d25c0..0x1810d3198`; the installed metadata/RVA tables
  also expose the interior table entry `0x1810d26bf`.
- The interior entry has no direct `E8` caller or raw code-pointer xref in
  the UnityPlayer image. Its invocation remains a table-driven ECS/job
  callback boundary.

## Positive native consumer

The body computes one source record per entity as:

```text
record = manager_shared_base + entity_index * 0x8c
```

The record base is kept in `r13`; the body tests `record+0x70` dirty bits and,
when bit 0 is set, copies exactly five 16-byte lanes:

```text
record+0x00 -> scratch+entry*0x100+0xb0
record+0x10 -> scratch+entry*0x100+0xc0
record+0x20 -> scratch+entry*0x100+0xd0
record+0x30 -> scratch+entry*0x100+0xe0
record+0x40 -> scratch+entry*0x100+0xf0
```

The five stores are the complete 80-byte shared per-draw payload width. The
same loop advances the scratch base by `0x100` bytes per entry. At function
entry, `0x1810d25e7` sets the base to `rbp-0x80`, and the callback saves that
pointer at `[rsp+0x68]`; later calls such as `0x18056cb40` consume the same
local data. The callback also updates separate per-entry arrays with `0xa4`,
`0xd0`, and `0x18` strides; those increments are distinct from the `0x100`
scratch stride. No persistent output handle is established by this body.

The native body has no direct ComputeBuffer upload, SetBuffer/property bind,
command recording, immediate dispatch, `GpuSceneDirtyUpdateCS` kernel-7
selection, or descriptor update. The static result is therefore:

```text
Burst SetEntitySharedDataPartial
  -> UnityPlayer manager + index*0x8c record
  -> 0x1810d25c0 five-lane callback-local scratch copy
  -> internal CPU/VFX/resource helpers
  -> [persistent render/GPU consumer not identified]
```

## Boundary

This is stronger than a generic `0x8c` shape match, but it is now classified
as a CPU/VFX/factory scratch layout rather than a render-side staging buffer.
It is still not the shader's literal `0x54` (84-byte) `_UploadBuffer` source
record. The numerical `+0xd0` scratch lane must not be aliased with the
renderer custom-per-draw resource's channel-2 `resource+0xd0` slot. Recovering
the persistent `0x100`-to-`0x54`/GPU upload and kernel-7 binding remains the
next fail-closed gap.

## Managed per-draw write-side bridge

The installed GameAssembly image (SHA-256
`0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`)
also closes the write-side path that feeds the same native record family.
`UnsafeJobFuncPointers.ApplyPerDrawRender$BurstManaged` at `0x1869d8434`
loops through `GlobalSharedData+PerDrawGlobalSetting.Apply` at
`0x1869d5d30`, which invokes `PerDrawConfig.Apply` at `0x1869f3654` for each
config. Its value-type branches are concrete native wrappers:

- scalar (`valueType=2`): `0x1840f30e0` validates `offset+4 <= 0x50`, calls
  `0x183d68850`, and marks the binder dirty through `0x1834a3fa0`;
- vector (`valueType=1/3`): `0x1876aaefc` forwards a 16-byte payload.

Both wrappers call the mapped `HGFactoryRenderManager.SetEntitySharedDataPartial`
endpoint at `0x183d689c0` with the config offset and sizes `4` or `0x10`.
The public `ApplyPerDrawRender` entry at `0x1869d8488` reaches the Burst direct
call wrapper at `0x1869d3434`; this is a positive managed-to-native
write-side edge, but it only updates native shared-data records. It contains
no ComputeBuffer/property bind, dispatch, or `_UploadBuffer` pack.
