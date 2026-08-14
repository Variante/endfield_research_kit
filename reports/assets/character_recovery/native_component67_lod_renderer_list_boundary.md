# Native component 67 LOD / renderer-list boundary

## Verdict

The installed UnityPlayer build now gives an exact identity for the previously
unnamed native ECS slot 67: it is the 24-byte per-entity state record consumed
by the native LOD/culling list path. Its standalone native type name is still
unresolved, so this does not license renaming it to a managed component.

This is a positive native identity/role result, not a retail frame-parity
claim and not evidence for the unresolved factory-channel-2 GPU upload edge.

## Source pins

| Input | SHA-256 |
| --- | --- |
| `D:\\Program Files\\Endfield Game\\UnityPlayer.dll` | `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2` |
| `D:\\Program Files\\Endfield Game\\GameAssembly.dll` | `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce` |
| `global-metadata.dat` | `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e` |

The raw xref census is retained in
`scratch/reverse_engineering/hgtree_renderer_list_vtables/lod_component67_accessor_xrefs.json`.

## Exact slot identity

`UnityPlayer!0x181038D00` is the typed ECS accessor used by 18 direct xrefs
(14 distinct native owners). Its first branch is:

```text
mov rax, [rcx]          ; archetype/type metadata
movzx edx, byte [rax+18h]
shr dl, 3
test dl, 1              ; require high-mask bit 3
```

The high mask is the component-id range 64..127, so bit 3 is exactly
component `64 + 3 = 67`. The accessor then popcounts the low mask and the
preceding high bits (`high & 7`) and uses the archetype offset table at `+44h`
with stride `+30h` to return the component-67 data pointer. The neighboring
helpers prove the numbering convention: `0x181038D70` tests low-mask bit 63
and `0x181038DE0` tests low-mask bit 62.

The managed IDs are deliberately different. The current GameAssembly mapping
returns `6` for `RenderObjectLODInfoComponent.get_id()` (`0x184D9EC60`) and
`0x50` for `HGTreeComponent.get_id()` (`0x184DBCEC0`). No managed `get_id`
target in the current HGGraphicsModule catalog returns 67. Do not merge slot
67 with either managed type.

## LOD and list-path behavior

- The component-67 callers advance the returned data pointer by `0x18` per
  entity, fixing the native element size at 24 bytes.
- LOD jobs `0x18106D7FF` and `0x18106DA9F` call the accessor, compute squared
  distance from three float coordinates, compare against LOD interval bounds,
  and mutate the record's byte state. The transition path writes `0x0808`
  into adjacent state bytes and updates the next state byte; this is a state
  update, not a texture/material payload.
- Native list/culling builders at `0x1810786D6`, `0x181078A06`,
  `0x181078D46`, and `0x1810790D0` call the same accessor, inspect the record
  bytes, and append entity indices plus packed state masks to list arrays.
- Initialization/maintenance callers at `0x181000F10`, `0x181001B80`,
  `0x181002CC0`, and `0x18108430D` complete the CPU-side lifecycle. The
  xref set contains no ComputeBuffer, command-stream opcode, or GPU dispatch.

This closes the semantic boundary as **native LOD/culling state feeding list
construction**. It does not identify the serializer's source-side type name,
prove a direct `HGTreeRender` managed-wrapper edge, or close the separate
factory-record-to-`UploadPerDrawParams` kernel-7 path.

## Reproduction

```bat
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x181038D00 0x181038D70
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x18106D7FF 0x18106D9D0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x1810786D6 0x181079316
```
