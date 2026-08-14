# Factory record to `0x100` staging contract

This report records the first positive native consumer after the Burst
factory-record producer. It closes the CPU-side `0x8c` record to render-side
`0x100` staging step, but it does not claim the shader `_UploadBuffer` or GPU
descriptor upload has been recovered.

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
record+0x00 -> output+entry*0x100+0xb0
record+0x10 -> output+entry*0x100+0xc0
record+0x20 -> output+entry*0x100+0xd0
record+0x30 -> output+entry*0x100+0xe0
record+0x40 -> output+entry*0x100+0xf0
```

The five stores are the complete 80-byte shared per-draw payload width. The
same loop advances the render-side output by `0x100` bytes per entry. It also
updates separate per-entry arrays with `0xa4`, `0xd0`, and `0x18` strides;
those increments are distinct from the `0x100` output stride.

The native body has no direct ComputeBuffer upload, SetBuffer/property bind,
command recording, immediate dispatch, `GpuSceneDirtyUpdateCS` kernel-7
selection, or descriptor update. The static result is therefore:

```text
Burst SetEntitySharedDataPartial
  -> UnityPlayer manager + index*0x8c record
  -> 0x1810d25c0 five-lane CPU copy
  -> entry*0x100 render-side staging
  -> [indirect consumer still open]
```

## Boundary

This is stronger than a generic `0x8c` shape match: the consumer reads the
same dirty record layout and emits the exact five-Vector4 payload into a
fixed `0x100`-stride native structure. It is still not the shader's literal
`0x54` (84-byte) `_UploadBuffer` source record. In particular, the numerical
`+0xd0` lane in the `0x100` staging structure must not be aliased with the
renderer custom-per-draw resource's channel-2 `resource+0xd0` slot. Recovering
the subsequent `0x100`-to-`0x54`/GPU upload and kernel-7 binding remains the
next fail-closed gap.
