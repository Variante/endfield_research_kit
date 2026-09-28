# ExtendData source paths and facial-bone values

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Levels 2–4, catalog lane.** `StringPathHash.bin` and
`InitStringPathHash.bin` are source-path catalogs; `FacBoneTRS.bin` carries
facial-bone values; `CompressData.bin` carries authored behavior graphs. These
are catalog, animation, and AI graph data, not world placement.
The separate BundleManifest format is documented in
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

## Current source-path boundary

A targeted, MD5-verified dump of the selected Persistent-overlay
`StringPathHash.bin` matches the current full VFS ledger. The maintained
`extend_data_binary.py` reader consumes its string pool through EOF: every
counted string is strict, terminated UTF-16LE, every bucket has a distinct
record position, and every stored path offset names a string start. The slot
and bucket regions have separately checked bounds. A four-byte gap immediately
before the string pool remains anonymous. The current count, length, source
hash, and gap position are in
`reports/animestudio/string_path_current_20260927.json`. The maintained full
inner gate also revalidated the selected initial catalog and FacBoneTRS
against the same current VFS ledger, with exact EOF and source identity for
all three payloads; its receipt is in
`reports/animestudio/extend_data_inner_20260927.json`.

This proves a framed stored path catalog, not an exhaustive runtime namespace.
Its strings name Bundle, Streaming, JsonData, terrain, and Unity asset paths.
The selected-build `string_path_hash_native.json` contract authenticates the
`StringPathHash.hash` 64-bit field and the construction/processor call routes.
Those routes test `data/` with `StringComparison.OrdinalIgnoreCase`: that
branch reaches the method named `Beyond.Cryptor.Crc32Utils.XXHash64`, while
the other branch reaches an auto-lower UTF-16 hash wrapper and its authenticated
managed fallback. The static route does not prove live execution, Burst
dispatch for an unseen input, or the producer that wrote this file.

The maintained `string_path_hash_corpus.py` gate binds either selected catalog
and BundleManifest to a full passing VFS ledger and separately authenticates
both native contracts. Every distinct current `Data/` path/hash pair in both
catalogs equals the VFS ledger's independently recomputed filename hash for
that exact path; the ledger distinguishes verified payloads from missing
optional audio or voice chunks whose metadata-only filename hashes still
match. The main catalog's remaining path/hash pairs, including repetitions,
equal the entire BundleManifest `AssetInfo` lowercased path/`pathHashHead`
multiset. The initial catalog's asset pairs are an exact multiset subset of
that same manifest. The BundleManifest native gate separately replays its
asset path hash through the auto-lower UTF-16 fallback.

The initial catalog repeats its own `Data/` path/hash pair, although the VFS
ledger carries one logical file row for that path. The gate retains this
catalog multiplicity and requires an independent keyed witness for every
distinct pair; it does not force a false one-to-one row count with the VFS.
All stored unsigned 64-bit hashes in both catalogs locate their slots by
modulo that catalog's count. These stored joins establish neither asset
ownership nor runtime use. The current native, main-catalog, and
initial-catalog receipts are in
`reports/animestudio/string_path_hash_native_20260927.json`,
`reports/animestudio/string_path_hash_corpus_20260927.json`, and
`reports/animestudio/init_string_path_hash_corpus_20260927.json`.

The VFS hash implementation in AnimeStudio's `EndfieldVfsHash.Hash64` uses
the longer-input path at exactly 128 UTF-8 bytes. A disposable standard
XXH3-64 comparison matches all other current `Data/` rows but differs at
the 128-byte boundary; those rows still match the VFS ledger exactly.
The main-catalog gate includes 127-, 128-, and 129-byte controls. This boundary
explains why the earlier common xxHash64 and standard XXH3 probes did not
replay the entire main catalog. It is not evidence for a third stored hash.
The other bucket word and the four-byte pre-string gap remain anonymous in
both catalogs.

An older controlled `InitChunkData` scan found many aligned values that joined
this path catalog, while bit-flipped hash controls almost never joined. The
result supports authored asset references in those sampled Init chunks. It
does not establish the owner or runtime use of each reference, nor prove that
other Streaming records cannot carry references under another encoding.

Earlier FNV, DJB2, SDBM, classic xxHash64, Murmur64A, and MurmurHash3
candidate tests remain negatives under their tested encodings and seeds;
the selected method name `XXHash64` does not mean classic xxHash64. The
next useful native witness is the catalog writer or the concrete comparer
passed into its multi-hash-table initializer, to distinguish stored slot
arithmetic from runtime lookup behavior.

## FacBoneTRS and CompressData

The `FacBoneTRS.bin` reader validates its file-provided counts, lookup and
value bounds, contiguous bone records, and 64-byte values through EOF. The
values are shape-consistent with row-vector homogeneous rigid-affine 4x4
float matrices; exact managed type, coordinate convention, and animation
consumer remain open. A fresh selected-input comparison found no exact
unit/bone hash match in either current path catalog; this is a stored-hash
equality check, not a proof that no other naming route exists. The changing
counts are in `reports/animestudio/facbone_catalog_join_20260927.json`. The
cross-family framing and evidence boundary are recorded in
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

`CompressData.bin` already has a maintained strict reader in AnimeStudio's
`EndfieldCompressData.cs` and an opt-in `extend-data` CLI command. A targeted
MD5-verified dump of the selected main file matches the current full VFS
ledger. The current `extend_data_compress_corpus.py` gate binds that source and
the audited CLI apphost to the same input set, pins the complete compiled
decoder output closure through `extend_data_compress_reader.json`, then reconciles
the decoder manifest with the complete absolute-offset table. Each record
has two little-endian lengths and an exact Brotli body that decodes as strict
UTF-16LE JSON; the last record reaches EOF. All current root objects identify
NodeCanvas behavior trees. The source identity, framing totals, root-type
inventory, and decoder receipt are in
`reports/animestudio/extend_data_compress_20260927.json`.

These bytes establish authored graph structure, including typed nodes and
connections, but no selected runtime branch or blackboard value. The selected
native route in `extend_data_graph_native.json`, checked by
`extend_data_graph_native.py`, connects the exact archive path to
`DataCompressManager.Init` and its VFS stream read. The selected metadata
also identifies `BehaviourTree` as a subclass of `Graph`. On the unpatched
branch, `Graph.DeserializeSelf` tests the compression flag, passes its stored
integer `_serializedGraphStringIndex` to `GetUnSafeString`, and deserializes the
decompressed string. The checked span reader uses that index in the archive's
offset table and the selected code calls Brotli. This is a conditional static
consumer route: the manager must be initialized and compression enabled, and
IFix can redirect methods. It does not witness a live graph instance or
execution. The selected-build native receipt is in
`reports/animestudio/extend_data_graph_native_20260927.json`.

The reviewed decoded-graph contract is
`scripts/game_data/contracts/extend_data_graph_schema.json`, enforced by
`extend_data_graph.py` during the current CompressData corpus gate. It closes
the named NodeCanvas root, the observed node-type/field-set combinations,
`BTConnection` source/target `$ref` objects, and every edge's reference to a
unique present node ID. Nodes without `$id` remain stored but cannot be edge
targets. Canvas metadata and dynamic blackboard values remain opaque; a node
type name does not establish execution. The generated current inventory and
failed-shape boundary are in the corpus report.

The separate `extend_data_task_envelopes.json` contract, enforced by
`extend_data_tasks.py` in the same gate, now follows each node's `_action` and
`_condition` task plus typed children in `ActionList.actions` and
`ConditionList.conditions`. It closes exact field sets and JSON value kinds
for every task type reached in the current authenticated corpus; an unknown
task type, new field set or kind, and new typed-child list are rejected.
Nested object/list values outside the declared wrappers remain opaque. In every reached
`EnemySwitchBehavior` task, the stored `behavior` value has the exact
`tag.tagId` integer wrapper. The current type/shape coverage and tag-ID
inventory are in `reports/animestudio/extend_data_compress_20260927.json`;
the full shallow-envelope coverage, absent mixed kinds/additional typed lists,
and mutation rejections are in
`reports/animestudio/extend_data_task_envelope_coverage_20260927.json`.
Neither the integer's meaning nor dynamic blackboard contents is established.

An independent selected-build native check in `extend_data_tasks_native.py`
authenticates `extend_data_tasks_native.json`: the matching
`EnemySwitchBehavior` type declares a `behavior` field and its checked
`OnExecute` body reads that field from its instance. This is a direct static
field read, not a witnessed execution or a join from one decoded archive task
to a runtime instance. The current native receipt is in
`reports/animestudio/extend_data_tasks_native_20260927.json`; the stored tag's
writer, comparison, and behavior semantics remain open.

No decoded graph root carries a separate owner key. The reviewed
`extend_data_graph_owner.json` contract and
`extend_data_graph_owner_corpus.py` instead join exported
`NodeCanvas.BehaviourTrees.BehaviourTree` MonoBehaviour objects to archive
ordinals through their `_serializedGraphStringIndex`. The gate checks the
MonoScript identity and object script pointer, source CAB and PathID, enabled
compression flag, empty inline graph, document hash, full ordinal coverage,
and the current VFS and selected native route. Several distinct authored
assets share an ordinal; the report retains each source-CAB/PathID-to-ordinal
assignment rather than forcing one-to-one ownership. An inline `CanvasGraph`
with compression disabled is excluded despite its incidental index. Index
kind/range and script-pointer mutations are rejected. This closes authored
asset ownership for the current exported set under the maintained freshness
guard. The export predates per-output provenance, so that guard relies on the
export summary's source fingerprints rather than an independent current-byte
authentication of each Unity object. The current map and freshness basis are
in `reports/animestudio/extend_data_graph_owner_20260927.json`.

The separate reviewed `extend_data_graph_ai.json` contract and
`extend_data_graph_ai_corpus.py` gate add an authored AI-config link. Within
each graph source CAB, its exported AssetBundle `m_Container` gives the exact
path and local PathID for every compressed BehaviourTree asset; this is a
stored pointer, not a filename guess. An `EnemyAIConfigData.aiBB` PPtr then
names an `EnemyAIBlackboard` in the same CAB. Each checked blackboard graph
mode maps a stored tag to a managed-reference RID, whose exactly decoded
`canvasGraph` PPtr names a BehaviourTree source CAB and PathID. The gate
requires the exporter-resolved PPtr receipt, the unique target object, and
the existing archive ordinal map at every step. It preserves null graph
pointers and uninterpreted modes separately. Mutated RIDs, graph pointers,
and managed-reference decode status are rejected. The current path map,
authored graph-mode links, and exclusions are in
`reports/animestudio/extend_data_graph_ai_20260927.json`.

For a subset of current `EnemyTable` rows, `aiTemplateId` equals a unique
exported `EnemyAIConfigData.m_Name`, connecting that stored table key to the
AI-config object and its checked graph mode. The selected-build
`extend_data_graph_ai_native.json` contract, checked by
`extend_data_graph_ai_native.py`, supplies an independent static consumer
route. `EntityDataStorage.CreateEnemyFromServer` takes a
`Proto.SCENE_MONSTER` and passes that same message to
`EnemyInfo.InitFromServerData`. The initializer reads
`SCENE_MONSTER.commonInfo.templateid` for a keyed `EnemyTable` lookup,
obtaining `EnemyData.templateId` for template setup. It also passes the
message to the `EnemyServerData` constructor, which copies the same
`templateid` into `EnemyServerData.enemyId` and stores that object as
`BaseEntityData.serverData`. This identifies a direct producer and a second,
independent Table-key use of the protocol field.

The checked `EntityNode._SpawnEntity` path reads its
`BaseEntityData.serverData`, passes it as a typed argument through
`ObjectContainer.SpawnEntity` and `LoadEntity`, and stores it in
`Entity.serverData` through `Entity.AssignServerData`. On the separate
checked `EnemyRootComponent.InitSelf` path, an `EnemyServerData` cast copies
its `enemyId` from `Entity.serverData` into the enemy-root field. On the
unpatched synchronous `EnemyAIComponent` initialization path, the code reads
its inherited `BaseComponent.entity`, then `Entity.enemy`, then
`EnemyRootComponent.enemyId` as the key for `Tables.s_enemyTable`. The
table map's value type is `EnemyData`; a successful lookup yields a bean.
It reads bean string slot zero, the same selector used by
`EnemyData.get_aiTemplateId`, formats an `AIConfig` asset path from that
string, and passes the path to `LoadSingleConfig`. The return is stored in a
field declared `EnemyAIConfigData`. The static chain is conditional on
selecting the initialized `EnemyInfo` into the checked `EntityNode` spawn
path, the cast, lookup, and nonempty AI field. It does not witness a live
message, resource load, or graph instance. IFix can redirect the methods.

The authored gate requires each current `EnemyTable` row key to equal its
stored `enemyId`. It also requires each Table-key match to have the case-folded
native-formatted path in the exported AssetBundle container before reporting
its `EnemyAIConfigData` and graph ordinal. The current matched subset closes;
other exported AI configs under a `Settlement` subdirectory are outside this
synchronous path. The source graph's `enemy_uses_ai_config` edge is a query
aid over the same Table field, not another raw witness. Other Table keys
remain unmatched by exact path. The targeted
`AIConfig/EnemyTemplateDataSummary` file maps enemy-template IDs to EnemyData
asset paths but does not select a graph. The native report is in
`reports/animestudio/extend_data_graph_ai_native_20260927.json`; the authored
report records path matches, graph joins, and rejected path mutations.

The gate requires fresh Table and Unity outputs under the export-summary
fingerprint fallback; it does not authenticate each Unity object's current
installed bytes. The source and selection of a live `SCENE_MONSTER` message,
its relation to installed spawn or scene records, selection of a constructed
`EnemyInfo` into a particular `EntityNode`, alternate constructors, async
and override paths, live graph instance, and execution remain open. Asset
names and graph task strings do not fill those gaps.

A targeted current VFS-ledger-to-export check authenticates the stored
`SpawnerConfig` logical files by exact path, length, and plaintext MD5.
Their existing named MemoryPack prefix reader exposes
`enemyLibrary[].enemyId`; every distinct current authored ID equals an
`EnemyTable` key, and some also occur in the graph-linked AI subset. This is
an authored key join only. The maintained
`extend_data_spawner_library_corpus.py` gate now also requires current
JsonData export freshness, rechecks every SpawnerConfig logical file against
the current VFS ledger, and decodes the wave, group, and action maps
sequentially to physical EOF. Every decoded
`SpawnMonsterFromTemplateV2.libraryKey` selects exactly one
`enemyLibrary[].key` in the same file, yielding that action's authored
`enemyId` and optional `overrideAIConfig`. This closes the current authored
action-to-library relation, while other action union tags retain the reader's
bounded status. The generated per-action joins and source basis are in
`reports/animestudio/extend_data_spawner_library_20260927.json`.
Neither those bytes nor the source graph builder's
authored spawner-enemy rule defines a conversion to
`SCENE_MONSTER.commonInfo.templateid` or selects a particular
`EnemyInfo`/`EntityNode`. The first missing witness is the producer or
consumer that carries one stored spawner entry's ID into a selected protocol
message or entity-data node. The scoped byte/ID inventory and the current
source-graph availability check are in
`reports/animestudio/extend_data_spawn_identity_20260927.json`.

The selected native `extend_data_spawner_library_native.json` contract and
`extend_data_spawner_library_native.py` audit close a different, runtime-facing
part of that join. `SpawnerConfigData.get_enemyLibraryDict` enumerates
`enemyLibrary` and inserts each item under its `key` field, separately from
`enemyId`. The checked `GameplayNetwork._Handle_EnemySpawnerObjectEnd` path
copies `SC_SCENE_MONSTER_SPAWNER_OBJECT_DATA_END.details[]` object, action,
and spawn indexes into `SpawnDataDetail` records. Its call to
`SpawnerManager.OnEnemySpawnerObjectEnd` passes those records to
`SpawnerRuntime.SetupSpawnData` and installs the record's server object ID to
action ID mapping in `m_entityId2ActionIdDict`. This is a static client
consumer of a server message, not a captured message.
`SpawnerManager.TryGetLibraryItem` uses an entity's server ID to
find its spawner action, reads that action's `SpawnMonsterFromTemplateV2.libraryKey`,
and selects an item from the config's key-indexed dictionary. On the checked
unpatched synchronous path, `EnemyAIComponent._InitSync` supplies its entity's
server ID and the enemy root's parent spawner to that lookup. A selected item
with nonempty `overrideAIConfig` can cause a distinct
`AIConfig/Override/{name}.asset` load and a typed
`EnemyAIRuntimeCfg.SetOverrideData(EnemyAIConfigDataOverride)` call. This is an
override layer beside the default `EnemyTable.aiTemplateId` to
`EnemyAIConfigData` route above; it does not itself select a base graph. The
same audit independently checks the `EnemyServerData` message constructor:
it copies `SCENE_MONSTER.commonInfo.templateid` into its `enemyId` and the
separate `SCENE_MONSTER.monsterLibraryKey` into its `subgameLibraryKey`. That
protocol library key is a candidate for an eventual spawner selection join,
but the selected client route does not compare it with the authored action's
`libraryKey`. The audit checks installed native hashes, metadata field
identities, exact code windows, decisive instructions, call targets, and the
path literal. It returns no route when those inputs differ. Its selected-build
receipt is in
`reports/animestudio/extend_data_spawner_library_native_20260927.json`.

The same selected native gate also checks the AI born-data fallback.
`EnemyAIComponent.TryGetRuntimeBornData` first allows entity-provided born
data; when that is absent, its `_TryGetSpawnerLibraryItem` branch reaches the
same keyed spawner lookup and copies the selected item's `bornTemplateId` and
`bornBehaviorData` as separate outputs. Synchronous AI initialization calls
that method and separately asks for resolved born behavior data. The current
authenticated authored corpus has positive `bornTemplateId` strings selected
by monster actions, while every stored `bornBehaviorData` member is null. In
those positive items, `bornTemplateId` differs from the item's `enemyId`.
The checked born-data fallback reads `bornTemplateId` and `bornBehaviorData`;
it does not copy the item's `enemyId`. The source counts and per-action joins
are in the updated
`reports/animestudio/extend_data_spawner_library_20260927.json`. This remains
a static, conditional client path; it does not show a live AI initialization.

The runtime lookup uses `libraryKey` and a selected entity server ID; the
checked AI branches read item override and born-data fields while the default
enemy identity comes through the protocol-derived enemy-root field. Neither
those native paths nor the authenticated authored `enemyId` inventory proves
that the item's `enemyId` becomes
`Proto.SCENE_MONSTER.commonInfo.templateid`. The protocol-message producer,
its binding to a particular spawner action and library item, selection into a
particular `EnemyInfo`/`EntityNode`, and live override load remain open. The
next direct witness is a server producer or client consumer that carries the
same selected library item into the monster message or entity data, with
matching object and action identity; an ID intersection alone cannot close it.
