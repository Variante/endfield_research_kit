# Native `+0x100` variant writer follow-up

This note records the next bounded UnityPlayer census for the current installed
image (`b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`).
Three broad candidates from the `+0x100`/`+0xb0..+0xf0` screen were inspected
at their PData starts:

- `0x181758280..0x18175b9b0`
- `0x18175ba50..0x1817604a1`
- `0x181760960..0x181763154`

They are variants selected by the dispatcher at `0x181757f8a`, which reads a
type byte at `record + 0xad` and calls one of four sibling bodies. Their common
shape is a CPU-side effect/record transform: each consumes an object whose
`+0x38` count and `+0x70` array are walked with a `0x220` source stride, emits
small `0x2c` records, serializes large local records, and advances a separate
destination by `+0x100`. The apparent `+0xb0..+0xf0` accesses are local record
fields or copies into the variant's own output; they do not read the factory
manager's `+0x38 + index*0x8c` records, test dirty `+0x70`, or consume the
factory staging lanes.

The bodies call only local math/container/serialization helpers and the generic
CPU copy helper `0x181c9f9a0`. No direct `ComputeBuffer` upload, buffer/property
bind, command recording, `GpuSceneDirtyUpdateCS` kernel 7, `_UploadBuffer`, or
the recovered factory consumer `0x1810d25c0` appears in the inspected paths.
The dispatcher itself has no direct caller in the installed UnityPlayer image,
so it does not establish an indirect GPU edge either.

Conclusion: these are additional false positives for the staging census. They
confirm that `+0x100` is reused by unrelated native record families, but do not
change the fail-closed boundary: the factory `0x8c -> +0xb0..+0xf0` staging
consumer and its upload/dispatch successor remain unresolved.
