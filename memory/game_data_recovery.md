# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.
This file is the entry point; per-family evidence lives in
[`game_data/`](game_data/README.md), and the mechanics of each reader, gate and
validator live in its module docstring and reviewed contract under `scripts/`.

Required runtime observations are collected in
[`runtime_capture_requirements.md`](runtime_capture_requirements.md). Append
future capture needs there, with links back to their owning evidence topics.

## Why this topic remains

Many evidence contracts are shared by several pages or exist before any page
projection: overlay behavior, binary framing, native build gates,
runtime/static distinctions, and cross-domain graph provenance.

## Understanding the running game

The current recovery target is understanding the binary implementation of
combat well enough to support a lightweight simulator for better combat
decisions. This stage recovers game data and executable rules; it does not yet
build the simulator. Exact file decoding, an architectural explanation and a
predictive combat model have different completion criteria. The four evidence
levels below organise proofs; the following map provides wider game context.
These are explanatory layers, not the client's exact module boundaries.

| System layer | Existing model and its evidence owner | Architectural gap |
| --- | --- | --- |
| Resources and versions | VFS overlay selects definitions and assets; native code and IFix supply consumers. See `install_and_vfs.md`, `unity_assets.md` and `ifix_patch.md` in the detail index. | Effective session loading and patch selection; these need not be observed again for every conditional explanation. |
| Configuration and assembly | Character/growth/weapon keys select skills; level, talent and potential processing precede Skill/Ability initialization and Blackboard layers. Enemy templates select AI configurations and authored graphs. See [Gameplay](game_data/gameplay_semantics.md) and [ExtendData](game_data/extend_data.md). | Unjoined constructors, override paths and genuinely different configuration types. |
| State and ownership | AbilitySystem, Attributes, Skill and Buff carry local combat state; scene controllers consume world state. See Gameplay and [DynamicStreaming](game_data/world_dynamic_streaming.md). | Cross-system identity, which owner writes each state, and client/server authority. |
| Behaviour and scheduling | Action/Sequence, Buff lifecycle, skill timelines, LevelScript and AI graphs provide triggers and execution structures. See Gameplay, ExtendData and [Story carriers](game_data/story_carriers.md). | A unified explanation of updates, synchronous reentry, deferred work, cancellation, death and unloading. |
| Evaluation and settlement | Attribute stages and the default healing pipeline are explained; damage and Poise have reviewed intermediate routes. See Gameplay. | Complete hit-to-damage-to-state/event chain and exceptional settlement paths. |
| World and persistence | Quest/mission/map-variable conditions feed scene-state visibility; interaction and Story have separate activation carriers. Factory definitions and blueprints describe authored layouts. See DynamicStreaming, Story carriers and Gameplay. | Production operation, persistent state transitions and server decisions; a definition is not a running producer. |
| Presentation and synchronization | Asset/controller/clip references, Wwise request and graph routes, Story playback carriers and selected protocol handoffs explain local interfaces. See Unity assets, [Audio](game_data/audio_overview.md) and Story carriers. | Cross-system ownership and feedback; a request or client message does not prove playback or server acceptance. |

Three existing vertical chains provide the starting point for synthesis:

| Chain | What can already be explained | Keep the real break visible |
| --- | --- | --- |
| Character configuration → Skill/Blackboard → Buff/action → attributes and healing → events | Configuration processing, parameter precedence, lifecycle/reentry, staged attributes, requested versus actual healing, and two event channels. | Other action semantics, shared scheduling and full damage settlement; historical scalar recovery is separate, while relevant listeners remain simulation requirements. |
| Enemy message/template → AIConfig → blackboard/graph → task | Selected default template/config/graph identity and a task's field consumption. | Spawner library identity is not proved to become the protocol template identity; graph scheduling and task-to-skill execution need separate joins. |
| Quest/mission/variables → MapConfig scene state → streaming visibility; LevelScript → interaction/Story | Conditional state calculation reaches state controllers; typed playback and callback carriers identify local interfaces. | Visibility is not a proof of interaction or Story activation. Mission transition ownership and server callback decisions remain separate. |

For each subsystem, design understanding is sufficient when its definitions,
state owner and instance lifetime, triggers, main branches, state changes,
outputs and neighbouring interfaces can be explained under stated conditions.
Use existing examples of a normal path and a materially different branch, and
resolve contradictory evidence. This does not require every configuration,
listener, transient scalar or branch to be observed, nor behavioural parity.
Reviewed static synthesis remains `conditional` where appropriate; it must not
be relabelled as observed execution or `exact` proof.

The current work order follows combat prediction: loadout and enemy inputs;
damage/Poise settlement and snapshot-versus-dynamic evaluation; Buff state,
stacking and event effects; combat time, skill/resource/cooldown transitions;
then target/hit and enemy behaviour where they change the selected scenario.
Client/server corrections matter where they change these outcomes. World,
mission, factory, rendering and audio recovery are separate work, rather than
prerequisites for the lightweight combat model. First connect existing bytes,
typed consumers and retained observations into these rules. The default
Buff/healing architecture is explained, but this alone does not certify its
complete executable semantics for simulation.

A new investigation should state which combat prediction changes with its
result. Prioritise reusable rules and required scenario inputs over an
unrecoverable historical value. Capture is warranted when existing data, code
and retained observations cannot resolve a necessary timing/input/transition
or distinguish competing implementations, the result changes supported combat
predictions, and a minimal scenario has acceptance and stop criteria. Relevant
listeners, snapshot rules and timing cannot be dismissed as details when they
alter a supported character's simulation. Reopen an understood mechanism for
contradictory evidence, new control logic, relevant build drift or a predictive
requirement it does not cover. Missing historical inputs alone do not justify
collecting a new run: that run supplies new inputs, not the historical ones.

## Refresh and evidence rules

```bat
python -m scripts.game_data.extraction.verify_export_freshness
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Run `--from-game` only when the user asks for an installed refresh.

- StreamingAssets is the fallback; Persistent is the active overlay. A changed
  logical path replaces its fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- Metadata default blobs require their primitive backing type: decoding a
  byte-backed enum as a signed compressed `Int32` invents negative IDs. Resolve
  the backing type from the selected MetadataRegistration first; the native
  enum helper supports reviewed byte and `Int32` cases and fails closed.
  The separate `il2cpp/enum64_defaults.py` reader handles authenticated
  Int64/UInt64 enum defaults as bounded raw eight-byte values; both the backing
  and each member's primitive must agree. Damage masks use that reader and
  must not be truncated or sent through the compressed Int32 decoder.
- A source-only classifier does not inherit the native gate because native
  evidence once motivated it. Direct gate callers are runtime-capture identity,
  metadata enum reads, and consumers of pinned methods, code windows, field
  offsets, registrations or native contracts. Current-export Story classifiers
  validate their own tables, object-index stage signatures and fingerprints.
- **`inputSetSha256` identifies one audit run, not the game build.** It hashes
  the exporter binary and absolute asset roots, so it is only a join key
  between one run's VFS summary, ledger and corpus reports. No contract is
  gated on it and tests must read it from their fixture, never hardcode it.
  Whether a contract applies is decided by its `nativeInputs`.
- Hash checks survive only where git cannot guard: the installed build against
  `nativeInputs`, native code bytes against a recorded window or body hash,
  installed game files such as iFix patches, and a generated report against
  its inputs.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- A typed usage context and its registered entry do not establish a different
  actual call target. Keep that registration as provenance until an independent
  body/ABI/caller join proves the target. An exact scalar read and its typed
  wrapper-property store can establish stored-byte composition separately;
  it does not prove generic sharing, internal field layout or live dispatch.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses and inventories belong in
  reports or versioned contracts.

## Re-resolving a native identity after a client update

A contract pinned to a superseded build is not evidence that its subject is
gone. Only the managed name survives an update, so a stale contract is
migrated by resolving names against the selected build, never by carrying an
address forward. `scripts/game_data/il2cpp/method_resolver.py` owns that
direction and documents the three name classes that drift without a source
change (compiler-generated closures, Burst direct-call wrappers, recorded
display forms). A resolved body extent is the gap to the next method pointer,
an upper bound rather than a proven length; re-resolution restores identity
only, so the old contract's conclusions about the bytes stay unvalidated until
re-derived. Prefer build-independent claims contracts
(`il2cpp/body_claims.py`) for new consumer claims.

Fully qualified type names can repeat in different managed images, including
IFix wrapper owners. A name-keyed dictionary's selected row does not establish
the concrete owner. Enumerate candidates, qualify the managed image and ordinary
signature, and bind the actual decoded call pointer to that method. Reject a
remaining ambiguity; a name-only claim is supplementary to this identity join.

[`il2cpp/unwind_chains.py`](../scripts/game_data/il2cpp/unwind_chains.py)
reuses the declared PE exception directory and complete parent triples to
establish selected-primary code-range membership. The
[AMD64 chained-unwind format](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64)
allows multiple and noncontiguous fragments. Membership does not prove a
managed control-flow path, unwind operations or fixed-allocation consistency;
the owning consumer still checks its complete byte program and frame conditions.

Native data-flow checks must retain instruction width and register writes,
not just the printed mnemonic. The shared x64 subset distinguishes the
ordinary 32-bit `FF` INC/DEC forms from their REX.W 64-bit forms and from
the 64-bit default of near indirect CALL/JMP and PUSH. An INC/DEC register
destination invalidates its previous pointer or argument origin, including
when the write is to its 32-bit alias. Unsupported decorated/extended-index
forms remain one unknown instruction boundary, and truncated addressing
bytes cannot supply a call or field witness. These decoder facts establish
neither a complete method path nor the runtime value of a loop counter;
those require the owning consumer's independent byte and path checks.
The admitted register-only 16-bit AND-immediate form consumes its two-byte
immediate without swallowing following instructions and preserves the upper
48 bits. Its conservative full-register origin invalidation does not assert
zero extension. Other decorated immediate-group forms retain one unknown
boundary, including their actual immediate width; truncated addresses and
immediates cannot supply a witness.

RIP-relative operands of the admitted immediate groups use the end of the
entire instruction, including the immediate bytes. The shared subset retains
the full address/immediate boundary for `80`/`81`/`83` and `C6`/`C7`, refuses
truncated forms, and keeps unsupported prefixes or extended SIB indices
unknown. An admitted REX.W `C7` sign-extends its four-byte immediate into the
64-bit operand; an ordinary `C7` register write clears the upper 32 bits.
These facts establish the selected operand address and stored width, not
the identity or runtime value at that address.

The selected [`MOVZX` subset](https://cdrdv2-public.intel.com/782151/253667-sdm-vol-2b.pdf)
records its eight- or sixteen-bit source and
zero extension into the ordinary 32- or 64-bit destination. Admitted register
sources retain their actual byte or word name, while conservative origin
invalidation prevents a partial source from carrying its full pointer origin.
The same rule applies to memory sources: a byte or word read cannot restore
the full pointer previously spilled to that stack slot. Exact read operands
and widths remain available to independent typed consumer checks.
Unsupported extended SIB indices, destination prefixes and legacy high-byte
forms retain one complete unknown boundary
and invalidate the destination's prior origin. They cannot establish a
printed source register or a field-flow witness. Truncated addressing is
terminal unknown data; a consumer needing another form must prove it
independently before using its register or memory meaning.

The admitted ordinary MOV/LEA and SSE memory forms retain REX.X's SIB index
extension independently of REX.B's base extension. R12 is an index when the
extension bit is set; it is not the absent-index encoding. In the selected
64-bit address mode, an absent-base SIB displacement is sign-extended, and
incomplete SIB/displacement bytes remain terminal unknown data. These
[instruction-format rules](https://cdrdv2-public.intel.com/858446/253666-088-sdm-vol-2a.pdf)
establish the operand expression only. They do not name an indexed field,
prove array bounds or supply the runtime address; the narrower MOVZX and
decorated-group admission boundaries above still apply.
Address-size overrides of these forms remain unknown complete instructions,
with conservative destination-origin invalidation. They cannot reuse a
64-bit expression for wrapped 32-bit addressing. The admitted shift-immediate
form also includes its trailing immediate when calculating a RIP operand;
decorated, extended-index and truncated shifts supply no semantic witness.

An AOT body's `call qword [rip+disp32]` indirect slot is not a pointer but an
IL2CPP metadata **key**: `key = (prefix << 24) | (2 * index + 1)`, prefixes `0x60`
methods, `0xc0` methodSpecs, `0xa0` stringLiteral, `0x20`/`0x40` Il2CppType.
Decoding it names an otherwise unresolved call site;
`scratch/reverse_engineering/network_analysis/20261013T135400637/msgb1/dis_keys.py`
is the annotating disassembler.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. A verified outer VFS boundary proves byte identity and
availability, not the inner payload schema. The full outer VFS audit, Bundle
inner audit, Table dump and JsonData source/export join give a strong
structural baseline for the selected build. Named-schema coverage is narrower,
and no file count measures effective runtime consumers or behavioral/visual
parity. Current denominators live in the generated `reports/animestudio/`
receipts; per-family reader boundaries are in
[`game_data/extraction_payload_boundaries.md`](game_data/extraction_payload_boundaries.md).

Read progress in four layers:

| Layer | What is proved | Current boundary |
| --- | --- | --- |
| Identity and container | Source, overlay, package and logical-byte identity | Broadly recovered; live provider/root selection remains separate |
| Framing | Bounded records and exact consumption of their owning bytes | Strong corpus coverage, with concentrated partial families |
| Named schema | Independently authenticated field names, types and recursive children | Broad coverage; Buff and Skill concentrate the remaining recursive work |
| Consumer meaning | Authored ownership joins and selected native reads | Selective proofs; activation, live values and output remain separate |

Behavioral and visual parity need their own output evidence. A bounded retained
packet replay does not establish general renderer or gameplay parity. Use the
current outer and family receipts for coverage counts; a matching native-input
gate establishes contract applicability, not a fresh corpus sweep.

Current position of the families with active recovery:

- **JsonData.** The authenticated registry (`scripts.game_data.jsondata_corpus`)
  joins every current logical file to the export by path, length and MD5, and
  assigns each a terminal status. Most families close exact named schemas to
  EOF. LevelScriptData, LevelScriptTemplateData and SkillData keep a
  bounded-partial residue; BuffData has an exact named subset while the rest
  stays format-framed. Shared child grammars and generated-reader routes are
  recovered across the residual corpus before another runtime capture is
  considered. Targeted replays measure advancement separately from whole-file
  closure; only the combined gate publishes current totals. Exact storage remains distinct from
  runtime use. See
  [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
- **LevelScript.** The sequential owner reader continues through action maps,
  task maps, NPC, enemy and module dictionaries at exact cursors. Each union
  route moves through three steps: an isolated contract and validator,
  registration in the shared ActionMap/layout with production replay, and
  whole-owner closure only through the full JsonData gate. This is
  stored-schema recovery; no stored action proves runtime execution.
- **SkillData.** Native-gated readers close the reviewed ActionGroup interiors
  and rejoin the selected top-level terminal. The live target-set cursor
  capture is complete and loss-free: every reviewed ambiguous source and the
  positive control verify, so no further capture is needed for that set.
  Purrche's below-Potential-3 branch was unavailable on the user's save; its
  stored source and native logic are recovered, its execution is unobserved.
  Separate Wulfa and Seraph cursors, plus one grouped four-source Zhuangfy
  capture, now have source-scoped complete stored-frame joins. Five Zhuangfy
  action routes are admitted to the shared reader under current native gates.
  A later loss-free grouped Lizhiyan/Pograni cursor now names fields 43-47
  and matches both selected static ActionGroups and top-level continuations
  through physical EOF. Both now close under the complete family gate.
  Complete framing remains distinct from recursively named child schemas:
  the registry publishes `storedFrameExact` while `namedSchemaStatus` remains
  unproved where complete child receipts are absent. Known fields are retained.
  Shared Skill routes can reuse Buff-owned action readers only after their own
  dispatcher, wrapper, source order and nested typed calls are proved. A shared
  union tag alone is insufficient. These admissions reuse
  source-scoped terminal evidence after current provenance revalidation and
  need no duplicate framing capture. Selected
  diagnostics alone never replace the family gate. Remaining action tags are
  ranked by corpus coverage and reusable child proofs before selecting a new
  observer.
- **BuffData.** A 30-field root reader closes selected cohorts from byte zero
  through source ID and physical EOF when every reached child has a native
  receipt; `scripts/game_data/memorypack/buff_corpus.py` combines the reviewed
  root, sole-CreateBuff and selected-source admissions with their child
  receipts. Selected positive-heal claymore, BreakPassing event, and equipment
  suit attribute/damage sources now compose to exact EOF under the complete
  family gate; their local diagnostics stay nonpublishable alone. Registry
  publication requires fresh canonical export replay. DataPair lists and the
  shared AttributeModifierData collection now use forward readers rather than
  historical candidate co-occurrence restrictions. Residual ranking excludes
  already exact roots and distinguishes proved children from a still-unproved
  parent composition. Shared event-map actions now compose the reviewed
  damage-mask condition and main-character target condition, plus the advanced
  Buff-ID condition's independently proved BlackboardString subtype list and
  GameplayTagQuery. DirectionSettings now composes independently owned source
  and target references recursively; Selector postprocessors compose Projection,
  shapes, ExcludeTarget's recursive target, PriorityFilter's BuffFindSettings
  and ShuffleTarget's concrete BlackboardInt through separate typed parents.
  CircularOrderSort and NavMeshPathPositionProcessor add owned generated-setter
  transfers, typed scalar/target children and explicit primitive cursor reads;
  their stored declarations do not establish ordering or navigation effects.
  Positive Timeline/ForceSync source elements now have independent buffered
  cursor and ordered owned-field programs; original-span element receipts
  deliberately leave nullable runtime adapters, positive lists and root
  admission open.
  Their separate static composition now proves original-type adapter and
  wrapper-formatter registration, concrete constructor contexts through shared
  code thunks, typed GetValue/formatter forwarding and the root's identical
  Timeline list carrier. The separate reference lane proves the buffered FF
  null branch's complete cursor accounting and original output clear. Its
  class-owned ABI distinguishes the non-null helper's by-value wrap from the
  byref original output and reader. Its selected non-null helper now proves
  the saved Reader reload, preserved input wrap slot, distinct owned generic
  parameters, actual second-interface lookup and concrete formatter/getter
  fallbacks through original output and return. This remains conditional on
  compatible runtime contexts and the reviewed provider result. The separate
  positive parent proof now preserves its own Reader/output saves, wrapper-owned
  Activator MethodInfo and created local through child dispatch, conversion and
  both complete returns. Provider and Activator MVARs have reciprocal ownership.
  The concrete wrapper metadata selects the creation branch when runtime
  attributes describe that same class; the abstract direct-zero alternative
  cannot replace it. The actual CreateInstance call matches its registered
  shared entry. A class-key prefix independently kills unused incoming byref
  bits before use, without proving helper purity. Runtime class/metadata parity,
  full creation/cache/provider effects remain open. A separate source-wrapper
  proof now consumes the buffered FF byte, updates all four cursors and clears
  the wrapper byref through a complete return under the disabled-barrier state.
  Each selected concrete constructor preserves its receiver and stores its
  original-type allocation result into the owned instance field. Allocation
  contents, actual constructor invocation and active barrier behavior remain
  conditional or unresolved; original nullable child/cursor composition is open.
  The same positive Timeline/ForceSync source-field programs now continue through
  complete no-call/no-object-write/no-Reader-write return suffixes, with exact
  stack and nonvolatile restoration. This closes their earlier final-store
  boundary while retaining the disabled-barrier and typed-call conditions.
  Timeline's child calls carry separately closed ReadValue contexts. Their
  actual helper now has a complete selected Reader/local-output/return proof
  with reciprocal provider/formatter parameter ownership. Its separately
  registered Object entry differs, leaving named body identity open. The
  dispatcher matches the original adapter's first optimized case and inlines
  it; complete selected FF and positive clear/conversion paths are separately
  proved. This cannot reuse the ordinary fallback for that outer call. Sequence
  concrete adapter/wrapper registration, closed constructor thunk and typed
  source forwarding are now independently joined; its nested formatter/getter
  pointers use the ordinary fallbacks. The actual formatter helper now has an
  independently required same-MethodInfo key/class and complete typed-reference
  return proof for both ReadValue and list control. The selected initialized
  cache and correctly typed normal returns remain conditions; indirect global
  calls and cache-miss effects remain unproved. Physical wrapper GetFormatter effects,
  original child cursor composition and complete root composition remain open;
  no child grammar, positive list or root is admitted by it.
  Sequence's inline action-array source now has complete selected FF,
  null/empty array and single/repeated positive-element programs through return,
  with owned ReadArray overload/element-context joins, direct cursor transfers,
  same-Reader child destinations and both normalized flags. Typed helper/child
  returns and compatible runtime context selection remain conditions; actual
  Empty/allocation identity/effects and child cursor composition remain open.
  A selected buffered existing-list loop now proves the signed count/cursor,
  null temporary reference, element dispatch, reference append and saved-count
  back edge. The root's actual ReadPackable helper now has a complete selected
  same-Reader/initialized-output/typed-dispatch/return proof, and a local caller
  joins that return to the owned timeline field. Complete null/new-list paths
  reuse the proved loop; the actual capacity constructor joins its owned class
  contexts and preserves the capacity/allocation result through return. Open
  generic field offsets do not name its observed reference slot. Fresh-list
  zero count, array capacity, allocation/static-field effects and runtime
  selection remain conditional or unresolved. Original element cursor
  composition, full root entry/tail and physical span/provider effects remain
  open. The actual reset helper's index-zero/version update is independently proved;
  initialization and actual runtime selection are unobserved.
  Nullable child framing now joins the actual ReadValue helper, concrete
  forwarding and complete source returns: FF advances one byte; the positive
  adapter peeks without consuming the source header. The direct Timeline,
  Sequence and ForceSync overheads compose with their child advances, and an
  audit checks the unchanged certified original storage spans against these
  equations. Callback native advances, string-helper cursor/global effects,
  stable Reader aliases and full list/root composition remain distinct;
  source-only receipts gain no admission from the arithmetic check.
  The action base and generated base wrapper are independently authenticated as
  abstract. The original adapter's `InitEager` allocation/context/key/RegisterWrap
  flow and concrete union formatter registration are now proved. The actual
  tag helper has complete buffered one-byte and three-byte UInt16 paths plus
  the high-marker zero/false path, with all four cursors and restored state.
  Reserved markers gain no canonical null admission. The selected abstract
  adapter branch now initializes a zero wrapper local without a direct Activator
  call and preserves the same Reader/local through both complete child-output
  returns. The union's AL-false branch clears its wrapper output and returns
  through an actual jump to the independently proved disabled shared barrier.
  Matching runtime attributes and initialized contexts remain conditions.
  The action adapter's declared virtual slot and void/byref ABI now join the
  exact original element, reciprocal generic parent and owned indexed array
  output through the
  [callback binding contract](../scripts/game_data/contracts/buff_action_array_callback_binding_native.json).
  The abstract base's raw slot remains structural-only. A missing unique closed
  compiled registration does not exclude runtime generic inflation; provider
  cache identity and the live vtable/MethodInfo still require independent proof.
  The [registration-state contract](../scripts/game_data/contracts/buff_formatter_registration_state_native.json)
  now connects the complete RegisterWrap caller and public Type lookup to their
  actual dictionary/result helpers. Setter and named lookup share the exact
  closed dictionary context and static address expression; the selected named
  hit returns its full reference output. Dictionary effects, physical inlined
  lookup control and runtime state remain open, including provider loads from
  storage without on-disk backing. The
  [dictionary lookup contract](../scripts/game_data/contracts/buff_formatter_dictionary_lookup_native.json)
  now checks the actual named caller target, sign-cleared word/remainder index,
  unsigned guard, finite node route and full hit/miss output through restored
  returns under explicit storage/helper/disabled-barrier conditions. Anonymous
  slot meanings remain structural; hash/equality helper semantics, setter
  mutation and live cache/class/callback selection are still unresolved.
  The [comparer-dispatch contract](../scripts/game_data/contracts/buff_formatter_comparer_dispatch_native.json)
  now connects the actual UInt16 selectors, unsigned record scan, signed offset
  arithmetic, function/context pair and complete ordinary/specialized returns.
  Runtime interface/slot identity and opaque object/payload child semantics
  remain open; compiled target declarations do not establish live selection.
  The [preparation/fallback contract](../scripts/game_data/contracts/buff_formatter_dispatch_fallback_native.json)
  separately proves the actual load/tail transfer, stored-byte gates, original
  receiver/context/UInt16 forwarding and conditional nonnull result returns.
  The resolver-child control contracts (scan, carrier conversion,
  relation, relation imports), selected Baselib export/import and complete
  semaphore/thread programs, and their open joins are summarized in
  [serialization_memorypack](game_data/serialization_memorypack.md); owned
  bytes alone do not establish executable code. Baselib's retry carries an
  adjusted DWORD request; a live binding, finite retry or original requested
  release total is not inferred. Its separately selected file participates in
  the native gate alongside GameAssembly, metadata and UnityPlayer.
  The context owner separately proves the first complete byte-count/array/flag
  program, both complete owned CFGs and conditional incoming-address handoffs.
  Count increment can wrap; saved-address equality does not prove pointed-slot
  contents unchanged. The direct copy target joins the existing bulk-copy
  entry, while caller-specific capacity/effect composition and the second
  body's complete typed fields remain open.
  The allocation owner joins that byte-count/eight-stride call to complete
  reservation, unsigned space/refill, metadata/node writes and restored
  clear-tail arguments. Its size product/reservation is bounded in this
  caller domain. The [clear-tail contract](../scripts/game_data/contracts/buff_formatter_clear_tail_native.json)
  separately proves complete fill/REP control, guarded tables, value lanes,
  byte ranges for every loop count and normal return of the incoming cursor.
  Rechecked parent flows join that cursor to the receiver's stored array
  field and the caller's zero-fill range. Writable storage, CPU/DF/stack and
  noninterference conditions still apply; valid capacity, live allocator
  protocol/callee, actual execution and visibility remain open.
  The [named class-ancestry contract](../scripts/game_data/contracts/buff_formatter_class_ancestry_native.json)
  now joins the complete `il2cpp_class_has_parent` program to that first
  context entry and the same parent/depth/array/ready fields. Its unsigned
  depth-indexed pointer equality supplies a direct ancestry-array consumer;
  closed named getter entries also anchor name, namespace, parent, element
  and embedded type fields. Coherent valid storage, prepared positive depth
  and normal ABI returns remain conditions; live receiver identity,
  initialization, slot mutation and capacity are not established.
  The [incoming-address contract](../scripts/game_data/contracts/buff_formatter_incoming_address_native.json)
  additionally authenticates the complete helper CFG and explicit writes,
  including vector/byte/locked forms, its RSP/RBP saved homes and conditional
  original-address register values at all proved call sites. Explicit and
  implicit stack writes avoid the saved homes; unknown aliases and child
  writes still prevent pointed-slot or fresh post-child pointer equality.
  Normal AL zero/one does not prove initialization success or runtime identity.
  The [named class-fields contract](../scripts/game_data/contracts/buff_formatter_class_fields_native.json)
  additionally joins closed type-flags/blittable entries and the complete
  has-references, field-iterator, preparation-bridge and recursive preparation
  programs to the same input-helper callee. Its bit replacement matches the
  named blittable bit; the fields base/count/stride have a direct named
  iterator consumer. Iterator writes followed by receiver reloads and
  post-child context loads stay fresh. Field storage construction, pointed
  slot effects, alias/noninterference, actual receiver identity, initialized
  capacity and recursion still require evidence.
  The [generic field-construction contract](../scripts/game_data/contracts/buff_formatter_field_construction_native.json)
  proves the complete generic child, named record getters, inline reservation,
  full explicit record coverage and the actual shared-clear return/zero-fill
  join under its stated conditions. Source name/offset/trailing-word reads
  are fresh after the type child; the saved original receiver becomes the
  record parent. Its saved source count does not directly assign the receiver
  count consumed by field iteration. That count join, trailing-word meaning,
  complete typed ordinary/auxiliary construction, child alias/slot effects, valid capacity
  and actual type/receiver identity remain open.
  The [ordinary/auxiliary field-setup contract](../scripts/game_data/contracts/buff_formatter_field_setup_native.json)
  checks both complete owned control/store/frame programs and selected
  count/home/reference/ready projections. Allocation and post-allocation
  loop counts remain separate fresh reads. Reusing a child's own RDX home
  as a DWORD counter does not describe its passed pointer's target. The
  auxiliary named reference bit joins parent/receiver reads conditionally;
  its ready write precedes later layout children and cannot prove their
  completion. Remaining typed effects, coherence, capacity and runtime
  joins stay open despite complete decoding.
  The [metadata creation count-flow contract](../scripts/game_data/contracts/buff_formatter_class_creation_native.json)
  checks a complete owned creation candidate and current named metadata
  count words. Signed source-address arithmetic, saved allocation/result
  registers, a fresh source-word copy into the named count offset and the
  normal allocated-result return are proved under their conditions. The
  allocation and copy dominate normal local returns. Runtime source-table
  pointers, valid index/storage, live class/cache/preparation identity and
  later count coherence remain unresolved; direct store coverage does not
  exclude child or alias mutation.
  The [generic creation count/cache contract](../scripts/game_data/contracts/buff_formatter_generic_creation_native.json)
  checks the complete code/table partition, guarded targets, stores, frames
  and selected register origins across the possible graph. The shared getter's
  fresh count word reaches the saved allocation, which also stores the incoming
  receiver in its generic link. Cache exchange overwrites the saved pointer;
  the non-null return uses a fresh cache reload whose equality with the
  allocation/publication is unproved. Existing-cache and null-source returns
  bypass creation. Live preparation identity, later count coherence, child
  aliases, synchronization/capacity and recursive termination stay open.
  The [source receiver resolution contract](../scripts/game_data/contracts/buff_formatter_receiver_resolution_native.json)
  joins closed nullable/pointer-index leaves to the complete owned cache
  resolver and actual metadata constructor. Valid selected record offsets
  round-trip through the signed reciprocal index calculation under matching,
  stable header/base reads. The same signed index and normal constructor
  result reach a fresh cache array; return uses another fresh array/element.
  Cache-view/count equality, live pointer/class identity, index validity and
  synchronization remain open, and leaf instruction closure does not infer
  unwind ownership or original-receiver null handling.
  The [metadata initialization owner](../scripts/game_data/memorypack/buff_formatter_metadata_initialization.py) joins the loader result to those header/base cells and the conditional section-size allocation result to the resolver cache cell; loaded-file identity, allocator outcome/capacity and later global stability remain unresolved.
  The [metadata loader owner](../scripts/game_data/memorypack/buff_formatter_metadata_loader.py) checks complete loader/path-helper control, literal descriptor arguments, close/error import declarations and conditional zero-or-saved-mapping-child returns; closed dependency transfers infer no ownership, and final path/file identity and live child effects remain open.
  The [metadata mapping owner](../scripts/game_data/memorypack/buff_formatter_metadata_mapping.py) checks that actual tail target's complete control and registration-slot flow: normal return is zero or a fresh post-registration slot value, after subtraction and mutable-slot forwarding. A nonnull view-child result does not prove final-return equality or validity; aliases, mapped-file identity, synchronization outcomes and retry termination remain open.
  Actual virtual callback/class/provider selection, positive union/child cursor
  composition and global effects remain open; static registration does not
  select a runtime object.
  The selected new-child PickTarget union route now joins its current UInt16
  table index, complete null-cast return, closed wrapper ReadPackable context
  thunk, actual shared helper and full wrapper output/barrier/caller return.
  The same Reader and generic parameter/local-output ownership are retained.
  Old bundle tag ordinals are not reused. The maintained PickTarget storage
  reader now joins its seven source results to inherited/concrete setters and
  the separately owned BlackboardInt and recursive TargetSettings children.
  BlackboardInt's complete ordinary program writes its key, flag and integer
  through the same closed int/int base; VAR indices are resolved through their
  owning generic container instead of being treated as argument ordinals.
  The complete corpus and independent original-element/root replays now validate
  that extension. Exact PickTarget action returns also survive as local receipts
  when their enclosing Timeline element refuses at a following action; this
  grants no enclosing list or root admission. Its named consumer independently
  reads the owned Data key, target and index and forwards the index to GetValue.
  Aggregate/key argument forwarding, evaluated index and target-group effects
  remain separate. Reused-wrapper paths, allocation/refill/error parity, actual
  array/provider selection and gameplay target selection remain open.
  The reached EffectLineCenter child now has independently validated current
  source/setter transfers across AbilityAction, EffectAction and its concrete
  Data. Its current inherited declaration includes `bigEffectTarget`, absent
  from the historical candidate. The complete buffered header and FF output-clear
  return are now proved, and its bounded recursive decoder composes independently
  owned target and effect-configuration values. Actual child wrapper instance
  types must match each closed source context. Original source-element replay,
  the complete current corpus gate and selected canonical root replay have now
  passed with prior admissions retained. The derived action closes additional
  source elements; related partial roots still stop at the positive Timeline
  list boundary. Enclosing list/root admission and observed effect execution
  remain separate.
  The independent consumer contract now proves the closed Data reference and
  fieldless derived receiver, complete preparation caller, conditional byref
  target substitution and disjoint aggregate-buffer forwarding to the complete
  Vector3 subtraction leaf. Under the unpatched caller and both getters' checked
  primary returns, center-position minus source-position is written into the
  unserialized `centerOffset`, distinct from persisted `positionOffset`.
  Ordinary parent `OnCreate` caches the same loaded configuration reference.
  Other getter/IFix paths, reference stability across the action lifetime,
  parent execution consumption and observed effects remain open. Separate
  current Data reloads are not assumed to denote the same object.
  Independent trail point consumers now prove ordered Single deformation and
  twelve-byte writeback, followed by conditional source copying, constructor
  reference stores and append/growth control. Whole no-resize copying requires
  stable source values and valid distinct-header/storage/capacity conditions;
  Selected small/snapshot/bounded-vector, REP and aligned temporal-loop Array.Copy
  paths now have conditional byte-preservation proofs, with explicit memory,
  overlap, runtime stride/selection and parent return/frame/bitset conditions.
  Non-temporal store coverage and ordering before following stores now also have
  an independent proof, now joined to the actual parent array-reference
  publication store and complete getter byte transfer. Old-point reads require
  actual publication visibility and observation, stable compatible references,
  live stride and the existing memory/frame/selection conditions; these remain
  unproved runtime selections. The complete backward-overlap program now also
  has a conditional byte proof, including delayed pipeline stores and every
  tail remainder. All selected copy programs now join the complete actual
  dispatch on one native image, with exact integer-domain coverage and both
  option-false fallthroughs checked. This closes conditional complete store-value
  coverage; only REP additionally requires clear DF, and non-temporal visibility
  retains its explicit boundary. Actual publication/read observation, live stride,
  general old-value preservation during resize, allocation/reference lifetime,
  renderer submission and the parent configuration join remain open. Details
  stay in the owning MemoryPack topic and reviewed consumer contracts.
  TickInterval's existing current Skill normal-source contract and shared Buff
  Sequence declaration provide a concrete parent/child recovery starting point.
  Canonical zero/FF Finder children now have an independent source/type proof;
  recursive Selector routing consumes it with fail-closed native gates.
  TickInterval's complete conditional caller, inherited/concrete setters,
  cached getter, FF return and formatter now join source returns to owned Data
  fields. Its separate helper composition now joins the full physical Sequence
  output and selected buffered primitive sources; the isolated stored-parent
  reader completely replays original parents with independent metadata-boundary
  agreement and unchanged recursive children. It supplies Tick and recursive
  native proofs separately rather than extending a cached validator return.
  The fresh zero-Finder family gate records complete-root gains without source
  drift or regressions. Tick's complete current new-child union output/return
  now has a separate reviewed proof, reusing the existing shared union facts.
  Recursive registration requires both independently owned packets and matching
  current wrapper/Data identities. Fresh complete native context, the full
  family gate and original recursive parent/enclosing source-element replay
  now pass after integration; original source identities and hashes are
  preserved, with no Tick-integration root gains or regressions. Previous
  cached evidence is not relabeled. Native action callback cursor equality
  and positive-list/root admission remain open, along with
  runtime context/provider selection and observed tick effects. The consumer
  lane must prove the generic Data reference and frame/counter/timer guards
  before stating scheduling behavior. The existing SSE lane decoder now
  completely decodes the selected OnTick body, including signed count-to-Single
  conversion; operand ownership and MXCSR/runtime selections remain separate.
  Its separate named consumer claims prove only the false-IFix getter's
  `AlwaysReturnTrue` policy. The strict closed-reference witness currently
  refuses the concrete suffix gap; OnReset uses an Int32-backed ResetReason
  enum, whose receiver/argument forwarding still needs proof.
  Hurt-animation curves share the same recursive Direction owner. Camera-control
  actions compose their named parent, AnimationCurve children and shared
  nullable string-list context; string interpretation remains conditional.
  Other reached children remain refusals until independently proved.
  Resource-cost, timed-marker, stack-storage and scalar-calculation
  parents now have named source/destination proofs and independent typed children.
  GameplayTag width admission requires an explicit closed unmanaged source proof;
    differing registered and optimized reader entries are authenticated separately.
    Skill cooldown, mode switching, super-armor checks and debug printing also
    have named source/destination proofs. Inline color storage requires its
    own source-copy, cursor and destination proof; object size alone is insufficient.
  Stored conditions still do not establish their evaluation.
  Positive damage, event-action and finder bodies retain
  their explicit recursive blockers.
- **Audio packages.** The complete available AKPK roster now retains sector,
  full-width key, language and package identity. Repeated typed keys and low-word
  collisions stay explicit; neither picks a runtime package or decoded file.
  This inventory supports corpus-wide byte and naming joins without another
  playback capture. See
  [`game_data/audio_overview.md`](game_data/audio_overview.md).
  The reviewed native bank loader now joins External Source IDs to descriptor
  cookies, and selected complete external rows have exact offline WEM/FLAC PCM
  comparisons across Vorbis and Opus. Native Event registry/queue transport
  and Play Action target lookup also have checked identity edges, and selected
  direct ordinary Event/Sound rows have exact package-to-FLAC PCM witnesses.
  Event-to-path eligibility remains
  conditional on the posted descriptor; managed queue lifetime, the live file
  handle and actual Event selection remain separate gaps.
- **ExtendData catalogs.** Both StringPathHash catalogs have current
  cross-format hash joins to VFS filename hashes and BundleManifest asset
  paths; the catalog writer and runtime lookup remain open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **CompressData / AI.** A selected native chain runs from a spawn record's
  template ID through `EnemyTable` to a formatted `AIConfig` load, and authored
  BehaviourTree identities join archive ordinals. No checked producer equates a
  SpawnerConfig library entry's stored `enemyId` with the protocol template ID,
  and live spawn selection stays open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **Video carriers.** Stored `PlayFmvAction.moviePath` values join installed
  Video files through a selected native `f_`/`m_` naming branch; that joins
  authored naming, not an activated scene
  ([`game_data/story_carriers.md`](game_data/story_carriers.md)).
- **Bundles.** Corrected AssetMap container paths resolve the former fallback
  residuals, and the CAB dependency sweep places every mapped external
  reference inside the BundleManifest dependency list; manifest-only edges and
  a live selected load stay open
  ([`game_data/unity_assets.md`](game_data/unity_assets.md)).
- **Unity and presentation.** Standard object and media decoding is established;
  prefab composition, material variants, Animator ownership and effect timing
  remain consumer joins. Retained ribbon output proofs apply only to their
  selected packets ([`game_data/unity_assets.md`](game_data/unity_assets.md)).
- **World.** DynamicStreaming's authored component ownership is recovered under
  its raw-source and template gates. Streaming still has anonymous subgraphs;
  Terrain texture-path bindings remain conditional on the selected resources,
  with channel meaning open; irradiance index ranges do not name record
  encoding or GPU interpretation. Their owning guides are indexed below.
- **Code and native I/O.** Decoded Lua and IFix instructions support static
  references and selected operand joins, while invocation and patch activation
  remain open. The static stream/read chain does not supply a live backing-file
  identity or full-buffer delivery guarantee. See
  [`game_data/ifix_patch.md`](game_data/ifix_patch.md) and
  [`game_data/native_read_path.md`](game_data/native_read_path.md).

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` stay visible and are never upgraded by a later name match.
- Runtime-mutable properties keep their authored initializer but are not final
  action targets unless later writes are excluded.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## Where the detail lives

[`game_data/README.md`](game_data/README.md) holds the four evidence levels,
the block-to-lane table and the file index. A claim may cite evidence only from
its own level or below; most recorded mistakes read a level-4 meaning off a
level-2 framing. Read
[`game_data/settled_and_open.md`](game_data/settled_and_open.md) before
reopening chunk slot typing or HIRC type coverage.

Per-build member orders live in `scripts/game_data/contracts/`; each reader,
gate and validator documents what it proves, and what it does not, in its
module docstring. What a decoded carrier proves about Story stays in
[`game_data/story_carriers.md`](game_data/story_carriers.md); what it means for
published Story stays in [`webui/story_recovery.md`](webui/story_recovery.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link keeps the earlier physical identity and is never replaced by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in
[`game_data/unity_assets.md`](game_data/unity_assets.md); Map publication
belongs in [`webui/map.md`](webui/map.md).

## Source graph

The canonical database is `reports/source_graph/endfield_source_graph.sqlite`.
It indexes evidence already produced by owning builders: a query and
provenance surface, never an authority that invents recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds keep only the exact AssetMap rows consumed by WebUI material,
shader, texture and FMV edges; full builds are for exhaustive PathID work.
Every edge keeps an evidence kind; availability, registration, address order
and mission context never become ownership or chronology. Before deleting or
renaming a generated report, search graph readers and rebuild the database if
that report is an input.

## Diagnostics

Use the closest owning report first: `reports/export/`, `reports/animestudio/`,
`reports/game_data/`, `reports/assets/`, `reports/audio/`,
`reports/source_graph/`, `reports/story/build/`, `reports/story/recovery/`.
Revisitable probes belong in `scratch/<topic>/`; disposable intermediates in
`tmp/<topic>/`.

## Recovery queue

The system work order above takes precedence when the goal is understanding
the game. The family list below is the format-recovery backlog, not a demand
to finish every stored field or runtime detail before explaining the system.
Offline work first; capture requests additionally obey the model-discrimination
criteria above.

Recovery work is corpus-first. Choose the next shared reader, child grammar,
provider rule or cross-format join by the authenticated files and distinct
stored shapes it can explain. A familiar character, filename or successful
playback is a representative fixture, not the unit of progress. Keep storage
coverage separate from runtime selection, ownership and output: closing one
runtime question may improve understanding without decoding another file.

- Start each batch from the owning current family receipt and ranked refusals.
  Prefer a shared dependency reached by many sources to another source-specific
  exception. Counts of first stops measure files that may advance; only a
  complete owner replay and family gate measure whole-file closures. Report
  both, and rerank when a newly exposed child becomes the next refusal.
- Compose independently proved child grammars into the shared reader, validate
  representative positive and refusing shapes, then publish the coherent batch
  once through its owning gate and page builder. Preserve exact, structural,
  conditional and unresolved claims in the published result. More probes,
  hook fields or successful checks are not coverage gains by themselves.
- Reuse retained captures, current stored bytes, native consumer proofs and
  selected offline decoding before requesting user work. A current source and
  dependency join can reuse a historical observation; repeating an unchanged
  source does not strengthen its stored grammar. An unobserved runtime branch
  stays unobserved without holding unrelated offline recovery.
- A capture request must state the missing reusable rule, the affected verified
  source cohort or explicitly runtime-only question, and why existing evidence
  cannot decide it. Name the distinct representative branches needed, the
  expected generalization boundary and the acceptance/stop criteria before
  collecting. Do not revisit one unique case for additional sampled fields
  unless those fields can decide a high-value shared join.
- Live capture tooling is internal-only; its repository boundary and the
  instrumentation prohibition are documented in `AGENTS.md`. Saved evidence
  remains useful only within its admitted format, consumer branch and source
  scope. Name the missing state transition or observation before requesting
  further evidence, and diagnose failed admission before repeating a recording.

1. **BuffData.** Rank residual recursive fields after excluding every admitted
   root. Reuse shared DataPair, AttributeModifierData, action and finder
   grammars only through independently proved parent typed calls. Ability and
   Buff event maps have different stored read orders despite sharing their
   SequenceActionData element. General input-list and sibling-action counts
   must follow the reader's bounded framing, not historical source-cohort
   restrictions. New compositions still require all thirty root fields,
   source-ID equality, physical EOF, the complete family gate and canonical
   export replay. Unproved positive-damage and finder/selector interiors stay
   explicit refusals; stored fields establish neither condition truth nor
   gameplay effects.
   Start with reusable event-action children and complete root composition,
   distinguishing an unproved child from a parent missing its composed receipt.
   The source-authenticated residual census owns changing cohort sizes; first
   obligations can overlap and reveal later blockers. The current family sweep
   includes the general shared event-map and AttributeModifier compositions;
   historical receipts from before those readers are coverage baselines only.
   The shared AnimationCurve reader now names wrap modes and Keyframe words
   through native source/cursor/destination copies; time-dilation and
   hurt-animation parents compose it with independently proved targets,
   direction and Blackboard providers. Shared directions now recursively compose
   independently owned source and target references; unsupported nested target
   variants remain refusals. Their compiled start/stop and animation calls
   are separate consumer evidence, with live argument ownership and effects
   still open. Reuse this curve child when recovering the remaining camera,
   movement parents instead of creating another anonymous
   curve grammar.
   Timed-marker creation and tag/object/physical-infliction conditions now
   compose independently typed providers, targets and queries. The query's
   explicit stack-output-to-field proof distinguishes its runtime extent
   from its variable-length serialized grammar. Reuse that distinction when
   recovering other output-buffer transfers; an instance getter after a
   typed source call is not another source read. Their consumer-call claims
   remain separate from argument ownership, quantifiers and evaluated effects.
   AddTag and ForEach now independently join source-proved tag elements and
   the shared recursive sequence owner. GameplayTag's inline wrapper requires
   an explicit reference-argument-to-receiver projection, rather than boxed
   offset coincidence. SpawnAbilityEntity now composes named recursive fields
   after separate raw12 return-buffer/registered-reader and inline raw16
   cursor/copy proofs. Stored names, targets and lifecycle flags still leave
   tag attachment, iteration order, entity ownership and live effects open.
   CameraImpulse now has independent parent, impulse-definition and inline
   envelope field proofs, including its inline vector cursor and complete
   provider-result-buffer copy. Curves and targets close on original spans;
   evaluated impulse shape, signal lookup and camera ownership remain open.
   NotNextCheckAction's four inherited stored fields now have an independent
   recursive action receipt outside the earlier selected damage pair. Its
   returned control result and the enclosing sequence's interpretation still
   require consumer evidence.
   Selected fieldless condition consumers now independently prove their closed
   generic data reference slot and incoming-instance path to a named target or
   mask read. Reuse this strict witness only for fieldless immediate subclasses;
   classes with their own fields, complete call arguments and evaluated mask
   predicates require separate proofs.
2. **LevelScript.** Native/source receipts feed the shared named reader. Only
   a complete owner at physical EOF can close the stored schema; the combined
   JsonData gate owns WebUI classification. The independent `levelscript_corpus`
   authenticates both complete LevelScript families against current logical VFS
   bytes and existing exports without Buff/Skill family receipts. It retains
   the native, CLI/chunk and complete raw-package reader gates, and cannot
   replace the combined registry or a WebUI publication. Saved family receipt
   verification closes its logical-read interval with physical input and
   overlay/path-set rechecks; publication also rechecks physical fingerprints
   after its final logical reads. A changed input rejects the new result and
   preserves the earlier successful receipt. Complete-reader drift can occur
   with unchanged native and VFS bytes when another raw-format lane adds a
   source or contract. A finished decode sweep from that refused run supplies
   no new published counts; the retained receipt still belongs to its earlier
   reader scope. Independently validated targeted results keep their own
   narrower evidence boundaries. `levelscript_receipt_compare` checks saved
   complete artifacts against their supplied hashes, compares identical source
   and selected-native identities, and rejects recorded schema regressions.
   A retained CLI path can change the audit-run identity with the same logical
   source bytes and selected native files. Comparison across those runs needs
   explicit opt-in and records both audit identities; complete path sets,
   each source's length and hashes, native identities and recorded named EOF
   still have to agree. This does not authenticate either run as current.
   Decoded rows must record named EOF; partial cursor changes are not measured.
   Its historical comparison does not authenticate current inputs or carry
   either receipt's reader scope into a later run. The independent
   `levelscript_param_value_native` consumer authenticates selected closed Int32
   evaluator entries, physical caller targets and explicit byref output. Its
   constant path copies the compatible parameter's DWORD through the caller
   local into the Int32 return; alternate selected paths retain the incoming
   fallback. Generated typed wrapper setters provide a conditional slot view.
   These proofs do not establish runtime receiver/provider selection, close a
   stored formatter cursor or authorize a new serialized source alternative.
   The separate `levelscript_long_param_value_native` named claims are evaluated
   against the explicit selected build, retaining complete Int64 fallback and
   output bits. Its generated typed setter view and ordinary byref output join
   the same concrete parameter definition; reciprocal class/method variable
   ownership and sole-argument arity are required. The independent Boolean
   consumer proves an unchanged single-byte constant transfer and complete
   caller return, without assuming that the storage byte is normalized to
   `0/1`. Its success byte is distinct from the transferred value. The scalar
   consumers share declared-type primitives; the Boolean and Int64 readers also
   share qualified registration and generated wrapper proofs, while their
   widths and control programs remain independent. Runtime selection and the
   stored cursor join stay unresolved. A changed unprovable claim is pending
   review.
   The Single variant additionally requires the complete primary/cold unwind
   join and actual cross-fragment branches. It preserves the original low
   Single fallback bits or the current local output, including the full XMM6
   restore; constant transfer and success remain separate, with no arithmetic
   or conversion on those selected transfers.
   A separate `levelscript_long_param_storage_consumer_native` composition
   cross-joins the validated stored Int64 wrapper and named evaluator through
   actual concrete holder/getter/setter identities and disjoint field byte
   intervals. Only its ready `CONST` path transports the stored constant to
   the full-width return. The output-slot wrapper, holder and constant/source
   storage must remain compatible and stable throughout field population and
   use; opaque callees and concurrent writers are not proved harmless. The
   actual UTF8 dependency and selected Unity image are authenticated alongside
   the native pair and proof sources. This conditional association does not
   establish runtime object/provider choice or positive enclosing owner
   admission.
   The separate global-variable callback proof joins fresh Param field loads
   and actual loaded generic contexts to two signed Int64-to-Single conversions,
   the ordinary comparison request and a `ConditionResult` enum setter request.
   Its complete selected original paths retain the full frame. The explicit
   byref event QWORD remains anonymous because the generic declaration does
   not prove concrete field placement; shared enum implementation compatibility,
   MXCSR conditions, opaque comparison/setter effects and live event order
   remain separate obligations.
   Failure-companion publication
   also rechecks the current reader path set and output/input aliases; an
   unsafe companion stays untouched and the CLI retains both the original
   failure and the publication refusal. Closing an action may
   expose a later first stop. Rerank with
   `scripts.game_data.levelscript_first_stop_census` after a gate, then recover
   the highest-value refusals in validated batches. A reached unsupported module
   is ranked by its raw tag/member count and current authenticated union type,
   with its source key/index/offset retained separately. The union type names
   the selected stored alternative; it does not supply the missing formatter
   grammar or an expected member count. Unlock, travel-pole and
   laser-event headers, string/entity getters and click-enable inputs now have
   reviewed stored routes. These compose through the existing typed child
   grammars; event activation, resolved outputs and provider/cache selection
   remain open. Damage-event filters, integer-list getters and movement and
   navigation stop inputs now have independently reviewed parent routes too; complete
   owners still require EOF, and a closed route can expose a later module gap.
   System-unlock override and duration-based rotation routes also retain their
   named operands and separately authenticated enum backings. The corresponding
   unlock-override removal and the enemy-patrol and pressure-board-sequence-failure
   headers have separate parent reader proofs. The module output parameter is
   only a source selector and path, not a serialized manual module value.
   The spline-movement route now composes an independently authenticated
   `Param<SplinePtr>` child: its constant contains one four-byte signed ID,
   followed by source selector/reference/path fields. This is a stored
   parameter identity, not a resolved spline or observed movement. Reached
   terminal suffixes with opaque prefixes retain their partial classification.
   CameraShake stays
   refused until its configuration wrapper's owned value slot, string store and
   optimized final-path receiver have an independent child composition proof.
   The same authenticated first-stop census also supports
   `LevelScriptTemplateData`, with separate owner and report identities;
   template property/task refusals retain their diagnostics. A replayed EOF
   from a prior partial cohort remains provisional until the complete gate.
   GameCondition routes have their own dispatcher and native gate. The union
   atlas keeps them separate from Action and server-condition routes even when
   numeric tags coincide; a type-table cell address is not the dereferenced
   type pointer. Atlas publication rechecks the selected native pair and proof
   sources, preserving its prior report on a refusal with contract/row context.
   Contract bytes read during the audit must match its initial proof snapshot;
   the output cannot alias a contract, proof source or selected native input,
   including through file identity. Repeated physical branch/usage bytes do not
   merge independently qualified dispatcher/tag proofs.
   Promotion rules and wire conclusions live in
   [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
3. **SkillData.** Historical cursor receipts can be rebound only to unchanged
   logical sources under current parser/native provenance and a complete corpus
   gate. The positive control must retain its previous claim. The verified
   source joins need no duplicate framing capture. Shared action grammars enter
   through independently authenticated dispatcher, wrapper and child-context
   contracts, including reuse of Buff-owned readers.
   Their ActionGroup closure still requires a source-bound terminal selection
   for complete stored framing. This does not prove recursive field naming:
   anonymous children and missing naming receipts remain explicit even at EOF.
   A complete family report owns framing promotion; a sparse report or a closed
   first ActionGroup does not classify the remaining corpus or top-level
   continuation. Rank the residual distinct
   action stops after publication, and reuse authenticated stored framing for
   selection-only replay when its current dependency closure still matches.
4. **Gameplay formulas.** Selected damage/Poise evaluators and callers are
   proven statically ([`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md));
   receiver identity, live invocation, subtype selection, patch state,
   provider values and final damage remain unresolved.
   Selected named numerical paths also preserve the actual rounding order:
   some multiply in Single before widening, while others widen before a Double
   product or round an intermediate Double to Single. Typed fields and named
   getter ABIs identify the inputs, but getter internals and live values remain
   open. These conditional rules cannot be replaced with algebraically similar
   real-number formulas; their floating environment and normal completion are
   explicit conditions. A branch-linked physical code range supplies byte and
   control-flow evidence, not a shared managed unwind identity.
   Damage snapshot consumers additionally have build-independent named claims
   and a bounded consumer program. Under its selected false-patch and snapshot
   guards, the incoming instance's cache and incoming index reach a closed
   Double getter, whose normal return reaches the complete CalcResult output.
   Producer-to-consumer index/value correspondence remains unresolved; this
   consumer path is not a complete snapshot formula. A
   separate simple producer fragment transfers the widened scalar-times-attack
   value, cache and closed Add context to a compiled helper. That physical target
   remains distinct from the registered Add entry. Its selected physical fast
   path separately proves an eight-byte store and anonymous counter/count
   updates; the consumer's physical getter checks its bounds and returns the
   corresponding eight bytes. Their value correspondence is conditional on
   the same receiver, array, index and unchanged storage. The guarded producer
   reset path writes zero to that same anonymous count slot; a null selected
   target instead returns without those stores. These physical proofs do not
   establish a general List implementation, actual append/index selection or
   runtime snapshot execution.
   Constructor and OnCreate proofs separately connect typed allocation requests,
   the incoming action cache pointer store and the snapshot entry. The tail
   helper has only a bounded reachable-entry proof; pointer preservation needs
   its actual derived write range to be disjoint from the field and normal,
   noninterfering execution. The zero snapshot flag skips an append request and
   reaches the shared Int32 iteration increment, without establishing cache
   order or consumer-index equality. Separate checked connections now join zero
   initialization, a positive signed bound and the selected unit/skip/simple
   backedge. Under every selected guard, normal returns and valid noninterfering
   storage, a conditional compact-cache recurrence counts simple appends rather
   than source iterations; a prior skip makes those positions differ. Actual
   count/array/action-slot disjointness and the consumer's incoming index are
   still unobserved. Runtime ABI gates inspect raw type records
   as well as names, since names alone discard reference qualifiers.
   A separate ByType caller path now forwards its incoming Int32 index and unit
   reference to the normal consumer's exact ABI slots, then returns its low64
   result bits through complete MOVQ transfers and an owned return path.
   Unnamed predicate calls supply only selected zero-AL guards. The actual
   ProcessDamage stack-probe helper independently preserves RAX on its checked
   complete normal graph; page-write/frame disjointness and normal execution
   condition its restoring return and the caller's allocation arithmetic.
   Neither proof establishes ProcessDamage's later frame continuity, local
   index writers or correspondence with the compact cache.
   Independently checked ProcessDamage fragments also transfer an anonymous
   local Int32 index to the normal consumer, preserve its returned low64 bits,
   and join selected modulo-32-bit increments to one signed bound guard. The
   actual collection target's complete normal path checks unsigned bounds and
   returns an eight-byte indexed load. Its caller's static context separately
   requests `List<DamageUnit>.get_Item`; the folded Object implementation and
   an absent registered closed entry remain distinct. Compatible live context,
   valid derived storage, returned Unit identity and continuity between the
   independently entered fragments remain conditions or unresolved joins.
   A separate continuation reads the explicit Boolean output byte; its selected
   zero branch clears AL and reaches a complete restoring return epilogue.
   This conditional ProcessDamage false return does not determine earlier
   side effects, the other branch or final damage.
   The normal consumer's selected simple, non-snapshot path separately stores
   the ordinary Float provider result in the typed pack's `atkScale` field,
   loads an anonymous Double slot through its `attackerAttributes` carrier,
   converts the Float to Double and multiplies into the same CalcResult return.
   Heap layout, slot meaning, provider values and floating-point environment
   remain conditions or unresolved; this is not a final-damage formula.
   A selected MultiplyAttribute path separately checks ordinary Float
   multiplier/addition requests, the Double attribute request and exact SSE
   operand order into the same concrete CalcResult return. Its nonzero source
   branch replaces the incoming source and override array with the defender
   inputs before the common request. These are actual branch-linked physical
   ranges; adjacency does not establish a managed unwind family. A selected
   Poise continuation writes a full vector while replacing its low Double
   bits and preserving the freshly read upper bits, then copies the typed pack
   to a new buffer. The producing dispatch and debug targets remain opaque;
   the raw transfer is exact, while its named field view additionally depends
   on the stated boxed-to-unboxed layout adjustment, which is not independently
   proved by that transfer.
   The attribute-store path now joins its selected zero-index guard, array
   carrier transfer, ordinary Double request and old-index store into one
   conditional loop. The same actual provider's selected entry-to-cached-return
   path establishes receiver/index transfers and saved-state restoration;
   its nested cache/header names, other branches and live selection stay open.
   Compatible frame/storage, normal returns and noninterference condition
   both joins, without proving live damage or Poise settlement.
   The selected Poise modifier getter separately retains its direction enum,
   anonymous Double input, SSE comparisons/multiplication and normal returns;
   its caller converts the returned Double to Single before the setter request.
   The setter's selected tail compares the actual post-call Single carrier with
   the field value loaded at that point, then either writes the typed Poise
   field or returns without that local store. Raw comparison flags, including
   unordered floating-point cases, remain explicit. The anonymous helper is
   not identified as a clamp, and the no-local-store branch does not establish
   noninterference from earlier opaque calls or complete live settlement.
5. **World.** DynamicStreaming now has selected-native scalar and inline-vector
   component layouts and a direct authored MissionCondition string-slot join;
   Data exposes these only after native, current-roster and raw-byte checks.
   Authored RootComp-to-DataIndex-to-component-instance ownership also closes
   under the raw-source and template gates. Selected nested component DataGroup
   layouts now resolve explicit same-grid type/index/count spans with original
   parent and child byte ranges; cross-grid targets and control behavior remain
   unresolved. A same-source template-checked join additionally retains every
   authored RootComp candidate through the containing component to each indirect
   child; missing direct root references stay explicit gaps. Live child assignment, spatial
   units and live condition evaluation remain separate joins in
   [`game_data/world_dynamic_streaming.md`](game_data/world_dynamic_streaming.md).
   Selected Erosion consumers additionally connect PosList index/count to
   supplied-grid Vector3 axis values and the original typed List's value
   arguments, and return the stored CoreId getter result unchanged. The proxy
   reference ABI stays separate from ordinary primitives and the Unity value
   ABI. Successful insertion, runtime grid/file selection, CoreId target and
   spatial units remain unresolved.
   Selected MissionCondition consumers independently read State/IsSame from
   the same supplied record: literal IsSame equal to one selects equality to
   a provider Int32 value, and other values select inequality. The update's
   anonymous cache byte returns whether it changed, rather than the predicate
   itself. Valid selected-record/index arithmetic, stable frame/storage and
   normal calls remain conditions. A selected usage-cell/MethodSpec and
   reciprocal generic-owner proof now bind the provider's actual typed
   Dictionary<Int32,Int32> TryGetValue request. Its success path returns the
   Int32 output slot and its miss path zero; null receivers follow an error
   path. Key-carrier meaning, authored-group/cache ownership, live dictionary
   contents and condition truth still need their own joins.
   A separate source-owned key lane connects the authored Id consumer's
   GetStrKey returned Int32 to a bounded slot write and the query's matching
   dictionary-key read. Composition requires the same pool, slot selectors,
   returned storage and unchanged contents; key allocation, deduplication,
   stability and live dictionary ownership remain unresolved.
   Names-based ready claims separately connect the typed GamePlayer mission
   field to its concrete getter through complete selected entry and return
   paths. Under false patch checks, nonnull receivers and normally returning
   initialization helpers, the getter returns constant true. It reads no
   readiness state field; actual invocation and live readiness stay unresolved.
   Independent string-provider claims check the ordinary String length field,
   the complete selected typed Dictionary<UInt64,Int32> lookup request and
   its Boolean/referenced-output return. Null or empty input returns false
   and writes minus one. A separate Int32 counter resets negative input
   before incrementing modulo 32 bits; wraparound prevents interpreting its
   method name as global uniqueness. Hash computation, retained mapping,
   synchronization and live key identity remain unresolved.
   The complete selected GetStrKey paths separately return the successful
   lookup's Int32 output, the counter candidate sent to the same typed map
   setter, or minus one when an anonymous carrier lane is zero. The lane's
   zero test does not identify a span length or prove empty-string semantics;
   these paths require the original Boolean false and normal returning callees.
   Selected Mission/Quest callbacks additionally request their ordinary state
   getters and forward the returned Int32 enum bits to the concrete cache
   setter. The successful lookup's same local key reaches that setter and an
   enqueue request under explicit frame and noninterference conditions.
   The generic event carrier's instance fields remain anonymous; this does
   not prove its first pointer's named field, a retained live cache value or
   a condition's runtime truth.
   Independent string enqueue claims join a concrete lookup context to the
   same local value copy and an actual typed owner request. The copy's width
   does not establish the managed value's size, fields or full indirect ABI.
   A selected Mission getter separately returns its actual MissionData enum
   field or null-reference zero bits. Concrete getter-return enum declarations
   and aliases are authenticated independently; neither a zero miss nor a
   declared symbol is an observed live state or a universal cache label.
   A selected authored IsQuest result equal to one skips the concrete
   HashSet<Int32>.Add request; other returned bits send the preserved GetStrKey
   result to that request. Its typed context and bounded argument flow do not
   establish actual set mutation or runtime selection. The other branch clears
   only SIL's low byte, so it does not prove the whole ESI value is zero.
   Named pause methods independently prove selected byte writes to the returned
   MissionData's ordinary Boolean field. PauseMission writes one; the update
   handler's state-return-bits-not-two path copies the message field's raw byte
   without normalization. The state-two branch reuses SIL and is excluded from
   that pointer-preservation path. A predicate lookup and the returned write
   receiver need not be the same object; their join requires separate stable
   selection evidence. Live paused state, message execution, network effects
   and complete post-write return behavior remain unresolved.
   Quest pause recovery separately identifies named pause/listening requests
   and the message-field branch selecting StartQuest or PauseQuest. Selected
   MissionData methods write its typed dirty byte; RefreshIfDirty has a proved
   zero-byte early return and a guarded clear-byte normal return with opaque
   helpers and anonymous reference-lane integers. GetDisplayQuestIds requests
   that refresh and returns the same receiver's typed List<String> reference.
   These rules do not name anonymous lanes as list counts or prove collection
   mutation, complete refresh semantics or live display contents.
   Completion predicates independently return Boolean low-byte results:
   a null MissionData yields false, otherwise its typed state is compared to
   the authenticated Completed enum value; Quest completion compares the
   actual typed getter return to its own enum domain. All declared aliases
   remain visible. These complete selected normal returns establish neither
   full-register zero extension nor live completion, mission order or stable
   repeated lookup selection.
   Quest state-message blocks separately transfer the sender's ordinary Int32
   bits and String reference into a compatible, concretely typed QuestData
   receiver, and spill its old state before a new typed enum-field write.
   The sender field is not an enum; its bits do not inherit target-domain
   labels. The selected type-context request and actual constructor identity
   do not establish allocation success, dictionary ownership or mutation, or
   reachability from the complete handler entry.
   The selected GetQuestState value policy independently returns the direct
   compatible QuestData state or maps a compatible MissionData state after a
   returned-String request and length check. Comparison and output constants
   are authenticated in their respective enum domains, retaining aliases.
   Ordinary Dictionary representation and complete selected normal returns
   do not identify the String-sharing API, establish a mission hierarchy,
   prove stable record selection or observe live state. The owning
   `dynamic_quest_state_value_source_native` claims keep those joins explicit.
   The returned-String producer separately proves selected normal returns:
   an actual ordinary IndexOf result selects a Substring request on the original
   String, with zero start and that result as length, then the preserved local
   result reaches the return after an opaque request. Other selected paths
   return a compatible local or global pointer. The typed String methods,
   comparison-enum declarations and Dictionary<String,String> representation
   do not prove delimiter contents, cache semantics, String algorithms or
   hierarchy; `dynamic_quest_parent_string_source_native` owns this boundary.
   The independent `dynamic_quest_action_requests_native` consumer proves a
   selected SucceedQuest suffix's typed remove/safe-run requests and the direct
   SafeRunQuestAction branches: a normal nonzero Boolean return from the actual
   level-availability request selects RunQuestAction with the original String,
   same system reference and QuestAction bits. The recipient enum declarations
   retain all aliases. Complete SucceedQuest entry reachability, collection
   mutation, opaque helper register effects and actual action execution remain
   separate joins.
   The Objective completion consumer independently normalizes the compatible
   ObjectiveData completion byte to the ordinary Boolean low return byte. The
   concrete QuestData/List/ObjectiveData representation and actual typed context
   descriptor do not identify the indexed API or prove item selection. An
   anonymous signed bound lane cannot be named as List size from an open generic
   layout, and the comparison does not establish a valid index. Compatible
   returned records, normal opaque requests and live state stay explicit
   conditions or gaps in `dynamic_quest_objective_boolean_native`.
   Streaming needs independent record-end evidence or a bounded
   runtime carrier witness before field names; keep selector9, Marker13 gap
   profiles and Marker17 bodies anonymous; slot-7 field 0 is each group's
   descriptor-ID mask, so its bits stay as anonymous as the IDs. Framing lives
   in `scripts/game_data/streaming/framing.py`; see
   [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md) and
   [`game_data/world_chunk_unread_region.md`](game_data/world_chunk_unread_region.md).
   Then Terrain channel meaning and live file selection, DynamicStreaming
   nested main records, auxiliary fields beyond descriptor 21 and live
   grid/area selection, and irradiance root/provider/record semantics.
6. **Audio.** HIRC layout and the shipped decision-tree walk are closed
   against the Wwise SDK and bank corpus. The current AKPK inventory and BKHD
   identity joins support broad offline recovery; preserve full external keys,
   package-qualified bank variants and ordered Event actions. Complete the
   decode pipeline's typed-entry/encoded-byte/decoded-byte provenance. Native
   authored Action/Event registration now joins the conditional post/drain and
   Sound-source route. Selected codec registration, RIFF-prefix parsing and
   sample-buffer consumers are authenticated, and original Opus code computes
   samples that its media wrapper returns with independently corroborated
   geometry and bounded quantization error, with identical floats from
   independent isolated host execution. Selected numeric Event sources also
   execute exact-key resident lookup, whole preparation and sample-wrapper
   output under explicit table/input/provider conditions, with original
   resident-row admission. Original node/source preparation now requests numeric
   file bytes and allocates/reads/publishes them before identical context PCM;
   immediate/deferred and open/read/EOF branches are distinct. Original package
   header/load/list admission, numeric row selection and aligned media XOR now
   preserve the same PCM under supplied load-call and stream-interface conditions.
   Original synchronous stream reads and OS completion/decryption now feed
   resident publication and original memory-provider methods before identical
   PCM, with actual byte counts independently authenticated. Close the game's
   load/reorder sequence, actual device/worker scheduling
   and authored owner/route/effect state next. Original parameter refresh,
   primary/embedded owner construction, policy/frame admission, context/frame
   construction, unity-rate conversion and
   release, frame preparation, filter bypass, master-bus output
   and render-buffer submission now compose under supplied scheduling, topology
   and COM interfaces. Native preparation populates descriptor fields and
   corrects the initial frame counter. Keep
   attachment success distinct from a prepared source; the native frame adapter
   adds initial silence when that preparation step is omitted. Prioritize
   authored owner/bus selection and effect values, varying pitch/rate
   and actual endpoint selection. Clean paired live evidence now admits the
   selected mixed-bus post-processing/master/render-client path, including
   bit-exact bounded AVX EQ output and separate master/sink gain comparisons.
   Reuse that accepted branch. Individual Event contribution through the
   multi-source mix, other effect/rate branches, allocation generations and
   physical audibility remain open. Original conditional
   sink negotiation now selects/falls back channel formats, tries Windows rate
   conversion before native resampler setup, checks event/device capacity and
   initial silence release, and allocates the sink buffer. The matched-format
   route cohort uses that native buffer and capacity query without helper sink
   capacity/valid-count assignment. Continuous resampled sink PCM remains open. Keep
   the stronger conditional route join: original attachment links source and
   bus lists, nonempty preparation builds route matrices, native collection and
   mixing create bus PCM, and bus reset advances frame reuse. Sample values
   agree completely, with signed-zero normalization recorded separately.
   No helper source-to-bus descriptor copy remains; authored topology, remaining
   route branches and the engine scheduler/arena lifetime remain open. Keep
   the separate non-excluded Sound cohort: original whole loading and fixed
   property collection join native volume/makeup-gain paths, active source
   filters and negotiated render buffers. Every submitted sample value agrees
   with independent AVX/FMA gain arithmetic from original filtered PCM,
   including terminal fades and padded filter history. Preserve constructor
   filter flags; inherited forced-bypass helper writes are rejected. Native
   parent/bus construction, exact registry admission, child-link fixups and
   recursive collection now have a separately reviewed inherited cohort.
   A reusable STMG reader and current available-bank corpus authenticate its
   physical default/transition inputs. Original collection, filters and native
   gain/mix reach finite render buffers with independent submitted-sample checks.
   The null-component/default empty listener branch and supplied single mixer
   bus remain conditions; stored bus ancestry is not actual mixer topology.
   Corrected phase capture now supplies readable component/listener returns,
   same-Action serial/allocation and source/constructor inputs, conditional
   owner continuity into PCM, and sampled context/bus links. Complete selected
   voice paths match current external headers; one finite nonzero live prefix
   exactly matches original codec output from its matching physical WEM.
   Device phase capture now retains successful same-client buffer requests,
   byte-exact copied sink prefixes and actual successful Windows release results.
   Mixer capture adds real row/descriptor inputs and completed output conversion
   with exact first-channel constant-gain prefix checks. The initial owner serial
   read used a neighboring word and is excluded. Its corrected repeat now
   supplies unique managed serial candidates beside PCM and complete local
   owner/source transport tuples for a subset. Source storage reuse still
   prevents whole frame attribution. Paired bus input/output and unsampled
   publication/source/reset capture now narrow current source identity into
   actual mixer inputs within observed intervals. Incoming gain/matrix/filter
   processing and later device-frame identity remain the next numeric gaps.
   Numeric operands are captured, but that session's queue loss withholds its
   interval joins; completed numeric/device pairs and earlier loss-free frame
   scopes stay separate. Attribution/address corrections are tested and both
   saved frame sessions replayed. Numerical operands, frame handoff and bounded
   recording scope require review and design before another capture request.
   Whole source-to-mixed-frame attribution and continuous allocation generations
   still need the targeted evidence specified in
   [`runtime_capture_requirements.md`](runtime_capture_requirements.md#audio-event-owner-listener-and-output-selection).
   Keep
   Vorbis emulator/host differences separate from original host/reference
   differences; whole preparation and direct host initialization agree for
   the shared file. Existing combined recordings
   already supply managed paths, local provider/descriptor entries, successful
   read completions and sparse pre-transform words; selected offline entries
   also have equal decoded PCM. These do not identify every live backing file,
   allocation generation, complete buffer or game decoder instance. A future
   session must target a named shared runtime join and distinct missing consumer
   branches, with acceptance criteria established first. Native plug-in value
   meanings and other offline work remain independent of that session. See
   [`game_data/audio_native_hooks.md`](game_data/audio_native_hooks.md) for the
   retained observation boundaries and
   [`game_data/audio_overview.md`](game_data/audio_overview.md) for the six-layer
   evidence model. Native callsites are re-proved by name on a new build through
   `scripts/webui/audio/semantics/native_callsite_rederivation.py`.
7. **Catalog and code.** BundleManifest cross-store identity and live lookup,
   mmap, and IFix patch execution.
8. Improve exact prefab, renderer, material, animation and world-instance
   ownership, and keep native gates and graph provenance deterministic across
   client updates. LevelScript, LevelData, Spawner, Story and the Buff action
   dispatcher resolve union tags by name; literal AbilityActionData tags remain
   in `skill_timeline_shared_sequence`, `buff_residual_actions`, the nested
   selector/processor profiles of `buff_actions`, `buff_corpus` frontier lists,
   receipt `TAG` constants and `buff.py` tables. Their per-route native
   contracts still refuse another build, but convert them before the next
   client update.
