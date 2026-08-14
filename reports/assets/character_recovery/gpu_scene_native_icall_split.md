# Factory shared-data and GPU-scene native boundary

This note records the installed UnityPlayer internal-call registrations below
the managed per-draw bridge. It is a positive/negative split: factory calls
land in the `0x8c` CPU record, while GPU-driven calls bind render resources
through a separate native surface. No static edge between those surfaces was
found in this pass.

## Binary identity

- `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`

UnityPlayer's internal-call table maps these names to native entry points:

| registered call | native entry | bounded behavior |
| --- | --- | --- |
| `HGFactoryRenderManager::SetEntitySharedData` | `0x1801eb970` | resolves manager state at `0x1810d8c30`, then jumps to `0x1810d9170` |
| `HGFactoryRenderManager::SetEntitySharedDataPartial` | `0x1801eb9a0` | resolves the same manager state, then calls `0x1810d91f0` with offset/size |
| `GPUDrivenRendererV1::BindBuffersForCulling` | `0x1801e93a0` | obtains render resources and calls `0x1810f2ab0` |
| `GPUDrivenRendererV1::BindBuffersForRendering` | `0x1801e9480` | obtains render resources and calls `0x1810ef150` |
| `HGShadingStateSystem::SetupGpuSceneUploadCs` | `0x1801ee4c0` | initializes/obtains a runtime GPU-scene upload context through dynamic slots |

The full factory setter at `0x1810d9170` copies the source payload into
`manager+0x38 + sharedDataIndex*0x8c`, including lanes `+0x00..+0x80` and the
trailing dword at `+0x88`. The partial setter at `0x1810d91f0` computes the
same record base and forwards `offset` and `size` to the generic size-copy
helper at `0x181c9f9a0`; this is the native endpoint reached by the managed
`SetEntitySharedDataPartial` wrappers.

The GPU-driven V1 culling/render wrapper bodies do not pass the factory
manager `+0x38` record or its `+0x70` dirty byte. Their native callees resolve
resource bindings and pass a runtime context into buffer-binding helpers;
whether a later runtime-indirect callee consumes that context is still open.
`SetupGpuSceneUploadCs` likewise resolves runtime slots and retains no static
reference to the factory record, `_UploadBuffer`, kernel 7, or channel-2
resource `+0xd0`.

## Context-side resource maintenance

The global-context accessor used by the custom-per-draw bridge and the
GPU-scene setup path is UnityPlayer `0x180fc5e60`; it is a small thunk that
obtains pointer-table slot `0x14`. The companion helper at `0x180fc5ec0`
obtains that context, calls `0x1810d36b0` on `context+0x110`, then forwards
`context+0x200` to `0x180e75000`.

`0x1810d36b0` performs a CPU-side resource-table update. Its `this+0x38`
array is walked with an exact `index*0x8c` stride; active entries are checked
through the per-entry flag at `record+0x74` and routed through
`0x1810d4020`. The resulting resource pair is copied by
`0x1810d8d40`, which reaches the persistent resolver family
(`0x180424d60`, `0x180424ec0`, `0x180425030`, `0x1804251a0`,
`0x180425310`, `0x180425480`, `0x1804258d0`, and `0x18033b740`) and then
`0x1810ccd20` for the `0x100`-byte resource-block copy (two `0x80`-byte
Vector4 passes). The terminal helper
`0x1810c7a30` updates the companion resource list.

The pointer alias is now closed rather than inferred. The manager resolver
`0x1810d8c30` calls the same `0x180fc5e60` and returns
`[context+0x110]`; both `HGFactoryRenderManager::SetEntitySharedData*`
internal-call wrappers use that resolver. Consequently the `this+0x38` array
walk in `0x1810d36b0` is the same `manager+0x38 + index*0x8c` record family
written by the factory setters. This proves a CPU-side factory-record to
persistent-resource-maintenance edge, including the `0x1810ccd20` copy.

None of these bodies directly calls ComputeBuffer, CommandBuffer,
`_UploadBuffer`, or dispatch. The persistent resource to GPU upload edge
therefore remains runtime-indirect and fail-closed.

The common resource context is now bounded separately from the factory record.
`HGRenderPath` BeforeCulling (`0x1812fdd80 -> 0x1813018c0`) also calls
`0x180fc5e60`, keeps the returned global context, and selects two entries from
`context+0xe8` through `0x1810e6310` (selectors `0` and `1`) for render-path
state. The GPUDriven V1 binders reach the same selector helper through
`0x1810f1980`. These bodies therefore share the runtime resource-context
origin, but do not read the global `context+0x110` factory-record array; the
render-path object's own `+0x110` input is a separate state field. This
strengthens the negative split: common `+0xe8` resource selection is proven,
while a static `manager+0x38`/`0x8c` to GPU binder upload edge is not.

The V1/V2 GPUDriven split is also concrete. V1 wrappers call
`0x1810f1980`, which selects `context+0xe8` entry `0`; V2 wrappers call
`0x1810fe120`, which selects the same table entry with selector `1`. V2's
render binder (`0x1810fb5a0`, reached by the managed
`GPUDrivenRendererV2::BindBuffersForRendering` wrapper) reads its runtime
resource descriptor block at `+0x88..+0xd0` and, for a command-stream target,
emits the high-level resource-binding writer `0x1804cb1a0` (opcode `0x0d`).
The immediate path uses `0x1805f84a0` for the same descriptor fields. V1/V2
dispatch helpers (`0x1810f17e0`/`0x1810f1890`) instead reach
`0x1805e7e10`, which invokes the graphics-context vtable slot `+0xab0`.
This proves a positive resource-selection -> GPUDriven binding/dispatch chain,
but the checked bodies never load the factory `context+0x110` record array or
the `manager+0x38 + index*0x8c` records. The runtime descriptor `+0xd0` must
therefore remain distinct from the factory channel-2 `+0xd0` until a stronger
alias is found.

The V1 command-record side is now bounded as a distinct format rather than
being grouped with V2. V1 rendering (`0x1810ef150`) uses immediate helper
`0x180fd96c0` or, for a command target, writer `0x1804cb730`, which records
opcode `0x2b` and one qword payload. The immediate helper resolves resource
IDs through its context metadata and appends the resulting index to dynamic
resource tables before reaching `0x1805d5520`; it does not read factory
records. V1 culling (`0x1810f2ab0`) uses immediate `0x1805f84a0` over runtime
descriptor fields beginning at `+0x8c..+0xb0`, or command writer
`0x1804cd7d0`, which records opcode `0x57` with a 0x20-byte payload. Thus the
runtime command formats are now explicit: V1 rendering `0x2b`, V1 culling
`0x57`, and V2 binding `0x0d`; none of these checked producers loads the
factory `manager+0x38 + index*0x8c` record.

The TLS tail is now resolved for the installed graphics-context constructor.
`0x180725dc0` reads the process TLS index at `0x182111300` and calls the
runtime-resolved `TlsGetValue` import at `0x181cb0980`. The setter
`0x180727ea0` stores the graphics-context pointer in `0x1821b9990`, calls
`TlsSetValue` through `0x181cb0970`, and is reached from device/backend
initialization at `0x1807303b5`. For the normal non-null backend path,
`0x180929430` allocates the `0x2a00`-byte TLS context through
`0x1809258c0`, whose constructor writes vtable `0x181dcb360`; therefore
vtable `+0xea0` is the static function pointer `0x1809324e0`, and vtable
`+0x850` is `0x180934850`. The alternate backend-state `0/5` branch still
returns through `0x18072f7e0` and is kept conditional rather than conflated
with this constructor.

`0x1809324e0` is a command-stream encoder, not a factory-record consumer. It
uses the context's `+0x2720` command arena and emits opcode `0x273b`, writing
the caller's resource/payload arguments and optional aligned data. The
`+0x850` implementation `0x180934850` emits opcode `0x2798`, updates the same
arena's size marker, and increments the context counter at `+0x29bc`. Context
binding at `0x180939c80` stores the selected backend object at `+0x2708`,
copies backend capabilities, and fills `+0x1fd8/+0x1fe0`; it does not load the
factory `context+0x110` record array or the `manager+0x38 + index*0x8c`
records. The static tail is consequently recovered, while the
factory-record-to-upload edge remains fail-closed.

The command interpreter confirms where these records land. The large
interpreter `0x1813aee90..0x1813bb9bc` subtracts `0x2711` from each command
opcode and dispatches through jump table `0x1813bb574`; entries map `0x273b`
to `0x1813b1110`, `0x2798` to `0x1813b55ea`, and the previously bounded `0x27ef`
to `0x1813b805b`. Case `0x273b` parses the encoded pointer, byte count, and
aligned payload, then invokes the function-pointer cell carried by the
record. The V1 culling producer supplies the on-disk trampoline at
`0x1810e6450` (an `E9` stub targeting `0x18115d810`); because the interpreter
calls through the carried cell, this is recorded as a trampoline/payload link,
not as a claim that the raw on-disk bytes are already the final callable slot.

The trampoline target is a positive resource-side path: `0x18115d810` builds a
small layout descriptor, obtains the global context via `0x180fc5e60`, and
passes `context+0x190` to `0x1810e3b40`. That helper allocates or reuses several
size/stride-specific buffer records through `0x1810e1ea0` and inserts/copies
the resulting 0x80-byte rows through `0x1810e0a30`. None of
`0x18115d810`, `0x1810e3b40`, `0x1810e1ea0`, or `0x1810e0a30` loads
`context+0x110`, `manager+0x38`, or an `index*0x8c` factory record. This
strengthens the resource-allocation side of the GPU tail while keeping the
factory-record-to-upload alias unresolved.

Therefore the current static boundary is:

```text
ApplyPerDrawRender
  -> SetEntitySharedDataPartial
  -> manager + sharedDataIndex*0x8c CPU record

GPUDrivenRenderer / SetupGpuSceneUploadCs
  -> runtime resource/context slots
  -> context+0xe8 selector 0/1
  -> V2 resource descriptors -> opcode 0x0d writer
  -> V1/V2 dispatch -> graphics-context vtable +0xab0
  -> context+0x110 FrameUpdateStep2 / CPU resource maintenance
  -> buffer/compute binding helpers

[factory record -> persistent GPU upload/dispatch consumer: unresolved]
```

The `0x1810d25c0` job callback remains a callback-local scratch consumer of
dirty factory records, as documented in
`factory_record_to_100_staging_contract.md`; it is not promoted to the GPU
upload path by these internal-call registrations.
