# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.

## Why this file remains

The WebUI page guides explain how recovered data is published. This file is
still required because many evidence contracts are shared by several pages or
exist before any page projection: overlay behavior, binary framing, native
build gates, runtime/static distinctions, and cross-domain graph provenance.

## Refresh and evidence rules

```bat
python scripts\verify_export_freshness.py
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

- StreamingAssets is the fallback; Persistent is the active overlay. Changed
  logical paths replace their fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version, and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses, and full inventories belong
  in reports or versioned code contracts.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. Maintained readers cover Unity bundles and AssetMaps, structured
Tables and JsonData, video, audio, Terrain, Streaming/DynamicStreaming, selected
ExtendData families, and native-gated contracts. A verified outer VFS boundary
proves byte identity and availability, not the inner payload schema.

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` remain visible and must not be upgraded by a later name match.
- Runtime-mutable properties preserve their authored initializer but cannot be
  treated as final action targets without excluding later writes.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## VFS-native payload families

The maintained evidence index in the AnimeStudio workflow routes each family to
its reader, fixtures, and generated corpus report. Durable current conclusions:

- DynamicStreaming is a generated FlatBuffers family with validated version,
  grid, string, resource/state, and area accessors. The deeper meaning of its
  DataMask and several record fields remains unresolved.
- StreamingChunkInfo has an exact anonymous EOF graph and slot partitions
  derived from actual vtable positions. Standard rows provide one inline
  eight-byte pair and a counted vector of eight-byte pairs. Their anonymous
  four-word projections uniquely match the same-directory secondary-file
  catalog among all permutations; duplicate multiplicity, missing paths and
  ambiguity are not discarded. Legacy three-field roots retain exact framing
  but are unsupported by this catalog projection. A separate native gate
  connects Info pairs through shared owner state, complete normal-container
  pair equality (including collision paths and custom register liveness),
  reviewed direct insertion guards, and unchanged key assembly to paired path
  formatters. This proves conditional static value provenance, not all possible
  active-set mutations, a concrete runtime Info instance or spatial meaning.
  See `layer3.infoCatalogRelation` and `layer4.infoKeyProducerStaticChain` in
  the Streaming corpus report; inventories and candidate comparisons live there.
- Init/Streaming have three exact anonymous subgraphs, not whole-file
  understanding: root-field2 through decoded EOF, parallel root-fields3/4/5,
  and paired root-fields6/7. Init field2 is empty; Streaming field2 rows have
  exact table/vtable layouts followed immediately by counted scalar32 vectors.
  Slot spans for present fields0--5 are 4/4/4/8/24/4 bytes without padding.
  Three-image native gates establish scalar32, int32[2], float32[6] and
  scalar32-key-vector representations; field names and key namespace/signedness
  remain unresolved. Numeric/Global filename relations are structural, not
  coordinate or gameplay names. Managed GridData names are candidates only.
  Parallel directories use equal-count width4/1/4 vectors. Their row-field0
  remains string/byte-vector ambiguous. Applicable row-field5 vectors are
  empty (nonempty fails closed); row-field3 reaches another parallel directory.
  Nested marker17 bounds two wrappers and a counted opaque byte range. Its
  maintained table-local directory retains each key, marker, raw selector,
  serialized ordinal and decoded wrapper/count range with logical-file
  provenance. Duplicate keys remain ambiguous across all markers in the table;
  absent selectors are not defaulted to zero. Directory counts reconcile with
  framing counts; failed gates suppress directory publication. This adds no
  owned bytes and does not name the opaque bodies or prove runtime selection.
  The separate marker17 body parser refines selected default slot3 tag5 bodies
  into a 64-byte anonymous header, one optional record and five counted arrays.
  Native-gated pointer arithmetic fixes their order and widths; counts are
  bounded before multiplication and the parser enforces exact body EOF.
  Header gaps and record fields remain opaque. Native construction, callback
  installation and publication are pinned separately from concrete execution;
  the native reader itself checks neither source extent nor final cursor.
  Its external-array equality remains conditional on an unavailable carrier.
  The remaining selected profiles independently bind tags1/4/6 to their keys.
  Their strict fixed lengths match reviewed maximum read ends and are tested
  against authenticated bodies, not inferred as native EOF checks. Bytes30--31
  are explicitly unread/opaque, not certified padding. Equal lengths do not
  imply equal tags: the tag6 profile must not be dispatched as tag1.
  The separate marker13 profile joins explicit raw selector9/root marker2 and
  unique full key FF000000 to two independently pinned default consumers.
  Its physical gap starts at a certified structural end and finishes at the
  next certified start; other anonymous target addresses do not define either
  boundary. The finite physical-gap profile accepts only 16 or 18 bytes; this
  end need not equal the native 16-byte read end. Four anonymous
  scalar32 positions are consumed conditionally; remaining gap bytes stay opaque
  with unresolved ownership, even when zero. Serialized sizeof, field meanings and
  native final cursor remain unknown; absent selectors and longer gaps are not
  silently defaulted or treated as padding. The corpus gate inventories the
  independently certified ranges, selected read windows and opaque complement,
  keeping physical-gap lengths separate from read-window byte counts.
  For absent selectors, the parser rechecks the actual row/vtable field2 and
  preserves null. A separate pinned slot5 accessor-default-zero witness is
  conditional on a new key and default registration, not a serialized value.
  The pair validator binds both file identities, complete ordered field3/4
  vectors and the same bounded ordinal, then rechecks the marker byte and row
  uoffset. Only a complete source-reconciled corpus terminal permits publication;
  existing-key history, overrides and runtime receipt remain unresolved.
  Marker16 belongs to a different outer-row shape. These associations do not
  prove a union registry. Marker15 references require nonzero forward bounded
  targets; hashes bind each source/slot directory, but target contents and
  record extent remain opaque, with zero additional owned target bytes.
  The reviewed default selector's initial callback is a false stub. Its later
  callback uses the second root's row-field3 for one scoped context. Full-u32
  key equality, collision probing, insertion/rehash and lookup are native-gated.
  Native duplicates retain the first ordinal; serialized joins instead reject
  ambiguity. Unique element keys yield bounded marker15 sixteen-byte candidate
  reads, with known-range overlap checks.
  Missing count keys remain explicit unsupported rows; readable spans are not
  record extents or execution receipts.
  The marker2 finite-gap parser selects only the independently gated
  selector6/full-key09020000 context. It rebuilds the complete nested target
  directory; unknown markers preserve raw slots and prevent occupancy closure.
  An exclusive target must start at the preceding certified end and have a
  4- or 6-byte gap to the next certified range. Only four bytes are projected;
  the extra two remain opaque, even when zero. All u32 bit patterns are accepted
  structurally. Native signed-positive loop use does not establish serialized
  validity, a semantic count name or sizeof. Multi-target clusters remain
  unsupported, aliases stay ambiguous, and unseen exclusive gap lengths fail.
  Selector9 remains unsupported: its prefix writes into returned component
  storage, but the live mapping index, record index and resulting pool span
  are not bounded by the reviewed accessors. Constructor allocations alone
  do not prove current backing ownership. A presumed valid runtime object
  must not substitute for this missing carrier/extent evidence.
  Paired formatters prove first=Init and second=Streaming with identical
  root/dev/key inputs; both use one serialized ordinal, not runtime allocation
  order. Complete ordered field3/field4 witnesses match between paired files,
  while row-field0 differs and is not shared identity. New runtime keys use
  Init's marker; existing keys reuse an already stored marker. Live key-map
  state, overrides, scheduling and execution are not established by these bytes.
  The family-level native reader closes requested/returned length, exact-read
  success, first leaf StreamingChunkInfo and base-relative root resolution.
  Its post-I/O closure is pointer-only: no parsed length/final cursor reaches
  the accessors. Static owner/handle/secondary-root chains do not supply a
  concrete runtime-root or scheduler-to-Create receipt.
  Details and per-file witnesses belong to `streaming_root_subgraphs_latest`
  under `reports/animestudio/`; the native contract is
  `scripts/game_data/streaming_field2_native.json`. Candidate marker15 native
  reads remain in `reports/animestudio/streaming_marker15_native_latest.json`.
- Terrain accepts the observed raw or length-prefixed inverted-LZ4 envelope and
  TRET versioned prefix. `_H` records close as row-major little-endian height
  samples; adjacent cells establish grid orientation. For the selected build,
  the hash-gated UnityPlayer reader directly consumes decoded offset 14 as
  `GraphicsFormat`, checks offset 16 against its allocated texture byte size,
  and copies from offset 20. Current metadata and the native footprint table
  establish 108/109 as BC7 sRGB/UNorm, 16 bytes per 4x4 block, so all observed
  Terrain bodies now have exact anonymous EOF-consuming ranges. Absolute
  height scale, no-data semantics, compressed-block channel meanings, D/N
  ownership, texture-array slots, and selected runtime rendering remain
  unresolved.
- `ExtendData/Main/CompressData.bin` is an absolute-offset archive of Brotli
  records whose decoded bodies are strict UTF-16LE JSON. Current bodies contain
  NodeCanvas behavior graphs. This proves authored graph structure, not selected
  runtime branches or blackboard values.
- String/path hash, facial-bone TRS, and manifest files have separate mmap or
  native consumers. Their member names guide bounded parsers but do not prove
  complete byte layouts.
- LipSync JsonData has an exact selected-build MemoryPack layout. Its float rows
  are native-proven Unity keyframe values. LipSync animation data remains
  distinct from language voice-audio availability.
- Video has exact outer framing for the maintained corpus; codec/container
  validity does not prove narrative attachment or playback.

Changing sizes and totals live in `reports/animestudio/`, not here.

## Gameplay semantics

Gameplay recovery joins authored Tables, exact binary/serialized structures,
selected native enum contracts, Assets, Audio, and the curated graph.

- Enemy variants resolve their exact attribute template before stats are shown.
- Authored level points, cooldowns, modifiers, formulas, and Buff actions are
  preserved as source values. Final runtime values across other Buffs, IFix,
  equipment, and server state remain uncomputed.
- Action/condition unions publish only the typed prefix or body that consumes
  exactly. Unknown selectors, enums, tags, blackboard operations, and nested
  payloads stay unresolved.
- Current-build native Buff action routes contradict the legacy reader's tag/name
  map. Exact byte consumption alone does not validate those names for current
  data. Selected token/module, switch-table and registered-type joins are recorded
  in `reports/animestudio/il2cpp_context_current_latest.*`; they establish wrapper
  identity, not nested field order or record extent. Do not alias unfamiliar tags
  to old parsers or assume a uniform renumbering; current consumer evidence is
  required before promoting legacy labels.
  Selected IfElse paths overwrite the callsite companion in native thunks;
  their common wrapper type argument does not determine the live formatter.
  Reuse reaches state-dependent provider dispatch with the same reader/output,
  not a direct field reader. The independently token/module-joined IfElse reader
  proves a member-eight fast path with a 14-byte anonymous scalar prefix followed
  by three calls carrying the same SequenceActionData type argument. This proves
  selected-consumer order, not live provider selection, nested extents or EOF;
  byte-to-boolean normalization must not be mistaken for a strict 0/1 encoding.
  `memorypack.buff_actions` now frames the anonymous first collection forward
  from byte zero under each retained filename-anchor candidate's hard limit.
  It supports the current IfElse/Sequence grammar, the selected member-five
  child profile, nulls and bounded counts,
  records completed nested spans, and stops at the first unsupported union.
  Atomic spans plus an explicit physical-file remainder tile the bytes; that
  remainder is opaque, not a decoded record. `buff_corpus` publishes a separate
  prefix success/failure/unsupported/ambiguity denominator and fails its gate
  on malformed prefixes even when the legacy suffix reader succeeds. Current
  Sequence consumer evidence places the counted indirect child array before
  two nonzero-normalized bytes; child output-slot width does not bound payloads.
  The member-five child closes a 13-byte anonymous scalar prefix followed by
  a counted member-three record collection. Each record contains two signed-
  length-prefixed byte spans separated by one nonzero-normalized byte. The
  selected native wrapper's type argument independently joins a List of
  BlackboardString; its element reader confirms that order and byte-length
  advancement. This is a structural-only profile, not proof of live generic
  formatter selection, decoder parity, field names or gameplay conditions.
  Null and empty byte spans remain distinct; negative lengths below -1 fail
  closed, and no standard MemoryPack UTF-16/negative-length variant is guessed.
  The selected member-ten action now closes forward through anonymous member-13,
  member-8 and member-3 nested profiles, then a byte, length-prefixed bytes,
  scalar32 and a member-three scalar payload. Independent native read order
  supports these boundaries; raw zero DWORDs in the action prefix are not a
  nested object or collection count. The member-eighteen action expands the
  finite selector profiles through concrete finder, validator and postprocessor
  readers pinned in `scripts/game_data/buff_b2_native.json`. Counted shape,
  validator, postprocessor and selection elements retain their own headers.
  A vector contains three variable-width scalar payloads, not twelve raw bytes.
  List count/null/loop framing remains conditional on the shared reference-list
  consumer; a provider bridge alone proves neither width nor runtime selection.
  Direction targets remain null-only; a postprocessor may expand one target,
  with a second non-null instance stopped before its header. Unknown nested
  tags stop in place without scanning for a later marker. The final
  payload reader consumes four scalar bytes despite its managed Double name.
  Keep those bits anonymous, including non-finite values. Byte decoding, live
  provider selection and whole-BuffData EOF remain unresolved; selected native
  pins and read order are owned by `scripts/game_data/buff_ec_native.json`.
  The selected member-seven child reuses that scalar-payload profile twice,
  after one byte and four scalar32 reads. The fourth scalar is serialized
  before both nested records despite its later destination-object offset;
  memory layout must not substitute for consumer order. Its selected native
  contract is `scripts/game_data/buff_50_native.json`; the two identical static
  type arguments do not certify live formatter selection or comparison meaning.
  Extended unions consume FA followed by a little-endian unsigned tag; record
  reports retain that decoded tag rather than the escape byte. Unknown tags
  stop at the original start. The selected extended member-eight child reads
  one byte, three scalar32 values, paired payload, scalar payload, one byte and
  paired payload. Its normal reader crosses chained unwind regions: the first
  `.pdata` end is not a record or function end. The selected read/null paths
  live in `scripts/game_data/buff_11f_native.json`; names and runtime use remain
  unresolved independently of this structural closure. Paired and scalar
  payloads can have identical extents; select their profiles from independent
  nested-consumer evidence, not byte length alone.
  The selected member-thirteen child closes three target profiles, a finder
  profile and a scalar payload in native read order. The finder contains a
  counted byte-payload list, scalar32 and a member-two query whose selected
  array helper consumes count times four bytes. Keep all values anonymous.
  `scripts/game_data/buff_b4_native.json` owns the native contract, including
  an explicit limitation: List<string> has a static type join but no separate
  formatter MethodSpec; the shared List<Object> count/loop and String element
  reader support a finite structural profile, not actual provider selection.
  Related member-eight children have a byte payload, counted nested records,
  scalar32 and the same query profile after their common scalar prefix.
  `scripts/game_data/buff_56_native.json` pins the member-one value-type list;
  `scripts/game_data/buff_57_native.json` joins a reference-type list whose
  member-three elements contain two byte payloads separated by a byte.
  Equal outer member counts do not imply equal element layouts. Each element
  consumes its own header; a managed name or output-slot width cannot replace
  the concrete nested reader. The reference-list loop remains conditional on
  the shared consumer, and active formatter selection stays open for both.
  A member-six child contains only a byte, four scalar32 values and scalar64.
  Its final helper reads and advances eight source bytes; that cursor evidence,
  pinned in `scripts/game_data/buff_5b_native.json`, establishes wire width.
  Preserve the raw bits: a mask-like managed name does not prove flag meanings.
  Another member-ten child reads the common byte/three-scalar prefix, finder,
  scalar32, target, scalar32, byte and scalar payload. Its three static type
  contexts reuse the existing finder/target/scalar readers; equal outer member
  counts do not select a layout. `scripts/game_data/buff_3c_native.json` pins
  that distinct order through normal return and the separate null path.
  Intermediate setters do not establish wire order or gameplay conditions.
  The member-nine child adds a scalar, two bytes, target and counted scalar32
  list after the common prefix. `scripts/game_data/buff_78_native.json` joins
  the list element to a separate concrete source consumer that advances four
  bytes. Its count/null/loop profile remains conditional on the shared list
  reader: the element-width witness does not prove actual provider selection.
  Preserve unknown enum values as raw bits; managed enum size is not the witness.
  The member-nineteen child adds counted input profiles containing counted
  assignment profiles, a scalar/byte-payload pair, and the existing scalar,
  byte-payload-list and target profiles. Preserve the native read order rather
  than destination offsets: helper calls also consume scalar and byte members.
  `scripts/game_data/buff_92_native.json` pins these readers, nested contexts,
  the assignment-list candidate and the selector finder's zero-member route.
  Shared reference-list and provider dispatch remain conditional; a concrete
  static reader is structural evidence, not proof of live formatter execution.
  Next close the most frequent unsupported child consumers before extending
  this grammar; do not import legacy tag/name aliases to improve coverage.
- Gameplay tag names come from exact predefined/config registries or validated
  runtime capture under the same native gate. CRC/context-derived names retain
  their derivation label; raw unmapped ids remain visible.
- Projectile behavior is immutable authored data. Skill/projectile ownership,
  event hashes, decoded media, and asset references keep separate provenance.
- Combat/source-graph consumers reject stale inputs and publish a degraded
  reason rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](webui/gameplay.md).

## Audio evidence

Audio recovery separates six layers:

1. physical package/media identity;
2. decoded playable media;
3. Wwise Event/action/media graph;
4. authored game consumer and control parameters;
5. validated runtime request;
6. selected branch, audibility, and final DSP behavior.

Evidence may advance only one layer at a time. A stronger downstream fact does
not retroactively make every upstream candidate unique.

Stable conclusions:

- `build_audio.py` owns decode, bank/HIRC indexing, relinking, and Gameplay
  sidecars. Shared SFX/music and language voice remain separate physical roots.
- AKPK entries, Wwise numeric media ids, Events, containers, switches, random
  nodes, RTPC curves, and authored consumers keep their native identities.
  Same-id files in different roots are not collapsed by filename stem.
- Authored Event requests, controller callbacks, Timeline clips, Lua calls,
  serialized AudioCue trees, external sources, and responsive-voice tables are
  typed consumer evidence. They do not prove the selected runtime arm.
- A source prefab or component proves a possible emitter, not scene
  instantiation or level ownership.
- Native method names and callsites are accepted only with exact-build hashes
  and bounded argument/control-flow validation. Literal, dictionary, selector,
  callback, and external-source paths remain distinct.
- Runtime trace bundles must be complete, verified, language-compatible, and
  source-matched. They prove the captured request only; playback success,
  audibility, and DSP response remain separate gaps.
- Unsupported codec/plugin media, absent historical/language chunks, decode
  failures, and mapping failures are reported independently.

Detailed changing investigations live under `reports/story/recovery/audio/`.
Page behavior and focused publication belong in
[`webui/audio.md`](webui/audio.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link must retain the earlier physical identity and cannot be substituted by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in [`asset_recovery.md`](asset_recovery.md);
Map publication belongs in [`webui/map.md`](webui/map.md).

## Source graph

Canonical database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

The graph indexes evidence already produced by owning builders. It is a query
and provenance surface, not an authority that may invent new recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds retain only exact AssetMap rows consumed by WebUI material,
shader, texture, and FMV edges. Full builds are for exhaustive Unity
object/PathID investigation. Every edge keeps an evidence kind; availability,
registration, address order, and mission environment context never become
ownership or chronology.

Before deleting or renaming a generated report, search graph readers and rebuild
the database if that report is an input.

## Diagnostics

Use the closest owning report first:

```text
reports/export/
reports/animestudio/
reports/assets/
reports/audio/
reports/source_graph/
reports/story/build/
reports/story/recovery/
```

Revisitable format probes belong in `scratch/<topic>/`; disposable extraction
and before/after evidence belongs in `tmp/<topic>/`.

## Remaining gaps

- Streaming's next advance requires independent record-end evidence or a
  bounded runtime carrier witness. Keep selector9 held until its component
  mapping indices and write span are authenticated; do not repeat anonymous
  load-width or target-distance statistics. Multi-target clusters need extents;
  neither zero values nor a loop skip establishes validity or sizeof.
  Marker13's observed gap profiles are anonymous, and serialized absence is
  not a numeric selector.
  Marker17 body profiles are structurally closed but anonymous. Marker15 still
  needs a concrete producer, source extent or independently bounded unread
  region: repeating a 16-byte native load does not prove record size. Its
  directory is bounded, not its records; missing count keys remain unsupported.
  Paired Init/Streaming paths, serialized ordinals and ordered witnesses do not
  prove concrete runtime root/key receipt, fresh key state, absence of overrides
  or execution. Native Info provenance is conditional, not a concrete record.
  Keep field namespaces and runtime semantics behind those gaps. Then Terrain
  block/channel semantics, DynamicStreaming, irradiance, manifest, mmap,
  patch, and JsonData body semantics.
- Recover more exact gameplay action/selector/formula contracts without
  treating native names as byte-layout proof.
- Close more authored and observed audio consumers through exact Event/media
  traversal, while preserving branch and audibility gaps.
- Improve exact prefab, renderer, material, animation, and world-instance
  ownership.
- Keep native gates and source-graph provenance deterministic across client
  updates.
