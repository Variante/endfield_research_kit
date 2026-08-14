# HGTree renderer-list to CommandBuffer boundary

## Verdict

The installed build now pins both halves of the managed HGTree renderer-list
route. The dedicated HyperGryph internal-call wrappers reach native cores that
build renderer/resource records and call a graphics-context vtable slot; the
separate CommandBuffer tree-list call is pinned to its GC-root and
string-payload validation boundary. Neither branch proves the final GPU
submission or command-stream consumer, so this remains fail-closed and is not a
retail frame-parity claim.

## Source pins

| Input | SHA-256 |
| --- | --- |
| `D:\\Program Files\\Endfield Game\\UnityPlayer.dll` | `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2` |
| `D:\\Program Files\\Endfield Game\\GameAssembly.dll` | `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce` |
| `global-metadata.dat` | `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e` |

## Recovered chain

1. The current metadata/catalog maps `HGTreeRender.CreateRendererList` and
   its `WithPreZ` overloads to the GameAssembly runtime-resolved internal-call
   wrappers (`0x18B3FBF44`, `0x18B3FBE50`, `0x18B3FBEB0`). Their strings are
   passed to `il2cpp_codegen_resolve_icall`; there is no static GameAssembly
   renderer implementation to substitute.
2. The dedicated HyperGryph table (729 entries; names at `0x1820E6E90`,
   functions at `0x1820E8560`) pins those calls to:

   | managed native call | UnityPlayer target | context slot read |
   | --- | ---: | ---: |
   | `HGTreeRender::CreateRendererList` (index 564) | `0x1801D9D10` | `context+0xC0` |
   | `HGTreeRender::CreateRendererListWithChildViewHandle` (index 565) | `0x1801D9F10` | `context+0xC0` |
   | `HGTreeRender::CreateRendererListWithPreZ` (index 566) | `0x1801D9FA0` | `context+0xC0` |

   The wrappers call `0x180FC5E60` for the context and forward to cores
   `0x18107EE40`, `0x18107FCF0`, and `0x181080190`. The normal core checks the
   renderer index, builds context-owned records and allocations, and its
   successful branch calls graphics-context vtable slot `+0xEA0` at
   `0x18107F13F`. Fallback builders `0x18107E2E0` and `0x181080730` write the
   result record and allocate/copy per-renderer arrays. This is a positive
   creation/resource-record boundary, but the dynamic vtable target and final
   command consumer remain unresolved.
3. `HGTreeRender.DrawECSRendererList` (`GameAssembly 0x18B3FBFA4`) rejects a
   null command buffer, then tail-jumps to the resolved internal call
   `UnityEngine.Rendering.CommandBuffer::AddDrawECSTreeRendererList(System.UInt32)`.
4. The current UnityPlayer CommandBuffer name/function tables map that call at
   index 321 to `0x1801719B0`. The earlier `0x180149500` attribution was a
   table-index error: that address is a Profiler entry, not the tree-list
   internal call. The true tree body uses slot `0x1821BE708` twice for local
   managed-pointer root writes. Static initialization at
   `0x18077C050/0x18077C055` calls `0x1806898F0` with the string
   `il2cpp_gc_wbarrier_set_field` (`0x181D9E7F8`) and writes the result into
   that BSS slot, so it is not a renderer-list converter.
5. After the two GC-barrier calls, `0x1801719B0` forwards the local wrapper to
   `0x180A5C5C0`. That helper is shared by neighboring CommandBuffer draw
   entry points; its checked body calls `0x180769E20` (string-payload
   conversion/validation) and `0x18065C0C0`, returns a status, and emits only
   an error path on failure. It contains no visible ComputeBuffer, dispatch,
   graphics API, or command-stream opcode. This is a separate draw
   validation boundary, not a proven downstream step from the creation cores.
6. Therefore this pass closes the HGTree creation/resource-record boundary and
   the separate CommandBuffer GC-root/validation boundary without claiming GPU
   submission. The next bounded target is the dynamic graphics-context
   `+0xEA0` target and the later tree-specific command/resource consumer, not
   `0x1821BE708` and not the unrelated Profiler entry `0x180149500`.

The component-67 evidence remains separate: its 24-byte records feed native
LOD/culling list construction, but no direct static xref from the accessor to
the managed HGTree wrapper or to the tree helper was established here.

## Reproduction

```bat
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --member-regex "$^" --body-target-regex "^(CreateRendererList|CreateRendererListWithPreZ|DrawECSRendererList)$" --body-target-type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --all-images --include-all-members --body-context 1 --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801D9D10 0x1801DA040
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107EE40 0x1810802A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801719B0 0x180171A40
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A5C5C0
```
