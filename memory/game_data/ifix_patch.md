# IFix patch records and native wrappers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, code lane.** This file owns what a decoded `IFixPatchOut` record
proves about a replacement target, and where that proof stops. The exact
framing boundary belongs to
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

## From installed bytes to a replacement target

`IFixPatchOut` is an encrypted VFS block. A direct AnimeStudio
`dump -b i-fix-patch --verify-md5` from the active Persistent root, with
StreamingAssets fallback, supplies the decoded logical bytes. The maintained
[`ifix_patch.py`](../../scripts/game_data/ifix_patch.py) reader consumes the
current files exactly: a bounded opaque prefix precedes the IFix file-VM
stream; the stream has strings, external type and method tables, raw
instruction/exception spans, and fix records. The parser validates lengths,
indices it understands, canonical string lengths, and EOF. The source
declarations and exact current file census are in the reader and its local
corpus report, not in this topic.

The selected native build declares `IFix.Core.Instruction` as an eight-byte
value type with 32-bit `Code` and `Operand` fields. Its `IFix.Core.Code` enum
names the first word. The maintained
[`ifix_vm_instruction_native.py`](../../scripts/game_data/ifix_vm_instruction_native.py)
derives that layout and enum from an explicit selected `GameAssembly.dll` and
`global-metadata.dat` pair, checks the native sizes and field offsets, then
names every instruction opcode inside the parser's exact method spans. Every
instruction in the freshly dumped patch files maps to a named enum member.
Unknown codes fail closed. The opcode name alone does not interpret its
numeric operand. The generated instruction inventory belongs in
`reports/animestudio/`.

The reviewed
[`ifix_vm_operands_native.json`](../../scripts/game_data/contracts/ifix_vm_operands_native.json)
contract pins the selected native `PatchManager.LoadInternal` and
`VirtualMachine.Execute` bodies and the VM table fields. Its
[`validator`](../../scripts/game_data/ifix_vm_operands_native.py)
checks the explicit native inputs, both method identities and complete body
bytes, field offsets, and opcode enum before projecting an operand.
`LoadInternal` reads each file VM body in sequence and stores its code at
the same index in `unmanagedCodes`. It likewise reads each external method
signature in sequence and stores its resolved method at the same index in
`externMethods`; it allocates `externInvokers` from that table's length.
`Execute` makes the second half of the join: `Call` and `Callvirt` use the
operand's low 16 bits as an index into `unmanagedCodes`; `CallExtern` and
`Newobj` use the same low half for external method lookup, with
`CallExtern` consulting the invoker cache first. Thus a valid low-half index
directly identifies one **declared file row**, conditional on the selected
native build and caller-supplied patch bytes. For `Call` and `Callvirt`, the
signed upper 16 bits are forwarded as `argsCount` to a recursive `Execute`
call. For `CallExtern`, the selected path multiplies the signed upper half by
the 12-byte VM slot size and subtracts it from the evaluation-stack top to
form the external call's argument base. The reviewed contract pins the
arithmetic helper bytes and call sites. This is a stack rewind count, not a
claim about the reflected method's parameter count. `Newobj` first reads
the resolved constructor's declaring type and its base type through the
selected virtual slots. It compares that base with the selected
`System.MulticastDelegate` type. If they differ, `Newobj` joins the same
signed-upper-half stack-rewind path as `CallExtern`; delegate construction
takes a separate path. The validator checks the virtual slots, helper bytes,
type-usage cell, pointer comparison, branch target, and shared rewind calls.
The current patch's three `Newobj` upper halves are 0, 3, and 0, matching
the file-declared constructor parameter counts. This is a **conditional
native operand rule**, since actual reflection selection and execution are
unobserved.

An IFix generic method signature stores ordinary type indices and generic
parameter names in separate streams, interleaved by a flag for each parameter.
The older text-only reference printer dropped the generic positions; its
shortened `LogError` spelling was incomplete. The maintained
[`ordered_signature_parameters`](../../scripts/game_data/ifix_patch.py)
restores the file order. The
[`external signature audit`](../../scripts/game_data/ifix_external_signatures_native.py)
then substitutes constructed owner and method arguments, including byref
parameters, and requires a unique full signature in the explicit selected
IL2CPP metadata pair. Every external declaration in the current patch files
has one such metadata definition. Its return type and static flag are direct
selected-build facts; the runtime reflection selection and invocation remain
unobserved. The per-build method inventory belongs in `reports/animestudio/`.

The same selected `Execute` body interprets `Br`, `Brtrue`, and `Brfalse`
operands as **signed instruction offsets relative to the current
instruction**. A taken branch adds that offset to the current instruction
pointer; conditional fallthrough advances one instruction. The validator
publishes both authored edges and marks a target outside the method's
instruction span as out of range, without assigning it a file row. It does
not decide which conditional edge ran. `Leave` uses a different rule: its
signed operand is stored as a pending **absolute instruction index**.
`Endfinally` with operand -1 resumes at that index when the pending value
is nonzero. The selected interpreter multiplies the index by the eight-byte
instruction size, adds the method code base, clears the pending value, and
returns to opcode dispatch. The validator checks the operand read, pending
store and read, code-base use, helper calls, and selected helper bytes. A
zero pending value takes another path, so the projection marks a `Leave 0`
target as a sentinel rather than a direct resume edge.

The same authenticated `LoadInternal` body reads each 24-byte exception
record as six signed `BinaryReader.ReadInt32` values, then stores them in
`ExceptionHandler` fields in this file order: `HandlerType`, `CatchTypeId`,
`TryStart`, `TryEnd`, `HandlerStart`, `HandlerEnd`. The
[`operand validator`](../../scripts/game_data/ifix_vm_operands_native.py)
checks the six read calls, their field stores, the runtime field offsets,
and the selected `ExceptionHandlerType` enum against its reviewed contract
before naming a record. The current Gameplay `_InitLoader` VM body declares
one `Finally` handler (`HandlerType` 2, `CatchTypeId` -1). Its try boundary
indices are 42 and 109; its handler boundary indices are 109 and 114,
all within the body's 117 instructions. In the authored code, instruction
107 is `Leave 114`, instruction 108 branches to 109, the handler begins
at 109, instruction 113 is `Endfinally -1`, and instruction 114 follows
the handler. This is a direct authored cleanup and resume chain under the
selected interpreter. Whether the path ran remains unobserved.

`LoadInternal` also preserves the file's `internStrings` and `fieldInfos`
row order in the VM tables. In `Execute`, `Ldstr` indexes `internStrings`;
the nonnegative operand paths for `Ldfld`, `Ldsfld`, `Stfld`, and `Stsfld`
index `fieldInfos`. The reviewed contract authenticates these consumer
paths and their table fields. Every such operand in the current patch files
is nonnegative and resolves to an in-range row. Negative field operands
select another native path, which the validator leaves unresolved rather
than interpreting as a file-field index. The named field rows describe
**authored references**; they do not prove a load, store, or resulting value
occurred at runtime.

`Execute` treats the first `StackSpace` instruction as a frame header before
dispatching ordinary opcodes. The header's signed upper 16 bits reserve
local slots, its unsigned lower 16 bits reserve evaluation-stack slots, and
execution starts at the next instruction. `Ldarg` indexes the runtime
`argumentBase`; `Ldloc`, `Ldloca`, and `Stloc` index the local base after the
runtime argument count. The header and local indices in the current files
are consistent: every local reference fits its method's declared local
count. An `Ldarg` index names an argument slot. The file supplies `argsCount`
for a recursive `Call` or `Callvirt` edge, while an externally entered
replacement's invocation count remains unobserved. `Ret` with operand zero
returns no stack value; a nonzero operand selects the top evaluation-stack
value. This explains the getter/setter-like shape of the Gameplay helper
bodies and the Rendering body's return instruction.

The selected `CallExtern` cache-miss path constructs a
`ReflectionMethodInvoker` from the resolved external method. Its encoded
MethodDef usage cell resolves exactly to
`ReflectionMethodInvoker.Invoke`, the delegate target. The reviewed contract
authenticates that cell, the constructor and invoke bodies, and the direct
calls. For a normally returning nonconstructor method with a nonvoid return,
`Invoke` calls `Call.PushObjectAsResult`; that helper pushes the reflected
result and updates the call's stack top, which `Execute` reads after the
delegate returns. This is a **conditional native data-flow path**, not an
observed invocation or result value.

A fix record binds a CLR method signature to an index in the patch's VM method
body table. That is direct evidence of a *declared replacement target* in this
file. An external-method table entry is a reference available to patch code;
it does not make that method a replacement target. The selected native
projection decodes reviewed operands and the exception record; those authored
declarations alone do not prove
the replacement's behavior, that the runtime loaded the file, or that any
call entered the patch. A target name is not an execution trace.

The VM method index and the AOT wrapper's `IsPatched` id are different identity
domains. `ifix_patch.py` reads the former from the file;
[`body_claims.py`](../../scripts/game_data/il2cpp/body_claims.py) reads the
latter from a native method's test. The current native spot-check finds
different values for the same fixed methods. Do not join these integers or
read an AOT id as an offset into the VM body table.

### The shipped patch declarations do not directly replace the checked PlaySound route

A fresh direct `IFixPatchOut` VFS dump with chunk and file MD5 verification
matches the earlier parsed patch-byte identities. The maintained `ifix_patch.py`
reader closes every dumped file to EOF and resolves each fix record's declaring
type and method name through its own external-type table. None of those
declared replacement targets is a named method in the checked default
PlaySound string-to-hash route recorded by
[`audio_play_sound_string_native.json`](../../scripts/game_data/contracts/audio_play_sound_string_native.json).
The current target rows and source digests are in the generated
`reports/audio/play_sound_ifix_targets_current.json`.

This is an exact absence from the installed files' **declared fix targets**.
An external reference inside a patch is not a replacement, and the file
declarations do not establish patch loading, runtime activation, or the path
actually taken by a PlaySound action. The selected default-body proof and its
remaining runtime boundary belong in
[`audio_native_hooks.md`](audio_native_hooks.md).

## Correcting the older mission reading

An older local mission audit describes a different patch payload and must not
be carried forward as current. A fresh direct VFS dump on the selected native
build matches the reviewed
[`ifix_patch.json`](../../scripts/game_data/contracts/ifix_patch.json)
Gameplay payload, and the active fix-record set is different. The older audit
must not be cited as current. The selected contract's fixed-target and
external-reference classifications contain no direct task-completion or
receiver-ownership match. This is a narrow negative over the decoded records,
not proof that the patch has no indirect effect on missions or Story. The
current file names and counts are in the local
`reports/story/recovery/current_ifix_mission_graph_audit.md` and the reviewed
contract.

There is a second, independent currentness gate. The production
[`ifix_patch_native.py`](../../scripts/game_data/ifix_patch_native.py) loader
checks the contract against the selected `GameAssembly.dll` and
`global-metadata.dat`, but it does **not** read the live VFS patch. Its
`validated` status proves the native pair and contract shape, not that a
patch-only hotfix still has the contract's `patchSha256`. For a current patch
claim, compare that digest with a fresh, MD5-verified VFS dump before using
the contract's target list. A native build match alone is insufficient.

The native helper `BodyIndex.ifix_patch_id` searches a bounded early window
for `IsPatched`. In the selected build, one method named by a fix record has
its first direct `IsPatched` call after that window because class
initialization precedes it. The helper returns `None` there. That result
means **not found by this bounded search**, not **unwrapped** or **not fixed**.
Later calls in the same long body may come from inlined methods, so merely
increasing the window does not safely identify the target's own id. The
patch's fix record is the authority for the declared replacement target.

## Remaining boundary

The selected native loader and interpreter bodies establish direct call,
branch, field, string, frame-slot, and return-operand readings. Every file
index, branch target, and local slot in the current patch fits its declared
table, method body, or frame. In the Gameplay patch, the `_InitLoader` replacement
body declares calls to three other VM bodies, and the external signatures
include typed `DeserializeFromJson` returns for both the list and per-level
UI map load configs, byref level-config lookups, and the loader-data
constructor. These are authored call sites with unique selected metadata
definitions, not evidence that the calls ran. Its field references cluster
around map loader configuration, inverse-coordinate setup, and loader-data
lookup dictionaries; the `NetClientManager.Launch` body references session and
network-limit fields. The three recursive call operands pass counts that cover
every authored `Ldarg` slot in their target helpers. One small helper has a
getter-like `Ldarg`/`Ldfld`/
`Ret` shape for `DataManager.uiLevelMapConfig`; two have setter-like
`Ldarg`/`Stfld`/`Ret` shapes for MapManager grid lengths. This is an inference
from authored opcode order and named field rows. The Rendering patch body
names the `_Crash1` string, calls
`ShaderWarmupManager._IsFeatureEnabled`, and requests a stack-value return.
The selected metadata declares that referenced method as static
`bool _IsFeatureEnabled(string featureKeyword)`; the authored string is its
apparent argument. Its `CallExtern` rewinds one slot after `Ldstr`, and `Ret 1`
selects the reflected result on the normal-return path above. The actual bool
value is unobserved.
These are **authored references and control-flow edges**, not proof that a patch ran or produced
an effect. The delegate-construction path and other unreviewed opcode
operands remain uninterpreted.
A runtime claim additionally needs
an authenticated load and dispatch receipt.
