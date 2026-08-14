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
proven HGTree handler. The separate CommandBuffer tree-list call is pinned to
its GC-root and string-payload validation boundary.
The later record loop is also pinned to Vulkan
`vkUpdateDescriptorSetWithTemplate` through a shared runtime slot, and the same
API-2 backend family has a concrete descriptor -> draw -> queue-submit sink.
The recorded HGTree receiver and its callback-produced resource/state records
are source-pinned. Managed tree-list playback, callback ordering, the
HGTree-specific Vulkan draw consumer, and queue submission ownership remain
unresolved; this is not yet a retail frame-parity claim.

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

12. The front-end/backend layering is now explicit. Setup
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

13. The remaining API-2 slots on this route are now bounded as resource and
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
    record builder`; the later record loop is a separate backend descriptor
    update path, not a consumer of this returned metadata value.

16. The post-F8F0 indirect at `0x18083F89D` is a shared runtime dispatch cell,
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

17. The same API-2 vtable contains a concrete backend draw and submit sink.
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

18. The interpreter cases now have an exact command-stream producer boundary.
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

19. The command-stream receiver is now pinned to the API-2 backend. The
    backend/context creation path `0x180929430` calls `0x1809258C0` to create
    the front-end context, obtains the selected backend from
    `0x18072F7E0`, and at `0x180929540` writes that same pointer to
    `[context+0x2700]+0x70` (the command-stream state receiver). The attach
    call immediately following it, `0x180939C80`, stores the pointer at
    `context+0x2708`; API id `2` gives that backend vtable
    `0x181DBC098`. Thus the receiver read by `0x1813AEE90` is not a second
    opaque object: it is the selected API-2 backend shared by immediate and
    recorded paths.

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

20. The managed HGTree draw route is now pinned separately from that recorded
    resource family. PData-scoped direct-call scanning of the pinned
    `GameAssembly.dll` maps `HGRendererListUtils.DrawTreeECSRendererList`
    (`0x189C0A130`, method index `288214`) to
    `HGTreeRender.DrawECSRendererList` (`0x18B3FBFA4`) at
    `0x189C0A165`. The helper loads the CommandBuffer from
    `[context+0x18]`, forwards the renderer-list id in `edx`, and enters the
    HGTree wrapper; that wrapper null-checks the command buffer and tail-jumps
    to `CommandBuffer::AddDrawECSTreeRendererList`
    (`0x18B3E3FE8`, method index `407629`). The UnityPlayer internal-call table
    maps that name to native `0x1801719B0` (global internal-call index `3467`; a
    previously used class-local table label was `321`).

    The same draw helper is directly called by six pinned render callbacks:
    `HGPunctualLightShadowManager+<>c::<.cctor>b__49_0` (`0x189B56CCC`),
    `GBufferPassConstructor+<>c::<.cctor>b__10_0` (`0x189BB6280`), both
    `OnePassDeferredPassConstructor+<>c::<.cctor>b__33_0/1`
    (`0x189BC526C`/`0x189BC5674`),
    `HGShadowManager+<>c::<.cctor>b__104_3` (`0x189D2572C`), and
    `HGASMManager+<>c::<.cctor>b__84_0` (`0x189D26464`). This is positive
    evidence that the tree-list draw entry is used by real render passes.
    Native `0x1801719B0` itself only performs the managed-root barrier and
    string-payload/hash validation before returning; it exposes no direct
    graphics call, `0x273x` opcode, or `+0xDE8` dispatch. Therefore the
    `+0xDE8` API-2 sink remains a separate command-family candidate, while the
    unresolved HGTree sink is the runtime CommandBuffer consumer/execution
    edge after this internal call (and the runtime-indirect consumer of the
    populated resource nodes).

21. The next managed execution boundary is now addressable, but it does not
    close the HGTree draw edge. The pinned UnityPlayer global internal-call
    table uses name base `0x1820D3DB0` and function base `0x1820D9520`; its
    entries are `ScriptableRenderContext::Submit_Internal_Injected` at
    `0x1801572F0` (global index 3636),
    `SubmitForRenderPassValidation_Internal_Injected` at `0x180157580`
    (3637), and
    `ExecuteCommandBuffer_Internal_Injected`/`Async`/`NoCopy`/`AsyncNoCopy`
    at `0x1801587D0`/`0x180158980`/`0x180158B30`/`0x180158B80`
    (3645-3648). The normal execute wrapper only validates the native context
    through `0x18075E280` and reads/writes its `+0xE4` state; it has no direct
    `0x273x`, `+0xDE8`, or graphics call. The no-copy variants enter
    `0x180B3E5C0`/`0x180A95EB0`, which build native state through indirect
    virtual/object calls, but still do not statically identify the API-2 draw
    sink. The remaining target is therefore the dynamic command-buffer or
    render-graph playback reached from these helpers, not another direct
    `AddDrawECSTreeRendererList` producer.

    This also removes a remaining alternative interpretation of the tree
    internal call: native `0x1801719B0` never consumes its `edx` renderer-list
    id, and its BSS call slot `0x1821BE708` has one executable writer only, at
    `0x18077C055`, where static initialization resolves
    `il2cpp_gc_wbarrier_set_field`. The tree path is therefore a fixed
    managed-payload validation boundary, not a late-bound renderer-list
    converter.

22. The high-level Unity command-buffer playback sink can now be separated
    from the ScriptableRenderContext wrappers above. In the class-local
    UnityPlayer registration, the name pointer at `0x1820D5A90` is
    `UnityEngine.Graphics::ExecuteCommandBuffer` and the paired function slot
    at `0x1820D31E8` is native `0x1800B6F40` (the async sibling is
    `0x1800B71D0`). `0x1800B6F40` roots the managed command-buffer payload
    through the fixed `0x1821BE708` barrier slot, then calls
    `0x18052D730`; that helper constructs the playback context, calls
    `0x1804CDF70`, and its dispatch core enters the high-level opcode
    interpreter `0x1804CE0A0`. The interpreter reads a dword opcode from the
    byte stream and dispatches through a bounded `0x00..0x6F` jump table before
    invoking the backend callbacks.

    This closes a real CommandBuffer playback chain for ordinary Unity command
    records, but it does not yet bind the HGTree path: `0x1801719B0` still has
    no call to the high-level record writers, and no static reference from its
    managed-payload validator to the interpreter or to API-2 `+0xDE8` exists.
    Therefore the remaining HGTree question is whether its renderer-list
    payload is consumed by this interpreter through an indirect object/table
    callback, or by the separate `0x27xx` command family; both remain
    fail-closed until a renderer-list-specific playback case is identified.

23. The ordinary `CommandBuffer::Internal_DrawRendererList_Injected` route is
    a distinct native path and must not be used as a proxy for HGTree tree
    draws. The global UnityPlayer internal-call table maps index `3463` to
    `0x1801713D0`; its two renderer/resource branches call `0x180A60190` at
    `0x180171520` and `0x18017153F`. An exhaustive direct-xref scan of
    `0x180A60190` finds only those two call sites. The helper performs
    payload/object validation and indirect renderer/resource-state resolution
    (including `0x180A50FA0`, `0x180A69570`, and `0x180A4A640` families), but
    has no direct graphics call, command opcode write, or API-2 `+0xDE8`
    dispatch. The HGTree `AddDrawECSTreeRendererList` body at `0x1801719B0`
    has no call to this helper and remains the separate managed-payload
    validation boundary described above. Thus ordinary `DrawRendererList`
    resource resolution and HGTree tree-list submission are statically split;
    neither one closes the missing renderer-list playback consumer.

24. The remaining native helper in the tree internal-call body is now bounded
    as a payload hash check, not a hidden renderer-list writer. At
    `0x180171A07`, `AddDrawECSTreeRendererList` calls shared helper
    `0x180A5C5C0`. That helper first rejects a null payload, uses
    `0x180769E20` to normalize the inline/indirect byte span, then seeds an
    accumulator with `0xffffffff` and calls `0x18065C0C0`. The latter is a
    byte-at-a-time CRC loop over the bounded span; `A5C5C0` returns the
    bitwise-not accumulator and only enters the ordinary error logger when the
    validation flag is false. An exhaustive direct-xref scan finds the same
    helper shared by unrelated command APIs (`Internal_DrawProcedural...`,
    instanced/indirect mesh draws, occlusion/random-write/scissor commands,
    `CopyTexture`, and `Blit_Identifier`) in addition to the HGTree entry.
    Neither `A5C5C0` nor `65C0C0` writes a command opcode, touches the
    graphics-context vtable, or dispatches API-2 `+0xDE8`. This closes the
    apparent late-bound call in the tree body as generic managed-payload
    validation and leaves the actual renderer-list playback edge after the
    internal call (or in the runtime-indirect resource consumer), still
    fail-closed.

25. The two apparent runtime consumers adjacent to this boundary are now
    bounded as state/lifetime machinery rather than a proven renderer-list
    submitter. `ScriptableRenderContext`'s no-copy wrappers at
    `0x180158B30`/`0x180158B80` enter `0x180B3E5C0` and `0x180A95EB0`.
    `B3E5C0` validates the native context, allocates/initializes a small
    context-state object, and returns a 16-byte state record; `A95EB0`
    allocates a `0x3c`-byte object, runs its virtual initialization methods,
    and forwards the resulting object through `0x180763670`. Neither body
    contains an opcode write, graphics-context vtable dispatch, Vulkan call,
    or API-2 `+0xDE8` call. They therefore do not close the missing playback
    edge.

    The API-2 resource pool has the same negative shape. `0x180559B30` walks
    bitmap-selected `0x80`-byte nodes and decrements their refcounts;
    zero-ref nodes enter `0x1805598C0`, which invokes node callbacks stored at
    `+0x30`/`+0x40`, clears record fields, and returns through
    `0x1805586C0`. `0x1805586C0` is an owner/resource lifetime collector
    (atomic counts, bitmap cleanup, and `0x18055AD70` release), not a direct
    graphics or command-stream sink. An indirect callback could still hide a
    runtime consumer, so this is a bounded fail-closed result rather than a
    claim that the pool is unrelated; however, no direct device, opcode, or
    API-2 submission edge is present in the inspected pool bodies.

26. The resource-callback branch is now closed through the shared API-2 record
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

27. The 0x60-byte records created on the resource path now have bounded
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

28. The indirect-slot names are source-pinned by Unity's Vulkan resolver
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

29. The neighboring indirect-draw control path is now source-identified rather
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
```
