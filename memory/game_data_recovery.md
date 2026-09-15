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
  DataMask and several record fields remains unresolved. The maintained
  `stream_area` gate rejoins current `FBStreamArea.bytes` files to the
  authenticated outer VFS ledger and requires the final vector to reach payload
  EOF; its six vector widths and one inline root field are framing evidence,
  not field names or runtime semantics. Current corpus details are in
  [`dynamic_stream_area_current_latest.md`](../reports/animestudio/dynamic_stream_area_current_latest.md).
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
  distinct from language voice-audio availability. The maintained
  `memorypack.lipsync_corpus` gate binds every current family identity to
  `AnimeStudio stream --verify-md5` bytes and requires the 15-member reader to
  consume each file through EOF; changing coverage totals stay in its generated
  report.
- NPC MontageNew JsonData has a bounded three-member root and 24-member body;
  member 3 and member 18 collections use explicit counts and nested member
  markers. Strings, scalar values and fixed record bodies stay anonymous. The
  `memorypack.npc_montage_corpus` gate joins current ledger identities to
  `AnimeStudio stream --verify-md5` bytes by path, length and logical MD5, then
  requires the maintained frame reader to consume supported records through
  EOF. Coverage totals belong in
  `reports/animestudio/npc_montage_current_latest.{json,md}`; exact framing does
  not establish field meaning or runtime use.
- SkillData's MemoryPack framing remains a structural prefix: the current
  corpus report preserves all valid EOF-anchored terminal candidates. Exact-
  build native evidence resolves the resource type as `Core.SkillData` and
  orders the first field as `actionGroupData`; its nested reader requests
  `passiveEventActions` followed by `timelineActions`. Current VFS branches
  cross-check those list counts and consumed prefix ranges. The empty-list
  nested endpoint `[1,10)` remains conditional on both generic formatter
  queries selecting the audited four-byte zero-count path. Provider/cache
  state and an executed cursor are not available offline, so this does not
  establish which formatter path ran or prove a parent record end. The
  exact-build offline audit now binds raw bytes
  for one terminal collision and branch samples covering every positive
  count shape of the three terminal lists to their current VFS identities,
  hashes and hard limits, then matches nested parser cursors and member order
  to registered static reader bodies. This includes the one-member
  GameplayTagList wrapper, its GameplayTag element reader, ToggleBuffData, and
  UIRangeHintData with its nested 21-member shape reader. The registered
  GameplayTag path consumes one member-count byte and a four-byte field; its
  `tagId` is `System.Int32`, while the parser preserves the same bytes as an
  unsigned id/hash view, so signed semantic interpretation remains open.
  Under these registered paths, the shifted tail fails either the wrapper's
  accepted-header path or the bounded list reader's remaining-byte check. This
  ranks the tail hypotheses offline, but provider/cache selection and an
  executed parent cursor remain unavailable, so no whole SkillData record is
  closed. A separate ActionGroupData branch probe conditionally matches a
  `passiveEventActions` AbilityActionMap element to its registered reader: an
  empty SequenceActionData array reaches the map's static end, while a
  nonempty sequence stops before its first non-null action-union payload. This
  does not close the parent list or ActionGroupData; bytes outside these
  sample-local ranges and before the terminal tail remain opaque.
  The report also verifies the observer's post-call return-address coordinates,
  which are hook locations rather than a live cursor receipt.
  Available TypeTrees do not cover these JsonData files.
  A bounded exact-build `skilldata-cursor` observer is available, but no receipt
  has yet verified a candidate. Cleanup now requires
  a post-disable thread-IP rendezvous over the detour and MinHook trampoline;
  incomplete enumeration, context reads, or thread resumption leaves the
  capture incomplete and transfers its owners to a cleanup worker that retries
  until teardown is proven or the process exits; later cleanup cannot upgrade
  the published receipt. Each cleanup attempt is bounded; a failed
  `ResumeThread` keeps its handle for later worker retries rather than dropping
  the cleanup responsibility.
  Keep candidates ambiguous until a loss-accounted
  receipt joins source bytes, start/end cursors, hard limit, and logical
  identity/hash to the same inputSet. Counts,
  hashes, and per-file ranges belong in
  `reports/animestudio/skilldata_current_latest.*` and
  `reports/animestudio/il2cpp_context_current_latest.*`.
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
  `memorypack.buff_1b_corpus` joins exact-closed root-continuation tag `0x1B`
  records to re-streamed current logical bytes and the exact-build selected
  `BlowOffAction_Data` reader contract. This keeps the action body anonymous;
  the continuation profile does not authenticate root-field ownership. Live
  provider selection, action semantics and whole-BuffData EOF remain unresolved.
  Changing coverage belongs in
  `reports/animestudio/buff_1b_current_latest.{json,md}`.
  `scripts/game_data/buff_184_native.json` joins TogglableAction to header6:
  the common prefix followed by two independent SequenceActionData records.
  Null or empty first sequences retain the second, and each count reserves
  its own two terminal bytes. Only Sequence-to-action entry increments depth;
  no extra outer byte follows the second sequence. The shared type argument
  proves neither activation/deactivation roles nor runtime execution order.
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
  Extended tag `0x15A` has a separate header-six order: byte, three scalar32
  values, the existing bounded paired-byte profile, then `TargetSettings`.
  `scripts/game_data/buff_15a_native.json` pins its native route and nested
  static types; remaining bytes stay opaque, and runtime provider selection or
  field meaning is not inferred.
  Extended tag `0x192` is another header-six reader: byte, three scalar32
  values, then two independent bounded byte payloads. Its selected native
  contract is `scripts/game_data/buff_192_native.json`; the Priority MethodSpec
  identifies only one scalar's static context. Payload text, field meaning,
  suffix ownership and whole-BuffData EOF remain unresolved.
  Short tag `0xBC` uses a separate header-six order: byte, three scalar32
  values, then two independently bounded `TargetSettings` profiles. Its native
  contract is `scripts/game_data/buff_bc_native.json`; the Priority MethodSpec
  identifies only the first scalar, while each target has its own exact static
  type join. Preserve the nested profiles' null and unsupported states. The
  observed suffix remains opaque; no field meaning or whole-BuffData EOF is
  established.
  Extended tag `0x14E` routes to `SetDamageTagImmuneRule_Data` and uses a
  header-six order: byte, three scalar32 values, `GameplayTagQuery`, then
  `TargetSettings`. Its native contract pins the outer route and contexts plus
  a type-identified query reader with a nullable count and bounded count-times-
  four-byte array. The array is raw fixed-width data; managed value semantics
  and live provider selection are not inferred. Preserve query/target null and
  failure boundaries, and leave following bytes opaque without suffix-ownership
  or whole-BuffData EOF claims.
  Short tag `0x0D` routes to `AirborneActionDataForMemoryPack` with a pinned
  header-16 source order in `scripts/game_data/buff_0d_native.json`. Its
  EffectActionCfg, DirectionSettings, BlackboardDouble and TargetSettings
  instances reuse their bounded profiles; typed DWORDs, direct bytes and raw
  four-byte reads retain only their observed source shapes. The selected reader
  endpoint leaves following bytes opaque and establishes neither field meaning,
  gameplay behavior, suffix ownership nor whole-BuffData EOF.
  Short tag `0xE0` routes to `LockCameraAimActionData` and has a 54-member
  source order pinned in `scripts/game_data/buff_e0_native.json`. Its nested
  AnimationCurve, BlackboardDouble and TargetSettings values reuse the bounded
  profiles above; raw vector copies and mount-point enum reads retain only their
  observed widths and static contexts. Leave the remaining suffix opaque: this
  contract does not assign gameplay meanings, suffix ownership or whole-BuffData
  EOF.
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
  `scripts/game_data/buff_91_native.json` reuses that ColliderShapeData before
  a required TargetSettings in CreateAdditionalBattleShape. Its header10
  consumes the common prefix, raw float32 bits, three bytes and both nested
  records. Each child may be null independently; the target is terminal.
  Short91 and FA9100 select the same union. Static identity and source order
  do not establish battle-shape creation behavior or anonymous field meaning.
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
  `scripts/game_data/buff_df_native.json` joins LaunchUpwardAction to header15:
  common prefix, effect, DWORD, direction, two Double profiles, raw4, DWORD,
  target, raw4, target and a required terminal byte. Enum contexts select the
  DWORD helpers, not the following nested calls. Preserve both Double/Target
  instances and both raw float spans even when adjacent profiles are null;
  upward-launch behavior, numerical units and target roles remain unresolved.
  `scripts/game_data/buff_1f_native.json` independently joins BombTouchLayerAction
  to three sequence instances, two effect configurations and one target among
  scalar members. Its LayerMask helper consumes one DWORD without a nested
  header; both mask reads remain required, including the terminal DWORD after
  the second effect. Preserve each sequence's count, depth and two tail bytes.
  Repeated type contexts do not merge source spans or establish activation
  roles; collision behavior, layer-bit meanings and effect ownership remain
  unresolved independently of the exact static identity and direct read order.
  `scripts/game_data/buff_b7_native.json` joins FlowTextAction to header nine:
  common prefix, raw16, byte, DWORD, target and terminal byte payload. Its
  inline sixteen-byte copy and Advance call share an explicit remaining-byte
  guard; pin the separate ensure-input rejoin without claiming refill parity.
  MountPoint selects the DWORD helper. A null target does not remove the final
  length word, and FF bytes inside raw16 are ordinary data. Raw16 meaning,
  payload encoding, text rendering and target ownership remain unresolved.
  `scripts/game_data/buff_f0_native.json` independently pins a member-five
  scalar-ending action. Its BlackboardDouble context reuses the bounded
  payload/byte/raw4 profile, not an eight-byte scalar. Null and empty payloads
  retain both tail fields; null scalar, null wrapper and null union differ.
  Equal source order permits parser reuse while preserving separate union
  identities. Resilience behavior, numeric interpretation and units remain
  unresolved; no extra outer payload follows the output setter.
  `scripts/game_data/buff_55_native.json` pins a member-nine condition with
  one BuffId value, two independent TargetSettings instances, a byte and a
  terminal scalar profile after the common prefix. BuffId uses its own
  nullable member-one payload wrapper; its output carrier width does not
  establish wire width. Equal target contexts preserve separate byte ranges.
  Null preceding profiles retain the byte and final scalar. Source/target
  ownership and condition behavior remain unresolved.
  `scripts/game_data/buff_36_native.json` pins three independent
  AnimatorParamAction instances around an outer raw4/byte span and a terminal
  DWORD. Each nullable child reuses the member-five fixed profile in
  `buff_14a_native.json`; identical contexts do not merge source ranges or
  remove intervening fields. Preserve all floating bits and the final DWORD
  even with null children. Weapon animation and parameter roles remain unresolved.
  `scripts/game_data/buff_20_native.json` pins BreakoutAction to a member-six
  order: common prefix, signed-length byte payload and terminal DWORD. Null
  and empty payloads retain that DWORD; neither output setter adds a nested
  record. The final static context joins AbnormalState without proving its
  value meanings or runtime effect. Keep payload encoding and breakout behavior
  unresolved, and preserve the opaque physical remainder after root framing.
  `scripts/game_data/buff_a8_native.json` pins a nullable ShapeEdit list before
  TargetSettings and a terminal DWORD. Its independent element union accepts
  tag zero as a nullable member-three Sector wrapper: DWORD, scalar payload,
  scalar payload. The two Double contexts establish separate variable-width
  profiles; the generic helper alone cannot identify either as a target.
  Reserve the following target and DWORD when bounding the list, and stop
  unknown element tags at their first byte. Aim geometry and units remain unresolved.
  `scripts/game_data/buff_23_native.json` joins BroadcastAlertToCharactersAction
  to a member-eleven order: common prefix, SkillAlertData, two DWORDs, byte
  payload, DWORD, raw4 and TargetSettings. SkillAlertData is FF or header9
  followed by raw4 three times, DWORD, raw4 four times and DWORD. Preserve
  nine separate four-byte spans; AlertMoveType and AlertShape contexts identify
  the DWORD carriers, not their value meanings. Null alert/payload values do
  not remove the final target. Alert geometry, units and broadcast behavior
  remain unresolved; exact static identity does not prove runtime selection.
  `scripts/game_data/buff_16a_native.json` pins SpawnEnemyAction to three
  independent targets around raw12, DWORD, raw16, a nullable CreateBuffActionInput
  list, two byte payloads, byte, scalar payload, raw4 and byte. Vector3 and
  Quaternion helpers prove their separate source guards and advances; output
  sizes alone are insufficient. List elements reuse the member-five input
  profile and its nested AssignPair list from `buff_92_native.json`, with
  distinct null/empty states and terminal reserves at both list levels.
  Spawning behavior, target ownership and coordinate/rotation conventions remain
  unresolved; the final target is required even when preceding lists are null.
  `scripts/game_data/buff_6f_native.json` joins CheckProfession to a member-six
  order: common prefix, TargetSettings and a terminal DWORD. Reuse the bounded
  target profile; a null target does not remove the final four source bytes.
  The last static context identifies ProfessionCategoryMask, but its bit
  meanings and runtime profession checks remain unresolved.
  `scripts/game_data/buff_161_native.json` joins ShowSquadTipsAction to a
  member-five reader: common prefix and one signed-length byte payload.
  Null and empty payloads stay distinct; no terminal scalar follows them.
  The extended union identity remains separate from the short low-byte tag.
  Payload encoding, text/identifier role and actual tip behavior remain unresolved.
  `scripts/game_data/buff_c0_native.json` extends the existing GainCost identity
  join to header7: common prefix, CastData.CostData and two terminal DWORDs.
  CostData is FF or header3 followed by raw4, DWORD and raw4. Its exact generic
  context selects this child despite sharing a helper address with TargetSettings.
  CostType and the two separate ActionTargetType contexts add no nested headers.
  Preserve raw bits and both terminal DWORDs when CostData is null; cost units,
  enum meanings and runtime effects remain unresolved.
  `scripts/game_data/buff_11c_native.json` pins PullAction's member19 order,
  including a nullable PullAttenuationValueConfig list, two independent targets
  and a required final byte. Each list element is FF or header2 with raw4 and
  BlackboardSuperArmorValue, whose member4 payload/byte/DWORD/byte profile
  reuses `buff_159_native.json`. Reserve the outer tail when bounding the list.
  Its large inline initialization and jump-table data remain distinct from
  source reads; output getters/setters add no wire members. Pull behavior,
  attenuation units and live list-provider selection remain unresolved.
  `scripts/game_data/buff_8c_native.json` pins ConvertToTargetContext's member12
  order: common prefix, Vector3, TargetSettings, two DWORDs, byte payload,
  DWORD, raw4 and final DWORD. Vector3 retains three independently nullable
  scalar profiles from `buff_b2_native.json`; it is not a raw coordinate triple.
  Null vector, target or payload never removes the twelve-byte terminal region.
  Operation enum contexts consume DWORDs without additional object headers.
  Coordinate conventions, target roles and conversion behavior remain unresolved.
  `scripts/game_data/buff_4e_native.json` pins ComboCacheAction's member5
  terminal list of BattleCmdMappingModifierData. Each element is FF or member6:
  byte, scalar payload, byte, DWORD, byte and an independent byte payload.
  Bound the list with a one-byte minimum element; it has no outer tail.
  A null scalar does not remove the element's final payload, and a null list
  is distinct from an empty list. Command mapping behavior and payload roles
  remain unresolved; the list provider bridge stays conditional.
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
  `scripts/game_data/buff_197_native.json` joins VoiceInterruptAction to a
  fixed header6 profile: common prefix, required DWORD and terminal BYTE.
  All bit patterns remain anonymous; neither an all-zero nor an all-FF scalar
  removes the terminal byte. Short97 is not the FA9701 union. Runtime voice
  interruption and scalar/flag meaning remain unresolved.
  `scripts/game_data/buff_198_native.json` joins VoiceTriggerAction to header11:
  the common prefix, two DWORDs, a nullable payload, two DWORDs, another nullable
  payload and terminal TargetSettings. Both length markers and the final target
  remain required for null/empty payloads. VoSpeakerType identifies a context,
  while voice behavior, payload encoding and speaker/target ownership remain
  unresolved. Short98 is a distinct union, not an alias for FA9801.
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
  `scripts/game_data/buff_16c_native.json` pins current union364 SpeedupAction:
  header13, common byte/three DWORDs, byte/byte, paired payload, scalar
  payload, nullable KeywordEnhanceEdit list, byte, scalar payload and two
  terminal TargetSettings. The outer list reserves four trailing bytes and
  permits one-byte elements; each nonnull element reuses the 19B header-three
  reader and its nullable payload list, DWORD and scalar profile. The second
  target ends this reader with no DWORD tail. Preserve null/empty states;
  payload decoding, gameplay meaning, live generic-provider choice and full
  BuffData EOF remain unresolved.
  `scripts/game_data/buff_85_native.json` pins decimal union tag 133 (`0x85`)
  to the `CompareDeckAttr` header10 reader. After the shared byte/three-DWORD
  prefix, it reads two DWORDs, a scalar payload, a DWORD, another scalar
  payload and a terminal `TargetSettings`. Exact MethodSpec joins identify
  `Priority`, `CompareType`, `DeckAttrOperand`, `BlackboardDouble` and
  `TargetSettings`; the context-free DWORDs remain raw, and enum values,
  condition semantics, runtime provider selection and whole-BuffData EOF
  remain unresolved. The scalar and target children reuse their existing
  finite structural readers.
  `scripts/game_data/buff_94_native.json` pins decimal union tag 148 (`0x94`)
  to the header-seven CreateDynamicBattleShape reader. After the common
  byte/three-DWORD prefix, it consumes two float32 reads and a terminal DWORD.
  MethodSpec contexts identify Priority and DynamicBattleShapeType; remaining
  scalar slots stay anonymous and float bits remain raw. No child profile or
  gameplay meaning is inferred; provider selection, enclosing ownership, and
  whole-file EOF remain unresolved.
  `scripts/game_data/buff_158_native.json` pins decimal union tag 344
  (`0x158`) to the header-ten SetStrafeModeAction reader. After the common
  byte/three-DWORD prefix it consumes two bytes, two DWORDs, bounded
  TargetSettings, and a required four-byte float read retained as raw bits.
  MethodSpec contexts identify Priority, GroundedMoveGait twice, and
  TargetSettings; the other scalar slots remain anonymous, without enum-value
  or gameplay claims. Provider selection, enclosing ownership, and whole-file
  EOF remain unresolved.
  `scripts/game_data/buff_179_native.json` pins decimal union tag 377
  (`0x179`) to the header-nine TagQueryListenerAction reader. After the common
  byte/three-DWORD prefix, the selected reader consumes bounded
  GameplayTagQuery and SequenceActionData profiles, then an anonymous byte and
  two raw DWORDs. MethodSpec joins identify the nested types but do not establish
  enum ordinal meanings, gameplay behavior, active generic-provider selection,
  enclosing ownership, or whole-BuffData EOF.
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
  `scripts/game_data/buff_0c_native.json` independently pins short tag `0x0C`
  to AddTagToEntities: header eight, common byte/three-DWORD prefix,
  BlackboardString, TargetSettings, direct List<GameplayTag>, terminal byte.
  Reuse the 0x0B list frame and conditional 0xC5 element reader; the distinct
  route/type identity does not establish provider selection or field meaning.
  Short tag `0x26` has a header-five order of byte, three anonymous scalar32
  values and the bounded `TargetSettings` profile. Its native route and exact
  nested type joins are pinned in `scripts/game_data/buff_26_native.json`;
  the first scalar's `Priority` context does not assign a field meaning.
  Runtime formatter/provider selection, suffix ownership and whole-BuffData
  EOF remain unresolved.
  Short tag `0x10C` has a header-six order of one byte, three anonymous
  scalar32 values, a signed-i32 length-prefixed byte payload, and one 4-byte
  Float32 bit pattern. Current VFS branch samples and the exact-build native
  reader close this action at the same byte boundary. Bytes after the action
  remain outside its frame and are accounted for only by independently bounded root
  reads or opaque ranges. See the current corpus report for the input-bound
  ranges; field meaning, suffix ownership and whole-BuffData EOF remain
  unresolved.
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
- Numeric HIRC type `0x03` Action bodies now have an input-set-bound structural
  cursor gate. It joins verified package hashes/chunks/physical sources to the
  authenticated outer ledger and reconciles per-bank with package totals;
  unsupported bodies stay unsupported. Exact framing does not establish
  operation names, field ownership, targets, runtime execution, selection, or
  audibility. Current corpus details belong in
  [`reports/animestudio/hirc_action_current_latest.md`](../reports/animestudio/hirc_action_current_latest.md).
- Numeric HIRC type `0x02` source prefixes have a companion current-corpus
  gate. The maintained parser bounds the 14-byte prefix and the optional
  plugin-type-`0x02` parameter range; the gate reconciles object counts and
  prefix-plus-opaque-tail body bytes per bank/package against the authenticated
  outer ledger. The remaining body stays opaque and has no full cursor claim.
  See [`reports/animestudio/hirc_type02_prefix_current_latest.md`](../reports/animestudio/hirc_type02_prefix_current_latest.md).
- Numeric HIRC type `0x04` bodies have a third current-corpus structural gate.
  It checks an anonymous one-byte-count/32-bit-entry candidate against declared
  body lengths and bank/package totals, preserving short bodies and trailing
  bytes as explicit failures or opaque tails. Its report binds the current CLI
  output-directory manifest and the exact intermediate bytes it parsed,
  separately from the outer audit's apphost fingerprint. Exact framing does not
  identify entry values, fields, Action relationships, runtime execution,
  selection, or audibility. Current corpus detail belongs in
  [`reports/animestudio/hirc_type04_u32_vector_current_latest.md`](../reports/animestudio/hirc_type04_u32_vector_current_latest.md).
- Numeric HIRC type `0x02` bodies are now consumed **whole** by a fourth
  current-corpus gate, which supersedes the prefix lane's opaque-tail
  statement without retracting it. After the bounded source prefix the
  maintained reader frames nine anonymous groups: two flag/count slot
  vectors, two parallel one-byte-key/value bundles (4- and 8-byte values), a
  selector-directed vector pair, a selector-directed fixed block, a fixed
  six-byte block, a nested property/group/state directory, and a counted
  entry list with counted 12-byte points. Every current body reaches its
  declared end with no trailing bytes. A one-dimension-at-a-time candidate
  sweep pins twelve of fourteen widths uniquely against whole-corpus exact
  closure; two stay unresolved and fail closed instead of guessing: group
  B's element width (no current body carries a nonempty vector) and group
  E's selector predicate (its two low bits never disagree, so bit0-only,
  bit1-only, and both-bits cannot be separated). The group A split between
  a shared mask byte plus 6-byte slots and no mask byte plus 7-byte slots
  rests on one counterexample object plus non-boolean trailing bytes under
  the rejected reading; treat it as the weakest link in the frame. Group
  letters, selector bits, keys, and values stay anonymous: exact
  consumption is not field ownership, source/effect/bus/parent identity,
  cross-object relationships, runtime execution, event selection, or
  audibility. Two things about this gate must not be over-read. The
  constraining checks are that framed body bytes equal the declared object
  bytes minus object ids and that every exact body ends at its declared
  end; the `exactCursorBytes + nonExactBodyBytes = bodyBytes` identity is an
  internal assert that cannot fail, because a short read is never labelled
  exact. And `failed = 0` is partly upstream luck: a malformed source prefix
  throws in the preceding prefix census and aborts the whole package, so it
  never reaches this lane as a counted failure. The lane now enforces its
  own result -- any failed, unsupported, or ambiguous body publishes
  `incomplete` and exits nonzero -- so a future client update that
  introduces a nonempty group B vector stops the gate instead of quietly
  lowering the number. Current corpus detail belongs in
  [`reports/animestudio/hirc_type02_body_current_latest.md`](../reports/animestudio/hirc_type02_body_current_latest.md).
- Those nine groups are **not** type-`0x02`-specific. Numeric HIRC type `0x07`
  reuses them with no source prefix and one terminal counted vector of
  four-byte anonymous references, and all 48,740 current objects / 3,572,927
  body bytes consume exactly. One maintained reader now frames both types, so
  the guards and the fail-closed rules cannot drift apart. Type `0x07` also
  corrected two things the type `0x02` corpus could not. The group I entry
  carries a **variable-size** anonymous key, not a fixed byte: type `0x02`
  bodies spend one byte on all 475 of theirs, so a fixed width survived that
  corpus and would have silently mis-framed exactly the 90 type-`0x07` objects
  that contain a wider key. And group E selector `0x01` appears with no
  extension, which disproves a bit-0 branch predicate — though that rests on
  4 objects out of 48,740, so treat it as thin. Selector `0x02` is still
  unobserved everywhere, so bit-1-only and both-bits-set remain tied and fail
  closed. Say the refactor result precisely: the type `0x02` **counts** are
  unchanged and its report diffs clean, but two **behaviours** changed on paths
  that corpus never exercises, so a fixture now pins a continued key on the
  type `0x02` path too. The key's five-byte cap and 32-bit range are inherited
  from the type `0x03` Action reader, not proven here; both lanes publish a
  `groupIKeyWidth_*` histogram so the widths actually witnessed stay auditable
  (today: only 1 and 2). Group B is still empty in every framed body of both
  types, so its element width stays unresolved, and both lanes now publish the
  same shared-framer residual list rather than each carrying a shorter one.
  Reference targets, container membership, ordering and selection are not
  claimed. See
  [`reports/animestudio/hirc_type07_body_current_latest.md`](../reports/animestudio/hirc_type07_body_current_latest.md).
- Numeric HIRC type `0x05` is the third type on the shared node frame: node
  groups, then a fixed 24-byte opaque block, one counted vector of four-byte
  anonymous references and one counted vector of eight-byte anonymous records.
  All 30,352 current objects / 3,652,971 body bytes consume exactly. The two
  terminal counts are **independent**: 130,591 references against 130,655
  records, and the reader publishes `referenceRecordCountMismatch` (39) so that
  per-object claim is a measurement in the report rather than prose nobody can
  check. Neither vector is a projection of the other and no relationship between
  them is claimed. When unifying lanes, keep each lane's own layout sentence and
  its own non-claims: collapsing them once silently dropped type `0x02`'s
  source-identity and cross-bank disclaimers and every lane's description of what
  its framer consumes, which the counts alone could not reveal. With three lanes sharing
  one framer, the maintained code now carries one census object, one metrics
  reader, one accumulator, one markdown renderer and one report publisher;
  adding a further type is a lane declaration plus a framer, and the shared
  residual list is published identically by every lane. Corpus detail is in
  [`reports/animestudio/hirc_type05_body_current_latest.md`](../reports/animestudio/hirc_type05_body_current_latest.md).
- The shared node frame's group H **state is variable-length**: a four-byte key
  plus its own `u16`-counted vector of six-byte elements. A fixed twelve bytes
  survived three whole corpora because every one of their 1,546 states carries
  exactly one element; type `0x09` bodies carry two and disprove it. This is the
  second latent fixed width of the same class, after the group I variable-size
  key. Within the field family `{key, count at +4, count elements, fixed tail}`
  the six-byte element is forced, not fitted: a `u32` count would make the
  two-element sample declare 65,538 elements, and widths 3, 4 or 12 contradict
  the count the one-element sample carries. That uniqueness is only inside that
  family -- a fixed twelve-byte state followed by a separately gated six-byte
  structure is **not** excluded, which is precisely the failure mode being
  corrected, so the census carries it as a residual. Note also that the shipped
  reports alone cannot settle this: every state they publish is one element wide,
  and the only non-degenerate witness is type `0x09`, which is not a shipped
  lane. Take the pattern seriously: a width that a
  one-dimension sweep reports as
  *uniquely determined* can still be a degenerate case, because uniqueness is
  only ever over the shapes the corpus happens to contain. Both lanes now publish
  `groupHStateWidth_*` and `groupIKeyWidth_*` histograms so the degenerate case
  is visible rather than inferred, and the gate requires each histogram to match
  both its count and its byte total. Type `0x02`, `0x05` and `0x07` still close
  exactly after the correction, so no published count changed.
- Numeric HIRC type `0x09` is **not** a closed lane and is deliberately not
  shipped as one. Its bodies are the shared node frame, a counted four-byte
  reference vector, a counted layer vector and one trailing byte, where a layer
  is a fifteen-byte header plus a counted list of per-reference twelve-byte graph
  points. That frames 5,154 of 5,158 current objects. The other 4 carry a
  nonempty `u16`-counted sub-list inside the layer header that the rest never
  exercise, and its element width cannot be separated from the surrounding
  fields without guessing, so the grammar stays unresolved rather than being
  fitted to four samples. Do not publish a type `0x09` lane until those four
  parse; the gate would refuse it anyway.
- **That 5,154 grammar is documented here but not implemented anywhere, and this
  prose is not enough to rebuild it.** A later attempt re-derived type `0x09` from
  scratch with a validated node-frame mirror and reached only 4,982 bodies at
  best, after sweeping 48 layer-grammar variants (header widths 8..23 against
  fixed, single-counted and per-reference point lists). None reproduced 5,154. If
  the layer grammar is revisited, **write it down as field widths and offsets or
  as code**, not as a sentence -- a number in a note that nobody can reproduce is
  worse than no number.
- What that attempt did confirm independently: the shared node frame opens **all
  5,158** type `0x09` bodies, and after it come a counted run of four-byte
  entries and a second count. Where the second count is zero, one further byte
  closes the body exactly -- 4,973 bodies, 308,489 of 344,190 bytes, now gated and
  tested in the reader. The other 185 are fenced. **This shipped census is
  deliberately weaker than the 5,154 recorded above**; it is what is verified in
  code, not the best reading anyone has had.
- **Layer 4 opens for audio.** The anonymous four-byte values inside the exactly
  framed terminal vectors of numeric types `0x04`, `0x05`, `0x06` and `0x07` are object
  identities. All 230,247 of them resolve, every one to exactly one HIRC object
  declared by the **same bank**: zero unresolved, zero crossing a bank or package
  boundary, zero self references, zero targets carrying more than one referrer,
  zero framed entries that never reached the census, and zero nodes on or feeding
  a cycle, at a longest traversed chain of 7 references (8 objects). Every one of
  those numbers is computed and published by the maintained reader; none is prose.
  Numeric edge counts and a per-type referenced-versus-population table are in
  [`reports/animestudio/hirc_reference_graph_current_latest.md`](../reports/animestudio/hirc_reference_graph_current_latest.md).
  Seventeen object ids repeat inside a bank, 17 distinct ids over 17 repeat
  occurrences, so each appears exactly twice; **no reference targets a duplicated
  id**, so that ambiguity does not touch the claim.
- Numeric HIRC type `0x06` is the fourth type on the shared node frame: node
  groups, a fixed ten-byte opaque header, one counted four-byte reference vector,
  one counted group list where each group carries a four-byte key and its own
  counted vector, and one counted vector of fourteen-byte records. All 4,573
  current objects / 1,334,519 body bytes consume exactly, and every suffix width
  is uniquely determined by whole-corpus closure.
- Type `0x06` is also where the reference join first had to say no. Only its
  child vector resolves completely (20,290/20,290). Of the other framed words,
  432 of 22,234 group items and 573 of 20,863 record leading words match no
  object in their bank, so those words are **not** established as identities and
  are not joined. Excluding them silently would have been cherry-picking -- a 98%
  rate reported as 100% -- so the census publishes them as `candidateWords` with
  the number that do match, and the gate requires that count to cover every
  framed word held out. The gate caught this: the first attempt claimed all three
  vectors as references and failed with 1,005 unresolved. Believe the counter and
  narrow the claim, never the reverse.
- **Bank ids are named too, and media ids are not -- both measured.** Applying the
  same coincidence arithmetic to id populations other than HIRC objects: 175 of
  20,873 bank ids are named by shipped literals (1,448x chance), while **0 of
  61,333 media ids** are, against an expectation of 0.36. So the identifier chain
  ends at an opaque media id and does **not** continue into a filename; do not go
  looking for one.
- None of the named bank ids is also a HIRC object id, so bank names and event
  names are different strings rather than one name reused across both.
- **Sixteen HIRC types match no literal at all**, and that zero is now measured
  rather than assumed: `0x03`, `0x05`, `0x06`, `0x07`, `0x09`, `0x0A`-`0x0E`,
  `0x10`-`0x14`, `0x16`. Their ids are not hashes of any string this build ships,
  so their anonymity is a property of the data, not a gap in the search. Only
  `0x04`, `0x08` and `0x15` carry names.
- **Naming now extends past type `0x04`, and the test is a computed coincidence
  rate rather than a vocabulary.** The prefix filter (`au_`/`bark_`/`radio_`/`vo_`)
  exists because unfiltered literals resolve generic words by chance -- sound
  reasoning that cannot be checked from inside the filter. Dropping the vocabulary,
  keeping a structural identifier shape, and using the shipped folded hash
  (`AudioHashGenerator`, which lowercases A-Z) gives 24,868 literals and a
  measurable answer.
- Because the hash is 32 bits, chance is computable: a literal hits a type by
  chance with probability `population / 2**32`. Observed against expected:
  `type15` 4 matches on 5 objects (**138,000x** chance), `type08` 3 on 161
  (**3,218x**), `type04` 204 on 22,910 (**1,538x**), `type02` 2 on 142,815
  (**2.4x** -- its own coincidence rate).
- So type `0x02` is reported and **not** claimed, which is the point of the test:
  its two matches read like names (`on_threst_timer_finish`) and are noise. The
  gate requires the bar to be applied to every type, not just the convenient ones,
  and refuses a pass where nothing clears it.
- Concretely gained: type `0x04` goes from 151 to **204** named objects, and two
  new types get names -- `type08` (`Character`, `Effect`, `object`) and `type15`
  (`SYSTEM`, `System_3D`, `Controller_Speaker`, `Wwise_Motion`), the latter naming
  **4 of its 5 objects**. The type `0x15` names are device-shaped and the `0x08`
  names bus-shaped, but that is an observation about the strings, not a claim
  about what either type does.
- The narrow prefix claim is untouched and still gated separately, so widening the
  filter cannot weaken it.
- **An audit of the published wording found the over-generalisation had spread.**
  After correcting the cross-bank claim in these notes, the same claim was still
  sitting in two published reports, and one of them contradicted a table twenty
  lines above it. Both are now scoped: the reference-graph report says its
  same-bank result is a fact about *those counted vectors*, not the corpus, and
  says plainly that names do exist for some endpoints. The named-reach report says
  its "all on type `0x04`" result is a fact about *those literals*, not the format,
  since the broad pass in the same module names `0x08` and `0x15`.
- **When a conclusion is corrected, grep for where else it was asserted.** A
  correction recorded only in memory leaves the wrong sentence in every report and
  docstring that repeated it, and those are what a future reader actually reads.
  The tests now pin the scoping rather than the old absolute sentence.
- One cross-check passed and is worth recording as passing: the five reached source
  ids that name no shipped media all come from plug-in ids the media partition says
  never name media (`00080001`, `00640002`, `00650002`). The media join and the
  identifier chain agree.
- **Correction: this corpus DOES contain cross-bank references.** The numeric type
  `0x03` target word leaves its bank routinely -- of 28,379 targets, 21,956 name an
  object in the same bank, **1,499 name one in another bank of the same package**,
  4,907 name nothing the package declares, and 17 are null. A Python probe that can
  see every package classifies 739 of those 4,907 as objects in a *different
  package*, so the relation crosses package boundaries too.
- This is not marginal and not a coincidence: a random 32-bit word lands on one of
  the 231,693 declared object ids about **1.53 times** across all 28,379 targets,
  against 2,238 observed crossings -- roughly 1,463x chance.
- **What was wrong was the generalisation, not the measurement.** The gated
  reference vectors of types `0x04`/`0x05`/`0x06`/`0x07` really are all same-bank,
  and that is still true. Recording it as "this corpus has no cross-bank evidence"
  extended a fact about those vectors to the whole corpus, and several notes in
  this file repeated it. Actions are a different relation and behave differently.
- The first body byte clearly matters -- `action_03` resolves 21,894 times in-bank
  while `action_04` resolves 17 times in 3,578 -- but it is **reported and not
  claimed as a decider**, because no class is clean the way the type `0x02`
  plug-in partition is. A rule here would be fitted rather than found.
- Targets outside the package are counted as outside rather than unresolved: the
  reader sees one package and cannot speak for the others. The gate asserts that
  the crossing is *observed*, so a future reader reporting zero cannot quietly
  restore the old conclusion.
- **The chain is closed end to end: shipped identifier -> media file.** 97 of the
  194 named identifiers reach at least one media file this corpus ships, reaching
  163 distinct files between them. The report lists them per identifier,
  so `au_int_erosion_sludge_recover_loop` resolves to 6 files, `au_int_box_touch`
  to 5, and so on.
- **The named-reach walk crosses banks now, and that was worth 14 identifiers.**
  It used to run once per bank, so any edge pointing at a sibling bank was counted
  as leaving and abandoned -- the same over-generalisation the type `0x03`
  classification exposed, except compiled in rather than written down. Walking the
  whole package at once takes reaching-a-source from 109 to 120, source ids from
  181 to 218, identifiers reaching media from 83 to 97, and distinct media from
  150 to 163. Abandoned edges drop from 102 to 47, so more than half of them were
  sibling-bank all along.
- The counter is now `walkEdgesLeavingThePackage`, not `...TheBank`. Renaming it
  mattered: a package-wide walk reporting "edges leaving the bank" would have
  described itself in the vocabulary of the bug it just fixed.
- Matched objects (199) exceed distinct identifiers (194) because 5 named objects
  are declared in two packages each. That is expected, not a defect -- the gate
  checks identities never exceed instances, which is the direction that would
  indicate one.
- Five reached source ids name **no** shipped media, and that is reported per
  identifier rather than dropped, because the plug-in partition establishes that
  some source ids never name media at all. A reached id missing from the media
  table is an expected outcome here, not a defect.
- The named-reach walk now publishes the reached ids themselves, not just how many,
  and the gate requires the id lists and the counts to describe the same walk: a
  count with no list, or a list shorter than its count, stops publication.
- **The audio chain now reaches shipped media, and the plug-in id decides whether
  it does.** Joining the source id in a numeric type `0x02` bounded prefix against
  the media ids in the AKPK bank and sound sectors: 60,049 of 60,997 distinct
  source ids name a file this corpus ships, and 1,284 of 61,333 media files are
  never named.
- **Read the partition, not the 98% rate.** The outcome is decided entirely by the
  plug-in id, with no exceptions anywhere: `0x00040001` (51,889) and `0x00140001`
  (8,160) name shipped media in **every** case, and `0x00080001`, `0x00640002`,
  `0x00650002`, `0x00940002` and `0x01990002` name it in **none** (948 together).
  No plug-in id appears on both sides. The gate enforces that no plug-in id is
  split and that both sides are non-empty; a rate would have hidden the structure
  entirely.
- The low nibble does not explain it: `0x00080001` is type 1 like the two that
  always resolve, and never resolves. It is the whole 32-bit plug-in id that
  decides, so do not simplify this to "type 1 has media, type 2 does not".
- **Compute this join across the whole corpus, never per package.** A bank's media
  almost always lives in a *different* package: the same join done inside one
  package matches 12 of 75,958. The reader therefore reports the two id sets and
  the gate unions them, which is also why the reader carries no verdict here.
- Not claimed: what any plug-in id is, what the five that name no media do instead
  (generation and out-of-corpus media are both consistent with these bytes), or
  that any of it is ever decoded or played.
- **The serializer is on disk, and it is Wwise SDK v2023.1.17.** The shipped
  `Endfield_Data/Plugins/x86_64/AkSoundEngine.dll` (3,586,536 bytes, SHA-256
  `FD75D48813DC5B6497F0FD18B1AEE1912B8383FFA0AC229AD45A147A7ED052C6`) carries
  compiled-in assert paths naming its build tree. The string `wwise_v2023.1.17`
  occurs 28 times and is the **only** version string in the binary, so the
  identification is not an inference from bank version 150 -- it comes from the
  reader itself.
- Two build roots appear: stock `C:\Jenkins\ws\wwise_v2023.1.17\Wwise\SDK\...`
  and a vendored tree at `E:\Engine\RM42.Beyond\Audio\Wwise\SDK\...`. So the
  engine is Wwise 2023.1.17 with in-house modifications, and a stock-SDK layout
  should be treated as a strong prior rather than ground truth.
- **This retires the claim that the stuck cases are undecidable.** They are
  undecidable *from the bank bytes alone* -- that part stands, and the reasoning
  for each still holds -- but the deciding witness exists and is now named: the
  Wwise 2023.1.17 SDK headers define every HIRC struct exactly, which would settle
  `0x11`'s 21-versus-27 tie, `0x09`'s second run, `0x10`'s `0x7F` variant and
  `0x12` outright. That SDK is licensed from Audiokinetic and is not in this repo;
  obtaining it is a decision for the project owner, not something to work around.
- The DLL does **not** name the bank structures directly: its only chunk-tag
  strings are `BKHD`, `DIDX`, `DATA`, `HIRC`, `STID`, `STMG`, and it carries no
  `AkBankMgr`/`AkMusic*`/`AkParameterNode` source paths, so the asserts that would
  have named them are not compiled in. Do not expect to recover layouts by
  string-mining this binary; the version is what it gives you.
- **Numeric type `0x12` is the one HIRC type with no framing at all, and these
  readings are ruled out.** 251 bodies, 15,175 bytes. It is not the `0x10`/`0x11`
  grammar -- its word at offset 4 fails `range_section` on all 251. It is not the
  `0x16` shape (0 of 251). Chained counted blocks after a four-byte lead close only
  8 of 251 at any chain depth from 1 to 4.
- Its leading 32-bit word names a same-bank object in 132 of 251 bodies and names
  nothing in the other 119, so unlike types `0x08`, `0x0A`, `0x0C` and `0x0D` it is
  **not** a reference field and must not be gated as one.
- A "fixed 21-byte tail" reading looked convincing on two sample bodies -- the float
  `9a 99 c0 c2` sat exactly 21 bytes from the end in both -- and is **wrong**: only
  100 of 251 bodies have it there. Two samples agreeing on an offset is not
  evidence; this corpus has now punished that three times.
- What the end-aligned census supports as a *shape hypothesis* only: counting back
  from EOF, bytes -5, -4 and -3 are zero in every body, byte -6 takes seven small
  values, and bytes -12 and -11 look like the high half of a float.
- **The fixed-trailer reading that hypothesis suggests has now been tested and
  fails.** Sweeping every trailer width from 0 to 39 against a four-byte lead and
  a block chain of any depth, the best is 33 bytes explaining 143 of 251. So the
  bytes before the trailer are not a block chain, or the trailer is not fixed, or
  both.
- Four further readings are eliminated, bringing the total to eight. Group I does
  not appear: scanning every offset, only 34 bodies have one landing within eight
  bytes of EOF and those start at two fixed offsets, which is coincidence rather
  than structure. TLV records -- a key byte, a size of one, two or four bytes, then
  that many bytes, with zero to two bytes of padding -- reach 84 of 251 at best.
  And the length is not predicted by flags: the best single byte fixes it for 26%
  of bodies and the best pair for 26%, against 100% for the `0x0E` flag byte, so
  `0x12` is not a fixed layout with flag-gated optional parts either.
- Taken together these say the body is **not** a linear sequence of self-describing
  records, which is what every model tried so far assumed.
- **The size-field premise that suggested has now been tried too, and also fails.**
  Testing every offset 0..23 at 16 and 32 bits for a value that sizes a following
  region gives at best 30% agreement on the leftover; repeating it relative to the
  end of a one-, two- or three-block chain gives at best 33%. In both sweeps the
  "agreeing" leftovers cluster at 76/72/32 bodies, which is exactly the body-length
  histogram -- so the agreement is an artifact of a few common lengths, not a field.
  **Check a candidate field's hit distribution against the length histogram before
  believing it**; these two sweeps looked like 30% signal and were 0%.
- Ten readings are now eliminated. I have no further structural hypothesis for
  `0x12` that this corpus can test, and would rather say so than keep sweeping.
  The Wwise 2023.1.17 SDK would settle it outright; short of that, a genuinely new
  premise is needed, not another parameterisation of an old one.
- **Numeric types `0x13`, `0x14` and `0x15` are framed byte-exact: 18 bodies, 685
  bytes, all of them.** `0x13` and `0x14` are a counted block of four-byte values,
  a counted block of **eight**-byte values, then two bytes; keys and values are
  parallel runs in both, the same shape `0x16` uses. `0x15` instead shares the
  eight-byte header `0x10` and `0x11` use and closes with eight further bytes.
- **Treat these as weak claims and keep the witness counts in view.** Four, nine
  and five bodies is not a corpus -- plenty of layouts consume four bodies. What
  distinguishes the eight-byte second-block width from a four-byte one is that 6
  bodies actually carry a nonempty second block (11 entries in total), and the
  gate refuses a corpus where every second block is empty precisely so the width
  cannot pass unwitnessed. If these types ever grow, re-check the width first.
- They were only findable because the shapes were already known: the block came
  from `0x16`, the header from `0x10`/`0x11`. That is now four types closed by
  reuse rather than decode.
- **Numeric type `0x10` shares type `0x11`'s grammar exactly, and was never
  decoded separately.** Its header matched (`u16`, `u16`, `u32` size), so the
  existing grammar was tried and 430 of its 453 bodies closed at once. That is now
  the third time "check whether another type already closes this" paid off, after
  `0x16` reusing group I and `0x11` doing the same.
- The 23 `0x10` bodies that do not close all carry third byte `0x7F`, and group I
  fails to parse in their tail at every offset tried. They are fenced under their
  own reason, `type10_variant7F`, not blamed on the shared grammar. The reader
  applies that rule to type `0x10` only -- a `0x7F` third byte on a `0x11` body is
  normal, and a test pins that so the rule cannot leak across types.
- Both types now report through one census with a **named reason for every fenced
  body**, and the gate requires the reasons to account for every fence. A fence
  without a reason is indistinguishable from a body quietly dropped.
- **Numeric type `0x11` is framed for 2,553 of its 2,645 bodies (208,891 of
  213,491 bytes); the other 92 are fenced because a width genuinely ties.**
  Layout: an eight-byte header whose second word sizes an opaque section, one
  byte, the node frame's group I structure, a 16-bit flag, then a counted run of
  six-byte elements. Group I is reused, not re-derived -- the third type now to
  end with it, after `0x16` and the node-frame types.
- **The tie is the important part, and it must not be broken by picking.** When
  the flag is set an extra block appears, and two widths consume *every* flagged
  body exactly: 21 and 27. They are the same bytes read two ways -- 27 swallows
  the run's single element and reads a zero count, 21 leaves it as one element.
  The flag is never greater than 1 anywhere in the corpus, so no body can separate
  them; a body with flag 2 would, and none exists. This is underdetermined in the
  same sense as type `0x09`, not merely undecoded, so those 92 bodies are not
  framed at all.
- The gate for this type forbids failures outright and allows only the fenced
  outcome, which is counted separately from both success and failure. Fencing
  everything would make the claim vacuous and is rejected too.
  See [`reports/animestudio/hirc_reference_graph_current_latest.md`](../reports/animestudio/hirc_reference_graph_current_latest.md).
- **Numeric type `0x08`'s leading 32-bit word is null or names exactly one
  same-bank object -- never a non-null value that names nothing.** 161 bodies: 157
  resolve, 4 are null, 0 unresolved. Null is a real outcome for this type, so the
  gate permits it and forbids only the third case; an all-null corpus would make
  the claim vacuous and does not count as closed either.
- `0x08` is **not framed**, and here is how far it got so it need not be redone.
  After the leading word comes the same counted key/value block type `0x16` uses
  (a count, that many one-byte keys, that many four-byte values). After *that* is a
  one-entry list whose key byte sizes the value: key `0x15` is followed by 11
  bytes and key `0x1D` by 27, exactly 16 apart. A fixed signature
  `02 e8 03 00 00 00 00 c0 c2` then recurs in every tail. That accounts for
  148 of 161 bodies and stops there, so no lane.
- The other small types do **not** share `0x08`'s head. Their leading word names
  nothing in 119 of 251 `0x12` bodies, all 453 `0x10` bodies, and all 2,645 `0x11`
  bodies, so offset 0 is simply not a reference field for them. `0x12`'s first
  reference sits at offset 39 in a third of its bodies, which is the thread to
  pull there.
- **Numeric HIRC type `0x16` is framed byte-exact: 778 bodies / 16,635 bytes.**
  Layout: a byte count, then that many one-byte keys followed by that many
  four-byte values as **two parallel runs rather than interleaved pairs**, then one
  anonymous byte, then the node frame's group I structure verbatim.
- It closed fast because most of it was already proven. Group I is the same
  structure the reader frames byte-exactly on types `0x02`, `0x05`, `0x06` and
  `0x07`, so the only new part was the key/value block. **When a small type
  resists, check whether it ends with a structure another type already closes** --
  that is what turned this one from a decode into a ten-line framer.
- The parallel-runs detail is the one thing worth remembering about the block: an
  interleaved reading of key-then-value fails immediately, and the giveaway was
  that body length is exactly `4 + 5 * count` for the short bodies.
- `0x16` shares *only* group I, not the whole node frame, so it carries the group I
  residuals and none of the others. Its property keys and group I key widths are
  **per-element** selector families -- one observation per counted thing, not per
  body -- so they reconcile against their own counters rather than the body total.
  The lane framework now supports that kind of family explicitly; the first attempt
  bounded them by exact bodies and the gate correctly rejected it.
  See [`reports/animestudio/hirc_type22_body_current_latest.md`](../reports/animestudio/hirc_type22_body_current_latest.md).
- None of the small types `0x08`, `0x10`, `0x11`, `0x12`, `0x16` open with the node
  frame. `0x08` and `0x12` begin *with* a same-bank reference at offset 0 (157/161
  and 132/251), which is a different head from every type seen so far and is the
  obvious next thread.
- **The music types `0x0A`-`0x0D` are attempted and NOT framed. Read this before
  trying again.** They do not open with the shared node frame, and the ways they
  fail are per-type: at offset 0 the frame dies on `range_groupHStateElements` for
  `0x0A` (2,505/4,158) and `0x0D` (912/2,431), on `unsupported_groupB_nonempty`
  for `0x0B` (4,217/4,325), while `0x0C` "succeeds" on 586/742 but leaves 143-303
  bytes over. Those successes are not evidence: see the next point.
- **Do not try to locate the frame by searching for a start offset.** Every music
  body admits many offsets at which the node frame parses cleanly -- typically 2
  to 12, and up to 12 for `0x0B`. The frame is permissive enough that "it parsed"
  carries almost no information here, which is a stronger version of the ambiguity
  that type `0x0E` had. A structural predictor is required, as with the `0x0E`
  flag byte.
- **Types `0x0A`, `0x0C` and `0x0D` share one head, and each names exactly one
  same-bank object.** Body byte 2 selects where the 32-bit word sits: zero puts it
  at offset 9, nonzero at offset 5. Under that rule 7,326 of 7,331 bodies resolve
  -- all 4,158 `0x0A`, all 2,431 `0x0D`, and 737 of 742 `0x0C` -- with zero
  unresolved, zero null, and no unobserved discriminant.
- The five exceptions are all `0x0C` bodies whose **first** byte is 6 rather than
  0. That is a different head shape: their offset 9 is null and their offset 5
  names nothing, so neither branch applies. They are excluded from the claim and
  **counted in the published total** rather than dropped, so the denominator stays
  the whole population. `0x0A` and `0x0D` are byte 0 == 0 in every body. Observed byte 2 values are 0 (6,368), 1 (194) and 2
  (27); anything else must fail closed, because a fourth value has no branch.
  This is gated inside the reference-graph report and is a Layer-4 identity fact
  only: it says nothing about direction, containment, or meaning.
- **That folding is load-bearing, and getting it wrong cost 46 names.** The first
  version of this lane carried its own `fnv1_utf16` without the case fold, even
  though `identifiers.audio_hash_generator_compute` already mirrored the shipped
  implementation correctly. 46 shipped literals contain capitals -- every
  `Au_UI_Button_*`, `Au_UI_Event_*` and similar -- and all of them were missed.
  Correcting it took the lane from 151 to 203 named objects, 63 to 109 reaching a
  source, and 57 to 83 reaching media. **Never re-implement a hash this repo
  already mirrors**; the duplicate is what drifted, not the original.
- The falsification property survives the correction and is stronger for it: all
  203 matches still land on type `0x04` and none anywhere else.
- That corrects an earlier reading in this file. Fixing the word at offset 9 for
  every body resolves only 97.3% of `0x0A` and 95.5% of `0x0D`, and the shortfall
  looks like missing references. It is not: those bodies put the word at offset 5,
  and the byte that says so is right there. **A rule that is "nearly always right"
  is worth one more look for the byte that makes it always right** -- the same
  lesson type `0x0E` taught. The residue really did name nothing in any bank --
  which is a fact about those words only. **Do not read it as "no cross-bank
  evidence anywhere"**, as this note once did: the numeric type `0x03` target word
  crosses banks routinely, and that is recorded above.
- Type `0x0A` also carries a *second* group of references: a counted run of
  same-bank object ids, and byte 14 is a count of five-byte elements -- the run
  starts at exactly `32 + 5 * byte14` for the clean cases. This run is **not**
  gated and is not in the reference graph, because it cannot be located in 255 of
  4,158 bodies. But a fit of `base + w14*byte14 + w17*byte17` only reaches 96.8%,
  and byte 17 takes values like 95 and 110, so it is not a second count and the
  correlation is partly spurious. At least one further variable-length interior
  region is unisolated, so **no `0x0A` layout is established and no lane exists.**
- **Type `0x0B` opens with a counted run of 14-byte source records, and they share
  numeric type `0x02`'s plug-in id space.** Layout of the head: one byte, a 32-bit
  record count, then that many records of plug-in id (`u32`), stream-type byte,
  source id (`u32`), and five further bytes. All 4,447 records across 4,325 bodies
  carry a plug-in id type `0x02` also uses -- only `0x00040001` (3,506) and
  `0x00140001` (941), both from type `0x02`'s seven-value set.
- Why that is evidence for the 14-byte stride rather than a coincidence: plug-in
  ids are sparse 32-bit values, not small integers, so a wrong stride would put
  arbitrary bytes in that field and they would leave the set immediately. The
  records *after the first* are what actually test it -- 106 bodies declare 2 to 4
  records, contributing 230 such records, and every one landed in the set.
- What is **not** established for `0x0B`, and must not be published as if it were.
  After the record run comes a second counted structure of 88-byte entries whose
  second word repeats one of the body's own source ids. That framing consumes
  2,221 of 4,325 bodies exactly to EOF, but 248 entries name something other than
  a declared source, and 2,010 bodies still have a tail afterwards. The node frame
  does not explain that tail either: walking it from the end of the entries
  reaches EOF in 2 bodies out of 4,325. So `0x0B` has no lane.
- Type `0x0B` carries **no** same-bank object references at all -- it is pointed to
  by `0x0A`, and points at media instead. The corpus has only 7 DIDX entries in
  total, so its media is streamed rather than embedded, and `0x0B`'s source ids
  match neither the DIDX ids nor type `0x02`'s source ids. Those are simply
  disjoint id sets, which is not evidence against the layout.
- `0x0B` is *not* yet the witness that would resolve the node frame's group B
  width. Its bodies would only make group B nonempty if the frame starts at offset
  0, which is exactly what is not established. Group B remains unresolved.
- Method that paid off and is worth reusing: mirror the C# node frame in Python
  under `tmp/`, then **prove the mirror first** against an already-closed type.
  The mirror reproduced all 48,740 type `0x07` bodies exactly before it was used
  on anything, which is what makes its music-type failures trustworthy. Iterating
  in Python avoids a C# rebuild per hypothesis; nothing from the mirror ships.
- **Numeric HIRC type `0x0E` is framed byte-exact, and it does not use the shared
  node frame.** 24,145 bodies / 5,143,855 bytes, every one consumed from its first
  byte to its declared object-body end. Layout: a fixed 21-byte head, an optional
  20-byte block, 19 opaque bytes, a byte-counted list whose entries each carry one
  selector byte plus a `u16` element count plus that many 12-byte elements, and two
  closing bytes that read as zero everywhere.
- The branch is decided by a byte, not by a search. The candidate layout was found
  by sweeping shapes, which left 6,218 of the bodies with two start offsets that
  both consumed exactly -- so the sweep alone could not fix the prefix. Byte 1 of
  the body settles it: it is 0 or 1 across the whole corpus, and it predicts prefix
  21 versus prefix 41 in every single body. The framer therefore reads the flag and
  computes the prefix; it never searches, and any other flag value fails closed.
  **Do not weaken this to "take the earliest offset that parses"** -- that would
  reintroduce the ambiguity the flag byte removes.
- The minority branch is real, not a degenerate fit: its 164 bodies span 37 distinct
  bodies, 89 banks, 130 object ids, 3 files, 23 lengths and 21 distinct optional
  blocks. That check is the standing lesson from the group I and group H fixed
  widths, applied before publishing rather than after being caught.
- This lane carries a **closed-form byte identity** the other lanes cannot: framed
  bytes must equal `24 * bodies + 12 * elements + 3 * entries + 20 * optionalBlocks`.
  It holds exactly at 5,143,855. That is an equation, not the containment inequality
  the node-frame lanes use, so a miscounted element or entry cannot hide in slack.
  See [`reports/animestudio/hirc_type14_body_current_latest.md`](../reports/animestudio/hirc_type14_body_current_latest.md).
- What stays open on `0x0E`: the 21-byte head and 20-byte block are consumed by
  extent only; the 12-byte element is not split internally (only its trailing word
  is published as a histogram, bounded 0..9); and the two closing zero bytes cannot
  be distinguished from an always-empty counted list in this corpus. The 12-byte
  elements are **not** claimed to be points, curves, or samples of anything.
- **Layer 5 opens: numeric HIRC type `0x04` is the object that shipped managed
  code addresses by name.** The evidence is a unique cross-table reference, not a
  label. `global-metadata.dat` `stringLiteral` rows give 221 exact audio-like
  strings the game's own code contains; 203 of their hashes equal a HIRC object
  identity, and **all 203 land on type `0x04` and none on any other type**. The
  hash is the shipped `AudioHashGenerator`: FNV-1 over UTF-16 code units, folding
  ASCII `A`-`Z` before each XOR. Type `0x04` is 22,910 of the 323,034 objects (7.09%), so coincidence
  would scatter about 140 of those 151 matches onto other types; none did. That
  share is measured from the reader's own type histogram by `named_type_share`,
  not asserted in prose. The gate refuses to
  publish if a single match ever lands elsewhere, because that would dissolve the
  identification rather than weaken it -- never turn this into a percentage.
- Walking from a named type `0x04` object through reference vectors alone reaches
  numeric type `0x02` objects, whose bounded 14-byte prefix yields a source id:
  63 of the 151 named objects reach at least one, 134 source ids in total. The
  other 88 reach none, almost always because the walk hits an edge leaving the
  bank -- 98 such edges, counted and never followed. The walk also uses the type
  `0x03` target word, which is **not** a gated reference vector (only about three
  quarters of those words name an object in their own bank), so it is reported as
  what it is rather than folded in.
  See [`reports/animestudio/hirc_named_reach_current_latest.md`](../reports/animestudio/hirc_named_reach_current_latest.md).
- What Layer 5 does **not** license, even now. A reached source id does not mean
  posting the identifier plays that media; nothing here establishes ordering,
  selection, mixing, audibility, or that the media is ever decoded. Only the type
  `0x04` entry point has a name -- every other object on the path is still
  anonymous, and an edge leaving the bank still resolves to nothing this corpus
  can see.
- Be precise about what the reference graph is. The only direction it establishes
  is physical: which object's body holds the four-byte value. Over that byte-level
  direction the relation is acyclic with at most one holder per target, which is
  why the reader can walk it and report a depth. Do **not** promote that to
  parenthood, containment, membership, a tree, or a root: those are semantic
  readings the join does not license, and neither endpoint of an edge has a name.
  Ordering, selection, mixing and playback are equally unclaimed. The absence of a
  cross-bank edge is a property of this corpus, not a proven rule.
- Two further properties are readable straight off the published table, because
  with zero multi-referrer targets the references into a type are that many
  distinct objects of it: type `0x03` shows 28,379 referenced against 28,379
  objects, so every one is referenced exactly once; type `0x04` shows 0 referenced
  against 22,910 objects, so no type `0x04` object is ever the target of a
  reference.
- The null model for that result is per bank, not corpus-wide, because resolution
  only ever looks inside one bank. With 323,034 objects over 20,873 banks the
  reference-weighted expectation is about **0.15** chance resolutions, not the
  ~16 a corpus-wide pool would suggest. The finding is roughly two orders of
  magnitude stronger than a whole-corpus null implies -- but it argues the values
  *are* identities, still not what the edges mean.
- A bounded read-only probe shows how far the node frame reaches: it consumes
  cleanly from byte 0 for every type `0x06` (4,573) body and, after the counted
  state correction, for all 5,158 type `0x09` bodies, each leaving a regular
  type-specific suffix, while types
  `0x0B`, `0x0E`, `0x12`, `0x16` and `0x08` reject it outright and
  `0x0A`/`0x0C`/`0x0D` match only in part. Type `0x09`'s suffix looks like a
  counted four-byte reference vector followed by a second counted section and
  one trailing byte; type `0x06`'s is more varied and not yet decoded. Treat
  this as a prioritisation signal, not a framing claim: no suffix is parsed and
  no maintained reader accepts those types yet.
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
