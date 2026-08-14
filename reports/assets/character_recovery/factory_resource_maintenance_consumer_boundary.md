# Factory resource-maintenance consumer boundary

This note records the newly checked consumer of the factory-linked
`context+0x110` resource-maintenance path. It is a teardown/reclamation path,
not the missing per-draw upload producer.

## Binary identity

- `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`

## Caller and behavior

The only direct `E8` call to `0x1810d8d40` in the installed UnityPlayer is at
`0x1810d3f27`, inside the split function ranges
`0x1810d39b3..0x1810d3fcd` (with the preceding frame-step ranges beginning at
`0x1810d36b0`). The surrounding loop:

1. walks active resource entries selected from the factory-linked `0x8c`
   records and tests the entry flags;
2. calls `0x1810d4020` to resolve the resource pair;
3. calls `0x1810d8d40` with the pair and the active-entry count; and
4. immediately passes the returned pointer to `0x1810c7a30`, then stores that
   result in the companion resource list.

The caller also clears/recycles the associated arrays and decrements the
resource counters around this loop. This is consistent with resource
maintenance/reclamation, not a frame upload or dispatch stage.

`0x1810d8d40` itself is closed as CPU metadata work. It copies descriptor
subrecords through `0x180424d60`, `0x180424ec0`, `0x180425030`,
`0x1804251a0`, `0x180425310`, `0x180425480`, `0x1804258d0`,
`0x18033b740`, and `0x1810cd540`; copies one 0x100-byte block through
`0x1810ccd20`; updates a flag and the resolver-derived array; and writes the
entry index into 0x18-byte metadata rows. There is no ComputeBuffer,
CommandBuffer, graphics-context `+0xab0`/`+0xab8`, command opcode, or kernel
selection in this body.

## Recovery consequence

This closes one tempting consumer of the factory record and persistent
resource alias as a negative: the `0x8c` record can reach CPU resource
maintenance and reclamation, but this direct branch cannot produce the
84-byte `_UploadBuffer`, select `UploadPerDrawParams` kernel 7, or bind the
channel-2 resource `+0xd0`. The runtime-indirect persistent-resource-to-GPU
upload edge remains fail-closed.

