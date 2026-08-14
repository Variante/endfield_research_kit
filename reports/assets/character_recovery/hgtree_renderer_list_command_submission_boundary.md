# HGTree renderer-list to CommandBuffer boundary

## Verdict

The installed build now pins the managed HGTree list path to the native
CommandBuffer tree-list enqueue path. This is the first checked edge from the
component-67 LOD/list work into a renderer-list command producer. The native
GPU submission/resource consumer after the tree helper remains opaque and is
still fail-closed; this is not a retail frame-parity claim.

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
2. The UnityPlayer internal-call name/function tables pin those wrappers to:

   | managed native call | UnityPlayer target | context slot read |
   | --- | ---: | ---: |
   | `HGTreeRender::CreateRendererList` | `0x1801D75A0` | `context+0x1F4C` |
   | `HGTreeRender::CreateRendererListWithChildViewHandle` | `0x1801D7640` | `context+0x1F50` |
   | `HGTreeRender::CreateRendererListWithPreZ` | `0x1801D76E0` | `context+0x1F3C` |
   | `HGTreeRender::RegisterTreeBatchGroup` | `0x1801D7780` | `context+0x1F44` |
   | `HGTreeRender::UnregisterTreeBatchGroup` | `0x1801D7820` | `context+0x1F48` |

   These targets perform the same context-owned keyed lookup and return an
   opaque renderer-list/resource handle. They do not contain a ComputeBuffer,
   dispatch, or direct graphics API call.
3. `HGTreeRender.DrawECSRendererList` (`GameAssembly 0x18B3FBFA4`) rejects a
   null command buffer, then tail-jumps to the resolved internal call
   `UnityEngine.Rendering.CommandBuffer::AddDrawECSTreeRendererList(System.UInt32)`.
4. The current UnityPlayer CommandBuffer table maps that call to
   `0x180149500`. Its body converts the incoming opaque handles through the
   shared runtime converter and reaches the tree-specific helper
   `0x180A16870`. This is the bounded native command-producer edge after the
   renderer-list handle; the helper's downstream GPU/command-stream consumer
   is not identified by static evidence in this pass.

The component-67 evidence remains separate: its 24-byte records feed native
LOD/culling list construction, but no direct static xref from the accessor to
the managed HGTree wrapper or to the tree helper was established here.

## Reproduction

```bat
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --member-regex "$^" --body-target-regex "^(CreateRendererList|CreateRendererListWithPreZ|DrawECSRendererList)$" --body-target-type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --all-images --include-all-members --body-context 1 --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A16870 0x180A160F0
```

