# HGTree renderer-list to CommandBuffer boundary

## Verdict

The installed build now pins the HGTree creation cores through their concrete
graphics-context and command-stream callback route. The dedicated HyperGryph
wrappers build renderer/resource records, resolve vtable `+0xEA0`, and emit
opcode `0x273B`; the interpreter dispatches that opcode to HGTree-specific
callbacks. The HGTree handlers then reach the API-2 `+0xDA0`/`+0x380`
resource/state wrappers. The neighboring `+0xDA8` callback has a real Vulkan
indirect-draw implementation, but its concrete producer is now separated: the
source-pinned `HGTerrainManager::RenderTerrain` command path, not a statically
proven HGTree handler. The HGTree `+0xDA0` path is now also closed through its
runtime list consumer to Vulkan buffer/state commands, while its indirect draw
ownership remains unproven. The managed CommandBuffer tree-list call has two
parallel UnityPlayer registrations in the pinned image. The table-A
implementation at `0x180064580` is the active global binding: it preserves the
renderer-list id and writes the high-level command record. The table-B
implementation at `0x1801719B0` is a duplicate validation-only body that
roots/hash-checks a managed payload. The static image does not expose the
runtime registration selector between these duplicate arrays. The maintained
UnityPlayer binding audit uses table A as the global active function array
(the same array maps the known `CullLights` binding to `0x1800FBCE0`); table B
is a parallel alternate/class-local implementation. Table A is therefore the
active command-writer path, while table B must not be used as its sink proof.
The later record loop is also pinned to Vulkan
`vkUpdateDescriptorSetWithTemplate` through a shared runtime slot, and the same
API-2 backend family has a concrete descriptor -> draw -> queue-submit sink.
The recorded HGTree receiver and its callback-produced resource/state records
are source-pinned, including the runtime list executor that invokes the
buffer/state callback thunks. Managed tree-list playback is now joined through
source-positive table-A command writer, high-level opcode `0x55`, and low-level
opcode `0x273B` direct callback dispatch. The API-2 `+0xEA8` callback queue is
an adjacent, separately decoded low-level case (`0x273C`), not part of the
HGTree `0x273B` edge. The asynchronous task's
renderer-record identity is also statically joined: its arg5 record becomes
task-descriptor `+0x68`, and the worker writes the callback/result pair back to
that same 0x30-byte record before the opcode-`0x55` fallback invokes it.
HGTree-specific indirect-draw selection, flush ordering, and queue submission
remain unresolved; this is not yet a retail frame-parity claim.

The generic flush boundary is now source-pinned as well: high-level opcode
`0x6A` is written by `0x1804CA0B0` and interpreted at `0x1804D178A`, where it
dispatches API-2 `+0xF10` (`0x18083F140`); low-level opcode `0x27D5` maps to
`0x1813B156A`, which dispatches the same slot. `+0xF10` closes pending
resource/state batches and enters `0x180841C40`; API-2 `+0xDE8`
(`0x18083F1E0`) also flushes and executes the master list through
`0x180843D60`. These are concrete command-stream flush/execute sinks, but the
inspected HGTree handlers still emit only `+0xDA0`/`+0x380`: no static HGTree
edge emits `0x6A`, `0x27D5`, `+0xF10`, `+0xDA8`, or `+0xDE8`. Therefore the
flush family is proven for the generic backend, while HGTree-specific ordering
and final draw/queue ownership remain fail-closed.

The complete UnityPlayer internal-call table fixes the command-buffer class
attribution used by this boundary. `ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected`
is index `3645` -> `0x1800B6F40 -> 0x18052D730 -> 0x1804CDF70 ->
0x1804CE0A0`, which is the positive high-level playback route. In contrast,
`Graphics::ExecuteCommandBuffer` is index `924` -> `0x18005C0D0`; its inspected
body is a separate resource/object path with no direct interpreter edge.
`Submit_Internal_Injected` is index `3636` -> `0x1800B4A40 -> 0x1805385A0 ->
0x18052E0B0`. Its type-2/type-3 deferred records reload command-buffer
pointers from `context+0x10128` and call the same interpreter, so Submit is a
concrete deferred consumer of the HGTree high-level buffer. It still does not
identify the HGTree API-2 draw owner.

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
   The wrapper is reached by `HGRendererListUtils.DrawTreeECSRendererList`
   (`0x189C0A130`), which loads `HGRenderGraphContext.cmd` from `+0x18` and
   forwards the renderer-list id in `edx`. The recovered source package
   `tools/FractalMiner/Assets/Project/EndField/HGRP/packages/com.hg.render-pipelines/runtime/HG/Rendering/Runtime/HGRendererListUtils.cs`
   shows the analogous `DrawECSRendererList` body forwarding
   `context.fields.cmd` and `ecsRendererList` to
   `UnityEngine::HyperGryph::HGMeshRender::DrawECSRendererList`; it contains
   no flush or queue-submit call of its own.
7. UnityPlayer contains two parallel function arrays for the same internal-call
   name table (`0x1820D3DB0`). At global index 3467 the table-A array
   (`0x1820CC000`) selects `0x180064580`; the parallel table-B array
   (`0x1820D9520`) selects `0x1801719B0`. Table A preserves `edx`, obtains the
   native command-buffer stream through `0x1804C7930`, and is therefore the
   active command-writer implementation. Table B ignores `edx`, uses
   the managed-root slot `0x1821BE708`, and enters the shared payload validator
   `0x180A5C5C0`. Keep B as a duplicate validation boundary, not as the
   renderer-list sink; the known global bindings establish table A as the
   active array, while table B remains an alternate duplicate.
8. Table-A `0x1804C7930` aligns the high-level stream cursor, writes dword
   opcode `0x55`, then writes the forwarded renderer-list id. The high-level
   interpreter `0x1804CE0A0` dispatches opcode `0x55` through table
   `0x1804D19C8` to `0x1804CE4BD`, which reads the id and calls
   `0x18106AAE0` with the global render context slot `+0xC0`.
9. `0x18106AAE0` validates the renderer-list index, builds the renderer-list
   state record, and calls the graphics context vtable `+0xEA0` with callback
   `0x181060D70 -> 0x18107AB10`. The concrete context implementation
   `0x1809324E0` records low-level opcode `0x273B`, callback pointer, size, and
   the record payload. Correct low-level-table indexing is `opcode - 0x2711`;
   `0x273B` lands at `0x1813B1110`, which parses the callback/record fields and
   calls the callback pointer stored in its parsed command state at
   `0x1813B12B0-0x1813B12B6`. It does not call API-2 `+0xEA8`.
10. The exact `0x18107AB10` body reached by `0x181060D70` is a resource/list lifetime
    callback: it calls `0x1806FCB10`, `0x180555A30`, `0x180555D30`,
    `0x180555E50`, `0x180555720`, `0x180FCE6F0`, and `0x180555A80`; the
    inspected `0x180FCE6F0` body performs resource refcount/cleanup work and
    contains no front-vtable slot or graphics command. The callbacks that
    actually reach front-end `+0xDA0`/`+0x380` are the resource-builder thunks
    `0x181060EA0 -> 0x18107AE60` and `0x181060EB0 -> 0x18107B3A0`, installed
    by `0x18106BEF0`/`0x18106D020`. Those handlers populate API-2
    resource/command records and bind-state callbacks, but this pass has not
    proven that this specific renderer-list record reaches the neighboring
    `+0xDA8` indirect-draw branch or the separate `+0xDE8` draw/submit sink.
11. Therefore this pass closes a positive managed-tree -> high-level opcode
    `0x55` -> low-level opcode `0x273B` -> direct HGTree callback route. The
    neighboring API-2 `+0xEA8` queue remains a separate low-level `0x273C`
    case, not a proven continuation of HGTree `0x273B`. The final
    renderer-list draw ownership and queue submission remain
    fail-closed; table B's validation body and the unrelated ordinary
    `Internal_DrawRendererList_Injected` route must not be substituted.

12. A direct-code xref census against the pinned `UnityPlayer.dll` bounds this
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

13. The next callback edge is now bounded. The static resource callbacks do
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
    slots. The TLS getter returns the front-end `0x2A00` context constructed
    by `0x1809258C0`, whose vtable is `0x181DCB360`; it does not return the
    API-specific backend directly. The main handler uses `+0x210`, `+0x268`,
    `+0x280`, `+0xC8`, `+0xD8`, `+0xD0`, `+0xE0`, `+0xE8`, `+0xDA0`, and
    `+0x380`; the sibling handler uses the analogous `+0x210`, `+0x268`,
    `+0x280`, `+0xC8`, `+0xB0`, `+0xD8`, `+0xC0`, `+0xD0`, `+0xE0`,
    `+0xE8`, `+0xDA0`, and `+0x380` front-end slots. This is the first
    concrete callback-built front-end boundary after the 0x80-byte resource
    nodes. The exact front-end-to-backend dispatch and final device/API calls
    remain the next target; component 67 and the separate CommandBuffer
    validation path stay out of this chain.

14. The front-end/backend layering is now explicit. Setup
    `0x18072F3EB -> 0x180929430 -> 0x1809258C0` constructs the front-end
    context and `0x1807303B5 -> 0x180727EA0` stores that same pointer in the
    TLS slot read by `0x180725DC0`. The front-end stores the API-selected
    backend at `context+0x2708` (`0x180939C80`); for the initialization path
    that passes API id `2`, `0x180891210 -> 0x180829030` installs backend
    vtable `0x181DBC098`. The handler's resource slots are wrappers, not
    direct API-2 calls. In particular:

    | front-end slot | front-end wrapper | immediate (non-recording) backend dispatch |
    | --- | ---: | ---: |
    | `+0xDA0` | `0x180931980` | `context+0x2708` `+0xDA0 -> 0x18083E720` |
    | `+0x380` | `0x18092C320` | `context+0x2708` `+0x380 -> 0x1808350E0` |

    With recording enabled, `0x180931980` writes opcode `0x2734` and
    `0x18092C320` writes opcode `0x27B6`; with recording disabled, both
    wrappers tail-dispatch through the backend pointer. The other state/handle
    slots follow the same front-end-wrapper shape. The API-2 backend entries
    used after that dispatch are:

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

    These backend functions mutate resource/state structures and counters; the
    inspected bodies still do not contain a direct D3D/Vulkan/Metal call or a
    final draw/dispatch submission. The API-id `4` selector instead returns
    `0x180925230`, whose backend vtable `0x181DCA338` leaves the corresponding
    backend callback slots at the deliberate no-op `0x180076890`; this is an
    explicit backend variant, not evidence that the front-end wrappers
    themselves are device calls. The durable boundary is therefore now
    `HGTree callback -> front-end wrapper -> API-specific backend
    resource/state method`; a concrete draw/queue-submit sink is proven in the
    same API-2 family, but its HGTree-specific receiver/branch ownership
    remains unresolved.

15. The remaining API-2 slots on this route are now bounded as resource and
    descriptor plumbing rather than draw calls. Front-end recording opcode
    `0x27B6` is interpreted by `0x1813B92F8`, whose receiver's backend slot
    `+0x358` dispatches to `0x1808351F0`. That method first enters `0x18083AA90`, allocates and
    fills descriptor/record arrays through `0x18082F3C0` and
    `0x181C9F9A0`, updates per-resource state through `0x1808558E0`, and
    calls `0x18086F1F0`/`0x180839D50` for arena/record bookkeeping. Its body
    has no direct graphics-device or draw/dispatch call.

    The sibling callback's extra front-end slots are likewise registry paths
    that tail-dispatch to the API-specific backend when recording is disabled:

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
    `HGTree callback -> API-2 resource/descriptor/registry methods`; item 17
    proves the backend's concrete draw/queue-submit sink, while the next proof
    target is the runtime receiver/branch that connects these records to that
    sink. Keep API-4's deliberate no-op slots separate.

16. The `+E90` branch was caller-audited to keep this boundary from being
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

17. A neighboring resource helper provides a stronger semantic bound for this
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
    record builder`; the later record loop is a separate backend descriptor
    update path, not a consumer of this returned metadata value.

18. The post-F8F0 indirect at `0x18083F89D` is a shared runtime dispatch cell,
    not an opaque per-object graphics call. Its RIP slot is
    `0x1821D3898`, and the same cell is referenced by 28 resource/record call
    sites, including `0x180823FF5`, `0x180839E83`, `0x180840EBA`,
    `0x1808464F0`, and `0x1808467B4`. A file-backed registration at
    `0x180848A8A` assigns `0x180861C20`, whose bounded body is:

    ```text
    mov r8, [r8+8]
    lea rcx, [rdx+8]
    shl r8, 5
    mov rdx, r9
    jmp 0x181C9F9A0
    ```

    That initializer is a generic `count * 0x20` record-copy helper, not a
    device call. However, the same cell is populated by the Vulkan symbol
    resolver at `0x18085127C`/`0x1808512A7`/`0x1808512CB`/`0x1808512F0`;
    each branch passes the file-backed string
    `vkUpdateDescriptorSetWithTemplate` and stores the resolved address into
    `0x1821D3898`. The call-site register shape is consistent with the Vulkan
    ABI (`device`, descriptor-set handle from `0x180839B00`, update-template
    handle, and a byte-offset-adjusted data pointer). Therefore the bounded
    post-record operation is now promoted to a concrete Vulkan descriptor
    update, while the earlier static copy assignment remains an initialization
    fallback.

19. The same API-2 vtable contains a concrete backend draw and submit sink.
    At base `0x181DBC098`, the relevant entries are
    `+0xDC0 -> 0x18083F680`, `+0xDE8 -> 0x18083F1E0`, and
    `+0xE90 -> 0x180843BF0`. The native interpreter region that contains the
    audited `+E90` caller (`0x1813AFEC3`) has an adjacent sibling case at
    `0x1813AFED9` dispatching the same receiver's `+0xDE8` slot. The `+0xDE8`
    target `0x18083F1E0` calls `0x180843D60`; inside that method:

    ```text
    0x1808445A6 -> 0x18083C6B0
    0x18083D316  vkUpdateDescriptorSetWithTemplate
    0x18083D329  vkCmdBindPipeline
    0x18083D35D  vkCmdBindDescriptorSets
    0x18083D37A  vkCmdDraw
    0x180844A09  vkQueueSubmit
    0x180844BD3  vkQueueSubmit (alternate branch)
    ```

    The draw register/stack setup matches Vulkan exactly: command buffer
    `[rdi+0x28]`, graphics bind point `0`, pipeline `[rbx+0x2FF8]`, layout
    `[rbx+0x2FF0]`, one descriptor set, and `vkCmdDraw(3, 1, 0, 0)`. The
    submit branches pass queue `[rdi+0x2BC8]`, submit count `1`, a submit-info
    record at `[rbp+0x170]`, and the fence at `[[rdi+0x2E28]+8]`. This is now
    positive proof of the backend's descriptor -> draw -> queue-submit path.
    The `+DE8` sibling is not proven to be an unconditional successor of the
    HGTree `+E90` case, so the remaining gap is receiver/branch ownership, not
    the existence of the concrete Vulkan sink.

20. The interpreter cases now have an exact command-stream producer boundary.
    The dispatch table at `0x1813BB574` uses `opcode - 0x2711` as its index:
    `0x2730 -> 0x1813AFB6B`, `0x2731 -> 0x1813AFECF`, and
    `0x273B -> 0x1813B1110`. Case `0x2730` parses the variable-size record
    payload and calls the receiver at `[r14+0x70]` through vtable `+0xE90` at
    `0x1813AFEC3`; its common-exit jump is at `0x1813AFECA`. The adjacent
    case `0x2731` calls the same receiver through `+0xDE8` at
    `0x1813AFED9` and exits at `0x1813AFEDF`. These are adjacent jump-table
    cases, not a fall-through from `+E90` into `+DE8`.

    Their native writers share the same command-buffer object layout and the
    same recorder flag (`byte [object+0x2711]`). Writer `0x18093AE10` stores
    literal opcode `0x2730` at `0x18093AEB5` and, when recording is disabled,
    immediately dispatches the same receiver through `+0xE90` at
    `0x18093B129`. Writer `0x18092E350` stores literal opcode `0x2731` at
    `0x18092E40F` and, on its immediate path, dispatches through `+0xDE8` at
    `0x18092E450`. This proves that the descriptor/resource operation and the
    draw/submit operation are separate recorded opcodes in the same native
    command architecture. It does not yet prove that every HGTree renderer
    list emits `0x2730` followed by `0x2731`, so the receiver/branch ownership
    and runtime ordering remain fail-closed. A pinned instruction census over
    the normal HGTree creation core and both callback handlers finds no
    indirect `+0x2A0` or `+0x3E8` call at all; those HGTree bodies instead use
    front-end `+0xEA0`, `+0xDA0`, and `+0x380` (recording `0x273B`, `0x2734`,
    and `0x27B6`). Thus `0x2730 -> 0x2731` is a separate native command-family
    candidate, not a recovered HGTree renderer-list order.

21. The command-stream receiver is now pinned to the API-2 backend. The
    backend/context creation path `0x180929430` calls `0x1809258C0` to create
    the front-end context, obtains the selected backend from
    `0x18072F7E0`, and at `0x180929540` writes that same pointer to
    `[context+0x2700]+0x70` (the command-stream state receiver). The attach
    call immediately following it, `0x180939C80`, stores the pointer at
    `context+0x2708`; API id `2` gives that backend vtable
    `0x181DBC098`. Thus the receiver read by `0x1813AEE90` is not a second
    opaque object: it is the selected API-2 backend shared by immediate and
    recorded paths.

    A vtable cross-check keeps the writer and backend identities separate.
    The data table at `0x181DCB600` contains `0x18093AE10` at slot `+0x0`
    and `0x18092E350` at slot `+0x148`; those are the two front/command-writer
    methods that produce `0x2730`/`0x2731` and use the shared object fields
    (`+0x2711`, `+0x2720`, `+0x2708`). The constructor at `0x1809258C0`
    installs a different front-context table (`0x181DCB360`), whose `+0x148`
    entry is `0x180728720`, while the API-2 backend table
    `0x181DBC098 + 0xDE8` resolves to `0x18083F1E0`. Therefore
    `0x18092E350`/`0x18093AE10` are command writers that immediately dispatch
    into the backend's `+0xDE8`/`+0xE90`; they are not the backend draw/submit
    implementations themselves. This removes a class/vtable conflation but
    does not create an HGTree-specific writer edge.

    The recorded HGTree wrapper opcodes now have concrete interpreter
    consumers. The `0x27B6` case begins at `0x1813B92D0` and calls the
    receiver's `+0x358` slot at `0x1813B92F8` (`0x1808351F0`). The `0x2734`
    case begins at `0x1813AFFF7` and calls the same receiver's `+0xDA0` slot
    at `0x1813B03DA` (`0x18083E720`). These are the exact recorded counterparts
    of front-end `+0x380`/`+0xDA0`; the immediate branches already tail-dispatch
    those slots directly. This closes front-end wrapper -> command record ->
    API-2 backend receiver for both HGTree resource paths. It still does not
    prove that either resource operation schedules the adjacent `+0xDE8`
    draw/submit case; that branch/order ownership remains fail-closed.

22. The managed draw edge is corrected by the duplicate-table audit above.
    The six render callbacks remain valid callers of
    `HGRendererListUtils.DrawTreeECSRendererList`, but the old attribution of
    the name to `0x1801719B0` was incomplete: active table A's `0x180064580` preserves
    the id and writes opcode `0x55`, while table B's `0x1801719B0` is only the
    managed-root/hash validator. Do not report B as the active sink; table B
    is only the alternate validation implementation.
23. The complete UnityPlayer internal-call table corrects the class attribution
    at the playback boundary. `ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected`
    is index `3645` -> `0x1800B6F40 -> 0x18052D730 -> 0x1804CDF70 ->
    0x1804CE0A0`; the table-A tree writer joins this interpreter at opcode
    `0x55`. `UnityEngine.Graphics::ExecuteCommandBuffer` is index `924` ->
    `0x18005C0D0`; the inspected body resolves resource/object handles and has
    no direct interpreter edge. `Submit_Internal_Injected` is index `3636` ->
    `0x1800B4A40 -> 0x1805385A0 -> 0x18052E0B0`; its type-2/type-3 records
    reload deferred command-buffer pointers and call the same interpreter.
    The async/no-copy entries use distinct helpers, so Submit is a concrete
    deferred consumer but still does not prove the HGTree API-2 draw or queue
    owner.
24. The ordinary `Internal_DrawRendererList_Injected` route is still distinct:
    table-A index 3463 resolves to `0x180062960`, while table-B's parallel
    implementation is `0x1801713D0`. Its resource-state helper must not be
    substituted for the tree-list route. The exact active table selector for
    table A is the active global binding; table B is the alternate duplicate.
25. The table-B body at `0x1801719B0` still uses
    `0x1821BE708 -> 0x180A5C5C0 -> 0x180769E20 -> 0x18065C0C0` for managed
    payload normalization and CRC/hash validation. This explains why the
    earlier static scan saw no opcode, but it no longer bounds the complete
    tree route: the source-positive table-A body records opcode `0x55`.
26. The remaining HGTree sink question is now after the positive chain:
    `DrawTreeECSRendererList -> 0x180064580 -> 0x1804C7930 -> 0x55 ->
    0x18106AAE0 -> 0x1809324E0 -> 0x273B -> 0x1813B1110 ->
    0x181060D70 -> 0x18107AB10`. The last callback is the resource/list lifetime boundary;
    it does not statically dispatch front-end `+0xDA0`/`+0x380`. Those slots
    are reached by the separately installed resource callbacks
    `0x181060EA0/0x181060EB0 -> 0x18107AE60/0x18107B3A0`, whose API-2 records
    are then consumed by the backend resource-list executor. This pass has
    not joined either branch to `+0xDA8` indirect draw or `+0xDE8`
    descriptor/draw/queue-submit. Keep the final renderer-list draw and queue
    ownership fail-closed.

27. The main-table no-copy entries are `0x1800B7440` -> `0x18052DB50` and
    `0x1800B7AD0` -> `0x18052DA20`; the former's ready branch directly calls
    `0x1804CDF70`, while the latter queues a distinct record helper. These are
    command-buffer variants, not the previously cited `0x180158...` state
    wrappers. They still contain no static HGTree API-2 `+0xDE8` draw/submit
    ownership proof. The API-2 resource pool has the same negative shape.
    `0x180559B30` walks bitmap-selected `0x80`-byte nodes and decrements their
    refcounts; zero-ref nodes enter `0x1805598C0`, which invokes node callbacks
    stored at `+0x30`/`+0x40`, clears record fields, and returns through
    `0x1805586C0`. `0x1805586C0` is an owner/resource lifetime collector
    (atomic counts, bitmap cleanup, and `0x18055AD70` release), not a direct
    graphics or command-stream sink. An indirect callback could still hide a
    runtime consumer, so this is a bounded fail-closed result rather than a
    claim that the pool is unrelated.

28. The resource-callback branch is now closed through the shared API-2 record
    builder, but still not through the final draw sink. Both native HGTree
    callback handlers (`0x18107AE60` and `0x18107B3A0`) resolve the TLS context
    vtable and dispatch either `+0xDA0` or `+0x380`. In the pinned API-2 vtable
    at `0x181DBC098`, those slots are `0x18083E720` and `0x1808350E0`;
    `0x1808350E0` is a thin payload wrapper that calls `0x18083E720` directly
    (`0x18083513E`). The shared builder allocates/links the `0x60`-byte records
    and calls `0x180839D50`; its downstream record consumer
    `0x18083AA90` contains only direct allocation, copy, and state-list work,
    with no static API-2 `+0xDE8`, Vulkan, or queue-submit call. The recorded
    `0x27B6` route remains separate: its interpreter case dispatches backend
    `+0x358` (`0x1808351F0`), whose inspected body likewise stays in record and
    resource state machinery. The positive API-2 submission family remains
    independently bounded as `+0xDE8 -> 0x18083F1E0 -> 0x180843D60` and the
    previously identified Vulkan descriptor/draw/queue operations, but no
    static edge from either HGTree callback branch or the shared record
    consumer reaches it. Keep the HGTree playback edge fail-closed until the
    runtime-indirect record consumer or a capture binds these families.

29. The 0x60-byte records created on the resource path now have bounded
    callback thunks, and their runtime slots are resolved to named Vulkan
    commands. The `+0xDA0` builder `0x18083E720` stores callback `0x180820580`
    at `0x18083EA2A`; that thunk jumps to `0x18082D6B0`, which compares
    resource handles, then calls `0x1821D35A0 = vkCmdBindIndexBuffer` and
    `0x1821D35A8 = vkCmdBindVertexBuffers`. The shared builder path
    `0x180839D50` stores callback `0x1808208F0` at `0x18083A033`; it jumps to
    `0x18082E660`, whose state-delta path calls
    `0x1821D3568 = vkCmdSetDepthBias`,
    `0x1821D3590 = vkCmdSetStencilReference`,
    `0x1821D3548 = vkCmdBindPipeline`, and
    `0x1821D3598 = vkCmdBindDescriptorSets`. The `+0xDA8` sibling
    `0x18083EC60` stores callback `0x180820940` at `0x18083F0F7`; it jumps to
    `0x18082E820`, binds index/vertex buffers through the same `35A0/35A8`
    slots, and selects `0x1821D35C8 = vkCmdDrawIndexedIndirect` or
    `0x1821D35C0 = vkCmdDrawIndirect` at its final branch. These are direct
    Vulkan command-recording calls, not merely resource-state copies. The
    ownership boundary is now explicit: a direct-code scan finds only four
    `+0xDA8` call sites (`0x1804D2A32`, `0x1804D492D`, `0x180932246`, and
    `0x1813B0580`); neither native HGTree callback handler contains one. The
    `+0xDA8` implementation therefore remains a neighboring render-family
    control path until a runtime record join proves an HGTree producer.

30. The indirect-slot names are source-pinned by Unity's Vulkan resolver
    `0x180746620`, which passes each symbol string to `0x181CA0480` and stores
    the resolved function pointer in the corresponding BSS cell. The resolver
    maps `0x1821D3548/3568/3590/3598/35A0/35A8/35C0/35C8` to
    `vkCmdBindPipeline`, `vkCmdSetDepthBias`, `vkCmdSetStencilReference`,
    `vkCmdBindDescriptorSets`, `vkCmdBindIndexBuffer`,
    `vkCmdBindVertexBuffers`, `vkCmdDrawIndirect`, and
    `vkCmdDrawIndexedIndirect`. This closes the previously unresolved
    callback receiver identity without treating the file-backed BSS contents as
    initialized pointers. Re-run
    `python scratch\\reverse_engineering\\hgtree_component67_producers\\resolve_vulkan_function_slots.py`
    against the pinned UnityPlayer to reproduce the mapping.

31. The neighboring indirect-draw control path is now source-identified rather
    than inferred from slot proximity. HyperGryph table index 503 names
    `HGTerrainManager::RenderTerrain` and maps to `0x1801F4D40`; its wrapper
    calls `0x1811DDC50` (`0x1801F4DB3`), which writes a high-level `0x60`
    callback record containing `0x1811A5BD0`. The high-level interpreter
    `0x1804CE0A0` uses table `0x1804D19C8`; case `0x60` begins at
    `0x1804CECEF`, extracts the recorded callback through
    `call qword [base+r10]`, and invokes it. `0x1811A5BD0` forwards to
    `0x1811AB1B0`; that function records `+0xEA0` at `0x1811AB110` and then
    enters pass executor `0x1811D03A0` at `0x1811AB7A8`. Its branch at
    `0x1811D0671` calls `0x1804D4680`, whose API-2/front-end branches are
    `+0xDA8` (`0x1804D492C`) or `+0x390` (`0x1804D4961`), reaching the named
    Vulkan indirect-draw thunks above. This is a complete Terrain render
    producer/consumer witness for the generic command framework; it is not an
    HGTree ownership proof because the HGTree `0x273B` records use distinct
    callbacks (`0x181060D90/0x181060D20/0x181060D00`) and their handlers still
    dispatch only `+0xDA0`/`+0x380`. Keep the HGTree draw edge fail-closed.

32. The backend resource/state callback list now has a positive runtime
    consumer. `0x18083E720` and its shared builder `0x180839D50` append
    `0x180820580` and `0x1808208F0` records to the API-2 list at
    `context+0x2B60`; `0x180841C40` wraps that list in a master-list node at
    `context+0x2B50` and installs callback `0x1808200C0`. The `+0xDE8`
    backend executor `0x180843D60` consumes the master list at
    `0x180843F04-0x180843F21`, calling each node's callback. The
    `0x1808200C0` callback then walks the `+0x2B60` records at
    `0x1808200C0-0x1808200F0` and invokes their stored callbacks. When this
    list is flushed, the records created by the HGTree `+0xDA0` family reach
    `0x18082D6B0` (index/vertex-buffer binds) and `0x18082E660`
    (depth/stencil/pipeline/descriptor state) through the named Vulkan
    resolver slots. This proves the runtime callback executor and Vulkan
    command recording for the API-2 resource/state family, but the static
    image still does not prove HGTree-specific flush/order, selection of the
    neighboring `+0xDA8` indirect draw, or ownership of the `+0xDE8`
    queue-submit branch; keep final draw/submit ownership fail-closed.

33. The command-stream flush family is now bounded independently of the HGTree
    producer. High-level writer `0x1804CA0B0` emits opcode `0x6A`; interpreter
    table `0x1804D19C8` maps that entry to `0x1804D178A`, which calls API-2
    `+0xF10` (`0x18083F140`). The low-level table `0x1813BB574` maps opcode
    `0x27D5` to `0x1813B156A`, which calls the same `+0xF10` slot. The
    implementation finalizes the pending resource/state records, invokes
    `0x180841C40`, and clears the corresponding batch heads. API-2 `+0xDE8`
    (`0x18083F1E0`) is a second explicit flush-and-execute sink: it calls
    `0x180841C40` and then consumes the master list through `0x180843D60`.
    Direct `0x6A` writers are found in generic pass/resource functions
    (`0x181118AD0`, `0x18111A7D7`, `0x1811BE9BA`, `0x1811C7FFD`), while no
    static HGTree handler or callback emits `0x6A`, `0x27D5`, `+0xF10`,
    `+0xDA8`, or `+0xDE8`. This closes the generic flush/execute boundary but
    not its HGTree-specific ordering or final draw/queue ownership; keep that
    final edge fail-closed.

34. A complete callback-side front-vtable census narrows the remaining
    receiver boundary. Main handler `0x18107AE60` calls slots `+0x210`,
    `+0x268`, `+0x280`, `+0xC8`, `+0xD8`, `+0xD0`, `+0xE0`, `+0xE8`,
    `+0xDA0`, and `+0x380`; sibling `0x18107B3A0` additionally calls
    `+0xB0`/`+0xC0`. API-2 maps those extra slots through
    `0x180833470`/`0x180833630` to `0x180822180`/`0x1808224F0` registry
    paths, while the other inspected slots are resource/handle/state
    mutations. None of these callback bodies emits `+0xDA8`, `+0xDE8`, or
    `+0xF10`, and the inspected bodies contain no direct Vulkan draw. The
    generic low-level writer `0x18092E350` records `0x2730` then `0x2731`;
    interpreter case `0x2731` (`0x1813AFED9`) dispatches `+0xDE8`, paired with
    `0x18093AE10`'s `0x2730`/`+0xE90` path. This identifies a separate
    render-pass/command family in the static image rather than an HGTree
    callback edge. The managed `HGRendererListUtils.DrawTreeECSRendererList`
    wrapper (`0x189C0A130 -> 0x18B3FBFA4`) also contains no flush writer.
    Keep HGTree ordering, final draw, and queue ownership fail-closed.

35. The callback identities are now explicitly separated. High-level opcode
    `0x55` queues `0x181060D70 -> 0x18107AB10`, whose body is limited to
    resource/list lifetime helpers and does not emit `+0xDA0`, `+0x380`,
    `+0xDA8`, `+0xDE8`, `+0xF10`, or a direct graphics call. The front-end
    resource/state callbacks are instead `0x181060EA0/0x181060EB0 ->
    0x18107AE60/0x18107B3A0`, installed by the resource builders. This
    correction tightens the fail-closed boundary: the positive tree command
    route reaches a lifecycle/resource callback, while the later resource
    callback-to-state path is a distinct runtime edge; neither proves
    HGTree-specific indirect draw ordering or queue submission.

36. The adjacent generic mesh-list wrappers are now mapped separately from
    the tree-list wrapper. Metadata/body mapping pins
    `HGMeshRender.DrawECSMeshRendererListWithSRPRendererList` to GameAssembly
    `0x18B3FA1F8`; its body forwards the ECS id and copied SRP `RendererList`
    to `CommandBuffer::AddDrawECSMeshRendererListWithSRPRendererList_Injected`
    through `0x18B3E3F44`. `HGMeshRender.DrawECSRendererList` is the sibling
    wrapper at `0x18B3FA224`, which enters the resolved
    `CommandBuffer::AddDrawECSMeshRendererList` path at `0x18B3E3FA8`.
    These wrappers only record the corresponding mesh/ECS command and contain
    no flush, `+0xF10`, `+0xDE8`, or queue-submit edge. They are useful positive
    CommandBuffer witnesses for the ordinary HGMesh family, but they do not
    join the HGTree `0x55 -> 0x273B` callback route or prove HGTree final-draw
    ownership.

37. The resource-pool callback identity is now bounded on the actual table-A
    HGTree ingress rather than left entirely indirect. The exact path is
    `0x18107AB10 -> 0x180555D30 -> 0x1805573D0 -> 0x180559520 ->
    0x1805592B0`. `0x1805573D0` supplies a callback tuple containing
    `0x180557650` and `0x180557750`; `0x1805592B0` copies that tuple into the
    node's `+0x30..+0x40` fields. Recycle/cleanup `0x1805598C0` invokes the
    stored node callback. On this ingress `0x180557650` is only a contained-
    object cleanup dispatcher and `0x180557750` is a field setter; neither
    contains a front-vtable slot, command opcode, Vulkan call, draw, or queue
    submission. This closes the AB10-to-pool-node callback identity for this
    ingress. It does not classify unrelated producers of the shared pool, so
    other node contexts remain fail-closed.

38. A second, distinct producer now closes the shared pool's callback-
    production edge. The normal/child/PreZ result builders call
    `0x181080730`, which copies the caller's two output slots into the new
    record at `+0x58/+0x60` and registers that record through
    `0x180555D30`. Depending on the record state, `0x181080730` stores
    `0x181065190` or `0x181067A70` as the node callback. Pool worker/dequeue
    call sites (including `0x180558463` and `0x180558A80`) reach
    `0x1805598C0`, whose normal node branch invokes the stored `+0x30`
    callback. The selected callback then calls `0x18106BEF0` or
    `0x18106D020`; those builders call `0x18107A410`/`0x181079860` for the
    resource result and write the output pair as `outResult+8 = result` and
    `outResult+0x10 = 0x181060EA0`/`0x181060EB0`. This is a positive
    producer-to-resource-callback edge, separate from the table-A
    `0x18107AB10` lifecycle ingress and its allocator tuple. It still does
    not statically prove HGTree-specific draw ordering, final indirect-draw
    ownership, or queue submission after the generated callback record.

39. The managed caller census now places the Tree command inside six concrete
    render-pass lambdas: `HGPunctualLightShadowManager`,
    `GBufferPassConstructor`, both `OnePassDeferredPassConstructor` branches,
    `HGShadowManager`, and `HGASMManager`. Each calls
    `HGRendererListUtils.DrawTreeECSRendererList` alongside ordinary renderer,
    ECS, and grass-list helpers. The GBuffer branches also issue the separate
    `CommandBuffer.Add_GPUDriven_DrawRendererList` path; it is not a Tree
    callback. `HGASMManager` has a
    `ScriptableRenderContext.ExecuteCommandBufferNoCopy` call before its
    renderer-list sequence, not a Tree-specific post-call flush. None of the
    six caller bodies has a direct edge to API-2 `+0xDA8`, `+0xDE8`, or
    `+0xF10`. This is positive pass-context evidence for Tree playback, while
    final render-graph/command-buffer execution and HGTree-specific draw/queue
    ownership remain external to these callbacks and fail-closed.

40. A focused consumer pass separates the callback pair produced by the
    resource builders from the pool node callback. `0x18106BEF0` and
    `0x18106D020` write `outResult+8` to the resource result returned by
    `0x18107A410`/`0x181079860`, and `outResult+0x10` to
    `0x181060EA0`/`0x181060EB0`; their callers pass that `outResult` through
    the per-record `+0x10` slot. The shared record initializer
    `0x181080730` instead copies its input pair into a new 0x98-byte record
    (`+0x58/+0x60`) and registers it via `0x180555D30`.
    `0x180555D30 -> 0x1805573D0 -> 0x180559520 -> 0x1805592B0` allocates an
    0x80-byte pool node; the pool worker `0x1805598C0` invokes the node's
    stored `+0x30` callback (`0x181065190` or `0x181067A70`), which rebuilds
    the resource result and re-emits the builder pair. No direct static
    read from the builder's `outResult+0x10` reaches API-2 `+0xDA8`,
    `+0xDE8`, `+0xF10`, Vulkan, or queue submission. The exact runtime
    consumer that turns this callback-produced resource pair into the final
    HGTree draw remains unresolved; keep the boundary fail-closed.

41. The handler-side field census closes the next tempting shortcut. The
    thunks `0x181060EA0` and `0x181060EB0` only rearrange arguments and tail-jump
    to `0x18107AE60`/`0x18107B3A0`; they do not invoke the builder pair's
    `+0x10` slot themselves.
    Inside both handlers, `rdx` is the result object itself: `[result]` is the
    item-array pointer and `[result+8]` is the item count. The handlers walk
    those records (0x60-byte stride), prepare front-end resource state, and
    dispatch only `+0xDA0`/`+0x380`. A bounded indirect-call scan over
    `0x181060000-0x181090000` found no statically joined builder-pair `+0x10`
    consumer; the matching calls are renderer-list fallback/cleanup branches
    in `0x18106AAE0` and its siblings. The
    pool worker `0x1805598C0` likewise invokes the node's `+0x30` callback
    (`0x181065190`/`0x181067A70`), not the builder pair. Targeted generic API2
    candidates are ordinary interface/resource-state vtable calls and do not
    match this result-pair shape. No new static edge reaches `+0xDA8`,
    `+0xDE8`, `+0xF10`, Vulkan, or queue submission; the runtime consumer that
    joins the resource pair to the final HGTree draw remains unresolved.

42. A broader exact indirect-call census does not uncover a hidden result-pair
    executor. Scanning the UnityPlayer `.text` for direct `call qword ptr
    [register+0x10]` sites and filtering API-2/resource ranges yields 40
    candidates. The four sites in the HGTree-adjacent `0x18106AAE0` cleanup
    family (`0x18106AAC6`, `0x18106AC96`, `0x18106AE54`, `0x18106B014`) all
    load an object from `[rsi+0x10]`, pass its `[object+8]` context, and invoke
    `[object+0x10]`; they are real renderer-list/resource fallback callbacks,
    but are not proven to consume the builder `outResult+0x10` slot. The analogous `0x18109EC12`/
    `0x18109EDDD` sites are the same per-slot cleanup pattern. The remaining
    `0x18082*`/`0x18084*`/`0x18085*`/`0x18086*` candidates are ordinary vtable
    release/destructor or container cleanup calls (their call target is loaded
    from a vtable object first), with no `rcx=outResult`, result-object item
    walk, API-2 `+0xDA8`/`+0xDE8`/`+0xF10`, Vulkan, or queue edge. Separately,
    `0x1805594BD` in `0x1805592B0` invokes a caller-supplied allocator control
    pair (`rdi` from the incoming control record) with a pool index; the node
    result is `rsi` and is not that pair. The `0x1810685A0` resource handler's
    direct-call census likewise contains only resource/registry work and
    indirect `+0xB0`/`+0xC0` interface slots. Keep the result-pair-to-final-draw
    join unresolved and fail-closed.

43. The producer side of that boundary is now positively joined to the async
    pool. `.pdata` identifies `0x181065190` and `0x181067A70` as the two worker
    callback entries installed by `0x181080730` through `0x180555D30`.
    Their bodies call the paired builders `0x18106BEF0` and `0x18106D020`
    with output slots `[context+0x58]` and `[context+0x60]`; those builders
    write the generated item array at `outResult+8` and the completion thunks
    `0x181060EA0`/`0x181060EB0` at `outResult+0x10`. The same initializer writes
    the completion flag at `context+0x68`, and the pool worker invokes the
    callback with `context` from the node's `+0x28` field. This closes
    `HGTree/resource record -> 0x98-byte async context -> pool node -> builder`
    on the producer side, but the post-callback consumer is still not a draw
    proof. A global short-window scan for `mov reg,[pair+0x10]` followed by
    `call reg` finds only five unrelated families: the XR audio-driver table
    around `0x180F150C0` (table at `0x181E17288`), a refcount notifier at
    `0x181AF9ECF`, and tagged generic operations at `0x181BBA56F`/
    `0x181BBA9FD`; none references the HGTree handlers, API-2 `+0xDA0`/
    `+0xDA8`/`+0xDE8`/`+0xF10`, Vulkan, or queue submission. Keep the
    post-callback result-pair-to-draw edge unresolved and fail-closed.

44. A second async resource-task route now explains how the result thunk can
    be regenerated after an upstream dependency. `0x18107E2E0` selects the
    callback at `0x181065FD0` (the non-empty dependency branch at
    `0x18107E492`) and queues it through `0x180555D30`. That callback calls
    `0x18106B5B0` (`0x181066E10`); the latter invokes `0x18107A410`, writes the
    generated result count at `result+8`, and stores the continuation pair at
    `continuation+8` with `0x181060EA0` at `continuation+0x10`
    (`0x18106BE8B`). This is a positive producer-to-continuation join, distinct
    from the initial `0x181080730 -> 0x181065190/0x181067A70` route.
    The pool path still remains generic: `0x1805598C0` invokes the node worker
    callback at `node+0x30`, optionally calls the scheduler setter at
    `node+0x40`, and then `0x1805586C0` retires the node. The helper tuple
    (`0x180555720`, `0x180557650`, `0x180557750`) wraps caller-supplied
    continuation state; no static call of the stored `0x181060EA0` reaches
    `0x18107AE60`, API-2 `+0xDA0/+0xDE8/+0xF10`, Vulkan, or queue submission.
    Therefore the continuation-object-to-HGTree-handler edge remains
    unresolved and fail-closed, while this task route is now the highest-value
    runtime probe target.

45. The continuation route is now bounded across all three worker selections,
    with their producer implementations separated. `0x18107E2E0` queues
    `0x181065FD0`, `0x181066F40`, or `0x181064100` (selected at
    `0x18107E492/0x18107E49F/0x18107E4A6`) through the same `0x180555D30`
    pool wrapper; each worker builds a resource/record result and its caller
    copies the returned pair into a record's `+0x20`.

    - The non-empty dependency branch `0x181065FD0` calls `0x18106B5B0`,
      whose `0x181066E10` path invokes `0x18107A410` and stores
      `0x181060EA0` at the continuation pair's `+0x10`
      (`0x18106BE8B`).
    - The other two selected workers call the shared builder
      `0x18106C6C0` at `0x1810678EC` (`0x181066F40`) and `0x181065056`
      (`0x181064100`). Their call sites forward task-context `+0x10` as
      stack argument 5 and `+0x68` as stack argument 6; the latter is the
      continuation object consumed by the shared tail
      (`0x18106CFA7`, tail `0x18106CFC9-0x18106D003`), which writes the
      result pair and the same `0x181060EA0` thunk. This is a distinct
      implementation, not a second call to `0x18106B5B0`.

    The `0x181060EB0` producer remains on the separate initial/sibling builder
    routes (`0x18106BEF0`'s `0x18106C639` branch and `0x18106D020`'s
    `0x18106D769` tail, called from `0x18106843E/0x1810684BD`). The pool
    worker `0x1805598C0` invokes only the node `+0x30` worker and optional
    `+0x40` index setter before `0x1805586C0` retires the node. The helper
    `0x180557650` invokes a holder's cleanup function only when its holder
    pointer is present, while `0x1805592B0` uses its `+0x8/+0x10` holder
    functions for allocation-failure cleanup and pool-index notification;
    neither is the result-pair callback. A narrowed static scan of the entire
    UnityPlayer image still finds no consumer that loads the generated pair's
    `+0x10` and reaches `0x18107AE60/0x18107B3A0`, API-2 `+0xDA0/+0xDE8/+0xF10`,
    Vulkan, or queue submission. The result-pair-to-draw edge therefore stays
    unresolved and fail-closed; runtime inspection of the record at `+0x20`
    remains the next useful probe.

46. The pool-context identity is now proven through the complete calling
    convention rather than inferred from matching offsets. `0x18107E2E0`
    passes its task context in `r9` to `0x180555D30`; that wrapper preserves
    it in `rbp`, `0x1805573D0` forwards it as `r8`, and `0x180559520` keeps the
    same `r8` when calling `0x1805592B0`. The latter saves incoming `r8` at
    entry (`[rsp+0x18]`) and later copies that saved slot (`[rsp+0xAF0]`) to
    `node+0x28` (`0x180559457`). `0x1805598C0` loads `node+0x28` into `rcx`
    before calling `node+0x30` (`0x1805598E1-0x1805598F0`), so all three
    `0x18107E2E0` worker selections receive the original task context. On
    this route `0x180559520` also supplies a 24-byte node callback tuple whose
    tail is zero; `0x1805592B0` copies it to `node+0x30/+0x40`, making the
    optional `node+0x40` setter null. The worker therefore returns to the
    generic retire path after the builder writes through the object referenced
    by task-context `+0x68`; task-context `+0x10` is only the forwarded
    argument-5 record/input slot. This closes the producer/pool identity edge
    but still leaves the continuation-pair-to-draw consumer unresolved and
    fail-closed.

47. The task-context offsets are now disambiguated from the continuation
    object's offsets. In the `0x18107E9C0` failure path, the caller loads its
    result/input record into task-context `+0x10` and the enclosing continuation
    pointer into task-context `+0x68`, then `0x18107E2E0` queues the worker.
    At `0x181066E10` and `0x1810678EC/0x181065056`, those fields become stack
    arguments 5 and 6 respectively. `0x18106B5B0`'s tail
    (`0x18106BE92`) and `0x18106C6C0`'s shared tail
    (`0x18106CFC9-0x18106D003`) dereference argument 6 and write the pair at
    continuation `+0x8/+0x10`; they do not write task-context `+0x10`.
    The earlier static negative boundary is unchanged in the narrower sense:
    no *statically joined* consumer of the generated pair reaches the HGTree
    handlers, API-2 draw callbacks, Vulkan, or queue submission.

48. The previously broad indirect-call negative is now corrected with an
    exact positive callback-consumer boundary. The high-level opcode-`0x55`
    dispatch reaches `0x18106AAE0` (`0x1804CE4DA`), whose failure branch
    reads the list entry's record at `[rsi+0x10]`, releases any record-owned
    `+0x20` pair, then calls `[record+0x10]` with `record+8` as the context
    (`0x18106AC65-0x18106AC96`). The same pattern exists at
    `0x18106A910`, `0x18106ACB0`, and `0x18106AE70` (local sites
    `0x18106AAC6`, `0x18106AC96`, `0x18106AE54`, and `0x18106B014`), plus
    analogous `0x18109EC12`/`0x18109EDDD` cleanup paths. These are genuine
    consumers of a renderer-list record callback slot and can therefore reach
    `0x181060EA0/0x181060EB0 -> 0x18107AE60/0x18107B3A0` when that slot is
    populated. The async route still writes its returned pair to the list
    record's `+0x20`, while its worker writes callback fields to a
    continuation/work object; static object identity between that object and
    `[rsi+0x10]` remains unproven. This closes the missing callback dispatch
    site without claiming the final continuation-pair-to-draw join.

49. The record/continuation distinction is now also checked from the other
    direction. `0x18107E2E0` has four direct caller families (`0x18107E9C0`,
    `0x181079400`, `0x18107AA30`, and sibling `0x18107F885`). The first
    allocates a distinct 0x30-byte item record at `item+0x10` and a separate
    0x98-byte task descriptor at `item+8`; its returned pair is copied to the
    item record's `+0x20`. The other three callers likewise copy the returned
    pair to their enclosing resource record's `+0x20`. In every worker route,
    pool dispatch preserves the task descriptor as the worker `rcx`, and the
    producer writes callback fields through task-context `+0x68`; no caller
    passes the E9C0 item record as that continuation argument.

    A hash-pinned Capstone alias scan over 7,353 functions in the HGTree and
    adjacent UnityPlayer ranges (`0x181050000-0x181320000`) found 18 simple
    `mov reg,[base+0x10]` -> write `[reg+8/+0x10]` candidates. The only hit in
    the worker range (`0x181065FD0` writing a vector capacity) and the 15 hits
    in later ranges are dynamic arrays, metadata/hash tables, or generic
    resource state; none is the E9C0 0x30-byte record, and none writes its
    callback slot (`+8/+0x10`). This closes the static record-field search
    within the inspected code ranges while retaining the runtime
    continuation-pair-to-draw join as unresolved and fail-closed.

50. The callback producer side is now bounded with a narrower constant-driven
    census. A hash-pinned Capstone scan of all 113,390 UnityPlayer functions
    tracks RIP-relative values landing in the known HGTree callback ranges
    (`0x181060D00/0x181060D20/0x181060D70/0x181060D90/0x181060EA0` families)
    and reports only four callback-valued writes to record-like `+8/+0x10`
    fields: `0x18106BECD` and `0x18106D003` write `0x181060EA0`, while
    `0x18106C66B` and `0x18106D79B` write `0x181060EB0`; all four target
    `+0x10`, with no additional `+8` callback write. The broader alias hit in
    `0x18107EE40` is only zero-initialization of a newly allocated 0x30-byte
    record (`+8/+0x10/+0x18`), not a callback producer. This closes the
    direct, statically recognizable callback producer set. At this stage the
    record identity was not yet interpreted correctly; the subsequent stack
    mapping in item 52 supersedes that narrow identity conclusion while the
    indirect-draw/flush/queue edge remains fail-closed.

52. The previous continuation/record separation is corrected by the Windows
    x64 stack mapping at `0x18107E2E0`. After its prologue, `[rsp+0xA0]` is
    caller arg5 and `[rsp+0xA8]` is arg6. The initializer stores arg5 into the
    task descriptor at `+0x68` (`0x18107E411`). In the primary E9C0 caller,
    arg5 is the 0x30-byte renderer record
    (`[rbx + index*24 - 8]`) and arg6 is a separate input/context pointer
    (`0x18107EDE2-0x18107EDF1`); the sibling FC92 caller likewise passes its
    record (`r14 = [r12+0x10]`) as arg5. Worker `0x181065FD0` reads descriptor
    `+0x68` and passes it as builder arg6 to `0x18106B5B0`; its tail writes
    `[record+8]` and `[record+0x10]` at `0x18106BEC9-0x18106BECD`. The other
    two worker selections route through `0x18106C6C0` and its equivalent
    arg6 tail, with the same record field semantics. The E2E0 caller then
    copies the returned pair into that record's `+0x20`
    (`0x18107EDF6-0x18107EDFE` or `0x18107FC97-0x18107FC9F`). Finally,
    opcode-`0x55` fallback `0x18106AAE0` loads exactly `[rsi+0x10]`, releases
    its `+0x20` pair, and calls `[record+0x10]` with `[record+8]`
    (`0x18106AC65-0x18106AC96`). This statically joins the async result pair,
    callback slot, and HGTree handler on one renderer record. Items 46-50's
    claim that this was a distinct continuation/work object is superseded;
    only the handler's indirect-draw/flush/queue ownership remains fail-closed.

53. The low-level dispatch table was rechecked to separate the adjacent API-2
    queue case from HGTree's renderer-list callback. With index
    `opcode - 0x2711`, `0x1813BB574[0x273B-0x2711]` resolves to
    `0x1813B1110`; that case parses the callback pointer/record fields and
    calls the parsed callback at `0x1813B12B0-0x1813B12B6`. The next table
    entry, `0x273C`, resolves to `0x1813B12BB` and is the case that dispatches
    API-2 vtable `+0xEA8` at `0x1813B13C5`. Therefore the earlier wording that
    joined HGTree `0x273B` directly to `0x18083F530` was an opcode-indexing
    error. The corrected positive chain ends at the direct HGTree callback
    `0x181060D70 -> 0x18107AB10`; API-2 `+0xEA8`, indirect draw, flush, and
    queue-submit ownership remain unjoined and fail-closed. A raw call-slot
    census finds generic `+0xDE8` sites at `0x18092E450`/`0x1813AFED9` and
    `+0xF10` sites at `0x1804D1791`/`0x1813B1574`, with no such call in the
    HGTree handler range `0x181060000-0x181081000`.

54. The next callback boundary after the corrected `0x273B -> 0x18107AB10`
    edge is now bounded. `0x18107AB10` registers pool callbacks
    `0x1810865C0` and `0x1810685A0`. The former allocates a small metadata
    object, initializes it through `0x18042C1B0`, and inserts it through
    `0x181074F10`; its body has no API-2 draw/flush/queue slot or graphics
    call. The latter is one logical resource worker split across chained
    `.pdata` entries `0x1810685A0-0x1810685CD`, `0x1810685CD-0x1810685D5`,
    `0x1810685D5-0x1810688BF`, `0x1810688BF-0x18106937E`,
    `0x18106937E-0x1810693D3`, `0x1810693D3-0x18106949B`,
    `0x18106949B-0x1810694C0`, and `0x1810694C0-0x1810694CC`.
    Its complete direct-call census is resource/registry work
    (`0x181060B30`, `0x1813ABD10`, bitset/format helpers, and allocation or
    validation helpers) plus only indirect `+0xB0` and `+0xC0` interface calls.
    The resolved `+0xB0/+0xC0` targets (`0x180833470/0x180833630`) are
    atomic resource-handle operations that tail into `0x180822180/0x1808224F0`;
    they do not record a command or call Vulkan. No instruction in either
    callback body reaches API-2 `+0xDA8`, `+0xDE8`, `+0xF10`, `+0xEA8`, a
    draw opcode, Vulkan, or queue submission. This closes the concrete
    AB10-to-worker path as a resource/state boundary while leaving the
    runtime consumer that turns the populated records into the final HGTree
    draw unresolved and fail-closed.

55. A complete hash-pinned exact-slot census now separates the remaining
    `+0xDA8` consumers from HGTree's `0x273B` callback. The four call sites
    are `0x180932245` (a generic record helper whose recording-mode twin
    writes `0x27B9` at `0x180931FBD`), `0x1804D2A31` and `0x1804D492C`
    (sibling high-level resource/format handlers), and `0x1813B057F` (the
    low-level command interpreter). The low-level dispatch table at
    `0x1813BB574` indexes by `opcode - 0x2711`: `0x2734` targets
    `0x1813AFFF7`, whose body reaches `+0xDA8` at `0x1813B057F`; the next
    `0x2735` case starts at `0x1813B05B6`. This is not the HGTree case:
    HGTree's `+0xEA0` writer `0x1809324E0` emits `0x273B` at
    `0x18093255B`, and `0x273B` still resolves to `0x1813B1110` and the
    direct callback `0x181060D70 -> 0x18107AB10`. The separate generic
    front-end writer `0x180931980` emits `0x2734` and falls back to
    `+0xDA0`, while `0x1809318F0` emits `0x2743`/falls back to `+0xF18`;
    neither has a static HGTree caller. Finally, the high-level command
    jump table at `0x1804D19C8` maps opcode `0x55` only to `0x1804CE4BD`;
    neither `0x1804D27AB` nor `0x1804D4705` (the owners of the two generic
    `+0xDA8` sites) is a high-level opcode target. Thus the global `+0xDA8`
    implementation and its `0x2734` producer are real indirect-draw/state
    candidates, but no installed-image edge joins them to HGTree `0x55` or
    its `0x273B` callback. The final HGTree record-to-draw/flush/queue join
    remains unresolved and fail-closed.

56. The resource-ready branches of all three renderer-list creation cores are
    now bounded and do not hide a draw call. `0x18107EE40` reaches
    `context+0xEA0` with callback `0x181060D90` at `0x18107F13F`, then calls
    `context+0x850` at `0x18107F150`; `0x18107FD22` does the same with
    callback `0x181060D20` at `0x181080032/0x181080043`; and
    `0x181080190` uses callback `0x181060D00` at
    `0x1810805EE/0x1810805FF`. When the readiness predicate
    `0x181057780` is false, each core instead calls the shared builder
    `0x181080730` and copies its result pair. The `+0x850` front-vtable
    implementation `0x180934850` only records low opcode `0x2798`, updates
    the command counter, and calls `0x1806888E0`; it has no `+0xDA8`,
    `+0xDE8`, `+0xF10`, or Vulkan draw edge. A direct-cell scan over the full
    HGTree/creation range `0x181060000-0x181081000` finds no calls to the
    resolver cells for `vkCmdDraw`, `vkCmdDrawIndexed`,
    `vkCmdDrawIndirect`, or `vkCmdDrawIndexedIndirect`. The named indirect
    draw calls remain confined to the neighboring API-2 `+0xDA8` thunk
    (`0x180820940 -> 0x18082E820`, calls at `0x18082E91B/0x18082E933`), so
    the renderer-record-to-draw/flush/queue edge remains unresolved and
    fail-closed for HGTree.

57. The main internal-call table audit removes the attribution ambiguity at
    the remaining playback boundary. `ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected`
    is index `3645` -> `0x1800B6F40 -> 0x18052D730 -> 0x1804CDF70 ->
    0x1804CE0A0`, and the table-A tree writer joins it at opcode `0x55`.
    `Graphics::ExecuteCommandBuffer` is index `924` -> `0x18005C0D0`, a
    separate resource/object body without a direct interpreter edge.
    `Submit_Internal_Injected` is index `3636` -> `0x1800B4A40 -> 0x1805385A0
    -> 0x18052E0B0`; its type-2/type-3 records reload deferred command-buffer
    pointers from `context+0x10128` and call the same interpreter, making it a
    concrete deferred consumer rather than an unrelated state wrapper. The
    no-copy entries likewise use distinct helpers (`0x18052DB50` and
    `0x18052DA20`), so the final renderer-list draw/flush/queue owner remains
    runtime-indirect and fail-closed.

58. The deferred Submit loop is now decoded rather than treated as an opaque
    flush candidate. `0x18052E0B0` reads 16-byte records at `context+0x10030`,
    dispatches their type through `0x18052F25C`, and maps type `2` to
    `0x18052E869` and type `3` to `0x18052E8F7`. Both branches load
    `context+0x10128[index]` and call `0x1804CDF70`; type 3 additionally passes
    the buffer `+0x170` mode. The producers `0x18052D730`/`0x18052DB50` write
    type 2, while `0x18052D8F0`/`0x18052DA20` write type 3. Therefore the
    table-A HGTree writer (`0x180064580 -> 0x1804C7930`, opcode `0x55`) can be
    consumed through Submit as well as direct Execute/NoCopy. The shared
    interpreter also makes generic opcode `0x6A -> +0xF10` reachable, but no
    static edge from the HGTree callback-produced records to `+0xDE8`,
    `+0xF10`, or the final queue owner is established.

59. The tempting API-2 resource bridge is now closed at the next static
    boundary. The `+0xE90` implementation `0x180843BF0` calls `+0xDC0`
    (`0x18083F680`), which invokes the nested runtime vtable `+0x48` at
    `0x18083F71B` and passes its return as the third stack argument to
    `0x18083F8F0`. The complete F8F0 body reads its first stack argument but
    never reads that third argument; it instead allocates/looks up resource
    records through `0x180879010`/`0x180839B00` and updates the shared
    descriptor cell `0x1821D3898` (the Vulkan resolver path is
    `vkUpdateDescriptorSetWithTemplate`). Direct-call census finds exactly
    three F8F0 callers (`0x18083F680`, `0x180840E00`, and `0x180846635`),
    all in the generic API-2 resource cluster, and no HGTree `0x18106*` or
    `0x18107*` caller. Together with the sibling `0x18061FB60` helper that
    consumes the same `+0x48` shape as a NUL-terminated metadata/name string,
    this is evidence for a resource metadata/descriptor-preparation boundary,
    not a final draw, flush, or queue-submit bridge. The HGTree-specific
    record-to-draw/flush/queue join therefore remains unresolved and
    fail-closed.

60. The managed render-pipeline boundary is now positively joined. The mapped
    `HGRenderPipeline.Render(ScriptableRenderContext, List<Camera>)` body spans
    GameAssembly `0x183455030-0x18345A6E4`; it directly calls
    `ExecuteCommandBuffer` at `0x183457129` and `0x18345997B`, calls
    `ExecuteCommandBufferNoCopy` at `0x183459502`, `0x1834595D4`, and
    `0x183459614`, and calls `Submit` at `0x183459D69`. The six concrete pass
    lambdas that call `HGRendererListUtils.DrawTreeECSRendererList` preserve
    their render-graph context in `rsi`, `rbx`, `rdi`, or `r13` and pass that
    same context as `rcx` to GameAssembly `0x189C0A130`, while passing their
    renderer-list id in `edx`; the helper then reads `context.fields.cmd`
    before forwarding to `HGTreeRender.DrawECSRendererList`. Thus HGTree's
    table-A `0x55 -> 0x273B` records are recorded through the same managed
    pass-command-buffer framework that the main Render method executes and
    ultimately submits. This joins HGTree playback to the render-pipeline
    Execute/NoCopy/Submit boundary, but it does not identify the HGTree-specific
    API-2 `+0xDA8` indirect-draw branch, `+0xDE8` flush order, or Vulkan queue
    owner; those remain fail-closed.

61. The RenderGraph command-buffer identity is now bounded below the pass
    callbacks. `HGRenderGraph.ExecuteRenderGraph` (`0x189B2BA30`) calls
    `ExecuteCompiledPass` (`0x189B2B62C`), which passes
    `r8 = [this + 0x60]` to both `PreRenderPassExecute`
    (`0x189B2E740`) and `PostRenderPassExecute` (`0x189B2E4B4`), then invokes
    the compiled pass through `HGRenderGraphPass.Execute` (`0x189B37D20`).
    The `HGRenderGraphContext` layout is source-backed as
    `renderContext` then `cmd`; the native Pre callback loads
    `cmd = [rgContext + 0x18]`, passes `&[rgContext + 0x10]` as the render
    context, and calls `ExecuteCommandBufferNoCopy` at `0x189B2E8D4`.
    The six previously identified pass lambdas receive this same context
    shape before calling `HGRendererListUtils.DrawTreeECSRendererList`, which
    reads the same `context.fields.cmd`. Therefore the HGTree `0x55 -> 0x273B`
    records are placed in the command buffer that RenderGraph prepares and
    executes around the pass, and the pipeline-level `Submit` remains its
    deferred consumer. This closes the command-buffer identity boundary, but
    still does not prove HGTree-specific `+0xDA8` selection, `+0xDE8` ordering,
    or queue ownership.

62. The generic pass/delegate boundary is now recovered from the shipped
    generic instantiation rather than inferred only from the decompiled source.
    `HGRenderGraphBuilder.SetRenderFunc<PassData>` at `0x1876BCA9C` forwards
    to its overload at `0x1876BC9C4`, which directly calls pass
    `SetupSubpass` (`0x1884756FC`) and `SetupRenderFunc` (`0x1884755E0`).
    `SetupRenderFunc` selects one of the four `SubpassDesc` slots at
    `SubpassDesc+0x20/+0x40/+0x60/+0x80`; its helper `0x188475590` stores the
    `RenderFunc` delegate, camera, and 16-byte custom payload into that
    descriptor. The generic `HGRenderGraphPass<PassData>.ExecuteInternal`
    body at `0x188474A4C` then calls `ExecuteSubpassRenderFunc`
    (`0x188474E38`). That body iterates `m_subpasses` (`this+0xB0`), calls
    `HGRenderGraph.InvokeOwnerCallback` (`0x189B2DA6C`) for each populated
    descriptor, obtains the graph context through `get_HGContext`
    (`0x189B3011C`), and invokes the stored delegate indirectly through its
    method pointer with the pass `data` (`this+0xD0`) and that
    `HGRenderGraphContext`. This is the concrete dynamic edge that reaches
    the six pass lambdas already pinned to
    `HGRendererListUtils.DrawTreeECSRendererList`; it explains why no direct
    HGTree-to-`+DA8/+DE8` call appears in the pass body. The generic pass body
    itself contains no `+DA8`, `+DE8`, `+F10`, Vulkan draw, or queue-submit
    edge, so final HGTree draw/queue ownership remains fail-closed.

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
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813B1080 0x1813B1480
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181060D00 0x18107AD80
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107AB10 0x18107AC30
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1810865C0 0x1810866AD
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1810685A0 0x1810694CC
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180833470 0x180833650
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180822180 0x180822520
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801719B0 0x180171A40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180064580 0x180064620
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804C7930 0x1804C79D0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804CE4BD 0x1804CE4DF
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18106AAE0 0x18106ACB0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083F530 0x18083F5D0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180844C3F 0x180844C80
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801713D0 0x1801715C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180A60190 0x180A6041C
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A60190
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A5C5C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801572F0 0x180158C00
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180B3E5C0 0x180B3E699
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180A95EB0 0x180A95F37
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1800B6F40 0x1800B6FC2
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18052D730 0x18052D8E9
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804CDF70 0x1804CDFEB
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804CE0A0 0x1804CE406
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18072F7E0 0x18072F810
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180829030 0x1808290A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083E720 0x18083EC40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180842370 0x180842650
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808351F0 0x180835EF0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180839D50 0x18083A0B0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808558E0 0x180855AA0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180843BF0 0x180843D40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083F680 0x18083F8F0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181DBC098 0x181DBCF30
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813AFEA0 0x1813AFF00
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083F1E0 0x18083F230
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180843D60 0x180844A20
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180841C40 0x180841D50
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808200C0 0x180820220
python scratch\\reverse_engineering\\hgtree_component67_producers\\scan_known_callback_slot_writes.py > scratch\\reverse_engineering\\hgtree_component67_producers\\known_callback_slot_writes_all.txt
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083C6B0 0x18083D3B0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180820580 0x1808205A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18082D6B0 0x18082D7A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808208F0 0x180820910
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18082E660 0x18082E750
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180820940 0x180820960
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18082E820 0x18082E8A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18061FB60 0x18061FD80
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180624000 0x1806242B0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180861C20 0x180861C34
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180850F80 0x180851320
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180823F80 0x180824040
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18093AE10 0x18093B150
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18092E350 0x18092E480
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1809258C0 0x180925C40
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180931980 0x180931F30
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18092C320 0x18092C6DC
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180929430 0x1809295A5
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813AFFF7 0x1813B03E2
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813B91F0 0x1813B9305
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x189C0A130 0x189C0A1AA
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_gameassembly_direct_calls.py 0x189C0A130 0x18B3FBFA4 0x18B3E3FE8
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1801719B0 0x180171A38
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180A5C5C0 0x180A5C650
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18065C0C0 0x18065C0F0
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x180A5C5C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107AE60 0x18107BA18
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1808350E0 0x180835230
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083AA90 0x18083C700
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18083F1E0 0x18083F230
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180843D60 0x180844D00
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1811DDC50 0x1811DDDCC
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804CECEF 0x1804CED50
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1811A5BD0 0x1811A5C08
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1811AB1B0 0x1811AB7DB
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1811D03A0 0x1811D06F8
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804D4680 0x1804D49A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_unity_target_xrefs.py 0x18106C30E 0x18106C639 0x18106C6C0 0x18106CFA7 0x18106D020 --jobs 8
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181064FE0 0x1810650A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181067880 0x181067930
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18106C6C0 0x18106D120
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1809318F0 0x180931F30
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180931980 0x180931F30
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180931F30 0x180932265
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1809324E0 0x180932780
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813AFFF7 0x1813B05B6
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1813B05B6 0x1813B0765
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804D27AB 0x1804D2AC1
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1804D4705 0x1804D4990
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107EE40 0x18107F1A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18107FD22 0x181080190
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x181080190 0x181080730
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180934850 0x180934910
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x180820940 0x18082E950
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^UnityEngine\\.Rendering\\.CommandBuffer$" --member-regex "^AddDrawECS.*" --body-target-regex "^AddDrawECS.*" --body-target-type-regex "^UnityEngine\\.Rendering\\.CommandBuffer$" --all-images --include-all-members --body-context 1 --out scratch\\reverse_engineering\\hgtree_component67_producers\\commandbuffer_hgdraw_targets.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\commandbuffer_hgdraw_targets.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\commandbuffer_hgdraw_targets.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\commandbuffer_hgdraw_native_map.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\commandbuffer_hgdraw_native_map.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x18B3E3F44 0x18B3E4028
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1800B4A40 0x1800B4A48
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x1800B6F40 0x1800B6FC2
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18005C0D0 0x18005C168
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18052D730 0x18052D7B2
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18052E0B0 0x1805385A0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18052D818 0x18052DE10
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_unity_range.py 0x18052E7D0 0x18052E957
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^HG\\.Rendering\\.Runtime\\.HGRenderPipeline$" --member-regex "^Render$" --body-target-regex "^Render$" --body-target-type-regex "^HG\\.Rendering\\.Runtime\\.HGRenderPipeline$" --all-images --include-all-members --body-context 2 --out scratch\\reverse_engineering\\hgtree_component67_producers\\hg_render_pipeline_render_metadata.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hg_render_pipeline_render_metadata.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\hg_render_pipeline_render_metadata.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\hg_render_pipeline_render_native_map.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hg_render_pipeline_render_native_map.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_gameassembly_direct_calls.py 0x183339850 0x1834534C0 0x183DBB470 0x189C0A130
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x1834570D0 0x183457170
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x183459580 0x183459650
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x183459930 0x1834599B0
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x183459D20 0x183459DB0
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraph$" --member-regex "^(ExecuteCompiledPass|PreRenderPassExecute|PostRenderPassExecute|ExecuteRenderGraph)$" --body-target-regex "^(ExecuteCompiledPass|PreRenderPassExecute|PostRenderPassExecute|ExecuteRenderGraph)$" --body-target-type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraph$" --all-images --include-all-members --body-context 2 --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraph_execute_metadata.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraph_execute_metadata.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraph_execute_metadata.json --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraph_execute_native_map.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraph_execute_native_map.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x189B2B62C 0x189B2B760
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x189B2E740 0x189B2EA6C
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x189B2E4B4 0x189B2E6C0
python scratch\\reverse_engineering\\hgtree_component67_producers\\find_gameassembly_direct_calls.py 0x1834534C0 0x189B37D20 0x189B2E740 0x189B2E4B4
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraphPass.*$" --member-regex "^(ExecuteInternal|ExecuteSubpassRenderFunc|BeginRenderPass|EndRenderPass|BeginSubpass|EndSubpass|SetupRenderFunc|SetupPreRenderPassFunc|SetupPostRenderPassFunc|Initialize|CreateRenderPass|HasRenderFunc)$" --body-target-regex "^(ExecuteInternal|ExecuteSubpassRenderFunc|BeginRenderPass|EndRenderPass|BeginSubpass|EndSubpass|SetupRenderFunc|SetupPreRenderPassFunc|SetupPostRenderPassFunc|Initialize|CreateRenderPass|HasRenderFunc)$" --body-target-type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraphPass.*$" --all-images --include-all-members --body-context 2 --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphpass_exec_metadata.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphpass_exec_metadata.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphpass_exec_metadata.json --include-generic-instantiations --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphpass_exec_native_map.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphpass_exec_native_map.md
python tools\\endfield-il2cpp\\catalog_option_flow_metadata.py --type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraphBuilder$" --member-regex "^(SetRenderFunc|SetPreRenderPassFunc|SetPostRenderPassFunc|SetupRenderFunc|SetupSubpass)$" --body-target-regex "^(SetRenderFunc|SetPreRenderPassFunc|SetPostRenderPassFunc|SetupRenderFunc|SetupSubpass)$" --body-target-type-regex "^HG\\.Rendering\\.RenderGraphModule\\.HGRenderGraphBuilder$" --all-images --include-all-members --body-context 2 --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphbuilder_renderfunc_metadata.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphbuilder_renderfunc_metadata.md
python tools\\endfield-il2cpp\\map_body_targets_to_gameassembly.py --metadata "D:\\Program Files\\Endfield Game\\Endfield_Data\\il2cpp_data\\Metadata\\global-metadata.dat" --gameassembly "D:\\Program Files\\Endfield Game\\GameAssembly.dll" --catalog scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphbuilder_renderfunc_metadata.json --include-generic-instantiations --out scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphbuilder_renderfunc_native_map.json --markdown scratch\\reverse_engineering\\hgtree_component67_producers\\hgrendergraphbuilder_renderfunc_native_map.md
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x188474A4C 0x188475350
python scratch\\reverse_engineering\\hgtree_component67_producers\\dump_gameassembly_range.py 0x188475590 0x1884756F9
```
