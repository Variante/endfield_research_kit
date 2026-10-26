# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and
level payloads: where each JsonData family's framing stands, how LevelScript,
SkillData and BuffData routes are promoted, and the IL2CPP chain that
identifies which formatter a payload resolves to -- static identity
throughout, never observed execution. Current denominators are in the
generated JsonData, SkillData and BuffData corpus reports; each reader,
validator and gate documents its own layout, evidence tier and non-proofs in
its module docstring, with per-build facts in `scripts/game_data/contracts/`.
Derived-plan EOF closure never substitutes for an independently named
whole-file schema.

## The JsonData registry gate

`python -m scripts.game_data.jsondata_corpus` joins each current JsonData
identity to its export file by path, length and logical MD5 and assigns one
terminal state (vocabulary in its docstring). The current gate retains named
schemas, bounded partials, framed, unclassified and unsupported identities.
Missing or mismatched native gates withhold the affected family's historical
decoder and receipt; a complete registry is not complete schema coverage.
Family gates own cursor, native and semantic claims. A type with a
registered `MemoryPackFormatter` (`SerializeFieldDictionary` and siblings) is
read from that formatter, never from its field list; see
[`codecs/levelscript/action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py).

Family receipt filenames are defaults, not freshness authority. The registry
can select an alternate complete Buff or Skill receipt through `--buff-report`
or `--skill-report`, but still checks its input set, source bytes and live
helper/native provenance. Admission failures identify the validator, failed
predicate, source identity and bounded expected/actual values. Buff's selected
root provenance follows its parser import closure, contributing dispatcher
declarations and transitive contract references. A contributing change requires
a fresh complete receipt; an unrelated contract change does not. Newly relevant
or conflicting dispatcher declarations still change or fail the dependency set.
The static parser closure follows repository imports across lane boundaries,
including IL2CPP helpers, per-module relative imports and package initializers.
Explicitly loaded external metadata/mapper helpers still need their owning
validator's source snapshots; this closure cannot discover dynamic loading.
Do not repair a provenance mismatch by editing receipt pins or repeating a
capture.

The compact SubGame reader admits only the independently authenticated
WorldChallenge variant and bounded child collections named by its current
contract. It binds the concrete union/root/Task adapters, current pooled text,
LangKey output and raw FunctionArea ID to the selected native build. Other
variants refuse; runtime provider selection and helper effects remain conditional.

The bounded native copy component proves source-byte preservation only in its
reviewed finite size/mode/alignment domain. Every caller still owns its exact
target, argument and storage joins; this component establishes no FMV name,
playback or whole-owner relationship.

The FadeIn/FadeOut parent routes independently bind their current union,
complete read/setter bodies and typed Param sources. Their Audio black-screen
enums use the separately gated byte representation; stored fields establish
no effective screen/audio state or runtime execution.

The standalone LevelScript family receipt binds the complete selected StringPool
page set to the same current VFS ledger and physical chunk snapshot as its
owners, passes that exact pool to both owning readers, and rechecks the page
set before publication and saved-receipt verification. Historical receipt
comparison also requires matching pool inputs; equal owner bytes alone do not
establish equal resolved text. Receipts without this binding are refused.

A rewritten outer VFS catalog invalidates its source fingerprint even when
the selected native build and Buff logical bytes still agree. Rerun the full
AnimeStudio VFS audit, compare the current logical identities and bytes, then
run the complete Buff family gate against the new audit. A previous JsonData
registry remains stale until its own complete gate succeeds. Current Buff
family admission and selected canonical Buff replay can retain independent
evidence without relabeling that older registry as current or weakening an
unrelated family's required primary receipt.

NativeImage and BodyIndex share immutable parsed indexes for the exact opened
image. Every native gate and claim still evaluates against its selected inputs;
sharing a parsed method/unwind table does not cache a validation result.

## JSON-schema and compact-table families

Each reader checks stored order, types and cross-index relations and fails
closed on drift; none proves runtime selection or consumption. Textual JSON
lives in the `scripts/game_data/schemas/` package (GameplayConfig compact and
`$type` tables, text tables, LevelMountPoint, NPC catalogs and PrefabInfo,
GoldCoin, UILevelMapLoadConfig, MissionRuntimeAsset, MapConfig). Binary
tables use `gameplay_compact_binary` (MissionArea, SubGame,
WorldEntityRegistry), `memorypack.tables` (DialogIdTable,
BambooRaftTaskTable), `interactive_binary`, the LevelConfig, NavMesh,
TeleportValidation, AetherEnergyLock and MatrixShockWave `*_binary` readers,
`atmospheric_npc_binary` and `gpu_ui_binary`/`gpu_ui_corpus`. Map marks
([`map_mark_relations.py`](../../scripts/game_data/map_mark_relations.py)):
a registry link needs an exact `markInstId` and equal position, a scene link
also a unique `LevelShortIdTable` scene, and it assigns only that marker.

## LevelData, Interactive, AbilitySystem and AnimationConfig

These families use maintained stored-schema readers. LevelData's sequential
43-field reader (`leveldata_binary.py`, `codecs/leveldata/`) shares value
codecs with LevelScript and placed NPC rows; its fallbacks are named
frames, never full schemas. Current SpawnerConfig owners close through EOF in
the selected corpus. CharInteractPerform admits the separately gated current
bounded sparse root described below.
Interactive templates (`memorypack/interactive.py`) take component
tags from the native `BaseComponentData` dispatcher; the 38-member
`Core_AbilitySystemForIntData` refuses positive nested domains rather than
inherit a schema from field names. AnimationConfig and NPC MontageNew resolve
path hashes only through an authenticated `StringPathHash` catalog; the
shader-publication proof is conditional on runtime actor and IFix selection.

The serialized AnimationConfigJson mask entry is distinct from the runtime
AnimationConfig type. Its generated wire order is pooled `layerName`, then
signed `StringPathHash`; the managed value places the hash before its string
reference, so managed size and wire extent must not be equated.
`animation_masks_native.py` authenticates this component's selected buffered
sources, owned stores, static registration, typed adapters and list paths
against the selected native pair and Unity input. The admitted list profiles
are null, empty and one entry; larger counts and growth remain refused.
Initialized contexts, canonical sharing and the actual provider/virtual
selection stay explicit conditions, even with the original key/adapter
registration proved. No closed method pointer is invented when only a
canonical reference-sharing entry is present.

Every supported mask count exposes only the first five stored fields, after
the current selected-native gate. Null or empty masks and an old fixed-size
empty-looking suffix do not admit the remaining Animation fields. ExtraData,
montages and Beyond.FAnimationCurve stay opaque until their own current source
composition is proved. The separate Unity AnimationCurve key profile has a
different managed element width and cannot supply this missing join. No whole
schema, montage/curve absence or playback claim follows from the prefix.
Raw, corpus, Data and coverage consumers pass the matching selected pool and
native context. Data and coverage bookend their pool, native and reader
inputs; counts omitted for an unread suffix mean unknown, never zero.

Current MontageNew inserts `decoEntities` before `dynamicEntities` and reads
clip/entity strings through the selected StringPool. Its direct async-clip
copies use the managed stored span, not the separately aligned native ABI
size. The reviewed
[`npc_montage_native.json`](../../scripts/game_data/contracts/npc_montage_native.json)
and matching validator join the owning root/body/clip source order, typed
stores, scalar/pool/raw-value reads, generated reference adapters and factories.
The maintained `memorypack.npc_montage` sparse reader admits only null or empty
Deco, Dynamic and transition-override lists, preserving those two states;
positive elements refuse at their actual count offset. Reference-list sharing
is conditional on a coherent initialized typed context and normal metadata,
allocator, constructor, Clear and pre-loop provider helpers. The empty path
does not consume an element or use the provider's result; this does not prove
live provider/cache/default selection or runtime playback.

Each lexical Montage operation validates fresh native semantics on enter and
exit and checks native, Unity, complete reader-source and selected StringPool
bookends before returning a result. A closed decoder cannot be reused, and a
late failure withholds its caller's receipt or decoded publication. The
standalone VFS census independently joins all selected pool pages to the same
authenticated source ledger as the streamed owners. Bounded physical-EOF
success does not admit positive lists or change whole-family coverage; the
canonical corpus gates own those denominators.

CharInteractPerform inserts the Boolean `replayLoopActions` between
`preStartActions` and `startActions`. Its current sparse reader binds all named
root transfers, typed registered adapters, reference/value returns, dictionaries
and the default entry under one selected native gate. It admits null or empty
literal collections, stored dictionaries and default-entry lists, plus one
GameplayTag element through its own current value dispatcher, member header,
Int32 read, getter and typed append. The `chars` list also admits at most one
current actor through its separately checked reference adapter and list loop.
The `loopActions` list additionally admits one current `AddMultiTagsActData`
through the freshly derived action union, eighteen-field reader and one-item
reference-list callback. Its inherited base interface returns the base holder;
the three derived setters use a separately proved coherent cached holder.
The nested `BodyTypeDef` serializes three fields in ten bytes while its native
value occupies thirty-two bytes; its fourth runtime field is not serialized.
The gate proves that hidden return, value adapter, conversion and full getter
independently. Other action tags, larger lists and positive special entries
remain refused; physical EOF is required for complete framing. Coherent selected
contexts, initialized
successful cache probes and normal helper/constructor/storage returns are
explicit conditions; live/default provider selection and gameplay execution
remain unproved.

CharInteractPerform actors have thirteen stored fields, keeping temporary-object
delayed destruction, its time and cloth-collider registration distinct. The
actor gate composes the current typed reader and every return store with nine
primitive reads, four direct-return pooled-string reads, wrapper creation and
the selected one-item reference-list callback. Strings resolve only through the
selected export pool; null and empty sentinels need no pool lookup. The
decoration ID is unsigned and the temporary path hash is signed. Pool-absent
UTF8, refill/error paths, allocation/storage effects and live provider selection
remain outside this conditional stored grammar. Embedded bounded jump tables
must be partitioned as data before checking the formatter graph; a linear
decoder's apparent instructions there do not establish a changed wire grammar.

The reviewed positive actor facts live in
[`char_interact_perform_actor_native.json`](../../scripts/game_data/contracts/char_interact_perform_actor_native.json).
Their matching validator authenticates the selected native inputs, field
identities, source/store instructions and complete owned windows and tables.
It returns no fields for missing or mismatched inputs, rechecks inputs after
validation, and keeps enclosing-owner admission false. This actor component
does not admit positive actors in the current sparse configuration reader.

Special-entry union readers use distinct new-reference and existing-byref
ReadPackable routes. Preserve the actual typed contexts and entry roles on
each route; a missing closed registration is not evidence for selecting the
canonical object instantiation. Complete child control and typed field stores
still do not establish collection/provider selection or the enclosing owner.
Folded physical entries can carry unrelated method aliases; resolve each
caller's own MethodInfo and reciprocal generic context instead of assigning
the entry whichever alias happens to be present.

Assign generated reader entry roles from the selected static flag and formal
byref parameters, including readers declared in nested formatter types. The
BodyTypeDef value path has its own hidden-output extent and wrapper copy;
its raw byte enum reader preserves the byte rather than normalizing a Boolean.
Inherited and concrete wrapper views can have separate typed holder fields.
Locate the field actually loaded by the selected program and preserve its
declaring type and inheritance chain; matching wrapper identities alone do not
establish that separate holders contain the same original object. The selected
concrete instance setter additionally needs its intervening helper's actual
register-preservation proof: ordinary ABI rules alone do not preserve volatile
temporaries. A closed call-free bitmap retry/return program can establish that
preservation and bound its writes, conditional on normal return and disjoint
object storage. This supports the initialized matching-holder path without
claiming cold cache conversion, helper termination or live formatter selection.

A successful Data publication does not establish complete schemas. Changed
placed NPC inheritance, positive NPC montage collections, animation-mask strings,
unadmitted CharInteractPerform collections and SubGame variants remain
independent migration boundaries. The admitted NPC PrefabInfo partition describes roster definitions;
it does not close placed proxy or montage payloads. Keep current refusals until
their native read/cursor joins pass; setter declarations alone name fields but
do not prove their wire representation.

The current placed-NPC gate keeps the flattened entity, NPC and proxy fields in
one native-derived plan. It includes `enableMaxPotentialOnCreate`,
`restaurantRole` and `forceEnableMorph`, pooled strings and the actual typed
setter widths. The selected initialized source proves every read-result
transfer and the final normal return. Inherited cache refreshes and the
compiler-inlined morph setter have their own checked paths; compatible cast,
metadata, allocator, collector and provider effects remain explicit conditions.
A declaration or successful candidate parse cannot replace those source joins.

`ReadValue<LangKey>` writes a sixteen-byte value through a hidden output pointer;
the reference-return clone cannot admit that call. Only the key is serialized;
the second reference is not exposed as stored text or assumed zero on reuse.
The placed override `AudioId` uses signed Int32 storage. The inherited
`belongLevelScriptId`, `dependencyGroupId` and `levelLogicId` instead retain
UInt64 bits as decimal strings. Arrays, GameplayTag lists and new UInt64 lists
have separate bounded source profiles. Larger counts or unsupported reused
collection paths refuse at the named field. The two unproved auxiliary lists
remain null-only. The opaque ability, battle, hit, proxy-info and runtime
children admit only the selected reference adapter's one-byte null path, which
writes a full null reference before any wrapper, getter or child callback;
positive children remain refused before consumption.

The shared NPC operation requires the matching StringPool and selected native
pair, re-proves native components at both lexical boundaries, and checks complete
reader and pool freshness. An inactive decoder cannot be reused. LevelData's
list and LevelScript's UInt32-key dictionary retain independent typed container
joins. Atmospheric tables use one sequential pooled-key dictionary cursor;
there are no marker anchors or guessed next-row boundaries. A child refusal
retains only known earlier entries as partial evidence. Whole-owner admission
still requires physical EOF and source, VFS, pool and native bookends. Map only
promotes a stored placement from a complete named owner, and neither that
placement nor a configured patrol id establishes live spawning or patrol use.

Check caller register origins at each selected read site over the complete
control-flow graph. A register reused after its last relevant read does not
invalidate that earlier origin; global unchanged-register tests over-refuse.

Owned native setter ranges can contain bounded relative jump tables. Partition
those bytes before instruction decoding, authenticate the index guard and every
target, and exclude incoming edges that bypass the guard. A linear decoder's
truncated instruction at a table boundary is not evidence of a changed opcode.

Treat setter storage as a separate join from reader order. Check the current
declared field, setter parameter and typed cache, then the actual store width
and return/frame flow. A checked initialized, matching-cache path does not
close metadata initialization or cache refresh. The compiler-inlined morph
setter needs its own selected control edges; a partitioned jump table alone
does not prove its field store. Base reference stores precede their collector
loop, whose storage must remain disjoint from the instance.

Open-generic List field offsets are placeholders. Use the concrete indexed-read
body to join serialized elements to accessible list values, without assigning
private field identities from declaration order. The selected UInt64 formatter
reads elements individually; a long list does not imply a large bulk-copy path.
Its positive and empty paths have separate control-flow joins. EnvTalk's typed
constructor sets its Boolean default true; positive pooled string and Int32
arrays use independently checked typed callbacks, allocation, copy and cursor
paths. An Atmospheric corpus census cannot restrict the domains
of other NPC consumers.
Likewise, a scalar GameplayTag transfer does not establish its collection-item
framing: the selected list formatter can use a generated wrapper instead of
the unmanaged fast path. The checked default collection path reads a one-member
wrapper before its Int32 value; a null wrapper becomes the zero GameplayTag,
not a nullable element. Its selected wrapper/interface transfers and list setup
remain conditional on the matching initialized contexts and provider.
Keep unproved positive children refused when migrating
the parent; successful corpus parsing cannot revive historical child decoders.

`NpcAiInstanceData` is a value type without its own deserialization methods.
Its generated reference wrapper embeds the value, and its conversion interface
returns the complete embedded value through a hidden output pointer. The
concrete generic adapter pairs the original value type with that wrapper;
its selected context distinguishes the original-type conversion interface
from the wrapper-type formatter and constructor. Current native component
checks cover the nonconsuming null peek, conditional null-header consumption,
parent reference dispatch, null zeroing and complete conversion/output copies.
These static identities and transfers do not establish a live provider result,
wrapper registration execution, allocator effects or the dictionary owner.
Keep those joins separate from successful candidate decoding.
The current AI child is a complete managed forty-eight-byte value, not six
independent reference fields. Its read order is float, key, long, string,
enum and vector; hidden-output conversion copies the whole value. The reached
dictionary profile supports a fresh empty dictionary or one positive entry
with a nonnull string key and positive six-member value. Its storage call is
`set_Item`, so normal storage may replace an existing key rather than behaving
as `Add`. The null wrapper produces a default value rather than a nullable AI
value; that default path remains refused by this raw profile. Matching provider,
canonical reference sharing and normal storage effects remain conditional.

A static generic context may contain an opaque entry that a selected source
never reads. Explicitly selected relative slots may be proved independently,
retaining the complete owning range and reciprocal generic-parameter identity.
Unselected slots stay uninterpreted; this is not a complete-context claim.
The default complete-context gate must still refuse any unsupported entry.

Inherited wrapper members also do not prove common object identity. A derived
wrapper can keep its own real-instance reference separately from the base
wrapper's typed instance reference. Resolve a transfer through its declaring
wrapper and prove constructor/assignment forwarding before treating stores
through those distinct slots as fields of one reconstructed owner.
The current paired instance setters retain the receiver/value in R10/R9 across
the direct write barrier. Its leaf program preserves those registers; ordinary
Win64 caller assumptions alone would not prove that transfer. The separate
tracking bitmap and normally terminating atomic update remain conditions.

Regenerating a StringPool can move indexes for unchanged text. A changed
JsonData hash alone therefore does not establish an authored-field change.
Compare decoded fields using each export's own authenticated pool; never
carry an index from one export into another's pool.

The current LevelData root keeps its declared order, but its scene ID is a
signed pool index, proved by `serialization_roots_native.json`; missing pool
pages never select inline text. Brief values include the inserted risk list.
Their positive risk/property children remain bounded until independently
proved, and searched ownership results no longer cache a native success.
`leveldata_function_area_native.json` proves the current base additions:
`enableFactoryHide` and a nullable seven-field `factoryHideDesc`. Its five
Boolean sources, owner enum storage and typed building-type list source are
separate from positive list framing or live factory visibility.
`leveldata_airwalls_native.json` independently proves the air-wall radio,
polyline effect and mission-check ID pooled sources. The mission ID passes
through a typed generated setter whose unchanged reference store is checked;
collector barrier equivalence remains outside that proof. Data publication
binds the selected pool, complete reader dependencies and native source gates
before and after decoding or cache reuse. Exact EOF, bounded child stops and
refused inputs remain distinct in the current corpus report.
The shared child string helper accepts only signed pool indices; an unavailable
positive index refuses that child instead of selecting inline UTF-8. Enemy and
lock collections retain named stops until their pooled child codecs are migrated.
The Interactive dictionary uses its separately gated sparse pooled profile.
The current NPC Patrol lane is separately gated by
`leveldata_npc_patrol_native.json`. It proves the inserted patrol Boolean,
direct scalar and pooled-string transfers, point/action field order and typed
child unions before the sequential LevelData cursor consumes a positive list.
Canonical reference-list sharing remains conditional on the proved current
factory, typed contexts and normal helper returns; it does not prove live
generic inflation or default formatter selection. Positive blackboard pairs
remain refused. One lexical operation proves fresh semantics on entry, binds
the selected pool and logical export receipt, and rechecks native, reader,
pool and owner bytes on exit. A leaked decoder or failed exit cannot publish
a result. Null and empty headers retain their existing generic owner framing.
Stored signed AudioIds and action enum cases remain structural candidates;
their compiled Audio consumer and Event-request meaning are separate joins.
The older suffix partition cannot close unknown current children.

The Data page now exposes SpawnerConfig's one sequential owner cursor through
`frame_spawner_named`, with an earlier enemy-library or through-settings prefix
on refusal. It never uses a tail match to close an unknown prefix. Atmospheric
NPC rows retain the shared proxy codec's own named/framed status, and MapConfig
publishes its validated fields rather than only counts; duplicate JSON keys
fail closed. These views expose authored storage, not observed spawning,
action execution or condition results.

The indexed-string Spawner reader uses the six-member root, including
`preprocessList` after `enemyLibrary`, and the added `defaultDisable` Boolean
after `deadlineBeginDeltaTime` in both waves and groups. The apparent nested
enemy-library framing disagreement came from reading pool indices as inline
strings. Its strings, patrol strings and action strings now use the explicitly
selected export pool, with no missing-pool inline fallback. The reviewed
[`spawner_records_native.json`](../../scripts/game_data/contracts/spawner_records_native.json)
and its validator preserve the complete root read/setter order, typed source
contexts, pooled-string helper proof and Boolean byte/cursor proof. These are
static source facts; collection-provider selection and live pool contents remain
conditional. Positive preprocess lists and non-null born behaviors still stop.
The old searched-tail implementation is removed; only a sequential owner can
close the file, and the current JsonData corpus receipt owns family admission.
Data cache reuse binds the selected pool and reader inputs, rechecking them
after decoding. Story group domination refuses disabled or unknown-disable
groups rather than carrying the older group's behavior assumption forward.

## LevelScriptData owner cursor

`levelscript_binary.frame_levelscript_named` owns the shared reader order for
the JsonData registry and Data page. It preserves each reader's own status and
physical cursor, keeps earlier exact-lane refusals on bounded fallbacks, and
reports all rejected profiles with bounded source/hash diagnostics if none
applies. A suffix fallback remains partial even after a native-lane refusal.

One generated-order walk (`codecs/levelscript/sequential_owner.py`) reads
members 2..28 after an exact action-map boundary: null (`0xff`), the 20-byte
empty `ActionMapAssetRaw`, or a positive map whose three lists and
`ParamListForGraph` close (`current_action_sequence.py`, then the reviewed
`action_map_layouts.json` nodes). The current root adds
`interactiveActiveRiskEntityIdList` before `interactiveLocks`; its brief record
adds the same list after `dataPath`. The reviewed
[`serialization_roots_native.json`](../../scripts/game_data/contracts/serialization_roots_native.json)
and its validator prove both count checks, original reader/byref-wrapper
argument preservation, the wrapper holder and direct field stores, and the
identical typed UInt64-list usage/entry used for each existing world-reference
list. The root template path independently passes the pooled-string helper
proof. These bounded facts do not establish positive list framing, Brief
property/string children, default-provider selection or whole-owner admission.

`top_level_prefix` reads the new null/empty field and explicitly pooled template
path. The sparse `interactives` dictionary has a separate current native gate:
the generated element reads the inherited entity fields and its own fields in
order, with the inherited holder and derived cache proved coherent. Pooled
ParamGraph properties and bounded component entries use independently gated
children; nonnull Int32 lists and positive conditions remain refused. Exact
dictionary factory, typed K/V contexts, initialized provider/dispatcher paths,
constructors and stores are separate from observed live provider selection.
Reference source sharing is conditional on the stated selected paths and normal
helper effects. The reader validates fresh for each operation and forwards the
owner's selected native paths. Other unsupported positive children retain named
source/composition stops; older inline readers cannot admit current owners. A file is exact only when the
supported sequential owner and `triggerVolumes` reach physical EOF. The current
Data cache gates this root source contract before reading and rechecks source,
pool and native inputs after decoding or reuse.
GameCondition and module tags renumber per build and resolve by type name.
The unique-suffix and first-record lanes stay partial. Rank first stops by
whole files unlocked after every list and the owner tail close, not by raw
union counts, and rerank after each complete gate.
The previously isolated task-map queue closed for its historical ledger-matched
sources. Newly admitted earlier actions can expose additional task, module or
trigger-volume stops, so rerank these owner fields after each shared batch;
the old queue is not a family-wide closure claim.

Current node UIDs are StringPool references in the common envelope, as read
by `codecs/levelscript/node_strings.py`. The legacy ASCII UID scan is not a
current ActionMap boundary proof: zero hits beside a positive serialized list
count means unavailable topology, never an empty graph. Consumers need the
typed sequential nodes and their matching pool; an unproved nested string
child still blocks complete topology rather than supplying guessed boundaries.

The shared UID reader consumes the three declared lists sequentially and keeps
their exact node cursors. Getter common fields end after seven members, actions
after eight and headers after fourteen; header filter level is not its next
action ID. Copied record views must still agree with every serialized count
and cursor. Typed projections retain selected operands and explicit getter
references rather than re-reading the former inline-string offsets.

The EventArgsPtr and EntityPtr Param contracts authenticate their separate
pooled-key and three-field entity wire formats, typed parent transfers and
generated wrapper routes. Their formatter selection remains conditional on
the matching initialized generated route. Static registrations and shared
native entries do not establish a live provider default, action execution or
resolved entity. Unknown children still stop the complete record list.

Null List constants use independently proved closed-type components. Only the
null count is admitted; empty or positive collections still require their own
element/composition proof. A condition proved independently of the stored-route
batch owns its own gate; the other rows keep their existing requirements.
Typed route string fields use the same checked read-order and CLR alias rules
for the scalar, collection and condition contract schemas.

## LevelScript action-map unions

`ActionMapAssetRaw` is the three-list `ActionSerializedMap` (action, getter,
header) plus a one-member `ParamListForGraph`; empty, it closes at root byte
20 (the map alone at byte 15). Templates and Interactive files reuse the same
reader ([template reader](../../scripts/game_data/levelscript_template_binary.py)).
Elements are unions keyed by `(tag, memberCount)` in four separate dispatcher
domains (ActionBase, PureGetter, ActionHeader, nested GameCondition). Tags are
per-build family ranks: name types via `scripts.game_data.levelscript_union_tags`.
`python -m scripts.game_data.levelscript_union_layouts` derives every layout
from setter order at the `direct` tier and returns nothing if a reviewed row
disagrees. Production reads only the reviewed (`exact`) rows of
`codecs/levelscript/action_map_layouts.json` through
[`action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py),
whose docstring owns wire shape, gate mechanics and non-obvious Param shapes.

One proof pattern covers every route: switch jump and registered wrapper fix
identity; the complete reader and forwarding formatter fix member count,
ordered reads and setters; typed `Param<T>` contexts fix parameter, element
and enum types; ledger-joined source spans replay exactly. That proves stored
fields only, never an action run, event fired, getter value or resolved ID.
Per route: `contracts/levelscript_<route>_native.json`, validator
`python -m scripts.game_data.levelscript_<route>_native` (its docstring holds
stored fields, reached authored forms and non-proofs), sometimes a
`codecs/levelscript/` codec, and an `action_map._required_native_gates` entry.
Promotion: (1) isolated contract, validator, tests; (2) layout row, gate
entry, production replay, clean derivation; (3) whole-owner closure, decided
only by the full JsonData gate (`scripts.game_data.jsondata_corpus`) at
physical EOF. Projections between (2) and (3) are provisional.

## LevelScript route status

The production inventory is the reviewed `action_map_layouts.json` plus
`action_map._required_native_gates`; route-specific fields, native proofs and
reached authored forms belong to each validator's docstring and contract.
The earlier per-route investigation narrative is condensed into that reusable
surface rather than duplicated here.

Native admission is selected-build evidence. Historical source receipts and
prior successful owner replays do not become current when a parent contract is
migrated. The shared typed-route migration re-proves complete owned readers,
union identities, typed contexts and setter order. Legacy source records that
lack an authenticated span digest are withheld, rather than converted into
current receipts. Entity attachment, spawner/camera and script-end/proxy readers
use this gate; their node strings bind to the actual pooled source helper.

The recent action/getter/header and task-condition batches pass their native
validators, source-span receipts, layout derivation and selected production
replays. Some selected owners close at named-exact physical EOF; others expose
later routes. The combined `jsondata_corpus` gate owns their whole-owner
publication. A source-specific EOF result never changes a family denominator
by itself.

After that boundary, run `levelscript_first_stop_census` against the new
summary and pinned per-file ledger. It rechecks each residual source and ranks
whole files at the first refusal; later unions stay hidden until that refusal
is recovered. Native-gate failures are tooling/build diagnostics, not schema
frontiers. Keep changing rankings and selected-source inventories in reports.
Stored action, event, getter and task-condition inputs establish no execution,
resolved target, property value or mission order. The census replays each
residual through the owner its action-map root selects (empty, null or current
sequence, as `frame_levelscript_named` does) with the gated export StringPool,
snapshotted before and after the replay; a census without the pool ranks a
StringPool-index refusal, not a format frontier.

The same authenticated first-stop census now selects `LevelScriptTemplateData`
with `--family`, retaining a separate owner and report. It joins that family's
ledger count, safe source path, length and logical hash before invoking the
template reader; action-map record positions are normalized while list kind,
union tag and member count remain distinct. A template's endpoint framing does
not close its opaque interior. The template reader now retains bounded
properties/property-map/task-map continuation diagnostics instead of discarding
those refusals, and removes them only after named physical EOF. Template
blackboard native-contract refusals fail the census rather than entering its
format ranking. The census is a route-selection aid, never a whole-family
promotion or runtime/mission-order proof.

The current template reader uses the owning StringPool and one sequential
cursor; the inline terminal-string suffix scan is removed. Its selected root
fact records the declared order and terminal pooled source/owned setter.
Positive blackboard, property and task children stop before their unproved
contents, leaving the following bytes opaque, including any apparent terminal
ID. Reviewed action-map nodes receive the same selected pool. Only a cursor
that reaches physical EOF names the whole template. A final source setup may
reuse the holder register for its pointee: require saved argument identity up
to that selected load and verify both exact setup moves, rather than requiring
the holder's old value after its last use. Historical closures and isolated
child proofs do not establish current named EOF.

The full JsonData gate compares the complete raw-format reader scope before
and after decoding, including added Python sources and contract JSON. Prepare
capture-profile and other raw-format edits before starting that sweep, then
keep those inputs fixed until publication. A drift refusal preserves the
previous publication and reports a bounded, sorted list of added, removed or
modified files with their expected and actual lengths and hashes.
During that run, freeze every `.py` and `.json` under `scripts/game_data/`,
including consumer contracts and census tools outside the active Buff import
closure. The complete LevelScript scope protects these negative dependencies
too; checking only the current family's imported files is insufficient. Keep
independent probes and their output outside the package until the run finishes.

The reusable `levelscript_route_deserialize_native.py` validator now admits
typed route contracts as well as the earlier read/setter-window contracts.
Typed admission joins the native union switch and registered wrapper to the
generated member count, complete reader and owned native fragments, ordered
read/setter calls, exact generic `ReadValue` context and authenticated logical
source spans. Grouped routes use
`contracts/levelscript_stored_routes_current_native.json`; specialized routes
retain their own parent contracts. `levelscript_stored_routes_native.json`
is the isolated integer-switch collection contract. Parent admission never
replaces the current child gate. The validator also authenticates
`ParamOutput<T>` separately from `Param<T>`:
the selected generic reader must name the exact output type, while the existing
two-member output codec reads only its source selector and path. This covers
scripted-patrol event outputs and camera-effect save IDs without treating those
stored destinations as observed values. Header enums additionally require
their native `value__` field to be signed Int32; a four-byte wrapper shape alone
cannot distinguish signed and unsigned backing types. The shared validator
refuses missing or different generic contexts and enum declarations.
The same admission now covers `EntityEvent_OnIntTryUnlock`,
`LevelEvent_OnTravelPoleBegin`, `OnHitByLaser`, `GetterString`,
`GetSpawnerGroupKeyOfEntity` and `ToggleGeneralAbilityLoneClick`. The unlock
header retains separate target entity, entity-list and output operands; its
`EntityEventHeader.TriggerTarget` requires its own signed-Int32 declaration.
The travel-pole and laser-hit headers retain typed output destinations, while
the getters retain authored string/entity inputs. None proves the output value,
resolved spawner group, target selection, unlocked state or event firing.
`LevelEvent_OnEntityTakeDamage` now retains its damage/entity outputs and typed
entity and boolean filters. `ListGetValueInt` and `ListGetLengthInt` retain
their typed `Param<List<int>>` parent reads; the literal Switch list proof does
not authenticate that Param child. `MainCharMoveToDirection` and
`MainCharStopNavMove` retain their direction, gait and navigation identifiers;
the gait requires its own native signed-Int32 backing proof. Every output,
list Param and gait reader needs its exact typed context and current child gate.
Stored routes do not prove damage, getter results,
actor movement or navigation completion; later owner blockers remain partial.
This improves the canonical stored owner and Data inspector; it adds
no Story playback, mission trigger/order or runtime property claims. Source-span
replay still requires the complete current JsonData gate before whole-owner
EOF or corpus counts are published.

The grouped current parent contract includes `AddSystemUnlockOverride` and
`EntityRotateDeltaWithDuration`. The former retains its authored unlock flag
and system enum; the latter retains Euler-angle delta, duration, easing enum,
entity operand and a separately typed unsigned output destination. Their
complete generated readers, selected generic contexts, ordered read/setter
calls and source spans are authenticated independently. Both enums require
their own native signed-Int32 backing declaration. These are stored operands
and output paths, not an unlocked system, observed rotation, completed tween,
output value or execution order. Selected same-source replays do not replace
a current complete JsonData gate, especially when the exporter/audit run
identity has changed.

`RemoveSystemUnlockOverride` independently authenticates its own action union,
complete reader and authored `UnlockSystemType` operand while reusing the
already proved enum Param grammar. Patrol-event and pressure-board-sequence
failure headers keep their separate header dispatcher: the former retains
entity, event-key and patrol-ID destinations plus its key filter; the latter
retains a typed module operand and `ParamOutput<LsmPtr>` destination. The
output's two members remain a source selector and path, with no manual module
value. Its exact output generic context is required independently of the
existing input Param. Header definitions do not establish event firing,
returned IDs, resolved modules or mission causality; complete selected owners
remain projections until the current whole-corpus gates admit them.

`RemoveMovementSettingModifier` has its own selected action-union, complete
generated reader and ordered actual setter proof. Its only additional member
is an authored `Param<string>` modifier name; the actual closed `ReadValue`
context must name that string Param before the established child grammar is
reused. A source span and a matching display name cannot replace this parent
gate. The stored name does not prove that a movement modifier existed, was
removed, or changed an actor. Whole-owner closure still needs a real sequential
owner replay, while corpus publication needs the separate complete family gate.

`CharacterStopMontage` remains outside this parent admission. Its reached
`Param<EntityPtr>` getter-reference bytes fit the existing structural codec,
but that acceptance is not an independent native child proof. The generated
EntityPtr declaration checks in the task-map contracts establish member shape,
not the complete native embedded-value bridge. The actual typed child reader
returns a structured value through formatter dispatch; its default wrapper
read order, owned value copy and return composition must be authenticated
separately. Live provider/cache selection remains unresolved. Do not substitute
the Race root, a managed display name or a raw-size match for that join.

`Beyond.MemoryPack.Beyond_Gameplay_RaceDataForMemoryPack.Deserialize` declares
`finalInteractive` through typed `ReadValue<EntityPtr>` and `npcEntityPtrList`
through `ReadPackable<List<EntityPtr>>`. The actual EntityPtr shim/provider
path returns a forty-byte aggregate requiring conversion; neither the named
three-member declaration nor its summed member widths proves that bridge.
[`modules._entity_ptr`](../../scripts/game_data/codecs/levelscript/modules.py)
is a framed stored codec, not authentication of this provider-return form.
The actual typed `ReadUnmanaged<Vector3>` normal source separately establishes
twelve raw component bytes, but closes neither EntityPtr conversion nor the
list provider. Keep Race parent admission unresolved until those child joins
are independent; an inventory or matching child display name cannot admit it.

`ToggleControllerHintBar` independently authenticates its authored key and
visibility boolean. `NpcProxyPatrolPointPassed` uses its separate getter union
and retains patrol identifier, point index and target proxy name. Both compose
the established primitive Param grammar only after their complete generated
readers, exact closed generic contexts and ordered actual setters pass the
selected native gate. Neither establishes visible UI state, proxy resolution
or a patrol point having been passed. Selected owners may close while other
owners advance to an unreviewed header or getter; a terminal suffix must retain
the preceding reader refusal and cannot close that earlier stored range.

The travel-pole enter, exit and reach headers are each authenticated independently
from the begin header and from one another. They preserve the inherited header
filters, boolean validation and
entity/key output destinations. `ParamOutput<EntityPtr>` reads its selector
and path only; it requires no manual EntityPtr input or embedded-value claim.
`StringFormat` independently retains its format and string operands under the
getter dispatcher. Stored output paths and string operands establish neither
an event firing nor a resolved formatting result.

The factory culling override, top-view toggle and build-mode exit retain their
authored boolean/float operands or inherited action fields under independently
authenticated parents. `GetterFloat`, `SendLuaEvent` and `GuideFreezeWorld`
likewise compose the established float, string, boolean and integer-output
grammars after their own generated readers and closed contexts pass the native
gate. Their stored values do not establish a visible factory view, an evaluated
getter, dispatched Lua event or a live frozen world. Later getter or action
refusals remain explicit even when a weaker profile finds a terminal suffix.

`GuideUnFreezeWorld` is an independent action parent and reads an integer
handle operand. It cannot reuse the freeze action's integer-output context:
the input Param retains its authored value, selector and path, whereas the
output stores only a destination. Neither reader establishes a live freeze
handle or the world having resumed.

The independently reviewed GameplayTag, WaterVolumePtr and EnvironmentVolumePtr Param children use
different actual buffered scalar source programs: the tag consumes an Int32,
and the volume operand consumes a UInt64 with its own cursor advance. Their
registered generic helper pointers are authenticated provenance and differ
from the actual parent calls; this proof does not establish registered helper
execution. Each child binds the actual read result to its ordinary typed
setter, proves all four Param properties in read order, and retains the
independently gated pooled path reader. Current v2 paths consume one signed
StringPool index: empty is `-1`, null is `-2`; other indices require the matching
exported pool. Pool-present selection remains conditional. Wrapper stores prove an owned
holder destination, not an independently recovered generic Param heap layout.
Fresh allocation bridges remain conditional on normal allocator,
initialization and barrier behavior, compatible wrapper/reader/storage and no
interference. Heap identity, refill paths and live provider selection remain
unresolved. Missing or mismatched selected native inputs refuse the child and
preserve a native-contract diagnostic rather than accepting its raw width.
Primitive Boolean regeneration checks the complete buffered byte-read program,
counter advances, normalized AL return and retained frame. Required instruction
substrings alone do not establish that transfer. A Boolean Param's inline
owned-holder stores need their own composition proof beyond that source check.
The allocation usage type has its own ordinary-reference ABI gate in addition
to the full raw type-record equality: modifiers, byref, pinned and a value
marker refuse the allocation bridge. This does not rely on a display name
match or on the property's separately checked holder type.
The reviewed child contracts are
[`GameplayTag Param`](../../scripts/game_data/contracts/levelscript_gameplay_tag_param_native.json)
and [`WaterVolumePtr Param`](../../scripts/game_data/contracts/levelscript_water_volume_ptr_param_native.json).
The independent [`EnvironmentVolumePtr Param`](../../scripts/game_data/contracts/levelscript_environment_volume_ptr_param_native.json)
uses the same proved UInt64 source profile with its own typed contexts and
owned setters. Its parent EnvironmentEnable route remains a separate migration.
The current [`SplinePtr Param`](../../scripts/game_data/contracts/levelscript_spline_ptr_native.json)
uses a separately proved Int32 load and cursor advance, a saved RSI reader and
an RDI holder. Its v3 declaration also records the factory-shaped constructor
and reversed null guard in the path setter. These complete programs retain the
same typed allocation, source, owned-store and pooled-path checks. Both scalar
and Int64 parents recheck the dependency's Unity input after composition;
missing or changed bytes empty the result even when composition was cached.

The independent [`Boolean Param`](../../scripts/game_data/contracts/levelscript_bool_param_native.json)
proves its generated byref ABI, owned allocation bridge and inline byte/Int32/
reference stores against the matching typed setters. Its byte source normalizes
nonzero input; the path consumes a pooled index. The public loader rechecks
native inputs, Unity and dependency declarations after composition.
This proves owned setter slots, conditional on compatible initialized holders,
not a separately established generic heap layout or live formatter selection.
ActionMap requires this child gate for present and null Boolean Params and
uses the pool-present wire reader for their paths. EnvironmentEnable retains
its separate parent and source-receipt gates.
The independent [`Int32 storage contract`](../../scripts/game_data/contracts/levelscript_int_param_native.json)
shares `memorypack/primitive_param.py` with Boolean while retaining its own
typed wrapper, DWORD source and stores. This storage proof is separate from
the Int32 evaluator and enclosing cursor/owner admission. ActionMap requires
this child gate even for null Int32 Params and reads paths as pooled indexes.
Enum backing width does not select this formatter: former enum-to-Int32
shortcuts refuse until their own composition is proved.
The [closed enum catalog](../../scripts/game_data/contracts/levelscript_enum_param_native.json)
authenticates reviewed closed Int32 enum components, including ScriptEndReason,
SpellAbnormalType and PhysicalInflictionType:
ordinary signed backing and typed ReadUnmanaged arguments, complete initialized
caller/null control, named owned setters, raw DWORD sources and pooled path.
ActionMap requires the particular component before consuming any bytes, including
null. Unlisted or differently backed enum components remain withheld; live provider selection, generic
heap layout and complete owner admission are separate.

LipSync's selected [channel reader](../../scripts/game_data/contracts/lipsync_native.json)
independently authenticates the channel declarations, member count, complete
reader windows, typed array contexts and ordered setter calls. Its corpus gate
also selects the language blocks through their exact ID, name and path namespace;
wholly absent languages remain explicit exclusions. Stored EOF closure does not
establish live formatter selection, Keyframe consumer semantics or playback.

The JsonData registry checks required Buff/Skill native input identities before
reading their family receipts. A missing or mismatched selected build withholds
that family's named decoder and old receipts while retaining authenticated file
identities as unsupported. Matching inputs still require every original receipt,
source and parser check. Gates and reader inputs are rechecked after the scan;
this publication behavior does not re-prove an unavailable native family.

The installed Buff icon wrapper adds `showProgressInEnemyHeadBar` immediately
before `showProgressInHpBar`. Its reader checks the new member count and writes
the inserted Boolean in that order. The historical icon contract's shorter
record and inline UTF-8 sprite path must not be repinned: the selected sprite
source now uses the separately authenticated pooled-string helper. Updating
that child still requires its complete typed read, field-transfer and native
layout proof, followed by the owning Buff root and corpus gates.

Keep the creation and conversion interfaces separate: a reference-returning
`GetValue` does not prove the instance-void `CreateInstance` program. A missing
concrete generic registration must not be invented from its canonical entry;
join the explicit concrete MethodInfo and same-definition shared target while
leaving provider state and execution unproved.

The closed `ParamOutput` components independently authenticate their typed
wrappers, owned setters, complete caller variants and null exits. They store
a signed Int32 `paramTarget` and a pooled path, with no serialized T value.
ActionMap requires the selected component before consuming present or null
outputs. Specialized event headers also forward their native root and pool;
spell-abnormal and physical-infliction headers use their independently proved
enum components. Default provider selection and whole-owner admission remain
separate.
The independent [`String Param`](../../scripts/game_data/contracts/levelscript_string_param_native.json)
uses that shared checker for both pooled reads and both reference barriers.
ActionMap requires its gate for null and present values; the value and path
each consume a signed pool index, preserving null versus empty strings.

The reviewed
[`null/empty List Param`](../../scripts/game_data/contracts/levelscript_null_list_param_native.json)
gates each closed kind before even its one-byte outer null. EntityPtr, UInt64 and string
constants admit signed collection count minus one or zero, preserving null
versus empty; Vector3 constants remain minus-one-only. All retain their two signed bindings
and pooled path, and every positive collection count refuses without advancing
the owning cursor. The schema declares capabilities per closed kind rather
than treating one kind's zero path as a generic list capability.

The same four closed proofs may be prepared for one explicitly selected
root-and-pool operation. Entry and exit each derive their current native
semantics afresh, with complete reader, native, Unity and pool bookends.
Only the active capability for that exact root and pool reaches the maintained
cursor; leaked or mismatched capabilities refuse. Direct per-Param calls still
perform their own fresh gate. Owners continue to decode their actual bytes,
and failed exits withhold the enclosing operation's output. Corpus callers
retain their raw/VFS and logical receipt checks; the protocol's typed node scan
also rechecks its authored file set and bytes, without gaining whole-owner or
VFS admission. The shared image's unwind index reuses immutable exception-table
facts, while body, context and window proofs remain fresh. A saved family
receipt supplies source identity and freshness, not complete decoded frames.

The EntityPtr zero path has independently checked new/existing source programs,
owned typed List/constructor contexts and a count-zero constructor. Its actual
optimized Clear and registered closed leaf Clear have matching selected memory
and argument effects through the same array-clear helper; open generic field
offsets are placeholders and never substitute for that proof. The pre-loop
optimized provider still must return normally without interfering with the
disjoint reader/output/frame, but its result is unused and no element formatter
is consumed. This conditional wire profile proves neither effective live
provider/default/cache selection nor the remaining owning action fields.

The UInt64 list has its own closed formatter, typed Param adapter and collection
proof. Its source inlines the signed count and reader cursor updates. Null skips
the constructor, Clear and provider; zero separately proves the initialized
new-list constructor or existing-list count/version stores. Those effects join
the actual closed constructor and Clear declarations, their owned generic
contexts and the selected field slots. The zero path still calls its actual
optimized provider before the loop test, under an explicit normal noninterfering
return condition; the returned formatter is unused. No EntityPtr instruction
profile, open-generic field offset, positive element path or provider-body
equality substitutes for this independent proof.

The string-list Param independently proves its current generated parent,
adapter, typed stored fields and pooled bindings. Its actual closed
ReadPackable MethodSpec, usage cell and native read target match the separately
reviewed literal string-list caller. The current reference-sharing source,
owned generic contexts, open List factory and initialized provider conditions
are checked through that lane; null and new-zero paths consume no elements.
The selected existing-list zero path requires its prior count zero. Both actual
and canonical Clear bodies independently prove the complete count/version
stores and return for that case; positive prior-size clearing stays unproved. Only those null/empty Param paths are admitted. Literal positive
count witnesses do not admit positive Param lists, establish an unbounded loop,
or prove live provider selection, inflation or initializer execution.
The [`Single Param`](../../scripts/game_data/contracts/levelscript_float_param_native.json)
adds a complete buffered XMM read/restore and its typed XMM store. Its gated
finite wire reader preserves Float32 precision and signed zero without rounding.
Shared Int32 source guards must leave the buffered body for cold paths.
The [`UInt32 Param`](../../scripts/game_data/contracts/levelscript_uint_param_native.json)
uses a distinct header/helper and typed-setter program. Its contiguous hot
chunks and null branch join only through authenticated unwind ownership; the
null edge skips the RSI restore whose save it never executed. Its wire reader
requires this separate gate and interprets the constant as unsigned bits.
The [`UInt64 Param`](../../scripts/game_data/contracts/levelscript_ulong_param_native.json)
proves the corresponding QWORD return and setter argument, with the actual
inline eight-byte counter updates. Its source differs from the separately
proved Advance-calling UInt64 helpers used by other current scalar wrappers.
Long, SplinePtr, GameplayTag, WaterVolumePtr and EnvironmentVolumePtr gates
also run before the common null shortcut. Missing or mismatched component
evidence leaves their cursors untouched for both null and present values.
Byte-backed enum Params likewise require their own selected formatter proof;
their former byte shortcuts and the unproved plain Byte component refuse.
The [`Vector3 Param`](../../scripts/game_data/contracts/levelscript_vector3_param_native.json)
joins its caller's MethodInfo to the independently typed raw Vector3 reader,
then proves the disjoint twelve-byte stack result and both owned field copies.
Its gated finite wire reader uses a pooled path. This closes that component,
while PosRot's list/default composition and whole-owner admission remain separate.
The [`Vector2 Param`](../../scripts/game_data/contracts/levelscript_vector2_param_native.json)
separately proves two Single loads, UNPCKLPS low-lane packing, full QWORD return
and both SIMD restores in the actual and registered readers. Its caller keeps
the matching MethodInfo live, and its typed setter splits the same packed XY
bits into the two owned fields. Vector layout and unwind recording are shared;
their distinct native programs remain independently checked.

`codecs/levelscript/node_strings.py` binds plain node string fields, including
UIDs, to the exact reviewed route fields and its recorded string helper.
The selected pooled source, native-input agreement and supplied pool resolve
the signed index; unmatched bindings refuse. The generic string cursor also
refuses an unbound UID, so pool index zero cannot be mistaken for empty inline
text. The canonical action/getter/header
sequence reads these reviewed nodes directly. Other child/string contexts and
complete owner admission still require their own proofs.
The typed route shape binds its node strings through its exact read order and
nested native-input pins. Its regenerator rederives the complete reader,
union identity, typed usage and setter transfers; historical receipts remain
separate. Receipt replay forwards the selected native root and export pool,
checks the pooled source helper, and uses the same gated child cursors.

`PreloadNpcMontage` and `WaterVolumeSetAmount` retain independently proved
parent union identities, complete generated read orders and closed Param
contexts before composing those children. A stored tag is not a resolved
montage, and a volume identifier/amount is not a live water-volume mutation.
Selected source advancement remains separate from a complete family receipt.

The later `CharacterPlayAnimationMontage` candidate still contains a non-null
EntityPtr Param. Its independently proved GameplayTag operand does not close
the entity child's owned-return/selection gap, so this parent remains refused.
Likewise, `ListSetValueBool` stores a null manual Boolean-list value in the
selected template sources, but its actual typed ReadPackable call first enters
provider/selection logic. A null source value cannot establish that selection
was skipped, and the closed generic registration lookup does not independently
resolve this child. Neither the observed NULL bytes nor a matching List<int>
declaration admits the Boolean-list Param. Keep both dependencies unresolved
until their own actual composition is proved; do not widen the existing entity
or list grammars to obtain a parent EOF.

The script-pre-active header candidate has a null target-script Param in its
selected source. Its actual typed ReadValue call performs provider and adapter
selection before payload interpretation. A source `0xff` and an isolated
default wrapper's null-output branch therefore cannot close that earlier join.
Keep this header refused until the actual selected composition is independently
proved; a structural non-null pointer codec or a null-only field restriction
cannot supply the missing native evidence.

The collision-toggle parent stores an Int32 input and an Int32 output
destination; the dither-toggle parent stores a Boolean parameter. Extra-streaming
load stores a Vector3 position and a Boolean shrink flag. Their independent
dispatcher, complete inherited order and typed read/setter joins compose the
existing child grammars. These stored operands establish neither collision or
dither state nor streaming execution or coordinate meaning.

The boss-skip-button parent stores one Boolean show parameter; extra-streaming
clear and gender-selection start add no members beyond the independently
proved inherited action fields. Each still has its own dispatcher identity and
complete parent read order. Their stored records do not prove UI visibility,
streaming cleanup or the selected gender.

Clear-screen toggle stores its Boolean show parameter; UI-panel blackout
stores a panel-name string and a Boolean flag; atmospheric-NPC environment-talk
reset stores its identifier string. Independent typed parent reads compose the
existing Boolean and string parameter grammars. The decoded records do not
establish UI state or an executed NPC-talk reset.

The dramatic-performance item-toast and dungeon-skip-panel parents store their
string identifiers. Anchor-core decoration refresh stores a Boolean and separate
close-animation, group, open-animation and scene strings. Their complete typed
parent reads reuse the independently proved parameter grammars; they do not
establish the displayed toast, panel state or an applied decoration transition.

The dramatic-performance bag parent stores a Boolean output destination;
dungeon-info popup and snapshot-close add no members beyond the inherited
action fields. Their independent parent proofs establish stored records, not
the output's runtime result or whether either UI operation executes.

The independent GameCondition domain also admits the dramatic-performance-bag
finish record with only its inherited fields, cutscene-finish with a string
parameter, and squad-in-fight with a Boolean parameter. Their own condition
dispatcher identities, complete field order and typed operands are authenticated
separately from ActionBase tags. Decoding these records does not establish that
a bag or cutscene finished or that the squad is actually fighting.

Client-global-variable comparison composes its own condition parent with the
independently proved signed-long parameter, comparison enum and string key.
Squad-revive condition and high-difficulty-notification reset add no fields
beyond their respective condition and action bases. These stored declarations
do not identify the evaluated global value, a revival event or notification state.

The stored water-fill-speed parent independently reads its float speed and
WaterVolumePtr operand. The snail-fill-complete header stores only an EntityPtr
output destination, while the main-character-change header stores separate
entity and template-ID destinations. Those outputs need no manual EntityPtr
value grammar and do not establish observed event values. Their inherited
header fields and generated reader order keep independent native evidence.
`ResetNpcEnvTalkTriggerDistance`, `SetPlayerName` and
`ClearMainCharFocusTarget` each carry only the inherited action fields; their
names do not supply a serialized distance, player name or focus target. These
parents prove stored framing and preserve downstream refusals, not execution.

The name-keyed v5 action layout separates field order from current union tags.
`GameCondition` retains an independent dispatcher, tag, wrapper, member count,
branch identity and actual read/setter order; an ActionBase audit with the same
numeric tag cannot authenticate a condition. Each reviewed condition needs its
own current native gate, including missing/mismatched and count/field identity
refusals. `GameConditionServer` remains a separate domain.

`FloatGetterMinus` stores two float operands and
`SetNpcEnvTalkTriggerDistance` stores one float operand. Their bytes do not
establish subtraction or a changed live trigger distance. `CheckFMVFinish`
independently retains the condition scope, unique ID, scope switches and a
string Param for the FMV identifier. The stored identifier establishes neither
resolved media nor completed playback. Historical family-artifact byte
identity may associate selected source replays after a reader change, but
cannot transfer the old full-reader status or EOF to the changed reader.

`FloatGetterMultiply` independently retains its two float operands, while
`InterruptHenshin` adds no child field beyond the inherited action fields.
`CheckServerGlobalVar` retains separate comparison/key enums and a signed
Int64 target Param. Both enum backing declarations require ordinary signed
Int32 metadata; byref/pinned modifiers and a different primitive kind refuse,
while the independent value marker is permitted. The closed Param argument
remains an ordinary reference and cannot carry that value marker.
[`levelscript_long_param_native.py`](../../scripts/game_data/levelscript_long_param_native.py)
authenticates the actual buffered QWORD read and cursor updates, the ordinary
signed `long` property setter, owned holder and four-field read order, and the
fresh allocation bridge. This physical source is not identified as a closed
registered `ReadUnmanaged<long>` helper. Its stored composition remains
conditional on the selected default generated wrapper and normal allocator,
initialization/barrier and compatible storage; refill, provider/cache selection
and live condition evaluation stay unresolved. Parent and non-null child
reads keep separate missing/mismatched native gates and preserve the selected
input paths. Historical receipt/source replay can establish new selected EOF
results, but cannot publish a changed full-family reader snapshot.
Its current v2 path is a StringPool index through the separately authenticated
BeyondReadString clone. Inline UTF-8 lengths are not interchangeable with that
index. The canonical LevelScript reader accepts an explicit matching pool;
saved values and Data-page cache entries also bind the complete pool page set
and bytes. Added, removed or changed pages and mid-read drift withhold reuse.

[`levelscript_param_value_native.py`](../../scripts/game_data/levelscript_param_value_native.py)
independently authenticates selected closed Int32 `GetValue`, `TryGetValue`
and `get_useGetter` registered entries. The actual caller targets must match
those entries, and ordinary method-generic return/default types, the explicit
byref output and the Boolean flag are proved before interpreting their raw
register transfers. The selected initialized/ready constant path copies the
parameter-compatible DWORD through the caller's local output into its Int32
return. Other selected normal returns use the incoming fallback; the success
Boolean is the low return byte after the output write, not the copied integer.
Generated closed-Param wrapper setters and its holder getter independently
provide a conditional view of source, constant and reference slots. Compatible
unchanged receiver storage, ordinary call/frame conditions and each selected
context branch remain explicit requirements. Runtime object/MethodInfo identity,
provider choice, nonconstant evaluation and stored formatter cursor integration
stay unresolved. The getter predicate's negative markers do not authorize new
serialized source alternatives. The explicit selected native pair and proof
sources are checked before and after validation; a refused audit clears rows
and preserves the previous publication.

[`levelscript_long_param_value_native.py`](../../scripts/game_data/levelscript_long_param_value_native.py)
evaluates qualified named Int64 consumer claims on the explicitly selected
native pair. Its caller independently preserves full fallback bits or returns
the current QWORD output; the selected constant path writes the complete QWORD
before returning success and restoring its frame. Branch-linked fragments must
remain inside the same authenticated owned native range; adjacent function
bytes do not belong to that control flow. The small getter predicate is a
bounded registered-entry-to-normal-return proof, with no inferred unwind range.
Generated wrapper getter/setter declarations supply a compatible named slot
view and must share the same concrete parameter definition as the evaluator.
The shared `levelscript_param_types` reader proves reciprocal class-variable
ownership, its ordinal and sole declared arity; method-variable arity and
explicit byref output are checked independently. A name suffix or one native
argument alone cannot replace those declarations. These evaluated claims carry
current addresses and byte hashes only in their generated report; their
reviewed contract names the methods and meaning. Unprovable changes remain
pending review. Runtime receiver/MethodInfo/provider choice, other selector
paths and the stored cursor/evaluator join stay unresolved; the stored Int64
formatter proof and parent owner EOF remain separate.

[`levelscript_long_param_storage_consumer_native.py`](../../scripts/game_data/levelscript_long_param_storage_consumer_native.py)
adds a separate conditional composition of those two Int64 proofs. It joins
the actual concrete wrapper, ordinary closed holder definition, getter and
constant/source setter identities, and checks complete field byte intervals
for overlap. The stored `CONST` selector takes the getter predicate's false
return, bypasses the caller's reference-id guard, and selects the constant
callee's full-width output and success byte before the caller returns the
current output. This is one selected initialized/ready path; other caller
alternatives are not assigned to the stored constant.

The deserializer reloads its wrapper through an output slot and each setter
reloads the holder. The composition therefore requires the same selected
wrapper and holder throughout field population, getter and consumer use,
plus unchanged constant/selector storage apart from the proved field writes.
Disjoint stores do not prove opaque source/barrier callees or concurrent
writers cannot interfere. The actual invoked pooled-string contract and selected
Unity image join the native pair and Python/JSON proof sources in the
before/after gates. Refusal clears the association and preserves the previous
publication. Runtime receiver/provider/MethodInfo selection, nonconstant
evaluation, positive enclosing owner/list admission and live execution remain
unresolved; the independent readers retain their own evidence boundaries.

[`levelscript_global_var_callback_native.py`](../../scripts/game_data/levelscript_global_var_callback_native.py)
independently proves the complete owned `CheckClientGlobalVar.EventCallback`
partition and its selected original normal paths, including initialization
branches and the full retained frame. The same preserved receiver supplies
fresh comparer and target Param loads. The actual loaded comparer MethodSpec
closes `CompareOperator`; the physical entry is separately registered for
`Int32Enum` with an ordinary Int32 enum backing. Shared implementation
compatibility remains a condition, rather than being inferred from a physical
entry match. The loaded Int64 context and actual registered call are joined
independently.

The callback reads an anonymous QWORD from its explicit byref
`EventData<long,long>` input and retains it across the parameter requests.
The ordinary value-generic declaration, both Int64 arguments and reciprocal
variable ownership are checked, but the generic definition's field offsets
do not establish concrete field placement. The lane therefore has no inferred
field name. Its signed Int64 value and the current Int64 parameter return
undergo separate Single conversions before the actual ordinary `DoCompare`
request; MXCSR rounding and exception conditions remain explicit. This does
not establish an exact integer comparison or a concrete converted value.
The comparison's low return byte is zero-extended into an ordinary
`ConditionResult` enum setter request. Normalization, comparison semantics,
setter effects, runtime event/provider selection and ordering remain open.

Both this contract and the stored Int64 composition declare dependencies as
relative path rows in the shared dependency enumerator's array format.
Their schema changes accompany the reader changes. Native and actually read
JSON/Python inputs are checked before and after proof; staged publication
rechecks freshness and output/input aliases before replacement.

[`levelscript_bool_param_value_native.py`](../../scripts/game_data/levelscript_bool_param_value_native.py)
independently evaluates the ordinary closed Boolean declarations and actual
caller targets. Its selected constant path copies one source byte through the
original explicit byref output, returns success in the low byte, and restores
the complete retained frame. The caller zero-extends its current output byte
or the original fallback byte into the return register. This byte transfer does
not prove normalization to `0/1`; success and the transferred value remain
distinct. The generated Boolean wrapper setter provides a compatible named
single-byte slot view, joined to the same concrete Param definition. The
Boolean and Int64 readers share named declaration, registration and wrapper
proofs in `levelscript_param_value_bridge`; their return programs and widths
remain separate. Qualified images, reciprocal class/method variable ownership,
sole arity and explicit byref declarations precede every interpretation.
Initialized/ready branches and unchanged compatible storage remain conditions;
runtime receiver/MethodInfo identity, nonconstant providers and stored cursor
integration stay unresolved. The predicate's server marker does not add a
serialized source alternative. Native/source refusals leave previous valid
publications intact.

[`levelscript_float_param_value_native.py`](../../scripts/game_data/levelscript_float_param_value_native.py)
proves the ordinary closed Single variant separately. Its complete caller has
a primary native range and an explicitly chained cold range: both raw
partitions, their actual branch targets and the parent unwind identity must
agree before interpreting a return. Selected initialized/ready paths return
either the current four-byte local output or the incoming fallback's low
Single bits. The full retained frame restores the saved integer registers and
XMM6. Its selected constant callee transfers a DWORD unchanged, then returns a
distinct Boolean success byte; the generated ordinary Single setter supplies
the compatible named field view. These transfers perform no floating arithmetic
or conversion. The shared metadata bridge still requires the same concrete
Param definition, reciprocal sole class/method variable ownership and explicit
byref output. Runtime receiver/MethodInfo selection, nonconstant evaluation and
the stored formatter-to-evaluator join remain unresolved.

Native union identity's type pointer denotes the dereferenced registration
entry, not the address of the table cell. Authenticate the usage index, table
cell arithmetic, complete ordinary class record and full wrapper identity
before correcting a recorded pointer; retaining matching usage bytes alone
does not close that join. The stored-route validator also rechecks the actual
selected native pair after its proof/source work and clears every validated
row on a late refusal, including when an inner proof reused immutable native
indexes. Successful semantic validation results are not cached.
Its CLI publishes only a validated audit, atomically under the ignored reports
root. Initial and write-time resolve/samefile checks protect contract, layout,
native, proof, selected source and reader/configuration inputs, including late
aliases. A missing/mismatched/unresolved audit or a legacy validator exception
leaves the prior main report untouched and emits a structured nonzero-exit
diagnostic; it does not publish an empty replacement as current evidence.

`Vector3GetY` stores a vector operand rather than a serialized computed Y
result. `SetSquadMemberPosRot` retains separate position/rotation vectors and
a slot operand without proving coordinate conventions or live placement.
`SwitchMovementSetting` retains a release-reset flag and a separately typed
MovementSettingName Param. That enum requires its own signed Int32 backing,
ordinary closed argument and actual parent read context before reusing the
integer Param grammar; a matching enum name or four-byte width is insufficient.
The stored selection does not establish an applied movement setting or reset.

The same independent parent admission now covers ordinary stored visibility,
main-character-switch and fire-seed-check flags, unique entity-list insertion
operands, and navmesh-area bake operands. Existing Boolean/entity/list grammars
are reused without widening their accepted authored forms. The character
perfect-dodge header separately retains entity output/filter and Boolean
filters through its header dispatcher and complete inherited read order.
These stored definitions establish neither visibility/switch outcomes, list
mutation, a baked navigation surface nor an actual perfect-dodge event.

`CameraShake` remains unadmitted in this batch. Its generated configuration
wrapper holds `__instance`; a store offset matching the original type's boxed
field offset does not prove the owned nested value slot. The Param reader's
optimized final path uses a different receiver register from its earlier
members. A future child composition must prove the typed byref output,
wrapper/embedded-value representation, string-return store and setter slot,
plus the actual final-path receiver preservation. Existing cursor support or
the outer action's typed ReadValue context alone does not close that child.

Property/proxy getters and entity-event headers use the same typed admission
through grouped or specialized current parent contracts. A Vector3 property
getter stores its property path and target script reference, with no serialized result;
saved-property and proxy getters likewise retain only authored operands.
The water-drone header's `targetEntityListOutput` is independently proved as
`ParamOutput<EntityPtr>` despite its list-shaped name. Output destinations
never stand in for delivered values. Each complete reader and source span is
checked before shared-codec reuse; later owner refusals and the full corpus
gate remain separate obligations.

## LevelScript route-specific conclusions

The name-keyed layout carries no build hashes. Corpus and frontier tools use
the current union-tag contract pins and refuse absent or malformed pins. A
per-node native audit may select one route while retaining every shared native,
reader, enum, collection and child gate; a full audit still checks all routes.
Neither form reuses a successful semantic validation result.
One opened native image may share immutable registration positions, folded
aliases, instantiation pointer positions and declaration-container arrays.
Selected triples, reciprocal ownership, arguments and semantic claims are
rechecked on every operation; duplicates and missing identities still refuse.

- `PreloadCutsceneAction` uses the name-keyed v5 layout in
  `codecs/levelscript/action_map_layouts.json`, including the inserted option
  controls. `current_action_sequence.py` requires matching selected-build,
  catalog, reviewed and serialized member counts before reading that order;
  its option-operation enum has an ordinary signed Int32 declaration and a
  typed parent Param read. This is stored configuration, not observed preload
  or option execution.
- Track-camera's selected parent read/store component is authenticated by
  `levelscript_track_camera_native.py`, including the inserted custom name,
  target-type argument positions and the move-state enum's `CustomPrefab`.
  The move-state Param has its own signed-Int32 and pooled-path proof.
  `levelscript_camera_target_param_native.py` independently authenticates the
  target-type Param's initialized buffered source, typed owned stores,
  allocation/getter paths and bitmap-marking branches. The constant is an
  observed raw Int32 read; its width is not inferred from enum backing alone.
  Pointer/counter widths and atomic retry edges remain checked. The native
  gate precedes even a null marker, and decoding requires the matching pool.
  Cold initialization/refill and live provider selection remain separate.
  EntityPtr arrays retain their independent child gate. Parent contracts and
  removed historical cursor spans do not establish current owner closure.
- The current EnvTalk reader authenticates each of the three concrete
  four-member `Param<List<EnvTalkStruct>>` families independently: a
  nullable list, two Int32 bindings and a pooled path. Each positive
  two-member value stores a pooled string index then Int32 odds; FF supplies
  the managed default null ID and zero odds. The native sixteen-byte hidden
  result and array stride are not the wire width. Generated source, owned
  factories/setters, typed list contexts, capacity/Add/store programs,
  adapter, wrapper forwarder and GetValue conversion are tied to the selected
  build (`conditional`: coherent initialized generated contexts, normal
  helpers, valid typed allocation/storage). Effective provider/default
  selection, runtime inflation and EnvTalk execution/scheduling remain
  unresolved; outer actions and physical owner EOF retain separate gates.
- A path/ID-sourced Param's constant slot is a placeholder: often
  `BoolCompare`'s first operand, and every reached `EventArgsAssignFloat`
  `EventArgsPtr`.
- The current PlayFmvAction parent has an independent generated-reader gate.
  Typed movie-path projection retains the complete selected pooled string Param
  range and carries no native video mapping identity. CommonMaskBlendData has
  a separate current source/Param gate: its positive six-member value preserves
  the raw managed audio extent and padding, admits only a null AnimationCurve,
  then reads two Singles, an Int32 mask enum and normalized Boolean. Nonnull
  curves, including empty arrays, refuse. Factories and static compatible
  formatter joins establish neither live default selection nor mask/playback
  effects. Whole-owner EOF and video resolution remain separate obligations.
- `PlayFmvAction.beforeMask` is `Param<bool>`; names never decide wire types.
  `SendLuaEvent1` reads a seven-member inner value, bypassing its setter.
- Widths vary (`AudioBlackScreenBehaviour` enums byte-backed, most Int32);
  action `Param<GameplayTag>` is a raw int32. The current LevelScriptPtr
  Param preserves its full sixteen-byte constant regardless of ID magnitude;
  its component and remaining ownership boundary are described below.
- `CameraBlendCurveKey` is a value struct containing one string. Its positive
  child is a member header plus one pool index; its managed output holds the
  reference. The current Param codec authenticates its typed value-return ABI,
  source, adapter, wrapper conversion and owned field stores, followed by two
  raw Int32 bindings and a pooled path. FF/default and null Param stay distinct.
  Key-to-curve lookup and evaluation are separate from stored decoding.
- The current LangKey Param serializes only its pooled `key` and bindings.
  Its managed value also carries `rawText`, which is not serialized and can
  survive wrapper reuse. Typed factories, complete source/adapters, owned
  stores and the value-return ABI have independent current gates. This does
  not admit GlobalBuffId, text resolution, live provider selection or owner EOF.
- `Param<List<LangKey>>` has a separate current bounded native gate for null,
  empty and single-element lists. Its initialized typed parent, requested
  capacity, prior-empty Clear, exact managed16 Add/store, provider, matched
  adapter callback and conversion source are proved together with the nominal
  child. Each positive child serializes its member header and pooled key; the
  managed value also contains nonserialized `rawText`, which is omitted from
  the projection. Null Param, null list, empty list and default element remain
  distinct. Counts above one, positive old-size Clear and growth are refused.
  The current open List factory and successful provider paths constrain the
  conditional generated route; live cache contents, inflated contexts, default
  selection, text resolution and enclosing owner execution remain separate.
- `PosRot` stores Euler angles then position as two raw Float32 triples. Its
  positive wire includes a member header; FF yields the zero/default value.
  The pooled `Param<List<PosRot>>` admits bounded null, empty and positive
  lists under its independent current native gate. Typed list contexts,
  requested-capacity construction, Add/store, value conversion and both
  actual provider-helper transfers are authenticated together. The separate
  BlendToCameraTransform parent proves ordered typed fields. Provider joins
  cover initialized coherent contexts and successful Type-cache hits; cold
  paths, cache misses, undersized reused-list growth, effective live provider
  selection and camera execution remain unresolved.
- `OnSquadMemberUspReachMax` has a separate current generated-parent contract
  for `Param<bool>`, `ParamOutput<EntityPtr>` and `ParamOutput<float>`.
  Each child retains its own current gate. Output wrappers serialize
  `paramTarget` and pooled `path`, without a generic output value. These current
  parent and child gates replace the old standalone inline-string decoder;
  stored destinations do not establish live delivered output values.
- Typed route schema v5 admits only metadata-owned inlined Boolean/Int32
  base-field stores whose complete transfer is rederived from the selected
  reader. It records the actual store instead of inventing a setter CALL.
  Earlier schemas and unsupported transfers refuse that claim. Parent field
  additions require a new reviewed layout; no child or runtime behavior is
  inferred from a matching field name or width.
  `il2cpp/formatter_composition.py` shares the registration, interface,
  constructor context, generic-context and usage-cell authentication across
  EnvTalk, camera poses, squad-USP and module readers. Each domain retains its
  own reviewed type identities, native ABI witnesses and field grammar.
  `il2cpp/rgctx_symbols.py` rederives referenced type/method names, nested
  instantiations and reciprocal VAR/MVAR owners. Every declared symbol and the
  complete slot sequence must match; unchanged entry bytes alone do not
  authenticate copied symbolic annotations. Runtime substitution is excluded.
  Constructor pairs or matching declarations alone remain insufficient.
  Each generated-route composition retains its stated initialized, matching
  typed-context and helper conditions. Static registration or a factory mapping
  does not prove effective provider/default/cache selection. Executed source
  cursors and whole-owner EOF remain separate obligations.

- `codecs/levelscript/modules.py` retains older module grammars, including
  `RollingStoneControllerData` and `RunePuzzleData`. Their module-structures
  contract does not authenticate the selected current build; positive bodies
  need current member, field, string and child proofs before reuse. Independently
  admitted null branches do not establish positive module contents.
  `EncounterData.OperaSegment` has no maintained reader: the encounter module
  codec refuses a non-null intro opera-segment array.

- The removed live LevelScript provider probe supplied no admitted observation
  and is unnecessary for the statically proved default stored grammar. Runtime
  provider selection remains unresolved: a useful witness would bind copied
  source bytes, the actual MethodInfo, returned formatter, typed class/context
  identity, child entry/registers and before/after cursor in one admitted source
  scope. Snapshot pointer offsets alone establish no typed slot or inflated
  companion identity; scene/name associations do not authenticate copied bytes.
  This gap cannot promote gameplay execution, other contexts' cache behavior,
  or whole-owner EOF.

## BuffData

Installed-build status: the current client stores every BuffData string,
including root `id` and icon `spritePath`, as a signed StringPool index read
through the pooled `BeyondReadString` helper, and BuffIconConfig gained a
twentieth member (`showProgressInEnemyHeadBar`). Re-derived on the installed
build: the root table (`buff_root_regenerate.py`), BuffIconConfig, the pooled
BlackboardDouble child (`buff_blackboard_double_native.py`, validator
re-derives and compares), addingCooldown, dispelConfig, the empty-timeline
suffix and the structural `buff_actions.Reader` (pooled `byte_payload`; drifted
EffectAction/SelfRotate/RecoverDashEnergy/CheckSkillType layouts). Still
prior-build: attributeModifier, stacking, datapair, globalModifier, event maps,
damage receipts and formatter windows, plus Reader layouts for
SpawnAbilityEntity, LaunchProjectile and MoveTo; the family gate therefore
still refuses. Re-pinning hex windows is stopped: the name-derived
`derived_values`/`wrapper_body_audit` line re-proves counts and write order
on each build without pins, so remaining Buff gates should move to that line
(read kinds via claims-style proofs) rather than new window hashes.

Frontier 9's direction-angle actions read the one-byte `clampToXZ` at member 4; `buff_residual_actions.py` owns the stored framing, while historical source cursors still need a current-byte rejoin.

The 30-member root readers (`memorypack/buff.py`, `buff_actions.py`,
`buff_residual_actions.py`, `buff_icon_config.py`, and the top-level
`buff_frontiers_native.py`) give every file a named outer frame, but `memorypack/buff_named_schema.py`
keeps nested action, positive `stackEffects` and timeline bodies opaque. A
whole schema needs a forward receipt from byte 0 through all 30 fields, `id`
equal to the source stem and physical EOF: `buff_root_no_positive`
(null/empty recursive lists, shared DataPair/AttributeModifier children,
reviewed GlobalModifier branches, and positive-damage roots whose
conditions and processors each have a selected receipt) or
`buff_create_action_root_receipt` (a sole `CreateBuffAction`); JsonData
replays it. The complete Buff family gate admits the selected gradual
positive-damage root at physical EOF through a four-action condition:
CheckDamageDecorateMask, SaveBuffStackNumAdvanced, ModifyDynamicBlackboard,
and SimpleCalcBBAction, followed by the selected damage-scale processor.
The two new action readers authenticate their member order and typed nested
contexts; the selected finder, target and BlackboardDouble children tile
their original source spans. The targeted audit joins the prior complete
BuffData report's native receipts to freshly validated gradual native inputs
on the same build and rereads only that source. This proves stored structure,
not live buff or damage behavior. Child receipts name direct members only; strings, flags
and value bits stay raw. Tag meanings are local to the Buff dispatcher.
The current complete BuffData report also carries a selected positive-damage
root with two `CheckTwoDirectionAngle` conditions and ordered damage processor
tags `[5, 6]`. Its reviewed condition, nested target, processor, root,
source-ID and EOF receipts compose to all 30 named fields in that one source.
The selected sword positive-damage root has a different recursive condition.
Its source-bound composition below also closes stored structure; neither root
proves live damage behavior.
For that one sword source, the selected condition now has source-bound receipts
for its first CheckDamageTypeMask and FindTarget actions and the following
CheckEntityNum action. The first two compose the existing mask reader with the
already validated Buff FindTarget formatter/dispatcher audit, rather than
borrowing native authority from the SkillData timeline parser. The
CheckEntityNum receipt independently matches the audited formatter and its
TargetSettings generic context to the current generated direct-member plan;
the original source closes both the action and its `checkTarget` child at their
selected endpoints. Its stored `targetGroupKey` and `storeKey` are file values,
not observed target or damage behavior. The original direct-child receipt
keeps its TargetSettings direction and selector interiors structural. The
independent `memorypack/buff_damage_check_entity_num_target_children.py`
now reparses that owned target through the existing TargetSettings,
DirectionSettings and SelectorData native gates. Its reached direction has
null nested source/target objects; its selector has a null finder and empty
subtype lists. Those branches close the selected stored target recursively;
positive interiors remain refused. The shared child owners expose
source-hash-checked bounded value readers for this composition. Its receipt
is selected-only and nonpublishable. The recursive condition and selected
root compositions below consume it through its owning reader; neither the
complete family gate nor the registry admits this isolated child directly.
The next IfElse action also closes
on this source: independently native-gated CompareFloat and
ModifyDynamicBlackboard children rejoin the selected eight-member IfElse
wrapper, whose fail sequence stores zero actions. The nested scalar, target
and blackboard interiors retain their structural tier in that storage receipt;
no branch decision was observed. The independent
`memorypack/buff_compare_float_blackboard_children.py` now joins both
CompareFloat operands to the exact BlackboardDouble child grammar in
`buff_adding_cooldown.py`. The parent validator rechecks each recorded
MethodSpec and type argument; the child gate authenticates its own reader and
generated setter order. Each original operand endpoint closes with named
`blackboardKey`, `useBlackboardKey` and `value` spans, retaining raw bytes.
This is a reusable stored-child proof, not a condition result or family
promotion. The independent selected condition composition below joins these
operands and target/selector children. The two later top-level ModifyDynamicBlackboard actions also close
under the existing native reader. A selected storage receipt now tiles all six
top-level actions and both terminal bytes through the condition endpoint.
That earlier storage receipt remains nonrecursive: its structural nested interiors
prevent whole-condition schema and whole-BuffData promotion even though the
stored condition span is exact. The reviewed gates and source selection are in
`buff_damage_sword_condition_prefix_native.json` and
`buff_damage_check_entity_num_child_native.json` and
`buff_damage_sword_if_else_child_native.json` and
`buff_damage_sword_condition_storage_native.json`; their readers consume only
the selected logical bytes and existing validated native contracts or audit rows.
The independent `memorypack/buff_damage_sword_condition_receipt.py` now
composes those action and child owners, the nested IfElse sequences and the
outer sequence terminals into a recursive selected stored-condition receipt.
The ModifyDynamicBlackboard parent rechecks both direct MethodSpec rows,
generic argument bytes and resolved child types before this composition. The
receipt marks `wholeConditionStoredSchemaExact`, while condition truth,
branch results and effects remain unobserved. It stays a nonpublishable child
diagnostic. The selected sword modifier below deliberately joins this child
to independently proved processor and enum reads before the sole root reader
can check all thirty fields, source-ID equality and physical EOF.
Four source-bound Buff roots have complete stored-schema compositions:

- The claymore upgrade's positive `healModifier` joins its native-audited
  `CheckHealTag` condition, four inherited members, `query` setter and two named
  `GameplayTagQuery` children to the parent heal modifier's three direct members.
  The tag-zero processor names `modifier` and `modifyTargetSide`; its nested
  attribute modifier names four members, with native-gated BlackboardDouble
  `param`. Reviewed selections: `buff_heal_check_tag_selected_native.json` and
  `buff_heal_processor_zero_native.json`.
- The selected BreakPassingSmallSceneObject source's `buffEventAction` contains
  one map and one SequenceActionData. The residual frontier proves the action's
  four inherited members; reviewed root-sixth and Sequence readers establish
  actions-before-event order and the two terminal booleans. The source selection
  is in `buff_break_passing_selected_native.json`.
- The selected empty-condition/tag-ten source first proves its positive root
  `attributeModifier`, including one named AttributeModifier and its converted
  attribute terminal. Its damage modifier then joins an empty SequenceActionData
  condition and one ModifyCalcResult processor with two native-gated
  BlackboardDouble children. The earlier attribute proof is required even though
  the cached blocker list names only damage. Reviewed selection:
  `buff_empty_condition_tag_ten_selected_native.json`.
- The selected sword damage source joins its recursive stored condition,
  one tag-five processor and stored `enableSide`. The parent condition,
  processor-list and enum MethodSpec arguments match the actual named setters
  and destination-field types. Reviewed selection:
  `buff_damage_sword_selected_native.json`. The JSON-safe condition certificate
  is checked against a regenerated private reader context on the selected
  native paths; it never serializes or trusts a cached parser object. The
  existing root reader then traverses every remaining field and physical EOF.

These selected fixtures no longer define the reach of shared root children.
`memorypack/buff_event_maps.py` owns the two event-map grammars: an
AbilityActionMap reads its event before its sequence list, while a BuffActionMap
reads the sequence list before its event. Their shared SequenceActionData child
uses the independently proved positive-sequence reader. The recursive action
owner composes reviewed CreateBuffAction and EffectAction children, including
bounded input and sibling-action lists; unsupported nested unions still refuse
the whole composition. This is a reusable root route, not an extension of a
selected filename's authority. Its complete root receipt must traverse all
thirty fields, match the source ID and reach physical EOF before either corpus
gate can admit it.

The complete family sweep now admits the shared event-map composition and
AttributeModifier root compositions beyond the earlier selected fixtures.
Older corpus receipts that predate those shared readers understate their
coverage. Use the current authenticated per-file root receipts and canonical
registry to select residual work; do not repeat already passing source probes
unless a related child, parent, contract or source finding requires it.

DamageAction's supported DamageUnit and calculation children compose through [the named reader](../../scripts/game_data/memorypack/buff_damage_action.py); unproved variants still refuse the root.
AuraAction and HealAction compose independently typed input, filter, shape and tag children through [their named reader](../../scripts/game_data/memorypack/buff_aura_heal_actions.py); unsupported recursive children still refuse the root.
CheckSkillType, CheckObtainAtbType, CheckBuffStackNum and InterruptAction compose independently typed lists, BuffId values, blackboards and targets through [their named reader](../../scripts/game_data/memorypack/buff_skill_stack_interrupt_actions.py). CheckObtainAtbType retains separate `checkObtainMethod` and `checkObtainType` flags and separate nullable lists of GainAtbMethod and GainAtbType. Named formatter-to-setter transfers, closed list element types and independent four-byte source witnesses establish storage. Null, empty and populated lists remain distinct; stored flags and enum bits do not establish the evaluated ATB event or condition result.

The same domain owns SetSkillCdAtOnce and SwitchModeAction. The cooldown
record retains its function, percentage flag, skill ID, type mask, target,
type-selection flag and BlackboardDouble operand independently. The mode
record retains its mode ID and independent start/end interruption and reset
flags. Reviewed source calls and runtime destinations prove this order;
the target and scalar children must close on their original spans. Storage
does not establish cooldown arithmetic, the selected skill, mode transition
or interrupt/reset execution.

[`animation_curve.py`](../../scripts/game_data/memorypack/animation_curve.py)
owns the shared named AnimationCurve value reader, independently of any
action that first exposed it. Its
[`native contract`](../../scripts/game_data/contracts/memorypack_animation_curve_native.json)
joins two source DWORDs to separately named pre/post wrap-mode resolution
caches. A closed Keyframe array allocation, index-times-stride instruction,
source loads, cursor accounting and actual typed array-field stores name
each keyframe's time, value, in/out tangents, weighted mode and in/out
weights. Native structure size corroborates those copies; it does not by
itself prove the wire grammar. Original floating-point and enum bits remain
intact. A null curve, null key array, empty key array and populated key
array retain distinct receipts. Each parent must independently prove its
typed curve field and original bounded span. Callback-name bindings do not
establish callback execution, evaluated interpolation or game effects.

[`buff_curve_actions.py`](../../scripts/game_data/memorypack/buff_curve_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_curve_actions_native.json)
compose TimeDilationAction and EnemyHurtAnimAction. Time dilation retains
independent effect/ignore target lists, BlackboardDouble duration and skill
cooldown operand, layer, slot/priority tags, curve and curve-key flags.
Enemy hurt retains separate attacker/defender, distance curve, direction,
BlackboardImpactValue and pushback/transition/immobilization providers,
alongside its stored animation, shake and scale flags. Every nested value
must independently close on its original span; positive direction targets
without recursive evidence still refuse this parent. The shared impact
reader now exposes a source-bound provider value without reusing a
SetSuperArmorAction parent receipt as authority for another action. Stored
names establish neither the selected live targets nor time scaling,
cooldown changes, hurt animation, displacement or armor effects. Complete
root and canonical registry gates still govern coverage admission.

The same curve owner separately joins HitStopAction's source order and
destinations. `attacker` and `target` are independent TargetSettings children;
`directCurve` has its own AnimationCurve receipt, while `curveKey` retains
nullable raw bytes. The plain floating-point duration, affect type, curve
selection flag and GameplayTag priority retain their original bits. The tag's
closed unmanaged source entry, actual DWORD read, cursor advance and returned
value must agree; a four-byte native type size is insufficient. Stored curve
choices do not establish which curve reaches StartHitStop or its evaluated
duration and affected entities.

The curve owner also independently joins CharHurtAnimAction's own source
order and destinations. Its attacker and defender targets, distance curve,
DirectionSettings and BlackboardDouble push-back operand retain separate
original-span receipts. Raw animation enum, armor limit and custom flags
remain uninterpreted. A direction profile closes here only when its nested
targets are independently exact nulls; a positive nested target leaves the
parent open. Stored curve, direction and distance values do not establish
hurt animation, facing, displacement or selected entities.

[`buff_marker_mask_actions.py`](../../scripts/game_data/memorypack/buff_marker_mask_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_marker_mask_actions_native.json)
compose CreateTimedMarker, CheckTagMatch, CheckObjectTypeMatch and
CheckPhysicalInflictionType and CheckSpellInflictionType. The marker retains independent duration,
BlackboardString ID, target and finish/time-dilation flags. The conditions
retain independent target/query, object-type mask, or physical-infliction
mask and nullable stored key. Every provider, target and query requires its
same-build child receipt on the original span. Raw enum, flag and payload
bits stay intact; storage does not establish marker registration, expiration,
selected entities, mask/query evaluation or predicate results.

CheckSpellInflictionType independently owns its stored enum mask and
nullable raw saved-key payload. The source's payload-kind spelling remains
part of the reviewed read order. A key name or mask does not establish the
state queried, bit-test result or condition outcome.

CheckTagMatch's query illustrates a second source-transfer shape. The typed
ReadValue context passes a hidden stack output pointer and the reader; only
after that call does an instance getter supply the runtime destination.
The complete intervening program reloads that same stack value and copies
its full runtime extent into the independently named field. The explicit
`providerOutputSource` check authenticates argument order, getter identity
and return type, runtime value extent, contiguous stack transfer and field
copy. This value contains a managed reference: the runtime copy extent is
not a raw wire length, and the independent GameplayTagQuery reader still
owns its serialized grammar. A nearest-call scan would mistake the getter
for the source. This proof does not equate the optimized target with a
distinct registered generic entry or establish live provider selection.

GameplayTag adds an object-identity boundary to named field recovery. It is
a value type stored inline in a generated class wrapper. Its actual reader
receives the wrapper by reference, aliases that argument, dereferences it and
preserves the resulting receiver through the scalar store. The
[`Aura/Heal child contract`](../../scripts/game_data/contracts/buff_aura_heal_actions_native.json)
records this complete normal program. `named_native_records` authenticates
the reader's two reference parameters, instance-field declaration and native
offset, then projects each boxed member offset into the wrapper's inline
value. Equal numerical offsets on the boxed type and wrapper are insufficient
without that receiver proof. The generated tag element retains its member
header; a nullable list of these elements is distinct from both a
GameplayTagList object and an unframed DWORD array.

[`buff_tag_sequence_actions.py`](../../scripts/game_data/memorypack/buff_tag_sequence_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_tag_sequence_actions_native.json)
compose AddTagAction's BlackboardString, target and direct GameplayTag list,
and ForEachAction's SequenceActionData and target. Parent fields independently
prove their closed source types before using the shared children.
[`buff_sequence.py`](../../scripts/game_data/memorypack/buff_sequence.py)
owns the common sequence proof and recursive value reader below event maps
and action parents. Its declaration remains once in the shared-event
contract. Every positive action must close on its own original span; null
wrappers, null/empty action arrays and null elements stay distinct. The two
terminal flag bytes remain stored values, without inferring iteration order,
guard selection, tag attachment or action execution.

[`buff_spawn_entity_action.py`](../../scripts/game_data/memorypack/buff_spawn_entity_action.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_spawn_entity_action_native.json)
compose SpawnAbilityEntity's complete named parent with independently proved
targets, direction targets, Blackboard duration, assignment elements and
nullable string lists. Its Vector3 field uses an actual typed unmanaged
return-buffer call before an independently identified wrapper getter.
[`struct_output_sources.py`](../../scripts/game_data/memorypack/struct_output_sources.py)
proves the direct reader and distinct registered reader separately: both
copy eight plus four source bytes and account for twelve consumed bytes.
The complete caller transfer reloads that same temporary and authenticates
both runtime stores. Quaternion instead copies sixteen bytes inline from
the parent reader, updates its stored cursor slots and copies the same
temporary into the complete destination field. Both paths require an
authenticated normal prefix preserving the reader and wrapper-reference
argument aliases. Runtime extent alone proves neither wire read. Stored
names and flags do not establish evaluated strings, entity creation,
ownership, navigation selection, rotation evaluation or lifetime; native
short-segment/provider selection remains outside these normal-path proofs.

[`buff_launch_projectile_action.py`](../../scripts/game_data/memorypack/buff_launch_projectile_action.py)
and its [named contract](../../scripts/game_data/contracts/buff_launch_projectile_action_native.json)
compose LaunchProjectile's complete stored parent with four independently
proved inline Vector3 transfers. Each source/cursor/temporary/destination
program owns its register profile, reader-argument restoration and complete
field stores; a nearby call or runtime extent cannot substitute for it.
PresetPointDef's target and nullable key have their own named read order,
while assignment elements use the independent AssignPair owner. Null wrappers,
null/empty lists and null elements remain distinct, and mandatory later
fields still have to close. Vector and scalar bits remain raw. This storage
proof does not establish emitted entities, trajectories, preset selection,
weapon calculations or projectile delivery.

[`buff_camera_impulse_action.py`](../../scripts/game_data/memorypack/buff_camera_impulse_action.py)
and its [named contract](../../scripts/game_data/contracts/buff_camera_impulse_action_native.json)
compose CameraImpulseAction, its ImpulseDefinitionData and the inline
EnvelopeDefinition wrapper, with independently typed AnimationCurve and
TargetSettings children. The parent's Vector3 is an inline eight-plus-four
source copy: its complete cursor program advances twelve, reloads the same
stack temporary and preserved remaining word, and writes both destination
parts. It does not use SpawnAbilityEntity's unmanaged return-buffer route.
The envelope instead arrives through a typed ReadValue result buffer. The
selected helper zeroes and forwards a thirty-two-byte output to provider
dispatch, then returns that buffer; the parent copies both sixteen-byte
halves into its independently named runtime field. Runtime output extent
does not establish serialized wire width or live formatter selection.
[`value_wrapper_sources.py`](../../scripts/game_data/memorypack/value_wrapper_sources.py)
independently projects each envelope member from the exact wrapper-reference
argument and actual inline instance field. Its complete normal program
preserves the incoming reader, requires the curve type context to reach the
source argument, and follows each returned reference, float or byte to its
named destination. Boxed field-offset coincidence, a partial store, a
clobbered alias or an unrecognized instruction cannot supply that proof.
Null stored wrappers remain distinct from evaluated runtime values. Curves,
flags, mount points and signal paths establish stored configuration; curve
evaluation, signal resolution, impulse creation, camera ownership and screen
motion remain open. Complete Buff admission still requires the family gate
and canonical original-byte root replay.

[`buff_leaf_actions.py`](../../scripts/game_data/memorypack/buff_leaf_actions.py)
and its [named contract](../../scripts/game_data/contracts/buff_leaf_actions_native.json)
separately admit NotNextCheckAction's four inherited action fields in recursive
sequences. The selected source reader and generated setter order contain no
fifth stored member or recursive child; this reusable action receipt removes
the earlier restriction to one specific damage-condition pair. The union uses
its proved extended encoding, including null wrappers. A plain reserved lead
byte, wrong member count, truncated scalar or trailing bytes cannot close the
action. Raw enable, priority and server-index bits establish storage. They do
not establish a no-op, a returned condition result, next-check suppression,
sequence ordering or gameplay execution.

The same nonrecursive reader and its versioned contract also name
PauseBuffTime's inherited prefix plus `isPaused`, and
OnSpellAbnormalStartFinish's inherited prefix plus `abnormalType` and
`isStart`. The latter's serialized member order differs from its runtime
field placement; generated setters, actual source calls and selected runtime
fields must be joined independently. Only byte and scalar suffixes belong to
this reader. Raw values and exact null-wrapper states do not establish pause
transitions, abnormal-event delivery or evaluated enum meaning.

RefreshBuffAttrModifierValue independently uses the same inherited-only leaf
shape and its own extended union tag. Its stored fields do not establish a
no-op or an attribute update; the named consumer is a separate obligation.

CheckDamageType now uses this same maintained leaf owner with a separately
reviewed current reader and dispatcher identity in the
[named contract](../../scripts/game_data/contracts/buff_leaf_actions_native.json),
backed by its [source windows](../../scripts/game_data/contracts/buff_5d_native.json).
Its inherited byte and three DWORDs are followed by one raw `DamageType`
DWORD. Both enum source contexts and every generated setter are joined to
their ordered source calls. Unknown enum bit patterns remain valid stored
bits; they are not normalized to a guessed runtime enum.
Original action spans independently match the structural reader and the
recursive named reader, preserving all field bytes and refusing truncation
or a borrowed trailing byte. This child integration still requires a fresh
complete family gate and original whole-root replay before increasing root
admission. Damage-event ownership, evaluated condition results and runtime
branch effects remain unresolved.

[`buff_keyword_actions.py`](../../scripts/game_data/memorypack/buff_keyword_actions.py)
and its [contract](../../scripts/game_data/contracts/buff_keyword_actions_native.json)
join VulnerableAction, ShelterAction, SlowAction, SpeedupAction, WeakAction,
EnhancedAction and SpellInflictionOnChar to their independent source orders
and actual destinations. The keyword parents separately prove their common
fields; the subtype parents retain an additional required enum word. The
minimum list suffix is derived from each proved subsequent storage field,
rather than borrowing the subtype parent's larger tail. VulnerableAction retains inherited keyword
fields, BlackboardString child ID, separate duration/rate providers, two
targets and subtype. Its KeywordEnhanceEdit elements separately own `buffIds`,
`operationType` and `value`. Nullable raw string lists, null edit wrappers,
null/empty outer lists and positive elements remain distinct; the parent's
required suffix still follows the list. SpellInflictionOnChar retains plain
count/type/immune-level values, a nullable stored blackboard key, separate
source/target and raw flags. Every provider and target receipt must close its
own original range. These grammars do not calculate keyword edits, choose a
count source, consume/add a live Buff or deliver an infliction event.

SpellInfliction has a separate stored parent from SpellInflictionOnChar.
Its energy-shard enum and raw extra flag precede independent source and
target profiles. Each target still requires its own same-build receipt on
its original extent. The shorter stored layout does not borrow the other
action's counts, immunity or trigger fields, and does not establish actual
infliction or the selected entities.

The [data-transfer owner](../../scripts/game_data/memorypack/buff_data_transfer_actions.py)
separately names GetAITransDataAction's `aiTransKey` and `saveTo` payloads.
Null and empty keys remain distinct, arbitrary payload bytes are preserved,
and the second signed length remains mandatory. The grammar does not prove
an AI transfer lookup, its returned value or a Blackboard save.

[`buff_global_creation_action.py`](../../scripts/game_data/memorypack/buff_global_creation_action.py)
and its [contract](../../scripts/game_data/contracts/buff_global_creation_action_native.json)
name CreateGlobalBuffAction's count, creation-finish flag, GlobalBuffInput
list and independent source target. Each GlobalBuffInput independently
names its assignment flag, AssignPair list and GlobalBuffId. The selected
inline-value proof follows the reader argument, wrapper reference and
address of GlobalBuffId's own `id` field through the complete string return
and reference store. Its in-memory reference extent does not change its
length-prefixed serialized bytes. Null wrapper, null string, empty string
and null/empty list remain distinct; evaluated counts, assignment execution
and actual global Buff creation or finish require consumer evidence.

[`buff_switch_action.py`](../../scripts/game_data/memorypack/buff_switch_action.py)
and its [contract](../../scripts/game_data/contracts/buff_switch_action_native.json)
separately name SwitchAction's `alwaysNext`, BlackboardDouble `choice` and
nullable Option list. Each Option owns `actionData` as SequenceActionData
and `value` as BlackboardDouble. Every reached sequence must recursively
prove its original action ranges; unsupported actions and excessive nesting
refuse the parent. The grammar does not evaluate choice or select an Option.

The [skill/stack owner](../../scripts/game_data/memorypack/buff_skill_stack_interrupt_actions.py)
separately names SetBuffDurationAction's BuffFindSettings, early-finish flag,
operation enum, target and BlackboardDouble value. BuffFindSettings and its
tag query use their independently authenticated child reader. The enum's
declaring type is ModifyDynamicBlackboard's OperationType; this remains a
SetBuffDurationAction record. Stored operands do not determine lifetime
arithmetic, selected Buff handles or accepted writes.

[`buff_ignite_text_action.py`](../../scripts/game_data/memorypack/buff_ignite_text_action.py)
and its [contract](../../scripts/game_data/contracts/buff_ignite_text_action_native.json)
own IgniteBuffTextAction's complete stored parent, including its raw
Vector2 offset, flags, enums, independent TargetSettings and final nullable
text payload. Its eight-byte source proof is separate from the DWORD
unmanaged reader and from a runtime-size inference. The actual helper reads
two Float32 words, advances eight bytes and packs their unchanged bits into
RAX. The selected generic registration independently proves a second entry
and its cursor helper. The parent forwards the full RAX value as RDX to its
own wrapper setter; that setter saves the argument, obtains the typed Data
reference and writes both words at the independently selected field offset.
The getter's normal program returns its own typed `__realInstance`, after
its reference checks. Full instruction boundaries, current windows, argument
aliases, closed type, cursor fields, word order and both destination stores
are separate gates. A raw eight-byte member without this explicit proof
fails closed. These are selected normal-path byte and ownership proofs;
slow/error behavior stays within the source formatter's existing boundary.
They do not establish evaluated offsets, energy effects, displayed text,
live provider selection or action execution.

The [marker/condition contract](../../scripts/game_data/contracts/buff_marker_mask_actions_native.json)
separately names CheckTargetsEqual's two TargetSettings source children.
Both must close on their own original ranges; matching bytes or a successful
receipt for the other target cannot stand in for that child. The
[skill/stack/interrupt contract](../../scripts/game_data/contracts/buff_skill_stack_interrupt_actions_native.json)
independently names InterruptCurSkillAction's single `skillOwner` target.
It also separately names RecoverLockOnEndIfNoLockAction's target after the
common AbilityActionData fields. That stored target, its null state and
original span do not prove lock-on recovery or a selected entity.
That family's reader now checks original child extents for targets, BuffId
values, blackboard operands and counted scalar lists, alongside current native
dependencies. The source window's null wrapper is separate from a non-null
wrapper with null target children; neither accepts a trailing byte.

[`buff_super_armor_condition.py`](../../scripts/game_data/memorypack/buff_super_armor_condition.py)
owns CheckSuperArmor's named target, comparison and BlackboardDouble operand.
Its independently typed child joins establish stored comparison inputs,
not a live entity's armor value or the evaluated predicate.

[`buff_debug_print_action.py`](../../scripts/game_data/memorypack/buff_debug_print_action.py)
owns DebugPrintAction's nullable `bbKey` and `identifier`, inline `color`,
`logType` and independent target. Color has no nested source MethodSpec in
this reader: the parent copies sixteen source bytes to a stack temporary,
explicitly advances sixteen, then copies that same temporary into the
runtime field. The named contract independently authenticates the source
pointer load, both complete copies, cursor helper, exact intervening bytes
and field destination. `named_native_records` admits this only through an
explicit `inlineSource` proof and selected unmanaged extent; it does not
waive the typed-context requirement for arbitrary object fields. Raw color
bits, stored strings and enum values do not establish rendered color or log
output. Short-segment/refill parity remains outside the normal-path proof.

[`buff_selector_distance_validator.py`](../../scripts/game_data/memorypack/buff_selector_distance_validator.py) owns the selector's DistanceValidator child. Its named contract proves the selected union branch and the stored `clampToXZ`, `compareType` and BlackboardDouble `value` fields. The shared selector-list reader composes that child on the original span, including a null wrapper; the scalar provider must have an independently exact boundary. This establishes stored distance operands. Live entity positions, projection, provider evaluation and predicate results remain unresolved. Whole Buff coverage still requires the root reader's contiguous thirty-field receipt and physical EOF, followed by the complete-family and canonical JsonData gates.

CheckHp and CheckPoiseValue compose through
[`buff_vitals_actions.py`](../../scripts/game_data/memorypack/buff_vitals_actions.py).
The selected-condition contract still owns their named parent fields; the shared
reader removes the former single-action restriction and independently closes
each target and BlackboardDouble on the original span. A condition's stored
comparison operands do not establish which live entity or value it evaluates.

ReadSkillSettingData and SendBattleSignalToLevel compose through
[`buff_data_transfer_actions.py`](../../scripts/game_data/memorypack/buff_data_transfer_actions.py)
and its reviewed native contract. ReadData keeps `column`, `dataKey`,
`enhanceAttributeSource` and `storeKey` separate. Its nullable list, null elements,
targets and blackboards have independent boundaries; absent and empty lists
are distinct. The signal's `doubleValue` and `signalId` also have distinct typed
children. Formatter-to-setter transfers prove stored fields, rather than field
names alone proving wire order. Key payloads retain their original bytes while
encoding is unresolved. Live skill lookup, output-key writes, signal delivery
and ownership remain separate consumer joins.

The same data-transfer domain also owns GetTargetBuffBBAdvanced and
StoreAttributeValue. The former keeps its output `blackboardKey`, requested
`desiredKey`, Buff finder and target in separate original-byte spans. The latter
keeps `baseValue`, `divisorValue` and `multiplierValue` as independent providers,
alongside the attribute selectors, output key, target and `useFloor`. These
stored names do not establish live arithmetic or the value written.
It also owns SaveBuffStackNumAdvanced and SimpleCalcBBAction. SaveBuffStackNumAdvanced
keeps its Buff finder, `buffStackNumType`, checked target, output `key` and
`limitSkillCastId` flag in independently proved spans. SimpleCalcBBAction keeps
its output key, operation and two BlackboardDouble operands separate. The
selected native readers prove those source reads and destinations; the finder,
target and provider children must independently close on the original bytes.
Stored selectors and operands do not establish the selected Buff, live stack
count, calculation result or blackboard assignment.

[`buff_timed_marker_condition.py`](../../scripts/game_data/memorypack/buff_timed_marker_condition.py)
owns CheckTimedMarkerCondition's named stored parent. Its marker `id` and
`blackboardKey` remain separate nullable byte payloads; `checkTarget` has its
own exact typed child, and `returnTrueIfNotExists` and `useBlackboardKey` retain
their stored flag bits. Source-to-setter transfers establish the parent layout.
They do not establish marker existence, evaluated key selection or predicate
results. Unsupported target children still refuse the parent composition.

[`buff_probability_action.py`](../../scripts/game_data/memorypack/buff_probability_action.py)
owns Conditions.Probablity, retaining the client's spelling. Its probability
provider has its own exact child boundary; stored probability is distinct from
the evaluated input, random source and decision.

[`buff_entity_count_action.py`](../../scripts/game_data/memorypack/buff_entity_count_action.py)
owns the general shared-event CheckEntityNum parent, separate from the earlier
source-bound positive-damage receipt. Its reviewed contract proves all ten
source reads and their actual runtime-field destinations. `minNum` is a plain
stored integer; `checkTarget` is a separately typed TargetSettings child.
The comparison and two flags retain their raw values, and `storeKey` retains
nullable bytes. Null targets close directly; positive targets compose their
direction, selector and finder children on the original span. Stored structure
does not establish selected entities, counted entities, the comparison result
or a blackboard write.

[`buff_notify_char_passive_ui_action.py`](../../scripts/game_data/memorypack/buff_notify_char_passive_ui_action.py)
owns NotifyCharPassiveUIAction's six stored fields. Its own native contract
proves the source reads, actual destinations and closed TargetSettings and
BlackboardDouble types. Both children must close on their original byte spans;
null targets and null providers remain distinct. This proves stored `target`
and `value`, without establishing live target selection, evaluated values,
notification delivery or the visible passive indicator.

[`buff_action_consumers_native.py`](../../scripts/game_data/buff_action_consumers_native.py)
re-proves narrow method-call claims from
[`buff_action_consumers_native.json`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
on the selected build. CheckHp and CheckPoiseValue contain target-selection and
blackboard-evaluation calls; CheckPoiseValue also calls `get_hasPoise`.
ReadSkillSettingData contains attribute lookup and dynamic blackboard assignment.
SendBattleSignalToLevel contains event allocation, sender/parameter assignment
and level-event raising. These are direct static call observations, conditional
on execution reaching those compiled paths. They do not join individual stored
fields to call arguments or establish IFix selection, values, delivery or mission
ownership. A failed method claim empties its group and marks it `pendingReview`;
native-input drift during evaluation empties all groups. This consumer audit is
independent of the stored-format coverage gates.

The skill-cooldown consumer group proves active-skill lookup, float-provider
evaluation, the cooldown helper and global-event calls. The helper separately
contains current-timer, period/cooldown and remaining-time reads, plus both
remaining-time update sinks. The mode-switch group contains owner lookup and
mode enabling in execution, then base ending and mode-handle disabling in
`OnEnd`. CheckSuperArmor contains target selection and provider evaluation;
its anonymous armor lookup and comparison remain separate unresolved joins.
These claims prove compiled calls, not individual stored field arguments,
selected branches, calculated values, timer changes or restored live modes.

TimeDilationAction has separately re-proved compiled global and entity
start calls, target collection and Blackboard evaluation. Its `OnEnd`
contains a TimeDilationHandle stop call. EnemyHurtAnimAction reaches
first-target and target-list selection, Blackboard evaluation, ordinary
hurt animation, back-swing hurt handling and additive animation sinks.
These consumer groups remain independent of the exact stored parent
receipts. They do not establish which effect/ignore list, curve, operand,
attacker/defender or finish flag supplied a live invocation, nor that
the selected IFix path actually executed or changed time/animation state.
The time-dilation end predicate still lacks its stored `finishByAction`
join: its data pointer passes through closed generic action storage whose
instantiated layout has not been proved for this consumer. Matching a
displacement to the nongeneric Data field does not establish that pointer's
ownership. Keep this separate from the already proved stop-call presence.

CreateTimedMarker's compiled body/helper paths contain target collection,
Blackboard evaluation and `AddTimedMarker`; its end path contains
`TimedMarker.Remove`. CheckTagMatch contains target-view selection,
part-source resolution and `MatchesQuery`. CheckObjectTypeMatch contains
target-view selection and object-type reads. CheckPhysicalInflictionType
contains event-context acquisition and Blackboard reads/assignment. These
claims are re-proved by the same consumer contract. Exact marker operands
and lifetime flags, query/mask argument ownership, target quantifiers,
short-circuit behavior, event variants and evaluated results remain
independent unresolved joins. Call presence does not settle those branches.

AddTagAction's compiled execution paths contain first-target selection,
Blackboard evaluation and Entity.AddTag; its ending contains
MultiTagHandle.RemoveTag. ForEachAction contains target collection/access,
target binding and SequenceAction.ExecuteInstant, with SequenceAction.End
in its ending. SpawnAbilityEntity contains target selection, rotation and
assignment helpers, entity-table lookup, ObjectContainer.SpawnAbilityEntity
and controller initialization; its ending contains entity release, attached
effect pause and target disposal. These independently re-proved calls do not
identify the stored argument values, selected branches, sequence/entity/handle
ownership or actual attachment, execution and cleanup.

CameraImpulseAction's compiled execution contains target collection, node
transform lookup, the camera-shake property and both two-dimensional and
ordinary impulse-start sinks; its ending contains EndImpulse. These named
call claims remain separate from the stored child receipts. Exact impulse
arguments, branch conditions, handle lifetime and camera ownership remain
unresolved.

NotNextCheckAction's `get_executeReturnType` has a narrower proved normal
return in the [consumer claims](../../scripts/game_data/contracts/buff_action_consumers_native.json).
When the selected Boolean IFix guard returns false, it returns the declared
`AlwaysReturnTrue` enum. The
[`constant_returns.py`](../../scripts/game_data/il2cpp/constant_returns.py)
check independently joins the selected method and Int32-backed enum, requires
the actual direct Boolean call and JNE false fallthrough, and proves that the
complete EAX literal survives a contiguous plain epilogue to RET. A literal
load alone, partial return, result clobber, unknown instruction, wrong guard
or branch into the return tail refuses the claim. This property is separate
from ExecuteInternal's result and from the sequence's returned result.
The environment/context getter dispatch, its returned receiver, policy-field
store and later sequence-policy branches still need separate ownership and
flow proofs. The action name does not establish skipped execution or a no-op.

The
[`consumer claims`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
also distinguish receiver-proved reads from an arbitrary field-displacement
match. CheckTagMatch's `checkTarget`, CheckObjectTypeMatch's `objectTypeMask`
and CheckPhysicalInflictionType's `mask` each have a compiled normal-path
read through the incoming instance's closed generic data reference.
[`reference_layouts.py`](../../scripts/game_data/il2cpp/reference_layouts.py)
requires a sole instance reference type parameter, an immediate concrete
witness with no declared instance fields, a fully occupied nongeneric base and exactly one reference
of additional concrete size. Declared fields are counted using their selected
static attributes: static declarations do not occupy the concrete instance,
while any own instance field still refuses this witness. Open generic offsets
and sizes remain excluded.
[`closed_data_fields.py`](../../scripts/game_data/il2cpp/closed_data_fields.py)
then checks body ownership and incoming-instance ABI, follows preserved
receiver/data aliases and joins the read to the actual nongeneric Data field.
Unknown instructions, partial pointer writes, clobbers and wrong owners erase
provenance. This closes selected stored-field reads, without promoting a
later call's argument, mask operation, branch selection or live condition
result. Classes with their own instance fields cannot use the fieldless
witness rule; the time-dilation finish predicate remains a separate layout
and flow gap.

[`cmp_memory_reads.py`](../../scripts/game_data/il2cpp/cmp_memory_reads.py)
also authenticates complete byte/DWORD memory CMP operands against the
selected declared field width, owned data-register base, displacement and
actual opcode bytes. Legacy address/operand prefixes, partial instructions,
unsupported addressing and mismatched text do not qualify. This is a read
claim only: comparison does not supply a value register for reference or byte
argument forwarding, nor does it establish flags or branch selection. Adding
that proof form does not recover candidate fields whose receiver provenance
has already been erased.

The same receiver proof independently reaches CheckTargetsEqual's two target
references and InterruptCurSkillAction's `skillOwner`. PauseBuffTime's
`isPaused` and OnSpellAbnormalStartFinish's `isStart` have complete byte reads
through that owned Data reference. Byte mode authenticates the actual byte
MOV or unsigned-byte MOVZX opcode, complete destination byte, memory base,
displacement and register width; a word read, wrong register/displacement or
partial pointer does not qualify. This preserves the stored byte without
normalizing it or evaluating a condition. OnSpellAbnormalStartFinish's
`abnormalType` ownership remains unproved where unknown instructions interrupt
the pointer chain, even though a later matching displacement is visible.

A small value-type extent alone also does not establish a callee's return
ABI. [Microsoft's x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)
places additional native type requirements on direct aggregate returns.
Selected managed metadata does not by itself prove all those C++ properties.
The reference forwarding mode therefore admits only independently named
reference parameters with direct primitive/reference returns. GetTargetsView's
value-type return still needs an independent entry/register witness before
its stored target field can be certified at the argument position; its call
presence and receiver-proved field read remain separate established claims.

The reference-argument check separately accepts either selected undecorated
String type record, with a complete pointer read and the exact declared
parameter type. Byref, pinned/decorated records and another primitive kind
still refuse forwarding. GetAITransDataAction's owned `aiTransKey` reaches
TryGetAITransData's `key`; its independent `saveTo` reaches
UpdateTargetGroup's `key`. The intervening SetTarget call is a separately
proved compiled sink. This makes `saveTo` a target-group key in this flow;
lookup outcomes, the returned transform/handle, update selection and live
group effects remain unresolved.

An explicitly selected concrete-field suffix provides a second closed
reference layout witness. It requires the same immediate closed generic
parent and sole VAR reference field, and the non-generic base still must
have no trailing padding. Every declared concrete instance field then needs
an independently named scalar or reference extent. Those fields must fill a
continuous suffix beginning immediately after one pointer beyond the base,
with no overlap, internal gap or unproved trailing extent. Static fields
remain separate. Unproved value types, a changed owner, wrong parent, field
count drift or padding fail closed; the original instance-fieldless mode
does not automatically admit this shape. LaunchProjectile's own string
fields satisfy the explicit suffix witness. Its `emitPos`, `projectileId`,
`projectileSource` and `targetSettings` Data reads are then independently
owned; the latter two reach their separately typed selection parameters.
Table lookup, start-position and launch calls remain compiled sinks, with
vector/provider evaluation, spawned objects, skill callbacks and trajectory
or delivery effects unresolved. RecoverLockOnEndIfNoLockAction's declared
ObjectPtr value field does not satisfy this suffix proof. Its execution and
end calls are authenticated without promoting a Data-field or recorded
pointer ownership claim.

Closed generic suffix references require an independent selected reference
class definition, generic owner/arity and complete closed argument identity.
Their argument's representation does not determine the reference width;
ObjectPtr and other generic value types remain excluded. This establishes
the complete concrete suffixes of CreateGlobalBuffAction and SwitchAction.
An explicit closed-generic-reference-field claim can then prove a whole
owned List reference read; generic callee-parameter forwarding stays open.
An explicit normal-forward-jump profile preserves aliases only across exact
local EB/E9 jumps whose byte-derived targets agree with the decoded text and
an instruction boundary in the selected body. Conditional branches keep
the fallthrough choice; external/backward/indirect jumps end this path.
Unknown instructions and partial pointer writes still erase provenance.

An independently selected local-path profile can examine both edges of a
complete local conditional branch. The
[`compiled_paths.py`](../../scripts/game_data/il2cpp/compiled_paths.py)
helper requires contiguous original instruction spans, byte-derived branch
targets and actual in-body instruction boundaries. Paths preserve the same
incoming-instance, named field, ABI and clobber checks; unknown instructions
end that path, loops and enumeration remain bounded, and a refused proof
reports inventory or traversal limits. This establishes a compiled control
flow prefix under unspecified branch outcomes. It does not establish
predicate feasibility, actual branch selection, callee return or effects.

With those explicit witnesses, CreateGlobalBuffAction owns its creation-
finish flag, count, input list and source target. The count reaches the
typed GetValue parameter; the source reaches GetFirstTarget's targetSettings.
SetBuffDurationAction's BuffFindSettings reaches GetBuffFindHandle_Dispose's
buffFindSettings, and its target reaches GetFirstTarget's targetSettings.
Creation, finish and lifetime-write calls remain compiled sinks, with live
handles and effects unresolved. Explicit local paths additionally prove
SetBuffDurationAction's stored operation and early-finish reads, and its
value reference reaches the typed GetValue parameter. Lifetime arithmetic,
finish-reason derivation and accepted writes remain separate obligations.
SwitchAction independently owns its choice and options references; a local
path sends choice to the typed GetValue parameter. Sequence creation,
reassignment, ticking, reset and end calls remain compiled evidence, with
Option-to-live-sequence identity, comparisons and selected results open.
Its return policy is CustomReturnType; global creation and duration actions
separately prove AlwaysReturnTrue policy getters. These getters do not
establish sequence or action results.

SwitchAction's separate Boolean `AlwaysReturnTrue` method has a narrower
owned-byte return proof. After false from the selected Boolean IFix guard,
its non-null owned Data fallthrough loads `alwaysNext` into AL and returns
that byte through a complete unchanged epilogue. The
[`owned_byte_returns.py`](../../scripts/game_data/il2cpp/owned_byte_returns.py)
checker requires the actual nongeneric Boolean caller and guard declarations,
incoming-instance field ownership, complete byte-load instruction and
separate guard/null alternatives. This Boolean method is distinct from
the enum-returning CustomReturnType getter. Live Data assignment, byte
normalization, IFix selection and the caller's use of the Boolean remain
unresolved.

The separately reviewed
[`buff_leaf_actions_native.json`](../../scripts/game_data/contracts/buff_leaf_actions_native.json)
and
[`buff_skill_stack_interrupt_actions_native.json`](../../scripts/game_data/contracts/buff_skill_stack_interrupt_actions_native.json)
name CheckSquadInFight's inversion byte and CheckOriginSkillType's attack
mask plus nullable List of SkillType. The mask reuses CheckSkillType's
declared enum without changing the parent action's identity. The list joins
the independently selected closed element type and four-byte element
reader. Null/empty lists and raw enum bits remain distinct. Native consumers
independently read the inversion byte and stored skill-type list and return
CustomReturnType on their normal false-guard property paths; fight-state
receiver ownership, originating event/skill selection, predicates and
condition results remain unresolved.

[`buff_weapon_visual_action_native.json`](../../scripts/game_data/contracts/buff_weapon_visual_action_native.json)
separately names CharWeaponVisibleAction and WeaponVFXOverrideConfig. The
parent retains include-all, override-VFX, show-VFX, visible and weapon-index
storage with its independently typed VFX child. That child has separate
enable flags and nullable string byte payloads for fight/idle appearance
and disappearance effects. Null wrappers, null strings and empty strings
remain distinct; string reference width does not define wire framing or
decoder parity. Compiled consumers call the single/all weapon-state and
VFX-override methods, with a separately proved CustomReturnType getter.
The concrete action's suffix still fails the strict complete contiguous
layout witness, so no configuration-field-to-rendering-parameter claim is
promoted. Selected weapon receivers, asset binding and actual rendering
effects remain open.

A separate explicit byte-argument mode admits only the sole bool/byte
parameter of a nongeneric reference instance method returning void or bool.
This excludes a hidden result buffer and aggregate parameter placement.
PauseBuffTime's normal branch supplies the complete byte read from its owned
Data `isPaused` field to `Buff.SetPaused.isPaused`; the independently selected
callee declaration and argument register agree. This joins a runtime Data
field to a compiled call argument. It does not prove assignment from a
particular serialized Buff into that Data object, source-byte normalization,
the returned/cast Buff receiver, selected IFix branch or an actual pause
transition.

The independently owned `Buff.SetPaused` body closes the next compiled step.
[`byte_instance_stores.py`](../../scripts/game_data/il2cpp/byte_instance_stores.py)
checks the selected instance declaration, complete incoming `this` and byte
argument aliases, the named Boolean IFix test and its false JNE fallthrough.
The actual byte-store instruction then writes that argument to this instance's
named `m_isPaused` field. Unknown instructions, partial pointers, clobbers,
wrong field owners or a different branch refuse the claim. Together with the
argument claim this establishes a compiled Data-field-to-instance-field path;
it still leaves the caller's returned/cast Buff ownership, active patch path,
serialized-source assignment and timer/tick effects unresolved.

The consumer contract separately follows HitStopAction to target selection
and StartHitStop; only its `attacker` and `target` Data reads currently have
the complete owned-field chain. RefreshBuffAttrModifierValue contains
OnBlackboardValueChange, attribute refresh recording and server-operation
creation calls. SpellInflictionOnChar contains blackboard lookup, infliction
Buff lookup, allocation/add/consume and event sinks. Its declared dictionary
is static, so the separately checkable `closedReferenceLayout` claim now
proves its instance-fieldless generic Data slot. Complete byte CMP decoding
now preserves the saved incoming-instance pointer across the initialization
check instead of treating its bytes as unknown instructions. This
independently reaches the `source` and `target` Data references: `source`
reaches GetFirstTarget's `targetSettings` argument, and `target` reaches
GetTargets_Dispose's same named argument. Both require the actual selected
callee signature and complete reference-argument ABI; the crossed mappings
are refused. Counts, immunity/trigger flags and other candidate chains still
lack complete owned reads. Compiled argument ownership does not establish
selected entities, branches, delivery or live infliction outcomes.

SpellInfliction independently proves the same source/target selection
argument pattern for its own shorter Data type. Its energy-shard Buff,
allocation, consumption, add and event calls do not close the enum/extra-flag
field chains or establish actual infliction. CharHurtAnimAction separately
owns attacker/defender references and their selection arguments; Blackboard
evaluation and ApplyCharHurtAnim calls do not prove the configuration values
or animation effects. CheckSpellInflictionType owns complete mask and saved-
key reads. Register-only BT decoding independently preserves operand
direction, width, instruction boundaries and its flags-only write, so the
saved receiver chain survives the bit-test instruction. Its event-context,
Blackboard and server-operation calls still retain gaps for context ownership,
bit-test results, saved-key sink arguments and condition outcomes.
IgniteBuffTextAction's target profile reaches its selection parameter. Its
generic EventDispatcher and EventBinding dispatch calls still need a closed
event-payload identity proof; their presence does not establish text output.
Shelter, Slow, Speedup, Weak and Enhanced independently prove their concrete
return-policy getters, with inherited keyword execution ownership left open.

The normal return policies are independently typed: HitStopAction and
RefreshBuffAttrModifierValue return AlwaysReturnTrue; CheckTargetsEqual,
VulnerableAction and SpellInflictionOnChar return CustomReturnType. The
[`constant return proof`](../../scripts/game_data/il2cpp/constant_returns.py)
admits the latter's actual complete EAX XOR-zero only when the selected enum
member is zero, then checks the same guard direction and uninterrupted return
epilogue. A byte/word clear or a nonself XOR cannot qualify. VulnerableAction's
policy getter does not establish ownership or behavior of inherited keyword
execution. None of these property returns is the action or sequence result.

DebugPrintAction has a stronger bounded conditional claim: when its compiled
IFix Boolean check returns false, the checked JNE falls through to `AL=1`
and a plain return epilogue without any intervening print call. The
`returnsAfterFalseCall` claim verifies the named call, test, branch direction,
constant and epilogue; a changed branch, additional call, unknown instruction
or return-register overwrite refuses it. This establishes the compiled
unpatched path only. The live IFix check and patched implementation remain
unresolved, so the action name alone does not establish logging behavior.

The additional consumer groups establish compiled Buff-finder and blackboard
read/assignment calls for GetTargetBuffBBAdvanced, attribute/provider reads,
dynamic assignment and Buff notification for StoreAttributeValue, and provider
evaluation plus `RandomUtils.Dice` for Conditions.Probablity. Method presence
does not establish field-to-argument flow, selected branches, numerical results
or server operation delivery. Whole-root replay and these consumer claims are
separate checks.

The CheckEntityNum consumer group separately proves target-list selection,
entity and hit-reaction carrier reads, blackboard retrieval/assignment and
server-operation construction calls. AddGlobalCDTimer calls first-target
selection, provider evaluation and `BattleManager.AddGlobalTimedMarker`;
NotifyCharPassiveUIAction calls first-target selection, provider evaluation and
`AbilitySystem.set_charPassiveNum`. These build-independent claims connect each
named action to compiled consumers while leaving its stored fields' argument
flow, live filters/count/comparison, evaluated duration or number, actual writes
and visible effects unresolved. Each group remains independently fail-closed;
a missing downstream call does not admit its partially proved rows or invalidate
unrelated groups.

The same claims contract follows the root consumers. `Buff.Reset` contains
action, ignite, shield and modifier loading calls. `_LoadActions` reaches
sequence construction/reassignment, action-container registration and timeline
loading; `_ExecuteBuffAction` contains both ordinary and instant sequence
execution calls, while `OnStart` reaches dispatch and triggering. These joins
establish compiled consumer stages, not the active Buff instance, selected
stored list, event, target or branch. `BuffData.ConvertToServer` and
`_ConvertAction` provide a separate client-side projection through action and
modifier converters into `BUFF_RES`. That projection does not establish
transport, server processing or parity with client execution. The loader uses
unique method names for these generic signatures; its claims do not declare
their argument ABI.

The independent Buff profile in
[`buff_runtime_trace_capture.json`](../../scripts/game_data/contracts/buff_runtime_trace_capture.json)
targets the missing stored-definition-to-instance-to-action join. Native
preparation proves the selected methods, field types and read programs before
recording. Buff lifecycle entries retain supplied definition IDs separately
from stored IDs and instance carriers. Action assignment and selected consumer
entries retain their environment reference identities. Closed generic ancestry
can establish access to a nongeneric base field without establishing a closed
generic field layout or value ABI. Reference identity observations read pointer
bits only; they do not enumerate collections or invoke getters.

The recipe also selects the registered `AbilityAction<T>.AssignData` body.
[`il2cpp/generic_entries.py`](../../scripts/game_data/il2cpp/generic_entries.py)
joins the current MethodSpec class/method contexts to the generic-function
table and requires one non-null entry without another method definition folded
onto it. Normal metadata signatures, bounded native extents and body windows
remain separate gates. The selected shared reference instantiation establishes
an entry address, not the live closed receiver type, hidden MethodInfo or
generic field layout. Observations retain nongeneric base fields and supplied
data/environment references; `m_data`, cast success and completed assignment
remain unread. Supplied data identity and server action index are separate
carriers, not a serialized action-node join.
Saved follow-up entries establish live use of the selected target-Buff
blackboard, attribute-store and probability consumers. Some entries have
confirmed Buff environment reference associations; others match an
Ability initialization environment or remain unresolved. This includes
probability entries in both Buff and Ability contexts. The method name or
its presence in BuffData does not establish a Buff owner.
Both ordinary and registered generic `AssignData` entries remain unobserved in
that complete, lossless sample. Matching explicit assignments still come from
`ReAssign`, which carries no supplied action-data reference. Registration proof
is not proof of an active initialization path, and a longer replay of the same
encounter cannot be assumed to close this gap. The reviewed loading consumer
claims establish sequence construction/reassignment stages; initializer entry
arguments can now be associated separately, while the selected action-data node
remains unresolved.

The initialization consumer claims now independently re-prove the compiled
`SequenceAction.Init` call to `AbilityActionData.NewAction` and forwarding of
the incoming environment. Skill highlight-condition initialization contains
skill-environment construction and sequence creation; the environment
constructor stores its incoming skill reference. These named claims establish
compiled paths, not live branch selection or a skill owner for the previously
unlinked probability entries. The capture recipe observes those initializer
entries plus `Skill.Init` and `Ability.Init`, retaining supplied data,
environment and skill references with separate stored skill identifiers.
`NewAction`'s direct class-reference return ABI is proved from the selected
declared native type; its returned action remains unobserved. Consequently a
creation entry cannot establish which consumer receiver received its data.

Saved initialization entries now distinguish two receiver carriers:
`SkillHighlightEnvironment` construction and `Ability.Init`. Selected probability,
target-Buff blackboard and attribute-store consumers have prior environment
references matching `Ability.Init` receivers, with captured incoming skill
references and matching stored/data skill IDs. Their references have no observed
Buff Reset or matching highlight-environment constructor. This is direct entry
argument evidence and a conditional reference association; it does not establish
a Buff or skill owner. Probability actions therefore cannot be assigned to a
Buff merely because their formatter also occurs in BuffData.

The runtime inspector retains constructor and Ability initialization arguments
in separate columns. Each association requires exactly one matching initializer
over the capture, prior entry order, a single observed environment thread, no
Buff-reset evidence or conflicting initializer receiver type, and consistent
observed skill identities. A later initializer or skill identity conflict
rejects earlier candidate joins; the rejected entry and reason remain visible.
This does not establish initializer completion, object lifetime, skill ownership
or serialized action-node identity. No runtime environment downcast or getter is
used. Available SkillData source bytes are archived with BuffData, and skill
ID-to-filename byte candidates remain distinct from a current schema receipt
and runtime file loading. Both selected `AssignData` entries remain unobserved
despite live sequence/creation entries. Their absence does not prove that data
assignment was absent. The initialization claims now re-prove the intervening
native dispatch: `NewAction` forwards its environment into a bounded anonymous
helper that reads the metadata-selected `AssignData` virtual slot and compares
its function pointer with the registered shared generic implementation. On the
equal side, the helper contains direct writes to the nongeneric base environment
and execution-state fields; on the unequal side, an owned native fragment
forwards action receiver, data, environment and MethodInfo through that virtual
slot. Thus a compiled initialization path can bypass both observed named entry
addresses. This is a conditional compiled-path explanation, not evidence that
the saved session selected it or completed assignment.

The rule derives the slot, base field offsets, declared signature and generic
registration from the selected build. It rejects implementation, slot, argument,
branch-direction, fragment-ownership or base-field drift, with bounded failure
diagnostics. It does not name the generic data-field offset, prove a cast, follow
IFix execution, or establish a runtime closed type. This dispatch proof alone
does not observe `NewAction`'s returned action or associate its data with a
consumer. Entry observations must retain that identity independently of branch
timing.

A named-consumer metadata check offers a narrower candidate for a future
association: `CheckEntityNum`, `AddGlobalCDTimer` and `NotifyCharPassiveUIAction`
inherit `AbilityAction<Data>` with their respective concrete nested `Data`
types. None declares its own data field or accessor; the shared base declares
`m_data` as a generic type parameter. This establishes declared ancestry, not
an instantiated field offset or the live receiver's closed type. A future
entry observation of that reference needs an independent closed-layout proof;
open generic offsets or a nearby native load cannot supply it.

Recipe v7 permits a narrowly proved reference slot on selected named consumers.
`il2cpp.reference_layouts` requires a sole instance type-parameter field, its
exact closed parent, a fieldless concrete subclass, a fully occupied nongeneric
base and a concrete size increment of exactly one reference. Selected native
inputs are authenticated before and after preparation; open generic placeholder
offsets are never used. Consumer entries retain the stored data pointer without
following it. The runtime inspector matches a unique earlier `NewAction` data
receiver and supplied environment to the consumer's stored references. Missing
fields, null references, repeated factory entries, thread conflicts, intervening
action/Buff resets or changed stored references withhold the match, including
conflicts observed later. Shared data in distinct environments is permitted.
This is reference agreement only: factory return, assignment completion, object
lifetime and serialized-node/file selection remain separate gaps. Existing
recordings receive no synthesized stored-data observation.

A complete, healthy combat recording has exercised this stored-reference
bridge on the covered consumers. An earlier factory and later consumer can
agree on both reference identities while still failing the reset boundary;
these entries remain refused. Live field coverage and per-entry results belong
in the generated capture reports, separate from the preparation layout proof.

The reviewed consumer recipe also composes this reference-slot witness with
named Data fields and inherited `AbilityActionData` fields. Within the existing
field budget it retains `serverActionIndex` plus selected comparison flags,
attribute enums, string keys or common configuration fields. The compiler
checks every declared owner/type and enum storage; stored strings require a
separate final reference read and remain within the two-indirection bound.
These bounded reads observe stored configuration, not evaluated blackboards,
collection elements, dynamic thresholds or the runtime Data class.

An authenticated payload recording has exercised the added fields on every
selected consumer class. On accepted reference/reset-window associations,
the stored consumer index agrees with the earlier factory entry. Rejected
associations retain their observed payload but supply no factory comparison.
This is sampled entry-value agreement, not proof of index conservation across
all creation paths or of an unchanged Data object between those entries.

An admitted whole Buff source can contain a unique action of the consumer's
declared Data type with an index equal to the factory entry's stored index.
This supplies a conditional source-node candidate. Reference agreement does
not prove that the Data index or parameters were unchanged before consumption,
and index agreement does not establish runtime file loading or node selection.
Compare newly recorded consumer fields separately, preserve ambiguous or absent
matches, and never synthesize these fields for an older recording. A SkillData
anonymous frame with physical EOF remains unnamed even when a legacy family
coverage flag says whole; it supplies no recursively named action-node join.
New payload comparisons also agree with scalar and enum fields in conditional
whole-Buff candidates. `utf8_source_helper.py` independently proves the actual
source helper's signed byte length, null and empty branches and UTF-8 decoder
call through `memorypack_utf8_source_helper_native.json`. It authenticates the
original source hash and exact field span before comparing a stored string
with its captured value. Invalid UTF-8 is refused; native replacement and error
behavior remain unproved. This supplies a supplemental comparison without
rewriting an older byte-payload receipt or promoting the containing schema.
Candidate uniqueness is limited to the admitted source, and does not identify
the runtime-selected node or loaded file.

The capture compiler now admits that reviewed helper through recipe v6. It first
authenticates the named caller's signature and direct reference return ABI, then
re-proves the unique anonymous entry, both dispatch sides, environment forwarding
and caller receiver forwarding into the data register. The helper is a separate
native entry, not a metadata method or a `NewAction` return observation. Only
the simultaneous action, data and environment register identities are retained;
the opaque context register, generic fields and all pointees are unread. Current
native preparation and host preflight pass. The observer is withdrawn from the
active Buff recipe after a Capture-only scene-load crash. The reduced named-entry
profile subsequently passed a user-recorded scene-load check with a complete,
healthy, lossless journal and screen backup. The captured runtime binary and all
retained hooks match the crashing profile, with only the anonymous observer
removed. This validates that loading sequence, not the corruption mechanism or
other workloads. Static argument and dispatch proof does not establish observer
safety; no complete dispatch association is admitted from the aborted recording.
An earlier startup attempt reached the helper but lost journal
records during an initialization burst. Those partial entries diagnose recorder
load; they do not establish a dispatch association. Offline preparation proves
hook selection and read programs, not queue throughput under live startup load.

The subsequent crash dump shows substantial remaining system commit capacity,
and the failure stack reaches shader-property string marshaling with an abnormal
length-derived allocation size. This does not establish ordinary memory
exhaustion or identify the recorder instruction that caused corruption. The
user reports that ordinary startup succeeds and Capture crashes during scene
loading. Retain the anonymous-observer regression as unresolved despite the
successful reduced-profile loading check; do not request another identical combat
sample to fill the disabled data-assignment gap. The loading check observes named
initialization entries but no selected consumer or assignment entry, so it adds
no action/data/consumer association. Its Buff definition identities join existing
authenticated stored-schema receipts without establishing runtime node selection
or increasing format coverage. Subsequent offline parent extensions can close
the remaining observed stored definitions when the complete family and canonical
JsonData receipts pass; replay that schema join separately while preserving the
original scene-load receipt. Such a format improvement supplies no additional
runtime assignment or consumer association.
Game-exit diagnostics retain the source log and incomplete session context,
without weakening journal completeness or promoting partial observations.

The Buff inspector records the triplet independently of named assignments and
Buff identity. It can associate a later consumer only through the same action
reference, environment and thread, refusing null data, intervening action or
Buff resets and conflicting thread or stored-instance evidence. A dispatch match
does not establish completed assignment, branch selection, object lifetime,
returned action, serialized-node selection or skill ownership. Existing saved
sessions validated before this hook was added contain no helper observation and
acquire no new dispatch association. A failed session remains inadmissible even
when its surviving helper and consumer entries appear to match.

Saved Buff sessions now provide lifecycle and selected consumer entries.
[`buff_runtime_trace_inspect.py`](../../scripts/game_data/buff_runtime_trace_inspect.py)
reuses a passing generic inspection, checks each interpreted field against its
retained raw row and profile, and requires a complete, healthy, lossless receipt.
It separates a consumer's stored environment reference from a same-thread Buff
Reset window confirmed by subsequent matching stored definition and instance
fields. A matching supplied action-assignment reference is a further, separate
association; action Reset, Buff Reset, conflicting instance fields and
cross-thread reference use prevent stale joins. Entry order and reference
equality do not establish the assignment's write or an independently proved
object lifetime.
Diagnostics distinguish an absent observed Buff Reset from an unconfirmed
stored identity and thread mismatch. A later identity conflict invalidates the
whole observed reset window and clears its consumer ID and identity claims,
while retaining the entry fields and reset sequence as evidence. Hook coverage
also lists selected entries with no records; zero entries do not establish
absence of behavior or an inactive alternate route.

The observed pooled reuse establishes a field-specific boundary: at Reset
entry, stored definition/data IDs can retain prior values while instance UID and
client-instance ID have already changed since the preceding observation.
Do not classify all Reset entry fields as the previous instance, or attribute
those changes to the body of Reset. Cached action execute-result fields likewise
precede the observed consumer call and are not its return value.

The named vitals, skill-setting and battle-signal consumers are observed in
confirmed Buff reference windows. Only some have a matching explicit action
reassignment entry; unlinked references and missing assignment records remain
gaps. Optional canonical receipt joins match archived source bytes and selected
native inputs, keeping whole stored schemas distinct from framed residuals.
They establish neither runtime file loading nor selection of a particular
action-data node. A failed schema gate empties that join while retaining valid
runtime observations. Source and reader identities are checked before and after
the join; changing coverage and per-session inventories remain in reports.

Per-frame triggering, action returns, target/provider values, dynamic
blackboard writes, IFix selection, server acceptance and final attribute writes
remain outside this observer. Archived BuffData bytes do not authenticate a
schema or native receipt by themselves. Format residuals remain independent
offline work even after a runtime sample is collected.

`buff_target_settings_child_receipt.decode_target_settings_value` is the bounded
value owner shared by typed action parents. Factoring this existing member loop
preserves earlier CreateBuff and Effect receipts; a new parent must independently
prove its field type, source context and exact child span. SetSuperArmor joins
its target to the reviewed final generic source read and composes the two
Blackboard value children. FinishBuffAdvanced joins its named BuffFindSettings
field to the exact child reader, including positive ID lists and GameplayTagQuery
arrays, and independently owns each target and BlackboardDouble field.

`buff_direct_target_actions.py` and `buff_direct_target_actions_native.json`
share an adapter across ShowHideActor, PlaySound, FinishOwner and
CheckMainCharacterCondition while retaining
a separate reviewed read order, member count and TargetSettings field for each
type. Every selected source context must belong to that parent's reader and
match the generated member type; a context belonging to a nested finder is not
another parent member. Physical union escapes retain their decoded action
identity: an extended union carrying the null-byte value is still an action,
whereas a literal null union consumes only its own byte. Named target composition
uses the shared recursive direction and selector owners. Each reached direction
reference and processor child must have its own native join and original-span
proof. Validator lists may compose the independently proved zero-member and
tag-query types; finder values must use an independently named reader. Other
selector children remain explicit refusals even when their cursor framing
succeeds.
These stored PlaySound members establish neither audio ownership nor live
playback. Action or child EOF alone never substitutes for complete root replay.

The maintained zero-member SelectorValidator owner now admits SkillCastId
alongside ExcludeOwner and MainCharacter under
[`buff_selector_validator_zero_native.json`](../../scripts/game_data/contracts/buff_selector_validator_zero_native.json).
The original routes remain unchanged; the added route authenticates its
current type-usage operand, empty generated plan, header-helper call and
zero-member test against the selected native inputs. Missing or changed
inputs at either end of validation withhold the selected routes.
Original mixed lists rejoin their typed `validatorData` field and complete
containing actions, including both direct FindTarget ownership and nested
TargetSettings ownership in CheckTimedMarkerCondition. This is stored
component evidence, not a new complete-root admission.

The current SkillCastIdValidator runtime owner declares no fields or
predicate method; its compiled constructor is only a return. Its parent is
the general Selector.Validator type. Consequently the empty stored Data
must not be interpreted as an always-passing predicate or as evidence that
the wrapper class executes the cast-identity check. The consumer selection
and actual invocation join must be traced through the surrounding Selector
consumers.

The nested `SkillCastIdValidator.Data` does contain the actual named
`Validate` consumer. Its verified signature returns `void` and receives
the owner, center, direction, blackboard, target handle, ability action and
input target. The reviewed
[`buff_selector_validator_consumer_claims.json`](../../scripts/game_data/contracts/buff_selector_validator_consumer_claims.json)
and its maintained loader authenticate calls to `get_targets`, target-wrapper
`Lock`, `get_objectType`, `Skill.get_skillCastId`, `RemoveTarget` and `Clear`.
The complete owned byte partition, closed branch targets and ordinary Win64
frames are checked by `il2cpp/consumer_control.py`, including split fragments
and the loop backedge. Both static branch outcomes remain conditional;
these checks do not establish path feasibility or an observed execution.

Empty stored Data therefore coexists with a nonempty compiled consumer.
Full-consumer joins still include the non-null abilityAction helper's class
selection and opaque fallback source, patched returns, effects inside opaque callees, IFix
selection, and invocation from Selector dispatch.
Neither a call to `Clear`/`RemoveTarget` nor this consumer's void signature
proves that any live target was removed. Native input drift, including
UnityPlayer drift before or after validation, withholds the consumer proof.

The separate reviewed
[`buff_selector_validator_mutation_claims.json`](../../scripts/game_data/contracts/buff_selector_validator_mutation_claims.json)
now authenticates the two mutation call sites' reference arguments through
the complete consumer CFG. `Clear` receives the incoming target handle and
passes true for `clearEntity`, `clearPosition` and `clearSlot`.
`RemoveTarget` receives that same handle and passes the named
`BattleTargetWrapper.Lock` return as its `AbilitySystem` target.
Both select a null MethodInfo argument. Full-width reference copies,
nonvolatile preservation, all branch joins and loop backedges are tracked;
partial overwrites and opaque volatile call returns lose provenance.
No branch may bypass the local literal argument setup. This is `conditional`
on ordinary returning Win64 callees, stable incoming stack slots and disjoint
storage, including indirect stores and opaque callee effects. It narrows the
argument join without proving the branch predicate, actual invocation or
target removal. The maintained mutation consumer loader checks the named
caller and callee signatures and withholds proof on native-input drift.

The reviewed
[`buff_selector_validator_identity_claims.json`](../../scripts/game_data/contracts/buff_selector_validator_identity_claims.json)
now joins the selected field types, explicit AbilitySystem ancestry and
inline SkillCastInfo layout to checked instruction projections. On the
unpatched candidate path, the locked AbilitySystem reference reaches
`BaseComponent.entity`, then `Entity.abilityEntityCtrl`, then the controller's
`m_skillCastInfo`. The copied value's first UInt32 is `skillCastId`; the
comparison does not compare `originSkill` or `nonReturnedAtbCost`.
The boxed field offsets and selected instance-size row support the inline
copy under the stated Win64 IL2CPP two-pointer object-header condition.

On the inspected compiled paths, a null Lock result goes to the iteration
step without a RemoveTarget call. An objectType result unequal to the selected
`AbilityEntity` enum member goes to the RemoveTarget call, as does a candidate
cast-ID DWORD unequal to the selected expected DWORD. A zero expected DWORD
selects the Clear path. When abilityAction is null, the owner fallback reads
`curSkill`: a null skill selects that same Clear path; otherwise it calls
`Skill.get_skillCastId`. That getter's unpatched path reads `Skill.m_ability`
and then its UInt32 `skillCastId`, returning the scalar used by the caller.
Clear still tests its handle for null and enters the checked exception path
for a null pointer; selecting Clear therefore is not an unconditional Clear
call. The iteration backedge tests the sign flag after a DWORD decrement,
without proving list bounds, live iteration counts or termination.

These are conditional static field and branch joins, with complete owned
caller/getter CFG and frame checks. The non-null abilityAction helper and
patched candidate/getter results remain unresolved sources. The actual
Selector invocation, opaque callee effects and live target removal remain
unobserved. Native method selection binds the selected pointer's metadata
method row: repeated full type names across images must not use the first or
last type-table match. The validation receipt gates both dynamically loaded
metadata/decoder helpers as well as ordinary package imports.

The named `Ability.FillSkillCastInfo` callee now has a separate reviewed
[`claims contract`](../../scripts/game_data/contracts/buff_skill_cast_fill_claims.json)
and [`native validator`](../../scripts/game_data/memorypack/buff_skill_cast_fill_consumer.py).
Its current instance-method signature returns `Skill.SkillCastInfo` without
explicit parameters. The named `skillCastId`, `castOriginSkill` and
`nonReturnedAtbCost` declarations and selected body-offset reads are checked,
along with patch calls and complete byte/control/frame coverage. The native
decoder now consumes the reached multi-byte NOP as one complete instruction;
unknown encodings still refuse the control proof. Missing or mismatched native
inputs, including a change during validation, withhold the proof.

The v2 claims and
[`complete return-program checker`](../../scripts/game_data/il2cpp/skill_cast_fill_program.py)
now follow the ordinary return's field flow. Under the selected hidden-output
Win64 ABI, incoming RDX supplies the Ability receiver and incoming RCX supplies
the output reference; the complete checked program retains their aliases.
When the first named IsPatched result is false and the normal path returns,
`skillCastId` supplies the result's UInt32, `castOriginSkill` supplies its
`originSkill` reference, and `nonReturnedAtbCost` supplies its Single bits.
Frame temporaries, vector/scalar copies and the final returned output pointer
are checked explicitly. The selected boxed-size/member rows establish the
inline layout under the stated object-header condition; padding is zeroed and
no numeric conversion is introduced.

The program covers both edges around the optional marking loop but does not
prove its termination, live global state or side effects. Valid readable
receiver storage, writable output/frame storage and disjoint source, output,
frame and barrier storage remain explicit conditions. The patch path is
structurally checked without substituting a value for the wrapper's return.
This narrows the named callee on one branch of the anonymous abilityAction
helper; the environment class discriminator, receiver selection, patched
values, actual invocation and live effects remain unresolved. No root or
consumer-execution admission follows from this callee proof.

The anonymous action-source helper now has a separate
[`reviewed claims contract`](../../scripts/game_data/contracts/buff_skill_cast_action_source_claims.json),
[`current native owner`](../../scripts/game_data/memorypack/buff_skill_cast_action_source_consumer.py)
and [`helper/caller program checker`](../../scripts/game_data/il2cpp/skill_cast_action_source_program.py).
The caller's abilityAction parameter reaches the helper, which reads the named
`actionEnvironment` reference. Complete control checks retain each real code
range and its branch addresses; no fallthrough is invented across the gap.
The helper returns its incoming output reference on the checked return paths.

One raw discriminator case supplies that environment reference to the actual
named Fill callee. Its three-member return composes only under the already
stated valid-Ability, unpatched, normal-return conditions; the discriminator
does not itself establish that class identity. A second case copies an
anonymous environment interval into the output. That copy is structural-only:
it does not assign a SkillCastInfo or controller field name to those bytes.
Three separately checked literal cases zero the entire output. The unnamed
fallback and patch-wrapper results remain opaque.

The caller's complete checked projection copies the helper result's low DWORD
to its expected-ID register without conversion, tests it for zero and selects
the previously proved Clear path. Only the independently proved owner-skill
fallback may rejoin that test from outside the projection; other entries that
bypass helper setup or result extraction refuse. The zero-helper cases
therefore select Clear conditionally, while Clear's own nullable handle guard
still prevents treating selection as an unconditional call or live removal.
Actual class-discriminator construction, receiver selection, opaque effects
and invocation remain unresolved. Current native and source gates authenticate
the caller, helper and Fill proofs freshly in one selected image.

The fallback now has a checked
[`interface-return contract`](../../scripts/game_data/contracts/buff_skill_cast_interface_return_claims.json)
and [`native consumer`](../../scripts/game_data/memorypack/buff_skill_cast_interface_return_consumer.py).
Its actual disk context resolves to the declared IActionEnvironment interface,
and the passed slot joins that interface's instance FillSkillCastInfo signature.
This is a static type/slot join; the unresolved disk usage cell is not treated
as an observed initialized runtime class pointer.

The complete adapter byte program and PE exception-family membership are
checked independently of the old display decoder, which splits some of its
integer instructions incorrectly. The matched-entry path uses an unsigned
word count/counter, doubles the index for the stored entry stride, adds the
slot in a wrapping DWORD, sign-extends that sum and derives a function/MethodInfo
pair. The invocation passes the original environment receiver, MethodInfo and
local output buffer, then copies the returned reference's value bytes to the
caller's output. The lookup path's returned pair remains opaque. These facts
require compatible readable tables, a correctly initialized interface class
and ordinary returning Win64 callees; table or vtable bounds are not invented
from a signed offset.

The named default IActionEnvironment.FillSkillCastInfo body separately zeros
the complete return buffer and returns its address, without receiver-field
reads or child calls. If the actual selected method pointer is this default
body, its result therefore reaches the caller's zero-ID Clear selection.
No installed-data name or slot match proves that runtime target selection.
The class discriminator, initialized cell, actual implementation pointer,
preparation/lookup/callee effects and invocation remain unresolved.

`buff_recursive_control_actions.py` composes IfElse's typed sequence children
recursively, CompareFloat operands, ModifyDynamicBlackboard targets and scalar
values, and CheckBuffStackNumAdvanced's independently owned children. Each
physical action span must close before its named child reader runs; recursively
anonymous children still refuse the root. `buff_id_actions.py` distinguishes
the one-member BuffId wrapper from BuffFindSettings' raw string-list elements
and CheckGlobalCDTimerAction's plain `buffId` string. The timer action joins its
separate TargetSettings child through the selected formatter source context;
its identifier bytes remain raw, and runtime timer selection or expiry remains
unobserved. Different parent field types and native source contexts prevent
treating these wire shapes as interchangeable.
The same owner independently admits AddGlobalCDTimer through its own reviewed
formatter and actual source-result stores. Its plain `buffId` bytes,
BlackboardDouble `cdTime` and TargetSettings `target` occupy separate spans;
the scalar and target generic contexts are checked independently of the common
priority context. Nullable identifiers and providers remain distinct from
evaluated durations and applied timers. This parent uses the Buff dispatcher
and its own current native gate; the earlier SkillData source-order proof
alone does not authorize a Buff composition.
CheckDamageDecorateMask also composes as a standalone event-map action through
its existing reviewed condition member plan. The original mask's eight stored
bytes stay intact; this broader parent composition does not add a predicate
evaluation claim.

`buff_blackboard_string_child_receipt.py` names the stored blackboard key,
use-key flag and value through matching native source stores and generated
setter destinations. CheckSkillId's list and RaiseTrainLevelEvent's direct
children independently join this grammar through their typed source calls.
Payload encoding and runtime interpretation remain unresolved: receipts retain
raw payload and flag bytes. Child contract reads observe current file bytes,
including after an earlier successful decode in the same process.

[`BindBountyEnemyAction`](../../scripts/game_data/memorypack/buff_bind_bounty_action.py)
now composes the same independently owned child under its
[reviewed parent contract](../../scripts/game_data/contracts/buff_bind_bounty_action_native.json).
The current parent stores the inherited byte/three-DWORD prefix followed by
`bountyKey`, whose typed source context identifies BlackboardString. The child
has its own bounded original receipt; a parent header or matching field name
does not supply that ownership. Short and extended encodings of the current
tag retain their actual byte spans, with null parent, null child and null/empty
child payloads kept distinct. Payloads remain raw bytes, including bytes that
are not valid UTF-8. Original action checks and shared-event integration grant
no bounty/enemy identity, evaluated key, binding effect or complete-root
admission; the full family and original-root replay gates remain required.

`buff_check_buff_id_context_advanced.py` independently joins the advanced
condition's list to BlackboardBuffId. That type inherits BlackboardString's
three members, but its own reader and typed list context still need proof:
the selected source calls invoke the same byte-payload, byte and byte-payload
helpers, then pass each result to the matching inherited setter in order.
Only after that join does the shared BlackboardString value decoder name each
list element. Null lists, empty lists and null elements remain distinct, and
the GameplayTagQuery field composes its own named child. This three-member
subtype is separate from the one-member BuffId wrapper. Neither inherited
layout nor child EOF proves condition execution, provider selection or whole
BuffData completeness; event-map admission still requires all original root
fields, source-ID equality and physical EOF.

`buff_selector_geometry.py` and `buff_find_target_action.py` compose the
FindTarget parent with independently typed DirectionSettings and SelectorData.
HitBoxFinder's bounded shape list contains named ShapeData records; each Double
and Vector3 field joins its own native child proof. BlackboardVector3 uses
three nullable, variable-width BlackboardDouble children, not a fixed raw
coordinate triple. Its value reader is shared with EffectAction. InFight's
zero-member finder is separately proved. Successful cursor traversal alone
does not supply any of these names, and unsupported finder or nested direction
target variants still refuse complete root admission.

The shared selector composer keeps the named `finderData`, `postProcessorData`,
`validatorData` order. `buff_selector_postprocessors` independently joins the
postprocessor list's closed `ReadPackable` context to its actual owned runtime
field, then authenticates the selected CircularOrderSort, Projection,
ExcludeTarget, NavMeshPathPositionProcessor, PriorityFilter and ShuffleTarget routes.
Projection's `boxShape` list composes the independently proved ShapeData
records; ShuffleTarget keeps raw `processTargetType` bits and the concrete
BlackboardInt's key, use-key flag and integer value. The latter reuses the
root's maintained concrete child proof, with an independently checked parent
type join. ExcludeTarget's child context joins the actual TargetSettings
wrapper's owned `__instance` type before invoking the shared recursive target
reader. PriorityFilter's separately typed BuffFilterSettings child composes
the maintained BuffFindSettings/GameplayTagQuery owner; the remaining filter,
count, reserve and process-mode operands retain their stored bytes. The
selector/target/postprocessor cycle uses the same bounded target depth and
strict original child endpoints, including repeated ExcludeTarget nesting.
Null list, empty list, null union, null wrapper and null Blackboard are
separate states. Other postprocessor subtypes still refuse the enclosing
composition. The [reviewed postprocessor contract](../../scripts/game_data/contracts/buff_selector_postprocessors_native.json)
records these current source/destination and child joins; target projection,
filtering, shuffling, provider choice and blackboard evaluation remain unresolved.

CircularOrderSort and NavMeshPathPositionProcessor now belong to the maintained
list composer, through actual union switch/type-usage chains and the
[reviewed source programs](../../scripts/game_data/contracts/postprocessor_circular_navmesh_native.json).
`setter_output_sources` proves their incoming byref-reader and ref-wrapper ABI,
the complete read-result/setter bridges, and the setter's exact owned Data
stores. These readers retain the reader in RDI and the ref-wrapper in RBX;
the final member deliberately replaces RBX with the wrapper it references.
Their typed `__realInstance` getter's selected ordinary path checks that its
cached derived Data equals the inherited base instance before returning it.
The proof retains an explicit condition that preceding calls return ordinarily
and preserve Win64 nonvolatile registers. Generic source contexts have no
unique registered entry join; the actual physical calls and their typed
MethodInfo argument programs are checked, without filling that gap by name.
CircularOrderSort
owns `desireCount` as BlackboardInt; `heightOffset`, `rangeThreshold` and
`reverseFlag` as BlackboardDouble; `indexKey` as a raw string payload; and a
separate `rangeCheckTarget` reference. In particular, the name `reverseFlag`
does not make its declared BlackboardDouble a Boolean. NavMeshPath's radius
joins BlackboardDouble, its maximum distance retains raw Single bits, and its
navigation flags retain their byte representation. The independently checked
primitive source programs read and account for one byte or four Single bytes;
the byte source's selected normal path applies nonzero normalization before
AL reaches the setter. Keeping raw stored flag bytes does not assert that the
runtime field preserves those bytes. Blackboard and recursive TargetSettings
children join their independently admitted actual types; `indexKey` reaches
the reviewed nullable byte-length string helper and retains raw payload bytes.
Complete original lists now replay through the maintained composer, including
mixed processors and these children. Complete family and independent canonical
root replay remain the enclosing-root admission boundary. These stored
declarations and conditional transfers do not establish circular order,
blackboard evaluation or navigation effects.

The corresponding Data `PostProcess` methods also expose separate consumer
leads. Bounded original prefixes trace their incoming reference receiver to
owned configuration reads. CircularOrderSort's scalar operands and NavMesh's
radius reach the actual static `ActionBlackboardExtensions.GetValue` parameter;
the BlackboardDouble overload returns Single. The selected `reverseFlag`
program compares that return with zero and assigns a local flag, without
proving the evaluated value or resulting order. NavMesh's `checkMaxDistance`
and `maxDistance` reads belong to `_GetRealLandPos`, with another distance read
in `_TryFindStraightLineDest`; absence from the main body's proved reads does
not establish that a field is unused.
The owned `checkMaxDistance` byte is compared with a separately proved zero
register, and its immediate JE reaches the local result's return-copy path;
the other compiled edge continues into distance processing. Its runtime value
and chosen edge remain unknown.

These helpers illustrate why aggregate return ABI must be proved per call.
The actual `_GetRealLandPos` caller supplies Data in RDX and a separate result
buffer in RCX. Its selected complete ordinary return program copies the
Nullable<Vector3> representation into that buffer and returns its address in
RAX. This is separate from the Boolean-returning straight-line helper's RCX
receiver. The straight-line distance program retains its owned maximum-distance
operand across a shared Vector3 squared-magnitude entry: its complete program
uses the actual coordinate fields, writes only other vector registers and
returns the sum of coordinate squares before the caller squares and compares
the maximum. The entry has both static and instance method declarations, so
this proves the compiled operation rather than a unique method-name join.
Vector provenance, floating-point exceptional behavior, chosen branches,
navigation success and target mutation remain open. These observations use
the [bounded compiled-path boundary](../../scripts/game_data/il2cpp/compiled_paths.py)
and the reviewed runtime field declarations above; isolated prototypes have
not added maintained consumer claims.

`buff_direction_target_children` composes nonnull `source` and `target`
TargetSettings through [separate reviewed reference transfers](../../scripts/game_data/contracts/buff_direction_target_joins_native.json).
The source has an independently initialized null stack reference, overwritten
only on the selected cached-provider branch before transfer to its owned field.
The target transfers its separate returned reference to a different owned
field. Complete normal pointer programs preserve the incoming reader and
ref-wrapper aliases; neither an eight-byte reference transfer nor a matching
type name establishes a child's wire format. Each nested TargetSettings must
pass its own reader, Selector/finder/validator/postprocessor composition and a
strictly contained original span. Recursion is bounded; no child completion
waives its siblings, parent endpoint or physical root EOF. CreateBuffAction,
EffectAction, the hurt-animation curve parents and the shared target callback
use this same composition, while FindTarget passes its own separately typed
direction and selector fields. Curve parents no longer require their
direction's source and target to be literal null values: each positive child
must independently close through the shared target owner.
Stored recursion does not establish evaluated directions or selected targets.

The single-CreateBuff root adapter now receives the same complete recursive
action proof as the shared event-map route, rather than assembling a separate
subset of target children. The corpus validates the shared action context once
and passes it to this adapter; standalone callers validate the same owner.
The adapter still checks its own sole action, input cardinality, every root
member, source-ID equality and physical EOF. Missing nested proofs and build
drift remain explicit failures before action replay. This prevents a newly
composed shared child from silently bypassing, or being omitted by, the older
root path.

The remaining consumer leads remain outside maintained execution claims.
The [reviewed FindTarget family](../../scripts/game_data/contracts/buff_b2_native.json)
contains the ExcludeTarget and PriorityFilter parents and BuffFilterSettings
reader. Their stored child joins now belong to the maintained postprocessor
composer, under independently checked closed contexts and exact original
spans. The authored filtering
methods belong to the nested Data types; method ownership must be resolved
before tracing incoming receivers. Native enum declarations distinguish
Targets and HittableTargets and name distance, HP, Buff-stack and screen-position
filter modes. These declarations and stored words do not prove that a mode
executes, forwards its operands, or mutates a target view.
Isolated current native prefixes also trace the incoming Data receiver to its
direct configuration reads. Naming a subsequent call parameter requires a
separate ABI and forwarding proof. In particular, GetTargetsView's caller
saves its RAX result directly, whereas FilterParamWrapper.Wrap's caller passes
a stack buffer and copies the returned aggregate. A value-type declaration
alone must not shift all named parameters as though a hidden buffer were
present; the actual caller, callee, return representation and field stores
must agree. An isolated original-program probe closes Wrap's ordinary
buffer-return path and its actual constructor. Each constructor helper has a
closed local retry/return graph: its instructions modify the bitmap through a
bounded native-image address range and preserve the volatile aliases carrying
the remaining constructor operands. The constructor's complete typed stores
establish the unboxed field representation; Wrap returns its original incoming
buffer after that constructor returns. Under the ordinary IsPatched-false path
and the explicit x64 nonvolatile-call boundary, incoming PriorityFilter Data
fields `buffFilterSettings`, `onlyReserveMaxPriorityTargets` and
`processTargetType` reach Wrap's separately identified named parameters.
The compiled caller prefix does not prove predicate feasibility, the action
environment's provenance or any evaluated filter result. These observations
remain outside the maintained consumer claims, and the concrete Wrap proof
does not supply an ABI rule for GetTargetsView or other aggregate returns.
An additional isolated forwarding check reuses the same owned caller prefix:
stored `maxNum` reaches Filter's register parameter after Wrap's complete
normal epilogue restores its incoming nonvolatile value, and `filterType`
reaches Filter's separately named outgoing stack parameter. The actual static
Filter declaration returns Int32, excluding a hidden result buffer for this
particular call; its enum parameter joins its declared Int32 underlying type.
The selected configured-count/fallthrough branches and the prior ordinary
callee boundary remain attached. Parameter forwarding does not establish
count enforcement, comparison order, the Filter result or target mutation.

`buff_camera_control_state_action` composes the
[camera-control parent window](../../scripts/game_data/contracts/buff_19e_native.json)
through its own [reviewed action contract](../../scripts/game_data/contracts/buff_camera_control_state_action_native.json).
Action bodies are located through their union
headers; an object-header-only inventory can miss them. The two custom-curve
fields have separate closed contexts that join the actual AnimationCurve
argument of the selected formatter's generic base. The existing
[AnimationCurve proof](../../scripts/game_data/contracts/memorypack_animation_curve_native.json)
can replay each independently owned original child without claiming curve
evaluation. The inheritSkillIds list joins the same actual closed List<string>
context and source read target as BuffFindSettings's buffIdList. Its bounded
nullable byte-payload grammar is shared, while string decoding and live
provider selection remain conditional. Null list, empty list, null elements,
empty payloads and arbitrary payload bytes retain distinct receipts. All
other parent flags, enums, scalar bits and key payloads retain their original
spans; no successful child replay waives sibling fields or complete root EOF.
Compiled addition, inheritance and cleanup calls are leads for argument/handle
flow. The separately checked ordinary getter returns CustomReturnType; that
policy does not identify the action result or prove a camera-state effect.

`memorypack/buff_attribute_modifier.py` and its own reviewed native contract
own the reusable AttributeModifierData collection/element grammar. It separates
null collection, null array, null elements and null BlackboardDouble params;
the terminal collection byte is still consumed after null or empty arrays.
The selected empty-condition route consumes this shared owner while preserving
its original complete receipt. Parameter, enum and flag values are stored
data, without attribute evaluation or live formatter selection.

The root's one-DataPair and GlobalModifier co-occurrence restrictions were
historical candidate filters, not native presence rules. The native-gated
bounded DataPair reader and complete forward root admit larger lists without
changing the wire grammar. Every promoted root still needs all thirty fields,
source-ID equality and EOF. `memorypack/buff_residual_census.py` excludes exact
roots before ranking unresolved child obligations and counts unique sources;
overlapping completed-action cohorts do not predict complete root closures.
It counts authenticated per-file exact flags and cross-checks total, exact and
residual counts against the canonical registry. A family summary may omit the
aggregate exact counter; when present it must agree with the per-file count.
Only a unique candidate explicitly accepted through EOF supplies named
obligations and owned unions. Rejected embedded-marker probes remain a
separate inventory: an absent receipt on a rejected probe is not another root
composition gap. Missing or competing accepted frames retain an explicit
root-frame obligation. Acceptance flags and declared accepted counts are
checked, and the named receipt's `physicalEof` must match the original logical
length. Another parser projection's `readerEndOffset` is not substituted for
this root coordinate.

The census's `--replay-shared-events` mode distinguishes that recorded baseline
from the newer shared event-map reader. It rereads only unresolved eligible
roots, rejoins their logical bytes, and authenticates current root/event native
inputs and the contributing reader/contract closure before and after the run.
Already exact roots remain excluded. A receipt must still cover thirty
contiguous fields, the source-ID join and physical EOF; this diagnostic never
publishes coverage. The ordinary null-event candidate filter cannot assess
event-bearing residuals, and event-map eligibility alone does not close them.
Composing proved children can close additional roots; residual refusals still
reach unsupported action dispatch and nested finder/selector interiors. Those
are typed child obligations, not a reason to loosen the parent or infer action
behavior.
A selected forward replay can close the complete named Buff root while an
earlier candidate filter prevents family admission. Embedded filename markers
can create rejected suffix candidates; shared-event selection counts only the
single suffix accepted through EOF and retains rejected markers as diagnostics.
Selection establishes eligibility only. The original byte-zero reader must
still prove every root field, source identity, current native dependencies and
exact EOF before the whole-family and canonical gates admit the file. A bounded
replay alone never changes coverage or the recorded-definition join.

[`buff_cost_action.py`](../../scripts/game_data/memorypack/buff_cost_action.py)
now owns the named stored `ObtainCostAction` parent. Its
`atbGainTag` and `uspRecoverTag` are `GameplayTag` value types, so the
primitive member-width derivation intentionally returns no width. The
reviewed `buff_fe_native.json` reader independently takes a DWORD for each
closed type, and `wrapper_members.unmanaged_value_sizes_from_image` derives
the same extent from the selected build. These are separate witnesses, not
permission to treat arbitrary value types as scalar integers. General named
parent admission now uses an explicit reviewed `unmanagedSource` proof to join
unmanaged size, closed source MethodSpec, source read width, cursor accounting
and destination. The registered generic entry and the parent's optimized
direct-call entry can differ: both native bodies are authenticated separately.
The registered normal path reads a DWORD and invokes its own cursor helper
with four; the optimized normal path performs the same four-byte reader-slot
updates directly. This proves the selected stored width without equating
addresses or extending the claim to short-segment/provider behavior. A missing
or changed entry, instruction window, typed context or destination refuses
admission with the record and field identified.
The cost reader keeps `coefficient` and `costValue` as independent BlackboardDouble
children, `source` and `target` as independent TargetSettings children, and
ATB/USP selectors, GameplayTag bits and flags as stored values. All children
must close on their original spans. These names and stored values do not
establish live resource gains, deductions, provider results, target selection
or sound/effect dispatch. The complete Buff root and canonical replay gates
remain required for coverage publication.

The census also ranks shared-event refusals already stored in the complete
family report, without running the parser again. It removes source-specific
positions from grouping keys while preserving union tags and structural
expectations, retains original diagnostics and source hashes in bounded
examples, and counts residual files with no recorded refusal separately. That
absence supplies no closure evidence.
Its first-stop cohorts normalize byte positions while retaining union tags and
raw per-source diagnostics. They rank unique sources sharing the first reached
gap, not all future gaps or predicted closures. Generated counts and examples
belong in the census report; complete-family admission and canonical original-
byte replay remain the publication boundary.

`memorypack/buff_selected_roots.py` owns their complete-family admission and
canonical export replay. It requires the exact reviewed logical path, length
and SHA, current root and child native gates, all 30 contiguous named fields,
source-ID equality and physical EOF. The positive-heal route also authenticates
its existing selected native audit. Helper source closure, contracts contributing
to dispatcher comparison, the audit and all three native inputs are pinned and
rechecked before and after the corpus scan and registry replay. Each source has
one exclusive cohort; a different source or changed bytes receive no admission.
The standalone selected child/root diagnostics keep `selectedOnly` and
`publicationEligible: false`; only a complete authenticated Buff family report
can supply a row for registry `schema_decoded` after fresh original-byte replay.
Other unsupported nested interiors remain partial. Raw query, enum, event,
priority and scalar bits do not prove live
healing, modifier arithmetic, event execution or formatter-provider selection.

The complete Buff family gate admits these sources after current dependency
and native validation. Registry publication additionally requires canonical
export replay; the standalone diagnostics never supply that publication.

## SkillData

`skill_custom_root_motion_regenerate.py` re-proves the v2 25-member plan, including member 9's added boolean and the inlined LayerMask DWORD/Advance(4); the enclosing shared timeline contract remains unmigrated and fail-closed.

**Current build (StringPool, 49-member root).** The installed client stores
every string as a signed i32 StringPool index and its SkillData root has 49
members, so the frozen pinned line (`skill_corpus`, the `skill_timeline_*`
readers, hard-coded root header 48 and old-build tag literals) refuses at its
first native gate; migrating its ~230-contract dependency closure would not
revive it without StringPool threading and the new root. The build-derived
line covers the family instead: `derived_values` (with the export StringPool)
frames all files to physical EOF with every `skillId` equal to its filename,
and `memorypack/wrapper_body_audit.py` proves, for every wrapper the corpus
reaches, the generated reader's `ThrowInvalidPropertyCount` count and its
own-member write order against the plan, by name on the selected build with
no pins. Every SkillData and BuffData file is `nativeOrderChecked`. That is
names, order and header counts (`direct`); per-member read kinds stay
`structuralOnly`, and the audit does not promote the frozen family report's
framing status. The paragraphs below describe the previous build's pinned
line.

SkillData (previous build) was one 48-member object: field 0 `ActionGroupData`, fields 1-42
read by a sequential reader derived from the generated wrapper types, and a
five-member terminal (fields 43-47). A gated immediate-registration site joins
the Core `ReadValue<T>` key to `GenericMemoryPackFormatter`. That is static
adapter identity, not executed registration or active dispatch
(`scripts/game_data/il2cpp/context_audit_skilldata.py`). Framing admission
climbs from exact action extent to timeline record, whole ActionGroup, then
whole file (fields 1-42 plus the selected terminal at physical EOF). A lower
rung never counts as a higher one.

The family report's legacy `wholeSchemaExact` flag and corresponding coverage
tokens describe top-level framing and EOF, not recursively named interiors.
`jsondata_corpus` retains that source flag as `familyWholeSchemaExact`,
publishes `storedFrameExact` separately, and keeps `namedSchemaStatus=unproved`
until an owning reader supplies complete recursive naming evidence. Anonymous
nested ranges and records carrying only a type, tag and extent remain
structural. Some compact profiles discard child receipts, so absence of an
anonymous marker is not affirmative named-schema proof. Known fields and
accepted frame evidence remain available; this correction requires no repeat
capture of an already authenticated terminal.

An independently named action can be replayed at an existing Skill span when
the selected native dispatcher, reached source reader and typed children agree
with the reviewed Buff route. Keep the original archive hash, physical span and
field bytes; this proves only that action's stored layout. Comparing its named
leaves with a consumer additionally requires an accepted same-reference
NewAction/environment window and supplied Ability skill identity. Type/index
and equal payloads can still match repeated physical nodes. Preserve every
candidate; missing nodes in a partial Skill profile are coverage gaps, and
neither outcome names the whole Skill root or proves runtime node selection.
Initializer entry caller addresses are separate evidence: native body ownership
may identify a registered caller, but an indirect call or an anonymous body
does not reveal the factory return or an assignment branch.

Per-tag layouts live in code, one reader per route:
`scripts/game_data/memorypack/skill_timeline_*.py` for actions,
`skill_selector_*.py` for nested selectors (their own switch tables), and
`skill_timeline_shared_sequence.py`, whose composite contract also admits
routes reused from reviewed Buff readers. Reviewed source routes pin the
dispatcher, reader body, source calls and generic contexts; declaration-derived
routes retain their weaker framing evidence. Readers check
every reached union tag and member-count byte. Nested children
(`skill_selector_postprocessor_convert_to_slot`, `skill_selector_zero_member`
-- where `FF` is not a zero header -- `skill_damage_unit_gameplay_tag_list`,
`skill_timeline_two_*`) are admitted only where reached. All of it is stored
framing only. Gate: `python -m scripts.game_data.memorypack.skill_corpus`.

`skill_timeline_recursive_actions` composes RepeatAction from the reviewed
BlackboardInt and SequenceActionData children. SetMultiTimesWeakness adds
BlackboardDouble and a nullable list of that child to the same Int/sequence
grammar. BlackboardDouble's stored scalar occupies four bytes despite its
type name; the reader preserves arbitrary scalar bits, including nonfinite
values, and distinguishes null, empty and positive lists. These recursive
routes use the ordinary shared sequence bounds and unknown-child refusals,
without source-name exceptions.

Their native join checks the exact typed MethodSpec/context operands and the
reviewed shared-consumer RGCTX propagation. These direct shared consumers do
not have closed-type entries in the generic-method pointer table; an absent
entry cannot establish a different child or a concrete provider selection.
The contract establishes stored read order and child boundaries. Formatter
replacement, runtime repetition and weakness-effect execution remain separate
questions, and whole-file admission still needs the complete family gate and
the existing source-bound terminal evidence.

**Static limit.** Rows with no content-bound prior receipt (files added by the
newer VFS overlay) have two terminal framings that both parse exactly to EOF.
The native field-43 bool and field-44 `GameplayTagList` header favor the
earlier one only conditionally on the ordinary formatter/provider route, and
static evidence cannot observe provider choice or the executed cursor. The
subset rebind carries a prior live selection only to logically identical rows,
so new rows stayed `ambiguous` until the live target-set capture. The capture
is gated by `il2cpp.skill_cursor_native_context` and
`il2cpp.skill_cursor_target_set_context`, verified by
`skill_cursor_capture_target_set` and promoted by
`skill_cursor_target_set_overlay`. Those docstrings own the provenance chain,
the rebuild order after a reader change, and the capture procedure.

Historical export-backed censuses do not establish current VFS coverage;
`memorypack.skill_corpus` starts from the authenticated ledger and stream
bytes, and a unique EOF candidate is unique only within its grammar.

## SkillData live cursor evidence

The historical reviewed target-set capture and positive control are complete
and loss-free for their original native build. Every witnessed source reads the earlier one-member terminal:
field 43 `switchToCenterBeforeCast` through field 47 `useAIExclusiveFrame` at
physical EOF. The prior complete sweep promoted that selected set; later
sparse checks do not replace a current complete family gate.

A cursor selects positions for one exact logical source: terminal candidate,
field vector and ActionGroup child checkpoints (`skill_cursor_receipt`). It
cannot name an unparsed populated child, choose a formatter/provider/cache,
show a gameplay branch, or give action semantics. Purrche's authored parent
places the base combo ability-range source in the fail branch of
`potential_3 >= 1`; the below-Potential-3 branch was unavailable on the user's
save. Its storage and native logic are recovered, execution is unobserved,
and preloading can explain a deserialization witness.

Capture reuse is source scoped. `skill_cursor_capture_target_set
--rebind-current-corpus` checks current logical path, length, hashes, copied
bytes, native reader/callsite vectors and loss-free transport before retaining
a historical selection. It preserves the historical observer fingerprint and
requires the captured vectors to equal the selected native vectors. An
exporter fingerprint change is not a new observation. Sparse reports remain
nonpublishable; a changed parser fingerprint must be revalidated rather than
silently carried forward.

The historical target-set verification and rebind summaries remain available,
but their original capture receipt is absent from its recorded local source
path. A summary's `validated` token cannot replace that primary input.
`jsondata_corpus._skill_capture_target_set_reference` correctly refuses the
complete registry when the original/rebind overlay cannot replay its pinned
receipt. Restore a hash-identical saved receipt and every required dependency
before rebuilding the complete canonical registry. A passing Buff family gate
or selected canonical Buff replay remains separate evidence and does not
repair the missing Skill capture or publish new registry coverage.

The original empty/passive/timeline family controls have unchanged-source
cursor replays. `skill_sparse_corpus_compose` can compose selected diagnostics
with frozen controls only after proving the admitted parser/contract delta
and that the controls do not reach it. A diagnostic's large `missingOld`
count describes rows outside its selection, not deleted installed sources.
A frozen complete-report rebind additionally needs current VFS chunk selection
and fingerprints; logical hashes stored in an old report alone are insufficient.

Selected-source joins beyond the original target set:

| Scope | Reusable proof owner | Current boundary |
| --- | --- | --- |
| Mifu | selected SnapPointFinder and `skill_timeline_check_skill_has_hit` | CheckSkillHasHit is admitted by the shared native gate; its ActionGroup closes in focused replay. The complete family gate and source-bound terminal evidence decide whole-file publication. No duplicate framing capture is needed. |
| Lbshamman / Agtrinit and other admitted routes | `skill_timeline_shared_sequence` and each route's native contract | Source-scoped replays close or advance under the shared reader. The code/contract inventory owns the route list; the family report owns publication. |
| Wulfa | `skill_cursor_wulfa_scope`, `skill_cursor_wulfa_terminal` | The separate native-gated cursor joins one whole stored source; no gameplay transition is inferred. |
| Seraph | `skill_cursor_seraph_capture`, `skill_cursor_seraph_terminal` | The separate cursor and independent ActionGroup reader join one whole stored source; no live action semantics are inferred. |
| Zhuangfy | `skill_cursor_zhuangfy_group_join` and source-specific joins | The grouped receipt and independently checked child readers close the selected stored sources. Five routes are admitted to the shared reader; saved earlier joins remain historical where parser provenance changed. |
| Lizhiyan combo / Pograni ultimate | `skill_cursor_lizhiyan_pograni_join`, `skill_cursor_lizhiyan_pograni_terminal_selection.json` | The loss-free grouped receipt names fields 43-47; static ActionGroup and fields 0-42 match every executed cursor and reach EOF in both selected sources. |

For Lizhiyan/Pograni, the reviewed context joins their separate one-source VFS
reports and copied-source identities. SetIgnoreGlobalTimeScale now joins the
shared reader through its own selected-build native gate, as do CheckSkillHasHit
and DispelAction. The composite contract references each domain contract and
checks its tag, member count and source-read declaration before admission.
Missing, mismatched or drifted native evidence refuses the route. Focused
ActionGroup closure does not replace the complete family gate or a source-bound
terminal selection. Both witnessed whole stored-record conclusions need no
further capture; changed parser provenance requires a current corpus basis and
offline receipt revalidation before publication.
The shared Skill reader also admits reusable Buff-owned action grammars only
after the Skill dispatcher, wrapper, read order and nested type contexts agree
with each owner's reviewed contract. Numeric tag equality alone is never an
admission. CheckPartTagMatch's TargetSettings is followed by the value-type
GameplayTagQuery, not a reference wrapper. Historical source-bound terminal
selections can be reused after current parser/source revalidation; adding these
stored action readers needs no duplicate live framing observation.
The earlier static one-byte-later terminal alternatives are superseded for
these witnessed sources only. Stored flags, keys, masks, movement and action
operands establish no gameplay execution, timing, target choice or final value.

## Resolving the native formatter

Each step is `direct` static evidence, never the live formatter, cache, cursor
or EOF; `il2cpp.context_audit` checks it, and each report `boundary` says what.

1. Registration is a pointer array of 16-byte records; `GetFormatter<T>`'s
   parameter belongs to `ReadValue<T>` (`il2cpp.context`).
2. The MVAR leaf ordinal indexes the method-inst vector; modules join by
   unique image name; usage cells resolve via the lazy MethodSpec resolver.
3. The cache is seeded from the registration and compares only the tag plus
   one flag bit. RGCTX slots are not module entries. Never put shared
   object/object arguments into the companion's class context.
4. Setter order is the wire order: generated setters, inherited first, never
   `fields_for` (`memorypack.wrapper_members`).
5. `memorypack.action_dispatcher` walks every AbilityActionData tag;
   `memorypack.union_subtypes` orders nested unions (`structuralOnly`).
6. A body is tag, member-count header, members. The opt-in `derived_*`
   modules fail closed; a plan-only tag is self-consistent, not proven.

## Wire rules every reader relies on

Owners: `memorypack.derived_schema`, `memorypack.wrapper_members`,
`il2cpp.context_audit_memorypack`.

- `List<T>` elements carry a header or `FF`; unmanaged `T[]` is packed raw.
- A struct is its aligned size; a union base is abstract without `Deserialize`.
- Maps are a count plus pairs, padded only when both sides are unmanaged.
- The wrapper reader takes one header byte; `ListFormatter` compares its
  signed count with the remaining bytes, unscaled.
- The `FF` peek consumes one byte; other elements convert through
  `IMemoryPackDeSerializeWrapper<T0>`, so output width is not consumption.
- The provider takes a companion, not the reader; its caches are stateful.
- Cursor state is never an EOF test; no caller compares consumption.
- The formatter-check carrier's last 16 bytes are opaque.

## Recovery acceleration

Historical schema bundles such as the ignored
`tools/endfield_schema_recovery_1.4.4/` are candidate references for recursive
Buff/Skill shapes and manual wire exceptions, never production dependencies.
Join their exact runtime types through `wrapper_members` and `action_dispatcher`;
rederive ordinal tags and check root layouts against the selected build. The
historical Buff root can retain its field order while nested union ordinals and
child records change. The existing derived-plan lane already
supplies current names and member order, so prioritize independently useful
physical-layout corrections rather than duplicate catalogs. Declaration agreement
and a successful reference-body parse still require current native reader,
typed-child and source-span proof before the ordinary family/registry gates;
they recover neither missing cursor receipts nor live consumer/provider selection.

The historical decoder, after isolated current-identity and declaration overlays,
now gives a structurally clean candidate for the complete selected Buff corpus.
It also reproduces the named root spans of previously admitted roots. These
checks close the reference grammar frontier; they do not admit the remaining
roots or establish preservation of raw flags, enum values, float bits and string
encodings. Keep the candidate outside production, authenticate each recursive
formatter and typed composition, then replay original source spans through the
maintained readers. Trial variants, coverage and per-source results belong in
the generated historical-schema leads report.

The maintained `buff_cast_skill_action` reader uses
`buff_cast_skill_action_native.json` to join `buff_27_native.json`'s named
parent source/destination program to its selected action route. Its `caster`
and `target` are separately owned TargetSettings records, while `skillId`
composes the independently authenticated paired BlackboardString. Null wrappers,
null/empty payloads and noncanonical flag bytes retain their original states.
These are stored operands; evaluating a skill ID, selecting a caster/target,
accepting costs, interrupting or invoking a skill are separate consumer claims.
Unsupported nested target children refuse the action instead of closing it
through a matching parent name or candidate endpoint.

The independent names-only consumer groups in
`buff_action_consumers_native.json` prove the incoming owned CastSkill Data
reads, `caster` flowing to `GetFirstTarget.targetSettings`, and `skillId`
flowing to `ActionBlackboardExtensions.GetValue.param`. They also prove the
three flag reads and the named target-view/cast calls. The target-view operand
forwarding remains a separate obligation: the current reference-flow checker
excludes that callee's aggregate return ABI. Its false-IFix property path
returns the typed `CustomReturnType` enum through a complete return epilogue.

The separate `buff_cast_skill_consumer_flow_native.json` contract and
`buff_cast_skill_consumer_flow_native` loader authenticate a narrower local
completion program through `il2cpp.call_completion_return`. The actual
`TryCastSkillDuringAction` callee returns void. After it returns ordinarily,
CastSkill assigns true to AL and directly reaches the complete matching
frame restore and return, preserving that Boolean. The checked entry saves,
allocation, exit jump and every epilogue instruction exclude a partial
return-tail claim. This proves the selected compiled completion value; it
does not prove branch feasibility, skill acceptance or effects, and that
true value is not a success result returned by the void callee. Other exits,
flag forwarding and inherited cast information remain separate.

The maintained `buff_animator_param_action` reader and
`buff_animator_param_action_native.json` use the separate parent and child
programs in `buff_14a_native.json`. `endAction` and `paramAction` each have their
own independently nullable AnimatorParamAction span. That child's ordered
animator parameter, Boolean value, float value, integer value and typed
AnimatorControllerParameterType enum retain raw bytes/bits. The required final
enum precedes the next parent field; truncating it cannot borrow the parent's
name-payload boundary. Name encoding, action-on-end selection, receiver state
and animation effects remain unresolved. Complete root admission still needs
the current family and canonical original-byte gates.

The separate names-only animator consumer groups prove `OnEnd` reading the
incoming owned Data's `actionOnEnd` byte, and owner-getter calls in `OnEnd`
and `ExecuteInternal`. The false-IFix return-policy getter reaches the typed
`AlwaysReturnTrue` enum through a complete epilogue. These claims do not
establish the flag branch outcome or selected animator. The two nested
configuration operands, their helper/receiver ownership and actual parameter
writes still require independent flow proofs; a return-policy enum is not an
observed animation result.

Useful current differences have selected evidence owners: the icon's
`showDirectlyInHeadBuff` flag (`buff_icon_config_native.json`), RandomPointFinder's
`extent2D` (`finder_10_native.json`), DamageUnit's `damageTags`
(`buff_damage_action_native.json`), EffectAction's `bigEffectTarget`
(`buff_a2_native.json`) and Aura's faction, angle and height operands
(`buff_aura_heal_actions_native.json`). RandomPointFinder's extent is a
BlackboardVector2 with two BlackboardDouble children, not a raw Vector2. A
DamageUnit tag list has wrapped elements and must not borrow the packed root
GameplayTag array grammar. Declaration matches are useful candidates for
FinishGlobalBuffAction, CheckDistanceCondition, RecoverPoiseAction and
ShapeFinder; their selected named source/destination checks now pass against
`buff_03_native.json`, `buff_42_native.json`, `buff_128_native.json` and
`buff_7c_native.json`. Those checks still leave recursive child admission and
consumer behavior as separate obligations.

The maintained DamageUnit reader now composes positive `damageTags` through
the independently authenticated signed nullable list grammar in
`skill_damage_unit_gameplay_tag_list_native.json` and named GameplayTag elements
in `buff_aura_heal_actions_native.json`. Null elements carry one byte; non-null
elements carry their own one-member header and four scalar bytes. The Damage
contract binds this collection to its named source member and fails closed on
either missing proof. Skill keeps its own cost-list and tag-list receipts when
composing the same physical DamageUnit. Cost lists do not gain Buff admission
from this tag-list proof; tag names and effects remain unresolved.
For the separate `damageProcessors` member, selected reads in
`buff_damage_action_native.json` and `buff_damage_modifier_child_native.json`
resolve the same closed `List<DamageProcessorBase>` MethodSpec and actual native
helper. The maintained `buff_damage_processor_collection.py` now binds this
source to DamageUnit's own member and composes ordered processor elements through
their independent scalar, scale, text, attribute-modifier and calculation span
readers. Signed null and empty lists remain distinct. Original source hashes,
element endpoints and the following tag-list and remaining unit fields must
rejoin before admission; the root modifier's receipt does not stand in for this
different parent. The reviewed `buff_damage_processor_collection_native.json`
authenticates the shared reference-list count program and its registered Object
instantiation as a conditional grammar reference. Live inflated list/provider
selection is still unresolved. Unsupported variants and unproved null union
elements refuse; raw numeric, payload and flag bits do not establish damage
arithmetic or accepted mutations. Whole-root coverage requires the complete
family gate and canonical original-byte replay.

CheckDistanceCondition has a maintained named reader under
`buff_check_distance_condition_native.json`. Its two distinct TargetSettings
operands compose through their own original spans; the distance float, radius
inclusion and comparison flags remain raw stored operands. The selected action
route and named reads do not establish evaluated distances or a predicate result.

ShapeFinder's `shapeData` is `Beyond.Gameplay.ColliderShapeData`, not
HitBoxFinder's separate eighteen-member ShapeData. Its maintained reader in
`buff_selector_shape_finder_native.json` depends on the independently named
sixteen-member `buff_collider_shape_native.json`. Collider's center, extent and
rotation offset are raw Vector3 values; each selected direct reader and separate
registered entry proves twelve-byte input and cursor accounting. The complete
parent transfer loads the typed wrapper instance directly into RCX, then copies
eight bytes from one result slot and four from the next. This explicit
`struct_output_sources.py` destination profile has no invented getter call.
String keys, geometry bits, enum and flags remain unevaluated. Both parent and
child proofs are required; missing or different native inputs refuse even a
structurally readable finder. Whole-root coverage still requires the complete
family gate and canonical original-byte replay.

FixedPointFinder has a maintained reader under
`buff_selector_fixed_point_finder_native.json`, whose selected source windows
are owned by `buff_119_native.json`. The current finder route and SelectorData
union plan join the concrete wrapper independently of the action source that
first exposed it. Position is an inline twelve-byte read and eight-plus-four
copy; rotation is an inline sixteen-byte read and complete SIMD copy. Both
programs update the same buffered-reader cursor slots and forward the entire
temporary through the typed wrapper getter to the named field. Explicit
temporary-stack and destination-displacement declarations must match every
read/store instruction; a native value size alone does not prove either wire
width or transfer. `sampleRadius` composes its independent BlackboardDouble
receipt, and `snapToNavmesh` retains its original byte. Null union, null wrapper
and null radius are distinct. These stored geometry/radius operands do not
establish sampling, snapping, selected coordinates or a target entity.

RandomPointFinder now has a maintained named reader under
`buff_selector_random_point_finder_native.json`. Its selected selector branch,
generated destinations and closed source contexts authenticate the complete
finder and BlackboardVector2 record. Vector2's two independently read
BlackboardDouble children and the separate Vector3 child compose at their
original spans; flags and shape enum bits remain raw. This proves stored
operands, not random choices, navigation snapping or resulting coordinates.

PointFinder has a maintained named reader under
[`buff_selector_point_finder_native.json`](../../scripts/game_data/contracts/buff_selector_point_finder_native.json)
and [`buff_selector_point_finder.py`](../../scripts/game_data/memorypack/buff_selector_point_finder.py).
The current selector union route, source contexts and generated setter
transfers prove `positionOffset` and `rotationOffset` as two separate
BlackboardVector3 fields. Each vector owns an independent original byte
range and reuses the authenticated x/y/z scalar children; null vectors and
null scalar children remain distinct. Original finder spans also reparse
their enclosing direct SelectorData field, preserving the recorded tag,
subtype and exact field boundary. The maintained SelectorData composition
is also replayed on the same original parent ranges; its remaining two
lists are independently verified empty. Positive lists retain their own
separate evidence requirements. This is an `exact` stored component with
`conditional` composition: complete roots still require the full family
gate and independent original-root replay. Evaluated offsets, resulting
coordinates, selected points and runtime execution remain `unresolved`.

ContinuousFindTargetAction has a maintained recursive reader under
[`buff_continuous_find_target.py`](../../scripts/game_data/memorypack/buff_continuous_find_target.py)
and its reviewed
[`buff_continuous_find_target_native.json`](../../scripts/game_data/contracts/buff_continuous_find_target_native.json).
The source framing contract authenticates nineteen members and the required
terminal four-byte float read. Both Data and wrapper inheritance pass
through the FindTarget layer before the common AbilityAction base; every
parent edge and the declared instance-field owner are checked explicitly.
The common direct-store proof covers only the four common fields, while
the generated identities and source/setter joins cover the remaining
target-selection fields. The
[`direct_float_sources.py`](../../scripts/game_data/memorypack/direct_float_sources.py)
profile checks the complete buffered Single helper, the source result in
XMM0, preservation in XMM6, the typed cached-instance getter and the final
owned `findInterval` store. These transfers are `conditional` on coherent
references and ordinary Win64 returns; initialization, cast, refill and
failure branches remain outside that proof.

Original action ranges compose direction, selector and independent source
strings and retain the final float as raw bits. Existing child native
returns retain the authenticated frozen family scope in which they were
proved; the new parent is separately checked against current native bytes.
The maintained recursive dispatcher reproduces each complete component
receipt. This does not replace a new complete family gate or original-root
replay for the live batch. Evaluated targeting, timing and gameplay effects
remain `unresolved`; the narrow Skill first-timeline reader keeps its own
separate evidence scope.

The coherent frozen reader epoch containing ConsumeLayer, BindBounty,
ArcheryChip, PointFinder and ContinuousFindTarget has now passed the complete
original Buff family gate and independent gained-root replay. Each gained
root reproduces all thirty named fields, source identity, the full canonical
receipt and physical EOF from the original bytes. Existing exact roots do
not regress. Admission belongs to that immutable reader/native source epoch;
later SkillCastId zero-member integration and consumer work retain separate
scopes. This closes the whole-family/root gate for the captured component
batch, without proving selected runtime providers, evaluated conditions,
targeting, timing or gameplay effects. Changing counts and inventories remain
in the current generated progress and residual reports. Missing original
Skill evidence continues to block cross-family publication.

SaveHealValue now has a maintained stored-action reader under
[`buff_save_heal_value_action_native.json`](../../scripts/game_data/contracts/buff_save_heal_value_action_native.json).
Its generated six-member wrapper and selected native source/setter joins
name the four common action fields plus `finalHealKey` and `realHealKey`.
Each key has its own bounded nullable UTF-8 source receipt, preserving null,
empty and valid multibyte strings without borrowing the following field.
The recursive dispatcher and contract-dependency collector include the owner,
and original independently closed action ranges reproduce the same complete
component receipt. This is later component evidence; complete-family and
independent root replay remain necessary before additional root admission.
Names of healing keys do not prove blackboard assignment or healed amounts.

The next typed-list candidate, CheckSkillDamageType, has independently
authenticated wrapper/source/setter names, but those joins alone do not prove
its list count and element consumption. Enum naming and a four-byte converted
result are not a four-byte serialized-read proof; retain the list/provider
join explicitly until its framing is independently established. Channeling
requires a mixed output proof rather than a setter-only matcher. The common
fields reach base Data directly; the absence of setter calls does not mean
those fields are absent.

Channeling now has a maintained stored-action owner under
[`buff_channeling_action_native.json`](../../scripts/game_data/contracts/buff_channeling_action_native.json).
Its ten-member source order joins four common inherited direct stores, a
SequenceActionData `actionOnTick`, primitive `executeEachFrame` and
`maxCountPerTarget` stores through the typed cached-instance getter,
TargetSettings, and two Single interval setters. The checked source helpers
establish the buffered byte/DWORD/Single reads and cursor increments;
`mixed_action_output_sources.py` proves the explicit reader/wrapper aliases,
reference or XMM return transfers and owned destinations. Cached getter cold
paths, refill/error outcomes and actual provider selection remain outside the
normal-path proof.

Fresh independent target/sequence and zero-validator proofs compose original
Channeling ranges through the recursive dispatcher. An older zero-validator
cache lacking the current route set must refuse even when its native inputs
match; replacing that component requires a fresh actual return, never a
fabricated added route. Positive action/target children remain gated by their
own source epochs, and an unsupported descendant refuses the parent. Full
family and original-root gates still decide additional root admission. Stored
intervals, flags and counts do not establish tick scheduling, target iteration
or gameplay effects.

The later action batch now has a separate immutable source epoch containing
SaveHealValue, Channeling and the current SkillCastId zero-member route. The
complete-family gate compares against the admitted recursive-components epoch
without rewriting its source identities or receipts. Its snapshot includes the
ignored test sources and bounded fixtures as well as both dynamically loaded
native metadata/decoder helpers. Starting that gate admits no additional roots:
complete-family success, no regression and independent original thirty-field
source/EOF replay remain required. Generated launch and process records retain
the specific job handle; an observation timeout is not a reason to restart it.

RecoverPoiseAction likewise has a maintained reader under
`buff_recover_poise_action_native.json`. Its dispatcher join and named source
reads authenticate the parent, including the distinct `effectData`,
`recoverValue` and `target` fields. EffectActionCfg, admitted CalculationBase
variants and TargetSettings reuse their independent readers on original byte
ranges. Unsupported recursive children still refuse the action. These child
admissions require the complete family gate and canonical original-byte replay
before a surrounding Buff root gains coverage; actual recovery amounts,
selected receivers and effect playback remain unresolved.

The independent consumer claims in `buff_action_consumers_native.json` now
cover RecoverPoiseAction's direct target-resolution, `NewPoise` and effect
creation calls, and a `target` read through its proved incoming closed
`m_data` slot on a checked local compiled path. Its false-IFix return-policy
getter yields `CustomReturnType`; the separate Boolean `AlwaysReturnTrue`
method returns the owned `alwaysNext` byte only on false-IFix/non-null-Data
fallthrough. `owned_byte_returns.py` authenticates unsigned byte-to-EAX loads
and owned cold branch targets without relaxing the contiguous return epilogue.
These claims do not prove target forwarding, recovery arithmetic, accepted
poise writes or playback. The `healer`, `effectData`, `recoverValue`, `poiseType`
and `playHealEffect` read proofs still encounter undecoded local instructions.
An isolated byte-XOR/long-NOP decoder trial reduces that frontier but reaches
the bounded local-path budget without proving these reads; it remains outside
production. Refusal is not proof that those fields are unused.

Stack effects require a separate concrete-value composition. The selected
wrapper declarations derived by `wrapper_members.py` expose
`StackBuffEffectData.effectActions` as a list of concrete
`EffectAction.EffectActionData`, rather than the abstract action union. Do not
prepend an invented action tag to reuse that union reader. The current
`buff_a2_native.json` reader includes an inline DWORD source for priority;
the maintained concrete record validator proves that scalar program and the
other named source/destination members. Priority is an Int32 enum, and its complete input read,
cursor accounting and full DWORD store reach the immediate parent's typed
AbilityActionData slot through the wrapper's inherited instance field. It is
not a helper call or a child-class-owned field. The maintained
[`struct_output_sources.py`](../../scripts/game_data/memorypack/struct_output_sources.py)
now checks this explicit scalar program, with the concrete record declared in
[`buff_effect_action_data_native.json`](../../scripts/game_data/contracts/buff_effect_action_data_native.json)
and authenticated by
[`buff_effect_action_data.py`](../../scripts/game_data/memorypack/buff_effect_action_data.py).
The profile independently checks the ref-reader/ref-wrapper ABI, Int32 enum
underlying type, retained pointer aliases, actual wrapper ancestor reference,
four-byte input and cursor accounting, and full store into the immediate
Data parent. It neither fabricates a helper call nor validates enum meaning.
Collection provider/registration joins and complete original-span composition
remain open.
The compact stacking contract therefore keeps positive interiors opaque.

The current stacking source contexts identify `ReadArray<StackBuffEffectData>`
and `ReadPackable<List<EffectActionData>>`. The list's concrete element definition
is exactly the reference type held by the generated EffectActionData wrapper,
whose selected reader remains owned by `buff_a2_native.json`. A complete selected
`GenericEntries` table lookup finds no exact closed registration for either
source context, and no registered generic pointer at either observed direct
helper target. Other instantiations of those method definitions are recorded.
Treat these as direct-call helper observations: their typed source joins remain
valid, while array/list helper programs, adapter conversion flow and element
formatter dispatch require independent checking. A nearby registered body or
an Object instantiation cannot supply the missing helper/element connection.

The selected generated initialization also constructs the original-value
adapters for StackBuffEffectData and concrete EffectActionData, retaining each
adapter object into `RegisterWrap` with its exact original type key. The
registration, conversion-interface return type, concrete formatter vtable and
forwarded reader identities pass the shared
`il2cpp/formatter_composition.py` checker. Stack's own `RegisterFormatter`
preserves its allocated `ListFormatter<EffectActionData>` into a registration
whose closed List argument and element pointer are exactly those of the source
field. These are static argument-flow and identity proofs, beyond names or
nearby generic registrations. Complete method-owned RGCTX ranges expose the
source-to-inner-reader and provider/formatter type propagation under ordinary
inflation. They do not substitute a registered Object template for the actual
direct helper, select a live cache return, prove the adapter's conversion
program, or admit positive original array/list spans. Keep the concrete
eighteen-member reader's inline scalar proof separate until those collection
programs, recursive children and following stacking tail are checked.

The actual array helper's normal buffered path also supplies a direct count
and loop witness: it loads four bytes into the count register, advances the
input and cursor counters by four, distinguishes minus-one null and zero
empty counts, and passes ordered reference-array element destinations with
the reader to the retained formatter receiver. Its selected source context
forwards the same owned generic parameter into the inner array reader, whose
provider slot is `GetFormatter<T>`. This is conditional on ordinary inflation
and the available-buffer cursor path. Keep refill/error branches, provider
success, adapter conversion and full original child spans as separate claims;
this normal-path witness alone does not admit a positive Stack root.

StackBuffEffectData's separate one-member record also passes the shared named
source/destination checker: its concrete list source result reaches the
`effectActions` setter through the non-null wrapper guard, and the selected
reader compares the member count with one. This isolated record is independent
of the EffectActionData record and its priority source. Positive list grammar,
object header/null parity and complete original parent spans still require
their own composition before the compact stacking reader can admit them.

Keep concrete wrapper return programs, object header/null paths, inherited
instance/cache relationships and generic adapter dispatch as separate proof
obligations. A wrapper's typed `GetValue` signature or captured constructor
body cannot establish which adapter invokes it. Likewise, metadata type
pointers can differ because field and return attributes differ while naming
the same reference definition: check the definition, reference kind and
decorations independently rather than requiring pointer equality. The
maintained source validator's ancestor check does not admit a collection or
prove the concrete getter's cache/class-check program.

For the concrete EffectActionData wrapper, the next conversion proof can be
split at two independently checkable points: the constructor's original
reference transfer into the inherited instance and concrete cache slots, and
the getter's non-null cache-equality fast path. Isolated current-body probes
have located those paths, but the helper's allocation and intervening memory
effects, cache refresh/cast branches and actual generic adapter invocation
remain outside the maintained concrete record contract. Preserve that boundary
when converting these leads into a reviewed profile; neither the constructor
signature nor a fast return admits a positive Stack collection.

Independently named processor-list children can succeed while a surrounding
sequence still refuses another action. The current source/dispatcher joins
in `buff_f4_native.json` and `buff_186_native.json` authenticate MoveGaitAction
and TriggerCharSpellInflictionEvent respectively. The former's six stored
members include separate `maxGait` and `minGait` enum operands; original child
spans reproduce their raw bits through the shared bounded Reader. The latter's
seven members include an independently typed `eventSource` TargetSettings,
`eventType` and `inflictionType`. The source/destination checker and current
union dispatcher establish these identities beyond a historical name match.
The maintained
[`buff_leaf_actions.py`](../../scripts/game_data/memorypack/buff_leaf_actions.py)
and its reviewed contract preserve MoveGait's `maxGait` before `minGait`;
[`buff_spell_infliction_action.py`](../../scripts/game_data/memorypack/buff_spell_infliction_action.py)
and its reviewed contract compose the independent TargetSettings child,
followed by both required four-byte enum operands. A target endpoint cannot
finish this action, even when the target is null. Original action spans now
reproduce through these independently native-gated readers. Complete sequence
ownership and root admission still come from the full family and canonical
original-owner replay gates. Stored gait limits and event operands do not
prove movement changes, event dispatch or spell attachment.

CheckSkillCastId is another independently named leaf in
[`buff_leaf_actions_native.json`](../../scripts/game_data/contracts/buff_leaf_actions_native.json).
Its current source in
[`buff_73_native.json`](../../scripts/game_data/contracts/buff_73_native.json)
ends after the four inherited operands: `isEnable`, `priorityLevel`,
`priorityOffset` and `serverActionIndex`. There is no additional serialized
skill or cast ID field. Historical schema-pack tag numbers cannot select this
reader: current dispatcher/type identity and source windows must agree first.
[`inherited_action_sources.py`](../../scripts/game_data/memorypack/inherited_action_sources.py)
proves the selected reader/ref-wrapper argument flow, buffered Boolean
normalization, DWORD reads and cursor accounting, and each inherited setter's
load of the metadata-owned base Data reference followed by its typed field
store. The stored Boolean byte remains raw in the receipt even though the
selected native helper normalizes a nonzero operand. These are conditional
ordinary paths, with Win64 nonvolatile preservation across returning children;
refill/error callees, acquired runtime cast identities, comparison result and
condition execution remain unresolved. A successful original leaf or selected
parent replay still requires the full current family and canonical root gates
before any whole-root gain is published.
Original-parent replay also demonstrates that passing this leaf can expose a
later unsupported action in the same sequence. The exact leaf boundary must
therefore stay separate from the enclosing sequence and root classification.

SkillAffixAction has a separate current reader and dispatcher identity in
[`buff_leaf_actions_native.json`](../../scripts/game_data/contracts/buff_leaf_actions_native.json),
with its source and inherited-helper windows in
[`buff_164_native.json`](../../scripts/game_data/contracts/buff_164_native.json).
Its complete stored leaf also ends after the four common inherited operands;
there is no additional serialized affix identifier. The shared inherited-source
validator checks this parent's own argument and return bridges, buffered
primitive cursor programs, and typed base-Data setter destinations. A matching
member count or another leaf's helper identity is not the admission evidence.
Skill-affix lookup, handler selection and resulting effects remain unresolved.

CheckTargetContains has a maintained Buff recursive owner in
[`buff_check_target_contains_action.py`](../../scripts/game_data/memorypack/buff_check_target_contains_action.py),
reviewed by
[`buff_check_target_contains_action_native.json`](../../scripts/game_data/contracts/buff_check_target_contains_action_native.json)
and the current source windows in `buff_7e_native.json`. After the common
inherited prefix, `childTargetSettings` and `parentTargetSettings` each have
their own typed source context, read-return bridge and generated setter. Equal
TargetSettings types do not merge the two stored objects: each nonnull child
must independently compose the existing recursive target owner at its original
absolute endpoints. A null action wrapper, a null child setting and a null
parent setting stay distinct. Passing the first setting cannot finish the
condition, and unsupported children refuse it. Stored configuration does not
establish acquired target sets, containment results or condition execution.

The current CheckSkillCastId consumer's object-filter call also joins the
complete reference-filter program already owned by
[`buff_effect_line_center_consumer_native.py`](../../scripts/game_data/buff_effect_line_center_consumer_native.py)
and its
[`consumer contract`](../../scripts/game_data/contracts/buff_effect_line_center_consumer_native.json).
This helper's normal return selects the saved incoming reference or null;
its actual child target joins `il2cpp_class_has_parent` and the complete
[`class ancestry proof`](../../scripts/game_data/contracts/buff_formatter_class_ancestry_native.json).
The ancestry interpretation retains the coherent initialized-class, positive
prepared depth, valid storage and ordinary-return conditions. Reusing this
same body avoids a second filter implementation. It does not identify the
consumer's live object/class, prove type-cell initialization, establish the full condition CFG,
or prove the skill-cast comparison result.

The context-adapter investigation must distinguish a stored selector from a
metadata type-definition index. The selected creation body in
[`buff_formatter_class_creation_native.json`](../../scripts/game_data/contracts/buff_formatter_class_creation_native.json)
copies the dialect's inserted anonymous DWORD from its saved metadata-record
source into the allocated class object. A separate saved-register, adjacent
read/store and normal-return dominance check connects that copy to the
adapter's DWORD load; the column's semantic field name remains unresolved.
The adapter's distinct cases have unique current stored-column rows for
Ability, Buff, SkillHighlightEnvironment, ComboSkillEnvironment and GlobalBuff.
Their receiver-relative QWORD loads agree with each type's instance `context`
backing field and its registered getter's closed load/return entry. Field
ownership uses the same explicit static/value-type checks as
[`NativeReferenceContext`](../../scripts/game_data/il2cpp/reference_layouts.py).

This is a conditional named-field connection: the actual compatible metadata
source/index must remain stable, the adapter receiver's class must be that
allocation, children must obey ordinary returning Win64 register behavior, and
no child or alias may change the selector before the adapter reads it. The
adapter's fallback receives the original input in RCX and R8 and forwards a
fresh normal child RAX result. The complete adapter, creation-selector copy,
named Context fields/getters and fallback are maintained by
[`buff_condition_context_adapter.py`](../../scripts/game_data/memorypack/buff_condition_context_adapter.py)
and its
[`reviewed contract`](../../scripts/game_data/contracts/buff_condition_context_adapter_native.json).
This owner authenticates explicit GameAssembly/metadata/Unity inputs and its
source closure before and after proof; missing or mismatched inputs emit no
program summary. The reusable control/column readers live under `il2cpp/`.

The fallback captures its comparison pointer before its preparation call,
then freshly loads an unsigned WORD limit and record-array pointer. Its guarded
scan selects the first matching record and cannot wrap its WORD index on a
reached continuing iteration. On a match, it adds the selected method slot to
the record DWORD at DWORD width, sign-extends that result, applies the checked
pair bias/stride and adds the saved class pointer. The miss path obtains a
fresh pair from its actual resolver call. Both paths load the pair's target
and method-info QWORDs, restore the normal Win64 frame/nonvolatile state and
tail-transfer the original object with the fresh method-info argument.
The captured on-disk type-usage encoding joins the current `IActionEnvironment`
interface declaration; the physical resolver and inline-pair slot joins its
unique declared `get_context` method. This is a stored declaration join,
conditional on proper runtime cell initialization and coherent class/pair
storage. It does not identify a live pair or prove index capacity, preparation
or resolver effects/termination, the actual indirect target, the full
CheckSkillCastId CFG, live context identity or comparison result.

The further source join is maintained by
[`buff_condition_context_dispatch.py`](../../scripts/game_data/memorypack/buff_condition_context_dispatch.py)
and its
[`reviewed dispatch contract`](../../scripts/game_data/contracts/buff_condition_context_dispatch_native.json).
The creation body stores the fresh allocator return into its own QWORD self
field and copies the saved metadata record's named `interface_offsets_count`
WORD into the later record-scan count. Both direct stores dominate every normal
local creation return. The metadata count columns are checked against the
original bytes for every type; the allocator size expression uses the distinct
named `vtable_count` WORD. Each selected Context type has a unique static
`IActionEnvironment` interface-offset record whose effective method slot points
to that type's previously checked getter. These static pairs fit the recorded
allocation-request geometry. An allocator request does not prove allocation
capacity, nor does a static interface record prove the prepared runtime array.

The context caller's actual preparation/resolver entries join the existing
[`dispatch fallback proof`](../../scripts/game_data/contracts/buff_formatter_dispatch_fallback_native.json)
and its direct child's complete
[`resolver scan proof`](../../scripts/game_data/contracts/buff_formatter_resolver_scan_native.json).
The entry first loads the self pointer; its preparation tail has stored-byte
guards and passes a caller slot initialized with a global address by reference.
The subsequent child reloads that slot, which the intervening child may change.
The resolver reloads a fresh class QWORD from the original object: equality with
the outer caller's earlier saved class still requires stable object-header and
alias/child behavior. Its direct search returns zero on a null query parameter
context or scan exhaustion. A nonzero result is forwarded; otherwise a guarded
alternate result may be forwarded after its continuation, while failure calls
the actual failure helper with `INT3` as its normal-call continuation. That failure is not a safe
normal null result. Full local control and normal-transfer/source joins do not
prove initialization, external child effects or termination, class/pair
identity, the full condition CFG or actual condition evaluation.

The selected preparation writers are now maintained by
[`buff_context_publication.py`](../../scripts/game_data/memorypack/buff_context_publication.py),
its
[`reviewed publication contract`](../../scripts/game_data/contracts/buff_context_publication_native.json)
and
[`context_publication_sources.py`](../../scripts/game_data/il2cpp/context_publication_sources.py).
The creation program also stores its saved metadata-record pointer and copies
the named `vtable_count` WORD into the later method-pair loop count. These
unique direct stores dominate every normal local creation return; child,
alias and concurrent mutations remain separate conditions. The stored range
starts, WORD counts and interface-offset/vtable header sections are checked
against the original metadata bytes and bounded table ranges for every type.
This does not establish the identity of live metadata/header/base cells.

Both selected interface-array branches have complete original-byte grammars
within the authenticated second preparation CFG. They publish a fresh normal
allocation-like return, then fill distinct DWORD offset and QWORD lookup-return
parts of each record. The linked branch obtains a fresh source receiver and
uses a separately reloaded linked pointer for its inflation argument; equality
with the earlier input is not assumed. Its early zero-count/already-present
skip avoids the saved-address reload, while the path that uses the WORD loop
counter reloads that address afterward. The ordinary branch keeps its original
receiver. Both loops use unsigned WORD continuation guards, so a continuing
iteration cannot wrap the counter. Counts and array pointers are loaded again
after children: an initial allocation request does not prove that subsequent
indexed writes fit its actual capacity.

Every instruction in that second preparation body now belongs to exactly one
checked semantic fragment, including its linked-method, special, restoration
and common completion paths. Actual branch targets join fragment labels;
the linked-method fragment additionally admits the array-skip entry that
retains the original incoming address instead of reloading its saved home.
Complete physical coverage still depends on normal child returns and compatible
storage; it does not prove the callees' meanings or termination.

The ordinary method-pair branch is selected only with the initial linked
pointer and special byte clear, in addition to the initial ready/blocked
guards. It reads the stored encoded vtable DWORD and stores the fresh normal method
lookup return into the pair's second QWORD before selecting its first QWORD.
A null lookup return substitutes a stored address for the second word. A null
return or null direct-target field selects the fallback target address;
otherwise the actual flag and global-pointer guards select the direct or
alternate target field. Completion freshly ORs the ready byte and blocked
mask. These are physical source/write and local-control proofs, not the
identities of lookup returns or callable targets. Publishing the array pointer
before its separate record writes does not prove that other readers observe
a complete array or pair.

The linked method-pair branch recursively prepares its captured source, then
copies a freshly read source count into the original receiver. Its lookup
candidate may be rewritten by a carrier/inflation path or a separate stack
tuple containing the candidate, a freshly read linked-context pointer and a
zero word. The former clears the full integer flag argument; the tuple path
sets only its low byte, leaving the upper register value unproved. The actual
false-flag branch repeats the candidate's class-pointer guard. The rewritten
candidate is stored into the pair before the guarded helper and target
selection. Direct, alternate, helper-return and fallback targets have distinct
checked source paths; the helper-return path preserves its fresh return while
computing the pair index. These are candidate and target byte flows, without
runtime method or callable identity.

The linked branch also has an actual conditional post-creation write to the
anonymous selector DWORD read by the Context adapter. With the sentinel still
present, it follows two guarded helper returns and a fresh nested pointer,
then copies that nested receiver's selector DWORD into the original receiver.
The first helper's result must be nonnull and differ from its saved input.
This proves a possible native selector mutation; its value's meaning, nested
class identity and equality across later fresh reads remain open.

The special branch passes the original incoming address to its helper, then
reloads the source pointer before its lookup. Equality with the pre-call source
is not assumed. It stores the fresh lookup result and chooses a flag bit using
the actual kind branches and a selected query result's high bit. Unknown kinds,
the null-address branch and the selected high-bit path copy the freshly read
source flag bit; they do not unconditionally clear it. The final masked merge
replaces that bit and preserves the other receiver bits. Both subsequent
children receive the original receiver. All outgoing incoming-address handoffs,
including the recursive and linked-method calls, have checked register/home
origins; the pointed slot's contents and child mutations are not proved.

Lookup/inflation/special child effects and termination, runtime interface/class
binding, recursion, allocator capacity, concurrent visibility and whole
condition execution remain open. Native, metadata, Unity and source drift
fail closed, independently of the unchanged complete Buff root reader.

PlayAnimation and JumpTo now have a maintained recursive composition in
[`buff_animation_sequence_actions.py`](../../scripts/game_data/memorypack/buff_animation_sequence_actions.py),
declared by
[`buff_animation_sequence_actions_native.json`](../../scripts/game_data/contracts/buff_animation_sequence_actions_native.json).
The current source windows in `buff_115_native.json` and `buff_d9_native.json`
independently authenticate their named destinations and dispatcher identities.
PlayAnimation's `animName` and `startTimeBlackboardKey` additionally use the
independently proved UTF-8 source helper on their original byte ranges; null,
empty and embedded-NUL strings stay distinct, while invalid UTF-8 refuses this
profile. Float operands preserve all original bits. Its `onEndAction` composes
the shared independently owned SequenceActionData, including positive recursive
actions and both terminal flag bytes. JumpTo composes its separate
`conditionAction` sequence and then requires the following Int32 `destFrame`;
the sequence endpoint cannot finish the action. Complete root admissions pass
both the full Buff family gate and independent canonical original-owner replay
through every root field, source ID and physical EOF. Animation playback,
callback execution, condition results and actual frame jumps remain unresolved.

MergeTargetAction has its own maintained
[`stored-action reader`](../../scripts/game_data/memorypack/buff_merge_target_action.py)
and
[`reviewed native contract`](../../scripts/game_data/contracts/buff_merge_target_action_native.json).
The historical schema identifies the older action but cannot select the current
union route or field count: the current source includes `mergeHittableTargets`
between the inherited operands and `targetGroupKey`. Its separate `targets`
field has a current closed `List<TargetSettings>` source context. Each reached
nonnull element requires an independent recursive target receipt on its own
original span; one element's receipt cannot close a different element. Null
wrapper, null/empty UTF-8 key, null/empty list and null target elements stay
distinct, and stored Boolean and integer bits are preserved. The actual string
source is joined to the existing UTF-8 helper proof. Bounded original action
replays validate this composition; integrating it changes the recursive reader
and requires a fresh full-family gate plus independent gained-root replay
before admitting new complete roots. Provider choice, inherited/owned setter
execution, evaluated flag/key, selected entities and merge or replacement
effects remain open.

[`TyphoeaArcheryChipDataAction`](../../scripts/game_data/memorypack/buff_archery_chip_action.py)
now has a current named stored parent under its
[reviewed contract](../../scripts/game_data/contracts/buff_archery_chip_action_native.json).
The inherited byte/three-DWORD prefix is followed by separately stored key
payloads and save-flag bytes in the generated setter order. Every key has an
independent nullable length and source-string receipt; a null or empty earlier
key does not remove later flags or the final key length markers. The parser
reserves the minimum required suffix while reading each payload, preventing
an earlier length from borrowing those required fields. Original field spans
retain raw flag/scalar bits and null/empty string distinctions.

The parent joins the existing selected UTF-8 helper proof and current extended
union route, rather than using an old schema's ordinal or interpreting key
names as cross-file links. This is stored configuration only. Full family and
original-root replay remain necessary before root admission, and key lookup,
projectile/bounce/split/trajectory/affix setting evaluation and writes remain
unresolved.

The historical schema also guides remaining action work when a current generated
wrapper still has the same named field order. Its union membership must still be
recovered independently. The current reviewed source windows for
`ChangeSkillAction`, `CheckWeaponTypeCondition`, `SaveBuffLifeTime`, `SetWeaknessAction`,
`TeleportAction`, `CheckEnemyRank`, `AddDynamicCcsAction` and
`TriggerSpellBurstEventAction` can be joined to generated setter destinations
with the maintained
[`named-source checker`](../../scripts/game_data/memorypack/named_native_records.py).
These are direct stored-name joins pending separate child, provider, original
action and complete-root admission, except for the maintained Teleport, MoveTo,
SpellBurst, target/mask and skill/lifetime/weakness compositions described here.

Fresh selected native/source checks also join `AddDynamicCcsAction`,
`RefrainObtainUsp` and `CheckSkillDamageType` to their ordered reads, generated
setter declarations and current union routes. Their reviewed source owners are
[`the dynamic-camera windows`](../../scripts/game_data/contracts/buff_08_native.json),
[`the USP windows`](../../scripts/game_data/contracts/buff_12a_native.json) and
[`the skill-damage-type windows`](../../scripts/game_data/contracts/buff_74_native.json).
Historical union numbers are not aliases for these installed types: even when
the runtime type and ordered names agree, membership must be independently
joined to the installed dispatcher. Original first-stop action spans are
rejoined separately and remain staged, without changing complete-root coverage.

The camera parent has separate `enterConditionsOr` and `leaveConditionsOr`
lists of `CameraControlState.TransitionConditionAnd`. Each group's `and` member
is a separate nullable list of `CameraControlState.TransitionCondition`.
Current child reader calls and generated destinations name its five operands
as `boolValue`, `buffValue`, `comparator`, `conditionType` and `floatValue`;
their stored forms are a byte, signed-length byte payload, two DWORDs and raw
float bits. The two parent-list contexts and the group's inner-list context
independently resolve the same runtime element owners as those child readers.
Closed list types alone do not establish provider selection or collection
cursor behavior. The first-stop originals and the larger set of camera action
intervals owned by accepted residual root fields currently show empty outer
condition lists. This bounded observation supplies no positive-element replay
and does not prove that other unparsed fields or client data lack conditions.

`RefrainObtainUsp` reads `clearUspOnEnd`, a `GameplayTagList` wrapper and a
required terminal `TargetSettings`, after the inherited action operands.
The tag-list object header, its own nullable list and each tag wrapper remain
separate from a direct DWORD array. `CheckSkillDamageType.damageTypeList` is
instead a concrete `List<DamageType>` whose element context joins the
independently reviewed DWORD source; enum metadata size alone is not a wire
width proof.

The reached camera scalar, vector and curve fields now join their closed source
contexts to the independent
[`BlackboardDouble`](../../scripts/game_data/memorypack/buff_adding_cooldown.py),
[`BlackboardVector3`](../../scripts/game_data/memorypack/buff_effect_vector_child_receipt.py)
and [`AnimationCurve`](../../scripts/game_data/memorypack/animation_curve.py)
owners. Original field intervals close independently, preserve raw operands and
reencode the original bytes. Non-curve stored trees also require complete named
source-receipt coverage; metadata plans alone do not admit their interiors.
The USP tag and target fields separately join the independently owned tag and
recursive target readers on their original intervals. The
[`tag owner`](../../scripts/game_data/memorypack/buff_aura_heal_actions.py)
provides a standalone GameplayTagList reader shared with HealAction, preserving
the object header, nullable list count and each nullable tag wrapper. Its parser
fixtures exercise positive entries without treating them as installed samples.
These child receipts remain staged below parent and complete-root admission;
the camera condition collections and damage-type collection still need their
independent element/loop compositions before dispatcher integration.

The ordinary `CheckDamageType.damageType` reader supplies a separate physical
DWORD-source proof for the same concrete element type used by the skill-damage
list. Its authenticated closed source context, actual CALL and generated setter
join to the complete
[`buffered DWORD transfer`](../../scripts/game_data/memorypack/buffered_dword_sources.py),
using the reviewed helper window in
[`its existing window owner`](../../scripts/game_data/contracts/buff_0c_native.json).
Under coherent readable reader storage and a signed available length of at
least four, that program reads four source bytes, updates the pointer, remaining
length and both counters, and returns those bits. Cold refill/error targets
remain outside this proof. The independently compiled `ReadUnmanaged<DamageType>`
registration is absent; the physical source transfer does not invent that
identity or establish the skill-damage list's selected element formatter.
Complete-family and independent original-root replay remain subsequent
admission gates. These stored names and transfers do not prove camera transition
evaluation, USP suppression or a damage predicate.

The reviewed
[`camera, USP and damage source contract`](../../scripts/game_data/contracts/buff_camera_usp_damage_actions_native.json)
collects the current named parent/condition readers and the independent scalar
damage-type source. Its
[`source validator`](../../scripts/game_data/memorypack/buff_camera_usp_damage_source.py)
also checks the generated formatter-registration programs. Both outer camera
fields pass the same concrete list key to `Register`; the group's inner list
registers its own concrete condition element. The skill-damage action registers
`ListFormatter<DamageType>` for its list and `UnmanagedFormatter<DamageType>`
for the scalar key independently observed in `CheckDamageType`. These joins
compare actual generic type pointers, rather than matching names or nearby
addresses, and have been independently replayed from the current source
contexts.

The shared
[`registration-flow checker`](../../scripts/game_data/il2cpp/formatter_registration_flow.py)
owns the complete selected allocation/constructor/Register argument program,
including both an ordinary call and a restored-frame tail transfer. Under
non-null typed allocation, normal constructor return and the native calling
convention, it preserves that allocated reference through both calls. This is
static argument-flow evidence: constructor effects, registration/cache mutation
and the actual formatter-provider result remain unresolved. It does not select
a compiled collection body or establish serialized element grammar. In
particular, the independently compiled integer unmanaged reader is not a
substitute for a missing damage-type entry, and output-slot size does not prove
wire width. Positive camera condition replay, the damage list's element/loop
composition and recursive parent/root admission remain separate gates.

An independent integer-list witness now has its own
[`reviewed control contract`](../../scripts/game_data/contracts/buff_value_list_control_native.json)
and [`native owner`](../../scripts/game_data/memorypack/buff_value_list_control.py).
Complete parent triples in the declared PE exception directory establish its
primary and chained code ranges; adjacency is not used as ownership. The
selected buffered paths cover the null sentinel, an existing empty list and a
positive spare-capacity loop, including an identical repeated iteration. The
header reads a signed DWORD and checks total-minus-consumed against the count,
without multiplying that count by a presumed element width. The null sentinel
clears the output pointer on the selected unset-barrier path. Reuse increments
the list version and clears its count before the signed positive-count guard;
that route does not establish universal rejection of other negative counts.
Each positive iteration zeros a DWORD output slot, passes the original reader
and that output to the element formatter, appends the returned word, then
compares its loop index with the separately saved header count. A child output
overwrite therefore does not replace the loop bound.

The independent `UnmanagedFormatter<int>` entry separately proves a buffered
DWORD source load, by-reference DWORD output, all cursor updates and normal
return. The
[`value-list source checker`](../../scripts/game_data/memorypack/value_list_sources.py)
keeps that source proof distinct from the list's runtime output/array stride.
Native type flags are retained while checking primitive kind and the byref bit;
an unrelated set flag is not evidence of a byref argument. Current damage-type
list and scalar registration keys still join the same concrete source element,
but the independent compiled damage-type list and unmanaged entries remain
absent. The integer witness does not fill those gaps or supply a live formatter
selection. Allocation, growth, refill, barriers and helper effects remain
outside the selected normal programs, and positive stored damage/camera
composition and complete-root admission still need their own proofs.

The anonymous method-carrier bridge has a separate
[`reviewed control contract`](../../scripts/game_data/contracts/buff_method_carrier_control_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_method_carrier_control.py)
and [`complete program checker`](../../scripts/game_data/il2cpp/method_carrier_control.py).
The encoded method input splits into high kind bits and a shifted, masked
index, with its low bit discarded. The complete program distinguishes the
plain-index tail, indexed-carrier lookup with a cleared flag, the single
anonymous static-address case and zero returns. These physical cases do not
name metadata usage kinds or prove child table bounds.

Carrier inflation sends its two child pointers and the same incoming context
to a child helper, then retains the returned QWORDs separately. Its complete
recursive probe writes neither RDX nor R8 nor any alias and calls only itself.
Induction over finite normal returns therefore proves full register
preservation, rather than assuming volatile Win64 registers survive a call.
This preserves the second child result through the first probe and the freshly
loaded DWORD limit through the second. A nonzero QWORD gate bypasses the
probes; otherwise signed DWORD comparisons reject a result above that same
limit. The surviving composition tail receives the original carrier's current
first QWORD and both opaque child results. Child identities, termination and
composition effects remain separate obligations.

Full parent triples establish the three complete programs' physical ownership.
Their incoming publication calls are joined by actual current bytes and owned
ranges. Source drift in the older full publication receipt prevents reusing
that receipt as a current semantic proof; this narrower control proof does not
repair it. Cache-miss table meanings, concrete reference/value sharing, current MethodInfo
and provider identity, positive stored elements and root admission remain open.

Cache-miss resolution now has its own
[`reviewed pointer-transfer contract`](../../scripts/game_data/contracts/buff_method_carrier_resolution_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_method_carrier_resolution.py)
and [`complete-control and selected-flow checker`](../../scripts/game_data/il2cpp/method_carrier_resolution.py).
The complete miss, selector and registration-projection bodies have strong
exception-family ownership, checked local edges and fixed normal frames.
Selected normalization slices pass the two context pointers separately, save
their opaque results, and freshly read the lookup bounds. This does not yet
prove the whole table-search semantics or the normalized argument identities.

The projection checks primary and invoker indices unsigned against DWORD
counts, then sign-extends them for addressing. Nonnegative accepted indices
require counts below the signed boundary. The adjustor sentinel reuses the
primary pointer; any other adjustor index has no local bounds check and needs
independent registration-row validation. Both projection outcomes return the
original output address. They write three QWORDs and one flag byte, leaving
seven padding bytes untouched; the selector's all-miss path instead clears the
entire four-QWORD output. The runtime registration cell's startup binding is
still a separate obligation.

The caller reads the whole output aggregate but tests only its flag byte.
Vector shifting and the low-byte test therefore do not make the padding part
of the flag predicate. Initial pointer stores, the zero-primary static
fallback, the conditional opaque adapter result, and the saved tail vector's
reload across that adapter call are checked directly. The destination's
`0x08` flag bit depends on the aggregate flag and an opaque predicate's low byte;
the `0x10` bit uses that newly formed bit plus fresh source-flag and primary
pointer reads. A conditional extended pointer write and a locked QWORD
counter increment are also present. Opaque children may mutate destination
fields, so later reads are not treated as preserved earlier values. These are
conditional static transfers, not evidence of execution, concrete generic
sharing, a live provider, whole method creation or Buff root admission.

The two normalization helpers and their shared stack probe now have a
[`reviewed normalization contract`](../../scripts/game_data/contracts/buff_generic_normalization_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_generic_normalization.py)
and [`full program checker`](../../scripts/game_data/il2cpp/normalization_control.py).
The bytes after the first helper's terminal return form a guarded DWORD jump
table, not extra instructions. Exact code/data partitioning, all table targets
and guard dominance are checked within the complete exception-owned ranges.

The stack probe reads a QWORD through the runtime GS base, masks only a WORD
of its working address and conditionally touches pages. That WORD operation
preserves the upper register bits. Its complete body calls no other helper and
writes no alias of RAX, RCX, RDX or R8, so these full registers survive finite
normal returns. This explicit preservation is needed because the callers use
RCX or R8 as allocation size and reuse RDX after the probe. The zero-extended
DWORD count, pointer stride and rounding establish an aligned size; null and
allocated frame paths join through RBP restoration. Stable input counts and
valid disjoint storage remain conditions, and allocation success is not observed.

The first normalization reads the two-level kind and descriptor representation,
collapses selected reference-shaped kinds, and gates the underlying-kind
projection on the first byte of a freshly loaded configuration pointer. Its
guarded table selects anonymous class cells before the recursive generic-kind
path and opaque argument interning. A matching scalar width therefore does
not establish concrete enum sharing. The second normalization reads the
original argument count but not its argument array: descriptor start plus
ordinal selects a metadata record or a sentinel, and an opaque DWORD
classification chooses among three fresh cells. Non-sentinel metadata indices
have no local bounds check. Runtime configuration values, class-cell identities,
constraint meaning, concrete DamageType sharing and provider selection are
separate joins; the original root-admission scope is retained.

The selected initialization writer inputs now have a
[`reviewed producer-input contract`](../../scripts/game_data/contracts/buff_normalization_producer_inputs_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_normalization_producer_inputs.py)
and [`physical block checker`](../../scripts/game_data/il2cpp/normalization_producer_inputs.py).
The complete owned instruction inventory authenticates the selected contiguous
configuration-pointer and class-request blocks. Local direct branches cannot
enter their interiors; indirect or external entry is not excluded. The writer
uses a static configuration image whose first byte is nonzero. This is an image
input, not an observed live configuration value or successful initialization.

The underlying-kind table's signed and unsigned integer cases correspond to
requests for the `System.*Enum` placeholder classes. In particular, the
kind associated with Int32 selects the cell whose initializer requests
`System.Int32Enum`; matching scalar width alone would miss this distinction.
Name and namespace literals reach the same lookup helper before its return is
stored into the selected cell. Most image arguments are fresh cell reads; the
Object request retains an earlier RCX image input, whose origin remains a
separate condition. Request names do not establish the returned class identity
or unchanged runtime cell contents.

Current metadata and independent compiled registrations contain
`ListFormatter<System.Int32Enum>` and `UnmanagedFormatter<System.Int32Enum>`
candidates. Their complete exception-owned bodies are captured, including cold
ranges. These candidates guide the remaining DamageType composition; they do
not select its live formatter. The fully shared class/struct request names have
no exact matching metadata TypeDef in this build, so their producer results
require another proof rather than a name-based join. Class lookup returns,
concrete underlying-enum composition, cache/provider selection, positive stored elements
and parent-reader integration remain open.

The independent enum candidates now have a
[`reviewed selected-control contract`](../../scripts/game_data/contracts/buff_enum_list_control_native.json),
[`explicit native owner`](../../scripts/game_data/memorypack/buff_enum_list_control.py)
and [`header/list/bridge checker`](../../scripts/game_data/memorypack/enum_list_sources.py).
The compiled arguments and the placeholder's Int32 underlying field are checked
against selected metadata. Complete exception-family windows authenticate the
physical entries, while the interpreted claims cover selected complete
entry-to-return traces rather than every owned path.

This enum list calls a separate collection-header program and a bridge for
each element. It cannot inherit the integer list's virtual-call proof. The
buffered header copies one DWORD, advances the pointer and both counters by
four, then compares total length minus sign-extended consumed with the
sign-extended count using signed ordering. The count is not multiplied by
element width. Header success alone does not establish element-byte availability:
a positive count can pass with fewer than one buffered element. Under stable
normal buffered conditions, the returned AL tests count against minus one;
other negative counts are not universally rejected. The selected existing-list
path resets the count and skips the loop for zero or other negative counts.

The element bridge prepares the class, then freshly reloads its method pointer
and companion. A raw pointer comparison with the independently registered
Int32Enum scalar entry selects an inline four-byte read and full DWORD output,
with the same pointer/counter updates as that scalar formatter. This is a
conditional pointer-selected path; it does not prove that the provider returned
such a receiver. Other pointer results use the retained virtual dispatch path,
whose effects are outside this composition.

The list preserves the header count in a nonvolatile register, initializes a
separate loop index, zeroes a separate element output on each iteration and
passes the original reader to that bridge. The actual add target's selected
spare-capacity path preserves the output DWORD into a four-byte-stride array
element and increments list count and version. An identical repeated loop and
its signed back edge prove count iterations for a positive count when every
helper returns normally and the selected ready-context, fresh pointer,
buffer/capacity and stable disjoint storage conditions continue to hold.
Conditional serialized extent is the four-byte header plus four bytes per
element. Allocation, growth, refill and concurrent or aliased changes remain
open. The null branch stores a null pointer before calling a barrier helper;
its unproved effects prevent an unconditional null-at-return claim.

No integer or enum-placeholder witness establishes concrete DamageType sharing.
Named class/cache identity, concrete underlying-enum normalization, provider selection,
authenticated positive parent spans and complete root integration remain open.

The underlying-enum projection now has a
[`reviewed entry-program contract`](../../scripts/game_data/contracts/buff_enum_underlying_native.json),
[`selected native owner`](../../scripts/game_data/memorypack/buff_enum_underlying.py),
[`complete control checker`](../../scripts/game_data/il2cpp/enum_underlying_control.py)
and [`memory-immediate TEST decoder`](../../scripts/game_data/il2cpp/enum_underlying_instructions.py).
The decoder treats the memory TEST as a flag operation with no operand write;
the whole projection's exception-owned range and every ordinary entry's local
branch, call frame, return and tail transfer are checked. Small entries without
an exception-table row are bounded by their complete reachable entry programs;
they do not borrow the next function's extent.

Fresh PE name/ordinal/function-table joins bind `il2cpp_class_is_enum`,
`il2cpp_class_get_element_class`, `il2cpp_class_get_type` and
`il2cpp_class_enum_basetype` to the observed fields and entries. The enum-base
entry compares the element-class pointer with the original class. A self
element returns null; otherwise it freshly reads the element class and returns
the embedded type's address. These reads require valid coherent class storage;
the pointer read after the comparison is not assumed unchanged by concurrent
mutation.

For an enum-record input whose selected type flag is clear, the projection
resolves the class, tests that result's enum flag, then resolves the class again.
Only this second fresh result supplies the self-element test and element-class
pointer. There is no second enum-flag test: the first class being an enum does
not prove that the second class is the same or an enum. For a generic-instance
input, one descriptor-class result passes the null, enum and type-flag guards
before an actual tail transfer to the named enum-base entry. Fallback paths
return the original type, while the enum-record self-element path returns null.
Opaque child effects and changing inputs remain outside this projection proof.

The type wrapper reads `type.data` and passes it to a record-pointer conversion
entry. That entry subtracts the selected live metadata base and the
TypeDefinition section offset before applying the already reviewed record
geometry and tailing to the class resolver. The aligned valid-record index
domain is checked independently. In contrast, the selected on-disk DamageType
type record contains a TypeDefinition **index** in `type.data`; selected
metadata identifies its `value__` field as Int32. This establishes the stored
enum representation, not a live record pointer. The initializer's index-to-
record-pointer programs are joined conditionally below; substituting the
selected loaded source and stable runtime globals remains a separate obligation.
Runtime class/element identity, concrete DamageType normalization
and shared formatter/provider selection remain unresolved. This projection
does not admit positive parent spans or new complete roots.

The initialization join now has a
[`reviewed registration and fixup contract`](../../scripts/game_data/contracts/buff_type_data_initialization_native.json),
[`selected native owner`](../../scripts/game_data/memorypack/buff_type_data_initialization.py),
[`complete initialization control checker`](../../scripts/game_data/il2cpp/type_data_initialization_control.py)
and [`optional memory-update instruction reader`](../../scripts/game_data/il2cpp/type_data_initialization_instructions.py).
The complete exception-family partitions distinguish code, indexed tables and
explicit padding. The metadata entry's terminal call reaches a separately
owned helper with no ordinary return path: if its children return, it reaches
an `INT3` trap. Its no-return rule comes from that program, not an assumed import
name. The following unreachable padding bytes stay in the owned-byte partition.

An actual runtime-initialization block takes the selected static code and
metadata registration addresses and writes their global cells before calling
the metadata entry. The metadata-registration store dominates that actual call
in the complete normal-control graph. The child entry calls the previously
proved metadata initializer, whose success path calls the type-data loop.
This is a direct static call and publication chain. Other paths, opaque child
aliases, later writers and actual invocation are not inferred from it. In
particular, the registration global lies in the disk image's unbacked data
region: its live value is never fabricated from zeros or from the static table.

The type-data loop starts its signed DWORD counter and pointer-table offset at
zero. Each iteration reads the current type-table pointer, obtains the type
pointer, sign-extends its kind byte, subtracts one and applies an unsigned bound
before the selector and relative-target tables. It increments the table offset
by one Win64 pointer and reloads the registration after either fixup helper.
The selected DamageType kind dispatches to the TypeDefinition-record fixup;
the alternate helper uses the generic-parameter record section. Stable positive
count, valid disjoint table/source/target/frame storage and ordinary helper
behavior are conditions for a finite complete traversal.

Both closed fixups read a **signed DWORD** index from the original type's data
slot. Minus one writes a null **QWORD** and returns. Otherwise, the selected
record stride, fresh signed section offset and metadata base form the pointer
written back as a QWORD to that same slot. Other negative indices are not
universally rejected, and applying the fixup again to an already initialized
pointer is not proved idempotent. The selected static type slot has no other
table writeback target overlapping its data or kind bytes; this is a static
destination separation proof, not observation of live aliases.

Independent raw replay composes this writeback with the enum consumer's actual
record-pointer inverse for the entire valid aligned record domain. Under the
selected loaded metadata/header/base and stable globals, the written pointer
returns the original record index. Runtime source identity, initialization
execution and later global stability remain open. This conditional join does
not identify the live class/element, equate repeated class resolutions, select
concrete DamageType sharing/provider, or admit positive parent spans or roots.

The actual class-request lookup and its cache/constructor children now have a
further [`enum-field contract`](../../scripts/game_data/contracts/buff_class_enum_fields_native.json),
[`selected field owner`](../../scripts/game_data/memorypack/buff_class_enum_fields.py)
and [`field/primitive-flow checker`](../../scripts/game_data/il2cpp/class_enum_fields_control.py).
The constructor's record pointer and saved allocation result remain distinct
nonvolatile origins under ordinary ABI returns. The metadata bitfield's enum bit
replaces the class enum-flag bit independently of the previous allocated byte;
the generic-presence update changes another bit. No zero-initialized allocation
is assumed. This proves the flag at the actual stores; opaque child aliases and
later mutation remain conditions when using a later flag read.

The constructor first writes its own class pointer to the element and cast-class
fields. On the enum branch, it reads a signed element type-table index, passes
the selected type pointer to the actual class-from-type helper and writes that
helper's unchanged result to both fields. It then returns the saved allocated
class before restoring the caller's registers. An element index of minus one
uses the saved zero pointer argument; the helper reads the kind byte without a
null-input guard, so this is not a null-class-return proof. The selected current
DamageType element index is in bounds and its stored type kind is Int32.

The complete class-from-type helper now distinguishes code, two indexed target
tables, selectors and padding. Its named API wrapper supplies the true byte
argument and tails to that actual helper. With a stable valid input kind of
Int32, the selected path performs one fresh primitive class-cell read. It
returns that value when nonzero and returns zero through the guarded fallback
when the cell is zero. Other recursive paths and external tail effects are not
silently made read-only. The cell's actual producer passes the literal
`System.Int32`, a fresh image argument and the name-lookup return to this same
cell; a named request does not prove the returned class's identity.

A zero primitive cell is an explicit static boundary: the constructor can store
a null element class, and the named enum-base program can then return the type
field offset as an address rather than null. Its self-element test does not
exclude a null element. This is a hypothetical coherent-memory trace through
authenticated programs, not observed gameplay. A valid nonnull Int32 class and
its actual embedded type identity must be proved before concrete normalization,
shared formatter/provider selection or positive stored parent/root admission.

The cache construction now has a
[`key/record contract`](../../scripts/game_data/contracts/buff_name_cache_key_record_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_key_record.py)
and [`construction checker`](../../scripts/game_data/il2cpp/name_cache_key_record_control.py).
The caller preserves the incoming image and metadata-record pointers under
ordinary ABI returns. Signed name and namespace indices, fresh metadata-header
string offsets and metadata-base reads construct one zero-header key containing
both string pointers and the original record pointer. The selected insertion
block copies its header, adjacent strings and record into the same node. The
node's unused gap bytes are not copied; field preservation does not mean a
whole-node byte copy. Stable valid disjoint strings, metadata, key, output,
cache and node storage remain conditions.

Complete insertion, capacity-growth and rehash-builder controls now distinguish
physical writes and unreachable owned trap padding. Actual calls join growth
to rehash and rehash to a separate migration program; growth also calls a
separate swap program. Those child bodies now have a
[`migration/swap contract`](../../scripts/game_data/contracts/buff_name_cache_migration_swap_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_migration_swap.py)
and [`field-preservation checker`](../../scripts/game_data/il2cpp/name_cache_migration_swap_control.py).
The actual configuration child is a closed no-call program despite having no
exception-table range. Complete byte coverage, local control and the selected
field grammar establish its boundary; no neighbouring method supplies an end.
It exchanges a byte, a DWORD and two QWORDs, retaining the original QWORD pair
through a vector load, low-fragment store and byte shift. Its complete program
preserves R11 and RBX. Thus the parent's second cache pointer saved in volatile
R11 survives this particular child because of its actual effects, rather than
an ordinary ABI promise.

The parent passes the two configuration subobjects to that child, exchanges the
cache metadata and node-array pointers, then recomputes thresholds. All later
ordinary stores stay outside the exchanged metadata/node-pointer fields. This
does not establish publication visibility or live pointer lifetime. Independent
symbolic byte replay proves the selected exchanges for arbitrary field bits
under stable valid disjoint object/frame storage. Unselected gap bytes remain
unchanged; the first header block's intermediate exchange is distinct from its
later threshold recomputation.

The selected migration copy transfers the source node's header, string pair and
record pointer to one destination slot and advances the source cursor by one
node. Its final record store uses the QWORD loaded before that advance. Iterator
creation stores the incoming cache, cursor and end, and both scan programs use
the node stride. Complete allocation, iterator, capacity and hash controls are
authenticated separately from their full numeric and storage effects. The
capacity's post-return backedge block is part of its closed reachable program;
stopping at its first RET would lose a real branch.

The next [`marker/iterator contract`](../../scripts/game_data/contracts/buff_name_cache_marker_iterator_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_marker_iterator.py)
and [`complete filter checker`](../../scripts/game_data/il2cpp/name_cache_marker_iterator_control.py)
close the actual initialization and comparison children. The initializer copies
the free descriptor's header, string pair and auxiliary QWORD to each node,
leaving its unused gap bytes unwritten. It increments the destination by one
node until it equals the passed end. For a valid nonwrapping aligned range,
the empty guard and decreasing remaining-slot invariant prove finite completion.
This is a conditional domain theorem: the native code does not validate or
reject other ranges. The allocation caller's actual argument block uses the
fresh node pointer and capacity, then assigns capacity and clears both count
fields; allocator success and allocation bounds still require separate evidence.

The comparison child is a fixed no-call program. It compares DWORD headers;
different headers produce zero AL, equal nonzero headers produce one AL without
reading strings. Equal zero headers compare the two zero-terminated byte strings
in order; a namespace mismatch bypasses the name read. Bytes following the
first zero are irrelevant, and record pointers and node gap bytes are not read.
Both return paths write only AL, so the rest of RAX may retain a header or
pointer value. A false result need not be a zero RAX. The complete child leaves
R11, the nonvolatile registers and memory unchanged under normal completion.
Its two iterator callsites test AL and therefore use the proved result width.

Both iterator programs now have complete marker-filter grammars, including their
separate cold ranges at original addresses. Under stable finite compatible
strings, node storage and iterator/cache views, each marker advances the cursor
by one node, while a non-marker or the passed end stops filtering. The auxiliary
gate is an unsigned greater-than-zero check; the second descriptor comparison
is selected exactly when that gate is nonzero. This does not establish the live
count's meaning from its name. Iterator creation can bypass filtering through
its scan byte. The function used as next does not advance an already occupied
cursor itself: migration increments its cursor before calling this filter.
The actual begin/end argument blocks and scan-byte frame geometry are joined.
End and cache fields remain stable under the stated disjoint-storage conditions.

The [`destination/migration contract`](../../scripts/game_data/contracts/buff_name_cache_destination_migration_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_destination_migration.py)
and [`complete migration checker`](../../scripts/game_data/il2cpp/name_cache_destination_migration_control.py)
now join the entire migration program with its hash, initializer and iterator
children. The hash processes alternating signed bytes of the name and namespace,
mixing both parts modulo the native word width; headers and record pointers are
not inputs. The destination probe masks the hash by capacity minus one, then
increments a counter and adds it before masking again. Thus its slot residues
are a translated triangular sequence.

For capacity C equal to a nonzero power of two, the first C triangular residues
form a permutation. If distinct positions had equal residues, twice C would
divide the product of their difference and their sum plus one. Those factors
have opposite parity, and their nonzero even factor is less than twice C,
which contradicts the required power-of-two divisibility. Native-word wrap
does not change the low mask bits. This theorem needs the stated capacity
condition: a non-power-of-two mask can permanently miss free slots.

With stable disjoint compatible source/destination/cache/frame storage, finite
selected strings, normal noninterfering child completion and an all-free
post-allocation destination having enough such slots, complete migration
preserves the ordinary-node header/string/record multiset. Each successful copy
consumes one source node and one destination free slot, then advances before
filtering. Copied ordinary keys do not become free markers, so the remaining
free-slot invariant supports every later probe. Source nodes are not written,
the destination used count reaches the ordinary-node count, and the generation
field increments on ordinary completion. Unused node padding is not equalized.
Equal names with distinct record values remain distinct migrated entries; this
is not a proof of insertion duplicate handling or unique class identity.

Independent complete-instruction models explicitly supply the capacity result
and valid allocation postconditions. They execute the real hash and migration
children over hypothetical memories, rather than treating allocator success as
observed. The capacity program starts its candidate at four and only doubles
it; its returned candidate copy dominates the return. Its finite returned value
is therefore a power of two or zero after wrap. Actual nonzero capacity,
sufficient size, allocation/storage and population/history invariants still
need proof or an explicit selected-state gate before this conditional theorem
can establish the live cache or the named primitive class.

The constructor-capacity follow-up uses the optional
[`WORD immediate-store decoder`](../../scripts/game_data/il2cpp/word_immediate_stores.py)
recognizes operand-size-prefixed memory MOV with a two-byte immediate, preserving
the following instruction and computing RIP-relative addresses from the complete
instruction end. Unsupported selected operands fail closed. Register-to-WORD
stores already have typed widths in the existing memory-move reader; their
presence does not justify changing the older admitted instruction inventories.

The [`constructor contract`](../../scripts/game_data/contracts/buff_name_cache_constructor_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_constructor.py)
and [`complete default-state checker`](../../scripts/game_data/il2cpp/name_cache_constructor_control.py)
now follow the reviewed lookup's actual constructor call and its actual base-child
call. The base child has branches into blocks after its first return, so
truncating at that return would omit part of the program. Its reviewed closed
no-call extent includes those blocks before padding, without claiming
exception-directory ownership. The constructor's separately recorded trailing
trap is excluded from its reachable graph, and code plus padding tile its
entire exception family.

Under valid stable disjoint cache/frame/input-byte storage and normal instruction
completion, the base child establishes a nonzero power-of-two default capacity,
zero used/removed counts and exact default thresholds. Its positive normal
binary32 factors are multiplied by an exactly representable power of two:
only their exponents change, with no rounding error in any MXCSR rounding mode.
The authenticated comparison constant is positive binary32 two-to-63. Both
selected products stay below it, so signed truncation and the zero correction
register determine the integer thresholds. Normal completion remains a condition
because inexact truncation can raise an SSE precision exception. The copied
input stack byte remains arbitrary; the proof never assumes a zeroed cache.

The base child preserves the receiver and nonvolatile registers and does not
rewrite the zero counts later. Therefore the constructor's immediate count
check does not select its cold rehash branch under those postconditions.
It establishes distinct nonzero free/removed marker headers, zero marker
strings and free auxiliary data, requests capacity times node stride from its
actual allocator, and passes the returned base and computed endpoint to the
complete node initializer. Valid disjoint nonwrapping allocation and preservation
of cache/frame fields are explicit allocator postconditions, not proved effects.
Under them every default slot receives the free descriptor's selected fields;
node padding and untouched cache bytes remain unconstrained. Independent
fresh-instruction replay varies the input byte and prior cache/node bytes and
clobbers volatile registers/vectors at the assumed allocator return, preserving
these boundaries. Future capacity sufficiency, insertion history, allocator
success and live execution remain open; this adds no root admission.

The [`allocator wrapper contract`](../../scripts/game_data/contracts/buff_name_cache_allocator_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_allocator.py)
and [`complete wrapper/helper checker`](../../scripts/game_data/il2cpp/name_cache_allocator_control.py)
now join the constructor's actual allocator call through its direct tail proxy
to the whole wrapper, retry gate, handler and error-cell helper programs. The
selected import is uniquely joined to the actual terminated on-disk lookup/IAT
tables and the KERNEL32 HeapAlloc declaration. Its arguments come from a fresh
heap-handle cell read, zero flags and the preserved byte count. This names no
live IAT target or valid heap state. Under a standard live binding and valid
heap, [HeapAlloc's specification](https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc)
supplies the conditional normal-success storage guarantee. Zero flags do not
request zero initialization; inherited heap exception settings also affect
whether a failure returns normally.

The wrapper rejects oversized requests through an unsigned guard and changes
a zero byte request to one before its first allocation attempt. The first
nonzero imported return word reaches its return unchanged. A zero word selects
the fresh DWORD retry gate; a zero gate or zero handler result selects the
error path. Otherwise the same saved byte count is retried. This proves control
and argument origins, not eventual success or finite retry termination.

The handler obtains a fresh word from its getter. Zero skips the dispatcher
and returns zero; nonzero remains in RAX while the saved byte count is passed
in RCX to the actual dispatcher helper. That helper's low DWORD return is
normalized to a boolean. The getter/dispatcher bodies and selected callback
effects remain separate open joins; the caller proof alone does not prove that
the word is a valid callback or that the dispatcher invoked it. The error-cell
helper returns its child result plus a field offset, or selects a static
fallback when the original child result is zero. Valid nonwrapping writable
storage is still required. The wrapper writes a DWORD error word through that
address and then returns zero under normal compatible completion.

Independent fresh-instruction traces include success, null returns, retry-gate
changes between attempts and arbitrary prior memory bytes. External heap,
getter, dispatcher and context returns are supplied normal-return conditions;
their missing bodies are not executed or replaced with claimed proofs. Allowed
hypothetical context aliases can direct the error write into cache storage,
which demonstrates why cache isolation needs a separate condition; no such
alias or allocation failure is observed in the client. The complete constructor
grammar has no returned-pointer test before forming the node endpoint and
calling initialization. Thus a null wrapper result is outside its valid-allocation
theorem, and normal allocator-wrapper completion alone does not establish a
successfully initialized cache. Future population/history, named primitive
identity and positive stored parent/root integration remain open.

The [`handler getter contract`](../../scripts/game_data/contracts/buff_name_cache_handler_getter_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_handler_getter.py)
and [`complete getter/dispatch checker`](../../scripts/game_data/il2cpp/name_cache_handler_getter_control.py)
now prove the returned word formula under normal guard-helper ABI completion:
rotate right the encoded-word read XOR the cookie read, using the low six cookie
bits as the count. Both actual guard calls receive zero ECX. The decoded word
is saved in nonvolatile RBX across the second guard call and copied to RAX
before restoring the caller's RBX/frame. Changes to global words after those
reads do not change that saved result. The proof uses the two values actually
read, without establishing a common publication epoch or guard locking effects.

The optional [`PE load-config reader`](../../scripts/game_data/il2cpp/pe_load_config.py)
joins the cookie storage to SecurityCookie and the dispatcher storage to
GuardCFDispatchFunctionPointer through the selected PE declaration. These
fields hold preferred-image VAs of pointer storage, as defined by the
[Microsoft PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format),
not loaded function identities. This closes the earlier zero-owner named-import
lookup without inventing an import symbol. The selected on-disk dispatcher
word identifies a whole JMP RAX entry. If the loaded/rebased slot still selects
that file-default entry and RAX is a valid callable target, the two tails
preserve register arguments and the caller's return stack. Loader replacement,
actual selection, callback validity and effects remain unproved.

Fresh-instruction models vary all rotate counts and independent cookie/encoded
words, including zero decoded results and changes after reads. The dispatcher
model explicitly supplies file-default selection and normal callback completion;
an alternative slot remains unresolved rather than being coerced into that
model. No missing guard/callback body is executed, and the decoded word is not
promoted to a live callback identity. The error-context joins, cache isolation,
insertion/population history and named class/positive parent/root joins remain
separate open work.

The [`guard contract`](../../scripts/game_data/contracts/buff_name_cache_handler_guard_native.json)
and [`guard owner`](../../scripts/game_data/memorypack/buff_name_cache_handler_guard.py)
close both actual getter helper bodies. Each sign-extends ECX and computes
the shared array base plus forty times that signed index with native-word
wrapping arithmetic, then tail-calls a static EnterCriticalSection or
LeaveCriticalSection import. Both zero-index calls select the same storage.
Static imports and a closed tail do not establish initialized objects, live
bindings, acquisition/release or protection of every writer.

The [`lifecycle`](../../scripts/game_data/contracts/buff_name_cache_handler_lifecycle_native.json)
and [`setter`](../../scripts/game_data/contracts/buff_name_cache_handler_setter_native.json)
definitions are independently authenticated by the
[`state owner`](../../scripts/game_data/memorypack/buff_name_cache_handler_state.py).
Initialization calls the actual InitializeCriticalSectionEx proxy with spin
count 4000 and flags zero for successive array objects; nonzero EAX increments
the global counter. The initializer does not zero that counter. With a zero
entry counter, stable disjoint storage and valid normal API completion, success
initializes the declared array, while failure cleans the successful prefix in
reverse order and returns the counter to zero. Cleanup assumes its count
describes a valid initialized prefix; it does not clamp invalid counts.
Lifecycle results write only AL, leaving the rest of RAX outside the Boolean
claim. Invocation, initial object state, ordering, repeat safety and concurrent
use remain unobserved.

The setter saves its incoming word across the first zero-index guard call,
uses one cookie read to decode the previous word and encode the replacement,
stores the encoded replacement, then returns the saved previous decoded word.
For cookie C, count C AND 63 and new word W, the emitted store is
ROR64(W, 64 minus count) XOR C; getter decoding with that same C inverts it.
Rotate counts are masked to six bits, including the count-zero case.
Unknown leave-helper memory effects may change the global word after the
store, so the emitted write is separate from surviving final state.

The [`direct-store contract`](../../scripts/game_data/contracts/buff_name_cache_handler_direct_init_native.json)
and [`direct-store owner`](../../scripts/game_data/memorypack/buff_name_cache_handler_direct_init.py)
also prove a whole owned caller and its actual closed store child. The caller
saves one cookie read in nonvolatile RBX and passes that saved word to each
direct sibling. One selected child writes incoming RCX directly to the encoded
handler cell. With that same saved cookie, decoding at the emitted store state
would yield zero. That narrower direct-store proof left other siblings' effects
open; the complete child proof below closes their emitted stores. The saved
argument alone does not establish a common global epoch under concurrent use.
The store has no own guard call,
which does not establish absence of an enclosing lock. The caller writes AL
true only; its invocation and startup ordering remain open.

Independent fresh-byte replays cover lifecycle success/failure and reverse
prefix rollback, setter encoding/previous-word returns and direct caller/store
flow. API/object effects, guard returns and hypothetical sibling writes are
explicit supplied conditions, not execution of missing bodies. Direct-call
candidates from
[`native_call_references.py`](../../scripts/game_data/il2cpp/native_call_references.py)
remain raw overlapping instruction candidates until whole caller ownership
and instruction boundaries establish an actual edge. No matching direct call
does not prove a definition unused; indirect registration remains open.
The [`complete sibling-store contract`](../../scripts/game_data/contracts/buff_name_cache_handler_sibling_stores_native.json),
[`native owner`](../../scripts/game_data/memorypack/buff_name_cache_handler_sibling_stores.py)
and [`closed-program checker`](../../scripts/game_data/il2cpp/name_cache_handler_sibling_stores_control.py)
now close every actual child of that selected caller. Each child consists only
of RIP-relative QWORD stores of incoming RCX followed by RET. The eight global
destinations are pairwise disjoint, none overlaps cookie storage, and exactly
one is the encoded handler cell. These child instructions do not explicitly
write registers or call another body; RET performs its normal return-stack pop.
The other destination cells remain anonymous words with no inferred purpose.

For valid normal frame/global storage without faults, stack/global aliasing or
concurrent/intervening writes, all children receive the saved entry cookie and
write it to their declared cells. The cookie remains unchanged, and encoded
handler equals it at caller return. Decoding that return-state pair gives zero.
This is a conditional state theorem, not an actual getter invocation or evidence
that its later guard calls leave those values unchanged. The complete caller
also preserves incoming RAX upper bits while setting AL true, so it does not
establish a full-register Boolean result. Fresh-byte models execute every child
and every store without supplying hypothetical sibling effects or returns.

The closed selected child inventory does not cover other caller chains,
indirect registration or concurrent writers. All-writer coverage, actual startup
and lifecycle order, enclosing-lock state, live import/callback identity, actual
cache isolation and complete positive Buff roots remain separate obligations.

Complete migration, duplicate-key record
history, probe/capacity termination, lookup success and loaded image identity
remain open. This construction proof does not establish a nonnull named Int32
class, concrete DamageType sharing/provider, or positive parent/root admission.

The earlier name/key/index/type-copy scope retains its
[`reviewed lookup contract`](../../scripts/game_data/contracts/buff_class_name_lookup_native.json),
[`selected native owner`](../../scripts/game_data/memorypack/buff_class_name_lookup.py)
and [`control and projection checker`](../../scripts/game_data/il2cpp/class_name_lookup_control.py).
Complete exception-owned instruction inventories establish normal local control,
call frames and explicit stores. The typed conclusions cover selected projections;
the other insertion, hashing, resolver and constructor effects remain structural.

The request constructs a zero-headed key containing adjacent namespace/name
pointers. The cache's ordinary lookup compares zero-terminated bytes separately
for namespace and name; its default-marker comparisons are distinct. With a
stable zero query header, both query comparisons dominate the non-sentinel hit
write. This is a conditional local path proof, not an observed match, search
termination or empty-cache helper result. Strings, node storage and cache views
still require compatible stable storage and normal noninterfering helper returns.

After comparing the iterator node with a newly computed end pointer, the caller
loads the node's metadata-record pointer. The signed high-multiply/add/shift
sequence yields the corresponding index for every valid aligned record in the
selected metadata table. Live header/base identity, actual node bounds and
coherence between the separately read cache views remain conditions. The selected
end-node branch returns zero; this does not establish all possible miss results.

The constructor copies one raw 16-byte registered type record into its value
and reference type slots. It changes a flag DWORD only in the reference copy,
then stores the original vector into the value copy. A later actual call receives
the value copy's address without an intervening RCX overwrite. That child's
captured complete owned bytes include fixed-stride table addressing and calls
that forward the address to another helper. The selected later call's read-only
behavior is established below; preservation through other constructor calls and
aliases remains unproved. A stored request name therefore
still cannot bind the returned live class or select DamageType's shared formatter.

The selected type-copy search/comparison family now has a
[`reviewed closed-family contract`](../../scripts/game_data/contracts/buff_copied_type_readonly_native.json),
[`explicit selected native owner`](../../scripts/game_data/memorypack/buff_copied_type_readonly.py)
and [`control and memory-effect checker`](../../scripts/game_data/il2cpp/type_comparer_control.py).
Every ordinary call stays inside the checked search, type comparer and count
leaf. Complete owned code is partitioned separately from the embedded target
table and padding. The count leaf has no exception-table entry at its actual
call target; its complete ordinary entry program includes both return paths.
That entry proof does not claim an exception-owned extent or borrow a neighbor's
boundary.

All explicit writes are bounded stack/frame-home stores; implicit push and
normal-call return-address writes are also accounted for. There are no other
memory updates or calls outside the checked family. Induction over a finite
normal call tree therefore preserves non-stack input bytes when the complete
recursive stack is valid and disjoint from the type copy. This closes preservation
across this selected later call, not across other constructor calls, aliases or
concurrent writers. Recursive termination and observed execution remain open.

The comparer first reads a kind byte and one selected flag bit. Its kind-mismatch
ordering is signed-byte ordering; flag and selected data-QWORD ordering use
unsigned comparisons. The count leaf compares initial DWORD reads for equality,
then uses fresh DWORD reads for its difference ordering while preserving the
caller scan registers. Separate reads are not assumed identical. The guarded
target table retains its image base along every local path to the load, including
pointer-recursion backedges; all table targets are checked code boundaries.

A checked counterexample reaches a zero QWORD-comparison return with two distinct
raw type records: kind, selected flag and data QWORD match, while another flag
bit differs. Zero consequently does not establish complete record equality or
runtime class identity. Other recursive result semantics and the table search's
full result meaning remain open, as do named class/cache identity, concrete enum
sharing, provider selection and stored-parent integration.

For the maintained SpellBurst and target/mask actions, fresh source/read-order,
generated setter and current route checks distinguish these parents:
`TriggerSpellBurstEventAction` adds a scalar `spellBurstType`, whereas
`CheckWeaponTypeCondition.checkTarget` and `CheckEnemyRank.target` are recursive
`TargetSettings` members. The latter two cannot be admitted as primitive-only
leaf actions. The maintained
[`target/mask reader`](../../scripts/game_data/memorypack/buff_target_mask_conditions.py)
and its
[`reviewed contract`](../../scripts/game_data/contracts/buff_target_mask_conditions_native.json)
join both parents'
actual closed source contexts to an independently selected TargetSettings
wrapper and its runtime instance type. Fresh TargetSettings, DirectionSettings,
SelectorData and direction-to-target validators use the explicit selected
native inputs. Every reached nonnull target, direction and selector object
must match its independent complete ordered-field receipt and original bytes;
the stored-plan tree alone cannot name a descendant. The reached directions
contain null nested targets, and the reached selectors have a null finder and
empty validator/postprocessor lists. These selected spans do not extend
admission to other finder, validator or processor branches. Complete parent
reencoding preserves scalar bits on either side of the target and requires the
final field. Missing, incomplete, shifted or differently named child evidence
refuses the parent. CheckWeaponType reads `checkTarget` before the `weaponTypes`
DWORD; CheckEnemyRank reads the `enemyRankSet` DWORD before `target`. The
independently named `spellBurstType` DWORD follows the inherited prefix in
TriggerSpellBurst, so that action belongs to the maintained leaf reader.
All three compose through the recursive action dispatcher. Fresh selected
native validators and original-span replay authenticate those maintained
routes; a complete current VFS family gate and each gained root's thirty fields,
source ID and physical EOF remain necessary before increasing complete coverage.
Stored masks and SpellBurst fields do not establish an evaluated predicate,
selected target, emitted event or gameplay effect.

A frozen source epoch containing these three maintained routes has passed the
complete installed Buff corpus gate. Its original path set and logical hashes
match the prior admitted family, with no complete-root regressions. Each gained
root is independently replayed from byte zero through all thirty named fields,
the source ID and physical EOF; the full receipt must equal the family result.
The replay uses the actual returned native audits from that completed gate,
with only the executable registry restored, and authenticates the selected
native files, frozen source closure and contract reads before and after.
This admission belongs to that captured epoch. It predates the later AI,
skill/lifetime/weakness and curve additions, so it does not validate those newer
routes or the current working tree as a complete family. The missing original
Skill capture receipt still blocks cross-family JsonData publication. Complete
stored roots do not prove the corresponding predicates or gameplay effects.

A later independently captured epoch containing the AI, skill/lifetime/weakness
and AnimationCurve stored readers has also completed the original installed
Buff family sweep. Every source retains the same logical identity, and no
previously admitted complete root regresses. Each newly complete root then
replays its original logical bytes separately through all named root fields,
source-ID equality and physical EOF, with complete receipt equality. The
replay authenticates the actual typed native return objects emitted by that
family run; restoring the executable registry does not synthesize a validator
return. The residual frontier is recomputed from this same family, with
changing counts and per-source inventories confined to reports.

This later admission belongs to its frozen stored-reader scope. Subsequent
AI caller, getter, flag-helper and named ancestry proofs have their own
explicit scopes, and neither a whole-current-working-tree pass nor observed
gameplay execution is inferred. The absent original Skill capture receipt
still blocks canonical cross-family publication. Unchanged passing format
checks can be reused under their authenticated source/native gates; unrelated
consumer or documentation edits do not require another corpus sweep.

The maintained source-bound parents `ChangeSkillAction`, `SaveBuffLifeTime` and
`SetWeaknessAction` compose through the
[`skill/lifetime/weakness reader`](../../scripts/game_data/memorypack/buff_skill_lifetime_weakness_actions.py)
and its
[`reviewed current contract`](../../scripts/game_data/contracts/buff_skill_lifetime_weakness_actions_native.json).
Their current formatter windows are reviewed separately in
[`ChangeSkill source`](../../scripts/game_data/contracts/buff_2c_native.json),
[`SaveBuffLifeTime source`](../../scripts/game_data/contracts/buff_133_native.json)
and
[`SetWeakness source`](../../scripts/game_data/contracts/buff_15b_native.json).
Native read-order audits, generated setter declarations and independent current
union routes must agree before using the historical toolkit's names as a recipe.
Historical union tags cannot select a current reader. The current Weakness
source includes `canConvertToInterruptibleWeakness`; the older toolkit's merged
layout omits it, so replaying that layout would shift every following member.

After the inherited action prefix, ChangeSkill stores `cacheTime`, `duration`,
`inheritOriginSkillCdProgress`, `lifeTimeType`, `overrideCacheTime`,
`revertedSkillId`, `skillSlot`, `skillSource`, `specificRevertedSkillId` and
`targetSkillId` in that source order. SaveBuffLifeTime stores `buffOwner`,
`buffSettings` and `key`. Weakness stores `alertEffectDurationBB`,
`alertEffectScaleBB`, `canConvertToInterruptibleWeakness`, `triggerActions`,
`triggerWeaknessCountBB`, `useWeakerTriggerEffect` and
`whiteAlertEffectDurationBB`. The scalar children are independently owned
BlackboardDouble or BlackboardInt readers; their matching three-member wire
shape does not make their runtime types interchangeable. The maintained
[`BlackboardDouble owner`](../../scripts/game_data/memorypack/buff_adding_cooldown.py),
[`BlackboardInt owner`](../../scripts/game_data/memorypack/buff_pick_target_action.py)
and
[`BuffFindSettings reader`](../../scripts/game_data/memorypack/buff_find_settings_child_receipt.py)
provide independent child evidence. Preserve null versus empty payloads,
noncanonical flag bytes and all scalar bits. Byte-payload framing does not prove
native string-decoder parity or evaluated blackboard values.

The selected ChangeSkill and SaveBuffLifeTime spans now have maintained complete
recursive stored-value receipts. Their TargetSettings descendants close through
the independent DirectionSettings, direction-to-target and SelectorData
validators: every reached nonnull object matches source-named ordered fields
and exact spans. Reached directions have null nested targets; reached selectors
have a null finder and empty processor/validator lists. This proves only those
reached branches. Complete field-value reencoding requires every final member
and does not substitute an opaque child blob for a named receipt. The maintained
dispatcher also closes selected Weakness sequences whose reached CreateBuff
actions have independently proved icon-duration, input-list, BlackboardDouble
and target descendants. The sequence's terminal flags remain raw. Each parent
field's closed source context must match the independently owned runtime type
and stored wrapper; BlackboardInt and BlackboardDouble keep separate owners.
Missing owner gates, incomplete or shifted child spans, unknown action tags and
trailing bytes refuse the parent. A fresh isolated source epoch authenticates
these maintained routes; shared changes outside the owning files do not make an
older broad publication current. A passing complete current VFS family gate and
independent full-root replay remain necessary before changing complete coverage.
Stored skill IDs, lifetime fields and weakness flags do not prove a skill
replacement, saved duration or gameplay weakness effect.

The remaining selected mine Weakness sequences reach `AddAIMarkerAction` and
`SaveValueFromAIBlackboard`. Fresh native read-order, setter-destination and
current union checks name their members from the reviewed
[`AddAIMarker source`](../../scripts/game_data/contracts/buff_07_native.json)
and
[`SaveValueFromAIBlackboard source`](../../scripts/game_data/contracts/buff_142_native.json).
After the inherited prefix, AddAIMarker reads `duration`, `marker`, `markerOwner`
and `removeByAction`; SaveValueFromAIBlackboard reads `aiBBKey`, `bbOwner`,
`skillBBKey`, `skillXKey`, `skillYKey`, `skillZKey` and `valueType`. Its independent
nullable strings and final DWORD remain required after the target.

The marker is a GameplayTag value class. Its name or unmanaged size alone cannot
supply a primitive wire read. The named checker requires the parent's actual
closed source context, the source-call destination, the reviewed DWORD-return
and four-byte cursor-update program, and the separate registered reader's
normal path. The existing
[`GameplayTag source proof`](../../scripts/game_data/contracts/buff_cost_action_native.json)
and its
[`helper window`](../../scripts/game_data/contracts/buff_fe_native.json)
are independently reauthenticated for this parent; the checker does not accept
a name-only width override. Refill/error behavior stays outside the proved
normal paths. The maintained
[`AI action reader`](../../scripts/game_data/memorypack/buff_ai_marker_blackboard_actions.py)
and its [reviewed declaration](../../scripts/game_data/contracts/buff_ai_marker_blackboard_actions_native.json)
compose independent Double/Target owners and preserve legal short/wide marker
tags in field-value reencoding; fresh selected-native and original-span checks
authenticate these maintained AI routes. Selected mine Weakness parents now
close through actual RandomPointFinder evidence, the returned
ModifyDynamicBlackboard parent packet and the explicit
[`AnimationCurve profile owner`](../../scripts/game_data/memorypack/animation_curve.py).
Every reached nonnull object and headerless Keyframe matches complete
source-named fields and raw values through the
[`record binder`](../../scripts/game_data/memorypack/source_bound_stored_tree.py).
Parent reencoding preserves all sequence descendants and terminal fields.
Full-family and whole-root admission remain separate requirements.
Stored keys and value-type words do not
establish a selected AI/skill blackboard, conversion result, marker lifetime or
gameplay side effect.

The separate
[`AI consumer validator`](../../scripts/game_data/buff_ai_consumers_native.py)
reproves the
[`named consumer claims`](../../scripts/game_data/contracts/buff_ai_consumer_claims.json)
against explicitly selected native inputs. These claims contain no build
addresses. A guard must be selected by its owning assembly as well as its type
and method: the installed metadata has identically named IFix managers in
different assemblies. The conversion caller uses the `Gameplay.Beyond.dll`
definition. The checker refuses ambiguous type owners, static field slots,
incompatible overloads and a callee whose class definition differs from the
destination field's actual generic definition.

On the false patch-check branch of
`SaveValueFromAIBlackboard.Data.ConvertToServerDataInternal`, the incoming Data
receiver supplies `skillBBKey`, `skillXKey`, `skillYKey` and `skillZKey` in that
order. Each declared String reference is skipped when null or when its
`System.String._stringLength` DWORD is zero; the guarded call otherwise receives
that unchanged reference. The constructor receiver's declared
`BATTLE_ACTION_MULTI_MODIFY_BB_ACTION_DATA.keys_` field supplies the collection
argument. Every key and collection receiver is reloaded after earlier calls,
so this is not a snapshot of their initial values. Complete owned instruction
boundaries, preserved receiver aliases and skip destinations establish this
conditional field-to-argument flow under coherent instances and ordinary
returning Win64 calls. Runtime patch selection, live generic MethodInfo,
callee mutation, AI source lookup, value conversion and gameplay effects remain
open.

The separate
[`AI lookup caller checker`](../../scripts/game_data/il2cpp/ai_blackboard_selection.py)
now proves the selected normal `ExecuteInternal` prefix and lookup blocks. It
derives `m_data` from the actual closed `AbilityAction<SaveValueFromAIBlackboard.Data>`
reference layout; an open generic's placeholder offset cannot supply this join.
The declared `bbOwner` and incoming target-handle representation reach
`GetFirstTarget`. Its returned AbilitySystem supplies the inherited
`BaseComponent.entity` reference; that Entity supplies `enemyAICom`. The
EnemyAIComponent ancestry must match the declaring AIComponent receiver before
calling `GetParentBlackboard` with its Boolean initialization argument false.
A null AI component joins a null blackboard reference before the Unity Object
null comparison. A null target or true blackboard-null comparison reaches the
false return leaf. A null Data or Entity read instead reaches the separately
recorded failure-helper path, whose effect is not inferred from proximity.

The separate
[`guarded reference getter checker`](../../scripts/game_data/il2cpp/guarded_reference_getter.py)
proves the complete owned primary `AIComponent.GetParentBlackboard` program
under a false patch-guard result and a false incoming initialization byte. Its
assembly-owned method signature and declared instance field bind the reference
read to `AIComponent.m_parentBlackboard`, with declared type `AssetBlackboard`.
The false byte skips the complete optional-helper block; the subsequent field
read reaches the plain RET through matching stack and nonvolatile-register
restores without changing RAX. The saved-register slot must lie in caller
shadow space without overlapping the return address. An independent actual
CALL-byte join connects the already proved caller's false argument to this
same exact getter entry. This proves the current field reference read after
the guard, not preservation of its pre-call value. The guard's side effects,
the skipped helper's behavior, the owned cold patch path and actual runtime
branch selection remain unresolved.

The current enum declarations and the actual DWORD selector distinguish Float,
String and Vector3. Each selected call reloads the current `aiBBKey` from Data
and passes the selected blackboard reference. Float mode tries float, then int,
then bool, advancing only after a null variable return; an earlier nonnull
result skips the later lookup blocks. These are repeated field reads, not a
guarantee that helper calls preserve the key's initial value. Unsupported
selector words or a final null lookup reach a separate true return leaf. Both
leaves are proved through their matching saved-register restores and RET.
The returned Boolean alone does not establish that a destination was assigned
or that preceding helpers had no side effects.

The lookup's generic parameter count selects its actual overload independently
of the nongeneric method with the same name. All five callsites have exact
static MethodSpec argument evidence. Vector3, float, int and bool also have
independent compiled-instantiation registration joins to the physical entry.
The String call has its own static MethodSpec and the same exact caller target,
but its direct compiled registration is absent in the selected table. This
remains a generic-sharing obligation; an object instantiation cannot substitute
for it. No live MethodInfo selection is observed. Getter, conversion and write
regions contain instructions outside this checker's selected program profile;
the checker does not promote them to complete caller or gameplay-effect proof.

Exact PE-owned lookup-helper windows now expose a distinct nongeneric
`GetVariable(IBlackboard, String, Type)` definition, a dictionary `TryGetValue`
call, recursive calls to that same lookup and a `Variable.GetGetConverter`
call. The generic lookup's final direct tail target also has an independently
owned complete byte window. These are algorithm candidates, not a proof that
the dictionary call returns a requested value, that the converter executes,
or that the tail helper performs a particular cast. Another generic helper
call lacks an exact primary PE extent; neighboring entry addresses cannot
supply its boundary. Generic MethodInfo context-slot meaning,
lookup/type-conversion algorithms, value getters and destination writes remain
separate obligations.

The
[`generic lookup forwarding checker`](../../scripts/game_data/il2cpp/generic_lookup_forwarding.py)
now proves the complete registered generic wrapper and its direct tail program.
The return type must use the selected method container's own parameter, and
each selected value-type instantiation must independently join the compiled
entry. The actual `RuntimeTypeHandle` value layout establishes its one-word
call ABI rather than assuming that a value class is passed by reference.
The wrapper preserves the incoming blackboard and String-key references,
passes an anonymous context word to the named `Type.GetTypeFromHandle` entry,
and passes that returned Type reference to the separate nongeneric lookup.
Metadata/context/class helpers remain opaque; their ordinary-return and valid
read conditions are explicit. In particular, the pointer region is reloaded
after the nongeneric lookup, so its subsequent word is not assumed to come
from the same pre-call context contents. These observed operands do not name
a native MethodInfo member or prove that the returned Type identifies T.

The nongeneric lookup's opaque Variable return is preserved for the exact
tail target. A null reference reaches a zero return and skips both tail
helper calls. A nonnull reference supplies its first word and the wrapper's
separate helper result to an opaque predicate; only a nonzero predicate AL
result reaches a return of the same Variable reference through matching
nonvolatile and stack restores. A zero predicate result instead reaches a
separate helper call followed by INT3. That helper's behavior and the
predicate's actual type-compatibility or cast rule remain unproved. This
conditional same-reference result does not prove a typed value getter,
requested runtime type identity or a destination assignment.

Actual CALL-byte joins connect the AI caller's selected lookup sites to the
complete wrapper program. Value-type sites retain their own registration
joins; the String site retains only its own static MethodSpec and exact
physical target, with its absent direct compiled registration still explicit.
The wrapper proof does not manufacture a String registration or observe its
live context. Nongeneric dictionary/recursive lookup, GetGetConverter and
Type-helper algorithms remain open beside the value/conversion/write and
runtime-effect obligations.

The historical EnvTalk investigation captured that missing-unwind helper
against the Buff investigation build. That historical raw capture retained the
absence of a PE primary extent; the current EnvTalk contract is not a build
substitute or a dependency for this older Buff claim. The legacy decoder does not recognize the initial byte TEST form and
can subsequently decode its operand bytes as a misleading separate CMP.
Those rows therefore cannot establish complete instruction boundaries or a
field read. The maintained
[`raw flag-leaf checker`](../../scripts/game_data/il2cpp/flag_guarded_reference_leaf.py)
now independently authenticates and parses the complete reviewed bytes,
including both exact local branch targets and the external signed tail jump.
Actual caller bytes connect this leaf to the generic lookup's second
anonymous context-slot helper. A nonzero masked byte returns the unchanged
incoming reference without executing an external helper. A zero mask result
preserves the argument registers, stack and return address while tail-jumping
to a separate owned program. The byte field's name and context-slot type
remain anonymous; the raw grammar does not invent a missing PE extent.

That external program has an exact primary PE extent and a separately owned
cold fragment. Both are captured and their complete control is checked by
the same maintained lane. It preserves the incoming reference, passes it to
an opaque preparation helper, then compares an anonymous DWORD read after
that call. Only a zero comparison reaches the matched normal return of the
same reference. The other branch rereads the same DWORD location into a
zero-extended argument, calls an opaque carrier helper, forwards its returned
word to another helper with a zero second argument, and reaches INT3 if both
return. No throwing behavior or cold return value is assigned. Neither the
initial DWORD value nor the compared value is claimed to survive helper
effects or concurrent mutation. The earlier failed single-fragment capture
and its frozen source remain separate from this complete ownership proof.

These conditional programs remove an instruction-boundary and ordinary-return
gap, while preparation and cold-helper algorithms, requested runtime type,
context-slot meaning and live context selection remain open. Full owned
windows for the preparation/cold children and the named Type helper remain
inventories; unsupported legacy instruction rows do not establish their
algorithms. The nongeneric query, value getters, conversions and destination
writes still require their own complete consumer proofs.

A separate fresh join now connects the tail's actual predicate CALL to the
selected GameAssembly export `il2cpp_class_has_parent`. This uses the already
maintained
[`named class ancestry validator`](../../scripts/game_data/memorypack/buff_formatter_class_ancestry.py),
its
[`reviewed declaration`](../../scripts/game_data/contracts/buff_formatter_class_ancestry_native.json)
and
[`complete control checker`](../../scripts/game_data/il2cpp/class_ancestry_control.py),
including the export name/ordinal/EAT bytes, complete owned body, named field
getters and its context/import parents. Under valid coherent storage and
normally returning initialization/synchronization helpers, normal AL is one
exactly when the unsigned first depth is at least the freshly loaded second
depth and the first ancestry array's entry at second depth minus one equals
the original second argument. The body has no extra zero-second-depth guard;
valid backing storage remains a condition.

The lookup tail passes the first QWORD read from the opaque nonnull Variable
reference as the first argument and the separately resolved anonymous context
word as the second. This identifies the checked ancestry predicate used by
the same-reference return; it does not independently bind the anonymous
context operands to the method's T and Variable<T> runtime types, select a
live object-header/class/context, or prove generic cast or typed-value
semantics. The legacy inventory's unsupported rows remain a
historical decoder limitation; the separate complete ancestry decoder is the
proof source. Initialization/synchronization outcome and all subsequent value
getter, conversion and write effects remain separate obligations.

`TeleportAction` has a
maintained
[`stored reader`](../../scripts/game_data/memorypack/buff_teleport_action.py)
and
[`reviewed current declaration`](../../scripts/game_data/contracts/buff_teleport_action_native.json).
Its current union route, fourteen generated members, source call contexts,
named setter transfers and primitive float helper are independently rejoined
against the selected native inputs. The historical layout lacks the current
`actionOnTargetPointInvalid` sequence and cannot supply the current header or
union tag. Missing or mismatched inputs provide no current parent names.

The Teleport stored composition binds that sequence, the BlackboardDouble
`radius` and `teleportTo` TargetSettings to their independent native child
owners. Primitive flags, signed words and floating bits remain raw; the final
`throughWall` byte is required after the target. Each child and the complete
parent must reencode to its original logical span. The current full-family
gate and independent gained-root replay now establish this maintained
composition on the accepted originals: byte-zero reads cover every named root
field, verify the stored source ID and end at physical EOF, with complete
receipt equality. Fresh unchanged typed native return objects are reused only
under the completed family, original implementation/consumed-contract pins and
selected native inputs; restoring the executable registry does not replace a
validator. This is stored-root admission, leaving actual target choice and
teleport effects unresolved. The shared
[`stored-tree binder`](../../scripts/game_data/memorypack/source_bound_stored_tree.py)
requires every nonnull object to have a separate exact named-field receipt
with the same ordered names and boundaries, and compares recorded raw wire
values where supplied. A metadata tree or a parent's span cannot close an
unproved child. Null wrappers, null versus empty collections, null versus
empty strings and noncanonical Boolean bytes retain distinct representations.
Selected original spans pass this composition and its recursive dispatcher;
new complete Buff roots still require the fresh full-family gate and original
root replay to physical EOF. Fallback execution, resolved radius, selected
destination, navigation checks and teleport effects remain unresolved.

The selected `_TryFindStraightLineDest` normal path binds the inherited
`m_data` reference through a concrete closed
[`reference witness`](../../scripts/game_data/il2cpp/reference_layouts.py) and
reciprocal [`VAR owner`](../../scripts/game_data/il2cpp/context.py). Saved incoming
aliases bind `startPos`, `expectPos`, raw `navmeshArea` and the Vector3 out
parameter to the navigation call's corresponding arguments. These
[`buffer programs`](../../scripts/game_data/il2cpp/vector3_distance_flow.py)
require valid Win64 preservation and normal completion; navigation algorithms
and actual writes are separate obligations.

After navigation succeeds, the caller saves its output before the complete
[`subtraction leaf`](../../scripts/game_data/il2cpp/vector_arithmetic.py)
overwrites that buffer with output minus `startPos` read after navigation. The
[`square/sum leaf`](../../scripts/game_data/il2cpp/vector3_squared_magnitude.py)
returns ordered Single `(x*x+y*y)+z*z`. Both complete leaves preserve the saved
volatile XMM4/R9 lanes by their actual instructions. The
[`limit program`](../../scripts/game_data/il2cpp/single_squared_limit.py) reads
`maxDistance` twice, multiplies, then uses COMISS/JA: ordered greater fails;
equality and unordered fall through after normal comparison. One squared
limit requires stable field reads, with floating exceptions/MXCSR explicit.
Success copies the saved navigation bytes, rather than the overwritten
buffer, and returns true. Navigation false and ordered-greater share the
[`failure program`](../../scripts/game_data/il2cpp/vector3_failure_flow.py): the
complete [`zero leaf`](../../scripts/game_data/il2cpp/vector3_zero_value.py)
writes twelve zero bytes; the caller reads its return pointer before clearing
AL, copies the zeros and enters the common
[`saved-frame return`](../../scripts/game_data/il2cpp/win64_rbp_frame.py).
Frame/home/output validity and absence of corrupting indirect writes remain
conditions; folded entry names do not establish live MethodInfo selection.

Outer Teleport ranges are owned by complete
[`exception-table parent chains`](../../scripts/game_data/il2cpp/unwind_chains.py),
including split and noncontiguous cold code. Full triples, frame bytes and
terminating chains establish membership without adjacency or a hop fallback.
Common version-one/two framing does not certify unwind operations, fixed-stack
consistency, language handler data or whole managed CFG. Raw decoder/call
inventories remain candidates where their instruction or identity proof is
incomplete.

`_GetRealLandPos` declares the selected closed `Nullable<Vector3>` return.
Its complete [`canonical interface programs`](../../scripts/game_data/il2cpp/nullable_vector3_programs.py)
bind the reciprocal static Vector3 argument: construction writes a one-byte
value tag and twelve payload bytes; `get_HasValue`, guarded `get_Value` and
both `GetValueOrDefault` overloads establish the corresponding reads/branches.
The exact MethodSpec is selected before canonical-pointer projection; a
fourth registration word is retained without interpreting its adjustor table.
Interface footprint is not a proof of total closed size or private field
layout. Same-qualified-name IFix owners occur in different assemblies, so
callee identity additionally requires the selected image/declaration and exact
registered pointer; a name-keyed dictionary alone is insufficient.

The complete [`ordinary path return`](../../scripts/game_data/il2cpp/nullable_vector3_path_return.py)
binds the hidden output pointer, instance and source/expected-position aliases,
frame and path argument, typed `m_Corners` array and `m_data.checkMaxDistance`
read, tagged payload copy and ordinary return. It initializes the full result
buffer, so copied padding stays zero. The indexed copy uses a sign-extended
dword count, **32-bit** `DEC EAX`, an unsigned bound comparison and a twelve-byte
stride; the earlier subset inventory's `DEC RAX` text is not its byte semantics.
Last-corner meaning requires stable positive signed counts and the external
array-header schema. On the initialized IFix-false path with distance checking
disabled, the output agrees with the selected nullable interfaces. Actual
corner calculation/writes, IFix/initialization, array header and total closed
value size, provider/target selection, whole caller control flow and actual
teleport effects remain unresolved. Complete
root gains still require current family-source admission and original replay
to physical EOF; an internal corpus result cannot override a rejected outer
source freeze.

The complete [`ordinary distance continuation`](../../scripts/game_data/il2cpp/nullable_vector3_distance_path.py)
rejoins that hot frame, zero accumulator and nonzero output tag. Its fixed
loop limit is signed low-DWORD count-provider result minus one; each segment
reloads corners after separate calculations and calls the independently
checked [`array element program`](../../scripts/game_data/il2cpp/vector3_array_element.py).
The helper compares the unsigned low index DWORD but addresses using the full
R8 index. Independent extended-SIB decoding proves R8 plus twice R8; the
candidate decoder's different index register was not accepted. Count/payload
coordinates and the twelve-byte copy establish observed array operations,
without certifying the full header or allocation. A bounded element
interpretation requires the full index to agree with its nonnegative low
DWORD and valid nonwrapping memory.

The complete anonymous [`distance program`](../../scripts/game_data/il2cpp/vector3_distance_program.py)
subtracts vector components, performs ordered Single `(dy*dy+dx*dx)+dz*dz`,
converts the sum and a zero lane to Double, applies **packed** `SQRTPD`, then
converts back with `CVTPD2PS`. Memory-source MOVSS clears the other Single
lanes. Its initialization and negative-result helper calls remain conditional
opaque edges; this body is not joined to a named Unity Distance entry.
The caller adds successive results as Singles and directly compares
`maxDistance` against the accumulated value. After normal COMISS, ordered
greater-or-equal recalculates and copies the current last corner; ordered
less or unordered calls the selected straight-line checker with the original
source/expected positions, saved area and independent output buffer. False
clears the entire tagged result; true copies twelve output bytes and preserves
the hot tag and padding. The straight-line checker retains its separately
proved squared-limit behavior and valid-memory/normal-call conditions.

The original count-call static context selects `SafeCount<Vector3>`. The
reciprocal MVAR/container join and exact registered Vector3 argument close its
static parameter declaration to `IList<Vector3>`; runtime context remains
separate. The actual anonymous entry differs from the canonical registration.
Both complete [`count programs`](../../scripts/game_data/il2cpp/null_safe_count_programs.py)
initialize a zero context slot before checking the list, return zero for a
null list after normal initialization, and pass the same zero slot, opaque
context-helper result and original list to the selected dispatch entry. Their
tail jump and call/return frames are checked independently. Matching arguments
do not establish identical physical entries or behavior for arbitrary dispatch
state. Static RGCTX definitions and getter-pointer candidates remain distinct
from emitted runtime slots, interface selection and the returned count.

The same reciprocal method variable also binds the static RGCTX type and
method references to `ICollection<T>.get_Count` and its declared interface slot.
The independently selected named `System.Array` getter has a complete
[`split count program`](../../scripts/game_data/il2cpp/array_collection_count.py):
its owned main, class-error and dimension-loop ranges are joined through exact
branches, without using adjacency to own the distant ranges. It reads the first
length as a QWORD through either the direct array coordinate or the nonnull
bounds pointer; the bounds path rejoins the dereference rather than returning
pointer bits. The normal result is the low DWORD. Additional dimensions multiply
DWORD results, increment a DWORD counter, reload the unsigned rank byte after
each opaque dimension helper, and continue on a signed counter comparison.
A fixed-dimensional product requires a stable rank and valid normal helper
results. Class/rank error producers and the shared raise helper remain opaque.

The selected `Array.get_Rank` independently reads that same class byte and
zero-extends its result. Its complete leaf return program is authenticated
without claiming an exception-table-owned extent. For rank one and a zero
bounds pointer, the Count program's low-DWORD result matches the element
helper's DWORD count coordinate, conditional on actual getter selection and
valid readable array memory. These programs do not prove runtime interface
selection, the complete array header or allocation, or a live returned count.

The selected `NavMeshPath.CalculateCorners` is a complete
[`reference-cache program`](../../scripts/game_data/il2cpp/lazy_reference_cache.py).
An already nonnull `m_Corners` returns without a call or explicit object-field
write. A null field calls the selected `CalculateCornersInternal`, whose
declaration returns `Vector3[]`, stores its returned reference, then tail-calls
an opaque notification with the slot address. Actual producer output and
notification effects remain open. Repeated calls on the cache-hit path therefore
do not themselves recalculate or replace that reference; this supplies no
synchronization or proof that other helpers, aliases or threads leave the
field and array contents unchanged.

Calling the accumulation a single path length additionally requires count
equality to the array length and stable arrays/contents across every
calculation. The patched wrapper is outside the proved ordinary continuation.
Static byte programs remain distinct from observed destination values or
teleport effects. Negative instruction-mutation checks must alter the intended
decoded instruction; changing an adjacent operand cannot isolate the claimed
register-width distinction.

The [`contract-read observer`](../../scripts/game_data/il2cpp/contract_read_scope.py)
authenticates CPython-audited JSON opens in a fresh process. Freeze ordinary
contracts before importing consumers, install the hook and observe its probe;
every watched read checks its original pin and completion rechecks the consumed
set. New, writable, linked or changed inputs fail with the offending path.
Every input error stays latched even when a consumer catches its exception;
later successful reads cannot make completion succeed. A separate failure
lock preserves this rule while another thread holds the verifier's pin lock.
Verifier hash reads are excluded only in the verifier's thread. A write through
an already-open descriptor can escape open observation, so the final consumed
pin check remains necessary. Native files, Python imports, external helpers and
VFS inputs retain their own before/after gates. An unopened contract is outside
this process's audited read set; this establishes neither universal nonuse nor
coverage of unaudited native I/O. The hook observes provenance rather than
providing a security boundary. A rejected older directory-wide freeze remains
rejected; changing the measured input scope requires a new actual full-family
run, followed by original-root replay before admitting coverage.

The shared `action_dispatcher.reviewed_switch_table` reads every JSON contract
before selecting AbilityActionData switch identities and reviewed tag blocks.
`buff_damage_check_decorate_mask_condition_receipt` reaches it through
`load_action_routes`, and actual fresh-process observation confirms the full
directory read. A contract with another domain's filename therefore cannot be
assumed outside Buff's measured dependencies. The scanner catches parsing and
read errors to continue catalog discovery, which is why observer exceptions
must remain latched independently of the consumer. Narrowing this dependency
requires a reviewed change to catalog selection and fresh native/corpus proof;
it cannot be achieved by exempting files from the current read gate.

`MoveToAction` now has a maintained
[`parent source validator`](../../scripts/game_data/memorypack/buff_move_to_source.py)
and
[`reviewed source declaration`](../../scripts/game_data/contracts/buff_move_to_source_native.json).
The validator independently rejoins the current union route, generated field
order and declared types; selected missing or mismatched native inputs publish
no names. Supplementary primitive and unmanaged source windows, the mapper and
metadata helper, and the complete source closure are authenticated before and
after the check. This is parent source evidence, without recursive action or
complete-root admission. `MoveToAction` has an explicit direct-store
path in its
[`reviewed source window`](../../scripts/game_data/contracts/buff_f6_native.json):
the four common operands load the inherited wrapper's declared base-Data
instance and store the actual primitive helper result into the corresponding
base fields, after both reference checks. They do not require a generated
setter call. The maintained
[`inherited direct-store checker`](../../scripts/game_data/memorypack/inherited_direct_action_sources.py)
checks the complete prefix through the fourth common store, exact source
arguments, declared instance/field slots and both reference guards. A later
wrapper dereference deliberately changes the alias role, so this prefix does
not establish aliases through the complete action. Its `fixAngle` instead passes a hidden result slot to the current
closed `Vector3` reader, then transfers the complete eight-plus-four stored
bytes into the instance returned by the actual getter. The maintained
[`struct-output checker`](../../scripts/game_data/memorypack/struct_output_sources.py)
checks that raw source, cursor, argument and destination program; this does not
establish the getter's runtime result or refill/failure parity.

`MoveToAction.ignoreCollisionLayer` is a declared `LayerMask` value. The current
compiled source and its independently resolved closed registered reader have
different entry points: each loads the stored DWORD, calls the actual shared
reader-advance helper for four bytes and returns the same bits. The complete
helper program updates the pointer and counters under the buffered normal-call
conditions. Its caller preserves the reader/wrapper aliases and passes the raw
DWORD to the declared setter. The source bytes are covered by
[`validator_02_native.json`](../../scripts/game_data/contracts/validator_02_native.json),
with the independently checked registered-reader/cursor program declared in
[`buff_cost_action_native.json`](../../scripts/game_data/contracts/buff_cost_action_native.json).
The named-source checker now selects the explicit `dword-with-cursor-call`
program in
[`unmanaged_cursor_sources.py`](../../scripts/game_data/memorypack/unmanaged_cursor_sources.py).
It retains the separate inline DWORD profile when no mode is declared and
rejects unknown modes. A value-type name or size cannot select either grammar.
The cursor-call algorithm also checks the sole method-generic return signature,
freshly derives the value-reader field slots and covers the complete direct,
registered and cursor programs. Shared helper identity uses its actual span
and native bytes; descriptive boundary text is not code identity. Type-size and
closed-registration caches initialize independently: a preceding raw-struct
read cannot leave a following unmanaged value without its selected entry
resolver. This proof does
not establish provider selection, actual setter execution, collision behavior
or a complete action. Integrating the checker changes the implementation
snapshot: retain earlier full-family counts under their completed source scope
until a coherent recursive-action batch passes a new full-family gate and
independent gained-root replay. Original MoveTo structural spans preserve the candidate
field order and bytes. Independent scalar, curve, string, vector and target
child proofs compose on selected original ranges. The complete selected
setter transfers now validate separately; constructor/header correspondence,
recursive SubSpeed and provider selection still precede named action and
complete-root admission.

MoveTo's declared `fixPosAngle` joins the existing
[`BlackboardVector3 reader`](../../scripts/game_data/memorypack/buff_effect_vector_child_receipt.py):
its stored `x`, `y` and `z` each close through the independently selected
BlackboardDouble grammar. Its declared `target` joins the existing
[`recursive TargetSettings reader`](../../scripts/game_data/memorypack/buff_recursive_actions.py)
through named DirectionSettings and SelectorData children. Selected enemy
teleport originals reach the maintained
[`FixedPointFinder reader`](../../scripts/game_data/memorypack/buff_selector_fixed_point_finder.py),
with raw position/rotation offsets, a BlackboardDouble sampling radius and
the stored navigation-mesh flag. These are existing named recursive formats,
not a new anonymous target variant. Current native direction-to-target and
fixed-point joins validate separately, and every selected original child
ends at its independently reparsed parent field boundary. Old full-validator
caches may be reused only for child owners whose source and contract closure
still matches; revalidate affected joins after a shared checker changes.
The historical candidate contributes original ranges only: reparse the
current typed parent order rather than asserting its old producer is current.
This proves selected stored child composition, not a live target, physical
generic provider, complete parent transfer, SubSpeed admission or Buff root.

The separate maintained
[`MoveTo setter-transfer validator`](../../scripts/game_data/memorypack/buff_move_to_setter_transfers.py),
[`selected caller/setter algorithm`](../../scripts/game_data/memorypack/selected_wrapper_setter_sources.py)
and
[`reviewed transfer declaration`](../../scripts/game_data/contracts/buff_move_to_setter_transfers_native.json)
join every generated setter to its actual caller return and metadata-owned
Data field. The complete caller prefix preserves the incoming Reader and
wrapper-reference aliases, reloads each selected wrapper, and deliberately
dereferences the final wrapper alias. Independent reader/context loads may
appear in either observed order; their exact register destinations, contiguous
arguments and source call remain checked. The common getter's initialized,
nonnull and equal-cache branch returns the same base/derived referent.
Boolean normalization, DWORD bits, raw Single bits and reference transfers
remain distinct, including larger field displacements. LayerMask retains its
separate unmanaged cursor/registered-reader proof instead of borrowing the
primitive DWORD template. Each selected setter restores its complete frame;
a reference store then reaches the independently checked common helper.

That helper has a complete return with no calls or memory writes when its
barrier flag is disabled. This connects the reference setter tails and the
SubSpeed post-store calls under the stated flag condition. The shared physical
reference-read entry also joins the existing complete outer-return program:
it initializes a local original output, forwards the same Reader/output to
selected dispatch, then returns that local reference. Current typed call
contexts share the owned generic declaration, but the full declared-method
registration scan still does not identify that actual physical entry. An
independently registered Object instantiation cannot substitute for it.
These are conditional static transfers, not a final accumulated parent state:
runtime MethodInfo/formatter choice, enabled barriers, runtime-constructor
effects, failure/refill and indirect allocation/global effects remain open.
Child grammar and whole-action/root admission are separate obligations. The
validator authenticates the explicit native pair, Unity input, reviewed
dependencies and source closure before and after checking, and a skipped
native build leaves its published report untouched.

The maintained
[`MoveTo lifecycle validator`](../../scripts/game_data/memorypack/buff_move_to_lifecycle.py),
[`buffered wrapper lifecycle algorithms`](../../scripts/game_data/memorypack/buffered_wrapper_lifecycle_sources.py)
and
[`reviewed lifecycle declaration`](../../scripts/game_data/contracts/buff_move_to_lifecycle_native.json)
close the selected buffered header and wrapper-return paths. A single header
byte updates the pointer and three counters with their native arithmetic
widths; `FF` clears the outer wrapper reference and reaches the same restored
frame as the normal return. Non-null MoveTo and SubSpeed require their exact
generated member counts. New-wrapper and reused-wrapper branches join the
current field owners' complete caller programs rather than inferring a field
grammar from the header. MoveTo's existing-wrapper preparation calls
`OnDeserialized`; its ready callback paths are composed by the separate
runtime-default owner below.

The wrapper constructors forward the statically authenticated runtime type
to allocation, call that runtime type's constructor, and preserve the same
allocation alias through the observed stores. The shared physical store writes
both the base and derived-cache slots; its many folded method aliases do not
identify a unique named constructor. The warm getter compares those slots.
Both missing-cache and unequal-cache branches refresh the cache from the base
through the actual cast callee, preserve the saved register, and rejoin the
cache return load. The cast returns the original pointer under the checked
class-flag and hierarchy conditions; its null-input path returns null. The
selected class-ready paths contain no heap/global writes, and the disabled
post-store helper does not disturb the saved reference aliases. Cold fragments
must be selected by actual control-flow edges: a primary unwind extent may
contain only the first instruction, while adjoining extents can belong to
other callers.

These complete selected paths still require ready usage/class flags, a
buffered byte, normal typed allocation and runtime-constructor returns, the
stated hierarchy comparisons and a disabled barrier. The lifecycle owner
alone does not prove nested constructor defaults or effects, initialization
slow paths, the live provider/MethodInfo, final accumulated object state,
recursive SubSpeed admission or a complete Buff root. It authenticates its
selected native inputs and source closure before and after checking; unchanged
field-owner and original-child receipts are reused only within their current
authenticated scopes.

The maintained
[`runtime-default validator`](../../scripts/game_data/memorypack/buff_move_to_runtime_defaults.py),
[`constructor transfer algorithms`](../../scripts/game_data/memorypack/runtime_constructor_sources.py)
and
[`reviewed default declaration`](../../scripts/game_data/contracts/buff_move_to_runtime_defaults_native.json)
prove the explicit stores on the complete selected MoveTo and SubSpeed
constructor paths, including their nested Blackboard, target, vector and
curve construction. The BlackboardDouble cell is joined to the existing
closed `float, double` carrier and its generated value setter; its stored
default is Float32 even though the public consumer returns Double. No open
generic layout or presumed allocator clearing supplies a field default.
The parameterless scalar constructor stores zero, the scalar overload
preserves its Float32 parameter bits, and the vector constructor forwards
its three Float32 parameters to three distinct scalar children while
restoring the full frame and saved SIMD registers.

The MoveTo constructor explicitly sets selected scalar defaults, including
the move-back distance, interaction radius and root-motion scale; it also
sets the enable, navmesh-ignore and cliff-stop flags. Each axis SubSpeed
creates separate fixed-speed and root-motion-scale children with zero and
one respectively. Target construction stores the selector-owner ordinal and
sets the nested direction's `clampToXZ` flag. The reviewed declaration owns
the exact fields and raw bits. Fields without an observed store retain an
explicit gap; they are not classified as zero, null or false merely because
the constructor allocates an object.

The curve constructor and the inlined SubSpeed curve creation load the same
cached function cell, pass a null keyframe-array argument, and store the
opaque returned pointer. The actual cold resolver input names
`UnityEngine.AnimationCurve::Internal_Create(UnityEngine.Keyframe[])`.
That string does not identify the live cached target, prove a concrete curve
handle or establish engine/allocation effects. The vector's selected nested
class-initializer call has a complete early return with no heap/global writes
under the checked nonzero class word; its slow paths remain open. The
profiling-byte test and address-only load are verified as such, rather than
allowing anonymous instructions to introduce an unaccounted field write.

The ready `OnDeserialized` callback has complete returns for a nonnull cache,
a null cache with a null base, and a null cache with a nonnull base. Only the
last path casts the base and writes the cache, followed by the disabled
barrier return. A nonnull cache remains unchanged without checking equality with
the base; the ordinary getter's unequal-cache refresh is a separate path.
The callback's initialization slow path and live invocation remain unproved.
All these constructor and callback claims require the stated class/usage
flags, normal typed allocation returns, warm curve function cache and
disabled barriers. They do not establish the final state after constructor,
preparation and deserialization are accumulated, select the anonymous
formatter's MethodInfo/provider, admit recursive SubSpeed or a whole action,
or prove execution in the game. The owner gates the selected native pair,
Unity input, reviewed dependencies and source closure before and after
validation and preserves the last report when native inputs differ.

The maintained
[`generated formatter route validator`](../../scripts/game_data/memorypack/buff_move_to_formatter_routes.py),
[`argument and tail algorithms`](../../scripts/game_data/memorypack/generated_formatter_routes.py)
and
[`reviewed route declaration`](../../scripts/game_data/contracts/buff_move_to_formatter_routes_native.json)
join the current MoveTo and SubSpeed **wrapper** formatter routes. Each
wrapper's static initializer tails to its actual `RegisterFormatter` method
with a null companion and no frame change. The selected registrar entry path
allocates the exact nested formatter type, calls its named constructor and
passes the same saved reference to the actual shared `Register` entry with a
closed MethodSpec for that wrapper. The Register declaration's sole method
parameter owns `MemoryPackFormatter<T>`; the actual physical Register entry
joins a unique registered method definition. Its independently registered
`object` instantiation does not replace the wrapper MethodInfo actually passed
by the caller.

The formatter metadata has a closed `MemoryPackFormatter<Wrapper>` base and
an instance Deserialize method at the required virtual slot with the same
reader/output byrefs as the existing static wrapper reader. Its ready
constructor has a complete return without heap/global writes. The ready
Deserialize caller preserves the incoming reader and output references,
restores its full nonvolatile/stack frame, supplies a null static-reader
companion and tails to the current reader's exact module pointer. This proves
the caller transfer; the selected reader behavior and return obligations stay
with the existing reader owners.

Registration of a generated wrapper is distinct from selecting an adapter for
the original runtime Data or SubSpeed type requested by a shared `ReadValue`.
The new proof stops at the registrar's first wrapper Register call; its
remaining array/enum registrations and Register's dictionary effects are
still open. The shared ReadValue entry has neither a module pointer for its
supplied declaration nor a matching slot anywhere in the current generic
method pointer array, so the independent `ReadValue<object>` registration
still cannot identify it. Warm metadata/class flags, typed normal allocation,
ordinary returning calls and the selected ABI remain conditions. These routes
do not observe provider/vtable selection, resolve the runtime-original
adapter, establish accumulated object state or admit an action or Buff root.
The new owner authenticates the explicit selected native pair, Unity input,
dependencies and source closure before and after validation, and preserves
its report on native-input drift.

The maintained
[`original-adapter validator`](../../scripts/game_data/memorypack/buff_move_to_original_adapters.py),
[`getter and interface-loop algorithms`](../../scripts/game_data/memorypack/original_adapter_sources.py)
and
[`reviewed adapter declaration`](../../scripts/game_data/contracts/buff_move_to_original_adapters_native.json)
locate the separate current `InitEager` registrations for original MoveTo Data
and SubSpeed. Each selected block allocates its exact
`GenericMemoryPackFormatter<Original, Wrapper>`, preserves that adapter across
the closed constructor thunk, resolves the original type handle and supplies
the same adapter and returned type key to `RegisterWrap`. The thunk reloads
that identical concrete constructor context before reaching the independently
registered shared physical constructor. Its Object/Object registration
identifies code; it does not replace the concrete ordered type arguments.
This is a complete local registration block, conditional on reaching it and
normal returning calls, rather than proof that the whole eager initializer ran.

Reciprocal generic owners join the adapter's original output parameter to its
formatter parent and virtual Deserialize declaration, while its distinct
wrapper parameter owns the nested provider and wrapper formatter. The two
parent SubSpeed child calls supply closed ReadValue arguments with the exact
same original type pointer as their eager registration key. The independently
registered shared adapter Deserialize pointer matches the actual dispatcher's
first optimized-case operand; that static relationship does not identify an
inflated concrete MethodInfo or prove runtime receiver selection. The shared
ReadValue clone's named-body identity remains unresolved.

Concrete conversion differs between the wrappers. SubSpeed `GetValue` returns
its metadata-owned original instance field directly. MoveTo `GetValue` keeps
the same receiver, clears the companion and tails to the existing cached
instance getter; its cache effects remain owned by the lifecycle proof. The
typed original conversion interface occurs after the first nonmatching pair
for SubSpeed and after four nonmatching pairs for MoveTo. The new algorithm
authenticates every repeated native lookup probe, its ordinal increments,
the actual metadata pair and the complete ordinary-call suffix and epilogue.
Both concrete getter and nested formatter pointers differ from the helper's
optimized alternatives, so their selected fallbacks apply. The formatter
return route joins the existing current wrapper reader with the same byrefs.

These joins close the static original/wrapper adapter relationship and
selected conversion callers. Compatible initialized runtime interface/class
tables, inflated contexts, provider results and typed normal callee returns
remain explicit conditions. They do not prove dictionary mutation or
retrieval, actual eager/provider/vtable selection, allocation/constructor
effects, final accumulated instance state, a complete recursive action or a
Buff root. The new owner gates the selected native pair, Unity input,
dependencies and source closure before and after validation; build drift
returns no proved summary and preserves the last report.

The current SubSpeed reader in the same reviewed source family has the generated
order `fixedSpeed`, `rootMotionAnimKey`, `rootMotionScale`, `speedCurve`,
`speedType`: two BlackboardDouble references, a string, a curve and a trailing
DWORD enum. Its own source writes directly into the declared Data fields;
reference writes are followed by a separate helper call. The maintained
[`SubSpeed source validator`](../../scripts/game_data/memorypack/buff_move_to_subspeed_source.py)
and its
[`reviewed declaration`](../../scripts/game_data/contracts/buff_move_to_subspeed_source_native.json)
now join the complete conditional operand program through the last store.
The separate
[`direct Data profile`](../../scripts/game_data/memorypack/direct_data_sources.py)
checks both incoming pointer aliases, the deliberate final wrapper dereference,
all null guards, actual RAX/EAX stores and each following slot-address helper
call. The final DWORD helper separately proves the buffered read and cursor
accounting. This is conditional on coherent declared references and ordinary
Win64 returning calls. A typed MethodSpec proves its owned generic declaration
and supplied argument; it does not identify the physical generic callee.
Exact closed registrations for these selected contexts remain unresolved;
do not substitute a nearby or independently registered entry. Disabled
post-store helper returns now compose through the separate transfer validator;
enabled helper effects, runtime provider/MethodInfo selection and failure/refill parity remain
open, and the validator admits no child grammar, action or root. Its source
closure, dynamic native helpers and explicitly selected native inputs are
authenticated before and after validation. The declared runtime field order differs from the generated member order
and cannot replace it. Original MoveTo scalar and curve spans can reuse their
independently native-gated child readers, including each distinct SubSpeed
interior range. Those independent scalar/curve spans and the earlier byte-exact
SubSpeed candidate alone did not establish a complete recursive SubSpeed
schema, barrier effects, selected provider or a complete MoveTo record. The
parent and SubSpeed root-motion keys separately join the maintained UTF-8
source helper on each original range.

The separate
[`complete SubSpeed stored codec`](../../scripts/game_data/memorypack/buff_move_to_subspeed.py)
now composes that source order, the complete null/new/reused wrapper returns,
the static original/wrapper conversion route and the current independently
proved BlackboardDouble, UTF-8 and animation-curve child grammars. It admits
exactly the single-byte null record or the five-member record, requires the
complete supplied child span, and reconstructs it from named nested values.
Raw wire Boolean bytes, Float32 words, curve/keyframe words and the final enum
DWORD remain bit-exact; null and empty strings, nullable key arrays and null
objects remain distinct. Missing/mismatched native inputs, incomplete route
bindings, unsupported member headers, invalid UTF-8/counts and truncation fail
closed. Current original spans join all named field boundaries and wire values
to their independently established child ranges before exact reencoding.
Selected native inputs and both source closures are authenticated before and
after replay; changing inventories stay in the generated reports.

This closes the recursive stored SubSpeed schema for the declared null/member-
five format under compatible initialized contexts and default formatter
bindings. It does not observe actual callback cursor equality, provider/vtable
selection, reference-barrier or allocation/engine effects, or accumulated
runtime object state. Other header variants and Buff root admission require
their own evidence. The codec reuses the existing
reviewed SubSpeed source contract rather than duplicating native declarations.

The owning
[`complete MoveTo stored codec`](../../scripts/game_data/memorypack/buff_move_to.py)
composes the entire declared parent order with independently proved
BlackboardDouble, BlackboardVector3, TargetSettings, UTF-8, curve and SubSpeed
children. It accepts only the declared null or complete parent header, consumes
the entire supplied action span and reconstructs every named field. The
[`stored-plan value helper`](../../scripts/game_data/memorypack/stored_plan_values.py)
preserves raw scalar words, Boolean bytes, nullable collections, null versus
empty strings and the original short or wide union encoding. Its metadata
trees remain `structuralOnly`: each recursive vector/target object must also
match the source-proved child receipt's complete named member boundaries and
raw wire values. A metadata name match or successful round trip alone cannot
admit a child.

The recursive action dispatcher includes this current source-declared union
route only with validated matching parent and child native inputs. The parent
composition keeps only its owned child dependencies; retaining the caller's
entire registry would make the returned native evidence cyclic when the caller
publishes the parent back into that registry. A complete root still requires
the current full-family gate and independent replay of any gained original
roots through every following root field and physical EOF. Historical family
classifications cannot be promoted by a successful selected action replay.

This is an `exact` stored representation under the `conditional` compatible
initialized-context/default-formatter route. Actual provider/MethodInfo and
callback cursor correspondence, accumulated instance state, enabled barriers,
allocation/engine effects and refill/failure paths remain `unresolved`. Exact
named reencoding is not a measurement of movement or of the runtime instance.

Consumer argument proofs have a separate owner in the
[`named instance-region copy checker`](../../scripts/game_data/il2cpp/instance_region_copy_arguments.py).
It authenticates a nongeneric incoming reference instance, selected named
field bounds, complete original branch/call instructions, a false Boolean
guard and a nonzero raw field byte before accepting a stack-copy receiver.
The
[`fixed vector-copy proof`](../../scripts/game_data/il2cpp/fixed_vector_copy.py)
derives literal loop counts, affine addresses and every transferred byte from
the selected complete instruction span. Its input address identities,
disjoint storage and nonwrapping arithmetic remain explicit conditions.
Unknown instructions, mismatched stored byte identities, incomplete coverage
or unsupported receiver signatures fail closed.

For the selected MoveTo `OnEnd` path, the named bounds are
`m_moveRequestHandle` through `m_circleCenter`, and the selected value-instance
callee is `MoveRequestHandle.StopMoveRequest`. This proves an owned field
region copied to a local receiver under the checked conditions; it does not
identify the closed Nullable's internal flag/value members or equate the
copied region with a fully proved managed value layout. A type-size record's
native-size entry is not substituted for this independently proved copy
coverage. Copied object pointers, the stop method's selected field arguments,
downstream writes and the final movement state retain separate obligations.
The generated named-copy and consumer inventories own the current byte counts
and branch details; the consumer claims registry still requires its own review.

The separate
[`value receiver bridge checker`](../../scripts/game_data/il2cpp/value_receiver_bridge.py)
checks complete full-width RCX-relative address-return and receiver-tail-jump
programs. The selected on-disk `il2cpp_object_unbox` export returns the
displaced incoming address through a plain RET; an independently selected
short program applies the same displacement and directly jumps to the unique
named `MoveRequestHandle.StopMoveRequest` body. Original instruction bytes,
export name/ordinal/function joins, current value-owner and instance-method
declarations, both address widths, the complete terminal transfers and equal
displacements are checked. ADD and LEA retain their different flag effects.

This is `exact` program evidence under the `conditional` selected-entry and
valid nonwrapping-address assumptions. The bridge's token/padding/pointer
registration-table candidate remains `structuralOnly`; a plausible row or an
equal bias does not authenticate that table's schema, actual registration
selection, boxed field-offset coordinates or closed Nullable/ObjectPtr
members. Those field-ownership joins and the stop method's writes and movement
effects remain `unresolved`. The named export improves the bias evidence
without promoting the copied region to a complete managed-value layout.

Static generic call evidence has a separate owner in the
[`canonical entry and call-block checker`](../../scripts/game_data/il2cpp/generic_call_projection.py).
The selected MethodSpec's exact registration row joins its canonical pointer
to the original direct call. A positive fourth registration word stays
uninterpreted; this projection proves neither an adjustor entry nor the full
generic registration. An absent exact row fails closed. The selected
`ObjectPtr<Entity>` usages in `StopMoveRequest` have no exact registered row;
their shared `Object` entries retain a separate runtime canonicalization gap.

The two selected `Nullable.get_Value` contexts declare
`MoveCommand.RootMotionMoveData` and `uint`. The return VAR joins its owning
type container and ordinal reciprocally through the maintained context
reader, then selects the corresponding static class argument. Complete
original call blocks load the hidden context and form the receiver address.
The uint block also reads a qword into RSI from an RAX-relative address; its
explicit mode checks the complete read and preserves RCX/RDX call arguments,
with valid readable source storage as a condition. That read supplies no
object-field identity.

The [`guarded Nullable getter checker`](../../scripts/game_data/il2cpp/nullable_value_getter.py)
checks each entire getter, its raw flag-byte branch, payload width, balanced
normal return and terminal failure call/trap. The selected nonzero paths
return the raw RootMotionMoveData word and uint word, with EAX zero-extension
on the latter. The zero paths call the uniquely named
`System.ThrowHelper.ThrowInvalidOperationException_InvalidOperation_NoValue`;
its body effects remain a separate obligation. This is `exact` static byte
and declaration evidence under `conditional` selected-entry/readable-address
assumptions. Live MethodInfo resolution, receiver ownership, boxed field
coordinates, full closed Nullable member layouts, returned payload member
identity and subsequent stop effects remain `unresolved`. Static argument
types and complete getter programs do not admit another complete Buff root.

BlackboardDouble keys now have their own
[`inline source and original-span reader`](../../scripts/game_data/memorypack/buff_blackboard_double_key.py)
and
[`reviewed source declaration`](../../scripts/game_data/contracts/memorypack_blackboard_double_key_native.json).
The reusable
[`inline UTF-8 source profile`](../../scripts/game_data/memorypack/inline_utf8_sources.py)
proves the incoming reader alias, buffered signed DWORD length and cursor,
remaining-total bound check, distinct null/empty/positive branches, exact
`ReadUtf8(int)` method identity and result join. Original child ranges retain
their independent scalar framing and required tail; valid UTF-8 keys decode
and reencode exactly without evaluating a blackboard lookup. A null child,
present null key and present empty key are distinct. Invalid bytes are rejected;
native replacement behavior and failure/refill paths remain unproved.

This key proof ends at the joined result register. The current concrete
BlackboardDouble runtime type inherits the instantiated generic
BlackboardParamBase; its absent own field-offset row cannot be replaced with
the open generic template's offsets. The separate maintained
[`closed scalar Data owner`](../../scripts/game_data/memorypack/buff_blackboard_double_data.py),
[`program profile`](../../scripts/game_data/memorypack/closed_scalar_wrapper_fields.py)
and
[`reviewed declaration`](../../scripts/game_data/contracts/memorypack_blackboard_double_data_native.json)
now join that result and the following Boolean/Single sources to the cells
written by the actual named generated setters. The runtime parent and the
wrapper's base-instance field carry the same closed generic instantiation.
Reciprocal metadata ownership places the stored `value` VAR at the first
argument, `float`; the second argument, `double`, does not change the stored
width. The emitted setter programs establish the concrete destination cells,
without using the generic definition's offset table as an instance layout.

The buffered reader normalizes the stored selector byte with a nonzero test
and copies the Float32 bits directly. Original-span receipts therefore retain
both the raw wire byte and the conditional normalized Boolean state; exact
wire reencoding does not substitute the normalized byte. Float32 negative
zero, infinity and NaN bit patterns also remain raw bits. The key setter and
reader use the same independently checked barrier flag; the selected disabled
path does not establish the enabled bitmap loop or observe the runtime flag.
These field flows remain conditional on coherent declared wrapper/base-instance
references and ordinary Win64 returning calls. Constructor/base-instance
correspondence, public GetValue composition, actual provider selection,
lookup results and failure/refill behavior remain separate
obligations. Other Blackboard scalar kinds and the vector's interior joins
require their own source and original-range proofs. Typed MethodSpec
declarations still do not identify the physical generic reference helper, and
these scalar receipts admit no complete action or Buff root.

The separate maintained
[`concrete consumer owner`](../../scripts/game_data/memorypack/buff_blackboard_double_consumers.py),
[`complete selected-program profile`](../../scripts/game_data/memorypack/closed_scalar_consumers.py)
and
[`reviewed declaration`](../../scripts/game_data/contracts/memorypack_blackboard_double_consumers_native.json)
now prove selected reads from these independently established cells through
the return instructions. The key getter returns the key reference. The cast
method loads the stored Single and applies legacy `CVTPS2PD`; its lower result
lane is Double. Both selections require the actual named patch check to return
false. The
[Intel instruction description](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2a-manual.pdf)
supplies that lower-lane conversion meaning; concrete CPU/MXCSR state,
denormal handling, exception completion and actual numeric results are not
observed or admitted by the source checker.

The concrete `TryGetValueInternal` proof covers the selected normal class,
reference and signed-DWORD guards, a nonnull incoming Blackboard and a writable
original Double output reference. A zero selector loads the stored Single,
converts it and writes eight output bytes with a true Boolean return. A nonzero
selector passes the stored key reference and incoming Blackboard to the actual
registered `_TryGetNumber(string, ref double)` overload. Its distinct temporary
Double slot is initialized to zero; the caller copies that slot into the
original output and preserves the lookup's actual Boolean return. This consumer component proves
delegated arguments and the caller's output/return flow, without proving the
lookup body, found value or guard-owner semantics. The original stored receipts
join these source/destination cells under the additional condition that their
proved field state survives until this consumer selection. Actual instance
correspondence, intervening writes and runtime branch selection remain open.

The separate public/default composition proofs are documented below. The
number-lookup discovery establishes that the current Blackboard
inherits `List<DataPair>` and separates its registered entry range from its
exact unwind-owned fragments. A single `.pdata` range need not contain a
complete managed method; fragment ownership must follow the unwind chain,
never adjacency. That discovery's subset-decoded call candidates alone do not
prove the complete lookup field flow. The separately maintained
[`managed key-comparison owner`](../../scripts/game_data/memorypack/buff_blackboard_key_comparison.py),
[`word-comparison CFG profile`](../../scripts/game_data/il2cpp/utf16_ascii_comparison.py)
and
[`reviewed callback declaration`](../../scripts/game_data/contracts/memorypack_blackboard_key_comparison_native.json)
prove the actual `_EqualsIgnoreCase$BurstManaged(short*, short*, int)` leaf,
including its loop and both Boolean returns. Its word arithmetic and unsigned
conditional moves fold only ASCII uppercase `A` through `Z` by adding the
lowercase delta. Every other 16-bit unit stays unchanged; this is not Unicode
case folding. The
[Intel conditional-move definition](https://cdrdv2-public.intel.com/812383/253666-sdm-vol-2a.pdf)
supplies the unsigned above condition and word operand meaning. Different
folded units return false; equal units advance by one word until the signed
Int32 length is exhausted. A nonpositive length returns true without reading
either input span. The leaf contains no calls or memory writes; readable,
unchanged input spans and normal instruction completion remain conditions.

The owner also checks the actual Burst getter call, its false-return branch
into the lookup's exact unwind-owned managed callback, and the fragment that
forwards the current aliases to this comparison entry. This component alone
does not observe the getter result or prove the preceding aliases' input
origins. The Burst enabled callback, actual key objects, matched lookup values
and all-dispatch lookup CFG remain separate obligations. The separately maintained
[`pair/list owner`](../../scripts/game_data/memorypack/buff_blackboard_pair_list.py),
[`value-cell profile`](../../scripts/game_data/memorypack/blackboard_pair_cells.py)
and
[`reviewed pair/list declaration`](../../scripts/game_data/contracts/memorypack_blackboard_pair_list_native.json)
now connect all four nongeneric DataPair field declarations to the actual
numeric, string and copy constructors. Each complete constructor reaches
its return. Actual stores establish the unboxed cells; their common boxing
bias agrees with the current field table, registered type-size record and
closed list's value extent. The pair contains two managed string references,
a Double bit cell and a raw dynamic byte. The remaining padding stays opaque;
the value extent is not a serialized wire schema.

Constructor aliases survive the helper calls only under the actual shared
barrier's disabled DWORD guard. Its complete selected path compares the
flag, copies the address into R8 and returns, with no memory writes or calls.
That program establishes preservation of the other volatile aliases and XMM
inputs. The ordinary
[Microsoft x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170)
alone cannot establish that preservation. The physical barrier is a leaf
without a `.pdata` extent; its authenticated entry, selected branch and return
CFG suffice for this path, without claiming an enabled-path or unwind proof.
The numeric constructor stores the incoming Double bits and clears the string
cell. The string constructor stores the incoming string and clears the Double
bits. The copy constructor transfers the four named fields, leaving padding
unwritten. The dynamic byte is copied without a Boolean normalization claim.

The complete selected normal `get_isNumericValue` paths return true for a null
string cell or an empty managed String, and false for a nonempty String.
The length read is joined to System.String's owned instance Int32 field;
the predicate reads neither the Double cell nor the dynamic byte. Thus a
string constructor supplied null or an empty String can classify as numeric
under these getter guards if its fields survive unchanged. This is a
conditional composition, not an observed game lookup or result. The raw
class/dispatch guards, normal completion and coherent readable value/String
state remain explicit conditions; initialization and alternate dispatch are
outside the proof.

The actual closed `List<DataPair>.get_Item` registration, reciprocal return
VAR owner/ordinal and selected DataPair value argument establish the returned
type. Its complete success path takes an output address, list receiver and
Int32 index, checks two unsigned bounds and a nonnull array reference, loads
two complete chunks before writing the output, and returns the original
output address. The emitted address arithmetic establishes the value stride
and array-cell relation. These are observed operand cells; the open generic
List offset table is not used to name instantiated `_items` or `_size` fields.
Coherent nonnegative index/list state and readable source/writable output
remain conditions. No bounds/error behavior, runtime closed receiver,
whole lookup loop or found value follows from this component.

The separately maintained
[`number-lookup owner`](../../scripts/game_data/memorypack/buff_blackboard_number_lookup.py),
[`whole selected CFG profile`](../../scripts/game_data/memorypack/blackboard_number_lookup.py)
and
[`reviewed lookup declaration`](../../scripts/game_data/contracts/memorypack_blackboard_number_lookup_native.json)
compose these dependencies through the complete managed-fallback loop and
both output returns. Every selected block belongs to the actual lookup's
entry or chained unwind extent. Incoming receiver, key and Double-output
aliases are preserved through the prefix. The selected element's key is
loaded into the low quadword of a saved XMM register and moved to the candidate
pointer; the
[Intel MOVQ definition](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf)
establishes this complete prefixed instruction's quadword transfer. Candidate
and original key lengths are compared before their owned String first-character
addresses and candidate length reach the actual managed comparison. No
global subset-decoder change or proximity-based fragment ownership is used.

The index starts at zero. Unequal lengths, unequal folded key units and
matching nonnumeric pairs all reach one increment and count comparison.
After the managed call, the volatile comparison-context source is reloaded
before this join. The signed continuation jumps to the existing unsigned
boundary branch, reusing the immediately preceding comparison's flags.
For stable coherent count and nonnegative Int32 index, the increment cannot
overflow before exhaustion; count minus index strictly decreases on every
rejection. This proves the arbitrary loop, rather than a fixed unrolled trace.
The unsigned list/array bounds and nonnull array guard are checked again
before full pair selection and before the found Double load.

The selected result is the first matching numeric candidate. A matching
pair whose string value is nonempty is skipped, so it does not hide a later
numeric pair with the same key. Found return copies the selected `valueDouble`
bits into the original caller output and returns true. Empty list or complete
exhaustion writes eight zero bits to that same output and returns false.
This selected lookup performs no numeric conversion and does not read the
pair's dynamic flag; these facts do not describe dynamic resolution elsewhere.
The output write reaches the original address before the common epilogue
restores the saved registers and frame.

This whole selected CFG proof requires normal dispatch guards, a false Burst
getter for every reached comparison, its ordinary returning-call preservation,
coherent stable list/String/dispatch state, readable inputs, a valid writable
output and normal completion. The pure comparison's preservation follows its
own checked program. The Burst getter's actual state and side effects are not
observed or promoted: stable referents across that call remain a condition.
Null/error/out-of-range, initialization/patch and enabled-Burst paths remain
outside the proof. Actual runtime objects or found values, public GetValue and
generic-provider composition, and complete action/root admission still need
their own evidence.

The separate maintained
[`keyed consumer/lookup owner`](../../scripts/game_data/memorypack/buff_blackboard_double_lookup.py)
and
[`call-boundary composition`](../../scripts/game_data/memorypack/closed_scalar_lookup.py)
now join the concrete nonzero-selector `TryGetValueInternal` to this complete
selected managed relation. Both existing owners authenticate their programs
against the same explicitly selected native inputs. The lookup declaration,
caller declaration and physical relative call must identify the same actual
registered method; a matching method name is insufficient. No duplicate native
catalog or invented live receiver is introduced by this composition.

The original incoming Blackboard and scalar's key become the lookup arguments.
The Double output argument addresses a separately initialized caller temporary,
and the companion argument is null. Derived stack regions place that temporary
outside the callee's shadow area and private frame. The lookup's explicit
stack stores and saved-register cells cannot overwrite it. The lookup saves
the caller's output-address alias before using that register for its key and
restores it on both selected returns. Ordinary called getters must preserve
the active frames and coherent referents; their unproved memory effects remain
conditions, rather than an assertion of complete memory-write coverage.

After the lookup returns, the caller loads the same temporary's Double bits,
copies them into its original output and restores its saved registers/frame.
These post-call instructions preserve `AL`. Thus, under both selected program
conditions, a found result writes the first matching numeric pair's Double
bits and returns true; exhaustion writes zero Double bits and returns false.
The keyed caller does not read its stored Single, perform a numeric conversion
or use that Single as a missing-key fallback. The zero-selector path's separate
Single-to-Double conversion remains subject to its own CPU/completion boundary.

The original keyed child receipts join their independently proved stored key
and normalized selector to this relation. Their Float32 bits are retained as
stored evidence even though the selected keyed program does not read them.
These joins require the same scalar instance and unchanged fields at consumer
entry, stable coherent lookup inputs, normal guards, every reached Burst getter
returning false, isolated valid Win64 frames and a writable final output that
does not alias those active frames. They do not supply the actual Blackboard
list or a concrete found value. Constructor/base-instance correspondence,
public GetValue/default behavior, physical generic helper/provider selection,
other dispatch and failure effects, runtime execution and complete action/root
admission remain separate obligations.

The maintained
[`normal default-chain owner`](../../scripts/game_data/memorypack/buff_blackboard_double_default.py),
[`complete default-program profile`](../../scripts/game_data/memorypack/blackboard_double_default.py)
and
[`reviewed default declaration`](../../scripts/game_data/contracts/memorypack_blackboard_double_default_native.json)
now prove the selected chain from concrete `GetValueOrDefaultInternal` through
Blackboard's `GetDoubleOrDefault` and `TryGetDouble`. These are distinct actual
method definitions. The named `TryGetDouble` body inlines the same independently
proved scalar cells: it keeps the Blackboard, scalar input and Double output
in separate saved aliases, then chooses the direct conversion or actual keyed
lookup. The complete direct and keyed returns preserve the chosen Boolean and
write the caller's eight output bytes. Its class/reference/dispatch guards are
authenticated as stored representation without inventing guard-owner meaning.

`GetDoubleOrDefault` captures the incoming Double default in a saved XMM
register before the named patch check. Under its false result and ordinary
returning calls, a true `TryGetDouble` result loads the same initialized output
temporary into the lower Double return lane. A false result copies the original
saved default bits into that lane. This choice performs no default-value
conversion or arithmetic; the Double default bits survive nonvolatile register
and frame restoration. The warning parameter is captured for the alternate
patch path and is not read beyond that capture in this selected normal program.
Its behavior outside that selection is not inferred from the parameter name.

The scalar default method similarly preserves its original Double default,
forwards the same scalar and nonnull Blackboard to the actual default callee,
passes a false warning Boolean and a null companion, and returns the callee's
Double lane through its complete epilogue. Its normal null-Blackboard edge
instead enters an authenticated helper-call followed by `INT3`, rather than
the selected default-return program. This proves the edge and instruction
sequence, not an exception kind, helper side effect or observed trap. Other
patch/null/error paths remain outside the normal default relation.

The original scalar child receipts now join these selected default paths under
the same-instance/unchanged-field condition. Direct fields select their
completed Single-to-Double result; keyed fields select the first matching
numeric Double or the caller-supplied default if lookup returns false. Original
stored bytes do not supply that API default argument. Stable lookup inputs,
normal guards, false patch/Burst selections, isolated valid frames and normal
instruction completion remain conditions. These proofs supply neither live
objects nor actual default or found values and admit no complete action/root.

Public `GetValue` retains a separate virtual-dispatch obligation. Current
owned-helper discovery locates its nonnull-Blackboard delegate's virtual entry
comparison against the concrete `TryGetValueInternal` entry; the matching arm
contains inlined scalar reads, while the other arm calls the selected virtual
entry. These helpers are not interchangeable with the named default methods.
The null-Blackboard delegate's on-disk tagged usage joins the closed
`BlackboardParamBase<float,double>.GetDirectValue` MethodSpec and its registered
physical call target. That stored usage does not establish a live MethodInfo
after lazy initialization; the maintained
[`registered MethodSpec join`](../../scripts/game_data/il2cpp/generic_entries.py)
and
[`static typed-usage validator`](../../scripts/game_data/il2cpp/formatter_composition.py)
keep those evidence layers separate. The public helper's unequal virtual-function
selection, initializer/context mutation and alternate dispatches still require
their own composition. The initialized null-Blackboard selection has a separate
complete return proof, described below.

The maintained
[`null-Blackboard public-return owner`](../../scripts/game_data/memorypack/buff_blackboard_null_getvalue.py),
[`selected return/tail profile`](../../scripts/game_data/memorypack/blackboard_null_getvalue.py)
and
[`reviewed null-return declaration`](../../scripts/game_data/contracts/memorypack_blackboard_null_getvalue_native.json)
authenticate the actual public entry, closed direct registration, concrete
metadata cast slot and all entry/chained-unwind windows of the three reached
bodies. Four complete selected programs cover public entry through its return,
both direct-delegate selector branches and the shared cast fallback through
its indirect tail. Tail programs have their own terminal checks; the shared
entry-to-RET validator is not weakened to accept unfinished delegates.

Under already-initialized public/direct flags and the public patch check
returning false, a null incoming Blackboard delegates the same scalar to the
closed direct entry. A zero selector forwards the actual metadata cast slot
and scalar to the shared helper after restoring the direct frame. The helper
computes the function/companion pair from the scalar's class and slot. Its
three special comparison targets belong to other current method bodies and
are distinct from the proved concrete scalar cast. If the computed function
equals that concrete cast entry, all three comparisons take their fallback
edges. The helper restores its saved registers/frame and tail-delegates the
same scalar with the companion in the context register. The independently
proved unpatched concrete cast completes its stored Single-to-Double lower
lane, which survives the public epilogue as the Double result.

A nonzero selector takes the direct entry's actual static string `LogError`
overload with its stored global message and null companion. After the logger
returns ordinarily, the direct program explicitly zeros the Double return
lane and returns through the public epilogue. This chosen branch neither
attempts Blackboard lookup nor reads the stored key or Single. The proved
logger identity and argument program do not establish actual log emission,
helper side effects or exception behavior.

The initialized direct programs overwrite their incoming context register
before reading it, and the chosen concrete cast does the same. Consequently,
their selected return instructions do not need a supplied live MethodInfo.
This does not prove usage initialization or context mutation: the stored
MethodSpec still establishes only the selected closed registration and actual
physical target. Likewise, the metadata slot and raw class-pair address
calculation do not supply the actual runtime class slot value; equality with
the concrete cast entry remains an explicit condition.

Unchanged original scalar receipts join these null-Blackboard choices under
the same-instance/field-state condition. Stable valid scalar/class/global
storage, isolated Win64 frames, ordinary helper returns, false reached patch
checks and completed SIMD conversion remain conditions. Actual runtime
selection and numeric values, unequal public virtual selection, other dispatch and
failure effects, provider selection and the remaining recursive action/root
joins retain their separate evidence obligations.

The maintained
[`nonnull public-return owner`](../../scripts/game_data/memorypack/buff_blackboard_nonnull_getvalue.py),
[`matching-Try return profile`](../../scripts/game_data/memorypack/blackboard_nonnull_getvalue.py)
and
[`reviewed nonnull declaration`](../../scripts/game_data/contracts/memorypack_blackboard_nonnull_getvalue_native.json)
now compose the initialized, unpatched public method with the helper arm whose
raw class function equals the current concrete `TryGetValueInternal` entry.
The metadata Try slot is authenticated independently of the helper's actual
function/companion loads and pointer comparison. All entry/chained-unwind
windows remain required even though the chosen complete programs exclude the
other dispatch and cold paths. No supplied runtime class slot follows from
the metadata declaration or this conditional equality.

The matching arm preserves separate scalar, Blackboard and public output
aliases. Under its normal stored class/reference guards, a zero selector
converts the same stored Single, writes the public Double output and returns
true. The public method then loads those exact output bytes into its Double
return lane. A nonzero selector passes the stored key and original Blackboard
to the independently proved managed lookup. Its complete arbitrary-length
loop supplies the first matching numeric Double and true, or exhausted-list
zero and false. The helper copies the same temporary into the public output
and restores its saved registers/frame without changing the lookup Boolean.
The public success arm returns those Double output bits.

The helper's temporary uses an unused part of its incoming Win64 home space,
between distinct saved-register cells. This differs from the earlier concrete
consumer's private temporary allocation. The independently authenticated
lookup non-output write ledger remains in its private frame or the helper's
provided shadow space, away from that temporary. The helper's frame, saved
cells and temporary are also separate from the public method's output cell.
The ordinary called helpers must preserve those active frames and coherent
referents; their unproved memory effects are not replaced by an assumption
that the named method has no other writes.

On the selected false lookup result, the public method loads the key from the
same scalar, calls the actual `DumpToString` on the original Blackboard and
preserves that returned string across its class helper. Its complete logger
argument program forwards the channel byte, format reference, key reference,
dump reference and reloaded context companion in their actual ABI positions.
After the actual logger returns ordinarily, the public method explicitly zeros
the Double return lane and restores its frame/registers. This path does not
read the stored Single or use it as a missing-key fallback. The dump/logger
identities and arguments do not prove their emitted text or other effects.

The logger join keeps a newly established static distinction: the calling
usage cell describes `LogError<string,string>` and has no AOT registration row
in the selected build, whereas the actual call target has an unambiguous
`LogError<object,object>` registration under the same method definition. Both
generic parameters have reciprocal current method ownership and ordinal.
These facts establish the two static identities and physical callee; they do
not equate the MethodSpecs, supply a live MethodInfo or prove the initializer
and generic context behavior. The generic-entry resolver's folded-definition
rejection remains intact.

Original scalar field receipts now join the selected nonnull public returns:
direct fields choose the completed conversion, while keyed fields retain both
conditional found and missing outcomes. Actual instances and lookup contents
are unsupplied. Initialized public usage state, false patch, matching concrete
Try function, normal stored guards/managed-loop selections, stable compatible
storage, valid isolated private frames/home spaces, ordinary dump/logger calls
with compatible context and completed SIMD remain explicit conditions. The
unequal virtual-function arm, other initialization/patch/failure effects,
actual provider/runtime selection and complete recursive action/root admission
still require their own evidence.

The `get_Count` pointer is folded with
other method definitions, so it remains an ambiguous witness rather than an
exclusive method or a missing registration. Alternate dispatch,
refill/failure parity, provider selection,
actual runtime effects and complete action/root admission remain unresolved.

For `TriggerSpellBurstEventAction`, the
[`reviewed source window`](../../scripts/game_data/contracts/buff_18b_native.json)
has a required terminal DWORD, now joined to the stored `spellBurstType` enum.
Original spans preserve these bits without an enum-range restriction. The
current `ExecuteInternal` candidate has a checkable `readsClosedDataField` claim
for that field through the immediate `AbilityAction<Data>::m_data` parent.
The maintained
[`closed-field proof`](../../scripts/game_data/il2cpp/closed_data_fields.py)
uses the concrete witness and occupied base layout, without taking a generic
definition's field offset as an instantiated offset. Its separate source and
owner paths check `NeedTriggerEvent` before the compiled `TriggerEvent` calls
for `OnCharBeforeOutputSpellBurst` and `OnEnemyBeforeTakeSpellBurst`.
The local DWORD transfer names the destination `SpellInflictionContext.inflictionType`
only conditionally on that context layout and the reloaded output-slot identity.
The actual static allocation usage names that context, while the
[`generic entry checker`](../../scripts/game_data/il2cpp/generic_entries.py)
finds no exact registered entry for the selected closed allocation instance.
The physical shared code still joins to the `Allocate` method definition.
Keep that closed-instance registration gap explicit: the candidate does not
establish allocation outcome, slot stability across delegated calls, selected
MethodInfo, IFix branch, event delivery, damage, or live execution. Consumer
claims and named action admission remain staged while the earlier complete
family gate freezes the maintained implementation.

The maintained
[`buff_custom_ability_event_condition.py`](../../scripts/game_data/memorypack/buff_custom_ability_event_condition.py)
and its reviewed
[`buff_custom_ability_event_condition_native.json`](../../scripts/game_data/contracts/buff_custom_ability_event_condition_native.json)
compose CheckCustomAbilityEvent's separate `eventName` BlackboardString and
required following `savedParamKey`. The former reuses the independently
named three-member child, preserving its key, selector flag and value bytes;
the latter additionally uses the independently authenticated current UTF-8
source helper. Null wrapper, null BlackboardString and null/empty parameter
keys remain distinct. The child's endpoint cannot omit the following key.
Current source/destination and dispatcher proofs establish authored operands,
not event matching, parameter capture or a condition result.

The reviewed direct-target contract's named-record version in
[`buff_direct_target_actions_native.json`](../../scripts/game_data/contracts/buff_direct_target_actions_native.json)
adds ForceHideHeadBar and RecoverFromPoiseBreak through the existing
[`buff_direct_target_actions.py`](../../scripts/game_data/memorypack/buff_direct_target_actions.py)
owner. Each new record independently proves its source-result assignment,
generated field order and closed TargetSettings context. ForceHideHeadBar's
`finishByAction` byte is required before its target; RecoverFromPoiseBreak
has no extra field between the inherited members and its final target.
The new named records separately admit null wrappers and null targets, retain
arbitrary flag/enum bits and require physical action end. Positive targets
must reproduce their same original ranges through the recursive child owner.
Selected native inputs, including UnityPlayer, are checked before and after
the validation; missing or changed inputs empty the result. Complete root
and canonical original-owner gates remain independent of selected action-span
diagnostics. Stored flags and target settings establish neither head-bar
behavior nor accepted poise-break recovery.

The maintained
[`buff_finish_global_action.py`](../../scripts/game_data/memorypack/buff_finish_global_action.py)
and
[`buff_finish_global_action_native.json`](../../scripts/game_data/contracts/buff_finish_global_action_native.json)
now own FinishGlobalBuff's nine-member parent and its conditional original-value
ID list. The parent proves its own source/destination order and current union
route; it composes the independently owned Blackboard scalar `finishCount`
on the same original range. The required `isFinishedEarly` byte follows the
complete ID list, including null and empty lists. Exact action end remains
required. Stored flags and evaluated finish count are separate evidence lanes.

Its ID collection is independent of Stack's reference-element collection. The
[`buff_global_creation_action_native.json`](../../scripts/game_data/contracts/buff_global_creation_action_native.json)
and [`buff_global_creation_action.py`](../../scripts/game_data/memorypack/buff_global_creation_action.py)
establish GlobalBuffId's value wrapper and addressed string reference. The new
profile authenticates exact ListFormatter and original-value adapter entries,
the source-list element's type pointer, value size and generic ownership. It
keeps the registered adapter's Object wrapper argument explicit; ordinary
inflation to the concrete wrapper is a condition, not an observed MethodInfo.
Runtime reference width does not establish wire framing.

The collection profile independently authenticates the buffered signed Int32
count and its four-byte cursor accounting, minus-one null list and the element
loop with a cleared eight-byte value slot. A fixed-slot call forwards the same
reader, original output and receiver MethodInfo. The shared
[`formatter_composition.py`](../../scripts/game_data/il2cpp/formatter_composition.py)
checker also proves the original-list registration using typed usage cells,
exact source/formatter element pointers, matching generic instantiation,
constructor/register call targets and allocation-result object flow. The
reviewed byte windows authenticate explicit arithmetic instruction programs
where the general body decoder has no operand support; no undecoded operand
is inferred from a diagnostic disassembly row.

Default registration has two independently checked static paths.
`MemoryPackGeneratedInit_Gameplay_Beyond.InitEager` allocates the concrete
GlobalBuffId/GlobalBuffIdForMemoryPack adapter and forwards that same object
with the exact original type key to `RegisterWrap`. The FinishGlobalBuff
wrapper's `RegisterFormatter` separately retains its allocated
ListFormatter object through its matching constructor and passes it to
`Register<List<GlobalBuffId>>`. That registration's generic argument is the
exact source-list carrier, and the formatter's element pointer is identical
to the source-list element pointer. The ID wrapper's own registration covers
its wrapper and wrapper array; it is not the original-list registration site.
These object/type flows are direct static evidence, conditional on executing
the initialization sites. They do not establish a later provider/cache return
or the inflated companion passed to a shared physical adapter entry.

The same maintained composition checker also validates the concrete ID
wrapper's `IMemoryPackDeSerializeWrapper<GlobalBuffId>` interface argument,
its GetValue virtual slot and exact original return-type pointer. Its concrete
formatter Deserialize slot forwards to the already reviewed ID reader.
Selected module/token ranges separately preserve generic-parameter ownership
through ListFormatter, the generic adapter, ReadPackable/ReadValue and
GetFormatter contexts. A shared leaf getter needs only its explicit MOV/RET
program; a diagnostic native-unwind extent can include neighboring methods
and is not a semantic method boundary. These identities narrow the missing
conversion join without proving which inflated MethodInfo or stateful
provider result the collection used.

The actual adapter's null probe first peeks at the null marker without moving
the reader. Its true branch then consumes one byte and the adapter clears the
original value slot. On the non-null branch, the checked concrete formatter
avoids the dispatcher's optimized pointer alternatives and follows its
generic fallback with the same reader/output. The concrete wrapper's interface
offset selects its checked GetValue slot; the getter reads the ID field and
the adapter writes the returned reference into the original value slot. This
conversion is conditional on the reviewed concrete formatter/wrapper,
ordinary generic inflation and successful initialized-buffer calls. Refill,
error, allocation and stateful provider paths remain unresolved.

Under that explicit composition, the stored reader preserves list order,
null versus empty list, null wrapper versus null payload versus empty payload,
raw ID bytes and the required following parent flag. IDs are not assigned an
unproved text encoding. Independently named parent/list reads reproduce
selected complete original action spans; candidate enclosing Timeline/event
ownership is still separate. The complete current Buff family and independent
canonical original-byte root gates decide coverage. These storage and static
composition proofs establish neither evaluated IDs/finish count nor which
global Buff instances finish, finish reasons or resulting effects.

The reviewed names-only consumer groups in
[`buff_action_consumers_native.json`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
separately prove FinishGlobal's incoming owned closed `m_data` slot, its
configuration reads and compiled calls to list count/indexing, Blackboard
evaluation, parent-root lookup, RemoveGlobalBuff and MarkFinish. Its
`finishCount` reference reaches the named `GetValue.param` parameter on a
checked local compiled path. The default fallthrough traversal skips that
field on the `finishAll` path, so the count claims explicitly select the
existing complete local-branch validator. This proves a compiled path,
without asserting branch feasibility or runtime selection.

Its false-IFix `get_executeReturnType` path returns the typed
`AlwaysReturnTrue` enum policy through a complete epilogue. It does not return
the `CustomReturnType` policy used by other reviewed actions, and this enum
getter is distinct from a Boolean method named AlwaysReturnTrue.
Additional selected-program joins use the independently derived closed Data
layout and actual callee parameter types: on the checked normal parent/list
paths, the owned `isFinishedEarly` byte is compared with zero and SETNE is
forwarded into the declared byte-sized FinishReason argument. Zero selects
Default and nonzero selects Early. Server remains a declared enum alternative
that these two argument programs do not generate. Those argument programs
remain isolated from the maintained names-only claim vocabulary and never
establish which manager or global Buff instance was selected.

The `finishAll` branch loads an exact float32 minus-one constant before the
same conversion helper used after Blackboard evaluation. The actual helper
has additional calls, sign-dependent branches and SSE conversions that the
general body decoder does not fully decode. Do not replace it with an assumed
ordinary integer cast, assign minus one's gameplay meaning, or infer accepted
removal counts. Count arithmetic, receiver identity, finish acceptance and
effects still require their own proofs.

BlowOffAction has a maintained seventeen-member reader under
[`buff_blow_off_action_native.json`](../../scripts/game_data/contracts/buff_blow_off_action_native.json)
and [`buff_blow_off_action.py`](../../scripts/game_data/memorypack/buff_blow_off_action.py).
Its selected source owns two TargetSettings fields, six BlackboardDouble
operands, DirectionSettings, the common action fields and interleaved byte/DWORD
operands. The
[`inherited setter checker`](../../scripts/game_data/memorypack/inherited_setter_output_sources.py)
authenticates the four common base setters, the derived cached-instance getter,
complete source argument/return transfers and the selected owned-field stores.
Wrapper reloads come from the checked ref-wrapper slot; other RSI writes after
the first reload refuse. Primitive buffered programs prove byte normalization,
DWORD reads and cursor accounting. An enum declaration or reference output
size is not substituted for that source proof.

Targets and nested direction targets compose their independent recursive
readers; each BlackboardDouble has its own source-bound child receipt. A scalar
child audit retains its actual `nativeStatus`/source-store/read-order shape and
the separately authenticated owning contract's native pins. Missing or stale
audits refuse instead of adding nonexistent fields to an earlier return.
Original independently framed action intervals close every named field and
reproduce the same full receipt through the maintained recursive dispatcher.
This is component admission only; the containing roots still require a new
complete-family gate and independent original-root replay. Distance, height,
direction conventions, timing, target choice and live effects remain unresolved.

SelfRotateAction's selected source in
[`buff_144_native.json`](../../scripts/game_data/contracts/buff_144_native.json)
has a maintained eighteen-member reader in
[`buff_self_rotate_action.py`](../../scripts/game_data/memorypack/buff_self_rotate_action.py),
with reviewed declarations in
[`buff_self_rotate_action_native.json`](../../scripts/game_data/contracts/buff_self_rotate_action_native.json).
It uses direct stores. The generated order and actual source/destination joins identify the
four common action fields, advanced DirectionSettings, five Boolean flags,
the root-motion animation string, direction/frame/rotation DWORD fields,
the raw Single rotation rate, TargetSettings and the final advanced-direction
flag. Stored raw Boolean bytes and Single bits remain separate from normalized
runtime values and evaluated rotation behavior.

The maintained
[`common direct-source checker`](../../scripts/game_data/memorypack/inherited_direct_action_sources.py)
independently proves this source's four common buffered operands, reader and
wrapper aliases, null guards and stores through the declared base Data field.
Derived fields instead pass through the cached-instance getter before direct
stores. Reference stores have a following barrier call; the Single result is
saved in XMM6 across the getter, and the final Boolean uses a different register
after the last wrapper dereference. The
[`getter direct-output checker`](../../scripts/game_data/memorypack/getter_direct_action_sources.py)
authenticates every selected derived argument and source-result bridge, the
typed cached getter normal return, actual owned field offsets, and the final
Boolean save. The Single store follows the next member's scheduled reader and
wrapper arguments; the checker verifies the complete interleaved instructions
and the shared previous-store identity instead of assuming a contiguous
argument-only prefix. DWORD enums retain their closed source contexts and
independent four-byte buffered source proof.

The maintained reader composes independent UTF8, DirectionSettings and
recursive TargetSettings readers, with exact child spans and a required action
end. Current native validation and original component replay establish this
component scope; recursive dispatcher receipt equality is checked separately.
Containing roots still require a complete-family gate and independent original
root replay. Getter initialization/cast/failure paths, reference barrier effects,
rotation conventions and actual runtime effects remain unresolved.

The maintained `buff_blow_off_character_action` reader uses the selected
BlowOffCharacter source windows in `buff_1c_native.json` and its reviewed
[`buff_blow_off_character_action_native.json`](../../scripts/game_data/contracts/buff_blow_off_character_action_native.json)
contract. Its distinct blackboard priority child has four required members:
key, key-selection flag, integer value and final custom-value flag.
`inherited_reference_sources` independently authenticates the runtime and
wrapper inheritance chains and concrete setter programs; it does not widen
the immediate-owner profile with guessed inherited offsets.
The runtime's closed generic parent and the base wrapper's instance field share
the exact generic-class carrier and instantiation; their field attributes
differ. The generic definition's offset table is not an inflated instance
layout. Its VAR payload is a metadata parameter index, whose reciprocal
container join supplies the ordinal; the displayed VAR number must not be
used as that ordinal. The generated integer setter's parameter pointer matches
the argument selected by this owned ordinal.

The inherited generated setters separately establish the key, key-selection
flag and value stores through the wrapper's base-instance field. The original
priority reader's normal source-result bridges reach those same stores.
Its final custom-value flag follows a distinct generated setter and instance
getter. The ordinary buffered Boolean source consumes one byte and returns
its nonzero normalization; the integer source consumes and returns four
raw bytes. Both update the same reader's current pointer and consumption
slots. The key uses the independently proved nullable signed-length UTF-8
source. Raw flag bytes remain distinct from their normalized stored values.
The custom getter's coherent non-null cache path returns the identical
underlying base instance; cache initialization and cast success remain
explicit conditions, rather than inferred synchronization.

The parent composes this child with two independently owned TargetSettings,
DirectionSettings and four nullable BlackboardDouble values in its proved
source order. The required fourth priority flag ends before the parent's
direction-angle value; a member-three Blackboard record cannot replace it.
The maintained readers reproduce complete original action spans. Complete
current-family and canonical original-byte root gates separately decide
enclosing admission. Evaluated priority/speeds, replacement and armor
decisions, selected targets, root motion and live blow-off effects remain
unresolved; a matching stored field or setter does not establish them.

The maintained names-only BlowOff consumer groups separately prove the
incoming owned closed `m_data` slot and its two target-setting references.
`attackerTargetSettings` reaches `GetFirstTarget.targetSettings`, while
`targetSettings` reaches `GetTargets_Dispose.targetSettings` in the ordinary
compiled prefix. A later same-body `GetTargetsView` name does not substitute
for this actual call-site identity. On the false selected IFix guard, the
return-policy getter returns the typed `CustomReturnType` enum through its
complete epilogue. This policy is separate from the action's Boolean result.
Later priority, speed, direction and ApplyBlowOff operands still need their
own supported instruction and ownership proofs; the large consumer body
contains SIMD/atomic operations outside the current complete decode profile.
Neither these narrow groups nor an ApplyBlowOff name proves selected targets,
accepted movement, replacement/armor decisions or live effects.

The separately reviewed
[`buff_blow_off_consumer_flow_native.json`](../../scripts/game_data/contracts/buff_blow_off_consumer_flow_native.json)
and `buff_blow_off_consumer_flow_native` loader authenticate a narrower local
return program. The actual `ApplyBlowOff` callee returns Boolean. After its
ordinary return, the selected caller updates the loop index, then overwrites
EAX with the loop count before its checked local back edge; no returned
AL/EAX/RAX value is consumed by that program. This proves a local discard,
not the whole caller's result or CFG. The action's CustomReturnType policy
and an accepted individual blow-off operation must therefore retain separate
evidence boundaries. The generic `il2cpp.call_result_discard` checker requires
the Boolean ABI, contiguous authenticated instructions, complete EAX overwrite
and an in-owner back edge; it does not need to decode the earlier SIMD/atomic
paths or infer gameplay success from a call name.

The selected `buff_timeline_empty_native.json` root context likewise exposes a
closed `List<TimelineAction.TimelineActionData>`. Its element type definition
matches the exact reference field held by the generated TimelineActionData
wrapper already reviewed in `skill_timeline_play_animation_native.json`; this
is a current metadata identity join, beyond a historical name match. Reuse the
four-member element evidence independently of SkillData's ActionGroup envelope
and first-record policy. Do not invent a SkillData prefix to pass Buff bytes
through a Skill root decoder. Positive Buff lists still need their own formatter
and nullable element parity, original spans, reached recursive actions and the
following trigger tail before gaining whole-root coverage.

[`buff_timeline_element_sources`](../../scripts/game_data/memorypack/buff_timeline_element_sources.py)
now owns the positive source elements independently of either root envelope.
Its reviewed
[`buff_timeline_element_sources_native.json`](../../scripts/game_data/contracts/buff_timeline_element_sources_native.json)
requires one authenticated entry-to-final-store program per wrapper. Timeline
reads `_endFrame`, `_sequenceActionData`, `_startFrame`, then
`forceSyncAnimData`; ForceSync reads `forceSync`, `montageName`,
`playbackSpeed`, then `targetFrame`. The shared `buffered_owned_sources`
algorithm checks actual local successors, the byref-reader/ref-wrapper ABI,
the wrapper's exact typed instance field, closed reference contexts, complete
buffered Int32/bool helpers, inline scalar cursor accounting and every owned
destination. Partial pointer writes, lost source values, wrong counters and
incomplete field programs refuse. Ordinary nonvolatile preservation across
returning calls remains conditional; the four-member header and source order
come from instructions, not runtime object size or setter address order.

The focused element codec takes absolute offsets into the original file,
reuses the independently gated Sequence reader for each reached action and
accepts only valid UTF-8 through the authenticated string helper. It preserves
raw flag, integer and floating-point bits and requires the exact element end.
Its `positiveSourceFieldsExact` receipt deliberately keeps
`recursiveStoredSchemaExact`, `positiveListAdmitted` and `wholeRootAdmitted`
false. Null Timeline/ForceSync runtime references, the list's count/loop and
conversion chain, preceding root fields and the following trigger tail remain
independent obligations. The registered Object shared-code adapter and list
entries are useful static candidates; their Object arguments must not replace
the original closed Timeline or ForceSync context. Actual provider, cache and
inflated MethodInfo selection are unresolved.

[`buff_timeline_composition`](../../scripts/game_data/memorypack/buff_timeline_composition.py)
adds an independent static registration proof, governed by
[`buff_timeline_static_composition_native.json`](../../scripts/game_data/contracts/buff_timeline_static_composition_native.json).
Generated wrapper `RegisterFormatter` methods register the concrete wrapper
formatter and wrapper array; the original runtime adapters are registered in
the separate generated `InitEager` owner. That owner allocates each exact
original/wrapper adapter, retains the object across its constructor calls,
resolves the original type handle, and passes the same object and returned
type key into `RegisterWrap`. Its concrete constructor thunks reload the
identical closed constructor MethodSpec before tail-jumping into separately
registered shared code. Absence of an exact closed generic table entry is
therefore not evidence that this concrete registration is absent; the actual
thunk, context and target must be joined. The shared Object/Object entry
identifies physical code and never replaces either concrete type argument.

The reusable `il2cpp.formatter_registration` checks complete static object/key
programs, exact allocation and registration type pointers, constructor thunk
contexts, typed helper signatures and concrete wrapper registration. The
composition additionally authenticates conversion interfaces and formatter
vtables. A typed reference `GetValue` loads the wrapper's owned original
instance, while the warmed formatter tail path preserves the same byref reader
and wrapper output into that wrapper's static source reader. Buff initialization
separately registers the original Timeline runtime-data list: its formatter
element pointer and registration carrier match the root's actual ReadPackable
context, rather than a list of generated wrappers.

This static validator remains outside root admission. It gates all native
inputs before and after validation and returns no proved rows after build
drift. Successful registration and forwarding checks do not establish that
initialization ran, that the provider/cache returned those objects, that a
nullable reference converted correctly, or that the list loop consumed its
original variable-width elements. These are separate obligations before the
source-only element receipt can gain a stored-list or whole-root claim.

[`buff_timeline_reference`](../../scripts/game_data/memorypack/buff_timeline_reference.py)
and its reviewed
[`buff_timeline_reference_native.json`](../../scripts/game_data/contracts/buff_timeline_reference_native.json)
separately authenticate the shared reference declarations, complete buffered
null path and selected conditional non-null conversion. The instance `Deserialize` takes the reader and original output by
reference. Static `DeserializeNotNull` instead takes a third `wrap` argument
by value. The selected complete helper program carries that incoming value
through the wrapper formatter's local byref slot; it does not presume an
initially null value or confuse it with a byref incoming wrapper. Each open
VAR ordinal is checked against the owning class generic container; shared Object registration
continues to identify physical code rather than concrete runtime inflation.

The reusable `reference_nullable_sources` checks the initialized, available-buffer
entry-to-return path without omitting pointer aliases, selected guard edges,
counter stores or the epilogue. Its original-byte `FF` comparison precedes
consumption: the null branch subtracts one remaining byte, advances the buffer
pointer and both counters once, and clears the original output reference.
The eight-byte output is runtime reference storage, not wire payload width.
Native drift discards this scoped proof. Source-wrapper refill/error paths,
original child dispatch, list iteration and actual provider
selection remain open; neither this proof nor a passing positive source element
admits an enclosing positive list or root.

Nonvolatile ABI preservation applies across returning calls. It does not
establish that the selected caller itself preserves a reader alias while
running its cache/query logic. The reusable
[`reference_conversion_sources`](../../scripts/game_data/memorypack/reference_conversion_sources.py)
tracks saved entry slots, temporary register reuse and the actual reader reload
on the selected initialized cache-hit branch. The same input reader and preserved
incoming wrap slot reach formatter slot five; the caller reloads the output
wrapper afterward. A null wrapper clears the original output. Otherwise the
same wrapper reaches slot zero of the original-value conversion interface and
the getter's reference return is stored into the original output. Both selected
paths include their epilogues and own every selected successor through return.

The context proof dereferences the static RGCTX payload indices rather than
trusting their recorded names. Reciprocal class-parameter ownership joins the
provider, formatter and Deserialize to the wrapper parameter, and the conversion
interface and GetValue to the distinct original parameter. Both concrete wrapper
interface tables place that typed interface after an earlier nonmatching pair;
the selected helper proves the actual ordinal increment and repeated lookup.
Concrete formatter and getter pointers differ from the helpers' optimized
special cases, so the complete ordinary-call fallback forwards the receiver,
reader/output references and MethodInfo, and preserves the getter return.

These are conditional selected programs. They assume compatible inflated runtime
contexts, the reviewed concrete provider result, normal returning calls and the
recorded guard outcomes, including the selected suffix without a GC barrier.
They do not prove cache misses, alternate probe repetitions, runtime context
inflation or provider state. The instance adapter's inlined logic is validated
independently; resemblance to the static helper never substitutes for that proof.

[`buff_timeline_instance`](../../scripts/game_data/memorypack/buff_timeline_instance.py)
and its reviewed
[`buff_timeline_instance_native.json`](../../scripts/game_data/contracts/buff_timeline_instance_native.json)
now prove the selected positive parent paths through both original-output stores
and complete returns. The positive non-FF peek consumes no bytes directly. The
parent saves its Reader and output references, passes the wrapper-owned
CreateInstance MethodInfo, preserves the returned wrapper in a local slot and
dispatches its formatter with that same Reader and slot. A null child output
clears the original; a non-null child reaches the original typed interface and
stores its getter return. Provider and Activator method parameters each have
reciprocal ownership, and both method instantiations bind the adapter's wrapper
parameter rather than its distinct original parameter.

The concrete wrappers' metadata has the abstract mask clear. Conditional on the
selected RuntimeType returning those same attributes, the parent therefore takes
the Activator branch. The direct-zero alternative cannot stand in for concrete
wrapper creation. The actual call matches the independently registered shared
CreateInstance entry. A separately authenticated class-key prefix proves that
unused incoming Reader/output pointer bits in argument registers are overwritten
before use on that selected helper path; it does not prove a complete helper
return or cache purity. The type-attribute dispatch proves its class Int32 read,
while the runtime class-to-metadata bridge remains conditional. Full Activator
invocation, allocation, cache/provider and global effects, child cursor
composition and alternate paths remain open. This parent proof stays outside
positive-list and whole-root admission.

[`buff_timeline_source_wrappers`](../../scripts/game_data/memorypack/buff_timeline_source_wrappers.py)
and its reviewed
[`buff_timeline_source_wrappers_native.json`](../../scripts/game_data/contracts/buff_timeline_source_wrappers_native.json)
separately close the initialized, available-buffer source `FF` path for both
concrete wrappers. It consumes one byte, updates all four Reader cursors and
clears the wrapper byref itself before completing the return. It does not
write the original instance's fields. One source restores its caller frame and
tail-jumps to the actual reference barrier; the other calls that barrier and
returns through its own epilogue. The independently proved disabled-barrier
path copies the output address and returns without a memory write or call;
the runtime flag state is a condition.

The same lane proves each concrete wrapper constructor's selected non-null
allocation path. The original-type usage descriptor is authenticated, the
wrapper receiver survives the allocation call, and the exact returned reference
is stored into its metadata-owned `__instance` field before the complete return.
This establishes the local field assignment under a compatible allocation
return; it does not prove allocation contents, actual Activator constructor
invocation or active barrier behavior. Source null semantics, positive field
reads and parent reference conversion have distinct ownership scopes. Their
proofs still require original child cursor composition before an enclosing
stored list can be admitted. The tracked positive-source contract records
separately closed `MemoryPackReader.ReadValue` MethodInfos for SequenceActionData
and ForceSyncAnimData at the same actual helper call target. A passed MethodInfo
name does not establish body identity with a registered shared entry. Keep this
child `ReadValue` join distinct from the root list's `ReadPackable` dispatch.

[`buff_timeline_source_returns`](../../scripts/game_data/memorypack/buff_timeline_source_returns.py)
and its reviewed
[`buff_timeline_source_returns_native.json`](../../scripts/game_data/contracts/buff_timeline_source_returns_native.json)
extend the same independently proved positive Timeline and ForceSync field
programs through their complete returns. The suffixes restore the exact caller
stack and saved nonvolatile registers, with no further calls, object writes or
Reader cursor writes. Timeline requires the final reference-store barrier's
disabled branch; ForceSync also restores its saved nonvolatile vector before
the last scalar field store. This removes the earlier last-store boundary from
the source proof. It does not supply the missing nullable original child cursor
composition or infer child wire widths from the epilogue.

[`buff_timeline_read_value`](../../scripts/game_data/memorypack/buff_timeline_read_value.py)
and its reviewed
[`buff_timeline_read_value_native.json`](../../scripts/game_data/contracts/buff_timeline_read_value_native.json)
now authenticate that actual helper's complete selected ABI and output return.
Its separately registered `ReadValue<Object>` entry differs from the called
physical entry, so named body identity stays unresolved. Reciprocal method
parameter ownership joins the closed Reader context to the provider key,
expected formatter class and slot-five Deserialize; the latter takes the same
Reader and original output by reference. The outer physical helper initializes
one local original output, forwards the saved Reader and that local, then
returns the same local in the full-width return register. It reads no Reader
fields and updates no Reader cursors directly.

The original adapter pointer matches the dispatcher's first optimized case.
That case inlines adapter logic; the already proved ordinary fallback cannot
replace it. The reusable
[`read_value_reference_sources`](../../scripts/game_data/memorypack/read_value_reference_sources.py)
owns the selected instructions, guard outcomes, context slots, locals, physical
calls and epilogues for all three output paths. Its FF branch consumes one
byte, updates all four cursors and clears the original output. Positive paths
preserve the Reader and original output, select the wrapper-owned Activator
context, save the returned wrapper, and call the actual physical wrapper
GetFormatter helper before nested formatter dispatch. The nested output either
clears the original or reaches its typed conversion interface and getter return.
The non-null output path selects the disabled-barrier state. Runtime cache,
class/context/provider selection and correctly typed normal callee returns
remain explicit conditions; anonymous cache fields do not establish collection
semantics or branch feasibility.

The known Timeline, ForceSync and Sequence wrapper formatters use the
independently proved nested ordinary fallback. The physical wrapper GetFormatter
helper's selected typed return is independently joined below. Its full effects,
original nullable child cursor composition, other paths
and root ReadPackable/list composition remain separate obligations. This scoped
transfer proof admits no child grammar, positive list or whole root and does not
observe runtime execution.

[`buff_formatter_provider`](../../scripts/game_data/memorypack/buff_formatter_provider.py)
and its reviewed
[`buff_formatter_provider_native.json`](../../scripts/game_data/contracts/buff_formatter_provider_native.json)
prove the actual helper's complete selected context and return transfer. The
incoming MethodInfo remains the same while its owned first context slot supplies
the type key and its second supplies the expected formatter class. The selected
cached candidate reaches the formatter-result helper; its non-null result is
checked against that expected class and returned as the identical full-width
reference through the complete epilogue. The body writes only caller stack
slots directly, but two indirect global calls have unproved effects. Stable
non-aliasing contexts, the selected initialized cache and correctly typed normal
helper returns remain explicit conditions. A different independently registered
Object entry still prevents promoting the physical clone to a named body.
Both the child ReadValue and selected list-control contracts require this proof;
a missing dependency cannot preserve their provider-return join. This closes
value and context transfer, not original child cursor accounting, provider/cache
effects, runtime selection or stored list/root admission.

[`buff_sequence_composition`](../../scripts/game_data/memorypack/buff_sequence_composition.py)
and its reviewed
[`buff_sequence_static_composition_native.json`](../../scripts/game_data/contracts/buff_sequence_static_composition_native.json)
independently establish SequenceActionData's concrete static composition. The
generated eager owner allocates the exact original/wrapper adapter, preserves
that object and the original type key through the closed constructor thunk,
and passes them together to RegisterWrap. The thunk reloads the identical closed
constructor context before entering the independently registered shared code.
The wrapper's RegisterFormatter allocates and passes its own concrete formatter
to Register<Wrapper>. Both selected blocks are checked inside their named
physical method extents. Allocation-null guards accept the exact short or near
JE encoding; a different condition fails the proof.

The Sequence wrapper's owned original-instance field, typed getter, conversion
interface and slot-five formatter are joined to the independently proved
Sequence source. Its warmed formatter preserves the same Reader and output
byrefs into that source. The actual formatter/getter pointers differ from all
optimized special cases, and the typed interface follows an earlier nonmatching
pair, so the complete nested ordinary-call and interface-lookup programs apply.
This composition is now a required dependency of the ReadValue contract; a
missing or mismatched dependency cannot leave the old concrete-selection gap
silently resolved. Metadata has the abstract mask clear, with runtime attributes
for the same class remaining a condition. Initialization, actual provider
selection, allocation/constructor effects and original Sequence cursor
composition remain unobserved or unproved. Static composition grants no list
or root admission.

[`buff_sequence_array_source`](../../scripts/game_data/memorypack/buff_sequence_array_source.py),
[`array_reference_sources`](../../scripts/game_data/memorypack/array_reference_sources.py)
and the reviewed
[`buff_sequence_array_source_native.json`](../../scripts/game_data/contracts/buff_sequence_array_source_native.json)
now prove the complete selected buffered array control inside that named
Sequence source. Its actual usage is `ReadArray<AbilityActionData>`; the single
owned context slot joins the `ReadArray(ref T[])` overload, whose reciprocal
method parameter independently binds Empty, the array class, provider,
formatter class and slot-five Deserialize. A similarly named ArrayFormatter
is not evidence for this inline path. Static context records are not runtime
context slots, and the proof does not observe their inflation or selection.

Complete wrapper-FF, null-array, empty-array and single/repeated positive-element
programs authenticate every selected successor through return. They prove the
signed count and remaining-length guard, all four direct cursor updates, the
allocation/count and provider arguments, the unchanged Reader, the repeated
child-call block and both ordered normalized flag stores. The caller advances
seven direct bytes for a nonnull Sequence, plus the child advances; the child
advances themselves remain unresolved. A wrapper FF advances one byte and
clears the wrapper reference through the independently proved disabled barrier.
The runtime element address is array base plus its data offset and index times
reference stride; this says nothing about a child wire width.

The selected paths require warmed compatible contexts/classes, stable
non-aliasing typed objects and local storage, valid buffered/counter bounds,
normal correctly typed helper and child returns, disabled reference barriers
and the Win64 stack/nonvolatile ABI. Full return includes exact stack and
nonvolatile restoration. Passing an Empty MethodInfo to a physical helper does
not name that helper or prove its managed effects. Empty/allocation identity
and effects, child grammar/cursor composition, alternate GC/refill/error/reuse
paths and runtime selection remain open. This source control proof grants no
child, positive list or complete root admission.

[`buff_timeline_list`](../../scripts/game_data/memorypack/buff_timeline_list.py)
and its reviewed
[`buff_timeline_list_control_native.json`](../../scripts/game_data/contracts/buff_timeline_list_control_native.json)
add a separate selected list-control proof. The buffered header reads a signed
Int32 count, consumes four bytes and updates all four Reader cursor fields.
Its count guard compares against `totalLength - consumed`; this guard does not
determine any element's wire width. The loop retains the same Reader, clears a
local reference before each element dispatch and loads both the method and its
MethodInfo from formatter slot five. It appends the returned reference using
the runtime array's pointer stride, increments the index and compares against
the saved original count. Temporary reuse of the count register does not replace
that saved count. A separately authenticated repeated program reaches the same
complete block through the actual back edge, and both paths include the return.

Static reciprocal ownership joins List, Clear, GetFormatter, element formatter,
Deserialize and Add to the same original element parameter. The selected
programs cover an existing list with spare capacity and normal returning calls.
The physical helpers receiving Clear and GetFormatter contexts differ from
the independently registered Object method entries. Their passed contexts do
not establish body identity. [`list_context_helpers`](../../scripts/game_data/memorypack/list_context_helpers.py)
independently proves the actual reset helper writes the caller's index slot to
zero and increments its version before branching on the old count; the
nonpositive path returns without calls. Its selected positive path passes array
data, zero and a sign-extended Int32 product to a span helper, whose writes
remain unresolved. The intended formatter result and compatible runtime contexts remain conditions;
allocation, growth, refill/error and GC-barrier paths remain outside this proof.
The same actual formatter helper now has the independently required key/class
and complete typed-return proof above; this does not close its indirect global
effects or establish runtime formatter selection.
Original nullable child composition and cursor accounting, allocation state
and complete root composition remain required for stored-list admission.
Neither the pointer stride nor a passing selected loop
promotes source-only elements to a positive list or whole root.

[`buff_timeline_root_list`](../../scripts/game_data/memorypack/buff_timeline_root_list.py),
[`packable_reference_sources`](../../scripts/game_data/memorypack/packable_reference_sources.py)
and [`new_list_reference_sources`](../../scripts/game_data/memorypack/new_list_reference_sources.py)
extend this control proof under the reviewed
[`buff_timeline_root_list_native.json`](../../scripts/game_data/contracts/buff_timeline_root_list_native.json).
The root's owned `ReadPackable` parameter joins its nested `ReadValue` slot.
The actual called helper inlines formatter selection, preserves the same Reader,
zeroes its local reference output, dispatches the concrete list formatter through
the ordinary fallback and returns the same full-width output through its complete
epilogue. Its independently registered Object entry differs, so the physical
body's named identity remains unresolved. A separately checked local root
program passes the current Reader and stores that returned reference into the
owned timeline field. This local join does not prove Reader/wrapper provenance
from the full root entry or the root's remaining fields and tail.

Complete selected null-list, empty-new-list and single/repeated new-list programs
now join allocation and the capacity constructor to the same independently
proved element loop. They retain the original count, same Reader, constructed
list and output location through return. The actual capacity constructor matches
its independent shared List registration; its reciprocal class parameter joins
the List and element-array context slots. The positive path forwards the signed
capacity unchanged to array allocation and stores the returned reference into
the observed receiver slot. The zero-capacity path stores its loaded static
reference. Both restore the caller frame, and the constructor/list output paths
use the same independently proved disabled barrier state.

The receiver reference slot remains a structural observation: open generic
field offsets are placeholders and are not used to name it. Neither selected
constructor path writes a count or version, so a freshly allocated list's zero
count and sufficient array capacity remain conditions, alongside compatible
runtime contexts/classes, correctly typed normal helper/child returns, stable
non-aliasing storage and the Win64 ABI. Actual allocation, static-field parity,
cache/global effects and runtime selection remain open. RIP-relative targets
are computed from complete instruction bytes, including trailing immediates;
candidate disassembly text cannot authenticate them. No child grammar,
positive list or whole root is admitted by this control proof.

[`buff_timeline_cursor_composition`](../../scripts/game_data/memorypack/buff_timeline_cursor_composition.py)
joins the complete nullable ReadValue paths, concrete wrapper forwarding,
Sequence array source and Timeline/ForceSync source returns. On the selected
buffered paths the outer helper adds no direct cursor advance. The adapter's
FF branch consumes one byte and updates all four cursors; its positive branch
only peeks at that byte, leaving the concrete source to consume the object
header once. Continuity requires stable buffered bytes and no cursor changes
through indirect/global aliases during the intervening non-reading helpers.

The positive Timeline source directly consumes its one-byte header and two
Int32 fields, plus the advances of the nullable Sequence and ForceSync children.
Positive Sequence consumes its header, array count and two flag bytes, plus
the action callbacks' advances. Positive ForceSync consumes its header,
normalized byte and two four-byte scalars, plus the string helper's advance.
Reference destination widths do not enter these wire equations. Complete
source epilogues add no calls or Reader writes. A bounded audit now checks
these framing equations against the unchanged certified original element,
Sequence/action and UTF-8 spans. Null objects, null arrays, empty arrays and
raw flag bytes remain distinct; an unproved null ForceSync source receipt is
refused. The original source-only receipts retain their admission boundary.
Equality between callback native advances and their certified stored spans,
full string-helper cursor/global effects, runtime selection and allocation
state remain separate obligations. This arithmetic audit grants no positive
list or whole-root admission and does not reparse previously passing sources.

The action array needs a distinct original/base-wrapper/union callback join.
[`buff_action_union_header`](../../scripts/game_data/memorypack/buff_action_union_header.py)
authenticates the selected original array element and all three metadata owners
through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_action_union_header_native.json).
Both `AbilityActionData` and its generated base wrapper are abstract; the union
formatter is concrete. The original/base-wrapper adapter is independently
located in `InitEager`: its allocation, closed constructor context, original
type key and `RegisterWrap` call form one checked flow. Its constructor thunk
joins an independently registered shared entry. The concrete union formatter's
separate registration reaches `Register<Wrapper>`. Static registration does
not establish runtime provider selection. The concrete Timeline/ForceSync
creation proof cannot cover this abstract wrapper's alternate creation branch
without the runtime class-attribute bridge. The requested schema bundle
locates names only; its old registrations and addresses are not reused.

[`buff_action_array_callback_binding`](../../scripts/game_data/memorypack/buff_action_array_callback_binding.py)
now joins that eager binding to the array's independently owned transfer through
its [`reviewed contract`](../../scripts/game_data/contracts/buff_action_array_callback_binding_native.json).
The shared
[`formatter_callback_signatures`](../../scripts/game_data/il2cpp/formatter_callback_signatures.py)
validator checks the sealed reference adapter, reciprocal class-generic owners,
the original-type substitution in its formatter parent, and the declared
instance virtual `Deserialize` slot. Its void return, byref unboxed Reader and
byref original reference output match the array's saved Reader, receiver and
indexed pointer-sized output. This is an exact declaration and static-transfer
join; it does not identify the runtime receiver or its inflated method.

The adapter's selected vtable entry names its metadata method definition. The
abstract base's selected slot is separately checked as stored representation;
it is not interpreted as a native callback address. Independently registered
shared code is still distinct from an inflated closed MethodInfo and companion
vtable entry. A missing unique closed entry in the compiled registration table
does not prove that runtime generic inflation cannot construct one. Provider
registration/cache identity, actual callback selection and callback advances
remain unresolved, so this binding admits no child, positive list or root.

[`buff_formatter_registration_state`](../../scripts/game_data/memorypack/buff_formatter_registration_state.py)
continues the eager registration through the complete named `RegisterWrap`
caller, using its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_registration_state_native.json)
and the shared
[`registration-state transfer validator`](../../scripts/game_data/il2cpp/formatter_registration_state.py).
The original type key and adapter reference reach `ConcurrentDictionary.set_Item`
together, after restoring the caller frame. Its MethodSpec and the named
`GetFormatter_` lookup's `TryGetValue` MethodSpec share the exact closed
`ConcurrentDictionary<System.Type, IMemoryPackFormatter>` instantiation. Both
read the same provider class usage cell and dictionary address expression.
The selected warmed first-hit lookup returns its full byref reference output;
only AL selects that hit. The complete public `GetFormatter(Type)` caller
preserves its type key and tails to the same physical result helper called by
the independently owned array provider.

This closes caller argument/return and static context joins. It does not prove
the dictionary mutation, equality comparer, retrieval, initialized cache contents
or the physical result helper's inlined lookup control. The declared static
field-offset word and native class-carrier displacements remain structural-only;
equal address expressions require stable initialized live storage. Some provider
loads select image regions without on-disk backing, so the installed bytes do
not supply their runtime values and cannot establish an empty cache. Live
class/MethodInfo/vtable selection and action callback cursor equality remain
separate requirements. No positive list or root gains admission.

[`buff_formatter_dictionary_lookup`](../../scripts/game_data/memorypack/buff_formatter_dictionary_lookup.py)
now authenticates the named lookup caller's original call and the callee's
complete unwind-owned instruction inventory through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_dictionary_lookup_native.json).
The shared
[`lookup-control validator`](../../scripts/game_data/il2cpp/dictionary_lookup_control.py)
checks every local branch against original instruction boundaries, including
the node loop, full reference output and restored return frame.

The selected word producer's original dword is retained for candidate word
comparison. A separate copy clears its sign bit, is sign-extended into the
double-width dividend and undergoes signed division. The remainder, rather
than the quotient, passes an unsigned bound guard and supplies the
pointer-sized slot index. With a positive signed divisor and stable compatible
storage this is the sign-cleared word modulo that divisor. The
[`signed-integer decoder`](../../scripts/game_data/il2cpp/signed_division.py)
owns the complete BTR/CDQ/IDIV encodings, operand widths, implicit registers,
divide faults and undefined flags. These instruction facts follow Intel's
[instruction reference](https://cdrdv2-public.intel.com/835781/325462-sdm-vol-1-2abcd-3abcd-4.pdf).

The ordinary node route compares the original word, forwards the original
query and candidate key to the selected predicate, and follows the next-node
reference when no candidate is selected. A finite stable miss clears the full
byref reference and returns false in AL. A hit copies the full node value and
returns true through the shared restored frame when the barrier flag is zero.
The guard's RIP target is computed from all original bytes, including its
immediate; the older mapper's displayed target for this form omits that final
byte and cannot supply the flag identity. LOCK operations on stack storage
retain their writes/order role; no whole-method purity is claimed.

This is conditional anonymous storage/control evidence. Valid compatible
memory, stable carriers/chain, normal ABI-compatible helper returns, a positive
divisor, valid disjoint output and the selected disabled barrier remain
conditions. The word producer's hash meaning and predicate's equality meaning
are not inferred from their callers. Closed generic field identities, live
dictionary contents, setter mutation, active barrier effects, physical result
helper control, runtime class/MethodInfo/vtable selection and callback cursor
equivalence remain open. The instruction coverage audit and opaque-helper
inventories belong in generated reports; this proof admits no positive list
or complete root.

[`buff_formatter_comparer_dispatch`](../../scripts/game_data/memorypack/buff_formatter_comparer_dispatch.py)
now joins the lookup's actual selector/argument transfers to both complete
word and predicate dispatch programs through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_comparer_dispatch_native.json)
and the shared
[`dispatch-control validator`](../../scripts/game_data/il2cpp/comparer_dispatch_control.py).
The caller selects one for word production and zero for the predicate; both
helpers explicitly truncate the selector to UInt16. Their record scan uses a
word count and word counter with unsigned guards. Because increment occurs
only below that count, ordinary exhaustion precedes low-word wrap. A matching
record's dword offset plus selector wraps at dword width before signed
extension and pair-address arithmetic. Function and companion method-context
qwords are loaded together; the fallback receives the original receiver,
context and narrowed selector.

The ordinary indirect routes preserve the original key arguments and selected
method-context word. Complete specialization branches and restored returns
are checked separately. One predicate specialization compares the two full
reference words directly and returns true/false in AL; byte XOR does not
establish a zero full return register. Other branches retain opaque object
or payload helper calls and their normal-return/compatible-storage conditions.
The
[`integer-width decoder`](../../scripts/game_data/il2cpp/integer_widths.py)
owns CDQE, word MOVZX/CMP/INC and register-byte XOR; the older display's widened
register names cannot establish these source widths. The instruction facts
follow Intel's [extension/reference](https://cdrdv2-public.intel.com/835781/325462-sdm-vol-1-2abcd-3abcd-4.pdf)
and [increment reference](https://cdrdv2-public.intel.com/782156/325383-sdm-vol-2abcd.pdf).

This closes anonymous dispatch control, not named runtime interface/slot
identity. A pointer comparison against a compiled specialization cannot select
the live comparer or substitute a nominal compiled generic instantiation for
an inflated MethodInfo. Current registered-target inventories remain candidates
under the [compiled registration index](../../scripts/game_data/il2cpp/body_claims.py);
class preparation, fallback resolution, opaque child effects, actual hash/
equality meaning and live cache/class selection require further evidence.
An absent primary unwind extent for a preparation helper does not prove an
empty function or no effects. Action callback identity/cursor and list/root
admission remain separate.

The preparation entry and fallback resolver now have a separate
[`conditional control proof`](../../scripts/game_data/memorypack/buff_formatter_dispatch_fallback.py)
under their
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_dispatch_fallback_native.json).
The preparation entry is a complete pointer-load/tail-jump transfer; its lack
of a primary unwind record does not prevent proving that transfer to the
independently owned target. That target tests stored bytes and either restores
its frame immediately or calls three actual helpers with a saved global-address
stack slot and the original loaded argument. Its middle helper receives the
slot's address, so the final forwarded slot value is not assumed unchanged.

The resolver retains the original receiver/context and truncates its selector
to UInt16 before the first child call. A nonnull first result returns unchanged.
If that result is null, anonymous byte/pointer gates decide whether an alternate
child is called with the original arguments; a nonnull alternate result is
preserved across a continuation and returned through the shared restored frame.
The remaining path calls an opaque failure helper and then reaches INT3 if it
returns. Valid compatible stable storage and normal ABI-compatible helper
returns remain conditions. These facts do not identify initialization, locking,
search semantics, mutation, live class/interface selection or actual effects.

[`integer_source_operands`](../../scripts/game_data/il2cpp/integer_source_operands.py)
owns complete source-memory ADD/AND, immediate IMUL, byte TEST and byte MOVZX
encodings. Immediate widths, memory widths and full instruction ends matter;
the former linear display had split immediate bytes into apparent returns and
other instructions. An unknown directive is recognized by its leading `db`,
not a substring in a hex operand. Instruction facts follow Intel's
[instruction reference](https://cdrdv2-public.intel.com/868137/325462-089-sdm-vol-1-2abcd-3abcd-4.pdf)
and [TEST reference](https://cdrdv2-public.intel.com/874240/325462-090-sdm-vol-1-2abcd-3abcd-4.pdf).
An owned resolver range can mix executable code, indexed dispatch tables and
padding; linear decoding of the whole range cannot certify that boundary. The
resolver-child control owners below partition their complete
primary/chained unwind-owned bytes into code, table data and padding, and check
every original branch, terminal transfer, indirect dispatch site and stored
table target against instruction boundaries. Their facts are `conditional`
on compatible stable storage and normal ABI-compatible child returns; none
extends the recursive storage reader's admission or the validated corpus
reader, and each fails closed through the selected native/source gates.

- **Resolver scan** --
  [`buff_formatter_resolver_scan`](../../scripts/game_data/memorypack/buff_formatter_resolver_scan.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_resolver_scan_native.json),
  lane [`il2cpp/resolver_scan_control`](../../scripts/game_data/il2cpp/resolver_scan_control.py)).
  Byte-selector/DWORD-target tables with guarded routes, non-wrapping record
  (UInt16) and parameter (DWORD) counters, and two closed-return index leaves.
  The resolver returns zero on missing context or exhausted records, else the
  receiver-relative pair address (DWORD offset + UInt16 selector, biased and
  scaled). Index arithmetic does not prove a live metadata header, bounds or
  valid records.
- **Carrier conversion** --
  [`buff_formatter_carrier_conversion`](../../scripts/game_data/memorypack/buff_formatter_carrier_conversion.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_carrier_conversion_native.json),
  lane [`il2cpp/carrier_conversion_control`](../../scripts/game_data/il2cpp/carrier_conversion_control.py)).
  A nonnull selected global returns unchanged; zero falls back to the input
  tag; other routes tail-forward the input, its payload, or a recursively
  obtained carrier with retained argument widths. No inline global/payload
  writes. Because the resolver reads the same global expressions, returned
  carriers support `conditional` value equality with the comparison carriers
  while the globals stay stable; this identifies no initialized runtime type.
  Recursive termination and tail-child effects are unproved.
- **Relation control** --
  [`buff_formatter_relation_control`](../../scripts/game_data/memorypack/buff_formatter_relation_control.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_relation_control_native.json),
  lane [`il2cpp/relation_control`](../../scripts/game_data/il2cpp/relation_control.py)).
  Equal input pointers return true before any call; other paths carry
  enumerated stack/global/context writes (locked exchange-add and
  compare-exchange -- a failed CMPXCHG still writes -- plus ordinary stores),
  so the relation is not read-only. Indirect calls prove only the storage
  address. Corrected RIP-relative immediate-store decoding joins one store to
  the shared global DWORD, not the adjacent cell the legacy display showed.
- **Relation imports** --
  [`buff_formatter_relation_import_control`](../../scripts/game_data/memorypack/buff_formatter_relation_import_control.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_relation_import_control_native.json),
  lanes [`il2cpp/relation_import_control`](../../scripts/game_data/il2cpp/relation_import_control.py)
  and [`il2cpp/pe_imports`](../../scripts/game_data/il2cpp/pe_imports.py)).
  The relation's indirect storage sites are `exact` on-disk import
  declarations of `baselib.dll` thread-ID and system-semaphore acquire/release
  (walked lookup tables and unbound IAT slots, never address proximity). The
  call sites implement an owner/reentry counter around a semaphore handle;
  this is declaration coverage, not a live IAT binding, initialized lock state
  or an executed acquire. The context pointer reloaded after the child call is
  treated as a fresh value.
- **Selected Baselib implementation** --
  [`buff_formatter_baselib`](../../scripts/game_data/memorypack/buff_formatter_baselib.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_baselib_native.json),
  lanes [`il2cpp/pe_exports`](../../scripts/game_data/il2cpp/pe_exports.py) and
  [`il2cpp/baselib_semaphore_control`](../../scripts/game_data/il2cpp/baselib_semaphore_control.py)).
  The caller's actual imported names join the selected file's name/ordinal/EAT
  entries, its complete primary/chained programs and actual named kernel import
  slots. All declared export-name ordering and ordinal indices are checked;
  selected forwarders cannot stand for a local body. The selected Baselib file
  joins GameAssembly, metadata and UnityPlayer in the before/after native gate.
  An explicit Baselib path reaches the proof; no sibling or game-root fallback
  replaces it. Missing/mismatched inputs yield no summary.
- **Context body and incoming-address control** --
  [`buff_formatter_context_setup`](../../scripts/game_data/memorypack/buff_formatter_context_setup.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_context_setup_native.json),
  lanes [`il2cpp/context_setup_control`](../../scripts/game_data/il2cpp/context_setup_control.py)
  and [`il2cpp/integer_byte_operations`](../../scripts/game_data/il2cpp/integer_byte_operations.py)).
  Rechecks the actual relation caller joins, complete primary/chained owned
  bytes, every possible local transfer, direct call and explicit store.
  The first complete physical field program and selected incoming-address
  handoffs are conditional on compatible stable/disjoint storage and normal
  Win64 calls. The second full CFG/store inventory remains `structuralOnly`
  for its complete typed field meaning. These optional proofs do not change
  the frozen recursive reader or grant child/list/root admission.
- **Context reservation/refill and tail arguments** --
  [`buff_formatter_context_allocation`](../../scripts/game_data/memorypack/buff_formatter_context_allocation.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_context_allocation_native.json),
  lanes [`il2cpp/context_allocation_control`](../../scripts/game_data/il2cpp/context_allocation_control.py)
  and [`il2cpp/integer_context_memory`](../../scripts/game_data/il2cpp/integer_context_memory.py)).
  Joins the actual first context call and its byte-count/eight-stride domain
  to the complete primary/chained reservation/refill/node program. Every
  local branch, direct/register call, external tail, trap and explicit store
  is checked. Indirect allocator identity remains open; the separate
  clear-tail owner below composes the child's normal result and conditional
  stores. Selected native/source drift yields no summary.
- **Clear-tail values, ranges and stored result** --
  [`buff_formatter_clear_tail`](../../scripts/game_data/memorypack/buff_formatter_clear_tail.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_clear_tail_native.json),
  lanes [`il2cpp/byte_fill_control`](../../scripts/game_data/il2cpp/byte_fill_control.py),
  [`il2cpp/fill_instructions`](../../scripts/game_data/il2cpp/fill_instructions.py)
  and [`il2cpp/fill_geometry`](../../scripts/game_data/il2cpp/fill_geometry.py)).
  Checks the complete owned fill and REP bodies, every image-relative table,
  register-value construction, store range and normal return. It rechecks
  the allocation/context parents and joins the returned old cursor to the
  receiver's stored array field. Native/source drift yields no summary;
  writable storage, CPU state and normal execution remain conditions.
- **Named class fields and ancestry-array consumer** --
  [`buff_formatter_class_ancestry`](../../scripts/game_data/memorypack/buff_formatter_class_ancestry.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_class_ancestry_native.json),
  lane [`il2cpp/class_ancestry_control`](../../scripts/game_data/il2cpp/class_ancestry_control.py)).
  Authenticates selected GameAssembly export names/ordinals/EAT entries,
  closed field getter programs and the complete owned `has_parent` program.
  It rechecks the first context proof and its actual child call, parent link,
  byte depth, stored array and ready-mask joins. This supplies a direct named
  ancestry consumer without selecting a live receiver or formatter.
- **Complete incoming-address helper control and saved homes** --
  [`buff_formatter_incoming_address`](../../scripts/game_data/memorypack/buff_formatter_incoming_address.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_incoming_address_native.json),
  lanes [`il2cpp/initializer_control`](../../scripts/game_data/il2cpp/initializer_control.py)
  and [`il2cpp/initializer_instructions`](../../scripts/game_data/il2cpp/initializer_instructions.py)).
  Rechecks the actual second-context call and named ancestry parent, then
  proves the helper's complete owned control, all explicit physical writes,
  frame/home geometry and finite register origins. Native/source drift
  yields no summary; unknown aliases, child effects and runtime identity
  remain open.
- **Named class bits, field iterator and preparation chain** --
  [`buff_formatter_class_fields`](../../scripts/game_data/memorypack/buff_formatter_class_fields.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_class_fields_native.json),
  lane [`il2cpp/class_field_control`](../../scripts/game_data/il2cpp/class_field_control.py)).
  Joins actual named exports to closed flag/bit entries, the complete
  has-references consumer, field iterator, preparation bridge and recursive
  preparation program. The input helper reaches the same preparation entry
  and its checked bit replacement matches the named blittable consumer.
  Native/source drift yields no summary; class storage, child effects,
  capacity, aliases and runtime identity retain their conditions or gaps.
- **Named field records and generic construction** --
  [`buff_formatter_field_construction`](../../scripts/game_data/memorypack/buff_formatter_field_construction.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_field_construction_native.json),
  lane [`il2cpp/field_construction_control`](../../scripts/game_data/il2cpp/field_construction_control.py)).
  Checks the complete owned generic child of the preparation program,
  selected name/type/parent/offset getter entries, the closed receiver wrapper,
  inline reservation and every record store. It rechecks the actual parent
  call and complete shared clear body. Selected native/source drift yields
  no summary; receiver count coherence, child effects, valid capacity and
  actual class/type identity remain open.
- **Ordinary and auxiliary field setup** --
  [`buff_formatter_field_setup`](../../scripts/game_data/memorypack/buff_formatter_field_setup.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_field_setup_native.json),
  lane [`il2cpp/field_setup_control`](../../scripts/game_data/il2cpp/field_setup_control.py)).
  Checks both actual sibling children completely for owned bytes, control,
  explicit stores and normal frame geometry, then proves selected count/home,
  parent-reference and early-ready projections. Native/source drift yields
  no summary. The remaining typed computations, count coherence, pointed
  slot and child effects, capacity and runtime identity remain open.
- **Metadata-record creation count flow** --
  [`buff_formatter_class_creation`](../../scripts/game_data/memorypack/buff_formatter_class_creation.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_class_creation_native.json),
  lanes [`il2cpp/class_creation_control`](../../scripts/game_data/il2cpp/class_creation_control.py)
  and [`il2cpp/class_creation_instructions`](../../scripts/game_data/il2cpp/class_creation_instructions.py)).
  Checks the complete creation candidate's owned control/stores/normal frame,
  selected source-address and allocation/result/count/return origins, plus
  the current metadata reader's named count words. It requires explicit
  native and metadata paths and rechecks the named count/allocator parent.
  Actual source/class/cache/preparation identity, count coherence, child
  alias effects, capacity and the remaining typed computations stay open.
- Generic creation code/data and selected count/cache flow owner:
  [`buff_formatter_generic_creation`](../../scripts/game_data/memorypack/buff_formatter_generic_creation.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_generic_creation_native.json),
  lanes [`il2cpp/generic_creation_control`](../../scripts/game_data/il2cpp/generic_creation_control.py)
  and [`il2cpp/generic_creation_instructions`](../../scripts/game_data/il2cpp/generic_creation_instructions.py)).
  Checks the complete owned code/table partition, guarded image-RVA targets,
  stores, normal frames and selected register origins across branches and
  backedges. The actual shared getter supplies a fresh source-count word;
  creation copies it into the allocation result's named count offset and
  stores the original incoming receiver in its named generic link. Cache
  publication uses an implicit memory exchange that overwrites the saved
  result register with the old cache value; the selected non-null return
  subsequently uses a fresh cache read. Existing-cache and null-source paths
  bypass creation/count copying. Fresh cache equality, live class/preparation
  identity, later count coherence, child aliases, synchronization, capacity,
  recursive termination and other typed effects remain unresolved.
- Source receiver resolution owner:
  [`buff_formatter_receiver_resolution`](../../scripts/game_data/memorypack/buff_formatter_receiver_resolution.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_receiver_resolution_native.json),
  [`il2cpp/receiver_resolution_control`](../../scripts/game_data/il2cpp/receiver_resolution_control.py)
  and [`il2cpp/record_index_geometry`](../../scripts/game_data/il2cpp/record_index_geometry.py)).
  Checks closed nullable/pointer-index leaf programs separately from the
  complete owned indexed-cache resolver. The signed high-multiply/add/shift
  bound converts every valid selected record offset to its index; matching,
  stable header/base reads conditionally round-trip to the constructor's
  source record. The actual metadata constructor result reaches a freshly
  loaded cache array with the same signed index. The resolver checks a null
  sentinel and two fresh cache views, then returns another fresh array/element
  view. Those views, live pointer/class/preparation identity and returned count
  equality remain unresolved; the nested nullable leaf does not establish
  null handling of the original receiver. No leaf unwind ownership is inferred.
- [`Metadata initialization owner`](../../scripts/game_data/memorypack/buff_formatter_metadata_initialization.py) ([contract](../../scripts/game_data/contracts/buff_formatter_metadata_initialization_native.json)) checks complete owned initialization control, actual loader-result/header/base and allocator-result/resolver-cache stores, and the conditional record-size quotient. The fresh header must match selected metadata; loaded-file identity, allocator target/outcome, capacity, global stability and child aliases remain open.
- [`Metadata loader owner`](../../scripts/game_data/memorypack/buff_formatter_metadata_loader.py) ([contract](../../scripts/game_data/contracts/buff_formatter_metadata_loader_native.json)) checks complete owned loader/path-helper control, literal descriptor/argument programs, close/error import declarations and conditional zero-or-saved-child-result returns; mapping/default-allocator transfers are closed programs without inferred ownership. Reserve/append/open/map effects, constructed path, live bindings and file identity remain open.
- [`Metadata mapping owner`](../../scripts/game_data/memorypack/buff_formatter_metadata_mapping.py) ([contract](../../scripts/game_data/contracts/buff_formatter_metadata_mapping_native.json)) checks the actual loader tail target's complete owned control, arguments, registration writes, normal frames and release-counter program. Status-error and zero-view edges select zero; the other path subtracts fresh slot contents, passes both mutable slot addresses to registration children and reloads the return slot afterwards. One registration stores the saved first child result, while the other stores a fresh view of the incoming offset home. A nonnull view-child result therefore does not establish final-return equality, nonnullness, pointer validity or mapped-file identity. Slot/alias noninterference, child registry effects, live bindings, synchronization and retry termination remain open.

Under normal Win64 calls, the thread-ID body zero-extends the DWORD result
before returning it to the caller's QWORD owner comparison. Acquire preserves
the incoming handle, passes an infinite nonalertable wait, and restores its
frame before tail-calling the error query only on the failed-wait value.
Release returns immediately for an original zero request. After its first
release fails, it queries the error without branching on that error code,
tries a single release with a DWORD previous-count output, and computes the
next request as `uint32(min_unsigned(previous request,
uint32(recorded limit - previous count)) - 1)`. A failed adjusted release
carries that adjusted DWORD into the next retry. There is no additional zero
guard before the adjusted call; unsigned subtraction can wrap. Applicable
saved registers and frames are restored on every normal return path. This
does not prove termination or equality between the original request and the
total count successfully released.

Those are conditional physical argument/control facts. Interpreting them as
Windows semaphore/thread effects additionally requires live API bindings and
compatible initialized handles. Microsoft's
[wait contract](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobjectex),
[release contract](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-releasesemaphore)
and [thread-ID contract](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getcurrentthreadid)
describe those APIs; the selected on-disk declarations establish neither a
loaded target nor an observed synchronization result.

The first context body returns through the shared restored frame when its
ready bit or stored array pointer is already nonzero. Otherwise it may call
itself on the linked receiver with the incoming second-argument address.
Its stored count is an unsigned byte: the fresh linked count plus one wraps
modulo 256, while a receiver with no link gets one. The allocation-like call
receives that zero-extended byte count and an eight-byte stride; its result
is stored without an inline failure guard. A linked path writes the receiver
QWORD at `array + (fresh count - 1) * 8` and forwards the two stored arrays
and `fresh linked count * 8` bytes to the copy-like child. The other path
writes the receiver at the array start. Normal continuation reloads the flag
byte, ORs its ready mask, stores it and restores the frame/register. That first
body has no inline guard excluding count wrap or establishing nonzero
allocation or valid capacity.

The named `il2cpp_class_has_parent` export directly calls that first context
entry with its original first argument and a context-slot address. Its
complete program checks the same ready flag and stored array, prepares the
original second argument through another child, reloads the second depth as
an unsigned byte, and returns AL one exactly when the first depth is at least
that fresh depth and the first array's `depth - 1` QWORD equals the original
second argument. Otherwise AL is zero. Under coherent class state, positive
prepared depth and valid array storage, this directly connects the stored
array to a class ancestry test. The parent/depth/array joins are physical
reads and an authenticated call, rather than a name or layout similarity.

Selected named getter entry programs return the QWORD name, namespace,
parent or element-class field, or form the embedded type-field address.
Each checked entry is a closed load/address-and-return program. That proves
its entry execution without claiming a physical function extent from absent
unwind data or extending into neighboring padding. These named reads anchor
the corresponding field roles; they do not identify the live object passed
to an anonymous initializer. The ancestry consumer still reloads its
post-child context pointer as fresh, lacks an additional zero-depth guard,
and depends on compatible storage and normal Win64 callees. Initialization,
synchronization success, capacity and actual runtime ancestry remain open.

The actual allocation-like child rounds the unsigned low product of count
and stride to an eight-byte reservation. In the selected caller's unsigned
byte/eight-stride domain, multiplication and this rounding cannot overflow
and the reservation equals the unrounded byte product. This does not prove
that pointer endpoints do not wrap or that the surrounding storage is valid.
Its unsigned remaining-space guard chooses refill when space is smaller;
otherwise the body takes the fresh cursor, writes cursor plus reservation
and subtracts that reservation from the QWORD remaining field. The refill
mode byte may select an alternate helper whose nonnull result rejoins that
same reservation path, while a null result goes through new-block setup.

New-block setup reads the global allocation-function cell twice, with one
metadata-size argument and one unsigned-selected block-size argument. These
are fresh cell reads, not proof of the same live function value or successful
allocation. The body stores buffer/cursor and total/remaining metadata, checks
a QWORD node-count equality guard, allocates and links a payload node, and
increments the count. The equality path calls the selected failure child
and reaches INT3 if that child returns normally. Named pool/list/class meaning,
counter invariants and the alternate/node/failure child effects remain open.
No inline null guard covers the global allocation results before their use.

All ordinary exits restore the applicable saved registers and stack before
tail-forwarding the old cursor, a zero fill word and the original count/stride
byte product. The reservation owner establishes this argument flow. The
separate clear-tail owner now follows the child through complete normal
returns: each returns the incoming destination. The actual receiver array
field receives that old cursor before later flag updates may change AL.
Normal Win64 calls, compatible stable noninterfering root/block/node storage
and valid allocation/refill results remain conditions; actual capacity,
protocol, allocator selection, visibility and observed effects are unproved.

The fill child zero-extends the low input value byte, replicates it through
a QWORD multiply and initializes the consumed SSE/AVX lanes. Its guarded
short-length table covers each admitted size, and larger paths select paired
endpoint stores, aligned loops or REP byte stores. The vector-tail tables
select only the proved rounded-remainder indices. Affine range comparisons
cover every natural loop count: the aligned loop advances by exactly its
store chunk, head/endpoint stores cover the alignment gap and remainder, and
overlapping writes carry the same byte value. Under the actual context
arguments, this establishes zero stores across the count/eight-stride range.
Zero length permits a normal return without payload stores and supplies no
nonnull-result guarantee.

These effects require a valid writable range and compatible stack/return,
supported instruction state on the selected SSE/AVX branch, zero direction
flag for REP, nonwrapping endpoints, and noninterference with control tables,
globals and saved return state. The REP body saves/restores its nonvolatile
destination register and frame; that save is a separate stack write. The
non-temporal path executes SFENCE after its stores, establishing store/store
ordering under the architectural conditions. All-store visibility at return,
live path selection and observed payload effects remain unproved. Instruction
semantics follow Intel's
[instruction manuals](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).

The second body saves the incoming address in an entry home cell. Its checked
frame delta joins later home-cell reloads to that same physical cell, and
direct stack stores do not overwrite it. Finite provenance over every local
CFG edge invalidates the origin on any whole or partial RBX/RDX write,
preserves RBX and invalidates RDX across normal Win64 calls, and proves the
selected recursive/helper handoffs. RBX's later object-like loads are fresh
unknown values; they cannot all be treated as the incoming address. Disjoint
storage and stable saved cells remain conditions: passing the same address
does not prove that the pointed slot contents, or the caller's post-child
context pointer, remain unchanged. The ABI condition follows Microsoft's
[x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention).

The incoming-address helper's complete local graph now includes direct,
register and imported calls, its normal RET and terminal INT3. Every explicit
write is checked, including packed vector and immediate-byte stack stores,
byte flag logic, memory subtraction and the locked QWORD counter step.
Typed moves preserve the actual REX-extended SIB index; an earlier linear
display omitted that extension. That display was a byte candidate, not a
field or effect proof. The optional decoder leaves the frozen stored reader
unchanged and fails closed on unsupported/truncated selected forms.

Separate frame analysis connects both saved entry values through RSP and
RBP addressing. Explicit stack-store ranges, PUSH writes and normal CALL
return-address writes avoid the saved homes. Finite source analysis over all
local edges invalidates whole/partial register overwrites and volatile
registers across normal calls, while preserving the applicable nonvolatile
origins. It enumerates every call site whose RDX is proved to carry the
original incoming address or its saved copy. A register value at a call site
does not establish that the callee owns or reads that parameter.

Every normal local return supplies AL zero or one; this is a low-byte return
fact, not proof of initialization success. Stable homes and noninterference
by unknown memory aliases or child writes remain conditions. Other indirect
stores can alias the incoming pointed slot, and child effects are still
open. The caller's post-child context pointer therefore stays fresh;
pointed-slot preservation, complete class-field meaning, actual receiver
identity, capacity and recursive termination are not admitted by this proof.

The named class-bit and field-preparation owner now gives the input helper
an additional direct interpretation. The closed `il2cpp_class_is_blittable`
entry extracts one bit from the field-state byte. In the actual input helper,
the checked XOR/mask/XOR sequence replaces precisely that bit of the original
receiver byte with the bit freshly read from another receiver. All other
bits of the loaded original byte are preserved. The preceding helper result
and recursive call are checked as actual register/call flows; the returned
object's live class identity and the original receiver's runtime identity
remain unproved. The generic receiver is therefore not selected by a layout
or getter-name match.

The complete `il2cpp_class_has_references` target first checks the separate
fields-ready bit, invokes the preparation bridge when it is clear, and
checks readiness again after that call. Its normal result is the selected
bit from a fresh state-flags byte; a still-clear ready bit reaches the
failure helper and INT3 if that helper returns normally. Closed
`il2cpp_class_get_flags` separately anchors the DWORD type-flags field.
These named consumers distinguish physical fields and bits without claiming
that preparation or an actual class initialization succeeded.

The complete named field iterator directly reads an unsigned word count and
the fields base, advances a nonzero iterator by the checked record stride,
and compares the resulting pointer against the fresh base plus scaled count
with an unsigned end guard. A null iterator address returns zero. For a
zero iterator value, it calls the preparation bridge and checks the count;
the nonempty path loads the fields base, writes the pointed iterator slot,
then reloads the receiver's fields base for its return. That second load is
fresh: the stored pointer and returned pointer are not proved equal without
noninterference. Valid coherent field storage and nonwrapping endpoints are
required to interpret the guard as capacity or iteration correctness.

The complete bridge passes the original receiver and a computed address of
its own stack context slot to the same preparation entry that the input
helper calls. It reloads the context pointer after the child and checks the
complete release/counter program against that fresh pointer. A computed
stack address is an origin fact, not proof that it differs numerically from
the original iterator or another pointer. The complete preparation program
checks readiness, sets a preparing bit, recursively prepares the parent or
generic receiver under its guards, calls the ordinary/generic and auxiliary
children, then clears preparing and sets fields-ready on its normal finish.
There is no additional preparing-bit guard before parent recursion. The
ordinary/auxiliary storage construction, mutations of the passed pointed slot, compatible
initialization/synchronization and recursive termination remain open.

The complete generic field child first obtains a candidate source receiver
through the checked closed wrapper and saves its unsigned word field count.
A zero saved count stores a null fields pointer and skips the inline
allocation path; the preceding receiver helper's effects remain unknown.
The nonzero path scales the saved count by the same record stride that the
named iterator uses, reserves a cursor range and calls the actual shared
clear entry with a zero fill word and that scaled byte length. Its normal
return is the old cursor under the clear proof's writable-storage, CPU/DF,
nonwrapping and payload/control/stack noninterference conditions. The two
global allocator-function loads are fresh, and neither they nor the
remaining-space guard prove allocation success or usable capacity.

Each generic loop iteration freshly reloads the source fields base and the
receiver's generic link. A child receives the fresh source type, an address
within that generic-link record and a zero third word; its return is stored
in the destination type slot. After the call, the source name, offset and
trailing DWORD are freshly loaded and copied, and the saved original
receiver is stored as the destination parent. Named getters directly anchor
the name/type/parent/offset slots; the offset getter sign-extends its DWORD
to a full GP register. The trailing DWORD remains anonymous. The explicit
record stores tile the entire stride once per iteration, and the saved
count controls the loop under normal ABI returns. This does not prove a
live class, successful type substitution, alias-safe child effects or that
other writes never touch the destination records.

The generic program publishes the clear-return pointer into the receiver's
fields slot but does not directly assign that receiver's field count. The
saved source count and the receiver count later read by the named iterator
are therefore a separate unresolved join. Setting fields-ready in the
parent cannot supply the missing count assignment, storage capacity or
initialization result.

The ordinary and auxiliary siblings now have complete owned instruction,
control, call/store and normal frame checks through their dedicated owner.
Its optional integer/Single decoder corrects previously split instructions;
apparent calls and pushes produced by the old unknown-byte splits are not
real control edges. Complete control coverage still leaves the remaining
metadata, hash-map, layout, static-storage and global allocation effects
structural only. Signed integer/Single conversions record their physical
lanes and rounding/exception conditions without evaluating a runtime result.

The ordinary prefix reads the receiver's unsigned word count for allocation
with the named record stride, then freshly reloads that count after the
allocator call for its loop. These are separate values unless their
coherence and child/alias noninterference are proved. The allocator entry
matches the reviewed allocator, but the older byte-count caller's numeric
domain cannot be transferred to this word-count caller. The ordinary child's
own saved RDX home is overwritten by DWORD loop-counter stores. This reuse
of a callee's incoming home is distinct from the pointer argument's target;
it proves neither preservation nor modification of the passed pointed slot.

The auxiliary parent-reference prefix first combines the parent byte with
a fresh receiver byte, then uses XOR/mask/XOR to replace the named
has-references bit in a second fresh receiver byte. The unselected bits
equal that second load; equality of the receiver loads is not assumed.
Under coherent state the selected bit inherits parent OR receiver. A later
actual named has-references call conditionally sets the same bit. The local
fields-ready write dominates two subsequent layout calls, so it occurs
before those children have completed. Readiness alone therefore establishes
neither completed layout effects nor successful initialization.

Count provenance also requires the creation path before preparation. The
maintained selected-dialect
[`metadata reader`](../../tools/endfield-il2cpp/catalog_option_flow_metadata.py)
exposes the type-definition `field_count` word; its reference-prefix and
layout-tail interpretation is distinct from the historical schema bundle's
helper. Matching a candidate native load to that count's stored position
does not prove the source table pointer, destination class, cache identity
or coherence with the later generic/ordinary preparation reads. Those joins
remain explicit prerequisites, and a displacement search cannot exclude
wider, indirect, aliased or child writes.

The metadata-record creation candidate now has a complete owned control,
call/store and normal-frame proof. Its source address scales the signed
incoming DWORD index by the selected record stride, then adds a signed
table offset from a fresh header-pointer load and a separately fresh global
metadata base. The stored source pointer and allocation-result register
remain preserved until the fresh count-word read under normal Win64 calls.
A source vtable-count word contributes to the allocator's stride argument,
with a unit count argument; the older allocator caller's numeric domain
does not transfer to this caller or prove capacity.

The source count word is copied into the allocation's same physical offset
that the named class field-count consumer reads. The actual allocation call
and this copy dominate every normal local return. The return projection
moves the saved allocation result into the result register and restores the
checked frame. The complete direct, unindexed destination-register store
inventory has no second write overlapping this count. This narrow store
fact does not exclude wider/indirect aliases or child changes, including
changes after the copy.

The current metadata file's field-count and vtable-count words agree with
the maintained named reader and selected record layout. That file evidence
does not authenticate the runtime global header/base pointers or establish
an in-range source index. The allocation has not been joined to a live
class/cache object or the later field-preparation receiver. Its copied
quantity therefore remains distinct from the later generic saved source
count and ordinary pre/post-allocation reads. Other metadata/cache/flag/type
creation computations remain structural only. The optional bit-set and
byte shift/add/not reader repairs the former fake immediate-return split;
only the complete authenticated program supports the return/dominance facts.

The optional [`integer_byte_shifts`](../../scripts/game_data/il2cpp/integer_byte_shifts.py)
reader supplies exact immediate logical byte-register shifts for these bit
consumers. It preserves high-byte/REX distinctions and the other parent bits;
it does not infer flags or CPU execution. Earlier bounded linear candidates
could split that opcode into unrelated byte/call rows. Only the authenticated
closed entries and complete owned programs support the interpretations above;
neighbouring bytes in a bounded prefix supply no function ownership.

The first body's direct copy target joins the same owned bulk entry used by
the maintained [EffectLineCenter copy dispatch proof](../../scripts/game_data/buff_effect_line_center_copy_dispatch_native.py)
and its [contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_dispatch_native.json).
This is a current-build entry
identity, not a name match. Those complete dispatch/store-value proofs can
be reused for further composition; the new caller still needs its own valid
buffer/capacity, noninterference, CPU/selection and applicable direction-flag
conditions. The managed Array.Copy wrapper's assumptions do not automatically
hold for these anonymous arrays, and observed results/visibility stay open.

Instruction-width facts these owners depend on live in
[`integer_tag_dispatch`](../../scripts/game_data/il2cpp/integer_tag_dispatch.py)
(signed-extension/compare/increment operands),
[`integer_decrement`](../../scripts/game_data/il2cpp/integer_decrement.py)
and [`integer_effects`](../../scripts/game_data/il2cpp/integer_effects.py)
(locked exchanges, unary arithmetic, physical write spans). The optional
[`integer_byte_operations`](../../scripts/game_data/il2cpp/integer_byte_operations.py)
adds byte-register INC/DEC and selected AND/OR with exact instruction ends,
partial parent-register writes, REX/high-byte selection and flag effects;
byte INC preserves CF and wraps rather than widening the count. Instruction
semantics follow Intel's [instruction manuals](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).
The optional [`integer_context_memory`](../../scripts/game_data/il2cpp/integer_context_memory.py)
adds memory-destination SUB, sign-extended accumulator AND, byte memory
INC/DEC/XOR and typed memory/register CMP with complete instruction ends.
This closes the selected helpers' former decoding gaps without changing the
frozen stored-data reader or treating known linear rows as complete control.

Still `unresolved`: remaining typed conversion/relation meaning, live
class/interface/slot and inflated MethodInfo identity, initialization/cache/lock
semantics, live Baselib/API identities, the second context body's complete
typed field program, context children's pointed-slot mutations and
allocation/copy effect composition under the actual caller conditions,
including valid storage/capacity, initialized allocator protocol and actual
clear/copy execution and visibility,
callback cursor equivalence, and positive list/full-root admission.

The union formatter's caller prefix saves its entry Reader and wrapper output,
initializes a UInt16 stack local, passes the same Reader/local to the actual
physical tag helper, tests only AL and reloads that unsigned word on success.
The helper's three selected buffered paths are checked through complete returns:
markers below `FA` consume one byte and produce that tag; `FA` consumes two
additional little-endian bytes and produces a UInt16 tag; `FB` through `FF`
consume one byte, write zero and return false. Each read updates the pointer,
remaining length, advanced count and consumed count. Saved nonvolatile state
and the frame are restored. Success establishes AL only; the false path clears
the full return register. These claims require warmed caller/helper state,
valid buffered/counter bounds, disjoint stable Reader/buffer/output/caller
storage and the Win64 ABI. The helper has no uniquely named metadata owner.

This native false behavior does not admit reserved `FB..FE` markers as canonical
stored nulls; the existing reader still requires its proved `FF` null encoding.
The header proof ends at the caller prefix. A separate
[`buff_action_reference`](../../scripts/game_data/memorypack/buff_action_reference.py)
proof, owned by its
[`reviewed contract`](../../scripts/game_data/contracts/buff_action_reference_native.json),
now follows the same actual shared adapter through the abstract branch. When
the owned runtime attribute query reports the abstract mask, the branch sets
the full wrapper reference local to zero instead of calling `Activator`.
The same saved Reader and initialized local reach slot-five child dispatch.
Complete zero and nonzero child-output paths respectively clear the original
output or call its owned typed getter and store that reference. Full frame and
nonvolatile restoration is preserved. This extends the existing instance
ownership algorithm with an explicit abstract mode; it does not reinterpret
the previously proved concrete creation paths. Matching runtime attributes,
inflated contexts/provider results, typed normal child returns and stable
Reader aliases remain conditions. Static eager registration does not establish
that the actual array callback selected this adapter.

The union formatter's AL-false branch is also proved through complete return:
its saved, zero-initialized RSI clears the full wrapper output, and the caller
passes that same output address to the actual barrier call. That target is a
short jump entry into the independently proved shared barrier, not a separate
barrier inferred from address proximity. Only its actual first jump is needed;
no complete leaf extent is inferred in the absence of a function-range record.
With the shared barrier disabled, its selected path has no calls or memory
writes and returns to the restored union caller. No direct Reader writes occur
outside the tag helper. The disabled state and indirect/global alias effects
remain conditions; this proof does not cover an active barrier.

Actual array callback/class/provider selection, positive union switch and
concrete-child advances relative to original spans, initialization/refill/error/
global effects and complete list/root composition remain open. Reserved-marker
false behavior still grants no canonical null admission. No grammar, positive
list, whole root or gameplay effect gains admission from these control proofs.

[`buff_pick_target_union_route`](../../scripts/game_data/memorypack/buff_pick_target_union_route.py)
now closes the selected new-child route for the leading reached
`PickTargetAction`, with its own
[`reviewed contract`](../../scripts/game_data/contracts/buff_pick_target_union_route_native.json).
The current UInt16 tag passes an unsigned range check, indexes four-byte
unsigned RVAs and adds the actual image base before the computed jump.
The current table entry selects the independently checked wrapper; old bundle
ordinals are not reused. On entry with a null wrapper output, the actual cast
helper has a complete no-call path returning a full null reference without
class or Reader dereferences. The route preserves the same saved Reader and
loads a closed `ReadPackable<PickTargetWrapper>` context.

That child entry is a two-instruction context thunk: it reloads the identical
closed MethodSpec into RDX without changing RCX, then jumps to the already
proved actual shared ReadPackable body. Its reciprocal generic parameter,
owned nested ReadValue/provider/formatter contexts and complete initialized
local-output/Reader/return transfer are reused. An unrelated Object entry does
not supply this physical identity. The route stores the full returned child
wrapper and passes that same value/address through the actual disabled shared
barrier before restoring the complete union caller. No Reader cursor writes
occur in the route or thunk; header and concrete child advances remain distinct.
No full leaf extent is inferred for the context thunk.

These are conditional control/value joins: initialized compatible inflated
contexts/cache/provider results, the selected tag and null prior wrapper,
stable disjoint storage, typed normal child returns, disabled barrier and
Win64 preservation remain required. Actual array virtual selection, reused
wrapper paths and native callback advancement relative to original spans
remain open. Its current named source identifies the
inherited action fields followed by `contextKey`, BlackboardInt `index` and
TargetSettings `target`; the route proof alone does not admit those payloads,
positive lists, whole roots or gameplay target selection.

The maintained [`PickTarget storage reader`](../../scripts/game_data/memorypack/buff_pick_target_action.py)
and its [`source contract`](../../scripts/game_data/contracts/buff_pick_target_action_native.json)
now extend that route into the concrete seven-member source. A complete
buffered object-header helper writes the original byte to the caller's local,
updates all four Reader counters and returns the FF comparison in AL. The
positive source forwards its inherited enable byte and three DWORDs, then
`contextKey`, BlackboardInt `index` and TargetSettings `target`, through the
actual generated setters. The concrete getter's coherent-cache path returns
the same underlying base instance; the source and setters restore their
ordinary frames. Allocation, refill, exceptional paths, active barriers and
actual provider choice remain independent conditions.

The BlackboardInt proof strengthens the previously named child with complete
ordinary header, source-result/store and return programs. Its inherited key,
use-key flag and integer value belong to the same closed `int/int` base carried
by its generated wrapper. The value's VAR record names a metadata parameter
index, whose owning container determines the relative argument ordinal; the
record's integer must not be used directly as that ordinal. Generic-definition
offset placeholders do not establish destinations: the emitted closed setters
and source stores do. Raw flag, DWORD and string bytes are retained, and the
typed TargetSettings field delegates to the existing recursive target owner.
Canonical null wrappers and children keep exact bounded spans. Any unsupported
target interior, wrong typed evidence, malformed child or incomplete action
refuses the action. The complete current corpus gate and independent
original-element/root replays now validate this extension. Complete roots
retain their other blockers. The newly reached following action also makes
selected refusing Timeline elements relevant again: complete unchanged
PickTarget decoder returns before that same refusal can be retained as
independent original action receipts. Passing elements are reused. A closed
action does not admit its enclosing element, positive list or root; native
callback selection and advancement remain distinct from stored-span closure.

[`CheckConsumeBuffLayer`](../../scripts/game_data/memorypack/buff_check_consume_layer.py)
now joins its current seven-member source and generated setters under its
[reviewed contract](../../scripts/game_data/contracts/buff_check_consume_layer_native.json).
Its `num` context names the same independently owned BlackboardInt type and
reader used by PickTarget. The integer owner exposes a separate native gate
for that child; full PickTarget validation reuses the same proof and returns
it separately, without granting PickTarget admission to an integer-only audit.
The new parent reuses the collected string-source validation rather than
performing another scan.

The stored comparison enum precedes the nullable integer, followed by a
separate nullable `storeKey` string. Child parsing reserves the final key's
required length header, and the integer and string receive independent
original-span receipts before the parent can close. Null parent, null integer,
null key and empty key remain distinct; raw flag, enum and integer bits are
preserved. This reusable shared-event action has bounded original-byte checks,
but complete root admission still requires a new full family gate and
independent original-root replay. No evaluated comparison, layer consumption,
blackboard lookup or destination-key write follows from stored closure.

The names-only
[`consumer claims`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
also independently join the actual `ExecuteInternal` receiver to its closed
`AbilityAction<Data>` slot. That owned Data supplies `contextKey`, `target` and
`index` reads; the integer reference reaches the named static
`ActionBlackboardExtensions.GetValue.param` argument with an Int32 return ABI.
The compiled body contains the target-list getter, `GetTargetsView`, `SetTarget`
and `Context.UpdateTargetGroup` calls. The existing argument checker excludes
the aggregate return ABI of `GetTargetsView`, so its target argument is not
promoted from call proximity. Key-to-update forwarding, evaluated index,
selected list item, bounds result, target-group writes, IFix selection and
actual execution remain separate gaps. This consumer claim supplies no stored
payload, positive-list or complete-root admission.

The next reached `EffectLineCenterAction` now has a maintained
[`source-field validator`](../../scripts/game_data/memorypack/buff_effect_line_center_action.py)
and a separately reviewed
[`current native contract`](../../scripts/game_data/contracts/buff_effect_line_center_action_native.json).
Its generated declaration has nineteen members, eighteen inherited. The
historical bundle omits the current inherited `bigEffectTarget`; its old member
count and union ordinal cannot supply the current layout. The actual reader
compares the current member count and performs individual source/setter calls,
rather than delegating the inherited prefix to the concrete EffectAction
reader. The first four fields use AbilityAction setters, the next fields use
EffectAction setters and the final `effectCenter` uses its own derived setter.
Current closed contexts independently identify the TargetSettings and
EffectActionCfg source returns.

The proof pairs actual wrapper and runtime ancestries, validates each owned
setter parameter and field, and carries the same saved Reader/ref-wrapper
through the ordered source calls and complete ordinary return. Base Effect
setters have their own inlined coherent-cache checks before the typed field
store. The derived target setter calls its concrete coherent-cache getter and
uses a full displacement store; it must not be reduced to a signed-byte
offset. Reference stores reach the independently proved shared barrier.
The switch route's actual RIP-relative load is joined to its recorded usage
cell as well as to the current table and wrapper identity.

The buffered object-header proof now lives in the shared
`buffered_owned_sources` owner and checks the complete ordinary byte read,
caller output, cursor commits, FF comparison and returned AL. The derived
reader's false-header branch clears its original ref-wrapper output, passes
that output to the shared barrier and jumps into the complete saved-register
epilogue. It skips the RSI restore used only after the positive header path.
Refills, exceptions and ordinary returning-call assumptions remain conditional.

The derived bounded decoder now reads its own nineteen-member original span.
Five separate TargetSettings fields and the EffectActionCfg field must join
their closed source contexts to the actual runtime type in each child wrapper's
instance field; wrapper and runtime definition indices are not interchangeable.
The configuration's independent `decode_effect_config_value` entry point names
its complete direct fields and scalar/vector interiors while preserving raw
values and null/empty terrain-effect collection states. Positive terrain-effect
arrays still refuse. Prepending an EffectAction tag or changing the derived
header to fit a parent-bound receipt is not a valid join.

The structural and recursive action dispatchers use this derived owner. Fresh
native validation, the complete current corpus gate, original source-element
replay and selected canonical root replay have passed. Prior complete elements
and roots are retained; additional original source elements now close through
their own derived action and child spans. Related partial roots still refuse at
the positive Timeline list boundary. Closing all source elements in a selected
file does not supply the array callback/cursor proof for its enclosing list.
Current inventories remain in generated reports. These stored-byte proofs do
not establish enclosing positive-list/root admission, actual array/provider
selection, target evaluation or effect execution.

Child source binding must respect each validator's actual input surface. The
metadata-owned wrapper plan authenticates GameAssembly and metadata, and its
hash strings may use lowercase. The independently validated target,
configuration and vector owners authenticate the full selected three-input
build. Comparing the plan to that larger dictionary wrongly rejects the
selected build; requiring its own exact keys and case-insensitive hash values
preserves the input gate. A child-binding failure names the specific owner,
status, inputs or ordered layout instead of truncating the entire recursive
child catalog. A failed native join must leave the previous complete corpus
report as a comparison baseline.

Consumer layout and conditional preparation flow have a separate
[`validator`](../../scripts/game_data/buff_effect_line_center_consumer_native.py)
and [`reviewed contract`](../../scripts/game_data/contracts/buff_effect_line_center_consumer_native.json).
The closed generic Data reference is witnessed by EffectAction's completely
occupied concrete field suffix. Its immediate EffectLineCenter receiver adds
no instance fields and has the same selected instance extent. Open generic
offsets are not substituted for that proof. The named target helper returns an
AbilitySystem; the selected ancestry supplies its Entity field through
BaseComponent. The concrete runtime type declares `PreExecuteInternal`, while
the inspected effect execution body belongs to its EffectAction parent.

The independent [`Vector3 leaf checker`](../../scripts/game_data/il2cpp/vector_arithmetic.py)
proves all three Single left-minus-right components, their twelve-byte output
and the returned original buffer through the complete straight-line RET. The
leaf requires neither a guessed next-method boundary nor the subset decoder's
unsupported unpack instruction. This is a compiled arithmetic/callee ABI
fact; caller arguments require the separate complete preparation grammar.

The current consumer contract now proves the complete preparation caller,
including original local branch destinations and its whole return frame.
The independent [`conditional-move decoder`](../../scripts/game_data/il2cpp/conditional_moves.py)
keeps CMOV as a flags-dependent write retaining the old destination on the
other outcome; fallback bytes are not allowed to invent jumps or pops.
The [`program grammar`](../../scripts/game_data/il2cpp/program_grammar.py)
checks branch predicates from original bytes and closes labels at checked
instruction boundaries. Memory widths are checked separately where a decoded
operand name alone would hide a partial reference-slot clear or a wider flag
comparison.

The source and center calls receive their respective TargetSettings and the
original input TargetHandleView. The handle's sole reference field and selected
boxed size establish its single-pointer unboxed representation. The complete
reference-filter helper returns its original input or null; its called class
predicate remains opaque. The actual initialized TypeInfo usage cell selects
the concrete EffectLineCenter Data declaration, but this does not observe a
runtime object or prove the predicate's meaning. Each current `forceMainBody`
zero branch alone enters that target's remap. A true Boolean return selects
the byref output; false retains the original AbilitySystem. The context helper
and actual target/out-slot values remain unevaluated.

Under the caller's unpatched branch and both Entity getters' validated primary
fallthrough returns, all three center-position and source-position components
are copied before either buffer is reused. The subtraction inputs and output
are disjoint, the complete leaf returns its original output buffer, and the
caller writes the twelve-byte center-minus-source displacement into
`centerOffset` of the configuration obtained from its final current Data
reload. Null selected AbilitySystem values branch to the complete epilogue
without that write. `centerOffset` remains an unserialized runtime field;
the persisted `positionOffset` is not this destination. The getter proof is
explicitly conditional on its primary return: initialization, IFix and other
getter paths are not admitted by it.

EffectAction's ordinary `OnCreate` loads the Data's configuration reference
after its base call and stores that same reference in `m_effectActionCfg`;
the checked assignment does not clone it. This closes the creation-time
cache assignment, not later object identity. Data reloads across intervening
calls are not equated, and neither stable references over the action lifetime
nor parent `ExecuteInternal` consumption and effect creation are proved.
These static consumer facts add no serialized field or list/root admission,
and do not establish observed target selection or effect execution.

The independent [`trail consumer validator`](../../scripts/game_data/buff_effect_line_center_trail_native.py)
now checks the ordinary entry prefix that reads the current EffectInstance
`m_data` configuration and forwards all three `centerOffset` components before
calling the current trail receiver's `Start`. Its static query/enumerator
MethodSpec cells consistently select VFXTrailPointsTool; initialized generic
objects and actual query results remain conditional. Ordinary `Start` skips
point calls when `isErosionLine` is nonzero. The trail's offset predicate checks
exact component zero, including negative zero, and treats NaN as nonzero;
the effect-instance entry instead compares the squared displacement to a small
float threshold. The parent execution/configuration lifetime join remains
open, alongside initialized component/query results and actual execution.

The independent [`point consumer validator`](../../scripts/game_data/buff_effect_line_center_points_native.py)
checks the complete ordinary `_ApplyCenterOffset` loop and its per-iteration
value flow. It first requires at least two source points, increments the
temporary list's compiled version slot and zeros its count slot, then checks
the offset predicate and calls `_GetPoints`. The deformation loop begins at
index one. This proves that the loop does not overwrite index zero; preservation
of the original first point still requires the initial population/alias join.
The physical list slots and twelve-byte array stride come from complete
selected get/set consumers and their Vector3 MethodSpecs. Open `List<T>` field
offsets are placeholders and are not used to claim a closed runtime layout.

Within a checked iteration, a complete TransformPoint wrapper binds the input
and output buffers. The loop converts the signed point index and count-minus-one
to Single, multiplies `right` by the converted index and then by
`offset.x / converted(count - 1)`, adds that vector to the TransformPoint output,
and repeats the two multiplications for `forward` and `offset.z` before adding
them to the first sum. These are ordered native Single operations: the multiply
leaf uses the scalar low lane as its first operand, and the formula must not be
collapsed into real-number interpolation or an exact endpoint displacement.
The complete addition/multiplication/axis leaves establish their returned
twelve-byte output buffers and preserve the held list/result pointers used by
the caller. Only x/z are direct displacement operands in this loop; y still
participates in the earlier zero predicate, so a y-only offset is not dismissed
as an inactive path.

The complete InverseTransformPoint wrapper returns its original output buffer,
whose twelve bytes pass through a proved copy wrapper to the selected bounded
list setter. That setter writes one element and increments the compiled version
slot without changing the count slot. The Unity wrappers' indirect internal
calls, coordinate meaning and floating-point environment remain separate from
this buffer proof. The separate population proof below establishes conditional
source transfer; complete initial population still depends on growth and
list/reference lifetime. ApplyPoints/renderer value submission, parent
configuration identity and observed execution remain open. This independent
consumer proof changes no serialized route, positive-list admission or
complete-root count.

The independent [`population consumer validator`](../../scripts/game_data/buff_effect_line_center_population_native.py)
checks the complete ordinary `_GetPoints`, trail constructor, physical Add
wrapper/append, AddWithResize, EnsureCapacity, set_Capacity and selected list
constructor programs. `_GetPoints` starts at index zero, reloads `this.points`
and its current count each iteration, obtains one bounded Vector3 value, and
passes all twelve bytes unchanged through the actual append chain. It does not
clear the destination. The parent offset program clears the temporary count
before this call; equating source and destination can therefore erase the source
count, while a standalone same-header copy can grow its own loop bound.

Whole-source copying without resize is proved only for ordinary successful
paths with stable nonnegative source count/reference/values, an initially empty
destination, distinct list headers, valid nonoverlapping or same-index array
storage, and sufficient destination capacity for every append. These are
explicit selections, not proved runtime preconditions. The constructor stores
the results of two separate allocation and List<Vector3> constructor calls into
the source and temporary fields, initializes useWorldSpace and zero centerOffset,
and retains an anonymous ancestor-byte assignment without naming its meaning.
Neither two allocation calls nor the selected list constructor proves fresh or
zeroed objects, an empty static array, or nonaliasing throughout the lifetime.

The append fast path increments the compiled version and writes one twelve-byte
element at the incoming count. The slow path snapshots that count, requests its
signed-int32 successor, calls EnsureCapacity, reloads the items reference, writes
the successor count and appends at the saved index. EnsureCapacity uses the
reviewed contract's default/maximum constants, a full-width zero-length test,
wrapping dword doubling, an unsigned ceiling comparison and a signed request
comparison in their original order. set_Capacity rejects capacity below count,
returns for equal capacity, forwards the old positive count to Array.Copy, then
replaces items; it does not itself alter count or version.

The actual named Array.Copy declaration has five managed parameters:
source array/index, destination array/index and length. The extra zero qword
stack argument is a trailing IL2CPP context under the static-method ABI, not a
sixth managed copy-policy parameter; its consumer read is not proved. Argument
forwarding does not establish Array.Copy's implementation or preservation of
old elements during resize. Static typed contexts and their complete matching
registration rows also do not equate the registered Add pointer with the actual
optimized append body or establish live RGCTX selection. The next joins are
the array-copy/helper implementation, compatible array class/stride, allocation
and reference lifetime, renderer submission and parent configuration identity.
These consumer facts add no stored route or list/root admission.

The separate [`copy-argument validator`](../../scripts/game_data/buff_effect_line_center_copy_arguments_native.py)
now joins the actual five managed Array.Copy arguments to its selected
same-element-class helper branch and actual bulk-callee entry. Correct REX.X
decoding establishes the extended length/index registers in the dword bounds
expressions. The helper sign-extends the runtime destination-class scalar,
multiplies it by the old count for the byte length, and uses that same scalar
with the source/destination indices to form the two payload addresses. The
multiply and address-add instructions are qword operations. The scalar's live
value and its equality to the separately proved Vector3 element stride remain
an explicit runtime join; this does not name an anonymous class field.

After normal bulk return with the required nonvolatile values preserved, the
selected helper checks an optional static-bitset update, including its qword
bit set and locked compare/exchange retry, then returns AL true through the
complete matching frame. Bitset disjointness from the array payloads and
successful retry termination are separate conditions. The managed caller's
true-result return is checked; its error and false-result fallback paths remain
outside this selection. The bulk body is authenticated in full; the REP subset
below now has conditional copy semantics. Independent proofs below also cover
the selected small, snapshot, bounded-vector and aligned temporal-loop paths;
non-temporal visibility/consumption and backward-overlap paths remain open. Consequently
the old-count-to-byte-length join is direct evidence, while general preservation
of old points across resize stays unresolved.

The independent [`REP copy validator`](../../scripts/game_data/buff_effect_line_center_copy_rep_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_rep_native.json)
revalidate that argument chain against the same opened native image. Complete
selected entry, size, overlap, mode and option blocks join both conditional
branches to the actual leaf entry through RET. The entry preserves the original
destination in the return register; the leaf saves RSI/RDI, copies the incoming
source/destination/byte-count operands into RSI/RDI/RCX, executes the exact
default-address REP MOVSB instruction, restores the saved registers and returns.
Mode and option remain anonymous dword/byte runtime cells. Their current values
and provider names are not supplied by a static branch proof.

Forward copying is established under DF=0, normal complete execution over
valid stable non-wrapping memory, a caller frame disjoint from the payloads,
and destination at/below source or at/above the source endpoint. The overlap
comparison excludes a destination strictly inside the source range from these
REP branches. The byte-prefix invariant then preserves each initial source
byte in the corresponding destination byte without overwriting future unread
source bytes. The [Intel MOVS/REP instruction reference](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf)
supplies the count/direction semantics. The [Windows x64 ABI convention](https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions?view=msvc-170)
is not a measurement of the actual direction flag; DF=0 stays a condition.

Combining this subset with the existing helper and append proofs establishes
conditional old-point preservation only when the same-element selections,
runtime class stride equal to the independently checked Vector3 width,
REP size/mode/option branch, memory/frame conditions, optional static-bitset
disjointness and successful retry all hold. This REP subset does not cover small
growth copying; the independent bounded proof below covers those selected
paths, with the aligned temporal-loop proof below covering selected larger
forward transfers. Non-temporal/backward paths, array providers and
allocation/alias lifetime still need their own proofs. Neither the conditional
copy nor the ABI reference establishes observed
execution, renderer submission or the parent configuration lifetime join.

The shared [`memory-move decoder`](../../scripts/game_data/il2cpp/memory_moves.py)
retains exact GP byte/word/dword/qword and legacy SSE/VEX transfer widths,
independent register/base/index extension bits, signed displacements,
instruction-specific alignment and partial/upper-register effects. It covers
the indexed vector tail forms and original dispatch-table dword loads without
changing the older shared mapper. Unsupported prefixes/maps/register forms and
invalid reserved VEX fields supply no move claim; recognized truncation has a
bounded diagnostic. Its selected padding decoder also keeps an entire legal
multi-prefix NOP in one original byte span without treating the operand as a
memory read. These operand facts are proof tooling, not whole-copy semantics.
The independent bounded consumer below now proves selected small-target,
snapshot and vector joins, table-index bounds, payload coverage and overlap
safety. Decoding other blocks alone still supplies no complete copy effect.

The [`bounded copy validator`](../../scripts/game_data/buff_effect_line_center_copy_small_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_small_native.json)
revalidate the parent argument/REP-selection proof on the same opened image and
authenticate the original dword RVA tables. The small dispatcher uses the
incoming full-width unsigned byte count, a zero-extended table entry and the
checked image base. Every reachable small-table target is checked through its
plain RET. Small and snapshot programs read all required source bytes before
writing, keep every access within the selected payload length, and therefore
retain conditional copy correctness under arbitrary source/destination overlap.

The two bounded vector branches save the head and final vector, round the
length using checked qword arithmetic, and join the resulting bounded index to
an actual instruction boundary in the original tail program. For every integer
length under each native bound, the shared
[`symbolic byte-copy proof`](../../scripts/game_data/il2cpp/byte_copy_programs.py)
tracks each distinct initial-source byte through register loads and stores,
checks every read/write range and proves complete destination coverage. Its
interleaved-load invariant places all earlier relative destination endpoints
at/below the next source start. Consequently a destination at/below source cannot
overwrite an unread source byte, while a destination at/above the source endpoint
is disjoint. The remaining destructive-overlap branch is outside this selection.

The complete selected programs preserve the original destination return value,
stack pointer, required nonvolatile GP registers and low nonvolatile vector
lanes; any vector cleanup follows all payload writes. These fixed memory moves
do not consult DF. The ordinary growth transfer now fits both checked mode
branches, but joining old points to preserved new-array elements still requires
the runtime class stride to equal the independently checked Vector3 width,
compatible current arrays/code/tables, supported instruction state, stable
memory and the parent frame/bitset/normal-return conditions. The separate proof
below closes larger aligned temporal loops. Non-temporal ordering, backward
copies, fresh allocation and reference lifetime remain separate. The bounded proof adds no stored route,
positive-list/root admission, observed execution or renderer/parent lifetime fact.

The [`aligned temporal-loop validator`](../../scripts/game_data/buff_effect_line_center_copy_loops_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_loops_native.json)
revalidate the small/REP/argument chain on the same opened native image. Complete
original alignment, padding, loop and unsigned guards join the bounded vector
prefixes to their actual shared tails. The destination advances to the next
vector boundary, including a full vector advance when already aligned. Source
advances by exactly the same amount and remaining length decreases equally;
the original destination and saved head/final vectors remain available.

The shared [`aligned-loop byte proof`](../../scripts/game_data/il2cpp/aligned_copy_loops.py)
first proves every chunk byte from distinct initial-source identities, checking
the alignment required by each temporal store. The original equal pointer
advances and strictly decreasing unsigned count then establish a natural-number
induction for arbitrary iteration counts under valid stable non-wrapping memory
and the parent forward-safe-overlap selection. This is an induction over the
checked program, not a sample of large copies. Every reachable remainder is
checked against the actual raw table and an original instruction boundary.
Affine byte identities retain the arbitrary copied-prefix displacement and
original endpoint, including saved-last stores that extend before the current
pointer when less than one vector remains. A zero remainder still reaches the
original-head write, closing the skipped alignment prefix.

Combining these programs establishes conditional larger temporal copying and
conditional old-point preservation through the selected helper/append chain.
The wider-vector non-temporal threshold edge is checked but its alternative
body and ordering are not proved here. Runtime class stride and mode/CPU
selection, non-temporal and backward copying, allocation/alias lifetime,
general resize preservation, renderer submission and the parent configuration
join remain open. No stored route or list/root admission changes, and no actual
execution is observed.

The independent [`non-temporal store validator`](../../scripts/game_data/buff_effect_line_center_copy_non_temporal_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_non_temporal_native.json)
now revalidate that parent chain and join the actual wider-vector threshold
edge to the complete non-temporal loop, its distinct raw tail table and every
reachable tail through fence, cleanup and plain return. The counter proof
requires at least one full initial chunk and exits below a chunk; affine tail
proofs retain the original head and endpoint even for a zero remainder.

The shared [`non-temporal value proof`](../../scripts/game_data/il2cpp/non_temporal_copy.py)
checks each streaming-store alignment before projecting only its transferred
byte values onto the existing loop/tail invariants. All writes, including
overlapping cached ordinary stores, carry the corresponding initial-source
bytes. This proves complete store-value coverage after the checked stores
become visible; it does not turn weak non-temporal ordering into ordinary
temporal ordering. The original instruction inventory remains contiguous,
and every reachable payload contains the exact fence after its final write.

The [Intel MOVNTDQ/SFENCE reference](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf)
establishes the aligned register-to-memory transfer and store-fence boundary:
stores before SFENCE become globally visible before following stores. SFENCE
does not order loads. That standalone proof leaves global visibility at RET,
subsequent read consumption and the actual parent publication-store join open;
the separate proof below now joins the actual following publication store.
It does not admit complete non-temporal copying or general resize old-value
preservation. Backward copying, live providers/stride/CPU choices, allocation
and alias lifetime, renderer and parent configuration joins remain separate;
stored/list/root admission and observed execution do not change.

The [`copy-publication validator`](../../scripts/game_data/buff_effect_line_center_copy_publication_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_publication_native.json)
revalidate the non-temporal and complete population proofs on the same selected
native image. The actual positive-count capacity path saves the allocation
result as a full reference, passes it to the checked Array.Copy entry, and
publishes it into the list's items slot in the instruction immediately after
that call returns. Complete original return-frame checks establish preservation
of the saved allocation and list references, under the existing selected
helper/normal-return and valid disjoint frame conditions. The earlier checked
SFENCE therefore orders its payload stores before this actual following store.

The complete bounds-checked getter reads the same compiled reference slot.
The [`scalar memory-fragment proof`](../../scripts/game_data/il2cpp/scalar_memory_moves.py)
checks the original eight-byte MOVSD and four-byte GP transfers and proves all
output bytes equal the selected indexed element's bytes. MOVSD performs no
floating-point conversion; its load clears the next vector qword, whose state
is explicitly outside this low-byte projection. The common symbolic index must
remain unchanged across source reads. This joins complete value consumption
to the published representation without equating separate runtime references.

Conditional old-point preservation now requires the actual publication to be
globally visible and the selected getter to observe that reference before its
payload reads, with stable coherent compatible memory, no intervening overwrite
or interfering alias, valid old-index bounds and disjoint output. All parent
branch/CPU/memory/frame/bitset conditions remain; the live class stride must
equal the independently checked getter width. Neither SFENCE nor the static
store/read join proves those visibility, selection or lifetime conditions.
Allocation freshness, general resize preservation, renderer
and parent configuration joins, stored/list/root admission and observed
execution remain unchanged.

The independent [`backward-copy validator`](../../scripts/game_data/buff_effect_line_center_copy_backward_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_backward_native.json)
now revalidate the argument/common-dispatch proof and authenticate the complete
called bulk body on one selected native image. The actual unsigned overlap edge
enters the complete original backward program before runtime mode selection.
The [`legacy vector decoder`](../../scripts/game_data/il2cpp/backward_copy_instructions.py)
checks full MOVUPS/MOVAPS bit transfers, alignment and preserved upper vector
state, the unchanged low-byte alignment test and complete padding spans;
these moves do not perform floating-point conversion. Original local edges and
qword arithmetic/counters are checked throughout, including the already-aligned
path that skips the unaligned path's remaining-length recomputation.

The [`descending byte proof`](../../scripts/game_data/il2cpp/backward_copy_programs.py)
retains symbolic source positions. Original head/last caches and alignment
establish a copied upper suffix or a cached current vector. A chunk body reads
every byte while writing its upper vectors; its two lowest vectors remain
pending in registers. The repeat header stores both before entering the next
body; the exit stores the upper pending vector and forwards the lowest into the
tail cache. Distinct byte identities establish both completions, and the actual
positive divided counter, single decrement and checked back edge establish
natural-number induction for arbitrary selected chunk counts. A store begins
at or above every later unread source endpoint in relative coordinates; with
destination greater than source, those stores cannot overwrite future reads.

Every bounded post-chunk remainder is checked through the descending vector
tail and final writes. A zero low remainder needs only its cached current
vector; a nonzero low remainder also writes the original cached head. Their
overlapping stores carry agreeing initial-source byte identities. The complete
selected backward program therefore has conditional byte-preservation,
destination-return and nonvolatile-preservation proofs under valid stable
non-wrapping memory and the parent return/frame/bitset conditions. Actual
overlap/stride/CPU choices remain unobserved. Its standalone proof does not
combine the other programs; the combined dispatch proof below now closes that
selection-coverage join. Publication/consumption across all selected paths,
compatible allocation and reference lifetime, general resize preservation and
renderer/parent joins remain separate; stored/list/root admissions do not change.

The [`combined copy-dispatch validator`](../../scripts/game_data/buff_effect_line_center_copy_dispatch_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_dispatch_native.json)
revalidate the complete forward proof chain and backward program on the same
selected native image. Original unsigned size/overlap/mode/option blocks and
both vector prefixes/alignment blocks are decoded again for their actual joins.
Both false option tests fall through exactly into their checked vector prefixes;
bounded and rebased tails, temporal loops, the non-temporal entry and the backward
overlap entry all connect to the complete programs owned by the earlier proofs.
No branch is admitted through a name match or by conjoining report flags alone.

The [`integer-domain partition proof`](../../scripts/game_data/il2cpp/copy_dispatch_domains.py)
uses disjoint closed integer intervals and checked adjacency to cover every
unsigned count and mode, rather than sampling representative lengths. The
option-bit conditions are complementary. With a positive count and non-wrapping
source endpoint, ordered trichotomy partitions destination-before-source,
interior backward overlap and destination-at-or-after-source-end; the actual
CMOVBE and unsigned comparison select exactly the middle case for backward copy.
Every possible masked destination residue has a separate complete count
partition. Alignment advances a full vector width when already aligned, and
the high non-temporal threshold applies to remaining after that advance, not
original length. An originally large count can therefore reach the shared tail
or temporal loop. Integer clipping preserves extreme count endpoints without
inventing wrapped comparisons; only bounded post-loop remainders are rounded.

Together these joins and complete payload proofs establish conditional store
values for every selected program: small and snapshot paths allow arbitrary
overlap, common forward paths use their checked forward-safe overlap, and the
backward path uses the actual interior-overlap selection. Every checked store
carries the corresponding initial-source bytes, including agreeing cached
overlap writes. Valid stable supported compatible ordinary memory, non-wrapping
endpoints, no interfering writes and all same-element/normal-return/frame/bitset
conditions remain required; only selected REP additionally requires clear DF.
Non-temporal visibility retains its fence/publication/observation boundary.
Complete static coverage does not prove global visibility at RET, actual getter
observation, live stride or CPU/option selection, compatible fresh allocation
and reference lifetime, general resize preservation or observed effects. It
does not admit new stored elements, enclosing lists or complete roots.

After the derived action is admitted, reached original-element refusals move
to other actions such as TickInterval, ConvertToTargetContext, SelfRotate and
RayCastEffect, alongside populated nested geometry/validator and damage lists.
Current dispatcher identity names those reached action wrappers; it supplies
no source program, stored child grammar or runtime behavior for the still
refusing action. First-refusal groups and overlapping source reach must remain
distinct from predicted full-root gains.

TickInterval has an independently reviewed current
[`Skill normal-source contract`](../../scripts/game_data/contracts/skill_timeline_tick_interval_native.json)
whose ordered reads name a `SequenceActionData` child. The shared
[`Buff sequence declaration`](../../scripts/game_data/contracts/buff_event_maps_native.json)
and reader remain reusable child evidence. The
[`complete source-flow owner`](../../scripts/game_data/memorypack/buff_tick_interval_sources.py)
now checks the complete unwind-owned caller, generated/inherited setters,
concrete cached-instance getter, FF output clear, normal return and formatter
forwarding against its
[`reviewed contract`](../../scripts/game_data/contracts/buff_tick_interval_sources_native.json).
Each of the nine source returns reaches its metadata-owned Data field under
the explicit normal-call, ABI, compatible-cache and noninterference conditions.
The selected Sequence context is joined to current metadata. The separate
[`source/helper composition owner`](../../scripts/game_data/memorypack/buff_tick_interval_composition.py)
checks the actual physical ReadValue body, same Reader and full reference
output, concrete Sequence adapter/getter and selected complete array-source
programs. That output conditionally reaches the owned `actionOnTick` field.
The actual primitive callees also join independently proved buffered
object-header, normalized byte, Int32 and Single source programs; the Single
low bits reach the owned setter, and the string field uses the proved nullable
valid-UTF8 helper. The Single source window belongs to the per-record source
contract, rather than the containing postprocessor catalog.
These joins require the stated compatible context, provider, cache, ABI,
buffer and normal-return conditions. The closed Sequence usage is metadata
joined, but no compiled row for that particular closed usage or actual runtime
inflation/invocation has been observed. Physical helper naming remains
unresolved. Historical candidate field names cannot replace the current
indexed dispatcher identity.

The [`isolated stored-parent reader`](../../scripts/game_data/memorypack/buff_tick_interval_action.py)
takes the fresh complete recursive native context and the separate Tick
composition proof as distinct inputs. It consumes canonical extended-tag
original parents with all named fields and exact recursive Sequence children;
null wrapper, null/empty arrays, raw terminal flags and valid stored strings
retain their separate representations. Original reached parents now replay
completely with matching independent current-metadata parent boundaries and
unchanged original child receipts. Metadata framing of the following enclosing
bytes supplies only a structural boundary check.

The separate [`Tick union-route owner`](../../scripts/game_data/memorypack/buff_tick_interval_union_route.py)
and [`reviewed route contract`](../../scripts/game_data/contracts/buff_tick_interval_union_route_native.json)
now prove the complete current indexed new-child case and restored return.
The null-prior-wrapper path sends the same Reader through the actual closed
wrapper ReadPackable thunk and shared packable body, stores the full reference
result and passes it through the actual shared barrier. Indexed prefix,
null-cast, restored return, shared contexts and barrier declarations remain in
their existing owning contracts rather than being copied into the Tick
contract. The selected path retains compatible initialized contexts/provider,
null prior output, normal ABI, stable disjoint storage and disabled-barrier
conditions; the reuse path and runtime selection remain separate.
The recursive action owner now registers Tick stored decoding and independently
validates the helper/source and union-route packets. Its adapter requires both
owned proofs and matching current concrete wrapper/original identities, with
no incomplete-proof fallback. The anonymous reader frames the same named
current layout. A fresh complete native context has now been generated by the
full-family gate, preserving its original return and the complete original
source keyset/hashes. Reached original parents pass the global recursive entry
with current metadata boundary agreement, and their enclosing positive
Timeline source elements independently close every field and typed Sequence
child. These element receipts grant no positive-list or whole-root admission;
the independently completed full corpus records no Tick-integration root gains
or regressions. The previous cached validator return is not extended,
relabeled or reused as current. Native action callback cursor equality and
positive-list adapter/root admission remain separate obligations; live
scheduling and effects remain unobserved.

Current named runtime bodies provide a further consumer lane through OnCreate,
ReAssign, ExecuteInternal, OnTick, End and Reset, with V2 kept distinct. The
stored Data reference, runtime counter/timer and frame guards still require
complete receiver/layout and control-flow proofs. The current OnTick primary
and owned chained fragments now decode completely through the existing
[`SSE lane decoder`](../../scripts/game_data/il2cpp/sse_lanes.py). Its complete
register CVTDQ2PS converts signed Int32 lanes to Single; the spurious POP from
the shared mapper's earlier split bytes is not frame restoration. Inexact
conversion follows MXCSR rounding, so no implicit exact-real or default
rounding assumption belongs in a tick formula. See the
[Intel instruction reference](https://cdrdv2-public.intel.com/774492/325383-sdm-vol-2abcd.pdf).
Complete instruction decoding still does not prove operand ownership or
branch selection, and call presence does not prove that the created Sequence
or retained target reaches a later execution call.

The independent named
[`consumer claims`](../../scripts/game_data/contracts/buff_tick_interval_consumers_native.json)
and [`validator`](../../scripts/game_data/buff_tick_interval_consumer_native.py)
now prove the getter's `AlwaysReturnTrue` policy through a complete Int32-backed
enum return and plain epilogue when `IFix.IsPatched` returns false. This policy
does not prove an actual ExecuteInternal/OnTick result. Selected metadata also
identifies OnReset's argument as `AbilityAction.ResetReason`, an Int32-backed
enum, rather than a byte Boolean. Forwarding that argument to the cached
Sequence receiver remains a separate ownership and call-ABI obligation.
The existing strict generic-reference layout checker refuses the concrete
Tick witness because its instance suffix has a gap; the selected closed parent
has no alternative immediate concrete witness. Preserve this refusal until a
separate layout or accessor proof authenticates the closed Data slot. Do not
reuse an open generic offset or silently admit suffix padding.
The selected compiled generic-method registration search provides no usable
closed Tick accessor entry; this says nothing about runtime inflation and
does not establish the slot by absence.

Reached original tick-sequence prefixes contain damage actions. Canonical
zero/FF Finder children now have an independent
[`source/type owner`](../../scripts/game_data/memorypack/buff_selector_zero_finders.py).
The [`recursive selector`](../../scripts/game_data/memorypack/buff_find_target_action.py)
now routes these tags to their source/type owner and refuses missing, mismatched
or incomplete native proof. The anonymous boundary reader also frames the
proved GuardAI and Typhoea zero-field tags. Fresh complete recursive native
validation and original Damage child replay now establish their current stored
composition. The complete family gate preserves the original source keyset and
hashes, records full-root gains, and reports no regressions. Generated counts,
source catalogs and replay receipts stay in reports; TickInterval's positive
list and enclosing runtime consumption remain open.
Isolated child replay grants no enclosing action, element, list or root receipt;
live context/formatter selection, ticking and damage effects remain separate.

CircularOrderSort and NavMesh lists can be embedded inside these positive
timeline records. Closing their local lists does not close the enclosing
TimelineActionData list: the root's conservative suffix frontier remains,
and selected related roots independently replay from byte zero until the
positive timeline count refuses. Earlier structural action receipts can still
retain anonymous naming obligations; structural eligibility and the native
forward replay's first refusal are separate evidence.
The maintained
[`buff_timeline_empty_native`](../../scripts/game_data/memorypack/buff_timeline_empty_native.py)
gate deliberately admits only null or empty lists; positive-list composition
must reuse the proved element identity without bypassing that boundary.

Find the first incorrect field before interpreting a late parse failure. In the
complete candidate, CheckSkillInterruptReason's `reasonList` required the
selected metadata's Int32 enum-element grammar; treating its elements as object
headers caused a later false PoiseModifier anomaly. The remaining missing
declarations were AttributeOverrideEntry (`attributeType`, `overrideValue`) and
BuffValidator (`buffFindSettings`, `validateMode`). Their historical or generated
names alone do not prove current source reads or nested union selection.

Static lifetime analysis also exposed an argument-location tooling gap:
`BodyIndex.parameter_location` describes general-purpose registers and cannot
prove a floating-point argument's carrier. The observed RawSetLifeTime caller
and callee use a SIMD register for `time`. A typed ABI resolver and direct value
flow proof are required before admitting lifetime arithmetic into that parameter;
existing call presence is insufficient.

The shared LevelScript reader now admits `GetClientMapVar` and
`GetSquadInFight` through the generic per-route Deserialize validator and
their reviewed contracts. Selected complete owners rejoin physical EOF after
those getter nodes. The map-variable getter stores an authored key and a
nonconstant map-ID Param selection; it does not supply a current map or live
variable value. The squad getter stores only inherited node fields, not an
authored combat-state result. Whole-owner publication still requires the
authenticated combined JsonData gate. The mount-point getter now uses the same
generated-reader proof, including its separately checked enum backing type;
stored entity and position operands remain unevaluated.

Grouped and specialized current parent contracts extend this pattern across
action and getter cohorts. Full native reader fragments and exact typed calls
authenticate the parent; Param, list, mask and blackboard children still need
their own current gates. Enum Params additionally require a selected-metadata
backing-type proof; missing or wrong declarations fail closed with a named diagnostic.
Nonconstant getter slots remain stored operands, not evaluated values.
Derivation must reproduce the resulting declarations; source-span
replay measures route admission, and the sequential owner separately measures
EOF or the next refusal. Recovering a cinematic, NPC or arithmetic node never
establishes its live execution, result or mission ordering. Current route lists
and source spans belong in the reviewed contract, with corpus deltas in reports.

Plain collection fields additionally require their own typed `ReadPackable`
join. The isolated v6 integer-switch contract covers only `SwitchIntLarger`'s
`caseIDList` and `caseValueList` through the exact `List<int>` reference ABI.
Its independent `levelscript_int_list_native.py` gate authenticates the current
list and Int32 formatters, typed contexts, signed Int32 count, null sentinel and
raw four-byte elements. Selected complete programs prove null, empty and positive
new/reused list paths, growth/copy and the element source, cursor, store and loop.
The current static setup maps open `List<>` to `ListFormatter<>`; it is not an
eager `Register<List<int>>` proof. The initialized successful provider path and
normal helper effects remain conditions. This admits neither arbitrary generic
lists nor `Param<List<int>>`, effective provider selection, or a Switch-bearing
source owner and EOF. A scanned signature is not an authenticated owner cursor.

Environment-talk wrappers carry a reviewed generated formatter composition
under its stated matching-route conditions. Their string/Int32 child order and
positive source occurrences alone would not suffice: admission additionally
authenticates the typed parent and list contexts, registered adapters and
concrete formatter/conversion identities. Effective provider selection and
whole-owner source admission remain independent.

The canonical JsonData report retains the complete LevelScript reader detail.
Data may reuse that result only when the versioned reader-input receipt also
matches a fresh, complete path enumeration and byte snapshot. That scope covers
the raw-format package, external shared imports and the native metadata/mapper
helpers; a saved dependency path list or the narrower development cache closure
cannot establish admission. Canonical start/end snapshots must match, and Data
rechecks the selected native/source receipt, full ledger fingerprint, complete
LevelScript source path set and every source length/hash before and after its
projection. Detail payloads remain unchanged, including their Json-relative
refusal locators; the outer Data source descriptor retains the full export path.
Missing, old or changed receipts invoke the maintained direct reader and bypass
the older page cache. Native-input failure makes the dataset unavailable before
either path. Receipt reuse does not promote partial owners or runtime meaning.

LevelScript native refusals remain distinct from unknown stored schemas. Module
grammar failures carry an explicit `nativeContract` marker; task-condition
failures retain their owning audit only when the authenticated current union
identity matches the reviewed wrapper and member count. An unused contract
failure or a changed member count does not turn an unknown condition into a
native failure. All attempted owner lanes retain their nested diagnostics,
including when a later lane reaches EOF, so a fallback cannot hide a reached
native-proof refusal. These diagnostics do not admit additional layouts.

The module dictionary preserves the reached union tag, serialized member
count and dictionary entry locator in `stopDetail.diagnostics`. A managed
module name is supplied only by the authenticated current union table; a
missing parser for that named union remains a stored-grammar gap. The key is
an opaque stored identifier, and field metadata alone supplies no expected
serialized member count. Null dictionaries and null union values retain their
existing branches without requiring a positive-value native proof. A rejected
module leaves the cursor at the original dictionary count boundary; naming
the refusal does not consume its interior or establish a runtime module.

The independent `levelscript_corpus` receipt authenticates only LevelScript
and LevelScriptTemplate stored results for its selected run. It does not depend
on Buff or Skill receipts. It retains the complete raw-package before/after
snapshot and the native, running CLI, terminal chunk and source-content gates;
current VFS bytes must join the existing export exactly. A successful receipt
can describe these two families, but cannot replace complete JsonData registry
closure or authorize WebUI publication. A refused run publishes no current
family result.

Authenticate a selected-source association while the complete family receipt's
reader scope is still frozen. Preserve its fixed generated artifact identity,
the selected source length/hash and the independently proved cursor spans in
the report; do not inherit its stored-schema status or candidate EOF. Subsequent
route edits invalidate that receipt as a current whole-family result, while
the separately authenticated source identity remains usable for explicitly
selected replay. The real admitted owner must establish its own EOF or refusal.

The stored route lane also admits entity-list getter/clear operations,
navmesh-area removal, the start-dungeon banner, event-log parameter changes
and entity-skill interruption. The interruption output uses its own typed
`ParamOutput<bool>` ReadValue context; sharing the nullable output wire grammar
does not permit substituting a different generic output. These routes retain
authored values and cursor boundaries only, without proving an emitted banner,
a navmesh change, an interrupt result or runtime list contents.
The following stored parents cover entity-skill attachment, tutorial restart
and level-sequence resume. Each has independent wrapper, member-count,
ordered-reader and setter evidence plus authenticated selected cursor spans;
none proves that the authored skill was attached, the game restarted or the
referenced sequence resumed.
The stored drone-cache/clear, spline-leave, unique-world-effect finish,
footstep-effect override and travel-pole cutscene handover parents use the
same separately proved base and Param grammars. Footstep target type is a
direct signed Int32 enum with its own metadata backing gate and the shared
Int32 read target, not a Param generic substitution. No effect asset, camera
behavior, drone ownership, movement or cutscene execution is established.
Further stored parents cover rune-column and special-sight operands, integer
list addition, blackscreen/kickable-trigger query definitions, enemy-pool and
drone-list controls, camera-follow effects, pivot/turn disable operands,
spawner references, factory battle-building state/target operands and movement
input-lock duration. The script-start getter identifies a stored query
definition without an observed result. Existing Param, output and bounded-list
grammars remain gated by the selected typed reader contexts; no live state,
effect binding, battle behavior or input-lock execution follows from these rows.

- `native_union_atlas` checks every union contract in one native context
  with family-qualified tags; publication still needs full corpus gates.
- A Skill replay cache keyed by `dependency_snapshot` reproduces warm and miss
  rows faster, but it is a prototype: changed bytes need a fresh stream, and
  admitting a route can change old bounded rows.

## Eliminated readings

Each line is a reading that was tested and refused; the owning module's
docstring keeps the refuting test.

**JsonData families and tables**

- `SerializeFieldDictionary` header as map count; `MapMarkTempTable` key
  always equal to `markInfoId`; marker group key as scene or level.
- UID-shaped bytes or an audio-map scan as extents; TriggerZone owning a
  later audio-key map; one tag number reused across union families.
- Buff: one-byte `FF` as `0x00FF`; anonymous first `globalModifier` member;
  compact-stacking EOF as ownership; shifted `tagsAfterTriggerExtendBuffAction`.
- Quest state `1`; `0x04B1` as `StopLevelSeqLoopSegment`; `AirWallPtr` as
  `EntityPtr`; `StartLevelCustomPerformance` bool as always present.
- `posList` as three floats; `preWarnEffectFixedRotation` as four floats;
  AnimationConfig offset 62 as `montages`; bulk `FKeyframe` in wrapper order;
  `npcMontages` tags as 64-bit; MontageNew 20-byte vectors; `renderNodes`
  count equal to `nodeCount`; a corpus enum subset for component keys.

**LevelScript unions**

- Byte-7 action-map framing (first list count only); a terminal template ID
  making earlier bytes exact; a child layout guessed from member count or
  position; an outer `WaitForCondition` licensing a nested-condition parse;
  merging dispatcher domains on identical scalar layouts.
- All-EOF `0x00DC`/`0x0065` projections: a scratch counter bug.

**SkillData**

- A one-byte-later terminal for sources whose executed cursors select the
  earlier one; treating the ordinary formatter/provider profile as an observed
  runtime selection; EOF validity or another source's witness as a terminal
  selector; promotion by derived-plan EOF, a same-tag layout, or a tag only
  the Buff reader admits.
- A diagnostic integer as a physical tag without a failed union-tag check;
  `FA FF 00` (`0x00FF`) as null; `BoneAttachAction` `0x0000` as a sentinel;
  `CheckSuperArmor` tail anomalies as offset errors (later bytes select other
  routes).
- SkillAIMove `markerInfo` as a wrapper call (it is an eight-byte unmanaged
  copy); `TeleportPosSelectAction` as an alias of `TeleportAction`; Buff's
  compact selector-tag or handwritten tag/member-count tables applied to Skill.
- A PlayAnimation prefix outranking a complete shared-sequence profile; broad
  catches that dropped later refusals; per-build RVAs or method indexes in
  Python as identity; file bytes for virtual-only PE globals.

**Formatter identity and wire framing**

- Identity: the `GetFormatter<T>` counterexample (a probe indirection bug);
  `table + i*16` as a record address; byte equality with `System.Object`
  selecting a shared body; all switch-table pins as one union; reviewed rows
  joined by tag across unions instead of by type name.
- Types: declaration order as wire order; nested-union tags in ordinal order;
  a subclass making a type a union; a memberless wrapper as unresolvable; an
  enum's base as `System.ValueType` or every enum as four bytes; a struct as
  the sum of its member widths; a four-byte output slot as a serialized width.
- Framing: one framing for list and array elements; a counted map with a
  managed side as unreadable; a short `ForceSyncAnimData` header (cursor
  drift); a depth limit of 24 or an empty (falsy) `PlanRegistry` as a
  schema signal; the reference census counting more than nested `skillId`;
  `MissionRuntimeAsset` payloads as MemoryPack (they are JSON).

The USP parent is independently composed by
[`buff_refrain_obtain_usp.py`](../../scripts/game_data/memorypack/buff_refrain_obtain_usp.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_refrain_obtain_usp_native.json).
Its inherited fields, `clearUspOnEnd`, `refrainObtainUspTags` and `targetSettings`
retain source order, declared types and their own byte intervals. GameplayTagList
reuses the independent tag object/element reader; TargetSettings requires its
independent recursive receipt. Their closed source contexts join independent
child runtime definitions and source-bound wrapper plans. Every field reencodes
its exact original bytes, and non-scalar child receipts bind their named trees.

Null parent, null union, null tag object, null/empty tag list and null tag element
remain distinct. Positive targets cannot close without their independent reader.
The maintained recursive dispatcher uses the selected contract's current tag;
an old-version tag is refused. The native aggregator first resolves and gates
the selected binaries, then passes those explicit paths to the parent owner.
Missing or mismatched inputs cannot produce a validated parent.

The frozen maintained-reader epoch has its own full Buff corpus gate and original
gained-root replay. Each admitted root closes all thirty fields from byte zero,
checks its source ID and ends at physical EOF with complete receipt equality.
Earlier complete roots and consumer claims retain their original scopes.
Changing coverage counts and per-source inventories remain in generated reports.
Stored clear flags, tags and targets do not establish actual formatter/provider
selection, selected entities, USP suppression or clearing. Remaining structures
and the missing original Skill receipt remain separate acceptance obligations.

The camera group's `and` source has a separately reviewed correction in
[`buff_camera_condition_group_source_return_native.json`](../../scripts/game_data/contracts/buff_camera_condition_group_source_return_native.json)
and [its validator](../../scripts/game_data/camera_condition_group_source_return_native.py).
The earlier camera source catalog selected the error-path call preceding an
INT3 as the value origin. The normal path instead preserves the preceding
source helper's full reference return into the setter argument when the receiver
is nonzero. A zero receiver reaches the error call and trap, with no ordinary
setter continuation. The legacy catalog remains a historical scope and is not
accepted as the normal source-return proof for this field.

Both outer camera condition lists and the group's inner list pass their own
closed `ReadPackable` contexts to the actual shared helper whose selected
Reader/local-output/return transfer is reviewed by
[`buff_timeline_root_list_native.json`](../../scripts/game_data/contracts/buff_timeline_root_list_native.json).
This physical join does not replace either concrete list or element type with
the shared Object type. Their direct closed compiled entries remain absent;
static registrations and actual provider selection are distinct obligations.

[`buff_camera_list_constructor`](../../scripts/game_data/memorypack/buff_camera_list_constructor.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_camera_list_constructor_native.json)
join both concrete list registrations to the independently registered shared
Object constructor and check its complete exception-owned primary and cold
ranges. The complete control reads an anonymous context chain, returns without
calls when its guard is nonzero, and otherwise re-reads the context and calls
through its slot-zero pointer before rejoining the restored return. It has no
explicit data stores or dereference of the entry receiver. The cold callee's
effects, context-slot semantic names, actual generic inflation and provider
selection remain unresolved. A normally returning indirect call and ordinary
Win64 stack preservation are conditions of the cold return proof.

These source and constructor joins grant no positive condition-list grammar,
camera parent or complete root admission. Concrete element conversion, list
cursor composition and actual camera evaluation remain separate work.

The independently registered shared Object `Deserialize` entry now has a
complete local control and normal-frame validator in
[`reference_list_control`](../../scripts/game_data/il2cpp/reference_list_control.py)
and [`buff_shared_reference_list`](../../scripts/game_data/memorypack/buff_shared_reference_list.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_shared_reference_list_native.json).
All declared primary and chained ranges are included; the earlier primary-only
prefix was not the complete program. Selected adjacent instructions load a
pointer, sign-extend its DWORD and save that DWORD in the caller's stack home.
The callback output address, QWORD slot reload and indexed QWORD store establish
an eight-byte reference-cell representation on this compiled Object path.
That representation does not establish an enum's element wire width or a
concrete camera/DamageType collection.

The complete graph includes local branches, indirect-call continuations,
ordinary returns and trap sites. It does not prove other memory effects,
callback algorithms, GC bitmap meaning, loop termination or actual context and
formatter selection. Whole-list cursor composition and parent/root admission
remain unresolved. Contract comparison preserves all registration fields while
normalizing the tuple/list distinction introduced by JSON serialization.

Its count/null/loop slices now have a separate semantic grammar in the same
owner. The count guard compares the signed interpretation of a wrapped QWORD
total-minus-sign-extended-consumed calculation with the signed source count.
The direct cursor update adds four at the native pointer/DWORD widths; its
alternate helper is selected by the sign flag of a wrapped DWORD subtraction.
These calculations do not independently establish valid byte bounds.

After that guard passes, a count of minus one takes an output-clearing branch
with no provider or element calls. The nonnull branch performs its provider
query candidate before testing whether the count is positive, so an empty
count still reaches that query. No explicit rejection of counts below minus
one is proved here; an opaque constructor or helper can still reject them.
The element call receives the saved candidate result, saved reader argument,
local output-slot address and a fresh companion from a fresh class read.
Selected nonvolatile origins are tracked across the complete graph's joins and
backedges; an unmodelled setup or loop-body write cannot retain a saved origin.
The loop reloads its saved DWORD bound rather than the register later reused
for context. Stable bound/output storage, ordinary callees, valid references
and synchronization progress remain conditions of a callback-count argument;
the program does not guarantee a number of executed callbacks.

The inherited list constructor context is independently joined by
[`list_formatter_base_context`](../../scripts/game_data/memorypack/list_formatter_base_context.py)
and [`buff_camera_base_constructor`](../../scripts/game_data/memorypack/buff_camera_base_constructor.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_base_constructor_native.json).
The complete declared ListFormatter class context names its inherited constructor
at slot seven and declared parent at slot eight. The actual parent type is
`MemoryPackFormatter<List<T>>`; its argument pointer and the inherited constructor's
argument pointer both equal the List type tied to the reciprocal ListFormatter
parameter. This is a static generic identity, not a populated runtime slot receipt.

An independently selected Object base-constructor registration points to code
shared by other method definitions. The
[`registration observer`](../../scripts/game_data/il2cpp/generic_entries.py)
retains those aliases, null pointers and duplicate rows; the strict resolver
continues to reject folded method identity. The registered entry begins with
`RET 0`. Its closed entry program preserves flags/general registers, performs
no explicit data stores and pops only the ordinary return address when entered
with a readable valid return stack. This establishes neither a unique named
body nor the full physical function extent beyond that return.

The camera constructor's cold indirect target has not been observed to equal
that registered pointer. Runtime slot geometry/population, original context
inflation and other selected call effects remain separate obligations. The
declared slot, argument equality and folded entry program grant no positive
camera list, parent or complete-root admission.

The constructor context's publication geometry now joins the complete
exception-owned initializer instruction graph through
[`context_slot_initializer_control`](../../scripts/game_data/il2cpp/context_slot_initializer_control.py)
and [`buff_camera_context_slot_publication`](../../scripts/game_data/memorypack/buff_camera_context_slot_publication.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_context_slot_publication_native.json).
Every local branch/normal call continuation reaches an instruction boundary;
normal calls have aligned home space and normal returns restore the entry stack.
Trap exits and indirect call locations remain explicit. This syntactic graph
does not prove loop termination, helper effects or actual initialization.

The selected range result supplies the same start and count used by the loop.
The start indexes sixteen-byte definitions; each normal iteration advances the
definition pointer by sixteen and the output pointer by eight, then decrements
the remaining count. At loop completion the original compatible array return
is reloaded and published into the class context field. Lookup selection,
allocation/fill semantics and stable disjoint frame/definition/output storage
remain conditions, rather than observations of a live array.

The method-kind branch reads the declaration payload index, passes two distinct
descriptor operands to the same helper with one saved generic context, and
constructs a three-QWORD local key. Its final pointer-producing helper's complete
return is stored into the current output slot. Descriptor substitution, cache
contents/selection and the intervening helper effects remain unresolved.

Under those stated compatible-class/module and normal-helper conditions, the
inherited constructor declaration at slot seven occupies byte offset fifty-six
in the published slot array, matching the constructor's checked physical read.
This closes the conditional geometry connection; it does not observe slot seven,
select its actual cold target or grant positive camera list/root admission.

The method-slot descriptor getter is independently joined by
[`method_spec_descriptor_control`](../../scripts/game_data/il2cpp/method_spec_descriptor_control.py)
and [`buff_camera_method_spec_descriptor`](../../scripts/game_data/memorypack/buff_camera_method_spec_descriptor.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_method_spec_descriptor_native.json).
Its complete exception-owned control sign-extends the input index, addresses a
twelve-byte MethodSpec record and forwards its definition index to the plain
definition helper. Class and method instantiation indices remain separate:
each uses an eight-byte pointer-table slot, while the signed sentinel produces
a zero argument. The selected inherited-constructor row independently joins
the previously proved List<T> class instantiation and null method instantiation.

The cold composition receives the definition helper's return and both selected
instantiation pointers. Its full return is written to the indexed descriptor
cache cell, but the ordinary return re-reads that cell. The hit branch likewise
tests and reads the cache separately. Concurrent cache/global changes can
therefore change the later return; neither a nonzero test nor a stored pointer
proves the eventual returned value without a stability condition.

The helper performs no input-index bounds check. Nonnegative in-range signed
indices, compatible registration/tables, valid cache storage and normally
returning ABI-preserving helpers remain explicit conditions. Descriptor
identity, definition helper and cache effects, actual cache history, parameter
substitution and the runtime cold target remain unresolved. This descriptor
join does not admit a positive camera list, parent or whole root.

The actual composition callee now has a complete exception-owned graph and
CFG-joined argument origins in
[`descriptor_composition_control`](../../scripts/game_data/il2cpp/descriptor_composition_control.py)
and [`buff_camera_descriptor_composition`](../../scripts/game_data/memorypack/buff_camera_descriptor_composition.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_descriptor_composition_native.json).
The new branch requests twenty-four bytes and emits three QWORD stores at
offsets zero, eight and sixteen. Their sources are respectively the plain
definition helper return, class instantiation pointer and method instantiation
pointer already proved at the caller. Entry arguments are saved in nonvolatile
registers; all local branches and backedges join their origins before each store.
The proof refuses partial-register overwrites and bypass paths rather than
assuming that address order establishes preservation.

The hit branch reads the selected cache entry's value pointer, while the new
branch saves the allocation return. Both pass the saved pointer to the normal
return through the complete suffix. This establishes the emitted triple layout
under valid disjoint allocation/storage and normal Win64 nonvolatile/stack-
preserving callees. It does not prove allocation success, that the lookup key
equals the supplied triple, or that insertion and later synchronization calls
leave its pointee contents intact. Those calls and the retry loop remain visible
in the complete graph; termination, concurrency and actual effects are open.

Definition identity, instantiation transformation, final method-pointer lookup,
runtime cold-target selection and positive camera list grammar still need their
own evidence. No positive list, parent or whole root is admitted by this scope.

The composition's lookup call now joins the complete explicit probe in
[`descriptor_cache_lookup_control`](../../scripts/game_data/il2cpp/descriptor_cache_lookup_control.py)
and [`buff_camera_descriptor_cache_lookup`](../../scripts/game_data/memorypack/buff_camera_descriptor_cache_lookup.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_descriptor_cache_lookup_native.json).
For a coherent zero-flag query wrapper, an explicit probe hit requires equality
of all three QWORDs at offsets zero, eight and sixteen between the query triple
and the selected entry's value. The entry stores a DWORD marker and its value
pointer in a sixteen-byte stride. A nonzero wrapper flag can bypass the triple
comparison; that separate branch does not acquire the zero-flag claim.

The complete graph distinguishes an explicit miss, which stores the end pointer
as both current and end, from a hit, which stores the selected current pointer
and end separately. Both return the supplied output address. The early
count-comparison branch delegates to an empty-output helper. Its conditional
end stores are joined below; the original explicit-probe proof alone did not
establish every result the caller might interpret as a cache hit.

The caller's frame joins the initialized temporary three-QWORD key, its
zero-flag wrapper and the separate iterator output. It reads the output's
current pointer, compares it with a freshly computed global end, then reads
the selected entry's value pointer on its hit branch. The new allocation is
passed through the same wrapper shape to the separate insertion call. Local
key contents across preceding opaque calls and current/global values after
lookup require stability conditions; frame geometry alone does not prove them.

Hashing reads an anonymous DWORD from the first key pointee and combines it
with shifted class/method pointer bits. Each advance increments a step counter,
adds it to the current index and masks again. The mask is initially capacity
minus one. The helper proof below joins the actual preservation of R9, R10
and R11; ordinary Win64 preservation alone could not establish those values.
Scan termination, opaque growth effects and subsequent descriptor contents remain unresolved; the local insertion stores are joined below. No runtime
selection, positive camera list or whole root is admitted by this scope.

The comparator and empty-output helpers now have their own
[`descriptor_cache_helper_control`](../../scripts/game_data/il2cpp/descriptor_cache_helper_control.py)
and [`buff_camera_descriptor_cache_helpers`](../../scripts/game_data/memorypack/buff_camera_descriptor_cache_helpers.py)
proof, under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_descriptor_cache_helpers_native.json).
The comparator lacks a declared exception entry, so
[`closed_leaf_entry`](../../scripts/game_data/il2cpp/closed_leaf_entry.py)
decodes every reachable branch from bounded selected bytes. Every reached
instruction belongs to a closed call-free graph; no branch escapes or enters
an instruction interior. Unused following bytes and physical function extent
remain outside that proof.

The comparator first checks two DWORD wrapper markers. Unequal markers return
zero AL; equal nonzero markers return one AL without reading the triples.
Equal zero markers require equality of all three QWORDs. Only AL is the boolean
result; upper RAX bits are not generally cleared. Its complete reachable
program writes no memory and changes only RAX, RCX and R8 among general
registers. In particular R9, R10 and R11 remain unchanged. Actual caller bytes
join this effect proof to the probe and iterator constructor, closing the
previously opaque preservation of their index, step, mask and output pointers.

The complete iterator constructor stores table, current and end at their
separate QWORD offsets and returns the original output address. Equal initial
current/end skips scanning. Its optional scan advances current by the entry
stride and calls the same now-proved comparator; no scan-termination claim is
made. The constructor also preserves R11 throughout its complete graph.

The complete empty-output helper passes the output address, two separately
computed end values and a fifth stack argument to that constructor. Both ends
use the same capacity sample but separate begin-global reads. When those reads
agree and storage is valid, current equals end and the constructor skips its
scan; preserved R11 supplies the original output address on return. Together
with the existing zero-flag explicit probe and caller frame join, coherent
key/current/end globals conditionally exclude an empty-output false hit.

This closes the selected helper effects, not concurrent cache history or an
observed runtime selection. Key contents across earlier opaque calls, changing
globals after lookup, insertion and later descriptor contents remain separate
obligations. A physical comparator function extent is still not inferred, and
no positive camera list, parent or whole root is admitted by this scope.

The actual insertion call now has a complete exception-owned control and
selected write proof in
[`descriptor_cache_insertion_control`](../../scripts/game_data/il2cpp/descriptor_cache_insertion_control.py)
and [`buff_camera_descriptor_cache_insertion`](../../scripts/game_data/memorypack/buff_camera_descriptor_cache_insertion.py),
under its [reviewed contract](../../scripts/game_data/contracts/buff_camera_descriptor_cache_insertion_native.json).
The new-entry path writes a fresh wrapper DWORD marker at entry offset zero and
a fresh wrapper value pointer at offset eight in a sixteen-byte entry stride.
Its counter choice either increments the stored count or decrements an auxiliary
count before the selected entry write. The matched-existing path does not make
those local entry stores. Opaque rebuild and growth calls may have other
effects, so this local distinction does not declare a side-effect-free function.

Both paths return the supplied output address and store table, current and end
pointers followed by a distinct inserted byte. The new path sets that byte to
one, while the existing path sets it to zero. The selected current pointer is
computed from the corresponding new or matched slot. A scalar memory QWORD
round trip preserves the stored end, and a packed pair plus an eight-byte vector
shift supplies table and current to separate QWORD stores. Their physical widths
are checked by the existing memory-move reader and
[`scalar_double_memory`](../../scripts/game_data/il2cpp/scalar_double_memory.py);
unused upper vector lanes do not acquire a claim from the scalar reader.

The complete graph includes a rebuild-request candidate, capacity candidates, replacement,
publication, conditional release and error calls followed by traps. After a
growth path it reloads capacity/count before hashing again. Its floating-point
capacity routing is checked structurally, without asserting a load-factor or
rounding policy. The previously proved comparator preserves the live probe
registers, and this caller explicitly reloads the query value pointer after a
probe call. Input/output pointers saved in nonvolatile registers remain subject
to normal callee and disjoint-storage conditions.

The composition retains its separately saved allocation pointer across the
insertion call under its established ABI conditions. The insertion result
record is not proved to replace that saved return with an existing entry value.
Fresh wrapper reads and opaque calls also leave a pointer/content stability
obligation; emitted writes do not prove that every insertion stores the original
allocation or that the caller returns the entry ultimately retained in the map.

Allocation/migration/release effects, numeric growth policy, termination,
concurrency and later descriptor contents remain unresolved. This complete
insertion program proof does not establish runtime selection or admit a positive
camera list, parent or whole root.

The recorded initialization-candidate name is now refined by
[`descriptor_cache_rebuild_request_control`](../../scripts/game_data/il2cpp/descriptor_cache_rebuild_request_control.py)
and [`buff_camera_descriptor_cache_rebuild`](../../scripts/game_data/memorypack/buff_camera_descriptor_cache_rebuild.py),
under the [request contract](../../scripts/game_data/contracts/buff_camera_descriptor_cache_rebuild_request_native.json).
It is a guarded capacity-halving request program, not a proved bootstrap
initializer. A nonzero threshold, an unsigned stored-count-minus-auxiliary-count
difference below that threshold, and an initial capacity greater than the cutoff
are required before it halves the candidate. Subsequent FP comparisons may halve
it again; the candidate cutoff stops further iteration, without establishing an
unconditional minimum candidate for arbitrary initial capacities.

Guard exits return zero AL. The selected temporary passes through replacement,
publication and cleanup calls; if they normally return under the saved-register
conditions, the program returns one AL. Every normal return clears the request
byte. One AL proves that path selection, not successful allocation, migration
or cleanup. Numeric FP policy, helper success and live scheduling remain open.

The joined call-free publication body is checked by
[`descriptor_cache_publication_control`](../../scripts/game_data/il2cpp/descriptor_cache_publication_control.py)
under its [publication contract](../../scripts/game_data/contracts/buff_camera_descriptor_cache_publication_native.json).
Selected byte, DWORD and QWORD fields move in both directions between the
temporary and global object, including capacity, marker/triple and entry-array
storage already consumed by the lookup/insertion proofs. Two initial packed
blocks exchange, but subsequent threshold calculations overwrite their leading
QWORDs and both request bytes are cleared. That is not a whole-object exact swap.

The returned record's packed control block has only two old-global byte ranges
proved through its scratch vector: one byte and one DWORD. Its remaining bytes
come from unmodelled entry-stack contents; they are not classified as padding
or assigned a field meaning. The separate scalar QWORD transfer remains exact.
This partial representation must not be promoted to a complete known object.

Publication consists of separate reads and writes. Coherent disjoint storage
conditions do not make it atomic, and the structural FP routing does not prove
a numeric threshold policy. Allocation/migration and cleanup bodies, pointer
history, concurrent visibility, runtime descriptor selection and positive camera
list/root admission remain separate obligations.

The old-array cleanup field now joins the complete release routing through
[`descriptor_temporary_cleanup_control`](../../scripts/game_data/il2cpp/descriptor_temporary_cleanup_control.py),
[`descriptor_release_control`](../../scripts/game_data/il2cpp/descriptor_release_control.py)
and [`buff_camera_descriptor_temporary_cleanup`](../../scripts/game_data/memorypack/buff_camera_descriptor_temporary_cleanup.py),
under the [reviewed contract](../../scripts/game_data/contracts/buff_camera_descriptor_temporary_cleanup_native.json).
The selected temporary field is the same QWORD offset that publication receives
from the old global entry-array pointer. Cleanup tests the field and reloads it
separately before passing the fresh value in RCX. A changing field can therefore
alter the actual argument even after a nonzero test.

The entry thunk is an exact tail jump preserving arguments, stack and flags;
its physical function extent remains unclaimed. The complete destination skips
heap/error calls for null input. Otherwise it passes the entry pointer in R8,
zero flags in RDX and a fresh heap-handle global in RCX to the declared HeapFree
IAT cell. The existing
[`PE import reader`](../../scripts/game_data/il2cpp/pe_imports.py)
proves terminated lookup-table ownership, unbound on-disk IAT equality and
KERNEL32.dll symbol declarations for HeapFree and GetLastError. It establishes
neither a live IAT binding nor a loaded callee identity.

Nonzero low EAX from the heap call skips the error path. Zero EAX calls the
declared GetLastError cell, forwards that DWORD to a local conversion helper,
saves its EAX and writes that DWORD through a second helper's full returned
pointer. The helper algorithms and writable-slot identity remain separate
obligations; ordinary return is not a whole-function success Boolean.

The documented [HeapFree contract](https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree)
permits interpreting nonzero as success only under genuine binding and valid
heap/block ownership. [GetLastError](https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-getlasterror)
supplies the calling thread's last-error value. Those API contracts do not prove
this program's handle, block ownership, binding or actual successful release.
The evidence remains conditional native argument/error flow, not a runtime
cleanup observation or positive camera list/root admission.

## Remaining gaps

The ordered queue across families is in
[`../game_data_recovery.md`](../game_data_recovery.md); these are the open
items this topic owns.

- **BuffData.** Recover shared event-action children and compose already proved
  root fields before adding source-specific exceptions. Other positive
  `attributeModifier` and `healModifier` processor interiors; remaining action
  parents, selector finders and nested direction targets; timeline and
  `stackEffects` interiors; string encoding remain open. Rank distinct residual
  sources after excluding complete roots. Separate recursive child refusals
  from a missing whole-root receipt; overlapping child reach does not predict
  complete-root admission. CheckEntityNum and AddGlobalCDTimer now have
  independent general parent gates in the shared Buff event-map reader;
  their older source-bound or SkillData proofs are insufficient on their own.
  AddGlobalCDTimer's stored fields remain separate from CheckGlobalCDTimerAction's
  timer check and from live timer application. Every
  composition still needs all root fields,
  source-ID equality, physical EOF and the complete family/registry gates.
  The older icon contract cannot admit the changed generated record or pooled
  sprite path. Its raw priority-byte/padding transfer must remain distinct
  from the normalized Boolean helpers; proving those field components does
  not migrate the default formatter or enclosing Buff root.
- **LevelScript.** The gate rerun, first-stop leaders and route integration
  follow Buff in the queue;
  [`levelscript_first_stop_census.py`](../../scripts/game_data/levelscript_first_stop_census.py)
  reruns the owner over the JsonData receipt's partial files and ranks first
  stops by whole files. Unsupported values: positive
  `GameplayTag`/`BuffPtr`
  list elements, non-null `CameraControllerBase` and target-script values,
  non-constant patrol `EntityPtr`, unproved blackboard parent/owner joins,
  camera configurations and curve keys without reviewed parent routes;
  `SendLuaEvent2` is unobserved; partial templates stop
  at unreviewed unions.
- **SkillData.** Remaining framing failures involve unreviewed action parents
  or typed children, positive `EffectActionCfg` arrays and a remaining selector
  postprocessor. Use the current family report's first refusal to select the
  next shared reader. Separately, complete frames still need recursively named
  child evidence, including children omitted by the common top-level
  continuation receipt. A terminal proof cannot name an earlier interior.
- **Formatter and runtime.** Registration history and the outer
  provider/cache path are unjoined; provider selection, live formatter/cache
  contents and substitution are unobserved; the DamageUnit tag-list and
  `CheckSkillType` list providers stay conditional. Nested-union tags stay
  `structuralOnly` until their tables are walked, and each plan-only tag needs
  a whole-corpus adoption run. `Dictionary<string, object>` has no plan.
- **Tooling.** Dependency-scoped Skill replay needs a route registry and
  mutation tests before it leaves prototype. Unadmitted CharInteractPerform
  action tags and positive curve paths remain refused by its current reader;
  AnimationConfig's bulk-key proof is independent and does not admit those
  paths. Unity AnimationCurve has a separate formatter and key layout; keep
  their corpus observations and proof boundaries apart.

## Pooled string target boundary

LevelScript source replay binds a complete current reader snapshot, selected native
inputs, source spans and the matching exported StringPool before and after reading.
The shared cursor retains the owning route's exact wire plan for node strings;
declared-type annotations do not replace that plan. Plain replay loops share one
owner, while script-ID and domain checks remain in their validators. Direct legacy
EntityPtr and LevelScriptPtr helpers refuse. The current
`levelscript_script_ptr_param_native` component separately authenticates the
registered Param wrapper, raw sixteen-byte source, typed stores, factories,
getter and pooled tail. Its codec preserves the UInt64 script ID, signed Int32
stored level ID and four unnamed bytes. An empty pooled path stays empty;
zero does not infer current-script selection. Refill effects, live provider
selection, effective script resolution and enclosing owners remain separate.

LevelScript formatter regeneration can recognize an anonymous optimized clone
of `MemoryPackReaderExtensions.BeyondReadString` through the reviewed
`memorypack_pooled_string_reader_native.json` fact. The native code consumes
an Int32 pool index, returns empty/null for the two sentinels, and forwards
the remaining index to the shared pool lookup. This establishes a string-valued
read; it does not establish inline MemoryPack string wire compatibility or
admit a current corpus. The selected build and complete native windows must
match before the equivalence is used.
Enum Params with the same member count can have different constant widths.
Check the selected enum backing declaration and actual source helper before
choosing a codec; a stored byte enum preserves its bits and is not a Boolean. The reviewed byte-enum Param catalog has its own selected-native gate and cursor: one raw unsigned byte followed by the ordinary pooled Param tail. Its complete typed caller profiles preserve the low-byte argument, while the source proof rejects Boolean normalization, signed extension and wider reads. Regeneration chooses that explicit profile; the separate signed-Int32 catalog keeps its four-byte grammar. Neither component proof admits an enclosing owner or effective runtime value.
The same contract separately records conditional inlined sources for
`ParamKeyValue.key` and `ParamValueAtom.valueString`. Their validator checks
the actual pool/empty cells and lookup, buffered index/cursor paths, current
reader ABI, typed holder/field and unchanged result store. The last atom field
reuses the reader register only after consuming its index; it needs its own
profile. These source-site facts alone do not admit the enclosing OperaSegment
array, which has no maintained reader. Missing or mismatched selected inputs yield no field facts, and every
call rechecks the inputs after validation.
Native reference discovery must scan PE sections by their executable flag,
not by the `.text` name: generated formatter registration also lives in other
code sections. The mapper exposes section characteristics;
`il2cpp/native_cell_references.py` and `native_call_references.py` keep their
results as raw candidates requiring independent owned-instruction and typed
argument proofs. A `.text`-only empty search does not establish a missing
registration or justify a canonical-sharing fallback.
The sibling `memorypack_reader_clones_native.json` separates reference-return,
hidden-output16 and hidden-output40 reader clones. Complete owned caller programs,
registered generic equivalents and selected native bytes prove each equivalence;
the hidden40 profile also checks its outlined class-initialization helper and full
output zeroing. Caller equivalence does not prove the callee wire grammar, provider
selection or enclosing Param. Typed contexts and owning validators remain gates.
Native LevelScript consumers keep numeric tags in reviewed contracts: Python checks
their uint16 shape, while the selected switch, usage cell and exact wrapper prove
identity before publication. A previous build's rank is not a stable schema constant.
Source cursor headers use that authenticated tag and member count. Typed Param,
ParamOutput and nested-list contexts are re-derived before publication. The
current cutscene contract also proves appended preload storage and scalar setter
inlining through typed field ownership and non-null instruction flow.
Event hooks select the authenticated current union type before reading a route
contract; a stale discriminator must not intercept another event. Argument-flow
proofs reject unknown instructions and overwrites of saved reader/output pointers.
A direct reference-store proof ends at the typed store and does not establish
collector barrier equivalence or live reference visibility.
The shared [`raw ID Params`](../../scripts/game_data/contracts/levelscript_pod_id_param_native.json)
gate authenticates LsmPtr, SpawnerPtr and FunctionAreaPtr separately. Their
constants contain the named value's raw UInt64 id, followed by two signed
Int32 bindings and a pooled path. FunctionAreaPtr has an independently checked
initialization-before-header caller, typed ReadUnmanaged context, QWORD setter,
constructor and null branch. The compact WorldChallenge field joins the same
current raw read source; its proof alone does not admit the Param wrapper.
Stored zero is preserved as an id and establishes no default/current area,
resolved object, effective spawner/method or live provider selection.

Literal pooled string lists are a separate conditional
component bounded to the proved three-element profile; no list Param follows
from that proof. The module reader admits only the independently validated
Rolling/Launcher stored profile; other positive module tags remain refused.
The UID source contract separates actual setter calls from guarded direct
stores to native-owned base fields. Its inline profile uses the optional
initializer decoder and retains write-barrier/runtime effects as unresolved. Its
separate initialized cached-holder profile proves the selected buffered UID
prefix while leaving cold metadata/cache selection, allocation, collector
behavior and subsequent members independent.

`levelscript_node_strings_native.json` records independently proved UID prefixes:
full current declarations/counts, the exact two-reference reader ABI, ordered
Boolean/Int32/Boolean sources and the unchanged pooled result passed to the
typed UID setter. The codec matches the complete reviewed layout and admits
only the listed string field; another string or wrapper gains no permission.
Complete caller, primitive and setter windows remain selected-build evidence.
The bounded action-map prefix now reads the authenticated union header at its
actual cursor and stops before node fields. Inline UID scans and their old
single-CallServer owner shortcut are retired; generic sequential decoding owns
positive maps. Current-corpus admission and runtime ownership remain separate.
Unproved nested strings and Param tails refuse the old inline reader in the
shared node cursor; a parent declaration or matching native build cannot select
their child encoding. StringPool is explicit but unmeasured in byte coverage:
its page decoder needs filename context, and compressed bytes have no coverage
framer. Native validation shares only immutable declaration/exception indexes,
including pre-indexed unwind families. Public native and dependency gates still
run before and after validation; no successful gate status is cached there.
The camera look-at parent has an independent typed-route contract; every
nested parameter keeps its own native gate. Camera initial-state Params copy
the unmanaged managed-layout value, including padding, then two Int32 bindings
and a pooled path. The marshalled native size is a different representation
and must not choose the wire width. The dedicated child proof authenticates
both copy lanes, cursor advance, field offsets, null/allocation paths and the
selected generated formatter. Positive blend-curve constants and live camera
provider selection remain separate; a parent proof does not admit them.
The camera-state reference Param shares its complete parent proof with the
null-list lane. Its nested CameraControlState constant admits only the generated
null branch, followed by the pooled binding tail; positive state fields remain
unproved. Removal has its own current typed-route parent gate. Static wrapper
and formatter joins preserve the conditional generated-route boundary.
The graph blackboard has its own current pooled contract and shared sequence/
template codec. Keys and Atom strings are signed pool indices; the enum field
and Atom integer bits stay raw. Atom's wire record differs from its managed
stride, and its null formatter result becomes a zero/default value. Nullable
classes and collections remain distinct from empty values. Positive lists need
the selected native/Unity gate, typed contexts, static wrapper registration and
reviewed source windows. The provider comparison covers only the initialized
successful cache-hit path through the same type lookup, backend, context entry
and compatible-result check. Live provider/default selection and graph execution
remain unproved; these conditions do not admit another native route.

The separate `Param<List<BlackboardKVPair>>` child represents authored reference
class entries: pooled `key`, normalized Boolean `useString`, raw Float32
`valueFloat` and pooled `valueString`. Null Params, null lists and null entries
remain distinct from empty/default values. Its independently checked formatter
composition and each current typed parent gate are required; it does not reuse
the graph Atom representation. Stored entries establish neither current AI
blackboard values nor buff/bounty execution. Child or selected-node replay does
not establish an enclosing owner cursor, EOF or current corpus admission.

Getter-backed inlining rechecks the named instance getter, its complete owned
windows, typed field offset and unchanged return transfer. Its store remains
conditional on the getter result; cache coherence, exception equivalence and
reference write-barrier effects are not established by that proof.
Current scalar and Int64 Param loaders share immutable native byte indexes,
but rerun composition checks on each operation. Successful composition results
are not retained; source/native/Unity gates still surround the checked values.
Grouped single-Param routes authenticate a shared switch/helper map while
retaining each route's ordered reads, own setter and typed context. Conflicting
tables or helpers refuse the whole contract; source receipts stay historical.
Snapshot headers and `GetterInt` reuse the inherited-Param proof: all reader
calls and setter transfers are re-derived, including owned fragments and the
final typed context. Dispatch identities must agree across the switch, usage
record and wrapper; call instructions must fit wholly inside owned windows.
The environment-volume pointer's one-member wrapper alone does not establish
the raw UInt64 Param composition. The independent current child now proves its
actual scalar source, typed ABI, owned stores and pooled path. EnvironmentEnable
authenticates its selected parent branch, complete owned reader fragments,
ordered setters and typed contexts through its public validator. Replay forwards
the selected native root and matching export pool through independently gated
children. Historical inner spans remain hash-gated; live default/provider
selection and authenticated current whole-owner EOF remain separate.
Catalog-owned actions re-derive inherited identities, managed fields and typed
setter/read contexts before their owners validate the candidate. A whole-instance
read must name its class argument and actual instance setter separately from the
declared field setter; historical inner-record receipts do not establish a current
child grammar. FMV corpus joins use the canonical union header and require each
complete string parameter, including its tail, to fit inside the action receipt.
Native identity gates require agreement between actual bytes, recorded identity
and required kind; chained inequalities do not express that check. Shared failure
reports retain bounded expected/recorded/actual values and the source contract hash.
The current UTF-8 source contract uses separate
collection-header/advance helpers and span-based Encoding.GetString through get_UTF8.
Complete buffered header, caller, span-transfer and cursor programs are checked by
`il2cpp/string_source_programs.py`, including original local cold-path edges.
These conditional transfers require independent context and decoder joins;
names alone cannot admit a stored string.
`il2cpp/string_source_bindings.py` now authenticates the byte MethodSpec and its
registered call target without using placeholder open-generic field offsets.
Folded CreateSpan/CreateReadOnlySpan entries do not replace that context join.
The cache program checks typed allocation, one shared cache slot and initialization
equivalent to the named nonthrowing UTF8 constructor under normal-call conditions.
The pointer overload's count/allocation/fill/returned-String program is checked,
including null decoder-state arguments and preserved character capacity.
Its internal DecoderNLS method declarations match the physical function/MethodInfo
pairs through a checked generic virtual-slot prefix. Internal instruction, edge
and frame coverage does not prove the character algorithm or a live receiver's
vtable. The v2 contract admits only bounded null, empty and valid UTF-8 spans
at the standard Encoding API boundary, conditional on the checked initialized
UTF8Encoding receiver and normal callees. Character-algorithm reconstruction,
invalid-byte replacement and live execution remain outside that boundary.
`memorypack/utf8_source_contract.py` derives its methods, contexts and complete
unwind-owned windows afresh; the owning validator and before/after selected
native/Unity gates must pass before publication. A parent still needs its own
current source-call and field proof; historical receipts gain no current admission.
The optional `il2cpp/string_source_instructions.py` lane preserves memory-update
widths, source registers and flag effects and reuses the word-store reader.
Other control validators keep their narrower lane until their memory-effect
analysis independently supports these instructions.
The decoder-loop extension is separately optional: register TEST, byte CMP and
partial-word masks/subtraction retain their exact widths, flags and upper bits.


### Current SkillData capture filter binding

The current capture observer has an additional serialized member and an
unobserved generic-dispatch field, so the historical cursor/corpus publication
chain cannot be rebound by replacing hashes. The target-set contract v2 retains
the reviewed logical paths with freshly streamed current byte identities. Its
`comparisonFilter` names the former control path without asserting a current
positive-control result. No ambiguous-set membership or terminal choice is
claimed.

The existing `il2cpp.skill_cursor_target_set_context` command dispatches this
contract to `skill_cursor_filter_context`: it checks explicitly selected native
inputs, the current named observer declaration and helper call targets, outer
source/build fingerprints and MD5-verified exact selected VFS bytes. The result
is an observation-only filter binding with publication disabled. It exposes
the current unobserved members, and historical corpus and receipt validators
reject its separate context schema. Those strict gates and original observer
contracts remain unchanged for historical evidence replay. A failing full
outer audit is reported explicitly; selected available bytes do not establish
a complete VFS or SkillData corpus.


### Current ModelView stored graph

The [ModelView native contract](../../scripts/game_data/contracts/model_view_state_controller_native.json)
owns the current generated field order and actual `AbstractBehaviorData` union.
`MVSCBehaviorData` is an ordinary payload, so its name cannot identify the union
root. The transition setting includes `doNotInheritSameAnimationTime` before
`easeType`; historical same-width fields and tags must not retain old labels.

[The operation reader](../../scripts/game_data/model_view_state_controller_binary.py)
re-proves the selected native pair and Unity input on entry and exit. Its
[composition gate](../../scripts/game_data/memorypack/modelview_composition.py)
checks owned source programs, typed field/callback contexts, factories,
reference and value adapters, collection loops, cursor/output aliases and
normal returns. Complete raw reader sources, reviewed declarations, matching
StringPool pages and authenticated owning source bytes remain bookended.
A decoder capability closes with its lexical operation; successful semantic
proofs do not survive into a later operation.

Unity `AnimationCurve` uses its own formatter and key layout. It does not
delegate to Beyond `FAnimationCurve`, whose bulk-key evidence remains an
independent lane. Reference lists retain their current typed element context;
positive string elements separately prove the pooled string formatter and its
registration/backend path. The stored grammar is conditional on coherent
initialized contexts and matching normal helpers/receivers, fresh collection
storage, compatible callbacks and the disabled collector. Runtime default or
provider selection, generic-instance hashing/cache population, allocation and
constructor side effects, refill/growth and live runtime execution are not
established by the stored-frame proof.

The raw result retains `storedGraph` with native field names and physical EOF.
Audio projections copy their rows before adding owner labels, preserving the
underlying stored graph. Stored bank/control candidates do not establish an
Event, media link, sink call or effective runtime activation.

The current CallServer consumer claim independently re-proves the original
Execute reference copy from its metadata-owned output UID list to inherited
ActionBase wait-list storage. The current source gate owns pooled field
admission; a stored list and this copy do not establish ActionExecutor UID/header
lookup or OnCustomEvent successor dispatch. Until that distinct compiled
continuation is proved, Story retains the stored candidates with an explicit
pending native-consumer diagnostic and withholds callback/order edges. No
import-time or saved-report native success admits those edges.

FunctionArea radio links remain unresolved on the current build. The retired byte-pattern probe did not establish sequential owner boundaries, pooled fields or a current native consumer. Story emits an explicit nativeConsumerGaps entry and withholds these links until those joins are proved; this is no evidence of absent playback.

The current `Param<CameraControllerBase>` profile authenticates its own
reference-valued four-field parent, typed caller, eager key/adapter and pooled
Int32/Int32/string tail. Only a present Param carrying the nested null marker
is decoded. The selected canonical reference-adapter null branch returns a
null reference before child wrapper, getter or factory operations; the
abstract camera wrapper therefore supplies no positive object grammar.
Unsupported positive constants and whole-Param null forms refuse before
consumption in this bounded codec. Matching initialized pool and provider
contexts, compatible reference sharing and ordinary helper effects remain
conditions; this is stored data, not evaluated camera selection or execution.
