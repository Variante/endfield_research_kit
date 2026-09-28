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

The VM method index and the AOT wrapper's `IsPatched` id are **different
identity domains**: `ifix_patch.py` reads the former from the file,
[`body_claims.py`](../../scripts/game_data/il2cpp/body_claims.py) the latter
from a native method's test, and they differ for the same fixed methods. Never
join the two integers or read an AOT id as a VM body offset. A `None` from
`BodyIndex.ifix_patch_id` means *not found by its bounded search*, not
*unwrapped* or *not fixed*; the fix record is the authority.

## Opcodes, operands, frames and signatures

Every module below derives its facts from the explicit selected
`GameAssembly.dll`/`global-metadata.dat` pair and checks the reviewed contract's
method identities and complete body bytes before projecting anything, failing
closed on a mismatch. A **row join** (an operand naming a declared file row) is
direct under the selected build and the supplied bytes; every **stack, slot or
resume effect** is conditional on the native path returning normally. Execution
is never observed. The native facts behind each rule are listed in
`validate_vm_operand_contract` in
[`ifix_vm_operands_native.py`](../../scripts/game_data/ifix_vm_operands_native.py),
against the reviewed
[`ifix_vm_operands_native.json`](../../scripts/game_data/contracts/ifix_vm_operands_native.json).

| Operands | Rule under the selected `LoadInternal`/`Execute` bodies |
| --- | --- |
| every opcode | `IFix.Core.Instruction` is 8 bytes (`Code`, `Operand`); the `IFix.Core.Code` enum names every current instruction and unknown codes fail closed ([`ifix_vm_instruction_native.py`](../../scripts/game_data/ifix_vm_instruction_native.py)) |
| `Call`, `Callvirt` | low 16 bits index `unmanagedCodes` (file body order); the signed upper half is the recursive `argsCount` |
| `CallExtern`, `Newobj` | low 16 bits index `externMethods`; the signed upper half rewinds that many 12-byte evaluation slots to the argument base, a stack count rather than a parameter count; `Newobj` takes a separate path for delegate constructors |
| `CallExtern` result | a cache miss builds a `ReflectionMethodInvoker` whose `Invoke` pushes a nonvoid result through `Call.PushObjectAsResult`: a conditional data-flow path |
| `Br`, `Brtrue`, `Brfalse` | signed offsets relative to the current instruction; a target outside the method span is marked out of range, never given a row |
| `Leave`, `Endfinally -1` | `Leave` stores a pending absolute index that `Endfinally -1` resumes when it is nonzero; `Leave 0` is a sentinel, not a resume edge |
| `Ldstr`, `Ldfld`, `Ldsfld`, `Stfld`, `Stsfld` | index `internStrings` / `fieldInfos` in file order; negative field operands take another native path, left unresolved |
| `Initobj`, `Constrained` | index `externTypes` in file order; `Initobj` after `Ldloca` updates that local slot with an `Activator.CreateInstance` object; `Constrained` converts the slot its preceding operand selects to an object |
| `StackSpace`, `Ldarg`, `Ldloc`/`Ldloca`/`Stloc`, `Ret` | the frame header reserves local and evaluation slots; locals index after the runtime argument count; `Ret` with a nonzero operand returns the top value |
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
agreement. The current two-file input set passes; without those arguments the
result is a projection over caller-supplied bytes, not a current installed-file
claim.

## Remaining boundary

**Level 3 (partial):** opcodes and selected operand routes through
authenticated file-VM code, frame slots, exception records, and uniquely
resolved external signatures. The delegate-construction path and other
unreviewed opcode operands remain uninterpreted.

**Level 4 (partial):** declared fix targets and conditional VM invoker flow
only. There is no runtime receipt of load, dispatch or behavior. A runtime
claim needs a trace tying the accepted patch-file hash to `LoadInternal`, the
selected fix record to its registered wrapper identity, and
`IsPatched`/`GetPatch` to an `Execute` entry at this VM instruction. Static
method bodies and the installed patch files cannot supply those observed
transitions.
