# AnimeStudio recovery

AnimeStudio is the maintained extraction boundary between installed Endfield
data and the repository's builders. Production users should enter through the
root wrappers; direct CLI commands are for focused recovery and diagnostics.

## Ownership

| Layer | Owner |
| --- | --- |
| Installed VFS catalog, overlay, block reads, Unity objects, conversion | `tools/AnimeStudio/` |
| Installed-game orchestration, scope, worker isolation, provenance | `scripts/export_full_from_game.py` |
| Story/Text, Map, Characters, Gameplay, Audio, Assets publication | owning Python builders under `scripts/` |
| Stable CLI mechanics and VFS evidence index | `.codex/skills/animestudio-workflow/references/animestudio.md` |
| Per-build counts, hashes, failures, and audits | `reports/animestudio/` and `reports/export/` |

Do not move page semantics into AnimeStudio. Improve AnimeStudio when extraction
omits or misdecodes source bytes; improve the owning builder when extracted
evidence needs a domain join or presentation contract.

## Production export

| Goal | Command | AnimeStudio scope |
| --- | --- | --- |
| Refresh Story/Text | `.\export.bat --from-game` | structured focused dump, maps, broad Story JSON |
| Refresh Story and assets together | `.\export.bat --from-game --with-assets` | one combined Story/asset pass |
| Apply a local client delta without publishing Updates | `.\export.bat --changed-only` | changed focused VFS files, reuse bundle-derived outputs, all WebUI builders |
| Refresh assets and CN audio only | `.\export_assets.bat --from-game` | skip structured Story, asset maps/conversion/JSON, VFS index, audio |

The focused structured dump includes Table, JsonData, and video. It excludes raw
bundles, audio packages, world streaming, irradiance, ExtendData, patch data,
and Lua. `--structured-dump-mode default` additionally includes the maintained
Terrain height subset; `debug` is for broad diagnosis.

Changed-only export keeps a private, export-root-local logical-file snapshot
and compares decoded FileDataMd5 plus length/type/path/encryption identity. It
uses exact full-path dump filters for changed structured files, validates the
staged output set, and handles deletions explicitly. The first post-update run
may seed the old side only from a certified VFS ledger whose input set and
physical inventory bind to the previous export summary; otherwise it fails
closed and requires a full export. Bundle-derived maps, objects, assets, and
audio are refreshed broadly because a changed bundle does not prove safe
per-output ownership. The snapshot commits only after the complete WebUI
pipeline succeeds, and this local mode never reads or writes Updates state.

Asset modes are intentionally ordered:

- `focused`: WebUI-referenced Texture2D media only.
- `default`: WebUI-facing image/model/material/animation outputs and audio
  callback ownership inputs.
- `debug`: broad conversion and JSON types for investigation.

After extraction, page builders consume `export_full/`; see
[`webui_recovery.md`](webui_recovery.md) for the complete publication flow.

## Build and direct CLI use

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\setup_vgmstream.bat
.\scripts\animestudio\rebuild.bat -Target CLI
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Expected executable:

```text
tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe
```

Use direct `dump`, `audio`, `stream`, `vfs-index`, or `list` only for a bounded
probe. Inspect each subcommand's `--help`; do not maintain another option
catalog here. `dump`, `audio`, `stream`, and `vfs-index` support the sibling
root fallback. `dump`, `stream`, and `vfs-index` support repeated block-type and
file-regex filters. Audio defaults to direct lossless FLAC: the CLI pipes PCM
from the pinned repo-local vgmstream decoder into its in-process FLAC encoder,
without an intermediate WAV file or `ffmpeg`.

## Export model and provenance

Keep these states distinct: indexed, loaded, exported, partial, and certified
clean. A zero exit code or wrapper stage success does not certify every object.

Every claim keeps its source root and physical identity. Unity references use
source/CAB plus PathID; a PathID or normalized name alone is not globally
unique. Persistent overlays StreamingAssets while retaining fallback chunk
resolution. Missing dependencies, ambiguous external targets, malformed
objects, and unsupported schemas must remain explicit.

The optional object index publishes compressed object/schema streams plus a
last-written terminal `summary.json`. Consumers fail closed on missing or
incomplete summaries, stale source or CLI provenance, hash mismatch, duplicate
physical identity, or ambiguous external CAB/PathID targets. Scene hierarchy
and world positions are exact only when their resolution status says so.

Use the generated export summary first when diagnosing a run:

```text
reports/export/export_full_summary.md
reports/export/runs/<timestamp>/
reports/export/benchmarks/
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/
```

An `Export <Type>:<Name> error` may be object-local even when the process
continues. A nonzero subprocess return code fails the wrapper. Metadata-only or
`$partial` output is useful evidence, not a completeness claim.

## Scheduling and memory

The measured default is `--animestudio-type-job-mode auto`:

- map-filtered conversion types may use balanced shards;
- broad Story JSON types run sequentially in isolated processes;
- MonoBehaviour and PlayableDirector remain broad;
- JSON export is not sharded or broadly concurrent.

Add a type to map filtering only after broad and filtered outputs match
byte-for-byte. Equal object counts are insufficient because skipped bundles can
remove script definitions or external PPtr targets. Lower `--asset-jobs` before
changing shard counts or architecture when memory is constrained.

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
- SkillData historical export-backed censuses cannot establish current VFS
  coverage by accepting a newer boundary report. Its maintained
  `memorypack.skill_corpus` gate starts from the authenticated outer ledger and
  current decrypted VFS stream bytes, checks the complete identity set and
  source/overlay/tool provenance at both ends, and records logical hashes.
  The anonymous terminal reader enumerates direct-counted and wrapped branches
  independently, including empty wrappers; unknown record member counts fail
  closed. A unique EOF candidate is unique only within the supported grammar,
  not a proven preceding cursor. Full record ranges, ambiguous candidates and
  opaque gaps remain distinct from whole-file ownership. Current coverage and
  full candidate inventories belong to
  `reports/animestudio/skilldata_current_latest.json` and its Markdown companion;
  the historical two-ambiguity census is superseded, not a current baseline.
  BuffData needs a
  provenance-matched census before reporting current coverage and has a bounded
  anonymous member-18 stacking-action
  reader; its fixed extent and terminal markers can be exact without claiming
  semantic field order, while changed or unsupported rows remain explicit.
  LevelScriptData and LevelData expose partial top-level frames only when their
  independently parsed prefix/suffix regions are unique and
  EOF-exact; nonempty/null LevelScript action maps may also expose only an
  anonymous first-list/record-envelope or raw-null prefix while all later
  union data stays opaque. One high-coverage first-record variant has a bounded
  sequential body reader, but later records/lists remain unowned. AnimationConfig likewise separates
  a proven anonymous prefix (and a small exact whole-frame variant) from an
  opaque remainder. Keep structural framing distinct from semantic schema
  ownership until formatter IL or a bounded deserialization trace closes the
  complete named cursor.
  Current registration locates real SkillData formatter/wrapper bodies and
  their relative five-operation terminal read sequence, not a file offset.
  The Core type used by `ReadValue<T>` differs from the generated wrapper's
  `Register<T>` type; a generated wrapped reader alone does not prove the
  adapter or active formatter. A separately gated immediate-registration site
  now joins the Core key to `GenericMemoryPackFormatter` with ordered arguments
  Core and `Beyond_Gameplay_Core_GameplayTagListForMemoryPack`: its type carrier
  and constructor MethodSpec share the same registered class instantiation.
  This proves static adapter identity and a conditional registration callsite,
  not completed allocation ABI, executed registration or active Deserialize
  dispatch. Registration and lookup independently share one RIP-relative cell
  and the same class/static-storage dereferences. The lookup's matched node
  supplies its returned value, but misses can invoke callbacks, retry or construct
  alternatives; this does not fix live contents or replacement history. The separate
  generic serializer's pointer/length-word carrier is not yet joined to this
  formatter or authenticated VFS allocation. Keep both terminal candidates;
  complete nested cursors and EOF remain unresolved. Native pins and reviewed
  limits belong to `reports/animestudio/skilldata_native_review_latest.json`;
  PE reads must remain within raw section extents: virtual-only globals have
  no disk value and need runtime-initialization evidence, not adjacent file bytes.
  Generic-instantiation registration is a pointer array, not inline records;
  preserve the record's padding separately from its u32 argument count. The
  maintained `scripts.game_data.il2cpp_context_audit` validates current native
  inputs, every registered instance, and reciprocal open-parameter ownership.
  Its inventory is `reports/animestudio/il2cpp_context_current_latest.json`.
  The selected `GetFormatter<T>` parameter belongs to `ReadValue<T>`; a prior
  concrete-type probe was an indirection bug, not a runtime counterexample.
  This static join does not establish actual generic substitution or formatter
  selection; preserve both terminal candidates until those separate gates close.
  The native MVAR leaf reads a parameter ordinal and indexes the supplied
  method-inst vector. The gate checks that ordinal against the selected call's
  registered argument. Native normal-path stores now connect method records to
  their class, the metadata image-range directory, and a module selected by
  bytewise name comparison from the gated CodeRegistration. The static image
  partition must be complete and unambiguous; module names must be unique since
  the native loop continues after a match. This does not certify initialization
  execution, all cold paths, active formatter selection, or source/cursor/EOF.
  The selected call's on-disk usage cell also joins through the wrapper's guarded
  lazy initializer and tag-specific MethodSpec/triple resolver. This establishes
  the static initialization mechanism, not an observed live cell or cache entry.
  The open formatter-check carrier independently joins the same MVAR through its
  class-inst pointer; reject duplicate pointer identities and token ranges.
  The native method-pointer resolver retries a missed original-context lookup
  with transformed argument vectors. Its direct class-tag branch uses one shared
  global carrier plus the type-record offset for both adapter arguments. The
  normal producer's image/namespace/name lookup and class copy connect this to
  the unique `mscorlib.dll / System.Object` byval record; its bytes match both
  arguments of the static object/object candidate. Actual initialization, cache
  population and interned pointer identity remain unobserved: byte equality does
  not select a particular shared Deserialize body.
  A separately gated initializer seeds the generic-instantiation cache from the
  selected registration's pointer table; insertion and lookup share the same
  storage global. This conditional path is not an observation of cache contents.
  The gated object-tag comparator and hash use only the tag and one flag bit,
  not record addresses; enumerate every registered pair matching that projection.
  A unique static match still does not prove the returned runtime instance.
  Matching MethodSpecs join bounded method/invoker index triples and pointer
  slots; the no-adjustor sentinel reuses the ordinary method pointer. Other
  adjustors need an independently bounded table and remain unsupported here.
  Keep RGCTX range-relative slots distinct from module entry indices. The adapter
  class-token range connects its selected slot to a reciprocal second type
  parameter (VAR), not an unrelated concrete type. The class initializer's
  conditional path converts 16-byte definitions to eight-byte runtime slots
  using the class generic context; static definitions are not observed slots.
  The reviewed MethodInfo construction path stores the original instantiated
  class separately from resolved shared-code pointers. Do not substitute the
  shared body candidate's object/object arguments for the companion's class
  context; actual cache contents and invocation still need independent evidence.
  Nested class slots independently link MethodSpecs for the non-null adapter,
  formatter lookup and instance creation to reciprocal parameters of that same
  adapter type. Keep these static links separate from serialized read order.
  The generated wrapper reader conditionally forwards the same reader after a
  one-byte fast-path header to an independently joined `ReadPackable<List<...>>`
  usage/MethodSpec/type carrier. This nested body is another provider/dispatch
  layer, not the list element reader. Cold advance normally returns true, resets
  the segment counter and accumulates the request; ensure can replace the cursor
  with an existing or copied segment. Pointer deltas cannot certify source offsets.
  The 24-byte descriptor has a conditional same-endpoint position-difference
  length path. Independently token-joined constructors accept that descriptor or
  a 16-byte pointer/length carrier and initialize total/remaining state and zero
  consumption. Native getters identify consumed and total-minus-consumed roles;
  reviewed caller paths return consumption but do not themselves compare EOF.
  The token-joined object-return overload discards this count. Selected async
  paths either discard it or forward it to another operation, not an EOF test.
  These general serializer paths do not establish SkillData entry selection.
  Exact Core.SkillData type arguments also join ResourceManager MethodSpecs;
  their generic definition module slots are null. Separately enumerated
  same-definition Object MethodSpecs supply shared-code candidates, not observed
  sharing selection or invocation. Never confuse the same-named nested AI type
  with the Core type, or substitute a shared body's arguments for live context.
  A downstream native carrier wrapper forwards a reconstructed pointer/length
  carrier to an inlined reader-state builder. Conditional dispatch uses that
  state and an output slot; its returned consumption is discarded by the wrapper.
  This corroborates the non-EOF boundary, not an authenticated file receipt.
  The manager entry's declared input independently joins `System.IO.Stream`.
  Native slot addressing connects its length calls and buffer-fill slot to the
  metadata virtual slots for `get_Length` and `Read`. Both allocation branches
  perform one `Read` and discard its returned count before parsing the requested
  carrier extent. Repeated length results also undergo unchecked 32-bit narrowing;
  no stability, allocation/filled-length equality or full-read guarantee follows.
  The normal VFS allocation usage, constructor token and Stream parent now join
  `VFSFileReadStream`. Its constructor copies a 32-byte descriptor and retains
  the inner stream. Normal getters expose a descriptor length word and inner
  position minus a descriptor base word. Read returns the inner stream's actual
  count after a request-limit branch and optional prefix transformation, without
  a full-fill loop. Normal inner-stream allocation joins `FileStream`; the two
  selected helpers sign-extend the descriptor offset and seek with numeric origin
  zero, but one requires a positive offset and the other any nonzero offset.
  They discard the seek result. The normal mode getter shifts a packed dword;
  its caller retains only eight bits, not the entire getter result. The relative
  path's normal chunk-name branch uses a descriptor integer as a container
  lookup key and copies a checked, indexed 16-byte result, not an inline hash
  from the descriptor's leading bytes. Negative keys/results divert through a
  helper; if it returns, the getter emits 16 zero bytes, not a proven exception.
  Do not conflate this native descriptor with the serialized BLC file record.
  The normal setter uses paired static containers: a lookup-hit integer or a
  count-difference candidate reaches the descriptor; the miss path supplies the
  integer and 16-byte input in opposite orders to two insertion helpers without
  checking their returns. Original usage cells join Dictionary `TryGetValue` and
  `set_Item` contexts with reversed Int32/UInt128 arguments, not the helper
  identities suggested by inlined call targets. This is a conditional producer
  path, not proof of successful insertion, reciprocal live contents or BLC MD5
  provenance. Preserve the distinct seek predicates; complete container
  mutation/initialization, alternate path branches, path encoding/root selection,
  constructor/seek internals, replacements and the descriptor-to-authenticated
  logical-file identity/hash remain unproved. This is not a runtime receipt.
  `ReadFromByteBuf` now connects a mutable ByteBufStream cursor/array carrier to
  the 16-byte lookup input and descriptor result on its normal path. Its initial
  skip adds two in 16 bits before sign extension. The selected little-endian
  eight-byte helper can return zero for insufficient length while the caller
  still advances; do not treat successful return as byte provenance or reuse
  this permissiveness in maintained parsers. The array's authenticated source,
  later version/flag branches and final cursor still require independent proof.
  Main-info construction now preserves the original array and supplied starting
  index in that carrier, shared by nested chunk/file loops. The main reader's
  pre-parse tail comparison is distinct from consumption: its normal final
  remainder calculation clamps nonpositive values to zero, and the selected
  legacy branch performs one extra integer read without a subsequent EOF
  equality check. A returned object therefore cannot certify full consumption.
  Its upstream block-group entry retains the original array through an in-place
  transform and forwards that same array to the main reader. The normal worker
  XORs input bytes with a state-buffer byte; its adapter aliases both arrays and
  offsets. Nonpositive counts return without validation. The transform offset
  and subsequent parse start are separate loads from the same static storage,
  not a demonstrated immutable value. Key/span/constructor ABI, state-block
  generation, complete cipher parity and replacement paths remain open; array
  aliasing alone is not a decryption or EOF proof. Both block-construction
  branches now retain the array returned by their normal file-helper path
  through that entry. Those helpers converge on `File.ReadAllBytes`, whose
  positive-length loop accumulates actual read counts and reduces remaining
  bytes; zero returns leave the normal loop for error helpers. Its array/offset/
  count overload uses slot 34, distinct from the previously reviewed slot 35.
  Its normal FileStream overload reaches MonoIO, then a PE import-name join to
  `ReadFile`; the supplied out DWORD, not the API boolean, supplies the read
  count. The error word is populated through `GetLastError` on the failure
  branch and selects count versus -1. Keep API status, error, byte count and
  accumulated count distinct. This static join does not prove live IAT contents,
  handle provenance or buffered-state invariants; full-fill remains conditional.
  The two file-helper checks copy a 32-byte/four-slot path carrier from distinct
  builders. Slot +8 comes from their respective getter; null/empty first input
  shifts the second candidate into +0x10 and leaves +0x18 zero. AppendPathInfo
  forwards the slots in order after null substitution. Its original AppendFormat
  MethodSpec has three ordered string arguments; shared-code type candidates
  cannot replace this companion. The temporary cursor and subsequent append
  count use two-byte units: append doubles count for copying but advances its
  cursor by the original count, writing a zero terminator only below capacity.
  The native tag-5 resolver independently connects selected first-slot loads to
  bounded literal-table/pool bytes: four brace/slash patterns are static format
  inputs, not executed output paths. The literal sweep validates every row while
  allowing shared pool ranges; it does not claim exclusive metadata coverage.
  The format-item helper and its separate cold fragment establish a local
  32-byte return: selector, optional bounded colon span, index after the closing
  brace and comma-derived numeric value. This cursor is not whole-format EOF;
  The character helper bounds the DWORD index against carrier length and reads
  two-byte elements. Literal construction independently joins ASCII widening,
  element-count forwarding and the same length/data offsets in the output carrier.
  Allocation/copy/capacity helpers, non-ASCII cold paths and complete arbitrary-input
  grammar remain open; this does not establish Unicode conversion parity.
  The normal streaming-path getter requests the exact Unity streaming-assets
  interface name through a cached indirect-call resolver and stores its return.
  This proves the static request, not the resolved implementation or directory;
  The resolver reads a runtime tree, can retry with a helper-transformed query,
  and returns a candidate value or zero on the final sentinel. A writer independently
  stores its second argument into the same candidate value slot; a separate initializer
  seeds a self-linked sentinel. Writer callers, insertion/query helpers, live contents
  and the Unity implementation join remain open; static producer code is not execution.
  Nested dispatch, capacity/copy helpers, getter values, final path/root,
  on-disk identity/hash, zero-length alternate behavior and concrete execution
  remain unresolved; neither four pointer slots nor getter names prove a path.
  Multi-segment conversion, the complete ResourceManager-to-reader path and authenticated input
  identity remain unresolved. No observed final cursor or terminal uniqueness
  follows from this conditional ABI.
  Preserve the open formatter-check carrier window's uninterpreted tail: its bytes do not certify a
  runtime allocation extent or select the returned formatter. Provider fallback
  includes a lazy callback path whose population remains a separate evidence gap.
  Saved corpus consumers must recheck live catalog, build, CLI, parser and chunk
  fingerprints at both ends; authenticating the report hash alone does not
  establish freshness after a tool rebuild. Reauthenticate affected bytes with
  the rebuilt tool rather than rewriting old provenance pins.
  DummyDll population and setter declarations do not fill these gaps. Historical
  residual JsonData censuses supply family leads, not current denominators
  without a ledger rejoin. SkillData still lacks whole-object cursor proof. The NPC
  Montage reader exact-frames all 3,631 current rows, including both non-empty
  counted collections and their nested member markers, while keeping UTF-8 and
  fixed record bodies anonymous. StreamingChunkInfo exact-frames the anonymous
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
  unresolved type boundary are owned by `game_data_recovery.md`; all other
  nested targets remain opaque. Marker 15 additionally has bounded uoffset
  targets, with widths unresolved and no target-byte ownership. Root fields
  6/7 retain paired-group, descriptor, and blob-length closure. Bytes outside
  the certified subgraphs stay opaque; no union, entity, component, matrix,
  descriptor, field name, or runtime meaning follows.
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

## DummyDll and MonoBehaviour schemas

```bat
python -m scripts.animestudio.generate_dummydll --dry-run
python -m scripts.animestudio.generate_dummydll --replace
python -m scripts.animestudio.generate_dummydll --status-only
```

DummyDll generation is tied to the exact installed `GameAssembly.dll` and
`global-metadata.dat`. The generator must uniquely recover registrations,
validate a complete staged managed image set, publish atomically, preserve the
previous set, and record provenance in `tools/DummyDll/generation.json`. It
must reject any type-population failure, required-image skip, and catastrophic
type/size regression by default, and must join every staged non-module TypeDef
to the selected metadata on assembly, token, and full name before publication.
Endfield Cpp2IL compatibility is maintained as source in
`Variante/Cpp2IL-Endfield` on `endfield/2022.0.7`; the generator consumes an
immutable release pinned by tag and commit instead of applying a local patch.
The checkout is tracked as the optional `tools/Cpp2IL-Endfield` submodule;
`setup.bat` does not initialize it, while the DummyDll generator initializes it
on demand for script-schema recovery. A pinned commit is insufficient by
itself: both preparation and validation also reject a foreign origin or tracked
local changes.
Never reuse registration addresses from another build.

Cpp2IL must attach a method shell and predeclare every method generic parameter
in metadata order before importing constraints, return types, or parameters.
Importing an MVAR-bearing return through the declaring type fails, while lazy
return-first parameter creation can silently reorder multi-generic signatures.
Commit global method maps only after signature construction succeeds and roll
back the shell plus newly registered parameters on failure.

The selected v29 build uses exact 92-byte TypeDef rows: the prefix is the stock
v29 layout, while one additional int32 occurs after the eight range-start
fields and before the ushort counts. Keep that slot semantically unnamed. The
image ranges, all eight start/count families, nested-child relationships, and
token sequences close exactly under this boundary; a retained-byref prefix
interpretation is disproven.

The safe TypeTree priority is `serialized-first`. Use `script-first` only for a
focused comparison. Missing, stale, malformed, or incomplete DummyDlls warn and
fall back without breaking a normal export. DummyDlls provide names,
inheritance, and possible field shapes—not method bodies or proof that a type
was emitted. Managed-reference registries and recovered semantic readers retain
their own exact-consumption and type gates.

## Shader recovery

AnimeStudio owns the maintained shader-container, bytecode-sidecar, metadata,
and SPIR-V readable-output path through the dependency-free
`AnimeStudio.ShaderRecovery` project. The former Ruri runtime/build dependency
is retired; keep historical local artifacts only as comparison provenance.

Do not remove that provenance until AnimeStudio-owned semantic fixtures cover
the high-value character, effect, deferred, shadow, and clearcoat cases and
verify bindings, constant buffers, entry points, I/O semantics, compilation,
and source hashes. Do not copy AGPL source. Any new translator dependency must
pass license and target-framework review for AnimeStudio's .NET targets.

## Change and verification workflow

1. Identify the smallest failing source, stage, type, or payload family.
2. Preserve the raw object/request as a focused fixture under the owning test
   project; keep revisitable probes in `scratch/animestudio/<task>/`.
3. Patch the narrow parser/exporter boundary and add positive and negative tests.
4. Rebuild the CLI, rerun the smallest affected export, and inspect object-level
   diagnostics.
5. Run broad extraction only when focused parity passes and publication needs it.
6. Update this file only for durable conclusions; publish inventories and hashes
   to reports.

## Remaining gaps

- Close SkillData's real formatter/ref-reader cursor from a current authenticated
  logical file through the anonymous terminal start; method identity and a final
  one-byte read alone do not prove source extent or exact EOF. Preserve candidate
  ambiguity until that connection exists, then continue the residual JsonData
  record queue rather than inferring field order from declarations.
- Continue Streaming nested element/byte-body framing using the bottom-up
  queue in `game_data_recovery.md`; concrete runtime paths and field names
  follow structural closure, not the reverse.
- Improve per-object clean/partial/error certification and dependency diagnostics.
- Recover more exact MonoBehaviour and managed-reference schemas.
- Expand shader-container coverage and complete semantic shader fixtures.
- Add converter regressions for more Unity layouts.
- Reduce peak memory for broad Story JSON/object-index work without unsafe
  filtering or unsupported JSON concurrency.
