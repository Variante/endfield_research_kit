# HGTree renderer-list to CommandBuffer boundary

## Verdict

The installed build now pins the HGTree creation cores through their concrete
graphics-context and command-stream callback route. The dedicated HyperGryph
wrappers build renderer/resource records, resolve vtable `+0xEA0`, and emit
opcode `0x273B`; the interpreter dispatches that opcode to HGTree-specific
callbacks. The populated resource records then reach callback-built renderer
records whose thunks enter graphics-context vtable loops. The separate
CommandBuffer tree-list call is pinned to its GC-root and string-payload
validation boundary. Concrete device/API submission behind those vtable slots
is still unresolved, so this remains fail-closed and is not a retail
frame-parity claim.

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
   result record and allocate/copy per-renderer arrays.
3. The dynamic graphics context is now pinned. Getter `0x180725DC0` reads TLS
   index `0x182111300` through `TlsGetValue` (`0x181CB0980`). The backend setup
   path `0x18072F3EB -> 0x180929430 -> 0x1809258C0` allocates the `0x2A00`
   context and writes vtable `0x181DCB360`; `0x1807303B5 -> 0x180727EA0`
   stores the same pointer in the TLS/global slot. Vtable `+0xEA0` is concrete
   target `0x1809324E0` (and `+0x850` is `0x180934850`).
4. `0x1809324E0` writes command-stream opcode `0x273B` (at
   `0x18093255B`), followed by the callback pointer and descriptor fields. The
   normal/child/PreZ creation cores supply callbacks
   `0x181060D90 -> 0x18107AD80`, `0x181060D20 -> 0x1810794D0`, and
   `0x181060D00 -> 0x181079320`. The command interpreter entry
   `0x1813AEE90` subtracts `0x2711` from the opcode and uses table
   `0x1813BB574`; entry `0x273B` lands at `0x1813B1110`, which consumes the
   callback/size/record fields and invokes the callback. The callback bodies
   call the HGTree fallback record builders and copy the resulting record into
   the renderer-list state; no direct graphics API or final backend draw is
   visible in this callback boundary.
5. The callback output layout is now bounded. The normal creation core appends
   a 0x18-byte list item whose `-0x10` and `-0x08` fields point to the 0x98-byte
   descriptor and 0x30-byte result records; `-0x18` is the completion status.
   `0x18107AD80` (normal) and `0x1810794D0` (child) call
   `0x181080730`, then copy its first 16-byte result into the result record at
   `+0x20`. `0x181079320` (PreZ) uses the same builder and copies that result
   into both linked result records. The builder allocates/copies the
   per-renderer array (`count * 16` from `+0x48` into `+0x50`) and passes the
   assembled record through `0x180555A30`/`0x180555D30`, an internal
   renderer-resource pool/list path. Those helpers continue into the
   `0x1805592B0 -> 0x1805582A0` resource-node allocator (0x80-byte node
   stride), but the
   inspected path still contains no explicit graphics API, draw, dispatch, or
   device submission. This closes callback-to-resource-pool ingress while
   leaving the final backend consumer unresolved.
6. `HGTreeRender.DrawECSRendererList` (`GameAssembly 0x18B3FBFA4`) rejects a
   null command buffer, then tail-jumps to the resolved internal call
   `UnityEngine.Rendering.CommandBuffer::AddDrawECSTreeRendererList(System.UInt32)`.
7. The current UnityPlayer CommandBuffer name/function tables map that call at
   index 321 to `0x1801719B0`. The earlier `0x180149500` attribution was a
   table-index error: that address is a Profiler entry, not the tree-list
   internal call. The true tree body uses slot `0x1821BE708` twice for local
   managed-pointer root writes. Static initialization at
   `0x18077C050/0x18077C055` calls `0x1806898F0` with the string
   `il2cpp_gc_wbarrier_set_field` (`0x181D9E7F8`) and writes the result into
   that BSS slot, so it is not a renderer-list converter.
8. After the two GC-barrier calls, `0x1801719B0` forwards the local wrapper to
   `0x180A5C5C0`. That helper is shared by neighboring CommandBuffer draw
   entry points; its checked body calls `0x180769E20` (string-payload
   conversion/validation) and `0x18065C0C0`, returns a status, and emits only
   an error path on failure. It contains no visible ComputeBuffer, dispatch,
   graphics API, or command-stream opcode. This is a separate draw
   validation boundary, not a proven downstream step from the creation cores.
9. Therefore this pass closes the HGTree creation/resource-record boundary, the
   concrete `+0xEA0 -> 0x273B -> callback` command-stream boundary, and the
   callback-to-resource-pool ingress plus the separate CommandBuffer
   GC-root/validation boundary without claiming final GPU submission. The next
   bounded target is the consumer of the `0x1805592B0` resource nodes (and its
   backend/device handoff), not `0x1821BE708` and not the unrelated Profiler
   entry `0x180149500`.

10. A direct-code xref census against the pinned `UnityPlayer.dll` bounds this
    pool further: `0x1805582A0` has only three direct callers in executable
    `.pdata` functions—`0x1805583B0` and the two retry sites inside
    `0x1805592B0`; `0x1805592B0` itself is reached from `0x180559240`,
    `0x180559520`, and `0x180559590`. The node allocator only selects an index
    from the pool bitmap and returns `pool+8 + index*0x80`; the population path
    writes status/flags, descriptor data, linkage, and refcount fields, then
    invokes only resource callbacks/allocator helpers. No graphics-context
    vtable call, command opcode writer, ComputeBuffer/dispatch helper, or
    device-facing symbol appears in `0x1805592B0`/`0x180559520`'s direct call
    set. `0x180555D30` is a shared resource-list helper with 110 callers, so it
    cannot by itself identify a renderer submission edge. This narrows the
    unresolved sink to a later consumer of the populated 0x80-byte records (or
    a runtime-indirect callback), rather than another missing allocator xref.

11. The next callback edge is now bounded. The static resource callbacks do
    not submit directly, but their terminal record builders do install the
    renderer callbacks consumed later by the resource system:

    - `0x181065190` calls `0x18106BEF0`; its terminal continuation
      `0x18106BE69 -> 0x18107A410` stores callback `0x181060EA0`.
    - The sibling path through `0x18106C639 -> 0x1810795A0` stores callback
      `0x181060EB0`.
    - The alternate callback body `0x181067A70` calls `0x18106D020`; its
      continuations `0x18106CFA7 -> 0x18107A720` and
      `0x18106D769 -> 0x181079860` install the same `EA0/EB0` pair.

    Thunk `0x181060EA0` remaps its arguments and jumps to `0x18107AE60`;
    `0x181060EB0` does the same for `0x18107B3A0`. Both handlers first obtain
    the TLS graphics context through `0x180725DC0`, iterate the renderer
    record array, perform resource/material lookup, and invoke context vtable
    slots. The main handler uses `+0x210`, `+0x268`, `+0x280`, `+0xC8`,
    `+0xD8`, `+0xD0`, `+0xE0`, `+0xE8`, `+0xDA0`, and `+0x380`; the sibling
    handler uses the analogous `+0x210`, `+0x268`, `+0x280`, `+0xC8`,
    `+0xB0`, `+0xD8`, `+0xC0`, `+0xD0`, `+0xE0`, `+0xE8`, `+0xDA0`, and
    `+0x380` slots. This is the first concrete callback-built
    backend-facing boundary after the 0x80-byte resource nodes. The exact
    implementations of those context slots and their final device/API calls
    remain the next target; component 67 and the separate CommandBuffer
    validation path stay out of this chain.

12. The callback slots now resolve to the graphics-context backend selected by
    `0x18072F7E0`, rather than an unknown generic vtable. The context setup
    `0x180929430` passes the requested graphics API id to that selector and
    stores the returned object at `ctx+0x2708` in `0x180939C80`. For the
    non-`4` path (the initialization caller at `0x180730281` explicitly uses
    API id `2`), `0x180891210 -> 0x180829030` installs backend vtable
    `0x181DBC098`. Its callback-relevant entries are concrete:

    | context slot | backend target | bounded effect |
    | --- | ---: | --- |
    | `+0x210` | `0x1808539D0` | updates the backend state bit at `+0x2e48/+0xbc` |
    | `+0x268` | `0x1808547C0 -> 0x180842370` | records/updates resource state through the backend context |
    | `+0x280` | `0x180855200 -> 0x180842370` | same shared resource-state path with a different flag |
    | `+0xC8` | `0x180853A00` | stores the current handle at `+0x2e48/+0x80` |
    | `+0xD0` | `0x180854A30` | stores the current handle at `+0x2e48/+0x88` |
    | `+0xD8` | `0x180853F90` | stores the current handle at `+0x2e48/+0x90` |
    | `+0xE0` | `0x1808553B0` | stores handle/size state at `+0x2e48/+0x98/+0xc0` |
    | `+0xDA0` | `0x18083E720` | builds resource arrays and copies records via `0x18082F3C0`/`0x181C9F9A0` |
    | `+0x380` | `0x1808350E0 -> 0x18083E720` | alternate entry into the same resource-array builder |

    These functions mutate backend resource/state structures and counters;
    the inspected bodies still do not contain a direct D3D/Vulkan/Metal call
    or a final draw/dispatch submission. The API-id `4` selector instead
    returns `0x180925230`, whose vtable `0x181DCA338` leaves the callback
    slots above at the deliberate no-op `0x180076890`; this is an explicit
    backend variant, not evidence that the renderer callbacks themselves are
    device calls. The durable boundary is therefore now
    `HGTree callback -> graphics-context wrapper -> API-specific backend
    resource/state method`; final device submission remains unresolved.

13. The remaining API-2 slots on this route are now bounded as resource and
    descriptor plumbing rather than draw calls. Command-interpreter opcode
    `0x27B6` reaches context slot `+0x358` at `0x1813B92F8`, which dispatches
    to `0x1808351F0`. That method first enters `0x18083AA90`, allocates and
    fills descriptor/record arrays through `0x18082F3C0` and
    `0x181C9F9A0`, updates per-resource state through `0x1808558E0`, and
    calls `0x18086F1F0`/`0x180839D50` for arena/record bookkeeping. Its body
    has no direct graphics-device or draw/dispatch call.

    The sibling callback's extra slots are likewise registry paths:

    - `+0xB0 -> 0x180833470 -> 0x180822180`;
    - `+0xC0 -> 0x180833630 -> 0x1808224F0`.

    Both perform hash/page lookup and reference-counted record insertion, with
    constructor callbacks at `0x1808205C0` and `0x180820220`; neither exposes
    a device call. The shared `+0xDA0` target `0x18083E720` remains the same
    array/record builder. The nearby `+0xDE0 -> 0x18083D3B0` path creates
    0x44-byte resource descriptors and registers them through `0x18088B850`,
    also without a direct device call.

    One adjacent API-2 setup branch is a useful unresolved sink candidate but
    is not statically reached from the HGTree callback body: `+0xE90 ->
    0x180843BF0 -> 0x18083F680` initializes backend resource tables, and
    `0x18083F71B` invokes a runtime object vtable slot `+0x48`. The concrete
    object behind that call is not present in the file-backed vtable, so it is
    recorded as an indirect resource/device boundary rather than promoted to
    a draw/dispatch claim. The durable current boundary is therefore
    `HGTree callback -> API-2 resource/descriptor/registry methods`; the next
    proof target is the runtime object/queue consumer after those records, with
    API-4's deliberate no-op slots kept separate.

14. The `+E90` branch was caller-audited to keep this boundary from being
    over-promoted. Four file-backed call sites were found (`0x180624349`,
    `0x18093B129`, `0x18093B6BB`, and `0x1813AFEC3`); each passes temporary
    record/command data into `0x180843BF0`, which then enters the same
    `0x18083F680` resource-table initializer. No static caller of the API-2
    `+DC0` slot was found. In `0x18083F680`, the unresolved call is more
    specifically:

    ```text
    rdi = [r8+8]
    rsi = 0x18061FB00(rdi) = [[rdi+0x70]+8]
    rcx = [[rdi+0x78]+0x208]
    rdx = [rcx]                 ; runtime vtable
    rax = [rdx+0x48](rcx)        ; 0x18083F71B
    ```

    The surrounding code then calls `0x18083F8F0`, copies four resource
    records, and updates backend counters/arrays; neither that method nor the
    `0x18061FB00/0x18061FB40` accessors contains a graphics-device call. The
    `+0x48` receiver is therefore bounded as a runtime resource-subobject
    interface, not yet a D3D/Vulkan/Metal queue or draw submission. The next
    useful proof is to identify the heap-created vtable or its returned record
    consumer, rather than treating the slot number alone as device evidence.

15. A neighboring resource helper provides a stronger semantic bound for this
    slot. `0x18061FB60` loads a resource object's `+0x208` subobject, dispatches
    its vtable `+0x48`, then treats the return value as a NUL-terminated byte
    string (`0x18061FC23` scans until `byte == 0`) and copies it into a small
    diagnostic/metadata record. The helper has 28 direct callers, including
    the resource-descriptor assembly at `0x180624035`, `0x180624047`, and the
    repeated sibling sites through `0x1806242A9`. This is an independent
    resource-family witness, not a proof that the nested F680 receiver has the
    identical concrete type, but it makes a name/key accessor much more likely
    than a device method.

    In F680, the returned `rax` is saved only as the third stack argument to
    `0x18083F8F0`. The complete bounded body of F8F0 reads the first stack
    argument (`[rbp+0x80]`) but never reads `[rbp+0x88]` or `[rbp+0x90]`, the
    following two arguments. Thus this `+0x48` result is not consumed as a
    queue, command list, or graphics handle on this path. The durable
    interpretation is now `resource metadata/name preparation -> resource
    record builder`; device submission remains a separate unresolved path.

The component-67 evidence remains separate: its 24-byte records feed native
LOD/culling list construction, but no direct static xref from the accessor to
the managed HGTree wrapper or to the tree helper was established here.

## Reproduction

```bat
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --member-regex "$^" --body-target-regex "^(CreateRendererList|CreateRendererListWithPreZ|DrawECSRendererList)$" --body-target-type-regex "^UnityEngine\\.HyperGryph\\.HGTreeRender$" --all-images --include-all-members --body-context 1 --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_metadata_current.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\tree_render_native_map_current.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801D9D10 0x1801DA040
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107EE40 0x1810802A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180725DC0 0x180727EA0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18072F300 0x1807303C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1809324E0 0x180932780
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813AEE90 0x1813B12C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181060D00 0x18107AD80
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801719B0 0x180171A40
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A5C5C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18072F7E0 0x18072F810
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180829030 0x1808290A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083E720 0x18083EC40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180842370 0x180842650
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808351F0 0x180835EF0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180839D50 0x18083A0B0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808558E0 0x180855AA0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180843BF0 0x180843D40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083F680 0x18083F8F0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18061FB60 0x18061FD80
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180624000 0x1806242B0
```
