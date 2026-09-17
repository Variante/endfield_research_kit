# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and level
payloads. The first section is where each family's framing stands; the rest is the
IL2CPP evidence chain that identifies *which* formatter a payload resolves to --
static identity throughout, never observed execution.

## Framing status, by serialized family

SkillData historical export-backed censuses cannot establish current VFS
coverage by accepting a newer boundary report. Its maintained
`memorypack.skill_corpus` gate starts from the authenticated outer ledger and
current decrypted VFS stream bytes, checks the complete identity set and
source/overlay/tool provenance at both ends, and records logical hashes.
The anonymous terminal reader enumerates direct-counted and wrapped branches
independently, including empty wrappers; unknown record member counts fail
closed. A unique EOF candidate is unique only within the supported grammar,
not a proven preceding cursor. Full record ranges, ambiguous candidates and
opaque gaps remain distinct from whole-file ownership. Current coverage and
full candidate inventories belong to
`reports/animestudio/skilldata_current_latest.json` and its Markdown companion;
the historical two-ambiguity census is superseded, not a current baseline.
BuffData needs a
provenance-matched census before reporting current coverage and has a bounded
anonymous member-18 stacking-action
reader; its fixed extent and terminal markers can be exact without claiming
semantic field order, while changed or unsupported rows remain explicit.
LevelScriptData and LevelData expose partial top-level frames only when their
independently parsed prefix/suffix regions are unique and
EOF-exact; nonempty/null LevelScript action maps may also expose only an
anonymous first-list/record-envelope or raw-null prefix while all later
union data stays opaque. One high-coverage first-record variant has a bounded
sequential body reader, but later records/lists remain unowned. AnimationConfig likewise separates
a proven anonymous prefix (and a small exact whole-frame variant) from an
opaque remainder. Keep structural framing distinct from semantic schema
ownership until formatter IL or a bounded deserialization trace closes the
complete named cursor.

## The SkillData formatter and wrapper registration

Current registration locates real SkillData formatter/wrapper bodies and
their relative five-operation terminal read sequence, not a file offset.
The Core type used by `ReadValue<T>` differs from the generated wrapper's
`Register<T>` type; a generated wrapped reader alone does not prove the
adapter or active formatter. A separately gated immediate-registration site
now joins the Core key to `GenericMemoryPackFormatter` with ordered arguments
Core and `Beyond_Gameplay_Core_GameplayTagListForMemoryPack`: its type carrier
and constructor MethodSpec share the same registered class instantiation.
This proves static adapter identity and a conditional registration callsite,
not completed allocation ABI, executed registration or active Deserialize
dispatch. Registration and lookup independently share one RIP-relative cell
and the same class/static-storage dereferences. The lookup's matched node
supplies its returned value, but misses can invoke callbacks, retry or construct
alternatives; this does not fix live contents or replacement history. The separate
generic serializer's pointer/length-word carrier is not yet joined to this
formatter or authenticated VFS allocation. Keep both terminal candidates;
complete nested cursors and EOF remain unresolved. Native pins and reviewed
limits belong to `reports/animestudio/skilldata_native_review_latest.json`;
PE reads must remain within raw section extents: virtual-only globals have
no disk value and need runtime-initialization evidence, not adjacent file bytes.

## Generic-instantiation registration is a pointer array

Generic-instantiation registration is a pointer array, not inline records;
preserve the record's padding separately from its u32 argument count. The
maintained `scripts.game_data.il2cpp_context_audit` validates current native
inputs, every registered instance, and reciprocal open-parameter ownership.
Its inventory is `reports/animestudio/il2cpp_context_current_latest.json`.
The selected `GetFormatter<T>` parameter belongs to `ReadValue<T>`; a prior
concrete-type probe was an indirection bug, not a runtime counterexample.
This static join does not establish actual generic substitution or formatter
selection; preserve both terminal candidates until those separate gates close.

## Resolving the formatter: the MVAR leaf, modules, and usage cells

The native MVAR leaf reads a parameter ordinal and indexes the supplied
method-inst vector. The gate checks that ordinal against the selected call's
registered argument. Native normal-path stores now connect method records to
their class, the metadata image-range directory, and a module selected by
bytewise name comparison from the gated CodeRegistration. The static image
partition must be complete and unambiguous; module names must be unique since
the native loop continues after a match. This does not certify initialization
execution, all cold paths, active formatter selection, or source/cursor/EOF.
The selected call's on-disk usage cell also joins through the wrapper's guarded
lazy initializer and tag-specific MethodSpec/triple resolver. This establishes
the static initialization mechanism, not an observed live cell or cache entry.
The open formatter-check carrier independently joins the same MVAR through its
class-inst pointer; reject duplicate pointer identities and token ranges.
The native method-pointer resolver retries a missed original-context lookup
with transformed argument vectors. Its direct class-tag branch uses one shared
global carrier plus the type-record offset for both adapter arguments. The
normal producer's image/namespace/name lookup and class copy connect this to
the unique `mscorlib.dll / System.Object` byval record; its bytes match both
arguments of the static object/object candidate. Actual initialization, cache
population and interned pointer identity remain unobserved: byte equality does
not select a particular shared Deserialize body.

## The instantiation cache, MethodSpec joins, and RGCTX slots

A separately gated initializer seeds the generic-instantiation cache from the
selected registration's pointer table; insertion and lookup share the same
storage global. This conditional path is not an observation of cache contents.
The gated object-tag comparator and hash use only the tag and one flag bit,
not record addresses; enumerate every registered pair matching that projection.
A unique static match still does not prove the returned runtime instance.
Matching MethodSpecs join bounded method/invoker index triples and pointer
slots; the no-adjustor sentinel reuses the ordinary method pointer. Other
adjustors need an independently bounded table and remain unsupported here.
Keep RGCTX range-relative slots distinct from module entry indices. The adapter
class-token range connects its selected slot to a reciprocal second type
parameter (VAR), not an unrelated concrete type. The class initializer's
conditional path converts 16-byte definitions to eight-byte runtime slots
using the class generic context; static definitions are not observed slots.
The reviewed MethodInfo construction path stores the original instantiated
class separately from resolved shared-code pointers. Do not substitute the
shared body candidate's object/object arguments for the companion's class
context; actual cache contents and invocation still need independent evidence.
Nested class slots independently link MethodSpecs for the non-null adapter,
formatter lookup and instance creation to reciprocal parameters of that same
adapter type. Keep these static links separate from serialized read order.

## The generated wrapper reader, and `ListFormatter`

The generated wrapper reader conditionally forwards the same reader after a
one-byte fast-path header to an independently joined `ReadPackable<List<...>>`
usage/MethodSpec/type carrier. Its nested body follows relative slot zero through
`ReadPackable` to `ReadValue`, then `GetFormatter`, then the latter's MVAR type.
Each method edge independently joins one ordinal-zero parameter owned by its
preceding method; these are distinct records, not interchangeable MVAR identities.
The original concrete argument propagates only conditionally on context inflation.
This remains a provider/dispatch layer, not the list element reader or a selected
runtime formatter. A separately joined `ListFormatter` registration shares the
list element instantiation and supplies a static Deserialize code candidate.
Its fast path consumes a four-byte count; the remaining-length comparison is
unscaled, and each positive iteration delegates element decoding. The four-byte
element output slot is not a serialized-width proof. Counts below minus one
reach an error helper only on the new-output path; the existing-output path
clears its length and skips the nonpositive loop. Preserve that native distinction
without relaxing the maintained parser's negative-count rejection. Actual
provider selection and EOF are still open. The element dispatcher reloads the
actual object's class after initialization and takes its target/companion pair.
The non-specialized branch calls that target with object, reader, output slot
and the loaded companion; a distinct equal-target path delegates through class
RGCTX helpers. Incoming RCX is not a caller-selected slot. Neither branch proves
the live formatter identity or a fixed element byte width.

## Element dispatch, the `FF` peek, and the conversion carrier

The comparison target separately joins a shared adapter code candidate with
GameplayTag/Object arguments; do not replace the loaded companion's context
with that candidate's Object argument. Its selected helper peeks for `FF` and
only on a match consumes one byte before returning true and clearing the output.
The byte consumer's own boolean is different and is not forwarded. A nonmatch
does not directly advance this helper's cursor; ensure may still replace its
segment. The non-FF helper passes the same reader and an initialized writable
object-reference slot to formatter dispatch. A null result produces zero;
otherwise a separate interface lookup selects a target/companion pair and
tail-jumps with the result object, without forwarding the reader. Returned EAX
becomes the four-byte output. This is a converted result width, not serialized
consumption. Interface record offsets and slot arithmetic are directly pinned,
and the conversion carrier independently joins
`IMemoryPackDeSerializeWrapper<T0>`: its argument reciprocally belongs to adapter
ordinal zero, distinct from the formatter query's ordinal-one argument. The
adjacent MethodSpec uses that same instantiation and names `GetValue`; its
metadata slot is explicitly zero, matching the native request without assuming
declaration order. The native branch does not directly read that MethodSpec slot.
Target-pair bounds, live provider/conversion implementation, branch selection
and non-FF source consumption remain unresolved; follow the delegated formatter
context before interpreting this output or eliminating a terminal candidate.

## The provider takes a companion, not the reader

That provider takes a companion, not the reader: its first method-context slot
supplies a type-derived lookup key, and its second supplies the returned-object
check. A carrier table and a separate formatter cache participate; cache misses
reach conditional generation and writeback paths. This is direct state-dependent
control flow, not an observed cache entry or proof of the registered candidate's
selection. The class helper's identity return is conditional on an initialized
flag; its other branch delegates initialization. Do not collapse these branches
into unconditional pointer identity or infer serialization from provider names.

## Cursor state, and why none of it is an EOF test

Cold advance normally returns true, resets
the segment counter and accumulates the request; ensure can replace the cursor
with an existing or copied segment. Pointer deltas cannot certify source offsets.
The 24-byte descriptor has a conditional same-endpoint position-difference
length path. Independently token-joined constructors accept that descriptor or
a 16-byte pointer/length carrier and initialize total/remaining state and zero
consumption. Native getters identify consumed and total-minus-consumed roles;
reviewed caller paths return consumption but do not themselves compare EOF.
The token-joined object-return overload discards this count. Selected async
paths either discard it or forward it to another operation, not an EOF test.
These general serializer paths do not establish SkillData entry selection.
Exact Core.SkillData type arguments also join ResourceManager MethodSpecs;
their generic definition module slots are null. Separately enumerated
same-definition Object MethodSpecs supply shared-code candidates, not observed
sharing selection or invocation. Never confuse the same-named nested AI type
with the Core type, or substitute a shared body's arguments for live context.
A downstream native carrier wrapper forwards a reconstructed pointer/length
carrier to an inlined reader-state builder. Conditional dispatch uses that
state and an output slot; its returned consumption is discarded by the wrapper.
This corroborates the non-EOF boundary, not an authenticated file receipt.

## The formatter-check carrier's uninterpreted tail

identity remain unresolved. No observed final cursor or terminal uniqueness
follows from this conditional ABI.
Preserve the open formatter-check carrier window's uninterpreted tail: its bytes do not certify a
runtime allocation extent or select the returned formatter. Provider fallback
includes a lazy callback path whose population remains a separate evidence gap.

## Remaining gaps

- Close SkillData's real formatter/ref-reader cursor from a current authenticated
  logical file through the anonymous terminal start; method identity and a final
  one-byte read alone do not prove source extent or exact EOF. Preserve candidate
  ambiguity until that connection exists, then continue the residual JsonData
  record queue rather than inferring field order from declarations.
  Two gates decide this thread: an authenticated logical file joined to the
  anonymous terminal start, and a proven element byte width at the `ListFormatter`
  element dispatch. Static registration/MethodSpec joins that move neither gate do
  not reduce the 2,621 ambiguous candidates. If continued tracing stops moving
  either gate, treat the static-join route as at its ceiling and evaluate a bounded
  runtime deserialization trace instead of extending the native inventory. A
  final outer-deserializer cursor cannot select between terminal candidates that
  both end at EOF; the witness must capture the cursor immediately before the
  ambiguous terminal member on the same authenticated source buffer and reader,
  joined to the actual Core.SkillData invocation. No maintained current-build
  runtime profile currently closes that chain, so preserve both candidates until
  such a witness exists.
- `memorypack.buff_corpus` supplies the full current BuffData denominator from
  authenticated outer-ledger identities and decrypted stream bytes, using shared
  `memorypack.corpus_gate` provenance guards. It retains all filename-string
  anchors and reader-accepted EOF suffix candidates rather than inheriting the
  legacy reader's anchor selection. A unique accepted suffix does not establish
  its top-level ownership or certify internal opaque regions; whole-schema status
  remains false. Coverage, multiple-anchor counts and per-file diagnostics belong
  in `reports/animestudio/buffdata_current_latest.{json,md}`. Next close the opaque
  prefix/anchor join and nested record bounds before promoting any field names.
  The legacy prefix reader now rejects invalid anchor limits instead of clamping
  them and receives only bytes before the anchor, so count/string/scalar helpers
  cannot borrow suffix bytes. The corpus records its accepted prefix endpoint or
  unsupported-action stop and the remaining gap for every accepted suffix; this
  does not certify the legacy field labels or close that gap.
  `memorypack.buff_1b_corpus` rebuilds the authenticated census and checks exact
  root-continuation tag `0x1B` ranges against re-streamed logical bytes, then
  joins the record to the current exact-build selected action reader. This
  continuation profile does not prove root-field ownership. The
  SequenceActionData provider remains unresolved; the anonymous action reader
  does not close BuffData suffix ownership or whole-file EOF.
