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
  A distinct member-five action reads a byte, three scalar32 values and the
  same variable-width target profile. `scripts/game_data/buff_68_native.json`
  pins its own normal/null paths and exact target context; its equal member
  count does not select the earlier member-five counted-payload layout.
  `scripts/game_data/buff_10f_native.json` pins a fixed member-five reader:
  byte, three scalar32 values, then a final byte, with no nested provider.
  Its byte helpers establish nonzero normalization, not gameplay meaning;
  equal member counts cannot substitute a target or payload for that final byte.
  The member-six reader in `scripts/game_data/buff_69_native.json` adds a
  fourth scalar32 before the target. Its later destination-object offset does
  not move that scalar after the target on the wire. The ObjectType enum
  context adds no nested record, and the target ends the action with no final
  source byte; the managed condition name remains separate from this framing.
  `scripts/game_data/buff_44_native.json` pins another member-six layout with
  a signed-length byte payload before the target instead of that fourth scalar.
  Preserve its variable extent and null/empty distinction; the payload's later
  object offset does not move it after the target in source order. Timer names
  and equal member counts establish neither runtime behavior nor wire grammar.
  The selected member-seven child reuses that scalar-payload profile twice,
  after one byte and four scalar32 reads. The fourth scalar is serialized
  before both nested records despite its later destination-object offset;
  memory layout must not substitute for consumer order. Its selected native
  contract is `scripts/game_data/buff_50_native.json`; the two identical static
  type arguments do not certify live formatter selection or comparison meaning.
  `scripts/game_data/buff_163_native.json` pins a member-eight reader that
  places a byte payload and scalar32 between the common prefix and two scalar
  payloads. Each nested instance has its own header and variable byte span;
  the second ends the record without a final byte. The scalar enum context
  does not establish an operation's meaning or add a nested source member.
  The separate member-seven reader in `scripts/game_data/buff_7b_native.json`
  instead places a target, scalar32 and scalar payload after the common prefix.
  Its interposed scalar remains in source order; the final payload consumes
  four raw scalar bytes despite its managed Double name, with no trailing byte.
  `scripts/game_data/buff_65_native.json` pins a distinct member-eight order:
  byte, four scalar32 values, target, byte and scalar payload. Its interleaved
  output setters consume no source bytes; distinguish their receiver from the
  reader before counting serialized members. The two exact nested contexts
  reuse existing finite profiles without promoting the managed condition name.
  The independently pinned `scripts/game_data/buff_6e_native.json` has that
  same source order and nested contexts. Both tags may share the finite parser
  branch while retaining distinct record tags and native identities; this
  structural equivalence does not establish equal gameplay conditions.
  The extended member-eleven action in `scripts/game_data/buff_157_native.json`
  adds a byte/payload/scalar32 segment before the target in that scalar-prefix
  family, then reads a byte and scalar payload. Equal nested type arguments
  permit profile reuse, not omission or reordering of intervening source reads.
  Extended unions consume FA followed by a little-endian unsigned tag; record
  reports retain that decoded tag rather than the escape byte. Supporting a
  decoded tag does not automatically admit its reserved single-byte encoding:
  `scripts/game_data/buff_fe_native.json` pins the member-twenty reader reached
  by the authenticated FA FE 00 records, while physical FE remains unsupported.
  Its value-class helper reads one DWORD; distinguish this source operation
  from the interleaved scalar-payload and target providers. The member-four
  reader in `scripts/game_data/buff_fd_native.json` ends immediately after the
  common byte/three-DWORD prefix, with no nested provider; its managed
  control-flow name does not prove branch suppression or execution order.
  Physical FD likewise stays unsupported independently of decoded tag FD. Unknown tags
  stop at the original start. `scripts/game_data/buff_119_native.json` pins a
  member-twenty-two action with inline DWORD advances among scalar helpers,
  a byte payload and target; two scalar32 values end the record. Output-side
  cast/cache branches add no source fields. Its required finder-three extension
  reads raw12, raw16, a scalar payload and a byte, each with an independent
  source boundary. Raw widths and managed names establish neither spatial
  meanings nor audio-event identity, ownership or actual playback.
  The selected extended member-eight child reads
  one byte, three scalar32 values, paired payload, scalar payload, one byte and
  paired payload. Its normal reader crosses chained unwind regions: the first
  `.pdata` end is not a record or function end. The selected read/null paths
  live in `scripts/game_data/buff_11f_native.json`; names and runtime use remain
  unresolved independently of this structural closure. Paired and scalar
  payloads can have identical extents; select their profiles from independent
  nested-consumer evidence, not byte length alone. The member-nine reader in
  `scripts/game_data/buff_96_native.json` places scalar and paired payloads
  consecutively before a target: their shared member-three header cannot choose
  a grammar, while the distinct exact type contexts support that source order.
  The extended member-38 action in `scripts/game_data/buff_169_native.json`
  combines two targets, direction, assignment and byte-payload lists with raw
  spans and scalar payloads. Its Vector3-context helper consumes twelve raw
  bytes, while a separate inline operation consumes sixteen; neither is the
  variable-width blackboard vector profile. Preserve all source operations,
  and reuse list element contracts only after exact instantiation joins.
  The selected member-thirteen child closes three target profiles, a finder
  profile and a scalar payload in native read order. The finder contains a
  counted byte-payload list, scalar32 and a member-two query whose selected
  array helper consumes count times four bytes. Keep all values anonymous.
  `scripts/game_data/buff_b4_native.json` owns the native contract, including
  an explicit limitation: List<string> has a static type join but no separate
  formatter MethodSpec; the shared List<Object> count/loop and String element
  reader support a finite structural profile, not actual provider selection.
  `scripts/game_data/buff_7c_native.json` places this variable query after a
  target; its sixteen-byte output store does not establish wire extent. The
  target's finder18 extension selects a distinct member-16 ColliderShapeData,
  not the member-18 HitBoxFinder ShapeData. Its three vector-context helpers
  each advance twelve raw bytes, separately from variable byte payloads;
  neither similar names nor destination layout selects the shape grammar.
  The distinct member-six reader in `scripts/game_data/buff_b6_native.json`
  instead follows the common scalar prefix with a target and one byte. Its
  output-side construction adds no source member; the managed action name
  establishes neither an owner relationship nor a runtime completion effect.
  `scripts/game_data/buff_80_native.json` pins another member-six layout with
  two successive targets after that prefix and no final byte. Their shared
  type context does not merge the two serialized instances or prove comparison
  semantics; each instance retains its own bounded nested grammar.
  The member-thirteen order in `scripts/game_data/buff_16e_native.json`
  interleaves extra bytes, scalar32 values and a variable byte payload before
  two targets, then reads a final byte. Its necessary finder5 extension has
  a zero-member reader: construction adds no serialized fields. Scalar-helper
  enum contexts likewise do not add nested members or establish effect meaning.
  Related member-eight children have a byte payload, counted nested records,
  scalar32 and the same query profile after their common scalar prefix.
  `scripts/game_data/buff_56_native.json` pins the member-one value-type list;
  `scripts/game_data/buff_57_native.json` joins a reference-type list whose
  member-three elements contain two byte payloads separated by a byte.
  Equal outer member counts do not imply equal element layouts. Each element
  consumes its own header; a managed name or output-slot width cannot replace
  the concrete nested reader. The reference-list loop remains conditional on
  the shared consumer, and active formatter selection stays open for both.
  `scripts/game_data/buff_58_native.json` selects a different member-eight
  order: common scalar prefix, one member-one value, target, scalar32 and
  scalar payload. Its BuffId context is a value type, not a list: no collection
  count precedes that nested header. Reuse the pinned element reader directly;
  a shared element type does not establish a shared collection shape. The final
  scalar payload still consumes four raw scalar bytes despite its managed name.
  The member-twelve action in `scripts/game_data/buff_02_native.json` instead
  reads a counted member-one value list, two targets, byte, scalar payload,
  third target and two bytes after the common prefix. Its list consumer and
  element instantiation match the existing value-list proof; a single-value
  reader cannot replace the collection count. Repeated target type arguments
  represent separate serialized instances, each with its own bounded profile.
  `scripts/game_data/buff_9a_native.json` closes a member-eleven action through
  counted member-33 units, member-85 effect configurations and selected
  calculation unions. Inline scalar/vector advances and helper reads must both
  appear in source order; an output-store inventory misses serialized members.
  The nested vector contains three variable-width scalar payloads, distinct
  from an inline twelve-byte span. Three unit lists and the effect array remain
  null/empty-only; positive counts stop explicitly until element readers close.
  A normal exit may tail-jump to the write barrier: pin the entire instruction
  and the separate null rejoin, not an assumed RET or partial JMP byte.
  The member-eighteen action in `scripts/game_data/buff_a2_native.json` reads
  two byte payloads, four separate targets and one effect configuration among
  its scalar members. Reuse the pinned member-85 configuration and finite
  target profiles, preserving each instance's own unsupported boundary.
  Cached output casts and stores rejoin the source reads; they add no wire
  members and cannot substitute for the source cursor order.
  A member-six child contains only a byte, four scalar32 values and scalar64.
  Its final helper reads and advances eight source bytes; that cursor evidence,
  pinned in `scripts/game_data/buff_5b_native.json`, establishes wire width.
  Preserve the raw bits: a mask-like managed name does not prove flag meanings.
  The separate member-six reader in `scripts/game_data/buff_6d_native.json`
  ends with a signed-length byte payload after a byte and four scalar32 values.
  Its final helper consumes variable bytes, not the preceding reader's scalar64;
  equal member counts and null samples cannot establish a fixed record width.
  Scalar enum contexts add no nested records, and output setters add no source
  reads. Keep null and empty payloads distinct and their contents anonymous.
  `scripts/game_data/buff_7a_native.json` pins another member-six order:
  common byte/three-scalar prefix, scalar32 and byte payload. It has no extra
  byte before that payload. Both enum contexts consume four bytes without a
  nested header; equal member counts cannot select this reader or the distinct
  byte/scalar/payload order above. Infliction meaning remains unresolved.
  Another member-ten child reads the common byte/three-scalar prefix, finder,
  scalar32, target, scalar32, byte and scalar payload. Its three static type
  contexts reuse the existing finder/target/scalar readers; equal outer member
  counts do not select a layout. `scripts/game_data/buff_3c_native.json` pins
  that distinct order through normal return and the separate null path.
  Intermediate setters do not establish wire order or gameplay conditions.
  `scripts/game_data/buff_136_native.json` pins a member-nine order with the
  same finder/scalar32/target segment followed by a byte payload and final byte.
  Its interposed scalar enum context adds no nested member. Preserve the final
  byte after the variable payload; a shared finder/target pair does not choose
  the surrounding action grammar or prove the managed action's runtime effect.
  `scripts/game_data/buff_c4_native.json` pins a member-eight order with two
  byte payloads separated by finder and ending in target. Both nested contexts
  match the finite readers above; preserve the intervening variable payload
  rather than treating finder/target as adjacent. Blackboard ownership remains
  unresolved even when the complete forward record is bounded.
  Member-nine actions have distinct orders: `scripts/game_data/buff_78_native.json`
  adds scalar32, two bytes, target and counted scalar32 values to the common
  prefix; `scripts/game_data/buff_81_native.json` instead adds a length-prefixed
  byte payload, target, another byte payload and two bytes. Equal headers do not
  select either layout. The former pins an independent four-byte element reader;
  its shared list count/null/loop remains conditional on provider selection.
  The latter reuses the byte-payload helper's length/advance proof, not the
  single-byte helper's width. Preserve unknown enum bits and byte contents.
  The member-six reader in `scripts/game_data/buff_48_native.json` reaches the
  same list context after only the common prefix and scalar32. Its element
  type and shared source-width witness support the same count-times-four
  profile without element headers; the different outer layout and live list
  provider selection remain separate claims. Preserve null and empty lists.
  `scripts/game_data/buff_9b_native.json` pins another member-nine order:
  two byte payloads separated by sixteen inline source bytes, then scalar32
  and target after the common prefix. The explicit sixteen-byte advance proves
  the raw extent independently of output stores; log and color meanings remain
  unresolved. Its scalar enum context adds no nested serialized member.
  `scripts/game_data/buff_c5_native.json` pins a member-sixteen action with
  separate effect configuration, calculation union, tag list and target reads,
  including the extra byte after its common prefix and the final byte. The tag
  list wrapper has one member; its separately pinned element has one scalar32
  member. Keep list count/loop framing conditional on the registered formatter
  candidate, preserve null/empty states, and retain unknown calculation unions.
  This bounded forward profile neither selects a live provider nor resolves
  Skill's independent terminal candidates or establishes healing/tag meanings.
  `scripts/game_data/buff_0a_native.json` pins a member-seven action adding a
  byte payload, scalar payload and target to the common prefix. The two static
  nested contexts match the existing finite readers; their order comes from
  source calls, not output fields. Preserve null/empty payloads and the scalar
  payload's four-byte raw value. Timer meaning and live provider choice remain
  unresolved; exact forward ranges do not establish whole-BuffData EOF.
  `scripts/game_data/buff_88_native.json` pins a member-five action whose final
  member is the same finite scalar payload. Its raw value occupies four bytes
  despite the managed type name; neither that name nor the action identity
  proves probability meaning. There is no source member after the nested read.
  `scripts/game_data/buff_5a_native.json` pins a member-six action adding the
  paired-payload profile and a separate final byte payload to the common prefix.
  The paired profile shares a member-three header with the scalar profile but
  reads a second variable payload instead of a four-byte value. Preserve all
  three payload lengths independently; event-name meaning remains unresolved.
  `scripts/game_data/buff_145_native.json` pins a member-six action ending
  with scalar payload then paired payload after the common prefix. Their exact
  type contexts select distinct finite profiles despite equal member-three
  headers; the first ends in four raw bytes, the second in a variable payload.
  No source read follows the second profile. Signal meaning remains unresolved.
  `scripts/game_data/buff_de_native.json` pins a member-37 reader with four
  independent inline raw12 advances and separate assignment/target-byte lists.
  The latter element has two members: target then byte payload. Its exact
  reference-type instantiation supports a conditional shared list profile;
  keep null elements and unsupported targets explicit. Getter/output offsets
  add no source fields, and the final two scalar32 reads remain separate.
  These boundaries do not establish projectile behavior or spatial meaning.
  `scripts/game_data/buff_bd_native.json` pins a member-six reader ending
  with a nested sequence followed by target. The exact sequence context reuses
  the bounded count/child/two-byte grammar, including its recursive depth gate.
  An unknown child stops inside the sequence and leaves the enclosing action
  incomplete; sequence termination alone does not consume the final target.
  The managed iteration name does not establish runtime execution semantics.
  `scripts/game_data/buff_6a_native.json` pins a member-eight reader with
  two bytes and two distinct counted scalar32 lists after the common prefix.
  A separately joined consumer passes each exact list element type to the
  DWORD source helper; enum names and output slots are not the width proof.
  Keep count/null/loop framing conditional, preserve each list independently,
  and admit no element headers or inferred ATB meanings.
  `scripts/game_data/buff_24_native.json` pins a member-twelve reader with
  a real raw12 source advance and nested member-eighteen/member-seven profiles.
  Their curve reader consumes raw8, a nullable signed count and raw28 elements;
  validate counts before iteration and retain independent null/empty curves.
  The member-seven profile has two separate curve members. Its provider's
  32-byte return buffer does not establish wire width. Preserve raw scalar
  bits and conditional provider selection; camera behavior remains unresolved.
  `scripts/game_data/buff_16b_native.json` pins a member-six reader ending
  in scalar payload then target. The exact BlackboardInt context has its own
  authenticated reader proving payload/byte/DWORD source order; equal headers
  and managed names alone do not justify profile reuse. An unknown target
  keeps the enclosing action incomplete. Spawning behavior remains unresolved.
  `scripts/game_data/buff_7e_native.json` pins a member-six reader ending
  in two target profiles. Both exact contexts select the same finite profile,
  but their null states, nested counts and source boundaries stay independent.
  No source field follows the second target. Containment meaning is unresolved.
  `scripts/game_data/buff_35_native.json` pins a member-fifteen reader with
  independent targets, a bounded curve, direction and final scalar payload.
  Its exact BlackboardDouble wrapper and inlined formatter both consume four
  source bytes for the final scalar; the name does not establish eight bytes.
  Reuse finite profiles only through these concrete source-reader joins, and
  keep unsupported direction children incomplete. Animation meaning and live
  formatter selection remain unresolved.
  `scripts/game_data/buff_ea_native.json` pins a member-seven reader ending
  with a byte, byte payload and independently counted target list. The exact
  list carrier joins the existing target element type; shared list dispatch
  remains conditional. Preserve nullable counts and null elements, and leave
  the list and action incomplete at an unsupported child. The managed merge
  name does not establish runtime behavior or cross-target relationships.
  `scripts/game_data/buff_61_native.json` pins a member-ten reader containing
  target, scalar32, two bytes, scalar32 and final byte payload after its common
  prefix. The comparison enum context is a DWORD source read, not a nested
  object. Unknown target children leave every following field unconsumed and
  the parent incomplete; entity-count and comparison semantics remain unresolved.
  `scripts/game_data/buff_3f_native.json` pins a member-seven reader ending
  with scalar32, scalar payload and a separate byte payload. Its BlackboardInt
  context joins the concrete reader already pinned for `16b`; preserve the two
  payload counts and null states independently. Nested completion cannot end
  the parent before the final payload. Buff-consumption meaning is unresolved.
  `scripts/game_data/buff_14d_native.json` pins an extended member-nine action:
  finder, byte, scalar32, target and final scalar payload follow the common
  prefix. Each nested context joins its own finite reader; preserve their null
  states and counts independently. An unsupported target keeps the final payload
  unconsumed. Duration and operation meanings remain unresolved.
  `scripts/game_data/buff_73_native.json` pins a member-four action ending
  immediately after the common byte and three scalar32 members. The Priority
  context belongs to a scalar read; neither constructors nor output setters
  introduce nested source data. Skill-cast identity meaning remains unresolved.
  `scripts/game_data/buff_5d_native.json` pins a member-five action whose final
  scalar32 follows the common prefix. Its exact DamageType context selects a
  DWORD source read, not a nested object. Keep all raw scalar bits; enum names
  do not validate runtime values or establish damage behavior.
  `scripts/game_data/buff_42_native.json` pins a member-ten action with byte,
  scalar32, two bytes and two independent target profiles after its common
  prefix. Both target contexts join the existing finite reader; completion of
  the first cannot complete the parent or consume an unsupported second target.
  Preserve raw scalar bits; distance/comparison behavior remains unresolved.
  `scripts/game_data/buff_27_native.json` pins a member-ten action containing
  target, two bytes, paired payload, byte and final target after the common
  prefix. The exact BlackboardString context joins the paired reader, not the
  equal-header scalar reader. Preserve its two signed payload counts and both
  target boundaries independently; skill identity and casting remain unresolved.
  `scripts/game_data/buff_95_native.json` pins member-eight framing with a
  scalar payload, counted member-three inputs and final target. Each input has
  its own counted AssignPair list and member-one GlobalBuffId byte payload;
  preserve both list contexts and counts independently. A value-type marker
  does not establish enum width; the ID output carrier is not its wire size.
  Global buff ownership, lifetime and ID meaning remain unresolved.
  `scripts/game_data/buff_74_native.json` pins a member-five action ending
  with a nullable counted scalar32 list. Its exact element context joins the
  independently pinned DamageType DWORD reader; preserve null/empty states
  and raw element bits, without object headers or inferred damage behavior.
  `scripts/game_data/buff_16d_native.json` pins an extended member-eight
  action ending with scalar32, byte and two independent target profiles after
  the common prefix. Preserve each target boundary and leave the parent
  incomplete at unsupported children; spell and target relationships remain unresolved.
  `scripts/game_data/buff_160_native.json` pins an extended member-ten
  action with two bytes, scalar32, byte, scalar32 and final target after the
  common prefix. Its two enum contexts select DWORD reads; the final target
  has a separate provider context. Actor visibility and part ownership remain unresolved.
  `scripts/game_data/buff_89_native.json` pins a member-six action ending
  with two independent byte payloads after the common prefix. Preserve both
  signed lengths and null/empty states without adding an object header or flag;
  payload encoding and heal-value ownership remain unresolved.
  `scripts/game_data/buff_171_native.json` pins a member-thirteen action
  with three independent scalar payloads, a separate byte payload and target
  followed by a required byte. Exact BlackboardDouble contexts reuse the
  four-byte scalar reader; attribute ownership and arithmetic remain unresolved.
  `scripts/game_data/buff_132_native.json` pins an extended member-six
  action ending in two independent byte payloads. Preserve both signed lengths
  and null/empty states; the parent completes only after the second payload.
  Payload encoding and ATB-value ownership remain unresolved.
  `scripts/game_data/buff_d4_native.json` pins a member-eight action
  with two independent target profiles followed by two four-byte scalars.
  Preserve raw scalar bits and keep the parent incomplete until both tails
  finish; target ownership and interrupt behavior remain unresolved.
  `scripts/game_data/buff_60_native.json` pins a member-six action
  ending with scalar32 and a final target profile. Its enum context selects
  a DWORD source read; preserve raw bits and keep incomplete targets explicit.
  Enemy rank interpretation and comparison behavior remain unresolved.
  `scripts/game_data/buff_126_native.json` pins an extended member-five
  action ending directly with a target profile. Preserve nested null/count
  boundaries and leave unknown children explicit; poise recovery behavior
  and target ownership remain unresolved.
  `scripts/game_data/buff_1c_native.json` pins a member-fifteen action
  with a distinct member-four payload/byte/scalar32/byte child. Its final byte
  is required before subsequent target, direction and scalar profiles can
  complete; blow-off behavior and priority meaning remain unresolved.
  `scripts/game_data/buff_06_native.json` pins a member-five action
  ending with a DWORD under an exact enum context. Preserve raw bits and
  reject missing scalar bytes; event meaning and achievement behavior
  remain unresolved.
  `scripts/game_data/buff_142_native.json` pins a member-eleven action
  with five independent byte payloads, a target between the first and second,
  and a required final DWORD. Unknown target profiles preserve the unread tail;
  blackboard meaning and value conversion remain unresolved.
  `scripts/game_data/buff_03_native.json` pins a member-nine action
  containing BlackboardDouble and a counted GlobalBuffId list followed by
  a required byte. List elements retain their own header and payload bounds;
  value-type identity does not establish raw wire width or buff lifetime.
  `scripts/game_data/buff_51_native.json` pins a member-six action
  ending with two independent BlackboardString profiles. Preserve both object
  null states and each payload length; a failed second profile leaves the parent
  incomplete. String decoding and comparison behavior remain unresolved.
  `scripts/game_data/buff_5e_native.json` pins a member-five action
  ending with a required DWORD under the exact DamageTypeMask context.
  Preserve arbitrary raw bits and reject incomplete scalars; mask meaning
  and condition evaluation remain unresolved.
  `scripts/game_data/buff_13b_native.json` pins a member-six action
  containing one signed-length byte payload and a required final DWORD.
  Preserve null/empty payloads and raw scalar bits; the selected body has no
  nested provider. Damage ownership and value meaning remain unresolved.
  `scripts/game_data/buff_84_native.json` pins a member-six action
  containing TargetSettings and a required final DWORD. Unknown nested targets
  preserve the unread scalar; a completed target alone does not complete the
  parent. Target ownership and weapon-mask meaning remain unresolved.
  `scripts/game_data/buff_174_native.json` pins a member-eleven action
  with three independent BlackboardDouble profiles, a byte payload, DWORD,
  target and required final byte. Preserve partial-parent boundaries and each
  null state; entity property meaning and target ownership remain unresolved.
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
