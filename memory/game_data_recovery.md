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
  The extended union in `scripts/game_data/buff_15c_native.json` independently
  selects this target-ending order. Preserve null target versus null wrapper
  and stop unknown nested shapes in place; its UI name does not establish
  shield ownership or add a source tail.
  `scripts/game_data/buff_05_native.json` independently pins another
  target-ending action, including its lazy initialization and null rejoin.
  Short and extended union encodings preserve their distinct widths; the
  registered interruption name does not establish live skill behavior.
  `scripts/game_data/buff_4c_native.json` pins two independent targets with a
  nullable byte-payload list between them. Its list count reserves the terminal
  target minimum before iteration; null lists, null elements and target nulls
  remain distinct. Projectile clearing behavior and string decoding are unproven.
  `scripts/game_data/buff_16f_native.json` separately establishes a byte before
  the target and a terminal BlackboardDouble profile after it. The scalar
  profile ends in four raw bytes; keep both nested null states independent and
  do not infer ATB spending or ownership from the action name.
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
  from an inline twelve-byte span. `scripts/game_data/buff_damage_lists_native.json`
  separately pins the second unit list as DamageProcessorBase: union 0 reads
  a scalar-payload profile; union 9 reads the existing AttributeModifier profile
  followed by a required DWORD. Its count reserves the shortest 42-byte unit
  tail. First/third lists and the effect array remain null/empty-only; unknown
  processor tags stop before their tag. Static type joins and selected source
  order do not establish live provider selection or gameplay behavior.
  `scripts/game_data/buff_calc5_native.json` adds CalculationBase tag 5:
  header four reads byte, DWORD, a scalar-payload profile and required DWORD.
  It cannot reuse tag 3's different header-four layout; null scalar payloads
  still require the final DWORD. Attribute arithmetic remains unresolved.
  `scripts/game_data/buff_calc1_native.json` pins tag 1 as header two followed
  by two independent scalar-payload profiles. A null first scalar still requires
  the second; the BreakingAttack type identity does not establish its arithmetic.
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
  `scripts/game_data/buff_5c_native.json` independently selects this same fixed
  source order and reuses the QWORD reader. Its Priority context belongs to
  the first DWORD and CheckType to the fourth; neither enum identity changes
  the wire width or establishes damage/immunity meaning. There is no extra tail.
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
  `scripts/game_data/buff_2f_native.json` separately pins sequence, byte,
  DWORD, target and two raw four-byte values after the common prefix. Its
  inlined header read preserves the same one-byte/FF boundary. Neither null
  nested profile removes later fields; preserve completed sequence evidence
  when target or tail consumption fails. Channeling/timing meaning stays open.
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
  `scripts/game_data/buff_3a_native.json` independently selects that same Int
  profile after an extra DWORD and before a terminal byte payload. Preserve
  independent null states and reject an incomplete terminal payload even after
  the nested profile completes; comparison names do not establish layer meaning.
  `scripts/game_data/buff_150_native.json` independently places a terminal
  byte after a BlackboardDouble profile. A null profile still requires that
  byte; a null wrapper ends separately. This source order does not prove a
  cooldown unit, operation, or runtime effect.
  `scripts/game_data/buff_a7_native.json` closes two independently nullable
  profiles repeated around a direct query. The member-one profile contains a
  byte; the member-six profile interleaves two DWORD/scalar-payload pairs before
  two terminal bytes. The parent still requires its own final byte. Preserve
  separate nested boundaries; part identity and modification meaning remain
  unresolved despite the exact selected type contexts.
  `scripts/game_data/buff_19e_native.json` independently joins a View wrapper
  with two curve profiles and a nullable byte-payload list before six terminal
  bytes. Reserve those six bytes while bounding the list; neither a null list
  nor a completed element completes the parent. Preserve raw four-byte values
  and independent curve nulls without promoting camera or blend meaning.
  `scripts/game_data/buff_08_native.json` closes two levels of nullable lists:
  each member-one element owns a list of member-five records containing a byte,
  byte payload, two DWORDs and raw4. Their exact contexts remain distinct from
  the action's vector, scalar and curve profiles. Both outer lists reserve the
  minimum remaining parent bytes; thirteen terminal bytes are independently
  required. Null lists, empty lists and null elements remain separate, while
  camera state and condition meanings stay unresolved.
  `scripts/game_data/buff_120_native.json` selects two independent scalar
  payload profiles followed by a DWORD and a terminal byte payload. The shared
  scalar context proves profile reuse, not shared null state or a fixed parent
  width. Both profiles may complete while the parent remains truncated; require
  the final DWORD and full signed-length payload. Random algorithm, distribution
  and payload ownership remain unresolved.
  `scripts/game_data/buff_9f_native.json` places an extra byte and DWORD before
  two independent target profiles and a final direct query. Matching target
  contexts do not merge their null states; completed targets do not replace
  the final query header, count or elements. Unknown target children leave the
  parent incomplete. Dispel behavior and query-tag meanings remain unresolved.
  `scripts/game_data/buff_1b_native.json` interleaves two target profiles,
  six scalar payloads and a direct direction profile with bytes and a DWORD.
  Repeated scalar contexts select independent variable-width instances; require
  the final scalar after the last byte. Direction's nested target children
  retain their explicit unsupported boundary. Blow-off behavior, units and
  direction conventions remain unresolved.
  `scripts/game_data/buff_87_native.json` closes a terminal nullable list of
  sequence profiles. Each element owns its header, action count and two final
  bytes; there is no additional parent tail. Preserve null/empty lists and
  null/empty sequences separately. Propagate recursive depth limits and unknown
  child unions without completing the parent. Boolean evaluation, execution
  order and short-circuit behavior remain unresolved.
  The EC native contract pins both direction-to-target calls and the reverse
  target-to-direction call. Direction now admits the existing finite target
  profile, with at most 64 active non-null target instances across recursive
  paths. Reject deeper targets before their header; unwind depth on failure,
  retain completed children and leave incomplete parents unrecorded.
  `scripts/game_data/buff_70_native.json` pins member-six framing: one byte
  and five DWORDs, including two required terminal DWORDs. Its three scalar
  generic contexts add no headers. Preserve raw values without promoting
  enum labels to projectile immunity behavior.
  `scripts/game_data/buff_71_native.json` independently pins the same member-five
  byte/three-DWORD/byte shape for short and extended union encodings. Its final
  byte is mandatory; equal layout does not establish a shared runtime purpose
  or projectile/dodge condition semantics.
  `scripts/game_data/buff_14f_native.json` pins a member-five body of one
  byte, three DWORDs and a required terminal byte. Its Priority context adds
  no header. Preserve terminal byte values without boolean or dash semantics;
  parent completion requires the final byte.
  `scripts/game_data/buff_124_native.json` pins a fixed member-five body:
  one byte and four DWORDs. Priority and RecordType contexts add no nested
  headers; the final DWORD is required for every non-null wrapper. Raw values
  remain structural evidence without battle-record semantics.
  `scripts/game_data/buff_125_native.json` pins an extended member-six action
  with a required byte between the common prefix and terminal scalar payload.
  The byte remains required when the scalar is null; dash-energy recovery
  semantics remain unresolved.
  `scripts/game_data/buff_14b_native.json` joins SetAnimTimeScaleAction to
  header6, the common prefix, TargetSettings and terminal BlackboardDouble.
  The scalar wrapper is required even when the target is null; no further
  byte or DWORD follows it. Time-scale behavior and target ownership remain
  unresolved.
  `scripts/game_data/buff_8a_native.json` joins ContinuousFindTargetAction to
  its header19 direction, scalar, payload and selector read order. Two final
  bytes and a required raw float32 field close the record; null nested profiles
  do not remove that tail. Short and extended union encodings share this order.
  Continuous targeting behavior and payload ownership remain unresolved.
  `scripts/game_data/buff_ad_native.json` joins EventListenerAction to header5,
  the common prefix and a nullable AbilityActionMap list. Each FF/header2 map
  places its DWORD before the nullable Sequence array; no field follows that
  array or the outer list. Nested sequences retain the action recursion depth
  and their two required tail bytes. Framing remains structural-only; the Event
  type context does not establish trigger ownership or runtime listener behavior.
  `scripts/game_data/buff_17_native.json` joins BindBountyEnemyAction to
  header5, the common prefix and terminal BlackboardString. Its paired profile
  retains both nullable payload lengths and the intervening byte; null/empty
  payloads do not remove later fields. Enemy binding, payload encoding and
  reference ownership remain unresolved.
  `scripts/game_data/buff_ce_native.json` joins IgniteAction to header8:
  the common prefix, TargetSettings, a DWORD, a nullable byte payload and
  terminal TargetSettings. Null/empty payloads retain the final target wrapper.
  The exact IgniteType context does not narrow allowed DWORD bits; ignition
  behavior and payload/target ownership remain unresolved.
  `scripts/game_data/buff_18e_native.json` joins TyphoeaArcheryChipDataAction
  to header18: the common prefix, four nullable byte payloads, five bytes,
  two payloads, one byte and two terminal payloads. Every payload retains its
  own required signed nullable length; null or empty values do not remove later
  fields. Payload encoding, reference ownership and archery behavior remain unresolved.
  `scripts/game_data/buff_102_native.json` joins OnSpellInflictionStart to
  header5, the common prefix and a required terminal DWORD. The exact final
  context identifies EnergyShardType, while its source width remains four
  bytes with arbitrary bits retained. Spell-infliction behavior, enum meaning
  and field ownership remain unresolved.
  `scripts/game_data/buff_28_native.json` joins ChangeGeneralAbilityButton
  to header7, the common prefix, one BuffId profile, a nullable byte payload
  and a required terminal DWORD. BuffId reuses the pinned header1 payload
  reader; its provider output carrier does not establish wire width. Button
  behavior, enum meaning and identifier/field ownership remain unresolved.
  `scripts/game_data/buff_172_native.json` joins StoreBuffCount to header8,
  the common prefix, two nullable byte payloads, TargetSettings and one
  required terminal byte. Null and empty payloads remain distinct; a null
  target does not remove the terminal byte. Count-storage behavior and
  payload/target ownership remain unresolved.
  `scripts/game_data/buff_166_native.json` independently joins SlowAction to
  the header13 paired/scalar/keyword-list/byte/scalar/two-target order. Its
  list reserves four bytes for the required remaining fields, including both
  nullable target wrappers; the second target ends the record. Slow-action
  behavior and keyword/target ownership remain unresolved.
  `scripts/game_data/buff_19c_native.json` independently joins WeakAction to
  the header13 paired/scalar/list/byte/scalar/two-target order shared with
  ShelterAction. The list reserves four bytes for later fields, and the second
  target wrapper is required without an extra terminal DWORD. Weakness behavior
  and keyword/target ownership remain unresolved.
  `scripts/game_data/buff_18b_native.json` joins TriggerSpellBurstEventAction
  to a fixed header5 reader: common byte/three DWORDs, then a required DWORD.
  The final context identifies EnergyShardType, but framing preserves arbitrary
  bits without inferring enum validity, spell-burst behavior or event ownership.
  `scripts/game_data/buff_07_native.json` joins AddAIMarkerAction to a header8
  reader with Double profile, GameplayTag DWORD, TargetSettings and a required
  terminal byte after the common fields. Existing independently pinned readers
  bound both nullable profiles and the tag DWORD; target completion does not
  imply action completion. AI marker behavior and tag meaning remain unresolved.
  `scripts/game_data/buff_15b_native.json` joins SetWeaknessAction to a header11
  reader with two Double profiles, byte, SequenceActionData, Int, byte and
  terminal Double. Int and Double independently have the same bounded
  payload/byte/DWORD shape; neither is a raw fixed-width number. Sequence
  completion retains required later fields; weakness behavior remains unresolved.
  `scripts/game_data/buff_144_native.json` joins SelfRotateAction to a header18
  reader with DirectionSettings, five bytes, a nullable byte payload, mixed
  DWORD/raw-float fields, TargetSettings and a required final byte. Source
  calls establish this order independently of setters; null nested wrappers
  retain the final byte. Rotation behavior and numeric meanings remain unresolved.
  `scripts/game_data/buff_12a_native.json` joins RefrainObtainUsp to a header7
  reader with a byte, a GameplayTagList wrapper and a required terminal target.
  The wrapper retains its header1 and nullable element list; it is not a raw
  DWORD array. This caller reserves one byte for the target. USP behavior and
  gameplay-tag meanings remain unresolved.
  `scripts/game_data/buff_37_native.json` joins CharWeaponVisibleAction to a
  header10 reader with three bytes, a nullable WeaponVFXOverrideConfig and
  required byte/DWORD tails. The nested header18 consumes nine bytes followed
  by nine independently nullable length-prefixed payloads. Null nested wrappers
  retain both outer tail fields; weapon/VFX behavior and payload meaning remain unresolved.
  `scripts/game_data/buff_15d_native.json` joins ShelterAction to a header13
  reader with paired/scalar payloads, a nullable KeywordEnhanceEdit list and
  two terminal targets. The last target ends the record; unlike the separately
  pinned header14 enhancement actions, no final DWORD follows. The list reserves
  four minimum tail bytes. Shelter behavior and keyword meaning remain unresolved.
  `scripts/game_data/buff_14a_native.json` joins SetAnimatorParamAction to a
  header8 reader with a byte, two independently nullable AnimatorParamAction
  objects and a required signed-length payload. Each nested header5 consumes
  DWORD, byte, raw4 and two DWORDs; null objects do not remove the terminal
  length. Parameter behavior and payload meaning remain unresolved.
  `scripts/game_data/buff_133_native.json` joins SaveBuffLifeTime to a header7
  reader with TargetSettings, BuffFindSettings and a required signed-length
  byte payload. Both nested objects may be null independently; neither removes
  the final payload length. Payload meaning and lifetime behavior remain unresolved.
  `scripts/game_data/buff_f4_native.json` joins MoveGaitAction to a header6
  reader with two required DWORDs after the common prefix. Both calls share
  the GroundedMoveGait context; neither adds a nested header, and the enum
  identity establishes framing without proving movement behavior.
  `scripts/game_data/buff_b9_native.json` joins ForceHideHeadBarAction
  to a header6 reader with one required BYTE before TargetSettings. Short and
  extended union encodings share this profile; the target ends the action,
  without establishing head-bar visibility behavior or target ownership.
  `scripts/game_data/buff_186_native.json` joins TriggerCharSpellInflictionEvent
  to a header7 reader with TargetSettings and two required DWORDs after it.
  Both scalar reads remain required for a null target. The selected helpers
  establish four-byte framing; enum identities do not establish event behavior.
  `scripts/game_data/buff_17c_native.json` joins TeleportAction to a header14
  reader with a bounded nested sequence, scalar payload and TargetSettings.
  Preserve sequence depth/count limits and its two-byte tail; the action also
  requires its own final byte after the target, including when the target is null.
  Static identity and framing do not establish teleport execution behavior.
  `scripts/game_data/buff_f6_native.json` joins MoveToAction to a bounded
  header46 reader: raw Vector3 and variable BlackboardVector3 stay distinct.
  Both final SubSpeed references are required; each nonnull header5 SubSpeed
  consumes scalar payload, byte payload, scalar payload, curve and final DWORD
  in that order. These boundaries do not establish movement behavior.
  `scripts/game_data/buff_ab_native.json` independently joins EnhancedAction
  to the same bounded header14 field order as VulnerableAction. Reuse the
  keyword-edit list reader and both count reserves; the post-list byte and
  final DWORD remain required. Shared framing does not establish shared behavior.
  `scripts/game_data/buff_127_native.json` joins RecoverLockOnEndIfNoLock
  to header5: the common byte/three DWORDs followed by an independently
  nullable TargetSettings, with no additional source tail. Nested target
  bounds and recursion limits remain required; lock-on behavior is unresolved.
  `scripts/game_data/postprocessor_01_native.json` joins postprocessor 1 to
  ConvertToBoxCenterPlaneProjectionPoint: header1 and a nullable List of
  HitBoxFinder.ShapeData, using the independently pinned header18 element.
  There is no local tail after the list; the parent still requires its
  validator count. Projection behavior and shape ownership remain unresolved.
  `scripts/game_data/postprocessor_08_native.json` joins postprocessor tag 8
  to ShuffleTarget: header2, DWORD, then an independently nullable BlackboardInt.
  Its payload/byte/DWORD reader reuses `buff_16b_native.json`; the parent still
  requires its validator count and later elements. Target-shuffling behavior
  and payload meaning remain unresolved.
  `scripts/game_data/validator_02_native.json` joins validator tag 2 to
  CheckRaycastValidator: header2 followed by two required raw DWORDs.
  Both native read contexts identify LayerMask without a nested object header;
  scalar FF bytes cannot suppress the second value or later parent elements.
  Actual raycast behavior and individual layer meanings remain unresolved.
  `scripts/game_data/validator_01_native.json` pins validator 1 independently
  of finder 1: member two consumes BuffFindSettings then a required DWORD.
  Reuse the bounded payload-list/query reader and preserve its null states;
  ValidateMode adds no header and does not establish runtime validation rules.
  `scripts/game_data/buff_root_prefix_native.json` pins root members 2-4 after
  the supported first collection: scalar payload, directly counted raw DWORD
  array, then a member-two collection profile. The array helper copies four
  bytes per entry without an element header; the GameplayTag type name does
  not select the separate tag-list wrapper grammar. The collection consumes a
  nullable reference array followed by a required byte; its selected member-four
  elements contain three DWORDs and a scalar payload. FF wrappers and null/empty
  arrays are distinct, and only a non-null collection has the terminal byte.
  Preserve conditional provider selection and structural-only field meanings.
  `scripts/game_data/buff_root_fifth_native.json` pins the next root collection
  to a List<DataPair> context. Its selected member-four elements read a byte,
  signed nullable byte payload, eight raw bytes and another nullable payload.
  The eight-byte load/advance is independently pinned; do not reuse the scalar
  profile's four-byte raw value or interpret the leading byte as a union tag.
  Null elements and null/empty collections remain distinct.
  `scripts/game_data/buff_root_sixth_native.json` pins the following
  List<BuffActionMap>: FF or member two, a nullable Sequence array, then a
  required inline DWORD. This reverses the first collection's scalar/array
  order; equal member counts do not make the maps interchangeable. Null map
  elements end immediately, while a null/empty array still needs the DWORD.
  Reuse the separately pinned Sequence/action grammar, keeping unknown actions
  at their first byte and preserving completed predecessors. The recovery queue
  now includes unsupported actions reached inside this collection; close those
  before treating all sixth-member endpoints as known. Retain conditional
  provider selection, the independent suffix anchor and the physical opaque range.
  `scripts/game_data/buff_159_native.json` independently pins the reached
  action and both BlackboardImpactValue/BlackboardSuperArmorValue wrappers.
  The header-seven action reads the common byte/three DWORD prefix, two
  `scalar_flag_payload` profiles, then TargetSettings. Each nested wrapper
  reads FF or header four, nullable byte payload, byte, DWORD and required
  final byte; do not substitute the header-three scalar profile. Exact type
  identity does not establish gameplay effects, numeric units or boolean
  meanings. Keep the existing TargetSettings depth/unknown-profile boundary.
  `scripts/game_data/buff_16_native.json` pins the header-thirty AuraAction
  and its distinct BuffInput and TargetFilter wrappers. BuffInput is FF or
  header three, byte, nullable AssignPair list and raw byte payload; neither
  CreateBuffInput nor GlobalBuffInput has this complete shape. TargetFilter
  is FF or header ten, byte/enum fields, GameplayTagQuery and a required final
  DWORD, distinct from BuffFilterSettings. The query helper has an output
  carrier, not a fixed sixteen-byte wire value. Preserve nested Sequence
  unknown stops, independent list null states and the minimum required tail.
  `scripts/game_data/buff_178_native.json` pins the header-eight SwitchMode
  action: common byte/three DWORDs, two bytes, nullable byte payload and a
  required final byte. There are no nested objects or list elements. Keep
  FF wrapper, null/empty payload and arbitrary terminal byte values distinct;
  the static type name does not prove mode behavior or payload meaning.
  `scripts/game_data/buff_c1_native.json` pins header-six GetAITransData:
  common byte/three DWORDs followed by two independently nullable byte
  payloads. Both length words are required even when the first is null/empty;
  keep payload encoding, cross-file identity and AI behavior unresolved.
  `scripts/game_data/buff_101_native.json` pins header-six
  OnSpellAbnormalStartFinish: common byte/three DWORDs, another DWORD and a
  required byte. Priority and SpellAbnormalType contexts add no wire headers;
  arbitrary values remain valid structural bytes, without boolean or spell
  behavior claims. Preserve the complete extended union identity.
  `scripts/game_data/buff_c7_native.json` pins header-twelve HitStop:
  common prefix, DWORD, target, payload, curve, raw4, target, raw GameplayTag
  DWORD and byte. GameplayTag has no object header at this call. Curve header3
  owns raw8 and a nullable raw28-element array; keep independent null states,
  target unknown stops and required tail, without hit-stop behavior claims.
  `scripts/game_data/buff_19b_native.json` pins header-fourteen Vulnerable
  and its KeywordEnhanceEdit list. Each header-three element owns a nullable
  byte-payload list, DWORD and scalar profile. Reserve at least eight bytes
  after the outer list and five after the inner list; null wrappers, null/empty
  lists and null payloads remain distinct. The post-list scalar precedes two
  targets and the required DWORD; keyword and vulnerability meanings remain
  unresolved independently of these structural boundaries.
  `scripts/game_data/buff_128_native.json` pins header-eleven RecoverPoise:
  common prefix, byte, EffectActionCfg, DWORD, byte, DWORD, CalculationBase
  and target. Reuse the bounded member85 configuration and calculation union
  profiles; unknown calculation variants stop before their tag, and the final
  target remains required after both children complete. Poise and calculation
  meanings stay unresolved independently of this framing.
  `scripts/game_data/buff_164_native.json` pins header-four SkillAffixAction:
  only the common byte and three DWORDs, with no additional nested fields.
  Extended normal records consume seventeen bytes; FF wrappers consume four.
  The final DWORD remains required, while skill-affix meanings stay unresolved.
  `scripts/game_data/buff_cf_native.json` pins header-eleven IgniteBuffText:
  common prefix, DWORD, byte, DWORD, raw8, byte, target and byte payload.
  The Vector2-context helper consumes eight raw bytes without a wire header;
  preserve its bits and require the final payload length after a null target.
  Text behavior and payload encoding remain unresolved.
  `scripts/game_data/buff_12b_native.json` independently pins header-four
  RefreshBuffAttrModifierValue to the common byte and three DWORDs.
  Its short-tag counterpart is a different action; shared field widths do not
  establish shared runtime behavior or attribute semantics.
  `scripts/game_data/buff_2c_native.json` pins header-fourteen ChangeSkill:
  two scalar-payload profiles precede the byte/DWORD/payload fields and target.
  Exact generic contexts distinguish BlackboardDouble from TargetSettings;
  the byte and final payload length remain required after a null target.
  Skill-switch, lifetime and slot behavior remain unresolved.
  `scripts/game_data/finder_00_native.json` joins finder tag 0 to the
  AbilityEntityTargetFinder wrapper: zero union tag and zero object header
  are separate required bytes, followed by no fields. The parent selector
  still requires both postprocessor and validator counts. Target selection
  and ability/entity ownership remain unresolved.
  `scripts/game_data/finder_01_native.json` pins finder 1 to a zero-member
  wrapper. Its constructor consumes no source fields; short/extended tags,
  member-zero wrappers and FF nulls remain distinct. AllEnemyFinder identity
  does not prove runtime enemy ownership or selection.
  `scripts/game_data/finder_10_native.json` pins finder 16 and its nested
  Vector2 reader. Member nine consumes scalar, Vector2, Vector3, three scalars,
  DWORD and two bytes; Vector2 independently contains two scalar payloads.
  Nulls and lengths remain independent, and both terminal bytes are required.
  Static type identity does not prove coordinates or runtime random selection.
  `scripts/game_data/finder_0e_native.json` pins selector-finder union 14 to
  a member-two PointFinder reader with two independent vector payloads. Shared
  type context does not merge their null states or length boundaries. The
  second vector ends the record; position/direction meanings remain unresolved.
  `scripts/game_data/finder_15_native.json` independently joins selector-finder
  union 21 to a member-zero SourceFinder reader. It has no serialized members
  or nested providers; runtime source-entity selection remains unresolved.
  `scripts/game_data/finder_0a_native.json` independently pins selector-finder
  union 10 to a member-zero reader. It consumes no fields after its header;
  constructor initialization adds no source bytes. Keep finder, validator and
  action tag spaces distinct. Main-target runtime selection remains unresolved.
  `scripts/game_data/buff_8e_native.json` pins a member-five body ending
  in an independent BlackboardDouble profile after the common byte and three
  DWORDs. Its null state and payload length remain local; the parent completes
  only after the profile's final four bytes. ATB cost and cooldown selection
  remain unresolved runtime meanings.
  `scripts/game_data/buff_52_native.json` pins a fixed member-five body:
  byte, three DWORDs and a final byte. It has no nested provider or variable
  count. The final byte remains required for every non-null wrapper, regardless
  of its value; raw scalar bits do not become counts or lengths. Squad combat
  state and runtime condition evaluation remain unresolved.
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
  `scripts/game_data/buff_132_native.json` and `buff_13a_native.json` pin
  separate extended member-six actions ending in two independent byte payloads.
  Their shared parser retains distinct union identities. Preserve both signed lengths
  and null/empty states; the parent completes only after the second payload.
  Payload encoding, ATB-value and collected-value ownership remain unresolved.
  `scripts/game_data/buff_6b_native.json` instead ends a member-seven action
  with three independent byte payloads. The third signed length is mandatory;
  completed earlier payloads remain recorded when a later payload is incomplete.
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
  `scripts/game_data/buff_188_native.json` pins paired and scalar profiles
  followed by two independent targets. Equal member-three headers do not make
  the first two profiles interchangeable: exact contexts select their distinct
  payload tails. The second target is mandatory; custom-event behavior remains unresolved.
  `scripts/game_data/buff_187_native.json` instead consumes an AssignPair
  list, byte and three targets. Its list reuses the member-six assignment reader;
  reserve the byte and three minimum target headers when checking the count.
  Each target is independent, and combo-skill meaning remains unresolved.
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
  `scripts/game_data/buff_41_native.json` pins a member-six action
  ending with a byte payload and GameplayTagQuery. Its explicit output-pointer
  ABI and sixteen-byte result do not establish wire width; preserve bounded
  query counts. Damage transfer meaning and tag interpretation remain unresolved.
  `scripts/game_data/buff_63_native.json` uses that same bounded query directly
  after the common prefix in a member-five action. Its output copy adds no wire
  fields; preserve distinct null-query, null-array and empty-array states.
  `scripts/game_data/buff_77_native.json` pins a terminal counted-DWORD list.
  Its enum element width is supported by explicit unmanaged-formatter registration,
  underlying-type normalization, a generic lookup retry and the canonical Int32
  source reader. Absence of an enum-specific MethodSpec does not justify selecting
  a shared reader without that chain; live provider selection remains conditional.
  `scripts/game_data/buff_a9_native.json` pins a member-28 action with
  independently nullable targets, curve, direction and scalar profiles. Its
  BlackboardImpactValue reader reuses the member-four payload/byte/DWORD/byte
  grammar; the dedicated enum helper consumes one byte. Hurt behavior remains unresolved.
  `scripts/game_data/buff_62_native.json` and `buff_13c_native.json` pin distinct
  member-four actions ending immediately after their common byte and three DWORDs.
  Preserve the latter's extended union encoding. Do not append a nested
  payload from the type name; damage skill-cast identity meaning remains unresolved.
  `scripts/game_data/buff_90_native.json` pins two independent BlackboardInt
  profiles before a byte and final target. Their payload/byte/DWORD grammar
  reuses the concrete Int reader; shield counts and UI behavior remain unresolved.
  `scripts/game_data/buff_bb_native.json` pins two independent targets after
  the common fields, without an intervening byte or extra tail. A failed second
  target preserves the first completed target; combat forcing remains unresolved.
  `scripts/game_data/buff_0b_native.json` distinguishes a direct GameplayTag
  list from the GameplayTagList wrapper. Its counted FF/member-one elements
  follow a string profile and target; reserve the required final byte before
  accepting the count. Tag meaning and runtime selection remain unresolved.
  `scripts/game_data/buff_40_native.json` ends a member-six action with a
  DWORD and that same direct element list. Preserve each element header; the
  QueryType context belongs to the preceding DWORD, not an extra query wrapper.
  Null list, empty list and null elements remain distinct; tag meaning is unresolved.
  `scripts/game_data/buff_2b_native.json` pins a member-five action ending
  immediately after one BlackboardDouble profile. Reuse the independently
  authenticated payload/byte/four-byte reader; its managed name does not
  establish an eight-byte value or energy semantics.
  `scripts/game_data/buff_115_native.json` pins a member-sixteen action whose
  nested sequence is followed by two four-byte values, payload and final byte.
  Keep that outer tail mandatory after a null or complete sequence; unknown
  children leave the outer action incomplete and retain their original offset.
  `scripts/game_data/buff_151_native.json` pins a member-eight action with a
  sequence, two independently bounded scalar profiles and final byte. Retain
  completed children when a later profile fails; neither a null sequence nor
  a null first profile permits omitting the remaining members.
  `scripts/game_data/buff_13f_native.json` pins payload, target and a final
  DWORD after the common fields. Its ValueType context belongs to that DWORD
  helper; it adds no nested header and does not establish a one-byte enum.
  Preserve a completed target when the final four bytes are truncated.
  `scripts/game_data/buff_139_native.json` ends immediately after payload
  and target, with no scalar tail. Preserve their independent null states and
  completed payload evidence when the target fails; character-type meaning is unresolved.
  `scripts/game_data/buff_135_native.json` places one BuffId profile before
  target and a final byte payload. Its exact value-type context reuses the
  member-one payload reader without a list count or implied raw value width.
  Preserve each null state and completed child on later failure; no source
  tail follows the last payload. Stack-count ownership remains unresolved.
  `scripts/game_data/buff_122_native.json` closes a nullable list after the
  common fields. Each member-four element reads scalar profile, payload,
  target and payload, with no element or outer tail. Bound the count using
  the null element's one-byte minimum; retain completed elements when a later
  element fails. The concrete element reader establishes source order, while
  shared list dispatch and skill-setting ownership remain unresolved.
  `scripts/game_data/buff_140_native.json` pins a payload followed by two
  independent targets with no extra tail. A completed first target remains
  evidence when the second fails; either null target still consumes its own
  marker and does not eliminate the other member.
  `scripts/game_data/buff_18a_native.json` places a DWORD before two
  independently nullable scalar profiles. Both exact Double contexts reuse the
  payload/byte/four-byte reader; their shared context does not merge instances.
  Preserve the second profile boundary and leave UI-event meaning unresolved.
  `scripts/game_data/buff_98_native.json` pins payload, curve, scalar profile,
  payload and final byte after the common fields. A null curve differs from a
  null key list; bound the key count before reading raw keys, and retain the
  mandatory outer payload/byte after the nested profiles complete.
  `scripts/game_data/buff_183_native.json` has two independent target lists
  separated by a byte, with a scalar profile before the first and after the
  second. Reserve the remaining minimum tail before either count-driven loop.
  Three DWORDs follow the second scalar, then a curve and two required bytes;
  the two GameplayTag reads use raw DWORD source advances without headers.
  Preserve null lists, completed targets and all terminal bytes. Time-dilation
  ownership remains unresolved despite the selected reader's exact identity.
  `scripts/game_data/buff_176_native.json` closes a direct nullable list of
  member-two sequence/scalar profiles after the action's extra byte and scalar
  profile. The list has no additional object header; each non-null element
  consumes its sequence before its scalar profile. Null elements, null lists
  and null nested sequences remain distinct. Bound counts and recursive depth
  before consumption, preserve completed children on later failure, and never
  mark the incomplete option or action complete. The selected native reader
  proves this structure; live provider choice and switch meaning remain open.
  `scripts/game_data/buff_175_native.json` instead closes a member-five action
  with a terminal byte payload after the common scalar prefix. Its reader has
  no nested provider or further tail. Keep null and empty payloads distinct;
  a managed storage-oriented name does not establish text or enum semantics.
  `scripts/game_data/buff_fc_native.json` closes an extended-only member-six
  action with target then scalar profile. Accept its full extended union
  encoding while keeping the one-byte reserved marker unsupported. A completed
  target never makes the independently nullable final scalar optional.
  `scripts/game_data/buff_83_native.json` adds a DWORD and byte before that
  target/scalar pair. Its CompareType context is consumed by the DWORD helper;
  preserve the full raw width instead of inferring an enum byte or validating
  gameplay values from the managed type name.
  `scripts/game_data/buff_86_native.json` pins three independent scalar
  profiles with a byte payload between the first two and a mandatory final
  byte. Identical generic arguments do not merge serialized instances; each
  profile retains its own null state, length bounds and four-byte value.
  The member-nineteen child adds counted input profiles containing counted
  assignment profiles, a scalar/byte-payload pair, and the existing scalar,
  byte-payload-list and target profiles. Preserve the native read order rather
  than destination offsets: helper calls also consume scalar and byte members.
  `scripts/game_data/buff_92_native.json` pins these readers, nested contexts,
  the assignment-list candidate and the selector finder's zero-member route.
  `scripts/game_data/buff_93_native.json` independently joins another action to
  the same source order and nested type arguments, allowing one shared parser
  branch while retaining separate union identities. Its ActionTargetType is a
  DWORD helper read, not a nested object. Both lists must reserve later fields,
  and completed input profiles never make a missing final target acceptable.
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
