# Persistent custom-per-draw resource bridge

This report records a positive native sink for the generic custom-per-draw
path. It is distinct from the factory manager's `0x8c` shared-data records and
from the callback-local `0x100` scratch array. It proves persistent CPU-side
resource storage, but it does not yet prove the factory GPU-scene upload,
`_RTPerDrawParamsBuffer`, or kernel 7.

## Binary identity

- UnityPlayer: `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- GameAssembly: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`

## Managed-to-native write bridge

The installed internal-call registration maps
`UnityEngine.Renderer::SetCustomPerDrawData_Injected` to UnityPlayer
`0x1800fe590`. The GameAssembly wrapper at `0x183e6e280` is used by the
managed `SetPerDrawData_*` channel helpers (including LitDissolve, HoudiniVAT,
MovingBamboo, Trail, UVAnimation, and VFXAlpha0). The native wrapper forwards
the renderer object, channel index, and a 16-byte Vector4 to `0x180430680`.

`0x180430680` accepts indices whose `index*0x10 < 0x50`, so it covers five
Vector4 lanes. It first writes the renderer-local cache at
`renderer+0xa0+index*0x10`, then checks the resource gate at
`[renderer+0x38]+0x80`. When open, it obtains the global context through
`0x180fc5e60` (pointer-table slot `0x14`), resolves the renderer resource
index from `renderer+0x268`, and writes the same lane to
`resolved+0xb0+index*0x10`.

The resolver `0x1804255f0` is a persistent resource lookup, not callback
stack scratch. Given the context, it reads a 16-byte descriptor from
`context+0x20+resourceIndex*0x10`, uses the descriptor ID to select a record
at `context[0]+id*0x240`, requires the record payload pointer at `record+0x20`,
and applies the record's mask/stride/offset metadata before returning a byte
pointer. This establishes a persistent resource-record destination for the
custom-per-draw payload.

The factory dirty-record callback also reaches this resolver: at
`0x1810d2fc4` and `0x1810d2fd9` it resolves two resource indices, then copies
`0x100` bytes from the first resolved record to the second resolved record,
covering destination offsets `+0x00..+0xf0` in two `0x80`-byte Vector4
passes. That is a second positive CPU-side resource edge, but the copy still
does not identify a GPU buffer upload or dispatch.

## Boundary

The evidence now separates three layouts:

```text
Renderer.SetCustomPerDrawData_Injected
  -> 0x180430680
  -> persistent resource record +0xb0..+0xf0

HGFactoryRenderManager.SetEntitySharedDataPartial
  -> manager + sharedDataIndex*0x8c CPU record

0x1810d25c0 callback
  -> callback-local rbp-0x80 + entry*0x100 scratch
  -> (separate) persistent resource-record copy at 0x1810d2fc4/2fd9
```

No body in this bridge directly calls `ComputeBuffer` upload, command-buffer
dispatch, `UploadPerDrawParams`, `_RTPerDrawParamsBuffer`, or kernel 7. The
factory-record-to-GPU upload edge therefore remains fail-closed; the next
target is the runtime-indirect consumer that binds these persistent records to
the GPU scene resources.
