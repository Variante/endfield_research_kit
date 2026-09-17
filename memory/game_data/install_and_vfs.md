# Where the installed data lives

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1 -- the outermost layer.** Before any format question, this is what the
installed client exposes: which VFS blocks exist, how big each one is, and which
maintained reader owns each payload family. Every other file assumes you know which
block its bytes came out of.

## The remaining VFS blocks, inventoried

Beyond `streaming` and `terrain`, the blocks hold: **`iv` 4.17 GB** (irradiance volumes;
`iv_N_N.bytes`, 92 `index.bytes`, a few `regionIv_room_*`), **`table`** 724 single-instance
config tables (`BuffTable`, `SkillConditionTable`, `CharacterConst`, ...), **`json-data`** ~1,264
name shapes of plain JSON, **`extend-data`** just three files
(`CompressData.bin`, `FacBoneTRS.bin`, `StringPathHash.bin`, 176 MB together), and
**`bundle-manifest`** a single 50 MB `manifest.hgmmap`. *`iv` is by a wide margin the largest
and was entirely uncharacterised.*

## Payload families, and the reader each one routes to


The maintained evidence index in the AnimeStudio workflow routes each family to
its reader, fixtures, and generated corpus report. Durable current conclusions:

- DynamicStreaming is a generated FlatBuffers family with validated version,
  grid, string, resource/state, and area accessors. The deeper meaning of its
  DataMask and several record fields remains unresolved. The maintained
  `stream_area` gate rejoins current `FBStreamArea.bytes` files to the
  authenticated outer VFS ledger and requires the final vector to reach payload
  EOF; its six vector widths and one inline root field are framing evidence,
  not field names or runtime semantics. Current corpus details are in
  [`dynamic_stream_area_current_latest.md`](../../reports/animestudio/dynamic_stream_area_current_latest.md).
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

## Reading VFS logical files: three things that look like corruption and are not

- **A raw span read is only valid for `encrypted=False` rows.** The audio probe's
  `read_logical` seeks to a ledger row's offset, reads its length and checks the
  MD5. That works because every audio block is `encrypted=False`. Five block types
  are `encrypted=True` -- `BundleManifest`, `IFixPatchOut`, `JsonData`, `Lua` and
  `Table` -- and on those the same read produces a confident MD5 mismatch that
  looks exactly like a corrupt or stale file.
- **A chunk's filename is not the MD5 of its raw bytes.** `fileChunkMd5...` is not
  the raw-byte digest: checked across six chunks, including ones whose files
  verify normally, the filename never equals the raw MD5. So "filename does not
  match its hash" is **not** evidence that a chunk changed on disk. That control
  is cheap and worth running before concluding anything about a mismatch.
- **`manifest.hgmmap` is a Brotli stream**, so XOR-decrypting it yields no UTF-16
  and looks like a failed decrypt. `scripts/game_data/bundle_manifest.py` already
  frames it end to end -- headers, three fixed-width row regions, a variable region
  with counted UTF-16 fragments. Do not re-derive it.
- **There is no Python VFS decryption path, by design.** Encrypted blocks are
  decrypted by the AnimeStudio CLI during `dump`, and Python reads the structured
  output; that is why no script takes an `ivSeed`. Hand-rolling the XOR with the
  ledger's seed does not reproduce the file -- I tried, and the result is not a
  Brotli stream.
- So **naming bundles is not the cheap step I called it.** The current structured
  export covers only `table` and `json-data`, so the decrypted manifest is not on
  disk. The recipe is: dump with `--block-type BundleManifest` (the CLI's `list`
  confirms that name), then feed the decrypted `.hgmmap` to
  `scripts/game_data/bundle_manifest.py`, then join its names to the CAB-to-bundle
  relation above. The join is cheap; producing its input is an export run.
- All three cost time here because a wrong tool produced a plausible failure rather
  than an obvious one. **When a read fails, check whether the reader was valid for
  that row before believing the bytes are wrong.**
