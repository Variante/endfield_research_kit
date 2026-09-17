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
