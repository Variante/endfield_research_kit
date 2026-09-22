# How far each reader is proven

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, extraction lane.** One statement per payload family: which reader is
fail-closed, how far its framing is exact, and where it stops. This is the
*boundary* layer -- what the data inside a family means belongs to that family's
lane file, and a reader boundary here never implies a semantic there.

## VFS and payload recovery

The outer VFS boundary and each inner payload schema are separate claims. A
validated range/hash proves the bytes under study, not their fields or runtime
meaning. Start at the VFS recovery evidence index in the AnimeStudio skill
reference; it maps each active family to its maintained reader, fixtures,
corpus report, and remaining boundary.

A parser becomes exact only after positive fixtures, truncated/malformed/
trailing-byte negatives, exact-consumption checks, and a current-corpus sweep.
Keep authored field names, envelope framing, cross-file ownership, and observed
runtime behavior as separate evidence layers. Changing totals and source
fingerprints belong in generated reports.

## Current durable boundaries, per family

Current durable boundaries:

- Bundle and InitBundle nested-container framing, current VFS logical-file
  reads, Terrain and Streaming envelopes, all five DynamicStreaming root
  families, LipSync payloads, video outer framing, and several routed JsonData
  families have fail-closed readers. SpawnerConfig framing treats the integer
  dictionary key and serialized string wave key as independent fields; exact
  wave maps still require one unique bounded parse through physical EOF.
  Every current SpawnerConfig file independently closes the exact named
  enemy-library prefix; files whose wave map does not close remain bounded
  partial rather than unclassified.
  Terrain additionally validates its body-length word against the complete
  decoded payload. A current-build UnityPlayer reader, IL2CPP GraphicsFormat
  enum, and native format-footprint table now close every selected-build body
  as exact contiguous anonymous ranges. In particular, raw words 108/109 are
  BC7 sRGB/UNorm footprints with 16 bytes per 4x4 block; the 1024-to-1 bodies
  split into eleven ranges and consume EOF. Offset 14 is therefore a direct
  format selector, while offset 12's numeric mip-count interpretation remains
  inferred. Block contents, D/N path meaning, texture-array ownership, and
  final rendering remain unresolved; unobserved header tuples fail closed.
- The current Table corpus has a direct low-output sweep covering selected
  overlay provenance, decoded MD5, exact read length, SparkBuffer parsing, and
  EOF for every metadata declaration. BundleManifest and IFixPatchOut likewise
  have current exact framing sweeps. BundleManifest uses corrected size/count
  fixed-width sections plus a repeated-size terminal variable envelope. Its
  variable payload begins with a gap-free sequential anonymous span of UTF-16LE
  fragments and three counted-u32 regions per record; its 48-byte rows index a
  second span with the same record multiset under a different order. Terminal
  bytes stay opaque. It has
  exact inner-file-count, basename-multiplicity, and row-index witnesses, but
  no serialized field ownership. Stale AssetMap source chunks cannot supply it.
  Exact method pins exist, but unresolved stream/ref-out carriers still block a
  safe lookup capture ABI. IFix instruction/runtime meanings remain separate
  claims.
- Irradiance-volume region framing is exact for seven files; all 92 IV indexes
  have a bounded unique UTF-16LE filename-table parser that references the 138
  remaining payloads exactly once. Supported single/grouped v3 indexes strictly
  bind filename-ordered groups to ranges that restart at zero and cover each
  payload through EOF without gaps or overlaps. Directory starts may use
  absolute or filename-table-end-relative four-byte alignment, but the combined
  candidate must remain unique. Other words and renderer meanings stay opaque;
  legacy indexes use a separate EOF-ending 24-record directory whose grouped
  ranges also tile every referenced payload. All indexed payload boundaries are
  now exact; record and renderer semantics remain open.
- IV runtime capture has a narrow UnityPlayer parser/cursor candidate, but must
  still close exact module/build/entry/caller, buffer-length, and final-cursor
  contracts. A generic file-I/O hook cannot preserve the authenticated virtual-
  path/hash join, and a stale capture manifest must fail preflight before the
  game starts. The current native parsers have no payload-length parameter or
  final EOF check, and repeated in-payload magic values rule out signature
  scanning as a replacement boundary witness.
- Audio has fail-closed AKPK/BNK/DIDX/DATA/media framing and a direct audit;
  its non-voice HIRC lane now exact-frames numeric object envelopes and keeps
  unknown types. HIRC behavior, selected runtime playback, and audibility
  remain separate.
- Audio availability is data-driven rather than type-excluded: shared and all
  language blocks parse normally whenever any declared chunk exists. A block
  wholly absent from both overlay roots remains visible as a conditional
  missing terminal state and does not fail; partial presence, bad hashes, and
  malformed payloads remain fail-closed.

## Corpus freshness, and why a report hash is not enough

Saved corpus consumers must recheck live catalog, build, CLI, parser and chunk
fingerprints at both ends; authenticating the report hash alone does not
establish freshness after a tool rebuild. Reauthenticate affected bytes with
the rebuilt tool rather than rewriting old provenance pins.
A corpus report is authenticated by that live provenance, not by a digest of
its own bytes pinned in code: the context audit hashes its SkillData basis only
to prove the file is stable while it runs. Each MemoryPack family report pins
the static import closure of its own gate inside `memorypack/` (imports inside
functions included), so an executed helper cannot escape provenance, while an
unrelated family's reader edit no longer stales every other report.
DummyDll population and setter declarations do not fill these gaps. Historical
residual JsonData censuses supply family leads, not current denominators
without a ledger rejoin. `jsondata_corpus` now owns that block-wide ledger
rejoin: it matches every current logical identity to `export_full/game/Json`
by safe relative path, exact length, and logical MD5, then records one terminal
state per file. Complete UTF-8 JSON syntax, exact schema readers, anonymous
exact frames, bounded partial frames, bounded ambiguous frames, unsupported
reader variants, and unclassified binary payloads remain distinct. It invokes only maintained
readers and never promotes a payload from its path, extension, or leading
MemoryPack member count. The generated summary and per-file ledger live under
`reports/animestudio/`; family-specific gates remain the authority for deeper
formatter, native-input, cursor, and semantic claims. BuffData and SkillData
are joined through their complete current family reports: the registry checks
the report contract and identity-set digest, requires a one-to-one current-ledger
path set, and rechecks each report length, logical MD5, and logical SHA-256
against the exported bytes. BuffData rows with a contiguous named 30-field
outer cursor are `format_framed`; rows stopped by a positive unsupported modifier list or
unsupported action remain `bounded_partial`. SkillData stays
`bounded_partial_ambiguous`.
LevelData's sequential generated-order reader closes the complete 43-field
schema for supported empty/null shapes, including exact member-22
`LevelScriptBriefData` dictionaries. It also advances exact camera-pose rows
and the current environment-volume profile, including the authored phase-asset
path and polygon/transform boundary. Map-region shapes/tier links and spline
knots/progress/owner transforms also have exact sequential codecs. The same
cursor now closes all 34 generated fields of each authored NPC attract point,
including linked waypoint/point IDs, pose, tags, animation selectors and timing;
runtime point selection remains outside this static payload evidence. Terminal
world-waypoint graphs also close their generated nine-field records and nested
lane direction/count values. Positive LevelData enemy lists reuse the exact
30-member LevelEnemyData value codec already owned by LevelScript; this closes
the list cursor without weakening either owner's later-field boundary. The
following enemy-patrol lists also close their current owner, point and fixed
action wrappers through the next LevelData field. NPC patrol owners, point
poses, and current concrete point actions now close sequentially. The current
action lane includes
populated blackboard pairs plus the observed environment-talk and play-audio
union routes; an unknown future route remains fail-closed. The separate
top-level patrol list closes the generated 39-member authored patrol and
four-member action wrappers also used by Spawner routes. Positive LevelData
interactive-lock lists reuse the exact two-field lock owner
and nested 18-member lock codec from LevelScript, then hand off at the next
top-level field. The current top-level `specificData` union also closes its
tag-zero eight-member spaceship wrapper, including cabin slots and showcase
poses, before the remaining LevelData fields. Level-wide bamboo-raft maps also
close their nested dictionary and the current raft/dock union wrappers,
including typed or null dock-filter conditions. Other files stop at the first unsupported
nonempty nested body and also retain one independent EOF frame: the short suffix
is `safeZone` through `worldWayPointData`, while the longer empty tail is
`levelIdNum` through `worldWayPointData`.

The same registry now routes every current binary JsonData identity: exact
readers close LevelConfig, NavMesh, TeleportValidation, DialogId,
AetherEnergyLock, MatrixShockWave, compact MissionArea, BambooRaft,
InteractiveTable, CharInteractPerform, and the supported Spawner/Interactive variants.
SpawnerConfig now uses its generated five-field order to join the exact enemy
library to route maps, settings and the terminal wave cursor. Empty-action
route patrols and current spawn-monster/pause/raise-event group actions close
sequentially; positive polymorphic route actions retain their earlier prefix.
Remaining
families are explicitly bounded rather than unclassified: empty-action-map
LevelScript files now follow a generated-order owner cursor through named
activation, collection, identity and reset fields. Files whose nested owner
collections and task map are null or empty close a complete schema at EOF;
positive collections stop at their named count without a scan. Most other
current LevelScript files expose a unique named five-member terminal suffix
through physical EOF, while their earlier members retain weaker partial
framing. LevelData, BuffData, and SkillData preserve
their partial boundaries; montage-bearing AnimationConfig files advance a
named five-member wrapper prefix before their opaque nested unions; GPU UI
DamageText now has named PrefabGroup/Prefab/Animation outer framing, while the
ExtendedPrefabGroup GPU UI roots close their complete named schemas, including
animation, node metadata, render nodes, subroots and texture-hash tails.
Unsupported Spawner/Interactive tails keep their opaque or ambiguous ranges
visible. A complete registry is
therefore an accounting result, while whole-schema and semantic recovery remain
per-family claims. AnimationConfig's empty-montage shape is a named exception:
its current 72-byte frames and one 270-byte ability mirror follow the exact
generated wrapper order and contain no opaque bytes. The larger mirror closes
populated sync-group and time-reference `FAnimationCurve` dictionaries with
exact fixed-width keyframes; populated polymorphic montage dictionaries remain
partial.

SkillData now has whole-object cursor proof for the current empty-ActionGroup
profile: an accepted live receipt authenticates every field cursor on two
byte-distinct samples, and a wrapper/type-driven reader generalizes only that
identical field-0 representation. One field-42 nested action tag remains
unsupported, while non-empty ActionGroup rows retain their bounded prefix and
authenticated five-field terminal. NPC MontageNew has a current
ledger/stream gate in `memorypack.npc_montage_corpus`; it binds each identity by
path, length, and logical MD5 and requires exact EOF closure. Current generated
formatter setters name the three root fields and all 24 `NPCMontageAnim`
members, plus `AnimClipInfo`, `DynamicEntity`, `EventInfo`, and transition
overrides. The nested extra-effect reader consumes both 12-byte vectors and its
single following mount path, and the parent consumes every remaining generated
field through EOF. This is a complete named stored schema; field names alone do
not prove runtime selection or playback.

## The Streaming and chunk families, framed to their native consumer

StreamingChunkInfo exact-frames the anonymous
table/vector graph in all 89 current files, including reused/forward vtables
and 4/8/12-byte vector widths; every nonzero byte is owned and the sole
four-byte gap is zero alignment. InitChunkData and StreamingChunkData also
share three exact anonymous subgraphs across all current files. Root field 2
is a width-4 table-offset vector: Init has an empty vector ending at EOF;
Streaming closes each immediate table/vtable against seven selected-build
layouts, and row field 5 is an exact count-prefixed vector of anonymous
little-endian scalar32 values. This terminal subgraph is continuous from the
field-2 vector
start through decoded EOF. Each row object also partitions exactly into its
four-byte vtable displacement and present slot-to-next-boundary spans:
fields 0/1/2 use 4-byte spans, field 3 uses 8, field 4 uses 24, and field 5
uses its proven 4-byte uoffset slot. A current-build hash-gated UnityPlayer
consumer and accessors directly close fields 0--2 as scalar32, field 3
as two int32 loads, and field 4 as six float32 loads. The same producer
retains the source row pointer at offset 16 of a copied 72-byte runtime
record; a later state consumer reloads it, reads the field-5 count and each
`vector+4+index*4` element, and passes the scalar32 value to a hash-table
lookup. Fields 0--5 therefore contain no padding and are directly consumed
in these representations. The numeric filename family has an exact current-corpus relation:
the field-3 lanes floor-divided by 128 equal the first two filename integers,
with residuals limited to 0/32/64/96; present fields 1/2 equal the last two
integers. The Global family has a separate present-field 1/2 relation to its
two integers. A separately hash-gated family-level native read path now
closes its payload base, requested length, returned byte count, exact-read
success branch, and `base + u32(base)` root calculation. Its first formatted
leaf is exactly `StreamingChunkInfo`, but the runtime root is unavailable,
leaving a bounded authenticated candidate set instead of one logical-file
identity. After I/O the selected closure is proven pointer-only: outer
length never reaches the FlatBuffer accessors and no parsed-length or final
cursor exists there. A separate hash-gated static chain carries anonymous
scene-root pairs through a state-selected 16-byte handle to two secondary
reads and the second root's field-2 row vector; the scheduler edge to one
concrete Create instance and both concrete paths remain unresolved. These
fields remain anonymous: the field-5 key namespace and signedness are
unresolved, and the matching managed `GridData` shape is candidate-only.
Root fields 3/4/5 have widths 4/1/4, equal counts, bounded field-5 row tables,
and a bounded row-field-0 byte range whose string/byte-vector representation
stays ambiguous. Rows with field 5 close only its empty count prefix,
not its element width, and field 3 as a nested table with equal-count
width-4/1/4 vectors. The marker-17 wrapper/byte-range closure and its
unresolved type boundary are owned by
[`game_data/install_and_vfs.md`](install_and_vfs.md); all other
nested targets remain opaque. Marker 15 additionally has bounded uoffset
targets, with widths unresolved and no target-byte ownership. Root fields
6/7 retain paired-group, descriptor, and blob-length closure. Bytes outside
the certified subgraphs stay opaque; no union, entity, component, matrix,
descriptor, field name, or runtime meaning follows.

## Catalogs, and what stays incomplete

- Both StringPathHash dictionaries and FacBoneTRS now self-bound their lookup
  and value pools. FacBoneTRS proves its file-provided unit count, observed
  boundary overlaps, contiguous bone records, and 64-byte ranges through EOF;
  every value is shape-consistent with a row-vector homogeneous rigid-affine
  4x4 float representation. The exact type/convention remains unnamed, and
  unit/bone hashes have no exact match in either StringPathHash dictionary.
- Terrain block/channel meaning, Streaming's concrete runtime-root/secondary-
  path joins and field-5 key namespace/ownership, nested parallel-vector
  element targets,
  remaining tails,
  manifest-row, mmap value semantics, patch-instruction/runtime, and remaining
  JsonData semantics are incomplete.
- Material and shader extraction preserves recoverable metadata; it does not
  prove renderer ownership, selected variants, final lighting, or appearance.

## Measuring a boundary, and the JsonData recovery order

A family's *status* says whether a reader closed it; it does not say how much
of a file is understood, and the obvious proxy is wrong. `bytesConsumed` is how
far a cursor reached, not how much it named: a framing anchored on a file's
tail reports EOF while declaring an opaque prefix. Scoring LevelScriptData that
way reads 66%; the honest figure is 39%.

`scripts/game_data/jsondata_schema_coverage.py` computes it as
`min(bytesConsumed, size)` minus the declared opaque spans inside that reach.
An unreached tail and a declared opaque span are different omissions -- one was
never looked at, the other was bounded and left anonymous on purpose -- but
neither is named, so neither counts. One class must stay separate: a framing
that advertises opaque content in its own status yet declares no span cannot be
scored at all, and is reported `unmeasurable` rather than credited as whole. A
reader that declares its opaque ranges is being more honest than one that stops
early in silence, not less covered.

That measurement, not file count, sets the order. The JsonData work concentrates
in four places, largest unnamed region first:

1. **LevelScriptData `opaqueRemainder`** -- the non-empty action-map records.
   The framing names the first record's prefix and stops, leaving the bulk of
   the family's bytes anonymous. This is the single largest unnamed region in
   the lane and the one codec that would move the number most. What blocks it
   is not the framing but the union table; see below.
2. **LevelScriptData `opaqueTopLevelPrefix`** -- files recovered from their
   tail. The five-member terminal suffix is exact through EOF; the earlier
   members are unnamed. Recovering these is the same action-map problem
   approached from the other end, so treat 1 and 2 as one target.
3. **BuffData** -- every current file is a `structural-prefix`; none is
   whole-schema exact. The named 30-field prefix and proven event prefix hold,
   and the suffix stays anonymous.
4. **SkillData** -- a minority of files are `exact-closed` through a named
   profile; the rest keep a bounded prefix and an authenticated terminal.
   Extending the profile route is incremental and already has its pattern.

Everything else in the lane is closed or plain JSON: LipSync, LevelData,
Interactive, SpawnerConfig, LevelConfig, AtmosphericNpcData,
CharInteractPerformCfgs, AnimationConfig, NavMesh and the GPU UI roots decode
against their readers, and MissionRuntimeAsset, MapConfig, UILevelMapLoadConfig
and the small config families are real JSON. Do not spend effort there.

`LevelScriptTemplateData` is a trap worth naming: its opaque-middle files look
complete because the framing reaches EOF without locating what it skipped. They
are unmeasured, not covered. Give that reader declared ranges before trusting
any figure for it.

### The action-map blocker is the union table, and it is derivable

Targets 1 and 2 are not a framing problem. `decode_action_serialized_map`
already walks the three declared lists correctly; it fails closed on
`unsupported-union=0xNNNN` because `action_map_layouts.json` holds 277 reviewed
rows and the corpus uses far more unions than that. Each reviewed row was read
out of the native dispatcher one at a time, which is why the table is small.

The table does not have to be recovered that way. Two facts hold across all 277
reviewed rows, on three families whose tags run to 1341, 1101 and 216:

- a union's compact tag is its **case-insensitive ordinal rank on the wrapped
  type's full name** among the `ForMemoryPack` wrappers of its family. The
  wrapper name flattens `.`, `<`, `,` and `>` to `_`, so the key must read them
  back (`_` as `.`, a generic's closing `_` as `>`). Ranking the flattened name
  directly -- the earlier rule -- reproduces all 277 reviewed rows yet
  mis-tags `IFixAction.Data`..`IFixAction3.Data` in AbilityActionData and six
  `GameConditionClientOnce<...>` instantiations, because `.` and `,` sort below
  digits and `>` where `_` does not. *A rule that reproduces every reviewed row
  can still be wrong on rows no reviewed family contains;*
- a wrapper's members are its `set____name__` setters in **declaration order**,
  base chain first and root first, each typed by that setter's parameter.

Both are read straight out of the build's own managed image, so
`scripts/game_data/levelscript_union_layouts.py` derives the whole table --
1342 ActionBase, 1106 GetterBase, 235 ActionHeader -- from `tools/DummyDll`.
It recomputes every reviewed row first and returns nothing if one disagrees,
so the derivation is a cross-check rather than a guess. Comparison is on wire
form, because the reviewed rows are not consistent about whether an enum inside
a generic keeps its name or is written `Param<int>`; both spell the same four
bytes, and the divergence is reported instead of failing the run.

Keep the two evidence tiers apart. A reviewed row's boundary is `exact`: its
`nativeIdentity` was read from the dispatcher. A derived row's is `direct`: an
observed declaration in the build's managed image, with nothing in the
derivation reading the dispatcher that assigns the tag.

**The dispatcher can be read whole, not one row at a time.** Each family's
`<Base>ForMemoryPackFormatter.Deserialize` guards a jump table with `cmp`/`ja`,
whose bound equals the derived family size; each entry reaches (through at most
one `e9` thunk) a body whose first `mov rdx,[rip+disp32]` loads the wrapper's
type-usage cell. Resolving every cell names every tag natively: all 2,683
LevelScript entries (ActionBase, PureGetter, ActionHeader), plus
AbilityActionData, GameCondition and BaseComponentData, agree with the
corrected derived table and with every reviewed row, with no shared targets.
That sweep is what exposed the rank-rule error. It is maintained as
`memorypack.union_dispatch`, which accepts a table only when its entries map
one-for-one onto the family's derived wrappers with no shared targets; smaller
families compile to compare chains rather than a jump table and are refused.
Per-row getter contracts (`entityptr_getter`, `spawnerptr_getter`) now record
tags, member counts and `GetResult` bodies as regenerated data keyed by managed
type, and tie each authored reading to the body hash it was reviewed against:
`--regenerate` refuses a row whose body changed. Between the recorded and the
current build every such tag moved, one getter gained a member, and two
recorded same-tag ambiguities split into distinct native tags. Tag identity read this way is native evidence, but a
derived row's nested struct and enum declarations stay `direct` until their
own codecs are proved.

**Never write a union tag as a literal.** A tag is a rank, so a client update
renumbers every type after an insertion; the ActionBase, PureGetter and
ActionHeader families all shifted between the recorded builds and the current
one. The Story record-hint lane had accumulated literals from several builds
and silently matched nothing (published missions carried no Split, IfElse,
Switch, Branch or While edges), while some stale pairs landed on unrelated
current actions of equal member count and were decoded as the wrong action.
LevelScript code now names the type and resolves it through
`levelscript_union_tags`, regenerated from the native switches. A literal was
converted only where the code itself named its type and the current member
count agreed; literals with no recorded name, or whose type gained members,
were left inert rather than guessed. The same applies to contracts: record
tags as regenerated data keyed by type name, never as a key the next build
reuses for another type.

The EntityPtr output-alias, property-initialization and script-slot contracts
remain on the recorded build. Their readings come from method bodies that the
current build restructured (a single recorded 2,080-byte base `Process` is now
a chain of smaller methods), so they need a fresh trace through the new call
graph; equal body sizes elsewhere are not a substitute for that review.

The derivation also closes the types those layouts refer to: 42 structs and 94
enums, reached by running the reference set to a fixed point. Both are checked
against the reviewed `primitiveEvidence` -- its `stringKeyStructs` must derive
to exactly one string member, its `int32Enums` to int32 -- so the declaration
walk is held to what the native side already established.

### Two facts a member list does not state

An enum's width is one. Most are int32, but the referenced set contains three
`uint8` enums and one `int16`, and the reviewed codec already special-cases the
byte-backed pair by hand. Defaulting to int32 would mis-size those silently, so
the width is read from each enum's own `value__` field.

Wire framing is the other, and it is the subtler one. MemoryPack frames a value
that holds any reference as an object -- a null marker or a member count, then
the members -- and writes a struct holding no reference as raw bytes with no
marker and no count. The reviewed contract encodes both by hand without naming
the rule: `Param<EventArgsPtr>` reads a header then a string, `Param<LsmPtr>`
reads a bare uint64.

What decides it is the *real* type's complete field list, not its serialized
members. `EntityPtr` and `AirWallPtr` declare the same three unmanaged members,
yet only `EntityPtr` is object-framed -- because it also carries a generated
`ObjectPtr<Entity>` backing field that never appears in the wrapper. Reading
the real type settles every reviewed framing, and the derivation records the
answer per struct as `containsReferences`.

A raw struct's bytes are its memory image, so its members sit where the *real*
field order and natural alignment put them -- not in serialized order. Every
one of these types is `SequentialLayout` with no `ClassLayout` row, so the
offsets follow. `AirWallPtr` is the case that makes it visible: it serializes
as logicId, slotId, useSlotId, but its memory is useSlotId, seven bytes of
padding, logicId, slotId, for twenty-four bytes.

That derivation also explains something the reviewed contract left anonymous.
`decode_levelscript_ptr_param` reads `scriptId` and then eight bytes it calls
`reserved` and requires to be zero. Those eight are `LevelScriptPtr`'s
generated `levelId` backing field plus its padding. Padding being zero is
therefore a real integrity check, and the derived reader applies it: non-zero
padding means the size or the offsets are wrong, and it fails rather than
sliding.

A struct whose layout cannot be established -- non-sequential, or holding a
field of unknown size -- carries no `rawLayout`, and the codec refuses it as
`unresolved-unmanaged-struct-layout`. Member order never stands in for memory
order.

### Framing is decided by position, not by the type alone

The reference test above is necessary but not sufficient. `LevelScriptShape`
is a struct holding only `Vector3`s, a float and an int32 -- as unmanaged as
`LsmPtr` -- yet the reviewed shape decoder reads a member-count header for
every `List<LevelScriptShape>` element, while the reviewed `Param<LsmPtr>`
decoder reads a bare uint64.

Both are right, and the rule is which formatter does the writing:

- a **member** of an object -- root member, struct member, union subtype
  member, `Param<T>` value -- is written by the enclosing type's generated
  formatter, which puts an unmanaged member out as raw memory;
- a **`List<T>` or dictionary element** goes through `T`'s own formatter, which
  writes the object header;
- a **`T[]` element** does not: an array of unmanaged `T` takes MemoryPack's
  unmanaged-array path, a count then the elements raw. `List<T>` and `T[]` are
  therefore not interchangeable;
- a type with **no MemoryPack wrapper** has no generated object formatter at
  all, so it is raw everywhere, elements included. `StringPathHash` is one bare
  int64.

Getting any of these backwards desynchronises the cursor by a byte or two,
which surfaces as a plausible count far downstream rather than as an error
where the mistake happened.

Two further discriminators come off the type flags:

- a **union base is abstract**. `BlackboardInt` has subtypes yet is concrete,
  and is written as itself with no tag; every genuine union base in this corpus
  carries the abstract flag. Treating a concrete base as a union costs two
  bytes per value.
- **static and literal fields are excluded** from a layout. They occupy no
  space in an instance, and counting them both inflates a struct's size and
  makes a type holding a static reference look reference-bearing --
  `GameplayTag` declares a `string[]` constant and is otherwise a bare int32.

Two more shapes follow from the same "read the memory image" principle:

- `Nullable<T>` for an unmanaged T is .NET's `Nullable<T>` layout -- a
  `hasValue` flag, padding to T's alignment, then the value. A `float?` is
  eight bytes, not one plus four, and not one when absent.
- a nullable count is `ff ff ff ff`. The generic null-object marker is a single
  `0xff`, so a null list or dictionary must be recognised *before* that marker
  is consulted or exactly one byte goes missing. This was the single change
  that took whole-file decoding from nothing to most of the family.

### The root is declared too, and that closes the file

`LevelScriptData` is a twenty-seven member MemoryPack type whose wrapper sits
beside the union wrappers. Deriving it closes whole files rather than parts of
them, and two independently recovered framings corroborate the member order:
the prefix framing proved member zero is `actionMap`, and the terminal framing
proved the file ends with `scriptId`, `startShapeList`, `startType`, `taskMap`,
`triggerVolumes` -- exactly the head and tail of the declared list.

Deriving the root pulls in the rest of the graph. Closing the declaration set
and deriving a family for every union base it discovers, run to a fixed point,
yields 104 structs, 116 enums and 13 union families. Two of those families were
already reviewed and reproduce exactly: `LevelScriptTriggerVolumeData` tag 1 is
the Leader subtype with the reviewed eight fields in the reviewed order, and
all 7 `conditionLayouts` rows reproduce, so the cross-check now gates on 284
reviewed rows rather than 277.

### Where the action-map lane now stands

`action_map.py` takes the derived table through an explicit `declarations`
argument. Passing nothing is byte-identical to the reviewed contract alone,
which is what `levelscript_template_binary` and `memorypack/interactive` keep
publishing at; passing it admits the `direct` tier and the caller owns saying
so. `frame_levelscript_declared_action_map` is the framing built on it, and
`jsondata_schema_coverage --declarations` measures with it.

`frame_levelscript_declared_root` is the whole-file framing built on the root
declaration. It refuses any file whose cursor does not land on physical EOF, so
a partial read is never reported as whole.

The framing generalises to any MemoryPack root with a wrapper, so it is not a
LevelScript result. `ROOT_TYPES` seeds the roots; everything else -- the
structs, the enums, and a family for every abstract union base -- is found by
closing the reference set to a fixed point.

Current position, measured by `jsondata_schema_coverage --declarations`:

Every JsonData family is registered in the coverage sweep, including the
plain-text ones, so that report is the whole answer for the lane rather than
something a reader corrects by hand. **All twenty-four families are at 100%:
826 MB across 95,243 files, every byte named.** LevelScriptData was the last
one open and now frames 5,030 of 5,030.

Read that as what it is. Every payload in this lane is consumed to EOF by a
reader that refuses anything it cannot place, and every byte sits under a
declared field name. It does not say the *meaning* of each field is
established: a named `int32` whose consumer is unknown is still named and
still unexplained, and the runtime-consumer question belongs to the lane files
rather than here.

**LevelScriptData's open set fell from 56 files to 24, and one form did it.**
Every param-tail the sweep rejected was the *same* triple -- `idRef`,
`paramSource` and `pathSize` all `-1`. The getter-reference rule required
`0 <= idRef`, but `-1` is exactly how the default tail spells an absent id, so
the form is a getter reference with no id rather than a new shape. Accepting it
frames 32 more files, and the reason that is a reading rather than a guess is
that `frame_levelscript_declared_root` refuses any file whose cursor does not
land on physical EOF: a misalignment onto a run of `0xFF` does not end 32
independent files on their last byte. This replaces the earlier recorded
boundary, which had pinned the triple as rejected on a conservative argument
rather than a measurement.

All four shapes are now closed and the family is complete:

| former first failure | files | what it was |
| --- | --- | --- |
| `manualValue:unsupported-declared-member-count=7,expected=9` | 15 | a wrapper property type read as a field type |
| `modules[N].value.backIndex` / `.defaultHide` | 7 | unmanaged `KeyValuePair` layout padding |
| `alternativeCameraPoses:unsupported-PosRot-count` | 2 | a recorded "unreviewed element layout" boundary |

**The member-count group is closed.** All fifteen files were one authored
action in one script family, and the nested value is now read from the bytes
by `codecs/levelscript/send_lua_event.py`. The declaration could never have
stated it: `manualValue` is not a field of the action or of its
`ForMemoryPack` wrapper but the wrapper's `set___manualValue__` property,
whose parameter type is the action itself, so the derivation recorded a
self-reference and the reader expected the wrapper's nine members where the
wire holds the instance's seven. Reading the wrapper's serialize body turned
out to be unnecessary -- the payload says it:

```text
memberCount 7 | int32 | string | byte | int32 | byte | Param<string> | string
```

Two members are named by more than position. `_eventName` is the only
`Param<string>` the class declares and holds a Lua event name; `_param1` is
declared `Param<object>`, which MemoryPack cannot serialize generically, and
the bytes hold JSON of the form `{"paramSource":200,"path":"RoomID"}` -- a
param descriptor written as text. The two booleans and the second `int32` keep
neutral keys, because `NodeBase` and `ActionBase` declare more candidate bools
than the wire carries and nothing says which were dropped.

The evidence is whole-file framing: the layout closes all fifteen at physical
EOF, taking the family from 5,006 to **5,021 of 5,030** and 98.0% to 99.7%.
`SendLuaEvent2` would write eight members, but **no file contains one**, so
that count is derived from the declaration and checked rather than measured,
and an unexpected count fails closed.

**An unmanaged `Dictionary<K,V>` pair carries .NET layout padding, and the
seven `modules` files were four bytes adrift per entry.** `RunePuzzleData`'s
`anchorPointToIndexMap` is a `Dictionary<ulong,int>`, and the wire writes each
entry in **sixteen** bytes, not twelve: `KeyValuePair<ulong,int>` is an
unmanaged struct written as raw memory, so the four-byte value is followed by
four bytes of padding that satisfy the eight-byte key's alignment. Reading the
two back to back drifted four bytes per entry, and the next field then read a
count out of the drifted cursor -- which is why the failure looked like
`backIndex:unsupported-count=-354705288` rather than like a dictionary
problem.

Two things make this a rule rather than a patch. It is the same shape
`SerializeFieldDictionary` already cost four bytes per value for, so the
padding belongs to the unmanaged pair and not to one dictionary. And the
padding must be zero, which keeps the reading self-checking: a wrong layout
refuses instead of producing plausible values. The reader computes the pair
layout from the two widths and leaves a managed side alone, because only an
unmanaged pair is a raw struct.

**The rule has exactly two sites, and both are handled.** Enumerating every
declared `Dictionary<K,V>` whose key and value are both unmanaged *and* of
different width -- the only shape that can carry this padding -- returns two
across the whole declaration set: `Dictionary<ulong,int>` in
`LevelScriptModuleData` and `Dictionary<ulong,uint>` in
`NavMeshStateContainer`. Every other declared map has a managed side, or two
sides of equal width, and needs nothing. So this is a closed question rather
than an open sweep.

The second site was latent. `navmesh_binary`'s `Dictionary<ulong,uint>` has the
same shape and read its pair back to back. It never failed because both maps
that use it -- `surfTileIDToSceneStateMask` and `surfTileIDToSceneStateSet` --
are **empty in all twelve files**, so no entry has ever been read. Its sibling
maps corroborate the rule from the other side: the ones whose value is already
eight-aligned are populated, need no padding, and do decode. The reader now
applies the padding by rule and requires it to be zero, so a build that
populates those maps fails loudly instead of returning quietly shifted values.
The path stays unexercised, and the test that pins it says so.

*A discarded reading, recorded so it is not retried.* The derived row lists
`RunePuzzleData`'s members in the wrapper's setter order, which is
alphabetical after the two base fields, while the type declares them
`delayToFinish, defaultHide, runeColumnList, ...`. Reordering to the
declaration order looked like the obvious fix and is wrong: it moved the
failure without closing a single file. The setter order is the wire order; the
padding was the whole defect.

**`List<PosRot>` closed the last two files, and confirmed the setter-order
rule from the other side.** The codec refused any non-empty
`Param<List<PosRot>>` as an unreviewed element layout. The elements are
PosRot's own two-member objects -- a header byte then two `Vector3`s, so
twenty-five bytes each, because `List<T>` writes every element through T's
formatter rather than as raw memory. **The two vectors are written
`eulerAngles` first**, against the declaration's `position, eulerAngles`:
`Beyond_PosRotForMemoryPack` sets `eulerAngles` then `position`, and the
payload agrees, giving a map02 world position and a plausible yaw/pitch/roll
where the declared order gives eulers past 1300 degrees. So the same rule that
made reordering `RunePuzzleData` wrong makes reversing `PosRot` right: the
generated formatter's member order is the wire order, and the declaration's is
not.

**LevelScriptData now frames 5,030 of 5,030.** Every JsonData family is at
100%.

**NavMesh is closed, and what it was is worth keeping.** All twelve files
decode to EOF with every field named, at the reviewed tier as well as the
derived one. The four that used to be reported unframed are the four whose
`surfTileIDToSceneStateBucketsMask` is non-empty, and the record there is
written with **no MemoryPack member-count byte** -- eight raw `ulong` buckets
-- while the structurally identical value inside
`surfTileIDToSceneStateBucketsSet` *is* written behind one. The derived
whole-root framing assumes the count byte, so it read the first bucket's low
byte as a member count and refused. That is the wrapped-versus-unwrapped
distinction the reviewed reader already draws, not an unread nested
dictionary, and the family is now measured by that reader.

**An unregistered family is the failure this report must not have.** LipSync
is 702 MB of the lane's 826, and while it was absent from the family registry
the sweep neither measured it nor reported it open -- it left it out and
computed the lane share over the 124 MB that remained, which reads as a figure
about the whole lane. It has a reviewed reader that closes all 74,336 files at
EOF; registering it restores the lane total. A test now asserts that every
directory under the Json root has a family, so an absent one fails instead of
quietly shrinking the denominator.

The rest -- MissionRuntimeAsset, UILevelMapLoadConfig, MapConfig, LevelConfig,
LevelScriptTemplateData, CharInteractPerformCfgs, GPUISystemConfig and the
small config families -- are at 100%.

### EOF closure is necessary, not sufficient, and here is the proof

A reader that consumes its payload exactly to EOF has shown that its *total* is
right. It has not shown that its *fields* are. The two come apart whenever a
mis-reading has the same width as the truth, and this lane has a confirmed case:

**`spawner_binary.py` reads `preWarnEffectFixedRotation` as four consecutive
`f32` axes. It is `Optional<Vector3>`** -- a `bool hasValue`, three bytes of ABI
padding, then the `Vector3`. Sixteen bytes either way, so the reader consumes
correctly and never fails, and the wrong value is published to the Audio page
through `audio/semantics/entity_contexts.py` and `event_summary.py`.

Measured across all 608 SpawnerConfig files: 17 distinct tuples, 1,452 all-zero
rows (`hasValue == false`), and **every one of the 45 non-zero rows begins
`1.401298464324817e-45`** -- float bits `0x00000001`, the `hasValue` byte read as
a float. The remaining three components are `(0, yaw, 0)`, plain Euler-Y
rotations of 90, 80, 78, 110 degrees. Boundary: `exact`.

Two things follow. The fix is to apply the `Optional<T>` framing this lane
already records for other families -- `levelscript_union_layouts.py` and the
nullable-padding rule above both have it; spawner simply never used it. And when
a framing conclusion rests on EOF closure, say so and look for a second
signal: a boundary landing on a known marker, a value distribution that makes
sense, a field whose domain is closed. Closure alone cannot distinguish a right
reading from a same-width wrong one.

### Check the hand-written formatters first

Every framing bug this lane has hit has been the same class: a type the build
gives a **hand-written `MemoryPackFormatter<T>`** instead of a generated
`<T>ForMemoryPack` wrapper. Its wire form comes from the formatter, so its
field list need not describe it. `SerializeFieldDictionary` cost four bytes
per value; `AnimationCurve` cost a whole reordering.

Enumerate them rather than discovering them one desync at a time: find every
type extending `MemoryPackFormatter<T>` whose own name does not end
`ForMemoryPackFormatter`, and read off `T`. The non-stdlib answers on this
build are `AnimationCurve`, `AudioId`, `BezierKnot`, `Gradient`, `RectOffset`,
`SendLuaEvent1`, `SendLuaEvent2`, `StringPathHash`, `string`, and the
`SerializeFieldDictionary` / `SerializeReferenceDictionary` family;
`FORMATTER_BACKED_TYPES` records them.

Only two are settled. `StringPathHash`'s formatter agrees with its single
int64 field, corroborated by SpawnerConfig and LevelConfig closing every file.
`AnimationCurve`'s disagrees. The rest are still read from their field lists
on the strength of nothing, so that list is the first place to look when a
family stalls -- `BezierKnot` in particular sits under LevelData's spline
knots.

### The keyframe that was not a struct

One shape held most of the lane, and it resolved. `AnimationCurve` is served by
a hand-written `MemoryPack.AnimationCurveFormatter`, and that formatter carries
its own `SerializeKeyFrame` / `DeserializeKeyFrame`. So a keyframe is not the
declared `FKeyframe` struct: the wire writes **seven of its eight fields,
dropping Unity's legacy `tangentMode`, for a 28-byte stride with no
per-element header**.

That single correction took SkillData from 13.4% to 92.0% and BuffData from
83.0% to 99.1%.

Two independent measurements establish it. Sweeping the element width gives a
*single sharp peak* at 28 -- SkillData and BuffData together go from 3,695
closed files to 5,494, with every other width from 12 to 44 flat at 3,695.
Field identity comes from the values themselves across 16,827 keyframes: slot 4
is a small integer in every one (0, 1, 2 -- a `WeightedMode`), slots 5 and 6
carry Unity's default 0.3333 weights, and `time` in slot 0 increases
monotonically across 96.8% of multi-key curves.

The method is the transferable part. Corpus-fitting *layouts* had stalled --
four consecutive hypotheses scored at or below doing nothing. What broke it was
asking the build which types have a hand-written formatter, then reading that
formatter's method list: `SerializeKeyFrame` existing at all is the whole
finding, because it says the element is custom-serialized and its declared
field list cannot be trusted. Resolve the type, list its methods, and only then
sweep the one number the formatter leaves free.

Worth not re-deriving:

- blame the innermost live union tag and a scatter of member-level errors
  becomes a few names -- here four of 416 `AbilityActionData` subtypes, all
  carrying a curve.
- injecting bytes after each member in turn localises a deficit to one member.
- checking that the next element of a union array starts with a valid tag
  marker proves multi-element arrays self-consistent.
- MemoryPack version tolerance was retested with every framing fix in place and
  still changes nothing. A short member count is a desync symptom, never a
  permitted encoding. Settled.

Register the *strongest* reader per family, not the newest. AnimationConfig,
CharInteractPerformCfgs and the NPC montages all have reviewed readers that
close every file at EOF; measuring them by the derived whole-root path instead
reported AnimationConfig at 0.1% and NPC at 88%, understating work that was
already exact. A family's figure is only as honest as the reader behind it.

One directory may hold several roots -- `Interactive/` holds three, one per
subdirectory -- so a family may register more than one. Trying each in turn is
safe because a root framing refuses any file it does not close at EOF.

Unity types are a standing hazard here. `Color` resolves by leaf name to
`System.Drawing.Color` unless the Unity value types are declared outright, and
`AnimationCurve` cannot be read from its own declaration at all -- its only
instance field is an engine pointer. MemoryPack serializes it through a
Beyond-side `FAnimationCurve`, so it needs an explicit alias rather than a
resolution rule.

`AnimationCurve` is also the one type whose **serialized order the wire
contradicts**. `FAnimationCurve` reads `keys, postWrapMode, preWrapMode` in
both setter order and real field order, but a curve body reads 8, 8, 3 before
its float data, and 8 is `WrapMode.ClampForever` -- the two wrap modes precede
the key array. Taking the declared order produced a self-consistent but wrong
parse, turning a three-key curve into eight keys and desynchronising the file
far downstream, which is worse than failing.

The corrected order is recorded in `SERIALIZED_ORDER_OVERRIDES`, and it rests
on **corpus closure, not declaration**: it raised whole-file closure on
SkillData from 826 to 964 files and BuffData from 2,659 to 2,729 with no family
regressing. That is the same sequential-closure corroboration the reviewed
layout contract cites for its own rows, and it is weaker than a declaration.
Anything else added there needs the same measurement, stated. A type whose
order is merely suspected belongs nowhere near that table -- withhold it
instead and let its consumers fail closed.

LevelScriptTemplateData's opaque-middle files -- the trap this document used to
flag, complete looking because the framing reached EOF without locating what it
skipped -- are genuinely closed now.

A family that registers no framer at a tier is reported as *not measured*
there, not as zero. Several of these have reviewed readers outside the coverage
registry, and scoring them zero would understate that work.

Keep the reviewed-tier report beside the declared one. The pair is what makes
the derived tier's contribution visible, and the `exact` figure is still what a
consumer publishing at that boundary may quote.

The 149 files that do not close are a thin tail with no class above sixty-four:
a `teleportSlot0` member, an NPC behaviour dictionary, a `manualValue` whose
member count disagrees, and the `handle` Param tail. `CharPerformHandleBase`
has no wrapper of its own and is the one remaining piece with real structure
behind it.

## What each corpus gate proves

One paragraph per maintained gate: what it reauthenticates, what it writes, and
what it explicitly leaves unresolved. The commands themselves are in
[`../../scripts/README.md`](../../scripts/README.md); this is the boundary each
one establishes.

`streaming.corpus` reauthenticates block-15 rows from that ledger and writes
`reports/animestudio/streaming_root_subgraphs_latest.json` plus `.md`; pass the
exact `inputSetSha256` from the current outer summary. The gate covers the
anonymous field-2 vector, immediate table/vtable framing, and terminal row
field-5 scalar32 vectors through EOF, as well as the field3/4/5 and field6/7
subgraphs. It also verifies the field-2 row object's four-byte prefix plus
slot-to-next-boundary partition. Before publishing fields 0--5 as anonymous
scalar32/scalar32/scalar32/int32[2]/float32[6]/scalar32[], it revalidates the
selected GameAssembly, metadata, UnityPlayer, and bounded accessor/consumer
bodies. The field-5 consumer reloads the retained row pointer from a 72-byte
runtime record, iterates the count-prefixed vector with four-byte loads, and
uses each value as a hash-table key. The report also gates the current
numeric/Global filename-token relations. The selected family-level native read
path closes payload base, requested length, actual-count equality, and root
calculation. The concrete runtime path is unavailable, FlatBuffer accessors
receive no outer length, and no final cursor is exposed, so the carrier is not
joined to one authenticated logical file. Key namespace and signedness, field
names, and semantics remain unresolved.
`streaming.marker17_corpus` reuses the source-bound marker17 directory from that
report, reauthenticates every listed physical range and refines the native-gated
tag5 counted arrays and fixed tag1/4/6 profiles with `streaming.marker17`;
unknown keys remain explicitly opaque/unsupported. It writes
`reports/animestudio/streaming_marker17_bodies_latest.json` plus `.md`.
Partial `--max-files` probes require explicit output paths and are not eligible
as complete-corpus evidence. Record fields and runtime selection remain unknown.
`streaming.marker13_corpus` rereads the complete block-15 ledger through the
source-bound Streaming parser, joins marker13 references to independently
certified structural neighbours, and tests native-gated explicit-selector9 and
byte-proven absent-selector profiles. `streaming.pairs` binds paired file
identities, complete ordered vectors and exact serialized ordinals; absence is
never rewritten to a stored zero. Its inventory separates structure, read windows,
physical gaps and opaque remainder; a physical gap is not a serialized sizeof or native EOF.
Outputs are `reports/animestudio/streaming_marker13_latest.json`/`.md` and
`streaming_marker13_inventory_latest.jsonl.gz`; partial outputs must stay in
`tmp/` or `scratch/`. The summary authenticates the inventory's content/hash.
`streaming.marker2_directory` owns the complete nested reference/occupancy
replay. `streaming.marker2_corpus` gates the separate selector6 finite-gap
parser against the same source-bound ledger and ordered pairs; it publishes
`streaming_marker2_latest.json`/`.md` and
`streaming_marker2_inventory_latest.jsonl.gz` under `reports/animestudio/`.
Its four-byte native window is separate from the physical gap and opaque
complement. Unknown representations and multi-target clusters remain explicit;
partial probes cannot replace complete reports. Both ends of a sweep check
the live BLC path set as well as fingerprint contents and executing sources.
`memorypack.skill_corpus` owns the SkillData current-VFS gate; `skill` owns
anonymous prefix/candidate framing and `skill_terminal` enumerates each terminal
branch with complete record ranges. The gate joins current decrypted stream
bytes to every selected outer-ledger identity and checks overlay, raw chunks,
CLI and parser provenance at both ends. Historical census rebinding is rejected,
with one narrow, opt-in exception: `--allow-exporter-rebind` carries a cursor
verification across input sets only when `AnimeStudio.CLI` is the sole moved
build fingerprint and the identity set, every selected file's logical hash and
length, and the BLC path set are identical. The rebuilt exporter otherwise
strands the verified basis the context audit and the capture preflight both
require, because only a capture can re-verify it and the preflight blocks the
capture. The output records `cursorVerification.rebinding`; a fresh capture
under the current input set supersedes it. A timeline continuation the reader
stopped short of field 42 is a valid unverified state and promotes nothing.
Unique, ambiguous, unsupported and failed rows remain explicit; no candidate
establishes whole-schema ownership. Each prefix/candidate binds the input-set
hash, logical identity/hash, `[start, hardLimit)`, grammar parser cursor, byte
ranges and opaque ranges. The aggregate keeps independently closed records,
structural-prefix evidence, ambiguity, unsupported/failed rows and opaque-byte
counts distinct; candidate EOF cursors do not certify the active formatter.
Partial `--max-files` outputs must stay in `tmp/` or `scratch/`.
`memorypack.skill_cursor_receipt` validates the current corpus/native-context
binding and joins a bounded cursor receipt to current SkillData identities,
hashes, hard limits, and terminal candidates. It can promote only the observed
terminal range, not the complete SkillData schema. Use its receipt mode from
the exact-build workflow in `tools/EndfieldCapture/README.md`; `--preflight`
prints the authenticated current input-set hash without launching the game.
`memorypack.skill_timeline_cursor` joins a complete current SkillData stream to
the source-bound corpus and exact-build native context, then replays child
action readers only when the selected native route, per-tag reader contract,
and hash-verified `memorypack.buff_actions.Reader` agree. It records candidate
byte ranges and precise unsupported/truncated stops; selected reader ends do
not prove runtime provider choice or close their parents. The command writes
`reports/animestudio/skilldata_timeline_cursor_latest.json` and `.md`; partial
probes belong in `tmp/` or `scratch/`.
`memorypack.npc_montage_corpus` authenticates the complete current
`Data/Json/NPC/MontageJson/MontageNew/*.json` family by joining each
outer-ledger identity to AnimeStudio `stream --verify-md5` output, then frames
supported records through EOF. It checks current chunks, CLI and parser
fingerprints at both ends and writes
`reports/animestudio/npc_montage_current_latest.json` and `.md`. Changing
coverage belongs in that report. The reader publishes named root/montage fields
only after a real cursor consumes the complete record; nested DynamicEntity
vector/value-type spans remain explicit unresolved ranges.
`memorypack.corpus_gate` owns shared outer-ledger, overlay, fingerprint and output
guards. `memorypack.buff_corpus` joins the full current BuffData stream and retains
every filename-string anchor and reader-accepted suffix candidate. Current
generated wrapper order names the first six fields, the supported field-6-to-14
middle, and the accepted field-15-to-29 suffix. A closed outer frame still keeps
internal icon/action bodies opaque. Its report partitions selected files into successful candidate framing, failed
reader execution and unsupported shapes; uniqueness is only within that reader.
Each accepted BuffData suffix also records a hard-bounded prefix-reader stop and
remaining gap, with prefix support counted separately from suffix acceptance.
The report binds its parser cursor and closed action ranges to current input-set
and logical-file identities, and keeps exact action closures, structural
prefixes, opaque bytes, rejected anchors and unsupported results separate.
`memorypack.buff_actions` owns the independent event-prefix grammar;
its per-candidate scalar/record spans now carry the current wrapper field names,
while explicit opaque remainders have a separate
success/failed/unsupported/ambiguous census. Malformed prefixes fail the corpus
gate even if the suffix candidate succeeds; unknown unions are not aliased.
`currentRootContinuation` consumes selected root members 2-6 only after a
supported first collection, beginning at `currentEventPrefix.consumedEnd`.
Its independent status and ranges retain later physical bytes as opaque;
malformed continuation data also fails publication. `currentNamedMiddle` then
advances empty damage/heal modifier-list forms and the generated four-field
positive `globalModifier` item through field 13, then bounds the 19-member
`iconConfig` range at the accepted `id` marker. Only that contiguous prefix plus
the sequential suffix earns `named_exact_frame`; a positive unsupported modifier list or an
earlier unsupported union keeps the file partial.
`memorypack.buff_1b_corpus` rebuilds that full current census, selects only
exact-closed tag `0x1B` records from root continuation, and re-streams matching
files to verify their literal tag byte against ledger MD5 and logical SHA-256.
It joins the tag to the exact-build selected `BlowOffAction_Data` reader order
and writes `reports/animestudio/buff_1b_current_latest.{json,md}`. Provider
selection, action semantics and whole-BuffData EOF remain unresolved.
`memorypack.lipsync_corpus` joins the full LipSync JsonData stream to current
ledger identities and runs the strict 15-member reader through EOF, checking
logical MD5 and source/tool/parser pins at both ends. It reads JSONL one row at a
time and writes `reports/animestudio/lipsync_current_latest.json` plus `.md`:


`python -m scripts.game_data.il2cpp.context_audit` emits an exact-build native
generic-instantiation audit as JSON on stdout. `il2cpp.context` owns bounded
pointer-table/record/vector decoding and reciprocal method-parameter identity;
the audit checks selected native inputs and consumer pins, scans all registered
instances, validates metadata image ownership and unique module-name joins, and
rechecks the saved SkillData corpus's live input/tool/parser/chunk pins through
`memorypack.skill_corpus.verify_current_report_inputs`. It does not
re-stream the full corpus or establish runtime formatter/cursor identity. Its
SkillData section re-reads one terminal sample and selected branches covering
every positive terminal-list count shape in the saved census. Each sample is
bound to its current logical identity/hash/hard limit and replayed against the
exact-build reader order and field types. It also checks the shifted candidate
against the registered GameplayTagList header and matching List<GameplayTag>
remaining-byte guard. These are conditional static-path checks; runtime
provider/cache selection and an executed cursor remain unobserved.
Its ActionGroupData section also replays current positive
`passiveEventActions` samples against registered AbilityActionMap,
SequenceActionData, and selected action readers. A child union advances only as
far as its independently pinned reader evidence supports: unverified tags stop
at their first byte, and the C9 member-eight path stops before its first generic
SequenceActionData call. The report separately keeps any three-call nested
SequenceActionData replay candidate-only: provider/cache selection remains
unobserved, so its ranges do not advance the authoritative parser cursor. The
following `timelineActions` count is only peeked; neither the parent
`ActionGroupData` nor whole SkillData is closed. See
`reports/animestudio/il2cpp_context_current_latest.*` for the current
identity-bound ranges and corpus classification.
