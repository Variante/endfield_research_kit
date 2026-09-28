# ExtendData source paths and facial-bone values

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Levels 2–4, catalog lane.** `StringPathHash.bin` and
`InitStringPathHash.bin` are source-path catalogs; `FacBoneTRS.bin` carries
facial-bone values; `CompressData.bin` carries authored behavior graphs. These
are catalog, animation, and AI graph data, not world placement.
The separate BundleManifest format is documented in
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

Every corpus gate below binds a targeted, MD5-verified dump of the selected
Persistent-overlay file to a full VFS audit ledger, and every native audit
checks the explicit selected `GameAssembly.dll`/`global-metadata.dat` pair;
each returns nothing on a mismatch. Each module's docstring holds the full
reading; the generated receipts go to `reports/animestudio/`.

## StringPathHash: a framed, stored path catalog

- **Framing (exact).** `scripts/game_data/extend_data_binary.py` consumes the
  current catalog through EOF: strict terminated UTF-16LE strings, distinct
  bucket record positions, and path offsets that each name a string start. The
  other bucket word and a four-byte gap before the string pool stay anonymous
  in both catalogs. The full inner gate also revalidates the initial catalog and
  FacBoneTRS against the same ledger, with exact EOF and source identity.
- **Hash route (direct, static).** `string_path_hash_native.py` authenticates
  the 64-bit `StringPathHash.hash` field and the construction/processor call
  routes: a `data/` prefix (ordinal, case-insensitive) reaches the method named
  `Beyond.Cryptor.Crc32Utils.XXHash64`, other paths an auto-lower UTF-16 wrapper
  with an authenticated managed fallback. It does not prove live execution,
  Burst dispatch for an unseen input, or the producer that wrote the file.
- **Replay (exact).** `string_path_hash_corpus.py` shows that every distinct
  `Data/` path/hash pair in either catalog equals the VFS ledger's
  independently recomputed filename hash, that the main catalog's remaining
  pairs equal the whole BundleManifest `AssetInfo` lowercased
  path/`pathHashHead` multiset, and that the initial catalog's asset pairs are a
  multiset subset of it. Repeated catalog pairs are kept rather than forced
  one-to-one with VFS rows, and every stored hash locates its slot by modulo the
  catalog's count. AnimeStudio's `EndfieldVfsHash.Hash64` takes its
  longer-input path at exactly 128 UTF-8 bytes, which is where standard XXH3
  disagrees; the gate keeps 127-, 128- and 129-byte controls.
- **Boundary.** This is a stored catalog naming Bundle, Streaming, JsonData,
  terrain and Unity asset paths. It is not an exhaustive runtime namespace, and
  its joins establish neither asset ownership nor runtime use.
- An older controlled `InitChunkData` scan found many aligned values that join
  this catalog while bit-flipped hash controls almost never did: authored asset
  references in those sampled chunks, without owner or runtime use, and without
  ruling out references under another encoding elsewhere in Streaming.

**Eliminated readings.** FNV, DJB2, SDBM, classic xxHash64, Murmur64A and
MurmurHash3 fail under their tested encodings and seeds; the method name
`XXHash64` does not mean classic xxHash64; the 128-byte branch explains the
earlier xxHash64 and XXH3 misses and is not evidence for a third stored hash.

**Next witness:** the catalog writer, or the concrete comparer passed to its
multi-hash-table initializer, to separate stored slot arithmetic from runtime
lookup behavior.

## FacBoneTRS

The `FacBoneTRS.bin` reader validates its file-provided counts, lookup and value
bounds, contiguous bone records, and 64-byte values through EOF. The values are
shape-consistent with row-vector homogeneous rigid-affine 4x4 float matrices;
the exact managed type, coordinate convention, and animation consumer are open.
No unit or bone hash equals a stored hash in either current path catalog; that
is a stored-hash equality check, not proof that no other naming route exists.
The cross-family framing boundary is in
[`extraction_payload_boundaries.md`](extraction_payload_boundaries.md).

## CompressData: authored behavior graphs

`CompressData.bin` has a strict reader in AnimeStudio (`EndfieldCompressData.cs`,
opt-in `extend-data` CLI command). Its records are length-prefixed exact Brotli
bodies of strict UTF-16LE JSON through EOF, and every current root is a
NodeCanvas behavior tree. The bytes establish authored graph structure with
typed nodes and connections, not a selected runtime branch or blackboard value.
Each link below is a separate gate under `scripts/game_data/`, with its reviewed
contract in `scripts/game_data/contracts/`:

| # | Link | Module | Tier |
| --- | --- | --- | --- |
| 1 | archive framing, decoder output closure pinned | `extend_data_compress_corpus.py` | exact |
| 2 | node types, field sets, `BTConnection` edges to unique node IDs | `extend_data_graph.py` | exact over the current corpus |
| 3 | every reached `_action`/`_condition` task's field set and value kinds | `extend_data_tasks.py` | exact shallow shape |
| 4 | `EnemySwitchBehavior.OnExecute` reads its `behavior` field | `extend_data_tasks_native.py` | direct, static |
| 5 | `DataCompressManager.Init` reads the archive; `Graph.DeserializeSelf` indexes it by `_serializedGraphStringIndex` | `extend_data_graph_native.py` | conditional, static |
| 6 | exported BehaviourTree MonoBehaviours name archive ordinals | `extend_data_graph_owner_corpus.py` | exact for the exported set |
| 7 | AssetBundle path to `EnemyAIConfigData.aiBB` to blackboard graph mode to `canvasGraph` to ordinal | `extend_data_graph_ai_corpus.py` | authored pointers |
| 8 | `SCENE_MONSTER.commonInfo.templateid` to enemy root to `EnemyTable.aiTemplateId` to `AIConfig` load | `extend_data_graph_ai_native.py` | conditional, static |
| 9 | each `SpawnMonsterFromTemplateV2.libraryKey` selects one `enemyLibrary[].key` in its file | `extend_data_spawner_library_corpus.py` | authored |
| 10 | server object ID to action to keyed library item, feeding an AI override and a born-data fallback | `extend_data_spawner_library_native.py` | conditional, static |

Conclusions that span the links:

- `EnemySwitchBehavior.behavior` is stored as an exact `tag.tagId` integer
  wrapper and read by the task's code; the integer's meaning, its writer, and
  any comparison are open.
- No decoded graph root carries an owner key. Ownership comes from the exported
  assets, several distinct assets share an ordinal, and every assignment is
  kept. Freshness rests on the export-summary fingerprint, not on per-object
  authentication of each Unity object's installed bytes.
- For a subset of `EnemyTable` rows, `aiTemplateId` equals a unique exported
  `EnemyAIConfigData.m_Name` whose natively formatted path is in the container,
  linking the Table key to a config and its graph mode. Configs under a
  `Settlement` subdirectory are outside this synchronous path, other Table keys
  have no exact path, and `AIConfig/EnemyTemplateDataSummary` maps template IDs
  to EnemyData paths without selecting a graph. The source graph's
  `enemy_uses_ai_config` edge is a query aid over the same field, not another
  witness.
- Every authored spawner `enemyId` is an `EnemyTable` key: an authored key join
  only. The runtime lookup keys items by `libraryKey`, and its AI branches read
  the item's `overrideAIConfig` (an override layer beside the default
  `aiTemplateId` route), `bornTemplateId` and `bornBehaviorData`, never its
  `enemyId`. In the current corpus, positive `bornTemplateId` values differ
  from the item's `enemyId`, and every `bornBehaviorData` is null.

None of these witnesses a live graph instance, protocol message, resource load,
or execution, and IFix can redirect every checked method. Asset names and graph
task strings do not fill that gap.

## Open join: spawner entry to live enemy

The default enemy identity reaches the AI through the protocol-derived
`EnemyServerData.enemyId`; the spawner lookup uses `libraryKey` and an entity
server ID. Nothing checked proves that a library item's `enemyId` becomes
`Proto.SCENE_MONSTER.commonInfo.templateid`. The message's separate
`monsterLibraryKey` (copied into `subgameLibraryKey`) is a candidate for the
selection join, but no selected client route compares it with an authored
action's `libraryKey`. Open: the protocol-message producer, its binding to a
particular spawner action and library item, selection into a particular
`EnemyInfo`/`EntityNode`, alternate constructors, async and override paths, and
a live override load. The next direct witness is a server producer or client
consumer that carries one selected library item into the monster message or
entity data with matching object and action identity; an ID intersection alone
cannot close it.
