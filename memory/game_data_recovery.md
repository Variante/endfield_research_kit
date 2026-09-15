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
  closed. A separate ActionGroupData census replays current positive
  `passiveEventActions` lists through empty and nonempty SequenceActionData
  branches. Exact-build dispatch and selected reader bodies align several
  non-null child unions to their independently pinned member-header counts.
  The C9 member-eight normal path is consumed only through its scalar prefix,
  stopping before its first generic SequenceActionData call because runtime
  provider selection for that nested reader remains unobserved. A separate
  candidate-only replay may record its three SequenceActionData call ranges
  against the current native sequence and child-action reader contracts, but
  those ranges do not advance the authoritative parser cursor or close C9.
  Other tags without a selected reader remain opaque at their first byte. The
  offline `memorypack.skill_timeline_cursor` now extends candidates through a
  child action only when the exact-build native route, per-tag reader contract,
  and source-hash-verified `memorypack.buff_actions.Reader` agree. Its selected
  reader endpoints and byte ranges remain candidates; an unsupported nested
  union stays unconsumed at its first byte. This broadens offline structural
  prefixes without selecting the runtime provider/cache or closing the parent.
  `timelineActions` remains a non-advancing count peek, and neither
  `ActionGroupData` nor whole SkillData is closed. Child fields remain unnamed,
  and bytes beyond each proven prefix or conditional list endpoint stay opaque.
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
- A second audit pass found a **stale non-claim**, which is the opposite failure
  and just as misleading. The type `0x02` prefix report listed "physical media
  placement" among the things it does not identify. That was true when written and
  is now false: the source id inside that prefix joins to the media the corpus
  ships, gated in the reference-graph report. Saying it is unidentified reads as
  caution while actually being wrong.
- **Non-claims go stale too, and nothing makes them fail.** A wrong positive claim
  eventually contradicts a number somewhere; a wrong "we do not know this" just
  sits there looking responsible. When a new join lands, re-read the non-claims of
  every report that touches the same bytes.
- Sweeping the remaining reports found two more. The type `0x03` action report
  said it does not establish **target resolution** -- which the reference-graph
  report had just gated (21,956 same-bank, 1,499 other-bank). The type `0x04`
  vector report said **entry values remain unnamed** and that no **Action
  relationship** is established, while the reference graph publishes this type's
  edges into type `0x03` and the named-reach report names 203 of the objects
  holding those vectors. Both are now scoped: the entry *targets* are still
  unnamed, which is narrower and still true.
- That is four stale non-claims across four reports, all written correctly and all
  falsified later by a different lane. **The pattern is structural, not careless**:
  each report is gated on what it claims, so nothing in the build can notice when a
  sibling lane makes one of its non-claims obsolete. Treat "this does not establish
  X" as a dated statement and re-read it whenever X lands somewhere else.
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
- **The DLL is not packed, and that now matters.** Measured sections: `.text`
  2,662,400 B at entropy **6.39**, `.rdata` 652,288 at 6.61, and **no `.tvm0`**
  section at all. Set against `EndfieldBase.dll` (79% `.tvm0` at 7.60) and
  `HGP.dll` (92% at 7.56), the Wwise reader is in the *readable* half of this
  game's binaries. Its RTTI is stripped -- only **12** `.?AV` type descriptors,
  every one a `std::` exception class -- so no `CAk*` names, consistent with the
  string-mining warning above.
- The six chunk-tag constants sit clustered in **`0xf4b74`-`0xf67a0`**, which is
  the section-dispatch region of the bank parser.
- ***So the blocker is weaker than recorded.*** The note above says the deciding
  witness is the licensed SDK and that obtaining it is the owner's call. That
  stands as the *cheap* route, but it is not the only one: the same structs are
  compiled into an unpacked 2.66 MB `.text` that ships with the game, with the
  parser's entry region located. **"Blocked on a licence" and "blocked on
  disassembly effort" are different states**, and only the second is true here.

  *A process note, since it cost a batch.* This DLL was already identified in these
  notes, with its SHA-256 and version string, **and with an explicit warning not to
  string-mine it** -- which is exactly what I then did. The recovery memory is the
  index of what is already known; **reading it first is cheaper than re-deriving
  it**, and the only reason this batch was not pure waste is that entropy and RTTI
  were questions the earlier pass had not asked.

#### THE HIRC TYPE DISPATCH, READ OUT OF THE SHIPPED PARSER

The warning was about *strings*. The **code** is a different matter, and it is readable
without a disassembler library -- the dispatch is a plain compare-and-jump chain.

**Locating it.** The bank chunk switch is at file `0xf4b60` and is literally
`cmp eax,'DATA' / je`, `cmp eax,'DIDX'`, `cmp eax,'HIRC' / je +0x35`, `cmp eax,'STID'`,
`cmp eax,'STMG'`. Following the `HIRC` branch reaches a `call` at `0xf4bdb` whose target
is the HIRC section parser at **file `0xf70a0`, VA `0x1800f7ca0`** -- confirmed by a
textbook prologue (`push rbp/rbx/rsi/rdi/r12/r14/r15; mov rbp,rsp; sub rsp,0x40`).

**The per-item dispatch**, at `0xf7147`:

```
movzx eax, byte [rbp-0x14]          ; the HIRC item's type byte
add   eax, -2                       ; type - 2
cmp   eax, 0x14                     ; 21 entries
ja    default
mov   ecx, [r13 + rax*4 + 0xf8008]  ; jump table at VA 0x1800f8008
add   rcx, r13
jmp   rcx
```

**21 entries covering types `0x02`-`0x16` exactly** -- the same range this project's
reader covers. Each arm writes a small constant to `[rbp+0x58]` and calls a per-type
constructor:

| class id | types |
| --- | --- |
| 0 | `0x02`, `0x05`, `0x06`, `0x07`, `0x09` |
| 1 | `0x08`, `0x12` |
| 2 | `0x03`, `0x04` |
| 5 | `0x0E` |
| **6** | **`0x13`, `0x14`, `0x16`** |
| 8 | `0x0F` |
| 9 | `0x11` |
| 10 | `0x10` |
| 11 | `0x15` |
| *(none)* | `0x0A`, `0x0B`, `0x0C`, `0x0D` |

**18 distinct constructors for 21 types**, each at a known address (`0x02` ->
`0x1800f0b90`, `0x09` -> `0x1800f2d30`, `0x10` -> `0x1800f2750`, `0x11` -> `0x1800f2460`,
`0x12` -> `0x1800f1850`, and so on).

***The result that bears on an open question.*** **Types `0x0A`, `0x0B`, `0x0C` and
`0x0D` share a single jump-table target** -- one handler, identical code, no per-type
constant. They are therefore parsed *the same way*, so **whatever `0x0B`'s layout is, it
is also `0x0A`'s, `0x0C`'s and `0x0D`'s**, and evidence gathered on any of them transfers
to the rest. The `0x0B` fenced-body question has been worked on in isolation; it need not
be.

**And every stuck type now has a located constructor.** The note above says the Wwise SDK
headers would settle `0x11`'s 21-versus-27 tie, `0x09`'s second run, `0x10`'s `0x7F`
variant and `0x12` outright. Those four constructors are at `0x1800f2460`, `0x1800f2d30`,
`0x1800f2750` and `0x1800f1850` in a shipped, unpacked binary.

**What is *not* claimed.** These are addresses and groupings, not decoded layouts. The
`[rbp+0x58]` value is a per-type constant handed to a shared tail; **calling it a class
selector is a reading, and only the grouping is a fact of the code.** No struct field has
been recovered here.

##### The address map, and where hand-decoding stops being reliable

Everything above lives in `.text`, where `VA = file + 0x180000C00`. **That delta is
section-specific and does not generalise** -- applying it to a `.data` reference put a
global 0xC00 bytes wrong and landed it in `.pdata`, i.e. in exception-unwind data, which
is how the error announced itself. The real section map:

| section | VA | file | raw |
| --- | --- | --- | --- |
| `.text` | `0x180001000` | `0x400` | 2,662,400 |
| `.rdata` | `0x18028b000` | `0x28a400` | 652,288 |
| `.data` | `0x18032b000` | `0x329800` | 72,192 |
| `.pdata` | `0x18034b000` | `0x33b200` | 150,528 |

The dispatch table above is unaffected -- every address in it is a `.text` address and each
target was confirmed against a real function prologue.

***Where hand-decoding stops.*** Reading handler *bodies* by hand goes wrong quietly: a
first pass mis-read a rip-relative operand as a `call` by starting mid-instruction, and the
`.data` global needed exactly the section mapping that was wrong.

**capstone 5.0.7 is installed** -- a note elsewhere recording its absence is stale -- and
re-running under it shows the hand-decoded *instruction stream* was right all along; only
the address resolution was wrong. So the reading below is the one that was provisionally
discarded, now verified.

#### HIRC `0x0A`-`0x0D` ARE NOT PARSED: THE ENGINE SKIPS THEM

The shared arm, disassembled:

```
mov  rax, [rip + 0x24ca0f]      ; global hook, .data VA 0x180344998
test rax, rax ; je default
lea  r9,[rbp-0x20] ; mov rdx,rdi ; lea r8,[rbp+0x58] ; lea rcx,[rbp-0x14]
call rax                         ; registered handler, if any
cmp  eax, 3 ; jne done           ; 3 == "not handled, fall through"
default:
mov  edx, [rbp-0x13]             ; the item's declared SIZE
lea  rcx, [rsi+8] ; lea r8,[rbp-0x18] ; mov [rbp-0x18], 0
call 0x1800ef2b0                 ; advance the read stream by `size`
cmp  [rbp-0x18], [rbp-0x13] ; cmovne ebx, 7    ; short read -> error 7
inc  r14d ; cmp r14d,[rbp-0x1c] ; jb loop      ; next item
```

`0x1800ef2b0` is a **buffered-stream skip**, not a parser: it takes `min(remaining,
requested)` against `[rbx + rax*4 + 0x18]`, advances `[rbx+0x50]`/`[rbx+0x10]`, calls a
virtual refill at `[rax+0x68]` when a buffer empties, and returns bytes consumed.

**So in this build, absent a registered hook, HIRC types `0x0A`, `0x0B`, `0x0C` and `0x0D`
are consumed as opaque payloads of their declared size**, with the only check being that
the skip consumed exactly `size` bytes.

***This changes the `0x0B` question rather than answering it.*** The open item -- the 210
multi-entry `0x0B` bodies -- has been looking for a structure that **the shipped reader
never imposes**. Six mechanisms were swept and excluded from the bytes; the reader explains
why none of them was found in the reader's own behaviour: *there is no `0x0B` layout in
this engine to recover.* Whatever structure those bodies have is imposed by the optional
hook or by the authoring tool, not by the runtime.

##### AND IT ANSWERS "WHERE IS MUSIC DRIVEN FROM" -- IN THE NEGATIVE

`0x0A`-`0x0D` are precisely the four music types this document has analysed at length
elsewhere: the offset-9 parent rule, the one-to-one `0x0A` -> `0x0B` edge, the symmetric
same-bank reference relation, the tempo-ranged floats. **All of that structure is real and
none of it is read by this engine.** The four share one jump-table arm that consults an
optional global hook and otherwise *skips the payload wholesale*.

Two independent lines now agree:

| line | finding |
| --- | --- |
| corpus (earlier) | the music family is **unreachable** from anything in the bank format |
| **reader (here)** | the music family is **not parsed** by the bank reader |

*Unreachable and unparsed are different claims from different evidence, and they point the
same way.* **The bank's music hierarchy does not drive music in this build.** The bodies
carry authored structure -- the corpus work established that beyond doubt -- but the
runtime path that would consume it is absent.

**The honest boundary.** The arm does call a registered hook first, so a plug-in *could*
parse these types at runtime; what is shown is that **no built-in parser exists**, not that
nothing can ever read them. That distinction matters because it names exactly what a
future answer would have to be: a registered handler, discovered at runtime, not a
structure recoverable from the bank bytes.

##### The `+12` / `+20` words inherit this, and it re-files them

The maintained reader's `Type11EntryPairFirstOffset = 12` / second at 20 are entry-header
words in **numeric type 11, which is `0x0B`** -- one of the four the engine skips. So the
open question about those two words sits inside a body **the runtime never parses**, and
the status recorded for it (blocked on a namespace outside the shipped files) is not the
real obstacle.

***What this rules out, and what it leaves.*** No engine-side evidence can ever name these
words, because no engine code reads them -- that route is closed, not merely unexplored.
But `0x0B` bodies are demonstrably *not* noise: the same reader already resolves their
source records, whose word at `+5` names a declared media id in **all 4,447** of `0x0B`'s
bodies and closed 1,276 media that nothing else accounted for. **That worked because it
had an external anchor -- the AKPK media declarations -- rather than an engine parser.**

So the `+12`/`+20` question is answerable in exactly one way: *another external anchor, of
the kind that resolved the source records.* Ten populations have already been eliminated
against the bytes alone; the lesson from the source-record success is that the missing
ingredient is a second table to join against, not a better sweep of the same bodies.

##### The chunk switch in full, and what it says about the "unowned" media

Disassembled properly, the bank dispatch is a flat fourcc chain:

```
cmp eax, 'DATA' ; je            cmp eax, 'DIDX' ; jne (other)
cmp eax, 'ENVS' ; ja / je
cmp eax, 'DATA' ; je 0x1800f57e5
cmp eax, 'HIRC' ; je -> call 0x1800f7ca0      <- confirms the HIRC parser address
cmp eax, 'STID' ; je -> call 0x1800f81e0
cmp eax, 'STMG' ; jne 0x1800f5831 -> the DIDX/DATA media path
```

The media path runs the same `0x1800ef2b0` stream advance with the same
consumed-versus-declared check and error 7, then allocates the media block (flags
`0x20000003`, size stored at `[rdx+0x28]`) through the same `0x1800ef040` /`0x1800ef120`
helpers the node loaders use.

***It never touches the HIRC section.*** Media declared in `DIDX` and carried in `DATA` are
allocated and registered **by id, straight from the chunk**, with no consultation of any
source record.

**So "unowned" is a property of the join, not an anomaly in the data.** The open item
counts media that no HIRC source record names, and 7 of the 8 were already characterised as
the Init bank's `DIDX`-embedded media. The reader explains *why that is the expected state*:
**a bank-embedded media needs no HIRC owner to be loadable**, because the chunk path is
self-sufficient. A media with no source record is not a dangling reference; it is a media
that happens not to be reached that way.

*That reframes the remaining question from "why are these 8 unowned" to "what, if anything,
distinguishes the 1 that is not Init-bank embedded" -- a much smaller question, and one the
existing censuses can be pointed at directly.*

**Incidentally recovered:** the HIRC item header is `u8 type` at `[rbp-0x14]` followed by
`u32 size` at `[rbp-0x13]`, with the section's item count at `[rbp-0x1c]` and the loop
index in `r14d` -- which is exactly the framing this project's reader already uses,
now confirmed against the engine.

##### Where the per-type field reads actually happen

Following the `0x11` arm (the 21-versus-27 tie) down: the arm **does not parse anything**.
It allocates via `0x1800ef040`, returns error `0x38` if that fails, then takes a refcounted
lock on a global registry at `[rip+0x252510] + 0x318`. The field reads are further on,
behind a **virtual call**:

```
mov  rax, [rbx]            ; vtable
mov  rcx, rbx              ; this
lea  rdx, [rsp+0x30]       ; cursor
lea  r8,  [rsp+0x20]       ; size (stored on entry from edx)
call qword ptr [rax+0x28]  ; <- the deserializer
```

**`vtable[+0x28]` is the field deserializer**, uniform across the type handlers -- the
single entry point any layout recovery has to go through. That is the useful, transferable
part: it applies to `0x09`, `0x10`, `0x11` and `0x12` alike, not just the one traced.

***What is left, stated precisely so the next attempt starts in the right place.*** Getting
a concrete layout needs the per-type **vtable address**, and that is not stored inline in
the arm -- it is written by a nested constructor, two or more calls down. A shortcut of
scanning `.rdata` for runs of code pointers **does not work as written**: it finds 94 runs
but merges adjacent tables, reporting 290-, 385- and 609-slot "vtables" that are plainly
concatenations. Splitting them needs the RTTI `type_info` pointer that precedes each real
vtable -- and this binary's RTTI is stripped to 12 `std::` descriptors, so that boundary is
not available either. **The remaining route is to follow the nested constructors, not to
scan for vtables.**

#### THE CHAIN COMPLETED, AND HIRC `0x11`'s LAYOUT READ FROM THE ENGINE

Following the constructors rather than scanning did work, in four hops:

1. the `0x11` arm looks a node up in an **id-keyed chain** (`cmp [rbx+0x10], esi` /
   `mov rbx, [rbx+8]`, refcount at `+0x14`, vtable at `+0x0`);
2. when absent it calls the **type-`0x11` factory at `0x18014aee0`**, which allocates
   **`0xa8` bytes** from pool 2, runs a base constructor, and **stores vtable
   `0x1802992d0`** at `[rbx]` (plus a secondary at `[rbx+0x18]`);
3. `vtable[+0x28]` is therefore `0x18014c250`;
4. that function is the deserializer, and it is short enough to read outright.

```
add  qword ptr [rdx], 4     ; cursor += 4   -- the node id, already consumed
mov  ebp, [rax]             ; FIELD A : u32
mov  [rdx], rsi             ; cursor += 4
mov  r14d, [rsi]            ; FIELD B : u32
add  rsi, 4 ; mov [rdx], rsi
cmp  ebp, -1 ; je done      ; A == 0xFFFFFFFF -> read nothing further
lea  rcx, [rip+0x1e38a5] ; mov edx, ebp ; call 0x18011e060    ; look A up
mov  rcx,[rsp+0x68] ; mov rax,[rcx] ; mov r9d, r14d ; mov r8, rsi
call qword ptr [rax + 0x18]  ; hand the REST of the payload to the plug-in
```

**So the engine parses exactly twelve bytes of a `0x11` body** -- the node id, then `A`,
then `B` -- and everything after that is passed to a plug-in **selected by `A`**, with `B`
handed over as a parameter. `A == 0xFFFFFFFF` means no plug-in and no further reading.

***This settles the `0x11` tie.*** The open item was a 21-versus-27 ambiguity in the body
length, undecidable from the bank bytes. It is undecidable *because the format does not fix
it*: **the engine-defined part is 12 bytes and the tail length is whatever the selected
plug-in consumes.** Two body lengths are not two candidate readings of one structure -- they
are two plug-ins. *A tie that will not break under more corpus evidence is often a tie the
format never had a side in.*

##### Running the recipe on the other types -- and a correction it caught

The four hops were automated and run over `0x09`, `0x10`, `0x12` **and `0x11` again as a
control**. The control earned its place immediately: it disagreed with the hand trace.

| type | factory | alloc | vtable | `vtable[+0x28]` |
| --- | --- | --- | --- | --- |
| `0x10` | `0x18014af30` | 0xa8 | `0x180299200` | **`0x18014c250`** |
| `0x11` | `0x18014aee0` | 0xa8 | `0x1802992d0` | **`0x18014c250`** |
| `0x09` | *recipe found none* | -- | -- | -- |
| `0x12` | *recipe found none* | -- | -- | -- |

***The correction.*** An earlier version of the note above gave `0x11`'s factory as
`0x18014af30` with vtable `0x180299200`. **Those are `0x10`'s.** The cause was reading a
`tail`-truncated disassembly: the listing began after `0x18014aee0`'s body and showed the
*next* function, whose vtable store was then attributed to the wrong type. *The deserializer
address was right, which is exactly why the error survived -- a wrong path to a right answer
looks like a right path.*

**The substantive finding is unaffected and in fact broadens.** `0x10` and `0x11` have
**different vtables but the same deserializer**, `0x18014c250`, so the 12-byte prefix plus
plug-in tail describes **both** types -- which fits them being the two plug-in-bearing node
kinds.

**`0x09` and `0x12` needed a wider scan, not a different method.** Searching *every* direct
call target in each loader for the factory signature finds exactly one per type:

| type | loader | factory | alloc | vtable |
| --- | --- | --- | --- | --- |
| `0x02` | `0x1800f0b90` | `0x180150c50` | 264 | `0x180299498` |
| `0x05` | `0x1800f3040` | `0x18013b6d0` | 304 | `0x1802984c8` |
| `0x09` | `0x1800f2d30` | `0x18015ea90` | 304 | `0x18029a3b0` |
| `0x10` | `0x1800f2750` | `0x18014af30` | 168 | `0x180299200` |
| `0x11` | `0x1800f2460` | `0x18014aee0` | 168 | `0x1802992d0` |
| `0x12` | `0x1800f1850` | `0x18015b170` | 400 | `0x180299cf0` |

##### CORRECTION: the deserializer slot is *not* uniform

An earlier note here said `vtable[+0x28]` is the field deserializer "uniform across the type
handlers... it applies to `0x09`, `0x10`, `0x11` and `0x12` alike". **That was generalised
from one loader and is false.** Reading the indirect calls each loader actually makes:

| slot called | types |
| --- | --- |
| `[rax+0x28]` | `0x10`, `0x11`, `0x15` |
| `[rax+0x278]` | `0x12` |
| neither | `0x02`, `0x05`, `0x09`, `0x13` |

***Why the wrong claim looked right.*** Slot `+0x28` **resolves to a real function on every
one of these vtables** -- for `0x02`, `0x05`, `0x09` and `0x12` it is `0x1800dacd0`, which
disassembles to a parent/flag setter (`bts`/`btr` on bits 13-15 of `[rbx+0x90]`, a virtual
at `[rax+0x260]`), **not a payload parser at all**. *A slot that resolves cleanly for every
type looks uniform; resolving is not the same as meaning the same thing, and only reading
the callers shows which slot is actually invoked.*

**`0x12`'s real deserializer is `0x180109030`** (`vtable[+0x278]`). It guards on a virtual
`[rax+0x78]`, bails with error `0x5b` unless that returns 0 or 0xA, then takes the cursor
and `add rax, 4` past the node id -- the same "id already consumed" convention as `0x11`.

#### HIRC `0x12`'s FIELD SEQUENCE, READ FROM THE DESERIALIZER

```
add  rax, 4                      ; cursor += 4   -- node id, consumed by the caller
mov  r14d, [rax] ; add rax,4     ; FIELD 1 : u32
test r14d, r14d ; je skip        ; 0 means "none"
  mov  rbx, [rip+0x23b911]       ; global object manager
  div  dword ptr [rbx+0xa0]      ; FIELD 1 % bucketCount
  mov  rax, [rbx+0x98]           ; bucket array
  mov  rdi, [rax+rdx*8]          ; chain head
  cmp  [rdi+0x10], r14d / mov rdi,[rdi+8]    ; walk, key at +0x10, next at +0x8
skip:
mov  ecx, [rax] ; add rax,4      ; FIELD 2 : u32  -> stored at object +0x188
call qword ptr [rax + 0x1f0]     ; nested parse, cursor passed by reference
cmp  eax, 1 ; jne fail
movsxd rcx, dword ptr [rax]      ; FIELD 3 : i32
imul   rcx, [rip+0x2267ee]       ; x a global rate
movabs rax, 0x20c49ba5e353f7cf ; imul ; sar rdx,7    ; / 1000
```

| field | width | what the code does with it |
| --- | --- | --- |
| node id | 4 | consumed by the caller, skipped here |
| **1** | 4 | an **object id**, resolved through the global id-keyed hash table (`0` = none) -- the same `+0x10` key / `+0x8` chain structure the loaders walk |
| **2** | 4 | stored at object offset `0x188` |
| *(nested)* | -- | virtual `[vt+0x1f0]` parses a further block, advancing the shared cursor |
| **3** | 4 | signed, multiplied by a global rate then divided by 1000 -- **a millisecond duration converted to samples** |

The divide is the standard `0x20c49ba5e353f7cf` / `sar 7` reciprocal for 1000, which is what
makes the units legible rather than guessed.

*So `0x12` is a node carrying one outbound reference, one stored word, a nested block and a
millisecond duration* -- recovered from the reader, not inferred from the corpus.

#### `0x09`: CALLED DIRECTLY, NOT THROUGH A VTABLE

The slot search found nothing for `0x09` because **there is no slot** -- its loader calls
the parser as a direct `call 0x180160450`. *A search for an indirect call cannot find a
direct one, and the empty result reads exactly like "this type has no parser".*

`0x180160450` has the same shape as `0x12`'s:

```
mov  rax,[rcx] ; call qword ptr [rax + 0x78]   ; type tag check
cmp  eax, 5 ; jne error                        ; 0x09 requires 5   (0x12 requires 0 or 0xA)
  ... log via 0x180036490, return 0x5b
add  qword ptr [rsp+0x78], 4                   ; cursor += 4 -- node id, as everywhere
lea  r8,[rsp+0x80] ; xor r9d,r9d ; lea rdx,[rsp+0x78]
call 0x1800dcfd0                               ; shared sub-parser (this, &cursor, &out, 0)
```

So the three conventions now confirmed across types are: **the node id is consumed by the
caller and skipped by the deserializer; a `[vt+0x78]` tag check gates entry with error
`0x5b`; and the cursor is passed by reference so nested parsers advance it.**

##### Status of the four types the notes called SDK-only

| type | reached | result |
| --- | --- | --- |
| `0x10` | `vtable[+0x28]` -> `0x18014c250` | 12-byte prefix, then a plug-in tail |
| `0x11` | `vtable[+0x28]` -> `0x18014c250` | same deserializer as `0x10` |
| `0x12` | `vtable[+0x278]` -> `0x180109030` | ref id, stored word, nested block, ms duration |
| `0x09` | **direct call** -> `0x180160450` | tag must be 5, delegates to `0x1800dcfd0` |

plus `0x0A`-`0x0D`, which are not parsed at all. **The obstacle recorded for these was a
licence; it was never the licence.**

#### THE SHARED SUB-PARSER, AND THE REGISTRY BOTH TYPES RESOLVE AGAINST

`0x1800dcfd0` -- what `0x09` delegates to -- is the common block:

```
call qword ptr [rax + 0x1f8]     ; per-class step 1, must return 1
test bl, bl ; jne done           ; the flag the caller passes in r9b (0x09 passes 0)
call qword ptr [rax + 0x200]     ; per-class step 2, cursor by reference
mov  ebp, [rcx] ; add rcx,4 ; mov [r15], rcx      ; read a u32
test ebp, ebp ; je skip                            ; 0 == none
mov  rbx, [rip+0x267983]         ; global object manager
lock cmpxchg [rbx+0x58] ...      ; refcount
div  dword ptr [rbx+0xa0]        ; id % bucketCount, then walk the chain
```

So the shared block reads **one u32 object reference, resolved through the global node
registry**, bracketed by two per-class virtuals at `[vt+0x1f8]` and `[vt+0x200]`.

***The registries are the same one, which is checkable rather than assumed.*** `0x12`'s
parser reaches it as `[rip+0x23b911]` from `0x1801090c7` and the shared block as
`[rip+0x267983]` from `0x1800dd055`. Both resolve to **`0x1803449d8`**. *Two different
displacements from two different call sites landing on one address is the kind of
arithmetic that either agrees exactly or is wrong* -- and it agrees.

**So `0x09` and `0x12` both carry an outbound object reference as their first parsed field
after the node id, and both resolve it against the same registry.**

#### THE PER-CLASS BLOCKS, AND `0x12`'s LAYOUT IN FULL

Both per-class virtuals open identically -- `movzx <r>, byte ptr [rax] ; inc rax ;
mov [rdx], rax` -- a **u8** taken from the shared cursor.

**`0x09`, `[vt+0x200]` -> `0x1800ffb50`** *(an earlier draft of this note said `[vt+0x1f8]`;
the slots are distinct -- `[+0x1f8]` is `0x1800ff980` and is not the function read here)*.
It reads **two** bytes and then a table:

```
movzx r9d, byte [rax] ; inc rax          ; FLAG : u8
mov  r8,[rcx+0x90] ; and/or with bit 54 ; cmove ; mov [rbp+0x90], r8   ; -> flags bit 54
movzx ecx, byte [rax] ; inc rax          ; B : u8 count
test cl,cl ; je done ; call 0x1800d70b0  ; reserve B
loop x B:
   movzx r10d, byte [rcx]      ; entry +0 : u8
   mov   r8d,  dword [rcx+1]   ; entry +1 : u32
   movzx r9d,  byte [rcx+5]    ; entry +5 : u8
   cursor += 6
   test r8d,r8d ; je next      ; the u32 being 0 skips the entry
   call 0x1800dcf90
```

**`u8` flag, `u8` count `B`, then `B` six-byte entries of `{u8, u32, u8}`** -- the cursor
advances 1, 4, 1 per entry, so the stride is read rather than assumed.

***And three types share one implementation.*** `0x02`, `0x05` and `0x09` have **identical**
per-class slots -- `[+0x1f0]` `0x1800ffc60`, `[+0x1f8]` `0x1800ff980`, `[+0x200]`
`0x1800ffb50` -- while `0x12` has its own trio. So this block is not `0x09`'s; **it is the
shared block of a three-type class family**, and anything established for one holds for the
other two.

##### The family's other two blocks, and a shape that appears twice independently

**`[+0x1f0]` -> `0x1800ffc60`.** `u8 N`, then `align = (N+4) & ~3`, allocate
`align + N*4`, store `N` at the head, fill from the cursor, and keep the block at
`[+0x88]`. **That is the same `N` bytes then `N` dwords structure as `0x12`'s `[+0x1f0]`**
(`0x180108d10`) -- *two different functions, compiled separately, producing an identical
serialized shape and storing it at the identical object offset.* A layout inferred once
could be a misreading; the same layout reached twice by independent code is the format.

**`[+0x1f8]` -> `0x1800ff980`.** A single `u8`, folded into the flag word at `[+0x90]` with
mask `0x3000000000000` -- **bits 48 and 49 together**, set or cleared as a pair. Note this
differs from `[+0x200]`'s byte, which drives the single bit 54: *three bytes in three blocks
all land in one flag word at different bit positions*, which is why they cannot be told
apart by value and only the code separates them.

##### The `0x02` / `0x05` / `0x09` node body, as far as the engine reads it

| block | content |
| --- | --- |
| `[+0x1f0]` | `u8 N`, `N` x byte, `N` x dword -> object `+0x88` |
| `[+0x1f8]` | `u8` -> flag bits 48-49 |
| `[+0x200]` | `u8` -> flag bit 54; `u8 B`; `B` x `{u8, u32, u8}` |
| shared tail | `u32` object reference, `0` = none, resolved via the registry at `0x1803449d8` |

*All three types carry this identically -- it is one class, reached from three jump-table
arms.*

##### `0x12`'s trio beside it -- same shapes, three precise differences

| block | `0x02` / `0x05` / `0x09` | `0x12` |
| --- | --- | --- |
| `[+0x1f0]` | `u8 N`, `N` x byte, `N` x dword -> `+0x88` | **same shape**, different function |
| `[+0x1f8]` | `u8` read, sets *or clears* bits 48-49 | **reads nothing**; ORs bits 48-49 **unconditionally** |
| `[+0x200]` | `u8` flag -> bit 54, **then** `u8 B` | **no flag byte** -- the first byte *is* `B` |
| entries | `B` x `{u8, u32, u8}`, stride 6, skip when the u32 is 0 | **identical**, same callee `0x1800dcf90` |

***The entry block is now confirmed three times over.*** `0x1800ffb50` and `0x180108c30`
are separately compiled functions that read the same six-byte record with the same 1/4/1
cursor advance and the same skip-on-zero rule, and `[+0x1f0]`'s `N`/bytes/dwords block
likewise appears in two independent implementations. *Three independent arrivals at one
layout is about as far from a lucky fit as byte-level work gets.*

**And the difference that matters for reading bodies:** `0x12` spends **one byte fewer**
in `[+0x200]` than the family does, and **zero bytes** in `[+0x1f8]` where the family
spends one. Two types whose blocks look interchangeable differ by exactly two bytes of
payload -- *which is the kind of discrepancy that makes a corpus-derived stride look
"nearly right" across a mixed population and never quite fit.*

**`0x12`, `[vt+0x1f0]` -> `0x180108d10`.** The byte is a **count**, and what follows is a
parallel-array block:

```
movzx ebx, byte [rax] ; inc rax          ; N
lea  r15d,[rbx+4] ; and r15d, 0xfffffffc ; align = (N+4) & ~3
lea  r8d,[r15 + rbx*4] ; call alloc      ; block size = align + N*4   (0x34 on failure)
mov  byte ptr [rax], bl                  ; N stored at the block head
memcpy(block + 1,     cursor, N)     ; cursor += N        ; N x u8
memcpy(block + align, cursor, N*4)   ; cursor += N*4      ; N x u32
mov  [rdi+0x88], r14                     ; block stored on the object
```

**`u8 N`, then `N` bytes, then `N` dwords** -- two parallel arrays of equal length, which is
a shape no amount of staring at body lengths would have separated from a single array of
5-byte records.

##### HIRC `0x12` complete

| order | field | width |
| --- | --- | --- |
| 1 | node id | u32 *(consumed by the caller)* |
| 2 | object reference, `0` = none | u32 |
| 3 | word stored at object `+0x188` | u32 |
| 4 | `N` | u8 |
| 5 | `N` x byte | N |
| 6 | `N` x dword | 4N |
| 7 | duration, `x rate / 1000` -- **milliseconds** | i32 |

*Read end to end from the engine's own deserializer.*
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
- **What that reference points AT, measured: `0x12` mostly names `0x08`.** Over both
  types' 412 bodies: `0x12` -> `0x08` **201**, `0x08` -> `0x08` **154**, `0x12` ->
  `0x12` **48**, plus 3 and 2 naming type `0x15` and 4 nulls. So the two types form a
  hierarchy with `0x08` beneath `0x12`, and `0x08` also nests within itself. No edge
  from either to `0x0B`.

### The first structure above byte layout: `0x08`/`0x12` form a forest

The leading word of every `0x08` and `0x12` body names another object. Followed as a
parent relation **per bank**, over 121 banks and 412 objects:

- **Zero cycles.** No object is its own ancestor anywhere in the corpus. A cycle
  would have meant the leading word is not a parent at all, so this is gated as
  equality with zero.
- **Depth runs to 7**, mode 2: `0`:123, `2`:126, `3`:64, `4`:32, `5`:23, `6`:21,
  `1`:18, `7`:5. It is a real hierarchy, not a flat list -- which the gate checks,
  because acyclicity is free when nothing is connected.
- **`0x08` is above, `0x12` below.** Internal nodes: `0x08` **68**, `0x12` **2**.
  Leaves: `0x08` 93, `0x12` **249**. The four objects with *no parent at all* are all
  `0x08`.
- **120 of 121 banks contribute exactly one tree**; one bank contributes three.

**The distinction that a first version of this gate got wrong.** An object with **no
parent** is a root of the relation; an object naming a parent that is merely **not in
this bank** is a root only of that bank's fragment. There are 119 of the second kind
and **all 119 are `0x12`**. Scored together they looked like 119 `0x12` roots, which
contradicts `0x12` being a leaf; scored apart they say something else entirely --
**a `0x12` object's parent usually lives in a different bank.** Corpus-wide those
references resolve: `0x12` -> `0x08` 201, `0x08` -> `0x08` 154, `0x12` -> `0x12` 48.

*Building this graph on deduplicated object ids gives 3 trees over 278 objects
instead of 121 over 412, because ids repeat across banks. A relation is only as
well-defined as the scope its endpoints are resolved in.*

### Three relation kinds, told apart by in-degree and symmetry

| relation | edges | a target is named by | reverse edge present | reading |
|---|---:|---|---:|---|
| main reference graph | 230,247 | exactly one referrer | -- | owner -> owned |
| `0x08`/`0x12` leading word | 275 | many children | -- | child -> parent |
| music types (`0A`,`0C`,`0D`) | 24,430 | many | **73.9%** | **mutual, neither** |

- **The music relation is symmetric.** Of 24,430 same-bank edges, 4,598 point at an
  object that was never scanned (only `0A`, `0C` and `0D` bodies are) and so cannot be
  asked the question; of the 19,832 that can, **14,652 have their reverse present**.
  Mutual across every type pair: `0A`<->`0D` 3,570 each way, `0C`<->`0D` 2,431,
  `0C`<->`0A` 588, `0C`<->`0C` 1,474.
- **So these edges cannot be read as parenthood in either direction**, and the music
  types do not form a hierarchy the way the other two relations do.
- **Not cliques either.** Neighbours of a node are linked to each other **0.1%** of
  the time, which rules out the reading that these bodies simply share a list of
  sibling ids.
- The graph has 7,341 back edges, which is exactly what a mostly-symmetric relation
  produces -- every mutual pair is a two-cycle. *Running a cycle check on a relation
  before checking whether it is symmetric answers the wrong question.*
- **Two corrections to my own earlier statements, both measured.**
  1. I said a shape analysis of the music edges "would be measuring the noise as much
     as the structure". Wrong by three orders of magnitude: expected chance matches
     are `646,465 x 213,138 / 2^32` = **32**, which is **0.13%** of 24,515.
  2. I assumed package-wide resolution was inflating the count. Also wrong --
     **24,430 of 24,515 music references are same-bank**, a difference of 85. Only
     0.35% leave the bank, against 119 of 275 for the `0x08`/`0x12` relation, which
     is the one that really does reach across banks.

#### The two reference relations in this format run in OPPOSITE directions

Both are forests, so shape alone does not tell them apart. **In-degree does.**

| | edges | a target is named by |
|---|---:|---|
| main reference graph (`05`->`02`, `07`->`07`, `04`->`03`, ...) | 230,247 | **exactly one** referrer, always |
| `0x08`/`0x12` leading word | 275 | **many** children -- 50 of 70 parents have two or more, and one has 16 |

- The main graph's `targetsWithMultipleReferrers` is **0 over 230,247 edges**. Every
  object there is named exactly once, which is what an **owner -> owned** edge looks
  like: a `0x05` object owns its `0x02` objects and no other object owns them.
- The `0x08` relation is the reverse: many children name one parent, which is what a
  **child -> parent** edge looks like.
- So the format carries downward ownership in one place and upward attachment in
  another, and the two must not be merged into one graph. **The `0x08`/`0x12`
  leading word is deliberately NOT in the main reference graph**, and adding it would
  break that graph's one-referrer-per-target closure -- which is a reason to keep them
  apart, not a defect.
- Gated by `the_hierarchy_runs_opposite_to_the_main_reference_graph`, which asserts
  the contrast rather than assuming it: the two relations are built by different code
  and nothing else would notice if one drifted into the other's shape.
- *Two relations can have the same shape and opposite meaning. Direction is not
  visible in "is it a forest"; it is visible in how many times a target is named.*

Gated by `the_shared_hierarchy_is_a_forest`, `almost_every_bank_contributes_one_tree`
and `numeric_type_12_is_a_leaf`. Nothing here claims what the relation *means* -- only
that it is a forest, that the two types occupy fixed positions in it, and that the
`0x12` end reaches across banks.

#### The curve record's values cannot be tested for propagation in this corpus

- The shuffle test that retired the fraction link has **no power** on the curve
  record, and this is a property of the corpus rather than a result about the data.
  Of the 408 reference edges inside `0x08`/`0x12`, only **17** have curve records at
  *both* ends.
- Worse, the obvious statistic is degenerate: "the two ends share an interpolation
  code" scores **17 of 17 on the real pairing and 17 of 17 shuffled**, because the
  alphabet is ten values of which two (9 and 4) cover about 87% of all records. Any
  two bodies share a code. Requiring a whole matching record gives 15 against 13 --
  seventeen samples, no power.
- *Before running a shuffle control, check that the statistic can tell the pairings
  apart at all. A test that scores identically on shuffled data has not produced a
  negative result; it has produced no result.*
- What the distributions do show, as corroboration rather than a link: the codes have
  the same two dominant values everywhere. `0x08`/`0x12` tail units run 9 at 44.9%
  and 4 at 41.7% of 314 records; `0x0B` element runs 9 at 49.4% and 4 at 24.5% of
  4,086. Same enum, same defaults, different mix.
- **`0x08` now frames byte-exact in 96 of its 161 bodies.** Layout, end to end:
  a 32-bit reference, the counted key/value block type `0x16` uses (a count, that
  many one-byte keys, that many four-byte values as parallel runs), a one-entry
  list whose key sizes its value (`0x15` -> 11 bytes, `0x1D` -> 27, exactly 16
  apart), the fixed nine-byte signature `02 e8 03 00 00 00 00 c0 c2`, a zero word,
  a counted run of six-byte entries, and five zero bytes.
- Two details are the whole difference between this and the earlier attempt.
  The one-entry list's key **predicts** its value width, so an unobserved key is
  held unsupported instead of walked with a guessed width. And the entry run
  carries **one extra byte when its count is nonzero and nothing at all when the
  count is zero** -- which the bodies declaring no entries fix, rather than being
  assumed.
- The 65 remaining bodies are fenced by named reason, never skipped:
  `trailer_is_not_five_bytes` 40, `word_after_signature_is_not_zero` 11,
  `signature_not_where_expected` 9, `range_properties` 4,
  `second_list_is_not_one_entry` 1. Those names are where the next attempt starts.
- `0x08` is deliberately **not** one of the closure-gated body lanes: a lane
  publishes a closed-form byte total and this type has none. Its gate forbids only
  what a partial framing must not do -- leave a body neither framed nor accounted
  for, report an ambiguous body, or pass with nothing framed at all.
- **The "zero word" after the middle block is a count too.** It is followed by that
  many **18-byte** elements. It reads as zero in 396 of the 412 bodies of both types,
  which is exactly why it was checked as a constant; the 16 that declare 1, 2, 3 or 7
  are what expose it. The width was **solved for**, not guessed: asking which element
  width lets each of those bodies close gives 18 for all of them, uniquely in 13 of
  14. That took `0x08` from 128 to **142 of 161**.
- **Third time this pattern has cost bodies in this layout.** The tail block's unit
  count, this middle-run count, and (earlier) the second-list count all looked like
  constants because the overwhelming majority of bodies declare the same value.
  *Before checking any field as a constant in this layout, look at its value
  distribution over both types -- a field that is 0 in 96% of bodies and small
  elsewhere is a count.*
### What "142,815 of 142,815 exact" does and does not establish

- **Six body lanes report 100% exact. That rate is real, but it is not one claim --
  it is a dozen claims of very different strength sharing a number.** The nine-group
  frame is optional almost everywhere: most bodies skip most groups, so a lane can
  frame every body exactly while one of its groups has been seen a handful of times.
- The reports published **group entry totals** and nothing else, and an entry total
  cannot be read on its own. `groupAEntries: 11` in type `0x06` might be eleven
  bodies with one entry or one body with eleven. Those are completely different
  amounts of evidence and only the first says anything about a layout.
- So every lane now also publishes **how many exact bodies exercise each group** and
  **the largest count any single body declares**, recorded at the one choke-point
  every framer passes through (`RecordHircBodyFrame`), so no lane can be added
  without it.
- **Pooled across all six lanes, nothing is thin.** The least-seen real group is
  group E at **324 bodies**; group C is at 85,397. The nine-group frame is well
  supported.
- **Per lane, several groups are very thin:**

  | lane | group | bodies |
  |---|---|---:|
  | `0x07` | group E items/vertices | **4** |
  | `0x06` | group A entries | **11** |
  | `0x05` | group H states/state elements | **12** |
  | `0x06` | group H groups/props/states | **14** |

- **Both numbers are true and the second is the one a reader needs.** Pooling is
  legitimate *only because* the nine groups are the same layout wherever they appear
  -- which is itself the claim under test, not a premise. "Group E's layout is
  established" rests on 324 bodies. "Type `0x07` frames group E correctly" rests on
  **four**. The `widestSingleBodyPerGroup` column is what rules out the one-fat-body
  case: group H's states are widest-1 or widest-2, so the 12 and 14 really are that
  many separate observations.
- Gated by `every_group_reports_the_bodies_behind_it`: a lane that counts group
  entries without counting the bodies behind them is refused, and a report with no
  groups at all fails rather than passing vacuously. The thin groups themselves are
  **reported, not gated** -- the corpus contains what it contains, and the point is
  to make the weak claim legible rather than to fail on it.
- **The rule this adds.** A completion rate over a corpus of mostly-optional
  structure is an average of claims, not a claim. Before reading one as evidence,
  ask which parts of the layout the passing bodies actually exercised -- and count
  bodies, not entries, because one body can carry a whole total.

### The shared frame's constants: closure never settled three of the four

- **Audited every constant in the shared framer by scoring it against every rival
  value, and closure turns out to be the wrong test for three of them.** The
  audit was prompted by the terrain retraction, where a claim validated only on
  degenerate inputs collapsed; the question asked here was the same one -- what do
  the *passing* bodies have in common?
- Two rules make the scoring fair, and both matter more than the result:
  1. **Score a constant only over the bodies that exercise it.** A body declaring a
     middle run of zero frames identically under every element width. Scoring all
     412 bodies buries the real margin under 398 that cannot tell the values apart
     -- and it did: the first cut of this census reported a best rival of 202
     against the chosen 325, which looked like a near-tie and was an artefact.
  2. **Reduce on corpus totals, not per package.** A per-package maximum of the best
     rival is not the corpus-wide best rival.
- What the corpus says, per constant (`chosen` / `exercising bodies` /
  `zero-trailer hits` / `best rival's hits` / `rivals that close every body`):

  | constant | chosen | exercising | chosen | best rival | rivals that close all |
  |---|---:|---:|---:|---:|---:|
  | `middleBlockBytes` | 9 | 408 | 325 | 0 | **0** |
  | `entryBytes` | 6 | 267 | 203 | 0 | **6** |
  | `middleRunElementBytes` | 18 | 14 | 10 | 0 | **2** |
  | `trailerBytes` | 5 | 408 | 325 | 0 | **12** |

- **Only `middleBlockBytes` is settled by closure.** Six entry widths close all 267
  bodies that carry an entry run. Three element widths close all 14 that carry a
  middle run. *Every* trailer length "closes", because a remainder that does not
  match simply routes the body to the tail block instead of refusing it -- so that
  constant was never under any test at all.
- What settles them is the **zero trailer**: landing exactly on five bytes that are
  all zero. Each chosen value wins that outright and every rival scores **zero**.
- **This corrects a stated reason, not a result.** The code comment claimed the
  18-byte element width "was solved for by asking which one lets each of them
  close". Widths 5 and 11 also close all fourteen. The width is right; the
  justification recorded for it was insufficient, and a reader trusting it would
  have believed the constant was better established than it was.
- Both facts are now **gates**, not remarks. `every_shared_constant_beats_its_rivals`
  demands a strict margin over the best rival and a nonzero score of its own; and a
  control gate demands that some rival still close every body, so that if closure
  ever did become the discriminator the reasoning here would fail loudly rather than
  rot quietly. Published per candidate in `hircSharedConstants` so the margin is
  re-measured every run.
- **The general rule, and it is the same one the terrain codec taught.** A constant
  fitted by "which value makes the parse close" is only established if the rivals
  are scored the same way and lose. Fit and discrimination are different claims, and
  a closure rate reports the first while sounding like the second.

### The fences are closed: `0x12` is complete, `0x08` is 160 of 161

Two readings closed 22 of the 23 fenced bodies. Both were *missing* structure, not
mis-sized structure, which is why widening ranges had never helped.

**1. A null leading reference carries a second 32-bit word.** Four `0x08` bodies
open `00 00 00 00` and then a word before the property count. Read without it they
ask for 74, 205 or 167 properties in a body far too short to hold them; read with
it, the second list's key lands on `0x15` in all four. That is the evidence -- where
the rest of the frame lands, not whether the count looks plausible. (An earlier
version of this idea was withdrawn because it "changed the exact count by zero".
It did, at the time, because these four were also failing later for the tail-block
reason below; fixing one without the other shows nothing.)

**2. A tail block ends with a section, and the old reading hardcoded its absence.**
The block is:

```
u8 zero, u8 unitCount, u8 zero          -- unitCount may be 0
unitCount x unit                         -- 12 head bytes, records, a byte, records
u8 entryCount
  entryCount == 0: one byte closes the body
  entryCount >  0: entries, then u8 one, u32 reference, u8 zero, u8 recordCount
                   recordCount x record
```

- An **entry** is 3 bytes, or 4 when the high bit of its first byte is set. The same
  high-bit width trick the format uses elsewhere. In bodies carrying several, the
  entries' first bytes run 0, 1, 2, ... .
- A **record** is `u32 id, u8 valueCount, u8 zero, valueCount x u16, valueCount x
  float`. `valueCount` is 1 in 36 of 38 records, **which is exactly why the record
  looked like a fixed 12 bytes** -- 4+1+1+2+4 = 12. Two records declare 2 and are 18
  bytes.
- **The two bytes the old code took for a fixed closing word were `entryCount = 0`
  plus its one closing byte.** So it framed the 64 bodies whose section is absent
  and none of the 18 whose section is present. A hardcoded constant standing in for
  an optional structure, for the second time this session -- the terrain codec's
  "closing run of exactly five literals" was the same mistake.

**Result.** `0x08` 142 -> **160 of 161**; `0x12` 247 -> **251 of 251, complete**.

### `0x08` IS CLOSED TOO: 161 of 161, and `0x12` 251 of 251

The last body's tail unit carries **three** bytes after its 12-byte head rather than
two, with the record count in the **middle**. The flag is the **high bit on head byte
6**: 111 units read `(count, pad)` with the bit clear, 1 reads `(pad, count, pad)`
with it set, and there are no counter-examples either way.

**One unit is thin evidence and the closure is not what carries this.** What does is
the content. Under the wide reading that body's **eight records all become curve
records** -- interpolation codes 9, 9, 9, 9, 5, 4, 4, 4, with values like (0.0, 1.0),
(0.005, 0.0), (100.0, 0.0), (60.0, 0.0) and (1.0, 0.0) -- and the body lands exactly
on its two-byte absent section. Under the narrow reading they are noise. *Eight
independent twelve-byte windows agreeing on a ten-value enum is the evidence; the one
unit is not.*

How it was finally found, after several wrong attempts: **the unit heads repeat.**
Unit 0's head begins `48 6a 10 56` and so does unit 1's -- and under the narrow
reading unit 1 appeared to start one byte earlier, at a `00` followed by those same
four bytes. A walk that lands one byte before a structure it has already seen is off
by one, and the repeated head is what makes that visible. *When a walk desynchronises,
look for the next occurrence of something it has already parsed correctly.*

Superseded by this: the earlier guesses that the head is 13 bytes, and that the count
is "whichever of the two bytes is nonzero". The head is 12 bytes and the gap is what
widens.

**The one body left, now characterised by content rather than by guesswork.**

- The two bytes after each tail unit's 12-byte head are a record count and a pad.
  Across all **110** units in the corpus: **109** read `(n, 0)` and **one** reads
  `(0, 3)`. Neither order is ever ambiguous -- **no unit has both bytes nonzero and
  none has both zero** -- so in 109 units the count is first and in one it is second.
- **The `(0, 3)` unit's three records are genuine curve records**, which is what makes
  the reading content-verified rather than size-fitted: `(0.0, 1.0, code 9)`,
  `(0.005, 0.0, code 9)`, `(100.0, 0.0, code 9)`. Reading the count as 0 skips them.
- **But "the count is whichever byte is nonzero" does not close the body.** It fixes
  the first unit and then the *second* unit's head fails its `b[+4] == 0` check, so
  the body needs more than the count. The corpus goes 160/161 either way, with the
  fence merely moving from `truncated_tailSectionEntry` to `unit_shape`.
- The earlier guess -- a 13-byte head signalled by the high bit on head byte 6 -- is
  superseded: the head is 12 bytes and the pair after it is what varies.
- *A rule that fixes the symptom you were looking at and breaks the next check has not
  been validated by the thing it fixed. Re-run the whole walk, not the failing step.*

**How these were found**, because the method is reusable: dump each fenced body
from its failure cursor to the end and read the bytes. Both structures were legible
by eye within a couple of samples -- the records end in recognisable floats
(`00 00 80 3f` = 1.0, `00 00 c8 42` = 100.0), which anchors the record boundary, and
from there the counts fall out. Widening a range would never have found either.

- The `range_tail_block_units` bodies declare **zero** units. Reading two of them by
  hand gives a tidy structure -- `00 00 00`, a count, a zero byte, that many 3-byte
  entries with an index running 0, 1, 2, ..., then `01`, a `u32`, a zero byte, a unit
  count, and that many 12-byte `(u32, u32, float)` units, closing the body exactly.
  It reproduces those two samples to the byte.
- **It is wrong, and this was checked before any of it was written into the reader.**
  Across the ten bodies it closes **1**, and that one's indices are not ascending;
  five type `0x08` bodies diverge at the byte after the entry run and four type
  `0x12` bodies one byte earlier. Two samples were enough to invent a layout and not
  nearly enough to test one.
- The alternative -- that the *entry run* walk is wrong for these bodies, so the tail
  does not start where the reader thinks -- is now **eliminated**: trying every run
  length from 0 to 63 makes the tail frame as a unit block for **none** of the 19
  bodies still fenced. The tail of these bodies is a different structure, not a
  misplaced start.
- **What the fence hides, censused rather than framed.** 40 bodies carry a tail
  after the entry run, and 27 of them end in a counted run of **twelve-byte
  records**: two 32-bit floats and a 32-bit code. The run is anchored from the
  **end**, never walked forward -- the tail must finish with a zero 16-bit word, and
  the count must sit exactly two bytes before a run of that many records. Zero tails
  are ambiguous and zero lack a count; the other 13 have no zero word at the end.
- The discriminator, and the reason this is not just arithmetic that fits: the
  record's **third field takes only five values across all 80 records** (0, 1, 4, 7
  and 9). Read at a wrong offset it would be arbitrary 32-bit noise. The first field
  reads as a float and takes values like -180, -96, -75, -48, -36, -18, 0, 0.6, 1,
  75, 100 and 180 -- recorded as an observation, not a claim; nothing establishes
  what any of them measures.
- **The tail block is framed, and both types now use it.** After the entry run a
  body either ends on the five zero bytes or carries this block, which finishes it:
  a 15-byte head, a record count, one byte, that many 12-byte records, and a zero
  `u16`. That took `0x08` from 96 to **109 of 161** exact and `0x12` from 213 to
  **245 of 251**.
- **The "fifteen-byte head" was a one-unit block. The tail is a counted run of
  units.** Layout: a zero byte, a **unit count**, a zero byte, then that many units,
  then a zero `u16`. A unit is `u32, zero byte, two bytes, u32, one byte`, then its
  own record count, one byte, and that many 12-byte records. Reading it this way took
  `0x08` from 115 to **128 of 161** and `0x12` from 245 to **247 of 251**.
- Why the old reading looked right: the unit count is 1 in every body that framed
  under it, so the whole 15 bytes looked constant. *A single-element counted run is
  indistinguishable from a fixed head -- find a body with two before believing a
  head is fixed.*
- This also settles the three bytes I had published as a per-type selector. They are
  **per unit**, not per type: across the corpus they take `020002`, `060200`,
  `060300`, `020402`, `020502`, `020100`, `022300`, `043100`. Publishing rather than
  checking them is what kept that reading recoverable -- a check would have been
  wrong and would have hidden it.
- Only the bytes zero in every body of both types are checked (the prefix's `[0]` and
  `[2]`, and each unit's `[4]`).
- **The 15-byte head's first word is a reference, and it names a numeric type
  `0x12` object.** 13 of the 27 located tails have a head of that width. Its word at
  offset 3 resolves to a same-bank object 5 times; the other 8 name objects the
  package does not ship, which is the same pattern type `0x03` targets show. The
  **control** -- the word at offset 10 of the same head, classified identically --
  resolves **zero** times. Object population 213,138, so chance resolutions across
  13 draws are expected at 0.000645; observing 5 settles it. Every resolved target
  is type `0x12`, and the gate fails rather than widening if a second type appears.
- Two readings of those words are **eliminated**. They are not names: 0 of 26 match
  an FNV-1 hash of any of the 49,324 distinct `global-metadata.dat` string literals.
  And the word at offset 10 is not a reference at all -- it is distinct in every
  body and resolves nowhere.
- What remains unexplained in the tail: the 14 located tails whose head is wider
  than 15 bytes, and the bytes of the 15-byte head other than its first word. That
  is where the next attempt starts -- and the `0x12` link says to attack type `0x12`
  alongside it rather than separately.
- **A rule that looked right and is withdrawn.** Bodies whose leading reference is
  null appeared to carry an extra 32-bit word before the property count. Adding
  that rule changes the exact count by **zero**, and not one of the four
  null-reference bodies frames under it. It was fitted to nothing. The general
  lesson: when a special case is suggested by a handful of bodies, check that
  removing it changes the count before keeping it.
- **Numeric type `0x12` shares `0x08`'s layout, and 213 of its 251 bodies now frame
  byte-exact.** Reference, counted key/value block, a second list whose key sizes
  its value, nine bytes, a zero word, the counted run of six-byte entries with its
  extra byte when the count is nonzero, five zero bytes. Two of the three
  second-list keys are `0x08`'s own: `0x15` -> 11 bytes, `0x1D` -> 27, plus `0x0A`
  -> 12. All 38 fenced bodies carry one reason, `trailer_is_not_five_bytes`.
- **How the widths were found, and why it is not a guess.** Everything after the
  second list is deterministic, so each body was asked which value width closes it
  exactly. Every body that closes has **exactly one** such width, and the width is a
  function of the key alone. Do not fit widths by eye; solve for them this way.
- **The nine bytes are a field, not a signature -- and `0x08` proves it inside its
  own type.** Read as `(u8 flag, u32, float)` the corpus carries four variants:
  `0x08` -> `(2, 1000, -96.0)` in 148 bodies, `(2, 0, -96.0)` in 8 and
  `(2, 500, -96.0)` in 1; `0x12` -> `(0, 0, -96.3)` in all 251. A magic does not vary
  in exactly one 32-bit slot, and the values are round decimals.
- **The two framers are now one.** Dropping the literal signature match and the
  "second list declares one entry" rule -- neither of which the shared layout
  justifies -- took `0x08` from 109 to **115 of 161** without moving `0x12`. Both
  the middle block's value and the second-list count are *published as selectors*
  rather than checked, because each type is uniform in them and a uniform corpus
  cannot tell a rule from a habit.
- **An ambiguity left open on purpose.** Key `0x0A` always arrives with a list count
  of 3 and a 12-byte value; the other keys always arrive with a count of 1. So "the
  key decides the width" and "the count multiplies a per-key width of 4, 11 and 27"
  predict the same bytes everywhere in this corpus. The simpler rule is implemented.
- **The 38 fenced `0x12` bodies carry `0x08`'s tail.** Same code censuses both. 34
  of the 38 have their trailing twelve-byte record run located by a unique count
  (100 records, third field only 4 and 9); zero are ambiguous; 4 have no zero word
  at the end and are read no further than the entry run. So of 251 bodies, 213 frame
  outright, 34 more are censused to their trailing run, and **4 remain opaque**.
- **Where the two types part, and it matters.** `0x12`'s tail-head words were
  classified exactly as `0x08`'s -- and they resolve to a package object **zero**
  times, control included. Sharing a layout does not make the same field mean the
  same thing. Do not carry `0x08`'s "names a `0x12` object" finding across.
- **What made this fast**: `0x08`'s tail head names a `0x12` object, so the two were
  attacked together. The reusable lesson is the one `0x16` already taught, now
  twice confirmed -- *when a small type resists, look for a structure another type
  already closes*, and here the whole layout was shared, not just a block.
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
- **Numeric type `0x0C` carries NAMES at fixed distances from the end of its body.**
  The words 12 and 24 bytes from the end are FNV name hashes of shipped string
  literals in **406 of 1,484 draws** over the 742 bodies -- against a chance
  expectation of **0.017**. Recovered values: `High` (72), `Low` (70), `Loop` (62),
  `WIN` (42+38), `Start`, `NONE`, `skip`, `General`, `END`, `Normal`, `Default`.
  146 bodies carry a name at *both* offsets.
- **Every music body references other objects, and the music types form a
  hierarchy.** Offering every 32-bit word of every body against the package's object
  set: **24,515 references across all 7,331 bodies, and not one body comes up
  empty.** Chance expectation over the 646,465 words offered is about 2. Edges:
  `0x0C`->`0x0D` 4,429, `0x0A`->`0x0B` 4,325, `0x0D`->`0x0A` 3,610, `0x0A`->`0x0D`
  3,570, `0x0C`->`0x0A` 3,262, `0x0D`->`0x0C` 2,431, `0x0C`->`0x0C` 1,920,
  `0x0A`->`0x0C` 588, plus small counts to `0x11`, `0x12` and `0x16`.
- **`0x0A` -> `0x0B` is one-to-one, and it is the only music edge that is.** 4,325
  edges reaching 4,325 distinct objects, none twice, out of a population of 4,325:
  every `0x0B` object is named by exactly one `0x0A` reference and none is missed.
- **The `0x0A` -> `0x0B` reference has a fixed place, measured from the END.** It
  sits **69 bytes from the end** in 3,707 of 4,325 cases, then -73 (288), -77 (59),
  -82 (52): four distances cover **94.9%**. Measured from the *front* the same
  references spread over 41, 36, 46, 45, 40, 48, 52, ... with no concentration at
  all. This is the first anchor the music types have had, and it only exists in
  end-coordinates.
- The secondary distances are 4 apart (-69, -73, -77), so an optional 4-byte field
  shifts the anchor -- the same kind of optional field `0x0D`'s lengths and `0x0B`'s
  entry widths both show.
- **`0x0A`'s HEAD has a rule: `36 + 5 * body[14]`.** Byte 14 is a count of five-byte
  elements, and it equals `(headLength - 36) / 5` in **3,441 of 3,441** bodies of
  the dominant family, including all 2,246 where the count is nonzero. Across the
  whole type the rule predicts a `0x0B` reference in **3,750 of 4,144** bodies.
- **Three controls, and they are what make it a finding.** Ignoring the count and
  reading at a fixed 36 scores **31.1%**; the position four bytes later scores
  **7.5%**; four bytes earlier scores **0.0%**. So the count is what places the
  reference, not proximity.
- **Byte 17 says whether the rule applies, and it is near-perfect.** Where
  `body[17] == 0` the rule places the reference in **3,744 of the 3,745** bodies
  that have one to place. Where it is nonzero: 6 of 144. Those 144 have longer
  heads, at `36 + 7 + 5k` (43, 48, 53) and a second family (52, 54, 59).
- **Mind the denominator.** Of the 394 bodies the rule "misses", **255 carry no
  `0x0B` reference at all** -- there is nothing there to find and nothing the rule
  got wrong. The real miss count is 139. The gate uses the denominator it can
  actually derive (bodies with `body[17] == 0`, which still includes those 255), so
  its threshold is 0.90 while the measurement against applicable bodies is 0.9997.
  The two numbers are not in conflict; they count different things, and the gate
  says which.
- **`0x0A` carries a SECOND reference, at offset 9 of its fixed head, and it names
  only `0x0C` or `0x0D`.** Over the 4,000 conditioned bodies it resolves in
  **3,999** -- 3,413 to `0x0D`, 586 to `0x0C`, one to nothing. Never a third type.
- **The fixed 36-byte head is half accounted for.** Conditioned on `body[17] == 0`,
  **16 of the first 36 bytes take a single value and all 16 are zero**. The varying
  positions fall in runs at 1, 5..12, 14..16, 18..20, 23..24, 28 and 32..33 -- the
  8-byte run at 5..12 contains the offset-9 reference, and `u32@1` and `u32@5` are
  zero in 3,736 and 3,624 of 3,744 bodies respectively.
- **The five-byte head element is fully read: a zero byte, a 16-bit value and two
  zero pad bytes.** Over the 3,052 elements in confirmed bodies: **0** with a
  nonzero leading byte, **0** with nonzero padding, and the value takes only
  **0, 1, 2, 3, 4** (598 / 2,240 / 186 / 26 / 2). So each element carries one small
  enumeration and nothing else.
- **The element census must be conditioned on the rule being confirmed, not merely
  on the discriminant.** Under `body[17] == 0` alone the same measurement gives 61
  nonzero leading bytes, 77 nonzero pads and 31 distinct values -- because a body
  whose reference is not where the rule says has no element boundary, so those bytes
  are being read at arbitrary offsets. Condition on the confirmed rule and every
  violation disappears.
- So `0x0A`'s head now reads end to end: 36 fixed bytes (16 of them constant zeros),
  then `body[14]` elements of `00 <u16 0..4> 00 00`, then the `0x0B` reference.
  What it leaves: the remaining varying fields inside the 36, the 144 bodies with a
  nonzero byte 17, and the 255 with no `0x0B` reference.
- **Byte 17 flags the longer head but does NOT determine its length** -- 36 distinct
  values over 126 bodies, 6 of them mapping to two different extras. It is a flag.
- **The count for the second run is `body[21]`, and the rule generalises.**
  `head = 36 + 5*body[14] + (7 + 5*body[21] if body[17] != 0 else 0)`.
  Byte 21 equals the second run's element count in **76 of 76** bodies of the
  `7 + 5k` family, all 56 with a nonzero count included. Over the whole type the
  generalised rule predicts the reference in **3,833 of 3,841** applicable bodies --
  **99.79%** -- against 3,744 for the single-run form.
- **The `0x0B` reference is an OPTIONAL four-byte field, and the 255 bodies without
  one are not anomalies.** Measured from the end of the head, **all 255 have a tail
  of exactly 65 bytes**, while the bodies that carry a reference sit at 69 (3,383)
  and longer. 69 - 65 = 4: the reference itself. Those bodies still carry the
  offset-9 head word (247 to `0x0D`, 8 to `0x0C`), so they are ordinary bodies with
  one field absent.
- That closes two of the three populations the head rule had excluded: 144 with a
  second counted run (framed), 255 with the reference absent (explained).
- **The third shape is a fixed 16-byte block, and `body[21]`'s MAGNITUDE selects
  it.** Where byte 17 is nonzero, byte 21 read as a count gives the five-byte run --
  but in some bodies it is part of a 32-bit value instead, taking 65, 97, 111 or
  243, and those carry a fixed 16-byte block. A count here is never above a handful,
  so the magnitude separates them cleanly: `byte21 <= 16` gives the run in 76 of 76
  bodies, `byte21 > 16` gives the block in 31 of 37.
- The complete rule:
  `head = 36 + 5*body[14] + (0 if body[17]==0 else 7 + 5*body[21] if body[21] <= 16 else 16)`.
  It predicts the reference in **3,875 of 3,903** applicable bodies, and the
  population it cannot reach at all drops from 62 to **14**.
- Searching for a *count* in those bodies found nothing above 80% under
  `base + width*byte` for base 0/7/12 and width 1/5. The answer was not a count --
  it was a fixed block selected by how big a byte is. *When "find the count" stops
  working, ask what the byte is when it is not a count.*
- Why byte 21 was invisible before: in the single-run family it is one of the 16
  **constant zero** bytes of the fixed head, so the second term vanishes and the
  general rule reduces to the special one. *A count that is zero in the population
  you are looking at is indistinguishable from padding.*
- **Every one of `0x0A`'s 4,158 bodies is now in a named category.**
  **3,875** have their `0x0B` reference placed by the head rule; **255** carry no
  reference at all, which the 65-vs-69 tail length explains as an absent optional
  field; and **28** are a residue the rule cannot place.
- The 28 are characterised, not just counted: their `body[14]` takes values like 35
  and 61 that are not counts (the implied extra comes out negative), `body[17]` is
  zero in 7 of them even though the head is long, and their actual head offsets
  cluster at 48, 51, 53, 54 and 59. A fourth shape, or variant bodies.

### `0x0A` IS CLOSED: the reference is a counted array, and the count is always right

```
u32 count
count x u32  -- type 0x0B object ids, four bytes apart
```

- **The word immediately before the first reference is a count, and it equals the
  number of references that follow in ALL 3,903 bodies that carry one.** Zero
  mismatches. Run lengths: 1 in 3,565 bodies, 2 in 271, 3 in 58, 4 in 5, 6 in 4.
- **Numeric type `0x0A` now has no unexplained bodies**: 3,903 counted arrays plus 255
  carrying no reference is its whole population of 4,158. The residue that stood at
  28, then at 3, is **zero**.
- **This supersedes the three-branch head rule and the two end anchors rather than
  competing with them.** Each was locating the first element of an array whose length
  it had no way to see; where they disagreed or reached nothing, the array was simply
  longer than one. The 28-body residue and the 3 that survived the anchors were
  bodies with 2 and 3 references.
- The gate is equality, and it also requires the run lengths to vary: a corpus where
  every array held one element could not tell a count from the constant 1 -- the same
  trap that left `0x0B`'s element count untested.
- *Three separate rules, each partly right, were describing one simpler thing. When
  rules accumulate around a field -- a head rule with three branches, then two end
  anchors, then a residue -- suspect that the field is a different shape, not that
  the rules need a fourth case.*

#### The end anchor takes the 28-body residue down to 3

- **The reference sits at one of a small set of distances from the END: `-69` in
  3,707 bodies and `-73` in 288.** The head rule works from the front and needs three
  of the body's bytes to be counts; the anchor needs nothing, so it reaches what the
  head rule cannot.
- **Combined, the type is accounted for: 3,875 placed by the head rule, 25 more by
  the anchor alone, 255 with no reference at all (the absent optional field), and
  three left.** The 28-body residue is now **3**.
- **The control is the whole evidence, and it is perfect.** A fixed distance from the
  end lands on *something* in every body, so a hit count says nothing. Every distance
  within five bytes that is *not* an anchor -- `-64` to `-68`, `-70`, `-71`, `-72`,
  `-74`, `-75` -- names a type `0x0B` object in **zero** bodies.
### The hierarchy is carried TWICE: a parent field inverse to the reference graph

- **Numeric types `0x02`, `0x05`, `0x06`, `0x07` and `0x09` name their owner at a
  fixed front offset** -- 8 for all but `0x02`, which uses 22.
- **Over 199,445 checkable cases the child's declared parent names the child back,
  with ZERO disagreements**, across 13 type pairs: `02`->`05` 129,413, `07`->`07`
  28,425, `05`->`06` 17,572, `05`->`07` 7,138, `02`->`07` 6,881, `06`->`07` 3,653,
  `09`->`07` 3,308, and smaller.
- The two readings come from **entirely different bytes**: the parent field is one
  word at a fixed offset, the reference graph is framed from each body's own counted
  runs. Their agreeing is the strongest cross-check this format allows, and it is
  gated as equality rather than a rate.
- **Two offsets the sweep also found are NOT parents, and the inverse test is what
  established that.**
  * `0x04` at offset 1 names a `0x03`, and the graph has `0x04` naming `0x03` too --
    the **same** direction, so it is that edge and not its inverse. 22,317 of its
    22,335 cases disagreed.
  * The music types at offset 9 are likewise downward.
- *A field that names a plausible object is not a parent until something independent
  says which way it points.* Both of these look exactly like the real parent fields
  and are not; nothing but the inverse test separates them.

### CORRECTION: the music offset-9 reference was already known

The previous two entries presented the music parent at front offset 9 as a
discovery. **It was not.** The reader has censused it all along as
`musicHeadReferences`: 7,084 bodies at offset 9, 242 at offset 5, selected by byte 2,
7,326 of 7,331 resolved. I rediscovered a field the report prints every run.

What the sweep did add, and what stands:
- the **non-music** parent fields, which are new;
- the **inverse test**, which is new and is what tells a parent from a child;
- the target types and forest shape of the music relation, which the existing census
  records the offset of but not the structure.

*Before presenting a located field as new, grep the reader for the offset.* The
sweep's value was the types nobody had swept, not the one already covered.

### THE MUSIC HIERARCHY: every music type has a parent at front offset 9

**All four music types name another object at front offset 9**, and the targets
chain:

```
0x0A --(3,461)--> 0x0D --(2,321)--> 0x0C --(716)--> 0x0C
  |                                   ^
  +--------------(586)----------------+
```

- Coverage: `0x0A` 97% of its bodies, `0x0C` 96%, `0x0D` 95%. Over the whole music
  corpus **7,084 of 7,331 objects (96.6%) name a parent**, 192 have none, 55 name one
  in another bank.
- Walked per bank: **zero cycles**, depth to **9** with a mode of 4, and **1,538 of
  3,066 parents named by several children** apiece (up to 16+).
- **That is the shape the `0x08`/`0x12` relation has** -- a forest, child-to-parent,
  many children per parent -- in an unrelated family of types, at a different offset,
  and spanning three types rather than one. What it means is still not claimed; that
  the pattern recurs is the finding.
- **`0x0B` completes the picture from the other side**: 2,713 of its 4,325 bodies
  name a `0x0A` at front offset **83**, which is the reverse of the `0A`->`0B` edge
  the head rule and end anchor place. The mutual music edges measured earlier are that
  pairing, seen from the aggregate.
- The sweep that found all of this is one measurement: **for each type, which front
  offsets carry a reference in more than 30% of bodies?** It took minutes and answered
  a question three previous passes had got wrong by measuring from the end.
- **How it was found, and it corrects the framing of the previous entry.** The census
  measures distance from the **end**, and from the end `0x0C` looks entirely unlocated
  -- 3,757 distinct distances for 9,634 references. Measured from the **front** it is
  3,193 distinct offsets, just as scattered, **except that one offset carries 716 of
  them.** A type can be unlocated in aggregate and still have a located field; the
  aggregate hides it.
- *Measure locality from both ends. A field at a fixed front offset is invisible to an
  end-distance census whenever body lengths vary, and every type here has variable
  bodies.*
- For the record, `0x0A` is more concentrated from the front too: **32** distinct
  front offsets against 77 end distances. The end anchor at `-69` is real and
  controlled, but the front is where these references are actually placed.

### `0x0C`'s list is LOCATED: a counted array at `32 + 5 * body[14]`

```
body[14]                 -- a count of five-byte optional fields
u32 count   at 32 + 5*body[14]
count x u32 at 36 + 5*body[14]   -- object ids
```

- **704 of the 704 arrays found there resolve completely** -- every entry naming an
  object in the same bank. 38 bodies have a count outside 1..64 and are not tested.
- Lengths spread 1 to 9+: `2`:270, `3`:148, `1`:80, `9`:70, `4`:60, `5`:24, `7`:22,
  `6`:20, `8`:10. Targets: `0D` 1,942, `0C` 644, `0A` 394.
- Selector values: 0 in 595 bodies, 1 in 122, 2 in 23, 6 in 2.
- **The control is total: 0 of 4,928 rival attempts resolve.** Read at base 28, 30,
  31, 33, 34, 36 or 40 the same test never even finds a usable count, let alone an
  array that resolves.
- **Base and step are settled by different evidence.** The base by resolution -- 32
  works and its neighbours find nothing. The step by *coverage* -- a step of 5 finds
  an array in 704 bodies where 0, 4, 6 and 8 find one in 564, and the 140 extra are
  exactly the bodies whose selector byte is nonzero. *A step that did not match the
  data would not reach more bodies; it would reach the same ones and fail on them.*
- This **locates a field**, not the type. Most bodies still carry references after
  the array -- 9 or more in 246 bodies, and 4,928 references in total across the type,
  targeting `0D` 5,470 times, `0A` 1,306 and `0C` 1,214.
- **ELIMINATED: there is no second counted array.** Applying the same step-back move
  after the first array appears to work in 438 bodies -- until you look at the counts.
  **Every one of them is 1**, and the run after it is length 1 in 702 of 704 bodies.
  A count of one before a single reference is satisfied by any word holding 1, so the
  match is worth nothing. The gap from the array's end to the next reference is also
  large and variable -- 99 bytes in 406 bodies, 126 in 240, 107 in 32 -- so whatever
  holds the remaining references is not adjacent to the array.
- **The remaining references are NOT scattered either -- they start at a computed
  position.** Measuring the first reference after the array as
  `offset - 4*arrayLength - 5*selector` gives **135 in 406 bodies and 162 in 240** --
  **646 of 704, or 92%** -- with every other value in single digits. So the next block
  begins at `135 + 4n + 5k` or `162 + 4n + 5k`, the two differing by 27.
- **The selector is INSIDE the region, at `arrayEnd + 96`.** Dumping the 99- and
  126-byte regions side by side shows them **identical for 96 bytes**, then diverging:
  a flag byte, and 27 further bytes when it is 1. So
  `nextBlock = arrayEnd + 99 + 27 * flag`, holding in **646 of 686** bodies (94.2%).
- *That is why scanning the body header found nothing.* The only "pure" bytes there
  were 9 to 12 at 86%, and those **are** the parent reference -- objects under a
  common parent sharing a layout, not a flag. **A selector that turns out to be an
  identifier is not a selector, and a selector need not be in the header at all.**
- **The multiplier stops at 1.** Flag 2 exists in 14 bodies and puts the next block at
  155, 167 or 215, not the 153 a repeat would predict. So it gates one block rather
  than counting them, and the gate refuses values above 1 instead of extrapolating.
- The 40 misses are all flag 0 with gaps of 107, 190 or 355 -- the rule places the
  block, but something else can lengthen the region further.

#### What the 96-byte region holds, and a constant shared across three types

| offset | distinct | commonest |
|---|---:|---|
| `+0` | 11 | `0` in 674 |
| `+4` | 13 | **`0x408F4000` = float 4.4766 in 670** |
| `+8`, `+12` | **1** | constant `0` in all 704 |
| `+16` | 12 | **`0x42F00000` = float 120.0 in 670** |
| `+20` | 4 | bytes `04 04 00 00` in 666 |
| `+84` | **1** | constant `0` in all 704 |

- From offset **27** the region carries a run of 32-bit words -- 4, 1, **-1**, 1,
  **-1**, 0, 4, 0, 7, 0, 1 -- so the region is **not aligned throughout**: an aligned
  prefix, then a run starting at a 3-byte offset. Reading it as u32s from 0 gives
  nonsense like `0x01FFFFFF`, which is a misaligned view of `01 00 00 00 ff ff ff ff`.
- **`0x408F4000` is a constant shared across the music hierarchy and absent from its
  leaf**: `0x0C`'s region `+4` **670 of 704**, `0x0A`'s `+8` **1,565 of 4,144**, and
  it appears somewhere in **2,056 of 2,431** `0x0D` bodies -- but in only **4 of
  4,325** `0x0B` bodies.
- That is the same value that dominates `0x0A`'s float block and appears as the top
  value of its `+4` field. So a single authored default is reused by `0x0A`, `0x0C`
  and `0x0D` -- the three types that form the parent chain -- and not by `0x0B`, which
  hangs off it. Nothing here says what it means.
- *A constant's distribution across types is evidence about which types share a
  concept. It costs one query and does not require framing anything.*

**The region's internal layout, from where its sentinels sit.** The four-byte `-1`
values land at region `+35` and `+43` in **700 of 704** bodies, and **every one is at
an offset congruent to 3 mod 4**. The floats at `+4` and `+16` are at `0 mod 4`. Two
grids, three bytes apart, so:

```
5 x u32      at  0 .. 19     -- includes the 4.4766 and 120.0 constants
3-byte field at 20 .. 22     -- `04 04 00` in most bodies
18 x u32     at 23 .. 94     -- includes the two -1 sentinels at 35 and 43
1 byte       at 95
flag         at 96           -- gates the 27-byte block
```

- 23 + 4x18 = 95 exactly, so the 3-byte field at 20 is what shifts the grid and the
  region divides with nothing left over.
- **38 of the 96 bytes are constant across all 704 regions**, in runs at 7-17, 24-26,
  40-42, 49-50, 52-54, 57-58, 64-66, 73-74, 80-82 and 84-87.
**Read at the recovered alignment, the region's 23 words are legible:**

| offset | reading | evidence |
|---|---|---|
| `+4` | **float** | plausible in **704 of 704**; 4.4766 in 670 |
| `+16` | **float** | plausible in **704 of 704**; 120.0 in 670 |
| `+8`, `+12` | **constant zero** | 704 of 704 each |
| `+31`, `+35` | **`1` then `-1`** | 700 each -- a value/sentinel pair |
| `+39`, `+43` | **`1` then `-1`** | 700 each -- a second pair |
| `+27` | small int, 30 distinct | 698 of 704 are <= 64 |
| `+51` | small int, `4` | 558 |
| `+71` | `0x400` = 1024 | 646 |
| `+91` | `0x100` = 256 | 698 |
| `+23`, `+63`, `+75`, `+79`, `+83`, `+87` | zero in almost all | |

- The float test has its control built in: at `+4` and `+16` it passes **704 of 704**,
  and at `+0`, `+8` and `+12` -- the same grid, four bytes away -- it passes **none**,
  because those hold zero. Two float fields, not twenty-three.
- The two `(1, -1)` pairs eight bytes apart are the clearest structure in the region.
  Nothing here says what they select.

- *Misaligned-looking words are a symptom, not a fact. Reading this region as u32s
  from its start produced values like `0x01FFFFFF` and `0x00FFFFFF`, which are not
  values at all -- they are a `-1` seen through a three-byte shift. Finding where a
  known sentinel actually sits is the cheapest way to recover a grid.*
- So `0x0C` is better described than "a variable-length list": a parent at 9, a
  counted array at `36 + 5k`, and a further block at a position computed from the
  array's length. What that block contains, and what chooses 135 over 162, are open.
- *The move that found the array is the same move that produced this false positive.
  What separates them is the length spread: the first array's lengths run 1 to 9 and
  the second's are all 1. A counted-array claim is only as good as the variation in
  its counts.*
- It came from applying the move that closed `0x0A` -- find a reference, step back
  four bytes, look for a count -- to a different type. That move has now worked twice
  and failed once (the `0x0B` residue), which is a better record than any of the
  width-enumeration attempts.

### `0x0C` keeps its references in a list; `0A` and `0D` keep theirs in fields

Asked of a census the reader has published for many runs: **how many distinct end
distances does each edge kind use?** A reference read from a fixed field lands at the
same distance body after body; one inside a variable-length list lands wherever the
preceding content leaves it.

| source | edges | bodies | edges/body | distinct distances | **edges per distance** |
|---|---:|---:|---:|---:|---:|
| `0x0A` | 8,701 | 4,158 | 2.1 | 112 | **77.7** |
| `0x0D` | 6,173 | 2,431 | 2.5 | 162 | **38.1** |
| `0x0C` | 9,641 | **742** | **13.0** | **5,021** | **1.9** |

- Per edge kind the separation is total and has an empty middle: `0A`->`0B` 135.2,
  `0A`->`0D` 81.1, `0A`->`0C` 73.5, `0D`->`0A` 43.5, `0D`->`0C` 43.4 --- then nothing
  --- `0C`->`0C` 2.5, `0C`->`0D` 2.1, `0C`->`0A` 1.6.
- **So `0x0C`'s references are not at fixed offsets and `0x0A`'s and `0x0D`'s are.**
  That is why a fixed-offset rule was findable for `0A`->`0B` and has never been
  findable for anything out of `0C`: there is no offset to find.
- **Correction to the "about 13 per body" reading, which was mine and was wrong.**
  13.0 is a mean over a wildly skewed distribution: the **median is 4** and the
  maximum is **2,172**. Ten of the 742 bodies carry **5,217 of the 9,634 references**.
  Nor is it a list -- only **6 of 742** bodies have all their reference positions
  mutually 4-aligned, and the same id typically appears at **4** scattered positions
  (mean 5.5, max 74), at gaps like 111, 264 and 201 within one 703-byte body. So a
  `0x0C` body mentions a handful of targets repeatedly, rather than listing many.
- **The split itself survives that.** Excluding the ten outlier bodies takes `0x0C`
  from 1.9 to **3.7** edges per distance, still an order of magnitude below `0x0D`'s
  38.1 and `0x0A`'s 82.9. *Check whether a ratio is carried by a handful of rows
  before building on it -- and quote the median beside the mean whenever the maximum
  is three orders of magnitude above it.*
- **The two edges into type `0x11` are NOT classified.** 118 and 130 references across
  19 and 22 distances gives about 6 per distance, which is between the groups. A
  hundred-odd samples cannot say which side they belong to, and the first version of
  this gate failed on correct data by trying to force them. *A discriminator with an
  empty middle still needs a minimum sample size, or the small cases land in the gap
  and get assigned by the threshold rather than by the data.*
- Read off `edgeDistanceFromEnd` again. **Two findings in a row have come from asking
  new questions of an unchanged census rather than from new probes** -- alignment
  modulo four, and now distinct-distance counts. When a lead runs dry, re-read what is
  already published before collecting more.

#### The rule is ALIGNMENT, not a list of anchor distances

- Enumerating anchors would have been fitting, and I nearly did it. Scanning every
  end distance shows **30** at which some body carries a `0x0B` reference, most with
  a handful of bodies: 81:9, 84:2, 85:4, 86:6, 87:6, 91:2, 112:2, 165:2. Adding those
  to an "anchor set" is just recording where the references happened to be.
- **The structure is that the distance from the end is 4-byte aligned.** 4,161 of the
  4,325 `0x0A` -> `0x0B` references -- **96.2%** -- sit at a distance congruent to 1
  modulo 4, with `-69` carrying 3,707 of them and the rest trailing off through 73,
  77, 81, 85, 89, 93, 97, 101.
- **Two controls, and both are needed.**
  1. *Aligned from the FRONT instead*: **47.7%**. Body lengths are spread across all
     four residues (2:1844, 1:1612, 3:635, 0:67), so the two questions are genuinely
     different and the end is the one that answers.
  2. *Every other music edge kind, measured identically in the same bodies*:
     `0C`->`0D` **3.9%**, `0C`->`0A` **4.5%**, `0D`->`0C` 14.7%, `0D`->`0A` 47.3%,
     `0A`->`0D` 43.0%. Corpus-wide 36.9%. So alignment is a property of **this edge**,
     not of the format or of the measurement.
- The generalisation I hoped for -- that all music references are end-aligned --
  **fails**, and its failure is what makes the `0A`->`0B` number mean something. *An
  attempted generalisation that fails is worth as much as one that succeeds: the
  cases it fails on become the control the original claim never had.*
- Read off `edgeDistanceFromEnd`, which the reader had been publishing all along.
  **The question was answerable from data already in the report**; no new collection
  was needed, only the idea of taking each distance modulo four.

- **A neighbouring offset is only a control if it is not itself part of the
  structure.** The first version of this gate scored `-73` as a control and failed on
  correct data. The head rule's own distance distribution -- 69, 73, 77, 82, 93, 125
  -- was already saying `-73` belongs to the family; I had the evidence and used it
  as its own refutation.
- **`u32@5` is a CROSS-PACKAGE reference, and it names numeric type `0x08`
  objects.** It is zero in almost every body; the 120 nonzero words take **four**
  distinct values and **none of them resolves inside its own package** -- which is
  why an earlier pass recorded it as "resolves nowhere". Joined against the whole
  corpus every one resolves: `0xF1339B46` (62), `0x4106E10A` (26), `0xEB239E75` (24)
  and `0xFD63C75F` (8) are all type `0x08` objects, plus one `0x0B` in a variant.
- **The lesson: "resolves nowhere" may mean the wrong id set was used.** The reader
  works per package, so a package-local set cannot see a cross-package edge. Before
  concluding a word is not a reference, try the corpus-wide set.
- **`float@16` in the fixed head is a bounded, whole-numbered value with a -96
  floor.** Range **[-96, 98]**, whole in 3,146 of the 3,594 in range, modes 0.0
  (1,622), 98.0 (192), 2.0 (176), -10.0 (175), -15.0 (122). The floor is the same
  -96 the `0x08`/`0x12` middle block carries. Gated at 1,856 nonzero whole values
  against an **overlapping** control window at offset 14 that carries **0**.
- The control overlaps the field by two bytes on purpose -- a window sharing most of
  its bytes is the hardest one to beat -- and it had to be judged on *both*
  properties, not just the range: at offset 14 the bytes read as a denormal near
  zero, which is trivially inside any band. **A range test alone accepts everything;
  the control has to be scored exactly like the candidate.**
- **What the 20 varying bytes of the fixed head actually hold** (conditioned on
  `byte17 == 0` and the rule confirmed, 3,744 bodies): `u32@5` takes only **5
  distinct values** and is zero in 3,624 -- an enumeration or a rare id, not a
  reference (it resolves nowhere). `u32@9` is the `0x0C`/`0x0D` reference.
  `byte@13` is constant zero. `byte@14` is the element count (0/1/2). `byte@15` and
  `byte@16` are small (0, 2, 5, 6). `byte@18`, `@19`, `@20` have 21, 23 and 8
  distinct values and look like parts of one 32-bit value. `byte@23` and `@24` are
  mixed. `byte@28` and `byte@33` are **booleans** (0/1, split 1,888/1,856 and
  3,146/598). `byte@32` takes 0, 1, 2, 3.
- **Twenty bytes past the reference sits an AUTHORED float, and its values look
  like tempo.** Over the 3,744 conditioned bodies it is finite in all of them,
  **whole in 3,727** (99.5%) and inside `[50, 200]` in 3,435 (91.7%). Its range is
  55 to 190 and its modes are **120.0** (1,557), 130, 110, 90.
- A float that is an exact integer 99.5% of the time is **authored, not computed** --
  that is the gated claim. That its range and modes are those of musical tempo, in
  the music object hierarchy, is recorded as an **observation**: it is the obvious
  reading and nothing here proves it.
- **`tail+8` is the opposite kind of field, and that contrast is the proof the
  offsets are right.** Whole in **202 of 3,744** against `tail+20`'s 3,727. Over the
  tail-69 subset it is whole in **0 of 3,321**. Two adjacent floats behaving that
  differently is what a real field boundary looks like; a reader slicing one
  quantity at two arbitrary places would get similar behaviour from both. The gate
  checks the contrast, not just the field.
- `tail+8` runs 3.366 to 6.533 with 85 distinct values (mode 4.477) and is **not a
  function of `tail+20`**: 12 of the 72 distinct `tail+20` values carry more than one
  `tail+8`, and no ratio, product or log relation between them is constant. Whatever
  it is, it is independent.
- **The tail's first 29 bytes are now fully accounted for** (tail-69 bodies, 3,321):
  `+0` the `0x0B` reference; `+4` a `u32` zero in 1,886 and taking 50 other values;
  `+8` the never-whole float; `+12` and `+16` `u32`s zero in 3,317 of 3,321; `+20`
  the authored float; `+24..27` four bytes reading `04 04 <0|1> 00` -- only **5
  distinct** 32-bit values across the corpus, so a packed flag record and not a
  number; `+28` constant zero. Seven 32-bit fields and a byte.
- **The 4-byte insertion sits immediately after the reference, before the float.**
  Tracking two fields by their signatures across the two tail lengths pins it: the
  never-whole float moves from `+8` to `+12` in **all 217** long-tail bodies, and the
  authored float from `+20` to `+24` in **all 217**. The reference stays at `+0`. So
  everything from `+8` onward shifts by exactly 4 and the extra field lands in the
  `+4..+7` region.
- That also rules out my own guess. I expected the insertion at `+12` or `+16`
  because those are zero in 3,317 of 3,321 -- the shape an optional field usually
  hides in. It is not there. **A field's being almost always zero says it could be
  optional, not that it is**; tracking a field with a distinctive signature across
  the two populations answers the question and a zero-rate does not.
- `+4` is also the one field whose behaviour differs between the two: zero in 1,886
  of 3,321 short tails and **never zero** in the 217 long ones.
- **`tail+4` is a 32-bit FIXED-POINT FRACTION of one.** Its nonzero values land on
  simple rationals to within a few parts in 10^10: `0x55555555` = 1/3,
  `0xAAAAAAAB` = 2/3, `0x92492492` = 4/7, `0xE8BA2E8B` = 10/11, `0x89D89D8A` = 7/13,
  `0x71C71C71` = 4/9, `0x0F0F0F0F` = 1/17, plus 27/49, 13/19, 4/23, 20/37. Over the
  corpus **1,399 of 1,804** nonzero values match a denominator <= 64; the same test
  on `tail+8` (a float) matches **114 of 3,614**. A 24x gap.
- Read it as bytes or as a rational, never as an integer or a float: as a `u32` it
  looks like arbitrary large numbers, and as a float it is nonsense. That is the
  second field in this tail whose meaning only appears in the right representation,
  after `tail+24`'s packed `04 04 <0|1> 00`.
- **The tail's optional 4-byte field is localized, and it is not counted.** Aligning
  the 3,321 tail-69 bodies against the 217 tail-73 bodies: from the **end** their
  constant profiles agree at **every one of 69 positions**, so the longer tail is the
  shorter one with four bytes inserted, not a different shape. From the **front**
  they agree to `tail+28` and diverge at `tail+29`. So the extra four bytes sit
  **within the first 29 bytes after the `0x0B` reference**.
- The constant word `0x5BBBD648` moves with the end, as expected: bytes 187 and 91
  sit at `tail+58,+59` in the 69-byte tails and at `tail+62,+63` in the 73-byte ones.
- **No byte inside the tail counts the extension either.** Best match for
  `tail == 69 + 4*byte` over the tail's own 69 positions is `tail+30` at 3,492 of
  3,585 -- but only **171 of the 264** bodies where the count would be nonzero, which
  is the giveaway. The high total is carried by zero bytes matching a zero count.
  *Always report the informative subset alongside the total.*
- **No single head byte predicts the tail length.** Tails are 69 (3,321), 73 (217),
  77 (44), 82 (32) -- steps of 4 -- and `69 + 4*byte` matches at best **2,829 of
  3,744** (byte 33), with byte 32 at 2,168 and byte 16 at 2,783. So the tail's
  optional fields are counted from **inside the tail**, not from the head. Do not
  spend another pass looking for a head byte that sizes the tail.
- **Conditioning on the anchor makes the tail legible.** Restricted to the 3,419
  `0x0A` bodies with exactly one `0x0B` reference and it at -69, **21 of the last 69
  byte positions are constant** -- against **6 of 101** over the unconditioned
  population. Constants include the word `0x5BBBD648` at -13, `0x00000002` at -30,
  `0x0298DF12` at -26, `0x02` at -23 and -30, and zero runs at -27..-29, -39..-42,
  -48..-49.
- The varying positions in that window fall in runs of **8 and 4 bytes** (-2..-9,
  -15..-22, -31..-38, -43..-46), i.e. whole 32-bit fields. So the region from the
  anchor to the end looks like a fixed record with `u32` slots, and that is where a
  `0x0A` framing attempt should start -- backwards from the end, conditioned on the
  anchor, never forwards from the head.
- **The two edges that looked the same are eliminated.** `0x0D`->`0x0C` has an edge
  total of exactly 2,431 -- the `0x0D` body count, which is what made it look like a
  bijection -- and reaches **578 of 742** objects, 382 of them repeatedly.
  `0x0C`->`0x0D` reaches every one of its 2,431 targets but reaches **1,628** of
  them twice.
- So a one-to-one claim needs **all three** measurements and an edge total supplies
  none of them: distinct targets equal to the population, no target reached twice,
  and the edge total equal to both. Two of the three neighbours here pass one or two
  of those conditions and fail the rest.
- The method that works when a type will not frame: **do not look for the reference,
  offer every word.** Object ids are sparse enough that the id space does the
  discrimination. It found three references per `0x0D` body where framing found one.
- **This is the first semantic recovery inside the music types**, and the way in was
  anchoring from the **end**. Their heads are variable -- only three byte positions
  from the front take a single value across the corpus -- but the tail is not:
  `0x0A` carries the constant word `0x5BBBD648` thirteen bytes from the end in all
  4,158 bodies; `0x0C` holds the constant bytes `0x64` (100) at -2 and `0x32` (50)
  at -4 in all 742; `0x0D` has **30** constant byte positions in its last 120, and
  every one of them is `0x00`. *When a type's head resists, tabulate from the end.*
- **Type `0x0D`'s body lengths are `165 + 34a + 5b`.** 2,273 of 2,431 fit, 130 do
  not, 28 are ambiguous; the modal `(a, b)` are `(1,0)` 906, `(1,1)` 410, `(2,0)`
  352, `(2,1)` 239, `(1,2)` 78, `(0,0)` 41. The 5 matches the optional field
  `0x0B`'s entry widths also show (84/89, 132/137, 168/173).
- **The arithmetic check that makes this worth believing.** 34 and 5 are coprime, so
  every `d >= 132` is representable for free (Frobenius number 131) and a fit there
  means nothing. Only **91** of the 2,431 bodies are in that range; **2,210** fit
  uniquely with `d < 132`, where roughly half the integers are representable at all.
  And it is type-specific: `0x0A` does **not** fit this shape (3,807 of 4,158 fail
  against base 101), so it is not just small-coefficient coverage.
- **The bytes do NOT back the "34-byte repeating element" reading, and it is
  withdrawn as a structural claim.** Each length group is internally very uniform --
  157 of 165 positions take a single value in the 165-group, 159 of 199 in the
  199-group -- but the groups do **not** align with each other. Comparing their
  fixed-position profiles gives only 70/89 to 91/141 agreement end-aligned and
  similar front-aligned, where a base-plus-inserted-element layout would give
  agreement everywhere both profiles are constrained.
- A trap inside that measurement: restricting the comparison to a window where both
  profiles happen to be constrained gives **1.0** at several different insertion
  points, including two that contradict each other. Score an alignment over the
  whole overlap, never over a window chosen after seeing the data.
- So `165 + 34a + 5b` is a real regularity **of the lengths** and nothing more. The
  length groups are different shapes, not one shape with a repeated block.
- **Count the constants, and do not read a distinct-value count as a byte value.**
  The first version of this tabulation printed a constant as two hex digits and a
  varying position as its number of distinct values, in the same column. A position
  with 64 distinct values printed as `64` and was read as the constant byte `0x64`.
  `0x0D` has no `100` or `50` anywhere near its end -- that was the bug, not the
  data. Print a sigil for varying positions.
- The census is in the maintained reader and gated, but the gate **skips when no
  names are supplied**: the corpus gate's reader run does not load the metadata
  literals -- the named-reach tool does -- and a census with nothing tested means
  the question was never asked, not that the answer is no.
- **The twelve-byte curve record is NOT in the music types.** Scanning every offset
  of all 7,331 bodies for a `u32` count followed by that many `(float, float,
  interp <= 9)` records finds it in 33 of 4,158 `0x0A`, 18 of 742 `0x0C` and **0 of
  2,431 `0x0D`**. At those rates, over a scan of every offset, these are chance
  fits. The record is in `0x08`, `0x12` and `0x0B`; the music types are the first
  miss, so the cross-type heuristic has a boundary.
- **The trap that nearly made this a finding, and it is the second time this
  session.** The same scan without a variation requirement reports the record in
  **2,423 of 2,431** `0x0D` bodies. Every one of those is a run of **zero bytes**:
  zeros are finite floats and zero is a valid interpolation code, so a zero-filled
  region satisfies every bound for free. The earlier music-type tail match failed
  the same way with `entries_0`.
- **General rule, now written down because it has cost two false results.** Before a
  structural test's hit rate means anything, check it against the degenerate input
  that satisfies it trivially -- a run of zeros, a count of zero, a single-element
  list. If the degenerate case passes, the rate is measuring how much of the corpus
  is degenerate, not how well the structure fits.
- **Two fresh eliminations on the music types (2026-09-15). Read these before
  trying the next idea.**
  (a) *Their head is not a fixed skeleton.* Tabulating every byte position across
  the whole corpus, only offsets 0, 3 and 4 take a single value in `0x0A` and
  `0x0D` (plus offset 34), and `0x0C` has none at all in its first five. A head read
  off one body -- "nine zero bytes, then the reference, then zeros, then a flag" --
  looks convincing and is over-fitting. Tabulate positions first.
  (b) *They do not share the `0x08`/`0x12` tail.* The tail block fits 2 of 7,331
  bodies. The entry-run-plus-five-zeros tail appears to fit 2,344 `0x0D` bodies --
  and every one of those is `entries_0`, which is just "the last six bytes are
  zero". A count of zero makes that test vacuous; check the count distribution
  before believing a tail match.
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
- **Every `0x0B` body ends with the 32-bit word 100** -- 4,325 of 4,325, no other
  word observed. Gated on equality with the body count, not a rate, because one
  exception would mean the reader is looking at a different layout.
- **After the record run comes a 32-bit entry count, that many variable-width
  entries, then that terminator.** Counts run 0 to 8 (4,019 bodies declare one).
  The first entry's leading word is 0 in 4,295 bodies and 1 in 26, and its *second*
  word is one of the body's own declared source ids in all 4,321 bodies that
  declare an entry -- the four declaring zero carry no echo, which is the control.
  What fixes the entry start is that **no other offset in a 48-byte window echoes
  a source id even once**; source ids are sparse 32-bit values, so this is not
  something arbitrary bytes produce. No body carries more echoes than it declares
  (4,261 match exactly, 64 carry fewer because later entries, being
  variable-width, do not land on four-byte boundaries).
- **Retraction.** The earlier reading of this tail as fixed 88-byte entries is
  withdrawn. It called 2,221 bodies exact because the run finished at EOF -- which
  it could only do by swallowing the terminator. The 88 was the 4-byte count plus
  the *modal* 84-byte entry, not a stride; entry widths are 84, 89, 120, 132, 168,
  137, ... The "248 entries name something other than a declared source" figure
  came from that same wrong stride and is withdrawn with it.
- **Inside a `0x0B` entry, three more fields are count-shaped.** Tabulating every
  32-bit slot across the 4,019 single-entry bodies (the entry is everything between
  the entry count and the terminator):
  `u32@0` is the flag (0 in 4,005, 1 in 14), `u32@4` is the source id, **`u32@8` is
  zero in all 4,019**, and then `u32@44` is 1/2/3 and never 0 (3,891/113/14),
  `u32@48` is 0/1/2/3 (2,833/903/253/...) and `u32@56` is 0/3/4/... -- the same
  "mostly one small value" shape that turned out to be a count three times in the
  `0x08`/`0x12` layout.
- **The elements they count are variable-length, so this is not yet a frame.**
  Solving `48 + c44 * w == entryWidth` gives a unique `w` for 3,618 of 4,019 bodies
  but `w` itself ranges over 36, 41, 43, 47, 72, 77, 84, 89, 96, 108 -- so `u32@44`
  counts something whose size is decided inside it, exactly like the tail's units.
- **The same twelve-byte record the `0x08`/`0x12` tail carries is inside `0x0B`'s
  entries too**, and it is now censused and gated. Where `u32@56` is nonzero,
  `u32@60` is a record count and the records start at offset 64: two floats and a
  32-bit interpolation code. Over the corpus: 775 entries of 4,019 carry them, 3,124
  declare none, 120 have an unusable count, **0 run past the end**, and the 1,759
  records' codes are **0 through 9 with no gaps and nothing above 9**.
- That contiguous ten-value enum is the discriminator. A 32-bit field read at a
  wrong offset would be noise, so the gate refuses any code outside a small range.
  The first float takes 0.0 (793), 0.11, 0.13, 0.1, 2.33, ... -- an observation, not
  a claim; nothing here establishes what it measures.
- So the twelve-byte curve record is now confirmed in **three** numeric types --
  `0x08`, `0x12` and `0x0B`. When a new type resists, look for it.
- Two regularities worth carrying in: entry widths come in pairs five bytes apart
  (84/89, 132/137, 168/173) with identical counts, so some five-byte field is
  optional; and once a base is chosen the remaining widths differ by multiples of 12,
  which is the record size the `0x08`/`0x12` tail also uses.
### `0x0B`'s element ends with a self-sizing trailer, and that explains the widths

- **The element's trailer chooses its own length from its first byte: `0` means 19
  bytes, `1` means 24.** That five-byte difference is the five-byte step the entry
  widths have shown all along -- 84/89, 132/137, 168/173 -- and it is an optional
  field's two forms, not two layouts.
- **What the trailer leaves behind is `17 + 12k`**: a 17-byte head and a run of
  twelve-byte records, the same record `0x08`, `0x12` and `0x0B`'s curves carry.
  Over the 3,891 bodies with exactly one entry and one element: **3,594 frame**
  (3,238 short trailer, 544 long), 109 are ambiguous, 188 leave a body that is not a
  whole number of records.
- **The evidence is the residue, not the parse.** Rival anchors pick exactly one
  trailer for just as many elements -- `-18/-23` picks one for **3,875**, more than
  the chosen `-19/-24`'s 3,782. Parsing separates nothing. But the bodies each
  anchor leaves behind do:

  | anchor | picks one trailer | leaves `17 + 12k` |
  |---|---:|---:|
  | `-17/-22` | 3,877 | 32 |
  | `-18/-23` | 3,875 | **0** |
  | **`-19/-24`** | 3,782 | **3,594** |
  | `-20/-25` | 3,418 | 6 |
  | `-21/-26` | 721 | 4 |

- **Rivals are not all independent, and the first version of this gate got that
  wrong.** `-19/-25` scores 3,108, which failed a tenfold-margin test -- but it
  scores that only because `-19` is right and most elements take the short trailer.
  An anchor sharing an endpoint is a near-duplicate, not an alternative. The gate now
  demands the chosen anchor win outright against every rival and by a wide margin
  against rivals sharing **neither** endpoint. *When scoring a two-part reading
  against rivals, rivals that share a part inherit its score; hold only the
  genuinely different ones to the wide margin.*
### `0x0B` has a whole-body frame: 4,115 of 4,325

```
u8  flag
u32 sourceCount, that many 14-byte source records
u32 entryCount
entryCount x entry:
    48 header bytes, the element count at +44
    elementCount x element:
        5 head bytes, the run count at +0
        runCount x run: 12 header bytes, the record count at +7,
                        then that many 12-byte records
        12 trailing bytes
        a trailer of 19 + 5 * flag bytes
u32 terminator, always 100
```

- **This type had no frame at all before.** Every counted run in it is a count the
  body declares, and every width was settled by scoring rivals the same way rather
  than by whether the parse closed.
- **Run the managed suite with `dotnet run --project
  tools/AnimeStudio/AnimeStudio.CLI.Tests`, never `dotnet test`.** That project is a
  console `Exe`, not a test-SDK project, so `dotnet test` finds no tests, prints no
  counts and **exits 0**. A green exit there means nothing ran. The real run ends
  with `Managed-reference and VFS recovery tests passed.`, and the `Error:` lines
  above it are its own negative cases.
- **The trailer length is `19 + 5 * flag`, and flags 0, 1 and 2 are each observed
  closing bodies exactly** -- 3,108, 575 and 32 elements. Three points on the line,
  not two and an extrapolation. Flag 2 was worth the check: adding it took the body
  frame from 3,683 to 3,715, and all 32 of the bodies it gained had failed on
  exactly `trailerFlag_02`. Anything above the highest observed flag is refused
  rather than assumed to continue.
- **The 388 fenced bodies, by reason:** `range_element_trailer_flag` 119,
  `range_element_runs` 102, `entries_do_not_reach_the_terminator` 94,
  `range_elements` 46, `range_element_head` 21,
  `trailing_zero_run_before_the_terminator` 6. None is partially framed into a
  result. (610 before the extended trailer, 464 before the trailing section.)
- **The largest bucket was two different things and is now named apart.** Of the 322
  bodies that stopped short of the terminator, **104 leave nothing but a run of
  zeros** -- 7 bytes in 98 of them, 5 in the other 6 -- and **218 leave real
  content**. Reporting one number hid that the second group is unread structure while
  the first may be padding. *When a fence bucket is the largest one, check whether it
  is one failure or several wearing the same name.*
- **What the 218 leave is recognisable.** A 44-byte leftover begins
  `00 00 40 3f 00 00 80 3f 09 00 00 00` -- 0.75, 1.0 and the interpolation code 9,
  which is the twelve-byte curve record this type already carries. The 32-byte
  leftovers carry an object id at +8. And every leftover of both sizes has `01`
  **ten bytes from the terminator**, which is where an element's short trailer puts
  its own marker.

#### `0x0B` has a SECOND element trailer, opened by the trailing block: 3,861 of 4,325

The residue was not noise, and it said exactly what it wanted. Of the bodies that
walked all their entries and stopped short, **98 were 7 bytes short and 48 were 12
bytes short, all at flag 0** -- where the flag says the trailer should be 19.

- **The first byte of the element's trailing block is a second flag.** It is `1` in
  exactly those 146 elements and `0` in the 3,108 that frame at flag 0. A clean
  split, not a majority. When it is 1 the head is **`14 + 5 * k`**, with `k` the byte
  seven into the trailer: `k = 0` in 98 elements and `k = 1` in 48.
- **Every part beats its rivals corpus-wide, scored by whole-body closure.**

  | part | chosen | rivals |
  | --- | --- | --- |
  | which block byte opens it | `block[0]`: **3,861** | the other eleven positions: at most 3,719 |
  | the extended base | `14`: **3,861** | 10, 12, 13, 15, 16, 19: **3,715 each** -- they add nothing at all |
  | which byte scales it | `trailer[7]`: **3,861** | bytes that are merely zero in this group: 3,813, closing the `k = 0` bodies and failing the `k = 1` ones |
  | the step | `5`: **3,861** | 0, 3, 4, 6, 7, 8: 3,206 -- a wrong step loses bodies the plain branch had |

- **Coverage rises 3,715 -> 3,861 of 4,325 (85.9% -> 89.3%)**, and the plain flag
  counts are **unchanged at 3,108, 575 and 32**. The 146 are bodies that framed under
  neither branch, not bodies moved between them.
- **The step of 5 is borrowed, not established.** Only `k = 0` and `k = 1` occur,
  which is two points; the reader refuses anything above 1 rather than extrapolating.
  This is weaker evidence than the plain flag, where three values are each observed
  closing bodies, and the reader says so.
- **Every element that takes the extended branch carries plain flag 0** -- all 146.
  Recorded rather than required: making it a rule would hide the day it stops holding.

#### `0x0B`'s body ends with a fixed 12-byte block

- **4,141 of 4,325 bodies (95.7%) end with `00 00 01 00 00 00 00 00 00 00 00 00`
  immediately before the u32 terminator**, and so do 3,713 of the 3,715 that framed
  before this batch. The two exceptions carry `00 04 01 01` in the first four bytes
  with the same eight zeros, so the shape is **four bytes that vary and eight that are
  zero**. Over the 3,861 close blocks the frame now reaches, the eight zeros hold
  **3,861 of 3,861**, against **0** for the same width read four bytes earlier.
- The trailer is therefore written as a head of `7 + 5 * flag` plus this 12-byte
  close (19 = 7 + 12, 24 = 12 + 12, 29 = 17 + 12). **For these bodies that split is
  not an independent fact** -- the trailer is the last thing before the terminator,
  so "the trailer ends with the block" and "the body ends with the block" say the
  same thing. It is written that way because the block is the same 12 bytes whether
  or not the body frames, which makes it a property of the format rather than of the
  walk.
- **This is why the extended head is `14 + 5k` and not `26 + 5k`:** the close is
  accounted for once, separately, in both branches.
- **The residue always ends at this block**, in every failing class. So the 464
  remaining failures misread body *interiors*; none of them has a different ending.

#### `0x0B` has a trailing section, and it brought the multi-entry layout into the frame

After the entry walk falls short, **one byte then the same 12-byte block and the same
trailer an element ends with** lands exactly on the terminator in **76 bodies**, all
of them multi-entry. Coverage **3,861 -> 3,937 of 4,325 (89.3% -> 91.0%)**.

- **The prefix is discriminated:** width 1 closes 76 and every other width from 0 to 9
  closes at most 10. The section costs nothing, because it is only attempted once the
  walk has already failed -- it can add bodies, never take one.
- **A length-only control closes 100, not 76, and the extra 24 are refused.** Accept
  any of the four observed trailer lengths and ignore the flag, and 24 more residues
  land exactly; but their block opening byte is `0xAF`, `0x55` or `0x59` and their
  selector is scattered. That is a total-length coincidence, not a section. *When a
  reading closes more cases than the rule that motivated it, the excess is the thing
  to look at, not the win.*
- The residue sizes made this findable: **32, 37, 39 and 44 are `13 + {19, 24, 26,
  31}`** -- 13 bytes plus each of the four trailer lengths already established on
  single-entry bodies.
- **The layouts that do NOT explain it, ruled out first.** A uniform wider entry
  header: no width from 8 to 200 closes any multi-entry body. All headers first and
  then all elements: likewise none. The element count somewhere other than `+44`: the
  sweep gives 3,861 at `+44` and at most 69 at every other offset. And the residue does
  not parse as more elements -- 122 of 142 stop at the first one. *Single-entry bodies
  cannot tell the interleaved layout from the headers-first one; both score 3,861. A
  corpus that cannot distinguish two readings is not evidence for either.*

#### Four of my own claims were true only because every framed body had one element

The coverage gain broke four gates at once, and every one of them was right to break.
**This is the degenerate-input trap in its purest form: the corpus could not
distinguish the claim from a weaker one, so the claim looked exact.**

| claim | how it looked | what it is |
| --- | --- | --- |
| the element count is a count | untestable -- **1 in every framed entry** | now read at **0, 1, 2 and 3** (130, 3,871, 8, 4) with the walk consuming exactly that many |
| the entry count is a count | untestable -- **1 in every framed body** | now **1 in 3,861 and 2 in 76** |
| the word at header `+4` is a source id | **3,715 of 3,715** headers | **3,937 of 4,013** headers, but **3,937 of 3,937 bodies**: in a two-entry body **exactly one of the two** entries names a declared source |
| the 12-byte close ends in eight zeros | **3,861 of 3,861** trailers | its **content** is body-final -- **3,937 of 3,937 final** blocks, **0 of 38 interior** ones -- while its **length** is per element |

- **The last of these is the one worth keeping, and it splits in two.** Before this
  batch I could not tell whether the 12-byte close belonged to the element or to the
  body, because every framed body had exactly one element and the two readings made
  identical predictions.
  - Its **content** is body-final. Interior blocks end in eight zeros **0 of 38**
    times against **3,937 of 3,937** for final ones.
  - Its **length** is per element, and that is the opposite answer. Charging the 12
    bytes to every element closes **3,937**; charging them only to the last element of
    an entry, only to the last of the body, or only to the first each close **3,925**,
    and charging them to none closes **58**. So an interior element does consume a
    12-byte close -- it simply does not hold the eight-zero pattern.
  - *These are two different claims about the same twelve bytes, and the first draft
    of this note ran them together. A field's length and a field's content are
    separately testable and can have separate answers.*
- The source join is now counted **per body**, not per header. Per header the same
  data reads as a regression from 100% to 98.1%; per body it is exact, and the 76
  "misses" are one half of each two-entry body.
- The retired element-count gate had said: *"If a body ever closes with an entry
  declaring two elements, this fails -- and that failure is the good news, because it
  means the reading has finally been tested. Change it then, not before."* That is
  exactly what happened, so it was replaced rather than relaxed. *Write the tripwire
  that tells you when your own caveat has expired.*

#### EVERY ENTRY AFTER THE FIRST BEGINS 4 BYTES EARLY: 3,937 -> 4,115

Identifying `+32` as a float handed over a second content check, and with two of them
the second entry header could be **located** rather than assumed.

- Two checks identify a first entry header, and both hold in **100%** of them: the word
  at `+4` is a source id the same body declares, and the word at `+32` is a plausible
  float.
- At the place the reader used to put the second header, **neither holds -- 0 of 216**
  two-entry bodies.
- Scanning every offset from `-32` to `+32` from the end of entry 1, **exactly one**
  passes either check: **`-4`**, in 168 of 216. **No other offset passes even once.**
- Scored corpus-wide the step-back closes **4,115** against 3,937 without it, and every
  rival step -- 2, 6, 8, 12, 16 -- lands at **3,861 to 3,863, below the baseline**.
- **The control flipped to agreement.** The same `+32` offset in later entry headers
  scored **2 of 26** while they were read four bytes late; with the step-back it scores
  **210 of 210**. *A control that becomes confirmation when an offset is corrected is
  the strongest evidence the correction was right.*
- **Which side owns the four bytes is not determined** and the reader says so: either
  the element walk over-consumes by four in the last element of a non-final entry, or
  the entry header is longer than 48. The reader compensates where the evidence is
  rather than inventing a field.
- The frame is now much simpler. 4,453 entries over 4,115 bodies; **338 declare zero
  elements and 4,115 declare one**, and the 338 step-backs are exactly those empty
  entries. Entry counts are exercised at **1, 2, 3, 4, 5 and 8**. Fences fall from 388
  to **210**.

#### RETIRED: the trailing section was patching this, and WITHDRAWN: the interior blocks

Two earlier results do not survive the step-back, and both are removed rather than left
standing.

- **The "trailing section"** -- one byte, a block and a trailer, which closed 76
  multi-entry bodies -- **never fires** under the corrected frame: 0 of 4,325. It was
  compensating for the misplaced header. *A reading that compensates for a misplaced
  field is worse than no reading, because it makes the misplacement look closed.* The
  code and its gate are deleted.
- **The interior close blocks are withdrawn.** "The eight zeros belong to the block
  ending the BODY, not to each element" rested on interior blocks scoring **0 of 38**
  -- and those 38 existed only because the trailing-section reading placed a second
  header four bytes late. Under the corrected frame every framed body carries exactly
  one element, there are no interior blocks, and **the question is untestable again**.
  *Evidence produced by a reading is only as good as the reading.*
- The managed suite caught this too: its synthetic multi-entry body stopped framing the
  moment the reader learned the step-back, which is the test doing its job.

#### `0x0B`'s word at `+32` IS A FLOAT, and negative zero is why it hid

Nine id populations had failed on this word: object references same-bank and
corpus-wide, source ids, media ids, **bank ids**, **STMG's 578 ids**, fixed-point
fractions, and the 24,231 identifier literal hashes. The last two populations only
existed after this batch framed STMG and published bank ids; both came back with **no
offset matching at all**.

Read as a **float**, in first entry headers it is **1,953 of 1,953 plausible** -- 823
exactly **negative zero**, and the rest in **-9.83 to 7.81** with most of them
negative.

| reading | plausible | share |
| --- | --- | --- |
| `+32` in the first entry header | **1,953 / 1,953** | **100%** |
| the same span at `+28`..`+31`, `+33`..`+39` | 202 / 3,116 | 6.5% |
| **`+32` in a LATER entry header** | **2 / 26** | **7.7%** |

- ***The `-0.0` is why this took so long.*** A band test that asks for
  `abs(v) > 1e-4` throws away `0x80000000` as "not a float" -- and that is **42%** of
  the field. **A field whose unset marker is negative zero looks unlike a float to any
  test that treats zero as uninteresting.** My own earlier float test on this header
  covered `+12` and `+20` and scored `+32` at 60.5%, which read as a miss.
- **The later-entry control is the sharp one, and it is a finding in itself.** The same
  offset one entry later scores 2 of 26, the rate of a shifted read. So the word is a
  float in the first entry header and **is not one after it** -- independent evidence
  that a later entry is **not the same 48-byte layout**, which is exactly what the 76
  trailing-section bodies have been hinting at.

#### `+12`/`+20`: TEN populations eliminated, and what that leaves

The pair is now tested against everything the shipped data contains.

| population | size | matches at `+12`/`+20` |
| --- | --- | --- |
| object references, same bank | -- | 0 |
| object references, corpus-wide | 238,807 | 0 |
| source ids | 62,273 | 0 |
| media ids | 61,333 | 0 |
| bank ids | 20,863 | 0 |
| `STMG` ids | 578 | 0 |
| identifier-shaped literal hashes | 24,231 | 0 |
| **every raw metadata literal hash** | **49,324** | **0** |
| floats | -- | not plausible |
| fixed-point fractions of 2^32 | -- | **2.9%**, see below |

- **The fraction test, done properly with controls.** Several of the most common values
  *look* like fractions -- `0xAAAAAAA3` is near 2/3, `0x71C71C6A` near 4/9,
  `0x0F0F0F18` near 1/17 -- and that appearance is misleading. Asking for the closest
  rational with denominator <= 64 and an error within 1 ULP: `+12` scores **2.9%** and
  `+20` **2.8%**, against **100%** at `+28` and **96.4%** at `+36`, the two fields
  already known to be fractions. The near-misses are off by 7 or 8 ULPs, and a real
  fraction field here is exact. *An eyeball reading of the top few values is not a
  measurement; the field that IS this encoding scores 100%.*
- **What the values look like:** 373 distinct over 1,317 occurrences, so each repeats
  about three and a half times; popcount centred on 16, which is what random 32-bit
  values look like; range 1 to `0xFFFFFFFF`; equal to each other in **998 of 1,158**
  headers where both are nonzero.
- **So the pair is a hash or an id in a namespace the shipped files do not contain.**
  Random-looking, repeating, 32 bits wide, and matching nothing the game ships --
  including every string literal in `global-metadata.dat` at a chance rate of 0.05.
  Further population tests on this field are not worth running until a new namespace
  appears; the shipped ones are exhausted.

#### The step-back is per ENTRY or per ELEMENT, and this corpus cannot tell

Applying it between elements as well as between entries changes nothing -- 4,115
either way -- because **every entry that frames carries at most one element**, so the
between-elements case never arises. Recorded as an indeterminacy rather than a choice:
the reader does it per entry because that is where the evidence was, and a corpus with
a multi-element entry would settle it.

#### `0x0B`'s `+12` and `+20` are one field written twice

- Where both are nonzero they are **equal in 998 of 1,158 (86.2%)**. They share a top
  value and a distribution: minimum 1, median about 2.18e9, maximum `0xFFFFFFFF`.
- **Still unidentified.** The same nine populations failed on them. This is a
  structural observation, gated so it cannot quietly stop being true while the note
  claims it.

#### CORPUS PROVENANCE: 10 banks ship twice, and one of them is the music bank

Looking at `0x0B`'s residue along a **provenance** axis instead of a grammar one
turned up something that qualifies a lot of numbers in this file.

- **All 4,325 type `0x0B` bodies live in 4 banks**, and bank **266542773** holds 4,260
  of them -- 2,130 in `audit_banks.pck` and 2,130 in `hotfix_main_b75.pck`, **byte-
  identical, all 2,130 of them**.
- Corpus-wide, **10 banks appear in more than one package**, duplicating **6,104 of
  323,049 objects (1.9%)**. Bank 266542773 alone accounts for 6,052 of those.
- **The duplication is concentrated in exactly the music types:**

  | type | counted | distinct | duplicated |
  | --- | --- | --- | --- |
  | `0x0A` | 4,158 | **2,112** | 49.2% |
  | `0x0B` | 4,325 | **2,195** | 49.2% |
  | `0x0C` | 742 | **373** | 49.7% |
  | `0x0D` | 2,431 | **1,230** | 49.4% |
  | `0x11` | 2,645 | 2,427 | 8.2% |
  | every other type | -- | -- | **under 0.2%** |

- **99.7% of music objects (11,507 of 11,656) live in that one bank.** The music family
  is one authored bank, shipped twice.
- **The closure RATE is unaffected**, because an exact copy closes exactly when its
  original does: `0x0B` is 3,937 of 4,325 and 1,998 of 2,195, both **91.0%**. What
  changes is the evidence base -- **197 distinct bodies are unexplained, not 388** --
  and the music-family size, **5,910 distinct rather than 11,656**.
- *A percentage over duplicated data is still the right percentage and the wrong
  sample size.* The audit now publishes the distinct count beside the total and gates
  their arithmetic, so the day a second bank starts shipping twice, something says so.
- **This is the cross-package trap for the FOURTH time.** A per-package census cannot
  see it: each package reports the bank once and looks unremarkable. After the media
  ids, the source ids and the plugin names, the rule is now unavoidable -- *if two
  sides of a question can land in different `.pck` files, the question belongs in the
  pass that unions them.*

#### TWELVE BYTES AN ELEMENT that are always zero, and were never checked

Looking for a condition that could drive a conditional element rule meant looking at
the element bytes nobody had read.

- The element head is 5 bytes and **only byte 0 was used** (the run count). Bytes
  **1, 2 and 3 are zero in all 3,861** first elements that frame.
- The run header is 11 bytes and **only byte 7 was used** (the record count). **Nine of
  the other ten are zero** in every run header that frames -- only byte 3 varies.
- **Enforcing all twelve costs nothing: 4,115 bodies frame either way.** 30,582
  reserved bytes are now validated where the reader used to walk straight through
  them. *A field that is always zero is still a field, and a parser that does not check
  it will happily walk through garbage.*
- **It moves the fences to where the problem is.** 115 bodies are now rejected at
  `element_head_reserved_byte_is_not_zero`, and `range_element_trailer_flag` falls
  from **111 to 14** -- the desynchronisation is caught three steps earlier, at its
  cause instead of its symptom.

**A control that could not work, recorded rather than hidden.** Reading the same three
offsets five bytes on scores **11,774 zero of 12,843 (91.7%)**, because it lands on the
run header's *own* zero-invariant bytes. The neighbourhood is zero-rich, so shifting
within it cannot discriminate. ***A control has to land somewhere the claim does not
already predict.*** The gate publishes the number instead of pretending it
discriminates, and the evidence it rests on is the pair a bad control cannot produce:
coverage unchanged at 4,115, and 115 bodies caught that were previously walked through.

#### `0x0B`'s residue is at a practical ceiling: six mechanisms swept and excluded

Every mechanism this format's own idioms suggest has now been tried on the 210, and
each was scored over the whole corpus rather than on the failing slice.

| mechanism | search space | best result |
| --- | --- | --- |
| a different uniform element grammar | ~2,300 shapes | 150-2,841 vs **4,115** |
| an extended entry header behind a flag | 1,728 triples | +8, and it fires on 14 bodies closing 0 of them |
| a different source-record width | 8..32, and a separate width after the first | 4,041 vs **4,115** |
| a gap before the entry count | -12..+16 | closes **nothing** when applied to all bodies |
| the step-back applied per element | -- | identical, the case never arises |
| shifting the failing element | -40..+40 | repairs **20 of 182**, at two inconsistent deltas |

Two further checks close off the easy explanations:

- **They are not dead data.** Every one of the 2,195 distinct `0x0B` objects is
  referenced by a `0x0A` counted array -- **100% of the framing ones and 100% of the
  failing ones**. The residue is live, referenced music tracks.
- **The surplus is not a constant.** For the 22 failing bodies simple enough that the
  frame can predict a length from their declared counts, the actual length exceeds it
  by 16, 38, 49 or 50 -- inconsistent. For the other 188 the element does not parse
  from its declared start at all, so no length can be predicted.

**The position, stated plainly: numeric type `0x0B` is at 4,115 of 4,325 counted and
2,087 of 2,195 distinct -- 95.1% either way -- and the residue resists every mechanism
the format's own vocabulary suggests.** Progress on it needs evidence this corpus does
not contain, not another sweep. *Recording a ceiling is worth more than a sweep that
was always going to fail, and cheaper than running it twice.*

#### The 210 scale with body complexity, and the source region is NOT the cause

With the twelve reserved bytes now fencing at the cause, the failing bodies can be
characterised properly.

- **Shifting the failing element repairs only 20 of 182**, at two inconsistent deltas
  (`-36` and `+17`). The desynchronisation begins earlier than the element that
  reports it.
- **Failure rate rises sharply with body complexity**, and the source count is the
  sharpest predictor:

  | declared sources | closing | failing | fail rate |
  | --- | --- | --- | --- |
  | 1 | 4,041 | 172 | **4.1%** |
  | 2 | 70 | 28 | **28.6%** |
  | 4 | 2 | 6 | **75%** |
  | 0 | 0 | 4 | 100% |

  Entry count and body length track it: 1 entry 3.9%, 2 entries 15.0%, 4 entries
  37.5%; bodies under 200 bytes 3.6%, 200-300 14.4%, 400+ 40%.

- **But the source region is framed correctly, and two sweeps say so.** A separate
  width for records after the first: **14 is uniquely best** over 8 to 32 (4,115
  against 4,041 for every alternative). A gap between the records and the entry count:
  **0 is uniquely best** over `-12` to `+16`, and applying any gap to all bodies closes
  **nothing at all**.
- So the correlation is **complexity, not a located mechanism** -- exactly what a
  per-element error probability produces. *A predictor is not a cause; a sweep that
  confirms the field it points at is the difference.*
- One provenance note: bank **4247105105** in `init_banks.pck` fails **5 of 13
  (38.5%)** against 4.8% for the music bank. Thirteen bodies is too thin to conclude
  from, and it is recorded as a lead rather than a finding.

#### Where the remaining 210 actually go wrong, and one methodological trap

Applying the content checks that found the four-byte step-back to the residue.

- **206 of the 210 failing bodies have a first entry header that passes both checks.**
  The walk starts in the right place and loses synchronisation later.
- **The 111 trailer-flag fences are a symptom, not a cause.** At the point of failure
  the trailing block's opening byte is scattered noise -- 4, 129, 2, 0, 100, 247, 82,
  15 -- so the walk is already lost before it reads the flag. The 36 that fail at a run
  count and the 21 at an element head are earlier detections of the same loss.
- **The zero-element entry advance is confirmed at 48.** Sweeping it from 17 to 52,
  only 48 reaches 4,115; every other value drops to 3,861.

**The trap, which nearly cost a batch.** Scanning *every* offset of a body for a window
passing both content checks produces coincidences: **130 failing bodies show a second
window exactly 17 bytes after the first**, consistently enough to look like a real
17-byte entry header. Sweeping that as a rule closes **3,861** -- below the baseline --
so it is a false positive of the scan, not a layout.

*The `-4` finding was clean because the scan was restricted to `[-32, +32]` and had a
unique answer.* A content check strong enough to locate a field within a restricted
window is not automatically strong enough to survive scanning a whole body. **When a
scan widens, its coincidence rate widens with it, and consistency across bodies is not
proof -- the same coincidence recurs for the same structural reason.**

#### Two exhaustive searches over `0x0B`'s 388, both negative

The method that settled STMG's middle block -- enumerate every shape and let closure
discriminate -- applied to `0x0B`. Both searches came back empty, and that is worth
recording precisely so the ground is not re-walked.

**1. No uniform element grammar beats the shipped one.** Over the whole space of
element-head bytes 1..12, run-header bytes 5..16, record-count offset 0..runheader-1
and run-trailing bytes 0..3 -- about 2,300 combinations -- **656 close at least one
currently-failing body and none reaches 3,937**.

| gained of the 388 | head | run header | count at | trailing | whole corpus |
| --- | --- | --- | --- | --- | --- |
| 88 | 11 | 14 | +9 | 0 | **150** |
| 81 | 5 | 16 | +7 | 1 | **2,841** |
| 0 | **5** | **11** | **+7** | **1** | **3,937** (shipped) |

The shipped grammar is a **local maximum over the entire four-parameter space**. Every
shape that gains on the residue collapses the corpus.

**2. No extended entry header selected by a flag.** The trailer turned out to be
`7 + 5*flag` normally and `14 + 5*k` when the trailing block opens with 1, so the same
idiom was tested on the entry header: 48 bytes normally, `48 + extra` when some header
byte equals some value. **1,728 (selector, value, extra) triples**; three beat the
baseline, by **+8, +2 and +2**, with **zero losses**.

- The best is `header[44] == 3 -> +12`. Zero losses looked encouraging until the
  mechanism was checked: **`header[44]` is the low byte of the element count**, the rule
  fires on **14** bodies whose first entry declares 3 elements, and it closes **0 of
  those 14**. The +8 comes from later entries in multi-entry bodies, not from the
  population the rule describes.
- All three rejected. *A rule that gains without losing is not thereby right; check
  that the gain comes from the cases the rule is about.* Out of 1,728 trials a maximum
  of +8 on 388 candidates is what noise looks like.

**So the 388 need something that is neither a global grammar change nor a
flag-selected header variant.** Both of the format's known idioms have been tried and
neither fits.

#### What does NOT explain `0x0B`'s remaining 388, tested and eliminated

Recorded so the same ground is not re-walked. Each was scored over the whole corpus
by whole-body closure, not on the failing slice alone.

| hypothesis | result |
| --- | --- |
| a wider entry header, uniform | **no width from 8 to 200** closes a single multi-entry body |
| all headers first, then all elements | likewise none; and note single-entry bodies score **3,861 either way**, so they cannot tell these two layouts apart at all |
| the element count somewhere other than `+44` | `+44`: **3,861**; every other offset from 0 to 44: **at most 69** |
| the residue is more elements | **122 of 142** stop at the first one |
| a different source-record width | no width from 8 to 32 rescues any of the 50 out-of-range bodies |
| a missing field before or after the entry count | gaps 0-16 either side rescue **2** at post-8, and cost the rest of the corpus |
| the close belongs only to some elements | see above -- every element, **3,937** against 3,925 |

- **The 119 trailer-flag fences almost all land at element index 1**, in single-entry
  bodies declaring two or more elements, with the flag and the block's opening byte
  both scattered. So the walk is already lost by then: **the first element's length is
  wrong**, not the second element's flag.
- **Shifting the second element does not repair them.** Of the 128 single-entry
  multi-element bodies, only **20** close at *any* offset in `[-40, +80]`, and those
  20 split between `-36` and `+17`. A single repeated delta would be a missing fixed
  field; this is not one.
- The 50 bodies whose counts come back wildly out of range have leading byte 0 and
  declared source counts of 0 to 4 -- indistinguishable on both from the 3,937 that
  frame.

#### `0x0B`'s residue, measured rather than guessed

(Superseded in part by the section above: 76 of these now frame.) Of the 4,325
bodies, **306 declare more than one entry** (240 declare 2, 34 declare
3, 16 declare 4, 2 declare 5, 10 declare 6 or more) and **4 declare none**. Among the
4,019 single-entry bodies, **128 declare more than one element** (113 declare 2, 14
declare 3, 1 declares 4).

- **146 of the multi-entry bodies walk every entry and leave residue**; 100 more
  desynchronise at a run count, which is what a wrong entry-header width looks like.
  The entry header is not known to be 48 bytes for entries after the first.
- The multi-entry residues **contain curve records** -- `0.75, 1.0, code 9` and
  `float, 1.0, code 4` among them -- so they are unread element data, not padding.

#### Correction: `0x0B`'s run splits 11 + 12n + 1, and its records ARE curve records

- **The run header is 11 bytes, not 12**, followed by the records and then one
  trailing byte. `11 + 12n + 1` and `12 + 12n` are **the same length**, so the body
  frame closes the same 3,715 bodies either way -- which is exactly why the split
  could not be settled by closure and had to be settled by what the records contain.
- Under the 11-byte header **all 4,086 records carry an interpolation code of 0 to 9**,
  spanning every value with no gaps: `9`:2017, `4`:1003, `1`:485, `7`:280, `8`:103,
  `0`:77, `5`:74, `2`:25, `6`:14, `3`:8. Under 12 the codes are noise and only the
  zeros pass. The control reading -- the same word one byte either side -- lands in
  range **377 of 9,376** times.
- **This corrects my own earlier measurement and restores the memory claim it
  appeared to contradict.** Reading the records at the 12-byte boundary showed codes
  in range for only 1,644 of 4,304, all of them zero, and I nearly recorded that the
  curve record is *not* in `0x0B`. The boundary was off by one byte; the claim was
  right.
- So the twelve-byte curve record is confirmed in **three** numeric types by a test
  with a working control: `0x08` and `0x12`'s tail units (314 records, all in range,
  codes 9/4/7/1/0/8/5) and `0x0B`'s element runs.
- **The lesson, and it is the sharpest form of one this session keeps teaching.** Two
  layouts of equal total length are indistinguishable by closure *no matter how large
  the corpus*. When a frame closes and its contents look like noise, suspect the
  internal split before suspecting the claim -- and settle it on content, because
  length cannot.

#### The region after `0x0A`'s `0x0B` reference is a FLOAT BLOCK, and `+4` is the exception

Reading every word after the reference as a float and asking how many are finite and
in 1e-2..1e4:

| offset | nonzero | plausible float | note |
|---|---:|---:|---|
| `+4` | 2,130 | **14%** | the odd one out |
| `+8` | 3,748 | **95%** | median 5.689, mode **4.4766** (1,565) |
| `+12` | 311 | 87% | |
| `+16` | 334 | 95% | |
| `+20` | 3,816 | **93%** | already recorded as an authored value |

- **`+8` is a float field and had never been identified.** The reader uses it only as
  the *control* for the `+4` fraction test -- where it works correctly, since a float
  is not a small rational -- but nothing ever asked what it is in its own right. *A
  word used as a control is still a field; passing as a control says what it is not,
  never what it is.*
- So the block after the `0x0B` reference is mostly floats, and `+4` is the one word
  that is not. Its values -- `0x55555555`, `0xAAAAAAAB`, `0x89D89D8A`, `0xE8BA2E8B`,
  `0x71C71C71` -- are `p/q` in Q32 for `q` in 3, 7, 9, 11, 13, 49. That it differs in
  kind from its neighbours is now measured rather than assumed.
- A test I wrote to check whether those values have repeating binary expansions
  returned 100% for **every** offset including the floats, so it discriminates nothing
  and is **discarded**. It is recorded here only so the next attempt does not rebuild
  it. *A structural test that passes everything has not been run; it has been
  mis-written.*

#### QUALIFIED: `0x0A`'s "fraction" is a mixed value set, not a fraction field

The discriminator that separates a real fixed-point field from a test artefact is
**how many denominators it uses**, and applying it to `0x0A` qualifies a finding I
strengthened two batches ago.

| field | passes `IsSmallFraction` | distinct fractions | denominators |
|---|---|---:|---|
| `0x0B` `+28` | 100% | **5** | **3, 6, 2** |
| `0x0B` `+36` | 96.3% | **18** | **3, 6, 2**, then a tail |
| `0x0A` fraction | 67.4% | **42** | 3, **13, 11, 7, 23, 9, 19, 49** |
| `0x0B` `+12` | 42.0% | **76** | 13, 17, 7, 3, 23, 19 -- no family |

- `0x0B`'s established fields use a **tight, authored family**: 1/3, 2/3, 1/6, 1/2,
  5/6. `0x0A`'s spreads across denominators 13, 11, 49, 23 and 19, which no one
  authors.
- **The field's real shape is a small repeated value set**: only **237 distinct
  values** over 2,130 bodies, the ten commonest covering **50%**. Its top value is
  `0x408F4000`, which is the **float 4.4766**, seen 203 times -- and the control word
  four bytes on holds that same value **1,565** times. So the field mixes
  float-shaped and fraction-shaped members.
- **What survives**: the field is still sharply different from its control -- 67.4%
  against 3.2%, a 20x margin, and random words pass at 0 of 2,130. Something real is
  there. **What does not survive**: calling it a fixed-point fraction. That reading
  over-reads a permissive test.
- *`IsSmallFraction` with denominators to 64 is too generous for structured data. It
  passes 42% of `0x0B`'s `+12`, which is definitely not a fraction field. The
  discriminating question is not "is this value a small rational" but "does this field
  use a handful of denominators".*
- `0x0B` `+44` is confirmed as the element count from the other side: raw values `1`
  in 3,903 entries, `2` in 133, `3` in 14, `4` in 1.

#### The fixed-point fraction is in two types, and they are NOT the same quantity

Three measurements, and the conclusion is a negative worth keeping.

1. **The `0x0A` fraction reading is much stronger than previously recorded.** Under
   the reader's own tolerance (16 parts in 2^32, denominators to 64): **1,435 of
   2,130** nonzero values are small fractions, the control word four bytes further
   on manages **121 of 3,748**, and **0 of 2,130 random 32-bit words** pass. The
   random control is the one that settles it -- a test that admitted arbitrary words
   would not have been evidence at all.
2. **`0x0A` -> `0x0B` does not carry the fraction.** For the 1,864 `0x0A` bodies with
   a nonzero fraction whose reference resolves to a framed `0x0B`, the value equals
   one of that `0x0B`'s two entry-header fractions in **58** cases. Shuffling the
   pairing gives **52**. That is chance, on the one edge in this format known to be
   one-to-one.
3. **The value distributions differ in kind.** `0x0B`'s entry fractions are a tight
   set -- 0, 1/3, 2/3, 1/2, 1/6. `0x0A`'s spread across 7/13, 1/3, 10/11, 2/3, 4/9,
   27/49, 4/7 and more, with denominators 7, 9, 11, 13, 49.

So the two types share an **encoding**, not a **meaning**. *A representation found in
two places is a lead, not a link -- test whether the values actually travel along the
reference before treating it as one.* The cheapest such test is the shuffle: score the
real pairing against a permuted one, and a difference of 58 against 52 says stop.

#### Four fields read in the 48-byte entry header -- and one caveat about the frame

Censused over the 3,715 entries of closing bodies only; an entry header from a body
that later fails says nothing, because the walk that reached it may be desynchronised.

| offset | reading | evidence | control |
|---|---|---|---|
| `+0`, `+8` | constant zero | 3,715 each | -- |
| `+4` | **source id, joined** | it is one of the source ids the **same body** declares: **3,715 of 3,715** | -- |
| `+16`, `+24` | a **symmetric float pair** | `low == -high` in **1,218 of 1,404** nonzero pairs; `low <= high` in 1,264 | the neighbouring word at `+12`: **0 of 1,391** |
| `+28`, `+36` | **fixed-point fractions of 2^32** | small rationals in **2,735 of 2,804** | the word at `+40`: **0 of 3,715** |
| `+40` | a **bounded float**, in every entry | 3,715 of 3,715 in 1e-3..1e4; range 3.951 to 10.1, median 7.548, 889 distinct | `+4` and `+12`: **420 of 4,806** |
| `+44` | element count | see below | -- |

- **The source id sits at record offset 5, which is NOT four-byte aligned.** Testing
  the 14-byte source record's aligned words -- 0, 4 and 8 -- against the header's `+4`
  finds **no match at all**; offset 5 matches **every one of the 4,321**. That is why
  this field read as unidentified for so long, and it is the second time in two
  batches that a field turned out not to be where alignment suggests. *A join that
  fails at every aligned offset has not been disproved; it has been tested at the
  wrong offsets.*
- **Nor are they among the audio-named literal hashes.** All twelve offsets score
  **0 of 4,321** against the 221 audio literal hashes the named-reach audit loads.
- *A correction on how I read that.* I dismissed this as "no discriminating power",
  which is backwards. With 221 hashes against 2^32, the expected chance matches over
  4,321 words is **0.0002** -- so the test can never produce a false positive, and a
  single hit would have been decisive. Finding none is a narrow but real elimination,
  not a failed experiment. **A test with a tiny false-positive rate is powerful for
  confirming and weak for refuting; say which of the two you got.**
- **The stronger test has now been run, and it is decisively negative.** Against the
  **24,231** distinct hashes of every identifier-shaped literal in
  `global-metadata.dat` -- not the 221 audio-filtered ones -- **all twelve offsets
  score 0**. Expected chance matches are **0.024**, so a single hit would have been
  conclusive and there are none.
- `scripts/audio_semantics/hirc_named_reach.py` already exposes `broad_literals()` for
  exactly this: identifier-shaped literals without the audio prefix vocabulary. **The
  population I said I would need was already a function in the repo.**
- So `0x0B`'s `+12`, `+20` and `+32` are eliminated as object references (same-bank
  and corpus-wide), source and media ids, floats, fixed-point fractions, **and name
  hashes**. Five populations, all negative, all properly powered.
- **None of the header words is a source id either.** Scored against the full
  source-id population, every offset including `+12`, `+20` and `+32` matches **zero**
  -- so those remain unread, now eliminated as object references, name hashes, floats,
  fractions **and** source ids.
- **The opaque words are not references.** Tested against the same-bank id set and the
  corpus-wide one, **none** of the twelve header words resolves to an object -- `+4`
  matches 8 ids out of 4,321 and the rest match zero. That confirms the standing note
  that `0x0B` points at media rather than objects, and closes "reference" as a reading
  for `+12`, `+20`, `+32` and `+44`.
- **`+12` and `+20` are not floats either**: only **2.0%** of their values land in
  1e-3..1e4, and they range over plus and minus 5e37. They remain unread.
- *A float field is not established by its own values being finite -- almost any
  32-bit word is a finite float. It is established by neighbouring words read the same
  way not being plausible.* Here `+40` is 100% in band against 8.7% for its
  neighbours.

- The float pair sits around plus or minus five: `(-5.16, +5.16)`, `(-4.84, +4.84)`,
  `(-5.48, +5.48)`. What it bounds is not claimed.
- The fractions read 0, 1/3, 2/3, 1/2 and 1/6 -- **the same fixed-point encoding
  `0x0A` carries**, which is now confirmed in two numeric types. Entries where both
  range words are zero are excluded, and a zero fraction is excluded, because zero
  satisfies both properties for free.
- **Both controls score exactly zero.** A word read one field away satisfies neither
  property in a single entry.

**The caveat, and it is about this reader rather than the format.** The word at `+44`
is read as an element count, and it is **1 in every one of the 3,715 entries the frame
closes**. Reading it as a count and reading it as the constant 1 produce the same
3,715 bodies, so **nothing in the corpus distinguishes them** and the "count" is a
hypothesis. Entries declaring 0, 2, 3 or 4 exist -- 370, 221, 48 and 7 of them -- and
every one is in a body that fails to frame.

This is stated as a gate, `the_type11_element_count_is_not_yet_a_count`, which holds
while the count is 1 everywhere. **When a body finally closes with two elements the
gate fails, and that failure is the good news**: the reading will have been tested for
the first time. *A field named as a count in a frame that never sees it take another
value has been assumed, not measured -- and the assumption should be visible in the
gate rather than buried in the field's name.*

#### The 119 trailer-flag fences: the size is found, the selector is not

- **A 17-byte trailing block instead of 12 closes 89 of the 119**, taking the body
  frame from 3,715 to 3,804 of 4,325. And `17 - 12 = 5`, the same optional five-byte
  step the element trailer and the entry widths both show.
- The size is discriminated: `(17,)` alone closes only **91** bodies, `(12, 16)`
  gains nothing, and `(12, 16, 17)` gains less than `(12, 17)` because 16 mis-matches
  first. So 17 is specifically right, not merely bigger.
- **But the selector is undetermined, and it is not adopted.** Thirteen byte
  positions separate the two groups perfectly -- element head bytes 1 to 4, run
  header bytes 0 to 4 and 7 to 9. The 89 are a completely homogeneous population:
  every one has exactly one run, that run declares zero records, and its head bytes
  1 to 4 are nonzero, while **2 of 3,804** twelve-byte-block elements have a nonzero
  head there and **none** has one run with zero records.
- So the two populations differ in every measured respect and nothing in the corpus
  can say which difference is the switch. Picking one of the thirteen would be
  arbitrary; taking `(12, 17)` as a fallback search would resolve the choice *by
  closure*, which is the exact failure mode that made the terrain codec's nibble
  reading look right for 6,442 files. **Measured, recorded, not adopted.**
- What would settle it: a `0x0B` body with a populated element head and more than one
  run, or one run declaring records. None exists in this corpus.

**A second property, measured later and worth only what it is worth.** Under the
17-byte block the fenced elements come out at size **53** in 93 of the 119 and **41**
in 20. Every element size closing bodies produce is of the form `36 + 12a + 5b` --
36, 41, 72, 77, 84, 89, 96, 120, 125, 137 -- and 53 fits it as `36 + 12 + 5`. So the
reading yields family-consistent sizes rather than arbitrary ones.

*But the family test is weak and saying so matters more than the result.* With 12 and
5 coprime, every size above **79** is representable, so the test is **vacuous** there;
across 36 to 139 it rules out only **22 of 104** candidates, or 21%. Size 53 passing
is corroboration, not evidence, and it does not change the standing conclusion that
the 12-vs-17 selector is undetermined. *Check a length model's Frobenius number before
quoting it -- this is the second length family in this format where most of the range
is free.*

### THE 218 ARE MOSTLY NOT AN ELEMENT PROBLEM AT ALL

Reading one failing body against a closing one -- the method that cracked `0x08`,
rather than the ten enumerations that did not -- settles where the problem lives.

- **Every one of the 3,715 bodies that frames has exactly ONE entry carrying exactly
  ONE element.** No exceptions. The entry/element shape `(1, (1,))` is the only shape
  the reader has ever parsed successfully.
- **142 of the 218 declare an entry with ZERO elements**, in shapes like `(2, (0,0))`
  54 times, `(2, (0,2))` 32, `(2, (0,1))` 24, `(3, (0,0,0))` 22. **No closing body has
  that shape.** Four more declare zero entries.
- So for most of this bucket the element walk is not at fault. **The multi-entry
  layout has never been parsed**, the 48-byte header width is verified only for the
  single-entry case, and the entry count -- like the element count already gated -- has
  never been read at any value but 1 by a successful walk.
- **The remaining 70** have the same `(1, (1,))` shape as every closing body. Those,
  and only those, are a genuine element-level mystery.

**The bucket decomposed, by (zero-element entries, residue bytes):**
`(0,12)` 48, `(2,32)` 36, `(1,44)` 24, `(1,32)` 22, `(3,112)` 16, `(0,16)` 10,
`(2,44)` 8, `(2,37)` 8, `(0,49)` 6, `(0,38)` 4.

- **The residue does not scale with the number of zero-element entries.** Two zero
  entries with a 32-byte residue is 16 each; one with 44 is 44; three with 112 is
  37.3. No constant per entry, so the multi-entry layout is not "a fixed extra block
  per empty entry".
- **The 48 bodies with the closing shape and a 12-byte residue**: the residue is
  `00 00 01 00 00 00 00 00 00 00 00 00` -- a mostly-zero twelve bytes with `01` at
  offset 2. It passes a curve-record test, but only as `(0.0, 0.0, 0)`, which **a run
  of zeros passes for free**. Not a curve record.
- **Not a doubled trailing block either.** A 24-byte block closes **0** of 4,325 and a
  36-byte block 0, against 3,715 for 12.

*Four more readings eliminated. The pattern across this whole bucket is that every
candidate that closes anything closes only the degenerate members -- zero runs, zero
records, all-zero blocks -- and the content test catches each one. That is now the
single most reliable signal in this investigation: if a reading's successes are all
zero-filled, it is wrong.*

*Ten hypotheses about element widths failed because the residue was never mostly an
element problem. When a residue resists every reading of structure X, check whether
the failing bodies even have the same shape at level X-1 as the ones that work.* Here
one query -- the distribution of (entryCount, elementCounts) over closing versus
failing bodies -- would have redirected the whole investigation.

Gated: `the_type11_element_count_is_not_yet_a_count` now also refuses if the entry
count is ever read at another value in a closing body, which would mean the
multi-entry layout had finally been parsed and this note needed revising.

#### The 218 are a PARTIAL ELEMENT, mis-entered by exactly four bytes

Applying the lesson that closed `0x08` -- when a walk desynchronises, look for the
next occurrence of something it already parses correctly:

- **152 of the 218 residues END with a valid element trailer** -- 122 with the 19-byte
  form, 26 with 24, 4 with 29. So the residue is not extra data appended to a finished
  body. It is the **tail of an element the walk entered too late**.
- Taking the trailer off leaves an element body, and **104 of those 152 are exactly
  four bytes short of `17 + 12k`** -- 13 where 17 is wanted, 25 where 29 is, 93 where
  97 is. The walk over-consumes by **4 bytes** in the element before it.
- **No global constant change accounts for it.** Head 5->1 closes 10 bodies, block
  12->8 or 12->16 closes 0, trailer 19->15 or 19->23 closes 0, head 5->9 closes 0.
  The chosen `(5, 12, 19)` closes 3,715 and nothing else comes close.

**ELIMINATED, and the "four bytes" framing with it.** I read the shortfall as one
element consuming four bytes too many. Every version of that fails:

* shortening each element in turn by four and re-running the walk: **0 of 322**;
* *growing* each element in turn by four: **0 of 322**;
* shortening one element by four **and** taking one extra element at the end, which is
  the only way a shift and the entry's element count can both be satisfied: **0**;
* alternative entry-header widths (44, 52, 56) and element-count offsets (4, 8, 40,
  48): **0** each, against 3,715 for the chosen 48 and +44.

So "four bytes" is not a walk error at all. It is an **arithmetic property of the
residue lengths**: the residue bodies are `13 + 12k` -- 13 in 66 bodies, 25 in 30, 37
in 4 -- which is four less than the `17 + 12k` a complete element body takes. That is
a description of the residue, not a diagnosis of the walk, and I turned one into the
other without checking.

**Also eliminated again, with the content test this time.** The residue lengths are
consistent with a 1-byte-head element -- 13 is `1 + 12`, 25 is `1 + 12 + 12`, 93 is
`1 + 80 + 12` -- but reading them that way still closes only the same **66**, every
one with **zero runs and therefore zero records**. The interpolation-code test has
nothing to check, so the arithmetic consistency is all there is. Third time this
reading has been measured and third time it is degenerate.

**What survives, and it is still the most useful thing known about this bucket**: 152
of the 218 residues end with a valid element trailer, so they are element *tails*
rather than appended data. The mechanism that leaves them is not a single mis-sized
element.

*Searching for a flag also failed for a reason worth keeping: once a walk
desynchronises, every element after the divergence is noise, so comparing the LAST
element of a failing body against good ones compares nothing. No byte separated the
two groups, and that result means nothing either.*

#### FIVE eliminations on the 218, so the next attempt does not repeat them

The residue of numeric type `0x0B` bodies that leave real content before the
terminator. Sizes: `32`:58, `12`:48, `44`:32, `112`:16, `49`:10, `16`:10, `37`:8,
then singles.

1. **Not one more element the entry count failed to declare.** Walking elements
   greedily after the declared ones takes **zero** extra in **every** body.
2. **Not whole elements of any observed shape.** The element sizes bodies that close
   actually use are 36, 41, 72, 84, 96, 120, 89, 77, 125, 137. Only **4 of 218**
   residues have a size in that set. This is independent of (1) and reaches the same
   place.
3. **Not a variant element with a one-byte head.** It closes 66, but every one of
   those declares a run count of zero, so only the fixed bytes are exercised and the
   interpolation-code test has nothing to check. Retracted in full.
4. **Not explained by the 17-byte trailing block.** Allowing it takes the frame to
   3,804 and drops the trailer-flag fences from 119 to 6, but grows this bucket from
   218 to 236. The two fence buckets have independent causes.
5. **Not a counted array of curve records.** Locating the first curve-shaped window
   and stepping back four bytes -- the move that closed `0x0A` -- gives no count in
   any body: 150 of 218 have no room for one and the rest disagree.

*Elimination (2) is the cheapest of the five and should have been first: comparing
the residue's size against the sizes the structure is actually observed to take costs
one query and rules out the whole "it is another one of those" family.*

#### Two eliminations on the 218, kept for the record

- **It is NOT one more element the count at +44 failed to declare.** Walking elements
  greedily after the declared ones -- taking every element that parses until the
  terminator -- takes **zero** extra elements in **every** body, and closes exactly
  the same 3,715. The residue does not parse as an element at all.
- **RETRACTED: the "66 of 218" one-byte-head reading is a length coincidence.**
  I recorded it as "a fixed rule with no free parameter" and it is not evidence at
  all. Every one of those 66 residues declares a **run count of zero**, so the
  reading consumes only its fixed parts: `1 + 12 + 19 = 32` and `1 + 12 + 24 = 37`,
  which are exactly the two residue sizes that close. It produces **zero records**,
  so the interpolation-code test -- the thing that settled the run split -- has
  nothing to test. Same trap as the flat terrain tiles, in a third costume.
- What the residue sizes actually are: `32`:58, `12`:48, `44`:32, `112`:16, `49`:10,
  `16`:10, `37`:8, then singles. Only **92** are of the form `32 + 12k` and **20** of
  `37 + 12k`; **106 fit neither**, so most of the residue is not even the right length
  to be a trailing element of the known shape.
- **Also eliminated: the 17-byte trailing block does not explain the 218.** Allowing
  it takes the frame to 3,804 and drops the trailer-flag fences from 119 to 6, but
  the `entries_do_not_reach_the_terminator` bucket *grows* from 218 to 236. So the
  two fence buckets have independent causes, and a reading that fixes one is not
  corroborated by the other.
- *When a candidate reading closes a residue, check what it exercised. A rule whose
  counted runs are all zero has been confirmed by arithmetic on its constants, not by
  the data.*
- Not a closure-gated lane, for the same reason `0x08` is not. The gate is a floor
  at 80% -- there to catch a regression, not to assert the frame is complete, which
  it is not.

### `0x0B`'s element is now a forward frame

```
element body:
  u8  runCount            -- element[0]
  4   head bytes
  runCount x run:
      12-byte run header, the record count at +7
      count x 12-byte record
  12  trailing block
then the trailer: first byte 0 -> 19 bytes, 1 -> 24
```

- **1,103 of the 1,151 elements that declare a run close exactly**, and the best
  rival frame closes **17**. Rivals varying the head, the run header width, the
  count's offset and the trailing block all score 0-17.
- **Scored over every element instead, the finding would have evaporated**: the
  chosen frame closes 3,594 and a rival closes 2,508, a ratio of 1.4. The 2,491
  elements that declare no runs close under almost any frame whose head and trailing
  block add up, and they outnumber the ones that walk a run two to one. Same frame,
  same corpus, completely different strength of claim -- which is why the gate reads
  `frameClosesWithRuns` and its control requires a rival to be visibly inflated by
  the empty ones.
- Run counts: 0 in 2,491 elements, 1 in 835, 2 in 242, 3 in 26.
- **How the layout fell out**, in order, because the sequence is the method:
  1. `element[0]` is 0 in exactly the 2,491 elements with no records -- so it is a
     run count, not a record count.
  2. For `element[0] == 1`, `k = 1 + element[12]` in **all 835**. The `+1` is the
     run's own twelve-byte header.
  3. For `element[0] == 2`, the second run's count sits at `element[24 + 12*c1]` in
     **242 of 242**, and at no other relative offset. That fixed the run stride at
     `12 + 12*c` and the count's place at `+7`.
  4. The lengths then forced a fixed twelve-byte block after the runs: an element
     with no runs is 17 body bytes, and 17 = 5 + 12.
- **Earlier searches missed it by looking for one count.** `element[8]` equals `k`
  in 575 of 1,103 -- a genuine half-fit that is not the rule and led nowhere,
  because `k` is a *total* over runs, not a field. *When a count field explains
  roughly half a corpus, consider that the quantity is a sum before hunting a better
  offset.*
- The degenerate trap caught this one too: scored without excluding `k = 0`, eight
  different offsets "carry k" in 2,491 elements, because an all-zero field matches a
  zero count for free. The census excludes them, and the code says why.
- Gated by `the_type11_trailer_anchor_beats_its_rivals` with
  `the_type11_trailer_is_not_settled_by_parsing` as its stated control: if the chosen
  anchor ever also wins on how many elements it can parse, the residue test is doing
  no work and the gate fails loudly.
- Supersedes the earlier note that "the 53 + 12k head widths that close are a fit
  rather than a layout". That measurement was made from the front, looking for a
  count in the first 53 bytes. The structure is anchored to the **end**, which the
  earlier attempt could not see -- and which is the third time in this type that
  tabulating from the end worked where the head resisted.
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

### Types `0x02` and `0x0B` share one source record, and it accounts for the media

This is the first result in this lane that is about the corpus rather than about a
body layout, so its evidence is stated in full.

**The record.** Numeric type `0x02` carries exactly one 14-byte source record at body
offset 0. Numeric type `0x0B` carries a counted array of the same record after its
leading flag and count. That they are the same record is shown twice:

- **The word at `+0` is a plugin id from a closed set.** `0x0B` uses two values --
  `0x00040001` (3,506 records) and `0x00140001` (941) -- and **140,121 of `0x02`'s
  142,815** bodies open with one of exactly those two. `0x02` uses five more
  (`0x00080001`, `0x00650002`, `0x00640002`, `0x00940002`, `0x01990002`), so it is a
  superset rather than a different field.
- **The word at `+5` names a declared media id in 4,447 of `0x0B`'s 4,447 records,
  and in 0 of them at any other offset in the record.** That contrast is what makes
  `+5` the id field. A bare hit rate would not.

**The attribution.** Pooled over every package, **61,325 of the 61,333 declared media
ids are named by some source record** -- 60,049 by `0x02`, 1,279 by `0x0B`, 3 by both,
and **8 by no record at all**. The words one byte either side of the id field name
**0 and 2**. Before `0x0B` was allowed to contribute, 1,284 media had no owner; it
closed 1,276 of them.

**The join has to cross a file boundary, and that is a trap worth recording.** A
source record names media that a *different* package declares. The first version of
this census joined inside one package and scored **12 of 147,262** -- not a weak
result, a meaningless one. `media_ids_from_audit` already carried the warning in its
own docstring: *"joining inside one package answers a question nobody asked."* The
census is published from C# as distinct value sets and joined in Python, where the
packages are already pooled.

### The bank has four sections nothing parsed, and STMG is one of them

Censusing the section tags was overdue. Across 20,873 bank payloads there are exactly
two tags everywhere -- `BKHD` (834,940 bytes) and `HIRC` (26,995,526) -- and **one
bank carries five more**: `DATA` 5,913,232, **`STMG` 10,118**, `INIT` 347, `ENVS` 216,
`PLAT` 8, `DIDX` 84. *A section census costs nothing and should have been the first
thing done to this format.*

#### `STMG` IS CLOSED: 10,118 of 10,118 bytes, byte-exact

```
u16                      observed 0
f32                      observed -60.0
u16                      observed 256
u16                      observed 50
u32 count                309
count x 12-byte record:  u32 id, u16 value, 6 bytes (all zero)
```

- **One instance in the whole corpus, so closure is not available as evidence and
  none is claimed from it.** Two checks stand in, neither needing the section to
  close:
  - **Distinctness.** At stride 12 the 309 ids are **all different**. At every other
    stride from 8 to 20 they collapse to between **107 and 220**. A stride that is not
    the record width reads each id from a sliding mix of two fields, and those
    collide. 12 rivals scored, **0** give distinct ids.
  - **What follows.** At 12 the word after the run is **15** -- a small count opening a
    further block. Every other stride lands on zero or an arbitrary large value.
- The record value is **1000 in 306**, and 3500, 500 and 0 once each.

#### `STMG`'s trailing run is framed BACKWARD, and its count is what locates it

```
u32 count                269
count x 21-byte record:  u32 id, f32, u8 selector, 3 zero bytes, f32, f32, u8
4 trailing bytes         all zero
```

- **It has to be backward.** The block between the two runs is variable-length and is
  not framed, so the trailing run's start cannot be computed forward.
- **The record shape bounds the run; the count locates it.** Walking back while the
  three zero bytes at `+9` hold reaches **270** records where the true count is **269**
  -- the bytes happen to be zero one record early. So the boundary is settled by the
  count instead: over every length from 1 to 480, **exactly one** has a preceding word
  equal to itself. *A shape test that overshoots by one is not a boundary; a count that
  agrees with the run length is.*
- **The shape is discriminated the same way the leading run's was.** All 269 ids are
  distinct and all 269 carry the zero bytes; **7 rival strides from 14 to 24 give
  neither** -- between 108 and 133 distinct ids and between 126 and 162 zero runs. All
  **807** floats across the three float fields are finite and bounded, taking values
  like 0, -96, 1, 0.1, 10, 50 and 16000. The selector at `+8` is 0 in 210, 2 in 47 and
  1 in 12.
#### `STMG`'s middle block, and why being bounded on both sides was the whole thing

```
u32 count                15
count x entry:  u32, u32, u8 zero, u32 records, 3 zero bytes   (13 bytes)
                records x 12-byte record: 8 bytes, u8 = 9, 3 zero bytes
```

- I said last batch this block was blocked on having one sample. **That was wrong, and
  the mistake is worth naming: one STMG, but FIFTEEN entries inside the block.** The
  sample size for an entry shape is 15, not 1.
- **What made it framable was being bounded on both sides.** Once the leading and
  trailing runs were located, the middle had a known start and a known end, so any
  candidate shape had to consume it *byte-exactly in exactly 15 steps*. Searching every
  shape of the form "head with a u32 count inside, then n records, then a tail" --
  head 4..40, count offset 0..head-4, record 1..32, tail 0..16, about **745,000
  candidates** -- **exactly one** does.
- **The content agrees independently of the search.** All 15 entry ids are distinct,
  the head's bytes at `+8` and `+10..+12` are zero in every entry, and the marker byte
  at record `+8` is **9 in all 45 records** with `+9..+11` zero. *A shape found by
  exhaustion needs content that the exhaustion did not select for.*
- Record counts per entry: 3 in six entries, 5 in three, 0/2/4 in two each.
- **Framed: 10,118 of 10,118. Nothing left over.** From 3,722 (36.8%) two batches ago.
- Each of the three blocks was located by **different** evidence, because each had
  something different available: the leading run by a forward count with a stride
  discriminated against eleven rivals; the trailing run by a backward count, unique
  over every length from 1 to 480; the middle by exhaustion plus closure.

#### `ENVS` is a run of curves over the SAME point record `0x0B` uses

```
(repeat until the section ends)
u8, u8, u8 count, u8
count x point:  f32 x, f32 y, u32 interpolation
```

- ENVS has **no count of its own** -- the run ends when the bytes do -- so byte-exact
  closure is what makes the walk a frame rather than a scan. **Three** shapes close it
  with every curve non-empty, and the content separated them:

  | shape | codes 0..9 | curves with rising x |
  | --- | --- | --- |
  | **head 4, count at `+2`, 12-byte point** | **16 of 16** | **6 of 6** |
  | head 12, count at `+2`, 18-byte record | 3 of 10 | 1 of 3 |

  *Closure found three candidates; content picked one.* The third ran off the end of
  the section, which is its own rejection.
- 6 curves, 16 points; codes 4 (x8), 0, 1, 2 (x2 each), 6 and 7. Same vocabulary as
  numeric type `0x0B`'s element runs.
- **This is the second record the format shares between two places**, after the
  14-byte source record that types `0x02` and `0x0B` share. The 12-byte
  `(x, y, interpolation)` point appears in `ENVS` curves and in `0x0B` element runs.

#### Every non-HIRC section of the bank format is now framed

| tag | instances | bytes | framed |
| --- | --- | --- | --- |
| `BKHD` | 20,873 | 834,940 | version field |
| `HIRC` | 20,873 | 26,995,526 | 10 types closed, `0x0B` at 3,937/4,325 |
| `DIDX` | 1 | 84 | 7 x 12 media entries |
| `DATA` | 1 | 5,913,232 | addressed by `DIDX` |
| `STMG` | 1 | 10,118 | **10,118 byte-exact** |
| `INIT` | 1 | 347 | **347 byte-exact** |
| `ENVS` | 1 | 216 | **216 byte-exact** |
| `PLAT` | 1 | 8 | **`Windows`** |

#### `INIT` is a plugin NAME table, and it names the plugins the records use

```
u32 count                22
count x entry:  u16 company, u16 plugin, NUL-terminated ASCII name
```

Closes byte-exactly on 347 bytes. A wrong field order would not land on the section
end, which is the whole check for a section that appears once.

- **The plugin id word at the front of the 14-byte source record decomposes as
  `(plugin << 16) | company`**, and every company-2 value the corpus carries is named
  here: `0x00640002` **AkSineTone**, `0x00650002` **AkSilenceGenerator**, `0x00940002`
  **AkSynthOne**, `0x01990002` **AkMotion**. **973 of 147,262** source records name a
  plugin the game itself names.
- **Everything unnamed is company 1** -- `0x00040001` (132,056), `0x00140001` (12,512),
  `0x00080001` (1,721). INIT lists plugin DLLs; company 1 is the built-in codec set,
  which the engine does not need named. The gate requires the absences to be company 1
  *exactly*, because a company-2 id missing would mean the decomposition is wrong.
- `PLAT` is a single NUL-terminated platform name: **`Windows`**.

#### THE CROSS-PACKAGE JOIN TRAP, THREE TIMES

This has now bitten three separate fields, and the pattern is always the same: a table
and its users live in **different `.pck` files**, so a join written inside the reader
scores near zero and looks like a negative result.

| field | package-local score | pooled score |
| --- | --- | --- |
| media ids named by source records | 12 of 147,262 | **61,325 of 61,333** |
| source ids reached from named events | (pooled from the start) | 163 |
| plugin ids named by `INIT` | **1** of 147,262 | **973** of 147,262 |

`media_ids_from_audit` has carried the warning in its own docstring the whole time:
*"joining inside one package answers a question nobody asked."* I wrote the C# join
twice more anyway. **When a table and its users are in separate files, the join belongs
in the pass that already unions the files** -- the reader collects, the audit joins.

#### The 8 media nothing names, explained

- **7 of the 8** are declared by `default_banks.pck`, which has `sounds=0`,
  `externals=0` and **exactly 7 media entries** -- so all 7 come from its `DIDX`
  section (84 bytes = 7 x 12). They are the Init bank's **embedded** media, and the
  same 7 ids are also declared as streamed copies in `default_stream_0.pck`. The 8th is
  in `default_stream_2.pck` only.
- **None of the 8 is a bank id**: pooled over 20,863 bank ids, the intersection with
  the 61,333 media ids is **0**, so they are genuine audio that no HIRC source record
  names rather than banks miscounted as media.
- Externals exist in this corpus -- 28,277 in `default_chinese_stream.pck` and 1 in
  `hotfix_japanese_bD0.pck` -- but not in the packages the 8 live in.

#### NOTHING outside HIRC references a music object either

Sliding a 32-bit window over all four unparsed sections -- 10,677 words -- **63 name a
HIRC object against 0.59 expected by chance**, so the references are real. Every one
is a **bus**: numeric type `0x12` 62 times and `0x08` once, all inside `STMG`. `INIT`,
`ENVS` and `PLAT` name nothing at all.

- Unaligned offsets were included deliberately. The source id inside the 14-byte
  source record sits at `+5`, which is not four-byte aligned, and testing only aligned
  words is exactly how that field stayed unidentified for so long.
- **Together with the object graph this closes the question.** Across every byte of
  the bank format -- the reference graph, the parent field, the `0x08`/`0x12` forest,
  every music relation, the action target word, and all four unparsed sections --
  **nothing references a music object from outside the music family.**
- Gated with its expiry in mind: a music type appearing here fails the audit. **That
  failure is the good news.**

### NOTHING in the HIRC object graph reaches the music family's media

The previous batch asked what addresses the music subgraph. The answer, over every
relation this reader has resolved, is **nothing** -- and the evidence is now complete
rather than suggestive, because the relations can be enumerated.

| relation | edges | any music type at either end? |
| --- | --- | --- |
| main reference graph | 230,247 | **no** -- sources `04/05/06/07`, targets `02/05/06/07/09` |
| parent field (its inverse) | 199,445 | **no** -- 13 type pairs, all in `02/05/06/07/09` |
| `0x08`/`0x12` forest | 412 | no |
| music hierarchy at `+9` | 7,084 | internal only: `0A->0C`, `0A->0D`, `0C->0C`, `0D->0C` |
| `0x0C`'s counted array | 2,980 | internal only: `->0A`, `->0C`, `->0D` |
| `0x0A`'s counted array | 3,903 | internal only: `->0B` |
| **action target word** | 23,455 resolvable | **8 land on `0x0C`; none on `0A`, `0B` or `0D`** |

- **The family is large and well connected internally**: 11,656 objects, 7,305
  downward edges from 4,607 sources, 4,351 objects with no incoming edge (3,764
  `0x0A`, 489 `0x0D`, 98 `0x0C`). **Every `0x0B` has an incoming edge** -- none is a
  root -- so the tracks are owned.
- **Entering it from outside there are 5 edges in the whole corpus**, all
  `action_03 -> type0C`, resolved within the same bank. All 5 land on objects that are
  **roots**, **none of the 5 has an outgoing edge**, and together they reach **0**
  source ids.
- So the family's **1,279 media are reached by nothing**. Extending the named walk to
  read `0x0B`'s source records changed the reach numbers by exactly nothing --
  120 identifiers, 218 source ids, before and after.
- *This is written as a gate, not a note.* If a later reading reaches even one source
  id through the music family, `reachedSourceIdCount` becomes positive and the audit
  fails. **That failure is the good news.** The same pattern retired the `0x0B`
  element-count caveat two batches ago.
- The gate also refuses when the walk has **no edges**, because an empty edge set
  reaches nothing and looks exactly like isolation. *A negative result needs proof
  that the instrument was working.*
- What this does **not** say: that music is unreachable at runtime. It says no
  relation resolved here reaches it, so whatever drives music is **outside the HIRC
  object graph**. That bounds the search rather than ending it.

### The music subgraph is not reachable from any named event

- **Actions almost never address music.** Of the 23,455 action target words that
  resolve to an object in the package, the types are `0x05` 7,709, `0x02` 7,466,
  `0x09` 3,869, `0x06` 3,826, `0x04` 393, `0x07` 126, `0x08` 46, `0x15` 12 -- and
  **`0x0C` 8**. None at all reach `0x0A`, `0x0B` or `0x0D`.
- **The named walk confirms it from the other side.** Starting at the 199 named
  `0x04` objects and following gated reference vectors, the walk arrives at types
  `0x03` (310), `0x02` (225), `0x09` (127), `0x05` (91), `0x06` (18), `0x07` (4) and
  `0x04` (1). **It never arrives at a music type.**
- So the **1,279 media owned by `0x0B` are reached by no named event**, and the 163
  media a named event does reach are all owned by `0x02`. Extending the walk to read
  `0x0B`'s source records changed the reach numbers by **nothing** -- 120 identifiers
  reaching 218 source ids, before and after -- which is itself the measurement.
- What this does **not** say: that music is unreachable at runtime. It says the
  music types are not addressed through the action target word or through any gated
  reference vector, so whatever addresses them is not in this graph.

### How much of the audio corpus is actually named

| | count | share of declared media |
| --- | --- | --- |
| media ids declared by the packages | 61,333 | 100% |
| named by some source record | 61,325 | **99.99%** |
| reachable from a named `0x04` event | 163 | **0.27%** |

The gap is not a defect in the walk. Only **221** audio-shaped literals survive in
`global-metadata.dat`, matching 199 objects; the event names for the rest are not
shipped as managed literals. *Coverage of the structure and coverage of the names are
different numbers, and quoting one for the other would overstate both.*

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

## IrradianceVolume: the largest unread VFS-native family

The audio lane's three open items are all blocked on evidence outside the shipped
audio data, so this batch triaged the whole VFS by byte volume to find where the
unread data actually is.

**The whole installed set is 67.5 GB over 455,691 ledger rows**, and by extension:

| extension | bytes | share |
| --- | --- | --- |
| `.ab` (Unity asset bundles) | 42.07 GB | **62.3%** |
| `.pck` (audio) | 11.49 GB | 17.0% |
| `.usm` (video) | 6.56 GB | 9.7% |
| **`.bytes` (VFS-native)** | **6.33 GB** | **9.4%** |
| `.json` | 827 MB | 1.2% |

Within `.bytes`, one family dominates:

| family | files | bytes | share of `.bytes` |
| --- | --- | --- | --- |
| **`iv_*.bytes`** | **132** | **4.16 GB** | **65.6%** |
| `LAYER_N_*` | 345 | 469 MB | 7.4% |
| `LAYER_D_*` | 345 | 414 MB | 6.5% |
| `InitChunkData_*` | 26,520 | 624 MB | 9.9% |
| `Terrain_*` | 30,280 | 245 MB | 3.9% |

### What is measured so far

- The family is **`Data/IrradianceVolume/PC/<scene>/v3/iv_<x>_<y>.bytes`**, streamed
  through the maintained CLI as `--block-type iv` (block value **14**); the `AuditIV`
  block is 8. Streaming every `iv_*.bytes` yields **138 files**, 16,064 bytes to
  70,032,579 bytes.
- The first two `u32` take **49 distinct pairs** across the 138 files. The most common
  is **`(3, 2)` in 34 files**; the rest are `(n, 512)`, `(n, 768)`, `(n, 1280)` with
  `n` in the 990-2,270 range, and `(12291, 8)` / `(12291, 6)` in the four smallest.
- The two 16,064-byte files (`gacha/character` and `gacha/weapon`) show a clear
  **16-byte repeat**: one word, then three `RGB 00` triples. Colour triples at a fixed
  stride are what an irradiance probe grid looks like, but that is a shape observation
  and nothing is claimed from it yet.

### What was measured and is WRONG

A first reading of one `(3, 2)` file showed `03 03 03 00` at `+40` and `472` at `+44`,
which looked like a 3x3x3 probe grid and a count. **Across the 34 files that share the
header, those offsets hold `(3,3,3)`/472, `(15,15,15)`/472, `(3,3,0)`/472 and
`(255,255,255)`/`0xFFFFFFFF`** -- the last being an all-`FF` region that starts at
different places. So `+40` is not a fixed field; what precedes it is variable-length.
*A tidy-looking triple in one file is a coincidence until the same offset is read in
every file that should share the layout.*

### The family splits in two, and the stride-4 peak is an artefact

Autocorrelating byte i against byte i+stride over each payload puts **stride 4** on top
in most files (0.14 to 0.42 agreement against a 0.03 to 0.09 mean), with 16, 32, 48 and
64 following as its harmonics. That reads as 4-byte records. **It is only half true,
and a per-phase content test says which half.**

Splitting each payload into its four byte phases and measuring each one separately:

| file | phase 0 | phase 1 | phase 2 | phase 3 | phase 3 zero |
| --- | --- | --- | --- | --- | --- |
| `gacha/character/iv_3_0_0` | 7.44 | 7.30 | 7.16 | **3.51** | **52.0%** |
| `gacha/weapon/iv_3_0_0` | 4.66 | 4.71 | 4.08 | **1.30** | **75.1%** |
| `indie_dg008/v3/iv_0_0` | 6.25 | 6.22 | 6.25 | 6.19 | 19.3% |
| `dung02_cdg012/v3/iv_0_0` | 7.30 | 7.28 | 7.28 | 7.18 | 14.5% |

(entropy in bits per byte)

- **The `gacha/*` files have a real 4-byte record.** Phase 3 carries a fraction of the
  entropy of phases 0 to 2 and is zero in half to three quarters of records -- the
  shape of three colour channels plus a shared exponent or alpha. Four such files, 16
  KB to 101 KB.
- **The `v3/*` files have no byte-phase structure at all.** All four phases have the
  same entropy to two decimal places and the same top byte values. **A file with
  4-byte records cannot look like that**, so the stride-4 peak there is an artefact of
  something else and not a record width. Those are 134 files and essentially the whole
  4.16 GB.
- *An autocorrelation peak says a distance matters; it does not say a record lives
  there. The phase test is what separates the two.*
- Entropy 6.2 to 7.3 with no phase structure is what compressed or block-packed data
  looks like. **The terrain container's codec does not apply** -- that reader needs the
  file's leading word to be the decoded size, and here the leading word is 3, 990,
  1,182 or 12,291 for files of 16 KB to 70 MB.

### The game names this format itself, and it has an INDEX

Rather than guess the container further, `global-metadata.dat` was asked what the
engine calls it. The answer is specific:

```
HGIrradianceVolumeManager / HGIrradianceVolumeManagerV2
HGIrradianceVolumeConfig  / HGIrradianceVolumeConfigV2
  GetCurrentIrradianceVolumePathV3      ReloadIndexFileV3 / ReloadIndexFileV2
  ToggleDebugUpdateClipmap              ToggleDebugUpdateClipmapLod0
  UpdateSceneStateMask                  UpdateGachaIV
  StreamingInNewMap / StreamingInCabin  SetOverrideStreamingCenterByCamera
```

Three of these change what to do next:

- **`ReloadIndexFileV3`** says there is an index. There is: **92 `index.bytes` files**
  in the IV block, 980 bytes to 504 KB, one per scene -- plus **7 `regionIv_*.bytes`**
  files totalling 3.09 MB. The earlier sweep matched only `iv_*.bytes` and missed both.
- **`ToggleDebugUpdateClipmap`, `...Lod0`** name the structure: a **clipmap**, a
  nested multi-resolution grid. That is what a volume file should be expected to hold.
- **`UpdateGachaIV`** is a separate entry point from the V3 streaming path, which
  independently confirms the `gacha` / `v3` split the byte-phase test measured.

#### The index is framed enough to join, and the join is exact

The index holds **length-prefixed UTF-16LE strings**: `u32 byteLength`, then that many
bytes of UTF-16. The 980-byte index carries `u32 24` followed by `iv_0_0.bytes`.

- Across the 92 index files, **138 `.bytes` names are listed -- exactly the 138 volume
  files the block contains**.
- **91 of the 92 indexes name precisely the set of files present in their own
  directory.** Not a hit rate over a large population: each index names between one and
  a few dozen files and gets the whole set right.
- A `u32` at `+20` equals the name count in **86 of 92**, so it is a **candidate**
  count offset rather than an established one, and is recorded that way.

#### The index IS framed: 86 of 92, and the other 6 are fenced by name

`scripts/asset_builder/irradiance_index.py`, with
`scripts/tests/test_irradiance_index.py`:

```
u32 magic            0x03000003 x82, 0x01000043 x2, 0x03000002 x2
u32 stateCount       the scene states GetStateNameList returns
stateCount x name    u32 byteLength, then that many bytes of UTF-16LE
u32 u32 u32          three words: 1, 0, 0 in every framed file
u32 volumeCount
volumeCount x name   the volume files in this directory
... remainder        the clipmap description, not framed
```

| | |
| --- | --- |
| indexes | **92** |
| framed exactly | **86** |
| fenced as unsupported | **6** |
| failed | **0** |
| volume names read | 103 |
| **volume sets matching the directory** | **86 of 86** |

- **The content check is the volume-name join, and it is strict on purpose.** Each
  index names between one and a few dozen files, so "the whole set, every time" is a far
  stronger statement than a percentage over a large population. A single name that is
  not there, or one missing, means the name table has been misread.
- **The three middle words are discriminated by closure.** At three words 86 files
  frame; at **zero, one, two, four or five words, not one file frames at all**. A width
  that framed fewer would be weak evidence; a width that frames none is the whole
  discrimination. Their values are constants -- 1, 0, 0 -- in all 86.
- **The 6 fenced files declare scene states**, and their names are what the engine's
  `GetStateNameList` returns: `Afternoon`, `Evening`, `001_damaged`, `001_normal`,
  `001_overcast_rainy`, `Map02_lv009_night`, `under_construction`. After those names the
  gap before the volume count is `3 + 3 x stateCount` words in three of them and
  something else in the other three, so **the variant is refused rather than guessed
  at** -- reported as `unsupported`, which cannot be mistaken for a defect.

#### The remainder after the name table: measured, not framed

With a fixed start offset in 86 files the remainder can be characterised, and what it
is *not* is worth recording as clearly as what it is.

- **It begins with a run of small signed integers.** In **63 of the 86** files all
  sixteen leading words satisfy `|v| <= 4096`; the rest break sooner. First words are
  `(4,3)`, `(5,3)`, `(5,2)`, `(9,5)`, `(7,5)`, `(11,7)`, `(5,3)`, `(11,9)` -- 23
  distinct openings over 86 files.
- **The `gacha` pair opens `24, -32, -32, -32, 0, 0`**, which reads as a size followed
  by a negative corner. Reading these words as **signed** matters: unsigned they are
  `4294967264` and look like garbage.
- **They are not floats.** Every one of the leading words is `0.0` or `NaN` when read
  as float32.
- **No grid product predicts the remainder size.** Testing `w0*w1`, `w0*w1*w2` and
  `w0*w1*w2*w3` against remainder minus a header of 8, 12, 16, 20 or 24 bytes, for a
  record size between 1 and 4,096: **every combination that divides does so for exactly
  one file of 86.** A record array would divide for many.
- So the remainder is **not** `header + grid x record`, and the leading words are not a
  dimension triple that sizes it. They are recorded as small signed integers and
  nothing more.

#### The index carries NO sizing for the volume payload, so the payload is self-describing

I said last batch that the volume payload should wait for the index, because the index
is what describes it. **Three joins say that is wrong, and the correction changes the
plan.**

| join tested | result |
| --- | --- |
| the volume file's byte length appears anywhere in its index | **0 of 86** |
| the sum of volume lengths, or length minus 8, or length over 4 | **0 of 86** |
| some remainder word divides the volume length into 1..4,096 parts | **2 of 71**, at record sizes 2,700 and 3,398 |

The index names its volume files and nothing more that this can find: no offset table,
no byte count, no probe count. **So the volume payload has to be self-describing**, and
framing should start from `iv_*.bytes` rather than waiting on the index.

*A plan built on "the index describes the payload" survived exactly as long as it took
to test the join.*

#### The `gacha` volume header: a candidate relation on four files, not a frame

The volume filenames are `iv_<lod>_<x>_<y>.bytes`, and size falls with the first
number -- `iv_0_0_0` is 2.25 MB, `iv_1_0_0` is 84.8 KB, `iv_3_0_0` is 16.1 KB. That is
the clipmap LOD `ToggleDebugUpdateClipmapLod0` refers to.

Six files carry magic **`0x00003003`**, and in **four of them** the first eight words
line up:

| file | w1 | w2 | w3 | w4 | w5 | w6 | w7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `character/iv_0_0_0` | 58 | **2000** | 140 | **604** | 5 | 3 | **32** |
| `weapon/iv_0_0_0` | 60 | **2000** | 140 | **620** | 4 | 3 | **32** |
| `character/iv_1_0_0` | 6 | **2000** | 64 | **112** | 3 | 2 | **32** |
| `weapon/iv_1_0_0` | 6 | **2000** | 64 | **112** | 5 | 2 | **32** |

- **`w4 = w1 x 8 + w3`** in all four: 58x8+140=604, 60x8+140=620, 6x8+64=112. So `w3`
  is a header size and `w1` counts 8-byte entries that follow it, ending at `w4`.
- `w2` is **2000** and `w7` is **32** in all four; `w6` is 3 at LOD 0 and 2 at LOD 1.
- **The two `iv_3_0_0` files share the magic and do not follow it**: their `w2` and `w3`
  are arbitrary 32-bit values. Either the deepest LOD has no header, or the magic is
  not what selects the layout.

***Four files is thin, and this is recorded as a candidate relation rather than a
frame.*** It is not in a maintained reader and has no gate. Three constants and one
arithmetic identity over four samples is the kind of pattern that has already failed
twice in this lane once the whole population was checked -- the stride-4 periodicity and
the clipmap grid extents both looked at least this good.

#### What the 132 `v3` payloads are NOT: five containers eliminated

The `v3` files are 4.16 GB and the thing worth framing. Five hypotheses are now
excluded, each by a measurement rather than by inspection.

| hypothesis | test | result |
| --- | --- | --- |
| a chain of size-prefixed blocks | 1/2/4-byte sizes, prefix in or out, starts 0..32 | **no chain reaches EOF** in any file |
| the terrain container's LZ4 variant | its reader needs the leading word to be the decoded size | the leading word is 3, 990, 1,182 or 12,291 for files of 16 KB to 70 MB |
| standard compression | zlib, gzip, zstd, lz4 frame, bzip2 magics in the first 4 KB | **none**; the 22 "zlib" hits are coincidental `78 01` byte pairs, and no offset 0..63 inflates to more than 1 KB |
| an array of 4-byte records | byte-phase entropy | **all four phases equal to two decimals**, which a 4-byte record cannot produce |
| an array of spatially coherent probe values | delta entropy at every stride 1..64 | **every delta raises entropy above raw** -- 6.21 to 6.74 at best |

The last is the sharpest. Irradiance data is spatially smooth by nature, so if the
payload were probe values laid out on a grid, differencing at the record stride would
*drop* the entropy. It rises at every stride from 1 to 64. **There is no byte stride at
which consecutive values resemble each other.**

Two more, from content tests rather than statistics:

| hypothesis | test | result |
| --- | --- | --- |
| **BC6H blocks** (HDR, the natural choice for probes) | four 5-bit mode values are reserved, so real BC6H never lands on them | **7.9% to 11.1% reserved**, against **11.7% for the same bytes shuffled** -- no signal at all, at any block start from 0 to 63 |
| run-length or sparse encoding | share of bytes in runs of 4 or more | **0.0% to 8.3%**, against 0.4% shuffled; one file has none whatever |

**The BC6H test is the one that mattered**, because bit-packed block compression was
the shape argument left standing after the other eliminations. It fails completely: the
mode field carries no more structure than shuffled bytes do. *A shape argument survives
exactly until someone tests the thing it predicts.*

So after seven eliminations the `v3` container is still unidentified, and the profile it
has to satisfy is now quite specific: **entropy 5.0-6.9 bits per byte, all four byte
phases identical, no delta coherence at any stride 1-64, no runs, no standard
compression, no block-mode structure.** The byte census is dominated by `00`, then
`FF`, `04`, `80`, `CC`, `40`, `30`, `01` -- round values and `0xCC`, which is the
repeating bit pattern `11001100`.

#### THE FORMAT IS DESCRIBED BY ITS OWN TYPE: `HGIrradianceVolumeConfigV2`

Seven eliminations by byte statistics had not identified the container. The IL2CPP type
layout identifies it in one read, using the metadata parser already in
`tools/endfield-il2cpp/catalog_option_flow_metadata.py`.

**`UnityEngine.HyperGryph.HGIrradianceVolumeConfigV2`, 34 fields:**

```
clipMapTextureSizeX / Y / Z          maxRegionCount
basisBaseGridDim, basisVoxelDataDim  perBasisLodBudget,  perBasisTextureOffset
coeffBaseGridDim, coeffVoxelDataDim  perCoeffLodBudget,  perCoeffTextureOffset
lod3BaseGridDim, lod3VoxelDataDim, lod3Budget
rawDataSize, modelBufferBudget, perLOD
perHalfStreamingChunkCountsX / Y / Z
perRawBufferOffsets, perRawBufferCounts
perBlockInfoBufferOffsets, perBlockInfoSize
perBasisTextureBlockCounts, perCoeffTextureBlockCounts
perFrameMaxLoadingByteCount, perFrameMaxUploadChunkCount
```

**`HGIrradianceVolumePipelineUpdateResultV2`:** `clipmapTextureALod0`, `BLod0`,
`ALod1`, `BLod1`, `ALod3`, `BLod3`.

So the payload is **GPU texture data for two textures per LOD** -- a **basis** and a
**coefficient** set, which is spherical-harmonic lighting -- uploaded to a clipmap.
***That is why no byte statistic found a record: there is no record.*** It is texture
upload data, and the block structure belongs to the GPU format, not to a file layout.

#### The LODs are 0, 1 and 3, and that explains the two exceptions

The config names exactly `Lod0`, `Lod1` and `Lod3`, and gives **LOD 3 its own fields**
(`lod3BaseGridDim`, `lod3VoxelDataDim`, `lod3Budget`) where the others share
`basis*`/`coeff*` ones. The filenames agree: the six `iv_<lod>_<x>_<y>.bytes` files are
**two each at LOD 0, 1 and 3** and nothing else.

That settles the candidate relation recorded last batch. `w4 = w1 x 8 + w3` holds for
LOD 0 and LOD 1, which share `w2 = 2000` and `w3` of 140 and 64 -- and fails for the two
LOD 3 files, **because the engine declares LOD 3 as a separate case**. The exceptions
were not noise in a thin sample; they are a documented variant. *A relation with
unexplained exceptions and a relation whose exceptions the vendor's own config explains
are different things.*

#### TWO SCHEMES, and the field names say which file uses which

There are two config types, and their fields are different schemes rather than
versions of one:

| `HGIrradianceVolumeConfigV2` (34 fields) | `HGIrradianceVolumeConfig` (26 fields) |
| --- | --- |
| `clipMapTextureSizeX/Y/Z` | `indirectionTextureSize`, `ClipmapTextureSize` |
| `basisBaseGridDim`, `basisVoxelDataDim` | `blockCountX/Y/Z`, **`blockSizesV3`** |
| `coeffBaseGridDim`, `coeffVoxelDataDim` | `hashTableSize`, `maxHashTableSize` |
| `perBasisTextureOffset`, `perCoeffTextureOffset` | `perHashTableOffsets`, `perHashTableSizes` |
| `lod3BaseGridDim`, `lod3VoxelDataDim`, `lod3Budget` | `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts` |
| `perRawBufferOffsets`, `perRawBufferCounts` | **`perFrameMaxLoadingByteCountV3`**, **`perFrameMaxUploadChunkCountV3`** |

- **V2 is a clipmap of basis and coefficient textures per LOD.** That is the
  `iv_<lod>_<x>_<y>.bytes` form -- the six non-`/v3/` gacha files at LODs 0, 1 and 3,
  with magic `0x00003003` and the `w4 = w1 x 8 + w3` header.
- **V3 is a sparse virtual texture: an indirection texture, a hash table, and physical
  texture blocks.** The three fields carrying the `V3` suffix all live in
  `HGIrradianceVolumeConfig`, alongside `blockSizesV3`. That is the
  `Data/.../v3/iv_<x>_<y>.bytes` form -- 132 files, 4.16 GB.

**This is what the byte statistics were seeing.** A hash table and an indirection
texture at the front of a file are exactly what "49 distinct leading word pairs, no byte
alignment, no delta coherence, no runs, entropy 5-7" look like. The leading words are
hash-table and indirection data, and the bulk is physical texture blocks. *Seven
eliminations were each correct and all pointing at the same answer, which none of them
could name.*

- **The LOD is carried inside the file, not in the name.** `perLOD`,
  `perHashTableOffsets`, `perHashTableSizes`, `perPhysicalTextureOffsets` and
  `perPhysicalTextureBlockCounts` are per-LOD arrays, so one `iv_<x>_<y>.bytes` holds
  every LOD for its chunk. The `<x>_<y>` are chunk coordinates, which is why 117 of 132
  begin `iv_0_`.

#### Both configs are blittable structs of fixed buffers, and that closes the argument

Every `per*` field is a C# **fixed buffer**: each has a generated nested type
`<name>e__FixedBuffer` holding a single `FixedElementField`.

| type | fields | of which fixed buffers |
| --- | --- | --- |
| `HGIrradianceVolumeConfig` (V3) | 26 | **11** -- `perLOD`, `perHalfChunkCounts`, `perHashTableOffsets`, `perHashTableSizes`, `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts`, `perFrameMaxLoadingByteCount`, `perFrameMaxUploadChunkCount`, `ClipmapTextureSize`, **`blockSizesV3`**, `cameraForwardBiasForYAxis` |
| `HGIrradianceVolumeConfigV2` | 34 | **19** -- the `basis*`/`coeff*` dims, `perRawBuffer*`, `perBlockInfo*`, `perBasisTexture*`, `perCoeffTexture*`, `perHalfStreamingChunkCounts{X,Y,Z}`, `streamingCenterBias` |

So both are **blittable structs with fixed-size per-LOD arrays** -- native interop
configs, not serialised objects.

***`blockSizesV3` is a fixed buffer, so block size varies per LOD.*** That is the last
of the byte-statistic negatives explained: there is no single record stride in a `v3`
payload because the physical texture blocks are sized per LOD, and one file holds every
LOD for its chunk.

#### THE EXTENTS: every per-LOD buffer is 3 x 4 bytes, so there are THREE LODs

`Il2CppTypeDefinitionSizes` in `GameAssembly.dll` gives each generated
`e__FixedBuffer` type's size, and that size *is* the buffer. Reached through the
existing bridge in `tools/endfield-il2cpp` -- CodeRegistration at `0x18a88e640`,
MetadataRegistration at `0x18a88e860`, 58,110 size entries.

**Every per-LOD buffer in both configs is `native 12` = 3 x 4 bytes**, without
exception:

| | buffers | native size | elements |
| --- | --- | --- | --- |
| `HGIrradianceVolumeConfig` (V3) | 11 | **12** each | **3** |
| `HGIrradianceVolumeConfigV2` | 17 of 19 | **12** each | **3** |
| `basisBaseGridDim`, `basisVoxelDataDim` | 2 | **24** | **6** |

- **Three LOD slots, and 28 independent fields agree on it.** That is not one
  measurement: `perLOD`, `perHashTableOffsets`, `perHashTableSizes`,
  `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts`, `blockSizesV3`,
  `perRawBufferOffsets`, `perBlockInfoSize`, `perBasisTextureOffset`,
  `perCoeffTextureOffset` and the rest are all 12 bytes.
- **It matches the names.** `HGIrradianceVolumePipelineUpdateResultV2` exposes
  `Lod0`, `Lod1` and `Lod3` -- three textures per set, indices 0, 1 and 3, three slots.
- The two 24-byte buffers, `basisBaseGridDim` and `basisVoxelDataDim`, hold **six**
  words where the matching `coeff*` fields are plain scalars. Three LODs x two values,
  or two triples; that is not settled and is not claimed.
- `streamingCenterBias` and `cameraForwardBiasForYAxis` are also 12 bytes, but they are
  a `Vector3` rather than per-LOD -- *a size alone does not say what a buffer is for,
  and these two are the reminder.*

#### The exact config layouts, read from `Il2CppFieldOffsets`

Both structs, byte-exact. Offsets below are struct-relative; the binary reports them
object-relative, so each is 16 higher there (the managed header), and the last field
lands on the struct size exactly -- which is the check that the table was read right.

**`HGIrradianceVolumeConfig` -- the V3 scheme, 192 bytes:**

```
+0   enableLowQualityMode    4     +96  perFrameMaxLoadingByteCount   12
+4   indirectionTextureSize  4     +108 perFrameMaxUploadChunkCount   12
+8   blockCountX             4     +120 perFrameMaxLoadingByteCountV3  4
+12  blockCountY             4     +124 perFrameMaxUploadChunkCountV3  4
+16  blockCountZ             4     +128 maxHashTableSize               4
+20  hashTableSize           4     +132 maxInactiveFrameCount          4
+24  perLOD                 12     +136 ClipmapTextureSize            12
+36  perHalfChunkCounts     12     +148 blockSizesV3                  12
+48  perHashTableOffsets    12     +160 cameraForwardBiasForYAxis     12
+60  perHashTableSizes      12     +172 maxRegionCount                 4
+72  perPhysicalTextureOffsets     12   +176 regionAtlasSizeX          4
+84  perPhysicalTextureBlockCounts 12   +180 regionAtlasSizeY          4
                                        +184 regionAtlasSizeZ          4
                                        +188 enableLowMemoryMode       4
```

**`HGIrradianceVolumeConfigV2` -- the clipmap scheme, 312 bytes:** same method;
`clipMapTextureSizeX/Y/Z` at +4/+8/+12, `basisBaseGridDim` +16 (24 bytes),
`basisVoxelDataDim` +40 (24), `coeffBaseGridDim` +64, `coeffVoxelDataDim` +68,
`perCoeffLodBudget` +72, `perBasisLodBudget` +84, `lod3BaseGridDim` +96,
`lod3VoxelDataDim` +100, `lod3Budget` +104, `rawDataSize` +108,
`modelBufferBudget` +112, `perLOD` +116, then the `perHalfStreamingChunkCounts{X,Y,Z}`,
`perRawBuffer{Offsets,Counts}`, `perBlockInfo{BufferOffsets,Size}`,
`perBasisTexture{Offset,BlockCounts}`, `perCoeffTexture{Offset,BlockCounts}` and
`perFrameMax{LoadingByteCount,UploadChunkCount}` buffers at 12 bytes each,
`maxRegionCount` +284, `regionAtlasSizeX/Y/Z` +288/+292/+296,
`streamingCenterBias` +300.

**The `v3` container, as far as the evidence goes:** an indirection texture and a hash
table addressing physical texture blocks, with **three** per-LOD offset/count pairs and
three per-LOD block sizes, all in fixed buffers inside these blittable structs.

#### The config is NOT in the shipped files, and the search had a positive control

Knowing the struct exactly turns "is it in the file?" into a search with a
specification rather than a pattern hunt. A 192-byte window counts only if every field
is plausible for what it is named: `enableLowQualityMode` 0 or 1, the block counts and
`indirectionTextureSize` positive and under 8192, `maxHashTableSize >= hashTableSize`,
the three `perLOD` entries in 1..64, and `perHashTableOffsets` and
`perPhysicalTextureOffsets` non-decreasing.

| scanned | candidates |
| --- | --- |
| all 92 `index.bytes` | **0** |
| 12 `v3` payloads, first 400 KB each | **0** |
| the same payload bytes shuffled | 0 |

***A test that returns zero on everything has not shown it can detect anything***, so
the zero above is only worth having because of a positive control:

| control | candidates |
| --- | --- |
| a synthetic config filled the way the engine would | **1** |
| that struct embedded at offset 5000 in 20 KB of random bytes | **1, at exactly 5000** |
| the 20 KB of random bytes alone | **0** |

So the scanner detects the struct when it is there and does not fire on noise -- and
**the V3 config does not appear in any shipped index or payload**. It is a runtime
config the engine holds, not something serialised into the data, and the `.bytes` files
must carry their geometry some other way.

That closes the gap flagged last batch: knowing a struct exactly is not the same as
knowing it is in the file, and here it is not.

#### WHY it is not: the payload parser is native, the index handler is managed

The method flags say exactly where the boundary runs.

| type | methods | `iflags` | kind |
| --- | --- | --- | --- |
| `HGIrradianceVolume`, `HGIrradianceVolumeV2` | `SetMap`, `SetMapV3`, `PipelineUpdate`, `StreamingInCabin`, `SetActiveSceneStateMask`, ... | **0x1000** | **InternalCall -- native C++** |
| `HGIrradianceVolumeManager` | `ReloadIndexFileV3`, `GetStateNameList`, `UpdateSceneStateMask`, `StreamingInNewMap`, ... | **0** | **managed C#** |

- **The `.bytes` payload is parsed in native code**, reached through internal calls. IL2CPP
  metadata cannot describe its layout because no managed type exists for it -- the
  managed side passes a path and a config struct and nothing else crosses.
- **That is why the config is not in the file.** It is the managed-to-native *parameter*,
  not serialised content. The two findings are the same fact seen from both sides.
- **The index handling is managed and therefore readable.** `ReloadIndexFileV3` and
  `GetStateNameList` are ordinary C# with method bodies in `GameAssembly.dll`, which the
  existing bridge can locate.

**So the lane splits cleanly by reachability.** The index frame at 86 of 92 can be
checked against the game's own parser. The payload layout cannot be reached this way at
all; it needs the native loader disassembled, and the project's existing note that
static work on `GameAssembly.dll` is constrained by HGP applies.

*Knowing that a thing is out of reach, and why, is worth more than another sweep that
was never going to find it.*

#### `ReloadIndexFileV3` does not parse the index either

The one reachable check turned out not to exist. `ReloadIndexFileV3` is managed, its
body is at `0x188fc27d8` in `HG.RenderPipelines.Runtime.dll` (local method #2222 of
9,473), and it is **40 instructions long**:

```
class-init guard (0x75a)
if [this+0x10] != 0:  release it, null it, store a value at [this+0x18]
store the path argument at [this+0x20]        <- m_irradianceDataPathV3
return
```

It **releases the current volume and stores the new path**. No file is opened, no bytes
are read, nothing is parsed. The load happens later, natively.

- So **the entire IrradianceVolume format -- index as well as payload -- is parsed in
  native code.** The managed surface is paths, a config struct, and lifetime calls.
- **The index frame therefore cannot be cross-checked against the game's own parser**,
  which was the reachable next step identified last batch. It is not reachable after
  all.
- That is acceptable rather than fatal, because the frame's evidence does not depend on
  it: 86 of 92 files framed, **86 of 86 naming exactly the volume files present in
  their directory**, and every rival middle-word width framing zero. *A name join that
  gets the whole set right in every file is evidence in its own right.*

**The lane's boundary, stated once:** everything the shipped bytes and the IL2CPP
metadata can say has been said. Further progress on the payload needs the native loader,
and the project's existing note about HGP applies to that.

**Where this lane stands:** the index is framed and shipped at 86 of 92 with 20 tests;
the payload's container is **identified** rather than guessed, with every one of the
seven byte-statistic eliminations explained by the identification; the remaining work is
extents and element widths, and it is reachable with `tools/endfield-il2cpp`.

*Two batches of byte statistics eliminated seven containers and identified none. One
read of the type layout named the format, explained the residue, and resolved the
exceptions in a candidate relation. **When a format has a reader, read the reader.***

*Asking the shipped code what a format is called cost one metadata scan and moved this
further than two batches of byte-pattern search.*

## `LAYER_D`/`LAYER_N`: the terrain splat arrays, named by the engine

The second-largest `.bytes` family after IrradianceVolume, and untouched until now:
**345 `LAYER_N_*` (469 MB) + 345 `LAYER_D_*` (414 MB) + 54 `LAYER_C_*` (57 MB)**, 940 MB
in all. Asking the metadata first this time, rather than after seven byte-statistic
eliminations.

`HG.Rendering.Runtime.VirtualTextureRenderer` has 93 fields, and four of them settle it:

```
m_splatsDiffuseArray      m_splatIndexMap        m_terrainNormalMap
m_splatsNormalArray       m_splatControlMap      m_terrainHeightmap
                          m_colorVariationTex    m_deformableControlMap
VT_CLIPMAP_BASE_WIDTH, VT_CACHE_PAGE_RESOLUTION, VT_CACHE_PAGE_BUFFER_SIDE_SIZE,
VT_INDIRECT_TEX_BUFFER_COUNT, VT_GPU_FEEDBACK_BUFFER_COUNT, VT_WORK_GROUP_COUNT
```

- **`LAYER_D` is the splat diffuse array and `LAYER_N` the splat normal array.** The
  counts agree: **345 each, exactly paired**, which is what two texture arrays over the
  same layer set look like. `LAYER_C` at 54 files is a control or colour map --
  `m_splatControlMap` and `m_colorVariationTex` are both candidates and it is not
  settled which.
- The surrounding machinery is named too: `HGASMVirtualTextureAllocator` with
  `AllocateTile` and `GetVTData`, `ASMTileManager` with an LRU tile cache,
  `HGTerrainGroundLayerClipmap` with `Initialize`/`Render`/`SetPlayerCenter`, and
  `HGTerrainGroundLayer` carrying `TEXTURE_SIZE` and
  `TERRAIN_GROUND_LAYER_CLIPMAP_NUM` with base, normal, wet and height render targets.
- So this family is **GPU texture data for a virtual-texture terrain splat system**,
  the same shape of answer the IrradianceVolume payload turned out to have.

### The engine's constants are readable, and they decode as compressed integers

`fieldDefaultValues` in `global-metadata.dat` holds every `const` in the image, and the
blob is **ECMA-335 compressed unsigned integers** -- not raw 4-byte values. Reading it
as raw int32 gives garbage like `TEXTURE_SIZE = 262280`; decoded properly:

| constant | value | | constant | value |
| --- | --- | --- | --- | --- |
| `HGTerrainGroundLayer.TEXTURE_SIZE` | **2048** | | `VT_CACHE_PAGE_RESOLUTION` | **512** |
| `TERRAIN_GROUND_LAYER_CLIPMAP_NUM` | **4** | | `VT_CACHE_PAGE_BUFFER_SIDE_SIZE` | **128** |
| `ASMTileManager.MAX_TILE_COUNT` | **512** | | `VT_CACHE_PAGE_BUFFER_SIZE` | **8192** |
| `VT_CLIPMAP_BASE_WIDTH` | **16** | | `VT_INDIRECT_TEX_BUFFER_COUNT` | **6** |
| `VT_WORK_GROUP_COUNT` | **64** | | `VT_GPU_FEEDBACK_BUFFER_COUNT` | **8** |
| `VT_COMPRESS_LOCAL_THREAD_COUNT` | **32** | | `VT_CPU_FEEDBACK_RAYCAST_DIST` | **1000.0f** |

**Three things check the decoder at once.** Every integer comes out a power of two or a
small round number; the one float reads exactly `1000.0`; and each field's `dataIndex`
advances by exactly the width the decoder consumed -- 1 byte for values under 0x80, 2
above. A wrong decoding satisfies none of those. *This is reusable: any `const` in the
image is now readable the same way.*

### The `LAYER_*` files are NOT raw texture slices

With `TEXTURE_SIZE = 2048` in hand the prediction was testable, and it fails:

| family | files | distinct sizes | typical |
| --- | --- | --- | --- |
| `LAYER_N` | 345 | **67** | ~1.33 MiB |
| `LAYER_D` | 345 | ~60 | ~1.20 MiB |
| `LAYER_C` | 54 | 9 | 0.86-1.11 MiB |

No size is a multiple of a 2048x2048 surface at any block rate -- the ratios land on
0.32, 0.64, 0.55 and similar, never a whole number or a mip chain. **Sizes that vary
file by file are not raw slices**, so the payload is compressed or variably encoded,
exactly as the IrradianceVolume payload turned out to be.

*The constant gave the prediction a number to fail against. Without it "about 1.3 MB" would have looked like agreement with almost anything.*

### CORRECTION: the `LAYER_*` files were already decoded, by the terrain lane

They are in the **Terrain** block -- 744 of them, which the CLI confirms -- and
`terrain_stream.load_samples` takes *every* file in that block rather than only
`Terrain_*`. So they have been inside the gated corpus the whole time.

- Running the maintained codec over them: **744 of 744 close**, 743 through the stream
  decoder and 1 stored, each to exactly its declared length. Every decoded payload
  begins `TRET`.
- Only **two decoded sizes** exist: 1,398,148 (x690) and 1,398,121 (x53).
- **The terrain report already names that group.** `terrain_tret_latest.json` carries
  `layer2And3.frontier108And109.files = 690`, status `exact_anonymous_record_tiling` --
  the same 690 files, already closed, already gated, counted inside the 46,164.

***I nearly reported "744 of 744 decode" as a new result.*** It is not. The decode is
the terrain lane's, done long ago; the filename triage found a family the block-level
corpus had already swallowed. *A file-name family and a block are different
partitions, and a new name for an old set is not a new set.*

**What IS new here** is the naming. The terrain report calls that group
`exact_anonymous_record_tiling` -- exact, and anonymous -- and its header report already
carries the formats:

| family | format | files | `VirtualTextureRenderer` field |
| --- | --- | --- | --- |
| `LAYER_D` | `mips11_format108` | 345 | **`m_splatsDiffuseArray`** |
| `LAYER_N` | `mips11_format109` | 345 | **`m_splatsNormalArray`** |
| `LAYER_C` | `mips11_format5` | 53 | see below |

`frontier108And109` in `terrain_tret_latest.json` is exactly **formats 108 and 109**,
which is exactly `LAYER_D` and `LAYER_N`. **690 anonymous records now have a name, and
the 940 MB they hold has a purpose.**

#### `LAYER_C` is per-layer and optional, which rules out the control map

Across the **38 directories** that hold LAYER files:

- **`D` and `N` carry identical index sets in all 38** -- strictly paired, one diffuse
  and one normal per splat layer. That confirms the pairing rather than assuming it from
  the equal totals.
- **`C` appears in only 22 of the 38**, and sparsely where it does: 1 `C` against 4
  `D`/`N`, 4 against 18, 2 against 27, 1 against 7. Its indices run to 34, the same
  layer-index shape as `D` and `N`.

An **optional, per-layer** texture is `m_colorVariationTex`. It is **not**
`m_splatControlMap`: a control map is one per terrain, always present, and would not
carry a layer index nor be absent from 16 directories. *The distribution settles which
of the two candidates it is without needing to read a byte of its content.*

##### REOPENED: a rival candidate the distribution argument could not have weighed

The argument above chose `m_colorVariationTex` by eliminating `m_splatControlMap`. The
engine, read since, offers a **third** candidate with the same profile, and the choice is
no longer forced.

**A per-layer mask map is a first-class concept here.** `maskMapRemapOffset` and
`maskMapRemapScale` sit inside **`TerrainLayerInfo`** and **`SplatLayerData`** -- the
*per-layer* structs -- and the shader side carries `_MaskMapTexture`,
`_MaskMapRemapMin/Max/Offset/Scale`. An optional, layer-indexed third texture is exactly
what a mask map is.

**And the typing mildly favours the rival.** `VirtualTextureRenderer` binds three:

| field | type index |
| --- | --- |
| `m_splatsDiffuseArray` | **144608** |
| `m_splatsNormalArray` | **144608** |
| `m_colorVariationTex` | **144600** *(different)* |

*The two per-layer arrays share one type; the colour-variation binding has another* -- the
shape of `Texture2DArray` twice and `Texture2D` once. A single non-array binding is an odd
consumer for files that carry layer indices running to 34, whereas the mask map's
parameters are stored per layer.

**The census is reproduced, not disputed.** An independent count gives `C` in 22 of 38
directories, 54 files against 345 each of `D` and `N`, with `D` and `N` equal in every
directory -- matching the numbers above exactly.

***The discriminator was run, and it disconfirms the answer above.*** Resolving the indices
through `MetadataRegistration.types` in `GameAssembly.dll` (225,789 entries at VA
`0x18c472bb0`; the type enum is bits 16-23 of the `Il2CppType` bitfield):

| field | type index | declared type |
| --- | --- | --- |
| `m_splatsDiffuseArray` / `m_splatsNormalArray` | 144608 | **`UnityEngine.Texture2DArray`** |
| `m_colorVariationTex` | 144600 | **`UnityEngine.Texture2D`** |

**The arrays are per-layer; the colour-variation binding is a single texture.** And the
argument that selected it eliminated `m_splatControlMap` on the grounds that *"a control map
is one per terrain, always present, and would not carry a layer index"*. **`Texture2D` is
one per terrain too** -- so the elimination that chose this answer also rules it out. *A
distribution argument can only separate candidates it has typed; this one separated a name
from a name.*

**The rival does not simply inherit the win.** `VirtualTextureRenderer` binds exactly
`m_splatsDiffuseArray`, `m_splatsNormalArray`, `m_colorVariationTex` and
`m_decalBlockMaskLut` -- there is **no mask-map texture array**. The mask map's
`maskMapRemapOffset`/`maskMapRemapScale` are `UnityEngine.Vector4` *parameters* per layer,
which is consistent with a mask packed into the existing arrays rather than shipped as its
own files.

**So `LAYER_C`'s consumer is unidentified, and that is a firmer position than before**: the
recorded answer is positively disconfirmed rather than merely unconfirmed, and the obvious
rival is ruled out by the binding list. What fits the evidence -- 54 layer-indexed files,
1-3 per directory, format 5 against 108/109 -- is something bound outside
`VirtualTextureRenderer` entirely, which is where the next look belongs.

`LAYER_C` also uses format **5** where `D` and `N` use 108 and 109 -- a low, presumably
standard format against two engine-specific ones, which is consistent, though the format
numbers themselves are not decoded.

*Two batches were spent eliminating containers for IrradianceVolume before asking the
metadata. This family got asked first, and the answer arrived in one read.*

**A route to `LAYER_C`'s purpose that is now closed.** `LAYER_` occurs **132** times in
`global-metadata.dat`, which looks like the obvious place to look next. It is not: every
one of those is an **animation** layer -- `LAYER_MAIN`, `LAYER_UPPER`, `LAYER_TWO_ARMS`,
`LAYER_LOOKAT_PITCH_YAW`, `LAYER_MASK2` -- plus a few concatenated string-table runs. The
terrain `LAYER_*` files share a prefix with an unrelated concept, and *a string search
that matches the wrong namespace is worse than no hits, because it returns something.*
`LAYER_C`'s purpose stays where the distribution argument left it.

## `InitChunkData`: the same container as terrain, and a named FlatBuffers schema

**26,520 files, 624 MB** -- the largest `.bytes` family by file count. Streaming a
312-file slice (`InitChunkData_-1_-1_0_0.bytes`, which recurs across scenes):

- **312 of 312 decode with the maintained terrain codec.** The custom LZ4 with
  big-endian offsets and bit-interleaved tokens in
  `scripts/asset_builder/terrain_stream.py` -- built for `Terrain_*` -- decodes these
  byte-exactly, each to the length its own leading word declares. *The container is
  shared across two families that no naming convention connects.*
- **All 312 decoded payloads are valid FlatBuffers**: root offset in range, vtable
  reachable, and a root table of **8 vtable slots** in every one.

The schema is named in the IL2CPP metadata:

```
Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneChunkData
    Version, StreamingVersion, UniqueId, Grids[], TotalStr[]

Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneSingleGrid   (278 methods)
    UniqueId, SceneVisibleStateInts, SceneVisibleAreaInts, PrimitiveIntList,
    PrimitiveStringList, DataIndex, Vector3, Model, Effect, Ecs, EcsModel,
    DataGroup, ResourceGroupWithStateDesc, NavModifyArea, MountPair, IntStrMapEntry,
    MissionCondition, IdComp, SeatComp, PureFuncComp, TriggerComp, HittableComp,
    FactoryBlockComp, DynamicEntityControlComp, NavModifyAreaComp,
    InteractiveStateComp, ViewStateControlComp, MissionControlComp,
    GlobalVarControlComp, SettlementControlComp, FactoryRegionControlComp,
    ScriptControlComp, ResourceComp, RootComp, TreeRootComp, DecorationRootComp,
    ErosionRootComp, ModelViewStateControllerNewComp, ConveyorBeltComp,
    ConveyorBeltBoxComp, ConveyorBeltGroupComp, ConveyorPath, PureSystemComp,
    NatureResourceComp, SludgeComp, Bounds, ExtraSceneComp, SceneGridInfo,
    RemapSceneComp, WaterPipeComp, StreamingAreaComp, NavmeshObstacle,
    MapVarControlComp, ActivityCondition, ActivityControlComp, PoiControlComp,
    BlightMiasmaComp, LodGridResource, SnowFallTreeComp, Desc, **DataMask**
```

- ***`DataMask` is in there***, the field this file's own Remaining-gaps list names as
  unresolved. It is a field of `FBDynamicSceneSingleGrid`, alongside sixty-odd
  component vectors that say what a scene grid holds: conveyor belts, nav-mesh
  obstacles, mission conditions, factory blocks, erosion and sludge, POI control.
- Smaller schemas named alongside: `FBDynamicSceneActivityControlComp`
  (`Conditions`, `CompareType`, `ToBeTrue`), `FBDynamicScenePoiControlComp` (`Id`,
  `DomainType`), `FBDynamicSceneSingleGridDescriptor` (`Scene`, `Ranges`),
  `FBDynamicSceneVersionData` (`Entries`, `Major`, `Minor`).

#### TESTED AND DISPROVED: the root is not `FBDynamicSceneChunkData`

The previous paragraph said the schema was *named*, not matched, and flagged the match
as unproven. It is now tested, and it fails.

- **Reading the 8 slots as the declared field order does not work.** `Grids` and
  `TotalStr` produce **identical** length distributions -- 1 in 46 files, 5 in 16, 3 in
  16, 4 in 15 -- which two independent vectors would not. And walking the supposed
  `Grids` elements, **0 of them resolve to a table**, in every file.
- **No declared root type has 8 fields.** The whole image contains exactly **six**
  FlatBuffers types with a `GetRootAs*`: `FBDynamicSceneChunkData` (5),
  `FBDynamicSceneSingleGrid` (61), `FBDynamicSceneSingleGridDescriptor` (2),
  `FBDynamicSceneVersionData` (3), `FBFactoryChunkData` (5) and
  `FBStreamAreaTotalData` (7). **None is 8.**
- The root's inline object is **40 bytes** in all 312 files, consistent with eight
  4-byte fields plus the vtable offset -- so the 8 slots are real fields, not deprecated
  holes.

**So `InitChunkData` is a FlatBuffer whose schema has no generated C# accessor.** Like
the IrradianceVolume payload, it is read natively; the `FBDynamicScene*` classes are a
different family that happens to sit in the same namespace.

***A schema that fits the subject matter is not thereby the schema of the file.*** The
sixty component names -- conveyor belts, nav-mesh obstacles, sludge, POI control --
described a scene grid so plausibly that it read as a match. The vtable disagreed in
two independent ways within one test.

**What survives, all of it measured from the bytes:**

| | |
| --- | --- |
| terrain codec decodes | **312 / 312**, each to its declared length |
| decoded payload is a valid FlatBuffer | **312 / 312** |
| root vtable slots | **8**, in every file |
| root inline object size | **40 bytes**, in every file |
| slot 0 | **constant 47** across all 312 -- a version, on any reading |

#### The root schema, read from the bytes with no schema at all

**One vtable layout in all 312 files** -- offsets `(4, 8, 16, 20, 24, 28, 32, 36)` with a
40-byte inline object -- so every field's width falls out of the gaps, exactly as the
IrradianceVolume config layout did:

| slot | offset | width | type, from what it points at |
| --- | --- | --- | --- |
| 0 | +4 | 4 | **`u32` = 47 in all 312** -- a version |
| 1 | +8 | **8** | 64-bit scalar |
| 2 | +16 | 4 | `u32` scalar (289 of 312 read as one) |
| 3 | +20 | 4 | **vector** (277 plain, 22 also table-like) |
| 4 | +24 | 4 | **vector** |
| 5 | +28 | 4 | **vector of tables** -- all 312 |
| 6 | +32 | 4 | **vector of tables** -- all 312 |
| 7 | +36 | 4 | **vector of tables** -- all 312 |

Each vector-of-tables classification is earned: the vector length is read, then the
first elements are followed as uoffsets and each must land on a table whose vtable
resolves. **Slots 5, 6 and 7 pass that in every file.**

**That single layout is itself the evidence.** 312 files of wildly different sizes --
171 bytes to 4.5 MB -- share one vtable byte-for-byte, so they are one schema, and the
typing is a statement about that schema rather than about a sample.

**And it independently confirms the disproof.** `FBDynamicSceneChunkData` is three
scalars and two vectors. This root is **three scalars (one of them 64-bit) and five
vectors, three of which hold tables**. They are not the same shape, which is a second,
structural reason beyond the failed vector walk.

#### The element tables, also read from the bytes

Walking the three vector-of-tables slots and collecting every element's vtable:

**Root slot 5 -- 7,272 element tables**, three layouts:

| slots | inline object | field widths | count |
| --- | --- | --- | --- |
| 6 | 40 | 4, 4, 4, 4, **16**, 4 | 4,294 |
| 4 | 20 | 4, 4, 4, 4 | 733 |
| 6 | 44 | 4, 4, 4, 4, **20**, 4 | 675 |

**Root slot 6 -- 642 element tables**, a single layout: **1 slot, 8-byte object, one
4-byte field.** No variation at all.

**Root slot 7 -- 642 element tables**, two layouts:

| slots | inline object | field widths | count |
| --- | --- | --- | --- |
| 5 | 60 | **20**, 4, **24**, 4, 4 | 430 |
| 5 | 56 | **16**, 4, **24**, 4, 4 | 212 |

- **Slots 6 and 7 are parallel arrays.** Identical vector-length distributions in every
  file -- 0 in 48 files, 1 in 166, 2 in 49, 3 in 14, 4 in 5 -- and **exactly 642 elements
  each**. Two vectors that agree on length in all 312 files are indexed together.
- **The 16, 20 and 24-byte fields are inline structs**, which is the only thing a
  FlatBuffers field of that width can be -- four, five or six 32-bit values held in the
  table rather than behind an offset. The 16-versus-20 variation in slot 5 and the
  16-versus-20 in slot 7 are the same choice appearing twice.
- Slot 5's population is a different scale entirely: 7,272 elements against 642, with
  its own length distribution.

**Where this family now stands**, all from the bytes and none of it from a schema:

| | |
| --- | --- |
| container | terrain codec, **312 / 312** |
| format | valid FlatBuffers, **312 / 312** |
| root | 8 fields: 3 scalars (one 64-bit), 2 vectors, 3 vectors-of-tables -- one layout in all 312 |
| element tables | typed for all three vector slots, 8,556 tables read |
| managed schema | **excluded twice** -- failed vector walk, and no declared root has 8 fields |

#### ROOT SLOT 1 IS THE CHUNK'S WORLD ORIGIN, joined to the filename

The first field in this family with a *meaning*, and it came from a join rather than a
name. Streaming **7,433** files across **361** distinct grid coordinates:

```
root slot 1, at table offset +8, eight bytes = two int32
    +8  == x * 128        where x, y are the coordinates in
    +12 == y * 128        InitChunkData_<x>_<y>_0_0.bytes
```

**7,433 of 7,433**, with the controls failing as they should:

| reading | files |
| --- | --- |
| `+8 = x*128, +12 = y*128` | **7,433 / 7,433** |
| axes swapped | 633 -- exactly the `x == y` cases where both readings coincide |
| scale 64 or 256 | 85 -- exactly the origin chunks, where every scale gives 0 |

So the 64-bit field is the chunk's **world-space origin**, and **128 is the chunk size
in world units**. The 361 distinct coordinate pairs map to 361 distinct field values,
one-to-one.

***This also explains how the wrong schema looked right.*** Under
`FBDynamicSceneChunkData` this slot read as `StreamingVersion`, with values 4294967168
and 128 -- which is `0xFFFFFF80`, i.e. `-128`, i.e. `x * 128` for `x = -1`. A plausible
name made a coordinate look like a version number. *The join to the filename settles in
one test what no amount of reading the field alone could.*

#### THE SLOT-7 ELEMENTS CARRY WORLD PLACEMENTS, found by joining to that origin

With the chunk origin known, the chunk is a **box in world units**, and a box is
something the other slots can be tested against. Over the same 7,433 files:

**Slots 5 and 6 are not spatial at all.** Every float-shaped field in them is
**0.0% non-denormal** -- the bytes are small integers, and reading them as float gives
denormals near zero. *Their apparent "box hits" in the first pass were entirely that
artefact:* a denormal lands in whatever box straddles zero, which is why own-box and
neighbour-box scored identically (28.9% vs 28.8%). **A test whose control matches it is
measuring the control.**

**Slot 7's element field 2 is a 24-byte inline struct of six floats.** Both element
shapes give it 24 bytes (`obj 60`: offsets 28..52; `obj 56`: 24..48), and it is either
**wholly zero or wholly populated, with zero exceptions**:

| | elements |
| --- | --- |
| all 24 bytes zero (unset) | 3,904 |
| populated | 7,112 |
| *records mixing the two* | **0** |

**The first triple is a world-space position, `(x, height, z)`:**

| reading | share of 7,112 |
| --- | --- |
| **f0 in own chunk's x, f2 in own chunk's z** | **73.96%** |
| same test against a neighbour chunk (control) | **1.28%** |
| `(f0, f1)` as the two axes -- the non-Y-up reading | 6.25% |
| rotations `(f1, f0)`, `(f2, f1)` (controls) | 1.92%, 1.91% |

A **58-fold** margin over the spatial control. The axis assignment is then confirmed a
*second* time, without using the box at all -- by sign:

```
axis 0 negative  61.7%      axis 1 negative   4.9%      axis 2 negative  48.2%
```

The middle axis is the one that stays positive, which is what a height does and what a
horizontal coordinate does not. *Two independent lines, one from geometry and one from
sign, pick the same middle float.*

**The second triple is non-negative, always.** 0 of 21,336 components negative across
7,112 records, range 0..687 -- while the position triple in those same records is
negative 61.7%/4.9%/48.2% of the time. It is **not** a second position (2.18% own box
against a 2.26% control -- chance), not a unit quaternion (lengths 411..693), not a
scale (magnitudes in the hundreds). An extent is consistent with all of it, but nothing
here *discriminates* an extent from any other non-negative triple, so it stays
**structural-only**.

***Disproved along the way:*** the six floats as a min/max bounding box. `min <= max`
componentwise holds for 38.52% -- **below** its own reversed control at 43.22%, and level
with a shuffled pairing at 37.69%. *The reversed control outscoring the claim is the
cleanest possible refutation, and it cost one run.* The `f3..f5 >= 0` check scored
100.00% in that same run and meant nothing, because the unset records were still in the
denominator; it only became evidence once the population was restricted to the 7,112 and
the position triple supplied the contrast.

#### THE ELEMENT'S FIRST FIELD IS A DESCRIPTOR THAT STATES ITS OWN CATEGORY TWICE

Field 0 is 16 bytes at offset +4 and takes only **34 distinct values** across 11,016
elements -- a vocabulary, so a type or flag word, not a per-instance identifier. Read as
eight u16 it comes apart cleanly.

**It partitions the placements perfectly.** Of the 34 values, **0 occur both placed and
unset**: 2 values are unset-only (3,831 + 73 = exactly the 3,904 unset records) and 32
are placed-only. Byte 1 alone carries it -- non-zero for **7,112 of 7,112** populated and
zero for **3,904 of 3,904** unset.

**Byte 1 is one-hot, without exception**: 7,112 of 7,112 are a single set bit, drawn from
`{01, 02, 04, 08, 10, 20}`. A byte that happened to be one-hot would manage it 8 times in
256.

**The fifth u16 restates the same category, shifted four bits.** Writing `byte1 = 2^k`,
that word carries the bits `8 | 2^(k+4)`:

| test | share |
| --- | --- |
| **w4 carries the bits for k** | **6,570 / 6,570 = 100.00%** |
| same test with k+1 (control) | **0.00%** |
| same test with k-1 (control) | **0.00%** |

*Both shifted controls at exactly zero is the strongest form this evidence takes:* the
relation is not merely frequent, its neighbours are impossible. The census is conditioned
on the `w1 == 0x2024` family (6,570 elements); the other families, `0x0820` (393) and
`0x1020` (149), leave w4 zero. Eight elements carry the predicted bits *plus* one extra
bit (73 = 72|1, 137 = 136|1, 4360 = 264|4096), which is why the relation is a **subset**
test and not equality -- as equality it would have shown 8 spurious counter-examples.

**Field 4 is the constant 4** in all 11,016 elements.

***Disproved:*** field 3 as an index into a sibling vector. Its 2,136 distinct small
integers look exactly like indices, but they fall inside slot 5's length only 4.37% of
the time and inside slots 6 and 7 **never**. Field 1 scores 90.45% against slot 5, which
is not evidence either -- its values are 1, 2 and 4, and *any* small integer clears that
bound. **A containment test only discriminates when the candidate could plausibly fail.**

#### THE 24-BYTE FIELD IS `FBDynamicSceneBounds`, AND THE NAME COMES FROM IL2CPP

The name from outside arrived. IL2CPP carries **73 generated FlatBuffers types**, 65 of
them in **`Beyond.Gameplay.Core.DynamicScene`** -- so InitChunkData belongs to the
DynamicScene family, and its generated vocabulary is readable:

| type | components | bytes |
| --- | --- | --- |
| `FBDynamicSceneVector3` | X, Y, Z (Single) | 12 |
| **`FBDynamicSceneBounds`** | **Center, Extents (Vector3)** | **24** |
| `FBDynamicSceneVisibilityInfo` | Center, BaseRadius, MinDis, Importance | 24 |
| `FBDynamicSceneTransform` | Pos, Rot, Scl (Vector3) | 36 |
| `FBDynamicSceneLodGridChain` | Lod0Grid, Lod1Grid, Lod2Grid (UInt32) | 12 |
| `FBDynamicSceneDataIndex` | IsInvalid, Type, Grid, Index | 13 |

**`Bounds` explains every byte-side observation at once**, and it was found by matching
the *shape* -- a 24-byte inline struct of six floats -- not by matching a name:

- **Center** is the first triple: a world position, in its own chunk 73.96% against a
  1.28% control
- **Extents** is the second triple, and an extent is a **half-size, so never negative** --
  which is exactly the 0-of-21,336 result, an invariant that had no explanation until
  the type supplied one
- `min <= max` had to fail: this is centre-and-extents, *not* a min/max pair. **The
  reading that the control killed was the reading the type was never going to support.**
- centre + extents lands in the chunk 32.94% of the time, which is what an AABB's far
  corner does -- it leaves the chunk whenever the object is large

**`VisibilityInfo` is ruled out, and it had to be ruled out** -- it is also 24 bytes, also
starts with a `Center`. The two differ in one place: its final component is
`Importance:Int32`, which read as a float would be a denormal.

| | share of 7,112 |
| --- | --- |
| f5 is a normal float | **7,112 / 7,112 = 100.00%** |
| f5 as Int32 in an Importance-like range | **0 / 7,112 = 0.00%** |

***`FBDynamicSceneModel` was also ruled out, by width.*** Its five fields match the
element's five exactly and its names are tempting -- `Guid, Trans, GridChain, PathHash,
VisInfo` -- but its slot 3 is `Int64`, eight bytes, where the data measures four. *A
five-field type with a plausible name is not a match; the widths are the match.*

##### The Bounds attribution has to be narrowed: the element is not a managed table

Checking the rest of the vocabulary walks part of the previous claim back, so it is
stated here rather than left standing.

**Exactly one of the 72 generated tables carries a `FBDynamicSceneBounds` field** --
`FBDynamicSceneSludgeComp`, which has **27** fields against the element's 5. And running
the widths against *every* generated table with 5 non-vector fields, **none matches**
`[16|20, 4, 24, 4, 4]`:

| table | widths |
| --- | --- |
| `FBDynamicSceneModel` | `[16, 36, 12, 8, 24]` |
| `FBDynamicSceneSeatComp` | `[4, 4, 12, 12, 4]` |
| `FBDynamicSceneRootComp`, `ActivityCondition`, `SettlementControlComp` | all `[4, 4, 4, 4, 4]` |
| `FBFactorySingleGridRangeData` | `[4, 4, 4, 4, 4]` |

So **the slot-7 element table is read by nothing in the managed assembly** -- the same
native boundary the IrradianceVolume lane hit. That is a real finding, and it is also the
reason the name has to be qualified.

***What survives and what does not.*** The *reading* stands on the bytes alone and is
unaffected: a centre that sits in its own chunk 73.96% against a 1.28% control, and a
second triple that is non-negative in 21,336 of 21,336 components. **What does not stand
is the stronger form -- that this field IS the declared `FBDynamicSceneBounds`.** The
engine declares a type with exactly this layout and that name, which is good evidence
that centre-and-extents is a real layout in this codebase; it is *not* evidence that this
particular field is that type, because no table that could contain it uses it. *The name
describes the layout; it does not locate a use site.* Anyone taking the earlier phrasing
literally would go looking for a managed reader that does not exist.

Note also that `FBDynamicSceneGuid` is **16 bytes** (V0..V3, UInt32) -- exactly slot 0's
width. It is still not a match: a GUID does not take **34 distinct values** across 11,016
records.

#### WHY SLOTS 5 AND 6 STAY UNINDEXED: THE CORPUS HAS NO VARIATION TO INDEX

Not "not yet decoded" -- **decoded, and almost empty.** Establishing that is what stops
this being mined forever.

**The root layout is one shape, everywhere.** Offsets `(4, 8, 16, 20, 24, 28, 32, 36)`,
object size 40, in **7,433 of 7,433** files. A single layout, no variants.

**Slots 6 and 7 are genuinely parallel, and that was worth proving rather than assuming.**
`len(slot6) == len(slot7)` in **7,433 of 7,433** files with identical length
distributions -- which is exactly what reading *one* vector twice would also produce. It
is not that: resolving every root slot and comparing landing offsets, slots 6 and 7 never
coincide, and they **share zero element tables**. (Only slots 1&4 and 1&2 ever alias, in
10 and 1 files.) *Two vectors agreeing that precisely is a reason to check for aliasing,
not a finding.*

**Slot 6 carries no information at all.** Its elements have exactly one vtable layout,
`((4,), 8)` -- a single four-byte field -- in **11,016 of 11,016**, and that field holds
**4 in every element of every file**: one distinct value corpus-wide, across 349 distinct
chunk coordinates.

***A vacuous test, caught by running the control both ways.*** The natural reading of a
vector parallel to the placements is an offset table into slot 5, which predicts
non-decreasing values. That scored **100%** -- and so did **non-increasing**. Both
directions at 100% means the values never change, and the hypothesis was never under
test. **When a claim and its opposite both pass, the corpus is degenerate, not
confirming.** The slot-6 constant is why.

**Slot 5 is a real table vector -- checked, not assumed.** Its scalar fields hold values
like 36, 32 and 40, which are also the object sizes in its own vtable layouts, and that
coincidence is what reading a vtable *as* a table produces. The discriminator is that
FlatBuffers shares one vtable across same-shaped tables, so a genuine table vector has far
fewer vtable addresses than elements:

| slot | elements | distinct vtable addresses | per element |
| --- | --- | --- | --- |
| 5 | 185,063 | 18,480 | **0.100** |
| 6 | 11,016 | 3,979 | 0.361 |
| 7 | 11,016 | 5,207 | 0.473 |

All far below 1.0, with forward uoffsets at 100.0%. The reading holds.

**But slot 5's variation is almost nil**: across 185,063 element tables its scalar fields
carry only **5 to 29 distinct values** each, and its 16/20-byte field is **all zeros in
156,058 of 156,058 reads**.

***One more coincidence declined.*** Slot 5's wide field is 16 or 20 bytes -- the same
signature as slot 7's 34-value descriptor, which invites treating them as one vocabulary.
They **share 0 values**: slot 5's is a single all-zero constant. *Matching field widths
are not a shared type.*

#### NO MANAGED CODE NAMES THESE FILES, AND THE TEMPTING MAPPING FAILS ITS OWN TEST

Chasing the reader through the filename ends in a clean negative:

| literal | global-metadata.dat | GameAssembly.dll |
| --- | --- | --- |
| `InitChunkData_` | **0** (ASCII and UTF-16) | **0** |
| `ChunkData_` | 0 | 0 |
| `_0_0.bytes` | 0 | 0 |
| `InitChunkData` | 2 -- *both* the method `_InitChunkDataPool` | 0 |

So **no managed string literal constructs these filenames.** The two hits are a
`MapManager` method that initialises a chunk-data *pool*, not a path. These files are
addressed some other way -- by catalogue id or hash -- which is consistent with the VFS
design and with the slot-7 element matching none of the 72 generated accessors.

***The mapping that looks obvious, and why it is refused.*** `MapManager+
LoaderChunkStaticData` holds **three** collections -- `grids`, `tiers`, `mists` -- against
the root's **three** vector slots, and `TierLoadConfigInfo` and `MistLoadConfigInfo` each
have **exactly 5 fields**, matching the slot-7 element's 5. Two independent-looking
coincidences pointing the same way.

It is still refused, on two counts:

1. **The widths disagree.** Both config types spend three of their five fields on vector
   members (`worldCenter`, `worldLeftBottom`, `worldRightTop`), where the data has one
   24-byte field and four small ones -- `[16|20, 4, 24, 4, 4]`. *A field-count match with
   a width mismatch is the same mistake `FBDynamicSceneModel` already cost.*
2. **The data argues against it directly.** `len(slot6) == len(slot7)` in **7,433 of
   7,433** files, with identical length distributions down to the 3,454 files where both
   are empty. Two *independent* collections -- tiers and mists -- would not have equal
   counts in every chunk in the world. Slots 6 and 7 read as **two parallel arrays over
   one list**, not as two separate concepts.

*The second point is the useful one: it is evidence from the corpus rather than an
absence of evidence from the binary, and it would still hold if a matching schema turned
up tomorrow.*

##### CONFIRMED LATER: the engine's own types say the same thing

The `<type-index:...>` placeholders that blocked this at the time are resolvable through
`MetadataRegistration.types` in `GameAssembly.dll`. Resolved, `LoaderChunkStaticData` reads:

```
loadConfig      Beyond.Gameplay.ChunkLoadConfigInfo     chunkId    string
compareId       uint                                    globalId   uint
levelId         string                                  levelNumId int
rectCenter / rectLeftBottom / rectRightTop  UnityEngine.Vector2
grids           List<...>
tiers           Dictionary<,>          mists      Dictionary<,>
```

***`tiers` and `mists` are dictionaries, not lists.*** The mapping was refused because
`len(slot6) == len(slot7)` in 7,433 of 7,433 files and two independent collections would not
match that exactly. The engine now says something stronger and quite separate: **two of the
three are not even the same container kind as the third**, so they could not serialize as
three parallel vectors whatever their lengths. *A refusal made on corpus evidence, upheld a
second time by type evidence that did not exist when it was made.*

Also worth keeping: the chunk rectangles are **`Vector2`** -- the loader addresses chunks in
two dimensions, matching `StreamingChunkInfo`'s two-int32 entries, while the *filenames*
carry a third coordinate that varies 0..7. And `LoaderLevelData` splits its chunks into
`lowChunks` / `mediumChunks` / `highChunks`, three `List<>` of chunk references, which is a
LOD tiering of chunks rather than of anything inside them.

#### THE SIX CATEGORIES ARE UNORDERED: THE SIZE-CLASS READING IS REFUSED

The `w4 = 8 | 2^(k+4)` lock-step makes `k` look like an index into something *ordered* --
an LOD ladder or a size class -- which predicts that extents grow with `k`. Taking the
geometric mean of each record's three extents and the median per category:

| k | records | median extent | p25 | p75 |
| --- | --- | --- | --- | --- |
| 0 | 1,711 | 36.42 | 14.48 | 67.30 |
| 1 | 1,178 | 30.32 | 11.09 | 58.09 |
| 2 | 1,824 | **96.06** | 34.24 | 195.05 |
| 3 | 1,204 | 39.48 | 16.85 | 59.89 |
| 4 | 807 | 36.21 | 15.57 | 54.89 |
| 5 | 388 | 33.77 | 14.21 | 50.73 |

**Neither increasing nor decreasing.** Exact monotonicity across six bins would be a
1-in-720 accident, so this had real power to confirm; it declined. `k` is a **categorical
label, not a scale**, and the bit-shift relation between `byte1` and `w4` is an encoding
convenience rather than an ordering.

What the census does show: **k=2 is the distinctive class** -- the largest population and
extents roughly three times the rest -- and **k=0 is the only category carrying the
`0x0820` family** (393 of its 1,711). Both element object sizes, 56 and 60, occur in
every category in roughly equal share, so the two shapes cut across the categories rather
than encoding them.

**Still open, with the route now narrowed:** what a slot-7 element *is*. Its category is a
6-valued **unordered** one-hot code confirmed twice over and its 24-byte centre/extents
field is read, but no managed accessor, no filename literal and no loader type matches it.
A name has to come from the native reader.

## `StreamingChunkInfo`: the per-level chunk index, and it checks out against the filenames

Asking what *else* lives in the directory turned out to be worth more than any amount of
further staring at the chunk payloads. Each level's `Data/Streaming/PC/<level>/Streaming/`
holds three families:

| file | per level |
| --- | --- |
| `InitChunkData_<x>_<y>_0_0.bytes` + `InitChunkData_Global_#_#.bytes` | one per chunk |
| `StreamingChunkData_<x>_<y>_0_0.bytes` + `_Global_` | **the same coordinates, paired 1:1** |
| **`StreamingChunkInfo.bytes`** | **exactly one -- the index** |

**The index is not in the terrain container at all.** It decodes with the terrain codec
**0 of 89** times, because it is a *plain, uncompressed FlatBuffers buffer* -- root
uoffset 16, vtable immediately after. Its neighbours in the same directory are all
codec-wrapped. *Sharing a directory does not mean sharing a container, and trying the
neighbour's codec first is what established that cheaply.*

**Framing, from the bytes.** 89 files, two root layouts and one element layout:

```
root   (4, 8, 12, 16) objectSize 20      x88        slot 3 = the chunk vector
root   (4, 8, 12)     objectSize 16      x1         DevOnly -- no slot 3
element (4, 12)       objectSize 16      x23,806    ALL of them, one layout
   field 0  8 bytes = two int32   the chunk's (x, y) grid coordinates
   field 1  4 bytes               the constant 4, in 23,806 of 23,806
```

Totals: **23,806 chunks indexed** across 88 levels, and exactly **88 sentinel entries** --
`(INT32_MIN, INT32_MIN)`, **one per level**, which is the `_Global_` chunk.

#### THE INDEX AGREES WITH THE FILENAMES EXACTLY, 88 OF 88

The reading makes a prediction with nothing fitted to it: for every level, the set of
coordinates *inside* the index equals the set of coordinates *in the filenames beside it*.
It can fail in both directions -- an index entry with no file, or a file with no entry.

| | levels |
| --- | --- |
| **exact set equality** | **88 / 88** |
| any mismatch, either direction | **0** |
| index did not frame | 1 (`DevOnly`, whose root has no slot 3) |
| **control: matches a *different* level's files** | **1 / 88** |

*Note the coordinates here are raw grid indices* -- `(-2, 0)`, `(-1, 1)` -- **not** scaled
by 128 the way `InitChunkData`'s own origin field is. The same quantity is stored in two
units in two places, which is exactly the sort of thing that makes a name-based guess go
wrong and a join go right.

***The control deserves its own note, because the single hit is real and not a weakness.***
One adjacent pair of levels does share an identical chunk set -- because the data genuinely
repeats: **73 distinct coordinate sets cover 88 levels**, with **14 levels sharing one
65-chunk set** and 2 sharing a 257-chunk set. Those are instanced layouts. So the control
fires where the world actually is duplicated, and nowhere else. *A control that returns
exactly zero is sometimes a control that cannot fire at all; this one could, did once, and
for a reason that is visible in the data.*

## `StreamingChunkData` shares `InitChunkData`'s schema -- and carries none of the placements

The paired family, over the same single-digit coordinate slice (**7,433 files each**, so
14,866 in total; the full family is larger):

- **7,433 of 7,433 decode with the terrain codec**, and show **one** root layout --
  `(4, 8, 16, 20, 24, 28, 32, 36)`, objectSize 40 -- *identical* to `InitChunkData`'s.
- **Slot 1 is the chunk origin here too: `(x*128, y*128)` in 7,433 of 7,433**, with the
  axes-swapped control at the same 633 symmetric cases. *This prediction was made from the
  Init family and tested on a family that had no part in fitting it.*
- **Slot 0 is the constant 47 in all 14,866 files of both families** -- a format version
  shared across the pair.

So the two are **one schema**. What separates them is population, and the split is total:

| | Init | Streaming |
| --- | --- | --- |
| slot 7 (placements) empty | 3,454 (46.47%) | **7,433 (100.00%)** |
| slot 5 length equal to its partner's | — | **7,433 (100.00%)** |
| byte-identical to its partner | — | **0 (0.00%)** |

***The naming intuition is backwards.*** `StreamingChunkData` carries **no placements at
all** in this slice, while `InitChunkData` carries them in 53.53% of chunks. Whatever
distinguishes the two files, it is not that the "streaming" one holds the streamed
objects. Their slot-5 vectors are the same length in every single pair, yet no pair is
byte-identical.

#### THE SCALAR SLOTS ARE SIZES, AND ONE EXACT RELATION TIES THEM TO SLOT 5

`s2 = s3 + 8 + 4 * len(slot5)` in **14,866 of 14,866 files**, both families, no
exceptions. Since a FlatBuffers vector occupies `4 + 4n` bytes, the gap between these two
scalars is exactly slot 5's serialized footprint plus four of alignment.

They are **not** offsets into the buffer: `s3 == slot-5 vector base`, `s2 == buffer
length` and every related test score **0.00%**.

##### SOLVED: they are payload sizes, and the formula is exact

Chasing the residual rather than the value settled it. `len(buffer) - s2` takes **exactly
two values** across all 7,433 Init files -- **44** (4,220) and **48** (3,213) -- and each
is fully determined by where the root table sits:

```
residual 44  <->  root at 24     4,220 of 4,220
residual 48  <->  root at 28     3,213 of 3,213
```

which is `rootOffset + 20`, and 20 is the root vtable's own size (4 header + 2x8 slots).
So:

| | Init | Streaming |
| --- | --- | --- |
| **`s2 == len - root - 20`** | **7,433 / 7,433 = 100.00%** | **0.00%** |
| **`s3 == len - root - 28 - 4*n5`** | **7,433 / 7,433 = 100.00%** | **0.00%** |
| control: `len - root - 16` / `- 24` | 0.00% | 0.00% |
| control: `len - 20`, dropping the root term | 0.00% | 0.00% |

**`s2` is the size of everything past the root vtable -- the serialized payload -- and
`s3` is that same size minus slot 5's vector footprint** (`4 + 4n` for the vector, plus 4
of alignment). The earlier exact relation `s2 = s3 + 8 + 4*n5` was these two formulas
seen from the side, with the length and root terms cancelling.

***That the same field means nothing of the sort in `StreamingChunkData` is the sharper
half.*** Every formula and control scores **0.00%** there, and `len - s2` spreads over
**845** distinct residuals. The two families share a root *layout*, a version constant and
a chunk origin -- and still do not agree on what slot 2 counts. *A shared schema does not
guarantee a shared meaning per field, and nothing short of testing the second family would
have shown it.*

### FULL-CORPUS GATE: 26,520 files per family, every claim re-run

Everything above was established on the single-digit coordinate slice. The gate re-runs it
over the whole family, and the headline is that **62.47% of the corpus -- 16,568
multi-digit-coordinate files -- had never been tested at all**, alongside 148 `_Global_`
files carrying no coordinate pair.

| claim | Init | Streaming |
| --- | --- | --- |
| total files | 26,520 | 26,520 |
| decoded with the terrain codec | 26,519 | 26,519 |
| **decode failed** | **1** | **1** |
| root layout `(4,8,16,20,24,28,32,36)`/40 | **26,519 / 26,519** | **26,519 / 26,519** |
| slot 0 == 47 | **26,519 / 26,519** | **26,519 / 26,519** |
| origin == `(x*128, y*128)` | **26,372 / 26,372**, 0 mismatches | **26,372 / 26,372**, 0 mismatches |
| origin unsupported (`_Global_`) | 147 | 147 |
| `s2 == len-root-20` | **26,519 (100.00%)** | **0 (0.00%)** |
| `s3 == len-root-28-4n5` | **26,519 (100.00%)** | **0 (0.00%)** |
| slot 7 (placements) empty | 20,517 (77.36%) | **26,519 (100.00%)** |

**Everything held, including on the 62% never previously seen.** And one slice-level
finding is *strengthened* rather than merely confirmed: `StreamingChunkData` carries
**no placements in any of its 26,519 decodable files, corpus-wide** -- not a property of
the sampled coordinates.

***The two failures are the same level, and they fail loudly.*** Both are `DevOnly`'s
`_Global_` files, rejected by the codec with `match offset 0 reaches before the output` --
a refusal, not a silent truncation. `DevOnly` is the consistent outlier in this family: it
is also the one level whose `StreamingChunkInfo` root has 3 slots instead of 4.

#### THE TWO FILES DISAGREE ABOUT HOW TO SPELL "GLOBAL"

All **294** decodable `_Global_` chunk files carry **one** origin value:

```
StreamingChunkInfo entry for the global chunk   (INT32_MIN, INT32_MIN)
InitChunkData_Global_* own origin field         (INT32_MAX, INT32_MIN)
```

*Same concept, two different sentinels, in files that sit in the same directory and
describe the same chunk.* The earlier 88-of-88 index join survived only because it matched
on **filenames**, not on origin values -- a join written the other way would have scored
zero and read as a refutation of a correct reading.

### THE `streaming` VFS BLOCK IS NOW FULLY INVENTORIED

A bounded completeness claim, which is worth more than another partial one. Streaming the
block with a filter that **excludes** the three known families returns **0 files**, so
nothing else is in there. The totals close exactly:

| family | files |
| --- | --- |
| `InitChunkData_<x>_<y>_0_0.bytes` | 26,372 |
| `InitChunkData_Global_#_#.bytes` | 148 |
| `StreamingChunkData_<x>_<y>_0_0.bytes` | 26,372 |
| `StreamingChunkData_Global_#_#.bytes` | 148 |
| `StreamingChunkInfo.bytes` | 89 |
| **total** | **53,129 files, 719.4 MB** |

and the five shapes sum to 53,129 with nothing left over. **Every family in this block is
framed, and the framing is gated over all of it.** Two files -- `DevOnly`'s `_Global_`
pair -- are reported as codec refusals rather than skipped.

***The schema is not shipped, and that is now checked rather than assumed.*** Streaming
the `table`, `json-data`, `extend-data` and `initial-extend-data` blocks for
`*.fbs`, `*.bfbs`, `*.schema` and `*.proto` returns **0 files**. So the two things still
unknown here -- what a slot-7 element *is*, and what slot 5's 19-value coupled code
selects -- **cannot be settled from the shipped data at all**. They need the native
reader. *That is a different statement from "not yet found", and it is the one the
evidence supports.*

#### WHERE THE NATIVE READER LIVES, AND WHY IT IS NOT READABLE

"Needs the native reader" is worth replacing with a measurement. The game ships
**`EndfieldBase.dll`, 35.8 MB**, which is the module that would hold a C++ FlatBuffers
reader -- and it yields **nothing**:

| probe | ASCII | UTF-16 |
| --- | --- | --- |
| `InitChunkData`, `StreamingChunkData`, `StreamingChunkInfo` | 0 | 0 |
| `ChunkData`, `Terrain`, `IrradianceVolume` | 0 | 0 |
| `flatbuffers`, `FlatBuffer` | 0 | 0 |

Section entropy says why:

| module | section | raw bytes | entropy |
| --- | --- | --- | --- |
| **`EndfieldBase.dll`** | **`.tvm0`** | **28,246,016** (79% of the file) | **7.60** |
| `HGP.dll` | `.tvm0` | 9,003,008 (92%) | **7.56** |
| `GameAssembly.dll` | `.tvm0` | 13,463,552 | 6.94 |
| `GameAssembly.dll` | `.text` / `il2cpp` | 11.2 MB / 165 MB | 6.46 / 6.35 |

**`EndfieldBase` is four fifths virtualised**, with the leftover `.rdata` at entropy 4.93
and odd companion sections (`.BNN`, `.i,9`) typical of a code virtualiser. `HGP.dll` is
the same construction plus `.detourc`/`.detourd` -- a detour engine, itself virtualised.

*This also explains the shape of every success so far.* `GameAssembly.dll`'s `.text` and
`il2cpp` sections are **not** packed, which is exactly why the managed metadata work keeps
paying -- 73 generated FlatBuffers types, field widths, `Il2CppFieldOffsets`. The moment a
question needs a *native* body, it moves into a `.tvm0` section and the evidence stops.
**The boundary is not "IL2CPP vs native"; it is "packed vs not", and it runs through
GameAssembly itself.**

##### CORRECTION: THE CEILING ABOVE IS WRONG -- I MEASURED THE WRONG MODULE

The paragraph this replaces concluded that every remaining question needs 28 MB of
entropy-7.6 bytes and that static recovery cannot reach it. **That is false, and the error
was testing `EndfieldBase.dll` because it looked like the right module rather than
following the evidence to the module that actually holds the code.**

**`UnityPlayer.dll` -- 33.1 MB, `.text` 25,530,880 bytes at entropy 6.52, not packed**
(its `.tvm0` is only 1.49 MB). This is a *heavily modified* Unity player carrying the
engine-side HyperGryph code with readable symbols:

| evidence in `UnityPlayer.dll` | count |
| --- | --- |
| `HyperGryph` symbols | **866** |
| `FlatBufferConvertContext` | 14 |
| `HG_ALWAYS_ASSERT failed on expression: '...'` | many, expression text intact |
| mangled `BindProxyEntityConvertFuncFromScript@HGStreamingSceneManager@HyperGryph@@...W4ProxyEntityType@3@` | present |
| `PropertySerializeId::GetComponentIndexFromType` | present |

#### AND THE FILENAMES ARE BUILT HERE, WHICH CORRECTS A SECOND CONCLUSION

The earlier note reasoned that because no complete `InitChunkData_` literal exists in
`global-metadata.dat` or `GameAssembly.dll`, the files must be "addressed by catalogue id
or hash". **The premise was right and the conclusion was wrong.** The format strings are
in `UnityPlayer.dll`, immediately beside the literals `Init` and `Streaming` that fill
their `{1}` slot:

```
{0}/{1}{2}ChunkData_{3}_{4}_{5}_{6}.bytes
{0}/{1}{2}ChunkData_Global_{3}_{4}.bytes
   ... adjacent literals: "Streaming", "Init"
```

*A search for `InitChunkData_` could never have found this, because the name does not
exist anywhere as one string.* **A negative string search bounds where a literal is, not
where the behaviour is** -- and I turned the first into the second.

So the native reader is **not** behind the virtualiser. `EndfieldBase.dll` (79% `.tvm0`
at 7.60) and `HGP.dll` (92% at 7.56) are packed and stay unreadable, but they are not
where this code lives. **The route is open, via `UnityPlayer.dll` and the
`UnityEngine.HyperGryph.Streaming` namespace.**

#### THE NEW SOURCE: `UnityEngine.HyperGryph.Streaming`

35 types in the IL2CPP metadata, engine-level rather than game-level, including the enums
a chunk record would plausibly reference:

| enum | members |
| --- | --- |
| `StreamingLayer` | Default, Persistent, HLOD0, HLOD1, HLOD2, Collider, Tiny, Water, Lighting, Audio, RendererWithCollider, Count |
| `ProxyEntityType` | IrradianceVolume, AudioVolume, AudioEmitter, AudioRoom, TerrainSurfaceTypeData, AudioPortal, SOCChunk, GrassGrid, GpuClothGroup, TreeGrid, GPUParticleSystem, TypeCount |
| `StreamingComponentType` | 45 members |
| `StreamingMode` | Stream, Pause, Teleport, Unload, TeleportUnload, TeleportLoad |
| `StreamingStatus` | Idle, Loading, Unloading, Empty |

***And `ProxyEntityType` is refused as the slot-5 kind code, despite reading perfectly.***
Its members are exactly the things a chunk places, which is the most seductive name match
in this whole family. It has an external anchor, so it is testable: the `iv` block
independently gives each level's IrradianceVolume count. Scoring **all 28** kind codes:

| | result |
| --- | --- |
| codes whose per-level total equals the IV count | **0 of 28, on 0 of 88 levels** |
| **positive control**: levels where *some* code equals the IV count | **17 of 88** -- the test can fire |
| slot-5 entries per level | median **4,861**, max 535,440 |
| IrradianceVolumes per level | median **1**, max 14 |

Three orders of magnitude apart. **Slot 5 is not a placement list at all**, whatever its
codes mean. *The positive control is what makes the zero worth anything: without it, a
test that cannot fire and a hypothesis that is false look identical.*

#### WHAT THE ENGINE'S OWN ASSERTS AND LOGS SAY -- AND WHAT THE DATA DOES WITH IT

`UnityPlayer.dll` keeps its `HG_ALWAYS_ASSERT` expression text and log formats, which is
vocabulary straight from the authors:

```
fbMonoEntityData->componentDataList()->Get(0)->type() == kComponentTypeTransform
!fbMonoEntityData->componentDataList()->empty()
componentType != kComponentTypeNone        entityType != kECSEntityTypeCount
entityType != kProxyEntityTypeCount        transition < EntityTransition::Count

"Missing chunk file at %d,%d,%d, lod %d"   "Unexpected chunk status %u when load"
"Unsupported Proxy entity type %u to ConvertFrom"   "[Streaming] Failed to load %s"
```

The first line is **literal FlatBuffers accessor code**: a table `MonoEntityData` with a
`componentDataList()` vector whose elements carry a `type()`, and element 0 is always a
Transform. Three bind functions sit beside it -- `BindMonoComponentConvertFuncFromScript`
(`StreamingComponentType`), `BindProxyEntityConvertFuncFromScript` (`ProxyEntityType`),
`BindECSEntityConvertFuncFromScript` (`ECSEntityType`) -- **three entity categories
against the root's three vector slots.** That is the same matching-counts shape already
refused twice in this family, so it is left as a lead, not a conclusion.

***Two readings this vocabulary suggests, both refused by the bytes.***

**`componentDataList` is not slot 5.** The assert predicts element 0 has one fixed type.
Across all 26,372 files, slot-5 element 0 carries **15 distinct kind codes**, the most
common covering 66%. Not a constant, so this vector is not that one.

**The filename's fourth field is not a lod.** `Missing chunk file at %d,%d,%d, lod %d`
invites reading `InitChunkData_<x>_<y>_<z>_<w>` as x/y/z/lod. The distribution says
otherwise: `w` is **0 in 26,070 of 26,372** files, and where it is not it takes values
like **587717614** and **293885694** -- confined entirely to **one level, `map02`**
(302 files). A lod index does not look like that. *A log format string names the
engine's addressing, not necessarily the filename's.*

##### A refinement to the StreamingChunkInfo join

The third field *does* vary -- `z` runs 0..7+ -- and **7 of 88 levels hold more chunk
files than distinct `(x, y)` pairs**: `map01` has 7,599 files over 6,028 columns, `map02`
1,952 over 1,229. So chunks are addressed by more than `(x, y)`.

This does not break the earlier 88-of-88 index result, which compared **sets** of
coordinates and so collapsed the `z` variants harmlessly -- but it does correct the
impression that index entries and chunk files stand 1:1. **The index carries one entry per
`(x, y)` column; the files are per `(x, y, z)`.** *The test was sound and its natural
reading was not, which is a failure mode worth naming: set equality proves set equality,
and nothing about multiplicity.*

#### SLOT 5's KIND CODES, IDENTIFIED: `StreamingLayer` AND `ECSEntityType`

Four independent lines agree, and each could have failed.

***1. Range exclusivity.*** Over **1,602,882** elements, `f2` takes `{0..10, 12, 13}`:

| candidate enum | verdict for `f2` |
| --- | --- |
| `StreamingLayer` (11) | **out of range** -- 12, 13 |
| `ProxyEntityType` (11) | **out of range** -- 12, 13 |
| **`ECSEntityType` (14)** | **in range, 13 of 14 values used (93%)** |
| `StreamingComponentType` (44) | in range but only 30% used |

*Two candidates are excluded outright by two values.* `StreamingComponentType` survives
the range test and fails the coverage one: 30 of its 44 members never appearing across 1.6
million elements is not what a live discriminator looks like. `ECSEntityType` uses every
value but index 11 (`TerrainSplineDecal`), and its maximum is exactly `TypeCount - 1`.

`f1` takes `0..10` -- exactly 100% of `StreamingLayer`'s eleven, and of
`ProxyEntityType`'s eleven.

***2. A cross-block join that had to be earned.*** The `terrain` block gives terrain
presence per level independently. Scoring every `(f1, f2)` pair over 38 terrain levels and
50 without:

| pair | terrain | non-terrain | separation |
| --- | --- | --- | --- |
| **`(5, 7)`** | **37/38** | **0/50** | **+97.37%** |
| `(0, 4)` | 38/38 | 0/50 | +100.00% |
| everything else | -- | -- | +52% or below, most near 0 |

Under the reading, `(5, 7)` is **`StreamingLayer.Collider` + `ECSEntityType.TerrainCollider`**
-- a terrain collider on the collider layer, present in essentially every terrain level and
**no** level without terrain. *The name and the statistic were derived from different
files and agree.*

***3. An earlier negative becomes positive evidence.*** `ProxyEntityType` is the rival for
`f1`, and it was already refused: if `f1` were `ProxyEntityType`, then `f1 == 0` would be
`IrradianceVolume` and its per-level count had to equal the `iv` block's -- it matched on
**0 of 88 levels**, with a positive control confirming the test could fire. Under
`StreamingLayer`, `f1 == 0` is `Default`, which makes no such prediction. **The failed test
does not merely leave the question open; it discriminates between the two survivors.**

***4. Absence behaves like a default.*** `f2` is *absent* on 405,611 elements, and
FlatBuffers omits any field equal to its default. `ECSEntityType.Render` is 0 -- the
commonest thing in a chunk -- so the commonest record carries no type word at all.

***5. The enum values are now verified, not assumed.*** The mapping above originally read
member values off **declaration order**, which is a guess. IL2CPP stores the real values in
`fieldDefaultValues` (127,853 records) indexing `fieldAndParameterDefaultValueData`, and
decoding them confirms it:

| enum | values | terminator | valid range |
| --- | --- | --- | --- |
| `StreamingLayer` | **sequential 0..11** | `Count` = 11 | **0..10** |
| `ECSEntityType` | **sequential 0..14** | `TypeCount` = 14 | **0..13** |
| `ProxyEntityType` | sequential 0..11 | `TypeCount` = 11 | 0..10 |
| `StreamingComponentType` | **NOT sequential** -- max value **128** | `Count` = 43 | -- |

`ECSEntityType`'s valid range ends at exactly **13**, which is exactly `f2`'s observed
maximum. And the fourth candidate is now excluded on a second, stronger ground: `f2`'s
values are **contiguous 0..13**, which a non-sequential enum carrying a 128 does not
produce. *The coverage argument against it was suggestive; this one is structural.*

**A read that failed usefully.** The values are stored as **single bytes**, and reading
them as int32 produced `0x03020100`, `0x04030201`, `0x05040302` -- consecutive overlapping
windows. *That the garbage was orderly is what identified the stride:* entries one byte
apart, values 0, 1, 2, 3. A wrong read that returns noise tells you nothing; a wrong read
that returns a pattern tells you the layout.

***6. The caveat is resolved, and the mapping is confirmed far harder than before.*** The
worry was `(0, 4)`, which separates terrain levels at 100% while reading as
`Default + SphereCollider`. Presence separation is a weak instrument -- it asks only
*whether* a pair occurs. Correlating **counts** against each level's terrain-file count,
over the 38 terrain levels, separates them completely:

| pair | reading | total | corr. with terrain files |
| --- | --- | --- | --- |
| **`(5, 7)`** | **Collider + TerrainCollider** | 5,406 | **+1.000** |
| `(0, 7)` | Default + TerrainCollider | 4,590 | +0.956 |
| `(0, 4)` | Default + SphereCollider | 5,312 | **+0.728** |
| `(3, 9)` | -- | 103,748 | +0.118 |
| `(1, 9)` | -- | 123,540 | -0.030 |

**`(5, 7)` is perfectly linear in terrain extent across all 38 levels.** A count of
"terrain colliders on the collider layer" rising exactly in step with the number of terrain
files is what the two enum names jointly predict, and nothing else in the census behaves
that way. *This is the confirmation the presence test could not give.*

**And `(0, 4)` behaves unlike a terrain record.** At +0.728 it is plainly correlated -- but
the two records that genuinely name terrain sit at +1.000 and +0.956, and the difference is
not marginal. `(0, 4)` is common on outdoor levels without scaling with terrain, which is
exactly what "sphere colliders are more numerous outdoors" predicts and what
"sphere colliders *are* a terrain feature" does not. *The pair that fit the statistic
without fitting the name turns out to fit a weaker statistic, which is the name's
prediction after all.*

#### SLOT 7's DESCRIPTOR: THREE CANDIDATES REFUSED, AND MY OWN "6-VALUED" CORRECTED

The method that worked on slot 5 does not transfer, and saying so precisely is the result.

***The category is 7-valued, not 6.*** Corpus-wide the one-hot invariant **strengthens** --
byte 1 is a single set bit in **12,859 of 12,859** non-zero descriptors, no exceptions --
but `k` runs **0..6**, with `k = 6` present on 2 descriptors (0.016%). **The earlier
"6-valued" figure was an artefact of the single-digit coordinate slice.** Two descriptors
out of 12,859 is thin, and it is enough: a range claim is settled by its rarest member.

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| descriptors | 2,956 | 1,980 | **3,305** | 2,250 | 1,536 | 830 | **2** |

***Refused 1 -- a mask over `ECSEntityType`.*** The word is 14 bits wide and
`ECSEntityType` has exactly 14 values, which is the same coincidence that identified slot
5's `f2`. Testing it *within* each file, against the types that chunk's slot 5 actually
contains:

| | share of 18,391 descriptors |
| --- | --- |
| mask is a subset of the chunk's types | 41.42% |
| **control: the mask shifted right** | **45.37%** |
| control: the mask shifted left | 37.37% |
| control: subset of a *different* chunk's types | 40.53% |

**A control beat the claim.** The same reasoning that succeeded one slot over fails here,
and it fails against three controls at once.

***Refused 2 -- `ECSExplicitEntityType` and `StreamingMode`.*** Both have exactly 6
members, which is why the corrected range matters: `k` reaches **6**, so seven values, and
both are excluded outright.

***Refused 3 -- a cross-slot join on the one name both enums share.***
`HGDecalProjector` appears as `ECSExplicitEntityType` position 5 *and* `ECSEntityType`
value 10, so `k = 5` records should co-occur with slot-5 `f2 = 10`. They do, at 65.88% --
and `k = 4` does at 61.27%, `k = 1` at 59.49%, `k = 2` at 27.43%. *Highest is not
isolated*, and a spread of 27-66% across the categories discriminates nothing.

**What the descriptor is made of, precisely.** The low byte takes only four values --
`0xFF` (12,638), `0x00` (5,459), `0xBF` (283), `0x3F` (11) -- so only bits 6 and 7 vary
there, while bits 8..14 carry the one-hot category. *The structure is fully framed and the
referent is unidentified*, which is a different and more useful state than either half
alone.

##### Three further constraints, each narrowing what the category can be

***It is not an enum in this vocabulary.*** Searching every enum in the HyperGryph,
Streaming and Beyond namespaces whose values are verified sequential from
`fieldDefaultValues`, exactly **one** has seven members -- `AudioDebugGizmosType`, a debug
gizmo list. There is no seven-valued streaming enum for `k` to be.

***It is orthogonal to level content.*** The terrain anchor that identified slot 5's `f2`
gives **nothing** here: every category appears in nearly every level, terrain or not.

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| terrain-vs-not separation | +0.00% | -0.63% | -0.63% | -0.63% | -5.79% | +9.26% | +5.26% |

**A category present in all 88 levels in similar proportion is a per-object attribute, not
a content kind** -- which rules out the whole family of readings that name *what* is
placed, and is why `ProxyEntityType`-style guesses were never going to land.

***The ordering refusal holds on the full corpus.*** Re-run with the corrected seven-value
range (the earlier run used the slice that misreported it as six), the median geometric
extent per category is **38.98, 28.45, 97.74, 40.89, 38.05, 33.77, 31.51** -- neither
increasing nor decreasing. *Re-testing was justified because the input had been shown
unrepresentative, not because the answer was unwelcome.*

**Two facts left for the next attempt.** `k = 2` is the outlier on every measure -- the
largest population (3,305) and a median extent **2.5x** every other category. And the two
varying low bits are not independent of the category: among populated descriptors the
value `0xBF` occurs **only** with `k = 0`, 221 times in 2,956, with every other category
exclusively `0xFF`.

***A degenerate fit, caught by fitting four rivals at once.*** `s4 == 24 + 24*n7` scores
**100.00%** on the Streaming family, which reads like a decoded record stride -- until the
rivals are run beside it. `24 + 32*n7`, `24 + 40*n7` and `24 + 44*n7` **all score
100.00% too**, because Streaming's `n7` is *always* zero and every candidate collapses to
the constant 24. On the Init family all four score the same 46.47% -- again exactly the
`n7 == 0` subset. **The stride is unidentified, and the way to know that was to make the
rivals compete rather than to check one and stop.** Init's actual `s4` grows far faster
than linearly in `n7` (`n7=1` spans 188 distinct values; `n7=8` reaches 81,200), so it is
a byte size over variable-length records, not a count times a stride.

#### THE PAIR SPLITS SLOT 5's FIELDS INTO INVARIANT AND VARYING -- WHICH ONE FAMILY CANNOT SHOW

Comparing each chunk's two files element by element, over **217,620 elements** in 7,433
pairs. The element counts match in **every** pair (0 differ), and **not one element is
byte-identical**:

| slot-5 field | agrees across the pair |
| --- | --- |
| **field 1** | **58,141 of 58,141 = 100.0%** |
| **field 2** | **100,822 of 100,822 = 100.0%** |
| field 4 | 88.2% |
| field 3 | 9.7% |
| field 0 | 4.2% |
| **field 5** | **0 of 81,172 = 0.0%** |

*Two fields never disagree and one never agrees.* Fields 1 and 2 also carry the fewest
distinct values in the corpus -- 5 and 11 -- so they read as a **kind or type code that
identifies the same entry in both files**, while 0, 3 and 5 carry per-file quantities.
**This partition is invisible from either family alone**: within `InitChunkData` all six
fields look alike, small integers with few distinct values. It took the pairing to
separate them.

Element *vtable layouts* match in only 2,930 of 7,433 pairs, so some of these fields are
optional and present in one file but not the other.

***What this does not establish.*** The natural follow-up -- that fields 0, 3 and 5 are
byte sizes summing to one of the scalars -- **fails**. Summing each across a chunk's
entries and testing against `s2`, `s3`, `s4` and the buffer length gives at best 16.70%,
and the one suggestive hit, `sum(field5) == s4 - 24` at **46.47%**, lands on **3,454**
files in *both* families -- the same recurring empty-chunk subset that every degenerate
fit in this family has produced. *When a number that has already been identified as the
degenerate subset turns up as a match rate, it is the subset talking, not the hypothesis.*
The scalars stay unexplained.

#### THE KIND CODES ARE COUPLED, BUT NOT A SECTION DIRECTORY

Fields 1 and 2 -- the two that never disagree across the pair -- take
`{5, 6, 8, 9, 10}` and `{1..10, 12}`. Independent codes would give 55 combinations;
**only 19 occur**, so the two are coupled and carry less information than their ranges
suggest. Over **629,607** slot-5 elements:

| reading | result |
| --- | --- |
| a directory keyed by kind (each kind once per chunk) | **refused** -- 3,410 of 7,433 files repeat a `(f1, f2)` |
| a sort key | **refused** -- field 2 is unordered in 2,226 of 7,433 files |
| distinct `(f1, f2)` combinations | 19 of a possible 55 |

***A test that cannot decide, recorded so it is not run again.*** The remaining reading is
that `(f1, f2)` is a **union tag** selecting a record type, which predicts one vtable
layout per kind. The census gives 19 kinds against 16 layouts, with only **6 of 19** kinds
showing a single layout -- which looks like a refutation and **is not one**. *FlatBuffers
omits any field whose value equals its default*, so a single type legitimately produces
several layouts depending on which fields happen to be defaulted. Layout spread within a
kind is uninformative here, in both directions. **The union reading is neither supported
nor refused by this evidence, and re-running it will not change that** -- separating the
cases needs the schema, not the bytes.

**Where this family stands.** Slots 5 and 6 are not unindexed for want of effort -- at
this `inputSetSha256` **slot 6 contains no variation to index against at all**, and slot
5's remaining questions are now pinned to a 19-value coupled code whose resolution needs
the schema. Further mining needs a different corpus, not a better test.

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
