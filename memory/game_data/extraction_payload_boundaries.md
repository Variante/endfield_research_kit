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
DummyDll population and setter declarations do not fill these gaps. Historical
residual JsonData censuses supply family leads, not current denominators
without a ledger rejoin. SkillData still lacks whole-object cursor proof. NPC
MontageNew now has a current ledger/stream gate in
`memorypack.npc_montage_corpus`; it binds each current identity by path,
length, and logical MD5 and records exact EOF only for supported frames in
`reports/animestudio/npc_montage_current_latest.{json,md}`. UTF-8 strings and
fixed record bodies remain anonymous, and field meaning or runtime use is not

## The Streaming and chunk families, framed to their native consumer

inferred. StreamingChunkInfo exact-frames the anonymous
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

## What each corpus gate proves

One paragraph per maintained gate: what it reauthenticates, what it writes, and
what it explicitly leaves unresolved. The commands themselves are in
[`../../scripts/README.md`](../../scripts/README.md); this is the boundary each
one establishes.

`streaming_corpus` reauthenticates block-15 rows from that ledger and writes
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
`streaming_marker17_corpus` reuses the source-bound marker17 directory from that
report, reauthenticates every listed physical range and refines the native-gated
tag5 counted arrays and fixed tag1/4/6 profiles with `streaming_marker17`;
unknown keys remain explicitly opaque/unsupported. It writes
`reports/animestudio/streaming_marker17_bodies_latest.json` plus `.md`.
Partial `--max-files` probes require explicit output paths and are not eligible
as complete-corpus evidence. Record fields and runtime selection remain unknown.
`streaming_marker13_corpus` rereads the complete block-15 ledger through the
source-bound Streaming parser, joins marker13 references to independently
certified structural neighbours, and tests native-gated explicit-selector9 and
byte-proven absent-selector profiles. `streaming_pairs` binds paired file
identities, complete ordered vectors and exact serialized ordinals; absence is
never rewritten to a stored zero. Its inventory separates structure, read windows,
physical gaps and opaque remainder; a physical gap is not a serialized sizeof or native EOF.
Outputs are `reports/animestudio/streaming_marker13_latest.json`/`.md` and
`streaming_marker13_inventory_latest.jsonl.gz`; partial outputs must stay in
`tmp/` or `scratch/`. The summary authenticates the inventory's content/hash.
`streaming_marker2_directory` owns the complete nested reference/occupancy
replay. `streaming_marker2_corpus` gates the separate selector6 finite-gap
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
CLI and parser provenance at both ends. Historical census rebinding is rejected.
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
coverage belongs in that report; nested strings, scalars and fixed record bodies
remain anonymous.
`memorypack.corpus_gate` owns shared outer-ledger, overlay, fingerprint and output
guards. `memorypack.buff_corpus` joins the full current BuffData stream and retains
every filename-string anchor and reader-accepted suffix candidate, without
promoting legacy field labels or internal opaque bodies. Run
`python -m scripts.game_data.memorypack.buff_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256 --output-json reports/animestudio/buffdata_current_latest.json --output-md reports/animestudio/buffdata_current_latest.md`.
The report partitions selected files into successful candidate framing, failed
reader execution and unsupported shapes; uniqueness is only within that reader.
Each accepted BuffData suffix also records a hard-bounded prefix-reader stop and
remaining gap, with prefix support counted separately from suffix acceptance.
The report binds its parser cursor and closed action ranges to current input-set
and logical-file identities, and keeps exact action closures, structural
prefixes, opaque bytes, rejected anchors and unsupported results separate.
`memorypack.buff_actions` owns the independent anonymous event-prefix grammar;
its per-candidate scalar/record spans and explicit opaque remainder have a separate
success/failed/unsupported/ambiguous census. Malformed prefixes fail the corpus
gate even if the legacy suffix candidate succeeds; unknown unions are not aliased.
`currentRootContinuation` consumes selected root members 2-6 only after a
supported first collection, beginning at `currentEventPrefix.consumedEnd`.
Its independent status and ranges retain the remaining physical bytes as opaque;
malformed continuation data also fails publication. This does not join the
filename suffix to a proven root field or establish whole-schema EOF.
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


`python -m scripts.game_data.il2cpp_context_audit` emits an exact-build native
generic-instantiation audit as JSON on stdout. `il2cpp_context` owns bounded
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
