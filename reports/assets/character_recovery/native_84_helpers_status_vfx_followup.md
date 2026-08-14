# Native 84-byte helper classification

This note records the exact `0x54`-stride helpers found in the current
`GameAssembly.dll` image (`0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`).
They are useful layout matches, but their call graph closes them as generic
gameplay/VFX data rather than the GPU-scene upload source.

## Exact native shape

`0x1800a5fe0..0x1800a6029` bounds-checks an index, computes
`index * 0x54`, reads five 16-byte lanes from object offsets
`+0x20,+0x30,+0x40,+0x50,+0x60`, and one dword at `+0x70`, then writes a
contiguous 84-byte result at the caller-provided destination (`+0x00..+0x50`).
`0x18067606c..0x1806760c5` is the inverse writer: it reads the same five lanes
and dword from a contiguous source and stores them back at the indexed object
element. The dword is therefore at the end of this layout, not at the
shader's source offset `+0x00`.

## Caller classification

The bounded executable-section xref census maps the reader/writer to:

- `Beyond.Gameplay.Factory.FacWikiBuildingRendererMono._ResolvePreviewSubState`;
- `HG.Rendering.Runtime.VFXPPCutsceneEffect.Apply`;
- `List<StatusSingleEffect>.get_Item` and related
  `ObjectEqualityComparer<StatusSingleEffect>.IndexOf/LastIndexOf`;
- generic list/array helpers over `StatusSingleEffect` and VFX `Options&`;
- unrelated `RVOAgentJobData`/MagicaCloth generic container instantiations.

No caller reads the factory manager record at
`0x1810d25c0 + index*0x8c`, the confirmed `+0xb0..+0xf0` staging lanes, or
`GpuSceneDirtyUpdateCS.UploadPerDrawParams`. No caller reaches a checked
ComputeBuffer upload, shader-buffer bind, command dispatch, or kernel 7.

## Boundary

The `0x54` literal and five-vector footprint are real native data-layout
evidence, but this exact helper family is status/VFX/container data. It must
not be substituted for the unresolved factory `0x8c -> 0x100 -> 0x54`
conversion or for `_UploadBuffer` (whose source record is index dword first,
then five Vector4 lanes). The shader upload producer, kernel-7 selection, and
channel-2/resource `+0xd0` binding remain fail-closed.
