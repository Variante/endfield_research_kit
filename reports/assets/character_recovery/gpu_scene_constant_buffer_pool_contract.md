# GPU-scene constant-buffer pool contract

This is an offline binary audit. Endfield and the Unity recovery lab were not
launched. The result narrows one plausible upload candidate; it does not claim
the missing factory channel-2 bridge.

Inputs:

- `GameAssembly.dll`: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `UnityPlayer.dll`: SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `global-metadata.dat`: SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- direct PData-scoped disassembly of the GameAssembly methods below; the
  maintained source evidence is also recorded in
  `unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/packed_flags_producer_recovery.json`.

## Recovered contract

`HG.Rendering.Runtime.HGConstantBufferPool::.ctor` at `0x189b6aa28` allocates
its `this+0x10` `ComputeBuffer` through `0x18b3d7374`. The call arguments are
unambiguous in the x64 body:

```text
count       = 0x80000       (edx)
stride      = 1 byte        (r8d)
type        = 8             (r9d)
destination = this + 0x10
```

The same body stores a dynamic segment container at `this+0x18`. Its segment
records are the metadata-backed `HGConstantBufferPool+Segment` shape with
`offset`, `size`, and `data` fields.

`HGConstantBufferPool::ApplyPendingUpload` at `0x189b6a7c0` first queries
`ComputeBuffer.get_stride`/`get_count`, grows or replaces the buffer when the
requested byte range no longer fits, then walks the segment array. Its only
direct GPU upload call is `0x187af05e0`, the generic
`ComputeBuffer.SetData<byte>` instantiation. The call passes each segment's
data pointer and offset/size range; no compute dispatch, shader property bind,
command recording, or named GPU-scene resource occurs in the body.

The replacement path reconstructs the same `count=0x80000`, `stride=1`,
`type=8` buffer and resets the pending counters. `Reset` at `0x189b6a9c0`
disposes the segment container and clears the upload cursor.

## Negative result and boundary

An image-wide direct-call census finds zero direct callers of
`ApplyPendingUpload` and exactly one direct caller of `ComputeBuffer.SetData<byte>`:
the pool's own loop at `0x189b6a97d`. The body contains no reference to
`GpuSceneDirtyUpdateCS`, `UploadPerDrawParams`, `_UploadBuffer`, factory staging
records, resource `+0xd0`, or channel 2. Its byte-stride buffer therefore cannot
be substituted for the shader's separate 84-byte `_UploadBuffer` source record.

This closes the generic constant-buffer pool as a false positive and preserves
the correct recovery boundary: the factory 0x100-stride staging-to-84-byte
pack, kernel-7 dispatch, and channel-2 resource-to-descriptor upload remain
unrecovered and fail-closed.

Reproduce the native body probe with:

```bat
python scratch\reverse_engineering\gpu_scene_upload_next\disasm_address.py 0x189b6aa28 0x180
python scratch\reverse_engineering\gpu_scene_upload_next\disasm_address.py 0x189b6a7c0 0x220
```
