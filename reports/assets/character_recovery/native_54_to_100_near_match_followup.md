# Native 0x54-to-0x100 near-match follow-up

## Scope

This is a bounded follow-up to the recovered UnityPlayer consumer
`0x1810d25c0..0x1810d3198`, which copies the factory `0x8c` record's five
shared-data lanes into `output + entry * 0x100 + 0xb0..0xf0`. The question was
whether the first literal `0x54` layouts in the same UnityPlayer image are the
missing `_UploadBuffer` packer.

Evidence is from the installed UnityPlayer image:

- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `0x1812117ec..0x181211c02`
- `0x1812145af..0x181214888`

## Exact near-match

Both functions contain a real `index * 0x54` source walk and an independent
`index * 0x100` destination walk. The useful shape is:

| body | source | destination | observed fields |
| --- | --- | --- | --- |
| `0x1812117ec` | `r14 + index*0x54`, source fields `+0x30..+0x50` | `r12 + index*0x100` | copies destination `+0x00..+0x30` into `+0x60..+0x90`; updates `+0x30/+0x34/+0x38` |
| `0x1812145af` | `r14 + index*0x54`, source fields `+0x00..+0x50` | `r12 + index*0x100` | same destination `+0x60..+0x90` preservation and `+0x30..+0x38` updates |

The first body also derives four scalar values from source `+0x30..+0x3c`
and accumulates source `+0x48..+0x50`; the second body calls native helpers
`0x18120b670`/`0x18120b470` while transforming the source. Neither body reads
`manager+0x38 + entityIndex*0x8c`, tests `record+0x70`, or copies the factory
shared prefix at destination `+0xb0..+0xf0`.

## Boundary result

These are genuine `0x54`/`0x100` native layouts, not a heuristic false
positive, but they are not the factory-to-`_UploadBuffer` path. Their direct
callee sets contain no checked ComputeBuffer upload, ComputeShader/Command-
Buffer bind, `GpuSceneDirtyUpdateCS`, `UploadPerDrawParams`, or kernel-7
dispatch edge. The exact `0x54` literal therefore remains an alternate native
record layout; it cannot close the shader ABI gap without an explicit link to
the factory staging lanes and the shader's 84-byte `[index, 5*Vector4]`
contract.

## Next gap

Keep the GPU edge fail-closed. The next useful search is an indirect scheduler
or callback consumer that reads `output + entry*0x100 + 0xb0..0xf0`, prefixes
the entity/index dword, and writes an 84-byte upload record before binding
`_UploadBuffer` and dispatching `UploadPerDrawParams` kernel 7.
