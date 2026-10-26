# IFix patch records and native wrappers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, code lane.** This file owns what a decoded `IFixPatchOut` record
proves about a replacement target, and where that proof stops. The exact
framing boundary belongs to
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

## From installed bytes to a replacement target

`IFixPatchOut` is an encrypted VFS block. A direct, MD5-verified AnimeStudio
dump from the active Persistent root, with StreamingAssets fallback, supplies
the decoded logical bytes. The maintained
[`ifix_patch.py`](../../scripts/game_data/ifix_patch.py) reader consumes every
current file exactly: a bounded opaque prefix, then the IFix file-VM stream of
strings, external type and method tables, raw instruction/exception spans, and
fix records through EOF.

A fix record binds a CLR method signature to an index in the patch's VM method
body table. That is direct evidence of a **declared replacement target** in
this file. An external-method row is a reference available to patch code, not
a replacement target. Declarations alone do not prove the replacement's
behavior, that the runtime loaded the file, or that any call entered the patch;
a target name is not an execution trace.

A patch-only update can change these records while the executable and metadata
stay identical. Rebuild the target catalog from a fresh MD5-verified VFS dump
and compare its patch digest before carrying a target-list conclusion forward.
A native-input match alone does not authenticate the installed patch. Native
proofs of an original body retain their stated IFix-selection conditions.

The VM method index and the AOT wrapper's `IsPatched` id are **different
identity domains**: `ifix_patch.py` reads the former from the file,
[`body_claims.py`](../../scripts/game_data/il2cpp/body_claims.py) the latter
from a native method's test, and they differ for the same fixed methods. Never
join the two integers or read an AOT id as a VM body offset. A `None` from
`BodyIndex.ifix_patch_id` means *not found by its bounded search*, not
*unwrapped* or *not fixed*; the fix record is the authority.

The installed build (GameAssembly AB00F1C4) has no direct `IsPatched` call:
wrapped methods open with an inline patch-table guard (RIP load of a zero-
initialized `.data` root, table qword at a per-method displacement, slot
function pointer; null table or null slot falls through to the original body).
[`il2cpp/patch_table_guard.py`](../../scripts/game_data/il2cpp/patch_table_guard.py)
proves the shape; the selection is anonymous runtime state, so proofs through it
are **conditional**. `ifix_patch_id` returns `None` for these bodies, and no
join from slot displacement to a VM method index is established.

## Opcodes, operands, frames and signatures

Native modules below derive their facts from the explicit selected
`GameAssembly.dll`/`global-metadata.dat` pair and checks the reviewed contract's
method identities and the declared complete bodies or finite entry programs
before projecting anything, failing
closed on a mismatch. A **row join** (an operand naming a declared file row) is
direct under the selected build and the supplied bytes; every **stack, slot or
resume effect** is conditional on the native path returning normally. Execution
is never observed. The native facts behind each rule are listed in
`validate_vm_operand_contract` in
[`ifix_vm_operands_native.py`](../../scripts/game_data/ifix_vm_operands_native.py),
against the reviewed
[`ifix_vm_operands_native.json`](../../scripts/game_data/contracts/ifix_vm_operands_native.json).
Derived alias equations require the corresponding validated native audit
instead of reopening the selected inputs.

The audit's [rule ownership inventory](../../scripts/game_data/ifix_vm_rule_inventory.py)
covers the complete selected `Code` enum independently of patch occurrences.
It distinguishes scoped conditional recipes, ordinary default requests and
pending recipe review. An empty patch projection or an assigned recipe owner
does not prove complete runtime semantics. `StackSpace` at entry remains a
frame header even though ordinary dispatch selects the default request.
The reviewed contract assigns every selected enum member a scoped recipe
owner or the authenticated ordinary default route. Core method coverage also
includes finite entries without a pdata extent; generic sharing, generated
game bridge behavior and framework/helper outcomes remain separate boundaries.

| Operands | Rule under the selected `LoadInternal`/`Execute` bodies |
| --- | --- |
| every opcode | `IFix.Core.Instruction` is 8 bytes (`Code`, `Operand`); the selected enum names code words and unknown codes fail closed. The native VM audit optionally marks long/double payloads and packed `Switch` tables as inline data while preserving physical indexes ([`ifix_vm_instruction_native.py`](../../scripts/game_data/ifix_vm_instruction_native.py)) |
| `Call`, `Callvirt` | low 16 bits index `unmanagedCodes` (file body order); the signed upper half is the recursive `argsCount` |
| `CallExtern`, `Newobj` | low 16 bits index `externMethods`; the signed upper half rewinds that many 12-byte evaluation slots to the argument base, a stack count rather than a parameter count; `Newobj` takes a separate path for delegate constructors |
| delegate `Newobj` | under the checked `MulticastDelegate` base-type selection, takes the two slots below top; the Integer-tag method value reaches receiver dispatch and a null-only generic fallback, while other tags reach a `MethodInfo` cast and `Delegate.CreateDelegate`; normal-return result storage reduces top by one slot and preserves the target slot's tag |
| `Ldftn`, `Ldvirtftn` | the whole signed operand selects `externMethods`, rather than its low half; `Ldftn` pushes an Object-tagged reflected row, while `Ldvirtftn` replaces the receiver slot with an Object-tagged row selected through type comparison and the unequal-type resolver |
| `Ldvirtftn2` | the unsigned low half selects a runtime anonymous-storey VTable slot; writes its stored integer into the method slot below top with an Integer tag, leaving top unchanged and reading the receiver one slot further below |
| `CallExtern` result | a cache miss builds a `ReflectionMethodInvoker` whose `Invoke` pushes a nonvoid result through `Call.PushObjectAsResult`: a conditional data-flow path |
| `Br`, `Brtrue`, `Brfalse` | signed offsets relative to the current instruction; a target outside the method span is marked out of range, never given a row |
| `Leave`, `Endfinally -1` | `Leave` stores a pending absolute index that `Endfinally -1` resumes when it is nonzero; `Leave 0` is a sentinel, not a resume edge |
| `Ldstr`, nonnegative `Ldfld`/`Ldsfld`/`Stfld`/`Stsfld` | index `internStrings` / `fieldInfos` in file order; negative routes have separate evidence boundaries below |
| `Initobj`, `Constrained` | index `externTypes` in file order; `Initobj` after `Ldloca` updates that local slot with an `Activator.CreateInstance` object; `Constrained` converts the slot its preceding operand selects to an object |
| `StackSpace`, `Ldarg`, `Ldloc`/`Ldloca`/`Stloc`, `Ret` | the frame header reserves local and evaluation slots; locals index after the runtime argument count; `Ret` with a nonzero operand returns the top value |
| `Ldc_I4`, `Ldnull`, `Pop`, `Nop` | selected dispatch and effect windows prove signed Int32 literal push, null Object push, discarded-slot managed-reference clear, and instruction advance respectively; operands other than the literal are not read by these paths |
| `Conv_I8` | selects the tag after `resolveStackReference` returns normally: Integer sign extension; Long with no conversion store; Float widening and Double through the same truncating Int64 helper; other tags enter the runtime exception route, storing zero only if that route returns normally |
| exception records | six signed `ReadInt32` fields per 24-byte record, `HandlerType` through `HandlerEnd`, with the selected `ExceptionHandlerType` enum |
| external signatures | generic positions restored to file order ([`ordered_signature_parameters`](../../scripts/game_data/ifix_patch.py)); constructed owner/method arguments and byref parameters substituted; one unique selected metadata definition each ([`ifix_external_signatures_native.py`](../../scripts/game_data/ifix_external_signatures_native.py)) |

In the current files every file index, branch target and local slot fits its
declared table, method body or frame; every field operand is nonnegative and in
range; every external declaration resolves uniquely, so its return type and
static flag are direct selected-build facts; and the `Newobj` upper halves equal
the file-declared constructor parameter counts.

**Eliminated readings.** The older text-only signature printer dropped generic
positions, so its shortened spellings (such as `LogError`) were incomplete. A
`CallExtern` upper half is not the reflected method's parameter count. A
`Leave 0` target is not a resume edge. Widening `ifix_patch_id`'s search window
does not safely find a method's own id, because later `IsPatched` calls can
come from inlined methods.

## Conditional delegate and basic effects

The delegate rules live in
[`ifix_vm_delegate_rules.py`](../../scripts/game_data/ifix_vm_delegate_rules.py),
and the basic opcode rules in
[`ifix_vm_basic_rules.py`](../../scripts/game_data/ifix_vm_basic_rules.py).
Both use the reviewed VM contract and the parent's explicit selected-native
gate. The finite dispatcher follows the selected enum value through checked
`cmp`/`sub` and conditional branches; it does not infer case order from
addresses. The delegate path ignores the call operand's upper half after its
type selection and uses two fixed input slots. If the wrapper-manager result
is null, the generic factory receives the same delegate type, VM method value
and target. If that result is also null, the selected exception route is
called. Factory outcome, reflective success and invocation remain open.

The result tail rewrites `Value1` and the managed array entry but does not
write `Type`; it is not an Object-tag normalization proof. Incoming slot
validity and changes made by children or aliases remain unresolved. `Nop`
does not read its own operand, but the already proved `Constrained` rule can
read the preceding instruction's operand, so the stored value is retained.
The audit inventories opcode names without a projector separately from
complete stack semantics: an empty residual inventory establishes neither
full interpreter understanding nor a valid execution stack.

The Float branch widens its low single-precision value to double, then joins
the Double branch at the checked `CVTTSD2SI` helper. Its signed Int64 conversion
uses truncation, as specified in the
[Intel instruction reference](https://cdrdv2-public.intel.com/812383/253666-sdm-vol-2a.pdf).
Hardware floating-point exception masks and state are unobserved, so the proof
records the selected instruction path without assigning a runtime result to
every exceptional input. Long bypasses the conversion stores after the
resolver; unsupported tags enter `throwRuntimeException`, with a zero-Long
store only on that call's normal-return continuation.

The method-value producers live in
[`ifix_vm_function_pointer_rules.py`](../../scripts/game_data/ifix_vm_function_pointer_rules.py).
`Ldftn` uses the reflected `MethodBase[]` table, so its Object tag alone does
not establish a successful `MethodInfo` cast in the constructor. `Ldvirtftn`
uses the declared row when the receiver's runtime type equals the row's
declaring type; the unequal-type path selects through the override resolver,
whose concrete result remains unresolved. Its normal-return store replaces
the receiver slot without a net top change.

`Ldvirtftn2` instead supplies the Integer-tag route: it reads the receiver's
`typeId`, selects the runtime anonymous-storey information and its VTable,
then rewrites the method slot while leaving the receiver slot in place. It
does not check an incoming receiver tag. Receiver validity, runtime bounds,
the selected integer and subsequent invocation remain conditional. The
framing reader refuses nonzero anonymous-storey tables: each interface record
stores one method ID per runtime `GetMethods(DeclaredOnly|Public|Instance)`
result, with no file-stored method count or order. The conditional loader recipe
is proved, while the projector exposes the authored low-half slot without
inventing a file VTable row.

## What the current patches author

- **Gameplay.** The `_InitLoader` replacement body declares calls to three
  other VM bodies, and its external signatures include typed
  `DeserializeFromJson` returns for the list and per-level UI map load configs,
  byref level-config lookups, and the loader-data constructor. Its field
  references cluster around map loader configuration, inverse-coordinate setup,
  and loader-data lookup dictionaries; `NetClientManager.Launch` references
  session and network-limit fields. The recursive call operands cover every
  authored `Ldarg` slot in their target helpers: one getter-like
  `Ldarg`/`Ldfld`/`Ret` helper for `DataManager.uiLevelMapConfig` and two
  setter-like `Ldarg`/`Stfld`/`Ret` helpers for MapManager grid lengths (an
  inference from opcode order and named field rows).
- **The `_InitLoader` finally chain.** Its one `Finally` handler forms a direct
  authored cleanup and resume chain: a `Leave` to the instruction after the
  handler, the handler, and `Endfinally -1`. Inside the handler, before an
  external call, the single `Constrained` selects the file-declared
  `List<string>.Enumerator` row and follows `Nop 0`, so it selects the top
  evaluation slot. Each `Initobj` follows an in-range `Ldloca`, so its
  destination is that authored local slot. Whether the path ran is unobserved.
- **Rendering.** The body names the `_Crash1` string and calls the metadata's
  static `bool ShaderWarmupManager._IsFeatureEnabled(string featureKeyword)`,
  rewinding one slot after `Ldstr` (the string is its apparent argument); `Ret 1`
  selects the reflected result on the normal-return path. The bool is
  unobserved.

These are authored references and control-flow edges, not proof that a patch
ran or produced an effect.

## Negatives over declared targets

- **PlaySound.** In a fresh, MD5-verified dump, no declared replacement target
  is a named method in the checked default PlaySound string-to-hash route
  ([`audio_play_sound_string_native.json`](../../scripts/game_data/contracts/audio_play_sound_string_native.json)).
  This is an exact absence from the **declared fix targets** only: an external
  reference is not a replacement, and nothing here establishes loading,
  activation, or the path a PlaySound action takes. The default-body proof and
  its runtime boundary belong to [`audio_native_hooks.md`](audio_native_hooks.md).
- **Missions.** An older local mission audit describes a different patch
  payload and must not be carried forward. The current payload matches the
  reviewed [`ifix_patch.json`](../../scripts/game_data/contracts/ifix_patch.json)
  contract, whose fixed-target and external-reference classifications contain
  no direct task-completion or receiver-ownership match: a narrow negative over
  the decoded records, not proof that the patch has no indirect effect on
  missions or Story.

## Currentness gate

The production
[`ifix_patch_native.py`](../../scripts/game_data/ifix_patch_native.py) loader
checks the contract against the selected native pair but does **not** read the
live VFS patch. Its `validated` status proves the native pair and contract
shape, not that a patch-only hotfix still has the contract's `patchSha256`, so
compare that digest with a fresh, MD5-verified VFS dump before using the target
list; a native build match alone is insufficient. The VM operand audit binds
its inputs to the current outer VFS summary and full ledger when given
`--outer-summary`, `--outer-ledger` and `--expected-input-set-sha256`: the
entire IFix file set, verified outer boundaries, and byte-for-byte MD5
agreement. This joins the complete input set to the supplied outer receipt,
which may be retained; it does not reread live VFS. Live currentness requires
a fresh VFS audit. Without those arguments the result is a projection over
caller-supplied bytes.

## Remaining boundary

**Level 3 (partial):** opcodes and selected operand routes through
authenticated file-VM code, frame slots, exception records, and uniquely
resolved external signatures, plus the conditional delegate construction and
basic effects above. Wrapper-manager implementation selection, generic factory
reflection arrays and reflection success, concrete unequal-type override results, floating-point exception state,
runtime reference storage, chain objects and native exception delivery remain open. The method
producer and constructor rules do not witness an incoming delegate stack.

| Conditional rule | Validated status | Remaining join |
| --- | --- | --- |
| [Wrapper dispatch](../../scripts/game_data/ifix_vm_wrapper_dispatch_rules.py) | named interface, image-qualified direct targets and slot-zero fallback | live manager selection and wrapper result |
| [Generic factory](../../scripts/game_data/ifix_vm_generic_delegate_rules.py) | typed cache, signature rejection and Action/Func array selection | catalog contents, runtime sharing and reflection success |
| [Generic catalog](../../scripts/game_data/ifix_vm_generic_catalog_rules.py) | lazy reflection/filter/order/materialization recipe and separately authenticated declared arities | reflected arrays, callback caches, enumeration and sharing |
| [Generic binding](../../scripts/game_data/ifix_vm_generic_binding_rules.py) | parameter Types, Func return Type last, MakeGenericMethod forwarding and closure captures | runtime Type arrays, virtual pairs and successful delegate creation |
| [Action bridge](../../scripts/game_data/ifix_vm_delegate_bridge_rules.py) and [generic bridges](../../scripts/game_data/ifix_vm_generic_bridge_rules.py) | saved state, ordered arguments, zero-refCount Execute and Func saved-result/physical-clear requests | reflection-selected contexts, method/stack validity, casts and invocation |
| [Virtual resolver](../../scripts/game_data/ifix_vm_virtual_dispatch_rules.py) | Type/base-definition cache, candidate search, hierarchy traversal and null caching | concrete reflection results and runtime sharing |
| [Slot copies](../../scripts/game_data/ifix_vm_slot_copy_rules.py) | Ldarg/Ldloc/Stloc/Dup and native copy/store tag cases | runtime bounds, Clone results and overlapping/reference storage |
| [Negative static fields](../../scripts/game_data/ifix_vm_negative_field_rules.py) | complemented index, initialization call and conditional load/store effects | static arrays and initializer/conversion results |
| [Negative instance fields](../../scripts/game_data/ifix_vm_instance_field_rules.py) and [instance aliases](../../scripts/game_data/ifix_vm_instance_alias_rules.py) | complemented index, AnonymousStorey storage, ordered same-Value/shared-array equations and two-slot store rewind without explicit consumed-reference clearing | live alias selection, partial overlap, conversion outcomes and later cleanup |
| [Whole-slot aliases](../../scripts/game_data/ifix_vm_slot_alias_rules.py) | ordered copy/store and Stloc clear consequences under stable same-slot or distinct-slot hypotheses | live index relations, partial overlap, helper mutation and Clone identity |
| [Stack references](../../scripts/game_data/ifix_vm_stack_reference_rules.py) | pointer words, one-hop decode and Object/ValueType rebasing | pointed storage, overlap, concrete tags and producer/consumer connection |
| [Reference updates](../../scripts/game_data/ifix_vm_reference_update_rules.py) | reflected/internal/array target requests and chain setter forwarding | successful setters, target contents and runtime alias mutation |
| [Chain fields](../../scripts/game_data/ifix_vm_chain_field_rules.py) | recursive parent selection and outward parent writeback | concrete parent objects, reflected implementation and successful writes |
| [New fields](../../scripts/game_data/ifix_vm_new_field_rules.py) | hash-keyed storage, default/initializer requests, static storage construction and snapshot/liveness pruning requests | collisions, mutable names, closed generic payload layout, enumeration, initialization and helper outcomes |
| [Object conversion](../../scripts/game_data/ifix_vm_object_conversion_rules.py) | complete tag, primitive-width, enum/pointer and recursive-reference programs | runtime Type/boxing/clone results, recursion stability and exception selection |
| [Reference addresses](../../scripts/game_data/ifix_vm_reference_address_rules.py) | argument/static/array descriptors and ordinary/new/appended field-chain requests | runtime addresses, selected paths, allocation/copy outcomes and alias mutation |
| [Opcode dispatch](../../scripts/game_data/ifix_vm_dispatch_rules.py) | complete ordinary-loop enum selection and shared default exception/message requests | actual entry, message/throwing results; initial frame header remains a separate scope |
| [Comparisons](../../scripts/game_data/ifix_vm_comparison_rules.py) | bit-based `Ceq`, left-tag relational selection, ordered/unordered floating predicates and conditional clears | actual values, right-tag compatibility, hardware state and helper mutation |
| [Conversions](../../scripts/game_data/ifix_vm_conversion_opcode_rules.py) | remaining numeric/checked conversion programs and stack-reference-to-pointer shortcut | source values, bounds/overflow request outcomes, SSE state and unwinding |
| [Anonymous objects](../../scripts/game_data/ifix_vm_anonymous_storey_rules.py) | normal record loop, reflection-sized interface slots, nested array/pointer carriers, field-tag construction and saved-object `Newanon` restore | nonzero raw framing, reflected method order, bridge selection, allocation defaults and recursive execution |
| [Arrays](../../scripts/game_data/ifix_vm_array_rules.py) | typed array selection, width/bounds access and conditional load/store/pop requests; reference loads preserve the destination tag | actual arrays, numeric fallback selection, reflection/conversion outcomes, GC and aliases |
| [Bitwise and unary](../../scripts/game_data/ifix_vm_bitwise_rules.py) | integer/long widths, masked shift counts, unsupported-tag outcomes and incoming-mask floating negation | source tags/values, floating mask preservation, exception requests and hardware state |
| [Literals and control](../../scripts/game_data/ifix_vm_literal_control_rules.py) | raw inline long/double bits, packed switch targets without stack pop, argument store/clear and common `Volatile` PC caller | incoming PC, branch-to-payload validity, negative switch counts, aliases and later loop/exception flow |
| [Array references](../../scripts/game_data/ifix_vm_array_reference_rules.py) | complete typed `arrayGet`/`arraySet` helpers, bounds/widths, fast paths without managed clears and fallback conversion requests | actual arrays, type predicates, reflection results and overlapping storage |
| [Indirect operations](../../scripts/game_data/ifix_vm_indirect_opcode_rules.py) | numeric raw-pointer widths and descriptor load/store routes; raw reference/object variants stop through the unsupported request | pointer validity, descriptor contents, aliases, clone/field/array outcomes and unwinding |
| [Arithmetic](../../scripts/game_data/ifix_vm_arithmetic_rules.py) and [floating remainder](../../scripts/game_data/ifix_vm_floating_remainder_rules.py) | native integer/FP programs, checked integer guards, normal pops, unsupported-tag outcomes and complete selected remainder helper programs | division faults, FP state/feature selection, error support outcomes, numerical equivalence and live values |
| [Positive fields](../../scripts/game_data/ifix_vm_positive_field_rules.py) | reflected/new-field requests, pointer conversion, instance descriptor writeback and explicit consumed clears | reflected rows, runtime addresses, helper results, initialization and aliases |
| [Branches](../../scripts/game_data/ifix_vm_branch_rules.py) | current-PC signed targets, tag predicates, native unsupported-tag paths and unary physical-index clears | incoming values, branch-to-inline-data validity, floating state and exception outcomes |
| [Type/object opcodes](../../scripts/game_data/ifix_vm_object_opcode_rules.py) | Type selectors, token/Type pushes, managed fetch before the Unbox tag test, native boxing/unboxing and anonymous Slots compatibility programs | runtime Type/boxing/assignability results, selected implementations, live values and aliases |
| [Calls and returns](../../scripts/game_data/ifix_vm_call_opcode_rules.py) and [Call zero-fill](../../scripts/game_data/ifix_vm_call_zero_rules.py) | recursive and indirect call requests, shared external caller, complete selected zero-fill, raw return copy/rebase and signed cleanup loops | cache/reflection/delegate results, storage overlap and cleanup termination |
| [Initialization and constrained calls](../../scripts/game_data/ifix_vm_init_constrained_rules.py) | complete Type/slot selection, clone request, Object rewrite and consumed Initobj clear | adjacency validity, helper results, target storage and aliases |
| [String loading](../../scripts/game_data/ifix_vm_string_opcode_rules.py) | signed string-table selection, typed handle and PushObject request | runtime table contents, Type materialization, helper results and aliases |
| [Exception requests](../../scripts/game_data/ifix_vm_exception_dispatch_rules.py) | Throw/Rethrow, Leave/Endfinally, stored-order handler selection and conditional catch/no-handler continuations | native EH delivery, live exception container, selected virtual result, unwind and clear-loop termination |
| [Static initialization](../../scripts/game_data/ifix_vm_static_initializer_rules.py) | shared constructor-ID suppression before the zero-argument Execute request and complete index bridge | live constructor table, concurrent mutation, constructor completion and exception delivery |
| [Anonymous loader](../../scripts/game_data/ifix_vm_anonymous_loader_rules.py) | typed reader producer, little-endian count routes, allocation request and contiguous record-loop join | runtime read counts, cold transfers, next loader section/publication and nonzero raw framing |
| [Stack construction](../../scripts/game_data/ifix_vm_stack_construction_rules.py) | Call.Begin, thread-local stack lookup, allocation requests and Base/Top initialization | live TLS selection, allocation/capacity, races and base identity |
| [Call pushes](../../scripts/game_data/ifix_vm_call_push_rules.py) | current-top Object/index store and argument-base typed result forwarding | live bounds, aliases, conversion/assignment results and mutation during calls |
| [Reference helpers](../../scripts/game_data/ifix_vm_reference_helper_rules.py) | complete array fetch/store, cast and conditional card-bitmap programs | full-width index validity, class-probe result, live GC state and CAS completion |
| [Runtime exception wrapper](../../scripts/game_data/ifix_vm_runtime_exception_rules.py) | low-byte wrap selection, constructor request, named Real backing-field store and stop request | allocation, framework initialization, exception state and native delivery |
| [Adjacent exception functions](../../scripts/game_data/ifix_vm_exception_funclet_rules.py) | raw object-word queries, signed container push and literal return programs | incoming frame association, class/relation results, EH entry and return-code meaning |
| [Frame entry](../../scripts/game_data/ifix_vm_entry_frame_rules.py) | first StackSpace check, signed/unsigned count extraction, wrapping capacity comparison and local/top pointer setup | actual capacity, negative counts, wrapped sums, storage and EH frame association |
| [Anonymous info construction](../../scripts/game_data/ifix_vm_anonymous_info_constructor_rules.py) | explicit count/reference defaults and complete array publication store/barrier caller | allocation, compatible full-width index, GC state, aliases and barrier completion |
| [Reflection invoker construction](../../scripts/game_data/ifix_vm_reflection_invoker_constructor_rules.py) | parameter flag/Type setup, return/receiver state and independent Nullable name queries | reflected arrays/results, live flags, allocation, aliases and invocation |
| [Reflection invocation](../../scripts/game_data/ifix_vm_reflection_invoker_rules.py) | complete Call marshaling, Nullable requests, constructor/method selection, reference updates and result/cleanup requests | actual reflection, Type predicates, results, aliases and native EH delivery |
| [Anonymous bridge dispatch](../../scripts/game_data/ifix_vm_bridge_dispatch_rules.py) | named interface, image-qualified direct targets and slot-one fallback | selected manager, generated bridge bodies, live virtual pairs and returned object |
| [Call reference writeback](../../scripts/game_data/ifix_vm_call_reference_update_rules.py) | argument descriptor, saved managed array and fresh thread-stack base passed to stackGet | saved/fresh base identity, descriptor contents, aliases and conversion/writeback results |
| [Reflection cleanup](../../scripts/game_data/ifix_vm_reflection_cleanup_rules.py) | complete Invoke capture producers, result-preserving signed cleanup loops and value-receiver writeback requests | captured storage, loop termination, class-selected marshalling/copy and EH delivery |
| [Scalar Call helpers](../../scripts/game_data/ifix_vm_call_scalar_rules.py) | typed pushes, payload reads and finite narrow/unsigned/pointer adapters | bounds, caller-side narrowing, overlap, helper mutation and actual values |
| [Generic reference reads](../../scripts/game_data/ifix_vm_generic_reference_get_rules.py) and [generic scalar reads](../../scripts/game_data/ifix_vm_generic_scalar_get_rules.py) | reciprocal generic declaration, exact stored contexts and complete ordinary pointer-candidate programs | incoming runtime context, sharing, Type/cast/unbox results and returned storage |
| [Selected generic adjustors](../../scripts/game_data/ifix_vm_generic_adjustor_rules.py) | raw-backed registration-addressed cells and finite boxed-header receiver adjustment/tail programs | logical table extent, runtime index/selection, receiver validity and invocation |
| [Anonymous virtual callers](../../scripts/game_data/ifix_vm_anonymous_virtual_rules.py) | sentinel fallbacks, recursive argument forwarding, result readers, finite Object base entries and detached Finalize frame program | live IDs/storage, exact string-context sharing, framework/recursive results and EH frame delivery |
| [VM construction and lifecycle](../../scripts/game_data/ifix_vm_vm_construction_rules.py) | table setters, logger cache, ObjectClone forwarding and Cleanner state/callback requests | allocation defaults, cache contents, reflection/delegate results, concurrency and native EH |
| [VM table accessors](../../scripts/game_data/ifix_vm_vm_table_accessor_rules.py) | finite registered field reads and stores before the barrier tail | live receiver/table identity, storage, GC, helper mutation and invocation |
| [Descriptor byte overlap](../../scripts/game_data/ifix_vm_instance_byte_alias_rules.py) | snapshot/copy, post-copy signed tag guard and post-rebase store index equations | actual displacement/bytes, stable address premises, managed-array identity/bounds and helper outcomes |

Static initialization suppresses every constructor-table entry equal to the
selected nonnegative ID before requesting execution. The selected helper has
no rollback store. This describes a mutation order under stable storage;
constructor success, concurrency and an actual once-only execution remain
unobserved. The index bridge reads the selected instruction pointer directly
from the runtime table, without its own explicit null or bounds check.

Call construction explicitly stores four fields after its zero-fill request,
then copies all five words. The complete selected helper's bounded paths
clear exactly the requested region, so the fifth word starts zero on normal
completion under valid stable storage and supported instruction-state
assumptions. Call.Begin obtains the thread-local stack and saved Base/Top
pointers through checked construction and lookup callers; allocation results,
capacity and actual TLS contents remain unobserved. Ordinary PushObject writes
at current top before advancing it. PushObjectAsResult instead passes argument
base to the already proved typed pusher and reloads that base after return
before setting top one slot beyond it.

Return cleanup increments a wrapping Int32 counter under
a signed bound; a finite caller proof does not establish termination or a
safe managed range. Throw retains an Int64 physical clear index, while the
pending-zero Endfinally route narrows its corresponding index to Int32.
Catch handler selection requests assignability before testing the try range
and chooses the first matching stored entry; Filter and Fault are skipped.

The instance-alias equations keep whole-Value identity separate from equality
of indexes relative to different buffers. A store snapshots the source bytes,
rebases the field's Value1, then reads source Value1. Under a same-Value
hypothesis that read therefore selects the field index. A load always reads
the physical managed-field index even after rebasing its destination. Managed
reads precede managed writes; later descriptor ownership and recursive lower
tag meanings remain unresolved. The small array helpers compare the low
Int32 index for bounds while forming the address with the full native index,
so that guard alone does not validate an arbitrary wider index.

The separate byte-overlap equations cover hypothetical partial descriptor
overlap. Both negative storey callees snapshot the complete source before
copying it, then reread its signed tag. That copy can enable or disable the
managed branch even when the incoming tag says otherwise. Rebase can change
the source tag again, but neither callee retests it. Stfld reads source Value1
after rebase; Ldfld still selects the physical field index. Neither complete
callee requests Clone. These equations require stable selected addresses and
Value writes separated from headers, native frame and managed-array storage;
they do not establish that any such alias occurs in the client. Managed reads
are captured before the assignment/store requests, with actual array identity,
bounds and helper outcomes left open.

The IFix exception wrapper stores the incoming exception in its named Real
backing field. It supplies no message argument to its constructor's inherited
initialization request. Adjacent exception programs read a raw object header
word and request an anonymous relation check; they do not establish a named
GetType call, actual catch delivery, or the meaning of their literal return
codes. Their container push stores a pointer before incrementing signed depth,
so aliases and helper mutation remain explicit boundaries.

Entry setup extracts signed locals from the operand's upper half and unsigned
reserve from its lower half. Its capacity request follows wrapping Int32
additions and a signed comparison; it does not establish valid counts or
allocated bounds. AnonymousStoreyInfo construction explicitly zeroes its
counts and reference fields, while the publication helper stores the supplied
reference before its barrier request. Reflection invoker construction computes
Out without In, requests reference element Types, and retains the native
low-byte IsStatic XOR for receiver state. Its Nullable HasValue and Value name
checks are independent, with fresh reads and queries preserved.

Reflection Invoke receives the Call value type by reference and uses its
unboxed payload offsets. Its pointer/value queries use the named implementation
slots rather than public convenience wrappers. Constructor and ordinary method
requests preserve their distinct argument order, followed by reference updates,
result pushing and cleanup requests. Call.UpdateReference computes the
descriptor from the saved argument base and uses the saved managed array, but
fetches the evaluation base from a fresh thread-stack lookup. It does not read
Call.evaluationStackBase for that request. Equality of those bases, and any
resulting live reference identity, remain unresolved.

Cleanup authenticates its full Invoke producer prerequisite before assigning
meanings to captured home addresses, including in the standalone validator.
Its callback clears physical managed positions under signed, wrapping count
comparisons, and requests conditional value-receiver writeback. It has no
explicit Call.currentTop write. Native marshalling/class-word selection and
detached depth/frame instructions do not prove successful copies or EH delivery.

Scalar Call pushes preserve the selected integer and floating payload widths.
PushBoolean stores the input byte without normalizing it. GetBoolean tests a
stored dword, while the narrow getter adapters forward GetInt32's return bits
without local narrowing. The ordinary getters guard the computed descriptor
pointer, without a tag or capacity test. The stored generic bool candidate
instead requests an unbox address and copies its returned byte without local
normalization; the native-pointer candidate reads a qword. Its separate byref
bool context is retained without receiving that program claim.

GetAsType has no ordinary MethodDef pointer, but selected typed MethodSpecs
have registered ordinary pointer candidates. The reference program saves
GetObject's result, queries the first generic-context word and requests a cast.
The selected adjustor cells point to finite programs that add the boxed Call
header to the receiver and tail to those candidates. These exact stored cells
do not establish the logical table extent, the runtime-selected context,
sharing, a valid boxed receiver, or an invocation. Anonymous ToString preserves
its own stored string context and joins the same program by MethodDef-family
membership, without inventing an exact string-context table registration.

Anonymous virtual callers preserve the sentinel fallbacks separately from
their recursive VM requests. Patched calls save the receiver and arguments,
reload the virtual ID, and request the result reader on normal completion.
Their detached Finalize program authenticates local frame-word operations,
without establishing that an ordinary call or native EH entered it.
The separate Object base entries provide pointer equality, wrapping receiver
hash arithmetic and a framework ToString tail request. Their finite proofs end
at the return or unconditional tail, without inventing a pdata extent or
including adjacent bytes.

VM table setters store in native order and leave allocation defaults and
existing cache contents unobserved. ObjectClone retains its MemberwiseClone
reflection-query result and forwards the supplied object to MethodBase.Invoke;
the returned object's identity is not established. Cleanner sets its start
byte before allocation, clears it on Stop/static initialization, and requests
Sweep and Start from a nonzero-byte Finalize path. Its constructor is a finite
return entry without a pdata extent. Logger/disposal callbacks and native
exception landings remain request programs.

The small VM getters return the selected field qword. Their setters store the
incoming reference before tail-requesting the write barrier with that field's
address. These finite entries perform no local null/type check, allocation,
element initialization or cache clearing. Actual receiver and table identity,
GC completion, helper mutation and invocation remain unobserved.

The anonymous loader's buffer route repeats until its signed accumulated
read count reaches four, rejecting zero and otherwise trusting returned
counts. Its MemoryStream route writes the advanced position before checking
length. Allocation receives the count's zero-extended raw Int32 bits without
an explicit nonnegative caller guard. These requests do not prove successful
reads or allocation, and they do not supply the runtime reflection-sized
method counts needed to widen the raw anonymous-storey reader.

**Level 4 (partial):** declared fix targets and conditional VM invoker flow
only. There is no runtime receipt of load, dispatch or behavior. A runtime
claim needs a trace tying the accepted patch-file hash to `LoadInternal`, the
selected fix record to its registered wrapper identity, and
`IsPatched`/`GetPatch` to an `Execute` entry at this VM instruction. Static
method bodies and the installed patch files cannot supply those observed
transitions.

## Runtime alias and generic-context evidence

The shared [capture requirements](../runtime_capture_requirements.md#ifix)
hold the pending IFix checklist. Append future capture needs to that document;
this topic retains the interpretation and evidence boundaries.

The [saved-evidence auditor](../../scripts/game_data/ifix_runtime_evidence.py)
rebinds retained entry inspections to their collection inventory, profile and
provider summary, then compares declared code sites with the selected IFix
native targets. Its [reviewed requirements](../../scripts/game_data/contracts/ifix_runtime_evidence.json)
name the alias, generic-context and patch-execution questions separately.
The auditor reuses the unchanged passing native proof and checks the explicit
selected build before producing a report. It reports capabilities and refusals;
it does not admit IFix runtime observations or implement a paired recorder.

The retained Mission/Buff entry formats do not provide IFix Value byte ranges,
post-copy tag reads, post-rebase index reads or effective query contexts. A
generic AssignData registration and raw argument references also do not supply
a live MethodInfo or closed-type observation. Unhit registered entries remain
unhit. Those sessions can retain their original admitted evidence without
closing these IFix questions.

An alias observation needs the actual source and destination descriptor
addresses and pre-copy bytes at a bound native site. Its consequences require
the post-copy guard, conditional rebase and subsequent managed read/store
phases to be correlated with the same call. Repeated receiver, array/header
and computed-field-address stability must support the equation's premises.
Shared array identity, valid indexes and a completed assignment are separate
facts. An entry-only pointer match cannot establish those phases, object
lifetime or a successful write.

A retained caller address needs authenticated same-session module identity
before rebasing. A bound caller site or preserved thread instruction pointer
can locate sampled code; alias and context claims still require their own
correlated phase observations.

For GetAsType, the ordinary candidate saves the incoming opaque context and
uses its first context entry after preparation and GetObject. Preparation and
other helpers can change that storage, so an entry snapshot is insufficient
to identify the effective query. Raw incoming/effective pointer bits, a Type
query result and a closed generic declaration each need their own proof.
An ordinary code address or stored MethodSpec index does not select the live
closed type. Adjustor entry selection also needs the incoming boxed receiver
and the receiver/context forwarded to the ordinary target to be observed.

The Func bridges reload their result-type context entry after Execute and
GetObject; the selected entry follows the generic input entries. Their incoming
context carrier changes with the entry's argument count. Action bridges only
test and prepare their context carrier, with no local typed result query.
Native hidden contexts and managed reflection MethodInfo references are
different representations; neither supplies the other's runtime identity.

The local observer has no admitted IFix phase/return protocol in these saved
formats. Live collection remains a distinct internal tooling task under the
repository's instrumentation rules. Preparation, a complete unrelated session
or missing hook coverage never becomes a runtime execution claim.
