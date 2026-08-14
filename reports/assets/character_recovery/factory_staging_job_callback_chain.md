# Factory staging job callback chain

This note records the first indirect caller edge for the native factory
staging consumer in the current UnityPlayer image
(`b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`).

## Registration

`0x1810d33a3..0x1810d367d` constructs a per-factory job object. It stores the
factory input/resource pointers in fields `+0x190/+0x198/+0x1a0/+0x1a8`, builds
the per-item list at `+0x1b8`, and keeps the item count at `+0x188`. At
`0x1810d356f`, a RIP-relative function pointer resolves exactly to
`0x1810d25c0`, the previously recovered dirty-record consumer. The surrounding
call supplies that pointer to `0x180555e50` with the job object in `r9`, the
parallel-item count in the first stack argument, and the per-job descriptor in
`rdx`.

`0x180555e50` is a Unity native job-scheduling wrapper. Its helper
`0x1805572f0` copies the callback pointer into the schedule descriptor and
forwards the descriptor to `0x180559240`; the latter allocates/links the
worker record and completion state. This closes the previously missing static
registration edge from the factory setup to the `0x8c -> 0x100` callback.

The worker-side handoff is also bounded. `0x180558440` selects a queue slot;
its worker path reaches `0x18055865f -> 0x1805598c0`, where an indirect task
entry is loaded from the queued slot and called with the scheduler context and
item index. The remaining alias from the schedule descriptor's stored
`0x1810d25c0` pointer to that final queued-slot field is not statically
unique in this image, so this is an execution-boundary location, not a claim
that the last indirect call has been fully resolved to the factory callback.

## What this does and does not prove

The callback is now positively reachable through a table/job-system path
rather than being an unreferenced pattern match. Its body still performs the
known dirty-bit test and writes the five Vector4 lanes into the per-entry
`+0x100` output record. The scheduler bodies contain no named
`GpuSceneDirtyUpdateCS`, `_UploadBuffer`, ComputeBuffer upload, shader-buffer
bind, or kernel-7 dispatch. The later consumer of the callback-produced
`+0x100` array is therefore still an indirect/table-driven boundary; do not
promote this registration edge to the missing `0x100 -> 0x54` pack or GPU
binding.
