# `_RTPerDrawParamsBuffer` property path: RayTracing false positive

This note records a native property-ID path that looks like a per-draw
binding at first glance but is not the missing character upload bridge.

## Binary identity

- `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`

## Property-ID registration

The large property registry initializer at `0x181217db0` writes the ID for
`_RTPerDrawParamsBuffer` into the registry object field `+0x130c`. The adjacent
entries are `_RTMaterialLevelBuffer` at `+0x1308` and `_RTRAccelStruct` at
`+0x1310`; the source strings are in the same UnityPlayer string table at
`0x181e2e668..0x181e2e6a8`.

The registry initializer is reached from `0x180fc0130`'s object setup through
`0x181222660`. Registration alone is only a name-to-ID mapping and does not
prove a buffer bind or dispatch.

## Native consumer classification

The only direct field-load match for the `_RTPerDrawParamsBuffer` registry
slot in this image is in `0x180ce30c1..0x180ce3124`. It copies registry fields
`+0x1308/+0x130c/+0x1310` to an internal object at `+0x1c4/+0x1c8/+0x1cc`,
then calls `0x180cf6a50` with the object's resource metadata. The caller-side
initializer `0x180ce2d70..0x180ce30c1` builds the same resource object and
uses the RayTracing-oriented property family (`_RTIndirectionBuffer`,
`_RTInstanceLevelBuffer`, `_RTBLASLevelBuffer`, `_RTMaterialLevelBuffer`,
`_RTPerDrawParamsBuffer`, `_RTRAccelStruct`, and `_RTR*` dispatch/resolve
resources).

The checked bodies contain no load of the factory manager's
`manager+0x38 + index*0x8c` records, no `context+0x110`, no `_UploadBuffer`
pack, no `GpuSceneDirtyUpdateCS.UploadPerDrawParams`, and no ComputeBuffer,
CommandBuffer, or dispatch call. The path therefore belongs to UnityPlayer's
RayTracing resource/object setup, not the unresolved character GPU-scene
upload path.

## Recovery boundary

```text
property registry +0x130c (_RTPerDrawParamsBuffer)
  -> RayTracing resource-object fields +0x1c8
  -> RayTracing metadata initialization

[RayTracing property path -> factory 0x8c -> kernel 7: not found]
```

Keep this path separate from the open edge:

```text
factory manager +0x38 + index*0x8c
  -> 80-byte CPU payload / persistent resource maintenance
  -> [runtime-indirect 0x100 -> 0x54 pack]
  -> [kernel 7 / channel-2 resource +0xd0]
```

